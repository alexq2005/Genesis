"""Helper: ejecuta todos los test_*.py y reporta total."""
import subprocess, os, sys, glob

os.chdir(os.path.dirname(os.path.abspath(__file__)))
files = sorted(glob.glob("test_*.py"))
total_p = 0
total_f = 0
issues = []

for f in files:
    try:
        r = subprocess.run(
            [sys.executable, f],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        out = (r.stdout or "") + (r.stderr or "")
        import re
        p = fl = 0
        # Formato A: "PASSED: N" / "FAILED: N"
        mA_p = re.search(r"PASSED:\s*(\d+)", out)
        mA_f = re.search(r"FAILED:\s*(\d+)", out)
        # Formato B: "N passed, N failed" (en cualquier parte)
        mB = re.search(r"(\d+)\s+passed,\s+(\d+)\s+failed", out)
        # Tomamos el MAYOR valor reportado (algunos tests reportan subtotales)
        if mA_p: p = max(p, int(mA_p.group(1)))
        if mA_f: fl = max(fl, int(mA_f.group(1)))
        if mB:
            p = max(p, int(mB.group(1)))
            fl = max(fl, int(mB.group(2)))
        total_p += p
        total_f += fl
        rc = r.returncode
        tag = "OK " if (fl == 0 and rc == 0) else "FAIL"
        print(f"  [{tag}] {f}: {p} passed, {fl} failed, rc={rc}")
        if rc != 0 or fl > 0:
            issues.append((f, p, fl, rc))
    except subprocess.TimeoutExpired:
        print(f"  [TOUT] {f}")
        issues.append((f, 0, 0, -1))

print()
print(f"TOTAL PASSED: {total_p}")
print(f"TOTAL FAILED: {total_f}")
print(f"Files with issues: {len(issues)}")
