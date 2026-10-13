"""Minimal JSON-RPC helper (stdlib only) for Unichain public RPC."""
import json
import time
import urllib.request
import urllib.error

RPC = "https://mainnet.unichain.org"

_id = 0


def _post(payload, url=RPC, timeout=60):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "User-Agent": "pegguard-research/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def call(method, params, url=RPC, retries=6):
    global _id
    for attempt in range(retries):
        _id += 1
        try:
            res = _post({"jsonrpc": "2.0", "id": _id, "method": method, "params": params}, url)
            if "error" in res:
                err = res["error"]
                msg = str(err)
                if any(s in msg.lower() for s in ("rate", "limit exceeded", "too many", "timeout")) and attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise RuntimeError(msg)
            return res["result"]
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def batch(calls, url=RPC, retries=6):
    """calls: list of (method, params). Returns list of results (None on per-item error)."""
    global _id
    payload = []
    for m, p in calls:
        _id += 1
        payload.append({"jsonrpc": "2.0", "id": _id, "method": m, "params": p})
    for attempt in range(retries):
        try:
            res = _post(payload, url, timeout=120)
            if isinstance(res, dict):
                raise RuntimeError(str(res)[:300])
            byid = {r["id"]: r for r in res}
            out = []
            missing = 0
            for q in payload:
                r = byid.get(q["id"])
                if r is None or "error" in r:
                    missing += 1
                    out.append(None)
                else:
                    out.append(r["result"])
            if missing and attempt < retries - 1:
                # retry only missing ones
                idx = [i for i, o in enumerate(out) if o is None]
                time.sleep(1 + attempt)
                sub = batch([calls[i] for i in idx], url, retries=1) if attempt < retries - 2 else [None] * len(idx)
                for i, s in zip(idx, sub):
                    out[i] = s
            return out
        except (urllib.error.URLError, TimeoutError, ConnectionError, RuntimeError) as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def h2i(x):
    return int(x, 16)


def s256(word_hex):
    v = int(word_hex, 16)
    return v - (1 << 256) if v >= (1 << 255) else v


def words(data_hex):
    d = data_hex[2:] if data_hex.startswith("0x") else data_hex
    return [d[i:i + 64] for i in range(0, len(d), 64)]
