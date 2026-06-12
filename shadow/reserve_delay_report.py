from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events
from .insurance_reserve_report import ReserveEvent
from .insurance_reserve_report import _claimable_markout, _fixture_event_to_reserve, _live_events, _payout


CLAIM_DELAYS_DAYS = (0, 1, 7, 30)
CLAIM_SCENARIOS = (
    ("charged correcting markout", Fraction(1, 2)),
    ("charged correcting markout", Fraction(1, 1)),
    ("all truth-correcting markout", Fraction(1, 2)),
    ("all truth-correcting markout", Fraction(1, 1)),
)
DAY_MS = 86_400_000


@dataclass(frozen=True)
class ReserveDelayRow:
    window: str
    claim_basis: str
    payout_rate: float
    claim_delay_days: int
    rows: int
    claim_rows: int
    premium_e6: int
    claims_e6: int
    ending_cash_e6: int
    ending_equity_e6: int
    max_pending_claims_e6: int
    min_cash_e6: int
    min_equity_e6: int
    required_cash_seed_e6: int
    required_economic_seed_e6: int
    hidden_liability_gap_e6: int
    cash_survives_without_seed: bool
    economically_solvent_without_seed: bool


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[ReserveDelayRow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        rows.extend(delay_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(delay_rows(window, [_fixture_event_to_reserve(event) for event in fixture]))
    return {
        "model": (
            "event-level claim-delay reserve stress. Premium is collected at swap time; claim liabilities are "
            "recognized immediately but paid after the configured delay. Cash solvency and economic solvency "
            "are reported separately so payout delay cannot hide pending liabilities."
        ),
        "claim_delays_days": list(CLAIM_DELAYS_DAYS),
        "claim_scenarios": [
            {"claim_basis": basis, "payout_rate": float(rate)}
            for basis, rate in CLAIM_SCENARIOS
        ],
        "rows": [asdict(row) for row in rows],
    }


def delay_rows(window: str, events: list[ReserveEvent]) -> list[ReserveDelayRow]:
    return [
        _delay_row(window, events, claim_basis, payout_rate, delay_days)
        for claim_basis, payout_rate in CLAIM_SCENARIOS
        for delay_days in CLAIM_DELAYS_DAYS
    ]


def markdown(report: dict) -> str:
    lines = [
        "# Reserve Claim Delay Stress",
        "",
        "This report tests whether delayed claim settlement creates a false sense of",
        "reserve solvency. Premium enters cash immediately; claim liabilities are",
        "recognized at the triggering event and paid after the configured delay.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Claim basis | Payout | Delay | Rows | Premium | Claims | Ending cash | Ending equity | Max pending | Cash seed | Economic seed | Hidden gap | Cash survives | Econ solvent |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {row['claim_basis']} | {float(row['payout_rate']):.0%} | "
            f"{int(row['claim_delay_days'])}d | {int(row['rows'])} | {_usd(int(row['premium_e6']))} | "
            f"{_usd(int(row['claims_e6']))} | {_usd(int(row['ending_cash_e6']))} | "
            f"{_usd(int(row['ending_equity_e6']))} | {_usd(int(row['max_pending_claims_e6']))} | "
            f"{_usd(int(row['required_cash_seed_e6']))} | {_usd(int(row['required_economic_seed_e6']))} | "
            f"{_usd(int(row['hidden_liability_gap_e6']))} | {'yes' if row['cash_survives_without_seed'] else 'no'} | "
            f"{'yes' if row['economically_solvent_without_seed'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `cash seed` is the seed needed to avoid a negative cash balance when claims are actually paid.",
            "- `economic seed` is the seed needed after recognizing pending claim liabilities immediately.",
            "- `hidden gap` is the reserve need masked by delayed settlement.",
            "- A delayed payout policy improves cash timing only; it does not improve claim economics.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _delay_row(
    window: str,
    events: list[ReserveEvent],
    claim_basis: str,
    payout_rate: Fraction,
    delay_days: int,
) -> ReserveDelayRow:
    actions: list[tuple[int, int, int, int]] = []
    premium = 0
    claims = 0
    claim_rows = 0
    for event in events:
        premium += event.extra_e6
        actions.append((event.t_ms, 0, event.extra_e6, 0))
        claim = _payout(_claimable_markout(event, claim_basis), payout_rate)
        if claim > 0:
            claim_rows += 1
            claims += claim
            actions.append((event.t_ms, 1, 0, claim))
            actions.append((event.t_ms + delay_days * DAY_MS, 2, -claim, -claim))

    cash = 0
    pending = 0
    min_cash = 0
    min_equity = 0
    max_pending = 0
    for _, _, cash_delta, pending_delta in sorted(actions):
        cash += cash_delta
        pending += pending_delta
        equity = cash - pending
        min_cash = min(min_cash, cash)
        min_equity = min(min_equity, equity)
        max_pending = max(max_pending, pending)

    required_cash_seed = max(0, -min_cash)
    required_economic_seed = max(0, -min_equity)
    return ReserveDelayRow(
        window=window,
        claim_basis=claim_basis,
        payout_rate=float(payout_rate),
        claim_delay_days=delay_days,
        rows=len(events),
        claim_rows=claim_rows,
        premium_e6=premium,
        claims_e6=claims,
        ending_cash_e6=cash,
        ending_equity_e6=cash - pending,
        max_pending_claims_e6=max_pending,
        min_cash_e6=min_cash,
        min_equity_e6=min_equity,
        required_cash_seed_e6=required_cash_seed,
        required_economic_seed_e6=required_economic_seed,
        hidden_liability_gap_e6=max(0, required_economic_seed - required_cash_seed),
        cash_survives_without_seed=required_cash_seed == 0,
        economically_solvent_without_seed=required_economic_seed == 0,
    )


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate reserve claim-delay stress report")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "reserve_delay_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "reserve_delay_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"reserve delay rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
