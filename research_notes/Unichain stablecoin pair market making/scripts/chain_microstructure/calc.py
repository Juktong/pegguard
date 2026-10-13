import math
# MMR (arXiv 2305.14604) Theorem 1: P_trade = 1/(1 + sqrt(2*lam)*gamma/sigma), sigma per sqrt(second), lam = 1/dt
def ptrade(sig_daily, gamma, dt):
    s=sig_daily/math.sqrt(86400); return 1/(1+math.sqrt(2/dt)*gamma/s)
print('sanity: paper sigma=5%/day, 12s, 5bp ->', round(100*ptrade(0.05,5e-4,12),1),'% (paper Table 1: 45.6%)')
print('sanity: 2s 5bp ->', round(100*ptrade(0.05,5e-4,2),1),'% (paper 25.4%); 12s 30bp', round(100*ptrade(0.05,30e-4,12),1),'(paper 12.3)')
dts=[('Ethereum 12s',12),('Base/OP 2s',2),('Unichain block 1s',1),('Arbitrum 0.25s',0.25),('Unichain flashblock 0.2s',0.2)]
for sig in [1e-4,3e-4,10e-4,50e-4]:
    for g in [0.5e-4,1e-4,5e-4]:
        row=[f'{100*ptrade(sig,g,dt):.2f}%' for _,dt in dts]
        print(f'sigma={sig*1e4:.0f}bp/day fee={g*1e4:.1f}bp :', dict(zip([n for n,_ in dts],row)))
# ratio ARB(dt)/ARB(12s) ~ P_trade ratio (LVR same)
print('ratio Unichain1s/Base2s at sigma 3bp fee 1bp:', ptrade(3e-4,1e-4,1)/ptrade(3e-4,1e-4,2), ' flash0.2/1s:', ptrade(3e-4,1e-4,0.2)/ptrade(3e-4,1e-4,1))
# cost table
ETH=2499.375
ops={'v4 swap, no hook (UR, observed median)':150610,'v4 swap + PegGuard hook (150.6k + repo-measured 137.6k)':150610+52699+84925,
     'v4 swap + hook + in-hook Pyth 1-feed update (~+174k)':150610+52699+84925+174000,'standalone Pyth updatePriceFeeds, 1 feed (estimateGas)':195193,
     'v4 LP mint (PositionManager, observed median)':243259,'v4 increaseLiquidity (median)':179472,'v4 decreaseLiquidity (median)':138330,'v4 collect (delta=0, median)':125490,'v4 burn (median)':107729,
     'multi-position rebalance (~45 ModifyLiquidity, observed)':3900000}
gps=[('floor 0.0005',0.0005),('typical UR eff 0.00195',0.00195),('repo low 0.005',0.005),('repo stressed 0.05',0.05)]
print('\nUSD per op at ETH $%.0f (L2 execution only; add ~$0.000003-0.00009 L1 data fee)'%ETH)
for k,g in ops.items():
    print(f'{k:62s} gas={g:>8,}  '+'  '.join(f'{n}: ${g*gp*1e-9*ETH:.5f}' for n,gp in gps))
# repo per-swap cost assumption vs corrected
repo=(52699+84925+90000); corr=(52699+84925+174000)
for n,gp in gps:
    print(n,'repo per-swap hook+pyth gas',repo,'$%.5f'%(repo*gp*1e-9*3500),'(@$3500)  corrected',corr,'$%.5f'%(corr*gp*1e-9*ETH),'(@$%.0f)'%ETH)
# bps for swap sizes
for size in [100,1000,10000]:
    g=150610+52699+84925+174000
    print('swap size $',size,'all-in gas bps @0.00195 gwei:', round(g*0.00195e-9*ETH/size*1e4,4),' @0.05 gwei:', round(g*0.05e-9*ETH/size*1e4,4))
# L1 fee formula check (Fjord): l1 = max(100e6, -42585600 + 836500*fastlz)*(16*2000*l1Base + 900000*blobBase)/1e12
l1b=130256447; bb=8072671
for fz in [200,300,1000,1500]:
    est=max(100e6,-42585600+836500*fz); print('fastlz',fz,'l1Fee wei',est*(16*2000*l1b+900000*bb)/1e12/1e6*1e6/1e6, 'ETH', est*(16*2000*l1b+900000*bb)/1e12/1e18)
