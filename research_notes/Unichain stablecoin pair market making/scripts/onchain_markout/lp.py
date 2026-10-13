"""LP-side analysis: positions, range widths, re-ranging, JIT, fee & markout attribution per LP.
Usage: python3 -I lp.py OUT_DIR TXS_JSONL LABELS_JSON"""
import sys, os, json, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, WSTART, WEND, pct, price
import refs
OUT, TXS, LAB = sys.argv[1], sys.argv[2], sys.argv[3]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ref')
ref, _ = refs.make_okx1m(DATA + '/okx_usdc_usdt_1m.jsonl', 'vwap')
labels = json.load(open(LAB))
tx = {}
for l in open(TXS):
    t = json.loads(l); tx[t['hash']] = t
swaps = json.load(open(OUT + '/swaps.json')); liq = json.load(open(OUT + '/liq.json'))
H = 300
res = {}
for pid in ORDER:
    sw = [r for r in swaps if r['pool'] == pid]
    ev = [e for e in liq if e['pool'] == pid and e['kind'] in ('modify', 'mint', 'burn') and e['block'] < WEND]
    if not sw: continue
    ver = sw[0]['ver']
    def owner(e):  # economic owner: tx.origin of the LP tx
        return tx.get(e['tx'], {}).get('from', '?')
    def pkey(e):
        return (e.get('sender') if ver == 'v4' else e.get('owner'), e['tl'], e['tu'], e.get('salt', ''))
    # timeline of liquidity events (only from window start; pre-window liquidity inferred per key)
    evw = [e for e in ev if e['block'] >= WSTART]
    cum = collections.defaultdict(int); mincum = collections.defaultdict(int)
    for e in evw:
        k = pkey(e); cum[k] += e['dL']; mincum[k] = min(mincum[k], cum[k])
    L = {k: -mincum[k] for k in cum}  # inferred pre-window liquidity of keys touched in window
    key_owner = {}
    for e in evw: key_owner.setdefault(pkey(e), owner(e))
    # merge events and swaps in (block, li) order
    items = [('L', e) for e in evw] + [('S', r) for r in sw if WSTART <= r['block'] < WEND]
    items.sort(key=lambda x: (x[1]['block'], x[1]['li']))
    fee_by_owner = collections.defaultdict(float); mk_by_owner = collections.defaultdict(float)
    fee_known = 0.0; fee_total = 0.0; share_known = []; n_active = []
    last_add = {}; jit = []; lifetimes = []; open_since = {}
    swaps_in_block = collections.defaultdict(list)
    for kind, x in items:
        if kind == 'S': swaps_in_block[x['block']].append(x['li'])
    for k, v in L.items():
        if v > 0: open_since[k] = None
    for kind, x in items:
        if kind == 'L':
            k = pkey(x); before = L[k]; L[k] += x['dL']
            if x['dL'] > 0 and before == 0: open_since[k] = (x['block'], x['li'])
            if x['dL'] < 0 and L[k] == 0 and k in open_since:
                st = open_since.pop(k)
                if st is not None:
                    lifetimes.append(x['block'] - st[0])
                    sw_between = [li for b in range(st[0], x['block'] + 1) for li in swaps_in_block.get(b, [])
                                  if (b, li) > st and (b, li) < (x['block'], x['li'])]
                    if x['block'] - st[0] <= 1 and sw_between:
                        jit.append(dict(key=str(k), owner=key_owner.get(k), blocks=x['block'] - st[0], swaps=len(sw_between), L=-x['dL']))
            continue
        r = x
        P = r['px']; F = ref.at(r['ts'])
        d0 = r['d0'] / 1e6; d1 = r['d1'] / 1e6
        fee = (d0 * (F or P) if d0 > 0 else d1) * r['fee'] / 1e6
        Fh = ref.at(r['ts'] + H)
        mk = (d0 * Fh + d1) if Fh else None  # LP gross P&L incl fees at +5 min
        fee_total += fee
        tick = r['tick']; Lev = r['L']
        act = [(k, v) for k, v in L.items() if v > 0 and k[1] <= tick < k[2]]
        n_active.append(len(act))
        if Lev <= 0: continue
        sk = 0.0
        for k, v in act:
            s = min(1.0, v / Lev); sk += s
            o = key_owner.get(k, '?')
            fee_by_owner[o] += fee * s
            if mk is not None: mk_by_owner[o] += mk * s
        sk = min(sk, 1.0); share_known.append(sk); fee_known += fee * sk
    adds = [e for e in evw if e['dL'] > 0]; rems = [e for e in evw if e['dL'] < 0]
    widths = [e['tu'] - e['tl'] for e in adds]
    owners = collections.Counter(owner(e) for e in evw)
    per_owner_ranges = {o: len(set((e['tl'], e['tu']) for e in adds if owner(e) == o)) for o in owners}
    days = (WEND - WSTART) / 86400
    top_fee = sorted(fee_by_owner.items(), key=lambda kv: -kv[1])[:8]
    res[pid] = dict(name=NAMES[pid], liq_events=len(evw), adds=len(adds), removes=len(rems), zero_pokes=sum(1 for e in evw if e['dL'] == 0),
                    position_keys=len(cum), lp_origins=len(owners), lp_entry=collections.Counter((tx.get(e['tx'], {}).get('to') or '') for e in evw).most_common(6),
                    width_ticks=dict(p10=pct(widths, .1), p50=pct(widths, .5), p90=pct(widths, .9), share_le2=sum(1 for w in widths if w <= 2) / len(widths) if widths else None,
                                     share_fullrange=sum(1 for w in widths if w > 100000) / len(widths) if widths else None),
                    adds_per_day=len(adds) / days, ranges_per_owner=sorted(per_owner_ranges.items(), key=lambda kv: -owners[kv[0]])[:6],
                    lifetime_blocks=dict(n=len(lifetimes), p10=pct(lifetimes, .1), p50=pct(lifetimes, .5), p90=pct(lifetimes, .9)),
                    jit=dict(n=len(jit), swaps=sum(j['swaps'] for j in jit), owners=collections.Counter(j['owner'] for j in jit).most_common(3)),
                    active_positions_per_swap=dict(p50=pct(n_active, .5), p90=pct(n_active, .9), max=max(n_active) if n_active else None),
                    fee_total=fee_total, fee_attributed_share=fee_known / fee_total if fee_total else None,
                    known_liq_share_per_swap=dict(p10=pct(share_known, .1), p50=pct(share_known, .5)),
                    top_lp_by_fee=[dict(owner=o, fee=f, fee_share=f / fee_total if fee_total else None, net_after_markout_5m=mk_by_owner.get(o), markout_exfee=(f - mk_by_owner.get(o, 0.0))) for o, f in top_fee])
    d = res[pid]
    print(f"\n== {d['name']}: liq events {d['liq_events']} adds {d['adds']} ({d['adds_per_day']:.1f}/day) removes {d['removes']} zero {d['zero_pokes']} keys {d['position_keys']} LP origins {d['lp_origins']}")
    print('   widths', d['width_ticks'], 'lifetime', d['lifetime_blocks'])
    print('   jit', d['jit'], 'active/swap', d['active_positions_per_swap'], 'fee attributed', round(d['fee_attributed_share'] or 0, 3), 'known share', d['known_liq_share_per_swap'])
    print('   ranges per owner', [(o[:10], n, owners[o]) for o, n in d['ranges_per_owner']])
    print('   entry', [(a[:10], labels.get(a.lower(), {}).get('name'), n) for a, n in d['lp_entry']])
    for t in d['top_lp_by_fee'][:6]:
        print(f"   LP {t['owner'][:10]} fee ${t['fee']:.2f} share {t['fee_share']:.3f} net5m ${t['net_after_markout_5m'] or 0:.2f} markout_exfee ${t['markout_exfee']:.2f}")
json.dump(res, open(OUT + '/lp.json', 'w'), indent=1, default=str)
