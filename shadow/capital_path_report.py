from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C

YEAR_DAYS = 365


@dataclass(frozen=True)
class PathSpec:
    name: str
    windows: tuple[str, ...]
    note: str


@dataclass(frozen=True)
class CapitalPathRow:
    path: str
    policy: str
    scenario: str
    days: int
    start_capital_e6: int
    ending_capital_e6: int
    pnl_e6: int
    cumulative_return: float
    annualized_return: float
    max_drawdown: float
    loss_days: int
    worst_day_return: float
    window_counts: dict[str, int]


PATHS = [
    PathSpec("calm 30d", ("calm",) * 30, "Repeats the calm fixture economics for 30 daily periods."),
    PathSpec(
        "weekly vol shock 30d",
        (("calm",) * 6 + ("vol",)) * 4 + ("calm", "calm"),
        "Four weekly volatile shocks embedded in otherwise calm trading.",
    ),
    PathSpec("all volatile 7d", ("vol",) * 7, "Seven consecutive volatile stress days."),
    PathSpec("live shadow 30d", ("live shadow",) * 30, "Repeats the current forward shadow sample for 30 daily periods."),
]


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    policy_returns = _policy_returns(data)
    rows: list[CapitalPathRow] = []
    for path in PATHS:
        if not all(window in policy_returns for window in set(path.windows)):
            continue
        common_keys = set.intersection(*(set(policy_returns[window]) for window in set(path.windows)))
        for key in sorted(common_keys):
            policy, scenario = key
            rows.append(_path_row(path, policy, scenario, policy_returns))
    return {
        "source": str(economic_tests_json),
        "rows": [asdict(row) for row in rows],
        "paths": [asdict(path) for path in PATHS],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Capital Path Stress",
        "",
        "This report compounds the existing gas-adjusted policy economics across",
        "deterministic multi-day paths. It is a stress harness, not a forecast: each",
        "daily step reuses measured calm, volatile, or live-shadow net APR from",
        "`economic_tests.json`, including the conservative 25% premium haircut, gas",
        "scenario, active-ratio, and rebalance-drag assumptions already used there.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        "",
        "## Path Definitions",
        "",
        "| Path | Days | Windows | Note |",
        "|---|---:|---|---|",
    ]
    for path in report.get("paths", []):
        counts = _counts(path.get("windows", []))
        lines.append(
            f"| {path['name']} | {len(path.get('windows', []))} | {_counts_text(counts)} | {path['note']} |"
        )
    lines.extend(
        [
            "",
            "## Results",
            "",
            "| Path | Policy | Scenario | Start capital | Ending capital | PnL | Cumulative return | Annualized | Max drawdown | Loss days | Worst day |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['path']} | {row['policy']} | {row['scenario']} | "
            f"{_usd(int(row['start_capital_e6']))} | {_usd(int(row['ending_capital_e6']))} | "
            f"{_usd(int(row['pnl_e6']))} | {_pct(float(row['cumulative_return']))} | "
            f"{_pct(float(row['annualized_return']))} | {_pct(float(row['max_drawdown']))} | "
            f"{int(row['loss_days'])} | {_pct(float(row['worst_day_return']))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Positive calm paths show whether routine trading can cover operating drag after route-away assumptions.",
            "- Weekly-shock and all-volatile paths expose drawdown and sequence risk that a single-window APR table hides.",
            "- The live-shadow path is measured same-swaps evidence and still does not measure real route-away.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


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


def _path_row(
    path: PathSpec,
    policy: str,
    scenario: str,
    policy_returns: dict[str, dict[tuple[str, str], tuple[int, float]]],
) -> CapitalPathRow:
    key = (policy, scenario)
    start_capital_e6 = policy_returns[path.windows[0]][key][0]
    capital = float(start_capital_e6)
    peak = capital
    max_drawdown = 0.0
    loss_days = 0
    worst_day_return = 0.0
    for window in path.windows:
        _, apr = policy_returns[window][key]
        daily_return = apr / YEAR_DAYS
        capital *= 1 + daily_return
        peak = max(peak, capital)
        drawdown = (capital - peak) / peak if peak else 0.0
        max_drawdown = min(max_drawdown, drawdown)
        if daily_return < 0:
            loss_days += 1
        worst_day_return = min(worst_day_return, daily_return)
    ending_capital_e6 = int(round(capital))
    cumulative_return = ending_capital_e6 / start_capital_e6 - 1 if start_capital_e6 else 0.0
    annualized_return = (ending_capital_e6 / start_capital_e6) ** (YEAR_DAYS / len(path.windows)) - 1 if start_capital_e6 else 0.0
    return CapitalPathRow(
        path=path.name,
        policy=policy,
        scenario=scenario,
        days=len(path.windows),
        start_capital_e6=start_capital_e6,
        ending_capital_e6=ending_capital_e6,
        pnl_e6=ending_capital_e6 - start_capital_e6,
        cumulative_return=cumulative_return,
        annualized_return=annualized_return,
        max_drawdown=max_drawdown,
        loss_days=loss_days,
        worst_day_return=worst_day_return,
        window_counts=_counts(path.windows),
    )


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _counts(windows: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    for window in windows:
        key = str(window)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _counts_text(counts: dict[str, int]) -> str:
    return ", ".join(f"{window} x{count}" for window, count in sorted(counts.items()))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Compound measured PegGuard economics through deterministic capital paths")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "capital_path_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "capital_path_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"capital path rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
