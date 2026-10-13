"""Download all logs for address+topic0 from Blockscout etherscan-compatible API, paginating by block.
usage: python3 bs_logs.py <base_api> <address> <topic0> <outfile.jsonl> [fromBlock] [toBlock] [extra k=v ...]
"""
import json, sys, time, urllib.request

base, address, topic0, outf = sys.argv[1:5]
frm = int(sys.argv[5]) if len(sys.argv) > 5 else 0
to = sys.argv[6] if len(sys.argv) > 6 else "latest"
extra = dict(a.split("=", 1) for a in sys.argv[7:])

seen = set()
n = 0
with open(outf, "w") as fo:
    while True:
        q = f"{base}?module=logs&action=getLogs&fromBlock={frm}&toBlock={to}&address={address}&topic0={topic0}"
        for k, v in extra.items():
            q += f"&{k}={v}"
        for attempt in range(40):
            try:
                req = urllib.request.Request(q, headers={"user-agent": "research/1.0"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    j = json.loads(r.read())
                break
            except Exception as e:
                print("retry", attempt, e, flush=True)
                time.sleep(min(60, 3 * (attempt + 1)))
        else:
            raise SystemExit("failed")
        res = j.get("result") or []
        if not isinstance(res, list):
            print("unexpected", str(j)[:300]); break
        new = 0
        maxb = frm
        for e in res:
            key = (e["transactionHash"], e["logIndex"])
            b = int(e["blockNumber"], 16)
            maxb = max(maxb, b)
            if key in seen:
                continue
            seen.add(key)
            fo.write(json.dumps(e) + "\n")
            new += 1
        n += new
        print(f"from {frm}: got {len(res)} new {new} total {n} maxblock {maxb}", flush=True)
        if len(res) < 1000:
            break
        if maxb == frm and new == 0:
            frm += 1
        else:
            frm = maxb
        time.sleep(0.4)
print("DONE", n)
