from __future__ import annotations

import argparse
import glob
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .live_convergence_report import compute as compute_convergence
from .live_status import compute_status


@dataclass(frozen=True)
class FeeTierSpec:
    label: str
    pair: str
    fee_pips: int
    database: Path | None = None
    database_glob: str | None = None


def default_specs(root: Path | None = None, primary_database: Path | None = None) -> list[FeeTierSpec]:
    root = root or C.repo_root()
    return [
        FeeTierSpec(
            "primary",
            "WETH/USDC",
            500,
            database=primary_database or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3",
        ),
        FeeTierSpec(
            "same-pair 1bps",
            "WETH/USDC",
            100,
            database_glob=str(root / "shadow" / "live_shadow_weth_usdc_1bps_*.sqlite3"),
        ),
        FeeTierSpec(
            "same-pair 30bps",
            "WETH/USDC",
            3000,
            database_glob=str(root / "shadow" / "live_shadow_weth_usdc_30bps_*.sqlite3"),
        ),
    ]


def compute(
    specs: list[FeeTierSpec] | None = None,
    min_truth_coverage: float = 0.50,
    min_swaps: int = 1,
    min_quality_hours: float = 1.0,
    min_quality_charged_rows: int = 50,
) -> dict:
    specs = specs or default_specs()
    rows = [
        _row(spec, min_truth_coverage, min_swaps, min_quality_hours, min_quality_charged_rows)
        for spec in specs
    ]
    out_of_sample = [row for row in rows if row.get("label") != "primary"]
    measurable = [row for row in out_of_sample if row.get("complete")]
    return {
        "complete": bool(measurable),
        "rows": rows,
        "min_truth_coverage": min_truth_coverage,
        "min_swaps": min_swaps,
        "min_quality_hours": min_quality_hours,
        "min_quality_charged_rows": min_quality_charged_rows,
        "note": (
            "Fee-tier live shadow broadens out-of-sample evidence across same-pair fee tiers. "
            "It is non-gating and does not replace the primary 24h live-shadow or controlled route-away A/B gates."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Fee-Tier Live Shadow",
        "",
        "This report tracks live-shadow economics across the primary WETH/USDC 5 bps",
        "pool and out-of-sample WETH/USDC 1 bps / 30 bps collectors. It is evidence",
        "tracking, not an added hard gate.",
        "",
        f"- Evidence status: {'measurable' if report.get('complete') else 'in progress'}",
        f"- Minimum truth coverage for measurable rows: {float(report.get('min_truth_coverage', 0)):.0%}",
        f"- Immature-row threshold: <{float(report.get('min_quality_hours', 0)):.2f}h span or <{int(report.get('min_quality_charged_rows', 0))} charged rows",
        "",
        "| Label | Pair | Fee tier | Status | Quality | Swaps | Span | Truth | Charged | Precision | Truth capture | Net | Database |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        status = str(row.get("status", "missing"))
        if row.get("error"):
            status = f"{status}: {row['error']}"
        lines.append(
            f"| {row.get('label', 'n/a')} | {row.get('pair', 'n/a')} | {int(row.get('fee_pips', 0)) / 100:.2f} bps | "
            f"{status} | {row.get('quality_status', 'n/a')} | {int(row.get('swaps', 0))} | {float(row.get('observed_span_hours', 0)):.2f}h | "
            f"{_pct(row.get('truth_coverage'))} | {int(row.get('charged_rows', 0))} | "
            f"{_pct(row.get('precision'))} | {_pct(row.get('capture_truth'))} | {_bps(row.get('net_bps'))} | "
            f"`{row.get('database', row.get('database_glob', 'n/a'))}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The 1 bps and 30 bps pools are same-pair out-of-sample checks for whether signal behavior is specific to the 5 bps pool.",
            "- Immature rows are useful tripwires but should not be used as stable economic estimates until more charged flow arrives.",
            "- This report is not route-away elasticity evidence because no flow is choosing between PegGuard and a controlled treatment pool.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(
    spec: FeeTierSpec,
    min_truth_coverage: float,
    min_swaps: int,
    min_quality_hours: float,
    min_quality_charged_rows: int,
) -> dict:
    database = _resolve_database(spec)
    base = {
        "label": spec.label,
        "pair": spec.pair,
        "fee_pips": spec.fee_pips,
        "database": str(database) if database is not None else None,
        "database_glob": spec.database_glob,
        "exists": database is not None and database.exists(),
        "complete": False,
        "status": "missing",
        "swaps": 0,
        "valid_truth_rows": 0,
        "truth_coverage": 0.0,
        "observed_span_hours": 0.0,
        "charged_rows": 0,
        "precision": None,
        "capture_truth": None,
        "net_bps": None,
        "error": None,
        "quality_status": "missing",
    }
    if database is None or not database.exists():
        return base
    try:
        status = compute_status(database, min_hours=0, min_truth_coverage=min_truth_coverage, min_swaps=min_swaps)
        convergence = compute_convergence(database)
    except sqlite3.Error as exc:
        return {**base, "status": "unreadable", "error": str(exc)}
    complete = status.swaps >= min_swaps and status.truth_coverage >= min_truth_coverage and status.valid_truth_rows > 0
    charged_rows = int(convergence.get("charged_rows", 0))
    quality_status = _quality_status(complete, status.observed_span_hours, charged_rows, min_quality_hours, min_quality_charged_rows)
    return {
        **base,
        "exists": True,
        "complete": complete,
        "status": "complete" if status.valid_truth_rows > 0 and status.truth_coverage >= min_truth_coverage else "in progress",
        "quality_status": quality_status,
        "swaps": status.swaps,
        "valid_truth_rows": status.valid_truth_rows,
        "truth_coverage": status.truth_coverage,
        "observed_span_hours": status.observed_span_hours,
        "notional_e6": status.notional_e6,
        "extra_e6": status.extra_e6,
        "truth_markout_e6": status.markout_e6,
        "charged_rows": charged_rows,
        "precision": convergence.get("precision"),
        "capture_truth": convergence.get("capture_truth"),
        "net_bps": convergence.get("net_bps"),
    }


def _quality_status(
    measurable: bool,
    observed_span_hours: float,
    charged_rows: int,
    min_quality_hours: float,
    min_quality_charged_rows: int,
) -> str:
    if not measurable:
        return "pending truth"
    if observed_span_hours < min_quality_hours or charged_rows < min_quality_charged_rows:
        return "immature"
    return "mature"


def _resolve_database(spec: FeeTierSpec) -> Path | None:
    if spec.database is not None:
        return spec.database
    if not spec.database_glob:
        return None
    matches = sorted(Path(path) for path in glob.glob(spec.database_glob) if not str(path).endswith(("-wal", "-shm")))
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate same-pair fee-tier live-shadow report")
    parser.add_argument("--primary-database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--one-bps-glob", default=str(root / "shadow" / "live_shadow_weth_usdc_1bps_*.sqlite3"))
    parser.add_argument("--thirty-bps-glob", default=str(root / "shadow" / "live_shadow_weth_usdc_30bps_*.sqlite3"))
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "live_fee_tier_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "live_fee_tier_report.json")
    parser.add_argument("--min-truth-coverage", type=float, default=0.50)
    parser.add_argument("--min-swaps", type=int, default=1)
    parser.add_argument("--min-quality-hours", type=float, default=1.0)
    parser.add_argument("--min-quality-charged-rows", type=int, default=50)
    args = parser.parse_args()
    report = compute(
        [
            FeeTierSpec("primary", "WETH/USDC", 500, database=args.primary_database),
            FeeTierSpec("same-pair 1bps", "WETH/USDC", 100, database_glob=args.one_bps_glob),
            FeeTierSpec("same-pair 30bps", "WETH/USDC", 3000, database_glob=args.thirty_bps_glob),
        ],
        min_truth_coverage=args.min_truth_coverage,
        min_swaps=args.min_swaps,
        min_quality_hours=args.min_quality_hours,
        min_quality_charged_rows=args.min_quality_charged_rows,
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"fee-tier live shadow={'measurable' if report['complete'] else 'in-progress'} rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
