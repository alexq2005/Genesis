"""
GENESIS Text Transformer — Transformaciones de texto rápidas.
Conversiones de caso, encoding, hashing, estadísticas, formateo.
"""
import base64
import hashlib
import re
import json
from urllib.parse import quote, unquote


class TextTransformer:
    """Transformaciones de texto sin depender de LLM."""

    # ── Case Conversions ──────────────────────────────
    @staticmethod
    def to_upper(text: str) -> str:
        return f"🔤 **MAYÚSCULAS:**\n\n{text.upper()}"

    @staticmethod
    def to_lower(text: str) -> str:
        return f"🔤 **minúsculas:**\n\n{text.lower()}"

    @staticmethod
    def to_title(text: str) -> str:
        return f"🔤 **Título:**\n\n{text.title()}"

    @staticmethod
    def to_capitalize(text: str) -> str:
        return f"🔤 **Capitalizado:**\n\n{text.capitalize()}"

    @staticmethod
    def to_swap_case(text: str) -> str:
        return f"🔤 **Invertido:**\n\n{text.swapcase()}"

    @staticmethod
    def to_camel_case(text: str) -> str:
        words = re.split(r'[\s_\-]+', text)
        result = words[0].lower() + ''.join(w.capitalize() for w in words[1:])
        return f"🔤 **camelCase:**\n\n{result}"

    @staticmethod
    def to_snake_case(text: str) -> str:
        # Insert _ before uppercase letters, lowercase all
        s1 = re.sub(r'([A-Z])', r'_\1', text)
        result = re.sub(r'[\s\-]+', '_', s1).lower().strip('_')
        result = re.sub(r'_+', '_', result)
        return f"🔤 **snake_case:**\n\n{result}"

    @staticmethod
    def to_kebab_case(text: str) -> str:
        s1 = re.sub(r'([A-Z])', r'-\1', text)
        result = re.sub(r'[\s_]+', '-', s1).lower().strip('-')
        result = re.sub(r'-+', '-', result)
        return f"🔤 **kebab-case:**\n\n{result}"

    # ── Encoding/Decoding ─────────────────────────────
    @staticmethod
    def encode_base64(text: str) -> str:
        encoded = base64.b64encode(text.encode("utf-8")).decode("utf-8")
        return f"🔐 **Base64 encode:**\n\n{encoded}"

    @staticmethod
    def decode_base64(text: str) -> str:
        try:
            decoded = base64.b64decode(text.encode("utf-8")).decode("utf-8")
            if not decoded.strip():
                return "❌ No es un texto Base64 válido (resultado vacío)."
            return f"🔓 **Base64 decode:**\n\n{decoded}"
        except Exception:
            return "❌ No es un texto Base64 válido."

    @staticmethod
    def encode_url(text: str) -> str:
        encoded = quote(text, safe='')
        return f"🔐 **URL encode:**\n\n{encoded}"

    @staticmethod
    def decode_url(text: str) -> str:
        decoded = unquote(text)
        return f"🔓 **URL decode:**\n\n{decoded}"

    @staticmethod
    def to_hex(text: str) -> str:
        hex_str = text.encode("utf-8").hex()
        return f"🔢 **Hexadecimal:**\n\n{hex_str}"

    @staticmethod
    def from_hex(text: str) -> str:
        try:
            decoded = bytes.fromhex(text.replace(" ", "")).decode("utf-8")
            return f"🔓 **Desde hex:**\n\n{decoded}"
        except Exception:
            return "❌ No es un texto hexadecimal válido."

    # ── Hashing ───────────────────────────────────────
    @staticmethod
    def hash_text(text: str) -> str:
        md5 = hashlib.md5(text.encode()).hexdigest()
        sha1 = hashlib.sha1(text.encode()).hexdigest()
        sha256 = hashlib.sha256(text.encode()).hexdigest()
        return (f"🔑 **Hashes de:** `{text[:50]}{'...' if len(text) > 50 else ''}`\n\n"
                f"  MD5:    `{md5}`\n"
                f"  SHA1:   `{sha1}`\n"
                f"  SHA256: `{sha256}`")

    # ── Text Statistics ───────────────────────────────
    @staticmethod
    def count_text(text: str) -> str:
        chars = len(text)
        chars_no_space = len(text.replace(" ", ""))
        words = len(text.split())
        lines = text.count("\n") + 1
        sentences = len(re.findall(r'[.!?]+', text)) or 1
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])

        # Estimaciones de lectura
        read_time_min = words / 200  # ~200 palabras/minuto
        speak_time_min = words / 130  # ~130 palabras/minuto

        return (f"📊 **ESTADÍSTICAS DE TEXTO**\n\n"
                f"  📝 Caracteres: {chars:,} (sin espacios: {chars_no_space:,})\n"
                f"  📖 Palabras: {words:,}\n"
                f"  📄 Líneas: {lines:,}\n"
                f"  📃 Oraciones: {sentences:,}\n"
                f"  📑 Párrafos: {paragraphs:,}\n"
                f"  ⏱️ Lectura: ~{read_time_min:.1f} min\n"
                f"  🗣️ Hablado: ~{speak_time_min:.1f} min")

    # ── Text Cleaning ─────────────────────────────────
    @staticmethod
    def remove_duplicates(text: str) -> str:
        """Elimina líneas duplicadas manteniendo el orden."""
        seen = set()
        unique = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped not in seen:
                seen.add(stripped)
                unique.append(line)
        removed = text.count("\n") + 1 - len(unique)
        return (f"🧹 **Duplicados eliminados:** {removed} líneas\n\n"
                + "\n".join(unique))

    @staticmethod
    def sort_lines(text: str, reverse: bool = False) -> str:
        """Ordena líneas alfabéticamente."""
        lines = [l for l in text.splitlines() if l.strip()]
        lines.sort(key=str.lower, reverse=reverse)
        direction = "Z→A" if reverse else "A→Z"
        return f"📋 **Líneas ordenadas ({direction}):**\n\n" + "\n".join(lines)

    @staticmethod
    def reverse_text(text: str) -> str:
        return f"🔄 **Texto invertido:**\n\n{text[::-1]}"

    @staticmethod
    def extract_emails(text: str) -> str:
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
        if not emails:
            return "📧 No encontré emails en el texto."
        unique = list(dict.fromkeys(emails))
        return f"📧 **Emails encontrados ({len(unique)}):**\n\n" + "\n".join(f"  • {e}" for e in unique)

    @staticmethod
    def extract_urls(text: str) -> str:
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', text)
        if not urls:
            return "🔗 No encontré URLs en el texto."
        unique = list(dict.fromkeys(urls))
        return f"🔗 **URLs encontradas ({len(unique)}):**\n\n" + "\n".join(f"  • {u}" for u in unique)

    @staticmethod
    def extract_numbers(text: str) -> str:
        numbers = re.findall(r'-?\d+\.?\d*', text)
        if not numbers:
            return "🔢 No encontré números en el texto."
        nums = [float(n) if '.' in n else int(n) for n in numbers]
        total = sum(nums)
        avg = total / len(nums)
        return (f"🔢 **Números encontrados ({len(nums)}):** {', '.join(numbers)}\n"
                f"  Suma: {total}\n"
                f"  Promedio: {avg:.2f}\n"
                f"  Min: {min(nums)} | Max: {max(nums)}")

    @staticmethod
    def to_json_pretty(text: str) -> str:
        """Formatea JSON de forma legible."""
        try:
            data = json.loads(text)
            pretty = json.dumps(data, indent=2, ensure_ascii=False)
            return f"📋 **JSON formateado:**\n\n```json\n{pretty}\n```"
        except json.JSONDecodeError:
            return "❌ No es un JSON válido."

    # ── Dispatcher ────────────────────────────────────
    def transform(self, action: str, text: str) -> str:
        """Despacha la transformación según la acción."""
        actions = {
            "mayusculas": self.to_upper,
            "minusculas": self.to_lower,
            "titulo": self.to_title,
            "capitalizar": self.to_capitalize,
            "invertir_caso": self.to_swap_case,
            "camelcase": self.to_camel_case,
            "snakecase": self.to_snake_case,
            "kebabcase": self.to_kebab_case,
            "base64_encode": self.encode_base64,
            "base64_decode": self.decode_base64,
            "url_encode": self.encode_url,
            "url_decode": self.decode_url,
            "hex": self.to_hex,
            "from_hex": self.from_hex,
            "hash": self.hash_text,
            "contar": self.count_text,
            "duplicados": self.remove_duplicates,
            "ordenar": self.sort_lines,
            "invertir": self.reverse_text,
            "emails": self.extract_emails,
            "urls": self.extract_urls,
            "numeros": self.extract_numbers,
            "json": self.to_json_pretty,
        }

        fn = actions.get(action.lower())
        if not fn:
            available = ", ".join(sorted(actions.keys()))
            return f"❌ Acción '{action}' no reconocida.\n\nDisponibles: {available}"
        return fn(text)


# Singleton
text_transformer = TextTransformer()
