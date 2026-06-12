from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, getcontext
from pathlib import Path

from . import constants as C
from .real_position_report import DEFAULT_POSITION_ID, DEFAULT_POSITION_URL


BASE_POSITION_MANAGER = "0x7c5f5a4bbd8fd63184577525326123b519429bdc"
BASE_POOL_MANAGER = "0x498581ff718922c3f8e6a244956af099b2652b2b"
BASE_STATE_VIEW = "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71"
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
Q96 = 1 << 96
Q128 = 1 << 128
CAST_TIMEOUT_SEC = 20
CAST_RETRIES = 2


@dataclass(frozen=True)
class RealPositionMetadata:
    status: str
    chain: str
    source_url: str
    position_id: str
    position_manager: str
    pool_manager: str
    state_view: str
    block_number: int
    owner: str
    token0: str
    token1: str
    token0_address: str
    token1_address: str
    token0_decimals: int
    token1_decimals: int
    pool_pair: str
    fee_pips: int
    tick_spacing: int
    hooks: str
    pool_id: str
    position_info: str
    has_subscriber: bool
    position_liquidity: int
    pool_liquidity: int
    sqrt_price_x96: int
    current_tick: int
    protocol_fee: int
    lp_fee: int
    tick_lower: int
    tick_upper: int
    in_range: bool
    sqrt_lower_x96: int
    sqrt_upper_x96: int
    amount0_raw: int
    amount1_raw: int
    amount0_human: str
    amount1_human: str
    spot_price_token1_per_token0: str
    computed_position_value_e6: int
    fee_owed0_raw: int
    fee_owed1_raw: int
    fee_owed0_human: str
    fee_owed1_human: str
    computed_uncollected_fees_e6: int
    computed_position_value_with_uncollected_fees_e6: int


def collect(
    rpc_url: str,
    position_id: str = DEFAULT_POSITION_ID,
    position_manager: str = BASE_POSITION_MANAGER,
    state_view: str = BASE_STATE_VIEW,
    chain: str = "base",
    source_url: str = DEFAULT_POSITION_URL,
) -> dict:
    owner = _cast_call(rpc_url, position_manager, "ownerOf(uint256)(address)", position_id)
    pool_manager = _cast_call(rpc_url, position_manager, "poolManager()(address)").strip()
    position_liquidity = _first_int(_cast_call(rpc_url, position_manager, "getPositionLiquidity(uint256)(uint128)", position_id))
    pool_line, info_line = _cast_call(
        rpc_url,
        position_manager,
        "getPoolAndPositionInfo(uint256)((address,address,uint24,int24,address),uint256)",
        position_id,
    ).splitlines()
    token0_address, token1_address, fee_pips, tick_spacing, hooks = _parse_pool_key(pool_line)
    position_info = _first_int(info_line)
    tick_lower, tick_upper, has_subscriber = decode_position_info(position_info)
    token0 = _strip_quotes(_cast_call(rpc_url, token0_address, "symbol()(string)"))
    token1 = _strip_quotes(_cast_call(rpc_url, token1_address, "symbol()(string)"))
    token0_decimals = _first_int(_cast_call(rpc_url, token0_address, "decimals()(uint8)"))
    token1_decimals = _first_int(_cast_call(rpc_url, token1_address, "decimals()(uint8)"))
    pool_id = _pool_id(token0_address, token1_address, fee_pips, tick_spacing, hooks)
    slot0 = _cast_call(rpc_url, state_view, "getSlot0(bytes32)(uint160,int24,uint24,uint24)", pool_id).splitlines()
    sqrt_price_x96, current_tick, protocol_fee, lp_fee = [_first_int(line) for line in slot0]
    pool_liquidity = _first_int(_cast_call(rpc_url, state_view, "getLiquidity(bytes32)(uint128)", pool_id))
    sqrt_lower_x96 = sqrt_price_at_tick(tick_lower)
    sqrt_upper_x96 = sqrt_price_at_tick(tick_upper)
    amount0_raw, amount1_raw = amounts_for_liquidity(
        sqrt_price_x96,
        sqrt_lower_x96,
        sqrt_upper_x96,
        position_liquidity,
    )
    position_value_e6 = quote_value_e6(amount0_raw, amount1_raw, sqrt_price_x96, token1_decimals)
    fee_owed0_raw, fee_owed1_raw = fees_owed(
        rpc_url,
        state_view,
        pool_id,
        position_manager,
        tick_lower,
        tick_upper,
        str(position_id),
    )
    fee_value_e6 = quote_value_e6(fee_owed0_raw, fee_owed1_raw, sqrt_price_x96, token1_decimals)
    block_number = _first_int(_run(["cast", "block-number", "--rpc-url", rpc_url]))
    metadata = RealPositionMetadata(
        status="metadata collected",
        chain=chain,
        source_url=source_url,
        position_id=str(position_id),
        position_manager=position_manager,
        pool_manager=pool_manager,
        state_view=state_view,
        block_number=block_number,
        owner=owner.strip(),
        token0=token0,
        token1=token1,
        token0_address=token0_address,
        token1_address=token1_address,
        token0_decimals=token0_decimals,
        token1_decimals=token1_decimals,
        pool_pair=f"{token0}/{token1}",
        fee_pips=fee_pips,
        tick_spacing=tick_spacing,
        hooks=hooks,
        pool_id=pool_id,
        position_info=str(position_info),
        has_subscriber=has_subscriber,
        position_liquidity=position_liquidity,
        pool_liquidity=pool_liquidity,
        sqrt_price_x96=sqrt_price_x96,
        current_tick=current_tick,
        protocol_fee=protocol_fee,
        lp_fee=lp_fee,
        tick_lower=tick_lower,
        tick_upper=tick_upper,
        in_range=tick_lower <= current_tick <= tick_upper,
        sqrt_lower_x96=sqrt_lower_x96,
        sqrt_upper_x96=sqrt_upper_x96,
        amount0_raw=amount0_raw,
        amount1_raw=amount1_raw,
        amount0_human=_human_amount(amount0_raw, token0_decimals),
        amount1_human=_human_amount(amount1_raw, token1_decimals),
        spot_price_token1_per_token0=_spot_price(sqrt_price_x96),
        computed_position_value_e6=position_value_e6,
        fee_owed0_raw=fee_owed0_raw,
        fee_owed1_raw=fee_owed1_raw,
        fee_owed0_human=_human_amount(fee_owed0_raw, token0_decimals),
        fee_owed1_human=_human_amount(fee_owed1_raw, token1_decimals),
        computed_uncollected_fees_e6=fee_value_e6,
        computed_position_value_with_uncollected_fees_e6=position_value_e6 + fee_value_e6,
    )
    return asdict(metadata)


def decode_position_info(info: int) -> tuple[int, int, bool]:
    mask_24 = (1 << 24) - 1
    tick_lower = _signed24((info >> 8) & mask_24)
    tick_upper = _signed24((info >> 32) & mask_24)
    return tick_lower, tick_upper, bool(info & 0xFF)


def sqrt_price_at_tick(tick: int) -> int:
    getcontext().prec = 100
    return int((Decimal("1.0001") ** (Decimal(tick) / Decimal(2))) * Decimal(Q96))


def amounts_for_liquidity(
    sqrt_price_x96: int,
    sqrt_lower_x96: int,
    sqrt_upper_x96: int,
    liquidity: int,
) -> tuple[int, int]:
    if sqrt_lower_x96 > sqrt_upper_x96:
        sqrt_lower_x96, sqrt_upper_x96 = sqrt_upper_x96, sqrt_lower_x96
    if sqrt_price_x96 <= sqrt_lower_x96:
        amount0 = (liquidity * Q96 * (sqrt_upper_x96 - sqrt_lower_x96)) // (sqrt_upper_x96 * sqrt_lower_x96)
        return amount0, 0
    if sqrt_price_x96 < sqrt_upper_x96:
        amount0 = (liquidity * Q96 * (sqrt_upper_x96 - sqrt_price_x96)) // (sqrt_upper_x96 * sqrt_price_x96)
        amount1 = (liquidity * (sqrt_price_x96 - sqrt_lower_x96)) // Q96
        return amount0, amount1
    amount1 = (liquidity * (sqrt_upper_x96 - sqrt_lower_x96)) // Q96
    return 0, amount1


def quote_value_e6(amount0_raw: int, amount1_raw: int, sqrt_price_x96: int, quote_decimals: int) -> int:
    amount0_quote_raw = (amount0_raw * sqrt_price_x96 * sqrt_price_x96) // (Q96 * Q96)
    quote_raw = amount0_quote_raw + amount1_raw
    return (quote_raw * 1_000_000) // (10**quote_decimals)


def fees_owed(
    rpc_url: str,
    state_view: str,
    pool_id: str,
    position_manager: str,
    tick_lower: int,
    tick_upper: int,
    position_id: str,
) -> tuple[int, int]:
    salt = "0x" + f"{int(position_id):064x}"
    position = _cast_call(
        rpc_url,
        state_view,
        "getPositionInfo(bytes32,address,int24,int24,bytes32)(uint128,uint256,uint256)",
        pool_id,
        position_manager,
        tick_lower,
        tick_upper,
        salt,
    ).splitlines()
    liquidity, fee_growth0_last, fee_growth1_last = [_first_int(line) for line in position]
    growth = _cast_call(
        rpc_url,
        state_view,
        "getFeeGrowthInside(bytes32,int24,int24)(uint256,uint256)",
        pool_id,
        tick_lower,
        tick_upper,
    ).splitlines()
    fee_growth0, fee_growth1 = [_first_int(line) for line in growth]
    owed0 = max(0, fee_growth0 - fee_growth0_last) * liquidity // Q128
    owed1 = max(0, fee_growth1 - fee_growth1_last) * liquidity // Q128
    return owed0, owed1


def markdown(report: dict) -> str:
    lines = [
        "# Real Position On-Chain Metadata",
        "",
        "This artifact collects immutable/current on-chain metadata for the target",
        "Uniswap v4 position. It is not the real-position economics gate because it",
        "does not value the inventory, HODL baseline, or fees in quote dollars.",
        "",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Chain: {report.get('chain', 'n/a')}",
        f"- Position: {report.get('position_id', 'n/a')}",
        f"- Block: {report.get('block_number', 'n/a')}",
        f"- Owner: `{report.get('owner', 'n/a')}`",
        f"- Pool id: `{report.get('pool_id', 'n/a')}`",
        f"- PoolManager: `{report.get('pool_manager', BASE_POOL_MANAGER)}`",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Pair | {report.get('pool_pair', 'n/a')} |",
        f"| token0 | `{report.get('token0_address', 'n/a')}` ({report.get('token0', 'n/a')}, {report.get('token0_decimals', 'n/a')} decimals) |",
        f"| token1 | `{report.get('token1_address', 'n/a')}` ({report.get('token1', 'n/a')}, {report.get('token1_decimals', 'n/a')} decimals) |",
        f"| Fee | {int(report.get('fee_pips', 0)) / 100:.2f} bps |",
        f"| Tick spacing | {report.get('tick_spacing', 'n/a')} |",
        f"| Hooks | `{report.get('hooks', 'n/a')}` |",
        f"| Position liquidity | {report.get('position_liquidity', 'n/a')} |",
        f"| Pool liquidity | {report.get('pool_liquidity', 'n/a')} |",
        f"| Current tick | {report.get('current_tick', 'n/a')} |",
        f"| Tick lower | {report.get('tick_lower', 'n/a')} |",
        f"| Tick upper | {report.get('tick_upper', 'n/a')} |",
        f"| In range | {'yes' if report.get('in_range') else 'no'} |",
        f"| LP fee from slot0 | {report.get('lp_fee', 'n/a')} pips |",
        f"| Current amount0 | {report.get('amount0_human', 'n/a')} {report.get('token0', '')} |",
        f"| Current amount1 | {report.get('amount1_human', 'n/a')} {report.get('token1', '')} |",
        f"| Spot token1/token0 | {report.get('spot_price_token1_per_token0', 'n/a')} |",
        f"| Current inventory value | {_usd_e6(int(report.get('computed_position_value_e6', 0)))} |",
        f"| Uncollected fee0 | {report.get('fee_owed0_human', 'n/a')} {report.get('token0', '')} |",
        f"| Uncollected fee1 | {report.get('fee_owed1_human', 'n/a')} {report.get('token1', '')} |",
        f"| Uncollected fee value | {_usd_e6(int(report.get('computed_uncollected_fees_e6', 0)))} |",
        f"| Inventory + uncollected fees | {_usd_e6(int(report.get('computed_position_value_with_uncollected_fees_e6', 0)))} |",
        "",
        "## Use",
        "",
        "Use this to fill optional metadata fields and independently check current",
        "`position_value_e6` in `docs/real_position_input.json`. The HODL baseline,",
        "collected historical fees, and any gas-cost allocation still need an audited",
        "position lifecycle export before the real-position economics gate can pass.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _cast_call(rpc_url: str, target: str, signature: str, *args: object) -> str:
    return _run(["cast", "call", "--rpc-url", rpc_url, target, signature, *(str(arg) for arg in args)])


def _run(cmd: list[str]) -> str:
    last_error: Exception | None = None
    for attempt in range(CAST_RETRIES + 1):
        try:
            completed = subprocess.run(
                cmd,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=CAST_TIMEOUT_SEC,
            )
            return completed.stdout.strip()
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last_error = exc
            if attempt < CAST_RETRIES:
                time.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _parse_pool_key(line: str) -> tuple[str, str, int, int, str]:
    match = re.fullmatch(r"\((0x[0-9a-fA-F]{40}), (0x[0-9a-fA-F]{40}), ([0-9]+).*?, (-?[0-9]+).*?, (0x[0-9a-fA-F]{40})\)", line.strip())
    if not match:
        raise ValueError(f"could not parse pool key: {line}")
    token0, token1, fee, tick_spacing, hooks = match.groups()
    return token0, token1, int(fee), int(tick_spacing), hooks


def _pool_id(token0: str, token1: str, fee_pips: int, tick_spacing: int, hooks: str) -> str:
    encoded = _run(
        [
            "cast",
            "abi-encode",
            "f(address,address,uint24,int24,address)",
            token0,
            token1,
            str(fee_pips),
            str(tick_spacing),
            hooks,
        ]
    )
    return _run(["cast", "keccak", encoded])


def _first_int(line: str) -> int:
    match = re.search(r"-?[0-9]+", line)
    if not match:
        raise ValueError(f"could not parse integer: {line}")
    return int(match.group(0), 10)


def _signed24(value: int) -> int:
    if value & (1 << 23):
        return value - (1 << 24)
    return value


def _human_amount(value: int, decimals: int) -> str:
    scale = Decimal(10) ** decimals
    out = Decimal(value) / scale
    return f"{out.normalize():f}"


def _spot_price(sqrt_price_x96: int) -> str:
    getcontext().prec = 80
    price = Decimal(sqrt_price_x96) * Decimal(sqrt_price_x96) / Decimal(Q96 * Q96)
    return f"{price.normalize():f}"


def _usd_e6(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Collect on-chain metadata for the real Uniswap v4 position")
    parser.add_argument("--rpc-url", default=os.environ.get("BASE_RPC_URL") or os.environ.get("CHAIN_RPC_URL") or "https://mainnet.base.org")
    parser.add_argument("--chain", default="base")
    parser.add_argument("--position-id", default=DEFAULT_POSITION_ID)
    parser.add_argument("--position-manager", default=BASE_POSITION_MANAGER)
    parser.add_argument("--state-view", default=BASE_STATE_VIEW)
    parser.add_argument("--source-url", default=DEFAULT_POSITION_URL)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "real_position_metadata.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "real_position_metadata.json")
    args = parser.parse_args()
    report = collect(
        rpc_url=args.rpc_url,
        position_id=str(args.position_id),
        position_manager=args.position_manager,
        state_view=args.state_view,
        chain=args.chain,
        source_url=args.source_url,
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"position {report['position_id']} {report['pool_pair']} in_range={report['in_range']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
