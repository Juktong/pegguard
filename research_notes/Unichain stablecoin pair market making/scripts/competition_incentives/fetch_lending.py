import sys, urllib.request, os, json
OUT=sys.argv[1]
def post(url, body):
    req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={"Content-Type":"application/json","User-Agent":"Mozilla/5.0"})
    return urllib.request.urlopen(req,timeout=60).read()
# Morpho vaults on Unichain
q={"query":"""{ vaults(first: 50, where: {chainId_in: [130]}, orderBy: TotalAssetsUsd, orderDirection: Desc) { items { address name symbol asset { symbol } state { totalAssetsUsd apy netApy fee } } } }"""}
try:
    d=post("https://api.morpho.org/graphql",q); open(os.path.join(OUT,"morpho_vaults_130.json"),"wb").write(d); print("OK morpho vaults",len(d))
except Exception as e: print("ERR morpho vaults",e)
q2={"query":"""{ markets(first: 50, where: {chainId_in: [130]}, orderBy: SupplyAssetsUsd, orderDirection: Desc) { items { uniqueKey loanAsset { symbol } collateralAsset { symbol } lltv state { supplyAssetsUsd borrowAssetsUsd supplyApy borrowApy utilization } } } }"""}
try:
    d=post("https://api.morpho.org/graphql",q2); open(os.path.join(OUT,"morpho_markets_130.json"),"wb").write(d); print("OK morpho markets",len(d))
except Exception as e: print("ERR morpho markets",e)
# Morpho top USDC vaults on Ethereum & Base for comparison
q3={"query":"""{ vaults(first: 15, where: {chainId_in: [1, 8453], assetSymbol_in: ["USDC","USDT"]}, orderBy: TotalAssetsUsd, orderDirection: Desc) { items { name chain { id } asset { symbol } state { totalAssetsUsd apy netApy } } } }"""}
try:
    d=post("https://api.morpho.org/graphql",q3); open(os.path.join(OUT,"morpho_vaults_eth_base.json"),"wb").write(d); print("OK morpho eth/base",len(d))
except Exception as e: print("ERR morpho eth/base",e)
