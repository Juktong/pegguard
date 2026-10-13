import json, os, sys, urllib.request
OUT=sys.argv[1]
ua={"User-Agent":"Mozilla/5.0 research-script"}
def get(url):
    req=urllib.request.Request(url,headers=ua)
    with urllib.request.urlopen(req,timeout=90) as r: return r.read()
for kind in ["opportunities","campaigns"]:
    allitems=[]
    for page in range(0,40):
        if kind=="opportunities":
            url=f"https://api.merkl.xyz/v4/opportunities?chainId=130&items=100&page={page}"
        else:
            url=f"https://api.merkl.xyz/v4/campaigns?chainId=130&items=100&page={page}"
        try:
            d=json.loads(get(url))
        except Exception as e:
            print("ERR",kind,page,e); break
        if not d: break
        allitems+=d
        print(kind,page,len(d))
        if len(d)<100: break
    json.dump(allitems,open(os.path.join(OUT,f"merkl_all_{kind}_130.json"),"w"))
    print(kind,"total",len(allitems))
