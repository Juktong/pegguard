from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C


NORMAL_STABLE_MIN_BPS = 0.0
NORMAL_STABLE_MAX_BPS = 0.35
FEED_NOISE_BPS = 0.2
GUARD_TRIP_BPS = 50
AMM_BASKET_CAPTURE_PCT = 0.006
AMM_PLUS_CEX_CAPTURE_PCT = 0.063
AMM_PLUS_CEX_CORRELATION = 0.58


def compute(root: Path | None = None) -> dict:
    root = root or C.repo_root()
    parameters_path = root / "research" / "PARAMETERS.md"
    _assert_provenance(parameters_path)
    trip_margin = GUARD_TRIP_BPS / NORMAL_STABLE_MAX_BPS
    best_directional_capture = max(AMM_BASKET_CAPTURE_PCT, AMM_PLUS_CEX_CAPTURE_PCT)
    complete = (
        trip_margin > 100
        and best_directional_capture < 0.10
        and AMM_PLUS_CEX_CORRELATION < 0.75
    )
    return {
        "complete": complete,
        "not_calibration": True,
        "mode": "GUARD stable-pair opportunity audit",
        "source": str(parameters_path),
        "directional_fee_policy": "disabled",
        "normal_stable_min_bps": NORMAL_STABLE_MIN_BPS,
        "normal_stable_max_bps": NORMAL_STABLE_MAX_BPS,
        "feed_noise_bps": FEED_NOISE_BPS,
        "guard_trip_bps": GUARD_TRIP_BPS,
        "trip_to_normal_ratio": trip_margin,
        "best_directional_capture_pct": best_directional_capture,
        "best_directional_correlation": AMM_PLUS_CEX_CORRELATION,
        "rows": [
            {
                "measurement": "normal stable cross-venue deviation",
                "value": f"{NORMAL_STABLE_MIN_BPS:.3f}-{NORMAL_STABLE_MAX_BPS:.2f} bps",
                "economic_read": "below feed noise; do not charge directional premium",
            },
            {
                "measurement": "feed noise",
                "value": f"about {FEED_NOISE_BPS:.1f} bps",
                "economic_read": "same order as the stable-pair signal",
            },
            {
                "measurement": "AMM basket directional capture",
                "value": f"{AMM_BASKET_CAPTURE_PCT:.2%}",
                "economic_read": "too small for HARVEST mode",
            },
            {
                "measurement": "AMM plus CEX capture",
                "value": f"{AMM_PLUS_CEX_CAPTURE_PCT:.2%}; corr {AMM_PLUS_CEX_CORRELATION:.2f}",
                "economic_read": "still weak and roughly random",
            },
            {
                "measurement": "GUARD trip margin",
                "value": f"{trip_margin:.1f}x over normal max",
                "economic_read": "breaker signal is separated from normal stable noise",
            },
        ],
        "limitation": (
            "This is a provenance audit of the stable-pair no-harvest decision. "
            "It is not a dual-feed stablecoin depeg replay; that remains a separate open item."
        ),
    }


def markdown(report: dict) -> str:
    lines = [
        "# GUARD Stable Opportunity Audit",
        "",
        "This report records the measured economics behind disabling directional",
        "premiums in GUARD mode. It is non-calibration evidence sourced from",
        "`research/PARAMETERS.md`.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Directional fee policy: {report.get('directional_fee_policy', 'n/a')}",
        f"- Normal stable deviation: {float(report.get('normal_stable_min_bps', 0)):.3f}-{float(report.get('normal_stable_max_bps', 0)):.2f} bps",
        f"- Best directional capture measured: {float(report.get('best_directional_capture_pct', 0)):.2%}",
        f"- GUARD trip margin: {float(report.get('trip_to_normal_ratio', 0)):.1f}x over normal max",
        f"- Limitation: {report.get('limitation', 'n/a')}",
        "",
        "| Measurement | Value | Economic read |",
        "|---|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(f"| {row['measurement']} | {row['value']} | {row['economic_read']} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Stable-pair directional fees are disabled because measured capture is too weak relative to noise.",
            "- GUARD mode should only arm the depeg circuit breaker; it should not tax ordinary stable-pair flow.",
            "- A future dual-feed stablecoin depeg fixture can extend this report, but should not change this no-harvest conclusion without new provenance.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _assert_provenance(parameters_path: Path) -> None:
    text = parameters_path.read_text(encoding="utf-8")
    needles = [
        "Normal stable-pair cross-venue deviations were 0.000-0.35 bps",
        "feed noise was about 0.2 bps",
        "Stable pairs showed no directional fuel",
        "AMM basket capture was 0.6%",
        "adding CEX reached only 6.3%",
        "58% correlation",
    ]
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise RuntimeError("stable-opportunity provenance missing: " + ", ".join(missing))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate GUARD stable-pair opportunity audit")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "stable_opportunity_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "stable_opportunity_report.json")
    args = parser.parse_args()

    report = compute(root)
    write_outputs(report, args.out_md, args.out_json)
    print(f"status={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
