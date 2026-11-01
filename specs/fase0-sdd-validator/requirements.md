# Requisitos — validador de trazabilidad SDD

- **Estado:** Borrador de demostración de la Fase 0
- **Alcance:** comprobar localmente que una spec Markdown enlaza requisitos, tareas y verificaciones.
- **Exclusiones:** validar gramática EARS completa, inspeccionar diseño semántico, modificar archivos o conectarse a servicios.

## Requisitos y criterios de aceptación

### REQ-001 — Validar la cadena REQ → TASK → verificación

**EARS:** Cuando se ejecute el validador sobre un directorio de spec SDD, el sistema deberá informar si cada requisito tiene una tarea enlazada, cada referencia de tarea apunta a un requisito existente y cada tarea declara una verificación.

**Criterios de aceptación:**

1. Acepta una spec válida con `requirements.md` y `tasks.md` y devuelve estado cero.
2. Reporta requisitos sin tarea, referencias REQ desconocidas, tareas sin REQ y verificaciones vacías con estado no cero.
3. Si falta alguno de los dos documentos, informa el archivo faltante sin traceback.
4. Usa solo la biblioteca estándar de Python.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-01 | Spec mínima creada con la skill `sdd-feature` para demostrar el bootstrap SDD de Fase 0. |
| 2026-11-01 | TASK-001 ejecutada por el agente de desarrollo; 4 pruebas pasan y el smoke test acepta esta spec. |
