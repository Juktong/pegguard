from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C
from .route_away_ab import evidence_errors as route_ab_evidence_errors


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def markdown(
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
    cross_pair_live_report: dict | None = None,
    live_soak_report: dict | None = None,
    cross_pair_live_economics_report: dict | None = None,
    live_fee_tier_report: dict | None = None,
    premium_utilization_report: dict | None = None,
    charge_attribution_report: dict | None = None,
    route_share_stability_report: dict | None = None,
    route_away_placebo_ab_report: dict | None = None,
    route_ab_power_report: dict | None = None,
    route_ab_sizing_report: dict | None = None,
    route_baseline_probe_report: dict | None = None,
    guard_depeg_report: dict | None = None,
    stable_opportunity_report: dict | None = None,
    market_regime_report: dict | None = None,
    signal_quality_stress_report: dict | None = None,
    signal_margin_report: dict | None = None,
) -> str:
    live_convergence_report = live_convergence_report or {}
    live_maturity_report = live_maturity_report or {}
    live_power_report = live_power_report or {}
    cross_pair_live_report = cross_pair_live_report or {}
    live_soak_report = live_soak_report or {}
    cross_pair_live_economics_report = cross_pair_live_economics_report or {}
    live_fee_tier_report = live_fee_tier_report or {}
    premium_utilization_report = premium_utilization_report or {}
    charge_attribution_report = charge_attribution_report or {}
    route_share_stability_report = route_share_stability_report or {}
    route_away_placebo_ab_report = route_away_placebo_ab_report or {}
    route_ab_power_report = route_ab_power_report or {}
    route_ab_sizing_report = route_ab_sizing_report or {}
    route_baseline_probe_report = route_baseline_probe_report or {}
    guard_depeg_report = guard_depeg_report or {}
    stable_opportunity_report = stable_opportunity_report or {}
    market_regime_report = market_regime_report or {}
    signal_quality_stress_report = signal_quality_stress_report or {}
    signal_margin_report = signal_margin_report or {}
    cross_pair_route_proxy = cross_pair_route_proxy or {}
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
    live_complete = bool(live_status.get("complete", False))
    route_proxy_events = sum(int(row.get("swaps", 0)) for row in route_proxy.get("tiers", []))
    cross_pair_events = sum(int(row.get("swaps", 0)) for row in cross_pair_route_proxy.get("tiers", []))
    route_share_rows = len(route_share_stability_report.get("rows", []))
    route_away_placebo_rows = len(route_away_placebo_ab_report.get("rows", []))
    route_ab_power_rows = len(route_ab_power_report.get("mde_rows", []))
    route_ab_sizing_rows = len(route_ab_sizing_report.get("candidate_rows", []))
    depth_rows = len(depth_proxy.get("tiers", []))
    cross_depth_rows = len(cross_pair_depth_proxy.get("tiers", []))
    oracle_rows = int(oracle_health.get("swaps", 0))
    oracle_lag_rows = len(oracle_lag.get("rows", []))
    risk_windows = len(risk_report.get("windows", []))
    drawdown_stop_rows = len(drawdown_stop.get("rows", []))
    fallback_rows = int(fallback_attribution.get("rows", 0))
    inventory_rows = len(inventory_report.get("windows", []))
    hedge_rows = len(hedge_report.get("rows", []))
    hedge_execution_rows = len(hedge_execution_report.get("rows", []))
    liquidity_rows = len(liquidity_share_report.get("rows", []))
    position_shadow_rows = len(position_shadow_report.get("rows", []))
    real_position_rows = len(real_position_report.get("rows", []))
    real_position_portfolio_rows = len(real_position_portfolio_report.get("rows", []))
    break_even_rows = len(route_break_even.get("rows", []))
    adverse_route_rows = len(adverse_route_away.get("rows", []))
    route_readiness_status = str(route_readiness.get("status", "missing checklist"))
    bootstrap_windows = len(bootstrap_report.get("windows", []))
    size_bucket_rows = len(size_bucket_report.get("rows", []))
    staleness_rows = int(staleness_bucket_report.get("rows", 0))
    market_regime_rows = len(market_regime_report.get("rows", []))
    signal_quality_rows = len(signal_quality_stress_report.get("rows", []))
    signal_margin_rows = len(signal_margin_report.get("rows", []))
    base_fee_rows = len(base_fee_report.get("rows", []))
    target_fee_rows = len(target_fee_report.get("rows", []))
    capital_path_rows = len(capital_path_report.get("rows", []))
    policy_monte_carlo_rows = len(policy_monte_carlo_report.get("rows", []))
    risk_adjusted_rows = len(risk_adjusted_return_report.get("rows", []))
    chain_cost_rows = len(chain_cost_report.get("rows", []))
    live_gas_rows = len(live_gas_snapshot_report.get("rows", []))
    control_plane_cost_rows = len(control_plane_cost_report.get("rows", []))
    pnl_attribution_rows = len(pnl_attribution_report.get("rows", []))
    capital_survival_rows = len(capital_survival_report.get("rows", []))
    operator_cost_rows = len(operator_cost_report.get("rows", []))
    alpha_rows = len(alpha_sweep.get("rows", []))
    target_return_rows = len(target_return_report.get("rows", []))
    order_split_rows = len(order_split_report.get("rows", []))
    tvl_equilibrium_rows = len(tvl_dilution_report.get("equilibrium_rows", []))
    lp_flow_rows = len(lp_flow_response_report.get("rows", []))
    live_fee_tier_rows = len(live_fee_tier_report.get("rows", []))
    route_cost_rows = len(route_cost_proxy.get("rows", []))
    sequential_split_rows = len(sequential_split_report.get("rows", []))
    quote_route_status = str(quote_route_readiness.get("status", "missing checklist"))
    quote_headroom_rows = len(quote_headroom_report.get("rows", []))
    cross_pair_quote_headroom_rows = len(cross_pair_quote_headroom_report.get("rows", []))
    quote_headroom_stability_rows = len(quote_headroom_stability_report.get("rows", []))
    quote_headroom_drift_rows = len(quote_headroom_drift_report.get("rows", []))
    quote_premium_stress_rows = len(quote_premium_stress_report.get("rows", []))
    quote_event_headroom_rows = len(quote_event_headroom_report.get("rows", []))
    quote_provenance_rows = len(quote_provenance_report.get("artifacts", []))
    quote_elasticity_rows = len(quote_elasticity_report.get("rows", []))
    insurance_reserve_rows = len(insurance_reserve_report.get("rows", []))
    premium_allocation_rows = len(premium_allocation_report.get("rows", []))
    premium_utilization_rows = len(premium_utilization_report.get("rows", []))
    charge_attribution_windows = len(charge_attribution_report.get("windows", []))
    reserve_delay_rows = len(reserve_delay_report.get("rows", []))
    reserve_lifecycle_rows = len(reserve_lifecycle_report.get("rows", []))
    reserve_tail_rows = len(reserve_tail_report.get("rows", []))
    headline_windows = len(headline_uncertainty_report.get("windows", []))
    headline_policy_rows = len(headline_uncertainty_report.get("policies", []))
    route_demand_rows = len(route_demand_report.get("rows", []))
    markout_sensitivity_rows = len(markout_sensitivity_report.get("rows", []))
    pilot_deployability_rows = len(pilot_deployability_report.get("rows", []))
    range_width_rows = len(range_width_deployability_report.get("rows", []))
    small_capital_decision_rows = len(small_capital_decision_report.get("rows", []))
    route_ab_errors = _route_ab_errors(route_ab)
    route_ab_events = _route_ab_events(route_ab)
    route_ab_complete = route_ab_events > 0
    route_ab_note = _route_ab_note(route_ab, route_ab_errors)

    lines = [
        "# Economic Evidence Ledger",
        "",
        "This file summarizes the economic test surface. It is evidence tracking, not calibration.",
        "",
        "## Status",
        "",
        "| Test area | Evidence | Status | Notes |",
        "|---|---|---|---|",
        (
            "| Historical event replay | `test/EventDiff.t.sol`, `docs/economic_tests.md` | complete | "
            "Per-event truth precision/capture gates pass on calm and volatile fixtures. |"
        ),
        (
            "| Strategy benchmarks | `docs/economic_tests.md` | complete | "
            "Static tiers, PegGuard variants, route-away haircuts, LP policy PnL, gas sensitivity, and range stress generated from fixtures/live DB. |"
        ),
        (
            "| Small-capital cost tests | `docs/economic_tests.md`, `docs/capital_model.md` | complete | "
            "`capital_model.md` sizes the pilot classes; `economic_tests.md` adds route-away haircut, gas scenario drag, and rebalance drag. |"
        ),
        (
            "| Sentinel calibration | `test/SentinelCalibration.t.sol`, `docs/sentinel_calibration.md` | complete | "
            "Fixture-based false-positive and trigger timing grid is covered. |"
        ),
        (
            f"| GUARD breaker economics | `docs/guard_depeg_report.md` | {'complete' if guard_depeg_report.get('complete') else 'in progress'} | "
            f"{_guard_depeg_summary(guard_depeg_report)}. |"
        ),
        (
            f"| GUARD stable opportunity | `docs/stable_opportunity_report.md` | {'complete' if stable_opportunity_report.get('complete') else 'in progress'} | "
            f"{_stable_opportunity_summary(stable_opportunity_report)}. |"
        ),
        (
            f"| Live shadow 24h | `{live_status.get('database', 'n/a')}` | {'complete' if live_complete else 'in progress'} | "
            f"{int(live_status.get('swaps', 0))} swaps, {float(live_status.get('observed_span_hours', 0)):.2f}h span, "
            f"{float(live_status.get('truth_coverage', 0)):.2%} truth coverage. |"
        ),
        (
            f"| Live convergence | `docs/live_convergence_report.md` | {'complete' if live_convergence_report.get('complete') else 'in progress'} | "
            f"{_live_convergence_summary(live_convergence_report)}. |"
        ),
        (
            f"| Live maturity | `docs/live_maturity_report.md` | {'complete' if live_maturity_report.get('complete') else 'in progress'} | "
            f"{_live_maturity_summary(live_maturity_report)}. |"
        ),
        (
            f"| Live sample power | `docs/live_power_report.md` | {'complete' if live_power_report.get('complete') else 'in progress'} | "
            f"{_live_power_summary(live_power_report)}. |"
        ),
        (
            f"| Cross-pair live shadow | `docs/cross_pair_live_report.md` | {'complete' if cross_pair_live_report.get('complete') else 'in progress'} | "
            f"{_cross_pair_live_summary(cross_pair_live_report)}. |"
        ),
        (
            f"| Live soak tracker | `docs/live_soak_report.md` | {'complete' if live_soak_report.get('complete') else 'in progress'} | "
            f"{_live_soak_summary(live_soak_report)}. |"
        ),
        (
            f"| Cross-pair live economics | `docs/cross_pair_live_economics_report.md` | {'complete' if cross_pair_live_economics_report.get('complete') else 'in progress'} | "
            f"{_cross_pair_live_economics_summary(cross_pair_live_economics_report)}. |"
        ),
        (
            f"| Live fee-tier shadow | `docs/live_fee_tier_report.md` | {_live_fee_tier_status(live_fee_tier_report)} | "
            f"{live_fee_tier_rows} rows; {_live_fee_tier_summary(live_fee_tier_report)}. |"
        ),
        (
            f"| Route-away proxy | `docs/route_away_proxy.md` | {'complete' if route_proxy_events else 'missing'} | "
            f"{route_proxy_events} same-pair fee-tier swaps; proxy only, not controlled elasticity. |"
        ),
        (
            f"| Cross-pair route-away proxy | `docs/route_away_proxy_weth_usdt.md` | {'complete' if cross_pair_events else 'missing'} | "
            f"{cross_pair_events} {cross_pair_route_proxy.get('pair', 'second-pair')} fee-tier swaps; route sensitivity context only. |"
        ),
        (
            f"| Route-share placebo stability | `docs/route_share_stability_report.md` | {'complete' if route_share_stability_report.get('complete') else 'missing'} | "
            f"{route_share_rows} lookback rows; {_route_share_stability_summary(route_share_stability_report)}. |"
        ),
        (
            f"| Route-away A/A placebo | `docs/route_away_placebo_ab_report.md` | {'complete' if route_away_placebo_ab_report.get('complete') else 'missing'} | "
            f"{route_away_placebo_rows} rows; {_route_away_placebo_ab_summary(route_away_placebo_ab_report)}. |"
        ),
        (
            f"| Controlled route-away power check | `docs/route_ab_power_report.md` | {'complete' if route_ab_power_report.get('complete') else 'missing'} | "
            f"{route_ab_power_rows} MDE rows; {_route_ab_power_summary(route_ab_power_report)}. |"
        ),
        (
            f"| Controlled route-away sizing plan | `docs/route_ab_sizing_report.md` | {'complete' if route_ab_sizing_report.get('complete') else 'missing'} | "
            f"{route_ab_sizing_rows} candidates; {_route_ab_sizing_summary(route_ab_sizing_report)}. |"
        ),
        (
            f"| Route-away baseline-flow probe | `docs/route_away_baseline_probe.md` | {'complete' if route_baseline_probe_report.get('complete') else 'in progress'} | "
            f"{_route_baseline_probe_summary(route_baseline_probe_report)}. |"
        ),
        (
            f"| Fee-tier depth proxy | `docs/depth_proxy.md` | {'complete' if depth_rows else 'missing'} | "
            f"{depth_proxy.get('pair', 'same-pair')} active depth snapshot across {depth_rows} tiers. |"
        ),
        (
            f"| Cross-pair depth proxy | `docs/depth_proxy_weth_usdt.md` | {'complete' if cross_depth_rows else 'missing'} | "
            f"{cross_pair_depth_proxy.get('pair', 'second-pair')} active depth snapshot across {cross_depth_rows} tiers. |"
        ),
        (
            f"| Oracle-health economics | `docs/oracle_health.md` | {'complete' if oracle_rows else 'missing'} | "
            f"{oracle_rows} swaps; fresh fallback notional share {_fresh_fallback_share(oracle_health):.2%}. |"
        ),
        (
            f"| Oracle-lag stress | `docs/oracle_lag_report.md` | {'complete' if oracle_lag_rows else 'missing'} | "
            f"{oracle_lag_rows} rows; lag5 net delta {_usd(_oracle_lag_delta(oracle_lag, 'lag5'))}. |"
        ),
        (
            f"| Tail-risk concentration | `docs/risk_report.md` | {'complete' if risk_windows else 'missing'} | "
            f"{risk_windows} windows; live max drawdown {_usd(_live_drawdown(risk_report))}. |"
        ),
        (
            f"| Drawdown stop-loss | `docs/drawdown_stop_report.md` | {'complete' if drawdown_stop_rows else 'missing'} | "
            f"{drawdown_stop_rows} rows; live $50 stop {_drawdown_stop_status(drawdown_stop, 'live shadow', 50_000_000)}. |"
        ),
        (
            f"| Fallback attribution | `docs/fallback_attribution.md` | {'complete' if fallback_rows else 'missing'} | "
            f"{fallback_rows} swaps; fresh missed premium {_usd(_fresh_missed_extra(fallback_attribution))}. |"
        ),
        (
            f"| LP inventory accounting | `docs/inventory_report.md` | {'complete' if inventory_rows else 'missing'} | "
            f"{inventory_rows} range rows; worst inventory IL {_usd(_worst_inventory_il(inventory_report))}. |"
        ),
        (
            f"| Hedge stress | `docs/hedge_report.md` | {'complete' if hedge_rows else 'missing'} | "
            f"{hedge_rows} rows; best volatile improvement {_usd(_best_hedge_improvement(hedge_report, 'vol'))}. |"
        ),
        (
            f"| Hedge execution-cost stress | `docs/hedge_execution_report.md` | {'complete' if hedge_execution_rows else 'missing'} | "
            f"{_hedge_execution_summary(hedge_execution_report)}. |"
        ),
        (
            f"| Liquidity-share sizing | `docs/liquidity_share_report.md` | {'complete' if liquidity_rows else 'missing'} | "
            f"{liquidity_rows} sizing rows; small live sample net {_usd(_small_live_share_net(liquidity_share_report))}. |"
        ),
        (
            f"| Position-level LP shadow | `docs/position_shadow_report.md` | {'complete' if position_shadow_rows else 'missing'} | "
            f"{_position_shadow_summary(position_shadow_report)}. |"
        ),
        (
            f"| Real position replay | `docs/real_position_report.md` | {'complete' if real_position_rows else 'missing input'} | "
            f"{_real_position_summary(real_position_report)}. |"
        ),
        (
            f"| Multi-position LP replay | `docs/real_position_portfolio_report.md` | {'complete' if real_position_portfolio_report.get('complete') else 'needs more audited positions'} | "
            f"{_real_position_portfolio_summary(real_position_portfolio_report)}. |"
        ),
        (
            f"| Route-away break-even | `docs/route_away_break_even.md` | {'complete' if break_even_rows else 'missing'} | "
            f"{break_even_rows} rows; vol zero-net tolerance {_rate(_vol_zero_tolerance(route_break_even))}. |"
        ),
        (
            f"| Adverse route-away stress | `docs/adverse_route_away_report.md` | {'complete' if adverse_route_rows else 'missing'} | "
            f"{_adverse_route_summary(adverse_route_away)}. |"
        ),
        (
            f"| Route-away readiness | `docs/route_away_readiness.md` | {route_readiness_status} | "
            f"{_route_readiness_notes(route_readiness)} |"
        ),
        (
            f"| Depth-adjusted route cost | `docs/route_cost_proxy.md` | {'complete' if route_cost_rows else 'missing'} | "
            f"{route_cost_rows} rows; WETH/USDC $50k headroom {_bps_or_na(_route_headroom(route_cost_proxy, 'WETH/USDC', 50_000_000_000))}. |"
        ),
        (
            f"| Quote-route readiness | `docs/quote_route_readiness.md` | {quote_route_status} | "
            f"{_quote_route_notes(quote_route_readiness)} |"
        ),
        (
            f"| Quote premium headroom | `docs/quote_headroom_report.md` | {'complete' if quote_headroom_rows else 'missing'} | "
            f"{quote_headroom_rows} rows; {_quote_headroom_range(quote_headroom_report)}. |"
        ),
        (
            f"| Cross-pair quote headroom | `docs/quote_headroom_weth_usdt.md` | {'complete' if cross_pair_quote_headroom_rows else 'missing'} | "
            f"{cross_pair_quote_headroom_rows} rows; {_quote_headroom_range(cross_pair_quote_headroom_report)}. |"
        ),
        (
            f"| Quote-headroom repeatability | `docs/quote_headroom_stability_report.md` | {'complete' if quote_headroom_stability_report.get('complete') else 'missing'} | "
            f"{_quote_headroom_stability_summary(quote_headroom_stability_report)}. |"
        ),
        (
            f"| Quote-headroom drift | `docs/quote_headroom_drift_report.md` | {'complete' if quote_headroom_drift_report.get('complete') else 'missing'} | "
            f"{quote_headroom_drift_rows} rows; {_quote_headroom_drift_summary(quote_headroom_drift_report)}. |"
        ),
        (
            f"| Quote premium stress | `docs/quote_premium_stress.md` | {'complete' if quote_premium_stress_rows else 'missing'} | "
            f"{_quote_premium_stress_summary(quote_premium_stress_report)}. |"
        ),
        (
            f"| Quote event headroom | `docs/quote_event_headroom_report.md` | {'complete' if quote_event_headroom_rows else 'missing'} | "
            f"{_quote_event_headroom_summary(quote_event_headroom_report)}. |"
        ),
        (
            f"| Quote provenance audit | `docs/quote_provenance_report.md` | {'complete' if quote_provenance_report.get('complete') else 'incomplete'} | "
            f"{_quote_provenance_summary(quote_provenance_report)}. |"
        ),
        (
            f"| Quote-headroom elasticity | `docs/quote_elasticity_report.md` | {'complete' if quote_elasticity_rows else 'missing'} | "
            f"{_quote_elasticity_summary(quote_elasticity_report)}. |"
        ),
        (
            f"| Insurance reserve solvency | `docs/insurance_reserve_report.md` | {'complete' if insurance_reserve_rows else 'missing'} | "
            f"{_insurance_reserve_summary(insurance_reserve_report)}. |"
        ),
        (
            f"| Premium allocation frontier | `docs/premium_allocation_report.md` | {'complete' if premium_allocation_rows else 'missing'} | "
            f"{_premium_allocation_summary(premium_allocation_report)}. |"
        ),
        (
            f"| Premium utilization | `docs/premium_utilization_report.md` | {'complete' if premium_utilization_rows else 'missing'} | "
            f"{_premium_utilization_summary(premium_utilization_report)}. |"
        ),
        (
            f"| Charge attribution | `docs/charge_attribution_report.md` | {'complete' if charge_attribution_windows else 'missing'} | "
            f"{_charge_attribution_summary(charge_attribution_report)}. |"
        ),
        (
            f"| Reserve claim-delay stress | `docs/reserve_delay_report.md` | {'complete' if reserve_delay_rows else 'missing'} | "
            f"{_reserve_delay_summary(reserve_delay_report)}. |"
        ),
        (
            f"| Reserve lifecycle churn | `docs/reserve_lifecycle_report.md` | {'complete' if reserve_lifecycle_rows else 'missing'} | "
            f"{_reserve_lifecycle_summary(reserve_lifecycle_report)}. |"
        ),
        (
            f"| Reserve tail sizing | `docs/reserve_tail_report.md` | {'complete' if reserve_tail_rows else 'missing'} | "
            f"{_reserve_tail_summary(reserve_tail_report)}. |"
        ),
        (
            f"| Bootstrap robustness | `docs/bootstrap_report.md` | {'complete' if bootstrap_windows else 'missing'} | "
            f"{bootstrap_windows} windows; vol P(net>=0) {_rate(_bootstrap_positive_net(bootstrap_report, 'vol'))}. |"
        ),
        (
            f"| Headline uncertainty bands | `docs/headline_uncertainty_report.md` | {'complete' if headline_windows else 'missing'} | "
            f"{headline_windows} windows, {headline_policy_rows} policy rows; {_headline_uncertainty_summary(headline_uncertainty_report)}. |"
        ),
        (
            f"| Trade-size buckets | `docs/size_bucket_report.md` | {'complete' if size_bucket_rows else 'missing'} | "
            f"{size_bucket_rows} rows; vol >=$50k net {_usd(_bucket_net(size_bucket_report, 'vol', '>=$50k'))}. |"
        ),
        (
            f"| Oracle staleness buckets | `docs/staleness_bucket_report.md` | {'complete' if staleness_rows else 'missing'} | "
            f"{staleness_rows} rows; stale/missing truth net {_usd(_staleness_bucket_net(staleness_bucket_report, '>5s/missing'))}. |"
        ),
        (
            f"| Market-regime segments | `docs/market_regime_report.md` | {'complete' if market_regime_rows else 'missing'} | "
            f"{_market_regime_summary(market_regime_report)}. |"
        ),
        (
            f"| Signal-quality stress | `docs/signal_quality_stress_report.md` | {'complete' if signal_quality_rows else 'missing'} | "
            f"{_signal_quality_stress_summary(signal_quality_stress_report)}. |"
        ),
        (
            f"| Signal margin | `docs/signal_margin_report.md` | {'complete' if signal_margin_rows else 'missing'} | "
            f"{_signal_margin_summary(signal_margin_report)}. |"
        ),
        (
            f"| Base-fee adequacy | `docs/base_fee_report.md` | {'complete' if base_fee_rows else 'missing'} | "
            f"{base_fee_rows} rows; vol zero-net base {_pips(_base_required(base_fee_report, 'vol', 'required_base_pips_zero'))}. |"
        ),
        (
            f"| Truth markout sensitivity | `docs/markout_sensitivity_report.md` | {'complete' if markout_sensitivity_rows else 'missing'} | "
            f"{_markout_sensitivity_summary(markout_sensitivity_report)}. |"
        ),
        (
            f"| Target-fee viability | `docs/target_fee_report.md` | {'complete' if target_fee_rows else 'missing'} | "
            f"{target_fee_rows} rows; vol 1 bps target {_target_viability(target_fee_report, 'vol', '1 bps net')}. |"
        ),
        (
            f"| Capital-path stress | `docs/capital_path_report.md` | {'complete' if capital_path_rows else 'missing'} | "
            f"{capital_path_rows} rows; worst drawdown {_rate(_capital_path_worst_drawdown(capital_path_report))}. |"
        ),
        (
            f"| Policy Monte Carlo | `docs/policy_monte_carlo_report.md` | {'complete' if policy_monte_carlo_rows else 'missing'} | "
            f"{_policy_monte_carlo_summary(policy_monte_carlo_report)}. |"
        ),
        (
            f"| Risk-adjusted return | `docs/risk_adjusted_return_report.md` | {'complete' if risk_adjusted_rows else 'missing'} | "
            f"{_risk_adjusted_return_summary(risk_adjusted_return_report)}. |"
        ),
        (
            f"| Chain cost matrix | `docs/chain_cost_report.md` | {'complete' if chain_cost_rows else 'missing'} | "
            f"{_chain_cost_summary(chain_cost_report)}. |"
        ),
        (
            f"| Live gas snapshot | `docs/live_gas_snapshot_report.md` | {'complete' if live_gas_rows else 'missing'} | "
            f"{_live_gas_snapshot_summary(live_gas_snapshot_report)}. |"
        ),
        (
            f"| Control-plane callback cost | `docs/control_plane_cost_report.md` | {'complete' if control_plane_cost_rows else 'missing'} | "
            f"{_control_plane_cost_summary(control_plane_cost_report)}. |"
        ),
        (
            f"| PnL attribution | `docs/pnl_attribution_report.md` | {'complete' if pnl_attribution_rows else 'missing'} | "
            f"{_pnl_attribution_summary(pnl_attribution_report)}. |"
        ),
        (
            f"| Capital survival runway | `docs/capital_survival_report.md` | {'complete' if capital_survival_rows else 'missing'} | "
            f"{_capital_survival_summary(capital_survival_report)}. |"
        ),
        (
            f"| Operator fixed-cost drag | `docs/operator_cost_report.md` | {'complete' if operator_cost_rows else 'missing'} | "
            f"{_operator_cost_summary(operator_cost_report)}. |"
        ),
        (
            f"| Pilot deployability stress | `docs/pilot_deployability_report.md` | {'complete' if pilot_deployability_rows else 'missing'} | "
            f"{_pilot_deployability_summary(pilot_deployability_report)}. |"
        ),
        (
            f"| Range-width deployability | `docs/range_width_deployability_report.md` | {'complete' if range_width_rows else 'missing'} | "
            f"{_range_width_deployability_summary(range_width_deployability_report)}. |"
        ),
        (
            f"| Small-capital decision matrix | `docs/small_capital_decision_report.md` | {'complete' if small_capital_decision_rows else 'missing'} | "
            f"{_small_capital_decision_summary(small_capital_decision_report)}. |"
        ),
        (
            f"| Alpha sensitivity | `docs/alpha_sweep.md` | {'complete' if alpha_rows else 'missing'} | "
            f"{alpha_rows} rows; default alpha rank {_alpha_rank(alpha_sweep, '1/2')}. |"
        ),
        (
            f"| Target-return thresholds | `docs/target_return_report.md` | {'complete' if target_return_rows else 'missing'} | "
            f"{target_return_rows} rows; small live 20% target {_target_return_status(target_return_report, 'live shadow', 'small active', 0.20)}. |"
        ),
        (
            f"| Route-away demand curve | `docs/route_demand_report.md` | {'complete' if route_demand_rows else 'missing'} | "
            f"{_route_demand_summary(route_demand_report)}. |"
        ),
        (
            f"| Order-splitting sensitivity | `docs/order_split_report.md` | {'complete' if order_split_rows else 'missing'} | "
            f"{order_split_rows} rows; max leakage {_rate(_max_split_leakage(order_split_report))}. |"
        ),
        (
            f"| Sequential split timing | `docs/sequential_split_report.md` | {'complete' if sequential_split_rows else 'missing'} | "
            f"{sequential_split_rows} rows; max abs leakage {_rate(_max_sequential_split_abs_leakage(sequential_split_report))}. |"
        ),
        (
            f"| TVL dilution equilibrium | `docs/tvl_dilution_report.md` | {'complete' if tvl_equilibrium_rows else 'missing'} | "
            f"{tvl_equilibrium_rows} rows; live 20% cap {_usd_or_na(_equilibrium_cap(tvl_dilution_report, 'live shadow', 0.25, 0.20))}. |"
        ),
        (
            f"| LP flow response | `docs/lp_flow_response_report.md` | {'complete' if lp_flow_rows else 'missing'} | "
            f"{_lp_flow_response_summary(lp_flow_response_report)}. |"
        ),
        (
            f"| Controlled route-away | `docs/route_away_ab.md` | {'complete' if route_ab_complete else 'missing live data'} | "
            f"{route_ab_note} |"
        ),
        "",
        "## Live Shadow Gates",
        "",
        "| Gate | Observed | Required | Passed |",
        "|---|---:|---:|---:|",
    ]
    for gate in live_status.get("gates", []):
        lines.append(
            f"| {gate.get('name', '')} | {gate.get('observed', '')} | {gate.get('required', '')} | "
            f"{'yes' if gate.get('passed') else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Route-Away Proxy Snapshot",
            "",
            f"- Total notional: {_usd(int(route_proxy.get('total_notional_e6', 0)))}",
            f"- 30 bps plus volume share: {float(route_proxy.get('high_fee_volume_share', 0)):.2%}",
            f"- Cross-pair total notional: {_usd(int(cross_pair_route_proxy.get('total_notional_e6', 0)))}",
            f"- Cross-pair 30 bps plus volume share: {float(cross_pair_route_proxy.get('high_fee_volume_share', 0)):.2%}",
            f"- Same-pair 50 bps active-depth total: {_usd(_depth_total(depth_proxy, '50'))}",
            f"- Cross-pair 50 bps active-depth total: {_usd(_depth_total(cross_pair_depth_proxy, '50'))}",
            f"- Oracle p90 staleness: {_seconds(oracle_health.get('staleness_p90_ms'))}",
            f"- Fresh fallback notional share: {_fresh_fallback_share(oracle_health):.2%}",
            f"- Lag5 net delta vs fresh: {_usd(_oracle_lag_delta(oracle_lag, 'lag5'))}",
            f"- Live max drawdown: {_usd(_live_drawdown(risk_report))}",
            f"- Live $50 drawdown stop: {_drawdown_stop_status(drawdown_stop, 'live shadow', 50_000_000)}",
            f"- Fresh missed premium from oracle fallback: {_usd(_fresh_missed_extra(fallback_attribution))}",
            f"- Worst static inventory IL: {_usd(_worst_inventory_il(inventory_report))}",
            f"- Best volatile hedge improvement: {_usd(_best_hedge_improvement(hedge_report, 'vol'))}",
            f"- Hedge execution-cost stress: {_hedge_execution_summary(hedge_execution_report)}",
            f"- Small live depth-share sample net: {_usd(_small_live_share_net(liquidity_share_report))}",
            f"- Position-level LP shadow: {_position_shadow_summary(position_shadow_report)}",
            f"- Real position replay: {_real_position_summary(real_position_report)}",
            f"- Vol charged-flow zero-net route-away tolerance: {_rate(_vol_zero_tolerance(route_break_even))}",
            f"- Worst adverse route-away gap: {_bps(_worst_adverse_gap(adverse_route_away))}",
            f"- Route-away readiness: {route_readiness_status}",
            f"- Route-away A/B power: {_route_ab_power_summary(route_ab_power_report)}",
            f"- Route-away A/B sizing: {_route_ab_sizing_summary(route_ab_sizing_report)}",
            f"- WETH/USDC $50k 5 bps route headroom: {_bps_or_na(_route_headroom(route_cost_proxy, 'WETH/USDC', 50_000_000_000))}",
            f"- Quote-route readiness: {quote_route_status}",
            f"- Quote premium headroom: {_quote_headroom_range(quote_headroom_report)}",
            f"- Cross-pair quote headroom: {_quote_headroom_range(cross_pair_quote_headroom_report)}",
            f"- Quote-headroom repeatability: {_quote_headroom_stability_summary(quote_headroom_stability_report)}",
            f"- Quote-headroom drift: {_quote_headroom_drift_summary(quote_headroom_drift_report)}",
            f"- Quote premium stress: {_quote_premium_stress_summary(quote_premium_stress_report)}",
            f"- Quote event headroom: {_quote_event_headroom_summary(quote_event_headroom_report)}",
            f"- Quote provenance audit: {_quote_provenance_summary(quote_provenance_report)}",
            f"- Quote-headroom elasticity: {_quote_elasticity_summary(quote_elasticity_report)}",
            f"- Insurance reserve solvency: {_insurance_reserve_summary(insurance_reserve_report)}",
            f"- Premium allocation frontier: {_premium_allocation_summary(premium_allocation_report)}",
            f"- Premium utilization: {_premium_utilization_summary(premium_utilization_report)}",
            f"- Charge attribution: {_charge_attribution_summary(charge_attribution_report)}",
            f"- Reserve claim-delay stress: {_reserve_delay_summary(reserve_delay_report)}",
            f"- Reserve lifecycle churn: {_reserve_lifecycle_summary(reserve_lifecycle_report)}",
            f"- Reserve tail sizing: {_reserve_tail_summary(reserve_tail_report)}",
            f"- Vol bootstrap P(net>=0): {_rate(_bootstrap_positive_net(bootstrap_report, 'vol'))}",
            f"- Vol >=$50k bucket net: {_usd(_bucket_net(size_bucket_report, 'vol', '>=$50k'))}",
            f"- Stale/missing bucket truth net: {_usd(_staleness_bucket_net(staleness_bucket_report, '>5s/missing'))}",
            f"- Market-regime segments: {_market_regime_summary(market_regime_report)}",
            f"- Signal-quality stress: {_signal_quality_stress_summary(signal_quality_stress_report)}",
            f"- Signal margin: {_signal_margin_summary(signal_margin_report)}",
            f"- Vol required base for zero net: {_pips(_base_required(base_fee_report, 'vol', 'required_base_pips_zero'))}",
            f"- Truth markout sensitivity: {_markout_sensitivity_summary(markout_sensitivity_report)}",
            f"- Vol 1 bps target routeability: {_target_viability(target_fee_report, 'vol', '1 bps net')}",
            f"- Worst capital-path drawdown: {_rate(_capital_path_worst_drawdown(capital_path_report))}",
            f"- Policy Monte Carlo: {_policy_monte_carlo_summary(policy_monte_carlo_report)}",
            f"- Risk-adjusted return: {_risk_adjusted_return_summary(risk_adjusted_return_report)}",
            f"- Chain cost matrix: {_chain_cost_summary(chain_cost_report)}",
            f"- Live gas snapshot: {_live_gas_snapshot_summary(live_gas_snapshot_report)}",
            f"- Control-plane callback cost: {_control_plane_cost_summary(control_plane_cost_report)}",
            f"- PnL attribution: {_pnl_attribution_summary(pnl_attribution_report)}",
            f"- Capital survival runway: {_capital_survival_summary(capital_survival_report)}",
            f"- Operator fixed-cost drag: {_operator_cost_summary(operator_cost_report)}",
            f"- Pilot deployability stress: {_pilot_deployability_summary(pilot_deployability_report)}",
            f"- Range-width deployability: {_range_width_deployability_summary(range_width_deployability_report)}",
            f"- Small-capital decision matrix: {_small_capital_decision_summary(small_capital_decision_report)}",
            f"- Default alpha sensitivity rank: {_alpha_rank(alpha_sweep, '1/2')}",
            f"- Small live 20% target status: {_target_return_status(target_return_report, 'live shadow', 'small active', 0.20)}",
            f"- Route-away demand curve: {_route_demand_summary(route_demand_report)}",
            f"- Max same-signal split leakage: {_rate(_max_split_leakage(order_split_report))}",
            f"- Max sequential split absolute leakage: {_rate(_max_sequential_split_abs_leakage(sequential_split_report))}",
            f"- GUARD breaker economics: {_guard_depeg_summary(guard_depeg_report)}",
            f"- GUARD stable opportunity: {_stable_opportunity_summary(stable_opportunity_report)}",
            f"- Live 20% APR dilution cap after 25% route-away: {_usd_or_na(_equilibrium_cap(tvl_dilution_report, 'live shadow', 0.25, 0.20))}",
            f"- Live convergence: {_live_convergence_summary(live_convergence_report)}",
            f"- Live maturity: {_live_maturity_summary(live_maturity_report)}",
            f"- Live sample power: {_live_power_summary(live_power_report)}",
            f"- Cross-pair live shadow: {_cross_pair_live_summary(cross_pair_live_report)}",
            f"- Live soak tracker: {_live_soak_summary(live_soak_report)}",
            f"- Cross-pair live economics: {_cross_pair_live_economics_summary(cross_pair_live_economics_report)}",
            f"- Live fee-tier shadow: {_live_fee_tier_summary(live_fee_tier_report)}",
            f"- Route-away baseline-flow probe: {_route_baseline_probe_summary(route_baseline_probe_report)}",
            f"- Route-away A/A placebo: {_route_away_placebo_ab_summary(route_away_placebo_ab_report)}",
            "",
            "## Controlled Route-Away Input",
            "",
            f"- Preflight status: {route_readiness_status}",
            f"- Missing preflight inputs: {_missing_inputs(route_readiness)}",
            f"- Existing route-away artifact: {route_ab_note}",
            f"- Pre/post live windows populated: {'yes' if route_ab_complete else 'no'}",
            f"- Routed-away rate: {float(route_ab.get('route_away_rate', 0)):.2%}",
            "",
            "## Quote Route Input",
            "",
            f"- Preflight status: {quote_route_status}",
            f"- Missing preflight inputs: {_missing_quote_inputs(quote_route_readiness)}",
            f"- Quote result complete: {'yes' if quote_route_readiness.get('quote_result_complete') else 'no'}",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(
    out_md: Path,
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
    cross_pair_live_report: dict | None = None,
    live_soak_report: dict | None = None,
    cross_pair_live_economics_report: dict | None = None,
    live_fee_tier_report: dict | None = None,
    premium_utilization_report: dict | None = None,
    charge_attribution_report: dict | None = None,
    route_share_stability_report: dict | None = None,
    route_away_placebo_ab_report: dict | None = None,
    route_ab_power_report: dict | None = None,
    route_ab_sizing_report: dict | None = None,
    route_baseline_probe_report: dict | None = None,
    guard_depeg_report: dict | None = None,
    stable_opportunity_report: dict | None = None,
    market_regime_report: dict | None = None,
    signal_quality_stress_report: dict | None = None,
    signal_margin_report: dict | None = None,
) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(
        markdown(
            live_status,
            route_proxy,
            route_ab,
            cross_pair_route_proxy,
            depth_proxy,
            cross_pair_depth_proxy,
            oracle_health,
            oracle_lag,
            risk_report,
            drawdown_stop,
            fallback_attribution,
            inventory_report,
            hedge_report,
            hedge_execution_report,
            liquidity_share_report,
            route_break_even,
            adverse_route_away,
            bootstrap_report,
            size_bucket_report,
            staleness_bucket_report,
            base_fee_report,
            target_fee_report,
            capital_path_report,
            policy_monte_carlo_report,
            risk_adjusted_return_report,
            chain_cost_report,
            live_gas_snapshot_report,
            control_plane_cost_report,
            pnl_attribution_report,
            capital_survival_report,
            operator_cost_report,
            alpha_sweep,
            target_return_report,
            route_readiness,
            order_split_report,
            tvl_dilution_report,
            route_cost_proxy,
            sequential_split_report,
            quote_route_readiness,
            quote_headroom_report,
            cross_pair_quote_headroom_report,
            quote_headroom_stability_report,
            quote_headroom_drift_report,
            quote_premium_stress_report,
            quote_event_headroom_report,
            quote_provenance_report,
            quote_elasticity_report,
            insurance_reserve_report,
            premium_allocation_report,
            reserve_delay_report,
            reserve_lifecycle_report,
            reserve_tail_report,
            route_demand_report,
            markout_sensitivity_report,
            pilot_deployability_report,
            range_width_deployability_report,
            position_shadow_report,
            small_capital_decision_report,
            real_position_report,
            real_position_portfolio_report,
            headline_uncertainty_report,
            lp_flow_response_report,
            live_convergence_report=live_convergence_report,
            live_maturity_report=live_maturity_report,
            live_power_report=live_power_report,
            cross_pair_live_report=cross_pair_live_report,
            live_soak_report=live_soak_report,
            cross_pair_live_economics_report=cross_pair_live_economics_report,
            live_fee_tier_report=live_fee_tier_report,
            premium_utilization_report=premium_utilization_report,
            charge_attribution_report=charge_attribution_report,
            route_share_stability_report=route_share_stability_report,
            route_away_placebo_ab_report=route_away_placebo_ab_report,
            route_ab_power_report=route_ab_power_report,
            route_ab_sizing_report=route_ab_sizing_report,
            route_baseline_probe_report=route_baseline_probe_report,
            guard_depeg_report=guard_depeg_report,
            stable_opportunity_report=stable_opportunity_report,
            market_regime_report=market_regime_report,
            signal_quality_stress_report=signal_quality_stress_report,
            signal_margin_report=signal_margin_report,
        ),
        encoding="utf-8",
    )


def _route_ab_events(route_ab: dict) -> int:
    return 2 if route_ab and not _route_ab_errors(route_ab) else 0


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


def _route_ab_note(route_ab: dict, errors: list[str] | None = None) -> str:
    if not route_ab:
        return "controlled route-away artifact missing"
    errors = _route_ab_errors(route_ab) if errors is None else errors
    if errors:
        return "invalid input: " + _summarize_errors(errors)
    return "valid=true controlled result artifact with collection metadata, matching notionals, and derived route-away fields"


def _summarize_errors(errors: list[str], limit: int = 4) -> str:
    shown = errors[:limit]
    suffix = f"; +{len(errors) - limit} more" if len(errors) > limit else ""
    return "; ".join(shown) + suffix


def _route_share_stability_summary(report: dict) -> str:
    if not report:
        return "missing route-share stability report"
    pairs = sorted({str(row.get("pair", "")) for row in report.get("pair_summaries", []) if row.get("pair")})
    return (
        f"pairs={','.join(pairs) or 'none'}, "
        f"max 5bps spread {float(report.get('max_5bps_spread_pp', 0)):.2f} pp, "
        f"max high-fee spread {float(report.get('max_high_fee_spread_pp', 0)):.2f} pp"
    )


def _route_away_placebo_ab_summary(report: dict) -> str:
    if not report:
        return "missing route-away A/A placebo report"
    pairs = sorted({str(row.get("pair", "")) for row in report.get("rows", []) if row.get("pair")})
    return (
        f"pairs={','.join(pairs) or 'none'}, "
        f"max false route-away {_rate(report.get('max_false_route_away_rate'))}, "
        f"max abs share shift {float(report.get('max_abs_share_shift_pp', 0)):.2f} pp"
    )


def _route_ab_power_summary(report: dict) -> str:
    if not report:
        return "missing route-away A/B power report"
    mde_rows = report.get("mde_rows", [])
    economic_rows = report.get("economic_rows", [])
    usable = sum(1 for row in mde_rows if str(row.get("status", "")) == "usable")
    before_break_even = sum(
        1 for row in economic_rows if str(row.get("interpretation", "")) == "detectable before modeled break-even"
    )
    pairs = sorted({str(row.get("pair", "")) for row in mde_rows if row.get("pair")})
    return (
        f"pairs={','.join(pairs) or 'none'}, usable MDE rows {usable}/{len(mde_rows)}, "
        f"before break-even {before_break_even}/{len(economic_rows)}"
    )


def _route_ab_sizing_summary(report: dict) -> str:
    if not report:
        return "missing route-away A/B sizing report"
    candidates = report.get("candidate_rows", [])
    recommendations = report.get("recommendations", [])
    pairs = sorted({str(row.get("pair", "")) for row in report.get("proxy_rows", []) if row.get("pair")})
    best_hours = min(
        (
            float(row.get("hours_for_target_treatment_notional"))
            for row in recommendations
            if row.get("hours_for_target_treatment_notional") is not None
        ),
        default=None,
    )
    target = int(report.get("target_treatment_notional_e6", 0))
    best = "n/a" if best_hours is None else f"{best_hours:.1f}h"
    return (
        f"pairs={','.join(pairs) or 'none'}, candidates {len(candidates)}, "
        f"recommendations {len(recommendations)}, {_usd(target)} target best window {best}"
    )


def _route_readiness_notes(route_readiness: dict) -> str:
    if not route_readiness:
        return "preflight report not generated"
    if route_readiness.get("controlled_result_complete"):
        return "controlled result artifact already has nonzero pre/post notional"
    if route_readiness.get("ready_to_collect"):
        return "collector inputs are present; run the controlled route-away collector"
    missing = route_readiness.get("missing_inputs", [])
    failed = route_readiness.get("failed_validations", [])
    notes = []
    if missing:
        notes.append("missing " + ", ".join(str(item) for item in missing))
    if failed:
        notes.append("failed " + ", ".join(str(item) for item in failed))
    return "; ".join(notes) or "waiting for pre/post route-away input"


def _quote_route_notes(quote_route_readiness: dict) -> str:
    if not quote_route_readiness:
        return "preflight report not generated"
    if quote_route_readiness.get("quote_result_complete"):
        quoted = int(quote_route_readiness.get("quoted_rows", 0))
        total = int(quote_route_readiness.get("quote_rows", 0))
        return f"real quote result artifact has quoted rows ({quoted}/{total})"
    if quote_route_readiness.get("ready_to_collect"):
        return "quote collector inputs are present; run the quote collector"
    missing = quote_route_readiness.get("missing_inputs", [])
    failed = quote_route_readiness.get("failed_validations", [])
    notes = []
    if missing:
        notes.append("missing " + ", ".join(str(item) for item in missing))
    if failed:
        notes.append("failed " + ", ".join(str(item) for item in failed))
    return "; ".join(notes) or "waiting for quote-route inputs"


def _missing_inputs(route_readiness: dict) -> str:
    missing = route_readiness.get("missing_inputs", [])
    if not missing:
        return "none"
    return ", ".join(str(item) for item in missing)


def _missing_quote_inputs(quote_route_readiness: dict) -> str:
    missing = quote_route_readiness.get("missing_inputs", [])
    if not missing:
        return "none"
    return ", ".join(str(item) for item in missing)


def _equilibrium_cap(tvl_dilution_report: dict, window: str, route_away: float, target_apr: float) -> int | None:
    for row in tvl_dilution_report.get("equilibrium_rows", []):
        if (
            row.get("window") == window
            and abs(float(row.get("route_away", 0)) - route_away) < 1e-9
            and abs(float(row.get("target_apr", 0)) - target_apr) < 1e-9
        ):
            value = row.get("max_active_capital_e6")
            return None if value is None else int(value)
    return None


def _lp_flow_response_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no adaptive-capital rows"
    paths = sorted({str(row.get("path", "")) for row in rows if row.get("path")})
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    max_outflow_days = max((int(row.get("outflow_days", 0)) for row in rows), default=0)
    worst_drawdown = min((float(row.get("max_drawdown", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows across {len(paths)} paths; statuses={','.join(statuses) or 'none'}; "
        f"max outflow days {max_outflow_days}; worst drawdown {_rate(worst_drawdown)}"
    )


def _live_convergence_summary(report: dict) -> str:
    rows = report.get("convergence_rows", [])
    if not rows:
        return "no live convergence buckets"
    fallback_notional = sum(int(row.get("fallback_notional_e6", 0)) for row in rows)
    notional = sum(int(row.get("notional_e6", 0)) for row in rows)
    fallback_share = (fallback_notional / notional) if notional else None
    return (
        f"{len(rows)} buckets; precision {_rate(report.get('precision'))}; "
        f"capture {_rate(report.get('capture_truth'))}; net {_bps(float(report.get('net_bps', 0.0)))}; "
        f"fallback share {_rate(fallback_share)}"
    )


def _live_maturity_summary(report: dict) -> str:
    rows = report.get("maturity_rows", [])
    if not rows:
        return "no live maturity checkpoints"
    return (
        f"{len(rows)} checkpoints; precision {_rate(report.get('precision'))}; "
        f"capture {_rate(report.get('capture_truth'))}; net {_bps(float(report.get('net_bps', 0.0)))}; "
        f"max capture drift {_rate(report.get('max_abs_capture_delta'))}; "
        f"max net drift {_bps(report.get('max_abs_net_bps_delta'))}"
    )


def _live_power_summary(report: dict) -> str:
    metrics = report.get("metrics", [])
    if not metrics:
        return "no live power metrics"
    statuses = sorted({str(row.get("status", "")) for row in metrics if row.get("status")})
    max_additional = max(
        (
            float(row.get("additional_hours_needed", 0))
            for row in metrics
            if row.get("additional_hours_needed") is not None
        ),
        default=0.0,
    )
    net_half_width = next(
        (row.get("ci95_half_width") for row in metrics if row.get("metric") == "net_bps"),
        None,
    )
    return (
        f"{int(report.get('bucket_count', 0))} buckets; span {float(report.get('observed_span_hours', 0)):.2f}h; "
        f"net 95% half-width {_bps(net_half_width)}; max additional {max_additional:.1f}h; "
        f"statuses={','.join(statuses) or 'none'}"
    )


def _cross_pair_live_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no cross-pair live rows"
    summaries = []
    for row in rows:
        summaries.append(
            f"{row.get('pair', 'n/a')} {int(row.get('swaps', 0))} swaps/"
            f"{float(row.get('observed_span_hours', 0)):.2f}h/"
            f"{_rate(row.get('truth_coverage'))} truth"
        )
    return "; ".join(summaries)


def _live_soak_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no live soak rows"
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    horizons = sorted({float(row.get("horizon_hours", 0)) for row in rows if row.get("horizon_hours") is not None})
    complete_rows = sum(1 for row in rows if row.get("complete"))
    spans = []
    for pair in pairs:
        pair_rows = [row for row in rows if row.get("pair") == pair]
        if not pair_rows:
            continue
        span = max(float(row.get("observed_span_hours", 0)) for row in pair_rows)
        truth = max(float(row.get("truth_coverage", 0)) for row in pair_rows)
        spans.append(f"{pair} {span:.2f}h/{_rate(truth)} truth")
    horizon_text = ",".join(_format_horizon(hours) for hours in horizons) or "none"
    return f"{len(rows)} rows; horizons={horizon_text}; complete {complete_rows}/{len(rows)}; " + "; ".join(spans)


def _cross_pair_live_economics_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no cross-pair live economics rows"
    parts = []
    complete = sum(1 for row in rows if row.get("complete"))
    for row in rows:
        parts.append(
            f"{row.get('pair', 'n/a')} {int(row.get('rows', 0))} rows/"
            f"{float(row.get('observed_span_hours', 0)):.2f}h/"
            f"precision {_rate(row.get('precision'))}/"
            f"capture {_rate(row.get('capture_truth'))}/"
            f"net {_bps(row.get('net_bps'))}"
        )
    return f"complete {complete}/{len(rows)}; " + "; ".join(parts)


def _live_fee_tier_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no fee-tier live-shadow rows"
    parts = []
    complete = sum(1 for row in rows if row.get("complete"))
    for row in rows:
        fee_bps = int(row.get("fee_pips", 0)) / 100
        parts.append(
            f"{row.get('pair', 'n/a')} {fee_bps:.2f} bps {int(row.get('swaps', 0))} swaps/"
            f"{float(row.get('observed_span_hours', 0)):.2f}h/"
            f"{row.get('quality_status', 'n/a')}/"
            f"precision {_rate(row.get('precision'))}/"
            f"capture {_rate(row.get('capture_truth'))}/"
            f"net {_bps(row.get('net_bps'))}"
        )
    return f"measurable {complete}/{len(rows)}; " + "; ".join(parts)


def _live_fee_tier_status(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "missing"
    complete = sum(1 for row in rows if row.get("complete"))
    if complete == len(rows):
        return "complete"
    if complete > 0:
        return "measurable"
    return "in progress"


def _format_horizon(hours: float) -> str:
    return "7d" if abs(hours - 168.0) < 1e-9 else f"{hours:.0f}h"


def _route_baseline_probe_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no baseline probe rows"
    parts = []
    for row in rows:
        windows = row.get("windows", [])
        if windows:
            swaps = sum(int(window.get("swaps", 0)) for window in windows)
            notional = sum(int(window.get("quote_notional_e6", 0)) for window in windows)
            parts.append(f"{row.get('pair', 'n/a')} {swaps} swaps/{_usd(notional)}")
        else:
            parts.append(f"{row.get('pair', 'n/a')} planned {int(row.get('window_blocks', 0))} blocks")
    prefix = "executed" if report.get("executed") else "planned"
    return f"{prefix}; " + "; ".join(parts)


def _guard_depeg_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "no GUARD breaker rows"
    selected = next((row for row in rows if row.get("label") == "selected"), rows[0])
    lead = selected.get("lead_time_before_measured_bleed_sec")
    before = selected.get("bled_before_first_trigger_e6")
    after = selected.get("measured_bleed_after_first_trigger_e6")
    return (
        f"calm triggers {int(selected.get('calm_triggers', 0))}; "
        f"vol triggers {int(selected.get('vol_triggers', 0))}; "
        f"lead {_plain_seconds(lead)}; before {_usd_or_na(before)}; after {_usd_or_na(after)}"
    )


def _stable_opportunity_summary(report: dict) -> str:
    if not report.get("rows"):
        return "no stable opportunity rows"
    return (
        f"policy {report.get('directional_fee_policy', 'n/a')}; "
        f"normal max {float(report.get('normal_stable_max_bps', 0)):.2f} bps; "
        f"best capture {float(report.get('best_directional_capture_pct', 0)):.2%}; "
        f"trip margin {float(report.get('trip_to_normal_ratio', 0)):.1f}x"
    )


def _plain_seconds(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value)}s"


def _route_headroom(route_cost_proxy: dict, pair: str, trade_size_e6: int) -> float | None:
    for row in route_cost_proxy.get("rows", []):
        if (
            row.get("pair") == pair
            and int(row.get("trade_size_e6", 0)) == trade_size_e6
            and int(row.get("fee_pips", 0)) == 500
        ):
            value = row.get("pegguard_headroom_bps")
            return None if value is None else float(value)
    return None


def _quote_headroom_range(quote_headroom_report: dict) -> str:
    values = [
        float(row.get("premium_headroom_bps", 0))
        for row in quote_headroom_report.get("rows", [])
        if row.get("premium_headroom_bps") is not None
    ]
    if not values:
        return "headroom n/a"
    positive = sum(1 for value in values if value > 0)
    return f"headroom min {min(values):.4f} bps, max {max(values):.4f} bps, positive {positive}/{len(values)}"


def _quote_headroom_stability_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "repeat rows n/a"
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    passed = sum(1 for row in rows if row.get("passed"))
    return (
        f"{passed}/{len(rows)} rows across {','.join(pairs) or 'none'}; "
        f"min repeat {_bps_or_na(report.get('min_repeat_headroom_bps'))}; "
        f"max abs delta {_bps_or_na(report.get('max_abs_delta_headroom_bps'))}"
    )


def _quote_headroom_drift_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "drift rows n/a"
    pairs = sorted({str(row.get("pair", "")) for row in rows if row.get("pair")})
    passed = int(report.get("passed_rows", 0))
    block_count = int(report.get("distinct_block_count", 0))
    sample_count = int(report.get("sample_count", 0))
    return (
        f"{passed}/{len(rows)} rows across {','.join(pairs) or 'none'}; "
        f"samples {sample_count}; blocks {block_count}; "
        f"min headroom {_bps_or_na(report.get('min_headroom_bps'))}; "
        f"max drift {_bps_or_na(report.get('max_abs_first_to_last_delta_bps'))}"
    )


def _quote_premium_stress_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "stress rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    over_rows = sum(int(row.get("over_headroom_rows", 0)) for row in rows)
    excess = sum(int(row.get("excess_e6", 0)) for row in rows)
    max_share = max(
        (float(row.get("excess_share_of_extra", 0)) for row in rows if row.get("excess_share_of_extra") is not None),
        default=0.0,
    )
    return f"{len(rows)} rows across {','.join(windows) or 'none'}; over budget rows {over_rows}; excess {_usd(excess)}; max excess share {max_share:.2%}"


def _quote_event_headroom_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "event-headroom rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    over_rows = sum(int(row.get("over_budget_rows", 0)) for row in rows)
    excess = sum(int(row.get("excess_e6", 0)) for row in rows)
    max_share = max(
        (float(row.get("excess_share_of_extra", 0)) for row in rows if row.get("excess_share_of_extra") is not None),
        default=0.0,
    )
    above_max = sum(int(row.get("above_max_quote_rows", 0)) for row in rows)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; "
        f"over budget rows {over_rows}; above max quote {above_max}; "
        f"excess {_usd(excess)}; max excess share {max_share:.2%}"
    )


def _quote_provenance_summary(report: dict) -> str:
    artifacts = report.get("artifacts", [])
    if not artifacts:
        return "quote provenance artifacts n/a"
    present = int(report.get("present_count", 0))
    total = int(report.get("artifact_count", len(artifacts)))
    quoted = int(report.get("quoted_rows", 0))
    rows = int(report.get("total_quote_rows", 0))
    latest = int(report.get("latest_block_tag_artifacts", 0))
    pinned = int(report.get("pinned_block_artifacts", 0))
    missing_generated_at = int(report.get("missing_generated_at_artifacts", 0))
    warnings = len(report.get("warnings", []))
    return (
        f"{present}/{total} artifacts; quoted {quoted}/{rows}; "
        f"pinned {pinned}; latest {latest}; missing generated_at {missing_generated_at}; warnings {warnings}"
    )


def _quote_elasticity_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "elasticity rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    margins = sorted({float(row.get("budget_margin", 0)) for row in rows})
    max_loss = max((float(row.get("lost_share_of_extra", 0)) for row in rows if row.get("lost_share_of_extra") is not None), default=0.0)
    max_lost = max((int(row.get("lost_extra_e6", 0)) for row in rows), default=0)
    margin_text = ",".join(f"{margin:.0%}" for margin in margins) or "none"
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; margins {margin_text}; "
        f"max lost share {max_loss:.2%}; max lost {_usd(max_lost)}"
    )


def _insurance_reserve_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "reserve rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_seed = max((int(row.get("max_deficit_e6", 0)) for row in rows), default=0)
    min_coverage = min(
        (float(row.get("coverage_ratio", 0)) for row in rows if row.get("coverage_ratio") is not None),
        default=None,
    )
    charged_100 = _reserve_row(rows, "vol", "charged correcting markout", 1.0)
    charged_note = ""
    if charged_100:
        charged_note = f"; vol charged 100% coverage {_ratio(charged_100.get('coverage_ratio'))}"
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; max seed {_usd(max_seed)}; "
        f"min coverage {_ratio(min_coverage)}{charged_note}"
    )


def _reserve_lifecycle_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "lifecycle rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    failures = sum(1 for row in rows if not row.get("survived_without_topup"))
    max_topup = max((int(row.get("required_topup_e6", 0)) for row in rows), default=0)
    max_withdrawal_share = max(
        (
            float(row.get("withdrawal_share_of_premium", 0))
            for row in rows
            if row.get("withdrawal_share_of_premium") is not None
        ),
        default=0.0,
    )
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; failures {failures}; "
        f"max top-up {_usd(max_topup)}; max withdrawal/premium {_rate(max_withdrawal_share)}"
    )


def _premium_allocation_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "allocation rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_seed = max((int(row.get("reserve_required_seed_e6", 0)) for row in rows), default=0)
    solvent = sum(1 for row in rows if row.get("reserve_unseeded_solvent"))
    min_lp_bps = min((float(row.get("lp_net_before_claims_bps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; unseeded solvent {solvent}; "
        f"max seed {_usd(max_seed)}; min LP net {_bps(min_lp_bps)}"
    )


def _premium_utilization_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "utilization rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_cap_hits = max((int(row.get("cap_hit_rows", 0)) for row in rows), default=0)
    max_near_cap = max((int(row.get("near_cap_rows", 0)) for row in rows), default=0)
    min_precision = min(
        (float(row.get("precision", 0)) for row in rows if row.get("precision") is not None),
        default=None,
    )
    max_top_share = max(
        (float(row.get("top_10pct_extra_share", 0)) for row in rows if row.get("top_10pct_extra_share") is not None),
        default=None,
    )
    max_p99 = max(
        (float(row.get("p99_charged_premium_bps", 0)) for row in rows if row.get("p99_charged_premium_bps") is not None),
        default=None,
    )
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; "
        f"min precision {_rate(min_precision)}; p99 max {_bps(max_p99)}; "
        f"cap hits max {max_cap_hits}; near cap max {max_near_cap}; top 10% extra max {_rate(max_top_share)}"
    )


def _charge_attribution_summary(report: dict) -> str:
    windows = report.get("windows", [])
    if not windows:
        return "charge-attribution windows n/a"
    names = sorted({str(row.get("window", "")) for row in windows if row.get("window")})
    min_precision = min(
        (float(row.get("precision", 0)) for row in windows if row.get("precision") is not None),
        default=None,
    )
    max_false_share = max(
        (float(row.get("false_charge_extra_share", 0)) for row in windows if row.get("false_charge_extra_share") is not None),
        default=None,
    )
    max_missed = max((int(row.get("missed_correcting_abs_markout_e6", 0)) for row in windows), default=0)
    min_markout_coverage = min(
        (
            float(row.get("truth_correcting_markout_coverage", 0))
            for row in windows
            if row.get("truth_correcting_markout_coverage") is not None
        ),
        default=None,
    )
    return (
        f"{len(windows)} windows across {','.join(names) or 'none'}; "
        f"min precision {_rate(min_precision)}; max false-charge extra {_rate(max_false_share)}; "
        f"min correcting markout coverage {_rate(min_markout_coverage)}; max missed correcting markout {_usd(max_missed)}"
    )


def _reserve_delay_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "delay rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_economic_seed = max((int(row.get("required_economic_seed_e6", 0)) for row in rows), default=0)
    max_hidden_gap = max((int(row.get("hidden_liability_gap_e6", 0)) for row in rows), default=0)
    econ_failures = sum(1 for row in rows if not row.get("economically_solvent_without_seed"))
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; econ failures {econ_failures}; "
        f"max economic seed {_usd(max_economic_seed)}; max hidden gap {_usd(max_hidden_gap)}"
    )


def _reserve_tail_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "tail rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    worst_p99 = max((int(row.get("p99_seed_e6", 0)) for row in rows), default=0)
    worst_cvar = max((int(row.get("cvar95_seed_e6", 0)) for row in rows), default=0)
    vol_charged = _reserve_row(rows, "vol", "charged correcting markout", 1.0)
    charged_note = ""
    if vol_charged:
        charged_note = f"; vol charged 100% p99 {_usd(int(vol_charged.get('p99_seed_e6', 0)))}"
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; "
        f"worst p99 seed {_usd(worst_p99)}; worst CVaR95 {_usd(worst_cvar)}{charged_note}"
    )


def _reserve_row(rows: list[dict], window: str, claim_basis: str, payout_rate: float) -> dict | None:
    for row in rows:
        if (
            row.get("window") == window
            and row.get("claim_basis") == claim_basis
            and abs(float(row.get("payout_rate", 0)) - payout_rate) < 1e-9
        ):
            return row
    return None


def _usd(value_e6: int) -> str:
    return f"${value_e6 / 1_000_000:,.2f}"


def _usd_or_na(value_e6: int | None) -> str:
    if value_e6 is None:
        return "n/a"
    return _usd(value_e6)


def _depth_total(depth_proxy: dict, band: str) -> int:
    return int(depth_proxy.get("band_totals", {}).get(band, 0))


def _fresh_fallback_share(oracle_health: dict) -> float:
    for row in oracle_health.get("decisions", []):
        if row.get("label") == "fresh":
            return float(row.get("fallback_notional_share", 0))
    return 0.0


def _oracle_lag_delta(oracle_lag: dict, label: str) -> int:
    for row in oracle_lag.get("rows", []):
        if row.get("label") == label:
            return int(row.get("delta_net_vs_fresh_e6", 0))
    return 0


def _live_drawdown(risk_report: dict) -> int:
    for row in risk_report.get("windows", []):
        if row.get("window") == "live shadow":
            return int(row.get("max_drawdown_e6", 0))
    return 0


def _drawdown_stop_status(drawdown_stop: dict, window: str, threshold_e6: int) -> str:
    for row in drawdown_stop.get("rows", []):
        if row.get("window") == window and int(row.get("threshold_e6", 0)) == threshold_e6:
            triggered = "triggered" if row.get("triggered") else "not triggered"
            return f"{triggered}, delta {_usd(int(row.get('delta_vs_full_e6', 0)))}"
    return "n/a"


def _fresh_missed_extra(fallback_attribution: dict) -> int:
    for row in fallback_attribution.get("labels", []):
        if row.get("label") == "fresh":
            return int(row.get("missed_extra_e6", 0))
    return 0


def _worst_inventory_il(inventory_report: dict) -> int:
    rows = inventory_report.get("windows", [])
    if not rows:
        return 0
    return min(int(row.get("inventory_il_e6", 0)) for row in rows)


def _best_hedge_improvement(hedge_report: dict, window: str) -> int:
    rows = [row for row in hedge_report.get("rows", []) if row.get("window") == window]
    if not rows:
        return 0
    return max(int(row.get("hedge_improvement_e6", 0)) for row in rows)


def _hedge_execution_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "execution rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    scenarios = sorted({str(row.get("scenario", "")) for row in rows if row.get("scenario")})
    improving = sum(1 for row in rows if row.get("status") == "improves after costs")
    infeasible = sum(1 for row in rows if row.get("status") == "operationally infeasible")
    best_vol = max(
        (int(row.get("hedge_improvement_e6", 0)) for row in rows if row.get("window") == "vol"),
        default=0,
    )
    worst = min((int(row.get("hedge_improvement_e6", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; scenarios {len(scenarios)}; "
        f"improves {improving}; infeasible {infeasible}; best vol {_usd(best_vol)}; worst {_usd(worst)}"
    )


def _small_live_share_net(liquidity_share_report: dict) -> int:
    for row in liquidity_share_report.get("rows", []):
        if row.get("window") == "live shadow" and int(row.get("capital_e6", 0)) == 10_000_000_000:
            return int(row.get("pro_rata_net_e6", 0))
    return 0


def _position_shadow_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "position rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    combined = sum(1 for row in rows if row.get("combined_net_e6") is not None)
    provisional = sum(1 for row in rows if row.get("combined_net_e6") is None)
    worst = report.get("worst_combined_net_e6")
    best = report.get("best_combined_net_e6")
    small_vol = _position_combined_net(report, "vol", "static +/-3%", 10_000_000_000)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; combined {combined}; "
        f"provisional {provisional}; worst {_usd_or_na(None if worst is None else int(worst))}; "
        f"best {_usd_or_na(None if best is None else int(best))}; "
        f"$10k +/-3% vol {_usd_or_na(small_vol)}"
    )


def _position_combined_net(report: dict, window: str, range_policy: str, capital_e6: int) -> int | None:
    for row in report.get("rows", []):
        if (
            row.get("window") == window
            and row.get("range_policy") == range_policy
            and int(row.get("capital_e6", 0)) == capital_e6
        ):
            value = row.get("combined_net_e6")
            return None if value is None else int(value)
    return None


def _real_position_summary(report: dict) -> str:
    rows = report.get("rows", [])
    status = str(report.get("status", "missing input"))
    if rows:
        row = rows[0]
        position_id = str(row.get("position_id", report.get("target_position_id", "n/a")))
        net = int(row.get("net_vs_hodl_e6", 0))
        bps = float(row.get("net_vs_hodl_bps", 0))
        return f"status {status}; position {position_id}; net {_usd(net)}; net {bps:.2f} bps"
    missing = report.get("missing_fields", [])
    missing_text = ",".join(str(field) for field in missing) or "input artifact"
    return f"status {status}; missing {missing_text}"


def _real_position_portfolio_summary(report: dict) -> str:
    summary = report.get("summary", {})
    breadth = report.get("breadth", {})
    positions = int(summary.get("complete_positions", 0))
    required = int(report.get("min_audited_positions", 3))
    net = int(summary.get("net_vs_hodl_e6", 0))
    bps = float(summary.get("net_vs_hodl_bps", 0))
    return (
        f"{positions}/{required} positions; pairs={int(breadth.get('pool_pairs', 0))}; "
        f"fee tiers={int(breadth.get('fee_tiers', 0))}; range statuses={int(breadth.get('range_statuses', 0))}; "
        f"net {_usd(net)}; net {bps:.2f} bps"
    )


def _vol_zero_tolerance(route_break_even: dict) -> float | None:
    for row in route_break_even.get("rows", []):
        if row.get("window") == "vol":
            value = row.get("charged_flow_zero_rate")
            return None if value is None else float(value)
    return None


def _adverse_route_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "stress rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    return f"{len(rows)} rows across {','.join(windows) or 'none'}; worst gap {_bps(_worst_adverse_gap(report))}"


def _worst_adverse_gap(report: dict) -> float | None:
    rows = report.get("rows", [])
    if not rows:
        return None
    return min(float(row.get("adverse_gap_bps", 0)) for row in rows)


def _bootstrap_positive_net(bootstrap_report: dict, window: str) -> float | None:
    for row in bootstrap_report.get("windows", []):
        if row.get("window") == window:
            value = row.get("positive_net_probability")
            return None if value is None else float(value)
    return None


def _headline_uncertainty_summary(report: dict) -> str:
    vol_capture_p05 = None
    for row in report.get("windows", []):
        if row.get("window") == "vol":
            value = row.get("capture_p05")
            vol_capture_p05 = None if value is None else float(value)
            break
    small_active_apr_p50 = None
    for row in report.get("policies", []):
        if row.get("window") == "calm" and row.get("policy") == "small active":
            value = row.get("net_apr_p50")
            small_active_apr_p50 = None if value is None else float(value)
            break
    return f"vol capture p05 {_rate(vol_capture_p05)}, calm small-active APR p50 {_rate(small_active_apr_p50)}"


def _bucket_net(size_bucket_report: dict, window: str, bucket: str) -> int:
    for row in size_bucket_report.get("rows", []):
        if row.get("window") == window and row.get("bucket") == bucket:
            return int(row.get("net_e6", 0))
    return 0


def _staleness_bucket_net(staleness_bucket_report: dict, bucket: str) -> int:
    for row in staleness_bucket_report.get("buckets", []):
        if row.get("bucket") == bucket:
            return int(row.get("truth_net_e6", 0))
    return 0


def _market_regime_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "missing"
    windows = ",".join(sorted({str(row.get("window", "")) for row in rows if row.get("window")}))
    high_vol = _market_regime_net(report, "live shadow", "high-vol >=5bp")
    oracle_lag = _market_regime_net(report, "live shadow", "oracle-lag/fallback")
    return f"{len(rows)} rows; windows={windows}; live high-vol net {_usd(high_vol)}; oracle-lag net {_usd(oracle_lag)}"


def _market_regime_net(report: dict, window: str, segment: str) -> int:
    for row in report.get("rows", []):
        if row.get("window") == window and row.get("segment") == segment:
            return int(row.get("net_e6", 0))
    return 0


def _signal_quality_stress_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "signal-quality rows n/a"
    windows = ",".join(sorted({str(row.get("window", "")) for row in rows if row.get("window")}))
    broken = sum(1 for row in rows if row.get("status") == "precision broken")
    worst_aligned = min((float(row.get("aligned_net_bps", 0)) for row in rows), default=0.0)
    max_gap = max((float(row.get("raw_minus_aligned_bps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; windows={windows}; precision-broken={broken}; "
        f"worst aligned net {_bps(worst_aligned)}; max raw/aligned gap {_bps(max_gap)}"
    )


def _signal_margin_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "signal-margin rows n/a"
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
        f"{len(rows)} rows; windows={windows}; min precision headroom {min_headroom * 100:.2f} pp; "
        f"max missed-correct tolerance {_rate(max_missed)}; below break-even={negative}"
    )


def _base_required(base_fee_report: dict, window: str, key: str) -> int:
    for row in base_fee_report.get("rows", []):
        if row.get("window") == window:
            return int(row.get(key, 0))
    return 0


def _markout_sensitivity_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    worst_net = min((float(row.get("net_bps", 0)) for row in rows), default=0.0)
    max_required = max((int(row.get("required_base_pips_zero", 0)) for row in rows), default=0)
    return f"{len(rows)} rows across {','.join(windows) or 'none'}; worst net {worst_net:.2f} bps; max zero-net base {_pips(max_required)}"


def _pips(value: int) -> str:
    return f"{value / 100:.2f} bps"


def _bps_or_na(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f} bps"


def _bps(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f} bps"


def _target_viability(target_fee_report: dict, window: str, target: str) -> str:
    for row in target_fee_report.get("rows", []):
        if row.get("window") == window and row.get("target") == target:
            return str(row.get("viability", "n/a"))
    return "n/a"


def _capital_path_worst_drawdown(capital_path_report: dict) -> float | None:
    rows = capital_path_report.get("rows", [])
    if not rows:
        return None
    return min(float(row.get("max_drawdown", 0)) for row in rows)


def _policy_monte_carlo_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "Monte Carlo rows n/a"
    mixes = sorted({str(row.get("mix", "")) for row in rows if row.get("mix")})
    max_loss = max((float(row.get("probability_loss", 0)) for row in rows), default=0.0)
    max_drawdown = max((float(row.get("probability_drawdown_gt_1pct", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows across {','.join(mixes) or 'none'}; "
        f"max P(loss) {_rate(max_loss)}; max P(dd>1%) {_rate(max_drawdown)}"
    )


def _risk_adjusted_return_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "risk-adjusted rows n/a"
    mixes = sorted({str(row.get("mix", "")) for row in rows if row.get("mix")})
    viable = sum(1 for row in rows if row.get("status") == "risk-adjusted viable")
    max_loss_day = max((float(row.get("loss_day_probability", 0)) for row in rows), default=0.0)
    min_sortino = min(
        (float(row["sortino_like"]) for row in rows if row.get("sortino_like") is not None),
        default=0.0,
    )
    return (
        f"{len(rows)} rows across {','.join(mixes) or 'none'}; viable={viable}; "
        f"max loss-day {_rate(max_loss_day)}; min sortino {min_sortino:.2f}"
    )


def _chain_cost_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "chain rows n/a"
    chains = sorted({str(row.get("chain", "")) for row in rows if row.get("chain")})
    min_net = min((float(row.get("net_after_chain_cost_bps", 0)) for row in rows), default=0.0)
    max_gas = max((float(row.get("gas_bps", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows across {','.join(chains) or 'none'}; min net {_bps(min_net)}; max gas {_bps(max_gas)}"


def _live_gas_snapshot_summary(report: dict) -> str:
    rows = report.get("rows", [])
    snapshots = report.get("snapshots", [])
    if not rows and not snapshots:
        return "live gas rows n/a"
    ok = sum(1 for row in snapshots if row.get("ok"))
    chains = sorted({str(row.get("chain", "")) for row in snapshots if row.get("chain")})
    max_gas = max((float(row.get("gas_bps", 0)) for row in rows if row.get("gas_bps") is not None), default=0.0)
    min_net = min(
        (float(row.get("net_after_live_gas_bps", 0)) for row in rows if row.get("net_after_live_gas_bps") is not None),
        default=0.0,
    )
    return (
        f"{ok}/{len(snapshots)} RPCs ok across {','.join(chains) or 'none'}; "
        f"rows {len(rows)}; max gas {_bps(max_gas)}; min net {_bps(min_net)}"
    )


def _control_plane_cost_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "control-plane rows n/a"
    priced = [row for row in rows if row.get("episode_cost_e6") is not None]
    max_cost = max((int(row.get("episode_cost_e6", 0)) for row in priced), default=0)
    max_bleed_bps = max(
        (float(row.get("cost_vs_measured_bleed_bps", 0)) for row in priced if row.get("cost_vs_measured_bleed_bps") is not None),
        default=0.0,
    )
    max_equiv = max((float(row.get("hot_path_equivalent_swaps", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; triggers={int(report.get('trigger_count', 0))}; "
        f"max cost {_usd(max_cost)}; max bleed cost {_bps(max_bleed_bps)}; "
        f"hot-path equiv {max_equiv:.2f} swaps"
    )


def _pnl_attribution_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "attribution rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    drags = sorted({str(row.get("dominant_drag", "")) for row in rows if row.get("dominant_drag")})
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    max_apr = max((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; "
        f"APR range {_rate(min_apr)} to {_rate(max_apr)}; dominant drags {','.join(drags) or 'none'}"
    )


def _capital_survival_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "survival rows n/a"
    labels = sorted({str(row.get("label", "")) for row in rows if row.get("label")})
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    burn_days = [
        float(row.get("days_to_10pct_loss"))
        for row in rows
        if row.get("days_to_10pct_loss") is not None
    ]
    shortest = min(burn_days) if burn_days else None
    return (
        f"{len(rows)} rows across {len(labels)} labels; "
        f"statuses {','.join(statuses) or 'none'}; shortest 10% runway {_days(shortest)}"
    )


def _operator_cost_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "operator rows n/a"
    statuses = sorted({str(row.get("status", "")) for row in rows if row.get("status")})
    viable = sum(1 for row in rows if str(row.get("status", "")).startswith("viable"))
    max_ops = max((float(row.get("annual_ops_cost_usdc", 0)) for row in rows), default=0.0)
    min_apr = min((float(row.get("net_apr_after_ops", 0)) for row in rows), default=0.0)
    return (
        f"{len(rows)} rows; statuses {','.join(statuses) or 'none'}; "
        f"viable {viable}; max ops {_usd_float(max_ops)}; min APR {_rate(min_apr)}"
    )


def _pilot_deployability_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "deployability rows n/a"
    viable = sum(1 for row in rows if row.get("status") == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and row.get("status") == "viable >=10% APR"
    )
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    return f"{len(rows)} rows; viable {viable}; 2x viable {stress_viable}; min APR {_rate(min_apr)}"


def _range_width_deployability_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "range-width rows n/a"
    widths = sorted({int(row.get("half_width_bps", 0)) for row in rows if row.get("half_width_bps")})
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    viable = sum(1 for row in rows if row.get("status") == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and row.get("status") == "viable >=10% APR"
    )
    best_apr = max((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    worst_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    width_text = ",".join(f"{width / 100:.1f}%" for width in widths) or "none"
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; widths {width_text}; "
        f"viable {viable}; 2x viable {stress_viable}; APR range {_rate(worst_apr)} to {_rate(best_apr)}"
    )


def _small_capital_decision_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "decision rows n/a"
    recommendations = sorted({str(row.get("recommendation", "")) for row in rows if row.get("recommendation")})
    pilot_only = sum(1 for row in rows if str(row.get("recommendation", "")).startswith("pilot only"))
    no_go = sum(1 for row in rows if str(row.get("recommendation", "")).startswith("no-go"))
    live_note = "live complete" if report.get("live_shadow_complete") else "live provisional"
    return (
        f"{len(rows)} rows; recommendations {','.join(recommendations) or 'none'}; "
        f"pilot-only {pilot_only}; no-go {no_go}; {live_note}"
    )


def _alpha_rank(alpha_sweep: dict, alpha: str) -> str:
    for idx, row in enumerate(alpha_sweep.get("rows", []), start=1):
        if str(row.get("alpha", "")) == alpha:
            return str(idx)
    return "n/a"


def _target_return_status(target_return_report: dict, window: str, policy: str, target_apr: float) -> str:
    for row in target_return_report.get("rows", []):
        if (
            row.get("window") == window
            and row.get("policy") == policy
            and abs(float(row.get("target_apr", 0)) - target_apr) < 1e-9
        ):
            return str(row.get("status", "n/a"))
    return "n/a"


def _route_demand_summary(report: dict) -> str:
    rows = report.get("rows", [])
    if not rows:
        return "demand rows n/a"
    windows = sorted({str(row.get("window", "")) for row in rows if row.get("window")})
    max_routed = max((float(row.get("routed_notional_share", 0)) for row in rows if row.get("routed_notional_share") is not None), default=0.0)
    min_delta = min((int(row.get("delta_vs_full_e6", 0)) for row in rows), default=0)
    max_delta = max((int(row.get("delta_vs_full_e6", 0)) for row in rows), default=0)
    return (
        f"{len(rows)} rows across {','.join(windows) or 'none'}; max routed {_rate(max_routed)}; "
        f"delta range {_usd(min_delta)} to {_usd(max_delta)}"
    )


def _max_split_leakage(order_split_report: dict) -> float | None:
    rows = order_split_report.get("rows", [])
    values = [float(row.get("leakage_rate", 0)) for row in rows if row.get("leakage_rate") is not None]
    if not values:
        return None
    return max(values)


def _max_sequential_split_abs_leakage(sequential_split_report: dict) -> float | None:
    rows = sequential_split_report.get("rows", [])
    values = [abs(float(row.get("leakage_rate", 0))) for row in rows if row.get("leakage_rate") is not None]
    if not values:
        return None
    return max(values)


def _rate(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value > 1:
        return ">100%"
    return f"{value:.2%}"


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _days(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.1f}d"


def _ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x"


def _seconds(value_ms: object) -> str:
    if value_ms is None:
        return "n/a"
    return f"{int(value_ms) / 1000:.3f}s"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate PegGuard economic evidence ledger")
    parser.add_argument("--live-status", type=Path, default=root / "docs" / "live-shadow-20260607T082122Z" / "status.json")
    parser.add_argument("--live-convergence-report", type=Path, default=root / "docs" / "live_convergence_report.json")
    parser.add_argument("--live-maturity-report", type=Path, default=root / "docs" / "live_maturity_report.json")
    parser.add_argument("--live-power-report", type=Path, default=root / "docs" / "live_power_report.json")
    parser.add_argument("--cross-pair-live-report", type=Path, default=root / "docs" / "cross_pair_live_report.json")
    parser.add_argument("--live-soak-report", type=Path, default=root / "docs" / "live_soak_report.json")
    parser.add_argument("--cross-pair-live-economics-report", type=Path, default=root / "docs" / "cross_pair_live_economics_report.json")
    parser.add_argument("--live-fee-tier-report", type=Path, default=root / "docs" / "live_fee_tier_report.json")
    parser.add_argument("--route-proxy", type=Path, default=root / "docs" / "route_away_proxy.json")
    parser.add_argument("--cross-pair-route-proxy", type=Path, default=root / "docs" / "route_away_proxy_weth_usdt.json")
    parser.add_argument("--route-share-stability-report", type=Path, default=root / "docs" / "route_share_stability_report.json")
    parser.add_argument("--route-away-placebo-ab-report", type=Path, default=root / "docs" / "route_away_placebo_ab_report.json")
    parser.add_argument("--route-ab-power-report", type=Path, default=root / "docs" / "route_ab_power_report.json")
    parser.add_argument("--route-ab-sizing-report", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    parser.add_argument("--route-baseline-probe-report", type=Path, default=root / "docs" / "route_away_baseline_probe.json")
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
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "economic_evidence.md")
    args = parser.parse_args()
    write_output(
        args.out_md,
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
        cross_pair_live_report=load_json(args.cross_pair_live_report),
        live_soak_report=load_json(args.live_soak_report),
        cross_pair_live_economics_report=load_json(args.cross_pair_live_economics_report),
        live_fee_tier_report=load_json(args.live_fee_tier_report),
        premium_utilization_report=load_json(args.premium_utilization_report),
        charge_attribution_report=load_json(args.charge_attribution_report),
        route_share_stability_report=load_json(args.route_share_stability_report),
        route_away_placebo_ab_report=load_json(args.route_away_placebo_ab_report),
        route_ab_power_report=load_json(args.route_ab_power_report),
        route_ab_sizing_report=load_json(args.route_ab_sizing_report),
        route_baseline_probe_report=load_json(args.route_baseline_probe_report),
        guard_depeg_report=load_json(args.guard_depeg_report),
        stable_opportunity_report=load_json(args.stable_opportunity_report),
        market_regime_report=load_json(args.market_regime_report),
        signal_quality_stress_report=load_json(args.signal_quality_stress_report),
        signal_margin_report=load_json(args.signal_margin_report),
    )
    print(f"wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
