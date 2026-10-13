import json, bisect, glob
class StepRef:
    """value(ts) = last observation with obs_time <= ts (obs_time = candle close time for 1s candles)."""
    def __init__(self, pts, max_stale):
        pts = sorted(pts); self.t = [p[0] for p in pts]; self.v = [p[1] for p in pts]; self.max_stale = max_stale
    def at(self, ts):
        i = bisect.bisect_right(self.t, ts) - 1
        if i < 0 or ts - self.t[i] > self.max_stale: return None
        return self.v[i]
class BucketRef:
    """value(ts) = candle value for the bucket containing ts (ex-post, look-ahead within bucket)."""
    def __init__(self, d, bar, fallback_stale_buckets=0):
        self.d = d; self.bar = bar; self.fb = fallback_stale_buckets
    def at(self, ts):
        b = (int(ts) // self.bar) * self.bar
        for k in range(self.fb + 1):
            v = self.d.get(b - k * self.bar)
            if v is not None: return v
        return None
def okx_rows(paths):
    rows = {}
    for p in paths:
        for l in open(p):
            r = json.loads(l); rows[int(r[0]) // 1000] = r
    return rows
def make_okx1s(paths):
    rows = okx_rows(paths)
    # candle [s, s+1) close observed at s+1
    return StepRef([(s + 1, float(r[4])) for s, r in rows.items()], max_stale=5), rows
def make_okx1m(path, mode='vwap'):
    rows = okx_rows([path]); d = {}
    for s, r in rows.items():
        vb, vq = float(r[5]), float(r[7])
        d[s] = (vq / vb) if (mode == 'vwap' and vb > 0) else float(r[4])
    return BucketRef(d, 60), rows
def make_cb1m(path):
    d = {}
    for l in open(path):
        t, lo, hi, op, cl, vol = json.loads(l)
        d[int(t)] = 1.0 / float(cl)  # USDT-USDC close -> USDC/USDT
    return BucketRef(d, 60, fallback_stale_buckets=5)
