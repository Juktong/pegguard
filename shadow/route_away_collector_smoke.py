from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C
from .route_away_collect import V4_SWAP_TOPIC0, decode_v4_swap_log


DEFAULT_BROADCAST = Path("broadcast/TestnetExercise.s.sol/1301/run-latest.json")


def compute(
    root: Path,
    broadcast_path: Path | None = None,
    quote_token_index: int = 1,
    quote_decimals: int = 18,
) -> dict:
    path = broadcast_path or root / DEFAULT_BROADCAST
    payload = _load_json(path)
    logs = _v4_swap_logs(payload)
    decoded = [decode_v4_swap_log(log) for log in logs]
    scale = 10**quote_decimals
    quote_notional_e6 = sum(
        (abs(log.amount0 if quote_token_index == 0 else log.amount1) * 1_000_000) // scale
        for log in decoded
    )
    fee_weighted = sum(
        ((abs(log.amount0 if quote_token_index == 0 else log.amount1) * 1_000_000) // scale) * int(log.fee_pips)
        for log in decoded
        if log.fee_pips is not None
    )
    fee_observations = sum(1 for log in decoded if log.fee_pips is not None)
    vwap_fee_pips = None if quote_notional_e6 == 0 or fee_observations == 0 else fee_weighted // quote_notional_e6
    pool_ids = sorted({str(log.get("topics", ["", ""])[1]) for log in logs if len(log.get("topics", [])) > 1})
    block_numbers = sorted({log.block_number for log in decoded})
    tx_hashes = sorted({log.tx_hash for log in decoded})
    chain = payload.get("chain")
    return {
        "complete": bool(decoded),
        "not_route_away_evidence": True,
        "source": _rel(root, path),
        "chain": chain,
        "swap_logs": len(decoded),
        "pool_ids": pool_ids,
        "block_numbers": block_numbers,
        "tx_hashes": tx_hashes,
        "quote_token_index": quote_token_index,
        "quote_decimals": quote_decimals,
        "quote_notional_e6": quote_notional_e6,
        "vwap_fee_pips": vwap_fee_pips,
        "fee_observation_count": fee_observations,
        "notes": [
            "This decodes real v4 Swap logs from the TestnetExercise broadcast.",
            "It verifies collector plumbing only; it has no comparable baseline pool, pre/post windows, or live route choice.",
            "It must not satisfy the controlled route-away economics gate.",
        ],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away Collector Smoke",
        "",
        "This is a non-gating smoke test for v4 swap-log decoding and quote-notional",
        "summarization. It is not route-away economics evidence because it has no",
        "comparable baseline pool, no treatment-share control, and no pre/post fee",
        "change window.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'missing logs'}",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Chain: {report.get('chain', 'n/a')}",
        f"- v4 swap logs decoded: {int(report.get('swap_logs', 0))}",
        f"- Quote token index: {report.get('quote_token_index', 'n/a')}",
        f"- Quote decimals: {report.get('quote_decimals', 'n/a')}",
        f"- Quote notional: {_usd(int(report.get('quote_notional_e6', 0)))}",
        f"- Decoded VWAP fee: {_fee(report.get('vwap_fee_pips'))}",
        f"- Fee observations: {int(report.get('fee_observation_count', 0))}",
        f"- Counts for controlled route-away gate: no",
        "",
        "## Pools",
        "",
    ]
    pool_ids = report.get("pool_ids", [])
    if pool_ids:
        lines.extend(f"- `{pool_id}`" for pool_id in pool_ids)
    else:
        lines.append("- none")
    lines.extend(["", "## Transactions", ""])
    tx_hashes = report.get("tx_hashes", [])
    if tx_hashes:
        lines.extend(f"- `{tx_hash}`" for tx_hash in tx_hashes)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Why This Is Non-Gating",
            "",
        ]
    )
    lines.extend(f"- {note}" for note in report.get("notes", []))
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _v4_swap_logs(payload: dict) -> list[dict]:
    rows: list[dict] = []
    for receipt in payload.get("receipts", []):
        for log in receipt.get("logs", []):
            topics = log.get("topics") or []
            if topics and str(topics[0]).lower() == V4_SWAP_TOPIC0:
                rows.append(log)
    return rows


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.6f}"


def _fee(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value) / 100:.2f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Decode existing testnet v4 swap logs as a non-gating collector smoke")
    parser.add_argument("--broadcast", type=Path, default=root / DEFAULT_BROADCAST)
    parser.add_argument("--quote-token-index", type=int, choices=[0, 1], default=1)
    parser.add_argument("--quote-decimals", type=int, default=18)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_collector_smoke.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_collector_smoke.json")
    args = parser.parse_args()
    report = compute(root, args.broadcast, args.quote_token_index, args.quote_decimals)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away collector smoke={'complete' if report['complete'] else 'missing logs'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
