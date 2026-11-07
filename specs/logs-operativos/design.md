# Diseño — Logs operativos de InvestiQ

## Resumen y requisitos cubiertos

REQ-001 a REQ-004: instrumentar las etapas del runtime local con la biblioteca `logging` de Python, sin un servicio ni dependencia nueva.

## Componentes y flujo

- `investiq.logging_config`: configura formato/nivel, contexto breve de petición, medición de duración y reporte seguro de fallos.
- `web.server`: inicio/parada, petición HTTP local y errores 4xx/5xx. El request ID se asigna al entrar en la API y se limpia al salir.
- `web.service`, `conversation`, `routing`, `orchestration`, `handlers`: etapas de diálogo, clasificación, ejecución de intención/tools y persistencia.
- `providers/*`, `llm`, `tutor`, `ml.pipeline`, `mcp_sec`: llamadas, omisiones, fallback y comandos clave.
- `INVESTIQ_LOG_LEVEL` configura el umbral global; INFO es el valor predeterminado.

Los mensajes usan hitos estables y duración en milisegundos. Los logs de niveles superiores muestran el recorrido completo; DEBUG queda para detalle de desarrollo seguro.

## Datos e interfaces

Salida en stderr mediante el formato `timestamp nivel [request_id] logger: mensaje`. El campo request ID es corto y no identifica al usuario. Los nombres de etapas, categorías de intención y proveedores son valores internos controlados.

## Determinista y LLM

Los logs describen el control determinista del flujo. Nunca se registran prompts, mensajes, respuestas generadas, símbolos, cifras de mercado ni contenido recuperado.

## Seguridad, fuentes y degradación

No se imprimen excepciones en bruto, headers, parámetros de requests, URLs autenticadas, claves, cadenas de conexión, usuario, cookie ni dirección IP. Los fallos inesperados registran clase de excepción y marcos `(archivo, línea, función)` del stack, omitiendo mensajes y líneas de código. Las excepciones recuperables de proveedor registran categoría y fallback. Los logs no sustituyen la respuesta visible ni modifican cuotas.

## Decisiones y alternativas

Python `logging` y salida de consola conforme a ADR-001/004. Se difieren archivos y plataformas remotas para mantener la app local y evitar almacenar datos personales/financieros.
