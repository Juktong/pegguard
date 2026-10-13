import sys, urllib.request, os, json, datetime
D=sys.argv[1]
sa=json.load(open(D+'/llama_stablecoins_all.json'))
ids=[(s['id'],s['symbol']) for s in sa['peggedAssets'] if 'Unichain' in (s.get('chains') or []) or 'Unichain' in s.get('chainCirculating',{})]
print(ids)
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
for i,sym in ids:
    try:
        d=json.loads(urllib.request.urlopen(urllib.request.Request(f"https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin={i}",headers={"User-Agent":"Mozilla/5.0"}),timeout=60).read())
        pts={ts(p['date']):sum((p.get('totalCirculatingUSD') or {}).values()) for p in d}
        sel=[k for k in ['2025-08-01','2026-01-01','2026-04-01','2026-06-01','2026-07-01','2026-07-15','2026-08-01','2026-10-01'] if k in pts]
        print(sym, i, {k:round(pts[k]/1e6,1) for k in sel})
    except Exception as e: print("ERR",sym,e)
