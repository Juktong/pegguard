# Analyze Pyth PriceFeedUpdate logs (USDC/USD eaa020c6, USDT/USD 2b89b9dc) -> per-feed and ratio stats.
import sys, json, math, time, collections
P=sys.argv[1]; label=sys.argv[2]
rows=[json.loads(l) for l in open(P)]
C,T='eaa020c6','2b89b9dc'
def q(a,p):
    if not a: return float('nan')
    a=sorted(a); k=(len(a)-1)*p; f=int(k); c=min(f+1,len(a)-1); return a[f]+(a[c]-a[f])*(k-f)
def st(a):
    return {"n":len(a),"mean":sum(a)/len(a),"p50":q(a,.5),"p90":q(a,.9),"p99":q(a,.99),"p999":q(a,.999),"max":max(a),"min":min(a)}
def fmt(d): return " ".join(f"{k}={v:.3f}" if isinstance(v,float) else f"{k}={v}" for k,v in d.items())
feeds=collections.defaultdict(dict)
for r in rows: feeds[r['id']][r['publishTime']]=(r['price']*1e-8, r['conf']*1e-8)
tmin=min(r['publishTime'] for r in rows); tmax=max(r['publishTime'] for r in rows)
print(f"[{label}] logs={len(rows)} window {time.strftime('%Y-%m-%d %H:%M',time.gmtime(tmin))} -> {time.strftime('%Y-%m-%d %H:%M',time.gmtime(tmax))} UTC ({(tmax-tmin)/86400:.1f} d)")
for fid,name in [(C,'USDC/USD'),(T,'USDT/USD')]:
    d=feeds[fid]; ts=sorted(d)
    dev=[(d[t][0]-1)*1e4 for t in ts]; conf=[d[t][1]/d[t][0]*1e4 for t in ts]
    gaps=[b-a for a,b in zip(ts,ts[1:])]
    print(f" {name}: unique publishTimes={len(ts)}")
    print("   dev_bps  ", fmt(st(dev)))
    print("   conf_bps ", fmt(st(conf)))
    print("   onchain update gap s", fmt(st(gaps)))
# paired by exact publishTime
common=sorted(set(feeds[C])&set(feeds[T]))
R=[];Rc_lin=[];Rc_rss=[];z=[]
for t in common:
    pc,cc=feeds[C][t]; pt,ct=feeds[T][t]
    r=pc/pt; R.append((r-1)*1e4)
    a,b=cc/pc,ct/pt
    Rc_lin.append((a+b)*1e4); Rc_rss.append(math.sqrt(a*a+b*b)*1e4)
print(f" RATIO USDC/USDT paired same publishTime n={len(common)}")
print("   ratio dev bps        ", fmt(st(R)))
print("   |ratio dev| bps      ", fmt(st([abs(x) for x in R])))
print("   ratio conf lin bps   ", fmt(st(Rc_lin)))
print("   ratio conf rss bps   ", fmt(st(Rc_rss)))
# changes between consecutive paired samples (noise of ratio increments), and de-meaned by rolling 1h median
dR=[b-a for a,b in zip(R,R[1:])]
print("   d(ratio) between consecutive paired samples bps", fmt(st([abs(x) for x in dR])))
# resample to fixed 300 s grid (last value at or before), to remove event-driven oversampling
grid=[];j=0
for g in range(common[0],common[-1],300):
    while j+1<len(common) and common[j+1]<=g: j+=1
    if g-common[j]<=3600: grid.append((g,R[j],Rc_lin[j],g-common[j]))
print(f"   300s-grid (sample-and-hold, max age 1h) n={len(grid)}  |ratio dev| ", fmt(st([abs(x[1]) for x in grid])))
print("   300s-grid age of last paired update s", fmt(st([x[3] for x in grid])))
# exceedance counts
for th in [5,10,20,30,50,100]:
    ex=sum(1 for x in grid if abs(x[1])>th)
    print(f"   grid share |ratio dev|>{th}bps: {ex/len(grid)*100:.3f}% ({ex})")
# top 5 excursions
top=sorted(zip(common,R,Rc_lin),key=lambda x:-abs(x[1]))[:8]
for t,r,c in top: print("   top", time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(t)), f"ratio_dev={r:.2f}bps conf_lin={c:.2f}bps")
# monthly medians of ratio dev
mon=collections.defaultdict(list)
for t,r in zip(common,R): mon[time.strftime('%Y-%m',time.gmtime(t))].append(r)
for m,v in sorted(mon.items()): print(f"   month {m} n={len(v)} median ratio dev={q(v,.5):.2f} p1={q(v,.01):.2f} p99={q(v,.99):.2f} bps")
