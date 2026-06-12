from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, GAS_SCENARIOS, PIPS_DENOM, fixture_events

REGIME_BUCKETS: tuple[tuple[str, float | None, float | None], ...] = (
    ("quiet <1bp", None, 1.0),
    ("normal 1-5bp", 1.0, 5.0),
    ("high-vol >=5bp", 5.0, None),
)


@dataclass(frozen=True)
class RegimeEvent:
    t_ms: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    premium_pips: int
    truth_corr: int
    oracle_lag: bool = False


@dataclass(frozen=True)
class RegimeRow:
    window: str
    segment: str
    rows: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    net_e6: int
    net_bps: float
    capture: float | None
    precision: float | None
    charged_rows: int
    low_l2_gas_bps: float
    low_l2_net_bps: float
    stressed_l2_gas_bps: float
    stressed_l2_net_bps: float
    source: str


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    live_db = live_db or _default_live_db(root)
    rows: list[RegimeRow] = []

    live_events = _live_events(live_db)
    if live_events:
        rows.extend(regime_rows("live shadow", live_events, "live DB truth"))

    for window in ("calm", "vol"):
        fixture, _parity = fixture_events(root, window)
        events = [
            RegimeEvent(
                t_ms=event.t_ms,
                notional_e6=event.notional_e6,
                base_fee_e6=(event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM,
                extra_e6=event.peg_extra_e6,
                markout_e6=event.truth_markout_e6,
                premium_pips=event.peg_premium_pips,
                truth_corr=event.truth_corr,
                oracle_lag=False,
            )
            for event in fixture
        ]
        rows.extend(regime_rows(window, events, "fixture truth"))

    return {
        "complete": _complete(rows),
        "database": str(live_db),
        "regime_buckets": [
            {"label": label, "min_abs_markout_bps": min_bps, "max_abs_markout_bps": max_bps}
            for label, min_bps, max_bps in REGIME_BUCKETS
        ],
        "high_gas_model": "event-level historical gas is not available; high-gas is modeled with the existing stressed L2 gas scenario",
        "gas_scenarios": {
            "low_l2": _scenario_name("low"),
            "stressed_l2": _scenario_name("stressed"),
        },
        "rows": [asdict(row) for row in rows],
    }


def regime_rows(window: str, events: list[RegimeEvent], source: str) -> list[RegimeRow]:
    rows = [_row(window, "all", events, source)]
    for label, min_bps, max_bps in REGIME_BUCKETS:
        rows.append(_row(window, label, [event for event in events if _in_markout_bucket(event, min_bps, max_bps)], source))
    rows.append(_row(window, "oracle-lag/fallback", [event for event in events if event.oracle_lag], source if window == "live shadow" else "not measured in fixture"))
    return rows


def markdown(report: dict) -> str:
    lines = [
        "# Market-Regime Segments",
        "",
        "This report segments economic performance by realized event markout intensity",
        "and live oracle-lag/fallback rows. It also overlays low-L2 and stressed-L2",
        "gas costs on each segment. Historical per-event gas is not available, so the",
        "high-gas view is a scenario overlay, not an event classifier.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Live database: `{report.get('database', 'n/a')}`",
        f"- High-gas model: {report.get('high_gas_model', 'n/a')}",
        "",
        "| Window | Segment | Rows | Notional | Extra | Markout | Net | Net bps | Capture | Precision | Charged rows | Low L2 gas bps | Low L2 net bps | Stressed L2 gas bps | Stressed L2 net bps | Source |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['segment']} | {int(row['rows'])} | {_usd(int(row['notional_e6']))} | "
            f"{_usd(int(row['extra_e6']))} | {_usd(int(row['markout_e6']))} | {_usd(int(row['net_e6']))} | "
            f"{float(row['net_bps']):.2f} | {_pct(row.get('capture'))} | {_pct(row.get('precision'))} | "
            f"{int(row['charged_rows'])} | {float(row['low_l2_gas_bps']):.4f} | {float(row['low_l2_net_bps']):.2f} | "
            f"{float(row['stressed_l2_gas_bps']):.4f} | {float(row['stressed_l2_net_bps']):.2f} | {row['source']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Markout regimes use absolute truth markout bps per event: quiet `<1bp`, normal `1-5bp`, high-vol `>=5bp`.",
            "- Oracle-lag/fallback is measured only for live shadow because fixtures do not contain hot-path oracle freshness fields.",
            "- Gas overlays reuse the economic-suite gas scenarios; they are cost stress tests, not claims about historical gas at each swap.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(window: str, segment: str, events: list[RegimeEvent], source: str) -> RegimeRow:
    rows = len(events)
    notional = sum(event.notional_e6 for event in events)
    base = sum(event.base_fee_e6 for event in events)
    extra = sum(event.extra_e6 for event in events)
    markout = sum(event.markout_e6 for event in events)
    net = base + extra - markout
    charged = [event for event in events if event.premium_pips > 0]
    premium_total = sum(event.extra_e6 for event in charged)
    premium_correct = sum(event.extra_e6 for event in charged if event.truth_corr == 1)
    low_gas = _gas_bps("low", rows, notional)
    stressed_gas = _gas_bps("stressed", rows, notional)
    return RegimeRow(
        window=window,
        segment=segment,
        rows=rows,
        notional_e6=notional,
        base_fee_e6=base,
        extra_e6=extra,
        markout_e6=markout,
        net_e6=net,
        net_bps=_bps(net, notional),
        capture=(extra / abs(markout)) if markout else None,
        precision=(premium_correct / premium_total) if premium_total else None,
        charged_rows=len(charged),
        low_l2_gas_bps=low_gas,
        low_l2_net_bps=_bps(net, notional) - low_gas,
        stressed_l2_gas_bps=stressed_gas,
        stressed_l2_net_bps=_bps(net, notional) - stressed_gas,
        source=source,
    )


def _live_events(db: Path) -> list[RegimeEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips,
                   l.fresh_fallback_reason, l.oracle_staleness_observed_ms,
                   t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()

    events: list[RegimeEvent] = []
    for row in rows:
        notional = abs(int(row["aq_e6"]))
        fallback = str(row["fresh_fallback_reason"] or "")
        staleness = row["oracle_staleness_observed_ms"]
        oracle_lag = bool(fallback) or staleness is None or int(staleness) > 5_000
        events.append(
            RegimeEvent(
                t_ms=int(row["ts_ms"]),
                notional_e6=notional,
                base_fee_e6=(notional * BASE_FEE_PIPS) // PIPS_DENOM,
                extra_e6=int(row["fresh_extra_e6"] or 0),
                markout_e6=int(row["truth_mk_e6"] or 0),
                premium_pips=int(row["fresh_premium_pips"] or 0),
                truth_corr=int(row["truth_corr"] or 0),
                oracle_lag=oracle_lag,
            )
        )
    return events


def _in_markout_bucket(event: RegimeEvent, min_bps: float | None, max_bps: float | None) -> bool:
    value = abs(_bps(event.markout_e6, event.notional_e6))
    return (min_bps is None or value >= min_bps) and (max_bps is None or value < max_bps)


def _scenario_name(kind: str) -> str:
    scenario = _scenario(kind)
    return scenario.name if scenario else "n/a"


def _scenario(kind: str):
    needle = "hook + Pyth, stressed L2" if kind == "stressed" else "hook + Pyth, low L2"
    return next((scenario for scenario in GAS_SCENARIOS if needle in scenario.name), None)


def _gas_bps(kind: str, swaps: int, notional_e6: int) -> float:
    scenario = _scenario(kind)
    if scenario is None or notional_e6 <= 0 or swaps <= 0:
        return 0.0
    gas = swaps * (scenario.hook_gas + scenario.pyth_update_gas)
    cost_e6 = int(round(gas * scenario.gas_price_gwei * 1e-9 * scenario.eth_usd * 1_000_000))
    return _bps(cost_e6, notional_e6)


def _complete(rows: list[RegimeRow]) -> bool:
    windows = {row.window for row in rows}
    required_windows = {"calm", "vol"}
    if not required_windows.issubset(windows):
        return False
    for window in required_windows:
        labels = {row.segment for row in rows if row.window == window and row.rows > 0}
        if not {"all", "quiet <1bp", "normal 1-5bp", "high-vol >=5bp"}.issubset(labels):
            return False
    live_rows = [row for row in rows if row.window == "live shadow"]
    if live_rows and not any(row.segment == "oracle-lag/fallback" and row.rows > 0 for row in live_rows):
        return False
    return all(row.low_l2_gas_bps >= 0 and row.stressed_l2_gas_bps >= 0 for row in rows)


def _default_live_db(root: Path) -> Path:
    primary = root / "shadow" / "live_shadow_20260607T082122Z.sqlite3"
    if primary.exists():
        return primary
    return root / "shadow" / "shadow.sqlite3"


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
    parser = argparse.ArgumentParser(description="Segment PegGuard economics by market regime and gas stress")
    parser.add_argument("--live-db", type=Path, default=_default_live_db(root))
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "market_regime_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "market_regime_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"market regime rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
