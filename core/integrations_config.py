"""Configuración de integraciones (correos, claves API, y futuros canales).

Schema-driven y extensible: para sumar un canal (WhatsApp/Telegram/…) se agrega
una sección al SCHEMA — el backend y el panel del engranaje lo toman solos.

SEGURIDAD:
- Las credenciales viven en `.env` (gitignored, única fuente de verdad — config.py
  ya lee de ahí). NUNCA se commitean ni se loguean.
- `get_config()` devuelve los secretos ENMASCARADOS (nunca el valor real).
- `set_config()` solo escribe claves del whitelist del SCHEMA (no inyección de env
  arbitrario), ignora valores vacíos o enmascarados, y no loguea valores.
"""
import os
from pathlib import Path

_ENV_PATH = Path(__file__).parent.parent / ".env"

# Secciones del panel. status: "active" (editable) | "soon" (próximamente, deshab.)
SCHEMA = [
    {
        "key": "email", "title": "Correos (Gmail)", "icon": "ti-mail",
        "status": "active",
        "help": ("App Passwords de Gmail (16 letras, requieren Verificación en 2 "
                 "pasos). NO sirve la contraseña normal."),
        "fields": [
            {"env": "GMAIL_USER", "label": "Cuenta de ENVÍO", "type": "text",
             "ph": "genesis.xxx@gmail.com"},
            {"env": "GMAIL_APP_PASSWORD", "label": "App Password (envío)",
             "type": "secret", "ph": "16 letras"},
            {"env": "GMAIL_READ_USER", "label": "Cuenta de LECTURA", "type": "text",
             "ph": "tucorreo@gmail.com"},
            {"env": "GMAIL_READ_APP_PASSWORD", "label": "App Password (lectura)",
             "type": "secret", "ph": "16 letras"},
        ],
    },
    {
        "key": "apikeys", "title": "Claves API", "icon": "ti-key", "status": "active",
        "help": "Claves de proveedores LLM (opcional — Genesis corre local por defecto).",
        "fields": [
            {"env": "GOOGLE_API_KEY", "label": "Google / Gemini", "type": "secret",
             "ph": "AIza..."},
            {"env": "OPENAI_API_KEY", "label": "OpenAI", "type": "secret",
             "ph": "sk-..."},
            {"env": "ANTHROPIC_API_KEY", "label": "Anthropic", "type": "secret",
             "ph": "sk-ant-..."},
        ],
    },
    {
        "key": "whatsapp", "title": "WhatsApp", "icon": "ti-brand-whatsapp",
        "status": "soon", "help": "Próximamente: comunicación por WhatsApp.",
        "fields": [
            {"env": "WHATSAPP_TOKEN", "label": "Token", "type": "secret", "ph": ""},
            {"env": "WHATSAPP_PHONE_ID", "label": "Phone Number ID", "type": "text",
             "ph": ""},
        ],
    },
    {
        "key": "telegram", "title": "Telegram", "icon": "ti-brand-telegram",
        "status": "soon", "help": "Próximamente: comunicación por Telegram.",
        "fields": [
            {"env": "TELEGRAM_BOT_TOKEN", "label": "Bot Token", "type": "secret",
             "ph": ""},
            {"env": "TELEGRAM_CHAT_ID", "label": "Chat ID", "type": "text", "ph": ""},
        ],
    },
]

# Whitelist de claves editables (solo estas se pueden escribir).
_ALLOWED = {f["env"] for s in SCHEMA for f in s["fields"]}


def _read_env():
    """Lee .env a dict {KEY: value}. {} si no existe."""
    out = {}
    try:
        if _ENV_PATH.exists():
            for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return out


def _mask(value):
    """Enmascara un secreto: '' si vacío; si no, '••••••' + últimos 2-4 chars."""
    v = (value or "").strip()
    if not v:
        return ""
    tail = v[-4:] if len(v) > 8 else v[-2:] if len(v) > 4 else ""
    return "••••••" + tail


def get_config():
    """Estado actual (para renderizar el panel). Secretos ENMASCARADOS."""
    env = _read_env()
    sections = []
    for s in SCHEMA:
        fields = []
        for f in s["fields"]:
            raw = env.get(f["env"], "") or os.environ.get(f["env"], "")
            is_set = bool((raw or "").strip())
            if f["type"] == "secret":
                shown = _mask(raw)          # nunca el valor real
            else:
                shown = raw                 # texto (ej. email) no es secreto
            fields.append({
                "env": f["env"], "label": f["label"], "type": f["type"],
                "ph": f.get("ph", ""), "set": is_set, "value": shown,
            })
        sections.append({
            "key": s["key"], "title": s["title"], "icon": s.get("icon", ""),
            "status": s["status"], "help": s.get("help", ""), "fields": fields,
        })
    return {"sections": sections}


def _write_env(updates):
    """Actualiza/agrega claves en .env preservando el resto (comentarios, otras
    vars). `updates` = {KEY: value}. Devuelve la cantidad escrita."""
    lines = []
    if _ENV_PATH.exists():
        lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    seen = set()
    out = []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k = s.partition("=")[0].strip()
            if k in updates:
                out.append(f"{k}={updates[k]}")
                seen.add(k)
                continue
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    _ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    return len(updates)


def set_config(payload):
    """Guarda credenciales. `payload` = {KEY: value}. Ignora claves fuera del
    whitelist, valores vacíos (= no cambiar) y enmascarados (= sin cambios).
    Escribe a .env y refresca os.environ. NO loguea valores."""
    if not isinstance(payload, dict):
        return {"ok": False, "error": "payload inválido"}
    updates = {}
    for k, v in payload.items():
        if k not in _ALLOWED:
            continue
        v = (v or "").strip()
        if not v or "•" in v:           # vacío o enmascarado → no tocar
            continue
        updates[k] = v
    if not updates:
        return {"ok": True, "updated": [], "msg": "Nada que cambiar."}
    try:
        _write_env(updates)
        for k, v in updates.items():    # efecto inmediato en el proceso
            os.environ[k] = v
        # nombres legibles de lo actualizado (sin valores)
        labels = []
        for s in SCHEMA:
            for f in s["fields"]:
                if f["env"] in updates:
                    labels.append(f["label"])
        return {"ok": True, "updated": labels}
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}
