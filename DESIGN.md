# Diseño de InvestiQ web local

La interfaz es una mesa de aprendizaje financiero en español. El rediseño responde al pedido del usuario de un ambiente verde, inspirado en pantallas de mercado, con superficies de vidrio y un robot profesor. No utiliza cifras decorativas ni simula actividad bursátil.

## Mundo visual

Fondo verde noche, paneles verde esmeralda translúcidos, bordes suaves y acentos lima para acciones. Fraunces da carácter a la bienvenida; Manrope mantiene legibles la conversación y los controles. Las fuentes y el SVG del profesor se sirven localmente, sin CDN.

## Composición y comportamiento

- En escritorio, identidad, búsqueda y catálogo de símbolos forman una franja superior horizontal. «Nueva conversación» y memoria siguen visibles. En móvil, el catálogo y la memoria se abren en un panel con foco contenido.
- Cuatro tarjetas de acceso para noticias, recomendaciones guiadas, sectores NASDAQ y sectores S&P 500 destacan sobre el chat. Cada tarjeta y cada pregunta de bienvenida reinicia la sesión antes de abrir su tema. El acceso de métricas solo precarga el borrador tras el reinicio.
- El profesor robot acompaña la bienvenida. Un icono pequeño lo identifica en las respuestas. La conversación sigue siendo la superficie principal para contenido y fuentes.
- El compositor se mantiene a la vista. Las acciones dentro de una respuesta, como elegir una noticia, continúan el hilo actual.

## Reglas de sistema

- Texto financiero con fuentes y «No es asesoría financiera» en cada respuesta. Sin precios, gráficos ni rendimiento inventados.
- Contraste objetivo de 4.5:1 en texto normal, foco visible, controles táctiles adecuados y ayudas de al menos 11 px.
- Movimiento breve en hover y pulsación solo con puntero fino; `prefers-reduced-motion` reduce las transiciones.
- Texto externo mediante DOM seguro; enlaces validados; tablas con desplazamiento horizontal en pantallas pequeñas.
- El fallo del reinicio muestra reintento y bloquea el envío de una nueva consulta.

## Criterio de aceptación visual

La persona debe reconocer al profesor y al tema financiero, encontrar un acceso o escribir una pregunta sin configuración previa, y leer fuentes y avisos en escritorio y móvil. La revisión usa Chrome local a 1440, 1024, 768 y 390 px e incluye estados de conversación, menú, memoria y error.

## Skills y límites

Se leyeron Taste, Impeccable y las guías de Emil Kowalski desde copias locales. El cargador auxiliar de contexto de Impeccable falló por su caché global, así que se leyó el contexto y las referencias directamente. El navegador de prueba corre sin credenciales de proveedores; no acredita integraciones financieras en vivo.
