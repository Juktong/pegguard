import rpc,json,sys,collections,math
def load(fn):
    out=[]
    for l in open(fn):
        e=json.loads(l); w=rpc.words(e['data'])
        a0=rpc.s(w[0]); a1=rpc.s(w[1])
        out.append(dict(block=int(e['blockNumber'],16),t=int(e['timeStamp'],16),tx=e['transactionHash'],li=int(e['logIndex'],16),sender=rpc.addr(e['topics'][2]),a0=a0,a1=a1,sqrtP=rpc.u(w[2]),L=rpc.u(w[3]),tick=rpc.s(w[4]),fee=rpc.u(w[5])))
    return out
def stats(sw,now,dec0=6,dec1=6,label=''):
    res={}
    for name,win in [('24h',86400),('7d',7*86400),('30d',30*86400)]:
        S=[x for x in sw if x['t']>now-win]
        vol=0; fees=0
        for x in S:
            # v4: swapper delta; negative = paid in
            if x['a0']<0: amt=-x['a0']/10**dec0
            else: amt=-x['a1']/10**dec1
            vol+=amt; fees+=amt*x['fee']/1e6
        res[name]=dict(n=len(S),vol=vol,fees=fees,senders=len(set(x['sender'] for x in S)))
    return res
if __name__=='__main__':
    fn=sys.argv[1]; now=int(sys.argv[2]); d0=int(sys.argv[3]); d1=int(sys.argv[4])
    sw=load(fn)
    print('events',len(sw),'first',min(x['t'] for x in sw) if sw else None)
    r=stats(sw,now,d0,d1)
    for k,v in r.items(): print(k,{kk:(round(vv,2) if isinstance(vv,float) else vv) for kk,vv in v.items()})
    c=collections.Counter(x['sender'] for x in sw)
    print('top senders (router/contract that called PM.swap):',c.most_common(8))
    fees=collections.Counter(x['fee'] for x in sw); print('fee values',fees.most_common(5))
    ticks=[x['tick'] for x in sw]; print('tick range over window',min(ticks),max(ticks))
    # size distribution
    sizes=sorted((-x['a0'] if x['a0']<0 else -x['a1'])/10**6 for x in sw)
    if sizes:
        q=lambda p:sizes[min(len(sizes)-1,int(p*len(sizes)))]
        print('size quantiles p10 p50 p90 p99 max',[round(q(p),2) for p in (0.1,0.5,0.9,0.99)],round(sizes[-1],2))
    dirn=collections.Counter('0->1' if x['a0']<0 else '1->0' for x in sw); print('direction',dirn)
