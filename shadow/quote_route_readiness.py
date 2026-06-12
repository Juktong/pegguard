from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Mapping

from . import constants as C


REQUIRED_INPUTS = (
    ("rpc_http", ("CHAIN_RPC_HTTP", "BASE_RPC_HTTP", "RPC_HTTP"), "HTTP RPC endpoint for eth_call quote measurements."),
    ("quoter", ("QUOTER_V2", "UNISWAP_V3_QUOTER_V2"), "Uniswap v3 QuoterV2-compatible contract address."),
    ("token_in", ("QUOTE_TOKEN_IN", "TOKEN_IN"), "Exact-input token address."),
    ("token_out", ("QUOTE_TOKEN_OUT", "TOKEN_OUT"), "Exact-output token address."),
    ("token_in_decimals", ("QUOTE_TOKEN_IN_DECIMALS", "TOKEN_IN_DECIMALS"), "Exact-input token decimals."),
    ("token_out_decimals", ("QUOTE_TOKEN_OUT_DECIMALS", "TOKEN_OUT_DECIMALS"), "Exact-output token decimals."),
    ("fee_tiers", ("QUOTE_FEE_TIERS", "FEE_TIERS"), "Comma-separated fee tiers in pips, e.g. 100,500,3000,10000."),
    ("amount_ins", ("QUOTE_AMOUNT_INS", "AMOUNT_INS"), "Comma-separated raw exact-input amounts."),
)

DEFAULTS = {
    "chain": "base",
    "block_tag": "latest",
}

OPTIONAL_INPUTS = (
    ("chain", ("QUOTE_CHAIN", "CHAIN"), "Chain label for the report."),
    ("block_tag", ("QUOTE_BLOCK_TAG", "BLOCK_TAG"), "Block tag or number for deterministic quotes."),
)

SECRET_KEYS = {"rpc_http"}
ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def compute(
    root: Path,
    env: Mapping[str, str] | None = None,
    quote_json_path: Path | None = None,
) -> dict:
    env = env if env is not None else os.environ
    quote_json_path = quote_json_path or root / "docs" / "quote_route_quotes.json"
    values = _collect_values(env)
    required = [_input_row(key, names, description, values, required=True) for key, names, description in REQUIRED_INPUTS]
    optional = [_input_row(key, names, description, values, required=False) for key, names, description in OPTIONAL_INPUTS]
    validations = _validations(values)
    artifacts = _artifact_rows(root, quote_json_path)
    quote_report = _load_json(quote_json_path)
    quote_rows = _quote_result_rows(quote_report)
    quoted_rows = _quoted_rows(quote_report)
    quote_complete = quoted_rows > 0
    ready_to_collect = all(row["present"] for row in required) and all(row["passed"] for row in validations)
    missing = [row["key"] for row in required if not row["present"]]
    failed = [row["name"] for row in validations if not row["passed"]]

    if quote_complete:
        status = "complete"
    elif ready_to_collect:
        status = "ready to collect"
    else:
        status = "missing inputs"

    return {
        "status": status,
        "ready_to_collect": ready_to_collect,
        "quote_result_complete": quote_complete,
        "quote_rows": quote_rows,
        "quoted_rows": quoted_rows,
        "missing_inputs": missing,
        "failed_validations": failed,
        "required_inputs": required,
        "optional_inputs": optional,
        "validations": validations,
        "artifacts": artifacts,
        "command": _command(values),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Route Readiness",
        "",
        "This is a preflight for real QuoterV2 routeability measurements.",
        "It does not count as controlled route-away evidence; it only replaces the",
        "depth-adjusted proxy with actual quote calls once the inputs are present.",
        "",
        f"- Status: {report['status']}",
        f"- Ready to collect: {'yes' if report['ready_to_collect'] else 'no'}",
        f"- Quote result complete: {'yes' if report['quote_result_complete'] else 'no'}",
        f"- Quoted rows: {int(report.get('quoted_rows', 0))}/{int(report.get('quote_rows', 0))}",
        "",
        "## Required Inputs",
        "",
        "| Input | Env names | Present | Notes |",
        "|---|---|---:|---|",
    ]
    for row in report["required_inputs"]:
        lines.append(
            f"| `{row['key']}` | `{', '.join(row['env_names'])}` | {'yes' if row['present'] else 'no'} | {row['description']} |"
        )

    lines.extend(
        [
            "",
            "## Optional Inputs And Defaults",
            "",
            "| Input | Env names | Value source | Notes |",
            "|---|---|---|---|",
        ]
    )
    for row in report["optional_inputs"]:
        source = row["source"] if row["present"] else f"default `{row['default']}`"
        lines.append(f"| `{row['key']}` | `{', '.join(row['env_names'])}` | {source} | {row['description']} |")

    lines.extend(
        [
            "",
            "## Validations",
            "",
            "| Check | Passed | Details |",
            "|---|---:|---|",
        ]
    )
    for row in report["validations"]:
        lines.append(f"| {row['name']} | {'yes' if row['passed'] else 'no'} | {row['details']} |")

    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "| Artifact | Present | Notes |",
            "|---|---:|---|",
        ]
    )
    for row in report["artifacts"]:
        lines.append(f"| `{row['path']}` | {'yes' if row['present'] else 'no'} | {row['notes']} |")

    lines.extend(
        [
            "",
            "## Command",
            "",
            "Run this only after the required inputs and validations pass:",
            "",
            "```sh",
            report["command"],
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _collect_values(env: Mapping[str, str]) -> dict[str, dict]:
    values: dict[str, dict] = {}
    for key, names, _description in REQUIRED_INPUTS + OPTIONAL_INPUTS:
        name, value = _first_env(env, names)
        default = DEFAULTS.get(key)
        resolved = value if value is not None else default
        values[key] = {
            "env_name": name,
            "env_names": list(names),
            "value": resolved,
            "present": value is not None,
            "default": default,
        }
    return values


def _input_row(key: str, names: tuple[str, ...], description: str, values: dict[str, dict], required: bool) -> dict:
    value = values[key]
    display = _display_value(key, value["value"]) if value["value"] is not None else ""
    return {
        "key": key,
        "env_names": list(names),
        "required": required,
        "present": bool(value["present"]),
        "source": value["env_name"] or "default",
        "default": value["default"],
        "display_value": display,
        "description": description,
    }


def _validations(values: dict[str, dict]) -> list[dict]:
    rpc_http = str(values["rpc_http"]["value"] or "")
    block_tag = str(values["block_tag"]["value"] or "")
    fee_tiers = _int_list(values["fee_tiers"]["value"])
    amount_ins = _int_list(values["amount_ins"]["value"])
    token_in_decimals = _int_value(values, "token_in_decimals")
    token_out_decimals = _int_value(values, "token_out_decimals")
    cast_path = shutil.which("cast")
    return [
        _validation("rpc url is http", rpc_http.startswith(("http://", "https://")), _masked(rpc_http) or "n/a"),
        _validation("quoter address valid", _is_address(values["quoter"]["value"]), _addr_details(values["quoter"]["value"])),
        _validation("token_in address valid", _is_address(values["token_in"]["value"]), _addr_details(values["token_in"]["value"])),
        _validation("token_out address valid", _is_address(values["token_out"]["value"]), _addr_details(values["token_out"]["value"])),
        _validation("token_in decimals valid", token_in_decimals is not None and 0 < token_in_decimals <= 36, f"token_in_decimals={_na(token_in_decimals)}"),
        _validation("token_out decimals valid", token_out_decimals is not None and 0 < token_out_decimals <= 36, f"token_out_decimals={_na(token_out_decimals)}"),
        _validation("fee tiers valid", bool(fee_tiers) and all(value > 0 for value in fee_tiers), ",".join(str(value) for value in fee_tiers) or "n/a"),
        _validation("amount inputs valid", bool(amount_ins) and all(value > 0 for value in amount_ins), ",".join(str(value) for value in amount_ins) or "n/a"),
        _validation("block tag present", bool(block_tag), block_tag or "n/a"),
        _validation("cast available", cast_path is not None, cast_path or "missing"),
    ]


def _artifact_rows(root: Path, quote_json_path: Path) -> list[dict]:
    artifacts = [
        (root / "shadow" / "quote_route_collect.py", "quote collector implementation"),
        (quote_json_path, "collected quote results"),
        (root / "docs" / "route_cost_proxy.md", "depth proxy comparator"),
    ]
    return [{"path": _rel(root, path), "present": path.exists(), "notes": notes} for path, notes in artifacts]


def _quote_result_rows(report: dict) -> int:
    return len(report.get("rows", []))


def _quoted_rows(report: dict) -> int:
    rows = report.get("rows", [])
    return sum(1 for row in rows if str(row.get("status", "")) == "quoted")


def _command(values: dict[str, dict]) -> str:
    return "\n".join(
        [
            "python3 -m shadow.quote_route_collect \\",
            '  --rpc-http "${CHAIN_RPC_HTTP:-${BASE_RPC_HTTP:-$RPC_HTTP}}" \\',
            '  --quoter "${QUOTER_V2:-$UNISWAP_V3_QUOTER_V2}" \\',
            '  --token-in "${QUOTE_TOKEN_IN:-$TOKEN_IN}" \\',
            '  --token-out "${QUOTE_TOKEN_OUT:-$TOKEN_OUT}" \\',
            '  --token-in-decimals "${QUOTE_TOKEN_IN_DECIMALS:-$TOKEN_IN_DECIMALS}" \\',
            '  --token-out-decimals "${QUOTE_TOKEN_OUT_DECIMALS:-$TOKEN_OUT_DECIMALS}" \\',
            '  --fee-tiers "${QUOTE_FEE_TIERS:-$FEE_TIERS}" \\',
            '  --amount-ins "${QUOTE_AMOUNT_INS:-$AMOUNT_INS}" \\',
            f"  --block-tag {values['block_tag']['value']} \\",
            "  --out-md docs/quote_route_quotes.md \\",
            "  --out-json docs/quote_route_quotes.json",
        ]
    )


def _first_env(env: Mapping[str, str], names: tuple[str, ...]) -> tuple[str | None, str | None]:
    for name in names:
        value = env.get(name)
        if value:
            return name, value
    return None, None


def _int_value(values: dict[str, dict], key: str) -> int | None:
    value = values[key]["value"]
    if value is None:
        return None
    try:
        return int(str(value), 0)
    except ValueError:
        return None


def _int_list(value: object) -> list[int]:
    if value is None:
        return []
    try:
        return [int(item.strip(), 0) for item in str(value).replace(";", ",").split(",") if item.strip()]
    except ValueError:
        return []


def _validation(name: str, passed: bool, details: str) -> dict:
    return {"name": name, "passed": bool(passed), "details": details}


def _is_address(value: object) -> bool:
    return bool(value) and ADDRESS_RE.match(str(value)) is not None


def _addr_details(value: object) -> str:
    if value is None:
        return "n/a"
    text = str(value)
    if len(text) <= 10:
        return text
    return f"{text[:6]}...{text[-4:]}"


def _display_value(key: str, value: object) -> str:
    if key in SECRET_KEYS:
        return _masked(str(value))
    return str(value)


def _masked(value: str) -> str:
    if not value:
        return ""
    if "://" in value:
        prefix = value.split("://", 1)[0]
        return f"{prefix}://<set>"
    return "<set>"


def _na(value: object) -> str:
    return "n/a" if value is None else str(value)


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate real quote-route readiness report")
    parser.add_argument("--quote-json", type=Path, default=root / "docs" / "quote_route_quotes.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_route_readiness.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_route_readiness.json")
    args = parser.parse_args()
    report = compute(root, quote_json_path=args.quote_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote route readiness={report['status']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["status"] in {"ready to collect", "complete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
