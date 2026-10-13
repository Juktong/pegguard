import json,sys,urllib.request,time
from known import KNOWN
D=sys.argv[1]; FROM=int(sys.argv[2])
v4=json.load(open(D+'/v4_pools.json'))
st=[p for p in v4 if p['c0'] in KNOWN and p['c1'] in KNOWN]
SW='0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f'
PM='0x1f98400000000000000000000000000000000004'
summary={}
for i,p in enumerate(st):
    fn=f"{D}/v4sw30/{p['id']}.jsonl"
    allres=[]; frm=FROM; seen=set()
    while True:
        q=f"https://unichain.blockscout.com/api?module=logs&action=getLogs&fromBlock={frm}&toBlock=latest&address={PM}&topic0={SW}&topic1={p['id']}&topic0_1_opr=and"
        for a in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(q,headers={'user-agent':'research/1.0'}),timeout=90) as r: j=json.loads(r.read()); break
            except Exception as e: time.sleep(3*(a+1))
        res=j.get('result') or []
        if not isinstance(res,list): res=[]
        mx=frm
        for e in res:
            k=(e['transactionHash'],e['logIndex'])
            if k in seen: continue
            seen.add(k); allres.append(e); mx=max(mx,int(e['blockNumber'],16))
        if len(res)<1000: break
        frm=mx
        time.sleep(0.3)
    with open(fn,'w') as f:
        for e in allres: f.write(json.dumps(e)+'\n')
    summary[p['id']]=len(allres)
    if allres: print(i,p['id'][:14],KNOWN[p['c0']],KNOWN[p['c1']],p['fee'],p['hooks'][-6:],len(allres),flush=True)
    time.sleep(0.25)
json.dump(summary,open(D+'/v4sw30_summary.json','w'))
print('DONE')
