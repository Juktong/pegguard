from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events


@dataclass(frozen=True)
class ChargeEvent:
    notional_e6: int
    premium_pips: int
    extra_e6: int
    truth_corr: int
    truth_markout_e6: int


@dataclass(frozen=True)
class AttributionBucket:
    window: str
    bucket: str
    rows: int
    notional_e6: int
    extra_e6: int
    truth_markout_e6: int
    abs_truth_markout_e6: int
    row_share: float
    notional_share: float | None
    extra_share: float | None
    abs_markout_share: float | None


@dataclass(frozen=True)
class AttributionWindow:
    window: str
    rows: int
    notional_e6: int
    charged_rows: int
    truth_correcting_rows: int
    extra_e6: int
    correct_extra_e6: int
    wrong_extra_e6: int
    precision: float | None
    false_charge_extra_share: float | None
    truth_correcting_row_recall: float | None
    truth_correcting_markout_coverage: float | None
    missed_correcting_abs_markout_e6: int
    buckets: list[AttributionBucket]


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    windows: list[AttributionWindow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        windows.append(attribution_window("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        windows.append(
            attribution_window(
                window,
                [
                    ChargeEvent(
                        notional_e6=event.notional_e6,
                        premium_pips=event.peg_premium_pips,
                        extra_e6=event.peg_extra_e6,
                        truth_corr=event.truth_corr,
                        truth_markout_e6=event.truth_markout_e6,
                    )
                    for event in fixture
                ],
            )
        )
    return {"windows": [asdict(window) for window in windows]}


def attribution_window(window: str, events: list[ChargeEvent]) -> AttributionWindow:
    rows = len(events)
    notional = sum(event.notional_e6 for event in events)
    charged = [event for event in events if event.premium_pips > 0]
    correct = [event for event in events if event.truth_corr == 1]
    charged_correct = [event for event in charged if event.truth_corr == 1]
    charged_wrong = [event for event in charged if event.truth_corr == 0]
    missed_correcting = [event for event in events if event.premium_pips == 0 and event.truth_corr == 1]
    ignored_noncorrecting = [event for event in events if event.premium_pips == 0 and event.truth_corr == 0]
    extra = sum(event.extra_e6 for event in charged)
    correct_extra = sum(event.extra_e6 for event in charged_correct)
    wrong_extra = sum(event.extra_e6 for event in charged_wrong)
    correct_abs_markout = sum(abs(event.truth_markout_e6) for event in correct)
    charged_correct_abs_markout = sum(abs(event.truth_markout_e6) for event in charged_correct)
    bucket_rows = [
        _bucket(window, "charged correct", charged_correct, events),
        _bucket(window, "charged wrong", charged_wrong, events),
        _bucket(window, "missed correcting", missed_correcting, events),
        _bucket(window, "ignored noncorrecting", ignored_noncorrecting, events),
    ]
    return AttributionWindow(
        window=window,
        rows=rows,
        notional_e6=notional,
        charged_rows=len(charged),
        truth_correcting_rows=len(correct),
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        wrong_extra_e6=wrong_extra,
        precision=(correct_extra / extra) if extra else None,
        false_charge_extra_share=(wrong_extra / extra) if extra else None,
        truth_correcting_row_recall=(len(charged_correct) / len(correct)) if correct else None,
        truth_correcting_markout_coverage=(charged_correct_abs_markout / correct_abs_markout)
        if correct_abs_markout
        else None,
        missed_correcting_abs_markout_e6=sum(abs(event.truth_markout_e6) for event in missed_correcting),
        buckets=bucket_rows,
    )


def markdown(report: dict) -> str:
    lines = [
        "# Charge Attribution",
        "",
        "This report classifies each swap by whether PegGuard charged premium and",
        "whether research truth labels it as correcting flow. It separates false",
        "charges from missed correcting flow, so low capture can be traced to a",
        "specific bucket instead of raw aggregate capture.",
        "",
        "## Window Summary",
        "",
        "| Window | Rows | Charged | Truth-correcting | Extra | Precision | False-charge extra | Correcting row recall | Correcting markout coverage | Missed correcting markout |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for window in report.get("windows", []):
        lines.append(
            f"| {window['window']} | {int(window['rows'])} | {int(window['charged_rows'])} | "
            f"{int(window['truth_correcting_rows'])} | {_usd(int(window['extra_e6']))} | "
            f"{_pct(window.get('precision'))} | {_pct(window.get('false_charge_extra_share'))} | "
            f"{_pct(window.get('truth_correcting_row_recall'))} | "
            f"{_pct(window.get('truth_correcting_markout_coverage'))} | "
            f"{_usd(int(window['missed_correcting_abs_markout_e6']))} |"
        )
    lines.extend(
        [
            "",
            "## Buckets",
            "",
            "| Window | Bucket | Rows | Notional | Extra | Truth markout | Abs markout | Row share | Notional share | Extra share | Abs markout share |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for window in report.get("windows", []):
        for row in window.get("buckets", []):
            lines.append(
                f"| {row['window']} | {row['bucket']} | {int(row['rows'])} | "
                f"{_usd(int(row['notional_e6']))} | {_usd(int(row['extra_e6']))} | "
                f"{_usd(int(row['truth_markout_e6']))} | {_usd(int(row['abs_truth_markout_e6']))} | "
                f"{_pct(row.get('row_share'))} | {_pct(row.get('notional_share'))} | "
                f"{_pct(row.get('extra_share'))} | {_pct(row.get('abs_markout_share'))} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `charged wrong` is premium collected from swaps that truth does not label correcting; it directly lowers premium-weighted precision.",
            "- `missed correcting` is truth-correcting flow that paid no dynamic premium; it explains capture shortfall.",
            "- Correcting markout coverage is based on absolute truth markout, not raw capture, so it is a coverage diagnostic rather than a fee objective.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _bucket(window: str, label: str, bucket_events: list[ChargeEvent], all_events: list[ChargeEvent]) -> AttributionBucket:
    total_notional = sum(event.notional_e6 for event in all_events)
    total_extra = sum(event.extra_e6 for event in all_events)
    total_abs_markout = sum(abs(event.truth_markout_e6) for event in all_events)
    notional = sum(event.notional_e6 for event in bucket_events)
    extra = sum(event.extra_e6 for event in bucket_events)
    abs_markout = sum(abs(event.truth_markout_e6) for event in bucket_events)
    return AttributionBucket(
        window=window,
        bucket=label,
        rows=len(bucket_events),
        notional_e6=notional,
        extra_e6=extra,
        truth_markout_e6=sum(event.truth_markout_e6 for event in bucket_events),
        abs_truth_markout_e6=abs_markout,
        row_share=(len(bucket_events) / len(all_events)) if all_events else 0.0,
        notional_share=(notional / total_notional) if total_notional else None,
        extra_share=(extra / total_extra) if total_extra else None,
        abs_markout_share=(abs_markout / total_abs_markout) if total_abs_markout else None,
    )


def _live_events(db: Path) -> list[ChargeEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.aq_e6, l.fresh_premium_pips, l.fresh_extra_e6, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        ChargeEvent(
            notional_e6=abs(int(row["aq_e6"])),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
            truth_markout_e6=int(row["truth_mk_e6"] or 0),
        )
        for row in rows
    ]


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Attribute charged premium to truth-correcting and missed-flow buckets")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "charge_attribution_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "charge_attribution_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"charge attribution windows={len(report['windows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["windows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
