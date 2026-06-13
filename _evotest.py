import sys, time
sys.path.insert(0, '.')
out = []
t0 = time.time()
from genesis import Genesis
g = Genesis()
out.append(f"Genesis instanciado en {round(time.time()-t0,1)}s")

accepted = 0
for i in range(5):
    t = time.time()
    try:
        r = g._auto_mutate_code()
    except Exception as e:
        r = {"mutated": False, "message": "EXC " + str(e)[:80]}
    dt = round(time.time() - t, 1)
    if r.get("mutated"):
        accepted += 1
        out.append(f"[{i+1}] ACEPTADA ({dt}s): {r.get('file')} +{r.get('additions',0)}/-{r.get('deletions',0)}")
    else:
        out.append(f"[{i+1}] no ({dt}s): {str(r.get('message',''))[:90]}")

out.append(f"=== {accepted}/5 mutaciones aceptadas ===")
open("_evotest_result.txt", "w", encoding="utf-8").write("\n".join(out))
print("done")
