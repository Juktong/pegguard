from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import PIPS_DENOM, fixture_events


@dataclass(frozen=True)
class PremiumEvent:
    notional_e6: int
    premium_pips: int
    extra_e6: int
    truth_corr: int


@dataclass(frozen=True)
class PremiumUtilizationRow:
    window: str
    rows: int
    notional_e6: int
    charged_rows: int
    charged_row_share: float
    charged_notional_e6: int
    charged_notional_share: float | None
    extra_e6: int
    correct_extra_e6: int
    precision: float | None
    avg_premium_all_bps: float
    avg_premium_charged_bps: float
    p50_charged_premium_bps: float | None
    p90_charged_premium_bps: float | None
    p99_charged_premium_bps: float | None
    max_premium_bps: float
    cap_hit_rows: int
    cap_hit_notional_e6: int
    near_cap_rows: int
    near_cap_notional_e6: int
    top_10pct_extra_share: float | None
    top_1pct_extra_share: float | None


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[PremiumUtilizationRow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        rows.append(utilization_row("live shadow", live_events))
    for window in ("calm", "vol"):
        fixtures, _ = fixture_events(root, window)
        rows.append(
            utilization_row(
                window,
                [
                    PremiumEvent(
                        notional_e6=event.notional_e6,
                        premium_pips=event.peg_premium_pips,
                        extra_e6=event.peg_extra_e6,
                        truth_corr=event.truth_corr,
                    )
                    for event in fixtures
                ],
            )
        )
    return {
        "cap_pips": C.CAP_PIPS,
        "cap_bps": C.CAP_PIPS / 100,
        "near_cap_threshold_pips": int(C.CAP_PIPS * 0.8),
        "rows": [asdict(row) for row in rows],
    }


def utilization_row(window: str, events: list[PremiumEvent]) -> PremiumUtilizationRow:
    rows = len(events)
    notional = sum(event.notional_e6 for event in events)
    charged = [event for event in events if event.premium_pips > 0]
    charged_notional = sum(event.notional_e6 for event in charged)
    extra = sum(event.extra_e6 for event in charged)
    correct_extra = sum(event.extra_e6 for event in charged if event.truth_corr == 1)
    premiums = sorted((event.premium_pips / 100 for event in charged))
    cap_hit = [event for event in charged if event.premium_pips >= C.CAP_PIPS]
    near_cap_threshold = int(C.CAP_PIPS * 0.8)
    near_cap = [event for event in charged if event.premium_pips >= near_cap_threshold]
    extra_values = sorted((event.extra_e6 for event in charged if event.extra_e6 > 0), reverse=True)
    return PremiumUtilizationRow(
        window=window,
        rows=rows,
        notional_e6=notional,
        charged_rows=len(charged),
        charged_row_share=(len(charged) / rows) if rows else 0.0,
        charged_notional_e6=charged_notional,
        charged_notional_share=(charged_notional / notional) if notional else None,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        precision=(correct_extra / extra) if extra else None,
        avg_premium_all_bps=_bps(extra, notional),
        avg_premium_charged_bps=_bps(extra, charged_notional),
        p50_charged_premium_bps=_pctl_float(premiums, 50),
        p90_charged_premium_bps=_pctl_float(premiums, 90),
        p99_charged_premium_bps=_pctl_float(premiums, 99),
        max_premium_bps=max(premiums, default=0.0),
        cap_hit_rows=len(cap_hit),
        cap_hit_notional_e6=sum(event.notional_e6 for event in cap_hit),
        near_cap_rows=len(near_cap),
        near_cap_notional_e6=sum(event.notional_e6 for event in near_cap),
        top_10pct_extra_share=_top_share(extra_values, 0.10),
        top_1pct_extra_share=_top_share(extra_values, 0.01),
    )


def markdown(report: dict) -> str:
    lines = [
        "# Premium Utilization",
        "",
        "This report measures how PegGuard uses the dynamic premium: charged-flow",
        "share, premium distribution, cap pressure, and whether premium dollars",
        "remain weighted toward truth-correcting swaps.",
        "",
        f"- Cap: {int(report.get('cap_pips', 0)) / 100:.2f} bps",
        f"- Near-cap threshold: {int(report.get('near_cap_threshold_pips', 0)) / 100:.2f} bps",
        "",
        "| Window | Rows | Charged | Charged notional | Extra | Precision | Avg all | Avg charged | p50 charged | p90 charged | p99 charged | Max | Cap hits | Near cap | Top 10% extra | Top 1% extra |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {int(row['rows'])} | {int(row['charged_rows'])} ({_pct(row.get('charged_row_share'))}) | "
            f"{_usd(int(row['charged_notional_e6']))} ({_pct(row.get('charged_notional_share'))}) | "
            f"{_usd(int(row['extra_e6']))} | {_pct(row.get('precision'))} | "
            f"{float(row['avg_premium_all_bps']):.2f} bps | {float(row['avg_premium_charged_bps']):.2f} bps | "
            f"{_bps_or_na(row.get('p50_charged_premium_bps'))} | {_bps_or_na(row.get('p90_charged_premium_bps'))} | "
            f"{_bps_or_na(row.get('p99_charged_premium_bps'))} | {float(row['max_premium_bps']):.2f} bps | "
            f"{int(row['cap_hit_rows'])} | {int(row['near_cap_rows'])} | "
            f"{_pct(row.get('top_10pct_extra_share'))} | {_pct(row.get('top_1pct_extra_share'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Cap hits indicate the measured signal wants more than the configured dynamic premium cap.",
            "- High top-extra shares mean fee revenue is concentrated in a small number of charged swaps.",
            "- Precision is premium-weighted, so a low value means premium dollars are landing on non-correcting flow.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _live_events(db: Path) -> list[PremiumEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.aq_e6, l.fresh_premium_pips, l.fresh_extra_e6, t.truth_corr
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        PremiumEvent(
            notional_e6=abs(int(row["aq_e6"])),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
        )
        for row in rows
    ]


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _pctl_float(values: list[float], pct: int) -> float | None:
    if not values:
        return None
    index = min(len(values) - 1, (len(values) * pct) // 100)
    return values[index]


def _top_share(values: list[int], fraction: float) -> float | None:
    if not values:
        return None
    count = max(1, int(len(values) * fraction))
    total = sum(values)
    return (sum(values[:count]) / total) if total else None


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
    parser = argparse.ArgumentParser(description="Measure PegGuard dynamic premium utilization")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "premium_utilization_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "premium_utilization_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"premium utilization rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
