from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    observed: str
    required: str


@dataclass(frozen=True)
class Status:
    database: str
    swaps: int
    valid_truth_rows: int
    truth_coverage: float
    observed_span_hours: float
    min_span_hours: float
    remaining_span_hours: float
    notional_e6: int
    markout_e6: int
    extra_e6: int
    precision: float | None
    truth_capture: float | None
    pyth_health_rows: int
    gap_minutes: float
    gates: list[Gate]

    @property
    def complete(self) -> bool:
        return all(gate.passed for gate in self.gates)


def compute_status(db: Path, min_hours: float = 24.0, min_truth_coverage: float = 0.80, min_swaps: int = 1) -> Status:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        swaps = int(conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0])
        pyth_health_rows = int(conn.execute("SELECT COUNT(*) FROM pyth_health").fetchone()[0])
        truth_rows = int(conn.execute("SELECT COUNT(*) FROM truth WHERE valid=1").fetchone()[0])
        times = conn.execute("SELECT MIN(ts_ms) AS start_ms, MAX(ts_ms) AS end_ms FROM ledger").fetchone()
        start_ms = int(times["start_ms"] or 0)
        end_ms = int(times["end_ms"] or 0)
        span_hours = max(0, end_ms - start_ms) / 3_600_000 if swaps > 1 else 0.0
        notional = int(conn.execute("SELECT COALESCE(SUM(ABS(aq_e6)), 0) FROM ledger").fetchone()[0] or 0)
        extra = int(conn.execute("SELECT COALESCE(SUM(fresh_extra_e6), 0) FROM ledger").fetchone()[0] or 0)
        truth = conn.execute(
            """
            SELECT
                COALESCE(SUM(t.truth_mk_e6), 0) AS markout,
                COALESCE(SUM(CASE WHEN l.fresh_premium_pips > 0 THEN l.fresh_extra_e6 ELSE 0 END), 0) AS premium,
                COALESCE(SUM(CASE WHEN l.fresh_premium_pips > 0 AND t.truth_corr = 1 THEN l.fresh_extra_e6 ELSE 0 END), 0) AS correct_premium
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            """
        ).fetchone()
        markout = int(truth["markout"] or 0)
        premium = int(truth["premium"] or 0)
        correct_premium = int(truth["correct_premium"] or 0)
        precision = correct_premium / premium if premium else None
        capture = extra / abs(markout) if markout else None
        gap_minutes = _gap_minutes(conn)
    finally:
        conn.close()

    truth_coverage = truth_rows / swaps if swaps else 0.0
    remaining_span_hours = max(0.0, min_hours - span_hours)
    gates = [
        Gate("minimum swaps", swaps >= min_swaps, str(swaps), f">= {min_swaps}"),
        Gate("observed span", span_hours >= min_hours, f"{span_hours:.2f}h", f">= {min_hours:.2f}h"),
        Gate("truth coverage", truth_coverage >= min_truth_coverage, f"{truth_coverage:.2%}", f">= {min_truth_coverage:.0%}"),
        Gate("valid truth rows", truth_rows > 0, str(truth_rows), "> 0"),
    ]
    return Status(
        database=str(db),
        swaps=swaps,
        valid_truth_rows=truth_rows,
        truth_coverage=truth_coverage,
        observed_span_hours=span_hours,
        min_span_hours=min_hours,
        remaining_span_hours=remaining_span_hours,
        notional_e6=notional,
        markout_e6=markout,
        extra_e6=extra,
        precision=precision,
        truth_capture=capture,
        pyth_health_rows=pyth_health_rows,
        gap_minutes=gap_minutes,
        gates=gates,
    )


def markdown(status: Status) -> str:
    lines = [
        "# Live Shadow Status",
        "",
        f"- Database: `{status.database}`",
        f"- Status: {'complete' if status.complete else 'in progress'}",
        f"- Swaps: {status.swaps}",
        f"- Valid truth rows: {status.valid_truth_rows} ({status.truth_coverage:.2%})",
        f"- Observed swap span: {status.observed_span_hours:.2f} hours",
        f"- Required swap span: {status.min_span_hours:.2f} hours",
        f"- Remaining span required: {status.remaining_span_hours:.2f} hours",
        f"- Notional: {_usd(status.notional_e6)}",
        f"- Extra premium: {_usd(status.extra_e6)}",
        f"- Truth markout: {_usd(status.markout_e6)}",
        f"- Precision: {_pct_or_na(status.precision)}",
        f"- Truth capture: {_pct_or_na(status.truth_capture)}",
        f"- Pyth health rows: {status.pyth_health_rows}",
        f"- Gap minutes: {status.gap_minutes:.2f}",
        "",
        "## Gates",
        "",
        "| Gate | Observed | Required | Passed |",
        "|---|---:|---:|---:|",
    ]
    for gate in status.gates:
        lines.append(f"| {gate.name} | {gate.observed} | {gate.required} | {'yes' if gate.passed else 'no'} |")
    lines.extend(
        [
            "",
            "A complete 24h economic sample requires all gates to pass. The true route-away elasticity test remains separate from this live-shadow gate.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(status: Status, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(status), encoding="utf-8")
    payload = asdict(status)
    payload["complete"] = status.complete
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _gap_minutes(conn: sqlite3.Connection) -> float:
    rows = conn.execute("SELECT start_ms, end_ms FROM gaps WHERE end_ms IS NOT NULL").fetchall()
    return sum((int(row["end_ms"]) - int(row["start_ms"])) / 60_000 for row in rows)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct_or_na(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check live shadow economic evidence gates")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--min-hours", type=float, default=24.0)
    parser.add_argument("--min-truth-coverage", type=float, default=0.80)
    parser.add_argument("--min-swaps", type=int, default=1)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--out-json", type=Path)
    args = parser.parse_args()

    status = compute_status(args.database, args.min_hours, args.min_truth_coverage, args.min_swaps)
    out_md = args.out_md or root / "docs" / "shadow" / "live_status.md"
    out_json = args.out_json or root / "docs" / "shadow" / "live_status.json"
    write_outputs(status, out_md, out_json)
    print(
        f"status={'complete' if status.complete else 'in-progress'} "
        f"swaps={status.swaps} span={status.observed_span_hours:.2f}h "
        f"remaining={status.remaining_span_hours:.2f}h truth={status.truth_coverage:.2%}"
    )
    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    return 0 if status.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
