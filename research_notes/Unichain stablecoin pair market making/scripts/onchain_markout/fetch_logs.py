"""Fetch v4 PoolManager Swap/ModifyLiquidity/Donate logs for given pool ids and v3 pool
Swap/Mint/Burn/Collect logs, in 10k-block chunks, into JSONL (resumable)."""
import sys, json, os, time
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpcutil import *
PM='0x1f98400000000000000000000000000000000004'
T4=['0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f','0xf208f4912782fd25c7f114ca3723a2d5dd6f3bcc3ac8db5af63baa85f711d5ec','0x29ef05caaff9404b7cb6d1c0e9bbae9eaa7ab2541feba1a9c4248594c08156cb']
T3=['0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67','0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde','0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c','0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0']
start=int(sys.argv[1]); end=int(sys.argv[2]); out=sys.argv[3]
ids=sys.argv[4].split(','); v3=sys.argv[5].split(',')
CH=10000
done=set()
prog=out+'.progress'
if os.path.exists(prog):
    done=set(int(x) for x in open(prog).read().split())
f=open(out,'a'); pf=open(prog,'a')
n=0; t0=time.time()
for a in range(start, end+1, CH):
    if a in done: continue
    b=min(a+CH-1, end)
    r4=call('eth_getLogs',[{'address':PM,'fromBlock':hex(a),'toBlock':hex(b),'topics':[T4,ids]}])
    r3=call('eth_getLogs',[{'address':v3,'fromBlock':hex(a),'toBlock':hex(b),'topics':[T3]}]) if v3 != ['none'] else []
    for lg in r4+r3:
        f.write(json.dumps(lg)+'\n')
    f.flush(); pf.write(f'{a}\n'); pf.flush()
    n+=len(r4)+len(r3)
    time.sleep(0.15)
print('logs',n,'secs',round(time.time()-t0,1))
