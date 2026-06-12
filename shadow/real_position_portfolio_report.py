from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .real_position_report import (
    DEFAULT_POSITION_ID,
    OPTIONAL_FIELDS,
    REQUIRED_FIELDS,
    RealPositionRow,
    _row as real_position_row,
    _usd,
    _validations,
)

MIN_AUDITED_POSITIONS = 3


@dataclass(frozen=True)
class PortfolioSummary:
    positions: int
    complete_positions: int
    capital_e6: int
    position_value_e6: int
    hodl_value_e6: int
    fees_earned_e6: int
    gas_cost_e6: int
    inventory_il_e6: int
    net_vs_hodl_e6: int
    net_vs_hodl_bps: float
    fee_yield_bps: float
    in_range_positions: int
    out_of_range_positions: int
    unknown_range_positions: int


def compute(
    root: Path,
    portfolio_input_json: Path,
    single_input_json: Path,
    template_json: Path,
) -> dict:
    del root
    payloads, source = _load_payloads(portfolio_input_json, single_input_json)
    complete_rows: list[RealPositionRow] = []
    row_dicts: list[dict] = []
    invalid_positions = []
    for index, payload in enumerate(payloads):
        missing = [field for field in REQUIRED_FIELDS if payload.get(field) in (None, "")]
        validations = _validations(payload) if not missing else []
        valid = not missing and all(row["passed"] for row in validations)
        if valid:
            row = real_position_row(payload)
            row_dict = asdict(row)
            row_dict["fee_pips"] = payload.get("fee_pips")
            row_dict["owner"] = payload.get("owner")
            row_dict["source_url"] = payload.get("source_url")
            complete_rows.append(row)
            row_dicts.append(row_dict)
        else:
            invalid_positions.append(
                {
                    "index": index,
                    "position_id": str(payload.get("position_id") or "unknown"),
                    "missing_fields": missing,
                    "failed_validations": [row["name"] for row in validations if not row["passed"]],
                }
            )
    summary = _summary(complete_rows)
    breadth = _breadth(row_dicts)
    breadth_complete = (
        summary.complete_positions >= MIN_AUDITED_POSITIONS
        and breadth["pool_pairs"] >= 2
        and breadth["fee_tiers"] >= 2
        and breadth["range_statuses"] >= 2
    )
    return {
        "status": "complete" if breadth_complete else "needs more audited positions",
        "complete": breadth_complete,
        "input_path": str(portfolio_input_json),
        "single_input_path": str(single_input_json),
        "input_source": source,
        "template_path": str(template_json),
        "input_present": portfolio_input_json.exists() or single_input_json.exists(),
        "template_present": template_json.exists(),
        "min_audited_positions": MIN_AUDITED_POSITIONS,
        "required_fields": list(REQUIRED_FIELDS),
        "optional_fields": list(OPTIONAL_FIELDS),
        "summary": asdict(summary),
        "breadth": breadth,
        "invalid_positions": invalid_positions,
        "rows": row_dicts,
        "command": f"python3 -m shadow.real_position_portfolio_report --input-json {portfolio_input_json}",
    }


def markdown(report: dict) -> str:
    summary = report.get("summary", {})
    breadth = report.get("breadth", {})
    lines = [
        "# Real Position Portfolio Replay",
        "",
        "This report aggregates audited real LP-position inputs. It is the",
        "multi-position extension of `docs/real_position_report.md`: each row must",
        "come from a collected position artifact or manually audited export with",
        "capital, current value, HODL value, fees, and gas.",
        "",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Input source: {report.get('input_source', 'n/a')}",
        f"- Complete positions: {int(summary.get('complete_positions', 0))}",
        f"- Minimum audited positions: {int(report.get('min_audited_positions', MIN_AUDITED_POSITIONS))}",
        f"- Pool pairs: {int(breadth.get('pool_pairs', 0))}",
        f"- Fee tiers: {int(breadth.get('fee_tiers', 0))}",
        f"- Range statuses: {int(breadth.get('range_statuses', 0))}",
        "",
        "## Portfolio Summary",
        "",
        "| Capital | Position value | HODL value | Fees | Gas | Inventory IL | Net vs HODL | Net bps | Fee yield bps | In range | Out of range | Unknown range |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        (
            f"| {_usd(int(summary.get('capital_e6', 0)))} | {_usd(int(summary.get('position_value_e6', 0)))} | "
            f"{_usd(int(summary.get('hodl_value_e6', 0)))} | {_usd(int(summary.get('fees_earned_e6', 0)))} | "
            f"{_usd(int(summary.get('gas_cost_e6', 0)))} | {_usd(int(summary.get('inventory_il_e6', 0)))} | "
            f"{_usd(int(summary.get('net_vs_hodl_e6', 0)))} | {float(summary.get('net_vs_hodl_bps', 0)):.2f} | "
            f"{float(summary.get('fee_yield_bps', 0)):.2f} | {int(summary.get('in_range_positions', 0))} | "
            f"{int(summary.get('out_of_range_positions', 0))} | {int(summary.get('unknown_range_positions', 0))} |"
        ),
        "",
        "## Positions",
        "",
        "| Chain | Position | Pair | Fee | Capital | Position value | HODL value | Fees | Gas | Net vs HODL | Net bps | Range status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        fee_pips = _position_fee_pips(row)
        lines.append(
            f"| {row['chain']} | {row['position_id']} | {row['pool_pair']} | {_fee_bps(fee_pips)} | "
            f"{_usd(int(row['capital_e6']))} | {_usd(int(row['position_value_e6']))} | "
            f"{_usd(int(row['hodl_value_e6']))} | {_usd(int(row['fees_earned_e6']))} | "
            f"{_usd(int(row['gas_cost_e6']))} | {_usd(int(row['net_vs_hodl_e6']))} | "
            f"{float(row['net_vs_hodl_bps']):.2f} | {row['status']} |"
        )
    if not report.get("rows"):
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | no complete audited positions |")

    if report.get("invalid_positions"):
        lines.extend(
            [
                "",
                "## Invalid Inputs",
                "",
                "| Index | Position | Missing fields | Failed validations |",
                "|---:|---|---|---|",
            ]
        )
        for row in report.get("invalid_positions", []):
            lines.append(
                f"| {int(row['index'])} | {row['position_id']} | "
                f"{', '.join(row.get('missing_fields', [])) or 'none'} | "
                f"{', '.join(row.get('failed_validations', [])) or 'none'} |"
            )

    lines.extend(
        [
            "",
            "## Breadth Gate",
            "",
            "The hard multi-position gate requires at least three complete audited",
            "positions, at least two pool pairs, at least two fee tiers, and at least",
            "two range-status buckets. The current single-position artifact is useful",
            "evidence, but it is not enough to characterize portfolio behavior.",
            "",
            "## Input Format",
            "",
            "`docs/real_position_portfolio_input.json` should be either a list of",
            "real-position input objects or an object with a `positions` list. If that",
            "file is absent, this report falls back to `docs/real_position_input.json`",
            "so the existing audited position remains visible.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def write_template(path: Path, seed_payload: dict | None = None) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    seed = seed_payload or {
        "chain": "base",
        "position_id": DEFAULT_POSITION_ID,
        "pool_pair": "TOKEN0/TOKEN1",
        "capital_e6": None,
        "position_value_e6": None,
        "hodl_value_e6": None,
        "fees_earned_e6": None,
        "gas_cost_e6": 0,
    }
    path.write_text(json.dumps({"positions": [seed]}, indent=2, sort_keys=True), encoding="utf-8")


def _load_payloads(portfolio_input_json: Path, single_input_json: Path) -> tuple[list[dict], str]:
    if portfolio_input_json.exists():
        raw = json.loads(portfolio_input_json.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return [dict(item) for item in raw], str(portfolio_input_json)
        if isinstance(raw, dict):
            positions = raw.get("positions", [])
            if isinstance(positions, list):
                return [dict(item) for item in positions], str(portfolio_input_json)
            return [raw], str(portfolio_input_json)
    if single_input_json.exists():
        return [json.loads(single_input_json.read_text(encoding="utf-8"))], str(single_input_json)
    return [], "missing"


def _summary(rows: list[RealPositionRow]) -> PortfolioSummary:
    capital = sum(row.capital_e6 for row in rows)
    position_value = sum(row.position_value_e6 for row in rows)
    hodl = sum(row.hodl_value_e6 for row in rows)
    fees = sum(row.fees_earned_e6 for row in rows)
    gas = sum(row.gas_cost_e6 for row in rows)
    inventory_il = sum(row.inventory_il_e6 for row in rows)
    net = sum(row.net_vs_hodl_e6 for row in rows)
    in_range = sum(1 for row in rows if row.in_range is True)
    out_of_range = sum(1 for row in rows if row.in_range is False)
    unknown = sum(1 for row in rows if row.in_range is None)
    return PortfolioSummary(
        positions=len(rows),
        complete_positions=len(rows),
        capital_e6=capital,
        position_value_e6=position_value,
        hodl_value_e6=hodl,
        fees_earned_e6=fees,
        gas_cost_e6=gas,
        inventory_il_e6=inventory_il,
        net_vs_hodl_e6=net,
        net_vs_hodl_bps=_bps(net, capital),
        fee_yield_bps=_bps(fees - gas, capital),
        in_range_positions=in_range,
        out_of_range_positions=out_of_range,
        unknown_range_positions=unknown,
    )


def _breadth(rows: list[dict]) -> dict:
    return {
        "pool_pairs": len({str(row.get("pool_pair", "")) for row in rows}),
        "fee_tiers": len({_position_fee_pips(row) for row in rows}),
        "range_statuses": len({str(row.get("status", "")) for row in rows}),
        "position_ids": len({str(row.get("position_id", "")) for row in rows}),
    }


def _position_fee_pips(row: dict) -> int | None:
    value = row.get("fee_pips")
    if value in (None, ""):
        return None
    return int(value)


def _fee_bps(fee_pips: int | None) -> str:
    if fee_pips is None:
        return "n/a"
    return f"{fee_pips / 100:.2f} bps"


def _bps(value_e6: int, capital_e6: int) -> float:
    if capital_e6 <= 0:
        return 0.0
    return value_e6 / capital_e6 * 10_000


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Aggregate audited real-position economics into a portfolio report")
    parser.add_argument("--input-json", type=Path, default=root / "docs" / "real_position_portfolio_input.json")
    parser.add_argument("--single-input-json", type=Path, default=root / "docs" / "real_position_input.json")
    parser.add_argument("--template-json", type=Path, default=root / "docs" / "real_position_portfolio_input_template.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "real_position_portfolio_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "real_position_portfolio_report.json")
    args = parser.parse_args()
    seed_payload = None
    if args.single_input_json.exists():
        seed_payload = json.loads(args.single_input_json.read_text(encoding="utf-8"))
    write_template(args.template_json, seed_payload)
    report = compute(root, args.input_json, args.single_input_json, args.template_json)
    write_outputs(report, args.out_md, args.out_json)
    print(
        f"real-position portfolio status={report['status']} "
        f"positions={report['summary']['complete_positions']}"
    )
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
