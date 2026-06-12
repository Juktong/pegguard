from __future__ import annotations

from dataclasses import dataclass, field

from . import constants as C


@dataclass(frozen=True)
class SentinelResult:
    triggered: bool
    move_bps: int
    trigger_count: int


@dataclass
class SentinelMirror:
    trig_bps: int = C.RSC_TRIG_BPS
    window_sec: int = C.RSC_WINDOW_SEC
    cooldown_sec: int = C.RSC_REFIRE_COOLDOWN_SEC
    ring: list[tuple[int, int] | None] = field(default_factory=lambda: [None] * 64)
    head: int = 0
    last_flip_sec: int = 0
    trigger_count: int = 0

    def observe(self, ts_ms: int, price_value: int) -> SentinelResult:
        ts_sec = ts_ms // 1000
        self.ring[self.head] = (ts_sec, price_value)
        self.head = (self.head + 1) % len(self.ring)
        lo, hi = self.range_in_window(ts_sec)
        move = move_bps(lo, hi)
        triggered = False
        if move > self.trig_bps and ts_sec > self.last_flip_sec + self.cooldown_sec:
            self.trigger_count += 1
            self.last_flip_sec = ts_sec
            triggered = True
        return SentinelResult(triggered, move, self.trigger_count)

    def range_in_window(self, now_sec: int) -> tuple[int, int]:
        cutoff = 0 if self.window_sec >= now_sec else now_sec - self.window_sec
        lo = 0
        hi = 0
        for obs in self.ring:
            if obs is None:
                continue
            ts, price = obs
            if ts < cutoff or price == 0:
                continue
            if lo == 0 or price < lo:
                lo = price
            if price > hi:
                hi = price
        return lo, hi


def move_bps(lo: int, hi: int) -> int:
    if lo == 0:
        return 0
    return ((hi - lo) * 10_000) // lo


def price_x96sq_from_sqrt(sqrt_price_x96: int) -> int:
    return (sqrt_price_x96 * sqrt_price_x96) >> 96

