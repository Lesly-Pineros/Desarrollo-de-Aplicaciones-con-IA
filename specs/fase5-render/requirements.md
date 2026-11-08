# Requisitos — Fase 5: POC en Render Free

- **Estado:** Aprobado para ejecución por solicitud del usuario (2026-11-08).
- **Alcance:** desplegar la web Python actual como un único servicio Render Free, con protección de acceso por contraseña, variables configurables por la usuaria y verificaciones locales y live.
- **Exclusiones:** costos, recursos pagos, base administrada, login multiusuario, persistencia garantizada, rediseño del frontend y validación de datos financieros en vivo.

## Requisitos y criterios de aceptación

### REQ-501 — Arranque compatible con Render

**EARS:** Cuando Render inicie el servicio, la aplicación deberá enlazar `0.0.0.0` en el puerto `PORT` configurado por la plataforma y responder al health check.

**Criterios de aceptación:**
1. El proceso acepta host y puerto por configuración de entorno o argumentos de arranque.
2. `GET /api/health` devuelve 200 sin revelar configuración ni secretos.

### REQ-502 — Protección del POC publicado

**EARS:** Cuando el servicio se ejecute en Render, la aplicación deberá rechazar el acceso a páginas y API si `INVESTIQ_ACCESS_PASSWORD` no está configurada o no coincide; el health check seguirá accesible.

**Criterios de aceptación:**
1. El servicio no inicia públicamente sin contraseña de acceso configurada.
2. Peticiones sin credenciales o con credenciales incorrectas reciben 401 y desafío Basic Auth.
3. Credenciales válidas acceden al front y API; contraseña y encabezado Authorization no se registran.
4. Las cookies de sesión se marcan Secure detrás de HTTPS.

### REQ-503 — Despliegue sin cobros ni persistencia falsa

**EARS:** Cuando se configure el servicio de POC, el manifiesto y las instrucciones deberán seleccionar exclusivamente Render Free, declarar secretos no sincronizables y advertir que SQLite es efímera.

**Criterios de aceptación:**
1. El manifiesto define un único Web Service, build/start command y health check.
2. Las claves no aparecen en el repositorio ni en logs.
3. Se documenta que el filesystem gratuito no persiste y que las claves externas son opcionales salvo NVIDIA para generación.

### REQ-504 — Verificación antes y después de publicar

**EARS:** Cuando se complete el despliegue, se deberán verificar build, suite local pertinente, acceso protegido y recursos básicos en la URL de Render; los resultados distinguirán mocks de servicios reales.

**Criterios de aceptación:**
1. Validaciones locales incluyen bind no-local, health, autenticación, carga del frontend y API con fixtures donde aplique.
2. En vivo se comprueban HTTPS, health check, Basic Auth y carga de frontend/assets sin llamar a proveedores financieros.
3. No se declara integración NVIDIA/financiera live si las claves no fueron configuradas y verificadas.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-08 | Spec inicial aprobada para ejecutar la fase 5 con Render Free; claves configuradas manualmente por la usuaria. |
