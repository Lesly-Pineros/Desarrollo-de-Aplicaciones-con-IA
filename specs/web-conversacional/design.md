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

## Extensión visual y de navegación — REQ-005

La nueva dirección solicitada sustituye la composición de cuaderno claro: fondo verde profundo, paneles de vidrio claros y oscuros con suficiente opacidad para leer, acentos verde lima y tipografía local existente. El profesor robot es una ilustración SVG original integrada en la bienvenida y un identificador pequeño en respuestas; no representa actividad ni precios. El catálogo pasa a una franja horizontal de instrumentos en escritorio, con búsqueda. En móvil conserva un explorador en diálogo lateral accesible, porque allí el ancho no permite mantener la franja y el chat a la vez. La navegación superior muestra tarjetas de acceso a noticias, exploración guiada, NASDAQ y S&P 500; la bienvenida conserva las preguntas de inicio y la preparación de métricas.

El navegador usa una tabla local de accesos con las consultas canónicas. Tanto las tarjetas superiores como las sugerencias invocan una transición única: POST `/api/session/reset`, vaciado visual de mensajes y contexto, luego POST `/api/chat` con la consulta o acción, o prellenado de la caja en métricas. El reinicio falla de manera visible sin enviar el segundo POST. La función de reintento de `/api/chat` trabaja en la nueva sesión y no vuelve a reiniciarla. El botón «Nueva conversación» llama solo al primer POST. El servidor y los contratos de proveedores permanecen como están; la respuesta y las fuentes se renderizan como nodos DOM seguros.

Verificación prevista: comprobaciones de navegador a 1440, 1024, 768 y 390 px sobre bienvenida, chat, catálogo y menú; comprobar que los dos accesos a una misma consulta generan un chat nuevo, que el prellenado no envía, que una acción de noticia conserva su contexto y que los estados de fallo/reintento no duplican mensajes. Contraste, foco, desbordamiento, `prefers-reduced-motion` y shell móvil se revisan con capturas reales.
## Extensión multimedia — REQ-006

La referencia visual es la imagen «Robot de Trading con Hologramas» aportada por el usuario. Los tokens se extraen de sus zonas opacas: marino `#011637`, azul `#0E64A4`, cian `#0AD6C8`, blanco frío `#EDF3F7` y naranja intenso `#F07000`. El nuevo MP4 H.264 contiene un fondo oscuro opaco; se convierte fuera de ejecución a WebM VP9 con alfa y se conserva el MP4 original como alternativa. La bienvenida muestra la animación como ilustración 16:9 sin marco opaco, silenciada y en bucle, sin controles. La imagen original sirve de respaldo cuando la reproducción falla o el usuario prefiere movimiento reducido. Se detiene al entrar al chat para evitar trabajo invisible. La leyenda marca las gráficas como ilustrativas. Se preserva la API y el comportamiento de los accesos.
