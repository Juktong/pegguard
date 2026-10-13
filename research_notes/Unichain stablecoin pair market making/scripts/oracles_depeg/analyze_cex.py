import sys, json, math, time
D=sys.argv[1]
def load(fn):
    d=json.load(open(f"{D}/{fn}")); return [(int(t),*v) for t,v in d['rows']]
def q(a,p):
    a=sorted(a); k=(len(a)-1)*p; f=int(k); c=min(f+1,len(a)-1); return a[f]+(a[c]-a[f])*(k-f)
def st(a): return f"n={len(a)} mean={sum(a)/len(a):.2f} p1={q(a,.01):.2f} p50={q(a,.5):.2f} p99={q(a,.99):.2f} p999={q(a,.999):.2f} min={min(a):.2f} max={max(a):.2f}"
def T(t): return time.strftime('%Y-%m-%d %H:%M',time.gmtime(t))
def recent(fn,label,invert=False):
    r=load(fn)
    c=[(row[0], (1/row[4] if invert else row[4])) for row in r]
    lo=[(row[0], (1/row[2] if invert else row[3])) for row in r]  # worst-side
    dev=[(p-1)*1e4 for _,p in c]
    print(f"[{label}] {T(r[0][0])} -> {T(r[-1][0])} 1m closes")
    print("  close dev from 1.0 bps:", st(dev))
    d1=[abs(b-a) for a,b in zip(dev,dev[1:])]
    print("  |1m change| bps:", st(d1))
    # deviation from trailing EMA tau=450s on 60s steps (mimic basis EMA) 
    k=60/(60+450); e=None; de=[]
    for x in dev:
        e=x if e is None else e+k*(x-e); de.append(abs(x-e))
    print("  |dev - trailing EMA(450s)| bps:", st(de))
    # 30-min rolling max-min range
    w=30; rng=[max(dev[i:i+w])-min(dev[i:i+w]) for i in range(0,len(dev)-w,5)]
    print("  30-min range bps:", st(rng))
    for th in [10,20,30,50]:
        print(f"   minutes with |close dev|>{th}bps: {sum(1 for x in dev if abs(x)>th)} of {len(dev)}")
    return dict(c)
okx=recent('okx_usdcusdt_1m_30d.json','OKX USDC-USDT')
cb=recent('coinbase_usdtusd_1m_30d.json','Coinbase USDT-USD (as USDC/USDT = 1/USDT-USD)',invert=True)
common=sorted(set(okx)&set(cb))
diff=[(okx[t]-cb[t])*1e4 for t in common]
print("[cross-venue OKX USDC-USDT minus Coinbase 1/USDT-USD] bps:", st(diff))
