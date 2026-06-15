"""
GENESIS Window Manager — Control de ventanas del sistema operativo.
Mover, redimensionar, snap, tile, minimizar, maximizar ventanas por voz.
Usa PowerShell + .NET para manipulación nativa sin dependencias externas.
"""
import subprocess
import re
import ctypes
from ctypes import wintypes
from typing import Optional

_U32 = ctypes.windll.user32


def _wm_win_list():
    """[(hwnd, título)] de ventanas top-level VISIBLES con título (ctypes, in-process)."""
    out = []
    EP = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def _cb(h, _l):
        try:
            if _U32.IsWindowVisible(h):
                n = _U32.GetWindowTextLengthW(h)
                if n > 0:
                    b = ctypes.create_unicode_buffer(n + 1)
                    _U32.GetWindowTextW(h, b, n + 1)
                    out.append((h, b.value))
        except Exception:
            pass
        return True
    try:
        _U32.EnumWindows(EP(_cb), 0)
    except Exception:
        pass
    return out


def _wm_hwnd_by_name(name):
    """hwnd de la 1ª ventana cuyo título CONTIENE `name` (case-insensitive)."""
    nl = (name or "").lower()
    for h, t in _wm_win_list():
        if nl in t.lower():
            return h, t
    return None, None


def _wm_title(h):
    try:
        n = _U32.GetWindowTextLengthW(h)
        b = ctypes.create_unicode_buffer(n + 1)
        _U32.GetWindowTextW(h, b, n + 1)
        return b.value
    except Exception:
        return ""


class WindowManager:
    """Control de ventanas del escritorio via PowerShell/.NET."""

    # ── Listar ventanas ───────────────────────────────
    @staticmethod
    def list_windows() -> str:
        """Lista todas las ventanas visibles con su título y posición."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
                 "Select-Object @{N='PID';E={$_.Id}}, "
                 "@{N='Name';E={$_.ProcessName}}, "
                 "@{N='Title';E={$_.MainWindowTitle}} | "
                 "Format-Table -AutoSize | Out-String -Width 200"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            output = result.stdout.strip()
            if not output:
                return "🪟 No hay ventanas visibles abiertas."

            lines = [l for l in output.splitlines() if l.strip()]
            count = max(0, len(lines) - 2)  # header + separator
            return f"🪟 **VENTANAS ABIERTAS** ({count})\n\n```\n{output}\n```"
        except Exception as e:
            return f"🪟 Error listando ventanas: {e}"

    # ── Operaciones con ventanas ──────────────────────
    @staticmethod
    def _run_window_ps(script: str) -> str:
        """Ejecuta un script PowerShell para manipular ventanas."""
        # Preámbulo: cargar la API de Windows
        preamble = """
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
    [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int W, int H, bool repaint);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsZoomed(IntPtr hWnd);
}
"@
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", preamble + script],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            return result.stdout.strip() or result.stderr.strip() or "OK"
        except subprocess.TimeoutExpired:
            return "Error: timeout"
        except Exception as e:
            return str(e)

    @staticmethod
    def _find_window_script(name: str) -> str:
        """Genera script PS para encontrar ventana por nombre parcial.
        Busca primero por título, luego por nombre de proceso como fallback."""
        safe = name.replace("'", "''")
        return (
            f"$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{safe}*' -and "
            f"$_.MainWindowHandle -ne 0 }} | Select-Object -First 1\n"
            f"if (-not $p) {{ $p = Get-Process | Where-Object {{ $_.ProcessName -like '*{safe}*' -and "
            f"$_.MainWindowHandle -ne 0 }} | Select-Object -First 1 }}\n"
            f"if (-not $p) {{ Write-Output 'NOT_FOUND'; exit }}\n"
            f"$h = $p.MainWindowHandle\n"
        )

    @staticmethod
    def _get_screen_size_script() -> str:
        """Script PS para obtener resolución de pantalla."""
        return ("[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null\n"
                "$scr = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea\n"
                "$sw = $scr.Width; $sh = $scr.Height; $sx = $scr.X; $sy = $scr.Y\n")

    # ── Snap ventanas ─────────────────────────────────
    def snap_left(self, window_name: str) -> str:
        """Ajusta ventana a la mitad izquierda de la pantalla."""
        script = (self._find_window_script(window_name) +
                  self._get_screen_size_script() +
                  "[WinAPI]::ShowWindow($h, 1) | Out-Null\n"  # SW_NORMAL
                  "[WinAPI]::MoveWindow($h, $sx, $sy, [int]($sw/2), $sh, $true) | Out-Null\n"
                  "[WinAPI]::SetForegroundWindow($h) | Out-Null\n"
                  "Write-Output \"SNAPPED_LEFT:$($p.ProcessName)\"")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** ajustada a la mitad izquierda ◀️"

    def snap_right(self, window_name: str) -> str:
        """Ajusta ventana a la mitad derecha de la pantalla."""
        script = (self._find_window_script(window_name) +
                  self._get_screen_size_script() +
                  "[WinAPI]::ShowWindow($h, 1) | Out-Null\n"
                  "[WinAPI]::MoveWindow($h, [int]($sx + $sw/2), $sy, [int]($sw/2), $sh, $true) | Out-Null\n"
                  "[WinAPI]::SetForegroundWindow($h) | Out-Null\n"
                  "Write-Output \"SNAPPED_RIGHT:$($p.ProcessName)\"")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** ajustada a la mitad derecha ▶️"

    def snap_top(self, window_name: str) -> str:
        """Ajusta ventana a la mitad superior."""
        script = (self._find_window_script(window_name) +
                  self._get_screen_size_script() +
                  "[WinAPI]::ShowWindow($h, 1) | Out-Null\n"
                  "[WinAPI]::MoveWindow($h, $sx, $sy, $sw, [int]($sh/2), $true) | Out-Null\n"
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** ajustada a la mitad superior ▲"

    def snap_bottom(self, window_name: str) -> str:
        """Ajusta ventana a la mitad inferior."""
        script = (self._find_window_script(window_name) +
                  self._get_screen_size_script() +
                  "[WinAPI]::ShowWindow($h, 1) | Out-Null\n"
                  "[WinAPI]::MoveWindow($h, $sx, [int]($sy + $sh/2), $sw, [int]($sh/2), $true) | Out-Null\n"
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** ajustada a la mitad inferior ▼"

    def maximize(self, window_name: str) -> str:
        """Maximiza una ventana."""
        script = (self._find_window_script(window_name) +
                  "[WinAPI]::ShowWindow($h, 3) | Out-Null\n"  # SW_MAXIMIZE
                  "[WinAPI]::SetForegroundWindow($h) | Out-Null\n"
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** maximizada ⬜"

    def minimize(self, window_name: str) -> str:
        """Minimiza una ventana."""
        script = (self._find_window_script(window_name) +
                  "[WinAPI]::ShowWindow($h, 6) | Out-Null\n"  # SW_MINIMIZE
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** minimizada ➖"

    def restore(self, window_name: str) -> str:
        """Restaura una ventana minimizada."""
        script = (self._find_window_script(window_name) +
                  "[WinAPI]::ShowWindow($h, 9) | Out-Null\n"  # SW_RESTORE
                  "[WinAPI]::SetForegroundWindow($h) | Out-Null\n"
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** restaurada 🔳"

    def focus(self, window_name: str) -> str:
        """Trae una ventana al frente."""
        script = (self._find_window_script(window_name) +
                  "[WinAPI]::ShowWindow($h, 9) | Out-Null\n"
                  "[WinAPI]::SetForegroundWindow($h) | Out-Null\n"
                  "Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** traída al frente 🔝"

    def minimize_all(self) -> str:
        """Minimiza todas las ventanas (mostrar escritorio)."""
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(New-Object -ComObject Shell.Application).MinimizeAll()"],
                capture_output=True, timeout=5
            )
            return "🪟 Todas las ventanas minimizadas — escritorio visible 🖥️"
        except Exception as e:
            return f"🪟 Error: {e}"

    def tile_two(self, left_name: str, right_name: str) -> str:
        """Pone dos ventanas lado a lado (50/50)."""
        r1 = self.snap_left(left_name)
        r2 = self.snap_right(right_name)
        if "No encontré" in r1 or "No encontré" in r2:
            return f"{r1}\n{r2}"
        return f"🪟 **Tile completado:**\n  ◀️ {left_name} (izquierda)\n  ▶️ {right_name} (derecha)"

    def move_window(self, window_name: str, x: int, y: int, w: int = 0, h: int = 0) -> str:
        """Mueve una ventana a coordenadas específicas."""
        if w > 0 and h > 0:
            size_cmd = f"[WinAPI]::MoveWindow($h, {x}, {y}, {w}, {h}, $true) | Out-Null"
        else:
            size_cmd = (f"$rect = New-Object RECT\n"
                        f"[WinAPI]::MoveWindow($h, {x}, {y}, 800, 600, $true) | Out-Null")
        script = (self._find_window_script(window_name) +
                  f"[WinAPI]::ShowWindow($h, 1) | Out-Null\n"
                  f"{size_cmd}\n"
                  f"Write-Output 'OK'")
        result = self._run_window_ps(script)
        if "NOT_FOUND" in result:
            return f"🪟 No encontré una ventana con '{window_name}'."
        return f"🪟 **{window_name}** movida a ({x}, {y})"

    def move_to_screen(self, screen: int = 2, window_name: str = None) -> str:
        """Mueve una ventana a otra pantalla, ocupándola completa. Si no se da
        `window_name`, mueve la ventana en PRIMER PLANO (lo que estás mirando).
        Usa ctypes IN-PROCESS → INSTANTÁNEO. (Antes lanzaba PowerShell+Add-Type
        que recompila C# en cada llamada ~2-4s → parecía que «no se movía».)"""
        try:
            from core.system_control import get_monitors
            mons = get_monitors()
        except Exception:
            mons = []
        idx = screen - 1
        if idx < 0 or idx >= len(mons):
            return f"🪟 No detecto la pantalla {screen} (hay {len(mons)} monitor/es)."
        x, y, w, h = mons[idx]
        try:
            _U32.SetProcessDPIAware()   # coords físicas consistentes con get_monitors
        except Exception:
            pass
        if window_name:
            hwnd, title = _wm_hwnd_by_name(window_name)
            if not hwnd:
                return f"🪟 No encontré una ventana con '{window_name}'."
        else:
            hwnd = _U32.GetForegroundWindow()
            title = _wm_title(hwnd)
            _tl = title.lower()
            _skip = ("powershell", "system32", "claude", "genesis", "jarvis",
                     "cmd.exe", "command prompt", "símbolo del sistema",
                     "windows terminal", "visual studio code", "consola",
                     "conhost", "lexus ai")
            if any(k in _tl for k in _skip) or not title.strip():
                return ("🪟 La ventana en primer plano es el chat/sistema, no tu "
                        "película. Para moverla: hacé **clic en la peli** y después "
                        "decí «mové esto a la otra pantalla», o nombrá la app: "
                        "«mové grass/chrome a la pantalla 2».")
        try:
            _U32.ShowWindow(hwnd, 9)    # SW_RESTORE: saca de maximizado para reposicionar
            _U32.MoveWindow(hwnd, int(x), int(y), int(w), int(h), True)
        except Exception as e:
            return f"🪟 Error moviendo la ventana: {str(e)[:80]}"
        return f"🪟 Moví «{title[:45]}» a la pantalla {screen} (completa)."

    def close_window(self, window_name: str) -> str:
        """Cierra una ventana por nombre."""
        safe = window_name.replace("'", "''")
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"$p = Get-Process | Where-Object {{ $_.MainWindowTitle -like '*{safe}*' }} | "
                 f"Select-Object -First 1; "
                 f"if ($p) {{ $p.CloseMainWindow() | Out-Null; Write-Output 'CLOSED' }} "
                 f"else {{ Write-Output 'NOT_FOUND' }}"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            if "NOT_FOUND" in result.stdout:
                return f"🪟 No encontré una ventana con '{window_name}'."
            return f"🪟 **{window_name}** cerrada ❌"
        except Exception as e:
            return f"🪟 Error: {e}"

    # ── Info de pantalla ──────────────────────────────
    @staticmethod
    def screen_info() -> str:
        """Muestra información de los monitores."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                 "$screens = [System.Windows.Forms.Screen]::AllScreens; "
                 "foreach ($s in $screens) { "
                 "  $b = $s.Bounds; $w = $s.WorkingArea; "
                 "  Write-Output \"$($s.DeviceName) | ${($b.Width)}x${($b.Height)} | Primary: $($s.Primary)\" "
                 "}"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            output = result.stdout.strip()
            return f"🖥️ **MONITORES:**\n\n{output}"
        except Exception as e:
            return f"🖥️ Error: {e}"

    # ── Parser de comandos ────────────────────────────
    def parse_and_execute(self, text: str) -> str:
        """Parsea lenguaje natural y ejecuta la operación de ventana."""
        t = text.lower().strip()

        # "pon X a la izquierda y Y a la derecha"
        m = re.search(r'pon\w*\s+(.+?)\s+a la izquierda\s+y\s+(.+?)\s+a la derecha', t)
        if m:
            return self.tile_two(m.group(1).strip(), m.group(2).strip())

        # "pon X a la izquierda" / "snap X left"
        m = re.search(r'(?:pon\w*|mueve|mover|snap)\s+(.+?)\s+(?:a la izquierda|izquierda|left)', t)
        if m:
            return self.snap_left(m.group(1).strip())

        m = re.search(r'(?:pon\w*|mueve|mover|snap)\s+(.+?)\s+(?:a la derecha|derecha|right)', t)
        if m:
            return self.snap_right(m.group(1).strip())

        # "maximiza X"
        m = re.search(r'(?:maximiza|maximizar|maximize)\s+(.+)', t)
        if m:
            return self.maximize(m.group(1).strip())

        # "minimiza X"
        m = re.search(r'(?:minimiza|minimizar|minimize)\s+(.+)', t)
        if m:
            name = m.group(1).strip()
            if name in ("todo", "todas", "all", "todas las ventanas"):
                return self.minimize_all()
            return self.minimize(name)

        # "restaura X"
        m = re.search(r'(?:restaura|restaurar|restore)\s+(.+)', t)
        if m:
            return self.restore(m.group(1).strip())

        # "enfoca X" / "cambia a X" / "ve a X"
        m = re.search(r'(?:enfoca|enfocar|focus|cambia a|cambiar a|ve a|ir a|muestra)\s+(.+)', t)
        if m:
            return self.focus(m.group(1).strip())

        return ("🪟 No entendí el comando de ventana. Ejemplos:\n"
                "  • `pon Chrome a la izquierda`\n"
                "  • `pon Chrome a la izquierda y VS Code a la derecha`\n"
                "  • `maximiza Discord`\n"
                "  • `minimiza todo`\n"
                "  • `cambia a Spotify`")


# Singleton
window_manager = WindowManager()
