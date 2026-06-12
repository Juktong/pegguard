from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .quote_headroom_report import compute as compute_headroom


@dataclass(frozen=True)
class SnapshotSpec:
    pair: str
    baseline_json: Path
    repeat_json: Path


@dataclass(frozen=True)
class StabilityRow:
    pair: str
    amount_in_raw: int
    baseline_block_tag: str
    repeat_block_tag: str
    baseline_headroom_bps: float | None
    repeat_headroom_bps: float | None
    delta_headroom_bps: float | None
    baseline_peg_rank: int | None
    repeat_peg_rank: int | None
    baseline_best_fee_pips: int | None
    repeat_best_fee_pips: int | None
    repeat_status: str
    passed: bool


def compute(specs: list[SnapshotSpec]) -> dict:
    rows: list[StabilityRow] = []
    sources: list[dict[str, str]] = []
    for spec in specs:
        sources.append(
            {
                "pair": spec.pair,
                "baseline_json": str(spec.baseline_json),
                "repeat_json": str(spec.repeat_json),
            }
        )
        if not spec.baseline_json.exists() or not spec.repeat_json.exists():
            rows.append(
                StabilityRow(
                    pair=spec.pair,
                    amount_in_raw=0,
                    baseline_block_tag="missing" if not spec.baseline_json.exists() else _block_tag(spec.baseline_json),
                    repeat_block_tag="missing" if not spec.repeat_json.exists() else _block_tag(spec.repeat_json),
                    baseline_headroom_bps=None,
                    repeat_headroom_bps=None,
                    delta_headroom_bps=None,
                    baseline_peg_rank=None,
                    repeat_peg_rank=None,
                    baseline_best_fee_pips=None,
                    repeat_best_fee_pips=None,
                    repeat_status="missing snapshot",
                    passed=False,
                )
            )
            continue
        rows.extend(_compare_pair(spec))

    row_dicts = [asdict(row) for row in rows]
    positive = [row.repeat_headroom_bps for row in rows if row.repeat_headroom_bps is not None]
    deltas = [abs(row.delta_headroom_bps) for row in rows if row.delta_headroom_bps is not None]
    return {
        "model": "repeat QuoterV2 snapshots must keep 5 bps route premium headroom positive by pair and size",
        "sources": sources,
        "rows": row_dicts,
        "complete": bool(rows) and all(row.passed for row in rows),
        "pairs": sorted({row.pair for row in rows if row.amount_in_raw}),
        "passed_rows": sum(1 for row in rows if row.passed),
        "min_repeat_headroom_bps": None if not positive else min(positive),
        "max_abs_delta_headroom_bps": None if not deltas else max(deltas),
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Headroom Stability",
        "",
        "This report compares repeated real QuoterV2 snapshots. It is still",
        "routeability evidence, not controlled route-away elasticity: it checks",
        "whether the 5 bps route still has positive premium headroom under a later",
        "on-chain quote.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Pairs: {', '.join(report.get('pairs', [])) or 'none'}",
        f"- Passed rows: {int(report.get('passed_rows', 0))}/{len(report.get('rows', []))}",
        f"- Min repeat headroom: {_bps_or_na(report.get('min_repeat_headroom_bps'))}",
        f"- Max absolute headroom delta: {_bps_or_na(report.get('max_abs_delta_headroom_bps'))}",
        "",
        "## Sources",
        "",
        "| Pair | Baseline | Repeat |",
        "|---|---|---|",
    ]
    for source in report.get("sources", []):
        lines.append(f"| {source['pair']} | `{source['baseline_json']}` | `{source['repeat_json']}` |")

    lines.extend(
        [
            "",
            "## Rows",
            "",
            "| Pair | Amount in raw | Baseline block | Repeat block | Baseline headroom | Repeat headroom | Delta | Repeat 5 bps rank | Repeat best fee | Status | Passed |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|",
        ]
    )
    for row in report.get("rows", []):
        lines.append(
            f"| {row['pair']} | {int(row['amount_in_raw'])} | {row['baseline_block_tag']} | {row['repeat_block_tag']} | "
            f"{_bps_or_na(row.get('baseline_headroom_bps'))} | {_bps_or_na(row.get('repeat_headroom_bps'))} | "
            f"{_bps_or_na(row.get('delta_headroom_bps'))} | {_int_or_na(row.get('repeat_peg_rank'))} | "
            f"{_fee(row.get('repeat_best_fee_pips'))} | {row['repeat_status']} | {'yes' if row.get('passed') else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Passing rows mean the 5 bps route remains the best quoted tier and has positive premium headroom at the repeat snapshot.",
            "- A large negative delta means headroom compressed; this should tighten route-away assumptions even if the row still passes.",
            "- This report does not replace the controlled PegGuard-vs-baseline pre/post route-away experiment.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def default_specs(root: Path, snapshot_dir: Path | None = None) -> list[SnapshotSpec]:
    snapshot_dir = snapshot_dir or _latest_snapshot_dir(root)
    return [
        SnapshotSpec(
            "WETH/USDC",
            root / "docs" / "quote_route_quotes.json",
            snapshot_dir / "quote_route_quotes_weth_usdc.json",
        ),
        SnapshotSpec(
            "WETH/USDT",
            root / "docs" / "quote_route_quotes_weth_usdt.json",
            snapshot_dir / "quote_route_quotes_weth_usdt.json",
        ),
    ]


def _compare_pair(spec: SnapshotSpec) -> list[StabilityRow]:
    baseline_quote = _load_json(spec.baseline_json)
    repeat_quote = _load_json(spec.repeat_json)
    baseline_rows = _headroom_by_amount(compute_headroom(spec.baseline_json))
    repeat_rows = _headroom_by_amount(compute_headroom(spec.repeat_json))
    amounts = sorted(set(baseline_rows) | set(repeat_rows))
    rows: list[StabilityRow] = []
    for amount in amounts:
        baseline = baseline_rows.get(amount, {})
        repeat = repeat_rows.get(amount, {})
        baseline_headroom = _optional_float(baseline.get("premium_headroom_bps"))
        repeat_headroom = _optional_float(repeat.get("premium_headroom_bps"))
        delta = None if baseline_headroom is None or repeat_headroom is None else repeat_headroom - baseline_headroom
        repeat_rank = _optional_int(repeat.get("peg_rank"))
        repeat_best_fee = _optional_int(repeat.get("best_fee_pips"))
        passed = (
            repeat_headroom is not None
            and repeat_headroom > 0
            and repeat_rank == 1
            and repeat_best_fee == 500
        )
        rows.append(
            StabilityRow(
                pair=spec.pair,
                amount_in_raw=amount,
                baseline_block_tag=str(baseline_quote.get("block_tag", "n/a")),
                repeat_block_tag=str(repeat_quote.get("block_tag", "n/a")),
                baseline_headroom_bps=baseline_headroom,
                repeat_headroom_bps=repeat_headroom,
                delta_headroom_bps=delta,
                baseline_peg_rank=_optional_int(baseline.get("peg_rank")),
                repeat_peg_rank=repeat_rank,
                baseline_best_fee_pips=_optional_int(baseline.get("best_fee_pips")),
                repeat_best_fee_pips=repeat_best_fee,
                repeat_status=str(repeat.get("status", "missing repeat row")),
                passed=passed,
            )
        )
    return rows


def _headroom_by_amount(report: dict) -> dict[int, dict]:
    return {int(row.get("amount_in_raw", 0)): row for row in report.get("rows", [])}


def _latest_snapshot_dir(root: Path) -> Path:
    base = root / "docs" / "quote-snapshots"
    dirs = [path for path in base.glob("*") if path.is_dir()]
    return sorted(dirs)[-1] if dirs else base / "missing"


def _block_tag(path: Path) -> str:
    return str(_load_json(path).get("block_tag", "n/a"))


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


def _int_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def _fee(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value) / 100:.2f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Compare repeated quote headroom snapshots")
    parser.add_argument("--snapshot-dir", type=Path, help="directory containing repeat quote_route_quotes_*.json files")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_headroom_stability_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_headroom_stability_report.json")
    args = parser.parse_args()
    report = compute(default_specs(root, args.snapshot_dir))
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote headroom stability rows={len(report['rows'])}; complete={report['complete']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
