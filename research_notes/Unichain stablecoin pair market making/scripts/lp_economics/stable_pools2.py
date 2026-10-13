import json, sys
d = json.load(open(sys.argv[1]))['data']
minTVL=float(sys.argv[2])
chains=set(sys.argv[3].split(','))
stables = {'USDC','USDT','DAI','USDE','USDT0','USDC.E','USDBC','FRAX','USDS','PYUSD','GHO','LUSD','CRVUSD','FDUSD','USD1','SUSDE','RLUSD','USD0','USDG','USDTB','DOLA','USDP','TUSD','USDM','AUSD','USD₮0','FRXUSD','USDT.E','BUSD','USDB','EURC','USDBC','MUSD','DUSD','SDAI','USDX','USDN'}
rows=[]
for p in d:
    sym = p['symbol'].upper()
    parts = [s for s in sym.replace('/','-').split('-') if s]
    if len(parts)!=2: continue
    if not all(x in stables for x in parts): continue
    if p.get('exposure')!='multi': continue
    if (p.get('tvlUsd') or 0) < minTVL: continue
    if 'ALL' not in chains and p['chain'] not in chains: continue
    rows.append(p)
rows.sort(key=lambda p:(p['chain'],-p['tvlUsd']))
print(f"{'chain':10} {'project':22} {'symbol':13} {'meta':22} {'tvl$M':>7} {'apyB':>6} {'apyR':>6} {'vol1d$M':>8} {'vol7d$M':>8} {'turn7d/d':>8} {'feeBpsImpl':>9}")
for p in rows:
    v1=p.get('volumeUsd1d') or 0; v7=p.get('volumeUsd7d') or 0
    turn = v7/7/p['tvlUsd']
    fee_impl = (p.get('apyBase') or 0)/100*p['tvlUsd']/365/v1*1e4 if v1>0 else float('nan')
    print(f"{p['chain'][:10]:10} {p['project'][:22]:22} {p['symbol'][:13]:13} {str(p.get('poolMeta'))[:22]:22} {p['tvlUsd']/1e6:7.2f} {p.get('apyBase') or 0:6.2f} {p.get('apyReward') or 0:6.2f} {v1/1e6:8.2f} {v7/1e6:8.2f} {turn:8.3f} {fee_impl:9.3f}")
