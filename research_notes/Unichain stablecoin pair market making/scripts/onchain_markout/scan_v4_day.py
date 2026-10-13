"""Scan ALL v4 PoolManager Swap logs for one day; rank pool ids by count; resolve keys of top ids; flag stable/stable."""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpcutil import *
PM='0x1f98400000000000000000000000000000000004'; SW='0x40e9cecb9f5f1f1c5b9c97dec2917b7ee92e57ba5563708daca94dd84ad7112f'
POSM='0x4529a01c7a0410167c5740c487a8de60232617bf'
a, b, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
cnt = collections.Counter(); usd = collections.Counter(); n = 0
f = open(out, 'w')
for s in range(a, b, 1000):
    r = call('eth_getLogs', [{'address': PM, 'fromBlock': hex(s), 'toBlock': hex(min(s + 999, b - 1)), 'topics': [SW]}])
    for lg in r:
        cnt[lg['topics'][1]] += 1; n += 1
print('total v4 swaps', n, 'pools', len(cnt))
STABLE = {'0x078d782b760474a361dda0af3839290b0ef57ad6': 'USDC', '0x9151434b16b9763660705744891fa906f660ecc5': 'USDT0', '0x588ce4f028d8e7b53b687865d6a67b3a54c75518': 'USDT'}
syms = {}
def sym(t):
    if t in syms: return syms[t]
    if t == '0x' + '0' * 40: syms[t] = 'ETH'; return 'ETH'
    try:
        h = call('eth_call', [{'to': t, 'data': '0x95d89b41'}, 'latest']); w = words(h)
        s = bytes.fromhex(''.join(w[2:])[:int(w[1], 16) * 2]).decode('utf-8', 'replace') if len(w) >= 3 else bytes.fromhex(h[2:]).rstrip(b'\0').decode('utf-8', 'replace')
    except Exception: s = t[:8]
    syms[t] = s; return s
rows = []
for pid, c in cnt.most_common(60):
    pk = words(call('eth_call', [{'to': POSM, 'data': '0x86b6be7d' + pid[2:52] + '0' * 14}, 'latest']))
    c0 = '0x' + pk[0][24:]; c1 = '0x' + pk[1][24:]; fee = int(pk[2], 16); hooks = '0x' + pk[4][24:]
    rows.append(dict(id=pid, n=c, c0=c0, c1=c1, s0=sym(c0), s1=sym(c1), fee=fee, hooks=hooks))
    print(c, pid[:12], sym(c0), sym(c1), fee, hooks[:12])
json.dump(rows, f, indent=1)
