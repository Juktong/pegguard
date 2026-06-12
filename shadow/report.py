from __future__ import annotations

import argparse
import sqlite3
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import constants as C
from .db import connect


DECISIONS = ("fresh", "lag2", "lag5")


def emit_reports(conn: sqlite3.Connection, output_dir: Path, now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    daily_dir = output_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    daily = _render(conn, day=day, since_start=False)
    summary = _render(conn, day=None, since_start=True)
    (daily_dir / f"{day}.md").write_text(daily, encoding="utf-8")
    (output_dir / "summary.md").write_text(summary, encoding="utf-8")


def _render(conn: sqlite3.Connection, day: str | None, since_start: bool) -> str:
    where = ""
    params: tuple[object, ...] = ()
    title = "Shadow Summary" if since_start else f"Shadow Daily {day}"
    if day is not None:
        start = int(datetime.fromisoformat(f"{day}T00:00:00+00:00").timestamp() * 1000)
        end = start + 86_400_000
        where = "WHERE l.ts_ms >= ? AND l.ts_ms < ?"
        params = (start, end)

    rows = conn.execute(f"SELECT l.*, t.truth_corr, t.truth_mk_e6, t.valid FROM ledger l LEFT JOIN truth t ON t.ledger_id=l.id {where}", params).fetchall()
    truth_rows = [row for row in rows if row["valid"]]
    swaps = len(rows)
    notional_e6 = sum(abs(int(row["aq_e6"])) for row in rows)
    markout_e6 = sum(int(row["truth_mk_e6"] or 0) for row in truth_rows)
    duration_hours = _duration_hours(rows)

    lines = [
        f"# {title}",
        "",
        '"same-swaps upper bound; route-away elasticity is not observable in shadow mode."',
        "",
        f"- Swaps: {swaps}",
        f"- Valid truth rows: {len(truth_rows)} ({_pct(len(truth_rows), swaps)})",
        f"- Observed swap span: {duration_hours:.2f} hours",
        f"- Notional: {_usd(notional_e6)}",
        f"- LP static markout, truth: {_usd(markout_e6)}",
        "",
        "## Fee Decisions",
        "",
        "| Decision | Extra | Truth capture | Precision | Fallbacks |",
        "|---|---:|---:|---:|---|",
    ]
    for label in DECISIONS:
        extra = sum(int(row[f"{label}_extra_e6"] or 0) for row in rows)
        truth_extra = sum(int(row[f"{label}_extra_e6"] or 0) for row in truth_rows)
        correct = sum(int(row[f"{label}_extra_e6"] or 0) for row in truth_rows if int(row["truth_corr"] or 0) == 1)
        total = sum(int(row[f"{label}_extra_e6"] or 0) for row in truth_rows if int(row[f"{label}_premium_pips"] or 0) > 0)
        fallbacks = Counter((row[f"{label}_fallback_reason"] or "priced") for row in rows)
        lines.append(
            f"| {label} | {_usd(extra)} | {_pct(truth_extra, abs(markout_e6))} | "
            f"{_pct(correct, total)} | {_format_counter(fallbacks)} |"
        )

    staleness = [int(row["oracle_staleness_observed_ms"]) for row in rows if row["oracle_staleness_observed_ms"] is not None]
    pyth_lags = _pyth_lags(conn, day)
    gap_minutes = _gap_minutes(conn, day)
    lines.extend(
        [
            "",
            "## Operations",
            "",
            f"- Regime flips: {_count(conn, 'regime_events', day)}",
            f"- Sentinel triggers: {_count(conn, 'sentinel_triggers', day)}",
            f"- Observed Pyth staleness p50/p90: {_pctl(staleness, 50)} / {_pctl(staleness, 90)}",
            f"- Pyth feed lag p50/p90: {_pctl(pyth_lags, 50)} / {_pctl(pyth_lags, 90)}",
            f"- Gap minutes: {gap_minutes:.2f}",
            "",
        ]
    )
    return "\n".join(lines)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    value = abs(value_e6)
    return f"{sign}${value / 1_000_000:,.2f}"


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "n/a"
    return f"{(num * 100) / den:.2f}%"


def _duration_hours(rows: list[sqlite3.Row]) -> float:
    if len(rows) < 2:
        return 0.0
    start = min(int(row["ts_ms"]) for row in rows)
    end = max(int(row["ts_ms"]) for row in rows)
    return max(0, end - start) / 3_600_000


def _format_counter(counter: Counter[str]) -> str:
    if not counter:
        return "none"
    return ", ".join(f"{key}:{value}" for key, value in sorted(counter.items()))


def _pctl(values: list[int], pct: int) -> str:
    if not values:
        return "n/a"
    ordered = sorted(values)
    value = ordered[(len(ordered) * pct) // 100]
    return f"{value / 1000:.3f}s"


def _count(conn: sqlite3.Connection, table: str, day: str | None) -> int:
    if day is None:
        return int(conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])
    start = int(datetime.fromisoformat(f"{day}T00:00:00+00:00").timestamp() * 1000)
    end = start + 86_400_000
    return int(conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE ts_ms >= ? AND ts_ms < ?", (start, end)).fetchone()["n"])


def _pyth_lags(conn: sqlite3.Connection, day: str | None) -> list[int]:
    if day is None:
        rows = conn.execute("SELECT lag_ms FROM pyth_health").fetchall()
    else:
        start = int(datetime.fromisoformat(f"{day}T00:00:00+00:00").timestamp() * 1000)
        end = start + 86_400_000
        rows = conn.execute("SELECT lag_ms FROM pyth_health WHERE observed_ms >= ? AND observed_ms < ?", (start, end)).fetchall()
    return [int(row["lag_ms"]) for row in rows]


def _gap_minutes(conn: sqlite3.Connection, day: str | None) -> float:
    if day is None:
        rows = conn.execute("SELECT start_ms, end_ms FROM gaps WHERE end_ms IS NOT NULL").fetchall()
    else:
        start = int(datetime.fromisoformat(f"{day}T00:00:00+00:00").timestamp() * 1000)
        end = start + 86_400_000
        rows = conn.execute(
            "SELECT start_ms, end_ms FROM gaps WHERE end_ms IS NOT NULL AND start_ms < ? AND end_ms > ?",
            (end, start),
        ).fetchall()
    return sum((int(row["end_ms"]) - int(row["start_ms"])) / 60_000 for row in rows)


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Regenerate PegGuard shadow reports from SQLite")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--reports", type=Path, default=root / "docs" / "shadow")
    args = parser.parse_args()
    conn = connect(args.database)
    try:
        emit_reports(conn, args.reports)
    finally:
        conn.close()
    print(f"wrote {args.reports / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
