import sys, json, time, urllib.request
sys.path.insert(0, sys.argv[1])
from cex_dl import okx, coinbase, get
outdir=sys.argv[2]
def kraken_trades(pair, start, end, out):
    rows=[]; since=start*10**9
    while True:
        d=get(f"https://api.kraken.com/0/public/Trades?pair={pair}&since={since}&count=1000")
        if not d or d.get('error'): print('kraken err',d and d.get('error'),flush=True); break
        res=d['result']; last=int(res['last']); key=[k for k in res if k!='last'][0]
        tr=res[key]
        for t in tr:
            ts=float(t[2])
            if ts>=end: break
            rows.append([ts,float(t[0]),float(t[1])])
        if not tr or float(tr[-1][2])>=end or last==since: break
        since=last; time.sleep(1.1)
    json.dump({"source":"kraken_trades","pair":pair,"cols":"ts,price,vol","rows":rows},open(out,'w'))
    print(out,len(rows),flush=True)
job=sys.argv[3]
if job=='okx_events':
    okx('USDC-USDT','1m',60,1678320000,1678924800,f"{outdir}/okx_usdcusdt_1m_2023-03.json")
    okx('USDC-USDT','1m',60,1760054400,1760313600,f"{outdir}/okx_usdcusdt_1m_2025-10.json")
    okx('USDC-USDT','1m',60,1652054400,1652659200,f"{outdir}/okx_usdcusdt_1m_2022-05.json")
    coinbase('DAI-USD',60,1678320000,1678924800,f"{outdir}/coinbase_daiusd_1m_2023-03.json")
    coinbase('USDT-USD',60,1760054400,1760313600,f"{outdir}/coinbase_usdtusd_1m_2025-10.json")
elif job=='kraken_events':
    kraken_trades('USDEUSD',1760126400,1760169600,f"{outdir}/kraken_usdeusd_trades_2025-10-10.json")  # 20:00Z Oct10 -> 08:00Z Oct11
    kraken_trades('USDCUSD',1678406400,1678665600,f"{outdir}/kraken_usdcusd_trades_2023-03-10_12.json")
