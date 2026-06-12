from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM


DEFAULT_BUCKET_SEC = 60 * 60
TARGET_NET_HALF_WIDTH_BPS = 0.50
TARGET_CAPTURE_HALF_WIDTH = 0.02
TARGET_PRECISION_HALF_WIDTH = 0.01


@dataclass(frozen=True)
class PowerBucket:
    bucket_index: int
    start_offset_hours: float
    end_offset_hours: float
    rows: int
    valid_rows: int
    charged_rows: int
    notional_e6: int
    extra_e6: int
    correct_extra_e6: int
    truth_markout_e6: int
    precision: float | None
    capture_truth: float | None
    net_bps: float


@dataclass(frozen=True)
class PowerMetric:
    metric: str
    current_value: float | None
    bucket_count: int
    bucket_mean: float | None
    bucket_stdev: float | None
    ci95_half_width: float | None
    target_half_width: float
    estimated_required_buckets: int | None
    estimated_required_hours: float | None
    additional_hours_needed: float | None
    status: str


def compute(database: Path | None = None, bucket_sec: int = DEFAULT_BUCKET_SEC) -> dict:
    database = database or C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3"
    if bucket_sec <= 0:
        raise ValueError("bucket_sec must be positive")
    rows = _load_rows(database)
    if not rows:
        return _empty(database, bucket_sec)

    first_ts = int(rows[0]["ts_ms"])
    last_ts = int(rows[-1]["ts_ms"])
    bucket_ms = bucket_sec * 1000
    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        grouped.setdefault((int(row["ts_ms"]) - first_ts) // bucket_ms, []).append(row)
    buckets = [_bucket(index, bucket_rows, first_ts, bucket_ms) for index, bucket_rows in sorted(grouped.items())]

    valid_rows = sum(bucket.valid_rows for bucket in buckets)
    charged_rows = sum(bucket.charged_rows for bucket in buckets)
    notional = sum(bucket.notional_e6 for bucket in buckets)
    extra = sum(bucket.extra_e6 for bucket in buckets)
    correct_extra = sum(bucket.correct_extra_e6 for bucket in buckets)
    truth_markout = sum(bucket.truth_markout_e6 for bucket in buckets)
    base_fee = sum((bucket.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM for bucket in buckets)
    net = base_fee + extra - truth_markout
    observed_hours = max(0.0, (last_ts - first_ts) / 3_600_000)
    metrics = [
        _metric(
            "net_bps",
            _bps(net, notional),
            [bucket.net_bps for bucket in buckets if bucket.valid_rows > 0],
            TARGET_NET_HALF_WIDTH_BPS,
            observed_hours,
            bucket_sec,
        ),
        _metric(
            "capture_truth",
            (extra / abs(truth_markout)) if truth_markout else None,
            [float(bucket.capture_truth) for bucket in buckets if bucket.capture_truth is not None],
            TARGET_CAPTURE_HALF_WIDTH,
            observed_hours,
            bucket_sec,
        ),
        _metric(
            "precision",
            (correct_extra / extra) if extra else None,
            [float(bucket.precision) for bucket in buckets if bucket.precision is not None],
            TARGET_PRECISION_HALF_WIDTH,
            observed_hours,
            bucket_sec,
        ),
    ]
    return {
        "database": str(database),
        "bucket_sec": bucket_sec,
        "complete": len(buckets) >= 2 and valid_rows > 0 and charged_rows > 0,
        "model": (
            "hourly bucket standard error; required-hours estimates assume future buckets have "
            "similar variance and are for evidence planning, not forecasting."
        ),
        "observed_span_hours": observed_hours,
        "bucket_count": len(buckets),
        "rows": len(rows),
        "valid_rows": valid_rows,
        "truth_coverage": valid_rows / len(rows) if rows else 0.0,
        "charged_rows": charged_rows,
        "notional_e6": notional,
        "extra_e6": extra,
        "truth_markout_e6": truth_markout,
        "net_e6": net,
        "net_bps": _bps(net, notional),
        "capture_truth": (extra / abs(truth_markout)) if truth_markout else None,
        "precision": (correct_extra / extra) if extra else None,
        "metrics": [asdict(metric) for metric in metrics],
        "buckets": [asdict(bucket) for bucket in buckets],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Live Sample Power",
        "",
        "This report estimates whether the current live-shadow sample is statistically",
        "stable enough to trust around the hard 24h gate. It uses hourly",
        "truth-backed buckets and reports 95% half-widths plus the estimated hours",
        "needed to reach tighter bands. It is evidence planning, not calibration.",
        "",
        f"- Database: `{report.get('database', 'n/a')}`",
        f"- Bucket size: {int(report.get('bucket_sec', 0))} seconds",
        f"- Status: {'complete' if report.get('complete') else 'in progress'}",
        f"- Observed span: {float(report.get('observed_span_hours', 0)):.2f} hours",
        f"- Buckets: {int(report.get('bucket_count', 0))}",
        f"- Truth coverage: {_pct(report.get('truth_coverage'))}",
        f"- Current precision: {_pct(report.get('precision'))}",
        f"- Current truth capture: {_pct(report.get('capture_truth'))}",
        f"- Current net: {_usd(int(report.get('net_e6', 0)))} ({float(report.get('net_bps', 0)):.2f} bps)",
        "",
        "| Metric | Current | Bucket mean | Bucket stdev | 95% half-width | Target half-width | Required hours | Additional hours | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("metrics", []):
        lines.append(
            f"| {row['metric']} | {_metric_value(row['metric'], row.get('current_value'))} | "
            f"{_metric_value(row['metric'], row.get('bucket_mean'))} | {_metric_value(row['metric'], row.get('bucket_stdev'))} | "
            f"{_metric_value(row['metric'], row.get('ci95_half_width'))} | "
            f"{_metric_value(row['metric'], row.get('target_half_width'))} | "
            f"{_hours(row.get('estimated_required_hours'))} | {_hours(row.get('additional_hours_needed'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `additional hours` can exceed the 24h gate when the observed bucket variance is high.",
            "- Passing this report means the sample is measurable enough for a power estimate; it does not make the 24h gate complete.",
            "- Required-hour estimates assume future hourly buckets resemble the observed bucket distribution.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _load_rows(database: Path) -> list[sqlite3.Row]:
    if not database.exists():
        return []
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """
            SELECT
                l.id,
                l.ts_ms,
                l.aq_e6,
                l.fresh_premium_pips,
                l.fresh_extra_e6,
                t.valid,
                t.truth_corr,
                t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()


def _bucket(index: int, rows: list[sqlite3.Row], first_ts: int, bucket_ms: int) -> PowerBucket:
    valid = [row for row in rows if int(row["valid"] or 0) == 1]
    charged = [row for row in valid if int(row["fresh_premium_pips"] or 0) > 0]
    notional = sum(abs(int(row["aq_e6"])) for row in valid)
    extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged)
    correct_extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged if int(row["truth_corr"] or 0) == 1)
    truth_markout = sum(int(row["truth_mk_e6"] or 0) for row in valid)
    base_fee = (notional * BASE_FEE_PIPS) // PIPS_DENOM
    net = base_fee + extra - truth_markout
    start = first_ts + index * bucket_ms
    end = start + bucket_ms
    return PowerBucket(
        bucket_index=index,
        start_offset_hours=(start - first_ts) / 3_600_000,
        end_offset_hours=(end - first_ts) / 3_600_000,
        rows=len(rows),
        valid_rows=len(valid),
        charged_rows=len(charged),
        notional_e6=notional,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        truth_markout_e6=truth_markout,
        precision=(correct_extra / extra) if extra else None,
        capture_truth=(extra / abs(truth_markout)) if truth_markout else None,
        net_bps=_bps(net, notional),
    )


def _metric(
    name: str,
    current: float | None,
    values: list[float],
    target_half_width: float,
    observed_hours: float,
    bucket_sec: int,
) -> PowerMetric:
    count = len(values)
    mean = sum(values) / count if count else None
    stdev = _stdev(values)
    half_width = 1.96 * stdev / math.sqrt(count) if stdev is not None and count > 0 else None
    required_buckets = None
    required_hours = None
    additional = None
    if stdev is not None and target_half_width > 0:
        required_buckets = max(2, math.ceil((1.96 * stdev / target_half_width) ** 2))
        required_hours = required_buckets * bucket_sec / 3600
        additional = max(0.0, required_hours - observed_hours)
    if half_width is None:
        status = "insufficient buckets"
    elif half_width <= target_half_width:
        status = "target met"
    else:
        status = "needs more live time"
    return PowerMetric(
        metric=name,
        current_value=current,
        bucket_count=count,
        bucket_mean=mean,
        bucket_stdev=stdev,
        ci95_half_width=half_width,
        target_half_width=target_half_width,
        estimated_required_buckets=required_buckets,
        estimated_required_hours=required_hours,
        additional_hours_needed=additional,
        status=status,
    )


def _stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def _empty(database: Path, bucket_sec: int) -> dict:
    return {
        "database": str(database),
        "bucket_sec": bucket_sec,
        "complete": False,
        "model": "hourly bucket standard error",
        "observed_span_hours": 0.0,
        "bucket_count": 0,
        "rows": 0,
        "valid_rows": 0,
        "truth_coverage": 0.0,
        "charged_rows": 0,
        "notional_e6": 0,
        "extra_e6": 0,
        "truth_markout_e6": 0,
        "net_e6": 0,
        "net_bps": 0.0,
        "capture_truth": None,
        "precision": None,
        "metrics": [],
        "buckets": [],
    }


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _metric_value(metric: str, value: object) -> str:
    if value is None:
        return "n/a"
    number = float(value)
    if metric == "net_bps":
        return f"{number:.2f} bps"
    return f"{number:.2%}"


def _hours(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}h"


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Estimate live-shadow sample sufficiency from hourly buckets")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--bucket-sec", type=int, default=DEFAULT_BUCKET_SEC)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "live_power_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "live_power_report.json")
    args = parser.parse_args()
    report = compute(args.database, args.bucket_sec)
    write_outputs(report, args.out_md, args.out_json)
    print(f"live power buckets={report['bucket_count']} complete={report['complete']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
