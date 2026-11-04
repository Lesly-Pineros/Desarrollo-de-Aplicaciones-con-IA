# InvestiQ

InvestiQ es una app educativa en español para entender conceptos financieros, consultar movimientos con sus fuentes y explorar similitudes o comparaciones entre 20 acciones y ETF. Abre directamente, sin registro ni contraseña. Las preferencias se conversan en el chat y la izquierda muestra ayuda y símbolos disponibles.

**No es asesoría financiera.** Los precios y las métricas provienen de herramientas y datos verificables; el modelo redacta sobre esos resultados.

## Preparar el entorno

Usa Python 3.11 o superior. Ejecuta los comandos desde la raíz del repositorio. La primera instalación de dependencias requiere conexión; si ya tienes un entorno preparado, pasa al arranque.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Crea tu configuración local solo si aún no existe:

```bash
if [ ! -f .env ]; then
  cp .env.example .env
fi
```

Edita `.env` en tu equipo:

| Variable | Uso |
|---|---|
| `NVIDIA_API_KEY` | Activa clasificación y redacción con NVIDIA. Sin ella funciona el modo local disponible. |
| `NVIDIA_MODEL` | Modelo solicitado al proveedor; debe estar disponible para tu cuenta. |
| `SEC_USER_AGENT` | Nombre de la app y correo real de contacto para consultar SEC EDGAR. Sustituye el ejemplo. |
| `DATABASE_URL` | Base local; por defecto `sqlite:///./investiq.db`. App y pipeline leen la misma configuración. |
| `TWELVE_DATA_API_KEY`, `MARKETAUX_API_KEY` | Enriquecimiento opcional de cotizaciones y noticias. |
| `CONVERSATION_MEMORY_DAYS` | Retención del contexto resumido, por defecto 90 días. |
| `INVESTIQ_SHOW_DIAGNOSTICS` | `true` muestra categorías de diagnóstico para desarrollo. Por defecto `false`. |

Las variables exportadas en la consola tienen prioridad sobre `.env`. Conserva `.env` en cada equipo; no se sube a Git.

## Arrancar la app

```bash
bash run_streamlit.sh
```

Abre la dirección local que indique Streamlit, normalmente `http://localhost:8501`. Detén el proceso con `Ctrl+C`.

El lanzador detecta su propia carpeta, entra en la raíz correcta y utiliza el Python local. Puedes llamarlo desde otra carpeta indicando la ruta al script. Para elegir otro intérprete o puerto:

```bash
INVESTIQ_PYTHON=/ruta/al/entorno/bin/python bash run_streamlit.sh --server.port 8502
```

`INVESTIQ_PYTHON` tiene prioridad; si no lo defines, se utiliza `.venv/bin/python` y después el Python disponible en la consola.

Puedes empezar con «¿Qué es beta?», «precio AAPL» o «compara AAPL y MSFT». Si falta un criterio, el agente lo pregunta en el chat. Una respuesta corta completa la consulta pendiente. También admite «sin preferencias», «qué recuerdas de mí», «olvida el contexto» y «borra mis preferencias».

## Cargar datos históricos y entrenar

Para tener precios históricos, features y un modelo de similitud en una instalación nueva, ejecuta en el equipo con internet:

```bash
.venv/bin/python -m investiq.ml.pipeline all --period 2y --seed 42
```

`all` hace la ingesta y el entrenamiento una sola vez. El comando informa las métricas y si el clustering superó los umbrales de aceptación. Si los precios ya están guardados, puedes recalcular el modelo sin descargar datos:

```bash
.venv/bin/python -m investiq.ml.pipeline train --seed 42
```

Los manifiestos y modelos quedan en `ml/artifacts/`. La base contiene precios, features y el registro `MLClusterRun`; copiar solo un `.joblib` no prepara una base vacía para consultas de similitud. Sin datos o modelo aprobados, la app explica la limitación. Más detalles en [ml/README.md](ml/README.md).

## Validar sin acceder a proveedores reales

Este es el comando principal de regresión. Deshabilita las credenciales aunque tu `.env` tenga valores:

```bash
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q
```

El comando configurado en `pyproject.toml` recoge `tests/unit`. La suite unitaria también aísla las credenciales mediante un fixture compartido. Incluye lógica local, modelos simulados y la interfaz con SQLite temporal; un resultado en verde no acredita una integración en vivo.

Para comprobar las especificaciones SDD, el siguiente bucle omite las plantillas y se detiene si encuentra un error:

```bash
(
  for spec_dir in specs/*/; do
    case "$spec_dir" in specs/_templates/) continue ;; esac
    .venv/bin/python tools/validate_spec.py "$spec_dir" || exit 1
  done
  git diff --check
)
```

Consulta el estado real y la trazabilidad en [PLAN.md](PLAN.md) y [specs/agente-modular/tasks.md](specs/agente-modular/tasks.md). Los resultados offline y las integraciones en vivo se registran por separado.

## Comprobar NVIDIA en vivo

Puedes inspeccionar el diagnóstico sin autorizar llamadas externas:

```bash
.venv/bin/python tools/verify_agent.py
```

Sin flags devuelve `status: not_run` y no contacta al proveedor. En la copia con internet, después de sustituir la clave previamente expuesta y configurar la nueva en `.env`, ejecuta:

```bash
.venv/bin/python tools/verify_agent.py --live --key-rotated
```

`--key-rotated` confirma que quien ejecuta ya reemplazó la clave; no realiza la rotación. El informe distingue `passed`, `failed` y `not_run`, y comprueba clasificación y dos turnos educativos. No imprime claves ni las respuestas completas. La naturalidad de toda la app requiere además revisar conversaciones con el modelo real.

Los tests de APIs están en `tests/integration` y requieren `RUN_LIVE_INTEGRATION=1` además de su configuración. Por ejemplo, para comprobar MCP contra SEC en el equipo con internet y contacto real configurado:

```bash
RUN_LIVE_INTEGRATION=1 .venv/bin/python -m pytest -q tests/integration/test_phase4_mcp_sec_live.py
```

La prueba NIM de integración exige también `NVIDIA_KEY_ROTATED=1`; para el diagnóstico habitual utiliza el script anterior. Sin activar las integraciones explícitamente, `pytest -q tests/integration` las omite. Estas pruebas se reportan aparte de la suite offline.

## Memoria y datos locales

Las preferencias se conservan en la base bajo una identidad local compartida por esta instalación. El recuerdo opcional entre visitas guarda tema, símbolos, consulta pendiente y nivel de explicación; excluye el historial literal y los precios antiguos. Puedes verlo, desactivarlo o borrarlo desde «Lo que recuerdo» o por chat. Borrar contexto y borrar preferencias son acciones distintas.

El historial visible pertenece a la sesión de Streamlit. `QueryLog` registra intención, herramientas, fuentes y consumo disponible, no el texto de tus consultas; su retención objetivo es de 90 días. `ResponseTrace` conserva categorías seguras para distinguir narración y respuestas de respaldo.

## Cómo está organizado el agente

`conversation.answer_turn` recibe cada turno y coordina el contexto con los componentes de `dialogue/`: comandos, estado pendiente y preferencias. `orchestration.answer_query` coordina la consulta financiera: `routing.py` elige la ruta, `handlers.py` ejecuta las herramientas, `responses.py` construye la respuesta y `query_log.py` registra sus metadatos una sola vez. La redacción con el modelo se valida antes de mostrarse.

La [guía de arquitectura](docs/architecture.md) describe las responsabilidades, la memoria y cómo añadir una capacidad conservando las comprobaciones deterministas. Las skills son guías de desarrollo; la conversación del producto se implementa en estos módulos y en sus prompts.

## Desarrollar y ejecutar en dos copias

Lleva al equipo de ejecución el código actualizado completo, incluidos `src/investiq/prompts/`, `pyproject.toml`, el lanzador y las herramientas. Prepara allí su entorno Python y su `.env`; las carpetas `.venv`, las claves y SQLite son locales. Las copias del repositorio no sincronizan conversaciones, preferencias o datos automáticamente.

Git excluye `.env`, `.venv` y la SQLite local predeterminada. Los artefactos de `ml/artifacts/` sí forman parte del repositorio. En una copia nueva, carga sus datos con `all`; si trasladarás una base existente, conserva una copia de respaldo y usa el mismo conjunto de base y artefactos.

## Servidor MCP SEC EDGAR

Desde la raíz, con `SEC_USER_AGENT` real configurado:

```bash
.venv/bin/python -m investiq.mcp_sec
```

El proceso espera mensajes MCP por entrada estándar; su salida está reservada al protocolo. Expone `sec_filings` y reutiliza la caché, los límites y el cliente SEC de la app. Para conectarlo a Codex, adapta el bloque de [.codex/config.example.toml](.codex/config.example.toml) a la ruta local y al intérprete de esa copia. Guía de configuración en [docs/codex-config.md](docs/codex-config.md).

## Skills de desarrollo

Se utilizaron [.codex/skills/sdd-feature/SKILL.md](.codex/skills/sdd-feature/SKILL.md), versionada en este repositorio, y `skill-creator`, disponible en el entorno de desarrollo. Orientan la especificación, las instrucciones y su validación; la app funciona independientemente de su instalación en el equipo de ejecución.

El formato [Agent Skills](https://github.com/agentskills/agentskills) describe cómo empaquetar estas instrucciones. La creación de una nueva skill local `investiq-agent-review` quedó bloqueada por el permiso de escritura de `.agents/skills`, y la autorización fue rechazada: esa skill no se creó ni se utilizó. La descarga del ejemplo externo [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) también quedó pendiente por el rechazo del permiso de red; es distinta de la skill ya disponible en el entorno. `.gitignore` reserva `/.agents/skills/skill-creator/` para aquella instalación local.

La clonación del repositorio solicitado `https://github.com/agentskills/agentskills.git` también quedó pendiente por el permiso del entorno. Para descargar esa referencia desde un equipo autorizado con internet, ejecuta desde la raíz:

```bash
git clone --depth 1 https://github.com/agentskills/agentskills.git .local/agentskills-reference
```

`.local/agentskills-reference/` está excluido de Git. Puedes trasladar esa carpeta completa desde el equipo conectado a la misma ruta de la copia de desarrollo. El repositorio contiene la especificación y `skills-ref`, la biblioteca de referencia para validar skills; su descarga no instala automáticamente una skill de revisión. La mejora actual se realizó con las skills disponibles y su alcance está documentado en [specs/agente-modular](specs/agente-modular/requirements.md).
