from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute(proxy_paths: list[Path]) -> dict:
    rows: list[dict] = []
    summaries: list[dict] = []
    for path in proxy_paths:
        proxy = load_json(path)
        if not proxy:
            continue
        pair = str(proxy.get("pair", "n/a"))
        chain = str(proxy.get("chain", "n/a"))
        source = str(path)
        windows = proxy.get("comparison_windows") or [_comparison_from_proxy(proxy)]
        pair_rows = [_window_row(source, chain, pair, window) for window in windows if window]
        rows.extend(pair_rows)
        if pair_rows:
            summaries.append(_pair_summary(source, chain, pair, pair_rows))

    max_5bps_spread = max((float(row["share_5bps_spread_pp"]) for row in summaries), default=0.0)
    max_high_fee_spread = max((float(row["share_high_fee_spread_pp"]) for row in summaries), default=0.0)
    return {
        "model": (
            "fee-tier share placebo stability from real route-away proxy lookback windows; "
            "nested lookbacks estimate natural share drift and do not measure PegGuard route-away"
        ),
        "rows": rows,
        "pair_summaries": summaries,
        "max_5bps_spread_pp": max_5bps_spread,
        "max_high_fee_spread_pp": max_high_fee_spread,
        "complete": len(summaries) >= 2 and len(rows) >= 4,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Route-Share Placebo Stability",
        "",
        "This report uses the real fee-tier route-away proxy artifacts to quantify",
        "how much fee-tier volume share moves across nested lookback windows when",
        "there is no PegGuard treatment. It is route-share noise context for the",
        "future controlled A/B; it is not controlled route-away evidence.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Pairs: {len(report.get('pair_summaries', []))}",
        f"- Window rows: {len(report.get('rows', []))}",
        f"- Max 5 bps share spread: {float(report.get('max_5bps_spread_pp', 0)):.2f} pp",
        f"- Max 30 bps+ share spread: {float(report.get('max_high_fee_spread_pp', 0)):.2f} pp",
        "",
        "## Pair Summary",
        "",
        "| Pair | Chain | Windows | Total notional range | 5 bps share range | 5 bps spread | 30 bps+ share range | 30 bps+ spread |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("pair_summaries", []):
        lines.append(
            f"| {row['pair']} | {row['chain']} | {row['windows']} | "
            f"{_usd(row['min_total_notional_e6'])}-{_usd(row['max_total_notional_e6'])} | "
            f"{_pct(row['min_share_5bps'])}-{_pct(row['max_share_5bps'])} | "
            f"{float(row['share_5bps_spread_pp']):.2f} pp | "
            f"{_pct(row['min_share_high_fee'])}-{_pct(row['max_share_high_fee'])} | "
            f"{float(row['share_high_fee_spread_pp']):.2f} pp |"
        )
    lines.extend(
        [
            "",
            "## Lookback Rows",
            "",
            "| Pair | Lookback blocks | Duration | Total notional | 1 bps share | 5 bps share | 30 bps+ share |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {int(row['lookback_blocks']):,} | {float(row['duration_hours']):.2f}h | "
            f"{_usd(row['total_notional_e6'])} | {_pct(row['share_1bps'])} | "
            f"{_pct(row['share_5bps'])} | {_pct(row['share_high_fee'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- A future controlled PegGuard A/B should clear this natural share-drift scale before being treated as strong route-away evidence.",
            "- The rows are nested lookbacks, not independent pre/post windows; they are useful as placebo context only.",
            "- This report complements, but cannot replace, `docs/route_away_ab.md` with nonzero baseline and treatment notional.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _comparison_from_proxy(proxy: dict) -> dict:
    return {
        "lookback_blocks": proxy.get("lookback_blocks", 0),
        "duration_hours": proxy.get("duration_hours", 0),
        "total_notional_e6": proxy.get("total_notional_e6", 0),
        "high_fee_volume_share": proxy.get("high_fee_volume_share", 0),
        "tiers": proxy.get("tiers", []),
    }


def _window_row(source: str, chain: str, pair: str, window: dict) -> dict:
    return {
        "source": source,
        "chain": chain,
        "pair": pair,
        "lookback_blocks": int(window.get("lookback_blocks", 0)),
        "duration_hours": float(window.get("duration_hours", 0)),
        "total_notional_e6": int(window.get("total_notional_e6", 0)),
        "share_1bps": _tier_share(window, 100),
        "share_5bps": _tier_share(window, 500),
        "share_high_fee": float(window.get("high_fee_volume_share", 0)),
    }


def _pair_summary(source: str, chain: str, pair: str, rows: list[dict]) -> dict:
    share_5 = [float(row["share_5bps"]) for row in rows]
    high = [float(row["share_high_fee"]) for row in rows]
    notionals = [int(row["total_notional_e6"]) for row in rows]
    return {
        "source": source,
        "chain": chain,
        "pair": pair,
        "windows": len(rows),
        "min_total_notional_e6": min(notionals),
        "max_total_notional_e6": max(notionals),
        "min_share_5bps": min(share_5),
        "max_share_5bps": max(share_5),
        "share_5bps_spread_pp": (max(share_5) - min(share_5)) * 100,
        "min_share_high_fee": min(high),
        "max_share_high_fee": max(high),
        "share_high_fee_spread_pp": (max(high) - min(high)) * 100,
    }


def _tier_share(data: dict, fee_pips: int) -> float:
    for row in data.get("tiers", []):
        if int(row.get("fee_pips", 0)) == fee_pips:
            return float(row.get("volume_share", 0))
    return 0.0


def _usd(value_e6: int) -> str:
    return f"${int(value_e6) / 1_000_000:,.2f}"


def _pct(value: float) -> str:
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compute route-share placebo stability from route-away proxy artifacts")
    parser.add_argument(
        "--proxy-json",
        type=Path,
        action="append",
        default=[],
        help="route_away_proxy JSON artifact; repeat for each pair",
    )
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_share_stability_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_share_stability_report.json")
    args = parser.parse_args()
    paths = args.proxy_json or [root / "docs" / "route_away_proxy.json", root / "docs" / "route_away_proxy_weth_usdt.json"]
    report = compute(paths)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-share stability={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
