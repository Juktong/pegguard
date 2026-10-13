"""Reconstruct v4 positions for a pool from ModifyLiquidity logs, compute liquidity shape, TVL, LP concentration.
usage: python3 v4_positions.py <pool_id> <dec0> <dec1> <out.json> <ml.jsonl> [ml2.jsonl ...]
"""
import json, sys, math, collections
import rpc

pid, dec0, dec1, outf = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
files = sys.argv[5:]
SV = '0x86e8631a016f9068c3f085faf484ee3f5fdee8f2'
POSM = '0x4529a01c7a0410167c5740c487a8de60232617bf'
ANCHOR_B, ANCHOR_T = 61167971, 1791916330

evs = {}
for fn in files:
    for l in open(fn):
        e = json.loads(l)
        if e['topics'][1].lower() != pid.lower():
            continue
        k = (e['transactionHash'], int(e['logIndex'], 16))
        evs[k] = e
evs = sorted(evs.values(), key=lambda e: (int(e['blockNumber'], 16), int(e['logIndex'], 16)))
print('ModifyLiquidity events', len(evs))

pos = collections.defaultdict(int)       # (sender, tl, tu, salt) -> liquidity
first_seen = {}
adds = removes = 0
by_block = collections.defaultdict(list)
for e in evs:
    w = rpc.words(e['data'])
    tl, tu, dl, salt = rpc.s(w[0]), rpc.s(w[1]), rpc.s(w[2]), '0x' + w[3]
    sender = rpc.addr(e['topics'][2])
    k = (sender, tl, tu, salt)
    pos[k] += dl
    b = int(e['blockNumber'], 16)
    first_seen.setdefault(k, b)
    if dl > 0: adds += 1
    elif dl < 0: removes += 1
    by_block[b].append((k, dl))
active = {k: v for k, v in pos.items() if v > 0}
neg = {k: v for k, v in pos.items() if v < 0}
print('adds', adds, 'removes', removes, 'distinct positions ever', len(pos), 'active', len(active), 'negative(anomaly)', len(neg))

# JIT detection: position added and fully removed within same block (or within 2 blocks)
jit_same_block = 0
for b, lst in by_block.items():
    d = collections.defaultdict(int); seen_add = set()
    for k, dl in lst:
        if dl > 0: seen_add.add(k)
        d[k] += dl
    for k in seen_add:
        if d[k] == 0: jit_same_block += 1
print('positions opened & closed in the same block (JIT-like):', jit_same_block)

# recent activity windows
def bt(b): return ANCHOR_T - (ANCHOR_B - b)
now = ANCHOR_T
for name, win in [('24h', 86400), ('7d', 7 * 86400), ('30d', 30 * 86400), ('90d', 90 * 86400)]:
    n = sum(1 for e in evs if bt(int(e['blockNumber'], 16)) > now - win)
    print(f'ML events last {name}: {n}')

# current state
S0 = rpc.sel('getSlot0(bytes32)'); GL = rpc.sel('getLiquidity(bytes32)')
r = rpc.calls([(SV, S0 + pid[2:]), (SV, GL + pid[2:])])
w = rpc.words(r[0]); sqrtP = rpc.u(w[0]); tick = rpc.s(w[1]); Lcur = rpc.u(r[1])
blk = rpc.block_number()
P = (sqrtP / 2 ** 96) ** 2 * 10 ** (dec0 - dec1)
print(f'block {blk} sqrtPriceX96 {sqrtP} tick {tick} price(token1 per token0, decimal-adj) {P:.8f} activeL {Lcur}')

# reconstruct active L at current tick from positions
Lrec = sum(v for (s, tl, tu, salt), v in active.items() if tl <= tick < tu)
print('reconstructed active L', Lrec, 'match' if Lrec == Lcur else 'MISMATCH')

sp = sqrtP / 2 ** 96
def amounts(L, tl, tu):
    sa = 1.0001 ** (tl / 2); sb = 1.0001 ** (tu / 2)
    if sp <= sa:
        a0 = L * (sb - sa) / (sa * sb); a1 = 0
    elif sp >= sb:
        a0 = 0; a1 = L * (sb - sa)
    else:
        a0 = L * (sb - sp) / (sp * sb); a1 = L * (sp - sa)
    return a0 / 10 ** dec0, a1 / 10 ** dec1

tot0 = tot1 = 0
posinfo = []
for (s, tl, tu, salt), L in active.items():
    a0, a1 = amounts(L, tl, tu)
    tot0 += a0; tot1 += a1
    posinfo.append(dict(sender=s, tl=tl, tu=tu, salt=salt, L=L, a0=a0, a1=a1, usd=a0 * 1 + a1 * 1, width=tu - tl, inrange=tl <= tick < tu, first_block=first_seen[(s, tl, tu, salt)]))
print(f'TVL from positions: token0 {tot0:,.2f} token1 {tot1:,.2f} total(@$1) {tot0 + tot1:,.2f}')

# owners
nft = [p for p in posinfo if p['sender'] == POSM]
OWN = rpc.sel('ownerOf(uint256)')
res = rpc.calls([(POSM, OWN + p['salt'][2:]) for p in nft], chunk=10)
for p, rr in zip(nft, res):
    p['owner'] = rpc.addr(rpc.words(rr)[0]) if rr else None
for p in posinfo:
    if p['sender'] != POSM:
        p['owner'] = p['sender']
owners = collections.defaultdict(float)
for p in posinfo:
    owners[p['owner']] += p['usd']
tv = sum(owners.values())
ol = sorted(owners.items(), key=lambda kv: -kv[1])
print('distinct owners', len(ol), 'positions', len(posinfo), 'NFT positions', len(nft))
for o, v in ol[:15]:
    print(f'  owner {o} ${v:,.2f} share {v / tv * 100:.1f}%')
hhi = sum((v / tv) ** 2 for _, v in ol) * 10000
print('HHI', round(hhi))
senders = collections.Counter(p['sender'] for p in posinfo)
print('senders (PoolManager callers) of active positions', senders.most_common(10))

# liquidity shape by tick (value in USD at current price)
ticks = collections.defaultdict(float)
for p in posinfo:
    for t in range(max(p['tl'], tick - 2000), min(p['tu'], tick + 2000)):
        a0, a1 = amounts(p['L'], t, t + 1)
        ticks[t] += a0 + a1
wide = sum(p['usd'] for p in posinfo if p['tu'] - p['tl'] > 4000)
total_in_window = sum(ticks.values())
print(f'value accounted in +-2000 ticks: {total_in_window:,.2f}')
def share_band(center, bps):
    lo, hi = center - bps, center + bps
    v = sum(val for t, val in ticks.items() if lo <= t < hi)
    return v
res_bands = {}
for center_name, center in [('current', tick), ('peg(tick0)', 0)]:
    for bps in [1, 2, 5, 10, 25, 50, 100]:
        v = share_band(center, bps)
        res_bands[f'{center_name}+-{bps}'] = (v, v / (tot0 + tot1) * 100)
        print(f'  value within +-{bps} ticks of {center_name}: ${v:,.2f} ({v / (tot0 + tot1) * 100:.1f}% of TVL)')
# depth: USD needed to move price by x bps (sum value in ticks between current and target in each direction)
for bps in [1, 5, 10]:
    up = sum(val for t, val in ticks.items() if tick < t <= tick + bps)
    dn = sum(val for t, val in ticks.items() if tick - bps <= t < tick)
    print(f'  approx depth to move +{bps}bp: ${up:,.0f} ; -{bps}bp: ${dn:,.0f}')
# top ticks
top = sorted(ticks.items(), key=lambda kv: -kv[1])[:15]
print('top ticks by value:', [(t, round(v)) for t, v in sorted(top)])
# width distribution
wd = collections.Counter()
for p in posinfo:
    w_ = p['width']
    b = '1' if w_ <= 1 else '2-5' if w_ <= 5 else '6-10' if w_ <= 10 else '11-50' if w_ <= 50 else '51-200' if w_ <= 200 else '201-2000' if w_ <= 2000 else '>2000'
    wd[b] += p['usd']
print('TVL by position width (ticks):', {k: round(v) for k, v in wd.items()})
json.dump(dict(pid=pid, block=blk, tick=tick, sqrtP=sqrtP, price=P, activeL=Lcur, tvl0=tot0, tvl1=tot1, positions=posinfo,
               owners=ol, bands={k: v for k, v in res_bands.items()}, ticks={str(k): v for k, v in ticks.items()}), open(outf, 'w'), default=str)
