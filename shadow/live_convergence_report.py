from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM


DEFAULT_BUCKET_SEC = 60 * 60


@dataclass(frozen=True)
class ConvergenceRow:
    bucket_index: int
    start_ts_ms: int
    end_ts_ms: int
    start_offset_hours: float
    end_offset_hours: float
    rows: int
    valid_rows: int
    truth_coverage: float
    notional_e6: int
    charged_rows: int
    charged_notional_e6: int
    fallback_rows: int
    fallback_notional_e6: int
    fallback_notional_share: float | None
    base_fee_e6: int
    extra_e6: int
    correct_extra_e6: int
    truth_markout_e6: int
    precision: float | None
    capture_truth: float | None
    net_e6: int
    net_bps: float
    avg_premium_bps: float


def compute(database: Path | None = None, bucket_sec: int = DEFAULT_BUCKET_SEC) -> dict:
    database = database or C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3"
    if bucket_sec <= 0:
        raise ValueError("bucket_sec must be positive")
    if not database.exists():
        return _empty(database, bucket_sec)

    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                l.id,
                l.ts_ms,
                l.aq_e6,
                l.fresh_premium_pips,
                l.fresh_extra_e6,
                l.fresh_fallback_reason,
                t.valid,
                t.truth_corr,
                t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return _empty(database, bucket_sec)

    first_ts = int(rows[0]["ts_ms"])
    bucket_ms = bucket_sec * 1000
    bucketed: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        index = (int(row["ts_ms"]) - first_ts) // bucket_ms
        bucketed.setdefault(index, []).append(row)

    convergence_rows = [
        _convergence_row(index, bucket_rows, first_ts, bucket_ms)
        for index, bucket_rows in sorted(bucketed.items())
    ]
    valid_rows = sum(row.valid_rows for row in convergence_rows)
    charged_rows = sum(row.charged_rows for row in convergence_rows)
    extra = sum(row.extra_e6 for row in convergence_rows)
    correct_extra = sum(row.correct_extra_e6 for row in convergence_rows)
    truth_markout = sum(row.truth_markout_e6 for row in convergence_rows)
    notional = sum(row.notional_e6 for row in convergence_rows)
    net = sum(row.net_e6 for row in convergence_rows)
    rows_count = sum(row.rows for row in convergence_rows)
    return {
        "database": str(database),
        "bucket_sec": bucket_sec,
        "complete": len(convergence_rows) >= 2 and valid_rows > 0 and charged_rows > 0,
        "rows": rows_count,
        "valid_rows": valid_rows,
        "truth_coverage": valid_rows / rows_count if rows_count else 0.0,
        "bucket_count": len(convergence_rows),
        "charged_rows": charged_rows,
        "notional_e6": notional,
        "extra_e6": extra,
        "truth_markout_e6": truth_markout,
        "precision": (correct_extra / extra) if extra else None,
        "capture_truth": (extra / abs(truth_markout)) if truth_markout else None,
        "net_e6": net,
        "net_bps": _bps(net, notional),
        "min_bucket_precision": _min_non_null(row.precision for row in convergence_rows),
        "min_bucket_capture_truth": _min_non_null(row.capture_truth for row in convergence_rows),
        "min_bucket_net_bps": min((row.net_bps for row in convergence_rows if row.valid_rows), default=None),
        "max_bucket_net_bps": max((row.net_bps for row in convergence_rows if row.valid_rows), default=None),
        "convergence_rows": [asdict(row) for row in convergence_rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Live Shadow Convergence",
        "",
        "This report splits the live shadow stream into fixed time buckets and",
        "checks whether premium precision, truth-denominated capture, and net",
        "economics are concentrated in one interval. It is live evidence quality",
        "tracking; it does not replace the required 24h shadow gate.",
        "",
        f"- Database: `{report.get('database', 'n/a')}`",
        f"- Bucket size: {int(report.get('bucket_sec', 0))} seconds",
        f"- Status: {'complete' if report.get('complete') else 'in progress'}",
        f"- Buckets: {int(report.get('bucket_count', 0))}",
        f"- Truth coverage: {_pct(report.get('truth_coverage'))}",
        f"- Overall precision: {_pct(report.get('precision'))}",
        f"- Overall truth capture: {_pct(report.get('capture_truth'))}",
        f"- Overall net: {_usd(int(report.get('net_e6', 0)))} ({float(report.get('net_bps', 0.0)):.2f} bps)",
        "",
        "| Bucket | Offset | Rows | Valid | Charged | Notional | Extra | Truth markout | Precision | Capture | Net | Net bps | Fallback share |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("convergence_rows", []):
        lines.append(
            f"| {int(row['bucket_index'])} | {float(row['start_offset_hours']):.2f}-{float(row['end_offset_hours']):.2f}h | "
            f"{int(row['rows'])} | {int(row['valid_rows'])} | {int(row['charged_rows'])} | "
            f"{_usd(int(row['notional_e6']))} | {_usd(int(row['extra_e6']))} | "
            f"{_usd(int(row['truth_markout_e6']))} | {_pct(row.get('precision'))} | "
            f"{_pct(row.get('capture_truth'))} | {_usd(int(row['net_e6']))} | "
            f"{float(row['net_bps']):.2f} | {_pct(row.get('fallback_notional_share'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Low per-bucket precision means the live signal is charging flow that the truth markout does not classify as correcting.",
            "- Negative net buckets show intervals where base fee plus dynamic premium did not offset measured truth markout.",
            "- Fallback share includes stale/unseeded/failure decisions and should be read with oracle-health attribution.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _empty(database: Path, bucket_sec: int) -> dict:
    return {
        "database": str(database),
        "bucket_sec": bucket_sec,
        "complete": False,
        "rows": 0,
        "valid_rows": 0,
        "truth_coverage": 0.0,
        "bucket_count": 0,
        "charged_rows": 0,
        "notional_e6": 0,
        "extra_e6": 0,
        "truth_markout_e6": 0,
        "precision": None,
        "capture_truth": None,
        "net_e6": 0,
        "net_bps": 0.0,
        "min_bucket_precision": None,
        "min_bucket_capture_truth": None,
        "min_bucket_net_bps": None,
        "max_bucket_net_bps": None,
        "convergence_rows": [],
    }


def _convergence_row(index: int, rows: list[sqlite3.Row], first_ts: int, bucket_ms: int) -> ConvergenceRow:
    start_ts = first_ts + index * bucket_ms
    end_ts = start_ts + bucket_ms
    valid = [row for row in rows if int(row["valid"] or 0) == 1]
    notional = sum(abs(int(row["aq_e6"])) for row in valid)
    charged = [row for row in valid if int(row["fresh_premium_pips"] or 0) > 0]
    charged_notional = sum(abs(int(row["aq_e6"])) for row in charged)
    fallback = [
        row
        for row in valid
        if row["fresh_fallback_reason"] is not None and str(row["fresh_fallback_reason"]) != ""
    ]
    fallback_notional = sum(abs(int(row["aq_e6"])) for row in fallback)
    base_fee = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in valid)
    extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged)
    correct_extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged if int(row["truth_corr"] or 0) == 1)
    truth_markout = sum(int(row["truth_mk_e6"] or 0) for row in valid)
    net = base_fee + extra - truth_markout
    return ConvergenceRow(
        bucket_index=index,
        start_ts_ms=start_ts,
        end_ts_ms=end_ts,
        start_offset_hours=(start_ts - first_ts) / 3_600_000,
        end_offset_hours=(end_ts - first_ts) / 3_600_000,
        rows=len(rows),
        valid_rows=len(valid),
        truth_coverage=len(valid) / len(rows) if rows else 0.0,
        notional_e6=notional,
        charged_rows=len(charged),
        charged_notional_e6=charged_notional,
        fallback_rows=len(fallback),
        fallback_notional_e6=fallback_notional,
        fallback_notional_share=(fallback_notional / notional) if notional else None,
        base_fee_e6=base_fee,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        truth_markout_e6=truth_markout,
        precision=(correct_extra / extra) if extra else None,
        capture_truth=(extra / abs(truth_markout)) if truth_markout else None,
        net_e6=net,
        net_bps=_bps(net, notional),
        avg_premium_bps=_bps(extra, charged_notional),
    )


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _min_non_null(values) -> float | None:
    concrete = [float(value) for value in values if value is not None]
    return min(concrete) if concrete else None


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Segment live shadow economics into convergence buckets")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--bucket-sec", type=int, default=DEFAULT_BUCKET_SEC)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "live_convergence_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "live_convergence_report.json")
    args = parser.parse_args()
    report = compute(args.database, args.bucket_sec)
    write_outputs(report, args.out_md, args.out_json)
    print(f"live convergence buckets={report['bucket_count']} complete={report['complete']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
