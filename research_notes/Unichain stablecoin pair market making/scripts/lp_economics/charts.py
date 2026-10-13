import json, glob, statistics as st, datetime
names={'52d6a1b3':'ETH fluid USDC-USDT','e737d721':'ETH univ3 USDC-USDT 1bp','fcf0e09f':'ETH univ4 USDC-USDT hook','396690fe':'ETH univ4 USDC-USDT 0.1bp(a)','811eb3de':'ETH univ4 USDC-USDT 0.1bp(b)','600291d6':'ARB fluid USDC-USDT0','ba557f7e':'BASE aero CL1 USDC-USDT','8a922da8':'ETH pcs-v3 USDC-USDT 1bp','ba3fb5f5':'ARB univ3 USDC-USDT 1bp','d6a444b3':'ETH univ4 USDe-USDC'}
end=datetime.datetime(2026,10,13,tzinfo=datetime.UTC)
for f in sorted(glob.glob('data/chart_*.json')):
    k=f.split('_')[1][:8]; d=json.load(open(f)).get('data',[])
    if not d: print(k,'empty'); continue
    rows=[(datetime.datetime.fromisoformat(x['timestamp'].replace('Z','+00:00')), x.get('tvlUsd') or 0, x.get('apyBase') or 0, x.get('apyReward') or 0) for x in d]
    first=rows[0][0].date()
    out=[]
    for days in (30,90,365):
        w=[r for r in rows if (end-r[0]).days<=days]
        if not w: out.append('n/a'); continue
        out.append(f"{days}d: TVL ${st.mean(r[1] for r in w)/1e6:.1f}M apyBase mean {st.mean(r[2] for r in w):.2f}% med {st.median(r[2] for r in w):.2f}% rew {st.mean(r[3] for r in w):.2f}%")
    print(f"{names.get(k,k):28} since {first} | " + ' | '.join(out))
