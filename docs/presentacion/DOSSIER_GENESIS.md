# GENESIS
## Asistente de Inteligencia Artificial Personal, 100% Local

**Dossier de presentación del proyecto**
Versión del documento: 1.0 — Junio 2026
Autor: Alex Quiñones

---

## 1. Resumen ejecutivo

**GENESIS** es un asistente de inteligencia artificial de uso personal que funciona
**íntegramente en la computadora del usuario**, sin depender de servicios en la nube ni de
APIs externas de pago. A diferencia de los asistentes comerciales (que envían cada
conversación a servidores de terceros), GENESIS procesa el lenguaje, genera imágenes,
sintetiza voz y controla el sistema operativo **de forma local y privada**.

El proyecto materializa una idea concreta: **soberanía digital personal** — que una persona
pueda tener un asistente potente sin entregar sus datos, sin pagar suscripciones y sin
conexión obligatoria a internet.

GENESIS está desarrollado en Python (~146 módulos, ~96.000 líneas de código), corre sobre
modelos de lenguaje locales (Ollama) y ofrece una aplicación de escritorio con una interfaz
tipo "JARVIS". Es un proyecto en evolución continua, documentado versión por versión, con
una suite de pruebas amplia y una arquitectura pensada para escalar.

> **En una frase:** un "JARVIS" personal que piensa, ve, habla, crea y actúa sobre tu
> computadora — todo local, privado y bajo tu control.

---

## 2. El problema

Los asistentes de IA actuales presentan limitaciones estructurales para el usuario:

| Problema | Impacto |
|---|---|
| **Dependencia de la nube** | Cada interacción viaja a servidores de terceros; sin internet no funcionan. |
| **Privacidad comprometida** | Conversaciones, archivos y hábitos quedan en manos de las empresas. |
| **Costos recurrentes** | Suscripciones mensuales y cobros por uso de API. |
| **Caja negra** | El usuario no controla el modelo, sus límites ni sus datos. |
| **Capacidad de acción limitada** | La mayoría solo conversa; no controlan realmente el equipo. |

En un contexto de creciente preocupación por la privacidad y la **soberanía tecnológica**,
existe una necesidad real de alternativas que devuelvan el control al usuario.

---

## 3. La solución: GENESIS

GENESIS responde a cada uno de esos problemas:

- **100% local** → funciona sin internet; los datos nunca salen del equipo.
- **Privado por diseño** → secretos y datos personales nunca se transmiten ni se versionan.
- **Sin costos recurrentes** → no requiere API keys ni suscripciones.
- **Abierto y controlable** → el usuario elige y administra los modelos.
- **Capacidad de acción real** → controla apps, hardware, archivos y dispositivos.

### Capacidades actuales (operativas)

**🧠 Inteligencia**
- Modelos de lenguaje locales vía Ollama (Llama 3.1 8B personalizado + Qwen 2.5 Coder 7B).
- Router multi-proveedor con *failover* automático y clasificación de tareas.
- Memoria persistente con recuperación semántica (RAG), aprendizaje y proactividad.
- Auto-mejora de código **segura** (con barreras de seguridad) y evolución asistida.

**👁️ Sentidos y creación**
- **Voz**: síntesis de voz (22 voces) y **clonación de voz local** (modelo XTTS).
- **Imágenes**: generación local con Stable Diffusion (en GPU, sin servicios externos).
- **Visión**: análisis de imágenes y pantalla.

**🎛️ Acción sobre el sistema**
- Control de volumen, brillo, energía, impresión y múltiples monitores.
- Gestión de conexiones: WiFi, Bluetooth, USB.
- Apertura de aplicaciones y carpetas por nombre; gestión de archivos con papelera segura.
- Reproducción de música y *casting* a TV (Chromecast); integración con apps de streaming.
- Envío y lectura de correo electrónico; despertador con voz y música.

**🖥️ Interfaz**
- Aplicación de escritorio (cabina tipo "JARVIS") con núcleo visual reactivo a la voz.
- Interfaz web local; panel de control con telemetría del sistema.

---

## 4. Diferencial / innovación

| Eje | GENESIS | Asistentes comerciales |
|---|---|---|
| Procesamiento | **Local (tu GPU)** | Nube de terceros |
| Privacidad | **Total** | Datos en servidores externos |
| Conexión | **Funciona offline** | Requiere internet |
| Costo | **Sin suscripción** | Pago mensual / por uso |
| Control del modelo | **Del usuario** | De la empresa |
| Acción en el equipo | **Amplia (sistema, hardware)** | Limitada |
| Evolución | **Auto-mejora documentada** | Cerrada |

El valor diferencial no es un modelo nuevo, sino la **integración local y soberana** de
capacidades de IA de última generación en un único asistente que **actúa** sobre el equipo.

---

## 5. Arquitectura (visión general)

GENESIS está organizado en módulos independientes coordinados por un núcleo:

- **Núcleo / orquestación**: procesa la entrada del usuario, clasifica la intención y
  despacha a la capacidad correspondiente.
- **Motor LLM**: Ollama local con router multi-proveedor (y *fallback* opcional a APIs
  externas si el usuario las habilita).
- **Capacidades** (módulos `core/*.py`): voz, imágenes, control de sistema, conexiones,
  archivos, comunicación, memoria, etc. — cada una aislada y combinable.
- **Interfaz**: app de escritorio (PyWebView) + interfaz web (Flask).
- **Memoria**: corto y largo plazo, con recuperación semántica.

**Principios de diseño:**
1. *Local-first* y privacidad (nada sale del equipo sin pedirlo).
2. Aislamiento por módulo (crecer sin romper lo existente).
3. Barreras de seguridad en la auto-modificación.
4. Degradación grácil (si algo falla, hay *fallback*; nunca se rompe del todo).
5. Verificación empírica antes de declarar "funciona".

**Hardware de referencia:** RTX 3060 Ti (8GB VRAM), Intel i7-13700KF, 16 GB RAM, Windows 11.

---

## 6. Estado del proyecto

- **Madurez**: producto funcional en uso real, en evolución continua.
- **Escala de código**: ~146 módulos, ~96.000 líneas de Python.
- **Calidad**: suite de pruebas amplia (decenas de suites de tests).
- **Trazabilidad**: evolución documentada versión por versión (v1.0 → v6.1).
- **Modelos en producción**: 2 modelos Ollama locales (general + especializado en código).

*(Las cifras provienen de la documentación interna del proyecto, `PROJECT_EVOLUTION.md`.)*

---

## 7. Hoja de ruta (Roadmap)

El proyecto avanza por versiones temáticas. Próxima evolución mayor: **v7.0 "Unbound"**,
organizada en 4 líneas de trabajo:

1. **Conductor** — orquestación inteligente de recursos (GPU) y plataforma de herramientas:
   permite usar voz + imagen + lenguaje simultáneamente sin saturar la memoria de la GPU.
2. **Sentidos en tiempo real** — visión continua (cámara/pantalla) y medios integrados.
3. **Autonomía** — agente que ejecuta tareas de varios pasos por su cuenta.
4. **Alcance** — control remoto y acceso desde el móvil.

El roadmap es un **documento vivo**, pensado para escalar de forma ordenada.

---

## 8. Impacto y aplicaciones

- **Privacidad y soberanía**: alternativa real a los asistentes que dependen de la nube.
- **Accesibilidad**: asistente por voz que controla el equipo (potencial uso en accesibilidad).
- **Educación**: plataforma para aprender IA aplicada, integración de modelos y arquitectura.
- **Productividad**: automatización de tareas cotidianas del escritorio.
- **Independencia tecnológica**: no requiere infraestructura ni proveedores externos.

---

## 9. Equipo y desarrollo

Proyecto desarrollado de forma independiente por **Alex Quiñones**, con metodología de
desarrollo estructurada (análisis → diseño → planificación → desarrollo → pruebas →
documentación) y control de versiones con historial limpio y trazable.

---

## 10. Contacto

**Alex Quiñones**
*(Datos de contacto a completar según la presentación.)*

---

*GENESIS — Inteligencia artificial personal, local y soberana.*
