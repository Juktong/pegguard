from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS


MARKOUT_MULTIPLIERS = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)


@dataclass(frozen=True)
class MarkoutSensitivityRow:
    window: str
    strategy: str
    markout_multiplier: float
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    scaled_markout_e6: int
    net_e6: int
    net_bps: float
    capture_truth_bps: int | None
    required_base_pips_zero: int
    required_base_pips_1bps: int
    surplus_vs_zero_pips: int
    status: str


def compute(economic_tests_json: Path, multipliers: tuple[float, ...] = MARKOUT_MULTIPLIERS) -> dict:
    data = _load_json(economic_tests_json)
    rows = [
        _row(metric, multiplier)
        for metric in data.get("benchmarks", [])
        if _is_selected(metric)
        for multiplier in multipliers
    ]
    return {
        "source": str(economic_tests_json),
        "model": (
            "selected PegGuard benchmark with truth markout rescaled by fixed multipliers. "
            "Base fee and dynamic premium are held constant so this isolates sensitivity to markout measurement."
        ),
        "markout_multipliers": list(multipliers),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Truth Markout Sensitivity",
        "",
        "This report stresses the measured PegGuard economics against truth-markout",
        "uncertainty. It holds base fees and dynamic premium fixed, then rescales",
        "truth markout to show how quickly the economic result changes.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Strategy | Markout x | Net | Net bps | Capture | Required base for 0 bps | Surplus vs 0 bps | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['strategy']} | {float(row['markout_multiplier']):.2f}x | "
            f"{_usd(int(row['net_e6']))} | {float(row['net_bps']):.2f} | "
            f"{_pct_bps(row.get('capture_truth_bps'))} | {_pips(int(row['required_base_pips_zero']))} | "
            f"{_signed_pips(int(row['surplus_vs_zero_pips']))} | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `0.50x` is an optimistic case where measured markout was twice the true drag.",
            "- `2.00x` is a conservative case where measured markout understated drag by half.",
            "- `Required base for 0 bps` shows the base fee needed to break even after the scaled markout and measured dynamic premium.",
            "- This is not calibration; it is a robustness check for the truth-denominated economics.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(metric: dict, multiplier: float) -> MarkoutSensitivityRow:
    notional = int(metric.get("notional_e6", 0))
    base = int(metric.get("base_fee_e6", 0))
    extra = int(metric.get("extra_e6", 0))
    scaled_markout = int(round(int(metric.get("markout_e6", 0)) * multiplier))
    net = base + extra - scaled_markout
    required_zero = _required_base_pips(notional, scaled_markout, extra, 0)
    required_one = _required_base_pips(notional, scaled_markout, extra, 1)
    return MarkoutSensitivityRow(
        window=str(metric.get("window", "")),
        strategy=str(metric.get("name", "")),
        markout_multiplier=multiplier,
        notional_e6=notional,
        base_fee_e6=base,
        extra_e6=extra,
        scaled_markout_e6=scaled_markout,
        net_e6=net,
        net_bps=_bps(net, notional),
        capture_truth_bps=(extra * 10_000 // abs(scaled_markout)) if scaled_markout and extra else None,
        required_base_pips_zero=required_zero,
        required_base_pips_1bps=required_one,
        surplus_vs_zero_pips=BASE_FEE_PIPS - required_zero,
        status="net positive" if net >= 0 else "net negative",
    )


def _required_base_pips(notional_e6: int, markout_e6: int, extra_e6: int, target_net_bps: int) -> int:
    if notional_e6 <= 0:
        return 0
    target_net_e6 = (notional_e6 * target_net_bps) // 10_000
    required_e6 = markout_e6 + target_net_e6 - extra_e6
    if required_e6 <= 0:
        return 0
    return (required_e6 * 1_000_000 + notional_e6 - 1) // notional_e6


def _is_selected(metric: dict) -> bool:
    return str(metric.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 <= 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pips(value: int) -> str:
    return f"{value / 100:.2f} bps"


def _signed_pips(value: int) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}{abs(value) / 100:.2f} bps"


def _pct_bps(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value) / 100:.2f}%"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Generate truth-markout sensitivity report")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "markout_sensitivity_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "markout_sensitivity_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"markout sensitivity rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
