"""
GENESIS — Cambiar el dispositivo de SALIDA de audio por defecto (Windows).

Usa la interfaz COM no documentada IPolicyConfig (la misma que usa el panel de
sonido de Windows) vía comtypes — sin binarios externos ni dependencias nuevas.
Enumera las salidas con pycaw. 100% local.

El id de endpoint codifica el flujo: '{0.0.0.' = render (salida),
'{0.0.1.' = capture (entrada). Filtramos solo salidas activas.
"""
from ctypes import c_int
from ctypes.wintypes import LPCWSTR

import comtypes
from comtypes import GUID, HRESULT, STDMETHOD, IUnknown

_CLSID_PolicyConfigClient = GUID("{870af99c-171d-4f9e-af0d-e63df40c2bc9}")


class _IPolicyConfig(IUnknown):
    _iid_ = GUID("{f8679f50-850a-41cf-9c72-430f290290c8}")
    # Hay que declarar TODOS los métodos previos para que el offset de
    # SetDefaultEndpoint en la vtable sea correcto (aunque no los llamemos).
    _methods_ = [
        STDMETHOD(HRESULT, "GetMixFormat"),
        STDMETHOD(HRESULT, "GetDeviceFormat"),
        STDMETHOD(HRESULT, "ResetDeviceFormat"),
        STDMETHOD(HRESULT, "SetDeviceFormat"),
        STDMETHOD(HRESULT, "GetProcessingPeriod"),
        STDMETHOD(HRESULT, "SetProcessingPeriod"),
        STDMETHOD(HRESULT, "GetShareMode"),
        STDMETHOD(HRESULT, "SetShareMode"),
        STDMETHOD(HRESULT, "GetPropertyValue"),
        STDMETHOD(HRESULT, "SetPropertyValue"),
        STDMETHOD(HRESULT, "SetDefaultEndpoint", [LPCWSTR, c_int]),
        STDMETHOD(HRESULT, "SetEndpointVisibility"),
    ]


def list_outputs():
    """Salidas de audio (render) activas: [{name, id}]."""
    from pycaw.pycaw import AudioUtilities
    out = []
    for d in AudioUtilities.GetAllDevices():
        try:
            did = d.id or ""
            if not did.startswith("{0.0.0."):  # solo render (salida)
                continue
            if str(d.state) != "AudioDeviceState.Active":
                continue
            out.append({"name": d.FriendlyName, "id": did})
        except Exception:
            continue
    return out


def list_text():
    outs = list_outputs()
    if not outs:
        return "🔈 No hay salidas de audio activas."
    return "🔈 Salidas de audio disponibles:\n" + "\n".join(
        f"  • {d['name']}" for d in outs)


def _set_default(device_id):
    comtypes.CoInitialize()
    try:
        pc = comtypes.CoCreateInstance(
            _CLSID_PolicyConfigClient, interface=_IPolicyConfig,
            clsctx=comtypes.CLSCTX_ALL)
        for role in (0, 1, 2):  # eConsole, eMultimedia, eCommunications
            pc.SetDefaultEndpoint(device_id, role)
    finally:
        try:
            comtypes.CoUninitialize()
        except Exception:
            pass


def set_output(query):
    """Cambia la salida por defecto al dispositivo que coincida con `query`."""
    outs = list_outputs()
    if not outs:
        return "🔈 No encontré dispositivos de salida activos."
    q = (query or "").lower().strip()
    if not q:
        return list_text()
    matches = [d for d in outs if q in d["name"].lower()]
    # si me pasan la frase entera, buscar por tokens significativos (ignora
    # conectores/verbos para no matchear basura como "de" → "...de koshi")
    if not matches:
        stop = {"de", "la", "el", "los", "las", "en", "un", "una", "al", "por",
                "con", "como", "salida", "salidas", "audio", "sonido", "dispositivo",
                "dispositivos", "conecta", "conectate", "conectá", "cambia", "cambiá",
                "pone", "poné", "pon", "pasa", "pasá", "usa", "usá", "que", "qué",
                "del", "mi", "reproduce", "reproducí", "sonar", "suena"}
        for tok in q.split():
            if len(tok) < 3 or tok in stop:
                continue
            matches = [d for d in outs if tok in d["name"].lower()]
            if matches:
                break
    if not matches:
        nombres = ", ".join(d["name"] for d in outs)
        return f"🔈 No encontré una salida «{query}». Disponibles: {nombres}."
    if len(matches) > 1:
        nombres = " / ".join(d["name"] for d in matches)
        return (f"🔈 Hay varias salidas con «{query}»: {nombres}. "
                f"Decime cuál más específico (ej: «salida flip» o «salida tune»).")
    d = matches[0]
    try:
        _set_default(d["id"])
        return f"🔈 Salida de audio cambiada a **{d['name']}**."
    except Exception as e:
        return f"[ERROR] No pude cambiar la salida: {str(e)[:140]}"
