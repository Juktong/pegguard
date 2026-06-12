from __future__ import annotations

import argparse
import json
import random
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .economic_suite import BASE_FEE_PIPS, PIPS_DENOM, fixture_events

ITERATIONS = 500
SEED = 1337


@dataclass(frozen=True)
class BootEvent:
    notional_e6: int
    base_fee_e6: int
    extra_e6: int
    markout_e6: int
    premium_total_e6: int
    premium_correct_e6: int


@dataclass(frozen=True)
class BootstrapWindow:
    window: str
    rows: int
    iterations: int
    seed: int
    net_bps_p05: float
    net_bps_p50: float
    net_bps_p95: float
    precision_p05: float | None
    precision_p50: float | None
    precision_p95: float | None
    capture_p05: float | None
    capture_p50: float | None
    capture_p95: float | None
    positive_net_probability: float
    precision_ge_90_probability: float | None
    capture_floor: float
    capture_ge_floor_probability: float | None


def compute(root: Path | None = None, live_db: Path | None = None, iterations: int = ITERATIONS, seed: int = SEED) -> dict:
    root = root or C.repo_root()
    windows: list[BootstrapWindow] = []
    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        windows.append(bootstrap_window("live shadow", live_events, iterations, seed))
    for window in ("calm", "vol"):
        fixture, _ = fixture_events(root, window)
        windows.append(bootstrap_window(window, [_fixture_event_to_boot(event) for event in fixture], iterations, seed))
    return {"iterations": iterations, "seed": seed, "windows": [asdict(row) for row in windows]}


def bootstrap_window(window: str, events: list[BootEvent], iterations: int = ITERATIONS, seed: int = SEED) -> BootstrapWindow:
    rng = random.Random(f"{seed}:{window}")
    net_bps_values: list[float] = []
    precision_values: list[float] = []
    capture_values: list[float] = []
    positive_net = 0
    precision_ge_90 = 0
    capture_ge_floor = 0
    precision_trials = 0
    capture_trials = 0
    capture_floor = 0.15 if window == "vol" else 0.08
    rows = len(events)

    for _ in range(iterations):
        sample = [events[rng.randrange(rows)] for _ in range(rows)] if rows else []
        notional = sum(event.notional_e6 for event in sample)
        extra = sum(event.extra_e6 for event in sample)
        markout = sum(event.markout_e6 for event in sample)
        premium_total = sum(event.premium_total_e6 for event in sample)
        premium_correct = sum(event.premium_correct_e6 for event in sample)
        net = sum(event.base_fee_e6 + event.extra_e6 - event.markout_e6 for event in sample)

        net_bps_values.append(_bps(net, notional))
        if net >= 0:
            positive_net += 1
        if premium_total > 0:
            precision = premium_correct / premium_total
            precision_values.append(precision)
            precision_trials += 1
            if precision >= 0.90:
                precision_ge_90 += 1
        if markout != 0:
            capture = extra / abs(markout)
            capture_values.append(capture)
            capture_trials += 1
            if capture >= capture_floor:
                capture_ge_floor += 1

    return BootstrapWindow(
        window=window,
        rows=rows,
        iterations=iterations,
        seed=seed,
        net_bps_p05=_pctl_float(net_bps_values, 5),
        net_bps_p50=_pctl_float(net_bps_values, 50),
        net_bps_p95=_pctl_float(net_bps_values, 95),
        precision_p05=_pctl_optional(precision_values, 5),
        precision_p50=_pctl_optional(precision_values, 50),
        precision_p95=_pctl_optional(precision_values, 95),
        capture_p05=_pctl_optional(capture_values, 5),
        capture_p50=_pctl_optional(capture_values, 50),
        capture_p95=_pctl_optional(capture_values, 95),
        positive_net_probability=positive_net / iterations if iterations else 0.0,
        precision_ge_90_probability=(precision_ge_90 / precision_trials) if precision_trials else None,
        capture_floor=capture_floor,
        capture_ge_floor_probability=(capture_ge_floor / capture_trials) if capture_trials else None,
    )


def markdown(report: dict) -> str:
    lines = [
        "# Bootstrap Robustness",
        "",
        "This report resamples valid-truth swap events with replacement to show how",
        "sensitive measured economics are to event mix. It is measurement only and",
        "does not change calibration constants.",
        "",
        f"- Iterations: {int(report.get('iterations', 0))}",
        f"- Seed: {int(report.get('seed', 0))}",
        "",
        "| Window | Rows | Net bps p05/p50/p95 | Precision p05/p50/p95 | Capture p05/p50/p95 | P(net>=0) | P(precision>=90%) | Capture floor | P(capture>=floor) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("windows", []):
        lines.append(
            f"| {row['window']} | {int(row['rows'])} | "
            f"{float(row['net_bps_p05']):.2f} / {float(row['net_bps_p50']):.2f} / {float(row['net_bps_p95']):.2f} | "
            f"{_pct_triplet(row.get('precision_p05'), row.get('precision_p50'), row.get('precision_p95'))} | "
            f"{_pct_triplet(row.get('capture_p05'), row.get('capture_p50'), row.get('capture_p95'))} | "
            f"{float(row['positive_net_probability']):.2%} | {_pct(row.get('precision_ge_90_probability'))} | "
            f"{float(row['capture_floor']):.2%} | {_pct(row.get('capture_ge_floor_probability'))} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Wide bands mean the point estimate depends heavily on the sampled event mix.",
            "- `live shadow` only includes rows with valid truth labels, so it will stabilize as truth coverage rises.",
            "- Capture floors use the permanent economics floors: 8% for calm/live and 15% for volatile.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _fixture_event_to_boot(event) -> BootEvent:
    base = (event.notional_e6 * BASE_FEE_PIPS) // PIPS_DENOM
    premium_total = event.peg_extra_e6 if event.peg_premium_pips > 0 else 0
    premium_correct = premium_total if event.truth_corr == 1 else 0
    return BootEvent(event.notional_e6, base, event.peg_extra_e6, event.truth_markout_e6, premium_total, premium_correct)


def _live_events(db: Path) -> list[BootEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.aq_e6, l.fresh_extra_e6, l.fresh_premium_pips, t.truth_corr, t.truth_mk_e6
            FROM ledger l JOIN truth t ON t.ledger_id = l.id
            WHERE t.valid = 1
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()
    events = []
    for row in rows:
        notional = abs(int(row["aq_e6"]))
        base = (notional * BASE_FEE_PIPS) // PIPS_DENOM
        extra = int(row["fresh_extra_e6"] or 0)
        premium_total = extra if int(row["fresh_premium_pips"] or 0) > 0 else 0
        premium_correct = premium_total if int(row["truth_corr"] or 0) == 1 else 0
        events.append(BootEvent(notional, base, extra, int(row["truth_mk_e6"] or 0), premium_total, premium_correct))
    return events


def _bps(value_e6: int, notional_e6: int) -> float:
    if notional_e6 == 0:
        return 0.0
    return value_e6 / notional_e6 * 10_000


def _pctl_float(values: list[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[(len(ordered) * pct) // 100]


def _pctl_optional(values: list[float], pct: int) -> float | None:
    if not values:
        return None
    return _pctl_float(values, pct)


def _pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2%}"


def _pct_triplet(p05: object, p50: object, p95: object) -> str:
    if p05 is None or p50 is None or p95 is None:
        return "n/a"
    return f"{float(p05):.2%} / {float(p50):.2%} / {float(p95):.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Bootstrap PegGuard economic robustness from valid-truth events")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--iterations", type=int, default=ITERATIONS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "bootstrap_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "bootstrap_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db, args.iterations, args.seed)
    write_outputs(report, args.out_md, args.out_json)
    print(f"bootstrap windows={len(report['windows'])} iterations={args.iterations}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
