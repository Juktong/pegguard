# Unichain stablecoin-pair market making: on-chain flow and LP markout measurement (chain id 130)

All numbers below come from my own measurements on real data pulled on 2026-10-13. Nothing is synthesized. "Source" links point to the raw data endpoint each number came from. The derived statistics were computed by the scripts listed under Q1, in the session scratchpad `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/onchain_markout/` (folders `scripts/`, `data/` for raw downloads, and `out/` for derived JSON). The scratchpad is session-local and is not committed to the repo.

**Conventions (match the repo where possible).** 1 bp = 0.01%. Fee pips: 100 pips = 1 bp. For every pool, token0 = USDC and the price P is token1 per token0 (USDT0 per USDC). The reference F is the OKX `USDC-USDT` price; Coinbase `USDT-USDC` is inverted and used as a cross-check. Pool deltas d0 and d1 are taken from the LP side (positive = pool received). v4 Swap events report amounts from the swapper's side, so I negated them. This was verified: in all 11 pools, 100% of price moves have the right sign, and the median trader cost against the geometric mid equals the fee tier (1.000 bp, 0.180 bp, and so on).

- **Fee per swap** = gross input × fee/1e6.
- **LP gross P&L at horizon h**: `MK_h = d0·F(t+h) + d1`, including fees, against holding.
- **Adverse selection / markout before fees (AS)** = `fee − MK_h`. Positive means the LP lost.
- **Net LP** = fees − AS = ΣMK_h.
- **Aggregation**: everything is summed and divided by Σ|USDC leg| × 1e4 to get bps.
- **Uncertainty**: 95% CIs come from a day-block bootstrap (1,000 resamples).
- **"Repo truth"** follows [shadow/truth.py](/home/user/pegguard/shadow/truth.py): basis = centered ±300 s median of post_mid/F, and fair_local = F·basis.
- **"Hook replay"** follows [shadow/pipeline.py](/home/user/pegguard/shadow/pipeline.py): trailing basis EMA with τ = 450 s, α = 0.5, deadband 0.5 bp, cap 50 bp.
- **Premium-weighted precision** = premium charged on truth-correcting (or truth-toxic) swaps ÷ total premium, as in [EventDiff.t.sol](/home/user/pegguard/test/EventDiff.t.sol).

## Q1. Which pools are the top stable/stable pools on Unichain, and what did their flow look like (count, notional, size distribution, fee revenue, effective fee, dynamic fees)?

### Takeaway
Stable/stable trading on Unichain is small. Over 30 days, all USDC/USDT0-type pools together traded about $5.33M of notional and paid about $373 in LP fees. Three pools carry most of it:
- **v4 USDC/USDT0 at 1 bp** (`0x77ea…59c9`): $1.30M and $129.56 in fees.
- **Velodrome Slipstream USDC/USDT0 at 1 bp**: $1.76M and $176.07. Its volume collapsed after Oct 1.
- **v4 USDC/USDT0 at 0.18 bp** (`0xaf58…5a`): $1.37M and $24.72, spread over 22.7k small swaps.

Every stable pool is hookless with a static fee. No dynamic fee was charged anywhere.

### Cited Findings
#### Data, window and reproducibility
- **Chain and timestamps.** The public RPC returned `eth_chainId` = 130. Block timestamps satisfy `ts = 1730748359 + block` exactly; I checked blocks 1, 1,000,000, head−2,592,000, head−604,800 and head 61,168,175 (2026-10-13 18:35:34 UTC). So blocks are exactly 1 s apart. — [Unichain RPC](https://mainnet.unichain.org)
- **30-day analysis window.** Blocks 58,509,241–61,101,240, which is 2026-09-13 00:00:00 to 2026-10-12 23:59:59 UTC. Logs were fetched up to block 61,168,000 so that 1 h markouts at the end of the window can be looked up.
- **7-day high-resolution window.** 2026-10-06 00:00 to 2026-10-13 00:00 UTC, blocks 60,496,441–61,101,240.
- **eth_getLogs limits.** Calls work in 10,000-block chunks. Ranges of 50,000 blocks or more return HTTP 400, and an unfiltered all-pool scan needs ≤1,000-block chunks (HTTP 500 otherwise). JSON-RPC batches are capped at 10 items. — [Unichain RPC](https://mainnet.unichain.org)
- **Contract addresses** from the official v4 deployments page (docs.uniswap.org now redirects to developers.uniswap.org):
  - PoolManager `0x1f98400000000000000000000000000000000004`
  - PositionManager `0x4529a01c7a0410167c5740c487a8de60232617bf`
  - StateView `0x86e8631a016f9068c3f085faf484ee3f5fdee8f2`
  - Universal Router `0xef740bf2…af3`, 2.1.1 `0xfdf682f5…bc7`, 2.1.2 `0xD1b797D9…343`

  — [Uniswap v4 deployments](https://developers.uniswap.org/contracts/v4/deployments)
- **v3 factory.** The v3 pools' `factory()` returns `0x1f98400000000000000000000000000000000003`. The Velodrome Slipstream pool's factory is `0x04625b04…5a55f`. — [Unichain RPC eth_call](https://mainnet.unichain.org)
- **Token identities.** On-chain `symbol()` and `decimals()` give:
  - USDC `0x078d782b…7ad6` (6 decimals)
  - USD₮0 `0x9151434b…ecc5` (6 decimals). GeckoTerminal displays this token as "USD0".
  - Legacy bridged "USDT" `0x588ce4f0…5518` (6 decimals)
  - DAI `0x20cab320…3f81` (18 decimals)

  — [Unichain RPC](https://mainnet.unichain.org), [GeckoTerminal Unichain pools](https://api.geckoterminal.com/api/v2/networks/unichain/pools?sort=h24_volume_usd_desc)
- **Pool discovery** had two parts:
  1. GeckoTerminal top pools, token-pool and search endpoints. These were partly rate-limited with HTTP 429. — [GeckoTerminal](https://api.geckoterminal.com/api/v2/networks/unichain/pools?sort=h24_volume_usd_desc)
  2. A full scan of every v4 PoolManager Swap log for 2026-10-12 (31,848 swaps across 133 pools), with each top-60 pool key resolved through `PositionManager.poolKeys`. The only stable/stable v4 pools in that top 60 were the five USDC/USDT0 pools, USDC/DAI 1 bp and USDC/USDT(bridged) 1 bp. All have `hooks = 0x0`. Hooked dynamic-fee pools on Unichain, for example hook `0xa0b0d2d0…` with fee flag 0x800000, appear only in volatile pairs.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Pool state.** StateView `getSlot0` shows protocolFee = 0 and a static lpFee for every v4 stable pool. Every v4 Swap event in the window carries a single constant `fee` value per pool (100, 18, 20, 40 or 500 pips). — [Unichain RPC](https://mainnet.unichain.org)
- **Raw data volumes:**
  - 58,793 + 2,719 logs, which decode to 56,518 swaps and 4,994 liquidity events
  - 48,483 transaction objects
  - 850 LP receipts
  - 44,340 OKX 1 m candles
  - 609,600 OKX 1 s candles
  - 16,210 non-empty Coinbase 1 m candles

  — [Unichain RPC](https://mainnet.unichain.org), [OKX candles](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s), [Coinbase candles](https://api.exchange.coinbase.com/products/USDT-USDC/candles?granularity=60)
- **Scripts:** `rpcutil.py`, `pool_meta.py`, `fetch_logs.py`, `fetch_okx.py`, `fetch_cb.py`, `fetch_txs.py`, `scan_v4_day.py`, `decode.py`, `basic_stats.py`, `markout.py`, `flow.py`, `category.py`, `lp.py`, `directional.py`, `extras.py`. All analysis was run with `python3 -I` on the downloaded data. — [Unichain RPC](https://mainnet.unichain.org)

#### Per-pool flow, 30 days (2026-09-13 to 2026-10-13 UTC)
Notional is |USDC leg|.

| Pool (id / address) | Fee | Swaps | Notional | Size p50 / p90 / p99 / max | LP fees | Effective fee |
|---|---:|---:|---:|---|---:|---:|
| v4 USDC/USDT0 `0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9` | 1 bp (100) | 3,175 (3,066 txs) | $1,295,058 | $130 / $1,042 / $3,773 / $18,269 | $129.56 | 1.000 bp |
| v4 USDC/USDT0 `0xaf58ab3ed922b34e94d13e01edf1b4ddbe5d2afbc29abbcef5ef8ff752a1ae5a` | 0.18 bp (18) | 22,697 | $1,372,883 | $17 / $160 / $390 / $2,967 | $24.72 | 0.180 bp |
| v4 USDC/USDT0 `0x2c6809bbb1ddc601d76ddee68f17e683bd8430795f1b38b1cb7b0d4c28b73e88` | 0.4 bp (40) | 9,682 | $629,490 | $19 / $157 / $460 / $2,347 | $25.19 | 0.400 bp |
| v4 USDC/USDT0 `0xc7ee4db44db3234cb0a3dc7fb2fd4d068d9bfb0c71092fc4a21edb2d95e34306` | 0.2 bp (20) | 6,888 | $209,471 | $15 / $80 / $185 / $1,474 | $4.19 | 0.200 bp |
| Velodrome Slipstream USDC/USDT0 `0x31bafd5d04580f71a808ae646bb787d38e9362f9` | 1 bp (`fee()`=100) | 7,339 (6,980 txs) | $1,760,364 | $51 / $261 / $4,998 / $26,206 | $176.10 | 1.000 bp |
| v3 USDC/USDT0 `0x5c75bfb6194d7d763d33ea292cbc50cda806451b` | 1 bp | 1,146 | $30,289 | $12 / $63 / $212 / $300 | $3.03 | 1.001 bp |
| v3 USDC/USDT0 `0xe92c7cc875245a86faf088febe4614e1e318bef5` | 5 bp | 89 | $8,194 | $15 / $266 / $1,001 / $1,337 | $4.10 | 5.004 bp |
| v4 USDC/USDT(bridged) `0x3d4d39a2…fa7` | 5 bp | 386 | $9,848 | $6 / $22 / $432 / $999 | $4.93 | 5.008 bp |
| v4 USDC/USDT(bridged) `0xa3851829…f0` | 1 bp | 1,518 | $6,922 | – | $0.69 | 1.001 bp |
| v3 USDC/USDT(bridged) `0x1dfab214…cc` | 1 bp | 1,831 | $6,847 | – | $0.69 | 1.001 bp |
| v4 USDC/DAI `0x3188bf36…e48d` | 1 bp | 1,076 | $547 (dust, priced about 2% off peg) | – | $0.06 | 1.02 bp |

Source: [Unichain RPC eth_getLogs](https://mainnet.unichain.org) (PoolManager Swap topic `0x40e9cecb…112f`; v3 Swap topic `0xc42079f9…ca67`).

- **Last 7 days (Oct 6–13).** The main v4 1 bp pool did 996 swaps, $379,732 and $38.00 of fees. Slipstream did only 253 swaps and $8,100. The 0.18 bp pool did 1,978 swaps and $128,446. — [Unichain RPC](https://mainnet.unichain.org)
- **Daily volume, main v4 1 bp pool:** p10 $7.3k, median $34.5k, p90 $105.7k, max $150.0k (Oct 8). — [Unichain RPC](https://mainnet.unichain.org)
- **Daily volume, Slipstream:** went from up to $246k/day (Sep 16) to under $5k/day from Oct 1, and $4 on Oct 10. — [Unichain RPC](https://mainnet.unichain.org)
- **Effective fee equals the tier.** It is exactly the fee tier in every pool, and the median trader cost against the geometric pre/post mid equals the tier. This includes Slipstream at 1.000 bp, so no dynamic fee module was in effect there either. — [Unichain RPC](https://mainnet.unichain.org)
- **GeckoTerminal snapshot** (≈18:33 UTC Oct 13), TVL and 24 h volume:
  - Main v4 1 bp pool: TVL $149,112; 24 h volume $68,171 over 316 transactions
  - v3 5 bp: TVL $67,544, 24 h volume $27
  - v4 USDC/USDT(bridged) 5 bp: TVL $9,388
  - 0.4 bp: TVL $3,981
  - 0.18 bp: TVL $3,902
  - v3 1 bp: TVL $2,601
  - Slipstream: TVL $2,267
  - 0.2 bp: TVL $2,193

  — [GeckoTerminal](https://api.geckoterminal.com/api/v2/networks/unichain/pools?sort=h24_volume_usd_desc)
- **The Pyth reference was not available.** Pyth Hermes returned HTTP 401 "unauthorized" for both latest and historical price updates, and the Benchmarks TradingView shim returned 404. Feed metadata still lists Crypto.USDC/USD, Crypto.USDT/USD and Crypto.USDT0/USD. — [Pyth Hermes](https://hermes.pyth.network/v2/updates/price/latest), [Pyth price_feeds](https://hermes.pyth.network/v2/price_feeds?query=USDT&asset_type=crypto)
- **Other references:** Bybit returned a CloudFront geo-block. Kraken USDC/USDT has a 0.0001 tick and only 720 one-minute candles. — [Bybit](https://api.bybit.com/v5/market/tickers?category=spot&symbol=USDCUSDT), [Kraken](https://api.kraken.com/0/public/AssetPairs?pair=USDCUSDT)

### Inferences
- The stable market on Unichain is a few hundred thousand dollars of turnover a day, with roughly $10k of active in-range depth in the main pool (see Q5). It is tiny next to the Arbitrum/mainnet venues the earlier repo research studied.
- The sub-bp v4 pools (0.18, 0.2 and 0.4 bp) carry many small trades, with p50 of $15–19, mostly from bots and aggregators. The 1 bp pools carry the larger trades.
- Slipstream's collapse after Oct 1 shows the venue mix shifts quickly. Thirty-day aggregates mix two regimes.

### Gaps
- There was no Pyth reference, so no dual-feed Pyth ratio (HTTP 401). The CEX references are OKX (0.1 bp tick, 1 s) and Coinbase (1 bp tick, 1 m, sparse).
- GeckoTerminal TVL is a single snapshot and is not reconciled on-chain. v4 is a singleton, so per-pool token balances cannot be read directly.
- Slipstream gauge emissions and staked/unstaked fee splits were not measured. LP economics there exclude emissions.

## Q2. How far do pool prices deviate from 1.0000 and from an external reference (bps p50/p90/p99/max)?

### Takeaway
USDC itself traded at a premium to USDT that drifted from about 0.5 bp to 12.7 bp during the window (OKX). Measured against 1.0000, the pools therefore look 2–13 bp off. Measured against the CEX reference, the USDT0 pools track tightly:
- **Time-weighted (per minute):** |dev| p50 0.30–0.54 bp, p90 0.67–1.22 bp, p99 1.2–2.2 bp, max 2.5–6.7 bp.
- **At swap time:** larger, with p90 1.0–2.6 bp and p99 3.7–13 bp, because trades cluster where deviations exist.

Legacy bridged-USDT pools sit 13–15 bp away from OKX persistently, which is a basis rather than mispricing. Deviations are 2–5x the repo's earlier 0.000–0.35 bp stable-pair figure, but they are the same order as the cross-venue reference noise (OKX against Coinbase 1 m: p50 0.40 bp, p90 0.90 bp).

### Cited Findings
- **The reference path itself.**
  - Over the 30 days, OKX USDC-USDT ran from 1.00005 at the start to 1.00111 at the end, with a minimum of 0.99985 and a maximum of 1.00127. |F − 1| had p50 2.3 bp, p90 8.0 bp and max 12.7 bp.
  - Daily closes moved between +0.2 bp and +9.6 bp.
  - Live at 18:40 UTC on Oct 13: bid 1.00105, ask 1.00106 (tick 0.00001 = 0.1 bp).

  — [OKX 1 m candles](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [OKX ticker](https://www.okx.com/api/v5/market/ticker?instId=USDC-USDT)
- **Reference resolution and noise:**
  - OKX 1 s closes against the same minute's VWAP: |diff| p50 0.05 bp, p90 0.11 bp, p99 0.25 bp. The OKX 1 s price changed in only 21% of seconds. The 60 s absolute change had p50 0.10 bp, p90 0.20 bp, p99 0.40 bp.
  - OKX against Coinbase 1 m closes (15,944 overlapping minutes): mean −0.31 bp, |diff| p50 0.40 bp, p90 0.90 bp, p99 1.40 bp. Coinbase USDT-USDC has a 0.0001 (1 bp) quote increment.

  — [OKX 1 s](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s), [Coinbase product](https://api.exchange.coinbase.com/products/USDT-USDC), [Coinbase candles](https://api.exchange.coinbase.com/products/USDT-USDC/candles?granularity=60)
- **Time-weighted per-minute deviation.** Pool mid (last post-swap price as of minute end) against the OKX 1 m close, and against 1.0, over 30 days. Each pool has about 43k minutes; minutes with |dev| > 50 bp from empty-liquidity outliers are excluded.

  | Pool | vs OKX p50 / p90 / p99 / max (bps) | vs 1.0000 mean, p50 / p90 / p99 / max (bps) |
  |---|---|---|
  | v4 1 bp | 0.45 / 0.97 / 1.24 / 2.46 | +3.50, 2.31 / 7.63 / 11.16 / 13.35 |
  | v4 0.18 bp | 0.30 / 0.67 / 1.55 / 5.99 | +3.52, 2.27 / 8.05 / 11.52 / 15.93 |
  | v4 0.2 bp | 0.34 / 0.81 / 2.19 / 6.70 | +3.48, 2.28 / 8.03 / 9.00 / 15.01 |
  | v4 0.4 bp | 0.32 / 0.68 / 1.18 / 5.73 | +3.53, 2.28 / 8.01 / 10.94 / 14.70 |
  | v3 1 bp | 0.46 / 1.13 / 1.76 / 3.70 | +3.53, 2.39 / 7.78 / 11.08 / 13.60 |
  | Slipstream 1 bp | 0.54 / 1.22 / 1.89 / 4.30 | +3.47, 2.14 / 7.49 / 11.34 / 14.00 |
  | v4 USDC/USDT(bridged) 5 bp | 14.62 / 18.22 / 23.36 / 24.92 (mean +13.8) | – |
  | v3 USDC/USDT(bridged) 1 bp | 13.08 / 18.27 / 21.69 / 23.19 (mean +12.9) | – |

  — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 m](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Per-swap pre-trade deviation**, pool mid against the reference at swap time:
  - Main v4 1 bp pool, 30 d against OKX 1 m VWAP: |dev| p50 0.75, p90 1.32, p99 9.33, max 27.9 bp (mean signed +0.29).
  - Same pool, 7 d against OKX 1 s: p50 0.70, p90 2.62, p99 13.42, max 27.83 bp.
  - 0.18 bp pool: 0.38 / 0.95 / 3.72 bp (30 d).
  - 0.4 bp pool: 0.47 / 1.20 / 3.74 bp.
  - v3 1 bp: 0.94 / 2.45 / 8.38 bp.
  - Slipstream: 1.11 / 2.21 / 2.71 bp. It carries a persistent signed basis of −0.54 bp (p50), meaning USDC is cheaper there than on OKX.

  — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s)
- **Empty-liquidity outliers.** Eight swaps in the 0.2 bp pool executed against empty liquidity, with post-prices up to 4.8M. They are excluded from all markout and deviation statistics and counted as outliers. Four Slipstream swaps (one post-price at 1.064) were excluded the same way. — [Unichain RPC](https://mainnet.unichain.org)
- **Earlier repo baseline.** The prior stable-pair conclusion used normal cross-venue deviations of 0.000–0.35 bp and feed noise of about 0.2 bp. — [research/PARAMETERS.md](/home/user/pegguard/research/PARAMETERS.md)

### Inferences
- Do not de-peg-test stables against 1.0000 in this regime. The USDC/USDT premium alone reached 12.7 bp, so the comparison must be pair-relative, for example a USDC/USD ÷ USDT0/USD ratio.
- Unichain USDT0 pools carry about 0.3–0.5 bp of median mispricing against OKX, with tails to a few bp. That is larger than the repo's prior stable measurement. The signal is real at 1 s/0.1 bp OKX resolution, where reference noise is ≤0.1 bp. Against a 1 bp-tick venue such as Coinbase, cross-venue noise (p90 0.9 bp) is the same size as the deviation.
- The 50 bp guard-mode trip would never have fired on the USDT0 pools in normal flow (time-weighted maximum 6.7 bp). It would mis-fire constantly on the bridged-USDT pools (persistent 13–15 bp basis) and on the USDC/DAI dust pool (about 40 bp) unless those pairs are excluded or basis-adjusted.

### Gaps
- No order-book mid was available historically. OKX 1 s "close" is a last-trade price on a 1-tick-wide book, so ±0.05 bp of bid/ask bounce is possible.
- Block timestamps have 1 s granularity, and Flashblock (200 ms) sub-block timing is not recoverable from the standard historical RPC. Swap-to-reference alignment is therefore ±1 s.

## Q3. LP markouts (10 s / 1 min / 5 min / 1 h) against the reference and against the pool's own future price; net LP = fees − markout. Is stable-pair LP net positive, and how does it change with fee tier?

### Takeaway
LP is net positive per unit of volume in every USDC/USDT0 pool, but the dollar amounts are tiny.
- **Main v4 1 bp pool:** LPs lose about 0.35–0.40 bp per notional to adverse selection before fees, and markouts are flat from 0 s to 1 h. The net is about +0.60 to +0.65 bp (30 d: +0.649 bp, CI [0.55, 0.72]; 7 d at 1 s: +0.60 bp at 60 s, CI [0.34, 0.72]).
- **Slipstream 1 bp:** about 0.90 bp of adverse selection leaves +0.10 bp net (CI [−0.06, 0.33]).
- **Sub-bp tiers (0.18, 0.2, 0.4 bp):** only 0.01–0.05 bp of adverse selection, so they keep most of their fee (+0.17, +0.17 and +0.38 bp net).
- **All stable pools combined (30 d):** fees $373 (0.70 bp), adverse selection $208 (0.39 bp), net $165 (0.31 bp).

### Cited Findings
- **30 days, OKX 1 m VWAP reference, h = 5 min** (h = 0 and h = 1 h are within ±0.05 bp unless noted):

  | Pool | n | Notional | Fees | AS (h=0 / 5 m / 1 h) | Net LP bps [95% CI] | Self-markout AS (pool's own mid, 5 m) |
  |---|---:|---:|---:|---|---|---:|
  | v4 USDC/USDT0 1 bp | 3,174 | $1,295,033 | $129.56 | 0.356 / 0.351 / 0.332 | +0.649 [0.55, 0.72] | 0.173 |
  | v4 0.18 bp | 22,696 | $1,372,870 | $24.72 | 0.010 / 0.010 / 0.010 | +0.170 [0.16, 0.17] | 0.029 |
  | v4 0.2 bp | 6,879 | $208,994 | $4.18 | 0.027 / 0.026 / 0.027 | +0.174 [0.17, 0.18] | 0.083 |
  | v4 0.4 bp | 9,681 | $629,422 | $25.19 | 0.023 / 0.021 / 0.022 | +0.379 [0.37, 0.39] | 0.045 |
  | v3 USDC/USDT0 1 bp | 1,145 | $30,271 | $3.03 | 0.191 / 0.177 / 0.178 | +0.823 [0.72, 0.90] | 0.224 |
  | Slipstream 1 bp | 7,334 | $1,760,151 | $176.07 | 0.922 / 0.897 / 1.006 | +0.103 [−0.06, 0.33] | 0.178 |
  | v3 USDC/USDT0 5 bp | 88 | $8,192 | $4.10 | 0.909 / 0.797 / 0.763 | +4.207 [2.56, 4.91] | 0.723 |
  | v4 USDC/USDT(bridged) 5 bp | 385 | $9,645 | $4.83 | −0.228 / −0.236 / −0.381 | +5.242 [2.29, 7.52] | 2.325 |
  | **Total (all stable pools)** | – | $5,328,355 | $373.05 | 0.39 (AS $207.66) | +0.31 (net $165.39) | – |

  — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 m](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **7 days, OKX 1 s reference, main v4 1 bp pool** (996 swaps, $379,732):
  - AS at h = 0 / 10 s / 60 s / 5 m / 1 h: 0.390 / 0.406 / 0.402 / 0.378 / 0.334 bp. The 60 s CI is [0.28, 0.66].
  - Net LP: +0.611 / +0.595 / +0.599 / +0.623 / +0.667 bp.
  - Self-markout (the pool's own future mid): 0.099 (10 s), 0.131 (60 s), 0.191 (5 m), 0.262 (1 h) bp.
  - Per-swap standard deviation of AS: 2.8 bp.
  - At 60 s, the 0.18, 0.2 and 0.4 bp pools had AS of 0.034, 0.051 and 0.051 bp, for net +0.146, +0.149 and +0.350 bp.
  - At 60 s, Slipstream had AS 0.250 and net +0.751 bp, in its low-volume final week ($8,100).

  — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 s](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s)
- **Reference robustness.** With Coinbase 1 m as the reference (30 d, about 85% coverage), the main pool has AS at 5 m of 0.361 bp and net +0.639 bp [0.52, 0.73]. Slipstream has AS 0.911 bp and net +0.090. The 7-day 1 m results match the 1 s results within about 0.03 bp (main pool 0.377 vs 0.378 bp; Slipstream 0.181 vs 0.150 bp). — [Coinbase candles](https://api.exchange.coinbase.com/products/USDT-USDC/candles?granularity=60), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **How much the basis assumption matters.** Main pool, 30 d, AS before fees at the instant of trade, under different fair-value definitions:
  - Raw OKX: 0.356 bp
  - Leave-own-tx-out centered ±12 h basis: 0.292 bp
  - ±1 h basis: 0.104 bp
  - ±5 min basis: 0.032 bp
  - Repo-style ±300 s centered median that includes the swap itself: 0.085 bp

  Slipstream under the same definitions: 0.922 / 0.725 / 0.049 / 0.010 bp. — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Size buckets, main pool** (30 d, AS at 5 m):
  - <$100: 0.36 bp (n = 1,385)
  - $100–1k: 0.57 bp (n = 1,457)
  - $1k–10k: 0.28 bp (n = 328)
  - >$10k: −0.81 bp (n = 4)

  Slipstream: 0.63 / 1.24 / 0.71 / 0.80 bp (the >$10k bucket has 23 swaps, $339k). — [Unichain RPC](https://mainnet.unichain.org)
- **Repo methodology baseline.** The repo's calm WETH/USDC window recorded 4.03 bp truth markout against a 5 bp base fee, for static net +0.97 bp. — [docs/capital_model.md](/home/user/pegguard/docs/capital_model.md)
- **LVR framework.** LVR is the cost to LPs of trading against arbitrageurs at stale prices. It is the conceptual basis for the markout measurement here. — [Milionis et al., arXiv:2208.06046](https://arxiv.org/abs/2208.06046)

### Inferences
- Stable-pair LP on Unichain is net positive per bp of volume at every tier measured. The ratio of adverse selection to fee is about 35–40% for the v4 1 bp pool, about 90% for Slipstream (net barely positive), and about 5–15% in the sub-bp pools.
- Markouts barely change between 0 s and 1 h. Stable pairs have essentially no post-trade drift: the adverse selection is the instantaneous mispricing at execution, consistent with LVR-type arbitrage that closes pool-versus-CEX gaps rather than informed flow ahead of a price move.
- **Fee tier.** Higher tiers keep more per unit of volume (0.17 → 0.38 → 0.65–0.82 → about 4.2 bp net). Volume is concentrated at the 1 bp tier and in the sub-bp pools, and the 5 bp pools see almost no flow (v3 5 bp: TVL $67.5k, 30 d volume $8.2k).
- **Break-even fee.** For the main pool this is about AS ≈ 0.35 bp, so 1 bp is about 3x break-even. The sub-bp pools' break-even is about 0.01–0.05 bp, but their low AS probably reflects the flow they attract: small bot and aggregator legs that are arbitraged against the 1 bp pool.
- **Dollar scale decides everything.** Using the repo formula net APR = net_bps × daily_volume/active_capital × 365, the main pool comes to about 0.65 bp × ($43k/day ÷ $149k GT TVL) × 365 ≈ 0.7% APR on TVL. Measured against only the about $8.8k of active in-range depth, it is about 11–12% APR (about 4.9x/day turnover). See Q5 for the realized APR of the top LP.

### Gaps
- No route-away counterfactual: fee-tier conclusions are same-swaps.
- Slipstream LP economics exclude gauge emissions and the staked/unstaked fee split.
- The ±300 s repo-truth figure (0.085 bp) is biased low on sparse pools (see Q6). The raw-OKX and ±12 h figures are the more defensible "truth" here.

## Q4. Flow composition: who trades (origins, routers, aggregators, bots), how concentrated, autocorrelation, and clustering in blocks/Flashblocks?

### Takeaway
Flow is dominated by a few unverified bot contracts. Benign retail and aggregator flow is the profitable part for LPs.
- **Bot share.** Unverified contracts (EOA fleets) account for about 68% of all stable-pool volume and are the toxic flow, with AS +0.66 to +0.70 bp. In the main pool they reach +1.0 to +1.35 bp.
- **Benign flow.** Uniswap Universal Router and named aggregators (0x, KyberSwap, LI.FI, Across, Relay and others) have negative AS: LPs gain 0.2–1.5 bp on them before fees.
- **Concentration.** The main pool's top 10 origins carry 50% of volume.
- **Cyclic arbitrage.** 71% of multi-pool transactions are opposite-direction cycles across the Unichain stable pools.
- **Persistence.** Order-flow direction is persistent: lag-1 sign autocorrelation is 0.44–0.47 in the main pool and 0.63 on Slipstream.

### Cited Findings
- **Concentration, main v4 1 bp pool (30 d).** 736 distinct tx.origin addresses, 224 distinct entry contracts (tx.to) and 48 v4 lockers (`sender` in the Swap event). The top 1, 5 and 10 origins carry 13%, 36% and 50% of volume. — [Unichain RPC eth_getTransactionByHash](https://mainnet.unichain.org)
- **Top entries in the main pool, by volume share:**
  - 28.6%: `0x099b1a87…07c9`, unverified. Six EOAs, a single custom selector `0x6bfd6286`, 529 swaps.
  - 13.2%: `0x9c1a4960…c855`, unverified. Two EOAs, selectors SwapV3()/SwapV4().
  - 11.3%: Uniswap UniversalRouter 2.1.2 `0xd1b797d9…`, 189 EOAs.
  - 3.8%: `0x9522d498…`, unverified, from a deployer family `0x5Dc7d46E84…`.
  - 3.6%: `0xbc728c14…`, unverified. One EOA, `execute_route(...)`, 84% one-directional.
  - 3.4%: `0xce488acd…`, 90 EOAs.
  - 2.7%: KyberSwap MetaAggregationRouterV2.
  - 2.4%: UniversalRouter 2.1.1.

  — [Unichain RPC](https://mainnet.unichain.org), [Unichain Blockscout](https://unichain.blockscout.com/address/0xef740bf23acae26f6492b10de645d6b98dc8eaf3), [openchain signature DB](https://api.openchain.xyz/signature-database/v1/lookup?function=0x61461954,0x2f139e4f,0xfd66ae06,0x2e931c2e,0x3593564c)
- **Top lockers in the main pool:** `0x099b1a87` 28.6%, UR 2.1.2 15.9%, `0x9c1a4960` 13.2%, 0x UnichainSettler `0x4c6112da…` 10.9%, UR `0xef740bf2…` 4.1%. — [Unichain RPC](https://mainnet.unichain.org), [Blockscout](https://unichain.blockscout.com/)
- **Other pools:**
  - 0.18 bp pool: 1,503 origins, top 1 origin 18%, top 5 38%. Entries: `0x099b1a87` 33.4%, `0x64e20394` 13.0% (10 EOAs, generic `execute()`), `0x72901a86` 11.4% (96 EOAs, single custom selector `0x7e7f0353`).
  - Slipstream: 635 origins, top 1 19%, top 5 54%. Entries: `0xbc728c14` 19.1%, `0x9c1a4960` 18.6%, a non-Uniswap "UniversalRouter" deploy `0xcaf22ce3` 14.1%.

  — [Unichain RPC](https://mainnet.unichain.org), [Blockscout](https://unichain.blockscout.com/)
- **Blockscout labels and coverage.** Verified named contracts seen:
  - Uniswap: UniversalRouter (official 3 deploys), SwapRouter02
  - Aggregators and solvers: MetaAggregationRouterV2 (KyberSwap); AllowanceHolder, UnichainSettler and UnichainSettlerIntent (0x); AugustusV6 (Velora/ParaSwap); LiFiDiamond and Permit2Proxy (LI.FI); DexRouter and UniversalUniswapV4Adapter (OKX DEX); TychoRouterV3; OkuRouter
  - Bridges: RelayApprovalProxyV3, SpokePoolPeriphery (Across), MayanForwarder2 and FastMCTP (Mayan)
  - Other: EthereumVaultConnector (Euler), CaliburEntry (EIP-7702 wallets)

  No UniswapX reactor, 1inch router or Odos router appeared among the labeled entries. Entry or locker addresses were looked up for 99.5% of all stable-pool volume. — [Blockscout](https://unichain.blockscout.com/)
- **AS by flow category, all stable pools (30 d, h = 5 min, OKX 1 m):**

  | Category | Volume share | AS before fees |
  |---|---:|---:|
  | Unverified contracts with ≤10 EOAs (bot-like) | 34.3% | +0.70 bp ($128) |
  | Unverified contracts with >10 EOAs | 34.1% | +0.66 bp ($120) |
  | Uniswap UR / SwapRouter02 | 8.0% | −1.25 bp |
  | 0x | 7.2% | −0.31 bp |
  | Non-Uniswap UR deploys | 4.8% | +0.74 bp |
  | Velodrome SwapRouter | 3.7% | +0.37 bp |
  | KyberSwap | 3.4% | +0.15 bp |
  | LI.FI | – | −0.24 bp |
  | Across | – | −1.24 bp |

  — [Unichain RPC](https://mainnet.unichain.org), [Blockscout](https://unichain.blockscout.com/), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Same breakdown, main pool:** >10-EOA contracts 34.1% of volume at +1.35 bp ($59.5); ≤10-EOA contracts 24.4% at +1.04 bp ($32.8); Uniswap UR 22.8% at −1.49 bp (−$44.0); 0x 10.3% at −0.18 bp. — [Unichain RPC](https://mainnet.unichain.org), [Blockscout](https://unichain.blockscout.com/)
- **Multi-pool transactions.**
  - 6,444 transactions touched two or more of these stable pools.
  - 4,589 (71%) traded in opposite directions in different pools. This is cyclic stable-stable arbitrage, $952k of swap notional, mainly via `0x64e20394` (2,453 txs), `0x72901a86` and `0xbb12031d`.
  - 1,855 were same-direction split routes ($757k), mainly via KyberSwap, 0x, Uniswap UR, Velora and LI.FI.
  - Multi-pool-tx share of volume: main pool 26.5%; 0.18 bp 35%; 0.2 bp 56%; 0.4 bp 41%; v3 1 bp 65%; Slipstream 27%.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Clustering.**
  - Main pool: median inter-arrival 80 s; 24% of swaps arrive within 2 s of the previous one; 278 of 2,714 active blocks had more than one swap.
  - 0.18 bp pool: median 6 s; 42% within 2 s; 3,879 of 17,116 blocks.
  - Slipstream: median 4 s.
  - In the 7-day window, blocks with swaps from two or more different transactions in the main pool had opposite directions 49% of the time and the same origin only 4% of the time. In the 0.18 bp pool, opposite directions occurred 76% of the time.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Flashblocks timing.** Unichain issues Flashblocks every 200 ms inside 1 s blocks. The JSON-RPC interface is unchanged, so historical sub-block index is not exposed. — [Uniswap blog](https://blog.uniswap.org/flashblocks-are-live), [OP Stack docs](https://docs.optimism.io/op-stack/features/flashblocks.md)
- **Order-flow sign autocorrelation** (lag 1 / 2 / 3 / 5, 30 d):
  - Main pool: 0.47 / 0.42 / 0.35 / 0.27. In the 7-day window, P(next trade in the same direction) = 0.72.
  - Slipstream: 0.63 / 0.57 / 0.54 / 0.50.
  - v3 1 bp: 0.40 / 0.26 / 0.21 / 0.12.
  - 0.18 bp: 0.08 / 0.25 / 0.01 / −0.01.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Priority fees.** Bot entries pay a maxPriorityFee of about 0.0005–0.00125 gwei. Uniswap UR transactions show a median priority fee of 0. — [Unichain RPC](https://mainnet.unichain.org)

### Inferences
- This is classic LVR. Searcher bots, mostly unverified contracts with rotating EOAs, trade when the pool is off CEX or off sister pools and earn about 0.7–1.35 bp before fees. Retail and aggregator flow arrives at roughly fair prices and pays the full fee. The LP's margin comes from the verified-router and aggregator share (about 32% of volume overall, about 41% in the main pool), most of which has negative AS. The exception is non-Uniswap UR deploys (+0.74 bp).
- High direction persistence (0.44–0.63) together with mostly unverified bot flow suggests split execution, or repeated arbitrage in the same direction as the USDC premium drifted on CEX. It does not suggest random retail.
- Labeling ">10 EOA" unverified contracts (`0x72901a86`, `0xbb12031d`, `0xce488acd`) as bots is an inference from their custom selectors and cyclic arbitrage usage, not a confirmed identity.

### Gaps
- Flashblock-level (200 ms) ordering could not be measured historically; only block and logIndex ordering was available.
- tx.origin is pseudonymous. Unverified contracts cannot be definitively attributed to named firms.
- Only top addresses were labeled via Blockscout, although that covers 99.5% of volume.

## Q5. LP side: positions, range widths, re-ranging, JIT, and share of fees by top LPs

### Takeaway
- **Main v4 1 bp pool.** Liquidity is actively managed in ultra-tight ranges: 73% of adds are ≤2 ticks (≤2 bp), median 1 tick, at 44.7 adds/day. The median position lives 3.5 h. No same-block JIT was detected.
  - One LP adding through the official PositionManager (about 1 re-range/day, about $8.5k per 1-tick position) earned about 52% of all pool fees: about $67/30 d gross and about $33 net of 5-min markout. That is roughly 9.6% gross and 4.7% net APR on about $8.5k.
  - Active in-range depth is only about $8.8k per bp.
  - LP gas on Unichain is negligible: about $1.5 for every LP transaction in the pool over 30 days.
- **Slipstream.** Two LPs earned 93% of fees, and one of them was net negative after markout.

### Cited Findings
- **Main pool liquidity events (30 d).**
  - 3,126 ModifyLiquidity events: 1,341 adds, 1,363 removes and 422 zero-liquidity pokes.
  - 172 distinct position keys (sender, tickLower, tickUpper, salt) from 30 LP tx.origins.
  - Width: p10 1 tick, p50 1 tick, p90 887,269 ticks (full range); 73% ≤2 ticks, 12% full range.
  - Position lifetime: p10 28 blocks (28 s), p50 12,664 blocks (3.5 h), p90 148,479 blocks (41 h).
  - Same-block or next-block add→swap→remove JIT: 0 cases.
  - In-range positions per swap: p50 17, p90 23.

  — [Unichain RPC](https://mainnet.unichain.org) (ModifyLiquidity topic `0xf208f491…d5ec`)
- **Who manages the liquidity.**
  - Most events come from custom LP-manager contracts: sender `0xe4453677…` via entry `0xc91ed9c2…` (1,218 events, origin `0x661d1534`), `0x3f039519…`/`0x94d026e7…` (818 events), `0xa0bf9b2c…`/`0x41ae13be…` (482), and others.
  - They rebalance mostly 1-tick ranges, using 11–32 distinct ranges each over 30 days.
  - Their fee share is small; `0x765285cc` has about 1.3%.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Fee attribution.** Each swap's fee was split pro rata to in-range position liquidity over the event's active liquidity.
  - Fees attributable to positions touched in the window: 54%. The rest is pre-window or untouched liquidity.
  - Top LP `0xeb41232c…`: 94 transactions via PositionManager, 47 adds (38 one-tick, 7 two-tick), L ≈ 1.7e14 per position (≈ $8.5k), adds from 09-14 to 10-12. It earned $67.24 of fees (51.9% of pool fees) and $32.72 net after 5-min markout (AS $34.52).
  - Next LP: `0x765285cc` with $1.66 of fees.

  — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Depth.** Active liquidity at the last swap of the window was L = 1.76e14 at tick 11. That is about $8.8k of token value per 1 bp of price move. — [Unichain RPC](https://mainnet.unichain.org)
- **LP gas cost.** All 379 LP transactions in the main pool cost 0.000594 ETH in L2 gas plus L1 fee over 30 days. Slipstream's 471 cost 0.000602 ETH. At about $2,504/ETH (Blockscout exchange rate), each is about $1.5. The top LP's 94 transactions cost 0.000015 ETH. — [Unichain RPC receipts](https://mainnet.unichain.org), [Blockscout](https://unichain.blockscout.com/)
- **Slipstream (30 d).**
  - 287 mints, 251 burns with liquidity and 518 zero-liquidity burns (fee collects); 53 position keys from 12 LP origins; 9.6 adds/day.
  - Width: p50 12 ticks, 48% ≤2 ticks. Lifetime p50 14,400 blocks (4 h). No JIT.
  - Fee attribution 99.8%.
  - LP `0x9c3967dc` took 54.4% of fees ($95.72), $25.29 net after 5-min markout.
  - LP `0xa399dcb7` took 39.1% ($68.84), −$11.54 net. The same address is also 13.5% of Slipstream swap volume.
  - An ALM-like entry `0x0000000ce42d…` (1,032 events, 12-tick ranges) earned only $0.35.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Low-fee and v3 pools.**
  - 0.18 bp pool: only 23 liquidity events from 3 LPs, positions 3–10 ticks wide and long-lived (p50 about 97k blocks, 27 h). Calibur/EIP-7702 wallet `0xcd6b2272` earned an attributable 13.5% of fees.
  - 0.4 bp pool: 0 liquidity events in the window.
  - v3 1 bp: one mint.

  — [Unichain RPC](https://mainnet.unichain.org)
- **Repo capital model.** The model calls for small capital to see 3x or more daily volume per capital, and says passive wide LP is not the best strategy. — [docs/capital_model.md](/home/user/pegguard/docs/capital_model.md)

### Inferences
- **Active vs passive.** Active tight-range LP in the main pool is profitable per unit of capital. The top LP earned roughly 4.7% net APR on about $8.5k, which is a rough estimate. The absolute size is tens of dollars per month, and capacity is limited by about $43k/day of volume.
- Passive full-range or wide liquidity, which is most of GeckoTerminal's $149k TVL, earns about 1% fee APR on TVL before adverse selection.
- Gas is not a constraint on Unichain. Operational and infrastructure cost and capacity are.
- High re-range counts from custom manager contracts, combined with their tiny fee share, suggest those strategies mostly pay to stay near the price without winning the in-range share. The 1-tick PositionManager LP captured most fees.
- No JIT and no meaningful same-block liquidity sniping is happening in these stable pools.

### Gaps
- Pre-window positions were not reconstructed, so 46% of main-pool fees are unattributed.
- Per-LP capital is approximated from L and the range at add time.
- APR figures are indicative only: no inventory P&L from the slow USDC/USDT drift, and no compounding.

## Q6. Do directional signals exist that a dynamic-fee hook could price, or does "no directional fuel" hold on Unichain?

### Takeaway
It depends on the signal, and in either case the dollar fuel is negligible.
- **PegGuard's de-trended signal finds no fuel.** With a τ = 450 s trailing basis, the deviation on the main pool is essentially random against any non-tautological truth: premium-weighted precision 50–61%, and correlation with trade direction −0.01 to −0.03. The repo-style ±300 s truth reports 96–99% precision only because on sparse pools the centered basis absorbs the swap's own price impact.
- **A raw pair-ratio signal does carry direction.** The un-de-trended USDC/USDT ratio, as a dual Pyth feed would provide:
  - The share of flow in the correcting direction rises from about 58% at |dev| < 0.25 bp to 85–92% at 1–5 bp.
  - After the pool is left ≥0.5 bp off, the next trade corrects it 70–80% of the time.
  - Correcting flow carries +1.07 bp of AS, against −1.57 bp for non-correcting flow (main pool, 30 d).
- **The dollar fuel is tiny.** All Unichain stable pools together had $208 of adverse selection before fees in 30 days. A raw-signal PegGuard premium would have raised about $51/30 d in the main pool.

### Cited Findings
- **Repo hook replay against tautological truth.** Main pool, 7 d, OKX 1 s fair, α = 0.5, deadband 0.5 bp, cap 50 bp, τ = 450 s:
  - 179 swaps charged, extra $19.40 (0.51 bp of notional).
  - Precision 98.9% and "capture" 437% against the repo-style ±300 s centered truth.
  - With a leave-own-tx-out ±300 s basis, the realized ex-fee truth markout falls to 0.053 bp. That makes the capture ratio (10.7x) meaningless.

  — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 s](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s), [shadow/pipeline.py](/home/user/pegguard/shadow/pipeline.py), [shadow/truth.py](/home/user/pegguard/shadow/truth.py)
- **Same τ = 450 s hook against non-tautological truths:**
  - Raw-OKX sign truth: precision 53%. Toxic (AS at 60 s > 0) precision 50%. Correlation(dev, buy USDC) −0.03; hit rate 54%. (Main pool, 7 d.)
  - Main pool, 30 d: raw precision 61%, toxic precision 56%, correlation −0.01.
  - Slipstream (30 d): toxic precision 97%, but the extra is only $2.77 against $157.90 of bleed (capture 1.8%).
  - Sub-bp pools (30 d): toxic precision 87–88%, extras of $7–14.

  — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Raw ratio signal, main pool, 30 d.** dev = F/pre_mid − 1 with no basis; F is the OKX 1 m VWAP.

  | \|dev\| bucket (bps) | Swaps | Share in correcting direction | AS of the bucket |
  |---|---:|---:|---:|
  | <0.25 | 490 | 58% | −0.68 bp |
  | 0.25–0.5 | 624 | 66% | −0.40 bp |
  | 0.5–1 | 946 | 72% | −0.04 bp |
  | 1–2 | 983 | 85% | +0.44 bp |
  | 2–5 | 59 | 92% | +1.90 bp |
  | ≥5 | 72 | 85% | +8.71 bp |

  Across all buckets, correcting flow is 73% of volume. The correlation between deviation and USDC-buy sign is 0.31. A premium at α = 0.5 on this signal would have extracted $50.85 (0.39 bp) against $45.50 of bleed (5-min AS). — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Raw ratio signal, other pools (30 d):**
  - Slipstream: correcting share rises from 56% to 95% across buckets; correlation 0.60; bleed $157.90; raw-signal extra $59.21 (37%).
  - 0.18 bp: correlation 0.17; bleed $1.34; extra $23.37.
  - 0.4 bp: correlation 0.21; bleed $1.34; extra $17.04.

  — [Unichain RPC](https://mainnet.unichain.org), [OKX](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m)
- **Next-trade prediction.** When a trade leaves the pool ≥0.5 bp off OKX at the next trade's time (7 d, 1 s), the next trade corrects it with hit rates of:
  - 76% in the main pool (n = 632, correlation 0.35)
  - 72% in the 0.18 bp pool
  - 80% in the 0.2 bp pool
  - 70% in the 0.4 bp pool
  - 77% in v3 1 bp
  - 60% on Slipstream

  — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 s](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s)
- **The deviation is real, not reference noise.** AS against OKX hardly decays from 0 s to 1 h (main pool 0.390 → 0.334 bp), and the pool's own mid moves in the trade's direction (self-markout 0.10 → 0.26 bp). So the pool converges toward OKX, not the other way round. — [Unichain RPC](https://mainnet.unichain.org), [OKX 1 s](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1s)
- **Repo baseline for comparison.** Stable pairs showed no directional fuel: AMM basket capture 0.6%, CEX addition 6.3% with 58% correlation. The repo calls a slow-basis de-trend mandatory for volatile pairs, where 62% of the raw gap is slow basis. — [research/PARAMETERS.md](/home/user/pegguard/research/PARAMETERS.md), [README.md](/home/user/pegguard/README.md)

### Inferences
- **For PegGuard as designed** (τ = 450 s de-trended deviation), "no directional fuel for stables" holds on Unichain's main stable pool. The trailing basis absorbs the slow pool-versus-CEX gaps that arbitrageurs actually close. The residual sign is about random (precision ≈ 50–60%).
- **Without de-trending**, a dual-feed USDC/USDT0 ratio carries a genuine signal at ≥1 bp deviations. This is the only Unichain-specific nuance against the repo's stable-pair conclusion: deviations here are larger, 0.3–0.5 bp median and 1–3 bp at p90–p99, and are corrected by bots.
- **The money is too small to matter.**
  - Total LVR-like fuel across all Unichain stable pools is about $200/month.
  - The best case for a raw-signal premium is about $50/month on the main pool, before route-away. Arbitrage bots, about 68% of flow, would likely route to sister pools: 71% of multi-pool transactions are already stable-stable cycles.
  - Raising the static base fee is the simpler lever. The main pool's break-even is about 0.35 bp against a 1 bp fee, which matches the repo's "base fee is the binding lever" conclusion.
- **Guard mode** with a 50 bp trip remains appropriate. A pair-relative (ratio) feed is mandatory, because USDC/USD alone drifted up to 12.7 bp.
- **Correction to the repo's truth metric.** For sparse stable pools (median inter-arrival 6–80 s, many ±300 s windows holding 1–3 swaps), the shadow/truth.py ±300 s centered median should exclude the labeled swap's own transaction or use a longer window. Otherwise precision and capture are inflated by construction.

### Gaps
- There was no Pyth reference (HTTP 401), so the "dual-feed" analysis uses the OKX USDC-USDT pair as a proxy. Pyth confidence and staleness effects on stable ratios remain unmeasured on Unichain.
- Route-away elasticity is unobservable. All extraction figures are same-swaps upper bounds.
- The single 30-day window included a regime shift: the USDC premium drifted from about 0 to 13 bp and Slipstream volume collapsed. Other regimes, such as depegs, were not sampled.
