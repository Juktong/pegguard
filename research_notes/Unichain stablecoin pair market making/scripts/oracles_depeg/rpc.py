import json, urllib.request, time
def call(url, method, params, retries=4):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode()
    for i in range(retries):
        try:
            req=urllib.request.Request(url,data=body,headers={"content-type":"application/json","user-agent":"research-script/1.0"})
            with urllib.request.urlopen(req,timeout=60) as r:
                d=json.loads(r.read())
            if 'error' in d: raise RuntimeError(d['error'])
            return d['result']
        except Exception as e:
            if i==retries-1: raise
            time.sleep(1.5*(i+1))
def ethcall(url,to,data,block='latest'):
    return call(url,'eth_call',[{"to":to,"data":data},block])
