# Diseño de InvestiQ web local

La interfaz es una mesa de aprendizaje financiero en español. Su identidad parte del robot aportado por el usuario para las diapositivas. La ilustración y el video son material expresivo; las cifras dibujadas en sus pantallas no son datos de mercado.

## Mundo visual

Fondo azul hielo, tinta azul marino, cian para señales de interacción y naranja para la acción principal. Fraunces da carácter a la bienvenida; Manrope mantiene legibles la conversación y los controles. Las fuentes, el video y la imagen del profesor se sirven localmente, sin CDN.

| Token | Valor | Uso |
|---|---|---|
| Marino profundo | `#011637` | Texto principal y tarjeta destacada |
| Azul eléctrico | `#0E64A4` | Enlaces, iconos y énfasis |
| Cian holográfico | `#0AD6C8` | Señales interactivas y detalle |
| Blanco frío | `#EDF3F7` | Superficie y respiro visual |
| Naranja del casco | `#F07000` | Origen de los botones de acción; se ajusta a `#FF891D` con texto marino para lectura |
| Acero azulado | `#88A0C0` | Bordes y sombras suaves |

## Composición y comportamiento

- En escritorio, identidad, búsqueda y catálogo de símbolos forman una franja superior horizontal. «Nueva conversación» y memoria siguen visibles. En móvil, el catálogo y la memoria se abren en un panel con foco contenido.
- Cuatro tarjetas de acceso para noticias, recomendaciones guiadas, sectores NASDAQ y sectores S&P 500 destacan sobre el chat. Cada tarjeta y cada pregunta de bienvenida reinicia la sesión antes de abrir su tema. El acceso de métricas solo precarga el borrador tras el reinicio.
- El video original de diez segundos del profesor acompaña la bienvenida en su marco: se repite silenciado y sin controles. La imagen original aparece si el video no se reproduce y bajo movimiento reducido. La leyenda indica que los gráficos animados son ilustrativos. Un icono pequeño identifica al profesor en las respuestas.
- El compositor se mantiene a la vista. Las acciones dentro de una respuesta, como elegir una noticia, continúan el hilo actual.

## Reglas de sistema

- Texto financiero con fuentes y «No es asesoría financiera» en cada respuesta. Sin precios, gráficos ni rendimiento inventados.
- Contraste objetivo de 4.5:1 en texto normal, foco visible, controles táctiles adecuados y ayudas de al menos 11 px.
- Movimiento breve en hover y pulsación solo con puntero fino; `prefers-reduced-motion` impide la reproducción automática del video. El video se pausa cuando comienza el chat.
- Texto externo mediante DOM seguro; enlaces validados; tablas con desplazamiento horizontal en pantallas pequeñas.
- El fallo del reinicio muestra reintento y bloquea el envío de una nueva consulta.

## Criterio de aceptación visual

La persona debe reconocer al profesor y al tema financiero, encontrar un acceso o escribir una pregunta sin configuración previa, y leer fuentes y avisos en escritorio y móvil. La revisión usa Chrome local a 1440, 1024, 768 y 390 px e incluye estados de conversación, menú, memoria y error.

## Skills y límites

Se leyeron Taste, Impeccable y las guías de Emil Kowalski desde copias locales. El cargador auxiliar de contexto de Impeccable falló por su caché global, así que se leyó el contexto y las referencias directamente. El navegador de prueba corre sin credenciales de proveedores; no acredita integraciones financieras en vivo.
