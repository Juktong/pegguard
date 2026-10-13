import json, sys, urllib.request, statistics as st, concurrent.futures as cf, time, random
URL='https://mainnet.unichain.org'; OUT=sys.argv[1]
def rpc(m,p,tries=4):
    for k in range(tries):
        try:
            req=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"Content-Type":"application/json","User-Agent":"curl/8"})
            with urllib.request.urlopen(req,timeout=90) as r: j=json.loads(r.read())
            if 'error' in j: raise RuntimeError(json.dumps(j['error'])[:300])
            return j['result']
        except Exception as e:
            if k==tries-1: raise
            time.sleep(1+2*k)
H=lambda x:int(x,16) if x else 0
head=H(rpc('eth_blockNumber',[]))
# sample every 6h back to genesis-ish (block ~0 at Feb 2025); 1s blocks => 21600 blocks per 6h
pts=list(range(head-1024, 1100, -21600))
def one(n):
    try:
        fh=rpc('eth_feeHistory',[hex(1024),hex(n),[50,90,99]])
        b=rpc('eth_getBlockByNumber',[hex(n),False])
        bf=[H(x) for x in fh['baseFeePerGas'][:-1]]; r=[[H(v) for v in rr] for rr in fh['reward']]
        return {'n':n,'ts':H(b['timestamp']),'ntx':len(b['transactions']),'gasLimit':H(b['gasLimit']),'gasUsed':H(b['gasUsed']),'extra':b['extraData'],
                'bf_min':min(bf),'bf_med':st.median(bf),'bf_max':max(bf),'gur_mean':st.mean(fh['gasUsedRatio']),
                'tip50_med':st.median(x[0] for x in r),'tip90_med':st.median(x[1] for x in r),'tip99_max':max(x[2] for x in r)}
    except Exception as e: return {'n':n,'err':str(e)[:200]}
out=[]
with cf.ThreadPoolExecutor(6) as ex:
    for x in ex.map(one,pts): out.append(x)
json.dump(out,open(OUT,'w'))
print('done',len(out),sum(1 for x in out if 'err' in x))
