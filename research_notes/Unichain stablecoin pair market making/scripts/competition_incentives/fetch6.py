import sys, urllib.request, os
OUT=sys.argv[1]
for n,u in {"llama_fees_v3.json":"https://api.llama.fi/summary/fees/uniswap-v3?dataType=dailyFees"}.items():
    d=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=120).read()
    open(os.path.join(OUT,n),"wb").write(d); print("OK",n,len(d))
