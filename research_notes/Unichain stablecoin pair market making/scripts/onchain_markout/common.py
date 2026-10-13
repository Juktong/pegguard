import json, bisect, math
WSTART, WEND = 58509241, 61101241  # 2026-09-13 00:00:00 UTC .. 2026-10-13 00:00:00 UTC (exclusive)
GEN = 1730748359
NAMES = {
 '0x77ea9d2be50eb3e82b62db928a1bcc573064dd2a14f5026847e755518c8659c9': 'v4 USDC/USDT0 1bp',
 '0xaf58ab3ed922b34e94d13e01edf1b4ddbe5d2afbc29abbcef5ef8ff752a1ae5a': 'v4 USDC/USDT0 0.18bp',
 '0xc7ee4db44db3234cb0a3dc7fb2fd4d068d9bfb0c71092fc4a21edb2d95e34306': 'v4 USDC/USDT0 0.2bp',
 '0x2c6809bbb1ddc601d76ddee68f17e683bd8430795f1b38b1cb7b0d4c28b73e88': 'v4 USDC/USDT0 0.4bp',
 '0x3d4d39a2ec28d80efa72679e47b8d4621caeecc15af8f21be97db234657d5fa7': 'v4 USDC/USDT(bridged) 5bp',
 '0x5c75bfb6194d7d763d33ea292cbc50cda806451b': 'v3 USDC/USDT0 1bp',
 '0x1dfab2147401be78ea05f05a0379f86ec87a81cc': 'v3 USDC/USDT(bridged) 1bp',
 '0xe92c7cc875245a86faf088febe4614e1e318bef5': 'v3 USDC/USDT0 5bp',
 '0x31bafd5d04580f71a808ae646bb787d38e9362f9': 'Slipstream USDC/USDT0 1bp',
 '0x3188bf36b4ac5127d077a5e873ec297cd1d05447a70ae05cdf8e7c3e74a4e48d': 'v4 USDC/DAI 1bp',
 '0xa3851829dd8fd7c336c9049e3f6b2b84581e0958fed5333757c6f9c595f4e4f0': 'v4 USDC/USDT(bridged) 1bp',
}
ORDER = list(NAMES)
def price(sqrtP):
    return (sqrtP / 2 ** 96) ** 2
def pct(xs, q):
    if not xs: return float('nan')
    xs = sorted(xs); k = (len(xs) - 1) * q; f = math.floor(k); c = math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c] - xs[f]) * (k - f)
def load_swaps(out_dir):
    return json.load(open(out_dir + '/swaps.json'))
def load_okx(path_glob_list, bar):
    """returns sorted list of (ts_sec, open, high, low, close, vol_base, vol_quote)"""
    rows = {}
    for p in path_glob_list:
        for l in open(p):
            r = json.loads(l)
            rows[int(r[0]) // 1000] = (int(r[0]) // 1000, float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5]), float(r[7]))
    return [rows[k] for k in sorted(rows)]
class Ref:
    """Step-function reference: value at time t = close of the latest candle that has CLOSED by t
    (candle [s, s+bar) closes at s+bar). mode='close' or 'vwap' (vwap falls back to close when vol=0)."""
    def __init__(self, candles, bar, mode='close'):
        self.t = [c[0] + bar for c in candles]
        if mode == 'close':
            self.v = [c[4] for c in candles]
        else:
            self.v = [(c[6] / c[5]) if c[5] > 0 else c[4] for c in candles]
        self.bar = bar
    def at(self, ts, max_stale=None):
        i = bisect.bisect_right(self.t, ts) - 1
        if i < 0: return None
        if max_stale is not None and ts - self.t[i] > max_stale: return None
        return self.v[i]
