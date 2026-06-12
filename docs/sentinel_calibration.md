# Sentinel Calibration

Status: completed with the immutable calm sentinel fixture from
`pegguard-truth-fixtures.zip` and the corrected volatile sentinel fixture from
`sentinel-vol-fixed.zip`.

Corrected volatile fixture:

- `test/fixtures/sentinel_mainnet_vol.json`
- 1,108 swaps
- 418 bps window
- SHA-256: `4eb34aa08f1da2dcd4b668b6ebadbd4329ac1813c3af5c03f8f6b5e2bbae8348`

`src/lib/SentinelWindow.sol` contains the shared RSC range/window math used by
`src/reactive/VolSentinelRSC.sol` and `test/SentinelCalibration.t.sol`.

Command:

```bash
forge test --match-contract SentinelCalibrationTest -vv
```

## Sweep

| TRIG_BPS | WINDOW_SEC | Calm triggers | Vol triggers | First vol trigger offset | Measured bleed before trigger |
|---:|---:|---:|---:|---:|---:|
| 20 | 180 | 0 | 14 | 1825 s | pre-window; not measured |
| 20 | 300 | 1 | 15 | 1825 s | pre-window; not measured |
| 20 | 600 | 3 | 22 | 1825 s | pre-window; not measured |
| 30 | 180 | 0 | 10 | 4332 s | pre-window; not measured |
| 30 | 300 | 0 | 12 | 4332 s | pre-window; not measured |
| 30 | 600 | 1 | 16 | 4332 s | pre-window; not measured |
| 40 | 180 | 0 | 6 | 4332 s | pre-window; not measured |
| 40 | 300 | 0 | 6 | 4332 s | pre-window; not measured |
| 40 | 600 | 0 | 8 | 4332 s | pre-window; not measured |
| 60 | 180 | 0 | 3 | 12656 s | $2,399 |
| 60 | 300 | 0 | 4 | 12656 s | $2,399 |
| 60 | 600 | 0 | 4 | 12656 s | $2,399 |

Selected `TRIG_BPS = 40`, `WINDOW_SEC = 180`. It has zero calm false positives
and 6 volatile triggers. Its first trigger at `+4332s` arms the volatile regime
74 minutes before the measured heavy-bleed window begins at `+8759s`; bleed
during the unmeasured ramp, where 180s ranges stay below 40 bps throughout, is
expected to be small but was not measured.

The `60/*` comparison is measured in-window: first trigger at `+12656s` and
about `$2,399` bled before trigger.
