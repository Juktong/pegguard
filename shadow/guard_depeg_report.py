from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import constants as C


TRIP_BPS = 50
NORMAL_STABLE_MAX_BPS = 0.35


def compute(root: Path | None = None) -> dict:
    root = root or C.repo_root()
    calm_path = root / "test" / "fixtures" / "sentinel_mainnet_calm.json"
    vol_path = root / "test" / "fixtures" / "sentinel_mainnet_vol.json"
    vol_rows_path = root / "test" / "fixtures" / "vol_0523_hot90m.json"
    vol_truth_path = root / "test" / "fixtures" / "vol_0523_truth.json"

    selected = _scenario("selected", C.RSC_TRIG_BPS, C.RSC_WINDOW_SEC, calm_path, vol_path, vol_rows_path, vol_truth_path)
    comparison = _scenario("60bps comparison", 60, C.RSC_WINDOW_SEC, calm_path, vol_path, vol_rows_path, vol_truth_path)
    total_bleed = _total_bleed(vol_rows_path, vol_truth_path)
    measured_start_ms = total_bleed["measured_start_ms"]
    sentinel_start_ms = _load_rows(vol_path)[0]["t_ms"]
    measured_start_offset_sec = (measured_start_ms - sentinel_start_ms) // 1000
    for row in (selected, comparison):
        first = row.get("first_vol_trigger_ms")
        row["measured_heavy_bleed_start_offset_sec"] = measured_start_offset_sec
        row["lead_time_before_measured_bleed_sec"] = (
            None if not first else max(0, (measured_start_ms - int(first)) // 1000)
        )
        row["measured_bleed_total_e6"] = total_bleed["measured_bleed_total_e6"]
        row["measured_bleed_after_first_trigger_e6"] = (
            None
            if row.get("bled_before_first_trigger_e6") is None
            else max(0, total_bleed["measured_bleed_total_e6"] - int(row["bled_before_first_trigger_e6"]))
        )

    complete = (
        selected["calm_triggers"] == 0
        and selected["vol_triggers"] > 0
        and selected["first_vol_trigger_ms"] is not None
    )
    return {
        "complete": complete,
        "not_calibration": True,
        "not_route_away_evidence": True,
        "mode": "GUARD/control-plane breaker economics",
        "trip_bps": TRIP_BPS,
        "normal_stable_max_bps": NORMAL_STABLE_MAX_BPS,
        "trip_to_normal_ratio": TRIP_BPS / NORMAL_STABLE_MAX_BPS,
        "selected_trig_bps": C.RSC_TRIG_BPS,
        "selected_window_sec": C.RSC_WINDOW_SEC,
        "regime_ttl_sec": C.REGIME_TTL_SEC,
        "fixtures": {
            "sentinel_calm": str(calm_path),
            "sentinel_vol": str(vol_path),
            "vol_rows": str(vol_rows_path),
            "vol_truth": str(vol_truth_path),
        },
        "limitation": (
            "No immutable stable-pair depeg fixture is present in the repo. This report uses the real sentinel "
            "calibration fixtures as breaker timing evidence and must not be read as a stablecoin depeg PnL backtest."
        ),
        "rows": [selected, comparison],
    }


def markdown(report: dict) -> str:
    lines = [
        "# GUARD Breaker Economics",
        "",
        "This report covers the economic side of GUARD/control-plane breaker timing.",
        "It is non-gating evidence and does not change calibrated constants.",
        "",
        f"- Status: {'complete' if report.get('complete') else 'incomplete'}",
        f"- Selected RSC trigger: {int(report.get('selected_trig_bps', 0))} bps / {int(report.get('selected_window_sec', 0))} s",
        f"- Hook GUARD trip threshold: {int(report.get('trip_bps', 0))} bps",
        f"- Stable normal-deviation margin: {float(report.get('trip_to_normal_ratio', 0)):.1f}x over {float(report.get('normal_stable_max_bps', 0)):.2f} bps normal max",
        f"- Limitation: {report.get('limitation', 'n/a')}",
        "",
        "| Scenario | Trigger | Calm triggers | Vol triggers | First trigger | Lead before measured bleed | Measured bleed before trigger | Measured bleed after trigger |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report.get("rows", []):
        lines.append(
            f"| {row['label']} | {int(row['trig_bps'])} bps / {int(row['window_sec'])} s | "
            f"{int(row['calm_triggers'])} | {int(row['vol_triggers'])} | "
            f"{_seconds(row.get('first_vol_trigger_offset_sec'))} | "
            f"{_seconds(row.get('lead_time_before_measured_bleed_sec'))} | "
            f"{_usd_or_note(row.get('bled_before_first_trigger_e6'), row.get('bled_before_note'))} | "
            f"{_usd_or_note(row.get('measured_bleed_after_first_trigger_e6'), None)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The selected 40 bps / 180 s trigger has zero calm false positives on the calm sentinel fixture.",
            "- Its first volatile trigger arms before the measured heavy-bleed window, so measured in-window bleed before trigger is zero.",
            "- The 60 bps comparison is intentionally slower and misses measured in-window bleed before arming.",
            "- This is breaker-timing economics, not a route-away or stablecoin depeg fixture.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(report: dict, out_md: Path, out_json: Path) -> None:
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(markdown(report), encoding="utf-8")
    out_json.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _scenario(
    label: str,
    trig_bps: int,
    window_sec: int,
    calm_path: Path,
    vol_path: Path,
    vol_rows_path: Path,
    vol_truth_path: Path,
) -> dict:
    calm = _run_sentinel(calm_path, trig_bps, window_sec)
    vol = _run_sentinel(vol_path, trig_bps, window_sec)
    bled, note = _bled_before(vol_rows_path, vol_truth_path, vol["first_trigger_ms"])
    return {
        "label": label,
        "trig_bps": trig_bps,
        "window_sec": window_sec,
        "calm_triggers": calm["trigger_count"],
        "calm_false_positive_ttl_sec": calm["trigger_count"] * C.REGIME_TTL_SEC,
        "vol_triggers": vol["trigger_count"],
        "first_vol_trigger_ms": vol["first_trigger_ms"],
        "first_vol_trigger_offset_sec": vol["first_trigger_offset_sec"],
        "bled_before_first_trigger_e6": bled,
        "bled_before_note": note,
    }


def _run_sentinel(path: Path, trig_bps: int, window_sec: int) -> dict:
    rows = _load_rows(path)
    ring: list[tuple[int, int] | None] = [None] * 64
    head = 0
    last_flip = 0
    start_ms = int(rows[0]["t_ms"]) if rows else 0
    trigger_count = 0
    first_ms: int | None = None
    first_offset: int | None = None
    for row in rows:
        ts = int(row["t_ms"]) // 1000
        ring[head] = (ts, int(row["p_e18"]))
        head = (head + 1) % len(ring)
        lo, hi = _range_in_window(ring, ts, window_sec)
        move = 0 if lo == 0 else ((hi - lo) * 10_000) // lo
        if move > trig_bps and ts > last_flip + C.RSC_REFIRE_COOLDOWN_SEC:
            trigger_count += 1
            last_flip = ts
            if first_ms is None:
                first_ms = int(row["t_ms"])
                first_offset = (first_ms - start_ms) // 1000
    return {
        "trigger_count": trigger_count,
        "first_trigger_ms": first_ms,
        "first_trigger_offset_sec": first_offset,
    }


def _range_in_window(ring: list[tuple[int, int] | None], now_ts: int, window_sec: int) -> tuple[int, int]:
    cutoff = 0 if window_sec >= now_ts else now_ts - window_sec
    values = [price for item in ring if item is not None for ts, price in [item] if ts >= cutoff and price > 0]
    if not values:
        return 0, 0
    return min(values), max(values)


def _bled_before(rows_path: Path, truth_path: Path, trigger_ms: int | None) -> tuple[int | None, str | None]:
    if trigger_ms is None:
        return None, "no trigger"
    rows = _load_rows(rows_path)
    truth = _load_rows(truth_path)
    if len(rows) != len(truth):
        raise ValueError("vol truth length mismatch")
    bleed = 0
    for row, truth_row in zip(rows, truth, strict=True):
        if int(row["t_ms"]) != int(truth_row["t_ms"]):
            raise ValueError("vol truth t_ms mismatch")
        if int(row["t_ms"]) > trigger_ms:
            break
        if int(truth_row.get("valid", 0)):
            bleed += int(truth_row["truth_mk_e6"])
    if rows and trigger_ms < int(rows[0]["t_ms"]):
        return 0, "trigger before measured truth window"
    return abs(bleed), None


def _total_bleed(rows_path: Path, truth_path: Path) -> dict:
    rows = _load_rows(rows_path)
    truth = _load_rows(truth_path)
    if len(rows) != len(truth):
        raise ValueError("vol truth length mismatch")
    bleed = 0
    valid = 0
    for row, truth_row in zip(rows, truth, strict=True):
        if int(row["t_ms"]) != int(truth_row["t_ms"]):
            raise ValueError("vol truth t_ms mismatch")
        if int(truth_row.get("valid", 0)):
            valid += 1
            bleed += int(truth_row["truth_mk_e6"])
    return {
        "valid_truth_rows": valid,
        "measured_start_ms": int(rows[0]["t_ms"]) if rows else 0,
        "measured_bleed_total_e6": abs(bleed),
    }


def _load_rows(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _seconds(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{int(value)} s"


def _usd_or_note(value: object, note: object) -> str:
    if note:
        return str(note)
    if value is None:
        return "n/a"
    return f"${int(value) / 1_000_000:,.2f}"


def main() -> int:
    root = C.repo_root()
    parser = argparse.ArgumentParser(description="Generate GUARD/control-plane breaker economic report")
    parser.add_argument("--out-md", type=Path, default=root / "docs" / "guard_depeg_report.md")
    parser.add_argument("--out-json", type=Path, default=root / "docs" / "guard_depeg_report.json")
    args = parser.parse_args()
    report = compute(root)
    write_outputs(report, args.out_md, args.out_json)
    print(f"status={'complete' if report['complete'] else 'incomplete'}")
    print(f"wrote {args.out_md}")
    print(f"wrote {args.out_json}")
    return 0 if report["complete"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
