import sys, urllib.request, os
OUT=sys.argv[1]
U={"llama_stablecoins_all.json":"https://stablecoins.llama.fi/stablecoins?includePrices=true",
   "llama_dexs_unichain_2.json":"https://api.llama.fi/overview/dexs/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=false",
   "llama_fees_uniswap.json":"https://api.llama.fi/summary/fees/uniswap?dataType=dailyFees",
   "llama_rev_uniswap.json":"https://api.llama.fi/summary/fees/uniswap?dataType=dailyRevenue",
   "llama_fees_unichain_chain.json":"https://api.llama.fi/summary/fees/unichain?dataType=dailyRevenue",
   "llama_aggs_unichain.json":"https://api.llama.fi/overview/aggregators/Unichain?excludeTotalDataChart=true&excludeTotalDataChartBreakdown=true",
   "llama_tbill.json":"https://yields.llama.fi/chart/aa70268e-4b52-42bf-a116-608b370f9501",
}
for n,u in U.items():
    try:
        d=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=120).read()
        open(os.path.join(OUT,n),"wb").write(d); print("OK",n,len(d))
    except Exception as e: print("ERR",n,e)
