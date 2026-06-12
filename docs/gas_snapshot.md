# Gas snapshot

Command:

```bash
forge snapshot --match-contract PegGuardHookTest
forge test --match-contract PegGuardHookTest --gas-report
```

Focused snapshot:

```text
PegGuardHookTest:test_staleOracle_fallsBackToBaseFee() (gas: 81641)
PegGuardHookTest:test_confSpike_fallsBackToBaseFee() (gas: 142222)
PegGuardHookTest:test_unseededBasis_fallsBackToBaseFee() (gas: 90870)
PegGuardHookTest:test_correctingSide_paysPremium_otherSideDoesNot() (gas: 159347)
PegGuardHookTest:test_breakerTrips_onChain_aboveThreshold() (gas: 161008)
PegGuardHookTest:test_tripped_deepeningPaysGuardFee_repeggingPaysBase() (gas: 169778)
```

The snapshot lines are whole-test costs, including setup and multiple hook
calls in some tests. The gas report isolates `PegGuardHook.beforeSwap`:

| Function | Min | Avg | Median | Max | Calls |
|---|---:|---:|---:|---:|---:|
| `beforeSwap` | 42017 | 52699 | 54108 | 58918 | 8 |
| `afterSwap` | 40717 | 84925 | 93767 | 93767 | 6 |

The isolated beforeSwap path is below the brief's ~150k gas flag threshold in
the focused harness. Storage-layout optimization is not needed before the
functional test baseline.
