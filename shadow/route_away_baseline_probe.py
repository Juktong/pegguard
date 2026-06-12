from __future__ import annotations

import argparse
import asyncio
import json
import os
import tomllib
from pathlib import Path
from typing import Mapping

from . import constants as C
from .route_away_collect import collect_pool_window, validate_collection_preflight
from .route_away_collect import _expected_chain_id, _rpc_client
from .route_away_window_plan import compute as compute_window_plan


DEFAULT_FINALITY_LAG_BLOCKS = 20


def compute_static(root: Path | None = None, env: Mapping[str, str] | None = None) -> dict:
    root = root or C.repo_root()
    rpc_url, rpc_source = _rpc_url(root, env)
    rows = _planned_rows(root)
    return {
        "status": "ready to execute" if rpc_url and rows else "missing inputs",
        "executed": False,
        "complete": False,
        "not_route_away_evidence": True,
        "rpc_url_resolved": bool(rpc_url),
        "rpc_url_source": rpc_source,
        "pair_count": len(rows),
        "rows": rows,
        "note": (
            "Baseline-flow probe validates the public baseline side of the controlled route-away design. "
            "It does not include PegGuard treatment flow and does not satisfy the controlled route-away gate."
        ),
    }


async def compute_execute(
    root: Path | None = None,
    env: Mapping[str, str] | None = None,
    finality_lag_blocks: int = DEFAULT_FINALITY_LAG_BLOCKS,
    chunk_blocks: int = 5_000,
) -> dict:
    root = root or C.repo_root()
    report = compute_static(root, env)
    if not report["rpc_url_resolved"]:
        report["status"] = "missing rpc"
        return report
    if finality_lag_blocks < 0:
        raise ValueError("finality_lag_blocks must be nonnegative")
    if chunk_blocks <= 0:
        raise ValueError("chunk_blocks must be positive")

    rpc_url, _source = _rpc_url(root, env)
    assert rpc_url is not None
    rows = []
    rpc_by_chain: dict[str, object] = {}
    session_by_chain: dict[str, object] = {}
    try:
        for planned in report["rows"]:
            chain = str(planned["chain"])
            rpc = rpc_by_chain.get(chain)
            session = session_by_chain.get(chain)
            if rpc is None:
                rpc = _rpc_client(rpc_url, chain)
                session = await rpc.connect()
                actual_chain_id = int(str(await rpc.call(session, "eth_chainId", [])), 16)
                expected_chain_id = _expected_chain_id(chain)
                if expected_chain_id is not None and actual_chain_id != expected_chain_id:
                    raise ValueError(f"RPC chain id {actual_chain_id} does not match {chain} expected {expected_chain_id}")
                rpc_by_chain[chain] = rpc
                session_by_chain[chain] = session
            latest = int(str(await rpc.call(session, "eth_blockNumber", [])), 16)
            row = await _execute_row(
                rpc,
                session,
                planned,
                latest,
                finality_lag_blocks,
                chunk_blocks,
            )
            rows.append(row)
    finally:
        for session in session_by_chain.values():
            close = getattr(session, "close", None)
            if close is not None:
                maybe = close()
                if hasattr(maybe, "__await__"):
                    await maybe

    complete = bool(rows) and all(row.get("complete") for row in rows)
    return {
        **report,
        "status": "complete" if complete else "incomplete",
        "executed": True,
        "complete": complete,
        "finality_lag_blocks": finality_lag_blocks,
        "chunk_blocks": chunk_blocks,
        "rows": rows,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away Baseline Flow Probe",
        "",
        "This non-gating probe checks whether the recommended baseline pools have",
        "recent same-length windows with nonzero swap flow. It validates the RPC,",
        "v3 swap decoder, quote-token index, and baseline liquidity context before",
        "a real PegGuard treatment pool is available.",
        "",
        f"- Status: {report.get('status', 'unknown')}",
        f"- Executed RPC scan: {'yes' if report.get('executed') else 'no'}",
        f"- Counts for controlled route-away gate: no",
        f"- RPC source: {report.get('rpc_url_source', 'missing')}",
        "",
        "| Pair | Chain | Baseline pool | Window | Swaps | Notional | Status |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        windows = row.get("windows", [])
        if not windows:
            lines.append(
                f"| {row.get('pair', 'n/a')} | {row.get('chain', 'n/a')} | `{row.get('baseline_pool', 'n/a')}` | "
                f"planned {int(row.get('window_blocks', 0))} blocks | 0 | n/a | planned |"
            )
            continue
        for window in windows:
            lines.append(
                f"| {row.get('pair', 'n/a')} | {row.get('chain', 'n/a')} | `{row.get('baseline_pool', 'n/a')}` | "
                f"{window.get('label', 'n/a')} {window.get('start_block', 'n/a')}-{window.get('end_block', 'n/a')} | "
                f"{int(window.get('swaps', 0))} | {_usd(int(window.get('quote_notional_e6', 0)))} | "
                f"{'ok' if window.get('complete') else 'insufficient flow'} |"
            )
    lines.extend(["", str(report.get("note", "")), ""])
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


async def _execute_row(
    rpc,
    session,
    planned: dict,
    latest_block: int,
    finality_lag_blocks: int,
    chunk_blocks: int,
) -> dict:
    end_post = latest_block - finality_lag_blocks
    window_blocks = int(planned.get("window_blocks", 0))
    if window_blocks <= 0:
        return {**planned, "latest_block": latest_block, "complete": False, "windows": []}
    start_post = end_post - window_blocks + 1
    end_pre = start_post - 1
    start_pre = end_pre - window_blocks + 1
    if start_pre < 0:
        return {**planned, "latest_block": latest_block, "complete": False, "windows": []}

    pool = str(planned["baseline_pool"])
    await validate_collection_preflight(rpc, session, str(planned["chain"]), {"baseline": pool})
    windows = []
    for label, start, end in (("reference_pre", start_pre, end_pre), ("reference_post", start_post, end_post)):
        stats = await collect_pool_window(
            rpc,
            session,
            pool,
            "v3",
            None,
            start,
            end,
            int(planned["quote_token_index"]),
            int(planned["quote_decimals"]),
            chunk_blocks,
        )
        windows.append(
            {
                "label": label,
                "start_block": start,
                "end_block": end,
                "swaps": stats.swaps,
                "quote_notional_e6": stats.quote_notional_e6,
                "complete": stats.swaps > 0 and stats.quote_notional_e6 > 0,
            }
        )
    return {
        **planned,
        "latest_block": latest_block,
        "finality_lag_blocks": finality_lag_blocks,
        "complete": all(window["complete"] for window in windows),
        "windows": windows,
    }


def _planned_rows(root: Path) -> list[dict]:
    plan = compute_window_plan(
        root / "docs" / "route_ab_sizing_report.json",
        [root / "docs" / "route_away_proxy.json", root / "docs" / "route_away_proxy_weth_usdt.json"],
    )
    rows = []
    for row in plan.get("rows", []):
        rows.append(
            {
                "pair": row.get("pair"),
                "chain": row.get("chain"),
                "baseline_pool": row.get("baseline_pool"),
                "quote_token_index": row.get("quote_token_index"),
                "quote_decimals": row.get("quote_decimals"),
                "planned_window_hours": row.get("planned_window_hours"),
                "window_blocks": row.get("window_blocks"),
                "target_treatment_share": row.get("treatment_share"),
            }
        )
    return rows


def _rpc_url(root: Path, env: Mapping[str, str] | None) -> tuple[str | None, str]:
    env = env or os.environ
    for key in ("CHAIN_RPC_HTTP", "ARBITRUM_RPC_HTTP", "RPC_HTTP", "CHAIN_RPC_WSS", "ARBITRUM_RPC_WSS", "RPC_WSS"):
        value = env.get(key)
        if value:
            return value, key
    config_path = root / "shadow" / "config.toml"
    if config_path.exists():
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        rpc = config.get("rpc", {})
        for key in ("arbitrum_http_primary", "arbitrum_wss_primary", "arbitrum_wss_fallback"):
            value = rpc.get(key)
            if value:
                return str(value), f"shadow/config.toml:{key}"
    return None, "missing"


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Probe recent baseline flow for controlled route-away A/B readiness")
    parser.add_argument("--execute", action="store_true", help="run live RPC eth_getLogs scans")
    parser.add_argument("--finality-lag-blocks", type=int, default=DEFAULT_FINALITY_LAG_BLOCKS)
    parser.add_argument("--chunk-blocks", type=int, default=5_000)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_baseline_probe.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_baseline_probe.json")
    args = parser.parse_args()

    if args.execute:
        report = asyncio.run(compute_execute(root, finality_lag_blocks=args.finality_lag_blocks, chunk_blocks=args.chunk_blocks))
    else:
        report = compute_static(root)
    write_outputs(report, args.out_md, args.out_json)
    print(f"status={report['status']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report.get("complete") else (2 if args.execute else 0)


if __name__ == "__main__":
    raise SystemExit(main())
