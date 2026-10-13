import json,sys,datetime
D=sys.argv[1]
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
for n in ['usdt','usdc']:
    d=json.load(open(D+f'/llama_stables_unichain_{n}.json'))
    out=[]
    for p in d:
        dd=ts(p['date'])
        if dd[8:10] in ('01','15') or p is d[-1]:
            v=(p.get('totalCirculatingUSD') or {}).get('peggedUSD',0)
            out.append(f"{dd}:{v/1e6:,.1f}")
    print(n.upper(),"Unichain $M:"," ".join(out[-40:]))
# daily around Jul-Aug 2026 for usdc
d=json.load(open(D+'/llama_stables_unichain_usdc.json'))
print("USDC daily Jul 10 - Aug 10 2026:")
for p in d:
    dd=ts(p['date'])
    if '2026-07-10'<=dd<='2026-08-10': print(' ',dd,round((p.get('totalCirculatingUSD') or {}).get('peggedUSD',0)/1e6,1))
y=json.load(open(D+'/llama_yields_pools.json'))['data']
print("\nAll Unichain pools w/ USD in symbol:")
for p in sorted([p for p in y if p['chain']=='Unichain'],key=lambda p:-(p['tvlUsd'] or 0)):
    if 'USD' in p['symbol'].upper():
        print(f"  {p['project']} | {p['symbol']} | {p.get('poolMeta')} | tvl ${p['tvlUsd']:,.0f} | apy {p.get('apy')} base {p.get('apyBase')} rew {p.get('apyReward')} | mean30d {p.get('apyMean30d')}")
print("count Unichain pools:",sum(1 for p in y if p['chain']=='Unichain'))
for f in ['uniswapv4','euler','morpho']:
    pr=json.load(open(D+f'/llama_proto_{f}.json'))
    ct=pr.get('chainTvls',{}).get('Unichain',{}).get('tvl',[])
    s=[f"{ts(p['date'])}:{p['totalLiquidityUSD']/1e6:,.1f}" for p in ct if ts(p['date'])[8:10]=='01']
    print(f,"Unichain TVL $M monthly:"," ".join(s[-20:]), "| last", ts(ct[-1]['date']) if ct else None, round(ct[-1]['totalLiquidityUSD']/1e6,2) if ct else None)
