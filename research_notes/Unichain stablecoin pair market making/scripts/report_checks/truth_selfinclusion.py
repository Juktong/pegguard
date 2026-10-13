"""Run the repo's own shadow/truth.py labeler on synthetic sparse swaps.

Each swap moves the pool price in its own direction; the oracle fair is flat
and the swap direction is random relative to fair. If truth_corr is ~100% on
isolated swaps, the label is tautological (own post-swap mid sets the basis).
"""
import random, sqlite3, sys
sys.path.insert(0, sys.argv[1])
from shadow import db, truth

WAD = 10**18
def run(gap_sec, n=400, seed=1):
    rnd = random.Random(seed)
    conn = sqlite3.connect(":memory:"); conn.row_factory = sqlite3.Row
    db.init(conn)
    mid = WAD
    fair = WAD  # flat fair: no swap is genuinely "correcting" more than chance
    t = 1_000_000_000
    cols = [r[1] for r in conn.execute("PRAGMA table_info(ledger)")]
    for i in range(n):
        z = rnd.random() < 0.5
        impact = rnd.uniform(0.2e-4, 1.0e-4)  # 0.2-1 bp price impact
        post = int(mid * (1 - impact)) if z else int(mid * (1 + impact))
        row = {c: None for c in cols if c != "id"}
        row.update(ts_ms=t, block_number=i, tx_hash=f"0x{i:x}", log_index=0,
                   pre_mid_e18=str(mid), post_mid_e18=str(post), ab_e18="0", aq_e6=0,
                   zero_for_one=int(z), regime="CALM", fresh_fair_e18=str(fair), created_at_ms=t)
        keys = ",".join(row); qs = ",".join("?" * len(row))
        conn.execute(f"INSERT INTO ledger ({keys}) VALUES ({qs})", list(row.values()))
        mid = post
        # mean-revert pool toward fair between swaps so the fair stays meaningful
        mid = int(mid + (fair - mid) * 0.5)
        t += gap_sec * 1000
    truth.process_delayed_truth(conn, now_ms=t + 10**7)
    rows = conn.execute("SELECT truth_corr FROM truth").fetchall()
    return sum(r[0] for r in rows) / len(rows), len(rows)

for gap in (700, 400, 200, 80, 20, 5):
    frac, k = run(gap)
    print(f"inter-arrival {gap:>4}s  swaps/±300s window ~{min(600//gap,600)+1:>3}  truth_corr share = {frac:.1%}  (n={k})")
