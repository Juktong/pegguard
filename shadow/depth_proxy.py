from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from decimal import Decimal, getcontext
from pathlib import Path

from . import constants as C
from .route_away_proxy import FEE_POOLS, RPC_WSS, FeePool, parse_fee_pool
from .rpc import RpcWs

getcontext().prec = 80

Q96 = 1 << 96
Q192 = 1 << 192
SLOT0_SELECTOR = "0x3850c7bd"
LIQUIDITY_SELECTOR = "0x1a686502"


@dataclass(frozen=True)
class BandDepth:
    band_bps: int
    up_quote_e6: int
    down_quote_e6: int
    min_side_quote_e6: int


@dataclass(frozen=True)
class DepthRow:
    fee_pips: int
    pool: str
    sqrt_price_x96: int
    tick: int
    liquidity: int
    depths: list[BandDepth]


async def collect(
    rpc_wss: str = RPC_WSS,
    chain: str = "arbitrum",
    pair: str = "WETH/USDC",
    fee_pools: list[FeePool] | None = None,
    quote_token_index: int = 1,
    quote_decimals: int = 6,
    bands_bps: list[int] | None = None,
) -> dict:
    fee_pools = fee_pools or FEE_POOLS
    bands_bps = bands_bps or [10, 50, 100]
    rpc = RpcWs([rpc_wss], chain)
    async with await rpc.connect() as ws:
        block_number = int(await rpc.call(ws, "eth_blockNumber", []), 16)
        rows = []
        for fee_pool in fee_pools:
            slot0 = await _eth_call(rpc, ws, fee_pool.pool, SLOT0_SELECTOR)
            liquidity = int(await _eth_call(rpc, ws, fee_pool.pool, LIQUIDITY_SELECTOR), 16)
            sqrt_price_x96 = int(_word(slot0, 0), 16)
            tick = _decode_signed_word(_word(slot0, 1))
            rows.append(
                depth_row(
                    fee_pool,
                    sqrt_price_x96,
                    tick,
                    liquidity,
                    quote_token_index,
                    quote_decimals,
                    bands_bps,
                )
            )
    return summarize(rows, block_number, chain, pair, quote_token_index, quote_decimals)


def depth_row(
    fee_pool: FeePool,
    sqrt_price_x96: int,
    tick: int,
    liquidity: int,
    quote_token_index: int,
    quote_decimals: int,
    bands_bps: list[int],
) -> DepthRow:
    return DepthRow(
        fee_pips=fee_pool.fee_pips,
        pool=fee_pool.pool,
        sqrt_price_x96=sqrt_price_x96,
        tick=tick,
        liquidity=liquidity,
        depths=[
            depth_for_band(sqrt_price_x96, liquidity, band_bps, quote_token_index, quote_decimals)
            for band_bps in bands_bps
        ],
    )


def depth_for_band(
    sqrt_price_x96: int,
    liquidity: int,
    band_bps: int,
    quote_token_index: int,
    quote_decimals: int,
) -> BandDepth:
    if not 0 < band_bps < 10_000:
        raise ValueError("band_bps must be between 0 and 10000")
    if quote_token_index not in (0, 1):
        raise ValueError("quote_token_index must be 0 or 1")
    if liquidity == 0:
        return BandDepth(band_bps, 0, 0, 0)

    sqrt_up = _scale_sqrt(sqrt_price_x96, Decimal(1) + (Decimal(band_bps) / Decimal(10_000)))
    sqrt_down = _scale_sqrt(sqrt_price_x96, Decimal(1) - (Decimal(band_bps) / Decimal(10_000)))

    # Token1 input moves price up; token0 input moves price down.
    amount1_up = liquidity * (sqrt_up - sqrt_price_x96) // Q96
    amount0_down = liquidity * (sqrt_price_x96 - sqrt_down) * Q96 // (sqrt_price_x96 * sqrt_down)

    if quote_token_index == 1:
        up_quote = _raw_to_e6(amount1_up, quote_decimals)
        down_quote_raw = amount0_down * sqrt_price_x96 * sqrt_price_x96 // Q192
        down_quote = _raw_to_e6(down_quote_raw, quote_decimals)
    else:
        up_quote_raw = amount1_up * Q192 // (sqrt_price_x96 * sqrt_price_x96)
        up_quote = _raw_to_e6(up_quote_raw, quote_decimals)
        down_quote = _raw_to_e6(amount0_down, quote_decimals)

    return BandDepth(
        band_bps=band_bps,
        up_quote_e6=up_quote,
        down_quote_e6=down_quote,
        min_side_quote_e6=min(up_quote, down_quote),
    )


def summarize(
    rows: list[DepthRow],
    block_number: int,
    chain: str,
    pair: str,
    quote_token_index: int,
    quote_decimals: int,
) -> dict:
    band_totals: dict[int, int] = {}
    for row in rows:
        for depth in row.depths:
            band_totals[depth.band_bps] = band_totals.get(depth.band_bps, 0) + depth.min_side_quote_e6
    return {
        "chain": chain,
        "pair": pair,
        "block_number": block_number,
        "quote_token_index": quote_token_index,
        "quote_decimals": quote_decimals,
        "band_totals": {str(key): value for key, value in sorted(band_totals.items())},
        "tiers": [asdict(row) for row in sorted(rows, key=lambda item: item.fee_pips)],
    }


def markdown(data: dict) -> str:
    bands = sorted(int(key) for key in data.get("band_totals", {}).keys())
    lines = [
        "# Fee-Tier Depth Proxy",
        "",
        "This is current on-chain liquidity context for the route-away proxy. It uses",
        "the active v3 pool liquidity at `slot0` and estimates quote notional needed",
        "to move price within small bands. It does not traverse initialized ticks, so",
        "treat wider bands as directional capacity evidence, not exact execution depth.",
        "",
        "## Snapshot",
        "",
        f"- Chain: {data['chain']}",
        f"- Pair: {data['pair']}",
        f"- Block: {data['block_number']}",
        f"- Quote token index/decimals: {data['quote_token_index']} / {data['quote_decimals']}",
        "",
        "## Active Depth",
        "",
        _depth_header(bands),
        _depth_separator(bands),
    ]
    totals = {int(key): int(value) for key, value in data.get("band_totals", {}).items()}
    for row in data["tiers"]:
        lines.append(_depth_line(row, totals, bands))
    lines.extend(
        [
            "",
            "## Band Totals",
            "",
            "| Band | Total min-side depth |",
            "|---:|---:|",
        ]
    )
    for band in bands:
        lines.append(f"| {band} bps | {_usd(totals.get(band, 0))} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_md: Path, out_json: Path, data: dict) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(data), encoding="utf-8")
    out_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


async def _eth_call(rpc: RpcWs, ws, address: str, data: str) -> str:
    return await rpc.call(ws, "eth_call", [{"to": address, "data": data}, "latest"])


def _word(data: str, index: int) -> str:
    clean = data[2:] if data.startswith("0x") else data
    start = index * 64
    return clean[start : start + 64]


def _decode_signed_word(word: str) -> int:
    value = int(word, 16)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


def _scale_sqrt(sqrt_price_x96: int, price_multiplier: Decimal) -> int:
    return int(Decimal(sqrt_price_x96) * price_multiplier.sqrt())


def _raw_to_e6(value: int, decimals: int) -> int:
    return (value * 1_000_000) // (10**decimals)


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _depth_header(bands: list[int]) -> str:
    cols = ["| Fee tier | Pool | Tick | Active liquidity |"]
    for band in bands:
        cols.append(f" Min {band} bps depth | {band} bps share |")
    return "".join(cols)


def _depth_separator(bands: list[int]) -> str:
    return "|---:|---|---:|---:|" + "---:|---:|" * len(bands)


def _depth_line(row: dict, totals: dict[int, int], bands: list[int]) -> str:
    parts = [
        f"| {row['fee_pips'] / 100:.2f} bps | `{row['pool']}` | {row['tick']} | {int(row['liquidity']):,} |"
    ]
    depths = {int(item["band_bps"]): int(item["min_side_quote_e6"]) for item in row["depths"]}
    for band in bands:
        total = totals.get(band, 0)
        value = depths.get(band, 0)
        share = value / total if total else 0.0
        parts.append(f" {_usd(value)} | {share:.2%} |")
    return "".join(parts)


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Estimate active on-chain depth across Uniswap v3 fee tiers")
    parser.add_argument("--rpc-wss", default=RPC_WSS)
    parser.add_argument("--chain", default="arbitrum")
    parser.add_argument("--pair", default="WETH/USDC")
    parser.add_argument("--fee-pool", action="append", default=[], help="fee_pips:pool_address; repeat for each tier")
    parser.add_argument("--quote-token-index", type=int, choices=[0, 1], default=1)
    parser.add_argument("--quote-decimals", type=int, default=6)
    parser.add_argument("--bands-bps", type=int, nargs="*", default=[10, 50, 100])
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "depth_proxy.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "depth_proxy.json")
    args = parser.parse_args()

    fee_pools = [parse_fee_pool(raw) for raw in args.fee_pool] if args.fee_pool else FEE_POOLS
    data = asyncio.run(
        collect(
            args.rpc_wss,
            args.chain,
            args.pair,
            fee_pools,
            args.quote_token_index,
            args.quote_decimals,
            args.bands_bps,
        )
    )
    write_outputs(args.out_md, args.out_json, data)
    print(f"{args.pair} active depth snapshot at block {data['block_number']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
