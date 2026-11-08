# Diseño — Fase 5: POC en Render Free

## Resumen y requisitos cubiertos

- REQ-501: permitir bind configurable a `0.0.0.0:$PORT` manteniendo loopback por defecto local.
- REQ-502: proteger rutas de usuario con HTTP Basic Auth usando `INVESTIQ_ACCESS_PASSWORD`; health check público y mínimo.
- REQ-503: un único Web Service Free en `render.yaml`, SQLite temporal y secretos `sync: false`.
- REQ-504: pruebas HTTP locales y verificación live de despliegue, sin proveedores externos por defecto.

## Componentes y flujo

Render instala el paquete desde `pyproject.toml`, ejecuta la entrada `investiq-app`, enlaza el puerto público y consulta `/api/health`. Las solicitudes a la interfaz y API pasan por Basic Auth. Render termina HTTPS y reenvía HTTP al proceso; las cookies de sesión reconocen el encabezado `X-Forwarded-Proto`.

## Datos e interfaces

- `PORT`: puerto de escucha suministrado por Render.
- `INVESTIQ_ACCESS_PASSWORD`: secreto obligatorio al correr en Render; no se define valor por defecto.
- `NVIDIA_API_KEY`: secreto opcional, necesario para generación con NVIDIA.
- `TWELVE_DATA_API_KEY`, `MARKETAUX_API_KEY`, `FMP_API_KEY`: credenciales opcionales de proveedores de datos.
- `SEC_USER_AGENT`: nombre y correo real de contacto, requerido por el flujo de filings SEC; no es una API key.
- Otros valores de `.env.example` con defaults explícitos para el servicio: modelo y límites de NVIDIA/HTTP, retención, zona horaria, fallback sectorial y logging.
- `DATABASE_URL`: permanece SQLite por defecto; el almacenamiento local de Render Free es efímero.
- `/api/health`: endpoint mínimo para monitor de Render.

## Determinista y LLM

La autenticación, validación HTTP y health check son deterministas. El LLM no forma parte de las verificaciones de despliegue; solo se consulta si la usuaria agrega su clave y se acuerda una verificación live separada.

## Seguridad, fuentes y degradación

- Basic Auth con contraseña secreta y comparación de tiempo constante; HTTPS lo proporciona Render.
- No registrar `Authorization`, cookies, claves ni cuerpos de solicitudes.
- Exigir contraseña al detectar entorno Render para evitar publicar por accidente sin protección.
- Excluir el health check de auth para que Render pueda monitorizar el proceso.
- Un único password restringe el POC, pero quienes lo compartan usan el perfil y memoria local compartidos; compartirlo solo con un grupo de confianza.
- SQLite, preferencias y cachés pueden perderse con reinicios o suspensión; no se prometen backups ni persistencia.
- No se generan afirmaciones financieras ni se consultan proveedores en el health check.

## Decisiones y alternativas

- [ADR-002](../../decisions/ADR-002-despliegue.md): Render Free seleccionado.
- [ADR-004](../../decisions/ADR-004-web-local.md): web en un proceso Python.
- Un proxy/servicio extra, Postgres y frontend separado se excluyen para mantener el POC de costo cero.
