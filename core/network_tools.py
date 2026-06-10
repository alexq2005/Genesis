"""
GENESIS Network Tools — Estado de red, conectividad, WiFi info.
Todas las funciones retornan datos reales del sistema.
"""
import subprocess
import socket
import urllib.request
import time
from typing import Optional


class NetworkTools:
    """Herramientas de red para diagnóstico y estado."""

    @staticmethod
    def check_connectivity() -> str:
        """Verifica conectividad a internet con múltiples checks."""
        results = []
        connected = False

        # Check 1: DNS resolution
        try:
            socket.setdefaulttimeout(5)
            ip = socket.gethostbyname("www.google.com")
            results.append(f"  ✅ DNS: google.com → {ip}")
            connected = True
        except socket.gaierror:
            results.append("  ❌ DNS: No se pudo resolver google.com")
        except Exception as e:
            results.append(f"  ❌ DNS: {e}")

        # Check 2: HTTP connection
        try:
            start = time.time()
            req = urllib.request.Request("http://www.google.com", method="HEAD")
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency = int((time.time() - start) * 1000)
                results.append(f"  ✅ HTTP: google.com respondió en {latency}ms")
                connected = True
        except Exception:
            results.append("  ❌ HTTP: No hay respuesta de google.com")

        # Check 3: HTTPS
        try:
            start = time.time()
            req = urllib.request.Request("https://www.cloudflare.com/cdn-cgi/trace", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency = int((time.time() - start) * 1000)
                body = resp.read().decode("utf-8", errors="replace")
                # Extraer IP del response de Cloudflare
                ip_line = [l for l in body.split("\n") if l.startswith("ip=")]
                public_ip = ip_line[0].split("=")[1] if ip_line else "?"
                results.append(f"  ✅ HTTPS: Cloudflare en {latency}ms (IP pública: {public_ip})")
                connected = True
        except Exception:
            results.append("  ❌ HTTPS: Sin acceso seguro")

        status = "🟢 **CONECTADO**" if connected else "🔴 **SIN CONEXIÓN**"
        header = f"🌐 Estado de Red: {status}\n"
        return header + "\n".join(results)

    @staticmethod
    def get_wifi_info() -> str:
        """Obtiene información de la conexión WiFi actual (Windows)."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            if result.returncode != 0 or "no hay" in result.stdout.lower():
                return "📶 No hay interfaz WiFi activa o no estás conectado por WiFi."

            lines = result.stdout.strip().split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().lower()
                    val = parts[1].strip()
                    if "ssid" in key and "bssid" not in key:
                        info["ssid"] = val
                    elif "señal" in key or "signal" in key:
                        info["signal"] = val
                    elif "velocidad" in key or "speed" in key or "receive rate" in key:
                        info["speed"] = val
                    elif "canal" in key or "channel" in key:
                        info["channel"] = val
                    elif "autenticación" in key or "authentication" in key:
                        info["auth"] = val
                    elif "banda" in key or "radio" in key:
                        info["band"] = val

            if not info:
                return "📶 No se pudo obtener info WiFi."

            output = ["📶 **CONEXIÓN WiFi**\n"]
            if "ssid" in info:
                output.append(f"  🔗 Red: **{info['ssid']}**")
            if "signal" in info:
                output.append(f"  📊 Señal: {info['signal']}")
            if "speed" in info:
                output.append(f"  ⚡ Velocidad: {info['speed']}")
            if "channel" in info:
                output.append(f"  📡 Canal: {info['channel']}")
            if "band" in info:
                output.append(f"  📻 Banda: {info['band']}")
            if "auth" in info:
                output.append(f"  🔒 Seguridad: {info['auth']}")

            return "\n".join(output)

        except Exception as e:
            return f"📶 Error obteniendo info WiFi: {e}"

    @staticmethod
    def ping(host: str = "8.8.8.8", count: int = 4) -> str:
        """Hace ping a un host y muestra latencia."""
        try:
            result = subprocess.run(
                ["ping", "-n", str(count), host],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace"
            )
            output = result.stdout.strip()

            # Extraer estadísticas
            lines = output.split("\n")
            stats_lines = [l.strip() for l in lines if any(k in l.lower() for k in
                          ["media", "average", "mínimo", "minimum", "perdidos", "lost", "promedio"])]

            summary = [f"🏓 **PING** a {host} ({count} paquetes)\n"]

            # Buscar línea de pérdida
            for line in lines:
                low = line.lower()
                if "perdidos" in low or "lost" in low:
                    summary.append(f"  {line.strip()}")
                if ("media" in low or "average" in low or "promedio" in low) and "ms" in low:
                    summary.append(f"  {line.strip()}")
                if ("mínimo" in low or "minimum" in low) and "ms" in low:
                    summary.append(f"  {line.strip()}")

            if len(summary) == 1:
                # Si no encontró resumen, mostrar las últimas 4 líneas
                for line in lines[-4:]:
                    if line.strip():
                        summary.append(f"  {line.strip()}")

            return "\n".join(summary)

        except subprocess.TimeoutExpired:
            return f"🏓 Ping a {host}: **TIMEOUT** — el host no responde."
        except Exception as e:
            return f"🏓 Error en ping: {e}"

    @staticmethod
    def get_network_adapters() -> str:
        """Lista adaptadores de red con estado."""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-NetAdapter | Select-Object Name, Status, LinkSpeed, MediaType | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=10,
                encoding="utf-8", errors="replace"
            )
            if result.stdout.strip():
                return f"🔌 **ADAPTADORES DE RED**\n\n```\n{result.stdout.strip()}\n```"
            return "🔌 No se pudieron listar los adaptadores."
        except Exception as e:
            return f"🔌 Error: {e}"

    @staticmethod
    def speed_test_quick() -> str:
        """Test de velocidad rápido (descarga un archivo pequeño)."""
        try:
            # Descargar archivo de prueba de Cloudflare (100KB)
            url = "https://speed.cloudflare.com/__down?bytes=102400"
            start = time.time()
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            elapsed = time.time() - start

            bytes_downloaded = len(data)
            speed_mbps = (bytes_downloaded * 8) / (elapsed * 1_000_000)

            return (f"⚡ **TEST DE VELOCIDAD** (estimado)\n\n"
                    f"  📥 Descargados: {bytes_downloaded / 1024:.0f} KB\n"
                    f"  ⏱️ Tiempo: {elapsed:.2f}s\n"
                    f"  🚀 Velocidad: **{speed_mbps:.1f} Mbps** (estimado)\n\n"
                    f"  ℹ️ Test rápido con archivo pequeño. Para precisión, usá speedtest.net")

        except Exception as e:
            return f"⚡ No se pudo medir velocidad: {e}"


# Singleton
network_tools = NetworkTools()
