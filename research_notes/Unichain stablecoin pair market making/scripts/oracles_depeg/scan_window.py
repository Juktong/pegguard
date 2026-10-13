# Find blocks for a UTC time window by binary search, then scan Pyth USDC/USDT logs in that window.
import sys, json, time
sys.path.insert(0, sys.argv[1])
from rpc import call
url, pyth, out, t0, t1, step = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
T='0xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec'
IDS=['0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a','0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b']
def bts(n): return int(call(url,'eth_getBlockByNumber',[hex(n),False])['timestamp'],16)
def find(ts):
    lo,hi=1,int(call(url,'eth_blockNumber',[]),16)
    while lo<hi:
        m=(lo+hi)//2
        if bts(m)<ts: lo=m+1
        else: hi=m
    return lo
b0,b1=find(t0),find(t1); print('blocks',b0,b1,flush=True)
n=0
with open(out,'w') as f:
    b=b0
    while b<=b1:
        e=min(b+step-1,b1)
        logs=call(url,'eth_getLogs',[{"address":pyth,"topics":[T,IDS],"fromBlock":hex(b),"toBlock":hex(e)}])
        for L in logs:
            d=L['data'][2:]; pt=int(d[0:64],16); pr=int(d[64:128],16); cf=int(d[128:192],16)
            if pr>=1<<255: pr-=1<<256
            f.write(json.dumps({"block":int(L['blockNumber'],16),"tx":L['transactionHash'],"id":L['topics'][1][2:10],"publishTime":pt,"price":pr,"conf":cf})+"\n"); n+=1
        b=e+1; time.sleep(0.1)
print('logs',n)
