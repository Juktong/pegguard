"""Fetch logs via public RPC using batched 10k-block getLogs (Unichain public RPC limits: 10k blocks/range, 10 calls/batch).
usage: python3 rpc_logs.py <address> <topics_json> <from> <to|latest> <out.jsonl>
topics_json e.g. '["0x40e9...", ["0xid1","0xid2"]]'
"""
import json, sys, time
import rpc

addr, topics, frm, to, out = sys.argv[1], json.loads(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
to = rpc.block_number() if to == "latest" else int(to)
STEP = 10000
ranges = [(b, min(to, b + STEP - 1)) for b in range(frm, to + 1, STEP)]
n = 0
t0 = time.time()
with open(out, "w") as fo:
    for i in range(0, len(ranges), 10):
        part = ranges[i:i + 10]
        calls = [("eth_getLogs", [{"fromBlock": hex(a), "toBlock": hex(b), "address": addr, "topics": topics}]) for a, b in part]
        for attempt in range(30):
            try:
                res = rpc.batch(calls)
                bad = [k for k, r in enumerate(res) if isinstance(r, Exception)]
                if bad:
                    raise RuntimeError(f"sub-errors {[str(res[k])[:100] for k in bad[:2]]}")
                break
            except Exception as e:
                print("retry", i, attempt, str(e)[:160], flush=True)
                time.sleep(min(30, 2 * (attempt + 1)))
        else:
            raise SystemExit("failed at range %s" % (part[0],))
        for r in res:
            for e in r:
                fo.write(json.dumps(e) + "\n")
                n += 1
        if (i // 10) % 20 == 0:
            print(f"{part[-1][1]} / {to}  logs {n}  {time.time()-t0:.0f}s", flush=True)
        time.sleep(0.15)
print("DONE", n, "to", to)
