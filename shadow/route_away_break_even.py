from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class BreakEvenRow:
    window: str
    strategy: str
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    net_e6: int
    static_net_e6: int
    charged_base_fee_e6: int
    charged_markout_e6: int
    premium_haircut_zero_rate: float | None
    charged_flow_zero_rate: float | None
    charged_flow_static_parity_rate: float | None


def compute(economic_tests_json: Path) -> dict:
    data = _load_json(economic_tests_json)
    rows = [break_even_row(row) for row in data.get("benchmarks", []) if _is_selected(row)]
    return {
        "source": str(economic_tests_json),
        "rows": [asdict(row) for row in rows],
    }


def break_even_row(metric: dict) -> BreakEvenRow:
    base_fee = int(metric.get("base_fee_e6", 0))
    extra = int(metric.get("extra_e6", 0))
    markout = int(metric.get("markout_e6", 0))
    net = int(metric.get("net_e6", base_fee + extra - markout))
    static_net = base_fee - markout
    charged_base = int(metric.get("charged_base_fee_e6", 0))
    charged_markout = int(metric.get("charged_markout_e6", 0))
    removal_drag = charged_base + extra - charged_markout
    return BreakEvenRow(
        window=str(metric.get("window", "")),
        strategy=str(metric.get("name", "")),
        notional_e6=int(metric.get("notional_e6", 0)),
        base_fee_e6=base_fee,
        extra_e6=extra,
        markout_e6=markout,
        net_e6=net,
        static_net_e6=static_net,
        charged_base_fee_e6=charged_base,
        charged_markout_e6=charged_markout,
        premium_haircut_zero_rate=_threshold(net, extra),
        charged_flow_zero_rate=_threshold(net, removal_drag),
        charged_flow_static_parity_rate=_threshold(extra, removal_drag),
    )


def markdown(report: dict) -> str:
    lines = [
        "# Route-Away Break-Even",
        "",
        "This report converts same-swap replay economics into route-away tolerance",
        "thresholds. It is not a substitute for the controlled route-away experiment;",
        "it defines the measured route-away rates that would make the strategy",
        "economically unacceptable.",
        "",
        f"- Source: `{report.get('source', 'n/a')}`",
        "",
        "## Thresholds",
        "",
        "| Window | Strategy | Net | Static net | Extra | Premium-haircut zero-net | Charged-flow zero-net | Charged-flow static parity |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['strategy']} | {_usd(int(row['net_e6']))} | "
            f"{_usd(int(row['static_net_e6']))} | {_usd(int(row['extra_e6']))} | "
            f"{_rate(row.get('premium_haircut_zero_rate'))} | {_rate(row.get('charged_flow_zero_rate'))} | "
            f"{_rate(row.get('charged_flow_static_parity_rate'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `premium-haircut zero-net` assumes base flow and markout remain but premium is lost as charged flow routes away.",
            "- `charged-flow zero-net` removes the same share of charged swaps, including base fee, premium, and truth markout.",
            "- `charged-flow static parity` is the maximum charged-flow removal before PegGuard no longer beats static 5 bps on the same full-flow replay.",
            "- `0.00%` means the measured strategy is already below that floor before route-away.",
            "- `>100%` means the floor survives complete removal under that mechanical model.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _is_selected(metric: dict) -> bool:
    name = str(metric.get("name", ""))
    return name == "PegGuard selected" or name == "PegGuard live shadow"


def _threshold(numerator_e6: int, drag_e6: int) -> float | None:
    if numerator_e6 <= 0:
        return 0.0
    if drag_e6 <= 0:
        return None
    return numerator_e6 / drag_e6


def _rate(value: object) -> str:
    if value is None:
        return ">100%"
    rate = float(value)
    if rate > 1:
        return ">100%"
    return f"{rate:.2%}"


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
    parser = argparse.ArgumentParser(description="Compute PegGuard route-away break-even thresholds")
    parser.add_argument("--economic-tests-json", type=Path, default=root / "docs" / default_tag / "economic_tests.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_away_break_even.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_away_break_even.json")
    args = parser.parse_args()
    report = compute(args.economic_tests_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-away break-even: rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
