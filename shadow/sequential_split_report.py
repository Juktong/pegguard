from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .pipeline import deviation_e2, ema_update, is_correcting, premium_pips

PIPS_DENOM = 1_000_000
SCENARIOS: tuple[tuple[int, int], ...] = (
    (2, 0),
    (5, 0),
    (10, 0),
    (25, 0),
    (5, 5),
    (10, 5),
    (5, 30),
    (10, 30),
)


@dataclass(frozen=True)
class SequenceEvent:
    t_ms: int
    pre_mid_e18: int
    post_mid_e18: int
    fair_e18: int
    ab_e18: int
    aq_e6: int
    valid: bool
    truth_corr: int
    truth_mk_e6: int
    update_basis: bool
    deadband_e2: int


@dataclass(frozen=True)
class SimMetric:
    events: int
    valid_events: int
    notional_e6: int
    markout_e6: int
    extra_e6: int
    premium_total_e6: int
    premium_correct_e6: int
    charged_events: int
    event_extras: tuple[int, ...]

    @property
    def precision(self) -> float | None:
        if self.premium_total_e6 == 0:
            return None
        return self.premium_correct_e6 / self.premium_total_e6

    @property
    def capture(self) -> float | None:
        if self.markout_e6 == 0:
            return None
        return self.extra_e6 / abs(self.markout_e6)


@dataclass(frozen=True)
class SequentialSplitRow:
    window: str
    child_count: int
    child_spacing_sec: int
    events: int
    valid_events: int
    notional_e6: int
    markout_e6: int
    original_extra_e6: int
    split_extra_e6: int
    leaked_extra_e6: int
    leakage_rate: float | None
    leakage_bps_of_notional: float
    original_charged_events: int
    split_charged_events: int
    original_precision: float | None
    split_precision: float | None
    original_capture: float | None
    split_capture: float | None
    max_abs_event_delta_e6: int


def compute(root: Path | None = None, live_db: Path | None = None, scenarios: tuple[tuple[int, int], ...] = SCENARIOS) -> dict:
    root = root or C.repo_root()
    rows: list[SequentialSplitRow] = []

    live_events = _live_events(live_db or root / "shadow" / "shadow.sqlite3")
    if live_events:
        rows.extend(sequential_rows("live shadow", live_events, scenarios))

    for window in ("calm", "vol"):
        rows.extend(sequential_rows(window, _fixture_events(root, window), scenarios))

    return {
        "model": (
            "linearized child mid path; no-split baseline and split rows both use hook timestamp semantics; "
            "spacing=0 keeps child swaps in one timestamp, spacing>0 advances the basis EMA between children"
        ),
        "scenarios": [{"child_count": count, "child_spacing_sec": spacing} for count, spacing in scenarios],
        "rows": [asdict(row) for row in rows],
    }


def sequential_rows(
    window: str,
    events: list[SequenceEvent],
    scenarios: tuple[tuple[int, int], ...] = SCENARIOS,
) -> list[SequentialSplitRow]:
    baseline = _simulate(events, child_count=1, child_spacing_sec=0)
    return [_row(window, events, baseline, count, spacing) for count, spacing in scenarios]


def markdown(report: dict) -> str:
    lines = [
        "# Sequential Split Timing Sensitivity",
        "",
        "This report checks a stronger split scenario than same-signal notional",
        "splitting: a trader breaks an event into child swaps and the hook updates",
        "basis after each child. It is still a model, not router behavior.",
        "",
        f"- Model: {report.get('model', 'n/a')}",
        "- Positive leaked extra means the split paid less premium than the no-split baseline.",
        "- Negative leaked extra means the split paid more premium.",
        "",
        "| Window | Children | Spacing | Events | Notional | No-split extra | Split extra | Leaked extra | Leakage | Leakage bps | Charged before/after | Precision before/after | Capture before/after | Max event delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['window']} | {int(row['child_count'])} | {int(row['child_spacing_sec'])}s | "
            f"{int(row['valid_events'])}/{int(row['events'])} | {_usd(int(row['notional_e6']))} | "
            f"{_usd(int(row['original_extra_e6']))} | {_usd(int(row['split_extra_e6']))} | "
            f"{_usd(int(row['leaked_extra_e6']))} | {_pct(row.get('leakage_rate'))} | "
            f"{float(row['leakage_bps_of_notional']):.6f} | "
            f"{int(row['original_charged_events'])}/{int(row['split_charged_events'])} | "
            f"{_pct(row.get('original_precision'))} / {_pct(row.get('split_precision'))} | "
            f"{_pct(row.get('original_capture'))} / {_pct(row.get('split_capture'))} | "
            f"{_usd(int(row['max_abs_event_delta_e6']))} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `spacing=0` uses same-timestamp hook semantics; the basis EMA does not advance between children after it has been seeded.",
            "- `spacing>0` models an adversarial wait between child swaps while reusing the same oracle path and a linearized pool-mid path.",
            "- This does not measure real route-away elasticity, mempool competition, or router child-ordering behavior.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _row(
    window: str,
    events: list[SequenceEvent],
    baseline: SimMetric,
    child_count: int,
    child_spacing_sec: int,
) -> SequentialSplitRow:
    split = _simulate(events, child_count, child_spacing_sec)
    leaked = baseline.extra_e6 - split.extra_e6
    max_delta = max(
        (abs(original - split_extra) for original, split_extra in zip(baseline.event_extras, split.event_extras, strict=True)),
        default=0,
    )
    return SequentialSplitRow(
        window=window,
        child_count=child_count,
        child_spacing_sec=child_spacing_sec,
        events=baseline.events,
        valid_events=baseline.valid_events,
        notional_e6=baseline.notional_e6,
        markout_e6=baseline.markout_e6,
        original_extra_e6=baseline.extra_e6,
        split_extra_e6=split.extra_e6,
        leaked_extra_e6=leaked,
        leakage_rate=(leaked / baseline.extra_e6) if baseline.extra_e6 else None,
        leakage_bps_of_notional=_bps(leaked, baseline.notional_e6),
        original_charged_events=baseline.charged_events,
        split_charged_events=split.charged_events,
        original_precision=baseline.precision,
        split_precision=split.precision,
        original_capture=baseline.capture,
        split_capture=split.capture,
        max_abs_event_delta_e6=max_delta,
    )


def _simulate(events: list[SequenceEvent], child_count: int, child_spacing_sec: int) -> SimMetric:
    if child_count <= 0:
        raise ValueError("child_count must be positive")
    if child_spacing_sec < 0:
        raise ValueError("child_spacing_sec must be non-negative")

    basis_wad = 0
    last_obs_t_ms = 0
    valid_events = 0
    notional_e6 = 0
    markout_e6 = 0
    extra_e6 = 0
    premium_total_e6 = 0
    premium_correct_e6 = 0
    charged_events = 0
    event_extras: list[int] = []

    for event in events:
        event_extra = 0
        event_charged = False
        event_premium_total = 0

        for child_idx in range(child_count):
            child_ts_ms = event.t_ms + child_idx * child_spacing_sec * 1000
            child_pre_mid = _interp(event.pre_mid_e18, event.post_mid_e18, child_idx, child_count)
            child_post_mid = _interp(event.pre_mid_e18, event.post_mid_e18, child_idx + 1, child_count)
            child_ab_e18 = _split_signed(event.ab_e18, child_count, child_idx)
            child_aq_e6 = _split_signed(event.aq_e6, child_count, child_idx)
            child_pips = _child_pips(basis_wad, child_pre_mid, event.fair_e18, child_ab_e18, event.deadband_e2)
            child_extra = (abs(child_aq_e6) * child_pips) // PIPS_DENOM

            if child_pips > 0:
                event_charged = True
                event_premium_total += child_extra
            event_extra += child_extra

            if event.update_basis and event.fair_e18 > 0 and child_post_mid > 0:
                obs_wad = (child_post_mid * C.WAD) // event.fair_e18
                dt_sec = 0 if last_obs_t_ms == 0 else max(0, (child_ts_ms - last_obs_t_ms) // 1000)
                basis_wad = ema_update(basis_wad, obs_wad, dt_sec, C.TAU_SEC)
                last_obs_t_ms = child_ts_ms

        if event.valid:
            valid_events += 1
            notional_e6 += abs(event.aq_e6)
            markout_e6 += event.truth_mk_e6
            extra_e6 += event_extra
            event_extras.append(event_extra)
            if event_charged:
                charged_events += 1
                premium_total_e6 += event_premium_total
                if event.truth_corr == 1:
                    premium_correct_e6 += event_premium_total

    return SimMetric(
        events=len(events),
        valid_events=valid_events,
        notional_e6=notional_e6,
        markout_e6=markout_e6,
        extra_e6=extra_e6,
        premium_total_e6=premium_total_e6,
        premium_correct_e6=premium_correct_e6,
        charged_events=charged_events,
        event_extras=tuple(event_extras),
    )


def _child_pips(basis_wad: int, pre_mid_e18: int, fair_e18: int, ab_e18: int, deadband_e2: int) -> int:
    if basis_wad == 0 or pre_mid_e18 <= 0 or fair_e18 <= 0:
        return 0
    dev_e2, _ = deviation_e2(pre_mid_e18, fair_e18, basis_wad)
    if not is_correcting(dev_e2, ab_e18 > 0):
        return 0
    return premium_pips(abs(dev_e2), deadband_e2, C.ALPHA_NUM, C.ALPHA_DEN, C.CAP_PIPS)


def _fixture_events(root: Path, window: str) -> list[SequenceEvent]:
    if window == "calm":
        rows = _load_json(root / "test" / "fixtures" / "calm_0530.json")
        truth_rows = _load_json(root / "test" / "fixtures" / "calm_0530_truth.json")
        deadband = C.DEADBAND_CALM_E2
    elif window == "vol":
        rows = _load_json(root / "test" / "fixtures" / "vol_0523_hot90m.json")
        truth_rows = _load_json(root / "test" / "fixtures" / "vol_0523_truth.json")
        deadband = C.DEADBAND_VOL_E2
    else:
        raise ValueError(f"unknown fixture window: {window}")

    events: list[SequenceEvent] = []
    prev_mid_e18 = 0
    for row, truth in zip(rows, truth_rows, strict=True):
        t_ms = int(row["t_ms"])
        if t_ms != int(truth["t_ms"]):
            raise AssertionError(f"{window} t_ms mismatch")
        post_mid_e18 = int(row["p_e18"])
        pre_mid_e18 = prev_mid_e18 if prev_mid_e18 > 0 else post_mid_e18
        events.append(
            SequenceEvent(
                t_ms=t_ms,
                pre_mid_e18=pre_mid_e18,
                post_mid_e18=post_mid_e18,
                fair_e18=int(row["fair_e18"]),
                ab_e18=int(row["ab_e18"]),
                aq_e6=int(row["aq_e6"]),
                valid=bool(truth.get("valid")),
                truth_corr=int(truth.get("truth_corr", 0) or 0),
                truth_mk_e6=int(truth.get("truth_mk_e6", 0) or 0),
                update_basis=True,
                deadband_e2=deadband,
            )
        )
        prev_mid_e18 = post_mid_e18
    return events


def _live_events(db: Path) -> list[SequenceEvent]:
    if not db.exists():
        return []
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.id
            """
        ).fetchall()
    finally:
        conn.close()

    events: list[SequenceEvent] = []
    for row in rows:
        fair_text = row["fresh_fair_e18"]
        fair_e18 = int(fair_text) if fair_text else 0
        fallback = str(row["fresh_fallback_reason"] or "")
        update_basis = fair_e18 > 0 and fallback not in {"STALE_OR_MISSING", "BAD_PRICE", "CONF_SPIKE"}
        regime = str(row["regime"] or "CALM")
        events.append(
            SequenceEvent(
                t_ms=int(row["ts_ms"]),
                pre_mid_e18=int(row["pre_mid_e18"]),
                post_mid_e18=int(row["post_mid_e18"]),
                fair_e18=fair_e18,
                ab_e18=int(row["ab_e18"]),
                aq_e6=int(row["aq_e6"]),
                valid=bool(row["valid"]),
                truth_corr=int(row["truth_corr"] or 0),
                truth_mk_e6=int(row["truth_mk_e6"] or 0),
                update_basis=update_basis,
                deadband_e2=C.DEADBAND_VOL_E2 if regime == "VOLATILE" else C.DEADBAND_CALM_E2,
            )
        )
    return events


def _split_signed(value: int, count: int, index: int) -> int:
    sign = -1 if value < 0 else 1
    magnitude = abs(value)
    base = magnitude // count
    remainder = magnitude % count
    child = base + (1 if index < remainder else 0)
    return sign * child


def _interp(start: int, end: int, step: int, steps: int) -> int:
    return start + ((end - start) * step) // steps


def _load_json(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    return f"{float(value):.4%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Check sequential split timing sensitivity")
    parser.add_argument("--live-db", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "sequential_split_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "sequential_split_report.json")
    args = parser.parse_args()
    report = compute(root, args.live_db)
    write_outputs(report, args.out_md, args.out_json)
    print(f"sequential split rows={len(report['rows'])}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
