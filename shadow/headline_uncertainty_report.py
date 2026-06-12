from __future__ import annotations

import argparse
import json
import random
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import (
    BASE_FEE_PIPS,
    GAS_SCENARIOS,
    PIPS_DENOM,
    SMALL_CAPITAL_POLICIES,
    YEAR_DAYS,
    fixture_events,
)

ITERATIONS = 500
SEED = 20260607
ROUTE_AWAY = 0.25
GAS_SCENARIO_NAME = "hook + Pyth, low L2"


@dataclass(frozen=True)
class HeadlineEvent:
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    premium_total_e6: int
    premium_correct_e6: int


@dataclass(frozen=True)
class HeadlineWindow:
    window: str
    rows: int
    iterations: int
    seed: int
    precision_point: float | None
    precision_p05: float | None
    precision_p50: float | None
    precision_p95: float | None
    capture_point: float | None
    capture_p05: float | None
    capture_p50: float | None
    capture_p95: float | None
    net_bps_point: float
    net_bps_p05: float
    net_bps_p50: float
    net_bps_p95: float


@dataclass(frozen=True)
class PolicyWindow:
    window: str
    policy: str
    scenario: str
    route_away: float
    capital_usdc: float
    rows: int
    iterations: int
    net_apr_point: float
    net_apr_p05: float
    net_apr_p50: float
    net_apr_p95: float
    annual_net_usdc_p50: float


def compute(
    root: Path | None = None,
    live_db: Path | None = None,
    iterations: int = ITERATIONS,
    seed: int = SEED,
) -> dict:
    root = root or C.repo_root()
    windows: list[tuple[str, list[HeadlineEvent]]] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        windows.append(("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        windows.append((window, [_fixture_event(event) for event in fixture]))

    window_rows = [asdict(_window_ci(window, events, iterations, seed)) for window, events in windows]
    policy_rows = [
        asdict(row)
        for window, events in windows
        for row in _policy_ci_rows(window, events, iterations, seed)
    ]
    return {
        "iterations": iterations,
        "seed": seed,
        "route_away": ROUTE_AWAY,
        "gas_scenario": GAS_SCENARIO_NAME,
        "windows": window_rows,
        "policies": policy_rows,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Headline Economic Uncertainty",
        "",
        "This report bootstraps valid-truth swap events with replacement to put",
        "uncertainty bands around the headline economic claims. It is measurement",
        "only and does not change calibration constants.",
        "",
        f"- Iterations: {int(report.get('iterations', 0))}",
        f"- Seed: {int(report.get('seed', 0))}",
        f"- Route-away assumption: {float(report.get('route_away', 0)):.0%}",
        f"- Gas scenario: {report.get('gas_scenario', 'n/a')}",
        "",
        "## Signal Economics",
        "",
        "| Window | Rows | Precision point | Precision p05/p50/p95 | Capture point | Capture p05/p50/p95 | Net bps point | Net bps p05/p50/p95 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("windows", []):
        lines.append(
            f"| {row['window']} | {int(row['rows'])} | {_pct(row.get('precision_point'))} | "
            f"{_pct_triplet(row.get('precision_p05'), row.get('precision_p50'), row.get('precision_p95'))} | "
            f"{_pct(row.get('capture_point'))} | "
            f"{_pct_triplet(row.get('capture_p05'), row.get('capture_p50'), row.get('capture_p95'))} | "
            f"{float(row['net_bps_point']):.2f} | "
            f"{float(row['net_bps_p05']):.2f} / {float(row['net_bps_p50']):.2f} / {float(row['net_bps_p95']):.2f} |"
        )

    lines.extend(
        [
            "",
            "## Small-Capital APR Bands",
            "",
            "APR bands use the same small-capital policy definitions as",
            "`economic_tests.json`, the stated route-away haircut, and the low-L2",
            "hook-plus-Pyth gas scenario.",
            "",
            "| Window | Policy | Capital | APR point | APR p05/p50/p95 | Annual net p50 |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in report.get("policies", []):
        lines.append(
            f"| {row['window']} | {row['policy']} | ${float(row['capital_usdc']):,.0f} | "
            f"{float(row['net_apr_point']):.2%} | "
            f"{float(row['net_apr_p05']):.2%} / {float(row['net_apr_p50']):.2%} / {float(row['net_apr_p95']):.2%} | "
            f"{_usd_float(float(row['annual_net_usdc_p50']))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The p05/p95 range is event-mix uncertainty, not a forecast of future regimes.",
            "- `live shadow` rows use only swaps with valid truth labels; the bands are same-swaps evidence and still do not measure real route-away.",
            "- Policy APR bands inherit the modeled route-away and gas assumptions; they are not evidence of real route retention.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _window_ci(window: str, events: list[HeadlineEvent], iterations: int, seed: int) -> HeadlineWindow:
    samples = _sample_stats(window, events, iterations, seed)
    point = _stats(events)
    return HeadlineWindow(
        window=window,
        rows=len(events),
        iterations=iterations,
        seed=seed,
        precision_point=point["precision"],
        precision_p05=_pctl_optional(samples["precision"], 5),
        precision_p50=_pctl_optional(samples["precision"], 50),
        precision_p95=_pctl_optional(samples["precision"], 95),
        capture_point=point["capture"],
        capture_p05=_pctl_optional(samples["capture"], 5),
        capture_p50=_pctl_optional(samples["capture"], 50),
        capture_p95=_pctl_optional(samples["capture"], 95),
        net_bps_point=float(point["net_bps"] or 0.0),
        net_bps_p05=_pctl_float(samples["net_bps"], 5),
        net_bps_p50=_pctl_float(samples["net_bps"], 50),
        net_bps_p95=_pctl_float(samples["net_bps"], 95),
    )


def _policy_ci_rows(window: str, events: list[HeadlineEvent], iterations: int, seed: int) -> list[PolicyWindow]:
    gas = next(scenario for scenario in GAS_SCENARIOS if scenario.name == GAS_SCENARIO_NAME)
    rows: list[PolicyWindow] = []
    point = _stats(events, route_away=ROUTE_AWAY, gas_per_swap=gas.hook_gas + gas.pyth_update_gas, gas_price_gwei=gas.gas_price_gwei, eth_usd=gas.eth_usd)
    sample_stats = _sample_stats(
        window,
        events,
        iterations,
        seed,
        route_away=ROUTE_AWAY,
        gas_per_swap=gas.hook_gas + gas.pyth_update_gas,
        gas_price_gwei=gas.gas_price_gwei,
        eth_usd=gas.eth_usd,
    )
    for policy in SMALL_CAPITAL_POLICIES:
        point_apr = _policy_apr(float(point["net_bps"] or 0.0), policy)
        apr_values = [_policy_apr(net_bps, policy) for net_bps in sample_stats["net_bps"]]
        p50 = _pctl_float(apr_values, 50)
        rows.append(
            PolicyWindow(
                window=window,
                policy=policy.name,
                scenario=GAS_SCENARIO_NAME,
                route_away=ROUTE_AWAY,
                capital_usdc=float(policy.capital_usdc),
                rows=len(events),
                iterations=iterations,
                net_apr_point=point_apr,
                net_apr_p05=_pctl_float(apr_values, 5),
                net_apr_p50=p50,
                net_apr_p95=_pctl_float(apr_values, 95),
                annual_net_usdc_p50=float(policy.capital_usdc) * p50,
            )
        )
    return rows


def _sample_stats(
    window: str,
    events: list[HeadlineEvent],
    iterations: int,
    seed: int,
    route_away: float = 0.0,
    gas_per_swap: int = 0,
    gas_price_gwei: float = 0.0,
    eth_usd: float = 0.0,
) -> dict[str, list[float]]:
    rng = random.Random(f"{seed}:{window}:{route_away}:{gas_per_swap}:{gas_price_gwei}:{eth_usd}")
    values: dict[str, list[float]] = {"precision": [], "capture": [], "net_bps": []}
    rows = len(events)
    for _ in range(iterations):
        sample = [events[rng.randrange(rows)] for _ in range(rows)] if rows else []
        stats = _stats(sample, route_away, gas_per_swap, gas_price_gwei, eth_usd)
        if stats["precision"] is not None:
            values["precision"].append(float(stats["precision"]))
        if stats["capture"] is not None:
            values["capture"].append(float(stats["capture"]))
        values["net_bps"].append(float(stats["net_bps"] or 0.0))
    return values


def _stats(
    events: list[HeadlineEvent],
    route_away: float = 0.0,
    gas_per_swap: int = 0,
    gas_price_gwei: float = 0.0,
    eth_usd: float = 0.0,
) -> dict[str, float | None]:
    notional = sum(event.notional_e6 for event in events)
    base = sum(event.base_fee_e6 for event in events)
    extra = sum(event.extra_e6 for event in events)
    markout = sum(event.markout_e6 for event in events)
    premium_total = sum(event.premium_total_e6 for event in events)
    premium_correct = sum(event.premium_correct_e6 for event in events)
    gas = _gas_cost_e6(len(events), gas_per_swap, gas_price_gwei, eth_usd)
    net = base + int(extra * (1 - route_away)) - markout - gas
    return {
        "precision": premium_correct / premium_total if premium_total else None,
        "capture": extra / abs(markout) if markout else None,
        "net_bps": _bps(net, notional),
    }


def _fixture_event(event) -> HeadlineEvent:
    base = (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
    premium_total = event.peg_extra_e6 if event.peg_premium_pips > 0 else 0
    premium_correct = premium_total if event.truth_corr == 1 else 0
    return HeadlineEvent(event.notional_e6, base, event.peg_extra_e6, event.truth_markout_e6, premium_total, premium_correct)


def _live_events(db: Path) -> list[HeadlineEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    events: list[HeadlineEvent] = []
    for row in rows:
        notional = abs(int(row["aq_e6"]))
        base = (notional * BASE_FEE_PIPS) // PIPS_DENOM
        extra = int(row["fresh_extra_e6"] or 0)
        premium_total = extra if int(row["fresh_premium_pips"] or 0) > 0 else 0
        premium_correct = premium_total if int(row["truth_corr"] or 0) == 1 else 0
        events.append(HeadlineEvent(notional, base, extra, int(row["truth_mk_e6"] or 0), premium_total, premium_correct))
    return events


def _policy_apr(net_bps: float, policy) -> float:
    gross_apr = (net_bps / 10_000) * float(policy.turnover_per_day) * float(policy.active_ratio) * YEAR_DAYS
    rebalance_drag = (float(policy.rebalance_cost_bps) / 10_000) * int(policy.rebalances_per_year)
    return gross_apr - rebalance_drag


def _gas_cost_e6(swaps: int, gas_per_swap: int, gas_price_gwei: float, eth_usd: float) -> int:
    return int(swaps * gas_per_swap * gas_price_gwei * 1e-9 * eth_usd * 1_000_000)


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _pctl_float(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[(len(ordered) * pct) // 100]


def _pctl_optional(values: list[float], pct: int) -> float | None:
    if not values:
        return None
    return _pctl_float(values, pct)


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _pct_triplet(p05: object, p50: object, p95: object) -> str:
    if p05 is None or p50 is None or p95 is None:
        return "n/a"
    return f"{float(p05):.2%} / {float(p50):.2%} / {float(p95):.2%}"


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Bootstrap headline PegGuard economic metrics")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "headline_uncertainty_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "headline_uncertainty_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, args.iterations, args.seed)
    write_outputs(report, args.out_md, args.out_json)
    print(f"headline uncertainty windows={len(report['windows'])} policy_rows={len(report['policies'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
