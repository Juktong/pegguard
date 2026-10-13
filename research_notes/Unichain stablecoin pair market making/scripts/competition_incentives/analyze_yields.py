import json, sys
D=sys.argv[1]
fc=json.load(open(D+'/llama_fees_unichain_chain.json'))
print("Unichain fees methodology:",fc.get('methodology'), fc.get('name'), fc.get('category'))
y=json.load(open(D+'/llama_yields_pools.json'))['data']
print("total pools",len(y))
for p in y:
    if p['pool'].startswith('aa70268e'): print("aa70268e pool:",p['project'],p['symbol'],p['chain'])
print("\n=== Unichain pools (DefiLlama yields) tvl>$20k ===")
u=[p for p in y if p['chain']=='Unichain']
for p in sorted(u,key=lambda p:-(p['tvlUsd'] or 0)):
    if (p['tvlUsd'] or 0)>20000:
        print(f"  {p['project']} | {p['symbol']} | {p.get('poolMeta')} | tvl ${p['tvlUsd']/1e6:,.2f}M | apy {p.get('apy')} base {p.get('apyBase')} rew {p.get('apyReward')} | base7d {p.get('apyBase7d')} | mean30d {p.get('apyMean30d')} | stable {p.get('stablecoin')} | exposure {p.get('exposure')} | pool {p['pool'][:12]}")
print("\n=== Benchmarks (other chains) ===")
want=[('sky-lending','SUSDS'),('spark-savings',None),('ethena-usde','SUSDE'),('ethena',None),('aave-v3','USDC'),('aave-v3','USDT'),('compound-v3','USDC'),('morpho-blue','USDC'),('morpho-v1','USDC'),('maple','USDC'),('sky',None),('ondo',None),('blackrock-buidl',None),('superstate',None),('franklin',None),('openeden',None),('usual',None),('fluid-lending','USDC'),('euler-v2','USDC')]
for p in sorted(y,key=lambda p:-(p['tvlUsd'] or 0)):
    proj=p['project']; sym=p['symbol']
    hit=False
    for wp,ws in want:
        if proj.startswith(wp) and (ws is None or sym.upper()==ws):
            hit=True
    if hit and p['tvlUsd']>100e6 and p['chain'] in ('Ethereum','Base','Arbitrum','OP Mainnet','Unichain'):
        print(f"  {proj} | {p['chain']} | {sym} | {p.get('poolMeta')} | tvl ${p['tvlUsd']/1e6:,.0f}M | apy {p.get('apy')} base {p.get('apyBase')} rew {p.get('apyReward')} | mean30d {p.get('apyMean30d')} | pool {p['pool']}")
print("\n=== RWA / T-bill style pools tvl>50M ===")
for p in sorted(y,key=lambda p:-(p['tvlUsd'] or 0)):
    s=(p['symbol']+' '+p['project']+' '+str(p.get('poolMeta'))).lower()
    if any(k in s for k in ['buidl','ustb','ousg','usyc','benji','tbill','t-bill','bill','usdy','wtgxx','treasur','stbt','jtrsy','usdtb']) and p['tvlUsd']>50e6:
        print(f"  {p['project']} | {p['chain']} | {p['symbol']} | {p.get('poolMeta')} | tvl ${p['tvlUsd']/1e6:,.0f}M | apy {p.get('apy')} | mean30d {p.get('apyMean30d')} | pool {p['pool']}")
