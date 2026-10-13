"""Directional-signal tests on per-swap records (non-tautological).
Usage: python3 -I directional.py OUT_DIR PERSWAP_JSONL TXS_JSONL TOX_H
Signals (all computable before the swap): dev_raw = F/pre - 1 (no basis, i.e. a dual-feed ratio hook);
 dev_ema450 = F*EMA450(post/F)/pre - 1 (PegGuard hook, tau 450 s); dev_ema6h = same with tau 6 h.
Truth: raw-reference instant markout sign / trade direction vs raw deviation; toxic = ex-fee LP markout at TOX_H > 0.
"""
import sys, os, json, collections, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, pct
OUT, PS, TXS, TOXH = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
ALPHA, DB, CAP = 0.5, 0.5e-4, 50e-4
tx = {}
for l in open(TXS):
    t = json.loads(l); tx[t['hash']] = t
bypool = collections.defaultdict(list)
for l in open(PS):
    r = json.loads(l); bypool[r['pool']].append(r)
res = {}
def corr(xs, ys):
    if len(xs) < 3: return None
    mx, my = statistics.fmean(xs), statistics.fmean(ys); sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs) / (sx * sy) if sx and sy else None
for pid in ORDER:
    rs = [r for r in bypool.get(pid, []) if not r['outlier']]
    if len(rs) < 50: continue
    # EMA bases (trailing, updated after each swap with post/F)
    for tau, key in ((450.0, 'b450'), (21600.0, 'b6h')):
        b = 0.0; last = None
        for r in rs:
            r[key] = b if b > 0 else None
            ob = r['post'] / r['F0']
            if b == 0: b = ob
            else:
                dt = r['ts'] - last
                if dt > 0: b += dt / (dt + tau) * (ob - b)
            last = r['ts']
    out = {}
    for sig in ('raw', 'b450', 'b6h'):
        rows = []
        for r in rs:
            bas = 1.0 if sig == 'raw' else r.get(sig)
            if bas is None: continue
            dev = r['F0'] * bas / r['pre'] - 1
            buy_usdc = not r['z41']  # trader buys USDC (token0) from pool
            corr_dir = (buy_usdc if dev > 0 else (not buy_usdc)) if dev != 0 else None
            mh = r['mk'].get(TOXH)
            tox = (r['fee'] - mh) > 0 if mh is not None else None
            a_raw = r['fee'] - r['mk'].get('0', r['mk'].get(0, 0))
            prem = min(ALPHA * (abs(dev) - DB), CAP) if (corr_dir and abs(dev) > DB) else 0.0
            rows.append(dict(dev=dev, corr=corr_dir, tox=tox, n=r['notional'], extra=abs(r['d1']) * prem, as0=a_raw, ash=(r['fee'] - mh) if mh is not None else None, buy=buy_usdc))
        V = sum(x['n'] for x in rows)
        bk = collections.OrderedDict()
        for lo, hi in ((0, .25), (.25, .5), (.5, 1), (1, 2), (2, 5), (5, 1e9)):
            sub = [x for x in rows if lo <= abs(x['dev']) * 1e4 < hi and x['corr'] is not None]
            if sub:
                vs = sum(x['n'] for x in sub)
                bk[f'{lo}-{hi}'] = dict(n=len(sub), p_corr=sum(1 for x in sub if x['corr']) / len(sub), p_corr_vol=sum(x['n'] for x in sub if x['corr']) / vs,
                                        as_bps=sum(x['ash'] for x in sub if x['ash'] is not None) / vs * 1e4)
        ext = sum(x['extra'] for x in rows)
        bleed = sum(x['ash'] for x in rows if x['ash'] is not None)
        corr_as = sum(x['ash'] for x in rows if x['corr'] and x['ash'] is not None)
        noncorr_as = sum(x['ash'] for x in rows if x['corr'] is False and x['ash'] is not None)
        vc = sum(x['n'] for x in rows if x['corr']); vn = sum(x['n'] for x in rows if x['corr'] is False)
        out[sig] = dict(n=len(rows), extra_usd=ext, extra_bps=ext / V * 1e4 if V else None,
                        precision_toxic=(sum(x['extra'] for x in rows if x['tox']) / ext) if ext else None,
                        capture_of_bleed=(ext / bleed) if bleed > 0 else None, bleed_usd=bleed,
                        as_bps_correcting=corr_as / vc * 1e4 if vc else None, as_bps_noncorrecting=noncorr_as / vn * 1e4 if vn else None,
                        vol_share_correcting=vc / V if V else None,
                        corr_dev_vs_buy=corr([x['dev'] * 1e4 for x in rows], [1 if x['buy'] else -1 for x in rows]),
                        buckets=bk)
    # next-trade prediction: deviation left after trade i (post_i vs F at t_{i+1}) predicts direction of trade i+1?
    hits = [0, 0]; xs = []; ys = []
    for a, b in zip(rs, rs[1:]):
        dev_after = b['F0'] / a['post'] - 1  # pool mid between trades is a['post'] (== b['pre'])
        if abs(dev_after) * 1e4 < 0.5: continue
        buy = not b['z41']
        hits[0] += 1; hits[1] += int((dev_after > 0) == buy)
        xs.append(dev_after * 1e4); ys.append(1 if buy else -1)
    out['next_trade_raw_dev_ge_0.5bp'] = dict(n=hits[0], hit_rate=hits[1] / hits[0] if hits[0] else None, corr=corr(xs, ys))
    # trade-direction persistence and same-block structure
    s = [1 if not r['z41'] else -1 for r in rs]
    same_dir = sum(1 for a, b in zip(s, s[1:]) if a == b) / max(1, len(s) - 1)
    blocks = collections.defaultdict(list)
    for r in rs: blocks[r['block']].append(r)
    mb = [v for v in blocks.values() if len(v) > 1]
    diff_tx = [v for v in mb if len(set(x['tx'] for x in v)) > 1]
    opp = sum(1 for v in diff_tx if len(set(x['z41'] for x in v)) > 1)
    same_origin = sum(1 for v in diff_tx if len(set(tx.get(x['tx'], {}).get('from') for x in v)) == 1)
    out['structure'] = dict(p_same_direction_next=same_dir, blocks_multi=len(mb), blocks_multi_difftx=len(diff_tx), share_opposite_dirs=opp / len(diff_tx) if diff_tx else None,
                            share_same_origin=same_origin / len(diff_tx) if diff_tx else None)
    res[pid] = dict(name=NAMES[pid], **out)
    print('\n==', NAMES[pid], 'n', len(rs))
    for sig in ('raw', 'b450', 'b6h'):
        o = out[sig]
        print(f"  {sig:5s} extra ${o['extra_usd']:.2f} ({o['extra_bps']:.3f}bp) prec_toxic {o['precision_toxic']} capture {o['capture_of_bleed']} bleed ${o['bleed_usd']:.2f} AScorr {o['as_bps_correcting']} ASnon {o['as_bps_noncorrecting']} volcorr {o['vol_share_correcting']} corr {o['corr_dev_vs_buy']}")
        print('        buckets', {k: (v['n'], round(v['p_corr'], 2), round(v['as_bps'], 2)) for k, v in o['buckets'].items()})
    print('  next-trade', out['next_trade_raw_dev_ge_0.5bp'], 'structure', out['structure'])
json.dump(res, open(f"{OUT}/directional_{os.path.basename(PS).replace('perswap_', '').replace('.jsonl', '')}.json", 'w'), indent=1)
