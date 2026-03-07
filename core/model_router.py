"""
GENESIS — Multi-Model Router
Enruta diferentes tipos de tareas a modelos/configuraciones optimizadas.

Cada modelo tiene un perfil con capacidades y configuracion optima.
El router decide automaticamente cual modelo usar basado en:
- Template detectado (code, creative, debug, etc.)
- Complejidad estimada del input
- Disponibilidad del modelo

Modelos soportados (locales .gguf):
- dolphin-2.8-mistral-7b: General purpose, sin censura (default)
- mistral-7b-instruct: Instrucciones precisas, mas formal
- qwen2.5-7b-instruct: Multilingual, razonamiento fuerte

Uso:
    router = ModelRouter(models_dir="models/")
    config = router.route("escribe un poema sobre la luna", template_name="creative")
    # config = {model_path, gpu_layers, temperature, context_length, ...}
"""
import os
from pathlib import Path
from typing import Optional


# ============================================================
# Perfil de modelo
# ============================================================
class ModelProfile:
    """Perfil de un modelo con capacidades y configuracion."""

    def __init__(self, name: str, filename: str, strengths: list = None,
                 default_temp: float = 0.7, context_length: int = 4096,
                 gpu_layers: int = 50, priority: int = 5,
                 description: str = ""):
        self.name = name
        self.filename = filename
        self.strengths = strengths or []
        self.default_temp = default_temp
        self.context_length = context_length
        self.gpu_layers = gpu_layers
        self.priority = priority
        self.description = description
        self.available = False  # Se actualiza al escanear

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "filename": self.filename,
            "strengths": self.strengths,
            "default_temp": self.default_temp,
            "context_length": self.context_length,
            "gpu_layers": self.gpu_layers,
            "priority": self.priority,
            "description": self.description,
            "available": self.available,
        }


# ============================================================
# Multi-Model Router
# ============================================================
class ModelRouter:
    """
    Router que selecciona el modelo optimo para cada tarea.
    Escanea el directorio de modelos y mantiene perfiles.
    """

    # Perfiles predefinidos para modelos conocidos
    KNOWN_MODELS = {
        "dolphin-2.8-mistral-7b-v02-Q4_K_M.gguf": ModelProfile(
            name="dolphin",
            filename="dolphin-2.8-mistral-7b-v02-Q4_K_M.gguf",
            strengths=["general", "creative", "code", "uncensored", "debug", "security"],
            default_temp=0.7,
            context_length=8192,
            gpu_layers=50,
            priority=10,
            description="Dolphin 2.8 Mistral 7B — General purpose, sin censura",
        ),
        "mistral-7b-instruct-v0.2.Q4_K_M.gguf": ModelProfile(
            name="mistral",
            filename="mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            strengths=["explain", "analysis", "summarize", "research", "formal"],
            default_temp=0.5,
            context_length=8192,
            gpu_layers=50,
            priority=8,
            description="Mistral 7B Instruct — Instrucciones precisas, formal",
        ),
        "Qwen2.5-7B-Instruct-Q4_K_M.gguf": ModelProfile(
            name="qwen",
            filename="Qwen2.5-7B-Instruct-Q4_K_M.gguf",
            strengths=["code", "analysis", "multilingual", "reasoning", "math"],
            default_temp=0.6,
            context_length=32768,
            gpu_layers=35,
            priority=7,
            description="Qwen 2.5 7B — Multilingual, razonamiento fuerte, 32k context",
        ),
    }

    # Mapeo de templates a strengths preferidos
    TEMPLATE_STRENGTHS = {
        "code": ["code", "reasoning"],
        "debug": ["debug", "code", "analysis"],
        "creative": ["creative", "uncensored"],
        "explain": ["explain", "formal"],
        "analysis": ["analysis", "reasoning"],
        "research": ["research", "formal"],
        "summarize": ["summarize", "formal"],
        "security": ["security", "uncensored"],
    }

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.profiles = {}       # name -> ModelProfile
        self.active_model = None  # nombre del modelo activo
        self.auto_route = True    # routing automatico activado
        self._manual_override = None  # override manual

        # Escanear modelos disponibles
        self.scan_models()

    def scan_models(self) -> int:
        """
        Escanea el directorio de modelos y actualiza perfiles.

        Returns:
            Cantidad de modelos encontrados
        """
        self.profiles = {}

        if not self.models_dir.exists():
            return 0

        for f in self.models_dir.glob("*.gguf"):
            filename = f.name

            if filename in self.KNOWN_MODELS:
                # Usar perfil predefinido
                profile = self.KNOWN_MODELS[filename]
                profile.available = True
            else:
                # Crear perfil generico
                profile = ModelProfile(
                    name=f.stem.lower()[:20],
                    filename=filename,
                    strengths=["general"],
                    description=f"Modelo: {filename}",
                )
                profile.available = True

            self.profiles[profile.name] = profile

        # Establecer modelo activo por defecto (mayor prioridad)
        if self.profiles and not self.active_model:
            best = max(self.profiles.values(), key=lambda p: p.priority)
            self.active_model = best.name

        return len(self.profiles)

    def route(self, user_input: str = "", template_name: str = "") -> dict:
        """
        Decide que modelo y configuracion usar para una tarea.

        Args:
            user_input: input del usuario (para analisis de complejidad)
            template_name: nombre del template detectado

        Returns:
            dict con configuracion: {model_name, model_path, gpu_layers,
                                      temperature, context_length, reason}
        """
        # Override manual tiene prioridad
        if self._manual_override and self._manual_override in self.profiles:
            profile = self.profiles[self._manual_override]
            return self._build_config(profile, "Seleccion manual")

        # Si auto_route esta desactivado, usar modelo activo
        if not self.auto_route or not template_name:
            if self.active_model and self.active_model in self.profiles:
                profile = self.profiles[self.active_model]
                return self._build_config(profile, "Modelo por defecto")
            # Fallback al primero disponible
            for p in self.profiles.values():
                if p.available:
                    return self._build_config(p, "Fallback")
            return self._empty_config("No hay modelos disponibles")

        # Routing automatico por template
        target_strengths = self.TEMPLATE_STRENGTHS.get(template_name, ["general"])

        # Puntuar cada modelo por coincidencia de fortalezas
        best_profile = None
        best_score = -1

        for profile in self.profiles.values():
            if not profile.available:
                continue
            score = 0
            for strength in target_strengths:
                if strength in profile.strengths:
                    score += 1
            # Bonus por prioridad base
            score += profile.priority * 0.1

            if score > best_score:
                best_score = score
                best_profile = profile

        if best_profile:
            reason = f"Auto-route: template '{template_name}' -> {best_profile.name} (score: {best_score:.1f})"
            return self._build_config(best_profile, reason)

        return self._empty_config("No se encontro modelo adecuado")

    def set_model(self, name: str) -> str:
        """
        Establece manualmente un modelo.

        Args:
            name: nombre del modelo (dolphin, mistral, qwen)

        Returns:
            Mensaje de confirmacion o error
        """
        # Buscar por nombre: primero match exacto, luego parcial por nombre, luego filename
        name_lower = name.lower()
        # Paso 1: match exacto por nombre de perfil
        for profile_name, profile in self.profiles.items():
            if name_lower == profile_name.lower():
                self._manual_override = profile_name
                self.active_model = profile_name
                return f"Modelo establecido: {profile.name} ({profile.description})"
        # Paso 2: match parcial por nombre de perfil
        for profile_name, profile in self.profiles.items():
            if name_lower in profile_name.lower():
                self._manual_override = profile_name
                self.active_model = profile_name
                return f"Modelo establecido: {profile.name} ({profile.description})"
        # Paso 3: match parcial por filename
        for profile_name, profile in self.profiles.items():
            if name_lower in profile.filename.lower():
                self._manual_override = profile_name
                self.active_model = profile_name
                return f"Modelo establecido: {profile.name} ({profile.description})"

        available = ", ".join(p.name for p in self.profiles.values())
        return f"Modelo '{name}' no encontrado. Disponibles: {available}"

    def set_auto(self) -> str:
        """Activa routing automatico."""
        self._manual_override = None
        self.auto_route = True
        return "Routing automatico activado. El modelo se seleccionara segun la tarea."

    def toggle_auto(self) -> str:
        """Alterna routing automatico."""
        self.auto_route = not self.auto_route
        if self.auto_route:
            self._manual_override = None
            return "Auto-routing ACTIVADO"
        return "Auto-routing DESACTIVADO — usando modelo fijo"

    def list_models(self) -> str:
        """Lista todos los modelos disponibles con detalles."""
        if not self.profiles:
            return "No hay modelos disponibles en: " + str(self.models_dir)

        lines = ["=== Modelos Disponibles ==="]
        for name, p in sorted(self.profiles.items(), key=lambda x: -x[1].priority):
            active = " [ACTIVO]" if name == self.active_model else ""
            manual = " [MANUAL]" if name == self._manual_override else ""
            status = "OK" if p.available else "NO DISPONIBLE"
            lines.append(f"\n  {p.name}{active}{manual} ({status})")
            lines.append(f"    Archivo: {p.filename}")
            lines.append(f"    Descripcion: {p.description}")
            lines.append(f"    Fortalezas: {', '.join(p.strengths)}")
            lines.append(f"    GPU layers: {p.gpu_layers} | Context: {p.context_length} | Temp: {p.default_temp}")
            lines.append(f"    Prioridad: {p.priority}")

        lines.append(f"\n  Auto-routing: {'SI' if self.auto_route else 'NO'}")
        return "\n".join(lines)

    def status(self) -> str:
        """Estado resumido del router."""
        total = len(self.profiles)
        available = sum(1 for p in self.profiles.values() if p.available)
        active = self.active_model or "ninguno"
        mode = "automatico" if self.auto_route else "manual"
        override = self._manual_override or "ninguno"

        return (f"ModelRouter: {available}/{total} modelos | "
                f"Activo: {active} | Modo: {mode} | Override: {override}")

    # --- Internos ---

    def _build_config(self, profile: ModelProfile, reason: str) -> dict:
        """Construye dict de configuracion desde un perfil."""
        return {
            "model_name": profile.name,
            "model_path": str(self.models_dir / profile.filename),
            "gpu_layers": profile.gpu_layers,
            "temperature": profile.default_temp,
            "context_length": profile.context_length,
            "reason": reason,
        }

    def _empty_config(self, reason: str) -> dict:
        """Config vacia cuando no hay modelos."""
        return {
            "model_name": "",
            "model_path": "",
            "gpu_layers": 0,
            "temperature": 0.7,
            "context_length": 4096,
            "reason": reason,
        }
