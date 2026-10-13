import json, sys, urllib.request, statistics as st, collections, time
sys.path.insert(0,'/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/chain_microstructure')
from k256 import sel, topic
URL='https://mainnet.unichain.org'; OUT=sys.argv[1]
def rpc(m,p):
    for k in range(4):
        try:
            req=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p}).encode(),headers={"Content-Type":"application/json","User-Agent":"curl/8"})
            with urllib.request.urlopen(req,timeout=90) as r: j=json.loads(r.read())
            if 'error' in j: raise RuntimeError(json.dumps(j['error'])[:300])
            return j['result']
        except Exception as e:
            if k==3: raise
            time.sleep(2)
H=lambda x:int(x,16) if x else 0
def s64(x): x&=(1<<64)-1; return x-(1<<64) if x>>63 else x
def s32(x): x&=(1<<32)-1; return x-(1<<32) if x>>31 else x
PY='0x2880aB155794e7179c9eE2e38200202908C17B43'
feeds={'ETH/USD':'ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace','USDC/USD':'eaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a','USDT/USD':'2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b'}
res={}
now=H(rpc('eth_getBlockByNumber',['latest',False])['timestamp']); res['now_ts']=now
for k,f in feeds.items():
    try:
        r=rpc('eth_call',[{'to':PY,'data':sel('getPriceUnsafe(bytes32)')+f},'latest'])[2:]
        w=[int(r[i:i+64],16) for i in range(0,len(r),64)]
        price=s64(w[0]); conf=w[1]; expo=s32(w[2]); pt=w[3]
        res[k]={'price':price*10**expo,'conf':conf*10**expo,'publishTime':pt,'age_s':now-pt}
    except Exception as e: res[k]={'err':str(e)[:200]}
# Pyth PriceFeedUpdate logs over recent windows
T=topic('PriceFeedUpdate(bytes32,uint64,int64,uint64)')
head=H(rpc('eth_blockNumber',[]))
logs=[]; spans=[]
for i in range(30):
    a=head-(i+1)*10000+1; b=head-i*10000
    try:
        l=rpc('eth_getLogs',[{'address':PY,'topics':[T],'fromBlock':hex(a),'toBlock':hex(b)}]); logs+=l; spans.append((a,b,len(l)))
    except Exception as e: spans.append((a,b,'err '+str(e)[:100]))
res['pyth_log_windows']=spans
res['pyth_updates_total']=len(logs)
txh=collections.Counter(l['transactionHash'] for l in logs)
res['pyth_update_txs']=len(txh)
res['pyth_feed_counts']=collections.Counter(l['topics'][1] for l in logs).most_common(10)
rec=[]
for h,_ in list(txh.items())[:60]:
    r=rpc('eth_getTransactionReceipt',[h]); t=rpc('eth_getTransactionByHash',[h])
    n_upd=sum(1 for lg in r['logs'] if lg['topics'] and lg['topics'][0]==T)
    n_swap=sum(1 for lg in r['logs'] if lg['topics'] and lg['topics'][0]==topic('Swap(bytes32,address,int128,int128,uint160,uint128,int24,uint24)'))
    rec.append({'h':h,'to':t['to'],'from':t['from'],'gasUsed':H(r['gasUsed']),'n_upd':n_upd,'n_v4swap':n_swap,'value':H(t['value']),'eff':H(r['effectiveGasPrice']),'l1Fee':H(r.get('l1Fee')),'inputLen':(len(t['input'])-2)//2,'status':H(r['status'])})
res['pyth_tx_samples']=rec
by=collections.defaultdict(list)
for x in rec: by[x['n_upd']].append(x['gasUsed'])
res['pyth_gas_by_n_updates']={k:{'n':len(v),'median':st.median(v),'min':min(v),'max':max(v)} for k,v in sorted(by.items())}
res['pyth_value_paid']=collections.Counter(x['value'] for x in rec).most_common(5)
res['pyth_to']=collections.Counter(x['to'] for x in rec).most_common(5)
json.dump(res,open(OUT,'w'),indent=1)
r2={k:v for k,v in res.items() if k!='pyth_tx_samples'}
print(json.dumps(r2,indent=1))
print(json.dumps(rec[:8],indent=0))
