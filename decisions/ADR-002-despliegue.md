# ADR-002 — Despliegue del POC en Render Free

- **Estado:** Aceptado para el POC; despliegue aún no iniciado.
- **Fecha:** 2026-11-08.
- **Historial:** La decisión original de Streamlit Community Cloud + Neon quedó obsoleta al retirarse Streamlit como interfaz. [ADR-004](ADR-004-web-local.md) define la web vigente servida desde Python.
- **Contexto:** El usuario confirma Render Free como destino del POC y solicita evitar costos. La app actual combina HTML/CSS/JS y API en un proceso Python. Render Free admite servicios web Python, pero su filesystem es efímero y el servicio puede suspenderse por inactividad.

## Decisión

Usar **un servicio web Render Free** para el POC. Mantener SQLite con datos temporales y no agregar una base gestionada mientras no se requiera persistencia, para evitar costos adicionales. La fase 5 permanece pendiente hasta completar los requisitos de acceso y adaptación del servidor.

## Justificación

- **Encaje:** Render ejecuta servicios web Python y puede servir el frontend y la API en el mismo proceso.
- **Costo del POC:** el plan Free permite probar el servicio sin suscripción mensual, dentro de sus cuotas y límites.
- **Simplicidad:** no requiere separar frontend/backend ni agregar una base de datos administrada para un POC con datos desechables.

## Consecuencias

- (+) Un solo servicio compatible con la app Python existente y sin costo recurrente dentro del nivel Free.
- (−) El filesystem es efímero: SQLite y los datos creados en ejecución pueden perderse al reiniciar, suspender o desplegar.
- (−) El servicio Free se suspende tras inactividad y puede tener arranque en frío; no es un compromiso de disponibilidad.
- (−) El servicio actual solo enlaza loopback y asume una identidad local compartida; no es publicable hasta adaptar el servidor y resolver aislamiento/autenticación.
- (−) Las cuotas gratuitas pueden cambiar; se deben revisar antes de desplegar y no habilitar recursos pagos.

## Alternativas

- **Vercel:** posible para frontend estático, pero requiere alojar el backend Python en otro servicio o rediseñarlo; agrega piezas para este POC.
- **Firebase Hosting + Cloud Run:** posible con frontend estático y backend en Cloud Run; requiere asociar facturación y revisar las cuotas/cargos de Google Cloud, por lo que no se elige para este objetivo de costo cero.
- **Railway:** alternativa técnica para servicio Python, pero sus recursos y volúmenes dependen del plan/cuotas vigentes; no se elige para evitar incertidumbre de costos.
