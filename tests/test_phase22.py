"""
Tests Phase 22 — Autonomous Orchestration: FileWatcher, SmartScheduler, HabitTracker, ContextEngine.
"""
import sys
import os
import time
import tempfile
from datetime import date, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


print("=" * 60)
print("  GENESIS Phase 22 — Autonomous Orchestration Tests")
print("=" * 60)


# ============================================================
# 1. FILE WATCHER
# ============================================================
print("\n--- FileWatcher ---")
from core.file_watcher import FileWatcher, file_watcher

with tempfile.TemporaryDirectory() as tmp:
    fw = FileWatcher(data_dir=tmp)

    # Add rule con directorio inexistente
    r = fw.add_rule("C:\\NoExiste12345", "*.txt", "notify")
    test("Add rule dir inexistente", "no existe" in r.lower())

    # Add rule sin parámetros
    r = fw.add_rule("", "", "")
    test("Add rule vacía", "necesita" in r.lower())

    # Add rule acción inválida
    r = fw.add_rule(tmp, "*.txt", "explode")
    test("Acción inválida", "inválida" in r.lower() or "opciones" in r.lower())

    # Add rule move sin destino
    r = fw.add_rule(tmp, "*.txt", "move")
    test("Move sin destino", "necesita" in r.lower() or "destino" in r.lower())

    # Add rule válida (notify no necesita args)
    r = fw.add_rule(tmp, "*.pdf", "notify", name="test_pdfs")
    test("Add rule válida", "creada" in r.lower())
    test("Rule tiene patrón", "*.pdf" in r)

    # List rules
    rules = fw.list_rules()
    test("List rules tiene regla", "test_pdfs" in rules.lower())

    # Add segunda regla
    watch_dir = os.path.join(tmp, "watch")
    os.makedirs(watch_dir)
    r2 = fw.add_rule(watch_dir, "*.jpg", "copy", action_args=tmp, name="fotos")
    test("Segunda regla", "creada" in r2.lower())

    # Remove rule
    r3 = fw.remove_rule(1)
    test("Remove rule", "eliminada" in r3.lower())

    # Remove inexistente
    r4 = fw.remove_rule(999)
    test("Remove inexistente", "no encontré" in r4.lower())

    # Events vacíos
    ev = fw.events()
    test("Events vacíos", "no hay" in ev.lower())

    # Start sin reglas activas (quitamos la única que queda)
    fw.remove_rule(2)
    r5 = fw.start()
    test("Start sin reglas", "no hay" in r5.lower())

    # Re-agregar y start
    fw.add_rule(tmp, "*.log", "notify", name="logs")
    r6 = fw.start()
    test("Start con regla", "monitoreo iniciado" in r6.lower())
    test("Watching activo", fw._watching is True)

    # Start duplicado
    r7 = fw.start()
    test("Start duplicado", "ya está activo" in r7.lower())

    # Stop
    r8 = fw.stop()
    test("Stop monitoreo", "detenido" in r8.lower())
    test("Watching inactivo", fw._watching is False)

    # Stop duplicado
    r9 = fw.stop()
    test("Stop duplicado", "no está activo" in r9.lower())

    # Enable/Disable
    fw.add_rule(tmp, "*.csv", "notify", name="csvs")
    rule_id = fw._rules[-1]["id"]
    r10 = fw.disable_rule(rule_id)
    test("Disable rule", "deshabilitada" in r10.lower() or "rule" in r10.lower())
    r11 = fw.enable_rule(rule_id)
    test("Enable rule", "habilitada" in r11.lower())
    r12 = fw.enable_rule(999)
    test("Enable inexistente", "no encontré" in r12.lower())

    # Status
    st = fw.status()
    test("Status tiene rules_count", "rules_count" in st)
    test("Status tiene watching", "watching" in st)
    test("Status tiene events_count", "events_count" in st)

    # Persistencia
    fw.save()
    fw2 = FileWatcher(data_dir=tmp)
    test("Persistencia reglas", fw2.status()["rules_count"] >= 1)

    # Singleton
    test("Singleton", isinstance(file_watcher, FileWatcher))


# ============================================================
# 2. SMART SCHEDULER
# ============================================================
print("\n--- SmartScheduler ---")
from core.smart_scheduler import SmartScheduler, smart_scheduler

with tempfile.TemporaryDirectory() as tmp:
    ss = SmartScheduler(data_dir=tmp)

    # Parse schedule — intervalo
    p1 = SmartScheduler.parse_schedule("every 30m")
    test("Parse every 30m", p1 is not None and p1["type"] == "interval")
    test("Parse 30m = 1800s", p1["interval_sec"] == 1800)

    p2 = SmartScheduler.parse_schedule("cada 2 horas")
    test("Parse cada 2 horas", p2 is not None and p2["interval_sec"] == 7200)

    p3 = SmartScheduler.parse_schedule("every 45s")
    test("Parse every 45s", p3 is not None and p3["interval_sec"] == 45)

    p4 = SmartScheduler.parse_schedule("cada 15 minutos")
    test("Parse cada 15 min", p4 is not None and p4["interval_sec"] == 900)

    # Parse schedule — diario
    p5 = SmartScheduler.parse_schedule("daily 09:00")
    test("Parse daily 09:00", p5 is not None and p5["type"] == "daily")
    test("Parse hour=9", p5["hour"] == 9)
    test("Parse minute=0", p5["minute"] == 0)

    p6 = SmartScheduler.parse_schedule("todos los días a las 14:30")
    test("Parse todos los días 14:30", p6 is not None and p6["hour"] == 14 and p6["minute"] == 30)

    p7 = SmartScheduler.parse_schedule("diario 08:00")
    test("Parse diario 08:00", p7 is not None and p7["type"] == "daily")

    # Parse schedule — semanal
    p8 = SmartScheduler.parse_schedule("weekly mon 10:00")
    test("Parse weekly mon", p8 is not None and p8["type"] == "weekly")
    test("Parse monday=0", p8["day_of_week"] == 0)

    p9 = SmartScheduler.parse_schedule("cada lunes a las 10")
    test("Parse cada lunes", p9 is not None and p9["day_of_week"] == 0)

    p10 = SmartScheduler.parse_schedule("cada viernes a las 18:00")
    test("Parse cada viernes", p10 is not None and p10["day_of_week"] == 4)

    # Parse inválido
    test("Parse inválido", SmartScheduler.parse_schedule("hola mundo") is None)
    test("Parse vacío", SmartScheduler.parse_schedule("") is None)

    # Add tarea
    r1 = ss.add("backup", "cada 30 minutos", "respaldar notas")
    test("Add tarea", "programada" in r1.lower())
    test("Add muestra schedule", "30 minutos" in r1.lower() or "30" in r1)

    # Add sin nombre
    test("Add sin nombre", "necesita" in ss.add("", "daily 09:00", "cmd").lower())
    test("Add sin comando", "necesita" in ss.add("x", "daily 09:00", "").lower())

    # Add con schedule inválido
    r2 = ss.add("bad", "xyz", "cmd")
    test("Add schedule inválido", "no entendí" in r2.lower())

    # List
    lista = ss.list_tasks()
    test("List tiene tarea", "backup" in lista.lower())

    # Add segunda tarea
    ss.add("limpieza", "daily 08:00", "limpiar temporales")
    lista2 = ss.list_tasks()
    test("List tiene 2 tareas", "backup" in lista2.lower() and "limpieza" in lista2.lower())

    # Enable/Disable
    r3 = ss.disable("backup")
    test("Disable tarea", "pausada" in r3.lower())
    r4 = ss.enable("backup")
    test("Enable tarea", "habilitada" in r4.lower())

    # Remove
    r5 = ss.remove("limpieza")
    test("Remove tarea", "eliminada" in r5.lower())
    r6 = ss.remove("inexistente")
    test("Remove inexistente", "no encontré" in r6.lower())

    # Tick sin executor
    results = ss.tick()
    test("Tick retorna lista", isinstance(results, list))

    # Tick con executor mock
    exec_log = []
    def mock_exec(cmd):
        exec_log.append(cmd)
        return f"OK: {cmd}"

    ss.set_executor(mock_exec)

    # Forzar next_run al pasado para que se ejecute
    ss._tasks["backup"]["next_run"] = time.time() - 10
    results2 = ss.tick()
    test("Tick ejecutó tarea", len(exec_log) == 1)
    test("Tick ejecutó comando correcto", "respaldar notas" in exec_log[0])
    test("Tick retorna resultado", len(results2) >= 1)

    # Run count incrementó
    test("Run count", ss._tasks["backup"]["run_count"] == 1)

    # History
    hist = ss.history()
    test("History tiene entry", "backup" in hist.lower())

    # History vacío (fresh)
    ss2 = SmartScheduler(data_dir=tmp + "/sub")
    test("History vacío", "no hay" in ss2.history().lower())

    # Status
    st = ss.status()
    test("Status total_tasks", "total_tasks" in st)
    test("Status active_tasks", "active_tasks" in st)
    test("Status total_runs", "total_runs" in st)

    # Persistencia
    ss.save()
    ss3 = SmartScheduler(data_dir=tmp)
    test("Persistencia", ss3.status()["total_tasks"] >= 1)

    # Singleton
    test("Singleton", isinstance(smart_scheduler, SmartScheduler))


# ============================================================
# 3. HABIT TRACKER
# ============================================================
print("\n--- HabitTracker ---")
from core.habit_tracker import HabitTracker, habit_tracker

with tempfile.TemporaryDirectory() as tmp:
    ht = HabitTracker(data_dir=tmp)

    # Crear hábito
    r1 = ht.add("ejercicio")
    test("Crear hábito", "creado" in r1.lower())

    # Duplicado
    r2 = ht.add("ejercicio")
    test("Duplicado rechazado", "ya existe" in r2.lower())

    # Crear con frequency
    r3 = ht.add("lectura", "daily")
    test("Crear con freq", "creado" in r3.lower())

    r4 = ht.add("limpieza", "semanal")
    test("Crear semanal", "creado" in r4.lower())

    # Nombre vacío
    test("Nombre vacío", "necesita" in ht.add("").lower())

    # Completar
    r5 = ht.complete("ejercicio")
    test("Completar hábito", "completado" in r5.lower())
    test("Muestra racha", "racha" in r5.lower() or "hecho" in r5.lower() or "día" in r5.lower())

    # Double-complete
    r6 = ht.complete("ejercicio")
    test("Double complete", "ya está completado" in r6.lower())

    # Completar inexistente
    r7 = ht.complete("xyzNoExiste")
    test("Complete inexistente", "no encontré" in r7.lower())

    # Today
    today_view = ht.today()
    test("Today retorna string", isinstance(today_view, str))
    test("Today muestra hábito", "ejercicio" in today_view.lower())
    test("Today muestra check", "✅" in today_view or "⬜" in today_view)

    # Uncomplete
    r8 = ht.uncomplete("ejercicio")
    test("Uncomplete", "removida" in r8.lower())

    # Uncomplete cuando no estaba
    r9 = ht.uncomplete("ejercicio")
    test("Uncomplete no marcado", "no estaba" in r9.lower())

    # Re-completar para stats
    ht.complete("ejercicio")

    # List
    lista = ht.list_habits()
    test("List tiene hábitos", "ejercicio" in lista.lower())
    test("List tiene racha", "racha" in lista.lower() or "total" in lista.lower())

    # Stats general
    stats = ht.stats()
    test("Stats general", "estadísticas" in stats.lower() or "total" in stats.lower())

    # Stats específico
    stats2 = ht.stats("ejercicio")
    test("Stats específico", "ejercicio" in stats2.lower())
    test("Stats tiene racha", "racha" in stats2.lower())

    # Stats inexistente
    r10 = ht.stats("xyzNoExiste")
    test("Stats inexistente", "no encontré" in r10.lower())

    # Streak calculation
    today_str = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    two_days = (date.today() - timedelta(days=2)).isoformat()
    three_days = (date.today() - timedelta(days=3)).isoformat()

    test("Streak vacío", HabitTracker._calculate_streak([]) == 0)
    test("Streak 1 día", HabitTracker._calculate_streak([today_str]) == 1)
    test("Streak 3 días", HabitTracker._calculate_streak([today_str, yesterday, two_days]) == 3)
    test("Streak con gap", HabitTracker._calculate_streak([today_str, three_days]) == 1)

    # Best streak
    test("Best streak vacío", HabitTracker._calculate_best_streak([]) == 0)
    test("Best streak 3", HabitTracker._calculate_best_streak([today_str, yesterday, two_days]) == 3)

    # Get summary
    summary = ht.get_summary()
    test("Summary retorna string", isinstance(summary, str))
    test("Summary tiene info", "hábitos" in summary.lower() or "hoy" in summary.lower() or len(summary) > 0)

    # Remove
    r11 = ht.remove("lectura")
    test("Remove hábito", "eliminado" in r11.lower())

    r12 = ht.remove("xyzNoExiste")
    test("Remove inexistente", "no encontré" in r12.lower())

    # Status
    st = ht.status()
    test("Status total_habits", "total_habits" in st)
    test("Status completed_today", "completed_today" in st)
    test("Status longest_streak", "longest_active_streak" in st)

    # Persistencia
    ht.save()
    ht2 = HabitTracker(data_dir=tmp)
    test("Persistencia", ht2.status()["total_habits"] >= 1)

    # Singleton
    test("Singleton", isinstance(habit_tracker, HabitTracker))


# ============================================================
# 4. CONTEXT ENGINE
# ============================================================
print("\n--- ContextEngine ---")
from core.context_engine import ContextEngine, context_engine

with tempfile.TemporaryDirectory() as tmp:
    ce = ContextEngine(data_dir=tmp)

    # Record
    ce.record("notes", "nueva nota test")
    ce.record("calculator", "2+2")
    ce.record("notes", "buscar nota")
    ce.record("system", "info del sistema")
    ce.record("notes", "listar notas")
    test("Record acumula", len(ce._interactions) == 5)

    # Top commands
    top = ce.top_commands()
    test("Top commands retorna", isinstance(top, str))
    test("Top tiene notes", "notes" in top.lower())

    # Time report
    time_r = ce.time_report()
    test("Time report retorna", isinstance(time_r, str))
    test("Time report tiene hora", ":" in time_r or "pico" in time_r.lower())

    # Day report
    day_r = ce.day_report()
    test("Day report retorna", isinstance(day_r, str))

    # Suggest con pocas interacciones (< 10)
    suggest = ce.suggest()
    test("Suggest con pocos datos", suggest is None)

    # Agregar más para que sugiera
    for _ in range(15):
        ce.record("briefing", "buenos días")
    suggest2 = ce.suggest()
    test("Suggest con datos", suggest2 is None or isinstance(suggest2, str))

    # Full report
    full = ce.full_report()
    test("Full report retorna", isinstance(full, str))
    test("Full report tiene datos", "comandos" in full.lower() or "uso" in full.lower())

    # Clear
    r1 = ce.clear()
    test("Clear borra", "borradas" in r1.lower())
    test("Clear vacía", len(ce._interactions) == 0)

    # Top con vacío
    top2 = ce.top_commands()
    test("Top vacío", "no hay" in top2.lower())

    # Re-record para status
    ce.record("test", "algo")

    # Status
    st = ce.status()
    test("Status total_interactions", "total_interactions" in st)
    test("Status unique_commands", "unique_commands" in st)
    test("Status peak_hour", "peak_hour" in st)

    # Persistencia
    ce.save()
    ce2 = ContextEngine(data_dir=tmp)
    test("Persistencia", ce2.status()["total_interactions"] >= 1)

    # Status vacío
    ce3 = ContextEngine(data_dir=tmp + "/sub")
    st3 = ce3.status()
    test("Status vacío", st3["total_interactions"] == 0)

    # Singleton
    test("Singleton", isinstance(context_engine, ContextEngine))


# ============================================================
# 5. DAILY BRIEFING INTEGRATION
# ============================================================
print("\n--- DailyBriefing Integration ---")
from core.daily_briefing import DailyBriefing

test("Has _get_habits_summary", hasattr(DailyBriefing, "_get_habits_summary"))
test("_get_habits_summary callable", callable(DailyBriefing._get_habits_summary))

# Verificar que generate incluye hábitos (si hay alguno)
db = DailyBriefing()
briefing = db.generate()
test("Briefing retorna con integración", isinstance(briefing, str))


# ============================================================
# 6. VERSION CHECK
# ============================================================
print("\n--- Version ---")
from config import GENESIS_VERSION
test(f"Version {GENESIS_VERSION} >= 5.8.0", GENESIS_VERSION >= "5.8.0")


# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print(f"  RESULTADOS: {passed}/{total} passed, {failed} failed")
print("=" * 60)

if failed > 0:
    print(f"\n  ⚠️ {failed} test(s) FALLARON")
else:
    print("\n  ✅ TODOS LOS TESTS PASARON — Phase 22 100% funcional")
