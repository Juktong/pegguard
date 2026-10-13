# Download public CEX candles. Usage: cex_dl.py <outdir> <job> ; jobs defined below. Polite sleeps.
import sys, json, time, urllib.request, os
UA={"user-agent":"research-script/1.0"}
def get(url):
    for i in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30) as r: return json.loads(r.read())
        except Exception as e:
            print('retry',i,url[:90],str(e)[:80],flush=True); time.sleep(2+3*i)
    return None
def bitstamp(pair, step, start, end, out):
    rows={}
    t=start
    while t<end:
        d=get(f"https://www.bitstamp.net/api/v2/ohlc/{pair}/?step={step}&limit=1000&start={t}")
        o=(d or {}).get('data',{}).get('ohlc',[])
        if not o: t+=step*1000; continue
        for c in o:
            ts=int(c['timestamp'])
            if start<=ts<end: rows[ts]=[float(c['open']),float(c['high']),float(c['low']),float(c['close']),float(c['volume'])]
        t=max(int(o[-1]['timestamp'])+step, t+step)
        time.sleep(0.4)
    json.dump({"source":"bitstamp","pair":pair,"step":step,"cols":"o,h,l,c,v","rows":sorted(rows.items())},open(out,'w'))
    print(out,len(rows),flush=True)
def coinbase(prod, gran, start, end, out):
    rows={}
    t=start
    while t<end:
        e=min(t+gran*300,end)
        d=get(f"https://api.exchange.coinbase.com/products/{prod}/candles?granularity={gran}&start={t}&end={e}")
        for c in d or []:
            rows[int(c[0])]=[c[3],c[2],c[1],c[4],c[5]]  # o,h,l,c,v (cb: time,low,high,open,close,vol)
        t=e
        time.sleep(0.35)
    json.dump({"source":"coinbase","pair":prod,"step":gran,"cols":"o,h,l,c,v","rows":sorted(rows.items())},open(out,'w'))
    print(out,len(rows),flush=True)
def okx(inst, bar, barsec, start, end, out):
    rows={}
    after=end*1000
    while True:
        d=get(f"https://www.okx.com/api/v5/market/history-candles?instId={inst}&bar={bar}&after={after}&limit=100")
        data=(d or {}).get('data',[])
        if not data: break
        for c in data:
            ts=int(c[0])//1000
            if ts>=start: rows[ts]=[float(c[1]),float(c[2]),float(c[3]),float(c[4]),float(c[5])]
        after=int(data[-1][0])
        if after//1000<start: break
        time.sleep(0.25)
    json.dump({"source":"okx","pair":inst,"step":barsec,"cols":"o,h,l,c,v","rows":sorted(rows.items())},open(out,'w'))
    print(out,len(rows),flush=True)
if __name__=='__main__':
    outdir=sys.argv[1]; job=sys.argv[2]
    NOW=int(time.time())//60*60
    D=86400
    if job=='recent':  # last 30 days at 1m
        s=NOW-30*D
        okx('USDC-USDT','1m',60,s,NOW,f"{outdir}/okx_usdcusdt_1m_30d.json")
        coinbase('USDT-USD',60,s,NOW,f"{outdir}/coinbase_usdtusd_1m_30d.json")
        bitstamp('usdtusd',60,s,NOW,f"{outdir}/bitstamp_usdtusd_1m_30d.json")
        bitstamp('usdcusd',60,s,NOW,f"{outdir}/bitstamp_usdcusd_1m_30d.json")
    elif job=='longhourly':  # ~3.5 years hourly
        s=1672531200  # 2023-01-01
        bitstamp('usdcusd',3600,1640995200,NOW,f"{outdir}/bitstamp_usdcusd_1h.json")
        bitstamp('usdtusd',3600,1640995200,NOW,f"{outdir}/bitstamp_usdtusd_1h.json")
        okx('USDC-USDT','1H',3600,s,NOW,f"{outdir}/okx_usdcusdt_1h.json")
        coinbase('USDT-USD',3600,1640995200,NOW,f"{outdir}/coinbase_usdtusd_1h.json")
    elif job=='events':
        # USDC/SVB Mar 9-16 2023, USDT/Terra May 9-16 2022, at 1m
        bitstamp('usdcusd',60,1678320000,1678924800,f"{outdir}/bitstamp_usdcusd_1m_2023-03.json")
        bitstamp('usdtusd',60,1678320000,1678924800,f"{outdir}/bitstamp_usdtusd_1m_2023-03.json")
        bitstamp('daiusd',60,1678320000,1678924800,f"{outdir}/bitstamp_daiusd_1m_2023-03.json")
        coinbase('USDT-USD',60,1678320000,1678924800,f"{outdir}/coinbase_usdtusd_1m_2023-03.json")
        bitstamp('usdtusd',60,1652054400,1652659200,f"{outdir}/bitstamp_usdtusd_1m_2022-05.json")
        bitstamp('usdcusd',60,1652054400,1652659200,f"{outdir}/bitstamp_usdcusd_1m_2022-05.json")
        coinbase('USDT-USD',60,1652054400,1652659200,f"{outdir}/coinbase_usdtusd_1m_2022-05.json")
