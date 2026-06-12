from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events
from .quote_premium_stress_report import QuoteBucket, StressEvent, quote_buckets, stress_rows
from .quote_premium_stress_report import _fixture_event_to_stress, _live_events


BUDGET_MARGINS = (1.00, 0.50, 0.25, 0.10)


@dataclass(frozen=True)
class ElasticityRow:
    window: str
    budget_margin: float
    rows: int
    charged_rows: int
    charged_notional_e6: int
    extra_e6: int
    correct_extra_e6: int
    precision: float | None
    lost_extra_e6: int
    retained_extra_e6: int
    lost_share_of_extra: float | None
    over_budget_rows: int
    over_budget_notional_e6: int
    over_budget_notional_share: float | None
    max_bucket_budget_bps: float
    model: str


def compute(
    root: Path | None = None,
    live_db: Path | None = None,
    quote_headroom_json: Path | None = None,
    margins: tuple[float, ...] = BUDGET_MARGINS,
) -> dict:
    root = root or C.repo_root()
    quote_headroom_json = quote_headroom_json or root / "docs" / "quote_headroom_report.json"
    source_buckets = quote_buckets(_load_json(quote_headroom_json))
    rows: list[ElasticityRow] = []
    if source_buckets:
        events_by_window = _events_by_window(root, live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
        for margin in margins:
            buckets = _scaled_buckets(source_buckets, margin)
            for window, events in events_by_window.items():
                rows.append(_aggregate(window, margin, stress_rows(window, events, buckets), buckets))
    return {
        "quote_headroom_source": str(quote_headroom_json),
        "model": (
            "route-away elasticity stress tied to real quote headroom; each margin treats only the stated fraction "
            "of measured headroom as routeable premium budget and counts premium above that budget as lost."
        ),
        "budget_margins": list(margins),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote-Headroom Route Elasticity",
        "",
        "This report ties route-away stress to the real QuoterV2 headroom grid.",
        "Instead of assuming every measured headroom bp is routeable, it tests",
        "100%, 50%, 25%, and 10% budget margins and treats premium above the",
        "margin-adjusted budget as lost.",
        "",
        f"- Source: `{report.get('quote_headroom_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Headroom budget | Charged | Extra | Lost premium | Lost share | Retained extra | Over-budget rows | Over-budget notional | Precision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {float(row['budget_margin']):.0%} | {int(row['charged_rows'])} | "
            f"{_usd(int(row['extra_e6']))} | {_usd(int(row['lost_extra_e6']))} | "
            f"{_pct(row.get('lost_share_of_extra'))} | {_usd(int(row['retained_extra_e6']))} | "
            f"{int(row['over_budget_rows'])} | {_usd(int(row['over_budget_notional_e6']))} | "
            f"{_pct(row.get('precision'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The 100% budget row should match the existing quote-premium stress result.",
            "- Smaller margins model routers or users leaving before PegGuard consumes the full quoted headroom.",
            "- `Lost premium` is only premium above the margin-adjusted quote budget; this is still not a controlled route-away experiment.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _events_by_window(root: Path, live_db: Path) -> dict[str, list[StressEvent]]:
    events: dict[str, list[StressEvent]] = {}
    live_events = _live_events(live_db)
    if live_events:
        events["live shadow"] = live_events
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        events[window] = [_fixture_event_to_stress(event) for event in fixture]
    return events


def _scaled_buckets(buckets: list[QuoteBucket], margin: float) -> list[QuoteBucket]:
    scaled = []
    for bucket in buckets:
        budget = max(0, int(round(bucket.premium_budget_pips * margin)))
        headroom = None if bucket.premium_headroom_bps is None else max(0.0, float(bucket.premium_headroom_bps) * margin)
        scaled.append(
            QuoteBucket(
                label=bucket.label,
                amount_in_raw=bucket.amount_in_raw,
                quote_notional_e6=bucket.quote_notional_e6,
                premium_headroom_bps=headroom,
                premium_budget_pips=budget,
                route_status=bucket.route_status,
            )
        )
    return scaled


def _aggregate(window: str, margin: float, bucket_rows: list[object], buckets: list[QuoteBucket]) -> ElasticityRow:
    rows = sum(int(row.rows) for row in bucket_rows)
    charged_rows = sum(int(row.charged_rows) for row in bucket_rows)
    charged_notional = sum(int(row.charged_notional_e6) for row in bucket_rows)
    extra = sum(int(row.extra_e6) for row in bucket_rows)
    correct_extra = sum(int(row.correct_extra_e6) for row in bucket_rows)
    lost = sum(int(row.excess_e6) for row in bucket_rows)
    over_rows = sum(int(row.over_headroom_rows) for row in bucket_rows)
    over_notional = sum(int(row.over_headroom_notional_e6) for row in bucket_rows)
    return ElasticityRow(
        window=window,
        budget_margin=margin,
        rows=rows,
        charged_rows=charged_rows,
        charged_notional_e6=charged_notional,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        precision=(correct_extra / extra) if extra else None,
        lost_extra_e6=lost,
        retained_extra_e6=extra - lost,
        lost_share_of_extra=(lost / extra) if extra else None,
        over_budget_rows=over_rows,
        over_budget_notional_e6=over_notional,
        over_budget_notional_share=(over_notional / charged_notional) if charged_notional else None,
        max_bucket_budget_bps=max((bucket.premium_budget_pips / 100 for bucket in buckets), default=0.0),
        model="premium above margin-adjusted quote headroom is lost",
    )


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Stress route-away against margin-adjusted real quote headroom")
    parser.add_argument("--quote-headroom-json", type=Path, default=root / "docs" / "quote_headroom_report.json")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_elasticity_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_elasticity_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, args.quote_headroom_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote elasticity rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
