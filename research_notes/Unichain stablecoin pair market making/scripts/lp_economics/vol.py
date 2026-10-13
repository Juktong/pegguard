import json, math, statistics as st
def load(f): return json.load(open(f))
def logret(rows, step=1):
    c=[float(r[4]) for r in rows]
    return [math.log(c[i]/c[i-step]) for i in range(step,len(c),step)]
def ann_daily_sigma(rets, per_day):
    v=sum(r*r for r in rets)/len(rets)   # zero-mean realized
    return math.sqrt(v*per_day)
print("Realized sigma (daily, bp) from Binance closes, zero-mean RV")
for s in ['USDCUSDT','USDEUSDT','FDUSDUSDT']:
    h=load(f'data/h1y_{s}.json')
    c=[float(r[4]) for r in h]; lo=min(float(r[3]) for r in h); hi=max(float(r[2]) for r in h)
    r1=logret(h,1); r24=logret(h,24)
    # rolling monthly sigma from 1h
    sig_h=ann_daily_sigma(r1,24)*1e4; sig_d=ann_daily_sigma(r24,1)*1e4
    # robust: median abs dev
    mad=st.median(abs(x) for x in r1)*1.4826*math.sqrt(24)*1e4
    # quiet vs all
    print(f"{s}: 1y hourly-sampled sigma_daily={sig_h:.2f}bp (robust MAD {mad:.2f}bp); daily-sampled sigma_daily={sig_d:.2f}bp; close range {min(c):.5f}-{max(c):.5f}; wick range {lo:.4f}-{hi:.4f}; mean {st.mean(c):.5f}")
m=load('data/m30d_USDCUSDT.json'); r=logret(m,1)
for step,lab in [(1,'1m'),(5,'5m'),(60,'1h')]:
    rr=logret(m,step); print(f"USDCUSDT last30d {lab}-sampled sigma_daily={ann_daily_sigma(rr,1440/step)*1e4:.2f}bp")
cs=[float(x[4]) for x in m]; print("last30d close min/max", min(cs), max(cs), "pct minutes w/ zero return", sum(1 for x in r if x==0)/len(r))
svb=load('data/svb_USDCUSDT.json')
print("SVB window USDCUSDT 1h: min low", min(float(x[3]) for x in svb), "max high", max(float(x[2]) for x in svb), "first", svb[0][0], "n",len(svb))
import datetime
for x in svb[::6]: print(datetime.datetime.utcfromtimestamp(x[0]/1000).strftime('%m-%d %H:%M'), x[3], x[4])
o=load('data/oct10_USDEUSDT.json')
lows=sorted(o,key=lambda x: float(x[3]))[:3]
print("Oct10 USDEUSDT 1m min lows:", [(datetime.datetime.utcfromtimestamp(x[0]/1000).strftime('%H:%M'), x[3]) for x in lows])
below=[x for x in o if float(x[4])<0.99]; print("minutes close<0.99:", len(below), "first", datetime.datetime.utcfromtimestamp(below[0][0]/1000).strftime('%H:%M') if below else None, "last", datetime.datetime.utcfromtimestamp(below[-1][0]/1000).strftime('%H:%M') if below else None)
below=[x for x in o if float(x[4])<0.995]; print("minutes close<0.995:", len(below))
