from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

from . import constants as C


TARGET_TREATMENT_NOTIONAL_E6 = 100_000_000_000
MAX_RECOMMENDED_TREATMENT_SHARE = 0.25


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute(route_ab_power_json: Path, route_proxy_jsons: list[Path]) -> dict:
    power = load_json(route_ab_power_json)
    proxy_rows = [_proxy_row(path) for path in route_proxy_jsons]
    proxy_rows = [row for row in proxy_rows if row]
    by_pair = {row["pair"]: row for row in proxy_rows}
    candidate_rows = _candidate_rows(power, by_pair)
    recommendations = _recommendations(candidate_rows)
    return {
        "model": (
            "controlled route-away A/B sizing plan. It combines route-away power rows "
            "with real fee-tier proxy notional to estimate treatment-share and window "
            "requirements for a future controlled experiment."
        ),
        "route_ab_power_source": str(route_ab_power_json),
        "route_proxy_sources": [str(path) for path in route_proxy_jsons],
        "target_treatment_notional_e6": TARGET_TREATMENT_NOTIONAL_E6,
        "max_recommended_treatment_share": MAX_RECOMMENDED_TREATMENT_SHARE,
        "proxy_rows": proxy_rows,
        "candidate_rows": candidate_rows,
        "recommendations": recommendations,
        "complete": bool(power.get("complete")) and len(proxy_rows) >= 2 and len(candidate_rows) > 0,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Controlled Route-Away A/B Sizing",
        "",
        "This is a planning report for the real controlled route-away test.",
        "It does not count as route-away evidence; it estimates which pair and",
        "treatment-share assumptions are measurable before the controlled A/B is run.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Target treatment notional per window: {_usd(int(report.get('target_treatment_notional_e6', 0)))}",
        f"- Recommended treatment-share cap: {float(report.get('max_recommended_treatment_share', 0)):.2%}",
        f"- Power source: `{report.get('route_ab_power_source', 'n/a')}`",
        "",
        "## Proxy Notional",
        "",
        "| Pair | Chain | Windows | Median daily notional | Min daily notional | Max daily notional |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in report.get("proxy_rows", []):
        lines.append(
            f"| {row['pair']} | {row['chain']} | {row['windows']} | "
            f"{_usd(int(row['median_daily_notional_e6']))} | {_usd(int(row['min_daily_notional_e6']))} | "
            f"{_usd(int(row['max_daily_notional_e6']))} |"
        )

    lines.extend(
        [
            "",
            "## Candidate Windows",
            "",
            "| Pair | Econ window | Noise basis | Treatment share | MDE route-away | Interpretation | Treatment/day | Hours for target |",
            "|---|---|---|---:|---:|---|---:|---:|",
        ]
    )
    for row in report.get("candidate_rows", []):
        lines.append(
            f"| {row['pair']} | {row['window']} | {row['noise_basis']} | "
            f"{float(row['pre_treatment_share']):.2%} | {_rate(row.get('mde_route_away_rate'))} | "
            f"{row['interpretation']} | {_usd(int(row['estimated_treatment_notional_per_day_e6']))} | "
            f"{_hours(row.get('hours_for_target_treatment_notional'))} |"
        )

    lines.extend(
        [
            "",
            "## Recommendations",
            "",
            "| Rank | Pair | Treatment share | Noise basis | MDE route-away | Hours for target | Reason |",
            "|---:|---|---:|---|---:|---:|---|",
        ]
    )
    for index, row in enumerate(report.get("recommendations", []), start=1):
        lines.append(
            f"| {index} | {row['pair']} | {float(row['pre_treatment_share']):.2%} | "
            f"{row['noise_basis']} | {_rate(row.get('mde_route_away_rate'))} | "
            f"{_hours(row.get('hours_for_target_treatment_notional'))} | {row['reason']} |"
        )

    lines.extend(
        [
            "",
            "## Env Starting Points",
            "",
            "| Pair | Chain | Baseline pool | Quote token index | Quote decimals |",
            "|---|---|---|---:|---:|",
        ]
    )
    for row in report.get("recommendations", []):
        lines.append(
            f"| {row['pair']} | {row.get('chain', 'n/a')} | `{row.get('baseline_pool', 'n/a')}` | "
            f"{_na(row.get('quote_token_index'))} | {_na(row.get('quote_decimals'))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Prefer rows marked `detectable before modeled break-even`; other rows are diagnostic only.",
            "- Very small treatment shares inflate MDE because ordinary route-share drift becomes a larger fraction of treatment volume.",
            "- This report does not replace `docs/route_away_ab.json`; it only sizes the experiment that will populate it.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _proxy_row(path: Path) -> dict:
    data = load_json(path)
    windows = data.get("comparison_windows", [])
    daily_values = []
    for window in windows:
        duration = float(window.get("duration_hours", 0))
        notional = int(window.get("total_notional_e6", 0))
        if duration > 0 and notional > 0:
            daily_values.append(notional * 24 / duration)
    if not daily_values:
        duration = float(data.get("duration_hours", 0))
        notional = int(data.get("total_notional_e6", 0))
        if duration > 0 and notional > 0:
            daily_values.append(notional * 24 / duration)
    if not daily_values:
        return {}
    return {
        "source": str(path),
        "pair": str(data.get("pair", "n/a")),
        "chain": str(data.get("chain", "n/a")),
        "baseline_pool": _pool_for_fee(data, 500) or "n/a",
        "quote_token_index": data.get("quote_token_index"),
        "quote_decimals": data.get("quote_decimals"),
        "windows": len(daily_values),
        "median_daily_notional_e6": int(statistics.median(daily_values)),
        "min_daily_notional_e6": int(min(daily_values)),
        "max_daily_notional_e6": int(max(daily_values)),
    }


def _pool_for_fee(route_proxy: dict, fee_pips: int) -> str | None:
    for row in route_proxy.get("tiers", []):
        if int(row.get("fee_pips", 0)) == fee_pips and row.get("pool"):
            return str(row["pool"])
    return None


def _candidate_rows(power: dict, proxy_by_pair: dict[str, dict]) -> list[dict]:
    rows = []
    for item in power.get("economic_rows", []):
        pair = str(item.get("pair", ""))
        proxy = proxy_by_pair.get(pair)
        if not proxy:
            continue
        share = float(item.get("pre_treatment_share", 0))
        median_daily = int(proxy.get("median_daily_notional_e6", 0))
        treatment_per_day = int(median_daily * share)
        hours_for_target = None
        if treatment_per_day > 0:
            hours_for_target = TARGET_TREATMENT_NOTIONAL_E6 / (treatment_per_day / 24)
        rows.append(
            {
                "pair": pair,
                "chain": str(proxy.get("chain", "n/a")),
                "baseline_pool": str(proxy.get("baseline_pool", "n/a")),
                "quote_token_index": proxy.get("quote_token_index"),
                "quote_decimals": proxy.get("quote_decimals"),
                "window": str(item.get("window", "n/a")),
                "noise_basis": str(item.get("noise_basis", "n/a")),
                "pre_treatment_share": share,
                "mde_route_away_rate": item.get("mde_route_away_rate"),
                "charged_flow_zero_rate": item.get("charged_flow_zero_rate"),
                "charged_flow_static_parity_rate": item.get("charged_flow_static_parity_rate"),
                "interpretation": str(item.get("interpretation", "n/a")),
                "median_daily_notional_e6": median_daily,
                "estimated_treatment_notional_per_day_e6": treatment_per_day,
                "hours_for_target_treatment_notional": hours_for_target,
                "rank_score": _rank_score(item, hours_for_target),
            }
        )
    rows.sort(key=lambda row: (row["rank_score"], row["hours_for_target_treatment_notional"] or 10**9))
    return rows


def _recommendations(candidate_rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    rows = []
    for row in candidate_rows:
        pair = str(row.get("pair", ""))
        if pair in seen:
            continue
        if row.get("interpretation") != "detectable before modeled break-even":
            continue
        if float(row.get("pre_treatment_share", 0)) > MAX_RECOMMENDED_TREATMENT_SHARE:
            continue
        rec = dict(row)
        rec["reason"] = "lowest-noise measurable row at or below the pilot treatment-share cap"
        rows.append(rec)
        seen.add(pair)
    return rows


def _rank_score(row: dict, hours_for_target: float | None) -> tuple[int, int, float, float]:
    interpretation = str(row.get("interpretation", ""))
    interp_rank = 0 if interpretation == "detectable before modeled break-even" else 1
    mde = _optional_float(row.get("mde_route_away_rate"))
    mde_rank = 0 if mde is not None and mde <= 0.20 else 1
    hour_value = hours_for_target if hours_for_target is not None else 10**9
    return (interp_rank, mde_rank, mde if mde is not None else 10**9, hour_value)


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rate(value: object) -> str:
    rate = _optional_float(value)
    if rate is None:
        return "n/a"
    if rate > 1:
        return ">100%"
    return f"{rate:.2%}"


def _hours(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}h"


def _na(value: object) -> str:
    return "n/a" if value is None else str(value)


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Size the controlled route-away A/B experiment")
    parser.add_argument("--route-ab-power-json", type=Path, default=root / "docs" / "route_ab_power_report.json")
    parser.add_argument(
        "--route-proxy-json",
        type=Path,
        action="append",
        default=[
            root / "docs" / "route_away_proxy.json",
            root / "docs" / "route_away_proxy_weth_usdt.json",
        ],
    )
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_ab_sizing_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_ab_sizing_report.json")
    args = parser.parse_args()
    report = compute(args.route_ab_power_json, args.route_proxy_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-ab sizing={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
