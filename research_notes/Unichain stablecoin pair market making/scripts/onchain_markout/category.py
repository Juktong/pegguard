"""Markout by flow category (entry contract / locker classification).
Usage: python3 -I category.py OUT_DIR PERSWAP_JSONL TXS_JSONL LABELS_JSON HORIZON"""
import sys, os, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import NAMES, ORDER, WSTART, WEND
OUT, PS, TXS, LAB, HZ = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
labels = json.load(open(LAB))
tx = {}
for l in open(TXS):
    t = json.loads(l); tx[t['hash']] = t
UNI_UR = {'0xef740bf23acae26f6492b10de645d6b98dc8eaf3', '0xfdf682f51fe81aa4898f0ae2163d8a55c127fbc7', '0xd1b797d92d87b688193a2b976efc8d577d204343'}
UNI_OTHER = {'0x73855d06de49d0fe4a9c42636ba96c62da12ff9c'}  # SwapRouter02 (verified name)
AGG_NAMES = {'MetaAggregationRouterV2': 'KyberSwap', 'AllowanceHolder': '0x', 'UnichainSettler': '0x', 'UnichainSettlerIntent': '0x',
             'AugustusV6': 'Velora/ParaSwap', 'LiFiDiamond': 'LI.FI', 'Permit2Proxy': 'LI.FI', 'DexRouter': 'OKX DEX', 'UniversalUniswapV4Adapter': 'OKX DEX',
             'UniversalUniswapV3Adaptor': 'OKX DEX', 'RelayApprovalProxyV3': 'Relay', 'SpokePoolPeriphery': 'Across', 'MayanForwarder2': 'Mayan', 'FastMCTP': 'Mayan',
             'OkuRouter': 'Oku', 'TychoRouterV3': 'Tycho', 'EthereumVaultConnector': 'Euler EVC', 'SwapRouter': 'Velodrome SwapRouter', 'UnichainExecutor': 'UnichainExecutor'}
# origins per entry address (over all stable-pool swaps)
orig_per_to = collections.defaultdict(set)
for t in tx.values():
    if t.get('to'): orig_per_to[t['to'].lower()].add(t['from'])
def cat(rec):
    t = tx.get(rec['tx'], {}); to = (t.get('to') or '').lower(); lk = (rec.get('sender') or '').lower()
    nm_to = labels.get(to, {}).get('name'); nm_lk = labels.get(lk, {}).get('name')
    if to in UNI_UR or lk in UNI_UR or to in UNI_OTHER or lk in UNI_OTHER: return 'Uniswap UniversalRouter/SwapRouter02'
    if nm_to == 'CaliburEntry': return 'Uniswap UniversalRouter/SwapRouter02' if lk in UNI_UR else 'EIP-7702 wallet (Calibur) other'
    for nm in (nm_to, nm_lk):
        if nm in AGG_NAMES: return 'Aggregator/solver/bridge: ' + AGG_NAMES[nm]
        if nm == 'UniversalRouter': return 'UniversalRouter (non-Uniswap deploy)'
    if labels.get(to, {}).get('verified'): return 'Other verified contract'
    n = len(orig_per_to.get(to, ()))
    return 'Unverified contract, <=10 EOAs (bot-like)' if n <= 10 else 'Unverified contract, >10 EOAs'
res = {}
agg_all = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
for l in open(PS):
    r = json.loads(l)
    if r['outlier'] or not (WSTART <= r['block'] < WEND): continue
    mh = r['mk'].get(HZ)
    if mh is None: continue
    c = cat(r)
    for key in ((r['pool'], c), ('ALL', c)):
        a = res.setdefault(key[0], collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0]))[key[1]]
        a[0] += 1; a[1] += r['notional']; a[2] += r['fee']; a[3] += r['fee'] - mh
out = {}
for pool, d in res.items():
    V = sum(v[1] for v in d.values())
    out[pool] = {c: dict(n=v[0], vol_share=v[1] / V, notional=v[1], fee_bps=v[2] / v[1] * 1e4, markout_exfee_bps=v[3] / v[1] * 1e4, markout_exfee_usd=v[3], share_of_pool_markout=None) for c, v in d.items()}
    tot = sum(v[3] for v in d.values())
    for c in out[pool]: out[pool][c]['share_of_pool_markout'] = out[pool][c]['markout_exfee_usd'] / tot if tot else None
    print('\n==', NAMES.get(pool, pool), f'V=${V:,.0f} total markout ${tot:,.2f}')
    for c, v in sorted(out[pool].items(), key=lambda kv: -kv[1]['notional']):
        print(f"   {c[:48]:48s} n={v['n']:6d} vol {v['vol_share']:.3f} AS {v['markout_exfee_bps']:+.3f}bp (${v['markout_exfee_usd']:+.2f}, {100*(v['share_of_pool_markout'] or 0):.0f}% of pool AS)")
json.dump(out, open(f"{OUT}/category_{os.path.basename(PS).replace('perswap_', '').replace('.jsonl', '')}_h{HZ}.json", 'w'), indent=1)
