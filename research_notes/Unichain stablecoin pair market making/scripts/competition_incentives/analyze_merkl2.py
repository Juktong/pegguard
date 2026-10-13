import json, sys, datetime, collections, ast
D=sys.argv[1]
camps=json.load(open(D+'/merkl_all_campaigns_130.json'))
opps=json.load(open(D+'/merkl_all_opportunities_130.json'))
oppmap={o['id']:o for o in opps}
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
# UNI by month for gauntlet creators
uni_m=collections.Counter(); uni_type=collections.Counter()
for c in camps:
    rt=c.get('rewardToken') or {}
    cr=(c.get('creator') or {}).get('creatorId') or c['creatorAddress']
    if rt.get('symbol')=='UNI':
        amt=int(c['amount'])/1e18
        uni_m[ts(c['startTimestamp'])[:7]]+=amt
        uni_type[c['type']]+=amt
print("UNI rewards by campaign start month (all creators):")
for k in sorted(uni_m): print("  ",k,f"{uni_m[k]:,.0f} UNI")
print("UNI total",f"{sum(uni_m.values()):,.0f}")
print("UNI by type:",{k:round(v) for k,v in uni_type.items()})
print("UNI price now:",[ (c['rewardToken'] or {}).get('price') for c in camps if (c.get('rewardToken') or {}).get('symbol')=='UNI'][:1])
print("\n=== UniswapV4 USDC-USDT0 0.01% / Bunni campaigns detail ===")
for c in sorted(camps,key=lambda c:c['startTimestamp']):
    o=oppmap.get(c.get('opportunityId'),{})
    n=o.get('name','')
    if ('USDC-USD₮0' in n or 'USDC-USDT' in n) and ('Uniswap' in n or 'Bunni' in n or 'Gamma' in n):
        rt=c.get('rewardToken') or {}
        p=c.get('params')
        try: p=json.loads(p) if isinstance(p,str) else p
        except Exception:
            try: p=ast.literal_eval(p)
            except Exception: pass
        keep={}
        if isinstance(p,dict):
            for k in ['weightFees','weightToken0','weightToken1','isOutOfRangeIncentivized','whitelist','blacklist','hooks','lowerPriceTolerance','upperPriceTolerance','poolId','fee','targetToken','symbolRewardToken','priceTolerance','lowerPriceBond','upperPriceBond','url']:
                if k in p: keep[k]=p[k]
        print(f"{ts(c['startTimestamp'])}->{ts(c['endTimestamp'])} {n} | {int(c['amount'])/10**rt.get('decimals',18):,.0f} {rt.get('symbol')} | creator={(c.get('creator') or {}).get('creatorId')} | {json.dumps(keep,default=str)[:500]}")
print("\n=== Opportunity snapshot for those (tvl/apr fields) ===")
for o in opps:
    n=o['name']
    if ('USD₮0' in n or 'USDT' in n or 'USDC' in n) and ('Uniswap' in n or 'Bunni' in n):
        print(n,'| tvl',o.get('tvl'),'| apr',o.get('apr'),'| status',o.get('status'),'| last',ts(o.get('lastCampaignCreatedAt') or 0), '| tokens',[t['symbol'] for t in o.get('tokens',[])])
print("\n=== Campaigns started 2026 ===")
for c in sorted(camps,key=lambda c:c['startTimestamp']):
    if c['startTimestamp']>=1767225600:
        o=oppmap.get(c.get('opportunityId'),{}); rt=c.get('rewardToken') or {}
        print(f"{ts(c['startTimestamp'])}->{ts(c['endTimestamp'])} {c['type']} {(c.get('creator') or {}).get('creatorId') or c['creatorAddress'][:10]} {int(c['amount'])/10**rt.get('decimals',18):,.1f} {rt.get('symbol')} | {o.get('name','?')[:80]}")
