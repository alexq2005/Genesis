"""
GENESIS System Actions — Acciones rápidas del sistema operativo.
Limpieza, mantenimiento, atajos de productividad.
"""
import subprocess
import os
import shutil
import time
from pathlib import Path
from typing import Optional


class SystemActions:
    """Acciones rápidas del sistema operativo."""

    @staticmethod
    def clean_temp(max_items: int = 200, timeout_sec: float = 30.0) -> str:
        """Limpia archivos temporales del sistema.
        Limitado a max_items y timeout_sec para no bloquear."""
        cleaned = 0
        freed = 0
        errors = 0
        skipped = 0
        t0 = time.time()

        temp_dirs = [
            os.environ.get("TEMP", ""),
            os.environ.get("TMP", ""),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp"),
        ]
        # Deduplicar
        temp_dirs = list(set(d for d in temp_dirs if d and os.path.isdir(d)))

        for temp_dir in temp_dirs:
            try:
                items = os.listdir(temp_dir)
                for item in items:
                    # Timeout check
                    if time.time() - t0 > timeout_sec:
                        skipped += len(items) - (cleaned + errors)
                        break
                    # Max items check
                    if cleaned + errors >= max_items:
                        skipped += len(items) - (cleaned + errors)
                        break

                    item_path = os.path.join(temp_dir, item)
                    try:
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            os.remove(item_path)
                            cleaned += 1
                            freed += size
                        elif os.path.isdir(item_path):
                            # Borrar primero, estimar tamaño solo del nivel superior
                            try:
                                top_size = sum(
                                    os.path.getsize(os.path.join(item_path, f))
                                    for f in os.listdir(item_path)
                                    if os.path.isfile(os.path.join(item_path, f))
                                )
                            except (OSError, PermissionError):
                                top_size = 0
                            shutil.rmtree(item_path, ignore_errors=True)
                            cleaned += 1
                            freed += top_size
                    except (PermissionError, OSError):
                        errors += 1
            except Exception:
                continue

        freed_mb = freed / (1024 * 1024)
        elapsed = time.time() - t0
        result = (f"🧹 **LIMPIEZA TEMPORAL**\n\n"
                  f"  ✅ Eliminados: {cleaned} archivos/carpetas\n"
                  f"  💾 Liberados: ~{freed_mb:.1f} MB\n"
                  f"  ⚠️ No eliminados (en uso): {errors}\n"
                  f"  ⏱️ Tiempo: {elapsed:.1f}s")
        if skipped > 0:
            result += f"\n  ⏭️ Omitidos (límite): {skipped}"
        return result

    @staticmethod
    def flush_dns() -> str:
        """Limpia la cache DNS del sistema."""
        try:
            result = subprocess.run(
                ["ipconfig", "/flushdns"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            if "correctamente" in result.stdout.lower() or "successfully" in result.stdout.lower():
                return "🌐 Cache DNS limpiada correctamente."
            return f"🌐 DNS flush: {result.stdout.strip()}"
        except Exception as e:
            return f"🌐 Error limpiando DNS: {e}"

    @staticmethod
    def empty_recycle_bin() -> str:
        """Vacía la papelera de reciclaje."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Clear-RecycleBin -Force -ErrorAction SilentlyContinue; Write-Output 'OK'"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace"
            )
            if "OK" in result.stdout:
                return "🗑️ Papelera de reciclaje vaciada."
            return f"🗑️ {result.stdout.strip() or result.stderr.strip()}"
        except Exception as e:
            return f"🗑️ Error: {e}"

    @staticmethod
    def system_uptime() -> str:
        """Muestra hace cuánto está encendido el equipo."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime | "
                 "ForEach-Object { \"$($_.Days)d $($_.Hours)h $($_.Minutes)m\" }"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            uptime = result.stdout.strip()
            if uptime:
                return f"⏱️ **Uptime**: {uptime} encendido"
            return "⏱️ No se pudo obtener el uptime."
        except Exception as e:
            return f"⏱️ Error: {e}"

    @staticmethod
    def battery_status() -> str:
        """Estado de la batería (solo laptops)."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "$b = Get-CimInstance Win32_Battery; "
                 "if ($b) { \"$($b.EstimatedChargeRemaining)% - $($b.BatteryStatus)\" } "
                 "else { 'NO_BATTERY' }"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            output = result.stdout.strip()
            if "NO_BATTERY" in output:
                return "🔌 Este equipo no tiene batería (desktop)."

            status_map = {"1": "Descargando", "2": "Conectado (AC)",
                         "3": "Cargado", "4": "Baja", "5": "Crítica"}
            parts = output.split(" - ")
            pct = parts[0] if parts else "?"
            status_code = parts[1] if len(parts) > 1 else "?"
            status_text = status_map.get(status_code, status_code)

            return f"🔋 **Batería**: {pct} — {status_text}"
        except Exception as e:
            return f"🔋 Error: {e}"

    @staticmethod
    def lock_screen() -> str:
        """Bloquea la pantalla."""
        try:
            subprocess.Popen(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return "🔒 Pantalla bloqueada."
        except Exception as e:
            return f"🔒 Error: {e}"

    @staticmethod
    def open_settings(section: str = "") -> str:
        """Abre configuración de Windows."""
        settings_map = {
            "wifi": "ms-settings:network-wifi",
            "red": "ms-settings:network-wifi",
            "bluetooth": "ms-settings:bluetooth",
            "pantalla": "ms-settings:display",
            "sonido": "ms-settings:sound",
            "audio": "ms-settings:sound",
            "notificaciones": "ms-settings:notifications",
            "almacenamiento": "ms-settings:storagesense",
            "actualizaciones": "ms-settings:windowsupdate",
            "apps": "ms-settings:appsfeatures",
            "privacidad": "ms-settings:privacy",
            "hora": "ms-settings:dateandtime",
            "idioma": "ms-settings:regionlanguage",
            "personalización": "ms-settings:personalization",
            "fondo": "ms-settings:personalization-background",
            "energía": "ms-settings:powersleep",
            "": "ms-settings:",
        }
        uri = settings_map.get(section.lower().strip(), f"ms-settings:{section}")
        try:
            os.startfile(uri)
            name = section or "principal"
            return f"⚙️ Abriendo configuración: {name}"
        except Exception as e:
            return f"⚙️ Error abriendo configuración: {e}"

    @staticmethod
    def get_installed_apps_count() -> str:
        """Cuenta las aplicaciones instaladas."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
                 "Where-Object { $_.DisplayName } | Measure-Object).Count"],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace"
            )
            count = result.stdout.strip()
            return f"📦 Aplicaciones instaladas: **{count}**"
        except Exception as e:
            return f"📦 Error: {e}"


# Singleton
system_actions = SystemActions()
