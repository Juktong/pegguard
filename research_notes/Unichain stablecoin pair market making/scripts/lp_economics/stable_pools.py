import json, sys
d = json.load(open(sys.argv[1]))['data']
print('keys', list(d[0].keys()))
stables = {'USDC','USDT','DAI','USDE','USDT0','USDC.E','USDBC','FRAX','USDS','PYUSD','GHO','LUSD','CRVUSD','FDUSD','USD1','SUSDE','RLUSD','USDGLO','USD0','USDG','USDTB','DOLA','USDP','TUSD','BUSD','USDM','AUSD','USD₮0','FRXUSD'}
rows=[]
for p in d:
    sym = p['symbol'].upper()
    parts = [s for s in sym.replace('/','-').split('-') if s]
    if len(parts)!=2: continue
    if not all(x in stables for x in parts): continue
    if p.get('exposure')!='multi': continue
    if (p.get('tvlUsd') or 0) < 2e6: continue
    rows.append(p)
rows.sort(key=lambda p:-p['tvlUsd'])
print(len(rows))
print(f"{'chain':10} {'project':24} {'symbol':14} {'meta':22} {'tvl$M':>8} {'apyBase':>7} {'apyRew':>7} {'apyB7d':>7} {'vol1d$M':>8} {'vol7d$M':>8} {'turn1d':>7} {'mean30d':>7}")
for p in rows[:120]:
    v1=p.get('volumeUsd1d'); v7=p.get('volumeUsd7d')
    turn = (v1/p['tvlUsd']) if v1 else None
    print(f"{p['chain'][:10]:10} {p['project'][:24]:24} {p['symbol'][:14]:14} {str(p.get('poolMeta'))[:22]:22} {p['tvlUsd']/1e6:8.1f} {p.get('apyBase') or 0:7.2f} {p.get('apyReward') or 0:7.2f} {p.get('apyBase7d') or 0:7.2f} {(v1 or 0)/1e6:8.2f} {(v7 or 0)/1e6:8.2f} {turn if turn is not None else float('nan'):7.3f} {p.get('apyMean30d') or 0:7.2f}")
