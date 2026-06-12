from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C

YEAR_DAYS = 365
ITERATIONS = 2_000
SEED = 20260607


@dataclass(frozen=True)
class MixSpec:
    name: str
    days: int
    probabilities: dict[str, float]
    note: str


@dataclass(frozen=True)
class PolicyMonteCarloRow:
    mix: str
    policy: str
    scenario: str
    days: int
    iterations: int
    start_capital_e6: int
    probability_loss: float
    probability_drawdown_gt_1pct: float
    ending_capital_p05_e6: int
    ending_capital_p50_e6: int
    ending_capital_p95_e6: int
    return_p05: float
    return_p50: float
    return_p95: float
    max_drawdown_p50: float
    max_drawdown_p95: float
    average_loss_days: float
    average_vol_days: float


MIXES = [
    MixSpec(
        "routine 30d",
        30,
        {"calm": 0.90, "vol": 0.10},
        "Independent daily draw with one volatile day expected every ten days.",
    ),
    MixSpec(
        "shock 30d",
        30,
        {"calm": 0.75, "vol": 0.25},
        "Higher-volatility month with one volatile day expected every four days.",
    ),
    MixSpec(
        "stress 30d",
        30,
        {"calm": 0.50, "vol": 0.50},
        "Severe stress mix; half the days reuse volatile-window economics.",
    ),
    MixSpec(
        "routine 90d",
        90,
        {"calm": 0.90, "vol": 0.10},
        "Longer routine path to expose compounding and drawdown frequency.",
    ),
]


def compute(economic_tests_json: Path, iterations: int = ITERATIONS, seed: int = SEED) -> dict:
    data = _load_json(economic_tests_json)
    returns = _policy_returns(data)
    rows: list[PolicyMonteCarloRow] = []
    for mix in MIXES:
        if not set(mix.probabilities).issubset(returns):
            continue
        common_keys = set.intersection(*(set(returns[window]) for window in mix.probabilities))
        for key in sorted(common_keys):
            policy, scenario = key
            rows.append(_simulate_row(mix, policy, scenario, returns, iterations, seed))
    return {
        "source": str(economic_tests_json),
        "iterations": iterations,
        "seed": seed,
        "mixes": [asdict(mix) for mix in MIXES],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Policy Monte Carlo",
        "",
        "This report turns measured gas-adjusted policy APR rows into stochastic",
        "multi-day capital paths. It is a regime-mix stress harness, not a forecast:",
        "daily returns are sampled from the already measured calm/volatile windows",
        "using the explicit mixes below.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Iterations: {int(report.get('iterations', 0))}",
        f"- Seed: {int(report.get('seed', 0))}",
        "",
        "## Mixes",
        "",
        "| Mix | Days | Probabilities | Note |",
        "|---|---:|---|---|",
    ]
    for mix in report.get("mixes", []):
        lines.append(
            f"| {mix['name']} | {int(mix['days'])} | {_probabilities(mix.get('probabilities', {}))} | {mix['note']} |"
        )
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Mix | Policy | Scenario | Start capital | P(loss) | P(drawdown >1%) | Ending p05/p50/p95 | Return p05/p50/p95 | Max drawdown p50/p95 | Avg loss days | Avg vol days |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['mix']} | {row['policy']} | {row['scenario']} | {_usd(int(row['start_capital_e6']))} | "
            f"{float(row['probability_loss']):.2%} | {float(row['probability_drawdown_gt_1pct']):.2%} | "
            f"{_usd(int(row['ending_capital_p05_e6']))} / {_usd(int(row['ending_capital_p50_e6']))} / {_usd(int(row['ending_capital_p95_e6']))} | "
            f"{_pct(float(row['return_p05']))} / {_pct(float(row['return_p50']))} / {_pct(float(row['return_p95']))} | "
            f"{_pct(-float(row['max_drawdown_p50']))} / {_pct(-float(row['max_drawdown_p95']))} | "
            f"{float(row['average_loss_days']):.1f} | {float(row['average_vol_days']):.1f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The daily regime mix is an explicit stress assumption; it is not inferred from enough history to be a production forecast.",
            "- `P(loss)` is the probability that ending capital is below starting capital after the simulated path.",
            "- Drawdown is measured from the running capital peak in each simulated path.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _simulate_row(
    mix: MixSpec,
    policy: str,
    scenario: str,
    returns: dict[str, dict[tuple[str, str], tuple[int, float]]],
    iterations: int,
    seed: int,
) -> PolicyMonteCarloRow:
    key = (policy, scenario)
    start_capital_e6 = next(iter(returns.values()))[key][0]
    rng = random.Random(_scenario_seed(seed, mix.name, policy, scenario))
    endings: list[int] = []
    returns_values: list[float] = []
    drawdowns: list[float] = []
    loss_paths = 0
    drawdown_gt_1pct = 0
    loss_days_total = 0
    vol_days_total = 0
    choices = _expanded_choices(mix.probabilities)
    for _ in range(iterations):
        capital = float(start_capital_e6)
        peak = capital
        max_drawdown = 0.0
        loss_days = 0
        vol_days = 0
        for _day in range(mix.days):
            window = _draw_window(rng, choices)
            if window == "vol":
                vol_days += 1
            _, apr = returns[window][key]
            daily_return = apr / YEAR_DAYS
            if daily_return < 0:
                loss_days += 1
            capital *= 1 + daily_return
            peak = max(peak, capital)
            drawdown = (capital - peak) / peak if peak else 0.0
            max_drawdown = min(max_drawdown, drawdown)
        ending = int(round(capital))
        path_return = ending / start_capital_e6 - 1 if start_capital_e6 else 0.0
        endings.append(ending)
        returns_values.append(path_return)
        drawdowns.append(max_drawdown)
        loss_days_total += loss_days
        vol_days_total += vol_days
        if ending < start_capital_e6:
            loss_paths += 1
        if max_drawdown <= -0.01:
            drawdown_gt_1pct += 1

    return PolicyMonteCarloRow(
        mix=mix.name,
        policy=policy,
        scenario=scenario,
        days=mix.days,
        iterations=iterations,
        start_capital_e6=start_capital_e6,
        probability_loss=loss_paths / iterations if iterations else 0.0,
        probability_drawdown_gt_1pct=drawdown_gt_1pct / iterations if iterations else 0.0,
        ending_capital_p05_e6=_percentile_int(endings, 0.05),
        ending_capital_p50_e6=_percentile_int(endings, 0.50),
        ending_capital_p95_e6=_percentile_int(endings, 0.95),
        return_p05=_percentile_float(returns_values, 0.05),
        return_p50=_percentile_float(returns_values, 0.50),
        return_p95=_percentile_float(returns_values, 0.95),
        max_drawdown_p50=_percentile_float(sorted(drawdowns), 0.50),
        max_drawdown_p95=_percentile_float(sorted(drawdowns), 0.05),
        average_loss_days=loss_days_total / iterations if iterations else 0.0,
        average_vol_days=vol_days_total / iterations if iterations else 0.0,
    )


def _policy_returns(data: dict) -> dict[str, dict[tuple[str, str], tuple[int, float]]]:
    result: dict[str, dict[tuple[str, str], tuple[int, float]]] = {}
    for row in data.get("gas_adjusted_policies", []):
        window = str(row.get("window", ""))
        policy = str(row.get("policy", ""))
        scenario = str(row.get("scenario", ""))
        capital_e6 = int(round(float(row.get("capital_usdc", 0)) * 1_000_000))
        net_apr = float(row.get("net_apr", 0))
        if not window or not policy or not scenario or capital_e6 <= 0:
            continue
        result.setdefault(window, {})[(policy, scenario)] = (capital_e6, net_apr)
    return result


def _expanded_choices(probabilities: dict[str, float]) -> list[tuple[str, float]]:
    total = sum(max(0.0, float(value)) for value in probabilities.values())
    if total <= 0:
        return []
    cumulative = 0.0
    choices: list[tuple[str, float]] = []
    for window, probability in sorted(probabilities.items()):
        cumulative += max(0.0, float(probability)) / total
        choices.append((window, cumulative))
    choices[-1] = (choices[-1][0], 1.0)
    return choices


def _draw_window(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    value = rng.random()
    for window, boundary in choices:
        if value <= boundary:
            return window
    return choices[-1][0]


def _percentile_int(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    return ordered[_percentile_index(len(ordered), percentile)]


def _percentile_float(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[_percentile_index(len(ordered), percentile)]


def _percentile_index(length: int, percentile: float) -> int:
    if length <= 0:
        return 0
    return min(length - 1, max(0, int(round((length - 1) * percentile))))


def _scenario_seed(seed: int, *parts: str) -> int:
    acc = seed
    for byte in "|".join(parts).encode("utf-8"):
        acc = ((acc * 131) + byte) & 0xFFFFFFFF
    return acc


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _probabilities(probabilities: object) -> str:
    if not isinstance(probabilities, dict):
        return "n/a"
    return ", ".join(f"{window} {float(probability):.0%}" for window, probability in sorted(probabilities.items()))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Simulate PegGuard policy returns across explicit regime mixes")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "policy_monte_carlo_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "policy_monte_carlo_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json, iterations=args.iterations, seed=args.seed)
    write_outputs(report, args.out_md, args.out_json)
    print(f"policy Monte Carlo rows={len(report['rows'])} iterations={args.iterations}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
