from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events
from .insurance_reserve_report import ReserveEvent
from .insurance_reserve_report import _fixture_event_to_reserve, _live_events


RESERVE_SHARES = (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1))
CLAIM_BASES = ("charged correcting markout", "all truth-correcting markout")


@dataclass(frozen=True)
class AllocationRow:
    window: str
    claim_basis: str
    reserve_share: float
    rows: int
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    lp_extra_kept_e6: int
    reserve_inflow_e6: int
    claims_e6: int
    lp_net_before_claims_e6: int
    lp_net_before_claims_bps: float
    reserve_ending_e6: int
    reserve_required_seed_e6: int
    reserve_terminal_shortfall_e6: int
    reserve_coverage_ratio: float | None
    lp_dynamic_drag_vs_all_lp_e6: int
    lp_net_positive: bool
    reserve_unseeded_solvent: bool
    model: str


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[AllocationRow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        rows.extend(allocation_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(allocation_rows(window, [_fixture_event_to_reserve(event) for event in fixture]))
    return {
        "model": (
            "same-event premium allocation frontier. A fixed share of PegGuard dynamic premium funds an insurance "
            "reserve and the remainder stays with LPs. Base fees stay LP revenue. Claims use measured positive "
            "truth markout under the listed claim promise with 100% payout."
        ),
        "reserve_shares": [float(share) for share in RESERVE_SHARES],
        "claim_bases": list(CLAIM_BASES),
        "rows": [asdict(row) for row in rows],
    }


def allocation_rows(
    window: str,
    events: list[ReserveEvent],
    reserve_shares: tuple[Fraction, ...] = RESERVE_SHARES,
) -> list[AllocationRow]:
    return [
        _row(window, events, claim_basis, reserve_share)
        for claim_basis in CLAIM_BASES
        for reserve_share in reserve_shares
    ]


def markdown(report: dict) -> str:
    lines = [
        "# Premium Allocation Frontier",
        "",
        "This report sweeps how much dynamic premium is paid to LPs versus reserved",
        "for an insurance promise. It bridges the PnL attribution view, where",
        "premium is LP income, with the reserve-solvency view, where premium funds",
        "claims.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Claim basis | Reserve share | LP net before claims | LP extra kept | Reserve inflow | Claims | Required seed | Coverage | Unseeded solvent |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['claim_basis']} | {float(row['reserve_share']):.0%} | "
            f"{_usd(int(row['lp_net_before_claims_e6']))} ({float(row['lp_net_before_claims_bps']):.2f} bps) | "
            f"{_usd(int(row['lp_extra_kept_e6']))} | {_usd(int(row['reserve_inflow_e6']))} | "
            f"{_usd(int(row['claims_e6']))} | {_usd(int(row['reserve_required_seed_e6']))} | "
            f"{_ratio(row.get('reserve_coverage_ratio'))} | {'yes' if row['reserve_unseeded_solvent'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `0%` reserve share is the pure LP-fee case; reserve coverage is zero unless claims are zero.",
            "- `100%` reserve share is the pure insurance-capital case; LPs keep base fee but no dynamic premium.",
            "- `Required seed` is path-dependent: it is the maximum reserve deficit after applying the chosen premium split event by event.",
            "- The table does not choose a product policy; it exposes the LP return versus insurance-solvency tradeoff.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(window: str, events: list[ReserveEvent], claim_basis: str, reserve_share: Fraction) -> AllocationRow:
    notional = sum(event.notional_e6 for event in events)
    base_fee = sum(_fee(event.notional_e6, BASE_FEE_PIPS) for event in events)
    extra = sum(event.extra_e6 for event in events)
    markout = sum(event.truth_markout_e6 for event in events)
    lp_extra = sum(_split_to_lp(event.extra_e6, reserve_share) for event in events)
    reserve_inflow = extra - lp_extra
    balance = 0
    min_balance = 0
    claims = 0
    for event in events:
        claim = _claimable_markout(event, claim_basis)
        claims += claim
        balance += _split_to_reserve(event.extra_e6, reserve_share) - claim
        min_balance = min(min_balance, balance)
    lp_net = base_fee + lp_extra - markout
    required_seed = max(0, -min_balance)
    terminal_shortfall = max(0, claims - reserve_inflow)
    return AllocationRow(
        window=window,
        claim_basis=claim_basis,
        reserve_share=float(reserve_share),
        rows=len(events),
        notional_e6=notional,
        base_fee_e6=base_fee,
        extra_e6=extra,
        markout_e6=markout,
        lp_extra_kept_e6=lp_extra,
        reserve_inflow_e6=reserve_inflow,
        claims_e6=claims,
        lp_net_before_claims_e6=lp_net,
        lp_net_before_claims_bps=_bps(lp_net, notional),
        reserve_ending_e6=reserve_inflow - claims,
        reserve_required_seed_e6=required_seed,
        reserve_terminal_shortfall_e6=terminal_shortfall,
        reserve_coverage_ratio=(reserve_inflow / claims) if claims else None,
        lp_dynamic_drag_vs_all_lp_e6=extra - lp_extra,
        lp_net_positive=lp_net >= 0,
        reserve_unseeded_solvent=required_seed == 0 and terminal_shortfall == 0,
        model="fixed premium split, 100% claim payout",
    )


def _split_to_reserve(value_e6: int, reserve_share: Fraction) -> int:
    return (value_e6 * reserve_share.numerator) // reserve_share.denominator


def _split_to_lp(value_e6: int, reserve_share: Fraction) -> int:
    return value_e6 - _split_to_reserve(value_e6, reserve_share)


def _claimable_markout(event: ReserveEvent, claim_basis: str) -> int:
    positive_markout = max(0, event.truth_markout_e6)
    if claim_basis == "charged correcting markout":
        return positive_markout if event.extra_e6 > 0 and event.truth_corr == 1 else 0
    if claim_basis == "all truth-correcting markout":
        return positive_markout if event.truth_corr == 1 else 0
    raise ValueError(f"unknown claim basis: {claim_basis}")


def _fee(notional_e6: int, pips: int) -> int:
    return (notional_e6 * pips) // PIPS_DENOM


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _ratio(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f}x"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate premium allocation frontier")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "premium_allocation_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "premium_allocation_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"premium allocation rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
