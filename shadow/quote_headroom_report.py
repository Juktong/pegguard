from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C

PEGGUARD_FEE_PIPS = 500
PIPS_PER_BPS = 100


@dataclass(frozen=True)
class QuoteHeadroomRow:
    amount_in_raw: int
    peg_fee_pips: int
    peg_rank: int | None
    peg_cost_bps_vs_best: float | None
    best_fee_pips: int | None
    limiting_fee_pips: int | None
    best_amount_out_raw: int | None
    limiting_amount_out_raw: int | None
    peg_amount_out_raw: int | None
    premium_headroom_bps: float | None
    premium_headroom_pips: int | None
    status: str


def compute(quote_json: Path, peg_fee_pips: int = PEGGUARD_FEE_PIPS) -> dict:
    quote = _load_json(quote_json)
    rows = [_row(amount, quote_rows, peg_fee_pips) for amount, quote_rows in _group_by_amount(quote.get("rows", [])).items()]
    return {
        "quote_source": str(quote_json),
        "peg_fee_pips": peg_fee_pips,
        "model": "additional premium headroom is the 5 bps route's quote shortfall budget before matching the best quoted alternative",
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Quote Premium Headroom",
        "",
        "This report converts the real QuoterV2 grid into PegGuard premium headroom.",
        "It asks how much extra dynamic premium the 5 bps route can add before it",
        "matches the best quoted alternative for the same exact-input amount.",
        "",
        f"- Source: `{report.get('quote_source', 'n/a')}`",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Amount in raw | 5 bps rank | Best fee tier | Limiting alternative | 5 bps cost vs best | Premium headroom | Status |",
        "|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {int(row['amount_in_raw'])} | {_int_or_na(row.get('peg_rank'))} | {_fee(row.get('best_fee_pips'))} | "
            f"{_fee(row.get('limiting_fee_pips'))} | "
            f"{_bps_or_na(row.get('peg_cost_bps_vs_best'))} | {_bps_or_na(row.get('premium_headroom_bps'))} | "
            f"{row['status']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `premium headroom` is routeability budget from quotes, not a guarantee that routers or users keep trading after fees change.",
            "- `headroom vs next best` means the 5 bps route was the top quote and the limiting alternative defines the premium budget.",
            "- `behind best` means the 5 bps route was already worse than another fee tier before adding any PegGuard premium.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(amount_in_raw: int, rows: list[dict], peg_fee_pips: int) -> QuoteHeadroomRow:
    quoted = [row for row in rows if row.get("status") == "quoted" and row.get("amount_out_raw") is not None]
    if not quoted:
        return QuoteHeadroomRow(
            amount_in_raw, peg_fee_pips, None, None, None, None, None, None, None, None, None, "no quotes"
        )

    best = max(quoted, key=lambda row: int(row.get("amount_out_raw", 0)))
    peg = next((row for row in quoted if int(row.get("fee_pips", 0)) == peg_fee_pips), None)
    if peg is None:
        return QuoteHeadroomRow(
            amount_in_raw,
            peg_fee_pips,
            None,
            None,
            int(best.get("fee_pips", 0)),
            None,
            int(best.get("amount_out_raw", 0)),
            None,
            None,
            None,
            None,
            "missing 5 bps quote",
        )

    peg_out = int(peg.get("amount_out_raw", 0))
    best_out = int(best.get("amount_out_raw", 0))
    peg_cost = _cost_bps(peg_out, best_out)
    best_fee = int(best.get("fee_pips", 0))
    best_is_peg = best_fee == peg_fee_pips
    alternatives = [row for row in quoted if int(row.get("fee_pips", 0)) != peg_fee_pips]
    limiting = max(alternatives, key=lambda row: int(row.get("amount_out_raw", 0))) if alternatives else None
    if best_is_peg:
        if limiting is None:
            headroom = None
            status = "no alternative"
        else:
            headroom = _cost_bps(int(limiting.get("amount_out_raw", 0)), peg_out)
            status = "headroom vs next best"
    else:
        # If 5 bps is behind the best quote, additional premium has no positive
        # quote budget. The negative value is still useful as a deficit size.
        headroom = -peg_cost
        status = "behind best"

    return QuoteHeadroomRow(
        amount_in_raw=amount_in_raw,
        peg_fee_pips=peg_fee_pips,
        peg_rank=_rank(peg),
        peg_cost_bps_vs_best=peg_cost,
        best_fee_pips=best_fee,
        limiting_fee_pips=None if limiting is None else int(limiting.get("fee_pips", 0)),
        best_amount_out_raw=best_out,
        limiting_amount_out_raw=None if limiting is None else int(limiting.get("amount_out_raw", 0)),
        peg_amount_out_raw=peg_out,
        premium_headroom_bps=headroom,
        premium_headroom_pips=None if headroom is None else int(round(headroom * PIPS_PER_BPS)),
        status=status,
    )


def _cost_bps(amount_out: int, best_amount_out: int) -> float:
    if best_amount_out <= 0:
        return 0.0
    return (best_amount_out - amount_out) / best_amount_out * 10_000


def _rank(row: dict) -> int | None:
    value = row.get("rank")
    return None if value is None else int(value)


def _group_by_amount(rows: list[dict]) -> dict[int, list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        amount = int(row.get("amount_in_raw", 0))
        grouped.setdefault(amount, []).append(row)
    return dict(sorted(grouped.items()))


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _int_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return str(int(value))


def _fee(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value) / PIPS_PER_BPS:.2f} bps"


def _bps_or_na(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.4f} bps"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Convert real quote grid into PegGuard premium headroom")
    parser.add_argument("--quote-json", type=Path, default=root / "docs" / "quote_route_quotes.json")
    parser.add_argument("--peg-fee-pips", type=int, default=PEGGUARD_FEE_PIPS)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "quote_headroom_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "quote_headroom_report.json")
    args = parser.parse_args()
    report = compute(args.quote_json, args.peg_fee_pips)
    write_outputs(report, args.out_md, args.out_json)
    print(f"quote headroom rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
