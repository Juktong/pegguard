"""Fetch tx objects (or receipts) for hashes listed in a file, 10 per batch, N threads; output JSONL (trimmed)."""
import sys, json, os, time, threading
from concurrent.futures import ThreadPoolExecutor
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rpcutil import batch
mode, hfile, out, nthreads = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
hs = [l.strip() for l in open(hfile) if l.strip()]
done = set()
if os.path.exists(out):
    for l in open(out):
        try: done.add(json.loads(l)['hash'])
        except Exception: pass
todo = [h for h in hs if h not in done]
print('todo', len(todo), flush=True)
lock = threading.Lock(); f = open(out, 'a')
method = 'eth_getTransactionByHash' if mode == 'tx' else 'eth_getTransactionReceipt'
def trim(h, x):
    if x is None: return {'hash': h, 'missing': True}
    if mode == 'tx':
        inp = x.get('input', '0x')
        return {'hash': h, 'from': x['from'], 'to': x.get('to'), 'sel': inp[:10], 'inlen': (len(inp) - 2) // 2,
                'nonce': int(x['nonce'], 16), 'gasPrice': int(x.get('gasPrice', '0x0'), 16),
                'maxPrio': int(x['maxPriorityFeePerGas'], 16) if x.get('maxPriorityFeePerGas') else None,
                'gas': int(x['gas'], 16), 'block': int(x['blockNumber'], 16), 'txi': int(x['transactionIndex'], 16), 'type': x.get('type')}
    return {'hash': h, 'from': x['from'], 'to': x.get('to'), 'status': x['status'], 'gasUsed': int(x['gasUsed'], 16),
            'egp': int(x.get('effectiveGasPrice', '0x0'), 16), 'l1Fee': int(x['l1Fee'], 16) if x.get('l1Fee') else None,
            'logs': [{'a': lg['address'], 't': lg['topics'], 'd': lg['data'][:2 + 64 * 8], 'i': int(lg['logIndex'], 16)} for lg in x['logs']]}
def work(chunk):
    r = batch([(method, [h]) for h in chunk])
    rows = [json.dumps(trim(h, x)) for h, x in zip(chunk, r)]
    with lock:
        f.write('\n'.join(rows) + '\n'); f.flush()
t0 = time.time()
chunks = [todo[i:i + 10] for i in range(0, len(todo), 10)]
with ThreadPoolExecutor(nthreads) as ex:
    for i, _ in enumerate(ex.map(work, chunks)):
        if i % 500 == 0: print(i, len(chunks), round(time.time() - t0, 1), flush=True)
print('done', round(time.time() - t0, 1))
