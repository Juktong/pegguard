from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Any, AsyncIterator

import websockets

from . import constants as C
from .sentinel import price_x96sq_from_sqrt


def _hex_to_int(value: str) -> int:
    return int(value, 16)


def _decode_int256(word: str) -> int:
    value = int(word, 16)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


@dataclass(frozen=True)
class SwapLog:
    block_number: int
    tx_hash: str
    log_index: int
    address: str
    amount0: int
    amount1: int
    sqrt_price_x96: int
    liquidity: int
    tick: int
    fee_pips: int | None = None

    @property
    def post_mid_e18_target(self) -> int:
        # token1 per token0, adjusted from raw USDC/WETH decimals to 1e18.
        # raw sqrt ratio is USDC-wei per WETH-wei = human_price * 1e-12.
        return (self.sqrt_price_x96 * self.sqrt_price_x96 * 10**30) // (1 << 192)

    @property
    def sentinel_price_value(self) -> int:
        return price_x96sq_from_sqrt(self.sqrt_price_x96)

    @property
    def ab_e18(self) -> int:
        return self.amount0

    @property
    def aq_e6(self) -> int:
        return self.amount1


def decode_swap_log(log: dict[str, Any]) -> SwapLog:
    data = log["data"][2:] if log["data"].startswith("0x") else log["data"]
    words = [data[i : i + 64] for i in range(0, len(data), 64)]
    if len(words) < 5:
        raise ValueError("swap log has too few data words")
    return SwapLog(
        block_number=_hex_to_int(log["blockNumber"]),
        tx_hash=log["transactionHash"],
        log_index=_hex_to_int(log["logIndex"]),
        address=log["address"].lower(),
        amount0=_decode_int256(words[0]),
        amount1=_decode_int256(words[1]),
        sqrt_price_x96=int(words[2], 16),
        liquidity=int(words[3], 16),
        tick=_decode_int256(words[4]),
    )


class RpcWs:
    def __init__(self, urls: list[str], name: str) -> None:
        self.urls = [url for url in urls if url]
        self.name = name
        self._next_id = 1

    async def connect(self):
        last_error: Exception | None = None
        for url in self.urls:
            try:
                return await websockets.connect(url, ping_interval=20, ping_timeout=20, max_size=16 * 1024 * 1024)
            except Exception as exc:  # pragma: no cover - network defensive path
                last_error = exc
        raise RuntimeError(f"could not connect {self.name}: {last_error}")

    async def call(self, ws, method: str, params: list[Any]) -> Any:
        req_id = self._next_id
        self._next_id += 1
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}))
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("id") != req_id:
                continue
            if "error" in msg:
                raise RuntimeError(f"{method} failed: {msg['error']}")
            return msg.get("result")

    async def subscribe_logs(
        self,
        pool: str,
        from_block: int | None = None,
        on_gap_start: Callable[[int | None], Awaitable[None]] | None = None,
        on_gap_end: Callable[[bool], Awaitable[None]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        backoff = 1.0
        next_backfill_block = from_block
        gap_open = False
        while True:
            try:
                async with await self.connect() as ws:
                    if gap_open and on_gap_end is not None:
                        await on_gap_end(next_backfill_block is not None)
                    gap_open = False
                    params: dict[str, Any] = {
                        "address": pool,
                        "topics": [C.SWAP_TOPIC0],
                    }
                    sub_id = await self.call(ws, "eth_subscribe", ["logs", params])
                    if next_backfill_block is not None:
                        latest = await self.call(ws, "eth_blockNumber", [])
                        latest_int = _hex_to_int(latest)
                        if next_backfill_block <= latest_int:
                            backfill = await self.call(
                                ws,
                                "eth_getLogs",
                                [
                                    {
                                        "address": pool,
                                        "topics": [C.SWAP_TOPIC0],
                                        "fromBlock": hex(next_backfill_block),
                                        "toBlock": hex(latest_int),
                                    }
                                ],
                            )
                            for log in backfill:
                                next_backfill_block = max(next_backfill_block, _hex_to_int(log["blockNumber"]) + 1)
                                yield log
                            next_backfill_block = latest_int + 1
                    backoff = 1.0
                    async for raw in ws:
                        msg = json.loads(raw)
                        if msg.get("method") == "eth_subscription" and msg.get("params", {}).get("subscription") == sub_id:
                            log = msg["params"]["result"]
                            block_number = _hex_to_int(log["blockNumber"])
                            if next_backfill_block is None or block_number >= next_backfill_block:
                                next_backfill_block = block_number + 1
                            yield log
            except asyncio.CancelledError:
                raise
            except Exception:
                if not gap_open and on_gap_start is not None:
                    await on_gap_start(None if next_backfill_block is None else next_backfill_block - 1)
                gap_open = True
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def poll_logs(
        self,
        pool: str,
        from_block: int | None = None,
        startup_backfill_blocks: int = 0,
        interval_sec: float = 2.0,
        max_block_range: int = 10_000,
        on_gap_start: Callable[[int | None], Awaitable[None]] | None = None,
        on_gap_end: Callable[[bool], Awaitable[None]] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        backoff = 1.0
        next_block = from_block
        gap_open = False
        while True:
            try:
                async with await self.connect() as ws:
                    latest = _hex_to_int(await self.call(ws, "eth_blockNumber", []))
                    if next_block is None:
                        next_block = max(0, latest - max(0, startup_backfill_blocks) + 1)
                    if gap_open and on_gap_end is not None:
                        await on_gap_end(True)
                    gap_open = False
                    backoff = 1.0
                    while True:
                        latest = _hex_to_int(await self.call(ws, "eth_blockNumber", []))
                        while next_block <= latest:
                            to_block = min(latest, next_block + max_block_range - 1)
                            logs = await self.call(
                                ws,
                                "eth_getLogs",
                                [
                                    {
                                        "address": pool,
                                        "topics": [C.SWAP_TOPIC0],
                                        "fromBlock": hex(next_block),
                                        "toBlock": hex(to_block),
                                    }
                                ],
                            )
                            for log in logs:
                                yield log
                            next_block = to_block + 1
                        await asyncio.sleep(interval_sec)
            except asyncio.CancelledError:
                raise
            except Exception:
                if not gap_open and on_gap_start is not None:
                    await on_gap_start(None if next_block is None else next_block - 1)
                gap_open = True
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60.0)

    async def block_timestamp_ms(self, ws, block_number: int) -> int:
        block = await self.call(ws, "eth_getBlockByNumber", [hex(block_number), False])
        return _hex_to_int(block["timestamp"]) * 1000


class RpcHttp:
    def __init__(self, url: str, name: str) -> None:
        self.url = url
        self.name = name
        self._next_id = 1

    async def connect(self):
        if not self.url:
            raise RuntimeError(f"missing HTTP RPC for {self.name}")
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def call(self, _session, method: str, params: list[Any]) -> Any:
        req_id = self._next_id
        self._next_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        return await asyncio.to_thread(self._call_sync, payload, method)

    def _call_sync(self, payload: dict[str, Any], method: str) -> Any:
        request = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={"content-type": "application/json", "user-agent": "pegguard-shadow/1.0"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network defensive path
            body = exc.read().decode(errors="replace")
            raise RuntimeError(f"{method} HTTP {exc.code}: {body}") from exc
        if "error" in data:
            raise RuntimeError(f"{method} failed: {data['error']}")
        return data.get("result")
