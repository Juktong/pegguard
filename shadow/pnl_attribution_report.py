from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import POLICIES, YEAR_DAYS


@dataclass(frozen=True)
class AttributionRow:
    window: str
    policy: str
    scenario: str
    capital_usdc: float
    turnover_per_day: float
    active_ratio: float
    route_away: float
    base_bps: float
    premium_kept_bps: float
    route_away_haircut_bps: float
    markout_bps: float
    gas_bps: float
    rebalance_drag_apr: float
    base_annual_usdc: float
    premium_kept_annual_usdc: float
    route_away_haircut_annual_usdc: float
    markout_annual_usdc: float
    gas_annual_usdc: float
    rebalance_annual_usdc: float
    annual_net_usdc: float
    net_apr: float
    dominant_drag: str


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    metrics = _selected_metrics(data)
    policies = {policy.name: policy for policy in POLICIES}
    rows: list[AttributionRow] = []
    for item in data.get("gas_adjusted_policies", []):
        window = str(item.get("window", ""))
        policy_name = str(item.get("policy", ""))
        metric = metrics.get(window)
        policy = policies.get(policy_name)
        if metric is None or policy is None:
            continue
        rows.append(_row(metric, item, policy))
    return {
        "source": str(economic_tests_json),
        "model": (
            "annual policy PnL waterfall from measured selected PegGuard economics; "
            "base fees, retained dynamic premium, route-away premium haircut, truth markout, gas, "
            "and rebalance drag are converted to annual dollars using each policy's turnover and active ratio."
        ),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# PnL Attribution",
        "",
        "This report decomposes each gas-adjusted policy return into annualized",
        "economic components. It uses the selected PegGuard benchmark per window",
        "and the same route-away, gas, active-ratio, and rebalance assumptions as",
        "`economic_tests.json`.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Policy | Scenario | Capital | Base | Premium kept | Route-away haircut | Markout | Gas | Rebalance | Annual net | Net APR | Dominant drag |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['scenario']} | ${float(row['capital_usdc']):,.0f} | "
            f"{_usd_float(float(row['base_annual_usdc']))} | {_usd_float(float(row['premium_kept_annual_usdc']))} | "
            f"{_usd_float(float(row['route_away_haircut_annual_usdc']))} | {_usd_float(float(row['markout_annual_usdc']))} | "
            f"{_usd_float(float(row['gas_annual_usdc']))} | {_usd_float(float(row['rebalance_annual_usdc']))} | "
            f"{_usd_float(float(row['annual_net_usdc']))} | {float(row['net_apr']):.2%} | {row['dominant_drag']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Premium kept` is dynamic premium after the configured route-away haircut.",
            "- `Route-away haircut` is the premium assumed lost because some charged flow routes away.",
            "- `Markout` uses truth-denominated markout and is negative when toxic-flow cost exceeds any beneficial markout.",
            "- `Dominant drag` names the largest negative annual component for that policy row.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(metric: dict, item: dict, policy) -> AttributionRow:
    notional = int(metric.get("notional_e6", 0))
    route_away = float(item.get("route_away", 0))
    base_bps = _bps(int(metric.get("base_fee_e6", 0)), notional)
    premium_bps = _bps(int(metric.get("extra_e6", 0)), notional)
    premium_kept_bps = premium_bps * (1 - route_away)
    route_away_haircut_bps = -premium_bps * route_away
    markout_bps = -_bps(int(metric.get("markout_e6", 0)), notional)
    gas_bps = -float(item.get("gas_bps", 0))
    rebalance_drag_apr = (float(policy.rebalance_cost_bps) / 10_000) * int(policy.rebalances_per_year)

    capital = float(item.get("capital_usdc", 0))
    turnover = float(item.get("turnover_per_day", 0))
    active_ratio = float(policy.active_ratio)
    base_annual = _annual_component(capital, base_bps, turnover, active_ratio)
    premium_kept_annual = _annual_component(capital, premium_kept_bps, turnover, active_ratio)
    route_away_annual = _annual_component(capital, route_away_haircut_bps, turnover, active_ratio)
    markout_annual = _annual_component(capital, markout_bps, turnover, active_ratio)
    gas_annual = _annual_component(capital, gas_bps, turnover, active_ratio)
    rebalance_annual = -capital * rebalance_drag_apr
    annual_net = base_annual + premium_kept_annual + route_away_annual + markout_annual + gas_annual + rebalance_annual

    drags = {
        "route-away haircut": route_away_annual,
        "markout": markout_annual,
        "gas": gas_annual,
        "rebalance": rebalance_annual,
    }
    dominant_drag = min(drags, key=lambda key: drags[key])
    return AttributionRow(
        window=str(item.get("window", "")),
        policy=str(item.get("policy", "")),
        scenario=str(item.get("scenario", "")),
        capital_usdc=capital,
        turnover_per_day=turnover,
        active_ratio=active_ratio,
        route_away=route_away,
        base_bps=base_bps,
        premium_kept_bps=premium_kept_bps,
        route_away_haircut_bps=route_away_haircut_bps,
        markout_bps=markout_bps,
        gas_bps=gas_bps,
        rebalance_drag_apr=rebalance_drag_apr,
        base_annual_usdc=base_annual,
        premium_kept_annual_usdc=premium_kept_annual,
        route_away_haircut_annual_usdc=route_away_annual,
        markout_annual_usdc=markout_annual,
        gas_annual_usdc=gas_annual,
        rebalance_annual_usdc=rebalance_annual,
        annual_net_usdc=annual_net,
        net_apr=annual_net / capital if capital else 0.0,
        dominant_drag=dominant_drag,
    )


def _selected_metrics(data: dict) -> dict[str, dict]:
    metrics = {}
    for metric in data.get("benchmarks", []):
        if str(metric.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}:
            metrics[str(metric.get("window", ""))] = metric
    return metrics


def _annual_component(capital_usdc: float, bps: float, turnover_per_day: float, active_ratio: float) -> float:
    return capital_usdc * (bps / 10_000) * turnover_per_day * active_ratio * YEAR_DAYS


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 <= 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Generate annualized policy PnL attribution from measured PegGuard economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "pnl_attribution_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"pnl attribution rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
