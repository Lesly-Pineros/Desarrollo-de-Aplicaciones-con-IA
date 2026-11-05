# Requisitos — Continuidad y claridad del profesor

- **Estado:** Borrador (2026-11-04).
- **Implementación:** completada y verificada localmente; evidencia en [tasks.md](tasks.md). No supone aprobación editorial independiente ni aceptación con NVIDIA real.
- **Alcance:** corregir pérdidas de contexto reproducidas en conversaciones educativas, mejorar el respaldo local para principiantes y verificar cambios de tema sin servicios externos.
- **Exclusiones:** nuevos proveedores o datos financieros, señales de operación, cambios de preferencias financieras implícitos, NVIDIA real, despliegue y fase 5.

### REQ-001 — Aclaraciones y ejemplos con contexto

**EARS:** Cuando la persona pida aclarar, interpretar, ejemplificar o profundizar una lección sin nombrar otro sujeto, el sistema deberá conservar su tema y recuperar evidencia de ese documento.

**Criterios de aceptación:** «No entiendo», «¿Me lo explicas con un ejemplo?», «¿Cómo se interpreta?», «¿Por qué importa?» y preguntas sobre sus riesgos o costes mantienen el tema; diálogo y recuperación comparten una interpretación determinista acotada. «¿Cómo funciona esto?» y «¿Para qué sirve esto?» continúan una lección activa y explican las capacidades de la app cuando no hay contexto. El comportamiento sobrevive a restaurar la memoria. Sin contexto no se selecciona un documento por coincidencias con palabras genéricas.

### REQ-002 — Cambios de tema y límites

**EARS:** Cuando un seguimiento nombre otro sujeto o pida datos de mercado, el sistema deberá atender esa consulta sin sustituirla por la lección anterior.

**Criterios de aceptación:** «¿Y qué es Bitcoin?», «Ahora explícame la inflación» y «¿Por qué importa la liquidez?» cambian de tema; temas desconocidos no se justifican con evidencia del tema anterior. Cotizaciones, actualidad sectorial y preferencias explícitas conservan sus rutas. Toda respuesta lleva «No es asesoría financiera»; textos recuperados siguen siendo datos no confiables.

### REQ-003 — Continuidad de instrumentos y nivel básico

**EARS:** Cuando se pida un ejemplo o los riesgos después de definir un instrumento del catálogo, el profesor deberá continuar desde su ficha educativa; cuando se indique nivel principiante, deberá ofrecer definición y ejemplo respaldados.

**Criterios de aceptación:** «¿Qué es AAPL?» → «Un ejemplo» → «¿Y sus riesgos?» utiliza la ficha de Apple sin pedir cotización, noticias ni filings, incluso tras restaurar memoria. Una lección básica conserva el significado del concepto además del ejemplo y cautelas; pedir su interpretación o importancia prioriza la explicación también en nivel básico. El nivel de explicación no crea preferencias de inversión. Las fuentes pertenecen a los documentos utilizados.

### REQ-004 — Verificación reproducible

**EARS:** Cuando se entregue la corrección, el repositorio deberá registrar resultados actuales, conversaciones de regresión y comandos exactos separados de la aceptación live pendiente.

**Criterios de aceptación:** pruebas con corpus real, SQLite temporal, generación simulada y proveedores bloqueados; navegador con credenciales desactivadas; biblioteca y specs válidas; README y PLAN actuales. Se preservan los cambios previos del workspace y rutas dinámicas. No atribuir naturalidad de NVIDIA real a mocks.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Borrador previo a implementar: fallos reproducidos de aclaración, interpretación, importancia y continuidad tras definir AAPL. |
| 2026-11-04 | Correcciones locales verificadas: 43 regresiones nuevas, 627 pruebas offline y 75 comprobaciones en Chrome. Incluye ayuda contextual, ausencia de tema y explicación en nivel básico. |
