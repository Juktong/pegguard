from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events

ROUTE_AWAY_RATES = (0.10, 0.25, 0.50, 0.75)


@dataclass(frozen=True)
class FlowEvent:
    t_ms: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int

    @property
    def net_e6(self) -> int:
        return self.base_fee_e6 + self.extra_e6 - self.markout_e6

    @property
    def charged(self) -> bool:
        return self.extra_e6 > 0


@dataclass(frozen=True)
class AdverseRow:
    window: str
    route_away: float
    rows: int
    removed_rows: int
    total_notional_e6: int
    charged_notional_e6: int
    removed_notional_e6: int
    realized_notional_e6: int
    full_net_e6: int
    uniform_net_e6: int
    adverse_net_e6: int
    uniform_net_bps_original: float
    adverse_net_bps_original: float
    adverse_net_bps_realized: float
    adverse_gap_bps: float


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[AdverseRow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(adverse_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(adverse_rows(window, [_fixture_event_to_flow(event) for event in fixture]))
    return {
        "model": "charged-flow route-away where the highest LP-net charged swaps leave first; uniform removal is shown as the comparison case",
        "route_away_rates": list(ROUTE_AWAY_RATES),
        "rows": [asdict(row) for row in rows],
    }


def adverse_rows(window: str, events: list[FlowEvent], route_away_rates: tuple[float, ...] = ROUTE_AWAY_RATES) -> list[AdverseRow]:
    return [_adverse_row(window, events, rate) for rate in route_away_rates]


def markdown(report: dict) -> str:
    lines = [
        "# Adverse Route-Away Stress",
        "",
        "This report stresses the route-away model by assuming the best LP-net",
        "charged swaps leave first. It is intentionally harsher than uniform",
        "charged-flow removal and is not a measured elasticity result.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Route-away | Removed notional | Realized notional | Full net | Uniform net | Adverse net | Uniform net bps | Adverse net bps | Realized adverse bps | Adverse gap | Removed rows |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {float(row['route_away']):.0%} | {_usd(int(row['removed_notional_e6']))} | "
            f"{_usd(int(row['realized_notional_e6']))} | {_usd(int(row['full_net_e6']))} | "
            f"{_usd(int(row['uniform_net_e6']))} | {_usd(int(row['adverse_net_e6']))} | "
            f"{float(row['uniform_net_bps_original']):.2f} | {float(row['adverse_net_bps_original']):.2f} | "
            f"{float(row['adverse_net_bps_realized']):.2f} | {float(row['adverse_gap_bps']):.2f} | "
            f"{int(row['removed_rows'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `uniform net` removes the same fraction of aggregate charged base, premium, and markout.",
            "- `adverse net` removes charged events ordered by LP net bps descending, so the most profitable charged flow disappears first.",
            "- A negative `adverse gap` shows how much the benign-flow-leaves-first assumption hurts versus uniform charged-flow removal.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _adverse_row(window: str, events: list[FlowEvent], route_away: float) -> AdverseRow:
    totals = _sum_events(events)
    charged = [event for event in events if event.charged]
    charged_totals = _sum_events(charged)
    target_removed = int(charged_totals["notional_e6"] * route_away)
    removed = _remove_best_flow_first(charged, target_removed)
    uniform_removed = {key: int(charged_totals[key] * route_away) for key in charged_totals}

    uniform_net = _net(totals) - _net(uniform_removed)
    adverse_net = _net(totals) - _net(removed)
    realized_notional = totals["notional_e6"] - removed["notional_e6"]
    return AdverseRow(
        window=window,
        route_away=route_away,
        rows=len(events),
        removed_rows=int(removed["rows"]),
        total_notional_e6=totals["notional_e6"],
        charged_notional_e6=charged_totals["notional_e6"],
        removed_notional_e6=removed["notional_e6"],
        realized_notional_e6=realized_notional,
        full_net_e6=_net(totals),
        uniform_net_e6=uniform_net,
        adverse_net_e6=adverse_net,
        uniform_net_bps_original=_bps(uniform_net, totals["notional_e6"]),
        adverse_net_bps_original=_bps(adverse_net, totals["notional_e6"]),
        adverse_net_bps_realized=_bps(adverse_net, realized_notional),
        adverse_gap_bps=_bps(adverse_net - uniform_net, totals["notional_e6"]),
    )


def _remove_best_flow_first(events: list[FlowEvent], target_notional_e6: int) -> dict[str, int]:
    remaining = target_notional_e6
    removed = {"rows": 0, "notional_e6": 0, "base_fee_e6": 0, "extra_e6": 0, "markout_e6": 0}
    ordered = sorted(events, key=lambda event: _bps(event.net_e6, event.notional_e6), reverse=True)
    for event in ordered:
        if remaining <= 0:
            break
        take = min(event.notional_e6, remaining)
        if take <= 0:
            continue
        removed["rows"] += 1
        removed["notional_e6"] += take
        removed["base_fee_e6"] += _pro_rata(event.base_fee_e6, take, event.notional_e6)
        removed["extra_e6"] += _pro_rata(event.extra_e6, take, event.notional_e6)
        removed["markout_e6"] += _pro_rata(event.markout_e6, take, event.notional_e6)
        remaining -= take
    return removed


def _sum_events(events: list[FlowEvent]) -> dict[str, int]:
    return {
        "rows": len(events),
        "notional_e6": sum(event.notional_e6 for event in events),
        "base_fee_e6": sum(event.base_fee_e6 for event in events),
        "extra_e6": sum(event.extra_e6 for event in events),
        "markout_e6": sum(event.markout_e6 for event in events),
    }


def _fixture_event_to_flow(event) -> FlowEvent:
    base = (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
    return FlowEvent(event.t_ms, event.notional_e6, base, event.peg_extra_e6, event.truth_markout_e6)


def _live_events(db: Path) -> list[FlowEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, t.truth_mk_e6
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
        events.append(FlowEvent(int(row["ts_ms"]), notional, base, int(row["fresh_extra_e6"] or 0), int(row["truth_mk_e6"] or 0)))
    return events


def _net(values: dict[str, int]) -> int:
    return int(values.get("base_fee_e6", 0)) + int(values.get("extra_e6", 0)) - int(values.get("markout_e6", 0))


def _pro_rata(value: int, take: int, notional: int) -> int:
    if notional <= 0:
        return 0
    return (value * take) // notional


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Stress route-away against adverse flow selection")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "adverse_route_away_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "adverse_route_away_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"adverse route-away rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
