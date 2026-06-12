from __future__ import annotations

import argparse
import json
import math
import os
import statistics
from pathlib import Path

from . import constants as C


DEFAULT_MIN_WINDOW_HOURS = 1.0


def compute(
    sizing_path: Path,
    route_proxy_paths: list[Path],
    fee_change_block: int | None = None,
    post_lag_blocks: int = 0,
    min_window_hours: float = DEFAULT_MIN_WINDOW_HOURS,
) -> dict:
    sizing = _load_json(sizing_path)
    proxy_by_pair = {
        str(row.get("pair", "")): row
        for row in (_proxy_row(path) for path in route_proxy_paths)
        if row.get("pair")
    }
    rows = []
    for recommendation in sizing.get("recommendations", []):
        pair = str(recommendation.get("pair", ""))
        proxy = proxy_by_pair.get(pair, {})
        block_time_sec = float(proxy.get("block_time_sec") or 0)
        target_hours = float(recommendation.get("hours_for_target_treatment_notional") or 0)
        window_hours = max(target_hours, min_window_hours)
        window_blocks = math.ceil((window_hours * 3600) / block_time_sec) if block_time_sec > 0 else 0
        ranges = _ranges(fee_change_block, post_lag_blocks, window_blocks)
        rows.append(
            {
                "pair": pair,
                "chain": str(recommendation.get("chain", proxy.get("chain", "n/a"))),
                "baseline_pool": str(recommendation.get("baseline_pool", proxy.get("baseline_pool", "n/a"))),
                "quote_token_index": recommendation.get("quote_token_index", proxy.get("quote_token_index")),
                "quote_decimals": recommendation.get("quote_decimals", proxy.get("quote_decimals")),
                "treatment_share": float(recommendation.get("pre_treatment_share", 0)),
                "target_hours": target_hours,
                "min_window_hours": min_window_hours,
                "planned_window_hours": window_hours,
                "empirical_block_time_sec": block_time_sec,
                "window_blocks": window_blocks,
                "fee_change_block": fee_change_block,
                "post_lag_blocks": post_lag_blocks,
                **ranges,
                "env": _env(recommendation, ranges, fee_change_block),
            }
        )
    return {
        "complete": bool(rows),
        "not_route_away_evidence": True,
        "fee_change_block_known": fee_change_block is not None,
        "sizing_source": str(sizing_path),
        "route_proxy_sources": [str(path) for path in route_proxy_paths],
        "post_lag_blocks": post_lag_blocks,
        "min_window_hours": min_window_hours,
        "rows": rows,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Controlled Route-Away Window Plan",
        "",
        "This is a non-gating operator plan. It converts the A/B sizing report",
        "into equal-length pre/post block windows once the real PegGuard fee-change",
        "block is known. It does not count as route-away evidence.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Fee-change block known: {'yes' if report.get('fee_change_block_known') else 'no'}",
        f"- Minimum window: {float(report.get('min_window_hours', 0)):.2f}h",
        f"- Post-change lag: {int(report.get('post_lag_blocks', 0))} blocks",
        "",
        "## Windows",
        "",
        "| Pair | Chain | Planned hours | Block time | Window blocks | Pre window | Post window |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {row['chain']} | {float(row['planned_window_hours']):.2f}h | "
            f"{float(row['empirical_block_time_sec']):.3f}s | {int(row['window_blocks'])} | "
            f"{_window(row.get('pre_start_block'), row.get('pre_end_block'))} | "
            f"{_window(row.get('post_start_block'), row.get('post_end_block'))} |"
        )

    lines.extend(
        [
            "",
            "## Collection Env",
            "",
            "Fill `TREATMENT_POOL`, `PEGGUARD_POOL_ID`, and",
            "`VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS` from the real deployment. If the",
            "fee-change block is still unknown, replace the `TODO_*` window values",
            "after enabling PegGuard premium.",
            "",
        ]
    )
    for row in report.get("rows", []):
        lines.extend([f"For {row['pair']}:", "", "```sh"])
        lines.extend(f"export {key}={value}" for key, value in row.get("env", {}).items())
        lines.extend(["```", ""])

    lines.extend(
        [
            "## Why This Is Non-Gating",
            "",
            "- It only plans block ranges; it does not collect baseline/treatment notional.",
            "- The controlled route-away gate still requires `docs/route_away_ab.json` with nonzero pre/post baseline and treatment notional.",
            "- Use the generated windows with `python3 -m shadow.route_away_collect` after the real PegGuard pool and post-window VWAP fee are known.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _proxy_row(path: Path) -> dict:
    data = _load_json(path)
    block_times = []
    for window in data.get("comparison_windows", []):
        blocks = int(window.get("lookback_blocks", 0))
        hours = float(window.get("duration_hours", 0))
        if blocks > 0 and hours > 0:
            block_times.append((hours * 3600) / blocks)
    blocks = int(data.get("lookback_blocks", 0))
    hours = float(data.get("duration_hours", 0))
    if blocks > 0 and hours > 0:
        block_times.append((hours * 3600) / blocks)
    return {
        "pair": str(data.get("pair", "")),
        "chain": str(data.get("chain", "")),
        "baseline_pool": _pool_for_fee(data, 500),
        "quote_token_index": data.get("quote_token_index"),
        "quote_decimals": data.get("quote_decimals"),
        "block_time_sec": statistics.median(block_times) if block_times else None,
    }


def _ranges(fee_change_block: int | None, post_lag_blocks: int, window_blocks: int) -> dict:
    if fee_change_block is None or window_blocks <= 0:
        return {
            "pre_start_block": None,
            "pre_end_block": None,
            "post_start_block": None,
            "post_end_block": None,
        }
    pre_start = fee_change_block - window_blocks
    pre_end = fee_change_block - 1
    post_start = fee_change_block + post_lag_blocks
    post_end = post_start + window_blocks - 1
    return {
        "pre_start_block": pre_start,
        "pre_end_block": pre_end,
        "post_start_block": post_start,
        "post_end_block": post_end,
    }


def _env(recommendation: dict, ranges: dict, fee_change_block: int | None) -> dict[str, str]:
    return {
        "ROUTE_AWAY_CHAIN": str(recommendation.get("chain", "TODO_CHAIN")),
        "ROUTE_AWAY_PAIR": str(recommendation.get("pair", "TODO_PAIR")),
        "BASELINE_POOL": str(recommendation.get("baseline_pool", "TODO_BASELINE_POOL")),
        "BASELINE_KIND": "v3",
        "TREATMENT_KIND": "v4",
        "TREATMENT_POOL": "TODO_POOL_MANAGER_OR_TREATMENT_POOL",
        "PEGGUARD_POOL_ID": "TODO_V4_POOL_ID",
        "FEE_CHANGE_BLOCK": str(fee_change_block) if fee_change_block is not None else "TODO_FEE_CHANGE_BLOCK",
        "PRE_START": _block_or_todo(ranges.get("pre_start_block"), "TODO_PRE_START_BLOCK"),
        "PRE_END": _block_or_todo(ranges.get("pre_end_block"), "TODO_PRE_END_BLOCK"),
        "POST_START": _block_or_todo(ranges.get("post_start_block"), "TODO_POST_START_BLOCK"),
        "POST_END": _block_or_todo(ranges.get("post_end_block"), "TODO_POST_END_BLOCK"),
        "PRE_TREATMENT_FEE_PIPS": "500",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "TODO_POST_VWAP_FEE_PIPS",
        "QUOTE_TOKEN_INDEX": str(recommendation.get("quote_token_index", "TODO_QUOTE_TOKEN_INDEX")),
        "QUOTE_DECIMALS": str(recommendation.get("quote_decimals", "TODO_QUOTE_DECIMALS")),
    }


def _pool_for_fee(route_proxy: dict, fee_pips: int) -> str | None:
    for row in route_proxy.get("tiers", []):
        if int(row.get("fee_pips", 0)) == fee_pips and row.get("pool"):
            return str(row["pool"])
    return None


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _block_or_todo(value: object, todo: str) -> str:
    return todo if value is None else str(value)


def _window(start: object, end: object) -> str:
    if start is None or end is None:
        return "TODO"
    return f"{start}-{end}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Plan equal pre/post block windows for controlled route-away collection")
    parser.add_argument("--sizing", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    parser.add_argument(
        "--route-proxy",
        type=Path,
        action="append",
        default=[root / "docs" / "route_away_proxy.json", root / "docs" / "route_away_proxy_weth_usdt.json"],
    )
    parser.add_argument("--fee-change-block", type=int, default=_env_int("FEE_CHANGE_BLOCK") or _env_int("ROUTE_AWAY_FEE_CHANGE_BLOCK"))
    parser.add_argument("--post-lag-blocks", type=int, default=0)
    parser.add_argument("--min-window-hours", type=float, default=DEFAULT_MIN_WINDOW_HOURS)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_window_plan.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_window_plan.json")
    args = parser.parse_args()
    report = compute(args.sizing, args.route_proxy, args.fee_change_block, args.post_lag_blocks, args.min_window_hours)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away window plan={'complete' if report['complete'] else 'incomplete'}")
    print(f"fee-change block known={'yes' if report['fee_change_block_known'] else 'no'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


def _env_int(name: str) -> int | None:
    value = os.environ.get(name)
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
