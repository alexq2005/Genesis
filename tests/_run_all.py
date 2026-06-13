"""Helper: ejecuta todos los test_*.py y reporta total."""
import subprocess, os, sys, glob

# Los tests deben correr desde la RAÍZ del proyecto (abren web_ui.py, config.py
# y otros con rutas relativas a la raíz). Correr desde tests/ los rompe con
# FileNotFoundError falso. El raíz es el directorio padre de tests/.
tests_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(tests_dir)
files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(tests_dir, "test_*.py")))
total_p = 0
total_f = 0
issues = []

for f in files:
    try:
        r = subprocess.run(
            [sys.executable, os.path.join("tests", f)],
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
            cwd=root_dir,
        )
        out = (r.stdout or "") + (r.stderr or "")
        import re
        p = fl = 0
        # Formato A: "PASSED: N" / "FAILED: N"
        mA_p = re.search(r"PASSED:\s*(\d+)", out)
        mA_f = re.search(r"FAILED:\s*(\d+)", out)
        # Formato B: "N passed, N failed" (en cualquier parte)
        mB = re.search(r"(\d+)\s+passed,\s+(\d+)\s+failed", out)
        # Formato C: "RESULTADOS: N/M tests pasaron" (N pasaron, M-N fallaron)
        mC = re.search(r"RESULTADOS:\s*(\d+)\s*/\s*(\d+)", out)
        # Formato D: "N/M pasaron, K fallaron"
        mD = re.search(r"(\d+)\s*/\s*(\d+)\s+pasaron,\s*(\d+)\s+fallaron", out)
        # Formato E: "GENESIS vX.X Tests: N/M passed" (+ opcional "K FAILED")
        mE = re.search(r"Tests:\s*(\d+)\s*/\s*(\d+)\s+passed", out)
        # Tomamos el MAYOR valor reportado (algunos tests reportan subtotales)
        if mA_p: p = max(p, int(mA_p.group(1)))
        if mA_f: fl = max(fl, int(mA_f.group(1)))
        if mB:
            p = max(p, int(mB.group(1)))
            fl = max(fl, int(mB.group(2)))
        if mC:
            passed, total = int(mC.group(1)), int(mC.group(2))
            p = max(p, passed)
            fl = max(fl, total - passed)
        if mD:
            p = max(p, int(mD.group(1)))
            fl = max(fl, int(mD.group(3)))
        if mE:
            passed, total = int(mE.group(1)), int(mE.group(2))
            p = max(p, passed)
            fl = max(fl, total - passed)
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
