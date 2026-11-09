---
slug: comunicacion-asertiva
titulo: Comunicación asertiva
resumen: Cómo decir lo que se piensa y se necesita con claridad y respeto, en conversaciones, en Slack, en PRs y en los pedidos a agentes.
lectura: 12
---

## La idea central

Comunicar de forma **asertiva** es decir con claridad lo que uno observa, piensa y necesita, sin pasar por encima del otro y sin esconderse. La persona asertiva defiende su posición (el plazo no da, el diseño tiene un riesgo, el PR no está listo) y al mismo tiempo trata la posición del otro como legítima.

En ingeniería esto tiene consecuencias concretas. Un riesgo que nadie dice en voz alta termina en un incidente; un "sí" que en realidad era un "no" termina en un sprint que no cierra; un comentario agresivo en un PR hace que la próxima vez el autor no pida revisión. Y hay un costado nuevo: escribir para un agente de código o un LLM es, en buena medida, comunicación asertiva. Un agente no adivina lo que no se dijo; necesita observaciones claras, un pedido explícito, restricciones y criterios de aceptación. Las mismas habilidades sirven para las dos audiencias.

## Conceptos

### Los cuatro estilos con la misma situación

Hay cuatro formas típicas de responder cuando algo nos afecta. Se entienden mejor con un solo caso.

**Ejemplo:** es jueves; Lucía, de producto, pide sumar "reprogramar entrega desde el chat" para la demo del lunes con un comercio grande. Martín, ingeniero del asistente de soporte, está terminando la migración del índice de RAG, comprometida para el mismo lunes.

- **Pasivo:** "Bueno, está bien, veo cómo lo hago." Martín no dice que no entra. Trabaja el fin de semana o llega el lunes con las dos cosas a medias. Respeta al otro, no se defiende a sí mismo.
- **Agresivo:** "Siempre lo mismo, ustedes prometen cosas sin preguntar. No se puede." Defiende su posición, pero ataca a la persona y generaliza ("siempre", "ustedes").
- **Pasivo-agresivo:** "Claro, como todo es para ayer, lo hago. Ya vamos a ver cómo sale la migración." Dice que sí, pero con ironía, y deja una amenaza velada. No defiende nada con claridad y además daña la relación.
- **Asertivo:** "Entiendo que la demo del lunes es importante. Con lo que tengo hoy no llego a las dos cosas con calidad: la migración necesita dos días más de pruebas. Puedo hacer una versión mínima de reprogramar si movemos la migración al miércoles, o mantener la migración y mostrar la reprogramación con un prototipo. ¿Cuál te sirve más para la demo?"

La versión asertiva reconoce lo que importa al otro, dice el hecho, lo explica con datos y ofrece opciones con un pedido.

```cuadrante
titulo: Estilos de comunicación
eje-x: Poca defensa de lo propio | Mucha defensa de lo propio
eje-y: Poco respeto por el otro | Mucho respeto por el otro
arriba-izquierda: Pasivo | Sí que es no; riesgo callado
arriba-derecha: Asertivo | Hechos, opciones y pedido
abajo-izquierda: Pasivo-agresivo | Ironía; sí con amenaza
abajo-derecha: Agresivo | Ataque; siempre y nunca
```

**Por qué importa:** el estilo pasivo parece el más cómodo, pero es el que más sorpresas produce. Se planifica sobre un "sí" que no era real.

### Mensajes en primera persona frente a acusaciones

Una acusación en segunda persona ("tú rompiste el deploy", "nunca avisas") pone al otro a la defensiva: en lugar de escuchar el problema, se defiende. Un mensaje en primera persona habla de lo que uno vio y de cómo lo afecta, sin atribuir intenciones.

La fórmula práctica es: **cuando pasa X, a mí me genera Y, y necesito Z**.

**Ejemplo:**

- Acusación: "Tú siempre fusionas sin esperar la revisión."
- Primera persona: "Cuando un PR se fusiona antes de que termine la revisión, me quedo sin poder marcar los problemas de latencia a tiempo. Necesito que esperemos al menos una aprobación en el servicio de asignación."

Ojo: "siento que eres un desprolijo" sigue siendo una acusación. Se describe el comportamiento y su efecto, no a la persona.

**Por qué importa:** quien se siente acusado discute la acusación y no el problema.

### Separar hechos de interpretaciones

Muchos conflictos vienen de tratar una interpretación como un hecho. "No le importa la calidad" es una interpretación; "el PR no tiene tests para el caso de pedido cancelado" es un hecho. El hecho se puede verificar y conversar; la interpretación solo se puede discutir.

Un ejercicio útil antes de escribir un mensaje difícil:

1. Anotar qué pasó, como lo registraría una cámara: horarios, números, archivos, frases textuales.
2. Anotar qué se concluyó a partir de eso.
3. Enviar el punto 1 y, si hace falta, el 2 como hipótesis, con signo de pregunta.

**Ejemplo:** Ana, de operaciones, escribe "El agente de operaciones no sirve, inventa causas". Un ingeniero lo traduce a hechos: "En 3 de las 12 investigaciones de esta semana, el agente atribuyó la caída de entregas a tiempo al clima sin consultar la herramienta de clima. En las otras 9 la causa coincidió con la que encontró la persona de guardia". Con esa frase, el problema ya tiene forma de bug.

**Por qué importa:** los hechos llevan a acciones; las interpretaciones llevan a defensas. Es la base del postmortem sin culpas (ver [On-call, runbooks e incidentes](#t/on-call)).

### Decir que no y negociar prioridades

Un "no" asertivo no es un portazo: es un **no a esto, ahora, en estas condiciones**, acompañado de lo que sí se puede hacer.

Tres herramientas ayudan:

1. **Hacer visible el costo:** "si sumo esto, sale X".
2. **Hablar en términos del triángulo de alcance, tiempo y costo.** Si el plazo es fijo y la gente también, lo que se negocia es el alcance (ver [Triángulo de hierro](#t/triangulo-hierro)).
3. **Remitir a la priorización acordada.** Si el equipo usa RICE o una matriz de impacto y esfuerzo, el pedido nuevo entra en la misma comparación (ver [Herramientas de priorización](#t/priorizacion)).

**Ejemplo:**

- Mal: "No tenemos tiempo." (No explica, no ofrece nada.)
- Mejor: "Esta semana tenemos comprometidos la migración del índice y la alerta de PII en logs. Puedo sumar el reporte para el comercio si lo hacemos con los datos del tablero actual, sin filtros nuevos, o puedo hacerlo completo la semana que viene. ¿Qué prefieres?"

**Por qué importa:** un equipo que no sabe decir que no promete de más, entrega tarde y pierde credibilidad justo cuando más la necesita.

### Escucha activa

La comunicación asertiva incluye escuchar. **Escucha activa** significa demostrar que se entendió antes de responder. Tiene tres herramientas:

- **Parafrasear:** repetir con palabras propias lo que dijo el otro. "Entonces, lo que te preocupa no es la demo en sí, sino que el comercio vea que el asistente no entiende pedidos con dos direcciones. ¿Es así?"
- **Preguntar para entender, no para ganar:** "¿Qué pasaría si la demo muestra solo el caso simple?" en lugar de "¿Y de verdad te parece que eso es urgente?".
- **Tolerar el silencio:** después de una pregunta, esperar; lo importante suele llegar en la segunda frase.

**Ejemplo:** soporte de un transportista dice "el asistente les responde cualquier cosa". En lugar de defender el modelo, el ingeniero pregunta: "¿Respuestas incorrectas o respuestas que no aplican a su caso? ¿Me pasas dos o tres ejemplos?". El problema era que el asistente usaba políticas de comercios para responder a transportistas: un filtro de documentos en el RAG, no el modelo.

**Por qué importa:** responder a lo que uno cree que el otro dijo es la forma más rápida de resolver el problema equivocado.

### El modelo de comunicación no violenta

La **comunicación no violenta** (CNV) propone cuatro pasos para expresar algo difícil. Es un buen esqueleto para mensajes delicados:

1. **Observación:** qué pasó, sin juicio.
2. **Sentimiento:** cómo me afecta (en el trabajo, a veces alcanza con "me preocupa" o "me cuesta").
3. **Necesidad:** qué necesito o qué valor está en juego.
4. **Pedido:** una acción concreta, realizable y negociable.

**Ejemplo:** "En las últimas dos guardias, las alertas de la zona norte sonaron 14 veces de noche y 11 se cerraron sin acción (observación). Me preocupa que empecemos a ignorarlas (sentimiento). Necesito confiar en que una alerta nocturna significa algo real (necesidad). ¿Podemos revisar juntos los umbrales el martes y bajar a advertencia diurna las que no requieren acción? (pedido)".

**Por qué importa:** sirve como lista de control; si falta el pedido, el otro no sabe qué hacer con el mensaje.

### Comunicación escrita y asincrónica

En Slack, en un PR o en un documento falta el tono de voz, la cara y la posibilidad de aclarar al instante. Lo que en persona suena neutro, por escrito puede sonar seco o irritado. Algunas reglas:

- **Dar contexto en el mismo mensaje**, para evitar idas y vueltas.
- **Hacer explícito el pedido y el plazo.** Un mensaje sin pedido se lee y se olvida.
- **Evitar la ambigüedad.** No "esto está raro", sino "la latencia p99 del servicio de asignación pasó de 38 a 61 ms después del deploy de las 11:20".
- **Cuidar el tono.** Preguntas genuinas, no retóricas ("¿Qué pasa si el pedido ya fue retirado?", no "¿No pensaste en los retirados?"). Sin mayúsculas, sin "obviamente" ni "simplemente".
- **Decir qué tipo de respuesta se espera.** "Solo para que estén al tanto, no requiere acción" ahorra mucha ansiedad.

**Ejemplo:**

- Mal: "¿Tienes un minuto?"
- Mejor: "¿Puedes revisar el PR 482 antes de las 15? Cambia el timeout del cliente de ETA y quiero desplegarlo antes del pico de la tarde."

**Por qué importa:** un mensaje claro ahorra una reunión; uno ambiguo genera tres.

### Estar en desacuerdo en una revisión de diseño

En una revisión de arquitectura el desacuerdo es parte del trabajo. Lo asertivo es decirlo con argumentos, separar la idea de la persona y, una vez tomada la decisión, comprometerse con ella. Esta última parte se conoce como **disagree and commit** (estar en desacuerdo y comprometerse): se discute a fondo antes de decidir; después, se ejecuta la decisión como si fuera propia, sin sabotearla ni repetir "yo avisé".

**Ejemplo:**

- Mal: "Esto con Kafka es sobreingeniería, no tiene sentido."
- Mejor: "Me preocupa sumar Kafka para un flujo de 200 eventos por hora: agrega un componente más para operar en on-prem. ¿Evaluamos una cola en la base con el patrón outbox? Si el equipo decide Kafka igual, propongo que dejemos escrito el umbral de volumen que lo justificó."

Si se elige Kafka, Martín lo implementa bien y deja su preocupación en el ADR como riesgo, con un disparador para revisarla.

**Por qué importa:** una decisión que se rediscute en cada PR nunca termina de tomarse.

### Escribirle a un agente también es comunicación asertiva

Un prompt para un agente de código tiene los problemas de un mensaje ambiguo a un colega, amplificados: el agente pregunta poco y completa los huecos con suposiciones plausibles. Los principios se traducen casi uno a uno:

| Principio asertivo | En un prompt o una especificación |
|---|---|
| Hechos, no interpretaciones | Describir el comportamiento actual con datos: "el endpoint devuelve 500 cuando el pedido no tiene zona" |
| Pedido explícito | Una tarea concreta: "agrega validación y devuelve 422 con el mensaje X" |
| Decir que no | Restricciones y no-objetivos: "no cambies el esquema de la tabla de pedidos" |
| Criterio compartido de éxito | Criterios de aceptación verificables: "el test `TestPedidoSinZona` pasa" |

**Ejemplo:**

- Ambiguo: "Mejora el manejo de errores del cliente de ETA."
- Asertivo: "En `cliente_eta.go`, cuando el modelo tarda más de 40 ms, hoy se propaga el error y la asignación falla. Quiero que en ese caso se use la ETA por distancia como respaldo y se registre una métrica `eta_fallback_total`. No cambies la firma pública del cliente. Hecho cuando: hay un test con un servidor lento simulado y la métrica aparece en `/metrics`."

Este es el mismo criterio que proponen [SDD](#t/sdd) y el prompt engineering: lo que no se dice, el modelo lo inventa.

**Por qué importa:** cada ambigüedad del pedido se vuelve una suposición del agente, y revisarla cuesta más que evitarla.

### Comunicar sobre IA sin sobrevender

Al presentar una funcionalidad con LLM, la tentación es mostrar el mejor caso. Lo asertivo es decir qué hace, qué tan bien, dónde falla y qué se hace cuando falla.

**Ejemplo:**

- Sobrevendido: "El asistente resuelve las consultas de los transportistas."
- Claro: "En la evaluación con 400 consultas reales, el asistente respondió bien el 86%. Falla sobre todo en consultas con dos pedidos mezclados. Cuando no tiene confianza, deriva a una persona. Esperamos que en producción el número sea algo menor, porque las consultas reales son más variadas que las de la evaluación."

**Por qué importa:** las expectativas infladas convierten un buen resultado en una decepción.

## Casos prácticos

### El "sí" del jueves que se volvió un fin de semana

**Situación:** en la planning, un ingeniero acepta sin objetar dos ítems que sabe que no entran. No quiere parecer poco comprometido. El viernes avisa que la integración con el nuevo transportista no llega.

**Qué se hace:** en la retrospectiva se acuerda una regla explícita: en la planning, cada persona dice en voz alta su nivel de confianza (alto, medio, bajo) para lo que toma, y un "bajo" abre una conversación de alcance, no un reproche. El tech lead modela la conducta diciendo primero sus propias dudas. A los dos sprints, los "bajos" aparecen el lunes y no el viernes.

### Un prompt que el agente interpretó a su manera

**Situación:** una ingeniera pide al agente de código "limpia el módulo de notificaciones". El agente borra funciones que parecían sin uso, renombra variables y cambia el formato de los SMS. Dos de las funciones borradas se usaban por reflexión desde un job nocturno.

**Qué se hace:** se revierte y se reescribe el pedido con estructura asertiva: observación ("hay tres funciones duplicadas para formatear teléfonos"), pedido ("unifícalas en una sola"), restricciones ("no borres funciones exportadas; no cambies el texto de los mensajes") y criterio de aceptación ("los tests actuales pasan sin modificarlos"). El nuevo PR tiene 40 líneas y se revisa en diez minutos.

### Una demo a operaciones con expectativas desalineadas

**Situación:** el equipo presenta el agente de operaciones que investiga alertas. Operaciones entiende que va a "resolver" las alertas solo y pide sacar a una persona de la guardia nocturna.

**Qué se hace:** el equipo aclara por escrito, con números, qué hace el agente: en 30 alertas de prueba, propuso la causa correcta en 21 y en 6 no encontró nada; usa herramientas de solo lectura y no ejecuta acciones. Propone un piloto de un mes en el que el agente prepara el informe y la persona de guardia decide. Se acuerda revisar los números al final del piloto antes de cambiar la guardia.

## Errores comunes

- **Confundir asertividad con franqueza brusca.** Decir "lo digo como es" no exime del respeto; los hechos se pueden decir sin atacar.
- **Usar mensajes en primera persona como disfraz.** "Siento que eres irresponsable" sigue siendo un juicio; se describe el comportamiento y su efecto.
- **Mensajes sin pedido.** Un mensaje que solo describe el problema deja al otro sin saber qué se espera; se cierra con una acción y un plazo.
- **Decir que sí para evitar el conflicto.** El conflicto aparece igual, más tarde y más caro; conviene decir el costo en el momento.
- **Seguir discutiendo después de decidir.** El desacuerdo se registra antes; después de la decisión, se ejecuta y se revisa con datos.
- **Prompts sin restricciones ni criterios de aceptación.** El agente completa con suposiciones; se escribe qué no tocar y cómo se verifica.

## Para discutir en equipo

- ¿En qué situaciones nos cuesta más decir que no: con producto, con otros equipos, con clientes grandes? ¿Qué nos ayudaría?
- ¿Qué mensajes recientes de Slack generaron más idas y vueltas de las necesarias? ¿Qué les faltaba?
- ¿Usamos "disagree and commit" de verdad, o los desacuerdos reaparecen después de decidir?
- ¿Nuestros pedidos a agentes de código incluyen restricciones y criterios de aceptación? ¿Conviene una plantilla?
- ¿Cómo comunicamos hoy la incertidumbre de las funcionalidades con LLM a quienes no son del equipo?
