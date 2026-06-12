from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .route_away_ab import evaluate, validation_errors, write_invalid_outputs, write_outputs
from .rpc import RpcHttp, RpcWs, SwapLog, decode_swap_log

V4_SWAP_TOPIC0 = "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f"

CHAIN_IDS = {
    "ethereum": 1,
    "mainnet": 1,
    "arbitrum": 42161,
    "arbitrum-one": 42161,
    "base": 8453,
    "base-mainnet": 8453,
    "base-sepolia": 84532,
    "unichain": 130,
    "unichain-mainnet": 130,
    "unichain-sepolia": 1301,
}


@dataclass(frozen=True)
class PoolWindowStats:
    pool: str
    start_block: int
    end_block: int
    swaps: int
    quote_notional_e6: int
    kind: str = "v3"
    pool_id: str | None = None
    vwap_fee_pips: int | None = None
    fee_observation_count: int = 0


@dataclass(frozen=True)
class ExperimentWindows:
    pre_baseline: PoolWindowStats
    pre_treatment: PoolWindowStats
    post_baseline: PoolWindowStats
    post_treatment: PoolWindowStats


async def collect_windows(
    rpc_url: str,
    chain: str,
    baseline_pool: str,
    treatment_pool: str,
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: str | None,
    treatment_pool_id: str | None,
    pre_start_block: int,
    pre_end_block: int,
    post_start_block: int,
    post_end_block: int,
    quote_token_index: int,
    quote_decimals: int,
    chunk_blocks: int,
) -> ExperimentWindows:
    validate_collection_config(
        baseline_pool,
        treatment_pool,
        baseline_kind,
        treatment_kind,
        baseline_pool_id,
        treatment_pool_id,
        pre_start_block,
        pre_end_block,
        post_start_block,
        post_end_block,
        quote_token_index,
        quote_decimals,
        chunk_blocks,
    )
    rpc = _rpc_client(rpc_url, chain)
    async with await rpc.connect() as ws:
        await validate_collection_preflight(
            rpc,
            ws,
            chain,
            {"baseline": baseline_pool, "treatment": treatment_pool},
        )
        pre_baseline = await collect_pool_window(
            rpc,
            ws,
            baseline_pool,
            baseline_kind,
            baseline_pool_id,
            pre_start_block,
            pre_end_block,
            quote_token_index,
            quote_decimals,
            chunk_blocks,
        )
        pre_treatment = await collect_pool_window(
            rpc,
            ws,
            treatment_pool,
            treatment_kind,
            treatment_pool_id,
            pre_start_block,
            pre_end_block,
            quote_token_index,
            quote_decimals,
            chunk_blocks,
        )
        post_baseline = await collect_pool_window(
            rpc,
            ws,
            baseline_pool,
            baseline_kind,
            baseline_pool_id,
            post_start_block,
            post_end_block,
            quote_token_index,
            quote_decimals,
            chunk_blocks,
        )
        post_treatment = await collect_pool_window(
            rpc,
            ws,
            treatment_pool,
            treatment_kind,
            treatment_pool_id,
            post_start_block,
            post_end_block,
            quote_token_index,
            quote_decimals,
            chunk_blocks,
        )
    return ExperimentWindows(pre_baseline, pre_treatment, post_baseline, post_treatment)


async def validate_collection_preflight(rpc: RpcHttp | RpcWs, ws, chain: str, pools: dict[str, str]) -> None:
    actual_chain_id = int(str(await rpc.call(ws, "eth_chainId", [])), 16)
    expected_chain_id = _expected_chain_id(chain)
    if expected_chain_id is not None and actual_chain_id != expected_chain_id:
        raise ValueError(f"RPC chain id {actual_chain_id} does not match --chain {chain} expected {expected_chain_id}")

    checked: set[str] = set()
    for label, address in pools.items():
        key = address.lower()
        if key in checked:
            continue
        checked.add(key)
        code = await rpc.call(ws, "eth_getCode", [address, "latest"])
        if not isinstance(code, str) or code.lower() in ("", "0x", "0x0"):
            raise ValueError(f"{label} address has no contract code on chain {actual_chain_id}: {address}")


async def collect_pool_window(
    rpc: RpcHttp | RpcWs,
    ws,
    pool: str,
    kind: str,
    pool_id: str | None,
    start_block: int,
    end_block: int,
    quote_token_index: int,
    quote_decimals: int,
    chunk_blocks: int,
) -> PoolWindowStats:
    topic0, topics = _log_topics(kind, pool_id)
    logs: list[SwapLog] = []
    cursor = start_block
    while cursor <= end_block:
        to_block = min(end_block, cursor + chunk_blocks - 1)
        raw_logs = await rpc.call(
            ws,
            "eth_getLogs",
            [
                {
                    "address": pool,
                    "topics": topics,
                    "fromBlock": hex(cursor),
                    "toBlock": hex(to_block),
                }
            ],
        )
        decoder = decode_swap_log if topic0 == C.SWAP_TOPIC0 else decode_v4_swap_log
        logs.extend(decoder(raw) for raw in raw_logs)
        cursor = to_block + 1
    return summarize_swaps(pool, start_block, end_block, logs, quote_token_index, quote_decimals, kind, pool_id)


def summarize_swaps(
    pool: str,
    start_block: int,
    end_block: int,
    logs: list[SwapLog],
    quote_token_index: int,
    quote_decimals: int,
    kind: str = "v3",
    pool_id: str | None = None,
) -> PoolWindowStats:
    if quote_token_index not in (0, 1):
        raise ValueError("quote_token_index must be 0 or 1")
    scale = 10 ** quote_decimals
    notional = 0
    fee_weighted = 0
    fee_count = 0
    for log in logs:
        raw_amount = log.amount0 if quote_token_index == 0 else log.amount1
        quote_notional = (abs(raw_amount) * 1_000_000) // scale
        notional += quote_notional
        if log.fee_pips is not None:
            fee_weighted += quote_notional * log.fee_pips
            fee_count += 1
    vwap_fee_pips = None if notional == 0 or fee_count == 0 else fee_weighted // notional
    return PoolWindowStats(pool, start_block, end_block, len(logs), notional, kind, pool_id, vwap_fee_pips, fee_count)


def decode_v4_swap_log(log: dict) -> SwapLog:
    data = log["data"][2:] if str(log["data"]).startswith("0x") else str(log["data"])
    words = [data[i : i + 64] for i in range(0, len(data), 64)]
    if len(words) < 6:
        raise ValueError("v4 swap log has too few data words")
    return SwapLog(
        block_number=int(log["blockNumber"], 16),
        tx_hash=log["transactionHash"],
        log_index=int(log["logIndex"], 16),
        address=str(log["address"]).lower(),
        amount0=_decode_signed_word(words[0]),
        amount1=_decode_signed_word(words[1]),
        sqrt_price_x96=int(words[2], 16),
        liquidity=int(words[3], 16),
        tick=_decode_signed_word(words[4]),
        fee_pips=int(words[5], 16),
    )


def build_payload(
    pair: str,
    baseline: str,
    treatment: str,
    pre_treatment_fee_pips: int,
    post_treatment_fee_pips: int | None,
    windows: ExperimentWindows,
    quote_token_index: int,
    quote_decimals: int,
) -> dict:
    post_fee = _effective_treatment_fee("post", post_treatment_fee_pips, windows.post_treatment)
    return {
        "pair": pair,
        "baseline": baseline,
        "treatment": treatment,
        "pre": {
            "baseline_notional_e6": windows.pre_baseline.quote_notional_e6,
            "treatment_notional_e6": windows.pre_treatment.quote_notional_e6,
            "treatment_fee_pips": pre_treatment_fee_pips,
        },
        "post": {
            "baseline_notional_e6": windows.post_baseline.quote_notional_e6,
            "treatment_notional_e6": windows.post_treatment.quote_notional_e6,
            "treatment_fee_pips": post_fee,
        },
        "collection": {
            "quote_token_index": quote_token_index,
            "quote_decimals": quote_decimals,
            "pre_baseline": asdict(windows.pre_baseline),
            "pre_treatment": asdict(windows.pre_treatment),
            "post_baseline": asdict(windows.post_baseline),
            "post_treatment": asdict(windows.post_treatment),
        },
    }


def _effective_treatment_fee(label: str, provided_fee_pips: int | None, window: PoolWindowStats) -> int:
    if provided_fee_pips is not None:
        return provided_fee_pips
    if window.vwap_fee_pips is not None:
        return window.vwap_fee_pips
    raise ValueError(
        f"{label} treatment fee is required unless the treatment window is v4 and has decoded Swap fee observations"
    )


def validate_nonzero_windows(windows: ExperimentWindows) -> None:
    failures = []
    for label, row in (
        ("pre baseline", windows.pre_baseline),
        ("pre treatment", windows.pre_treatment),
        ("post baseline", windows.post_baseline),
        ("post treatment", windows.post_treatment),
    ):
        if row.swaps <= 0 or row.quote_notional_e6 <= 0:
            failures.append(f"{label}: swaps={row.swaps}, quote_notional_e6={row.quote_notional_e6}")
    if failures:
        raise ValueError(
            "controlled route-away collection requires nonzero swaps and quote notional in every window; "
            + "; ".join(failures)
        )


def write_payload_artifacts(payload: dict, out_input: Path, out_md: Path, out_json: Path) -> list[str]:
    out_input.parent.mkdir(parents=True, exist_ok=True)
    out_input.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    errors = validation_errors(payload)
    if errors:
        write_invalid_outputs(payload, errors, out_md, out_json)
        return errors
    result = evaluate(payload)
    write_outputs(result, out_md, out_json, payload)
    return []


def validate_collection_config(
    baseline_pool: str,
    treatment_pool: str,
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: str | None,
    treatment_pool_id: str | None,
    pre_start_block: int,
    pre_end_block: int,
    post_start_block: int,
    post_end_block: int,
    quote_token_index: int,
    quote_decimals: int,
    chunk_blocks: int,
) -> None:
    failures: list[str] = []
    baseline_kind_norm = baseline_kind.strip().lower()
    treatment_kind_norm = treatment_kind.strip().lower()
    if baseline_kind_norm not in ("v3", "v4"):
        failures.append(f"baseline kind must be v3 or v4: {baseline_kind}")
    if treatment_kind_norm not in ("v3", "v4"):
        failures.append(f"treatment kind must be v3 or v4: {treatment_kind}")
    if pre_start_block > pre_end_block:
        failures.append(f"pre window start must be <= end: {pre_start_block}>{pre_end_block}")
    if post_start_block > post_end_block:
        failures.append(f"post window start must be <= end: {post_start_block}>{post_end_block}")
    if pre_end_block >= post_start_block:
        failures.append(f"pre window must end before post window starts: pre_end={pre_end_block}, post_start={post_start_block}")
    pre_len = pre_end_block - pre_start_block + 1
    post_len = post_end_block - post_start_block + 1
    if pre_len > 0 and post_len > 0 and pre_len != post_len:
        failures.append(f"pre/post windows must have equal length: pre_blocks={pre_len}, post_blocks={post_len}")
    if quote_token_index not in (0, 1):
        failures.append(f"quote token index must be 0 or 1: {quote_token_index}")
    if quote_decimals <= 0:
        failures.append(f"quote decimals must be > 0: {quote_decimals}")
    if chunk_blocks <= 0:
        failures.append(f"chunk blocks must be > 0: {chunk_blocks}")
    for label, kind, pool_id in (
        ("baseline", baseline_kind_norm, baseline_pool_id),
        ("treatment", treatment_kind_norm, treatment_pool_id),
    ):
        if kind != "v4":
            continue
        if not pool_id:
            failures.append(f"{label} v4 collection requires a pool id")
            continue
        try:
            _normalize_pool_id(pool_id)
        except ValueError as exc:
            failures.append(f"{label} pool id invalid: {exc}")
    if not failures:
        try:
            validate_distinct_pool_identities(
                baseline_pool,
                treatment_pool,
                baseline_kind,
                treatment_kind,
                baseline_pool_id,
                treatment_pool_id,
            )
        except ValueError as exc:
            failures.append(str(exc))
    if failures:
        raise ValueError("invalid controlled route-away collection config: " + "; ".join(failures))


def validate_distinct_pool_identities(
    baseline_pool: str,
    treatment_pool: str,
    baseline_kind: str,
    treatment_kind: str,
    baseline_pool_id: str | None,
    treatment_pool_id: str | None,
) -> None:
    baseline_kind_norm = baseline_kind.strip().lower()
    treatment_kind_norm = treatment_kind.strip().lower()
    baseline_pool_norm = baseline_pool.strip().lower()
    treatment_pool_norm = treatment_pool.strip().lower()
    if baseline_pool_norm != treatment_pool_norm:
        return
    if baseline_kind_norm == treatment_kind_norm == "v4":
        baseline_id = _normalize_pool_id(baseline_pool_id)
        treatment_id = _normalize_pool_id(treatment_pool_id)
        if baseline_id and treatment_id and baseline_id != treatment_id:
            return
    raise ValueError(
        "controlled route-away collection requires distinct baseline and treatment pools; "
        "for v4 comparisons, use different pool ids even when both pools share one PoolManager"
    )


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Collect pool-log inputs for the controlled route-away experiment")
    parser.add_argument("--rpc-wss", help="WebSocket RPC endpoint for the chain")
    parser.add_argument("--rpc-http", help="HTTP RPC endpoint for historical eth_getLogs collection")
    parser.add_argument("--chain", default="unknown")
    parser.add_argument("--pair", required=True)
    parser.add_argument("--baseline-pool", required=True, help="v3 pool address, or PoolManager address when --baseline-kind=v4")
    parser.add_argument("--treatment-pool", required=True, help="v3 pool address, or PoolManager address when --treatment-kind=v4")
    parser.add_argument("--baseline-kind", choices=["v3", "v4"], default="v3")
    parser.add_argument("--treatment-kind", choices=["v3", "v4"], default="v3")
    parser.add_argument("--baseline-pool-id", help="required when --baseline-kind=v4")
    parser.add_argument("--treatment-pool-id", help="required when --treatment-kind=v4")
    parser.add_argument("--pre-start-block", type=int, required=True)
    parser.add_argument("--pre-end-block", type=int, required=True)
    parser.add_argument("--post-start-block", type=int, required=True)
    parser.add_argument("--post-end-block", type=int, required=True)
    parser.add_argument("--pre-treatment-fee-pips", type=int, required=True)
    parser.add_argument(
        "--post-treatment-fee-pips",
        type=int,
        help="VWAP effective treatment fee in pips; if omitted for a v4 treatment, derive it from Swap log fee fields",
    )
    parser.add_argument("--quote-token-index", type=int, choices=[0, 1], required=True)
    parser.add_argument("--quote-decimals", type=int, default=6)
    parser.add_argument("--chunk-blocks", type=int, default=5_000)
    parser.add_argument(
        "--allow-zero-notional",
        action="store_true",
        help="write diagnostic output even if a window has zero swaps or quote notional; this is not valid gate evidence",
    )
    parser.add_argument("--out-input", type=Path, default=root / "docs" / "route_away_ab_input.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_ab.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_ab.json")
    args = parser.parse_args()
    rpc_url = args.rpc_wss or args.rpc_http
    if not rpc_url:
        parser.error("one of --rpc-wss or --rpc-http is required")

    windows = asyncio.run(
        collect_windows(
            rpc_url,
            args.chain,
            args.baseline_pool,
            args.treatment_pool,
            args.baseline_kind,
            args.treatment_kind,
            args.baseline_pool_id,
            args.treatment_pool_id,
            args.pre_start_block,
            args.pre_end_block,
            args.post_start_block,
            args.post_end_block,
            args.quote_token_index,
            args.quote_decimals,
            args.chunk_blocks,
        )
    )
    if not args.allow_zero_notional:
        validate_nonzero_windows(windows)
    payload = build_payload(
        args.pair,
        args.baseline_pool,
        args.treatment_pool,
        args.pre_treatment_fee_pips,
        args.post_treatment_fee_pips,
        windows,
        args.quote_token_index,
        args.quote_decimals,
    )
    errors = write_payload_artifacts(payload, args.out_input, args.out_md, args.out_json)
    if errors:
        print("route_away=invalid")
        print(f"errors={len(errors)}")
        print(f"wrote {args.out_input}")
        print(f"wrote {args.out_md}")
        print(f"wrote {args.out_json}")
        return 0 if args.allow_zero_notional else 2
    result = evaluate(payload)
    print(f"route_away={result.route_away_rate:.2%}")
    print(f"wrote {args.out_input}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


def _log_topics(kind: str, pool_id: str | None) -> tuple[str, list[str]]:
    if kind == "v3":
        return C.SWAP_TOPIC0, [C.SWAP_TOPIC0]
    if kind == "v4":
        if not pool_id:
            raise ValueError("v4 collection requires a pool id")
        return V4_SWAP_TOPIC0, [V4_SWAP_TOPIC0, _bytes32_topic(pool_id)]
    raise ValueError(f"unsupported pool kind: {kind}")


def _rpc_client(rpc_url: str, chain: str) -> RpcHttp | RpcWs:
    if rpc_url.startswith("http://") or rpc_url.startswith("https://"):
        return RpcHttp(rpc_url, chain)
    return RpcWs([rpc_url], chain)


def _expected_chain_id(chain: str) -> int | None:
    normalized = chain.strip().lower()
    if normalized in CHAIN_IDS:
        return CHAIN_IDS[normalized]
    if normalized.startswith("chain-"):
        normalized = normalized[len("chain-") :]
    try:
        return int(normalized, 10)
    except ValueError:
        return None


def _normalize_pool_id(pool_id: str | None) -> str | None:
    if pool_id is None:
        return None
    clean = pool_id.strip().lower()
    if clean.startswith("0x"):
        clean = clean[2:]
    if not clean:
        return None
    if len(clean) > 64:
        raise ValueError("v4 pool id is too long")
    if any(char not in "0123456789abcdef" for char in clean):
        raise ValueError("v4 pool id must be hex bytes32")
    return clean.rjust(64, "0")


def _bytes32_topic(value: str) -> str:
    clean = _normalize_pool_id(value)
    if clean is None:
        raise ValueError("bytes32 topic is empty")
    return "0x" + clean


def _decode_signed_word(word: str) -> int:
    value = int(word, 16)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


if __name__ == "__main__":
    raise SystemExit(main())
