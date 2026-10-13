# Compare Pyth (Sonic on-chain paired USDC/USD,USDT/USD) ratio with OKX USDC-USDT 1m close and Coinbase USDT-USD at same minute.
import sys, json, collections
S, D = sys.argv[1], sys.argv[2]
def q(a,p):
    a=sorted(a); k=(len(a)-1)*p; f=int(k); c=min(f+1,len(a)-1); return a[f]+(a[c]-a[f])*(k-f)
by=collections.defaultdict(dict)
for l in open(S):
    r=json.loads(l); by[r['id']][r['publishTime']]=r['price']*1e-8
okx={int(t):v for t,v in json.load(open(f"{D}/okx_usdcusdt_1m_30d.json"))['rows']}
cb={int(t):v for t,v in json.load(open(f"{D}/coinbase_usdtusd_1m_30d.json"))['rows']}
com=sorted(set(by['eaa020c6'])&set(by['2b89b9dc']))
d1=[];d2=[];inrange=[]
for t in com:
    m=(t//60)*60
    R=by['eaa020c6'][t]/by['2b89b9dc'][t]
    if m in okx:
        o,h,l,c,v=okx[m]
        d1.append((R-c)*1e4); inrange.append(l-1e-4<=R<=h+1e-4)
    if m in cb:
        d2.append((by['2b89b9dc'][t]-cb[m][3])*1e4)
f=lambda a: f"n={len(a)} mean={sum(a)/len(a):+.2f} p1={q(a,.01):+.2f} p50={q(a,.5):+.2f} p99={q(a,.99):+.2f} min={min(a):+.2f} max={max(a):+.2f}"
print("Pyth ratio (Sonic paired) minus OKX USDC-USDT 1m close, bps:", f(d1))
print("  share of Pyth ratio within OKX 1m [low-1bp, high+1bp]:", f"{sum(inrange)/len(inrange)*100:.1f}%")
print("Pyth USDT/USD minus Coinbase USDT-USD 1m close, bps:", f(d2))
print("abs diffs: OKX p50=%.2f p99=%.2f | Coinbase p50=%.2f p99=%.2f" % (q([abs(x) for x in d1],.5),q([abs(x) for x in d1],.99),q([abs(x) for x in d2],.5),q([abs(x) for x in d2],.99)))
