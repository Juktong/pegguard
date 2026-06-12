from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class SignalMarginRow:
    window: str
    rows: int
    notional_e6: int
    markout_e6: int
    base_fee_e6: int
    premium_total_e6: int
    correct_extra_e6: int
    wrong_extra_e6: int
    observed_precision: float | None
    aligned_extra_e6: int
    aligned_net_e6: int
    aligned_net_bps: float
    required_aligned_extra_e6: int
    precision_breakeven: float | None
    precision_headroom_pp: float | None
    max_missed_correct_share: float | None
    max_false_wrong_share_of_correct: float | None
    status: str


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    rows = [_row(metric) for metric in data.get("benchmarks", []) if _is_selected(metric)]
    return {
        "source": str(economic_tests_json),
        "model": (
            "Aligned economics count truth-correct premium minus wrong-side premium. "
            "The margin is the share of observed correct premium that can be missed or matched by new wrong premium before aligned net reaches zero."
        ),
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Signal Margin",
        "",
        "This report converts the observed precision/capture result into safety",
        "margins: how much correct premium can be missed, or wrong premium can be",
        "added, before aligned net economics reach zero.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Precision | Break-even precision | Precision headroom | Aligned net | Aligned net bps | Required aligned extra | Max missed correct | Max false wrong/correct | Status |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {_pct(row.get('observed_precision'))} | {_pct(row.get('precision_breakeven'))} | "
            f"{_pp(row.get('precision_headroom_pp'))} | {_usd(int(row['aligned_net_e6']))} | "
            f"{float(row['aligned_net_bps']):.2f} | {_usd(int(row['required_aligned_extra_e6']))} | "
            f"{_pct(row.get('max_missed_correct_share'))} | {_pct(row.get('max_false_wrong_share_of_correct'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `Break-even precision` assumes the observed premium total is fixed, but shifts premium from correct to wrong-side flow.",
            "- `Max missed correct` and `Max false wrong/correct` are equal under this linear aligned-net model.",
            "- Negative margin means base fee plus aligned premium is already below measured truth markout.",
            "- This is a robustness diagnostic only; it does not alter calibration constants.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(metric: dict) -> SignalMarginRow:
    notional = int(metric.get("notional_e6", 0))
    markout = int(metric.get("markout_e6", 0))
    base = int(metric.get("base_fee_e6", 0))
    total = int(metric.get("premium_total_e6", metric.get("extra_e6", 0)))
    correct = int(metric.get("premium_correct_e6", 0))
    wrong = max(0, total - correct)
    aligned_extra = max(0, correct - wrong)
    required = max(0, markout - base)
    margin_e6 = correct - wrong - required
    margin_share = (margin_e6 / correct) if correct > 0 else None
    precision = (correct / total) if total > 0 else None
    breakeven_precision = _breakeven_precision(total, required)
    return SignalMarginRow(
        window=str(metric.get("window", "")),
        rows=int(metric.get("rows", 0)),
        notional_e6=notional,
        markout_e6=markout,
        base_fee_e6=base,
        premium_total_e6=total,
        correct_extra_e6=correct,
        wrong_extra_e6=wrong,
        observed_precision=precision,
        aligned_extra_e6=aligned_extra,
        aligned_net_e6=base + aligned_extra - markout,
        aligned_net_bps=_bps(base + aligned_extra - markout, notional),
        required_aligned_extra_e6=required,
        precision_breakeven=breakeven_precision,
        precision_headroom_pp=(precision - breakeven_precision) if precision is not None and breakeven_precision is not None else None,
        max_missed_correct_share=margin_share,
        max_false_wrong_share_of_correct=margin_share,
        status=_status(margin_share, base + aligned_extra - markout),
    )


def _breakeven_precision(premium_total_e6: int, required_aligned_extra_e6: int) -> float | None:
    if premium_total_e6 <= 0:
        return None
    if required_aligned_extra_e6 <= 0:
        return 0.5
    return (premium_total_e6 + required_aligned_extra_e6) / (2 * premium_total_e6)


def _status(margin_share: float | None, aligned_net_e6: int) -> str:
    if margin_share is None:
        return "no dynamic premium"
    if aligned_net_e6 < 0:
        return "already below aligned break-even"
    if margin_share < 0.10:
        return "thin margin"
    return "positive margin"


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


def _pp(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f} pp"


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
    parser = argparse.ArgumentParser(description="Generate signal margin economics")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "signal_margin_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "signal_margin_report.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"signal margin rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
