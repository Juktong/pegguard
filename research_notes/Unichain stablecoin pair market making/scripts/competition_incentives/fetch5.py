import sys, urllib.request, os
OUT=sys.argv[1]
U={"llama_fees_unichain_chainfees.json":"https://api.llama.fi/summary/fees/unichain?dataType=dailyFees",
   "llama_dexs_v4.json":"https://api.llama.fi/summary/dexs/uniswap-v4",
   "llama_fees_v4.json":"https://api.llama.fi/summary/fees/uniswap-v4?dataType=dailyFees",
   "llama_rev_v3.json":"https://api.llama.fi/summary/fees/uniswap-v3?dataType=dailyRevenue",
   "llama_rev_v4.json":"https://api.llama.fi/summary/fees/uniswap-v4?dataType=dailyRevenue",
}
for n,u in U.items():
    try:
        d=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=120).read()
        open(os.path.join(OUT,n),"wb").write(d); print("OK",n,len(d))
    except Exception as e: print("ERR",n,e)
