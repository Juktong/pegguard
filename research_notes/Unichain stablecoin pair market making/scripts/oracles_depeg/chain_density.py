import sys, json, concurrent.futures as cf
sys.path.insert(0, sys.argv[1])
from rpc import call
T='0xd06a6b7f4918494b3719217d1802786c1f5112a6c1d88fe2cfec00b4584f6aec'
USDC='0xeaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a'; USDT='0x2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b'
CH=[("ethereum","https://ethereum-rpc.publicnode.com","0x4305FB66699C3B2702D4d05CF36551390A4c69C6",5000),
("arbitrum","https://arb1.arbitrum.io/rpc","0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",10000),
("optimism","https://mainnet.optimism.io","0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",10000),
("base","https://mainnet.base.org","0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a",10000),
("polygon","https://polygon-rpc.com","0xff1a0f4744e8582DF1aE09D5611b887B6a12925C",10000),
("avalanche","https://api.avax.network/ext/bc/C/rpc","0x4305FB66699C3B2702D4d05CF36551390A4c69C6",2000),
("bnb","https://bsc-dataseed.bnbchain.org","0x4D7E825f80bDf85e913E0DD2A2D54927e9dE1594",5000),
("blast","https://rpc.blast.io","0x2880aB155794e7179c9eE2e38200202908C17B43",10000),
("sonic","https://rpc.soniclabs.com","0x2880aB155794e7179c9eE2e38200202908C17B43",10000),
("berachain","https://rpc.berachain.com","0x2880aB155794e7179c9eE2e38200202908C17B43",10000),
("hyperevm","https://rpc.hyperliquid.xyz/evm","0xe9d69CdD6Fe41e7B621B4A688C5D1a68cB5c8ADc",1000),
("linea","https://rpc.linea.build","0xA2aa501b19aff244D90cc15a4Cf739D2725B5729",10000),
("mantle","https://rpc.mantle.xyz","0xA2aa501b19aff244D90cc15a4Cf739D2725B5729",10000),
("sei","https://evm-rpc.sei-apis.com","0x2880aB155794e7179c9eE2e38200202908C17B43",2000),
("unichain","https://mainnet.unichain.org","0x2880aB155794e7179c9eE2e38200202908C17B43",10000)]
def run(c):
    name,url,addr,rng=c
    try:
        h=int(call(url,'eth_blockNumber',[],retries=2),16)
        b0=call(url,'eth_getBlockByNumber',[hex(h-rng),False],retries=2); b1=call(url,'eth_getBlockByNumber',[hex(h),False],retries=2)
        span=int(b1['timestamp'],16)-int(b0['timestamp'],16)
        res={}
        for k,t in [("USDC",USDC),("USDT",USDT)]:
            logs=call(url,'eth_getLogs',[{"address":addr,"topics":[T,t],"fromBlock":hex(h-rng),"toBlock":hex(h)}],retries=2)
            res[k]=len(logs)
        return f"{name:10s} span={span}s USDC={res['USDC']} USDT={res['USDT']} per_hour_USDC={res['USDC']*3600/max(span,1):.1f} per_hour_USDT={res['USDT']*3600/max(span,1):.1f}"
    except Exception as e:
        return f"{name:10s} ERR {str(e)[:120]}"
with cf.ThreadPoolExecutor(8) as ex:
    for r in ex.map(run,CH): print(r)
