"""Fetch Coinbase Exchange USDT-USDC 1m candles [time, low, high, open, close, volume] in 300-candle pages."""
import sys, json, time, urllib.request, datetime
start, end, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
f = open(out, 'w'); n = 0
iso = lambda t: datetime.datetime.fromtimestamp(t, datetime.UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
t = start
while t < end:
    b = min(t + 300 * 60, end)
    url = f"https://api.exchange.coinbase.com/products/USDT-USDC/candles?granularity=60&start={iso(t)}&end={iso(b)}"
    for att in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'pegguard-research/0.1'}), timeout=30) as r:
                rows = json.loads(r.read())
            if not isinstance(rows, list): raise RuntimeError(str(rows)[:200])
            break
        except Exception as e:
            time.sleep(2 ** att)
    else:
        raise SystemExit('fail ' + str(t))
    for row in rows:
        if t <= row[0] < b:
            f.write(json.dumps(row) + '\n'); n += 1
    t = b
    time.sleep(0.35)
print('rows', n)
