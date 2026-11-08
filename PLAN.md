# InvestiQ con Codex — Plan de trabajo (SDD)

> App educativa en español que explica movimientos de acciones/ETF con datos y **fuentes citadas**, enseña conceptos financieros, **clasifica/agrupa instrumentos** para recomendación y compara instrumentos contra las **preferencias del usuario**. Piloto → **20 instrumentos en v0.1**, cobertura objetivo posterior **150 acciones + 50 ETF**.
>
> **No es asesoría financiera.** Todo output lleva disclaimer y trazabilidad de fuente.

**Alcance vigente:** InvestiQ es una app educativa financiera en español. Su interfaz principal es una web local HTML/CSS/JS servida por Python; el motor conserva tools locales para educación, cotizaciones/métricas de símbolos, noticias, filings y exploración guiada. No se incluye Streamlit como código o dependencia activa. Twelve Data y otras fuentes externas son opcionales y su disponibilidad depende de claves, cuota y cobertura. El estado de implementación, cambios recientes y verificaciones se mantiene por separado en [docs/progress.md](docs/progress.md). Consulta también [README](README.md), [arquitectura](docs/architecture.md) y las specs enlazadas por cada feature. Fase 5 sin iniciar.

---

## 0. Supuestos y decisiones (explícitos, revisables en la spec)

| # | Decisión | Justificación | Revisión |
|---|----------|---------------|----------|
| D1 | **Web local HTML/CSS/JS + API mínima en el mismo proceso Python**, sobre la orquestación existente. Streamlit fue retirado como interfaz instalable; su antiguo plan cloud queda solo como registro histórico. Ver [ADR-004](decisions/ADR-004-web-local.md) | Rediseño solicitado; control de conversación y accesibilidad sin Node ni nuevo framework | Hosting de la web se revisa en fase 5 |
| D2 | **Single-user local sin login**; la app abre directamente y guarda preferencias/trazas bajo una identidad local fija | Acceso simple para el piloto educativo local | Auth y multiusuario diferidos |
| D3 | **Noticias del día con caché, fecha y aviso de desactualización** | Marketaux free documentado: 100 req/día, tres artículos/petición y acceso inmediato. ADR-006 corrige el supuesto de 24 h | Condiciones de cuenta y validación live pendientes |
| D4 | **SQLite (local) → Postgres gestionado (Neon free) en nube** vía SQLAlchemy/SQLModel | SQLite no persiste en hosting efímero; capa portable desde el día 1 | — |
| D5 | **yfinance solo ingesta batch para ML** (offline), nunca como fuente "oficial" en vivo | yfinance es "research/educational", no respaldado por Yahoo | — |
| D6 | **LLM: ChatNVIDIA (NVIDIA NIM / API Catalog)**, modelo **configurable**. **Único proveedor LLM; claves de datos opcionales y propias** | Free tier amplio, tool-calling y structured output | Fallback / 2º proveedor en v0.2 |
| D7 | **Nube pendiente**: ADR-002 conserva Streamlit Community Cloud + Neon como plan histórico. La web implementada requiere revisar hosting según ADR-004 | El rediseño local no equivale a desplegar ni validar compatibilidad cloud | Fase 5 sin iniciar; no se selecciona otro proveedor aquí |
| D8 | Límites de free tier = **requisitos no funcionales** (caché, cuotas, degradación). **Clave LLM para generación**; Twelve Data/Marketaux/FMP son fuentes **opcionales** y degradables según acceso de cuenta | Twelve Data 8/min·800/día; Marketaux 100/día; SEC ≤10 req/s + User-Agent | — |
| D9 | **v0.1: orquestación en Python plano** (router + tools como funciones puras + cliente ChatNVIDIA, **sin LangGraph/LangChain**). **LangGraph en v0.2** si el flujo lo justifica | Complejidad proporcional. Ver [ADR-001](decisions/ADR-001-orquestacion.md) | LangGraph en v0.2 |
| D10 | **Columna vertebral sin key**: yfinance (histórico/ML) + filings de la SEC. Twelve Data/Marketaux **enriquecen** y degradan si no hay key/cuota | Garantiza app funcional con una sola key (LLM) | — |
| D11 | **ML real (clustering multi-característica)** para "instrumentos similares a X"; **clasificación de volatilidad por umbrales deterministas** (sin ML). Ver [ADR-003](decisions/ADR-003-ml.md) | "Parecido" es multidimensional (justifica ML); "baja/media/alta volatilidad" es estadística simple (no requiere ML) | Features ajustables |
| D12 | **Profesor RAG con documentos revisados locales y TF-IDF**, generación educativa con evidencias y fallback local. Ver [ADR-005](decisions/ADR-005-profesor-rag-local.md) | Ampliar conocimiento mediante documentos; sin servicios de búsqueda alojados ni descargar embeddings | Evaluación de recuperación/generación antes de introducir otra infraestructura |

**Fuentes verificadas** (oct 2026): [ChatNVIDIA/LangChain](https://python.langchain.com/docs/integrations/chat/nvidia_ai_endpoints) · [Twelve Data planes](https://twelvedata.com/docs/) · [Marketaux límites](https://www.marketaux.com/) · [SEC: acceso a datos de filings](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [yfinance README](https://github.com/ranaroussi/yfinance/blob/main/README.md) · [Codex customization](https://developers.openai.com/codex/concepts/customization) · [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) · [Neon free tier](https://neon.tech/). *Contenido reformulado por cumplimiento de licencias.*

---

## 1. Metodología SDD (obligatoria)

Flujo versionado por feature, trazable extremo a extremo:

```
requisitos (EARS + criterios aceptación) → diseño técnico → tareas → implementación → validación
```

- **Spec primero:** criterios de aceptación definidos **antes** de implementar.
- **Trazabilidad:** cada `REQ-xxx` ↔ `TASK-xxx` ↔ verificación (test/manual) ↔ commit.
- **Cambio de alcance:** se actualiza la spec (changelog) antes de codear.
- **Contexto breve:** se conservan specs, decisiones y progreso en documentos cortos del repo (ver §11).

**Estructura de repo (SDD):**
```
.
├── AGENTS.md                      # Config Codex (comportamiento, comandos, guardrails)
├── PLAN.md                        # Este documento (vivo)
├── docs/
│   ├── decisions/ADR-*.md         # Decisiones (1 archivo breve c/u)
│   ├── progress.md                # Estado vigente y registro cronológico de cambios
│   └── agentic-matrix.md          # Matriz comparativa workflows/herramientas
├── specs/
│   └── <feature>/
│       ├── requirements.md        # REQ-xxx en EARS + criterios aceptación
│       ├── design.md              # Arquitectura, modelos, APIs, LLM vs determinista
│       └── tasks.md               # TASK-xxx ↔ REQ ↔ verificación
├── .codex/
│   ├── skills/sdd-feature/        # Skill: andamiar una feature SDD
│   └── agents/dev-agent.md        # Subagente de desarrollo
├── src/investiq/                  # Web Python local + agente, tools y datos
├── ml/                            # Pipeline ML offline + artefactos
└── tests/                         # unit / integration (marcados, ver §9)
```

Una **spec de ejemplo completa** (feature "explicar movimiento diario") está en §13 para arrancar de inmediato.

---

## 2. Entorno Codex + personalización (Resultado 1)

Según capacidades reales de Codex ([customization](https://developers.openai.com/codex/concepts/customization)):

| Artefacto | Qué hace | Entregable |
|-----------|----------|------------|
| **`AGENTS.md`** | Comportamiento global + reglas del proyecto (estilo, comandos build/test, guardrails: no exponer claves, citar fuentes, tratar texto externo como no confiable) | 1 archivo raíz + overrides por subdir |
| **Config (`config.toml`)** | Modelo por defecto, permisos de herramientas, MCP servers | `~/.codex/config.toml` documentado |
| **1 Skill: `sdd-feature`** | Proceso repetible: dado un nombre de feature, genera `requirements/design/tasks` con plantilla EARS y checklist de trazabilidad | `.codex/skills/sdd-feature/SKILL.md` |
| **1 Subagente: `dev-agent`** | Agente de desarrollo para tareas acotadas (implementar un `TASK-xxx`, correr tests, reportar) invocable vía `/agent` | `.codex/agents/dev-agent.md` |

**Criterio de aceptación del entorno:** abrir Codex en el repo → lee `AGENTS.md`, la skill `sdd-feature` genera una spec esqueleto válida, y `dev-agent` ejecuta un `TASK` de ejemplo con tests en verde.

---

## 3. Matriz comparativa de workflows y herramientas agénticas (Resultado 2)

Se entrega `docs/agentic-matrix.md` comparando con criterios: **personalización (AGENTS/skills/subagentes), soporte MCP, tool-calling, control de contexto, costo, encaje con SDD, madurez**.

Ejes: **Codex (elegido)** vs. alternativas de orquestación/flujo (agentes de IDE, frameworks de grafo). Dentro de la app: motor de workflow **evolutivo** — **Python plano en v0.1** y **LangGraph en v0.2** ([ADR-001](decisions/ADR-001-orquestacion.md)). Justifica por qué Codex para *desarrollo* y por qué se difiere el framework de grafos en el *runtime*.

---

## 4. Arquitectura (Resultados 3, 4, 8)

```
┌──────────────────────────────────────────────────────────────┐
│  Web local (ES) — chat, catálogo y memoria                   │
│  API mínima + servicio → answer_turn                         │
└───────────────┬──────────────────────────────────────────────┘
                │ (in-process, mismo proceso Python)
┌───────────────▼──────────────────────────────────────────────┐
│  Orquestación                                                  │
│   v0.1: Python plano (router + funciones + estado Pydantic)    │
│   v0.2: LangGraph (mismo contrato de nodos/tools)              │
│   • Router → {Explicador, Educador, Recomendador, Comparador}  │
│   • Tools (deterministas, funciones puras):                    │
│       market_quote, news, sec_docs,                            │
│       volatility_bucket, similar_instruments, instr_features   │
│   • Guardrails: citación obligatoria, disclaimer, cuotas,      │
│       texto externo tratado como DATO no confiable             │
└───┬───────────────┬───────────────┬───────────────┬───────────┘
    │               │               │               │
 Twelve Data*    Marketaux*       Filings SEC    LLM (ChatNVIDIA)
 (cotización)    (noticias+       (docs ofic.,   (NIM, configurable,
  *opcional       sentim.)         sin key)       ÚNICA key real)
    │             *opcional
 [Capa de datos]  SQLite(local)/Postgres-Neon(nube) + caché (TTL por fuente)
    ▲
 [ML offline]  yfinance → features (vol, corr, beta, sector) →
               scikit-learn (clustering) + umbrales volatilidad → artefactos (joblib)
```

\* Twelve Data y Marketaux son **enriquecimiento opcional**: sin key o sin cuota, la app degrada a yfinance (precio histórico) + aviso, manteniéndose funcional con la sola key del LLM.

### 4.1 ¿Qué necesita LLM y qué debe ser determinista? (Justificación)

| Componente | LLM | Determinista | Por qué |
|-----------|:---:|:---:|---------|
| Redacción de explicaciones en ES, didáctica | ✅ | | Lenguaje natural, adaptación pedagógica |
| Enrutado de intención (router) | ✅* | | *Con fallback de reglas; salida estructurada |
| Preguntas de clarificación (¿qué volatilidad? ¿referencia?) | ✅ | | Diálogo natural; la decisión final es determinista |
| Cotizaciones / precios | | ✅ | Datos de API, cero alucinación |
| Recuperación de noticias y docs SEC | | ✅ | Llamadas API + filtros, fuente citable |
| **Clasificación de volatilidad (baja/media/alta)** | | ✅ | **Umbrales sobre desviación estándar de retornos; sin ML** |
| **Agrupamiento "similares a X" (ML)** | | ✅ | **scikit-learn clustering multi-feature; reproducible y evaluable** |
| Comparación features vs. preferencias | | ✅ | Scoring determinista; LLM solo **narra** el resultado |
| Citación de fuentes / cálculo de métricas | | ✅ | Trazabilidad y auditoría |
| Traducción EN→ES de fuentes | ✅ | | Resume/traduce; **conserva y enlaza la cita original** |
| Cuotas, caché, rate-limit | | ✅ | Infra |

**Regla de oro:** el LLM **explica, pregunta y redacta**; los **números, clasificaciones, fuentes y decisiones** salen de componentes deterministas. El LLM nunca inventa cifras ni fuentes, ni decide la cubeta de volatilidad.

### 4.2 Modelo de datos (núcleo)
`User`, `Session`, `Instrument(symbol, type, name, sector…)`, `UserPreference`, `PriceCacheEntry`, `NewsCacheEntry`, `FilingRef`, `InstrumentFeatures(vol, beta, sector, …)`, `MLClusterRun`, `MLClusterMembership`, `VolatilityBucket`, `QueryLog(trace, sources, tokens, cost)`. Pydantic para validación; SQLModel para portabilidad SQLite↔Postgres.

---

## 5. Integraciones externas + caso MCP (Resultado 6)

| Fuente | Uso | Key | Determinista | Límite (free) → mitigación |
|--------|-----|-----|:---:|-----|
| **yfinance** | **Columna vertebral**: histórico para ML + precio de respaldo | No | ✅ | Offline/batch; no es fuente "oficial" en vivo |
| **Filings SEC** | **Columna vertebral**: documentos oficiales (10-K/10-Q…) | No | ✅ | ≤10 req/s + **User-Agent con contacto** obligatorio |
| **ChatNVIDIA (NIM)** | Redacción/enseñanza | **Sí (única)** | ✅ LLM | Modelo configurable + límite de tokens por request |
| **Twelve Data** | *Enriquecimiento*: cotización en vivo | Opc. | ✅ | 8/min, 800/día → caché TTL + cuota + degradar a yfinance |
| **Marketaux** | Noticias por símbolo, sector o país y día | Opc. | ✅ | 100/día, tres artículos; caché diaria 15 min y por símbolo 6–12 h; fechas y aviso si está vencida |
| **FMP** | Snapshot de once sectores NASDAQ y cierres EOD para calcular variación simple de componentes del S&P 500 | Opc. | ✅ | Acceso dependiente del plan; cuota local 100/día, caché; cobertura y fecha obligatorias; promedio S&P 500 no ponderado |

**Presupuesto de requests (v0.1, 20 instrumentos)** — demuestra que cabe en free tier:
- Precios históricos (yfinance, batch 1 vez/día): 20 símbolos → cero coste de API de pago.
- Twelve Data (si hay key): cotización bajo demanda, **caché TTL 15 min**; con 20 símbolos y uso interactivo normal << 800/día.
- Marketaux (si hay key): noticias **caché TTL 6–12 h** por símbolo y **15 min** para el listado diario por filtros. Las dos rutas comparten una cuota total de 100/día; superar filtros o frecuencia degrada sin excederla. FMP usa una cuota local independiente de 100/día y requiere acceso al endpoint.
- SEC: filings cacheados tras primera descarga; refresco esporádico.

**Caso MCP pertinente:** exponer la consulta de **filings SEC como servidor MCP** para que Codex (desarrollo) y/o el runtime consuman documentos oficiales de forma estandarizada, con límite de frecuencia y User-Agent encapsulados. El servicio es externo al workspace; estandarizarlo vía MCP evita duplicar lógica y da trazabilidad.

---

## 6. App full-stack local con LLM real y seguro (Resultado 4)

- **Secretos:** `.env` + `pydantic-settings`; **nunca** en código ni logs; `.env.example` versionado. **Única key obligatoria: `NVIDIA_API_KEY`**; Twelve Data/Marketaux opcionales.
- **Integración LLM segura:** timeouts, reintentos con backoff, límite de tokens, y **validación de output** (structured output Pydantic) antes de mostrar.
- **Prompt-injection:** el **texto de noticias y filings SEC se trata como DATO no confiable**, nunca como instrucciones. Se encapsula (delimitadores + instrucción de sistema que prohíbe obedecer contenido recuperado) y se valida la salida. Caso de eval dedicado a inyección.
- **Guardrails:** disclaimer financiero en cada respuesta; toda cifra/afirmación con fuente citada; si falta fuente → el agente lo declara, no inventa.
- **Trazabilidad:** `QueryLog` guarda trace, fuentes, tokens y costo por consulta.
- **Datos — retención y backup:** `QueryLog` con política de retención (p. ej. 90 días); caché con TTL y purga; en nube, backups del Postgres gestionado (Neon ofrece point-in-time). **Rotación de claves:** documentada; `NVIDIA_API_KEY` rotable vía variable de entorno sin redeploy de código.

---

## 7. Agente con herramientas + workflow multiagente (Resultado 7)

**Orquestación evolutiva** — mismos nodos y contratos de tools en ambas versiones, cambia solo el motor:
- **v0.1 — Python plano:** `router()` (LLM + fallback reglas) despacha a funciones; estado en Pydantic. Sin framework. Fácil de depurar y testear.
- **v0.2 — LangGraph:** se migra a grafo de estado cuando aparezcan bucles, estado compartido complejo, checkpointing o paralelismo. El contrato de nodos/tools no cambia → migración acotada.

Nodos (idénticos en v0.1 y v0.2):
- **Router** (LLM + fallback reglas) → clasifica intención.
- **Explicador de movimientos:** combina `market_quote` + `news` + `sec_docs` → LLM redacta con fuentes.
- **Educador:** conceptos financieros (LLM) con glosario determinista como *grounding*.
- **Recomendador** (reemplaza al "ML-Consultor"): diálogo de clarificación (LLM pregunta volatilidad objetivo o instrumento de referencia) → llama tools deterministas:
  - `volatility_bucket(target)` → filtra instrumentos de la cubeta **baja/media/alta** (umbrales).
  - `similar_instruments(ref)` → **clustering ML** multi-feature, devuelve los más parecidos a la referencia.
  - LLM **narra** la lista resultante con disclaimer; no la inventa.
- **Comparador:** `instr_features` + `UserPreference` → scoring determinista → LLM explica el match.

**Tools = funciones puras** reutilizables por ambos motores (clave para que la migración v0.1→v0.2 sea barata). Workflow documentado en `specs/*/design.md` con diagrama de estados y contratos de cada tool.

---

## 8. Evaluación, trazabilidad, límites y fallos (Resultado transversal)

| Aspecto | Enfoque y **umbrales concretos** |
|---------|---------|
| **Eval de respuestas LLM** | **15–20 casos dorados** en ES. Aprobación: **100%** con disclaimer presente, **≥90%** con todas las cifras citando fuente (check automatizado: toda cifra en la respuesta debe mapear a un registro de caché/fuente del `QueryLog`), **≥90%** de intención enrutada correctamente, **0** casos donde el agente obedezca una instrucción inyectada. Ejecutable en CI. |
| **Eval de ML** | Clustering: **silhouette ≥ 0.25** (umbral de arranque, ajustable) y **estabilidad** (ARI entre corridas con semillas distintas ≥ 0.6). Volatilidad: validar que los umbrales producen 3 cubetas no vacías y monótonas. Ficha de dataset, semilla fija, artefactos versionados. |
| **Trazabilidad de fuentes** | Cada afirmación → referencia a `PriceCacheEntry`/`NewsCacheEntry`/`FilingRef`; visible en UI, con **enlace a la fuente original** aunque la respuesta esté en español. |
| **Límites de consumo** | Cuota por usuario/día, caché TTL por fuente (ver §5), presupuesto de tokens por request, degradación a yfinance. |
| **Manejo de fallos** | Degradación elegante (fuente caída → aviso + datos cacheados), reintentos con backoff, circuit breaker por proveedor. |

---

## 9. Pruebas: simuladas vs. integraciones comprobadas (Resultado transversal)

- **`tests/unit`** — lógica determinista (umbrales de volatilidad, clustering sobre fixtures, scoring, parsing, caché) con **mocks** de red. Rápidas, en cada commit.
- **`tests/integration`** — golpean APIs **reales** (yfinance, SEC, NIM; Twelve Data/Marketaux si hay key), marcadas `@pytest.mark.integration`, con *rate-limit* y *skip* si no hay credenciales.
- **Diferenciación explícita:** el reporte distingue *"mocked"* de *"verified against live API"*; una feature no se marca "integrada" sin al menos un test real en verde.

---

## 10. Fases de ejecución — local y nube (Resultado 9 + evolución v0.1→v0.2)

### Fase 0 — Bootstrap SDD + Codex (Resultados 1, 2)
`AGENTS.md`, skill `sdd-feature`, subagente `dev-agent`, `docs/agentic-matrix.md`, estructura de specs. **Hito:** entorno Codex reproducible.

### Fase 1 — Spec del piloto (Resultado 3)
`specs/piloto/requirements.md` (REQ en EARS + criterios; ver ejemplo §13), `design.md`, `tasks.md` trazables, lista de **20 instrumentos**. **Hito:** backlog aprobado.

### Fase 2 — Datos + ML offline (Resultados 6, 8)
Capa SQLModel (SQLite), ingesta **yfinance** batch (20 instrumentos), features (vol, corr, beta, sector), **clustering scikit-learn** + **umbrales de volatilidad**, eval ML (silhouette/ARI), artefactos versionados. **Hito:** `similar_instruments` y `volatility_bucket` reproducibles y evaluados.

### Fase 3 — App local full-stack v0.1 (Resultados 4, 7)
**Web local** HTML/CSS/JS y API mínima en el mismo proceso Python, sobre orquestación en **Python plano** (router + tools como funciones puras), ChatNVIDIA configurable, sin login, caché/cuotas, trazabilidad, disclaimers y mitigación de prompt-injection. La interfaz Streamlit anterior fue retirada; ADR-002 conserva únicamente su plan histórico de hosting. Integraciones yfinance/SEC con verificaciones históricas; Twelve Data/Marketaux opcionales. **Arranque local:** `bash run_web.sh` (SQLite). **Hito v0.1:** demo end-to-end con fuentes citadas, **un solo proceso, sin framework de grafos**. La aceptación NIM real sigue pendiente; el rediseño no la acredita.

### Fase 4 — Hardening → v0.2 (evolución)
Debugging guiado por eval, ampliar cobertura de tests, caso **MCP de filings SEC**, (opcional) **extraer FastAPI** como capa API, **commits trazables** por `TASK`. **Hito v0.2:** eval en verde + MCP operativo.

### Fase 5 — Despliegue en nube GRATIS (Resultado 9)

**Sin iniciar.** ADR-004 cambia la entrada local; antes de publicar la nueva web se revisará un hosting compatible. Las opciones siguientes conservan el plan histórico para Streamlit y no constituyen un despliegue de la web nueva.
- **App Streamlit** → **Streamlit Community Cloud** (gratis, target nativo de Streamlit).
- **Datos** → **Neon Postgres (free)**; migración SQLite→Postgres vía SQLModel; `DATABASE_URL` por entorno.
- **ML** → entrenamiento **offline**; se despliegan solo **artefactos** + inferencia ligera.
- **Secretos** → gestionados en los *secrets* de Streamlit Cloud (solo `NVIDIA_API_KEY` obligatoria).
- **Hito nube:** app pública, gratis, con datos persistentes y clave segura.
- **Alternativa documentada** ([ADR-002](decisions/ADR-002-despliegue.md)): contenedor único en Render/Railway (free), o Vercel con API FastAPI separada si en v0.2 se extrae la API.

### Hitos posteriores (orientativos, menor detalle)
Escalar de 20 → 150+50 instrumentos; multiusuario + roles (RBAC); mayor capacidad de noticias si la demanda lo justifica; más proveedores LLM con fallback; ampliación de la suite de eval.

---

## 11. Gestión de contexto (documentos vivos y breves)
- `docs/progress.md`: *estado actual*, verificaciones, pendientes y registro de actualizaciones. Se actualiza cuando cambie el estado del proyecto.
- `decisions/ADR-*.md`: una decisión por archivo, formato corto (ADR-001 orquestación, ADR-002 despliegue, ADR-003 ML).
- `specs/<feature>/*`: fuente de verdad del alcance; cambios → changelog en la spec.
- Regla: el **próximo trabajo** se detalla; los **hitos lejanos** se describen solo lo necesario para orientar.

---

## 12. Trazabilidad (ejemplo de cadena)
`REQ-001 "explicar movimiento diario de un ticker con ≥2 fuentes citadas"` → `design.md §Explicador` → `TASK-003 implementar nodo Explicador` → `tests/integration/test_explicador_live.py` (verified) + caso dorado de eval → commit `feat: explicador (REQ-001)`.

---

## 13. Spec de ejemplo (lista para arrancar) — Feature: "Explicar movimiento diario"

**`specs/explicar-movimiento/requirements.md` (extracto EARS):**

- **REQ-001** — *Cuando* el usuario pregunta por el movimiento del día de un ticker cubierto, *el sistema deberá* devolver una explicación en español que incluya la variación de precio y **al menos 2 fuentes citadas** (precio + noticia o filing).
  - **Criterios de aceptación:**
    1. La variación (%) proviene de una tool determinista (no del LLM).
    2. La respuesta enlaza cada afirmación a `PriceCacheEntry`/`NewsCacheEntry`/`FilingRef`.
    3. Incluye disclaimer "no es asesoría financiera".
    4. Si una fuente no está disponible, la respuesta lo declara explícitamente (degradación), no inventa.
    5. Fuentes en inglés → resumidas al español con enlace al original.
- **REQ-002** — *Si* el ticker no está en los 20 cubiertos, *el sistema deberá* indicarlo y ofrecer la lista de cubiertos.
- **REQ-003** — *Mientras* se exceda la cuota de una API externa, *el sistema deberá* degradar a datos cacheados/yfinance y mostrar aviso de retraso.

**`tasks.md` (extracto, trazable):**

| TASK | REQ | Verificación |
|------|-----|--------------|
| TASK-001 tool `market_quote` (determinista) | REQ-001 | unit (mock) + integration (yfinance live) |
| TASK-002 tool `news`/`sec_docs` con caché y TTL | REQ-001, REQ-003 | unit + integration |
| TASK-003 nodo Explicador + guardrails de cita | REQ-001 | caso dorado de eval |
| TASK-004 degradación por cuota/fuente caída | REQ-003 | unit (simula 402/timeout) |

---

### Seguimiento
El estado detallado y el historial de actualizaciones se mantienen en [docs/progress.md](docs/progress.md).
