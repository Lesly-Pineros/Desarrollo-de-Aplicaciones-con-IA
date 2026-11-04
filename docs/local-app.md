# App local de InvestiQ

La guía de instalación y los comandos de consola se mantienen en el [README principal](../README.md). El arranque recomendado es `bash run_streamlit.sh`: resuelve la raíz del repositorio dinámicamente y permite ejecutar copias ubicadas en rutas distintas.

La interfaz Streamlit envía los turnos a `conversation.answer_turn` en el mismo proceso. Abre sin login; las preferencias se definen y corrigen en el chat. La izquierda explica la app, muestra los símbolos consultables y permite ver, desactivar o borrar el recuerdo resumido.

La fachada de conversación coordina comandos, preferencias y aclaraciones. Las consultas de dominio pasan a `orchestration.answer_query`, que delega en router, handlers, construcción de respuesta y registro. La [guía de arquitectura](architecture.md) explica estos límites y cómo ampliar el agente.

## Configuración y datos

App y pipeline leen `DATABASE_URL` desde las variables de entorno y `.env`, con prioridad del entorno. SQLite usa por defecto `investiq.db` en la raíz cuando se utiliza el lanzador. Cada copia del repo mantiene su propia base, configuración y entorno Python.

`all --period 2y` hace ingesta y entrenamiento; no hay que ejecutar `train` de nuevo después. `train` sirve para recalcular sobre precios que ya estén en la base, sin descarga. Las consultas de similitud necesitan tanto el artefacto aprobado como las features y su registro en SQLite. Véase [ml/README.md](../ml/README.md).

## Memoria y trazas

Las preferencias se guardan bajo la identidad `local`, compartida por la instalación. El historial literal permanece en la sesión; el recuerdo opcional entre visitas guarda solo contexto estructurado y expira según `CONVERSATION_MEMORY_DAYS` (90 por defecto). Borrar contexto conserva las preferencias hasta que la persona pida borrarlas.

`QueryLog` conserva metadatos, herramientas, fuentes y consumo disponible; no guarda texto de consulta ni credenciales. La purga se aplica con la política de retención configurada al registrar respuestas. `ResponseTrace` registra categorías seguras de ruta, narración y respaldo. `INVESTIQ_SHOW_DIAGNOSTICS=true` permite consultarlas en la interfaz de desarrollo.

## Verificación local y en vivo

Sin NVIDIA siguen disponibles las rutas y datos locales. La suite offline utiliza SQLite temporal y respuestas simuladas; no acredita proveedores reales. Cubre rutas, transiciones de diálogo, procedencia de preferencias, trazas y AppTest de Streamlit. El estado y la evidencia de ejecución se mantienen en [PLAN.md](../PLAN.md) y [las tareas de modularización](../specs/agente-modular/tasks.md).

El diagnóstico `tools/verify_agent.py` requiere `--live --key-rotated` para llamar a NVIDIA, únicamente en el entorno autorizado con internet y después de reemplazar la clave expuesta. SEC requiere `SEC_USER_AGENT` con contacto real. Los comandos completos están en el README.

## MCP SEC

`.venv/bin/python -m investiq.mcp_sec` inicia por stdio la herramienta `sec_filings`. Reutiliza cliente SEC, caché, User-Agent y rate limit de la app. La configuración de cliente está descrita en [docs/codex-config.md](codex-config.md).
