import sys, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpcutil import *
POSM='0x4529a01c7a0410167c5740c487a8de60232617bf'
SV='0x86e8631a016f9068c3f085faf484ee3f5fdee8f2'
TOK={'0x078d782b760474a361dda0af3839290b0ef57ad6':'USDC','0x9151434b16b9763660705744891fa906f660ecc5':'USDT0','0x588ce4f028d8e7b53b687865d6a67b3a54c75518':'USDT(bridged)'}
v4ids=sys.argv[1].split(',')
v3=sys.argv[2].split(',')
out={'v4':{},'v3':{}}
for pid in v4ids:
    pk=call('eth_call',[{'to':POSM,'data':'0x86b6be7d'+pid[2:52]+'0'*14},'latest'])
    w=words(pk)
    c0='0x'+w[0][24:]; c1='0x'+w[1][24:]; fee=int(w[2],16); ts=s256(w[3]); hooks='0x'+w[4][24:]
    s0=words(call('eth_call',[{'to':SV,'data':'0xc815641c'+pid[2:]},'latest']))
    sqrtp=int(s0[0],16); tick=s256(s0[1]); proto=int(s0[2],16); lpfee=int(s0[3],16)
    L=int(call('eth_call',[{'to':SV,'data':'0xfa6793d5'+pid[2:]},'latest']),16)
    price=(sqrtp/2**96)**2 if sqrtp else None
    out['v4'][pid]=dict(c0=c0,c1=c1,sym0=TOK.get(c0,c0),sym1=TOK.get(c1,c1),fee=fee,tickSpacing=ts,hooks=hooks,sqrtP=sqrtp,tick=tick,protocolFee=proto,lpFee=lpfee,liquidity=L,price=price)
    print(pid[:12], TOK.get(c0,c0[:10]), TOK.get(c1,c1[:10]), 'fee',fee,'ts',ts,'hooks',hooks,'tick',tick,'proto',proto,'lpfee',lpfee,'L',L,'px',price)
for a in v3:
    def ec(sel): return call('eth_call',[{'to':a,'data':sel},'latest'])
    t0='0x'+words(ec('0x0dfe1681'))[0][24:]; t1='0x'+words(ec('0xd21220a7'))[0][24:]
    fee=int(ec('0xddca3f43'),16); fac='0x'+words(ec('0xc45a0155'))[0][24:]
    try: ts=s256(words(ec('0xd0c93a7c'))[0])
    except Exception as e: ts=None
    L=int(ec('0x1a686502'),16)
    s0=words(ec('0x3850c7bd')); sqrtp=int(s0[0],16); tick=s256(s0[1]); fp=int(s0[5],16) if len(s0)>5 else None
    out['v3'][a]=dict(t0=t0,t1=t1,sym0=TOK.get(t0,t0),sym1=TOK.get(t1,t1),fee=fee,factory=fac,tickSpacing=ts,liquidity=L,sqrtP=sqrtp,tick=tick,feeProtocol=fp,price=(sqrtp/2**96)**2)
    print(a[:12], TOK.get(t0,t0[:10]), TOK.get(t1,t1[:10]), 'fee',fee,'factory',fac,'ts',ts,'tick',tick,'L',L,'feeProtocol',fp,'px',(sqrtp/2**96)**2)
json.dump(out, open(sys.argv[3],'w'), indent=1)
