"""
GENESIS Weather Module — Datos meteorológicos en tiempo real.
Usa wttr.in (gratuito, sin API key) + fallback a Open-Meteo.
"""
import json
import threading
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional


class WeatherService:
    """Obtiene datos del clima en tiempo real."""

    WTTR_URL = "https://wttr.in/{location}?format=j1"
    OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
    GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=es"

    def __init__(self):
        self._cache: dict = {}
        self._cache_ttl = 600  # 10 minutos
        self._lock = threading.RLock()
        self._default_location = ""   # vacío → geolocaliza por IP real
        self._geo_cache = None        # (lat, lon, ciudad) cacheado por sesión

    def _geolocate_ip(self):
        """Geolocaliza por la IP pública real del usuario (sin API key).

        Devuelve 'lat,lon' (preciso para wttr.in) o None. Cachea por sesión.
        Antes el clima dependía del nearest_area de wttr.in (devolvía barrios
        raros como 'Villa Crespo'); ahora parte de la ubicación REAL.
        """
        if self._geo_cache:
            return self._geo_cache
        import urllib.request, json as _json
        servicios = [
            "https://ipapi.co/json/",
            "http://ip-api.com/json/",
        ]
        for url in servicios:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=6) as r:
                    d = _json.loads(r.read().decode("utf-8", "replace"))
                lat = d.get("latitude") or d.get("lat")
                lon = d.get("longitude") or d.get("lon")
                ciudad = d.get("city") or d.get("regionName") or d.get("region") or ""
                if lat and lon:
                    self._geo_cache = f"{lat},{lon}"
                    return self._geo_cache
                if ciudad:
                    self._geo_cache = ciudad
                    return self._geo_cache
            except Exception:
                continue
        return None

    # ── Clima actual ──────────────────────────────────
    def current(self, location: str = "") -> str:
        """Obtiene el clima actual de una ubicación."""
        # Sin ubicación explícita → geolocalizar por IP real, luego default.
        location = (location or "").strip()
        if not location:
            location = self._geolocate_ip() or self._default_location or "Buenos Aires"
        if not location:
            return "🌤️ Necesito una ubicación. Ejemplo: 'clima Buenos Aires'"

        # Verificar cache
        cache_key = f"current:{location.lower()}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        # Intentar wttr.in primero
        result = self._fetch_wttr(location)
        if not result:
            # Fallback a Open-Meteo
            result = self._fetch_open_meteo(location)

        if result:
            self._set_cache(cache_key, result)
            return result

        return f"🌤️ No pude obtener el clima para '{location}'. Verificá la conexión a internet."

    # ── Pronóstico extendido ──────────────────────────
    def forecast(self, location: str = "", days: int = 3) -> str:
        """Pronóstico de varios días."""
        location = (location or "").strip()
        if not location:
            location = self._geolocate_ip() or self._default_location or "Buenos Aires"
        if not location:
            return "🌤️ Necesito una ubicación."

        days = min(max(days, 1), 7)

        cache_key = f"forecast:{location.lower()}:{days}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        result = self._fetch_wttr_forecast(location, days)
        if not result:
            result = self._fetch_open_meteo_forecast(location, days)

        if result:
            self._set_cache(cache_key, result)
            return result

        return f"🌤️ No pude obtener el pronóstico para '{location}'."

    # ── wttr.in ───────────────────────────────────────
    def _fetch_wttr(self, location: str) -> Optional[str]:
        """Obtiene clima actual de wttr.in."""
        try:
            url = self.WTTR_URL.format(location=urllib.parse.quote(location))
            req = urllib.request.Request(url, headers={
                "User-Agent": "Genesis/5.9 (Weather Module)",
                "Accept-Language": "es"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            current = data.get("current_condition", [{}])[0]
            area = data.get("nearest_area", [{}])[0]

            city = area.get("areaName", [{}])[0].get("value", location)
            country = area.get("country", [{}])[0].get("value", "")
            region = area.get("region", [{}])[0].get("value", "")

            temp_c = current.get("temp_C", "?")
            feels_like = current.get("FeelsLikeC", "?")
            humidity = current.get("humidity", "?")
            wind_kmph = current.get("windspeedKmph", "?")
            wind_dir = current.get("winddir16Point", "")
            pressure = current.get("pressure", "?")
            visibility = current.get("visibility", "?")
            uv_index = current.get("uvIndex", "?")
            cloud_cover = current.get("cloudcover", "?")
            precip_mm = current.get("precipMM", "0")

            # Descripción en español
            desc_es = current.get("lang_es", [{}])[0].get("value", "")
            if not desc_es:
                desc_es = current.get("weatherDesc", [{}])[0].get("value", "")

            # Emoji según condición
            weather_code = int(current.get("weatherCode", 0))
            emoji = self._weather_emoji(weather_code)

            # Tono casual argentino: una o dos frases naturales, no un reporte.
            lugar = city + (f", {region}" if region and region != city else "")
            try:
                t = float(temp_c); fl = float(feels_like); h = float(humidity); w = float(wind_kmph)
            except (TypeError, ValueError):
                t = fl = h = w = 0
            # Comentario según temperatura
            if t <= 8: tip = "Abrigate bien que está fresco 🧥"
            elif t <= 15: tip = "Llevá una campera por las dudas"
            elif t <= 24: tip = "Lindo clima, ni frío ni calor"
            elif t <= 30: tip = "Hace calorcito, andá liviano"
            else: tip = "Un horno — hidratate 💧"
            extra = ""
            if abs(fl - t) >= 3:
                extra += f" (se siente como {feels_like}°)"
            detalle = []
            if w >= 25: detalle.append(f"viento fuerte ({wind_kmph} km/h)")
            elif w >= 1: detalle.append(f"viento {wind_kmph} km/h")
            if h >= 80: detalle.append(f"húmedo ({humidity}%)")
            if float(precip_mm or 0) > 0: detalle.append(f"lluvia {precip_mm} mm")
            cola = (". " + ", ".join(detalle).capitalize() + ".") if detalle else "."
            return (f"{emoji} En {lugar} hay {temp_c}°C{extra} y está {desc_es.lower()}{cola} "
                    f"{tip}.")

        except Exception:
            return None

    def _fetch_wttr_forecast(self, location: str, days: int) -> Optional[str]:
        """Obtiene pronóstico de wttr.in."""
        try:
            url = self.WTTR_URL.format(location=urllib.parse.quote(location))
            req = urllib.request.Request(url, headers={
                "User-Agent": "Genesis/5.9 (Weather Module)",
                "Accept-Language": "es"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            area = data.get("nearest_area", [{}])[0]
            city = area.get("areaName", [{}])[0].get("value", location)
            weather_list = data.get("weather", [])

            lines = [f"📅 **PRONÓSTICO {days} DÍAS — {city.upper()}**\n"]

            for i, day in enumerate(weather_list[:days]):
                date = day.get("date", "")
                max_t = day.get("maxtempC", "?")
                min_t = day.get("mintempC", "?")
                avg_t = day.get("avgtempC", "?")
                sun_hours = day.get("sunHour", "?")
                total_snow = day.get("totalSnow_cm", "0")

                # Descripción promedio del día
                hourly = day.get("hourly", [])
                mid_day = hourly[len(hourly)//2] if hourly else {}
                desc = mid_day.get("lang_es", [{}])[0].get("value", "")
                if not desc:
                    desc = mid_day.get("weatherDesc", [{}])[0].get("value", "")
                code = int(mid_day.get("weatherCode", 0))
                emoji = self._weather_emoji(code)
                humidity = mid_day.get("humidity", "?")
                wind = mid_day.get("windspeedKmph", "?")
                rain_chance = mid_day.get("chanceofrain", "?")

                # Nombre del día
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
                    day_name = day_names[dt.weekday()]
                    date_fmt = f"{day_name} {dt.day}/{dt.month}"
                except Exception:
                    date_fmt = date

                lines.append(f"  {emoji} **{date_fmt}**: {min_t}°C → {max_t}°C | {desc}")
                lines.append(f"     💧 Humedad: {humidity}% | 💨 Viento: {wind} km/h | 🌧️ Lluvia: {rain_chance}%")

            lines.append(f"\n  ⏰ Actualizado: {datetime.now().strftime('%H:%M:%S')}")
            return "\n".join(lines)

        except Exception:
            return None

    # ── Open-Meteo (fallback) ─────────────────────────
    def _fetch_open_meteo(self, location: str) -> Optional[str]:
        """Fallback: Open-Meteo (sin API key)."""
        try:
            # Geocodificar
            geo_url = self.GEOCODE_URL.format(location=urllib.parse.quote(location))
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Genesis/5.9"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                geo_data = json.loads(resp.read().decode("utf-8"))

            results = geo_data.get("results", [])
            if not results:
                return None

            place = results[0]
            lat = place["latitude"]
            lon = place["longitude"]
            city = place.get("name", location)
            country = place.get("country", "")

            # Clima actual
            params = (
                f"?latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
                f"weather_code,cloud_cover,pressure_msl"
                f"&timezone=auto"
            )
            wx_url = self.OPEN_METEO_URL + params
            req = urllib.request.Request(wx_url, headers={"User-Agent": "Genesis/5.9"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                wx_data = json.loads(resp.read().decode("utf-8"))

            current = wx_data.get("current", {})
            temp = current.get("temperature_2m", "?")
            humidity = current.get("relative_humidity_2m", "?")
            wind = current.get("wind_speed_10m", "?")
            cloud = current.get("cloud_cover", "?")
            pressure = current.get("pressure_msl", "?")
            wmo_code = current.get("weather_code", 0)

            emoji = self._wmo_emoji(wmo_code)
            desc = self._wmo_description(wmo_code)

            lines = [
                f"{emoji} **CLIMA EN {city.upper()}** — {country}",
                f"",
                f"  🌡️ Temperatura: **{temp}°C**",
                f"  ☁️ {desc}",
                f"  💧 Humedad: {humidity}%",
                f"  💨 Viento: {wind} km/h",
                f"  ☁️ Nubosidad: {cloud}%",
                f"  📊 Presión: {pressure} hPa",
                f"",
                f"  ⏰ Fuente: Open-Meteo | {datetime.now().strftime('%H:%M:%S')}",
            ]
            return "\n".join(lines)

        except Exception:
            return None

    def _fetch_open_meteo_forecast(self, location: str, days: int) -> Optional[str]:
        """Pronóstico via Open-Meteo."""
        try:
            geo_url = self.GEOCODE_URL.format(location=urllib.parse.quote(location))
            req = urllib.request.Request(geo_url, headers={"User-Agent": "Genesis/5.9"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                geo_data = json.loads(resp.read().decode("utf-8"))

            results = geo_data.get("results", [])
            if not results:
                return None

            place = results[0]
            lat, lon = place["latitude"], place["longitude"]
            city = place.get("name", location)

            params = (
                f"?latitude={lat}&longitude={lon}"
                f"&daily=temperature_2m_max,temperature_2m_min,weather_code,"
                f"precipitation_probability_max,wind_speed_10m_max"
                f"&timezone=auto&forecast_days={days}"
            )
            wx_url = self.OPEN_METEO_URL + params
            req = urllib.request.Request(wx_url, headers={"User-Agent": "Genesis/5.9"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                wx_data = json.loads(resp.read().decode("utf-8"))

            daily = wx_data.get("daily", {})
            dates = daily.get("time", [])
            maxs = daily.get("temperature_2m_max", [])
            mins = daily.get("temperature_2m_min", [])
            codes = daily.get("weather_code", [])
            rain = daily.get("precipitation_probability_max", [])
            wind = daily.get("wind_speed_10m_max", [])

            day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            lines = [f"📅 **PRONÓSTICO {days} DÍAS — {city.upper()}**\n"]

            for i in range(min(len(dates), days)):
                try:
                    dt = datetime.strptime(dates[i], "%Y-%m-%d")
                    d_name = day_names[dt.weekday()]
                    d_fmt = f"{d_name} {dt.day}/{dt.month}"
                except Exception:
                    d_fmt = dates[i]

                code = codes[i] if i < len(codes) else 0
                emoji = self._wmo_emoji(code)
                desc = self._wmo_description(code)

                lines.append(
                    f"  {emoji} **{d_fmt}**: {mins[i]}°C → {maxs[i]}°C | {desc}"
                )
                r = rain[i] if i < len(rain) else "?"
                w = wind[i] if i < len(wind) else "?"
                lines.append(f"     🌧️ Lluvia: {r}% | 💨 Viento: {w} km/h")

            lines.append(f"\n  ⏰ Fuente: Open-Meteo | {datetime.now().strftime('%H:%M:%S')}")
            return "\n".join(lines)

        except Exception:
            return None

    # ── Helpers ────────────────────────────────────────
    def _weather_emoji(self, code: int) -> str:
        """Emoji según weatherCode de wttr.in."""
        if code in (113,):
            return "☀️"
        elif code in (116,):
            return "⛅"
        elif code in (119, 122):
            return "☁️"
        elif code in (143, 248, 260):
            return "🌫️"
        elif code in (176, 263, 266, 293, 296, 299, 302, 305, 308, 311, 314, 353, 356, 359):
            return "🌧️"
        elif code in (179, 182, 185, 227, 230, 317, 320, 323, 326, 329, 332, 335, 338, 362, 365, 368, 371, 374, 377, 392, 395):
            return "🌨️"
        elif code in (200, 386, 389):
            return "⛈️"
        else:
            return "🌤️"

    def _wmo_emoji(self, code: int) -> str:
        """Emoji según WMO weather code (Open-Meteo)."""
        if code == 0:
            return "☀️"
        elif code in (1, 2):
            return "⛅"
        elif code == 3:
            return "☁️"
        elif code in (45, 48):
            return "🌫️"
        elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
            return "🌧️"
        elif code in (71, 73, 75, 77, 85, 86):
            return "🌨️"
        elif code in (95, 96, 99):
            return "⛈️"
        return "🌤️"

    def _wmo_description(self, code: int) -> str:
        """Descripción en español del WMO code."""
        descriptions = {
            0: "Cielo despejado", 1: "Mayormente despejado",
            2: "Parcialmente nublado", 3: "Nublado",
            45: "Niebla", 48: "Niebla con escarcha",
            51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna intensa",
            56: "Llovizna helada ligera", 57: "Llovizna helada intensa",
            61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
            66: "Lluvia helada ligera", 67: "Lluvia helada intensa",
            71: "Nieve ligera", 73: "Nieve moderada", 75: "Nieve intensa",
            77: "Granizo fino", 80: "Chubascos ligeros", 81: "Chubascos moderados",
            82: "Chubascos intensos", 85: "Chubascos de nieve ligeros",
            86: "Chubascos de nieve intensos", 95: "Tormenta eléctrica",
            96: "Tormenta con granizo ligero", 99: "Tormenta con granizo intenso",
        }
        return descriptions.get(code, "Condiciones variables")

    def set_default_location(self, location: str) -> str:
        """Configura ubicación por defecto."""
        if not location or not location.strip():
            return "🌤️ Necesito una ubicación."
        self._default_location = location.strip()
        return f"🌤️ Ubicación por defecto: **{self._default_location}**"

    def _get_cache(self, key: str) -> Optional[str]:
        with self._lock:
            if key in self._cache:
                ts, val = self._cache[key]
                if (datetime.now() - ts).total_seconds() < self._cache_ttl:
                    return val
                del self._cache[key]
        return None

    def _set_cache(self, key: str, value: str):
        with self._lock:
            self._cache[key] = (datetime.now(), value)

    def status(self) -> dict:
        return {
            "default_location": self._default_location,
            "cache_entries": len(self._cache),
            "cache_ttl_seconds": self._cache_ttl,
            "sources": ["wttr.in", "Open-Meteo (fallback)"]
        }


# Singleton
weather_service = WeatherService()
