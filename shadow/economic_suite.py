from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .pipeline import (
    Decision,
    ema_update,
    is_correcting,
    premium_pips,
    replay_event_result,
    replay_rows_exact,
)

BASE_FEE_PIPS = 500
STATIC_30BPS_PIPS = 3_000
PIPS_DENOM = 1_000_000
YEAR_DAYS = 365


@dataclass(frozen=True)
class Event:
    t_ms: int
    mid_e18: int
    notional_e6: int
    truth_markout_e6: int
    truth_corr: int
    peg_extra_e6: int
    peg_premium_pips: int
    raw_extra_e6: int
    raw_premium_pips: int
    no_deadband_extra_e6: int
    no_deadband_premium_pips: int
    alpha1_extra_e6: int
    alpha1_premium_pips: int


@dataclass(frozen=True)
class Metric:
    name: str
    window: str
    rows: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    premium_total_e6: int
    premium_correct_e6: int
    charged_rows: int
    charged_notional_e6: int
    charged_base_fee_e6: int
    charged_markout_e6: int

    @property
    def precision_bps(self) -> int | None:
        if self.premium_total_e6 == 0:
            return None
        return (self.premium_correct_e6 * 10_000) // self.premium_total_e6

    @property
    def capture_bps(self) -> int | None:
        if self.markout_e6 == 0 or self.extra_e6 == 0:
            return None
        return (self.extra_e6 * 10_000) // abs(self.markout_e6)

    @property
    def net_e6(self) -> int:
        return self.base_fee_e6 + self.extra_e6 - self.markout_e6

    @property
    def net_bps(self) -> float:
        if self.notional_e6 == 0:
            return 0.0
        return self.net_e6 / self.notional_e6 * 10_000

    @property
    def extra_bps(self) -> float:
        if self.notional_e6 == 0:
            return 0.0
        return self.extra_e6 / self.notional_e6 * 10_000

    @property
    def markout_bps(self) -> float:
        if self.notional_e6 == 0:
            return 0.0
        return self.markout_e6 / self.notional_e6 * 10_000


@dataclass(frozen=True)
class RouteAwayRow:
    window: str
    route_away: float
    premium_haircut_net_bps: float
    charged_flow_removal_net_bps: float
    charged_flow_realized_net_bps: float
    realized_turnover_multiplier: float


@dataclass(frozen=True)
class Policy:
    name: str
    capital_usdc: float
    turnover_per_day: float
    active_ratio: float
    rebalances_per_year: int
    rebalance_cost_bps: float


@dataclass(frozen=True)
class PolicyRow:
    window: str
    policy: str
    capital_usdc: float
    route_away: float
    net_apr: float
    annual_net_usdc: float


@dataclass(frozen=True)
class RangePolicy:
    name: str
    half_width_bps: int
    mode: str
    target_turnover_per_day: float
    rebalance_cost_bps: float
    interval_sec: int = 0


@dataclass(frozen=True)
class RangeRow:
    window: str
    policy: str
    active_coverage: float
    active_notional_e6: int
    rebalances: int
    rebalance_drag_e6: int
    extra_e6: int
    markout_e6: int
    net_bps_before_drag: float
    net_bps_after_drag: float


@dataclass(frozen=True)
class GasScenario:
    name: str
    hook_gas: int
    pyth_update_gas: int
    gas_price_gwei: float
    eth_usd: float
    note: str


@dataclass(frozen=True)
class GasRow:
    window: str
    scenario: str
    swaps: int
    gas_per_swap: int
    gas_price_gwei: float
    eth_usd: float
    gas_usdc_e6: int
    gas_bps: float
    peg_net_bps: float
    net_after_gas_bps: float
    note: str


@dataclass(frozen=True)
class GasAdjustedPolicyRow:
    window: str
    policy: str
    scenario: str
    capital_usdc: float
    turnover_per_day: float
    route_away: float
    net_bps_after_route: float
    gas_bps: float
    net_apr: float
    annual_net_usdc: float


POLICIES = [
    Policy("micro passive", 2_500, 1.0, 0.90, 12, 1.0),
    Policy("small active", 10_000, 3.0, 0.80, 52, 2.0),
    Policy("focused active", 25_000, 5.0, 0.75, 156, 1.5),
    Policy("serious ladder", 100_000, 3.0, 0.85, 104, 1.2),
    Policy("large ladder", 500_000, 2.0, 0.90, 52, 0.8),
]

RANGE_POLICIES = [
    RangePolicy("static +/-1%", 100, "static", 3.0, 0.0),
    RangePolicy("static +/-3%", 300, "static", 3.0, 0.0),
    RangePolicy("static +/-5%", 500, "static", 3.0, 0.0),
    RangePolicy("hourly +/-2%", 200, "interval", 5.0, 1.0, 3600),
    RangePolicy("exit recenter +/-1%", 100, "exit", 5.0, 1.0),
    RangePolicy("exit recenter +/-2%", 200, "exit", 5.0, 1.0),
]

SMALL_CAPITAL_POLICIES = POLICIES[:3]

# Scenario inputs, not calibrated hook constants. The hook gas values come from
# docs/gas_snapshot.md's isolated gas report. Pyth update gas is a conservative
# operator/caller allowance so the table bounds cost if the update is bundled.
GAS_SCENARIOS = [
    GasScenario("hook only, low L2", 52_699 + 84_925, 0, 0.005, 3_500.0, "isolated hook avg; no Pyth update subsidy"),
    GasScenario("hook + Pyth, low L2", 52_699 + 84_925, 90_000, 0.005, 3_500.0, "hook avg plus 90k Pyth update allowance"),
    GasScenario("hook + Pyth, stressed L2", 52_699 + 84_925, 90_000, 0.050, 3_500.0, "10x gas-price stress on the bundled path"),
]


def _load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _raw_decision(prev_mid_e18: int, fair_e18: int, ab_e18: int, aq_e6: int) -> Decision:
    if prev_mid_e18 == 0:
        return Decision("raw", fair_e18, None, None, None, 0, False, 0, 0, "BASIS_UNSEEDED")
    dev_e2 = ((fair_e18 * 1_000_000) // prev_mid_e18) - 1_000_000
    correcting = is_correcting(dev_e2, ab_e18 > 0)
    pips = premium_pips(abs(dev_e2), C.DEADBAND_CALM_E2) if correcting else 0
    extra_e6 = (abs(aq_e6) * pips) // PIPS_DENOM
    return Decision("raw", fair_e18, None, None, None, dev_e2, correcting, pips, extra_e6, "")


def fixture_events(root: Path, window: str) -> tuple[list[Event], dict[str, int]]:
    if window == "calm":
        rows = _load_json(root / "test" / "fixtures" / "calm_0530.json")
        truth_rows = _load_json(root / "test" / "fixtures" / "calm_0530_truth.json")
    elif window == "vol":
        rows = _load_json(root / "test" / "fixtures" / "vol_0523_hot90m.json")
        truth_rows = _load_json(root / "test" / "fixtures" / "vol_0523_truth.json")
    else:
        raise ValueError(f"unknown fixture window: {window}")

    parity = replay_rows_exact(rows, truth_rows, include_quantiles=True)
    basis_wad = 0
    last_obs_t_ms = 0
    prev_mid_e18 = 0
    events: list[Event] = []
    for row, truth in zip(rows, truth_rows, strict=True):
        t_ms = int(row["t_ms"])
        if t_ms != int(truth["t_ms"]):
            raise AssertionError(f"{window} t_ms mismatch")

        peg, _ = replay_event_result(
            basis_wad,
            prev_mid_e18,
            int(row["fair_e18"]),
            int(row["ab_e18"]),
            int(row["aq_e6"]),
            C.DEADBAND_CALM_E2,
        )
        no_deadband, _ = replay_event_result(
            basis_wad,
            prev_mid_e18,
            int(row["fair_e18"]),
            int(row["ab_e18"]),
            int(row["aq_e6"]),
            0,
        )
        alpha1, _ = replay_event_result(
            basis_wad,
            prev_mid_e18,
            int(row["fair_e18"]),
            int(row["ab_e18"]),
            int(row["aq_e6"]),
            C.DEADBAND_CALM_E2,
            1,
            1,
        )
        raw = _raw_decision(prev_mid_e18, int(row["fair_e18"]), int(row["ab_e18"]), int(row["aq_e6"]))

        if truth.get("valid"):
            events.append(
                Event(
                    t_ms=t_ms,
                    mid_e18=int(row["p_e18"]),
                    notional_e6=abs(int(row["aq_e6"])),
                    truth_markout_e6=int(truth["truth_mk_e6"]),
                    truth_corr=int(truth["truth_corr"]),
                    peg_extra_e6=peg.extra_e6,
                    peg_premium_pips=peg.premium_pips,
                    raw_extra_e6=raw.extra_e6,
                    raw_premium_pips=raw.premium_pips,
                    no_deadband_extra_e6=no_deadband.extra_e6,
                    no_deadband_premium_pips=no_deadband.premium_pips,
                    alpha1_extra_e6=alpha1.extra_e6,
                    alpha1_premium_pips=alpha1.premium_pips,
                )
            )

        obs = (int(row["p_e18"]) * C.WAD) // int(row["fair_e18"])
        dt = 0 if last_obs_t_ms == 0 else (t_ms - last_obs_t_ms) // 1000
        basis_wad = ema_update(basis_wad, obs, 1 if dt == 0 else dt)
        last_obs_t_ms = t_ms
        prev_mid_e18 = int(row["p_e18"])

    return events, {
        "rows": parity.rows,
        "valid_rows": parity.valid_rows,
        "precision_bps": parity.precision_bps,
        "capture_truth_bps": parity.capture_truth_bps,
        "dev_mae_e2": parity.dev_mae_e2,
    }


def metric_from_events(window: str, name: str, events: list[Event], extra_attr: str, premium_attr: str) -> Metric:
    notional = sum(event.notional_e6 for event in events)
    markout = sum(event.truth_markout_e6 for event in events)
    base_fee = sum((event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM for event in events)
    extra = sum(int(getattr(event, extra_attr)) for event in events)
    charged = [event for event in events if int(getattr(event, premium_attr)) > 0]
    premium_total = sum(int(getattr(event, extra_attr)) for event in charged)
    premium_correct = sum(int(getattr(event, extra_attr)) for event in charged if event.truth_corr == 1)
    charged_notional = sum(event.notional_e6 for event in charged)
    charged_base = sum((event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM for event in charged)
    charged_markout = sum(event.truth_markout_e6 for event in charged)
    return Metric(
        name=name,
        window=window,
        rows=len(events),
        notional_e6=notional,
        base_fee_e6=base_fee,
        extra_e6=extra,
        markout_e6=markout,
        premium_total_e6=premium_total,
        premium_correct_e6=premium_correct,
        charged_rows=len(charged),
        charged_notional_e6=charged_notional,
        charged_base_fee_e6=charged_base,
        charged_markout_e6=charged_markout,
    )


def static_metric(window: str, name: str, events: list[Event], pips: int) -> Metric:
    notional = sum(event.notional_e6 for event in events)
    markout = sum(event.truth_markout_e6 for event in events)
    base = sum((event.notional_e6 * pips) // PIPS_DENOM for event in events)
    return Metric(name, window, len(events), notional, base, 0, markout, 0, 0, 0, 0, 0, 0)


def live_shadow_metric(root: Path, db: Path | None = None) -> Metric | None:
    db = db or root / "shadow" / "shadow.sqlite3"
    if not db.exists():
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
        FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
        """
    ).fetchall()
    if not rows:
        return None
    notional = sum(abs(int(row["aq_e6"])) for row in rows)
    base = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in rows)
    extra = sum(int(row["fresh_extra_e6"] or 0) for row in rows)
    truth_rows = [row for row in rows if row["valid"]]
    if not truth_rows:
        return None
    markout = sum(int(row["truth_mk_e6"] or 0) for row in truth_rows)
    charged = [row for row in truth_rows if int(row["fresh_premium_pips"] or 0) > 0]
    premium_total = sum(int(row["fresh_extra_e6"] or 0) for row in charged)
    premium_correct = sum(int(row["fresh_extra_e6"] or 0) for row in charged if int(row["truth_corr"] or 0) == 1)
    charged_notional = sum(abs(int(row["aq_e6"])) for row in charged)
    charged_base = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in charged)
    charged_markout = sum(int(row["truth_mk_e6"] or 0) for row in charged)
    return Metric(
        "PegGuard live shadow",
        "live shadow",
        len(rows),
        notional,
        base,
        extra,
        markout,
        premium_total,
        premium_correct,
        len(charged),
        charged_notional,
        charged_base,
        charged_markout,
    )


def route_away_rows(metric: Metric, rates: list[float] | None = None) -> list[RouteAwayRow]:
    rates = rates or [0.0, 0.10, 0.25, 0.50, 0.75]
    rows = []
    for rate in rates:
        premium_haircut_net = metric.base_fee_e6 + int(metric.extra_e6 * (1 - rate)) - metric.markout_e6
        remaining_notional = metric.notional_e6 - int(metric.charged_notional_e6 * rate)
        removal_net = (
            metric.base_fee_e6
            - int(metric.charged_base_fee_e6 * rate)
            + int(metric.extra_e6 * (1 - rate))
            - (metric.markout_e6 - int(metric.charged_markout_e6 * rate))
        )
        rows.append(
            RouteAwayRow(
                window=metric.window,
                route_away=rate,
                premium_haircut_net_bps=_bps(premium_haircut_net, metric.notional_e6),
                charged_flow_removal_net_bps=_bps(removal_net, metric.notional_e6),
                charged_flow_realized_net_bps=_bps(removal_net, remaining_notional),
                realized_turnover_multiplier=remaining_notional / metric.notional_e6 if metric.notional_e6 else 0.0,
            )
        )
    return rows


def policy_rows(metric: Metric, route_away: float = 0.25) -> list[PolicyRow]:
    net = metric.base_fee_e6 + int(metric.extra_e6 * (1 - route_away)) - metric.markout_e6
    net_bps = _bps(net, metric.notional_e6)
    rows = []
    for policy in POLICIES:
        gross_apr = (net_bps / 10_000) * policy.turnover_per_day * policy.active_ratio * YEAR_DAYS
        rebalance_drag = (policy.rebalance_cost_bps / 10_000) * policy.rebalances_per_year
        net_apr = gross_apr - rebalance_drag
        rows.append(
            PolicyRow(
                window=metric.window,
                policy=policy.name,
                capital_usdc=policy.capital_usdc,
                route_away=route_away,
                net_apr=net_apr,
                annual_net_usdc=policy.capital_usdc * net_apr,
            )
        )
    return rows


def gas_sensitivity_rows(metric: Metric, scenarios: list[GasScenario] | None = None) -> list[GasRow]:
    scenarios = scenarios or GAS_SCENARIOS
    rows: list[GasRow] = []
    for scenario in scenarios:
        gas_per_swap = scenario.hook_gas + scenario.pyth_update_gas
        gas_cost = _gas_cost_e6(metric.rows, gas_per_swap, scenario.gas_price_gwei, scenario.eth_usd)
        gas_bps = _bps(gas_cost, metric.notional_e6)
        rows.append(
            GasRow(
                window=metric.window,
                scenario=scenario.name,
                swaps=metric.rows,
                gas_per_swap=gas_per_swap,
                gas_price_gwei=scenario.gas_price_gwei,
                eth_usd=scenario.eth_usd,
                gas_usdc_e6=gas_cost,
                gas_bps=gas_bps,
                peg_net_bps=metric.net_bps,
                net_after_gas_bps=metric.net_bps - gas_bps,
                note=scenario.note,
            )
        )
    return rows


def gas_adjusted_policy_rows(
    metric: Metric,
    route_away: float = 0.25,
    policies: list[Policy] | None = None,
    scenarios: list[GasScenario] | None = None,
) -> list[GasAdjustedPolicyRow]:
    policies = policies or SMALL_CAPITAL_POLICIES
    scenarios = scenarios or GAS_SCENARIOS[1:]
    net = metric.base_fee_e6 + int(metric.extra_e6 * (1 - route_away)) - metric.markout_e6
    net_bps = _bps(net, metric.notional_e6)
    rows: list[GasAdjustedPolicyRow] = []
    for scenario in scenarios:
        gas_per_swap = scenario.hook_gas + scenario.pyth_update_gas
        gas_bps = _bps(_gas_cost_e6(metric.rows, gas_per_swap, scenario.gas_price_gwei, scenario.eth_usd), metric.notional_e6)
        for policy in policies:
            gross_apr = ((net_bps - gas_bps) / 10_000) * policy.turnover_per_day * policy.active_ratio * YEAR_DAYS
            rebalance_drag = (policy.rebalance_cost_bps / 10_000) * policy.rebalances_per_year
            net_apr = gross_apr - rebalance_drag
            rows.append(
                GasAdjustedPolicyRow(
                    window=metric.window,
                    policy=policy.name,
                    scenario=scenario.name,
                    capital_usdc=policy.capital_usdc,
                    turnover_per_day=policy.turnover_per_day,
                    route_away=route_away,
                    net_bps_after_route=net_bps,
                    gas_bps=gas_bps,
                    net_apr=net_apr,
                    annual_net_usdc=policy.capital_usdc * net_apr,
                )
            )
    return rows


def range_stress_rows(window: str, events: list[Event]) -> list[RangeRow]:
    rows: list[RangeRow] = []
    if not events:
        return rows
    total_notional = sum(event.notional_e6 for event in events)
    duration_days = max((events[-1].t_ms - events[0].t_ms) / 86_400_000, 1 / 86_400)
    for policy in RANGE_POLICIES:
        center = events[0].mid_e18
        next_recenter_ms = events[0].t_ms + policy.interval_sec * 1000
        active: list[Event] = []
        rebalances = 0
        for event in events:
            if policy.mode == "interval" and policy.interval_sec > 0 and event.t_ms >= next_recenter_ms:
                center = event.mid_e18
                rebalances += 1
                while event.t_ms >= next_recenter_ms:
                    next_recenter_ms += policy.interval_sec * 1000

            lower = center * (10_000 - policy.half_width_bps) // 10_000
            upper = center * (10_000 + policy.half_width_bps) // 10_000
            in_range = lower <= event.mid_e18 <= upper
            if not in_range and policy.mode == "exit":
                center = event.mid_e18
                rebalances += 1
                in_range = True
            if in_range:
                active.append(event)

        active_notional = sum(event.notional_e6 for event in active)
        base = sum((event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM for event in active)
        extra = sum(event.peg_extra_e6 for event in active)
        markout = sum(event.truth_markout_e6 for event in active)
        net_before_drag = base + extra - markout
        active_capital_e6 = int(active_notional / (policy.target_turnover_per_day * duration_days)) if active_notional else 0
        rebalance_drag = int(active_capital_e6 * policy.rebalance_cost_bps / 10_000 * rebalances)
        rows.append(
            RangeRow(
                window=window,
                policy=policy.name,
                active_coverage=active_notional / total_notional if total_notional else 0.0,
                active_notional_e6=active_notional,
                rebalances=rebalances,
                rebalance_drag_e6=rebalance_drag,
                extra_e6=extra,
                markout_e6=markout,
                net_bps_before_drag=_bps(net_before_drag, active_notional),
                net_bps_after_drag=_bps(net_before_drag - rebalance_drag, active_notional),
            )
        )
    return rows


def suite(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    C.assert_frozen_constants(root)
    fixture_metrics: list[Metric] = []
    range_rows: list[RangeRow] = []
    parity: dict[str, dict[str, int]] = {}
    for window in ("calm", "vol"):
        events, parity[window] = fixture_events(root, window)
        range_rows.extend(range_stress_rows(window, events))
        fixture_metrics.extend(
            [
                static_metric(window, "static 5 bps", events, BASE_FEE_PIPS),
                static_metric(window, "static 30 bps", events, STATIC_30BPS_PIPS),
                metric_from_events(window, "PegGuard selected", events, "peg_extra_e6", "peg_premium_pips"),
                metric_from_events(window, "PegGuard no deadband", events, "no_deadband_extra_e6", "no_deadband_premium_pips"),
                metric_from_events(window, "PegGuard alpha 1", events, "alpha1_extra_e6", "alpha1_premium_pips"),
                metric_from_events(window, "naive raw deviation", events, "raw_extra_e6", "raw_premium_pips"),
            ]
        )
    live = live_shadow_metric(root, live_db)
    route_source = [metric for metric in fixture_metrics if metric.name == "PegGuard selected"]
    if live is not None:
        route_source.insert(0, live)
    return {
        "parity": parity,
        "benchmarks": [_metric_dict(metric) for metric in ([live] if live else []) + fixture_metrics],
        "route_away": [asdict(row) for metric in route_source for row in route_away_rows(metric)],
        "policies": [asdict(row) for metric in route_source for row in policy_rows(metric)],
        "gas_sensitivity": [asdict(row) for metric in route_source for row in gas_sensitivity_rows(metric)],
        "gas_adjusted_policies": [asdict(row) for metric in route_source for row in gas_adjusted_policy_rows(metric)],
        "range_stress": [asdict(row) for row in range_rows],
        "coverage": coverage(root, live is not None, live_db),
    }


def coverage(root: Path, has_live_shadow: bool, live_db: Path | None = None) -> list[dict[str, object]]:
    fixture_dir = root / "test" / "fixtures"
    live_source = str(live_db) if live_db is not None else "shadow/shadow.sqlite3"
    return [
        {"source": "calm_0530 + truth", "kind": "historical fixture", "events": len(_load_json(fixture_dir / "calm_0530.json")), "covered": True},
        {"source": "vol_0523_hot90m + truth", "kind": "historical fixture", "events": len(_load_json(fixture_dir / "vol_0523_hot90m.json")), "covered": True},
        {"source": "sentinel_mainnet_calm", "kind": "RSC false-positive fixture", "events": len(_load_json(fixture_dir / "sentinel_mainnet_calm.json")), "covered": True},
        {"source": "sentinel_mainnet_vol", "kind": "RSC trigger fixture", "events": len(_load_json(fixture_dir / "sentinel_mainnet_vol.json")), "covered": True},
        {"source": live_source, "kind": "forward shadow sample", "events": _live_count(root, live_db), "covered": has_live_shadow},
        {"source": "docs/route_away_proxy.json", "kind": "same-pair fee-tier proxy", "events": _route_proxy_count(root), "covered": _route_proxy_count(root) > 0},
        {"source": "docs/route_away_ab.json", "kind": "controlled route-away experiment", "events": _route_ab_events(root), "covered": _route_ab_events(root) > 0},
        {"source": "multi-day live shadow", "kind": "forward evidence gap", "events": 0, "covered": False},
        {"source": "real route-away elasticity", "kind": "not observable from same-swap replay", "events": 0, "covered": False},
    ]


def markdown(data: dict) -> str:
    lines = [
        "# Economic Test Suite",
        "",
        "This report is generated by `python -m shadow.economic_suite`. It is measurement, not calibration.",
        "Objective metrics remain premium-weighted precision and truth-denominated capture; raw capture is diagnostic only.",
        "",
        "## Replay Parity",
        "",
        "| Window | Rows | Valid | Precision | Truth capture | Dev MAE e2 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for window, row in data["parity"].items():
        lines.append(
            f"| {window} | {row['rows']} | {row['valid_rows']} | {_pct_bps(row['precision_bps'])} | "
            f"{_pct_bps(row['capture_truth_bps'])} | {row['dev_mae_e2']} |"
        )

    lines.extend(
        [
            "",
            "## Strategy Benchmarks",
            "",
            "| Window | Strategy | Notional | Base fees | Extra | Markout cost | Extra bps | Markout bps | Precision | Capture | Net bps |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in data["benchmarks"]:
        lines.append(
            f"| {row['window']} | {row['name']} | {_usd(row['notional_e6'])} | {_usd(row['base_fee_e6'])} | "
            f"{_usd(row['extra_e6'])} | {_usd(row['markout_e6'])} | {row['extra_bps']:.2f} | {row['markout_bps']:.2f} | "
            f"{_nullable_pct(row['precision_bps'])} | {_nullable_pct(row['capture_bps'])} | {row['net_bps']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Route-Away Sensitivity",
            "",
            "Two mechanical models are shown. `premium haircut` assumes the LP still suffers the same markout but loses routed-away premium. `charged-flow removal` removes the same fraction of charged swaps, including their base fees, premiums, and truth markout.",
            "",
            "| Window | Route-away | Premium haircut net bps | Flow-removal net bps, original volume | Flow-removal net bps, realized volume | Realized turnover multiplier |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in data["route_away"]:
        lines.append(
            f"| {row['window']} | {row['route_away']:.0%} | {row['premium_haircut_net_bps']:.2f} | "
            f"{row['charged_flow_removal_net_bps']:.2f} | {row['charged_flow_realized_net_bps']:.2f} | "
            f"{row['realized_turnover_multiplier']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## LP Policy PnL",
            "",
            "Policy PnL uses the conservative 25% premium-haircut route-away model. APR also subtracts an explicit rebalance drag from the policy assumptions in `shadow.economic_suite`.",
            "",
            "| Window | Policy | Capital | Net APR | Annual net |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in data["policies"]:
        lines.append(
            f"| {row['window']} | {row['policy']} | ${row['capital_usdc']:,.0f} | {row['net_apr']:.2%} | "
            f"${row['annual_net_usdc']:,.0f} |"
        )

    lines.extend(
        [
            "",
            "## Gas And Oracle Cost Sensitivity",
            "",
            "Gas rows are scenario inputs, not calibration. They show how much net edge remains if hook execution, and optionally a bundled Pyth update, is treated as an explicit cost to the route or LP/operator.",
            "",
            "| Window | Scenario | Swaps | Gas/swap | Gas gwei | ETH/USD | Gas cost | Gas bps | PegGuard net bps | Net after gas bps |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in data["gas_sensitivity"]:
        lines.append(
            f"| {row['window']} | {row['scenario']} | {row['swaps']} | {row['gas_per_swap']:,} | "
            f"{row['gas_price_gwei']:.3f} | ${row['eth_usd']:,.0f} | {_usd(row['gas_usdc_e6'])} | "
            f"{row['gas_bps']:.3f} | {row['peg_net_bps']:.2f} | "
            f"{row['net_after_gas_bps']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Small-Capital Cost-Adjusted Policies",
            "",
            "These rows apply the conservative 25% premium-haircut route-away model, then subtract gas scenario drag and each policy's rebalance drag. They are pilot-position tests for smaller LP capital, not a promise that the volume can be sourced.",
            "",
            "| Window | Policy | Scenario | Capital | Turnover/day | Net bps after route | Gas bps | Net APR | Annual net |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in data["gas_adjusted_policies"]:
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['scenario']} | ${row['capital_usdc']:,.0f} | "
            f"{row['turnover_per_day']:.1f}x | {row['net_bps_after_route']:.2f} | {row['gas_bps']:.3f} | "
            f"{row['net_apr']:.2%} | ${row['annual_net_usdc']:,.0f} |"
        )

    lines.extend(
        [
            "",
            "## Range Stress",
            "",
            "This isolates LP range behavior on the real fixture events. `static` ranges stay centered at the first observed mid; `hourly` and `exit recenter` are operational upper-bound policies that pay turnover-normalized rebalance drag.",
            "",
            "| Window | Policy | Active coverage | Active notional | Rebalances | Rebalance drag | Extra | Markout | Net bps before drag | Net bps after drag |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in data["range_stress"]:
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['active_coverage']:.2%} | "
            f"{_usd(row['active_notional_e6'])} | {row['rebalances']} | {_usd(row['rebalance_drag_e6'])} | "
            f"{_usd(row['extra_e6'])} | {_usd(row['markout_e6'])} | "
            f"{row['net_bps_before_drag']:.2f} | {row['net_bps_after_drag']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Coverage And Gaps",
            "",
            "| Source | Kind | Events | Covered |",
            "|---|---|---:|---:|",
        ]
    )
    for row in data["coverage"]:
        lines.append(f"| {row['source']} | {row['kind']} | {row['events']} | {'yes' if row['covered'] else 'no'} |")
    interpretation = _interpretation_lines(data)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ]
    )
    lines.extend(interpretation)
    return "\n".join(lines) + "\n"


def _interpretation_lines(data: dict) -> list[str]:
    rows = {(row["window"], row["name"]): row for row in data["benchmarks"]}
    calm = rows.get(("calm", "PegGuard selected"))
    vol = rows.get(("vol", "PegGuard selected"))
    live = rows.get(("live shadow", "PegGuard live shadow"))

    lines: list[str] = []
    if calm is not None and live is not None:
        calm_net = float(calm.get("net_bps", 0.0))
        live_net = float(live.get("net_bps", 0.0))
        if calm_net >= 0 and live_net >= 0:
            lines.append(
                f"- The selected hook is economically positive in the calm fixture ({calm_net:.2f} bps) "
                f"and current live-shadow sample ({live_net:.2f} bps) under normal turnover assumptions."
            )
        elif calm_net >= 0:
            lines.append(
                f"- The selected hook is economically positive in the calm fixture ({calm_net:.2f} bps), "
                f"but the current live-shadow sample is negative ({live_net:.2f} bps); "
                "it is measured same-swaps evidence and still does not measure real route-away."
            )
        else:
            lines.append(
                f"- The selected hook is negative in the calm fixture ({calm_net:.2f} bps) and current live-shadow sample "
                f"({live_net:.2f} bps); treat the economics as failing until explained."
            )
    elif calm is not None:
        calm_net = float(calm.get("net_bps", 0.0))
        lines.append(f"- The selected hook's calm fixture net is {calm_net:.2f} bps under normal turnover assumptions.")

    if vol is not None:
        vol_net = float(vol.get("net_bps", 0.0))
        if vol_net < 0:
            lines.append(
                f"- The volatile fixture is still negative after markout at a 5 bps base fee ({vol_net:.2f} bps); "
                "PegGuard materially reduces but does not fully eliminate extreme LVR."
            )
        else:
            lines.append(
                f"- The volatile fixture is positive after markout at a 5 bps base fee ({vol_net:.2f} bps), "
                "but route-away still needs controlled validation."
            )

    lines.extend(
        [
            "- Static 30 bps looks strong in same-swap replay, but this is not a credible production baseline without route-away modeling because it assumes the same flow accepts a 6x higher base fee.",
            "- Real route-away elasticity and multi-day live shadow remain the largest missing economic evidence.",
        ]
    )
    return lines


def write_outputs(root: Path, out_md: Path, out_json: Path, live_db: Path | None = None) -> dict:
    data = suite(root, live_db)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(data), encoding="utf-8")
    out_json.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _metric_dict(metric: Metric | None) -> dict:
    if metric is None:
        raise ValueError("metric cannot be None")
    data = asdict(metric)
    data.update(
        {
            "precision_bps": metric.precision_bps,
            "capture_bps": metric.capture_bps,
            "net_e6": metric.net_e6,
            "net_bps": metric.net_bps,
            "extra_bps": metric.extra_bps,
            "markout_bps": metric.markout_bps,
        }
    )
    return data


def _bps(num_e6: int, den_e6: int) -> float:
    if den_e6 == 0:
        return 0.0
    return num_e6 / den_e6 * 10_000


def _gas_cost_e6(swaps: int, gas_per_swap: int, gas_price_gwei: float, eth_usd: float) -> int:
    return int(swaps * gas_per_swap * gas_price_gwei * 1e-9 * eth_usd * 1_000_000)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.0f}"


def _pct_bps(value: int) -> str:
    return f"{value / 100:.2f}%"


def _nullable_pct(value: int | None) -> str:
    if value is None:
        return "n/a"
    return _pct_bps(value)


def _live_count(root: Path, db: Path | None = None) -> int:
    db = db or root / "shadow" / "shadow.sqlite3"
    if not db.exists():
        return 0
    conn = sqlite3.connect(db)
    return int(conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0])


def _route_proxy_count(root: Path) -> int:
    path = root / "docs" / "route_away_proxy.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return sum(int(row["swaps"]) for row in data.get("tiers", []))


def _route_ab_events(root: Path) -> int:
    path = root / "docs" / "route_away_ab.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    pre = data.get("pre", {})
    post = data.get("post", {})
    values = [
        int(pre.get("baseline_notional_e6", 0)),
        int(pre.get("treatment_notional_e6", 0)),
        int(post.get("baseline_notional_e6", 0)),
        int(post.get("treatment_notional_e6", 0)),
    ]
    return 2 if all(value > 0 for value in values) else 0


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "economic_tests.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "economic_tests.json")
    parser.add_argument("--live-db", type=Path, help="override live-shadow database used for forward-sample metrics")
    args = parser.parse_args()
    data = write_outputs(root, args.out_md, args.out_json, args.live_db)
    selected = [row for row in data["benchmarks"] if row["name"] == "PegGuard selected"]
    for row in selected:
        print(
            f"{row['window']}: precision={_nullable_pct(row['precision_bps'])} "
            f"capture={_nullable_pct(row['capture_bps'])} net_bps={row['net_bps']:.2f}"
        )
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
