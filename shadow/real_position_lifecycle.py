from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import constants as C
from .real_position_metadata import (
    BASE_POOL_MANAGER,
    BASE_POSITION_MANAGER,
    BASE_STATE_VIEW,
    amounts_for_liquidity,
    quote_value_e6,
    sqrt_price_at_tick,
)
from .real_position_report import DEFAULT_POSITION_ID


TRANSFER_TOPIC0 = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
MODIFY_LIQUIDITY_TOPIC0 = "0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec"
ZERO_TOPIC = "0x" + "0" * 64


@dataclass(frozen=True)
class LifecycleEvent:
    block_number: int
    tx_hash: str
    log_index: int
    tick_lower: int
    tick_upper: int
    liquidity_delta: int
    sqrt_price_x96: int
    amount0_raw: int
    amount1_raw: int
    transfer0_raw: int | None
    transfer1_raw: int | None
    direction: str


def compute(
    rpc_url: str,
    metadata: dict,
    checkpoint_path: Path,
    chunk_blocks: int = 10_000,
    max_chunks: int | None = None,
    sleep_sec: float = 0.0,
) -> dict:
    position_id = str(metadata.get("position_id") or DEFAULT_POSITION_ID)
    position_manager = str(metadata.get("position_manager") or BASE_POSITION_MANAGER)
    pool_manager = str(metadata.get("pool_manager") or BASE_POOL_MANAGER)
    state_view = str(metadata.get("state_view") or BASE_STATE_VIEW)
    pool_id = str(metadata["pool_id"])
    token0_address = str(metadata.get("token0_address") or "")
    token1_address = str(metadata.get("token1_address") or "")
    tick_lower = int(metadata["tick_lower"])
    tick_upper = int(metadata["tick_upper"])
    token_topic = _topic_uint(int(position_id))
    latest = _rpc_int(rpc_url, "eth_blockNumber", [])

    checkpoint = _load_json(checkpoint_path)
    mint = checkpoint.get("mint")
    scan = checkpoint.get("scan", {})
    if mint is None:
        cursor = int(scan.get("mint_cursor", latest))
        mint, cursor, chunks = _find_mint(
            rpc_url,
            position_manager,
            token_topic,
            cursor,
            chunk_blocks,
            max_chunks,
            sleep_sec,
        )
        checkpoint = {
            "status": "mint found" if mint else "mint scan in progress",
            "latest_seen": latest,
            "mint": mint,
            "scan": {"mint_cursor": cursor, "chunks_scanned": int(scan.get("chunks_scanned", 0)) + chunks},
        }
        _write_json(checkpoint_path, checkpoint)
        if mint is None:
            return _report(metadata, checkpoint, [], latest)

    start_block = int(mint["block_number"])
    events = _collect_modify_events(
        rpc_url,
        pool_manager,
        position_manager,
        state_view,
        pool_id,
        int(position_id),
        tick_lower,
        tick_upper,
        token0_address,
        token1_address,
        start_block,
        latest,
        chunk_blocks,
        sleep_sec,
    )
    checkpoint = {
        "status": "lifecycle scanned",
        "latest_seen": latest,
        "mint": mint,
        "scan": {
            "mint_cursor": start_block,
            "modify_from_block": start_block,
            "modify_to_block": latest,
            "chunks_scanned": checkpoint.get("scan", {}).get("chunks_scanned", 0),
        },
    }
    _write_json(checkpoint_path, checkpoint)
    return _report(metadata, checkpoint, events, latest)


def markdown(report: dict) -> str:
    lines = [
        "# Real Position Lifecycle Scan",
        "",
        "This report scans Base logs for the target Uniswap v4 position lifecycle.",
        "It is an evidence artifact for the real-position gate. Contributed",
        "inventory uses exact receipt transfers when present and falls back to",
        "liquidity-change reconstruction from block-level pool state otherwise.",
        "Same-block swap ordering can require deeper trace evidence for positions",
        "without exact transfer matches.",
        "",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Position: {report.get('position_id', 'n/a')}",
        f"- Latest seen block: {report.get('latest_seen', 'n/a')}",
        f"- Mint block: {report.get('mint_block', 'not found')}",
        f"- Lifecycle events: {len(report.get('events', []))}",
        f"- Net contributed token0: {report.get('net_token0_human', 'n/a')} {report.get('token0', '')}",
        f"- Net contributed token1: {report.get('net_token1_human', 'n/a')} {report.get('token1', '')}",
        f"- Provisional HODL value: {_usd_e6(int(report.get('provisional_hodl_value_e6', 0)))}",
        f"- Current inventory + uncollected fees: {_usd_e6(int(report.get('current_value_with_fees_e6', 0)))}",
        f"- Provisional net vs HODL: {_usd_e6(int(report.get('provisional_net_vs_hodl_e6', 0)))}",
        "",
        "## Events",
        "",
        "| Block | Log | Direction | Liquidity delta | amount0 | amount1 | transfer0 | transfer1 | tx |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("events", []):
        lines.append(
                f"| {row['block_number']} | {row['log_index']} | {row['direction']} | "
                f"{row['liquidity_delta']} | {row['amount0_raw']} | {row['amount1_raw']} | "
                f"{_na(row.get('transfer0_raw'))} | {_na(row.get('transfer1_raw'))} | `{row['tx_hash']}` |"
            )
    if not report.get("events"):
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Mint discovery scans ERC-721 `Transfer(0x0, owner, tokenId)` in reverse block chunks.",
            "- Lifecycle events scan PoolManager `ModifyLiquidity` for the pool id, PositionManager sender, and `bytes32(tokenId)` salt.",
            "- Positive liquidity deltas are treated as deposits; negative deltas reduce net contributed inventory.",
            "- When receipt transfer amounts are present, contributed inventory uses those exact transfers instead of liquidity-math reconstruction.",
            "- This narrows the manual real-position gate, but final pass still needs audited lifecycle/HODL evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _find_mint(
    rpc_url: str,
    position_manager: str,
    token_topic: str,
    cursor: int,
    chunk_blocks: int,
    max_chunks: int | None,
    sleep_sec: float,
) -> tuple[dict | None, int, int]:
    chunks = 0
    while cursor >= 0 and (max_chunks is None or chunks < max_chunks):
        start = max(0, cursor - chunk_blocks + 1)
        logs = _rpc(
            rpc_url,
            "eth_getLogs",
            [
                {
                    "address": position_manager,
                    "fromBlock": hex(start),
                    "toBlock": hex(cursor),
                    "topics": [TRANSFER_TOPIC0, ZERO_TOPIC, None, token_topic],
                }
            ],
        )
        chunks += 1
        if logs:
            log = logs[0]
            return _log_ref(log), start, chunks
        if start == 0:
            return None, -1, chunks
        cursor = start - 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return None, cursor, chunks


def _collect_modify_events(
    rpc_url: str,
    pool_manager: str,
    position_manager: str,
    state_view: str,
    pool_id: str,
    position_id: int,
    tick_lower: int,
    tick_upper: int,
    token0_address: str,
    token1_address: str,
    start_block: int,
    end_block: int,
    chunk_blocks: int,
    sleep_sec: float,
) -> list[LifecycleEvent]:
    salt = _topic_uint(position_id)
    position_manager_topic = _topic_address(position_manager)
    sqrt_lower = sqrt_price_at_tick(tick_lower)
    sqrt_upper = sqrt_price_at_tick(tick_upper)
    rows: list[LifecycleEvent] = []
    cursor = start_block
    while cursor <= end_block:
        to_block = min(end_block, cursor + chunk_blocks - 1)
        logs = _rpc(
            rpc_url,
            "eth_getLogs",
            [
                {
                    "address": pool_manager,
                    "fromBlock": hex(cursor),
                    "toBlock": hex(to_block),
                    "topics": [MODIFY_LIQUIDITY_TOPIC0, pool_id, position_manager_topic],
                }
            ],
        )
        for raw in logs:
            decoded = decode_modify_liquidity(raw)
            if decoded["salt"].lower() != salt.lower():
                continue
            if decoded["tick_lower"] != tick_lower or decoded["tick_upper"] != tick_upper:
                continue
            sqrt_price = _slot0_sqrt_at_block(rpc_url, state_view, pool_id, decoded["block_number"])
            amount0, amount1 = amounts_for_liquidity(sqrt_price, sqrt_lower, sqrt_upper, abs(decoded["liquidity_delta"]))
            direction = "deposit" if decoded["liquidity_delta"] > 0 else "withdraw"
            transfer0, transfer1 = _receipt_transfer_amounts(
                rpc_url,
                decoded["tx_hash"],
                token0_address,
                token1_address,
                pool_manager,
                direction == "deposit",
            )
            rows.append(
                LifecycleEvent(
                    block_number=decoded["block_number"],
                    tx_hash=decoded["tx_hash"],
                    log_index=decoded["log_index"],
                    tick_lower=decoded["tick_lower"],
                    tick_upper=decoded["tick_upper"],
                    liquidity_delta=decoded["liquidity_delta"],
                    sqrt_price_x96=sqrt_price,
                    amount0_raw=amount0,
                    amount1_raw=amount1,
                    transfer0_raw=transfer0,
                    transfer1_raw=transfer1,
                    direction=direction,
                )
            )
        cursor = to_block + 1
        if sleep_sec > 0:
            time.sleep(sleep_sec)
    return rows


def decode_modify_liquidity(log: dict) -> dict:
    words = _words(log.get("data", "0x"))
    if len(words) < 4:
        raise ValueError("ModifyLiquidity data has too few words")
    return {
        "block_number": int(log["blockNumber"], 16),
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
        "tick_lower": _decode_int256(words[0]),
        "tick_upper": _decode_int256(words[1]),
        "liquidity_delta": _decode_int256(words[2]),
        "salt": "0x" + words[3].lower(),
    }


def decode_modify_position(log: dict) -> dict:
    return decode_modify_liquidity(log)


def _slot0_sqrt_at_block(rpc_url: str, state_view: str, pool_id: str, block_number: int) -> int:
    data = "0xc815641c" + pool_id.removeprefix("0x")
    result = _rpc(
        rpc_url,
        "eth_call",
        [{"to": state_view, "data": data}, hex(block_number)],
    )
    return int(result[2:66], 16)


def _receipt_transfer_amounts(
    rpc_url: str,
    tx_hash: str,
    token0_address: str,
    token1_address: str,
    pool_manager: str,
    deposit: bool,
) -> tuple[int | None, int | None]:
    if not token0_address or not token1_address:
        return None, None
    receipt = _rpc(rpc_url, "eth_getTransactionReceipt", [tx_hash])
    pool_topic = _topic_address(pool_manager)
    token0 = token0_address.lower()
    token1 = token1_address.lower()
    amount0 = 0
    amount1 = 0
    seen0 = False
    seen1 = False
    for raw in receipt.get("logs", []):
        topics = [str(topic).lower() for topic in raw.get("topics", [])]
        if len(topics) < 3 or topics[0] != TRANSFER_TOPIC0:
            continue
        if deposit and topics[2] != pool_topic:
            continue
        if not deposit and topics[1] != pool_topic:
            continue
        value = int(str(raw.get("data", "0x0")), 16)
        address = str(raw.get("address", "")).lower()
        if address == token0:
            amount0 += value
            seen0 = True
        elif address == token1:
            amount1 += value
            seen1 = True
    return (amount0 if seen0 else None, amount1 if seen1 else None)


def _report(metadata: dict, checkpoint: dict, events: list[LifecycleEvent], latest: int) -> dict:
    token0_decimals = int(metadata.get("token0_decimals", 18))
    token1_decimals = int(metadata.get("token1_decimals", 6))
    current_sqrt = int(metadata.get("sqrt_price_x96", 0))
    net0 = 0
    net1 = 0
    for event in events:
        sign = 1 if event.liquidity_delta > 0 else -1
        net0 += sign * (event.transfer0_raw if event.transfer0_raw is not None else event.amount0_raw)
        net1 += sign * (event.transfer1_raw if event.transfer1_raw is not None else event.amount1_raw)
    provisional_hodl = _signed_quote_value_e6(net0, net1, current_sqrt, token1_decimals) if current_sqrt else 0
    current_value = int(metadata.get("computed_position_value_with_uncollected_fees_e6", 0))
    mint = checkpoint.get("mint")
    status = checkpoint.get("status", "unknown")
    return {
        "status": status,
        "position_id": str(metadata.get("position_id", DEFAULT_POSITION_ID)),
        "token0": metadata.get("token0", "token0"),
        "token1": metadata.get("token1", "token1"),
        "latest_seen": latest,
        "mint": mint,
        "mint_block": None if mint is None else int(mint["block_number"]),
        "checkpoint": checkpoint,
        "events": [asdict(event) for event in events],
        "net_token0_raw": net0,
        "net_token1_raw": net1,
        "net_token0_human": _human_signed(net0, token0_decimals),
        "net_token1_human": _human_signed(net1, token1_decimals),
        "provisional_hodl_value_e6": provisional_hodl,
        "current_value_with_fees_e6": current_value,
        "provisional_net_vs_hodl_e6": current_value - provisional_hodl,
    }


def _rpc_int(rpc_url: str, method: str, params: list[Any]) -> int:
    return int(_rpc(rpc_url, method, params), 16)


def _rpc(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    request = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={"content-type": "application/json", "user-agent": "curl/8.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} HTTP {exc.code}: {body}") from exc
    if "error" in data:
        raise RuntimeError(f"{method} failed: {data['error']}")
    return data["result"]


def _log_ref(log: dict) -> dict:
    return {
        "block_number": int(log["blockNumber"], 16),
        "tx_hash": log["transactionHash"],
        "log_index": int(log["logIndex"], 16),
    }


def _topic_uint(value: int) -> str:
    return "0x" + f"{value:064x}"


def _topic_address(value: str) -> str:
    clean = value.removeprefix("0x").lower()
    if len(clean) != 40:
        raise ValueError(f"invalid address: {value}")
    return "0x" + ("0" * 24) + clean


def _words(data: str) -> list[str]:
    clean = data[2:] if data.startswith("0x") else data
    return [clean[i : i + 64] for i in range(0, len(clean), 64)]


def _decode_int256(word: str) -> int:
    value = int(word, 16)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


def _signed_quote_value_e6(amount0_raw: int, amount1_raw: int, sqrt_price_x96: int, quote_decimals: int) -> int:
    sign0 = -1 if amount0_raw < 0 else 1
    sign1 = -1 if amount1_raw < 0 else 1
    value0 = quote_value_e6(abs(amount0_raw), 0, sqrt_price_x96, quote_decimals)
    value1 = quote_value_e6(0, abs(amount1_raw), sqrt_price_x96, quote_decimals)
    return sign0 * value0 + sign1 * value1


def _human_signed(value: int, decimals: int) -> str:
    sign = "-" if value < 0 else ""
    scale = 10**decimals
    whole = abs(value) // scale
    frac = abs(value) % scale
    if decimals == 0:
        return f"{sign}{whole}"
    return f"{sign}{whole}.{frac:0{decimals}d}".rstrip("0").rstrip(".")


def _usd_e6(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _na(value: object) -> str:
    return "n/a" if value is None else str(value)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Scan real Uniswap v4 position lifecycle logs")
    parser.add_argument("--rpc-url", default=os.environ.get("BASE_RPC_URL") or "https://mainnet.base.org")
    parser.add_argument("--metadata-json", type=Path, default=root / "docs" / "real_position_metadata.json")
    parser.add_argument("--checkpoint-json", type=Path, default=root / "docs" / "real_position_lifecycle_checkpoint.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "real_position_lifecycle.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "real_position_lifecycle.json")
    parser.add_argument("--chunk-blocks", type=int, default=10_000)
    parser.add_argument("--max-chunks", type=int)
    parser.add_argument("--sleep-sec", type=float, default=0.0)
    args = parser.parse_args()
    metadata = _load_json(args.metadata_json)
    if not metadata:
        raise SystemExit(f"missing metadata: {args.metadata_json}")
    report = compute(
        args.rpc_url,
        metadata,
        args.checkpoint_json,
        chunk_blocks=args.chunk_blocks,
        max_chunks=args.max_chunks,
        sleep_sec=args.sleep_sec,
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"lifecycle status={report['status']} events={len(report.get('events', []))}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["status"] == "lifecycle scanned" else 2


if __name__ == "__main__":
    raise SystemExit(main())
