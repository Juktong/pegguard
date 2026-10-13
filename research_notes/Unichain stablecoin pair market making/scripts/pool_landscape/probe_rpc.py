import rpc,time,sys
T0="0xdd466e674ea557f56295e2d0218a125ea4b4f0f6f3307b95f85e6110838d6438"
PM="0x1f98400000000000000000000000000000000004"
for url in sys.argv[1:]:
    for rng in [5000,10000,100000,1000000]:
        t=time.time()
        try:
            L=rpc.rpc("eth_getLogs",[{"fromBlock":hex(20_000_000),"toBlock":hex(20_000_000+rng-1),"address":PM,"topics":[T0]}],url=url,retries=1)
            print(url,rng,'ok',len(L),round(time.time()-t,1),flush=True)
        except Exception as e:
            print(url,rng,'ERR',str(e)[:150],round(time.time()-t,1),flush=True); break
