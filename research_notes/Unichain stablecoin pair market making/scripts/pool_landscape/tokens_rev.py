import rpc,json,sys,os
D=sys.argv[1]
v4=[json.loads(l) for l in open(D+'/v4_initialize.jsonl')]
v3=[json.loads(l) for l in open(D+'/v3_poolcreated.jsonl')]
toks=set()
for e in v4: toks.add(rpc.addr(e['topics'][2])); toks.add(rpc.addr(e['topics'][3]))
for e in v3: toks.add(rpc.addr(e['topics'][1])); toks.add(rpc.addr(e['topics'][2]))
toks.discard('0x0000000000000000000000000000000000000000')
cache=D+'/token_meta_rev.json'
meta=json.load(open(cache)) if os.path.exists(cache) else {}
todo=[t for t in sorted(toks,reverse=True) if t not in meta]
print('tokens',len(toks),'todo',len(todo),flush=True)
SYM=rpc.sel('symbol()'); DEC=rpc.sel('decimals()'); NAME=rpc.sel('name()')
for i in range(0,len(todo),3):
    part=todo[i:i+3]
    reqs=[]
    for t in part: reqs+= [("eth_call",[{"to":t,"data":SYM},"latest"]),("eth_call",[{"to":t,"data":DEC},"latest"]),("eth_call",[{"to":t,"data":NAME},"latest"])]
    try: res=rpc.batch(reqs)
    except Exception as e: print('err',e); continue
    for k,t in enumerate(part):
        s,d,n=res[3*k:3*k+3]
        meta[t]={"symbol":None if isinstance(s,Exception) else rpc.dec_string(s),"decimals":None if isinstance(d,Exception) or d in (None,'0x') else int(d,16),"name":None if isinstance(n,Exception) else rpc.dec_string(n)}
    if i%300==0:
        json.dump(meta,open(cache,'w')); print(i,flush=True)
json.dump(meta,open(cache,'w'))
print('done',len(meta))
