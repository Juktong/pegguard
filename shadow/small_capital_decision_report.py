from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


PROFILES = (
    ("micro passive", 2_500_000_000, "micro passive"),
    ("small active", 10_000_000_000, "small active"),
    ("focused active", 25_000_000_000, "focused active"),
    ("depth-share $100k", 100_000_000_000, None),
)


@dataclass(frozen=True)
class DecisionRow:
    profile: str
    capital_e6: int
    policy: str | None
    recommendation: str
    best_calm_apr: float | None
    best_vol_apr: float | None
    best_live_apr: float | None
    viable_rows_1x: int
    viable_rows_2x: int
    min_required_turnover_10pct: float | None
    min_required_daily_volume_10pct_e6: int | None
    best_calm_position_bps: float | None
    best_vol_position_bps: float | None
    worst_vol_position_bps: float | None
    live_pro_rata_net_e6: int | None
    live_provisional: bool
    rationale: str


def compute(
    pilot_deployability_json: Path,
    position_shadow_json: Path,
    target_return_json: Path,
    live_status_json: Path,
) -> dict:
    pilot = _load_json(pilot_deployability_json)
    position = _load_json(position_shadow_json)
    target = _load_json(target_return_json)
    live_status = _load_json(live_status_json)
    rows = [
        asdict(
            _decision_row(
                profile,
                capital_e6,
                policy,
                pilot,
                position,
                target,
                live_status,
            )
        )
        for profile, capital_e6, policy in PROFILES
    ]
    return {
        "model": (
            "decision matrix distilled from pilot deployability, target-return, "
            "and position-shadow economics. This is a go/no-go summary, not calibration."
        ),
        "pilot_source": str(pilot_deployability_json),
        "position_source": str(position_shadow_json),
        "target_return_source": str(target_return_json),
        "live_status_source": str(live_status_json),
        "live_shadow_complete": bool(live_status.get("complete", False)),
        "rows": rows,
    }


def markdown(report: dict) -> str:
    rows = report.get("rows", [])
    lines = [
        "# Small-Capital Decision Matrix",
        "",
        "This report distills the detailed economic stress reports into a practical",
        "small-capital go/no-go view. It combines deployability APR, required",
        "turnover, position-level inventory plus pro-rata economics, and live-shadow",
        "completeness.",
        "",
        f"- Live shadow complete: {'yes' if report.get('live_shadow_complete') else 'no'}",
        f"- Rows: {len(rows)}",
        "",
        "| Profile | Capital | Recommendation | Best calm APR | Best vol APR | Best live APR | 1x viable | 2x viable | Req. turnover for 10% | Req. daily volume | Best calm position | Best vol position | Live pro-rata | Rationale |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | {_usd(int(row['capital_e6']))} | {row['recommendation']} | "
            f"{_pct_or_na(row.get('best_calm_apr'))} | {_pct_or_na(row.get('best_vol_apr'))} | "
            f"{_pct_or_na(row.get('best_live_apr'))} | {int(row['viable_rows_1x'])} | "
            f"{int(row['viable_rows_2x'])} | {_turnover(row.get('min_required_turnover_10pct'))} | "
            f"{_usd_or_na(row.get('min_required_daily_volume_10pct_e6'))} | "
            f"{_bps_or_na(row.get('best_calm_position_bps'))} | {_bps_or_na(row.get('best_vol_position_bps'))} | "
            f"{_usd_or_na(row.get('live_pro_rata_net_e6'))} | {row['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## Decision Rules",
            "",
            "- `deployable` requires at least one 2x-markout viable row and non-negative volatile evidence.",
            "- `pilot only` means calm-window economics can clear the hurdle, but volatile/live or markout-stress evidence does not.",
            "- `no-go` means the current measured economics do not justify deployment at that capital profile.",
            "- Live-shadow evidence is measured same-swaps evidence and still does not measure real route-away.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _decision_row(
    profile: str,
    capital_e6: int,
    policy: str | None,
    pilot: dict,
    position: dict,
    target: dict,
    live_status: dict,
) -> DecisionRow:
    pilot_rows = [
        row
        for row in pilot.get("rows", [])
        if policy is not None and row.get("policy") == policy and abs(float(row.get("markout_multiplier", 0)) - 1.0) < 1e-9
    ]
    pilot_rows_2x = [
        row
        for row in pilot.get("rows", [])
        if policy is not None and row.get("policy") == policy and float(row.get("markout_multiplier", 0)) >= 2.0
    ]
    viable_1x = sum(1 for row in pilot_rows if row.get("status") == "viable >=10% APR")
    viable_2x = sum(1 for row in pilot_rows_2x if row.get("status") == "viable >=10% APR")
    best_calm = _best_apr(pilot_rows, "calm")
    best_vol = _best_apr(pilot_rows, "vol")
    best_live = _best_apr(pilot_rows, "live shadow")
    min_turnover, min_volume = _target_turnover(target, policy)
    best_calm_position = _best_position_bps(position, "calm", capital_e6)
    best_vol_position = _best_position_bps(position, "vol", capital_e6)
    worst_vol_position = _worst_position_bps(position, "vol", capital_e6)
    live_pro_rata = _live_position_net(position, capital_e6)
    live_provisional = not bool(live_status.get("complete", False))
    recommendation, rationale = _recommendation(
        policy,
        viable_1x,
        viable_2x,
        best_calm,
        best_vol,
        best_live,
        best_vol_position,
        live_provisional,
    )
    return DecisionRow(
        profile=profile,
        capital_e6=capital_e6,
        policy=policy,
        recommendation=recommendation,
        best_calm_apr=best_calm,
        best_vol_apr=best_vol,
        best_live_apr=best_live,
        viable_rows_1x=viable_1x,
        viable_rows_2x=viable_2x,
        min_required_turnover_10pct=min_turnover,
        min_required_daily_volume_10pct_e6=min_volume,
        best_calm_position_bps=best_calm_position,
        best_vol_position_bps=best_vol_position,
        worst_vol_position_bps=worst_vol_position,
        live_pro_rata_net_e6=live_pro_rata,
        live_provisional=live_provisional,
        rationale=rationale,
    )


def _recommendation(
    policy: str | None,
    viable_1x: int,
    viable_2x: int,
    best_calm: float | None,
    best_vol: float | None,
    best_live: float | None,
    best_vol_position: float | None,
    live_provisional: bool,
) -> tuple[str, str]:
    if policy is None:
        return (
            "no-go: sizing stress only",
            "No deployability policy covers this capital size; position-shadow volatile rows are negative.",
        )
    volatile_nonnegative = (best_vol is not None and best_vol >= 0) or (best_vol_position is not None and best_vol_position >= 0)
    live_nonnegative = best_live is not None and best_live >= 0
    if viable_2x > 0 and volatile_nonnegative and live_nonnegative and not live_provisional:
        return "deployable", "Clears the 2x-markout viability check with non-negative volatile and completed live evidence."
    if viable_1x > 0:
        return (
            "pilot only: calm/liquid windows",
            "Clears at least one 1x calm deployment row, but 2x-markout, volatile, or live evidence is not robust.",
        )
    if best_calm is not None and best_calm > 0:
        return (
            "observe only",
            "Measured calm edge is positive, but it does not clear the 10% deployability hurdle.",
        )
    return "no-go", "Current measured APR is negative or unsupported across the deployability rows."


def _best_apr(rows: list[dict], window: str) -> float | None:
    values = [float(row.get("net_apr", 0)) for row in rows if row.get("window") == window]
    return max(values) if values else None


def _target_turnover(target: dict, policy: str | None) -> tuple[float | None, int | None]:
    if policy is None:
        return None, None
    candidates = [
        row
        for row in target.get("rows", [])
        if row.get("policy") == policy
        and abs(float(row.get("target_apr", 0)) - 0.10) < 1e-9
        and row.get("required_turnover_per_day") is not None
    ]
    if not candidates:
        return None, None
    best = min(candidates, key=lambda row: float(row.get("required_turnover_per_day", 0)))
    volume = best.get("required_daily_volume_e6")
    return float(best.get("required_turnover_per_day")), None if volume is None else int(volume)


def _best_position_bps(position: dict, window: str, capital_e6: int) -> float | None:
    values = [
        float(row.get("combined_net_bps"))
        for row in position.get("rows", [])
        if row.get("window") == window
        and int(row.get("capital_e6", 0)) == capital_e6
        and row.get("combined_net_bps") is not None
    ]
    return max(values) if values else None


def _worst_position_bps(position: dict, window: str, capital_e6: int) -> float | None:
    values = [
        float(row.get("combined_net_bps"))
        for row in position.get("rows", [])
        if row.get("window") == window
        and int(row.get("capital_e6", 0)) == capital_e6
        and row.get("combined_net_bps") is not None
    ]
    return min(values) if values else None


def _live_position_net(position: dict, capital_e6: int) -> int | None:
    values = [
        int(row.get("pro_rata_net_e6", 0))
        for row in position.get("rows", [])
        if row.get("window") == "live shadow" and int(row.get("capital_e6", 0)) == capital_e6
    ]
    return values[0] if values else None


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


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} bps"


def _turnover(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x/day"


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Generate small-capital economic go/no-go decision matrix")
    parser.add_argument("--pilot-deployability-json", type=Path, default=root / "docs" / "pilot_deployability_report.json")
    parser.add_argument("--position-shadow-json", type=Path, default=root / "docs" / "position_shadow_report.json")
    parser.add_argument("--target-return-json", type=Path, default=root / "docs" / "target_return_report.json")
    parser.add_argument("--live-status-json", type=Path, default=root / "docs" / default_tag / "status.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "small_capital_decision_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "small_capital_decision_report.json")
    args = parser.parse_args()
    report = compute(
        args.pilot_deployability_json,
        args.position_shadow_json,
        args.target_return_json,
        args.live_status_json,
    )
    write_outputs(report, args.out_md, args.out_json)
    print(f"small-capital decision rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
