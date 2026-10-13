import base64, struct, json, urllib.request, time
ACCTS={"USDC/USD":"Dpw1EAVrSB1ibxiDQyTAW6Zip3J4Btk2x4SgApQCeFbX","USDT/USD":"HT2PLQBcG5EiCcNSaMHAjSgd9F98ecpATbk4Sk5oYuM"}
def decode(b64):
    d=base64.b64decode(b64)
    off=8+32
    vl=d[off]
    if vl==0: off+=2   # Partial{num_signatures}
    else: off+=1       # Full
    fid=d[off:off+32].hex(); off+=32
    price,conf,expo,pt,ppt,ema,emac=struct.unpack_from('<qQiqqqQ',d,off); off+=struct.calcsize('<qQiqqqQ')
    slot,=struct.unpack_from('<Q',d,off)
    return dict(feed_id=fid,verif=vl,price=price,conf=conf,expo=expo,publish_time=pt,prev_publish_time=ppt,ema_price=ema,ema_conf=emac,posted_slot=slot)
def fetch(url="https://api.mainnet-beta.solana.com"):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"getMultipleAccounts","params":[list(ACCTS.values()),{"encoding":"base64","commitment":"confirmed"}]}).encode()
    req=urllib.request.Request(url,data=body,headers={"content-type":"application/json"})
    with urllib.request.urlopen(req,timeout=20) as r: j=json.loads(r.read())
    res=j['result']; out={"slot":res['context']['slot'],"t_local":time.time()}
    for (k,_),v in zip(ACCTS.items(),res['value']): out[k]=decode(v['data'][0])
    return out
if __name__=='__main__':
    print(json.dumps(fetch(),indent=1))
