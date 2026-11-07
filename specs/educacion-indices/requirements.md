# Requisitos — Explicar el S&P 500 y aclarar el frontend

- **Estado:** Implementada y verificada offline y en navegador local (2026-11-04). NVIDIA real pendiente; sin despliegue.
- **Alcance:** explicar el S&P 500 con variantes de escritura, fuente oficial y seguimiento conversacional; hacer inequívoco el arranque de la web gratuita existente.
- **Exclusiones:** cotizaciones de índices, ampliar el universo de instrumentos, instalar otro frontend, publicar en Internet, pruebas live de NVIDIA o avanzar a fase 5.

### REQ-001 — S&P 500 como concepto educativo

**EARS:** Cuando la persona pregunte qué es el S&P 500, SP500 o SP 500, el sistema deberá explicar el índice con lenguaje claro, una fuente oficial y el disclaimer.

**Criterios de aceptación:** reconocer mayúsculas, acentos y espacios; definición disponible sin Internet; no sustituir índice por SPY ni consultar precios; no confundir SP5000 ni el nombre del ETF SPY con el concepto; permitir añadir términos mediante un catálogo educativo modular. En preguntas sobre volatilidad, ETF o beta que mencionan incidentalmente S&P 500, debe explicarse el concepto solicitado y conservarse la definición de un instrumento cuando sea el sujeto de la pregunta.

### REQ-002 — Continuidad y validación factual

**EARS:** Cuando la persona complete una aclaración con «sp500» o pida una explicación más sencilla del tema, el sistema deberá conservar el concepto y sus fuentes, incluso al restaurar el resumen de memoria.

**Criterios de aceptación:** no guardar preferencias por una pregunta educativa; números y nombre del índice proceden del catálogo verificado; la narración opcional no puede añadir datos ni perder la fuente; ninguna llamada externa durante las pruebas offline.

### REQ-003 — Entrada web gratuita inequívoca

**EARS:** Cuando se ejecute la entrada principal de la aplicación, el sistema deberá abrir el servidor de la web HTML/CSS/JS existente sin importar ni requerir Streamlit.

**Criterios de aceptación:** `run_web.sh`, `investiq-app` e `investiq-web` apuntan al servidor web; no se instala ni mantiene un frontend heredado. README documenta solo la instalación y dirección local vigentes. Sin promesas de hosting gratuito ni despliegue en esta tarea.

## Changelog

| Fecha | Cambio |
|---|---|
| 2026-11-04 | Especificación previa de la ampliación solicitada y aclaración de frontend. |
| 2026-11-04 | Catálogo, seguimiento y entrada web verificados; revisión independiente corrigió prioridad de conceptos frente a contexto incidental. 380 pruebas offline y 43 checks de Chrome pasan. |
