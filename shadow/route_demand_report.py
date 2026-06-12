from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events


TOLERANCE_BPS = (1.0, 2.0, 5.0, 10.0)


@dataclass(frozen=True)
class DemandEvent:
    t_ms: int
    notional_e6: int
    premium_pips: int
    extra_e6: int
    truth_corr: int
    truth_markout_e6: int


@dataclass(frozen=True)
class DemandRow:
    window: str
    tolerance_bps: float
    rows: int
    routed_rows: int
    retained_rows: int
    notional_e6: int
    routed_notional_e6: int
    retained_notional_e6: int
    extra_e6: int
    lost_extra_e6: int
    retained_extra_e6: int
    retained_correct_extra_e6: int
    markout_e6: int
    avoided_markout_e6: int
    retained_markout_e6: int
    base_fee_e6: int
    retained_base_fee_e6: int
    full_net_e6: int
    net_after_demand_e6: int
    delta_vs_full_e6: int
    routed_notional_share: float | None
    lost_extra_share: float | None
    retained_precision: float | None
    retained_extra_bps: float
    model: str


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[DemandRow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        rows.extend(_rows_for_window("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(_rows_for_window(window, [_fixture_event_to_demand(event) for event in fixture]))
    return {
        "model": (
            "hard route-away demand curve; a swap is assumed to leave the pool when PegGuard premium exceeds "
            "the listed user/router tolerance. Routed swaps lose base fee and premium but also remove their "
            "measured truth markout from LP PnL. This is behavioral stress, not observed routing elasticity."
        ),
        "tolerance_bps": list(TOLERANCE_BPS),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away Demand Curve",
        "",
        "This report models how PegGuard economics change if routers or users leave",
        "once the dynamic premium crosses simple bps tolerances.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Tolerance | Routed notional | Lost premium | Avoided markout | Net after demand | Delta vs full | Retained precision | Retained extra |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {float(row['tolerance_bps']):.1f} bps | "
            f"{_usd(int(row['routed_notional_e6']))} ({_pct(row.get('routed_notional_share'))}) | "
            f"{_usd(int(row['lost_extra_e6']))} ({_pct(row.get('lost_extra_share'))}) | "
            f"{_usd(int(row['avoided_markout_e6']))} | {_usd(int(row['net_after_demand_e6']))} | "
            f"{_usd(int(row['delta_vs_full_e6']))} | {_pct(row.get('retained_precision'))} | "
            f"{float(row['retained_extra_bps']):.2f} bps |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Lower tolerance rows are harsher behavioral assumptions: more charged flow leaves.",
            "- A positive `delta vs full` means the routed-away flow was more harmful than valuable under measured markout.",
            "- A negative `delta vs full` means the premium and base-fee loss outweighed the avoided markout.",
            "- This still does not replace the controlled route-away A/B experiment because the tolerances are modeled, not measured.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def demand_rows(window: str, events: list[DemandEvent], tolerances_bps: tuple[float, ...] = TOLERANCE_BPS) -> list[DemandRow]:
    return [_row(window, events, tolerance) for tolerance in tolerances_bps]


def _rows_for_window(window: str, events: list[DemandEvent]) -> list[DemandRow]:
    return demand_rows(window, events)


def _row(window: str, events: list[DemandEvent], tolerance_bps: float) -> DemandRow:
    threshold_pips = int(round(tolerance_bps * 100))
    routed = [event for event in events if event.premium_pips > threshold_pips]
    retained = [event for event in events if event.premium_pips <= threshold_pips]

    notional = sum(event.notional_e6 for event in events)
    routed_notional = sum(event.notional_e6 for event in routed)
    retained_notional = notional - routed_notional
    extra = sum(event.extra_e6 for event in events)
    lost_extra = sum(event.extra_e6 for event in routed)
    retained_extra = extra - lost_extra
    retained_correct_extra = sum(event.extra_e6 for event in retained if event.truth_corr == 1)
    markout = sum(event.truth_markout_e6 for event in events)
    avoided_markout = sum(event.truth_markout_e6 for event in routed)
    retained_markout = markout - avoided_markout
    base_fee = _fee(notional, BASE_FEE_PIPS)
    retained_base_fee = _fee(retained_notional, BASE_FEE_PIPS)
    full_net = base_fee + extra - markout
    net_after_demand = retained_base_fee + retained_extra - retained_markout
    return DemandRow(
        window=window,
        tolerance_bps=tolerance_bps,
        rows=len(events),
        routed_rows=len(routed),
        retained_rows=len(retained),
        notional_e6=notional,
        routed_notional_e6=routed_notional,
        retained_notional_e6=retained_notional,
        extra_e6=extra,
        lost_extra_e6=lost_extra,
        retained_extra_e6=retained_extra,
        retained_correct_extra_e6=retained_correct_extra,
        markout_e6=markout,
        avoided_markout_e6=avoided_markout,
        retained_markout_e6=retained_markout,
        base_fee_e6=base_fee,
        retained_base_fee_e6=retained_base_fee,
        full_net_e6=full_net,
        net_after_demand_e6=net_after_demand,
        delta_vs_full_e6=net_after_demand - full_net,
        routed_notional_share=(routed_notional / notional) if notional else None,
        lost_extra_share=(lost_extra / extra) if extra else None,
        retained_precision=(retained_correct_extra / retained_extra) if retained_extra else None,
        retained_extra_bps=_bps(retained_extra, retained_notional),
        model="hard threshold: route away when premium exceeds tolerance",
    )


def _fixture_event_to_demand(event) -> DemandEvent:
    return DemandEvent(
        t_ms=event.t_ms,
        notional_e6=event.notional_e6,
        premium_pips=event.peg_premium_pips,
        extra_e6=event.peg_extra_e6,
        truth_corr=event.truth_corr,
        truth_markout_e6=event.truth_markout_e6,
    )


def _live_events(db: Path) -> list[DemandEvent]:
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
    return [
        DemandEvent(
            t_ms=int(row["ts_ms"]),
            notional_e6=abs(int(row["aq_e6"])),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
            truth_markout_e6=int(row["truth_mk_e6"] or 0),
        )
        for row in rows
    ]


def _fee(notional_e6: int, pips: int) -> int:
    return (notional_e6 * pips) // PIPS_DENOM


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
    parser = argparse.ArgumentParser(description="Generate route-away demand-curve stress")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_demand_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_demand_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route demand rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
