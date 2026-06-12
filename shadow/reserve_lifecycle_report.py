from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path

from . import constants as C
from .economic_suite import fixture_events
from .insurance_reserve_report import ReserveEvent
from .insurance_reserve_report import _fixture_event_to_reserve, _live_events


HORIZON_DAYS = (30, 90)
CLAIM_SCENARIOS = (
    ("charged correcting markout", Fraction(1, 1)),
    ("all truth-correcting markout", Fraction(1, 1)),
)


@dataclass(frozen=True)
class LifecyclePolicy:
    name: str
    initial_seed_multiple: float
    target_buffer_multiple: float
    withdrawal_period_days: int
    surplus_skim_rate: float
    balance_churn_rate: float


POLICIES = (
    LifecyclePolicy("zero seed compound", 0.0, 0.0, 0, 0.0, 0.0),
    LifecyclePolicy("seeded compound", 1.0, 1.0, 0, 0.0, 0.0),
    LifecyclePolicy("monthly 25% surplus skim", 1.0, 1.0, 30, 0.25, 0.0),
    LifecyclePolicy("monthly 10% LP churn", 1.0, 1.0, 30, 0.0, 0.10),
    LifecyclePolicy("weekly 25% surplus skim", 1.0, 1.0, 7, 0.25, 0.0),
)


@dataclass(frozen=True)
class LifecycleRow:
    window: str
    horizon_days: int
    claim_basis: str
    payout_rate: float
    policy: str
    rows: int
    initial_seed_e6: int
    target_buffer_e6: int
    premium_e6: int
    claims_e6: int
    withdrawals_e6: int
    ending_balance_e6: int
    min_balance_e6: int
    required_topup_e6: int
    deficit_events: int
    withdrawal_events: int
    survived_without_topup: bool
    withdrawal_share_of_premium: float | None
    ending_coverage_ratio: float | None
    model: str


def compute(root: Path | None = None, live_db: Path | None = None) -> dict:
    root = root or C.repo_root()
    rows: list[LifecycleRow] = []
    live_events = _live_events(live_db or root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    if live_events:
        rows.extend(_window_rows("live shadow", live_events))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        rows.extend(_window_rows(window, [_fixture_event_to_reserve(event) for event in fixture]))
    return {
        "model": (
            "compressed daily lifecycle replay. Each historical window is treated as one representative day and "
            "replayed for 30d/90d horizons. Premium funds the reserve; claims follow the listed promise; skim/churn "
            "policies withdraw reserve capital on schedule."
        ),
        "horizon_days": list(HORIZON_DAYS),
        "claim_scenarios": [
            {"claim_basis": basis, "payout_rate": float(rate)}
            for basis, rate in CLAIM_SCENARIOS
        ],
        "policies": [asdict(policy) for policy in POLICIES],
        "rows": [asdict(row) for row in rows],
    }


def markdown(report: dict) -> str:
    lines = [
        "# Reserve Lifecycle Churn",
        "",
        "This report turns the reserve solvency rows into a lifecycle stress with",
        "scheduled LP exits and reserve withdrawals.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "",
        "| Window | Horizon | Claim basis | Policy | Seed | Premium | Claims | Withdrawals | Ending reserve | Required top-up | Withdrawal/premium | Survived |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {int(row['horizon_days'])}d | {row['claim_basis']} | {row['policy']} | "
            f"{_usd(int(row['initial_seed_e6']))} | {_usd(int(row['premium_e6']))} | "
            f"{_usd(int(row['claims_e6']))} | {_usd(int(row['withdrawals_e6']))} | "
            f"{_usd(int(row['ending_balance_e6']))} | {_usd(int(row['required_topup_e6']))} | "
            f"{_pct(row.get('withdrawal_share_of_premium'))} | {'yes' if row['survived_without_topup'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `zero seed compound` shows whether premium timing alone can carry the promise.",
            "- Seeded rows start with one observed-window required seed as a target reserve buffer.",
            "- Skim rows remove surplus above the target buffer; churn rows model LP exits withdrawing part of total reserve.",
            "- This is a lifecycle model, not a claim implementation in the hook.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def lifecycle_rows(window: str, events: list[ReserveEvent]) -> list[LifecycleRow]:
    return [
        _simulate(window, events, horizon_days, claim_basis, payout_rate, policy)
        for horizon_days in HORIZON_DAYS
        for claim_basis, payout_rate in CLAIM_SCENARIOS
        for policy in POLICIES
    ]


def _window_rows(window: str, events: list[ReserveEvent]) -> list[LifecycleRow]:
    return lifecycle_rows(window, events)


def _simulate(
    window: str,
    events: list[ReserveEvent],
    horizon_days: int,
    claim_basis: str,
    payout_rate: Fraction,
    policy: LifecyclePolicy,
) -> LifecycleRow:
    seed = _required_seed(events, claim_basis, payout_rate)
    initial_seed = int(round(seed * policy.initial_seed_multiple))
    target_buffer = int(round(seed * policy.target_buffer_multiple))
    balance = initial_seed
    min_balance = balance
    premium = 0
    claims = 0
    withdrawals = 0
    deficit_events = 0
    withdrawal_events = 0

    for day in range(horizon_days):
        for event in events:
            claim = _payout(_claimable_markout(event, claim_basis), payout_rate)
            balance += event.extra_e6 - claim
            premium += event.extra_e6
            claims += claim
            if balance < 0:
                deficit_events += 1
            min_balance = min(min_balance, balance)
        if policy.withdrawal_period_days > 0 and (day + 1) % policy.withdrawal_period_days == 0:
            amount = _withdrawal(balance, target_buffer, policy)
            if amount > 0:
                balance -= amount
                withdrawals += amount
                withdrawal_events += 1
                min_balance = min(min_balance, balance)

    required_topup = max(0, -min_balance)
    return LifecycleRow(
        window=window,
        horizon_days=horizon_days,
        claim_basis=claim_basis,
        payout_rate=float(payout_rate),
        policy=policy.name,
        rows=len(events) * horizon_days,
        initial_seed_e6=initial_seed,
        target_buffer_e6=target_buffer,
        premium_e6=premium,
        claims_e6=claims,
        withdrawals_e6=withdrawals,
        ending_balance_e6=balance,
        min_balance_e6=min_balance,
        required_topup_e6=required_topup,
        deficit_events=deficit_events,
        withdrawal_events=withdrawal_events,
        survived_without_topup=required_topup == 0,
        withdrawal_share_of_premium=(withdrawals / premium) if premium else None,
        ending_coverage_ratio=(balance / claims) if claims > 0 else None,
        model="compressed daily replay with scheduled withdrawals",
    )


def _required_seed(events: list[ReserveEvent], claim_basis: str, payout_rate: Fraction) -> int:
    balance = 0
    min_balance = 0
    for event in events:
        balance += event.extra_e6 - _payout(_claimable_markout(event, claim_basis), payout_rate)
        min_balance = min(min_balance, balance)
    return max(0, -min_balance)


def _withdrawal(balance: int, target_buffer: int, policy: LifecyclePolicy) -> int:
    surplus = max(0, balance - target_buffer)
    skim = int(surplus * policy.surplus_skim_rate)
    churn = int(max(0, balance) * policy.balance_churn_rate)
    return min(max(0, balance), skim + churn)


def _claimable_markout(event: ReserveEvent, claim_basis: str) -> int:
    positive_markout = max(0, event.truth_markout_e6)
    if claim_basis == "charged correcting markout":
        return positive_markout if event.extra_e6 > 0 and event.truth_corr == 1 else 0
    if claim_basis == "all truth-correcting markout":
        return positive_markout if event.truth_corr == 1 else 0
    raise ValueError(f"unknown claim basis: {claim_basis}")


def _payout(value_e6: int, payout_rate: Fraction) -> int:
    return (value_e6 * payout_rate.numerator) // payout_rate.denominator


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate reserve lifecycle churn stress")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "live_shadow_20260607T082122Z.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "reserve_lifecycle_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "reserve_lifecycle_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"reserve lifecycle rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["rows"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
