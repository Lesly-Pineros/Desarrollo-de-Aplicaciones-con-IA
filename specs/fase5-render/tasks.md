# Tareas — Fase 5: POC en Render Free

| TASK | Descripción | REQ | Verificación | Estado |
|---|---|---|---|---|
| TASK-501 | Parametrizar bind/puerto y health check; mantener defaults locales. | REQ-501 | Pruebas unitarias de HTTP local; compilación. | Completa |
| TASK-502 | Implementar Basic Auth fail-closed en Render y cookies seguras detrás del proxy. | REQ-502 | Pruebas HTTP de acceso permitido/denegado y cookie Secure. | Completa |
| TASK-503 | Crear Blueprint Render Free y guía de variables/limitaciones. | REQ-503 | Parseo YAML, build de wheel y revisión de diff por secretos. | Completa |
| TASK-504 | Publicar en Render después de configurar secretos; validar health, auth, front y assets en vivo. | REQ-504 | Smoke test contra URL real; proveedores externos y NVIDIA excluidos salvo petición/configuración explícitas. | Pendiente: configuración manual de la usuaria |

## Trazabilidad

| REQ | TASK(s) | Evidencia de verificación esperada |
|---|---|---|
| REQ-501 | TASK-501 | Tests unitarios y HTTP local con host/puerto no predeterminados. |
| REQ-502 | TASK-502 | Tests HTTP locales con contraseña fixture, 401/200, cookie Secure y revisión de logs. |
| REQ-503 | TASK-503 | Parseo del manifiesto, `pip install .` y revisión estática del diff. |
| REQ-504 | TASK-504 | Comprobaciones HTTP HTTPS contra servicio Render real, antes y después de activar claves manuales. |
