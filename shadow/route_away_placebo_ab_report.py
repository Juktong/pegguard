from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C


TREATMENT_FEE_PIPS = 500


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute(proxy_paths: list[Path], treatment_fee_pips: int = TREATMENT_FEE_PIPS) -> dict:
    rows = []
    for path in proxy_paths:
        proxy = load_json(path)
        if not proxy:
            continue
        row = _placebo_row(path, proxy, treatment_fee_pips)
        if row:
            rows.append(row)
    max_false = max((float(row["false_route_away_rate"]) for row in rows), default=0.0)
    max_abs_shift = max((abs(float(row["share_shift_pp"])) for row in rows), default=0.0)
    return {
        "complete": len(rows) >= 2,
        "not_route_away_evidence": True,
        "model": (
            "adjacent equal-length A/A placebo derived from nested fee-tier route proxy lookbacks; "
            "prior half = 100k-window minus current 50k-window"
        ),
        "treatment_fee_pips": treatment_fee_pips,
        "rows": rows,
        "max_false_route_away_rate": max_false,
        "max_abs_share_shift_pp": max_abs_shift,
        "note": (
            "This is a noise-floor test for the controlled route-away estimator. "
            "No PegGuard fee changed in these windows, so any route-away value is natural fee-tier share drift."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away A/A Placebo",
        "",
        "This report applies the controlled route-away treatment-share estimator to",
        "adjacent equal-length fee-tier proxy windows where no PegGuard fee changed.",
        "It is a noise-floor check for the future controlled A/B, not route-away",
        "evidence.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Treatment tier: {int(report.get('treatment_fee_pips', 0)) / 100:.2f} bps",
        f"- Max false route-away: {_pct(report.get('max_false_route_away_rate'))}",
        f"- Max absolute treatment-share shift: {float(report.get('max_abs_share_shift_pp', 0)):.2f} pp",
        "",
        "| Pair | Chain | Prior window | Current window | Prior total | Current total | Prior treatment share | Current treatment share | Share shift | False routed away | False route-away rate |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {row['chain']} | {row['prior_window']} | {row['current_window']} | "
            f"{_usd(row['prior_total_notional_e6'])} | {_usd(row['current_total_notional_e6'])} | "
            f"{_pct(row['prior_treatment_share'])} | {_pct(row['current_treatment_share'])} | "
            f"{float(row['share_shift_pp']):+.2f} pp | {_usd(row['false_routed_away_e6'])} | "
            f"{_pct(row['false_route_away_rate'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- This uses real fee-tier flow, but it has no PegGuard treatment and no fee-change intervention.",
            "- A future controlled route-away result should clear this placebo drift scale before being treated as strong evidence.",
            "- Positive `false routed away` means the 5 bps share fell from the prior half to the current half even though no treatment changed.",
            "- This complements, but cannot replace, `docs/route_away_ab.md` with nonzero baseline and treatment notional.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _placebo_row(path: Path, proxy: dict, treatment_fee_pips: int) -> dict | None:
    current, full = _nested_pair(proxy)
    if not current or not full:
        return None
    prior = _subtract_window(full, current)
    prior_total = int(prior.get("total_notional_e6", 0))
    current_total = int(current.get("total_notional_e6", 0))
    prior_treatment = _tier_notional(prior, treatment_fee_pips)
    current_treatment = _tier_notional(current, treatment_fee_pips)
    prior_share = prior_treatment / prior_total if prior_total else 0.0
    current_share = current_treatment / current_total if current_total else 0.0
    expected_current_treatment = int(current_total * prior_share)
    false_routed_away = max(0, expected_current_treatment - current_treatment)
    false_rate = false_routed_away / expected_current_treatment if expected_current_treatment else 0.0
    return {
        "source": str(path),
        "pair": str(proxy.get("pair", "n/a")),
        "chain": str(proxy.get("chain", "n/a")),
        "treatment_fee_pips": treatment_fee_pips,
        "prior_lookback_blocks": int(full.get("lookback_blocks", 0)) - int(current.get("lookback_blocks", 0)),
        "current_lookback_blocks": int(current.get("lookback_blocks", 0)),
        "prior_window": _window(prior),
        "current_window": _window(current),
        "prior_total_notional_e6": prior_total,
        "current_total_notional_e6": current_total,
        "prior_treatment_notional_e6": prior_treatment,
        "current_treatment_notional_e6": current_treatment,
        "prior_treatment_share": prior_share,
        "current_treatment_share": current_share,
        "share_shift_pp": (current_share - prior_share) * 100,
        "expected_current_treatment_e6": expected_current_treatment,
        "false_routed_away_e6": false_routed_away,
        "false_route_away_rate": false_rate,
    }


def _nested_pair(proxy: dict) -> tuple[dict | None, dict | None]:
    windows = sorted(
        (row for row in proxy.get("comparison_windows", []) if row.get("lookback_blocks")),
        key=lambda row: int(row.get("lookback_blocks", 0)),
    )
    by_lookback = {int(row.get("lookback_blocks", 0)): row for row in windows}
    for lookback in sorted(by_lookback):
        full = by_lookback.get(lookback * 2)
        if full is not None:
            return by_lookback[lookback], full
    return None, None


def _subtract_window(full: dict, current: dict) -> dict:
    tiers = []
    current_by_fee = {int(row.get("fee_pips", 0)): row for row in current.get("tiers", [])}
    for full_tier in full.get("tiers", []):
        fee = int(full_tier.get("fee_pips", 0))
        current_tier = current_by_fee.get(fee, {})
        notional = max(0, int(full_tier.get("notional_e6", 0)) - int(current_tier.get("notional_e6", 0)))
        swaps = max(0, int(full_tier.get("swaps", 0)) - int(current_tier.get("swaps", 0)))
        tiers.append({"fee_pips": fee, "notional_e6": notional, "swaps": swaps})
    total = sum(int(row.get("notional_e6", 0)) for row in tiers)
    for row in tiers:
        row["volume_share"] = int(row.get("notional_e6", 0)) / total if total else 0.0
    return {
        "lookback_blocks": int(full.get("lookback_blocks", 0)) - int(current.get("lookback_blocks", 0)),
        "start_block": full.get("start_block"),
        "end_block": int(current.get("start_block", 0)) - 1 if current.get("start_block") else None,
        "duration_hours": max(0.0, float(full.get("duration_hours", 0)) - float(current.get("duration_hours", 0))),
        "total_notional_e6": total,
        "tiers": tiers,
    }


def _tier_notional(window: dict, fee_pips: int) -> int:
    for row in window.get("tiers", []):
        if int(row.get("fee_pips", 0)) == fee_pips:
            return int(row.get("notional_e6", 0))
    return 0


def _window(row: dict) -> str:
    start = row.get("start_block")
    end = row.get("end_block")
    if start is None or end is None:
        return f"{int(row.get('lookback_blocks', 0)):,} blocks"
    return f"{int(start):,}-{int(end):,}"


def _usd(value: object) -> str:
    value_e6 = int(value)
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    return f"{float(value or 0):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compute equal-window route-away A/A placebo from route proxy artifacts")
    parser.add_argument(
        "--proxy-json",
        type=Path,
        action="append",
        default=[],
        help="route_away_proxy JSON artifact; repeat for each pair",
    )
    parser.add_argument("--treatment-fee-pips", type=int, default=TREATMENT_FEE_PIPS)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_placebo_ab_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_placebo_ab_report.json")
    args = parser.parse_args()
    paths = args.proxy_json or [root / "docs" / "route_away_proxy.json", root / "docs" / "route_away_proxy_weth_usdt.json"]
    report = compute(paths, args.treatment_fee_pips)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away A/A placebo={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
