from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import YEAR_DAYS
from .policy_monte_carlo_report import MIXES


LOSS_THRESHOLDS = (0.01, 0.05, 0.10, 0.25, 1.00)


@dataclass(frozen=True)
class SurvivalRow:
    label: str
    kind: str
    policy: str
    scenario: str
    capital_usdc: float
    annual_income_usdc: float
    annual_drag_usdc: float
    annual_net_usdc: float
    net_apr: float
    daily_income_usdc: float
    daily_drag_usdc: float
    daily_net_usdc: float
    drag_coverage: float | None
    days_to_1pct_loss: float | None
    days_to_5pct_loss: float | None
    days_to_10pct_loss: float | None
    days_to_25pct_loss: float | None
    days_to_depletion: float | None
    dominant_drag: str
    status: str


def compute(pnl_attribution_json: Path) -> dict:
    data = _load_json(pnl_attribution_json)
    rows = [_from_components(row, str(row.get("window", "")), "window") for row in data.get("rows", [])]
    rows.extend(_mix_rows(data.get("rows", [])))
    return {
        "source": str(pnl_attribution_json),
        "model": (
            "linear small-capital runway from PnL attribution components; income is base fee plus kept premium, "
            "drag is route-away haircut plus markout plus gas plus rebalance. Loss-day estimates use constant "
            "daily burn and do not model compounding, withdrawals, or route-away feedback."
        ),
        "loss_thresholds": list(LOSS_THRESHOLDS),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Capital Survival Runway",
        "",
        "This report converts the PnL attribution waterfall into a small-capital",
        "runway table. It asks how long each policy can absorb the measured drag",
        "before losing fixed percentages of starting capital.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "## Window Runway",
        "",
        "| Window | Policy | Scenario | Capital | Income/day | Drag/day | Net/day | Net APR | Drag coverage | 10% runway | Depletion | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        if row.get("kind") != "window":
            continue
        lines.append(_row_line(row, "Window"))
    lines.extend(
        [
            "",
            "## Regime-Mix Runway",
            "",
            "| Mix | Policy | Scenario | Capital | Income/day | Drag/day | Net/day | Net APR | Drag coverage | 10% runway | Depletion | Status |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("rows", []):
        if row.get("kind") != "mix":
            continue
        lines.append(_row_line(row, "Mix"))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Income/day` is base fees plus retained dynamic premium.",
            "- `Drag/day` is route-away premium haircut, truth markout, gas, and rebalance drag.",
            "- A covered row has non-negative net after all measured drag.",
            "- Runway is a linear burn estimate; it is deliberately simpler than the Monte Carlo path test.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _mix_rows(source_rows: list[dict]) -> list[SurvivalRow]:
    by_key: dict[tuple[str, str, str], dict] = {}
    for row in source_rows:
        by_key[(str(row.get("window", "")), str(row.get("policy", "")), str(row.get("scenario", "")))] = row

    result: list[SurvivalRow] = []
    keys = {(policy, scenario) for _, policy, scenario in by_key}
    for mix in MIXES:
        windows = set(mix.probabilities)
        for policy, scenario in sorted(keys):
            parts = {
                window: by_key.get((window, policy, scenario))
                for window in windows
            }
            if any(part is None for part in parts.values()):
                continue
            result.append(_weighted_row(mix.name, parts, policy, scenario, mix.probabilities))
    return result


def _weighted_row(
    label: str,
    parts: dict[str, dict | None],
    policy: str,
    scenario: str,
    probabilities: dict[str, float],
) -> SurvivalRow:
    first = next(row for row in parts.values() if row is not None)
    weighted = dict(first)
    weighted["window"] = label
    for field in (
        "base_annual_usdc",
        "premium_kept_annual_usdc",
        "route_away_haircut_annual_usdc",
        "markout_annual_usdc",
        "gas_annual_usdc",
        "rebalance_annual_usdc",
        "annual_net_usdc",
    ):
        weighted[field] = sum(float(parts[window].get(field, 0)) * float(probability) for window, probability in probabilities.items() if parts[window] is not None)
    weighted["policy"] = policy
    weighted["scenario"] = scenario
    return _from_components(weighted, label, "mix")


def _from_components(row: dict, label: str, kind: str) -> SurvivalRow:
    capital = float(row.get("capital_usdc", 0))
    income = float(row.get("base_annual_usdc", 0)) + float(row.get("premium_kept_annual_usdc", 0))
    drag_components = {
        "route-away haircut": float(row.get("route_away_haircut_annual_usdc", 0)),
        "markout": float(row.get("markout_annual_usdc", 0)),
        "gas": float(row.get("gas_annual_usdc", 0)),
        "rebalance": float(row.get("rebalance_annual_usdc", 0)),
    }
    drag = -sum(min(value, 0.0) for value in drag_components.values())
    annual_net = float(row.get("annual_net_usdc", income - drag))
    daily_net = annual_net / YEAR_DAYS
    dominant_drag = min(drag_components, key=lambda key: drag_components[key])
    runway = _runway_days(capital, daily_net)
    coverage = income / drag if drag > 0 else None
    return SurvivalRow(
        label=label,
        kind=kind,
        policy=str(row.get("policy", "")),
        scenario=str(row.get("scenario", "")),
        capital_usdc=capital,
        annual_income_usdc=income,
        annual_drag_usdc=drag,
        annual_net_usdc=annual_net,
        net_apr=annual_net / capital if capital else 0.0,
        daily_income_usdc=income / YEAR_DAYS,
        daily_drag_usdc=drag / YEAR_DAYS,
        daily_net_usdc=daily_net,
        drag_coverage=coverage,
        days_to_1pct_loss=runway[0.01],
        days_to_5pct_loss=runway[0.05],
        days_to_10pct_loss=runway[0.10],
        days_to_25pct_loss=runway[0.25],
        days_to_depletion=runway[1.00],
        dominant_drag=dominant_drag,
        status=_status(annual_net, runway[0.10]),
    )


def _runway_days(capital_usdc: float, daily_net_usdc: float) -> dict[float, float | None]:
    if capital_usdc <= 0 or daily_net_usdc >= 0:
        return {threshold: None for threshold in LOSS_THRESHOLDS}
    daily_burn = -daily_net_usdc
    return {threshold: (capital_usdc * threshold) / daily_burn for threshold in LOSS_THRESHOLDS}


def _status(annual_net_usdc: float, days_to_10pct_loss: float | None) -> str:
    if annual_net_usdc >= 0:
        return "covered"
    if days_to_10pct_loss is not None and days_to_10pct_loss >= 90:
        return "slow burn"
    if days_to_10pct_loss is not None and days_to_10pct_loss >= 30:
        return "watch"
    return "fast burn"


def _row_line(row: dict, label_header: str) -> str:
    label = row["label"]
    return (
        f"| {label} | {row['policy']} | {row['scenario']} | {_usd_float(float(row['capital_usdc']))} | "
        f"{_usd_float(float(row['daily_income_usdc']))} | {_usd_float(float(row['daily_drag_usdc']))} | "
        f"{_usd_float(float(row['daily_net_usdc']))} | {float(row['net_apr']):.2%} | "
        f"{_ratio(row.get('drag_coverage'))} | {_days(row.get('days_to_10pct_loss'))} | "
        f"{_days(row.get('days_to_depletion'))} | {row['status']} |"
    )


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd_float(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


def _ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x"


def _days(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):,.1f}d"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate small-capital survival runway from PnL attribution")
    parser.add_argument("--pnl-attribution-json", type=Path, default=root / "docs" / "pnl_attribution_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "capital_survival_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "capital_survival_report.json")
    args = parser.parse_args()
    report = compute(args.pnl_attribution_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"capital survival rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
