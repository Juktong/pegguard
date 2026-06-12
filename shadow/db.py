from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Mapping


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    init(conn)
    return conn


def init(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_ms INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            tx_hash TEXT NOT NULL,
            log_index INTEGER NOT NULL,
            pre_mid_e18 TEXT NOT NULL,
            post_mid_e18 TEXT NOT NULL,
            ab_e18 TEXT NOT NULL,
            aq_e6 INTEGER NOT NULL,
            zero_for_one INTEGER NOT NULL,
            regime TEXT NOT NULL,
            oracle_staleness_observed_ms INTEGER,
            conf_e2 INTEGER,
            fresh_publish_time_ms INTEGER,
            fresh_fair_e18 TEXT,
            fresh_dev_e2 INTEGER,
            fresh_correcting INTEGER,
            fresh_premium_pips INTEGER,
            fresh_extra_e6 INTEGER,
            fresh_fallback_reason TEXT,
            lag2_publish_time_ms INTEGER,
            lag2_fair_e18 TEXT,
            lag2_dev_e2 INTEGER,
            lag2_correcting INTEGER,
            lag2_premium_pips INTEGER,
            lag2_extra_e6 INTEGER,
            lag2_fallback_reason TEXT,
            lag5_publish_time_ms INTEGER,
            lag5_fair_e18 TEXT,
            lag5_dev_e2 INTEGER,
            lag5_correcting INTEGER,
            lag5_premium_pips INTEGER,
            lag5_extra_e6 INTEGER,
            lag5_fallback_reason TEXT,
            created_at_ms INTEGER NOT NULL,
            UNIQUE(block_number, tx_hash, log_index)
        );

        CREATE TABLE IF NOT EXISTS truth (
            ledger_id INTEGER PRIMARY KEY,
            valid INTEGER NOT NULL,
            truth_basis_e18 TEXT,
            truth_dev_e2 INTEGER,
            truth_corr INTEGER,
            truth_mk_e6 INTEGER,
            computed_at_ms INTEGER NOT NULL,
            FOREIGN KEY(ledger_id) REFERENCES ledger(id)
        );

        CREATE TABLE IF NOT EXISTS regime_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_ms INTEGER NOT NULL,
            old_regime TEXT NOT NULL,
            new_regime TEXT NOT NULL,
            expiry_ms INTEGER,
            reason TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sentinel_triggers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts_ms INTEGER NOT NULL,
            block_number INTEGER,
            tx_hash TEXT,
            log_index INTEGER,
            move_bps INTEGER NOT NULL,
            trig_bps INTEGER NOT NULL,
            window_sec INTEGER NOT NULL,
            expiry_ms INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER,
            last_block INTEGER,
            recovered INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS pyth_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observed_ms INTEGER NOT NULL,
            publish_time_ms INTEGER NOT NULL,
            lag_ms INTEGER NOT NULL,
            price_e18 TEXT NOT NULL,
            conf_e2 INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS binance_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            observed_ms INTEGER NOT NULL,
            price_e18 TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS daemon_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    conn.commit()


def insert_ledger(conn: sqlite3.Connection, row: Mapping[str, object]) -> int | None:
    columns = list(row.keys())
    placeholders = ",".join("?" for _ in columns)
    sql = f"INSERT OR IGNORE INTO ledger ({','.join(columns)}) VALUES ({placeholders})"
    cur = conn.execute(sql, [row[c] for c in columns])
    conn.commit()
    if cur.rowcount == 0:
        existing = conn.execute(
            "SELECT id FROM ledger WHERE block_number=? AND tx_hash=? AND log_index=?",
            (row["block_number"], row["tx_hash"], row["log_index"]),
        ).fetchone()
        return int(existing["id"]) if existing else None
    return int(cur.lastrowid)


def insert_truth(conn: sqlite3.Connection, row: Mapping[str, object]) -> None:
    columns = list(row.keys())
    placeholders = ",".join("?" for _ in columns)
    updates = ",".join(f"{col}=excluded.{col}" for col in columns if col != "ledger_id")
    sql = f"INSERT INTO truth ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT(ledger_id) DO UPDATE SET {updates}"
    conn.execute(sql, [row[c] for c in columns])
    conn.commit()


def save_state(conn: sqlite3.Connection, values: Mapping[str, object]) -> None:
    conn.executemany(
        "INSERT INTO daemon_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        [(key, str(value)) for key, value in values.items()],
    )
    conn.commit()


def load_state(conn: sqlite3.Connection) -> dict[str, str]:
    return {str(row["key"]): str(row["value"]) for row in conn.execute("SELECT key, value FROM daemon_state")}
