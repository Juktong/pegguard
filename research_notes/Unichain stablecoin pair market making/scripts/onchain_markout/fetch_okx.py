"""Fetch OKX USDC-USDT history candles backward from end_ms to start_ms. Resumable via output file."""
import sys, json, time, os, urllib.request
inst, bar, start_ms, end_ms, out, rate = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], float(sys.argv[6])
after = end_ms
if os.path.exists(out):
    ts = [int(json.loads(l)[0]) for l in open(out)]
    if ts: after = min(ts)
f = open(out, 'a'); n = 0; t0 = time.time()
while after > start_ms:
    url = f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar={bar}&limit=100&after={after}"
    for att in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'pegguard-research/0.1'}), timeout=30) as r:
                d = json.loads(r.read())
            if d.get('code') != '0':
                raise RuntimeError(str(d)[:200])
            break
        except Exception as e:
            time.sleep(2 ** att)
    else:
        raise SystemExit('failed at ' + str(after))
    rows = d['data']
    if not rows: break
    for row in rows:
        if int(row[0]) >= start_ms:
            f.write(json.dumps(row) + '\n')
    n += len(rows)
    after = min(int(r[0]) for r in rows)
    time.sleep(1.0 / rate)
f.close()
print('rows', n, 'secs', round(time.time() - t0, 1))
