from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

from . import constants as C


DEFAULT_POSITION_URL = "https://app.uniswap.org/positions/v4/base/2200741"
DEFAULT_POSITION_ID = "2200741"
FIELD_SPECS = {
    "chain": (("REAL_POSITION_CHAIN", "CHAIN"), "Chain label for the position export."),
    "position_id": (("REAL_POSITION_ID", "POSITION_ID"), "Uniswap v4 position NFT id."),
    "pool_pair": (("REAL_POSITION_POOL_PAIR", "POOL_PAIR"), "Human-readable pair label, e.g. WETH/USDC."),
    "capital_e6": (("REAL_POSITION_CAPITAL_E6", "CAPITAL_E6"), "Initial or contributed capital in quote-token e6 units."),
    "position_value_e6": (("REAL_POSITION_VALUE_E6", "POSITION_VALUE_E6"), "Current position inventory value in quote-token e6 units."),
    "hodl_value_e6": (("REAL_POSITION_HODL_VALUE_E6", "HODL_VALUE_E6"), "Value of the original token inventory if held outside the pool."),
    "fees_earned_e6": (("REAL_POSITION_FEES_EARNED_E6", "FEES_EARNED_E6"), "Collected plus uncollected fees in quote-token e6 units."),
    "owner": (("REAL_POSITION_OWNER", "POSITION_OWNER"), "Position owner address."),
    "block_number": (("REAL_POSITION_BLOCK_NUMBER", "BLOCK_NUMBER"), "Block used for valuation."),
    "collected_at": (("REAL_POSITION_COLLECTED_AT", "COLLECTED_AT"), "UTC timestamp for the audited export."),
    "token0": (("REAL_POSITION_TOKEN0", "TOKEN0"), "Pool token0 symbol or address."),
    "token1": (("REAL_POSITION_TOKEN1", "TOKEN1"), "Pool token1 symbol or address."),
    "fee_pips": (("REAL_POSITION_FEE_PIPS", "FEE_PIPS"), "Pool fee in pips."),
    "tick_lower": (("REAL_POSITION_TICK_LOWER", "TICK_LOWER"), "Position lower tick."),
    "tick_upper": (("REAL_POSITION_TICK_UPPER", "TICK_UPPER"), "Position upper tick."),
    "current_tick": (("REAL_POSITION_CURRENT_TICK", "CURRENT_TICK"), "Current pool tick at valuation time."),
    "liquidity": (("REAL_POSITION_LIQUIDITY", "LIQUIDITY"), "Position liquidity."),
    "in_range": (("REAL_POSITION_IN_RANGE", "IN_RANGE"), "Whether the current tick is within the position range."),
    "gas_cost_e6": (("REAL_POSITION_GAS_COST_E6", "GAS_COST_E6"), "Gas cost assigned to the position in quote-token e6 units."),
    "source_url": (("REAL_POSITION_SOURCE_URL", "POSITION_SOURCE_URL"), "Source URL or export reference."),
}
REQUIRED_FIELDS = (
    "chain",
    "position_id",
    "pool_pair",
    "capital_e6",
    "position_value_e6",
    "hodl_value_e6",
    "fees_earned_e6",
)
OPTIONAL_FIELDS = (
    "owner",
    "block_number",
    "collected_at",
    "token0",
    "token1",
    "fee_pips",
    "tick_lower",
    "tick_upper",
    "current_tick",
    "liquidity",
    "in_range",
    "gas_cost_e6",
    "source_url",
)


@dataclass(frozen=True)
class RealPositionRow:
    chain: str
    position_id: str
    pool_pair: str
    capital_e6: int
    position_value_e6: int
    hodl_value_e6: int
    fees_earned_e6: int
    gas_cost_e6: int
    inventory_il_e6: int
    net_vs_hodl_e6: int
    inventory_il_bps: float
    fee_yield_bps: float
    net_vs_hodl_bps: float
    in_range: bool | None
    tick_lower: int | None
    tick_upper: int | None
    current_tick: int | None
    status: str


def compute(root: Path, input_json: Path, template_json: Path, env: Mapping[str, str] | None = None) -> dict:
    payload = _load_json(input_json)
    metadata = _load_json(root / "docs" / "real_position_metadata.json")
    lifecycle = _load_json(root / "docs" / "real_position_lifecycle.json")
    template_present = template_json.exists()
    input_present = input_json.exists()
    missing = [field for field in REQUIRED_FIELDS if payload.get(field) in (None, "")]
    validations = _validations(payload) if input_present else []
    complete = input_present and not missing and all(row["passed"] for row in validations)
    row = _row(payload) if complete else None
    if complete:
        status = "complete"
    elif input_present:
        status = "incomplete input"
    else:
        status = "missing input"
    readiness = _readiness(root, payload, missing, env)
    return {
        "status": status,
        "complete": complete,
        "target_position_url": payload.get("source_url") or DEFAULT_POSITION_URL,
        "target_position_id": str(payload.get("position_id") or DEFAULT_POSITION_ID),
        "input_path": str(input_json),
        "template_path": str(template_json),
        "input_present": input_present,
        "template_present": template_present,
        "missing_fields": missing,
        "validations": validations,
        "readiness": readiness,
        "metadata": metadata,
        "lifecycle": lifecycle,
        "required_fields": list(REQUIRED_FIELDS),
        "optional_fields": list(OPTIONAL_FIELDS),
        "rows": [] if row is None else [asdict(row)],
        "command": _command(root, input_json),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Real Position Replay",
        "",
        "This report is the real LP-position economics gate. It intentionally does",
        "not infer ownership, value, or fee data from proxy reports. The input must",
        "come from a collected position artifact or manually audited position export.",
        "",
        f"- Status: {report.get('status', 'missing input')}",
        f"- Target position: `{report.get('target_position_id', DEFAULT_POSITION_ID)}`",
        f"- Target URL: {report.get('target_position_url', DEFAULT_POSITION_URL)}",
        f"- Input present: {'yes' if report.get('input_present') else 'no'}",
        f"- Template present: {'yes' if report.get('template_present') else 'no'}",
        "",
    ]
    if report.get("missing_fields"):
        lines.extend(
            [
                "## Missing Fields",
                "",
                ", ".join(f"`{field}`" for field in report.get("missing_fields", [])),
                "",
            ]
        )
    if report.get("validations"):
        lines.extend(
            [
                "## Validations",
                "",
                "| Check | Passed | Details |",
                "|---|---:|---|",
            ]
        )
        for row in report["validations"]:
            lines.append(f"| {row['name']} | {'yes' if row['passed'] else 'no'} | {row['details']} |")
        lines.append("")

    metadata = report.get("metadata", {})
    complete = bool(report.get("complete"))
    lines.extend(
        [
            "## On-Chain Metadata",
            "",
        ]
    )
    if metadata:
        metadata_note = (
            [
                "The metadata collector proves the NFT and pool shape and supplies",
                "the current inventory and uncollected-fee values used by the",
                "materialized input.",
            ]
            if complete
            else [
                "The metadata collector proves the NFT and pool shape, but it does not",
                "replace the audited value/HODL/fee fields required for the economic gate.",
            ]
        )
        lines.extend(
            [
                f"- Metadata status: {metadata.get('status', 'unknown')}",
                f"- Metadata block: {metadata.get('block_number', 'n/a')}",
                f"- Owner: `{metadata.get('owner', 'n/a')}`",
                f"- Pair: {metadata.get('pool_pair', 'n/a')}",
                f"- Fee: {int(metadata.get('fee_pips', 0)) / 100:.2f} bps",
                f"- Position liquidity: {metadata.get('position_liquidity', 'n/a')}",
                f"- Current tick: {metadata.get('current_tick', 'n/a')}",
                f"- Tick range: {metadata.get('tick_lower', 'n/a')} to {metadata.get('tick_upper', 'n/a')}",
                f"- In range: {'yes' if metadata.get('in_range') else 'no'}",
                f"- Current inventory value: {_usd(int(metadata.get('computed_position_value_e6', 0)))}",
                f"- Uncollected fee value: {_usd(int(metadata.get('computed_uncollected_fees_e6', 0)))}",
                f"- Inventory + uncollected fees: {_usd(int(metadata.get('computed_position_value_with_uncollected_fees_e6', 0)))}",
                "",
                *metadata_note,
                "",
            ]
        )
    else:
        lines.extend(
            [
                "No on-chain metadata artifact is present.",
                "",
                "```sh",
                "python3 -m shadow.real_position_metadata --rpc-url https://mainnet.base.org",
                "```",
                "",
            ]
        )

    lifecycle = report.get("lifecycle", {})
    if lifecycle:
        lifecycle_note = (
            [
                "The materialized input uses this lifecycle scan for contributed",
                "inventory and current HODL value, paired with StateView metadata for",
                "current inventory and uncollected fees. Same-block ordering caveats",
                "remain documented in the lifecycle artifact.",
            ]
            if complete
            else [
                "This scan is provisional evidence from Base logs. It does not replace",
                "the audited `capital_e6`, `hodl_value_e6`, and `fees_earned_e6` fields",
                "required for the real-position economics gate.",
            ]
        )
        lines.extend(
            [
                "## Lifecycle Scan",
                "",
                f"- Scan status: {lifecycle.get('status', 'unknown')}",
                f"- Mint block: {lifecycle.get('mint_block', 'not found')}",
                f"- Lifecycle events: {len(lifecycle.get('events', []))}",
                f"- Provisional HODL value: {_usd(int(lifecycle.get('provisional_hodl_value_e6', 0)))}",
                f"- Provisional net vs HODL: {_usd(int(lifecycle.get('provisional_net_vs_hodl_e6', 0)))}",
                "",
                *lifecycle_note,
                "",
            ]
        )

    readiness = report.get("readiness", {})
    lines.extend(
        [
            "## Readiness",
            "",
            f"- Ready to materialize from env: {'yes' if readiness.get('ready_from_env') else 'no'}",
            "",
            "| Field | Required | Artifact | Env available | Env names | Notes |",
            "|---|---:|---:|---:|---|---|",
        ]
    )
    for row in readiness.get("fields", []):
        lines.append(
            f"| `{row['field']}` | {'yes' if row['required'] else 'no'} | "
            f"{'yes' if row['artifact_present'] else 'no'} | {'yes' if row['env_present'] else 'no'} | "
            f"`{', '.join(row['env_names'])}` | {row['description']} |"
        )
    if readiness.get("missing_for_env"):
        lines.extend(
            [
                "",
                "Missing required env/materialized fields: "
                + ", ".join(f"`{field}`" for field in readiness.get("missing_for_env", [])),
                "",
            ]
        )
    lines.extend(
        [
            "Materialize audited input after collecting the values:",
            "",
            "```sh",
            readiness.get("collect_command", ""),
            "```",
            "",
        ]
    )

    lines.extend(
        [
            "## Economics",
            "",
            "| Chain | Position | Pair | Capital | Position value | HODL value | Fees | Gas | Inventory IL | Net vs HODL | Net bps | Range status |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['chain']} | {row['position_id']} | {row['pool_pair']} | {_usd(int(row['capital_e6']))} | "
            f"{_usd(int(row['position_value_e6']))} | {_usd(int(row['hodl_value_e6']))} | "
            f"{_usd(int(row['fees_earned_e6']))} | {_usd(int(row['gas_cost_e6']))} | "
            f"{_usd(int(row['inventory_il_e6']))} | {_usd(int(row['net_vs_hodl_e6']))} | "
            f"{float(row['net_vs_hodl_bps']):.2f} | {row['status']} |"
        )
    if not report.get("rows"):
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no collected position input |")

    lines.extend(
        [
            "",
            "## Input Schema",
            "",
            f"- Required: {', '.join(f'`{field}`' for field in report.get('required_fields', []))}",
            f"- Optional: {', '.join(f'`{field}`' for field in report.get('optional_fields', []))}",
            "",
            "## Command",
            "",
            "After `docs/real_position_input.json` is filled with audited position data:",
            "",
            "```sh",
            report.get("command", ""),
            "```",
            "",
            "## Interpretation",
            "",
            "- `inventory_il = position_value - hodl_value`.",
            "- `net_vs_hodl = position_value + fees_earned - gas_cost - hodl_value`.",
            "- This is a position-level measurement, not a same-swap upper bound or route-away proxy.",
            "- A missing input keeps the economic-test goal open; do not substitute proxy rows for this gate.",
            "- The collector only materializes audited values; it does not infer position value, HODL value, or fees from proxy reports.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def write_template(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    template = {
        "source_url": DEFAULT_POSITION_URL,
        "chain": "base",
        "position_id": DEFAULT_POSITION_ID,
        "pool_pair": "TOKEN0/TOKEN1",
        "owner": "0x0000000000000000000000000000000000000000",
        "block_number": None,
        "collected_at": "YYYY-MM-DDTHH:MM:SSZ",
        "token0": "TOKEN0",
        "token1": "TOKEN1",
        "fee_pips": None,
        "tick_lower": None,
        "tick_upper": None,
        "current_tick": None,
        "liquidity": None,
        "in_range": None,
        "capital_e6": None,
        "position_value_e6": None,
        "hodl_value_e6": None,
        "fees_earned_e6": None,
        "gas_cost_e6": 0,
    }
    path.write_text(json.dumps(template, indent=2, sort_keys=True), encoding="utf-8")


def build_payload_from_env(env: Mapping[str, str] | None = None) -> dict:
    env = env or _merged_env(C.repo_root())
    payload: dict[str, object] = {}
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        spec = FIELD_SPECS.get(field)
        if spec is None:
            continue
        env_name, value = _first_env(env, spec[0])
        if value is None:
            continue
        payload[field] = _coerce_field(field, value)
    payload.setdefault("source_url", DEFAULT_POSITION_URL)
    payload.setdefault("position_id", DEFAULT_POSITION_ID)
    payload.setdefault("gas_cost_e6", 0)
    return payload


def write_input_from_payload(payload: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _row(payload: dict) -> RealPositionRow:
    capital = int(payload["capital_e6"])
    position_value = int(payload["position_value_e6"])
    hodl_value = int(payload["hodl_value_e6"])
    fees = int(payload["fees_earned_e6"])
    gas = int(payload.get("gas_cost_e6") or 0)
    inventory_il = position_value - hodl_value
    net = inventory_il + fees - gas
    in_range = payload.get("in_range")
    status = _range_status(in_range)
    return RealPositionRow(
        chain=str(payload["chain"]),
        position_id=str(payload["position_id"]),
        pool_pair=str(payload["pool_pair"]),
        capital_e6=capital,
        position_value_e6=position_value,
        hodl_value_e6=hodl_value,
        fees_earned_e6=fees,
        gas_cost_e6=gas,
        inventory_il_e6=inventory_il,
        net_vs_hodl_e6=net,
        inventory_il_bps=_bps(inventory_il, capital),
        fee_yield_bps=_bps(fees - gas, capital),
        net_vs_hodl_bps=_bps(net, capital),
        in_range=None if in_range is None else bool(in_range),
        tick_lower=_maybe_int(payload.get("tick_lower")),
        tick_upper=_maybe_int(payload.get("tick_upper")),
        current_tick=_maybe_int(payload.get("current_tick")),
        status=status,
    )


def _validations(payload: dict) -> list[dict]:
    rows = []
    capital = _maybe_int(payload.get("capital_e6"))
    position_value = _maybe_int(payload.get("position_value_e6"))
    hodl_value = _maybe_int(payload.get("hodl_value_e6"))
    fees = _maybe_int(payload.get("fees_earned_e6"))
    gas = _maybe_int(payload.get("gas_cost_e6")) if payload.get("gas_cost_e6") is not None else 0
    tick_lower = _maybe_int(payload.get("tick_lower"))
    tick_upper = _maybe_int(payload.get("tick_upper"))
    current_tick = _maybe_int(payload.get("current_tick"))
    rows.append(_validation("capital positive", capital is not None and capital > 0, f"capital_e6={_na(capital)}"))
    rows.append(_validation("position value non-negative", position_value is not None and position_value >= 0, f"position_value_e6={_na(position_value)}"))
    rows.append(_validation("hodl value positive", hodl_value is not None and hodl_value > 0, f"hodl_value_e6={_na(hodl_value)}"))
    rows.append(_validation("fees non-negative", fees is not None and fees >= 0, f"fees_earned_e6={_na(fees)}"))
    rows.append(_validation("gas non-negative", gas is not None and gas >= 0, f"gas_cost_e6={_na(gas)}"))
    if tick_lower is not None or tick_upper is not None:
        rows.append(_validation("tick range ordered", tick_lower is not None and tick_upper is not None and tick_lower < tick_upper, f"tick_lower={_na(tick_lower)}, tick_upper={_na(tick_upper)}"))
    if current_tick is not None and tick_lower is not None and tick_upper is not None:
        rows.append(_validation("range flag matches ticks", payload.get("in_range") is None or bool(payload.get("in_range")) == (tick_lower <= current_tick <= tick_upper), f"current_tick={current_tick}"))
    return rows


def _validation(name: str, passed: bool, details: str) -> dict:
    return {"name": name, "passed": passed, "details": details}


def _range_status(in_range: object) -> str:
    if in_range is None:
        return "range unknown"
    return "in range" if bool(in_range) else "out of range"


def _bps(value_e6: int, capital_e6: int) -> float:
    if capital_e6 <= 0:
        return 0.0
    return value_e6 / capital_e6 * 10_000


def _command(root: Path, input_json: Path) -> str:
    if input_json.is_relative_to(root):
        path = input_json.relative_to(root)
    else:
        path = input_json
    return f"python3 -m shadow.real_position_report --input-json {path}"


def _readiness(root: Path, payload: dict, missing: list[str], env: Mapping[str, str] | None) -> dict:
    env = env or _merged_env(root)
    fields = []
    for field in REQUIRED_FIELDS + OPTIONAL_FIELDS:
        env_names, description = FIELD_SPECS[field]
        _env_name, env_value = _first_env(env, env_names)
        fields.append(
            {
                "field": field,
                "required": field in REQUIRED_FIELDS,
                "artifact_present": payload.get(field) not in (None, ""),
                "env_present": env_value not in (None, ""),
                "env_names": list(env_names),
                "description": description,
            }
        )
    missing_for_env = [
        field
        for field in REQUIRED_FIELDS
        if payload.get(field) in (None, "")
        and _first_env(env, FIELD_SPECS[field][0])[1] in (None, "")
    ]
    return {
        "ready_from_env": not missing_for_env,
        "missing_for_env": missing_for_env,
        "missing_from_artifact": missing,
        "fields": fields,
        "collect_command": _collect_command(root),
    }


def _collect_command(root: Path) -> str:
    del root
    return "\n".join(
        [
            "python3 -m shadow.real_position_collect \\",
            '  --chain "${REAL_POSITION_CHAIN:-base}" \\',
            '  --position-id "${REAL_POSITION_ID:-2200741}" \\',
            '  --pool-pair "$REAL_POSITION_POOL_PAIR" \\',
            '  --capital-e6 "$REAL_POSITION_CAPITAL_E6" \\',
            '  --position-value-e6 "$REAL_POSITION_VALUE_E6" \\',
            '  --hodl-value-e6 "$REAL_POSITION_HODL_VALUE_E6" \\',
            '  --fees-earned-e6 "$REAL_POSITION_FEES_EARNED_E6" \\',
            "  --out-input docs/real_position_input.json \\",
            "  --out-md docs/real_position_report.md \\",
            "  --out-json docs/real_position_report.json",
        ]
    )


def _merged_env(root: Path) -> dict[str, str]:
    merged = _load_dotenv(root / ".env")
    merged.update(os.environ)
    return merged


def _load_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    wanted = {name for names, _description in FIELD_SPECS.values() for name in names}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in wanted:
            continue
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        if value:
            values[key] = value
    return values


def _first_env(env: Mapping[str, str], names: tuple[str, ...]) -> tuple[str | None, str | None]:
    for name in names:
        value = env.get(name)
        if value not in (None, ""):
            return name, value
    return None, None


def _coerce_field(field: str, value: str) -> object:
    if field in {
        "block_number",
        "capital_e6",
        "position_value_e6",
        "hodl_value_e6",
        "fees_earned_e6",
        "fee_pips",
        "tick_lower",
        "tick_upper",
        "current_tick",
        "gas_cost_e6",
    }:
        return int(value, 10)
    if field == "in_range":
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
        raise ValueError(f"in_range must be boolean-like, got {value!r}")
    return value



def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _maybe_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _na(value: object) -> str:
    return "n/a" if value is None else str(value)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate real LP-position economics from a collected position artifact")
    parser.add_argument("--input-json", type=Path, default=root / "docs" / "real_position_input.json")
    parser.add_argument("--template-json", type=Path, default=root / "docs" / "real_position_input_template.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "real_position_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "real_position_report.json")
    args = parser.parse_args()
    write_template(args.template_json)
    report = compute(root, args.input_json, args.template_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"real-position status={report['status']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
