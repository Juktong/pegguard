from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


SCENARIOS = (
    ("observed", 0.0, 0.0),
    ("miss 25pct correct", 0.25, 0.0),
    ("miss 50pct correct", 0.50, 0.0),
    ("false 25pct correct", 0.0, 0.25),
    ("false 50pct correct", 0.0, 0.50),
    ("false 100pct correct", 0.0, 1.00),
    ("miss 25pct + false 25pct", 0.25, 0.25),
)


@dataclass(frozen=True)
class SignalQualityStressRow:
    window: str
    scenario: str
    rows: int
    notional_e6: int
    markout_e6: int
    base_fee_e6: int
    observed_extra_e6: int
    retained_correct_extra_e6: int
    wrong_extra_e6: int
    injected_wrong_extra_e6: int
    stressed_extra_e6: int
    precision: float | None
    raw_capture: float | None
    aligned_capture: float | None
    raw_net_e6: int
    raw_net_bps: float
    aligned_net_e6: int
    aligned_net_bps: float
    raw_minus_aligned_bps: float
    status: str


def compute(economic_tests_json: Path, scenarios: tuple[tuple[str, float, float], ...] = SCENARIOS) -> dict:
    data = _load_json(economic_tests_json)
    rows = [
        _row(metric, label, miss_correct, false_wrong)
        for metric in data.get("benchmarks", [])
        if _is_selected(metric)
        for label, miss_correct, false_wrong in scenarios
    ]
    return {
        "source": str(economic_tests_json),
        "model": (
            "Signal-quality stress on selected PegGuard rows. Miss scenarios remove a share of truth-correct premium. "
            "False scenarios add wrong-side premium equal to a share of observed truth-correct premium. "
            "Raw net counts every premium dollar; aligned net counts retained correcting premium and subtracts wrong premium as an economic penalty."
        ),
        "scenarios": [
            {"label": label, "miss_correct_share": miss_correct, "false_wrong_share": false_wrong}
            for label, miss_correct, false_wrong in scenarios
        ],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Signal Quality Stress",
        "",
        "This report tests how fragile PegGuard economics are to weaker signal",
        "quality. It is a Goodhart check: a bad signal can raise raw fees while",
        "precision and aligned economics deteriorate.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Scenario | Precision | Raw capture | Aligned capture | Raw net | Raw net bps | Aligned net | Aligned net bps | Gap | Status |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['scenario']} | {_pct(row.get('precision'))} | "
            f"{_pct(row.get('raw_capture'))} | {_pct(row.get('aligned_capture'))} | "
            f"{_usd(int(row['raw_net_e6']))} | {float(row['raw_net_bps']):.2f} | "
            f"{_usd(int(row['aligned_net_e6']))} | {float(row['aligned_net_bps']):.2f} | "
            f"{float(row['raw_minus_aligned_bps']):.2f} bps | {row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `raw capture` and `raw net` count every premium dollar, including wrong-side premium.",
            "- `aligned capture` counts retained truth-correcting premium minus wrong-side premium, floored at zero.",
            "- `aligned net` subtracts wrong-side premium as an economic penalty. This is intentionally stricter than LP fee accounting.",
            "- A scenario where raw net improves while aligned net falls is a precision failure, not an economic win.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(metric: dict, label: str, miss_correct: float, false_wrong: float) -> SignalQualityStressRow:
    notional = int(metric.get("notional_e6", 0))
    markout = int(metric.get("markout_e6", 0))
    base = int(metric.get("base_fee_e6", 0))
    observed_extra = int(metric.get("extra_e6", 0))
    premium_total = int(metric.get("premium_total_e6", observed_extra))
    correct = int(metric.get("premium_correct_e6", 0))
    current_wrong = max(0, premium_total - correct)
    retained_correct = int(round(correct * (1 - miss_correct)))
    missed_correct = correct - retained_correct
    injected_wrong = int(round(correct * false_wrong))
    wrong = current_wrong + injected_wrong
    stressed_extra = max(0, observed_extra - missed_correct + injected_wrong)
    stressed_premium_total = retained_correct + wrong
    precision = (retained_correct / stressed_premium_total) if stressed_premium_total else None
    raw_net = base + stressed_extra - markout
    aligned_extra = max(0, retained_correct - wrong)
    aligned_net = base + aligned_extra - markout
    return SignalQualityStressRow(
        window=str(metric.get("window", "")),
        scenario=label,
        rows=int(metric.get("rows", 0)),
        notional_e6=notional,
        markout_e6=markout,
        base_fee_e6=base,
        observed_extra_e6=observed_extra,
        retained_correct_extra_e6=retained_correct,
        wrong_extra_e6=wrong,
        injected_wrong_extra_e6=injected_wrong,
        stressed_extra_e6=stressed_extra,
        precision=precision,
        raw_capture=(stressed_extra / abs(markout)) if markout else None,
        aligned_capture=(aligned_extra / abs(markout)) if markout else None,
        raw_net_e6=raw_net,
        raw_net_bps=_bps(raw_net, notional),
        aligned_net_e6=aligned_net,
        aligned_net_bps=_bps(aligned_net, notional),
        raw_minus_aligned_bps=_bps(raw_net - aligned_net, notional),
        status=_status(precision, aligned_net),
    )


def _status(precision: float | None, aligned_net_e6: int) -> str:
    if precision is None:
        return "no premium"
    if precision < 0.90:
        return "precision broken"
    if aligned_net_e6 < 0:
        return "aligned net negative"
    return "passes stress"


def _is_selected(metric: dict) -> bool:
    return str(metric.get("name", "")) in {"PegGuard selected", "PegGuard live shadow"}


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 <= 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = C.repo_root()
    default_tag = "live-shadow-20260607T082122Z"
    parser = argparse.ArgumentParser(description="Generate signal-quality stress economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "signal_quality_stress_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "signal_quality_stress_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"signal-quality stress rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
