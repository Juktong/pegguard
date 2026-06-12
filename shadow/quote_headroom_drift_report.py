from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .quote_headroom_report import compute as compute_headroom


@dataclass(frozen=True)
class QuoteSample:
    pair: str
    amount_in_raw: int
    path: str
    block_tag: str
    generated_at: str
    premium_headroom_bps: float | None
    peg_rank: int | None
    best_fee_pips: int | None
    status: str
    passed: bool


@dataclass(frozen=True)
class DriftRow:
    pair: str
    amount_in_raw: int
    samples: int
    distinct_blocks: int
    first_block_tag: str
    last_block_tag: str
    first_headroom_bps: float | None
    last_headroom_bps: float | None
    min_headroom_bps: float | None
    max_headroom_bps: float | None
    first_to_last_delta_bps: float | None
    all_samples_passed: bool
    passed: bool
    status: str


def compute(root: Path | None = None, paths_by_pair: dict[str, list[Path]] | None = None) -> dict:
    root = root or C.repo_root()
    paths_by_pair = paths_by_pair or default_paths(root)
    samples: list[QuoteSample] = []
    sources = []
    for pair, paths in paths_by_pair.items():
        for path in _dedupe(paths):
            source = _source_row(pair, path)
            sources.append(source)
            if not path.exists():
                continue
            samples.extend(_samples_for_path(pair, path))

    rows = [_drift_row(pair, amount, rows) for (pair, amount), rows in _group_samples(samples).items()]
    distinct_blocks = sorted({sample.block_tag for sample in samples if sample.block_tag and sample.block_tag != "missing"})
    headrooms = [sample.premium_headroom_bps for sample in samples if sample.premium_headroom_bps is not None]
    deltas = [abs(row.first_to_last_delta_bps) for row in rows if row.first_to_last_delta_bps is not None]
    return {
        "model": (
            "time-diverse quote-headroom drift across stored real QuoterV2 snapshots; "
            "this checks routeability budget stability, not controlled route-away elasticity"
        ),
        "complete": bool(rows) and all(row.passed for row in rows) and len({row.pair for row in rows}) >= 2,
        "pairs": sorted({row.pair for row in rows}),
        "sources": sources,
        "samples": [asdict(sample) for sample in samples],
        "rows": [asdict(row) for row in rows],
        "sample_count": len(samples),
        "distinct_blocks": distinct_blocks,
        "distinct_block_count": len(distinct_blocks),
        "passed_rows": sum(1 for row in rows if row.passed),
        "min_headroom_bps": None if not headrooms else min(headrooms),
        "max_abs_first_to_last_delta_bps": None if not deltas else max(deltas),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Headroom Drift",
        "",
        "This report compares every stored real QuoterV2 quote snapshot by pair and",
        "amount. It is routeability-budget evidence across time; it does not measure",
        "controlled route-away elasticity.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Pairs: {', '.join(report.get('pairs', [])) or 'none'}",
        f"- Quote samples: {int(report.get('sample_count', 0))}",
        f"- Distinct blocks: {int(report.get('distinct_block_count', 0))}",
        f"- Passed rows: {int(report.get('passed_rows', 0))}/{len(report.get('rows', []))}",
        f"- Min headroom: {_bps_or_na(report.get('min_headroom_bps'))}",
        f"- Max first-to-last drift: {_bps_or_na(report.get('max_abs_first_to_last_delta_bps'))}",
        "",
        "## Sources",
        "",
        "| Pair | Path | Present | Block | Generated at | Quoted rows |",
        "|---|---|---:|---:|---|---:|",
    ]
    for source in report.get("sources", []):
        lines.append(
            f"| {source['pair']} | `{source['path']}` | {'yes' if source['present'] else 'no'} | "
            f"{source['block_tag']} | {source['generated_at'] or 'n/a'} | {int(source['quoted_rows'])} |"
        )

    lines.extend(
        [
            "",
            "## Drift Rows",
            "",
            "| Pair | Amount in raw | Samples | Blocks | First block | Last block | Min headroom | Max headroom | First-to-last | Status | Passed |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {int(row['amount_in_raw'])} | {int(row['samples'])} | {int(row['distinct_blocks'])} | "
            f"{row['first_block_tag']} | {row['last_block_tag']} | {_bps_or_na(row.get('min_headroom_bps'))} | "
            f"{_bps_or_na(row.get('max_headroom_bps'))} | {_bps_or_na(row.get('first_to_last_delta_bps'))} | "
            f"{row['status']} | {'yes' if row.get('passed') else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Passing rows require at least two distinct quote blocks and positive 5 bps headroom in every sample.",
            "- Large negative drift means routeability budget compressed over time even if the row still passes.",
            "- Same-block stability and this drift report are routeability checks; the controlled A/B remains the route-away proof.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def default_paths(root: Path) -> dict[str, list[Path]]:
    return {
        "WETH/USDC": [
            root / "docs" / "quote_route_quotes.json",
            *sorted((root / "docs" / "quote-snapshots").glob("*/quote_route_quotes_weth_usdc.json")),
        ],
        "WETH/USDT": [
            root / "docs" / "quote_route_quotes_weth_usdt.json",
            *sorted((root / "docs" / "quote-snapshots").glob("*/quote_route_quotes_weth_usdt.json")),
        ],
    }


def _samples_for_path(pair: str, path: Path) -> list[QuoteSample]:
    quote = _load_json(path)
    headroom = compute_headroom(path)
    block_tag = str(quote.get("block_tag", "missing"))
    generated_at = str(quote.get("generated_at") or "")
    samples = []
    for row in headroom.get("rows", []):
        headroom_bps = _optional_float(row.get("premium_headroom_bps"))
        peg_rank = _optional_int(row.get("peg_rank"))
        best_fee = _optional_int(row.get("best_fee_pips"))
        passed = headroom_bps is not None and headroom_bps > 0 and peg_rank == 1 and best_fee == 500
        samples.append(
            QuoteSample(
                pair=pair,
                amount_in_raw=int(row.get("amount_in_raw", 0)),
                path=str(path),
                block_tag=block_tag,
                generated_at=generated_at,
                premium_headroom_bps=headroom_bps,
                peg_rank=peg_rank,
                best_fee_pips=best_fee,
                status=str(row.get("status", "missing")),
                passed=passed,
            )
        )
    return samples


def _drift_row(pair: str, amount: int, rows: list[QuoteSample]) -> DriftRow:
    ordered = sorted(rows, key=_sample_sort_key)
    headrooms = [row.premium_headroom_bps for row in ordered if row.premium_headroom_bps is not None]
    first = ordered[0]
    last = ordered[-1]
    first_headroom = first.premium_headroom_bps
    last_headroom = last.premium_headroom_bps
    delta = None if first_headroom is None or last_headroom is None else last_headroom - first_headroom
    distinct_blocks = len({row.block_tag for row in ordered})
    all_passed = all(row.passed for row in ordered)
    passed = distinct_blocks >= 2 and all_passed
    if distinct_blocks < 2:
        status = "single block only"
    elif not all_passed:
        status = "headroom failed"
    elif delta is not None and delta < 0:
        status = "positive headroom, compressed"
    else:
        status = "positive headroom"
    return DriftRow(
        pair=pair,
        amount_in_raw=amount,
        samples=len(ordered),
        distinct_blocks=distinct_blocks,
        first_block_tag=first.block_tag,
        last_block_tag=last.block_tag,
        first_headroom_bps=first_headroom,
        last_headroom_bps=last_headroom,
        min_headroom_bps=None if not headrooms else min(headrooms),
        max_headroom_bps=None if not headrooms else max(headrooms),
        first_to_last_delta_bps=delta,
        all_samples_passed=all_passed,
        passed=passed,
        status=status,
    )


def _group_samples(samples: list[QuoteSample]) -> dict[tuple[str, int], list[QuoteSample]]:
    grouped: dict[tuple[str, int], list[QuoteSample]] = {}
    for sample in samples:
        grouped.setdefault((sample.pair, sample.amount_in_raw), []).append(sample)
    return dict(sorted(grouped.items()))


def _source_row(pair: str, path: Path) -> dict:
    if not path.exists():
        return {
            "pair": pair,
            "path": str(path),
            "present": False,
            "block_tag": "missing",
            "generated_at": "",
            "rows": 0,
            "quoted_rows": 0,
        }
    data = _load_json(path)
    rows = data.get("rows", [])
    return {
        "pair": pair,
        "path": str(path),
        "present": True,
        "block_tag": str(data.get("block_tag", "missing")),
        "generated_at": str(data.get("generated_at") or ""),
        "rows": len(rows),
        "quoted_rows": sum(1 for row in rows if row.get("status") == "quoted"),
    }


def _dedupe(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped = []
    for path in paths:
        key = str(path.resolve(strict=False))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _sample_sort_key(sample: QuoteSample) -> tuple[int, str, str]:
    if sample.block_tag.isdigit():
        return (int(sample.block_tag), sample.generated_at, sample.path)
    return (0, sample.generated_at, sample.path)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Measure quote-headroom drift across stored real quote snapshots")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_headroom_drift_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_headroom_drift_report.json")
    args = parser.parse_args()
    report = compute(root)
    write_outputs(report, args.out_md, args.out_json)
    print(
        f"quote headroom drift rows={len(report['rows'])}; "
        f"blocks={report['distinct_block_count']}; complete={report['complete']}"
    )
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
