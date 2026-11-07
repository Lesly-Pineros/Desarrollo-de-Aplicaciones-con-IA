# InvestiQ

InvestiQ es un profesor de educación financiera en una web en español: explica acciones, fondos, ETF, bolsas, brókers, criptoactivos e indicadores consultando una biblioteca local con fuentes. También permite consultar noticias del día, pedir resúmenes y explorar candidatos entre 20 acciones y ETF mediante criterios conversados y el modelo de clustering local. Abre directamente, sin registro ni contraseña. Las preferencias se conversan en el chat; el catálogo y la ayuda están a mano.

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
| `SEC_USER_AGENT` | Nombre de la app y correo real de contacto para consultar filings de la SEC. Sustituye el ejemplo. |
| `DATABASE_URL` | Base local; por defecto `sqlite:///./investiq.db`. App y pipeline leen la misma configuración. |
| `TWELVE_DATA_API_KEY` | Enriquecimiento opcional de cotizaciones. |
| `MARKETAUX_API_KEY` | Clave propia para noticias del día por país, sector o símbolo; sin ella se informa de la falta de fuente. |
| `FMP_API_KEY` | Opcional para snapshots de once sectores de NASDAQ. Acceso dependiente del plan; no se contrata ninguno. |
| `MARKET_TIMEZONE` | Zona IANA para «hoy» en noticias; por defecto `America/Bogota`. |
| `CONVERSATION_MEMORY_DAYS` | Retención del contexto resumido, por defecto 90 días. |
| `INVESTIQ_SHOW_DIAGNOSTICS` | `true` muestra categorías de diagnóstico para desarrollo. Por defecto `false`. |

Las variables exportadas en la consola tienen prioridad sobre `.env`. Conserva `.env` en cada equipo; no se sube a Git.

## Arrancar la app

```bash
bash run_web.sh
```

Abre `http://127.0.0.1:8000`. Detén el proceso con `Ctrl+C`. La web y su API se sirven desde el mismo proceso Python; no necesitas Node, npm ni compilar el frontend. Las fuentes y los estilos están en el repositorio y funcionan sin CDN.

Este es el **frontend gratuito principal**, hecho con HTML, CSS y JavaScript, servido desde Python. Tras instalar o actualizar el paquete, `investiq-app` e `investiq-web` también arrancan esta web. Si tenías una instalación anterior, actualiza sus entradas con `.venv/bin/python -m pip install -e '.[dev]'`; `bash run_web.sh` utiliza directamente el código de esta copia.

El lanzador detecta su propia carpeta, entra en la raíz correcta y utiliza el Python local. Puedes llamarlo desde otra carpeta indicando la ruta al script. Para elegir otro intérprete o puerto:

```bash
INVESTIQ_PYTHON=/ruta/al/entorno/bin/python bash run_web.sh --port 8001
```

`INVESTIQ_PYTHON` tiene prioridad; si no lo defines, se utiliza `.venv/bin/python` y después el Python disponible en la consola.

Puedes empezar con «¿Qué es el sp500?», «¿Qué es AAPL?», «¿Qué es beta?» o «compara AAPL y MSFT». «SP500», «SP 500» y «S&P 500» identifican el mismo tema educativo. Puedes continuar con «un ejemplo» o «más sencillo». Si falta un criterio, el agente lo pregunta en el chat. Una respuesta corta completa la consulta pendiente. También admite «sin preferencias», «qué recuerdas de mí», «olvida el contexto» y «borra mis preferencias».

Para abrir sin llamadas al modelo ni enriquecimientos externos, aunque `.env` tenga claves:

```bash
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= SEC_USER_AGENT= bash run_web.sh
```

Sin Internet puedes aprender conceptos y definir símbolos del catálogo. Las consultas de mercado necesitan datos locales o acceso a sus fuentes; la app informa cuando no están disponibles. La web escucha únicamente en `127.0.0.1` o `localhost`: es un piloto local, no un servidor público.

La aplicación local usa la web HTML/CSS/JS servida por Python; no mantiene una segunda interfaz frontend. Usar esta web local no tiene una tarifa de framework; publicarla en Internet y el consumo de proveedores son cuestiones separadas. No se ha iniciado el despliegue cloud.

## Biblioteca educativa y RAG

Puedes preguntar «¿qué es una acción?», «¿qué brókers existen?», «¿cómo funciona una orden límite?», «¿qué son los dividendos?» o «¿a qué se dedica Apple?». El agente recupera pasajes de documentos revisados y los utiliza para explicar con fuentes; admite ejemplos y distintos niveles de detalle. Si no encuentra respaldo suficiente, lo reconoce.

La biblioteca contiene **119 documentos en 16 categorías**, con 113 referencias. Incluye fondos de inversión, Bitcoin, Ethereum, blockchain, wallets, stablecoins y staking; análisis fundamental y técnico, RSI, MACD, medias móviles, Bollinger, ATR, ADX, estocástico, OBV, CCI y VWAP. También cubre órdenes, derivados, tamaño de posición, drawdown y backtesting. Es una cobertura educativa ampliable, no una garantía de responder cualquier tema ni un generador de señales de compra o venta.

La pregunta «¿qué es mejor para obtener mayores rentabilidades a largo plazo: un ETF o acciones individuales?» recibe una comparación de diversificación, concentración, costes y riesgo, sin prometer un ganador. «¿Qué sectores lideran hoy?» pide mercado y puede consultar un snapshot completo de once sectores de NASDAQ mediante FMP configurado. Declara bolsa, fecha y cobertura; sin acceso o datos válidos informa la limitación. La integración real de ese proveedor sigue pendiente. La biblioteca estática y los pocos ETF del catálogo no permiten afirmar líderes actuales. Si escribes ambas preguntas en un mensaje, atiende la comparación y conserva la aclaración del mercado.

La búsqueda es local, por alias y similitud TF-IDF; no necesita descargar embeddings ni contratar una base vectorial. La redacción con NVIDIA necesita conexión. Sin modelo o ante una salida que no pase la validación, responde con explicaciones y ejemplos locales. Las fuentes citadas no eliminan por sí solas los errores del modelo.

Puedes seguir una lección con «No entiendo», «¿Me lo explicas con un ejemplo?», «¿Cómo se interpreta?» o «¿Por qué importa?». Conserva el tema y sus fuentes, también tras restaurar la memoria; «Ahora explícame la inflación» inicia otro tema. Después de «¿Qué es AAPL?» puedes pedir un ejemplo o sus riesgos desde la ficha educativa, sin consultar precios. «Soy principiante» adapta las explicaciones: conserva la definición y añade el ejemplo revisado, sin guardar preferencias de inversión. Sin un tema previo, el profesor necesita que concretes el concepto.

## Noticias y exploración guiada

Los accesos **Noticias de hoy**, **Recomendaciones guiadas** y **Sectores de hoy · NASDAQ** permanecen visibles junto al chat, también en móvil. Las sugerencias iniciales conducen a esos tres modos. Puedes preguntar «Últimas noticias del sector financiero en Colombia», «Noticias del sector tecnológico» o «Noticias de AAPL». Se muestran hasta tres titulares de hoy por recencia, con publicación y fuente. NVIDIA puede traducirlos y resumir el extracto al pulsar «Resumir noticia 2» o escribir «Resume la segunda». Sin modelo se conserva el original; sin extracto no se inventa un resumen. Los artículos no se guardan en la memoria personal.

Para consultar una acción o ETF, el acceso inicial pregunta **«¿Quieres conocer las métricas de una acción o ETF?»** y luego solicita su símbolo. La ficha reúne cotización, variación, volatilidad anualizada, beta, correlación con instrumentos similares, sector y período de cálculo, con su fuente y fecha cuando están disponibles. La cobertura de mercado es de instrumentos estadounidenses. La cotización puede ser en tiempo real si Twelve Data y el plan de la cuenta lo permiten; si no, la app identifica el dato histórico o demorado. Las métricas calculadas usan precios históricos y no son valores en tiempo real ni predicen resultados. La cotización en tiempo real requiere `TWELVE_DATA_API_KEY` y acceso habilitado por el proveedor.

«¿Qué acción o ETF me recomiendas para invertir hoy?» pregunta tipo, plazo, variación histórica y referencia opcional dentro del chat. Usa el KMeans aprobado y características coherentes; presenta hasta tres candidatos para estudiar con volatilidad anualizada en porcentaje, beta, sector, grupo y fuentes del período histórico. La coincidencia del modelo no es rentabilidad ni probabilidad de ganar, y el tercil de volatilidad no constituye un perfil financiero completo. Los criterios no se guardan automáticamente como preferencias. Sin modelo/datos o coincidencias compatibles, se explica la limitación; el corto plazo no se resuelve presentando acciones o ETF como seguros.

Configuración, cuotas, filtros y límites en [docs/market-branches.md](docs/market-branches.md). Marketaux anuncia actualmente 100 peticiones/día, tres artículos/petición y acceso inmediato en su plan gratuito; se corrigió la antigua suposición de 24 horas de retraso. Las pruebas usan fuentes/modelos simulados y KMeans real con datos sintéticos; no acreditan integración live. Se conserva Python plano y el mismo NVIDIA configurable; no se necesita LangGraph.

Para revisar la biblioteca y comprobar la recuperación sin llamadas externas:

```bash
.venv/bin/python -m investiq.knowledge validate
.venv/bin/python -m investiq.knowledge stats
.venv/bin/python -m investiq.knowledge search 'qué brokers existen para invertir'
.venv/bin/python -m investiq.knowledge search 'qué es una criptomoneda'
.venv/bin/python -m investiq.knowledge search 'qué es el RSI'
```

Los JSON están en `src/investiq/knowledge/data/`. Puedes añadir contenido revisado sin programar otra respuesta. Formato, fuentes, biblioteca externa y actualización en [docs/knowledge.md](docs/knowledge.md). Los brókers se presentan como ejemplos, sin ranking ni recomendaciones personales; país, registro, condiciones y tarifas actuales requieren verificación.

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
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q
```

El comando configurado en `pyproject.toml` recoge `tests/unit`. La suite unitaria también aísla las credenciales mediante un fixture compartido. Incluye lógica local, modelos simulados y la interfaz con SQLite temporal; un resultado en verde no acredita una integración en vivo.

Para comprobar solo los nuevos temas, las dos preguntas propuestas y sus seguimientos:

```bash
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/unit/test_trading_education.py
```

Para comprobar conversaciones completas con aclaraciones, interpretación, ejemplos, cambios de tema, nivel principiante y memoria restaurada:

```bash
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/unit/test_teacher_continuity.py
```

Las pruebas offline cubren la conversación, las tools, los proveedores simulados y la web local. Para ejecutarlas instala `.[dev]`; la integración real de proveedores requiere configuración aparte.

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

Consulta el estado vigente y el historial de cambios en [docs/progress.md](docs/progress.md). El alcance y las decisiones están en [PLAN.md](PLAN.md); la trazabilidad por feature está en las specs de [profesor RAG](specs/profesor-rag/tasks.md), [formación](specs/formacion-trading/tasks.md), [continuidad del profesor](specs/continuidad-profesor/tasks.md) y [web](specs/web-conversacional/tasks.md). Los resultados offline y las integraciones en vivo se registran por separado.

## Verificar la web en Chrome

Esta comprobación opcional necesita Node 22 o superior y Chrome instalado. Son herramientas de prueba, no requisitos para arrancar la app:

```bash
node tools/check_web.mjs
```

El script inicia servidores y bases SQLite temporales, desactiva las credenciales y prueba la conversación y controles en Chrome headless. Las ramas nuevas usan noticias/snapshots sintéticos y un KMeans real entrenado sobre fixtures; no se utiliza la base ni los modelos del usuario. Cierra los procesos al terminar. No debes arrancar la app primero. Necesita permiso para abrir puertos locales. Las capturas y el informe quedan en `.impeccable/review/`, excluida de Git. Si Chrome está en otra ubicación, indica su ejecutable con `CHROME_PATH=/ruta/a/chrome` antes del comando. No sustituye una prueba con el modelo real.

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

Las preferencias se conservan en la base bajo una identidad local compartida por esta instalación. El recuerdo opcional entre visitas guarda tema, símbolos, consulta pendiente y nivel de explicación; excluye el historial literal y los precios antiguos. Puedes verlo, desactivarlo o borrarlo desde los controles de memoria o por chat. Borrar contexto y borrar preferencias son acciones distintas. «Nueva conversación» vacía el chat y su contexto; conserva las preferencias y la elección de activar o desactivar memoria.

El historial visible permanece temporalmente en el servidor local, asociado a una cookie de sesión opaca; no se guarda en localStorage. La sesión expira tras dos horas de inactividad y el servidor mantiene un máximo de 128 sesiones y 80 mensajes por sesión. Las pestañas del mismo navegador comparten cookie; la memoria persistente sigue siendo común a la instalación. `QueryLog` registra intención, herramientas, fuentes y consumo disponible, no el texto de tus consultas; su retención objetivo es de 90 días. `ResponseTrace` conserva categorías seguras para distinguir narración y respuestas de respaldo.

## Cómo está organizado el agente

`web/server.py` sirve archivos y API; `web/service.py` adapta las operaciones del chat y `web/sessions.py` mantiene el estado temporal. `conversation.answer_turn` recibe cada turno y coordina el contexto con los componentes de `dialogue/`: comandos, estado pendiente y preferencias. `orchestration.answer_query` coordina la consulta financiera: `routing.py` elige la ruta, `handlers.py` ejecuta las herramientas, `responses.py` construye la respuesta y `query_log.py` registra sus metadatos una sola vez. La redacción con el modelo se valida antes de mostrarse.

La [guía de arquitectura](docs/architecture.md) describe las responsabilidades, la memoria y cómo añadir una capacidad conservando las comprobaciones deterministas. Las skills son guías de desarrollo; la conversación del producto se implementa en estos módulos y en sus prompts.

## Desarrollar y ejecutar en dos copias

Lleva al equipo de ejecución el código actualizado completo, incluidos `src/investiq/prompts/`, `src/investiq/knowledge/data/`, `src/investiq/web/static/` (con sus fuentes y licencias), `pyproject.toml`, `run_web.sh` y las herramientas. Prepara allí su entorno Python y su `.env`; las carpetas `.venv`, las claves y SQLite son locales. Las copias del repositorio no sincronizan conversaciones, preferencias o datos automáticamente.

Git excluye `.env`, `.venv` y la SQLite local predeterminada. Los artefactos de `ml/artifacts/` sí forman parte del repositorio. En una copia nueva, carga sus datos con `all`; si trasladarás una base existente, conserva una copia de respaldo y usa el mismo conjunto de base y artefactos.

## Servidor MCP de filings SEC

Desde la raíz, con `SEC_USER_AGENT` real configurado:

```bash
.venv/bin/python -m investiq.mcp_sec
```

El proceso espera mensajes MCP por entrada estándar; su salida está reservada al protocolo. Expone `sec_filings` y reutiliza la caché, los límites y el cliente SEC de la app. Para conectarlo a Codex, adapta el bloque de [.codex/config.example.toml](.codex/config.example.toml) a la ruta local y al intérprete de esa copia. Guía de configuración en [docs/codex-config.md](docs/codex-config.md).

## Skills de desarrollo

Las tres skills de diseño solicitadas están **descargadas localmente y utilizadas**: Taste, Emil Design Engineering e Impeccable, en `.local/design-skills/`. Esa carpeta está excluida de Git; no es necesaria para ejecutar la aplicación. Impeccable guía la interfaz, Taste la composición y Emil los detalles de interacción. Los orígenes, reinstalación y límites de sus herramientas están en [docs/design-skills.md](docs/design-skills.md).

Se utilizaron [.codex/skills/sdd-feature/SKILL.md](.codex/skills/sdd-feature/SKILL.md), versionada en este repositorio, y `skill-creator`, disponible en el entorno de desarrollo. Orientan la especificación, las instrucciones y su validación; la app funciona independientemente de su instalación en el equipo de ejecución.

El formato [Agent Skills](https://github.com/agentskills/agentskills) describe cómo empaquetar estas instrucciones. La creación de una nueva skill local `investiq-agent-review` quedó bloqueada por el permiso de escritura de `.agents/skills`, y la autorización fue rechazada: esa skill no se creó ni se utilizó. La descarga del ejemplo externo [skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) también quedó pendiente por el rechazo del permiso de red; es distinta de la skill ya disponible en el entorno. `.gitignore` reserva `/.agents/skills/skill-creator/` para aquella instalación local.

La clonación del repositorio solicitado `https://github.com/agentskills/agentskills.git` también quedó pendiente por el permiso del entorno. Para descargar esa referencia desde un equipo autorizado con internet, ejecuta desde la raíz:

```bash
git clone --depth 1 https://github.com/agentskills/agentskills.git .local/agentskills-reference
```

`.local/agentskills-reference/` está excluido de Git. Puedes trasladar esa carpeta completa desde el equipo conectado a la misma ruta de la copia de desarrollo. El repositorio contiene la especificación y `skills-ref`, la biblioteca de referencia para validar skills; su descarga no instala automáticamente una skill de revisión. La modularización previa se realizó con las skills entonces disponibles y su alcance está documentado en [specs/agente-modular](specs/agente-modular/requirements.md). Esa referencia pendiente es distinta de las tres skills de diseño ahora instaladas.
