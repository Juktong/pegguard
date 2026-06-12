from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM

BUCKET_LABELS = ("<=1s", "1-2s", "2-5s", ">5s/missing", "other fallback")


@dataclass(frozen=True)
class StalenessBucket:
    bucket: str
    rows: int
    valid_truth_rows: int
    notional_e6: int
    truth_notional_e6: int
    fallback_rows: int
    fallback_notional_e6: int
    fallback_share: float
    charged_rows: int
    truth_base_fee_e6: int
    truth_extra_e6: int
    truth_markout_e6: int
    truth_net_e6: int
    truth_net_bps: float
    precision: float | None
    capture: float | None


def compute(db: Path) -> dict:
    rows = _load_rows(db)
    buckets = [bucket_for_rows(label, [row for row in rows if _bucket_label(row) == label]) for label in BUCKET_LABELS]
    return {
        "database": str(db),
        "rows": len(rows),
        "buckets": [asdict(row) for row in buckets],
    }


def bucket_for_rows(label: str, rows: list[sqlite3.Row]) -> StalenessBucket:
    valid = [row for row in rows if row["valid"]]
    fallback = [row for row in rows if str(row["fresh_fallback_reason"] or "")]
    charged_valid = [row for row in valid if int(row["fresh_premium_pips"] or 0) > 0]
    notional = sum(abs(int(row["aq_e6"])) for row in rows)
    truth_notional = sum(abs(int(row["aq_e6"])) for row in valid)
    base = sum((abs(int(row["aq_e6"])) * BASE_FEE_PIPS) // PIPS_DENOM for row in valid)
    extra = sum(int(row["fresh_extra_e6"] or 0) for row in valid)
    markout = sum(int(row["truth_mk_e6"] or 0) for row in valid)
    net = base + extra - markout
    premium_total = sum(int(row["fresh_extra_e6"] or 0) for row in charged_valid)
    premium_correct = sum(int(row["fresh_extra_e6"] or 0) for row in charged_valid if int(row["truth_corr"] or 0) == 1)
    fallback_notional = sum(abs(int(row["aq_e6"])) for row in fallback)
    return StalenessBucket(
        bucket=label,
        rows=len(rows),
        valid_truth_rows=len(valid),
        notional_e6=notional,
        truth_notional_e6=truth_notional,
        fallback_rows=len(fallback),
        fallback_notional_e6=fallback_notional,
        fallback_share=(fallback_notional / notional) if notional else 0.0,
        charged_rows=len(charged_valid),
        truth_base_fee_e6=base,
        truth_extra_e6=extra,
        truth_markout_e6=markout,
        truth_net_e6=net,
        truth_net_bps=_bps(net, truth_notional),
        precision=(premium_correct / premium_total) if premium_total else None,
        capture=(extra / abs(markout)) if markout else None,
    )


def markdown(report: dict) -> str:
    lines = [
        "# Oracle Staleness Buckets",
        "",
        "This report segments live-shadow economics by the hot-path `fresh` oracle",
        "decision's observed staleness/fallback bucket. Net, precision, and capture",
        "use only rows with valid truth labels.",
        "",
        f"- Database: `{report.get('database', 'n/a')}`",
        f"- Rows: {int(report.get('rows', 0))}",
        "",
        "| Bucket | Rows | Valid truth | Notional | Truth notional | Fallback share | Charged truth rows | Truth extra | Truth markout | Truth net | Net bps | Precision | Capture |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("buckets", []):
        lines.append(
            f"| {row['bucket']} | {int(row['rows'])} | {int(row['valid_truth_rows'])} | "
            f"{_usd(int(row['notional_e6']))} | {_usd(int(row['truth_notional_e6']))} | "
            f"{float(row['fallback_share']):.2%} | {int(row['charged_rows'])} | "
            f"{_usd(int(row['truth_extra_e6']))} | {_usd(int(row['truth_markout_e6']))} | "
            f"{_usd(int(row['truth_net_e6']))} | {float(row['truth_net_bps']):.2f} | "
            f"{_pct(row.get('precision'))} | {_pct(row.get('capture'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `>5s/missing` includes stale or absent Pyth observations that fall back to base fee.",
            "- `other fallback` covers non-staleness oracle fallback reasons such as confidence spikes or bad price.",
            "- Empty or truthless buckets are still shown so missing measurement coverage is visible.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _load_rows(db: Path) -> list[sqlite3.Row]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            """
            SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()


def _bucket_label(row: sqlite3.Row) -> str:
    reason = str(row["fresh_fallback_reason"] or "")
    staleness = row["oracle_staleness_observed_ms"]
    if reason and reason != "STALE_OR_MISSING":
        return "other fallback"
    if reason == "STALE_OR_MISSING" or staleness is None:
        return ">5s/missing"
    value = int(staleness)
    if value <= 1_000:
        return "<=1s"
    if value <= 2_000:
        return "1-2s"
    if value <= 5_000:
        return "2-5s"
    return ">5s/missing"


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Segment live-shadow economics by oracle staleness bucket")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "staleness_bucket_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "staleness_bucket_report.json")
    args = parser.parse_args()
    report = compute(args.database)
    write_outputs(report, args.out_md, args.out_json)
    print(f"staleness buckets rows={report['rows']}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
