# GENESIS — Aviso Legal

## Propiedad Intelectual
- GENESIS es software propietario desarrollado para uso personal.
- Todo el código fuente, arquitectura, diseño y documentación son propiedad del autor.
- Queda prohibida la reproducción, distribución o modificación sin autorización expresa.

## Disclaimer
- GENESIS es un asistente de IA experimental para uso personal y educativo.
- Las respuestas generadas por IA pueden contener errores. Siempre verificar información crítica.
- El autor no se responsabiliza por decisiones tomadas basándose en outputs de GENESIS.
- GENESIS accede al sistema local del usuario con los permisos que este le otorga.
- Los modelos locales (Llama 3.1, Qwen 2.5 Coder) están sujetos a sus respectivas licencias upstream (Llama Community License, Apache 2.0 / Qwen License). Cumplir los términos de uso de cada modelo descargado.

## Privacidad y Datos
**Desde v6.0 (Digital Sovereignty), GENESIS corre 100% local por defecto.** Esto significa:

- **Sin API externa requerida**: con Ollama corriendo, GENESIS no envía prompts a ningún servicio externo.
- **Soberanía de datos**: toda la inferencia ocurre en la GPU local del usuario. Los prompts, respuestas, memoria y embeddings nunca salen de la máquina.
- **Fallback opcional**: si el usuario configura `GOOGLE_API_KEY`, `OPENAI_API_KEY` o `ANTHROPIC_API_KEY` en `.env`, esos servicios se usan SOLO cuando Ollama falla (circuit breaker abierto). El usuario puede desactivarlos quitando las keys.
- **Búsquedas web**: DuckDuckGo se consulta cuando el usuario lo pide explícitamente o cuando el sistema auto-investiga (puede desactivarse via config).
- **Datos locales**: conversación, memoria, evolución y configuración se almacenan en el directorio del proyecto bajo `memory_data/`, `evolution_data/`, `backups/`.
- **API keys**: se almacenan en `.env` (excluido de git via `.gitignore`) y nunca se loguean, imprimen o transmiten.
- **Cookies/sesiones**: el desktop app no usa cookies. La Web UI usa sesión local de Flask sin persistencia.

## Modelos LLM Locales
- **Genesis/Llama 3.1 8B Q4_K_M** (~4.58GB): conversación general, basado en Llama 3.1 de Meta. Licencia: [Llama Community License](https://www.llama.com/llama3_1/license/).
- **Qwen 2.5 Coder 7B Q4_K_M** (~4.36GB): tareas de código, basado en Qwen 2.5 de Alibaba. Licencia: [Qwen License](https://huggingface.co/Qwen/Qwen2.5-Coder-7B/blob/main/LICENSE).
- Descargados vía Ollama (https://ollama.com). Almacenados en `~/.ollama/models/`.
- Los modelos son propiedad de sus respectivos autores — GENESIS los USA pero no los redistribuye.

## Retención de Datos
- **Logs**: Rotación automática cada 5MB, máximo 3 archivos de respaldo.
- **Memoria a largo plazo**: Persistente hasta que el usuario la borre (`/limpiar memoria`).
- **Backups**: Automáticos cada 25 interacciones, almacenados en `backups/`.
- **Historial de conversación**: Memoria de corto plazo se resume automáticamente al llenarse.
- **Datos de evolución**: `evolution_data/` mantiene historial de versiones de comportamiento.
- **Telemetría del ProviderRouter** (v6.0): `calls_by_provider`, `calls_by_model`, `last_model_used`, `circuit_breaker.status()` — todo local, nunca se transmite.

## Uso de APIs de Terceros (OPCIONAL)
Las APIs externas solo se usan si el usuario configura las keys correspondientes. Por defecto (100% local), NINGUNA se usa.

| Servicio | Estado default | Datos enviados | Propósito |
|----------|---------------|---------------|-----------|
| **Ollama (local)** | **ACTIVO** | Prompts de usuario (loopback 127.0.0.1) | Inferencia LLM local, sin salida a internet |
| Google Gemini | Opcional | Prompts de usuario | Fallback si Ollama cae (requiere `GOOGLE_API_KEY`) |
| OpenAI | Opcional | Prompts de usuario | Fallback alternativo (requiere `OPENAI_API_KEY`) |
| Anthropic | Opcional | Prompts de usuario | Fallback alternativo (requiere `ANTHROPIC_API_KEY`) |
| DuckDuckGo | Opcional | Queries de búsqueda | Investigación web (solo si el usuario lo pide) |

## Estrategia de Routing (ProviderRouter)
`GENESIS_LLM_STRATEGY` controla el orden de failover:
- `local_first` (default): Ollama → Gemini → OpenAI → Anthropic
- `quality_first`: Anthropic → OpenAI → Gemini → Ollama
- `cost_first`: Ollama → Gemini → OpenAI → Anthropic
- `speed_first`: Gemini → Ollama → OpenAI → Anthropic

**Implicación de privacidad**: solo `local_first` y `cost_first` priorizan Ollama (sin salida a internet para inferencia). Las otras estrategias enviarían prompts a terceros primero. Recomendación: mantener default `local_first` salvo que se necesite explícitamente otra cosa.

## Seguridad
- **API keys**: únicamente en `.env`. Nunca en logs, commits, ni en mensajes al usuario.
- **Circuit breaker**: bloquea providers que fallan repetidamente para evitar spam de requests / costos inesperados.
- **Rate limiting**: Token Bucket en `core/rate_limiter.py` evita abuso.
- **Ejecución con timeout**: todas las llamadas LLM tienen límite de tiempo configurable.
- **Sandbox**: ejecución de código del usuario vía `core/safe_io.py` con validación de path.

## Contacto
Para consultas sobre este software, contactar al autor directamente.

---
*Última actualización: 2026-04-17 (v6.0.0 — Digital Sovereignty)*
