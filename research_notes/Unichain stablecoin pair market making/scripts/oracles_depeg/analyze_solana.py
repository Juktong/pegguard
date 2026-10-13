# Analyze polled Solana Pyth sponsored PriceUpdateV2 accounts (USDC/USD, USDT/USD) and compare to OKX/Coinbase 1m.
import sys, json, math, time
P, D = sys.argv[1], sys.argv[2]


def q(a, p):
    a = sorted(a)
    k = (len(a) - 1) * p
    f = int(k)
    c = min(f + 1, len(a) - 1)
    return a[f] + (a[c] - a[f]) * (k - f)


def st(a):
    return f"n={len(a)} mean={sum(a)/len(a):.2f} p50={q(a,.5):.2f} p99={q(a,.99):.2f} min={min(a):.2f} max={max(a):.2f}"


rows = [json.loads(l) for l in open(P)]
U = lambda t: time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))
print(f"polls={len(rows)} {U(rows[0]['t_local'])} -> {U(rows[-1]['t_local'])} UTC")
ups = []
last = None
for r in rows:
    c, t = r['USDC/USD'], r['USDT/USD']
    k = (c['publish_time'], t['publish_time'])
    if k != last:
        ups.append((r['t_local'], c, t, r['slot']))
        last = k
same = sum(1 for u in ups if u[1]['publish_time'] == u[2]['publish_time'])
print(f"distinct account updates={len(ups)}; both feeds same publish_time in {same}")
gaps = [b[1]['publish_time'] - a[1]['publish_time'] for a, b in zip(ups, ups[1:])]
print("  gap between successive on-chain (Solana) updates, s:", st(gaps))
print("  age of price when first seen by poller, s:", st([u[0] - u[1]['publish_time'] for u in ups]))
print("  Pythnet continuity publish_time - prev_publish_time, s:", st([u[1]['publish_time'] - u[1]['prev_publish_time'] for u in ups]))
cd = [(u[1]['price'] * 1e-8 - 1) * 1e4 for u in ups]
td = [(u[2]['price'] * 1e-8 - 1) * 1e4 for u in ups]
cc = [u[1]['conf'] / u[1]['price'] * 1e4 for u in ups]
tc = [u[2]['conf'] / u[2]['price'] * 1e4 for u in ups]
print("  USDC/USD dev bps:", st(cd))
print("  USDT/USD dev bps:", st(td))
print("  USDC conf bps:", st(cc))
print("  USDT conf bps:", st(tc))
R = [((u[1]['price'] / u[2]['price']) - 1) * 1e4 for u in ups]
Rl = [a + b for a, b in zip(cc, tc)]
Rr = [math.sqrt(a * a + b * b) for a, b in zip(cc, tc)]
print("  ratio USDC/USDT dev bps:", st(R))
print("  ratio conf (linear sum) bps:", st(Rl))
print("  ratio conf (root-sum-square) bps:", st(Rr))
dR = [abs(b - a) for a, b in zip(R, R[1:])]
print("  |delta ratio| between successive updates (~53 s) bps:", st(dR))
mu = sum(R) / len(R)
sd = math.sqrt(sum((x - mu) ** 2 for x in R) / (len(R) - 1))
print(f"  ratio std over window = {sd:.3f} bps")
# EMA price vs spot
print("  |USDC price - ema_price| bps:", st([abs(u[1]['price'] - u[1]['ema_price']) / u[1]['price'] * 1e4 for u in ups]))
# Compare with OKX USDC-USDT 1m close and Coinbase USDT-USD at same minute
okx = {int(t): v[3] for t, v in json.load(open(f"{D}/okx_usdcusdt_1m_30d.json"))['rows']}
cb = {int(t): v[3] for t, v in json.load(open(f"{D}/coinbase_usdtusd_1m_30d.json"))['rows']}
diffs = []
diffs_cb = []
for u, r in zip(ups, R):
    m = (u[1]['publish_time'] // 60) * 60
    if m in okx:
        diffs.append(r - (okx[m] - 1) * 1e4)
    if m in cb:
        diffs_cb.append((u[2]['price'] * 1e-8 - cb[m]) * 1e4)
if diffs:
    print("  Pyth ratio minus OKX USDC-USDT close (same minute) bps:", st(diffs))
if diffs_cb:
    print("  Pyth USDT/USD minus Coinbase USDT-USD close (same minute) bps:", st(diffs_cb))
