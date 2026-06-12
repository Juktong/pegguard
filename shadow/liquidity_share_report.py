from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events


CAPITALS_E6 = [2_500_000_000, 10_000_000_000, 25_000_000_000, 100_000_000_000]
DEPTH_BAND_BPS = 50
YEAR_HOURS = 365 * 24


@dataclass(frozen=True)
class ShareRow:
    window: str
    capital_e6: int
    depth_band_bps: int
    active_depth_e6: int
    depth_share: float
    duration_hours: float
    full_flow_notional_e6: int
    realized_notional_e6: int
    full_flow_net_e6: int
    pro_rata_net_e6: int
    pro_rata_base_e6: int
    pro_rata_extra_e6: int
    pro_rata_markout_e6: int
    net_apr: float | None
    annualized_net_e6: int | None


@dataclass(frozen=True)
class CapacityRow:
    pair: str
    capital_e6: int
    depth_band_bps: int
    active_depth_e6: int
    depth_share: float


def compute(
    root: Path,
    economic_tests_json: Path,
    live_status_json: Path,
    depth_proxy_json: Path,
    cross_pair_depth_proxy_json: Path | None = None,
) -> dict:
    economic_tests = _load_json(economic_tests_json)
    live_status = _load_json(live_status_json)
    depth_proxy = _load_json(depth_proxy_json)
    cross_pair_depth_proxy = _load_json(cross_pair_depth_proxy_json) if cross_pair_depth_proxy_json else {}
    active_depth_e6 = _band_depth(depth_proxy, DEPTH_BAND_BPS)
    rows = [
        asdict(row)
        for row in _share_rows(root, economic_tests, live_status, active_depth_e6)
    ]
    capacity = [
        asdict(row)
        for proxy in (depth_proxy, cross_pair_depth_proxy)
        for row in _capacity_rows(proxy, DEPTH_BAND_BPS)
        if proxy
    ]
    return {
        "depth_pair": depth_proxy.get("pair", "n/a"),
        "depth_band_bps": DEPTH_BAND_BPS,
        "depth_block": depth_proxy.get("block_number"),
        "rows": rows,
        "capacity": capacity,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Liquidity Share Sizing",
        "",
        "This report converts measured PegGuard economics into a pro-rata depth-share",
        "view for small LP positions. Depth share uses current v3 active-depth proxy",
        "data, so it is a capacity/sizing model, not exact v4 liquidity ownership.",
        "",
        f"- Depth pair: {report.get('depth_pair', 'n/a')}",
        f"- Depth band: {int(report.get('depth_band_bps', 0))} bps",
        f"- Depth block: {report.get('depth_block', 'n/a')}",
        "",
        "## Pro-Rata Economics",
        "",
        "| Window | Capital | Depth share | Duration | Realized notional | Pro-rata base | Pro-rata extra | Pro-rata markout | Pro-rata net | Stress APR | Annualized stress net |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {_usd(int(row['capital_e6']))} | {float(row['depth_share']):.2%} | "
            f"{float(row['duration_hours']):.2f}h | {_usd(int(row['realized_notional_e6']))} | "
            f"{_usd(int(row['pro_rata_base_e6']))} | {_usd(int(row['pro_rata_extra_e6']))} | "
            f"{_usd(int(row['pro_rata_markout_e6']))} | {_usd(int(row['pro_rata_net_e6']))} | "
            f"{_pct(row.get('net_apr'))} | {_usd_or_na(row.get('annualized_net_e6'))} |"
        )
    lines.extend(
        [
            "",
            "## Depth Capacity",
            "",
            "| Pair | Capital | Depth band | Active depth | Depth share |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in report.get("capacity", []):
        lines.append(
            f"| {row['pair']} | {_usd(int(row['capital_e6']))} | {int(row['depth_band_bps'])} bps | "
            f"{_usd(int(row['active_depth_e6']))} | {float(row['depth_share']):.2%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `depth_share = capital / (capital + active_depth)` using the selected active-depth band.",
            "- Pro-rata rows scale full-flow replay economics by depth share; they are useful for sizing, not route elasticity.",
            "- Stress APR annualizes short windows only to compare sample intensity; do not quote it as expected return.",
            "- Cross-pair rows are capacity-only until matching truth replay fixtures exist for that pair.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _share_rows(root: Path, economic_tests: dict, live_status: dict, active_depth_e6: int) -> list[ShareRow]:
    durations = _fixture_durations(root)
    if float(live_status.get("observed_span_hours", 0)) > 0:
        durations["live shadow"] = float(live_status.get("observed_span_hours", 0))
    rows = []
    for metric in economic_tests.get("benchmarks", []):
        if not _is_selected_metric(metric):
            continue
        window = str(metric["window"])
        duration_hours = durations.get(window, 0.0)
        for capital_e6 in CAPITALS_E6:
            rows.append(_share_row(metric, capital_e6, active_depth_e6, duration_hours))
    return rows


def _share_row(metric: dict, capital_e6: int, active_depth_e6: int, duration_hours: float) -> ShareRow:
    share = _depth_share(capital_e6, active_depth_e6)
    base = int(int(metric.get("base_fee_e6", 0)) * share)
    extra = int(int(metric.get("extra_e6", 0)) * share)
    markout = int(int(metric.get("markout_e6", 0)) * share)
    net = base + extra - markout
    annualized = None
    apr = None
    if duration_hours > 0 and capital_e6 > 0:
        annualized = int(net * (YEAR_HOURS / duration_hours))
        apr = annualized / capital_e6
    return ShareRow(
        window=str(metric["window"]),
        capital_e6=capital_e6,
        depth_band_bps=DEPTH_BAND_BPS,
        active_depth_e6=active_depth_e6,
        depth_share=share,
        duration_hours=duration_hours,
        full_flow_notional_e6=int(metric.get("notional_e6", 0)),
        realized_notional_e6=int(int(metric.get("notional_e6", 0)) * share),
        full_flow_net_e6=int(metric.get("net_e6", 0)),
        pro_rata_net_e6=net,
        pro_rata_base_e6=base,
        pro_rata_extra_e6=extra,
        pro_rata_markout_e6=markout,
        net_apr=apr,
        annualized_net_e6=annualized,
    )


def _capacity_rows(depth_proxy: dict, band_bps: int) -> list[CapacityRow]:
    active_depth = _band_depth(depth_proxy, band_bps)
    return [
        CapacityRow(
            pair=str(depth_proxy.get("pair", "n/a")),
            capital_e6=capital,
            depth_band_bps=band_bps,
            active_depth_e6=active_depth,
            depth_share=_depth_share(capital, active_depth),
        )
        for capital in CAPITALS_E6
    ]


def _is_selected_metric(metric: dict) -> bool:
    name = str(metric.get("name", ""))
    return name == "PegGuard selected" or name == "PegGuard live shadow"


def _fixture_durations(root: Path) -> dict[str, float]:
    durations = {}
    for window in ("calm", "vol"):
        events, _ = fixture_events(root, window)
        if len(events) >= 2:
            durations[window] = (events[-1].t_ms - events[0].t_ms) / 3_600_000
    return durations


def _band_depth(depth_proxy: dict, band_bps: int) -> int:
    return int(depth_proxy.get("band_totals", {}).get(str(band_bps), 0))


def _depth_share(capital_e6: int, active_depth_e6: int) -> float:
    if capital_e6 <= 0:
        return 0.0
    return capital_e6 / (capital_e6 + active_depth_e6) if active_depth_e6 > 0 else 1.0


def _load_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _usd_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return _usd(int(value))


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Estimate pro-rata LP economics from active-depth share")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy.json")
    parser.add_argument("--cross-pair-depth-proxy-json", type=Path, default=root / "docs" / "depth_proxy_weth_usdt.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "liquidity_share_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "liquidity_share_report.json")
    args = parser.parse_args()
    report = compute(root, args.economic_tests_json, args.live_status_json, args.depth_proxy_json, args.cross_pair_depth_proxy_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"liquidity share report: rows={len(report['rows'])} capacity={len(report['capacity'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
