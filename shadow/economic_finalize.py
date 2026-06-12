from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

from . import constants as C
from .adverse_route_away_report import compute as compute_adverse_route_away_report
from .adverse_route_away_report import write_outputs as write_adverse_route_away_outputs
from .alpha_sweep import compute as compute_alpha_sweep
from .alpha_sweep import write_outputs as write_alpha_sweep_outputs
from .base_fee_report import compute as compute_base_fee_report
from .base_fee_report import write_outputs as write_base_fee_outputs
from .bootstrap_report import compute as compute_bootstrap_report
from .bootstrap_report import write_outputs as write_bootstrap_outputs
from .capital_path_report import compute as compute_capital_path_report
from .capital_path_report import write_outputs as write_capital_path_outputs
from .capital_survival_report import compute as compute_capital_survival_report
from .capital_survival_report import write_outputs as write_capital_survival_outputs
from .chain_cost_report import compute as compute_chain_cost_report
from .chain_cost_report import write_outputs as write_chain_cost_outputs
from .charge_attribution_report import compute as compute_charge_attribution_report
from .charge_attribution_report import write_outputs as write_charge_attribution_outputs
from .control_plane_cost_report import compute as compute_control_plane_cost_report
from .control_plane_cost_report import write_outputs as write_control_plane_cost_outputs
from .cross_pair_live_report import PairSpec as CrossPairLiveSpec
from .cross_pair_live_report import compute as compute_cross_pair_live_report
from .cross_pair_live_report import write_outputs as write_cross_pair_live_outputs
from .cross_pair_live_economics_report import PairSpec as CrossPairLiveEconomicsSpec
from .cross_pair_live_economics_report import compute as compute_cross_pair_live_economics_report
from .cross_pair_live_economics_report import write_outputs as write_cross_pair_live_economics_outputs
from .db import connect
from .drawdown_stop_report import compute as compute_drawdown_stop_report
from .drawdown_stop_report import write_outputs as write_drawdown_stop_outputs
from .economic_gate import evaluate as evaluate_gate
from .economic_gate import load_json, write_outputs as write_gate_outputs
from .economic_suite import write_outputs as write_suite_outputs
from .evidence_ledger import write_output as write_evidence_output
from .fallback_attribution import compute as compute_fallback_attribution
from .fallback_attribution import write_outputs as write_fallback_attribution_outputs
from .guard_depeg_report import compute as compute_guard_depeg_report
from .guard_depeg_report import write_outputs as write_guard_depeg_outputs
from .stable_opportunity_report import compute as compute_stable_opportunity_report
from .stable_opportunity_report import write_outputs as write_stable_opportunity_outputs
from .hedge_execution_report import compute as compute_hedge_execution_report
from .hedge_execution_report import write_outputs as write_hedge_execution_outputs
from .hedge_report import compute as compute_hedge_report
from .hedge_report import write_outputs as write_hedge_outputs
from .headline_uncertainty_report import compute as compute_headline_uncertainty_report
from .headline_uncertainty_report import write_outputs as write_headline_uncertainty_outputs
from .insurance_reserve_report import compute as compute_insurance_reserve_report
from .insurance_reserve_report import write_outputs as write_insurance_reserve_outputs
from .inventory_report import compute as compute_inventory_report
from .inventory_report import write_outputs as write_inventory_outputs
from .live_gas_snapshot_report import compute as compute_live_gas_snapshot_report
from .live_gas_snapshot_report import write_outputs as write_live_gas_snapshot_outputs
from .live_status import compute_status, write_outputs as write_status_outputs
from .live_convergence_report import compute as compute_live_convergence_report
from .live_convergence_report import write_outputs as write_live_convergence_outputs
from .live_maturity_report import compute as compute_live_maturity_report
from .live_maturity_report import write_outputs as write_live_maturity_outputs
from .live_power_report import compute as compute_live_power_report
from .live_power_report import write_outputs as write_live_power_outputs
from .live_fee_tier_report import FeeTierSpec as LiveFeeTierSpec
from .live_fee_tier_report import compute as compute_live_fee_tier_report
from .live_fee_tier_report import write_outputs as write_live_fee_tier_outputs
from .live_soak_report import PairSpec as LiveSoakSpec
from .live_soak_report import compute as compute_live_soak_report
from .live_soak_report import write_outputs as write_live_soak_outputs
from .liquidity_share_report import compute as compute_liquidity_share_report
from .liquidity_share_report import write_outputs as write_liquidity_share_outputs
from .lp_flow_response_report import compute as compute_lp_flow_response_report
from .lp_flow_response_report import write_outputs as write_lp_flow_response_outputs
from .markout_sensitivity_report import compute as compute_markout_sensitivity_report
from .markout_sensitivity_report import write_outputs as write_markout_sensitivity_outputs
from .market_regime_report import compute as compute_market_regime_report
from .market_regime_report import write_outputs as write_market_regime_outputs
from .oracle_health import compute as compute_oracle_health
from .oracle_health import write_outputs as write_oracle_health_outputs
from .oracle_lag_report import compute as compute_oracle_lag_report
from .oracle_lag_report import write_outputs as write_oracle_lag_outputs
from .operator_cost_report import compute as compute_operator_cost_report
from .operator_cost_report import write_outputs as write_operator_cost_outputs
from .pilot_deployability_report import compute as compute_pilot_deployability_report
from .pilot_deployability_report import write_outputs as write_pilot_deployability_outputs
from .order_split_report import compute as compute_order_split_report
from .order_split_report import write_outputs as write_order_split_outputs
from .pnl_attribution_report import compute as compute_pnl_attribution_report
from .pnl_attribution_report import write_outputs as write_pnl_attribution_outputs
from .policy_monte_carlo_report import compute as compute_policy_monte_carlo_report
from .policy_monte_carlo_report import write_outputs as write_policy_monte_carlo_outputs
from .position_shadow_report import compute as compute_position_shadow_report
from .position_shadow_report import write_outputs as write_position_shadow_outputs
from .premium_allocation_report import compute as compute_premium_allocation_report
from .premium_allocation_report import write_outputs as write_premium_allocation_outputs
from .premium_utilization_report import compute as compute_premium_utilization_report
from .premium_utilization_report import write_outputs as write_premium_utilization_outputs
from .quote_route_readiness import compute as compute_quote_route_readiness
from .quote_route_readiness import write_outputs as write_quote_route_readiness_outputs
from .quote_headroom_report import compute as compute_quote_headroom_report
from .quote_headroom_report import write_outputs as write_quote_headroom_outputs
from .quote_headroom_stability_report import default_specs as quote_stability_default_specs
from .quote_headroom_stability_report import compute as compute_quote_headroom_stability
from .quote_headroom_stability_report import write_outputs as write_quote_headroom_stability_outputs
from .quote_headroom_drift_report import compute as compute_quote_headroom_drift_report
from .quote_headroom_drift_report import write_outputs as write_quote_headroom_drift_outputs
from .quote_event_headroom_report import compute as compute_quote_event_headroom_report
from .quote_event_headroom_report import write_outputs as write_quote_event_headroom_outputs
from .quote_provenance_report import compute as compute_quote_provenance_report
from .quote_provenance_report import write_outputs as write_quote_provenance_outputs
from .quote_elasticity_report import compute as compute_quote_elasticity_report
from .quote_elasticity_report import write_outputs as write_quote_elasticity_outputs
from .quote_premium_stress_report import compute as compute_quote_premium_stress_report
from .quote_premium_stress_report import write_outputs as write_quote_premium_stress_outputs
from .range_width_deployability_report import compute as compute_range_width_deployability_report
from .range_width_deployability_report import write_outputs as write_range_width_deployability_outputs
from .real_position_report import compute as compute_real_position_report
from .real_position_report import write_outputs as write_real_position_outputs
from .real_position_report import write_template as write_real_position_template
from .real_position_portfolio_report import compute as compute_real_position_portfolio_report
from .real_position_portfolio_report import write_outputs as write_real_position_portfolio_outputs
from .real_position_portfolio_report import write_template as write_real_position_portfolio_template
from .report import emit_reports
from .reserve_delay_report import compute as compute_reserve_delay_report
from .reserve_delay_report import write_outputs as write_reserve_delay_outputs
from .reserve_lifecycle_report import compute as compute_reserve_lifecycle_report
from .reserve_lifecycle_report import write_outputs as write_reserve_lifecycle_outputs
from .reserve_tail_report import compute as compute_reserve_tail_report
from .reserve_tail_report import write_outputs as write_reserve_tail_outputs
from .risk_report import compute as compute_risk_report
from .risk_report import write_outputs as write_risk_outputs
from .risk_adjusted_return_report import compute as compute_risk_adjusted_return_report
from .risk_adjusted_return_report import write_outputs as write_risk_adjusted_return_outputs
from .route_demand_report import compute as compute_route_demand_report
from .route_demand_report import write_outputs as write_route_demand_outputs
from .route_ab_power_report import compute as compute_route_ab_power_report
from .route_ab_power_report import write_outputs as write_route_ab_power_outputs
from .route_ab_sizing_report import compute as compute_route_ab_sizing_report
from .route_ab_sizing_report import write_outputs as write_route_ab_sizing_outputs
from .route_share_stability_report import compute as compute_route_share_stability_report
from .route_share_stability_report import write_outputs as write_route_share_stability_outputs
from .route_away_break_even import compute as compute_route_break_even
from .route_away_break_even import write_outputs as write_route_break_even_outputs
from .route_away_collector_smoke import compute as compute_route_collector_smoke
from .route_away_collector_smoke import write_outputs as write_route_collector_smoke_outputs
from .route_away_readiness import compute as compute_route_readiness
from .route_away_readiness import write_outputs as write_route_readiness_outputs
from .route_away_placebo_ab_report import compute as compute_route_away_placebo_ab_report
from .route_away_placebo_ab_report import write_outputs as write_route_away_placebo_ab_outputs
from .route_away_rpc_preflight import compute_static as compute_route_rpc_preflight
from .route_away_rpc_preflight import write_outputs as write_route_rpc_preflight_outputs
from .route_away_window_plan import compute as compute_route_window_plan
from .route_away_window_plan import write_outputs as write_route_window_plan_outputs
from .route_cost_proxy import compute as compute_route_cost_proxy
from .route_cost_proxy import write_outputs as write_route_cost_outputs
from .sequential_split_report import compute as compute_sequential_split_report
from .sequential_split_report import write_outputs as write_sequential_split_outputs
from .signal_margin_report import compute as compute_signal_margin_report
from .signal_margin_report import write_outputs as write_signal_margin_outputs
from .signal_quality_stress_report import compute as compute_signal_quality_stress_report
from .signal_quality_stress_report import write_outputs as write_signal_quality_stress_outputs
from .size_bucket_report import compute as compute_size_bucket_report
from .size_bucket_report import write_outputs as write_size_bucket_outputs
from .small_capital_decision_report import compute as compute_small_capital_decision_report
from .small_capital_decision_report import write_outputs as write_small_capital_decision_outputs
from .staleness_bucket_report import compute as compute_staleness_bucket_report
from .staleness_bucket_report import write_outputs as write_staleness_bucket_outputs
from .target_fee_report import compute as compute_target_fee_report
from .target_fee_report import write_outputs as write_target_fee_outputs
from .target_return_report import compute as compute_target_return_report
from .target_return_report import write_outputs as write_target_return_outputs
from .truth import process_delayed_truth
from .tvl_dilution_report import compute as compute_tvl_dilution_report
from .tvl_dilution_report import write_outputs as write_tvl_dilution_outputs


@dataclass(frozen=True)
class FinalizePaths:
    database: Path
    reports: Path
    economic_tests_md: Path
    economic_tests_json: Path
    live_status_md: Path
    live_status_json: Path
    live_convergence_md: Path
    live_convergence_json: Path
    live_maturity_md: Path
    live_maturity_json: Path
    live_power_md: Path
    live_power_json: Path
    cross_pair_live_database: Path
    cross_pair_live_md: Path
    cross_pair_live_json: Path
    live_soak_md: Path
    live_soak_json: Path
    cross_pair_live_economics_md: Path
    cross_pair_live_economics_json: Path
    live_fee_tier_md: Path
    live_fee_tier_json: Path
    live_fee_tier_one_bps_glob: str
    live_fee_tier_thirty_bps_glob: str
    route_proxy_json: Path
    cross_pair_route_proxy_json: Path
    route_share_stability_md: Path
    route_share_stability_json: Path
    route_away_placebo_ab_md: Path
    route_away_placebo_ab_json: Path
    route_ab_power_md: Path
    route_ab_power_json: Path
    route_ab_sizing_md: Path
    route_ab_sizing_json: Path
    route_baseline_probe_json: Path
    guard_depeg_md: Path
    guard_depeg_json: Path
    stable_opportunity_md: Path
    stable_opportunity_json: Path
    depth_proxy_json: Path
    cross_pair_depth_proxy_json: Path
    oracle_health_md: Path
    oracle_health_json: Path
    oracle_lag_md: Path
    oracle_lag_json: Path
    risk_report_md: Path
    risk_report_json: Path
    drawdown_stop_md: Path
    drawdown_stop_json: Path
    fallback_attribution_md: Path
    fallback_attribution_json: Path
    inventory_report_md: Path
    inventory_report_json: Path
    hedge_report_md: Path
    hedge_report_json: Path
    hedge_execution_md: Path
    hedge_execution_json: Path
    liquidity_share_report_md: Path
    liquidity_share_report_json: Path
    position_shadow_report_md: Path
    position_shadow_report_json: Path
    route_break_even_md: Path
    route_break_even_json: Path
    adverse_route_away_md: Path
    adverse_route_away_json: Path
    route_collector_smoke_md: Path
    route_collector_smoke_json: Path
    route_window_plan_md: Path
    route_window_plan_json: Path
    route_rpc_preflight_md: Path
    route_rpc_preflight_json: Path
    route_readiness_md: Path
    route_readiness_json: Path
    route_cost_md: Path
    route_cost_json: Path
    quote_route_readiness_md: Path
    quote_route_readiness_json: Path
    quote_headroom_md: Path
    quote_headroom_json: Path
    cross_pair_quote_headroom_md: Path
    cross_pair_quote_headroom_json: Path
    quote_headroom_stability_md: Path
    quote_headroom_stability_json: Path
    quote_headroom_drift_md: Path
    quote_headroom_drift_json: Path
    quote_premium_stress_md: Path
    quote_premium_stress_json: Path
    quote_event_headroom_md: Path
    quote_event_headroom_json: Path
    quote_provenance_md: Path
    quote_provenance_json: Path
    quote_elasticity_md: Path
    quote_elasticity_json: Path
    insurance_reserve_md: Path
    insurance_reserve_json: Path
    premium_allocation_md: Path
    premium_allocation_json: Path
    premium_utilization_md: Path
    premium_utilization_json: Path
    charge_attribution_md: Path
    charge_attribution_json: Path
    reserve_delay_md: Path
    reserve_delay_json: Path
    reserve_lifecycle_md: Path
    reserve_lifecycle_json: Path
    reserve_tail_md: Path
    reserve_tail_json: Path
    bootstrap_report_md: Path
    bootstrap_report_json: Path
    headline_uncertainty_md: Path
    headline_uncertainty_json: Path
    size_bucket_report_md: Path
    size_bucket_report_json: Path
    staleness_bucket_report_md: Path
    staleness_bucket_report_json: Path
    market_regime_report_md: Path
    market_regime_report_json: Path
    signal_quality_stress_md: Path
    signal_quality_stress_json: Path
    signal_margin_md: Path
    signal_margin_json: Path
    base_fee_report_md: Path
    base_fee_report_json: Path
    markout_sensitivity_md: Path
    markout_sensitivity_json: Path
    target_fee_report_md: Path
    target_fee_report_json: Path
    capital_path_report_md: Path
    capital_path_report_json: Path
    policy_monte_carlo_md: Path
    policy_monte_carlo_json: Path
    risk_adjusted_return_md: Path
    risk_adjusted_return_json: Path
    chain_cost_md: Path
    chain_cost_json: Path
    live_gas_snapshot_md: Path
    live_gas_snapshot_json: Path
    control_plane_cost_md: Path
    control_plane_cost_json: Path
    pnl_attribution_md: Path
    pnl_attribution_json: Path
    capital_survival_md: Path
    capital_survival_json: Path
    operator_cost_md: Path
    operator_cost_json: Path
    pilot_deployability_md: Path
    pilot_deployability_json: Path
    range_width_deployability_md: Path
    range_width_deployability_json: Path
    alpha_sweep_md: Path
    alpha_sweep_json: Path
    target_return_md: Path
    target_return_json: Path
    small_capital_decision_md: Path
    small_capital_decision_json: Path
    real_position_md: Path
    real_position_json: Path
    real_position_input_json: Path
    real_position_template_json: Path
    real_position_portfolio_md: Path
    real_position_portfolio_json: Path
    real_position_portfolio_input_json: Path
    real_position_portfolio_template_json: Path
    route_ab_json: Path
    route_demand_md: Path
    route_demand_json: Path
    order_split_md: Path
    order_split_json: Path
    sequential_split_md: Path
    sequential_split_json: Path
    tvl_dilution_md: Path
    tvl_dilution_json: Path
    lp_flow_response_md: Path
    lp_flow_response_json: Path
    evidence_md: Path
    completion_md: Path
    completion_json: Path


def finalize_once(root: Path, paths: FinalizePaths, min_hours: float, min_truth_coverage: float, min_swaps: int) -> bool:
    conn = connect(paths.database)
    try:
        _backfill_truth(conn)
        emit_reports(conn, paths.reports)
    finally:
        conn.close()

    write_suite_outputs(root, paths.economic_tests_md, paths.economic_tests_json, paths.database)
    status = compute_status(paths.database, min_hours, min_truth_coverage, min_swaps)
    write_status_outputs(status, paths.live_status_md, paths.live_status_json)
    live_convergence_report = compute_live_convergence_report(paths.database)
    write_live_convergence_outputs(
        live_convergence_report,
        paths.live_convergence_md,
        paths.live_convergence_json,
    )
    live_maturity_report = compute_live_maturity_report(paths.database)
    write_live_maturity_outputs(
        live_maturity_report,
        paths.live_maturity_md,
        paths.live_maturity_json,
    )
    live_power_report = compute_live_power_report(paths.database)
    write_live_power_outputs(
        live_power_report,
        paths.live_power_md,
        paths.live_power_json,
    )
    cross_pair_live_report = compute_cross_pair_live_report(
        [
            CrossPairLiveSpec("primary", "WETH/USDC", paths.database),
            CrossPairLiveSpec("cross-pair", "WETH/USDT", paths.cross_pair_live_database),
        ],
        min_hours=min_hours,
        min_truth_coverage=min_truth_coverage,
        min_swaps=min_swaps,
    )
    write_cross_pair_live_outputs(
        cross_pair_live_report,
        paths.cross_pair_live_md,
        paths.cross_pair_live_json,
    )
    live_soak_report = compute_live_soak_report(
        [
            LiveSoakSpec("primary", "WETH/USDC", paths.database),
            LiveSoakSpec("cross-pair", "WETH/USDT", paths.cross_pair_live_database),
        ],
        min_truth_coverage=min_truth_coverage,
        min_swaps=min_swaps,
    )
    write_live_soak_outputs(
        live_soak_report,
        paths.live_soak_md,
        paths.live_soak_json,
    )
    cross_pair_live_economics_report = compute_cross_pair_live_economics_report(
        [
            CrossPairLiveEconomicsSpec("primary", "WETH/USDC", paths.database),
            CrossPairLiveEconomicsSpec("cross-pair", "WETH/USDT", paths.cross_pair_live_database),
        ]
    )
    write_cross_pair_live_economics_outputs(
        cross_pair_live_economics_report,
        paths.cross_pair_live_economics_md,
        paths.cross_pair_live_economics_json,
    )
    live_fee_tier_report = compute_live_fee_tier_report(
        [
            LiveFeeTierSpec("primary", "WETH/USDC", 500, database=paths.database),
            LiveFeeTierSpec("same-pair 1bps", "WETH/USDC", 100, database_glob=paths.live_fee_tier_one_bps_glob),
            LiveFeeTierSpec("same-pair 30bps", "WETH/USDC", 3000, database_glob=paths.live_fee_tier_thirty_bps_glob),
        ]
    )
    write_live_fee_tier_outputs(
        live_fee_tier_report,
        paths.live_fee_tier_md,
        paths.live_fee_tier_json,
    )
    oracle_health_report = compute_oracle_health(paths.database)
    write_oracle_health_outputs(oracle_health_report, paths.oracle_health_md, paths.oracle_health_json)
    oracle_lag_report = compute_oracle_lag_report(paths.database)
    write_oracle_lag_outputs(oracle_lag_report, paths.oracle_lag_md, paths.oracle_lag_json)
    risk_report = compute_risk_report(root, paths.database)
    write_risk_outputs(risk_report, paths.risk_report_md, paths.risk_report_json)
    drawdown_stop_report = compute_drawdown_stop_report(root, paths.database)
    write_drawdown_stop_outputs(drawdown_stop_report, paths.drawdown_stop_md, paths.drawdown_stop_json)
    fallback_attribution_report = compute_fallback_attribution(paths.database)
    write_fallback_attribution_outputs(
        fallback_attribution_report,
        paths.fallback_attribution_md,
        paths.fallback_attribution_json,
    )
    inventory_report = compute_inventory_report(root, database=paths.database)
    write_inventory_outputs(inventory_report, paths.inventory_report_md, paths.inventory_report_json)
    hedge_report = compute_hedge_report(root)
    write_hedge_outputs(hedge_report, paths.hedge_report_md, paths.hedge_report_json)
    hedge_execution_report = compute_hedge_execution_report(root)
    write_hedge_execution_outputs(hedge_execution_report, paths.hedge_execution_md, paths.hedge_execution_json)
    liquidity_share_report = compute_liquidity_share_report(
        root,
        paths.economic_tests_json,
        paths.live_status_json,
        paths.depth_proxy_json,
        paths.cross_pair_depth_proxy_json,
    )
    write_liquidity_share_outputs(
        liquidity_share_report,
        paths.liquidity_share_report_md,
        paths.liquidity_share_report_json,
    )
    position_shadow_report = compute_position_shadow_report(
        paths.liquidity_share_report_json,
        paths.inventory_report_json,
    )
    write_position_shadow_outputs(
        position_shadow_report,
        paths.position_shadow_report_md,
        paths.position_shadow_report_json,
    )
    route_break_even_report = compute_route_break_even(paths.economic_tests_json)
    write_route_break_even_outputs(route_break_even_report, paths.route_break_even_md, paths.route_break_even_json)
    adverse_route_away_report = compute_adverse_route_away_report(root, paths.database)
    write_adverse_route_away_outputs(
        adverse_route_away_report,
        paths.adverse_route_away_md,
        paths.adverse_route_away_json,
    )
    route_share_stability_report = compute_route_share_stability_report(
        [paths.route_proxy_json, paths.cross_pair_route_proxy_json]
    )
    write_route_share_stability_outputs(
        route_share_stability_report,
        paths.route_share_stability_md,
        paths.route_share_stability_json,
    )
    route_away_placebo_ab_report = compute_route_away_placebo_ab_report(
        [paths.route_proxy_json, paths.cross_pair_route_proxy_json]
    )
    write_route_away_placebo_ab_outputs(
        route_away_placebo_ab_report,
        paths.route_away_placebo_ab_md,
        paths.route_away_placebo_ab_json,
    )
    route_ab_power_report = compute_route_ab_power_report(paths.route_share_stability_json, paths.route_break_even_json)
    write_route_ab_power_outputs(
        route_ab_power_report,
        paths.route_ab_power_md,
        paths.route_ab_power_json,
    )
    route_ab_sizing_report = compute_route_ab_sizing_report(
        paths.route_ab_power_json,
        [paths.route_proxy_json, paths.cross_pair_route_proxy_json],
    )
    write_route_ab_sizing_outputs(
        route_ab_sizing_report,
        paths.route_ab_sizing_md,
        paths.route_ab_sizing_json,
    )
    guard_depeg_report = compute_guard_depeg_report(root)
    write_guard_depeg_outputs(guard_depeg_report, paths.guard_depeg_md, paths.guard_depeg_json)
    stable_opportunity_report = compute_stable_opportunity_report(root)
    write_stable_opportunity_outputs(
        stable_opportunity_report,
        paths.stable_opportunity_md,
        paths.stable_opportunity_json,
    )
    route_collector_smoke_report = compute_route_collector_smoke(root)
    write_route_collector_smoke_outputs(
        route_collector_smoke_report,
        paths.route_collector_smoke_md,
        paths.route_collector_smoke_json,
    )
    route_window_plan_report = compute_route_window_plan(
        paths.route_ab_sizing_json,
        [paths.route_proxy_json, paths.cross_pair_route_proxy_json],
    )
    write_route_window_plan_outputs(
        route_window_plan_report,
        paths.route_window_plan_md,
        paths.route_window_plan_json,
    )
    route_rpc_preflight_report = compute_route_rpc_preflight(root)
    write_route_rpc_preflight_outputs(
        route_rpc_preflight_report,
        paths.route_rpc_preflight_md,
        paths.route_rpc_preflight_json,
    )
    route_readiness_report = compute_route_readiness(
        root,
        route_ab_path=paths.route_ab_json,
        route_sizing_path=paths.route_ab_sizing_json,
    )
    write_route_readiness_outputs(route_readiness_report, paths.route_readiness_md, paths.route_readiness_json)
    route_cost_report = compute_route_cost_proxy(paths.depth_proxy_json, paths.cross_pair_depth_proxy_json)
    write_route_cost_outputs(route_cost_report, paths.route_cost_md, paths.route_cost_json)
    quote_route_readiness_report = compute_quote_route_readiness(root)
    write_quote_route_readiness_outputs(
        quote_route_readiness_report,
        paths.quote_route_readiness_md,
        paths.quote_route_readiness_json,
    )
    quote_headroom_report = compute_quote_headroom_report(root / "docs" / "quote_route_quotes.json")
    write_quote_headroom_outputs(quote_headroom_report, paths.quote_headroom_md, paths.quote_headroom_json)
    cross_pair_quote_headroom_report = compute_quote_headroom_report(root / "docs" / "quote_route_quotes_weth_usdt.json")
    write_quote_headroom_outputs(
        cross_pair_quote_headroom_report,
        paths.cross_pair_quote_headroom_md,
        paths.cross_pair_quote_headroom_json,
    )
    quote_headroom_stability_report = compute_quote_headroom_stability(quote_stability_default_specs(root))
    write_quote_headroom_stability_outputs(
        quote_headroom_stability_report,
        paths.quote_headroom_stability_md,
        paths.quote_headroom_stability_json,
    )
    quote_headroom_drift_report = compute_quote_headroom_drift_report(root)
    write_quote_headroom_drift_outputs(
        quote_headroom_drift_report,
        paths.quote_headroom_drift_md,
        paths.quote_headroom_drift_json,
    )
    quote_premium_stress_report = compute_quote_premium_stress_report(root, paths.database, paths.quote_headroom_json)
    write_quote_premium_stress_outputs(
        quote_premium_stress_report,
        paths.quote_premium_stress_md,
        paths.quote_premium_stress_json,
    )
    quote_event_headroom_report = compute_quote_event_headroom_report(root, paths.database, paths.quote_headroom_json)
    write_quote_event_headroom_outputs(
        quote_event_headroom_report,
        paths.quote_event_headroom_md,
        paths.quote_event_headroom_json,
    )
    quote_provenance_report = compute_quote_provenance_report(root)
    write_quote_provenance_outputs(
        quote_provenance_report,
        paths.quote_provenance_md,
        paths.quote_provenance_json,
    )
    quote_elasticity_report = compute_quote_elasticity_report(root, paths.database, paths.quote_headroom_json)
    write_quote_elasticity_outputs(
        quote_elasticity_report,
        paths.quote_elasticity_md,
        paths.quote_elasticity_json,
    )
    insurance_reserve_report = compute_insurance_reserve_report(root, paths.database)
    write_insurance_reserve_outputs(
        insurance_reserve_report,
        paths.insurance_reserve_md,
        paths.insurance_reserve_json,
    )
    premium_allocation_report = compute_premium_allocation_report(root, paths.database)
    write_premium_allocation_outputs(
        premium_allocation_report,
        paths.premium_allocation_md,
        paths.premium_allocation_json,
    )
    premium_utilization_report = compute_premium_utilization_report(root, paths.database)
    write_premium_utilization_outputs(
        premium_utilization_report,
        paths.premium_utilization_md,
        paths.premium_utilization_json,
    )
    charge_attribution_report = compute_charge_attribution_report(root, paths.database)
    write_charge_attribution_outputs(
        charge_attribution_report,
        paths.charge_attribution_md,
        paths.charge_attribution_json,
    )
    reserve_delay_report = compute_reserve_delay_report(root, paths.database)
    write_reserve_delay_outputs(
        reserve_delay_report,
        paths.reserve_delay_md,
        paths.reserve_delay_json,
    )
    reserve_lifecycle_report = compute_reserve_lifecycle_report(root, paths.database)
    write_reserve_lifecycle_outputs(
        reserve_lifecycle_report,
        paths.reserve_lifecycle_md,
        paths.reserve_lifecycle_json,
    )
    reserve_tail_report = compute_reserve_tail_report(root, paths.database)
    write_reserve_tail_outputs(reserve_tail_report, paths.reserve_tail_md, paths.reserve_tail_json)
    bootstrap_report = compute_bootstrap_report(root, paths.database)
    write_bootstrap_outputs(bootstrap_report, paths.bootstrap_report_md, paths.bootstrap_report_json)
    headline_uncertainty_report = compute_headline_uncertainty_report(root, paths.database)
    write_headline_uncertainty_outputs(
        headline_uncertainty_report,
        paths.headline_uncertainty_md,
        paths.headline_uncertainty_json,
    )
    size_bucket_report = compute_size_bucket_report(root, paths.database)
    write_size_bucket_outputs(size_bucket_report, paths.size_bucket_report_md, paths.size_bucket_report_json)
    staleness_bucket_report = compute_staleness_bucket_report(paths.database)
    write_staleness_bucket_outputs(
        staleness_bucket_report,
        paths.staleness_bucket_report_md,
        paths.staleness_bucket_report_json,
    )
    market_regime_report = compute_market_regime_report(root, paths.database)
    write_market_regime_outputs(
        market_regime_report,
        paths.market_regime_report_md,
        paths.market_regime_report_json,
    )
    signal_quality_stress_report = compute_signal_quality_stress_report(paths.economic_tests_json)
    write_signal_quality_stress_outputs(
        signal_quality_stress_report,
        paths.signal_quality_stress_md,
        paths.signal_quality_stress_json,
    )
    signal_margin_report = compute_signal_margin_report(paths.economic_tests_json)
    write_signal_margin_outputs(
        signal_margin_report,
        paths.signal_margin_md,
        paths.signal_margin_json,
    )
    base_fee_report = compute_base_fee_report(paths.economic_tests_json)
    write_base_fee_outputs(base_fee_report, paths.base_fee_report_md, paths.base_fee_report_json)
    markout_sensitivity_report = compute_markout_sensitivity_report(paths.economic_tests_json)
    write_markout_sensitivity_outputs(
        markout_sensitivity_report,
        paths.markout_sensitivity_md,
        paths.markout_sensitivity_json,
    )
    target_fee_report = compute_target_fee_report(paths.base_fee_report_json, paths.route_proxy_json)
    write_target_fee_outputs(target_fee_report, paths.target_fee_report_md, paths.target_fee_report_json)
    capital_path_report = compute_capital_path_report(paths.economic_tests_json)
    write_capital_path_outputs(capital_path_report, paths.capital_path_report_md, paths.capital_path_report_json)
    policy_monte_carlo_report = compute_policy_monte_carlo_report(paths.economic_tests_json)
    write_policy_monte_carlo_outputs(
        policy_monte_carlo_report,
        paths.policy_monte_carlo_md,
        paths.policy_monte_carlo_json,
    )
    risk_adjusted_return_report = compute_risk_adjusted_return_report(paths.economic_tests_json)
    write_risk_adjusted_return_outputs(
        risk_adjusted_return_report,
        paths.risk_adjusted_return_md,
        paths.risk_adjusted_return_json,
    )
    chain_cost_report = compute_chain_cost_report(paths.economic_tests_json)
    write_chain_cost_outputs(chain_cost_report, paths.chain_cost_md, paths.chain_cost_json)
    live_gas_snapshot_report = compute_live_gas_snapshot_report(paths.economic_tests_json)
    write_live_gas_snapshot_outputs(
        live_gas_snapshot_report,
        paths.live_gas_snapshot_md,
        paths.live_gas_snapshot_json,
    )
    control_plane_cost_report = compute_control_plane_cost_report(paths.guard_depeg_json, paths.live_gas_snapshot_json)
    write_control_plane_cost_outputs(
        control_plane_cost_report,
        paths.control_plane_cost_md,
        paths.control_plane_cost_json,
    )
    pnl_attribution_report = compute_pnl_attribution_report(paths.economic_tests_json)
    write_pnl_attribution_outputs(
        pnl_attribution_report,
        paths.pnl_attribution_md,
        paths.pnl_attribution_json,
    )
    capital_survival_report = compute_capital_survival_report(paths.pnl_attribution_json)
    write_capital_survival_outputs(
        capital_survival_report,
        paths.capital_survival_md,
        paths.capital_survival_json,
    )
    operator_cost_report = compute_operator_cost_report(paths.pnl_attribution_json)
    write_operator_cost_outputs(
        operator_cost_report,
        paths.operator_cost_md,
        paths.operator_cost_json,
    )
    pilot_deployability_report = compute_pilot_deployability_report(paths.pnl_attribution_json)
    write_pilot_deployability_outputs(
        pilot_deployability_report,
        paths.pilot_deployability_md,
        paths.pilot_deployability_json,
    )
    range_width_deployability_report = compute_range_width_deployability_report(
        root,
        paths.economic_tests_json,
        paths.live_status_json,
    )
    write_range_width_deployability_outputs(
        range_width_deployability_report,
        paths.range_width_deployability_md,
        paths.range_width_deployability_json,
    )
    alpha_sweep = compute_alpha_sweep(root)
    write_alpha_sweep_outputs(alpha_sweep, paths.alpha_sweep_md, paths.alpha_sweep_json)
    target_return_report = compute_target_return_report(root, paths.economic_tests_json, paths.live_status_json)
    write_target_return_outputs(target_return_report, paths.target_return_md, paths.target_return_json)
    small_capital_decision_report = compute_small_capital_decision_report(
        paths.pilot_deployability_json,
        paths.position_shadow_report_json,
        paths.target_return_json,
        paths.live_status_json,
    )
    write_small_capital_decision_outputs(
        small_capital_decision_report,
        paths.small_capital_decision_md,
        paths.small_capital_decision_json,
    )
    write_real_position_template(paths.real_position_template_json)
    real_position_report = compute_real_position_report(
        root,
        paths.real_position_input_json,
        paths.real_position_template_json,
    )
    write_real_position_outputs(
        real_position_report,
        paths.real_position_md,
        paths.real_position_json,
    )
    seed_payload = load_json(paths.real_position_input_json)
    write_real_position_portfolio_template(paths.real_position_portfolio_template_json, seed_payload or None)
    real_position_portfolio_report = compute_real_position_portfolio_report(
        root,
        paths.real_position_portfolio_input_json,
        paths.real_position_input_json,
        paths.real_position_portfolio_template_json,
    )
    write_real_position_portfolio_outputs(
        real_position_portfolio_report,
        paths.real_position_portfolio_md,
        paths.real_position_portfolio_json,
    )
    route_demand_report = compute_route_demand_report(root, paths.database)
    write_route_demand_outputs(route_demand_report, paths.route_demand_md, paths.route_demand_json)
    order_split_report = compute_order_split_report(root, paths.database)
    write_order_split_outputs(order_split_report, paths.order_split_md, paths.order_split_json)
    sequential_split_report = compute_sequential_split_report(root, paths.database)
    write_sequential_split_outputs(
        sequential_split_report,
        paths.sequential_split_md,
        paths.sequential_split_json,
    )
    tvl_dilution_report = compute_tvl_dilution_report(root, paths.economic_tests_json, paths.live_status_json)
    write_tvl_dilution_outputs(tvl_dilution_report, paths.tvl_dilution_md, paths.tvl_dilution_json)
    lp_flow_response_report = compute_lp_flow_response_report(root, paths.economic_tests_json, paths.live_status_json)
    write_lp_flow_response_outputs(
        lp_flow_response_report,
        paths.lp_flow_response_md,
        paths.lp_flow_response_json,
    )

    live_status = load_json(paths.live_status_json)
    live_convergence = load_json(paths.live_convergence_json)
    live_maturity = load_json(paths.live_maturity_json)
    live_power = load_json(paths.live_power_json)
    cross_pair_live = load_json(paths.cross_pair_live_json)
    live_soak = load_json(paths.live_soak_json)
    cross_pair_live_economics = load_json(paths.cross_pair_live_economics_json)
    live_fee_tier = load_json(paths.live_fee_tier_json)
    route_proxy = load_json(paths.route_proxy_json)
    cross_pair_route_proxy = load_json(paths.cross_pair_route_proxy_json)
    route_share_stability = load_json(paths.route_share_stability_json)
    route_away_placebo_ab = load_json(paths.route_away_placebo_ab_json)
    route_ab_power = load_json(paths.route_ab_power_json)
    route_ab_sizing = load_json(paths.route_ab_sizing_json)
    route_baseline_probe = load_json(paths.route_baseline_probe_json)
    guard_depeg = load_json(paths.guard_depeg_json)
    stable_opportunity = load_json(paths.stable_opportunity_json)
    depth_proxy = load_json(paths.depth_proxy_json)
    cross_pair_depth_proxy = load_json(paths.cross_pair_depth_proxy_json)
    oracle_health = load_json(paths.oracle_health_json)
    oracle_lag = load_json(paths.oracle_lag_json)
    risk_report_json = load_json(paths.risk_report_json)
    drawdown_stop_json = load_json(paths.drawdown_stop_json)
    fallback_attribution = load_json(paths.fallback_attribution_json)
    inventory_report_json = load_json(paths.inventory_report_json)
    hedge_report_json = load_json(paths.hedge_report_json)
    hedge_execution_json = load_json(paths.hedge_execution_json)
    liquidity_share_report_json = load_json(paths.liquidity_share_report_json)
    position_shadow_json = load_json(paths.position_shadow_report_json)
    route_break_even = load_json(paths.route_break_even_json)
    adverse_route_away = load_json(paths.adverse_route_away_json)
    route_readiness = load_json(paths.route_readiness_json)
    route_cost = load_json(paths.route_cost_json)
    quote_route_readiness = load_json(paths.quote_route_readiness_json)
    quote_headroom = load_json(paths.quote_headroom_json)
    cross_pair_quote_headroom = load_json(paths.cross_pair_quote_headroom_json)
    quote_headroom_stability = load_json(paths.quote_headroom_stability_json)
    quote_headroom_drift = load_json(paths.quote_headroom_drift_json)
    quote_premium_stress = load_json(paths.quote_premium_stress_json)
    quote_event_headroom = load_json(paths.quote_event_headroom_json)
    quote_provenance = load_json(paths.quote_provenance_json)
    quote_elasticity = load_json(paths.quote_elasticity_json)
    insurance_reserve = load_json(paths.insurance_reserve_json)
    premium_allocation = load_json(paths.premium_allocation_json)
    premium_utilization = load_json(paths.premium_utilization_json)
    charge_attribution = load_json(paths.charge_attribution_json)
    reserve_delay = load_json(paths.reserve_delay_json)
    reserve_lifecycle = load_json(paths.reserve_lifecycle_json)
    reserve_tail = load_json(paths.reserve_tail_json)
    bootstrap_report_json = load_json(paths.bootstrap_report_json)
    headline_uncertainty_json = load_json(paths.headline_uncertainty_json)
    size_bucket_report_json = load_json(paths.size_bucket_report_json)
    staleness_bucket_report_json = load_json(paths.staleness_bucket_report_json)
    market_regime_report_json = load_json(paths.market_regime_report_json)
    signal_quality_stress_json = load_json(paths.signal_quality_stress_json)
    signal_margin_json = load_json(paths.signal_margin_json)
    base_fee_report_json = load_json(paths.base_fee_report_json)
    markout_sensitivity_json = load_json(paths.markout_sensitivity_json)
    target_fee_report_json = load_json(paths.target_fee_report_json)
    capital_path_report_json = load_json(paths.capital_path_report_json)
    policy_monte_carlo_json = load_json(paths.policy_monte_carlo_json)
    risk_adjusted_return_json = load_json(paths.risk_adjusted_return_json)
    chain_cost_json = load_json(paths.chain_cost_json)
    live_gas_snapshot_json = load_json(paths.live_gas_snapshot_json)
    control_plane_cost_json = load_json(paths.control_plane_cost_json)
    pnl_attribution_json = load_json(paths.pnl_attribution_json)
    capital_survival_json = load_json(paths.capital_survival_json)
    operator_cost_json = load_json(paths.operator_cost_json)
    pilot_deployability_json = load_json(paths.pilot_deployability_json)
    range_width_deployability_json = load_json(paths.range_width_deployability_json)
    alpha_sweep_json = load_json(paths.alpha_sweep_json)
    target_return_json = load_json(paths.target_return_json)
    small_capital_decision_json = load_json(paths.small_capital_decision_json)
    real_position_json = load_json(paths.real_position_json)
    real_position_portfolio_json = load_json(paths.real_position_portfolio_json)
    route_demand_json = load_json(paths.route_demand_json)
    order_split_json = load_json(paths.order_split_json)
    sequential_split_json = load_json(paths.sequential_split_json)
    tvl_dilution_json = load_json(paths.tvl_dilution_json)
    lp_flow_response_json = load_json(paths.lp_flow_response_json)
    route_ab = load_json(paths.route_ab_json)
    write_evidence_output(
        paths.evidence_md,
        live_status,
        route_proxy,
        route_ab,
        cross_pair_route_proxy,
        depth_proxy,
        cross_pair_depth_proxy,
        oracle_health,
        oracle_lag,
        risk_report_json,
        drawdown_stop_json,
        fallback_attribution,
        inventory_report_json,
        hedge_report_json,
        hedge_execution_json,
        liquidity_share_report_json,
        route_break_even,
        adverse_route_away,
        bootstrap_report_json,
        size_bucket_report_json,
        staleness_bucket_report_json,
        base_fee_report_json,
        target_fee_report_json,
        capital_path_report_json,
        policy_monte_carlo_json,
        risk_adjusted_return_json,
        chain_cost_json,
        live_gas_snapshot_json,
        control_plane_cost_json,
        pnl_attribution_json,
        capital_survival_json,
        operator_cost_json,
        alpha_sweep_json,
        target_return_json,
        route_readiness,
        order_split_json,
        tvl_dilution_json,
        route_cost,
        sequential_split_json,
        quote_route_readiness,
        quote_headroom,
        cross_pair_quote_headroom,
        quote_headroom_stability,
        quote_headroom_drift,
        quote_premium_stress,
        quote_event_headroom,
        quote_provenance,
        quote_elasticity,
        insurance_reserve,
        premium_allocation,
        reserve_delay,
        reserve_lifecycle,
        reserve_tail,
        route_demand_json,
        markout_sensitivity_report=markout_sensitivity_json,
        pilot_deployability_report=pilot_deployability_json,
        range_width_deployability_report=range_width_deployability_json,
        position_shadow_report=position_shadow_json,
        small_capital_decision_report=small_capital_decision_json,
        real_position_report=real_position_json,
        real_position_portfolio_report=real_position_portfolio_json,
        headline_uncertainty_report=headline_uncertainty_json,
        lp_flow_response_report=lp_flow_response_json,
        live_convergence_report=live_convergence,
        live_maturity_report=live_maturity,
        live_power_report=live_power,
        cross_pair_live_report=cross_pair_live,
        live_soak_report=live_soak,
        cross_pair_live_economics_report=cross_pair_live_economics,
        live_fee_tier_report=live_fee_tier,
        premium_utilization_report=premium_utilization,
        charge_attribution_report=charge_attribution,
        route_share_stability_report=route_share_stability,
        route_away_placebo_ab_report=route_away_placebo_ab,
        route_ab_power_report=route_ab_power,
        route_ab_sizing_report=route_ab_sizing,
        route_baseline_probe_report=route_baseline_probe,
        guard_depeg_report=guard_depeg,
        stable_opportunity_report=stable_opportunity,
        market_regime_report=market_regime_report_json,
        signal_quality_stress_report=signal_quality_stress_json,
        signal_margin_report=signal_margin_json,
    )

    gate = evaluate_gate(
        load_json(paths.economic_tests_json),
        live_status,
        route_proxy,
        route_ab,
        cross_pair_route_proxy,
        depth_proxy,
        cross_pair_depth_proxy,
        oracle_health,
        oracle_lag,
        risk_report_json,
        drawdown_stop_json,
        fallback_attribution,
        inventory_report_json,
        hedge_report_json,
        hedge_execution_json,
        liquidity_share_report_json,
        route_break_even,
        adverse_route_away,
        bootstrap_report_json,
        size_bucket_report_json,
        staleness_bucket_report_json,
        base_fee_report_json,
        target_fee_report_json,
        capital_path_report_json,
        policy_monte_carlo_json,
        risk_adjusted_return_json,
        chain_cost_json,
        live_gas_snapshot_json,
        control_plane_cost_json,
        pnl_attribution_json,
        capital_survival_json,
        operator_cost_json,
        alpha_sweep_json,
        target_return_json,
        route_readiness,
        order_split_json,
        tvl_dilution_json,
        route_cost,
        sequential_split_json,
        quote_route_readiness,
        quote_headroom,
        cross_pair_quote_headroom,
        quote_headroom_stability,
        quote_headroom_drift,
        quote_premium_stress,
        quote_event_headroom,
        quote_provenance,
        quote_elasticity,
        insurance_reserve,
        premium_allocation,
        reserve_delay,
        reserve_lifecycle,
        reserve_tail,
        route_demand_json,
        markout_sensitivity_report=markout_sensitivity_json,
        pilot_deployability_report=pilot_deployability_json,
        range_width_deployability_report=range_width_deployability_json,
        position_shadow_report=position_shadow_json,
        small_capital_decision_report=small_capital_decision_json,
        real_position_report=real_position_json,
        real_position_portfolio_report=real_position_portfolio_json,
        headline_uncertainty_report=headline_uncertainty_json,
        lp_flow_response_report=lp_flow_response_json,
        live_convergence_report=live_convergence,
        live_maturity_report=live_maturity,
        live_power_report=live_power,
        premium_utilization_report=premium_utilization,
        charge_attribution_report=charge_attribution,
        route_share_stability_report=route_share_stability,
        route_away_placebo_ab_report=route_away_placebo_ab,
        route_ab_power_report=route_ab_power,
        route_ab_sizing_report=route_ab_sizing,
        guard_depeg_report=guard_depeg,
        stable_opportunity_report=stable_opportunity,
        market_regime_report=market_regime_report_json,
        signal_quality_stress_report=signal_quality_stress_json,
        signal_margin_report=signal_margin_json,
    )
    write_gate_outputs(gate, paths.completion_md, paths.completion_json)
    return gate.complete


def _backfill_truth(conn) -> int:
    total = 0
    while True:
        count = process_delayed_truth(conn)
        total += count
        if count == 0:
            return total


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Refresh all PegGuard economic reports and completion gates")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--reports", type=Path, default=root / "docs" / default_tag)
    parser.add_argument("--economic-tests-md", type=Path, default=root / "docs" / default_tag / "economic_tests.md")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-md", type=Path, default=root / "docs" / default_tag / "status.md")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--live-convergence-md", type=Path, default=root / "docs" / "live_convergence_report.md")
    parser.add_argument("--live-convergence-json", type=Path, default=root / "docs" / "live_convergence_report.json")
    parser.add_argument("--live-maturity-md", type=Path, default=root / "docs" / "live_maturity_report.md")
    parser.add_argument("--live-maturity-json", type=Path, default=root / "docs" / "live_maturity_report.json")
    parser.add_argument("--live-power-md", type=Path, default=root / "docs" / "live_power_report.md")
    parser.add_argument("--live-power-json", type=Path, default=root / "docs" / "live_power_report.json")
    parser.add_argument(
        "--cross-pair-live-database",
        type=Path,
        default=root / "shadow" / "live_shadow_weth_usdt_20260607T204521Z.sqlite3",
    )
    parser.add_argument("--cross-pair-live-md", type=Path, default=root / "docs" / "cross_pair_live_report.md")
    parser.add_argument("--cross-pair-live-json", type=Path, default=root / "docs" / "cross_pair_live_report.json")
    parser.add_argument("--live-soak-md", type=Path, default=root / "docs" / "live_soak_report.md")
    parser.add_argument("--live-soak-json", type=Path, default=root / "docs" / "live_soak_report.json")
    parser.add_argument("--cross-pair-live-economics-md", type=Path, default=root / "docs" / "cross_pair_live_economics_report.md")
    parser.add_argument("--cross-pair-live-economics-json", type=Path, default=root / "docs" / "cross_pair_live_economics_report.json")
    parser.add_argument("--live-fee-tier-md", type=Path, default=root / "docs" / "live_fee_tier_report.md")
    parser.add_argument("--live-fee-tier-json", type=Path, default=root / "docs" / "live_fee_tier_report.json")
    parser.add_argument("--live-fee-tier-one-bps-glob", default=str(root / "shadow" / "live_shadow_weth_usdc_1bps_*.sqlite3"))
    parser.add_argument("--live-fee-tier-thirty-bps-glob", default=str(root / "shadow" / "live_shadow_weth_usdc_30bps_*.sqlite3"))
    parser.add_argument("--route-proxy-json", type=Path, default=root / "docs" / "route_away_proxy.json")
    parser.add_argument("--cross-pair-route-proxy-json", type=Path, default=root / "docs" / "route_away_proxy_weth_usdt.json")
    parser.add_argument("--route-share-stability-md", type=Path, default=root / "docs" / "route_share_stability_report.md")
    parser.add_argument("--route-share-stability-json", type=Path, default=root / "docs" / "route_share_stability_report.json")
    parser.add_argument("--route-away-placebo-ab-md", type=Path, default=root / "docs" / "route_away_placebo_ab_report.md")
    parser.add_argument("--route-away-placebo-ab-json", type=Path, default=root / "docs" / "route_away_placebo_ab_report.json")
    parser.add_argument("--route-ab-power-md", type=Path, default=root / "docs" / "route_ab_power_report.md")
    parser.add_argument("--route-ab-power-json", type=Path, default=root / "docs" / "route_ab_power_report.json")
    parser.add_argument("--route-ab-sizing-md", type=Path, default=root / "docs" / "route_ab_sizing_report.md")
    parser.add_argument("--route-ab-sizing-json", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    parser.add_argument("--route-baseline-probe-json", type=Path, default=root / "docs" / "route_away_baseline_probe.json")
    parser.add_argument("--guard-depeg-md", type=Path, default=root / "docs" / "guard_depeg_report.md")
    parser.add_argument("--guard-depeg-json", type=Path, default=root / "docs" / "guard_depeg_report.json")
    parser.add_argument("--stable-opportunity-md", type=Path, default=root / "docs" / "stable_opportunity_report.md")
    parser.add_argument("--stable-opportunity-json", type=Path, default=root / "docs" / "stable_opportunity_report.json")
    parser.add_argument("--depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy.json")
    parser.add_argument("--cross-pair-depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy_weth_usdt.json")
    parser.add_argument("--oracle-health-md", type=Path, default=root / "docs" / "oracle_health.md")
    parser.add_argument("--oracle-health-json", type=Path, default=root / "docs" / "oracle_health.json")
    parser.add_argument("--oracle-lag-md", type=Path, default=root / "docs" / "oracle_lag_report.md")
    parser.add_argument("--oracle-lag-json", type=Path, default=root / "docs" / "oracle_lag_report.json")
    parser.add_argument("--risk-report-md", type=Path, default=root / "docs" / "risk_report.md")
    parser.add_argument("--risk-report-json", type=Path, default=root / "docs" / "risk_report.json")
    parser.add_argument("--drawdown-stop-md", type=Path, default=root / "docs" / "drawdown_stop_report.md")
    parser.add_argument("--drawdown-stop-json", type=Path, default=root / "docs" / "drawdown_stop_report.json")
    parser.add_argument("--fallback-attribution-md", type=Path, default=root / "docs" / "fallback_attribution.md")
    parser.add_argument("--fallback-attribution-json", type=Path, default=root / "docs" / "fallback_attribution.json")
    parser.add_argument("--inventory-report-md", type=Path, default=root / "docs" / "inventory_report.md")
    parser.add_argument("--inventory-report-json", type=Path, default=root / "docs" / "inventory_report.json")
    parser.add_argument("--hedge-report-md", type=Path, default=root / "docs" / "hedge_report.md")
    parser.add_argument("--hedge-report-json", type=Path, default=root / "docs" / "hedge_report.json")
    parser.add_argument("--hedge-execution-md", type=Path, default=root / "docs" / "hedge_execution_report.md")
    parser.add_argument("--hedge-execution-json", type=Path, default=root / "docs" / "hedge_execution_report.json")
    parser.add_argument("--liquidity-share-report-md", type=Path, default=root / "docs" / "liquidity_share_report.md")
    parser.add_argument("--liquidity-share-report-json", type=Path, default=root / "docs" / "liquidity_share_report.json")
    parser.add_argument("--position-shadow-report-md", type=Path, default=root / "docs" / "position_shadow_report.md")
    parser.add_argument("--position-shadow-report-json", type=Path, default=root / "docs" / "position_shadow_report.json")
    parser.add_argument("--route-break-even-md", type=Path, default=root / "docs" / "route_away_break_even.md")
    parser.add_argument("--route-break-even-json", type=Path, default=root / "docs" / "route_away_break_even.json")
    parser.add_argument("--adverse-route-away-md", type=Path, default=root / "docs" / "adverse_route_away_report.md")
    parser.add_argument("--adverse-route-away-json", type=Path, default=root / "docs" / "adverse_route_away_report.json")
    parser.add_argument("--route-collector-smoke-md", type=Path, default=root / "docs" / "route_away_collector_smoke.md")
    parser.add_argument("--route-collector-smoke-json", type=Path, default=root / "docs" / "route_away_collector_smoke.json")
    parser.add_argument("--route-window-plan-md", type=Path, default=root / "docs" / "route_away_window_plan.md")
    parser.add_argument("--route-window-plan-json", type=Path, default=root / "docs" / "route_away_window_plan.json")
    parser.add_argument("--route-rpc-preflight-md", type=Path, default=root / "docs" / "route_away_rpc_preflight.md")
    parser.add_argument("--route-rpc-preflight-json", type=Path, default=root / "docs" / "route_away_rpc_preflight.json")
    parser.add_argument("--route-readiness-md", type=Path, default=root / "docs" / "route_away_readiness.md")
    parser.add_argument("--route-readiness-json", type=Path, default=root / "docs" / "route_away_readiness.json")
    parser.add_argument("--route-cost-md", type=Path, default=root / "docs" / "route_cost_proxy.md")
    parser.add_argument("--route-cost-json", type=Path, default=root / "docs" / "route_cost_proxy.json")
    parser.add_argument("--quote-route-readiness-md", type=Path, default=root / "docs" / "quote_route_readiness.md")
    parser.add_argument("--quote-route-readiness-json", type=Path, default=root / "docs" / "quote_route_readiness.json")
    parser.add_argument("--quote-headroom-md", type=Path, default=root / "docs" / "quote_headroom_report.md")
    parser.add_argument("--quote-headroom-json", type=Path, default=root / "docs" / "quote_headroom_report.json")
    parser.add_argument("--cross-pair-quote-headroom-md", type=Path, default=root / "docs" / "quote_headroom_weth_usdt.md")
    parser.add_argument("--cross-pair-quote-headroom-json", type=Path, default=root / "docs" / "quote_headroom_weth_usdt.json")
    parser.add_argument("--quote-headroom-stability-md", type=Path, default=root / "docs" / "quote_headroom_stability_report.md")
    parser.add_argument("--quote-headroom-stability-json", type=Path, default=root / "docs" / "quote_headroom_stability_report.json")
    parser.add_argument("--quote-headroom-drift-md", type=Path, default=root / "docs" / "quote_headroom_drift_report.md")
    parser.add_argument("--quote-headroom-drift-json", type=Path, default=root / "docs" / "quote_headroom_drift_report.json")
    parser.add_argument("--quote-premium-stress-md", type=Path, default=root / "docs" / "quote_premium_stress.md")
    parser.add_argument("--quote-premium-stress-json", type=Path, default=root / "docs" / "quote_premium_stress.json")
    parser.add_argument("--quote-event-headroom-md", type=Path, default=root / "docs" / "quote_event_headroom_report.md")
    parser.add_argument("--quote-event-headroom-json", type=Path, default=root / "docs" / "quote_event_headroom_report.json")
    parser.add_argument("--quote-provenance-md", type=Path, default=root / "docs" / "quote_provenance_report.md")
    parser.add_argument("--quote-provenance-json", type=Path, default=root / "docs" / "quote_provenance_report.json")
    parser.add_argument("--quote-elasticity-md", type=Path, default=root / "docs" / "quote_elasticity_report.md")
    parser.add_argument("--quote-elasticity-json", type=Path, default=root / "docs" / "quote_elasticity_report.json")
    parser.add_argument("--insurance-reserve-md", type=Path, default=root / "docs" / "insurance_reserve_report.md")
    parser.add_argument("--insurance-reserve-json", type=Path, default=root / "docs" / "insurance_reserve_report.json")
    parser.add_argument("--premium-allocation-md", type=Path, default=root / "docs" / "premium_allocation_report.md")
    parser.add_argument("--premium-allocation-json", type=Path, default=root / "docs" / "premium_allocation_report.json")
    parser.add_argument("--premium-utilization-md", type=Path, default=root / "docs" / "premium_utilization_report.md")
    parser.add_argument("--premium-utilization-json", type=Path, default=root / "docs" / "premium_utilization_report.json")
    parser.add_argument("--charge-attribution-md", type=Path, default=root / "docs" / "charge_attribution_report.md")
    parser.add_argument("--charge-attribution-json", type=Path, default=root / "docs" / "charge_attribution_report.json")
    parser.add_argument("--reserve-delay-md", type=Path, default=root / "docs" / "reserve_delay_report.md")
    parser.add_argument("--reserve-delay-json", type=Path, default=root / "docs" / "reserve_delay_report.json")
    parser.add_argument("--reserve-lifecycle-md", type=Path, default=root / "docs" / "reserve_lifecycle_report.md")
    parser.add_argument("--reserve-lifecycle-json", type=Path, default=root / "docs" / "reserve_lifecycle_report.json")
    parser.add_argument("--reserve-tail-md", type=Path, default=root / "docs" / "reserve_tail_report.md")
    parser.add_argument("--reserve-tail-json", type=Path, default=root / "docs" / "reserve_tail_report.json")
    parser.add_argument("--bootstrap-report-md", type=Path, default=root / "docs" / "bootstrap_report.md")
    parser.add_argument("--bootstrap-report-json", type=Path, default=root / "docs" / "bootstrap_report.json")
    parser.add_argument("--headline-uncertainty-md", type=Path, default=root / "docs" / "headline_uncertainty_report.md")
    parser.add_argument("--headline-uncertainty-json", type=Path, default=root / "docs" / "headline_uncertainty_report.json")
    parser.add_argument("--size-bucket-report-md", type=Path, default=root / "docs" / "size_bucket_report.md")
    parser.add_argument("--size-bucket-report-json", type=Path, default=root / "docs" / "size_bucket_report.json")
    parser.add_argument("--staleness-bucket-report-md", type=Path, default=root / "docs" / "staleness_bucket_report.md")
    parser.add_argument("--staleness-bucket-report-json", type=Path, default=root / "docs" / "staleness_bucket_report.json")
    parser.add_argument("--market-regime-report-md", type=Path, default=root / "docs" / "market_regime_report.md")
    parser.add_argument("--market-regime-report-json", type=Path, default=root / "docs" / "market_regime_report.json")
    parser.add_argument("--signal-quality-stress-md", type=Path, default=root / "docs" / "signal_quality_stress_report.md")
    parser.add_argument("--signal-quality-stress-json", type=Path, default=root / "docs" / "signal_quality_stress_report.json")
    parser.add_argument("--signal-margin-md", type=Path, default=root / "docs" / "signal_margin_report.md")
    parser.add_argument("--signal-margin-json", type=Path, default=root / "docs" / "signal_margin_report.json")
    parser.add_argument("--base-fee-report-md", type=Path, default=root / "docs" / "base_fee_report.md")
    parser.add_argument("--base-fee-report-json", type=Path, default=root / "docs" / "base_fee_report.json")
    parser.add_argument("--markout-sensitivity-md", type=Path, default=root / "docs" / "markout_sensitivity_report.md")
    parser.add_argument("--markout-sensitivity-json", type=Path, default=root / "docs" / "markout_sensitivity_report.json")
    parser.add_argument("--target-fee-report-md", type=Path, default=root / "docs" / "target_fee_report.md")
    parser.add_argument("--target-fee-report-json", type=Path, default=root / "docs" / "target_fee_report.json")
    parser.add_argument("--capital-path-report-md", type=Path, default=root / "docs" / "capital_path_report.md")
    parser.add_argument("--capital-path-report-json", type=Path, default=root / "docs" / "capital_path_report.json")
    parser.add_argument("--policy-monte-carlo-md", type=Path, default=root / "docs" / "policy_monte_carlo_report.md")
    parser.add_argument("--policy-monte-carlo-json", type=Path, default=root / "docs" / "policy_monte_carlo_report.json")
    parser.add_argument("--risk-adjusted-return-md", type=Path, default=root / "docs" / "risk_adjusted_return_report.md")
    parser.add_argument("--risk-adjusted-return-json", type=Path, default=root / "docs" / "risk_adjusted_return_report.json")
    parser.add_argument("--chain-cost-md", type=Path, default=root / "docs" / "chain_cost_report.md")
    parser.add_argument("--chain-cost-json", type=Path, default=root / "docs" / "chain_cost_report.json")
    parser.add_argument("--live-gas-snapshot-md", type=Path, default=root / "docs" / "live_gas_snapshot_report.md")
    parser.add_argument("--live-gas-snapshot-json", type=Path, default=root / "docs" / "live_gas_snapshot_report.json")
    parser.add_argument("--control-plane-cost-md", type=Path, default=root / "docs" / "control_plane_cost_report.md")
    parser.add_argument("--control-plane-cost-json", type=Path, default=root / "docs" / "control_plane_cost_report.json")
    parser.add_argument("--pnl-attribution-md", type=Path, default=root / "docs" / "pnl_attribution_report.md")
    parser.add_argument("--pnl-attribution-json", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    parser.add_argument("--capital-survival-md", type=Path, default=root / "docs" / "capital_survival_report.md")
    parser.add_argument("--capital-survival-json", type=Path, default=root / "docs" / "capital_survival_report.json")
    parser.add_argument("--operator-cost-md", type=Path, default=root / "docs" / "operator_cost_report.md")
    parser.add_argument("--operator-cost-json", type=Path, default=root / "docs" / "operator_cost_report.json")
    parser.add_argument("--pilot-deployability-md", type=Path, default=root / "docs" / "pilot_deployability_report.md")
    parser.add_argument("--pilot-deployability-json", type=Path, default=root / "docs" / "pilot_deployability_report.json")
    parser.add_argument("--range-width-deployability-md", type=Path, default=root / "docs" / "range_width_deployability_report.md")
    parser.add_argument("--range-width-deployability-json", type=Path, default=root / "docs" / "range_width_deployability_report.json")
    parser.add_argument("--alpha-sweep-md", type=Path, default=root / "docs" / "alpha_sweep.md")
    parser.add_argument("--alpha-sweep-json", type=Path, default=root / "docs" / "alpha_sweep.json")
    parser.add_argument("--target-return-md", type=Path, default=root / "docs" / "target_return_report.md")
    parser.add_argument("--target-return-json", type=Path, default=root / "docs" / "target_return_report.json")
    parser.add_argument("--small-capital-decision-md", type=Path, default=root / "docs" / "small_capital_decision_report.md")
    parser.add_argument("--small-capital-decision-json", type=Path, default=root / "docs" / "small_capital_decision_report.json")
    parser.add_argument("--real-position-md", type=Path, default=root / "docs" / "real_position_report.md")
    parser.add_argument("--real-position-json", type=Path, default=root / "docs" / "real_position_report.json")
    parser.add_argument("--real-position-input-json", type=Path, default=root / "docs" / "real_position_input.json")
    parser.add_argument("--real-position-template-json", type=Path, default=root / "docs" / "real_position_input_template.json")
    parser.add_argument("--real-position-portfolio-md", type=Path, default=root / "docs" / "real_position_portfolio_report.md")
    parser.add_argument("--real-position-portfolio-json", type=Path, default=root / "docs" / "real_position_portfolio_report.json")
    parser.add_argument("--real-position-portfolio-input-json", type=Path, default=root / "docs" / "real_position_portfolio_input.json")
    parser.add_argument("--real-position-portfolio-template-json", type=Path, default=root / "docs" / "real_position_portfolio_input_template.json")
    parser.add_argument("--route-ab-json", type=Path, default=root / "docs" / "route_away_ab.json")
    parser.add_argument("--route-demand-md", type=Path, default=root / "docs" / "route_demand_report.md")
    parser.add_argument("--route-demand-json", type=Path, default=root / "docs" / "route_demand_report.json")
    parser.add_argument("--order-split-md", type=Path, default=root / "docs" / "order_split_report.md")
    parser.add_argument("--order-split-json", type=Path, default=root / "docs" / "order_split_report.json")
    parser.add_argument("--sequential-split-md", type=Path, default=root / "docs" / "sequential_split_report.md")
    parser.add_argument("--sequential-split-json", type=Path, default=root / "docs" / "sequential_split_report.json")
    parser.add_argument("--tvl-dilution-md", type=Path, default=root / "docs" / "tvl_dilution_report.md")
    parser.add_argument("--tvl-dilution-json", type=Path, default=root / "docs" / "tvl_dilution_report.json")
    parser.add_argument("--lp-flow-response-md", type=Path, default=root / "docs" / "lp_flow_response_report.md")
    parser.add_argument("--lp-flow-response-json", type=Path, default=root / "docs" / "lp_flow_response_report.json")
    parser.add_argument("--evidence-md", type=Path, default=root / "docs" / "economic_evidence.md")
    parser.add_argument("--completion-md", type=Path, default=root / "docs" / "economic_completion.md")
    parser.add_argument("--completion-json", type=Path, default=root / "docs" / "economic_completion.json")
    parser.add_argument("--min-hours", type=float, default=24.0)
    parser.add_argument("--min-truth-coverage", type=float, default=0.80)
    parser.add_argument("--min-swaps", type=int, default=1)
    parser.add_argument("--poll-sec", type=float, default=0.0, help="if positive, poll until gates complete")
    parser.add_argument("--max-polls", type=int, default=1, help="maximum finalize attempts; use with --poll-sec")
    args = parser.parse_args()

    paths = FinalizePaths(
        database=args.database,
        reports=args.reports,
        economic_tests_md=args.economic_tests_md,
        economic_tests_json=args.economic_tests_json,
        live_status_md=args.live_status_md,
        live_status_json=args.live_status_json,
        live_convergence_md=args.live_convergence_md,
        live_convergence_json=args.live_convergence_json,
        live_maturity_md=args.live_maturity_md,
        live_maturity_json=args.live_maturity_json,
        live_power_md=args.live_power_md,
        live_power_json=args.live_power_json,
        cross_pair_live_database=args.cross_pair_live_database,
        cross_pair_live_md=args.cross_pair_live_md,
        cross_pair_live_json=args.cross_pair_live_json,
        live_soak_md=args.live_soak_md,
        live_soak_json=args.live_soak_json,
        cross_pair_live_economics_md=args.cross_pair_live_economics_md,
        cross_pair_live_economics_json=args.cross_pair_live_economics_json,
        live_fee_tier_md=args.live_fee_tier_md,
        live_fee_tier_json=args.live_fee_tier_json,
        live_fee_tier_one_bps_glob=args.live_fee_tier_one_bps_glob,
        live_fee_tier_thirty_bps_glob=args.live_fee_tier_thirty_bps_glob,
        route_proxy_json=args.route_proxy_json,
        cross_pair_route_proxy_json=args.cross_pair_route_proxy_json,
        route_share_stability_md=args.route_share_stability_md,
        route_share_stability_json=args.route_share_stability_json,
        route_away_placebo_ab_md=args.route_away_placebo_ab_md,
        route_away_placebo_ab_json=args.route_away_placebo_ab_json,
        route_ab_power_md=args.route_ab_power_md,
        route_ab_power_json=args.route_ab_power_json,
        route_ab_sizing_md=args.route_ab_sizing_md,
        route_ab_sizing_json=args.route_ab_sizing_json,
        route_baseline_probe_json=args.route_baseline_probe_json,
        guard_depeg_md=args.guard_depeg_md,
        guard_depeg_json=args.guard_depeg_json,
        stable_opportunity_md=args.stable_opportunity_md,
        stable_opportunity_json=args.stable_opportunity_json,
        depth_proxy_json=args.depth_proxy_json,
        cross_pair_depth_proxy_json=args.cross_pair_depth_proxy_json,
        oracle_health_md=args.oracle_health_md,
        oracle_health_json=args.oracle_health_json,
        oracle_lag_md=args.oracle_lag_md,
        oracle_lag_json=args.oracle_lag_json,
        risk_report_md=args.risk_report_md,
        risk_report_json=args.risk_report_json,
        drawdown_stop_md=args.drawdown_stop_md,
        drawdown_stop_json=args.drawdown_stop_json,
        fallback_attribution_md=args.fallback_attribution_md,
        fallback_attribution_json=args.fallback_attribution_json,
        inventory_report_md=args.inventory_report_md,
        inventory_report_json=args.inventory_report_json,
        hedge_report_md=args.hedge_report_md,
        hedge_report_json=args.hedge_report_json,
        hedge_execution_md=args.hedge_execution_md,
        hedge_execution_json=args.hedge_execution_json,
        liquidity_share_report_md=args.liquidity_share_report_md,
        liquidity_share_report_json=args.liquidity_share_report_json,
        position_shadow_report_md=args.position_shadow_report_md,
        position_shadow_report_json=args.position_shadow_report_json,
        route_break_even_md=args.route_break_even_md,
        route_break_even_json=args.route_break_even_json,
        adverse_route_away_md=args.adverse_route_away_md,
        adverse_route_away_json=args.adverse_route_away_json,
        route_collector_smoke_md=args.route_collector_smoke_md,
        route_collector_smoke_json=args.route_collector_smoke_json,
        route_window_plan_md=args.route_window_plan_md,
        route_window_plan_json=args.route_window_plan_json,
        route_rpc_preflight_md=args.route_rpc_preflight_md,
        route_rpc_preflight_json=args.route_rpc_preflight_json,
        route_readiness_md=args.route_readiness_md,
        route_readiness_json=args.route_readiness_json,
        route_cost_md=args.route_cost_md,
        route_cost_json=args.route_cost_json,
        quote_route_readiness_md=args.quote_route_readiness_md,
        quote_route_readiness_json=args.quote_route_readiness_json,
        quote_headroom_md=args.quote_headroom_md,
        quote_headroom_json=args.quote_headroom_json,
        cross_pair_quote_headroom_md=args.cross_pair_quote_headroom_md,
        cross_pair_quote_headroom_json=args.cross_pair_quote_headroom_json,
        quote_headroom_stability_md=args.quote_headroom_stability_md,
        quote_headroom_stability_json=args.quote_headroom_stability_json,
        quote_headroom_drift_md=args.quote_headroom_drift_md,
        quote_headroom_drift_json=args.quote_headroom_drift_json,
        quote_premium_stress_md=args.quote_premium_stress_md,
        quote_premium_stress_json=args.quote_premium_stress_json,
        quote_event_headroom_md=args.quote_event_headroom_md,
        quote_event_headroom_json=args.quote_event_headroom_json,
        quote_provenance_md=args.quote_provenance_md,
        quote_provenance_json=args.quote_provenance_json,
        quote_elasticity_md=args.quote_elasticity_md,
        quote_elasticity_json=args.quote_elasticity_json,
        insurance_reserve_md=args.insurance_reserve_md,
        insurance_reserve_json=args.insurance_reserve_json,
        premium_allocation_md=args.premium_allocation_md,
        premium_allocation_json=args.premium_allocation_json,
        premium_utilization_md=args.premium_utilization_md,
        premium_utilization_json=args.premium_utilization_json,
        charge_attribution_md=args.charge_attribution_md,
        charge_attribution_json=args.charge_attribution_json,
        reserve_delay_md=args.reserve_delay_md,
        reserve_delay_json=args.reserve_delay_json,
        reserve_lifecycle_md=args.reserve_lifecycle_md,
        reserve_lifecycle_json=args.reserve_lifecycle_json,
        reserve_tail_md=args.reserve_tail_md,
        reserve_tail_json=args.reserve_tail_json,
        bootstrap_report_md=args.bootstrap_report_md,
        bootstrap_report_json=args.bootstrap_report_json,
        headline_uncertainty_md=args.headline_uncertainty_md,
        headline_uncertainty_json=args.headline_uncertainty_json,
        size_bucket_report_md=args.size_bucket_report_md,
        size_bucket_report_json=args.size_bucket_report_json,
        staleness_bucket_report_md=args.staleness_bucket_report_md,
        staleness_bucket_report_json=args.staleness_bucket_report_json,
        market_regime_report_md=args.market_regime_report_md,
        market_regime_report_json=args.market_regime_report_json,
        signal_quality_stress_md=args.signal_quality_stress_md,
        signal_quality_stress_json=args.signal_quality_stress_json,
        signal_margin_md=args.signal_margin_md,
        signal_margin_json=args.signal_margin_json,
        base_fee_report_md=args.base_fee_report_md,
        base_fee_report_json=args.base_fee_report_json,
        markout_sensitivity_md=args.markout_sensitivity_md,
        markout_sensitivity_json=args.markout_sensitivity_json,
        target_fee_report_md=args.target_fee_report_md,
        target_fee_report_json=args.target_fee_report_json,
        capital_path_report_md=args.capital_path_report_md,
        capital_path_report_json=args.capital_path_report_json,
        policy_monte_carlo_md=args.policy_monte_carlo_md,
        policy_monte_carlo_json=args.policy_monte_carlo_json,
        risk_adjusted_return_md=args.risk_adjusted_return_md,
        risk_adjusted_return_json=args.risk_adjusted_return_json,
        chain_cost_md=args.chain_cost_md,
        chain_cost_json=args.chain_cost_json,
        live_gas_snapshot_md=args.live_gas_snapshot_md,
        live_gas_snapshot_json=args.live_gas_snapshot_json,
        control_plane_cost_md=args.control_plane_cost_md,
        control_plane_cost_json=args.control_plane_cost_json,
        pnl_attribution_md=args.pnl_attribution_md,
        pnl_attribution_json=args.pnl_attribution_json,
        capital_survival_md=args.capital_survival_md,
        capital_survival_json=args.capital_survival_json,
        operator_cost_md=args.operator_cost_md,
        operator_cost_json=args.operator_cost_json,
        pilot_deployability_md=args.pilot_deployability_md,
        pilot_deployability_json=args.pilot_deployability_json,
        range_width_deployability_md=args.range_width_deployability_md,
        range_width_deployability_json=args.range_width_deployability_json,
        alpha_sweep_md=args.alpha_sweep_md,
        alpha_sweep_json=args.alpha_sweep_json,
        target_return_md=args.target_return_md,
        target_return_json=args.target_return_json,
        small_capital_decision_md=args.small_capital_decision_md,
        small_capital_decision_json=args.small_capital_decision_json,
        real_position_md=args.real_position_md,
        real_position_json=args.real_position_json,
        real_position_input_json=args.real_position_input_json,
        real_position_template_json=args.real_position_template_json,
        real_position_portfolio_md=args.real_position_portfolio_md,
        real_position_portfolio_json=args.real_position_portfolio_json,
        real_position_portfolio_input_json=args.real_position_portfolio_input_json,
        real_position_portfolio_template_json=args.real_position_portfolio_template_json,
        route_ab_json=args.route_ab_json,
        route_demand_md=args.route_demand_md,
        route_demand_json=args.route_demand_json,
        order_split_md=args.order_split_md,
        order_split_json=args.order_split_json,
        sequential_split_md=args.sequential_split_md,
        sequential_split_json=args.sequential_split_json,
        tvl_dilution_md=args.tvl_dilution_md,
        tvl_dilution_json=args.tvl_dilution_json,
        lp_flow_response_md=args.lp_flow_response_md,
        lp_flow_response_json=args.lp_flow_response_json,
        evidence_md=args.evidence_md,
        completion_md=args.completion_md,
        completion_json=args.completion_json,
    )

    attempts = max(1, args.max_polls)
    complete = False
    for index in range(attempts):
        print(f"economic finalize attempt {index + 1}/{attempts}: started", flush=True)
        complete = finalize_once(root, paths, args.min_hours, args.min_truth_coverage, args.min_swaps)
        print(f"economic finalize attempt {index + 1}/{attempts}: {'complete' if complete else 'incomplete'}", flush=True)
        if complete or args.poll_sec <= 0 or index == attempts - 1:
            break
        time.sleep(args.poll_sec)

    print(f"wrote {paths.reports / 'summary.md'}")
    print(f"wrote {paths.economic_tests_md}")
    print(f"wrote {paths.live_status_md}")
    print(f"wrote {paths.live_convergence_md}")
    print(f"wrote {paths.live_maturity_md}")
    print(f"wrote {paths.live_power_md}")
    print(f"wrote {paths.cross_pair_live_md}")
    print(f"wrote {paths.live_soak_md}")
    print(f"wrote {paths.cross_pair_live_economics_md}")
    print(f"wrote {paths.live_fee_tier_md}")
    print(f"wrote {paths.oracle_health_md}")
    print(f"wrote {paths.oracle_lag_md}")
    print(f"wrote {paths.risk_report_md}")
    print(f"wrote {paths.drawdown_stop_md}")
    print(f"wrote {paths.fallback_attribution_md}")
    print(f"wrote {paths.inventory_report_md}")
    print(f"wrote {paths.hedge_report_md}")
    print(f"wrote {paths.hedge_execution_md}")
    print(f"wrote {paths.liquidity_share_report_md}")
    print(f"wrote {paths.position_shadow_report_md}")
    print(f"wrote {paths.route_break_even_md}")
    print(f"wrote {paths.adverse_route_away_md}")
    print(f"wrote {paths.route_collector_smoke_md}")
    print(f"wrote {paths.route_window_plan_md}")
    print(f"wrote {paths.route_rpc_preflight_md}")
    print(f"wrote {paths.route_readiness_md}")
    print(f"wrote {paths.route_share_stability_md}")
    print(f"wrote {paths.route_away_placebo_ab_md}")
    print(f"wrote {paths.route_ab_power_md}")
    print(f"wrote {paths.route_ab_sizing_md}")
    print(f"wrote {paths.guard_depeg_md}")
    print(f"wrote {paths.stable_opportunity_md}")
    print(f"wrote {paths.route_cost_md}")
    print(f"wrote {paths.quote_route_readiness_md}")
    print(f"wrote {paths.quote_headroom_md}")
    print(f"wrote {paths.cross_pair_quote_headroom_md}")
    print(f"wrote {paths.quote_headroom_stability_md}")
    print(f"wrote {paths.quote_headroom_drift_md}")
    print(f"wrote {paths.quote_premium_stress_md}")
    print(f"wrote {paths.quote_event_headroom_md}")
    print(f"wrote {paths.quote_provenance_md}")
    print(f"wrote {paths.quote_elasticity_md}")
    print(f"wrote {paths.insurance_reserve_md}")
    print(f"wrote {paths.premium_allocation_md}")
    print(f"wrote {paths.premium_utilization_md}")
    print(f"wrote {paths.charge_attribution_md}")
    print(f"wrote {paths.reserve_delay_md}")
    print(f"wrote {paths.reserve_lifecycle_md}")
    print(f"wrote {paths.reserve_tail_md}")
    print(f"wrote {paths.bootstrap_report_md}")
    print(f"wrote {paths.headline_uncertainty_md}")
    print(f"wrote {paths.size_bucket_report_md}")
    print(f"wrote {paths.staleness_bucket_report_md}")
    print(f"wrote {paths.market_regime_report_md}")
    print(f"wrote {paths.signal_quality_stress_md}")
    print(f"wrote {paths.signal_margin_md}")
    print(f"wrote {paths.base_fee_report_md}")
    print(f"wrote {paths.markout_sensitivity_md}")
    print(f"wrote {paths.target_fee_report_md}")
    print(f"wrote {paths.capital_path_report_md}")
    print(f"wrote {paths.policy_monte_carlo_md}")
    print(f"wrote {paths.risk_adjusted_return_md}")
    print(f"wrote {paths.chain_cost_md}")
    print(f"wrote {paths.live_gas_snapshot_md}")
    print(f"wrote {paths.control_plane_cost_md}")
    print(f"wrote {paths.pnl_attribution_md}")
    print(f"wrote {paths.capital_survival_md}")
    print(f"wrote {paths.operator_cost_md}")
    print(f"wrote {paths.pilot_deployability_md}")
    print(f"wrote {paths.range_width_deployability_md}")
    print(f"wrote {paths.alpha_sweep_md}")
    print(f"wrote {paths.target_return_md}")
    print(f"wrote {paths.small_capital_decision_md}")
    print(f"wrote {paths.real_position_md}")
    print(f"wrote {paths.real_position_portfolio_md}")
    print(f"wrote {paths.route_demand_md}")
    print(f"wrote {paths.order_split_md}")
    print(f"wrote {paths.sequential_split_md}")
    print(f"wrote {paths.tvl_dilution_md}")
    print(f"wrote {paths.lp_flow_response_md}")
    print(f"wrote {paths.evidence_md}")
    print(f"wrote {paths.completion_md}")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
