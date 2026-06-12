from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .db import connect

DECISIONS = ("fresh", "lag2", "lag5")


@dataclass(frozen=True)
class DecisionHealth:
    label: str
    rows: int
    fallback_rows: int
    fallback_notional_e6: int
    fallback_notional_share: float
    charged_rows: int
    extra_e6: int
    precision: float | None
    truth_capture: float | None
    fallback_counts: dict[str, int]


@dataclass(frozen=True)
class OracleHealth:
    database: str
    swaps: int
    notional_e6: int
    valid_truth_rows: int
    pyth_health_rows: int
    gap_minutes: float
    staleness_p50_ms: int | None
    staleness_p90_ms: int | None
    staleness_max_ms: int | None
    pyth_lag_p50_ms: int | None
    pyth_lag_p90_ms: int | None
    pyth_lag_max_ms: int | None
    decisions: list[DecisionHealth]


def compute(db: Path) -> OracleHealth:
    conn = connect(db)
    try:
        rows = conn.execute(
            """
            SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            """
        ).fetchall()
        pyth_lags = [int(row["lag_ms"]) for row in conn.execute("SELECT lag_ms FROM pyth_health").fetchall()]
        pyth_health_rows = len(pyth_lags)
        gap_minutes = _gap_minutes(conn)
    finally:
        conn.close()

    notional = sum(abs(int(row["aq_e6"])) for row in rows)
    truth_rows = [row for row in rows if row["valid"]]
    markout = sum(int(row["truth_mk_e6"] or 0) for row in truth_rows)
    staleness = [int(row["oracle_staleness_observed_ms"]) for row in rows if row["oracle_staleness_observed_ms"] is not None]

    return OracleHealth(
        database=str(db),
        swaps=len(rows),
        notional_e6=notional,
        valid_truth_rows=len(truth_rows),
        pyth_health_rows=pyth_health_rows,
        gap_minutes=gap_minutes,
        staleness_p50_ms=_pctl(staleness, 50),
        staleness_p90_ms=_pctl(staleness, 90),
        staleness_max_ms=max(staleness) if staleness else None,
        pyth_lag_p50_ms=_pctl(pyth_lags, 50),
        pyth_lag_p90_ms=_pctl(pyth_lags, 90),
        pyth_lag_max_ms=max(pyth_lags) if pyth_lags else None,
        decisions=[_decision_health(label, rows, truth_rows, markout, notional) for label in DECISIONS],
    )


def markdown(report: OracleHealth) -> str:
    lines = [
        "# Oracle Health Economics",
        "",
        "This report quantifies how oracle freshness and fallback behavior affect the",
        "economic shadow sample. It is measurement only; it does not change hook",
        "constants or calibration.",
        "",
        "## Snapshot",
        "",
        f"- Database: `{report.database}`",
        f"- Swaps: {report.swaps}",
        f"- Notional: {_usd(report.notional_e6)}",
        f"- Valid truth rows: {report.valid_truth_rows}",
        f"- Pyth health rows: {report.pyth_health_rows}",
        f"- Gap minutes: {report.gap_minutes:.2f}",
        f"- Observed oracle staleness p50/p90/max: {_seconds(report.staleness_p50_ms)} / {_seconds(report.staleness_p90_ms)} / {_seconds(report.staleness_max_ms)}",
        f"- Pyth feed lag p50/p90/max: {_seconds(report.pyth_lag_p50_ms)} / {_seconds(report.pyth_lag_p90_ms)} / {_seconds(report.pyth_lag_max_ms)}",
        "",
        "## Decision Economics",
        "",
        "| Decision | Fallback rows | Fallback notional | Fallback share | Charged rows | Extra | Precision | Truth capture | Fallback reasons |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.decisions:
        lines.append(
            f"| {row.label} | {row.fallback_rows} | {_usd(row.fallback_notional_e6)} | "
            f"{row.fallback_notional_share:.2%} | {row.charged_rows} | {_usd(row.extra_e6)} | "
            f"{_pct(row.precision)} | {_pct(row.truth_capture)} | {_counter(row.fallback_counts)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `fresh` is the actual hot-path decision used in the shadow run.",
            "- `lag2` and `lag5` are sensitivity decisions using delayed oracle observations.",
            "- Fallback rows degrade to base fee; large fallback-notional share means the dynamic premium is intentionally disabled for those swaps.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: OracleHealth, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")


def _decision_health(
    label: str,
    rows: list[sqlite3.Row],
    truth_rows: list[sqlite3.Row],
    markout_e6: int,
    total_notional_e6: int,
) -> DecisionHealth:
    reason_key = f"{label}_fallback_reason"
    extra_key = f"{label}_extra_e6"
    premium_key = f"{label}_premium_pips"
    fallback = [row for row in rows if row[reason_key]]
    charged = [row for row in rows if int(row[premium_key] or 0) > 0]
    truth_charged = [row for row in truth_rows if int(row[premium_key] or 0) > 0]
    premium_total = sum(int(row[extra_key] or 0) for row in truth_charged)
    premium_correct = sum(int(row[extra_key] or 0) for row in truth_charged if int(row["truth_corr"] or 0) == 1)
    truth_extra = sum(int(row[extra_key] or 0) for row in truth_rows)
    fallback_notional = sum(abs(int(row["aq_e6"])) for row in fallback)
    return DecisionHealth(
        label=label,
        rows=len(rows),
        fallback_rows=len(fallback),
        fallback_notional_e6=fallback_notional,
        fallback_notional_share=(fallback_notional / total_notional_e6) if total_notional_e6 else 0.0,
        charged_rows=len(charged),
        extra_e6=sum(int(row[extra_key] or 0) for row in rows),
        precision=(premium_correct / premium_total) if premium_total else None,
        truth_capture=(truth_extra / abs(markout_e6)) if markout_e6 else None,
        fallback_counts=dict(Counter(str(row[reason_key]) for row in fallback)),
    )


def _pctl(values: list[int], pct: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[(len(ordered) * pct) // 100]


def _gap_minutes(conn: sqlite3.Connection) -> float:
    rows = conn.execute("SELECT start_ms, end_ms FROM gaps WHERE end_ms IS NOT NULL").fetchall()
    return sum((int(row["end_ms"]) - int(row["start_ms"])) / 60_000 for row in rows)


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _seconds(value_ms: int | None) -> str:
    if value_ms is None:
        return "n/a"
    return f"{value_ms / 1000:.3f}s"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def _counter(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ", ".join(f"{key}:{counts[key]}" for key in sorted(counts))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Measure oracle-health economic exposure in a shadow DB")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "oracle_health.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "oracle_health.json")
    args = parser.parse_args()
    report = compute(args.database)
    write_outputs(report, args.out_md, args.out_json)
    print(f"oracle health: swaps={report.swaps} pyth={report.pyth_health_rows}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
