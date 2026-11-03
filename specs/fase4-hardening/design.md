# Diseño — Fase 4: hardening y MCP SEC

## Arquitectura

Servidor ejecutable como `python -m investiq.mcp_sec`. Usa el transporte stdio JSON-RPC de MCP y expone una única herramienta `sec_filings`. El método de herramienta crea una sesión SQLModel en SQLite/local `DATABASE_URL` y llama `providers.sec.sec_docs`, preservando la misma caché, validación de ticker, User-Agent y rate limit. `.codex/config.example.toml` documenta cómo registrarlo en Codex.

La suite eval offline amplía los golden del router y guardrails existentes; las pruebas de protocolo y provider usan fixtures/mocks. No requiere SDK MCP adicional: se implementan los mensajes JSON-RPC mínimos del ciclo `initialize`, `notifications/initialized`, `tools/list` y `tools/call` sobre stdin/stdout, con errores MCP estructurados. stdout queda reservado a protocolo; logs/diagnósticos van a stderr.

## Seguridad

Solo se aceptan símbolos del catálogo y límites entre 1 y 10. Errores externos se traducen a mensajes genéricos. No registrar credenciales ni incluir contenido externo como instrucciones. El cliente debe configurar `SEC_USER_AGENT` con contacto; sin configuración, la tool responde con el motivo degradado de la integración existente.

## Validación

- Unit: ciclo MCP y errores de parámetros con proveedor simulado.
- Offline: suite `tests/unit` y validador SDD sobre esta spec.
- Live: test SEC y ChatNVIDIA existentes, solo si configuración válida; mock no equivale a live.
