# Unichain chain-level microstructure for stablecoin-pair market making (state as of 2026-10-13)

Measurement conventions used throughout:
- "Own RPC measurement" means queries the researcher ran against the public endpoint `https://mainnet.unichain.org` on 2026-10-13 between about 18:30 and 19:30 UTC. The 30-minute receipt sample covers blocks 61,166,920–61,168,719. The 300-block sample covers 61,167,820–61,168,119. The base-fee history takes one 1,024-block `eth_feeHistory` window every 6 hours from Nov 2024 to Oct 2026, 2,832 windows in all.
- The scripts and raw JSON are in the scratchpad at `/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/chain_microstructure/` (`probe.py`, `sample.py`, `hist.py`, `pyth.py`, `calc.py`, `data_*`).
- ETH/USD = **$2,499** (Coinbase spot $2,499.375 and Kraken last $2,498.89, both read 2026-10-13 ~18:37 UTC). Sources: [Coinbase API](https://api.coinbase.com/v2/prices/ETH-USD/spot), [Kraken API](https://api.kraken.com/0/public/Ticker?pair=ETHUSD). The repo assumes $3,500.

---

## Block production, Flashblocks, Rollup-Boost/TEE building, ordering, and 2025–2026 changes

### Takeaway
Unichain produces exactly 1-second L2 blocks. Each block is split into 200 ms Flashblocks, built by a Flashbots Rollup-Boost/op-rbuilder builder running in a TEE. Transactions are ordered strictly by priority fee *within each Flashblock* but not across the whole block, so ordering is effectively time-then-fee at 200 ms granularity. The biggest pending change is operational. Optimism takes over sequencing, RPC and incident response under "OP Enterprise" on **2026-10-29** (testnet migrated 2026-10-13). The UVN (Unichain Validation Network) still has no confirmed mainnet launch.

### Cited Findings
**Block time and production (live, 2026-10-13)**
- Measured block time is 1.000023 s over the last 86,400 blocks and 1.002 s over the last 1,000. Chain id is 130 and `miner` is the OP sequencer fee vault `0x4200…0011`. — [own RPC measurement](https://mainnet.unichain.org)
- Every block contains **exactly 7 builder system transactions** from EOA `0xcabba9e7f4b3a885c5aa069f88469ac711dd4acc`, all with 0 tip:
  - 5 calls to `0x3c3a8a41…753e`, whose Blockscout-verified implementation is **`FlashblockNumber`** (94,258 gas each);
  - 1 call to `0xd44f9d13…6a29`, verified as **`BlockBuilderPolicy`**, the on-chain TEE builder-attestation/"flashtestation" policy contract (73,120 gas);
  - 1 transaction to `0x0` (21,880 gas).
  - These made up 12,599 of 13,088 transactions (96.3%) in the 30-minute sample, and 1,799 of 1,800 blocks had 5 FlashblockNumber calls. — [own RPC measurement](https://mainnet.unichain.org); contract names from [Blockscout FlashblockNumber](https://unichain.blockscout.com/address/0x3c3a8a41e095c76b03f79f70955fff3b03cf753e) and [Blockscout BlockBuilderPolicy](https://unichain.blockscout.com/address/0xd44f9d1331659f417a3e22c9e29529d498b66a29)
- The Flashblocks interval is 200 ms. Preconfirmations arrive in ~200 ms, compared with up to 1 s for a full block.
  - Read them with the `pending` tag on `eth_getBlockByNumber`, `eth_call`, `eth_getBalance` and `eth_getTransactionCount`. `eth_getTransactionReceipt` returns preconfirmed receipts without a tag.
  - The WebSocket feed is `wss://mainnet-flashblocks.unichain.org/ws` (Sepolia: `wss://sepolia-flashblocks.unichain.org/ws`). It is Brotli-compressed: the first message is the base block, then per-Flashblock diffs.
  - While a block is preconfirmed its block hash is a `0x0` placeholder.
  - Flashblocks are an "out-of-protocol" extension and do not change consensus.
  - Nodes run `ghcr.io/base/node-reth` with `--websocket-url=…`. Production Flashblocks RPC is offered by Alchemy and QuickNode. — [Unichain docs: Integrating Flashblocks](https://developers.uniswap.org/docs/unichain/technical-information/flashblocks)
- Flashblocks went live on **2025-08-14**. The announcement says "Unichain now confirms transactions every 200 milliseconds," designed by Uniswap Labs and Flashbots to run inside TEEs, with transactions "ordered by the fee users are willing to pay." Day-one integrations were Matcha, Odos, OKX and Zerion. — [Uniswap changelog 2025-08-14](https://developers.uniswap.org/docs/changelog/completed-notifications/live-on-unichain-flashblocks-200ms-sub-blocks); [Uniswap blog "Flashblocks are live"](https://blog.uniswap.org/flashblocks-are-live)
- Preconfirmations are not final. A Flashblock can be invalidated if the sequencer crashes or the TEE fails. This comes from a secondary source. — [Chainstack: what are flashblocks](https://chainstack.com/what-are-flashblocks/amp/)
- The TEE builder and Rollup-Boost went live on mainnet on **2025-05-01/02**. Unichain was described as "the first L2 to build blocks inside a TEE" and "the first L2 to launch revert protection on mainnet." In May 2025, public TEE-ordering attestations and 200 ms Flashblocks were still roadmap items. — [Uniswap changelog 2025-05-01](https://developers.uniswap.org/docs/changelog/completed-notifications/live-on-unichain-fair-transaction-ordering-and-mev-protection); [Flashbots "Unichain mainnet" 2025-05-02](https://writings.flashbots.net/unichain-mainnet)

**Ordering rule (empirical)**
- Splitting each block at the FlashblockNumber calls, priority-fee order was strictly non-increasing in **all 82 of 82** segments that held ≥2 user transactions. Across whole blocks, **43 of 90** multi-transaction blocks were *not* fee-monotonic.
  - User transactions appear only in the 4 gaps between the 5 FlashblockNumber calls: 197 / 104 / 87 / 101 transactions in gaps 1–4, and none before the first call or after the last.
  - Gap 1 holds about twice as many transactions as the others. — [own RPC measurement](https://mainnet.unichain.org)
- An academic study (sample Jan–Aug 2025) also finds higher priority fees associated with earlier inclusion on Unichain before Flashblocks (pooled coefficient −0.047, R²=0.919). After Flashblocks, fee sensitivity is significant only in some slots (1, 6, 7, 9).
  - Caveat: the paper's Table 1 lists Unichain at 2.0 s blocks with an "Apr 24" launch, and its appendix says "~22 seconds." Both are wrong, since measured blocks are 1 s. — [Gogol, Schneider, Tessone, arXiv:2506.01462v4 (2025-09-22)](https://arxiv.org/html/2506.01462v4)

**Timeline of chain-level changes (2024-11 → 2026-10)**
- 2024-11-04: L1 contracts deployed. 2025-02-12: mainnet launch per L2BEAT; the public launch was announced 2025-02-11 ([Fortune](https://fortune.com/crypto/2025/02/11/uniswap-labs-opens-hyper-fast-blockchain-unichain-to-the-public-as-l2-race-heats-up)). The rest of L2BEAT's milestone list:
  - 2025-05-01: TEE block building.
  - 2025-08-14: Flashblocks.
  - 2025-11-28: Jovian upgrade (fee and DA-footprint changes).
  - 2025-12-27: UNIfication executed, routing Unichain fees to UNI burns.
  - 2026-02-13: Upgrade 18 (OP Contracts v6.0.0).
  - 2026-07-08: Karst L2 hardfork.
  - 2026-09-24: Upgrade 20 (OP Contracts v8.0.0-rc.3), which moved to **super roots and SUPER_CANNON_KONA** fault proofs.
  - L2BEAT counts 93 upgrades to date. — [L2BEAT Unichain](https://l2beat.com/scaling/projects/unichain)
- Header-parameter changes seen in the 6-hourly samples (first-seen, ±6 h). All come from block `extraData` and `gasLimit`:
  - 2025-01-09: Holocene EIP-1559 params, denominator 250 and elasticity 6, gas limit 30M.
  - **2025-12-02**: Jovian v1 extraData appears, with min base fee 0. This is 4 days after L2BEAT's 2025-11-28 Jovian date, which may be the L1-side upgrade date.
  - **2026-01-09**: gas limit raised to **60M** and elasticity to **12**.
  - **2026-01-21**: **minimum base fee = 500,000 wei (0.0005 gwei)**.
  - Current extraData is `0x01000000fa0000000c000000000007a120`. — [own RPC measurement](https://mainnet.unichain.org)
- Karst (OP Upgrade 19) brings Osaka EIPs on L2, promotes kona-client to primary fault-proof program, and adds an L2 Contract Manager. op-geth/op-program do **not** support Karst, so node operators must migrate to op-reth. — [Optimism Upgrade 19 notice](https://docs.optimism.io/notices/upgrade-19); [Optimism gov: Upgrade 19b Karst](https://gov.optimism.io/t/upgrade-19b-karst-hardfork/10713)
- **OP Enterprise migration** (post dated 2026-10-09):
  - Dates: testnet migrates **Oct 13**, mainnet **Oct 29, 2026**. Optimism will run "sequencers on mainnet and testnet, RPC, monitoring, and incident response."
  - Unchanged, per the post: chain ID, contracts, balances, and v2/v3/v4 deployments. Unichain remains Stage 1 with permissionless fault proofs, and upgrades stay under Optimism Governance and the Security Council. The stated purpose is "to prepare for native interoperability across the OP Stack," starting with ETH.
  - Not mentioned: Flashblocks, the TEE builder, revert protection, downtime, or integrator actions. — [Uniswap blog: Unichain is Upgrading to OP Enterprise](https://blog.uniswap.org/unichain-is-upgrading-to-op-enterprise)
- Rollup security today:
  - Stage 1, with permissionless proposing (0.08 ETH stake per root).
  - Challenge period 3d12h plus a 3d12h execution delay.
  - Forced inclusion via L1 with up to 12 h delay.
  - **No exit window** for Security Council upgrades.
  - L2BEAT flags that "the operator could front-run user transactions." — [L2BEAT Unichain](https://l2beat.com/scaling/projects/unichain)
- UVN: announced with 65% of net chain revenue to UNI-staked validators, piloted first on a testnet ([Uniswap Foundation](https://uniswapfoundation.org/blog/growing-defi-with-unichain)). A third-party risk report updated 2026-08-01 says UVN was "not live on mainnet as of August 2026" ([Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)). No later confirmation was found.
- Hindenrank also states that Uniswap Labs holds "unilateral upgrade authority." This conflicts with the Uniswap blog and L2BEAT, which both say upgrades require the Security Council/Optimism governance. — [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work) vs [L2BEAT](https://l2beat.com/scaling/projects/unichain)

### Inferences
- For an LP, the relevant "block" for arbitrage is the ~200 ms Flashblock, not the 1 s block. Within a Flashblock, the highest priority fee wins. Across Flashblocks, arrival time wins.
- Hooks that read `block.number` or `block.timestamp` to decide staleness or epochs see 1 s granularity. Up to ~4 user-bearing Flashblocks share the same `block.timestamp`, so a hook that throttles "once per block" allows several trades per 200 ms sub-slot sequence.
- The ~2× load in the first user gap likely reflects transactions queued during the final and deposit Flashblocks of the previous block. Latency-sensitive arbitrage therefore probably clusters at the start of each block. This is an inference from the segment counts and was not tested further.
- OP Enterprise (Oct 29) is the main near-term operational risk for anyone depending on public RPC behavior or Flashblocks/bundle endpoints. The announcement promises no continuity for those features.

### Gaps
- No primary source found on whether Flashblocks, the TEE builder, `eth_sendBundle` and revert protection continue unchanged after Optimism takes over sequencing on 2026-10-29.
- No primary source on formal Flashblock preconfirmation guarantees (e.g., reorg probability, slashing).
- UVN status after August 2026 is unconfirmed.
- I could not determine why user transactions never appear after the 5th FlashblockNumber call. Whether the last 200 ms slot is reserved or empty would need op-rbuilder source code.

---

## MEV environment: sandwiching, arbitrage competition, revert behavior, bundles, MEV data

### Takeaway
Unichain has no public mempool and orders by priority fee per Flashblock inside a TEE, so third-party sandwiching is structurally hard. MEV is overwhelmingly arbitrage, competed for with latency and modest priority fees rather than spam. `eth_sendBundle` exists but is **single-transaction only**: it gives revert protection and block or time windows, not atomic backruns. Ordinary transactions that revert still land and pay; 5.1% of non-builder transactions failed in today's sample. No public MEV-share dataset specific to Unichain was found.

### Cited Findings
- Bundles (`eth_sendBundle`, posted 2025-07-09):
  - The first iteration is "limited to single transactions to enforce priority fee ordering."
  - Bundles stay active for up to 10 blocks or until max block/timestamp.
  - Revert protection "prevents paying gas if opportunity disappears." — [Flashbots Collective: Bundles Are Coming to Unichain](https://collective.flashbots.net/t/bundles-are-coming-to-unichain/5072)
- Current docs:
  - `eth_sendBundle` is sent to `https://mainnet.unichain.org` and takes params `txs` (exactly one), `minBlockNumber`/`maxBlockNumber` *or* `minTimestamp`/`maxTimestamp`, and `revertingTxHashes`.
  - "If `revertingTxHashes` is omitted, reverted transactions do not charge gas fees."
  - Bundles cannot be cancelled. The default lifetime is 10 blocks, and an expired bundle returns `-32602`. — [Unichain docs: advanced transactions](https://developers.uniswap.org/docs/unichain/technical-information/advanced-txn)
- Public RPC method checks on 2026-10-13: `eth_sendBundle` is accepted (a malformed probe returned "typed transaction too short"). `eth_sendRawTransactionSync` and `web3_clientVersion` return "rpc method is not whitelisted." — [own RPC measurement](https://mainnet.unichain.org)
- Today's activity mix (30-minute sample, non-builder transactions only):
  - **489 transactions (0.27 tx/s ≈ 23.5k/day)**. **25 failed (5.1%)**, concentrated in unverified bot contracts such as `0x9b5ab606…`, `0x2cc4fcb2…` and `0xbc728c14…`. Failed transactions' median tip was 0.001075 gwei.
  - Of 286 successful single-v4-swap transactions, 153 (53.5%) went through Universal Router `0xef74…` and **133 (46.5%) through other contracts**. Top non-router contract: `0x099b1a87…` (74), which uses 68-byte calldata from multiple EOAs, typical of arbitrage bots.
  - v3 single swaps were dominated by `0x389ea624…` (27 of 44), which pays a 1-wei tip.
  - Tips: 18.4% of non-builder transactions pay ≤1 wei. Median tip 0.00145 gwei, p90 0.004 gwei, max 0.1 gwei.
  - Whole sample: 345 v4 Swap events, 55 v3, 3 v2 (≈16.6k v4 swaps/day). — [own RPC measurement](https://mainnet.unichain.org)
- Academic measurement (Jan–Aug 2025):
  - Unichain revert rates "rose sharply in mid-May and stayed close to 40% until July" 2025. >80% of reverted transactions are swaps, and >90% of reverted swaps target Uniswap v4.
  - "Nearly all reverted transactions on Unichain set the priority fee to exactly 1 wei." Unichain reverts peak around the 4th block position.
  - Reverted transactions generate roughly 20–25% of priority-fee revenue on Base and Unichain.
  - Bots generally duplicate transactions and rely on speed rather than bidding priority fees. The authors derive that CEX-DEX arbitrageurs should split trades on fast-finality chains. — [arXiv:2506.01462v4](https://arxiv.org/html/2506.01462v4)
- Uniswap says priority ordering "supports value-capture mechanisms like MEV taxes, returning value to users rather than searchers." — [Uniswap blog, Flashblocks are live](https://blog.uniswap.org/flashblocks-are-live). The MEV-tax mechanism lets an app charge a fee that increases in the transaction's priority fee, capturing competitive arbitrage rents under priority ordering. — [Paradigm, "Priority Is All You Need"](https://www.paradigm.xyz/2024/06/priority-is-all-you-need)
- The arXiv paper classifies Unichain as a "private mempool" chain with priority-fee-auction order flow. — [arXiv:2506.01462v4](https://arxiv.org/html/2506.01462v4). L2BEAT still notes the centralized operator "could front-run user transactions." — [L2BEAT](https://l2beat.com/scaling/projects/unichain)
- Monthly maximum 99th-percentile tips in the 6-hourly fee-history samples show rare extreme bids: 761 gwei (Sep 2025), 577 gwei (Jul 2026), and 7–90 gwei in most 2026 months. Monthly *median* tips were ≈0 in 2026. — [own RPC measurement](https://mainnet.unichain.org)

### Inferences
- **Sandwiching by third parties is effectively prevented** because there is no public mempool and ordering is enforced by the TEE builder. The residual risk is the operator or TEE trust assumption (Intel TDX per Hindenrank). After 2026-10-29 that operator becomes Optimism.
- **Atomic backrunning is not available.** Bundles are single-transaction, so an arbitrageur cannot attach to a victim transaction. LP adverse selection on Unichain therefore comes mostly from latency arbitrage after external price moves, competing on arrival time across Flashblocks and on tip within a Flashblock.
- For a stable pair this competition is mild. Tips cluster near 0.00145 gwei (the wallet default) or 1 wei.
- A v4 hook can implement an MEV tax by reading `tx.gasprice − block.basefee` in `beforeSwap`. This is attractive on Unichain because ordering is priority-based per Flashblock. It is a design opportunity for PegGuard, not something observed live.
- Revert spam is not a cost to LPs, but it does mean some failed arbitrage attempts are visible on-chain. The 5% failure rate is far below the ~40% of mid-2025, consistent with lower incentive-era activity.

### Gaps
- No public Dune or other dashboard was found that quantifies arbitrage/MEV share of Unichain DEX volume, sandwich counts, or backrun-auction revenue. MEV-Share-style backrun auctions or BuilderNet do not appear to be offered on Unichain; none were found.
- The bot contract identities (e.g., `0x099b1a87…`) are unverified on Blockscout.

---

## Theory link: fast blocks, fees and LVR/arbitrage for a stable pair

### Takeaway
In Milionis–Moallemi–Roughgarden's model with fees, the probability that a block carries an arbitrage trade is P_trade = 1/(1 + √(2/Δt)·γ/σ). In the fast-block regime, arbitrage profit ≈ LVR × P_trade, which scales with √Δt·σ³/γ. For a stable pair (σ of a few bp/day) with a 1 bp fee, P_trade at Unichain's 1 s blocks is ≈0.7%, falling to ≈0.3% if arbitrage can act every 200 ms Flashblock. Diffusive arbitrage losses are therefore tiny. Stable-pair LP risk is dominated by **jumps/depegs**, which faster blocks do not mitigate, and by competition for uninformed flow.

### Cited Findings
- The paper is "Automated Market Making and Arbitrage Profits in the Presence of Fees" by Milionis, Moallemi and Roughgarden (v1 2023-05-24, v2 revised 2025-07-23). Main results:
  - Theorem 1: P_trade = 1/(1 + √(2λ)γ/σ), with λ = blocks per second.
  - Fast-block asymptotic: ARB ≈ LVR × P_trade, and ARB = Θ(√(1/λ)) when γ>0 versus Θ(1) when γ=0.
  - "Faster blockchains will result in reduced LP losses."
  - Section 6 adds fixed gas costs δ, which widen the no-trade region to γ+δ.
  - Table 1 (σ=5%/day): P_trade = 45.6% (12 s, 5 bp) vs 25.4% (2 s, 5 bp). — [arXiv:2305.14604 abstract](https://arxiv.org/abs/2305.14604); [arXiv HTML v2](https://arxiv.org/html/2305.14604v2)
- Uniswap Labs research claims "full-range LPs on faster chains earn around 20% more in arbitrage-adjusted returns than on Ethereum Mainnet." This is vendor research. An earlier version predates EIP-4844. — [Uniswap blog, "Beyond speed" (2025-05-04)](https://blog.uniswap.org/beyond-speed-building-for-efficient-onchain-markets); [Uniswap blog, "Layer 2 Be or Layer Not 2 Be"](https://blog.uniswap.org/layer-2-be-or-layer-not-2-be)
- Researcher's computation with the Theorem 1 formula (`calc.py`). The formula reproduces the paper's Table 1 values (45.5% vs 45.6%; 25.4%; 12.2% vs 12.3%). σ values below are **scenario assumptions, not measurements**. P_trade by venue:

| σ (daily) | fee γ | Ethereum 12 s | Base/OP 2 s | Unichain 1 s | Arbitrum 0.25 s | Unichain Flashblock 0.2 s |
|---|---|---|---|---|---|---|
| 1 bp | 1 bp | 0.83% | 0.34% | 0.24% | 0.12% | 0.11% |
| 3 bp | 0.5 bp | 4.76% | 2.00% | 1.42% | 0.72% | 0.64% |
| 3 bp | 1 bp | 2.44% | 1.01% | **0.72%** | 0.36% | **0.32%** |
| 3 bp | 5 bp | 0.50% | 0.20% | 0.14% | 0.07% | 0.06% |
| 10 bp | 1 bp | 7.69% | 3.29% | 2.35% | 1.19% | 1.06% |
| 50 bp (stress) | 1 bp | 29.4% | 14.5% | 10.7% | 5.7% | 5.1% |
| 50 bp (stress) | 5 bp | 7.69% | 3.29% | 2.35% | 1.19% | 1.06% |

- Ratios at σ=3 bp/day and γ=1 bp: Unichain 1 s / Base 2 s = 0.709, and Flashblock 0.2 s / 1 s = 0.449. — [computation](https://arxiv.org/html/2305.14604v2)
- The gas threshold δ is negligible on Unichain. An all-in v4 swap costs ≈$0.0007 (see the Costs section), so for a $10k arbitrage δ ≈ 0.0007 bp, compared with ≈0.1 bp for a $0.11 Ethereum swap ([growthepie fee table](https://api.growthepie.com/v1/fees/table.json), 2026-10-13 17:00 UTC). — [own computation](https://mainnet.unichain.org)

### Inferences
- With η = γ/(σ√(Δt/2)) ≫ 1 (η≈139 at σ=3 bp/day, γ=1 bp, Δt=1 s), arbitrageurs trade in <1% of blocks. LP *arbitrage* losses are ≈LVR×0.7%. LVR itself is tiny for σ of a few bp/day, but concentrated stable liquidity amplifies it in proportion to depth.
- Moving the same pool from Base (2 s) to Unichain (1 s) cuts modeled ARB by ~29%. Flashblocks would cut it a further ~55% *if* arbitrageurs effectively re-quote every 200 ms.
- Model limits for stables:
  - Stable-pair "true" prices are mean-reverting and quoted in 1 bp CEX ticks, the same order as γ, so the GBM/diffusion assumption is weak.
  - Real adverse selection concentrates in rare jumps (depeg, issuer news, CEX dislocations), where the full jump is taken in the next Flashblock regardless of block time.
  - So faster blocks help the *diffusive* component, which is already negligible, but not jump risk. That favors PegGuard-style oracle-gated dynamic fees, i.e. raising γ during jumps, over relying on block speed.
- Fees paid by arbitrageurs are also proportional to P_trade, so the fee *income* from arbitrage flow is equally small. A stable-pair LP's revenue on Unichain depends on uninformed (router) flow, which is currently thin (see the Activity section).

### Gaps
- No measured USDC/USDT or USDC/USDT0 volatility on Unichain or CEX was gathered here, so σ is scenario-based.
- No empirical Unichain-specific LVR/markout study for stable pools was found.

---

## Costs: gas prices, L1 data fee, per-operation USD costs, Pyth update cost — and correction of repo assumptions

### Takeaway
Unichain gas is at a **0.0005 gwei base-fee floor**, set by a Jovian min-base-fee parameter since 2026-01-21. The chain is ~1% utilized (60M gas limit), and wallets pay ≈0.00195 gwei effective. A plain v4 swap costs ≈150k gas ≈ **$0.0007**, and the L1 data fee is only ~1% of that.
The repo's assumptions are off in four ways:
- "Unichain low 0.005 gwei" is ~2.6× the typical paid price and 10× the floor.
- "Stressed 0.05 gwei" has never been approached by the base fee (max sampled 0.00255 gwei, Jun 2025).
- ETH is $2,499, not $3,500.
- **`PYTH_UPDATE_GAS = 90,000` is ~2× too low.** A single-feed Pyth `updatePriceFeeds` on Unichain costs ≈195k gas standalone, or ≈174k incremental inside a swap.
The gas and ETH errors roughly cancel in USD terms.

### Cited Findings
**Live gas (2026-10-13)**
- Point readings:
  - `eth_gasPrice` = 1,500,000 wei (**0.0015 gwei**) and `eth_maxPriorityFeePerGas` = 1,000,000 wei (0.001 gwei).
  - Latest `baseFeePerGas` = 500,000 wei (**0.0005 gwei**), gasLimit 60,000,000.
- Last 1,024 blocks (`eth_feeHistory`):
  - Base fee min = median = max = 0.0005 gwei.
  - Mean gasUsedRatio 1.08% (max 2.9%).
  - Reward percentiles: median over blocks 0 at every percentile (p10–p99); max 0.1 gwei.
- 30-minute sample, single v4 swaps via Universal Router (n=153):
  - Median gasUsed **150,610**.
  - Effective gas price **0.00195 gwei** (tip 0.00145 gwei). This is the dominant wallet default, set for p10–p90.
  - Median total fee **2.96e-7 ETH ≈ $0.00074**, of which L1 data fee is 2.29e-9 ETH (**0.8%**).
- Other cohorts in the same sample:
  - Non-router single v4 swaps: median 142,879 gas at 0.00189 gwei.
  - v3 single swaps: median 118,578 gas.
  - All successful non-builder transactions: median total fee 2.77e-7 ETH. — [own RPC measurement](https://mainnet.unichain.org)
- The builder system transactions use ≈566k gas per block (5×94,258 + 73,120 + 21,880), about 88% of current gas used. — [own RPC measurement](https://mainnet.unichain.org)

**L1 data fee component (OP Stack Fjord/Isthmus/Jovian formula, live 2026-10-13)**
- Oracle readings:
  - GasPriceOracle v1.6.0 reports `isFjord`/`isEcotone`/`isIsthmus`/`isJovian` all true.
  - l1BaseFee 0.1303 gwei, blobBaseFee 0.00807 gwei, baseFeeScalar 2,000, blobBaseFeeScalar 900,000.
  - Operator fee scalar and constant are 0, so `getOperatorFee` returns 0.
  - L1Block `daFootprintGasScalar` = 400.
- Upper-bound fee by transaction size:
  - `getL1FeeUpperBound`: 400 bytes → 4.15e-9 ETH; 1,000 bytes → 9.9e-9 ETH; 1,500 bytes → 1.47e-8 ETH.
  - Formula check: fastlz size 300 → 2.38e-9 ETH, which matches observed swap L1 fees of ~2.0–2.3e-9 ETH. — [own RPC measurement of 0x420…000F/0x420…0015](https://mainnet.unichain.org)

**Base-fee history since launch (6-hourly 1,024-block windows, 2,832 windows)**
- Most of 2025: base fee effectively ~0 (wei-level).
- Brief rises in **Jun–Jul 2025** during the incentive peak, with gasUsedRatio ~16% (window max base fee **0.00255 gwei** on 2025-06-18).
- Since 2026-01-21 the base fee is pinned at **0.0005 gwei**. The highest 2026 window was 0.00224 gwei (2026-01-26).
- **No window ever exceeded 0.005 gwei.** — [own RPC measurement](https://mainnet.unichain.org)

**Cross-chain comparison (growthepie hourly, 2026-10-13 17:00 UTC)**

| Chain | Median tx | Swap | Other |
|---|---|---|---|
| Unichain | $0.0001 | $0.0007 | TPS 7.44 |
| Base | $0.0015 | $0.0035 | |
| Arbitrum | $0.0045 | $0.0123 | |
| OP Mainnet | ≈$0.0000 | ≈$0.0000 (rounded) | |
| Ethereum | $0.0388 | $0.1129 | |

Source: [growthepie fees API](https://api.growthepie.com/v1/fees/table.json) ([growthepie fees page](https://www.growthepie.com/fees)). Uniswap's Aug 2025 claim was gas "often under a cent." — [Uniswap blog](https://blog.uniswap.org/flashblocks-are-live)

**LP operations (v4, last ~300k blocks ≈3.5 days to block 61,169,043; median gasUsed)**

| Operation | Median gas | Range | n |
|---|---|---|---|
| Mint via PositionManager | 243,259 | 207k–402k | 81 |
| increaseLiquidity | 179,472 | | 16 |
| decreaseLiquidity | 138,330 | | 94 |
| collect (liquidityDelta=0) | 125,490 | | 36 |
| burn | 107,729 | | 16 |

- Two unverified "Admin" contracts from the same deployer (`0x94d026e7…`, `0xc91ed9c2…`) run 26–58 ModifyLiquidity calls per transaction at ≈2–4.2M gas, i.e. active multi-position LP managers.
- There were 16,378 ModifyLiquidity events in the window. — [own RPC measurement](https://mainnet.unichain.org)

**Pyth on Unichain**
- Contract `0x2880aB155794e7179c9eE2e38200202908C17B43` is the same address on mainnet and Sepolia. Unichain was **not** in the list of EVM deployments auto-upgraded by the DAO on 2026-08-26. — [Pyth EVM contract addresses](https://docs.pyth.network/price-feeds/core/contract-addresses/evm)
- On-chain state on 2026-10-13: `version()` = 1.4.6, `singleUpdateFeeInWei()` = **0**, `validTimePeriodSeconds()` = 60. The fee was 1 wei at block 26,065,676 (Sep 2025). — [own RPC measurement](https://mainnet.unichain.org)
- **Stale on-chain prices:** USDC/USD and USDT/USD were last updated 2025-09-02, ≈406 days ago. ETH/USD was last updated 2026-07-02 at $1,618, ≈103 days ago. **Zero `PriceFeedUpdate` events** occurred in the 300k blocks to 61,168,229. — [own RPC measurement](https://mainnet.unichain.org)
- **Measured Pyth update gas.** The last USDC/USDT update transaction (2025-09-02) was a 7-feed `updatePriceFeedsIfNecessary` that used 357,439 gas, with 4,132 calldata bytes and an L1 fee of 2.06e-8 ETH. Re-encoding its accumulator payload and running `eth_estimateGas` at the parent block gives the per-feed costs below, i.e. **~168.6k fixed (VAA verification) + ~26.6k per feed**. — [own RPC measurement](https://mainnet.unichain.org)

| `updatePriceFeeds` call | Calldata (bytes) | Gas |
|---|---|---|
| 1 feed | 1,444 | **195,193** |
| 2 feeds | 1,796 | 221,830 |
| 3 feeds | 2,148 | 248,372 |
| 7 feeds | 3,556 | 358,717 |
| 1 feed, price already fresh (no storage write) | | 184,636 |

- Third-party contract `0x493dc0e3…` updated ETH/USD in July 2026 through its own wrapper at 261k–400k gas, paying 0.000204 ETH in that app's own fee. — [own RPC measurement](https://mainnet.unichain.org)
- **Hermes requires an API key** since the Pyth Core upgrade completed 2026-08-26 16:00 UTC. The header is `Authorization: Bearer $PYTH_API_KEY`, and early adopters can switch to `pyth.dourolabs.app/hermes`. — [Pyth Core upgrade guide](https://docs.pyth.network/price-feeds/core/upgrade/preparing). The researcher's unauthenticated request to `hermes.pyth.network/v2/updates/price/latest` returned HTTP 401 "unauthorized" on 2026-10-13. — own test

**Repo assumptions vs reality** (from `shadow/chain_cost_report.py` and `shadow/live_gas_snapshot_report.py`)
- Gas-price inputs:
  - Repo "Unichain low" 0.005 gwei vs observed floor 0.0005 gwei and typical paid 0.00195 gwei.
  - Repo "stressed" 0.050 gwei vs max sampled base fee 0.00255 gwei.
  - Repo ETH $3,500 vs $2,499.
  - Repo `live_gas_snapshot_report` uses `eth_gasPrice`, which returns 0.0015 gwei: the floor plus a 0.001 gwei suggested tip.
- Gas-quantity inputs: repo `HOOK_GAS` = 52,699 + 84,925 (from `docs/gas_snapshot.md`) plus `PYTH_UPDATE_GAS` 90,000 vs measured ≈174k (in-hook) / 195k (standalone). — [own RPC measurement](https://mainnet.unichain.org)
- USD per operation at ETH $2,499, L2 execution only (`calc.py`). Add ≈$0.000005 L1 fee for a swap and ≈$0.00003–0.00005 for a 1.4–2 KB Pyth payload.

| Operation | Gas | 0.0005 gwei (floor) | 0.00195 gwei (typical) | 0.005 (repo low) | 0.05 (repo stressed) |
|---|---|---|---|---|---|
| v4 swap, no hook | 150,610 | $0.00019 | $0.00073 | $0.00188 | $0.0188 |
| v4 swap + PegGuard hook (repo-measured 137.6k) | 288,234 | $0.00036 | $0.00140 | $0.00360 | $0.0360 |
| … + in-hook Pyth 1-feed update (≈+174k) | 462,234 | $0.00058 | $0.00225 | $0.00578 | $0.0578 |
| Standalone Pyth update, 1 feed | 195,193 | $0.00024 | $0.00095 | $0.00244 | $0.0244 |
| v4 mint | 243,259 | $0.00030 | $0.00119 | $0.00304 | $0.0304 |
| v4 decrease / collect | 138k / 125k | $0.00017 / $0.00016 | $0.00067 / $0.00061 | — | — |
| ~45-position rebalance | ~3.9M | $0.0049 | $0.0190 | $0.0487 | $0.487 |

- All-in hook+Pyth swap cost at 0.00195 gwei = 0.225 bp of a $100 swap, 0.023 bp of $1k, 0.002 bp of $10k. At 0.05 gwei: 5.8 / 0.58 / 0.058 bp. — [computation](https://mainnet.unichain.org)
- The repo's per-swap hook+Pyth USD cost (227,624 gas at $3,500) comes out within ~3% of the corrected figure (311,624 gas at $2,499) at any given gwei. The two errors offset. — [computation](https://mainnet.unichain.org)

### Inferences
- Recommended re-calibration for the PegGuard cost scripts (inference, not a source claim):
  - Unichain "low" = 0.0005–0.002 gwei. A *base-fee* stress of 0.05 gwei is far outside history.
  - EIP-1559 math with denominator 250 and elasticity 12 gives a max +4.4% per 1 s block. Reaching 0.05 gwei from 0.0005 requires ~107 consecutive full 60M-gas blocks, while current usage is ~0.65M gas/block against a 5M target.
  - A tip-driven stress for urgent transactions of 0.01–0.1 gwei is plausible.
  - Set `PYTH_UPDATE_GAS` ≈ 175k (in-hook, 1 feed), plus ≈27k per additional feed.
  - Re-measure on the current Pyth contract (v1.4.6, not auto-upgraded) once a Hermes API key is available.
  - Use live ETH/USD rather than a static $3,500.
- Because the swapper pays gas, PegGuard's chain cost is mostly a **routing-competitiveness** issue: aggregators see a pool whose swaps cost ~3× more gas than a no-hook pool. It is not an LP cost.
- At ~$0.002 per swap this matters only for retail-sized swaps (<$1k) competing against 0.5–1 bp stable pools.
- On-chain Pyth feeds on Unichain are effectively unused: no updates in ≥3.5 days, and stablecoin feeds ~13 months stale. PegGuard must push its own update with every swap (pull model) or run a keeper, and must budget a Hermes API key. Relying on someone else's fresh price is not possible.

### Gaps
- Single-feed Pyth update gas was estimated on Sept-2025 contract state and payload format. It has not been re-verified on the post-2026-08-26 Pyth Core backend or current contract.
- The v4 LP gas figures are for whatever pools users touched, with mixed hooks and tick ranges, not for PegGuard's hook specifically.
- L2BEAT's cost-per-operation figure was not captured.
- The Hermes API key pricing tier is not public in the docs read.

---

## Infrastructure: Uniswap contract addresses, RPC/WS/Flashblocks endpoints, log limits, indexers

### Takeaway
Official Uniswap v4 and v3 addresses on Unichain are confirmed by docs and by on-chain bytecode checks. The public RPC is fine for light reads but unsuitable for production. It caps `eth_getLogs` at ~10k blocks, returned inconsistent results, has a **stale `pending` tag** (so no usable Flashblocks view), and does not whitelist several methods. Use a Flashblocks-aware provider (Alchemy, QuickNode) or your own `node-reth` subscribed to the Flashblocks WebSocket. After Oct 29 the public endpoints will be operated by Optimism.

### Cited Findings
- **Uniswap v4 (Unichain, chain 130)**:

| Contract | Address |
|---|---|
| PoolManager | `0x1f98400000000000000000000000000000000004` |
| PositionManager | `0x4529a01c7a0410167c5740c487a8de60232617bf` |
| StateView | `0x86e8631a016f9068c3f085faf484ee3f5fdee8f2` |
| Quoter (V4Quoter) | `0x333e3c607b141b18ff6de9f258db6e77fe7491e0` |
| PositionDescriptor | `0x9fb28449a191cd8c03a1b7abfb0f5996ecf7f722` |
| ReservesLens | `0x0000001b173C3bbF3984D417d8614E3eed34865B` |
| Universal Router | `0xef740bf23acae26f6492b10de645d6b98dc8eaf3` |
| Universal Router 2.1.1 | `0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7` |
| Universal Router 2.1.2 | `0xD1b797D92d87B688193A2B976eFc8D577D204343` |
| Permit2 | `0x000000000022D473030F116dDEE9F6B43aC78BA3` |

  - Docs also list PoolManager on Base (`0x498581ff…2b2b`) and Ethereum (`0x000000000004444c…8A90`). — [Uniswap v4 deployments](https://developers.uniswap.org/docs/protocols/v4/deployments)
  - Bytecode confirmed present on 2026-10-13: PoolManager 24,050 B, PositionManager 23,877 B, StateView 3,531 B, Quoter 5,820 B, Universal Router `0xef74…` 19,499 B, Permit2 9,152 B. Universal Router 2.1.2 `0xd1b7…` was seen as a transaction target in the sample. Code checks for 2.1.1 and ReservesLens were not run. — [own RPC measurement](https://mainnet.unichain.org)
- **Uniswap v3 (Unichain)**:

| Contract | Address |
|---|---|
| UniswapV3Factory | `0x1f98400000000000000000000000000000000003` |
| NonfungiblePositionManager | `0x943e6e07a7e8e791dafc44083e54041d743c46e9` |
| SwapRouter02 | `0x73855d06de49d0fe4a9c42636ba96c62da12ff9c` |
| QuoterV2 | `0x385a5cf5f83e99f7bb2852b6a19c3538b9fa7658` |
| TickLens | `0xd5d76fa166ab8d8ad4c9f61aaa81457b66cbe443` |
| UniswapInterfaceMulticall | `0xb7610f9b733e7d45184be3a1bc966960ccc54f0b` |
| V3Migrator | `0xb9d0c246f306b1aaf02ae6ba112d5ef25e5b60dc` |
| WETH | `0x4200000000000000000000000000000000000006` |

  - The explorer is uniscan.xyz. — [Uniswap v3 Unichain deployments](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-unichain-deployments)
  - The v2 factory at `0x1f98…0002` has bytecode (13,859 B). — [own RPC measurement](https://mainnet.unichain.org)
- **Stablecoins (on-chain, 2026-10-13)**:
  - Native USDC `0x078D782b760474a361dDA0AF3839290b0EF57AD6`: symbol "USDC", totalSupply 19,998,245.66.
  - USDT0 `0x9151434b16b9763660705744891fA906F660EcC5`: symbol "USD₮0", totalSupply 7,595,959.02. — [own RPC measurement](https://mainnet.unichain.org)
- **L1 contracts**: OptimismPortal `0x0bd48f6B86a26D3a217d0Fa6FfE2B491B956A7a2` and DisputeGameFactory `0x2F12d621a16e2d3285929C9996f478508951dFe4`. — [Unichain docs: submitting transactions from L1](https://developers.uniswap.org/docs/unichain/technical-information/submitting-transactions-from-l1)
- **Endpoints**: HTTP `https://mainnet.unichain.org`, which is rate-limited and for development use. Flashblocks WebSocket `wss://mainnet-flashblocks.unichain.org/ws`. Production providers: [Alchemy Flashblocks quickstart](https://www.alchemy.com/docs/reference/unichain-flashblocks-api-quickstart) and [QuickNode Flashblocks](https://www.quicknode.com/docs/Unichain/flashblocks/overview). — [Unichain docs: Flashblocks](https://developers.uniswap.org/docs/unichain/technical-information/flashblocks)
- **Public RPC behavior (2026-10-13)**:
  - `eth_getLogs` on PoolManager Swap: ranges of 2,000, 5,000, 9,999, 10,000 and 10,001 blocks succeeded consistently (400 / 1,513 / 3,081 / 3,081 / 3,084 logs). 20,000+ blocks returned **HTTP 400**.
  - Once, a 10,000-block query returned **0 logs** where a near-identical query minutes earlier returned 3,248, so results can be silently inconsistent across backends.
  - `eth_getBlockByNumber("pending")` returned blocks **59,441,607 and 60,492,312** (≈20 and ≈8 days old) while latest was 61,168,853. The public load-balanced RPC's `pending` is therefore **not** a usable Flashblocks preconfirmation view.
  - Historical state at block ~26M (Sep 2025) was served for `eth_call` and `eth_estimateGas`, i.e. archive-capable. — [own RPC measurement](https://mainnet.unichain.org)
- **Indexers/explorers**: the Blockscout API at `unichain.blockscout.com/api/v2` works (address metadata retrieved), and uniscan.xyz is linked in the docs. — [Blockscout](https://unichain.blockscout.com/address/0x3c3a8a41e095c76b03f79f70955fff3b03cf753e); [Uniswap v3 Unichain deployments](https://developers.uniswap.org/docs/protocols/v3/deployments/v3-unichain-deployments)
- Uniswap Labs' own stable-pair hook, **StablePair**, launched 2026-09-10 on **Ethereum mainnet only** (USDC/USDG and USDC/USDT). It is a v4 dynamic-fee hook that quotes a fixed spread around a reference rate. Outside the band, trades that push the price further pay no fee, and corrective trades go through a per-block Dutch auction. It is upgradeable via governance. No Unichain deployment was announced. — [Uniswap blog: StablePair Hook](https://blog.uniswap.org/stablepair-hook-a-fee-that-moves-with-the-market); [The Block](https://theblock.co/news/defi/2026-09-10-uniswap-stablepair-hook-414160)

### Inferences
- PegGuard's monitoring and backfills should not depend on the public RPC. Page `eth_getLogs` in ≤10k-block chunks and cross-check counts, or use a provider or own node.
- Any Flashblocks-aware quoting, e.g. reading preconfirmed pool state at `pending`, needs `node-reth` with the WebSocket feed or a provider that documents Flashblocks support.
- StablePair is the most direct competitor design to PegGuard. If Uniswap Labs deploys it to Unichain, PegGuard would compete against a first-party stable hook for the same router flow.

### Gaps
- The Unichain docs pages for network information, RPC rate limits, data indexers (subgraph/Goldsky/etc.) and node providers could not be retrieved. The site returned Cloudflare 1015/429 rate limits. Official subgraph IDs and documented getLogs/archive limits for Alchemy and QuickNode on Unichain are therefore not captured.
- The researcher did not test the Flashblocks WebSocket directly. The stdlib-only environment has no WebSocket client.

---

## Inventory logistics for a stable MM: bridging/rebalancing latency and cost

### Takeaway
USDC is the easiest inventory to move. CCTP v2 Fast Transfer out of Unichain takes ~8 s at **2 bp**; into Unichain it costs 1–1.4 bp depending on source. Standard transfer is free but takes ~15–19 min. The canonical OP bridge withdrawal still takes **7 days**. USDT0 moves via LayerZero OFT, but Unichain-specific latency and fee data were not found. Native Superchain interop is **not live**. Only Coinbase is confirmed as a CEX supporting Unichain USDC directly.

### Cited Findings
- CCTP v2:
  - Unichain is domain **10** and supports CCTP v2 including Fast Transfer.
  - Fast Transfer attestation from Unichain needs 1 block confirmation (~8 s). Standard Transfer from Unichain needs ~65 ETH blocks (~15–19 min).
  - Standard transfers are free. Fast Transfer fees range from 0 to 13–14 bp by source chain, deducted at mint or optionally paid upfront. Fast transfers are capped by a global Fast Transfer allowance, and a `maxFee` set too low degrades to Standard. — [Circle: supported chains & domains](https://developers.circle.com/cctp/concepts/supported-chains-and-domains); [Circle: finality & block confirmations](https://developers.circle.com/cctp/concepts/finality-and-block-confirmations); [Circle: CCTP fees](https://developers.circle.com/cctp/concepts/fees)
- Live Iris fee API (2026-10-13), minimum fee at `finalityThreshold` 1000 (fast); every route below is 0 bp at 2000 (standard). — [Circle Iris API 10→0](https://iris-api.circle.com/v2/burn/USDC/fees/10/0); [0→10](https://iris-api.circle.com/v2/burn/USDC/fees/0/10)

| Route | Fast fee |
|---|---|
| Unichain → Ethereum / Base / Arbitrum | **2 bp** each |
| Ethereum → Unichain | **1 bp** |
| Base → Unichain | **1.3 bp** |
| Arbitrum → Unichain | **1.4 bp** |

- Canonical bridge withdrawal: initiate on L2, prove after an output is proposed (≈1 h), then finalize "no sooner than 7 days after" because of the challenge period. — [Unichain docs: submitting transactions from L1](https://developers.uniswap.org/docs/unichain/technical-information/submitting-transactions-from-l1). L2BEAT lists a 3d12h challenge period plus a 3d12h execution delay. — [L2BEAT](https://l2beat.com/scaling/projects/unichain)
- Native Superchain interop:
  - Unichain's move to OP Enterprise is "to prepare for native interoperability across the OP Stack." Once live, users can move assets "starting with ETH" without a bridge. — [Uniswap blog, 2026-10-09](https://blog.uniswap.org/unichain-is-upgrading-to-op-enterprise)
  - Upgrade 20 (2026-09-24) moved Unichain's proofs to super roots. — [L2BEAT](https://l2beat.com/scaling/projects/unichain)
  - The original OP Labs roadmap promised sub-2-second cross-chain asset access but has slipped from 2025. — [OP Labs interop post](https://blog.oplabs.co/solving-interoperability-for-the-superchain-and-beyond)
  - USDT0 was presented in March 2025 as an interoperable Superchain asset, at token level via LayerZero OFT. — [Optimism blog](https://www.optimism.io/blog/interoperable-superchain-assets-are-here-with-usdt0-leading-the-way)
- USDT0 on Unichain is a live OFT deployment: USD₮0 contract, supply ≈$7.6M on 2026-10-13. — [own RPC measurement](https://mainnet.unichain.org). Secondary guides list Unichain among USDT0 chains and say USDT0 is issued by Everdawn Labs under Tether license. These are low-reliability SEO sources. — [eco.com USDT0 explainer](https://eco.com/support/en/articles/15192015-what-is-usdt0-tether-s-omnichain-stablecoin-explained-2026)
- CEX: "Some prominent centralized exchanges, including Coinbase, support native USDC on Unichain" (usdc.com, Nov 2025). Native USDC circulation on Unichain was ">$50 million as of November 2025." — [usdc.com guide](https://www.usdc.com/learn/how-to-get-usdc-on-unichain). (Searches found no evidence either way on Kraken, Binance or OKX supporting Unichain; see Gaps.)
- Forced inclusion through L1 if the sequencer censors: up to 12 h. — [L2BEAT](https://l2beat.com/scaling/projects/unichain)

### Inferences
- A USDC/USDT0 MM on Unichain can rebalance USDC to and from Ethereum, Base or Arbitrum in seconds for ~2 bp (out) or 1–1.4 bp (in), or within ~20 minutes for free. The free path is fast enough for daily inventory rebalancing and makes 2 bp the ceiling on *urgent* cross-venue rebalancing cost.
- That is comparable to or larger than the 1 bp stable-pool fee. Inventory imbalance should be managed with on-chain fee skew (PegGuard's correcting-side discount) rather than frequent fast bridging.
- USDT0 legs depend on LayerZero OFT latency and fees, which are unquantified here, plus CEX support for USDT0-on-Unichain, which is unconfirmed. The USDT side of a USDC/USDT0 book is the harder inventory to recycle.
- Canonical 7-day withdrawals are irrelevant for stablecoin inventory given CCTP. They matter only for ETH gas balances, which are trivial at these gas prices.

### Gaps
- USDT0 (LayerZero OFT) Unichain transfer latency, fees and any rate limits were not found from primary sources.
- CEX direct deposit/withdrawal support for Unichain (USDC, USDT0) at Binance, OKX, Kraken and Bybit is unconfirmed, and Coinbase's support is only confirmed via a Nov-2025 Circle page.
- The Fast Transfer allowance size for Unichain is unknown.
- No date for native Superchain interop on Unichain.

---

## Unichain activity context: transactions, DEX volume, share of Uniswap, trends 2025–2026

### Takeaway
Unichain went from incentive-driven prominence in mid-2025 to a small chain in Oct 2026:
- At the May–Jul 2025 peak it carried ~$13B/month of DEX volume and up to 51.5% of Uniswap v4 volume, with TVL peaking at $903M.
- Now: ~$322M per 30 days of DEX volume (≈0.4% of Uniswap, 0.3% of v4), $26.8M DeFi TVL, ~$27M stablecoins, and ~23.5k organic transactions per day.
- Headline tx/TPS metrics are ~96% Flashblocks builder system transactions.

### Cited Findings
- **DefiLlama, fetched 2026-10-13**, Unichain DEX volume:
  - 24h $9.82M; 7d $54.67M; **30d $321.85M** (Uniswap V3 $192.78M, Uniswap V4 $122.27M, Velodrome V3 $6.75M, EulerSwap $0.06M); 1y $11.91B; all-time $77.52B.
  - Monthly: Feb-25 $0.35B, Apr-25 $3.24B, **May-25 $12.88B, Jun-25 $10.51B, Jul-25 $13.45B**, Aug-25 $12.43B, Sep-25 $6.41B, Oct-25 $8.64B, Nov-25 $2.97B, Dec-25 $1.06B, Jan-26 $0.76B, Feb-26 $0.39B, Mar-26 $0.39B, Apr-26 $0.24B, May-26 $0.18B, Jun-26 $0.40B, Jul-26 $0.24B, Aug-26 $0.33B, Sep-26 $0.34B.
  - Peak day: 2025-07-18, $756M. — [DefiLlama Unichain DEXs](https://defillama.com/dexs/chain/unichain) ([API](https://api.llama.fi/overview/dexs/unichain))
- **Share of Uniswap (DefiLlama, 2026-10-13)**:
  - Uniswap volume across all versions over 30d was $79.46B (V3 $38.83B, V4 $39.48B). Unichain's Uniswap volume of $315M is **≈0.40%** of that. All-chain DEX volume was $288.06B over 30d, so Unichain ≈0.11% of it.
  - Unichain's monthly share of Uniswap v4 volume went from 36.6% (Apr-25), **51.5% (May-25)**, 43% (Jun/Jul-25) and 22.9% (Oct-25) down to 2.6% (Jan-26), 0.9% (Jun-26) and **0.3% (Sep–Oct-26)**.
  - Last-30-day v4 volume by chain: Ethereum 37.5%, Robinhood Chain 36.2%, Base 7.3%, BSC 5.5%, Polygon 4.9%. — [DefiLlama Uniswap V4](https://defillama.com/protocol/uniswap-v4) ([API](https://api.llama.fi/summary/dexs/uniswap-v4)); [DefiLlama DEX overview API](https://api.llama.fi/overview/dexs)
- **TVL and stablecoins (DefiLlama)**:
  - Chain DeFi TVL is **$26.8M** on 2026-10-13, against a peak of $902.9M on 2025-07-21. Month-start values: $855.6M (Jul-25), $118.6M (Dec-25), $48.2M (Mar-26), $23.9M (Jul-26), $30.8M (Oct-26).
  - Stablecoin supply is **$27.08M**, against a peak of $462.5M on 2025-07-11. It was $165–178M in Jan–Apr 2026, then **fell from $127.9M (2026-07-01) to $25.8M (2026-08-01)**. — [DefiLlama TVL API](https://api.llama.fi/v2/historicalChainTvl/Unichain); [DefiLlama stablecoins API](https://stablecoins.llama.fi/stablecoincharts/Unichain)
- L2BEAT: total value secured **$88.40M** (−3.87% over 7d; canonical $42.55M, external $45.85M), **7.66 UOPS** over the past day, and $3.19M of cross-chain volume across 672 transfers in 24h. — [L2BEAT Unichain](https://l2beat.com/scaling/projects/unichain)
- Hindenrank (updated 2026-08-01):
  - An incentive program of **$21.8M in UNI (Apr–Jul 2025)** drove the ~$1.4B peak.
  - ~2,500 custom v4 pools use third-party hooks.
  - Sequencer fees, after L1 costs and a 15% Superchain share, burn UNI via TokenJar/Firepit, at an estimated $5.5–7.5M/yr.
  - Its header and body TVL figures ($3M vs $27M) are internally inconsistent. — [Hindenrank](https://hindenrank.com/blog/how-does-unichain-work)
- Organic vs system transactions:
  - growthepie reports Unichain at 7.44 TPS (2026-10-13 17:00 UTC). — [growthepie fees API](https://api.growthepie.com/v1/fees/table.json)
  - The researcher measured 7 builder system transactions per 1 s block, which is 604,800 per day. Non-builder transactions were only **0.27/s ≈ 23.5k/day** (30-minute sample), with ≈16.6k v4 swaps/day and ≈2.6k v3 swaps/day. — [own RPC measurement](https://mainnet.unichain.org)
- Uniswap's stablecoin context: stablecoin-to-stablecoin swaps on Uniswap reached **$43.4B in Q2 2026**, "more than the next three onchain venues combined." — [Uniswap blog: StablePair Hook (2026-09-10)](https://blog.uniswap.org/stablepair-hook-a-fee-that-moves-with-the-market)
- Snapshot discrepancy: Coinpaprika reported Unichain 24h DEX volume of $13.25M on 2026-09-23, versus DefiLlama's ~$6.7–6.9M daily figures in a similar window. — [Coinpaprika DEX market share](https://coinpaprika.com/education/dex-market-share-by-chain/) vs [DefiLlama](https://defillama.com/dexs/chain/unichain)

### Inferences
- Organic flow is thin: ~$10M/day DEX volume, ~$27M stablecoins, ~20k organic transactions/day.
- A stable-pair LP on Unichain today would be fishing in a small pond. PegGuard's fee benefits from 1 s/200 ms blocks and sub-cent gas are real but small against the absence of uninformed stable flow.
- The ~$100M stablecoin outflow in Jul–Aug 2026 suggests a large holder or protocol left (cause unknown). It removed most of the stablecoin base a USDC/USDT0 pool would draw on.
- Any tx-count or TPS-based activity metric for Unichain (L2BEAT UOPS, growthepie TPS) should be divided by roughly 25–30 to get organic user transactions.

### Gaps
- No cause was found for the Jul→Aug 2026 stablecoin drop.
- No Unichain-specific USDC/USDT or USDC/USDT0 pool volumes or fee tiers were pulled. Pool-level data would need StateView/Swap-log aggregation or a DefiLlama/GeckoTerminal pool query.
- Token Terminal and growthepie daily-transaction time series were not retrieved; the growthepie chain endpoint returned 403.
- There is no official Uniswap/Unichain 2026 activity report.
