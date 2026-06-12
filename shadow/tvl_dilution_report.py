from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events

YEAR_DAYS = 365
ROUTE_AWAY_RATES = (0.0, 0.25, 0.50)
TARGET_APRS = (0.10, 0.20, 0.30)
ACTIVE_CAPITAL_E6 = (
    10_000_000_000,
    25_000_000_000,
    100_000_000_000,
    500_000_000_000,
    1_000_000_000_000,
)


@dataclass(frozen=True)
class WindowEdge:
    window: str
    strategy: str
    sample_days: float
    sample_notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int


@dataclass(frozen=True)
class CapitalRow:
    window: str
    route_away: float
    active_capital_e6: int
    sample_days: float
    sample_net_e6: int
    daily_net_e6: int
    annualized_apr: float | None
    status: str


@dataclass(frozen=True)
class EquilibriumRow:
    window: str
    route_away: float
    target_apr: float
    sample_days: float
    sample_net_e6: int
    daily_net_e6: int
    max_active_capital_e6: int | None
    status: str


def compute(root: Path, economic_tests_json: Path, live_status_json: Path) -> dict:
    economic_tests = _load_json(economic_tests_json)
    live_status = _load_json(live_status_json)
    edges = _window_edges(root, economic_tests, live_status)
    capital_rows: list[CapitalRow] = []
    equilibrium_rows: list[EquilibriumRow] = []
    for edge in edges:
        for route_away in ROUTE_AWAY_RATES:
            sample_net = _sample_net(edge, route_away)
            daily_net = _daily_net(sample_net, edge.sample_days)
            for capital_e6 in ACTIVE_CAPITAL_E6:
                capital_rows.append(_capital_row(edge, route_away, capital_e6, sample_net, daily_net))
            for target_apr in TARGET_APRS:
                equilibrium_rows.append(_equilibrium_row(edge, route_away, target_apr, sample_net, daily_net))
    return {
        "economic_tests_source": str(economic_tests_json),
        "live_status_source": str(live_status_json),
        "route_away_rates": list(ROUTE_AWAY_RATES),
        "target_aprs": list(TARGET_APRS),
        "active_capital_e6": list(ACTIVE_CAPITAL_E6),
        "windows": [asdict(edge) for edge in edges],
        "capital_rows": [asdict(row) for row in capital_rows],
        "equilibrium_rows": [asdict(row) for row in equilibrium_rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# TVL Dilution And Equilibrium",
        "",
        "This report asks how much active capital can share the measured PegGuard",
        "edge before APR falls below target returns. It is an equilibrium-capacity",
        "view: same measured daily edge, more active capital sharing it.",
        "",
        f"- Source: `{report.get('economic_tests_source', 'n/a')}`",
        "- Route-away haircut is applied only to PegGuard extra premium; base fees and truth markout stay measured.",
        "- Live-shadow rows are same-swaps evidence and still do not measure real route-away.",
        "",
        "## APR At Active Capital",
        "",
        "| Window | Route-away | Active capital | Sample net | Daily net | APR | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("capital_rows", []):
        lines.append(
            f"| {row['window']} | {float(row['route_away']):.0%} | {_usd(int(row['active_capital_e6']))} | "
            f"{_usd(int(row['sample_net_e6']))} | {_usd(int(row['daily_net_e6']))} | {_pct_or_na(row.get('annualized_apr'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Equilibrium Active Capital",
            "",
            "| Window | Route-away | Target APR | Sample net | Daily net | Max active capital | Status |",
            "|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("equilibrium_rows", []):
        lines.append(
            f"| {row['window']} | {float(row['route_away']):.0%} | {_pct_or_na(row.get('target_apr'))} | "
            f"{_usd(int(row['sample_net_e6']))} | {_usd(int(row['daily_net_e6']))} | "
            f"{_usd_or_na(row.get('max_active_capital_e6'))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `max active capital` is the equilibrium TVL cap for the target APR under the measured daily edge.",
            "- Negative or zero measured daily edge means extra capital cannot fix the economics; the row is `edge non-positive`.",
            "- This is not a route-away measurement and should be read beside the controlled route-away gate.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _window_edges(root: Path, economic_tests: dict, live_status: dict) -> list[WindowEdge]:
    durations = {
        "calm": _fixture_duration_days(root, "calm"),
        "vol": _fixture_duration_days(root, "vol"),
    }
    live_hours = float(live_status.get("observed_span_hours", 0))
    if live_hours > 0:
        durations["live shadow"] = live_hours / 24

    edges: list[WindowEdge] = []
    for row in economic_tests.get("benchmarks", []):
        name = str(row.get("name", ""))
        if name not in {"PegGuard selected", "PegGuard live shadow"}:
            continue
        window = str(row.get("window", ""))
        sample_days = durations.get(window, 0.0)
        if sample_days <= 0:
            continue
        edges.append(
            WindowEdge(
                window=window,
                strategy=name,
                sample_days=sample_days,
                sample_notional_e6=int(row.get("notional_e6", 0)),
                base_fee_e6=int(row.get("base_fee_e6", 0)),
                extra_e6=int(row.get("extra_e6", 0)),
                markout_e6=int(row.get("markout_e6", 0)),
            )
        )
    return sorted(edges, key=lambda item: ("0" if item.window == "live shadow" else item.window))


def _capital_row(edge: WindowEdge, route_away: float, capital_e6: int, sample_net: int, daily_net: int) -> CapitalRow:
    if capital_e6 <= 0:
        apr = None
    else:
        apr = (daily_net * YEAR_DAYS) / capital_e6
    status = _status(apr)
    return CapitalRow(edge.window, route_away, capital_e6, edge.sample_days, sample_net, daily_net, apr, status)


def _equilibrium_row(edge: WindowEdge, route_away: float, target_apr: float, sample_net: int, daily_net: int) -> EquilibriumRow:
    max_capital = int((daily_net * YEAR_DAYS) / target_apr) if daily_net > 0 and target_apr > 0 else None
    status = "capacity exists" if max_capital is not None else "edge non-positive"
    return EquilibriumRow(edge.window, route_away, target_apr, edge.sample_days, sample_net, daily_net, max_capital, status)


def _sample_net(edge: WindowEdge, route_away: float) -> int:
    return edge.base_fee_e6 + int(edge.extra_e6 * (1 - route_away)) - edge.markout_e6


def _daily_net(sample_net_e6: int, sample_days: float) -> int:
    if sample_days <= 0:
        return 0
    return int(round(sample_net_e6 / sample_days))


def _fixture_duration_days(root: Path, window: str) -> float:
    events, _ = fixture_events(root, window)
    if len(events) < 2:
        return 0.0
    return (events[-1].t_ms - events[0].t_ms) / 86_400_000


def _status(apr: float | None) -> str:
    if apr is None:
        return "no capital"
    if apr < 0:
        return "negative edge"
    if apr < 0.10:
        return "below 10%"
    if apr < 0.20:
        return "10-20%"
    if apr < 0.30:
        return "20-30%"
    return ">=30%"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return _usd(int(value))


def _pct_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Compute active-capital dilution against measured PegGuard edge")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "tvl_dilution_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "tvl_dilution_report.json")
    args = parser.parse_args()
    report = compute(root, args.economic_tests_json, args.live_status_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"tvl dilution: capital_rows={len(report['capital_rows'])} equilibrium_rows={len(report['equilibrium_rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
