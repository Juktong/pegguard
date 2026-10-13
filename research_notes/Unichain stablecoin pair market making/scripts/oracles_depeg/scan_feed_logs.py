# Scan Pyth PriceFeedUpdate logs for selected feed ids (topic1 OR) in fixed block chunks.
import sys, json, time
sys.path.insert(0, sys.argv[1])
from rpc import call
url, pyth, out, days, step = sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]), int(sys.argv[6])
T='0xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec'
IDS=['0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a','0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b']
head=int(call(url,'eth_blockNumber',[]),16)
bh=call(url,'eth_getBlockByNumber',[hex(head),False]); bo=call(url,'eth_getBlockByNumber',[hex(head-100000),False])
bt=(int(bh['timestamp'],16)-int(bo['timestamp'],16))/100000
start=max(0,int(head-days*86400/bt))
print('head',head,'blocktime',bt,'start',start,flush=True)
n=0; errs=0
with open(out,'w') as f:
    b=start
    while b<=head:
        e=min(b+step-1,head)
        try:
            logs=call(url,'eth_getLogs',[{"address":pyth,"topics":[T,IDS],"fromBlock":hex(b),"toBlock":hex(e)}])
        except Exception as ex:
            errs+=1; print('ERR',b,str(ex)[:80],flush=True); time.sleep(2)
            b=e+1; continue
        for L in logs:
            d=L['data'][2:]
            pt=int(d[0:64],16); pr=int(d[64:128],16); cf=int(d[128:192],16)
            if pr>=1<<255: pr-=1<<256
            f.write(json.dumps({"block":int(L['blockNumber'],16),"tx":L['transactionHash'],"li":int(L['logIndex'],16),"id":L['topics'][1][2:10],"publishTime":pt,"price":pr,"conf":cf})+"\n"); n+=1
        b=e+1
        time.sleep(0.12)
print('logs',n,'errs',errs,flush=True)
