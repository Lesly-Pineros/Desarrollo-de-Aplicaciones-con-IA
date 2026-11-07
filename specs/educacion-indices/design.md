# Diseño — Educación sobre índices

## Componentes y trazabilidad

REQ-001 y REQ-002: catálogo educativo independiente con definición, ejemplo, alias y referencias por término. `language.canonical_education_topic` reconoce el concepto; `education_tool` conserva su contrato de texto; el handler obtiene las referencias del término y la memoria guarda su identificador canónico. La definición usa [S&P Dow Jones Indices](https://www.spglobal.com/spdji/en/indices/equity/sp-500/), consultado el 2026-11-04, como fuente oficial: índice de 500 empresas líderes del segmento de grandes empresas estadounidenses. No se inventa composición actual, valor, variación ni rentabilidad. La definición y su fuente se conservan localmente; el enlace no provoca una petición al responder.

Los alias respetan límites de palabra; una consulta sobre el precio del índice no se transforma en una cotización del ETF SPY. Las preguntas sobre el ETF nombrado siguen el catálogo de instrumentos. La narración de la nueva definición mantiene el bloque factual protegido porque el nombre y contenido incorporan cifras; los conectores permitidos y citas siguen bajo validación determinista.

REQ-003: `pyproject.toml` expone una única interfaz: la web HTML/CSS/JS, mediante `investiq-app`, `investiq-web` y `run_web.sh`. El código, extra de dependencia y launcher de la interfaz anterior se retiraron; las pruebas cubren el servidor local.

## Decisiones y límites

ADR-001, ADR-003 y ADR-004 se conservan. La web principal ya es gratuita y funciona sin runtime Node. No se cambia el diseño visual ni se propone un hosting en fase 5. Se documenta cómo abrir la versión correcta en otra copia del repo, sin asumir qué proceso está ejecutando el usuario.
