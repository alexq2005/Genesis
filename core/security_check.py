"""
GENESIS — Chequeo de seguridad del sistema (Windows).

Revisa el estado real de seguridad vía PowerShell (sin requerir admin):
Windows Defender / antivirus, protección en tiempo real, antigüedad de firmas,
último escaneo, Firewall (3 perfiles), UAC y actualizaciones pendientes.
Solo LECTURA — no cambia nada. 100% local.
"""
import subprocess

_PS = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]
try:
    _FLAGS = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
except Exception:
    _FLAGS = 0x08000000


def _ps(cmd, timeout=30):
    try:
        r = subprocess.run(_PS + [cmd], capture_output=True, text=True,
                           timeout=timeout, creationflags=_FLAGS)
        return (r.stdout or "").strip()
    except Exception:
        return ""


_SCRIPT = r"""
$o=[ordered]@{}
try{$m=Get-MpComputerStatus -ErrorAction Stop
 $o.AV=$m.AntivirusEnabled;$o.RT=$m.RealTimeProtectionEnabled
 $o.AS=$m.AntispywareEnabled;$o.SigAge=$m.AntivirusSignatureAge
 $o.Tamper=$m.IsTamperProtected}catch{$o.AV='NA'}
try{$fw=Get-NetFirewallProfile -ErrorAction Stop
 foreach($p in $fw){$o["FW_"+$p.Name]=$p.Enabled}}catch{$o.FW='NA'}
try{$u=(Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' -Name EnableLUA -ErrorAction Stop).EnableLUA
 $o.UAC=$u}catch{$o.UAC='NA'}
try{$s=New-Object -ComObject Microsoft.Update.Session
 $sr=$s.CreateUpdateSearcher();$r=$sr.Search("IsInstalled=0 and IsHidden=0")
 $o.Updates=$r.Updates.Count}catch{$o.Updates='NA'}
$o.GetEnumerator()|ForEach-Object{"$($_.Key)=$($_.Value)"}
"""


def _b(v):
    return str(v).strip().lower() in ("true", "1")


def check():
    """Devuelve un reporte 🛡️ del estado de seguridad del sistema."""
    out = _ps(_SCRIPT)
    if not out:
        return ("🛡️ No pude leer el estado de seguridad (PowerShell no respondió). "
                "Quizás Defender está reemplazado por otro antivirus.")
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            d[k.strip()] = v.strip()

    def mark(ok):
        return "🟢" if ok else "🔴"

    L = ["🛡️ **Estado de seguridad del sistema**", ""]
    # Antivirus / Defender
    if d.get("AV", "NA") != "NA":
        L.append(f"{mark(_b(d.get('AV')))} Antivirus: "
                 + ("activado" if _b(d.get("AV")) else "DESACTIVADO"))
        L.append(f"{mark(_b(d.get('RT')))} Protección en tiempo real: "
                 + ("activa" if _b(d.get("RT")) else "DESACTIVADA"))
        sig = d.get("SigAge", "NA")
        if sig.isdigit():
            L.append(f"{mark(int(sig) <= 7)} Firmas antivirus: hace {sig} día(s)"
                     + ("" if int(sig) <= 7 else " — conviene actualizar"))
        if _b(d.get("Tamper")):
            L.append("🟢 Protección antimanipulación: activa")
    else:
        L.append("⚠️ Defender no disponible (¿otro antivirus instalado?)")
    # Firewall
    fw = [(n[3:], _b(d[n])) for n in d if n.startswith("FW_")]
    if fw:
        on = sum(1 for _, e in fw if e)
        L.append(f"{mark(on == len(fw))} Firewall: {on}/{len(fw)} perfiles activos"
                 + ("" if on == len(fw) else " ("
                    + ", ".join(n for n, e in fw if not e) + " apagado)"))
    # UAC
    if d.get("UAC", "NA") != "NA":
        L.append(f"{mark(_b(d.get('UAC')))} Control de cuentas (UAC): "
                 + ("activo" if _b(d.get("UAC")) else "DESACTIVADO"))
    # Updates
    up = d.get("Updates", "NA")
    if up.isdigit():
        n = int(up)
        L.append(f"{mark(n == 0)} Actualizaciones pendientes: {n}"
                 + (" — al día" if n == 0 else " — conviene instalar"))

    # Resumen
    riesgos = [ln for ln in L if ln.startswith("🔴")]
    L.append("")
    if riesgos:
        L.append(f"⚠️ {len(riesgos)} punto(s) a revisar.")
    else:
        L.append("✅ Todo en orden: sin riesgos detectados.")
    return "\n".join(L)
