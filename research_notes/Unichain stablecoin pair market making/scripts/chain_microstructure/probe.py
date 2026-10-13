import json, sys, time, urllib.request, statistics as st
sys.path.insert(0,'/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/chain_microstructure')
from k256 import sel, topic
URL=sys.argv[1] if len(sys.argv)>1 else 'https://mainnet.unichain.org'
OUT=sys.argv[2]
_id=0
def rpc(m,p):
    global _id; _id+=1
    req=urllib.request.Request(URL,data=json.dumps({"jsonrpc":"2.0","id":_id,"method":m,"params":p}).encode(),headers={"Content-Type":"application/json","User-Agent":"curl/8"})
    with urllib.request.urlopen(req,timeout=60) as r: j=json.loads(r.read())
    if 'error' in j: raise RuntimeError(json.dumps(j['error']))
    return j['result']
H=lambda x:int(x,16)
res={}
def call(to,data,blk='latest'):
    return rpc('eth_call',[{"to":to,"data":data},blk])
res['chainId']=H(rpc('eth_chainId',[]))
bn=H(rpc('eth_blockNumber',[])); res['blockNumber']=bn
res['eth_gasPrice_wei']=H(rpc('eth_gasPrice',[]))
try: res['eth_maxPriorityFeePerGas_wei']=H(rpc('eth_maxPriorityFeePerGas',[]))
except Exception as e: res['eth_maxPriorityFeePerGas_err']=str(e)
lb=rpc('eth_getBlockByNumber',['latest',False])
res['latest']={k:lb.get(k) for k in ['number','timestamp','baseFeePerGas','gasUsed','gasLimit','miner','extraData','blobGasUsed','excessBlobGas']}
res['latest']['ntx']=len(lb['transactions'])
# block time over windows
for back in [1000, 86400]:
    b=rpc('eth_getBlockByNumber',[hex(bn-back),False])
    res[f'avg_block_time_last_{back}']=(H(lb['timestamp'])-H(b['timestamp']))/back
    if back==86400:
        res['block_minus_86400_ts']=H(b['timestamp']); res['block_minus_86400_txcount']=len(b['transactions'])
# fee history
try:
    fh=rpc('eth_feeHistory',[hex(1024),'latest',[10,25,50,75,90,99]])
    bf=[H(x) for x in fh['baseFeePerGas']]; gur=fh['gasUsedRatio']
    rw=list(zip(*[[H(v) for v in r] for r in fh['reward']]))
    res['feeHistory']={'n':len(gur),'oldest':H(fh['oldestBlock']),
      'baseFee_wei':{'min':min(bf),'median':st.median(bf),'max':max(bf),'last':bf[-1]},
      'gasUsedRatio':{'mean':st.mean(gur),'median':st.median(gur),'max':max(gur)},
      'reward_pctiles_median_over_blocks_wei':{p:st.median(r) for p,r in zip([10,25,50,75,90,99],rw)},
      'reward_pctiles_max_over_blocks_wei':{p:max(r) for p,r in zip([10,25,50,75,90,99],rw)}}
    for k in ['baseFeePerBlobGas','blobGasUsedRatio']:
        if k in fh: res['feeHistory'][k+'_sample']=fh[k][-3:]
except Exception as e: res['feeHistory_err']=str(e)
# GasPriceOracle
GPO='0x420000000000000000000000000000000000000F'
for fn in ['l1BaseFee()','blobBaseFee()','baseFeeScalar()','blobBaseFeeScalar()','isFjord()','isEcotone()','isIsthmus()','decimals()','version()','isJovian()']:
    try:
        r=call(GPO,sel(fn)); res['GPO_'+fn]= H(r) if fn!='version()' else bytes.fromhex(r[2+128:2+128+64]).rstrip(b'\0').decode(errors='ignore')
    except Exception as e: res['GPO_'+fn+'_err']=str(e)[:120]
for size in [200,400,600,1000,1500]:
    try: res[f'GPO_getL1FeeUpperBound({size})_wei']=H(call(GPO,sel('getL1FeeUpperBound(uint256)')+hex(size)[2:].rjust(64,'0')))
    except Exception as e: res[f'GPO_getL1FeeUpperBound_err']=str(e)[:120]
for g in [100000,200000,300000]:
    try: res[f'GPO_getOperatorFee({g})_wei']=H(call(GPO,sel('getOperatorFee(uint256)')+hex(g)[2:].rjust(64,'0')))
    except Exception as e: res['GPO_getOperatorFee_err']=str(e)[:120]
L1B='0x4200000000000000000000000000000000000015'
for fn in ['number()','timestamp()','basefee()','blobBaseFee()','sequenceNumber()','operatorFeeScalar()','operatorFeeConstant()','baseFeeScalar()','blobBaseFeeScalar()','daFootprintGasScalar()']:
    try: res['L1Block_'+fn]=H(call(L1B,sel(fn)))
    except Exception as e: res['L1Block_'+fn+'_err']=str(e)[:120]
# code checks
addrs={
 'v4_PoolManager':'0x1f98400000000000000000000000000000000004',
 'v4_PositionManager':'0x4529a01c7a0410167c5740c487a8de60232617bf',
 'v4_StateView':'0x86e8631a016f9068c3f085faf484ee3f5fdee8f2',
 'v4_Quoter':'0x333e3c607b141b18ff6de9f258db6e77fe7491e0',
 'v4_PositionDescriptor':'0x9fb28449a191cd8c03a1b7abfb0f5996ecf7f722',
 'UniversalRouter':'0xef740bf23acae26f6492b10de645d6b98dc8eaf3',
 'Permit2':'0x000000000022D473030F116dDEE9F6B43aC78BA3',
 'v3_Factory':'0x1f98400000000000000000000000000000000003',
 'v3_NFPM':'0x943e6e07a7e8e791dafc44083e54041d743c46e9',
 'v3_SwapRouter02':'0x73855d06de49d0fe4a9c42636ba96c62da12ff9c',
 'v3_QuoterV2':'0x385a5cf5f83e99f7bb2852b6a19c3538b9fa7658',
 'v2_Factory':'0x1f98400000000000000000000000000000000002',
 'pyth_cand_2880':'0x2880aB155794e7179c9eE2e38200202908C17B43',
 'pyth_cand_4305':'0x4305FB66699C3B2702D4d05CF36551390A4c69C6',
 'pyth_cand_ff1a':'0xff1a0f4744e8582DF1aE09D5611b887B6a12925C',
 'pyth_cand_8250':'0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a',
 'pyth_cand_A2aa':'0xA2aa501b19aff244D90cc15a4Cf739D2725B5729',
 'USDC_native':'0x078D782b760474a361dDA0AF3839290b0EF57AD6',
 'USDT0':'0x9151434b16b9763660705744891fA906F660EcC5',
 'WETH':'0x4200000000000000000000000000000000000006',
}
res['code']={}
for k,a in addrs.items():
    try: c=rpc('eth_getCode',[a,'latest']); res['code'][k]=(a,(len(c)-2)//2)
    except Exception as e: res['code'][k]=(a,'err '+str(e)[:80])
# token symbols
for k in ['USDC_native','USDT0']:
    try:
        r=call(addrs[k],sel('symbol()')); n=H(r[2+64:2+128]); res[k+'_symbol']=bytes.fromhex(r[2+128:2+128+2*n]).decode()
        res[k+'_totalSupply_raw']=H(call(addrs[k],sel('totalSupply()')))
    except Exception as e: res[k+'_symbol_err']=str(e)[:100]
# pyth fees
for k in ['pyth_cand_2880','pyth_cand_4305','pyth_cand_ff1a','pyth_cand_8250','pyth_cand_A2aa']:
    if isinstance(res['code'][k][1],int) and res['code'][k][1]>0:
        for fn in ['singleUpdateFeeInWei()','version()','validTimePeriodSeconds()']:
            try:
                r=call(addrs[k],sel(fn))
                res[k+'_'+fn]= H(r) if fn!='version()' else bytes.fromhex(r[2+128:]).rstrip(b'\0').decode(errors='ignore')
            except Exception as e: res[k+'_'+fn+'_err']=str(e)[:100]
json.dump(res,open(OUT,'w'),indent=1,default=str)
print(json.dumps(res,indent=1,default=str))
