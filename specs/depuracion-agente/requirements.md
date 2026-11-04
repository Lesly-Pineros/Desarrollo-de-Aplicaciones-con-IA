# Requisitos — Depuración del agente y ejecución reproducible

- **Estado:** Implementación local verificada (2026-11-04). Instalación externa y NIM real pendientes; no se declaran completados.
- **Alcance:** corregir fallos concretos de diálogo/procedencia, reducir duplicación, unificar configuración y actualizar pruebas, plan y documentación de consola.
- **Instalación externa:** la URL entregada corresponde al estándar Agent Skills. El catálogo de ejemplos enlazado ofrece skill-creator; su descarga local se intentó y el permiso de red fue rechazado. No está instalada ni se declara utilizada. Se aplica la skill SDD ya disponible; la instalación externa permanece pendiente.
- **Exclusiones:** despliegue, login, nuevos proveedores, borrar datos locales, desactivar controles financieros y uso de claves reales no rotadas.

### REQ-001 — Procedencia de preferencias

**EARS:** Cuando un mensaje cite una preferencia ajena o pregunte por el significado de una declaración, el sistema deberá tratarlo como información y conservar intactas las preferencias guardadas.

**Criterios de aceptación:**
1. «¿Qué significa “prefiero volatilidad alta”?» y «Mi amigo dice “prefiero volatilidad alta”» no actualizan UserPreference.
2. El control se aplica tanto al parser determinista como al semántico, incluso durante una aclaración pendiente.
3. Declaraciones propias y comandos explícitos de consulta/borrado siguen funcionando.

### REQ-002 — Continuidad y correcciones naturales

**EARS:** Cuando la persona cambie su comparación o responda a una aclaración de beta, el agente deberá completar la operación correcta usando el contexto tipado.

**Criterios de aceptación:**
1. «Compara AAPL» → «Compara NVDA y MSFT» compara solo NVDA/MSFT; «MSFT» como respuesta corta sí completa AAPL/MSFT.
2. Una pregunta sobre volatilidad que mencione precio sigue siendo educativa y no descarta una comparación pendiente.
3. Tras una beta inválida, «1.2» completa el campo beta y se valida su rango sin exigir repetir la palabra beta.
4. El campo pendiente de beta sobrevive a la memoria estructurada sin guardar texto literal.

### REQ-003 — Prosa factual controlada

**EARS:** Cuando el LLM acompañe un resultado factual, el sistema deberá renderizar solo el resultado verificado y conectores conversacionales controlados.

**Criterios de aceptación:**
1. Una prosa como «los dividendos aumentaron y la demanda se disparó» fuera de {{result}} se rechaza aunque no incluya cifras ni símbolos.
2. El modelo puede elegir una apertura/cierre de un catálogo seguro; las citas y el bloque factual permanecen protegidos.
3. Educación conserva el flujo de explicación respaldada por glosario y las validaciones existentes.

### REQ-004 — Configuración y consola portables

**EARS:** Cuando se ejecute la app o el pipeline desde la misma copia del repositorio, ambos deberán resolver DATABASE_URL con la misma configuración.

**Criterios de aceptación:**
1. DATABASE_URL en .env se usa en app y CLI; una variable de entorno explícita tiene prioridad.
2. El lanzador resuelve la raíz dinámicamente y respeta INVESTIQ_PYTHON aun si existe .venv.
3. La verificación offline deshabilita credenciales y no contacta APIs; la validación live queda explícitamente separada.

### REQ-005 — Documentación y skill local

**EARS:** Cuando se cierre la revisión, el repositorio deberá incluir un README con comandos comprobables y estado real de las verificaciones e instalación.

**Criterios de aceptación:**
1. README cubre instalación, configuración, arranque, datos/ML, pruebas, MCP y dos copias del repo sin requerir login ni duplicar entrenamiento.
2. PLAN y documentos relacionados distinguen evidencias históricas, estado actual y NIM live pendiente.
3. .gitignore excluye únicamente el directorio de la instalación externa local prevista; conserva sdd-feature y specs versionables.
4. No se declara la skill descargada/instalada/usada mientras el permiso de descarga siga rechazado.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Auditoría previa y plan de correcciones; descarga externa no ejecutada por permiso de red rechazado. |
| 2026-11-04 | Correcciones y documentación completadas; 223 pruebas offline pasan, 4 integraciones omitidas, siete specs válidas. Exclusión local de Git comprobada. |
