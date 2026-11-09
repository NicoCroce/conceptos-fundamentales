---
slug: brainstorming-mapas-mentales
titulo: Brainstorming y mapas mentales
resumen: Cómo generar muchas ideas en grupo sin que gane la voz más fuerte, cómo converger, y cómo usar mapas mentales y LLMs para explorar problemas.
lectura: 12
---

## La idea central

Generar ideas y evaluarlas son dos tareas distintas que se hacen mal al mismo tiempo. Si alguien propone algo y otra persona responde enseguida «eso no escala», la idea muere junto con las que podían salir de ella. El **brainstorming** (lluvia de ideas) separa las dos fases: primero se **diverge** (se busca cantidad y variedad sin juzgar) y después se **converge** (se agrupa, se compara y se elige). El problema es que la versión clásica, todos hablando en una sala, rinde bastante menos de lo que promete; hay variantes simples que funcionan mejor.

El **mapa mental** es la herramienta complementaria para pensar solo o en grupo: una idea en el centro y ramas que se abren por asociación. Sirve para explorar un problema antes de saber cómo se divide. En sistemas con agentes, las dos técnicas ganan un participante nuevo: un LLM puede generar decenas de opciones en segundos o agrupar cien notas adhesivas, pero también puede anclar a todo el equipo en sus primeras ideas si se usa sin cuidado.

## Conceptos

### Las reglas del brainstorming

Las reglas clásicas son cuatro, y cada una ataca un freno concreto:

1. **Cantidad antes que calidad.** Las buenas ideas suelen aparecer después de las obvias. Si la sesión termina con 8 ideas, probablemente son las 8 que todos ya tenían en la cabeza.
2. **Juicio diferido.** Nadie critica durante la fase de generación, ni con palabras ni con gestos. La evaluación tiene su momento.
3. **Construir sobre las ideas de otros.** «Sí, y además…» en lugar de «sí, pero…». Una idea mala puede ser el escalón hacia una buena.
4. **Las ideas extrañas son bienvenidas.** Es más fácil bajar a tierra una idea exagerada que estirar una tímida.

Una sesión también necesita una **pregunta bien formulada**: «¿cómo mejoramos las entregas?» es demasiado amplia; «¿cómo podríamos reducir las entregas fallidas por destinatario ausente en la zona norte?» da foco sin cerrar soluciones.

**Ejemplo:** el equipo de operaciones de Rumbo hace una sesión de 20 minutos con la pregunta «¿cómo podríamos lograr que el destinatario esté en casa cuando llega el pedido?». Con las reglas a la vista, salen 46 ideas; entre ellas, una exagerada («que el transportista llame a cada destinatario») que deriva en una viable: un aviso automático 30 minutos antes con opción de dejar el pedido a un vecino.

**Por qué importa:** sin reglas explícitas, la primera crítica marca el tono y la sesión se convierte en una reunión de evaluación con pocas ideas.

### Por qué el brainstorming en grupo rinde menos

La investigación sobre grupos muestra de forma bastante consistente que varias personas pensando por separado y juntando después sus ideas producen más ideas, y más variadas, que el mismo número de personas haciendo brainstorming en voz alta. Hay tres causas principales:

- **Bloqueo de producción:** solo una persona habla a la vez; mientras espera su turno, la otra olvida o descarta su idea.
- **Anclaje:** las primeras ideas dichas orientan todas las siguientes. Si alguien abre con «mejor geocodificación», la próxima media hora gira alrededor de direcciones.
- **La voz más fuerte:** quien tiene más jerarquía o confianza habla primero y más; las personas nuevas o calladas se autocensuran.

**Ejemplo:** 8 personas en 30 minutos, con intervenciones de un minuto, tienen como máximo unos 30 turnos. Si cada una escribe en silencio 5 minutos, a una idea por minuto, el grupo junta unas 40 ideas antes de que nadie hable.

**Por qué importa:** el problema no es la gente sino el formato. Cambiar el formato cuesta poco y mejora el resultado.

### Variantes que funcionan mejor

Todas comparten un principio: **primero pensar en silencio, después compartir**.

- **Silencio y puesta en común:** 5 a 8 minutos de escritura individual, una idea por nota; después cada persona lee las suyas sin debate.
- **Brainwriting 6-3-5:** 6 personas, cada una escribe 3 ideas en 5 minutos y pasa la hoja a la siguiente, que agrega 3 ideas nuevas inspiradas en las anteriores. En 6 rondas (30 minutos) se llega a un máximo de 108 ideas, muchas construidas sobre otras.
- **1-2-4-todos:** 1 minuto solo, 2 minutos en pares, 4 minutos en grupos de cuatro y 5 minutos con todo el grupo. Cada paso filtra y combina; las ideas de la persona más callada llegan al plenario ya respaldadas por su pareja.
- **Tablero remoto:** pizarra compartida con notas anónimas y temporizador. El anonimato reduce el peso de la jerarquía y la escritura simultánea elimina el bloqueo.

| Formato | Tiempo típico | Mejor para | Cuidado con |
|---|---|---|---|
| Brainstorming en voz alta | 20 a 30 min | Grupos chicos y con confianza | Anclaje y voz más fuerte |
| Silencio y puesta en común | 15 a 20 min | Casi todo | Lectura larga si hay muchas notas |
| 6-3-5 | 30 min | Profundizar sobre ideas ajenas | Requiere grupo de tamaño fijo |
| 1-2-4-todos | 12 a 15 min | Grupos grandes y mixtos | Los pares pueden descartar ideas raras |
| Tablero remoto | 15 a 25 min | Equipos distribuidos | Notas duplicadas en masa |

**Ejemplo:** 12 personas de soporte, operaciones e ingeniería usan 1-2-4-todos con la pregunta «¿qué consultas al asistente deberían resolverse sin una persona?». En 13 minutos llegan al plenario 3 propuestas por grupo de cuatro, 9 en total, ya discutidas y combinadas.

**Por qué importa:** con el mismo tiempo de reunión, estos formatos producen más ideas y dan voz a quienes normalmente no la toman.

### Converger: afinidad, votación y priorización

Generar 80 ideas no sirve si no se decide nada. La convergencia tiene tres pasos:

1. **Agrupamiento por afinidad:** se juntan en silencio las notas que hablan de lo mismo y recién después se nombra cada grupo, para no forzar las ideas en categorías decididas de antemano.
2. **Votación por puntos (dot voting):** cada persona reparte un número fijo de votos, por ejemplo 3, entre ideas o grupos. Se vota en silencio y a la vez, para evitar el efecto manada.
3. **Priorización:** lo más votado no es lo que se hace; es lo que se evalúa en serio. Ahí entran el impacto, el esfuerzo y el riesgo, con las herramientas de [priorización](#t/priorizacion).

**Ejemplo:** las 46 ideas de la sesión sobre destinatarios ausentes se agrupan en 7 temas. Con 3 votos por persona y 8 personas, el resultado es:

```barras
titulo: Votos por tema (8 personas, 3 votos)
unidad: votos
Aviso previo con ventana | 7
Entrega a vecino o punto de retiro | 6
Reprogramar desde el chat | 5
ETA más precisa | 3
Notas del comercio más claras | 2
Otros | 1
```

Los tres primeros pasan a una matriz de impacto y esfuerzo; «reprogramar desde el chat» es el más costoso porque el asistente con LLM ejecuta una acción.

**Por qué importa:** la votación ordena la conversación pero no la reemplaza. Un tema con pocos votos puede ser el único que ataca una causa de fondo.

### Mapas mentales

Un mapa mental tiene una **idea central** en el medio y **ramas** que salen de ella. Cada rama principal es un tema; de cada una salen subideas, y de esas, más detalle. Las reglas prácticas son pocas:

- **Palabras clave**, no oraciones: «geocodificación dudosa» y no «a veces la geocodificación de la dirección no es confiable».
- **Un color por rama principal**, para ver de un vistazo qué pertenece a qué tema.
- **Asociación libre:** una subidea puede aparecer en dos ramas; el mapa no necesita ser exhaustivo ni prolijo.

**Ejemplo:** mapa mental de un ingeniero que prepara una sesión sobre entregas fallidas:

```arbol
titulo: Mapa mental de entregas fallidas
Reducir entregas fallidas
- Dirección
-- Validar al cargar el pedido
-- Geocodificación dudosa
-- Referencias del destinatario
- Destinatario ausente
-- Aviso previo con ventana
-- Reprogramar desde el chat
-- Punto de retiro cercano
- Transportista
-- Ruta mal ordenada
-- Sin señal en la zona
-- Capacitación en zonas nuevas
- Ventana horaria
-- ETA más precisa
-- Ventanas más cortas
-- Avisar demoras en vivo
- Comercio
-- Datos incompletos
-- Notas confusas
- Medición
-- Motivo de falla estandarizado
-- Pareto mensual de motivos
```

**Por qué importa:** el mapa hace visible la forma del problema antes de decidir cómo atacarlo, y muestra ramas vacías que nadie había pensado.

### Cuándo un mapa mental, una lista o una EDT

El mapa mental sirve para **explorar**: entender un problema nuevo, preparar una charla, ordenar ideas antes de escribir un documento. No sirve para **ejecutar**: no tiene orden ni responsables y no garantiza que esté todo.

- Si importa la **secuencia** (pasos de un runbook, agenda de una reunión), conviene una lista numerada.
- Si hay que descomponer un **entregable** en paquetes de trabajo completos y sin solapamientos, conviene una [EDT o WBS](#t/wbs-edt), que sigue la regla de cubrir el 100 % del alcance.
- Si hay que buscar la **causa** de un problema concreto, sirven más los [5 porqués](#t/cinco-porques) o un Pareto.

**Ejemplo:** el mapa de entregas fallidas sirve para la sesión de ideas; cuando se decide construir el aviso previo, el trabajo pasa a una EDT (mensajería, plantilla, ventana, métricas).

**Por qué importa:** usar el mapa mental como plan de proyecto deja huecos; usar una EDT para explorar mata la asociación libre.

### Un LLM como compañero de brainstorming

Un LLM es muy bueno en la fase divergente: produce 40 opciones en segundos y no teme quedar mal. Pero sus respuestas tienden a las ideas más típicas, las más frecuentes en sus datos de entrenamiento, y quien lee primero su lista queda anclado en ella, igual que en una sala con una voz fuerte.

Una forma de usarlo bien:

1. **Pensar primero sin el modelo.** Cada persona escribe sus ideas en silencio; recién después se consulta al LLM.
2. **Pedir diversidad explícita:** «dame 30 ideas en al menos 6 categorías distintas», «10 ideas que un operador de logística consideraría absurdas», «ideas que no requieran tecnología».
3. **Pedir lo contrario:** «¿cómo lograríamos que fallen más entregas?» y después invertir cada respuesta.
4. **Juzgar con criterio humano.** El modelo no conoce los costos, las restricciones legales ni la historia del equipo. Sus ideas entran al mismo tablero que las demás y se votan igual.

**Ejemplo:** de las 10 ideas que el LLM da para reducir entregas fallidas, 8 ya estaban en el tablero. Con el pedido «ideas desde el punto de vista del destinatario, del edificio y del barrio» aparecen 3 nuevas, entre ellas coordinar con encargados de edificio.

**Por qué importa:** el modelo sirve para ampliar el espacio de ideas; consultado primero, lo achica.

### Un LLM para agrupar y un mapa como contexto

Tras una sesión remota es común tener 120 notas, muchas repetidas. Un LLM puede proponer grupos de afinidad, con un nombre y los identificadores de las notas de cada uno. Ahorra media hora, pero se revisa: a veces junta notas por palabras parecidas aunque hablen de otra cosa, o deja afuera una idea rara.

El mapa mental también sirve como **contexto para una especificación**: las ramas se convierten en secciones de un [PRD](#t/prd) o de la especificación para un agente de código.

**Ejemplo:** 118 notas se pasan al LLM con la instrucción «agrupa por tema, no inventes notas, lista aparte las que no encajan». Devuelve 9 grupos y 6 notas sueltas. El equipo corrige 2 grupos y rescata una nota suelta («avisar al destinatario por el canal que usa el comercio») que termina siendo una idea votada.

**Por qué importa:** la clasificación es una tarea donde el LLM ahorra tiempo y el error es fácil de revisar, siempre que se le pida que no descarte nada.

## Casos prácticos

### Una sesión remota que siempre ganaba el mismo

**Situación:** en las sesiones de ideas del asistente de soporte, el tech lead habla primero y todo gira en torno a su idea. Las dos personas nuevas casi no participan.

**Qué se hace:** se pasa a un tablero remoto con notas anónimas y 7 minutos de escritura en silencio. El tech lead escribe sus ideas, pero las presenta al final. La sesión siguiente produce 64 notas frente a las 20 habituales, y la idea más votada (un resumen automático del caso cuando el ticket pasa a una persona) viene de una de las personas nuevas.

### El LLM que dio las mismas ideas de siempre

**Situación:** para ahorrar tiempo, el equipo abre una sesión pidiéndole al LLM ideas para reducir el costo de tokens del asistente. Se discuten 20 minutos las 10 ideas del modelo (caché, modelo más chico, resúmenes) y no aparece nada nuevo.

**Qué se hace:** en la sesión siguiente se invierte el orden: 8 minutos de ideación individual, puesta en común y recién después el LLM, con el pedido de ideas «que no sean técnicas» y «que cambien el producto». Aparecen ideas como mostrar el estado del pedido antes de abrir el chat, que evita conversaciones enteras. El modelo aporta variaciones, pero no domina la sesión.

### Del mapa mental a la especificación

**Situación:** una ingeniera tiene que escribir la especificación de «reprogramar desde el chat» y no sabe por dónde empezar: hay temas de producto, permisos del agente, mensajes y métricas.

**Qué se hace:** arma un mapa mental en 15 minutos con ramas para destinatario, comercio, agente, seguridad y métricas. La rama de seguridad deja ver una pregunta que no estaba en el pedido original: qué pasa si las notas del comercio traen instrucciones para el agente. El mapa se convierte en el índice del PRD y la rama de seguridad, en una sección con requisitos de confirmación humana.

## Errores comunes

- **Criticar durante la generación.** Un «eso ya lo probamos» en el minuto dos apaga la sesión; se anota y se discute en la convergencia.
- **Empezar hablando en voz alta.** Sin unos minutos de silencio, el anclaje y la jerarquía deciden el resultado; siempre primero escribir.
- **Confundir votos con decisión.** La votación dice qué evaluar en serio, no qué construir; después viene la priorización con impacto y esfuerzo.
- **Consultar al LLM antes que al equipo.** Ancla a todos en las ideas más típicas; se usa después y con pedidos de diversidad explícitos.
- **Aceptar el agrupamiento del LLM sin revisar.** Puede mezclar temas o perder ideas raras; se le pide que liste lo que no encaja y una persona revisa.
- **Usar el mapa mental como plan.** Para ejecutar hace falta una lista o una EDT con responsables y alcance completo.

## Para discutir en equipo

- ¿En nuestras últimas sesiones de ideas, quién habló primero y cuánto influyó en el resultado?
- ¿Qué formato (silencio, 6-3-5, 1-2-4-todos) probaríamos en la próxima sesión y con qué pregunta?
- ¿En qué momento de una sesión conviene sumar a un LLM, y qué le pediríamos para que aporte variedad?
- ¿Qué decisiones recientes se tomaron por votación sin pasar por una priorización con datos?
- ¿Para qué documentos o charlas nos habría servido empezar con un mapa mental?
