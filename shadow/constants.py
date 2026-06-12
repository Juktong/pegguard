from __future__ import annotations

from pathlib import Path

WAD = 10**18

ALPHA_NUM = 1
ALPHA_DEN = 2
CAP_PIPS = 5000
TAU_SEC = 450
DEADBAND_CALM_E2 = 50
DEADBAND_VOL_E2 = 50
MAX_STALENESS_CALM_SEC = 5
MAX_STALENESS_VOL_SEC = 2
CONF_ANOMALY_NUM = 3
CONF_EMA_KEEP_NUM = 9
CONF_EMA_DEN = 10

RSC_TRIG_BPS = 40
RSC_WINDOW_SEC = 180
RSC_REFIRE_COOLDOWN_SEC = 5 * 60
REGIME_TTL_SEC = 30 * 60

BASELINE = {
    "calm": {
        "precision_bps": 9242,
        "capture_truth_bps": 2298,
    },
    "vol": {
        "precision_bps": 9886,
        "capture_truth_bps": 2556,
    },
}

PARITY_TOLERANCE_BPS = 100

TARGET_POOL = "0xc6962004f452be9203591991d15f6b388e09e8d0"
SENTINEL_POOL = "0x88e6a0c2ddd26feeb64f039a2c41296fcb3f5640"
SWAP_TOPIC0 = "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
PYTH_ETH_USD_FEED_ID = "0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _require_text(path: Path, needles: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        joined = ", ".join(repr(m) for m in missing)
        raise RuntimeError(f"{path} does not contain frozen constant evidence: {joined}")


def assert_frozen_constants(root: Path | None = None) -> None:
    """Refuse to run if the checked-in provenance no longer matches constants.

    This is deliberately strict and boring. Live shadow data is measurement, not
    calibration; changing a constant should break boot until the code and docs
    are reviewed together.
    """

    root = root or repo_root()
    _require_text(
        root / "research" / "PARAMETERS.md",
        [
            "| `alphaNum/Den` | 1/2",
            "| `capPips` | 5000",
            "| `MAX_STALENESS_CALM` | 5 s",
            "| `MAX_STALENESS_VOL` | 2 s",
            "| `tauSec` | 450 s",
            "| `CONF_ANOMALY_NUM` | 3x",
            "| `deadbandCalmE2/deadbandVolE2` | 50 / 50",
            "| RSC `TRIG_BPS/WINDOW` | 40 bps / 180 s",
            "| RSC `REGIME_TTL` | 30 min",
        ],
    )
    _require_text(
        root / "src" / "PegGuardHook.sol",
        [
            "MAX_STALENESS_CALM = 5",
            "MAX_STALENESS_VOL  = 2",
            "CONF_ANOMALY_NUM   = 3",
            "DEFAULT_DEADBAND_CALM_E2 = 50",
            "DEFAULT_DEADBAND_VOL_E2  = 50",
        ],
    )
    _require_text(
        root / "src" / "reactive" / "VolSentinelRSC.sol",
        [
            "TRIG_BPS    = 40",
            "WINDOW_SEC  = 180",
        ],
    )

