import json,sys,datetime,collections
D=sys.argv[1]
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
def series(fn):
    d=json.load(open(D+'/'+fn)); out={}
    for t,b in d.get('totalDataChartBreakdown') or []:
        v=b.get('Unichain') or b.get('unichain')
        if v is not None: out[ts(t)]=sum(v.values()) if isinstance(v,dict) else v
    return out
rev=series('llama_rev_v3.json'); fee=series('llama_fees_v3.json')
nz=[k for k in sorted(rev) if rev[k]>0]
print("Unichain v3-adapter revenue first nonzero:",nz[:3],"count nonzero",len(nz))
mon=collections.defaultdict(lambda:[0,0])
for k in fee: mon[k[:7]][0]+=fee[k]
for k in rev: mon[k[:7]][1]+=rev[k]
for m in sorted(mon):
    f,r=mon[m]
    if m>='2025-11': print(f"  {m} v3 fees ${f:,.0f} revenue ${r:,.0f} ratio {r/f if f else 0:.3f}")
d=json.load(open(D+'/llama_rev_v3.json'))
print(d.get('methodology',{}).get('Revenue'))
print([k for k in d.keys()])
