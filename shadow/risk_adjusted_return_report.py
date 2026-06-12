from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .policy_monte_carlo_report import MIXES

YEAR_DAYS = 365
TARGET_RETURN = 0.10


@dataclass(frozen=True)
class RiskAdjustedReturnRow:
    mix: str
    policy: str
    scenario: str
    capital_e6: int
    annual_mean_return: float
    annual_volatility: float
    annual_downside_volatility: float
    sharpe_like: float | None
    sortino_like: float | None
    loss_day_probability: float
    worst_window_daily_return: float
    best_window_daily_return: float
    target_return: float
    status: str


def compute(economic_tests_json: Path, target_return: float = TARGET_RETURN) -> dict:
    data = _load_json(economic_tests_json)
    returns = _policy_returns(data)
    rows: list[RiskAdjustedReturnRow] = []
    for mix in MIXES:
        if not set(mix.probabilities).issubset(returns):
            continue
        common_keys = set.intersection(*(set(returns[window]) for window in mix.probabilities))
        for policy, scenario in sorted(common_keys):
            rows.append(_row(mix.name, mix.probabilities, policy, scenario, returns, target_return))
    return {
        "source": str(economic_tests_json),
        "target_return": target_return,
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Risk-Adjusted Return",
        "",
        "This report converts measured gas-adjusted policy economics into",
        "risk-adjusted regime-mix metrics. It is not a forecast: the calm/volatile",
        "probabilities are the explicit mixes from the policy Monte Carlo report.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Target return: {_pct(float(report.get('target_return', TARGET_RETURN)))}",
        "",
        "| Mix | Policy | Scenario | Capital | Mean APR | Ann vol | Downside vol | Sharpe-like | Sortino-like | Loss-day prob | Daily range | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['mix']} | {row['policy']} | {row['scenario']} | {_usd(int(row['capital_e6']))} | "
            f"{_pct(float(row['annual_mean_return']))} | {_pct(float(row['annual_volatility']))} | "
            f"{_pct(float(row['annual_downside_volatility']))} | {_ratio(row.get('sharpe_like'))} | "
            f"{_ratio(row.get('sortino_like'))} | {_pct(float(row['loss_day_probability']))} | "
            f"{_pct(float(row['worst_window_daily_return']))} to {_pct(float(row['best_window_daily_return']))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Mean APR` is the probability-weighted annualized return from measured calm/volatile policy rows.",
            "- `Ann vol` is annualized volatility of the daily regime returns, not price volatility.",
            "- `Downside vol` measures only negative daily policy returns; Sortino-like uses that denominator.",
            "- The target-return status is diagnostic. It does not change hook parameters or completion floors.",
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
    mix: str,
    probabilities: dict[str, float],
    policy: str,
    scenario: str,
    returns: dict[str, dict[tuple[str, str], tuple[int, float]]],
    target_return: float,
) -> RiskAdjustedReturnRow:
    normalized = _normalized_probabilities(probabilities)
    capital_e6 = next(iter(returns.values()))[(policy, scenario)][0]
    daily_returns = {window: returns[window][(policy, scenario)][1] / YEAR_DAYS for window in normalized}
    mean_daily = sum(normalized[window] * daily_returns[window] for window in normalized)
    variance_daily = sum(
        normalized[window] * (daily_returns[window] - mean_daily) ** 2 for window in normalized
    )
    downside_variance_daily = sum(
        normalized[window] * min(0.0, daily_returns[window]) ** 2 for window in normalized
    )
    annual_mean = mean_daily * YEAR_DAYS
    annual_volatility = math.sqrt(variance_daily * YEAR_DAYS)
    downside_volatility = math.sqrt(downside_variance_daily * YEAR_DAYS)
    sharpe = annual_mean / annual_volatility if annual_volatility > 0 else None
    sortino = annual_mean / downside_volatility if downside_volatility > 0 else None
    loss_day_probability = sum(
        normalized[window] for window, daily_return in daily_returns.items() if daily_return < 0
    )
    return RiskAdjustedReturnRow(
        mix=mix,
        policy=policy,
        scenario=scenario,
        capital_e6=capital_e6,
        annual_mean_return=annual_mean,
        annual_volatility=annual_volatility,
        annual_downside_volatility=downside_volatility,
        sharpe_like=sharpe,
        sortino_like=sortino,
        loss_day_probability=loss_day_probability,
        worst_window_daily_return=min(daily_returns.values()),
        best_window_daily_return=max(daily_returns.values()),
        target_return=target_return,
        status=_status(annual_mean, loss_day_probability, sortino, target_return),
    )


def _policy_returns(data: dict) -> dict[str, dict[tuple[str, str], tuple[int, float]]]:
    result: dict[str, dict[tuple[str, str], tuple[int, float]]] = {}
    for item in data.get("gas_adjusted_policies", []):
        window = str(item.get("window", ""))
        policy = str(item.get("policy", ""))
        scenario = str(item.get("scenario", ""))
        capital_e6 = int(round(float(item.get("capital_usdc", 0)) * 1_000_000))
        net_apr = float(item.get("net_apr", 0))
        if window and policy and scenario and capital_e6 > 0:
            result.setdefault(window, {})[(policy, scenario)] = (capital_e6, net_apr)
    return result


def _normalized_probabilities(probabilities: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, float(value)) for value in probabilities.values())
    if total <= 0:
        return {}
    return {window: max(0.0, float(value)) / total for window, value in probabilities.items()}


def _status(
    annual_mean: float,
    loss_day_probability: float,
    sortino: float | None,
    target_return: float,
) -> str:
    if annual_mean < target_return:
        return "below target"
    if loss_day_probability > 0.25:
        return "loss-prone"
    if sortino is not None and sortino < 1.0:
        return "weak downside-adjusted"
    return "risk-adjusted viable"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _pct(value: float) -> str:
    return f"{value:.2%}"


def _ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}"


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Compute risk-adjusted policy return metrics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--target-return", type=float, default=TARGET_RETURN)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "risk_adjusted_return_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "risk_adjusted_return_report.json")
    args = parser.parse_args()

    report = compute(args.economic_tests_json, args.target_return)
    write_outputs(report, args.out_md, args.out_json)
    print(f"risk-adjusted rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
