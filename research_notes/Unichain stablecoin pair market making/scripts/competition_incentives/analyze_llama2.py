import json, sys, datetime, collections
D=sys.argv[1]
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
sa=json.load(open(D+'/llama_stablecoins_all.json'))
print("Stablecoins on Unichain now (DefiLlama):")
rows=[]
for s in sa['peggedAssets']:
    cc=s.get('chainCirculating',{}).get('Unichain')
    if cc:
        cur=cc.get('current',{}); v=sum(x for x in cur.values() if isinstance(x,(int,float)))
        pm=cc.get('circulatingPrevMonth',{}); vpm=sum(x for x in pm.values() if isinstance(x,(int,float)))
        rows.append((v,s['symbol'],s['name'],vpm))
for v,sym,n,vpm in sorted(rows,reverse=True)[:20]: print(f"  {sym} ({n}): ${v/1e6:,.2f}M (prev month ${vpm/1e6:,.2f}M)")
# Protocol TVL on Unichain
pr=json.load(open(D+'/llama_protocols.json'))
print("\nProtocols with Unichain TVL (DefiLlama /protocols chainTvls):")
r=[]
for p in pr:
    v=(p.get('chainTvls') or {}).get('Unichain')
    if v and v>50000: r.append((v,p['name'],p.get('category')))
for v,n,c in sorted(r,reverse=True)[:45]: print(f"  {n} [{c}]: ${v/1e6:,.2f}M")
print("  count protocols listing Unichain:",sum(1 for p in pr if 'Unichain' in (p.get('chains') or [])))
# aggregator volume
ag=json.load(open(D+'/llama_aggs_unichain.json'))
print("\nAggregators on Unichain: total24h",ag.get('total24h'),'total30d',ag.get('total30d'),'total1y',ag.get('total1y'))
for p in sorted(ag.get('protocols',[]),key=lambda p:-(p.get('total30d') or 0))[:20]:
    print(f"   {p.get('name')} | 30d ${(p.get('total30d') or 0)/1e6:,.2f}M | 1y ${(p.get('total1y') or 0)/1e6:,.1f}M")
# DEX volume breakdown by protocol monthly
dx=json.load(open(D+'/llama_dexs_unichain_2.json'))
bd=dx.get('totalDataChartBreakdown',[])
mon=collections.defaultdict(collections.Counter)
for t,b in bd:
    for k,v in b.items(): mon[ts(t)[:7]][k]+=v
print("\nUnichain monthly DEX volume by protocol ($M):")
for m in sorted(mon):
    tot=sum(mon[m].values())
    top=", ".join(f"{k} {v/1e6:,.0f}" for k,v in mon[m].most_common(6))
    print(f"  {m} total {tot/1e6:,.0f} | {top}")
# Unichain chain revenue
fc=json.load(open(D+'/llama_fees_unichain_chain.json'))
print("\nUnichain chain revenue summary keys:",[k for k in fc.keys()][:20])
for k in ['total24h','total7d','total30d','total1y','totalAllTime']: print('  ',k,fc.get(k))
ch=fc.get('totalDataChart',[])
mm=collections.Counter()
for t,v in ch: mm[ts(t)[:7]]+=v
print("  monthly:",{k:round(v) for k,v in sorted(mm.items())})
# tbill
tb=json.load(open(D+'/llama_tbill.json'))
dat=tb.get('data',[])
print("\ntbill pool chart last pts:",dat[-3:] if dat else tb)
