# ADR-003 — ML: clustering multi-característica para "similares", umbrales deterministas para volatilidad

- **Estado:** Aceptado
- **Fecha:** 2026-10-31
- **Contexto:** El caso de uso de recomendación tiene dos variantes: (a) el usuario pide instrumentos de una **volatilidad objetivo** (baja/media/alta); (b) el usuario da un instrumento de **referencia** y pide otros **parecidos**. Se evaluó si ambas necesitan un modelo de ML.

## Decisión

- **Clasificación de volatilidad (baja/media/alta): SIN ML.** Se calcula la volatilidad histórica (desviación estándar de retornos) de cada instrumento y se asigna a 3 cubetas por **umbrales deterministas** (p. ej. terciles).
- **"Instrumentos similares a X": CON ML.** Se usa **clustering no supervisado (scikit-learn)** sobre un vector **multi-característica** por instrumento: **volatilidad, correlación de retornos, beta y sector** (codificado). La similitud "parecido a X" se resuelve por pertenencia al mismo clúster y/o distancia en el espacio de features.

## Justificación

- La volatilidad en 3 cubetas es un problema **unidimensional** → un umbral es más simple, explicable, reproducible y citable que un modelo. Meter ML ahí sería sobre-ingeniería.
- "Parecido" es **multidimensional** (no basta la volatilidad) → aquí el clustering aporta valor real y cumple el requisito original de "agrupamientos históricos vía ML".
- Mantiene la **regla de oro**: el ML/estadística produce la clasificación; el LLM solo **narra** el resultado.

## Parámetros de arranque (ajustables)

- **Features:** volatilidad (σ de retornos), correlación de retornos, beta, sector (one-hot). Escalado estándar antes de clusterizar.
- **Algoritmo:** K-Means como base (alternativa: aglomerativo jerárquico); `k` elegido por silhouette.
- **Horizonte:** ~1–2 años de histórico (yfinance).
- **Eval:** silhouette ≥ 0.25 (arranque) y estabilidad ARI ≥ 0.6 entre semillas; semilla fija; artefactos versionados.

## Consecuencias

- (+) Complejidad proporcional: ML solo donde aporta.
- (+) Resultados reproducibles y evaluables; cumple el requisito de ML sin inflarlo.
- (−) Con solo 20 instrumentos en v0.1, el clustering es modesto; se re-evalúan features/`k` al escalar a 150+50.

## Alternativas descartadas

- **ML para todo (incluida la volatilidad):** innecesario; umbral determinista es superior en simplicidad y explicabilidad.
- **Sin ML (todo por reglas):** no cubre bien "parecido" multidimensional; perdería el requisito de agrupamientos históricos.
