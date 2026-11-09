---
slug: ux-ui-fundamentos
titulo: UX y UI: fundamentos
resumen: Qué distingue UX, UI, diseño de producto, de interacción y UX writing, y cómo se recorre el proceso de diseño de un problema a una pantalla construida.
lectura: 17
---

## La idea central

Una destinataria de Rumbo recibe un mensaje: «Tu pedido llega hoy entre 14 y 18 h». Ella no va a estar en casa. Lo que pase en los próximos dos minutos depende del diseño: si encuentra cómo cambiar el día, si entiende qué opciones tiene, si confía en que el cambio quedó hecho y si el transportista se entera a tiempo. Nada de eso es «hacer lindo» un botón. Es decidir qué problema se resuelve, para quién, en qué orden aparecen las cosas, qué dice cada texto y qué pasa cuando algo falla.

**UX** (experiencia de usuario) es todo lo que la persona vive al intentar lograr algo con el producto, de punta a punta. **UI** (interfaz de usuario) es la capa que toca: pantallas, componentes, textos, colores. Una buena UI sobre un flujo mal pensado sigue siendo una mala experiencia; un flujo bien pensado con una UI confusa también. Este tema da el vocabulario y el proceso para que diseñadores e ingenieros discutan esas decisiones con el mismo idioma, y muestra dónde los agentes cambian la forma de trabajar y dónde conviene desconfiar de ellos.

## Conceptos

### UX, UI, diseño de producto, de interacción y UX writing

Los términos se mezclan en las búsquedas laborales y en las conversaciones, pero designan focos distintos:

| Disciplina | Pregunta que responde | Entregable típico |
|---|---|---|
| UX | ¿La persona logra su objetivo sin fricción? | Investigación, flujos, journey maps |
| UI | ¿Cómo se ve y se organiza cada pantalla? | Diseño visual, componentes, estados |
| Diseño de interacción | ¿Cómo responde el sistema a cada acción? | Microinteracciones, transiciones, reglas de comportamiento |
| Diseño de producto | ¿Qué construimos y por qué, dado el negocio? | Problema definido, alcance, métricas, decisiones de trade-off |
| UX writing | ¿Qué dice la interfaz y con qué tono? | Textos de botones, errores, avisos, guías de voz |

En equipos chicos una persona cubre varias columnas; lo importante es que ninguna quede vacía.

**Ejemplo:** en el flujo «reprogramar entrega», UX define que la destinataria pueda reprogramar desde el mismo mensaje sin iniciar sesión; diseño de interacción define que al elegir un día se muestren solo las franjas con capacidad; UI define el selector de fechas y su estado deshabilitado; UX writing decide que el botón diga «Cambiar a jueves 14» y no «Confirmar»; diseño de producto decide si se permite reprogramar más de una vez, mirando el costo operativo.

**Por qué importa:** ante «el diseño está mal», conviene saber si el problema es de flujo, de pantalla, de comportamiento o de texto: cada uno se corrige en otro lugar.

### El proceso: doble diamante y design thinking

El **doble diamante**, propuesto por el Design Council británico, describe el proceso en cuatro fases. Cada diamante se abre (divergir: explorar muchas opciones) y se cierra (converger: elegir):

1. **Descubrir:** investigar el problema sin suponer la solución. Entrevistas, datos, tickets de soporte.
2. **Definir:** converger en un enunciado del problema claro y acotado.
3. **Desarrollar:** explorar muchas soluciones posibles, prototipar, probar.
4. **Entregar:** construir, lanzar, medir y ajustar.

**Design thinking** (en la versión difundida por la d.school de Stanford) propone cinco modos parecidos: empatizar, definir, idear, prototipar y probar. No son pasos lineales: una prueba puede devolver al equipo a definir de nuevo.

**Ejemplo:** en Rumbo, el 18 % de las entregas fallidas de un mes (unas 2.700 de 15.000) tienen como motivo «destinatario ausente». En *descubrir*, el equipo lee 200 tickets y entrevista a 8 destinatarios: muchos sabían que no iban a estar, pero no encontraron cómo avisar. En *definir* el problema queda así: «los destinatarios que saben que no estarán no tienen una forma rápida de cambiar el día antes de que salga el vehículo». En *desarrollar* se prototipan tres opciones: un enlace en el mensaje, una respuesta por texto al asistente y un llamado automático. En *entregar* se lanza el enlace a un 10 % de los pedidos y se mide la caída de ausentes.

**Por qué importa:** el primer diamante es el que más se saltea. Si se arranca en «desarrollar», se construye rápido la solución a un problema que nadie verificó.

### Encuadre del problema y jobs to be done

Encuadrar el problema es escribirlo de forma que no prescriba la solución. «Hay que agregar un botón de reprogramar» es una solución; «los destinatarios no pueden avisar que no estarán» es un problema, y admite varias respuestas.

**Jobs to be done** (JTBD) es una forma de pensar el problema desde el progreso que la persona quiere lograr, no desde sus características demográficas. Una plantilla habitual es la **job story**:

> Cuando [situación], quiero [motivación], para [resultado esperado].

La diferencia con una historia de usuario clásica («como destinataria, quiero reprogramar») es que pone el contexto en primer plano. El contexto cambia el diseño.

**Ejemplo:** «Cuando me entero a la mañana de que voy a estar fuera todo el día, quiero mover la entrega sin llamar a nadie, para no perder otro día esperando». De esta frase salen requisitos concretos: tiene que funcionar desde el teléfono, en menos de un minuto, sin registrarse, y antes de que el pedido salga a reparto (en Rumbo, hasta las 8:30).

**Por qué importa:** un problema bien encuadrado es el insumo del [PRD](#t/prd) y evita discusiones de solución que en realidad son desacuerdos sobre el problema.

### Personas y proto-personas

Una **persona** es un perfil arquetípico construido a partir de investigación real: objetivos, contexto, frustraciones y comportamientos de un grupo de usuarios. Sirve para que el equipo tome decisiones pensando en alguien concreto y no en «el usuario» abstracto, que suele terminar pareciéndose a quien diseña.

Una **proto-persona** es una versión hipotética, armada en un taller con lo que el equipo cree saber. Es útil para alinear supuestos al principio, siempre que se la marque como hipótesis y se valide después.

Los usos incorrectos más comunes:

- Inventar detalles decorativos (edad, hobbies, foto genérica) que no cambian ninguna decisión.
- Tratar una proto-persona como si fuera resultado de investigación.
- Tener doce personas: nadie recuerda más de tres o cuatro, y si todas pesan igual, ninguna guía.

**Ejemplo:** Rumbo trabaja con tres personas: **Lucía**, destinataria que trabaja fuera de casa y recibe dos o tres pedidos al mes; **Marcos**, transportista con 40 paradas diarias que usa la app con una mano; y **Sofía**, operadora de un comercio que gestiona 300 envíos por día desde el panel. Para el flujo de reprogramar, la decisión de no pedir inicio de sesión sale de Lucía; la de avisar en la app del transportista sin interrumpir la navegación sale de Marcos.

**Por qué importa:** una persona útil se nota porque resuelve discusiones: «¿Lucía haría esto?» tiene respuesta. Si nunca se la cita al decidir, no está sirviendo.

### Journey maps y service blueprints

Un **user journey map** muestra la experiencia de una persona a lo largo del tiempo, en etapas, con lo que hace, piensa y siente en cada una, y los puntos de dolor. Mira desde afuera hacia adentro.

Un **service blueprint** agrega, debajo de la línea de visibilidad, todo lo que la organización hace para sostener esa experiencia: personas de soporte, sistemas, eventos, procesos. Mira de adentro hacia afuera y es donde ingeniería encuentra su parte del problema.

**Ejemplo:** journey de Lucía para un pedido: compra, recibe confirmación, recibe aviso del día, decide si estará, reprograma, recibe el pedido. El punto de mayor frustración está en «decide si estará»: no hay forma clara de actuar. El blueprint de esa etapa muestra, en capas: el mensaje enviado por el servicio de notificaciones; la página de seguimiento; el servicio de asignación que ya asignó transportista a las 7:00; el evento `pedido.reprogramado` en Kafka que la app del transportista consume. Aparece un hueco: si Lucía reprograma después de las 7:00, el pedido ya está en una ruta y nadie lo saca. El blueprint convierte un problema de experiencia en un requisito técnico: reprogramar después de la asignación debe quitar la parada de la ruta y avisar al transportista.

**Por qué importa:** muchos problemas de UX nacen debajo de la línea de visibilidad. El blueprint es el documento donde diseño e ingeniería ven el mismo sistema.

### Arquitectura de información: card sorting y navegación

La **arquitectura de información** decide cómo se organiza y se nombra el contenido para que la gente lo encuentre. Incluye la estructura (qué va dentro de qué), los rótulos (cómo se llama cada sección) y la navegación (cómo se llega).

Dos técnicas para decidirla con datos:

1. **Card sorting:** se dan a usuarios fichas con los contenidos y se les pide agruparlas. En el *abierto* nombran ellos los grupos; en el *cerrado* usan categorías dadas. Revela cómo piensa la gente el dominio.
2. **Tree testing:** se presenta solo la estructura de navegación, sin diseño visual, y se pide encontrar algo («¿dónde cambiarías la dirección de un envío?»). Mide si la estructura funciona.

**Ejemplo:** el panel de comercios tiene «Envíos», «Operaciones» y «Logística». En un tree testing con 30 operadoras, solo el 43 % encuentra dónde reprogramar un envío en bloque: la mitad lo busca en «Envíos» y estaba en «Operaciones». Un card sorting abierto muestra que nadie usa la palabra «Operaciones»; las operadoras hablan de «Envíos del día» y «Problemas». Se reorganiza y el éxito sube al 81 %.

**Por qué importa:** los rótulos internos de la empresa (los nombres de los equipos o de los servicios) suelen filtrarse a la navegación. Para el usuario no significan nada.

### Wireframes y prototipos según su fidelidad

Un **wireframe** es un esquema de la pantalla: qué elementos hay y dónde, sin estilo visual. Un **prototipo** es algo con lo que se puede interactuar para probar un flujo. Ambos varían en **fidelidad**:

| Fidelidad | Forma | Sirve para | Costo de cambiarlo |
|---|---|---|---|
| Baja | Boceto en papel o en pizarra | Explorar muchas ideas, discutir estructura | Minutos |
| Media | Wireframe navegable en una herramienta de diseño | Probar el flujo y la jerarquía | Horas |
| Alta | Pantallas con estilo final y comportamiento realista | Probar detalles, textos, microinteracciones | Días |
| Código | Prototipo funcionando con datos reales o simulados | Probar rendimiento, datos reales, casos borde | Días o semanas |

La regla práctica: la fidelidad tiene que coincidir con la pregunta. Si la duda es «¿el enlace o el asistente?», un boceto alcanza. Si la duda es «¿se entiende el texto del selector de franjas?», hace falta alta fidelidad.

**Ejemplo:** el equipo prueba primero tres bocetos con 5 destinatarios en 20 minutos cada uno. Dos opciones se descartan. La elegida pasa a alta fidelidad y se prueba de nuevo, ahora mirando si entienden «franja» (dos de cinco no lo entienden; se cambia por «horario»).

**Por qué importa:** un prototipo de alta fidelidad demasiado temprano hace que la gente opine sobre colores en lugar de sobre el flujo, y que el equipo se resista a tirarlo.

### Flujos y estados: vacío, carga, error y casos borde

Un **flujo** es la secuencia de pasos y decisiones para completar una tarea. Diseñarlo solo con el «camino feliz» deja huecos que ingeniería después rellena improvisando. Cada pantalla tiene, como mínimo, estos estados:

- **Vacío:** no hay datos todavía (un comercio nuevo sin envíos). Es una oportunidad para explicar qué hacer.
- **Cargando:** la información está en camino. Esqueletos o indicadores, sin saltos de diseño.
- **Parcial:** hay datos, pero incompletos (la ETA aún no se calculó).
- **Error:** algo falló. Qué pasó, si es culpa de la persona o del sistema y qué hacer.
- **Éxito:** confirmación clara de que la acción quedó hecha.

Y los **casos borde** del dominio, que son los que más cuestan.

**Ejemplo:** casos borde de «reprogramar entrega»: el pedido ya salió a reparto; no hay capacidad en ninguna franja de los próximos 5 días; la destinataria ya reprogramó dos veces y el comercio lo limita a dos; el pedido es parte de un envío con varios bultos; la página se abre a las 8:29 y se confirma a las 8:31. Cada uno necesita una pantalla o un texto diseñado, no un error genérico.

**Por qué importa:** listar estados y casos borde en el diseño es, en la práctica, escribir criterios de aceptación. Es la conversación de diseño más útil para ingeniería.

### UX writing y microcopy

El **microcopy** son los textos breves de la interfaz: botones, etiquetas, ayudas, errores, confirmaciones. Algunas reglas que funcionan:

1. Botones con verbo y objeto: «Cambiar a jueves 14», no «Aceptar».
2. Lenguaje del usuario, no del sistema: «El pedido ya está en camino», no «Estado EN_RUTA, operación no permitida».
3. Errores que digan qué pasó y qué hacer: «Ese horario se completó. Quedan lugares de 18 a 21 h».
4. Lo importante primero: en el teléfono se leen las primeras cuatro palabras.
5. El mismo término para lo mismo en todo el producto: si es «horario» en un lado, no es «franja» en otro.

**Ejemplo:** la primera versión del mensaje decía «Para modificar la ventana de entrega acceda al portal». La nueva dice «¿No vas a estar? Cambia el día aquí», seguido del enlace. Con un test A/B sobre 20.000 mensajes, el porcentaje que entra al enlace pasa del 6 % al 11 %.

**Por qué importa:** el texto es parte del diseño, no un relleno. Cambiar un texto es el ajuste más barato y a veces el de mayor efecto.

### Colaboración entre diseño e ingeniería

El **handoff** es el momento en que el diseño pasa a desarrollo. Funciona mal cuando es una entrega de pantallas terminadas «por encima del muro». Funciona bien cuando:

- Ingeniería participa desde el primer diamante y avisa temprano qué es caro o imposible (por ejemplo, que la capacidad por franja no se conoce en tiempo real).
- El diseño incluye estados, casos borde, comportamiento responsive (ver [Diseño responsive](#t/responsive)) y textos finales.
- Diseño y código comparten el vocabulario de los **design tokens** y los componentes del [design system](#t/design-systems): si el diseño usa «color.estado.error», el código usa lo mismo y no un hexadecimal copiado.
- Hay una **design review** antes de cerrar el ticket: quien diseñó revisa lo construido en un entorno real, con datos reales y en un teléfono.

**Ejemplo:** en la design review del flujo, la diseñadora encuentra que con un nombre de calle largo la dirección empuja el botón fuera de la pantalla en un teléfono de 360 px. En el prototipo todas las direcciones eran cortas. Se corrige en una hora; detectado en producción habría sido un incidente.

**Por qué importa:** la mayoría de los desvíos entre diseño y producto no son desacuerdos, son detalles que nadie miró en el entorno real.

### Dónde los agentes cambian el proceso de diseño

Los LLMs y los agentes ya intervienen en casi todas las fases:

- **Síntesis de investigación:** resumir 40 entrevistas transcriptas, agrupar citas por tema, detectar patrones. Ver [Investigación de usuarios](#t/investigacion-usabilidad).
- **Generación de prototipos:** a partir de una descripción, un agente de código produce un prototipo navegable en minutos, incluso usando los componentes del design system.
- **Exploración de variantes:** generar diez versiones de un microcopy o de un layout para elegir.
- **Revisión:** pedirle a un modelo que evalúe una pantalla contra las [heurísticas de Nielsen](#t/heuristicas-nielsen) o que liste estados faltantes.

Y los riesgos:

1. **Saltar el primer diamante.** Si un prototipo cuesta cinco minutos, se prototipa sin haber definido el problema.
2. **Síntesis que inventa.** Un resumen de entrevistas puede incluir citas que nadie dijo o suavizar las quejas minoritarias.
3. **Diseño promedio.** Los modelos tienden al patrón más frecuente. Sirve como punto de partida; rara vez resuelve lo específico del dominio.
4. **Falsa fidelidad.** Un prototipo generado «se ve terminado» aunque no maneje ningún estado de error.

**Ejemplo:** un agente genera en diez minutos un prototipo del flujo de reprogramar con los componentes del panel. Es útil para una prueba con usuarios esa misma tarde. La revisión muestra que no contempla el pedido ya en reparto ni la falta de capacidad, y que el texto del botón dice «Enviar». Se usa para probar el flujo principal; los estados se diseñan a mano.

**Por qué importa:** los agentes abaratan producir artefactos, no decidir qué problema resolver. El juicio sobre el problema, los estados y el texto sigue siendo el trabajo. Las interfaces donde el producto *es* un agente tienen sus propios patrones, que se tratan en [UX para agentes](#t/ux-agentes).

## Casos prácticos

### El botón que nadie usaba

**Situación:** se agregó «Reprogramar» en la página de seguimiento. Tras un mes, solo el 2 % de los destinatarios ausentes lo usó. El equipo propone hacerlo más grande y de otro color.

**Qué se hace:** antes de tocar la UI se vuelve a *descubrir*: se revisan las analíticas y se entrevista a 6 destinatarios ausentes. Ninguno había abierto la página de seguimiento; leían solo el mensaje. El problema no era el botón sino el punto de contacto. Se agrega el enlace directo en el mensaje del día y el uso sube al 14 %. La lección: un problema de UX puede estar en un lugar distinto de donde aparece el síntoma.

### Un prototipo generado que se volvió el producto

**Situación:** un agente de código armó en una tarde un prototipo del nuevo panel de reprogramación en bloque para operadoras. Gustó tanto en la demo que se decidió «terminarlo» y publicarlo en dos semanas.

**Qué se hace:** se separa el prototipo del producto. Se lista lo que el prototipo no resolvía: estados de carga con 300 envíos, errores parciales (20 de 300 no se pudieron reprogramar), permisos por rol, accesibilidad con teclado. Se diseñan esos estados y se reescribe con los componentes del design system. El prototipo queda como referencia del flujo validado, no como base de código.

### El blueprint que destapó un problema de backend

**Situación:** la destinataria reprograma a las 7:40, ve «Listo, cambiamos tu entrega al jueves», y aun así el transportista toca el timbre a las 10:00.

**Qué se hace:** se arma el service blueprint de la etapa y se descubre que la app del transportista solo refresca la ruta al iniciar el día. El evento `pedido.reprogramado` existe, pero la app no lo consume en vivo. Se agrega la actualización en vivo de la ruta con un aviso no intrusivo al transportista, y hasta que esté lista, el texto de confirmación cambia para los pedidos ya asignados: «Avisamos a tu transportista. Si ya salió, puede que pase igual; en ese caso, no hace falta que atiendas».

## Errores comunes

- **Empezar por la solución.** «Necesitamos un chatbot» no es un problema. Escribe el problema y su evidencia antes de cualquier pantalla.
- **Diseñar solo el camino feliz.** Lista estados vacío, carga, error, parcial y los casos borde del dominio antes del handoff, y conviértelos en criterios de aceptación.
- **Personas decorativas.** Si una persona no cambia ninguna decisión, sobra. Basa las personas en investigación y cítalas al decidir.
- **Dejar el texto para el final.** Los textos provisorios terminan en producción. El microcopy se diseña junto con la pantalla y se prueba con usuarios.
- **Confundir fidelidad con avance.** Un prototipo pulido, humano o generado por un agente, no está más cerca de producción si no maneja estados ni datos reales.
- **Handoff sin design review.** Revisar lo construido en un teléfono real y con datos reales encuentra problemas que ninguna pantalla de diseño muestra.

## Para discutir en equipo

- ¿Qué flujo de Rumbo tiene hoy el mayor costo por casos borde no diseñados, y quién lo sabe mejor: soporte, operaciones o ingeniería?
- ¿Nuestras personas actuales salen de investigación o de supuestos? ¿Cuándo fue la última vez que una cambió una decisión?
- Si un agente puede generar un prototipo en minutos, ¿qué paso del proceso queremos proteger para que no se saltee?
- ¿Quién escribe hoy el microcopy de nuestras pantallas y del asistente? ¿Deberíamos tener una guía de voz compartida?
- ¿En qué momento entra ingeniería a la conversación de diseño y qué perdemos cuando entra tarde?
