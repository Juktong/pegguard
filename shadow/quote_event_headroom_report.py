from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import PIPS_DENOM, fixture_events
from .quote_premium_stress_report import QuoteBucket, StressEvent, quote_buckets
from .quote_premium_stress_report import _fixture_event_to_stress, _live_events


@dataclass(frozen=True)
class EventBudget:
    budget_pips: float
    relation: str


@dataclass(frozen=True)
class EventHeadroomRow:
    window: str
    rows: int
    charged_rows: int
    notional_e6: int
    charged_notional_e6: int
    extra_e6: int
    correct_extra_e6: int
    precision: float | None
    retained_extra_e6: int
    excess_e6: int
    excess_share_of_extra: float | None
    over_budget_rows: int
    over_budget_notional_e6: int
    over_budget_notional_share: float | None
    below_min_quote_rows: int
    above_max_quote_rows: int
    avg_budget_bps: float | None
    p50_budget_bps: float | None
    p90_budget_bps: float | None
    max_premium_bps: float
    max_budget_bps: float | None
    max_excess_bps: float


def compute(
    root: Path | None = None,
    live_db: Path | None = None,
    quote_headroom_json: Path | None = None,
) -> dict:
    root = root or C.repo_root()
    live_db = live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3"
    quote_headroom_json = quote_headroom_json or root / "docs" / "quote_headroom_report.json"
    buckets = quote_buckets(_load_json(quote_headroom_json))
    rows = []
    if buckets:
        for window, events in _events_by_window(root, live_db).items():
            rows.append(_window_row(window, events, buckets))
    return {
        "quote_headroom_source": str(quote_headroom_json),
        "model": (
            "per-event routeability stress: interpolate the real QuoterV2 premium "
            "headroom by event notional and count charged premium above that budget as excess."
        ),
        "quote_points": [asdict(bucket) for bucket in buckets],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Event Headroom",
        "",
        "This report applies the real QuoterV2 5 bps route headroom to each swap",
        "event by notional size. The bucketed quote-premium stress report assigns",
        "each event to a quoted size bucket; this report linearly interpolates",
        "between quote points and separately flags below/above-range extrapolation.",
        "It is routeability stress, not controlled route-away evidence.",
        "",
        f"- Source: `{report.get('quote_headroom_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Charged | Extra | Excess | Excess/extra | Over-budget rows | Over-budget notional | Below min quote | Above max quote | Avg budget | p90 budget | Max premium | Precision |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {int(row['charged_rows'])} | {_usd(int(row['extra_e6']))} | "
            f"{_usd(int(row['excess_e6']))} | {_pct(row.get('excess_share_of_extra'))} | "
            f"{int(row['over_budget_rows'])} | {_usd(int(row['over_budget_notional_e6']))} | "
            f"{int(row['below_min_quote_rows'])} | {int(row['above_max_quote_rows'])} | "
            f"{_bps_or_na(row.get('avg_budget_bps'))} | {_bps_or_na(row.get('p90_budget_bps'))} | "
            f"{float(row['max_premium_bps']):.2f} bps | {_pct(row.get('precision'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `excess` is premium above the interpolated quote headroom, not measured lost flow.",
            "- Events above the largest quote reuse the largest quoted budget and are explicitly counted as extrapolated.",
            "- This should be read with `quote_headroom_stability_report.md`; stale quote grids can make the budget too generous or too strict.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def event_budget(event: StressEvent, buckets: list[QuoteBucket]) -> EventBudget:
    if not buckets:
        return EventBudget(0.0, "missing")
    points = sorted(buckets, key=lambda bucket: bucket.quote_notional_e6)
    if event.notional_e6 < points[0].quote_notional_e6:
        return EventBudget(float(points[0].premium_budget_pips), "below_min")
    if event.notional_e6 > points[-1].quote_notional_e6:
        return EventBudget(float(points[-1].premium_budget_pips), "above_max")
    for left, right in zip(points, points[1:]):
        if event.notional_e6 == left.quote_notional_e6:
            return EventBudget(float(left.premium_budget_pips), "interpolated")
        if left.quote_notional_e6 < event.notional_e6 <= right.quote_notional_e6:
            span = right.quote_notional_e6 - left.quote_notional_e6
            if span <= 0:
                return EventBudget(float(right.premium_budget_pips), "interpolated")
            weight = (event.notional_e6 - left.quote_notional_e6) / span
            budget = left.premium_budget_pips + (right.premium_budget_pips - left.premium_budget_pips) * weight
            return EventBudget(max(0.0, budget), "interpolated")
    return EventBudget(float(points[-1].premium_budget_pips), "above_max")


def _window_row(window: str, events: list[StressEvent], buckets: list[QuoteBucket]) -> EventHeadroomRow:
    charged = [event for event in events if event.premium_pips > 0]
    budgets = [event_budget(event, buckets) for event in charged]
    excess_values = [_excess_e6(event, budget.budget_pips) for event, budget in zip(charged, budgets)]
    over_pairs = [
        (event, budget, excess)
        for event, budget, excess in zip(charged, budgets, excess_values)
        if excess > 0
    ]
    notional = sum(event.notional_e6 for event in events)
    charged_notional = sum(event.notional_e6 for event in charged)
    extra = sum(event.extra_e6 for event in charged)
    correct_extra = sum(event.extra_e6 for event in charged if event.truth_corr == 1)
    excess = sum(excess_values)
    budget_bps_values = [budget.budget_pips / 100 for budget in budgets]
    max_excess_bps = max(
        (
            max(0.0, event.premium_pips - budget.budget_pips) / 100
            for event, budget in zip(charged, budgets)
        ),
        default=0.0,
    )
    return EventHeadroomRow(
        window=window,
        rows=len(events),
        charged_rows=len(charged),
        notional_e6=notional,
        charged_notional_e6=charged_notional,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        precision=(correct_extra / extra) if extra else None,
        retained_extra_e6=extra - excess,
        excess_e6=excess,
        excess_share_of_extra=(excess / extra) if extra else None,
        over_budget_rows=len(over_pairs),
        over_budget_notional_e6=sum(event.notional_e6 for event, _, _ in over_pairs),
        over_budget_notional_share=(
            sum(event.notional_e6 for event, _, _ in over_pairs) / charged_notional if charged_notional else None
        ),
        below_min_quote_rows=sum(1 for budget in budgets if budget.relation == "below_min"),
        above_max_quote_rows=sum(1 for budget in budgets if budget.relation == "above_max"),
        avg_budget_bps=(sum(budget_bps_values) / len(budget_bps_values)) if budget_bps_values else None,
        p50_budget_bps=_percentile(budget_bps_values, 0.50),
        p90_budget_bps=_percentile(budget_bps_values, 0.90),
        max_premium_bps=max((event.premium_pips / 100 for event in charged), default=0.0),
        max_budget_bps=max(budget_bps_values) if budget_bps_values else None,
        max_excess_bps=max_excess_bps,
    )


def _events_by_window(root: Path, live_db: Path) -> dict[str, list[StressEvent]]:
    events: dict[str, list[StressEvent]] = {}
    live_events = _live_events(live_db)
    if live_events:
        events["live shadow"] = live_events
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        events[window] = [_fixture_event_to_stress(event) for event in fixture]
    return events


def _excess_e6(event: StressEvent, budget_pips: float) -> int:
    excess_pips = max(0.0, event.premium_pips - budget_pips)
    return int(round(event.notional_e6 * excess_pips / PIPS_DENOM))


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * q))))
    return ordered[index]


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


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Apply real quote headroom to charged events by notional")
    parser.add_argument("--quote-headroom-json", type=Path, default=root / "docs" / "quote_headroom_report.json")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_event_headroom_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_event_headroom_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, args.quote_headroom_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote event headroom rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
