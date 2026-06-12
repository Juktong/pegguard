from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .live_status import compute_status


@dataclass(frozen=True)
class PairSpec:
    label: str
    pair: str
    database: Path


def default_specs(root: Path | None = None, cross_pair_database: Path | None = None) -> list[PairSpec]:
    root = root or C.repo_root()
    return [
        PairSpec("primary", "WETH/USDC", root / "shadow" / "live_shadow_20260607T082122Z.sqlite3"),
        PairSpec(
            "cross-pair",
            "WETH/USDT",
            cross_pair_database or root / "shadow" / "live_shadow_weth_usdt_20260607T204521Z.sqlite3",
        ),
    ]


def compute(
    specs: list[PairSpec] | None = None,
    min_hours: float = 24.0,
    min_truth_coverage: float = 0.80,
    min_swaps: int = 1,
) -> dict:
    specs = specs or default_specs()
    rows = [_row(spec, min_hours, min_truth_coverage, min_swaps) for spec in specs]
    return {
        "complete": bool(rows) and all(bool(row.get("complete")) for row in rows),
        "min_span_hours": min_hours,
        "min_truth_coverage": min_truth_coverage,
        "min_swaps": min_swaps,
        "rows": rows,
        "note": (
            "Cross-pair live shadow is report-level evidence. It broadens live coverage across pairs, "
            "but the hard completion gate remains the primary 24h live-shadow and controlled route-away A/B."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Cross-Pair Live Shadow",
        "",
        "This report tracks live-shadow status across the primary WETH/USDC run and the",
        "WETH/USDT cross-pair run. It is evidence tracking, not an added hard gate.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'in progress'}",
        f"- Required span per pair: {float(report.get('min_span_hours', 0)):.2f} hours",
        f"- Required truth coverage: {float(report.get('min_truth_coverage', 0)):.0%}",
        "",
        "| Label | Pair | Status | Swaps | Span | Remaining | Truth | Precision | Truth capture | Database |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        status = str(row.get("status", "missing"))
        if row.get("error"):
            status = f"{status}: {row['error']}"
        lines.append(
            f"| {row.get('label', 'n/a')} | {row.get('pair', 'n/a')} | {status} | "
            f"{int(row.get('swaps', 0))} | {float(row.get('observed_span_hours', 0)):.2f}h | "
            f"{float(row.get('remaining_span_hours', 0)):.2f}h | "
            f"{_pct(row.get('truth_coverage'))} | {_pct(row.get('precision'))} | "
            f"{_pct(row.get('truth_capture'))} | `{row.get('database', 'n/a')}` |"
        )
    lines.extend(["", str(report.get("note", "")), ""])
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(spec: PairSpec, min_hours: float, min_truth_coverage: float, min_swaps: int) -> dict:
    base = {
        "label": spec.label,
        "pair": spec.pair,
        "database": str(spec.database),
        "exists": spec.database.exists(),
        "complete": False,
        "status": "missing",
        "swaps": 0,
        "valid_truth_rows": 0,
        "truth_coverage": 0.0,
        "observed_span_hours": 0.0,
        "remaining_span_hours": min_hours,
        "precision": None,
        "truth_capture": None,
        "error": None,
    }
    if not spec.database.exists():
        return base
    try:
        status = compute_status(spec.database, min_hours, min_truth_coverage, min_swaps)
    except sqlite3.Error as exc:
        base["status"] = "unreadable"
        base["error"] = str(exc)
        return base

    failed = [gate.name for gate in status.gates if not gate.passed]
    return {
        **base,
        "exists": True,
        "complete": status.complete,
        "status": "complete" if status.complete else "in progress",
        "swaps": status.swaps,
        "valid_truth_rows": status.valid_truth_rows,
        "truth_coverage": status.truth_coverage,
        "observed_span_hours": status.observed_span_hours,
        "remaining_span_hours": status.remaining_span_hours,
        "notional_e6": status.notional_e6,
        "markout_e6": status.markout_e6,
        "extra_e6": status.extra_e6,
        "precision": status.precision,
        "truth_capture": status.truth_capture,
        "pyth_health_rows": status.pyth_health_rows,
        "gap_minutes": status.gap_minutes,
        "failed_gates": failed,
    }


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate cross-pair live-shadow status report")
    parser.add_argument("--primary-database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument(
        "--cross-pair-database",
        type=Path,
        default=root / "shadow" / "live_shadow_weth_usdt_20260607T204521Z.sqlite3",
    )
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "cross_pair_live_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "cross_pair_live_report.json")
    parser.add_argument("--min-hours", type=float, default=24.0)
    parser.add_argument("--min-truth-coverage", type=float, default=0.80)
    parser.add_argument("--min-swaps", type=int, default=1)
    args = parser.parse_args()

    report = compute(
        [
            PairSpec("primary", "WETH/USDC", args.primary_database),
            PairSpec("cross-pair", "WETH/USDT", args.cross_pair_database),
        ],
        min_hours=args.min_hours,
        min_truth_coverage=args.min_truth_coverage,
        min_swaps=args.min_swaps,
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"status={'complete' if report['complete'] else 'in-progress'} pairs={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
