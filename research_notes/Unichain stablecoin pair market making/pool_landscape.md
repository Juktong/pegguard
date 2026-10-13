# Unichain stablecoin inventory and stable/stable pool landscape (snapshot 2026-10-13)

Snapshot convention: unless labelled otherwise, every number is from **2026-10-13 18:32–19:45 UTC**. The Unichain head at the start was **block 61,167,971 (ts 1791916330 = 18:32:10 UTC)**. Pool-state reads ran at blocks 61,169,0xx–61,170,4xx. Unichain has exactly 1-second blocks: blocks 8,829,241, 15,309,241 and 36,477,241 map to 2025-02-15, 2025-05-01 and 2026-01-01 00:00:00 UTC, which were checked with `eth_getBlockByNumber`. That is why "30d" means blocks 58,575,971 → ~61,169,300. All scripts are in `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/pool_landscape/` (rpc.py, bs_logs.py, rpc_logs.py, v4_positions.py, hist_77ea.py, swapstats.py, bench.py, bench_agg.py, vol_sample.py). Raw downloads are in `.../pool_landscape/data/`.

**Naming warning:** GeckoTerminal renders Unichain **USD₮0 (USDT0) as "USD0"**. For example, GT calls pool 0x77ea…59c9 "USDC / USD0 0.01%", while Merkl and on-chain data show it is USDC/USD₮0 (currency1 = 0x9151…ecc5). Usual's USD0 is **not** present on Unichain. GT's "USDT" on Unichain is the legacy OP-standard-bridged USDT (0x588c…5518), not USDT0.

## Q1. Which stablecoins are live on Unichain, at what supply, and how has supply moved through 2025–2026?

### Takeaway
Unichain has **~$27.7M of stablecoins**, ranked **#56 of all chains** on DefiLlama. Base has $5.2B, Arbitrum $3.7B and OP Mainnet $695M. Nearly all of it is **native USDC ($20.0M) and USDT0 ($7.6M)**. Everything else (sUSDS, sUSDC, bridged USDT, oUSDT, DAI, frxUSD, USDS, vyUSD) totals under $0.4M.
- Supply peaked around $433–440M in late June/July 2025 during the Uniswap/Merkl incentive programme. That figure includes a ~$100M USDS (and ~$95M sUSDS) inventory pre-minted to Spark's ALM proxy.
- Supply then decayed steadily. The Spark inventory was burned on 2026-07-06.
- Several "stablecoins" in Unichain pools are fakes with billion-scale supplies: fake USDC 0xb3fc…, fake USDe, BOLD, FRAX, EURC and others.

### Cited Findings
**Current inventory.** On-chain `totalSupply()` was read at block 61,169,045 (2026-10-13 ~18:50 UTC) and cross-checked against DefiLlama `chainCirculating.Unichain`.

| Token | Address (Unichain) | Type / bridge | On-chain supply | DefiLlama (current) | Source |
|---|---|---|---|---|---|
| USDC | 0x078D782b760474a361dDA0AF3839290b0EF57AD6 | Circle native | 19,998,245.66 | $20,160,046 (prev week $24.68M, prev month $22.02M) | [Circle USDC addresses](https://developers.circle.com/stablecoins/usdc-contract-addresses); [DefiLlama](https://stablecoins.llama.fi/stablecoins?includePrices=true) |
| USD₮0 (USDT0) | 0x9151434b16b9763660705744891fA906F660EcC5 | LayerZero OFT (OFT contract 0xc07bE8994D035631c36fb4a89C918CeFB2f03EC3; listed under "Native Deployments", not "Legacy Mesh") | 7,596,008.21 | $7,577,125 | [USDT0 deployments](https://docs.usdt0.to/technical-documentation/deployments); [DefiLlama](https://stablecoins.llama.fi/stablecoins?includePrices=true) |
| sUSDS | 0xa06b10db9f390990364a3984c04fadf1c13691b5 | Sky savings token (not ERC-4626 on Unichain; `convertToAssets` reverts) | 149,319.49 sUSDS | DefiLlama yields "sky-lending SUSDS" TVL $166,014 | [uniscan](https://uniscan.xyz/address/0xa06b10db9f390990364a3984c04fadf1c13691b5); [DefiLlama yields](https://yields.llama.fi/pools) |
| sUSDC (Spark USDC Vault) | 0x14d9143becc348920b68d123687045db49a016c6 | ERC-4626; 1 sUSDC = 1.112698 USDC; totalAssets 126,470.94 USDC | 113,661.44 | n/a | [uniscan](https://uniscan.xyz/address/0x14d9143becc348920b68d123687045db49a016c6) |
| USDT (bridged, "USDT.e") | 0x588ce4f028d8e7b53b687865d6a67b3a54c75518 | OP standard bridge (`bridge()` = 0x4200…0010, `remoteToken()` = mainnet USDT 0xdac1…1ec7) | 68,117.22 | (in DefiLlama USDT total) | [uniscan](https://uniscan.xyz/address/0x588ce4f028d8e7b53b687865d6a67b3a54c75518) |
| oUSDT (OpenUSDT) | 0x1217bfe6c773eec6cc4a38b5dc45b92292b6e189 | Superchain OpenUSDT | 11,419.09 | n/a | [uniscan](https://uniscan.xyz/address/0x1217bfe6c773eec6cc4a38b5dc45b92292b6e189) |
| vyUSD | 0x984ae4c68fb3ec037fac36d48622f30eb5ae1361 | — | 7,144.61 | n/a | [uniscan](https://uniscan.xyz/address/0x984ae4c68fb3ec037fac36d48622f30eb5ae1361) |
| DAI (bridged) | 0x20cab320a855b39f724131c69424240519573f81 | OP standard bridge (remote = mainnet DAI) | 4,499.41 | $4,500 | [DefiLlama](https://stablecoins.llama.fi/stablecoins?includePrices=true) |
| frxUSD | 0x80eede496655fb9047dd39d9f418d5483ed600df | Frax (LZ) | 1,843.59 | $1,843 | same |
| USDS | 0x7e10036acc4b56d4dfca3b77810356ce52313f9c | Sky USDS (not OP standard bridge) | 177.73 | $178 (DefiLlama yields labels this underlying "SUSDS", but on-chain symbol is "USDS") | same |
| GUSD (bridged) | 0xeba12ec786cdc21b4bd5ba601b595b6a5c0920a9 | OP standard bridge | 44.43 | n/a | uniscan |
| PYUSD (bridged) | 0x0d2f98904d88909072ea6e61105cbbf78e6207c5 | OP standard bridge (remote 0x6c3e…a0e8) | 10.00 | n/a | uniscan |
| rUSD (Reservoir) | 0x09d4214c03d01f49544c0448dbe3a27f768f2b34 | — | 5.18 | $5 | DefiLlama |

- **Not present or not real.**
  - The standard Ethena USDe/sUSDe OFT addresses (0x5d3a…ef34, 0x211c…e5d2) have no code on Unichain.
  - Tokens named "USDe" with 2.63B and 631M supply are fakes, as are "BOLD" (100B), "FRAX" (100B), "EURC" 0x7352… (18 decimals, 1T), "WEUR" (1T), "SUSDE" 0x6421… (1B), "USD.uni" (421.5M) and "azUsd" (1.6e32).
  - **0xb3fca863dd0f6b496ccddf6497da5dad67857f56 ("USDC", 2.03B supply) is a fake USDC paired in 1,034 pools.**
  - No GHO, crvUSD, Circle EURC or USDC.e (bridged USDC) was found among the 10,590 tokens that appear in v3/v4 pools.
  - Source: on-chain `totalSupply/decimals/remoteToken/bridge` reads via [Unichain RPC](https://mainnet.unichain.org), saved in `data/stable_supply_onchain.json` and `data/token_meta_merged.json`.
- **Chain ranking:** Unichain is #56 by stablecoin market cap at $27,741,855, against Ethereum $145.68B, Base $5.21B, Arbitrum $3.75B, OP Mainnet $695.4M, Ink $165.9M and World Chain $17.3M. — [DefiLlama stablecoinchains](https://stablecoins.llama.fi/stablecoinchains)

**Supply trend.** On-chain `totalSupply` was read via archive `eth_call` at each date's 00:00 UTC block. Values are in token units (≈USD).

| Date (block) | USDC | USDT0 | USDS | sUSDS | sUSDC | USDT.e | DAI | oUSDT |
|---|---|---|---|---|---|---|---|---|
| 2025-02-15 (8,829,241) | 5,147,365 | – | – | – | – | 154,757 | 30,278 | – |
| 2025-04-01 (12,717,241) | 6,227,213 | 1,534 | – | – | – | 123,502 | 30,328 | 7,191 |
| 2025-05-01 (15,309,241) | 78,094,602 | 132,292,810 | 0 | 0 | – | 406,188 | 32,390 | 10,182 |
| 2025-07-01 (20,579,641) | 152,273,355 | 180,670,659 | 100,000,000 | 94,897,184 | 22,082,607 | 461,173 | 39,625 | 38,507 |
| 2025-09-01 (25,936,441) | 96,762,116 | 66,394,563 | 100,001,000 | 94,897,184 | 40,400,822 | 186,200 | 39,866 | 68,321 |
| 2025-11-01 (31,206,841) | 57,288,116 | 34,805,963 | 100,001,005 | 94,897,184 | 25,036,800 | 119,849 | 45,868 | 104,456 |
| 2026-01-01 (36,477,241) | 42,134,604 | 23,333,465 | 100,001,005 | 94,897,184 | 3,271,425 | 99,809 | 12,183 | 78,000 |
| 2026-03-01 (41,574,841) | 39,710,335 | 33,605,268 | 100,001,005 | 94,897,184 | 1,315,430 | 97,609 | 4,860 | 32,488 |
| 2026-05-01 (46,845,241) | 36,393,717 | 7,055,464 | 100,001,007 | 94,897,186 | 285,327 | 71,121 | 4,901 | 36,628 |
| 2026-07-01 (52,115,641) | 21,878,563 | 6,077,635 | 99,991,007 | 94,887,186 | 127,159 | 71,121 | 4,715 | 40,884 |
| 2026-07-09 (52,806,841) | 21,066,707 | 6,148,236 | 178 | 149,319 | 126,877 | 71,121 | 4,715 | 15,316 |
| 2026-09-01 (57,472,441) | 18,597,676 | 5,618,874 | 178 | 149,319 | 145,193 | 71,121 | 4,675 | 19,566 |
| 2026-10-13 (61,166,041) | 19,998,308 | 7,582,749 | 178 | 149,319 | 113,661 | 68,117 | 4,499 | 11,419 |
— on-chain via [Unichain RPC](https://mainnet.unichain.org) (`data/supply_history_onchain.json`)

- **DefiLlama totals for all Unichain stablecoins** (`totalCirculatingUSD`, 1st of month):
  - 2025: Mar $4.65M, May $210.4M, Jul $433.0M, Sep $263.1M, Nov $192.2M.
  - 2026: Jan $165.4M, Mar $173.3M, May $143.4M, Jul $127.9M, Aug $25.8M, Sep $24.0M, Oct $29.4M.
  - 2026-10-13: $27.1M (chart) and $27.74M (current endpoint).
  - DefiLlama's peak days: USDT 2025-07-08 at $203.7M; USDC 2025-07-18 at $235.4M. — [DefiLlama Unichain chart](https://stablecoins.llama.fi/stablecoincharts/Unichain); [USDC](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=2); [USDT](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=1)
- **The ~$100M step-down in DefiLlama's total between 2026-07-01 and 2026-07-07 is USDS.**
  - DefiLlama USDS (id 209) on Unichain was a flat ~$99.97M "minted" from 2025-06-28 and fell to $178 on 2026-07-08. — [DefiLlama USDS on Unichain](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=209)
  - On-chain, 99,990,828.81 USDS and 94,737,866.16 sUSDS were burned by **Spark `ALMProxy` 0x345e368fccd62266b3f5f37c9a131fd1c39f5869** at block 52,612,800 (2026-07-06 ~18:00 UTC), tx 0x33f66feba68e407fd92e5b4c46da5a53389096a5a6b9c40b8909f1a57986edda. — [Blockscout ALMProxy](https://unichain.blockscout.com/address/0x345e368fccd62266b3f5f37c9a131fd1c39f5869)
- **Where supply sits now** (Blockscout holder lists, 2026-10-13):
  - USDC top holders are EOAs 0xB5A2…138C (3.73M), 0x5752…C792 (2.11M) and 0xdc32…8B87 (2.00M); the v3 USDC/HYPE pool 0x5d3e…08C3 (2.32M); and the **v4 PoolManager (2.00M USDC)**.
  - The largest USDT0 holders are EOAs 0xdc32…8B87 (2.88M), 0xE1fb…B93c (1.41M) and 0xaA1b…B897 (1.21M). The v4 PoolManager holds 324,134 USDT0.
  - — [Blockscout USDC holders](https://unichain.blockscout.com/token/0x078D782b760474a361dDA0AF3839290b0EF57AD6?tab=holders); [USDT0 holders](https://unichain.blockscout.com/token/0x9151434b16b9763660705744891fA906F660EcC5?tab=holders); PoolManager `balanceOf` via [RPC](https://mainnet.unichain.org)
- **Lending wrappers:** Euler EVK vaults on Unichain are small. eUSDC-1 (0x6eae…82ba) has totalAssets 104,605 USDC and eUSD₮0-1 (0xd491…ead3) 71,900 USDT0. — on-chain `totalAssets()` via [RPC](https://mainnet.unichain.org)

### Inferences
- The "addressable" stable float on Unichain is ~$27.6M of USDC+USDT0, about 0.5% of Base's. The 2025 peak was incentive-driven (UNI via Merkl, and the Spark/Sky inventory), and both programmes have ended or unwound.
- USDT0 supply is volatile in the low single-digit millions: it went 33.6M → 7.1M between Mar and May 2026, then rose 5.6M → 7.6M from Sep to Oct 2026. A USDT0-heavy inventory therefore depends on bridging flows.
- Any MM or hook logic must hard-code token addresses. Symbol-based discovery on Unichain is polluted by fakes such as fake USDC 0xb3fc…, which sits in 1,034 pools.

### Gaps
- I did not verify Circle's CCTP domain ID for Unichain or whether CCTP V2 fast transfers are enabled. I also did not check whether Sky/Spark plans to redeploy the USDS/sUSDS inventory.
- A Uniswap governance RFC says "Unichain USDS holdings rose from under 20M to nearly 45M" (per search-result summary only). That conflicts with the flat on-chain 100M pre-mint and was not verified. — [Uniswap gov RFC](https://gov.uniswap.org/t/rfc-uniswap-unichain-usds-and-susds-co-incentives-growth-management-plan/25650)

## Q2. What are all the stable/stable pools on Unichain, and what are their TVL, volume, fees, hooks and turnover?

### Takeaway
Unichain's stable/stable DEX liquidity is **~$0.30M in total**.
- **One pool matters:** Uniswap v4 USDC/USDT0 **0.01%, tickSpacing 1, no hook** (poolId 0x77ea…59c9). It has **$159.5k TVL, $84.6k 24h / $409k 7d / $1.36M 30d volume and $136 of LP fees in 30d (~1.0% fee APR)**. It carries ~93% of the last 24h of stable/stable volume (~$84.6k of ~$90.5k).
- About a dozen satellite pools (fee 0.0018%/0.002%/0.004% v4, Velodrome CL1, v3 0.01%/0.05%) each hold $2–66k. They collect bursty arbitrage/aggregator flow. All USDC/USDT0 venues together did **~$5.4M in 30d**, about 1.7% of Unichain's $321.9M 30d DEX volume.
- Hook-based venues are almost empty now: Bunni, 212 EulerSwap instances, VII Finance YieldHarvestingHook, LogCumHook, GridHook and Spot.
- **No incentive campaign is live on Unichain** (Merkl LIVE list for chain 130 = 0).

### Cited Findings
**Discovery methodology.**
- All v4 pools come from PoolManager `Initialize` logs: 0x1f98400000000000000000000000000000000004, topic0 0xdd466e67…6438. There were **7,748 pools** through block 60,954,140; 2,573 use the dynamic-fee flag and 5,481 have hooks.
- All v3 pools come from UniswapV3Factory 0x1f98400000000000000000000000000000000003 `PoolCreated` logs: **5,780 pools**.
- The v2 factory 0x1f98…0002 reports `allPairsLength` = **1,046,223** (mostly spam), so v2 was checked with `getPair` over all stable×stable combinations instead.
- Velodrome CL factory 0x04625b046c69577efc40e6c0bb83cdbafab5a55f (from `factory()` of a CL pool) was queried with `getPool(a,b,ts)` for ts ∈ {1,10,50,100,200,2000}. Velodrome v2 PoolFactory 0x31832f2a97fd20664d76cc421207669b55ce4bc0 was queried with `getPool(a,b,stable)`.
- Stable sets are the 13 legit tokens in Q1. Pools between yield-bearing wrappers (sUSDC/sUSDS, Euler eUSDC/eUSD₮0, VII-wrapped vaults, Morpho/Venus/Compound shares) were also checked.
- Logs came from the Blockscout etherscan-compatible API, paginated by block, and from the public RPC in 10k-block × 10-call batches. Blockscout completeness was cross-checked against RPC on 4 sample ranges and matched exactly.
- Volumes are computed from `Swap` events (v4: the input side is the negative swapper delta; v3/Velodrome: the positive pool delta), over 24h, 7d and 30d windows ending at block ~61,169,300.
- v4 TVL = the sum of token amounts of all live positions, reconstructed from `ModifyLiquidity` and valued at the current sqrtPrice with both tokens at $1. For the main pool the reconstructed active liquidity equals StateView `getLiquidity` exactly (136,161,330,009,421).
- — Uniswap addresses from [Uniswap v4 deployments](https://developers.uniswap.org/contracts/v4/deployments) and [v3 Unichain deployments](https://developers.uniswap.org/contracts/v3/reference/deployments/unichain-deployments); logs via [Unichain Blockscout API](https://unichain.blockscout.com/api-docs) and [RPC](https://mainnet.unichain.org)
- **Counts:**
  - **331 v4 pools** have both currencies in the legit stable set (261 of them USDC/USDT0). They break down as:
    - 67 vanilla (no hook), including USDC/USDT0 at 31 different static fee tiers from 0 to 10,000 pips;
    - 212 EulerSwap instances (hook address low-14-bit flags 0x28a8 = beforeInitialize|beforeAddLiquidity|beforeSwap|beforeDonate|beforeSwapReturnsDelta; `getReserves()`/`getParams()` respond);
    - 25 other static-fee hooked pools and 7 dynamic-fee hooked pools;
    - 20 pools with fees of 10% or more (e.g. 85–99.6% fee USDC/sUSDC and USDC/sUSDS pools, which are non-economic).
  - **19 v3 pools** and **22 v2 pairs**; every v2 pair holds less than $2.
  - **4 Velodrome CL pools** and **2 Velodrome v2 pools** (v2 = dust).
  - — on-chain (`data/v4_pools.json`, `data/v3_stable_state.json`)

**Pool table.** Pools with TVL > ~$1k or 30d volume > $10k; the rest are dust. Fee is in hundredths of a bp (pips): 100 = 0.01%. "Turn30" = 30d volume / TVL. "APR" = 30d LP fees × 365/30 / TVL, with no incentives.

| Venue / pool | Pair | Fee, tickSpacing, hook | Current tick (price USDT-side/USDC) | TVL | 24h vol | 7d vol | 30d vol | 30d LP fees | Turn30 | Fee APR |
|---|---|---|---|---|---|---|---|---|---|---|
| **v4 0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9** (created blk 12,876,338, 2025-04-02) | USDC/USDT0 | 100 (0.01%), ts 1, none | 10 (1.00101) | $159,515 (61,587 USDC + 97,928 USDT0) [GT: $148,900] | $84,595 (404 swaps) | $409,145 | $1,359,569 (3,453 swaps; GT OHLCV: $1,122,781) | $135.96 | 8.5× | 1.0% |
| v4 0xaf58ab3ed922b34e94d13e01edf1b4ddbe5d2afbc29abbcef5ef8ff752a1ae5a | USDC/USDT0 | 18 (0.0018%), ts 1, none | 9 | $4,178 | $1,811 | $113,818 | $1,360,608 (22,421 swaps) | $24.49 | 326× | 7.1% |
| v4 0x2c6809bbb1ddc601d76ddee68f17e683bd8430795f1b38b1cb7b0d4c28b73e88 | USDC/USDT0 | 40 (0.004%), ts 1, none | 12 | $4,251 | $203 | $71,555 | $626,078 (9,616) | $25.04 | 147× | 7.2% |
| v4 0xc7ee4db44db3234cb0a3dc7fb2fd4d068d9bfb0c71092fc4a21edb2d95e34306 | USDC/USDT0 | 20 (0.002%), ts 1, none | 8 | $2,351 | $54 | $20,351 | $206,499 (6,795) | $4.13 | 88× | 2.1% |
| Velodrome CL 0x31bafd5d04580f71a808ae646bb787d38e9362f9 | USDC/USDT0 | fee() 100, ts 1 | 9 | $2,277 | $181 | $8,307 | $1,731,679 (7,225; 98% of it on Sep 14–30) | $173 | 760× | (≈92%, burst-driven) |
| v3 0xe92c7cc875245a86faf088febe4614e1e318bef5 | USDC/USDT0 | 500 (0.05%), ts 10 | 13 | $65,815 (25,841 + 39,974) | $75 | $4,551 | $8,205 | $4.10 | 0.12× | 0.08% |
| v3 0x5c75bfb6194d7d763d33ea292cbc50cda806451b | USDC/USDT0 | 100, ts 1 | 10 | $2,543 | $2,044 | $13,451 | $31,702 | $3.17 | 12.5× | 1.5% |
| v3 0x18b268965e4e702bdf13469205937894b8ab0ee8 | USDC/USDT.e | 500, ts 10 | 16 | $25,464 | $0 | $10,291 | $33,251 | $16.63 | 1.3× | 0.8% |
| v4 0x3d4d39a2ec28d80efa72679e47b8d4621caeecc15af8f21be97db234657d5fa7 | USDC/USDT.e | 500, ts 10, none | 16 | $10,157 | $397 | $1,747 | $9,850 | $4.93 | 1.0× | 0.6% |
| v4 0xa3851829dd8fd7c336c9049e3f6b2b84581e0958fed5333757c6f9c595f4e4f0 | USDC/USDT.e | 100, ts 1, none | 16 | ~$550 (GT) | $25 | $443 | $6,948 | $0.69 | — | — |
| v3 0x1dfab2147401be78ea05f05a0379f86ec87a81cc | USDC/USDT.e | 100, ts 1 | 16 | $238 | $47 | $891 | $6,864 | $0.69 | — | — |
| v4 0x8273f8aa0a528c776286195d53fb12cacc63006aebca40e012e2ec6203b3649b | USDC/vyUSD | 500, ts 10, none | 276324 (1.00003) | $11,683 | 0 | 0 | $2 | 0 | 0 | 0 |
| v4 0x3188bf36b4ac5127d077a5e873ec297cd1d05447a70ae05cdf8e7c3e74a4e48d | USDC/DAI | 100, ts 1, none | 276413 (1 USDC = 1.00895 DAI; stale) | $3,437 | $28 | $152 | $568 | $0.06 | 0.17× | 0.02% |
| v4 0x56805e9aa6db6842d13defda4c1c4cadaaf040a0aa153df12f826dda89b7ff53 | frxUSD/USDC | 100, ts 1, none | — | ~$1,770 (GT) | $1 | $57 | $175 | — | — | — |
| Velodrome CL 0x5c7e1f0dcfa6d4f300c55bab41f27289c88a202a | USDC/oUSDT | 100, ts 1 | 4 | $2,923 | 0 | 0 | $32,997 | $3.30 | 11× | 1.4% |
| v4 0xfd7f15c95d41bf752b054d7d877d84943722b78941f56aeec2ee29d6f9b85237 (blk 43,375,097) | USDC/USDT0 | dynamic (0x800000), ts 1, **LogCumHook** 0xf425990ae831f3ad1b93d1058882456c0b18b0c0 | — | ~$5,075 (GT) | 0 | 0 | 0 swaps | 0 | 0 | 0 |
| EulerSwap instance (hook 0xb5c643879006742699d1cc2581c28f177963a8a8; pool 0xe97d693d41…) | USDC/USDT0 via Euler vaults eUSDC-1 / eUSD₮0-1 | key fee 10 (0.001%); hook fee param 1e13/1e18 = 0.001%; eq. price 1.00018; concentration ≈0.99999 | — | equilibriumReserve0 1,999.32 USDC (virtual, Euler-credit backed) | $1,022 | $20,835 | $60,214 (678 hook Swap events; matches DefiLlama EulerSwap Unichain 30d $60,101) | ~$0.6 | — | — |
| VII Finance pools (YieldHarvestingHook 0x777ef319… / 0x77a19c56…), e.g. 0xb4772185… VII-eUSD₮0-1/VII-eUSDC-1 (fee 18) and 0xcca661c1… VII-eUSD₮0-2/VII-eUSDC-5 (fee 20) | vault-share pairs | static, ts 1 | −3 / −11 | < $1k (VII wrapper supplies 1–482 units) | — | — | 32 swaps ≈$2.0k / 105 swaps ≈$4.0k | ~0 | — | — |
| Bunni v2 USDC/USDT0 (BunniHook 0x0000fe59823933ac763611a69c88f91d45f81888; pool 0x477e849b19565e52a8f6fa9c710c064445857e760c9db80b312495df7b48b340; LP token 0x65e44c6863f36735B7D98836BDdBdA734CCDF19d) | USDC/USDT0 | key fee 0, ts 10 | — | ~$17–26 (GT $17; 26.4 LP shares) | 0 | 0 | 0 | 0 | — | — |
| v2 pairs (22, e.g. USDC/USDT0 0xc536e0d1f44b8a405779a05095266f4db4b447bb) | various | 0.3% | — | < $2 each | 0 | 0 | 0 | — | — | — |

— on-chain via [Unichain RPC](https://mainnet.unichain.org) and [Blockscout](https://unichain.blockscout.com/api-docs). Main pool GT figures from [GeckoTerminal pool 0x77ea…](https://www.geckoterminal.com/unichain/pools/0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9) and [GT API](https://api.geckoterminal.com/api/v2/networks/unichain/tokens/0x078D782b760474a361dDA0AF3839290b0EF57AD6/pools?page=1&sort=h24_volume_usd_liquidity_desc) (fetched ~18:35 UTC). Data files: `data/v4_stable_swap_agg30.json`, `data/pos_*.json`, `data/v3logs/`.

- **Hooks seen on Unichain stable pools**, identified via Blockscout verified-source names:
  - Bunni hooks: `BunniHook` at 0x000052423c1db6b7ff8641b85a7eefc7b2791888, 0x004ff78112c3fbc1004fa517e1334dd4930f1888 and 0x005af73a245d8171a0550ffae2631f12cc211888. The hook used by the Bunni USDC/USDT0 pool (0x0000fe59…1888, 23.5KB) is unverified.
  - `LogCumHook` (0xf425990a…b0c0, 0xf8744e2d…b0c0; dynamic fee).
  - `GridHook` (0x2e7c80cf…9540; pools 0xeb33fe71… fee 100 and 0x8a52260a… fee 20; GT TVL ~$17).
  - `Spot` (0xa0b0d2d0…10cc; dynamic, ts 200/60).
  - `YieldHarvestingHook` (VII Finance).
  - `AssetToAssetSwapHookForERC4626` (0xc92338e0…4888, 0x604e6c45…c888, 0x7fc3b316…8888, 0x01cc8dc6…4088): USDC/USDT0 "router" pools that convert into vault-share pools. Their PoolManager `Swap` events carry zero amounts (105 and 32 swaps in 30d).
  - `Generic4626Router` (0x17a10f79…6888).
  - `LongETH` (0xbaeb9a7c…28c4, 0x1112f587…28c4).
  - Unverified: 0x420ba55b…9a80, 0xbf910eb9…0088, 0x86838db6…c0c4, 0x58e5954e…c040, 0xb249770a…5088, 0x1673ce5f…0088, 0xf1336bfd…c088, 0xb0d6135a…4088, 0xf8c3f424…4300, 0xa6c8d751…c0c0, 0xb28e8bda…4320.
  - Only the vanilla pools, Velodrome, v3, the one EulerSwap instance, VII and the ERC4626 router pools recorded any swap in the 30d scan of all 331 v4 stable pools (46,063 Swap logs).
  - — [Blockscout smart-contract API](https://unichain.blockscout.com/api-docs) (e.g. [LogCumHook](https://unichain.blockscout.com/address/0xf425990ae831f3ad1b93d1058882456c0b18b0c0), [GridHook](https://unichain.blockscout.com/address/0x2e7c80cf7ecc15c9d6578b8efb4fc37a28ce9540))
- **EulerSwap footprint:**
  - There are 212 EulerSwap-pattern instances on stable pairs, mostly USDC/USDT0, created at blocks ~19.1M–26.4M (Jun–Sep 2025).
  - Their stored `getReserves()` sum to $78.3M USDC / $77.2M USDT0. These are virtual or stale reserves, **not TVL**: the backing Euler vaults now hold ~$105k/$72k.
  - Only instance 0xb5c6…a8a8 traded in the last 30d. — on-chain `getReserves/getParams` via [RPC](https://mainnet.unichain.org); [DefiLlama dexs Unichain](https://api.llama.fi/overview/dexs/Unichain)
- **Unichain DEX context:**
  - DefiLlama: total 24h $9.82M, 7d $54.67M, 30d $321.85M. By protocol (30d): Uniswap V3 $192.8M, Uniswap V4 $122.3M, Velodrome V3 $6.75M, EulerSwap $60.1k, Curve DEX $24.4k, UniDerp $29.2k. Uniswap V2, Velodrome V2 and Bunni V2 are $0. — [DefiLlama dexs Unichain](https://api.llama.fi/overview/dexs/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true)
  - The busiest Unichain pools are non-stable: v3 USDC/HYPE 0.3% ($8.58M 24h, $7.45M TVL) and v4 USDC/ETH 0.05% ($1.25M 24h, $3.71M TVL). — [GT top pools](https://api.geckoterminal.com/api/v2/networks/unichain/pools?page=1&sort=h24_volume_usd_desc)
- **Main pool history** (monthly snapshots; TVL reconstructed from 138,901 `ModifyLiquidity` events plus archive `getSlot0`; volume = average daily volume over a 3-day sample starting on the 2nd of each month, or Apr 15–17 for 2025-04):

| Date (TVL) | TVL | tick | Active positions | Sample avg daily vol |
|---|---|---|---|---|
| 2025-04 (15–17) | — | — | — | $43.0M |
| 2025-05-01 | $123.9M | −2 | 871 | $45.2M |
| 2025-06-01 | $118.5M | −4 | 1,558 | $20.3M |
| 2025-07-01 | $106.2M | −2 | 1,382 | $28.2M |
| 2025-08-01 | $34.5M | 0 | 1,435 | $17.0M |
| 2025-09-01 | $23.0M | −2 | 1,182 | $3.81M |
| 2025-10-01 | $2.77M | −4 | 834 | $2.02M |
| 2025-11-01 | $416k | 1 | 903 | $620k |
| 2025-12-01 | $393k | −3 | 874 | $122k |
| 2026-01-01 | $329k | 11 | 861 | $183k |
| 2026-02-01 | $340k | 9 | 834 | $405k |
| 2026-03-01 | $236k | −2 | 857 | $278k |
| 2026-04-01 | $175k | 4 | 846 | $91.7k |
| 2026-05-01 | $175k | 1 | 818 | $6.5k |
| 2026-06-01 | $164k | 10 | 797 | $94.3k |
| 2026-07-01 | $163k | 11 | 788 | $23.0k |
| 2026-08-01 | $158k | 8 | 786 | $39.8k |
| 2026-09-01 | $159k | 2 | 779 | $33.6k |
| 2026-10-01 | $161k | 5 | 769 | $27.4k |
— on-chain (`data/hist_77ea.json`, `data/vol_sample_77ea.json`)

- GT daily OHLCV for the main pool by month (2026): Apr 14–30 $246.5k, May $370.0k, Jun $1.267M, Jul $701.9k, Aug $1.012M, Sep $877.1k, Oct 1–13 $520.5k. — [GT OHLCV](https://api.geckoterminal.com/api/v2/networks/unichain/pools/0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9/ohlcv/day?limit=400&currency=usd)
- **Incentives:**
  - Main pool Merkl campaigns (creator 0x2016EF507C…) ran from 2025-05-27 to 2025-09-02 for a total of **206,028 UNI**, in biweekly tranches of 62,310, 50,540, 48,706, 13,489, 10,618, 9,102, 6,799 and 4,464 UNI.
  - The Bunni USDC-USD₮0 pool got 101,174 UNI plus 967 rEUL (2025-06-10 → 2025-09-02).
  - Merkl lists a "UniswapV4 USDC-USD₮0 0.01%" opportunity with Merkl-reported TVL $88.28M (campaign created 2025-05-12) and another on the full poolId with "tvl" $21.18M and lastCampaignCreatedAt 2026-02-24. **That $21.18M conflicts with the on-chain reconstruction ($340k on 2026-02-01), so the Merkl tvl field appears stale.**
  - Bunni's Merkl-reported TVL was $24.58M in Aug 2025. Gamma USDC-USD₮0 vaults 0x3f03…EE4F ($239k) and 0xE445…3cBB are listed with past campaigns.
  - There are **zero LIVE Merkl opportunities on chain 130**.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&mainParameter=0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9&items=100); [Merkl opportunities](https://api.merkl.xyz/v4/opportunities?chainId=130&items=100&page=0); [Merkl LIVE](https://api.merkl.xyz/v4/opportunities?chainId=130&items=100&status=LIVE)
- **Who trades the main pool** (30d, by `Swap.sender`, i.e. the PoolManager caller):

| Caller | Share of volume | Swaps |
|---|---|---|
| unverified 0x099b1a87ded758e99d5a33a7df5ba9cf3a0907c9 | 28.5% | 548 |
| Universal Router 2.1.2 (0xd1b7…4343) | 15.1% | — |
| unverified 0x9c1a…c855 | 12.9% | — |
| 0x `UnichainSettler` (0x4c61…b3e9) | 11.8% | — |
| Universal Router (0xef74…eaf3) | 3.9% | — |
| Universal Router 2.1.1 (0xfdf6…fbc7) | 2.4% | — |

  - Uniswap routers plus the 0x Settler account for 33.3% in total.
  - Flow is two-sided: $676k USDC→USDT0 and $683k USDT0→USDC.
  - Swap size percentiles: p10 $7.5, p50 $127, p90 $998, p99 $3,737; max $18,273.
  - — on-chain; names via [Blockscout](https://unichain.blockscout.com/address/0x4c6112da485a9c86270ecb1b35fed0f776cfb3e9)
- **Velodrome and Curve on Unichain:** Velodrome CL pools are USDC/USDT0 ts1 ($2.3k), USDC/oUSDT ts1 ($2.9k), USDC/oUSDT ts100 (dust) and sUSDC/USDT0 ts1 (dust). Curve's API returns 0 pools for "unichain", although DefiLlama shows $24.4k of 30d Curve volume. — on-chain; [Curve API](https://api.curve.finance/v1/getPools/all/unichain)

### Inferences
- **The total fee pool available to stable/stable LPs on Unichain is about $400 per 30 days** across all venues, with $136 of it in the main pool, and there are no incentives. At 0.01%, even capturing 100% of the main pool's current flow ($1.36M/30d) yields ~$1.6k/yr. That is ~1% APR on the existing $160k, and less on new capital unless volume grows.
- Volume/TVL in the satellite pools (88–760× per 30d) is extremely high but tiny in dollars. It is bursty bot/aggregator routing that arbitrages the main pool against the 0.0018%/0.004% pools and Velodrome. The flow stopped once the main pool's price (tick 10) moved above those pools' liquidity (Q3).
- Unichain stable liquidity is about 1/775th of its 2025 incentive peak ($123.9M on 2025-05-01 vs $159.5k now) and has been stuck at ~$160k with ~$25–85k/day of flow since Apr 2026. This looks like a liquidity vacuum: modest capital would dominate the book. The binding constraint is flow, not competition.

### Gaps
- Velodrome CL fees might be dynamic (Velodrome dynamic-fee module). I used `fee()` = 100 pips, so Velodrome fee figures are approximate.
- I did not identify the unverified high-volume caller contracts (0x099b…07c9, 0x9c1a…c855, 0x7290…9768, 0x64e2…de06), which are probably aggregator executors or arbitrage bots.
- Volume for hook pools whose PoolManager Swap amounts are zero (AssetToAsset/VII router pools) is only partly measured, from VII pool swaps (~$6k/30d).
- Curve DEX pools on Unichain were not enumerated: the Curve API does not cover Unichain and I found no factory address.
- 2025 monthly volumes are 3-day samples, not full-month sums.

## Q3. How is liquidity distributed around the peg in the top pools?

### Takeaway
In the main pool (snapshot block 61,169,542, 18:58:21 UTC), price is **tick 10 (1 USDC = 1.00101 USDT0)**, i.e. USDT0 is ~10 bps below USDC. **Every other major USDC/USDT pool on Ethereum, Base, Arbitrum and OP sat at tick 9–12 at the same time** (see Q4), so this is the global USDT discount rather than a Unichain dislocation.
- Concentrated liquidity is centred on the 1.0000 peg (ticks −10…+2), not on the current price. Only **$7.1k (4.4% of TVL) sits within ±1 tick of the current price** and $22.8k (14.3%) within ±10 ticks, against $43.8k (27.4%) within ±10 ticks of 1.0000.
- About 67% of TVL is in wide or full-range positions.
- Depth is asymmetric: **~$5.9k of USDT0 moves price +1 bp but only ~$7.6k moves it +10 bp**; −10 bp (back to peg) needs ~$14.9k of USDC.
- Over 30d the time-weighted tick averaged +3.2, spent 57% of the time within ±2 bps and 97% within ±10 bps, and peaked at +33.

### Cited Findings
- **Main pool state** (StateView 0x86e8631a016f9068c3f085faf484ee3f5fdee8f2 `getSlot0`/`getLiquidity`, block 61,169,542):
  - sqrtPriceX96 79,268,315,456,777,710,726,149,054,668; tick 10; price 1.00101386; protocolFee 0; lpFee 100.
  - Active L 136,161,330,009,421; 766 live positions; TVL 61,587 USDC + 97,928 USDT0.
  - — [StateView on uniscan](https://uniscan.xyz/address/0x86e8631a016f9068c3f085faf484ee3f5fdee8f2); [RPC](https://mainnet.unichain.org)
- **Value by distance** (main pool; USD value of liquidity in each 1-tick bucket at current price):
  - Around current tick 10: ±1 tick $7,093 (4.4%); ±2 $7,683 (4.8%); ±5 $9,128 (5.7%); ±10 $22,839 (14.3%); ±25 $55,187 (34.6%); ±50 $61,000 (38.2%); ±100 $70,181 (44.0%).
  - Around the peg (tick 0): ±1 $6,149 (3.9%); ±2 $11,319 (7.1%); ±5 $32,369 (20.3%); ±10 $43,763 (27.4%); ±25 $54,844 (34.4%).
  - Largest buckets: tick 2 $7.7k, tick 10 $6.8k, tick −5 $5.5k, tick −7 $4.0k, ticks −4 to −1 about $3.4–3.5k each.
  - — on-chain (`data/pos_77ea.json`)
- **Main pool TVL by position width:**

| Width | TVL |
|---|---|
| 1 tick | $17,149 |
| 2–5 ticks | $940 |
| 6–10 ticks | $23,259 |
| 11–50 ticks | $7,046 |
| 51–200 ticks | $3,607 |
| 201–2000 ticks | $51,000 |
| >2000 ticks (incl. full range) | $56,513 |

  - In-range positions hold $119.2k of $159.5k. — on-chain
- **Exact price-impact depth** (USD in, integrating L over sqrtP from the reconstructed position set):

| Pool (tick) | +1 bp | +2 bp | +5 bp | +10 bp | +25 bp | −1 bp | −2 bp | −5 bp | −10 bp | −25 bp |
|---|---|---|---|---|---|---|---|---|---|---|
| Main 0x77ea (10) | $5,927 | $6,190 | $6,824 | $7,616 | $9,688 | $1,168 | $1,489 | $2,297 | $14,856 | $45,634 |
| 0xaf58 0.0018% (9) | $0 | — | — | $4 | — | $276 | — | — | $1,890 | — |
| 0x2c68 0.004% (12) | $0 | — | $1 | — | — | $0 | — | $263 | $1,323 | — |
| 0xc7ee 0.002% (8) | $0 | — | — | — | — | $51 | — | $253 | $789 | — |
| v4 USDC/USDT.e 0x3d4d (16) | $70 | — | — | — | — | $70 | — | — | $702 | — |

  - "+" means price up, i.e. USDT0 sold in. — on-chain (`data/pos_*.json`)
- **Satellite pools** are all out of range on the upside, holding almost only USDT0, with liquidity concentrated around the peg:
  - 0xaf58: 98.5% of TVL within ±10 ticks of 1.0000.
  - 0x2c68: 94.9%.
  - 0xc7ee: 95.7%.
  - v3 USDC/USDT0 0.05% (0xe92c): one $65.7k position over ticks −120…100, in range at tick 13.
  - v3 USDC/USDT.e 0.05% (0x18b2): 78% in a single (0, 30) position, in range at tick 16.
  - — on-chain
- **Main pool price over 30d** (time-weighted from 3,450 Swap events, 2026-09-13 18:32 → 2026-10-13 18:32 UTC):

| tick | −1 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| share of time | 1.0% | 13.2% | 22.9% | 20.0% | 9.7% | 3.3% | 4.3% | 4.8% | 11.4% | 2.3% | 2.6% | 1.6% | 2.8% | 0.1% |

  - Swap-tick range −2…+33. Time-weighted mean +3.24. Share of time with |tick| ≤ 1: 37.1%; ≤ 2: 57.1%; ≤ 5: 74.4%; ≤ 10: 97.1%.
  - Monthly snapshots since 2025-05 show ticks between −4 and +11 (Q2 history table).
  - — on-chain (Blockscout logs `data/v4logs/sw30_77ea.jsonl`)
- **Cross-pool price consistency on Unichain at the snapshot:**

| Pool | tick |
|---|---|
| Main v4 | 10 |
| v4 fee-18 | 9 |
| v4 fee-20 | 8 |
| v4 fee-40 | 12 |
| Velodrome CL | 9 |
| v3 0.01% | 10 |
| v3 0.05% | 13 |
| USDC/USDT.e | 16 (bridged USDT ~16 bps below USDC) |

  - — on-chain

### Inferences
- The "fair" stable price is currently ~1.0010 USDT per USDC everywhere, while the passive liquidity on Unichain is anchored at 1.0000. Most concentrated capital is therefore idle: it was converted entirely to USDT0 when the price drifted up. An LP that recenters on the market price, not the 1.0000 peg, would face almost no competition within ±2 bps.
- The ±1–2 bps band around the current price holds only ~$7k, so a $50–150k inventory placed at ±1–2 bps would become the dominant depth. Q2 shows that fee income at current volume is negligible, though. Depth may attract more aggregator flow, but that is not demonstrated.
- For PegGuard GUARD: deviations of 3–33 bps from 1.0000 here are mostly the global USDT/USDC basis, not a Unichain-local mispricing. The 50 bps breaker was never approached in the 30d window (max +33 bps, briefly).

### Gaps
- I did not compute a time-weighted cross-venue deviation series (Unichain vs. Ethereum/Base minute-by-minute). The "~0 tick" difference is from single-block snapshots across chains (blocks listed in Q4).
- The 30d tick distribution uses post-swap ticks only (piecewise-constant between swaps). The pre-window initial tick was approximated by the first swap's tick.

## Q4. How do the top Unichain stable pools compare to the dominant USDC/USDT pools on Base, Arbitrum, OP Mainnet and Ethereum, and which fee tiers win the volume?

### Takeaway
Elsewhere, USDC/USDT volume is won by **sub-basis-point fees**: Uniswap v4 vanilla pools at **0.0004–0.0008%**, Aerodrome/Velodrome CL at **0.0008–0.0015%**, Fluid DEX, and on Ethereum a **dynamic `StablePairHook` pool charging 0–0.28 bps (volume-weighted ~0.086 bps)**. These pools turn over 170–670× their TVL per 30d. Legacy 0.01% v3 pools keep large TVL but have 11–47× turnover.
- Unichain's main pool is **0.01% (12.5× the dominant 0.0008% tier)**, has $160k TVL and 8.5× turnover. That is roughly 1/2,250 of Ethereum's top-pool 30d volume and 1/250 of Base's Aerodrome CL1 pool.
- All benchmark USDC/USDT pools were at **ticks 9–12** at the snapshot, the same basis as Unichain.

### Cited Findings
**Benchmark snapshot.**
- TVL and 24h volume are from GeckoTerminal token-pool lists, fetched 2026-10-13 ~18:50–19:10 UTC.
- 7d and 30d volume are from GT daily OHLCV (last 7/30 daily candles ending 2026-10-13, so the last day is partial).
- tick, lpFee and hooks are on-chain. Blocks: Ethereum 26,185,534; Base 52,564,417; Arbitrum 514,519,106; OP 158,159,706.
- Fee APR = 30d volume × lpFee / TVL × 365/30, excluding rewards.
- Sources: [GT eth USDC pools](https://api.geckoterminal.com/api/v2/networks/eth/tokens/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48/pools?page=1&sort=h24_volume_usd_liquidity_desc), [GT base](https://api.geckoterminal.com/api/v2/networks/base/tokens/0x833589fcd6edb6e08f4c7c32d4f71b54bda02913/pools?page=1&sort=h24_volume_usd_liquidity_desc), [GT arbitrum](https://api.geckoterminal.com/api/v2/networks/arbitrum/tokens/0xaf88d065e77c8cc2239327c5edb3a432268e5831/pools?page=1&sort=h24_volume_usd_liquidity_desc), [GT optimism](https://api.geckoterminal.com/api/v2/networks/optimism/tokens/0x0b2c639c533813f4aa9d7837caf62653d097ff85/pools?page=1&sort=h24_volume_usd_liquidity_desc). On-chain reads via StateView: [Ethereum 0x7ffe…7227](https://etherscan.io/address/0x7ffe42c4a5deea5b0fec41c94c136cf115597227), [Base 0xa3c0…7a71](https://basescan.org/address/0xa3c0c9b65bad0b08107aa264b0f3db444b867a71), [Arbitrum 0x76fd…9990](https://arbiscan.io/address/0x76fd297e2d437cd7f76d50f01afe6160f86e9990), [OP 0xc18a…cdb](https://optimistic.etherscan.io/address/0xc18a3169788f4f75a170290584eca6395c75ecdb). Addresses are per [Uniswap v4 deployments](https://developers.uniswap.org/contracts/v4/deployments).

| Chain | Pool (id/address prefix) | Venue, fee, hook | tick | TVL | 24h vol | 7d vol | 30d vol | Turn30 | Fee APR |
|---|---|---|---|---|---|---|---|---|---|
| Ethereum | 0x2b21c65d9a7dc692…f634 (created 2026-09-10) | v4 dynamic (0x800000), ts 1, hook **StablePairHook** (proxy 0x0000113dcf4add69999fad8f20f2b63f979bfcc0 → impl 0x5f216d21b1C81346938EDDc1Df7e0111A0F64000) | 10 | $4.55M | $87.3M | $468.3M | $3.057B | 672× | ~7% (if the sampled ~0.086 bp average fee holds) |
| Ethereum | 0x667701e51b4d… | Fluid DEX | — | $43.86M | $156.5M | $584.2M | $2.354B | 54× | n/a |
| Ethereum | 0x0fb0e40cec3b… | v4 **0.0007%**, ts 1, no hook | 10 | $3.33M | $76.2M | $357.8M | $1.723B | 518× | 4.4% |
| Ethereum | 0x395f91b34aa3… | v4 0.0008%, ts 1, no hook | 10 | $3.60M | $36.1M | $136.2M | $609.9M | 169× | 1.6% |
| Ethereum | 0x8aa4e11cbdf3… | v4 0.001%, no hook | 10 | $5.39M | $14.0M | $68.5M | $391.7M | 73× | 0.9% |
| Ethereum | 0x3416cf6c708d… | v3 0.01% | 9 | $33.87M | $14.3M | $74.5M | $372.2M | 11× | 1.3% |
| Ethereum | 0xbebc44782c7d… | Curve 3pool | — | $159.5M | $6.85M | $0.38M | $6.95M | 0.04× | n/a |
| Base | 0xa41bc0affba7… | Aerodrome Slipstream CL1, fee **0.0008%** | 12 | $906k | $10.57M | $64.3M | $342.4M | 378× | 3.7% (+6.69% AERO per DefiLlama apyReward) |
| Base | 0x7681c00520c2… | v4 **0.0005%** | 12 | $274k | $6.07M | $42.2M | $43.1M (new pool) | — | — |
| Base | 0xf13203ddbf2c… | v4 0.0007% | 12 | $226k | $2.90M | $15.6M | $128.1M | 567× | 4.8% |
| Base | 0xfba2c4592d32… | v4 0.0006% | 12 | $43k | $1.52M | $41.4M | $80.5M (14 days) | — | — |
| Base | 0x49fff8ec5449… | v4 0.0004% | 12 | $36k | $1.56M | $5.1M (5 days) | — | — | — |
| Base | 0xd56da2b74ba8… | v3 0.01% | 12 | $206k | $0.81M | — | — | — | — |
| Arbitrum | 0x3c0441b42195… | Fluid DEX | — | $11.65M | $12.28M | $58.7M | $257.9M | 22× | n/a |
| Arbitrum | 0xab05003a63d2… | v4 **0.0008%**, ts 1, no hook | 10 | $546k | $6.83M | $46.6M | $204.3M | 374× | 3.6% |
| Arbitrum | 0xbe3ad6a5669d… | v3 0.01% (USDC/USDT0 0xfd08…cbb9) | 10 | $1.21M | $2.27M | $12.3M | $56.6M | 47× | 5.7% |
| Arbitrum | 0x7f90122bf070… | Curve | — | $631k | $0.41M | $4.18M | $21.8M | 35× | n/a |
| Arbitrum | 0x13fd8faf63c1… | v4 0.0001% + hook 0x4440854b2d02c57a0dc5c58b7a884562d875c0c4 | 10 | $343k | $0.34M | $2.24M | $8.4M | 25× | ~0 |
| OP | 0x84ce89b4f6f6… | Velodrome CL USDC/USDT(bridged 0x94b0…8e58), fee **0.0015%** | 11 | $148k | $2.66M | $16.7M | $64.9M | 440× | 8.0% |
| OP | 0x4da46c6afe73… | Velodrome CL USDT0(0x01bf…1071)/USDT(bridged), 0.01% | 1 | $6.25M | $1.01M | $9.52M | $34.8M | 5.6× | 0.7% |
| OP | 0xf7f575f2c0f6… | Velodrome CL USDT0/USDC, 0.01% | −10 (token0 = USDT0) | $511k | $0.70M | $4.94M | $14.5M | 28× | 3.4% |
| OP | 0xebe9db89947d… | v4 0.0025%, no hook | 11 | $31k | $0.15M | — | — | — | — |
| **Unichain** | **0x77ea9d2be50e…** | **v4 0.01%, ts 1, no hook** | **10** | **$160k** | **$84.6k** | **$409k** | **$1.36M** | **8.5×** | **1.0%** |

- **StablePairHook fee behaviour** (Ethereum, 1,500 blocks 26,184,077–26,185,577): 505 swaps, $25.30M volume.
  - Fee per swap (Swap event `fee` field, pips): 0 on 248 swaps; 15 on 148, 14 on 50, 16 on 13, 17 on 11, and up to 28.
  - The volume-weighted average fee was **0.086 bps**. Ticks ranged 8–12. The same hook also runs the Ethereum USDG/USDC pool 0xeda62d29… (TVL $3.41M, 30d $314.1M).
  - — [Ethereum RPC (publicnode)](https://ethereum-rpc.publicnode.com) logs; hook identification via [Blockscout ETH](https://eth.blockscout.com/address/0x0000113dcf4add69999fad8f20f2b63f979bfcc0)
- **Aggregate scale of stable/stable pools observed in GT lists** (sum of 24h volume and TVL; the Unichain row includes dust pools):

| Chain | Pools | 24h volume | TVL |
|---|---|---|---|
| Ethereum | 29 | $498.1M | $528.4M |
| Base | 26 | $27.0M | $13.5M |
| Arbitrum | 16 | $24.3M | $28.2M |
| OP | 36 | $5.0M | $12.7M |
| Unichain | 47 | $72.7k | $294.8k |

  - — GT (`data/gt_bench_stable_rows.json`)
- **DefiLlama yields cross-check** (24h volume):
  - Ethereum: v4 USDC-USDT "Dynamic fee" TVL $4.86M, 1d volume $94.9M, apyBase 5.85%. v4 "0.00%" tier TVL $3.70M, 1d $61.2M.
  - Base: Aerodrome Slipstream USDC-USDT "CL1 - 0.0008%" TVL $906,920, 1d $10.59M, 7d $65.27M, apyBase 36.36%, apyReward 6.69%. DefiLlama's apyBase is evidently computed on a different basis.
  - Arbitrum: v3 USDC-USDT 0.01% TVL $1.23M, 1d $2.16M, apyBase 6.42%.
  - — [DefiLlama yields](https://yields.llama.fi/pools)
- **Peg level:** all benchmark USDC/USDT pools were at ticks 9–12, i.e. USDT ≈ 9–12 bps below USDC, versus Unichain at tick 10. OP's USDT0/USDT(bridged) pool was at tick 1. DefiLlama's aggregated prices at fetch time were USDC 0.99981 and USDT 0.99926, a 5.5 bp gap. — on-chain; [DefiLlama prices](https://stablecoins.llama.fi/stablecoins?includePrices=true)

### Inferences
- **Fee-tier winners by chain:**
  - Ethereum: v4 dynamic StablePairHook (0–0.28 bp) and v4 0.0007–0.001% pools plus Fluid. v3 0.01% holds the TVL but only ~11× turnover.
  - Base: Aerodrome CL1 at 0.0008% (with AERO emissions) plus v4 0.0004–0.0007%.
  - Arbitrum: Fluid plus v4 0.0008%; v3 0.01% is still relevant at 47×.
  - OP: Velodrome CL at 0.0015%.
  - On mature chains, flow goes to the lowest-fee deep pool, and fee APRs at the winning tiers settle around 1–5% before incentives.
- Unichain's 0.01% tier survives because there is no deeper cheap alternative. Its satellite sub-bp pools are tiny. A sub-bp or dynamic pool with real depth would likely take the flow, but the whole pie is only ~$1.4M/30d in the main pool, ~$5.4M across all venues.
- A peg-anchored hook would mis-specify fair value, because the global USDC/USDT basis is ~10 bps. The Ethereum StablePairHook charges 0 on about half of swaps and ~0.15–0.28 bp on the rest. That pattern looks consistent with a directional fee (cheap when trading toward fair value), but the hook's logic was not read.

### Gaps
- I did not decode StablePairHook's fee logic or reference price; the implementation source was not read. The Arbitrum hook 0x4440…c0c4 is unidentified (Arbitrum Blockscout was behind a Cloudflare challenge).
- I could not resolve v4 pool keys (hooks / tickSpacing) for the Base v4 pools (Base Blockscout returned 403/429). Base lpFee values (4–7 pips) are from StateView `getSlot0` only; no hooks were confirmed.
- GT 7d/30d OHLCV was missing for some pools (rate limits) and was partial for recently created pools; those cells are blank. The DefiLlama yields "OP Mainnet" listing showed no Uniswap/Velodrome USDC-USDT pools in its top results.

## Q5. Who are the LPs in the top Unichain stable pools: how many, how concentrated, any professional managers or JIT?

### Takeaway
The main pool has **766 live positions from 461 distinct owners**, nearly all EOAs holding PositionManager NFTs. Concentration is moderate (**HHI 1,094**):
- The top owner (EOA 0xc9d2…4449) holds **29.2%** in a single ±3% range (ticks −296…304).
- The top 5 hold 55.0% and the top 10 68.6%.

Professional ALM activity exists but with trivial capital: 4–5 Gamma-style `MultiPositionManager` contracts generate ~95% of the 30d `ModifyLiquidity` events (rebalancing 1-tick ranges) while holding under $600 in total. JIT-like same-block add/remove peaked in Aug and Nov 2025 (1,461 and 909 instances) and is now low (116 in 30d). The satellite pools are owned by 10–17 EOAs each, and the top v3 pool by a single EOA.

### Cited Findings
- **Main pool position reconstruction** (138,901 `ModifyLiquidity` events from pool creation to block ~61.17M; blocks 0–24,136,967 via Blockscout, 24,136,967–61,169,234 via RPC):
  - 68,922 adds, 60,036 removes, the rest zero-delta fee pokes.
  - 12,312 distinct position keys ever (sender, tickLower, tickUpper, salt); 766 live.
  - 526 live positions belong to PositionManager 0x4529a01c7a0410167c5740c487a8de60232617bf. Owners came from `ownerOf(salt = tokenId)`.
  - — on-chain ([PositionManager](https://uniscan.xyz/address/0x4529a01c7a0410167c5740c487a8de60232617bf), `data/pos_77ea.json`)
- **Top owners** (USD at current price):

| Rank | Owner | Value | Share |
|---|---|---|---|
| 1 | 0xc9d270d7baa126fc84a81ec8b15f2cb032954449 (EOA) | $46,656 | 29.2% |
| 2 | 0xba6741f9…1e3b | $11,997 | 7.5% |
| 3 | 0xbcff86c5…a451 | $11,997 | 7.5% |
| 4 | 0x6c767c85…0f2a | $10,184 | 6.4% |
| 5 | 0x4488a906…6451 | $7,068 | 4.4% |
| 6 | 0xeb41232c…7e9e (EIP-7702-delegated EOA, 23-byte code) | $6,517 | 4.1% |
| 7 | 0x5bdb9db2…3a44 | $5,217 | 3.3% |

  - 11 of the top 12 have codesize 0 (plain EOAs); the exception is the 7702-delegated 0xeb41…7e9e. — on-chain
- **Recent LP activity** (last 30d: 3,130 `ModifyLiquidity` events in 383 txs, 422 of them zero-delta fee collects):

| Sender | Events | Live capital |
|---|---|---|
| 0xe44536772519f158622d949afd8a438fd1fd3cbb | 1,218 | ~$5 |
| 0x3f039519c5a74a3af1487d8112ffa953a88aee4f | 818 | ~$527 |
| 0xa0bf9b2cd5f0d9eb0c9f2d5355b4743a384dbfa6 | 482 | ~$5 |
| 0xdbda40512e00192cc56825b339795b9a7e1afd3c | 235 | ~$3 |
| 0x5e5ff3654934ebc1fae01d3531028564ba4a8e9b | 220 | ~$51 |
| PositionManager NFTs | 157 | — |

  - Blockscout labels 0xe445…, 0x3f03…, 0xa0bf… and 0x5e5f… as verified `MultiPositionManager`. Merkl lists 0xE445…3cBB and 0x3f03…EE4F as "Gamma USDC-USD₮0 vault" opportunities.
  - Widths of the touched positions: 1 tick (2,127 events), 10 ticks (379), 2–4 ticks.
  - Other contract senders hold 19–22 one-tick ladder positions each (e.g. 0x33313ce5…, 0x2da71d12…, 0x5b7d3bf0…) worth ~$1–3 in total.
  - — [Blockscout MultiPositionManager 0x3f03…](https://unichain.blockscout.com/address/0x3f039519c5a74a3af1487d8112ffa953a88aee4f); [Merkl opportunities](https://api.merkl.xyz/v4/opportunities?chainId=130&items=100&page=1)
- **Most active NFT positions in 30d:** tokenId 159,887 (23 events, owner 0xb1db513ac47e476944f392d8e047e3a0a5a5ff9c), 2,486,675 (owner 0xcd6b…9e37) and 2,482,707 (owner 0xeb41…7e9e). — on-chain
- **JIT-like activity** (position key added and fully removed within the same block; may include ALM rebalance churn): 4,505 instances all-time.

| Month | ML events | JIT-like |
|---|---|---|
| 2025-04 | 17,320 | 36 |
| 2025-05 | 7,905 | 26 |
| 2025-06 | 7,768 | 1 |
| 2025-07 | 18,990 | 18 |
| 2025-08 | 29,832 | 1,461 |
| 2025-09 | 2,675 | 47 |
| 2025-10 | 3,548 | 112 |
| 2025-11 | 12,572 | 909 |
| 2025-12 | 8,438 | 742 |
| 2026-01 | 6,808 | 452 |
| 2026-02 | 3,085 | 147 |
| 2026-03 | 6,397 | 146 |
| 2026-04 | 2,627 | 30 |
| 2026-05 | 679 | 4 |
| 2026-06 | 1,821 | 38 |
| 2026-07 | 571 | 3 |
| 2026-08 | 2,637 | 131 |
| 2026-09 | 4,204 | 179 |
| 2026-10 (1–13) | 1,024 | 23 |

  - Last 30d: 116 JIT-like instances. — on-chain
- **Satellite pools** (all live positions are PositionManager NFTs; no JIT-like events):

| Pool | Live positions | Owners | Top owner | HHI | 30d ML events |
|---|---|---|---|---|---|
| v4 0xaf58 (0.0018%) | 24 | 17 | 0x7d12b24051901a749f53936b1d1e50de19ce2966, 39.2% | 2,447 | 23 |
| v4 0x2c68 (0.004%) | 12 | 10 | 0x548b926141e6f53c3db38ec5667505183a34abe2, 75.9% | 6,316 | 0 |
| v4 0xc7ee (0.002%) | 15 | 15 | 0xd8cd9c195b5f1e13d04861fdcdcd1cf81a36405a, 42.9% | 3,180 | 6 |
| v4 USDC/USDT.e 0x3d4d | 110 | 100 | 0x0e7755e5a5376887c4776ae8beaecfb7bbc67f83, 76.3% | 5,945 | 6 |
| v4 USDC/DAI 0x3188 | 85 | 69 | 0x2f7508e0…0993, 94.6% | — | — |
| v4 USDC/vyUSD 0x8273 | — | 2 | 0x69472e85…2bdd, 99.8% | — | — |

  - The same EOA 0xd8cd…405a also holds 23.6% of 0x2c68. — on-chain (`data/pos_*.json`)
- **v3 pools** (NPM 0x943e6e07a7e8e791dafc44083e54041d743c46e9; tokenIds recovered from `IncreaseLiquidity` logs in Mint txs, then `positions()`/`ownerOf()`):
  - USDC/USDT0 0.05% (0xe92c): 102 Mints, 67 tokenIds, 36 live positions, but **one owner (0x65d5c417252bbfd806938a4c8321c92be24f7275) holds 100% ($65,714)** in ticks −120…100. There were also 29 Mints by non-NPM contract 0x0393c31f…29e8.
  - USDC/USDT.e 0.05% (0x18b2): 946 Mints, 534 tokenIds, 54 live positions, 50 owners. The top owner, 0xf56ba84c6d9a3b43254b5cd48e9b43383bf2d139, holds 79.9% ($19,969) in ticks 0…30.
  - — on-chain ([NPM](https://uniscan.xyz/address/0x943e6e07a7e8e791dafc44083e54041d743c46e9))

### Inferences
- The LP base is retail-like and mostly passive. Many of the 461 owners are probably former incentive farmers who left small or out-of-range positions after the UNI campaigns ended in Sep 2025.
- The only active managers are Gamma MultiPositionManagers that rebalance 1-tick ranges near the current price but hold under $600. A professional MM entering with $50k+ at ±1–2 bps around fair value would face effectively no active competitor.
- JIT is not currently a meaningful threat at this flow size (largest 30d swap $18.3k, median $127). It spiked in Aug and Nov 2025, when flow and TVL were higher, so it could return if volume returns.

### Gaps
- I did not link LP owners to known entities (CEX or market-maker labels). Blockscout lists no names for the top EOAs.
- I did not compute per-LP fee earnings or markouts. The `ModifyLiquidity` history is in `data/v4logs/ml_77ea*.jsonl` if another workstream needs it.
- The JIT heuristic (same-block add and full removal of the same key) does not separate true JIT from ALM rebalancing. A precise JIT classification would need ordering against Swap events within each block.
