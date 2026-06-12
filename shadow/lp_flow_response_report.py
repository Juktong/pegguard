from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import YEAR_DAYS, fixture_events

ROUTE_AWAY = 0.25
SCENARIOS = ("hook + Pyth, low L2", "hook + Pyth, stressed L2")
START_CAPITAL_E6 = (10_000_000_000, 25_000_000_000, 100_000_000_000)
ENTRY_APR = 0.20
EXIT_APR = 0.00
INFLOW_RATE = 0.10
OUTFLOW_RATE = 0.20
MIN_CAPITAL_E6 = 1_000_000_000
MAX_CAPITAL_E6 = 1_000_000_000_000

PATHS = {
    "calm 30d": ("calm",) * 30,
    "weekly vol shock 30d": (("calm",) * 6 + ("vol",)) * 4 + ("calm", "calm"),
    "all volatile 7d": ("vol",) * 7,
    "live shadow 30d": ("live shadow",) * 30,
}


@dataclass(frozen=True)
class WindowEdge:
    window: str
    scenario: str
    sample_days: float
    sample_net_e6: int
    daily_net_e6: int
    gas_e6: int


@dataclass(frozen=True)
class FlowRow:
    path: str
    scenario: str
    start_capital_e6: int
    ending_capital_e6: int
    cumulative_pnl_e6: int
    net_flow_e6: int
    min_apr: float
    median_apr: float
    ending_apr: float
    max_drawdown: float
    inflow_days: int
    outflow_days: int
    exit_floor_days: int
    status: str


def compute(root: Path, economic_tests_json: Path, live_status_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    live_status = _load_json(live_status_json)
    edges = _window_edges(root, data, live_status)
    rows: list[FlowRow] = []
    for path_name, windows in PATHS.items():
        for scenario in SCENARIOS:
            if not all((window, scenario) in edges for window in set(windows)):
                continue
            for start_capital in START_CAPITAL_E6:
                rows.append(_simulate(path_name, windows, scenario, start_capital, edges))
    return {
        "economic_tests_source": str(economic_tests_json),
        "live_status_source": str(live_status_json),
        "model": (
            "LP flow-response simulation. Daily edge is measured PegGuard base plus retained dynamic premium "
            "minus truth markout and gas. Active capital enters when implied APR is at least 20%, exits when "
            "APR is negative, and flows are bounded per day. This tests adaptive TVL behavior, not route-away."
        ),
        "route_away": ROUTE_AWAY,
        "entry_apr": ENTRY_APR,
        "exit_apr": EXIT_APR,
        "inflow_rate": INFLOW_RATE,
        "outflow_rate": OUTFLOW_RATE,
        "min_capital_e6": MIN_CAPITAL_E6,
        "max_capital_e6": MAX_CAPITAL_E6,
        "start_capital_e6": list(START_CAPITAL_E6),
        "windows": [asdict(edge) for edge in edges.values()],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    rows = report.get("rows", [])
    lines = [
        "# LP Flow Response",
        "",
        "This report models active LP capital as adaptive instead of fixed. It uses",
        "measured PegGuard daily edge from the economic suite and lets capital enter",
        "when implied APR is high, leave when APR is negative, and stay bounded by",
        "per-day flow limits.",
        "",
        f"- Source: `{report.get('economic_tests_source', 'n/a')}`",
        f"- Live status source: `{report.get('live_status_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Route-away haircut: {_pct(float(report.get('route_away', ROUTE_AWAY)))}",
        f"- Entry APR: {_pct(float(report.get('entry_apr', ENTRY_APR)))}",
        f"- Exit APR: {_pct(float(report.get('exit_apr', EXIT_APR)))}",
        f"- Daily inflow/outflow caps: {_pct(float(report.get('inflow_rate', INFLOW_RATE)))} / {_pct(float(report.get('outflow_rate', OUTFLOW_RATE)))}",
        "",
        "## Measured Daily Edge",
        "",
        "| Window | Scenario | Sample days | Sample net | Daily net | Gas |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for edge in report.get("windows", []):
        lines.append(
            f"| {edge['window']} | {edge['scenario']} | {float(edge['sample_days']):.3f} | "
            f"{_usd(int(edge['sample_net_e6']))} | {_usd(int(edge['daily_net_e6']))} | {_usd(int(edge['gas_e6']))} |"
        )
    lines.extend(
        [
            "",
            "## Flow Simulation",
            "",
            "| Path | Scenario | Start capital | Ending capital | PnL | Net flow | Min APR | Median APR | Ending APR | Max drawdown | Inflow days | Outflow days | Floor days | Status |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['path']} | {row['scenario']} | {_usd(int(row['start_capital_e6']))} | "
            f"{_usd(int(row['ending_capital_e6']))} | {_usd(int(row['cumulative_pnl_e6']))} | "
            f"{_usd(int(row['net_flow_e6']))} | {_pct(float(row['min_apr']))} | "
            f"{_pct(float(row['median_apr']))} | {_pct(float(row['ending_apr']))} | "
            f"{_pct(float(row['max_drawdown']))} | {int(row['inflow_days'])} | {int(row['outflow_days'])} | "
            f"{int(row['exit_floor_days'])} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Positive calm rows with inflow show the edge can attract capital, but the resulting TVL dilutes APR.",
            "- Volatile rows with outflow show whether measured premiums are enough to keep capital through stress.",
            "- `net flow` is external LP capital movement, separate from trading PnL.",
        "- Live-shadow rows are measured same-swaps evidence and still do not measure real route-away.",
        "- Realized losses are capped at the minimum-capital floor; remaining measured demand would require more depth than the simulated capital can support.",
        "",
    ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _window_edges(root: Path, data: dict, live_status: dict) -> dict[tuple[str, str], WindowEdge]:
    selected = {
        str(row.get("window", "")): row
        for row in data.get("benchmarks", [])
        if str(row.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}
    }
    gas_rows = {
        (str(row.get("window", "")), str(row.get("scenario", ""))): row
        for row in data.get("gas_sensitivity", [])
    }
    sample_days = {
        "calm": _fixture_duration_days(root, "calm"),
        "vol": _fixture_duration_days(root, "vol"),
    }
    live_hours = float(live_status.get("observed_span_hours", 0))
    if live_hours > 0:
        sample_days["live shadow"] = live_hours / 24

    edges: dict[tuple[str, str], WindowEdge] = {}
    for window, metric in selected.items():
        days = sample_days.get(window, 0.0)
        if days <= 0:
            continue
        for scenario in SCENARIOS:
            gas = gas_rows.get((window, scenario))
            if gas is None:
                continue
            sample_net = (
                int(metric.get("base_fee_e6", 0))
                + int(int(metric.get("extra_e6", 0)) * (1 - ROUTE_AWAY))
                - int(metric.get("markout_e6", 0))
                - int(gas.get("gas_usdc_e6", 0))
            )
            edges[(window, scenario)] = WindowEdge(
                window=window,
                scenario=scenario,
                sample_days=days,
                sample_net_e6=sample_net,
                daily_net_e6=int(round(sample_net / days)),
                gas_e6=int(gas.get("gas_usdc_e6", 0)),
            )
    return edges


def _simulate(
    path_name: str,
    windows: tuple[str, ...],
    scenario: str,
    start_capital_e6: int,
    edges: dict[tuple[str, str], WindowEdge],
) -> FlowRow:
    capital = float(start_capital_e6)
    external_capital = float(start_capital_e6)
    cumulative_pnl = 0.0
    net_flow = 0.0
    peak_capital = capital
    max_drawdown = 0.0
    aprs: list[float] = []
    inflow_days = 0
    outflow_days = 0
    floor_days = 0

    for window in windows:
        edge = edges[(window, scenario)]
        raw_pnl = float(edge.daily_net_e6)
        pnl = max(raw_pnl, MIN_CAPITAL_E6 - capital)
        capital += pnl
        cumulative_pnl += pnl
        if capital <= MIN_CAPITAL_E6:
            capital = float(MIN_CAPITAL_E6)
            floor_days += 1
        peak_capital = max(peak_capital, capital)
        max_drawdown = min(max_drawdown, (capital - peak_capital) / peak_capital if peak_capital else 0.0)

        apr = (pnl * YEAR_DAYS) / capital if capital > 0 else -1.0
        aprs.append(apr)
        if apr >= ENTRY_APR:
            flow = min(capital * INFLOW_RATE, MAX_CAPITAL_E6 - capital)
            if flow > 0:
                inflow_days += 1
                capital += flow
                external_capital += flow
                net_flow += flow
        elif apr < EXIT_APR:
            flow = min(capital * OUTFLOW_RATE, max(0.0, capital - MIN_CAPITAL_E6))
            if flow > 0:
                outflow_days += 1
                capital -= flow
                external_capital -= flow
                net_flow -= flow

    ending_apr = (edges[(windows[-1], scenario)].daily_net_e6 * YEAR_DAYS) / capital if capital > 0 else -1.0
    return FlowRow(
        path=path_name,
        scenario=scenario,
        start_capital_e6=start_capital_e6,
        ending_capital_e6=int(round(capital)),
        cumulative_pnl_e6=int(round(cumulative_pnl)),
        net_flow_e6=int(round(net_flow)),
        min_apr=min(aprs) if aprs else 0.0,
        median_apr=statistics.median(aprs) if aprs else 0.0,
        ending_apr=ending_apr,
        max_drawdown=max_drawdown,
        inflow_days=inflow_days,
        outflow_days=outflow_days,
        exit_floor_days=floor_days,
        status=_status(capital, external_capital, cumulative_pnl, outflow_days, floor_days),
    )


def _status(capital: float, external_capital: float, cumulative_pnl: float, outflow_days: int, floor_days: int) -> str:
    if floor_days > 0:
        return "capital floor hit"
    if outflow_days > 0 and capital < external_capital:
        return "capital leaving"
    if cumulative_pnl < 0:
        return "loss-making"
    return "capital retained"


def _fixture_duration_days(root: Path, window: str) -> float:
    events, _ = fixture_events(root, window)
    if len(events) < 2:
        return 0.0
    return (events[-1].t_ms - events[0].t_ms) / 86_400_000


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: float) -> str:
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Simulate LP capital response to measured PegGuard economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "lp_flow_response_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "lp_flow_response_report.json")
    args = parser.parse_args()
    report = compute(root, args.economic_tests_json, args.live_status_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"lp flow response rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
