"""Decode raw logs into swap and liquidity event tables (JSON)."""
import sys, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpcutil import s256, words
GEN = 1730748359  # Unichain: block timestamp = GEN + block_number (verified at blocks 1, 1e6, head)
logs_paths, meta_path, out_dir = sys.argv[1].split(','), sys.argv[2], sys.argv[3]
meta = json.load(open(meta_path))
SW4 = '0x40e9cecb'; ML4 = '0xf208f491'; DN4 = '0x29ef05ca'
SW3 = '0xc42079f9'; MI3 = '0x7a53080b'; BU3 = '0x0c396cd9'; CO3 = '0x70935338'
def s128(w):
    v = int(w, 16) & ((1 << 128) - 1)
    return v - (1 << 128) if v >= (1 << 127) else v
def s24(w):
    v = int(w, 16) & ((1 << 24) - 1)
    return v - (1 << 24) if v >= (1 << 23) else v
POOL_DEC = {'0x3188bf36b4ac5127d077a5e873ec297cd1d05447a70ae05cdf8e7c3e74a4e48d': (6, 18)}  # USDC/DAI(18 dec)
swaps = []; liq = []
seen = set()
import itertools
for line in itertools.chain(*[open(p) for p in logs_paths]):
    lg = json.loads(line)
    key = (lg['transactionHash'], lg['logIndex'])
    if key in seen: continue
    seen.add(key)
    t0 = lg['topics'][0][:10]; bn = int(lg['blockNumber'], 16); w = words(lg['data'])
    base = dict(block=bn, ts=GEN + bn, li=int(lg['logIndex'], 16), txi=int(lg['transactionIndex'], 16), tx=lg['transactionHash'])
    if t0 in (SW4, ML4, DN4):
        pool = lg['topics'][1]; sender = '0x' + lg['topics'][2][26:]
        if t0 == SW4:
            a0, a1 = s128(w[0]), s128(w[1])
            swaps.append(dict(base, pool=pool, ver='v4', sender=sender, d0=-a0, d1=-a1, sqrtP=int(w[2], 16), L=int(w[3], 16), tick=s24(w[4]), fee=int(w[5], 16)))
        elif t0 == ML4:
            liq.append(dict(base, pool=pool, ver='v4', kind='modify', sender=sender, tl=s24(w[0]), tu=s24(w[1]), dL=s256(w[2]), salt='0x' + w[3]))
        else:
            liq.append(dict(base, pool=pool, ver='v4', kind='donate', sender=sender, a0=int(w[0], 16), a1=int(w[1], 16)))
    else:
        pool = lg['address'].lower(); fee = meta['v3'][pool]['fee']
        if t0 == SW3:
            swaps.append(dict(base, pool=pool, ver='v3', sender='0x' + lg['topics'][1][26:], recipient='0x' + lg['topics'][2][26:], d0=s256(w[0]), d1=s256(w[1]), sqrtP=int(w[2], 16), L=int(w[3], 16), tick=s24(w[4]), fee=fee))
        elif t0 == MI3:
            liq.append(dict(base, pool=pool, ver='v3', kind='mint', owner='0x' + lg['topics'][1][26:], tl=s24(lg['topics'][2]), tu=s24(lg['topics'][3]), sender='0x' + w[0][24:], dL=int(w[1], 16), a0=int(w[2], 16), a1=int(w[3], 16)))
        elif t0 == BU3:
            liq.append(dict(base, pool=pool, ver='v3', kind='burn', owner='0x' + lg['topics'][1][26:], tl=s24(lg['topics'][2]), tu=s24(lg['topics'][3]), dL=-int(w[0], 16), a0=int(w[1], 16), a1=int(w[2], 16)))
        elif t0 == CO3:
            liq.append(dict(base, pool=pool, ver='v3', kind='collect', owner='0x' + lg['topics'][1][26:], tl=s24(lg['topics'][2]), tu=s24(lg['topics'][3]), recipient='0x' + w[0][24:], a0=int(w[1], 16), a1=int(w[2], 16)))
for r in swaps:
    d0d, d1d = POOL_DEC.get(r['pool'], (6, 6))
    r['px'] = (r['sqrtP'] / 2 ** 96) ** 2 * 10 ** (d0d - d1d)
    if d1d != 6: r['d1'] = r['d1'] / 10 ** (d1d - 6)
    if d0d != 6: r['d0'] = r['d0'] / 10 ** (d0d - 6)
swaps.sort(key=lambda r: (r['block'], r['li'])); liq.sort(key=lambda r: (r['block'], r['li']))
json.dump(swaps, open(out_dir + '/swaps.json', 'w')); json.dump(liq, open(out_dir + '/liq.json', 'w'))
print('swaps', len(swaps), 'liq', len(liq))
