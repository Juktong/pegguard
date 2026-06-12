from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from . import constants as C
from .db import connect
from .pipeline import deviation_e2, ema_update, is_correcting, premium_pips

DECISIONS = ("fresh", "lag2", "lag5")
ORACLE_FALLBACK_REASONS = {"STALE_OR_MISSING", "CONF_SPIKE", "BAD_PRICE"}
PIPS_DENOM = 1_000_000


@dataclass(frozen=True)
class LabelAttribution:
    label: str
    rows: int
    valid_truth_rows: int
    fallback_rows: int
    oracle_fallback_rows: int
    oracle_fallback_notional_e6: int
    opportunity_rows: int
    opportunity_notional_e6: int
    actual_extra_e6: int
    missed_extra_e6: int
    truth_missed_extra_e6: int
    missed_correct_extra_e6: int
    missed_precision: float | None
    missed_truth_capture: float | None


@dataclass(frozen=True)
class ReasonAttribution:
    label: str
    reason: str
    rows: int
    valid_truth_rows: int
    opportunity_rows: int
    notional_e6: int
    missed_extra_e6: int
    truth_missed_extra_e6: int
    missed_correct_extra_e6: int
    missed_precision: float | None
    missed_truth_capture: float | None


@dataclass(frozen=True)
class FallbackAttribution:
    database: str
    rows: int
    valid_truth_rows: int
    truth_markout_e6: int
    labels: list[LabelAttribution]
    reasons: list[ReasonAttribution]


@dataclass
class _Agg:
    rows: int = 0
    valid_truth_rows: int = 0
    fallback_rows: int = 0
    oracle_fallback_rows: int = 0
    oracle_fallback_notional_e6: int = 0
    opportunity_rows: int = 0
    opportunity_notional_e6: int = 0
    notional_e6: int = 0
    actual_extra_e6: int = 0
    missed_extra_e6: int = 0
    truth_missed_extra_e6: int = 0
    missed_correct_extra_e6: int = 0


def compute(db: Path) -> FallbackAttribution:
    conn = connect(db)
    try:
        rows = conn.execute(
            """
            SELECT l.*, t.valid, t.truth_corr, t.truth_mk_e6
            FROM ledger l LEFT JOIN truth t ON t.ledger_id = l.id
            ORDER BY l.ts_ms, l.block_number, l.log_index, l.id
            """
        ).fetchall()
    finally:
        conn.close()

    valid_truth_rows = [row for row in rows if row["valid"]]
    truth_markout_e6 = sum(int(row["truth_mk_e6"] or 0) for row in valid_truth_rows)
    abs_truth_markout_e6 = abs(truth_markout_e6)
    label_aggs = {label: _Agg() for label in DECISIONS}
    reason_aggs: dict[tuple[str, str], _Agg] = defaultdict(_Agg)

    basis_wad = 0
    last_obs_t_ms = 0
    for row in rows:
        valid = bool(row["valid"])
        truth_corr = int(row["truth_corr"] or 0)
        notional_e6 = abs(int(row["aq_e6"]))

        for label in DECISIONS:
            reason = str(row[f"{label}_fallback_reason"] or "")
            actual_extra_e6 = int(row[f"{label}_extra_e6"] or 0)
            potential_extra_e6, potential_pips = _counterfactual_extra(row, label, basis_wad)
            missed_extra_e6 = max(0, potential_extra_e6 - actual_extra_e6)

            label_agg = label_aggs[label]
            label_agg.rows += 1
            label_agg.actual_extra_e6 += actual_extra_e6
            if valid:
                label_agg.valid_truth_rows += 1
            if reason:
                label_agg.fallback_rows += 1
                if reason in ORACLE_FALLBACK_REASONS:
                    label_agg.oracle_fallback_rows += 1
                    label_agg.oracle_fallback_notional_e6 += notional_e6
                    if potential_pips > 0:
                        label_agg.opportunity_rows += 1
                        label_agg.opportunity_notional_e6 += notional_e6
                    label_agg.missed_extra_e6 += missed_extra_e6
                    if valid:
                        label_agg.truth_missed_extra_e6 += missed_extra_e6
                        if truth_corr == 1:
                            label_agg.missed_correct_extra_e6 += missed_extra_e6

                    reason_agg = reason_aggs[(label, reason)]
                    reason_agg.rows += 1
                    reason_agg.notional_e6 += notional_e6
                    if valid:
                        reason_agg.valid_truth_rows += 1
                        reason_agg.truth_missed_extra_e6 += missed_extra_e6
                        if truth_corr == 1:
                            reason_agg.missed_correct_extra_e6 += missed_extra_e6
                    reason_agg.missed_extra_e6 += missed_extra_e6
                    if potential_pips > 0:
                        reason_agg.opportunity_rows += 1
                        reason_agg.opportunity_notional_e6 += notional_e6

        # Match the live pipeline's basis hygiene: an unseeded basis is still
        # updated when the oracle itself is healthy; stale/conf/bad-price rows
        # do not update the basis.
        fresh_reason = str(row["fresh_fallback_reason"] or "")
        fresh_fair = _int_or_none(row["fresh_fair_e18"])
        if fresh_fair and fresh_fair > 0 and fresh_reason not in ORACLE_FALLBACK_REASONS:
            obs_wad = (int(row["post_mid_e18"]) * C.WAD) // fresh_fair
            dt_sec = 0 if last_obs_t_ms == 0 else max(0, (int(row["ts_ms"]) - last_obs_t_ms) // 1000)
            basis_wad = ema_update(basis_wad, obs_wad, dt_sec, C.TAU_SEC)
            last_obs_t_ms = int(row["ts_ms"])

    labels = [
        LabelAttribution(
            label=label,
            rows=agg.rows,
            valid_truth_rows=agg.valid_truth_rows,
            fallback_rows=agg.fallback_rows,
            oracle_fallback_rows=agg.oracle_fallback_rows,
            oracle_fallback_notional_e6=agg.oracle_fallback_notional_e6,
            opportunity_rows=agg.opportunity_rows,
            opportunity_notional_e6=agg.opportunity_notional_e6,
            actual_extra_e6=agg.actual_extra_e6,
            missed_extra_e6=agg.missed_extra_e6,
            truth_missed_extra_e6=agg.truth_missed_extra_e6,
            missed_correct_extra_e6=agg.missed_correct_extra_e6,
            missed_precision=_ratio(agg.missed_correct_extra_e6, agg.truth_missed_extra_e6),
            missed_truth_capture=_ratio(agg.truth_missed_extra_e6, abs_truth_markout_e6),
        )
        for label, agg in label_aggs.items()
    ]
    reasons = [
        ReasonAttribution(
            label=label,
            reason=reason,
            rows=agg.rows,
            valid_truth_rows=agg.valid_truth_rows,
            opportunity_rows=agg.opportunity_rows,
            notional_e6=agg.notional_e6,
            missed_extra_e6=agg.missed_extra_e6,
            truth_missed_extra_e6=agg.truth_missed_extra_e6,
            missed_correct_extra_e6=agg.missed_correct_extra_e6,
            missed_precision=_ratio(agg.missed_correct_extra_e6, agg.truth_missed_extra_e6),
            missed_truth_capture=_ratio(agg.truth_missed_extra_e6, abs_truth_markout_e6),
        )
        for (label, reason), agg in sorted(reason_aggs.items())
    ]
    return FallbackAttribution(str(db), len(rows), len(valid_truth_rows), truth_markout_e6, labels, reasons)


def markdown(report: FallbackAttribution) -> str:
    lines = [
        "# Fallback Attribution",
        "",
        "This report estimates same-swap premium suppressed by oracle fallback.",
        "It is a local counterfactual: it prices fallback rows against the same",
        "basis state when an oracle value was present, and does not assume those",
        "swaps would still route after a premium.",
        "",
        "## Snapshot",
        "",
        f"- Database: `{report.database}`",
        f"- Swaps: {report.rows}",
        f"- Valid truth rows: {report.valid_truth_rows}",
        f"- Truth markout denominator: {_usd(report.truth_markout_e6)}",
        "",
        "## Decision Attribution",
        "",
        "| Decision | Fallback rows | Oracle fallback rows | Oracle fallback notional | Opportunity rows | Opportunity notional | Actual extra | Missed extra | Truth-known missed | Missed precision | Missed truth capture |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.labels:
        lines.append(
            f"| {row.label} | {row.fallback_rows} | {row.oracle_fallback_rows} | "
            f"{_usd(row.oracle_fallback_notional_e6)} | {row.opportunity_rows} | {_usd(row.opportunity_notional_e6)} | "
            f"{_usd(row.actual_extra_e6)} | {_usd(row.missed_extra_e6)} | {_usd(row.truth_missed_extra_e6)} | {_pct(row.missed_precision)} | "
            f"{_pct(row.missed_truth_capture)} |"
        )
    lines.extend(
        [
            "",
            "## Reason Breakdown",
            "",
            "| Decision | Reason | Rows | Valid truth rows | Opportunity rows | Notional | Missed extra | Truth-known missed | Missed precision | Missed truth capture |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in report.reasons:
        lines.append(
            f"| {row.label} | {row.reason} | {row.rows} | {row.valid_truth_rows} | {row.opportunity_rows} | "
            f"{_usd(row.notional_e6)} | {_usd(row.missed_extra_e6)} | {_usd(row.truth_missed_extra_e6)} | {_pct(row.missed_precision)} | "
            f"{_pct(row.missed_truth_capture)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `fresh` is the actual hot-path oracle decision.",
            "- `lag2` and `lag5` are delayed-oracle sensitivity decisions.",
            "- `BASIS_UNSEEDED` is excluded from oracle-fallback attribution because it is not an oracle failure.",
            "- Missed extra is total same-state suppressed premium; precision/capture use only the truth-known subset.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: FallbackAttribution, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(asdict(report), indent=2, sort_keys=True), encoding="utf-8")


def _counterfactual_extra(row: sqlite3.Row, label: str, basis_wad: int) -> tuple[int, int]:
    if basis_wad == 0:
        return 0, 0
    fair_e18 = _int_or_none(row[f"{label}_fair_e18"])
    if fair_e18 is None or fair_e18 <= 0:
        return 0, 0
    dev_e2, _ = deviation_e2(int(row["pre_mid_e18"]), fair_e18, basis_wad)
    if not is_correcting(dev_e2, bool(int(row["zero_for_one"]))):
        return 0, 0
    deadband_e2 = C.DEADBAND_VOL_E2 if str(row["regime"]) == "VOLATILE" else C.DEADBAND_CALM_E2
    pips = premium_pips(abs(dev_e2), deadband_e2, C.ALPHA_NUM, C.ALPHA_DEN, C.CAP_PIPS)
    return (abs(int(row["aq_e6"])) * pips) // PIPS_DENOM, pips


def _int_or_none(value: object) -> int | None:
    if value is None:
        return None
    text = str(value)
    if not text:
        return None
    return int(text)


def _ratio(num: int, den: int) -> float | None:
    if den == 0:
        return None
    return num / den


def _usd(value_e6: int) -> str:
    sign = "-" if value_e6 < 0 else ""
    return f"{sign}${abs(value_e6) / 1_000_000:,.2f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2%}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Attribute premium suppressed by oracle fallback")
    parser.add_argument("--database", type=Path, default=root / "shadow" / "shadow.sqlite3")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "fallback_attribution.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "fallback_attribution.json")
    args = parser.parse_args()
    report = compute(args.database)
    write_outputs(report, args.out_md, args.out_json)
    fresh = next((row for row in report.labels if row.label == "fresh"), None)
    missed = fresh.missed_extra_e6 if fresh else 0
    print(f"fallback attribution: swaps={report.rows} fresh_missed={_usd(missed)}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
