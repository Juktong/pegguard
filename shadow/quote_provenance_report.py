from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C


@dataclass(frozen=True)
class QuoteArtifactRow:
    label: str
    path: str
    present: bool
    chain: str
    block_tag: str
    pinned_block: bool
    generated_at: str
    rows: int
    quoted_rows: int
    failed_rows: int
    fee_tiers: int
    amount_inputs: int
    min_amount_in_raw: int | None
    max_amount_in_raw: int | None
    warning: str


def compute(root: Path | None = None, paths: dict[str, Path] | None = None) -> dict:
    root = root or C.repo_root()
    paths = paths or default_paths(root)
    rows = [_artifact_row(label, path) for label, path in paths.items()]
    present = [row for row in rows if row.present]
    total_rows = sum(row.rows for row in rows)
    quoted_rows = sum(row.quoted_rows for row in rows)
    failed_rows = sum(row.failed_rows for row in rows)
    latest_rows = sum(1 for row in present if row.block_tag == "latest")
    pinned_rows = sum(1 for row in present if row.pinned_block)
    missing_generated_at = sum(1 for row in present if not row.generated_at)
    warnings = [row.warning for row in rows if row.warning]
    return {
        "model": (
            "quote-source provenance audit for routeability economics; this does not "
            "collect new quotes and does not measure route-away elasticity."
        ),
        "complete": len(present) == len(rows) and quoted_rows > 0,
        "artifact_count": len(rows),
        "present_count": len(present),
        "total_quote_rows": total_rows,
        "quoted_rows": quoted_rows,
        "failed_rows": failed_rows,
        "latest_block_tag_artifacts": latest_rows,
        "pinned_block_artifacts": pinned_rows,
        "missing_generated_at_artifacts": missing_generated_at,
        "warnings": warnings,
        "artifacts": [asdict(row) for row in rows],
    }


def default_paths(root: Path) -> dict[str, Path]:
    snapshot = _latest_snapshot_dir(root)
    return {
        "WETH/USDC primary": root / "docs" / "quote_route_quotes.json",
        "WETH/USDT primary": root / "docs" / "quote_route_quotes_weth_usdt.json",
        "WETH/USDC repeat": snapshot / "quote_route_quotes_weth_usdc.json",
        "WETH/USDT repeat": snapshot / "quote_route_quotes_weth_usdt.json",
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Provenance Audit",
        "",
        "This report audits the quote artifacts used by quote-headroom economics.",
        "It checks whether quote tables are present, whether rows actually quoted,",
        "and whether the source block is reproducible. It is provenance evidence,",
        "not route-away elasticity.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Quoted rows: {int(report.get('quoted_rows', 0))}/{int(report.get('total_quote_rows', 0))}",
        f"- Pinned block artifacts: {int(report.get('pinned_block_artifacts', 0))}/{int(report.get('present_count', 0))}",
        f"- `latest` block-tag artifacts: {int(report.get('latest_block_tag_artifacts', 0))}",
        f"- Missing generated-at fields: {int(report.get('missing_generated_at_artifacts', 0))}",
        "",
        "| Artifact | Present | Chain | Block tag | Pinned | Rows | Quoted | Failed | Amount range | Warning |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("artifacts", []):
        lines.append(
            f"| {row['label']} | {'yes' if row['present'] else 'no'} | {row['chain']} | "
            f"{row['block_tag']} | {'yes' if row['pinned_block'] else 'no'} | "
            f"{int(row['rows'])} | {int(row['quoted_rows'])} | {int(row['failed_rows'])} | "
            f"{_amount_range(row)} | {row['warning'] or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `latest` block tags mean the stored table is real but not self-reproducible unless paired with a pinned repeat snapshot.",
            "- Missing `generated_at` means the artifact predates timestamped quote collection and should be replaced on the next real quote run.",
            "- Failed quote rows would make downstream headroom reports incomplete; they are kept visible instead of silently dropped.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _artifact_row(label: str, path: Path) -> QuoteArtifactRow:
    if not path.exists():
        return QuoteArtifactRow(
            label=label,
            path=str(path),
            present=False,
            chain="n/a",
            block_tag="missing",
            pinned_block=False,
            generated_at="",
            rows=0,
            quoted_rows=0,
            failed_rows=0,
            fee_tiers=0,
            amount_inputs=0,
            min_amount_in_raw=None,
            max_amount_in_raw=None,
            warning="missing quote artifact",
        )
    data = _load_json(path)
    rows = data.get("rows", [])
    amounts = [int(row.get("amount_in_raw", 0)) for row in rows if row.get("amount_in_raw") is not None]
    block_tag = str(data.get("block_tag", ""))
    pinned = _is_pinned_block(block_tag)
    quoted = sum(1 for row in rows if row.get("status") == "quoted")
    failed = len(rows) - quoted
    warning = _warning(path, block_tag, pinned, data.get("generated_at"), len(rows), quoted)
    return QuoteArtifactRow(
        label=label,
        path=str(path),
        present=True,
        chain=str(data.get("chain", "n/a")),
        block_tag=block_tag or "missing",
        pinned_block=pinned,
        generated_at=str(data.get("generated_at") or ""),
        rows=len(rows),
        quoted_rows=quoted,
        failed_rows=failed,
        fee_tiers=len(data.get("fee_tiers", [])),
        amount_inputs=len(data.get("amount_ins", [])),
        min_amount_in_raw=min(amounts) if amounts else None,
        max_amount_in_raw=max(amounts) if amounts else None,
        warning=warning,
    )


def _warning(path: Path, block_tag: str, pinned: bool, generated_at: object, rows: int, quoted: int) -> str:
    warnings = []
    if rows == 0:
        warnings.append("no quote rows")
    if quoted < rows:
        warnings.append("failed quote rows")
    if not pinned:
        warnings.append("unpinned block tag")
    if not generated_at:
        warnings.append("missing generated_at")
    return "; ".join(warnings)


def _is_pinned_block(block_tag: str) -> bool:
    return block_tag.isdigit() or (block_tag.startswith("0x") and len(block_tag) > 2)


def _latest_snapshot_dir(root: Path) -> Path:
    base = root / "docs" / "quote-snapshots"
    snapshots = sorted(path for path in base.glob("*") if path.is_dir())
    return snapshots[-1] if snapshots else base / "missing"


def _amount_range(row: dict) -> str:
    minimum = row.get("min_amount_in_raw")
    maximum = row.get("max_amount_in_raw")
    if minimum is None or maximum is None:
        return "n/a"
    return str(minimum) if int(minimum) == int(maximum) else f"{minimum}-{maximum}"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Audit quote artifact provenance for economic reports")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_provenance_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_provenance_report.json")
    args = parser.parse_args()
    report = compute(root)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote provenance artifacts={report['present_count']}/{report['artifact_count']}; quoted={report['quoted_rows']}/{report['total_quote_rows']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
