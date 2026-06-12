from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events

BUCKETS: tuple[tuple[str, int | None, int | None], ...] = (
    ("<$1k", None, 1_000_000_000),
    ("$1k-$10k", 1_000_000_000, 10_000_000_000),
    ("$10k-$50k", 10_000_000_000, 50_000_000_000),
    (">=$50k", 50_000_000_000, None),
)


@dataclass(frozen=True)
class BucketEvent:
    t_ms: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    premium_total_e6: int
    premium_correct_e6: int


@dataclass(frozen=True)
class BucketRow:
    window: str
    bucket: str
    rows: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    net_e6: int
    net_bps: float
    extra_bps: float
    markout_bps: float
    precision: float | None
    capture: float | None
    positive_row_share: float


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[BucketRow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(bucket_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(bucket_rows(window, [_fixture_event_to_bucket(event) for event in fixture]))
    return {
        "buckets": [{"label": label, "min_e6": min_e6, "max_e6": max_e6} for label, min_e6, max_e6 in BUCKETS],
        "rows": [asdict(row) for row in rows],
    }


def bucket_rows(window: str, events: list[BucketEvent]) -> list[BucketRow]:
    rows = []
    for label, min_e6, max_e6 in BUCKETS:
        bucket_events = [
            event
            for event in events
            if (min_e6 is None or event.notional_e6 >= min_e6)
            and (max_e6 is None or event.notional_e6 < max_e6)
        ]
        rows.append(_bucket_row(window, label, bucket_events))
    return rows


def markdown(report: dict) -> str:
    lines = [
        "# Trade-Size Buckets",
        "",
        "This report segments measured economics by quote-notional trade size. It",
        "checks whether precision, capture, and net PnL survive outside the aggregate",
        "average.",
        "",
        "| Window | Bucket | Rows | Notional | Base | Extra | Markout | Net | Net bps | Extra bps | Markout bps | Precision | Capture | Positive rows |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['bucket']} | {int(row['rows'])} | {_usd(int(row['notional_e6']))} | "
            f"{_usd(int(row['base_fee_e6']))} | {_usd(int(row['extra_e6']))} | {_usd(int(row['markout_e6']))} | "
            f"{_usd(int(row['net_e6']))} | {float(row['net_bps']):.2f} | {float(row['extra_bps']):.2f} | "
            f"{float(row['markout_bps']):.2f} | {_pct(row.get('precision'))} | {_pct(row.get('capture'))} | "
            f"{float(row['positive_row_share']):.2%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Buckets use absolute quote notional, so they are comparable across fixtures and live shadow.",
            "- Empty buckets remain in the table to make missing size coverage visible.",
            "- Precision is premium-weighted and only defined for buckets with charged premium.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _bucket_row(window: str, bucket: str, events: list[BucketEvent]) -> BucketRow:
    rows = len(events)
    notional = sum(event.notional_e6 for event in events)
    base = sum(event.base_fee_e6 for event in events)
    extra = sum(event.extra_e6 for event in events)
    markout = sum(event.markout_e6 for event in events)
    net = base + extra - markout
    premium_total = sum(event.premium_total_e6 for event in events)
    premium_correct = sum(event.premium_correct_e6 for event in events)
    return BucketRow(
        window=window,
        bucket=bucket,
        rows=rows,
        notional_e6=notional,
        base_fee_e6=base,
        extra_e6=extra,
        markout_e6=markout,
        net_e6=net,
        net_bps=_bps(net, notional),
        extra_bps=_bps(extra, notional),
        markout_bps=_bps(markout, notional),
        precision=(premium_correct / premium_total) if premium_total else None,
        capture=(extra / abs(markout)) if markout else None,
        positive_row_share=(sum(1 for event in events if event.base_fee_e6 + event.extra_e6 - event.markout_e6 >= 0) / rows) if rows else 0.0,
    )


def _fixture_event_to_bucket(event) -> BucketEvent:
    base = (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
    premium_total = event.peg_extra_e6 if event.peg_premium_pips > 0 else 0
    premium_correct = premium_total if event.truth_corr == 1 else 0
    return BucketEvent(event.t_ms, event.notional_e6, base, event.peg_extra_e6, event.truth_markout_e6, premium_total, premium_correct)


def _live_events(db: Path) -> list[BucketEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    events = []
    for row in rows:
        notional = abs(int(row["aq_e6"]))
        base = (notional * BASE_FEE_PIPS) // PIPS_DENOM
        extra = int(row["fresh_extra_e6"] or 0)
        premium_total = extra if int(row["fresh_premium_pips"] or 0) > 0 else 0
        premium_correct = premium_total if int(row["truth_corr"] or 0) == 1 else 0
        events.append(BucketEvent(int(row["ts_ms"]), notional, base, extra, int(row["truth_mk_e6"] or 0), premium_total, premium_correct))
    return events


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Segment PegGuard economics by trade-size bucket")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "size_bucket_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "size_bucket_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"size buckets rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
