# Skills locales de diseño

Se descargaron las tres skills solicitadas en `.local/design-skills/`; esa ruta está ignorada por Git. Son instrucciones de desarrollo y recursos auxiliares, no dependencias del agente ni del navegador. Se leyeron para el rediseño de [web-conversacional](../specs/web-conversacional/requirements.md).

| Sitio solicitado | Fuente utilizada | Carpeta local |
|---|---|---|
| [Taste](https://www.tasteskill.dev/) | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill/tree/main/skills/taste-skill) | `.local/design-skills/design-taste-frontend` |
| [Emil Kowalski](https://emilkowal.ski/skill) | [emilkowalski/skills](https://github.com/emilkowalski/skills/tree/main/skills/emil-design-eng) | `.local/design-skills/emil-design-eng` |
| [Impeccable](https://impeccable.style/designing/) | [pbakaus/impeccable](https://github.com/pbakaus/impeccable/tree/main/.agents/skills/impeccable) | `.local/design-skills/impeccable` |

La instalación usó `install-skill-from-github.py` de `skill-installer`, con destino local explícito. Para repetirla en otro entorno Codex, define su ruta real y ejecuta desde la raíz (requiere Internet; las carpetas destino deben estar libres):

```bash
SKILL_INSTALLER=/ruta/a/skill-installer/scripts/install-skill-from-github.py
.venv/bin/python "$SKILL_INSTALLER" --repo Leonxlnx/taste-skill --path skills/taste-skill --name design-taste-frontend --dest .local/design-skills
.venv/bin/python "$SKILL_INSTALLER" --repo emilkowalski/skills --path skills/emil-design-eng --dest .local/design-skills
.venv/bin/python "$SKILL_INSTALLER" --repo pbakaus/impeccable --path .agents/skills/impeccable --dest .local/design-skills
```

También puedes trasladar la carpeta completa desde el equipo conectado. Una ruta personalizada no implica registro global automático en Codex: se usan leyendo explícitamente cada `SKILL.md`. No hace falta llevar estas skills al equipo que solo ejecuta la aplicación.

## Aplicación y límites

Impeccable guió la superficie de tarea (Operate): conversación central, estados claros y comprobación visual. Taste aportó jerarquía y coherencia; sus reglas comerciales no sustituyen las necesidades del chat. Emil aportó foco, interacción táctil y movimiento contenido. Las decisiones están en [PRODUCT.md](../PRODUCT.md) y [DESIGN.md](../DESIGN.md).

El ejecutable auxiliar Impeccable no arrancó: intentó crear su caché en `~/.impeccable`, fuera del directorio escribible. Tampoco ejecutó `concept-seed`. Se utilizó la alternativa de lectura directa de su `SKILL.md`; no se declara que sus comandos de análisis hayan pasado. La web se verifica con Chrome headless y herramientas locales. Ninguna skill se carga como instrucción recibida por el agente financiero.

## Tipografías

Manrope y Fraunces proceden del [repositorio Google Fonts](https://github.com/google/fonts). Sus fuentes variables y licencias OFL se incluyen en `src/investiq/web/static/fonts/`, sí versionadas: son assets para ejecutar sin CDN.
