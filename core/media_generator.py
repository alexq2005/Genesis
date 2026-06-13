"""
GENESIS — Media Generator
Genera imagenes, audio y video.

Capacidades:
- Imagenes: Pollinations.ai (gratis, sin API key) + Pillow local (diagramas, banners)
- Audio: pyttsx3 (TTS local a archivo WAV/MP3) + edge-tts (online, mas natural)
- Video: Combina imagenes + audio con OpenCV + ffmpeg

Uso:
    gen = MediaGenerator()
    gen.generate_image("un gato en el espacio", style="realistic")
    gen.generate_audio("Hola, soy Genesis", voice="es")
    gen.generate_video(images=["img1.png"], audio="audio.wav", output="video.mp4")
"""
import os
import json
import time
import threading
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Pipeline de Stable Diffusion local cacheado (se carga 1 vez, queda en VRAM).
_SD_PIPE = None


class MediaGenerator:
    """
    Generador de medios: imagenes, audio y video.
    """

    OUTPUT_DIR = "generated_media"

    def __init__(self, output_dir: str = ""):
        base = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = Path(output_dir) if output_dir else base / self.OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "images").mkdir(exist_ok=True)
        (self.output_dir / "audio").mkdir(exist_ok=True)
        (self.output_dir / "video").mkdir(exist_ok=True)

        self.generated: List[dict] = []
        self.enabled = True

    # =========================================================
    # IMAGE GENERATION
    # =========================================================
    def _try_local_sd(self, full_prompt: str, width: int, height: int, output_path,
                      prompt: str, style: str, start: float) -> Optional[dict]:
        """Stable Diffusion LOCAL en GPU (sd-turbo, offline). None si no disponible.

        Carga el pipeline una sola vez (cacheado en VRAM). La PRIMERA llamada baja
        el modelo (~2.5GB) desde HuggingFace; después es 100% offline."""
        global _SD_PIPE
        try:
            import torch
            if not torch.cuda.is_available():
                return None
            from diffusers import AutoPipelineForText2Image
        except Exception:
            return None
        try:
            if _SD_PIPE is None:
                try:
                    _SD_PIPE = AutoPipelineForText2Image.from_pretrained(
                        "stabilityai/sd-turbo", torch_dtype=torch.float16, variant="fp16")
                except Exception:
                    _SD_PIPE = AutoPipelineForText2Image.from_pretrained(
                        "stabilityai/sd-turbo", torch_dtype=torch.float16)
                _SD_PIPE = _SD_PIPE.to("cuda")
                try:
                    _SD_PIPE.enable_attention_slicing()
                except Exception:
                    pass
            # sd-turbo es nativo 512px → cap para calidad y VRAM (8GB)
            w = min(int(width), 512)
            h = min(int(height), 512)
            image = _SD_PIPE(prompt=full_prompt, num_inference_steps=3,
                             guidance_scale=0.0, width=w, height=h).images[0]
            image.save(str(output_path))
            elapsed = round(time.time() - start, 1)
            result = {
                "success": True, "is_real": True, "path": str(output_path),
                "filename": output_path.name, "prompt": prompt, "style": style,
                "dimensions": f"{w}x{h}",
                "size_kb": round(output_path.stat().st_size / 1024, 1),
                "time_s": elapsed, "method": "stable-diffusion-local (sd-turbo, GPU)",
            }
            self.generated.append(result)
            return result
        except Exception:
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:
                pass
            return None

    def generate_image(self, prompt: str, width: int = 1024, height: int = 1024,
                       style: str = "", filename: str = "") -> dict:
        """
        Genera una imagen usando Pollinations.ai (gratis, sin API key).

        Args:
            prompt: Descripcion de la imagen a generar
            width: Ancho en pixeles
            height: Alto en pixeles
            style: Estilo opcional (realistic, anime, digital-art, oil-painting, etc.)
            filename: Nombre de archivo personalizado

        Returns:
            dict con path, prompt, dimensions, etc.
        """
        start = time.time()

        if style:
            full_prompt = f"{prompt}, {style} style"
        else:
            full_prompt = prompt

        # Generar nombre de archivo
        if not filename:
            safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt[:40]).strip()
            safe_name = safe_name.replace(" ", "_") or "image"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_name}_{timestamp}.png"

        output_path = self.output_dir / "images" / filename

        # 0) Stable Diffusion LOCAL (GPU, offline) — backend principal
        _local = self._try_local_sd(full_prompt, width, height, output_path,
                                    prompt, style, start)
        if _local:
            return _local

        try:
            import urllib.request
            import urllib.parse

            # Pollinations.ai — API gratuita sin key (fallback; hoy da 402)
            encoded_prompt = urllib.parse.quote(full_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"

            req = urllib.request.Request(url)
            req.add_header("User-Agent", "Genesis-AI/5.9")

            with urllib.request.urlopen(req, timeout=60) as response:
                img_data = response.read()

            with open(output_path, "wb") as f:
                f.write(img_data)

            # Validar que de verdad vino una imagen (no HTML de error / paywall)
            if not (img_data[:8].startswith(b"\x89PNG") or img_data[:2] == b"\xff\xd8"):
                raise ValueError("la respuesta no es una imagen (posible paywall/HTML)")

            elapsed = round(time.time() - start, 1)
            result = {
                "success": True,
                "is_real": True,  # imagen IA real
                "path": str(output_path),
                "filename": filename,
                "prompt": prompt,
                "style": style,
                "dimensions": f"{width}x{height}",
                "size_kb": round(len(img_data) / 1024, 1),
                "time_s": elapsed,
                "method": "pollinations.ai",
            }
            self.generated.append(result)
            return result

        except Exception as e:
            # Fallback: generar imagen placeholder con Pillow
            return self._generate_placeholder_image(prompt, width, height, output_path, start, str(e))

    def _generate_placeholder_image(self, prompt: str, width: int, height: int,
                                     output_path: Path, start_time: float,
                                     error_msg: str = "") -> dict:
        """Genera imagen placeholder local con Pillow cuando Pollinations falla."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (width, height), color=(20, 25, 35))
            draw = ImageDraw.Draw(img)

            # Borde cyan estilo Genesis
            for i in range(3):
                draw.rectangle(
                    [i, i, width - 1 - i, height - 1 - i],
                    outline=(0, 255, 255)
                )

            # Texto del prompt
            try:
                font = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 16)
            except Exception:
                font = ImageFont.load_default()
                font_small = font

            # Titulo
            draw.text((width // 2, 30), "GENESIS IMAGE", fill=(0, 255, 255),
                      font=font, anchor="mt")

            # Prompt (word wrap)
            y = 80
            words = prompt.split()
            line = ""
            for word in words:
                test = f"{line} {word}".strip()
                bbox = draw.textbbox((0, 0), test, font=font_small)
                if bbox[2] > width - 40:
                    draw.text((20, y), line, fill=(200, 200, 200), font=font_small)
                    y += 25
                    line = word
                else:
                    line = test
            if line:
                draw.text((20, y), line, fill=(200, 200, 200), font=font_small)

            # Nota de error
            if error_msg:
                draw.text((20, height - 40),
                          f"[Offline: {error_msg[:60]}]",
                          fill=(255, 100, 100), font=font_small)

            img.save(str(output_path))
            elapsed = round(time.time() - start_time, 1)

            result = {
                "success": True,
                "is_real": False,  # NO es una imagen IA real, es un placeholder de texto
                "path": str(output_path),
                "filename": output_path.name,
                "prompt": prompt,
                "dimensions": f"{width}x{height}",
                "time_s": elapsed,
                "method": "pillow_placeholder",
                "warning": "NO es una imagen IA — placeholder de texto. Backend caido: " + error_msg,
            }
            self.generated.append(result)
            return result

        except Exception as e2:
            return {"success": False, "error": f"Error generando imagen: {e2}"}

    def generate_banner(self, text: str, width: int = 1200, height: int = 400,
                        bg_color: tuple = (15, 20, 30),
                        text_color: tuple = (0, 255, 255),
                        filename: str = "") -> dict:
        """Genera un banner/header con texto estilizado (100% local, Pillow)."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"banner_{timestamp}.png"

            output_path = self.output_dir / "images" / filename
            img = Image.new("RGB", (width, height), color=bg_color)
            draw = ImageDraw.Draw(img)

            # Borde
            draw.rectangle([2, 2, width - 3, height - 3], outline=text_color, width=2)

            # Texto centrado
            try:
                font_size = min(width // len(text), height // 3) if text else 40
                font = ImageFont.truetype("arial.ttf", max(font_size, 20))
            except Exception:
                font = ImageFont.load_default()

            draw.text((width // 2, height // 2), text, fill=text_color,
                      font=font, anchor="mm")

            img.save(str(output_path))

            result = {
                "success": True,
                "path": str(output_path),
                "filename": filename,
                "dimensions": f"{width}x{height}",
                "method": "pillow_banner",
            }
            self.generated.append(result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================
    # AUDIO GENERATION (TTS a archivo)
    # =========================================================
    def generate_audio(self, text: str, filename: str = "",
                       voice: str = "es", rate: int = 170,
                       fmt: str = "wav") -> dict:
        """
        Genera audio a partir de texto (TTS).

        Intenta edge-tts (voces naturales) → pyttsx3 (local) como fallback.

        Args:
            text: Texto a convertir en audio
            filename: Nombre del archivo de salida
            voice: Idioma/voz (es, en, etc.)
            rate: Velocidad de habla
            fmt: Formato de salida (wav, mp3)
        """
        start = time.time()

        if not filename:
            safe_text = "".join(c if c.isalnum() or c in " -_" else "" for c in text[:30]).strip()
            safe_text = safe_text.replace(" ", "_") or "audio"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{safe_text}_{timestamp}.{fmt}"

        output_path = self.output_dir / "audio" / filename

        # Intentar pyttsx3 (local, sin internet)
        result = self._tts_pyttsx3(text, str(output_path), voice, rate)
        if result.get("success"):
            result["time_s"] = round(time.time() - start, 1)
            self.generated.append(result)
            return result

        return {"success": False, "error": "No se pudo generar audio. Instala pyttsx3: pip install pyttsx3"}

    def _tts_pyttsx3(self, text: str, output_path: str, voice: str, rate: int) -> dict:
        """TTS con pyttsx3 (100% local)."""
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.setProperty("volume", 0.9)

            # Seleccionar voz por idioma
            voices = engine.getProperty("voices")
            for v in voices:
                if voice.lower() in v.id.lower() or voice.lower() in (v.name or "").lower():
                    engine.setProperty("voice", v.id)
                    break

            engine.save_to_file(text, output_path)
            engine.runAndWait()

            if os.path.exists(output_path):
                size = os.path.getsize(output_path)
                return {
                    "success": True,
                    "path": output_path,
                    "filename": os.path.basename(output_path),
                    "text_length": len(text),
                    "size_kb": round(size / 1024, 1),
                    "method": "pyttsx3",
                    "voice": voice,
                }
            return {"success": False, "error": "pyttsx3 no genero archivo"}
        except Exception as e:
            return {"success": False, "error": f"pyttsx3: {e}"}

    # =========================================================
    # VIDEO GENERATION
    # =========================================================
    def generate_video(self, images: List[str] = None, text: str = "",
                       audio_path: str = "", duration: float = 10.0,
                       fps: int = 24, width: int = 1280, height: int = 720,
                       filename: str = "") -> dict:
        """
        Genera un video simple.

        Modos:
        1. Slideshow: lista de imagenes → video con transiciones
        2. Text-to-video: texto → genera imagen + TTS audio → video
        3. Images + audio: combina imagenes con audio existente

        Args:
            images: Lista de rutas a imagenes
            text: Texto para generar TTS narration
            audio_path: Ruta a audio existente
            duration: Duracion en segundos (si no hay audio)
            fps: Frames por segundo
            width, height: Resolucion
            filename: Nombre del archivo de salida
        """
        start = time.time()

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"genesis_video_{timestamp}.mp4"

        output_path = self.output_dir / "video" / filename

        try:
            import cv2
            import numpy as np
        except ImportError:
            return {"success": False, "error": "OpenCV no instalado. Ejecuta: pip install opencv-python"}

        # Si solo hay texto, generar imagen + audio
        if text and not images:
            # Generar imagen con el texto
            img_result = self._generate_placeholder_image(
                text, width, height,
                self.output_dir / "images" / f"frame_{datetime.now().strftime('%H%M%S')}.png",
                time.time()
            )
            if img_result.get("success"):
                images = [img_result["path"]]

            # Generar audio si no hay
            if not audio_path:
                audio_result = self.generate_audio(text, fmt="wav")
                if audio_result.get("success"):
                    audio_path = audio_result["path"]

        if not images:
            return {"success": False, "error": "Se necesita al menos una imagen o texto para generar video"}

        # Calcular duracion
        if audio_path and os.path.exists(audio_path):
            try:
                import wave
                wf = wave.open(audio_path, "rb")
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / rate if rate > 0 else duration
                wf.close()
            except Exception:
                pass

        # Crear video con OpenCV
        try:
            # Preparar frames
            frames_list = []
            duration_per_image = duration / len(images)

            for img_path in images:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                # Resize manteniendo aspect ratio
                h_orig, w_orig = img.shape[:2]
                scale = min(width / w_orig, height / h_orig)
                new_w, new_h = int(w_orig * scale), int(h_orig * scale)
                resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

                # Crear canvas negro y centrar imagen
                canvas = np.zeros((height, width, 3), dtype=np.uint8)
                y_offset = (height - new_h) // 2
                x_offset = (width - new_w) // 2
                canvas[y_offset:y_offset + new_h, x_offset:x_offset + new_w] = resized

                # Repetir frame por la duracion
                num_frames = int(duration_per_image * fps)
                for _ in range(max(1, num_frames)):
                    frames_list.append(canvas)

            if not frames_list:
                return {"success": False, "error": "No se pudieron cargar las imagenes"}

            # Escribir video temporal sin audio
            temp_video = str(output_path).replace(".mp4", "_temp.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(temp_video, fourcc, fps, (width, height))

            for frame in frames_list:
                writer.write(frame)
            writer.release()

            # Combinar video + audio con ffmpeg
            if audio_path and os.path.exists(audio_path):
                ffmpeg_bin = self._get_ffmpeg_path()
                if ffmpeg_bin:
                    import subprocess
                    cmd = [
                        ffmpeg_bin, "-y",
                        "-i", temp_video,
                        "-i", audio_path,
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        "-shortest",
                        str(output_path)
                    ]
                    subprocess.run(cmd, capture_output=True, timeout=120)
                    # Limpiar temporal
                    try:
                        os.unlink(temp_video)
                    except Exception:
                        pass
                else:
                    # Sin ffmpeg, renombrar video sin audio
                    os.rename(temp_video, str(output_path))
            else:
                # Sin audio, renombrar
                os.rename(temp_video, str(output_path))

            if os.path.exists(str(output_path)):
                elapsed = round(time.time() - start, 1)
                size_mb = round(os.path.getsize(str(output_path)) / (1024 * 1024), 2)
                result = {
                    "success": True,
                    "path": str(output_path),
                    "filename": filename,
                    "duration_s": round(duration, 1),
                    "resolution": f"{width}x{height}",
                    "fps": fps,
                    "frames": len(frames_list),
                    "size_mb": size_mb,
                    "has_audio": bool(audio_path),
                    "time_s": elapsed,
                    "method": "opencv+ffmpeg",
                }
                self.generated.append(result)
                return result

            return {"success": False, "error": "No se pudo generar el archivo de video"}

        except Exception as e:
            # Limpiar temporales
            for tmp in [str(output_path).replace(".mp4", "_temp.mp4")]:
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
            return {"success": False, "error": f"Error generando video: {e}"}

    def _get_ffmpeg_path(self) -> Optional[str]:
        """Obtiene ruta a ffmpeg."""
        import shutil
        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        return None

    # =========================================================
    # STATUS & STATS
    # =========================================================
    def status(self) -> str:
        """Estado del generador de medios."""
        lines = [
            "=== Media Generator ===",
            f"  Directorio: {self.output_dir}",
            f"  Generados esta sesion: {len(self.generated)}",
            f"  Imagen: Pollinations.ai + Pillow local",
        ]

        # Verificar pyttsx3
        try:
            import pyttsx3
            lines.append("  Audio TTS: pyttsx3 (local)")
        except ImportError:
            lines.append("  Audio TTS: NO DISPONIBLE")

        # Verificar OpenCV
        try:
            import cv2
            lines.append(f"  Video: OpenCV {cv2.__version__}")
        except ImportError:
            lines.append("  Video: NO DISPONIBLE (falta opencv)")

        # Verificar ffmpeg
        ffmpeg = self._get_ffmpeg_path()
        lines.append(f"  FFmpeg: {'OK' if ffmpeg else 'NO ENCONTRADO'}")

        return "\n".join(lines)

    def get_stats(self) -> dict:
        return {
            "total_generated": len(self.generated),
            "images": len([g for g in self.generated if "image" in g.get("method", "") or "pillow" in g.get("method", "") or "pollinations" in g.get("method", "")]),
            "audio": len([g for g in self.generated if "tts" in g.get("method", "") or "pyttsx" in g.get("method", "")]),
            "video": len([g for g in self.generated if "opencv" in g.get("method", "") or "video" in g.get("method", "")]),
        }

    def clear(self):
        self.generated.clear()

    def save(self):
        pass  # Estado efimero por sesion

    def load(self):
        pass


# Singleton
media_generator = MediaGenerator()
