import sys, urllib.request, os
OUT=sys.argv[1]
U={"llama_stables_unichain_usdt.json":"https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=1",
   "llama_stables_unichain_usdc.json":"https://stablecoins.llama.fi/stablecoincharts/Unichain?stablecoin=2",
   "llama_proto_uniswapv4.json":"https://api.llama.fi/protocol/uniswap-v4",
   "llama_proto_euler.json":"https://api.llama.fi/protocol/euler-v2",
   "llama_proto_morpho.json":"https://api.llama.fi/protocol/morpho-blue",
}
for n,u in U.items():
    try:
        d=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=120).read()
        open(os.path.join(OUT,n),"wb").write(d); print("OK",n,len(d))
    except Exception as e: print("ERR",n,e)
