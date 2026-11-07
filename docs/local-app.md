# App local de InvestiQ

La guía de instalación y los comandos de consola están en el [README principal](../README.md). El arranque recomendado es `bash run_web.sh`, en `http://127.0.0.1:8000`: resuelve la raíz dinámicamente y funciona en copias ubicadas en rutas distintas. No requiere Node, compilación, CDN ni un framework frontend. `investiq-app` e `investiq-web` apuntan también a la web tras actualizar la instalación.

La web sirve HTML/CSS/JS y API en un proceso Python. `web/server.py` valida las peticiones y recursos permitidos, `web/service.py` adapta las operaciones a `conversation.answer_turn` y `web/sessions.py` mantiene el contexto temporal. Abre sin login; las preferencias se definen en el chat. El catálogo permite preguntar por un símbolo y la ayuda explica el propósito. En móvil se recogen en un explorador accesible. Véase [ADR-004](../decisions/ADR-004-web-local.md).

La fachada de conversación coordina comandos, preferencias y aclaraciones. Las consultas de dominio pasan a `orchestration.answer_query`, que delega en router, handlers, construcción de respuesta y registro. La [guía de arquitectura](architecture.md) explica estos límites y cómo ampliar el agente.

Para educación, la orquestación consulta la biblioteca RAG de `knowledge/` y el profesor de `tutor/`. Hay 119 documentos con fuentes y fecha de revisión; los pasajes recuperados permiten generar una explicación estructurada con NVIDIA o responder localmente sin modelo. Biblioteca y memoria personal están separadas. Incluye fondos, criptoactivos e indicadores; no calcula indicadores en vivo ni consulta cotizaciones de criptomonedas. Las consultas de líderes sectoriales actuales piden mercado y explican que no hay un ranking actual verificado. Validación, cobertura y cómo añadir documentos en [knowledge.md](knowledge.md).

## Configuración y datos

App y pipeline leen `DATABASE_URL` desde las variables de entorno y `.env`, con prioridad del entorno. SQLite usa por defecto `investiq.db` en la raíz cuando se utiliza el lanzador. Cada copia del repo mantiene su propia base, configuración y entorno Python.

`all --period 2y` hace ingesta y entrenamiento; no hay que ejecutar `train` de nuevo después. `train` sirve para recalcular sobre precios que ya estén en la base, sin descarga. Las consultas de similitud necesitan tanto el artefacto aprobado como las features y su registro en SQLite. Véase [ml/README.md](../ml/README.md).

## Memoria y trazas

Las preferencias y el recuerdo persistente usan la identidad `local`, compartida por instalación. La cookie opaca HttpOnly SameSite=Strict separa los chats temporales, sin separar preferencias persistentes. El historial visible queda temporalmente en el servidor: máximo 80 mensajes, 128 sesiones y dos horas de inactividad. Reiniciar el servidor borra esos chats, no la base. El recuerdo entre visitas guarda solo contexto estructurado y expira según `CONVERSATION_MEMORY_DAYS` (90 por defecto).

«Nueva conversación» y «Olvidar contexto» vacían chat y recuerdo, conservando preferencias y elección de memoria. Se invalidan las copias antiguas de contexto para evitar que otra ventana restaure lo olvidado. Desactivar memoria elimina el resumen persistente; el chat abierto conserva su contexto temporal.

`QueryLog` conserva metadatos, herramientas, fuentes y consumo disponible; no guarda texto de consulta ni credenciales. La purga aplica la retención al registrar respuestas. `ResponseTrace` guarda categorías seguras de ruta, narración y respaldo. La web no expone detalles internos de proveedores.

## Verificación local y en vivo

Sin NVIDIA puedes aprender conceptos y definir símbolos desde el catálogo; consultar movimientos necesita datos locales o acceso a fuentes. La suite offline utiliza SQLite temporal y respuestas simuladas; no acredita proveedores reales. Cubre diálogo, guardrails, API HTTP local y sesiones. La prueba de Chrome verifica interacciones y diseño con otra base temporal y sin proveedores financieros. Evidencia en [PLAN.md](../PLAN.md) y [las tareas de la web](../specs/web-conversacional/tasks.md).

El diagnóstico `tools/verify_agent.py` requiere `--live --key-rotated` para llamar a NVIDIA, únicamente en el entorno autorizado con internet y después de reemplazar la clave expuesta. SEC requiere `SEC_USER_AGENT` con contacto real. Los comandos completos están en el README.

## MCP SEC

`.venv/bin/python -m investiq.mcp_sec` inicia por stdio la herramienta `sec_filings`. Reutiliza cliente SEC, caché, User-Agent y rate limit de la app. La configuración de cliente está descrita en [docs/codex-config.md](codex-config.md).
