# Multi-year hourly stable-pair levels and episode catalog (|dev|>threshold, contiguous hours).
import sys, json, time, collections
D = sys.argv[1]


def q(a, p):
    a = sorted(a)
    k = (len(a) - 1) * p
    f = int(k)
    c = min(f + 1, len(a) - 1)
    return a[f] + (a[c] - a[f]) * (k - f)


def U(t):
    return time.strftime('%Y-%m-%d %H:%M', time.gmtime(t))


def run(fn, label, use_extreme=True):
    rows = [(int(t), *v) for t, v in json.load(open(f"{D}/{fn}"))['rows']]
    print(f"== {label}: {U(rows[0][0])} -> {U(rows[-1][0])} n={len(rows)} hourly candles")
    byq = collections.defaultdict(list)
    for t, o, h, l, c, v in rows:
        lt = time.gmtime(t)
        byq[f"{lt.tm_year}Q{(lt.tm_mon-1)//3+1}"].append(((c - 1) * 1e4, (l - 1) * 1e4, (h - 1) * 1e4))
    for k, v in sorted(byq.items()):
        cl = [x[0] for x in v]
        print(f"  {k}: n={len(v)} close p1={q(cl,.01):+.1f} p50={q(cl,.5):+.1f} p99={q(cl,.99):+.1f} | hourly low min={min(x[1] for x in v):+.0f} high max={max(x[2] for x in v):+.0f} | hours |close|>10:{sum(1 for x in cl if abs(x)>10)} >25:{sum(1 for x in cl if abs(x)>25)} >50:{sum(1 for x in cl if abs(x)>50)}")
    # episodes: contiguous hours where hourly extreme (low or high) beyond 50 bps
    for th in [50]:
        eps = []
        cur = None
        for t, o, h, l, c, v in rows:
            ext = max(abs(l - 1), abs(h - 1)) * 1e4 if use_extreme else abs(c - 1) * 1e4
            if ext > th:
                if cur and t - cur['end'] <= 3600:
                    cur['end'] = t
                    if ext > cur['peak']:
                        cur['peak'], cur['pt'], cur['sign'] = ext, t, (1 if abs(h - 1) > abs(l - 1) else -1)
                    cur['hrs'] += 1
                else:
                    if cur:
                        eps.append(cur)
                    cur = {'start': t, 'end': t, 'peak': ext, 'pt': t, 'hrs': 1, 'sign': (1 if abs(h - 1) > abs(l - 1) else -1)}
        if cur:
            eps.append(cur)
        print(f"  episodes with hourly extreme beyond {th} bps: {len(eps)}")
        for e in eps:
            print(f"    {U(e['start'])} .. {U(e['end'])} hours={e['hrs']} peak={'+' if e['sign']>0 else '-'}{e['peak']:.0f}bps at {U(e['pt'])}")


run('okx_usdcusdt_1h.json', 'OKX USDC-USDT (USDC per USDT)')
run('bitstamp_usdtusd_1h.json', 'Bitstamp USDT/USD')
try:
    run('coinbase_usdtusd_1h.json', 'Coinbase USDT-USD')
except FileNotFoundError:
    print('coinbase hourly missing')
