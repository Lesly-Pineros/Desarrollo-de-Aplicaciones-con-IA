# Noticias, sectores y exploración educativa

La web ofrece accesos persistentes para **Noticias de hoy**, **Recomendaciones guiadas**, **Sectores de hoy · NASDAQ** y **Sectores · S&P 500**. Los dos universos sectoriales se consultan por separado. Todos usan el mismo chat; no hay formulario de perfil. Arranque: `bash run_web.sh`, en `http://127.0.0.1:8000`.

## Configurar en cada equipo

Añade las variables que necesites a tu `.env` existente sin sobrescribirlo ni compartir claves:

```dotenv
NVIDIA_API_KEY=
MARKETAUX_API_KEY=
FMP_API_KEY=
MARKET_TIMEZONE=America/Bogota
```

Los valores vacíos son intencionales. El modelo NVIDIA sigue configurado mediante `NVIDIA_MODEL`; no se contrató otro proveedor de LLM. Marketaux necesita una clave de tu cuenta para consultar noticias; FMP es opcional y el acceso a sus endpoints depende de tu plan. No se afirma que todos los endpoints de FMP estén incluidos en su cuenta gratuita. No se cambia ninguna suscripción ni se configura una clave real en el repositorio.

## Noticias y resúmenes

Ejemplos: «¿Cuáles son las noticias de hoy?», «Últimas noticias del sector tecnológico», «Noticias financieras de Colombia», «Noticias del sector energético en España» o «Noticias de AAPL».

La [documentación Marketaux](https://www.marketaux.com/documentation) permite filtrar industrias, entidades y países; se soportan los once sectores del proveedor y trece países por nombre: Estados Unidos, Colombia, España, México, Argentina, Chile, Perú, Brasil, Reino Unido, Alemania, Francia, Canadá y Japón. Su filtro de país corresponde al mercado de las entidades identificadas, no a toda la portada nacional ni a la residencia del usuario. Las consultas ambiguas piden un sector o país.

Se muestran hasta tres noticias del día por recencia, con publicación y fuentes; no es un ranking editorial de importancia ni cobertura exhaustiva. «Hoy» usa `MARKET_TIMEZONE` y se convierte a UTC para la API. Se rechazan fechas ausentes, futuras o de otro día. Las fechas históricas solicitadas se reconocen como no cubiertas. La caché de titulares dura quince minutos por filtros/día; ante fallo solo puede mostrarse caché del mismo día, con aviso de desactualización. La cuota de Marketaux se comparte con las noticias de símbolos: 100 peticiones/día y tres artículos/petición según [los precios consultados](https://www.marketaux.com/pricing) el 2026-11-04. No se asume un retraso fijo de 24 horas; no se promete latencia cero.

NVIDIA traduce títulos y, al pulsar **Resumir noticia 2** o escribir «Resume la segunda», resume el extracto de esa noticia. El botón conserva la selección por un identificador oculto; el chat muestra una frase natural. Nunca se descarga el artículo completo ni se inventa su contenido. Si falta extracto, se informa. Si no hay modelo o la salida no pasa los controles, se conserva el original y se explica que no hay traducción/resumen generado. Los titulares ya publicados en español no requieren traducción. La operación del LLM tiene un intento y conserva timeout/tokens configurados. Validar citas y cifras no demuestra equivalencia semántica de la traducción.

Los tres artículos y sus selecciones viven temporalmente en la sesión del chat; no se incluyen en la memoria persistente. Reiniciar la sesión requiere volver a consultar el listado. Los textos recuperados se tratan como datos no confiables y se muestran sin ejecutar HTML o instrucciones.

## Sectores que lideran hoy

El botón **Sectores de hoy · NASDAQ** consulta el snapshot diario de los once sectores de esa bolsa en [FMP](https://site.financialmodelingprep.com/developer/docs/stable/sector-performance-snapshot). Si hoy no es un día de mercado o aún no se publicó el snapshot, busca fechas recientes anteriores y muestra la fecha de los datos. Se exige el mismo día y bolsa, once sectores únicos y porcentajes finitos. NASDAQ es una bolsa y no representa todo el mercado estadounidense.

El botón **Sectores · S&P 500** intenta primero obtener la lista actual de componentes y cierres diarios por lote desde FMP. Busca los dos días de mercado más recientes con datos completos, calcula el cambio entre ambos cierres y promedia esas variaciones por sector. Muestra cuántos componentes incluye. Ese cálculo no es un índice sectorial oficial ni ponderado por capitalización.

Si FMP no está configurado o no entrega datos utilizables, la app consulta los cierres históricos de los [once ETF sectoriales Select Sector SPDR de State Street](https://www.ssga.com/us/en/individual/capabilities/equities/sector-investing/select-sector-etfs). Valida dos sesiones recientes comunes y presenta la variación cierre a cierre de cada ETF, con símbolo, fecha y enlaces a sus series en Yahoo Finance. Se identifica expresamente como referencia mediante ETF: no es el rendimiento oficial del sector ni el promedio de los componentes. Si tampoco hay once series completas y recientes, se explica la falta de datos; no se rellenan valores. Para pruebas desconectadas, `INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED=false` desactiva solo este respaldo.

## Recomendaciones guiadas

El botón **Recomendaciones guiadas** inicia una exploración educativa. Se pregunta solo lo que falte, una pregunta por turno y con ejemplos fáciles: tipo («ETF»), plazo («1–5 años»), variación («baja») y referencia opcional («sin referencia»). Puedes incluir todo en un mensaje: «Explorar acciones a largo plazo, volatilidad baja, tecnología, referencia AAPL» o «Recomiéndame ETF a largo plazo con volatilidad alta sin referencia». Los criterios parametrizan esa consulta; no escriben preferencias financieras automáticamente. Puedes preguntar qué significa un concepto, retomar la pregunta pendiente o cancelar.

El corto plazo no devuelve candidatos como una solución segura para dinero necesario pronto. Para otros plazos, se usa exclusivamente el modelo KMeans aprobado y su scaler, con features del mismo universo/período y comprobación de huella si está disponible. Primero se filtran tipo, tercil de volatilidad y sector; después se ordena por clúster/distancia a una referencia o por cercanía al centro del clúster. Se muestran hasta tres coincidencias, sin rellenar con instrumentos incompatibles.

La tabla incluye tipo, volatilidad anualizada en porcentaje, tercil, beta, sector, grupo y coincidencia. El score deriva de distancia; no es rentabilidad ni probabilidad de ganar. El nivel de volatilidad no es un perfil financiero completo ni una garantía de protección. Las fechas y fuentes del modelo/features quedan visibles. NVIDIA puede acompañar el bloque factual protegido; no elige símbolos ni cambia métricas. La herramienta no decide qué conviene comprar hoy.

## Consulta individual de un símbolo

La sugerencia inicial pregunta «¿Quieres conocer las métricas de una acción o ETF?» y luego pide el símbolo. La ficha muestra su precio y variación reportados por Twelve Data si hay clave y datos disponibles, o el dato histórico de yfinance cuando existe. También muestra todas las características locales calculadas: volatilidad anualizada y su tercil, beta, correlación media con pares, sector y fecha de cálculo. Puedes consultar cualquier símbolo del catálogo. La cobertura corresponde a instrumentos de Estados Unidos. La cotización puede ser en tiempo real si Twelve Data y el plan de la cuenta lo permiten; de lo contrario aparece con su fecha y marcada como histórica o demorada. Volatilidad, beta y correlación se calculan sobre retornos históricos y no predicen resultados. Si faltan características o cotización se indica explícitamente. La consulta de movimientos además conserva las noticias y filings disponibles.

Necesita base y artefactos coherentes del mismo equipo. Si ya tienes históricos locales, prepara el modelo sin descargar datos:

```bash
.venv/bin/python -m investiq.ml.pipeline train --seed 42
```

Para preparar una copia nueva con Internet, el comando histórico sigue siendo `.venv/bin/python -m investiq.ml.pipeline all --period 2y --seed 42`. No se ejecuta automáticamente desde el chat y no se utilizó durante los tests offline. Copiar solo el joblib no prepara una base vacía.

## Verificar offline

```bash
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED=false SEC_USER_AGENT= .venv/bin/python -m pytest -q
NVIDIA_API_KEY= TWELVE_DATA_API_KEY= MARKETAUX_API_KEY= FMP_API_KEY= INVESTIQ_SECTOR_ETF_FALLBACK_ENABLED=false SEC_USER_AGENT= .venv/bin/python -m pytest -q tests/unit/test_market_current.py tests/unit/test_guided_exploration.py tests/unit/test_llm.py
.venv/bin/python -m investiq.knowledge validate
node tools/check_web.mjs
```

Chrome prueba la aplicación real con dos servidores/bases temporales: primero la regresión educativa y después fixtures claramente rotulados offline. La segunda base contiene noticias/snapshots sintéticos y un KMeans entrenado sobre características sintéticas. No representan datos actuales ni prueban Marketaux, FMP o NVIDIA en vivo. Los artefactos del fixture se crean en el directorio temporal y se eliminan con él; no se toca la base ni los modelos del usuario.

Trazabilidad: [actualidad](../specs/actualidad-mercados/tasks.md), [exploración](../specs/exploracion-guiada/tasks.md) y [ADR-006](../decisions/ADR-006-actualidad-y-exploracion.md). Fase 5 sin iniciar.
