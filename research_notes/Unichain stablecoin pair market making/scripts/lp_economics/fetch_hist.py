import json, sys, time, urllib.request, os
sym, interval, start_ms, end_ms, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
rows=[]; t=start_ms
while t < end_ms:
    url=f"https://data-api.binance.vision/api/v3/klines?symbol={sym}&interval={interval}&startTime={t}&endTime={end_ms}&limit=1000"
    with urllib.request.urlopen(url, timeout=30) as r: k=json.loads(r.read())
    if not k: break
    rows+=k; t=k[-1][0]+1
    if len(k)<1000: break
json.dump(rows, open(out,'w')); print(sym, interval, len(rows))
