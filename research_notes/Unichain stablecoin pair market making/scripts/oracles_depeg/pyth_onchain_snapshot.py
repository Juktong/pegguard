import sys, json, time
sys.path.insert(0, sys.argv[1])
from rpc import call, ethcall
url=sys.argv[2]; pyth=sys.argv[3]
FEEDS={"USDC/USD":"eaa020c61cc479712813461ce153894a96a6c00b21ed0cfc2798d1f9a9e9c94a","USDT/USD":"2b89b9dc8fdf9f34709a5b106b472f0f39bb6ca9ce04b0fd7f2e971688e2e53b","USDT0/USD":"cfc1303ea9f083b1b4f99e1369fb9d2611f3230d5ea33a6abf2f86071c089fdc","DAI/USD":"b0948a5e5313200c632b51bb5ca32f6de0d36e9950a942d19751e833f70dabfd","USDS/USD":"77f0971af11cc8bac224917275c1bf55f2319ed5c654a1ca955c82fa2d297ea1","USDE/USD":"6ec879b1e9963de5ee97e9c8710b742d6228252a5e2ca12d4ae81d7fe5ee8c5d","ETH/USD":"ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace","FDUSD/USD":"ccdc1a08923e2e4f4b1e6ea89de6acbc5fe1948e9706f5604b8cb50bc1ed3979","PYUSD/USD":"c1da1b73d7f01e7ddd54b3766cf7fcd644395ad14f70aa706ec5384c59e76692"}
blk=call(url,'eth_getBlockByNumber',['latest',False]); now=int(blk['timestamp'],16)
print("block",int(blk['number'],16),"ts",now,time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(now)))
code=call(url,'eth_getCode',[pyth,'latest']); print('code bytes',len(code)//2-1)
for sel,name in [("0x48b6404d","singleUpdateFeeInWei"),("0xe18910a3","getValidTimePeriod")]:
    try: print(name,int(ethcall(url,pyth,sel),16))
    except Exception as e: print(name,'ERR',e)
def s64(h): v=int(h,16); return v-(1<<256) if v>=1<<255 else v
for k,fid in FEEDS.items():
    try:
        r=ethcall(url,pyth,"0x96834ad3"+fid)[2:]
        w=[r[i:i+64] for i in range(0,len(r),64)]
        price=s64(w[0]); conf=int(w[1],16); expo=s64(w[2]); pt=int(w[3],16)
        p=price*10**expo
        print(f"{k:10s} price={p:.8f} conf={conf*10**expo:.8f} ({conf/price*1e4:.2f} bps) expo={expo} publishTime={pt} age_s={now-pt} ({(now-pt)/86400:.2f} d)")
    except Exception as e:
        print(k,'ERR',str(e)[:120])
