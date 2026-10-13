import rpc,json,datetime,time
D='/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/pool_landscape/data'
PM='0x1f98400000000000000000000000000000000004'; SW='0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f'
ids={'77ea':'0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9'}
AB,AT=61167971,1791916330
def tb(t): return AB-(AT-t)
out=[]
for y,m in [(2025,4),(2025,5),(2025,6),(2025,7),(2025,8),(2025,9),(2025,10),(2025,11),(2025,12),(2026,1),(2026,2),(2026,3),(2026,4),(2026,5),(2026,6),(2026,7),(2026,8),(2026,9),(2026,10)]:
    d=datetime.datetime(y,m,15 if (y,m)==(2025,4) else 2,tzinfo=datetime.UTC)
    b0=tb(int(d.timestamp())); b1=b0+3*86400
    calls=[('eth_getLogs',[{'fromBlock':hex(a),'toBlock':hex(min(b1,a+9999)),'address':PM,'topics':[SW,ids['77ea']]}]) for a in range(b0,b1,10000)]
    logs=[]
    for i in range(0,len(calls),10):
        for att in range(10):
            try:
                res=rpc.batch(calls[i:i+10])
                if any(isinstance(r,Exception) for r in res): raise RuntimeError('sub')
                break
            except Exception as e: time.sleep(3)
        for r in res: logs+=r
    vol=0; fee=0
    for e in logs:
        w=rpc.words(e['data']); a0=rpc.s(w[0]); a1=rpc.s(w[1]); f=rpc.u(w[5])
        amt=-a0/1e6 if a0<0 else -a1/1e6; vol+=amt; fee+=amt*f/1e6
    out.append(dict(start=str(d.date()),days=3,swaps=len(logs),vol=vol,avg_daily_vol=vol/3,fees=fee))
    print(d.date(),'swaps',len(logs),'3d vol',round(vol),'avg/day',round(vol/3),flush=True)
json.dump(out,open(D+'/vol_sample_77ea.json','w'))
