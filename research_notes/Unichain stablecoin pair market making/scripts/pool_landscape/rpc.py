"""Minimal JSON-RPC helpers (stdlib only) for Unichain/other EVM chains."""
import json, time, urllib.request, urllib.error

RPC = "https://mainnet.unichain.org"

# ---------------- keccak256 (pure python) ----------------
_RC = [0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
       0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
       0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
       0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
       0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
       0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008]
_ROT = [[0, 36, 3, 41, 18], [1, 44, 10, 45, 2], [62, 6, 43, 15, 61], [28, 55, 25, 21, 56], [27, 20, 39, 8, 14]]
M64 = (1 << 64) - 1

def _rol(x, n):
    return ((x << n) | (x >> (64 - n))) & M64 if n else x

def _f(A):
    for rc in _RC:
        C = [A[x][0] ^ A[x][1] ^ A[x][2] ^ A[x][3] ^ A[x][4] for x in range(5)]
        D = [C[(x - 1) % 5] ^ _rol(C[(x + 1) % 5], 1) for x in range(5)]
        A = [[A[x][y] ^ D[x] for y in range(5)] for x in range(5)]
        B = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                B[y][(2 * x + 3 * y) % 5] = _rol(A[x][y], _ROT[x][y])
        A = [[B[x][y] ^ ((~B[(x + 1) % 5][y]) & B[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]
        A[0][0] ^= rc
    return A

def keccak(data: bytes) -> bytes:
    rate = 136
    p = bytearray(data) + b"\x01"
    while len(p) % rate:
        p += b"\x00"
    p[-1] |= 0x80
    A = [[0] * 5 for _ in range(5)]
    for off in range(0, len(p), rate):
        blk = p[off:off + rate]
        for i in range(rate // 8):
            x, y = i % 5, i // 5
            A[x][y] ^= int.from_bytes(blk[8 * i:8 * i + 8], "little")
        A = _f(A)
    out = b""
    for i in range(4):
        x, y = i % 5, i // 5
        out += A[x][y].to_bytes(8, "little")
    return out

def sel(sig):
    return "0x" + keccak(sig.encode()).hex()[:8]

def topic(sig):
    return "0x" + keccak(sig.encode()).hex()

# ---------------- RPC ----------------
_id = 0
def rpc(method, params, url=None, retries=6):
    global _id
    _id += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id, "method": method, "params": params}).encode()
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url or RPC, data=body, headers={"content-type": "application/json", "user-agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=90) as r:
                j = json.loads(r.read())
            if "error" in j:
                raise RuntimeError(j["error"])
            return j["result"]
        except RuntimeError:
            raise
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last

def batch(calls, url=None, retries=6):
    """calls: list of (method, params). Returns list of results (or Exception)."""
    body = json.dumps([{"jsonrpc": "2.0", "id": i, "method": m, "params": p} for i, (m, p) in enumerate(calls)]).encode()
    last = None
    for k in range(retries):
        try:
            req = urllib.request.Request(url or RPC, data=body, headers={"content-type": "application/json", "user-agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                j = json.loads(r.read())
            if isinstance(j, dict):
                raise RuntimeError(j)
            out = [None] * len(calls)
            for e in j:
                out[e["id"]] = RuntimeError(e["error"]) if "error" in e else e["result"]
            return out
        except Exception as e:
            last = e
            time.sleep(1.5 * (k + 1))
    raise last

def eth_call(to, data, block="latest", url=None):
    return rpc("eth_call", [{"to": to, "data": data}, block], url=url)

def calls(reqs, block="latest", url=None, chunk=10):
    """reqs: list of (to, data). returns list of hex results or None on revert."""
    out = []
    for i in range(0, len(reqs), chunk):
        part = reqs[i:i + chunk]
        res = batch([("eth_call", [{"to": t, "data": d}, block]) for t, d in part], url=url)
        out += [None if isinstance(r, Exception) else r for r in res]
    return out

def block_number(url=None):
    return int(rpc("eth_blockNumber", [], url=url), 16)

def get_logs(address, topics, frm, to, url=None, step=None, verbose=False):
    """Adaptive range splitting getLogs."""
    out = []
    step = step or (to - frm + 1)
    cur = frm
    while cur <= to:
        end = min(to, cur + step - 1)
        try:
            flt = {"fromBlock": hex(cur), "toBlock": hex(end), "topics": topics}
            if address:
                flt["address"] = address
            res = rpc("eth_getLogs", [flt], url=url, retries=3)
            out += res
            if verbose:
                print(f"  logs {cur}-{end}: {len(res)} (total {len(out)})", flush=True)
            cur = end + 1
            if len(res) < 2000:
                step = min(step * 2, 50_000_000)
        except Exception as e:
            if step <= 1:
                raise
            step = max(1, step // 4)
            if verbose:
                print(f"  shrink step -> {step}: {str(e)[:120]}", flush=True)
    return out

# ---------------- ABI helpers ----------------
def enc_addr(a):
    return a.lower().replace("0x", "").rjust(64, "0")

def enc_uint(v):
    return hex(v & ((1 << 256) - 1))[2:].rjust(64, "0")

def words(hexdata):
    h = hexdata[2:] if hexdata.startswith("0x") else hexdata
    return [h[i:i + 64] for i in range(0, len(h), 64)]

def u(w):
    return int(w, 16)

def s(w, bits=256):
    v = int(w, 16)
    if v >= 1 << 255:
        v -= 1 << 256
    return v

def addr(w):
    return "0x" + w[-40:]

def dec_string(hexdata):
    if not hexdata or hexdata == "0x":
        return None
    try:
        h = hexdata[2:]
        if len(h) == 64:  # bytes32
            return bytes.fromhex(h).rstrip(b"\x00").decode(errors="replace")
        off = int(h[:64], 16) * 2
        ln = int(h[off:off + 64], 16)
        return bytes.fromhex(h[off + 64:off + 64 + ln * 2]).decode(errors="replace")
    except Exception:
        return None
