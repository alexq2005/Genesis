"""
GENESIS Brain — Motor LLM multi-proveedor.
Soporta Ollama (local/gratis), OpenAI, Anthropic y Gemini.
Todos los proveedores soportan streaming via callback.
"""
import json
import urllib.request
import urllib.error
from typing import Optional, Callable


class Brain:
    """Interfaz unificada para multiples proveedores de LLM."""

    def __init__(self, provider: str, model: str, **kwargs):
        self.provider = provider
        self.model = model
        self.ollama_url = kwargs.get("ollama_url", "http://localhost:11434")
        self.openai_key = kwargs.get("openai_key", "")
        self.anthropic_key = kwargs.get("anthropic_key", "")
        self.google_key = kwargs.get("google_key", "")
        self.total_tokens_used = 0
        self.total_calls = 0

    def think(self, system_prompt: str, messages: list[dict],
              temperature: float = 0.7, max_tokens: int = 2048,
              stream: bool = False, stream_callback: Callable = None) -> str:
        """
        Envia un prompt al LLM y retorna la respuesta.

        Args:
            system_prompt: Instrucciones del sistema
            messages: Lista de {"role": "user/assistant", "content": "..."}
            temperature: Creatividad (0.0 = determinista, 1.0 = creativo)
            max_tokens: Longitud maxima de respuesta
            stream: Si True, genera tokens uno a uno
            stream_callback: Funcion callback(token_str) para streaming

        Returns:
            Texto de respuesta del LLM (completo, incluso en modo streaming)
        """
        self.total_calls += 1

        if self.provider == "ollama":
            return self._think_ollama(
                system_prompt, messages, temperature, max_tokens,
                stream=stream, callback=stream_callback,
            )
        elif self.provider == "openai":
            return self._think_openai(
                system_prompt, messages, temperature, max_tokens,
                stream=stream, callback=stream_callback,
            )
        elif self.provider == "anthropic":
            return self._think_anthropic(
                system_prompt, messages, temperature, max_tokens,
                stream=stream, callback=stream_callback,
            )
        elif self.provider == "gemini":
            return self._think_gemini(
                system_prompt, messages, temperature, max_tokens,
                stream=stream, callback=stream_callback,
            )
        else:
            raise ValueError(f"Proveedor no soportado: {self.provider}")

    def _think_ollama(self, system_prompt: str, messages: list[dict],
                      temperature: float, max_tokens: int,
                      stream: bool = False, callback: Callable = None,
                      timeout: int = 300) -> str:
        """Genera respuesta usando Ollama (local)."""
        all_messages = [{"role": "system", "content": system_prompt}] + messages

        # Ollama soporta streaming nativo via NDJSON
        use_stream = stream and callback is not None

        # Calcular num_ctx dinámico basado en el tamaño real del prompt
        # Esto optimiza el uso de RAM: preguntas simples usan menos KV cache
        total_chars = sum(len(m.get("content", "")) for m in all_messages)
        estimated_tokens = total_chars // 3  # ~3 chars por token aprox
        # Mínimo 8K, máximo 32K, con margen del 50% para respuesta
        dynamic_ctx = max(8192, min(32768, int(estimated_tokens * 1.5) + max_tokens))
        # Alinear a múltiplos de 2048 para eficiencia
        dynamic_ctx = ((dynamic_ctx + 2047) // 2048) * 2048

        payload = {
            "model": self.model,
            "messages": all_messages,
            "stream": use_stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": dynamic_ctx,
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.ollama_url}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            if use_stream:
                # Streaming: Ollama envia NDJSON (una linea JSON por token)
                # IMPORTANTE: usar readline() en vez de 'for line in resp:'
                # porque el iterador de archivo bufferea internamente (~8KB),
                # bloqueando el streaming real. readline() entrega cada linea
                # inmediatamente cuando Ollama la envia via chunked encoding.
                full_response = []
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    while True:
                        line = resp.readline()
                        if not line:
                            break
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line.decode("utf-8"))
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                callback(token)
                                full_response.append(token)
                            # Ollama envia done:true en el ultimo chunk
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
                return "".join(full_response)
            else:
                # Batch: esperar respuesta completa
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    return result["message"]["content"]

        except urllib.error.URLError:
            return ("[ERROR] No se pudo conectar con Ollama. "
                    "Asegurate de que Ollama este corriendo (ollama serve) "
                    "y que el modelo este descargado (ollama pull llama3.1)")
        except Exception as e:
            return f"[ERROR] Ollama: {e}"

    def _think_openai(self, system_prompt: str, messages: list[dict],
                      temperature: float, max_tokens: int,
                      stream: bool = False, callback: Callable = None) -> str:
        """Genera respuesta usando OpenAI API."""
        if not self.openai_key:
            return "[ERROR] No se configuro OPENAI_API_KEY. Edita config.py o usa variable de entorno."

        all_messages = [{"role": "system", "content": system_prompt}] + messages
        use_stream = stream and callback is not None

        payload = {
            "model": self.model,
            "messages": all_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": use_stream,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}",
                },
                method="POST"
            )

            if use_stream:
                # Streaming: OpenAI envia SSE (Server-Sent Events)
                full_response = []
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for line in resp:
                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        if line == "data: [DONE]":
                            break
                        try:
                            chunk = json.loads(line[6:])  # Remover "data: "
                            delta = chunk["choices"][0].get("delta", {})
                            token = delta.get("content", "")
                            if token:
                                callback(token)
                                full_response.append(token)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                return "".join(full_response)
            else:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    usage = result.get("usage", {})
                    self.total_tokens_used += usage.get("total_tokens", 0)
                    return result["choices"][0]["message"]["content"]

        except Exception as e:
            return f"[ERROR] OpenAI: {e}"

    def _think_anthropic(self, system_prompt: str, messages: list[dict],
                         temperature: float, max_tokens: int,
                         stream: bool = False, callback: Callable = None) -> str:
        """Genera respuesta usando Anthropic API (Claude)."""
        if not self.anthropic_key:
            return "[ERROR] No se configuro ANTHROPIC_API_KEY. Edita config.py o usa variable de entorno."

        use_stream = stream and callback is not None

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": messages,
            "stream": use_stream,
        }

        try:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                "https://api.anthropic.com/v1/messages",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.anthropic_key,
                    "anthropic-version": "2023-06-01",
                },
                method="POST"
            )

            if use_stream:
                # Streaming: Anthropic envia SSE
                full_response = []
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for line in resp:
                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        try:
                            chunk = json.loads(line[6:])
                            if chunk.get("type") == "content_block_delta":
                                token = chunk.get("delta", {}).get("text", "")
                                if token:
                                    callback(token)
                                    full_response.append(token)
                        except (json.JSONDecodeError, KeyError):
                            continue
                return "".join(full_response)
            else:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    usage = result.get("usage", {})
                    self.total_tokens_used += usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    return result["content"][0]["text"]

        except Exception as e:
            return f"[ERROR] Anthropic: {e}"

    def _think_gemini(self, system_prompt: str, messages: list[dict],
                      temperature: float, max_tokens: int,
                      stream: bool = False, callback: Callable = None) -> str:
        """Genera respuesta usando Google Gemini API."""
        if not self.google_key:
            return "[ERROR] No se configuro GOOGLE_API_KEY. Edita config.py o usa variable de entorno."

        use_stream = stream and callback is not None

        # Convertir mensajes de formato OpenAI a formato Gemini
        # Gemini usa "user"/"model" (no "assistant") y "parts" (no "content")
        gemini_contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        payload = {
            "contents": gemini_contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        try:
            data = json.dumps(payload).encode("utf-8")

            if use_stream:
                # Streaming: Gemini usa streamGenerateContent con SSE
                url = (f"https://generativelanguage.googleapis.com/v1beta/"
                       f"models/{self.model}:streamGenerateContent"
                       f"?alt=sse&key={self.google_key}")
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                full_response = []
                with urllib.request.urlopen(req, timeout=120) as resp:
                    for line in resp:
                        line = line.decode("utf-8").strip()
                        if not line or not line.startswith("data: "):
                            continue
                        try:
                            chunk = json.loads(line[6:])
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for part in parts:
                                    token = part.get("text", "")
                                    if token:
                                        callback(token)
                                        full_response.append(token)
                            # Contar tokens del uso
                            usage = chunk.get("usageMetadata", {})
                            if usage:
                                self.total_tokens_used += usage.get("totalTokenCount", 0)
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                return "".join(full_response)
            else:
                # Batch: respuesta completa
                url = (f"https://generativelanguage.googleapis.com/v1beta/"
                       f"models/{self.model}:generateContent"
                       f"?key={self.google_key}")
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    candidates = result.get("candidates", [])
                    if not candidates:
                        # Puede ser un bloqueo de seguridad
                        block_reason = result.get("promptFeedback", {}).get("blockReason", "UNKNOWN")
                        return f"[ERROR] Gemini bloqueo la respuesta: {block_reason}"
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                    # Contar tokens
                    usage = result.get("usageMetadata", {})
                    self.total_tokens_used += usage.get("totalTokenCount", 0)
                    return text

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                error_json = json.loads(error_body)
                error_msg = error_json.get("error", {}).get("message", str(e))
            except Exception:
                error_msg = error_body or str(e)
            if e.code == 429:
                return f"[ERROR] Gemini: limite de requests excedido. {error_msg}"
            return f"[ERROR] Gemini ({e.code}): {error_msg}"
        except Exception as e:
            return f"[ERROR] Gemini: {e}"

    def quick_think(self, prompt: str, system: str = "Responde de forma concisa.",
                    temperature: float = 0.5) -> str:
        """Atajo para pensamientos rapidos internos (debate, evaluacion, etc)."""
        messages = [{"role": "user", "content": prompt}]
        return self.think(system, messages, temperature=temperature, max_tokens=512)

    def is_available(self) -> bool:
        """Verifica si el proveedor esta disponible."""
        if self.provider == "ollama":
            try:
                req = urllib.request.Request(f"{self.ollama_url}/api/tags")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status == 200
            except Exception:
                return False
        elif self.provider == "openai":
            return bool(self.openai_key)
        elif self.provider == "anthropic":
            return bool(self.anthropic_key)
        elif self.provider == "gemini":
            if not self.google_key:
                return False
            try:
                url = (f"https://generativelanguage.googleapis.com/v1beta/"
                       f"models/{self.model}?key={self.google_key}")
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status == 200
            except Exception:
                return False
        return False

    def get_stats(self) -> dict:
        """Retorna estadisticas de uso."""
        return {
            "provider": self.provider,
            "model": self.model,
            "total_calls": self.total_calls,
            "total_tokens": self.total_tokens_used,
        }
