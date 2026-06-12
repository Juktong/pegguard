from __future__ import annotations

import argparse
import asyncio
import signal
import sqlite3
import sys
import time
import tomllib
from contextlib import suppress
from decimal import Decimal
from pathlib import Path
from typing import Any

import aiohttp

from . import constants as C
from .db import connect, insert_ledger, load_state, save_state
from .parity import assert_parity
from .pipeline import Decision, Regime, SignalPipeline, SwapInput
from .pyth import PythBuffer, PythClient
from .report import emit_reports
from .rpc import RpcWs, decode_swap_log
from .sentinel import SentinelMirror
from .truth import process_delayed_truth


def _now_ms() -> int:
    return int(time.time() * 1000)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _path(root: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


async def main_async(args: argparse.Namespace) -> int:
    root = C.repo_root()
    config = load_config(args.config)

    parity = assert_parity(root)
    print(
        "parity ok: "
        f"calm precision={parity['calm'].precision_bps / 100:.2f}% capture={parity['calm'].capture_truth_bps / 100:.2f}%; "
        f"vol precision={parity['vol'].precision_bps / 100:.2f}% capture={parity['vol'].capture_truth_bps / 100:.2f}%"
    )
    if args.parity_only:
        return 0

    db_path = _path(root, args.database or config["paths"]["database"])
    report_dir = _path(root, args.reports or config["paths"]["reports"])
    conn = connect(db_path)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    pyth_buffer = PythBuffer()
    pipeline = SignalPipeline()
    _hydrate_pipeline(conn, pipeline)
    sentinel = SentinelMirror(
        trig_bps=int(config["sentinel"].get("trig_bps", C.RSC_TRIG_BPS)),
        window_sec=int(config["sentinel"].get("window_sec", C.RSC_WINDOW_SEC)),
    )

    async with aiohttp.ClientSession(headers={"user-agent": "pegguard-shadow/0.1", "accept-encoding": "gzip, deflate"}) as session:
        pyth_client = PythClient(
            feed_id=config["pyth"].get("feed_id", C.PYTH_ETH_USD_FEED_ID),
            base_url=config["pyth"].get("hermes_base_url", "https://hermes.pyth.network"),
            buffer=pyth_buffer,
            session=session,
        )
        tasks = [
            asyncio.create_task(pyth_client.run(), name="pyth"),
            asyncio.create_task(_write_pyth_health(conn, pyth_client), name="pyth-health"),
            asyncio.create_task(_target_loop(config, conn, pyth_buffer, pipeline, stop), name="target"),
            asyncio.create_task(_sentinel_loop(config, conn, pipeline, sentinel, stop), name="sentinel"),
            asyncio.create_task(_truth_report_loop(config, conn, report_dir, stop), name="truth-report"),
        ]
        if args.binance:
            tasks.append(asyncio.create_task(_binance_loop(conn, session, stop), name="binance"))
        for task in tasks:
            task.add_done_callback(lambda done: _surface_task_failure(done, stop))

        try:
            if args.duration_sec:
                try:
                    await asyncio.wait_for(stop.wait(), timeout=args.duration_sec)
                except TimeoutError:
                    stop.set()
            else:
                await stop.wait()
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with suppress(asyncio.CancelledError):
                    await task
            emit_reports(conn, report_dir)
            conn.close()
    return 0


def _surface_task_failure(task: asyncio.Task, stop: asyncio.Event) -> None:
    if task.cancelled():
        return
    exc = task.exception()
    if exc is None:
        return
    print(f"shadow task {task.get_name()} failed: {exc!r}", file=sys.stderr, flush=True)
    stop.set()


async def _target_loop(config: dict[str, Any], conn: sqlite3.Connection, pyth_buffer: PythBuffer, pipeline: SignalPipeline, stop: asyncio.Event) -> None:
    rpc = RpcWs(
        [
            config["rpc"].get("arbitrum_wss_primary", ""),
            config["rpc"].get("arbitrum_wss_fallback", ""),
        ],
        "arbitrum",
    )
    pool = config["target"].get("pool", C.TARGET_POOL)
    last_block_row = conn.execute("SELECT MAX(block_number) AS n FROM ledger").fetchone()
    from_block = int(last_block_row["n"]) + 1 if last_block_row and last_block_row["n"] is not None else None
    poll_interval = float(config["run"].get("poll_interval_sec", 2))
    startup_backfill_blocks = int(config["target"].get("startup_backfill_blocks", 0))
    ts_cache: dict[int, int] = {}
    call_ws = None
    gaps = GapRecorder(conn, "target-arbitrum")

    async for raw in rpc.poll_logs(
        pool,
        from_block=from_block,
        startup_backfill_blocks=startup_backfill_blocks,
        interval_sec=poll_interval,
        on_gap_start=gaps.start,
        on_gap_end=gaps.end,
    ):
        if stop.is_set():
            break
        log = decode_swap_log(raw)
        if log.address.lower() != pool.lower():
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

        pre_mid = pipeline.state.prev_mid_e18
        swap = SwapInput(
            ts_ms=ts_ms,
            pre_mid_e18=pre_mid,
            post_mid_e18=log.post_mid_e18_target,
            ab_e18=log.ab_e18,
            aq_e6=log.aq_e6,
            block_number=log.block_number,
            tx_hash=log.tx_hash,
            log_index=log.log_index,
        )
        fresh = pyth_buffer.as_of(ts_ms)
        decisions = {
            "fresh": fresh,
            "lag2": pyth_buffer.at_or_before_offset(ts_ms, 2),
            "lag5": pyth_buffer.at_or_before_offset(ts_ms, 5),
        }
        regime = pipeline.state.effective_regime(ts_ms).value
        result = pipeline.process_swap(swap, decisions, fresh)
        insert_ledger(conn, _ledger_row(swap, regime, result))
        _save_pipeline_state(conn, pipeline)


async def _sentinel_loop(config: dict[str, Any], conn: sqlite3.Connection, pipeline: SignalPipeline, sentinel: SentinelMirror, stop: asyncio.Event) -> None:
    rpc = RpcWs(
        [
            config["rpc"].get("mainnet_wss_primary", ""),
            config["rpc"].get("mainnet_wss_fallback", ""),
        ],
        "mainnet",
    )
    pool = config["sentinel"].get("pool", C.SENTINEL_POOL)
    poll_interval = float(config["run"].get("poll_interval_sec", 2))
    startup_backfill_blocks = int(config["sentinel"].get("startup_backfill_blocks", 0))
    ts_cache: dict[int, int] = {}
    call_ws = None
    gaps = GapRecorder(conn, "sentinel-mainnet")
    async for raw in rpc.poll_logs(
        pool,
        startup_backfill_blocks=startup_backfill_blocks,
        interval_sec=poll_interval,
        on_gap_start=gaps.start,
        on_gap_end=gaps.end,
    ):
        if stop.is_set():
            break
        log = decode_swap_log(raw)
        if log.address.lower() != pool.lower():
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
        old = pipeline.state.effective_regime(ts_ms)
        changed = pipeline.set_volatile(ts_ms)
        expiry_ms = pipeline.state.regime_expiry_ms
        conn.execute(
            """
            INSERT INTO sentinel_triggers
                (ts_ms, block_number, tx_hash, log_index, move_bps, trig_bps, window_sec, expiry_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (ts_ms, log.block_number, log.tx_hash, log.log_index, result.move_bps, sentinel.trig_bps, sentinel.window_sec, expiry_ms),
        )
        if changed:
            conn.execute(
                "INSERT INTO regime_events (ts_ms, old_regime, new_regime, expiry_ms, reason) VALUES (?, ?, ?, ?, ?)",
                (ts_ms, old.value, Regime.VOLATILE.value, expiry_ms, "sentinel"),
            )
        conn.commit()
        _save_pipeline_state(conn, pipeline)


def _ledger_row(swap: SwapInput, regime: str, decisions: dict[str, Decision]) -> dict[str, object]:
    fresh = decisions["fresh"]
    row: dict[str, object] = {
        "ts_ms": swap.ts_ms,
        "block_number": swap.block_number or 0,
        "tx_hash": swap.tx_hash or "",
        "log_index": swap.log_index or 0,
        "pre_mid_e18": str(swap.pre_mid_e18),
        "post_mid_e18": str(swap.post_mid_e18),
        "ab_e18": str(swap.ab_e18),
        "aq_e6": swap.aq_e6,
        "zero_for_one": 1 if swap.zero_for_one else 0,
        "regime": regime,
        "oracle_staleness_observed_ms": fresh.staleness_ms,
        "conf_e2": fresh.conf_e2,
        "created_at_ms": _now_ms(),
    }
    for label in ("fresh", "lag2", "lag5"):
        row.update(_decision_columns(label, decisions[label]))
    return row


def _decision_columns(prefix: str, decision: Decision) -> dict[str, object]:
    return {
        f"{prefix}_publish_time_ms": decision.publish_time_ms,
        f"{prefix}_fair_e18": str(decision.fair_e18) if decision.fair_e18 is not None else None,
        f"{prefix}_dev_e2": decision.dev_e2,
        f"{prefix}_correcting": 1 if decision.correcting else 0,
        f"{prefix}_premium_pips": decision.premium_pips,
        f"{prefix}_extra_e6": decision.extra_e6,
        f"{prefix}_fallback_reason": decision.fallback_reason,
    }


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


def _hydrate_pipeline(conn: sqlite3.Connection, pipeline: SignalPipeline) -> None:
    state = load_state(conn)
    if not state:
        return
    pipeline.state.basis_wad = int(state.get("basis_wad", "0"))
    pipeline.state.last_obs_t_ms = int(state.get("last_obs_t_ms", "0"))
    pipeline.state.prev_mid_e18 = int(state.get("prev_mid_e18", "0"))
    pipeline.state.conf_ema_e2 = int(state.get("conf_ema_e2", "0"))
    pipeline.state.regime = Regime(state.get("regime", Regime.CALM.value))
    pipeline.state.regime_expiry_ms = int(state.get("regime_expiry_ms", "0"))


def _save_pipeline_state(conn: sqlite3.Connection, pipeline: SignalPipeline) -> None:
    save_state(
        conn,
        {
            "basis_wad": pipeline.state.basis_wad,
            "last_obs_t_ms": pipeline.state.last_obs_t_ms,
            "prev_mid_e18": pipeline.state.prev_mid_e18,
            "conf_ema_e2": pipeline.state.conf_ema_e2,
            "regime": pipeline.state.regime.value,
            "regime_expiry_ms": pipeline.state.regime_expiry_ms,
        },
    )


async def _write_pyth_health(conn: sqlite3.Connection, client: PythClient) -> None:
    while True:
        observed_ms, snapshot = await client.health_rows.get()
        conn.execute(
            "INSERT INTO pyth_health (observed_ms, publish_time_ms, lag_ms, price_e18, conf_e2) VALUES (?, ?, ?, ?, ?)",
            (
                observed_ms,
                snapshot.publish_time_ms,
                max(0, observed_ms - snapshot.publish_time_ms),
                str(snapshot.fair_e18),
                snapshot.effective_conf_e2(),
            ),
        )
        conn.commit()


async def _truth_report_loop(config: dict[str, Any], conn: sqlite3.Connection, report_dir: Path, stop: asyncio.Event) -> None:
    truth_interval = int(config["run"].get("truth_interval_sec", 30))
    report_interval = int(config["run"].get("report_interval_sec", 300))
    truth_delay = int(config["run"].get("truth_delay_sec", 360))
    last_report = 0.0
    while not stop.is_set():
        process_delayed_truth(conn, delay_sec=truth_delay)
        now = time.time()
        if now - last_report >= report_interval:
            emit_reports(conn, report_dir)
            last_report = now
        try:
            await asyncio.wait_for(stop.wait(), timeout=truth_interval)
        except TimeoutError:
            pass


async def _binance_loop(conn: sqlite3.Connection, session: aiohttp.ClientSession, stop: asyncio.Event) -> None:
    url = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDC"
    while not stop.is_set():
        try:
            async with session.get(url, timeout=5) as resp:
                resp.raise_for_status()
                payload = await resp.json()
                price_e18 = int(Decimal(payload["price"]) * Decimal(10**18))
                conn.execute(
                    "INSERT INTO binance_prices (observed_ms, price_e18) VALUES (?, ?)",
                    (_now_ms(), str(price_e18)),
                )
                conn.commit()
        except Exception:
            pass
        try:
            await asyncio.wait_for(stop.wait(), timeout=1)
        except TimeoutError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PegGuard live shadow daemon")
    parser.add_argument("--config", type=Path, default=Path("shadow/config.toml"))
    parser.add_argument("--binance", action="store_true", help="record Binance ETHUSDC as an auxiliary truth source")
    parser.add_argument("--database", type=str, help="override [paths].database for isolated long-run captures")
    parser.add_argument("--reports", type=str, help="override [paths].reports for isolated long-run captures")
    parser.add_argument("--duration-sec", type=int, default=0, help="optional bounded run for smoke tests")
    parser.add_argument("--parity-only", action="store_true", help="run the parity gate and exit")
    return parser.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(main_async(parse_args())))


if __name__ == "__main__":
    main()
