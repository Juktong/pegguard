from __future__ import annotations

import asyncio
import json
import subprocess
from fractions import Fraction

from . import constants as C
from .adverse_route_away_report import FlowEvent, adverse_rows
from .adverse_route_away_report import markdown as adverse_route_markdown
from .alpha_sweep import compute as alpha_sweep_compute
from .alpha_sweep import markdown as alpha_sweep_markdown
from .base_fee_report import base_fee_row
from .base_fee_report import compute as base_fee_compute
from .base_fee_report import markdown as base_fee_markdown
from .bootstrap_report import BootEvent, bootstrap_window
from .bootstrap_report import compute as bootstrap_compute
from .bootstrap_report import markdown as bootstrap_markdown
from .capital_path_report import compute as capital_path_compute
from .capital_path_report import markdown as capital_path_markdown
from .capital_model import markdown as capital_markdown
from .chain_cost_report import compute as chain_cost_compute
from .chain_cost_report import markdown as chain_cost_markdown
from .charge_attribution_report import ChargeEvent, attribution_window
from .charge_attribution_report import markdown as charge_attribution_markdown
from .control_plane_cost_report import compute as control_plane_cost_compute
from .control_plane_cost_report import markdown as control_plane_cost_markdown
from .cross_pair_live_report import PairSpec as CrossPairLiveSpec
from .cross_pair_live_report import compute as cross_pair_live_compute
from .cross_pair_live_report import markdown as cross_pair_live_markdown
from .cross_pair_live_economics_report import PairSpec as CrossPairLiveEconomicsSpec
from .cross_pair_live_economics_report import compute as cross_pair_live_economics_compute
from .cross_pair_live_economics_report import markdown as cross_pair_live_economics_markdown
from .db import connect
from .depth_proxy import BandDepth, DepthRow, depth_for_band
from .depth_proxy import markdown as depth_markdown
from .depth_proxy import summarize as depth_summarize
from .drawdown_stop_report import compute as drawdown_stop_compute
from .drawdown_stop_report import markdown as drawdown_stop_markdown
from .evidence_ledger import markdown as evidence_markdown
from .economic_gate import evaluate as gate_evaluate
from .economic_gate import _live_evidence_consistent, _live_evidence_observed
from .economic_gate import markdown as gate_markdown
from .economic_finalize import FinalizePaths, finalize_once
from .economic_suite import fixture_events, live_shadow_metric, markdown as economic_suite_markdown, suite
from .fallback_attribution import compute as fallback_attribution_compute
from .fallback_attribution import markdown as fallback_attribution_markdown
from .guard_depeg_report import compute as guard_depeg_compute
from .guard_depeg_report import markdown as guard_depeg_markdown
from .stable_opportunity_report import compute as stable_opportunity_compute
from .stable_opportunity_report import markdown as stable_opportunity_markdown
from .hedge_execution_report import compute as hedge_execution_compute
from .hedge_execution_report import markdown as hedge_execution_markdown
from .hedge_report import compute as hedge_compute
from .hedge_report import markdown as hedge_markdown
from .headline_uncertainty_report import compute as headline_uncertainty_compute
from .headline_uncertainty_report import markdown as headline_uncertainty_markdown
from .insurance_reserve_report import ReserveEvent
from .insurance_reserve_report import markdown as insurance_reserve_markdown
from .insurance_reserve_report import reserve_rows
from .inventory_report import compute as inventory_compute
from .inventory_report import markdown as inventory_markdown
from . import live_gas_snapshot_report as live_gas_module
from .live_gas_snapshot_report import GasSnapshot
from .live_gas_snapshot_report import compute as live_gas_compute
from .live_gas_snapshot_report import markdown as live_gas_markdown
from .live_convergence_report import compute as live_convergence_compute
from .live_convergence_report import markdown as live_convergence_markdown
from .live_maturity_report import compute as live_maturity_compute
from .live_maturity_report import markdown as live_maturity_markdown
from .live_power_report import compute as live_power_compute
from .live_power_report import markdown as live_power_markdown
from .live_fee_tier_report import FeeTierSpec as LiveFeeTierSpec
from .live_fee_tier_report import compute as live_fee_tier_compute
from .live_fee_tier_report import markdown as live_fee_tier_markdown
from .live_soak_report import PairSpec as LiveSoakSpec
from .live_soak_report import compute as live_soak_compute
from .live_soak_report import markdown as live_soak_markdown
from .live_status import compute_status, markdown as live_status_markdown
from .liquidity_share_report import compute as liquidity_share_compute
from .liquidity_share_report import markdown as liquidity_share_markdown
from .lp_flow_response_report import compute as lp_flow_response_compute
from .lp_flow_response_report import markdown as lp_flow_response_markdown
from .position_shadow_report import compute as position_shadow_compute
from .position_shadow_report import markdown as position_shadow_markdown
from .real_position_report import compute as real_position_compute
from .real_position_report import build_payload_from_env as real_position_payload_from_env
from .real_position_report import markdown as real_position_markdown
from .real_position_report import write_input_from_payload as real_position_write_input
from .real_position_report import write_template as real_position_write_template
from .real_position_portfolio_report import compute as real_position_portfolio_compute
from .real_position_portfolio_report import markdown as real_position_portfolio_markdown
from .real_position_portfolio_report import write_template as real_position_portfolio_write_template
from .real_position_metadata import decode_position_info as real_position_decode_info
from .real_position_metadata import markdown as real_position_metadata_markdown
from .real_position_metadata import amounts_for_liquidity as real_position_amounts_for_liquidity
from .real_position_metadata import quote_value_e6 as real_position_quote_value_e6
from .real_position_metadata import sqrt_price_at_tick as real_position_sqrt_price_at_tick
from .real_position_lifecycle import decode_modify_position as real_position_decode_modify_position
from .real_position_lifecycle import markdown as real_position_lifecycle_markdown
from .markout_sensitivity_report import compute as markout_sensitivity_compute
from .markout_sensitivity_report import markdown as markout_sensitivity_markdown
from .market_regime_report import RegimeEvent, compute as market_regime_compute
from .market_regime_report import markdown as market_regime_markdown
from .market_regime_report import regime_rows
from .oracle_health import compute as oracle_health_compute
from .oracle_health import markdown as oracle_health_markdown
from .oracle_lag_report import compute as oracle_lag_compute
from .oracle_lag_report import markdown as oracle_lag_markdown
from .operator_cost_report import compute as operator_cost_compute
from .operator_cost_report import markdown as operator_cost_markdown
from .pilot_deployability_report import compute as pilot_deployability_compute
from .pilot_deployability_report import markdown as pilot_deployability_markdown
from .order_split_report import SplitEvent, compute as order_split_compute
from .order_split_report import markdown as order_split_markdown
from .order_split_report import split_rows
from .capital_survival_report import compute as capital_survival_compute
from .capital_survival_report import markdown as capital_survival_markdown
from .pnl_attribution_report import compute as pnl_attribution_compute
from .pnl_attribution_report import markdown as pnl_attribution_markdown
from .policy_monte_carlo_report import compute as policy_monte_carlo_compute
from .policy_monte_carlo_report import markdown as policy_monte_carlo_markdown
from .premium_allocation_report import allocation_rows
from .premium_allocation_report import markdown as premium_allocation_markdown
from .premium_utilization_report import PremiumEvent, utilization_row
from .premium_utilization_report import markdown as premium_utilization_markdown
from .quote_route_collect import compute as quote_route_collect_compute
from .quote_route_collect import markdown as quote_route_collect_markdown
from .quote_route_readiness import compute as quote_route_readiness_compute
from .quote_route_readiness import markdown as quote_route_readiness_markdown
from .quote_headroom_report import compute as quote_headroom_compute
from .quote_headroom_report import markdown as quote_headroom_markdown
from .quote_headroom_stability_report import SnapshotSpec
from .quote_headroom_stability_report import compute as quote_stability_compute
from .quote_headroom_stability_report import markdown as quote_stability_markdown
from .quote_headroom_drift_report import compute as quote_drift_compute
from .quote_headroom_drift_report import markdown as quote_drift_markdown
from .quote_event_headroom_report import compute as quote_event_headroom_compute
from .quote_event_headroom_report import event_budget
from .quote_event_headroom_report import markdown as quote_event_headroom_markdown
from .quote_provenance_report import compute as quote_provenance_compute
from .quote_provenance_report import markdown as quote_provenance_markdown
from .quote_elasticity_report import compute as quote_elasticity_compute
from .quote_elasticity_report import markdown as quote_elasticity_markdown
from .quote_premium_stress_report import StressEvent, quote_buckets, stress_rows
from .quote_premium_stress_report import markdown as quote_premium_stress_markdown
from .range_width_deployability_report import compute as range_width_deployability_compute
from .range_width_deployability_report import markdown as range_width_deployability_markdown
from .reserve_delay_report import delay_rows
from .reserve_delay_report import markdown as reserve_delay_markdown
from .reserve_lifecycle_report import lifecycle_rows
from .reserve_lifecycle_report import markdown as reserve_lifecycle_markdown
from .reserve_tail_report import markdown as reserve_tail_markdown
from .reserve_tail_report import reserve_tail_row, reserve_tail_rows
from .report import emit_reports
from .risk_report import RiskEvent, markdown as risk_markdown, risk_for_events
from .risk_adjusted_return_report import compute as risk_adjusted_return_compute
from .risk_adjusted_return_report import markdown as risk_adjusted_return_markdown
from .route_demand_report import DemandEvent, demand_rows
from .route_demand_report import markdown as route_demand_markdown
from .route_away_placebo_ab_report import compute as route_away_placebo_ab_compute
from .route_away_placebo_ab_report import markdown as route_away_placebo_ab_markdown
from .route_share_stability_report import compute as route_share_stability_compute
from .route_share_stability_report import markdown as route_share_stability_markdown
from .route_away_collect import (
    ExperimentWindows,
    PoolWindowStats,
    V4_SWAP_TOPIC0,
    _expected_chain_id,
    _log_topics,
    _rpc_client,
    build_payload,
    decode_v4_swap_log,
    summarize_swaps,
    validate_collection_preflight,
    validate_collection_config,
    validate_distinct_pool_identities,
    validate_nonzero_windows,
    write_payload_artifacts,
)
from .route_away_collector_smoke import compute as route_collector_smoke_compute
from .route_away_collector_smoke import markdown as route_collector_smoke_markdown
from .route_away_window_plan import compute as route_window_plan_compute
from .route_away_window_plan import markdown as route_window_plan_markdown
from .route_away_ab import evaluate as route_ab_evaluate
from .route_away_ab import evidence_errors as route_ab_evidence_errors
from .route_away_ab import markdown as route_ab_markdown
from .route_away_ab import validate_payload as route_ab_validate_payload
from .route_away_ab import validation_errors as route_ab_validation_errors
from .route_away_ab import write_invalid_outputs as route_ab_write_invalid_outputs
from .route_away_break_even import break_even_row, compute as break_even_compute
from .route_away_break_even import markdown as break_even_markdown
from .route_ab_power_report import compute as route_ab_power_compute
from .route_ab_power_report import markdown as route_ab_power_markdown
from .route_ab_sizing_report import compute as route_ab_sizing_compute
from .route_ab_sizing_report import markdown as route_ab_sizing_markdown
from .route_away_baseline_probe import compute_static as route_baseline_probe_compute_static
from .route_away_baseline_probe import markdown as route_baseline_probe_markdown
from .route_away_proxy import markdown as route_proxy_markdown
from .route_away_proxy import parse_fee_pool
from .route_away_proxy import summarize as route_proxy_summarize
from .route_away_readiness import compute as route_readiness_compute
from .route_away_readiness import markdown as route_readiness_markdown
from .route_away_rpc_preflight import compute_static as route_rpc_preflight_compute_static
from .route_away_rpc_preflight import markdown as route_rpc_preflight_markdown
from .rpc import RpcHttp, RpcWs
from .route_cost_proxy import compute as route_cost_compute
from .route_cost_proxy import markdown as route_cost_markdown
from .sequential_split_report import SequenceEvent
from .sequential_split_report import compute as sequential_split_compute
from .sequential_split_report import markdown as sequential_split_markdown
from .sequential_split_report import sequential_rows
from .signal_margin_report import compute as signal_margin_compute
from .signal_margin_report import markdown as signal_margin_markdown
from .signal_quality_stress_report import compute as signal_quality_stress_compute
from .signal_quality_stress_report import markdown as signal_quality_stress_markdown
from .rpc import SwapLog
from .size_bucket_report import BucketEvent, bucket_rows
from .size_bucket_report import compute as size_bucket_compute
from .size_bucket_report import markdown as size_bucket_markdown
from .small_capital_decision_report import compute as small_capital_decision_compute
from .small_capital_decision_report import markdown as small_capital_decision_markdown
from .staleness_bucket_report import compute as staleness_bucket_compute
from .staleness_bucket_report import markdown as staleness_bucket_markdown
from .target_fee_report import compute as target_fee_compute
from .target_fee_report import markdown as target_fee_markdown
from .target_return_report import compute as target_return_compute
from .target_return_report import markdown as target_return_markdown
from .truth import process_delayed_truth
from .tvl_dilution_report import compute as tvl_dilution_compute
from .tvl_dilution_report import markdown as tvl_dilution_markdown


def _complete_reserve_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for claim_basis in ("charged correcting markout", "all truth-correcting markout", "all positive markout"):
            for payout_rate in (0.25, 0.5, 1.0):
                rows.append(
                    {
                        "window": window,
                        "claim_basis": claim_basis,
                        "payout_rate": payout_rate,
                        "max_deficit_e6": 100,
                        "coverage_ratio": 0.8,
                    }
                )
    return {"rows": rows}


def _complete_route_share_stability_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {"pair": "WETH/USDC", "lookback_blocks": 10_000},
            {"pair": "WETH/USDC", "lookback_blocks": 50_000},
            {"pair": "WETH/USDT", "lookback_blocks": 10_000},
            {"pair": "WETH/USDT", "lookback_blocks": 50_000},
        ],
        "pair_summaries": [
            {"pair": "WETH/USDC", "share_5bps_spread_pp": 1.0, "share_high_fee_spread_pp": 0.5},
            {"pair": "WETH/USDT", "share_5bps_spread_pp": 0.5, "share_high_fee_spread_pp": 0.25},
        ],
        "max_5bps_spread_pp": 1.0,
        "max_high_fee_spread_pp": 0.5,
    }


def _complete_route_away_placebo_ab_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "pair": "WETH/USDC",
                "chain": "arbitrum",
                "false_route_away_rate": 0.01,
                "share_shift_pp": -1.0,
            },
            {
                "pair": "WETH/USDT",
                "chain": "arbitrum",
                "false_route_away_rate": 0.0,
                "share_shift_pp": 0.5,
            },
        ],
        "max_false_route_away_rate": 0.01,
        "max_abs_share_shift_pp": 1.0,
    }


def _complete_route_ab_power_report() -> dict:
    return {
        "complete": True,
        "mde_rows": [
            {
                "pair": "WETH/USDC",
                "noise_basis": "30 bps+ share drift",
                "pre_treatment_share": 0.25,
                "mde_route_away_rate": 0.02,
                "status": "usable",
            },
            {
                "pair": "WETH/USDT",
                "noise_basis": "5 bps share drift",
                "pre_treatment_share": 0.25,
                "mde_route_away_rate": 0.04,
                "status": "usable",
            },
        ],
        "economic_rows": [
            {
                "window": "calm",
                "pair": "WETH/USDC",
                "interpretation": "detectable before modeled break-even",
            },
            {
                "window": "vol",
                "pair": "WETH/USDT",
                "interpretation": "detectable only after zero-net route loss",
            },
        ],
    }


def _complete_route_ab_sizing_report() -> dict:
    return {
        "complete": True,
        "target_treatment_notional_e6": 100_000_000_000,
        "proxy_rows": [
            {"pair": "WETH/USDC", "median_daily_notional_e6": 1_000_000_000_000},
            {"pair": "WETH/USDT", "median_daily_notional_e6": 500_000_000_000},
        ],
        "candidate_rows": [
            {
                "pair": "WETH/USDC",
                "window": "calm",
                "pre_treatment_share": 0.25,
                "mde_route_away_rate": 0.05,
                "interpretation": "detectable before modeled break-even",
                "hours_for_target_treatment_notional": 9.6,
            },
            {
                "pair": "WETH/USDT",
                "window": "calm",
                "pre_treatment_share": 0.25,
                "mde_route_away_rate": 0.05,
                "interpretation": "detectable before modeled break-even",
                "hours_for_target_treatment_notional": 19.2,
            },
        ],
        "recommendations": [
            {
                "pair": "WETH/USDC",
                "pre_treatment_share": 0.25,
                "noise_basis": "30 bps+ share drift",
                "mde_route_away_rate": 0.05,
                "hours_for_target_treatment_notional": 9.6,
                "reason": "lowest-noise measurable row for this pair using current proxy notional",
            }
        ],
    }


def _complete_route_baseline_probe_report() -> dict:
    return {
        "complete": True,
        "executed": True,
        "rows": [
            {
                "pair": "WETH/USDC",
                "chain": "arbitrum",
                "baseline_pool": "0xpool",
                "windows": [
                    {"label": "reference_pre", "swaps": 10, "quote_notional_e6": 100_000_000, "complete": True},
                    {"label": "reference_post", "swaps": 12, "quote_notional_e6": 120_000_000, "complete": True},
                ],
            }
        ],
    }


def _complete_market_regime_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for segment in ("all", "quiet <1bp", "normal 1-5bp", "high-vol >=5bp"):
            rows.append(
                {
                    "window": window,
                    "segment": segment,
                    "rows": 1,
                    "net_bps": 1.0,
                    "low_l2_net_bps": 0.9,
                    "stressed_l2_net_bps": 0.5,
                }
            )
    rows.extend(
        [
            {
                "window": "live shadow",
                "segment": "all",
                "rows": 2,
                "net_bps": -1.0,
                "low_l2_net_bps": -1.1,
                "stressed_l2_net_bps": -1.5,
            },
            {
                "window": "live shadow",
                "segment": "high-vol >=5bp",
                "rows": 1,
                "net_bps": -4.0,
                "low_l2_net_bps": -4.1,
                "stressed_l2_net_bps": -4.5,
            },
            {
                "window": "live shadow",
                "segment": "oracle-lag/fallback",
                "rows": 1,
                "net_bps": -2.0,
                "low_l2_net_bps": -2.1,
                "stressed_l2_net_bps": -2.5,
            },
        ]
    )
    return {"complete": True, "rows": rows}


def _complete_signal_quality_stress_report() -> dict:
    rows = []
    for window in ("calm", "vol", "live shadow"):
        for scenario in ("observed", "miss 50pct correct", "false 100pct correct"):
            rows.append(
                {
                    "window": window,
                    "scenario": scenario,
                    "aligned_net_bps": -1.0 if scenario != "observed" else 1.0,
                    "raw_minus_aligned_bps": 2.0,
                    "status": "precision broken" if scenario == "false 100pct correct" else "passes stress",
                }
            )
    return {"rows": rows}


def _complete_signal_margin_report() -> dict:
    return {
        "rows": [
            {
                "window": window,
                "precision_breakeven": 0.75,
                "precision_headroom_pp": 0.20,
                "max_missed_correct_share": 0.20,
                "status": "positive margin",
            }
            for window in ("calm", "vol", "live shadow")
        ]
    }


def _complete_reserve_tail_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for claim_basis in ("charged correcting markout", "all truth-correcting markout", "all positive markout"):
            for payout_rate in (0.25, 0.5, 1.0):
                rows.append(
                    {
                        "window": window,
                        "claim_basis": claim_basis,
                        "payout_rate": payout_rate,
                        "p99_seed_e6": 100,
                        "cvar95_seed_e6": 100,
                    }
                )
    return {"iterations": 10, "rows": rows}


def _complete_reserve_lifecycle_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for horizon in (30, 90):
            for claim_basis in ("charged correcting markout", "all truth-correcting markout"):
                for policy in ("seeded compound", "monthly 25% surplus skim", "monthly 10% LP churn"):
                    rows.append(
                        {
                            "window": window,
                            "horizon_days": horizon,
                            "claim_basis": claim_basis,
                            "policy": policy,
                            "required_topup_e6": 0,
                            "survived_without_topup": True,
                            "withdrawal_share_of_premium": 0.1,
                        }
                    )
    return {"rows": rows}


def _complete_premium_allocation_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for claim_basis in ("charged correcting markout", "all truth-correcting markout"):
            for reserve_share in (0.0, 0.25, 0.5, 0.75, 1.0):
                rows.append(
                    {
                        "window": window,
                        "claim_basis": claim_basis,
                        "reserve_share": reserve_share,
                        "reserve_required_seed_e6": 0,
                        "reserve_unseeded_solvent": True,
                        "lp_net_before_claims_bps": 1.0,
                    }
                )
    return {"rows": rows}


def _complete_reserve_delay_report() -> dict:
    rows = []
    for window in ("calm", "vol", "live shadow"):
        for claim_basis in ("charged correcting markout", "all truth-correcting markout"):
            for payout_rate in (0.5, 1.0):
                for delay_days in (0, 1, 7, 30):
                    rows.append(
                        {
                            "window": window,
                            "claim_basis": claim_basis,
                            "payout_rate": payout_rate,
                            "claim_delay_days": delay_days,
                            "required_economic_seed_e6": 100,
                            "hidden_liability_gap_e6": 10,
                            "economically_solvent_without_seed": False,
                        }
                    )
    return {"rows": rows}


def _complete_policy_monte_carlo_report() -> dict:
    rows = []
    for mix in ("routine 30d", "shock 30d", "stress 30d", "routine 90d"):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "mix": mix,
                        "policy": policy,
                        "scenario": scenario,
                        "probability_loss": 0.1,
                        "probability_drawdown_gt_1pct": 0.0,
                    }
                )
    return {"iterations": 10, "rows": rows}


def _complete_risk_adjusted_return_report() -> dict:
    rows = []
    for mix in ("routine 30d", "shock 30d", "stress 30d", "routine 90d"):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "mix": mix,
                        "policy": policy,
                        "scenario": scenario,
                        "loss_day_probability": 0.1,
                        "sortino_like": 1.5,
                        "status": "risk-adjusted viable",
                    }
                )
    return {"target_return": 0.10, "rows": rows}


def _complete_headline_uncertainty_report() -> dict:
    return {
        "iterations": 500,
        "windows": [
            {"window": "calm", "capture_p05": 0.10},
            {"window": "vol", "capture_p05": 0.20},
        ],
        "policies": [
            {"window": window, "policy": policy, "net_apr_p50": 0.05}
            for window in ("calm", "vol")
            for policy in ("micro passive", "small active", "focused active")
        ],
    }


def _complete_lp_flow_response_report() -> dict:
    rows = []
    for path in ("calm 30d", "weekly vol shock 30d", "all volatile 7d"):
        for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
            for start in (10_000_000_000, 25_000_000_000, 100_000_000_000):
                rows.append(
                    {
                        "path": path,
                        "scenario": scenario,
                        "start_capital_e6": start,
                        "status": "capital retained",
                        "max_drawdown": -0.01,
                        "outflow_days": 0,
                    }
                )
    return {"rows": rows}


def _complete_chain_cost_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for chain in ("base", "unichain", "arbitrum", "ethereum"):
            rows.append(
                {
                    "window": window,
                    "chain": chain,
                    "net_after_chain_cost_bps": 0.5,
                    "gas_bps": 0.1,
                }
            )
    return {"hook_gas": 140_579, "default_pyth_update_gas": 90_000, "rows": rows}


def _complete_live_gas_snapshot_report() -> dict:
    snapshots = []
    rows = []
    for chain in ("base", "unichain", "arbitrum", "ethereum"):
        snapshots.append({"chain": chain, "ok": True, "gas_price_gwei": 0.01, "block_number": 1})
        for window in ("calm", "vol"):
            rows.append(
                {
                    "window": window,
                    "chain": chain,
                    "gas_bps": 0.01,
                    "net_after_live_gas_bps": 1.0,
                }
            )
    return {"snapshots": snapshots, "rows": rows}


def _complete_control_plane_cost_report() -> dict:
    return {
        "complete": True,
        "trigger_count": 6,
        "measured_bleed_e6": 10_000_000_000,
        "rows": [
            {
                "chain": chain,
                "episode_cost_e6": 1_000,
                "cost_vs_measured_bleed_bps": 0.001,
                "hot_path_equivalent_swaps": 2.45,
            }
            for chain in ("base", "unichain", "arbitrum", "ethereum")
        ],
    }


def _complete_pnl_attribution_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "window": window,
                        "policy": policy,
                        "scenario": scenario,
                        "net_apr": 0.05,
                        "dominant_drag": "markout",
                    }
                )
    return {"rows": rows}


def _complete_capital_survival_report() -> dict:
    rows = []
    for label, kind in (("calm", "window"), ("vol", "window"), ("routine 30d", "mix"), ("shock 30d", "mix"), ("stress 30d", "mix")):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "label": label,
                        "kind": kind,
                        "policy": policy,
                        "scenario": scenario,
                        "net_apr": 0.05,
                        "days_to_10pct_loss": None,
                        "status": "covered",
                    }
                )
    return {"rows": rows}


def _complete_operator_cost_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                for ops in ("free operator", "hobby infra", "paid light ops", "active manager"):
                    rows.append(
                        {
                            "window": window,
                            "policy": policy,
                            "scenario": scenario,
                            "ops_scenario": ops,
                            "annual_ops_cost_usdc": 100.0,
                            "net_apr_after_ops": 0.05,
                            "status": "positive but subscale",
                        }
                    )
    return {"rows": rows}


def _complete_hedge_execution_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for range_policy in ("static +/-1%", "static +/-3%", "static +/-5%"):
            for hedge_policy, rebalances in (("open only", 0), ("50 bps drift", 6), ("every event", 3881)):
                for scenario in ("low-cost perp", "stressed funding", "thin hedge venue"):
                    status = "operationally infeasible" if hedge_policy == "every event" and scenario == "thin hedge venue" else "worse than unhedged"
                    rows.append(
                        {
                            "window": window,
                            "range_policy": range_policy,
                            "hedge_policy": hedge_policy,
                            "scenario": scenario,
                            "rebalances": rebalances,
                            "hedge_improvement_e6": -100,
                            "status": status,
                        }
                    )
    return {"rows": rows}


def _complete_quote_elasticity_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for margin in (1.0, 0.5, 0.25, 0.10):
            rows.append(
                {
                    "window": window,
                    "budget_margin": margin,
                    "lost_share_of_extra": 0.0,
                    "lost_extra_e6": 0,
                }
            )
    return {"rows": rows}


def _complete_quote_event_headroom_report() -> dict:
    return {
        "quote_points": [{"quote_notional_e6": 1_000_000_000, "premium_budget_pips": 500}],
        "rows": [
            {
                "window": "calm",
                "charged_rows": 1,
                "extra_e6": 100,
                "excess_e6": 0,
                "excess_share_of_extra": 0.0,
                "over_budget_rows": 0,
                "above_max_quote_rows": 0,
            },
            {
                "window": "vol",
                "charged_rows": 1,
                "extra_e6": 100,
                "excess_e6": 10,
                "excess_share_of_extra": 0.1,
                "over_budget_rows": 1,
                "above_max_quote_rows": 1,
            },
        ],
    }


def _complete_quote_provenance_report() -> dict:
    artifacts = []
    for label, block_tag in (
        ("WETH/USDC primary", "latest"),
        ("WETH/USDT primary", "latest"),
        ("WETH/USDC repeat", "123"),
        ("WETH/USDT repeat", "123"),
    ):
        artifacts.append(
            {
                "label": label,
                "path": f"docs/{label}.json",
                "present": True,
                "chain": "arbitrum",
                "block_tag": block_tag,
                "pinned_block": block_tag != "latest",
                "generated_at": "",
                "rows": 16,
                "quoted_rows": 16,
                "failed_rows": 0,
                "fee_tiers": 4,
                "amount_inputs": 4,
                "min_amount_in_raw": 1,
                "max_amount_in_raw": 4,
                "warning": "unpinned block tag" if block_tag == "latest" else "",
            }
        )
    return {
        "complete": True,
        "artifact_count": 4,
        "present_count": 4,
        "total_quote_rows": 64,
        "quoted_rows": 64,
        "failed_rows": 0,
        "latest_block_tag_artifacts": 2,
        "pinned_block_artifacts": 2,
        "missing_generated_at_artifacts": 4,
        "warnings": ["unpinned block tag", "missing generated_at"],
        "artifacts": artifacts,
    }


def _complete_live_convergence_report() -> dict:
    return {
        "complete": True,
        "bucket_count": 2,
        "valid_rows": 20,
        "charged_rows": 10,
        "precision": 0.95,
        "capture_truth": 0.22,
        "net_bps": 1.2,
        "convergence_rows": [
            {
                "bucket_index": 0,
                "valid_rows": 10,
                "charged_rows": 5,
                "notional_e6": 1_000_000,
                "fallback_notional_e6": 0,
            },
            {
                "bucket_index": 1,
                "valid_rows": 10,
                "charged_rows": 5,
                "notional_e6": 1_000_000,
                "fallback_notional_e6": 100_000,
            },
        ],
    }


def _complete_live_maturity_report() -> dict:
    return {
        "complete": True,
        "checkpoint_count": 2,
        "valid_rows": 20,
        "charged_rows": 10,
        "precision": 0.95,
        "capture_truth": 0.22,
        "net_bps": 1.2,
        "max_abs_capture_delta": 0.03,
        "max_abs_net_bps_delta": 0.4,
        "maturity_rows": [
            {
                "checkpoint_index": 0,
                "valid_rows": 10,
                "charged_rows": 5,
                "capture_delta_vs_final": -0.03,
                "net_bps_delta_vs_final": -0.4,
            },
            {
                "checkpoint_index": 1,
                "valid_rows": 20,
                "charged_rows": 10,
                "capture_delta_vs_final": 0.0,
                "net_bps_delta_vs_final": 0.0,
            },
        ],
    }


def _complete_live_power_report() -> dict:
    return {
        "complete": True,
        "observed_span_hours": 2.0,
        "bucket_count": 2,
        "valid_rows": 20,
        "charged_rows": 10,
        "metrics": [
            {
                "metric": "net_bps",
                "current_value": 1.0,
                "bucket_count": 2,
                "ci95_half_width": 0.25,
                "target_half_width": 0.5,
                "additional_hours_needed": 0.0,
                "status": "target met",
            },
            {
                "metric": "capture_truth",
                "current_value": 0.1,
                "bucket_count": 2,
                "ci95_half_width": 0.01,
                "target_half_width": 0.02,
                "additional_hours_needed": 0.0,
                "status": "target met",
            },
            {
                "metric": "precision",
                "current_value": 0.95,
                "bucket_count": 2,
                "ci95_half_width": 0.005,
                "target_half_width": 0.01,
                "additional_hours_needed": 0.0,
                "status": "target met",
            },
        ],
    }


def _complete_cross_pair_live_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "label": "primary",
                "pair": "WETH/USDC",
                "database": "shadow/live.sqlite3",
                "complete": True,
                "status": "complete",
                "swaps": 100,
                "valid_truth_rows": 95,
                "truth_coverage": 0.95,
                "observed_span_hours": 24.1,
                "remaining_span_hours": 0.0,
                "precision": 0.97,
                "truth_capture": 0.1,
            },
            {
                "label": "cross-pair",
                "pair": "WETH/USDT",
                "database": "shadow/live_weth_usdt.sqlite3",
                "complete": True,
                "status": "complete",
                "swaps": 80,
                "valid_truth_rows": 78,
                "truth_coverage": 0.975,
                "observed_span_hours": 24.0,
                "remaining_span_hours": 0.0,
                "precision": 0.96,
                "truth_capture": 0.08,
            },
        ],
    }


def _complete_live_soak_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "label": "primary",
                "pair": "WETH/USDC",
                "database": "shadow/live.sqlite3",
                "horizon_hours": 24.0,
                "complete": True,
                "status": "complete",
                "swaps": 100,
                "valid_truth_rows": 95,
                "truth_coverage": 0.95,
                "observed_span_hours": 168.0,
                "remaining_span_hours": 0.0,
                "precision": 0.97,
                "truth_capture": 0.1,
            },
            {
                "label": "cross-pair",
                "pair": "WETH/USDT",
                "database": "shadow/live_weth_usdt.sqlite3",
                "horizon_hours": 168.0,
                "complete": True,
                "status": "complete",
                "swaps": 80,
                "valid_truth_rows": 78,
                "truth_coverage": 0.975,
                "observed_span_hours": 168.0,
                "remaining_span_hours": 0.0,
                "precision": 0.96,
                "truth_capture": 0.08,
            },
        ],
    }


def _complete_cross_pair_live_economics_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "label": "primary",
                "pair": "WETH/USDC",
                "database": "shadow/live.sqlite3",
                "complete": True,
                "status": "complete",
                "rows": 100,
                "observed_span_hours": 24.1,
                "truth_coverage": 0.95,
                "charged_rows": 40,
                "precision": 0.97,
                "capture_truth": 0.1,
                "net_bps": 0.2,
                "convergence_complete": True,
                "maturity_complete": True,
                "power_complete": True,
            },
            {
                "label": "cross-pair",
                "pair": "WETH/USDT",
                "database": "shadow/live_weth_usdt.sqlite3",
                "complete": True,
                "status": "complete",
                "rows": 80,
                "observed_span_hours": 24.0,
                "truth_coverage": 0.975,
                "charged_rows": 30,
                "precision": 0.96,
                "capture_truth": 0.08,
                "net_bps": 0.1,
                "convergence_complete": True,
                "maturity_complete": True,
                "power_complete": True,
            },
        ],
    }


def _complete_live_fee_tier_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "label": "primary",
                "pair": "WETH/USDC",
                "fee_pips": 500,
                "database": "shadow/live.sqlite3",
                "complete": True,
                "status": "complete",
                "swaps": 100,
                "valid_truth_rows": 95,
                "truth_coverage": 0.95,
                "observed_span_hours": 24.1,
                "charged_rows": 40,
                "precision": 0.97,
                "capture_truth": 0.1,
                "net_bps": 0.2,
                "quality_status": "mature",
            },
            {
                "label": "same-pair 1bps",
                "pair": "WETH/USDC",
                "fee_pips": 100,
                "database": "shadow/live_weth_usdc_1bps.sqlite3",
                "complete": True,
                "status": "complete",
                "swaps": 20,
                "valid_truth_rows": 18,
                "truth_coverage": 0.9,
                "observed_span_hours": 1.5,
                "charged_rows": 8,
                "precision": 0.96,
                "capture_truth": 0.08,
                "net_bps": 0.1,
                "quality_status": "immature",
            },
            {
                "label": "same-pair 30bps",
                "pair": "WETH/USDC",
                "fee_pips": 3000,
                "database": "shadow/live_weth_usdc_30bps.sqlite3",
                "complete": False,
                "status": "missing",
                "swaps": 0,
                "valid_truth_rows": 0,
                "truth_coverage": 0.0,
                "observed_span_hours": 0.0,
                "charged_rows": 0,
                "precision": None,
                "capture_truth": None,
                "net_bps": None,
                "quality_status": "missing",
            },
        ],
    }


def _complete_guard_depeg_report() -> dict:
    return {
        "complete": True,
        "rows": [
            {
                "label": "selected",
                "first_vol_trigger_ms": 1,
                "calm_triggers": 0,
                "vol_triggers": 6,
                "lead_time_before_measured_bleed_sec": 4427,
                "bled_before_first_trigger_e6": 0,
                "measured_bleed_after_first_trigger_e6": 10_000_000,
            }
        ],
    }


def _complete_stable_opportunity_report() -> dict:
    return {
        "complete": True,
        "directional_fee_policy": "disabled",
        "normal_stable_max_bps": 0.35,
        "best_directional_capture_pct": 0.063,
        "trip_to_normal_ratio": 142.857,
        "rows": [{"measurement": "AMM plus CEX capture"}],
    }


def _complete_premium_utilization_report() -> dict:
    return {
        "cap_pips": C.CAP_PIPS,
        "rows": [
            {
                "window": "calm",
                "charged_rows": 2,
                "precision": 0.95,
                "p99_charged_premium_bps": 5.0,
                "cap_hit_rows": 0,
                "near_cap_rows": 0,
                "top_10pct_extra_share": 0.55,
            },
            {
                "window": "vol",
                "charged_rows": 3,
                "precision": 0.98,
                "p99_charged_premium_bps": 12.0,
                "cap_hit_rows": 0,
                "near_cap_rows": 1,
                "top_10pct_extra_share": 0.60,
            },
            {
                "window": "live shadow",
                "charged_rows": 4,
                "precision": 0.99,
                "p99_charged_premium_bps": 10.0,
                "cap_hit_rows": 0,
                "near_cap_rows": 1,
                "top_10pct_extra_share": 0.50,
            },
        ],
    }


def _complete_charge_attribution_report() -> dict:
    windows = []
    for window in ("calm", "vol", "live shadow"):
        windows.append(
            {
                "window": window,
                "charged_rows": 10,
                "precision": 0.95,
                "false_charge_extra_share": 0.05,
                "truth_correcting_markout_coverage": 0.7,
                "missed_correcting_abs_markout_e6": 1_000_000,
                "buckets": [
                    {"bucket": "charged correct"},
                    {"bucket": "charged wrong"},
                    {"bucket": "missed correcting"},
                    {"bucket": "ignored noncorrecting"},
                ],
            }
        )
    return {"windows": windows}


def _complete_quote_headroom_stability_report() -> dict:
    return {
        "complete": True,
        "pairs": ["WETH/USDC", "WETH/USDT"],
        "passed_rows": 2,
        "min_repeat_headroom_bps": 1.2,
        "max_abs_delta_headroom_bps": 0.3,
        "rows": [
            {
                "pair": "WETH/USDC",
                "amount_in_raw": 1,
                "repeat_headroom_bps": 1.2,
                "repeat_peg_rank": 1,
                "repeat_best_fee_pips": 500,
                "passed": True,
            },
            {
                "pair": "WETH/USDT",
                "amount_in_raw": 1,
                "repeat_headroom_bps": 2.0,
                "repeat_peg_rank": 1,
                "repeat_best_fee_pips": 500,
                "passed": True,
            },
        ],
    }


def _complete_quote_headroom_drift_report() -> dict:
    return {
        "complete": True,
        "pairs": ["WETH/USDC", "WETH/USDT"],
        "sample_count": 4,
        "distinct_block_count": 2,
        "passed_rows": 2,
        "min_headroom_bps": 1.2,
        "max_abs_first_to_last_delta_bps": 0.4,
        "rows": [
            {
                "pair": "WETH/USDC",
                "amount_in_raw": 1,
                "samples": 2,
                "distinct_blocks": 2,
                "min_headroom_bps": 1.2,
                "max_headroom_bps": 1.6,
                "first_to_last_delta_bps": 0.4,
                "passed": True,
            },
            {
                "pair": "WETH/USDT",
                "amount_in_raw": 1,
                "samples": 2,
                "distinct_blocks": 2,
                "min_headroom_bps": 2.0,
                "max_headroom_bps": 2.1,
                "first_to_last_delta_bps": 0.1,
                "passed": True,
            },
        ],
    }


def _complete_route_demand_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for tolerance in (1.0, 2.0, 5.0, 10.0):
            rows.append(
                {
                    "window": window,
                    "tolerance_bps": tolerance,
                    "routed_notional_share": 0.1,
                    "delta_vs_full_e6": 100,
                }
            )
    return {"rows": rows}


def _complete_markout_sensitivity_report() -> dict:
    rows = []
    for window in ("calm", "vol"):
        for multiplier in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
            rows.append(
                {
                    "window": window,
                    "strategy": "PegGuard selected",
                    "markout_multiplier": multiplier,
                    "net_bps": 1.0,
                    "required_base_pips_zero": 500,
                }
            )
    return {"rows": rows}


def _complete_pilot_deployability_report() -> dict:
    rows = []
    for window in ("calm", "vol", "live shadow"):
        for policy in ("micro passive", "small active", "focused active"):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                for ops in ("free operator", "hobby infra", "paid light ops", "active manager"):
                    for multiplier in (1.0, 1.5, 2.0):
                        rows.append(
                            {
                                "window": window,
                                "policy": policy,
                                "scenario": scenario,
                                "ops_scenario": ops,
                                "markout_multiplier": multiplier,
                                "net_apr": 0.12,
                                "status": "viable >=10% APR",
                            }
                        )
    return {"rows": rows}


def _complete_range_width_deployability_report() -> dict:
    rows = []
    for window in ("calm", "vol", "live shadow"):
        for half_width in (50, 100, 200, 500, 1000):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                for multiplier in (1.0, 1.5, 2.0):
                    rows.append(
                        {
                            "window": window,
                            "profile": f"+/-{half_width / 100:.1f}%",
                            "scenario": scenario,
                            "markout_multiplier": multiplier,
                            "half_width_bps": half_width,
                            "net_apr": 0.12,
                            "required_turnover_for_10pct": 2.0,
                            "status": "viable >=10% APR",
                        }
                    )
    return {"rows": rows}


def _complete_position_shadow_report() -> dict:
    rows = []
    combined_values = []
    for window in ("calm", "vol", "live shadow"):
        for policy in ("static +/-1%", "static +/-3%", "static +/-5%"):
            for capital in (2_500_000_000, 10_000_000_000, 25_000_000_000, 100_000_000_000):
                combined = 100
                combined_values.append(combined)
                rows.append(
                    {
                        "window": window,
                        "range_policy": policy,
                        "capital_e6": capital,
                        "combined_net_e6": combined,
                        "pro_rata_net_e6": 50,
                        "inventory_il_e6": 50,
                        "status": "net positive",
                    }
                )
    return {
        "rows": rows,
        "combined_rows": len(combined_values),
        "provisional_rows": len(rows) - len(combined_values),
        "worst_combined_net_e6": min(combined_values),
        "best_combined_net_e6": max(combined_values),
    }


def _complete_small_capital_decision_report() -> dict:
    rows = []
    for profile, capital, recommendation in (
        ("micro passive", 2_500_000_000, "observe only"),
        ("small active", 10_000_000_000, "pilot only: calm/liquid windows"),
        ("focused active", 25_000_000_000, "pilot only: calm/liquid windows"),
        ("depth-share $100k", 100_000_000_000, "no-go: sizing stress only"),
    ):
        rows.append(
            {
                "profile": profile,
                "capital_e6": capital,
                "recommendation": recommendation,
                "live_provisional": True,
                "viable_rows_1x": 1,
                "viable_rows_2x": 0,
            }
        )
    return {"live_shadow_complete": False, "rows": rows}


def _complete_real_position_report() -> dict:
    return {
        "complete": True,
        "status": "complete",
        "rows": [
            {
                "position_id": "2200741",
                "chain": "base",
                "pool_pair": "WETH/USDC",
                "net_vs_hodl_e6": 100,
                "net_vs_hodl_bps": 1.0,
            }
        ],
    }


def _complete_real_position_portfolio_report() -> dict:
    rows = []
    for index, (pair, fee_pips, status) in enumerate(
        (
            ("WETH/USDC", 500, "in range"),
            ("WETH/USDC", 3000, "out of range"),
            ("LIKE/USDC", 10000, "in range"),
        ),
        start=1,
    ):
        rows.append(
            {
                "position_id": str(2200000 + index),
                "chain": "base",
                "pool_pair": pair,
                "fee_pips": fee_pips,
                "capital_e6": 10_000_000,
                "position_value_e6": 10_100_000,
                "hodl_value_e6": 10_000_000,
                "fees_earned_e6": 50_000,
                "gas_cost_e6": 0,
                "net_vs_hodl_e6": 150_000,
                "net_vs_hodl_bps": 150.0,
                "status": status,
            }
        )
    return {
        "complete": True,
        "status": "complete",
        "min_audited_positions": 3,
        "summary": {
            "complete_positions": 3,
            "net_vs_hodl_e6": 450_000,
            "net_vs_hodl_bps": 150.0,
        },
        "breadth": {"pool_pairs": 2, "fee_tiers": 3, "range_statuses": 2},
        "rows": rows,
    }


def test_economic_suite_contains_required_sections() -> None:
    data = suite(C.repo_root())

    benchmark_names = {(row["window"], row["name"]) for row in data["benchmarks"]}
    assert ("calm", "PegGuard selected") in benchmark_names
    assert ("vol", "PegGuard selected") in benchmark_names
    assert ("calm", "naive raw deviation") in benchmark_names
    assert ("vol", "static 30 bps") in benchmark_names

    assert data["parity"]["calm"]["precision_bps"] == 9242
    assert data["parity"]["vol"]["capture_truth_bps"] == 2556

    route_windows = {row["window"] for row in data["route_away"]}
    assert {"calm", "vol"}.issubset(route_windows)
    assert any(row["route_away"] == 0.25 for row in data["route_away"])

    assert data["policies"]
    assert data["gas_sensitivity"]
    assert data["gas_adjusted_policies"]
    assert any(row["scenario"] == "hook + Pyth, stressed L2" for row in data["gas_sensitivity"])
    assert any(row["policy"] == "small active" for row in data["gas_adjusted_policies"])
    assert data["range_stress"]
    assert {"calm", "vol"}.issubset({row["window"] for row in data["range_stress"]})
    assert any(row["policy"] == "exit recenter +/-1%" for row in data["range_stress"])
    assert any(row["kind"] == "same-pair fee-tier proxy" for row in data["coverage"])
    assert any(row["kind"] == "controlled route-away experiment" and not row["covered"] for row in data["coverage"])
    assert any(not row["covered"] for row in data["coverage"])


def test_economic_suite_accepts_live_db_override() -> None:
    root = C.repo_root()
    live_db = root / "shadow" / "shadow.sqlite3"
    data = suite(root, live_db)

    assert any(row["source"] == str(live_db) for row in data["coverage"])


def test_economic_suite_interpretation_tracks_live_sample_sign() -> None:
    data = suite(C.repo_root())
    live = next(row for row in data["benchmarks"] if row["window"] == "live shadow")
    live["net_bps"] = -0.09

    text = economic_suite_markdown(data)

    assert "economically positive in calm and current live-shadow samples" not in text
    assert "current live-shadow sample is negative" in text


def test_economic_gate_live_evidence_requires_same_database() -> None:
    economic_tests = {
        "coverage": [
            {
                "kind": "forward shadow sample",
                "source": "shadow/other.sqlite3",
                "events": 100,
            }
        ],
        "benchmarks": [{"window": "live shadow", "rows": 100}],
    }
    live_status = {
        "database": "shadow/live_shadow_20260607T082122Z.sqlite3",
        "swaps": 120,
    }

    assert not _live_evidence_consistent(economic_tests, live_status)
    assert "shadow/other.sqlite3" in _live_evidence_observed(economic_tests, live_status)

    economic_tests["coverage"][0]["source"] = "shadow/live_shadow_20260607T082122Z.sqlite3"
    assert _live_evidence_consistent(economic_tests, live_status)


def test_live_shadow_metric_requires_truth_rows(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    conn.execute(
        """
        INSERT INTO ledger (
            ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
            ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
            fresh_premium_pips, fresh_fallback_reason, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1_700_000_000_000,
            1,
            "0x1",
            0,
            "2000000000000000000000",
            "2000000000000000000000",
            "1000000000000000000",
            2_000_000_000,
            1,
            "CALM",
            10_000,
            5,
            "",
            1_700_000_000_000,
        ),
    )
    conn.commit()

    assert live_shadow_metric(C.repo_root(), db) is None


def test_truth_backfill_labels_stale_fallback_rows_with_recorded_fair(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    for idx, reason in ((1, "STALE_OR_MISSING"), (2, "")):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_fair_e18,
                fresh_extra_e6, fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                1_700_000_000_000 + idx * 1_000,
                idx,
                f"0x{idx}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                2_000_000_000,
                1,
                "VOLATILE",
                "2000000000000000000000",
                0,
                0,
                reason,
                1_700_000_000_000,
            ),
        )
    conn.commit()

    count = process_delayed_truth(conn, now_ms=1_700_000_500_000, delay_sec=360)
    stale_truth = conn.execute("SELECT valid FROM truth WHERE ledger_id = 1").fetchone()
    conn.close()

    assert count == 2
    assert stale_truth is not None
    assert stale_truth["valid"] == 1


def test_route_away_proxy_summary_and_markdown() -> None:
    data = route_proxy_summarize(
        [
            {"fee_pips": 100, "pool": "0x1", "swaps": 2, "notional_e6": 100_000_000, "fee_e6": 10_000},
            {"fee_pips": 500, "pool": "0x2", "swaps": 3, "notional_e6": 300_000_000, "fee_e6": 150_000},
            {"fee_pips": 3000, "pool": "0x3", "swaps": 1, "notional_e6": 100_000_000, "fee_e6": 300_000},
        ],
        10,
        20,
        1_700_000_000_000,
        1_700_003_600_000,
        "arbitrum",
        "WETH/USDT",
        1,
        6,
    )

    assert data["total_notional_e6"] == 500_000_000
    assert data["high_fee_volume_share"] == 0.2
    assert data["pair"] == "WETH/USDT"
    assert data["quote_token_index"] == 1
    assert parse_fee_pool("500:0xpool").fee_pips == 500
    text = route_proxy_markdown(data)
    assert "Route-Away Proxy" in text
    assert "WETH/USDT" in text
    assert "controlled route-away experiment" in text


def test_depth_proxy_band_depth_is_monotonic() -> None:
    sqrt_price_x96 = 2_000 * (1 << 96)
    liquidity = 10**18

    depth_10 = depth_for_band(sqrt_price_x96, liquidity, 10, quote_token_index=1, quote_decimals=6)
    depth_50 = depth_for_band(sqrt_price_x96, liquidity, 50, quote_token_index=1, quote_decimals=6)

    assert depth_10.min_side_quote_e6 > 0
    assert depth_50.min_side_quote_e6 > depth_10.min_side_quote_e6


def test_depth_proxy_markdown_contains_pair_and_band_totals() -> None:
    data = depth_summarize(
        [
            DepthRow(
                fee_pips=500,
                pool="0xpool",
                sqrt_price_x96=1,
                tick=0,
                liquidity=100,
                depths=[BandDepth(band_bps=10, up_quote_e6=100, down_quote_e6=90, min_side_quote_e6=90)],
            )
        ],
        123,
        "arbitrum",
        "WETH/USDC",
        1,
        6,
    )

    text = depth_markdown(data)

    assert "Fee-Tier Depth Proxy" in text
    assert "WETH/USDC" in text
    assert "10 bps" in text


def test_route_cost_proxy_ranks_fee_tiers_with_depth() -> None:
    root = C.repo_root()
    report = route_cost_compute(root / "docs" / "depth_proxy.json", root / "docs" / "depth_proxy_weth_usdt.json")
    text = route_cost_markdown(report)
    rows = report["rows"]
    pairs = {row["pair"] for row in rows}
    weth_usdc_50k_5bps = next(
        row
        for row in rows
        if row["pair"] == "WETH/USDC" and row["trade_size_e6"] == 50_000_000_000 and row["fee_pips"] == 500
    )

    assert {"WETH/USDC", "WETH/USDT"}.issubset(pairs)
    assert weth_usdc_50k_5bps["total_cost_bps"] is not None
    assert weth_usdc_50k_5bps["pegguard_headroom_bps"] is not None
    assert "Depth-Adjusted Route Cost Proxy" in text
    assert "5 bps headroom" in text


def test_quote_route_readiness_reports_missing_inputs_and_complete_artifact(tmp_path) -> None:
    missing = quote_route_readiness_compute(C.repo_root(), env={}, quote_json_path=tmp_path / "missing.json")
    text = quote_route_readiness_markdown(missing)

    assert missing["status"] == "missing inputs"
    assert "rpc_http" in missing["missing_inputs"]
    assert "Quote Route Readiness" in text

    complete_json = tmp_path / "quote_route_quotes.json"
    complete_json.write_text('{"rows": [{"status": "quoted"}]}', encoding="utf-8")
    complete = quote_route_readiness_compute(C.repo_root(), env={}, quote_json_path=complete_json)

    assert complete["status"] == "complete"
    assert complete["quote_result_complete"]


def test_quote_route_collect_ranks_fake_quoter_outputs() -> None:
    def fake_runner(cmd, **_kwargs):
        output = "1000 [1e3]\n1\n2\n30000 [3e4]\n" if ",500," in cmd[4] else "900 [9e2]\n1\n2\n50000 [5e4]\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=output, stderr="")

    report = quote_route_collect_compute(
        rpc_http="https://example.invalid",
        quoter="0x0000000000000000000000000000000000000001",
        token_in="0x0000000000000000000000000000000000000002",
        token_out="0x0000000000000000000000000000000000000003",
        token_in_decimals=6,
        token_out_decimals=18,
        fee_tiers=(500, 3000),
        amount_ins=(1_000_000,),
        chain="testchain",
        runner=fake_runner,
    )
    text = quote_route_collect_markdown(report)
    best = next(row for row in report["rows"] if row["fee_pips"] == 500)
    worse = next(row for row in report["rows"] if row["fee_pips"] == 3000)

    assert best["rank"] == 1
    assert report["chain"] == "testchain"
    assert best["gas_estimate"] == 30000
    assert worse["rank"] == 2
    assert worse["cost_bps_vs_best"] == 1000
    assert "Quote Route Measurements" in text


def test_quote_headroom_report_uses_next_best_when_5bps_is_best(tmp_path) -> None:
    quote_json = tmp_path / "quotes.json"
    quote_json.write_text(
        json.dumps(
            {
                "rows": [
                    {"amount_in_raw": 1, "fee_pips": 500, "amount_out_raw": 1_000, "rank": 1, "status": "quoted"},
                    {"amount_in_raw": 1, "fee_pips": 3000, "amount_out_raw": 990, "rank": 2, "status": "quoted"},
                    {"amount_in_raw": 2, "fee_pips": 500, "amount_out_raw": 995, "rank": 2, "status": "quoted"},
                    {"amount_in_raw": 2, "fee_pips": 3000, "amount_out_raw": 1_000, "rank": 1, "status": "quoted"},
                ]
            }
        ),
        encoding="utf-8",
    )
    report = quote_headroom_compute(quote_json)
    text = quote_headroom_markdown(report)
    best_row = next(row for row in report["rows"] if row["amount_in_raw"] == 1)
    behind_row = next(row for row in report["rows"] if row["amount_in_raw"] == 2)

    assert best_row["premium_headroom_bps"] == 100
    assert best_row["limiting_fee_pips"] == 3000
    assert behind_row["premium_headroom_bps"] < 0
    assert "Quote Premium Headroom" in text
    assert "headroom vs next best" in text


def test_quote_headroom_stability_compares_repeat_snapshots(tmp_path) -> None:
    baseline = tmp_path / "baseline.json"
    repeat = tmp_path / "repeat.json"
    baseline.write_text(
        json.dumps(
            {
                "block_tag": "100",
                "rows": [
                    {"amount_in_raw": 1, "fee_pips": 500, "amount_out_raw": 1_000, "rank": 1, "status": "quoted"},
                    {"amount_in_raw": 1, "fee_pips": 3000, "amount_out_raw": 990, "rank": 2, "status": "quoted"},
                ],
            }
        ),
        encoding="utf-8",
    )
    repeat.write_text(
        json.dumps(
            {
                "block_tag": "200",
                "rows": [
                    {"amount_in_raw": 1, "fee_pips": 500, "amount_out_raw": 1_100, "rank": 1, "status": "quoted"},
                    {"amount_in_raw": 1, "fee_pips": 3000, "amount_out_raw": 1_080, "rank": 2, "status": "quoted"},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = quote_stability_compute([SnapshotSpec("WETH/USDC", baseline, repeat)])
    text = quote_stability_markdown(report)
    row = report["rows"][0]

    assert report["complete"]
    assert row["passed"]
    assert row["repeat_block_tag"] == "200"
    assert row["repeat_headroom_bps"] > 0
    assert "Quote Headroom Stability" in text


def test_quote_headroom_drift_requires_time_diverse_positive_headroom(tmp_path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    single = tmp_path / "single.json"
    for path, block, peg_out, alt_out in (
        (first, "100", 1_000, 990),
        (second, "200", 1_100, 1_085),
        (single, "100", 1_000, 990),
    ):
        path.write_text(
            json.dumps(
                {
                    "block_tag": block,
                    "generated_at": f"{block}-generated",
                    "rows": [
                        {"amount_in_raw": 1, "fee_pips": 500, "amount_out_raw": peg_out, "rank": 1, "status": "quoted"},
                        {"amount_in_raw": 1, "fee_pips": 3000, "amount_out_raw": alt_out, "rank": 2, "status": "quoted"},
                    ],
                }
            ),
            encoding="utf-8",
        )

    complete = quote_drift_compute(paths_by_pair={"WETH/USDC": [first, second], "WETH/USDT": [first, second]})
    text = quote_drift_markdown(complete)
    weak = quote_drift_compute(paths_by_pair={"WETH/USDC": [single], "WETH/USDT": [single]})

    assert complete["complete"]
    assert complete["distinct_block_count"] == 2
    assert complete["rows"][0]["passed"]
    assert "Quote Headroom Drift" in text
    assert not weak["complete"]
    assert weak["rows"][0]["status"] == "single block only"


def test_quote_premium_stress_buckets_premium_against_headroom() -> None:
    buckets = quote_buckets(
        {
            "rows": [
                {
                    "amount_in_raw": 1,
                    "peg_amount_out_raw": 1_000_000_000,
                    "premium_headroom_bps": 1.0,
                    "premium_headroom_pips": 100,
                    "status": "headroom vs next best",
                },
                {
                    "amount_in_raw": 2,
                    "peg_amount_out_raw": 10_000_000_000,
                    "premium_headroom_bps": -0.5,
                    "premium_headroom_pips": -50,
                    "status": "behind best",
                },
            ]
        }
    )
    rows = stress_rows(
        "sample",
        [
            StressEvent(1, 500_000_000, 50, 25_000, 1),
            StressEvent(2, 2_000_000_000, 200, 400_000, 0),
            StressEvent(3, 20_000_000_000, 10, 200_000, 1),
        ],
        buckets,
    )
    text = quote_premium_stress_markdown({"quote_headroom_source": "test", "model": "test", "rows": [row.__dict__ for row in rows]})
    small = rows[0]
    large = rows[1]

    assert small.excess_e6 == 0
    assert large.premium_budget_pips == 0
    assert large.over_headroom_rows == 2
    assert large.over_quote_max_rows == 1
    assert large.excess_e6 == 600_000
    assert large.excess_share_of_extra == 1
    assert "Quote Premium Stress" in text


def test_quote_event_headroom_interpolates_premium_budget(tmp_path) -> None:
    quote_headroom = tmp_path / "quote_headroom.json"
    quote_headroom.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "amount_in_raw": 1,
                        "peg_amount_out_raw": 1_000_000_000,
                        "premium_headroom_bps": 1.0,
                        "premium_headroom_pips": 100,
                        "status": "headroom vs next best",
                    },
                    {
                        "amount_in_raw": 2,
                        "peg_amount_out_raw": 3_000_000_000,
                        "premium_headroom_bps": 3.0,
                        "premium_headroom_pips": 300,
                        "status": "headroom vs next best",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    buckets = quote_buckets(json.loads(quote_headroom.read_text(encoding="utf-8")))
    midpoint = event_budget(StressEvent(1, 2_000_000_000, 250, 500_000, 1), buckets)
    above = event_budget(StressEvent(2, 4_000_000_000, 400, 1_600_000, 0), buckets)
    report = quote_event_headroom_compute(C.repo_root(), tmp_path / "missing.sqlite3", quote_headroom)
    text = quote_event_headroom_markdown(report)
    vol = next(row for row in report["rows"] if row["window"] == "vol")

    assert midpoint.budget_pips == 200
    assert above.budget_pips == 300
    assert above.relation == "above_max"
    assert vol["charged_rows"] > 0
    assert vol["excess_e6"] >= 0
    assert "Quote Event Headroom" in text
    assert "linearly interpolates" in text


def test_quote_provenance_audits_pinned_and_latest_artifacts(tmp_path) -> None:
    latest = tmp_path / "latest.json"
    pinned = tmp_path / "pinned.json"
    latest.write_text(
        json.dumps(
            {
                "chain": "arbitrum",
                "block_tag": "latest",
                "fee_tiers": [500],
                "amount_ins": [1],
                "rows": [{"amount_in_raw": 1, "status": "quoted"}],
            }
        ),
        encoding="utf-8",
    )
    pinned.write_text(
        json.dumps(
            {
                "chain": "arbitrum",
                "block_tag": "123",
                "generated_at": "2026-06-07T00:00:00Z",
                "fee_tiers": [500],
                "amount_ins": [1],
                "rows": [{"amount_in_raw": 1, "status": "quoted"}],
            }
        ),
        encoding="utf-8",
    )

    report = quote_provenance_compute(
        tmp_path,
        {
            "latest quote": latest,
            "pinned quote": pinned,
        },
    )
    text = quote_provenance_markdown(report)

    assert report["complete"]
    assert report["quoted_rows"] == 2
    assert report["latest_block_tag_artifacts"] == 1
    assert report["pinned_block_artifacts"] == 1
    assert report["missing_generated_at_artifacts"] == 1
    assert any("unpinned block tag" in warning for warning in report["warnings"])
    assert "Quote Provenance Audit" in text
    assert "`latest` block-tag artifacts: 1" in text


def test_quote_elasticity_report_scales_real_headroom(tmp_path) -> None:
    quote_headroom = tmp_path / "quote_headroom.json"
    quote_headroom.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "amount_in_raw": 1,
                        "peg_amount_out_raw": 10_000_000_000,
                        "premium_headroom_bps": 5.0,
                        "premium_headroom_pips": 500,
                        "status": "headroom vs next best",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = quote_elasticity_compute(C.repo_root(), tmp_path / "missing.sqlite3", quote_headroom)
    text = quote_elasticity_markdown(report)
    rows = {(row["window"], row["budget_margin"]): row for row in report["rows"]}

    assert {1.0, 0.5, 0.25, 0.1}.issubset({row["budget_margin"] for row in report["rows"]})
    assert rows[("vol", 0.1)]["lost_extra_e6"] >= rows[("vol", 1.0)]["lost_extra_e6"]
    assert rows[("vol", 0.1)]["retained_extra_e6"] <= rows[("vol", 1.0)]["retained_extra_e6"]
    assert "Quote-Headroom Route Elasticity" in text


def test_route_demand_curve_removes_flow_above_tolerance() -> None:
    rows = demand_rows(
        "sample",
        [
            DemandEvent(1, 1_000_000_000, 50, 50_000, 1, 300_000),
            DemandEvent(2, 1_000_000_000, 250, 250_000, 1, 1_000_000),
            DemandEvent(3, 1_000_000_000, 0, 0, 0, -100_000),
        ],
        (1.0, 5.0),
    )
    text = route_demand_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    one_bps = next(row for row in rows if row.tolerance_bps == 1.0)
    five_bps = next(row for row in rows if row.tolerance_bps == 5.0)

    assert one_bps.routed_rows == 1
    assert one_bps.lost_extra_e6 == 250_000
    assert one_bps.avoided_markout_e6 == 1_000_000
    assert one_bps.delta_vs_full_e6 > 0
    assert five_bps.routed_rows == 0
    assert five_bps.delta_vs_full_e6 == 0
    assert "Route-Away Demand Curve" in text


def test_premium_utilization_tracks_cap_pressure_and_concentration() -> None:
    row = utilization_row(
        "sample",
        [
            PremiumEvent(100_000_000, 0, 0, 0),
            PremiumEvent(100_000_000, 100, 10_000, 1),
            PremiumEvent(100_000_000, C.CAP_PIPS, 500_000, 1),
            PremiumEvent(100_000_000, int(C.CAP_PIPS * 0.8), 400_000, 0),
        ],
    )
    text = premium_utilization_markdown({"cap_pips": C.CAP_PIPS, "near_cap_threshold_pips": int(C.CAP_PIPS * 0.8), "rows": [row.__dict__]})

    assert row.charged_rows == 3
    assert row.cap_hit_rows == 1
    assert row.near_cap_rows == 2
    assert row.precision == 510_000 / 910_000
    assert row.p99_charged_premium_bps == C.CAP_PIPS / 100
    assert row.top_10pct_extra_share == 500_000 / 910_000
    assert "Premium Utilization" in text


def test_charge_attribution_splits_charged_and_missed_truth_buckets() -> None:
    report_window = attribution_window(
        "sample",
        [
            ChargeEvent(100_000_000, 100, 10_000, 1, 1_000_000),
            ChargeEvent(100_000_000, 100, 10_000, 0, 500_000),
            ChargeEvent(100_000_000, 0, 0, 1, 2_000_000),
            ChargeEvent(100_000_000, 0, 0, 0, 100_000),
        ],
    )
    text = charge_attribution_markdown(
        {"windows": [{**report_window.__dict__, "buckets": [bucket.__dict__ for bucket in report_window.buckets]}]}
    )
    buckets = {bucket.bucket: bucket for bucket in report_window.buckets}

    assert report_window.precision == 0.5
    assert report_window.false_charge_extra_share == 0.5
    assert report_window.truth_correcting_row_recall == 0.5
    assert report_window.truth_correcting_markout_coverage == 1_000_000 / 3_000_000
    assert buckets["missed correcting"].rows == 1
    assert buckets["missed correcting"].abs_truth_markout_e6 == 2_000_000
    assert "Charge Attribution" in text


def test_live_status_gates(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    conn.execute(
        """
        INSERT INTO ledger (
            id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
            ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
            fresh_premium_pips, fresh_fallback_reason, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1_700_000_000_000,
            1,
            "0x1",
            0,
            "2000000000000000000000",
            "2000000000000000000000",
            "1000000000000000000",
            2_000_000_000,
            1,
            "CALM",
            10_000,
            5,
            "",
            1_700_000_000_000,
        ),
    )
    conn.execute(
        """
        INSERT INTO truth (
            ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (1, 1, "1000000000000000000", 1, 1, 100_000, 1_700_000_001_000),
    )
    conn.commit()

    status = compute_status(db, min_hours=0, min_truth_coverage=0.5, min_swaps=1)

    assert status.complete
    assert status.truth_coverage == 1
    assert status.min_span_hours == 0
    assert status.remaining_span_hours == 0
    text = live_status_markdown(status)
    assert "Live Shadow Status" in text
    assert "Remaining span required: 0.00 hours" in text
    assert "truth coverage" in text

    incomplete = compute_status(db, min_hours=24, min_truth_coverage=0.5, min_swaps=1)
    assert not incomplete.complete
    assert incomplete.min_span_hours == 24
    assert incomplete.remaining_span_hours == 24


def test_cross_pair_live_report_summarizes_primary_and_second_pair(tmp_path) -> None:
    primary = tmp_path / "primary.sqlite3"
    cross = tmp_path / "cross.sqlite3"
    for db, pair_index in ((primary, 1), (cross, 2)):
        conn = connect(db)
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                1_700_000_000_000,
                pair_index,
                f"0x{pair_index}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                2_000_000_000,
                1,
                "CALM",
                10_000,
                5,
                "",
                1_700_000_000_000,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (1, 1, "1000000000000000000", 1, 1, 100_000, 1_700_000_001_000),
        )
        conn.commit()
        conn.close()

    report = cross_pair_live_compute(
        [
            CrossPairLiveSpec("primary", "WETH/USDC", primary),
            CrossPairLiveSpec("cross-pair", "WETH/USDT", cross),
        ],
        min_hours=0,
        min_truth_coverage=0.5,
        min_swaps=1,
    )
    text = cross_pair_live_markdown(report)

    assert report["complete"]
    assert [row["pair"] for row in report["rows"]] == ["WETH/USDC", "WETH/USDT"]
    assert all(row["swaps"] == 1 for row in report["rows"])
    assert "Cross-Pair Live Shadow" in text
    assert "WETH/USDT" in text


def test_live_soak_report_tracks_multiple_horizons(tmp_path) -> None:
    db = tmp_path / "primary.sqlite3"
    conn = connect(db)
    for row_id, ts_ms in ((1, 1_700_000_000_000), (2, 1_700_090_000_000)):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                ts_ms,
                row_id,
                f"0x{row_id}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                2_000_000_000,
                1,
                "CALM",
                10_000,
                5,
                "",
                ts_ms,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, 1, "1000000000000000000", 1, 1, 100_000, ts_ms + 1_000),
        )
    conn.commit()
    conn.close()

    missing = tmp_path / "missing.sqlite3"
    report = live_soak_compute(
        [
            LiveSoakSpec("primary", "WETH/USDC", db),
            LiveSoakSpec("cross-pair", "WETH/USDT", missing),
        ],
        horizons=(24.0, 72.0, 168.0),
        min_truth_coverage=0.5,
        min_swaps=1,
    )
    text = live_soak_markdown(report)

    assert not report["complete"]
    assert len(report["rows"]) == 6
    primary_rows = [row for row in report["rows"] if row["pair"] == "WETH/USDC"]
    assert primary_rows[0]["complete"]
    assert not primary_rows[1]["complete"]
    assert primary_rows[0]["observed_span_hours"] == 25
    assert "Live Soak Tracker" in text
    assert "7d" in text
    assert "non-gating" in text


def test_cross_pair_live_economics_reuses_live_quality_reports(tmp_path) -> None:
    primary = tmp_path / "primary.sqlite3"
    cross = tmp_path / "cross.sqlite3"
    for db, block_base in ((primary, 1), (cross, 100)):
        conn = connect(db)
        for row_id, ts_ms, premium, extra, truth_corr in (
            (1, 1_700_000_000_000, 5, 10_000, 1),
            (2, 1_700_003_700_000, 0, 0, 0),
        ):
            conn.execute(
                """
                INSERT INTO ledger (
                    id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                    ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                    fresh_premium_pips, fresh_fallback_reason, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ts_ms,
                    block_base + row_id,
                    f"0x{block_base + row_id}",
                    0,
                    "2000000000000000000000",
                    "2000000000000000000000",
                    "1000000000000000000",
                    2_000_000_000,
                    1,
                    "CALM",
                    extra,
                    premium,
                    "",
                    ts_ms,
                ),
            )
            conn.execute(
                """
                INSERT INTO truth (
                    ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row_id, 1, "1000000000000000000", 1, truth_corr, 100_000, ts_ms + 1_000),
            )
        conn.commit()
        conn.close()

    report = cross_pair_live_economics_compute(
        [
            CrossPairLiveEconomicsSpec("primary", "WETH/USDC", primary),
            CrossPairLiveEconomicsSpec("cross-pair", "WETH/USDT", cross),
        ]
    )
    text = cross_pair_live_economics_markdown(report)

    assert report["complete"]
    assert [row["pair"] for row in report["rows"]] == ["WETH/USDC", "WETH/USDT"]
    assert all(row["convergence_complete"] for row in report["rows"])
    assert all(row["maturity_complete"] for row in report["rows"])
    assert all(row["power_complete"] for row in report["rows"])
    assert "Cross-Pair Live Economics" in text
    assert "WETH/USDT" in text


def test_live_fee_tier_report_tracks_same_pair_out_of_sample(tmp_path) -> None:
    primary = tmp_path / "primary.sqlite3"
    one_bps = tmp_path / "live_shadow_weth_usdc_1bps_20260607T000000Z.sqlite3"
    for db, block_base in ((primary, 1), (one_bps, 100)):
        conn = connect(db)
        for row_id, ts_ms, premium, extra, truth_corr in (
            (1, 1_700_000_000_000, 5, 10_000, 1),
            (2, 1_700_003_700_000, 0, 0, 0),
        ):
            conn.execute(
                """
                INSERT INTO ledger (
                    id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                    ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                    fresh_premium_pips, fresh_fallback_reason, created_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row_id,
                    ts_ms,
                    block_base + row_id,
                    f"0x{block_base + row_id}",
                    0,
                    "2000000000000000000000",
                    "2000000000000000000000",
                    "1000000000000000000",
                    2_000_000_000,
                    1,
                    "CALM",
                    extra,
                    premium,
                    "",
                    ts_ms,
                ),
            )
            conn.execute(
                """
                INSERT INTO truth (
                    ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row_id, 1, "1000000000000000000", 1, truth_corr, 100_000, ts_ms + 1_000),
            )
        conn.commit()
        conn.close()

    report = live_fee_tier_compute(
        [
            LiveFeeTierSpec("primary", "WETH/USDC", 500, database=primary),
            LiveFeeTierSpec("same-pair 1bps", "WETH/USDC", 100, database_glob=str(tmp_path / "live_shadow_weth_usdc_1bps_*.sqlite3")),
            LiveFeeTierSpec("same-pair 30bps", "WETH/USDC", 3000, database_glob=str(tmp_path / "live_shadow_weth_usdc_30bps_*.sqlite3")),
        ],
        min_truth_coverage=0.5,
        min_swaps=1,
    )
    text = live_fee_tier_markdown(report)

    assert report["complete"]
    assert [row["fee_pips"] for row in report["rows"]] == [500, 100, 3000]
    assert report["rows"][1]["database"] == str(one_bps)
    assert report["rows"][1]["precision"] == 1
    assert report["rows"][1]["quality_status"] == "immature"
    assert report["rows"][2]["status"] == "missing"
    assert "Fee-Tier Live Shadow" in text
    assert "WETH/USDC" in text
    assert "1.00 bps" in text
    assert "30.00 bps" in text
    assert "Immature-row threshold" in text


def test_live_convergence_segments_live_economics(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    for row_id, ts_ms, aq_e6, premium_pips, extra_e6, fallback, truth_corr, truth_mk_e6 in (
        (1, 1_700_000_000_000, 100_000_000, 1_000, 100_000, "", 1, 1_000_000),
        (2, 1_700_003_700_000, 200_000_000, 500, 100_000, "STALE", 0, 500_000),
    ):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                ts_ms,
                row_id,
                f"0x{row_id}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                aq_e6,
                1,
                "CALM",
                extra_e6,
                premium_pips,
                fallback,
                ts_ms,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, 1, "1000000000000000000", 1, truth_corr, truth_mk_e6, ts_ms + 1_000),
        )
    conn.commit()
    conn.close()

    report = live_convergence_compute(db, bucket_sec=3600)
    text = live_convergence_markdown(report)

    assert report["complete"]
    assert report["bucket_count"] == 2
    assert report["charged_rows"] == 2
    assert report["precision"] == 0.5
    assert report["capture_truth"] == 200_000 / 1_500_000
    assert report["convergence_rows"][1]["fallback_notional_share"] == 1.0
    assert "Live Shadow Convergence" in text


def test_live_maturity_tracks_cumulative_live_economics(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    for row_id, ts_ms, aq_e6, premium_pips, extra_e6, fallback, truth_corr, truth_mk_e6 in (
        (1, 1_700_000_000_000, 100_000_000, 1_000, 100_000, "", 1, 1_000_000),
        (2, 1_700_003_700_000, 200_000_000, 500, 100_000, "STALE", 0, 500_000),
    ):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                ts_ms,
                row_id,
                f"0x{row_id}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                aq_e6,
                1,
                "CALM",
                extra_e6,
                premium_pips,
                fallback,
                ts_ms,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, 1, "1000000000000000000", 1, truth_corr, truth_mk_e6, ts_ms + 1_000),
        )
    conn.commit()
    conn.close()

    report = live_maturity_compute(db, checkpoint_sec=3600)
    text = live_maturity_markdown(report)

    assert report["complete"]
    assert report["checkpoint_count"] == 2
    assert report["charged_rows"] == 2
    assert report["precision"] == 0.5
    assert report["capture_truth"] == 200_000 / 1_500_000
    assert report["maturity_rows"][0]["precision_delta_vs_final"] == 0.5
    assert report["maturity_rows"][1]["capture_delta_vs_final"] == 0
    assert "Live Shadow Maturity" in text


def test_live_power_estimates_required_hours_from_buckets(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    for row_id, ts_ms, aq_e6, premium_pips, extra_e6, truth_corr, truth_mk_e6 in (
        (1, 1_700_000_000_000, 100_000_000, 1_000, 100_000, 1, 1_000_000),
        (2, 1_700_003_700_000, 200_000_000, 500, 100_000, 0, 500_000),
        (3, 1_700_007_300_000, 150_000_000, 500, 75_000, 1, 200_000),
    ):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                ts_ms,
                row_id,
                f"0x{row_id}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                aq_e6,
                1,
                "CALM",
                extra_e6,
                premium_pips,
                "",
                ts_ms,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (row_id, 1, "1000000000000000000", 1, truth_corr, truth_mk_e6, ts_ms + 1_000),
        )
    conn.commit()
    conn.close()

    report = live_power_compute(db, bucket_sec=3600)
    text = live_power_markdown(report)
    metrics = {row["metric"]: row for row in report["metrics"]}

    assert report["complete"]
    assert report["bucket_count"] == 3
    assert {"net_bps", "capture_truth", "precision"}.issubset(metrics)
    assert metrics["net_bps"]["ci95_half_width"] is not None
    assert metrics["net_bps"]["estimated_required_hours"] is not None
    assert "Live Sample Power" in text
    assert "Additional hours" in text


def test_guard_depeg_report_uses_sentinel_fixture_economics() -> None:
    report = guard_depeg_compute(C.repo_root())
    text = guard_depeg_markdown(report)
    selected = next(row for row in report["rows"] if row["label"] == "selected")
    comparison = next(row for row in report["rows"] if row["label"] == "60bps comparison")

    assert report["complete"]
    assert selected["calm_triggers"] == 0
    assert selected["vol_triggers"] == 6
    assert selected["bled_before_first_trigger_e6"] == 0
    assert comparison["bled_before_first_trigger_e6"] == 2_399_213_733
    assert "GUARD Breaker Economics" in text
    assert "stablecoin depeg PnL backtest" in text


def test_stable_opportunity_report_documents_no_harvest_decision() -> None:
    report = stable_opportunity_compute(C.repo_root())
    text = stable_opportunity_markdown(report)

    assert report["complete"]
    assert report["directional_fee_policy"] == "disabled"
    assert report["normal_stable_max_bps"] == 0.35
    assert report["best_directional_capture_pct"] == 0.063
    assert report["trip_to_normal_ratio"] > 100
    assert "GUARD Stable Opportunity Audit" in text
    assert "do not charge directional premium" in text


def test_route_away_ab_evaluator() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {
            "baseline_notional_e6": 1_000_000_000,
            "treatment_notional_e6": 1_000_000_000,
            "treatment_fee_pips": 500,
        },
        "post": {
            "baseline_notional_e6": 1_200_000_000,
            "treatment_notional_e6": 800_000_000,
            "treatment_fee_pips": 700,
        },
    }
    route_ab_validate_payload(payload)
    result = route_ab_evaluate(payload)

    assert result.expected_post_treatment_e6 == 1_000_000_000
    assert result.routed_away_e6 == 200_000_000
    assert result.route_away_rate == 0.2
    assert result.fee_delta_bps == 2
    assert result.elasticity_per_bps == 0.1
    assert "Controlled Route-Away Experiment" in route_ab_markdown(result)


def test_route_away_ab_evidence_requires_collection_metadata() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
    }

    route_ab_validate_payload(payload)

    assert "controlled route-away evidence requires evaluated result artifact with valid=true" in route_ab_evidence_errors(payload)
    assert "controlled route-away evidence requires collection metadata" in route_ab_evidence_errors(payload)


def test_route_away_ab_evidence_requires_evaluated_artifact() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "0xbase",
        "treatment": "0xPoolManager",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1_000_000,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1_000_000,
            },
            "post_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1_200_000,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 800_000,
            },
        },
    }

    route_ab_validate_payload(payload)

    assert route_ab_evidence_errors(payload) == [
        "controlled route-away evidence requires evaluated result artifact with valid=true"
    ]


def test_route_away_ab_validation_rejects_placeholder_input() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0, "treatment_fee_pips": 500},
    }
    try:
        route_ab_validate_payload(payload)
    except ValueError as exc:
        text = str(exc)
        assert "pre baseline_notional_e6 must be > 0" in text
        assert "post treatment_fee_pips must be greater" in text
    else:
        raise AssertionError("expected placeholder controlled route-away input to fail validation")


def test_route_away_ab_writes_invalid_placeholder_artifact(tmp_path) -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline pool or route id",
        "treatment": "PegGuard pool or route id",
        "pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0, "treatment_fee_pips": 500},
    }
    errors = route_ab_validation_errors(payload)
    out_md = tmp_path / "route_away_ab.md"
    out_json = tmp_path / "route_away_ab.json"

    route_ab_write_invalid_outputs(payload, errors, out_md, out_json)
    written = json.loads(out_json.read_text(encoding="utf-8"))
    text = out_md.read_text(encoding="utf-8")

    assert written["valid"] is False
    assert "not route-away evidence" in text
    assert "pre baseline_notional_e6 must be > 0" in text
    assert "Top-level pre/post notionals must match collection" in text
    assert "Evaluated result fields must re-compute" in text


def test_route_away_ab_validation_checks_collection_metadata() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {"start_block": 100, "end_block": 200, "swaps": 1, "quote_notional_e6": 1},
            "pre_treatment": {"start_block": 100, "end_block": 200, "swaps": 1, "quote_notional_e6": 1},
            "post_baseline": {"start_block": 201, "end_block": 350, "swaps": 1, "quote_notional_e6": 1},
            "post_treatment": {"start_block": 201, "end_block": 350, "swaps": 0, "quote_notional_e6": 1},
        },
    }

    try:
        route_ab_validate_payload(payload)
    except ValueError as exc:
        text = str(exc)
        assert "collection.post_treatment swaps must be > 0" in text
        assert "collection pre/post windows must have equal length" in text
    else:
        raise AssertionError("expected invalid collection metadata to fail validation")


def test_route_away_ab_validation_rejects_collection_notional_mismatch() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "0xbase",
        "treatment": "0xPoolManager",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 2_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 3_000_000, "treatment_notional_e6": 4_000_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1_000_000,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 2_000_000,
            },
            "post_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 999,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 4_000_000,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert "collection.post_baseline quote_notional_e6 must match top-level post baseline notional" in errors


def test_route_away_ab_validation_rejects_same_pool_without_v4_disambiguation() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "0xpoolmanager",
        "treatment": "0xPoolManager",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
    }

    errors = route_ab_validation_errors(payload)

    assert any("same PoolManager comparisons require distinct v4 pool ids" in error for error in errors)


def test_route_away_ab_validation_allows_same_poolmanager_with_distinct_v4_pool_ids() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "0xPoolManager",
        "treatment": "0xpoolmanager",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1_000_000,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1_000_000,
            },
            "post_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1_200_000,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 800_000,
            },
        },
    }

    route_ab_validate_payload(payload)


def test_route_away_ab_validation_rejects_same_collection_identity() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "pre_treatment": {
                "pool": "0xpoolmanager",
                "kind": "v4",
                "pool_id": "0x0000000000000000000000000000000000000000000000000000000000000001",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert "collection pre baseline/treatment pools must be distinct" in errors


def test_route_away_ab_validation_rejects_same_address_with_mixed_kinds() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xPoolManager",
                "kind": "v3",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "pre_treatment": {
                "pool": "0xpoolmanager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_baseline": {
                "pool": "0xPoolManager",
                "kind": "v3",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert "collection pre baseline/treatment pools must be distinct" in errors
    assert "collection post baseline/treatment pools must be distinct" in errors


def test_route_away_ab_validation_rejects_invalid_v4_pool_id() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0xnot_hex",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_baseline": {
                "pool": "0xbase",
                "kind": "v3",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert any("collection.pre_treatment pool_id invalid: v4 pool id must be hex bytes32" in error for error in errors)


def test_route_away_ab_validation_rejects_top_level_collection_pool_mismatch() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "0xbase",
        "treatment": "0xPoolManager",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xotherbase",
                "kind": "v3",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_baseline": {
                "pool": "0xotherbase",
                "kind": "v3",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert "collection baseline pool must match top-level baseline" in errors


def test_route_away_ab_validation_rejects_pool_identity_drift_across_windows() -> None:
    payload = {
        "pair": "WETH/USDC",
        "baseline": "baseline",
        "treatment": "pegguard",
        "pre": {"baseline_notional_e6": 1_000_000, "treatment_notional_e6": 1_000_000, "treatment_fee_pips": 500},
        "post": {"baseline_notional_e6": 1_200_000, "treatment_notional_e6": 800_000, "treatment_fee_pips": 700},
        "collection": {
            "pre_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x01",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "pre_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 100,
                "end_block": 200,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_baseline": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x03",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
            "post_treatment": {
                "pool": "0xPoolManager",
                "kind": "v4",
                "pool_id": "0x02",
                "start_block": 201,
                "end_block": 301,
                "swaps": 1,
                "quote_notional_e6": 1,
            },
        },
    }

    errors = route_ab_validation_errors(payload)

    assert "collection baseline pool identity must match across pre/post windows" in errors


def test_route_away_collect_summarizes_quote_notional() -> None:
    logs = [
        SwapLog(1, "0x1", 0, "0xpool", -1_000_000_000_000_000_000, 2_000_000_000, 1, 1, 0),
        SwapLog(2, "0x2", 0, "0xpool", 500_000_000_000_000_000, -1_200_000_000, 1, 1, 0),
    ]

    quote1 = summarize_swaps("0xpool", 1, 2, logs, quote_token_index=1, quote_decimals=6)
    quote0 = summarize_swaps("0xpool", 1, 2, logs, quote_token_index=0, quote_decimals=18)

    assert quote1.swaps == 2
    assert quote1.quote_notional_e6 == 3_200_000_000
    assert quote0.quote_notional_e6 == 1_500_000


def test_route_away_baseline_probe_static_plan() -> None:
    report = route_baseline_probe_compute_static(C.repo_root(), env={"CHAIN_RPC_WSS": "wss://example.invalid"})
    text = route_baseline_probe_markdown(report)

    assert report["status"] == "ready to execute"
    assert report["rpc_url_resolved"]
    assert report["rows"]
    assert all(row["baseline_pool"] for row in report["rows"])
    assert "Route-Away Baseline Flow Probe" in text
    assert "Counts for controlled route-away gate: no" in text


def test_route_away_collect_selects_rpc_transport() -> None:
    assert isinstance(_rpc_client("https://example.invalid", "base"), RpcHttp)
    assert isinstance(_rpc_client("wss://example.invalid", "base"), RpcWs)


class _FakeRouteRpc:
    def __init__(self, chain_id: int = 8453, code_by_address: dict[str, str] | None = None) -> None:
        self.chain_id = chain_id
        self.code_by_address = {key.lower(): value for key, value in (code_by_address or {}).items()}

    async def call(self, _session, method: str, params: list) -> object:
        if method == "eth_chainId":
            return hex(self.chain_id)
        if method == "eth_getCode":
            return self.code_by_address.get(str(params[0]).lower(), "0x1234")
        raise AssertionError(f"unexpected RPC method {method}")


def test_route_away_collect_preflight_accepts_expected_chain_and_contracts() -> None:
    asyncio.run(
        validate_collection_preflight(
            _FakeRouteRpc(),
            object(),
            "base",
            {"baseline": "0xbase", "treatment": "0xpeg"},
        )
    )
    assert _expected_chain_id("chain-1301") == 1301


def test_route_away_collect_preflight_rejects_wrong_chain() -> None:
    try:
        asyncio.run(validate_collection_preflight(_FakeRouteRpc(chain_id=42161), object(), "base", {"baseline": "0xbase"}))
    except ValueError as exc:
        assert "does not match --chain base" in str(exc)
    else:
        raise AssertionError("expected wrong-chain route-away collection to fail")


def test_route_away_collect_preflight_rejects_no_code_address() -> None:
    try:
        asyncio.run(
            validate_collection_preflight(
                _FakeRouteRpc(code_by_address={"0xpeg": "0x"}),
                object(),
                "base",
                {"baseline": "0xbase", "treatment": "0xpeg"},
            )
        )
    except ValueError as exc:
        assert "treatment address has no contract code" in str(exc)
    else:
        raise AssertionError("expected no-code route-away address to fail")


def test_route_away_collect_accepts_valid_collection_config() -> None:
    validate_collection_config(
        "0xbase",
        "0xpeg",
        "v3",
        "v4",
        None,
        "0x01",
        100,
        200,
        201,
        301,
        1,
        6,
        5_000,
    )


def test_route_away_collect_rejects_invalid_collection_windows_before_rpc() -> None:
    try:
        validate_collection_config(
            "0xbase",
            "0xpeg",
            "v3",
            "v4",
            None,
            "0x01",
            200,
            100,
            90,
            300,
            1,
            6,
            5_000,
        )
    except ValueError as exc:
        text = str(exc)
        assert "pre window start must be <= end" in text
        assert "pre window must end before post window starts" in text
    else:
        raise AssertionError("expected invalid route-away collection windows to fail before RPC")


def test_route_away_collect_rejects_unequal_collection_windows_before_rpc() -> None:
    try:
        validate_collection_config(
            "0xbase",
            "0xpeg",
            "v3",
            "v4",
            None,
            "0x01",
            100,
            200,
            201,
            250,
            1,
            6,
            5_000,
        )
    except ValueError as exc:
        assert "pre/post windows must have equal length" in str(exc)
    else:
        raise AssertionError("expected unequal route-away collection windows to fail before RPC")


def test_route_away_collect_rejects_missing_or_invalid_pool_ids_before_rpc() -> None:
    try:
        validate_collection_config(
            "0xbase",
            "0xpeg",
            "v3",
            "v4",
            None,
            "0xnot_hex",
            100,
            200,
            201,
            301,
            1,
            6,
            5_000,
        )
    except ValueError as exc:
        assert "treatment pool id invalid: v4 pool id must be hex bytes32" in str(exc)
    else:
        raise AssertionError("expected invalid route-away v4 pool id to fail before RPC")


def test_route_away_collect_rejects_bad_quote_or_chunk_config_before_rpc() -> None:
    try:
        validate_collection_config(
            "0xbase",
            "0xpeg",
            "v3",
            "v4",
            None,
            "0x01",
            100,
            200,
            201,
            301,
            2,
            0,
            0,
        )
    except ValueError as exc:
        text = str(exc)
        assert "quote token index must be 0 or 1" in text
        assert "quote decimals must be > 0" in text
        assert "chunk blocks must be > 0" in text
    else:
        raise AssertionError("expected bad route-away quote/chunk config to fail before RPC")


def test_route_away_collect_rejects_same_pool_identity() -> None:
    try:
        validate_distinct_pool_identities("0xpool", "0xPool", "v3", "v3", None, None)
    except ValueError as exc:
        assert "requires distinct baseline and treatment pools" in str(exc)
    else:
        raise AssertionError("expected identical route-away pools to fail")


def test_route_away_collect_rejects_same_address_with_mixed_pool_kinds() -> None:
    try:
        validate_distinct_pool_identities("0xpool", "0xPool", "v3", "v4", None, "0x01")
    except ValueError as exc:
        assert "requires distinct baseline and treatment pools" in str(exc)
    else:
        raise AssertionError("expected same-address mixed-kind route-away pools to fail")


def test_route_away_collect_allows_same_poolmanager_with_different_v4_pool_ids() -> None:
    validate_distinct_pool_identities("0xPoolManager", "0xpoolmanager", "v4", "v4", "0x01", "0x02")


def test_route_away_collect_rejects_same_poolmanager_and_same_v4_pool_id() -> None:
    try:
        validate_distinct_pool_identities(
            "0xPoolManager",
            "0xpoolmanager",
            "v4",
            "v4",
            "0x01",
            "0x0000000000000000000000000000000000000000000000000000000000000001",
    )
    except ValueError as exc:
        assert "different pool ids" in str(exc)
    else:
        raise AssertionError("expected identical v4 route-away pool ids to fail")


def test_route_away_collect_rejects_invalid_v4_pool_id_topic() -> None:
    try:
        _log_topics("v4", "0xnot_hex")
    except ValueError as exc:
        assert "v4 pool id must be hex bytes32" in str(exc)
    else:
        raise AssertionError("expected invalid v4 pool id topic to fail")


def test_route_away_collect_payload_feeds_evaluator() -> None:
    payload = build_payload(
        "WETH/USDC",
        "0xbase",
        "0xpeg",
        500,
        700,
        ExperimentWindows(
            PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xpeg", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
            PoolWindowStats("0xpeg", 11, 20, 8, 800_000_000),
        ),
        quote_token_index=1,
        quote_decimals=6,
    )

    result = route_ab_evaluate(payload)

    assert payload["collection"]["post_treatment"]["swaps"] == 8
    assert result.expected_post_treatment_e6 == 1_000_000_000
    assert result.routed_away_e6 == 200_000_000
    assert result.route_away_rate == 0.2


def test_route_away_collect_rejects_zero_notional_windows() -> None:
    windows = ExperimentWindows(
        PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
        PoolWindowStats("0xpeg", 1, 10, 0, 0),
        PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
        PoolWindowStats("0xpeg", 11, 20, 8, 800_000_000),
    )

    try:
        validate_nonzero_windows(windows)
    except ValueError as exc:
        assert "pre treatment" in str(exc)
        assert "quote_notional_e6=0" in str(exc)
    else:
        raise AssertionError("expected zero-notional controlled route-away window to fail")


def test_route_away_collect_decodes_v4_swap_log() -> None:
    def word(value: int) -> str:
        if value < 0:
            value = (1 << 256) + value
        return f"{value:064x}"

    raw = {
        "blockNumber": "0x7b",
        "transactionHash": "0xabc",
        "logIndex": "0x2",
        "address": "0xPoolManager",
        "data": "0x"
        + word(-1_000_000_000_000_000_000)
        + word(2_000_000_000)
        + word(79_228_162_514_264_337_593_543_950_336)
        + word(123)
        + word(-100)
        + word(500),
    }

    decoded = decode_v4_swap_log(raw)
    summary = summarize_swaps(
        "0xPoolManager",
        123,
        123,
        [decoded],
        quote_token_index=1,
        quote_decimals=6,
        kind="v4",
        pool_id="0x01",
    )

    assert decoded.amount0 == -1_000_000_000_000_000_000
    assert decoded.amount1 == 2_000_000_000
    assert decoded.tick == -100
    assert decoded.fee_pips == 500
    assert summary.kind == "v4"
    assert summary.pool_id == "0x01"
    assert summary.quote_notional_e6 == 2_000_000_000
    assert summary.vwap_fee_pips == 500
    assert summary.fee_observation_count == 1


def test_route_away_collect_derives_post_fee_from_v4_window() -> None:
    post_treatment = PoolWindowStats(
        "0xpeg",
        11,
        20,
        8,
        800_000_000,
        kind="v4",
        pool_id="0x01",
        vwap_fee_pips=700,
        fee_observation_count=8,
    )
    payload = build_payload(
        "WETH/USDC",
        "0xbase",
        "0xpeg",
        500,
        None,
        ExperimentWindows(
            PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xpeg", 1, 10, 10, 1_000_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=500),
            PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
            post_treatment,
        ),
        quote_token_index=1,
        quote_decimals=6,
    )

    assert payload["post"]["treatment_fee_pips"] == 700
    assert payload["collection"]["post_treatment"]["vwap_fee_pips"] == 700


def test_route_away_collect_writes_invalid_artifact_for_nonpositive_derived_fee_delta(tmp_path) -> None:
    payload = build_payload(
        "WETH/USDC",
        "0xbase",
        "0xpeg",
        500,
        None,
        ExperimentWindows(
            PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xpeg", 1, 10, 10, 1_000_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=500),
            PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
            PoolWindowStats(
                "0xpeg",
                11,
                20,
                8,
                800_000_000,
                kind="v4",
                pool_id="0x01",
                vwap_fee_pips=500,
                fee_observation_count=8,
            ),
        ),
        quote_token_index=1,
        quote_decimals=6,
    )
    out_input = tmp_path / "route_away_ab_input.json"
    out_md = tmp_path / "route_away_ab.md"
    out_json = tmp_path / "route_away_ab.json"

    errors = write_payload_artifacts(payload, out_input, out_md, out_json)
    written = json.loads(out_json.read_text(encoding="utf-8"))
    text = out_md.read_text(encoding="utf-8")

    assert "post treatment_fee_pips must be greater than pre treatment_fee_pips" in errors
    assert written["valid"] is False
    assert json.loads(out_input.read_text(encoding="utf-8"))["post"]["treatment_fee_pips"] == 500
    assert "not route-away evidence" in text


def test_route_away_collect_preserves_collection_metadata_in_valid_artifact(tmp_path) -> None:
    payload = build_payload(
        "WETH/USDC",
        "0xbase",
        "0xpeg",
        500,
        700,
        ExperimentWindows(
            PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xpeg", 1, 10, 10, 1_000_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=500),
            PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
            PoolWindowStats("0xpeg", 11, 20, 8, 800_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=700),
        ),
        quote_token_index=1,
        quote_decimals=6,
    )
    out_input = tmp_path / "route_away_ab_input.json"
    out_md = tmp_path / "route_away_ab.md"
    out_json = tmp_path / "route_away_ab.json"

    errors = write_payload_artifacts(payload, out_input, out_md, out_json)
    written = json.loads(out_json.read_text(encoding="utf-8"))

    assert errors == []
    assert written["valid"] is True
    assert written["collection"]["post_treatment"]["pool_id"] == "0x01"
    assert route_ab_evidence_errors(written) == []


def test_route_away_ab_evidence_rejects_derived_result_mismatch(tmp_path) -> None:
    payload = build_payload(
        "WETH/USDC",
        "0xbase",
        "0xpeg",
        500,
        700,
        ExperimentWindows(
            PoolWindowStats("0xbase", 1, 10, 10, 1_000_000_000),
            PoolWindowStats("0xpeg", 1, 10, 10, 1_000_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=500),
            PoolWindowStats("0xbase", 11, 20, 12, 1_200_000_000),
            PoolWindowStats("0xpeg", 11, 20, 8, 800_000_000, kind="v4", pool_id="0x01", vwap_fee_pips=700),
        ),
        quote_token_index=1,
        quote_decimals=6,
    )
    out_input = tmp_path / "route_away_ab_input.json"
    out_md = tmp_path / "route_away_ab.md"
    out_json = tmp_path / "route_away_ab.json"
    errors = write_payload_artifacts(payload, out_input, out_md, out_json)
    written = json.loads(out_json.read_text(encoding="utf-8"))

    assert errors == []
    written["route_away_rate"] = 0

    assert "route-away result route_away_rate must match evaluated pre/post windows" in route_ab_evidence_errors(written)


def test_route_away_collector_smoke_decodes_broadcast_without_counting_as_evidence(tmp_path) -> None:
    def word(value: int) -> str:
        if value < 0:
            value = (1 << 256) + value
        return f"{value:064x}"

    broadcast = tmp_path / "broadcast.json"
    broadcast.write_text(
        json.dumps(
            {
                "chain": 1301,
                "receipts": [
                    {
                        "logs": [
                            {
                                "address": "0xPoolManager",
                                "topics": [
                                    V4_SWAP_TOPIC0,
                                    "0xpoolid",
                                    "0xsender",
                                ],
                                "data": "0x"
                                + word(-1_000_000_000_000_000_000)
                                + word(2_000_000_000)
                                + word(79_228_162_514_264_337_593_543_950_336)
                                + word(123)
                                + word(-100)
                                + word(500),
                                "blockNumber": "0x7b",
                                "transactionHash": "0xabc",
                                "logIndex": "0x2",
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = route_collector_smoke_compute(tmp_path, broadcast, quote_token_index=1, quote_decimals=6)
    text = route_collector_smoke_markdown(report)

    assert report["complete"]
    assert report["not_route_away_evidence"]
    assert report["swap_logs"] == 1
    assert report["quote_notional_e6"] == 2_000_000_000
    assert report["vwap_fee_pips"] == 500
    assert report["fee_observation_count"] == 1
    assert "Counts for controlled route-away gate: no" in text


def test_route_share_stability_reports_proxy_share_spread(tmp_path) -> None:
    def proxy(pair: str, share_5_a: float, share_5_b: float) -> dict:
        return {
            "pair": pair,
            "chain": "arbitrum",
            "comparison_windows": [
                {
                    "lookback_blocks": 10,
                    "duration_hours": 1.0,
                    "total_notional_e6": 1_000_000,
                    "high_fee_volume_share": 0.01,
                    "tiers": [
                        {"fee_pips": 100, "volume_share": 0.0},
                        {"fee_pips": 500, "volume_share": share_5_a},
                    ],
                },
                {
                    "lookback_blocks": 20,
                    "duration_hours": 2.0,
                    "total_notional_e6": 2_000_000,
                    "high_fee_volume_share": 0.03,
                    "tiers": [
                        {"fee_pips": 100, "volume_share": 0.0},
                        {"fee_pips": 500, "volume_share": share_5_b},
                    ],
                },
            ],
        }

    first = tmp_path / "route_away_proxy.json"
    second = tmp_path / "route_away_proxy_weth_usdt.json"
    first.write_text(json.dumps(proxy("WETH/USDC", 0.95, 0.90)), encoding="utf-8")
    second.write_text(json.dumps(proxy("WETH/USDT", 0.98, 0.97)), encoding="utf-8")

    report = route_share_stability_compute([first, second])
    text = route_share_stability_markdown(report)

    assert report["complete"]
    assert len(report["rows"]) == 4
    assert abs(report["pair_summaries"][0]["share_5bps_spread_pp"] - 5.0) < 1e-9
    assert abs(report["max_high_fee_spread_pp"] - 2.0) < 1e-9
    assert "not controlled route-away evidence" in text


def test_route_away_placebo_ab_derives_adjacent_equal_windows(tmp_path) -> None:
    def proxy(pair: str, current_treatment: int, full_treatment: int) -> dict:
        return {
            "pair": pair,
            "chain": "arbitrum",
            "comparison_windows": [
                {
                    "lookback_blocks": 50_000,
                    "start_block": 151,
                    "end_block": 200,
                    "duration_hours": 1.0,
                    "total_notional_e6": 1_000,
                    "tiers": [
                        {"fee_pips": 500, "notional_e6": current_treatment, "swaps": 2},
                        {"fee_pips": 3000, "notional_e6": 1_000 - current_treatment, "swaps": 3},
                    ],
                },
                {
                    "lookback_blocks": 100_000,
                    "start_block": 101,
                    "end_block": 200,
                    "duration_hours": 2.0,
                    "total_notional_e6": 3_000,
                    "tiers": [
                        {"fee_pips": 500, "notional_e6": full_treatment, "swaps": 7},
                        {"fee_pips": 3000, "notional_e6": 3_000 - full_treatment, "swaps": 8},
                    ],
                },
            ],
        }

    first = tmp_path / "route_away_proxy.json"
    second = tmp_path / "route_away_proxy_weth_usdt.json"
    first.write_text(json.dumps(proxy("WETH/USDC", current_treatment=200, full_treatment=1_000)), encoding="utf-8")
    second.write_text(json.dumps(proxy("WETH/USDT", current_treatment=500, full_treatment=1_500)), encoding="utf-8")

    report = route_away_placebo_ab_compute([first, second])
    text = route_away_placebo_ab_markdown(report)

    assert report["complete"]
    assert len(report["rows"]) == 2
    assert report["rows"][0]["prior_treatment_notional_e6"] == 800
    assert report["rows"][0]["current_treatment_notional_e6"] == 200
    assert report["rows"][0]["false_routed_away_e6"] == 200
    assert report["rows"][0]["false_route_away_rate"] == 0.5
    assert report["max_false_route_away_rate"] == 0.5
    assert "Route-Away A/A Placebo" in text
    assert "not route-away" in text


def test_route_ab_power_report_maps_placebo_noise_to_detectable_route_loss(tmp_path) -> None:
    route_share = tmp_path / "route_share_stability_report.json"
    break_even = tmp_path / "route_away_break_even.json"
    route_share.write_text(
        json.dumps(
            {
                "complete": True,
                "rows": [{"pair": "WETH/USDC"}, {"pair": "WETH/USDT"}],
                "pair_summaries": [
                    {"pair": "WETH/USDC", "share_5bps_spread_pp": 2.0, "share_high_fee_spread_pp": 1.0},
                    {"pair": "WETH/USDT", "share_5bps_spread_pp": 1.0, "share_high_fee_spread_pp": 1.0},
                ],
            }
        ),
        encoding="utf-8",
    )
    break_even.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "window": "calm",
                        "strategy": "PegGuard selected",
                        "charged_flow_zero_rate": 0.30,
                        "charged_flow_static_parity_rate": 0.20,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = route_ab_power_compute(route_share, break_even)
    text = route_ab_power_markdown(report)
    row = next(
        row
        for row in report["mde_rows"]
        if row["pair"] == "WETH/USDC"
        and row["noise_basis"] == "5 bps share drift"
        and abs(float(row["pre_treatment_share"]) - 0.10) < 1e-9
    )

    assert report["complete"]
    assert abs(float(row["mde_route_away_rate"]) - 0.20) < 1e-9
    assert row["status"] == "usable"
    assert any(
        econ["interpretation"] == "detectable before modeled break-even"
        for econ in report["economic_rows"]
    )
    assert "Controlled Route-Away Power" in text


def test_route_ab_sizing_report_estimates_window_length_from_proxy_notional(tmp_path) -> None:
    power = tmp_path / "route_ab_power_report.json"
    proxy = tmp_path / "route_away_proxy.json"
    cross_proxy = tmp_path / "route_away_proxy_weth_usdt.json"
    power.write_text(
        json.dumps(
            {
                "complete": True,
                "economic_rows": [
                    {
                        "window": "calm",
                        "pair": "WETH/USDC",
                        "noise_basis": "30 bps+ share drift",
                        "pre_treatment_share": 0.25,
                        "mde_route_away_rate": 0.05,
                        "charged_flow_zero_rate": 0.30,
                        "charged_flow_static_parity_rate": 0.20,
                        "interpretation": "detectable before modeled break-even",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDC",
                "chain": "arbitrum",
                "quote_token_index": 1,
                "quote_decimals": 6,
                "tiers": [{"fee_pips": 500, "pool": "0xbaseline"}],
                "comparison_windows": [
                    {"duration_hours": 24.0, "total_notional_e6": 1_000_000_000_000},
                    {"duration_hours": 12.0, "total_notional_e6": 500_000_000_000},
                ],
            }
        ),
        encoding="utf-8",
    )
    cross_proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDT",
                "chain": "arbitrum",
                "comparison_windows": [
                    {"duration_hours": 24.0, "total_notional_e6": 500_000_000_000}
                ],
            }
        ),
        encoding="utf-8",
    )

    report = route_ab_sizing_compute(power, [proxy, cross_proxy])
    text = route_ab_sizing_markdown(report)
    candidate = report["candidate_rows"][0]

    assert report["complete"]
    assert candidate["estimated_treatment_notional_per_day_e6"] == 250_000_000_000
    assert candidate["baseline_pool"] == "0xbaseline"
    assert report["recommendations"][0]["quote_token_index"] == 1
    assert abs(float(candidate["hours_for_target_treatment_notional"]) - 9.6) < 1e-9
    assert report["recommendations"][0]["pair"] == "WETH/USDC"
    assert "Controlled Route-Away A/B Sizing" in text


def test_route_away_window_plan_builds_equal_windows_from_fee_change_block(tmp_path) -> None:
    sizing = tmp_path / "route_ab_sizing_report.json"
    proxy = tmp_path / "route_away_proxy.json"
    sizing.write_text(
        json.dumps(
            {
                "recommendations": [
                    {
                        "pair": "WETH/USDC",
                        "chain": "arbitrum",
                        "baseline_pool": "0xbaseline",
                        "quote_token_index": 1,
                        "quote_decimals": 6,
                        "pre_treatment_share": 0.25,
                        "hours_for_target_treatment_notional": 0.25,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDC",
                "chain": "arbitrum",
                "quote_token_index": 1,
                "quote_decimals": 6,
                "tiers": [{"fee_pips": 500, "pool": "0xbaseline"}],
                "comparison_windows": [{"lookback_blocks": 7200, "duration_hours": 1.0}],
            }
        ),
        encoding="utf-8",
    )

    report = route_window_plan_compute(sizing, [proxy], fee_change_block=100_000, min_window_hours=1.0)
    text = route_window_plan_markdown(report)
    row = report["rows"][0]

    assert report["complete"]
    assert report["not_route_away_evidence"]
    assert report["fee_change_block_known"]
    assert row["window_blocks"] == 7200
    assert row["pre_start_block"] == 92_800
    assert row["pre_end_block"] == 99_999
    assert row["post_start_block"] == 100_000
    assert row["post_end_block"] == 107_199
    assert row["env"]["PRE_START"] == "92800"
    assert "does not count as route-away evidence" in text


def test_route_away_window_plan_keeps_todos_without_fee_change_block(tmp_path) -> None:
    sizing = tmp_path / "route_ab_sizing_report.json"
    proxy = tmp_path / "route_away_proxy.json"
    sizing.write_text(
        json.dumps(
            {
                "recommendations": [
                    {
                        "pair": "WETH/USDT",
                        "chain": "arbitrum",
                        "baseline_pool": "0xbaseline",
                        "quote_token_index": 1,
                        "quote_decimals": 6,
                        "pre_treatment_share": 0.25,
                        "hours_for_target_treatment_notional": 1.5,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDT",
                "chain": "arbitrum",
                "tiers": [{"fee_pips": 500, "pool": "0xbaseline"}],
                "comparison_windows": [{"lookback_blocks": 3600, "duration_hours": 1.0}],
            }
        ),
        encoding="utf-8",
    )

    report = route_window_plan_compute(sizing, [proxy])
    row = report["rows"][0]

    assert report["complete"]
    assert not report["fee_change_block_known"]
    assert row["pre_start_block"] is None
    assert row["env"]["FEE_CHANGE_BLOCK"] == "TODO_FEE_CHANGE_BLOCK"
    assert row["env"]["PRE_START"] == "TODO_PRE_START_BLOCK"


def test_real_position_lifecycle_decodes_modify_position_log() -> None:
    def word(value: int) -> str:
        if value < 0:
            value = (1 << 256) + value
        return f"{value:064x}"

    raw = {
        "blockNumber": "0x7b",
        "transactionHash": "0xabc",
        "logIndex": "0x2",
        "data": "0x"
        + word(-65_600)
        + word(-62_200)
        + word(4_572_842_275)
        + word(2_200_741),
    }

    decoded = real_position_decode_modify_position(raw)
    text = real_position_lifecycle_markdown(
        {
            "status": "lifecycle scanned",
            "position_id": "2200741",
            "latest_seen": 123,
            "mint_block": 100,
            "events": [
                {
                    "block_number": decoded["block_number"],
                    "log_index": decoded["log_index"],
                    "direction": "deposit",
                    "liquidity_delta": decoded["liquidity_delta"],
                    "amount0_raw": 1,
                    "amount1_raw": 2,
                    "tx_hash": decoded["tx_hash"],
                }
            ],
            "provisional_hodl_value_e6": 1_000_000,
            "current_value_with_fees_e6": 1_100_000,
            "provisional_net_vs_hodl_e6": 100_000,
        }
    )

    assert decoded["tick_lower"] == -65_600
    assert decoded["tick_upper"] == -62_200
    assert decoded["liquidity_delta"] == 4_572_842_275
    assert decoded["salt"] == "0x" + f"{2_200_741:064x}"
    assert "Real Position Lifecycle Scan" in text
    assert "receipt transfers" in text


def test_route_away_readiness_reports_missing_inputs(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    route_sizing = tmp_path / "route_ab_sizing_report.json"
    route_sizing.write_text(
        json.dumps(
            {
                "recommendations": [
                    {
                        "pair": "WETH/USDT",
                        "chain": "arbitrum",
                        "baseline_pool": "0xbaseline",
                        "quote_token_index": 1,
                        "quote_decimals": 6,
                        "pre_treatment_share": 0.25,
                        "mde_route_away_rate": 0.05,
                        "hours_for_target_treatment_notional": 1.5,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = route_readiness_compute(C.repo_root(), env={}, route_ab_path=route_ab, route_sizing_path=route_sizing)
    text = route_readiness_markdown(report)

    assert report["status"] == "missing inputs"
    assert not report["ready_to_collect"]
    assert "treatment_pool_id" in report["missing_inputs"]
    assert report["collection_plan"]["status"].startswith("not ready")
    assert report["collection_plan"]["pre_window"] == "missing"
    assert "Controlled Route-Away Readiness" in text
    assert "does not count as route-away evidence" in text
    assert "## Collection Plan" in text
    assert "## A/B Sizing Recommendations" in text
    assert "## Collection Input Packets" in text
    assert report["sizing_recommendations"][0]["suggested_env"]["ROUTE_AWAY_PAIR"] == "WETH/USDT"
    assert report["collection_packets"][0]["env"]["TREATMENT_POOL"] == "TODO_POOL_MANAGER_OR_TREATMENT_POOL"
    assert "PEGGUARD_POOL_ID" in report["collection_packets"][0]["missing_fields"]
    assert "TODO_POST_VWAP_FEE_PIPS" in text
    assert "Command template omitted because this packet still contains `TODO_*` placeholders." in text
    assert "No collector command is printed because readiness validations have not passed." in text
    assert "python3 -m shadow.route_away_collect" not in text
    assert "Value source" in text


def test_route_away_readiness_reports_testnet_deployment_hints(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    broadcast = tmp_path / "broadcast" / "TestnetExercise.s.sol" / "1301" / "run-latest.json"
    broadcast.parent.mkdir(parents=True)
    broadcast.write_text(
        json.dumps(
            {
                "chain": 1301,
                "transactions": [
                    {
                        "contractName": "PegGuardHook",
                        "contractAddress": "0xhook",
                        "arguments": ["0xmanager", "0xpyth", "0xowner"],
                    }
                ],
                "receipts": [
                    {
                        "logs": [
                            {
                                "topics": [
                                    "0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f",
                                    "0xpoolid",
                                ]
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = route_readiness_compute(tmp_path, env={}, route_ab_path=route_ab)
    text = route_readiness_markdown(report)

    assert not report["ready_to_collect"]
    assert report["deployment_hints"][0]["hook"] == "0xhook"
    assert report["deployment_hints"][0]["pool_ids"] == ["0xpoolid"]
    assert report["deployment_hints"][0]["suggested_env"]["POOL_MANAGER"] == "0xmanager"
    assert report["deployment_hints"][0]["suggested_env"]["PEGGUARD_POOL_ID"] == "0xpoolid"
    assert not report["deployment_hints"][0]["counts_for_gate"]
    assert "Deployment Hints" in text
    assert "Suggested non-gating env" in text
    assert "testnet hook smoke only" in text


def test_route_away_readiness_accepts_collection_inputs(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_WSS": "wss://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)
    text = route_readiness_markdown(report)

    assert report["status"] == "ready to collect"
    assert report["ready_to_collect"]
    assert not report["missing_inputs"]
    assert report["collection_plan"]["status"].startswith("ready to collect")
    assert report["collection_plan"]["pre_window"] == "100-200 (101 blocks)"
    assert report["collection_plan"]["fee_delta"] == "200 pips (2.00 bps)"
    assert all(row["passed"] for row in report["validations"])
    assert "shadow.route_away_collect" in report["command"]
    assert "Required inputs and setup validations are satisfied. Run:" in text
    assert "python3 -m shadow.route_away_collect" in text


def test_route_away_readiness_rejects_same_pool_identity(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_WSS": "wss://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xpoolmanager",
        "POOL_MANAGER": "0xPoolManager",
        "PEGGUARD_POOL_ID": "0x01",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert not report["ready_to_collect"]
    assert "baseline/treatment pool identities distinct" in report["failed_validations"]
    identity = next(row for row in report["validations"] if row["name"] == "baseline/treatment pool identities distinct")
    assert "requires distinct baseline and treatment pools" in identity["details"]


def test_route_away_readiness_rejects_invalid_v4_pool_id(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_WSS": "wss://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0xnot_hex",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert not report["ready_to_collect"]
    assert "v4 pool ids valid" in report["failed_validations"]
    pool_ids = next(row for row in report["validations"] if row["name"] == "v4 pool ids valid")
    assert "treatment: v4 pool id must be hex bytes32" in pool_ids["details"]


def test_route_away_readiness_allows_same_poolmanager_with_distinct_v4_pool_ids(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_WSS": "wss://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xPoolManager",
        "BASELINE_KIND": "v4",
        "BASELINE_POOL_ID": "0x01",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x02",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert report["ready_to_collect"]
    identity = next(row for row in report["validations"] if row["name"] == "baseline/treatment pool identities distinct")
    assert identity["passed"]
    assert identity["details"] == "same PoolManager with distinct v4 pool ids"


def test_route_away_readiness_allows_v4_post_fee_derivation(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_HTTP": "https://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)
    text = route_readiness_markdown(report)

    assert report["ready_to_collect"]
    assert "post_treatment_fee_pips" not in report["missing_inputs"]
    assert report["collection_plan"]["fee_delta"] == "derived from v4 Swap logs during collection"
    assert "--post-treatment-fee-pips" not in report["command"]
    assert "derive from v4 logs" in text


def test_route_away_readiness_derives_windows_from_fee_change_block(tmp_path) -> None:
    (tmp_path / "docs").mkdir()
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    route_sizing = tmp_path / "docs" / "route_ab_sizing_report.json"
    route_sizing.write_text(
        json.dumps(
            {
                "recommendations": [
                    {
                        "pair": "WETH/USDC",
                        "chain": "base",
                        "baseline_pool": "0xbaseline",
                        "quote_token_index": 1,
                        "quote_decimals": 6,
                        "pre_treatment_share": 0.25,
                        "hours_for_target_treatment_notional": 1.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "route_away_proxy.json").write_text(
        json.dumps(
            {
                "pair": "WETH/USDC",
                "chain": "base",
                "quote_token_index": 1,
                "quote_decimals": 6,
                "tiers": [{"fee_pips": 500, "pool": "0xbaseline"}],
                "comparison_windows": [{"lookback_blocks": 7200, "duration_hours": 1.0}],
            }
        ),
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_HTTP": "https://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "FEE_CHANGE_BLOCK": "100000",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(tmp_path, env=env, route_ab_path=route_ab, route_sizing_path=route_sizing)

    assert report["ready_to_collect"]
    assert report["collection_plan"]["pre_window"] == "92800-99999 (7200 blocks)"
    assert report["collection_plan"]["post_window"] == "100000-107199 (7200 blocks)"
    assert "--pre-start-block 92800" in report["command"]
    assert "pre_start_block" not in report["missing_inputs"]


def test_route_away_rpc_preflight_requires_explicit_network_context() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "POOL_MANAGER": "0xpoolmanager",
            "PEGGUARD_POOL_ID": "0x01",
        },
    )
    text = route_rpc_preflight_markdown(report)

    assert report["status"] == "missing explicit context"
    assert not report["executed"]
    assert "rpc_url" in report["implicit_inputs"]
    assert "chain" in report["implicit_inputs"]
    assert "Counts for controlled route-away gate: no" in text


def test_route_away_rpc_preflight_ready_with_explicit_context() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "base",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xbaseline",
            "TREATMENT_POOL": "0xtreatment",
            "PEGGUARD_POOL_ID": "0x01",
        },
    )

    assert report["status"] == "ready to execute"
    assert not report["missing_inputs"]
    assert not report["implicit_inputs"]
    identity = next(check for check in report["checks"] if check["name"] == "baseline/treatment pool identities distinct")
    assert identity["passed"]


def test_route_away_rpc_preflight_requires_v4_pool_id() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "base",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xbaseline",
            "TREATMENT_POOL": "0xtreatment",
        },
    )

    assert report["status"] == "failed setup checks"
    v4_ids = next(check for check in report["checks"] if check["name"] == "v4 pool ids present")
    assert not v4_ids["passed"]
    assert "treatment_pool_id=missing" in v4_ids["observed"]


def test_route_away_rpc_preflight_rejects_chain_id_mismatch() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "arbitrum",
            "CHAIN_ID": "1301",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xbaseline",
            "TREATMENT_POOL": "0xtreatment",
            "PEGGUARD_POOL_ID": "0x01",
        },
    )

    assert report["status"] == "failed setup checks"
    chain_id = next(check for check in report["checks"] if check["name"] == "chain id matches selected chain")
    assert not chain_id["passed"]
    assert "chain_id=1301, selected chain=arbitrum" in chain_id["observed"]
    assert chain_id["expected"] == 42161


def test_route_away_rpc_preflight_rejects_invalid_v4_pool_id() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "base",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xbaseline",
            "TREATMENT_POOL": "0xtreatment",
            "PEGGUARD_POOL_ID": "0xnot_hex",
        },
    )

    assert report["status"] == "failed setup checks"
    pool_ids = next(check for check in report["checks"] if check["name"] == "v4 pool ids valid")
    assert not pool_ids["passed"]
    assert "treatment: v4 pool id must be hex bytes32" in pool_ids["observed"]


def test_route_away_rpc_preflight_rejects_same_pool_identity() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "base",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xpoolmanager",
            "TREATMENT_POOL": "0xPoolManager",
            "PEGGUARD_POOL_ID": "0x01",
        },
    )
    text = route_rpc_preflight_markdown(report)

    assert report["status"] == "failed setup checks"
    identity = next(check for check in report["checks"] if check["name"] == "baseline/treatment pool identities distinct")
    assert not identity["passed"]
    assert "requires distinct baseline and treatment pools" in identity["observed"]
    assert "failed setup checks" in text


def test_route_away_rpc_preflight_allows_same_poolmanager_with_distinct_v4_ids() -> None:
    report = route_rpc_preflight_compute_static(
        C.repo_root(),
        env={
            "CHAIN_RPC_HTTP": "https://example.invalid",
            "ROUTE_AWAY_CHAIN": "base",
            "ROUTE_AWAY_PAIR": "WETH/USDC",
            "BASELINE_POOL": "0xPoolManager",
            "BASELINE_KIND": "v4",
            "BASELINE_POOL_ID": "0x01",
            "TREATMENT_POOL": "0xpoolmanager",
            "TREATMENT_KIND": "v4",
            "PEGGUARD_POOL_ID": "0x02",
        },
    )

    assert report["status"] == "ready to execute"
    identity = next(check for check in report["checks"] if check["name"] == "baseline/treatment pool identities distinct")
    assert identity["passed"]
    assert identity["observed"] == "same PoolManager with distinct v4 pool ids"


def test_route_away_readiness_rejects_invalid_existing_route_input(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    route_input = tmp_path / "route_away_ab_input.json"
    route_input.write_text(
        json.dumps(
            {
                "pair": "WETH/USDC",
                "baseline": "baseline",
                "treatment": "pegguard",
                "pre": {"baseline_notional_e6": 1, "treatment_notional_e6": 1, "treatment_fee_pips": 500},
                "post": {"baseline_notional_e6": 1, "treatment_notional_e6": 1, "treatment_fee_pips": 700},
                "collection": {
                    "pre_baseline": {"start_block": 100, "end_block": 200, "swaps": 1, "quote_notional_e6": 1},
                    "pre_treatment": {"start_block": 100, "end_block": 200, "swaps": 1, "quote_notional_e6": 1},
                    "post_baseline": {"start_block": 201, "end_block": 350, "swaps": 1, "quote_notional_e6": 1},
                    "post_treatment": {"start_block": 201, "end_block": 350, "swaps": 0, "quote_notional_e6": 1},
                },
            }
        ),
        encoding="utf-8",
    )

    report = route_readiness_compute(C.repo_root(), env={}, route_input_path=route_input, route_ab_path=route_ab)

    assert not report["controlled_result_complete"]
    assert not report["route_input_ready"]


def test_route_away_readiness_rejects_mismatched_window_lengths(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_WSS": "wss://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "450",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert report["status"] == "missing inputs"
    assert not report["ready_to_collect"]
    assert "windows equal length" in report["failed_validations"]


def test_route_away_readiness_accepts_http_rpc_for_historical_collection(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "CHAIN_RPC_HTTP": "https://example.invalid",
        "ROUTE_AWAY_CHAIN": "base",
        "ROUTE_AWAY_PAIR": "WETH/USDC",
        "BASELINE_POOL": "0xbaseline",
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
        "QUOTE_TOKEN_INDEX": "1",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert report["ready_to_collect"]
    assert "--rpc-http" in report["command"]
    assert "--rpc-wss" not in report["command"]


def test_route_away_readiness_loads_project_dotenv_without_unrelated_keys(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "PRIVATE_KEY=not-for-reporting",
                "CHAIN_RPC_WSS=wss://example.invalid",
                "ROUTE_AWAY_CHAIN=base",
                "ROUTE_AWAY_PAIR=WETH/USDC",
                "BASELINE_POOL=0xbaseline",
                "POOL_MANAGER=0xpoolmanager",
                "PEGGUARD_POOL_ID=0x01",
                "PRE_START=100",
                "PRE_END=200",
                "POST_START=300",
                "POST_END=400",
                "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS=700",
                "QUOTE_TOKEN_INDEX=1",
            ]
        ),
        encoding="utf-8",
    )

    report = route_readiness_compute(tmp_path, route_ab_path=route_ab)

    assert report["dotenv_loaded"]
    assert report["ready_to_collect"]
    assert not report["missing_inputs"]
    assert "PRIVATE_KEY" not in json.dumps(report)
    assert "<set>" in json.dumps(report)


def test_route_away_readiness_rejects_mixed_default_network_context(tmp_path) -> None:
    route_ab = tmp_path / "route_away_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )
    env = {
        "POOL_MANAGER": "0xpoolmanager",
        "PEGGUARD_POOL_ID": "0x01",
        "CHAIN_ID": "1301",
        "PRE_START": "100",
        "PRE_END": "200",
        "POST_START": "300",
        "POST_END": "400",
        "VWAP_EFFECTIVE_PEGGUARD_FEE_PIPS": "700",
    }

    report = route_readiness_compute(C.repo_root(), env=env, route_ab_path=route_ab)

    assert not report["ready_to_collect"]
    assert "treatment_pool" in report["missing_inputs"]
    assert "treatment_pool_id" in report["missing_inputs"]
    assert "controlled network context explicit" in report["failed_validations"]
    assert "chain id matches selected chain" in report["failed_validations"]
    treatment = next(row for row in report["required_inputs"] if row["key"] == "treatment_pool")
    treatment_pool_id = next(row for row in report["required_inputs"] if row["key"] == "treatment_pool_id")
    assert not treatment["resolved"]
    assert not treatment_pool_id["resolved"]
    assert treatment["display_value"].startswith("ignored ")
    assert treatment["source"] == "unsafe mixed/default context"
    assert any("implicit route context" in warning for warning in report["collection_plan"]["warnings"])


def test_evidence_ledger_marks_missing_controlled_route_away() -> None:
    text = evidence_markdown(
        live_status={
            "complete": False,
            "database": "shadow/live.sqlite3",
            "swaps": 10,
            "observed_span_hours": 1.5,
            "truth_coverage": 0.5,
            "gates": [{"name": "observed span", "observed": "1.50h", "required": ">= 24.00h", "passed": False}],
        },
        route_proxy={
            "total_notional_e6": 1_000_000_000,
            "high_fee_volume_share": 0.02,
            "tiers": [{"swaps": 100}],
        },
        route_share_stability_report=_complete_route_share_stability_report(),
        route_away_placebo_ab_report=_complete_route_away_placebo_ab_report(),
        route_ab_power_report=_complete_route_ab_power_report(),
        route_ab_sizing_report=_complete_route_ab_sizing_report(),
        route_baseline_probe_report=_complete_route_baseline_probe_report(),
        route_ab={
            "pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0},
            "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0},
            "route_away_rate": 0,
        },
        cross_pair_route_proxy={"pair": "WETH/USDT", "total_notional_e6": 1_000_000_000, "high_fee_volume_share": 0.01, "tiers": [{"swaps": 10}]},
        depth_proxy={"pair": "WETH/USDC", "band_totals": {"50": 1}, "tiers": [{"fee_pips": 500}]},
        cross_pair_depth_proxy={"pair": "WETH/USDT", "band_totals": {"50": 1}, "tiers": [{"fee_pips": 500}]},
        oracle_health={"swaps": 10, "staleness_p90_ms": 1000, "decisions": [{"label": "fresh", "fallback_notional_share": 0.1}]},
        oracle_lag={"rows": [{"label": "fresh"}, {"label": "lag2"}, {"label": "lag5", "delta_net_vs_fresh_e6": -1}]},
        risk_report={"windows": [{"window": "live shadow", "max_drawdown_e6": -100}, {"window": "calm"}, {"window": "vol"}]},
        drawdown_stop={"rows": [{"window": "live shadow", "threshold_e6": 50_000_000, "triggered": True, "delta_vs_full_e6": 1}]},
        fallback_attribution={"rows": 10, "labels": [{"label": "fresh", "missed_extra_e6": 123}]},
        inventory_report={"windows": [{"window": "calm", "inventory_il_e6": -10}, {"window": "vol", "inventory_il_e6": -100}]},
        hedge_report={"rows": [{"window": "calm"}, {"window": "vol", "hedge_improvement_e6": 10}]},
        hedge_execution_report=_complete_hedge_execution_report(),
        liquidity_share_report={"rows": [{"window": "live shadow", "capital_e6": 10_000_000_000, "net_apr": 0.1}]},
        route_break_even={"rows": [{"window": "calm"}, {"window": "vol", "charged_flow_zero_rate": 0.1}, {"window": "live shadow"}]},
        adverse_route_away={"rows": [{"window": "calm", "adverse_gap_bps": -0.1}, {"window": "vol", "adverse_gap_bps": -0.2}]},
        bootstrap_report={"windows": [{"window": "calm"}, {"window": "vol", "positive_net_probability": 0.1}]},
        size_bucket_report={"rows": [{"window": "calm", "bucket": ">=$50k", "net_e6": 1}, {"window": "vol", "bucket": ">=$50k", "net_e6": -1}]},
        staleness_bucket_report={"rows": 10, "buckets": [{"bucket": "<=1s"}, {"bucket": "1-2s"}, {"bucket": "2-5s"}, {"bucket": ">5s/missing", "truth_net_e6": -1}]},
        market_regime_report=_complete_market_regime_report(),
        base_fee_report={"rows": [{"window": "calm"}, {"window": "vol", "required_base_pips_zero": 600}, {"window": "live shadow"}]},
        target_fee_report={"route_total_notional_e6": 1, "rows": [{"window": "calm"}, {"window": "vol", "target": "1 bps net", "viability": "thin"}, {"window": "live shadow"}]},
        capital_path_report={"rows": [{"path": "all volatile 7d", "max_drawdown": -0.01}]},
        policy_monte_carlo_report=_complete_policy_monte_carlo_report(),
        risk_adjusted_return_report=_complete_risk_adjusted_return_report(),
        chain_cost_report=_complete_chain_cost_report(),
        live_gas_snapshot_report=_complete_live_gas_snapshot_report(),
        control_plane_cost_report=_complete_control_plane_cost_report(),
        pnl_attribution_report=_complete_pnl_attribution_report(),
        capital_survival_report=_complete_capital_survival_report(),
        operator_cost_report=_complete_operator_cost_report(),
        alpha_sweep={"rows": [{"alpha": "1/2", "feasible": True}]},
        target_return_report={"rows": [{"window": "live shadow", "policy": "small active", "target_apr": 0.2, "status": "needs more turnover"}]},
        order_split_report={"rows": [{"window": "calm", "child_count": 2, "leakage_rate": 0.001}, {"window": "vol", "child_count": 100, "leakage_rate": 0.002}]},
        tvl_dilution_report={"equilibrium_rows": [{"window": "calm", "route_away": 0.25, "target_apr": 0.2, "max_active_capital_e6": 1}, {"window": "vol", "route_away": 0.25, "target_apr": 0.2, "max_active_capital_e6": None}, {"window": "live shadow", "route_away": 0.25, "target_apr": 0.2, "max_active_capital_e6": 1}]},
        route_cost_proxy={"rows": [{"pair": "WETH/USDC", "trade_size_e6": 50_000_000_000, "fee_pips": 500, "pegguard_headroom_bps": 1.2}]},
        sequential_split_report={"rows": [{"window": "calm", "child_count": 2, "child_spacing_sec": 0, "leakage_rate": -0.001}, {"window": "vol", "child_count": 10, "child_spacing_sec": 30, "leakage_rate": 0.002}]},
        quote_route_readiness={"status": "missing inputs", "missing_inputs": ["rpc_http"], "failed_validations": ["rpc url is http"], "quote_result_complete": False},
        quote_headroom_report={"rows": [{"premium_headroom_bps": 1.2}, {"premium_headroom_bps": -0.4}]},
        cross_pair_quote_headroom_report={"quote_source": "docs/quote_route_quotes_weth_usdt.json", "rows": [{"premium_headroom_bps": 5.0}]},
        quote_headroom_stability_report=_complete_quote_headroom_stability_report(),
        quote_headroom_drift_report=_complete_quote_headroom_drift_report(),
        quote_premium_stress_report={"rows": [{"window": "calm", "over_headroom_rows": 1, "excess_e6": 100, "excess_share_of_extra": 0.1}]},
        quote_event_headroom_report=_complete_quote_event_headroom_report(),
        quote_provenance_report=_complete_quote_provenance_report(),
        quote_elasticity_report=_complete_quote_elasticity_report(),
        insurance_reserve_report=_complete_reserve_report(),
        premium_allocation_report=_complete_premium_allocation_report(),
        premium_utilization_report=_complete_premium_utilization_report(),
        reserve_delay_report=_complete_reserve_delay_report(),
        reserve_lifecycle_report=_complete_reserve_lifecycle_report(),
        reserve_tail_report=_complete_reserve_tail_report(),
        route_demand_report=_complete_route_demand_report(),
        markout_sensitivity_report=_complete_markout_sensitivity_report(),
        pilot_deployability_report=_complete_pilot_deployability_report(),
        range_width_deployability_report=_complete_range_width_deployability_report(),
        position_shadow_report=_complete_position_shadow_report(),
        small_capital_decision_report=_complete_small_capital_decision_report(),
        real_position_report=_complete_real_position_report(),
        real_position_portfolio_report=_complete_real_position_portfolio_report(),
        headline_uncertainty_report=_complete_headline_uncertainty_report(),
        lp_flow_response_report=_complete_lp_flow_response_report(),
        live_convergence_report=_complete_live_convergence_report(),
        live_maturity_report=_complete_live_maturity_report(),
        live_power_report=_complete_live_power_report(),
        cross_pair_live_report=_complete_cross_pair_live_report(),
        live_soak_report=_complete_live_soak_report(),
        cross_pair_live_economics_report=_complete_cross_pair_live_economics_report(),
        live_fee_tier_report=_complete_live_fee_tier_report(),
        guard_depeg_report=_complete_guard_depeg_report(),
        stable_opportunity_report=_complete_stable_opportunity_report(),
        charge_attribution_report=_complete_charge_attribution_report(),
        signal_quality_stress_report=_complete_signal_quality_stress_report(),
        signal_margin_report=_complete_signal_margin_report(),
    )

    assert "Economic Evidence Ledger" in text
    assert "missing live data" in text
    assert "invalid input" in text
    assert "Cross-pair route-away proxy" in text
    assert "Route-share placebo stability" in text
    assert "Controlled route-away power check" in text
    assert "Controlled route-away sizing plan" in text
    assert "Route-away baseline-flow probe" in text
    assert "Cross-pair live shadow" in text
    assert "Live soak tracker" in text
    assert "Cross-pair live economics" in text
    assert "Live fee-tier shadow" in text
    assert "| Live fee-tier shadow | `docs/live_fee_tier_report.md` | measurable |" in text
    assert "Route-away A/A placebo" in text
    assert "GUARD breaker economics" in text
    assert "GUARD stable opportunity" in text
    assert "Oracle-health economics" in text
    assert "Oracle-lag stress" in text
    assert "Tail-risk concentration" in text
    assert "Drawdown stop-loss" in text
    assert "Fallback attribution" in text
    assert "LP inventory accounting" in text
    assert "Hedge stress" in text
    assert "Hedge execution-cost stress" in text
    assert "Liquidity-share sizing" in text
    assert "Position-level LP shadow" in text
    assert "Real position replay" in text
    assert "Multi-position LP replay" in text
    assert "Route-away break-even" in text
    assert "Adverse route-away stress" in text
    assert "Bootstrap robustness" in text
    assert "Headline uncertainty bands" in text
    assert "Trade-size buckets" in text
    assert "Oracle staleness buckets" in text
    assert "Market-regime segments" in text
    assert "Signal-quality stress" in text
    assert "Signal margin" in text
    assert "Base-fee adequacy" in text
    assert "Truth markout sensitivity" in text
    assert "Target-fee viability" in text
    assert "Capital-path stress" in text
    assert "Policy Monte Carlo" in text
    assert "Risk-adjusted return" in text
    assert "Chain cost matrix" in text
    assert "Live gas snapshot" in text
    assert "Control-plane callback cost" in text
    assert "PnL attribution" in text
    assert "Capital survival runway" in text
    assert "Operator fixed-cost drag" in text
    assert "Pilot deployability stress" in text
    assert "Range-width deployability" in text
    assert "Small-capital decision matrix" in text
    assert "Alpha sensitivity" in text
    assert "Target-return thresholds" in text
    assert "Order-splitting sensitivity" in text
    assert "Sequential split timing" in text
    assert "TVL dilution equilibrium" in text
    assert "LP flow response" in text
    assert "Live convergence" in text
    assert "Live maturity" in text
    assert "Live sample power" in text
    assert "Depth-adjusted route cost" in text
    assert "Quote-route readiness" in text
    assert "Quote premium headroom" in text
    assert "Cross-pair quote headroom" in text
    assert "Quote-headroom repeatability" in text
    assert "Quote-headroom drift" in text
    assert "Quote premium stress" in text
    assert "Quote event headroom" in text
    assert "Quote provenance audit" in text
    assert "Quote-headroom elasticity" in text
    assert "Insurance reserve solvency" in text
    assert "Premium allocation frontier" in text
    assert "Premium utilization" in text
    assert "Charge attribution" in text
    assert "Reserve claim-delay stress" in text
    assert "Reserve lifecycle churn" in text
    assert "Reserve tail sizing" in text
    assert "Risk-adjusted return" in text
    assert "Route-away demand curve" in text
    assert "observed span" in text


def test_economic_gate_requires_live_and_controlled_route_away() -> None:
    data = suite(C.repo_root())
    report = gate_evaluate(
        data,
        {"complete": False, "swaps": 10, "observed_span_hours": 1.0, "truth_coverage": 0.5},
        {"tiers": [{"swaps": 5}]},
        {
            "pre": {"baseline_notional_e6": 1, "treatment_notional_e6": 1},
            "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 1},
        },
        {"pair": "WETH/USDT", "tiers": []},
        {"pair": "WETH/USDC", "band_totals": {"50": 1_000_000}, "tiers": [{"fee_pips": 500}]},
        {"pair": "WETH/USDT", "band_totals": {"50": 1_000_000}, "tiers": [{"fee_pips": 500}]},
        {"swaps": 10, "pyth_health_rows": 10, "staleness_p90_ms": 1000},
        {"rows": [{"label": "fresh"}, {"label": "lag2"}, {"label": "lag5"}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}]},
        {"rows": [{"window": "calm", "threshold_e6": 10_000_000}, {"window": "vol", "threshold_e6": 50_000_000}, {"window": "live shadow", "threshold_e6": 100_000_000}]},
        {"rows": 10, "labels": [{"label": "fresh", "missed_extra_e6": 1}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}]},
        {"rows": [{"window": "calm"}, {"window": "vol", "hedge_improvement_e6": 1}]},
        _complete_hedge_execution_report(),
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"window": "calm", "route_away": 0.10}, {"window": "calm", "route_away": 0.25}, {"window": "calm", "route_away": 0.50}, {"window": "calm", "route_away": 0.75}, {"window": "vol", "route_away": 0.10}, {"window": "vol", "route_away": 0.25}, {"window": "vol", "route_away": 0.50}, {"window": "vol", "route_away": 0.75, "adverse_gap_bps": -0.2}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}], "iterations": 10},
        {"rows": [{"window": "calm", "bucket": "<$1k"}, {"window": "vol", "bucket": "<$1k"}]},
        {"rows": 10, "buckets": [{"bucket": "<=1s"}, {"bucket": "1-2s"}, {"bucket": "2-5s"}, {"bucket": ">5s/missing"}]},
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"route_total_notional_e6": 1, "rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"path": "calm 30d"}, {"path": "weekly vol shock 30d"}, {"path": "all volatile 7d"}]},
        _complete_policy_monte_carlo_report(),
        _complete_risk_adjusted_return_report(),
        _complete_chain_cost_report(),
        _complete_live_gas_snapshot_report(),
        _complete_control_plane_cost_report(),
        _complete_pnl_attribution_report(),
        _complete_capital_survival_report(),
        _complete_operator_cost_report(),
        {"rows": [{"alpha": "1/2", "feasible": True}]},
        {"rows": [{"window": "calm", "target_apr": 0.1}, {"window": "vol", "target_apr": 0.2}, {"window": "live shadow", "target_apr": 0.3}]},
        {},
        {"rows": [{"window": "calm", "child_count": 2}, {"window": "calm", "child_count": 10}, {"window": "calm", "child_count": 100}, {"window": "vol", "child_count": 2}, {"window": "vol", "child_count": 10}, {"window": "vol", "child_count": 100}]},
        {"equilibrium_rows": [{"window": "calm", "route_away": 0.0, "target_apr": 0.1}, {"window": "calm", "route_away": 0.25, "target_apr": 0.2}, {"window": "calm", "route_away": 0.5, "target_apr": 0.3}, {"window": "vol", "route_away": 0.0, "target_apr": 0.1}, {"window": "vol", "route_away": 0.25, "target_apr": 0.2}, {"window": "vol", "route_away": 0.5, "target_apr": 0.3}]},
        {"rows": [{"pair": "WETH/USDC", "trade_size_e6": 1_000_000_000, "fee_pips": 100}, {"pair": "WETH/USDC", "trade_size_e6": 10_000_000_000, "fee_pips": 500}, {"pair": "WETH/USDC", "trade_size_e6": 50_000_000_000, "fee_pips": 3000}, {"pair": "WETH/USDT", "trade_size_e6": 1_000_000_000, "fee_pips": 100}, {"pair": "WETH/USDT", "trade_size_e6": 10_000_000_000, "fee_pips": 500}, {"pair": "WETH/USDT", "trade_size_e6": 50_000_000_000, "fee_pips": 3000}]},
        {"rows": [{"window": "calm", "child_count": 2, "child_spacing_sec": 0}, {"window": "calm", "child_count": 10, "child_spacing_sec": 30}, {"window": "vol", "child_count": 2, "child_spacing_sec": 0}, {"window": "vol", "child_count": 10, "child_spacing_sec": 30}]},
        {"ready_to_collect": True, "quote_result_complete": False, "status": "ready to collect"},
        {"rows": [{"premium_headroom_bps": 1.2}, {"premium_headroom_bps": -0.4}]},
        {"quote_source": "docs/quote_route_quotes_weth_usdt.json", "rows": [{"premium_headroom_bps": 2.0}]},
        _complete_quote_headroom_stability_report(),
        _complete_quote_headroom_drift_report(),
        {"buckets": [{"label": "a"}], "rows": [{"window": "calm"}, {"window": "vol", "over_headroom_rows": 1, "excess_e6": 1, "excess_share_of_extra": 0.1}]},
        _complete_quote_event_headroom_report(),
        _complete_quote_provenance_report(),
        _complete_quote_elasticity_report(),
        _complete_reserve_report(),
        _complete_premium_allocation_report(),
        _complete_reserve_delay_report(),
        _complete_reserve_lifecycle_report(),
        _complete_reserve_tail_report(),
        _complete_route_demand_report(),
        markout_sensitivity_report=_complete_markout_sensitivity_report(),
        pilot_deployability_report=_complete_pilot_deployability_report(),
        range_width_deployability_report=_complete_range_width_deployability_report(),
        position_shadow_report=_complete_position_shadow_report(),
        small_capital_decision_report=_complete_small_capital_decision_report(),
        real_position_report=_complete_real_position_report(),
        real_position_portfolio_report=_complete_real_position_portfolio_report(),
        headline_uncertainty_report=_complete_headline_uncertainty_report(),
        lp_flow_response_report=_complete_lp_flow_response_report(),
        live_convergence_report=_complete_live_convergence_report(),
        live_maturity_report=_complete_live_maturity_report(),
        live_power_report=_complete_live_power_report(),
        premium_utilization_report=_complete_premium_utilization_report(),
        charge_attribution_report=_complete_charge_attribution_report(),
        route_share_stability_report=_complete_route_share_stability_report(),
        route_away_placebo_ab_report=_complete_route_away_placebo_ab_report(),
        route_ab_power_report=_complete_route_ab_power_report(),
        route_ab_sizing_report=_complete_route_ab_sizing_report(),
        guard_depeg_report=_complete_guard_depeg_report(),
        stable_opportunity_report=_complete_stable_opportunity_report(),
        market_regime_report=_complete_market_regime_report(),
        signal_quality_stress_report=_complete_signal_quality_stress_report(),
        signal_margin_report=_complete_signal_margin_report(),
    )

    text = gate_markdown(report)

    assert not report.complete
    assert "24h live shadow" in text
    assert "GUARD breaker economics" in text
    assert "GUARD stable opportunity" in text
    assert "controlled route-away" in text
    assert "live evidence source consistency" in text
    assert "invalid input" in text
    assert "cross-pair route-away proxy" in text
    assert "route-share placebo stability" in text
    assert "route-away A/A placebo" in text
    assert "controlled route-away power check" in text
    assert "controlled route-away sizing plan" in text
    assert "fee-tier depth proxy" in text
    assert "oracle-health economics" in text
    assert "oracle-lag stress" in text
    assert "tail-risk concentration" in text
    assert "drawdown stop-loss" in text
    assert "fallback attribution" in text
    assert "LP inventory accounting" in text
    assert "hedge stress" in text
    assert "hedge execution-cost stress" in text
    assert "liquidity-share sizing" in text
    assert "position-level LP shadow" in text
    assert "real-position replay" in text
    assert "multi-position LP replay" in text
    assert "route-away break-even" in text
    assert "adverse route-away stress" in text
    assert "controlled route-away readiness" in text
    assert "bootstrap robustness" in text
    assert "headline uncertainty bands" in text
    assert "trade-size buckets" in text
    assert "oracle staleness buckets" in text
    assert "market-regime segmentation" in text
    assert "signal-quality stress" in text
    assert "signal margin" in text
    assert "base-fee adequacy" in text
    assert "truth markout sensitivity" in text
    assert "target-fee viability" in text
    assert "capital-path stress" in text
    assert "policy Monte Carlo" in text
    assert "risk-adjusted return" in text
    assert "chain cost matrix" in text
    assert "live gas snapshot" in text
    assert "control-plane callback cost" in text
    assert "PnL attribution" in text
    assert "capital survival runway" in text
    assert "operator fixed-cost drag" in text
    assert "pilot deployability stress" in text
    assert "range-width deployability" in text
    assert "small-capital decision matrix" in text
    assert "alpha sensitivity" in text
    assert "target-return thresholds" in text
    assert "order-splitting sensitivity" in text
    assert "sequential split timing" in text
    assert "TVL dilution equilibrium" in text
    assert "LP flow response" in text
    assert "live convergence" in text
    assert "live maturity" in text
    assert "live sample power" in text
    assert "depth-adjusted route cost" in text
    assert "quote-route readiness" in text
    assert "quote premium headroom" in text
    assert "cross-pair quote headroom" in text
    assert "quote-headroom repeatability" in text
    assert "quote-headroom drift" in text
    assert "quote premium stress" in text
    assert "quote event headroom" in text
    assert "quote provenance audit" in text
    assert "quote-headroom elasticity" in text
    assert "insurance reserve solvency" in text
    assert "premium allocation frontier" in text
    assert "premium utilization" in text
    assert "charge attribution" in text
    assert "reserve claim-delay stress" in text
    assert "reserve lifecycle churn" in text
    assert "reserve tail sizing" in text
    assert "route-away demand curve" in text
    assert any(gate.name == "controlled route-away" and not gate.passed for gate in report.gates)
    assert any(gate.name == "controlled route-away readiness" and not gate.passed for gate in report.gates)


def test_economic_gate_passes_complete_payload() -> None:
    data = suite(C.repo_root())
    live_source = next(
        row["source"] for row in data["coverage"] if row["kind"] == "forward shadow sample"
    )
    live_rows = next(row["rows"] for row in data["benchmarks"] if row["window"] == "live shadow")
    report = gate_evaluate(
        data,
        {
            "complete": True,
            "database": live_source,
            "swaps": live_rows + 1,
            "observed_span_hours": 24.1,
            "truth_coverage": 0.9,
        },
        {"tiers": [{"swaps": 5}]},
        {
            "valid": True,
            "pair": "WETH/USDC",
            "baseline": "0x0000000000000000000000000000000000000001",
            "treatment": "0x0000000000000000000000000000000000000002",
            "pre": {"baseline_notional_e6": 1, "treatment_notional_e6": 1, "treatment_fee_pips": 500},
            "post": {"baseline_notional_e6": 1, "treatment_notional_e6": 1, "treatment_fee_pips": 700},
            "expected_post_treatment_e6": 1,
            "routed_away_e6": 0,
            "route_away_rate": 0.0,
            "fee_delta_bps": 2.0,
            "elasticity_per_bps": 0.0,
            "collection": {
                "pre_baseline": {
                    "pool": "0x0000000000000000000000000000000000000001",
                    "kind": "v3",
                    "start_block": 100,
                    "end_block": 200,
                    "swaps": 1,
                    "quote_notional_e6": 1,
                },
                "pre_treatment": {
                    "pool": "0x0000000000000000000000000000000000000002",
                    "kind": "v4",
                    "pool_id": "0x01",
                    "start_block": 100,
                    "end_block": 200,
                    "swaps": 1,
                    "quote_notional_e6": 1,
                },
                "post_baseline": {
                    "pool": "0x0000000000000000000000000000000000000001",
                    "kind": "v3",
                    "start_block": 201,
                    "end_block": 301,
                    "swaps": 1,
                    "quote_notional_e6": 1,
                },
                "post_treatment": {
                    "pool": "0x0000000000000000000000000000000000000002",
                    "kind": "v4",
                    "pool_id": "0x01",
                    "start_block": 201,
                    "end_block": 301,
                    "swaps": 1,
                    "quote_notional_e6": 1,
                },
            },
        },
        {"pair": "WETH/USDT", "tiers": [{"swaps": 5}]},
        {"pair": "WETH/USDC", "band_totals": {"50": 1_000_000}, "tiers": [{"fee_pips": 500}]},
        {"pair": "WETH/USDT", "band_totals": {"50": 1_000_000}, "tiers": [{"fee_pips": 500}]},
        {"swaps": 10, "pyth_health_rows": 10, "staleness_p90_ms": 1000},
        {"rows": [{"label": "fresh"}, {"label": "lag2"}, {"label": "lag5"}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}]},
        {"rows": [{"window": "calm", "threshold_e6": 10_000_000}, {"window": "vol", "threshold_e6": 50_000_000}, {"window": "live shadow", "threshold_e6": 100_000_000}]},
        {"rows": 10, "labels": [{"label": "fresh", "missed_extra_e6": 1}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}]},
        {"rows": [{"window": "calm"}, {"window": "vol", "hedge_improvement_e6": 1}]},
        _complete_hedge_execution_report(),
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"window": "calm", "route_away": 0.10}, {"window": "calm", "route_away": 0.25}, {"window": "calm", "route_away": 0.50}, {"window": "calm", "route_away": 0.75}, {"window": "vol", "route_away": 0.10}, {"window": "vol", "route_away": 0.25}, {"window": "vol", "route_away": 0.50}, {"window": "vol", "route_away": 0.75}]},
        {"windows": [{"window": "calm"}, {"window": "vol"}], "iterations": 10},
        {"rows": [{"window": "calm", "bucket": "<$1k"}, {"window": "vol", "bucket": "<$1k"}]},
        {"rows": 10, "buckets": [{"bucket": "<=1s"}, {"bucket": "1-2s"}, {"bucket": "2-5s"}, {"bucket": ">5s/missing"}]},
        {"rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"route_total_notional_e6": 1, "rows": [{"window": "calm"}, {"window": "vol"}, {"window": "live shadow"}]},
        {"rows": [{"path": "calm 30d"}, {"path": "weekly vol shock 30d"}, {"path": "all volatile 7d"}]},
        _complete_policy_monte_carlo_report(),
        _complete_risk_adjusted_return_report(),
        _complete_chain_cost_report(),
        _complete_live_gas_snapshot_report(),
        _complete_control_plane_cost_report(),
        _complete_pnl_attribution_report(),
        _complete_capital_survival_report(),
        _complete_operator_cost_report(),
        {"rows": [{"alpha": "1/2", "feasible": True}]},
        {"rows": [{"window": "calm", "target_apr": 0.1}, {"window": "vol", "target_apr": 0.2}, {"window": "live shadow", "target_apr": 0.3}]},
        {},
        {"rows": [{"window": "calm", "child_count": 2}, {"window": "calm", "child_count": 10}, {"window": "calm", "child_count": 100}, {"window": "vol", "child_count": 2}, {"window": "vol", "child_count": 10}, {"window": "vol", "child_count": 100}]},
        {"equilibrium_rows": [{"window": "calm", "route_away": 0.0, "target_apr": 0.1}, {"window": "calm", "route_away": 0.25, "target_apr": 0.2}, {"window": "calm", "route_away": 0.5, "target_apr": 0.3}, {"window": "vol", "route_away": 0.0, "target_apr": 0.1}, {"window": "vol", "route_away": 0.25, "target_apr": 0.2}, {"window": "vol", "route_away": 0.5, "target_apr": 0.3}]},
        {"rows": [{"pair": "WETH/USDC", "trade_size_e6": 1_000_000_000, "fee_pips": 100}, {"pair": "WETH/USDC", "trade_size_e6": 10_000_000_000, "fee_pips": 500}, {"pair": "WETH/USDC", "trade_size_e6": 50_000_000_000, "fee_pips": 3000}, {"pair": "WETH/USDT", "trade_size_e6": 1_000_000_000, "fee_pips": 100}, {"pair": "WETH/USDT", "trade_size_e6": 10_000_000_000, "fee_pips": 500}, {"pair": "WETH/USDT", "trade_size_e6": 50_000_000_000, "fee_pips": 3000}]},
        {"rows": [{"window": "calm", "child_count": 2, "child_spacing_sec": 0}, {"window": "calm", "child_count": 10, "child_spacing_sec": 30}, {"window": "vol", "child_count": 2, "child_spacing_sec": 0}, {"window": "vol", "child_count": 10, "child_spacing_sec": 30}]},
        {"ready_to_collect": True, "quote_result_complete": False, "status": "ready to collect"},
        {"rows": [{"premium_headroom_bps": 1.2}, {"premium_headroom_bps": -0.4}]},
        {"quote_source": "docs/quote_route_quotes_weth_usdt.json", "rows": [{"premium_headroom_bps": 2.0}]},
        _complete_quote_headroom_stability_report(),
        _complete_quote_headroom_drift_report(),
        {"buckets": [{"label": "a"}], "rows": [{"window": "calm"}, {"window": "vol"}]},
        _complete_quote_event_headroom_report(),
        _complete_quote_provenance_report(),
        _complete_quote_elasticity_report(),
        _complete_reserve_report(),
        _complete_premium_allocation_report(),
        _complete_reserve_delay_report(),
        _complete_reserve_lifecycle_report(),
        _complete_reserve_tail_report(),
        _complete_route_demand_report(),
        markout_sensitivity_report=_complete_markout_sensitivity_report(),
        pilot_deployability_report=_complete_pilot_deployability_report(),
        range_width_deployability_report=_complete_range_width_deployability_report(),
        position_shadow_report=_complete_position_shadow_report(),
        small_capital_decision_report=_complete_small_capital_decision_report(),
        real_position_report=_complete_real_position_report(),
        real_position_portfolio_report=_complete_real_position_portfolio_report(),
        headline_uncertainty_report=_complete_headline_uncertainty_report(),
        lp_flow_response_report=_complete_lp_flow_response_report(),
        live_convergence_report=_complete_live_convergence_report(),
        live_maturity_report=_complete_live_maturity_report(),
        live_power_report=_complete_live_power_report(),
        premium_utilization_report=_complete_premium_utilization_report(),
        charge_attribution_report=_complete_charge_attribution_report(),
        route_share_stability_report=_complete_route_share_stability_report(),
        route_away_placebo_ab_report=_complete_route_away_placebo_ab_report(),
        route_ab_power_report=_complete_route_ab_power_report(),
        route_ab_sizing_report=_complete_route_ab_sizing_report(),
        guard_depeg_report=_complete_guard_depeg_report(),
        stable_opportunity_report=_complete_stable_opportunity_report(),
        market_regime_report=_complete_market_regime_report(),
        signal_quality_stress_report=_complete_signal_quality_stress_report(),
        signal_margin_report=_complete_signal_margin_report(),
    )

    assert report.complete


def test_inventory_report_covers_fixture_windows() -> None:
    report = inventory_compute(C.repo_root(), capital_e6=10_000_000_000)
    text = inventory_markdown(report)
    windows = {row["window"] for row in report["windows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert len(report["windows"]) == 6
    assert all(row["capital_e6"] == 10_000_000_000 for row in report["windows"])
    assert any(row["inventory_il_e6"] <= 0 for row in report["windows"])
    assert "LP Inventory Accounting" in text
    assert "Full-flow fee upper bound" in text


def test_inventory_report_can_include_live_shadow_path(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    rows = [
        (
            1,
            1_700_000_000_000,
            1,
            "0x1",
            0,
            "0",
            "2000000000000000000000",
            "1000000000000000000",
            1_000_000_000,
            1,
            "CALM",
            500,
            500,
            "",
            1_700_000_000_000,
        ),
        (
            2,
            1_700_000_060_000,
            2,
            "0x2",
            0,
            "2000000000000000000000",
            "2040000000000000000000",
            "1000000000000000000",
            1_000_000_000,
            1,
            "CALM",
            500,
            500,
            "",
            1_700_000_060_000,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO ledger (
            id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
            ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
            fresh_premium_pips, fresh_fallback_reason, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    conn.close()

    report = inventory_compute(C.repo_root(), capital_e6=10_000_000_000, database=db)
    text = inventory_markdown(report)
    live_rows = [row for row in report["windows"] if row["window"] == "live shadow"]

    assert report["live_rows"] == 2
    assert len(live_rows) == 3
    assert all(row["start_price_e6"] == 2_000_000_000 for row in live_rows)
    assert all(row["end_price_e6"] == 2_040_000_000 for row in live_rows)
    assert "Live shadow rows: 2" in text


def test_hedge_report_covers_fixture_windows() -> None:
    report = hedge_compute(C.repo_root(), capital_e6=10_000_000_000)
    text = hedge_markdown(report)
    windows = {row["window"] for row in report["rows"]}
    volatile_rows = [row for row in report["rows"] if row["window"] == "vol"]

    assert {"calm", "vol"}.issubset(windows)
    assert len(report["rows"]) == 18
    assert any(row["hedge_cost_e6"] > 0 for row in report["rows"])
    assert any(row["hedge_pnl_e6"] != 0 for row in volatile_rows)
    assert "Hedge Stress" in text


def test_hedge_execution_report_adds_funding_and_operational_limits() -> None:
    report = hedge_execution_compute(C.repo_root(), capital_e6=10_000_000_000)
    text = hedge_execution_markdown(report)
    rows = report["rows"]
    low = next(
        row
        for row in rows
        if row["window"] == "calm"
        and row["range_policy"] == "static +/-1%"
        and row["hedge_policy"] == "open only"
        and row["scenario"] == "low-cost perp"
    )
    thin_every = next(
        row
        for row in rows
        if row["window"] == "vol"
        and row["range_policy"] == "static +/-1%"
        and row["hedge_policy"] == "every event"
        and row["scenario"] == "thin hedge venue"
    )

    assert len(rows) == 54
    assert {"low-cost perp", "stressed funding", "thin hedge venue"}.issubset({row["scenario"] for row in rows})
    assert low["execution_cost_e6"] > 0
    assert low["funding_cost_e6"] >= 0
    assert low["total_hedge_cost_e6"] == low["execution_cost_e6"] + low["funding_cost_e6"]
    assert thin_every["status"] == "operationally infeasible"
    assert thin_every["rebalances"] > thin_every["max_rebalances_per_window"]
    assert "Hedge Execution-Cost Stress" in text
    assert "Funding APR" in text


def test_liquidity_share_report_scales_depth_share() -> None:
    root = C.repo_root()
    report = liquidity_share_compute(
        root,
        root / "docs" / "economic_tests.json",
        root / "docs" / "live-shadow-20260607T082122Z" / "status.json",
        root / "docs" / "depth_proxy.json",
        root / "docs" / "depth_proxy_weth_usdt.json",
    )
    text = liquidity_share_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert report["capacity"]
    assert all(0 < row["depth_share"] < 1 for row in report["capacity"])
    assert any(row["capital_e6"] == 10_000_000_000 for row in report["rows"])
    assert "Liquidity Share Sizing" in text
    assert "Depth Capacity" in text


def test_position_shadow_report_combines_pro_rata_and_inventory(tmp_path) -> None:
    liquidity = tmp_path / "liquidity_share_report.json"
    inventory = tmp_path / "inventory_report.json"
    liquidity.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "window": "calm",
                        "capital_e6": 10_000_000_000,
                        "depth_band_bps": 50,
                        "depth_share": 0.1,
                        "duration_hours": 1.0,
                        "pro_rata_base_e6": 2_000_000,
                        "pro_rata_extra_e6": 1_000_000,
                        "pro_rata_markout_e6": 2_000_000,
                        "pro_rata_net_e6": 1_000_000,
                    },
                    {
                        "window": "live shadow",
                        "capital_e6": 10_000_000_000,
                        "depth_band_bps": 50,
                        "depth_share": 0.1,
                        "duration_hours": 1.0,
                        "pro_rata_base_e6": 2_000_000,
                        "pro_rata_extra_e6": 1_000_000,
                        "pro_rata_markout_e6": 2_000_000,
                        "pro_rata_net_e6": 1_000_000,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    inventory.write_text(
        json.dumps(
            {
                "capital_e6": 10_000_000_000,
                "windows": [
                    {"window": "calm", "policy": "static +/-1%", "active_coverage": 1.0, "inventory_il_e6": -2_000_000},
                    {"window": "calm", "policy": "static +/-3%", "active_coverage": 0.9, "inventory_il_e6": -500_000},
                    {"window": "calm", "policy": "static +/-5%", "active_coverage": 0.8, "inventory_il_e6": -250_000},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = position_shadow_compute(liquidity, inventory)
    text = position_shadow_markdown(report)
    calm_3 = next(row for row in report["rows"] if row["window"] == "calm" and row["range_policy"] == "static +/-3%")
    live = next(row for row in report["rows"] if row["window"] == "live shadow" and row["range_policy"] == "static +/-3%")

    assert calm_3["combined_net_e6"] == 500_000
    assert calm_3["combined_net_e6"] == calm_3["pro_rata_net_e6"] + calm_3["inventory_il_e6"]
    assert calm_3["active_coverage"] == 0.9
    assert live["combined_net_e6"] is None
    assert "pro-rata only" in live["status"]
    assert report["combined_rows"] == 3
    assert report["provisional_rows"] == 3
    assert "Position-Level LP Shadow Economics" in text
    assert "Combined rows" in text


def test_small_capital_decision_report_distills_go_no_go(tmp_path) -> None:
    pilot = tmp_path / "pilot.json"
    position = tmp_path / "position.json"
    target = tmp_path / "target.json"
    status = tmp_path / "status.json"
    pilot.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "window": "calm",
                        "policy": "small active",
                        "markout_multiplier": 1.0,
                        "net_apr": 0.12,
                        "status": "viable >=10% APR",
                    },
                    {
                        "window": "vol",
                        "policy": "small active",
                        "markout_multiplier": 1.0,
                        "net_apr": -0.10,
                        "status": "negative after ops",
                    },
                    {
                        "window": "live shadow",
                        "policy": "small active",
                        "markout_multiplier": 1.0,
                        "net_apr": -0.02,
                        "status": "negative after ops",
                    },
                    {
                        "window": "calm",
                        "policy": "small active",
                        "markout_multiplier": 2.0,
                        "net_apr": -0.20,
                        "status": "negative after ops",
                    },
                    {
                        "window": "calm",
                        "policy": "micro passive",
                        "markout_multiplier": 1.0,
                        "net_apr": 0.03,
                        "status": "positive but subscale",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    position.write_text(
        json.dumps(
            {
                "rows": [
                    {"window": "calm", "capital_e6": 10_000_000_000, "combined_net_bps": 8.0},
                    {"window": "vol", "capital_e6": 10_000_000_000, "combined_net_bps": -100.0},
                    {"window": "live shadow", "capital_e6": 10_000_000_000, "pro_rata_net_e6": -10},
                    {"window": "vol", "capital_e6": 100_000_000_000, "combined_net_bps": -80.0},
                ]
            }
        ),
        encoding="utf-8",
    )
    target.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "policy": "small active",
                        "target_apr": 0.10,
                        "required_turnover_per_day": 2.7,
                        "required_daily_volume_e6": 27_000_000_000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    status.write_text('{"complete": false}', encoding="utf-8")

    report = small_capital_decision_compute(pilot, position, target, status)
    text = small_capital_decision_markdown(report)
    small = next(row for row in report["rows"] if row["profile"] == "small active")
    micro = next(row for row in report["rows"] if row["profile"] == "micro passive")
    large = next(row for row in report["rows"] if row["profile"] == "depth-share $100k")

    assert small["recommendation"] == "pilot only: calm/liquid windows"
    assert small["viable_rows_1x"] == 1
    assert small["viable_rows_2x"] == 0
    assert small["min_required_turnover_10pct"] == 2.7
    assert micro["recommendation"] == "observe only"
    assert large["recommendation"] == "no-go: sizing stress only"
    assert report["live_shadow_complete"] is False
    assert "Small-Capital Decision Matrix" in text
    assert "pilot only" in text


def test_real_position_report_marks_missing_input(tmp_path) -> None:
    input_json = tmp_path / "missing_real_position_input.json"
    template_json = tmp_path / "real_position_input_template.json"

    report = real_position_compute(C.repo_root(), input_json, template_json, env={})
    text = real_position_markdown(report)
    real_position_write_template(template_json)

    assert not report["complete"]
    assert report["status"] == "missing input"
    assert "Real Position Replay" in text
    assert "missing input" in text
    assert not report["readiness"]["ready_from_env"]
    assert "Readiness" in text
    assert "real_position_collect" in text
    assert template_json.exists()


def test_real_position_payload_from_env_materializes_input(tmp_path) -> None:
    env = {
        "REAL_POSITION_CHAIN": "base",
        "REAL_POSITION_ID": "2200741",
        "REAL_POSITION_POOL_PAIR": "WETH/USDC",
        "REAL_POSITION_CAPITAL_E6": "10000000000",
        "REAL_POSITION_VALUE_E6": "10050000000",
        "REAL_POSITION_HODL_VALUE_E6": "10000000000",
        "REAL_POSITION_FEES_EARNED_E6": "5000000",
        "REAL_POSITION_GAS_COST_E6": "1000000",
        "REAL_POSITION_IN_RANGE": "true",
    }
    input_json = tmp_path / "real_position_input.json"
    template_json = tmp_path / "real_position_input_template.json"

    payload = real_position_payload_from_env(env)
    real_position_write_input(payload, input_json)
    report = real_position_compute(C.repo_root(), input_json, template_json, env={})

    assert payload["in_range"] is True
    assert report["complete"]
    assert report["rows"][0]["net_vs_hodl_e6"] == 54_000_000
    assert input_json.exists()


def test_real_position_metadata_decodes_position_info_and_renders(tmp_path) -> None:
    info = 2163355214880867104041076501053215742352868332531936706076365088603179565056
    tick_lower, tick_upper, has_subscriber = real_position_decode_info(info)
    sqrt_price = 3_418_626_803_371_505_763_286_168_306
    sqrt_lower = real_position_sqrt_price_at_tick(tick_lower)
    sqrt_upper = real_position_sqrt_price_at_tick(tick_upper)
    amount0, amount1 = real_position_amounts_for_liquidity(
        sqrt_price,
        sqrt_lower,
        sqrt_upper,
        4_572_842_275,
    )
    position_value_e6 = real_position_quote_value_e6(amount0, amount1, sqrt_price, 6)
    metadata = {
        "status": "metadata collected",
        "chain": "base",
        "source_url": "https://app.uniswap.org/positions/v4/base/2200741",
        "position_id": "2200741",
        "position_manager": "0x7c5f5a4bbd8fd63184577525326123b519429bdc",
        "state_view": "0xa3c0c9b65bad0b08107aa264b0f3db444b867a71",
        "block_number": 47_026_883,
        "owner": "0x2782B3d4cd06256a4C21ADbE51a9933D429706Ca",
        "token0": "LIKE",
        "token1": "USDC",
        "token0_address": "0x1EE5DD1794C28F559f94d2cc642BaE62dC3be5cf",
        "token1_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "token0_decimals": 6,
        "token1_decimals": 6,
        "pool_pair": "LIKE/USDC",
        "fee_pips": 10_000,
        "tick_spacing": 200,
        "hooks": "0x0000000000000000000000000000000000000000",
        "pool_id": "0x04c86a68b10b44e9a27c6851350afe8655b1eabf0661c3729b82d4ab3eaa8bcf",
        "position_info": str(info),
        "has_subscriber": has_subscriber,
        "position_liquidity": 4_572_842_275,
        "pool_liquidity": 878_739_475_452,
        "sqrt_price_x96": sqrt_price,
        "current_tick": -62_866,
        "protocol_fee": 0,
        "lp_fee": 10_000,
        "tick_lower": tick_lower,
        "tick_upper": tick_upper,
        "in_range": tick_lower <= -62_866 <= tick_upper,
        "sqrt_lower_x96": sqrt_lower,
        "sqrt_upper_x96": sqrt_upper,
        "amount0_raw": amount0,
        "amount1_raw": amount1,
        "amount0_human": "3465.648998",
        "amount1_human": "25.217892",
        "spot_price_token1_per_token0": "0.001861847985487547483192368962072541917412147400224883259354528892767995597676457502674445609914037802",
        "computed_position_value_e6": position_value_e6,
        "fee_owed0_raw": 82_975_466,
        "fee_owed1_raw": 276_306,
        "fee_owed0_human": "82.975466",
        "fee_owed1_human": "0.276306",
        "computed_uncollected_fees_e6": 430_821,
        "computed_position_value_with_uncollected_fees_e6": position_value_e6 + 430_821,
    }
    metadata_path = tmp_path / "docs" / "real_position_metadata.json"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    report = real_position_compute(tmp_path, tmp_path / "missing.json", tmp_path / "template.json", env={})
    text = real_position_markdown(report)
    metadata_text = real_position_metadata_markdown(metadata)

    assert tick_lower == -65_600
    assert tick_upper == -62_200
    assert has_subscriber is False
    assert amount0 == 3_465_648_998
    assert amount1 == 25_217_892
    assert position_value_e6 == 31_670_403
    assert metadata["in_range"] is True
    assert "On-Chain Metadata" in text
    assert "LIKE/USDC" in text
    assert "Real Position On-Chain Metadata" in metadata_text
    assert "$31.67" in metadata_text


def test_real_position_report_computes_net_vs_hodl(tmp_path) -> None:
    input_json = tmp_path / "real_position_input.json"
    template_json = tmp_path / "real_position_input_template.json"
    input_json.write_text(
        json.dumps(
            {
                "chain": "base",
                "position_id": "2200741",
                "pool_pair": "WETH/USDC",
                "capital_e6": 10_000_000_000,
                "position_value_e6": 10_050_000_000,
                "hodl_value_e6": 10_000_000_000,
                "fees_earned_e6": 5_000_000,
                "gas_cost_e6": 1_000_000,
                "tick_lower": -100,
                "tick_upper": 100,
                "current_tick": 0,
                "in_range": True,
            }
        ),
        encoding="utf-8",
    )

    report = real_position_compute(C.repo_root(), input_json, template_json)
    text = real_position_markdown(report)
    row = report["rows"][0]

    assert report["complete"]
    assert row["inventory_il_e6"] == 50_000_000
    assert row["net_vs_hodl_e6"] == 54_000_000
    assert row["net_vs_hodl_bps"] == 54.0
    assert row["status"] == "in range"
    assert "Net vs HODL" in text


def test_real_position_portfolio_falls_back_to_single_position_input(tmp_path) -> None:
    single = tmp_path / "real_position_input.json"
    portfolio = tmp_path / "real_position_portfolio_input.json"
    template = tmp_path / "real_position_portfolio_input_template.json"
    single.write_text(
        json.dumps(
            {
                "chain": "base",
                "position_id": "1",
                "pool_pair": "WETH/USDC",
                "fee_pips": 500,
                "capital_e6": 10_000_000,
                "position_value_e6": 9_500_000,
                "hodl_value_e6": 10_000_000,
                "fees_earned_e6": 100_000,
                "gas_cost_e6": 10_000,
                "in_range": True,
            }
        ),
        encoding="utf-8",
    )

    real_position_portfolio_write_template(template)
    report = real_position_portfolio_compute(C.repo_root(), portfolio, single, template)
    text = real_position_portfolio_markdown(report)

    assert not report["complete"]
    assert report["summary"]["complete_positions"] == 1
    assert report["input_source"] == str(single)
    assert "Real Position Portfolio Replay" in text
    assert "not enough to characterize portfolio behavior" in text


def test_real_position_portfolio_requires_diverse_audited_positions(tmp_path) -> None:
    single = tmp_path / "single.json"
    portfolio = tmp_path / "portfolio.json"
    template = tmp_path / "template.json"
    positions = []
    for index, (pair, fee_pips, in_range) in enumerate(
        (("WETH/USDC", 500, True), ("WETH/USDC", 3000, False), ("LIKE/USDC", 10000, True)),
        start=1,
    ):
        positions.append(
            {
                "chain": "base",
                "position_id": str(index),
                "pool_pair": pair,
                "fee_pips": fee_pips,
                "capital_e6": 10_000_000,
                "position_value_e6": 10_100_000,
                "hodl_value_e6": 10_000_000,
                "fees_earned_e6": 50_000,
                "gas_cost_e6": 0,
                "in_range": in_range,
            }
        )
    portfolio.write_text(json.dumps({"positions": positions}), encoding="utf-8")

    report = real_position_portfolio_compute(C.repo_root(), portfolio, single, template)
    text = real_position_portfolio_markdown(report)

    assert report["complete"]
    assert report["summary"]["complete_positions"] == 3
    assert report["breadth"]["pool_pairs"] == 2
    assert report["breadth"]["fee_tiers"] == 3
    assert report["breadth"]["range_statuses"] == 2
    assert report["summary"]["net_vs_hodl_e6"] == 450_000
    assert "Portfolio Summary" in text


def test_route_away_break_even_computes_thresholds() -> None:
    row = break_even_row(
        {
            "window": "sample",
            "name": "PegGuard selected",
            "notional_e6": 1_000_000_000,
            "base_fee_e6": 500_000,
            "extra_e6": 200_000,
            "markout_e6": 400_000,
            "net_e6": 300_000,
            "charged_base_fee_e6": 100_000,
            "charged_markout_e6": 50_000,
        }
    )

    assert row.premium_haircut_zero_rate == 1.5
    assert row.charged_flow_zero_rate == 1.2
    assert row.charged_flow_static_parity_rate == 0.8


def test_route_away_break_even_report_covers_selected_windows() -> None:
    root = C.repo_root()
    report = break_even_compute(root / "docs" / "economic_tests.json")
    text = break_even_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert "Route-Away Break-Even" in text
    assert "Charged-flow zero-net" in text


def test_adverse_route_away_removes_best_flow_first() -> None:
    rows = adverse_rows(
        "sample",
        [
            FlowEvent(1, 1_000_000_000, 500_000, 500_000, 0),
            FlowEvent(2, 1_000_000_000, 500_000, 100_000, 1_000_000),
            FlowEvent(3, 1_000_000_000, 500_000, 0, 2_000_000),
        ],
        (0.50,),
    )
    text = adverse_route_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    row = rows[0]

    assert row.removed_notional_e6 == 1_000_000_000
    assert row.removed_rows == 1
    assert row.adverse_net_e6 < row.uniform_net_e6
    assert row.adverse_gap_bps < 0
    assert "Adverse Route-Away Stress" in text


def test_insurance_reserve_rows_measure_claim_solvency() -> None:
    rows = reserve_rows(
        "sample",
        [
            ReserveEvent(1, 1_000_000_000, 100_000, 100, 1, 200_000),
            ReserveEvent(2, 1_000_000_000, 0, 0, 1, 300_000),
            ReserveEvent(3, 1_000_000_000, 50_000, 50, 0, 100_000),
        ],
    )
    text = insurance_reserve_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    charged_100 = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout" and row.payout_rate == 1.0
    )
    all_positive_100 = next(row for row in rows if row.claim_basis == "all positive markout" and row.payout_rate == 1.0)

    assert charged_100.claim_rows == 1
    assert charged_100.claims_e6 == 200_000
    assert charged_100.terminal_shortfall_e6 == 50_000
    assert charged_100.max_deficit_e6 == 100_000
    assert all_positive_100.claims_e6 == 600_000
    assert all_positive_100.coverage_ratio == 0.25
    assert "Insurance Reserve Solvency" in text
    assert "premium-only reserve" in text


def test_reserve_delay_report_separates_cash_from_pending_liability() -> None:
    rows = delay_rows(
        "sample",
        [
            ReserveEvent(1, 1_000_000_000, 100_000, 100, 1, 300_000),
            ReserveEvent(1 + 2 * 86_400_000, 1_000_000_000, 300_000, 300, 0, 0),
        ],
    )
    text = reserve_delay_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    same_day = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout"
        and row.payout_rate == 1.0
        and row.claim_delay_days == 0
    )
    delayed = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout"
        and row.payout_rate == 1.0
        and row.claim_delay_days == 7
    )

    assert same_day.required_cash_seed_e6 == 200_000
    assert same_day.required_economic_seed_e6 == 200_000
    assert delayed.required_cash_seed_e6 == 0
    assert delayed.required_economic_seed_e6 == 200_000
    assert delayed.hidden_liability_gap_e6 == 200_000
    assert delayed.cash_survives_without_seed
    assert not delayed.economically_solvent_without_seed
    assert "Reserve Claim Delay Stress" in text


def test_premium_allocation_frontier_splits_lp_and_reserve() -> None:
    rows = allocation_rows(
        "sample",
        [
            ReserveEvent(1, 1_000_000_000, 300_000, 300, 1, 200_000),
            ReserveEvent(2, 1_000_000_000, 100_000, 100, 1, 500_000),
        ],
    )
    text = premium_allocation_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    zero = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout" and row.reserve_share == 0.0
    )
    full = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout" and row.reserve_share == 1.0
    )
    half = next(
        row
        for row in rows
        if row.claim_basis == "charged correcting markout" and row.reserve_share == 0.5
    )

    assert zero.lp_extra_kept_e6 == 400_000
    assert zero.reserve_inflow_e6 == 0
    assert full.lp_extra_kept_e6 == 0
    assert full.reserve_inflow_e6 == 400_000
    assert full.reserve_required_seed_e6 == 300_000
    assert half.reserve_coverage_ratio == 200_000 / 700_000
    assert half.lp_net_before_claims_e6 > full.lp_net_before_claims_e6
    assert "Premium Allocation Frontier" in text


def test_reserve_lifecycle_rows_apply_withdrawal_churn() -> None:
    rows = lifecycle_rows(
        "sample",
        [
            ReserveEvent(1, 1_000_000_000, 300_000, 300, 1, 100_000),
            ReserveEvent(2, 1_000_000_000, 300_000, 300, 1, 100_000),
        ],
    )
    text = reserve_lifecycle_markdown({"model": "test", "rows": [row.__dict__ for row in rows]})
    monthly_skim = next(
        row
        for row in rows
        if row.horizon_days == 30
        and row.claim_basis == "charged correcting markout"
        and row.policy == "monthly 25% surplus skim"
    )
    zero_seed = next(
        row
        for row in rows
        if row.horizon_days == 30
        and row.claim_basis == "charged correcting markout"
        and row.policy == "zero seed compound"
    )

    assert monthly_skim.withdrawal_events == 1
    assert monthly_skim.withdrawals_e6 > 0
    assert monthly_skim.survived_without_topup
    assert zero_seed.premium_e6 > zero_seed.claims_e6
    assert "Reserve Lifecycle Churn" in text


def test_reserve_tail_row_measures_event_order_seed() -> None:
    row = reserve_tail_row(
        "sample",
        [
            ReserveEvent(1, 1_000_000_000, 0, 0, 1, 100_000),
            ReserveEvent(2, 1_000_000_000, 200_000, 200, 0, 0),
        ],
        "all positive markout",
        Fraction(1, 1),
        iterations=20,
        seed=1,
    )

    assert row.observed_seed_e6 == 100_000
    assert row.terminal_shortfall_e6 == 0
    assert row.p95_seed_e6 == 100_000
    assert row.cvar95_seed_e6 >= row.p95_seed_e6
    assert row.seed_needed_probability > 0


def test_reserve_tail_report_covers_fixture_windows() -> None:
    root = C.repo_root()
    fixture, _ = fixture_events(root, "calm")
    rows = reserve_tail_rows(
        "calm",
        [ReserveEvent(event.t_ms, event.notional_e6, event.peg_extra_e6, event.peg_premium_pips, event.truth_corr, event.truth_markout_e6) for event in fixture],
        iterations=10,
        seed=1,
    )
    text = reserve_tail_markdown({"model": "test", "iterations": 10, "seed": 1, "rows": [row.__dict__ for row in rows]})

    assert len(rows) == 9
    assert any(row.claim_basis == "all positive markout" for row in rows)
    assert "Reserve Tail Sizing" in text
    assert "CVaR95" in text


def test_bootstrap_window_reports_uncertainty() -> None:
    row = bootstrap_window(
        "sample",
        [
            BootEvent(1_000_000, 500, 100, 200, 100, 100),
            BootEvent(1_000_000, 500, 0, 2_000, 0, 0),
            BootEvent(1_000_000, 500, 200, 100, 200, 200),
        ],
        iterations=50,
        seed=1,
    )

    assert row.rows == 3
    assert row.iterations == 50
    assert row.net_bps_p05 <= row.net_bps_p50 <= row.net_bps_p95
    assert row.precision_ge_90_probability == 1


def test_bootstrap_report_covers_fixture_windows() -> None:
    report = bootstrap_compute(C.repo_root(), iterations=50, seed=1)
    text = bootstrap_markdown(report)
    windows = {row["window"] for row in report["windows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert report["iterations"] == 50
    assert "Bootstrap Robustness" in text
    assert "P(net>=0)" in text


def test_headline_uncertainty_report_covers_headline_metrics() -> None:
    report = headline_uncertainty_compute(C.repo_root(), iterations=25, seed=1)
    text = headline_uncertainty_markdown(report)
    windows = {row["window"] for row in report["windows"]}
    policies = {(row["window"], row["policy"]) for row in report["policies"]}
    calm = next(row for row in report["windows"] if row["window"] == "calm")

    assert {"calm", "vol"}.issubset(windows)
    assert ("calm", "small active") in policies
    assert calm["net_bps_p05"] <= calm["net_bps_p50"] <= calm["net_bps_p95"]
    assert "Headline Economic Uncertainty" in text
    assert "Small-Capital APR Bands" in text


def test_size_bucket_rows_assign_boundaries() -> None:
    rows = bucket_rows(
        "sample",
        [
            BucketEvent(1, 999_999_999, 1, 0, 0, 0, 0),
            BucketEvent(2, 1_000_000_000, 1, 0, 0, 0, 0),
            BucketEvent(3, 10_000_000_000, 1, 0, 0, 0, 0),
            BucketEvent(4, 50_000_000_000, 1, 0, 0, 0, 0),
        ],
    )
    counts = {row.bucket: row.rows for row in rows}

    assert counts["<$1k"] == 1
    assert counts["$1k-$10k"] == 1
    assert counts["$10k-$50k"] == 1
    assert counts[">=$50k"] == 1


def test_size_bucket_report_covers_fixture_windows() -> None:
    report = size_bucket_compute(C.repo_root())
    text = size_bucket_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert len(report["buckets"]) == 4
    assert "Trade-Size Buckets" in text
    assert "Positive rows" in text


def test_market_regime_report_segments_markout_and_gas() -> None:
    events = [
        RegimeEvent(1, 1_000_000_000, 500_000, 10_000, 50_000, 10, 1),
        RegimeEvent(2, 1_000_000_000, 500_000, 10_000, 250_000, 10, 1),
        RegimeEvent(3, 1_000_000_000, 500_000, 10_000, 700_000, 10, 0, True),
    ]
    rows = regime_rows("live shadow", events, "test")
    report = {"complete": True, "database": "test.sqlite3", "rows": [row.__dict__ for row in rows]}
    text = market_regime_markdown(report)
    counts = {row.segment: row.rows for row in rows}
    oracle = next(row for row in rows if row.segment == "oracle-lag/fallback")
    stressed = next(row for row in rows if row.segment == "high-vol >=5bp")

    assert counts["quiet <1bp"] == 1
    assert counts["normal 1-5bp"] == 1
    assert counts["high-vol >=5bp"] == 1
    assert oracle.rows == 1
    assert stressed.stressed_l2_gas_bps > stressed.low_l2_gas_bps
    assert "Market-Regime Segments" in text
    assert "stressed-L2" in text


def test_market_regime_report_covers_fixture_windows() -> None:
    report = market_regime_compute(C.repo_root(), C.repo_root() / "shadow" / "does_not_exist.sqlite3")
    windows = {row["window"] for row in report["rows"]}

    assert report["complete"]
    assert {"calm", "vol"}.issubset(windows)
    assert any(row["segment"] == "high-vol >=5bp" and row["rows"] > 0 for row in report["rows"])


def test_signal_quality_stress_report_penalizes_false_precision(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "rows": 10,
                        "notional_e6": 1_000_000_000,
                        "markout_e6": 40_000_000,
                        "base_fee_e6": 5_000_000,
                        "extra_e6": 10_000_000,
                        "premium_total_e6": 10_000_000,
                        "premium_correct_e6": 9_000_000,
                    },
                    {
                        "window": "vol",
                        "name": "PegGuard selected",
                        "rows": 10,
                        "notional_e6": 1_000_000_000,
                        "markout_e6": 40_000_000,
                        "base_fee_e6": 5_000_000,
                        "extra_e6": 10_000_000,
                        "premium_total_e6": 10_000_000,
                        "premium_correct_e6": 9_000_000,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = signal_quality_stress_compute(economic_tests)
    text = signal_quality_stress_markdown(report)
    observed = next(row for row in report["rows"] if row["window"] == "calm" and row["scenario"] == "observed")
    false_equal = next(row for row in report["rows"] if row["window"] == "calm" and row["scenario"] == "false 100pct correct")

    assert observed["precision"] == 0.9
    assert false_equal["precision"] < 0.5
    assert false_equal["raw_net_e6"] > observed["raw_net_e6"]
    assert false_equal["aligned_net_e6"] < observed["aligned_net_e6"]
    assert false_equal["status"] == "precision broken"
    assert "Signal Quality Stress" in text


def test_signal_margin_report_computes_precision_headroom(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "rows": 10,
                        "notional_e6": 1_000_000_000,
                        "markout_e6": 12_000_000,
                        "base_fee_e6": 5_000_000,
                        "premium_total_e6": 10_000_000,
                        "premium_correct_e6": 9_000_000,
                    },
                    {
                        "window": "vol",
                        "name": "PegGuard selected",
                        "rows": 10,
                        "notional_e6": 1_000_000_000,
                        "markout_e6": 12_000_000,
                        "base_fee_e6": 5_000_000,
                        "premium_total_e6": 10_000_000,
                        "premium_correct_e6": 9_000_000,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = signal_margin_compute(economic_tests)
    text = signal_margin_markdown(report)
    row = next(row for row in report["rows"] if row["window"] == "calm")

    assert row["observed_precision"] == 0.9
    assert row["precision_breakeven"] == 0.85
    assert round(row["precision_headroom_pp"], 4) == 0.05
    assert round(row["max_missed_correct_share"], 4) == round(1_000_000 / 9_000_000, 4)
    assert row["status"] == "positive margin"
    assert "Signal Margin" in text


def test_staleness_bucket_report_segments_live_rows(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    rows = [
        (1, 500, ""),
        (2, 1_500, ""),
        (3, 4_000, ""),
        (4, 6_000, "STALE_OR_MISSING"),
        (5, 500, "CONF_SPIKE"),
    ]
    for idx, staleness_ms, reason in rows:
        premium = 10 if not reason else 0
        extra = 1_000 if not reason else 0
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, oracle_staleness_observed_ms,
                fresh_extra_e6, fresh_premium_pips, fresh_fallback_reason, created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                1_700_000_000_000 + idx,
                idx,
                f"0x{idx}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                1_000_000_000,
                1,
                "CALM",
                staleness_ms,
                extra,
                premium,
                reason,
                1_700_000_000_000,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (idx, 1, "1000000000000000000", 1, 1, 100_000, 1_700_000_001_000),
        )
    conn.commit()
    conn.close()

    report = staleness_bucket_compute(db)
    text = staleness_bucket_markdown(report)
    buckets = {row["bucket"]: row for row in report["buckets"]}

    assert report["rows"] == 5
    assert buckets["<=1s"]["rows"] == 1
    assert buckets["1-2s"]["rows"] == 1
    assert buckets["2-5s"]["rows"] == 1
    assert buckets[">5s/missing"]["rows"] == 1
    assert buckets["other fallback"]["rows"] == 1
    assert "Oracle Staleness Buckets" in text


def test_base_fee_report_computes_required_base() -> None:
    row = base_fee_row(
        {
            "window": "sample",
            "name": "PegGuard selected",
            "notional_e6": 1_000_000_000,
            "markout_e6": 800_000,
            "extra_e6": 200_000,
            "net_bps": -1.0,
        }
    )

    assert row.required_base_pips_zero == 600
    assert row.required_base_pips_1bps == 700
    assert row.required_base_pips_5bps == 1100
    assert row.current_surplus_vs_zero_pips == -100


def test_base_fee_report_covers_selected_windows() -> None:
    root = C.repo_root()
    report = base_fee_compute(root / "docs" / "economic_tests.json")
    text = base_fee_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert {"calm", "vol"}.issubset(windows)
    assert "Base-Fee Adequacy" in text
    assert "Required base for 0 bps net" in text


def test_markout_sensitivity_report_rescales_truth_markout(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "vol",
                        "name": "PegGuard selected",
                        "notional_e6": 1_000_000_000,
                        "base_fee_e6": 500_000,
                        "extra_e6": 200_000,
                        "markout_e6": 800_000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = markout_sensitivity_compute(economic_tests)
    rows = report["rows"]
    one_x = next(row for row in rows if row["markout_multiplier"] == 1.0)
    two_x = next(row for row in rows if row["markout_multiplier"] == 2.0)
    text = markout_sensitivity_markdown(report)

    assert len(rows) == 6
    assert one_x["net_e6"] == -100_000
    assert two_x["net_e6"] == -900_000
    assert two_x["required_base_pips_zero"] > one_x["required_base_pips_zero"]
    assert two_x["status"] == "net negative"
    assert "Truth Markout Sensitivity" in text


def test_target_fee_report_maps_required_fee_to_proxy_tier(tmp_path) -> None:
    base_fee = tmp_path / "base_fee.json"
    base_fee.write_text(
        """
        {
          "rows": [
            {"window": "vol", "required_base_pips_zero": 548, "required_base_pips_1bps": 648, "required_base_pips_5bps": 1048}
          ]
        }
        """,
        encoding="utf-8",
    )
    route_proxy = tmp_path / "route_proxy.json"
    route_proxy.write_text(
        """
        {
          "pair": "WETH/USDC",
          "total_notional_e6": 1000000,
          "high_fee_volume_share": 0.03,
          "tiers": [
            {"fee_pips": 500, "notional_e6": 970000},
            {"fee_pips": 3000, "notional_e6": 30000}
          ]
        }
        """,
        encoding="utf-8",
    )

    report = target_fee_compute(base_fee, route_proxy)
    text = target_fee_markdown(report)
    rows = {(row["window"], row["target"]): row for row in report["rows"]}

    assert rows[("vol", "0 bps net")]["nearest_tier_pips"] == 3000
    assert rows[("vol", "0 bps net")]["viability"] == "thin"
    assert rows[("vol", "5 bps net")]["nearest_tier_pips"] == 3000
    assert "Target Fee Viability" in text


def test_capital_path_report_compounds_measured_policy_rows(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    rows = []
    for window, apr in (("calm", 0.12), ("vol", -0.24), ("live shadow", 0.06)):
        rows.append(
            {
                "window": window,
                "policy": "small active",
                "scenario": "hook + Pyth, low L2",
                "capital_usdc": 10_000,
                "net_apr": apr,
            }
        )
    economic_tests.write_text(json.dumps({"gas_adjusted_policies": rows}), encoding="utf-8")

    report = capital_path_compute(economic_tests)
    text = capital_path_markdown(report)
    paths = {row["path"] for row in report["rows"]}
    vol = next(row for row in report["rows"] if row["path"] == "all volatile 7d")
    weekly = next(row for row in report["rows"] if row["path"] == "weekly vol shock 30d")

    assert {"calm 30d", "weekly vol shock 30d", "all volatile 7d", "live shadow 30d"}.issubset(paths)
    assert vol["ending_capital_e6"] < vol["start_capital_e6"]
    assert vol["loss_days"] == 7
    assert weekly["window_counts"]["vol"] == 4
    assert "Capital Path Stress" in text


def test_policy_monte_carlo_report_simulates_regime_mixes(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    rows = []
    for window, apr in (("calm", 0.12), ("vol", -0.24)):
        for policy, capital in (("micro passive", 2_500), ("small active", 10_000), ("focused active", 25_000)):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "window": window,
                        "policy": policy,
                        "scenario": scenario,
                        "capital_usdc": capital,
                        "net_apr": apr,
                    }
                )
    economic_tests.write_text(json.dumps({"gas_adjusted_policies": rows}), encoding="utf-8")

    report = policy_monte_carlo_compute(economic_tests, iterations=100, seed=1)
    text = policy_monte_carlo_markdown(report)
    mixes = {row["mix"] for row in report["rows"]}
    stress = next(
        row
        for row in report["rows"]
        if row["mix"] == "stress 30d" and row["policy"] == "small active" and row["scenario"] == "hook + Pyth, low L2"
    )

    assert {"routine 30d", "shock 30d", "stress 30d", "routine 90d"}.issubset(mixes)
    assert stress["probability_loss"] > 0
    assert stress["average_vol_days"] > 0
    assert "Policy Monte Carlo" in text
    assert "P(loss)" in text


def test_risk_adjusted_return_report_scores_regime_mixes(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    rows = []
    for window, apr in (("calm", 0.18), ("vol", -0.12)):
        for policy, capital in (("micro passive", 2_500), ("small active", 10_000), ("focused active", 25_000)):
            for scenario in ("hook + Pyth, low L2", "hook + Pyth, stressed L2"):
                rows.append(
                    {
                        "window": window,
                        "policy": policy,
                        "scenario": scenario,
                        "capital_usdc": capital,
                        "net_apr": apr,
                    }
                )
    economic_tests.write_text(json.dumps({"gas_adjusted_policies": rows}), encoding="utf-8")

    report = risk_adjusted_return_compute(economic_tests)
    text = risk_adjusted_return_markdown(report)
    mixes = {row["mix"] for row in report["rows"]}
    routine = next(
        row
        for row in report["rows"]
        if row["mix"] == "routine 30d" and row["policy"] == "small active" and row["scenario"] == "hook + Pyth, low L2"
    )
    stress = next(
        row
        for row in report["rows"]
        if row["mix"] == "stress 30d" and row["policy"] == "small active" and row["scenario"] == "hook + Pyth, low L2"
    )

    assert {"routine 30d", "shock 30d", "stress 30d", "routine 90d"}.issubset(mixes)
    assert routine["annual_mean_return"] > stress["annual_mean_return"]
    assert routine["loss_day_probability"] == 0.1
    assert stress["loss_day_probability"] == 0.5
    assert routine["sharpe_like"] is not None
    assert "Risk-Adjusted Return" in text
    assert "Sortino-like" in text


def test_chain_cost_report_applies_static_chain_assumptions(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "rows": 100,
                        "notional_e6": 1_000_000_000_000,
                        "net_bps": 1.5,
                    },
                    {
                        "window": "vol",
                        "name": "PegGuard selected",
                        "rows": 100,
                        "notional_e6": 1_000_000_000_000,
                        "net_bps": -0.5,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = chain_cost_compute(economic_tests)
    text = chain_cost_markdown(report)
    chains = {row["chain"] for row in report["rows"]}
    calm_base = next(row for row in report["rows"] if row["window"] == "calm" and row["label"] == "Base low")
    vol_base = next(row for row in report["rows"] if row["window"] == "vol" and row["label"] == "Base low")

    assert {"base", "unichain", "arbitrum", "ethereum"}.issubset(chains)
    assert calm_base["gas_bps"] > 0
    assert calm_base["break_even_gas_gwei"] is not None
    assert vol_base["break_even_gas_gwei"] is None
    assert "Chain Cost Matrix" in text
    assert "Break-even gas" in text


def test_live_gas_snapshot_report_applies_rpc_gas(tmp_path, monkeypatch) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "rows": 100,
                        "notional_e6": 1_000_000_000_000,
                        "net_bps": 1.5,
                    },
                    {
                        "window": "vol",
                        "name": "PegGuard selected",
                        "rows": 100,
                        "notional_e6": 1_000_000_000_000,
                        "net_bps": -0.5,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        live_gas_module,
        "_snapshot",
        lambda endpoint, timeout_sec: GasSnapshot(
            chain=endpoint.chain,
            block_number=123,
            gas_price_wei=10_000_000,
            gas_price_gwei=0.01,
            source="test",
            ok=True,
            error=None,
            observed_at_ms=1,
        ),
    )

    report = live_gas_compute(economic_tests)
    text = live_gas_markdown(report)
    calm_base = next(row for row in report["rows"] if row["window"] == "calm" and row["chain"] == "base")
    chains = {row["chain"] for row in report["snapshots"] if row["ok"]}

    assert {"base", "unichain", "arbitrum", "ethereum"}.issubset(chains)
    assert calm_base["gas_bps"] > 0
    assert calm_base["net_after_live_gas_bps"] < calm_base["peg_net_bps"]
    assert "Live Gas Snapshot Economics" in text
    assert "RPC Snapshot" in text


def test_control_plane_cost_report_prices_callback_triggers(tmp_path) -> None:
    guard_json = tmp_path / "guard_depeg_report.json"
    gas_json = tmp_path / "live_gas_snapshot_report.json"
    guard_json.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "label": "selected",
                        "calm_triggers": 0,
                        "vol_triggers": 6,
                        "measured_bleed_total_e6": 10_000_000_000,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    gas_json.write_text(
        json.dumps(
            {
                "eth_usd_assumption": 3_500.0,
                "snapshots": [
                    {"chain": chain, "ok": True, "gas_price_gwei": 0.01}
                    for chain in ("base", "unichain", "arbitrum", "ethereum")
                ],
            }
        ),
        encoding="utf-8",
    )

    report = control_plane_cost_compute(guard_json, gas_json)
    text = control_plane_cost_markdown(report)
    base = next(row for row in report["rows"] if row["chain"] == "base")

    assert report["complete"]
    assert report["trigger_count"] == 6
    assert base["episode_cost_e6"] is not None
    assert base["cost_vs_measured_bleed_bps"] is not None
    assert base["hot_path_equivalent_swaps"] > 0
    assert "Control-Plane Cost" in text
    assert "Calm false-positive triggers: 0" in text


def test_pnl_attribution_report_decomposes_policy_return(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "notional_e6": 1_000_000_000_000,
                        "base_fee_e6": 500_000_000,
                        "extra_e6": 200_000_000,
                        "markout_e6": 100_000_000,
                    }
                ],
                "gas_adjusted_policies": [
                    {
                        "window": "calm",
                        "policy": "micro passive",
                        "scenario": "hook + Pyth, low L2",
                        "capital_usdc": 2_500,
                        "turnover_per_day": 1.0,
                        "route_away": 0.25,
                        "gas_bps": 0.1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = pnl_attribution_compute(economic_tests)
    text = pnl_attribution_markdown(report)
    row = report["rows"][0]
    component_sum = (
        row["base_annual_usdc"]
        + row["premium_kept_annual_usdc"]
        + row["route_away_haircut_annual_usdc"]
        + row["markout_annual_usdc"]
        + row["gas_annual_usdc"]
        + row["rebalance_annual_usdc"]
    )

    assert abs(row["annual_net_usdc"] - component_sum) < 1e-9
    assert row["premium_kept_annual_usdc"] > 0
    assert row["route_away_haircut_annual_usdc"] < 0
    assert row["markout_annual_usdc"] < 0
    assert row["dominant_drag"] in {"route-away haircut", "markout", "gas", "rebalance"}
    assert "PnL Attribution" in text


def test_capital_survival_report_computes_runway(tmp_path) -> None:
    pnl_report = tmp_path / "pnl_attribution_report.json"
    rows = []
    for window, annual_net in (("calm", 365.0), ("vol", -365.0)):
        rows.append(
            {
                "window": window,
                "policy": "micro passive",
                "scenario": "hook + Pyth, low L2",
                "capital_usdc": 2_500.0,
                "base_annual_usdc": 500.0,
                "premium_kept_annual_usdc": 50.0,
                "route_away_haircut_annual_usdc": -25.0,
                "markout_annual_usdc": -700.0 if window == "vol" else -100.0,
                "gas_annual_usdc": -10.0,
                "rebalance_annual_usdc": -3.0,
                "annual_net_usdc": annual_net,
            }
        )
    pnl_report.write_text(json.dumps({"rows": rows}), encoding="utf-8")

    report = capital_survival_compute(pnl_report)
    text = capital_survival_markdown(report)
    vol = next(row for row in report["rows"] if row["kind"] == "window" and row["label"] == "vol")
    calm = next(row for row in report["rows"] if row["kind"] == "window" and row["label"] == "calm")
    routine = next(row for row in report["rows"] if row["kind"] == "mix" and row["label"] == "routine 30d")

    assert calm["status"] == "covered"
    assert vol["days_to_10pct_loss"] == 250.0
    assert vol["dominant_drag"] == "markout"
    assert routine["annual_net_usdc"] > 0
    assert "Capital Survival Runway" in text


def test_operator_cost_report_applies_fixed_overhead(tmp_path) -> None:
    pnl_report = tmp_path / "pnl_attribution_report.json"
    pnl_report.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "window": "calm",
                        "policy": "micro passive",
                        "scenario": "hook + Pyth, low L2",
                        "capital_usdc": 2_500.0,
                        "annual_net_usdc": 250.0,
                        "net_apr": 0.10,
                    },
                    {
                        "window": "vol",
                        "policy": "small active",
                        "scenario": "hook + Pyth, low L2",
                        "capital_usdc": 10_000.0,
                        "annual_net_usdc": -100.0,
                        "net_apr": -0.01,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    report = operator_cost_compute(pnl_report)
    text = operator_cost_markdown(report)
    rows = {
        (row["window"], row["policy"], row["ops_scenario"]): row
        for row in report["rows"]
    }
    calm_paid = rows[("calm", "micro passive", "paid light ops")]
    calm_free = rows[("calm", "micro passive", "free operator")]
    vol_paid = rows[("vol", "small active", "paid light ops")]

    assert calm_free["annual_net_after_ops_usdc"] == 250.0
    assert calm_paid["annual_ops_cost_usdc"] == 1540.0
    assert calm_paid["annual_net_after_ops_usdc"] == -1290.0
    assert calm_paid["break_even_capital_usdc"] == 15_400.0
    assert vol_paid["break_even_capital_usdc"] is None
    assert "Operator Fixed-Cost Drag" in text


def test_pilot_deployability_report_combines_ops_and_markout_stress(tmp_path) -> None:
    pnl_report = tmp_path / "pnl_attribution_report.json"
    pnl_report.write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "window": "calm",
                        "policy": "small active",
                        "scenario": "hook + Pyth, low L2",
                        "capital_usdc": 10_000.0,
                        "turnover_per_day": 3.0,
                        "active_ratio": 0.75,
                        "base_annual_usdc": 1_000.0,
                        "premium_kept_annual_usdc": 500.0,
                        "route_away_haircut_annual_usdc": -100.0,
                        "markout_annual_usdc": -300.0,
                        "gas_annual_usdc": -50.0,
                        "rebalance_annual_usdc": -25.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = pilot_deployability_compute(pnl_report)
    text = pilot_deployability_markdown(report)
    rows = {
        (row["ops_scenario"], row["markout_multiplier"]): row
        for row in report["rows"]
    }
    free_1x = rows[("free operator", 1.0)]
    free_2x = rows[("free operator", 2.0)]
    paid_1x = rows[("paid light ops", 1.0)]

    assert free_1x["annual_net_usdc"] == 1025.0
    assert free_1x["status"] == "viable >=10% APR"
    assert free_2x["annual_net_usdc"] == 725.0
    assert free_2x["required_turnover_for_10pct"] > free_1x["required_turnover_for_10pct"]
    assert paid_1x["annual_net_usdc"] == -515.0
    assert paid_1x["status"] == "negative after ops"
    assert "Pilot Deployability Stress" in text


def test_range_width_deployability_report_sweeps_width_and_markout(tmp_path) -> None:
    economic_tests = tmp_path / "economic_tests.json"
    economic_tests.write_text(
        json.dumps(
            {
                "benchmarks": [
                    {
                        "window": "calm",
                        "name": "PegGuard selected",
                        "notional_e6": 1_000_000_000_000,
                        "base_fee_e6": 500_000_000,
                        "extra_e6": 200_000_000,
                        "markout_e6": 100_000_000,
                    }
                ],
                "gas_sensitivity": [
                    {"window": "calm", "scenario": "hook + Pyth, low L2", "gas_bps": 0.1},
                    {"window": "calm", "scenario": "hook + Pyth, stressed L2", "gas_bps": 1.0},
                ],
            }
        ),
        encoding="utf-8",
    )

    report = range_width_deployability_compute(C.repo_root(), economic_tests)
    text = range_width_deployability_markdown(report)
    rows = {
        (row["profile"], row["scenario"], row["markout_multiplier"]): row
        for row in report["rows"]
    }
    pilot_low = rows[("pilot +/-2%", "hook + Pyth, low L2", 1.0)]
    pilot_stressed = rows[("pilot +/-2%", "hook + Pyth, stressed L2", 1.0)]
    pilot_2x = rows[("pilot +/-2%", "hook + Pyth, low L2", 2.0)]

    assert len(report["rows"]) == 30
    assert {row["half_width_bps"] for row in report["rows"]} == {50, 100, 200, 500, 1000}
    assert pilot_low["net_apr"] > pilot_stressed["net_apr"]
    assert pilot_low["net_apr"] > pilot_2x["net_apr"]
    assert pilot_low["required_turnover_for_10pct"] < pilot_2x["required_turnover_for_10pct"]
    assert pilot_low["implied_capacity_for_10pct_usdc"] is not None
    assert "Range-Width Deployability Stress" in text
    assert "Operating Profiles" in text


def test_target_return_report_computes_turnover_thresholds() -> None:
    root = C.repo_root()
    report = target_return_compute(
        root,
        root / "docs" / "live-shadow-20260607T082122Z" / "economic_tests.json",
        root / "docs" / "live-shadow-20260607T082122Z" / "status.json",
    )
    text = target_return_markdown(report)
    rows = {(row["window"], row["policy"], row["target_apr"]): row for row in report["rows"]}
    calm_small_20 = rows[("calm", "small active", 0.2)]
    vol_small_10 = rows[("vol", "small active", 0.1)]

    assert calm_small_20["required_turnover_per_day"] is not None
    assert calm_small_20["required_daily_volume_e6"] > 0
    assert vol_small_10["status"] == "impossible"
    assert "Target Return Thresholds" in text


def test_alpha_sweep_report_covers_default_alpha() -> None:
    report = alpha_sweep_compute(C.repo_root(), alphas=[Fraction(1, 4), Fraction(1, 2), Fraction(1, 1)])
    text = alpha_sweep_markdown(report)
    rows = {row["alpha"]: row for row in report["rows"]}

    assert "1/2" in rows
    assert rows["1/2"]["calm"]["precision_bps"] >= 9_000
    assert rows["1/2"]["vol"]["precision_bps"] >= 9_500
    assert "Alpha Backtest Sweep" in text


def test_fallback_attribution_prices_stale_opportunity(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    rows = [
        (1, 1_700_000_000_000, "2000000000000000000000", "2000000000000000000000", "2000000000000000000000", 1, "BASIS_UNSEEDED"),
        (2, 1_700_000_001_000, "2000000000000000000000", "2000000000000000000000", "2020000000000000000000", 0, "STALE_OR_MISSING"),
    ]
    for idx, ts_ms, pre_mid, post_mid, fair, zero_for_one, reason in rows:
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime,
                fresh_publish_time_ms, fresh_fair_e18, fresh_extra_e6,
                fresh_premium_pips, fresh_fallback_reason,
                lag2_publish_time_ms, lag2_fair_e18, lag2_extra_e6,
                lag2_premium_pips, lag2_fallback_reason,
                lag5_publish_time_ms, lag5_fair_e18, lag5_extra_e6,
                lag5_premium_pips, lag5_fallback_reason,
                created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                ts_ms,
                idx,
                f"0x{idx}",
                0,
                pre_mid,
                post_mid,
                "-1000000000000000000",
                1_000_000_000,
                zero_for_one,
                "CALM",
                ts_ms,
                fair,
                0,
                0,
                reason,
                ts_ms,
                fair,
                0,
                0,
                reason,
                ts_ms,
                fair,
                0,
                0,
                reason,
                ts_ms,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (idx, 1, "1000000000000000000", 1, 1, 100_000_000, ts_ms),
        )
    conn.commit()
    conn.close()

    report = fallback_attribution_compute(db)
    text = fallback_attribution_markdown(report)
    fresh = next(row for row in report.labels if row.label == "fresh")

    assert fresh.oracle_fallback_rows == 1
    assert fresh.opportunity_rows == 1
    assert fresh.missed_extra_e6 == 4_975_000
    assert fresh.missed_precision == 1
    assert "Fallback Attribution" in text
    assert "STALE_OR_MISSING" in text


def test_risk_report_measures_drawdown_and_concentration() -> None:
    risk = risk_for_events(
        "sample",
        [
            RiskEvent(1, 1_000_000, 500, 100, 100, 500),
            RiskEvent(2, 1_000_000, 500, 0, 2_000, -1_500),
            RiskEvent(3, 1_000_000, 500, 100, 0, 600),
        ],
    )
    text = risk_markdown({"windows": [risk.__dict__]})

    assert risk.rows == 3
    assert risk.loss_rows == 1
    assert risk.max_drawdown_e6 == -1_500
    assert risk.top_5_loss_share == 1
    assert "Tail Risk And Concentration" in text


def test_drawdown_stop_report_covers_thresholds() -> None:
    report = drawdown_stop_compute(C.repo_root(), C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    text = drawdown_stop_markdown(report)
    windows = {row["window"] for row in report["rows"]}
    vol_50 = next(row for row in report["rows"] if row["window"] == "vol" and row["threshold_e6"] == 50_000_000)

    assert {"calm", "vol"}.issubset(windows)
    assert len(report["rows"]) >= 8
    assert vol_50["triggered"]
    assert vol_50["skipped_rows"] > 0
    assert "Drawdown Stop-Loss" in text


def test_order_split_report_models_rounding_leakage() -> None:
    rows = split_rows(
        "sample",
        [
            SplitEvent(1_000_001, 503, 503, 10_000, 1),
            SplitEvent(2_000_000, 0, 0, 0, 0),
        ],
        child_counts=(2, 10),
    )
    report = order_split_compute(C.repo_root(), C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3", child_counts=(2, 10))
    text = order_split_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert rows[0].leaked_extra_e6 >= 0
    assert rows[1].leaked_extra_e6 >= rows[0].leaked_extra_e6
    assert {"calm", "vol"}.issubset(windows)
    assert "Order-Splitting Sensitivity" in text
    assert "same-signal" in text


def test_sequential_split_report_models_time_spaced_basis_updates() -> None:
    events = [
        SequenceEvent(
            t_ms=1_000,
            pre_mid_e18=1_000 * C.WAD,
            post_mid_e18=1_000 * C.WAD,
            fair_e18=1_000 * C.WAD,
            ab_e18=1,
            aq_e6=1_000_000_000,
            valid=True,
            truth_corr=1,
            truth_mk_e6=1_000_000,
            update_basis=True,
            deadband_e2=C.DEADBAND_CALM_E2,
        ),
        SequenceEvent(
            t_ms=61_000,
            pre_mid_e18=1_010 * C.WAD,
            post_mid_e18=1_010 * C.WAD,
            fair_e18=1_000 * C.WAD,
            ab_e18=1,
            aq_e6=1_000_000_000,
            valid=True,
            truth_corr=1,
            truth_mk_e6=1_000_000,
            update_basis=True,
            deadband_e2=C.DEADBAND_CALM_E2,
        ),
    ]
    rows = sequential_rows("sample", events, scenarios=((2, 0), (2, 30)))
    report = sequential_split_compute(
        C.repo_root(),
        C.repo_root() / "shadow" / "live_shadow_20260607T082122Z.sqlite3",
        scenarios=((2, 0), (10, 30)),
    )
    text = sequential_split_markdown(report)
    windows = {row["window"] for row in report["rows"]}

    assert rows[0].original_extra_e6 > 0
    assert rows[1].leaked_extra_e6 >= rows[0].leaked_extra_e6
    assert {"calm", "vol"}.issubset(windows)
    assert "Sequential Split Timing Sensitivity" in text
    assert "spacing>0" in text


def test_tvl_dilution_report_covers_equilibrium_capacity() -> None:
    root = C.repo_root()
    report = tvl_dilution_compute(
        root,
        root / "docs" / "economic_tests.json",
        root / "docs" / "live-shadow-20260607T082122Z" / "status.json",
    )
    text = tvl_dilution_markdown(report)
    windows = {row["window"] for row in report["equilibrium_rows"]}
    targets = {row["target_apr"] for row in report["equilibrium_rows"]}
    calm_20 = next(
        row
        for row in report["equilibrium_rows"]
        if row["window"] == "calm" and row["route_away"] == 0.25 and row["target_apr"] == 0.20
    )
    vol_20 = next(
        row
        for row in report["equilibrium_rows"]
        if row["window"] == "vol" and row["route_away"] == 0.25 and row["target_apr"] == 0.20
    )

    assert {"calm", "vol"}.issubset(windows)
    assert {0.10, 0.20, 0.30}.issubset(targets)
    assert calm_20["max_active_capital_e6"] is not None
    assert vol_20["max_active_capital_e6"] is None
    assert "TVL Dilution And Equilibrium" in text
    assert "Max active capital" in text


def test_lp_flow_response_report_covers_adaptive_capital_paths() -> None:
    root = C.repo_root()
    report = lp_flow_response_compute(
        root,
        root / "docs" / "economic_tests.json",
        root / "docs" / "live-shadow-20260607T082122Z" / "status.json",
    )
    text = lp_flow_response_markdown(report)
    paths = {row["path"] for row in report["rows"]}
    scenarios = {row["scenario"] for row in report["rows"]}
    starts = {row["start_capital_e6"] for row in report["rows"]}

    assert {"calm 30d", "weekly vol shock 30d", "all volatile 7d"}.issubset(paths)
    assert {"hook + Pyth, low L2", "hook + Pyth, stressed L2"}.issubset(scenarios)
    assert {10_000_000_000, 25_000_000_000, 100_000_000_000}.issubset(starts)
    assert any(row["outflow_days"] > 0 for row in report["rows"])
    assert "LP Flow Response" in text
    assert "Flow Simulation" in text


def test_economic_finalize_refreshes_reports(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        live_gas_module,
        "_snapshot",
        lambda endpoint, timeout_sec: GasSnapshot(
            chain=endpoint.chain,
            block_number=1,
            gas_price_wei=10_000_000,
            gas_price_gwei=0.01,
            source="test",
            ok=True,
            error=None,
            observed_at_ms=1,
        ),
    )
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    conn.execute(
        """
        INSERT INTO ledger (
            id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
            ab_e18, aq_e6, zero_for_one, regime, fresh_extra_e6,
            fresh_premium_pips, fresh_fallback_reason, created_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            1,
            1_700_000_000_000,
            1,
            "0x1",
            0,
            "2000000000000000000000",
            "2000000000000000000000",
            "1000000000000000000",
            2_000_000_000,
            1,
            "CALM",
            10_000,
            5,
            "",
            1_700_000_000_000,
        ),
    )
    conn.execute(
        """
        INSERT INTO truth (
            ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (1, 1, "1000000000000000000", 1, 1, 100_000, 1_700_000_001_000),
    )
    conn.commit()
    conn.close()

    route_proxy = tmp_path / "route_proxy.json"
    route_proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDC",
                "total_notional_e6": 1,
                "high_fee_volume_share": 0.1,
                "tiers": [{"fee_pips": 500, "swaps": 1, "volume_share": 0.9}],
                "comparison_windows": [
                    {"lookback_blocks": 10, "duration_hours": 1, "total_notional_e6": 1, "high_fee_volume_share": 0.1, "tiers": [{"fee_pips": 500, "volume_share": 0.9}]},
                    {"lookback_blocks": 20, "duration_hours": 2, "total_notional_e6": 2, "high_fee_volume_share": 0.2, "tiers": [{"fee_pips": 500, "volume_share": 0.8}]},
                ],
            }
        ),
        encoding="utf-8",
    )
    cross_proxy = tmp_path / "cross_proxy.json"
    cross_proxy.write_text(
        json.dumps(
            {
                "pair": "WETH/USDT",
                "total_notional_e6": 1,
                "high_fee_volume_share": 0.1,
                "tiers": [{"fee_pips": 500, "swaps": 1, "volume_share": 0.95}],
                "comparison_windows": [
                    {"lookback_blocks": 10, "duration_hours": 1, "total_notional_e6": 1, "high_fee_volume_share": 0.01, "tiers": [{"fee_pips": 500, "volume_share": 0.95}]},
                    {"lookback_blocks": 20, "duration_hours": 2, "total_notional_e6": 2, "high_fee_volume_share": 0.02, "tiers": [{"fee_pips": 500, "volume_share": 0.94}]},
                ],
            }
        ),
        encoding="utf-8",
    )
    depth_proxy = tmp_path / "depth_proxy.json"
    depth_proxy.write_text('{"pair": "WETH/USDC", "band_totals": {"50": 1}, "tiers": [{"fee_pips": 500}]}', encoding="utf-8")
    cross_depth_proxy = tmp_path / "cross_depth_proxy.json"
    cross_depth_proxy.write_text('{"pair": "WETH/USDT", "band_totals": {"50": 1}, "tiers": [{"fee_pips": 500}]}', encoding="utf-8")
    route_ab = tmp_path / "route_ab.json"
    route_ab.write_text(
        '{"pre": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}, "post": {"baseline_notional_e6": 0, "treatment_notional_e6": 0}}',
        encoding="utf-8",
    )

    complete = finalize_once(
        C.repo_root(),
        FinalizePaths(
            database=db,
            reports=tmp_path / "reports",
            economic_tests_md=tmp_path / "economic_tests.md",
            economic_tests_json=tmp_path / "economic_tests.json",
            live_status_md=tmp_path / "status.md",
            live_status_json=tmp_path / "status.json",
            live_convergence_md=tmp_path / "live_convergence_report.md",
            live_convergence_json=tmp_path / "live_convergence_report.json",
            live_maturity_md=tmp_path / "live_maturity_report.md",
            live_maturity_json=tmp_path / "live_maturity_report.json",
            live_power_md=tmp_path / "live_power_report.md",
            live_power_json=tmp_path / "live_power_report.json",
            cross_pair_live_database=tmp_path / "live_shadow_weth_usdt.sqlite3",
            cross_pair_live_md=tmp_path / "cross_pair_live_report.md",
            cross_pair_live_json=tmp_path / "cross_pair_live_report.json",
            live_soak_md=tmp_path / "live_soak_report.md",
            live_soak_json=tmp_path / "live_soak_report.json",
            cross_pair_live_economics_md=tmp_path / "cross_pair_live_economics_report.md",
            cross_pair_live_economics_json=tmp_path / "cross_pair_live_economics_report.json",
            live_fee_tier_md=tmp_path / "live_fee_tier_report.md",
            live_fee_tier_json=tmp_path / "live_fee_tier_report.json",
            live_fee_tier_one_bps_glob=str(tmp_path / "live_shadow_weth_usdc_1bps_*.sqlite3"),
            live_fee_tier_thirty_bps_glob=str(tmp_path / "live_shadow_weth_usdc_30bps_*.sqlite3"),
            route_proxy_json=route_proxy,
            cross_pair_route_proxy_json=cross_proxy,
            route_share_stability_md=tmp_path / "route_share_stability_report.md",
            route_share_stability_json=tmp_path / "route_share_stability_report.json",
            route_away_placebo_ab_md=tmp_path / "route_away_placebo_ab_report.md",
            route_away_placebo_ab_json=tmp_path / "route_away_placebo_ab_report.json",
            route_ab_power_md=tmp_path / "route_ab_power_report.md",
            route_ab_power_json=tmp_path / "route_ab_power_report.json",
            route_ab_sizing_md=tmp_path / "route_ab_sizing_report.md",
            route_ab_sizing_json=tmp_path / "route_ab_sizing_report.json",
            route_baseline_probe_json=tmp_path / "route_away_baseline_probe.json",
            guard_depeg_md=tmp_path / "guard_depeg_report.md",
            guard_depeg_json=tmp_path / "guard_depeg_report.json",
            stable_opportunity_md=tmp_path / "stable_opportunity_report.md",
            stable_opportunity_json=tmp_path / "stable_opportunity_report.json",
            depth_proxy_json=depth_proxy,
            cross_pair_depth_proxy_json=cross_depth_proxy,
            oracle_health_md=tmp_path / "oracle_health.md",
            oracle_health_json=tmp_path / "oracle_health.json",
            oracle_lag_md=tmp_path / "oracle_lag_report.md",
            oracle_lag_json=tmp_path / "oracle_lag_report.json",
            risk_report_md=tmp_path / "risk_report.md",
            risk_report_json=tmp_path / "risk_report.json",
            drawdown_stop_md=tmp_path / "drawdown_stop_report.md",
            drawdown_stop_json=tmp_path / "drawdown_stop_report.json",
            fallback_attribution_md=tmp_path / "fallback_attribution.md",
            fallback_attribution_json=tmp_path / "fallback_attribution.json",
            inventory_report_md=tmp_path / "inventory_report.md",
            inventory_report_json=tmp_path / "inventory_report.json",
            hedge_report_md=tmp_path / "hedge_report.md",
            hedge_report_json=tmp_path / "hedge_report.json",
            hedge_execution_md=tmp_path / "hedge_execution_report.md",
            hedge_execution_json=tmp_path / "hedge_execution_report.json",
            liquidity_share_report_md=tmp_path / "liquidity_share_report.md",
            liquidity_share_report_json=tmp_path / "liquidity_share_report.json",
            position_shadow_report_md=tmp_path / "position_shadow_report.md",
            position_shadow_report_json=tmp_path / "position_shadow_report.json",
            route_break_even_md=tmp_path / "route_away_break_even.md",
            route_break_even_json=tmp_path / "route_away_break_even.json",
            adverse_route_away_md=tmp_path / "adverse_route_away_report.md",
            adverse_route_away_json=tmp_path / "adverse_route_away_report.json",
            route_collector_smoke_md=tmp_path / "route_away_collector_smoke.md",
            route_collector_smoke_json=tmp_path / "route_away_collector_smoke.json",
            route_window_plan_md=tmp_path / "route_away_window_plan.md",
            route_window_plan_json=tmp_path / "route_away_window_plan.json",
            route_rpc_preflight_md=tmp_path / "route_away_rpc_preflight.md",
            route_rpc_preflight_json=tmp_path / "route_away_rpc_preflight.json",
            route_readiness_md=tmp_path / "route_away_readiness.md",
            route_readiness_json=tmp_path / "route_away_readiness.json",
            route_cost_md=tmp_path / "route_cost_proxy.md",
            route_cost_json=tmp_path / "route_cost_proxy.json",
            quote_route_readiness_md=tmp_path / "quote_route_readiness.md",
            quote_route_readiness_json=tmp_path / "quote_route_readiness.json",
            quote_headroom_md=tmp_path / "quote_headroom_report.md",
            quote_headroom_json=tmp_path / "quote_headroom_report.json",
            cross_pair_quote_headroom_md=tmp_path / "quote_headroom_weth_usdt.md",
            cross_pair_quote_headroom_json=tmp_path / "quote_headroom_weth_usdt.json",
            quote_headroom_stability_md=tmp_path / "quote_headroom_stability_report.md",
            quote_headroom_stability_json=tmp_path / "quote_headroom_stability_report.json",
            quote_headroom_drift_md=tmp_path / "quote_headroom_drift_report.md",
            quote_headroom_drift_json=tmp_path / "quote_headroom_drift_report.json",
            quote_premium_stress_md=tmp_path / "quote_premium_stress.md",
            quote_premium_stress_json=tmp_path / "quote_premium_stress.json",
            quote_event_headroom_md=tmp_path / "quote_event_headroom_report.md",
            quote_event_headroom_json=tmp_path / "quote_event_headroom_report.json",
            quote_provenance_md=tmp_path / "quote_provenance_report.md",
            quote_provenance_json=tmp_path / "quote_provenance_report.json",
            quote_elasticity_md=tmp_path / "quote_elasticity_report.md",
            quote_elasticity_json=tmp_path / "quote_elasticity_report.json",
            insurance_reserve_md=tmp_path / "insurance_reserve_report.md",
            insurance_reserve_json=tmp_path / "insurance_reserve_report.json",
            premium_allocation_md=tmp_path / "premium_allocation_report.md",
            premium_allocation_json=tmp_path / "premium_allocation_report.json",
            premium_utilization_md=tmp_path / "premium_utilization_report.md",
            premium_utilization_json=tmp_path / "premium_utilization_report.json",
            charge_attribution_md=tmp_path / "charge_attribution_report.md",
            charge_attribution_json=tmp_path / "charge_attribution_report.json",
            reserve_delay_md=tmp_path / "reserve_delay_report.md",
            reserve_delay_json=tmp_path / "reserve_delay_report.json",
            reserve_lifecycle_md=tmp_path / "reserve_lifecycle_report.md",
            reserve_lifecycle_json=tmp_path / "reserve_lifecycle_report.json",
            reserve_tail_md=tmp_path / "reserve_tail_report.md",
            reserve_tail_json=tmp_path / "reserve_tail_report.json",
            bootstrap_report_md=tmp_path / "bootstrap_report.md",
            bootstrap_report_json=tmp_path / "bootstrap_report.json",
            headline_uncertainty_md=tmp_path / "headline_uncertainty_report.md",
            headline_uncertainty_json=tmp_path / "headline_uncertainty_report.json",
            size_bucket_report_md=tmp_path / "size_bucket_report.md",
            size_bucket_report_json=tmp_path / "size_bucket_report.json",
            staleness_bucket_report_md=tmp_path / "staleness_bucket_report.md",
            staleness_bucket_report_json=tmp_path / "staleness_bucket_report.json",
            market_regime_report_md=tmp_path / "market_regime_report.md",
            market_regime_report_json=tmp_path / "market_regime_report.json",
            signal_quality_stress_md=tmp_path / "signal_quality_stress_report.md",
            signal_quality_stress_json=tmp_path / "signal_quality_stress_report.json",
            signal_margin_md=tmp_path / "signal_margin_report.md",
            signal_margin_json=tmp_path / "signal_margin_report.json",
            base_fee_report_md=tmp_path / "base_fee_report.md",
            base_fee_report_json=tmp_path / "base_fee_report.json",
            markout_sensitivity_md=tmp_path / "markout_sensitivity_report.md",
            markout_sensitivity_json=tmp_path / "markout_sensitivity_report.json",
            target_fee_report_md=tmp_path / "target_fee_report.md",
            target_fee_report_json=tmp_path / "target_fee_report.json",
            capital_path_report_md=tmp_path / "capital_path_report.md",
            capital_path_report_json=tmp_path / "capital_path_report.json",
            policy_monte_carlo_md=tmp_path / "policy_monte_carlo_report.md",
            policy_monte_carlo_json=tmp_path / "policy_monte_carlo_report.json",
            risk_adjusted_return_md=tmp_path / "risk_adjusted_return_report.md",
            risk_adjusted_return_json=tmp_path / "risk_adjusted_return_report.json",
            chain_cost_md=tmp_path / "chain_cost_report.md",
            chain_cost_json=tmp_path / "chain_cost_report.json",
            live_gas_snapshot_md=tmp_path / "live_gas_snapshot_report.md",
            live_gas_snapshot_json=tmp_path / "live_gas_snapshot_report.json",
            control_plane_cost_md=tmp_path / "control_plane_cost_report.md",
            control_plane_cost_json=tmp_path / "control_plane_cost_report.json",
            pnl_attribution_md=tmp_path / "pnl_attribution_report.md",
            pnl_attribution_json=tmp_path / "pnl_attribution_report.json",
            capital_survival_md=tmp_path / "capital_survival_report.md",
            capital_survival_json=tmp_path / "capital_survival_report.json",
            operator_cost_md=tmp_path / "operator_cost_report.md",
            operator_cost_json=tmp_path / "operator_cost_report.json",
            pilot_deployability_md=tmp_path / "pilot_deployability_report.md",
            pilot_deployability_json=tmp_path / "pilot_deployability_report.json",
            range_width_deployability_md=tmp_path / "range_width_deployability_report.md",
            range_width_deployability_json=tmp_path / "range_width_deployability_report.json",
            alpha_sweep_md=tmp_path / "alpha_sweep.md",
            alpha_sweep_json=tmp_path / "alpha_sweep.json",
            target_return_md=tmp_path / "target_return_report.md",
            target_return_json=tmp_path / "target_return_report.json",
            small_capital_decision_md=tmp_path / "small_capital_decision_report.md",
            small_capital_decision_json=tmp_path / "small_capital_decision_report.json",
            real_position_md=tmp_path / "real_position_report.md",
            real_position_json=tmp_path / "real_position_report.json",
            real_position_input_json=tmp_path / "real_position_input.json",
            real_position_template_json=tmp_path / "real_position_input_template.json",
            real_position_portfolio_md=tmp_path / "real_position_portfolio_report.md",
            real_position_portfolio_json=tmp_path / "real_position_portfolio_report.json",
            real_position_portfolio_input_json=tmp_path / "real_position_portfolio_input.json",
            real_position_portfolio_template_json=tmp_path / "real_position_portfolio_input_template.json",
            route_ab_json=route_ab,
            route_demand_md=tmp_path / "route_demand_report.md",
            route_demand_json=tmp_path / "route_demand_report.json",
            order_split_md=tmp_path / "order_split_report.md",
            order_split_json=tmp_path / "order_split_report.json",
            sequential_split_md=tmp_path / "sequential_split_report.md",
            sequential_split_json=tmp_path / "sequential_split_report.json",
            tvl_dilution_md=tmp_path / "tvl_dilution_report.md",
            tvl_dilution_json=tmp_path / "tvl_dilution_report.json",
            lp_flow_response_md=tmp_path / "lp_flow_response_report.md",
            lp_flow_response_json=tmp_path / "lp_flow_response_report.json",
            evidence_md=tmp_path / "economic_evidence.md",
            completion_md=tmp_path / "economic_completion.md",
            completion_json=tmp_path / "economic_completion.json",
        ),
        min_hours=24,
        min_truth_coverage=0.8,
        min_swaps=1,
    )

    assert not complete
    assert "Shadow Summary" in (tmp_path / "reports" / "summary.md").read_text(encoding="utf-8")
    assert "Live Shadow Status" in (tmp_path / "status.md").read_text(encoding="utf-8")
    assert "Live Shadow Convergence" in (tmp_path / "live_convergence_report.md").read_text(encoding="utf-8")
    assert "Live Shadow Maturity" in (tmp_path / "live_maturity_report.md").read_text(encoding="utf-8")
    assert "Live Sample Power" in (tmp_path / "live_power_report.md").read_text(encoding="utf-8")
    assert "Cross-Pair Live Shadow" in (tmp_path / "cross_pair_live_report.md").read_text(encoding="utf-8")
    assert "Live Soak Tracker" in (tmp_path / "live_soak_report.md").read_text(encoding="utf-8")
    assert "Cross-Pair Live Economics" in (tmp_path / "cross_pair_live_economics_report.md").read_text(encoding="utf-8")
    assert "Fee-Tier Live Shadow" in (tmp_path / "live_fee_tier_report.md").read_text(encoding="utf-8")
    assert "Oracle Health Economics" in (tmp_path / "oracle_health.md").read_text(encoding="utf-8")
    assert "Oracle Lag Stress" in (tmp_path / "oracle_lag_report.md").read_text(encoding="utf-8")
    assert "Tail Risk And Concentration" in (tmp_path / "risk_report.md").read_text(encoding="utf-8")
    assert "Drawdown Stop-Loss" in (tmp_path / "drawdown_stop_report.md").read_text(encoding="utf-8")
    assert "Fallback Attribution" in (tmp_path / "fallback_attribution.md").read_text(encoding="utf-8")
    assert "LP Inventory Accounting" in (tmp_path / "inventory_report.md").read_text(encoding="utf-8")
    assert "Hedge Stress" in (tmp_path / "hedge_report.md").read_text(encoding="utf-8")
    assert "Hedge Execution-Cost Stress" in (tmp_path / "hedge_execution_report.md").read_text(encoding="utf-8")
    assert "Liquidity Share Sizing" in (tmp_path / "liquidity_share_report.md").read_text(encoding="utf-8")
    assert "Position-Level LP Shadow Economics" in (tmp_path / "position_shadow_report.md").read_text(encoding="utf-8")
    assert "Route-Away Break-Even" in (tmp_path / "route_away_break_even.md").read_text(encoding="utf-8")
    assert "Adverse Route-Away Stress" in (tmp_path / "adverse_route_away_report.md").read_text(encoding="utf-8")
    assert "Route-Away Collector Smoke" in (tmp_path / "route_away_collector_smoke.md").read_text(encoding="utf-8")
    assert "Controlled Route-Away Window Plan" in (tmp_path / "route_away_window_plan.md").read_text(encoding="utf-8")
    assert "Route-Away RPC Preflight" in (tmp_path / "route_away_rpc_preflight.md").read_text(encoding="utf-8")
    assert "Controlled Route-Away Readiness" in (tmp_path / "route_away_readiness.md").read_text(encoding="utf-8")
    assert "GUARD Breaker Economics" in (tmp_path / "guard_depeg_report.md").read_text(encoding="utf-8")
    assert "route_away_collector_smoke.json" in (tmp_path / "route_away_readiness.md").read_text(encoding="utf-8")
    assert "route_away_window_plan.json" in (tmp_path / "route_away_readiness.md").read_text(encoding="utf-8")
    assert "route_away_rpc_preflight.json" in (tmp_path / "route_away_readiness.md").read_text(encoding="utf-8")
    assert "A/B Sizing Recommendations" in (tmp_path / "route_away_readiness.md").read_text(encoding="utf-8")
    assert "Route-Share Placebo Stability" in (tmp_path / "route_share_stability_report.md").read_text(encoding="utf-8")
    assert "Route-Away A/A Placebo" in (tmp_path / "route_away_placebo_ab_report.md").read_text(encoding="utf-8")
    assert "Controlled Route-Away Power" in (tmp_path / "route_ab_power_report.md").read_text(encoding="utf-8")
    assert "Controlled Route-Away A/B Sizing" in (tmp_path / "route_ab_sizing_report.md").read_text(encoding="utf-8")
    assert "Depth-Adjusted Route Cost Proxy" in (tmp_path / "route_cost_proxy.md").read_text(encoding="utf-8")
    assert "GUARD Stable Opportunity Audit" in (tmp_path / "stable_opportunity_report.md").read_text(encoding="utf-8")
    assert "Quote Route Readiness" in (tmp_path / "quote_route_readiness.md").read_text(encoding="utf-8")
    assert "Quote Premium Headroom" in (tmp_path / "quote_headroom_report.md").read_text(encoding="utf-8")
    assert "Quote Premium Headroom" in (tmp_path / "quote_headroom_weth_usdt.md").read_text(encoding="utf-8")
    assert "Quote Headroom Stability" in (tmp_path / "quote_headroom_stability_report.md").read_text(encoding="utf-8")
    assert "Quote Headroom Drift" in (tmp_path / "quote_headroom_drift_report.md").read_text(encoding="utf-8")
    assert "Quote Premium Stress" in (tmp_path / "quote_premium_stress.md").read_text(encoding="utf-8")
    assert "Quote Event Headroom" in (tmp_path / "quote_event_headroom_report.md").read_text(encoding="utf-8")
    assert "Quote Provenance Audit" in (tmp_path / "quote_provenance_report.md").read_text(encoding="utf-8")
    assert "Quote-Headroom Route Elasticity" in (tmp_path / "quote_elasticity_report.md").read_text(encoding="utf-8")
    assert "Insurance Reserve Solvency" in (tmp_path / "insurance_reserve_report.md").read_text(encoding="utf-8")
    assert "Premium Allocation Frontier" in (tmp_path / "premium_allocation_report.md").read_text(encoding="utf-8")
    assert "Premium Utilization" in (tmp_path / "premium_utilization_report.md").read_text(encoding="utf-8")
    assert "Charge Attribution" in (tmp_path / "charge_attribution_report.md").read_text(encoding="utf-8")
    assert "Reserve Claim Delay Stress" in (tmp_path / "reserve_delay_report.md").read_text(encoding="utf-8")
    assert "Reserve Lifecycle Churn" in (tmp_path / "reserve_lifecycle_report.md").read_text(encoding="utf-8")
    assert "Reserve Tail Sizing" in (tmp_path / "reserve_tail_report.md").read_text(encoding="utf-8")
    assert "Bootstrap Robustness" in (tmp_path / "bootstrap_report.md").read_text(encoding="utf-8")
    assert "Headline Economic Uncertainty" in (tmp_path / "headline_uncertainty_report.md").read_text(encoding="utf-8")
    assert "Trade-Size Buckets" in (tmp_path / "size_bucket_report.md").read_text(encoding="utf-8")
    assert "Oracle Staleness Buckets" in (tmp_path / "staleness_bucket_report.md").read_text(encoding="utf-8")
    assert "Market-Regime Segments" in (tmp_path / "market_regime_report.md").read_text(encoding="utf-8")
    assert "Signal Quality Stress" in (tmp_path / "signal_quality_stress_report.md").read_text(encoding="utf-8")
    assert "Signal Margin" in (tmp_path / "signal_margin_report.md").read_text(encoding="utf-8")
    assert "Base-Fee Adequacy" in (tmp_path / "base_fee_report.md").read_text(encoding="utf-8")
    assert "Truth Markout Sensitivity" in (tmp_path / "markout_sensitivity_report.md").read_text(encoding="utf-8")
    assert "Target Fee Viability" in (tmp_path / "target_fee_report.md").read_text(encoding="utf-8")
    assert "Capital Path Stress" in (tmp_path / "capital_path_report.md").read_text(encoding="utf-8")
    assert "Risk-Adjusted Return" in (tmp_path / "risk_adjusted_return_report.md").read_text(encoding="utf-8")
    assert "Live Gas Snapshot Economics" in (tmp_path / "live_gas_snapshot_report.md").read_text(encoding="utf-8")
    assert "Control-Plane Cost" in (tmp_path / "control_plane_cost_report.md").read_text(encoding="utf-8")
    assert "PnL Attribution" in (tmp_path / "pnl_attribution_report.md").read_text(encoding="utf-8")
    assert "Capital Survival Runway" in (tmp_path / "capital_survival_report.md").read_text(encoding="utf-8")
    assert "Operator Fixed-Cost Drag" in (tmp_path / "operator_cost_report.md").read_text(encoding="utf-8")
    assert "Pilot Deployability Stress" in (tmp_path / "pilot_deployability_report.md").read_text(encoding="utf-8")
    assert "Range-Width Deployability Stress" in (tmp_path / "range_width_deployability_report.md").read_text(encoding="utf-8")
    assert "Alpha Backtest Sweep" in (tmp_path / "alpha_sweep.md").read_text(encoding="utf-8")
    assert "Target Return Thresholds" in (tmp_path / "target_return_report.md").read_text(encoding="utf-8")
    assert "Small-Capital Decision Matrix" in (tmp_path / "small_capital_decision_report.md").read_text(encoding="utf-8")
    assert "Real Position Replay" in (tmp_path / "real_position_report.md").read_text(encoding="utf-8")
    assert (tmp_path / "real_position_input_template.json").exists()
    assert "Real Position Portfolio Replay" in (tmp_path / "real_position_portfolio_report.md").read_text(encoding="utf-8")
    assert (tmp_path / "real_position_portfolio_input_template.json").exists()
    assert "Route-Away Demand Curve" in (tmp_path / "route_demand_report.md").read_text(encoding="utf-8")
    assert "Order-Splitting Sensitivity" in (tmp_path / "order_split_report.md").read_text(encoding="utf-8")
    assert "Sequential Split Timing Sensitivity" in (tmp_path / "sequential_split_report.md").read_text(encoding="utf-8")
    assert "TVL Dilution And Equilibrium" in (tmp_path / "tvl_dilution_report.md").read_text(encoding="utf-8")
    assert "LP Flow Response" in (tmp_path / "lp_flow_response_report.md").read_text(encoding="utf-8")
    assert "Economic Completion Gates" in (tmp_path / "economic_completion.md").read_text(encoding="utf-8")


def test_capital_model_contains_position_economics() -> None:
    text = capital_markdown()

    assert "## Measured Windows" in text
    assert "## APR Sensitivity" in text
    assert "## Required Turnover" in text
    assert "## Capital Classes" in text
    assert "live shadow" in text
    assert "calibrated calm" in text
    assert "calibrated vol" in text
    assert "daily_volume_per_active_capital" in text


def test_shadow_report_includes_pyth_feed_lag(tmp_path) -> None:
    conn = connect(tmp_path / "shadow.sqlite3")
    conn.execute(
        "INSERT INTO pyth_health (observed_ms, publish_time_ms, lag_ms, price_e18, conf_e2) VALUES (?, ?, ?, ?, ?)",
        (1_700_000_000_000, 1_699_999_998_000, 2_000, "2000000000000000000", 1),
    )
    conn.execute(
        "INSERT INTO pyth_health (observed_ms, publish_time_ms, lag_ms, price_e18, conf_e2) VALUES (?, ?, ?, ?, ?)",
        (1_700_000_001_000, 1_699_999_996_000, 5_000, "2000000000000000000", 1),
    )
    conn.commit()

    emit_reports(conn, tmp_path / "reports")

    summary = (tmp_path / "reports" / "summary.md").read_text(encoding="utf-8")
    assert "Valid truth rows" in summary
    assert "Observed swap span" in summary
    assert "Pyth feed lag p50/p90" in summary
    assert "5.000s" in summary


def test_oracle_health_reports_fallback_economics(tmp_path) -> None:
    conn = connect(tmp_path / "shadow.sqlite3")
    for idx, reason in ((1, ""), (2, "STALE_OR_MISSING")):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime, oracle_staleness_observed_ms,
                fresh_extra_e6, fresh_premium_pips, fresh_fallback_reason,
                lag2_extra_e6, lag2_premium_pips, lag2_fallback_reason,
                lag5_extra_e6, lag5_premium_pips, lag5_fallback_reason,
                created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                1_700_000_000_000 + idx * 1000,
                idx,
                f"0x{idx}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                1_000_000_000,
                1,
                "CALM",
                idx * 1000,
                10_000 if not reason else 0,
                5 if not reason else 0,
                reason,
                8_000,
                4,
                "",
                6_000,
                3,
                "",
                1_700_000_000_000,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (idx, 1, "1000000000000000000", 1, 1, 100_000, 1_700_000_001_000),
        )
    conn.execute(
        "INSERT INTO pyth_health (observed_ms, publish_time_ms, lag_ms, price_e18, conf_e2) VALUES (?, ?, ?, ?, ?)",
        (1, 1, 1_000, "1", 1),
    )
    conn.execute(
        "INSERT INTO pyth_health (observed_ms, publish_time_ms, lag_ms, price_e18, conf_e2) VALUES (?, ?, ?, ?, ?)",
        (2, 2, 5_000, "1", 1),
    )
    conn.commit()
    conn.close()

    report = oracle_health_compute(tmp_path / "shadow.sqlite3")
    text = oracle_health_markdown(report)

    assert report.swaps == 2
    assert report.pyth_health_rows == 2
    assert report.decisions[0].fallback_rows == 1
    assert report.decisions[0].fallback_notional_share == 0.5
    assert "Oracle Health Economics" in text
    assert "STALE_OR_MISSING" in text


def test_oracle_lag_report_compares_lagged_decisions(tmp_path) -> None:
    db = tmp_path / "shadow.sqlite3"
    conn = connect(db)
    for idx, truth_corr in ((1, 1), (2, 0)):
        conn.execute(
            """
            INSERT INTO ledger (
                id, ts_ms, block_number, tx_hash, log_index, pre_mid_e18, post_mid_e18,
                ab_e18, aq_e6, zero_for_one, regime,
                fresh_extra_e6, fresh_premium_pips, fresh_fallback_reason,
                lag2_extra_e6, lag2_premium_pips, lag2_fallback_reason,
                lag5_extra_e6, lag5_premium_pips, lag5_fallback_reason,
                created_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                1_700_000_000_000 + idx,
                idx,
                f"0x{idx}",
                0,
                "2000000000000000000000",
                "2000000000000000000000",
                "1000000000000000000",
                100_000_000,
                1,
                "CALM",
                1_000 if truth_corr else 0,
                10 if truth_corr else 0,
                "",
                1_000,
                10,
                "",
                0,
                0,
                "STALE_OR_MISSING",
                1_700_000_000_000,
            ),
        )
        conn.execute(
            """
            INSERT INTO truth (
                ledger_id, valid, truth_basis_e18, truth_dev_e2, truth_corr, truth_mk_e6, computed_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (idx, 1, "1000000000000000000", 1, truth_corr, 10_000, 1_700_000_001_000),
        )
    conn.commit()
    conn.close()

    report = oracle_lag_compute(db)
    text = oracle_lag_markdown(report)
    rows = {row["label"]: row for row in report["rows"]}

    assert {"fresh", "lag2", "lag5"}.issubset(rows)
    assert rows["lag2"]["wrong_extra_e6"] > rows["fresh"]["wrong_extra_e6"]
    assert rows["lag5"]["fallback_rows"] == 2
    assert "Oracle Lag Stress" in text
