from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import POLICIES, fixture_events

TARGET_APRS = (0.10, 0.20, 0.30)
YEAR_DAYS = 365


@dataclass(frozen=True)
class TargetReturnRow:
    window: str
    policy: str
    scenario: str
    target_apr: float
    current_turnover_per_day: float
    current_net_apr: float
    capital_e6: int
    edge_bps_after_route_and_gas: float
    active_ratio: float
    rebalance_drag_apr: float
    required_turnover_per_day: float | None
    required_daily_volume_e6: int | None
    estimated_daily_notional_e6: int | None
    max_capital_at_target_e6: int | None
    capacity_multiple: float | None
    feasible_at_current_turnover: bool
    status: str


def compute(root: Path, economic_tests_json: Path, live_status_json: Path) -> dict:
    economic_tests = _load_json(economic_tests_json)
    live_status = _load_json(live_status_json)
    daily_notional = _daily_notional(root, economic_tests, live_status)
    policies = {policy.name: policy for policy in POLICIES}
    rows: list[TargetReturnRow] = []
    for item in economic_tests.get("gas_adjusted_policies", []):
        policy = policies.get(str(item.get("policy", "")))
        if policy is None:
            continue
        for target_apr in TARGET_APRS:
            rows.append(_target_row(item, policy, target_apr, daily_notional.get(str(item.get("window", "")))))
    return {
        "economic_tests_source": str(economic_tests_json),
        "live_status_source": str(live_status_json),
        "targets": list(TARGET_APRS),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Target Return Thresholds",
        "",
        "This report converts measured gas-adjusted PegGuard economics into turnover",
        "and capacity requirements for target APRs. It uses the same conservative",
        "25% premium-haircut route-away model, gas scenarios, active-ratio, and",
        "rebalance-drag assumptions already present in `economic_tests.json`.",
        "",
        f"- Source: `{report.get('economic_tests_source', 'n/a')}`",
        "",
        "| Window | Policy | Scenario | Target APR | Current turnover | Current APR | Required turnover | Required daily volume | Max capital at observed daily notional | Capacity multiple | Status |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['policy']} | {row['scenario']} | {_pct(float(row['target_apr']))} | "
            f"{float(row['current_turnover_per_day']):.1f}x | {_pct(float(row['current_net_apr']))} | "
            f"{_turnover(row.get('required_turnover_per_day'))} | {_usd_or_na(row.get('required_daily_volume_e6'))} | "
            f"{_usd_or_na(row.get('max_capital_at_target_e6'))} | {_multiple(row.get('capacity_multiple'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `required turnover` includes gas drag, active-ratio, and annualized rebalance drag.",
            "- `max capital at observed daily notional` divides measured daily notional by the required turnover.",
            "- Live-shadow daily notional is measured same-swaps evidence and still does not measure real route-away.",
            "- `impossible` means measured edge after route-away and gas is non-positive for that row.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _target_row(item: dict, policy, target_apr: float, estimated_daily_notional_e6: int | None) -> TargetReturnRow:
    capital_e6 = int(round(float(item.get("capital_usdc", 0)) * 1_000_000))
    edge_bps = float(item.get("net_bps_after_route", 0)) - float(item.get("gas_bps", 0))
    rebalance_drag = (float(policy.rebalance_cost_bps) / 10_000) * int(policy.rebalances_per_year)
    required_turnover = _required_turnover(edge_bps, float(policy.active_ratio), rebalance_drag, target_apr)
    required_volume = int(round(capital_e6 * required_turnover)) if required_turnover is not None else None
    max_capital = (
        int(round(estimated_daily_notional_e6 / required_turnover))
        if estimated_daily_notional_e6 is not None and required_turnover and required_turnover > 0
        else None
    )
    capacity_multiple = max_capital / capital_e6 if max_capital is not None and capital_e6 > 0 else None
    current_net_apr = float(item.get("net_apr", 0))
    feasible = current_net_apr >= target_apr
    if required_turnover is None:
        status = "impossible"
    elif feasible:
        status = "current turnover sufficient"
    else:
        status = "needs more turnover"
    return TargetReturnRow(
        window=str(item.get("window", "")),
        policy=str(item.get("policy", "")),
        scenario=str(item.get("scenario", "")),
        target_apr=target_apr,
        current_turnover_per_day=float(item.get("turnover_per_day", 0)),
        current_net_apr=current_net_apr,
        capital_e6=capital_e6,
        edge_bps_after_route_and_gas=edge_bps,
        active_ratio=float(policy.active_ratio),
        rebalance_drag_apr=rebalance_drag,
        required_turnover_per_day=required_turnover,
        required_daily_volume_e6=required_volume,
        estimated_daily_notional_e6=estimated_daily_notional_e6,
        max_capital_at_target_e6=max_capital,
        capacity_multiple=capacity_multiple,
        feasible_at_current_turnover=feasible,
        status=status,
    )


def _required_turnover(edge_bps: float, active_ratio: float, rebalance_drag: float, target_apr: float) -> float | None:
    edge_rate = edge_bps / 10_000
    denom = edge_rate * active_ratio * YEAR_DAYS
    if denom <= 0:
        return None
    return (target_apr + rebalance_drag) / denom


def _daily_notional(root: Path, economic_tests: dict, live_status: dict) -> dict[str, int]:
    daily: dict[str, int] = {}
    metrics = {
        str(row.get("window", "")): int(row.get("notional_e6", 0))
        for row in economic_tests.get("benchmarks", [])
        if str(row.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}
    }
    for window in ("calm", "vol"):
        duration_days = _fixture_duration_days(root, window)
        if duration_days > 0 and metrics.get(window):
            daily[window] = int(metrics[window] / duration_days)
    live_hours = float(live_status.get("observed_span_hours", 0))
    if live_hours > 0 and metrics.get("live shadow"):
        daily["live shadow"] = int(metrics["live shadow"] / (live_hours / 24))
    return daily


def _fixture_duration_days(root: Path, window: str) -> float:
    events, _ = fixture_events(root, window)
    if len(events) < 2:
        return 0.0
    return (events[-1].t_ms - events[0].t_ms) / 86_400_000


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


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    value_e6 = int(value)
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _multiple(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Compute turnover and capacity needed to hit target APRs")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "target_return_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "target_return_report.json")
    args = parser.parse_args()
    report = compute(root, args.economic_tests_json, args.live_status_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"target return rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
