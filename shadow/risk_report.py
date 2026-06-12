from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events


@dataclass(frozen=True)
class RiskEvent:
    t_ms: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    net_e6: int


@dataclass(frozen=True)
class WindowRisk:
    window: str
    rows: int
    notional_e6: int
    net_e6: int
    net_bps: float
    positive_row_share: float
    loss_rows: int
    gross_loss_e6: int
    worst_event_e6: int
    p10_net_e6: int
    p50_net_e6: int
    p90_net_e6: int
    max_drawdown_e6: int
    top_1pct_loss_share: float
    top_5_loss_share: float
    top_1pct_abs_markout_share: float


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    windows: list[WindowRisk] = []
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        windows.append(risk_for_events(window, [_fixture_event_to_risk(event) for event in fixture]))
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        windows.insert(0, risk_for_events("live shadow", live_events))
    return {"windows": [asdict(row) for row in windows]}


def risk_for_events(window: str, events: list[RiskEvent]) -> WindowRisk:
    rows = len(events)
    notional = sum(event.notional_e6 for event in events)
    net_values = [event.net_e6 for event in events]
    gross_loss = sum(-value for value in net_values if value < 0)
    losses = sorted((-value for value in net_values if value < 0), reverse=True)
    abs_markouts = sorted((abs(event.markout_e6) for event in events), reverse=True)
    total_abs_markout = sum(abs_markouts)
    top_1pct_count = max(1, rows // 100) if rows else 0
    return WindowRisk(
        window=window,
        rows=rows,
        notional_e6=notional,
        net_e6=sum(net_values),
        net_bps=_bps(sum(net_values), notional),
        positive_row_share=(sum(1 for value in net_values if value >= 0) / rows) if rows else 0.0,
        loss_rows=sum(1 for value in net_values if value < 0),
        gross_loss_e6=gross_loss,
        worst_event_e6=min(net_values) if net_values else 0,
        p10_net_e6=_pctl(net_values, 10),
        p50_net_e6=_pctl(net_values, 50),
        p90_net_e6=_pctl(net_values, 90),
        max_drawdown_e6=_max_drawdown(net_values),
        top_1pct_loss_share=(sum(losses[:top_1pct_count]) / gross_loss) if gross_loss and top_1pct_count else 0.0,
        top_5_loss_share=(sum(losses[:5]) / gross_loss) if gross_loss else 0.0,
        top_1pct_abs_markout_share=(sum(abs_markouts[:top_1pct_count]) / total_abs_markout) if total_abs_markout and top_1pct_count else 0.0,
    )


def markdown(data: dict) -> str:
    lines = [
        "# Tail Risk And Concentration",
        "",
        "This report checks whether measured economics are broad-based or dominated",
        "by a few adverse swaps. Net PnL is base fee plus PegGuard extra premium",
        "minus truth markout.",
        "",
        "| Window | Rows | Notional | Net | Net bps | Positive rows | Loss rows | Gross loss | Worst event | Max drawdown | Top 1% loss share | Top 1% markout share |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in data["windows"]:
        lines.append(
            f"| {row['window']} | {row['rows']} | {_usd(row['notional_e6'])} | {_usd(row['net_e6'])} | "
            f"{row['net_bps']:.2f} | {row['positive_row_share']:.2%} | {row['loss_rows']} | "
            f"{_usd(row['gross_loss_e6'])} | {_usd(row['worst_event_e6'])} | {_usd(row['max_drawdown_e6'])} | "
            f"{row['top_1pct_loss_share']:.2%} | {row['top_1pct_abs_markout_share']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Distribution",
            "",
            "| Window | p10 net/event | p50 net/event | p90 net/event | Top 5 loss share |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in data["windows"]:
        lines.append(
            f"| {row['window']} | {_usd(row['p10_net_e6'])} | {_usd(row['p50_net_e6'])} | "
            f"{_usd(row['p90_net_e6'])} | {row['top_5_loss_share']:.2%} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_outputs(data: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(data), encoding="utf-8")
    out_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _fixture_event_to_risk(event) -> RiskEvent:
    base = (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
    return RiskEvent(event.t_ms, event.notional_e6, base, event.peg_extra_e6, event.truth_markout_e6, base + event.peg_extra_e6 - event.truth_markout_e6)


def _live_events(db: Path) -> list[RiskEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, t.valid, t.truth_mk_e6
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
        markout = int(row["truth_mk_e6"] or 0)
        events.append(RiskEvent(int(row["ts_ms"]), notional, base, extra, markout, base + extra - markout))
    return events


def _pctl(values: list[int], pct: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[(len(ordered) * pct) // 100]


def _max_drawdown(values: list[int]) -> int:
    cumulative = 0
    peak = 0
    drawdown = 0
    for value in values:
        cumulative += value
        peak = max(peak, cumulative)
        drawdown = min(drawdown, cumulative - peak)
    return drawdown


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate PegGuard tail-risk and concentration economics")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "risk_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "risk_report.json")
    args = parser.parse_args()
    data = compute(root, args.live_db)
    write_outputs(data, args.out_md, args.out_json)
    print(f"risk windows={len(data['windows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
