# Diseño — Web conversacional

## Requisitos y componentes

- REQ-001: HTML/CSS/JS locales en `src/investiq/web/static/`; conversación como tarea principal, catálogo lateral y controles de memoria secundarios. Impeccable guía principal (modo Operate), Taste para jerarquía y coherencia, Emil para interacción y accesibilidad. Se evita aplicar recetas de landing comercial a una app educativa.
- REQ-002: servidor HTTP de biblioteca estándar, servicio de conversación y registro de sesiones separados. Un proceso Python sirve web/API y llama `answer_turn`; ninguna credencial llega al navegador. Sin dependencias nuevas de runtime.
- REQ-003: cambios deterministas en router/handlers/diálogo y regresiones de los ejemplos de la captura. Catálogo local como fuente de nombre, símbolo y tipo; ninguna inferencia de rentabilidad.
- REQ-004: `run_web.sh`, entrada de consola y assets incluidos en el paquete; nueva ADR para interfaz local; fase de despliegue sin iniciar.

## Contrato API

- GET `/api/bootstrap`: `{instruments: [{symbol,name,kind,sector}], messages: [{role,content,sources?,status?}], memory: {enabled,summary}, mode: "local"|"configured"}`. Configurado indica presencia de configuración, nunca conectividad comprobada.
- POST `/api/chat`: `{message: string}`; devuelve `{response: AssistantResponse, memory: {enabled,summary}}`. Respuesta conserva campos del agente y `clear_history`.
- POST `/api/session/reset`: vacía conversación temporal y contexto pendiente, conserva preferencias explícitas y elección de memoria.
- POST `/api/memory`: `{enabled: boolean}` o `{forget: true}`; devuelve `{memory: {enabled,summary}}`. Olvidar elimina contexto persistente y temporal, conserva preferencias explícitas.
- GET `/api/health`: disponibilidad local sin configuración sensible.
- Fallos: `{error: string}` y HTTP apropiado; sin tracebacks. POST JSON, máximo 16 KiB, mensaje máximo 2000 caracteres, origen y host locales comprobados. Cookie HttpOnly SameSite=Strict, identificador aleatorio; retención temporal acotada. La app sigue siendo single-user local, no multiusuario autenticado.

## Estado, fuentes y seguridad

Cada sesión temporal conserva ConversationState y mensajes visibles acotados. Cada operación usa su propia SQLModel Session; el motor SQLite permite hilos. La memoria persistente sigue siendo un resumen sanitizado bajo la identidad local de instalación, como en Streamlit; no se promete aislamiento persistente entre personas. El navegador usa DOM seguro, texto externo nunca ejecutable y enlaces de fuentes validados. Modo local no oculta indisponibilidad de datos.

## Dirección visual y decisiones

Web de aprendizaje tranquila y editorial: papel claro, verde profundo, tipografía legible, conversación amplia, catálogo compacto; sin avatares robóticos, paneles de preferencias ni gráficas de mercado ficticias. Diseño provisional derivado del pedido explícito, sin atribuir una aprobación estética adicional al usuario. La herramienta de contexto Impeccable no pudo arrancar por permisos sobre su caché global; se sigue su alternativa de lectura directa. App construida desde código, sin composición gráfica previa.

ADR-001 y ADR-003 conservadas; ADR-004 modifica solo el frontend local de ADR-002. El destino cloud se revisará en su fase, sin desplegar.
