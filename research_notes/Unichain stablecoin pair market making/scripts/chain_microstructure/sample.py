import json, sys, urllib.request, statistics as st, collections, concurrent.futures as cf
sys.path.insert(0,'/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/chain_microstructure')
from k256 import sel, topic
URL='https://mainnet.unichain.org'; OUT=sys.argv[1]; NB=int(sys.argv[2]) if len(sys.argv)>2 else 300
_id=[0]
def rpc(m,p,tries=5):
    import time
    for k in range(tries):
        try:
            _id[0]+=1
            req=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":_id[0],"method":m,"params":p}).encode(),headers={"Content-Type":"application/json","User-Agent":"curl/8"})
            with urllib.request.urlopen(req,timeout=90) as r: j=json.loads(r.read())
            if 'error' in j: raise RuntimeError(json.dumps(j['error'])[:300])
            return j['result']
        except Exception as e:
            if k==tries-1 or (m=='eth_getLogs' and 'HTTP Error 400' in str(e)): raise
            time.sleep(1+2*k)
H=lambda x:int(x,16) if x else 0
PM='0x1f98400000000000000000000000000000000004'
T={'v4Swap':topic('Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)'),
   'v4Modify':topic('ModifyLiquidity(bytes32,address,int24,int24,int256,bytes32)'),
   'v4Init':topic('Initialize(bytes32,address,address,uint24,int24,address,uint160,int24)'),
   'pythUpdate':topic('PriceFeedUpdate(bytes32,uint64,int64,uint64)'),
   'v3Swap':topic('Swap(address,address,int256,int256,uint160,uint128,int24)'),
   'v2Swap':topic('Swap(address,uint256,uint256,uint256,uint256,address)'),
   'Transfer':topic('Transfer(address,address,uint256)')}
res={'topics':T}
bn=H(rpc('eth_blockNumber',[])); res['head']=bn
# log range limit tests
lr={}
for span in [1000,10000,50000,100000,500000]:
    try:
        l=rpc('eth_getLogs',[{'address':PM,'topics':[T['v4Swap']],'fromBlock':hex(bn-span),'toBlock':hex(bn)}]); lr[span]=f'ok {len(l)} logs'
    except Exception as e: lr[span]='err '+str(e)[:200]
res['getLogs_range_tests_PoolManager_Swap']=lr
# blocks with full txs + receipts
def getblk(n):
    b=rpc('eth_getBlockByNumber',[hex(n),True]); r=rpc('eth_getBlockReceipts',[hex(n)]); return n,b,r
blocks={}
with cf.ThreadPoolExecutor(8) as ex:
    for n,b,r in ex.map(getblk, range(bn-NB+1,bn+1)): blocks[n]=(b,r)
txs=[]; fails=0; total=0; per_block=[]; ordering_viol=0; ordering_blocks=0; tos=collections.Counter(); fail_tos=collections.Counter()
swap_tx=[]; mod_tx=[]; pyth_tx=[]; v3_tx=[]
for n in sorted(blocks):
    b,rs=blocks[n]; bf=H(b['baseFeePerGas']); rmap={r['transactionHash']:r for r in rs}
    user=[t for t in b['transactions'] if t['type']!='0x7e']
    per_block.append(len(user))
    tips=[]
    for t in user:
        r=rmap[t['hash']]; total+=1
        eff=H(r['effectiveGasPrice']); tip=eff-bf; tips.append(tip)
        ok=H(r['status'])==1
        if not ok: fails+=1; fail_tos[t.get('to')]+=1
        tos[t.get('to')]+=1
        l1=H(r.get('l1Fee','0x0')); gu=H(r['gasUsed'])
        rec={'blk':n,'idx':H(t['transactionIndex']),'hash':t['hash'],'to':t.get('to'),'from':t['from'],'gasUsed':gu,'gasLimit':H(t['gas']),'eff':eff,'tip':tip,'l1Fee':l1,'l2Fee':gu*eff,'ok':ok,'inputLen':(len(t['input'])-2)//2,'type':t['type'],
             'nSwapV4':sum(1 for lg in r['logs'] if lg['address'].lower()==PM and lg['topics'][0]==T['v4Swap']),
             'nModV4':sum(1 for lg in r['logs'] if lg['address'].lower()==PM and lg['topics'][0]==T['v4Modify']),
             'nPyth':sum(1 for lg in r['logs'] if lg['topics'] and lg['topics'][0]==T['pythUpdate']),
             'nV3':sum(1 for lg in r['logs'] if lg['topics'] and lg['topics'][0]==T['v3Swap']),
             'nV2':sum(1 for lg in r['logs'] if lg['topics'] and lg['topics'][0]==T['v2Swap']),
             'l1GasUsed':H(r.get('l1GasUsed','0x0')),'daFootprint':r.get('daFootprintGasScalar')}
        txs.append(rec)
    if len(tips)>=2:
        ordering_blocks+=1
        if any(tips[i]<tips[i+1] for i in range(len(tips)-1)): ordering_viol+=1
res['sample_blocks']=[min(blocks),max(blocks)]
res['user_tx_total']=total; res['user_tx_per_block']={'mean':st.mean(per_block),'median':st.median(per_block),'max':max(per_block)}
res['failed_tx']=fails; res['failed_share']=fails/max(total,1)
res['blocks_with_tip_order_violation']=f'{ordering_viol}/{ordering_blocks}'
res['top_to']=tos.most_common(12); res['top_fail_to']=fail_tos.most_common(8)
def stats(rows,key):
    v=[r[key] for r in rows]
    if not v: return None
    return {'n':len(v),'min':min(v),'p25':st.quantiles(v,n=4)[0] if len(v)>1 else v[0],'median':st.median(v),'p75':st.quantiles(v,n=4)[2] if len(v)>1 else v[0],'max':max(v),'mean':st.mean(v)}
for name,cond in [('all',lambda r:True),('ok',lambda r:r['ok']),('failed',lambda r:not r['ok']),
                  ('v4swap_single_ok',lambda r:r['ok'] and r['nSwapV4']==1 and r['nV3']==0 and r['nV2']==0),
                  ('v4swap_any_ok',lambda r:r['ok'] and r['nSwapV4']>=1),
                  ('v4modify_ok',lambda r:r['ok'] and r['nModV4']>=1 and r['nSwapV4']==0),
                  ('pyth_ok',lambda r:r['ok'] and r['nPyth']>=1),
                  ('v3swap_ok',lambda r:r['ok'] and r['nV3']>=1)]:
    rows=[r for r in txs if cond(r)]
    res['grp_'+name]={k:stats(rows,k) for k in ['gasUsed','eff','tip','l1Fee','l2Fee','inputLen']} if rows else None
    if rows: res['grp_'+name]['top_to']=collections.Counter(r['to'] for r in rows).most_common(6)
json.dump({'summary':res,'txs':txs},open(OUT,'w'),indent=1,default=str)
print(json.dumps(res,indent=1,default=str))
