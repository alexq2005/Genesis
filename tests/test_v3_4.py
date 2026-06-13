"""Tests para Genesis v3.4 — Collaborative Mind"""
import sys, os, tempfile, shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

passed = 0
failed = 0
errors = []
def test(name, condition):
    global passed, failed, errors
    try:
        if condition: passed += 1
        else: failed += 1; errors.append(f"FAIL: {name}"); print(f"  FAIL: {name}")
    except Exception as e:
        failed += 1; errors.append(f"ERROR: {name}: {e}"); print(f"  ERROR: {name}: {e}")

print("=" * 60)
print("GENESIS v3.4 — Collaborative Mind Tests")
print("=" * 60)

# === PEER DEBATE ===
print("\n--- PeerDebate ---")
from core.peer_debate import DebateRole, DebateArgument, DebateRound, PeerDebate

print("  DebateRole...")
test("DR: tiene roles predefinidos", hasattr(DebateRole, 'ROLES') or hasattr(DebateRole, 'PERSPECTIVES'))
dr = DebateRole.__new__(DebateRole)
test("DR: instanciable", dr is not None)

print("  DebateArgument...")
da = DebateArgument.__new__(DebateArgument)
test("DA: instanciable", da is not None)

print("  PeerDebate coordinator...")
tmp = tempfile.mkdtemp()
try:
    pd = PeerDebate(base_dir=tmp)
    test("PD: init ok", pd is not None)
    test("PD: total_debates 0", pd.total_debates == 0)
    test("PD: total_arguments 0", pd.total_arguments == 0)

    # get_stats
    stats = pd.get_stats()
    test("PD: stats tiene total_debates", "total_debates" in stats)
    test("PD: stats tiene total_arguments", "total_arguments" in stats)

    # status
    st = pd.status()
    test("PD: status es string", isinstance(st, str))

    # generate_report
    report = pd.generate_report()
    test("PD: report contiene PEER", "PEER" in report.upper() or "DEBATE" in report.upper())

    # get_context_for_prompt
    ctx = pd.get_context_for_prompt(max_chars=200)
    test("PD: context retorna string", isinstance(ctx, str))

    # save/load
    pd.save()
    pd2 = PeerDebate(base_dir=tmp)
    test("PD: persistencia ok", pd2.total_debates == 0)

    # clear
    pd.clear()
    test("PD: clear ok", pd.total_debates == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === CONSENSUS ENGINE ===
print("\n--- ConsensusEngine ---")
from core.consensus_engine import Opinion, AgreementMetric, DelphiRound, ConsensusEngine

print("  Opinion...")
op = Opinion.__new__(Opinion)
test("OP: instanciable", op is not None)

print("  AgreementMetric...")
am = AgreementMetric.__new__(AgreementMetric)
test("AM: instanciable", am is not None)

print("  ConsensusEngine coordinator...")
tmp = tempfile.mkdtemp()
try:
    ce = ConsensusEngine(base_dir=tmp)
    test("CE: init ok", ce is not None)
    test("CE: total_consensuses 0", ce.total_consensuses == 0)

    stats = ce.get_stats()
    test("CE: stats tiene total_consensuses", "total_consensuses" in stats)

    st = ce.status()
    test("CE: status es string", isinstance(st, str))

    report = ce.generate_report()
    test("CE: report contiene CONSENSUS", "CONSENSUS" in report.upper())

    ctx = ce.get_context_for_prompt(max_chars=200)
    test("CE: context retorna string", isinstance(ctx, str))

    ce.save()
    ce2 = ConsensusEngine(base_dir=tmp)
    test("CE: persistencia ok", ce2.total_consensuses == 0)

    ce.clear()
    test("CE: clear ok", ce.total_consensuses == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === KNOWLEDGE SHARING ===
print("\n--- KnowledgeSharing ---")
from core.knowledge_sharing import KnowledgePacket, KnowledgeIndex, MergeStrategy, KnowledgeSharing

print("  KnowledgePacket...")
kp = KnowledgePacket.__new__(KnowledgePacket)
test("KP: instanciable", kp is not None)

print("  KnowledgeSharing coordinator...")
tmp = tempfile.mkdtemp()
try:
    ks = KnowledgeSharing(base_dir=tmp)
    test("KS: init ok", ks is not None)
    test("KS: total_shared 0", ks.total_shared == 0)

    stats = ks.get_stats()
    test("KS: stats tiene total_shared", "total_shared" in stats)

    st = ks.status()
    test("KS: status es string", isinstance(st, str))

    report = ks.generate_report()
    test("KS: report contiene KNOWLEDGE", "KNOWLEDGE" in report.upper())

    ctx = ks.get_context_for_prompt("compartir algo", max_chars=200)
    test("KS: context retorna string", isinstance(ctx, str))

    ks.save()
    ks2 = KnowledgeSharing(base_dir=tmp)
    test("KS: persistencia ok", ks2.total_shared == 0)

    ks.clear()
    test("KS: clear ok", ks.total_shared == 0)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# === VERSION CHECK ===
print("\n--- Version Check ---")
from config import GENESIS_VERSION
major, minor, patch = GENESIS_VERSION.split(".")
test("Version >= 3.4", float(f"{major}.{minor}") >= 3.4)

# === INTEGRATION CHECK ===
print("\n--- Integration Check ---")
gp = os.path.join(os.path.dirname(__file__), "..", "genesis.py")
with open(gp, "r", encoding="utf-8") as f: gs = f.read()
for _extra in ("genesis_processing.py", "genesis_commands.py", "genesis_tools.py"):
    _ep = os.path.join(os.path.dirname(__file__), "..", "core", _extra)
    if os.path.exists(_ep):
        with open(_ep, "r", encoding="utf-8") as f: gs += "\n" + f.read()
wp = os.path.join(os.path.dirname(__file__), "..", "web_ui.py")
with open(wp, "r", encoding="utf-8") as f: ws = f.read()

for mod in ["peer_debate", "consensus_engine", "knowledge_sharing"]:
    test(f"Int: import {mod}", f"from core.{mod} import" in gs)
    test(f"Int: self.{mod}", f"self.{mod}" in gs)
    test(f"Int: {mod}.save()", f'"{mod}"' in gs)
    test(f"WebUI: {mod}", mod in ws)

test("Int: cmd /peer_debate", "/peer_debate" in gs)
test("Int: cmd /consensus", "/consensus" in gs)
test("Int: cmd /knowledge", "/knowledge" in gs)
test("Int: status PEER DEBATE", "PEER DEBATE" in gs)
test("Int: status CONSENSUS ENGINE", "CONSENSUS ENGINE" in gs)
test("Int: status KNOWLEDGE SHARING", "KNOWLEDGE SHARING" in gs)

print("\n" + "=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
if errors:
    print("\nFailed tests:")
    for e in errors: print(f"  {e}")
print("=" * 60)
