from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .rpc import RpcWs, decode_swap_log


RPC_WSS = "wss://arbitrum-one-rpc.publicnode.com"


@dataclass(frozen=True)
class FeePool:
    fee_pips: int
    pool: str

    @property
    def fee_bps(self) -> float:
        return self.fee_pips / 100


@dataclass(frozen=True)
class TierMetric:
    fee_pips: int
    pool: str
    swaps: int
    notional_e6: int
    fee_e6: int
    volume_share: float
    fee_share: float

    @property
    def fee_bps(self) -> float:
        return self.fee_pips / 100


FEE_POOLS = [
    FeePool(100, "0x6f38e884725a116C9C7fBF208e79FE8828a2595F"),
    FeePool(500, "0xC6962004f452bE9203591991D15f6b388e09E8D0"),
    FeePool(3000, "0xc473e2aEE3441BF9240Be85eb122aBB059A3B57c"),
    FeePool(10000, "0x42FC852A750BA93D5bf772ecdc857e87a86403a9"),
]


async def collect(
    lookback_blocks: int,
    chunk_blocks: int = 10_000,
    rpc_wss: str = RPC_WSS,
    chain: str = "arbitrum",
    pair: str = "WETH/USDC",
    fee_pools: list[FeePool] | None = None,
    quote_token_index: int = 1,
    quote_decimals: int = 6,
) -> dict:
    fee_pools = fee_pools or FEE_POOLS
    rpc = RpcWs([rpc_wss], chain)
    async with await rpc.connect() as ws:
        latest = int(await rpc.call(ws, "eth_blockNumber", []), 16)
        start = max(0, latest - lookback_blocks + 1)
        start_ts = await rpc.block_timestamp_ms(ws, start)
        end_ts = await rpc.block_timestamp_ms(ws, latest)
        raw_rows: list[dict] = []
        for fee_pool in fee_pools:
            notional = 0
            swaps = 0
            cursor = start
            while cursor <= latest:
                to_block = min(latest, cursor + chunk_blocks - 1)
                logs = await rpc.call(
                    ws,
                    "eth_getLogs",
                    [
                        {
                            "address": fee_pool.pool,
                            "topics": [C.SWAP_TOPIC0],
                            "fromBlock": hex(cursor),
                            "toBlock": hex(to_block),
                        }
                    ],
                )
                for raw in logs:
                    log = decode_swap_log(raw)
                    raw_notional = log.amount0 if quote_token_index == 0 else log.amount1
                    notional += (abs(raw_notional) * 1_000_000) // (10**quote_decimals)
                    swaps += 1
                cursor = to_block + 1
            raw_rows.append(
                {
                    "fee_pips": fee_pool.fee_pips,
                    "pool": fee_pool.pool,
                    "swaps": swaps,
                    "notional_e6": notional,
                    "fee_e6": (notional * fee_pool.fee_pips) // 1_000_000,
                }
            )
    return summarize(raw_rows, start, latest, start_ts, end_ts, chain, pair, quote_token_index, quote_decimals)


def summarize(
    raw_rows: list[dict],
    start_block: int,
    end_block: int,
    start_ts_ms: int,
    end_ts_ms: int,
    chain: str = "arbitrum",
    pair: str = "WETH/USDC",
    quote_token_index: int = 1,
    quote_decimals: int = 6,
) -> dict:
    total_notional = sum(int(row["notional_e6"]) for row in raw_rows)
    total_fee = sum(int(row["fee_e6"]) for row in raw_rows)
    tiers = []
    for row in raw_rows:
        notional = int(row["notional_e6"])
        fee = int(row["fee_e6"])
        tiers.append(
            TierMetric(
                fee_pips=int(row["fee_pips"]),
                pool=str(row["pool"]),
                swaps=int(row["swaps"]),
                notional_e6=notional,
                fee_e6=fee,
                volume_share=(notional / total_notional) if total_notional else 0.0,
                fee_share=(fee / total_fee) if total_fee else 0.0,
            )
        )
    high_fee_notional = sum(tier.notional_e6 for tier in tiers if tier.fee_pips >= 3000)
    target_notional = sum(tier.notional_e6 for tier in tiers if tier.fee_pips == 500)
    duration_hours = max((end_ts_ms - start_ts_ms) / 3_600_000, 0.0)
    return {
        "chain": chain,
        "pair": pair,
        "quote_token_index": quote_token_index,
        "quote_decimals": quote_decimals,
        "start_block": start_block,
        "end_block": end_block,
        "duration_hours": duration_hours,
        "total_notional_e6": total_notional,
        "target_5bps_notional_e6": target_notional,
        "high_fee_notional_e6": high_fee_notional,
        "high_fee_volume_share": (high_fee_notional / total_notional) if total_notional else 0.0,
        "tiers": [asdict(tier) for tier in sorted(tiers, key=lambda item: item.fee_pips)],
    }


def markdown(data: dict) -> str:
    lines = [
        "# Route-Away Proxy",
        "",
        "This is real on-chain routing evidence, not a controlled route-away experiment.",
        f"It compares recent {data['pair']} swap flow across Uniswap v3 {data['chain']} fee tiers.",
        "The result is useful for scale-of-effect intuition only: liquidity depth, route",
        "construction, incentives, and MEV paths differ across tiers.",
        "",
        "## Window",
        "",
        f"- Chain: {data['chain']}",
        f"- Pair: {data['pair']}",
        f"- Quote token index/decimals: {data.get('quote_token_index', 1)} / {data.get('quote_decimals', 6)}",
        f"- Blocks: {data['start_block']} to {data['end_block']}",
        f"- Approx duration: {data['duration_hours']:.2f} hours",
        f"- Total notional: {_usd(data['total_notional_e6'])}",
        f"- 30 bps plus volume share: {data['high_fee_volume_share']:.2%}",
        "",
        "## Fee-Tier Flow",
        "",
        "| Fee tier | Pool | Swaps | Notional | Volume share | Fee revenue at tier | Fee share |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for row in data["tiers"]:
        lines.append(
            f"| {row['fee_pips'] / 100:.2f} bps | `{row['pool']}` | {row['swaps']} | "
            f"{_usd(row['notional_e6'])} | {row['volume_share']:.2%} | "
            f"{_usd(row['fee_e6'])} | {row['fee_share']:.2%} |"
        )
    if data.get("comparison_windows"):
        lines.extend(
            [
                "",
                "## Lookback Stability",
                "",
                "| Lookback blocks | Approx duration | Total notional | 1 bps share | 5 bps share | 30 bps+ share |",
                "|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in data["comparison_windows"]:
            lines.append(
                f"| {row['lookback_blocks']:,} | {row['duration_hours']:.2f}h | {_usd(row['total_notional_e6'])} | "
                f"{_tier_share(row, 100):.2%} | {_tier_share(row, 500):.2%} | {row['high_fee_volume_share']:.2%} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- PegGuard's measured extra fee in the current live shadow sample is sub-bps to low-bps, much closer to the 5 bps tier than to the 30 bps tier.",
            f"- Any material flow already using 30 bps or 100 bps {data['pair']} pools shows that some order flow tolerates higher explicit fees when route quality or liquidity warrants it.",
            "- This does not prove PegGuard route retention. The real test still requires a live PegGuard pool competing against comparable alternatives.",
            "- Use this as a sanity check beside the mechanical route-away haircut table, not as calibration input.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(out_md: Path, out_json: Path, data: dict) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(data), encoding="utf-8")
    out_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _tier_share(data: dict, fee_pips: int) -> float:
    for row in data.get("tiers", []):
        if int(row["fee_pips"]) == fee_pips:
            return float(row["volume_share"])
    return 0.0


def _comparison_row(data: dict, lookback_blocks: int) -> dict:
    return {
        "lookback_blocks": lookback_blocks,
        "start_block": data["start_block"],
        "end_block": data["end_block"],
        "duration_hours": data["duration_hours"],
        "total_notional_e6": data["total_notional_e6"],
        "high_fee_volume_share": data["high_fee_volume_share"],
        "tiers": data["tiers"],
    }


def parse_fee_pool(raw: str) -> FeePool:
    fee, pool = raw.split(":", 1)
    return FeePool(int(fee), pool)


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compare same-pair fee-tier flow as a route-away proxy")
    parser.add_argument("--rpc-wss", default=RPC_WSS)
    parser.add_argument("--chain", default="arbitrum")
    parser.add_argument("--pair", default="WETH/USDC")
    parser.add_argument("--fee-pool", action="append", default=[], help="fee_pips:pool_address; repeat for each tier")
    parser.add_argument("--quote-token-index", type=int, choices=[0, 1], default=1)
    parser.add_argument("--quote-decimals", type=int, default=6)
    parser.add_argument("--lookback-blocks", type=int, default=50_000)
    parser.add_argument("--extra-lookback-blocks", type=int, nargs="*", default=[])
    parser.add_argument("--chunk-blocks", type=int, default=10_000)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_proxy.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_proxy.json")
    args = parser.parse_args()
    fee_pools = [parse_fee_pool(raw) for raw in args.fee_pool] if args.fee_pool else FEE_POOLS
    data = asyncio.run(
        collect(
            args.lookback_blocks,
            args.chunk_blocks,
            args.rpc_wss,
            args.chain,
            args.pair,
            fee_pools,
            args.quote_token_index,
            args.quote_decimals,
        )
    )
    data["lookback_blocks"] = args.lookback_blocks
    windows = [_comparison_row(data, args.lookback_blocks)]
    for lookback in args.extra_lookback_blocks:
        if lookback == args.lookback_blocks:
            continue
        windows.append(
            _comparison_row(
                asyncio.run(
                    collect(
                        lookback,
                        args.chunk_blocks,
                        args.rpc_wss,
                        args.chain,
                        args.pair,
                        fee_pools,
                        args.quote_token_index,
                        args.quote_decimals,
                    )
                ),
                lookback,
            )
        )
    data["comparison_windows"] = sorted(windows, key=lambda row: int(row["lookback_blocks"]))
    write_outputs(args.out_md, args.out_json, data)
    print(f"30bps+ share={data['high_fee_volume_share']:.2%} over {_usd(data['total_notional_e6'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
