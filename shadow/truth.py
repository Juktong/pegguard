from __future__ import annotations

import sqlite3
import time

from . import constants as C
from .db import insert_truth
from .pipeline import div_toward_zero, is_correcting, median_int


def process_delayed_truth(conn: sqlite3.Connection, now_ms: int | None = None, delay_sec: int = 360, window_sec: int = 300) -> int:
    now_ms = now_ms or int(time.time() * 1000)
    cutoff_ms = now_ms - delay_sec * 1000
    # Ex-post truth labeling is not a hot-path pricing decision. Rows that
    # correctly fell back because their oracle was stale can still receive a
    # truth label when a fair price is recorded for post-run economics.
    pending = conn.execute(
        """
        SELECT l.*
        FROM ledger l
        LEFT JOIN truth t ON t.ledger_id = l.id
        WHERE t.ledger_id IS NULL
          AND l.ts_ms <= ?
          AND l.fresh_fair_e18 IS NOT NULL
        ORDER BY l.ts_ms
        LIMIT 500
        """,
        (cutoff_ms,),
    ).fetchall()
    count = 0
    for row in pending:
        if _compute_one(conn, row, now_ms, window_sec):
            count += 1
    return count


def _compute_one(conn: sqlite3.Connection, row: sqlite3.Row, now_ms: int, window_sec: int) -> bool:
    ts_ms = int(row["ts_ms"])
    peers = conn.execute(
        """
        SELECT post_mid_e18, fresh_fair_e18
        FROM ledger
        WHERE ts_ms BETWEEN ? AND ?
          AND fresh_fair_e18 IS NOT NULL
        """,
        (ts_ms - window_sec * 1000, ts_ms + window_sec * 1000),
    ).fetchall()
    ratios: list[int] = []
    for peer in peers:
        fair = int(peer["fresh_fair_e18"])
        if fair > 0:
            ratios.append((int(peer["post_mid_e18"]) * C.WAD) // fair)
    if not ratios:
        return False

    basis = median_int(ratios)
    pre_mid = int(row["pre_mid_e18"])
    fair = int(row["fresh_fair_e18"])
    fair_local = (fair * basis) // C.WAD
    dev_e2 = ((fair_local * 1_000_000) // pre_mid) - 1_000_000 if pre_mid > 0 else 0
    zero_for_one = bool(row["zero_for_one"])
    corr = 1 if is_correcting(dev_e2, zero_for_one) else 0
    markout_e6 = div_toward_zero(int(row["ab_e18"]) * fair_local, 10**30) + int(row["aq_e6"])
    insert_truth(
        conn,
        {
            "ledger_id": int(row["id"]),
            "valid": 1 if pre_mid > 0 else 0,
            "truth_basis_e18": str(basis),
            "truth_dev_e2": dev_e2,
            "truth_corr": corr,
            "truth_mk_e6": markout_e6,
            "computed_at_ms": now_ms,
        },
    )
    return True
