from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import YEAR_DAYS


ROUTE_AWAY = 0.25
MARKOUT_MULTIPLIERS = (1.0, 1.5, 2.0)
TARGET_APR = 0.10
SCENARIOS = ("hook + Pyth, low L2", "hook + Pyth, stressed L2")


@dataclass(frozen=True)
class RangeProfile:
    name: str
    half_width_bps: int
    reference_capital_usdc: float
    turnover_per_day: float
    active_ratio: float
    rebalances_per_year: int
    rebalance_cost_bps: float
    note: str


@dataclass(frozen=True)
class RangeWidthRow:
    window: str
    profile: str
    scenario: str
    markout_multiplier: float
    half_width_bps: int
    reference_capital_usdc: float
    turnover_per_day: float
    active_ratio: float
    rebalances_per_year: int
    rebalance_cost_bps: float
    base_bps: float
    premium_kept_bps: float
    route_away_haircut_bps: float
    markout_bps: float
    gas_bps: float
    net_bps_before_rebalance: float
    rebalance_drag_apr: float
    annual_net_usdc: float
    net_apr: float
    required_turnover_for_10pct: float | None
    implied_capacity_for_10pct_usdc: float | None
    current_turnover_sufficient: bool
    status: str


RANGE_PROFILES = (
    RangeProfile(
        "ultra tight +/-0.5%",
        50,
        10_000,
        7.0,
        0.55,
        365,
        2.5,
        "high fee density, high out-of-range and rebalance burden",
    ),
    RangeProfile(
        "tight +/-1%",
        100,
        10_000,
        5.0,
        0.70,
        156,
        2.0,
        "active manager range with frequent recentering",
    ),
    RangeProfile(
        "pilot +/-2%",
        200,
        10_000,
        3.0,
        0.80,
        52,
        2.0,
        "small-capital pilot range with weekly rebalance budget",
    ),
    RangeProfile(
        "wide +/-5%",
        500,
        10_000,
        1.5,
        0.90,
        24,
        1.0,
        "lower maintenance range with weaker fee density",
    ),
    RangeProfile(
        "passive +/-10%",
        1000,
        10_000,
        0.75,
        0.95,
        12,
        0.8,
        "passive reference; mostly tests whether width dilutes the edge",
    ),
)


def compute(
    root: Path,
    economic_tests_json: Path,
    live_status_json: Path | None = None,
    profiles: tuple[RangeProfile, ...] = RANGE_PROFILES,
    markout_multipliers: tuple[float, ...] = MARKOUT_MULTIPLIERS,
) -> dict:
    data = _load_json(economic_tests_json)
    live_status = _load_json(live_status_json) if live_status_json is not None else {}
    metrics = _selected_metrics(data)
    gas_bps = _gas_bps(data)
    daily_notional = _daily_notional(root, metrics, live_status)
    rows: list[RangeWidthRow] = []
    for window, metric in metrics.items():
        for scenario in SCENARIOS:
            window_gas_bps = gas_bps.get((window, scenario))
            if window_gas_bps is None:
                continue
            for profile in profiles:
                for multiplier in markout_multipliers:
                    rows.append(_row(metric, scenario, window_gas_bps, profile, multiplier, daily_notional.get(window)))
    return {
        "source": str(economic_tests_json),
        "live_status_source": str(live_status_json) if live_status_json is not None else None,
        "route_away": ROUTE_AWAY,
        "target_apr": TARGET_APR,
        "profiles": [asdict(profile) for profile in profiles],
        "model": (
            "range-width deployability grid. It applies measured PegGuard base, dynamic premium, "
            "truth markout, route-away haircut, and gas to fixed operating assumptions for range width, "
            "active ratio, turnover, and rebalance cost. This is an operations stress, not calibration."
        ),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    rows = report.get("rows", [])
    viable = sum(1 for row in rows if row.get("status") == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and row.get("status") == "viable >=10% APR"
    )
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    best_apr = max((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    lines = [
        "# Range-Width Deployability Stress",
        "",
        "This report answers whether small-capital range choices still work after",
        "measured truth markout, route-away haircut, gas, active-ratio dilution,",
        "and rebalance drag. It is an operations stress, not calibration.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Live status source: `{report.get('live_status_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Route-away haircut: {_pct(float(report.get('route_away', ROUTE_AWAY)))}",
        f"- Target APR: {_pct(float(report.get('target_apr', TARGET_APR)))}",
        f"- Rows: {len(rows)}; viable rows: {viable}; 2x-markout viable rows: {stress_viable}; APR range {_pct(min_apr)} to {_pct(best_apr)}",
        "",
        "## Operating Profiles",
        "",
        "| Profile | Half-width | Capital | Turnover | Active ratio | Rebalances/year | Rebalance cost | Note |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for profile in report.get("profiles", []):
        lines.append(
            f"| {profile['name']} | {int(profile['half_width_bps']) / 100:.2f}% | "
            f"{_usd_float(float(profile['reference_capital_usdc']))} | "
            f"{float(profile['turnover_per_day']):.2f}x/day | {_pct(float(profile['active_ratio']))} | "
            f"{int(profile['rebalances_per_year'])} | {float(profile['rebalance_cost_bps']):.2f} bps | "
            f"{profile['note']} |"
        )
    lines.extend(
        [
            "",
            "## Grid",
            "",
            "| Window | Profile | Scenario | Markout x | Net bps before rebalance | Rebalance drag | Annual net | APR | Req turnover for 10% | Capacity at 10% | Status |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['window']} | {row['profile']} | {row['scenario']} | "
            f"{float(row['markout_multiplier']):.2f}x | {float(row['net_bps_before_rebalance']):.2f} bps | "
            f"{_pct(float(row['rebalance_drag_apr']))} | {_usd_float(float(row['annual_net_usdc']))} | "
            f"{_pct(float(row['net_apr']))} | {_turnover(row.get('required_turnover_for_10pct'))} | "
            f"{_usd_or_na(row.get('implied_capacity_for_10pct_usdc'))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Width is represented by operating assumptions, not by changing hook constants.",
            "- `Capacity at 10%` uses observed daily notional times the active ratio divided by required active turnover.",
            "- `2x-markout` rows are the conservative check: they fail when the strategy only works if truth markout was understated.",
            "- Live-shadow rows are measured same-swaps evidence and still do not measure real route-away.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(
    metric: dict,
    scenario: str,
    gas_bps: float,
    profile: RangeProfile,
    markout_multiplier: float,
    observed_daily_notional_usdc: float | None,
) -> RangeWidthRow:
    notional = int(metric.get("notional_e6", 0))
    capital = profile.reference_capital_usdc
    base_bps = _bps(int(metric.get("base_fee_e6", 0)), notional)
    premium_bps = _bps(int(metric.get("extra_e6", 0)), notional)
    premium_kept_bps = premium_bps * (1 - ROUTE_AWAY)
    route_away_haircut_bps = -premium_bps * ROUTE_AWAY
    markout_bps = -_bps(int(metric.get("markout_e6", 0)), notional) * markout_multiplier
    net_bps_before_rebalance = base_bps + premium_kept_bps + markout_bps - gas_bps
    rebalance_drag_apr = (profile.rebalance_cost_bps / 10_000) * profile.rebalances_per_year
    gross_apr = (net_bps_before_rebalance / 10_000) * profile.turnover_per_day * profile.active_ratio * YEAR_DAYS
    net_apr = gross_apr - rebalance_drag_apr
    annual_net = capital * net_apr
    required_turnover = _required_turnover(net_bps_before_rebalance, profile.active_ratio, rebalance_drag_apr, TARGET_APR)
    capacity = None
    if required_turnover is not None and observed_daily_notional_usdc is not None:
        capacity = (observed_daily_notional_usdc * profile.active_ratio) / required_turnover
    return RangeWidthRow(
        window=str(metric.get("window", "")),
        profile=profile.name,
        scenario=scenario,
        markout_multiplier=markout_multiplier,
        half_width_bps=profile.half_width_bps,
        reference_capital_usdc=capital,
        turnover_per_day=profile.turnover_per_day,
        active_ratio=profile.active_ratio,
        rebalances_per_year=profile.rebalances_per_year,
        rebalance_cost_bps=profile.rebalance_cost_bps,
        base_bps=base_bps,
        premium_kept_bps=premium_kept_bps,
        route_away_haircut_bps=route_away_haircut_bps,
        markout_bps=markout_bps,
        gas_bps=gas_bps,
        net_bps_before_rebalance=net_bps_before_rebalance,
        rebalance_drag_apr=rebalance_drag_apr,
        annual_net_usdc=annual_net,
        net_apr=net_apr,
        required_turnover_for_10pct=required_turnover,
        implied_capacity_for_10pct_usdc=capacity,
        current_turnover_sufficient=required_turnover is not None and profile.turnover_per_day >= required_turnover,
        status=_status(net_apr),
    )


def _required_turnover(
    net_bps_before_rebalance: float,
    active_ratio: float,
    rebalance_drag_apr: float,
    target_apr: float,
) -> float | None:
    apr_per_turnover = (net_bps_before_rebalance / 10_000) * active_ratio * YEAR_DAYS
    if apr_per_turnover <= 0:
        return None
    return (target_apr + rebalance_drag_apr) / apr_per_turnover


def _selected_metrics(data: dict) -> dict[str, dict]:
    metrics = {}
    for metric in data.get("benchmarks", []):
        if str(metric.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}:
            metrics[str(metric.get("window", ""))] = metric
    return metrics


def _gas_bps(data: dict) -> dict[tuple[str, str], float]:
    return {
        (str(row.get("window", "")), str(row.get("scenario", ""))): float(row.get("gas_bps", 0))
        for row in data.get("gas_sensitivity", [])
    }


def _daily_notional(root: Path, metrics: dict[str, dict], live_status: dict) -> dict[str, float]:
    result: dict[str, float] = {}
    for window in ("calm", "vol"):
        metric = metrics.get(window)
        if metric is None:
            continue
        duration_days = _fixture_duration_days(root, window)
        if duration_days is not None and duration_days > 0:
            result[window] = (int(metric.get("notional_e6", 0)) / 1_000_000) / duration_days
    live_metric = metrics.get("live shadow")
    live_hours = float(live_status.get("observed_span_hours", 0))
    if live_metric is not None and live_hours > 0:
        result["live shadow"] = (int(live_metric.get("notional_e6", 0)) / 1_000_000) / (live_hours / 24)
    return result


def _fixture_duration_days(root: Path, window: str) -> float | None:
    path = {
        "calm": root / "test" / "fixtures" / "calm_0530.json",
        "vol": root / "test" / "fixtures" / "vol_0523_hot90m.json",
    }.get(window)
    if path is None or not path.exists():
        return None
    rows = json.loads(path.read_text(encoding="utf-8"))
    if len(rows) < 2:
        return None
    start = int(rows[0]["t_ms"])
    end = int(rows[-1]["t_ms"])
    return max((end - start) / 86_400_000, 1 / 86_400)


def _status(net_apr: float) -> str:
    if net_apr >= TARGET_APR:
        return "viable >=10% APR"
    if net_apr >= 0:
        return "positive but subscale"
    return "negative"


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 <= 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _load_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _turnover(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x/day"


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return _usd_float(float(value))


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Generate range-width deployability stress report")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "range_width_deployability_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "range_width_deployability_report.json")
    args = parser.parse_args()
    report = compute(root, args.economic_tests_json, args.live_status_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"range-width deployability rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
