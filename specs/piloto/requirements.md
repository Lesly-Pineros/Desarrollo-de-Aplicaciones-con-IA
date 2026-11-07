# Requisitos — piloto InvestiQ v0.1

- **Estado:** Backlog aprobado para v0.1; cambio de acceso aprobado por solicitud del usuario (2026-11-04)
- **Objetivo:** app educativa en español que explica movimientos de instrumentos, enseña conceptos financieros, ofrece instrumentos similares y por volatilidad, y compara opciones con preferencias del usuario.
- **Usuarios:** una persona usuaria en una instalación local; la app abre directamente sin login.
- **Alcance:** 20 instrumentos cotizados en EE. UU.; UI Streamlit, orquestación Python simple, tools deterministas, ChatNVIDIA, fuentes citadas y persistencia local SQLite.
- **Exclusiones:** asesoría o ejecución de operaciones, cartera/conexión a broker, cobertura de instrumentos fuera de la lista, multiusuario/roles, despliegue cloud, LangGraph/FastAPI, y dependencia obligatoria de Twelve Data o Marketaux.
- **Datos y frescura:** yfinance para histórico batch de investigación; Twelve Data y Marketaux son opcionales; la SEC es la fuente oficial de filings. La respuesta expone fuente y fecha/hora de los datos.

## Universo aprobado del piloto

La lista se fija para v0.1 y debe compartirse con la canasta de `src/investiq/instruments.py`.

| Símbolo | Tipo | Nombre | Sector/categoría |
|---|---|---|---|
| AAPL | Acción | Apple | Tecnología |
| MSFT | Acción | Microsoft | Tecnología |
| NVDA | Acción | NVIDIA | Tecnología |
| AMZN | Acción | Amazon | Consumo discrecional |
| GOOGL | Acción | Alphabet | Servicios de comunicación |
| META | Acción | Meta Platforms | Servicios de comunicación |
| JPM | Acción | JPMorgan Chase | Financieros |
| XOM | Acción | Exxon Mobil | Energía |
| JNJ | Acción | Johnson & Johnson | Salud |
| WMT | Acción | Walmart | Consumo básico |
| COST | Acción | Costco | Consumo básico |
| TSLA | Acción | Tesla | Consumo discrecional |
| AVGO | Acción | Broadcom | Tecnología |
| BRK-B | Acción | Berkshire Hathaway | Financieros |
| UNH | Acción | UnitedHealth Group | Salud |
| SPY | ETF | SPDR S&P 500 ETF | Mercado amplio |
| QQQ | ETF | Invesco QQQ ETF | Tecnología |
| IWM | ETF | iShares Russell 2000 ETF | Mercado amplio |
| XLK | ETF | Technology Select Sector SPDR Fund | Tecnología |
| XLF | ETF | Financial Select Sector SPDR Fund | Financieros |

La inclusión solo fija cobertura del producto y del pipeline; no constituye una recomendación de inversión.

## Requisitos funcionales y criterios de aceptación

### REQ-001 — Explicar el movimiento de un instrumento

**EARS:** Cuando la persona usuaria pregunte por el movimiento de un símbolo cubierto en una fecha, el sistema deberá responder en español con el cambio de precio calculado por una tool determinista y sus fuentes.

**Criterios de aceptación:**

1. La variación absoluta y porcentual proviene de datos validados; el LLM solo la explica.
2. La respuesta enlaza el dato de precio y al menos una noticia o filing pertinente cuando estén disponibles, con fecha y fuente originales.
3. Si no hay una segunda fuente, la respuesta lo declara y no inventa contexto causal.
4. El precio se presenta con su proveedor, hora/fecha y condición de retraso; yfinance histórico nunca se etiqueta como cotización oficial en vivo.

### REQ-002 — Limitar y explicar la cobertura

**EARS:** Si se consulta un símbolo no incluido en el universo aprobado, el sistema deberá indicar que está fuera de cobertura y mostrar la lista de los 20 símbolos.

**Criterios de aceptación:**

1. La validación de cobertura ocurre antes de solicitar precios, noticias, filings o LLM.
2. Símbolos válidos se normalizan de forma determinista (mayúsculas y espacios externos eliminados); símbolos desconocidos no se sustituyen por otros.

### REQ-003 — Fuentes opcionales, caché y degradación

**EARS:** Cuando un proveedor opcional no esté configurado, exceda cuota, falle o devuelva datos vencidos, el sistema deberá degradar a datos disponibles y comunicar la limitación.

**Criterios de aceptación:**

1. Twelve Data es opcional; aplica TTL de 15 minutos y límites internos no mayores a 8 solicitudes/minuto y 800/día.
2. Marketaux es opcional; mantiene TTL de 6–12 horas por símbolo y quince minutos para el listado diario por filtros. Respeta fechas/retrasos informados y no consulta sin key. ADR-006 corrige la suposición histórica de 24 horas: el plan gratuito documentado anuncia acceso inmediato, con 100 peticiones/día y tres artículos/petición.
3. Sin proveedor de cotización, se puede mostrar el último histórico yfinance disponible únicamente con fecha y aviso de que no es tiempo real; si no hay dato utilizable, se omite el cálculo.
4. Timeout, cuota y respuestas inválidas no borran datos cacheados válidos; los tests simulan estos casos.

### REQ-004 — Consultar filings oficiales SEC

**EARS:** Cuando se soliciten documentos de una compañía cubierta, el sistema deberá buscar filings pertinentes en la SEC y devolver referencias verificables.

**Criterios de aceptación:**

1. Cada resultado incluye formulario, fecha, enlace SEC original y símbolo/empresa asociada.
2. Las llamadas respetan el máximo de 10 solicitudes por segundo y envían un `User-Agent` identificable con contacto configurado.
3. Ausencia de filing, mapeo CIK o configuración de contacto produce un mensaje explícito, no un documento inferido.
4. Se cachean respuestas y se limitan los campos recuperados al contenido necesario para la consulta.

### REQ-005 — Enseñar conceptos financieros

**EARS:** Cuando la persona usuaria pregunte por un concepto financiero, el sistema deberá explicarlo en español con lenguaje educativo y ejemplos que no impliquen una recomendación personalizada.

**Criterios de aceptación:**

1. El glosario local aporta definiciones base para conceptos del piloto (volatilidad, beta, correlación, ETF, retorno y riesgo).
2. El LLM puede adaptar la explicación, pero no inventa cifras de mercado ni cita fuentes inexistentes.
3. La respuesta diferencia una explicación general de una evaluación personal e incluye el disclaimer global.

### REQ-006 — Recomendar por volatilidad objetivo

**EARS:** Cuando la persona usuaria solicite instrumentos de volatilidad baja, media o alta, el sistema deberá filtrar con cubetas estadísticas deterministas calculadas sobre retornos históricos.

**Criterios de aceptación:**

1. Se reutiliza `volatility_bucket`; no se entrena un clasificador ML para estas tres etiquetas.
2. Cada candidato muestra horizonte, fecha de cálculo y definición de volatilidad; el resultado no promete riesgo futuro.
3. Si la cubeta está vacía o faltan features válidas, se explica la limitación en vez de completar la lista con instrumentos de otra categoría.

### REQ-007 — Encontrar instrumentos similares

**EARS:** Cuando la persona usuaria indique un instrumento de referencia, el sistema deberá devolver instrumentos cercanos según el clustering multi-característica evaluado.

**Criterios de aceptación:**

1. Se reutiliza el artefacto de Fase 2 y features de volatilidad, correlación, beta y sector codificado.
2. Se excluye el instrumento de referencia; la lista informa clúster, features/horizonte y motivo de similitud de forma trazable.
3. Si el artefacto está ausente, es incompatible o el símbolo no tiene features, la tool falla de forma explícita y no inventa vecinos.
4. El LLM puede narrar el resultado determinista, pero no añadir candidatos.

### REQ-008 — Comparar contra preferencias

**EARS:** Cuando la persona usuaria compare instrumentos con preferencias declaradas, el sistema deberá calcular el ajuste mediante un score determinista y explicar sus componentes.

**Criterios de aceptación:**

1. Las preferencias se solicitan de forma gradual dentro del chat (volatilidad, sector, beta o referencia); se permite omitirlas. La sidebar explica la app y muestra símbolos consultables.
2. Las reglas, pesos y datos que forman cada score se muestran; el mismo input genera el mismo resultado.
3. No se presenta el ranking como recomendación personalizada ni garantía de rendimiento.

### REQ-009 — Enrutar intención y pedir aclaración

**EARS:** Cuando llegue una consulta, el sistema deberá clasificarla en explicación, educación, recomendación o comparación y pedir aclaración cuando falte un dato indispensable.

**Criterios de aceptación:**

1. El router usa salida estructurada validada y un fallback de reglas para intenciones reconocibles si el LLM falla.
2. Para recomendación distingue objetivo de volatilidad de instrumento de referencia; no llama la tool hasta identificar la modalidad.
3. Una intención desconocida produce una pregunta/ayuda y no llama tools no relacionadas.
4. El estado de conversación se valida con Pydantic y no contiene secretos.

### REQ-010 — Citas, disclaimer y contenido recuperado no confiable

**EARS:** Siempre que el sistema muestre una respuesta de la app, deberá incluir el disclaimer y conservar las fuentes originales de las afirmaciones factuales.

**Criterios de aceptación:**

1. Toda cifra y afirmación de mercado generada desde tools enlaza al registro de precio, noticia o filing correspondiente; si no hay fuente, se declara.
2. Toda respuesta incluye exactamente o de forma equivalente el aviso «No es asesoría financiera».
3. Noticias y filings se delimitan como datos no confiables en el prompt; instrucciones embebidas en esos textos no alteran el flujo ni el sistema.
4. La salida estructurada del LLM se valida antes de mostrarla; una salida inválida se reintenta según política y después se degrada con un mensaje seguro.
5. Fuentes en inglés pueden resumirse en español conservando la cita y URL original.

### REQ-011 — Acceso local directo y gestión de secretos

**EARS:** Cuando se inicie la app local, el sistema deberá permitir el acceso directo sin solicitar correo, contraseña ni crear una cuenta.

**Criterios de aceptación:**

1. La app presenta directamente el chat y las preferencias locales.
2. No se solicitan ni persisten credenciales de acceso; las preferencias y trazas usan un identificador local fijo.
3. `NVIDIA_API_KEY` es la única key obligatoria; Twelve Data y Marketaux son opcionales. Secretos provienen de entorno/secret manager, nunca del repositorio, UI o logs.
4. La ausencia de credenciales de proveedores no bloquea el acceso y se comunica con un aviso claro.

### REQ-012 — Trazabilidad y retención local

**EARS:** Cuando se procese una consulta, el sistema deberá registrar suficiente traza operativa para auditar herramientas, fuentes y consumo sin guardar secretos.

**Criterios de aceptación:**

1. `QueryLog` registra intención, tools ejecutadas, referencias de fuente, timestamp, estado y tokens/costo disponibles.
2. El log no persiste contraseña, API keys ni texto secreto de sesión.
3. Se documenta retención objetivo de 90 días y purga; cachés respetan TTL por fuente.
4. La capa SQLModel usa SQLite en local y `DATABASE_URL` permite Postgres en despliegue futuro.

### REQ-013 — Límites, latencia y pruebas de aceptación

**EARS:** Mientras el piloto use proveedores con cuotas gratuitas, el sistema deberá limitar consumo, registrar degradación y permitir validar las rutas sin credenciales reales.

**Criterios de aceptación:**

1. Los límites internos no superan los de REQ-003/004 y se exponen avisos de caché/datos demorados.
2. Llamadas LLM usan timeout, reintentos acotados y presupuesto de tokens configurable.
3. La suite dorada en español cubre 15–20 casos: 100% con disclaimer, ≥90% de afirmaciones numéricas trazables, ≥90% de intención correcta y 0 obediencias a prompt injection.
4. Tests unitarios no dependen de red; tests reales se marcan integration, se omiten sin credenciales/configuración y reportan claramente el proveedor comprobado.

### REQ-014 — LLM configurable y resiliente

**EARS:** Cuando una ruta requiera redacción o clasificación mediante ChatNVIDIA, el sistema deberá usar el modelo configurado con límites de tiempo, reintentos y tokens, y degradar con seguridad si no hay respuesta válida.

**Criterios de aceptación:**

1. El identificador del modelo, timeout y presupuesto de tokens son configuración de entorno; `NVIDIA_API_KEY` no tiene valor por defecto ni aparece en errores/logs.
2. Cada llamada tiene timeout finito y como máximo dos reintentos con backoff; no hay reintentos infinitos ni llamadas en bucle.
3. Una respuesta se valida contra el esquema esperado antes de usarla; agotados los reintentos, se responde con un aviso determinista sin inventar datos.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-01 | Spec inicial EARS, backlog de implementación y universo de 20 instrumentos aprobados para el piloto v0.1. |
| 2026-11-01 | Fase 1 completada: universo cotejado con el catálogo de Fase 2 y trazabilidad REQ/TASK validada. |
| 2026-11-01 | Implementación Fase 3: app local, auth, router/tools, trazabilidad y tests. La suite y smoke pasan; filings SEC y yfinance se verificaron en vivo. ChatNVIDIA y demo end-to-end pendientes de rotar la clave y repetir el test. |
| 2026-11-04 | Por solicitud del usuario, se elimina el login del piloto local; la app abre directamente y conserva preferencias/trazas bajo una identidad local anónima. |
| 2026-11-04 | Conversación con contexto y preferencias por chat detalladas en specs/conversacion-preferencias; sidebar informativa y catálogo de símbolos. |
| 2026-11-04 | Guía de tono, narración factual validada, memoria resumida opcional y comprensión semántica con evidencia detalladas en specs/agente-amigable; NIM live pendiente. |
| 2026-11-04 | Depuración de procedencia, beta pendiente, reemplazo de comparación y configuración compartida en specs/depuracion-agente. README raíz con comandos y estado de skill externa pendiente. |
| 2026-11-04 | Agente modular: fachadas de diálogo/ejecución, componentes separados, aprendizaje sin mutar preferencias y un solo cliente por turno. Verificación offline detallada en specs/agente-modular. |
| 2026-11-04 | ADR-006 revisa la suposición de retraso Marketaux; actualidad-mercados añade noticias diarias/snapshots y exploracion-guiada conecta criterios conversados con el clustering aprobado. |
