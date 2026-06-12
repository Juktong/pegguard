from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, Event, fixture_events


@dataclass(frozen=True)
class InventoryPolicy:
    name: str
    half_width_bps: int


@dataclass(frozen=True)
class InventoryRow:
    window: str
    policy: str
    capital_e6: int
    start_price_e6: int
    end_price_e6: int
    min_price_e6: int
    max_price_e6: int
    price_move_bps: float
    active_coverage: float
    lp_end_value_e6: int
    hodl_end_value_e6: int
    inventory_il_e6: int
    inventory_il_bps: float
    max_inventory_drawdown_e6: int
    full_flow_fee_upper_bound_e6: int


POLICIES = [
    InventoryPolicy("static +/-1%", 100),
    InventoryPolicy("static +/-3%", 300),
    InventoryPolicy("static +/-5%", 500),
]


def compute(root: Path, capital_e6: int = 10_000_000_000, database: Path | None = None) -> dict:
    rows: list[InventoryRow] = []
    for window in ("calm", "vol"):
        events, _ = fixture_events(root, window)
        rows.extend(inventory_rows_for_events(window, events, capital_e6))
    live_events = _live_events_from_db(database)
    rows.extend(inventory_rows_for_events("live shadow", live_events, capital_e6))
    return {
        "capital_e6": capital_e6,
        "live_database": None if database is None else str(database),
        "live_rows": len(live_events),
        "windows": [asdict(row) for row in rows],
    }


def inventory_rows_for_events(window: str, events: list[Event], capital_e6: int) -> list[InventoryRow]:
    if not events:
        return []
    prices = [event.mid_e18 / 1e18 for event in events]
    return [_inventory_row(window, policy, events, prices, capital_e6) for policy in POLICIES]


def markdown(report: dict) -> str:
    lines = [
        "# LP Inventory Accounting",
        "",
        "This report isolates static concentrated-LP inventory exposure on the real",
        "calm and volatile fixture price paths plus, when available, the live shadow",
        "database price path. It compares the final LP inventory value against holding",
        "the position's initial token amounts outside the pool.",
        "Fee upper bounds are full-flow fixture fees, not pro-rata LP earnings.",
        "",
        f"- Position capital: {_usd(int(report.get('capital_e6', 0)))}",
        f"- Live shadow rows: {int(report.get('live_rows', 0))}",
        "",
        "| Window | Policy | Active coverage | Start price | End price | Price move | LP end | HODL end | Inventory IL | IL bps | Max drawdown | Full-flow fee upper bound |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("windows", []):
        lines.append(
            f"| {row['window']} | {row['policy']} | {float(row['active_coverage']):.2%} | "
            f"{_price(int(row['start_price_e6']))} | {_price(int(row['end_price_e6']))} | "
            f"{float(row['price_move_bps']):.1f} bps | {_usd(int(row['lp_end_value_e6']))} | "
            f"{_usd(int(row['hodl_end_value_e6']))} | {_usd(int(row['inventory_il_e6']))} | "
            f"{float(row['inventory_il_bps']):.2f} | {_usd(int(row['max_inventory_drawdown_e6']))} | "
            f"{_usd(int(row['full_flow_fee_upper_bound_e6']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Inventory IL is price-path exposure only; it does not include markout, route-away, or pro-rata liquidity share.",
            "- Full-flow fee upper bound is useful as a scale check, but it is not a realizable LP fee estimate without pool-liquidity share.",
            "- Live shadow inventory uses observed swap price path from the local shadow database; it remains a static-range model, not exact position ownership.",
            "- Narrow static ranges can look good in inventory terms after leaving range, but then they stop earning fees for much of the path.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _inventory_row(window: str, policy: InventoryPolicy, events: list[Event], prices: list[float], capital_e6: int) -> InventoryRow:
    start_price = prices[0]
    end_price = prices[-1]
    lower = start_price * (1 - policy.half_width_bps / 10_000)
    upper = start_price * (1 + policy.half_width_bps / 10_000)
    unit_value = _position_value(1.0, start_price, lower, upper)
    liquidity = (capital_e6 / 1_000_000) / unit_value
    start_amount0, start_amount1 = _amounts(liquidity, start_price, lower, upper)

    active = 0
    full_flow_fee_upper_bound = 0
    max_drawdown = 0
    for event, price in zip(events, prices, strict=True):
        in_range = lower <= price <= upper
        if in_range:
            active += 1
            full_flow_fee_upper_bound += (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
            full_flow_fee_upper_bound += event.peg_extra_e6
        lp_value = _position_value(liquidity, price, lower, upper)
        hodl_value = start_amount0 * price + start_amount1
        drawdown_e6 = int(round((lp_value - hodl_value) * 1_000_000))
        max_drawdown = min(max_drawdown, drawdown_e6)

    lp_end = _position_value(liquidity, end_price, lower, upper)
    hodl_end = start_amount0 * end_price + start_amount1
    il_e6 = int(round((lp_end - hodl_end) * 1_000_000))
    return InventoryRow(
        window=window,
        policy=policy.name,
        capital_e6=capital_e6,
        start_price_e6=int(round(start_price * 1_000_000)),
        end_price_e6=int(round(end_price * 1_000_000)),
        min_price_e6=int(round(min(prices) * 1_000_000)),
        max_price_e6=int(round(max(prices) * 1_000_000)),
        price_move_bps=((end_price / start_price) - 1) * 10_000,
        active_coverage=active / len(events),
        lp_end_value_e6=int(round(lp_end * 1_000_000)),
        hodl_end_value_e6=int(round(hodl_end * 1_000_000)),
        inventory_il_e6=il_e6,
        inventory_il_bps=(il_e6 / capital_e6) * 10_000 if capital_e6 else 0.0,
        max_inventory_drawdown_e6=max_drawdown,
        full_flow_fee_upper_bound_e6=full_flow_fee_upper_bound,
    )


def _live_events_from_db(database: Path | None) -> list[Event]:
    if database is None or not database.exists():
        return []
    conn = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT ts_ms, pre_mid_e18, post_mid_e18, aq_e6, fresh_extra_e6, fresh_premium_pips
            FROM ledger
            ORDER BY ts_ms, block_number, log_index
            """
        ).fetchall()
    finally:
        conn.close()

    events: list[Event] = []
    for row in rows:
        mid_e18 = _positive_price(row["post_mid_e18"]) or _positive_price(row["pre_mid_e18"])
        if mid_e18 is None:
            continue
        notional_e6 = abs(int(row["aq_e6"]))
        extra_e6 = int(row["fresh_extra_e6"] or 0)
        premium_pips = int(row["fresh_premium_pips"] or 0)
        events.append(
            Event(
                t_ms=int(row["ts_ms"]),
                mid_e18=mid_e18,
                notional_e6=notional_e6,
                truth_markout_e6=0,
                truth_corr=0,
                peg_extra_e6=extra_e6,
                peg_premium_pips=premium_pips,
                raw_extra_e6=extra_e6,
                raw_premium_pips=premium_pips,
                no_deadband_extra_e6=extra_e6,
                no_deadband_premium_pips=premium_pips,
                alpha1_extra_e6=extra_e6,
                alpha1_premium_pips=premium_pips,
            )
        )
    return events


def _positive_price(value: object) -> int | None:
    price = int(value or 0)
    return price if price > 0 else None


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


def _price(price_e6: int) -> str:
    return f"${price_e6 / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live_shadow_20260607T082122Z.sqlite3"
    parser = argparse.ArgumentParser(description="Measure static LP inventory exposure on fixture price paths")
    parser.add_argument("--capital-e6", type=int, default=10_000_000_000)
    parser.add_argument("--database", type=Path, default=root / "shadow" / default_tag)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "inventory_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "inventory_report.json")
    args = parser.parse_args()
    report = compute(root, args.capital_e6, args.database)
    write_outputs(report, args.out_md, args.out_json)
    print(f"inventory report: rows={len(report['windows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
