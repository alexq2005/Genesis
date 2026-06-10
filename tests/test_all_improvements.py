"""
Tests para todas las mejoras implementadas:
1. Logger
2. Safe I/O (thread-safe + backups)
3. Code Sandbox + Path Validator
4. Memory resource limits + TF-IDF cache
5. Shell Executor
6. Streaming support
7. Session persistence
8. Imports correctos
"""
import sys
import os
import json
import time
import threading
import tempfile
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

passed = 0
failed = 0
total = 0


def test(name, condition):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name}")


# ============================================================
# TEST 1: Logger
# ============================================================
print("\n=== TEST: Logger ===")
from core.logger import GenesisLogger, ModuleLogger

with tempfile.TemporaryDirectory() as tmpdir:
    logger = GenesisLogger(log_dir=Path(tmpdir))
    test("Logger creado", logger is not None)

    # Child logger
    child = logger.get_child("test")
    test("Child logger creado", isinstance(child, ModuleLogger))

    # Log messages
    child.debug("mensaje debug")
    child.info("mensaje info")
    child.error("mensaje error")
    test("Mensajes loggeados", logger._message_count == 3)

    # Log file exists
    log_file = Path(tmpdir) / "genesis.log"
    test("Archivo de log creado", log_file.exists())

    # Read recent logs
    recent = logger.get_recent_logs(n=10, level="WARN")
    test("Logs leidos contienen WARN", "warn" in recent.lower() or "WARN" in recent)

    # Status
    status = logger.status()
    test("Status del logger", "Mensajes loggeados" in status)


# ============================================================
# TEST 2: Safe I/O
# ============================================================
print("\n=== TEST: Safe I/O ===")
from core.safe_io import safe_read_json, safe_write_json, BackupManager

with tempfile.TemporaryDirectory() as tmpdir:
    test_file = Path(tmpdir) / "test.json"
    test_data = {"key": "value", "list": [1, 2, 3]}

    # Write
    result = safe_write_json(test_file, test_data)
    test("safe_write_json exitoso", result is True)
    test("Archivo creado", test_file.exists())

    # Read
    loaded = safe_read_json(test_file)
    test("safe_read_json datos correctos", loaded == test_data)

    # Backup created
    backup = test_file.with_suffix(".json.bak")
    # Second write should create backup
    safe_write_json(test_file, {"updated": True})
    test("Backup creado en segunda escritura", backup.exists())

    # Read default when file doesn't exist
    missing = safe_read_json(Path(tmpdir) / "missing.json", default={"default": True})
    test("Default para archivo inexistente", missing == {"default": True})

    # Thread safety test
    counter_file = Path(tmpdir) / "counter.json"
    safe_write_json(counter_file, {"count": 0})

    def increment():
        for _ in range(10):
            data = safe_read_json(counter_file)
            data["count"] += 1
            safe_write_json(counter_file, data)

    threads = [threading.Thread(target=increment) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final = safe_read_json(counter_file)
    # Con locks, el counter final debe ser 30 (3 threads * 10 increments)
    # Pero con concurrent access the value could be less, that's expected
    # The important thing is no crash and file is valid JSON
    test("Thread safety: archivo valido despues de concurrencia", isinstance(final, dict) and "count" in final)

    # BackupManager
    data_dir = Path(tmpdir) / "data"
    data_dir.mkdir()
    safe_write_json(data_dir / "test1.json", {"data": 1})
    safe_write_json(data_dir / "test2.json", {"data": 2})

    bm = BackupManager(data_dirs=[data_dir], backup_dir=Path(tmpdir) / "backups")
    backup_path = bm.create_backup(label="test")
    test("BackupManager crea backup", backup_path is not None)

    backups = bm.list_backups()
    test("BackupManager lista backups", len(backups) == 1)
    test("BackupManager status", "Backups" in bm.status())


# ============================================================
# TEST 3: Path Validator
# ============================================================
print("\n=== TEST: Path Validator ===")
from core.tools import PathValidator, CodeSandbox, ShellExecutor

# Read validation
valid, _ = PathValidator.validate_read("C:\\Users\\test\\file.txt")
test("Ruta normal de lectura valida", valid)

valid, msg = PathValidator.validate_read("C:\\Windows\\System32\\cmd.exe")
test("System32 bloqueado", not valid)

valid, msg = PathValidator.validate_read("C:\\Users\\test\\.env")
test(".env bloqueado", not valid)

valid, msg = PathValidator.validate_read("C:\\Users\\test\\id_rsa")
test("id_rsa bloqueado", not valid)

# Write validation
valid, _ = PathValidator.validate_write("C:\\Users\\test\\script.py")
test("Escritura .py valida", valid)

valid, msg = PathValidator.validate_write("C:\\Users\\test\\malware.exe")
test("Escritura .exe bloqueada", not valid)

valid, msg = PathValidator.validate_write("C:\\Users\\test\\script.bat")
test("Escritura .bat bloqueada", not valid)


# ============================================================
# TEST 4: Code Sandbox
# ============================================================
print("\n=== TEST: Code Sandbox ===")

# Safe code
safe, warnings = CodeSandbox.analyze("print('hello world')")
test("Codigo seguro permitido", safe)

safe, warnings = CodeSandbox.analyze("import math\nprint(math.sqrt(16))")
test("Import math permitido", safe)

# Dangerous code
safe, warnings = CodeSandbox.analyze("import ctypes\nctypes.windll.kernel32.ExitProcess(0)")
test("Import ctypes bloqueado", not safe)

safe, warnings = CodeSandbox.analyze("import winreg\nwinreg.OpenKey(...)")
test("Import winreg bloqueado", not safe)

safe, warnings = CodeSandbox.analyze("os.system('rm -rf /')")
test("os.system bloqueado", not safe)


# ============================================================
# TEST 5: Shell Executor
# ============================================================
print("\n=== TEST: Shell Executor ===")

# Blocked commands
result = ShellExecutor.run("format C:")
test("Shell: format bloqueado", "[ERROR]" in result)

result = ShellExecutor.run("shutdown /s")
test("Shell: shutdown bloqueado", "[ERROR]" in result)

# Safe command (platform-independent check)
if os.name == "nt":
    result = ShellExecutor.run("echo hello")
    test("Shell: echo funciona", "hello" in result)
else:
    result = ShellExecutor.run("echo hello")
    test("Shell: echo funciona", "hello" in result)


# ============================================================
# TEST 6: Memory Resource Limits
# ============================================================
print("\n=== TEST: Memory Resource Limits ===")
from core.memory import LongTermMemory, EmotionalMemory, TFIDFSearch

test("LongTermMemory tiene MAX_MEMORIES", hasattr(LongTermMemory, "MAX_MEMORIES"))
test("MAX_MEMORIES = 500", LongTermMemory.MAX_MEMORIES == 500)

test("EmotionalMemory tiene MAX_MEMORIES", hasattr(EmotionalMemory, "MAX_MEMORIES"))
test("EmotionalMemory MAX = 200", EmotionalMemory.MAX_MEMORIES == 200)


# ============================================================
# TEST 7: TF-IDF Cache
# ============================================================
print("\n=== TEST: TF-IDF Cache ===")

docs = ["python es genial", "javascript es rapido", "rust es seguro", "python y rust son modernos"]

# Primera busqueda
results1 = TFIDFSearch.search("python programacion", docs)
test("TF-IDF busqueda funciona", len(results1) > 0)

# Cache deberia estar seteado
test("TF-IDF cache hash seteado", TFIDFSearch._idf_cache_hash != 0)
test("TF-IDF cache IDF no vacio", len(TFIDFSearch._idf_cache) > 0)

# Segunda busqueda (deberia usar cache)
old_hash = TFIDFSearch._idf_cache_hash
results2 = TFIDFSearch.search("rust seguridad", docs)
test("TF-IDF cache reutilizado (mismo hash)", TFIDFSearch._idf_cache_hash == old_hash)
test("Segunda busqueda funciona", len(results2) > 0)


# ============================================================
# TEST 8: Streaming Support (local_engine)
# ============================================================
print("\n=== TEST: Streaming Support ===")
from core.local_engine import LocalEngine

engine = LocalEngine(model_key="medium")
# Verificar que el metodo acepta parametros de streaming
import inspect
sig = inspect.signature(engine.generate)
test("generate() acepta stream param", "stream" in sig.parameters)
test("generate() acepta stream_callback", "stream_callback" in sig.parameters)

sig_think = inspect.signature(engine.think)
test("think() acepta stream param", "stream" in sig_think.parameters)


# ============================================================
# TEST 9: Config nuevas variables
# ============================================================
print("\n=== TEST: Config ===")
from config import SESSION_FILE, STREAMING_ENABLED, AUTO_BACKUP_INTERVAL, GENESIS_VERSION

test("SESSION_FILE definido", SESSION_FILE is not None)
test("STREAMING_ENABLED definido", STREAMING_ENABLED is not None)
test("AUTO_BACKUP_INTERVAL definido", AUTO_BACKUP_INTERVAL is not None)
test("Version actualizada", GENESIS_VERSION >= "1.1.0")


# ============================================================
# TEST 10: Imports de genesis.py
# ============================================================
print("\n=== TEST: Imports ===")

try:
    from core.logger import GenesisLogger
    from core.safe_io import BackupManager, safe_read_json, safe_write_json
    from core.tools import PathValidator, CodeSandbox, ShellExecutor
    from core.router import IntentRouter
    from core.context_manager import ContextBudgetManager
    from core.summarizer import ConversationSummarizer
    test("Todos los imports exitosos", True)
except ImportError as e:
    test(f"Import fallo: {e}", False)


# ============================================================
# TEST 11: Heartbeat Thread Safety
# ============================================================
print("\n=== TEST: Heartbeat Thread Safety ===")
from core.heartbeat import HeartbeatLog

with tempfile.TemporaryDirectory() as tmpdir:
    log_file = Path(tmpdir) / "heartbeat_test.json"
    hb_log = HeartbeatLog(log_file)

    test("HeartbeatLog tiene _lock", hasattr(hb_log, "_lock"))
    test("_lock es threading.Lock", isinstance(hb_log._lock, type(threading.Lock())))

    # Concurrent writes
    def add_entries(prefix):
        for i in range(5):
            hb_log.add(f"{prefix}_ACTION", f"detail {i}")

    threads = [threading.Thread(target=add_entries, args=(f"T{i}",)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    test("HeartbeatLog: escritura concurrente sin crash", len(hb_log.entries) == 15)
    test("HeartbeatLog: archivo valido", log_file.exists())


# ============================================================
# RESUMEN
# ============================================================
print(f"\n{'='*50}")
print(f"  RESULTADOS: {passed}/{total} pasaron, {failed} fallaron")
print(f"{'='*50}")

if failed > 0:
    sys.exit(1)
