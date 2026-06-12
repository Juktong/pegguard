from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from . import constants as C
from .pipeline import OracleSnapshot


def _price_to_e18(price: int, expo: int) -> int:
    power = 18 + expo
    if power >= 0:
        return price * (10**power)
    return price // (10 ** (-power))


@dataclass
class PythBuffer:
    maxlen: int = 100_000
    observations: deque[OracleSnapshot] = field(default_factory=deque)

    def add(self, snapshot: OracleSnapshot) -> None:
        self.observations.append(snapshot)
        while len(self.observations) > self.maxlen:
            self.observations.popleft()

    def as_of(self, ts_ms: int) -> OracleSnapshot | None:
        best: OracleSnapshot | None = None
        for obs in reversed(self.observations):
            if obs.publish_time_ms <= ts_ms:
                best = obs
                break
        return best

    def at_or_before_offset(self, ts_ms: int, offset_sec: int) -> OracleSnapshot | None:
        return self.as_of(ts_ms - offset_sec * 1000)


def parse_hermes_payload(payload: dict[str, Any]) -> list[OracleSnapshot]:
    parsed = payload.get("parsed")
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        parsed = []
    snapshots: list[OracleSnapshot] = []
    for item in parsed:
        price_obj = item.get("price") if isinstance(item, dict) else None
        if not isinstance(price_obj, dict):
            continue
        price = int(price_obj["price"])
        conf = int(price_obj.get("conf", 0))
        expo = int(price_obj["expo"])
        publish_time = int(price_obj["publish_time"])
        fair_e18 = _price_to_e18(price, expo)
        conf_e2 = (conf * 1_000_000) // price if price > 0 else 0
        snapshots.append(
            OracleSnapshot(
                fair_e18=fair_e18,
                publish_time_ms=publish_time * 1000,
                price=price,
                conf=conf,
                conf_e2=conf_e2,
            )
        )
    return snapshots


class PythClient:
    def __init__(self, feed_id: str, base_url: str, buffer: PythBuffer, session: aiohttp.ClientSession) -> None:
        self.feed_id = feed_id
        self.base_url = base_url.rstrip("/")
        self.buffer = buffer
        self.session = session
        self.health_rows: asyncio.Queue[tuple[int, OracleSnapshot]] = asyncio.Queue()

    async def run(self) -> None:
        while True:
            try:
                await self._run_sse()
            except asyncio.CancelledError:
                raise
            except Exception:
                await self._run_polling_until_sse_retry()

    async def _run_sse(self) -> None:
        url = f"{self.base_url}/v2/updates/price/stream?ids[]={self.feed_id}"
        async with self.session.get(url, timeout=None, headers={"accept": "text/event-stream"}) as resp:
            resp.raise_for_status()
            async for raw in resp.content:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                payload = json.loads(line[5:].strip())
                self._record_payload(payload)

    async def _run_polling_until_sse_retry(self) -> None:
        for _ in range(120):
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(2)
            await asyncio.sleep(0.25)

    async def poll_once(self) -> None:
        url = f"{self.base_url}/v2/updates/price/latest?ids[]={self.feed_id}"
        async with self.session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            self._record_payload(await resp.json())

    def _record_payload(self, payload: dict[str, Any]) -> None:
        observed_ms = int(time.time() * 1000)
        for snapshot in parse_hermes_payload(payload):
            self.buffer.add(snapshot)
            self.health_rows.put_nowait((observed_ms, snapshot))
