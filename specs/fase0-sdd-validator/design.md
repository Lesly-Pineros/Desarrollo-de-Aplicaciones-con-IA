# Diseño — validador de trazabilidad SDD

## Resumen y requisitos cubiertos

REQ-001: una comprobación local y de solo lectura para validar enlaces mínimos entre requisitos, tareas y verificaciones.

## Componentes y flujo

`tools/validate_spec.py` recibe una ruta. Lee `requirements.md` y `tasks.md`, extrae encabezados `REQ-NNN` y filas de tabla `TASK-NNN`, y compara las referencias. La función pura `validate_spec(path)` devuelve mensajes de error; el CLI imprime esos mensajes y devuelve código de salida 1 si encuentra alguno, o 0 si la spec es válida.

## Datos e interfaces

- Entrada: directorio con `requirements.md` y `tasks.md` en UTF-8.
- Salida de biblioteca: lista ordenada de mensajes; vacía significa válida.
- Salida CLI: errores por stderr y código 1; mensaje de éxito por stdout y código 0.
- Sintaxis soportada: headings `### REQ-NNN` y tabla Markdown cuyas columnas, en orden, son `TASK`, `Descripción`, `REQ`, `Verificación`.

## Determinista y LLM

No usa LLM; parsing y comparación deterministas con la biblioteca estándar.

## Seguridad, fuentes y degradación

Solo lee los dos archivos indicados; no ejecuta contenido de la spec ni sigue enlaces externos. Errores de lectura se reportan como validación fallida.

## Decisiones y alternativas

Es una TASK demostrativa de la Fase 0 y reutilizable por el flujo SDD. Se evita un framework de parsing para mantener el alcance pequeño.
