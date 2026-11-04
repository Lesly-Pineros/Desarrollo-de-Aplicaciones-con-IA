# Requisitos — Agente modular y diálogo pulido

- **Estado:** Implementada y verificada offline (2026-11-04). NIM real y nueva skill local siguen pendientes; no se declaran verificados/creados.
- **Alcance:** separar responsabilidades del agente actual y corregir defectos de conversación demostrables; mantener los contratos públicos y actualizar pruebas/documentación.
- **Skills aplicadas:** sdd-feature y skill-creator disponibles. Crear una nueva skill en .agents fue rechazado por el permiso de escritura; no está instalada ni se declara utilizada. No se requiere descarga para trabajar con las skills disponibles.
- **Exclusiones:** despliegue, nuevos proveedores, login, LangGraph, borrar datos, cálculos por LLM o pruebas live no autorizadas en este entorno.

### REQ-001 — Ejecución de consultas por componentes

**EARS:** Cuando se procese una consulta, el sistema deberá separar enrutamiento, ejecución de herramientas, construcción de respuesta y trazabilidad.

**Criterios de aceptación:**
1. answer_query conserva su interfaz principal y delega en APIs públicas de módulos cohesivos.
2. Los handlers devuelven resultado/fuentes/hechos/herramientas sin llamar al LLM ni registrar conversaciones.
3. El log se registra una sola vez por respuesta y conserva purga/diagnósticos sin texto del usuario.
4. No se agregan wrappers para mantener imports privados de tests: se actualizan las pruebas al componente propietario.

### REQ-002 — Diálogo con responsabilidades claras

**EARS:** Cuando un turno implique memoria, una aclaración o preferencias, el sistema deberá resolver cada responsabilidad mediante componentes comprobables por separado.

**Criterios de aceptación:**
1. Los comandos de memoria/nivel se separan de la ejecución financiera y el estado pendiente tiene transiciones explícitas.
2. Respuestas cortas, cambios de tema, correcciones, omisión y restauración mantienen su comportamiento verificado.
3. No se repite la creación fallida del cliente NIM dentro de un mismo turno.
4. Los ajustes de nivel y contexto se reflejan en una respuesta educativa disponible localmente.

### REQ-003 — Fluidez y procedencia bajo revisión independiente

**EARS:** Cuando una revisión identifique un defecto reproducible, el sistema deberá corregirlo con una regresión que observe el comportamiento y preserve la procedencia de preferencias.

**Criterios de aceptación:**
1. Pedir aprender o entender un concepto no declara una preferencia aunque mencione volatilidad.
2. Mensajes conversacionales no activan herramientas financieras por coincidencias ambiguas con símbolos.
3. Revisión independiente evalúa el cambio sin depender solo de los resultados esperados del implementador.

### REQ-004 — Validación y documentación actuales

**EARS:** Cuando se cierre la modularización, el repo deberá documentar responsabilidades y comandos reales y distinguir verificación offline de integraciones live.

**Criterios de aceptación:**
1. Suite local y AppTest pasan sin proveedores reales; diagnóstico live permanece opt-in.
2. README, PLAN y specs reflejan los módulos finales y el estado real de la skill no creada.
3. Se conservan disclaimer, bloque factual protegido, validación de evidencia, retención y memoria sanitizada.
4. No se modifica el alcance de las ADR ni se adelanta despliegue.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Plan previo usando skills disponibles; nueva skill local no creada por rechazo de escritura en .agents. |
| 2026-11-04 | Modularización y correcciones verificadas: 270 pruebas offline pasan, cuatro integraciones omitidas y ocho specs válidas. |
