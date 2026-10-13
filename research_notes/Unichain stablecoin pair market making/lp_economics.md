# Economics of stablecoin-pair market making / LP on AMMs (theory, cross-chain empirics, competition, depeg tail risk, mechanism design) — for a PegGuard stable-pair strategy on Unichain

Research date: 2026-10-13. Conventions: 1 bp = 0.01%; "fee APR" means trading-fee income / pool TVL annualized (pool-level, not per in-range position) unless stated. **[THEORY]** = model result; **[MEASURED]** = observed data; **[COMPUTED]** = my own calculation from cited data (scripts and raw pulls in `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/lp_economics/`: `theory.py`, `vol.py`, `stable_pools2.py`, `charts.py`; data in `data/`).

## 1. Theory: LVR, fees, block time, range width, and optimal fee for pegged pairs

### Takeaway
For a pegged pair, fee-free LVR is negligible in full range (about 0.02-0.09 bp/yr) but scales as σ²/(4δ) under concentration. That is about 4%/yr of in-range capital for a ±1 bp range at σ ≈ 2 bp/day. With any fee much larger than per-block σ (Unichain's 1 s blocks give per-block σ of about 0.005-0.01 bp), arbitrageurs pay almost all of LVR back to LPs as fees, and the LP's net arb loss (ARB ≈ LVR × P_trade) drops to roughly 0.01-0.2%/yr of in-range capital. Diffusive adverse selection is therefore not what decides stable-LP profitability. What decides it is fee share versus competitors, opportunity cost of capital, gas/rebalancing costs, and jump (depeg) risk, none of which the diffusion model covers.

### Cited Findings
- **[THEORY] LVR baseline.** For a constant-product (full-range) AMM, instantaneous LVR = σ²/8 of pool value per unit time. Worked example: σ = 5%/day gives ≈ 3.125 bp/day of pool value. LVR is a function of realized variance, and delta-hedged LP P&L ≈ fees − LVR — [Milionis, Moallemi, Roughgarden, Zhang, "Automated Market Making and Loss-Versus-Rebalancing", arXiv 2208.06046](https://arxiv.org/abs/2208.06046)
- **[THEORY] Fees + discrete blocks.** The probability that a block contains an arbitrage trade is P_trade = 1/(1+η), with η = γ/(σ√(Δt/2)). This is the fee expressed in units of the typical price move over half the inter-block time. When η is large (high fee, low vol or fast blocks), P_trade ≈ 1/η. In the fast-block regime, ARB ≈ LVR × P_trade and FEE (fees paid by arbs to LPs) ≈ LVR × (1 − P_trade), so ARB + FEE ≈ LVR. "Introducing fees simply changes how LVR is split and who earns it." Once fees are positive, arb profits scale with √(block time) and go to zero as blocks get faster. Table 1 at σ = 5%/day: P_trade = 80.7% at 12 s/1 bp, 63.0% at 2 s/1 bp, 5.1% at 50 ms/5 bp — [Milionis, Moallemi, Roughgarden, "Automated Market Making and Arbitrage Profits in the Presence of Fees", arXiv 2305.14604 (rev. Jul 2025)](https://arxiv.org/abs/2305.14604); [Roughgarden thread summary](https://www.timroughgarden.org/tldr/lvrfees.pdf)
- **[THEORY] Gas.** A fixed gas cost acts as an extra no-trade band. The paper's Uniswap calibration uses gas δ ≈ 9 bp on Ethereum L1. Lower gas reduces LP losses in the fast-block regime — [arXiv 2305.14604](https://arxiv.org/abs/2305.14604)
- **[THEORY] Deterministic (fixed-interval) blocks.** Per-block, per-unit-liquidity expected LVR ≈ σ_b² / (2 + 1.7164·γ/σ_b), where σ_b is intra-block volatility and γ the AMM spread. The authors call this "quasi-exact" in Monte Carlo. Among block-time laws, only constant block spacing attains the asymptotically minimal LVR. This is relevant to Unichain's fixed 1 s blocks — [Nezlobin & Tassy, "LVR under Deterministic and Generalized Block-Times", arXiv 2505.05113 (May 2025)](https://arxiv.org/abs/2505.05113)
- **[THEORY + calibration] Optimal static fee.** Under normal conditions the profit-maximizing AMM fee is "competitive with the trading cost on the CEX and remarkably stable". The TVL-maximizing fee under competitive LP entry is typically slightly below the CEX cost. In very high volatility, a high fee protects LPs. "A threshold-type dynamic fee schedule is robust to market conditions and improves LP outcomes" — [Campbell, Bergault, Milionis, Nutz, "Optimal Fees for Liquidity Provision in AMMs", arXiv 2508.08152 v2 (2 Oct 2026)](https://arxiv.org/abs/2508.08152)
- **[THEORY] Dynamic fees.** A separate optimal-dynamic-fee model finds two regimes: high fees to deter arbitrageurs, and low fees to attract noise traders — [arXiv 2506.02869](https://arxiv.org/html/2506.02869) (summary from search result; full text not read)
- **[MEASURED, older] Stable-pair position returns on Uniswap v3.** In DAI-USDC (0.01% and 0.05%) positions, daily returns "are never significantly negative" because of negligible IL. Mean daily returns for the narrowest positions reach only about 0.3% in the most extreme cases. The DAI-USDC 0.01% pool "appears to be in the hands of large liquidity providers", with a very small number of active positions and single positions worth more than $100M (data 2021-2022) — [Heimbach, Schertenleib, Wattenhofer, "Risks and Returns of Uniswap V3 LPs", arXiv 2205.08904](https://arxiv.org/abs/2205.08904)
- **[MEASURED] Block time and LP losses (volatile pairs).** Losses to arbitrageurs exceed LP fees in many of the largest Uniswap pools. Uniswap v2 pools were more profitable for passive LPs than v3. Moving from 12 s to 100 ms blocks cuts arbitrage losses by 20-70% depending on the pair. The study does not cover stable-stable pools — [Fritsch & Canidio, "Measuring Arbitrage Losses and Profitability of AMM Liquidity", arXiv 2404.05803 (2024)](https://arxiv.org/abs/2404.05803)
- **[MEASURED] Realistic σ for stable pairs (my pull of Binance closes, 2025-10-13 → 2026-10-13)** — [Binance public market-data API](https://data-api.binance.vision/api/v3/klines?symbol=USDCUSDT&interval=1h&limit=5):
  - USDC/USDT: daily-sampled σ ≈ **2.15 bp/day** (≈ 41 bp/yr annualized). 1 h-sampled ≈ 3.57 bp/day (robust MAD 2.18). Over the last 30 days: 1 h-sampled 2.54, 5 m-sampled 3.00, 1 m-sampled 4.45 bp/day. The rise at higher sampling frequency is microstructure noise and bid/ask bounce. Hourly closes stayed in 0.99900-1.00210 over the year, but wicks reached 1.0219. In the last 30 days, 42% of 1-minute returns were exactly zero.
  - USDe/USDT: daily-sampled σ ≈ 2.14 bp/day, hourly MAD ≈ 0 (price usually pinned), with fat tails: hourly wick range 0.9202-1.0655.
  - FDUSD/USDT: daily-sampled σ ≈ 4.73 bp/day; hourly 7.2 bp/day; hourly wick high 1.1932 (2026-02-24).
  - USDC/DAI and USDC/USDe on-chain σ were not measured. Binance does not list DAI.

### Inferences
- **[COMPUTED] Fee-free LVR as % of in-range position value per year** (concentrated-liquidity approximation LVR/V ≈ σ²/(4δ) for a symmetric log half-width δ; full range = σ²/8):

  | σ (bp/day) | full range | ±1 bp | ±2 bp | ±5 bp | ±10 bp | ±50 bp |
  |---|---|---|---|---|---|---|
  | 2.15 (daily-sampled USDC/USDT) | 0.0002 bp/yr ≈ 0 | 4.22% | 2.11% | 0.84% | 0.42% | 0.08% |
  | 3.0 (5-min sampled) | ≈ 0 | 8.21% | 4.11% | 1.64% | 0.82% | 0.16% |
  | 4.45 (1-min sampled, noise-inflated) | ≈ 0 | 18.1% | 9.0% | 3.6% | 1.8% | 0.36% |

  Concentration multiplies full-range LVR by about 2/δ: ≈20,000× for ±1 bp and ≈2,000× for ±10 bp.
- **[COMPUTED] P_trade (share of blocks with a profitable arb)** at σ = 2.15 bp/day, for fees of 0.05 / 0.1 / 0.5 / 1 / 5 bp:

  | Block time | 0.05 bp | 0.1 bp | 0.5 bp | 1 bp | 5 bp |
  |---|---|---|---|---|---|
  | Ethereum 12 s | 26% | 15% | 3.5% | 1.8% | 0.4% |
  | Base/OP 2 s | 12.8% | 6.8% | 1.4% | 0.7% | 0.15% |
  | Unichain 1 s | 9.4% | 4.9% | 1.0% | 0.5% | 0.1% |
  | 0.2 s (Flashblock-like) | 4.4% | 2.3% | 0.5% | 0.2% | 0.05% |
- **[COMPUTED] Net arb loss ARB = LVR × P_trade on Unichain (1 s)** for a ±1 bp range: 0.21%/yr (0.1 bp fee), 0.04%/yr (0.5 bp), 0.02%/yr (1 bp) at σ = 2.15 bp/day. With the noise-inflated σ = 4.45 bp/day: 1.75% / 0.38% / 0.19%/yr. For ±5 bp ranges, divide by 5.
- **[COMPUTED] Model-implied arb fee income FEE ≈ LVR × (1 − P_trade)** is about 4%/yr of in-range capital for a ±1 bp range at σ = 2.15 bp/day. Two caveats apply. (a) This assumes a GBM-like efficient price; stablecoin "σ" at high frequency is mostly venue noise around $1. (b) The income is shared by in-range liquidity share and contested by JIT/pro LPs. Treat it as an upper bound on arb-driven fee income, not a forecast.
- The PegGuard measurement fits this theory. Stable cross-venue deviations of 0.000-0.35 bp are smaller than any fee ≥ 0.5 bp, so η is large, P_trade is under about 1%, and there is essentially no "directional fuel" to tax. That is why a directional premium on stables captures roughly nothing (0.6% AMM basket / 6.3% AMM+CEX in PegGuard's own measurement).
- **Optimal fee tier for low-vol pairs.** The theory (Campbell et al.) says to set the fee at or slightly below the competing venue's all-in cost. For USDC/USDT the competing "venue" is other AMM pools and RFQ at ~0.05-1 bp, not Binance's 10 bp taker fee. The observed migration to 0.05-0.1 bp v4 pools (Section 2) is the market finding that price. At a 0.1 bp fee on a 1 s chain, LVR leakage is already small (P_trade ≈ 5%). Going lower mainly trades fee revenue for volume share.
- Range width is a share-vs-risk choice, not an LVR choice. Narrowing from ±10 bp to ±1 bp multiplies fee share per dollar about 10× (when in range) and multiplies LVR the same way. With LVR mostly refunded as fees on fast chains, narrow ranges are rational for active managers. The binding costs become re-centering gas, out-of-range time, and depeg jumps.

### Gaps
- No published LVR or markout measurement specifically for USDC/USDT, USDC/DAI or USDC/USDe pools was found. Fritsch & Canidio and Milionis et al. calibrate on volatile pairs.
- The Nezlobin "directional fee" proposal (primary source) was not located. Only the Nezlobin-Tassy LVR paper was found.
- The GBM assumption is a poor fit for pegged assets, which are mean-reverting with discrete jumps. I found no paper with a closed-form LVR for a mean-reverting peg plus jump process.

## 2. Empirics: realized LP returns, turnover, fee APR by chain, venue and fee tier

### Takeaway
As of 2026-10-13, stable-stable volume has moved to ultra-low-fee venues. These are Uniswap v4 pools at about 0.05-0.1 bp (some with hooks), Fluid DEX (fee ≈ 0.07-0.2 bp plus lending yield), and Aerodrome Slipstream CL1 on Base. Those pools turn over 4-20× TVL per day, but pool-level fee APRs are only about 0.5-6%. The old Uniswap v3 0.01% USDC/USDT pool on Ethereum turns over only about 0.3×/day for about 1.3-2.2% APR. These yields are at or below the risk-free-ish stablecoin lending alternatives (Aave USDC 2.5-4.4%, sUSDS 3.8%, sUSDe 4.9%). So passive stable LPing is roughly breakeven-to-negative versus opportunity cost unless the LP has above-average fee share (tight active ranges), stacks lending yield, or receives incentives. Unichain has essentially no stable-stable AMM liquidity or volume today.

### Cited Findings
- **[MEASURED] Pool snapshot (2026-10-13).** Source: [DefiLlama yields API `/pools`](https://yields.llama.fi/pools) (fields tvlUsd, volumeUsd1d/7d, apyBase). Implied fee = apyBase × TVL / 365 / 1-day volume; it is computed, so treat it as approximate:

  | Chain / venue / pool | TVL $M | 1d vol $M | 7d vol $M | turnover/day (7d avg) | fee APR 1d % | fee APR 30d mean % | implied fee bp |
  |---|---|---|---|---|---|---|---|
  | Ethereum / Fluid DEX USDC/USDT | 43.91 | 206.57 | 633.2 | 2.06x | 1.20 | 0.47 | 0.07 |
  | Ethereum / Uniswap v3 USDC/USDT 0.01% | 33.88 | 13.29 | 74.1 | 0.31x | 1.43 | 1.27 | 1.00 |
  | Ethereum / PancakeSwap v3 USDC/USDT 0.01% | 17.60 | 6.67 | 9.7 | 0.08x | 1.38 | 0.07 | 1.00 |
  | Arbitrum / Fluid DEX USDC/USDT0 | 11.65 | 12.05 | 68.7 | 0.84x | 0.76 | 0.44 | 0.20 |
  | Ethereum / Uniswap v4 USDC/USDT "0.00%" (b) | 6.49 | 2.08 | 69.2 | 1.52x | 0.14 | 0.43 | 0.12 |
  | Ethereum / Uniswap v4 USDC/USDT dynamic-fee hook (created 2026-09-10) | 4.86 | 94.88 | 462.9 | 13.61x | 5.85 | 3.17 | 0.08 |
  | Ethereum / Uniswap v4 USDC/USDT "0.00%" (c) | 4.03 | 30.67 | 120.3 | 4.26x | 2.78 | 1.60 | 0.10 |
  | Ethereum / Uniswap v4 USDC/USDT "0.00%" (a) | 3.70 | 61.16 | 330.8 | 12.78x | 5.43 | 3.68 | 0.09 |
  | Ethereum / Uniswap v3 USDe/USDC 0.01% | 2.42 | 0.51 | 11.7 | 0.69x | 0.76 | 3.13 | 1.00 |
  | Ethereum / Uniswap v4 USDe/USDC "0.00%" | 2.15 | 15.37 | 90.9 | 6.04x | 8.09 | 8.65 | 0.31 |
  | Arbitrum / Uniswap v3 USDC/USDT 0.01% | 1.23 | 2.16 | 12.2 | 1.42x | 6.42 | 5.67 | 1.00 |
  | Polygon / Uniswap v3 USDC/USDT 0.01% | 1.18 | 1.10 | 9.1 | 1.09x | 3.38 | 7.04 | 1.00 |
  | Base / Aerodrome Slipstream CL1 USDC/USDT | 0.91 | 10.59 | 65.3 | 10.28x | 36.36 | 35.83 | 0.85 |
  | BSC / Uniswap v4 USDT/USDC "0.00%" | 0.41 | 8.20 | n/a | n/a | 2.21 | 3.51 | 0.03 |
  | BSC / Uniswap v3 USDT/USDC 0.01% | 0.33 | 0.24 | 0.9 | 0.40x | 2.67 | 1.84 | 1.00 |
  | Base / Uniswap v3 USDC/USDT 0.01% | 0.21 | 0.82 | 2.1 | 1.46x | 14.45 | 4.40 | 1.00 |

  Notes on the table. DefiLlama prints v4 sub-bp tiers as "0.00%"; the implied fees are 0.03-0.12 bp. DefiLlama labels the Aerodrome pool "0.0008%", GeckoTerminal labels it 0.01%, and the implied fee is about 0.85 bp, so the sources conflict. Fluid's apyBase covers swap fees only; Fluid LPs also earn lending yield on smart collateral.
- **[MEASURED] Longer averages** from [DefiLlama `/chart/{pool}` history](https://yields.llama.fi/chart/e737d721-f45c-40f0-9793-9f56261862b9), mean apyBase over windows ending 2026-10-13:

  | Pool | 30d | 90d | 365d |
  |---|---|---|---|
  | Ethereum Uniswap v3 USDC/USDT 0.01% (TVL ≈ $28-35M) | 1.26% | 1.22% | 2.24% |
  | Ethereum Fluid USDC/USDT | 0.48% | 0.52% | 0.60% |
  | Arbitrum Fluid USDC/USDT0 | 0.45% | 0.45% | 0.42% |
  | Arbitrum Uniswap v3 0.01% | 4.42% | 4.59% | 5.06% |
  | Base Aerodrome CL1 USDC/USDT (TVL ≈ $1-1.7M) | 28.9% | 18.1% | 12.6% (+≈2.5% AERO rewards) |
  | Ethereum PancakeSwap v3 0.01% | 0.10% | 0.08% | 0.18% |
  | Ethereum Uniswap v4 USDC/USDT 0.1 bp pool (a) | 3.72% | 3.43% | median 4.16% (mean distorted by outliers) |
  | Ethereum v4 USDe/USDC (since 2026-07-18) | 7.35% | 11.37% | n/a |
- **[MEASURED] GeckoTerminal cross-check (2026-10-13)** — [GeckoTerminal API search](https://api.geckoterminal.com/api/v2/search/pools?query=USDC%20USDT&network=eth):
  - Ethereum: Curve 3pool TVL $159.7M on $1.40M/24h (0.01×/day turnover); Fluid USDC/USDT $44.0M TVL on $156.1M/24h; Uniswap v3 0.01% $33.9M on $13.5M; Uniswap v4 USDC/USDT 0.001% $5.4M on $13.6M; Uniswap v4 USDC/USDT hook pool (created 2026-09-10) $4.5M on $84.2M (18.6×).
  - Base: Uniswap v4 USDT/USDC $0.27M on $6.07M (22×); Aerodrome CL $0.91M on $10.6M.
  - Arbitrum: Uniswap v4 $0.54M on $6.86M (12.6×); Fluid $11.6M on $12.3M.
  - OP: Velodrome Slipstream 0.01% $0.15M on $2.67M (18×).
- **[MEASURED] Unichain (2026-10-13).** GeckoTerminal search shows only USDC/USDT pools of ≤$0.03M TVL with roughly zero volume: v3/v4 at 0.05% and 0.01%, created Feb 2025. Searching "USDT0" on Unichain returns only a dust USDT0/WETH v2 pool. The largest stable-stable pool found is USDC/USD0 0.01% v4 with $0.15M TVL and $0.07M/24h. Unichain's top pool by volume is USDC/HYPE 0.3% v3 at $8.6M/24h. DefiLlama yields lists no Unichain DEX stable pools; it shows only lending (Euler, Morpho, Sky sUSDS 3.8%) — [GeckoTerminal Unichain top pools API](https://api.geckoterminal.com/api/v2/networks/unichain/pools?page=1&sort=h24_volume_usd_desc); [GeckoTerminal Unichain USDC/USDT 0.05% pool page](https://www.geckoterminal.com/unichain/pools/0x3d4d39a2ec28d80efa72679e47b8d4621caeecc15af8f21be97db234657d5fa7) (an earlier snapshot of that page showed $126.84/24h volume across 2 transactions).
- **[MEASURED] Stable-to-stable fee compression on v4.** Uniswap v4 carried $11-14B/month of stable-to-stable swaps versus $1-2B on v3, and stable-to-stable was about 45-53% of v4's total volume. "Uniswap v4 fees on major stable pairs: 0.0005% to 0.0008%" (article 10 Oct 2026, Dune source) — [CryptoBriefing](https://cryptobriefing.com/uniswap-v4-v3-stablecoin-dex-volume/)
- **[MEASURED] Stablecoin DEX volume by venue.** $161.4B over 30 days across 35 venues: Uniswap v4 25.7%, v3 21.5% (47.2% combined), PancakeSwap 8.7%, BisonFi 6.0%, Aerodrome 5.3%, Orca 4.5%, Tessera V 4.0%, Hyperliquid Spot 3.7%, Fluid 3.6%, Meteora 2.7% (Token Terminal, shared 10 Oct 2026). This metric appears to count any swap involving a stablecoin, not only stable-stable — [CoinGabbar summary of Token Terminal data](https://www.coingabbar.com/en/stablecoin-dex-volume-uniswap-30-days). It conflicts with an earlier DL News 2025 claim that Fluid passed Uniswap on stablecoin volume on Ethereum/Base/Arbitrum/Polygon with 55% share ([cited via Eco](https://eco.com/support/en/articles/11788679-best-stablecoin-swap-platforms-2026)) and a commentator's figure of about 31% ([X post](https://x.com/hilmarxo/status/1966099322631589963)). The definitions and periods differ.
- **[MEASURED, backtest] Active LP on the Ethereum v3 USDC/USDT 0.01% pool, 1-30 Sep 2024.** Average TVL $35M, volume $595.1M (≈0.57×/day), pool fees $59.5k (≈2.0% APR). A $1M active LP that re-allocates its range every τ epochs (uniform vs ML allocation) earned $3.5k-3.7k in fees with τ = 2, against $5.9k in gas costs (430k gas to mint, 215k gas to burn, 20 gwei). With τ = 5 it earned $1.6-1.9k against $1.7k costs; with τ = 10, $0.9-1.1k against $0.7k. Gas roughly equals or exceeds fees for active management on L1 — [Urusov et al., "Dynamic Liquidity Provision in Decentralized Markets", arXiv 2505.15338 (Table 2)](https://arxiv.org/abs/2505.15338)
- **[MEASURED, older] Uniswap v3 stable fee tiers.**
  - DAI/USDC 0.01% earned about 0.35% APR from one day of fees (≈2022), and one position in USDT/USDC 0.01% supplied about $100M — [CrocSwap, "Stablecoins on Uniswap V3"](https://crocswap.medium.com/stablecoins-on-uniswap-v3-25b88ba36bd3) (search snippet; page returned 403).
  - After the 1 bp tier launched (Nov 2021), almost all stable-stable TVL and volume moved from 0.05% to 0.01%, and median collected fees were about 0.005% of deposits — [Lambert, "Designing a constant volatility AMM"](https://lambert-guillaume.medium.com/designing-a-constant-volatility-amm-e167278b5d61) (search snippet; page 403).
  - The 0.01% DAI/USDC tier has fewer LPs but higher average wallet liquidity — [Keyrock](https://keyrock.com/liquidity-providers-on-uniswap-v3-2/).
- **[MEASURED, context] The IL studies everyone quotes exclude stables.** The Topaz Blue/Bancor study (5 May-20 Sep 2021, 17 pools, $260M IL against $199M fees, 49.5% of LPs negative) excluded stablecoin pairs such as USDC/DAI — [CryptoSlate](https://cryptoslate.com/new-report-shows-50-of-uniswap-v3-liquidity-providers-are-losing-money/)
- **[MEASURED] Opportunity cost (2026-10-13)**, from [DefiLlama yields](https://yields.llama.fi/pools):
  - Aave v3 USDC supply: Ethereum 3.68% (30d mean 4.32%), Arbitrum 2.50% (3.14%), Base 4.40% (3.90%).
  - Aave v3 USDT supply, Ethereum: 3.17% (3.86%).
  - Sky sUSDS: 3.8%.
  - Ethena sUSDe: 4.87%.

### Inferences
- **Volume follows the lowest all-in price.** Pools charging 0.05-0.1 bp turn over 10-20×/day. The 1 bp v3 pool turns over 0.3×/day and the 1 bp PancakeSwap pool 0.08×/day; these keep TVL mostly from inertia or incentives. Curve 3pool ($160M) is now almost purely parked capital (0.01×/day).
- **Pool-level APR understates pro APR.** DefiLlama's TVL includes out-of-range and idle capital, so in-range pro LPs earn a multiple of the pool-level figure. A pro holding 30-60% of in-range liquidity in a 0.1 bp pool turning 15×/day could plausibly clear 5-10% gross. The pool-level 3-6% is the best available upper bound for a passive or new entrant.
- **Small pools on L2s show high fee APR because TVL is tiny.** Aerodrome CL1 shows 12-36% on $1M; Arbitrum v3 0.01% shows 4-6% on $1.2M. Capacity is limited: adding $5-10M would dilute APR roughly in proportion unless volume is elastic to depth.
- **Fluid's "low" fee APR (≈0.5%) is paired with lending yield** on the same capital through smart collateral/debt, which is why it wins volume while posting tiny fee APR. A rehypothecating design competes against "fee APR + about 3-4% lending".
- **Unichain is greenfield for stable-stable.** There is no incumbent pool to compete with, but there is also no organic flow; any volume would depend on aggregator routing (UniswapX, Uniswap routing API) and cross-chain USDC/USDT0 demand.

### Gaps
- Per-LP realized returns and markouts for v4 sub-bp stable pools, Fluid, Aerodrome CL1 and PancakeSwap Infinity on BSC were not found. PancakeSwap's BSC USDT/USDC pools were not captured (GeckoTerminal rate-limited; DefiLlama coverage thin). OP/Base coverage on DefiLlama looks incomplete.
- I could not identify which hook the high-volume Ethereum v4 USDC/USDT "dynamic fee (hook)" pool uses (created 2026-09-10; GeckoTerminal address prefix 0x2b21c65d9a7d).
- No Unichain-specific stable volume history was found. Today's near-zero might reflect where liquidity sits rather than a lack of demand.

## 3. Competition: professional LPs, JIT, fee-tier migration, and aggregator/RFQ routing

### Takeaway
Stable pools are dominated by a few large, professionally managed positions in tight ranges, with fee tiers that keep migrating downward (1 bp → 0.1 bp → 0.05 bp). Measured JIT is a small share of total fee revenue but can cut passive LP fee income by up to about 40%. RFQ/intents (UniswapX, 1inch Fusion) are concentrated in 2-3 market makers. A new passive entrant should expect a small fee share, roughly proportional to in-range depth relative to the pros and only while flow is routed to it. Fee income on stables is a "rent for being the deepest quote at the lowest fee" business.

### Cited Findings
- **[MEASURED] JIT on Ethereum (20 months, 2021-2023).** 36,671 JIT attacks generated 7,498 ETH in profit. Attackers supplied liquidity 269× the swap volume on average, the average ROI was only 0.007%, and existing LPs' shares were diluted by about 85% on attacked swaps — [Xiong et al., "Demystifying JIT Liquidity Attacks on Uniswap V3", IACR ePrint 2023/973](https://eprint.iacr.org/2023/973)
- **[MEASURED] JIT on the USDC/WETH 0.05% pool, Jan-Jun 2024** (1,013,147 transactions; 6,829 JIT swaps). JIT LPs "account for a small share of total fee revenue", and 93.7% of JIT revenue comes from price impact rather than from passive LPs' fees. Optimized JIT could reduce passive LP fee income by up to 40% — [Trotti et al., "Strategic Analysis of JIT Liquidity Provision in CLMMs", arXiv 2509.16157 (v2 Jun 2026)](https://arxiv.org/abs/2509.16157)
- **[MEASURED, older] JIT by count of LP actions.** JIT was over 90% of all LP mint/burn activity on Uniswap v3 at end-2022, but the share of volume affected was small — [VirtuSwap analysis](https://medium.com/virtuswap/dissecting-the-jit-liquidity-attack-b283504e0de7)
- **[THEORY] JIT can reduce liquidity.** JIT LPs only serve uninformed orders and can crowd out passive LPs when order volume is not elastic, so total liquidity can fall. Proposed remedies are a two-tier fee or Cournot competition among JIT LPs — [Capponi, Jia, Zhu, "The Paradox of Just-in-Time Liquidity", arXiv 2311.18164](https://arxiv.org/abs/2311.18164)
- **[MEASURED] Concentration of stable LP capital:**
  - Single positions above $100M and very few active positions in DAI-USDC 0.01% — [Heimbach et al.](https://arxiv.org/abs/2205.08904)
  - One about $100M position in USDT/USDC 0.01% — [CrocSwap](https://crocswap.medium.com/stablecoins-on-uniswap-v3-25b88ba36bd3) (snippet)
  - Fewer LPs but larger average wallets in the 0.01% tier — [Keyrock](https://keyrock.com/liquidity-providers-on-uniswap-v3-2/)
- **[MEASURED] Fee-tier migration:**
  - 0.05% → 0.01% for stable-stable after Nov 2021 — [Lambert](https://lambert-guillaume.medium.com/designing-a-constant-volatility-amm-e167278b5d61) (snippet)
  - v4 stable pools at 0.0005-0.0008% carrying $11-14B/month versus $1-2B on v3 (Oct 2026) — [CryptoBriefing](https://cryptobriefing.com/uniswap-v4-v3-stablecoin-dex-volume/)
  - Live v4 pools with implied 0.03-0.12 bp fees turning 4-20×/day (Section 2) — [DefiLlama](https://yields.llama.fi/pools)
- **[MEASURED] RFQ/intent concentration (talk, ≈mid-2025).**
  - UniswapX: 2 market makers ≈ 90% of volume ("heavily dominated by RFQ inventory").
  - 1inch Fusion: 3 makers ≈ 80%.
  - CoW Swap: top maker ≈ 25%.
  - About 70% of DEX transaction volume goes through private mempools.
  - Source: [Danning Sui, "Execution Quality and Orderflow Landscape" (HackMD transcript)](https://hackmd.io/@freddmannen/H1N4kxxSxx). No stable-specific RFQ share was given.
- **[MEASURED] Venue/tier routing in stress.** During the March 2023 USDC depeg, trades with worse execution were routed through the USDC-USDT 0.05% pool and better execution through the 0.01% pool, with wide spreads as bots arbitraged between pools — [Kaiko](https://research.kaiko.com/insights/usdc-depeg-bots) (search snippet; page now redirects)

### Inferences
- **For a new Unichain entrant the competitor is cross-chain venues plus RFQ, not on-chain incumbents.** Ethereum and Base 0.05-0.1 bp pools, Fluid, and RFQ makers who can quote USDC/USDT at about 0-0.5 bp. Aggregators route by all-in price, so a PegGuard pool with base fee ≥ 1 bp would likely be routed around in calm markets. Sub-bp base fees are table stakes.
- **Unichain has no public mempool, which removes mempool-sniping JIT.** Classic JIT needs mempool visibility of pending swaps. Builder- or sequencer-level ordering is a separate question; see Gaps.
- **Where the "PegGuard premium" would come from.** Since pros quote tight and cheap, the only flow a stable pool can charge more for is flow that is inelastic to price: depeg panic and large size needing depth. That supports keeping a low symmetric base fee and charging only in stress (threshold dynamic fee), consistent with Campbell et al.

### Gaps
- No study measures JIT share specifically in USDC/USDT pools, or on v4/L2s. One search summary attributed a "~0.3% of Uniswap v3 liquidity from JIT" figure to a 2023-2024 study. I checked arXiv 2509.05013 and 2505.15338 and could not find that figure, so it is unverified.
- No public number was found for the share of stable-stable flow filled by RFQ/PMM versus AMMs.
- Unichain block-building rules (private sequencer, priority ordering, Flashblocks) and whether in-block JIT or backrunning is possible were not researched here; likely covered by another researcher.

## 4. Tail risk: depeg episodes and what happens to concentrated stable LPs

### Takeaway
Depegs are jump events of 1-35% that last minutes (single-venue wicks) to about 3 days (USDC/SVB). A concentrated stable LP is mechanically short a put on each leg: arbitrageurs sell the weakening coin into the pool at roughly par until the range is exhausted, so the LP ends 100% in the depegged asset. If the peg recovers, the LP round-trips with large fee income (USDT-USDC was among Uniswap's most lucrative pools in March 2023). If it does not, the LP eats about half the haircut relative to a 50/50 hold (all of it relative to holding the good coin). A 50 bp fee cap or breaker barely dents a 3-12% gap. Protection has to come from oracle-relative pricing, one-sided halts, or withdrawal.

### Cited Findings
- **[MEASURED] USDC/SVB, 10-13 Mar 2023.**
  - My pull of Binance USDCUSDT hourly candles: the series starts 2023-03-11 14:00 UTC with a low of 0.882 and close 0.9129. It hovered at 0.94-0.97 through 12 Mar, was back above 0.99 by 13 Mar 14:00 UTC, and around 0.995-0.996 on 14-15 Mar — [Binance market-data API](https://data-api.binance.vision/api/v3/klines?symbol=USDCUSDT&interval=1h&startTime=1678233600000&limit=200)
  - USDC fell to $0.87; USDT-USDC was among the most profitable Uniswap pairs for LPs with $2.4M in fees over the period — [Decrypt](https://decrypt.co/123327/curve-finance-uniswap-trade-volumes-soar-usdc-depeg)
  - USDC returned to $1 after about three days — [EigenPhi](https://eigenphi.substack.com/p/usdc-depegging-victims-signals-and-opportunities)
  - Worse-execution flow went through the 0.05% pool and better execution through 0.01% — [Kaiko](https://research.kaiko.com/insights/usdc-depeg-bots) (snippet)
- **[MEASURED] USDT, 12 May 2022 (Terra collapse).** USDT down 4.8% to 0.9508 (single secondary source) — [CoinGape](https://coingape.com/breaking-usdt-depegs-again-as-whales-dump-largest-stablecoin/)
- **[MEASURED] USDT, June 2023.** Curve 3pool USDT share exceeded 70% and USDT traded around $0.997. The Block notes a similar imbalance after Terra in May 2022 — [The Block](https://www.theblock.co/post/234822/tether-depeg-curve-3pool)
- **[MEASURED] USDe, 10 Oct 2025.**
  - USDe hit $0.65 on Binance only — [Bloomberg Law](https://news.bloomberglaw.com/crypto/third-largest-stablecoin-briefly-loses-dollar-peg-in-crypto-rout)
  - Ethena attributed the move to Binance's internal orderbook-based oracle and said Curve, Fluid and Uniswap showed deviations of ≤30 bp — [Cointelegraph](https://cointelegraph.com/news/usde-depeg-oracle-issues-ethena-founder)
  - Binance paid about $283M in compensation for three depegged assets — [The Block](https://theblock.co/post/374295/binance-pays-283-million-in-compensation-following-fridays-depegs-covering-user-losses)
  - My Binance USDEUSDT 1-minute pull: low 0.6500 at 21:54 UTC; 86 one-minute closes below 0.99 between 21:20 and 22:53 UTC; 118 below 0.995 — [Binance market-data API](https://data-api.binance.vision/api/v3/klines?symbol=USDEUSDT&interval=1m&limit=5)
- **[MEASURED] USDe, 22 Sep 2026 (Binance wick).** Binance USDEUSDT 1-minute low 0.9202 at 05:04 UTC, with only 3 one-minute closes below 0.99 and 6 below 0.998 — [Binance market-data API](https://data-api.binance.vision/api/v3/klines?symbol=USDEUSDT&interval=1m&limit=5). No news corroboration was found, so treat it as a single-venue wick.
- **[MEASURED] FDUSD wicks.** Binance FDUSDUSDT hourly high 1.1932 (2026-02-24) and low 0.9905 (2026-10-08) — [Binance market-data API](https://data-api.binance.vision/api/v3/klines?symbol=FDUSDUSDT&interval=1h&limit=5)
- **[MEASURED] Smart-contract tail on a stable LP hook.** Bunni v2 (a Uniswap v4 hook) lost about $8.4M on 2 Sep 2025 from its USDC/USDT pool on Ethereum and weETH/ETH on Unichain, caused by a rounding-direction bug in idle-balance withdrawal accounting. The USDC/USDT pool was drained of most of its USDC — [BlockSec](https://blocksec.com/blog/bunni-incident-repeated-small-withdrawals-compound-a-rounding-error-into-an-8.4m-drain); [DefiLlama](https://defillama.com/protocol/bunni). Bunni shut down in Oct 2025, saying a secure relaunch would cost six to seven figures in audits and monitoring — [The Block](https://www.theblock.co/post/375813/bunni-dex-shuts-down)
- **[MODELED] Stable-pair contagion.** Under contagion, LPs in USDC/USDT, DAI/USDC and 3pool suffer severe IL as arbitrageurs drain the "good" stablecoin. This is scenario analysis, not measured data — [Spark research](https://www.spark.money/research/stablecoin-depeg-contagion-defi-cascades)

### Inferences
- **[COMPUTED] Loss arithmetic for a ±δ range LP when coin A drops to price 1−J (J ≫ δ).** The pool sells all its B for A at about par minus fee. Marked-to-market loss versus a 50/50 hold ≈ J/2 of position value: about 6% at SVB's 0.88 trough, about 17.5% for USDe's Binance 0.65 print if DEXs had followed (they did not; ≤30 bp). If A re-pegs, the LP buys B back near par within its range, so the loss is not realized and fee income from two-way panic flow is a windfall. That matches the $2.4M USDT-USDC fees in March 2023. The real risk is permanence (UST-type collapse) or forced withdrawal at the trough.
- **A fixed 50 bp guard fee only changes the conversion price by 50 bp** against a 3-35% gap. It does not stop inventory flipping into the weak coin. Real protection options:
  - (a) Oracle-anchored fee ≥ |oracle − pool| on the draining direction, which effectively quotes at the oracle price.
  - (b) A one-sided halt or extreme fee on sells of the weak coin once a dual-feed ratio (e.g., USDC/USD ÷ USDT/USD) breaches the threshold.
  - (c) Automated LP withdrawal/rebalance to a wider range.
  - (d) Accepting the risk as a deliberate "peg-recovery" bet, with fees as compensation.
- **Important observation on PegGuard's current GUARD code** (read-only review of `src/PegGuardHook.sol` lines 244-254 and `src/lib/SignalMath.sol` `isCorrecting`/`deviationBps`):
  - When TRIPPED, only *non-correcting* flow (flow moving the pool away from the oracle fair value) pays `guardFeePips`. *Correcting* flow pays the base fee.
  - In a real depeg the oracle fair value moves and the pool lags. Arbitrage that dumps the weak coin into the pool is the "correcting" direction, so the flow that drains LPs' good asset pays only the base fee. The flow charged the guard fee is the direction a rational arb would not take.
  - The 450 s basis EMA will also absorb a persistent depeg into `basisWad`, shrinking `devE2` over time. The trip latches until disarm, but re-arming after a disarm could be muted.
  - The team should verify whether the intent is to charge peg-*deepening* flow (relative to $1) or pool-vs-oracle *non-correcting* flow; these are opposite during a depeg. The README already flags that guard mode needs a dual-feed ratio. This is an inference from code reading, not a test result.
- **A sub-minute single-venue wick (USDe Oct 2025 and Sep 2026 on Binance) argues for multi-venue/dual-feed confirmation.** A single-feed breaker keyed to Binance-like prices could trip on a venue-specific oracle artifact while DEX prices held within 30 bp. Tighten-fast/loosen-slow, as PegGuard already does, limits the cost of false trips.

### Gaps
- No on-chain study quantifies realized P&L of concentrated USDC/USDT LP positions through March 2023 (fees versus mark-to-market at the trough versus final).
- The DAI March 2023 path (DAI tracked USDC down via PSM) and the Curve 3pool composition at the SVB trough were not retrieved with sources.
- Other 2024-2026 stablecoin failures with permanent losses (e.g., yield-bearing synthetic dollars) were not researched. None appeared in my searches with reliable sourcing.

## 5. Mechanism designs that change stable-pair LP outcomes

### Takeaway
The mechanisms with real traction for stables combine near-zero swap fees with a second revenue source: lending yield on the same capital (Fluid smart collateral/debt, EulerSwap, Bunni rehypothecation), or auctioned/managed fees (am-AMM, Angstrom). Imbalance- or off-peg-triggered dynamic fees (Curve StableSwap-NG `offpeg_fee_multiplier`, threshold fees) are the theory-backed way to charge stress flow. Published, independent performance numbers for these designs on stable pairs are scarce. The clearest real-world signal is Fluid's and v4 sub-bp pools' volume capture, plus Bunni's exploit and shutdown as a warning on hook complexity.

### Cited Findings
- **Curve StableSwap-NG dynamic fee** (formula from docs): `dynamic_fee = (fee_m × fee) / (((fee_m − 10^10) × 4 × xp_i × xp_j / (xp_i + xp_j)^2) + 10^10)`, where `fee_m` = `offpeg_fee_multiplier`. The fee equals the base fee when balanced and rises toward `fee × fee_m / 10^10` as the pool imbalances — [Curve docs, StableSwap-NG overview](https://docs.curve.finance/developer/amm/stableswap-ng/overview). Typical multiplier values were not stated on the page. Empirically, Curve 3pool ($160M) now turns only 0.01×/day ([GeckoTerminal](https://api.geckoterminal.com/api/v2/search/pools?query=USDC%20USDT&network=eth)).
- **am-AMM (auction-managed AMM).** A Harberger-lease auction picks a pool manager who pays per-block rent to LPs, sets the fee (up to a cap) and keeps fees. The manager can trade fee-free, capturing arb/LVR. "Under certain assumptions, this AMM should have higher liquidity in equilibrium than any standard, fixed-fee AMM" — [Adams, Moallemi, Reynolds, Robinson, arXiv 2403.03367](https://arxiv.org/abs/2403.03367). It was adopted in Bunni v2 alongside surge fees and rehypothecation into ERC-4626 vaults (Aave/Yearn/Euler/Morpho) — [BlockSec](https://blocksec.com/blog/bunni-incident-repeated-small-withdrawals-compound-a-rounding-error-into-an-8.4m-drain); [DefiLlama Bunni page](https://defillama.com/protocol/bunni) (cites an illustrative 13% lending APY on USDC-USDT; marketing, not measured). Bunni was exploited (Sep 2025) and shut down (Oct 2025) — [The Block](https://www.theblock.co/post/375813/bunni-dex-shuts-down). No independent measured am-AMM or surge-fee results on stables were found.
- **Angstrom (Sorella).** A v4 hook plus an off-chain app-specific sequencer network that auctions aggregated flow at uniform clearing prices, aimed at LVR, sandwiching and reward distribution — [Uniswap Foundation, builder story](https://uniswapfoundation.org/blog/builder-stories-yuki-yuminaga-on-ass-and-angstrom); launch noted in [Uniswap Foundation builder update #31](https://uniswapfoundation.org/blog/builder-update-31-angstrom-oz-hook-library-eth-nyc). No stable-pair performance data was found.
- **EulerSwap.** LP deposits sit in Euler lending vaults and earn lending yield while backing swaps; launch materials claim up to 50× the depth of a traditional AMM (team claim) — [The Block](https://www.theblock.co/post/356004/euler-to-launch-eulerswap-dex-with-lending-boosted-yield). The only stable data point found is promotional: a $250k test USDC/USDT pool swapping more than 5× its size (Euler Binance Square post, unverified).
- **Fluid DEX** (smart collateral/debt; LP capital also earns lending yield). Ethereum USDC/USDT: $43.9M TVL, $206.6M/day, 2.06×/day 7-day average turnover, swap-fee APR 0.47-0.60% (30-365 day means). Arbitrum USDC/USDT0: $11.7M TVL, fee APR 0.42-0.45% (2026-10-13) — [DefiLlama](https://yields.llama.fi/pools). Fluid is 3.6% of all stablecoin-involved DEX volume over 30 days to 10 Oct 2026 per Token Terminal — [CoinGabbar](https://www.coingabbar.com/en/stablecoin-dex-volume-uniswap-30-days).
- **Uniswap v4 dynamic-fee hooks on stables (live).** An Ethereum v4 USDC/USDT dynamic-fee hook pool created 2026-09-10 is doing $85-95M/day on about $4.5-4.9M TVL (13.6-19.5×/day), with implied fee ≈ 0.08 bp and fee APR 3.2-5.9% — [DefiLlama](https://yields.llama.fi/pools); [GeckoTerminal](https://api.geckoterminal.com/api/v2/search/pools?query=USDC%20USDT&network=eth). The hook logic is unknown.
- **Threshold dynamic fee (theory).** "A threshold-type dynamic fee schedule is robust to market conditions and improves LP outcomes" — [Campbell et al. 2026](https://arxiv.org/abs/2508.08152).
- **Volatility/momentum dynamic fees (empirical sim).** Short-term volatility and momentum fee functions give significantly better LVR-reduction-per-fee-increase trade-offs for USDC-WETH, but not for UNI-WETH (Uniswap v2/v3 and CoW AMM data, 2024) — [Ahlroos & Eloranta, HackMD](https://hackmd.io/@anteroe/BkIbSfwmJx)
- **Faster or constant blocks are a free mechanism.** ARB scales with √Δt for positive fees ([arXiv 2305.14604](https://arxiv.org/abs/2305.14604)), and constant spacing minimizes LVR ([arXiv 2505.05113](https://arxiv.org/abs/2505.05113)). Unichain's 1 s fixed blocks already deliver most of the LVR reduction that hooks target on slow chains.

### Inferences
- **For stables the binding problem is revenue per dollar, not LVR.** So the value-adding mechanisms are those that:
  - (i) stack yield on idle capital (rehypothecation/lending), raising the hurdle-adjusted return by about 3-4%/yr;
  - (ii) keep calm-market fees at or below the market-clearing ~0.05-0.1 bp to win routing;
  - (iii) charge stress flow via imbalance or oracle-triggered fees (Curve NG-style or threshold);
  - (iv) protect inventory in depegs.
  
  PegGuard addresses (iii) and partly (iv). It does not address (i) or (ii) unless base-fee configuration and a vault integration are added.
- **Bunni shows the costs of complexity.** Rehypothecation plus custom LDF accounting raised smart-contract tail risk (8.4M loss) and the audit/monitoring cost per relaunch (six to seven figures). For a small team on Unichain, a minimal hook is a risk-management choice, consistent with PegGuard's "never revert, fall back to base fee" invariant.
- **The dynamic-fee hook pool doing about 19×/day turnover on Ethereum since Sep 2026 suggests hooks are not penalized by routers** when calm-market fees are competitive.

### Gaps
- No independent, measured LP-return data for am-AMM, Bunni surge fees/LDFs, Angstrom, EulerSwap or Ekubo on stable pairs. Ekubo was not researched (no results surfaced).
- Typical `offpeg_fee_multiplier` values and their realized effect on Curve stable LP returns were not found.
- No public evaluation of oracle-pegged stable AMMs (pricing at oracle ± fee) on live stable pairs was found.

## 6. Bottom line: when is stable-pair LP net positive, and what does a PegGuard-style hook add?

### Takeaway
Stable LPing is net positive when (fee share × pool turnover × fee) + any lending yield or incentives exceeds the opportunity cost (≈3-4.5% for USDC/USDT lending in Oct 2026) plus gas/re-centering costs plus expected depeg loss. On fast, cheap chains, LVR is a rounding error.

With measured market-clearing fees of about 0.05-0.1 bp, a pool needs roughly 10-20× daily turnover just to reach 3.6-7.3% pool-level APR. Only the best-routed pools on Ethereum, Base and Arbitrum achieve that today, and Unichain stable-stable volume is about zero. PegGuard's GUARD value over a static 0.01%/0.005% pool is therefore not in calm markets, where the right move is a low symmetric base fee. Its value is in (a) stress-period fee capture from inelastic depeg flow and (b) inventory protection, provided the breaker charges the draining direction and uses a dual-feed ratio. As coded today it appears to charge the opposite direction (Section 4).

### Cited Findings
- [COMPUTED] **Pool-level fee APR = turnover/day × fee × 365.** At 0.1 bp: 0.73% at 2×/day, 3.65% at 10×, 7.3% at 20×. At 0.5 bp: 3.65% at 2×, 18.3% at 10×. At 1 bp: 1.83% at 0.5× and 7.3% at 2×. Observed: 1 bp v3 Ethereum pool at 0.3×/day earns 1.3-2.2%; 0.1 bp v4 pools at 4-19×/day earn about 1.6-5.9% — [DefiLlama](https://yields.llama.fi/pools)
- [MEASURED] **Opportunity cost** 2.5-4.4% (Aave USDC across chains), 3.8% (sUSDS), 4.9% (sUSDe) on 2026-10-13 — [DefiLlama](https://yields.llama.fi/pools)
- [MEASURED] **On L1, re-centering gas** for a $1M active USDC/USDT position at 20 gwei roughly equaled or exceeded monthly fees (Sep 2024) — [arXiv 2505.15338](https://arxiv.org/abs/2505.15338)
- [THEORY] **On a 1 s chain with fee ≥ 0.5 bp,** P_trade ≈ 0.5-1% and arb losses are about 0.01-0.2%/yr of in-range capital — derived from [arXiv 2305.14604](https://arxiv.org/abs/2305.14604) and the Binance σ above
- [THEORY] **Profit-maximizing fee ≈ competing venue cost;** threshold dynamic fees are robust — [arXiv 2508.08152](https://arxiv.org/abs/2508.08152)
- [MEASURED] **Depeg windfall versus loss:** USDT-USDC Uniswap fees $2.4M during the March 2023 USDC depeg, with USDC re-pegging in about 3 days — [Decrypt](https://decrypt.co/123327/curve-finance-uniswap-trade-volumes-soar-usdc-depeg); [EigenPhi](https://eigenphi.substack.com/p/usdc-depegging-victims-signals-and-opportunities)

### Inferences
- **Conditions for a net-positive stable strategy on Unichain** (all inferences):
  1. **Fee and routing.** Calm-market base fee ≤ about 0.1 bp, or ≤ 0.5 bp if Unichain routing has less competition. At 1 bp the pool will be routed around unless it is the only venue.
  2. **Turnover.** About 10×/day or more at 0.1 bp (≈3.65%+) to clear lending opportunity cost on fees alone. Or about 2×/day at 0.5 bp.
  3. **Range.** Tight (±1-5 bp) active ranges. Gas on Unichain is cheap, so frequent re-centering is affordable, unlike L1 where it ate the fees in the Sep 2024 backtest.
  4. **Yield stacking.** Idle out-of-range liquidity earning about 3-4% in Unichain lending markets (Euler and Morpho are live there per DefiLlama), accepting the smart-contract risk Bunni illustrates.
  5. **Incentives.** Likely necessary to bootstrap any Unichain stable flow, since organic stable-stable volume on Unichain is about zero today.
  6. **Depeg policy.** An explicit choice between peg-recovery exposure (earn fees, hold the weak coin) and protection (oracle-anchored fee or one-sided halt).
- **What PegGuard adds beyond a static 0.01%/0.005% pool:**
  1. **Lower fee floor.** It allows a lower static floor (e.g., 0.05-0.1 bp) without exposing LPs to stress-flow underpricing. A static pool must pick one fee for both regimes; a threshold hook does not. This is consistent with Campbell et al.
  2. **Stress capture.** It captures inelastic depeg-period flow at a higher fee, which a static pool gives away at 0.5-1 bp.
  3. **Inventory protection, only if redesigned.** This requires: charging the pool-draining direction during a depeg (today's code charges the non-correcting direction); a dual-feed USDC/USD ÷ USDT/USD ratio with multi-venue confirmation to avoid single-venue wicks like USDe on Binance; and freezing the basis EMA when the breaker trips so a persistent depeg is not de-trended away.
  4. **Fallback safety.** "Never worse than static" fallback limits integration and oracle risk.
  
  It does **not** add calm-market alpha on stables. That matches PegGuard's own measurement (0.000-0.35 bp deviations) and the theory, where P_trade is about 0.5% at 1 bp on 1 s blocks.
- **Expected magnitude (rough, inference).** If the depeg breaker turns a once-every-1-2-years 3-12% event from "LP sells good coin at ~par" into "LP sells at the oracle price minus base fee", it avoids about J/2 ≈ 1.5-6% of position value per event. That is comparable to or larger than a full year of calm fee APR at sub-bp fees. Tail protection, not calm-market premium, is where a stable hook can matter economically.

### Gaps
- There are no route-away elasticity estimates for stable flow under a hook fee versus static pools. PegGuard's own analysis also lists this as an open item.
- No measured frequency distribution of stable depegs ≥ 50 bp across 2023-2026 on DEX prices (as opposed to single-CEX wicks) was assembled.
- The Unichain-specific aggregator routing share, and whether Uniswap's routing API or UniswapX would route USDC/USDT0 to a Unichain hook pool, were not researched.
