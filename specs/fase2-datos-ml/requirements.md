# Requisitos — Fase 2: datos y ML offline

- **Estado:** Implementado; verificación unitaria y batch live completados
- **Alcance:** ingesta histórica batch, persistencia local portable, features, agrupamiento, cubetas deterministas, evaluación y artefactos reproducibles.
- **Exclusiones:** UI, orquestación de chat, recomendaciones narradas, fuentes de noticias, SEC, despliegue y conexión Postgres; corresponden a otras fases.
- **Universo:** usa la lista aprobada para el piloto en `specs/piloto/requirements.md`, sincronizada con `src/investiq/instruments.py` (15 acciones + 5 ETF); su selección no representa una recomendación financiera.

## Requisitos y criterios de aceptación

### REQ-201 — Persistencia local portable

**EARS:** Cuando se inicialice la capa de datos, el sistema deberá crear el esquema SQLModel en SQLite y persistir instrumentos, barras de precios, features y resultados de ML.

**Criterios de aceptación:**

1. Se puede elegir la ruta de SQLite con `DATABASE_URL` y la capa usa modelos SQLModel.
2. La operación de guardado de barras es idempotente por símbolo y fecha.
3. La inicialización y persistencia se verifican con una base temporal sin red.

### REQ-202 — Ingesta histórica batch

**EARS:** Cuando se ejecute el comando batch, el sistema deberá descargar historia diaria ajustada para los 20 símbolos, validar los registros y guardarlos sin depender de Twelve Data o Marketaux.

**Criterios de aceptación:**

1. Horizonte por defecto de 2 años; la fecha, símbolo y cierre ajustado se conservan.
2. Errores por símbolo se informan y no borran datos previamente persistidos.
3. La ingesta admite un proveedor y datos simulados en pruebas; la verificación live es explícita y opcional.

### REQ-203 — Features multi-característica

**EARS:** Cuando existan cierres históricos válidos para varios instrumentos, el sistema deberá calcular volatilidad anualizada, correlación media con pares, beta frente al benchmark y sector codificado para el clustering.

**Criterios de aceptación:**

1. Los retornos se alinean por fecha y los NaN/instrumentos sin historia suficiente se excluyen con motivo explícito.
2. El vector usa volatilidad, correlación, beta y variables sectoriales; el escalado se ajusta en entrenamiento.
3. Las features guardadas quedan asociadas al instrumento y a la fecha de cálculo.

### REQ-204 — Agrupamiento y similitud

**EARS:** Cuando se entrene el pipeline con features válidas, el sistema deberá elegir K-Means entre candidatos por silhouette, producir membresías reproducibles y permitir obtener instrumentos similares a un símbolo.

**Criterios de aceptación:**

1. Se evalúan candidatos válidos con `2 <= k < n`; no se aceptan clusters degenerados.
2. El resultado registra `silhouette >= 0.25` y `ARI >= 0.6` entre semillas como umbrales de aprobación; cualquier incumplimiento queda explícito y no se presenta como evaluación aprobada.
3. `similar_instruments(symbol, top_n)` prioriza miembros del mismo cluster y desempata por distancia escalada.
4. Mismo dataset y semilla producen mismo artefacto y etiquetas normalizadas.

### REQ-205 — Cubetas deterministas de volatilidad

**EARS:** Cuando existan valores de volatilidad válidos, el sistema deberá asignar cubetas baja, media y alta usando terciles deterministas, sin entrenar un clasificador ML.

**Criterios de aceptación:**

1. Con al menos tres valores distintos se generan tres cubetas no vacías y ordenadas por volatilidad.
2. Empates se resuelven de forma determinista; valores ausentes no se asignan.
3. Se pueden consultar símbolos por cubeta.

### REQ-206 — Evaluación y artefactos versionados

**EARS:** Cuando el pipeline complete un entrenamiento, el sistema deberá guardar un artefacto versionado con dataset/features, semilla, configuración, métricas y membresías.

**Criterios de aceptación:**

1. Artefactos joblib se escriben bajo `ml/artifacts/` con metadatos JSON legibles y no incluyen secretos.
2. La ficha de evaluación informa universo, fechas, cantidad de filas, algoritmo, `k`, silhouette, ARI y aprobación por umbral.
3. Un test sintético offline valida el flujo completo; la descarga real de yfinance se identifica por separado.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-01 | Spec creada para ejecutar exclusivamente la Fase 2; se registra canasta técnica provisional por ausencia de la lista de Fase 1. |
| 2026-11-01 | Se implementó la fase; 7 tests offline pasan y la evaluación con datos yfinance supera silhouette/ARI. |
| 2026-11-01 | Fase 1 aprobó la misma canasta de 20 símbolos usada por el entrenamiento; se cierra el supuesto provisional. |
