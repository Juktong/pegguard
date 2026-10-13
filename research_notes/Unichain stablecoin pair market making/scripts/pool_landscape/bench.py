import json,urllib.request,time,rpc,sys
D='/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/pool_landscape/data'
rows=json.load(open(D+'/gt_bench_stable_rows.json'))
CH={'eth':dict(rpc='https://ethereum-rpc.publicnode.com',bs='https://eth.blockscout.com/api',pm='0x000000000004444c5dc75cb358380d2e3de08a90',sv='0x7ffe42c4a5deea5b0fec41c94c136cf115597227'),
    'base':dict(rpc='https://mainnet.base.org',bs='https://base.blockscout.com/api',pm='0x498581ff718922c3f8e6a244956af099b2652b2b',sv='0xa3c0c9b65bad0b08107aa264b0f3db444b867a71'),
    'arbitrum':dict(rpc='https://arb1.arbitrum.io/rpc',bs='https://arbitrum.blockscout.com/api',pm='0x360e68faccca8ca495c1b759fd9eee466db9fb32',sv='0x76fd297e2d437cd7f76d50f01afe6160f86e9990'),
    'optimism':dict(rpc='https://mainnet.optimism.io',bs='https://optimism.blockscout.com/api',pm='0x9a13f98cb987694c9f086b1f5eb990eea8264ec3',sv='0xc18a3169788f4f75a170290584eca6395c75ecdb')}
INIT='0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438'
out=[]
for net,c in CH.items():
    R=sorted([r for r in rows if r['net']==net],key=lambda r:-r['v24'])[:8]
    R+= [r for r in sorted([r for r in rows if r['net']==net],key=lambda r:-r['tvl'])[:3] if r not in R]
    blk=rpc.block_number(url=c['rpc'])
    for r in R:
        r=dict(r); r['block']=blk
        try:
            if 'v4' in r['dex'] and len(r['addr'])==66:
                q=f"{c['bs']}?module=logs&action=getLogs&fromBlock=0&toBlock=latest&address={c['pm']}&topic0={INIT}&topic1={r['addr']}&topic0_1_opr=and"
                j=json.loads(urllib.request.urlopen(urllib.request.Request(q,headers={'user-agent':'research/1.0'}),timeout=60).read())
                if j.get('result'):
                    e=j['result'][0]; w=rpc.words(e['data'])
                    r.update(c0=rpc.addr(e['topics'][2]),c1=rpc.addr(e['topics'][3]),feeKey=rpc.u(w[0]),ts=rpc.s(w[1]),hooks=rpc.addr(w[2]))
                s0=rpc.words(rpc.eth_call(c['sv'],rpc.sel('getSlot0(bytes32)')+r['addr'][2:],url=c['rpc']))
                r.update(tick=rpc.s(s0[1]),lpFee=rpc.u(s0[3]),sqrtP=rpc.u(s0[0]))
                r['L']=rpc.u(rpc.eth_call(c['sv'],rpc.sel('getLiquidity(bytes32)')+r['addr'][2:],url=c['rpc']))
                time.sleep(1)
            elif any(k in r['dex'] for k in ['uniswap_v3','uniswap-v3','pancakeswap-v3','slipstream','sushiswap-v3']):
                s0=rpc.words(rpc.eth_call(r['addr'],rpc.sel('slot0()'),url=c['rpc']))
                r.update(tick=rpc.s(s0[1]),sqrtP=rpc.u(s0[0]))
                r['lpFee']=rpc.u(rpc.eth_call(r['addr'],rpc.sel('fee()'),url=c['rpc']))
                r['t0']=rpc.addr(rpc.eth_call(r['addr'],rpc.sel('token0()'),url=c['rpc'])); r['t1']=rpc.addr(rpc.eth_call(r['addr'],rpc.sel('token1()'),url=c['rpc']))
        except Exception as ex:
            r['err']=str(ex)[:120]
        out.append(r)
        print(net, r['name'][:24], r['dex'][:24], r['addr'][:14], 'tvl',round(r['tvl']), 'v24',round(r['v24']), 'tick',r.get('tick'),'lpFee',r.get('lpFee'),'feeKey',r.get('feeKey'),'ts',r.get('ts'),'hooks',r.get('hooks'),'tokens',r.get('c0') or r.get('t0'),r.get('c1') or r.get('t1'), r.get('err',''),flush=True)
json.dump(out,open(D+'/bench_pools_onchain.json','w'))
