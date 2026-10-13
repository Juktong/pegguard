"""GeckoTerminal fetcher with polite rate limiting and on-disk cache.
usage: python3 gt.py <outdir> <path1> [path2 ...]   (paths relative to /api/v2/)
"""
import json, os, sys, time, urllib.request, hashlib

BASE = "https://api.geckoterminal.com/api/v2/"
_last = [0.0]

def fetch(path, outdir, force=False):
    fn = os.path.join(outdir, "gt_" + hashlib.sha1(path.encode()).hexdigest()[:16] + ".json")
    if os.path.exists(fn) and not force:
        return json.load(open(fn))
    for attempt in range(6):
        wait = 5.0 - (time.time() - _last[0])
        if wait > 0:
            time.sleep(wait)
        _last[0] = time.time()
        try:
            req = urllib.request.Request(BASE + path, headers={"accept": "application/json", "user-agent": "research/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                j = json.loads(r.read())
            j["_path"] = path
            j["_fetched_at"] = int(time.time())
            json.dump(j, open(fn, "w"))
            return j
        except urllib.error.HTTPError as e:
            if e.code == 404:
                j = {"_path": path, "_error": 404, "_fetched_at": int(time.time())}
                json.dump(j, open(fn, "w"))
                return j
            print("http", e.code, path, flush=True)
            time.sleep(10 * (attempt + 1))
        except Exception as e:
            print("err", e, path, flush=True)
            time.sleep(5 * (attempt + 1))
    return None

if __name__ == "__main__":
    out = sys.argv[1]
    for p in sys.argv[2:]:
        j = fetch(p, out)
        print(p, "ok" if j and "data" in j else "fail", flush=True)
