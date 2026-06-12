from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import PIPS_DENOM, fixture_events

CHILD_COUNTS = (2, 5, 10, 25, 100)


@dataclass(frozen=True)
class SplitEvent:
    notional_e6: int
    premium_pips: int
    extra_e6: int
    markout_e6: int
    truth_corr: int


@dataclass(frozen=True)
class SplitRow:
    window: str
    child_count: int
    rows: int
    charged_rows: int
    notional_e6: int
    markout_e6: int
    original_extra_e6: int
    split_extra_e6: int
    leaked_extra_e6: int
    leakage_rate: float | None
    leakage_bps_of_notional: float
    original_precision: float | None
    split_precision: float | None
    original_capture: float | None
    split_capture: float | None


def compute(root: Path | None = None, live_db: Path | None = None, child_counts: tuple[int, ...] = CHILD_COUNTS) -> dict:
    root = root or C.repo_root()
    rows: list[SplitRow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(split_rows("live shadow", live_events, child_counts))
    for window in ("calm", "vol"):
        events, _ = fixture_events(root, window)
        rows.extend(split_rows(window, [_fixture_event(event) for event in events], child_counts))
    return {
        "child_counts": list(child_counts),
        "model": "same-signal notional split; children inherit the original premium pips",
        "rows": [asdict(row) for row in rows],
    }


def split_rows(window: str, events: list[SplitEvent], child_counts: tuple[int, ...] = CHILD_COUNTS) -> list[SplitRow]:
    return [_split_row(window, events, child_count) for child_count in child_counts]


def markdown(report: dict) -> str:
    lines = [
        "# Order-Splitting Sensitivity",
        "",
        "This report checks whether splitting one swap into multiple same-signal",
        "children can avoid PegGuard premium. The model is deliberately narrow:",
        "each child inherits the original premium pips. That isolates the direct",
        "notional-splitting bypass risk from route-away or time-separated oracle",
        "changes.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Children | Rows | Charged rows | Notional | Original extra | Split extra | Leaked extra | Leakage | Leakage bps | Precision before/after | Capture before/after |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {int(row['child_count'])} | {int(row['rows'])} | {int(row['charged_rows'])} | "
            f"{_usd(int(row['notional_e6']))} | {_usd(int(row['original_extra_e6']))} | {_usd(int(row['split_extra_e6']))} | "
            f"{_usd(int(row['leaked_extra_e6']))} | {_pct(row.get('leakage_rate'))} | "
            f"{float(row['leakage_bps_of_notional']):.6f} | {_pct(row.get('original_precision'))} / {_pct(row.get('split_precision'))} | "
            f"{_pct(row.get('original_capture'))} / {_pct(row.get('split_capture'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Since premium is pips-on-notional, same-signal splitting should only save integer-rounding dust.",
            "- This does not model a trader waiting between children for a new oracle/basis state; that is a route/timing behavior, not a notional-threshold bypass.",
            "- Live-shadow rows include only events with valid truth labels, so the live row will stabilize as truth coverage rises.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _split_row(window: str, events: list[SplitEvent], child_count: int) -> SplitRow:
    if child_count <= 0:
        raise ValueError("child_count must be positive")
    notional = sum(event.notional_e6 for event in events)
    markout = sum(event.markout_e6 for event in events)
    original_extra = sum(event.extra_e6 for event in events)
    split_extra = sum(_split_fee(event.notional_e6, event.premium_pips, child_count) for event in events)
    original_total = sum(event.extra_e6 for event in events if event.premium_pips > 0)
    original_correct = sum(event.extra_e6 for event in events if event.premium_pips > 0 and event.truth_corr == 1)
    split_total = sum(_split_fee(event.notional_e6, event.premium_pips, child_count) for event in events if event.premium_pips > 0)
    split_correct = sum(
        _split_fee(event.notional_e6, event.premium_pips, child_count)
        for event in events
        if event.premium_pips > 0 and event.truth_corr == 1
    )
    leaked = original_extra - split_extra
    return SplitRow(
        window=window,
        child_count=child_count,
        rows=len(events),
        charged_rows=sum(1 for event in events if event.premium_pips > 0),
        notional_e6=notional,
        markout_e6=markout,
        original_extra_e6=original_extra,
        split_extra_e6=split_extra,
        leaked_extra_e6=leaked,
        leakage_rate=(leaked / original_extra) if original_extra else None,
        leakage_bps_of_notional=_bps(leaked, notional),
        original_precision=(original_correct / original_total) if original_total else None,
        split_precision=(split_correct / split_total) if split_total else None,
        original_capture=(original_extra / abs(markout)) if markout else None,
        split_capture=(split_extra / abs(markout)) if markout else None,
    )


def _split_fee(notional_e6: int, pips: int, child_count: int) -> int:
    if pips <= 0 or notional_e6 <= 0:
        return 0
    base = notional_e6 // child_count
    remainder = notional_e6 % child_count
    larger = ((base + 1) * pips) // PIPS_DENOM
    smaller = (base * pips) // PIPS_DENOM
    return remainder * larger + (child_count - remainder) * smaller


def _fixture_event(event) -> SplitEvent:
    return SplitEvent(
        notional_e6=event.notional_e6,
        premium_pips=event.peg_premium_pips,
        extra_e6=event.peg_extra_e6,
        markout_e6=event.truth_markout_e6,
        truth_corr=event.truth_corr,
    )


def _live_events(db: Path) -> list[SplitEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        SplitEvent(
            notional_e6=abs(int(row["aq_e6"])),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            markout_e6=int(row["truth_mk_e6"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
        )
        for row in rows
    ]


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
    return f"{float(value):.4%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check same-signal order-splitting premium leakage")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--child-counts", type=int, nargs="+", default=list(CHILD_COUNTS))
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "order_split_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "order_split_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, tuple(args.child_counts))
    write_outputs(report, args.out_md, args.out_json)
    print(f"order split rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
