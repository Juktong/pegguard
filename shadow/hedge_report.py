from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import Event, fixture_events
from .inventory_report import POLICIES as INVENTORY_POLICIES
from .inventory_report import InventoryPolicy


@dataclass(frozen=True)
class HedgePolicy:
    name: str
    rebalance_price_move_bps: int | None
    cost_bps: float


@dataclass(frozen=True)
class HedgeRow:
    window: str
    range_policy: str
    hedge_policy: str
    capital_e6: int
    cost_bps: float
    start_price_e6: int
    end_price_e6: int
    price_move_bps: float
    rebalances: int
    hedge_turnover_e6: int
    hedge_cost_e6: int
    hedge_pnl_e6: int
    unhedged_inventory_il_e6: int
    hedged_inventory_pnl_e6: int
    hedge_improvement_e6: int
    max_hedged_drawdown_e6: int


HEDGE_POLICIES = [
    HedgePolicy("open only", None, 1.0),
    HedgePolicy("50 bps drift", 50, 1.0),
    HedgePolicy("every event", 0, 1.0),
]


def compute(root: Path, capital_e6: int = 10_000_000_000) -> dict:
    rows: list[HedgeRow] = []
    for window in ("calm", "vol"):
        events, _ = fixture_events(root, window)
        for range_policy in INVENTORY_POLICIES:
            for hedge_policy in HEDGE_POLICIES:
                rows.append(_hedge_row(window, events, range_policy, hedge_policy, capital_e6))
    return {
        "capital_e6": capital_e6,
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Hedge Stress",
        "",
        "This report simulates short-token0 hedges for static concentrated LP",
        "inventory on the real calm and volatile fixture price paths. It isolates",
        "whether delta hedging improves inventory PnL after explicit hedge turnover",
        "cost. It does not include funding, borrow constraints, or route-away.",
        "",
        f"- Position capital: {_usd(int(report.get('capital_e6', 0)))}",
        "",
        "| Window | Range | Hedge | Rebalances | Hedge turnover | Hedge cost | Hedge PnL | Unhedged IL | Hedged inventory PnL | Improvement | Max hedged drawdown |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['range_policy']} | {row['hedge_policy']} | {int(row['rebalances'])} | "
            f"{_usd(int(row['hedge_turnover_e6']))} | {_usd(int(row['hedge_cost_e6']))} | "
            f"{_usd(int(row['hedge_pnl_e6']))} | {_usd(int(row['unhedged_inventory_il_e6']))} | "
            f"{_usd(int(row['hedged_inventory_pnl_e6']))} | {_usd(int(row['hedge_improvement_e6']))} | "
            f"{_usd(int(row['max_hedged_drawdown_e6']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Hedge PnL assumes a short token0 hedge sized to the LP's token0 amount.",
            "- `open only` hedges the starting token0 exposure and never rebalances.",
            "- `50 bps drift` rebalances when price moves 50 bps from the last hedge.",
            "- `every event` is an upper-bound tracking policy and can overstate operational feasibility.",
            "- Hedge costs include initial opening turnover plus rebalance turnover at the listed cost bps.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _hedge_row(
    window: str,
    events: list[Event],
    range_policy: InventoryPolicy,
    hedge_policy: HedgePolicy,
    capital_e6: int,
) -> HedgeRow:
    prices = [event.mid_e18 / 1e18 for event in events]
    start_price = prices[0]
    end_price = prices[-1]
    lower = start_price * (1 - range_policy.half_width_bps / 10_000)
    upper = start_price * (1 + range_policy.half_width_bps / 10_000)
    unit_value = _position_value(1.0, start_price, lower, upper)
    liquidity = (capital_e6 / 1_000_000) / unit_value
    start_amount0, start_amount1 = _amounts(liquidity, start_price, lower, upper)
    hedge_amount0 = start_amount0
    hedge_turnover = hedge_amount0 * start_price
    hedge_cost = hedge_turnover * hedge_policy.cost_bps / 10_000
    hedge_pnl = 0.0
    rebalances = 0
    last_rebalance_price = start_price
    max_drawdown = 0
    previous_price = start_price

    for price in prices[1:]:
        hedge_pnl += hedge_amount0 * (previous_price - price)
        previous_price = price
        current_amount0, _ = _amounts(liquidity, price, lower, upper)
        if _should_rebalance(hedge_policy, last_rebalance_price, price):
            turnover = abs(current_amount0 - hedge_amount0) * price
            hedge_turnover += turnover
            hedge_cost += turnover * hedge_policy.cost_bps / 10_000
            hedge_amount0 = current_amount0
            last_rebalance_price = price
            rebalances += 1
        lp_value = _position_value(liquidity, price, lower, upper)
        hodl_value = start_amount0 * price + start_amount1
        hedged = lp_value + hedge_pnl - hedge_cost - hodl_value
        max_drawdown = min(max_drawdown, int(round(hedged * 1_000_000)))

    lp_end = _position_value(liquidity, end_price, lower, upper)
    hodl_end = start_amount0 * end_price + start_amount1
    inventory_il = lp_end - hodl_end
    hedged_inventory = inventory_il + hedge_pnl - hedge_cost
    return HedgeRow(
        window=window,
        range_policy=range_policy.name,
        hedge_policy=hedge_policy.name,
        capital_e6=capital_e6,
        cost_bps=hedge_policy.cost_bps,
        start_price_e6=int(round(start_price * 1_000_000)),
        end_price_e6=int(round(end_price * 1_000_000)),
        price_move_bps=((end_price / start_price) - 1) * 10_000,
        rebalances=rebalances,
        hedge_turnover_e6=int(round(hedge_turnover * 1_000_000)),
        hedge_cost_e6=int(round(hedge_cost * 1_000_000)),
        hedge_pnl_e6=int(round(hedge_pnl * 1_000_000)),
        unhedged_inventory_il_e6=int(round(inventory_il * 1_000_000)),
        hedged_inventory_pnl_e6=int(round(hedged_inventory * 1_000_000)),
        hedge_improvement_e6=int(round((hedged_inventory - inventory_il) * 1_000_000)),
        max_hedged_drawdown_e6=max_drawdown,
    )


def _should_rebalance(policy: HedgePolicy, last_price: float, price: float) -> bool:
    if policy.rebalance_price_move_bps is None:
        return False
    if policy.rebalance_price_move_bps == 0:
        return True
    return abs((price / last_price - 1) * 10_000) >= policy.rebalance_price_move_bps


def _amounts(liquidity: float, price: float, lower: float, upper: float) -> tuple[float, float]:
    sqrt_price = math.sqrt(price)
    sqrt_lower = math.sqrt(lower)
    sqrt_upper = math.sqrt(upper)
    if price <= lower:
        return liquidity * (sqrt_upper - sqrt_lower) / (sqrt_lower * sqrt_upper), 0.0
    if price >= upper:
        return 0.0, liquidity * (sqrt_upper - sqrt_lower)
    amount0 = liquidity * (sqrt_upper - sqrt_price) / (sqrt_price * sqrt_upper)
    amount1 = liquidity * (sqrt_price - sqrt_lower)
    return amount0, amount1


def _position_value(liquidity: float, price: float, lower: float, upper: float) -> float:
    amount0, amount1 = _amounts(liquidity, price, lower, upper)
    return amount0 * price + amount1


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Simulate delta-hedged LP inventory on fixture price paths")
    parser.add_argument("--capital-e6", type=int, default=10_000_000_000)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "hedge_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "hedge_report.json")
    args = parser.parse_args()
    report = compute(root, args.capital_e6)
    write_outputs(report, args.out_md, args.out_json)
    print(f"hedge report rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
