# GENESIS — Configuración para Claude Code

## Idioma
- **SIEMPRE responder en español.** Todo: explicaciones, insights, comentarios en código, mensajes de error, nombres de variables descriptivas — todo en español.

## Contexto del Proyecto
- GENESIS es un sistema de IA auto-evolutivo que corre 100% local
- Hardware: RTX 3060 Ti (8GB VRAM), 16GB RAM
- Modelo actual: Dolphin 2.8 Mistral 7B vía ctransformers con CUDA
- NO usar APIs externas (Groq, OpenAI, etc.) — todo debe ser local
- Python 3.10, Windows

## Arquitectura
- `genesis.py` — Motor principal, loop de interacción, Coding Agent Loop
- `core/brain.py` — Cerebro (inferencia LLM local)
- `core/local_engine.py` — Motor de inferencia (ctransformers/llama-cpp)
- `core/memory.py` — Memoria corto/largo plazo + emocional
- `core/evolution.py` — Sistema de evolución (selección por torneo)
- `core/debate.py` — Debate multi-agente
- `core/curiosity.py` — Motor de curiosidad autónoma
- `core/tools.py` — Herramientas (web, archivos, código, auto-modificación)
- `core/code_memory.py` — Memoria de código (soluciones exitosas)
- `core/workspace.py` — Sistema de workspace (proyecto activo)
- `config.py` — Configuración central

## Convenciones
- Comentarios en código: español
- Variables y funciones: snake_case, pueden ser en inglés o español
- Docstrings: español
- Mensajes al usuario: español
- Prints de debug: español
