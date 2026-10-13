import math
# Milionis-Moallemi-Roughgarden (2023/2025) fast-block results; sigma in bp/day
def ptrade(sig_bp_day, dt_s, fee_bp):
    sig_s = sig_bp_day/math.sqrt(86400)        # bp per sqrt(s)
    eta = fee_bp/(sig_s*math.sqrt(dt_s/2))
    return 1/(1+eta)
def lvr_frac_per_day(sig_bp_day, half_width_bp=None):
    s2=(sig_bp_day*1e-4)**2
    if half_width_bp is None: return s2/8
    return s2/(4*half_width_bp*1e-4)          # CL approx, delta small, in-range
print("P_trade (% of blocks with arb) ; sigma bp/day x block time x fee")
for sig in (2.15,3.0,4.45):
    for dt,lab in ((12,'ETH 12s'),(2,'Base/OP 2s'),(1,'Unichain 1s'),(0.25,'Arb 0.25s'),(0.2,'Uni flashblock 0.2s')):
        row=[f"{100*ptrade(sig,dt,f):6.2f}%" for f in (0.05,0.1,0.5,1,5)]
        print(f"sig={sig:4.2f} {lab:20}", ' '.join(row), "  (fees 0.05/0.1/0.5/1/5 bp)")
print()
print("LVR (fee-free) as bp of in-range position value per day / per year")
for sig in (2.15,3.0,4.45):
    out=[f"full {lvr_frac_per_day(sig)*1e4*365:.5f}bp/yr"]
    for hw in (1,2,5,10,50):
        v=lvr_frac_per_day(sig,hw)*1e4
        out.append(f"±{hw}bp {v:.3f}bp/d={v*365/100:.2f}%/yr")
    print(f"sig={sig}: "+' | '.join(out))
print()
print("ARB = LVR*P_trade (LP net loss to arbs), ±1bp and ±5bp ranges, % per year in range")
for sig in (2.15,4.45):
  for dt,lab in ((12,'ETH'),(1,'Unichain'),(0.2,'flashblk')):
    for f in (0.1,0.5,1):
        a1=lvr_frac_per_day(sig,1)*ptrade(sig,dt,f)*365*100; a5=lvr_frac_per_day(sig,5)*ptrade(sig,dt,f)*365*100
        print(f"sig={sig} {lab:9} fee={f}bp: ARB ±1bp {a1:.3f}%/yr  ±5bp {a5:.3f}%/yr; FEE-from-arb ≈ LVR(1-P) ±1bp {lvr_frac_per_day(sig,1)*(1-ptrade(sig,dt,f))*365*100:.2f}%/yr")
print()
# Fee APR needed vs opportunity cost: fee APR (on in-range capital) = turnover/day * fee * 365 / share
for fee in (0.05,0.1,0.5,1):
    for turn in (0.5,2,10,20):
        print(f"fee {fee}bp turnover {turn}x/day (pool-level) -> pool fee APR {turn*fee*1e-4*365*100:.2f}%")
