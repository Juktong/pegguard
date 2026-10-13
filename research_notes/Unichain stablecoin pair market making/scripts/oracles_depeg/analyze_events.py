# Profile historical stablecoin depeg events from 1-minute CEX candles.
# dev (bps) = side * (price - 1) * 1e4, so positive = depeg magnitude in the chosen direction.
import sys, json, time
D = sys.argv[1]


def T(t):
    return time.strftime('%Y-%m-%d %H:%M', time.gmtime(t))


def load(fn, invert=False):
    d = json.load(open(f"{D}/{fn}"))
    out = []
    for t, v in d['rows']:
        o, h, l, c, vol = v
        if invert:
            o, h, l, c = 1 / o, 1 / l, 1 / h, 1 / c
        out.append((int(t), o, h, l, c, vol))
    return out


def profile(rows, label, side):
    dev = [(r[0], side * (r[4] - 1) * 1e4, side * ((r[3] if side < 0 else r[2]) - 1) * 1e4) for r in rows]
    pk = max(dev, key=lambda x: x[2])
    pkc = max(dev, key=lambda x: x[1])
    print(f"[{label}] {T(rows[0][0])} -> {T(rows[-1][0])} n={len(rows)}; peak 1m-extreme {pk[2]:.0f} bps at {T(pk[0])}; peak close {pkc[1]:.0f} bps at {T(pkc[0])}")
    for th in [10, 25, 50, 100, 200, 500, 1000]:
        cross = [t for t, c, _ in dev if c > th]
        if not cross:
            print(f"   >{th:>4} bps: never (close)")
            continue
        first, last = cross[0], cross[-1]
        s5 = None
        run = 0
        for t, c, _ in dev:
            run = run + 1 if c > th else 0
            if run == 5:
                s5 = t
                break
        print(f"   >{th:>4} bps: first {T(first)}  sustained5m {T(s5) if s5 else '-'}  last {T(last)}  minutes_above={len(cross)}  first->peakclose {(pkc[0]-first)/60:.0f} min  first->last {(last-first)/3600:.1f} h")


ev = [('bitstamp_usdcusd_1m_2023-03.json', False, -1, 'USDC/USD Bitstamp Mar-2023'),
      ('okx_usdcusdt_1m_2023-03.json', False, -1, 'USDC/USDT OKX Mar-2023'),
      ('bitstamp_usdtusd_1m_2023-03.json', False, +1, 'USDT/USD Bitstamp Mar-2023 (upside)'),
      ('coinbase_daiusd_1m_2023-03.json', False, -1, 'DAI/USD Coinbase Mar-2023'),
      ('bitstamp_usdtusd_1m_2022-05.json', False, -1, 'USDT/USD Bitstamp May-2022'),
      ('coinbase_usdtusd_1m_2022-05.json', False, -1, 'USDT/USD Coinbase May-2022'),
      ('okx_usdcusdt_1m_2022-05.json', True, -1, 'USDT/USDC OKX May-2022 (=1/USDC-USDT)'),
      ('bitstamp_usdcusd_1m_2022-05.json', False, +1, 'USDC/USD Bitstamp May-2022 (upside)'),
      ('coinbase_usdtusd_1m_2023-03.json', False, +1, 'USDT/USD Coinbase Mar-2023 (upside)'),
      ('okx_usdcusdt_1m_2025-10.json', False, -1, 'USDC/USDT OKX Oct-2025 (downside)'),
      ('okx_usdcusdt_1m_2025-10.json', False, +1, 'USDC/USDT OKX Oct-2025 (upside)'),
      ('coinbase_usdtusd_1m_2025-10.json', False, -1, 'USDT/USD Coinbase Oct-2025 (downside)'),
      ('coinbase_usdtusd_1m_2025-10.json', False, +1, 'USDT/USD Coinbase Oct-2025 (upside)')]
for fn, inv, side, label in ev:
    try:
        profile(load(fn, inv), label, side)
    except FileNotFoundError:
        print('missing', fn)
k = json.load(open(f"{D}/kraken_usdeusd_trades_2025-10-10.json"))['rows']
m = min(k, key=lambda x: x[1])
lowk = [x for x in k if x[1] < 0.995]
print(f"[USDe/USD Kraken trades 2025-10-10 20:00 -> 10-11 08:00 UTC] n={len(k)} min {m[1]} at {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(m[0]))}; trades<0.995: {len(lowk)}"
      + (f" first {time.strftime('%H:%M:%S', time.gmtime(lowk[0][0]))} last {time.strftime('%H:%M:%S', time.gmtime(lowk[-1][0]))}" if lowk else ""))
