from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS

TARGET_NET_BPS = (0, 1, 5)


@dataclass(frozen=True)
class BaseFeeRow:
    window: str
    strategy: str
    notional_e6: int
    markout_e6: int
    extra_e6: int
    current_base_pips: int
    current_net_bps: float
    required_base_pips_zero: int
    required_base_pips_1bps: int
    required_base_pips_5bps: int
    current_surplus_vs_zero_pips: int
    current_surplus_vs_1bps_pips: int
    current_surplus_vs_5bps_pips: int


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    rows = [base_fee_row(row) for row in data.get("benchmarks", []) if _is_selected(row)]
    return {
        "source": str(economic_tests_json),
        "current_base_pips": BASE_FEE_PIPS,
        "target_net_bps": list(TARGET_NET_BPS),
        "rows": [asdict(row) for row in rows],
    }


def base_fee_row(metric: dict) -> BaseFeeRow:
    notional = int(metric.get("notional_e6", 0))
    markout = int(metric.get("markout_e6", 0))
    extra = int(metric.get("extra_e6", 0))
    required = {target: _required_base_pips(notional, markout, extra, target) for target in TARGET_NET_BPS}
    return BaseFeeRow(
        window=str(metric.get("window", "")),
        strategy=str(metric.get("name", "")),
        notional_e6=notional,
        markout_e6=markout,
        extra_e6=extra,
        current_base_pips=BASE_FEE_PIPS,
        current_net_bps=float(metric.get("net_bps", 0)),
        required_base_pips_zero=required[0],
        required_base_pips_1bps=required[1],
        required_base_pips_5bps=required[5],
        current_surplus_vs_zero_pips=BASE_FEE_PIPS - required[0],
        current_surplus_vs_1bps_pips=BASE_FEE_PIPS - required[1],
        current_surplus_vs_5bps_pips=BASE_FEE_PIPS - required[5],
    )


def markdown(report: dict) -> str:
    lines = [
        "# Base-Fee Adequacy",
        "",
        "This report measures whether the configured base fee is sufficient after",
        "truth markout and PegGuard dynamic premium. It is measurement only and does",
        "not change hook constants.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Current base fee: {int(report.get('current_base_pips', BASE_FEE_PIPS)) / 100:.2f} bps",
        "",
        "| Window | Strategy | Current net bps | Required base for 0 bps net | Required base for 1 bps net | Required base for 5 bps net | Surplus vs 0 bps | Surplus vs 1 bps | Surplus vs 5 bps |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['strategy']} | {float(row['current_net_bps']):.2f} | "
            f"{_pips(row['required_base_pips_zero'])} | {_pips(row['required_base_pips_1bps'])} | "
            f"{_pips(row['required_base_pips_5bps'])} | {_signed_pips(row['current_surplus_vs_zero_pips'])} | "
            f"{_signed_pips(row['current_surplus_vs_1bps_pips'])} | {_signed_pips(row['current_surplus_vs_5bps_pips'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Required base fee is computed after applying the measured PegGuard extra premium.",
            "- Negative surplus means the current 5 bps base fee is below the required level for that target.",
            "- A high required base fee may not be routeable; compare this with route-away proxy and controlled route-away results.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _required_base_pips(notional_e6: int, markout_e6: int, extra_e6: int, target_net_bps: int) -> int:
    if notional_e6 <= 0:
        return 0
    target_net_e6 = (notional_e6 * target_net_bps) // 10_000
    required_e6 = markout_e6 + target_net_e6 - extra_e6
    if required_e6 <= 0:
        return 0
    return (required_e6 * 1_000_000 + notional_e6 - 1) // notional_e6


def _is_selected(metric: dict) -> bool:
    name = str(metric.get("name", ""))
    return name == "PegGuard selected" or name == "PegGuard live shadow"


def _pips(value: object) -> str:
    return f"{int(value) / 100:.2f} bps"


def _signed_pips(value: object) -> str:
    integer = int(value)
    sign = "+" if integer >= 0 else "-"
    return f"{sign}{abs(integer) / 100:.2f} bps"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Measure required base fee for PegGuard economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "base_fee_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "base_fee_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"base fee adequacy rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
