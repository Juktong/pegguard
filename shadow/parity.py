from __future__ import annotations

import json
from pathlib import Path

from . import constants as C
from .pipeline import ReplayMetrics, replay_rows_exact


def _load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def replay_fixture(root: Path, window: str) -> ReplayMetrics:
    if window == "calm":
        rows = _load_json(root / "test" / "fixtures" / "calm_0530.json")
        truth = _load_json(root / "test" / "fixtures" / "calm_0530_truth.json")
    elif window == "vol":
        rows = _load_json(root / "test" / "fixtures" / "vol_0523_hot90m.json")
        truth = _load_json(root / "test" / "fixtures" / "vol_0523_truth.json")
    else:
        raise ValueError(f"unknown fixture window: {window}")
    return replay_rows_exact(rows, truth, include_quantiles=True)


def assert_parity(root: Path | None = None) -> dict[str, ReplayMetrics]:
    root = root or C.repo_root()
    C.assert_frozen_constants(root)
    results = {window: replay_fixture(root, window) for window in ("calm", "vol")}
    for window, metrics in results.items():
        expected = C.BASELINE[window]
        _assert_close(window, "precision", metrics.precision_bps, expected["precision_bps"])
        _assert_close(window, "truth capture", metrics.capture_truth_bps, expected["capture_truth_bps"])
    return results


def _assert_close(window: str, label: str, actual_bps: int, expected_bps: int) -> None:
    delta = abs(actual_bps - expected_bps)
    if delta > C.PARITY_TOLERANCE_BPS:
        raise AssertionError(
            f"{window} {label} parity failed: actual {actual_bps / 100:.2f}% "
            f"expected {expected_bps / 100:.2f}% +/- {C.PARITY_TOLERANCE_BPS / 100:.2f}pp"
        )

