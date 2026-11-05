# Diseño de InvestiQ web local

La nueva superficie es una aplicación de conversación para aprender, construida desde código. Esta dirección parte del pedido de reemplazar Streamlit por una web amigable; no presupone una aprobación estética adicional del usuario.

## Mundo visual

Un cuaderno de consulta contemporáneo: superficies claras cálidas, tinta verde profunda y composición editorial tranquila. Fraunces aporta carácter a los títulos; Manrope facilita la lectura y los controles. Ambas fuentes variables se sirven localmente con sus licencias OFL.

## Composición y comportamiento

La conversación ocupa el centro y domina la lectura. Un lateral compacto reúne identidad, propósito, nueva conversación y catálogo de instrumentos. En móvil se recoge en un menú accesible. La bienvenida ofrece caminos concretos que envían preguntas reales; desaparece al comenzar el chat. El compositor permanece disponible sin tapar mensajes.

Las respuestas no usan avatares de robot. Las fuentes se muestran como referencias legibles, el aviso educativo acompaña cada respuesta y los estados de carga/error permiten entender qué ocurre. La memoria tiene controles secundarios explícitos; las preferencias se conversan.

## Reglas de sistema

- Espaciado coherente, texto de conversación de ancho limitado y títulos con escala clara.
- Contraste mínimo 4.5:1 en texto normal; foco visible y blancos táctiles cómodos.
- Iconos SVG con geometría y trazo consistentes; sin emoji como sistema de interfaz.
- Interacciones breves; transiciones de propiedades explícitas, hover solo con puntero y respeto de movimiento reducido.
- Ninguna gráfica, precio, ganancia ni actividad de mercado se fabrica para llenar espacio.
- Texto externo mediante DOM seguro, enlaces de fuentes validados y tablas contenidas en pantallas pequeñas.

## Contrato de dirección de la superficie

| Bloque | Compromiso comprobable |
|---|---|
| TYPE | Fraunces en bienvenida; Manrope en diálogo y controles. Avisos, ayudas y referencias de al menos 11 px. |
| MATERIAL | Superficies planas de lectura y divisores finos; sin cristales, fotografías ajenas ni cifras decorativas. |
| GROUND | Papel `#f9f8f4`, lateral `#efeee7`, tinta verde `#1d453b`; texto secundario `#59675a` con contraste medido. |
| COMPOSITION | Conversación central, catálogo compacto a la izquierda, compositor visible; menú lateral adaptable en móvil. |
| INTERACTION | Preguntas reales desde sugerencias/catálogo, carga y reintento visibles, foco recuperable y memoria controlable. |

**QUALITY BAR:** una persona puede entender para qué sirve InvestiQ, iniciar una pregunta y encontrar los símbolos sin configurar preferencias. A 1440, 1024, 768 y 390 px no hay desplazamiento horizontal de página ni compositor tapado. Las fuentes y el aviso financiero siguen legibles en el chat. Se revisan también conversación, menú, memoria y error, no solo la bienvenida. Esta es una dirección construida desde código y derivada del encargo; no existe un comp gráfico aprobado.

## Skills y límites

Impeccable es la guía principal (Operate); Taste contribuye criterios de jerarquía y coherencia, Emil los detalles de interacción. Las recetas comerciales de Taste no se aplican como una landing a esta herramienta. El ejecutable auxiliar de Impeccable no pudo cargar contexto ni generar direcciones porque su caché global no está disponible; se siguió la alternativa de lectura directa de sus referencias. No se atribuyen resultados a ese ejecutable.

La evidencia visual se genera con Chrome headless local en escritorio, tablet y móvil; las pruebas de proveedores externos se reportan por separado.
