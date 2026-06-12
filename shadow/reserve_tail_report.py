from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from fractions import Fraction
from math import ceil
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events
from .insurance_reserve_report import CLAIM_BASES, PAYOUT_RATES, ReserveEvent
from .insurance_reserve_report import _claimable_markout, _fixture_event_to_reserve, _live_events, _payout


@dataclass(frozen=True)
class ReserveTailRow:
    window: str
    claim_basis: str
    payout_rate: float
    rows: int
    iterations: int
    premium_e6: int
    claims_e6: int
    observed_seed_e6: int
    terminal_shortfall_e6: int
    p50_seed_e6: int
    p95_seed_e6: int
    p99_seed_e6: int
    cvar95_seed_e6: int
    max_seed_e6: int
    seed_needed_probability: float


def compute(root: Path | None = None, live_db: Path | None = None, iterations: int = 500, seed: int = 47) -> dict:
    root = root or C.repo_root()
    rows: list[ReserveTailRow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(reserve_tail_rows("live shadow", live_events, iterations=iterations, seed=seed))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(
            reserve_tail_rows(
                window,
                [_fixture_event_to_reserve(event) for event in fixture],
                iterations=iterations,
                seed=seed,
            )
        )
    return {
        "model": (
            "premium-only reserve event-order stress; each row shuffles realized premium and claim events "
            "and sizes the zero-start reserve seed needed to avoid a negative balance."
        ),
        "iterations": iterations,
        "seed": seed,
        "rows": [asdict(row) for row in rows],
    }


def reserve_tail_rows(
    window: str,
    events: list[ReserveEvent],
    iterations: int = 500,
    seed: int = 47,
    payout_rates: tuple[Fraction, ...] = PAYOUT_RATES,
) -> list[ReserveTailRow]:
    rows: list[ReserveTailRow] = []
    for claim_basis in CLAIM_BASES:
        for payout_rate in payout_rates:
            rows.append(reserve_tail_row(window, events, claim_basis, payout_rate, iterations=iterations, seed=seed))
    return rows


def reserve_tail_row(
    window: str,
    events: list[ReserveEvent],
    claim_basis: str,
    payout_rate: Fraction,
    iterations: int = 500,
    seed: int = 47,
) -> ReserveTailRow:
    deltas = [_reserve_delta(event, claim_basis, payout_rate) for event in events]
    observed_seed = _required_seed(deltas)
    premium = sum(max(0, event.extra_e6) for event in events)
    claims = sum(_payout(_claimable_markout(event, claim_basis), payout_rate) for event in events)
    terminal_shortfall = max(0, claims - premium)

    rng = random.Random(_scenario_seed(seed, window, claim_basis, payout_rate))
    shuffled_seeds: list[int] = []
    order = list(deltas)
    for _ in range(iterations):
        rng.shuffle(order)
        shuffled_seeds.append(_required_seed(order))

    sorted_seeds = sorted(shuffled_seeds)
    seed_needed = sum(1 for value in sorted_seeds if value > 0)
    p95_index = _percentile_index(len(sorted_seeds), 0.95)
    tail = sorted_seeds[p95_index:] or [0]
    return ReserveTailRow(
        window=window,
        claim_basis=claim_basis,
        payout_rate=float(payout_rate),
        rows=len(events),
        iterations=iterations,
        premium_e6=premium,
        claims_e6=claims,
        observed_seed_e6=observed_seed,
        terminal_shortfall_e6=terminal_shortfall,
        p50_seed_e6=_percentile(sorted_seeds, 0.50),
        p95_seed_e6=_percentile(sorted_seeds, 0.95),
        p99_seed_e6=_percentile(sorted_seeds, 0.99),
        cvar95_seed_e6=sum(tail) // len(tail),
        max_seed_e6=max(sorted_seeds, default=0),
        seed_needed_probability=0 if not sorted_seeds else seed_needed / len(sorted_seeds),
    )


def markdown(report: dict) -> str:
    lines = [
        "# Reserve Tail Sizing",
        "",
        "This report extends the insurance-reserve test by measuring event-order risk.",
        "It uses the same premium-only reserve model as `insurance_reserve_report.md`,",
        "then shuffles the realized event path to estimate p95/p99/CVaR seed capital.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        f"- Iterations: {int(report.get('iterations', 0))}",
        f"- Seed: {int(report.get('seed', 0))}",
        "",
        "| Window | Claim basis | Payout | Rows | Premium | Claims | Observed seed | Terminal shortfall | p50 seed | p95 seed | p99 seed | CVaR95 seed | Max seed | P(seed needed) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['claim_basis']} | {float(row['payout_rate']):.0%} | "
            f"{int(row['rows'])} | {_usd(int(row['premium_e6']))} | {_usd(int(row['claims_e6']))} | "
            f"{_usd(int(row['observed_seed_e6']))} | {_usd(int(row['terminal_shortfall_e6']))} | "
            f"{_usd(int(row['p50_seed_e6']))} | {_usd(int(row['p95_seed_e6']))} | "
            f"{_usd(int(row['p99_seed_e6']))} | {_usd(int(row['cvar95_seed_e6']))} | "
            f"{_usd(int(row['max_seed_e6']))} | {float(row['seed_needed_probability']):.2%} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `observed seed` is the reserve required on the realized event order.",
            "- `p95`, `p99`, and `CVaR95` are shuffled event-order seed requirements, not price forecasts.",
            "- `terminal shortfall` is aggregate insolvency; seed sizing also captures temporary deficits even when aggregate premiums cover claims.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _reserve_delta(event: ReserveEvent, claim_basis: str, payout_rate: Fraction) -> int:
    claim = _payout(_claimable_markout(event, claim_basis), payout_rate)
    return max(0, event.extra_e6) - claim


def _required_seed(deltas: list[int]) -> int:
    balance = 0
    min_balance = 0
    for delta in deltas:
        balance += delta
        min_balance = min(min_balance, balance)
    return max(0, -min_balance)


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    return values[_percentile_index(len(values), percentile)]


def _percentile_index(length: int, percentile: float) -> int:
    if length <= 0:
        return 0
    return min(length - 1, max(0, ceil(length * percentile) - 1))


def _scenario_seed(seed: int, window: str, claim_basis: str, payout_rate: Fraction) -> int:
    scenario = f"{window}|{claim_basis}|{payout_rate.numerator}/{payout_rate.denominator}"
    acc = seed
    for byte in scenario.encode("utf-8"):
        acc = ((acc * 131) + byte) & 0xFFFFFFFF
    return acc


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate PegGuard reserve tail-sizing scenarios")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--iterations", type=int, default=500)
    parser.add_argument("--seed", type=int, default=47)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "reserve_tail_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "reserve_tail_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, iterations=args.iterations, seed=args.seed)
    write_outputs(report, args.out_md, args.out_json)
    print(f"reserve tail rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
