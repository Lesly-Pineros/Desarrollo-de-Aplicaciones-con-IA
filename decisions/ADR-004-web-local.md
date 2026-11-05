# ADR-004 — Web conversacional local en un proceso Python

- **Estado:** Aceptado para el frontend local por petición de reemplazo del usuario.
- **Fecha:** 2026-11-04.
- **Contexto:** el usuario solicita una experiencia más natural y similar a una página web, reemplazando la presentación Streamlit. El proyecto se edita sin Internet y se ejecuta también en otra máquina.

## Decisión

La entrada principal local será una web HTML/CSS/JS servida junto a una API mínima por Python. La API adapta la fachada `answer_turn`; no duplica el router, las herramientas ni la memoria. Se usa la biblioteca estándar para evitar un nuevo runtime o una instalación npm. Streamlit queda disponible como alternativa heredada.

## Consecuencias

Un solo comando y proceso; assets locales, sin CDN ni login. El servidor escucha por defecto solo en loopback y está diseñado para el piloto local single-user. Las fuentes, cuotas, validación factual, clustering y umbrales conservan sus contratos.

Esta decisión sustituye D1 para uso local. ADR-002 conserva el destino previsto para la alternativa Streamlit; la publicación del nuevo frontend requiere revisar hosting en fase 5. Esta tarea no inicia esa fase ni promete compatibilidad de la web con Streamlit Community Cloud.

## Alternativas

Seguir estilizando Streamlit limita el control del flujo y mantiene su apariencia. React con compilación y un backend separado añade dependencias y dos procesos sin una necesidad actual; se reconsiderará si la aplicación crece.
