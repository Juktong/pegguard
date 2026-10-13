# Unichain stablecoin-pair market making: competition, incentives, protocol fees and opportunity cost (as of 2026-10-13)

Data note: live API pulls were made on 2026-10-13 from Merkl (`api.merkl.xyz/v4`, chain 130), DefiLlama (TVL, DEX, aggregator, fees, stablecoins, yields APIs) and Morpho (`api.morpho.org/graphql`). The raw JSON and analysis scripts are in `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/competition_incentives/` (data in `data_merkl/`). The scratchpad is temporary, so the key numbers are copied below. All dollar figures are DefiLlama/Merkl/Morpho values at pull time unless dated otherwise. "STALE" marks figures superseded by newer data.

## Q1. Venues on Unichain that trade stablecoins, and v4 hooks targeting stables or LP management

### Takeaway
As of Oct 2026, stablecoin trading on Unichain is almost entirely Uniswap v3/v4. Uniswap had about 98% of the last 30 days' DEX volume. Velodrome, Curve, EulerSwap, SushiSwap v4 and 1inch Aqua are present but carry close to zero stable flow. Aave, Fluid, Balancer, PancakeSwap, Ekubo, Angstrom and Arrakis are not deployed on Unichain according to DefiLlama. The stable-focused hook that drew real liquidity (Bunni USDC/USDT0) is defunct. The closest live analog to PegGuard is Solo Labs' Aegis dynamic-fee hook, with about $1.7M of TVL.

### Cited Findings
- **DEX volume on Unichain, last 30 days to 2026-10-13 (DefiLlama):**
  - Total: $321.9M; 24h $9.8M; 1y $11.9B; all-time $77.5B.
  - Uniswap V3: $192.8M (1y $795M).
  - Uniswap V4: $122.3M (1y $9.94B).
  - Velodrome V3: $6.8M (1y $1.157B, about $0 in the last 7 days).
  - EulerSwap: $0.1M.
  - Curve DEX, Uniswap V2, Velodrome V2, Bunni V2, 1inch Aqua and Tristero Darkpool: about $0.
  - — [DefiLlama DEX overview API, Unichain](https://api.llama.fi/overview/dexs/Unichain)
- **TVL by protocol on Unichain, 2026-10-13 (DefiLlama):**
  - DEXs: Uniswap V4 $13.00M; Uniswap V3 $8.53M; Curve DEX $0.77M; DyorSwap $0.10M; Uniswap V2 $0.06M; Velodrome V3 $0.06M; SushiSwap V4 about $2.6K.
  - Hooks / LP management: Aegis Markets (Liquidity Manager) $1.71M; Bunni V2 $4.3K; Gamma $3.4K; Arcadia $83; Steer $10; GlueHook $430.
  - Lending and curators: alphagrowth (risk curator) $2.85M; Euler V2 $1.96M; Morpho Blue $1.12M; Compound V3 $0.67M; Gauntlet $0.40M; Venus $16.5K.
  - Bridges: Stargate/LayerZero $0.37M.
  - Sky / Spark: Spark Savings $0.13M; Spark Liquidity Layer $28.5K.
  - In total, 64 protocols list Unichain.
  - — [DefiLlama protocols API](https://api.llama.fi/protocols)
- **Not deployed on Unichain per DefiLlama's chain lists (2026-10-13):** Aave V3, Fluid (Lending/DEX), Balancer (V2/V3), PancakeSwap (AMM/V3/Infinity), Ekubo, Angstrom, Arrakis (V2/Modular), Maverick, ICHI, KyberSwap Elastic. — [DefiLlama protocols API](https://api.llama.fi/protocols)
- **Unichain DEX volume share by month (DefiLlama breakdown):**
  - Aug 2025: Uniswap v4 $11.75B of $12.43B; Velodrome V3 $532M (4.3%).
  - Nov 2025: Velodrome V3 $487M of $2.97B (about 16%, its peak share).
  - Sep 2026: Uniswap V3 $199M + V4 $134M of $342M (about 97%); Velodrome $10M.
  - From Jun 2026, v3 volume overtook v4 (Jun 2026: v3 $161M vs v4 $226M; Jul–Sep 2026: v3 larger every month).
  - — [DefiLlama DEX overview API, Unichain](https://api.llama.fi/overview/dexs/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=false)
- **Average fee rates, last 30 days (DefiLlama):**
  - Uniswap v4 on Unichain: $115.9K of fees on $122.3M of volume.
  - Uniswap v3 on Unichain (monthly): fees jumped from about $12K/month (Jan–May 2026) to $483K (Jun), $371K (Jul), $540K (Aug) and $594K (Sep 2026). That implies an average fee of about 30bp on v3 volume.
  - — [DefiLlama Uniswap v4 fees](https://api.llama.fi/summary/fees/uniswap-v4?dataType=dailyFees); [DefiLlama Uniswap v3 fees](https://api.llama.fi/summary/fees/uniswap-v3?dataType=dailyFees)
- **Aegis:** a Solo Labs Uniswap v4 hook described as "a fully on-chain, self-regulating dynamic fee system". Fees change per block with price movement, to protect LPs from MEV and toxic flow. DefiLlama lists it on Unichain and Base. — [Uniswap Foundation Hook Design Lab](https://uniswapfoundation.org/blog/introducing-the-uniswap-v4-hook-design-lab); [DefiLlama Aegis Markets](https://defillama.com/protocol/aegis-markets)
- **Bunni (USDC/USDT stable hook):**
  - Over Apr–Jul 2025, the Bunni USDC/USDT hooked pool on Unichain held about 40% of TVL and volume share against its vanilla v4 counterpart. Its base yield was 4.14%, against 1.66% for the vanilla pool.
  - Hooked variants in general captured 40–96% market share in their pairs (Gauntlet retro).
  - — [Gauntlet 3-month retro](https://www.gauntlet.xyz/resources/gauntlet-generated-33b-in-volume-for-unichain)
- **Bunni exploit and shutdown:**
  - Bunni was exploited for about $8.4M in early Sep 2025 (rounding bug in withdrawals, plus flash loan and sandwich).
  - Per Bunni's post-mortem, the exploit hit weETH/ETH on Unichain and USDC/USDT on Ethereum. The largest pool, Unichain USDC/USD₮0, reportedly escaped because there was not enough flash-loan liquidity.
  - Bunni announced a permanent shutdown on 2025-10-23.
  - Reports conflict on the chain split of the losses: one says $5.9M was lost on Unichain.
  - — [Decrypt](https://decrypt.co/345621/decentralized-exchange-bunni-pulls-the-plug-following-8-4m-flash-loan-exploit); [The Block](https://www.theblock.co/post/368987/bunni-exploit)
- **Other hooked pools in the Gauntlet program (2025):**
  - Renzo hook (ezETH/ETH): 90% of ezETH volume and 96% of ezETH TVL on Unichain.
  - Solo Labs ETH/WBTC0: 90% of TVL and volume share.
  - — [Gauntlet retro](https://www.gauntlet.xyz/resources/gauntlet-generated-33b-in-volume-for-unichain)
- **Hook count:** about 2,500 custom Uniswap v4 pools use third-party hooks on Unichain (Hindenrank, updated 2026-08-01). — [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)

### Inferences
- A new stable-pair LP on Unichain competes mainly with other Uniswap v4/v3 USDC–USDT0 pools, including the formerly Gauntlet-incentivized static 0.01% v4 pool, id `0x77ea9d2b…59c9`. It does not compete with other AMMs in any meaningful way.
- The 2025 Bunni result is direct evidence that a smarter stable hook can win about 40% share and earn 2.5x the vanilla base yield. That supports PegGuard's thesis.
- The same Bunni history, however, shows that hook-level smart-contract risk can be fatal for a venue.
- Aegis is the live dynamic-fee competitor to watch. Its $1.7M of TVL is small, but it is larger than any LP manager on the chain.

### Gaps
- I could not confirm which Unichain pools Aegis currently hosts, so I can't say whether it runs a USDC/USDT0 pool.
- I did not find whether EulerSwap on Unichain has a live USDC/USDT0 curve (DefiLlama shows only $0.1M of 30d volume).
- Pool-level stable TVL and volume per venue is out of scope here and is covered by the other researcher.

## Q2. Order-flow routing: UniswapX, aggregators, interface routing, RFQ / private market makers

### Takeaway
DefiLlama-tracked aggregators routed about $36.7M on Unichain in the last 30 days, about 11% of the $321.9M of DEX volume. KyberSwap and 0x lead, with Uniswap's own aggregator (interface/UniswapX) third. Unichain is listed among the UniswapX DutchV3 chains, so some flow can be filled off-AMM by fillers. I found no data on what share of Unichain stable flow is filled off-AMM.

### Cited Findings
- **Aggregator volume on Unichain, last 30 days to 2026-10-13:**
  - Total $36.72M (1y $1.437B).
  - KyberSwap $13.91M (1y $107.7M); 0x $13.31M (1y $98.0M); Uniswap Aggregator $6.79M (1y $23.4M); OKX Swap $1.19M; Nordstern $0.86M; 1inch $0.45M (1y $16.0M); LI.FI $0.05M; Jumper $0.07M.
  - Rubic shows $1,021M over 1y but about $0 in the last 30 days.
  - — [DefiLlama aggregators API, Unichain](https://api.llama.fi/overview/aggregators/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true)
- **UniswapX auction types:**
  - Per the current Uniswap filler FAQ, Unichain is among the "DutchV3 chains" (with Arbitrum, Base, BNB, Ink, Robinhood Chain and others). Exclusivity is measured in blocks (about 2–4 s), and decay starts at `decayStartBlock`.
  - Quote requests include `tokenInChainId`; fillers return 204 for chains they don't quote, and quotes must come back within 500ms.
  - — [Uniswap filler FAQ](http://developers.uniswap.org/llms.mdx/docs/liquidity/uniswapx/filling/faq)
- **Conflicting docs on L2 RFQ:**
  - A search-surfaced docs version listed "Base, Unichain | Priority Gas Auction" and said that on L2s "RFQ is not used and the auction is parameterized based on the AMM price".
  - A 2026-06-13 changelog moved Base and Arbitrum to RFQ/DutchV3 and does not mention Unichain.
  - — [Uniswap changelog: UniswapX RFQ on Base and Arbitrum](https://developers.uniswap.org/docs/changelog/completed-notifications/uniswapx-rfq-auctions-on-base-and-arbitrum.md); [Fillers overview](https://developers.uniswap.org/docs/liquidity/uniswapx/filling/overview)
- **Uniswap Labs fees:** UNIfication set Labs' interface, wallet and API fees to zero. — [UNIfication proposal](https://gov.uniswap.org/t/unification-proposal/25881)
- **Sequencer ordering:** the Unichain sequencer runs in an Intel TDX enclave and orders transactions by effective fee. Flashblocks give 200ms soft confirmations inside 1s blocks (Flashbots Rollup-Boost). — [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)

### Inferences
- Aggregator volume largely re-routes into the same Uniswap pools, so it overlaps with DEX volume rather than adding to it. A PegGuard pool must be indexed by KyberSwap, 0x and Uniswap's routing API to see that roughly 11% of flow.
- v4 hooked pools with custom dynamic fees need explicit aggregator support (custom quoters). That is an integration cost.
- With priority-fee ordering and 200ms Flashblocks, arbitrage against stale pool prices is competitive and fast. A depeg breaker must react within a block.

### Gaps
- No public figure found for the UniswapX fill share or the RFQ/private-MM share of Unichain stablecoin swaps. The "Uniswap Aggregator" line on DefiLlama is not split between UniswapX and classic routing.
- No Dune dashboard was retrieved for Unichain stable-pair flow by router.

## Q3. Professional LPs and LP managers active on Unichain

### Takeaway
LP-management products are almost absent on Unichain in Oct 2026. Gamma has $3.4K, Steer $10, Arcadia $83, Bunni $4.3K residual and vfat $71K. Arrakis and ICHI are not deployed. Aegis's $1.7M is the largest "liquidity manager" TVL. The remaining roughly $21.5M of Uniswap v3+v4 TVL is presumably held by direct LPs, but I could not verify who.

### Cited Findings
- **LP manager / automation TVL on Unichain, 2026-10-13:** Aegis Markets $1.71M; vfat.io $71K; Bunni V2 $4.3K; Gamma $3.4K; GlueHook $430; Arcadia V2 $83; Steer $10. Arrakis and ICHI are not listed on Unichain. — [DefiLlama protocols API](https://api.llama.fi/protocols)
- **Gamma during the 2025 incentives:** the Gamma USDC-USD₮0 vaults on Unichain got only about 140 UNI of Merkl rewards (May–Sep 2025), against 455,281 UNI for direct LPs in the v4 0.01% pool. That suggests vault share was negligible even at peak. — [Merkl campaigns API, chain 130](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)
- **Risk curators on Unichain lending:** alphagrowth ($2.85M), Gauntlet ($0.40M), Re7 ($34K), K3 Capital ($20K), Steakhouse ($5K) and MEV Capital ($92). Market-making firms are not identified publicly. — [DefiLlama protocols API](https://api.llama.fi/protocols)
- **Gauntlet's own lessons:** fixed rewards "risk attracting mercenary capital". Stablecoin, blue-chip and long-tail pools have different ROI profiles. — [Gauntlet retro](https://www.gauntlet.xyz/resources/gauntlet-generated-33b-in-volume-for-unichain)

### Inferences
- There is no vault/ALM incumbent controlling stable-pair liquidity on Unichain. The competition is a small number of direct concentrated-liquidity LPs, probably including professional market makers who stayed after incentives.
- A small, sophisticated LP could win meaningful share of a thin pool. The other side of that is a thin addressable fee pool.

### Gaps
- I could not determine LP-address concentration in the Unichain USDC/USDT0 v4/v3 pools (needs on-chain position analysis or a Dune query), nor which market-making firms are active.

## Q4. Incentives: past and current LP rewards on Unichain

### Takeaway
There are no live incentive campaigns on Unichain as of 2026-10-13: the Merkl chain endpoint reports `liveCampaigns: 0`.
- Stable-pair LP incentives (UNI via Gauntlet/Merkl) ran only from 2025-04-15 to 2025-09-02.
- All Gauntlet UNI campaigns ended by March 2026, when the Merkl router-oracle contracts expired. The governance extension was withdrawn, and a delegate said Unichain incentives are "much harder to justify … without a more clear strategy".
- A new LP should assume zero external rewards.

### Cited Findings
- **Live campaigns:** the Merkl chain-130 endpoint returned `"liveCampaigns":0` on 2026-10-13. `/v4/opportunities?chainId=130&status=LIVE` returned an empty list. — [Merkl chain API](https://api.merkl.xyz/v4/chains/130); [Merkl opportunities API](https://api.merkl.xyz/v4/opportunities?chainId=130&status=LIVE&items=100)
- **Campaign history (1,780 campaigns over 242 opportunities on chain 130, Merkl API):**
  - Starts by month: Apr 2025: 37; May: 114; Jun: 520; Jul: 416; Aug: 282; Sep: 146; Oct: 83; Nov: 75; Dec: 40; Jan 2026: 34; Feb: 24; Mar: 8; then none until one Sep 2026 airdrop.
  - The last campaign end date was 2026-09-09: a one-off "Compound V3 Legacy Rewards — Unichain" airdrop of 917.8 COMP.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)
- **UNI distributed through Merkl on Unichain:** 4,234,634 UNI in total, all from the creator `gauntlet`.
  - By campaign start month: Apr 2025 1.65M; May 775K; Jun 823K; Jul 389K; Aug 190K; Sep 251K; Oct 93K; Nov 10K; Dec 14K; Jan 2026 15K; Feb 21K; Mar 1.7K.
  - 4.06M of the total went to UNISWAP_V4-type campaigns.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)
- **Stable-pair LP incentives specifically:**
  - "UniswapV4 USDC-USD₮0 0.01%" (poolId `0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9`): 455,281 UNI over 12 campaigns from 2025-04-15 to 2025-09-02. That is 10.8% of all Unichain UNI.
    - Tranches tapered: 108,977 UNI (Apr 15–29), 88,967, 51,306, 62,310, 50,540, 48,706, 13,489 (weekly), 10,618, 9,102, 6,799, then 4,464 UNI (Aug 19–Sep 2).
  - "Bunni USDC-USD₮0": 101,173 UNI (2025-06-10 to 2025-09-02), plus 967 rEUL from Euler (Aug 2025).
  - Gamma USDC-USD₮0 vaults: about 140 UNI.
  - No stable-pair LP campaign has run since 2025-09-02.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)
- **Eligibility rules on the v4 stable pool campaigns (Merkl campaign params):**
  - `isOutOfRangeIncentivized: false`, so only in-range liquidity earned rewards.
  - Weights: first tranche weightFees 9800 / token0 100 / token1 100. From 2025-04-29, weightFees 2000 / weightToken0 4000 / weightToken1 4000, i.e. 20% of rewards by fees earned and 80% by in-range token holdings.
  - Empty hook whitelist; the campaign was bound to a single poolId.
  - A May 2025 ANGLE test campaign used price bounds of 0.98–1.02.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100); [Merkl UniswapV4 campaign docs](https://docs.merkl.xyz/merkl-mechanisms/campaign-types/uniswapv4)
- **Other stablecoin-related incentives (2025, all ended):**
  - `gauntlet-unichain` paid USDC rewards for borrowing USDC: Euler USDC vault $177,300 (2025-05-30 to 08-29); Venus $110,588; Compound V3 $88,650.
  - Morpho USDC/USDT0 vault supply rewards (MORPHO/USDC/OP) ran to 2025-12-23; the Gauntlet USDC vault got UNI until 2026-03-10.
  - Euler rEUL rewards on its USDC/USDT0 vaults ran to 2025-09-01.
  - — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)
- **Unichain launch incentive program:**
  - Gauntlet and the Uniswap Foundation launched the program on 2025-04-14: $21.8M (3.5M UNI) across 12 pools, part of a $45M DAO-approved budget for Unichain and v4 ("Uniswap Unleashed").
  - The volume KPI of $22.5B was met by 2025-06-21. Cumulative volume reached $32.8B, and TVS hit $1.4B.
  - About 3.3M UNI was used, leaving a surplus of about 198K UNI.
  - The retro covers 2025-04-14 to 2025-07-19.
  - — [Gauntlet retro](https://www.gauntlet.xyz/resources/gauntlet-generated-33b-in-volume-for-unichain); [Merkl blog](https://merkl.xyz/blog/growing-uniswap-v4-unichain-liquidity-with-merkl)
- **Why incentives stopped:**
  - On 2026-03-03, Gauntlet proposed redeploying the UniV3/UniV4 Merkle Router Oracle contracts, which expired on 2026-03-10, with a 2030 expiry.
  - On 2026-03-10 the group recommended not proceeding and Gauntlet cancelled the Snapshot vote.
  - Commenters cited about 2.66M UNI still in the Aera vault, and about $32M allocated against the $45M request (unverified).
  - The original proposal said incentives "are not meant to be perpetual".
  - — [Uniswap governance forum](https://gov.uniswap.org/t/extension-of-uniswap-incentive-campaign-infrastructure-univ3-univ4-merkle-router-oracles/26048)
- **UNIfication growth budget:** 20M UNI per year to Uniswap Labs, vesting quarterly from 2026-01-01 (5M UNI per 91.25 days; 40M UNI approved for two years). No Unichain LP campaigns funded from it appear on Merkl. — [UNIfication proposal](https://gov.uniswap.org/t/unification-proposal/25881)
- **Unichain Validation Network (UVN):** announced in March 2025 and "not live on mainnet" as of August 2026. It is slated to pay 65% of net chain revenue to UNI-staking validators once live. — [Hindenrank, 2026-08-01](https://hindenrank.com/blog/how-does-unichain-work); [Unichain whitepaper](https://developers.uniswap.org/whitepaper_unichain.pdf)
- **OP rewards:** OP-token rewards on Unichain appear only on 2025 Morpho vault campaigns (174 OP-denominated campaigns, about 192K OP from an unlabelled creator `0xF057…`). I found no 2026 Superchain/OP grant targeting Unichain stable LPs. — [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)

### Inferences
- At Gauntlet's program-average price (about $6.23/UNI, implied by $21.8M / 3.5M UNI), the 455K UNI on the 0.01% stable pool was worth roughly $2.8M over about 4.5 months. Liquidity left once it stopped; see the trajectory in Q7.
- Any 2026–27 Unichain stable incentives would need a fresh, scoped governance proposal (eek637's stated preference). A PegGuard team could pitch one, but should not underwrite it.
- If a campaign is revived on Merkl's v4 template, it binds to a poolId. A PegGuard hooked pool would need its own campaign, and in-range-only rewards would favor tight ranges.

### Gaps
- I found no 2026 Uniswap Foundation, Uniswap Labs or Optimism program aimed at Unichain stable LPs. If one exists off-Merkl (e.g. direct grants), it is not visible here.
- Historical USD value of rewards at time of distribution was not computed: Merkl reports current token prices only.
- The UVN launch date is unknown.

## Q5. Protocol fee policy (UNIfication and follow-ons) and the Unichain sequencer burn

### Takeaway
Unichain pools do not appear to be in any executed protocol-fee activation as of Oct 2026:
- v2/v3 fees are live on Ethereum plus 11 other chains, but Unichain is not among them.
- v4 fees (executed 2026-07-27) cover seven chains, excluding Unichain, and only static-fee hookless, CCA and aggregator-hook pools.

Only Unichain sequencer revenue feeds the UNI burn. Even if Unichain were added, a dynamic-fee hooked pool such as PegGuard falls outside the v4 fee "families". A static 1bp stable pool would pay 0.25bp, i.e. 25% of LP fees.

### Cited Findings
- **UNIfication, approved 2025-12-25 and executed about 2025-12-28:**
  - v2: LP fee 0.30% becomes 0.25% LP + 0.05% protocol.
  - v3 mainnet, per the prose: 0.01% and 0.05% tiers start at 1/4 of LP fees; 0.30% and 1% tiers at 1/6. The forum spec's packed values appeared to encode 1/10, 1/8, 1/6 and 1/4 instead, a discrepancy flagged in the thread.
  - Retroactive burn of 100M UNI.
  - Unichain sequencer fees go to the burn after L1 data costs and Optimism's 15% share; the stated scale then was about $7.5M of annualized sequencer fees.
  - TokenJar/Firepit mechanics: fees accrue in an immutable TokenJar and can only be withdrawn by burning UNI via Firepit.
  - Labs plans "LVR-reducing hooks", a Protocol Fee Discount Auction (estimated to add $0.06–0.26 per $10k traded for LPs) and "stable-stable hooks" on its roadmap.
  - — [UNIfication proposal](https://gov.uniswap.org/t/unification-proposal/25881); [The Defiant](https://thedefiant.io/news/defi/uniswap-passes-unification-fee-switch-proposal)
- **Protocol Fee Expansion Vote 1 (executed 2026-03-07; 62.8M FOR / 4,968 AGAINST):**
  - v2/v3 fees on Arbitrum, Base, Celo, OP Mainnet, Soneium, X Layer, Worldchain and Zora.
  - All mainnet v3 pools via a tier-based v3OpenFeeAdapter (same fee for every pool in a tier; example: "all 1bps LP fee pools could have protocol fees set to 25%").
  - Unichain is not included; it is mentioned only as the precedent for UNI-burn bridging.
  - — [Uniswap Foundation vote page, Proposal 94](https://vote.uniswapfoundation.org/proposals/94); [Temp check](https://gov.uniswap.org/t/temp-check-protocol-fee-expansion-eight-more-chains-and-remaining-mainnet-v3-pools/26035)
- **"Three More Chains" temp check (2026-05-16):** Celo (completion), BNB Chain, Polygon; Unichain not included. DefiLlama dates those activations to 2026-06-02. — [Temp check](https://gov.uniswap.org/t/temp-check-protocol-fee-expansion-three-more-chains/26108); [DefiLlama Uniswap v3 revenue methodology](https://api.llama.fi/summary/fees/uniswap-v3?dataType=dailyRevenue)
- **Activate v4 Protocol Fees (Part 1/2), Proposal 100 (executed 2026-07-27; 46.6M FOR / 1.27M AGAINST):**
  - Chains: Ethereum, Arbitrum, Base, BNB Chain, Polygon, Optimism, Robinhood Chain.
  - Part 2 is deferred: Celo, Soneium, Worldchain, X Layer, Zora.
  - Unichain is not mentioned in either part.
  - Families: static-fee hookless pools, CCA/LBP pools, and aggregator-hook pools. The proposal "does not enable the protocol fee for any pools other than those in the Families".
  - Static curve: 1bp LP fee → 0.25bp protocol fee; 5bp → 1.25bp; 30bp → 5bp; 100bp → 10bp.
  - Aggregator hooks: 10bp default and 3bp for select stable pairs (Base: 3bp and 1bp).
  - — [Proposal 100](https://vote.uniswapfoundation.org/proposals/100); [The Block, 2026-07-18](https://www.theblock.co/post/408836/uni-burn-poised-to-grow-as-uniswap-governance-votes-on-v4-fees-and-robinhood-chain-expansion); [v4 fee temp check](https://gov.uniswap.org/t/temp-check-activate-v4-protocol-fees/26162)
- **DefiLlama methodology:**
  - Fee-switch revenue starts 28 Dec 2025 on Ethereum; 8 Mar 2026 on Optimism, Arbitrum, Base, World Chain, Zora and X Layer; 2 Jun 2026 on Polygon, BSC and Celo; 27 Jul 2026 on Robinhood. Unichain is not listed.
  - DefiLlama nonetheless shows sporadic Unichain "revenue" in the uniswap-v3 adapter: 14 non-zero days since 2026-01-09, with $29.7K in Jan 2026 exceeding v3 fees, and $16.4K in Oct 2026. That looks like sequencer-burn/TokenJar flows rather than pool-level fees (ambiguous).
  - DefiLlama shows $0 of v4 revenue on Unichain.
  - — [DefiLlama Uniswap v3 revenue](https://api.llama.fi/summary/fees/uniswap-v3?dataType=dailyRevenue); [DefiLlama Uniswap v4 revenue](https://api.llama.fi/summary/fees/uniswap-v4?dataType=dailyRevenue)
- **Unichain chain economics (DefiLlama "Unichain" chain):**
  - Gas fees paid: Jul 2025 $710K peak; Oct 2025 $662K; Jan 2026 $34K; Sep 2026 $10.8K; last 365 days $733K.
  - "Revenue (burned coins)": $112.3K in total since Dec 2025; Sep 2026 $7.2K.
  - This contradicts, and makes STALE, the UNIfication-era figure of about $7.5M annualized sequencer fees and Hindenrank's 2026-08 estimate of about $5.5–7.5M/yr burned.
  - — [DefiLlama Unichain fees API](https://api.llama.fi/summary/fees/unichain?dataType=dailyFees); [DefiLlama Unichain revenue API](https://api.llama.fi/summary/fees/unichain?dataType=dailyRevenue); [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)
- **OP Enterprise migration:**
  - Unichain moves to Optimism's OP Enterprise: testnet 2026-10-13, mainnet 2026-10-29 (announced 2026-10-09).
  - Optimism takes over the sequencers, RPC, monitoring and incident response.
  - Chain ID, contracts, balances and Uniswap v2/v3/v4 deployments are unchanged.
  - The post does not address sequencer revenue, the burn or UVN.
  - — [Uniswap blog](https://blog.uniswap.org/unichain-is-upgrading-to-op-enterprise); [CryptoTicker](https://cryptoticker.io/en/unichain-op-enterprise-upgrade-october/)

### Inferences
- Today a Unichain stable LP keeps 100% of pool LP fees: no protocol cut was found for Unichain v2/v3/v4 pools.
- The main fee-policy risk is a future "Unichain" add-on. For a hookless 0.01% v4 or v3 pool that would likely mean a 25% haircut (1bp → 0.75bp net), going by the tier defaults used on other chains.
- PegGuard's dynamic-fee hooked pool would be outside the current v4 families. That gives it a relative edge of up to 25% of fee revenue over a static 1bp competitor if Unichain is ever enabled under the current family rules.
- How sequencer revenue is shared after the OP Enterprise handover is unclear.

### Gaps
- I could not access the Uniswap/protocol-fees GitHub deployment files, so I could not confirm whether a Unichain v3 fee adapter is deployed but set to zero.
- The official fee-split table was not retrieved.
- The sequencer-revenue arrangement after 2026-10-29 is not public in the sources found.

## Q6. Opportunity cost: the hurdle rate for a stable LP (Oct 2026)

### Takeaway
The risk-free-ish hurdle is about 3.5–4.0% in October 2026:
- The FOMC raised rates to 3.75–4.00% on 2026-09-16.
- Tokenized T-bills pay 3.45–3.81%.
- sUSDS pays 3.80%, and Aave USDC on Ethereum 3.68%.
- Curated USDC lending on Base and Ethereum pays about 4.2–5.2%; sUSDe 4.87%; Maple syrupUSDC 5.26%.

On Unichain itself, stable lending pays only about 0.1–1.1% on Morpho. sUSDS (3.8%) is available there, with $166K of TVL. A Unichain stable LP needs net fees above roughly 4% plus depeg, hook and bridge risk premia.

### Cited Findings
- **Fed policy:** the FOMC raised the target range by 25bp to 3.75–4.00% on 2026-09-16 ("raise the target range for the federal funds rate by 1/4 percentage point to 3-3/4 to 4 percent"). The prior range was 3.50–3.75%, held in July 2026. — [Federal Reserve press release, 2026-09-16](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm)
- **Tokenized T-bill / RWA yields (DefiLlama, 2026-10-13):**
  - BlackRock BUIDL: 3.81% (Ethereum Institutional), 3.47% (Ethereum), 3.78% (Solana/Avalanche).
  - Circle USYC: 3.57%.
  - Ondo OUSG 3.70%; Ondo USDY 3.67%.
  - Invesco USTB: 3.45%.
  - Janus Henderson via Centrifuge: 3.67%.
  - — [DefiLlama yields API](https://yields.llama.fi/pools)
- **Sky / Spark (DefiLlama, 2026-10-13):**
  - sUSDS 3.80% (Ethereum, $5.03B TVL; 30d mean 3.64%).
  - sUSDS on Unichain 3.80% ($166K TVL).
  - Spark Savings USDC/USDT on Ethereum 3.75–3.80%.
  - stUSDS 5.6%.
  - — [DefiLlama yields API](https://yields.llama.fi/pools)
- **Ethena (DefiLlama, 2026-10-13):** sUSDe 4.87% (7-day unstaking; $1.21B TVL; 30d mean 4.94%). — [DefiLlama yields API](https://yields.llama.fi/pools)
- **Lending on other chains (DefiLlama, 2026-10-13):**
  - Aave v3 USDC on Ethereum 3.68% (30d mean 4.32%); Aave v3 USDT 3.17%.
  - Fluid USDC on Ethereum 5.74%.
  - Maple syrupUSDC 5.26%.
  - — [DefiLlama yields API](https://yields.llama.fi/pools); [DefiLlama Aave USDC pool chart](https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f9501)
- **Morpho vault net APYs, Base and Ethereum (2026-10-13):**
  - Base: Gauntlet USDC Prime 4.71% ($414M); Spark USDC Vault 4.22% ($452M); Steakhouse USDC 3.60%.
  - Ethereum: Gauntlet USDC Prime 5.20%; Steakhouse USDC 4.22%; Steakhouse USDT 2.40%.
  - Two Ethereum vaults with nonsensical APYs (Adpend, "1337") were excluded as data artifacts.
  - — [Morpho GraphQL API](https://api.morpho.org/graphql)
- **Morpho vaults on Unichain (2026-10-13):**
  - Gauntlet USDC: $71.6K TVL, net APY 1.12%.
  - Gauntlet USDT0: $6.2K, 0.12%.
  - Re7 USDT0: $6.7K, 0%.
  - Other USDC/USDT0 vaults are under $2K.
  - — [Morpho GraphQL API](https://api.morpho.org/graphql)
- **Euler and Compound on Unichain:** DefiLlama yields lists no Unichain USDC/USDT lending pool above $20K. Euler V2 Unichain TVL is $1.96M, but the listed vaults are WETH/weETH; Compound V3 Unichain TVL is $0.67M. — [DefiLlama yields API](https://yields.llama.fi/pools); [DefiLlama protocols API](https://api.llama.fi/protocols)
- **Gauntlet's measured stable LP base yields (Apr–Jul 2025, during peak activity):** vanilla v4 USDC/USDT 1.66% vs Bunni hooked 4.14%. — [Gauntlet retro](https://www.gauntlet.xyz/resources/gauntlet-generated-33b-in-volume-for-unichain)

### Inferences
- The local Unichain alternative (Morpho at about 1%) is not the real hurdle. Capital is mobile through CCTP and USDT0, so the hurdle is about 3.7–4.0% (sUSDS / T-bills, available even on Unichain via sUSDS) to about 4.7–5.2% (curated USDC lending on Base and Ethereum).
- Even at peak 2025 activity the vanilla stable pool earned only 1.66% base. A PegGuard pool would need Bunni-like outperformance and today's (much lower) volume to clear the hurdle, which looks unlikely without incentives. That is an inference; pool-level volumes are with the other researcher.
- Rates moved up in Sep 2026 (a hike), which raises the hurdle further.

### Gaps
- No official 3-month T-bill yield for October 2026 was retrieved. Tokenized-fund APYs and the Fed range serve as proxies; a podcast blurb put the 3M bill at about 3.85% in mid-2026, which is unverified.
- Euler and Compound USDC supply APYs on Unichain were not obtained (not in DefiLlama yields; no API pulled).

## Q7. Ecosystem trajectory: TVL, stablecoins, DEX volume, Uniswap share, entrants and retrenchment

### Takeaway
Unichain was a 2025 incentive-driven boom followed by a 2026 bust:
- TVL went from a $902.9M peak on 2025-07-21 to $26.8M on 2026-10-13 (−97%).
- Stablecoins fell from a $433M peak to $27.1M; Sky's flat $100M USDS line vanished in July 2026.
- Monthly DEX volume fell from $10–13B (May–Aug 2025) to about $0.2–0.4B (2026). Uniswap still has about 97% share.

Uniswap's own attention has visibly shifted: Robinhood Chain v4 fees are about 440x Unichain's, and Unichain ops are being handed to Optimism. Expect a small, low-competition but low-flow venue.

### Cited Findings
- **Unichain TVL (DefiLlama):**
  - Rise: $8.4M (2025-03-01) → $533.5M (2025-05-01) → $855.6M (2025-07-01); peak $902.9M on 2025-07-21.
  - Decline: $487.9M (2025-09-01) → $118.6M (2025-12-01) → $48.2M (2026-03-01) → $27.3M (2026-06-01) → $30.8M (2026-10-01) → $26.8M (2026-10-13).
  - For comparison on 2026-10-13: Base $6.22B, OP Mainnet $445M, Ink $205M, World Chain $42M.
  - — [DefiLlama historical chain TVL API](https://api.llama.fi/v2/historicalChainTvl/Unichain); [DefiLlama chains API](https://api.llama.fi/v2/chains)
- **STALE press figures:** late-2025 reports of "TVL collapses 86%" after the incentives ended, and a "peak US$657M" (different metric/date) are superseded by the DefiLlama series above. Hindenrank's "$1.4B peak" is TVS, not TVL. — [Bitget/Cryptonews](https://www.bitget.com/news/detail/12560605085909); [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)
- **Stablecoins on Unichain (DefiLlama):**
  - Aggregate: $210M (2025-05-01); $433M (2025-07-01); $165M (2026-01-01); $128M (2026-07-01); $25.8M (2026-08-01); $27.1M (2026-10-13).
  - Composition now: USDC $20.2M and USDT (USDT0) $7.6M; DAI, USDS and frxUSD are about 0.
  - USDC: about $167M mid-Jul 2025 → $42M (2026-01) → $36M (2026-06) → $21.9M (2026-07-01) → $19.5M (2026-10-13).
  - USDT: $181M (2025-07-01) → $23M (2026-01) → $40.5M (2026-04-01) → $7.1M (2026-05-01) → $7.6M (2026-10-13).
  - USDS: a flat $100M from 2025 through 2026-07-01, then $0 by 2026-07-15.
  - — [DefiLlama stablecoins, Unichain](https://stablecoins.llama.fi/stablecoincharts/Unichain); [USDS series](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=209); [USDC series](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=2); [USDT series](https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=1)
- **Spark's Unichain allocation:** the May 2025 Sky poll onboarded Unichain to the Spark Liquidity Layer with 100M USDS plus 100M USDS worth of sUSDS bridged. I found no 2026 announcement of a withdrawal. — [Sky governance poll](https://vote.makerdao.com/polling/QmXjeJtw)
- **Monthly DEX volume on Unichain (DefiLlama):**
  - 2025: Apr $3.24B; May $12.88B; Jun $10.51B; Jul $13.45B; Aug $12.43B; Sep $6.41B; Oct $8.64B; Nov $2.97B; Dec $1.06B.
  - 2026: Jan $0.76B; Feb $0.39B; Mar $0.39B; Apr $0.24B; May $0.18B; Jun $0.40B; Jul $0.24B; Aug $0.32B; Sep $0.34B; Oct 1–13 $0.11B.
  - — [DefiLlama DEX overview API, Unichain](https://api.llama.fi/overview/dexs/Unichain)
- **Uniswap v4 TVL on Unichain:** $638M (2025-07-01) → $68M (2025-12-01) → $23.5M (2026-03-01) → $13.7M (2026-07-01) → $13.0M (2026-10-13). — [DefiLlama Uniswap v4 protocol API](https://api.llama.fi/protocol/uniswap-v4)
- **Lending TVL on Unichain:**
  - Morpho: peak $127.6M (2025-08-01) → $1.12M (2026-10-13).
  - Euler: peak $83.6M (2025-07-01) → $1.96M.
  - — [DefiLlama Morpho API](https://api.llama.fi/protocol/morpho-blue); [DefiLlama Euler API](https://api.llama.fi/protocol/euler-v2)
- **Relative Uniswap attention (DefiLlama Uniswap v4 fees, last 30 days):** Robinhood Chain $51.2M; Ethereum $12.1M; BSC $5.8M; Arc $5.0M; Base $3.6M; OP Mainnet $1.6M; Unichain $116K. Robinhood Chain launched on 2026-07-01 with Uniswap v2/v3/v4 and reached $6B of cumulative swap volume by 2026-07-10. — [DefiLlama Uniswap v4 fees](https://api.llama.fi/summary/fees/uniswap-v4?dataType=dailyFees); [The Block](https://www.theblock.co/post/408836/uni-burn-poised-to-grow-as-uniswap-governance-votes-on-v4-fees-and-robinhood-chain-expansion)
- **OP Enterprise handover:** testnet 2026-10-13, mainnet 2026-10-29; Optimism runs the sequencers, RPC and incident response; native interop starting with ETH is planned but undated. — [Uniswap blog](https://blog.uniswap.org/unichain-is-upgrading-to-op-enterprise)
- **Institutional rails:**
  - Circle launched native USDC on Unichain with CCTP at mainnet launch (Feb 2025; page dates conflict between Feb 11 and Mar 31, 2025).
  - USDT0 (LayerZero OFT) lists Unichain among its connected chains (Nov 2025 press release).
  - I found no Coinbase or Kraken Unichain-specific entry; Kraken runs its own OP-Stack chain, Ink.
  - — [Circle blog](https://www.circle.com/blog/now-available-usdc-on-unichain); [USDT0 press release](https://ru.tradingview.com/news/chainwire:b64d7f64c094b:0-usdt0-becomes-the-world-s-largest-cross-chain-liquidity-network-after-surpassing-50-billion-in-transfers)
- **UNI price context:** about $3.50 on 2026-07-18 (The Block); $7.34 on 2026-10-12 (CoinPaprika via CryptoTicker); $7.55 in the Merkl price feed on 2026-10-13. Relevant for valuing any UNI-denominated incentives. — [The Block](https://www.theblock.co/post/408836/uni-burn-poised-to-grow-as-uniswap-governance-votes-on-v4-fees-and-robinhood-chain-expansion); [CryptoTicker](https://cryptoticker.io/en/unichain-op-enterprise-upgrade-october/); [Merkl campaigns API](https://api.merkl.xyz/v4/campaigns?chainId=130&items=100)

### Inferences
- Liquidity on Unichain was largely mercenary. Once UNI rewards tapered (Sep 2025) and stopped (Mar 2026), TVL, stablecoins and volume fell 95–98%, and the late-2025 Bunni exploit and shutdown removed the leading stable hook.
- The July 2026 disappearance of the $100M USDS line (likely the Spark Liquidity Layer allocation; inference) removed the largest stablecoin balance on the chain.
- For PegGuard this cuts both ways:
  - In its favor: competition for stable LP share is thin, there is no protocol fee, and dynamic-fee hooks would be exempt even if fees expanded.
  - Against it: absolute stable flow is small (total chain DEX volume about $11M/day, with only part of it stable-stable). There are no incentives, Uniswap Labs' strategic attention has moved to Robinhood Chain and others, and operations are being handed to Optimism.
- Any Unichain stable LP should be sized as an option on a Unichain revival, such as native interop, a new incentive program or UVN launch. It should not be sized as a carry trade.

### Gaps
- I found no source explaining the July 2026 USDS drop. It may be a Spark Liquidity Layer reallocation or a DefiLlama tracking change; check Spark's allocation dashboard or forum.
- I found no explicit Uniswap Labs statement on long-term Unichain strategy after the OP Enterprise move, or on whether sequencer-revenue burns continue unchanged.
- Messari or Blockworks quarterly coverage of Unichain for 2026 was not retrieved.
