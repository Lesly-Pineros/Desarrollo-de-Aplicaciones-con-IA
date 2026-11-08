# InvestiQ

<!-- impeccable:product-schema 1 -->

## Platform

web

## Usuarios y propósito

Aplicación educativa financiera en español para aprender conceptos y explorar acciones y ETF con fuentes. El usuario ha pedido una conversación humana y amigable, sin login y con preferencias que se expresan durante el chat. No ofrece asesoría financiera.

## Contexto de uso

Piloto local de una persona. El desarrollo y la ejecución pueden ocurrir en equipos distintos; uno no tiene acceso a Internet. Cada instalación conserva su propia configuración y base de datos. Los assets de interfaz deben funcionar sin CDN.

## Capacidades y restricciones

Catálogo inicial de 20 instrumentos, explicaciones educativas, consultas de movimientos con fuentes, similitud mediante clustering y comparación con preferencias explícitas. Los datos financieros y cálculos son deterministas; la redacción opcional se valida. Memoria resumida opcional, historial literal temporal y controles para consultar u olvidar contexto. La identidad persistente es compartida por la instalación local.

Los conceptos educativos pueden incluir índices fuera del catálogo negociable: S&P 500 se reconoce también como SP500 o SP 500 y se explica con fuente oficial, sin necesitar cotizaciones ni conexión para la definición. La interfaz local vigente es la web HTML/CSS/JS servida desde Python.

El profesor consulta una biblioteca local de 119 documentos sobre fundamentos, fondos, índices, bolsas, intermediarios, criptoactivos, indicadores, riesgos, operativa, costes, análisis, planificación y protección. La generación RAG utiliza pasajes recuperados con fuentes; existe respaldo local sin modelo. La biblioteca se amplía mediante documentos revisados y es independiente de la memoria personal. Los ejemplos de brókers no son recomendaciones ni confirman condiciones actuales por país.

La comparación ETF/acciones a largo plazo explica las condiciones sin garantizar rentabilidad. Los indicadores se enseñan con sus límites, sin convertirlos en órdenes de trading. La web ofrece accesos distintos para sectores NASDAQ y S&P 500. El primero usa el snapshot FMP de la última sesión disponible cuando hay cobertura completa; el segundo agrupa componentes actuales y sus cambios de cierre a cierre por sector. Ambos declaran fuente, fecha y límites, o explican por qué no hay datos verificables.

Se mantienen Python plano, SQLModel y los proveedores existentes. La nueva interfaz local no decide todavía un destino de despliegue. No se deben inventar cifras, fuentes ni afirmar que un proveedor está conectado por tener una clave configurada.

## Voz y compromisos

Nombre InvestiQ. Español cercano, preguntas breves y pertinentes; explicar desde lo que pregunta la persona. La ayuda y los símbolos consultables deben ser fáciles de encontrar. Los accesos iniciales crean una conversación nueva; el botón «Nueva conversación» permanece disponible. Las preferencias no deben convertirse en un formulario lateral. Toda respuesta conserva «No es asesoría financiera».

## Evidencia disponible

PLAN.md, decisiones, specs, catálogo local y pruebas. La captura aportada por el usuario documenta la interfaz que desea reemplazar y errores de interpretación. No se dispone de testimonios, métricas comerciales ni cotizaciones para decorar el diseño.
