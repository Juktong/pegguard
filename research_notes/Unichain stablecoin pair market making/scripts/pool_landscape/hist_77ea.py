import rpc,json,collections,datetime,sys
D='/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/pool_landscape/data'
pid='0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9'
SV='0x86e8631a016f9068c3f085faf484ee3f5fdee8f2'
AB,AT=61167971,1791916330
def bt(b): return AT-(AB-b)
def tb(t): return AB-(AT-t)
evs={}
for fn in ['v4logs/ml_77ea.jsonl','v4logs/ml_77ea_part2.jsonl']:
    for l in open(D+'/'+fn):
        e=json.loads(l); evs[(e['transactionHash'],int(e['logIndex'],16))]=e
evs=sorted(evs.values(),key=lambda e:(int(e['blockNumber'],16),int(e['logIndex'],16)))
parsed=[]
for e in evs:
    w=rpc.words(e['data']); parsed.append((int(e['blockNumber'],16),rpc.addr(e['topics'][2]),rpc.s(w[0]),rpc.s(w[1]),rpc.s(w[2]),w[3]))
# snapshot dates
dates=[datetime.datetime(2025,m,1,tzinfo=datetime.UTC) for m in range(3,13)]+[datetime.datetime(2026,m,1,tzinfo=datetime.UTC) for m in range(1,11)]+[datetime.datetime(2026,10,13,18,0,tzinfo=datetime.UTC)]
i=0; pos=collections.defaultdict(int)
out=[]
for d in dates:
    B=tb(int(d.timestamp()))
    while i<len(parsed) and parsed[i][0]<=B:
        b,s,tl,tu,dl,salt=parsed[i]; pos[(s,tl,tu,salt)]+=dl; i+=1
    try:
        w=rpc.words(rpc.eth_call(SV,rpc.sel('getSlot0(bytes32)')+pid[2:],hex(B)))
    except Exception as ex:
        print(d.date(),'err',ex); continue
    sqrtP=rpc.u(w[0]); tick=rpc.s(w[1])
    if sqrtP==0: print(d.date(),'not initialized'); continue
    sp=sqrtP/2**96
    t0=t1=0; n=0; inb=collections.Counter()
    for (s,tl,tu,salt),L in pos.items():
        if L<=0: continue
        n+=1
        sa=1.0001**(tl/2); sb=1.0001**(tu/2)
        if sp<=sa: a0=L*(sb-sa)/(sa*sb); a1=0
        elif sp>=sb: a0=0; a1=L*(sb-sa)
        else: a0=L*(sb-sp)/(sp*sb); a1=L*(sp-sa)
        t0+=a0/1e6; t1+=a1/1e6
    owners=len(set(k[0] if k[0]!='0x4529a01c7a0410167c5740c487a8de60232617bf' else k[3] for k,v in pos.items() if v>0))
    out.append(dict(date=str(d.date()),block=B,tick=tick,price=sp*sp,tvl=t0+t1,usdc=t0,usdt0=t1,positions=n))
    print(f"{d.date()} block {B} tick {tick} price {sp*sp:.6f} TVL {t0+t1:,.0f} (USDC {t0:,.0f} / USDT0 {t1:,.0f}) active positions {n}",flush=True)
json.dump(out,open(D+'/hist_77ea.json','w'))
