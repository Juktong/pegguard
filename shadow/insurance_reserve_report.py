from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events

PAYOUT_RATES = (Fraction(1, 4), Fraction(1, 2), Fraction(1, 1))
CLAIM_BASES = (
    "charged correcting markout",
    "all truth-correcting markout",
    "all positive markout",
)


@dataclass(frozen=True)
class ReserveEvent:
    t_ms: int
    notional_e6: int
    extra_e6: int
    premium_pips: int
    truth_corr: int
    truth_markout_e6: int


@dataclass(frozen=True)
class ReserveRow:
    window: str
    claim_basis: str
    payout_rate: float
    rows: int
    claim_rows: int
    notional_e6: int
    premium_e6: int
    claimable_markout_e6: int
    claims_e6: int
    ending_reserve_e6: int
    terminal_shortfall_e6: int
    max_deficit_e6: int
    first_deficit_index: int | None
    first_deficit_t_ms: int | None
    coverage_ratio: float | None


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[ReserveRow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(reserve_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(reserve_rows(window, [_fixture_event_to_reserve(event) for event in fixture]))
    return {
        "model": (
            "premium-only reserve; base fees remain LP revenue. Claim rows use positive measured truth markout "
            "under three possible product promises."
        ),
        "payout_rates": [float(rate) for rate in PAYOUT_RATES],
        "claim_bases": list(CLAIM_BASES),
        "rows": [asdict(row) for row in rows],
    }


def reserve_rows(
    window: str,
    events: list[ReserveEvent],
    payout_rates: tuple[Fraction, ...] = PAYOUT_RATES,
) -> list[ReserveRow]:
    rows: list[ReserveRow] = []
    for claim_basis in CLAIM_BASES:
        for payout_rate in payout_rates:
            rows.append(_reserve_row(window, events, claim_basis, payout_rate))
    return rows


def markdown(report: dict) -> str:
    lines = [
        "# Insurance Reserve Solvency",
        "",
        "This premium-only reserve report treats PegGuard extra premium as the only reserve inflow.",
        "Base fees are excluded because they are normal LP revenue, not insurance",
        "capital. No claim policy is implemented by the hook; these rows are",
        "scenario tests for possible insurance promises.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Claim basis | Payout | Rows | Claim rows | Premium | Claimable markout | Claims | Ending reserve | Terminal shortfall | Required seed | Coverage |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['claim_basis']} | {float(row['payout_rate']):.0%} | "
            f"{int(row['rows'])} | {int(row['claim_rows'])} | {_usd(int(row['premium_e6']))} | "
            f"{_usd(int(row['claimable_markout_e6']))} | {_usd(int(row['claims_e6']))} | "
            f"{_usd(int(row['ending_reserve_e6']))} | {_usd(int(row['terminal_shortfall_e6']))} | "
            f"{_usd(int(row['max_deficit_e6']))} | {_ratio(row.get('coverage_ratio'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `charged correcting markout` is the narrowest promise: pay only measured markout on swaps PegGuard actually charged and the truth labels as correcting.",
            "- `all truth-correcting markout` asks whether charged premiums can cover all measured toxic-flow markout, including rows PegGuard did not charge.",
            "- `all positive markout` is the conservative upper bound that ignores direction labels and pays any positive measured markout.",
            "- `required seed` is the maximum zero-initial-reserve deficit along the event path, so it captures timing as well as aggregate solvency.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _reserve_row(window: str, events: list[ReserveEvent], claim_basis: str, payout_rate: Fraction) -> ReserveRow:
    premium = sum(event.extra_e6 for event in events)
    notional = sum(event.notional_e6 for event in events)
    balance = 0
    min_balance = 0
    first_deficit_index: int | None = None
    first_deficit_t_ms: int | None = None
    claim_rows = 0
    claimable = 0
    claims = 0
    for index, event in enumerate(events):
        claimable_event = _claimable_markout(event, claim_basis)
        claim_event = _payout(claimable_event, payout_rate)
        balance += event.extra_e6 - claim_event
        if claimable_event > 0:
            claim_rows += 1
            claimable += claimable_event
            claims += claim_event
        if balance < 0 and first_deficit_index is None:
            first_deficit_index = index
            first_deficit_t_ms = event.t_ms
        min_balance = min(min_balance, balance)

    coverage = None if claims == 0 else premium / claims
    return ReserveRow(
        window=window,
        claim_basis=claim_basis,
        payout_rate=float(payout_rate),
        rows=len(events),
        claim_rows=claim_rows,
        notional_e6=notional,
        premium_e6=premium,
        claimable_markout_e6=claimable,
        claims_e6=claims,
        ending_reserve_e6=premium - claims,
        terminal_shortfall_e6=max(0, claims - premium),
        max_deficit_e6=max(0, -min_balance),
        first_deficit_index=first_deficit_index,
        first_deficit_t_ms=first_deficit_t_ms,
        coverage_ratio=coverage,
    )


def _claimable_markout(event: ReserveEvent, claim_basis: str) -> int:
    positive_markout = max(0, event.truth_markout_e6)
    if claim_basis == "charged correcting markout":
        return positive_markout if event.extra_e6 > 0 and event.truth_corr == 1 else 0
    if claim_basis == "all truth-correcting markout":
        return positive_markout if event.truth_corr == 1 else 0
    if claim_basis == "all positive markout":
        return positive_markout
    raise ValueError(f"unknown claim basis: {claim_basis}")


def _payout(value_e6: int, payout_rate: Fraction) -> int:
    return (value_e6 * payout_rate.numerator) // payout_rate.denominator


def _fixture_event_to_reserve(event) -> ReserveEvent:
    return ReserveEvent(
        t_ms=event.t_ms,
        notional_e6=event.notional_e6,
        extra_e6=event.peg_extra_e6,
        premium_pips=event.peg_premium_pips,
        truth_corr=event.truth_corr,
        truth_markout_e6=event.truth_markout_e6,
    )


def _live_events(db: Path) -> list[ReserveEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.ts_ms, l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    return [
        ReserveEvent(
            t_ms=int(row["ts_ms"]),
            notional_e6=abs(int(row["aq_e6"])),
            extra_e6=int(row["fresh_extra_e6"] or 0),
            premium_pips=int(row["fresh_premium_pips"] or 0),
            truth_corr=int(row["truth_corr"] or 0),
            truth_markout_e6=int(row["truth_mk_e6"] or 0),
        )
        for row in rows
    ]


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate PegGuard insurance reserve solvency scenarios")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "insurance_reserve_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "insurance_reserve_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"insurance reserve rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
