from __future__ import annotations

import argparse
import asyncio
import sqlite3
import time
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

import aiohttp

from . import constants as C
from .alpha_sweep import parse_alpha
from .pipeline import Decision, OracleSnapshot, Regime, SignalPipeline, SwapInput, div_toward_zero, is_correcting, median_int
from .pyth import PythBuffer, PythClient
from .rpc import RpcWs, decode_swap_log
from .sentinel import SentinelMirror


DEFAULT_POOL = "arb-weth-usdc-500,0xc6962004f452be9203591991d15f6b388e09e8d0,18,6"


@dataclass(frozen=True)
class PoolSpec:
    name: str
    address: str
    token0_decimals: int
    token1_decimals: int


@dataclass(frozen=True)
class Candidate:
    name: str
    alpha: Fraction


def _now_ms() -> int:
    return int(time.time() * 1000)


def parse_pool(value: str) -> PoolSpec:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("pool must be name,address,token0_decimals,token1_decimals")
    return PoolSpec(parts[0], parts[1].lower(), int(parts[2]), int(parts[3]))


def _scale_signed(value: int, from_decimals: int, to_decimals: int) -> int:
    delta = to_decimals - from_decimals
    if delta >= 0:
        return value * (10**delta)
    return div_toward_zero(value, 10 ** (-delta))


def _post_mid_e18(sqrt_price_x96: int, token0_decimals: int, token1_decimals: int) -> int:
    raw = sqrt_price_x96 * sqrt_price_x96
    scale_power = 18 + token0_decimals - token1_decimals
    if scale_power >= 0:
        return (raw * (10**scale_power)) // (1 << 192)
    return raw // ((1 << 192) * (10 ** (-scale_power)))


def init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS pools (
            name TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            token0_decimals INTEGER NOT NULL,
            token1_decimals INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS candidates (
            name TEXT PRIMARY KEY,
            alpha_num INTEGER NOT NULL,
            alpha_den INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS swaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pool TEXT NOT NULL,
            ts_ms INTEGER NOT NULL,
            block_number INTEGER NOT NULL,
            tx_hash TEXT NOT NULL,
            log_index INTEGER NOT NULL,
            pre_mid_e18 TEXT NOT NULL,
            post_mid_e18 TEXT NOT NULL,
            ab_e18 TEXT NOT NULL,
            aq_e6 INTEGER NOT NULL,
            regime TEXT NOT NULL,
            oracle_staleness_ms INTEGER,
            conf_e2 INTEGER,
            fresh_publish_time_ms INTEGER,
            fresh_fair_e18 TEXT,
            fresh_fallback_reason TEXT,
            created_at_ms INTEGER NOT NULL,
            UNIQUE(pool, block_number, tx_hash, log_index)
        );
        CREATE TABLE IF NOT EXISTS decisions (
            swap_id INTEGER NOT NULL,
            candidate TEXT NOT NULL,
            dev_e2 INTEGER NOT NULL,
            correcting INTEGER NOT NULL,
            premium_pips INTEGER NOT NULL,
            extra_e6 INTEGER NOT NULL,
            fallback_reason TEXT NOT NULL,
            PRIMARY KEY(swap_id, candidate),
            FOREIGN KEY(swap_id) REFERENCES swaps(id)
        );
        CREATE TABLE IF NOT EXISTS truth (
            swap_id INTEGER PRIMARY KEY,
            valid INTEGER NOT NULL,
            truth_basis_e18 TEXT,
            truth_dev_e2 INTEGER,
            truth_corr INTEGER,
            truth_mk_e6 INTEGER,
            computed_at_ms INTEGER NOT NULL,
            FOREIGN KEY(swap_id) REFERENCES swaps(id)
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
        """
    )
    conn.commit()
    return conn


def register_metadata(conn: sqlite3.Connection, pools: list[PoolSpec], candidates: list[Candidate]) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO pools (name, address, token0_decimals, token1_decimals) VALUES (?, ?, ?, ?)",
        [(pool.name, pool.address, pool.token0_decimals, pool.token1_decimals) for pool in pools],
    )
    conn.executemany(
        "INSERT OR REPLACE INTO candidates (name, alpha_num, alpha_den) VALUES (?, ?, ?)",
        [(candidate.name, candidate.alpha.numerator, candidate.alpha.denominator) for candidate in candidates],
    )
    conn.commit()


async def run_live(args: argparse.Namespace) -> None:
    pools = [parse_pool(value) for value in args.pool]
    candidates = [Candidate(f"alpha_{str(alpha).replace('/', '_')}", alpha) for alpha in [parse_alpha(value) for value in args.alphas.split(",")]]
    conn = init_db(args.database)
    register_metadata(conn, pools, candidates)

    stop = asyncio.Event()
    pyth_buffer = PythBuffer()
    sentinel = SentinelMirror()
    states: dict[tuple[str, str], SignalPipeline] = {
        (pool.name, candidate.name): SignalPipeline(alpha_num=candidate.alpha.numerator, alpha_den=candidate.alpha.denominator)
        for pool in pools
        for candidate in candidates
    }
    ts_cache: dict[tuple[str, int], int] = {}

    async with aiohttp.ClientSession(headers={"user-agent": "pegguard-live-alpha/0.1", "accept-encoding": "gzip, deflate"}) as session:
        pyth_client = PythClient(
            feed_id=args.pyth_feed_id,
            base_url=args.hermes_base_url,
            buffer=pyth_buffer,
            session=session,
        )
        tasks = [asyncio.create_task(pyth_client.run(), name="pyth")]
        tasks.extend(
            asyncio.create_task(_pool_loop(args, conn, pool, candidates, states, pyth_buffer, ts_cache, stop), name=f"pool-{pool.name}")
            for pool in pools
        )
        tasks.append(asyncio.create_task(_sentinel_loop(args, conn, states, sentinel, stop), name="sentinel"))
        try:
            await asyncio.wait_for(stop.wait(), timeout=args.duration_sec)
        except TimeoutError:
            stop.set()
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task
            compute_truth(conn, truth_delay_sec=args.truth_delay_sec, window_sec=args.truth_window_sec)
            emit_report(conn, args.report_dir)
            conn.close()


async def _pool_loop(
    args: argparse.Namespace,
    conn: sqlite3.Connection,
    pool: PoolSpec,
    candidates: list[Candidate],
    states: dict[tuple[str, str], SignalPipeline],
    pyth_buffer: PythBuffer,
    ts_cache: dict[tuple[str, int], int],
    stop: asyncio.Event,
) -> None:
    rpc = RpcWs([args.arbitrum_wss_primary, args.arbitrum_wss_fallback], f"arbitrum-{pool.name}")
    call_ws = None
    gaps = GapRecorder(conn, f"target-{pool.name}")
    async for raw in rpc.subscribe_logs(pool.address, on_gap_start=gaps.start, on_gap_end=gaps.end):
        if stop.is_set():
            break
        log = decode_swap_log(raw)
        if log.address.lower() != pool.address:
            continue
        if call_ws is None:
            call_ws = await rpc.connect()
        cache_key = (pool.name, log.block_number)
        try:
            ts_ms = ts_cache.get(cache_key)
            if ts_ms is None:
                ts_ms = await rpc.block_timestamp_ms(call_ws, log.block_number)
                ts_cache[cache_key] = ts_ms
        except Exception:
            with suppress(Exception):
                await call_ws.close()
            call_ws = await rpc.connect()
            ts_ms = await rpc.block_timestamp_ms(call_ws, log.block_number)
            ts_cache[cache_key] = ts_ms

        fair = pyth_buffer.as_of(ts_ms)
        first_state = states[(pool.name, candidates[0].name)]
        pre_mid = first_state.state.prev_mid_e18
        swap = SwapInput(
            ts_ms=ts_ms,
            pre_mid_e18=pre_mid,
            post_mid_e18=_post_mid_e18(log.sqrt_price_x96, pool.token0_decimals, pool.token1_decimals),
            ab_e18=_scale_signed(log.amount0, pool.token0_decimals, 18),
            aq_e6=_scale_signed(log.amount1, pool.token1_decimals, 6),
            block_number=log.block_number,
            tx_hash=log.tx_hash,
            log_index=log.log_index,
        )
        regime = first_state.state.effective_regime(ts_ms).value
        decisions: dict[str, Decision] = {}
        for candidate in candidates:
            pipeline = states[(pool.name, candidate.name)]
            result = pipeline.process_swap(swap, {"fresh": fair}, fair)
            decisions[candidate.name] = result["fresh"]

        swap_id = insert_swap(conn, pool.name, swap, regime, decisions[candidates[0].name])
        for candidate in candidates:
            insert_decision(conn, swap_id, candidate.name, decisions[candidate.name])
        conn.commit()


async def _sentinel_loop(
    args: argparse.Namespace,
    conn: sqlite3.Connection,
    states: dict[tuple[str, str], SignalPipeline],
    sentinel: SentinelMirror,
    stop: asyncio.Event,
) -> None:
    rpc = RpcWs([args.mainnet_wss_primary, args.mainnet_wss_fallback], "mainnet-sentinel")
    call_ws = None
    ts_cache: dict[int, int] = {}
    gaps = GapRecorder(conn, "sentinel-mainnet")
    async for raw in rpc.subscribe_logs(args.sentinel_pool.lower(), on_gap_start=gaps.start, on_gap_end=gaps.end):
        if stop.is_set():
            break
        log = decode_swap_log(raw)
        if log.address.lower() != args.sentinel_pool.lower():
            continue
        if call_ws is None:
            call_ws = await rpc.connect()
        try:
            ts_ms = ts_cache.get(log.block_number)
            if ts_ms is None:
                ts_ms = await rpc.block_timestamp_ms(call_ws, log.block_number)
                ts_cache[log.block_number] = ts_ms
        except Exception:
            with suppress(Exception):
                await call_ws.close()
            call_ws = await rpc.connect()
            ts_ms = await rpc.block_timestamp_ms(call_ws, log.block_number)
            ts_cache[log.block_number] = ts_ms

        result = sentinel.observe(ts_ms, log.sentinel_price_value)
        if not result.triggered:
            continue
        expiry_ms = ts_ms + C.REGIME_TTL_SEC * 1000
        for pipeline in states.values():
            pipeline.set_volatile(ts_ms)
        conn.execute(
            """
            INSERT INTO sentinel_triggers (ts_ms, block_number, tx_hash, log_index, move_bps, trig_bps, window_sec, expiry_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts_ms, log.block_number, log.tx_hash, log.log_index, result.move_bps, sentinel.trig_bps, sentinel.window_sec, expiry_ms),
        )
        conn.commit()


def insert_swap(conn: sqlite3.Connection, pool: str, swap: SwapInput, regime: str, decision: Decision) -> int:
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO swaps
            (pool, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18, ab_e18, aq_e6,
             regime, oracle_staleness_ms, conf_e2, fresh_publish_time_ms, fresh_fair_e18, fresh_fallback_reason, created_at_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pool,
            swap.ts_ms,
            swap.block_number or 0,
            swap.tx_hash or "",
            swap.log_index or 0,
            str(swap.pre_mid_e18),
            str(swap.post_mid_e18),
            str(swap.ab_e18),
            swap.aq_e6,
            regime,
            decision.staleness_ms,
            decision.conf_e2,
            decision.publish_time_ms,
            str(decision.fair_e18) if decision.fair_e18 is not None else None,
            decision.fallback_reason,
            _now_ms(),
        ),
    )
    if cur.rowcount:
        return int(cur.lastrowid)
    row = conn.execute(
        "SELECT id FROM swaps WHERE pool=? AND block_number=? AND tx_hash=? AND log_index=?",
        (pool, swap.block_number or 0, swap.tx_hash or "", swap.log_index or 0),
    ).fetchone()
    return int(row["id"])


def insert_decision(conn: sqlite3.Connection, swap_id: int, candidate: str, decision: Decision) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO decisions
            (swap_id, candidate, dev_e2, correcting, premium_pips, extra_e6, fallback_reason)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (swap_id, candidate, decision.dev_e2, 1 if decision.correcting else 0, decision.premium_pips, decision.extra_e6, decision.fallback_reason),
    )


class GapRecorder:
    def __init__(self, conn: sqlite3.Connection, source: str) -> None:
        self.conn = conn
        self.source = source
        self.current_id: int | None = None

    async def start(self, last_block: int | None) -> None:
        if self.current_id is not None:
            return
        cur = self.conn.execute(
            "INSERT INTO gaps (source, start_ms, last_block, recovered) VALUES (?, ?, ?, 0)",
            (self.source, _now_ms(), last_block),
        )
        self.conn.commit()
        self.current_id = int(cur.lastrowid)

    async def end(self, recovered: bool) -> None:
        if self.current_id is None:
            return
        self.conn.execute(
            "UPDATE gaps SET end_ms=?, recovered=? WHERE id=?",
            (_now_ms(), 1 if recovered else 0, self.current_id),
        )
        self.conn.commit()
        self.current_id = None


def compute_truth(conn: sqlite3.Connection, truth_delay_sec: int, window_sec: int) -> int:
    now_ms = _now_ms()
    cutoff = now_ms - truth_delay_sec * 1000
    rows = conn.execute(
        """
        SELECT *
        FROM swaps
        WHERE ts_ms <= ?
          AND fresh_fair_e18 IS NOT NULL
          AND fresh_fallback_reason = ''
        ORDER BY pool, ts_ms, id
        """,
        (cutoff,),
    ).fetchall()
    count = 0
    for row in rows:
        peers = conn.execute(
            """
            SELECT post_mid_e18, fresh_fair_e18
            FROM swaps
            WHERE pool = ?
              AND ts_ms BETWEEN ? AND ?
              AND fresh_fair_e18 IS NOT NULL
              AND fresh_fallback_reason = ''
            """,
            (row["pool"], int(row["ts_ms"]) - window_sec * 1000, int(row["ts_ms"]) + window_sec * 1000),
        ).fetchall()
        ratios = []
        for peer in peers:
            fair = int(peer["fresh_fair_e18"])
            if fair > 0:
                ratios.append((int(peer["post_mid_e18"]) * C.WAD) // fair)
        if not ratios:
            continue
        basis = median_int(ratios)
        pre_mid = int(row["pre_mid_e18"])
        fair = int(row["fresh_fair_e18"])
        fair_local = (fair * basis) // C.WAD
        dev_e2 = ((fair_local * 1_000_000) // pre_mid) - 1_000_000 if pre_mid > 0 else 0
        corr = 1 if is_correcting(dev_e2, int(row["ab_e18"]) > 0) else 0
        markout_e6 = div_toward_zero(int(row["ab_e18"]) * fair_local, 10**30) + int(row["aq_e6"])
        conn.execute(
            """
            INSERT OR REPLACE INTO truth
                (swap_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (int(row["id"]), 1 if pre_mid > 0 else 0, str(basis), dev_e2, corr, markout_e6, now_ms),
        )
        count += 1
    conn.commit()
    return count


def emit_report(conn: sqlite3.Connection, report_dir: Path) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "summary.md").write_text(render_report(conn), encoding="utf-8")


def render_report(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT COUNT(*) AS n, SUM(abs(aq_e6)) AS notional FROM swaps").fetchone()
    truth_rows = conn.execute("SELECT COUNT(*) AS n FROM truth WHERE valid=1").fetchone()
    lines = [
        "# Live Alpha Shadow Report",
        "",
        '"same-swaps upper bound; route-away elasticity is not observable in shadow mode."',
        "",
        f"- Swaps: {int(rows['n'] or 0)}",
        f"- Notional: {_usd(int(rows['notional'] or 0))}",
        f"- Truth-scored swaps: {int(truth_rows['n'] or 0)}",
        f"- Sentinel triggers: {_count(conn, 'sentinel_triggers')}",
        f"- Gap minutes: {_gap_minutes(conn):.2f}",
        "",
        "## Candidate Performance",
        "",
        "| Pool | Candidate | Alpha | Swaps | Truth rows | Extra | Truth capture | Precision | Fallbacks |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    candidates = conn.execute("SELECT * FROM candidates ORDER BY name").fetchall()
    pools = conn.execute("SELECT * FROM pools ORDER BY name").fetchall()
    for pool in pools:
        for candidate in candidates:
            metrics = _candidate_metrics(conn, pool["name"], candidate["name"])
            alpha = Fraction(int(candidate["alpha_num"]), int(candidate["alpha_den"]))
            lines.append(
                f"| {pool['name']} | {candidate['name']} | {alpha} | {metrics['swaps']} | {metrics['truth_rows']} | "
                f"{_usd(metrics['extra'])} | {_pct(metrics['truth_extra'], abs(metrics['markout']))} | "
                f"{_pct(metrics['correct'], metrics['premium_total'])} | {metrics['fallbacks']} |"
            )
    lines.append("")
    return "\n".join(lines)


def _candidate_metrics(conn: sqlite3.Connection, pool: str, candidate: str) -> dict[str, Any]:
    row = conn.execute("SELECT COUNT(*) AS n FROM swaps WHERE pool=?", (pool,)).fetchone()
    swaps = int(row["n"] or 0)
    truth = conn.execute(
        """
        SELECT COUNT(*) AS truth_rows,
               SUM(t.truth_mk_e6) AS markout,
               SUM(d.extra_e6) AS truth_extra,
               SUM(CASE WHEN t.truth_corr=1 THEN d.extra_e6 ELSE 0 END) AS correct,
               SUM(CASE WHEN d.premium_pips>0 THEN d.extra_e6 ELSE 0 END) AS premium_total
        FROM truth t
        JOIN swaps s ON s.id = t.swap_id
        JOIN decisions d ON d.swap_id = s.id
        WHERE s.pool=? AND d.candidate=? AND t.valid=1
        """,
        (pool, candidate),
    ).fetchone()
    extra = conn.execute(
        """
        SELECT SUM(d.extra_e6) AS extra
        FROM swaps s
        JOIN decisions d ON d.swap_id=s.id
        WHERE s.pool=? AND d.candidate=?
        """,
        (pool, candidate),
    ).fetchone()
    fallbacks = conn.execute(
        """
        SELECT d.fallback_reason AS reason, COUNT(*) AS n
        FROM swaps s
        JOIN decisions d ON d.swap_id=s.id
        WHERE s.pool=? AND d.candidate=?
        GROUP BY d.fallback_reason
        ORDER BY n DESC
        """,
        (pool, candidate),
    ).fetchall()
    return {
        "swaps": swaps,
        "truth_rows": int(truth["truth_rows"] or 0),
        "markout": int(truth["markout"] or 0),
        "truth_extra": int(truth["truth_extra"] or 0),
        "correct": int(truth["correct"] or 0),
        "premium_total": int(truth["premium_total"] or 0),
        "extra": int(extra["extra"] or 0),
        "fallbacks": ", ".join(f"{row['reason'] or 'priced'}:{row['n']}" for row in fallbacks) or "none",
    }


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(num: int, den: int) -> str:
    if den == 0:
        return "n/a"
    return f"{(num * 100) / den:.2f}%"


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"])


def _gap_minutes(conn: sqlite3.Connection) -> float:
    rows = conn.execute("SELECT start_ms, end_ms FROM gaps WHERE end_ms IS NOT NULL").fetchall()
    return sum((int(row["end_ms"]) - int(row["start_ms"])) / 60_000 for row in rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run side-by-side live PegGuard alpha candidates")
    parser.add_argument("--pool", action="append", default=[], help="name,address,token0_decimals,token1_decimals")
    parser.add_argument("--alphas", default="1/2", help="comma-separated alpha fractions")
    parser.add_argument("--duration-sec", type=int, default=1800)
    parser.add_argument("--truth-delay-sec", type=int, default=360)
    parser.add_argument("--truth-window-sec", type=int, default=300)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--arbitrum-wss-primary", default="wss://arbitrum-one-rpc.publicnode.com")
    parser.add_argument("--arbitrum-wss-fallback", default="")
    parser.add_argument("--mainnet-wss-primary", default="wss://ethereum-rpc.publicnode.com")
    parser.add_argument("--mainnet-wss-fallback", default="")
    parser.add_argument("--sentinel-pool", default=C.SENTINEL_POOL)
    parser.add_argument("--pyth-feed-id", default=C.PYTH_ETH_USD_FEED_ID)
    parser.add_argument("--hermes-base-url", default="https://hermes.pyth.network")
    args = parser.parse_args()
    if not args.pool:
        args.pool = [DEFAULT_POOL]
    return args


def main() -> None:
    raise SystemExit(asyncio.run(run_live(parse_args())))


if __name__ == "__main__":
    main()
