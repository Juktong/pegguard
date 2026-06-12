from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM


DEFAULT_CHECKPOINT_SEC = 60 * 60


@dataclass(frozen=True)
class MaturityRow:
    checkpoint_index: int
    end_offset_hours: float
    rows: int
    valid_rows: int
    truth_coverage: float
    notional_e6: int
    charged_rows: int
    fallback_notional_e6: int
    fallback_notional_share: float | None
    base_fee_e6: int
    extra_e6: int
    correct_extra_e6: int
    truth_markout_e6: int
    precision: float | None
    capture_truth: float | None
    net_e6: int
    net_bps: float
    precision_delta_vs_final: float | None
    capture_delta_vs_final: float | None
    net_bps_delta_vs_final: float | None


def compute(database: Path | None = None, checkpoint_sec: int = DEFAULT_CHECKPOINT_SEC) -> dict:
    database = database or C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3"
    if checkpoint_sec <= 0:
        raise ValueError("checkpoint_sec must be positive")
    if not database.exists():
        return _empty(database, checkpoint_sec)

    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                l.id,
                l.ts_ms,
                l.aq_e6,
                l.fresh_premium_pips,
                l.fresh_extra_e6,
                l.fresh_fallback_reason,
                t.valid,
                t.truth_corr,
                t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return _empty(database, checkpoint_sec)

    first_ts = int(rows[0]["ts_ms"])
    checkpoint_ms = checkpoint_sec * 1000
    last_index = (int(rows[-1]["ts_ms"]) - first_ts) // checkpoint_ms
    cumulative_rows = []
    prefix: list[sqlite3.Row] = []
    cursor = 0
    final_metrics = _metrics(rows)
    for index in range(last_index + 1):
        end_ts = first_ts + (index + 1) * checkpoint_ms
        while cursor < len(rows) and int(rows[cursor]["ts_ms"]) < end_ts:
            prefix.append(rows[cursor])
            cursor += 1
        if not prefix:
            continue
        metrics = _metrics(prefix)
        cumulative_rows.append(_maturity_row(index, metrics, final_metrics, checkpoint_sec))

    return {
        "database": str(database),
        "checkpoint_sec": checkpoint_sec,
        "complete": len(cumulative_rows) >= 2 and final_metrics["valid_rows"] > 0 and final_metrics["charged_rows"] > 0,
        "checkpoint_count": len(cumulative_rows),
        "rows": final_metrics["rows"],
        "valid_rows": final_metrics["valid_rows"],
        "truth_coverage": final_metrics["truth_coverage"],
        "charged_rows": final_metrics["charged_rows"],
        "notional_e6": final_metrics["notional_e6"],
        "extra_e6": final_metrics["extra_e6"],
        "truth_markout_e6": final_metrics["truth_markout_e6"],
        "precision": final_metrics["precision"],
        "capture_truth": final_metrics["capture_truth"],
        "net_e6": final_metrics["net_e6"],
        "net_bps": final_metrics["net_bps"],
        "max_abs_precision_delta": _max_abs(row.precision_delta_vs_final for row in cumulative_rows),
        "max_abs_capture_delta": _max_abs(row.capture_delta_vs_final for row in cumulative_rows),
        "max_abs_net_bps_delta": _max_abs(row.net_bps_delta_vs_final for row in cumulative_rows),
        "maturity_rows": [asdict(row) for row in cumulative_rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Live Shadow Maturity",
        "",
        "This report recomputes cumulative live economics at fixed elapsed-time",
        "checkpoints. It answers whether the live headline is stabilizing as",
        "more swaps accrue, not whether the required 24h run is complete.",
        "",
        f"- Database: `{report.get('database', 'n/a')}`",
        f"- Checkpoint size: {int(report.get('checkpoint_sec', 0))} seconds",
        f"- Status: {'complete' if report.get('complete') else 'in progress'}",
        f"- Checkpoints: {int(report.get('checkpoint_count', 0))}",
        f"- Current precision: {_pct(report.get('precision'))}",
        f"- Current truth capture: {_pct(report.get('capture_truth'))}",
        f"- Current net: {_usd(int(report.get('net_e6', 0)))} ({float(report.get('net_bps', 0.0)):.2f} bps)",
        f"- Max absolute precision delta vs current: {_pct(report.get('max_abs_precision_delta'))}",
        f"- Max absolute capture delta vs current: {_pct(report.get('max_abs_capture_delta'))}",
        f"- Max absolute net-bps delta vs current: {_bps(report.get('max_abs_net_bps_delta'))}",
        "",
        "| Checkpoint | Elapsed | Rows | Valid | Charged | Notional | Extra | Truth markout | Precision | Capture | Net | Net bps | Precision delta | Capture delta | Net-bps delta | Fallback share |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("maturity_rows", []):
        lines.append(
            f"| {int(row['checkpoint_index'])} | {float(row['end_offset_hours']):.2f}h | "
            f"{int(row['rows'])} | {int(row['valid_rows'])} | {int(row['charged_rows'])} | "
            f"{_usd(int(row['notional_e6']))} | {_usd(int(row['extra_e6']))} | "
            f"{_usd(int(row['truth_markout_e6']))} | {_pct(row.get('precision'))} | "
            f"{_pct(row.get('capture_truth'))} | {_usd(int(row['net_e6']))} | "
            f"{float(row['net_bps']):.2f} | {_signed_pct(row.get('precision_delta_vs_final'))} | "
            f"{_signed_pct(row.get('capture_delta_vs_final'))} | {_signed_bps(row.get('net_bps_delta_vs_final'))} | "
            f"{_pct(row.get('fallback_notional_share'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Large early deltas mean the live evidence is still sample-sensitive and should not be treated as a settled headline.",
            "- Precision can stabilize before truth capture because capture depends on the size and timing of adverse markouts.",
            "- This report is cumulative live evidence; it is not a substitute for the separate 24h gate.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _empty(database: Path, checkpoint_sec: int) -> dict:
    return {
        "database": str(database),
        "checkpoint_sec": checkpoint_sec,
        "complete": False,
        "checkpoint_count": 0,
        "rows": 0,
        "valid_rows": 0,
        "truth_coverage": 0.0,
        "charged_rows": 0,
        "notional_e6": 0,
        "extra_e6": 0,
        "truth_markout_e6": 0,
        "precision": None,
        "capture_truth": None,
        "net_e6": 0,
        "net_bps": 0.0,
        "max_abs_precision_delta": None,
        "max_abs_capture_delta": None,
        "max_abs_net_bps_delta": None,
        "maturity_rows": [],
    }


def _metrics(rows: list[sqlite3.Row]) -> dict:
    valid = [row for row in rows if int(row["valid"] or 0) == 1]
    notional = sum(abs(int(row["aq_e6"])) for row in valid)
    charged = [row for row in valid if int(row["fresh_premium_pips"] or 0) > 0]
    fallback = [
        row
        for row in valid
        if row["fresh_fallback_reason"] is not None and str(row["fresh_fallback_reason"]) != ""
    ]
    fallback_notional = sum(abs(int(row["aq_e6"])) for row in fallback)
    base_fee = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in valid)
    extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged)
    correct_extra = sum(int(row["fresh_extra_e6"] or 0) for row in charged if int(row["truth_corr"] or 0) == 1)
    truth_markout = sum(int(row["truth_mk_e6"] or 0) for row in valid)
    net = base_fee + extra - truth_markout
    return {
        "rows": len(rows),
        "valid_rows": len(valid),
        "truth_coverage": len(valid) / len(rows) if rows else 0.0,
        "notional_e6": notional,
        "charged_rows": len(charged),
        "fallback_notional_e6": fallback_notional,
        "fallback_notional_share": (fallback_notional / notional) if notional else None,
        "base_fee_e6": base_fee,
        "extra_e6": extra,
        "correct_extra_e6": correct_extra,
        "truth_markout_e6": truth_markout,
        "precision": (correct_extra / extra) if extra else None,
        "capture_truth": (extra / abs(truth_markout)) if truth_markout else None,
        "net_e6": net,
        "net_bps": _raw_bps(net, notional),
    }


def _maturity_row(index: int, metrics: dict, final: dict, checkpoint_sec: int) -> MaturityRow:
    return MaturityRow(
        checkpoint_index=index,
        end_offset_hours=((index + 1) * checkpoint_sec) / 3600,
        rows=int(metrics["rows"]),
        valid_rows=int(metrics["valid_rows"]),
        truth_coverage=float(metrics["truth_coverage"]),
        notional_e6=int(metrics["notional_e6"]),
        charged_rows=int(metrics["charged_rows"]),
        fallback_notional_e6=int(metrics["fallback_notional_e6"]),
        fallback_notional_share=metrics["fallback_notional_share"],
        base_fee_e6=int(metrics["base_fee_e6"]),
        extra_e6=int(metrics["extra_e6"]),
        correct_extra_e6=int(metrics["correct_extra_e6"]),
        truth_markout_e6=int(metrics["truth_markout_e6"]),
        precision=metrics["precision"],
        capture_truth=metrics["capture_truth"],
        net_e6=int(metrics["net_e6"]),
        net_bps=float(metrics["net_bps"]),
        precision_delta_vs_final=_delta(metrics["precision"], final["precision"]),
        capture_delta_vs_final=_delta(metrics["capture_truth"], final["capture_truth"]),
        net_bps_delta_vs_final=float(metrics["net_bps"]) - float(final["net_bps"]),
    )


def _delta(value: object, final: object) -> float | None:
    if value is None or final is None:
        return None
    return float(value) - float(final)


def _max_abs(values) -> float | None:
    concrete = [abs(float(value)) for value in values if value is not None]
    return max(concrete) if concrete else None


def _raw_bps(value_e6: int, notional_e6: int) -> float:
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


def _signed_pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):+.2%}"


def _bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def _signed_bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):+.2f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Measure cumulative live-shadow economics at elapsed-time checkpoints")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--checkpoint-sec", type=int, default=DEFAULT_CHECKPOINT_SEC)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "live_maturity_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "live_maturity_report.json")
    args = parser.parse_args()
    report = compute(args.database, args.checkpoint_sec)
    write_outputs(report, args.out_md, args.out_json)
    print(f"live maturity checkpoints={report['checkpoint_count']} complete={report['complete']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
