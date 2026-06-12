from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C


SHARE_ASSUMPTIONS = (0.05, 0.10, 0.25, 0.50)


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def compute(route_share_json: Path, route_break_even_json: Path) -> dict:
    share = load_json(route_share_json)
    break_even = load_json(route_break_even_json)
    noise_rows = _noise_rows(share)
    mde_rows = _mde_rows(noise_rows)
    economic_rows = _economic_rows(mde_rows, break_even)
    return {
        "model": (
            "controlled route-away A/B minimum-detectable-effect grid. It converts real fee-tier "
            "placebo share drift into route-away rates under assumed treatment shares, then compares "
            "those rates with same-swap route-away break-even thresholds."
        ),
        "route_share_source": str(route_share_json),
        "route_break_even_source": str(route_break_even_json),
        "share_assumptions": list(SHARE_ASSUMPTIONS),
        "noise_rows": noise_rows,
        "mde_rows": mde_rows,
        "economic_rows": economic_rows,
        "complete": bool(share.get("complete")) and len(noise_rows) >= 2 and len(economic_rows) > 0,
    }


def markdown(report: dict) -> str:
    lines = [
        "# Controlled Route-Away Power",
        "",
        "This report turns the real route-share placebo drift into minimum",
        "detectable route-away rates for a future PegGuard-vs-baseline A/B.",
        "It does not count as controlled route-away evidence; it is the power",
        "check that says how large a treatment-share drop must be before it is",
        "bigger than ordinary fee-tier share movement.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Route-share source: `{report.get('route_share_source', 'n/a')}`",
        f"- Break-even source: `{report.get('route_break_even_source', 'n/a')}`",
        "",
        "## Placebo Noise",
        "",
        "| Pair | Noise basis | Share drift |",
        "|---|---|---:|",
    ]
    for row in report.get("noise_rows", []):
        lines.append(f"| {row['pair']} | {row['noise_basis']} | {float(row['noise_share']):.2%} |")

    lines.extend(
        [
            "",
            "## Minimum Detectable Route-Away",
            "",
            "| Pair | Noise basis | Assumed pre treatment share | MDE route-away | Status |",
            "|---|---|---:|---:|---|",
        ]
    )
    for row in report.get("mde_rows", []):
        lines.append(
            f"| {row['pair']} | {row['noise_basis']} | {float(row['pre_treatment_share']):.2%} | "
            f"{_rate(row['mde_route_away_rate'])} | {row['status']} |"
        )

    lines.extend(
        [
            "",
            "## Economics Comparison",
            "",
            "| Window | Pair | Noise basis | Pre treatment share | MDE route-away | Zero-net threshold | Static-parity threshold | Interpretation |",
            "|---|---|---|---:|---:|---:|---:|---|",
        ]
    )
    for row in report.get("economic_rows", []):
        lines.append(
            f"| {row['window']} | {row['pair']} | {row['noise_basis']} | "
            f"{float(row['pre_treatment_share']):.2%} | {_rate(row['mde_route_away_rate'])} | "
            f"{_rate(row.get('charged_flow_zero_rate'))} | {_rate(row.get('charged_flow_static_parity_rate'))} | "
            f"{row['interpretation']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- If MDE is above the break-even threshold, a clean statistical signal would arrive only after economically material route loss.",
            "- Smaller treatment-share assumptions make the A/B harder because the same absolute share drift maps to a larger route-away rate.",
            "- Use this to choose windows and target routing share before running `docs/route_away_ab.md`; do not use it as calibration input.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _noise_rows(share: dict) -> list[dict]:
    rows: list[dict] = []
    for summary in share.get("pair_summaries", []):
        pair = str(summary.get("pair", "n/a"))
        rows.append(
            {
                "pair": pair,
                "noise_basis": "5 bps share drift",
                "noise_share": float(summary.get("share_5bps_spread_pp", 0)) / 100,
            }
        )
        rows.append(
            {
                "pair": pair,
                "noise_basis": "30 bps+ share drift",
                "noise_share": float(summary.get("share_high_fee_spread_pp", 0)) / 100,
            }
        )
    return rows


def _mde_rows(noise_rows: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for noise in noise_rows:
        for pre_share in SHARE_ASSUMPTIONS:
            mde = float(noise["noise_share"]) / pre_share if pre_share > 0 else None
            rows.append(
                {
                    "pair": noise["pair"],
                    "noise_basis": noise["noise_basis"],
                    "noise_share": noise["noise_share"],
                    "pre_treatment_share": pre_share,
                    "mde_route_away_rate": mde,
                    "status": _mde_status(mde),
                }
            )
    return rows


def _economic_rows(mde_rows: list[dict], break_even: dict) -> list[dict]:
    rows: list[dict] = []
    for threshold in break_even.get("rows", []):
        zero_rate = _optional_float(threshold.get("charged_flow_zero_rate"))
        parity_rate = _optional_float(threshold.get("charged_flow_static_parity_rate"))
        for mde in mde_rows:
            mde_rate = _optional_float(mde.get("mde_route_away_rate"))
            rows.append(
                {
                    "window": str(threshold.get("window", "n/a")),
                    "strategy": str(threshold.get("strategy", "n/a")),
                    "pair": mde["pair"],
                    "noise_basis": mde["noise_basis"],
                    "pre_treatment_share": mde["pre_treatment_share"],
                    "mde_route_away_rate": mde_rate,
                    "charged_flow_zero_rate": zero_rate,
                    "charged_flow_static_parity_rate": parity_rate,
                    "interpretation": _interpret(mde_rate, zero_rate, parity_rate),
                }
            )
    return rows


def _interpret(mde: float | None, zero_rate: float | None, parity_rate: float | None) -> str:
    if mde is None:
        return "missing MDE"
    if mde > 1:
        return "not detectable at this treatment share"
    if zero_rate is not None and mde > zero_rate:
        return "detectable only after zero-net route loss"
    if parity_rate is not None and mde > parity_rate:
        return "detectable only after static-parity route loss"
    return "detectable before modeled break-even"


def _mde_status(mde: float | None) -> str:
    if mde is None:
        return "missing"
    if mde > 1:
        return ">100%; not detectable"
    if mde > 0.5:
        return "very coarse"
    if mde > 0.2:
        return "coarse"
    return "usable"


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rate(value: object) -> str:
    if value is None:
        return ">100%" if value is None else "n/a"
    rate = float(value)
    if rate > 1:
        return ">100%"
    return f"{rate:.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compute controlled route-away A/B power from placebo share drift")
    parser.add_argument("--route-share-json", type=Path, default=root / "docs" / "route_share_stability_report.json")
    parser.add_argument("--route-break-even-json", type=Path, default=root / "docs" / "route_away_break_even.json")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "route_ab_power_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "route_ab_power_report.json")
    args = parser.parse_args()
    report = compute(args.route_share_json, args.route_break_even_json)
    write_outputs(report, args.out_md, args.out_json)
    print(f"route-ab power={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
