import json,glob,datetime
D='/tmp/claude-0/-home-user-pegguard/75eb22d9-d5d6-5979-97ed-b3b406371418/scratchpad/pool_landscape/data'
rows=json.load(open(D+'/bench_pools_onchain.json'))
ohl={}
for f in glob.glob(D+'/gt/gt_*.json'):
    j=json.load(open(f)); p=j.get('_path','')
    if '/ohlcv/' not in p or 'data' not in j: continue
    net=p.split('/')[1]; addr=p.split('/')[3]
    L=sorted(j['data']['attributes']['ohlcv_list'],key=lambda x:x[0])
    ohl[(net,addr.lower())]=(L,j['_fetched_at'])
for r in sorted(rows,key=lambda r:(r['net'],-r['v24'])):
    k=(r['net'],r['addr'].lower()); L=ohl.get(k,([],0))[0]
    v7=sum(x[5] for x in L[-7:]) if L else None; v30=sum(x[5] for x in L[-30:]) if L else None
    fee=r.get('lpFee'); 
    feepct=(f"{fee/1e4:.4f}%" if fee is not None else '?')
    hooks=r.get('hooks') or ''
    t=r.get('tick')
    apr=None
    if fee is not None and v30 and r['tvl']>0: apr=v30*fee/1e6/r['tvl']*365/30*100
    print(f"{r['net']:9} {r['name'][:22]:22} {r['dex'][:24]:24} {r['addr'][:12]} fee {feepct:>9} dyn={r.get('feeKey')==8388608} hooks={hooks[:8]+'..'+hooks[-4:] if hooks and hooks!='0x'+'0'*40 else 'none'} tick {t} TVL {r['tvl']:>12,.0f} v24 {r['v24']:>12,.0f} v7 {('-' if v7 is None else f'{v7:,.0f}'):>13} v30 {('-' if v30 is None else f'{v30:,.0f}'):>14} turn30 {v30/r['tvl'] if v30 and r['tvl'] else 0:7.1f} feeAPR {('-' if apr is None else f'{apr:.1f}%')} days {len(L)}")
