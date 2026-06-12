from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C

TRADE_SIZES_E6 = (1_000_000_000, 10_000_000_000, 50_000_000_000, 100_000_000_000)
DEPTH_BAND_BPS = 50
PEGGUARD_BASE_FEE_PIPS = 500


@dataclass(frozen=True)
class RouteCostRow:
    pair: str
    trade_size_e6: int
    fee_pips: int
    depth_band_bps: int
    active_depth_e6: int
    fee_bps: float
    impact_bps: float | None
    total_cost_bps: float | None
    rank: int | None
    pegguard_headroom_bps: float | None
    status: str


def compute(
    depth_proxy_json: Path,
    cross_pair_depth_proxy_json: Path | None = None,
    trade_sizes_e6: tuple[int, ...] = TRADE_SIZES_E6,
    depth_band_bps: int = DEPTH_BAND_BPS,
) -> dict:
    proxies = [_load_json(depth_proxy_json)]
    if cross_pair_depth_proxy_json is not None:
        cross = _load_json(cross_pair_depth_proxy_json)
        if cross:
            proxies.append(cross)
    rows: list[RouteCostRow] = []
    for proxy in proxies:
        rows.extend(_rows_for_proxy(proxy, trade_sizes_e6, depth_band_bps))
    return {
        "depth_sources": [str(path) for path in (depth_proxy_json, cross_pair_depth_proxy_json) if path is not None],
        "depth_band_bps": depth_band_bps,
        "trade_sizes_e6": list(trade_sizes_e6),
        "model": "fee_bps + trade_size / active_depth_at_band * band_bps",
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Depth-Adjusted Route Cost Proxy",
        "",
        "This report is routeability context. It is not a real quoter call. It uses",
        "the active v3 depth snapshots and estimates an all-in route cost as explicit",
        "fee plus linearized price impact inside the selected depth band.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Depth band: {int(report.get('depth_band_bps', 0))} bps",
        "",
        "| Pair | Trade size | Fee tier | Active depth | Fee bps | Impact bps | Total cost bps | Rank | 5 bps headroom | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {_usd(int(row['trade_size_e6']))} | {int(row['fee_pips']) / 100:.2f} bps | "
            f"{_usd(int(row['active_depth_e6']))} | {float(row['fee_bps']):.2f} | {_float(row.get('impact_bps'))} | "
            f"{_float(row.get('total_cost_bps'))} | {_rank(row.get('rank'))} | {_float(row.get('pegguard_headroom_bps'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `5 bps headroom` is how much extra premium the 5 bps tier could add before another observed fee tier is cheaper under this proxy.",
            "- Negative headroom means the 5 bps tier is already not the cheapest route in the linearized depth model for that trade size.",
            "- This should be read beside the route-away proxy and controlled route-away gate; it cannot observe router behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _rows_for_proxy(proxy: dict, trade_sizes_e6: tuple[int, ...], depth_band_bps: int) -> list[RouteCostRow]:
    pair = str(proxy.get("pair", "n/a"))
    rows: list[RouteCostRow] = []
    tiers = sorted(proxy.get("tiers", []), key=lambda row: int(row.get("fee_pips", 0)))
    for size in trade_sizes_e6:
        cost_by_fee: dict[int, float] = {}
        tier_depths: dict[int, int] = {}
        for tier in tiers:
            fee_pips = int(tier.get("fee_pips", 0))
            depth = _tier_depth(tier, depth_band_bps)
            tier_depths[fee_pips] = depth
            cost = _total_cost_bps(size, fee_pips, depth, depth_band_bps)
            if cost is not None:
                cost_by_fee[fee_pips] = cost
        ranked = {fee: rank for rank, fee in enumerate(sorted(cost_by_fee, key=lambda fee: cost_by_fee[fee]), start=1)}
        peg_cost = cost_by_fee.get(PEGGUARD_BASE_FEE_PIPS)
        best_alt = min((cost for fee, cost in cost_by_fee.items() if fee != PEGGUARD_BASE_FEE_PIPS), default=None)
        headroom = (best_alt - peg_cost) if peg_cost is not None and best_alt is not None else None
        for tier in tiers:
            fee_pips = int(tier.get("fee_pips", 0))
            depth = tier_depths.get(fee_pips, 0)
            fee_bps = fee_pips / 100
            impact = _impact_bps(size, depth, depth_band_bps)
            total = _total_cost_bps(size, fee_pips, depth, depth_band_bps)
            rows.append(
                RouteCostRow(
                    pair=pair,
                    trade_size_e6=size,
                    fee_pips=fee_pips,
                    depth_band_bps=depth_band_bps,
                    active_depth_e6=depth,
                    fee_bps=fee_bps,
                    impact_bps=impact,
                    total_cost_bps=total,
                    rank=ranked.get(fee_pips),
                    pegguard_headroom_bps=headroom if fee_pips == PEGGUARD_BASE_FEE_PIPS else None,
                    status=_status(fee_pips, total, ranked.get(fee_pips), headroom),
                )
            )
    return rows


def _tier_depth(tier: dict, depth_band_bps: int) -> int:
    for item in tier.get("depths", []):
        if int(item.get("band_bps", 0)) == depth_band_bps:
            return int(item.get("min_side_quote_e6", 0))
    return 0


def _impact_bps(trade_size_e6: int, active_depth_e6: int, depth_band_bps: int) -> float | None:
    if trade_size_e6 <= 0 or active_depth_e6 <= 0:
        return None
    return (trade_size_e6 / active_depth_e6) * depth_band_bps


def _total_cost_bps(trade_size_e6: int, fee_pips: int, active_depth_e6: int, depth_band_bps: int) -> float | None:
    impact = _impact_bps(trade_size_e6, active_depth_e6, depth_band_bps)
    if impact is None:
        return None
    return fee_pips / 100 + impact


def _status(fee_pips: int, total_cost_bps: float | None, rank: int | None, headroom: float | None) -> str:
    if total_cost_bps is None:
        return "no depth"
    if fee_pips == PEGGUARD_BASE_FEE_PIPS:
        if headroom is None:
            return "no alternative"
        if headroom >= 0:
            return "premium headroom"
        return "already behind"
    if rank == 1:
        return "best proxy route"
    return "alternative"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _float(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def _rank(value: object) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Estimate depth-adjusted fee-tier route costs")
    parser.add_argument("--depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy.json")
    parser.add_argument("--cross-pair-depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy_weth_usdt.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_cost_proxy.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_cost_proxy.json")
    args = parser.parse_args()
    report = compute(args.depth_proxy_json, args.cross_pair_depth_proxy_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route cost proxy rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
