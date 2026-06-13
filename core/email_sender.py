"""
GENESIS — Envío de email (Gmail SMTP).

Capacidad de RED concedida explícitamente por un humano (no auto-otorgada: el
builder y el self_modifier de Genesis bloquean código de red a propósito).

Config (en .env, gitignored):
  GMAIL_USER=tucuenta@gmail.com
  GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # App Password de 16 chars (no la normal)

Gmail exige App Password (Cuenta Google → Seguridad → Verificación en 2 pasos →
Contraseñas de aplicaciones). La contraseña normal NO funciona para SMTP.
"""
import os
import re
import smtplib
import ssl
from email.message import EmailMessage

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _creds():
    """Lee credenciales de env (o config.py como fallback)."""
    user = os.environ.get("GMAIL_USER", "")
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not user or not pwd:
        try:
            import config
            user = user or getattr(config, "GMAIL_USER", "")
            pwd = pwd or getattr(config, "GMAIL_APP_PASSWORD", "")
        except Exception:
            pass
    return user.strip(), pwd.strip()


def is_configured() -> bool:
    """True si hay credenciales para enviar."""
    u, p = _creds()
    return bool(u and p)


def valid_email(addr: str) -> bool:
    return bool(_EMAIL_RE.match((addr or "").strip()))


def send_email(to: str, subject: str, body: str) -> dict:
    """Envía un email vía Gmail SMTP. Devuelve {ok, message}."""
    to = (to or "").strip()
    if not valid_email(to):
        return {"ok": False, "message": f"Dirección inválida: «{to}»"}
    user, pwd = _creds()
    if not user or not pwd:
        return {"ok": False, "message": (
            "Falta configurar el email. Generá un App Password de Gmail y poné "
            "GMAIL_USER y GMAIL_APP_PASSWORD en el .env.")}
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject or "(sin asunto)"
    msg.set_content(body or "")
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
        return {"ok": True, "message": f"Email enviado a {to}"}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "message": (
            "Login rechazado por Gmail. ¿Es un App Password válido (16 chars) y "
            "está la verificación en 2 pasos activa?")}
    except Exception as e:
        return {"ok": False, "message": f"No pude enviar: {str(e)[:160]}"}
