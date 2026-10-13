"""Flow composition: origins, entry contracts, v4 lockers, multi-pool txs, clustering, autocorrelation.
Usage: python3 -I flow.py OUT_DIR TXS_JSONL [LABELS_JSON]"""
import sys, os, json, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, WSTART, WEND, pct, price
OUT, TXS = sys.argv[1], sys.argv[2]
labels = json.load(open(sys.argv[3])) if len(sys.argv) > 3 and os.path.exists(sys.argv[3]) else {}
swaps = [r for r in json.load(open(OUT + '/swaps.json')) if WSTART <= r['block'] < WEND]
tx = {}
for l in open(TXS):
    t = json.loads(l)
    if not t.get('missing'): tx[t['hash']] = t
pools_by_tx = collections.defaultdict(set)
for r in swaps: pools_by_tx[r['tx']].add(r['pool'])
res = {}
allto = collections.Counter(); allfrom = collections.Counter(); alllock = collections.Counter()
def lab(a):
    a = (a or '').lower(); return labels.get(a, {}).get('name') or a[:10]
for pid in ORDER:
    rows = [r for r in swaps if r['pool'] == pid]
    if not rows: continue
    V = sum(abs(r['d0']) / 1e6 for r in rows)
    vol_from = collections.Counter(); vol_to = collections.Counter(); vol_lock = collections.Counter(); n_to = collections.Counter()
    from_by_to = collections.defaultdict(set); prio = collections.defaultdict(list)
    miss = 0
    for r in rows:
        t = tx.get(r['tx']); v = abs(r['d0']) / 1e6
        if not t: miss += 1; continue
        vol_from[t['from']] += v; vol_to[(t['to'] or 'create').lower()] += v; n_to[(t['to'] or 'create').lower()] += 1
        from_by_to[(t['to'] or '').lower()].add(t['from'])
        vol_lock[r['sender'].lower()] += v
        if t.get('maxPrio') is not None: prio[(t['to'] or '').lower()].append(t['maxPrio'])
        allto[(t['to'] or '').lower()] += v; allfrom[t['from']] += v; alllock[r['sender'].lower()] += v
    top = lambda c, k: sum(v for _, v in c.most_common(k)) / V if V else 0
    multi = [r for r in rows if len(pools_by_tx[r['tx']]) > 1]
    # same-block clustering
    per_block = collections.Counter(r['block'] for r in rows)
    multi_swap_blocks = sum(1 for b, c in per_block.items() if c > 1)
    swaps_in_multi_blocks = sum(c for b, c in per_block.items() if c > 1)
    per_tx = collections.Counter(r['tx'] for r in rows)
    ia = [rows[i]['ts'] - rows[i - 1]['ts'] for i in range(1, len(rows))]
    # direction runs by same origin
    same_origin_next = sum(1 for i in range(1, len(rows)) if tx.get(rows[i]['tx'], {}).get('from') == tx.get(rows[i - 1]['tx'], {}).get('from'))
    # per-origin net direction imbalance (one-way flow?)
    net = collections.defaultdict(float); gross = collections.defaultdict(float)
    for r in rows:
        t = tx.get(r['tx'])
        if not t: continue
        net[t['from']] += r['d0'] / 1e6; gross[t['from']] += abs(r['d0']) / 1e6
    top_orig = []
    for a, v in vol_from.most_common(10):
        top_orig.append(dict(addr=a, share=v / V, n=sum(1 for r in rows if tx.get(r['tx'], {}).get('from') == a), net_usdc_into_pool=net[a], imbalance=net[a] / gross[a] if gross[a] else None))
    top_to = []
    for a, v in vol_to.most_common(12):
        pr = prio.get(a, [])
        top_to.append(dict(addr=a, label=lab(a), share=v / V, n=n_to[a], n_origins=len(from_by_to[a]), prio_p50_gwei=(pct(pr, .5) / 1e9) if pr else None))
    top_lock = [dict(addr=a, label=lab(a), share=v / V) for a, v in vol_lock.most_common(8)]
    res[pid] = dict(name=NAMES[pid], swaps=len(rows), missing_tx=miss, notional=V, n_origins=len(vol_from), n_entry=len(vol_to), n_lockers=len(vol_lock),
                    top1_origin_share=top(vol_from, 1), top5_origin_share=top(vol_from, 5), top10_origin_share=top(vol_from, 10),
                    top_origins=top_orig, top_entries=top_to, top_lockers=top_lock,
                    multi_pool_tx_swaps=len(multi), multi_pool_tx_share_vol=sum(abs(r['d0']) / 1e6 for r in multi) / V if V else 0,
                    blocks_with_swaps=len(per_block), blocks_multi_swap=multi_swap_blocks, swaps_in_multi_swap_blocks=swaps_in_multi_blocks,
                    txs_multi_swap_same_pool=sum(1 for c in per_tx.values() if c > 1),
                    interarrival_s=dict(p10=pct(ia, .1), p50=pct(ia, .5), p90=pct(ia, .9), share_le2s=sum(1 for x in ia if x <= 2) / len(ia) if ia else None),
                    same_origin_consecutive_share=same_origin_next / max(1, len(rows) - 1))
    d = res[pid]
    print(f"\n== {d['name']}: swaps {d['swaps']} origins {d['n_origins']} entries {d['n_entry']} lockers {d['n_lockers']} top1 {d['top1_origin_share']:.2f} top5 {d['top5_origin_share']:.2f} top10 {d['top10_origin_share']:.2f} multi-pool-tx vol {d['multi_pool_tx_share_vol']:.3f} multi-swap blocks {multi_swap_blocks}/{len(per_block)} ia p50 {d['interarrival_s']['p50']} le2s {d['interarrival_s']['share_le2s']:.3f} same-origin-consec {d['same_origin_consecutive_share']:.2f}")
    for e in top_to[:8]: print('   to', e['addr'][:12], (e['label'] or '')[:28].ljust(28), f"{e['share']:.3f} n={e['n']} orig={e['n_origins']} prio={e['prio_p50_gwei']}")
    for e in top_lock[:5]: print('   lock', e['addr'][:12], (e['label'] or '')[:28].ljust(28), f"{e['share']:.3f}")
    for e in top_orig[:5]: print('   from', e['addr'][:12], f"{e['share']:.3f} n={e['n']} imb={e['imbalance']:+.2f}")
json.dump(res, open(OUT + '/flow.json', 'w'), indent=1, default=str)
json.dump(dict(to=allto.most_common(60), lockers=alllock.most_common(40), origins=allfrom.most_common(40)), open(OUT + '/flow_top_addrs.json', 'w'), indent=1)
