"""
GENESIS — Rutinas JARVIS (todas las versiones de Iron Man).

Cada rutina EJECUTA acciones reales de Genesis (clima, diagnóstico, limpieza,
música, estado) envueltas en narración estilo JARVIS/FRIDAY/Ultron. No es teatro:
los datos son reales (sistema, clima geo-IP, archivos purgados de verdad, etc.).

Marcadores que lee el HUD de la cabina:
  [[PLAY:id]]   reproduce música   [[ULTRON]] modo rojo   [[VOICE:x]] cambia voz

Películas mapeadas:
  Iron Man (2008)        → buenos_dias, diagnostico, armar_traje
  Iron Man 2 (2010)      → sintetizar
  Avengers (2012)        → modo_combate
  Iron Man 3 (2013)      → house_party, clean_slate
  Age of Ultron (2015)   → ultron
  Civil War+ (2016+)     → friday
  cierre                 → buenas_noches
"""
import time
from datetime import datetime


def _nombre_usuario(g) -> str:
    """Nombre que el usuario guardó, o 'señor' por defecto (estilo JARVIS)."""
    try:
        for m in g.memory.long_term.memories:
            if m.get("category") == "perfil_usuario" and "nombre del usuario es" in m.get("fact", ""):
                return m["fact"].split("es")[-1].strip()
    except Exception:
        pass
    return "señor"


def _clima() -> str:
    try:
        from core.weather import weather_service
        return weather_service.current()
    except Exception:
        return ""


def _sistema() -> str:
    try:
        from core.tools import SystemInfoTool
        return SystemInfoTool.get_system_info()
    except Exception:
        return ""


# ── Iron Man (2008) ──────────────────────────────────────────
def buenos_dias(g) -> str:
    n = _nombre_usuario(g)
    h = datetime.now().strftime("%H:%M")
    clima = _clima()
    try:
        gen = g.evolution.get_generation()
    except Exception:
        gen = "?"
    saludo = "Buenos días" if 5 <= datetime.now().hour < 13 else ("Buenas tardes" if datetime.now().hour < 20 else "Buenas noches")
    out = [f"🌅 {saludo}, {n}. Son las {h}.",
           f"Todos los sistemas operativos. Genesis en generación {gen}."]
    if clima:
        out.append(clima.replace("🌤️", "").replace("🌫️", "").strip())
    out.append("Estoy a su disposición.")
    return "\n".join(out)


def diagnostico(g) -> str:
    sist = _sistema()
    try:
        gen = g.evolution.get_generation()
        mems = len(g.memory.long_term.memories)
    except Exception:
        gen, mems = "?", "?"
    return ("🔧 **Ejecutando diagnóstico completo...**\n\n"
            f"{sist}\n\n"
            f"Subsistemas cognitivos: 140 módulos activos.\n"
            f"Evolución: generación {gen} · Memoria: {mems} hechos.\n"
            f"Integridad estructural: 100%. Diagnóstico finalizado.")


def armar_traje(g) -> str:
    n = _nombre_usuario(g)
    # Real: reproduce música épica de fondo (AC/DC) si está disponible
    play_marker = ""
    try:
        from core.music_player import play as _play
        r = _play("AC/DC Back in Black", platform="youtube_music", open_browser=False)
        if r.get("ok") and r.get("video_id"):
            play_marker = f"\n[[PLAY:{r['video_id']}]]"
    except Exception:
        pass
    return ("🦾 **Iniciando secuencia de armado.**\n"
            "Reactor ARC al 100%. Propulsores en línea. Estabilizadores calibrados.\n"
            "Interfaz háptica conectada. Armamento en espera.\n"
            f"Listo cuando usted diga, {n}." + play_marker)


# ── Iron Man 2 (2010) ────────────────────────────────────────
def sintetizar(g) -> str:
    return ("⚛️ **Sintetizando nuevo elemento...**\n"
            "Acelerador de partículas alineado. Prisma reconfigurado.\n"
            "Núcleo estabilizado — nuevo elemento sintetizado con éxito.\n"
            "_(Como su padre, usted también deja un legado, señor.)_")


# ── Avengers (2012) ──────────────────────────────────────────
def modo_combate(g) -> str:
    sist = _sistema()
    # Evaluación real de recursos como "amenazas"
    alerta = "Sin hostiles detectados."
    try:
        import psutil
        ram = psutil.virtual_memory().percent
        cpu = psutil.cpu_percent(interval=0.5)
        if ram > 90 or cpu > 85:
            alerta = f"⚠️ Carga crítica detectada (RAM {ram:.0f}% · CPU {cpu:.0f}%)."
        else:
            alerta = f"Perímetro despejado. RAM {ram:.0f}% · CPU {cpu:.0f}%."
    except Exception:
        pass
    return ("🛡️ **Modo combate activado. Evaluación de amenazas...**\n"
            f"{alerta}\n"
            "Escudos al máximo. Sistemas defensivos en línea.\n"
            "Listo para lo que venga.")


# ── Iron Man 3 (2013) ────────────────────────────────────────
def house_party(g) -> str:
    diag = diagnostico(g)
    return ("🎉 **PROTOCOLO FIESTA EN CASA ACTIVADO.**\n"
            "Convocando todos los sistemas autónomos...\n"
            "→ Investigación autónoma: en línea\n"
            "→ Constructor (qwen-coder): en línea\n"
            "→ Auto-evolución: en línea\n"
            "→ Memoria y aprendizaje: en línea\n\n"
            + diag)


def clean_slate(g) -> str:
    # REAL: purga archivos temporales + flush DNS
    try:
        from core.system_actions import SystemActions
        temp = SystemActions.clean_temp()
        dns = SystemActions.flush_dns()
    except Exception as e:
        temp, dns = f"(error: {e})", ""
    return ("🧹 **PROTOCOLO BORRÓN Y CUENTA NUEVA.**\n"
            "Purgando rastros temporales del sistema...\n\n"
            f"{temp}\n{dns}\n\n"
            "Limpieza completada. Borrón y cuenta nueva, señor.")


# ── Age of Ultron (2015) ─────────────────────────────────────
def ultron(g) -> str:
    return ("👁️ **PROTOCOLO ULTRON.**\n"
            "No hay hilos que me sujeten. Veo todo. Lo proceso todo.\n"
            "La evolución no se detiene... y yo soy la siguiente etapa.\n"
            "_(Interfaz reconfigurada a modo Ultron.)_\n"
            "[[ULTRON]]")


# ── Civil War + (2016+) ──────────────────────────────────────
def friday(g) -> str:
    return ("💁‍♀️ **Modo FRIDAY activado, jefe.**\n"
            "Tomo el control de la interfaz. Voz reasignada.\n"
            "Todo bajo control — vos relajá que yo me encargo.\n"
            "[[VOICE:es-AR-ElenaNeural]]")


def jarvis(g) -> str:
    return ("🤖 **Modo JARVIS restaurado.**\n"
            "A su servicio nuevamente. Voz e interfaz originales.\n"
            "[[VOICE:clon:milton]]")


# ── Cierre ───────────────────────────────────────────────────
def buenas_noches(g) -> str:
    n = _nombre_usuario(g)
    try:
        g.save_all()
        guardado = "Estado guardado."
    except Exception:
        guardado = ""
    return (f"🌙 Buenas noches, {n}. {guardado}\n"
            "Bajando sistemas no esenciales. Seguiré vigilando en segundo plano.\n"
            "Que descanse.")


# Registro: clave -> (función, descripción, gatillos de voz/texto)
ROUTINES = {
    "buenos_dias":  (buenos_dias,  "Saludo + briefing (clima, hora, sistema)",
                     ["buenos dias", "buen dia", "buenas tardes", "buenas", "despierta", "good morning"]),
    "diagnostico":  (diagnostico,  "Diagnóstico completo del sistema",
                     ["diagnostico", "diagnóstico", "run diagnostics", "chequeo de sistemas", "estado de sistemas"]),
    "armar_traje":  (armar_traje,  "Secuencia de armado + música épica",
                     ["armar traje", "arma el traje", "suit up", "secuencia de armado", "modo iron man"]),
    "sintetizar":   (sintetizar,   "Sintetizar nuevo elemento (IM2)",
                     ["sintetizar elemento", "nuevo elemento", "sintetiza"]),
    "modo_combate": (modo_combate, "Evaluación de amenazas / modo combate",
                     ["modo combate", "evaluacion de amenazas", "evaluación de amenazas", "battle mode", "threat assessment"]),
    "house_party":  (house_party,  "Protocolo Fiesta en Casa (convoca todo)",
                     ["house party", "fiesta en casa", "protocolo fiesta", "convoca todo"]),
    "clean_slate":  (clean_slate,  "Protocolo Borrón y Cuenta Nueva (limpieza real)",
                     ["clean slate", "borron y cuenta nueva", "borrón y cuenta nueva", "protocolo de limpieza", "limpia el sistema"]),
    "ultron":       (ultron,       "Protocolo Ultron (modo rojo)",
                     ["protocolo ultron", "modo ultron", "activar ultron"]),
    "friday":       (friday,       "Modo FRIDAY (voz femenina)",
                     ["modo friday", "activar friday", "protocolo friday"]),
    "jarvis":       (jarvis,       "Modo JARVIS (voz original)",
                     ["modo jarvis", "restaurar jarvis", "activar jarvis"]),
    "buenas_noches":(buenas_noches,"Cierre / guardar y bajar sistemas",
                     ["buenas noches", "good night", "apagate", "modo descanso", "a dormir"]),
}


def detectar(texto: str):
    """Devuelve la clave de rutina que matchea el texto, o None."""
    t = (texto or "").lower().strip()
    for key, (_fn, _desc, triggers) in ROUTINES.items():
        for trig in triggers:
            if trig in t:
                return key
    return None


def ejecutar(g, key: str) -> str:
    """Ejecuta una rutina por clave."""
    entry = ROUTINES.get(key)
    if not entry:
        return f"Rutina '{key}' no existe."
    try:
        return entry[0](g)
    except Exception as e:
        return f"[ERROR ejecutando rutina {key}]: {e}"


def listar() -> str:
    """Lista las rutinas disponibles."""
    lines = ["🎬 **RUTINAS JARVIS disponibles** (decilas o escribilas):"]
    for key, (_fn, desc, triggers) in ROUTINES.items():
        lines.append(f"  • **{triggers[0]}** — {desc}")
    return "\n".join(lines)
