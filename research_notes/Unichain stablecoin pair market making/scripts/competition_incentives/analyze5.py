import json,sys,datetime,collections
D=sys.argv[1]
def ts(t): return datetime.datetime.fromtimestamp(int(t),datetime.UTC).strftime('%Y-%m-%d')
f=json.load(open(D+'/llama_fees_unichain_chainfees.json'))
print("Unichain chain fees: methodology",f.get('methodology'))
for k in ['total24h','total30d','total1y','totalAllTime']: print('  ',k,f.get(k))
mm=collections.Counter()
for t,v in f.get('totalDataChart',[]): mm[ts(t)[:7]]+=v
print('  monthly fees:',{k:round(v) for k,v in sorted(mm.items())})
for n in ['rev_v3','rev_v4','fees_v4']:
    d=json.load(open(D+f'/llama_{n}.json'))
    cb=d.get('totalDataChartBreakdown') or []
    # chain breakdown for last 30 days
    agg=collections.Counter(); 
    for t,b in cb[-30:]:
        for ch,v in b.items():
            agg[ch]+=sum(v.values()) if isinstance(v,dict) else v
    print(n,'last30d by chain:',{k:round(v) for k,v in agg.most_common(15)})
    print(n,'unichain last30d:',round(agg.get('unichain',0) or agg.get('Unichain',0)))
    print('  methodology:',str(d.get('methodology'))[:600])
