"""Extras: daily volume per pool, reference path, OKX-vs-Coinbase noise, time-weighted pool deviation, top LP detail.
Usage: python3 -I extras.py OUT_DIR"""
import sys, os, json, collections, bisect, statistics, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, WSTART, WEND, GEN, pct
import refs, glob
OUT = sys.argv[1]
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
TS0, TS1 = GEN + WSTART, GEN + WEND
sw = json.load(open(OUT + '/swaps.json'))
res = {}
# daily volume
dv = collections.defaultdict(lambda: collections.defaultdict(float))
for r in sw:
    if WSTART <= r['block'] < WEND:
        dv[r['pool']][time.strftime('%m-%d', time.gmtime(r['ts']))] += abs(r['d0']) / 1e6
res['daily_volume'] = {NAMES[p]: dict(sorted(v.items())) for p, v in dv.items()}
for p in ORDER[:1] + ['0x31bafd5d04580f71a808ae646bb787d38e9362f9', '0xaf58ab3ed922b34e94d13e01edf1b4ddbe5d2afbc29abbcef5ef8ff752a1ae5a']:
    v = dv[p]; xs = list(v.values())
    print(NAMES[p], 'daily vol p10/p50/p90/max', [round(pct(xs, q)) for q in (.1, .5, .9)], round(max(xs)), 'days', len(xs), 'top days', sorted(v.items(), key=lambda kv: -kv[1])[:4])
# reference path (OKX 1m close)
okx = {}
for l in open(DATA + '/ref/okx_usdc_usdt_1m.jsonl'):
    r = json.loads(l); okx[int(r[0]) // 1000] = (float(r[4]), float(r[5]), float(r[7]))
days = collections.defaultdict(list)
for t, (c, vb, vq) in okx.items():
    if TS0 <= t < TS1: days[time.strftime('%m-%d', time.gmtime(t))].append(c)
res['okx_daily'] = {d: dict(min=min(v), max=max(v), last=v[-1]) for d, v in sorted(days.items())}
allc = [c for t, (c, _, _) in okx.items() if TS0 <= t < TS1]
res['okx_30d'] = dict(min=min(allc), max=max(allc), first=okx[min(k for k in okx if k >= TS0)][0], last=okx[max(k for k in okx if k < TS1)][0],
                      dev_vs_1_bps=dict(p50=pct([(c - 1) * 1e4 for c in allc], .5), p90=pct([abs(c - 1) * 1e4 for c in allc], .9), max=max(abs(c - 1) * 1e4 for c in allc)))
print('OKX 30d', res['okx_30d'])
# OKX vs Coinbase 1m closes (same minute, both traded)
cb = {}
for l in open(DATA + '/ref/cb_usdt_usdc_1m.jsonl'):
    t, lo, hi, op, cl, vol = json.loads(l); cb[int(t)] = 1 / float(cl)
diffs = [(okx[t][0] / cb[t] - 1) * 1e4 for t in cb if t in okx and TS0 <= t < TS1]
res['okx_vs_coinbase_1m_bps'] = dict(n=len(diffs), mean=statistics.fmean(diffs), p50_abs=pct([abs(x) for x in diffs], .5), p90_abs=pct([abs(x) for x in diffs], .9), p99_abs=pct([abs(x) for x in diffs], .99))
print('OKX vs CB', res['okx_vs_coinbase_1m_bps'])
# OKX 1s: within-minute range & 1s close vs 1m VWAP
s1 = {}
for p in sorted(glob.glob(DATA + '/ref/okx_usdc_usdt_1s_part*.jsonl')):
    for l in open(p):
        r = json.loads(l); s1[int(r[0]) // 1000] = float(r[4])
d1 = []
for t, c in s1.items():
    m = (t // 60) * 60
    if m in okx and okx[m][1] > 0: d1.append((c / (okx[m][2] / okx[m][1]) - 1) * 1e4)
res['okx_1s_close_vs_1m_vwap_bps'] = dict(n=len(d1), p50_abs=pct([abs(x) for x in d1], .5), p90_abs=pct([abs(x) for x in d1], .9), p99_abs=pct([abs(x) for x in d1], .99))
ch = [abs(s1[t] / s1[t - 1] - 1) * 1e4 for t in s1 if t - 1 in s1]
res['okx_1s_abs_change_bps'] = dict(share_nonzero=sum(1 for x in ch if x > 0) / len(ch), p99=pct(ch, .99))
ch60 = [abs(s1[t] / s1[t - 60] - 1) * 1e4 for t in s1 if t - 60 in s1]
res['okx_60s_abs_change_bps'] = dict(p50=pct(ch60, .5), p90=pct(ch60, .9), p99=pct(ch60, .99))
print('1s vs 1m vwap', res['okx_1s_close_vs_1m_vwap_bps'], '1s change', res['okx_1s_abs_change_bps'], '60s change', res['okx_60s_abs_change_bps'])
# time-weighted (per-minute) pool mid vs OKX 1m close and vs 1.0
tw = {}
for p in ORDER:
    rows = [r for r in sw if r['pool'] == p]
    if len(rows) < 100: continue
    ts = [r['ts'] for r in rows]; px = [r['px'] for r in rows]
    dref, done = [], []
    for m in range(TS0, TS1, 60):
        i = bisect.bisect_right(ts, m + 59) - 1
        if i < 0 or (m + 60) not in okx and m not in okx: continue
        P = px[i]; F = okx.get(m, (None,))[0]
        if F is None: continue
        if abs(P / F - 1) * 1e4 > 50: continue
        dref.append((P / F - 1) * 1e4); done.append((P - 1) * 1e4)
    q = lambda xs: dict(n=len(xs), mean=statistics.fmean(xs), p50_abs=pct([abs(x) for x in xs], .5), p90_abs=pct([abs(x) for x in xs], .9), p99_abs=pct([abs(x) for x in xs], .99), max_abs=max(abs(x) for x in xs))
    tw[NAMES[p]] = dict(vs_okx=q(dref), vs_one=q(done))
    print('TW', NAMES[p], {k: round(v, 2) for k, v in tw[NAMES[p]]['vs_okx'].items()}, 'vs1', {k: round(v, 2) for k, v in tw[NAMES[p]]['vs_one'].items()})
res['time_weighted_dev'] = tw
json.dump(res, open(OUT + '/extras.json', 'w'), indent=1)
