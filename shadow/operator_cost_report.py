from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class OpsScenario:
    name: str
    monthly_infra_usdc: float
    hours_per_week: float
    hourly_rate_usdc: float
    note: str


OPS_SCENARIOS = (
    OpsScenario("free operator", 0.0, 0.0, 0.0, "no fixed operator or infra cost"),
    OpsScenario("hobby infra", 20.0, 0.25, 0.0, "basic RPC/monitoring infra with unpaid operator time"),
    OpsScenario("paid light ops", 20.0, 0.5, 50.0, "light weekly review priced at a modest operator rate"),
    OpsScenario("active manager", 50.0, 2.0, 75.0, "hands-on management, alerts, and periodic execution"),
)


@dataclass(frozen=True)
class OperatorCostRow:
    window: str
    policy: str
    scenario: str
    ops_scenario: str
    capital_usdc: float
    annual_net_before_ops_usdc: float
    net_apr_before_ops: float
    annual_ops_cost_usdc: float
    infra_cost_usdc: float
    labor_cost_usdc: float
    annual_net_after_ops_usdc: float
    net_apr_after_ops: float
    break_even_capital_usdc: float | None
    capital_multiple_to_break_even: float | None
    status: str
    note: str


def compute(pnl_attribution_json: Path, ops_scenarios: tuple[OpsScenario, ...] = OPS_SCENARIOS) -> dict:
    data = _load_json(pnl_attribution_json)
    rows = [
        _row(source, ops)
        for source in data.get("rows", [])
        for ops in ops_scenarios
    ]
    return {
        "source": str(pnl_attribution_json),
        "model": (
            "fixed operator-cost overlay on PnL attribution. Gas and rebalance drag are already in the source rows; "
            "this report adds recurring infra and labor overhead to show when small capital is too small to operate economically."
        ),
        "ops_scenarios": [asdict(scenario) for scenario in ops_scenarios],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Operator Fixed-Cost Drag",
        "",
        "This report applies fixed operator and infrastructure costs on top of the",
        "existing PnL attribution rows. It is aimed at small-capital deployment",
        "decisions, where a few hours of operation can overwhelm hook edge.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Policy | Scenario | Ops | Capital | Before ops | Ops cost | After ops | After-ops APR | Break-even capital | Status |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['scenario']} | {row['ops_scenario']} | "
            f"{_usd_float(float(row['capital_usdc']))} | {_usd_float(float(row['annual_net_before_ops_usdc']))} | "
            f"{_usd_float(float(row['annual_ops_cost_usdc']))} | {_usd_float(float(row['annual_net_after_ops_usdc']))} | "
            f"{float(row['net_apr_after_ops']):.2%} | {_usd_or_na(row.get('break_even_capital_usdc'))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `free operator` is the pure modeled-economic result with no fixed human/infra overhead.",
            "- `hobby infra` prices recurring infrastructure but treats operator time as unpaid.",
            "- `paid light ops` and `active manager` are sanity checks for whether the capital base justifies active management.",
            "- `break-even capital` assumes the same measured before-ops APR scales linearly with capital and asks how much capital is needed to cover fixed ops cost.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(source: dict, ops: OpsScenario) -> OperatorCostRow:
    capital = float(source.get("capital_usdc", 0))
    before = float(source.get("annual_net_usdc", 0))
    before_apr = float(source.get("net_apr", 0))
    infra = ops.monthly_infra_usdc * 12
    labor = ops.hours_per_week * ops.hourly_rate_usdc * 52
    ops_cost = infra + labor
    after = before - ops_cost
    break_even = (ops_cost / before_apr) if before_apr > 0 and ops_cost > 0 else (0.0 if ops_cost == 0 else None)
    multiple = (break_even / capital) if break_even is not None and capital > 0 else None
    return OperatorCostRow(
        window=str(source.get("window", "")),
        policy=str(source.get("policy", "")),
        scenario=str(source.get("scenario", "")),
        ops_scenario=ops.name,
        capital_usdc=capital,
        annual_net_before_ops_usdc=before,
        net_apr_before_ops=before_apr,
        annual_ops_cost_usdc=ops_cost,
        infra_cost_usdc=infra,
        labor_cost_usdc=labor,
        annual_net_after_ops_usdc=after,
        net_apr_after_ops=(after / capital) if capital else 0.0,
        break_even_capital_usdc=break_even,
        capital_multiple_to_break_even=multiple,
        status=_status(after, capital),
        note=ops.note,
    )


def _status(after_ops_usdc: float, capital_usdc: float) -> str:
    if capital_usdc <= 0:
        return "no capital"
    apr = after_ops_usdc / capital_usdc
    if apr >= 0.10:
        return "viable >=10% APR"
    if after_ops_usdc >= 0:
        return "positive but subscale"
    return "negative after ops"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return _usd_float(float(value))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate fixed operator-cost drag report")
    parser.add_argument("--pnl-attribution-json", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "operator_cost_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "operator_cost_report.json")
    args = parser.parse_args()
    report = compute(args.pnl_attribution_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"operator cost rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
