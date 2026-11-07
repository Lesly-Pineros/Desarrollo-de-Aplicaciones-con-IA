# Requisitos — Logs operativos de InvestiQ

- **Estado:** Implementada; verificación pendiente
- **Alcance:** Dar visibilidad en terminal del inicio, etapas principales, duración, modo/proveedor, resultado, fallos y ruta interna del error en la web local y comandos de ejecución de InvestiQ.
- **Exclusiones:** Guardar logs en archivos o servicios externos, registrar conversaciones/valores financieros, telemetría, métricas remotas y cambios en la lógica de negocio.

## Requisitos y criterios de aceptación

### REQ-001 — Configuración de logs en consola

**EARS:** Cuando se inicie la web local, el MCP o el pipeline de datos, el sistema deberá configurar logs legibles en stderr con nivel INFO por defecto y nivel configurable por `INVESTIQ_LOG_LEVEL`.

**Criterios de aceptación:** muestra fecha/hora, nivel, componente y etapa; acepta niveles estándar; la aplicación sigue arrancando sin configurar variables nuevas.

### REQ-002 — Trazabilidad del flujo

**EARS:** Cuando se procese una petición, el sistema deberá registrar inicio, finalización, duración y etapas principales para ubicar si el trabajo llegó a web, diálogo, router, herramienta/proveedor, narración o persistencia.

**Criterios de aceptación:** los eventos de una petición concurrente comparten un identificador breve; se registran las categorías de intención, herramienta/proveedor y modo configurado/local, sin registrar la consulta ni el símbolo.

### REQ-003 — Errores útiles y seguros

**EARS:** Cuando una etapa falle, el sistema deberá registrar componente, etapa, duración, tipo de excepción y ubicación del código con traceback de marcos, sin incluir el mensaje bruto de excepción.

**Criterios de aceptación:** errores 500 inesperados dejan una pista diagnóstica en terminal; claves, URLs autenticadas, configuración secreta, texto del usuario y respuestas de proveedores/LLM no aparecen en logs.

### REQ-004 — Degradaciones de proveedores

**EARS:** Cuando un proveedor externo no esté configurado, alcance su cuota, falle o devuelva datos inválidos, el sistema deberá registrar qué ruta se omitió o degradó y la ruta alternativa, sin imprimir la solicitud ni su respuesta.

**Criterios de aceptación:** se distingue `sin clave`, `fallback`, `cuota` y `error de proveedor`; los fallos recuperables mantienen su comportamiento actual.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-07 | Borrador inicial para trazabilidad segura de la ejecución local en terminal. |
