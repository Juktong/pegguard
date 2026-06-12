from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .route_away_ab import evidence_errors as route_ab_evidence_errors


@dataclass(frozen=True)
class EconomicGate:
    name: str
    passed: bool
    observed: str
    required: str


@dataclass(frozen=True)
class EconomicGateReport:
    complete: bool
    gates: list[EconomicGate]


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(
    economic_tests: dict,
    live_status: dict,
    route_proxy: dict,
    route_ab: dict,
    cross_pair_route_proxy: dict | None = None,
    depth_proxy: dict | None = None,
    cross_pair_depth_proxy: dict | None = None,
    oracle_health: dict | None = None,
    oracle_lag: dict | None = None,
    risk_report: dict | None = None,
    drawdown_stop: dict | None = None,
    fallback_attribution: dict | None = None,
    inventory_report: dict | None = None,
    hedge_report: dict | None = None,
    hedge_execution_report: dict | None = None,
    liquidity_share_report: dict | None = None,
    route_break_even: dict | None = None,
    adverse_route_away: dict | None = None,
    bootstrap_report: dict | None = None,
    size_bucket_report: dict | None = None,
    staleness_bucket_report: dict | None = None,
    base_fee_report: dict | None = None,
    target_fee_report: dict | None = None,
    capital_path_report: dict | None = None,
    policy_monte_carlo_report: dict | None = None,
    risk_adjusted_return_report: dict | None = None,
    chain_cost_report: dict | None = None,
    live_gas_snapshot_report: dict | None = None,
    control_plane_cost_report: dict | None = None,
    pnl_attribution_report: dict | None = None,
    capital_survival_report: dict | None = None,
    operator_cost_report: dict | None = None,
    alpha_sweep: dict | None = None,
    target_return_report: dict | None = None,
    route_readiness: dict | None = None,
    order_split_report: dict | None = None,
    tvl_dilution_report: dict | None = None,
    route_cost_proxy: dict | None = None,
    sequential_split_report: dict | None = None,
    quote_route_readiness: dict | None = None,
    quote_headroom_report: dict | None = None,
    cross_pair_quote_headroom_report: dict | None = None,
    quote_headroom_stability_report: dict | None = None,
    quote_headroom_drift_report: dict | None = None,
    quote_premium_stress_report: dict | None = None,
    quote_event_headroom_report: dict | None = None,
    quote_provenance_report: dict | None = None,
    quote_elasticity_report: dict | None = None,
    insurance_reserve_report: dict | None = None,
    premium_allocation_report: dict | None = None,
    reserve_delay_report: dict | None = None,
    reserve_lifecycle_report: dict | None = None,
    reserve_tail_report: dict | None = None,
    route_demand_report: dict | None = None,
    markout_sensitivity_report: dict | None = None,
    pilot_deployability_report: dict | None = None,
    range_width_deployability_report: dict | None = None,
    position_shadow_report: dict | None = None,
    small_capital_decision_report: dict | None = None,
    real_position_report: dict | None = None,
    real_position_portfolio_report: dict | None = None,
    headline_uncertainty_report: dict | None = None,
    lp_flow_response_report: dict | None = None,
    live_convergence_report: dict | None = None,
    live_maturity_report: dict | None = None,
    live_power_report: dict | None = None,
    premium_utilization_report: dict | None = None,
    charge_attribution_report: dict | None = None,
    route_share_stability_report: dict | None = None,
    route_away_placebo_ab_report: dict | None = None,
    route_ab_power_report: dict | None = None,
    route_ab_sizing_report: dict | None = None,
    guard_depeg_report: dict | None = None,
    stable_opportunity_report: dict | None = None,
    market_regime_report: dict | None = None,
    signal_quality_stress_report: dict | None = None,
    signal_margin_report: dict | None = None,
) -> EconomicGateReport:
    live_convergence_report = live_convergence_report or {}
    live_maturity_report = live_maturity_report or {}
    live_power_report = live_power_report or {}
    premium_utilization_report = premium_utilization_report or {}
    charge_attribution_report = charge_attribution_report or {}
    cross_pair_route_proxy = cross_pair_route_proxy or {}
    route_share_stability_report = route_share_stability_report or {}
    route_away_placebo_ab_report = route_away_placebo_ab_report or {}
    route_ab_power_report = route_ab_power_report or {}
    route_ab_sizing_report = route_ab_sizing_report or {}
    guard_depeg_report = guard_depeg_report or {}
    stable_opportunity_report = stable_opportunity_report or {}
    market_regime_report = market_regime_report or {}
    signal_quality_stress_report = signal_quality_stress_report or {}
    signal_margin_report = signal_margin_report or {}
    depth_proxy = depth_proxy or {}
    cross_pair_depth_proxy = cross_pair_depth_proxy or {}
    oracle_health = oracle_health or {}
    oracle_lag = oracle_lag or {}
    risk_report = risk_report or {}
    drawdown_stop = drawdown_stop or {}
    fallback_attribution = fallback_attribution or {}
    inventory_report = inventory_report or {}
    hedge_report = hedge_report or {}
    hedge_execution_report = hedge_execution_report or {}
    liquidity_share_report = liquidity_share_report or {}
    route_break_even = route_break_even or {}
    adverse_route_away = adverse_route_away or {}
    route_readiness = route_readiness or {}
    bootstrap_report = bootstrap_report or {}
    size_bucket_report = size_bucket_report or {}
    staleness_bucket_report = staleness_bucket_report or {}
    base_fee_report = base_fee_report or {}
    target_fee_report = target_fee_report or {}
    capital_path_report = capital_path_report or {}
    policy_monte_carlo_report = policy_monte_carlo_report or {}
    risk_adjusted_return_report = risk_adjusted_return_report or {}
    chain_cost_report = chain_cost_report or {}
    live_gas_snapshot_report = live_gas_snapshot_report or {}
    control_plane_cost_report = control_plane_cost_report or {}
    pnl_attribution_report = pnl_attribution_report or {}
    capital_survival_report = capital_survival_report or {}
    operator_cost_report = operator_cost_report or {}
    alpha_sweep = alpha_sweep or {}
    target_return_report = target_return_report or {}
    order_split_report = order_split_report or {}
    tvl_dilution_report = tvl_dilution_report or {}
    route_cost_proxy = route_cost_proxy or {}
    sequential_split_report = sequential_split_report or {}
    quote_route_readiness = quote_route_readiness or {}
    quote_headroom_report = quote_headroom_report or {}
    cross_pair_quote_headroom_report = cross_pair_quote_headroom_report or {}
    quote_headroom_stability_report = quote_headroom_stability_report or {}
    quote_headroom_drift_report = quote_headroom_drift_report or {}
    quote_premium_stress_report = quote_premium_stress_report or {}
    quote_event_headroom_report = quote_event_headroom_report or {}
    quote_provenance_report = quote_provenance_report or {}
    quote_elasticity_report = quote_elasticity_report or {}
    insurance_reserve_report = insurance_reserve_report or {}
    premium_allocation_report = premium_allocation_report or {}
    reserve_delay_report = reserve_delay_report or {}
    reserve_lifecycle_report = reserve_lifecycle_report or {}
    reserve_tail_report = reserve_tail_report or {}
    route_demand_report = route_demand_report or {}
    markout_sensitivity_report = markout_sensitivity_report or {}
    pilot_deployability_report = pilot_deployability_report or {}
    range_width_deployability_report = range_width_deployability_report or {}
    position_shadow_report = position_shadow_report or {}
    small_capital_decision_report = small_capital_decision_report or {}
    real_position_report = real_position_report or {}
    real_position_portfolio_report = real_position_portfolio_report or {}
    headline_uncertainty_report = headline_uncertainty_report or {}
    lp_flow_response_report = lp_flow_response_report or {}
    gates = [
        _gate(
            "historical replay parity",
            _has_windows(economic_tests.get("parity", {}), ("calm", "vol")),
            ", ".join(sorted(economic_tests.get("parity", {}).keys())) or "none",
            "calm and vol replay parity",
        ),
        _gate(
            "strategy benchmark matrix",
            _has_strategy_benchmarks(economic_tests),
            _benchmark_summary(economic_tests),
            "static/PegGuard/naive benchmarks for calm and vol",
        ),
        _gate(
            "route-away sensitivity",
            bool(economic_tests.get("route_away")),
            f"{len(economic_tests.get('route_away', []))} rows",
            "mechanical route-away rows present",
        ),
        _gate(
            "gas-adjusted small-capital economics",
            bool(economic_tests.get("gas_sensitivity")) and bool(economic_tests.get("gas_adjusted_policies")),
            f"{len(economic_tests.get('gas_sensitivity', []))} gas rows, {len(economic_tests.get('gas_adjusted_policies', []))} policy rows",
            "gas sensitivity and cost-adjusted policy rows present",
        ),
        _gate(
            "range stress",
            bool(economic_tests.get("range_stress")),
            f"{len(economic_tests.get('range_stress', []))} rows",
            "range stress rows present",
        ),
        _gate(
            "GUARD breaker economics",
            _guard_depeg_complete(guard_depeg_report),
            _guard_depeg_observed(guard_depeg_report),
            "breaker timing report has zero calm false positives and volatile triggers",
        ),
        _gate(
            "GUARD stable opportunity",
            _stable_opportunity_complete(stable_opportunity_report),
            _stable_opportunity_observed(stable_opportunity_report),
            "stable-pair no-harvest economics are documented from research provenance",
        ),
        _gate(
            "24h live shadow",
            bool(live_status.get("complete", False)),
            _live_observed(live_status),
            "live_status complete=true",
        ),
        _gate(
            "live evidence source consistency",
            _live_evidence_consistent(economic_tests, live_status),
            _live_evidence_observed(economic_tests, live_status),
            "economic_tests live sample uses the same database as live_status and is not ahead of it",
        ),
        _gate(
            "live convergence",
            _live_convergence_complete(live_convergence_report),
            _live_convergence_observed(live_convergence_report),
            "multiple truth-backed live time buckets with charged flow",
        ),
        _gate(
            "live maturity",
            _live_maturity_complete(live_maturity_report),
            _live_maturity_observed(live_maturity_report),
            "multiple cumulative live checkpoints with charged flow",
        ),
        _gate(
            "live sample power",
            _live_power_complete(live_power_report),
            _live_power_observed(live_power_report),
            "live sample has enough hourly buckets to estimate metric confidence bands",
        ),
        _gate(
            "route-away proxy",
            _route_proxy_swaps(route_proxy) > 0,
            f"{_route_proxy_swaps(route_proxy)} swaps",
            "same-pair fee-tier proxy has swaps",
        ),
        _gate(
            "cross-pair route-away proxy",
            _route_proxy_swaps(cross_pair_route_proxy) > 0,
            _cross_pair_observed(cross_pair_route_proxy),
            "second-pair fee-tier proxy has swaps",
        ),
        _gate(
            "route-share placebo stability",
            _route_share_stability_complete(route_share_stability_report),
            _route_share_stability_observed(route_share_stability_report),
            "fee-tier share stability covers at least two proxy pairs and multiple lookbacks",
        ),
        _gate(
            "route-away A/A placebo",
            _route_away_placebo_ab_complete(route_away_placebo_ab_report),
            _route_away_placebo_ab_observed(route_away_placebo_ab_report),
            "adjacent equal-window fee-tier placebo covers at least two proxy pairs",
        ),
        _gate(
            "controlled route-away power check",
            _route_ab_power_complete(route_ab_power_report),
            _route_ab_power_observed(route_ab_power_report),
            "A/B power report maps placebo share drift to detectable route-away thresholds",
        ),
        _gate(
            "controlled route-away sizing plan",
            _route_ab_sizing_complete(route_ab_sizing_report),
            _route_ab_sizing_observed(route_ab_sizing_report),
            "A/B sizing report maps detectable route-away thresholds to proxy notional and window length",
        ),
        _gate(
            "fee-tier depth proxy",
            _depth_proxy_rows(depth_proxy) > 0,
            _depth_observed(depth_proxy),
            "same-pair active depth snapshot has tiers",
        ),
        _gate(
            "cross-pair depth proxy",
            _depth_proxy_rows(cross_pair_depth_proxy) > 0,
            _depth_observed(cross_pair_depth_proxy),
            "second-pair active depth snapshot has tiers",
        ),
        _gate(
            "oracle-health economics",
            _oracle_health_complete(oracle_health),
            _oracle_health_observed(oracle_health),
            "oracle-health report has swaps and Pyth health rows",
        ),
        _gate(
            "oracle-lag stress",
            _oracle_lag_complete(oracle_lag),
            _oracle_lag_observed(oracle_lag),
            "oracle-lag report covers fresh, lag2, and lag5 decisions",
        ),
        _gate(
            "tail-risk concentration",
            _risk_report_complete(risk_report),
            _risk_report_observed(risk_report),
            "risk report has calm, vol, and optional live windows",
        ),
        _gate(
            "drawdown stop-loss",
            _drawdown_stop_complete(drawdown_stop),
            _drawdown_stop_observed(drawdown_stop),
            "drawdown stop-loss report covers calm, vol, and live threshold rows",
        ),
        _gate(
            "fallback attribution",
            _fallback_attribution_complete(fallback_attribution),
            _fallback_attribution_observed(fallback_attribution),
            "fallback attribution report covers fresh live decision",
        ),
        _gate(
            "LP inventory accounting",
            _inventory_report_complete(inventory_report),
            _inventory_report_observed(inventory_report),
            "inventory report covers calm and vol fixture paths",
        ),
        _gate(
            "hedge stress",
            _hedge_report_complete(hedge_report),
            _hedge_report_observed(hedge_report),
            "hedge report covers calm and vol fixture paths",
        ),
        _gate(
            "hedge execution-cost stress",
            _hedge_execution_complete(hedge_execution_report),
            _hedge_execution_observed(hedge_execution_report),
            "hedge execution overlay covers calm/vol, range policies, hedge policies, and cost scenarios",
        ),
        _gate(
            "liquidity-share sizing",
            _liquidity_share_complete(liquidity_share_report),
            _liquidity_share_observed(liquidity_share_report),
            "liquidity-share report covers calm, vol, and live sizing rows",
        ),
        _gate(
            "position-level LP shadow",
            _position_shadow_complete(position_shadow_report),
            _position_shadow_observed(position_shadow_report),
            "position shadow covers calm, vol, and live combined inventory plus pro-rata rows",
        ),
        _gate(
            "real-position replay",
            _real_position_complete(real_position_report),
            _real_position_observed(real_position_report),
            "audited real LP position input with net-vs-HODL economics",
        ),
        _gate(
            "multi-position LP replay",
            _real_position_portfolio_complete(real_position_portfolio_report),
            _real_position_portfolio_observed(real_position_portfolio_report),
            "at least three diverse audited real LP positions in portfolio replay",
        ),
        _gate(
            "route-away break-even",
            _route_break_even_complete(route_break_even),
            _route_break_even_observed(route_break_even),
            "break-even report covers calm, vol, and live selected strategies",
        ),
        _gate(
            "adverse route-away stress",
            _adverse_route_away_complete(adverse_route_away),
            _adverse_route_away_observed(adverse_route_away),
            "best-flow-leaves-first route-away stress covers calm and vol",
        ),
        _gate(
            "controlled route-away readiness",
            _route_readiness_complete(route_readiness, route_ab),
            _route_readiness_observed(route_readiness, route_ab),
            "collector ready or controlled route-away artifact complete",
        ),
        _gate(
            "depth-adjusted route cost",
            _route_cost_complete(route_cost_proxy),
            _route_cost_observed(route_cost_proxy),
            "route-cost proxy covers same-pair and cross-pair fee tiers",
        ),
        _gate(
            "quote-route readiness",
            _quote_route_readiness_complete(quote_route_readiness),
            _quote_route_readiness_observed(quote_route_readiness),
            "real quoter result exists or quote collector inputs are ready",
        ),
        _gate(
            "quote premium headroom",
            _quote_headroom_complete(quote_headroom_report),
            _quote_headroom_observed(quote_headroom_report),
            "real quote grid maps 5 bps route premium headroom by size",
        ),
        _gate(
            "cross-pair quote headroom",
            _quote_headroom_complete(cross_pair_quote_headroom_report),
            _cross_pair_quote_headroom_observed(cross_pair_quote_headroom_report),
            "second-pair real quote grid maps 5 bps route premium headroom",
        ),
        _gate(
            "quote-headroom repeatability",
            _quote_headroom_stability_complete(quote_headroom_stability_report),
            _quote_headroom_stability_observed(quote_headroom_stability_report),
            "repeat quote snapshots keep 5 bps route headroom positive",
        ),
        _gate(
            "quote-headroom drift",
            _quote_headroom_drift_complete(quote_headroom_drift_report),
            _quote_headroom_drift_observed(quote_headroom_drift_report),
            "time-diverse quote snapshots keep 5 bps route headroom positive across pairs and sizes",
        ),
        _gate(
            "quote premium stress",
            _quote_premium_stress_complete(quote_premium_stress_report),
            _quote_premium_stress_observed(quote_premium_stress_report),
            "charged event premiums are bucketed against real quote headroom",
        ),
        _gate(
            "quote event headroom",
            _quote_event_headroom_complete(quote_event_headroom_report),
            _quote_event_headroom_observed(quote_event_headroom_report),
            "charged event premiums are checked against interpolated real quote headroom",
        ),
        _gate(
            "quote provenance audit",
            _quote_provenance_complete(quote_provenance_report),
            _quote_provenance_observed(quote_provenance_report),
            "quote artifacts are audited for coverage and reproducibility metadata",
        ),
        _gate(
            "quote-headroom elasticity",
            _quote_elasticity_complete(quote_elasticity_report),
            _quote_elasticity_observed(quote_elasticity_report),
            "route-away elasticity stress covers quote-headroom margins by window",
        ),
        _gate(
            "insurance reserve solvency",
            _insurance_reserve_complete(insurance_reserve_report),
            _insurance_reserve_observed(insurance_reserve_report),
            "premium-only reserve scenarios cover calm and vol payout rows",
        ),
        _gate(
            "premium allocation frontier",
            _premium_allocation_complete(premium_allocation_report),
            _premium_allocation_observed(premium_allocation_report),
            "premium split frontier covers calm/vol reserve shares and claim bases",
        ),
        _gate(
            "premium utilization",
            _premium_utilization_complete(premium_utilization_report),
            _premium_utilization_observed(premium_utilization_report),
            "dynamic premium distribution covers calm, vol, and live windows",
        ),
        _gate(
            "charge attribution",
            _charge_attribution_complete(charge_attribution_report),
            _charge_attribution_observed(charge_attribution_report),
            "charged/missed truth attribution covers calm, vol, and live windows",
        ),
        _gate(
            "reserve claim-delay stress",
            _reserve_delay_complete(reserve_delay_report),
            _reserve_delay_observed(reserve_delay_report),
            "claim-delay reserve stress covers windows, payout rates, claim bases, and delay horizons",
        ),
        _gate(
            "reserve lifecycle churn",
            _reserve_lifecycle_complete(reserve_lifecycle_report),
            _reserve_lifecycle_observed(reserve_lifecycle_report),
            "reserve lifecycle covers calm/vol horizons, withdrawals, and LP churn",
        ),
        _gate(
            "reserve tail sizing",
            _reserve_tail_complete(reserve_tail_report),
            _reserve_tail_observed(reserve_tail_report),
            "shuffled event-order reserve seed sizing covers calm and vol payout rows",
        ),
        _gate(
            "bootstrap robustness",
            _bootstrap_report_complete(bootstrap_report),
            _bootstrap_report_observed(bootstrap_report),
            "bootstrap report covers calm, vol, and optional live windows",
        ),
        _gate(
            "headline uncertainty bands",
            _headline_uncertainty_complete(headline_uncertainty_report),
            _headline_uncertainty_observed(headline_uncertainty_report),
            "bootstrap confidence bands cover calm/vol headline metrics and small-capital APRs",
        ),
        _gate(
            "trade-size buckets",
            _size_bucket_complete(size_bucket_report),
            _size_bucket_observed(size_bucket_report),
            "size-bucket report covers calm and vol trade sizes",
        ),
        _gate(
            "oracle staleness buckets",
            _staleness_bucket_complete(staleness_bucket_report),
            _staleness_bucket_observed(staleness_bucket_report),
            "staleness-bucket report covers live oracle freshness buckets",
        ),
        _gate(
            "market-regime segmentation",
            _market_regime_complete(market_regime_report),
            _market_regime_observed(market_regime_report),
            "market-regime report covers quiet, normal, high-vol, oracle-lag, and gas-stress overlays",
        ),
        _gate(
            "signal-quality stress",
            _signal_quality_stress_complete(signal_quality_stress_report),
            _signal_quality_stress_observed(signal_quality_stress_report),
            "signal-quality report covers observed, missed-correct, and false-charge precision stresses",
        ),
        _gate(
            "signal margin",
            _signal_margin_complete(signal_margin_report),
            _signal_margin_observed(signal_margin_report),
            "signal margin report covers calm, vol, and optional live selected PegGuard rows",
        ),
        _gate(
            "base-fee adequacy",
            _base_fee_report_complete(base_fee_report),
            _base_fee_report_observed(base_fee_report),
            "base-fee report covers calm, vol, and live selected strategies",
        ),
        _gate(
            "truth markout sensitivity",
            _markout_sensitivity_complete(markout_sensitivity_report),
            _markout_sensitivity_observed(markout_sensitivity_report),
            "selected PegGuard calm/vol rows cover fixed truth-markout multipliers",
        ),
        _gate(
            "target-fee viability",
            _target_fee_report_complete(target_fee_report),
            _target_fee_report_observed(target_fee_report),
            "target-fee report maps required fees to route proxy tiers",
        ),
        _gate(
            "capital-path stress",
            _capital_path_report_complete(capital_path_report),
            _capital_path_report_observed(capital_path_report),
            "capital-path report covers calm, weekly-shock, and volatile paths",
        ),
        _gate(
            "policy Monte Carlo",
            _policy_monte_carlo_complete(policy_monte_carlo_report),
            _policy_monte_carlo_observed(policy_monte_carlo_report),
            "policy return Monte Carlo covers routine, shock, and stress regime mixes",
        ),
        _gate(
            "risk-adjusted return",
            _risk_adjusted_return_complete(risk_adjusted_return_report),
            _risk_adjusted_return_observed(risk_adjusted_return_report),
            "risk-adjusted policy return report covers routine, shock, and stress regime mixes",
        ),
        _gate(
            "chain cost matrix",
            _chain_cost_complete(chain_cost_report),
            _chain_cost_observed(chain_cost_report),
            "chain-specific gas/oracle cost matrix covers Base, Unichain, Arbitrum, and L1 reference",
        ),
        _gate(
            "live gas snapshot",
            _live_gas_snapshot_complete(live_gas_snapshot_report),
            _live_gas_snapshot_observed(live_gas_snapshot_report),
            "current RPC gas snapshot covers Base, Unichain, Arbitrum, and Ethereum",
        ),
        _gate(
            "control-plane callback cost",
            _control_plane_cost_complete(control_plane_cost_report),
            _control_plane_cost_observed(control_plane_cost_report),
            "Reactive/control-plane callback gas is priced across live gas chains",
        ),
        _gate(
            "PnL attribution",
            _pnl_attribution_complete(pnl_attribution_report),
            _pnl_attribution_observed(pnl_attribution_report),
            "component waterfall covers calm/vol policies and low/stressed L2 scenarios",
        ),
        _gate(
            "capital survival runway",
            _capital_survival_complete(capital_survival_report),
            _capital_survival_observed(capital_survival_report),
            "small-capital runway covers calm/vol windows and routine/shock/stress mixes",
        ),
        _gate(
            "operator fixed-cost drag",
            _operator_cost_complete(operator_cost_report),
            _operator_cost_observed(operator_cost_report),
            "operator-cost overlay covers policies, ops scenarios, calm, and vol",
        ),
        _gate(
            "pilot deployability stress",
            _pilot_deployability_complete(pilot_deployability_report),
            _pilot_deployability_observed(pilot_deployability_report),
            "small-capital deployment scoreboard covers windows, policies, ops costs, and markout stress",
        ),
        _gate(
            "range-width deployability",
            _range_width_deployability_complete(range_width_deployability_report),
            _range_width_deployability_observed(range_width_deployability_report),
            "range-width grid covers calm/vol/live, width buckets, gas scenarios, and markout stress",
        ),
        _gate(
            "small-capital decision matrix",
            _small_capital_decision_complete(small_capital_decision_report),
            _small_capital_decision_observed(small_capital_decision_report),
            "decision matrix covers micro, small, focused, and $100k depth-share profiles",
        ),
        _gate(
            "alpha sensitivity",
            _alpha_sweep_complete(alpha_sweep),
            _alpha_sweep_observed(alpha_sweep),
            "alpha sweep covers default alpha and feasible sensitivity rows",
        ),
        _gate(
            "target-return thresholds",
            _target_return_complete(target_return_report),
            _target_return_observed(target_return_report),
            "target-return report covers calm, vol, and live threshold rows",
        ),
        _gate(
            "route-away demand curve",
            _route_demand_complete(route_demand_report),
            _route_demand_observed(route_demand_report),
            "hard-threshold demand curve covers calm/vol premium tolerances",
        ),
        _gate(
            "order-splitting sensitivity",
            _order_split_complete(order_split_report),
            _order_split_observed(order_split_report),
            "order-splitting report covers calm and vol same-signal splits",
        ),
        _gate(
            "sequential split timing",
            _sequential_split_complete(sequential_split_report),
            _sequential_split_observed(sequential_split_report),
            "sequential split report covers same-timestamp and time-spaced child swaps",
        ),
        _gate(
            "TVL dilution equilibrium",
            _tvl_dilution_complete(tvl_dilution_report),
            _tvl_dilution_observed(tvl_dilution_report),
            "TVL dilution report covers calm and vol target APR capacity",
        ),
        _gate(
            "LP flow response",
            _lp_flow_response_complete(lp_flow_response_report),
            _lp_flow_response_observed(lp_flow_response_report),
            "adaptive LP entry/exit simulation covers calm, shock, and volatile paths",
        ),
        _gate(
            "controlled route-away",
            _route_ab_complete(route_ab),
            _route_ab_observed(route_ab),
            "evaluated valid=true artifact with collection metadata, matching notionals, and derived route-away fields",
        ),
    ]
    return EconomicGateReport(all(gate.passed for gate in gates), gates)


def markdown(report: EconomicGateReport) -> str:
    lines = [
        "# Economic Completion Gates",
        "",
        "This is the hard completion check for the economic test plan. It is stricter",
        "than the evidence ledger: every row must pass before the economic-test goal",
        "is complete.",
        "",
        f"Status: {'complete' if report.complete else 'incomplete'}",
        "",
        "| Gate | Observed | Required | Passed |",
        "|---|---:|---:|---:|",
    ]
    for gate in report.gates:
        lines.append(f"| {gate.name} | {gate.observed} | {gate.required} | {'yes' if gate.passed else 'no'} |")
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: EconomicGateReport, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")


def _gate(name: str, passed: bool, observed: str, required: str) -> EconomicGate:
    return EconomicGate(name, passed, observed, required)


def _has_windows(data: dict, windows: tuple[str, ...]) -> bool:
    return all(window in data for window in windows)


def _has_strategy_benchmarks(data: dict) -> bool:
    names = {(str(row.get("window", "")), str(row.get("name", ""))) for row in data.get("benchmarks", [])}
    required = {
        ("calm", "static 5 bps"),
        ("calm", "PegGuard selected"),
        ("calm", "naive raw deviation"),
        ("vol", "static 5 bps"),
        ("vol", "PegGuard selected"),
        ("vol", "naive raw deviation"),
    }
    return required.issubset(names)


def _guard_depeg_complete(report: dict) -> bool:
    selected = _guard_depeg_selected(report)
    return (
        bool(report.get("complete"))
        and selected is not None
        and int(selected.get("calm_triggers", 0)) == 0
        and int(selected.get("vol_triggers", 0)) > 0
        and selected.get("first_vol_trigger_ms") is not None
    )


def _guard_depeg_observed(report: dict) -> str:
    selected = _guard_depeg_selected(report)
    if selected is None:
        return "missing"
    lead = selected.get("lead_time_before_measured_bleed_sec")
    before = selected.get("bled_before_first_trigger_e6")
    after = selected.get("measured_bleed_after_first_trigger_e6")
    return (
        f"calm triggers {int(selected.get('calm_triggers', 0))}; "
        f"vol triggers {int(selected.get('vol_triggers', 0))}; "
        f"lead {_seconds_or_na(lead)}; before {_usd_or_na(before)}; after {_usd_or_na(after)}"
    )


def _guard_depeg_selected(report: dict) -> dict | None:
    rows = report.get("rows", [])
    if not rows:
        return None
    return next((row for row in rows if row.get("label") == "selected"), rows[0])


def _stable_opportunity_complete(report: dict) -> bool:
    return (
        bool(report.get("complete"))
        and report.get("directional_fee_policy") == "disabled"
        and float(report.get("normal_stable_max_bps", 999)) <= 0.35
        and float(report.get("best_directional_capture_pct", 1)) < 0.10
        and float(report.get("trip_to_normal_ratio", 0)) > 100
    )


def _stable_opportunity_observed(report: dict) -> str:
    if not report:
        return "missing"
    return (
        f"policy={report.get('directional_fee_policy', 'n/a')}; "
        f"normal max {float(report.get('normal_stable_max_bps', 0)):.2f} bps; "
        f"best capture {float(report.get('best_directional_capture_pct', 0)):.2%}; "
        f"trip margin {float(report.get('trip_to_normal_ratio', 0)):.1f}x"
    )


def _seconds_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value)}s"


def _benchmark_summary(data: dict) -> str:
    windows = sorted({str(row.get("window", "")) for row in data.get("benchmarks", []) if row.get("window")})
    return f"{len(data.get('benchmarks', []))} rows; windows={','.join(windows) or 'none'}"


def _live_observed(status: dict) -> str:
    observed = (
        f"{int(status.get('swaps', 0))} swaps, "
        f"{float(status.get('observed_span_hours', 0)):.2f}h, "
        f"{float(status.get('truth_coverage', 0)):.2%} truth"
    )
    remaining = float(status.get("remaining_span_hours", 0))
    if remaining > 0:
        observed += f", {remaining:.2f}h remaining"
    return observed


def _live_evidence_consistent(economic_tests: dict, live_status: dict) -> bool:
    status_db = str(live_status.get("database", ""))
    source = _live_coverage_source(economic_tests)
    if not status_db or not source or not _same_path(status_db, source):
        return False

    status_swaps = int(live_status.get("swaps", 0))
    if status_swaps <= 0:
        return False

    benchmark_rows = _live_benchmark_rows(economic_tests)
    coverage_events = _live_coverage_events(economic_tests)
    return 0 < benchmark_rows <= status_swaps and 0 < coverage_events <= status_swaps


def _live_evidence_observed(economic_tests: dict, live_status: dict) -> str:
    status_db = str(live_status.get("database", "missing"))
    source = _live_coverage_source(economic_tests) or "missing"
    return (
        f"live_status={status_db}; economic_tests={source}; "
        f"benchmark_rows={_live_benchmark_rows(economic_tests)}; "
        f"coverage_events={_live_coverage_events(economic_tests)}; "
        f"status_swaps={int(live_status.get('swaps', 0))}"
    )


def _live_coverage_source(economic_tests: dict) -> str:
    for row in economic_tests.get("coverage", []):
        if row.get("kind") == "forward shadow sample":
            return str(row.get("source", ""))
    return ""


def _live_coverage_events(economic_tests: dict) -> int:
    for row in economic_tests.get("coverage", []):
        if row.get("kind") == "forward shadow sample":
            return int(row.get("events", 0))
    return 0


def _live_benchmark_rows(economic_tests: dict) -> int:
    for row in economic_tests.get("benchmarks", []):
        if row.get("window") == "live shadow":
            return int(row.get("rows", 0))
    return 0


def _same_path(left: str, right: str) -> bool:
    def normalize(value: str) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = C.repo_root() / path
        return path.resolve(strict=False)

    return normalize(left) == normalize(right)


def _live_convergence_complete(report: dict) -> bool:
    return (
        bool(report.get("complete"))
        and len(report.get("convergence_rows", [])) >= 2
        and int(report.get("valid_rows", 0)) > 0
        and int(report.get("charged_rows", 0)) > 0
    )


def _live_convergence_observed(report: dict) -> str:
    rows = report.get("convergence_rows", [])
    return (
        f"{len(rows)} buckets; {int(report.get('valid_rows', 0))} valid; "
        f"{int(report.get('charged_rows', 0))} charged; "
        f"precision {_pct_or_na(report.get('precision'))}; "
        f"capture {_pct_or_na(report.get('capture_truth'))}; "
        f"net {_bps_or_na(report.get('net_bps'))}"
    )


def _live_maturity_complete(report: dict) -> bool:
    return (
        bool(report.get("complete"))
        and len(report.get("maturity_rows", [])) >= 2
        and int(report.get("valid_rows", 0)) > 0
        and int(report.get("charged_rows", 0)) > 0
    )


def _live_maturity_observed(report: dict) -> str:
    rows = report.get("maturity_rows", [])
    return (
        f"{len(rows)} checkpoints; {int(report.get('valid_rows', 0))} valid; "
        f"{int(report.get('charged_rows', 0))} charged; "
        f"precision {_pct_or_na(report.get('precision'))}; "
        f"capture {_pct_or_na(report.get('capture_truth'))}; "
        f"max capture drift {_pct_or_na(report.get('max_abs_capture_delta'))}; "
        f"max net drift {_bps_or_na(report.get('max_abs_net_bps_delta'))}"
    )


def _live_power_complete(report: dict) -> bool:
    metrics = report.get("metrics", [])
    names = {str(row.get("metric", "")) for row in metrics}
    return (
        bool(report.get("complete"))
        and int(report.get("bucket_count", 0)) >= 2
        and int(report.get("valid_rows", 0)) > 0
        and int(report.get("charged_rows", 0)) > 0
        and {"net_bps", "capture_truth", "precision"}.issubset(names)
    )


def _live_power_observed(report: dict) -> str:
    metrics = report.get("metrics", [])
    statuses = sorted({str(row.get("status", "")) for row in metrics if row.get("status")})
    net_half_width = next(
        (row.get("ci95_half_width") for row in metrics if row.get("metric") == "net_bps"),
        None,
    )
    max_additional = max(
        (
            float(row.get("additional_hours_needed", 0))
            for row in metrics
            if row.get("additional_hours_needed") is not None
        ),
        default=0.0,
    )
    return (
        f"{int(report.get('bucket_count', 0))} buckets; "
        f"{int(report.get('valid_rows', 0))} valid; "
        f"{int(report.get('charged_rows', 0))} charged; "
        f"span {float(report.get('observed_span_hours', 0)):.2f}h; "
        f"net half-width {_bps_or_na(net_half_width)}; "
        f"max additional {max_additional:.1f}h; statuses={','.join(statuses) or 'none'}"
    )


def _route_proxy_swaps(route_proxy: dict) -> int:
    return sum(int(row.get("swaps", 0)) for row in route_proxy.get("tiers", []))


def _cross_pair_observed(route_proxy: dict) -> str:
    pair = str(route_proxy.get("pair", "n/a"))
    return f"{pair}, {_route_proxy_swaps(route_proxy)} swaps"


def _route_share_stability_complete(report: dict) -> bool:
    return bool(report.get("complete")) and len(report.get("pair_summaries", [])) >= 2 and len(report.get("rows", [])) >= 4


def _route_share_stability_observed(report: dict) -> str:
    pairs = sorted({str(row.get("pair", "")) for row in report.get("pair_summaries", []) if row.get("pair")})
    return (
        f"{len(report.get('rows', []))} rows; pairs={','.join(pairs) or 'none'}; "
        f"max 5bps spread {float(report.get('max_5bps_spread_pp', 0)):.2f} pp; "
        f"max high-fee spread {float(report.get('max_high_fee_spread_pp', 0)):.2f} pp"
    )


def _route_away_placebo_ab_complete(report: dict) -> bool:
    return bool(report.get("complete")) and len(report.get("rows", [])) >= 2


def _route_away_placebo_ab_observed(report: dict) -> str:
    pairs = sorted({str(row.get("pair", "")) for row in report.get("rows", []) if row.get("pair")})
    return (
        f"{len(report.get('rows', []))} rows; pairs={','.join(pairs) or 'none'}; "
        f"max false route-away {_pct_or_na(report.get('max_false_route_away_rate'))}; "
        f"max abs share shift {float(report.get('max_abs_share_shift_pp', 0)):.2f} pp"
    )


def _route_ab_power_complete(report: dict) -> bool:
    return bool(report.get("complete")) and len(report.get("mde_rows", [])) > 0 and len(report.get("economic_rows", [])) > 0


def _route_ab_power_observed(report: dict) -> str:
    rows = report.get("mde_rows", [])
    economic_rows = report.get("economic_rows", [])
    usable = sum(1 for row in rows if str(row.get("status", "")) == "usable")
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    before_break_even = sum(
        1 for row in economic_rows if str(row.get("interpretation", "")) == "detectable before modeled break-even"
    )
    return (
        f"{len(rows)} MDE rows; pairs={','.join(pairs) or 'none'}; "
        f"usable={usable}; before break-even={before_break_even}/{len(economic_rows)}"
    )


def _route_ab_sizing_complete(report: dict) -> bool:
    return bool(report.get("complete")) and len(report.get("proxy_rows", [])) >= 2 and len(report.get("candidate_rows", [])) > 0


def _route_ab_sizing_observed(report: dict) -> str:
    rows = report.get("candidate_rows", [])
    recs = report.get("recommendations", [])
    pairs = sorted({str(row.get("pair", "")) for row in report.get("proxy_rows", []) if row.get("pair")})
    best_hours = min(
        (
            float(row.get("hours_for_target_treatment_notional"))
            for row in recs
            if row.get("hours_for_target_treatment_notional") is not None
        ),
        default=None,
    )
    best = "n/a" if best_hours is None else f"{best_hours:.1f}h"
    return f"{len(rows)} candidates; pairs={','.join(pairs) or 'none'}; recommendations={len(recs)}; best target window {best}"


def _depth_proxy_rows(depth_proxy: dict) -> int:
    return len(depth_proxy.get("tiers", []))


def _depth_observed(depth_proxy: dict) -> str:
    pair = str(depth_proxy.get("pair", "n/a"))
    band_totals = depth_proxy.get("band_totals", {})
    total_50 = int(band_totals.get("50", 0))
    return f"{pair}, {_depth_proxy_rows(depth_proxy)} tiers, 50bps depth {_usd(total_50)}"


def _oracle_health_complete(oracle_health: dict) -> bool:
    return int(oracle_health.get("swaps", 0)) > 0 and int(oracle_health.get("pyth_health_rows", 0)) > 0


def _oracle_health_observed(oracle_health: dict) -> str:
    return (
        f"{int(oracle_health.get('swaps', 0))} swaps, "
        f"{int(oracle_health.get('pyth_health_rows', 0))} Pyth rows, "
        f"p90 staleness {_seconds(oracle_health.get('staleness_p90_ms'))}"
    )


def _oracle_lag_complete(oracle_lag: dict) -> bool:
    labels = {str(row.get("label", "")) for row in oracle_lag.get("rows", [])}
    return {"fresh", "lag2", "lag5"}.issubset(labels)


def _oracle_lag_observed(oracle_lag: dict) -> str:
    rows = oracle_lag.get("rows", [])
    labels = sorted({str(row.get("label", "")) for row in rows})
    lag5_delta = 0
    for row in rows:
        if row.get("label") == "lag5":
            lag5_delta = int(row.get("delta_net_vs_fresh_e6", 0))
            break
    return f"{len(rows)} rows: {', '.join(labels) or 'none'}; lag5 delta {_usd(lag5_delta)}"


def _risk_report_complete(risk_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in risk_report.get("windows", [])}
    return {"calm", "vol"}.issubset(windows)


def _risk_report_observed(risk_report: dict) -> str:
    windows = [str(row.get("window", "")) for row in risk_report.get("windows", [])]
    return f"{len(windows)} windows: {', '.join(windows) or 'none'}"


def _drawdown_stop_complete(drawdown_stop: dict) -> bool:
    windows = {str(row.get("window", "")) for row in drawdown_stop.get("rows", [])}
    thresholds = {int(row.get("threshold_e6", 0)) for row in drawdown_stop.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows) and {10_000_000, 50_000_000}.issubset(thresholds)


def _drawdown_stop_observed(drawdown_stop: dict) -> str:
    rows = drawdown_stop.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    triggered = sum(1 for row in rows if row.get("triggered"))
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; triggered={triggered}"


def _fallback_attribution_complete(fallback_attribution: dict) -> bool:
    labels = {str(row.get("label", "")) for row in fallback_attribution.get("labels", [])}
    return int(fallback_attribution.get("rows", 0)) > 0 and "fresh" in labels


def _fallback_attribution_observed(fallback_attribution: dict) -> str:
    fresh = {}
    for row in fallback_attribution.get("labels", []):
        if row.get("label") == "fresh":
            fresh = row
            break
    return (
        f"{int(fallback_attribution.get('rows', 0))} swaps, "
        f"fresh missed {_usd(int(fresh.get('missed_extra_e6', 0)))}"
    )


def _inventory_report_complete(inventory_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in inventory_report.get("windows", [])}
    return {"calm", "vol"}.issubset(windows)


def _inventory_report_observed(inventory_report: dict) -> str:
    windows = [str(row.get("window", "")) for row in inventory_report.get("windows", [])]
    return f"{len(windows)} rows: {', '.join(sorted(set(windows))) or 'none'}"


def _hedge_report_complete(hedge_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in hedge_report.get("rows", [])}
    return {"calm", "vol"}.issubset(windows)


def _hedge_report_observed(hedge_report: dict) -> str:
    rows = hedge_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    best_vol = max((int(row.get("hedge_improvement_e6", 0)) for row in rows if row.get("window") == "vol"), default=0)
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}; best vol improvement {_usd(best_vol)}"


def _hedge_execution_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    ranges = {str(row.get("range_policy", "")) for row in rows}
    hedge_policies = {str(row.get("hedge_policy", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    statuses = {str(row.get("status", "")) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol"}.issubset(windows)
        and {"static +/-1%", "static +/-3%", "static +/-5%"}.issubset(ranges)
        and {"open only", "50 bps drift", "every event"}.issubset(hedge_policies)
        and {"low-cost perp", "stressed funding", "thin hedge venue"}.issubset(scenarios)
        and {"worse than unhedged", "operationally infeasible"}.issubset(statuses)
    )


def _hedge_execution_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    scenarios = sorted({str(row.get("scenario", "")) for row in rows if row.get("scenario")})
    improving = sum(1 for row in rows if row.get("status") == "improves after costs")
    infeasible = sum(1 for row in rows if row.get("status") == "operationally infeasible")
    best_vol = max((int(row.get("hedge_improvement_e6", 0)) for row in rows if row.get("window") == "vol"), default=0)
    worst = min((int(row.get("hedge_improvement_e6", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; scenarios={len(scenarios)}; "
        f"improves={improving}; infeasible={infeasible}; best vol {_usd(best_vol)}; worst {_usd(worst)}"
    )


def _liquidity_share_complete(liquidity_share_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in liquidity_share_report.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows)


def _liquidity_share_observed(liquidity_share_report: dict) -> str:
    rows = liquidity_share_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}"


def _position_shadow_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    policies = {str(row.get("range_policy", "")) for row in rows}
    capitals = {int(row.get("capital_e6", 0)) for row in rows}
    required_policies = {"static +/-1%", "static +/-3%", "static +/-5%"}
    required_capitals = {2_500_000_000, 10_000_000_000, 25_000_000_000, 100_000_000_000}
    if not {"calm", "vol", "live shadow"}.issubset(windows):
        return False
    if not required_policies.issubset(policies) or not required_capitals.issubset(capitals):
        return False
    for window in ("calm", "vol", "live shadow"):
        for policy in required_policies:
            for capital in required_capitals:
                if not _position_row_has_combined(report, window, policy, capital):
                    return False
    return True


def _position_row_has_combined(report: dict, window: str, policy: str, capital_e6: int) -> bool:
    for row in report.get("rows", []):
        if (
            row.get("window") == window
            and row.get("range_policy") == policy
            and int(row.get("capital_e6", 0)) == capital_e6
        ):
            return row.get("combined_net_e6") is not None
    return False


def _position_shadow_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    combined = sum(1 for row in rows if row.get("combined_net_e6") is not None)
    provisional = sum(1 for row in rows if row.get("combined_net_e6") is None)
    worst = report.get("worst_combined_net_e6")
    best = report.get("best_combined_net_e6")
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; combined={combined}; "
        f"provisional={provisional}; worst {_usd_or_na(worst)}; best {_usd_or_na(best)}"
    )


def _real_position_complete(report: dict) -> bool:
    return bool(report.get("complete")) and len(report.get("rows", [])) > 0


def _real_position_observed(report: dict) -> str:
    rows = report.get("rows", [])
    status = str(report.get("status", "missing input"))
    if rows:
        row = rows[0]
        position_id = str(row.get("position_id", report.get("target_position_id", "n/a")))
        net = int(row.get("net_vs_hodl_e6", 0))
        bps = float(row.get("net_vs_hodl_bps", 0))
        return f"{status}; position={position_id}; net {_usd(net)}; net {bps:.2f} bps"
    missing = report.get("missing_fields", [])
    missing_text = ",".join(str(field) for field in missing) or "input artifact"
    return f"{status}; missing={missing_text}"


def _real_position_portfolio_complete(report: dict) -> bool:
    return bool(report.get("complete"))


def _real_position_portfolio_observed(report: dict) -> str:
    summary = report.get("summary", {})
    breadth = report.get("breadth", {})
    positions = int(summary.get("complete_positions", 0))
    min_positions = int(report.get("min_audited_positions", 3))
    net = int(summary.get("net_vs_hodl_e6", 0))
    bps = float(summary.get("net_vs_hodl_bps", 0))
    return (
        f"{positions}/{min_positions} positions; pairs={int(breadth.get('pool_pairs', 0))}; "
        f"fee tiers={int(breadth.get('fee_tiers', 0))}; range statuses={int(breadth.get('range_statuses', 0))}; "
        f"net {_usd(net)}; net {bps:.2f} bps"
    )


def _route_break_even_complete(route_break_even: dict) -> bool:
    windows = {str(row.get("window", "")) for row in route_break_even.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows)


def _route_break_even_observed(route_break_even: dict) -> str:
    rows = route_break_even.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}"


def _adverse_route_away_complete(adverse_route_away: dict) -> bool:
    rows = adverse_route_away.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    rates = {float(row.get("route_away", 0)) for row in rows}
    return {"calm", "vol"}.issubset(windows) and {0.10, 0.25, 0.50, 0.75}.issubset(rates)


def _adverse_route_away_observed(adverse_route_away: dict) -> str:
    rows = adverse_route_away.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    worst_gap = min((float(row.get("adverse_gap_bps", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; worst gap {worst_gap:.2f} bps"


def _route_readiness_complete(route_readiness: dict, route_ab: dict) -> bool:
    return _route_ab_complete(route_ab) or bool(route_readiness.get("ready_to_collect")) or bool(
        route_readiness.get("controlled_result_complete")
    )


def _route_readiness_observed(route_readiness: dict, route_ab: dict) -> str:
    if _route_ab_complete(route_ab):
        return "controlled result artifact complete"
    status = str(route_readiness.get("status", "missing checklist"))
    missing = route_readiness.get("missing_inputs", [])
    failed = route_readiness.get("failed_validations", [])
    parts = [status]
    if missing:
        parts.append("missing=" + ",".join(str(item) for item in missing))
    if failed:
        parts.append("failed=" + ",".join(str(item) for item in failed))
    return "; ".join(parts)


def _route_cost_complete(route_cost_proxy: dict) -> bool:
    rows = route_cost_proxy.get("rows", [])
    pairs = {str(row.get("pair", "")) for row in rows}
    sizes = {int(row.get("trade_size_e6", 0)) for row in rows}
    fee_tiers = {int(row.get("fee_pips", 0)) for row in rows}
    return {"WETH/USDC", "WETH/USDT"}.issubset(pairs) and {1_000_000_000, 10_000_000_000, 50_000_000_000}.issubset(sizes) and {100, 500, 3000}.issubset(fee_tiers)


def _route_cost_observed(route_cost_proxy: dict) -> str:
    rows = route_cost_proxy.get("rows", [])
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    headroom = "n/a"
    for row in rows:
        if row.get("pair") == "WETH/USDC" and int(row.get("trade_size_e6", 0)) == 50_000_000_000 and int(row.get("fee_pips", 0)) == 500:
            value = row.get("pegguard_headroom_bps")
            headroom = "n/a" if value is None else f"{float(value):.2f} bps"
            break
    return f"{len(rows)} rows; pairs={','.join(pairs) or 'none'}; WETH/USDC $50k headroom {headroom}"


def _quote_route_readiness_complete(quote_route_readiness: dict) -> bool:
    return bool(quote_route_readiness.get("quote_result_complete")) or bool(quote_route_readiness.get("ready_to_collect"))


def _quote_route_readiness_observed(quote_route_readiness: dict) -> str:
    if quote_route_readiness.get("quote_result_complete"):
        quoted = int(quote_route_readiness.get("quoted_rows", 0))
        total = int(quote_route_readiness.get("quote_rows", 0))
        return f"complete; quoted rows={quoted}/{total}"
    status = str(quote_route_readiness.get("status", "missing checklist"))
    missing = quote_route_readiness.get("missing_inputs", [])
    failed = quote_route_readiness.get("failed_validations", [])
    parts = [status]
    if missing:
        parts.append("missing=" + ",".join(str(item) for item in missing))
    if failed:
        parts.append("failed=" + ",".join(str(item) for item in failed))
    return "; ".join(parts)


def _quote_headroom_complete(quote_headroom_report: dict) -> bool:
    rows = quote_headroom_report.get("rows", [])
    return bool(rows) and any(
        row.get("premium_headroom_bps") is not None and float(row.get("premium_headroom_bps", 0)) > 0
        for row in rows
    )


def _quote_headroom_observed(quote_headroom_report: dict) -> str:
    rows = quote_headroom_report.get("rows", [])
    values = [float(row.get("premium_headroom_bps", 0)) for row in rows if row.get("premium_headroom_bps") is not None]
    positive = sum(1 for value in values if value > 0)
    minimum = min(values) if values else 0.0
    maximum = max(values) if values else 0.0
    return f"{len(rows)} rows; positive={positive}; min {minimum:.4f} bps; max {maximum:.4f} bps"


def _cross_pair_quote_headroom_observed(quote_headroom_report: dict) -> str:
    source = str(quote_headroom_report.get("quote_source", "n/a"))
    return f"{_quote_headroom_observed(quote_headroom_report)}; source={Path(source).name}"


def _quote_headroom_stability_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    return bool(report.get("complete")) and bool(rows) and all(bool(row.get("passed")) for row in rows)


def _quote_headroom_stability_observed(report: dict) -> str:
    rows = report.get("rows", [])
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    passed = sum(1 for row in rows if row.get("passed"))
    min_headroom = report.get("min_repeat_headroom_bps")
    max_delta = report.get("max_abs_delta_headroom_bps")
    return (
        f"{passed}/{len(rows)} rows; pairs={','.join(pairs) or 'none'}; "
        f"min repeat {_bps_or_na(min_headroom)}; max abs delta {_bps_or_na(max_delta)}"
    )


def _quote_headroom_drift_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    return (
        bool(report.get("complete"))
        and bool(rows)
        and int(report.get("distinct_block_count", 0)) >= 2
        and all(bool(row.get("passed")) and int(row.get("distinct_blocks", 0)) >= 2 for row in rows)
    )


def _quote_headroom_drift_observed(report: dict) -> str:
    rows = report.get("rows", [])
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    passed = sum(1 for row in rows if row.get("passed"))
    return (
        f"{passed}/{len(rows)} rows; pairs={','.join(pairs) or 'none'}; "
        f"samples={int(report.get('sample_count', 0))}; blocks={int(report.get('distinct_block_count', 0))}; "
        f"min headroom {_bps_or_na(report.get('min_headroom_bps'))}; "
        f"max drift {_bps_or_na(report.get('max_abs_first_to_last_delta_bps'))}"
    )


def _quote_premium_stress_complete(quote_premium_stress_report: dict) -> bool:
    rows = quote_premium_stress_report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    return bool(quote_premium_stress_report.get("buckets")) and {"calm", "vol"}.issubset(windows)


def _quote_premium_stress_observed(quote_premium_stress_report: dict) -> str:
    rows = quote_premium_stress_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    over_rows = sum(int(row.get("over_headroom_rows", 0)) for row in rows)
    excess = sum(int(row.get("excess_e6", 0)) for row in rows)
    max_share = max(
        (float(row.get("excess_share_of_extra", 0)) for row in rows if row.get("excess_share_of_extra") is not None),
        default=0.0,
    )
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; over={over_rows}; excess {_usd(excess)}; max excess share {max_share:.2%}"


def _quote_event_headroom_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    charged = sum(int(row.get("charged_rows", 0)) for row in rows)
    return bool(report.get("quote_points")) and {"calm", "vol"}.issubset(windows) and charged > 0


def _quote_event_headroom_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    over_rows = sum(int(row.get("over_budget_rows", 0)) for row in rows)
    above_max = sum(int(row.get("above_max_quote_rows", 0)) for row in rows)
    excess = sum(int(row.get("excess_e6", 0)) for row in rows)
    max_share = max(
        (float(row.get("excess_share_of_extra", 0)) for row in rows if row.get("excess_share_of_extra") is not None),
        default=0.0,
    )
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; over={over_rows}; "
        f"above quote max={above_max}; excess {_usd(excess)}; max excess share {max_share:.2%}"
    )


def _quote_provenance_complete(report: dict) -> bool:
    return (
        bool(report.get("complete"))
        and int(report.get("artifact_count", 0)) >= 4
        and int(report.get("present_count", 0)) >= 4
        and int(report.get("quoted_rows", 0)) > 0
    )


def _quote_provenance_observed(report: dict) -> str:
    return (
        f"{int(report.get('present_count', 0))}/{int(report.get('artifact_count', 0))} artifacts; "
        f"quoted={int(report.get('quoted_rows', 0))}/{int(report.get('total_quote_rows', 0))}; "
        f"pinned={int(report.get('pinned_block_artifacts', 0))}; "
        f"latest={int(report.get('latest_block_tag_artifacts', 0))}; "
        f"missing_generated_at={int(report.get('missing_generated_at_artifacts', 0))}; "
        f"warnings={len(report.get('warnings', []))}"
    )


def _quote_elasticity_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    margins = {float(row.get("budget_margin", 0)) for row in rows}
    return {"calm", "vol"}.issubset(windows) and {1.0, 0.5, 0.25, 0.10}.issubset(margins)


def _quote_elasticity_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_loss = max((float(row.get("lost_share_of_extra", 0)) for row in rows if row.get("lost_share_of_extra") is not None), default=0.0)
    max_lost = max((int(row.get("lost_extra_e6", 0)) for row in rows), default=0)
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; max lost share {max_loss:.2%}; max lost {_usd(max_lost)}"


def _insurance_reserve_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    bases = {str(row.get("claim_basis", "")) for row in rows}
    rates = {float(row.get("payout_rate", 0)) for row in rows}
    return (
        {"calm", "vol"}.issubset(windows)
        and {
            "charged correcting markout",
            "all truth-correcting markout",
            "all positive markout",
        }.issubset(bases)
        and {0.25, 0.5, 1.0}.issubset(rates)
    )


def _insurance_reserve_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    worst_seed = max((int(row.get("max_deficit_e6", 0)) for row in rows), default=0)
    coverage_values = [
        float(row.get("coverage_ratio", 0))
        for row in rows
        if row.get("coverage_ratio") is not None
    ]
    min_coverage = min(coverage_values) if coverage_values else None
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; max seed {_usd(worst_seed)}; min coverage {_ratio(min_coverage)}"


def _reserve_lifecycle_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    horizons = {int(row.get("horizon_days", 0)) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    bases = {str(row.get("claim_basis", "")) for row in rows}
    return (
        {"calm", "vol"}.issubset(windows)
        and {30, 90}.issubset(horizons)
        and {"monthly 25% surplus skim", "monthly 10% LP churn"}.issubset(policies)
        and {"charged correcting markout", "all truth-correcting markout"}.issubset(bases)
    )


def _premium_allocation_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    shares = {float(row.get("reserve_share", 0)) for row in rows}
    bases = {str(row.get("claim_basis", "")) for row in rows}
    return (
        {"calm", "vol"}.issubset(windows)
        and {0.0, 0.25, 0.5, 0.75, 1.0}.issubset(shares)
        and {"charged correcting markout", "all truth-correcting markout"}.issubset(bases)
    )


def _premium_allocation_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_seed = max((int(row.get("reserve_required_seed_e6", 0)) for row in rows), default=0)
    solvent = sum(1 for row in rows if row.get("reserve_unseeded_solvent"))
    min_lp_bps = min((float(row.get("lp_net_before_claims_bps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"unseeded solvent={solvent}; max seed {_usd(max_seed)}; min LP net {min_lp_bps:.2f} bps"
    )


def _premium_utilization_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    return (
        {"calm", "vol", "live shadow"}.issubset(windows)
        and int(report.get("cap_pips", 0)) == C.CAP_PIPS
        and any(int(row.get("charged_rows", 0)) > 0 for row in rows)
    )


def _premium_utilization_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_cap_hits = max((int(row.get("cap_hit_rows", 0)) for row in rows), default=0)
    max_near_cap = max((int(row.get("near_cap_rows", 0)) for row in rows), default=0)
    min_precision = min(
        (float(row.get("precision", 0)) for row in rows if row.get("precision") is not None),
        default=None,
    )
    max_p99 = max(
        (float(row.get("p99_charged_premium_bps", 0)) for row in rows if row.get("p99_charged_premium_bps") is not None),
        default=None,
    )
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"min precision {_pct_or_na(min_precision)}; p99 max {_bps_or_na(max_p99)}; "
        f"cap hits max {max_cap_hits}; near cap max {max_near_cap}"
    )


def _charge_attribution_complete(report: dict) -> bool:
    windows = report.get("windows", [])
    names = {str(row.get("window", "")) for row in windows}
    return (
        {"calm", "vol", "live shadow"}.issubset(names)
        and all(len(row.get("buckets", [])) >= 4 for row in windows)
        and any(int(row.get("charged_rows", 0)) > 0 for row in windows)
    )


def _charge_attribution_observed(report: dict) -> str:
    windows = report.get("windows", [])
    names = sorted({str(row.get("window", "")) for row in windows if row.get("window")})
    min_precision = min(
        (float(row.get("precision", 0)) for row in windows if row.get("precision") is not None),
        default=None,
    )
    max_false_share = max(
        (float(row.get("false_charge_extra_share", 0)) for row in windows if row.get("false_charge_extra_share") is not None),
        default=None,
    )
    min_markout_coverage = min(
        (
            float(row.get("truth_correcting_markout_coverage", 0))
            for row in windows
            if row.get("truth_correcting_markout_coverage") is not None
        ),
        default=None,
    )
    max_missed = max((int(row.get("missed_correcting_abs_markout_e6", 0)) for row in windows), default=0)
    return (
        f"{len(windows)} windows; windows={','.join(names) or 'none'}; "
        f"min precision {_pct_or_na(min_precision)}; max false-charge extra {_pct_or_na(max_false_share)}; "
        f"min correcting markout coverage {_pct_or_na(min_markout_coverage)}; max missed {_usd(max_missed)}"
    )


def _reserve_delay_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    delays = {int(row.get("claim_delay_days", -1)) for row in rows}
    bases = {str(row.get("claim_basis", "")) for row in rows}
    rates = {float(row.get("payout_rate", 0)) for row in rows}
    return (
        {"calm", "vol", "live shadow"}.issubset(windows)
        and {0, 1, 7, 30}.issubset(delays)
        and {"charged correcting markout", "all truth-correcting markout"}.issubset(bases)
        and {0.5, 1.0}.issubset(rates)
    )


def _reserve_delay_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_economic_seed = max((int(row.get("required_economic_seed_e6", 0)) for row in rows), default=0)
    max_hidden_gap = max((int(row.get("hidden_liability_gap_e6", 0)) for row in rows), default=0)
    econ_failures = sum(1 for row in rows if not row.get("economically_solvent_without_seed"))
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"econ failures={econ_failures}; max economic seed {_usd(max_economic_seed)}; max hidden gap {_usd(max_hidden_gap)}"
    )


def _reserve_lifecycle_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_topup = max((int(row.get("required_topup_e6", 0)) for row in rows), default=0)
    failures = sum(1 for row in rows if not row.get("survived_without_topup"))
    max_withdrawal_share = max(
        (
            float(row.get("withdrawal_share_of_premium", 0))
            for row in rows
            if row.get("withdrawal_share_of_premium") is not None
        ),
        default=0.0,
    )
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"failures={failures}; max top-up {_usd(max_topup)}; max withdrawal/premium {max_withdrawal_share:.2%}"
    )


def _reserve_tail_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    bases = {str(row.get("claim_basis", "")) for row in rows}
    rates = {float(row.get("payout_rate", 0)) for row in rows}
    return (
        int(report.get("iterations", 0)) > 0
        and {"calm", "vol"}.issubset(windows)
        and {
            "charged correcting markout",
            "all truth-correcting markout",
            "all positive markout",
        }.issubset(bases)
        and {0.25, 0.5, 1.0}.issubset(rates)
    )


def _reserve_tail_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    worst_p99 = max((int(row.get("p99_seed_e6", 0)) for row in rows), default=0)
    worst_cvar = max((int(row.get("cvar95_seed_e6", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows, {int(report.get('iterations', 0))} iterations; "
        f"windows={','.join(windows) or 'none'}; p99 seed {_usd(worst_p99)}; CVaR95 {_usd(worst_cvar)}"
    )


def _bootstrap_report_complete(bootstrap_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in bootstrap_report.get("windows", [])}
    return {"calm", "vol"}.issubset(windows)


def _bootstrap_report_observed(bootstrap_report: dict) -> str:
    windows = [str(row.get("window", "")) for row in bootstrap_report.get("windows", [])]
    iterations = int(bootstrap_report.get("iterations", 0))
    return f"{len(windows)} windows, {iterations} iterations: {', '.join(windows) or 'none'}"


def _headline_uncertainty_complete(report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in report.get("windows", [])}
    policy_pairs = {
        (str(row.get("window", "")), str(row.get("policy", "")))
        for row in report.get("policies", [])
    }
    required_policy_pairs = {
        (window, policy)
        for window in ("calm", "vol")
        for policy in ("micro passive", "small active", "focused active")
    }
    return (
        int(report.get("iterations", 0)) >= 100
        and {"calm", "vol"}.issubset(windows)
        and required_policy_pairs.issubset(policy_pairs)
    )


def _headline_uncertainty_observed(report: dict) -> str:
    windows = [str(row.get("window", "")) for row in report.get("windows", [])]
    policy_rows = len(report.get("policies", []))
    vol_capture_p05 = next(
        (
            row.get("capture_p05")
            for row in report.get("windows", [])
            if str(row.get("window", "")) == "vol"
        ),
        None,
    )
    capture = "n/a" if vol_capture_p05 is None else f"{float(vol_capture_p05):.2%}"
    return (
        f"{len(windows)} windows, {policy_rows} policy rows, {int(report.get('iterations', 0))} iterations; "
        f"windows={','.join(windows) or 'none'}; vol capture p05 {capture}"
    )


def _size_bucket_complete(size_bucket_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in size_bucket_report.get("rows", [])}
    return {"calm", "vol"}.issubset(windows)


def _size_bucket_observed(size_bucket_report: dict) -> str:
    rows = size_bucket_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    buckets = sorted({str(row.get("bucket", "")) for row in rows})
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}; buckets={len(buckets)}"


def _staleness_bucket_complete(staleness_bucket_report: dict) -> bool:
    buckets = {str(row.get("bucket", "")) for row in staleness_bucket_report.get("buckets", [])}
    return int(staleness_bucket_report.get("rows", 0)) > 0 and {"<=1s", "1-2s", "2-5s", ">5s/missing"}.issubset(buckets)


def _staleness_bucket_observed(staleness_bucket_report: dict) -> str:
    buckets = staleness_bucket_report.get("buckets", [])
    nonempty = [str(row.get("bucket", "")) for row in buckets if int(row.get("rows", 0)) > 0]
    return f"{int(staleness_bucket_report.get('rows', 0))} rows; nonempty={', '.join(nonempty) or 'none'}"


def _market_regime_complete(report: dict) -> bool:
    if not report.get("complete"):
        return False
    rows = report.get("rows", [])
    required = {"all", "quiet <1bp", "normal 1-5bp", "high-vol >=5bp"}
    for window in ("calm", "vol"):
        labels = {
            str(row.get("segment", ""))
            for row in rows
            if row.get("window") == window and int(row.get("rows", 0)) > 0
        }
        if not required.issubset(labels):
            return False
    live_rows = [row for row in rows if row.get("window") == "live shadow"]
    if live_rows and not any(row.get("segment") == "oracle-lag/fallback" and int(row.get("rows", 0)) > 0 for row in live_rows):
        return False
    return all("low_l2_net_bps" in row and "stressed_l2_net_bps" in row for row in rows)


def _market_regime_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = ",".join(sorted({str(row.get("window", "")) for row in rows if row.get("window")}))
    high_vol = _market_regime_row(rows, "live shadow", "high-vol >=5bp")
    oracle_lag = _market_regime_row(rows, "live shadow", "oracle-lag/fallback")
    return (
        f"{len(rows)} rows; windows={windows or 'none'}; "
        f"live high-vol net {_bps_or_na(high_vol.get('net_bps') if high_vol else None)}; "
        f"oracle-lag rows {int(oracle_lag.get('rows', 0)) if oracle_lag else 0}"
    )


def _market_regime_row(rows: list[dict], window: str, segment: str) -> dict:
    return next((row for row in rows if row.get("window") == window and row.get("segment") == segment), {})


def _signal_quality_stress_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        {"calm", "vol"}.issubset(windows)
        and {"observed", "miss 50pct correct", "false 100pct correct"}.issubset(scenarios)
        and all("aligned_net_bps" in row and "raw_minus_aligned_bps" in row for row in rows)
    )


def _signal_quality_stress_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = ",".join(sorted({str(row.get("window", "")) for row in rows if row.get("window")}))
    broken = sum(1 for row in rows if row.get("status") == "precision broken")
    worst_aligned = min((float(row.get("aligned_net_bps", 0)) for row in rows), default=0.0)
    max_gap = max((float(row.get("raw_minus_aligned_bps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; windows={windows or 'none'}; precision-broken={broken}; "
        f"worst aligned net {worst_aligned:.4f} bps; max raw/aligned gap {max_gap:.4f} bps"
    )


def _signal_margin_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    return (
        {"calm", "vol"}.issubset(windows)
        and all("precision_breakeven" in row and "max_missed_correct_share" in row for row in rows)
    )


def _signal_margin_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = ",".join(sorted({str(row.get("window", "")) for row in rows if row.get("window")}))
    min_headroom = min(
        (float(row.get("precision_headroom_pp", 0)) for row in rows if row.get("precision_headroom_pp") is not None),
        default=0.0,
    )
    max_missed = max(
        (float(row.get("max_missed_correct_share", 0)) for row in rows if row.get("max_missed_correct_share") is not None),
        default=0.0,
    )
    negative = sum(1 for row in rows if str(row.get("status", "")).startswith("already below"))
    return (
        f"{len(rows)} rows; windows={windows or 'none'}; min precision headroom {min_headroom * 100:.2f} pp; "
        f"max missed-correct tolerance {max_missed:.2%}; below break-even={negative}"
    )


def _base_fee_report_complete(base_fee_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in base_fee_report.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows)


def _base_fee_report_observed(base_fee_report: dict) -> str:
    rows = base_fee_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}"


def _markout_sensitivity_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    required_multipliers = {0.5, 0.75, 1.0, 1.25, 1.5, 2.0}
    for window in ("calm", "vol"):
        multipliers = {
            round(float(row.get("markout_multiplier", 0)), 2)
            for row in rows
            if str(row.get("window", "")) == window and str(row.get("strategy", "")) == "PegGuard selected"
        }
        if not required_multipliers.issubset(multipliers):
            return False
    return True


def _markout_sensitivity_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    worst_net = min((float(row.get("net_bps", 0)) for row in rows), default=0.0)
    max_required = max((int(row.get("required_base_pips_zero", 0)) for row in rows), default=0)
    return f"{len(rows)} rows: {', '.join(windows) or 'none'}; worst net {worst_net:.2f} bps; max zero-net base {max_required / 100:.2f} bps"


def _target_fee_report_complete(target_fee_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in target_fee_report.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows) and int(target_fee_report.get("route_total_notional_e6", 0)) > 0


def _target_fee_report_observed(target_fee_report: dict) -> str:
    rows = target_fee_report.get("rows", [])
    viability = sorted({str(row.get("viability", "")) for row in rows})
    return f"{len(rows)} rows; route notional {_usd(int(target_fee_report.get('route_total_notional_e6', 0)))}; {','.join(viability) or 'none'}"


def _capital_path_report_complete(capital_path_report: dict) -> bool:
    paths = {str(row.get("path", "")) for row in capital_path_report.get("rows", [])}
    return {"calm 30d", "weekly vol shock 30d", "all volatile 7d"}.issubset(paths)


def _capital_path_report_observed(capital_path_report: dict) -> str:
    rows = capital_path_report.get("rows", [])
    paths = sorted({str(row.get("path", "")) for row in rows})
    worst_drawdown = min((float(row.get("max_drawdown", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows; paths={len(paths)}; worst drawdown {worst_drawdown:.2%}"


def _policy_monte_carlo_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    mixes = {str(row.get("mix", "")) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        int(report.get("iterations", 0)) > 0
        and {"routine 30d", "shock 30d", "stress 30d", "routine 90d"}.issubset(mixes)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    )


def _policy_monte_carlo_observed(report: dict) -> str:
    rows = report.get("rows", [])
    mixes = sorted({str(row.get("mix", "")) for row in rows if row.get("mix")})
    worst_loss = max((float(row.get("probability_loss", 0)) for row in rows), default=0.0)
    worst_drawdown = max((float(row.get("probability_drawdown_gt_1pct", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows, {int(report.get('iterations', 0))} iterations; "
        f"mixes={','.join(mixes) or 'none'}; max P(loss) {worst_loss:.2%}; max P(dd>1%) {worst_drawdown:.2%}"
    )


def _risk_adjusted_return_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    mixes = {str(row.get("mix", "")) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        len(rows) > 0
        and {"routine 30d", "shock 30d", "stress 30d", "routine 90d"}.issubset(mixes)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    )


def _risk_adjusted_return_observed(report: dict) -> str:
    rows = report.get("rows", [])
    mixes = sorted({str(row.get("mix", "")) for row in rows if row.get("mix")})
    viable = sum(1 for row in rows if row.get("status") == "risk-adjusted viable")
    max_loss_day = max((float(row.get("loss_day_probability", 0)) for row in rows), default=0.0)
    min_sortino = min(
        (float(row["sortino_like"]) for row in rows if row.get("sortino_like") is not None),
        default=0.0,
    )
    return (
        f"{len(rows)} rows; mixes={','.join(mixes) or 'none'}; "
        f"viable={viable}; max loss-day {max_loss_day:.2%}; min sortino {min_sortino:.2f}"
    )


def _chain_cost_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    chains = {str(row.get("chain", "")) for row in rows}
    windows = {str(row.get("window", "")) for row in rows}
    return (
        len(rows) > 0
        and {"base", "unichain", "arbitrum", "ethereum"}.issubset(chains)
        and {"calm", "vol"}.issubset(windows)
        and int(report.get("hook_gas", 0)) > 0
        and int(report.get("default_pyth_update_gas", 0)) > 0
    )


def _chain_cost_observed(report: dict) -> str:
    rows = report.get("rows", [])
    chains = sorted({str(row.get("chain", "")) for row in rows if row.get("chain")})
    min_net = min((float(row.get("net_after_chain_cost_bps", 0)) for row in rows), default=0.0)
    max_gas_bps = max((float(row.get("gas_bps", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows; chains={','.join(chains) or 'none'}; min net {min_net:.2f} bps; max gas {max_gas_bps:.2f} bps"


def _live_gas_snapshot_complete(report: dict) -> bool:
    snapshots = report.get("snapshots", [])
    rows = report.get("rows", [])
    ok_chains = {str(row.get("chain", "")) for row in snapshots if row.get("ok")}
    windows = {str(row.get("window", "")) for row in rows if row.get("gas_bps") is not None}
    return {"base", "unichain", "arbitrum", "ethereum"}.issubset(ok_chains) and {"calm", "vol"}.issubset(windows)


def _live_gas_snapshot_observed(report: dict) -> str:
    snapshots = report.get("snapshots", [])
    rows = report.get("rows", [])
    ok = sum(1 for row in snapshots if row.get("ok"))
    max_gas = max((float(row.get("gas_bps", 0)) for row in rows if row.get("gas_bps") is not None), default=0.0)
    min_net = min(
        (float(row.get("net_after_live_gas_bps", 0)) for row in rows if row.get("net_after_live_gas_bps") is not None),
        default=0.0,
    )
    return f"{ok}/{len(snapshots)} RPCs ok; rows={len(rows)}; max gas {max_gas:.4f} bps; min net {min_net:.2f} bps"


def _control_plane_cost_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    priced_chains = {str(row.get("chain", "")) for row in rows if row.get("episode_cost_e6") is not None}
    return (
        bool(report.get("complete"))
        and int(report.get("trigger_count", 0)) > 0
        and int(report.get("measured_bleed_e6", 0)) > 0
        and {"base", "unichain", "arbitrum", "ethereum"}.issubset(priced_chains)
    )


def _control_plane_cost_observed(report: dict) -> str:
    rows = report.get("rows", [])
    priced = [row for row in rows if row.get("episode_cost_e6") is not None]
    max_cost = max((int(row.get("episode_cost_e6", 0)) for row in priced), default=0)
    max_bleed_bps = max(
        (float(row.get("cost_vs_measured_bleed_bps", 0)) for row in priced if row.get("cost_vs_measured_bleed_bps") is not None),
        default=0.0,
    )
    max_equiv = max((float(row.get("hot_path_equivalent_swaps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; triggers={int(report.get('trigger_count', 0))}; "
        f"max cost {_usd_or_na(max_cost)}; max bleed cost {max_bleed_bps:.4f} bps; "
        f"hot-path equiv {max_equiv:.2f} swaps"
    )


def _pnl_attribution_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol"}.issubset(windows)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    )


def _pnl_attribution_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    drags = sorted({str(row.get("dominant_drag", "")) for row in rows if row.get("dominant_drag")})
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"min APR {min_apr:.2%}; drags={','.join(drags) or 'none'}"
    )


def _capital_survival_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("label", "")) for row in rows if row.get("kind") == "window"}
    mixes = {str(row.get("label", "")) for row in rows if row.get("kind") == "mix"}
    policies = {str(row.get("policy", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol"}.issubset(windows)
        and {"routine 30d", "shock 30d", "stress 30d"}.issubset(mixes)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    )


def _capital_survival_observed(report: dict) -> str:
    rows = report.get("rows", [])
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    burn_days = [
        float(row.get("days_to_10pct_loss"))
        for row in rows
        if row.get("days_to_10pct_loss") is not None
    ]
    shortest = min(burn_days) if burn_days else None
    return f"{len(rows)} rows; statuses={','.join(statuses) or 'none'}; shortest 10% runway {_days(shortest)}"


def _operator_cost_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    ops = {str(row.get("ops_scenario", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol"}.issubset(windows)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"free operator", "hobby infra", "paid light ops", "active manager"}.issubset(ops)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    )


def _operator_cost_observed(report: dict) -> str:
    rows = report.get("rows", [])
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    min_apr = min((float(row.get("net_apr_after_ops", 0)) for row in rows), default=0.0)
    viable = sum(1 for row in rows if str(row.get("status", "")).startswith("viable"))
    max_ops = max((float(row.get("annual_ops_cost_usdc", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; statuses={','.join(statuses) or 'none'}; "
        f"viable={viable}; max ops {_usd_float(max_ops)}; min APR {min_apr:.2%}"
    )


def _pilot_deployability_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    policies = {str(row.get("policy", "")) for row in rows}
    ops = {str(row.get("ops_scenario", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    multipliers = {round(float(row.get("markout_multiplier", 0)), 2) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol", "live shadow"}.issubset(windows)
        and {"micro passive", "small active", "focused active"}.issubset(policies)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
        and {"free operator", "hobby infra", "paid light ops", "active manager"}.issubset(ops)
        and {1.0, 1.5, 2.0}.issubset(multipliers)
    )


def _pilot_deployability_observed(report: dict) -> str:
    rows = report.get("rows", [])
    viable = sum(1 for row in rows if row.get("status") == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and row.get("status") == "viable >=10% APR"
    )
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows; viable={viable}; 2x viable={stress_viable}; min APR {min_apr:.2%}"


def _range_width_deployability_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    widths = {int(row.get("half_width_bps", 0)) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    multipliers = {round(float(row.get("markout_multiplier", 0)), 2) for row in rows}
    return (
        len(rows) > 0
        and {"calm", "vol", "live shadow"}.issubset(windows)
        and {50, 100, 200, 500, 1000}.issubset(widths)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
        and {1.0, 1.5, 2.0}.issubset(multipliers)
    )


def _range_width_deployability_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    widths = sorted({int(row.get("half_width_bps", 0)) for row in rows if row.get("half_width_bps")})
    viable = sum(1 for row in rows if row.get("status") == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and row.get("status") == "viable >=10% APR"
    )
    best_apr = max((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    min_required = min(
        (
            float(row.get("required_turnover_for_10pct"))
            for row in rows
            if row.get("required_turnover_for_10pct") is not None
        ),
        default=None,
    )
    required = "n/a" if min_required is None else f"{min_required:.2f}x/day"
    width_text = ",".join(str(width) for width in widths) or "none"
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; widths={width_text}; "
        f"viable={viable}; 2x viable={stress_viable}; best APR {best_apr:.2%}; min req turnover {required}"
    )


def _small_capital_decision_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    profiles = {str(row.get("profile", "")) for row in rows}
    recommendations = {str(row.get("recommendation", "")) for row in rows}
    return (
        {"micro passive", "small active", "focused active", "depth-share $100k"}.issubset(profiles)
        and all(recommendation for recommendation in recommendations)
        and any(row.get("live_provisional") is not None for row in rows)
    )


def _small_capital_decision_observed(report: dict) -> str:
    rows = report.get("rows", [])
    recommendations = sorted({str(row.get("recommendation", "")) for row in rows if row.get("recommendation")})
    pilot_only = sum(1 for row in rows if str(row.get("recommendation", "")).startswith("pilot only"))
    no_go = sum(1 for row in rows if str(row.get("recommendation", "")).startswith("no-go"))
    live_note = "live complete" if report.get("live_shadow_complete") else "live provisional"
    return (
        f"{len(rows)} rows; recs={','.join(recommendations) or 'none'}; "
        f"pilot-only={pilot_only}; no-go={no_go}; {live_note}"
    )


def _alpha_sweep_complete(alpha_sweep: dict) -> bool:
    rows = alpha_sweep.get("rows", [])
    alphas = {str(row.get("alpha", "")) for row in rows}
    feasible = [row for row in rows if bool(row.get("feasible", False))]
    return "1/2" in alphas and len(feasible) > 0


def _alpha_sweep_observed(alpha_sweep: dict) -> str:
    rows = alpha_sweep.get("rows", [])
    feasible = [row for row in rows if bool(row.get("feasible", False))]
    default_rank = "n/a"
    for idx, row in enumerate(rows, start=1):
        if str(row.get("alpha", "")) == "1/2":
            default_rank = str(idx)
            break
    return f"{len(rows)} rows; feasible={len(feasible)}; default rank={default_rank}"


def _target_return_complete(target_return_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in target_return_report.get("rows", [])}
    targets = {float(row.get("target_apr", 0)) for row in target_return_report.get("rows", [])}
    return {"calm", "vol", "live shadow"}.issubset(windows) and {0.10, 0.20, 0.30}.issubset(targets)


def _target_return_observed(target_return_report: dict) -> str:
    rows = target_return_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    sufficient = sum(1 for row in rows if row.get("status") == "current turnover sufficient")
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; sufficient={sufficient}"


def _route_demand_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    tolerances = {float(row.get("tolerance_bps", 0)) for row in rows}
    return {"calm", "vol"}.issubset(windows) and {1.0, 2.0, 5.0, 10.0}.issubset(tolerances)


def _route_demand_observed(report: dict) -> str:
    rows = report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_routed = max((float(row.get("routed_notional_share", 0)) for row in rows if row.get("routed_notional_share") is not None), default=0.0)
    min_delta = min((int(row.get("delta_vs_full_e6", 0)) for row in rows), default=0)
    max_delta = max((int(row.get("delta_vs_full_e6", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows; windows={','.join(windows) or 'none'}; "
        f"max routed {max_routed:.2%}; delta range {_usd(min_delta)} to {_usd(max_delta)}"
    )


def _order_split_complete(order_split_report: dict) -> bool:
    windows = {str(row.get("window", "")) for row in order_split_report.get("rows", [])}
    child_counts = {int(row.get("child_count", 0)) for row in order_split_report.get("rows", [])}
    return {"calm", "vol"}.issubset(windows) and {2, 10, 100}.issubset(child_counts)


def _order_split_observed(order_split_report: dict) -> str:
    rows = order_split_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    max_leak = max((float(row.get("leakage_rate", 0)) for row in rows if row.get("leakage_rate") is not None), default=0.0)
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; max leakage {max_leak:.2%}"


def _sequential_split_complete(sequential_split_report: dict) -> bool:
    rows = sequential_split_report.get("rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    child_counts = {int(row.get("child_count", 0)) for row in rows}
    spacings = {int(row.get("child_spacing_sec", -1)) for row in rows}
    return {"calm", "vol"}.issubset(windows) and {2, 10}.issubset(child_counts) and {0, 30}.issubset(spacings)


def _sequential_split_observed(sequential_split_report: dict) -> str:
    rows = sequential_split_report.get("rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    max_abs_leak = max(
        (abs(float(row.get("leakage_rate", 0))) for row in rows if row.get("leakage_rate") is not None),
        default=0.0,
    )
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; max abs leakage {max_abs_leak:.2%}"


def _tvl_dilution_complete(tvl_dilution_report: dict) -> bool:
    rows = tvl_dilution_report.get("equilibrium_rows", [])
    windows = {str(row.get("window", "")) for row in rows}
    targets = {float(row.get("target_apr", 0)) for row in rows}
    route_aways = {float(row.get("route_away", 0)) for row in rows}
    return {"calm", "vol"}.issubset(windows) and {0.10, 0.20, 0.30}.issubset(targets) and {0.0, 0.25, 0.50}.issubset(route_aways)


def _tvl_dilution_observed(tvl_dilution_report: dict) -> str:
    rows = tvl_dilution_report.get("equilibrium_rows", [])
    windows = sorted({str(row.get("window", "")) for row in rows})
    live_20 = "n/a"
    for row in rows:
        if row.get("window") == "live shadow" and abs(float(row.get("route_away", 0)) - 0.25) < 1e-9 and abs(float(row.get("target_apr", 0)) - 0.20) < 1e-9:
            value = row.get("max_active_capital_e6")
            live_20 = _usd(int(value)) if value is not None else "n/a"
            break
    return f"{len(rows)} rows; windows={','.join(windows) or 'none'}; live 20% cap {live_20}"


def _lp_flow_response_complete(report: dict) -> bool:
    rows = report.get("rows", [])
    paths = {str(row.get("path", "")) for row in rows}
    scenarios = {str(row.get("scenario", "")) for row in rows}
    starts = {int(row.get("start_capital_e6", 0)) for row in rows}
    return (
        {"calm 30d", "weekly vol shock 30d", "all volatile 7d"}.issubset(paths)
        and {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
        and {10_000_000_000, 25_000_000_000, 100_000_000_000}.issubset(starts)
    )


def _lp_flow_response_observed(report: dict) -> str:
    rows = report.get("rows", [])
    paths = sorted({str(row.get("path", "")) for row in rows if row.get("path")})
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    worst_drawdown = min((float(row.get("max_drawdown", 0)) for row in rows), default=0.0)
    max_outflow_days = max((int(row.get("outflow_days", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows; paths={len(paths)}; statuses={','.join(statuses) or 'none'}; "
        f"worst drawdown {worst_drawdown:.2%}; max outflow days {max_outflow_days}"
    )


def _route_ab_complete(route_ab: dict) -> bool:
    return bool(route_ab) and not _route_ab_errors(route_ab)


def _route_ab_observed(route_ab: dict) -> str:
    if not route_ab:
        return "missing controlled route-away artifact"
    errors = _route_ab_errors(route_ab)
    if errors:
        return "invalid input; " + _summarize_errors(errors)
    payload = _route_ab_payload(route_ab)
    pre = payload.get("pre", {})
    post = payload.get("post", {})
    return (
        f"pre=({_usd(int(pre.get('baseline_notional_e6', 0)))}, {_usd(int(pre.get('treatment_notional_e6', 0)))}), "
        f"post=({_usd(int(post.get('baseline_notional_e6', 0)))}, {_usd(int(post.get('treatment_notional_e6', 0)))}), "
        f"fee_delta={(int(post.get('treatment_fee_pips', 0)) - int(pre.get('treatment_fee_pips', 0))) / 100:.2f} bps"
    )


def _route_ab_payload(route_ab: dict) -> dict:
    payload = route_ab.get("input") if route_ab.get("valid") is False else route_ab
    return payload if isinstance(payload, dict) else {}


def _route_ab_errors(route_ab: dict) -> list[str]:
    if route_ab.get("valid") is False:
        errors = route_ab.get("errors", [])
        if isinstance(errors, list) and errors:
            return [str(error) for error in errors]
    try:
        return route_ab_evidence_errors(_route_ab_payload(route_ab))
    except Exception as exc:  # pragma: no cover - defensive against malformed JSON artifacts
        return [f"route-away artifact unreadable: {exc}"]


def _summarize_errors(errors: list[str], limit: int = 4) -> str:
    shown = errors[:limit]
    suffix = f"; +{len(errors) - limit} more" if len(errors) > limit else ""
    return "; ".join(shown) + suffix


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def _pct_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _usd_or_na(value_e6: object) -> str:
    if value_e6 is None:
        return "n/a"
    return _usd(int(value_e6))


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _days(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.1f}d"


def _ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}x"


def _seconds(value_ms: object) -> str:
    if value_ms is None:
        return "n/a"
    return f"{int(value_ms) / 1000:.3f}s"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check whether all PegGuard economic tests are complete")
    parser.add_argument("--economic-tests", type=Path, default=root / "docs" / "economic_tests.json")
    parser.add_argument("--live-status", type=Path, default=root / "docs" / "live-shadow-20260607T082122Z" / "status.json")
    parser.add_argument("--live-convergence-report", type=Path, default=root / "docs" / "live_convergence_report.json")
    parser.add_argument("--live-maturity-report", type=Path, default=root / "docs" / "live_maturity_report.json")
    parser.add_argument("--live-power-report", type=Path, default=root / "docs" / "live_power_report.json")
    parser.add_argument("--route-proxy", type=Path, default=root / "docs" / "route_away_proxy.json")
    parser.add_argument("--cross-pair-route-proxy", type=Path, default=root / "docs" / "route_away_proxy_weth_usdt.json")
    parser.add_argument("--route-share-stability-report", type=Path, default=root / "docs" / "route_share_stability_report.json")
    parser.add_argument("--route-away-placebo-ab-report", type=Path, default=root / "docs" / "route_away_placebo_ab_report.json")
    parser.add_argument("--route-ab-power-report", type=Path, default=root / "docs" / "route_ab_power_report.json")
    parser.add_argument("--route-ab-sizing-report", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    parser.add_argument("--guard-depeg-report", type=Path, default=root / "docs" / "guard_depeg_report.json")
    parser.add_argument("--stable-opportunity-report", type=Path, default=root / "docs" / "stable_opportunity_report.json")
    parser.add_argument("--depth-proxy", type=Path, default=root / "docs" / "depth_proxy.json")
    parser.add_argument("--cross-pair-depth-proxy", type=Path, default=root / "docs" / "depth_proxy_weth_usdt.json")
    parser.add_argument("--oracle-health", type=Path, default=root / "docs" / "oracle_health.json")
    parser.add_argument("--oracle-lag", type=Path, default=root / "docs" / "oracle_lag_report.json")
    parser.add_argument("--risk-report", type=Path, default=root / "docs" / "risk_report.json")
    parser.add_argument("--drawdown-stop", type=Path, default=root / "docs" / "drawdown_stop_report.json")
    parser.add_argument("--fallback-attribution", type=Path, default=root / "docs" / "fallback_attribution.json")
    parser.add_argument("--inventory-report", type=Path, default=root / "docs" / "inventory_report.json")
    parser.add_argument("--hedge-report", type=Path, default=root / "docs" / "hedge_report.json")
    parser.add_argument("--hedge-execution-report", type=Path, default=root / "docs" / "hedge_execution_report.json")
    parser.add_argument("--liquidity-share-report", type=Path, default=root / "docs" / "liquidity_share_report.json")
    parser.add_argument("--route-break-even", type=Path, default=root / "docs" / "route_away_break_even.json")
    parser.add_argument("--adverse-route-away", type=Path, default=root / "docs" / "adverse_route_away_report.json")
    parser.add_argument("--route-readiness", type=Path, default=root / "docs" / "route_away_readiness.json")
    parser.add_argument("--bootstrap-report", type=Path, default=root / "docs" / "bootstrap_report.json")
    parser.add_argument("--size-bucket-report", type=Path, default=root / "docs" / "size_bucket_report.json")
    parser.add_argument("--staleness-bucket-report", type=Path, default=root / "docs" / "staleness_bucket_report.json")
    parser.add_argument("--market-regime-report", type=Path, default=root / "docs" / "market_regime_report.json")
    parser.add_argument("--signal-quality-stress-report", type=Path, default=root / "docs" / "signal_quality_stress_report.json")
    parser.add_argument("--signal-margin-report", type=Path, default=root / "docs" / "signal_margin_report.json")
    parser.add_argument("--base-fee-report", type=Path, default=root / "docs" / "base_fee_report.json")
    parser.add_argument("--target-fee-report", type=Path, default=root / "docs" / "target_fee_report.json")
    parser.add_argument("--capital-path-report", type=Path, default=root / "docs" / "capital_path_report.json")
    parser.add_argument("--policy-monte-carlo-report", type=Path, default=root / "docs" / "policy_monte_carlo_report.json")
    parser.add_argument("--risk-adjusted-return-report", type=Path, default=root / "docs" / "risk_adjusted_return_report.json")
    parser.add_argument("--chain-cost-report", type=Path, default=root / "docs" / "chain_cost_report.json")
    parser.add_argument("--live-gas-snapshot-report", type=Path, default=root / "docs" / "live_gas_snapshot_report.json")
    parser.add_argument("--control-plane-cost-report", type=Path, default=root / "docs" / "control_plane_cost_report.json")
    parser.add_argument("--pnl-attribution-report", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    parser.add_argument("--capital-survival-report", type=Path, default=root / "docs" / "capital_survival_report.json")
    parser.add_argument("--operator-cost-report", type=Path, default=root / "docs" / "operator_cost_report.json")
    parser.add_argument("--alpha-sweep", type=Path, default=root / "docs" / "alpha_sweep.json")
    parser.add_argument("--target-return-report", type=Path, default=root / "docs" / "target_return_report.json")
    parser.add_argument("--route-ab", type=Path, default=root / "docs" / "route_away_ab.json")
    parser.add_argument("--order-split-report", type=Path, default=root / "docs" / "order_split_report.json")
    parser.add_argument("--tvl-dilution-report", type=Path, default=root / "docs" / "tvl_dilution_report.json")
    parser.add_argument("--route-cost-proxy", type=Path, default=root / "docs" / "route_cost_proxy.json")
    parser.add_argument("--sequential-split-report", type=Path, default=root / "docs" / "sequential_split_report.json")
    parser.add_argument("--quote-route-readiness", type=Path, default=root / "docs" / "quote_route_readiness.json")
    parser.add_argument("--quote-headroom-report", type=Path, default=root / "docs" / "quote_headroom_report.json")
    parser.add_argument("--cross-pair-quote-headroom-report", type=Path, default=root / "docs" / "quote_headroom_weth_usdt.json")
    parser.add_argument("--quote-headroom-stability-report", type=Path, default=root / "docs" / "quote_headroom_stability_report.json")
    parser.add_argument("--quote-headroom-drift-report", type=Path, default=root / "docs" / "quote_headroom_drift_report.json")
    parser.add_argument("--quote-premium-stress-report", type=Path, default=root / "docs" / "quote_premium_stress.json")
    parser.add_argument("--quote-event-headroom-report", type=Path, default=root / "docs" / "quote_event_headroom_report.json")
    parser.add_argument("--quote-provenance-report", type=Path, default=root / "docs" / "quote_provenance_report.json")
    parser.add_argument("--quote-elasticity-report", type=Path, default=root / "docs" / "quote_elasticity_report.json")
    parser.add_argument("--insurance-reserve-report", type=Path, default=root / "docs" / "insurance_reserve_report.json")
    parser.add_argument("--premium-allocation-report", type=Path, default=root / "docs" / "premium_allocation_report.json")
    parser.add_argument("--premium-utilization-report", type=Path, default=root / "docs" / "premium_utilization_report.json")
    parser.add_argument("--charge-attribution-report", type=Path, default=root / "docs" / "charge_attribution_report.json")
    parser.add_argument("--reserve-delay-report", type=Path, default=root / "docs" / "reserve_delay_report.json")
    parser.add_argument("--reserve-lifecycle-report", type=Path, default=root / "docs" / "reserve_lifecycle_report.json")
    parser.add_argument("--reserve-tail-report", type=Path, default=root / "docs" / "reserve_tail_report.json")
    parser.add_argument("--route-demand-report", type=Path, default=root / "docs" / "route_demand_report.json")
    parser.add_argument("--markout-sensitivity-report", type=Path, default=root / "docs" / "markout_sensitivity_report.json")
    parser.add_argument("--pilot-deployability-report", type=Path, default=root / "docs" / "pilot_deployability_report.json")
    parser.add_argument("--range-width-deployability-report", type=Path, default=root / "docs" / "range_width_deployability_report.json")
    parser.add_argument("--position-shadow-report", type=Path, default=root / "docs" / "position_shadow_report.json")
    parser.add_argument("--small-capital-decision-report", type=Path, default=root / "docs" / "small_capital_decision_report.json")
    parser.add_argument("--real-position-report", type=Path, default=root / "docs" / "real_position_report.json")
    parser.add_argument("--real-position-portfolio-report", type=Path, default=root / "docs" / "real_position_portfolio_report.json")
    parser.add_argument("--headline-uncertainty-report", type=Path, default=root / "docs" / "headline_uncertainty_report.json")
    parser.add_argument("--lp-flow-response-report", type=Path, default=root / "docs" / "lp_flow_response_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "economic_completion.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "economic_completion.json")
    args = parser.parse_args()

    report = evaluate(
        load_json(args.economic_tests),
        load_json(args.live_status),
        load_json(args.route_proxy),
        load_json(args.route_ab),
        load_json(args.cross_pair_route_proxy),
        load_json(args.depth_proxy),
        load_json(args.cross_pair_depth_proxy),
        load_json(args.oracle_health),
        load_json(args.oracle_lag),
        load_json(args.risk_report),
        load_json(args.drawdown_stop),
        load_json(args.fallback_attribution),
        load_json(args.inventory_report),
        load_json(args.hedge_report),
        load_json(args.hedge_execution_report),
        load_json(args.liquidity_share_report),
        load_json(args.route_break_even),
        load_json(args.adverse_route_away),
        load_json(args.bootstrap_report),
        load_json(args.size_bucket_report),
        load_json(args.staleness_bucket_report),
        load_json(args.base_fee_report),
        load_json(args.target_fee_report),
        load_json(args.capital_path_report),
        load_json(args.policy_monte_carlo_report),
        load_json(args.risk_adjusted_return_report),
        load_json(args.chain_cost_report),
        load_json(args.live_gas_snapshot_report),
        load_json(args.control_plane_cost_report),
        load_json(args.pnl_attribution_report),
        load_json(args.capital_survival_report),
        load_json(args.operator_cost_report),
        load_json(args.alpha_sweep),
        load_json(args.target_return_report),
        load_json(args.route_readiness),
        load_json(args.order_split_report),
        load_json(args.tvl_dilution_report),
        load_json(args.route_cost_proxy),
        load_json(args.sequential_split_report),
        load_json(args.quote_route_readiness),
        load_json(args.quote_headroom_report),
        load_json(args.cross_pair_quote_headroom_report),
        load_json(args.quote_headroom_stability_report),
        load_json(args.quote_headroom_drift_report),
        load_json(args.quote_premium_stress_report),
        load_json(args.quote_event_headroom_report),
        load_json(args.quote_provenance_report),
        load_json(args.quote_elasticity_report),
        load_json(args.insurance_reserve_report),
        load_json(args.premium_allocation_report),
        load_json(args.reserve_delay_report),
        load_json(args.reserve_lifecycle_report),
        load_json(args.reserve_tail_report),
        load_json(args.route_demand_report),
        markout_sensitivity_report=load_json(args.markout_sensitivity_report),
        pilot_deployability_report=load_json(args.pilot_deployability_report),
        range_width_deployability_report=load_json(args.range_width_deployability_report),
        position_shadow_report=load_json(args.position_shadow_report),
        small_capital_decision_report=load_json(args.small_capital_decision_report),
        real_position_report=load_json(args.real_position_report),
        real_position_portfolio_report=load_json(args.real_position_portfolio_report),
        headline_uncertainty_report=load_json(args.headline_uncertainty_report),
        lp_flow_response_report=load_json(args.lp_flow_response_report),
        live_convergence_report=load_json(args.live_convergence_report),
        live_maturity_report=load_json(args.live_maturity_report),
        live_power_report=load_json(args.live_power_report),
        premium_utilization_report=load_json(args.premium_utilization_report),
        charge_attribution_report=load_json(args.charge_attribution_report),
        route_share_stability_report=load_json(args.route_share_stability_report),
        route_away_placebo_ab_report=load_json(args.route_away_placebo_ab_report),
        route_ab_power_report=load_json(args.route_ab_power_report),
        route_ab_sizing_report=load_json(args.route_ab_sizing_report),
        guard_depeg_report=load_json(args.guard_depeg_report),
        stable_opportunity_report=load_json(args.stable_opportunity_report),
        market_regime_report=load_json(args.market_regime_report),
        signal_quality_stress_report=load_json(args.signal_quality_stress_report),
        signal_margin_report=load_json(args.signal_margin_report),
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"economic gates={'complete' if report.complete else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report.complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
