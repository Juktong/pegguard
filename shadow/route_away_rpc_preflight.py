from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Mapping

from . import constants as C
from .route_away_collect import _expected_chain_id, _normalize_pool_id, _rpc_client, validate_distinct_pool_identities
from .route_away_readiness import _collect_values, _load_dotenv, _project_defaults


NETWORK_KEYS = ("rpc_url", "chain", "pair", "baseline_pool", "treatment_pool")
SETUP_KEYS = NETWORK_KEYS + ("chain_id", "baseline_kind", "baseline_pool_id", "treatment_kind", "treatment_pool_id")


def compute_static(root: Path, env: Mapping[str, str] | None = None) -> dict:
    values = _values(root, env)
    missing = [key for key in NETWORK_KEYS if not values[key]["resolved"]]
    implicit = [key for key in NETWORK_KEYS if values[key]["resolved"] and not values[key]["present"]]
    checks = _static_checks(values)
    failed_checks = [check for check in checks if not check["passed"]]
    return {
        "status": _static_status(missing, implicit, failed_checks),
        "executed": False,
        "missing_inputs": missing,
        "implicit_inputs": implicit,
        "inputs": _input_summary(values),
        "checks": checks,
        "notes": [
            "This preflight checks chain id and contract code before route-away log collection.",
            "It is not route-away evidence and does not satisfy the controlled A/B gate.",
            "Run with --execute only after setting explicit chain, RPC, baseline/treatment addresses, and v4 pool ids when needed.",
        ],
    }


async def compute_execute(root: Path, env: Mapping[str, str] | None = None) -> dict:
    report = compute_static(root, env)
    setup_failures = [check for check in report["checks"] if not check["passed"]]
    if report["missing_inputs"] or report["implicit_inputs"] or setup_failures:
        report["status"] = "not executed"
        report["notes"].append("Execution skipped because controlled network context is incomplete, implicit, or invalid.")
        return report

    values = _values(root, env)
    rpc_url = str(values["rpc_url"]["value"])
    chain = str(values["chain"]["value"])
    baseline = str(values["baseline_pool"]["value"])
    treatment = str(values["treatment_pool"]["value"])
    expected_chain_id = _expected_chain_id(chain)
    checks = list(report["checks"])
    rpc = _rpc_client(rpc_url, chain)
    async with await rpc.connect() as session:
        actual_chain_id = int(str(await rpc.call(session, "eth_chainId", [])), 16)
        checks.append(
            {
                "name": "chain id matches",
                "passed": expected_chain_id is None or actual_chain_id == expected_chain_id,
                "observed": actual_chain_id,
                "expected": expected_chain_id,
            }
        )
        for label, address in (("baseline", baseline), ("treatment", treatment)):
            code = await rpc.call(session, "eth_getCode", [address, "latest"])
            has_code = isinstance(code, str) and code.lower() not in ("", "0x", "0x0")
            checks.append(
                {
                    "name": f"{label} contract code",
                    "passed": has_code,
                    "observed": "code present" if has_code else "no code",
                    "address": address,
                }
            )
    report["executed"] = True
    report["checks"] = checks
    report["status"] = "passed" if all(check["passed"] for check in checks) else "failed"
    return report


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away RPC Preflight",
        "",
        "This is a non-gating setup check for the controlled route-away experiment.",
        "It verifies network/address consistency before the expensive log scan.",
        "",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Executed RPC checks: {'yes' if report.get('executed') else 'no'}",
        f"- Counts for controlled route-away gate: no",
        "",
        "## Inputs",
        "",
        "| Input | Resolved | Explicit | Source | Value |",
        "|---|---:|---:|---|---|",
    ]
    for row in report.get("inputs", []):
        lines.append(
            f"| `{row['key']}` | {'yes' if row['resolved'] else 'no'} | {'yes' if row['explicit'] else 'no'} | "
            f"{row['source']} | {row['display_value']} |"
        )
    if report.get("missing_inputs"):
        lines.extend(["", f"- Missing inputs: {', '.join(f'`{item}`' for item in report['missing_inputs'])}"])
    if report.get("implicit_inputs"):
        lines.extend(["", f"- Implicit inputs: {', '.join(f'`{item}`' for item in report['implicit_inputs'])}"])

    lines.extend(["", "## Checks", "", "| Check | Passed | Observed | Expected |", "|---|---:|---|---|"])
    for check in report.get("checks", []):
        lines.append(
            f"| {check['name']} | {'yes' if check.get('passed') else 'no'} | "
            f"{check.get('observed', 'n/a')} | {check.get('expected', check.get('address', 'n/a'))} |"
        )
    if not report.get("checks"):
        lines.append("| n/a | no | not executed | explicit controlled context required |")

    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in report.get("notes", []))
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _values(root: Path, env: Mapping[str, str] | None) -> dict[str, dict]:
    if env is None:
        dotenv = _load_dotenv(root / ".env")
        merged = dict(dotenv)
        merged.update(os.environ)
        env = merged
    return _collect_values(env, _project_defaults(root))


def _input_summary(values: dict[str, dict]) -> list[dict]:
    rows = []
    for key in SETUP_KEYS:
        value = values[key]
        rows.append(
            {
                "key": key,
                "resolved": bool(value["resolved"]),
                "explicit": bool(value["present"]),
                "source": value["source"] or "missing",
                "display_value": _display(key, value["value"]),
            }
        )
    return rows


def _static_status(missing: list[str], implicit: list[str], failed_checks: list[dict]) -> str:
    if missing or implicit:
        return "missing explicit context"
    if failed_checks:
        return "failed setup checks"
    return "ready to execute"


def _static_checks(values: dict[str, dict]) -> list[dict]:
    baseline = str(values["baseline_pool"]["value"] or "")
    treatment = str(values["treatment_pool"]["value"] or "")
    if not baseline or not treatment:
        return []
    checks: list[dict] = []
    chain_id_check = _chain_id_check(values)
    if chain_id_check is not None:
        checks.append(chain_id_check)
        if not chain_id_check["passed"]:
            return checks
    baseline_kind = str(values["baseline_kind"]["value"] or "v3")
    treatment_kind = str(values["treatment_kind"]["value"] or "v4")
    baseline_pool_id = str(values["baseline_pool_id"]["value"] or "") or None
    treatment_pool_id = str(values["treatment_pool_id"]["value"] or "") or None
    kinds_valid = baseline_kind in ("v3", "v4") and treatment_kind in ("v3", "v4")
    checks.append(
        {
            "name": "pool kinds valid",
            "passed": kinds_valid,
            "observed": f"baseline={baseline_kind}, treatment={treatment_kind}",
            "expected": "baseline/treatment kind in {v3,v4}",
        }
    )
    if not kinds_valid:
        return checks
    v4_ids_present = (baseline_kind != "v4" or bool(baseline_pool_id)) and (
        treatment_kind != "v4" or bool(treatment_pool_id)
    )
    checks.append(
        {
            "name": "v4 pool ids present",
            "passed": v4_ids_present,
            "observed": f"baseline_pool_id={'set' if baseline_pool_id else 'missing'}, treatment_pool_id={'set' if treatment_pool_id else 'missing'}",
            "expected": "pool id required for each v4 PoolManager side",
        }
    )
    if not v4_ids_present:
        return checks
    pool_id_format_error = _pool_id_format_error(baseline_kind, treatment_kind, baseline_pool_id, treatment_pool_id)
    checks.append(
        {
            "name": "v4 pool ids valid",
            "passed": pool_id_format_error is None,
            "observed": pool_id_format_error or "set v4 pool ids are hex bytes32-compatible",
            "expected": "hex bytes32-compatible pool ids",
        }
    )
    if pool_id_format_error is not None:
        return checks
    try:
        validate_distinct_pool_identities(
            baseline,
            treatment,
            baseline_kind,
            treatment_kind,
            baseline_pool_id,
            treatment_pool_id,
        )
    except ValueError as exc:
        checks.append(
            {
                "name": "baseline/treatment pool identities distinct",
                "passed": False,
                "observed": str(exc),
                "expected": "distinct controlled A/B pools",
            }
        )
        return checks
    observed = "same PoolManager with distinct v4 pool ids" if baseline.lower() == treatment.lower() else "addresses differ"
    checks.append(
        {
            "name": "baseline/treatment pool identities distinct",
            "passed": True,
            "observed": observed,
            "expected": "distinct controlled A/B pools",
        }
    )
    return checks


def _chain_id_check(values: dict[str, dict]) -> dict | None:
    raw_chain_id = values["chain_id"]["value"]
    if raw_chain_id in (None, ""):
        return None
    chain = str(values["chain"]["value"] or "")
    expected = _expected_chain_id(chain) if chain else None
    try:
        actual = int(str(raw_chain_id), 0)
    except ValueError:
        return {
            "name": "chain id matches selected chain",
            "passed": False,
            "observed": f"chain_id={raw_chain_id} is not an integer; selected chain={chain or 'missing'}",
            "expected": "numeric chain id compatible with selected chain",
        }
    if expected is None:
        return {
            "name": "chain id matches selected chain",
            "passed": True,
            "observed": f"chain_id={actual}; selected chain={chain or 'missing'} has no known numeric mapping",
            "expected": "no known mapping",
        }
    return {
        "name": "chain id matches selected chain",
        "passed": actual == expected,
        "observed": f"chain_id={actual}, selected chain={chain}",
        "expected": expected,
    }


def _pool_id_format_error(
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: str | None,
    treatment_pool_id: str | None,
) -> str | None:
    failures = []
    for label, kind, pool_id in (
        ("baseline", baseline_kind, baseline_pool_id),
        ("treatment", treatment_kind, treatment_pool_id),
    ):
        if kind != "v4" or not pool_id:
            continue
        try:
            _normalize_pool_id(pool_id)
        except ValueError as exc:
            failures.append(f"{label}: {exc}")
    return "; ".join(failures) if failures else None


def _display(key: str, value: object) -> str:
    if value is None:
        return "missing"
    if key == "rpc_url":
        return "<set>"
    text = str(value)
    if len(text) > 18:
        return text[:10] + "..." + text[-6:]
    return text


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check route-away controlled A/B RPC and address setup")
    parser.add_argument("--execute", action="store_true", help="perform live RPC chain/code checks")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_rpc_preflight.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_rpc_preflight.json")
    args = parser.parse_args()
    report = asyncio.run(compute_execute(root)) if args.execute else compute_static(root)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away rpc preflight={report['status']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["status"] in {"passed", "ready to execute"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
