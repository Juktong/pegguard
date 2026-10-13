# Scan all Pyth PriceFeedUpdate logs on an EVM chain in chunks; write jsonl
import sys, json, time
sys.path.insert(0, sys.argv[1])
from rpc import call
url, pyth, out, start, end, step = sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
T='0xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec'
n=0
with open(out,'w') as f:
    b=start
    while b<=end:
        e=min(b+step-1,end)
        try:
            logs=call(url,'eth_getLogs',[{"address":pyth,"topics":[T],"fromBlock":hex(b),"toBlock":hex(e)}])
        except Exception as ex:
            print('ERR',b,e,str(ex)[:100]); b=e+1; continue
        for L in logs:
            d=L['data'][2:]
            pt=int(d[0:64],16); pr=int(d[64:128],16); cf=int(d[128:192],16)
            if pr>=1<<255: pr-=1<<256
            f.write(json.dumps({"block":int(L['blockNumber'],16),"tx":L['transactionHash'],"id":L['topics'][1][2:],"publishTime":pt,"price":pr,"conf":cf})+"\n"); n+=1
        b=e+1
        time.sleep(0.15)
print('logs',n)
