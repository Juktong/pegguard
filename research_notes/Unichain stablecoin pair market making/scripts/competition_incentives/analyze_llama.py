import json, sys, datetime, collections
D=sys.argv[1]
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
# chains
ch=json.load(open(D+'/llama_chains.json'))
for c in ch:
    if c.get('name') in ('Unichain','Base','OP Mainnet','Optimism','Arbitrum','Ink','Soneium','World Chain'): print('chain',c['name'],'tvl',round(c.get('tvl',0)))
# TVL history monthly
h=json.load(open(D+'/llama_tvl_unichain.json'))
print("\nUnichain TVL (DefiLlama) month-start samples:")
seen=set()
for p in h:
    d=ts(p['date'])
    if d[8:10]=='01' or p is h[-1]:
        print('  ',d,f"${p['tvl']/1e6:,.1f}M")
mx=max(h,key=lambda p:p['tvl']); print('  peak',ts(mx['date']),f"${mx['tvl']/1e6:,.1f}M")
# dex volumes
dx=json.load(open(D+'/llama_dexs_unichain.json'))
print("\nDEX overview keys:",list(dx.keys())[:30])
for k in ['total24h','total7d','total30d','total1y','totalAllTime','change_1d','change_7d','change_1m']:
    print('  ',k,dx.get(k))
print("\nDEX protocols on Unichain (sorted by 30d):")
prots=dx.get('protocols',[])
for p in sorted(prots,key=lambda p:-(p.get('total30d') or 0))[:40]:
    print(f"   {p.get('name')} | {p.get('displayName')} | 24h ${ (p.get('total24h') or 0)/1e6:,.2f}M | 7d ${(p.get('total7d') or 0)/1e6:,.1f}M | 30d ${(p.get('total30d') or 0)/1e6:,.1f}M | 1y ${(p.get('total1y') or 0)/1e6:,.0f}M | parent {p.get('parentProtocol')}")
# monthly dex volume from chart
chart=dx.get('totalDataChart',[])
mon=collections.Counter()
for t,v in chart: mon[ts(t)[:7]]+=v
print("\nUnichain monthly DEX volume (DefiLlama):")
for k in sorted(mon): print('  ',k,f"${mon[k]/1e9:,.2f}B")
# stablecoins
sc=json.load(open(D+'/llama_stables_unichain.json'))
print("\nUnichain stablecoin mcap month-start samples:")
for p in sc:
    d=ts(p['date'])
    if d[8:10]=='01' or p is sc[-1]:
        v=(p.get('totalCirculatingUSD') or {}).get('peggedUSD',0)
        print('  ',d,f"${v/1e6:,.1f}M")
for c in json.load(open(D+'/llama_stables_chains.json')):
    if c.get('name')=='Unichain': print('stablechains entry',c)
