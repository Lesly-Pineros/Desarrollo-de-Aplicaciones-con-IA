# ADR-002 — Despliegue en nube: Streamlit Community Cloud + Neon (gratis), no Vercel en v0.1

- **Estado:** Aceptado
- **Fecha:** 2026-10-31
- **Contexto:** La petición inicial sugería Vercel como nube de despliegue. El frontend elegido es Streamlit (ADR implícito D1). Vercel **no es un target nativo de Streamlit** (está orientado a Next.js/funciones serverless), por lo que desplegar Streamlit en Vercel exige separar la app de la API y añadir piezas. El usuario priorizó: "lo que sea, pero que me sirva para desplegar y gratis".

## Decisión

Para **v0.1** desplegar en **Streamlit Community Cloud** (app, gratis, target nativo) + **Neon Postgres (free tier)** para persistencia. **Vercel queda descartado para v0.1** y se documenta como alternativa para v0.2 si se extrae una API FastAPI.

## Justificación

- **Encaje nativo:** Streamlit Community Cloud despliega apps Streamlit con un push a GitHub; cero fricción.
- **Gratis y de una sola pieza:** no requiere separar frontend/backend ni gestionar contenedores en v0.1.
- **Persistencia real:** el filesystem de Streamlit Cloud no es apto como BD → Neon aporta Postgres gestionado gratis con el mismo `DATABASE_URL` que ya usa SQLModel.
- **Una sola key:** los *secrets* de Streamlit Cloud guardan `NVIDIA_API_KEY`.

## Consecuencias

- (+) Despliegue gratuito, coherente con el stack, sin doble proceso.
- (+) Capa de datos portable (SQLite local → Neon) desde el día 1.
- (−) No se usa Vercel en v0.1 (diverge de la sugerencia inicial, aceptado por el usuario).
- (−) Streamlit Community Cloud tiene límites de recursos (suficientes para piloto single-user).

## Alternativas

- **Contenedor único en Render/Railway (free):** viable si se quiere empaquetar app + dependencias en un contenedor; más control, algo más de configuración. Documentada como plan B.
- **Vercel + FastAPI:** solo tiene sentido si en v0.2 se extrae una API (ADR-001); Streamlit iría igualmente en servicio aparte.
