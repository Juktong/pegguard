# Oracles, depeg history and Unichain-specific stablecoin risk: design input for a dual-feed GUARD depeg breaker

Prepared 2026-10-13. Every number has a UTC date. "Measured" means I computed it from raw data pulled on 2026-10-13. The scripts and raw data are in `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/oracles_depeg/` (`scripts/` and `data_*/`). Repo code I refer to: `src/PegGuardHook.sol` (GUARD branch of `_feeForSignal`, `_readOracle`, `MAX_STALENESS_*`, `CONF_ANOMALY_NUM`, `MIN_DISARM_DELAY`) and `research/PARAMETERS.md` (`tripBps` = 50, justified by "feed noise about 0.2 bps").

**Data access caveat (important).** The brief assumed Hermes works from this environment, but Pyth's historical and price endpoints no longer do. On 2026-10-13 at 18:33 UTC, `/v2/updates/price/latest`, `/v2/updates/price/{ts}`, `/api/latest_price_feeds`, `/api/get_price_feed` and benchmarks `/v1/updates/price/{ts}` all returned HTTP 401 "unauthorized". The TradingView history shim returned 404. Only the metadata endpoints (`/v2/price_feeds`) still answer. Pyth says Hermes has required an API key since the 2026-08-26 Pyth Core upgrade. I replaced Hermes with real Pyth aggregate data from three other places:
- Pyth `PriceFeedUpdate` events on EVM chains. Sonic carries both stable feeds; Unichain has had no updates since 2025-09-02.
- Live polling of Pyth's sponsored `PriceUpdateV2` accounts on Solana.
- Public CEX candles from OKX, Coinbase, Bitstamp and Kraken. Binance returned 451 and Bybit returned 403 (geo-blocked).

## Q1. Which oracle providers are live on Unichain (chain id 130) for stablecoins, and what are their properties?

### Takeaway
Pyth is the only provider I could confirm that has both USDC/USD and USDT/USD (plus USDT0/USD, DAI, USDS, USDe and others) at sub-second publisher cadence. On Unichain, though, the Pyth contract is effectively dormant for stables. The last USDC/USD and USDT/USD update was 2025-09-02, 406 days ago, and USDT0, DAI, USDS and USDe were never pushed. A PegGuard pool therefore has to bring its own Pyth updates on every swap. The update fee is currently 0 wei, but Hermes now needs a paid or trial API key. Chainlink on Unichain has only USDC/USD (24 h heartbeat, 0.3 % deviation) and no USDT/USD, so it cannot form a USDC/USDT ratio. It does provide the L2 sequencer uptime feed, which is useful. I could not verify stablecoin feed addresses for RedStone, Chronicle, API3, Stork or eOracle on Unichain.

### Cited Findings
**Pyth on Unichain**
- The Pyth contract on Unichain mainnet (and Unichain Sepolia) is `0x2880aB155794e7179c9eE2e38200202908C17B43`. Unichain is listed under "Not upgraded" in the 2026-08-26 Pyth Core EVM upgrade table, which shows "Upgraded (0) / Not upgraded (65)" mainnets. Pyth says "We recommend new integrations use the upgraded EVM contracts" — [Pyth EVM contract addresses](https://docs.pyth.network/price-feeds/core/contract-addresses/evm).
- Hermes now requires a key. Cutover was 2026-08-26 16:00 UTC: "`hermes.pyth.network` now requires authentication, including for integrations that were upgraded automatically". Keys are self-serve at Pyth Terminal, where "a free trial is included, paid plans cover ongoing use". The header is `Authorization: Bearer $PYTH_API_KEY`. The on-chain contracts were upgraded in place and "preserve the Pyth Core interface" — [Pyth upgrade guide](https://docs.pyth.network/price-feeds/core/upgrade/preparing); [Pyth getting started](https://docs.pyth.network/price-feeds/core/getting-started). The Price Pusher needs v10.5.0+ with an API-key flag — [Pyth price pusher docs](https://docs.pyth.network/price-feeds/schedule-price-updates/using-price-pusher).
- Measured on-chain state of the Unichain Pyth contract at block 61,168,151 (2026-10-13 18:35:10 UTC), read via `eth_call` — [Unichain public RPC](https://mainnet.unichain.org), [contract on Uniscan](https://uniscan.xyz/address/0x2880aB155794e7179c9eE2e38200202908C17B43):
  - `singleUpdateFeeInWei()` = 0 and `getValidTimePeriod()` = 60 s.
  - `getPriceUnsafe(USDC/USD)`: 0.99988856, conf 6.30 bps, publishTime 1756817007 (2025-09-02 12:43:27 UTC), 406.2 days old.
  - `getPriceUnsafe(USDT/USD)`: 1.00011496, conf 6.06 bps, same publishTime.
  - ETH/USD was last updated 2026-07-02 08:10:02 UTC, 103 days old.
  - USDT0/USD, DAI/USD, USDS/USD, USDe/USD, FDUSD/USD and PYUSD/USD revert with `PriceFeedNotFound()` (0x14aebe68), so they have never been pushed on Unichain.
- Measured: `eth_getLogs` returned zero USDC/USD or USDT/USD `PriceFeedUpdate` events from this contract over the latest 10,000 blocks (about 2.8 h, 2026-10-13). The public Unichain RPCs cap `eth_getLogs` at 10,000 blocks, and publicnode needs a token for archive ranges, so I did not reconstruct the full history — [Unichain RPC](https://mainnet.unichain.org), [drpc](https://unichain.drpc.org).
- Pyth Hermes metadata, fetched 2026-10-13. Feed IDs, all `Crypto.X/USD`, exponent −8 — [Hermes /v2/price_feeds](https://hermes.pyth.network/v2/price_feeds?asset_type=crypto):

| Feed | Pyth ID |
|---|---|
| USDC/USD | `eaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a` |
| USDT/USD | `2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b` |
| USDT0/USD | `cfc1303ea9f083b1b4f99e1369fb9d2611f3230d5ea33a6abf2f86071c089fdc` |
| DAI/USD | `b0948a5e5313200c632b51bb5ca32f6de0d36e9950a942d19751e833f70dabfd` |
| USDS/USD | `77f0971af11cc8bac224917275c1bf55f2319ed5c654a1ca955c82fa2d297ea1` |
| USDE/USD | `6ec879b1e9963de5ee97e9c8710b742d6228252a5e2ca12d4ae81d7fe5ee8c5d` |
| SUSDE/USD | `ca3ba9a619a4b3755c10ac7d5e760275aa95e9823d38a84fedd416856cdba37c` |
| FDUSD/USD | `ccdc1a08923e2e4f4b1e6ea89de6acbc5fe1948e9706f5604b8cb50bc1ed3979` |
| PYUSD/USD | `c1da1b73d7f01e7ddd54b3766cf7fcd644395ad14f70aa706ec5384c59e76692` |
| USDG/USD | `daa58c6a3ce7d4b9c46c32a6e646012c17c4a2b24c08dd8c5e476118b855a7da` |
| RLUSD/USD | `65652029e7acde632e80192dcaa6ea88e61d84a4c78a982a63e98f4bbcb288d5` |
| USD1/USD | `0a2425d43486780990d8b63543029e20556be51fd756cca584212f4d539611d4` |
| GHO/USD | `2a0e948f637a8c251d9f06055e72eb4b3880dd57848bbdb02993c8165d7df4ee` |
| FRAX/USD | `735f591e4fed988cd38df74d8fcedecf2fe8d9111664e0fd500db9aa78b316b1` |
| TUSD/USD | `433faaa801ecdb6618e3897177a118b273a8e18cc3ff545aadfc207d58d028f7` |
| EURC/USD | `76fa85158bf14ede77087fe3ae472f66213f6ea2f5b411cb2de472794990fa5c` |

- The Pyth feed ID equals the Pythnet price-account pubkey. USDC/USD `eaa020c6…` base58-encodes to `Gnt27xtC473ZT2Mw5u8wZ68Z3gULkSTb5DuxJy7eJotD` (my computation). The public Pythnet RPC returned "Your IP or provider is blocked" (403), so I could not read it directly — [pythnet.rpcpool.com](https://pythnet.rpcpool.com).
- Pyth confidence semantics: each publisher's interval is meant "to achieve 95% coverage". The aggregate is (μ−σ, μ+σ). A protocol can decide "there is too much uncertainty when σ/μ exceeds some threshold". The best-practices page gives no guidance on cross rates — [Pyth best practices](https://docs.pyth.network/price-feeds/core/best-practices).
- Cross-rate confidence in Pyth's own SDK: `Price::div` "uses the 1-norm instead of the 2-norm". For p±a divided by q±b it computes `p/q * (a/p + b/q)`, which is "at most a factor of sqrt(2) greater than the correct result" `p/q*sqrt((a/p)^2+(b/q)^2)` — [pyth-sdk-rs price.rs](https://raw.githubusercontent.com/pyth-network/pyth-sdk-rs/main/pyth-sdk/src/price.rs). The Solidity `PythUtils.deriveCrossRate` "doesn't return the combined confidence interval" — [PythUtils.sol](https://raw.githubusercontent.com/pyth-network/pyth-crosschain/main/target_chains/ethereum/sdk/solidity/PythUtils.sol).

**Chainlink on Unichain**

- Chainlink's Unichain directory has 12 entries — [Chainlink reference data directory, feeds-ethereum-mainnet-unichain-1.json](https://reference-data-directory.vercel.app/feeds-ethereum-mainnet-unichain-1.json):
  - USDC/USD proxy `0xbd1cD1518eFB92a92100da62D4C488c810dFd75b`: heartbeat 86,400 s, deviation 0.3 %, 18 decimals.
  - USDC/USD-SVR proxy `0x7E0145617F93fd5fc507Cf68D628Ebf59C76c04c`: 86,400 s, 0.3 %, 18 decimals.
  - L2 Sequencer Uptime Status Feed proxy `0x495639D9914e7D270c5dCC641BfB1d807423F813`.
  - Also ETH/USD, BTC/USD, UNI/USD, LINK/USD, a USDC/USD test-capped feed, and the ezETH, rsETH, weETH and wstETH exchange-rate feeds.
  - There is no USDT/USD, DAI/USD, USDS/USD or USDe/USD feed on Unichain.
- A Chainlink changelog entry dated 2026-03-08 lists a new USDC/USD feed on Unichain — [Chainlink changelog](https://dev.chain.link/changelog/added-support-to-data-feeds-9026c).
- Measured on 2026-10-13 18:52 UTC. Chainlink USDC/USD on Unichain read 0.99988517, last updated 2026-10-12 22:23:51 UTC (20.5 h old). The uptime feed read answer 0 (up), with status last changed 2026-09-02 20:00:59 UTC — [Unichain RPC](https://mainnet.unichain.org).

**Other providers**

- Data Streams: Chainlink lists Streams Trade on Arbitrum, Avalanche, Base, BNB Chain, Ethereum, Optimism and Polygon. I could not retrieve the verifier-proxy network table, so Unichain support is unconfirmed — [Chainlink Data Streams supported networks](https://docs.chain.link/data-streams/supported-networks).
- Unichain's developer docs list these oracle providers for Unichain mainnet and Sepolia: Api3 (Api3 Market), Pyth, RedStone ("both Pull and Push (onchain) price feeds"), Stork, eOracle, Gas Network (mainnet only) and Chronicle ("90+ data feeds"). No contract addresses are given — [Unichain oracles docs](https://developers.uniswap.org/docs/unichain/tools/oracles.md).
- RedStone calls itself the official oracle on Unichain and says its Push model backs Venus Protocol there — [RedStone blog, 2025-02-11](https://blog.redstone.finance/2025/02/11/redstone-the-go-to-blockchain-oracle-powering-unichains-defi/). I found no Unichain USDC, USDT or USDT0 push-feed address.
- Chronicle says it is live on Unichain with 90+ feeds. Its Unichain-specific stablecoin feeds are not listed in the sources I found, and reads are whitelist-gated — [Chronicle blog](https://chroniclelabs.org/blog/chronicle-oracles-now-powering-unichain); [KeeperHub Chronicle plugin](https://docs.keeperhub.com/plugins/chronicle).

**Uniswap v4 pool oracle**

- The repo's vendored `lib/v4-core/src` has no `observe` function and no `Oracle` library (checked with grep on 2026-10-13). `lib/v4-periphery/src/hooks` contains only `permissionedPools`. v4 pools have no built-in TWAP, so a TWAP needs an oracle hook. Source: repo files `/home/user/pegguard/lib/v4-core/src`, `/home/user/pegguard/lib/v4-periphery/src/hooks`.

**How often Pyth stables are actually pushed on chain**

Measured on 2026-10-13 with `eth_getLogs` over each chain's latest 1k–10k blocks, filtered on the USDC and USDT feed IDs — [chain_density.py output; public RPCs](https://rpc.soniclabs.com):

| Chain | USDC/USD | USDT/USD |
|---|---|---|
| Sonic | 6.5 /h | 6.5 /h |
| HyperEVM | 3.7 /h | 3.7 /h |
| Ethereum | 2.2 /h | 0 in 16.7 h |
| Berachain | 1.4 /h | 1.4 /h |
| Arbitrum, Optimism, Avalanche, Blast, Linea, Mantle, Unichain | 0 | 0 |

Base, BNB, Polygon and Sei could not be measured (rate-limited or refused).

### Inferences
- On Unichain, PegGuard cannot rely on a third party to keep Pyth fresh. Every swap that hits GUARD logic has to carry fresh Hermes update bytes. The swapper or router can call `updatePriceFeeds` first, or the hook can accept `hookData` and call `pyth.updatePriceFeeds{value: fee}` itself inside a try/catch. The fee is 0 today, but governance can change it, so the code should handle a non-zero fee.
- Because Hermes needs a key, every router, keeper or solver that wants to swap through the pool needs Pyth API access. That is a new availability dependency: if Hermes is unreachable, the pool silently falls back to the base fee.
- Chainlink cannot be a second leg on Unichain because there is no USDT/USD feed. With a 0.3 % deviation and 24 h heartbeat it is also blind to anything under 30 bps. It is useful only as a coarse sanity bound on the USDC leg, plus the sequencer uptime feed.
- A v4 pool TWAP is circular for a breaker that protects the same pool, and v4 has no built-in TWAP. It should not be a fallback.

### Gaps
- RedStone, Chronicle, API3, Stork and eOracle: I found no verified Unichain addresses, heartbeats or deviation thresholds for USDC, USDT or USDT0. Their catalogs are JS-rendered and the GitHub manifests were not reachable from this session.
- Chainlink Data Streams on Unichain is unconfirmed.
- Full Unichain Pyth update history is unknown because of the RPC range caps. I only know the last-update timestamps.
- I don't know which chains count as "upgraded" for Pyth Core, or whether the "Not upgraded" Unichain contract will keep accepting new-format updates long term. The docs only say "contact the team".
- I found no gas cost figure for a two-feed `updatePriceFeeds` call on Unichain.
- I did not find the Hermes free-tier limits or pricing.

## Q2. Measured feed quality: noise, staleness and confidence of Pyth USDC/USD and USDT/USD and of the USDC/USDT ratio, compared with CEX

### Takeaway
The repo's "feed noise 0.2 bps" is the right size for short-horizon changes but the wrong measure for a ratio-vs-1.0 breaker:
- **Short horizons, all measured:** Pyth USDC/USD moves 0.21 bps (p99) between ~6-second updates and 0.44 bps (p99) over about 60 s. The Pyth ratio moves 1.6 bps (p99) over 1 h.
- **Level, which matters more for a breaker vs 1.0:** in calm 2026 the Pyth ratio USDC/USDT sat 6.5 bps (median) and 12.9 bps (p99) away from 1.0, with a 151-day maximum of 15.7 bps. This is driven by USDT's persistent 2026 discount of about 5–12 bps.
- **Confidence:** Pyth conf is 5–12 bps per leg and 11–24 bps on the ratio (1-norm, p50–p99) in calm, which is 10–50× the short-horizon noise. During the 2025-10-10 crash it widened to 90 bps.
- **Accuracy:** the Pyth ratio matches OKX USDC-USDT within 0.13 bps (median) and 0.77 bps (p99) at the same minute.
- **Staleness:** Pythnet publishes stable aggregates every 1 s, so staleness is purely a delivery problem, and on Unichain nobody delivers.

### Cited Findings
**Method and reproducibility (all windows in UTC)**

| Dataset | Source | Window | Script and data |
|---|---|---|---|
| Sonic Pyth on-chain | `eth_getLogs` on Pyth `0x2880aB155794e7179c9eE2e38200202908C17B43`, topic0 `PriceFeedUpdate(bytes32,uint64,int64,uint64)` = `0xd06a6b7f…6aec`, topic1 ∈ {USDC, USDT IDs}, 10k-block chunks — [Sonic RPC](https://rpc.soniclabs.com) | 2026-05-15 07:32 → 2026-10-13 18:47 (151.5 d); 121,661 logs, 0 errors | `scripts/scan_feed_logs.py` → `data_sonic_logs/sonic_usdc_usdt.jsonl`; `scripts/analyze_onchain_pyth.py`, `scripts/analyze_breaker.py` |
| Oct-2025 crash | Same scan | 2025-10-10 14:00 → 2025-10-11 14:00 (blocks 50,010,546–50,193,567) | `scripts/scan_window.py` → `data_sonic_oct2025/` |
| Solana sponsored accounts | `getMultipleAccounts` (confirmed) every 2 s on USDC `Dpw1EAVrSB1ibxiDQyTAW6Zip3J4Btk2x4SgApQCeFbX` and USDT `HT2PLQBcG5EiCcNSaMHAjSgd9F98ecpATbk4Sk5oYuM`, owner Pyth receiver `rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ`; feed_id checked against the IDs above — [Solana RPC](https://api.mainnet-beta.solana.com) | 2026-10-13 18:50:08 → 19:14:31 (727 polls, 30 distinct updates) | `scripts/sol_poll.py`, `scripts/analyze_solana.py` → `data_solana/` |
| CEX 1-minute | OKX `USDC-USDT`, Coinbase `USDT-USD`, Bitstamp `usdtusd` and `usdcusd` — [OKX history-candles](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [Coinbase candles](https://api.exchange.coinbase.com/products/USDT-USD/candles), [Bitstamp OHLC](https://www.bitstamp.net/api/v2/ohlc/usdtusd/) | 2026-09-13 18:51 → 2026-10-13 18:50 | `scripts/cex_dl.py`, `scripts/analyze_cex.py` |
| CEX hourly | Same venues | Bitstamp and Coinbase from 2022-01-01, OKX from 2023-01-01 to 2026-10-13 | `scripts/analyze_hourly.py` → `data_cex/hourly_analysis.txt` |

**Formulas**
- Leg deviation: `dev = (P − 1)·1e4` bps.
- Leg relative confidence: `conf/P·1e4`.
- Ratio: `R = P_USDC / P_USDT`.
- Ratio confidence (1-norm, as in the Pyth SDK): `c_R,lin = (c_C/P_C + c_T/P_T)·1e4`.
- Ratio confidence (2-norm): `c_R,rss = sqrt((c_C/P_C)² + (c_T/P_T)²)·1e4`.
- Ratio pairs are formed only when both legs have the same `publishTime`.

**Staleness and delivery cadence**
- **Pythnet (measured, Solana sponsored accounts, 2026-10-13 18:50–19:14 UTC):** `publish_time − prev_publish_time` = 1 s in 30 of 30 updates, so the Pythnet stable aggregate updates every second. Pyth refreshes the sponsored Solana accounts about every 53 s (p50 gap 53 s, max 55 s), with both feeds sharing the same `publish_time` in 29 of 30 updates. I first saw each price at p50 2.4 s after its publish time — [Solana RPC](https://api.mainnet-beta.solana.com).
- **Sonic (measured, 2026-05-15 → 2026-10-13):**
  - USDC/USD: on-chain update gap p50 6 s and p90 8 s. A ~6 s pusher was active from at least 2026-05-15 (the window start) to about 2026-06-29; after that it was mostly hourly. Gap p99 3,601 s, max 27,537 s.
  - USDT/USD: hourly heartbeat, gap p50 2,072 s, p90 3,603 s, max 27,537 s — [Sonic RPC](https://rpc.soniclabs.com).
- **Unichain:** last stable update 2025-09-02 (see Q1).

**Leg levels and confidence (measured, Sonic, 151 d)**

| | Deviation from 1.0 (bps) | Confidence (bps) |
|---|---|---|
| USDC/USD (n=115,117) | p50 −3.38, min −4.51, max +0.53 | p50 6.35, p90 9.69, p99 11.57, max 17.31 |
| USDT/USD (n=6,544) | p50 −8.01, min −19.0, max +2.77 | p50 5.30, p99 11.93, max 14.01 |

Source: [Sonic RPC](https://rpc.soniclabs.com).

**Short-horizon USDC/USD noise (measured, Sonic, dense stretches)**
- Consecutive updates ≤10 s apart (n=106,679): |Δ| p50 0.01, p90 0.06, p99 0.21, p999 0.46, max 1.15 bps.
- About 60 s horizon (n=86,186): |Δ| p99 0.44, max 1.82 bps.
- |USDC dev − trailing EMA(τ=450 s)|: p99 0.45, max 1.53 bps.

Source: [Sonic RPC](https://rpc.soniclabs.com).

**Ratio USDC/USDT from Pyth (measured, Sonic, 6,532 same-publishTime pairs, 2026-05-15 → 2026-10-13)**
- Signed ratio deviation: min −3.89, max +15.73 bps.
- |R−1|: p50 6.47, p90 10.59, p99 12.87, p999 14.04, max 15.73 bps.
- On a 300 s sample-and-hold grid (n=43,425): 0 % of points above 20 bps; 13.9 % above 10 bps.
- Monthly median R−1: May +8.56, Jun +7.88, Jul +7.31, Aug +6.65, Sep +2.05, Oct +8.55 bps.
- |ΔR| over about 1 h: p50 0.26, p99 1.64, max 3.12 bps.
- c_R,lin: p50 11.37, p90 20.40, p99 24.17, max 29.27 bps. c_R,rss: p50 8.51, p99 17.23, max 20.96 bps.
- |R−1| / c_R,lin: p50 0.51, p99 1.29, max 2.73.

Source: [Sonic RPC](https://rpc.soniclabs.com).

**Ratio from Solana sponsored accounts (measured, 2026-10-13 18:50–19:14 UTC, 30 updates)**
- USDC/USD −1.46 bps, conf 11.7 bps. USDT/USD −12.3 bps, conf 1.6 bps.
- R−1 = +10.9 bps, std 0.040 bps, |ΔR| between ~53 s updates p99 0.14 bps.
- c_R,lin 13.3 bps; c_R,rss 11.8 bps.

Source: [Solana RPC](https://api.mainnet-beta.solana.com).

**Pyth compared with CEX (measured, 2026-09-13 → 2026-10-13)**
- Pyth ratio (Sonic pairs) minus OKX USDC-USDT 1-minute close at the same minute, n=1,814: mean +0.16, p1 −0.16, p99 +0.76, min −0.85, max +1.10 bps. In 99.9 % of cases the Pyth ratio sat inside OKX's 1-minute [low−1 bp, high+1 bp] range.
- Pyth USDT/USD minus Coinbase USDT-USD close, n=1,808: |diff| p50 0.10, p99 0.64 bps.

Sources: [OKX API](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [Coinbase API](https://api.exchange.coinbase.com/products/USDT-USD/candles), [Sonic RPC](https://rpc.soniclabs.com).

**CEX USDC/USDT over the last 30 days (measured, 2026-09-13 → 2026-10-13)**

| | OKX USDC-USDT (n=43,200) | Coinbase 1/USDT-USD |
|---|---|---|
| Close dev (bps) | mean +3.75, p1 −0.30, p50 +2.40, p99 +11.50, max +12.70, min −1.50 | p99 +12.72, max +14.12 |
| 1-minute \|Δ\| (bps) | p50 0.10, p99 0.40, max 1.30 | p99 0.70, max 2.00 |
| \|dev − EMA450\| (bps) | p99 0.45, max 1.37 | p99 0.61 |
| 30-minute range (bps) | p99 1.50, max 2.70 | — |
| Minutes beyond threshold | 1,878 above 10 bps; none above 20 bps | 3,776 above 10 bps |

- The OKX-minus-Coinbase cross-venue basis: mean −1.03, p1 −2.3, p99 +0.1 bps.
- Daily mean OKX deviation rose from +0.8 bps (2026-10-06) to +11.0 bps (2026-10-13). This is a slow drift of about 10 bps in a week as the USDT discount widened.

Sources: [OKX API](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [Coinbase API](https://api.exchange.coinbase.com/products/USDT-USD/candles).

**USDT discount regime (measured, Coinbase USDT-USD hourly closes)**

| Period | Median USDT-USD vs $1 (bps) | Hours with \|close\| > 25 bps |
|---|---|---|
| 2025Q2 | +2.2 | 0 |
| 2025Q3 | +2.0 | 0 |
| 2026Q1 | −4.6 | 0 |
| 2026Q2 | −4.5 | 0 |
| 2026Q3 | −7.4 | 0 |
| 2026Q4 to date | −5.2 | 0 |

Source: [Coinbase API](https://api.exchange.coinbase.com/products/USDT-USD/candles). A secondary price page shows USDT at 0.998885 on 2026-08-06 (about −11 bps), which agrees — [cryptoast](https://cryptoast.fr/cours-tether-usdt-825.html).

**Single-venue wick noise (measured, OKX USDC-USDT, 2023-01 → 2026-10)**
- There were 24 hourly-extreme excursions beyond 50 bps. Outside SVB (2023-03-10 to 03-15) and 2025-10-10, all lasted ≤3 hours.
- 1-minute drill-downs show most are single-minute prints:

| Date | 1-min extreme | Minutes beyond 50 bps | Minutes with close beyond 50 bps |
|---|---|---|---|
| 2026-02-02 | 59 bps | 1 | 0 |
| 2026-02-05 | 63 bps | 1 | 0 |
| 2024-06-21 | 91 bps | 1 | 0 |
| 2023-10-02 | 566 bps | 1 | 0 |
| 2024-01-03 | 445 bps | 7 | 1 |

- 2025-01-19 was a genuine USDC premium: close up to 45 bps, 56 minutes with close above 25 bps, but no close above 50 bps.

Source: [OKX API](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m). Thin venues are much worse: Bitstamp's USDT/USD hourly series had 199 extreme-excursion episodes beyond 50 bps from 2022 to 2026, including an obviously bad print — [Bitstamp API](https://www.bitstamp.net/api/v2/ohlc/usdtusd/).

**Stress behaviour, 2025-10-10 crash (measured, Pyth on Sonic, 166 same-publishTime pairs)**
- **Before the crash (18:00–21:15 UTC):** median c_R,lin 11.8 bps, R−1 about −3 to −4 bps.
- **First move:**
  - 21:39:21: R−1 −25.8 bps (USDT/USD +33.6 bps, conf 40.0 bps).
  - 21:47:27: R−1 −51.6 bps (USDT +55.3, conf 38.7; c_R,lin 65.8).
- **Partial recovery:** back to −18 to −42 bps between 21:48 and 22:30.
- **Second excursion, 22:33–22:49:** R−1 between −54 and −65.1 bps. The low was −65.1 at 22:43:26 (c_R,lin 37.8).
- **Window extremes:** maximum c_R,lin 90.5 bps (22:11:14). |R−1| last above 25 bps at 23:18:36.
- Pyth's USDC leg stayed within ±8 bps, so the move was a USDT premium.

Source: [Sonic RPC](https://rpc.soniclabs.com).

**Same crash on CEX (measured)**
- OKX USDC-USDT: 1-minute extreme −148 bps (21:48), close −88 bps (21:47). It went from 10 to 50 bps in about 8 minutes (21:38→21:46) and spent 22 minutes with close beyond 50 bps.
- Coinbase USDT-USD: +726 bps extreme and +472 bps close (21:35–21:45), 43 minutes with close beyond 50 bps.

Sources: [OKX API](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [Coinbase API](https://api.exchange.coinbase.com/products/USDT-USD/candles).

**How the hook's confidence gate would have behaved (measured simulation)**

I replicated the hook's gate exactly: flag when confE2 > 3×EMA, return early without updating the EMA, and otherwise update the EMA as (9·EMA + x)/10.
- **Calm, Sonic 151 d:** 0 flags on either leg.
- **2025-10-10, USDT/USD:** flagged 15 of 172 observations between 21:20:07 and 22:11:14. That includes 21:47:27, the first −51.6 bps ratio crossing (conf 38.7 vs EMA 8.1). The gate was also flagged at 21:39:21 and continuously from 21:44:56 to 21:55:02.
- **2025-10-10, USDC/USD:** 0 of 19,707.

Source: [Sonic RPC](https://rpc.soniclabs.com); script `scripts/analyze_breaker.py`.

### Inferences
- **What "noise" should calibrate the breaker:**
  - For an oracle-vs-peg breaker, the relevant noise is the *level band*: 2026 Pyth max 15.7 bps, CEX hourly closes rarely above 25 bps outside events.
  - It is not the 0.2-bps short-horizon jitter.
  - At `tripBps` = 50 the margin is about 3× over the calm Pyth maximum, not 140×.
  - The margin depends on USDT's discount regime, which has already moved by about 10 bps within a week (October 2026).
- **Confidence is not a noise estimate for the ratio level:**
  - c_R ≈ 11–24 bps in calm against |ΔR| ≈ 1.6 bps per hour.
  - Conf scales up with stress: 90 bps on 2025-10-10.
  - Subtracting conf from the deviation would blind the breaker in exactly the episodes it exists for.
- **The current CONF_SPIKE fallback is unsafe in GUARD mode:** it would have masked the first 50-bps ratio crossing on 2025-10-10.
- **The EMA lock-in effect is real:** flagged observations never update the EMA, so the gate stays latched until conf falls back below 3×EMA.
- **Delivery, not publication, sets staleness:** because Pythnet updates stables every second, any staleness on Unichain comes from delivery.
- **Pyth is not the weak link for the ratio:** the Pyth-derived ratio tracks the deepest CEX market to sub-bp, so the synthetic ratio is a faithful USDC/USDT reference.

### Gaps
- The Solana poll covers only 24 minutes (30 updates). It is a snapshot of current levels and confidence, not a multi-day series.
- I have no Pyth USDT0/USD history. The Sonic scan covered only the USDC and USDT IDs, and Hermes is closed. So I cannot say how USDT0/USD differs from USDT/USD.
- I have no Pyth data for 2022–2023 events, because the Sonic history and Hermes access don't reach back. The pre-2025 events in Q3 come from CEX data only.
- I did not measure Unichain-side delivery latency (Hermes fetch to inclusion) because of the API key requirement.

## Q3. Depeg history: peak, onset speed, duration and venue differences, and what threshold and persistence a breaker should use

### Takeaway
Real issuer or reserve depegs (USDC/SVB 2023, USDT/Terra 2022, DAI 2023) crossed 50 bps **3.6–18 hours before their peak**. They stayed beyond 50 bps for **14–110 hours** with repeated re-crossings. Liquidity dislocations (2025-10-10, January 2025 USDC premium, single-minute wicks) last minutes to about an hour and are venue-dependent. Binance-only crashes such as USDe at 0.65 and FDUSD at 0.87 are invisible on other venues. So a 50-bps trip that requires about 60–120 s of persistence on an aggregated feed loses nothing material on real depegs and suppresses single-print wicks. Disarming needs a lower band (about 20–25 bps) plus a delay of 30 minutes or more.

### Cited Findings
**Event profiles from 1-minute closes (measured)**

"Peak" is the 1-minute extreme. "First >50" and the duration come from closes.

| Event | Peak (bps, time UTC) | 10 → 50 bps | First >50 → peak close | Minutes with close >50 bps; first→last span |
|---|---|---|---|---|
| USDC/USD, Bitstamp, 2023-03 | −1,947 (0.8053) at 2023-03-11 07:14 | 22:49 → 23:11 on 03-10 | 486 min (≈8.1 h) | 3,557 min; 85.3 h |
| USDC/USDT, OKX, 2023-03 | −1,302 (0.870) at 03-11 07:12 | 21:54 → 23:19 | 474 min | 5,832 min; 110.5 h |
| DAI/USD, Coinbase, 2023-03 | −1,418 (0.858) at 03-11 07:04 | (>50 first at 03:25) | 219 min | 2,404 min; 65.7 h |
| USDT/USD, Bitstamp, 2023-03 (upside) | +500 bps peak on 03-11; close peak +475 on 03-13 | — | — | 3,324 min |
| USDT/USD, Bitstamp, 2022-05 | −899 (0.9101) at 2022-05-12 07:22 | 2022-05-09 11:33 → 05-11 13:11 | 1,091 min | 823 min; 43.6 h |
| USDT/USD, Coinbase, 2022-05 | −590 (0.941) at 07:18 | (>50 first 05-11 20:57) | 624 min | 847 min; 18.9 h |
| USDT/USDC, OKX, 2022-05 | −1,150 at 07:21 | — | 1,119 min | 859 min |
| USDC/USDT, OKX, 2025-10-10 | −148 at 21:48 | 21:38 → 21:46 (≈8 min) | 1 min | 22 min; 0.4 h |
| USDT/USD, Coinbase, 2025-10-10 (upside) | +726 at 21:45 | 21:30 → 21:33 | 2 min | 43 min |
| USDT/USD, Coinbase, 2022-11 (FTX week) | −288 hourly low on 2022-11-10 12:00 | — | — | 8 hours with hourly extremes beyond 50 bps |

Additional detail for the table:
- USDC/USD Bitstamp 2023: first >100 bps at 03-11 03:51, first >500 bps at 05:56.
- USDC/USDT OKX 2023: first >100 bps at 00:55, first >500 bps at 03:34.
- USDT/USD Bitstamp 2022: first >100 bps at 05-11 20:26.
- 2025-10-10: Pyth's ratio was beyond 50 bps for about 1 h in two excursions (see Q2).

Sources: [Bitstamp OHLC API](https://www.bitstamp.net/api/v2/ohlc/usdcusd/), [OKX history-candles](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1m), [Coinbase candles](https://api.exchange.coinbase.com/products/USDT-USD/candles). Script: `scripts/analyze_events.py` → `data_cex/events_profile.txt`.

**Literature and reported events**
- **USDe on Kraken, 2025-10-10 (measured, 92 trades 20:00–08:00 UTC):** low 0.9496 at 21:23:25, 9 trades below 0.995 between 21:23 and 23:06 — [Kraken Trades API](https://api.kraken.com/0/public/Trades?pair=USDEUSD).
- **USDe on Binance, 2025-10-10:** fell to about $0.65. Binance says "severe de-pegging occurred after 21:36 (UTC)". Dune describes about 90 minutes on Binance "while holding the peg on the most liquid onchain venues like Curve". Binance paid $283M in compensation — [The Block](https://theblock.co/post/374295/binance-pays-283-million-in-compensation-following-fridays-depegs-covering-user-losses); [Dune](https://dune.com/blog/32); [CCN](https://www.ccn.com/education/crypto/ethena-usde-depeg-binance-crash-explained/).
- **FDUSD, 2025-04-02:** low reported as $0.87 by one source and $0.91 by another (they conflict). It rebounded to about $0.90 on 2025-04-03 and re-pegged about a day later. The trigger was Justin Sun calling First Digital Trust "effectively insolvent". Curve and PancakeSwap pools were 90–98 % FDUSD — [The Defiant](https://thedefiant.io/news/cefi/justin-sun-declares-first-digital-trust-insolvent-fdusd-depegs-binance-holds-1-fcdb4d5a); [Cork](https://www.cork.tech/blog/fdusd-depeg).
- **S&P Global (June 2021 – June 2023):**
  - USDC was below $0.90 for 23 minutes and DAI for 20 minutes.
  - USDT dipped below $0.95 for 1 minute; BUSD never fell below $0.975.
  - "one-minute de-peg events can be attributed to noise" near $1.
  - [Cointelegraph on S&P, 2023-09-12](https://cointelegraph.com/news/usdc-dai-depegged-more-than-usdt-sp-global-research).
- **Moody's (secondary reports):** 1,914 depeg events in 2023 (through mid-2023), 609 of them in large fiat-backed stablecoins, versus 707 in 2022 — [Cryptoast on Moody's](https://cryptoast.fr/600-stablecoins-depeg-2023-selon-les-analystes-de-moodys/).
- **Academic definitions vary:** for example, |dev| > 1 % for two consecutive days or a daily close beyond 2 % — [Research Square](https://www.researchsquare.com/article/rs-10083601).
- **Kaiko on March 2023:** USDC-USD pairs were thin beforehand ($20–40M a day). Saturday volume hit an all-time high of $600M, dominated by Kraken. Binance had delisted USDC pairs the previous September — [Kaiko](https://research.kaiko.com/insights/usdc-depeg-bots).
- **2026 events (vendor sources, unverified):**
  - ResolvUSD (USR) fell as low as $0.14 after an exploit of about $80M in March 2026 — [REAP](https://reap.global/blog/stablecoin-statistics-2026).
  - Synthetix sUSD depegged in late January 2026 — [Webacy](https://www.webacy.com/blog/from-the-ctos-desk-january-2026-webacys-stablecoin-depeg-risk-monitor).
  - Balance Coin (BLC) dropped about 99.75 % on 2026-07-22 — [CryptoDaily](https://cryptodaily.co.uk/2026/07/stablecoin-depeg-explained).
  - My OKX and Coinbase hourly data show no USDC/USDT or USDT/USD close beyond 25 bps in 2026Q1–Q4 to date. The 2026 maxima were single-minute wicks of 59–63 bps (2026-02-02 and 02-05) — [OKX API](https://www.okx.com/api/v5/market/history-candles?instId=USDC-USDT&bar=1H).

### Inferences
- **Threshold for real depegs:**
  - 50 bps fires 3.6–18 h before peak in all three reserve-driven depegs. A 25–30 bps level fires 1–2 h earlier still.
  - A 60–120 s persistence requirement costs at most about 11–22 bps of extra move. That figure comes from the fastest onset observed on the Pyth ratio: −23.6 → −51.6 bps between 21:44:56 and 21:47:27 on 2025-10-10, about 11 bps per minute.
- **Wick suppression:** OKX hourly closes were never beyond 50 bps outside real events in 2023Q2–2026Q4. The worst 1-minute close in my wick drill-downs was a single 75-bps minute (2024-01-03). Requiring two consecutive fresh reads at least 30–60 s apart removes all the single-minute wicks I measured. Pyth aggregation already removes most of them: the 151-day maximum is 15.7 bps.
- **Durations argue for hysteresis:**
  - Reserve depegs re-cross 50 bps many times over 14–110 h.
  - On 2025-10-10 the Pyth ratio fell back to 18–42 bps for 42 minutes between two excursions beyond 50 bps.
  - A disarm band at 50 bps with a 30-minute delay would have disarmed around 22:18 and re-tripped at 22:33. A 25-bps band would have stayed tripped until after 23:48.
- **Venue-local crashes don't move Pyth:** Binance-only events (USDe 0.65, FDUSD) mostly don't move an aggregated feed. An on-chain Unichain pool sees them only if arbitrageurs bridge that dislocation in. That is a reason to keep a pool-vs-oracle lag check as well as the peg check.

### Gaps
- I have no Pyth-aggregate history for 2022–2023, so I can't tell how Pyth's ratio and conf behaved during SVB or Terra. Those event numbers are CEX-based.
- I found no primary-source minute data for FDUSD or for Binance's USDe series, since Binance is geo-blocked here and OKX doesn't list them.
- Kraken USDCUSD trades for March 2023 were not downloaded (the job was stopped for time).
- Bitstamp's USDC/USD book is thin (−1,947 bps vs about −1,300 on OKX), so Bitstamp lows overstate the depth of the dip.
- I did not verify the 2026 USR, sUSD or BLC events beyond vendor summaries. None of them affects USDC or USDT.

## Q4. Unichain-specific risk: issuer, bridge and sequencer

### Takeaway
Stablecoin TVS on Unichain is small: about $28M, measured on-chain on 2026-10-13. USDC is native: Circle mints and burns via CCTP domain 10, and its contract has blacklist and pause roles. USDT0 is a LayerZero OFT backed by USDT locked on Ethereum; I verified a 3-of-3 required-DVN set on every pathway (LayerZero Labs, Canary, USDT0). A small canonical-bridge USDT also exists, which is a different asset from USDT0. The sequencer has had 20 reported down episodes (126 minutes in total) since February 2025. Forced inclusion takes up to 12 h, and upgrades have no exit window. USDT0 can depeg from USDT independently, through a bridge, DVN or adapter failure, and the USDT/USD feed would not see that.

### Cited Findings
**Supplies on Unichain (measured, `totalSupply` via `eth_call`, 2026-10-13 18:52 UTC)** — [Unichain RPC](https://mainnet.unichain.org)

| Token | Address | Supply |
|---|---|---|
| Native USDC | `0x078D782b760474a361dDA0AF3839290b0EF57AD6` | 19,998,245.66 |
| USD₮0 | `0x9151434b16b9763660705744891fA906F660EcC5` | 7,596,008.21 |
| "Tether USD" (canonical-bridge USDT) | `0x588CE4F028D8e7B53B687865d6A67b3A54C75518` | 68,117.22 |
| DAI | `0x20CAb320A855b39F724131C69424240519573f81` | 4,499.4 |
| USDS | `0x7E10036Acc4B56d4dFCa3b77810356CE52313F9C` | 177.7 |

- L2BEAT shows total TVS of $88.40M, of which stablecoins are $27.96M (31.6 %), consistent with the on-chain sum of about $27.67M — [L2BEAT Unichain](https://l2beat.com/scaling/projects/unichain).

**USDC (Circle)**
- USDC went live on Unichain natively with CCTP; Circle says no bridging is required. The announcement is dated 2025-02-11 — [Circle](https://www.circle.com/blog/now-available-usdc-on-unichain).
- Unichain is CCTP domain 10 and supports Standard Transfer, Fast Transfer and the Forwarding Service as a source chain — [Circle CCTP domains](https://developers.circle.com/cctp/concepts/supported-chains-and-domains).
- Measured on 2026-10-13: the USDC contract exposes `owner` `0x0806d309…dd64`, `masterMinter` `0xd000dfe6…25d0`, `blacklister` `0x15dab8b3…a55a` and `pauser` `0x12bf9d1d…8b46`. `paused()` = false and `version()` = "2" — [Unichain RPC](https://mainnet.unichain.org).

**USDT0 (LayerZero OFT)**
- Architecture: "The original asset (USDT…) is locked in the OFT Adapter smart contract on Ethereum Mainnet". OFT-to-OFT transfers burn on one chain and mint on the other without touching Ethereum — [USDT0 docs](https://docs.usdt0.to/).
- Tokens "share a common upgradeable ERC-20 implementation… a chain's feature set can change when its implementation is upgraded", and there is "a compliance blocklist" — [USDT0 token features](https://docs.usdt0.to/technical-documentation/token-features).
- Security page: "Triple-DVN Verification (3/3)" (LayerZero, USDT0 and Canary DVNs). Audits by Guardian (filename dated 2025-01-14), Paladin (2025-01-10) and ChainSecurity. Immunefi bounty up to $6,000,000 — [USDT0 security](https://docs.usdt0.to/technical-documentation/security).
- Legacy Mesh: Ethereum, Tron, TON, Solana and Celo USDT connect through an Arbitrum USDT0 hub using liquidity pools, with "a 0.03% fee attached to each transfer". Unichain is not mentioned — [USDT0 Legacy Mesh](https://docs.usdt0.to/overview/the-legacy-mesh).
- Measured USDT0 config on Unichain at block 61,169,268 (2026-10-13 18:53:47 UTC). The OFT is `0xc07bE8994D035631c36fb4a89C918CeFB2f03EC3` (token `0x9151…`, endpoint `0x6F475642a6e85809B1c36Fa62763669b1b48DD5B`, owner `0x4DFF9b5b0143E642a3F63A5bcf2d1C328e600bf8`). For all 14 peers found among the EIDs I probed (EIDs 30101 Ethereum, 30109, 30110 Arbitrum, 30111 Optimism, 30181, 30280, 30295, 30333, 30339, 30362, 30367, 30383, 30390, 30396):
  - Receive and send ULN configs both use **requiredDVNs = 3, optional = 0**: `0x282b3386…46b4`, `0x00a979a5…6fc8` and `0x20889434…a899`.
  - Send confirmations are 1,600 blocks.
  - Receive confirmations vary by source: 65 from Ethereum, 60 from Arbitrum, 1,000 from Optimism, up to 43,200 from HyperEVM.
  - [Unichain RPC](https://mainnet.unichain.org), `data_lz/usdt0_unichain_dvn_config.txt`.
- LayerZero's metadata names those DVNs on Unichain as LayerZero Labs (`0x282b…`), Canary (`0x00a9…`) and USDT0 (`0x2088…`) — [LayerZero metadata API](https://metadata.layerzero-api.com/v1/metadata/dvns).
- Measured on 2026-10-13: the USDT0 token is an EIP-1967 proxy (implementation `0xaf37e8b6…47ff`, admin `0xcb768e26…59cc`), and the OFT is a proxy too (implementation `0x13c41af9…6ef9`, admin `0xa882c21c…15b1`), so both are upgradeable — [Unichain RPC](https://mainnet.unichain.org).
- Context, secondary source: on 2026-04-18 the Kelp DAO rsETH OFT lost about $292M through forged messages under a 1-of-1 DVN setup. The same analysis said USDT0 deployments on Ethereum, Optimism and Base were flagged as 1-of-1 at that time; Unichain was not named. USDT0 itself was not exploited — [ThreatCluster](https://threatcluster.io/cluster/usdt0-enhances-security-architecture-after-kelp-incident-6dd325a4). One Eco explainer describes only a 2-DVN set, which conflicts with the 3/3 that I verified on-chain for Unichain — [Eco](https://eco.com/support/en/articles/14998914-usdt0-explained-layerzero-s-omnichain-usdt).
- LayerZero's own docs warn that each pathway has its own DVN config and that defaults can resolve to a single DVN — [LayerZero message security](https://docs.layerzero.network/v2/concepts/protocol/message-security).

**Other bridged representations**
- The "Tether USD" at `0x588CE4F0…5518` is an OptimismMintableERC20 with `remoteToken` = `l1Token` = Ethereum USDT `0xdAC17F958D2ee523a2206206994597C13D831ec7` and `bridge` = `0x4200000000000000000000000000000000000010` (the L2StandardBridge). It is a canonical-bridge USDT, separate from USDT0 — [Unichain RPC](https://mainnet.unichain.org).
- I found no USDC.e. Circle says Unichain USDC is native — [Circle](https://www.circle.com/blog/now-available-usdc-on-unichain).

**Blacklist and freeze background**
- Tether's per-chain blacklists are controlled by Tether's owner multisig. In 2025, 4,163 addresses were blacklisted, freezing $1.26B across Ethereum and Tron — [BlockSec](https://blocksec.com/blog/1-26-billion-frozen-usdt-blacklisting-on-ethereum-and-tron-in-2025).

**Sequencer and rollup**
- L2BEAT rates Unichain Stage 1. It uses interactive fraud proofs (a 3d12h challenge plus 3d12h execution delay). Users can force transactions through L1 "with up to a 12h delay". "There is no exit window for users to exit in case of unwanted upgrades". Both the Security Council and the Foundation must approve upgrades. Data goes to Ethereum as blobs. L2BEAT lists no sequencer outage in its milestones (mainnet 2025-02-12, flashblocks 2025-08-14) — [L2BEAT Unichain](https://l2beat.com/scaling/projects/unichain).
- Measured from the Chainlink L2 Sequencer Uptime Feed on Unichain, 56 rounds (`getRoundData`, phase 1) — [Unichain RPC](https://mainnet.unichain.org), `data_unichain_seq/uptime_rounds.txt`:
  - 28 DOWN rounds, which merge into **20 down episodes** (flaps within 10 minutes counted as one) between 2025-02-18 and 2026-09-02.
  - Total 126.5 minutes; median 4.4 minutes; maximum 27.0 minutes (2026-08-07 20:42:11 → 21:09:11, with 9 flips).
  - Others: 15.4 min (2025-02-18), 13.0 min (2025-10-12 02:25), 11.4 min (2025-06-06), 8.2 min (2026-08-05), 4.6 min (2026-09-02).
  - Six episodes clustered on 2025-10-02 to 10-12.
- Alchemy reported a finalized-tag stall on Unichain mainnet, resolved after about 2 h on 2026-09-23. This is provider-side, not confirmed as a sequencer halt — [IsDown/Alchemy](https://isdown.app/status/alchemy/incidents/659640-finalized-block-stall-on-unichain-mainnet-in-use).
- Unichain's status page lists an "Active Sequencer stalled" incident of about 11 h that the search summary attributes to Sepolia. I could not open it because of an `instatus` redirect — [status.unichain.org](https://status.unichain.org/cm478l6qg004cpa98khiodtyl).

### Inferences
- **USDT0 can depeg from USDT on its own.** A USDC/USDT0 pool is exposed to issuer risk on both coins and also to USDT0 bridge risk: a DVN collusion or compromise, an adapter bug, or a malicious upgrade by the OFT or token admin. All of these could create unbacked USDT0 without any USDT/USD move.
- **The 3/3 DVN set limits mint risk but adds an exit delay.** A forged mint would need all three DVNs. Liveness, though, depends on all three: Unichain-to-other-chain sends wait 1,600 confirmations (about 27 min at 1 s blocks). Arbitrage across chains is therefore slow, which can stretch out a local USDT0 discount.
- **Freeze risk:** USDC can be paused or blacklisted by Circle. USDT0 has a compliance blocklist with an upgradeable implementation. If a pool's address or a large LP were blacklisted, swaps would revert, which is outside PegGuard's control. A global USDC pause would make USDC/X pools unusable.
- **Sequencer downtime is real but short** (median about 4 min). After downtime, pent-up arbitrage and stale pull prices hit the pool in the first blocks. Forced inclusion takes up to 12 h, so LPs can't exit promptly during an outage.
- **The canonical-bridge USDT is a third "USDT".** Its risk profile differs: it relies on the OP-stack bridge with no Tether blocklist on L2, and its liquidity is tiny. Pools must pin token addresses explicitly.

### Gaps
- I could not confirm whether Unichain's USDT0 is reachable through the Legacy Mesh (via the Arbitrum hub) or what that means for redemption paths.
- I did not decode the USDT0 token's blocklist or pause functions; `paused()` reverted on the token.
- I did not verify the OFT and ProxyAdmin owner multisig thresholds.
- The exact Chainlink criterion for flagging DOWN on OP-stack chains is unknown, so the episodes are "reported" downtime.
- I found no official Unichain mainnet incident post-mortems.
- I don't know the CCTP Fast Transfer allowance for Unichain.

## Q5. Design recommendations for PegGuard GUARD mode: a dual-feed ratio breaker

### Takeaway
Replace the current single-feed, pool-vs-oracle trip with an oracle-vs-peg ratio signal, D = P_A/P_B − 1, and keep the pool-lag deviation only for pricing. Trip at |D| ≥ 50 bps on two fresh reads at least 60 s apart, or immediately at |D| ≥ 100 bps. Arm at 25 bps or on a confidence or sequencer stress signal. Never treat a confidence spike or stale data as a reason to loosen. Disarm only after 30–60 minutes with |D| + c_R ≤ 20–25 bps, checked on chain. Charge the guard fee on flow that sells the *weak* token into the pool, priced at least at the pool-oracle gap. The current code charges the opposite side and, as written, likely never trips on a real depeg.

### Cited Findings
- **Repo code: trip input.** GUARD trips on `absE2 > tripBps*100`, where `devE2 = fair·basis/mid − 1` and `basis` is a pool-vs-oracle EMA (τ=450 s, updated every swap in `afterSwap`). This measures *pool lag vs oracle*, not oracle vs peg. Source: `/home/user/pegguard/src/PegGuardHook.sol` lines 211–256 and 261–279; `src/lib/SignalMath.sol` (`deviationBps`, `emaUpdate`).
- **Repo code: fee direction.** When TRIPPED, `if (!SignalMath.isCorrecting(devE2, zeroForOne)) fee = c.guardFeePips;`. Flow that moves the pool *toward* the oracle pays the base fee; flow moving away pays `guardFee`. Source: `PegGuardHook.sol` lines 251–254; `SignalMath.isCorrecting`.
- **Repo code: oracle failure.** Any failure, including `CONF_SPIKE`, returns `_beforeSwapFee(c.baseFeePips)` before the breaker is evaluated. The confidence EMA updates only on non-flagged reads (`(9·ema+x)/10` per `afterSwap`). Source: `PegGuardHook.sol` lines 198–202 and 299–321.
- **Repo code: disarm path.** Only the control plane disarms (`onBreakerSignal`, after holding the request for `MIN_DISARM_DELAY` = 30 min). No oracle check is made at disarm time. Source: `PegGuardHook.sol` lines 354–368.
- Measured evidence for thresholds, staleness and hysteresis is in Q2 and Q3 above (Sonic Pyth, Solana Pyth, OKX, Coinbase and Bitstamp data, 2022-01 → 2026-10-13).
- The confidence propagation formula `c_R/R = c_A/P_A + c_B/P_B` follows the Pyth SDK `Price::div` (1-norm, ≤√2× the 2-norm) — [pyth-sdk-rs](https://raw.githubusercontent.com/pyth-network/pyth-sdk-rs/main/pyth-sdk/src/price.rs).
- On Unichain the Pyth update fee is 0 wei, nobody pushes stable feeds, and Hermes needs an API key — [Unichain RPC](https://mainnet.unichain.org); [Pyth upgrade guide](https://docs.pyth.network/price-feeds/core/upgrade/preparing).
- The Chainlink Sequencer Uptime Feed on Unichain is at `0x495639D9914e7D270c5dCC641BfB1d807423F813` — [Chainlink directory](https://reference-data-directory.vercel.app/feeds-ethereum-mainnet-unichain-1.json).

### Inferences
**1. The current GUARD breaker as written probably misses real depegs, and its fee asymmetry may protect the wrong side**

- **Missed depegs.** On Unichain (1 s blocks), arbitrage keeps the pool close to the oracle, and the 450-s basis EMA absorbs any persistent offset. A real depeg therefore shows up as a large *oracle* move with a small *pool-vs-oracle* deviation. May 2022 took about 50 h to go from 10 to 50 bps on Bitstamp, so a 50-bps pool-lag trip would rarely fire.
- **Fee on the wrong side.** Suppose USDT0 falls to 0.95 with token0 = USDC and token1 = USDT0. Fair (USDT0 per USDC) is about 1.0526 against a pool mid of 1.00, so devE2 > 0. "Correcting" flow sells USDT0 for USDC, which is exactly the arbitrage that drains good USDC from LPs. Under the current code that flow pays only the **base** fee. The flow that buys the weak USDT0 from LPs pays the guard fee.
- **Recommendation.** Define direction relative to the *peg* and the weak leg, not relative to the oracle. Please verify this against the intended semantics.

**2. Signal**

Compute:
- Per leg: `d_A = P_A − 1` and `d_B = P_B − 1`.
- Ratio: `R = P_A/P_B` (orient to the pool's token1-per-token0).
- Peg deviation: `D = R − 1`.
- Ratio confidence: `c_R = c_A/P_A + c_B/P_B`.
- Weak leg: the one with the lower `d`.

The state machine uses D and the legs. Pricing uses the pool lag `L = mid/(R·basis_long) − 1`, with a slow basis (hours or days, never adapting while ARMED or TRIPPED) or no basis at all for stables. For a USDT0 pool, also read Pyth USDT0/USD and use `min(P_USDT, P_USDT0)` for that leg. ARM if `|P_USDT0/P_USDT − 1| ≥ 25 bps`, as a bridge-specific depeg detector (unmeasured; see Gaps).

**3. Thresholds**

| State | Trigger | Rationale |
|---|---|---|
| ARMED | `|D| ≥ 25 bps` on 2 fresh reads ≥30 s apart; OR `c_R ≥ max(40 bps, 3× its 24-h median)`; OR sequencer uptime feed DOWN or less than 30–60 min since UP; OR the USDT0-vs-USDT spread is ≥25 bps | Calm Pyth max 15.7 bps over 151 d; January 2025 USDC-premium closes of 45 bps would ARM but not TRIP |
| TRIPPED | `|D| ≥ 50 bps` on 2 fresh reads spanning ≥60 s; OR one fresh read with `|D| ≥ 100 bps` | 50-bps crossings came 3.6–18 h before peak in reserve depegs. The fastest observed Pyth onset is about 11 bps/min, so persistence costs ≤20 bps. The Pyth ratio never exceeded 15.7 bps in 151 calm days, and OKX hourly closes never exceeded 50 bps outside real events (2023Q2–2026Q4) |
| Disarm | `|D| + c_R ≤ 20–25 bps` held continuously for ≥30 min (60 min if the trip came from a ≥100-bps print), checked **on chain with a fresh read** at disarm, plus the control-plane delay | On 2025-10-10 the ratio stayed at 18–42 bps for 42 min between excursions beyond 50 bps; real depegs re-crossed for 14–110 h |

Keep the threshold absolute against 1.0 rather than against a moving baseline. A baseline would absorb slow depegs, like May 2022's two-day ramp from 10 to 50 bps. Revisit 25/50 if USDT's discount regime shifts: 2026 medians are −4.5 to −7.4 bps, and the current Pyth ratio is about +11 bps.

**4. Confidence handling**

- Don't subtract conf from |D| to decide a trip. On 2025-10-10, `|D| − 1.0·c_R > 50` never fired even though |D| reached 65 bps.
- In GUARD mode a conf anomaly should ARM, not fall back to the base fee and skip the breaker.
- Use a time-based conf baseline, such as a 24-h median or an EMA with a time constant, not a per-swap EMA with α=0.1.
- Update the baseline even on flagged reads, or cap how long the gate can stay latched. The current gate latches because flagged reads never update the EMA.
- Use conf asymmetrically: it may only make loosening harder (as in the disarm condition).

**5. Staleness**

- **Pricing reads.** Pythnet publishes every second, so keep tight freshness for the fee premium: the existing 5 s calm and 2 s volatile limits.
- **Breaker reads.** A breaker read can safely accept `maxAge` ≤ 60 s for *tightening*. Calm |ΔR| over 1 h is p99 1.6 bps, and the fastest onset is about 11 bps/min.
- **Loosening reads.** Require ≤5–10 s freshness.
- **Delivery.** On Unichain every swap must bundle an update. Accept the update bytes via `hookData` and call `updatePriceFeeds` in a try/catch; the fee is 0 wei now, but read `getUpdateFee`. Alternatively, run an API-keyed keeper pushing about every 30–60 s.

**6. When one or both feeds are stale**

- **One leg stale (≤ a 10-min hard cap):** evaluate the fresh leg alone against 1.0 at the same thresholds, using the stale leg's last value as the denominator. Allow tightening only.
- **Both legs stale or missing:** keep the last breaker state. If TRIPPED, keep charging the guard fee on the last-known weak-leg sell side. Don't silently revert to the base fee: the invariant "never worse than static fee" still holds because the guard fee applies only to weak-leg-selling flow.
- **Sequencer:** on DOWN or during the grace period, treat as ARMED.

**7. Fee asymmetry ("deepening" versus "re-pegging")**

When TRIPPED:
- Flow that sells the weak leg into the pool should pay `max(guardFee, base + k·|L| + m·|D|)`, capped. For example k = 1 and m = 0.5, with a cap of a few hundred bps. The arbitrageur then pays roughly the oracle gap, which effectively makes LPs whole.
- Flow that buys the weak leg (re-pegging) pays the base fee.
- When ARMED: use the HARVEST-style premium on weak-leg-selling flow only, at half strength.

**8. Fallbacks**

- Don't use a v4 pool TWAP: it is circular, has no built-in oracle, and can be manipulated.
- Don't use Chainlink as a second leg, because there is no USDT/USD feed on Unichain. Use Chainlink USDC/USD (0.3 %/24 h) only as an extra ARM input when `|P_CL − 1| ≥ 30 bps`.
- RedStone or Chronicle could become a second source later if Unichain stable feeds are confirmed.

**9. Operational items**

- Budget for a Pyth API key: the Hermes free trial is followed by paid plans.
- Monitor the Pyth "Not upgraded" status of the Unichain contract.
- Re-run this calibration quarterly. The USDT-discount regime moved the ratio level by about 10 bps within one week in October 2026.

### Gaps
- The direction and semantics issue (item 1) comes from code reading plus a worked example. It has not been tested in the Foundry suite. A replay test with a synthetic depeg path should confirm it, for example the measured 2025-10-10 Pyth ratio path from `data_sonic_oct2025/`.
- The USDT0/USD feed's quality and divergence from USDT/USD are unmeasured, so the 25-bps bridge-spread ARM is a judgment call.
- I didn't measure the gas cost of adding a second feed read and an in-hook `updatePriceFeeds`.
- I don't know the swap frequency on Unichain stable pools, which affects how the per-swap EMA and conf gate behave.
- Route-away elasticity is not modeled: if the guard fee drives flow to other venues, the economic effect is unknown.
