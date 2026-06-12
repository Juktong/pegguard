from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .hedge_report import compute as compute_hedge_report


@dataclass(frozen=True)
class ExecutionScenario:
    name: str
    execution_cost_bps: float
    funding_apr: float
    max_rebalances_per_window: int
    note: str


@dataclass(frozen=True)
class HedgeExecutionRow:
    window: str
    range_policy: str
    hedge_policy: str
    scenario: str
    duration_days: float
    rebalances: int
    max_rebalances_per_window: int
    hedge_turnover_e6: int
    average_hedge_notional_e6: int
    execution_cost_e6: int
    funding_cost_e6: int
    total_hedge_cost_e6: int
    hedge_pnl_e6: int
    unhedged_inventory_il_e6: int
    hedged_net_e6: int
    hedge_improvement_e6: int
    adjusted_max_drawdown_e6: int
    status: str


SCENARIOS = (
    ExecutionScenario(
        "low-cost perp",
        1.0,
        0.05,
        5_000,
        "liquid venue, modest execution cost and conservative positive funding/borrow drag",
    ),
    ExecutionScenario(
        "stressed funding",
        3.0,
        0.25,
        5_000,
        "same hedge path with wider execution and high annualized carry cost",
    ),
    ExecutionScenario(
        "thin hedge venue",
        8.0,
        0.50,
        250,
        "thin or manual hedge venue; every-event rebalancing is treated as operationally infeasible",
    ),
)


def compute(
    root: Path,
    capital_e6: int = 10_000_000_000,
    scenarios: tuple[ExecutionScenario, ...] = SCENARIOS,
) -> dict:
    base_report = compute_hedge_report(root, capital_e6)
    rows = base_report.get("rows", [])
    open_notional = _open_notional_by_range(rows)
    durations = {
        "calm": _fixture_duration_days(root / "test" / "fixtures" / "calm_0530.json"),
        "vol": _fixture_duration_days(root / "test" / "fixtures" / "vol_0523_hot90m.json"),
    }
    overlay_rows: list[HedgeExecutionRow] = []
    for row in rows:
        window = str(row.get("window", ""))
        duration_days = durations.get(window, 0.0)
        initial = open_notional.get((window, str(row.get("range_policy", ""))), int(row.get("hedge_turnover_e6", 0)))
        for scenario in scenarios:
            overlay_rows.append(_row(row, scenario, duration_days, initial))
    return {
        "capital_e6": int(base_report.get("capital_e6", capital_e6)),
        "model": (
            "hedge execution overlay on the fixture LP inventory hedge paths. It replaces the base "
            "1 bps hedge cost with scenario execution cost, adds funding/borrow carry on average hedge "
            "notional, and flags operationally unrealistic rebalance counts."
        ),
        "scenarios": [asdict(scenario) for scenario in scenarios],
        "rows": [asdict(row) for row in overlay_rows],
    }


def markdown(report: dict) -> str:
    rows = report.get("rows", [])
    improving = sum(1 for row in rows if row.get("status") == "improves after costs")
    infeasible = sum(1 for row in rows if row.get("status") == "operationally infeasible")
    worst = min((int(row.get("hedge_improvement_e6", 0)) for row in rows), default=0)
    best = max((int(row.get("hedge_improvement_e6", 0)) for row in rows), default=0)
    lines = [
        "# Hedge Execution-Cost Stress",
        "",
        "This report overlays funding, borrow/carry, and venue execution costs on",
        "the fixture LP inventory hedge paths. It is an operational stress test,",
        "not calibration and not a claim that the hedge venue has enough depth.",
        "",
        f"- Position capital: {_usd(int(report.get('capital_e6', 0)))}",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Rows: {len(rows)}; improving rows: {improving}; infeasible rows: {infeasible}; improvement range {_usd(worst)} to {_usd(best)}",
        "",
        "## Scenarios",
        "",
        "| Scenario | Execution cost | Funding APR | Max rebalances/window | Note |",
        "|---|---:|---:|---:|---|",
    ]
    for scenario in report.get("scenarios", []):
        lines.append(
            f"| {scenario['name']} | {float(scenario['execution_cost_bps']):.2f} bps | "
            f"{_pct(float(scenario['funding_apr']))} | {int(scenario['max_rebalances_per_window'])} | "
            f"{scenario['note']} |"
        )
    lines.extend(
        [
            "",
            "## Grid",
            "",
            "| Window | Range | Hedge | Scenario | Rebalances | Avg hedge notional | Exec cost | Funding cost | Hedge PnL | Unhedged IL | Hedged net | Improvement | Max drawdown | Status |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['window']} | {row['range_policy']} | {row['hedge_policy']} | {row['scenario']} | "
            f"{int(row['rebalances'])} | {_usd(int(row['average_hedge_notional_e6']))} | "
            f"{_usd(int(row['execution_cost_e6']))} | {_usd(int(row['funding_cost_e6']))} | "
            f"{_usd(int(row['hedge_pnl_e6']))} | {_usd(int(row['unhedged_inventory_il_e6']))} | "
            f"{_usd(int(row['hedged_net_e6']))} | {_usd(int(row['hedge_improvement_e6']))} | "
            f"{_usd(int(row['adjusted_max_drawdown_e6']))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Funding is modeled as a cost on average hedge notional over the fixture duration.",
            "- Average hedge notional is approximated from the starting open hedge and rebalance turnover; it is a conservative operational overlay, not a per-block funding ledger.",
            "- `operationally infeasible` means the hedge path required more rebalances than the scenario allows, even if its terminal PnL looks acceptable.",
            "- Volatile-window rows show whether hedging reduces inventory risk after realistic costs; they do not include route-away or dynamic-fee revenue.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(row: dict, scenario: ExecutionScenario, duration_days: float, initial_notional_e6: int) -> HedgeExecutionRow:
    rebalances = int(row.get("rebalances", 0))
    hedge_turnover = int(row.get("hedge_turnover_e6", 0))
    average_notional = max(initial_notional_e6, int(round(hedge_turnover / max(rebalances + 1, 1))))
    execution_cost = int(round(hedge_turnover * scenario.execution_cost_bps / 10_000))
    funding_cost = int(round(average_notional * scenario.funding_apr * duration_days / 365))
    total_cost = execution_cost + funding_cost
    hedge_pnl = int(row.get("hedge_pnl_e6", 0))
    unhedged_il = int(row.get("unhedged_inventory_il_e6", 0))
    hedged_net = unhedged_il + hedge_pnl - total_cost
    improvement = hedged_net - unhedged_il
    base_cost = int(row.get("hedge_cost_e6", 0))
    adjusted_drawdown = int(row.get("max_hedged_drawdown_e6", 0)) - max(total_cost - base_cost, 0)
    infeasible = rebalances > scenario.max_rebalances_per_window
    if infeasible:
        status = "operationally infeasible"
    elif improvement > 0:
        status = "improves after costs"
    else:
        status = "worse than unhedged"
    return HedgeExecutionRow(
        window=str(row.get("window", "")),
        range_policy=str(row.get("range_policy", "")),
        hedge_policy=str(row.get("hedge_policy", "")),
        scenario=scenario.name,
        duration_days=duration_days,
        rebalances=rebalances,
        max_rebalances_per_window=scenario.max_rebalances_per_window,
        hedge_turnover_e6=hedge_turnover,
        average_hedge_notional_e6=average_notional,
        execution_cost_e6=execution_cost,
        funding_cost_e6=funding_cost,
        total_hedge_cost_e6=total_cost,
        hedge_pnl_e6=hedge_pnl,
        unhedged_inventory_il_e6=unhedged_il,
        hedged_net_e6=hedged_net,
        hedge_improvement_e6=improvement,
        adjusted_max_drawdown_e6=adjusted_drawdown,
        status=status,
    )


def _open_notional_by_range(rows: list[dict]) -> dict[tuple[str, str], int]:
    result: dict[tuple[str, str], int] = {}
    for row in rows:
        if row.get("hedge_policy") == "open only":
            result[(str(row.get("window", "")), str(row.get("range_policy", "")))] = int(row.get("hedge_turnover_e6", 0))
    return result


def _fixture_duration_days(path: Path) -> float:
    if not path.exists():
        return 0.0
    rows = json.loads(path.read_text(encoding="utf-8"))
    if len(rows) < 2:
        return 0.0
    return max((int(rows[-1]["t_ms"]) - int(rows[0]["t_ms"])) / 86_400_000, 1 / 86_400)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Overlay funding and execution costs on fixture hedge paths")
    parser.add_argument("--capital-e6", type=int, default=10_000_000_000)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "hedge_execution_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "hedge_execution_report.json")
    args = parser.parse_args()
    report = compute(root, args.capital_e6)
    write_outputs(report, args.out_md, args.out_json)
    print(f"hedge execution rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
