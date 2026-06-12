from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .live_convergence_report import compute as compute_convergence
from .live_maturity_report import compute as compute_maturity
from .live_power_report import compute as compute_power


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


def compute(specs: list[PairSpec] | None = None) -> dict:
    specs = specs or default_specs()
    rows = [_row(spec) for spec in specs]
    return {
        "complete": bool(rows) and all(bool(row.get("complete")) for row in rows),
        "rows": rows,
        "note": (
            "Cross-pair live economics applies the primary live convergence, maturity, and sample-power checks "
            "to each active live-shadow database. It broadens live evidence but is not an added hard gate."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Cross-Pair Live Economics",
        "",
        "This report applies live convergence, maturity, and sample-power checks to",
        "each active live-shadow database. It is evidence tracking, not an added",
        "hard completion gate.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'in progress'}",
        "",
        "| Label | Pair | Status | Rows | Span | Truth | Charged | Precision | Truth capture | Net | Convergence | Maturity | Power | Max additional | Database |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        status = str(row.get("status", "missing"))
        if row.get("error"):
            status = f"{status}: {row['error']}"
        lines.append(
            f"| {row.get('label', 'n/a')} | {row.get('pair', 'n/a')} | {status} | "
            f"{int(row.get('rows', 0))} | {float(row.get('observed_span_hours', 0)):.2f}h | "
            f"{_pct(row.get('truth_coverage'))} | {int(row.get('charged_rows', 0))} | "
            f"{_pct(row.get('precision'))} | {_pct(row.get('capture_truth'))} | "
            f"{_bps(row.get('net_bps'))} | {_yes(row.get('convergence_complete'))} | "
            f"{_yes(row.get('maturity_complete'))} | {_yes(row.get('power_complete'))} | "
            f"{_hours(row.get('max_additional_hours_needed'))} | `{row.get('database', 'n/a')}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `complete` here means that convergence, maturity, and power are each measurable for that pair.",
            "- A young cross-pair collector can still have high precision but insufficient buckets for a stable sample-power estimate.",
            "- This report does not replace the primary 24h live-shadow gate or the controlled route-away A/B.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(spec: PairSpec) -> dict:
    base = {
        "label": spec.label,
        "pair": spec.pair,
        "database": str(spec.database),
        "exists": spec.database.exists(),
        "complete": False,
        "status": "missing",
        "rows": 0,
        "observed_span_hours": 0.0,
        "truth_coverage": 0.0,
        "charged_rows": 0,
        "precision": None,
        "capture_truth": None,
        "net_bps": None,
        "convergence_complete": False,
        "maturity_complete": False,
        "power_complete": False,
        "max_additional_hours_needed": None,
        "power_statuses": [],
        "error": None,
    }
    if not spec.database.exists():
        return base
    try:
        convergence = compute_convergence(spec.database)
        maturity = compute_maturity(spec.database)
        power = compute_power(spec.database)
    except sqlite3.Error as exc:
        return {**base, "status": "unreadable", "error": str(exc)}

    power_metrics = power.get("metrics", [])
    statuses = sorted({str(row.get("status", "")) for row in power_metrics if row.get("status")})
    max_additional = max(
        (
            float(row.get("additional_hours_needed", 0))
            for row in power_metrics
            if row.get("additional_hours_needed") is not None
        ),
        default=None,
    )
    complete = bool(convergence.get("complete")) and bool(maturity.get("complete")) and bool(power.get("complete"))
    return {
        **base,
        "exists": True,
        "complete": complete,
        "status": "complete" if complete else "in progress",
        "rows": int(convergence.get("rows", power.get("rows", 0))),
        "observed_span_hours": float(power.get("observed_span_hours", 0.0)),
        "truth_coverage": float(convergence.get("truth_coverage", power.get("truth_coverage", 0.0))),
        "charged_rows": int(convergence.get("charged_rows", power.get("charged_rows", 0))),
        "precision": convergence.get("precision"),
        "capture_truth": convergence.get("capture_truth"),
        "net_bps": convergence.get("net_bps"),
        "convergence_complete": bool(convergence.get("complete")),
        "maturity_complete": bool(maturity.get("complete")),
        "power_complete": bool(power.get("complete")),
        "convergence_bucket_count": int(convergence.get("bucket_count", 0)),
        "maturity_checkpoint_count": int(maturity.get("checkpoint_count", 0)),
        "power_bucket_count": int(power.get("bucket_count", 0)),
        "max_additional_hours_needed": max_additional,
        "power_statuses": statuses,
    }


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def _hours(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}h"


def _yes(value: object) -> str:
    return "yes" if value else "no"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate cross-pair live economic quality report")
    parser.add_argument("--primary-database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument(
        "--cross-pair-database",
        type=Path,
        default=root / "shadow" / "live_shadow_weth_usdt_20260607T204521Z.sqlite3",
    )
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "cross_pair_live_economics_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "cross_pair_live_economics_report.json")
    args = parser.parse_args()

    report = compute(
        [
            PairSpec("primary", "WETH/USDC", args.primary_database),
            PairSpec("cross-pair", "WETH/USDT", args.cross_pair_database),
        ]
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"status={'complete' if report['complete'] else 'in-progress'} pairs={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
