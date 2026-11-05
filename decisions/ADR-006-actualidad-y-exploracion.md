# ADR-006 — Noticias del día, snapshots y exploración guiada

- **Estado:** Adoptada para la implementación local solicitada; integración de proveedores reales pendiente.
- **Fecha:** 2026-11-04.
- **Contexto:** el usuario solicita consultar noticias por sector/país, traducción y resúmenes, rendimiento sectorial y un acceso de recomendación educativa apoyado en el modelo entrenado.

## Decisión

Extender el proveedor Marketaux existente para noticias del día, con fecha según zona IANA y filtros documentados. Se revisaron sus [precios](https://www.marketaux.com/pricing) y [API](https://www.marketaux.com/documentation): el plan gratuito anuncia 100 peticiones diarias, tres artículos por petición y acceso inmediato. Se corrige la antigua suposición de retraso fijo de 24 horas; fecha de publicación, consulta, caché y posibles retrasos siguen visibles. Las condiciones comerciales pueden cambiar; esta lectura no constituye una integración live.

NVIDIA conserva su modelo configurable. Traduce titulares y resume exclusivamente extractos recibidos en una operación estructurada y acotada a un intento. El original queda enlazado. Las comprobaciones de IDs, spans, cifras, acrónimos e inyección reducen errores sin probar equivalencia semántica. No se descargan artículos arbitrarios ni se copian textos completos. La selección temporal de noticias no se incorpora al recuerdo personal ni a la biblioteca.

Para rendimiento se añade [FMP Sector Performance Snapshot](https://site.financialmodelingprep.com/developer/docs/stable/sector-performance-snapshot), opcional con clave y acceso dependiente del plan. Solo se representa el snapshot completo de once sectores de NASDAQ y su fecha; no se afirma que sea todo Estados Unidos ni se fabrica una hora de actualización. Sin acceso, cobertura completa o datos del día, la respuesta se degrada. No se contrata ni activa ningún plan de pago.

La exploración de acciones/ETF pregunta criterios de esa consulta y utiliza scaler, KMeans y características del modelo local aprobado. Los filtros y la volatilidad siguen siendo deterministas; la centralidad del clúster o la distancia a una referencia ordena candidatos para estudiar. Las métricas son históricas; no se presenta una instrucción de comprar hoy, un perfil financiero completo o una predicción de rentabilidad. Se comprueba huella de características cuando el artefacto la incluye, fechas y universo antes de combinarlos.

## Arquitectura y límites

Se mantienen ADR-001/003/004/005: módulos Python, web local y un único cliente NVIDIA configurable. Las nuevas ramas tienen aclaraciones lineales y estado acotado; no necesitan LangGraph. Las claves Marketaux/FMP son opcionales y propias del equipo; sin ellas continúan el profesor y el ML local preparado. No se añade otro framework, base vectorial, CDN, servicio alojado ni fase 5.

Las verificaciones usan HTTP/NVIDIA simulados y KMeans real sobre datos sintéticos en bases temporales. La aceptación de las APIs y el tono de NVIDIA real permanecen pendientes.
