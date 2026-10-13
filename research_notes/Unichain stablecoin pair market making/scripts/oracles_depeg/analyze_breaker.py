# Breaker-design analysis on real Pyth on-chain samples (Sonic PriceFeedUpdate logs).
# Usage: analyze_breaker.py <sonic_120d.jsonl> <sonic_oct10_2025.jsonl>
import sys, json, math, time, collections

C, T = 'eaa020c6', '2b89b9dc'


def q(a, p):
    a = sorted(a)
    k = (len(a) - 1) * p
    f = int(k)
    c = min(f + 1, len(a) - 1)
    return a[f] + (a[c] - a[f]) * (k - f)


def st(a):
    return f"n={len(a)} p50={q(a,.5):.2f} p90={q(a,.9):.2f} p99={q(a,.99):.2f} p999={q(a,.999):.2f} max={max(a):.2f}"


def U(t):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t))


def load(p):
    by = collections.defaultdict(dict)
    for l in open(p):
        r = json.loads(l)
        by[r['id']][r['publishTime']] = (r['price'] * 1e-8, r['conf'] * 1e-8)
    return by


def conf_gate_sim(series, label, mult=3, w=0.1):
    """Replicates PegGuardHook conf gate: flag if confE2 > mult*EMA; EMA updated (9*ema+x)/10 on every obs."""
    ema = 0
    flagged = 0
    runs = []
    cur = 0
    for t, (p, c) in series:
        x = c / p * 1e6  # bps*100
        f = ema != 0 and x > ema * mult
        if f:
            flagged += 1
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
        ema = x if ema == 0 else (ema * 9 + x) / 10
    print(f"  conf-gate sim [{label}] mult={mult}: flagged {flagged}/{len(series)} = {flagged/len(series)*100:.3f}%  longest run={max(runs) if runs else 0}")


def main():
    big = load(sys.argv[1])
    oct25 = load(sys.argv[2])
    # 1) Dense USDC/USD series (pushed every ~6 s in part of the window)
    cs = sorted(big[C].items())
    gaps = [b[0] - a[0] for a, b in zip(cs, cs[1:])]
    dense = [(a, b) for a, b in zip(cs, cs[1:]) if b[0] - a[0] <= 10]
    print(f"USDC/USD Sonic samples={len(cs)} window {U(cs[0][0])} -> {U(cs[-1][0])}; consecutive pairs with gap<=10s: {len(dense)}")
    d6 = [abs(b[1][0] / a[1][0] - 1) * 1e4 for a, b in dense]
    print("  |delta price| over consecutive <=10s updates (bps):", st(d6))
    # 60 s horizon on dense stretch
    idx = {t: v for t, v in cs}
    ts = [t for t, _ in cs]
    j = 0
    d60 = []
    for i, t in enumerate(ts):
        while j < len(ts) and ts[j] < t + 60:
            j += 1
        if j < len(ts) and ts[j] - t <= 70 and all(ts[k + 1] - ts[k] <= 10 for k in range(i, j)):
            d60.append(abs(idx[ts[j]][0] / idx[t][0] - 1) * 1e4)
    if d60:
        print("  |delta price| over ~60s on dense stretches (bps):", st(d60))
    # deviation from trailing EMA(450 s) on dense stretches
    e = None
    lt = None
    dev_e = []
    for t, (p, c) in cs:
        x = (p - 1) * 1e4
        if e is None or t - lt > 600:
            e = x
        else:
            k = (t - lt) / ((t - lt) + 450)
            e = e + k * (x - e)
            dev_e.append(abs(x - e))
        lt = t
    print("  |USDC dev - trailing EMA450| (bps):", st(dev_e))
    print("  USDC conf/price (bps):", st([c / p * 1e4 for _, (p, c) in cs]))
    conf_gate_sim(cs, 'USDC/USD Sonic 120d')
    ts_ = sorted(big[T].items())
    conf_gate_sim(ts_, 'USDT/USD Sonic 120d (hourly)')
    # 2) Paired ratio over 120 d (hourly heartbeat), z-score style metrics
    common = sorted(set(big[C]) & set(big[T]))
    R = []
    for t in common:
        pc, cc = big[C][t]
        pt, ct = big[T][t]
        r = pc / pt
        conf_lin = (cc / pc + ct / pt) * 1e4
        R.append((t, (r - 1) * 1e4, conf_lin, (cc / pc) * 1e4, (ct / pt) * 1e4))
    print(f"RATIO paired n={len(R)} {U(common[0])} -> {U(common[-1])}")
    print("  |ratio-1| bps:", st([abs(x[1]) for x in R]))
    print("  ratio-1 signed: min=%.2f max=%.2f" % (min(x[1] for x in R), max(x[1] for x in R)))
    print("  conf_lin(ratio) bps:", st([x[2] for x in R]))
    print("  |ratio-1|/conf_lin:", st([abs(x[1]) / x[2] for x in R]))
    # change of ratio over 1 h (consecutive heartbeat samples ~3600s apart)
    dh = [abs(b[1] - a[1]) for a, b in zip(R, R[1:]) if 3000 <= b[0] - a[0] <= 4000]
    print("  |delta ratio| over ~1h (bps):", st(dh))
    # 3) Oct-10-2025 window: candidate rules
    cs2 = sorted(oct25[C].items())
    ts2 = sorted(oct25[T].items())
    com2 = sorted(set(oct25[C]) & set(oct25[T]))
    print(f"OCT-10-2025 Sonic paired samples={len(com2)}; USDC samples={len(cs2)} USDT samples={len(ts2)}")
    conf_gate_sim(ts2, 'USDT/USD Oct-10-2025 window (feed-level gate)')
    conf_gate_sim(cs2, 'USDC/USD Oct-10-2025 window (feed-level gate)')
    rows = []
    for t in com2:
        pc, cc = oct25[C][t]
        pt, ct = oct25[T][t]
        rows.append((t, (pc / pt - 1) * 1e4, (cc / pc + ct / pt) * 1e4))
    for th in [25, 30, 40, 50]:
        hit = [r for r in rows if abs(r[1]) > th]
        print(f"  rule |ratio-1|>{th}bps: first {U(hit[0][0]) if hit else '-'} last {U(hit[-1][0]) if hit else '-'} samples={len(hit)}")
    for k in [0.5, 1.0]:
        for th in [25, 50]:
            hit = [r for r in rows if abs(r[1]) - k * r[2] > th]
            print(f"  rule |ratio-1| - {k}*conf_lin > {th}bps: samples={len(hit)} first {U(hit[0][0]) if hit else '-'}")
    mx = max(rows, key=lambda r: abs(r[1]))
    print(f"  max |ratio-1| {mx[1]:.1f} bps at {U(mx[0])} conf_lin {mx[2]:.1f}")
    print(f"  max conf_lin {max(r[2] for r in rows):.1f} bps; pre-crash (18:00-21:15) median conf_lin {q([r[2] for r in rows if 1760119200 <= r[0] <= 1760130900], .5):.1f}")


main()
