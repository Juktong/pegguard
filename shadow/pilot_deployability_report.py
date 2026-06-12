from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .operator_cost_report import OPS_SCENARIOS, OpsScenario


MARKOUT_MULTIPLIERS = (1.0, 1.5, 2.0)
TARGET_APR = 0.10


@dataclass(frozen=True)
class DeployabilityRow:
    window: str
    policy: str
    scenario: str
    ops_scenario: str
    markout_multiplier: float
    capital_usdc: float
    turnover_per_day: float
    active_ratio: float
    annual_ops_cost_usdc: float
    annual_net_usdc: float
    net_apr: float
    required_turnover_for_10pct: float | None
    required_daily_volume_for_10pct_usdc: float | None
    status: str


def compute(
    pnl_attribution_json: Path,
    multipliers: tuple[float, ...] = MARKOUT_MULTIPLIERS,
    ops_scenarios: tuple[OpsScenario, ...] = OPS_SCENARIOS,
) -> dict:
    data = _load_json(pnl_attribution_json)
    rows = [
        _row(source, ops, multiplier)
        for source in data.get("rows", [])
        for ops in ops_scenarios
        for multiplier in multipliers
    ]
    return {
        "source": str(pnl_attribution_json),
        "target_apr": TARGET_APR,
        "markout_multipliers": list(multipliers),
        "model": (
            "small-capital deployability scoreboard. It reuses the measured PnL attribution, "
            "adds fixed operator costs, and rescales truth markout to test whether a policy remains "
            "viable if markout was understated."
        ),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    rows = report.get("rows", [])
    viable = sum(1 for row in rows if str(row.get("status", "")) == "viable >=10% APR")
    stress_viable = sum(
        1
        for row in rows
        if float(row.get("markout_multiplier", 0)) >= 2.0 and str(row.get("status", "")) == "viable >=10% APR"
    )
    min_apr = min((float(row.get("net_apr", 0)) for row in rows), default=0.0)
    lines = [
        "# Pilot Deployability Stress",
        "",
        "This report turns measured PegGuard economics into an operations-level",
        "small-capital go/no-go table. It combines PnL attribution, fixed operator",
        "costs, and truth-markout understatement stress. It is not calibration.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Target APR: {_pct(float(report.get('target_apr', TARGET_APR)))}",
        f"- Rows: {len(rows)}; viable rows: {viable}; 2x-markout viable rows: {stress_viable}; worst APR: {_pct(min_apr)}",
        "",
        "| Window | Policy | Scenario | Ops | Markout x | Capital | Current turnover | Net | APR | Required turnover for 10% | Required daily volume | Status |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['scenario']} | {row['ops_scenario']} | "
            f"{float(row['markout_multiplier']):.2f}x | {_usd_float(float(row['capital_usdc']))} | "
            f"{float(row['turnover_per_day']):.1f}x/day | {_usd_float(float(row['annual_net_usdc']))} | "
            f"{_pct(float(row['net_apr']))} | {_turnover(row.get('required_turnover_for_10pct'))} | "
            f"{_usd_or_na(row.get('required_daily_volume_for_10pct_usdc'))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `markout x` scales only truth markout; base fee, dynamic premium, route-away haircut, gas, and rebalances stay fixed.",
            "- `required turnover` is the active daily volume/capital needed to clear a 10% APR after operator cost.",
            "- `negative after ops` means the measured edge is not enough for deployment at that capital and operating model.",
            "- Rows using the live-shadow window are measured same-swaps evidence and still do not measure real route-away.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(source: dict, ops: OpsScenario, multiplier: float) -> DeployabilityRow:
    capital = float(source.get("capital_usdc", 0))
    turnover = float(source.get("turnover_per_day", 0))
    active_ratio = float(source.get("active_ratio", 0))
    infra = ops.monthly_infra_usdc * 12
    labor = ops.hours_per_week * ops.hourly_rate_usdc * 52
    ops_cost = infra + labor

    variable_current = (
        float(source.get("base_annual_usdc", 0))
        + float(source.get("premium_kept_annual_usdc", 0))
        + float(source.get("route_away_haircut_annual_usdc", 0))
        + float(source.get("gas_annual_usdc", 0))
        + float(source.get("markout_annual_usdc", 0)) * multiplier
    )
    rebalance = float(source.get("rebalance_annual_usdc", 0))
    annual_net = variable_current + rebalance - ops_cost
    required_turnover = _required_turnover(
        variable_current,
        turnover,
        capital,
        rebalance,
        ops_cost,
        TARGET_APR,
    )
    required_daily_volume = (required_turnover * capital) if required_turnover is not None else None
    return DeployabilityRow(
        window=str(source.get("window", "")),
        policy=str(source.get("policy", "")),
        scenario=str(source.get("scenario", "")),
        ops_scenario=ops.name,
        markout_multiplier=multiplier,
        capital_usdc=capital,
        turnover_per_day=turnover,
        active_ratio=active_ratio,
        annual_ops_cost_usdc=ops_cost,
        annual_net_usdc=annual_net,
        net_apr=(annual_net / capital) if capital else 0.0,
        required_turnover_for_10pct=required_turnover,
        required_daily_volume_for_10pct_usdc=required_daily_volume,
        status=_status(annual_net, capital),
    )


def _required_turnover(
    variable_current_usdc: float,
    current_turnover: float,
    capital_usdc: float,
    rebalance_usdc: float,
    ops_cost_usdc: float,
    target_apr: float,
) -> float | None:
    if current_turnover <= 0 or capital_usdc <= 0:
        return None
    variable_per_turnover = variable_current_usdc / current_turnover
    if variable_per_turnover <= 0:
        return None
    target_net = target_apr * capital_usdc
    return (target_net - rebalance_usdc + ops_cost_usdc) / variable_per_turnover


def _status(annual_net_usdc: float, capital_usdc: float) -> str:
    if capital_usdc <= 0:
        return "no capital"
    apr = annual_net_usdc / capital_usdc
    if apr >= TARGET_APR:
        return "viable >=10% APR"
    if annual_net_usdc >= 0:
        return "positive but subscale"
    return "negative after ops"


def _load_json(path: Path) -> dict:
    if not path.exists():
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
    parser = argparse.ArgumentParser(description="Generate small-capital pilot deployability stress report")
    parser.add_argument("--pnl-attribution-json", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "pilot_deployability_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "pilot_deployability_report.json")
    args = parser.parse_args()
    report = compute(args.pnl_attribution_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"pilot deployability rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
