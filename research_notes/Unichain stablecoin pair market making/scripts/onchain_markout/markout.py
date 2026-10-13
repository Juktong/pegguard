"""LP markout / fee / deviation / directional-signal analysis for Unichain stable pools.

Usage: python3 -I markout.py OUT_DIR REF(okx1s|okx1m|cb1m) WSTART_TS WEND_TS TAG

Conventions (all P&L in token1 = USDT0 units ~ USD):
  pool deltas d0, d1 (raw, 6 decimals): positive = pool (LPs) received.
  P = token1/token0 = USDT0 per USDC; reference F = USDC/USDT (OKX USDC-USDT; Coinbase inverted).
  fee_i = gross input * feePips/1e6 (input token valued at F if token0).
  MK_h (LP gross P&L incl. fees, vs holding) = d0*F(t+h) + d1.
  AS_h (LP adverse-selection markout before fees, + = LP loss) = fee_i - MK_h.
  bps aggregates are sum / sum(notional) * 1e4, notional = |USDC leg|.
  Repo 'truth' (shadow/truth.py analogue): basis_c = median over same-pool swaps within +/-300 s of post_mid/F;
  fair_local = F(t)*basis_c; truth_dev = fair_local/pre_mid - 1; truth markout (ex-fee) = fee - (d0*fair_local + d1).
  Hook replay (shadow/pipeline.py analogue): trailing basis EMA tau=450 s from post_mid/F after each swap;
  dev = F*basis/pre_mid - 1; correcting per is_correcting; premium = alpha*(|dev|-deadband) with alpha=0.5,
  deadband 0.5 bp, cap 50 bp; extra = |d1| * premium.
"""
import sys, os, json, math, random, statistics, bisect, collections, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, price, pct, GEN
import refs

OUT, REF, TS0, TS1, TAG = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'ref')
if REF == 'okx1s':
    ref, _ = refs.make_okx1s(sorted(glob.glob(DATA + '/okx_usdc_usdt_1s_part*.jsonl')))
    H = [0, 10, 60, 300, 3600]
elif REF == 'okx1m':
    ref, _ = refs.make_okx1m(DATA + '/okx_usdc_usdt_1m.jsonl', 'vwap'); H = [0, 300, 3600]
elif REF == 'okx1mclose':
    ref, _ = refs.make_okx1m(DATA + '/okx_usdc_usdt_1m.jsonl', 'close'); H = [0, 300, 3600]
elif REF == 'cb1m':
    ref = refs.make_cb1m(DATA + '/cb_usdt_usdc_1m.jsonl'); H = [0, 300, 3600]
SELF_H = [10, 60, 300, 3600]
OUTLIER_BPS = 50.0
ALPHA = 0.5; DEADBAND = 0.5e-4; CAP = 50e-4; TAU = 450.0

swaps = json.load(open(OUT + '/swaps.json'))
bypool = collections.defaultdict(list)
for r in swaps: bypool[r['pool']].append(r)

def block_boot(contrib_by_day, notional_by_day, n=1000, seed=7):
    days = sorted(notional_by_day)
    if len(days) < 2: return (float('nan'), float('nan'))
    rng = random.Random(seed); vals = []
    for _ in range(n):
        s = [rng.choice(days) for _ in days]
        num = sum(contrib_by_day[d] for d in s); den = sum(notional_by_day[d] for d in s)
        if den > 0: vals.append(num / den * 1e4)
    vals.sort(); return (vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1])

results = {}
ALLRECS = []
for pid in ORDER:
    rows = bypool.get(pid, [])
    if not rows: continue
    ts_list = [r['ts'] for r in rows]
    post = [r['px'] for r in rows]
    # pre-mid: previous swap of same pool
    recs = []
    for i, r in enumerate(rows):
        if not (TS0 <= r['ts'] < TS1) or i == 0: continue
        F0 = ref.at(r['ts'])
        if F0 is None: continue
        pre = post[i - 1]; po = post[i]
        notional = abs(r['d0']) / 1e6
        if notional <= 0: continue
        d0 = r['d0'] / 1e6; d1 = r['d1'] / 1e6
        fee = (d0 * F0 if d0 > 0 else d1) * r['fee'] / 1e6
        outlier = abs(pre / F0 - 1) * 1e4 > OUTLIER_BPS or abs(po / F0 - 1) * 1e4 > OUTLIER_BPS
        rec = dict(i=i, ts=r['ts'], block=r['block'], tx=r['tx'], d0=d0, d1=d1, notional=notional, fee=fee, pre=pre, post=po, F0=F0,
                   z41=r['d0'] > 0, outlier=outlier, sender=r['sender'])
        rec['mk'] = {}
        for h in H:
            Fh = ref.at(r['ts'] + h)
            rec['mk'][h] = None if Fh is None else d0 * Fh + d1
        rec['self'] = {}
        for h in SELF_H:
            j = bisect.bisect_right(ts_list, r['ts'] + h) - 1
            j = max(j, i)
            rec['self'][h] = d0 * post[j] + d1
        rec['pool'] = pid
        recs.append(rec)
    # centered basis (truth) over all swaps with ref (incl. outside window margins)
    obs_t, obs_v = [], []
    for i, r in enumerate(rows):
        F = ref.at(r['ts'])
        if F is None: continue
        b = post[i] / F
        if abs(b - 1) * 1e4 > OUTLIER_BPS: continue
        obs_t.append(r['ts']); obs_v.append(b)
    for rec in recs:
        lo = bisect.bisect_left(obs_t, rec['ts'] - 300); hi = bisect.bisect_right(obs_t, rec['ts'] + 300)
        win = obs_v[lo:hi]
        rec['basis_c'] = statistics.median(win) if win else None
    # leave-own-tx-out centered bases (non-tautological truth variants)
    obs_tx = []
    for i, r in enumerate(rows):
        F = ref.at(r['ts'])
        if F is None: continue
        if abs(post[i] / F - 1) * 1e4 > OUTLIER_BPS: continue
        obs_tx.append(r['tx'])
    for rec in recs:
        rec['bv'] = {}
        for W in (300, 3600, 43200):
            lo = bisect.bisect_left(obs_t, rec['ts'] - W); hi = bisect.bisect_right(obs_t, rec['ts'] + W)
            win = [obs_v[k] for k in range(lo, hi) if obs_tx[k] != rec['tx']]
            rec['bv'][W] = statistics.median(win) if win else None
        rec['bv']['raw'] = 1.0
    # trailing EMA basis replay (hook), sequential over all swaps of pool in time order
    basis = 0.0; last_t = None
    rec_by_i = {rec['i']: rec for rec in recs}
    for i, r in enumerate(rows):
        F = ref.at(r['ts'])
        rec = rec_by_i.get(i)
        if rec is not None:
            rec['basis_t'] = basis if basis > 0 else None
        if F is None: continue
        ob = post[i] / F
        if abs(ob - 1) * 1e4 > OUTLIER_BPS: continue  # hook would see it, but keep basis sane; flagged in notes
        if basis == 0: basis = ob
        else:
            dt = r['ts'] - last_t
            if dt > 0:
                k = dt / (dt + TAU); basis = basis + k * (ob - basis)
        last_t = r['ts']
    good = [x for x in recs if not x['outlier']]
    N = len(good); V = sum(x['notional'] for x in good); FEES = sum(x['fee'] for x in good)
    out = dict(name=NAMES[pid], ref=REF, n_all=len(recs), n_outlier=len(recs) - N, n=N, notional=V, fees=FEES,
               fee_bps=FEES / V * 1e4 if V else None)
    # deviations
    dev_ref = [(x['pre'] / x['F0'] - 1) * 1e4 for x in good]
    dev_one = [(x['pre'] - 1) * 1e4 for x in recs]
    ref_one = [(x['F0'] - 1) * 1e4 for x in recs]
    def q(xs):
        a = [abs(v) for v in xs]
        return dict(n=len(xs), mean_signed=statistics.fmean(xs) if xs else None, p50_signed=pct(xs, .5), abs_p50=pct(a, .5), abs_p90=pct(a, .9), abs_p99=pct(a, .99), abs_max=max(a) if a else None)
    out['dev_pool_vs_ref_bps'] = q(dev_ref)
    out['dev_pool_vs_1_bps'] = q(dev_one)
    out['dev_ref_vs_1_bps'] = q(ref_one)
    bc = [x for x in good if x.get('basis_c')]
    out['dev_pool_vs_ref_detrended_bps'] = q([(x['pre'] / (x['F0'] * x['basis_c']) - 1) * 1e4 for x in bc])
    out['basis_c_bps'] = q([(x['basis_c'] - 1) * 1e4 for x in bc])
    # markouts
    mk = {}
    for h in H:
        sub = [x for x in good if x['mk'][h] is not None]
        v = sum(x['notional'] for x in sub)
        if not v: continue
        gross = sum(x['mk'][h] for x in sub); fees = sum(x['fee'] for x in sub)
        byday_c = collections.defaultdict(float); byday_v = collections.defaultdict(float); byday_g = collections.defaultdict(float)
        for x in sub:
            d = x['ts'] // 86400
            byday_c[d] += x['fee'] - x['mk'][h]; byday_v[d] += x['notional']; byday_g[d] += x['mk'][h]
        mk[h] = dict(n=len(sub), notional=v, fee_bps=fees / v * 1e4, markout_exfee_bps=(fees - gross) / v * 1e4,
                     net_lp_bps=gross / v * 1e4, net_lp_usd=gross, markout_exfee_usd=fees - gross,
                     markout_ci95=block_boot(byday_c, byday_v), net_ci95=block_boot(byday_g, byday_v),
                     per_swap_sd_bps=statistics.pstdev([(x['fee'] - x['mk'][h]) / x['notional'] * 1e4 for x in sub]))
    out['markout_ref'] = mk
    sm = {}
    for h in SELF_H:
        gross = sum(x['self'][h] for x in good)
        sm[h] = dict(markout_exfee_bps=(FEES - gross) / V * 1e4 if V else None, net_lp_bps=gross / V * 1e4 if V else None)
    out['markout_self'] = sm
    # size buckets (h=300 if available else 0)
    hb = 300 if 300 in H else H[-1]
    sb = {}
    for lo, hi in [(0, 100), (100, 1000), (1000, 10000), (10000, 1e12)]:
        sub = [x for x in good if lo <= x['notional'] < hi and x['mk'].get(hb) is not None]
        v = sum(x['notional'] for x in sub)
        if v:
            sb[f'{lo}-{hi}'] = dict(n=len(sub), notional=v, fee_bps=sum(x['fee'] for x in sub) / v * 1e4,
                                    markout_exfee_bps=sum(x['fee'] - x['mk'][hb] for x in sub) / v * 1e4,
                                    markout0_exfee_bps=sum(x['fee'] - x['mk'][0] for x in sub if x['mk'][0] is not None) / v * 1e4)
    out['size_buckets_h'] = hb; out['size_buckets'] = sb
    # repo-style truth + hook replay
    tr = [x for x in good if x.get('basis_c')]
    tot_extra = 0.0; corr_extra = 0.0; charged = 0; agree = 0; truth_mk_exfee = 0.0; truth_mk_gross = 0.0
    corr_n = 0; corr_v = 0.0; corr_as = 0.0; tot_as = 0.0
    buckets = collections.OrderedDict((k, [0, 0, 0.0, 0.0]) for k in ['<0.25', '0.25-0.5', '0.5-1', '1-2', '2-5', '>=5'])
    def bk(a):
        return '<0.25' if a < .25 else '0.25-0.5' if a < .5 else '0.5-1' if a < 1 else '1-2' if a < 2 else '2-5' if a < 5 else '>=5'
    sign_pairs = []
    for x in tr:
        fl = x['F0'] * x['basis_c']
        tdev = fl / x['pre'] - 1
        tcorr = (not x['z41']) if tdev > 0 else (x['z41'] if tdev < 0 else False)
        g = x['d0'] * fl + x['d1']
        truth_mk_gross += g; truth_mk_exfee += x['fee'] - g
        tot_as += x['fee'] - g
        if tcorr:
            corr_n += 1; corr_v += x['notional']; corr_as += x['fee'] - g
        b = buckets[bk(abs(tdev) * 1e4)]; b[0] += 1; b[1] += int(tcorr); b[2] += x['notional']; b[3] += x['fee'] - g
        x['tdev'] = tdev; x['tcorr'] = tcorr
        if x.get('basis_t'):
            hdev = x['F0'] * x['basis_t'] / x['pre'] - 1
            hcorr = (not x['z41']) if hdev > 0 else (x['z41'] if hdev < 0 else False)
            prem = min(ALPHA * (abs(hdev) - DEADBAND), CAP) if (hcorr and abs(hdev) > DEADBAND) else 0.0
            extra = abs(x['d1']) * prem
            x['hdev'] = hdev
            if extra > 0:
                charged += 1; tot_extra += extra
                if tcorr: agree += 1; corr_extra += extra
            sign_pairs.append((hdev, 1 if not x['z41'] else -1, x['notional']))
    out['truth'] = dict(n=len(tr), truth_markout_exfee_usd=truth_mk_exfee, truth_markout_exfee_bps=truth_mk_exfee / max(1e-9, sum(x['notional'] for x in tr)) * 1e4,
                        truth_gross_lp_usd=truth_mk_gross, correcting_share_n=corr_n / max(1, len(tr)), correcting_share_vol=corr_v / max(1e-9, sum(x['notional'] for x in tr)),
                        markout_from_correcting_usd=corr_as, markout_total_usd=tot_as,
                        buckets={k: dict(n=v[0], p_correcting=(v[1] / v[0]) if v[0] else None, notional=v[2], markout_exfee_bps=(v[3] / v[2] * 1e4) if v[2] else None) for k, v in buckets.items()})
    out['hook_replay'] = dict(charged=charged, extra_usd=tot_extra, extra_bps=tot_extra / V * 1e4 if V else None, precision=(corr_extra / tot_extra) if tot_extra else None,
                              sign_agreement=(agree / charged) if charged else None,
                              capture_vs_truth_exfee=(tot_extra / abs(truth_mk_exfee)) if truth_mk_exfee else None,
                              capture_vs_truth_gross=(tot_extra / abs(truth_mk_gross)) if truth_mk_gross else None)
    # directional: correlation between hook dev (signed) and trade sign (+1 = buys USDC from pool, i.e. correcting when dev>0)
    if len(sign_pairs) > 10:
        xs = [p[0] * 1e4 for p in sign_pairs]; ys = [p[1] for p in sign_pairs]
        mx, my = statistics.fmean(xs), statistics.fmean(ys)
        cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / len(xs)
        sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
        out['dir_corr_hookdev_vs_sign'] = cov / (sx * sy) if sx and sy else None
        out['dir_hit_rate_hookdev'] = sum(1 for a, b in zip(xs, ys) if a * b > 0) / max(1, sum(1 for a in xs if a != 0))
    # flow sign autocorrelation (all swaps in window, incl outliers), lag 1..3
    s = [1 if not x['z41'] else -1 for x in recs]
    ac = {}
    if len(s) > 20:
        m = statistics.fmean(s); var = statistics.pvariance(s)
        for lag in (1, 2, 3, 5):
            ac[lag] = sum((s[k] - m) * (s[k - lag] - m) for k in range(lag, len(s))) / ((len(s) - lag) * var) if var else None
    out['sign_autocorr'] = ac
    # truth variants: centered leave-own-tx-out basis windows + raw (no basis); hook premium precision & capture under each
    HT = 60 if 60 in H else 300
    tv = {}
    for W in ('raw', 300, 3600, 43200):
        sub = [x for x in good if x['bv'].get(W) and x.get('basis_t')]
        if not sub: continue
        vv = sum(x['notional'] for x in sub); tm = 0.0; ncorr = 0; vcorr = 0.0; asc = 0.0; ext = 0.0; extc = 0.0; ext_tox = 0.0
        hit = [0, 0]
        for x in sub:
            fl = x['F0'] * x['bv'][W]
            dv = fl / x['pre'] - 1
            c = (not x['z41']) if dv > 0 else (x['z41'] if dv < 0 else False)
            a = x['fee'] - (x['d0'] * fl + x['d1'])
            tm += a
            if c: ncorr += 1; vcorr += x['notional']; asc += a
            hdev = x['F0'] * x['basis_t'] / x['pre'] - 1
            hc = (not x['z41']) if hdev > 0 else (x['z41'] if hdev < 0 else False)
            prem = min(ALPHA * (abs(hdev) - DEADBAND), CAP) if (hc and abs(hdev) > DEADBAND) else 0.0
            e = abs(x['d1']) * prem
            ext += e
            if c: extc += e
            mh = x['mk'].get(HT)
            if mh is not None:
                fh = x['F0'] and (mh - x['d1']) / x['d0'] if x['d0'] else None
                # toxic at horizon HT vs ref scaled by this basis
                tox = (x['fee'] - (x['d0'] * (fh * x['bv'][W]) + x['d1'])) > 0 if fh else False
                if tox: ext_tox += e
            if abs(hdev) > DEADBAND:
                hit[0] += 1; hit[1] += int(hc == c)
        tv[str(W)] = dict(n=len(sub), truth_markout_exfee_bps=tm / vv * 1e4, truth_markout_exfee_usd=tm, correcting_share_n=ncorr / len(sub), correcting_share_vol=vcorr / vv,
                          markout_from_correcting_usd=asc, extra_usd=ext, precision_sign=(extc / ext) if ext else None, precision_toxic_h=(ext_tox / ext) if ext else None,
                          capture=(ext / tm) if tm > 0 else None, hook_vs_truth_sign_agree_outside_deadband=(hit[1] / hit[0]) if hit[0] else None)
    out['truth_variants'] = tv
    out['toxic_horizon_s'] = HT
    results[pid] = out
    ALLRECS.extend(recs)
    m300 = mk.get(300) or mk.get(H[-1]); m0 = mk.get(0)
    print(f"{out['name']:28s} n={N:6d} out={out['n_outlier']:4d} V=${V:,.0f} fee={out['fee_bps']:.3f}bp | AS0={m0['markout_exfee_bps']:+.3f} AS300={m300['markout_exfee_bps']:+.3f} net300={m300['net_lp_bps']:+.3f} CI{tuple(round(c,2) for c in m300['net_ci95'])} | AS3600={mk[3600]['markout_exfee_bps'] if 3600 in mk else float('nan'):+.3f} | |dev| p50 {out['dev_pool_vs_ref_bps']['abs_p50']:.2f} p90 {out['dev_pool_vs_ref_bps']['abs_p90']:.2f} p99 {out['dev_pool_vs_ref_bps']['abs_p99']:.2f} | prec={out['hook_replay']['precision']} cap={out['hook_replay']['capture_vs_truth_exfee']}")
json.dump(results, open(f'{OUT}/markout_{TAG}.json', 'w'), indent=1, default=str)
with open(f'{OUT}/perswap_{TAG}.jsonl', 'w') as fo:
    for rec in ALLRECS:
        fo.write(json.dumps({k: rec.get(k) for k in ('pool', 'tx', 'ts', 'block', 'notional', 'fee', 'd0', 'd1', 'pre', 'post', 'F0', 'z41', 'outlier', 'mk', 'self', 'bv', 'basis_t', 'sender')}) + '\n')
