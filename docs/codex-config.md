# Configuración local de Codex

La configuración personal de Codex vive fuera del repositorio, en `~/.codex/config.toml`; no se versiona porque depende de la instalación y permisos de cada desarrollador. `.codex/config.example.toml` muestra un punto de partida sin fijar un modelo que quizá no esté disponible. Copia solo las opciones que necesites y consulta la documentación de Codex correspondiente a tu versión antes de habilitar herramientas o MCP. Nunca pongas claves en este archivo.

El comportamiento compartido del proyecto está en `AGENTS.md`; la skill y el agente del repo están en `.codex/skills/sdd-feature/` y `.codex/agents/`. Se conserva la cadena requisitos → tareas → verificaciones en `specs/`.

## Skill compartida y ejemplo externo

`sdd-feature` es la skill disponible que se ha utilizado para planear los cambios. [Agent Skills](https://github.com/agentskills/agentskills) es el formato de empaquetado de instrucciones; la organización de GitHub no representa una skill concreta que se pueda instalar.

Se identificó el ejemplo [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator), pero el permiso para descargarlo fue rechazado. La instalación externa está pendiente y no se declara utilizada. La ruta local prevista `/.agents/skills/skill-creator/` está excluida por `.gitignore`; no se excluyen las instrucciones compartidas, las specs o los planes.

Las skills ayudan al desarrollo del repositorio. El tono del agente que usa la persona se configura en `src/investiq/prompts/conversation.md`, cargado por el runtime, junto con sus contratos y validadores.

Para el rediseño web se descargaron y utilizaron Taste, Emil Design Engineering e Impeccable en `.local/design-skills/`, ignorada por Git. Son distintas del ejemplo externo pendiente descrito arriba. Rutas, fuentes y reinstalación en [design-skills.md](design-skills.md). Se acceden por su `SKILL.md` local; no se ha modificado la configuración global ni se requieren al ejecutar la app.

## MCP SEC EDGAR

`.codex/config.example.toml` contiene el bloque `mcp_servers.investiq_sec`. Antes de copiarlo a tu configuración personal, adapta la ruta al repo. El ejemplo usa `uv`; si tu entorno se preparó con los comandos del README, puedes definir `command` con la ruta absoluta a su `.venv/bin/python` y `args = ["-m", "investiq.mcp_sec"]`, manteniendo como directorio de trabajo la raíz de esa copia.

El proceso debe recibir `SEC_USER_AGENT` con nombre y contacto real. El servidor usa stdio; no lo conectes a una consola que mezcle mensajes informales con la salida del protocolo. Las claves permanecen en el entorno o la configuración local de secretos.
