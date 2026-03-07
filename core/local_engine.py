"""
GENESIS Local Engine — Motor de inferencia local.

Corre modelos LLM directamente en tu PC usando tu GPU NVIDIA.
No requiere internet, API keys ni servicios externos.
Usa ctransformers con soporte CUDA para inferencia acelerada por GPU.
"""
import os
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


# Directorio donde se guardan los modelos
MODELS_DIR = Path(__file__).parent.parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

# Catalogo de modelos recomendados (GGUF format)
# Los modelos "uncensored" no tienen filtros de rechazo
MODEL_CATALOG = {
    "small": {
        "name": "TinyLlama 1.1B",
        "description": "Modelo ultraligero. Rapido pero basico.",
        "repo": "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF",
        "file": "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf",
        "size_gb": 0.7,
        "vram_needed": 1,
        "model_type": "llama",
        "chat_format": "chatml",
        "context_length": 2048,
    },
    "qwen": {
        "name": "Qwen 2.5 7B Instruct [SIN CENSURA]",
        "description": "Mejor modelo 7B. Sin filtros. Requiere llama-cpp-python.",
        "repo": "bartowski/Qwen2.5-7B-Instruct-GGUF",
        "file": "Qwen2.5-7B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.7,
        "vram_needed": 6,
        "model_type": "llama",
        "chat_format": "chatml",
        "context_length": 8192,
        "backend": "llama-cpp",
        "fallback_key": "medium",
    },
    "medium": {
        "name": "Dolphin 2.8 Mistral 7B [SIN CENSURA]",
        "description": "Mistral 7B sin censura por Eric Hartford. Sin filtros de rechazo.",
        "repo": "bartowski/dolphin-2.8-mistral-7b-v02-GGUF",
        "file": "dolphin-2.8-mistral-7b-v02-Q4_K_M.gguf",
        "size_gb": 4.4,
        "vram_needed": 5,
        "model_type": "mistral",
        "chat_format": "chatml",
        "context_length": 8192,
        "fallback_key": "medium-censored",
    },
    "medium-censored": {
        "name": "Mistral 7B Instruct (censurado)",
        "description": "Mistral 7B original con filtros. Backup si Dolphin da problemas.",
        "repo": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        "file": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
        "size_gb": 4.4,
        "vram_needed": 5,
        "model_type": "mistral",
        "chat_format": "mistral",
        "context_length": 8192,
    },
    "large": {
        "name": "Dolphin 2.9.3 Mistral 7B 32k [SIN CENSURA]",
        "description": "Dolphin 2.9.3 Mistral 7B sin censura. Contexto 32k. Maxima calidad.",
        "repo": "bartowski/dolphin-2.9.3-mistral-7B-32k-GGUF",
        "file": "dolphin-2.9.3-mistral-7B-32k-Q4_K_M.gguf",
        "size_gb": 4.4,
        "vram_needed": 5,
        "model_type": "mistral",
        "chat_format": "chatml",
        "context_length": 32768,
        "fallback_key": "medium",
    },
}


class ModelDownloader:
    """Descarga modelos desde HuggingFace."""

    HF_BASE_URL = "https://huggingface.co"

    @staticmethod
    def list_available() -> dict:
        """Lista los modelos disponibles en el catalogo."""
        return MODEL_CATALOG

    @staticmethod
    def get_model_path(model_key: str) -> Optional[Path]:
        """Retorna el path del modelo si ya esta descargado."""
        if model_key not in MODEL_CATALOG:
            return None
        model_info = MODEL_CATALOG[model_key]
        filepath = MODELS_DIR / model_info["file"]
        if filepath.exists():
            return filepath
        return None

    @staticmethod
    def download(model_key: str, callback=None) -> Path:
        """
        Descarga un modelo desde HuggingFace.

        Args:
            model_key: Clave del catalogo ("small", "medium", "large")
            callback: Funcion callback(bytes_downloaded, total_bytes)

        Returns:
            Path al archivo descargado
        """
        if model_key not in MODEL_CATALOG:
            raise ValueError(f"Modelo '{model_key}' no encontrado en el catalogo. "
                             f"Opciones: {list(MODEL_CATALOG.keys())}")

        model_info = MODEL_CATALOG[model_key]
        filepath = MODELS_DIR / model_info["file"]

        # Verificar si ya existe
        if filepath.exists():
            print(f"  Modelo ya descargado: {filepath.name}")
            return filepath

        # Construir URL de descarga
        url = (f"{ModelDownloader.HF_BASE_URL}/"
               f"{model_info['repo']}/resolve/main/{model_info['file']}")

        print(f"  Descargando: {model_info['name']}")
        print(f"  Tamano: ~{model_info['size_gb']} GB")
        print(f"  Desde: {model_info['repo']}")
        print(f"  Destino: {filepath}")
        print()

        try:
            # Intentar primero con huggingface_hub si esta instalado
            try:
                from huggingface_hub import hf_hub_download
                downloaded_path = hf_hub_download(
                    repo_id=model_info["repo"],
                    filename=model_info["file"],
                    local_dir=str(MODELS_DIR),
                    local_dir_use_symlinks=False,
                )
                print(f"\n  Descarga completada: {downloaded_path}")
                return Path(downloaded_path)
            except ImportError:
                pass

            # Fallback: descarga directa con urllib
            req = urllib.request.Request(url, headers={
                "User-Agent": "Genesis-AI/1.0"
            })

            with urllib.request.urlopen(req, timeout=30) as response:
                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0
                chunk_size = 1024 * 1024  # 1 MB

                with open(filepath, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)

                        if callback:
                            callback(downloaded, total_size)
                        elif total_size > 0:
                            pct = (downloaded / total_size) * 100
                            bar_len = 30
                            filled = int(bar_len * downloaded / total_size)
                            bar = "█" * filled + "░" * (bar_len - filled)
                            dl_mb = downloaded / (1024 * 1024)
                            total_mb = total_size / (1024 * 1024)
                            print(f"\r  [{bar}] {pct:.1f}% "
                                  f"({dl_mb:.0f}/{total_mb:.0f} MB)", end="")

            print(f"\n  Descarga completada: {filepath.name}")
            return filepath

        except Exception as e:
            # Limpiar archivo parcial
            if filepath.exists():
                filepath.unlink()
            raise RuntimeError(f"Error descargando modelo: {e}")


class LocalEngine:
    """
    Motor de inferencia local usando ctransformers.
    Corre modelos LLM directamente en tu GPU.
    """

    def __init__(self, model_path: str = None, model_key: str = "medium",
                 gpu_layers: int = 50, context_length: int = 4096):
        """
        Args:
            model_path: Path directo al archivo .gguf (opcional)
            model_key: Clave del catalogo si no se da model_path
            gpu_layers: Capas del modelo en GPU (mas = mas rapido, mas VRAM)
            context_length: Longitud maxima de contexto
        """
        self.model = None
        self.model_key = model_key
        self.model_path = model_path
        self.gpu_layers = gpu_layers
        self.context_length = context_length
        self.model_type = "llama"
        self.chat_format = "chatml"
        self.backend = None  # "llama-cpp" o "ctransformers"
        self.loaded = False
        self.total_tokens = 0

    def _resolve_model_path(self) -> Optional[Path]:
        """Resuelve el path del modelo: descarga si falta, fallback si falla."""
        if self.model_path:
            return Path(self.model_path)

        path = ModelDownloader.get_model_path(self.model_key)
        if path:
            return path

        print(f"  Modelo '{self.model_key}' no descargado. Descargando...")
        try:
            return ModelDownloader.download(self.model_key)
        except RuntimeError as e:
            print(f"  [ERROR] Descarga fallida: {e}")
            # Intentar fallback
            fallback = MODEL_CATALOG.get(self.model_key, {}).get("fallback_key")
            if fallback:
                print(f"  Intentando modelo alternativo: {fallback}...")
                fallback_path = ModelDownloader.get_model_path(fallback)
                if fallback_path:
                    self.model_key = fallback
                    print(f"  Usando modelo existente: {fallback_path.name}")
                    return fallback_path
                try:
                    path = ModelDownloader.download(fallback)
                    self.model_key = fallback
                    return path
                except RuntimeError:
                    pass
            # Ultimo recurso: buscar cualquier .gguf en la carpeta models
            print(f"  Buscando cualquier modelo disponible...")
            for gguf in MODELS_DIR.glob("*.gguf"):
                if "mistral" in gguf.name.lower():
                    self.model_type = "mistral"
                elif "llama" in gguf.name.lower():
                    self.model_type = "llama"
                print(f"  Encontrado: {gguf.name}")
                return gguf
        return None

    def load(self) -> bool:
        """Carga el modelo en memoria/GPU. Elige el mejor backend con soporte GPU."""
        path = self._resolve_model_path()
        if not path or not path.exists():
            print(f"  [ERROR] Modelo no encontrado.")
            print(f"  Descarga uno manualmente a: {MODELS_DIR}")
            return False

        # Obtener tipo de modelo del catalogo
        if self.model_key in MODEL_CATALOG:
            self.model_type = MODEL_CATALOG[self.model_key]["model_type"]
            self.context_length = MODEL_CATALOG[self.model_key]["context_length"]
            self.chat_format = MODEL_CATALOG[self.model_key].get("chat_format", "chatml")

        print(f"  Cargando modelo: {path.name}")
        print(f"  GPU layers: {self.gpu_layers}")
        print(f"  Context length: {self.context_length}")

        # Detectar soporte GPU en llama-cpp
        llama_has_gpu = self._check_llama_gpu()

        # Estrategia: priorizar el backend que tenga GPU
        # Modelos mistral/llama funcionan con ctransformers (que tiene CUDA)
        # Modelos que requieren llama-cpp (como qwen) necesitan llama-cpp con GPU
        requires_llama = MODEL_CATALOG.get(self.model_key, {}).get("backend") == "llama-cpp"

        if requires_llama and not llama_has_gpu:
            print(f"  [WARN] Modelo '{self.model_key}' requiere llama-cpp con GPU.")
            print(f"  llama-cpp no tiene CUDA. Necesitas instalar CUDA Toolkit.")
            # Intentar fallback a otro modelo que funcione con ctransformers
            fallback = MODEL_CATALOG.get(self.model_key, {}).get("fallback_key")
            if fallback:
                print(f"  Usando modelo alternativo: {fallback}")
                self.model_key = fallback
                return self.load()  # Reintentar con fallback
            return False

        if llama_has_gpu:
            # llama-cpp con GPU — mejor opcion
            if self._load_llama_cpp(path):
                return True

        # ctransformers con CUDA — excelente para mistral/llama
        if self._load_ctransformers(path):
            return True

        # Ultimo recurso: llama-cpp sin GPU (lento)
        if not llama_has_gpu and self._load_llama_cpp(path):
            return True

        print(f"  [ERROR] No se pudo cargar el modelo con ningun backend.")
        print(f"  Instala: pip install ctransformers[cuda]")
        return False

    def _check_llama_gpu(self) -> bool:
        """Verifica si llama-cpp-python tiene soporte GPU."""
        try:
            import llama_cpp
            return llama_cpp.llama_supports_gpu_offload()
        except (ImportError, AttributeError):
            return False

    def _load_llama_cpp(self, path: Path) -> bool:
        """Intenta cargar con llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            return False

        gpu_ok = self._check_llama_gpu()
        gpu_layers = self.gpu_layers if gpu_ok else 0

        try:
            self.model = Llama(
                model_path=str(path),
                n_gpu_layers=gpu_layers,
                n_ctx=self.context_length,
                verbose=False,
            )
            self.backend = "llama-cpp"
            self.loaded = True
            if gpu_ok:
                print(f"  Modelo cargado en GPU (llama-cpp-python + CUDA)")
            else:
                print(f"  Modelo cargado en CPU (llama-cpp-python, sin CUDA)")
            return True
        except Exception as e:
            print(f"  [WARN] llama-cpp fallo: {e}")
            return False

    def _load_ctransformers(self, path: Path) -> bool:
        """Fallback: cargar con ctransformers."""
        try:
            from ctransformers import AutoModelForCausalLM
        except ImportError:
            return False

        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                str(path.parent),
                model_file=path.name,
                model_type=self.model_type,
                gpu_layers=self.gpu_layers,
                context_length=self.context_length,
            )
            self.backend = "ctransformers"
            self.loaded = True
            print(f"  Modelo cargado exitosamente en GPU (ctransformers)")
            return True
        except Exception as e:
            print(f"  [WARN] ctransformers fallo: {e}")
            if self.gpu_layers > 0:
                print(f"  Reintentando con menos capas en GPU...")
                self.gpu_layers = max(0, self.gpu_layers - 20)
                return self._load_ctransformers(path)
            return False

    def generate(self, prompt: str, max_tokens: int = 1024,
                 temperature: float = 0.7, stop: list[str] = None,
                 stream: bool = False, stream_callback=None) -> str:
        """
        Genera texto a partir de un prompt formateado.

        Args:
            prompt: Prompt formateado
            max_tokens: Tokens maximos a generar
            temperature: Creatividad
            stop: Secuencias de parada
            stream: Si True, genera token por token
            stream_callback: Funcion callback(token_str) para streaming
        """
        if not self.loaded or not self.model:
            return "[ERROR] Modelo no cargado. Ejecuta load() primero."

        stop_sequences = stop or ["</s>", "<|im_end|>", "<|eot_id|>", "<|im_start|>"]

        try:
            # Modo streaming
            if stream and stream_callback:
                return self._generate_stream(
                    prompt, max_tokens, temperature,
                    stop_sequences, stream_callback
                )

            # Modo normal (batch)
            if self.backend == "llama-cpp":
                output = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop_sequences,
                )
                response = output["choices"][0]["text"]
            else:
                # ctransformers
                response = self.model(
                    prompt,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop_sequences,
                )

            self.total_tokens += len(response.split())
            return response.strip()

        except Exception as e:
            return f"[ERROR] Generacion fallida: {e}"

    def _generate_stream(self, prompt: str, max_tokens: int,
                         temperature: float, stop_sequences: list[str],
                         callback) -> str:
        """
        Genera texto token por token, llamando callback para cada uno.
        Permite mostrar la respuesta progresivamente en la consola.
        """
        try:
            if self.backend == "llama-cpp":
                output = self.model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop_sequences,
                    stream=True,
                )
                full_response = ""
                for chunk in output:
                    token = chunk["choices"][0]["text"]
                    full_response += token
                    callback(token)
                    # Verificar stop sequences
                    for seq in stop_sequences:
                        if seq in full_response:
                            full_response = full_response.split(seq)[0]
                            self.total_tokens += len(full_response.split())
                            return full_response.strip()

                self.total_tokens += len(full_response.split())
                return full_response.strip()

            else:
                # ctransformers — usar tokens() para streaming
                formatted = prompt
                full_response = ""
                for token in self.model.tokens():
                    if len(full_response.split()) >= max_tokens:
                        break
                    text = self.model.detokenize([token])
                    full_response += text
                    callback(text)
                    for seq in stop_sequences:
                        if seq in full_response:
                            full_response = full_response.split(seq)[0]
                            self.total_tokens += len(full_response.split())
                            return full_response.strip()

                self.total_tokens += len(full_response.split())
                return full_response.strip()

        except Exception:
            # Fallback a generacion normal si streaming falla
            return self.generate(prompt, max_tokens, temperature,
                                 stop_sequences, stream=False)

    def format_chat(self, system_prompt: str, messages: list[dict]) -> str:
        """
        Formatea mensajes de chat al formato del modelo.
        Usa chat_format del catalogo: chatml, mistral, llama3, generic.
        """
        fmt = getattr(self, "chat_format", "chatml")
        if fmt == "chatml":
            return self._format_chatml(system_prompt, messages)
        elif fmt == "mistral":
            return self._format_mistral(system_prompt, messages)
        elif fmt == "llama3":
            return self._format_llama3(system_prompt, messages)
        else:
            return self._format_generic(system_prompt, messages)

    def _format_chatml(self, system_prompt: str, messages: list[dict]) -> str:
        """Formato ChatML para modelos Dolphin."""
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n"

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"

        prompt += "<|im_start|>assistant\n"
        return prompt

    def _format_mistral(self, system_prompt: str, messages: list[dict]) -> str:
        """Formato de chat para Mistral Instruct."""
        prompt = f"<s>[INST] {system_prompt}\n\n"

        for i, msg in enumerate(messages):
            if msg["role"] == "user":
                if i > 0:
                    prompt += f"[INST] {msg['content']} [/INST]"
                else:
                    prompt += f"{msg['content']} [/INST]"
            elif msg["role"] == "assistant":
                prompt += f" {msg['content']}</s>"

        return prompt

    def _format_llama3(self, system_prompt: str, messages: list[dict]) -> str:
        """Formato de chat para Llama 3."""
        prompt = (f"<|begin_of_text|>"
                  f"<|start_header_id|>system<|end_header_id|>\n\n"
                  f"{system_prompt}<|eot_id|>")

        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            prompt += (f"<|start_header_id|>{role}<|end_header_id|>\n\n"
                       f"{content}<|eot_id|>")

        prompt += "<|start_header_id|>assistant<|end_header_id|>\n\n"
        return prompt

    def _format_generic(self, system_prompt: str, messages: list[dict]) -> str:
        """Formato generico para cualquier modelo."""
        prompt = f"System: {system_prompt}\n\n"
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n\n"
        prompt += "Assistant: "
        return prompt

    def think(self, system_prompt: str, messages: list[dict],
              temperature: float = 0.7, max_tokens: int = 1024,
              stream: bool = False, stream_callback=None) -> str:
        """
        Interfaz compatible con Brain.think() para integracion directa.
        Soporta streaming opcional.
        """
        prompt = self.format_chat(system_prompt, messages)
        return self.generate(prompt, max_tokens=max_tokens,
                             temperature=temperature,
                             stream=stream,
                             stream_callback=stream_callback)

    def quick_think(self, prompt: str, system: str = "Responde de forma concisa.",
                    temperature: float = 0.5) -> str:
        """Atajo para pensamientos rapidos (compatible con Brain). Sin streaming."""
        messages = [{"role": "user", "content": prompt}]
        return self.think(system, messages, temperature=temperature,
                          max_tokens=512)

    def is_available(self) -> bool:
        """Verifica si el motor esta disponible."""
        return self.loaded

    def get_stats(self) -> dict:
        """Retorna estadisticas."""
        return {
            "provider": "local",
            "model": self.model_key,
            "model_type": self.model_type,
            "backend": self.backend or "none",
            "gpu_layers": self.gpu_layers,
            "context_length": self.context_length,
            "total_tokens": self.total_tokens,
            "loaded": self.loaded,
        }

    def unload(self):
        """Libera el modelo de la memoria."""
        if self.model:
            del self.model
            self.model = None
            self.loaded = False
            print("  Modelo descargado de memoria.")
