from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .db import connect
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM

DECISIONS = ("fresh", "lag2", "lag5")


@dataclass(frozen=True)
class OracleLagRow:
    label: str
    rows: int
    valid_truth_rows: int
    fallback_rows: int
    fallback_notional_e6: int
    fallback_share: float
    charged_rows: int
    notional_e6: int
    base_e6: int
    extra_e6: int
    correct_extra_e6: int
    wrong_extra_e6: int
    markout_e6: int
    net_e6: int
    net_bps: float
    precision: float | None
    truth_capture: float | None
    delta_extra_vs_fresh_e6: int
    delta_wrong_extra_vs_fresh_e6: int
    delta_net_vs_fresh_e6: int
    delta_net_bps_vs_fresh: float
    delta_precision_vs_fresh: float | None
    delta_capture_vs_fresh: float | None


def compute(db: Path) -> dict:
    conn = connect(db)
    try:
        rows = conn.execute(
            """
            SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            """
        ).fetchall()
    finally:
        conn.close()

    raw_rows = [_row_for_label(label, rows) for label in DECISIONS]
    fresh = raw_rows[0]
    return {
        "database": str(db),
        "rows": [asdict(_with_delta(row, fresh)) for row in raw_rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Oracle Lag Stress",
        "",
        "This report compares the actual fresh hot-path oracle decision with lagged",
        "2s and 5s sensitivity decisions recorded in the live shadow ledger. It",
        "quantifies the staleness trap: lagged signals can change capture, precision,",
        "wrong-side premium, and net economics even when the same swaps are replayed.",
        "",
        f"- Database: `{report.get('database', 'n/a')}`",
        "",
        "| Decision | Truth rows | Fallback share | Charged rows | Extra | Wrong extra | Precision | Truth capture | Net bps | Delta net | Delta precision | Delta capture |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['label']} | {int(row['valid_truth_rows'])} | {float(row['fallback_share']):.2%} | "
            f"{int(row['charged_rows'])} | {_usd(int(row['extra_e6']))} | {_usd(int(row['wrong_extra_e6']))} | "
            f"{_pct(row.get('precision'))} | {_pct(row.get('truth_capture'))} | {float(row['net_bps']):.2f} | "
            f"{_usd(int(row['delta_net_vs_fresh_e6']))} | {_pp(row.get('delta_precision_vs_fresh'))} | "
            f"{_pp(row.get('delta_capture_vs_fresh'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `fresh` is the actual hot-path behavior; its deltas are zero by definition.",
            "- `lag2` and `lag5` are same-swap delayed-oracle sensitivity rows from the shadow daemon.",
            "- Higher raw capture is not automatically better; precision and wrong-side premium show whether the extra fee is economically aligned.",
            "- Fallback rows degrade to base fee and are included because production safety intentionally disables dynamic premium there.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row_for_label(label: str, rows: list) -> OracleLagRow:
    premium_key = f"{label}_premium_pips"
    extra_key = f"{label}_extra_e6"
    reason_key = f"{label}_fallback_reason"
    truth_rows = [row for row in rows if row["valid"]]
    charged_truth = [row for row in truth_rows if int(row[premium_key] or 0) > 0]
    fallback = [row for row in rows if row[reason_key]]
    notional = sum(abs(int(row["aq_e6"])) for row in truth_rows)
    all_notional = sum(abs(int(row["aq_e6"])) for row in rows)
    base = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in truth_rows)
    extra = sum(int(row[extra_key] or 0) for row in truth_rows)
    correct_extra = sum(int(row[extra_key] or 0) for row in charged_truth if int(row["truth_corr"] or 0) == 1)
    wrong_extra = sum(int(row[extra_key] or 0) for row in charged_truth if int(row["truth_corr"] or 0) != 1)
    markout = sum(int(row["truth_mk_e6"] or 0) for row in truth_rows)
    net = base + extra - markout
    premium_total = correct_extra + wrong_extra
    return OracleLagRow(
        label=label,
        rows=len(rows),
        valid_truth_rows=len(truth_rows),
        fallback_rows=len(fallback),
        fallback_notional_e6=sum(abs(int(row["aq_e6"])) for row in fallback),
        fallback_share=(sum(abs(int(row["aq_e6"])) for row in fallback) / all_notional) if all_notional else 0.0,
        charged_rows=len([row for row in rows if int(row[premium_key] or 0) > 0]),
        notional_e6=notional,
        base_e6=base,
        extra_e6=extra,
        correct_extra_e6=correct_extra,
        wrong_extra_e6=wrong_extra,
        markout_e6=markout,
        net_e6=net,
        net_bps=_bps(net, notional),
        precision=(correct_extra / premium_total) if premium_total else None,
        truth_capture=(extra / abs(markout)) if markout else None,
        delta_extra_vs_fresh_e6=0,
        delta_wrong_extra_vs_fresh_e6=0,
        delta_net_vs_fresh_e6=0,
        delta_net_bps_vs_fresh=0.0,
        delta_precision_vs_fresh=0.0,
        delta_capture_vs_fresh=0.0,
    )


def _with_delta(row: OracleLagRow, fresh: OracleLagRow) -> OracleLagRow:
    return OracleLagRow(
        label=row.label,
        rows=row.rows,
        valid_truth_rows=row.valid_truth_rows,
        fallback_rows=row.fallback_rows,
        fallback_notional_e6=row.fallback_notional_e6,
        fallback_share=row.fallback_share,
        charged_rows=row.charged_rows,
        notional_e6=row.notional_e6,
        base_e6=row.base_e6,
        extra_e6=row.extra_e6,
        correct_extra_e6=row.correct_extra_e6,
        wrong_extra_e6=row.wrong_extra_e6,
        markout_e6=row.markout_e6,
        net_e6=row.net_e6,
        net_bps=row.net_bps,
        precision=row.precision,
        truth_capture=row.truth_capture,
        delta_extra_vs_fresh_e6=row.extra_e6 - fresh.extra_e6,
        delta_wrong_extra_vs_fresh_e6=row.wrong_extra_e6 - fresh.wrong_extra_e6,
        delta_net_vs_fresh_e6=row.net_e6 - fresh.net_e6,
        delta_net_bps_vs_fresh=row.net_bps - fresh.net_bps,
        delta_precision_vs_fresh=_delta_optional(row.precision, fresh.precision),
        delta_capture_vs_fresh=_delta_optional(row.truth_capture, fresh.truth_capture),
    )


def _delta_optional(value: float | None, base: float | None) -> float | None:
    if value is None or base is None:
        return None
    return value - base


def _bps(num_e6: int, den_e6: int) -> float:
    if den_e6 == 0:
        return 0.0
    return num_e6 / den_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _pp(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:+.2f}pp"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compare fresh and lagged oracle-decision economics")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "oracle_lag_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "oracle_lag_report.json")
    args = parser.parse_args()
    report = compute(args.database)
    write_outputs(report, args.out_md, args.out_json)
    print(f"oracle lag rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
