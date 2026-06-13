"""
GENESIS — Gestión de conexiones/periféricos: WiFi, Bluetooth, USB.

Vía netsh + PowerShell (sin dependencias). Algunas acciones (toggle de adaptador
WiFi/BT) pueden requerir permisos de administrador en Windows.
"""
import subprocess


def _ps(cmd: str, timeout: int = 12) -> str:
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace")
        return (r.stdout or "") + (("\n" + r.stderr) if r.returncode != 0 and r.stderr else "")
    except Exception as e:
        return f"[ERROR] {e}"


def _netsh(args: list, timeout: int = 12) -> str:
    try:
        r = subprocess.run(["netsh"] + args, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        return r.stdout or r.stderr or ""
    except Exception as e:
        return f"[ERROR] {e}"


# =============================================================== WiFi ===
def wifi_list() -> str:
    """Redes WiFi disponibles (SSID + señal)."""
    out = _netsh(["wlan", "show", "networks", "mode=bssid"])
    import re
    nets = []
    ssid = None
    for line in out.splitlines():
        m = re.match(r"\s*SSID\s+\d+\s*:\s*(.+)", line)
        if m:
            ssid = m.group(1).strip()
        ms = re.match(r"\s*Se[ñn]al\s*:\s*(\d+%)", line) or re.match(r"\s*Signal\s*:\s*(\d+%)", line)
        if ms and ssid:
            nets.append((ssid, ms.group(1)))
            ssid = None
    if not nets:
        if "no hay" in out.lower() or "not" in out.lower() or "no interface" in out.lower():
            return "📶 No detecté redes WiFi (¿adaptador WiFi activo?)."
        # algunas redes pueden no traer señal parseable
        ssids = re.findall(r"SSID\s+\d+\s*:\s*(.+)", out)
        if ssids:
            return "📶 Redes WiFi:\n" + "\n".join("  • " + s.strip() for s in ssids if s.strip())
        return "📶 No encontré redes WiFi disponibles."
    nets.sort(key=lambda x: int(x[1].rstrip("%")), reverse=True)
    return "📶 Redes WiFi:\n" + "\n".join(f"  • {s}  ({sig})" for s, sig in nets)


def wifi_connect(ssid: str) -> str:
    """Conecta a una red WiFi GUARDADA (perfil existente)."""
    out = _netsh(["wlan", "connect", f"name={ssid}"])
    if "se complet" in out.lower() or "completed successfully" in out.lower():
        return f"📶 Conectando a «{ssid}»…"
    if "no se encuentra" in out.lower() or "is not found" in out.lower():
        return (f"📶 No tengo un perfil guardado de «{ssid}». Conectate manual la "
                f"primera vez (para guardar la contraseña) y después yo la reconecto.")
    return f"📶 {out.strip()[:160] or ('Intenté conectar a ' + ssid)}"


def wifi_toggle(on: bool) -> str:
    """Enciende/apaga el adaptador WiFi. (Puede requerir admin.)"""
    state = "enabled" if on else "disabled"
    out = _netsh(["interface", "set", "interface", "Wi-Fi", f"admin={state}"])
    if not out.strip() or "ok" in out.lower():
        return f"📶 WiFi {'encendido' if on else 'apagado'}."
    if "requ" in out.lower() and "admin" in out.lower() or "elevation" in out.lower():
        return "📶 Necesito permisos de administrador para apagar/encender el WiFi."
    return f"📶 {out.strip()[:160]}"


# ========================================================== Bluetooth ===
def bluetooth_list() -> str:
    """Dispositivos Bluetooth emparejados/presentes."""
    out = _ps("Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction SilentlyContinue | "
              "Where-Object { $_.FriendlyName } | Select-Object -ExpandProperty FriendlyName")
    names = [n.strip() for n in out.splitlines() if n.strip() and not n.startswith("[ERROR]")]
    # filtrar adaptadores genéricos para mostrar dispositivos reales
    devs = [n for n in names if not any(k in n.lower() for k in
            ("enumerator", "enumerador", "adapter", "adaptador", "radio",
             "controller", "controlador", "rfcomm", "service", "microsoft",
             "intel(r) wireless"))]
    # dedup conservando orden (a veces hay duplicados por perfiles AVRCP)
    seen, uniq = set(), []
    for n in (devs or names):
        base = n.split(" Transporte")[0].strip()
        if base.lower() not in seen:
            seen.add(base.lower())
            uniq.append(base)
    show = uniq
    if not show:
        return "🔵 No detecté dispositivos Bluetooth (¿BT encendido?)."
    return "🔵 Bluetooth:\n" + "\n".join("  • " + n for n in show[:20])


def bluetooth_toggle(on: bool) -> str:
    """Enciende/apaga el Bluetooth (WinRT Radio). Puede requerir confirmación de Windows."""
    val = "On" if on else "Off"
    # WinRT Radios API vía PowerShell
    cmd = (
        "$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | "
        "? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and "
        "$_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' });"
        "Function Await($o,$t){$m=$asTask.MakeGenericMethod($t);$tk=$m.Invoke($null,@($o));"
        "$tk.Wait();$tk.Result};"
        "[Windows.Devices.Radios.Radio,Windows.System.Devices,ContentType=WindowsRuntime]|Out-Null;"
        "[Windows.Devices.Radios.RadioAccessStatus,Windows.System.Devices,ContentType=WindowsRuntime]|Out-Null;"
        "Await ([Windows.Devices.Radios.Radio]::RequestAccessAsync()) "
        "([Windows.Devices.Radios.RadioAccessStatus])|Out-Null;"
        "$radios=Await ([Windows.Devices.Radios.Radio]::GetRadiosAsync()) "
        "([System.Collections.Generic.IReadOnlyList[Windows.Devices.Radios.Radio]]);"
        "$bt=$radios|?{$_.Kind -eq 'Bluetooth'};"
        f"if($bt){{Await ($bt.SetStateAsync('{val}')) ([Windows.Devices.Radios.RadioAccessStatus])|Out-Null;"
        "'OK'}else{'NO_BT'}")
    out = _ps(cmd, timeout=20)
    if "OK" in out:
        return f"🔵 Bluetooth {'encendido' if on else 'apagado'}."
    if "NO_BT" in out:
        return "🔵 No encontré radio Bluetooth en este equipo."
    return f"🔵 No pude {'encender' if on else 'apagar'} el Bluetooth (puede requerir permisos)."


# ================================================================ USB ===
def usb_list() -> str:
    """Discos/dispositivos USB conectados."""
    drives = _ps("Get-Volume | Where-Object {$_.DriveType -eq 'Removable' -and $_.DriveLetter} | "
                 "ForEach-Object { \"$($_.DriveLetter): $($_.FileSystemLabel) "
                 "[$([math]::Round($_.Size/1GB,1)) GB]\" }")
    dl = [d.strip() for d in drives.splitlines() if d.strip() and not d.startswith("[ERROR]")]
    out = ["🔌 USB conectados:"]
    if dl:
        out.append("  Unidades:")
        out += ["    • " + d for d in dl]
    if len(out) == 1:
        return "🔌 No detecté unidades USB conectadas."
    return "\n".join(out)


def usb_eject(drive: str) -> str:
    """Expulsa de forma segura una unidad USB (ej: 'E' o 'E:')."""
    letter = drive.strip().rstrip(":").upper()[:1]
    if not letter.isalpha():
        return "🔌 Decime la letra de la unidad (ej: E)."
    cmd = (f"$sh=New-Object -comObject Shell.Application;"
           f"$sh.Namespace(17).ParseName('{letter}:').InvokeVerb('Eject')")
    _ps(cmd, timeout=10)
    return f"🔌 Expulsé la unidad {letter}: (ya la podés sacar)."
