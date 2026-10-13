import sys, json, time
sys.path.insert(0, sys.argv[1])
from sol_pyth import fetch
out=sys.argv[2]; dur=float(sys.argv[3]); cad=float(sys.argv[4])
t0=time.time(); n=0; errs=0
with open(out,'a') as f:
    while time.time()-t0<dur:
        ts=time.time()
        try:
            r=fetch(); f.write(json.dumps(r)+"\n"); f.flush(); n+=1
        except Exception as e:
            errs+=1
        time.sleep(max(0, cad-(time.time()-ts)))
print('polls',n,'errs',errs)
