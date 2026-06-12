from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import PIPS_DENOM, fixture_events


@dataclass(frozen=True)
class QuoteBucket:
    label: str
    amount_in_raw: int
    quote_notional_e6: int
    premium_headroom_bps: float | None
    premium_budget_pips: int
    route_status: str


@dataclass(frozen=True)
class StressEvent:
    t_ms: int
    notional_e6: int
    premium_pips: int
    extra_e6: int
    truth_corr: int


@dataclass(frozen=True)
class StressRow:
    window: str
    bucket: str
    quote_amount_in_raw: int
    quote_notional_e6: int
    premium_headroom_bps: float | None
    premium_budget_pips: int
    route_status: str
    rows: int
    charged_rows: int
    notional_e6: int
    charged_notional_e6: int
    over_quote_max_rows: int
    extra_e6: int
    correct_extra_e6: int
    precision: float | None
    avg_premium_bps: float
    over_headroom_rows: int
    over_headroom_notional_e6: int
    over_headroom_extra_e6: int
    excess_e6: int
    excess_bps_of_charged_notional: float
    excess_share_of_extra: float | None
    over_headroom_premium_share: float | None


def compute(root: Path | None = None, live_db: Path | None = None, quote_headroom_json: Path | None = None) -> dict:
    root = root or C.repo_root()
    quote_headroom_json = quote_headroom_json or root / "docs" / "quote_headroom_report.json"
    quote_headroom = _load_json(quote_headroom_json)
    buckets = quote_buckets(quote_headroom)
    rows: list[StressRow] = []
    if buckets:
        live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
        if live_events:
            rows.extend(stress_rows("live shadow", live_events, buckets))
        for window in ("calm", "vol"):
            fixture, _ = fixture_events(root, window)
            rows.extend(stress_rows(window, [_fixture_event_to_stress(event) for event in fixture], buckets))
    return {
        "quote_headroom_source": str(quote_headroom_json),
        "model": "bucket charged PegGuard premiums by real QuoterV2 5 bps route headroom; excess is premium above the measured routeability budget",
        "buckets": [asdict(bucket) for bucket in buckets],
        "rows": [asdict(row) for row in rows],
    }


def quote_buckets(report: dict) -> list[QuoteBucket]:
    rows = []
    for row in report.get("rows", []):
        quote_notional = _quote_notional(row)
        if quote_notional <= 0:
            continue
        headroom = row.get("premium_headroom_bps")
        headroom_bps = None if headroom is None else float(headroom)
        budget_pips = row.get("premium_headroom_pips")
        if budget_pips is None and headroom_bps is not None:
            budget_pips = int(round(headroom_bps * 100))
        rows.append(
            QuoteBucket(
                label="",
                amount_in_raw=int(row.get("amount_in_raw", 0)),
                quote_notional_e6=quote_notional,
                premium_headroom_bps=headroom_bps,
                premium_budget_pips=max(0, int(budget_pips or 0)),
                route_status=str(row.get("status", "n/a")),
            )
        )
    rows.sort(key=lambda bucket: bucket.quote_notional_e6)
    return [
        QuoteBucket(
            label=f"<= {_usd(bucket.quote_notional_e6)} quote",
            amount_in_raw=bucket.amount_in_raw,
            quote_notional_e6=bucket.quote_notional_e6,
            premium_headroom_bps=bucket.premium_headroom_bps,
            premium_budget_pips=bucket.premium_budget_pips,
            route_status=bucket.route_status,
        )
        for bucket in rows
    ]


def stress_rows(window: str, events: list[StressEvent], buckets: list[QuoteBucket]) -> list[StressRow]:
    by_bucket: dict[str, list[StressEvent]] = {bucket.label: [] for bucket in buckets}
    for event in events:
        bucket = _bucket_for_event(event, buckets)
        by_bucket[bucket.label].append(event)
    return [_stress_row(window, bucket, by_bucket[bucket.label]) for bucket in buckets]


def markdown(report: dict) -> str:
    lines = [
        "# Quote Premium Stress",
        "",
        "This report compares actual charged PegGuard premiums against the real",
        "QuoterV2 premium headroom measured for the configured WETH/USDC 5 bps route.",
        "It is routeability stress, not controlled route-away evidence.",
        "",
        f"- Source: `{report.get('quote_headroom_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Quote bucket | Headroom | Budget | Rows | Charged | Over quote max | Extra | Excess | Excess/extra | Events over budget | Avg premium | Precision |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['bucket']} | {_bps_or_na(row.get('premium_headroom_bps'))} | "
            f"{int(row['premium_budget_pips']) / 100:.2f} bps | {int(row['rows'])} | {int(row['charged_rows'])} | "
            f"{int(row['over_quote_max_rows'])} | {_usd(int(row['extra_e6']))} | {_usd(int(row['excess_e6']))} | "
            f"{_pct(row.get('excess_share_of_extra'))} | {int(row['over_headroom_rows'])} | "
            f"{float(row['avg_premium_bps']):.2f} bps | {_pct(row.get('precision'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Negative quoted headroom is treated as a zero premium budget for excess calculations, while the negative value remains visible in the table.",
            "- `excess` is the portion of dynamic premium above the quote bucket's measured headroom; it is a stress indicator, not lost revenue by itself.",
            "- `over quote max` means the event was larger than the biggest quoted exact-input size and is assigned to the largest bucket, so those rows are extrapolated.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _stress_row(window: str, bucket: QuoteBucket, events: list[StressEvent]) -> StressRow:
    charged = [event for event in events if event.premium_pips > 0]
    over = [event for event in charged if event.premium_pips > bucket.premium_budget_pips]
    notional = sum(event.notional_e6 for event in events)
    charged_notional = sum(event.notional_e6 for event in charged)
    extra = sum(event.extra_e6 for event in charged)
    correct_extra = sum(event.extra_e6 for event in charged if event.truth_corr == 1)
    over_extra = sum(event.extra_e6 for event in over)
    over_notional = sum(event.notional_e6 for event in over)
    excess = sum(_excess_e6(event, bucket.premium_budget_pips) for event in over)
    return StressRow(
        window=window,
        bucket=bucket.label,
        quote_amount_in_raw=bucket.amount_in_raw,
        quote_notional_e6=bucket.quote_notional_e6,
        premium_headroom_bps=bucket.premium_headroom_bps,
        premium_budget_pips=bucket.premium_budget_pips,
        route_status=bucket.route_status,
        rows=len(events),
        charged_rows=len(charged),
        notional_e6=notional,
        charged_notional_e6=charged_notional,
        over_quote_max_rows=sum(1 for event in events if event.notional_e6 > bucket.quote_notional_e6),
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        precision=(correct_extra / extra) if extra else None,
        avg_premium_bps=_bps(extra, charged_notional),
        over_headroom_rows=len(over),
        over_headroom_notional_e6=over_notional,
        over_headroom_extra_e6=over_extra,
        excess_e6=excess,
        excess_bps_of_charged_notional=_bps(excess, charged_notional),
        excess_share_of_extra=(excess / extra) if extra else None,
        over_headroom_premium_share=(over_extra / extra) if extra else None,
    )


def _fixture_event_to_stress(event) -> StressEvent:
    return StressEvent(
        t_ms=event.t_ms,
        notional_e6=event.notional_e6,
        premium_pips=event.peg_premium_pips,
        extra_e6=event.peg_extra_e6,
        truth_corr=event.truth_corr,
    )


def _live_events(db: Path) -> list[StressEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        StressEvent(
            t_ms=int(row["ts_ms"]),
            notional_e6=abs(int(row["aq_e6"])),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
        )
        for row in rows
    ]


def _bucket_for_event(event: StressEvent, buckets: list[QuoteBucket]) -> QuoteBucket:
    for bucket in buckets:
        if event.notional_e6 <= bucket.quote_notional_e6:
            return bucket
    return buckets[-1]


def _quote_notional(row: dict) -> int:
    for key in ("peg_amount_out_raw", "best_amount_out_raw", "limiting_amount_out_raw"):
        value = row.get(key)
        if value is not None:
            return int(value)
    return 0


def _excess_e6(event: StressEvent, budget_pips: int) -> int:
    excess_pips = max(0, event.premium_pips - budget_pips)
    return (event.notional_e6 * excess_pips) // PIPS_DENOM


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Stress charged PegGuard premiums against real quote headroom")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--quote-headroom-json", type=Path, default=root / "docs" / "quote_headroom_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_premium_stress.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_premium_stress.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, args.quote_headroom_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote premium stress rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
