import sys, json, collections
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
out = sys.argv[1]
sw = load_swaps(out)
res = {}
for pid in ORDER:
    rows = [r for r in sw if r['pool'] == pid and WSTART <= r['block'] < WEND]
    if not rows: continue
    notional = [abs(r['d0']) / 1e6 for r in rows]
    fees = []
    for r in rows:
        P = r['px']
        if r['d0'] > 0: fees.append(r['d0'] * r['fee'] / 1e6 / 1e6 * P)
        elif r['d1'] > 0: fees.append(r['d1'] * r['fee'] / 1e6 / 1e6)
        else: fees.append(0)
    feeset = collections.Counter(r['fee'] for r in rows)
    px = [r['px'] for r in rows]
    z41 = sum(1 for r in rows if r['d0'] > 0)
    senders = collections.Counter(r['sender'] for r in rows)
    txs = len(set(r['tx'] for r in rows))
    blocks = len(set(r['block'] for r in rows))
    V = sum(notional)
    d = dict(name=NAMES[pid], swaps=len(rows), txs=txs, blocks=blocks, notional=V, p50=pct(notional, .5), p90=pct(notional, .9), p99=pct(notional, .99), max=max(notional),
             mean=V / len(rows), fees=sum(fees), eff_fee_bps=sum(fees) / V * 1e4 if V else 0, fee_pips=dict(feeset), zeroForOne_share=z41 / len(rows),
             px_min=min(px), px_p50=pct(px, .5), px_max=max(px), n_senders=len(senders), top_sender=senders.most_common(3))
    res[pid] = d
    print(f"{d['name']:30s} swaps {d['swaps']:6d} txs {txs:6d} vol ${V:,.0f} p50 ${d['p50']:,.0f} p90 ${d['p90']:,.0f} p99 ${d['p99']:,.0f} max ${d['max']:,.0f} fees ${d['fees']:,.2f} eff {d['eff_fee_bps']:.3f}bp feepips {dict(feeset)} z41 {d['zeroForOne_share']:.2f} px[{d['px_min']:.5f},{d['px_p50']:.5f},{d['px_max']:.5f}] senders {len(senders)}")
json.dump(res, open(out + '/basic_stats.json', 'w'), indent=1, default=str)
