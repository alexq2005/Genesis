"""
GENESIS — Lectura de email (Gmail IMAP).

Lee la bandeja de entrada vía IMAP (imap.gmail.com:993 SSL). Capacidad de red
concedida por humano (no auto-otorgada).

Credenciales (en .env, gitignored). Para leer TU casilla personal, usá una
cuenta distinta a la de envío:
  GMAIL_READ_USER=alexq2005@gmail.com
  GMAIL_READ_APP_PASSWORD=xxxx xxxx xxxx xxxx   # App Password de ESA cuenta
Si no se setean, cae a GMAIL_USER / GMAIL_APP_PASSWORD (la cuenta de Genesis).

Gmail exige App Password (16 chars) + Verificación en 2 pasos, igual que el envío.
IMAP debe estar habilitado en Gmail (Config → Reenvío y POP/IMAP → IMAP activado).
"""
import os
import email
import imaplib
from email.header import decode_header

_IMAP_HOST = "imap.gmail.com"
_IMAP_PORT = 993


def _creds():
    user = os.environ.get("GMAIL_READ_USER", "") or os.environ.get("GMAIL_USER", "")
    pwd = os.environ.get("GMAIL_READ_APP_PASSWORD", "") or os.environ.get("GMAIL_APP_PASSWORD", "")
    if not user or not pwd:
        try:
            import config
            user = user or getattr(config, "GMAIL_READ_USER", "") or getattr(config, "GMAIL_USER", "")
            pwd = pwd or getattr(config, "GMAIL_READ_APP_PASSWORD", "") or getattr(config, "GMAIL_APP_PASSWORD", "")
        except Exception:
            pass
    return user.strip(), pwd.strip()


def is_configured() -> bool:
    u, p = _creds()
    return bool(u and p)


def _decode(s) -> str:
    if not s:
        return ""
    parts = []
    for txt, enc in decode_header(s):
        if isinstance(txt, bytes):
            try:
                parts.append(txt.decode(enc or "utf-8", errors="replace"))
            except Exception:
                parts.append(txt.decode("utf-8", errors="replace"))
        else:
            parts.append(txt)
    return "".join(parts)


def _body_snippet(msg, limit=300) -> str:
    try:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8",
                                              errors="replace").strip()[:limit]
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                return payload.decode(msg.get_content_charset() or "utf-8",
                                      errors="replace").strip()[:limit]
    except Exception:
        pass
    return ""


def read_inbox(limit: int = 5, unread_only: bool = False) -> dict:
    """Lee los últimos `limit` correos. Devuelve {ok, account, emails:[...], message}."""
    user, pwd = _creds()
    if not user or not pwd:
        return {"ok": False, "message": (
            "Falta configurar la lectura de email. Poné GMAIL_READ_USER y "
            "GMAIL_READ_APP_PASSWORD (App Password de esa cuenta) en el .env.")}
    try:
        M = imaplib.IMAP4_SSL(_IMAP_HOST, _IMAP_PORT)
        M.login(user, pwd)
        M.select("INBOX")
        crit = "UNSEEN" if unread_only else "ALL"
        typ, data = M.search(None, crit)
        ids = data[0].split()
        ids = ids[-limit:][::-1]  # los más recientes primero
        emails = []
        for eid in ids:
            typ, msg_data = M.fetch(eid, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            emails.append({
                "from": _decode(msg.get("From")),
                "subject": _decode(msg.get("Subject")) or "(sin asunto)",
                "date": msg.get("Date", ""),
                "snippet": _body_snippet(msg),
            })
        M.close()
        M.logout()
        return {"ok": True, "account": user, "emails": emails}
    except imaplib.IMAP4.error as e:
        return {"ok": False, "message": (
            f"IMAP rechazó el login ({str(e)[:80]}). ¿App Password válido e IMAP "
            f"habilitado en Gmail?")}
    except Exception as e:
        return {"ok": False, "message": f"No pude leer: {str(e)[:160]}"}
