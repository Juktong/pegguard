import json, sys, datetime, collections
D=sys.argv[1]
camps=json.load(open(D+'/merkl_all_campaigns_130.json'))
opps=json.load(open(D+'/merkl_all_opportunities_130.json'))
oppmap={o['id']:o for o in opps}
def ts(t): return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')
STABLES={'USDC','USDT','USDT0','USD₮0','DAI','USDS','USDe','sUSDe','sUSDS','FRAX','frxUSD','USDbC','PYUSD','GHO','LUSD','crvUSD','EURC','USDG','RLUSD','USR','BOLD','USD0','USDtb','deUSD','rUSD','USDa','USDai','wUSDC','USDC.e','AUSD','USDQ','USDL','USDN','sUSDC','DOLA','agEUR','EURe','mUSD','USDH','USDX','yUSD'}
def is_stable(sym):
    s=sym.replace('.e','')
    return sym in STABLES or s in STABLES or 'USD' in sym.upper() or 'EUR' in sym.upper()
print("n campaigns",len(camps),"n opps",len(opps))
# overall by creator and year-month
by_creator=collections.Counter(); by_month=collections.Counter(); usd_creator=collections.Counter()
rows=[]
for c in camps:
    rt=c.get('rewardToken') or {}
    dec=rt.get('decimals',18); price=rt.get('price') or 0
    amt=int(c['amount'])/10**dec
    usd=amt*price
    cr=(c.get('creator') or {}).get('creatorId') or c['creatorAddress']
    o=oppmap.get(c.get('opportunityId'),{})
    name=o.get('name','?')
    toks=[t['symbol'] for t in o.get('tokens',[])]
    proto=(o.get('protocol') or {}).get('id','?')
    rows.append(dict(start=ts(c['startTimestamp']),end=ts(c['endTimestamp']),type=c['type'],creator=cr,rt=rt.get('symbol'),amt=amt,usd=usd,name=name,toks=toks,proto=proto,oppid=c.get('opportunityId'),dur=(c['endTimestamp']-c['startTimestamp'])/86400))
    by_creator[cr]+=1; usd_creator[cr]+=usd; by_month[ts(c['startTimestamp'])[:7]]+=1
print("\nCampaign counts by creator:"); 
for k,v in by_creator.most_common(30): print(f"  {k}: {v} campaigns, ~${usd_creator[k]:,.0f} at CURRENT token price")
print("\nCampaign starts by month:")
for k in sorted(by_month): print("  ",k,by_month[k])
print("\nCampaign types:",collections.Counter(r['type'] for r in rows).most_common())
print("\nReward tokens:",collections.Counter(r['rt'] for r in rows).most_common(20))
# latest end date
print("\nLatest campaign end:",max(r['end'] for r in rows))
print("Campaigns ending >= 2026-06-01:")
for r in sorted(rows,key=lambda r:r['end']):
    if r['end']>='2026-06-01' and r['type']!='JSON_AIRDROP':
        print(f"  {r['start']}->{r['end']} {r['type']} {r['creator']} {r['rt']} {r['amt']:,.0f} (${r['usd']:,.0f}) | {r['name'][:80]}")
# Stable-pair pool campaigns
print("\n=== Stable-pair (both tokens stable) pool campaigns ===")
sp=[r for r in rows if len(r['toks'])>=2 and all(is_stable(t) for t in r['toks'][:2]) and r['type'] not in ('JSON_AIRDROP',)]
agg=collections.defaultdict(lambda: dict(n=0,usd=0,first='9999',last='0000',creators=set(),rts=set(),types=set()))
for r in sp:
    a=agg[r['name']]; a['n']+=1; a['usd']+=r['usd']; a['first']=min(a['first'],r['start']); a['last']=max(a['last'],r['end']); a['creators'].add(r['creator']); a['rts'].add(r['rt']); a['types'].add(r['type'])
for k,a in sorted(agg.items(),key=lambda kv:-kv[1]['usd']):
    print(f"  {k[:90]} | n={a['n']} ${a['usd']:,.0f} | {a['first']}->{a['last']} | {sorted(a['creators'])} | {sorted(a['rts'])} | {sorted(a['types'])}")
json.dump(rows,open(D+'/merkl_campaign_rows.json','w'),default=list)
