from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events
from .risk_report import RiskEvent, _fixture_event_to_risk, _live_events

THRESHOLDS_E6 = (10_000_000, 50_000_000, 100_000_000, 500_000_000)


@dataclass(frozen=True)
class DrawdownStopRow:
    window: str
    threshold_e6: int
    triggered: bool
    trigger_index: int | None
    active_rows: int
    skipped_rows: int
    full_notional_e6: int
    skipped_notional_e6: int
    full_net_e6: int
    stopped_net_e6: int
    delta_vs_full_e6: int
    skipped_base_e6: int
    skipped_extra_e6: int
    skipped_markout_e6: int
    max_drawdown_e6: int


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    windows: list[tuple[str, list[RiskEvent]]] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        windows.append(("live shadow", live_events))
    for window in ("calm", "vol"):
        events, _ = fixture_events(root, window)
        windows.append((window, [_fixture_event_to_risk(event) for event in events]))
    rows = [
        _row_for_threshold(window, events, threshold)
        for window, events in windows
        for threshold in THRESHOLDS_E6
    ]
    return {
        "thresholds_e6": list(THRESHOLDS_E6),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Drawdown Stop-Loss",
        "",
        "This report applies mechanical pause-after-drawdown thresholds to measured",
        "event PnL. It uses the same PnL definition as `risk_report`: base fee plus",
        "PegGuard extra premium minus truth markout. A trigger includes the breach",
        "event and skips all later swaps in that window.",
        "",
        "| Window | Threshold | Triggered | Active rows | Skipped rows | Skipped notional | Full net | Stopped net | Delta vs full | Skipped extra | Skipped markout | Max drawdown |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {_usd(int(row['threshold_e6']))} | {'yes' if row['triggered'] else 'no'} | "
            f"{int(row['active_rows'])} | {int(row['skipped_rows'])} | {_usd(int(row['skipped_notional_e6']))} | "
            f"{_usd(int(row['full_net_e6']))} | {_usd(int(row['stopped_net_e6']))} | "
            f"{_usd(int(row['delta_vs_full_e6']))} | {_usd(int(row['skipped_extra_e6']))} | "
            f"{_usd(int(row['skipped_markout_e6']))} | {_usd(int(row['max_drawdown_e6']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Positive `delta vs full` means pausing after the threshold would have improved that window's final net.",
            "- Negative `delta vs full` means the stop skipped enough later profitable flow to hurt final net.",
            "- This is an operational stress rule, not a hook constant or calibration input.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row_for_threshold(window: str, events: list[RiskEvent], threshold_e6: int) -> DrawdownStopRow:
    cumulative = 0
    peak = 0
    max_drawdown = 0
    trigger_index: int | None = None
    for index, event in enumerate(events):
        cumulative += event.net_e6
        peak = max(peak, cumulative)
        drawdown = cumulative - peak
        max_drawdown = min(max_drawdown, drawdown)
        if trigger_index is None and drawdown <= -threshold_e6:
            trigger_index = index
            break

    active_count = len(events) if trigger_index is None else trigger_index + 1
    active = events[:active_count]
    skipped = events[active_count:]
    full_net = sum(event.net_e6 for event in events)
    stopped_net = sum(event.net_e6 for event in active)
    return DrawdownStopRow(
        window=window,
        threshold_e6=threshold_e6,
        triggered=trigger_index is not None,
        trigger_index=trigger_index,
        active_rows=len(active),
        skipped_rows=len(skipped),
        full_notional_e6=sum(event.notional_e6 for event in events),
        skipped_notional_e6=sum(event.notional_e6 for event in skipped),
        full_net_e6=full_net,
        stopped_net_e6=stopped_net,
        delta_vs_full_e6=stopped_net - full_net,
        skipped_base_e6=sum(event.base_fee_e6 for event in skipped),
        skipped_extra_e6=sum(event.extra_e6 for event in skipped),
        skipped_markout_e6=sum(event.markout_e6 for event in skipped),
        max_drawdown_e6=max_drawdown,
    )


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Simulate pause-after-drawdown operational thresholds")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "drawdown_stop_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "drawdown_stop_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"drawdown stop rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
