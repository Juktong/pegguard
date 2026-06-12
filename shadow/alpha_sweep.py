from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from . import constants as C
from .parity import _load_json
from .pipeline import ReplayMetrics, replay_rows_exact


DEFAULT_ALPHAS = "1/4,3/8,1/2,5/8,3/4,7/8,1,5/4"
DEFAULT_PRECISION_FLOOR_BPS = 9_000
DEFAULT_VOL_PRECISION_FLOOR_BPS = 9_500


@dataclass(frozen=True)
class AlphaResult:
    alpha: Fraction
    calm: ReplayMetrics
    vol: ReplayMetrics
    feasible: bool

    @property
    def score_bps(self) -> int:
        if not self.feasible:
            return -1
        total_extra = self.calm.extra_e6 + self.vol.extra_e6
        total_markout = abs(self.calm.truth_markout_e6) + abs(self.vol.truth_markout_e6)
        return (total_extra * 10_000) // total_markout if total_markout else 0

    def as_dict(self) -> dict[str, object]:
        return {
            "alpha": str(self.alpha),
            "alpha_float": float(self.alpha),
            "feasible": self.feasible,
            "score_capture_bps": self.score_bps,
            "calm": _metrics_dict(self.calm),
            "vol": _metrics_dict(self.vol),
        }


def parse_alpha(value: str) -> Fraction:
    value = value.strip()
    if not value:
        raise ValueError("empty alpha")
    return Fraction(value)


def sweep_alphas(
    root: Path,
    alphas: list[Fraction],
    precision_floor_bps: int,
    vol_precision_floor_bps: int,
) -> list[AlphaResult]:
    calm_rows = _load_json(root / "test" / "fixtures" / "calm_0530.json")
    calm_truth = _load_json(root / "test" / "fixtures" / "calm_0530_truth.json")
    vol_rows = _load_json(root / "test" / "fixtures" / "vol_0523_hot90m.json")
    vol_truth = _load_json(root / "test" / "fixtures" / "vol_0523_truth.json")

    results: list[AlphaResult] = []
    for alpha in alphas:
        calm = replay_rows_exact(calm_rows, calm_truth, include_quantiles=False, alpha_num=alpha.numerator, alpha_den=alpha.denominator)
        vol = replay_rows_exact(vol_rows, vol_truth, include_quantiles=False, alpha_num=alpha.numerator, alpha_den=alpha.denominator)
        feasible = calm.precision_bps >= precision_floor_bps and vol.precision_bps >= vol_precision_floor_bps
        results.append(AlphaResult(alpha=alpha, calm=calm, vol=vol, feasible=feasible))
    return sorted(results, key=lambda r: (r.feasible, r.score_bps, r.vol.capture_truth_bps), reverse=True)


def compute(
    root: Path,
    alphas: list[Fraction] | None = None,
    precision_floor_bps: int = DEFAULT_PRECISION_FLOOR_BPS,
    vol_precision_floor_bps: int = DEFAULT_VOL_PRECISION_FLOOR_BPS,
) -> dict:
    alphas = alphas or [parse_alpha(value) for value in DEFAULT_ALPHAS.split(",")]
    results = sweep_alphas(root, alphas, precision_floor_bps, vol_precision_floor_bps)
    return {
        "precision_floor_bps": precision_floor_bps,
        "vol_precision_floor_bps": vol_precision_floor_bps,
        "default_alpha": "1/2",
        "rows": [result.as_dict() for result in results],
    }


def render_markdown(results: list[AlphaResult], top_n: int, precision_floor_bps: int, vol_precision_floor_bps: int) -> str:
    selected = [r for r in results if r.feasible][:top_n]
    lines = [
        "# Alpha Backtest Sweep",
        "",
        "Fixtures: `calm_0530` and `vol_0523_hot90m` with checked-in truth rows.",
        f"Selection rule: maximize combined truth-capture among candidates with calm precision >= {precision_floor_bps / 100:.2f}% and volatile precision >= {vol_precision_floor_bps / 100:.2f}%.",
        "",
        "## Selected",
        "",
        "| Rank | Alpha | Combined capture | Calm precision | Calm capture | Vol precision | Vol capture |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, result in enumerate(selected, start=1):
        lines.append(_row(idx, result))
    if not selected:
        lines.append("| - | - | - | - | - | - | - |")

    lines.extend(
        [
            "",
            "## Full Sweep",
            "",
            "| Rank | Alpha | Combined capture | Calm precision | Calm capture | Vol precision | Vol capture |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for idx, result in enumerate(results, start=1):
        lines.append(_row(idx, result))
    lines.append("")
    return "\n".join(lines)


def markdown(report: dict, top_n: int = 3) -> str:
    results = [_result_from_dict(row) for row in report.get("rows", [])]
    return render_markdown(
        results,
        top_n,
        int(report.get("precision_floor_bps", DEFAULT_PRECISION_FLOOR_BPS)),
        int(report.get("vol_precision_floor_bps", DEFAULT_VOL_PRECISION_FLOOR_BPS)),
    )


def write_outputs(report: dict, out_md: Path, out_json: Path, top_n: int = 3) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report, top_n), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(idx: int, result: AlphaResult) -> str:
    return (
        f"| {idx} | {result.alpha} | {_pct(result.score_bps)} | "
        f"{_pct(result.calm.precision_bps)} | {_pct(result.calm.capture_truth_bps)} | "
        f"{_pct(result.vol.precision_bps)} | {_pct(result.vol.capture_truth_bps)} |"
    )


def _pct(bps: int) -> str:
    if bps < 0:
        return "n/a"
    return f"{bps / 100:.2f}%"


def _metrics_dict(metrics: ReplayMetrics) -> dict[str, int]:
    return {
        "rows": metrics.rows,
        "valid_rows": metrics.valid_rows,
        "priced_rows": metrics.priced_rows,
        "charged_rows": metrics.charged_rows,
        "precision_bps": metrics.precision_bps,
        "capture_truth_bps": metrics.capture_truth_bps,
        "premium_total_e6": metrics.premium_total_e6,
        "premium_correct_e6": metrics.premium_correct_e6,
        "extra_e6": metrics.extra_e6,
        "truth_markout_e6": metrics.truth_markout_e6,
        "dev_mae_e2": metrics.dev_mae_e2,
    }


def _result_from_dict(row: dict) -> AlphaResult:
    return AlphaResult(
        alpha=Fraction(str(row["alpha"])),
        calm=_metrics_from_dict(row["calm"]),
        vol=_metrics_from_dict(row["vol"]),
        feasible=bool(row["feasible"]),
    )


def _metrics_from_dict(row: dict) -> ReplayMetrics:
    return ReplayMetrics(
        rows=int(row["rows"]),
        valid_rows=int(row["valid_rows"]),
        priced_rows=int(row["priced_rows"]),
        charged_rows=int(row["charged_rows"]),
        premium_total_e6=int(row["premium_total_e6"]),
        premium_correct_e6=int(row["premium_correct_e6"]),
        charged_agree_rows=0,
        truth_markout_e6=int(row["truth_markout_e6"]),
        extra_e6=int(row["extra_e6"]),
        dev_mae_e2=int(row["dev_mae_e2"]),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep PegGuard alpha candidates against checked-in truth fixtures")
    parser.add_argument("--alphas", default=DEFAULT_ALPHAS, help="comma-separated fractions, e.g. 1/4,1/2,3/4,1")
    parser.add_argument("--top-n", type=int, default=3)
    parser.add_argument("--precision-floor-bps", type=int, default=DEFAULT_PRECISION_FLOOR_BPS)
    parser.add_argument("--vol-precision-floor-bps", type=int, default=DEFAULT_VOL_PRECISION_FLOOR_BPS)
    parser.add_argument("--out-md", type=Path, default=Path("docs/alpha_sweep.md"))
    parser.add_argument("--out-json", type=Path, default=Path("docs/alpha_sweep.json"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = C.repo_root()
    alphas = [parse_alpha(value) for value in args.alphas.split(",")]
    report = compute(root, alphas, args.precision_floor_bps, args.vol_precision_floor_bps)
    write_outputs(report, args.out_md, args.out_json, args.top_n)

    selected = [_result_from_dict(row) for row in report["rows"] if row["feasible"]][: args.top_n]
    for result in selected:
        print(f"{result.alpha} capture={result.score_bps / 100:.2f}% calm_precision={result.calm.precision_bps / 100:.2f}% vol_precision={result.vol.precision_bps / 100:.2f}%")


if __name__ == "__main__":
    main()
