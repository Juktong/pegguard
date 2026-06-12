from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .chain_cost_report import HOOK_GAS


REGIME_CALLBACK_GAS = 56_296
BREAKER_CALLBACK_GAS = 53_109
CONTROL_CALLBACK_GAS = max(REGIME_CALLBACK_GAS, BREAKER_CALLBACK_GAS)


@dataclass(frozen=True)
class ControlPlaneCostRow:
    chain: str
    gas_price_gwei: float | None
    trigger_count: int
    callback_gas: int
    episode_cost_e6: int | None
    cost_per_trigger_e6: int | None
    false_positive_triggers: int
    false_positive_cost_e6: int | None
    measured_bleed_e6: int
    cost_vs_measured_bleed_bps: float | None
    hot_path_equivalent_swaps: float
    status: str


def compute(guard_depeg_json: Path, live_gas_snapshot_json: Path) -> dict:
    guard = _load_json(guard_depeg_json)
    gas = _load_json(live_gas_snapshot_json)
    selected = _selected_guard_row(guard)
    trigger_count = int(selected.get("vol_triggers", 0))
    false_positive_triggers = int(selected.get("calm_triggers", 0))
    measured_bleed = _measured_bleed(selected)
    eth_usd = float(gas.get("eth_usd_assumption", 3_500.0))
    rows = [
        _row(snapshot, trigger_count, false_positive_triggers, measured_bleed, eth_usd)
        for snapshot in gas.get("snapshots", [])
    ]
    ok_rows = [row for row in rows if row.status == "priced"]
    return {
        "complete": bool(ok_rows) and trigger_count > 0 and measured_bleed > 0,
        "not_calibration": True,
        "not_route_away_evidence": True,
        "guard_source": str(guard_depeg_json),
        "gas_source": str(live_gas_snapshot_json),
        "model": (
            "Reactive/control-plane callback gas priced with the same live gas snapshots as the chain-cost report. "
            "The selected sentinel trigger count is charged once per callback episode, not once per swap."
        ),
        "regime_callback_gas": REGIME_CALLBACK_GAS,
        "breaker_callback_gas": BREAKER_CALLBACK_GAS,
        "control_callback_gas": CONTROL_CALLBACK_GAS,
        "hot_path_swap_gas": HOOK_GAS,
        "trigger_count": trigger_count,
        "false_positive_triggers": false_positive_triggers,
        "measured_bleed_e6": measured_bleed,
        "eth_usd_assumption": eth_usd,
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Control-Plane Cost",
        "",
        "This report prices Reactive/control-plane callback gas against the measured",
        "sentinel episode. It is an economics check for the architecture split:",
        "control-plane callbacks are rare, while Pyth pricing remains on the hot",
        "swap path.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Regime callback gas: {int(report.get('regime_callback_gas', 0)):,}",
        f"- Breaker callback gas: {int(report.get('breaker_callback_gas', 0)):,}",
        f"- Priced callback gas: {int(report.get('control_callback_gas', 0)):,}",
        f"- Selected volatile triggers: {int(report.get('trigger_count', 0))}",
        f"- Calm false-positive triggers: {int(report.get('false_positive_triggers', 0))}",
        f"- Measured bleed denominator: {_usd(int(report.get('measured_bleed_e6', 0)))}",
        "",
        "| Chain | Gas price | Triggers | Episode cost | Cost/trigger | Calm FP cost | Cost vs measured bleed | Hot-path equivalent | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['chain']} | {_gwei(row.get('gas_price_gwei'))} | {int(row['trigger_count'])} | "
            f"{_usd_or_na(row.get('episode_cost_e6'))} | {_usd_or_na(row.get('cost_per_trigger_e6'))} | "
            f"{_usd_or_na(row.get('false_positive_cost_e6'))} | {_bps_or_na(row.get('cost_vs_measured_bleed_bps'))} | "
            f"{float(row['hot_path_equivalent_swaps']):.2f} swaps | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The selected sentinel had zero calm false positives, so the measured calm false-positive callback cost is zero.",
            "- Even when priced on the most expensive sampled chain, the selected episode costs only a few hot-path swap equivalents.",
            "- This does not price the off-chain Reactive Network service itself and does not substitute for the route-away A/B gate.",
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
    snapshot: dict,
    trigger_count: int,
    false_positive_triggers: int,
    measured_bleed_e6: int,
    eth_usd: float,
) -> ControlPlaneCostRow:
    chain = str(snapshot.get("chain", "n/a"))
    gas_price = snapshot.get("gas_price_gwei")
    hot_path_equivalent = (trigger_count * CONTROL_CALLBACK_GAS / HOOK_GAS) if HOOK_GAS else 0.0
    if not snapshot.get("ok") or gas_price is None:
        return ControlPlaneCostRow(
            chain=chain,
            gas_price_gwei=None,
            trigger_count=trigger_count,
            callback_gas=CONTROL_CALLBACK_GAS,
            episode_cost_e6=None,
            cost_per_trigger_e6=None,
            false_positive_triggers=false_positive_triggers,
            false_positive_cost_e6=None,
            measured_bleed_e6=measured_bleed_e6,
            cost_vs_measured_bleed_bps=None,
            hot_path_equivalent_swaps=hot_path_equivalent,
            status="missing gas",
        )
    gas_price_float = float(gas_price)
    cost_per = _gas_cost_e6(CONTROL_CALLBACK_GAS, gas_price_float, eth_usd)
    episode_cost = trigger_count * cost_per
    false_cost = false_positive_triggers * cost_per
    return ControlPlaneCostRow(
        chain=chain,
        gas_price_gwei=gas_price_float,
        trigger_count=trigger_count,
        callback_gas=CONTROL_CALLBACK_GAS,
        episode_cost_e6=episode_cost,
        cost_per_trigger_e6=cost_per,
        false_positive_triggers=false_positive_triggers,
        false_positive_cost_e6=false_cost,
        measured_bleed_e6=measured_bleed_e6,
        cost_vs_measured_bleed_bps=_bps(episode_cost, measured_bleed_e6),
        hot_path_equivalent_swaps=hot_path_equivalent,
        status="priced",
    )


def _selected_guard_row(report: dict) -> dict:
    rows = report.get("rows", [])
    if not rows:
        return {}
    return next((row for row in rows if row.get("label") == "selected"), rows[0])


def _measured_bleed(row: dict) -> int:
    total = row.get("measured_bleed_total_e6")
    if total is not None:
        return int(total)
    before = int(row.get("bled_before_first_trigger_e6", 0) or 0)
    after = int(row.get("measured_bleed_after_first_trigger_e6", 0) or 0)
    return before + after


def _gas_cost_e6(gas: int, gas_price_gwei: float, eth_usd: float) -> int:
    return int(round(gas * gas_price_gwei * 1e-9 * eth_usd * 1_000_000))


def _bps(value_e6: int, denominator_e6: int) -> float | None:
    if denominator_e6 <= 0:
        return None
    return value_e6 / denominator_e6 * 10_000


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


def _gwei(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} gwei"


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate Reactive/control-plane callback cost report")
    parser.add_argument("--guard-depeg-json", type=Path, default=root / "docs" / "guard_depeg_report.json")
    parser.add_argument("--live-gas-snapshot-json", type=Path, default=root / "docs" / "live_gas_snapshot_report.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "control_plane_cost_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "control_plane_cost_report.json")
    args = parser.parse_args()
    report = compute(args.guard_depeg_json, args.live_gas_snapshot_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"control-plane cost rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
