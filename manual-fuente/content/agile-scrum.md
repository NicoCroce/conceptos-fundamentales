---
slug: agile-scrum
titulo: Agile, Scrum y Kanban
resumen: Qué propone el enfoque ágil y cómo lo aplican Scrum y Kanban, incluido su ajuste cuando parte del trabajo lo hacen agentes de código.
lectura: 14
---

## La idea central

Construir software es trabajar con información incompleta: no sabemos del todo qué necesita el usuario, ni cuánto va a costar, ni cómo se va a comportar el sistema en producción. El enfoque **ágil** (*agile*) acepta esa incertidumbre en lugar de negarla. En vez de planificar todo al principio y entregar al final, se construye en pasos cortos, se muestra algo que funciona, se escucha la reacción y se ajusta el rumbo. La analogía es manejar de noche con luces bajas: no se ve todo el camino, pero se ve lo suficiente para avanzar unos metros y corregir.

**Scrum** y **Kanban** son las dos formas más usadas de llevar esa idea a la práctica. Scrum organiza el trabajo en iteraciones de duración fija con roles y reuniones definidas. Kanban organiza el flujo continuo de trabajo y limita cuánto se hace a la vez. Con agentes de código, ambos siguen valiendo, pero cambia dónde está el cuello de botella: escribir código se abarata y lo caro pasa a ser especificar bien y revisar.

## Conceptos

### El manifiesto ágil en palabras simples

En 2001 un grupo de desarrolladores escribió el **manifiesto ágil**: cuatro valores y doce principios. Los valores comparan dos cosas y dicen que, sin despreciar la segunda, se valora más la primera:

1. **Personas e interacciones** por sobre procesos y herramientas.
2. **Software que funciona** por sobre documentación exhaustiva.
3. **Colaboración con el cliente** por sobre negociación de contratos.
4. **Responder al cambio** por sobre seguir un plan.

Los principios se resumen en cuatro ideas: entregar seguido, medir el avance con software que funciona, usar el feedback para cambiar de opinión y revisar con regularidad cómo trabaja el equipo.

Lo que agile **no** es: no es "sin planificación" (se planifica todo el tiempo, en tramos cortos), no es "sin documentación" (se documenta lo que alguien va a usar), no es una certificación ni un conjunto de reuniones obligatorias, y no es una forma de prometer más en menos tiempo.

**Ejemplo:** Rumbo quiere que el asistente de soporte atienda consultas de transportistas. En lugar de diseñar durante dos meses las 40 consultas posibles, el equipo lanza en dos semanas una versión que responde solo "¿dónde retiro este pedido?" a 50 transportistas. Con lo aprendido (el 60% de las consultas reales eran otras) ajusta el siguiente paso.

**Por qué importa:** el valor de agile está en acortar el ciclo entre una decisión y la evidencia de si fue buena. Si ese ciclo sigue siendo de meses, el nombre no cambia nada.

### Scrum: roles, eventos y artefactos

Scrum define tres responsabilidades:

- **Product owner:** decide qué se construye y en qué orden. Mantiene el *product backlog* (la lista ordenada de todo lo pendiente) y es la única voz que lo prioriza.
- **Scrum master:** cuida que el proceso funcione. Facilita las reuniones, quita impedimentos y ayuda al equipo a mejorar. No es jefe ni asigna tareas.
- **Developers:** quienes construyen el incremento (ingeniería, datos, diseño, QA). Deciden cómo hacer el trabajo y cuánto entra en un sprint.

El trabajo ocurre en **sprints** de duración fija, típicamente una o dos semanas. Para un sprint de dos semanas, los eventos y sus duraciones máximas habituales son:

| Evento | Cuándo | Duración típica (sprint de 2 semanas) | Pregunta que responde |
|---|---|---|---|
| Sprint planning | Primer día | Hasta 4 horas | ¿Qué objetivo tiene el sprint y qué entra? |
| Daily | Cada día | 15 minutos | ¿Vamos bien hacia el objetivo? ¿Qué nos bloquea? |
| Sprint review | Último día | Hasta 2 horas | ¿Qué se construyó y qué aprendimos con quienes lo usan? |
| Retrospectiva | Último día, después de la review | Hasta 1,5 horas | ¿Cómo trabajamos y qué cambiamos? |

Además hay una actividad continua, el **refinamiento** del backlog: aclarar, partir y estimar los ítems que vienen. No es un evento formal; muchos equipos le dedican una o dos horas por semana.

Los tres **artefactos** son el *product backlog*, el *sprint backlog* (lo elegido para este sprint más el plan para hacerlo) y el **incremento**: el software terminado y usable al final del sprint.

**Ejemplo:** el equipo del modelo de ETA trabaja en sprints de dos semanas. En la planning fija el objetivo "reducir el error de ETA en zona norte en horario pico" y elige cuatro ítems. En la review muestra a operaciones el error antes y después en un tablero, no una lista de tareas cerradas.

**Por qué importa:** cada evento existe para inspeccionar algo y adaptar. Si una reunión no termina en ninguna decisión, se volvió ceremonia.

### Definición de listo y definición de terminado

La **definición de terminado** (*definition of done*) es la lista de condiciones que todo ítem cumple para considerarse hecho: tests pasando, revisión de código, desplegado en staging, métricas visibles, documentación actualizada. Es parte de Scrum y es compartida por todo el equipo.

La **definición de listo** (*definition of ready*) es una práctica común, aunque no forma parte de la guía oficial de Scrum: las condiciones que un ítem cumple antes de entrar a un sprint. Por ejemplo, que tenga criterios de aceptación, que no dependa de otro equipo sin acuerdo y que sea lo bastante chico.

| | Definición de listo | Definición de terminado |
|---|---|---|
| Cuándo se aplica | Antes de empezar | Antes de dar por cerrado |
| Protege contra | Empezar trabajo ambiguo | Cerrar trabajo a medias |
| Ejemplo | "Tiene criterios Dado/Cuando/Entonces" | "Desplegado en staging con alerta configurada" |

**Ejemplo:** en Rumbo, la definición de terminado del equipo del asistente incluye "los casos del golden set no empeoran más de 2 puntos" y "ningún dato de destinatario aparece en logs". Un ítem que pasa los tests unitarios pero baja la calidad de respuestas no está terminado.

**Por qué importa:** sin definición de terminado, "hecho" significa cosas distintas para cada persona, y la deuda aparece sprints después como bugs.

### Historias de usuario y criterios de aceptación

Una **historia de usuario** describe una necesidad desde el punto de vista de quien la tiene: "Como *rol*, quiero *algo*, para *beneficio*". No es una especificación; es un recordatorio de una conversación pendiente. Lo que la vuelve verificable son sus **criterios de aceptación**.

**Ejemplo:**

```text
Como transportista de Rumbo,
quiero preguntarle al asistente dónde retirar un pedido asignado,
para no tener que llamar a soporte.

Criterios de aceptación:
- Dado un pedido asignado a mí, cuando pregunto por su retiro,
  el asistente responde con la dirección y el horario del comercio.
- Dado un pedido asignado a otro transportista, el asistente no revela datos.
- Si el asistente no puede responder, ofrece derivar a una persona.
```

Una guía clásica para historias es **INVEST**: independiente, negociable, valiosa, estimable, pequeña (*small*) y testeable. La que más se incumple es "pequeña": una historia que no entra holgada en un sprint conviene partirla por comportamiento (primero solo retiro, después demoras), no por capa técnica (primero backend, después frontend).

**Por qué importa:** el criterio "no revela datos de otro transportista" es un requisito de seguridad. Si no está escrito, nadie lo prueba.

### Kanban: flujo, límites de WIP y pull

**Kanban** parte del trabajo tal como ocurre hoy y lo hace visible en un tablero con columnas (por ejemplo: Pendiente, En curso, En revisión, Desplegado). Sus tres prácticas centrales:

1. **Visualizar el flujo:** cada ítem es una ficha en el tablero y se ve dónde está.
2. **Limitar el trabajo en curso** (WIP, *work in progress*): cada columna tiene un máximo. Si "En revisión" tiene límite 3 y ya hay 3 ítems, nadie empieza algo nuevo; se ayuda a revisar.
3. **Pull en lugar de push:** se toma trabajo nuevo cuando hay capacidad, no cuando alguien lo asigna.

**Ejemplo:** el tablero del equipo de plataforma de Rumbo tiene las columnas Pendiente, En curso (límite 4), En revisión (límite 3) y Desplegado. Cuando una ingeniera termina un cambio de Terraform y ve "En revisión" llena, en vez de tomar un ítem nuevo revisa el PR más viejo de la columna.

Dos tiempos se confunden seguido. El **lead time** va desde que alguien pide algo hasta que lo recibe. El **cycle time** va desde que el equipo empieza a trabajarlo hasta que lo entrega. Si un pedido espera 6 días en el backlog y se trabaja 3, el lead time es 9 y el cycle time es 3. Las definiciones varían entre equipos; lo importante es acordarlas y medir siempre igual.

**Por qué importa:** limitar el WIP parece frenar, pero es lo que acelera. Con muchas cosas abiertas, todas avanzan despacio y ninguna llega.

### La ley de Little con números

La **ley de Little** relaciona tres magnitudes de cualquier sistema estable:

```text
tiempo promedio en el sistema = trabajo en curso promedio / throughput
```

**Ejemplo:** el equipo de plataforma de Rumbo tiene en promedio 24 ítems en curso y termina 8 por semana. El tiempo promedio de cada ítem es 24 / 8 = 3 semanas. Si baja el WIP a 12 sin cambiar cuánto termina por semana, el tiempo cae a 12 / 8 = 1,5 semanas. Nadie trabajó más rápido: solo se dejó de empezar cosas que iban a esperar.

Bajar el WIP además suele subir el throughput, por menos cambio de contexto. La ley vale para promedios en un sistema más o menos estable; no predice un ítem individual.

**Por qué importa:** es el argumento más sólido contra "arranquemos esto también, total ya lo vamos a terminar".

### Scrum frente a Kanban

| Aspecto | Scrum | Kanban |
|---|---|---|
| Ritmo | Iteraciones fijas (sprints) | Flujo continuo |
| Compromiso | Objetivo del sprint | Límites de WIP por columna |
| Roles | Product owner, scrum master, developers | No prescribe roles |
| Cambios a mitad de camino | Se evitan dentro del sprint | Se admiten si hay capacidad |
| Métrica natural | Lo completado por sprint | Cycle time y throughput |
| Encaja mejor en | Equipos de producto con roadmap | Plataforma, soporte, operaciones, trabajo con interrupciones |

**Ejemplo:** en Rumbo, el equipo del asistente de soporte, que construye funcionalidades nuevas con un objetivo cada dos semanas, usa Scrum. El equipo de plataforma, que recibe pedidos de otros equipos, incidentes y cambios de infraestructura impredecibles, usa Kanban con un carril de urgencias. Muchos equipos mezclan: sprints con tablero y límites de WIP.

**Por qué importa:** el método debe ajustarse a cómo llega el trabajo. Forzar sprints sobre un flujo de interrupciones produce objetivos que nunca se cumplen.

### Antipatrones frecuentes

- **Zombie scrum:** todas las reuniones se hacen, pero ningún usuario mira el incremento, la review es una demo sin feedback y la retrospectiva repite las mismas quejas. Hay forma sin propósito.
- **Daily como reporte de estado:** cada persona le cuenta al líder qué hizo ayer. La daily es del equipo y su pregunta es si se llega al objetivo; los detalles van después, entre quienes los necesitan.
- **Velocity como meta:** la *velocity* (puntos completados por sprint) sirve para que el equipo planifique, no para comparar equipos ni exigir crecimiento. Si se vuelve meta, los puntos se inflan y el número deja de decir algo (ver [Métricas de entrega](#t/metricas-entrega)).
- **Cambios constantes dentro del sprint:** si cada semana entra algo urgente, quizás el equipo necesita Kanban o un carril explícito para interrupciones.

**Ejemplo:** en un equipo de Rumbo, la daily duraba 40 minutos porque cada persona detallaba sus tickets al líder técnico. Al recorrer el tablero de derecha a izquierda y hablar solo de lo bloqueado, bajó a 12 minutos.

**Por qué importa:** los antipatrones conservan la apariencia del método y vacían su contenido; por eso cuestan detectarse desde adentro.

### Sprints con agentes de código

Cuando parte del trabajo lo hacen agentes de código, la mecánica de Scrum o Kanban no cambia, pero sí varias proporciones:

1. **Historias más chicas y con especificación clara.** Un agente rinde con tareas acotadas y verificables. La historia del transportista se parte en tareas con criterios comprobables, al estilo de [SDD](#t/sdd), y el nivel de proceso se ajusta al riesgo, como propone [ODD](#t/odd).
2. **La revisión pasa a ser el cuello de botella.** Si un ingeniero con agentes abre 5 PRs por día en vez de 1, la columna "En revisión" se llena. La respuesta Kanban es directa: un **límite de WIP en revisión** (por ejemplo, 4 PRs) y la regla de que, si se alcanza, se revisa antes de abrir más.
3. **Refinamiento asistido.** Un agente puede proponer el desglose de una historia, detectar criterios faltantes ("¿qué pasa si el pedido ya fue retirado?") o agrupar tickets duplicados. El product owner sigue decidiendo el orden; el agente acelera la preparación, no la responsabilidad.
4. **Spikes para funcionalidades con LLM.** Antes de comprometer una historia que depende de que un modelo responda bien, conviene un **spike**: una tarea de exploración con tiempo fijo (por ejemplo, 3 días) para probar si es factible y con qué calidad.
5. **Evaluación en la definición de terminado.** Para funcionalidades con LLM, "terminado" incluye correr la [evaluación](#t/evaluacion-llms) y no empeorar el golden set, además de los tests.

**Ejemplo:** el equipo del asistente medía 2 días de espera promedio en revisión antes de usar agentes. Después de adoptarlos, la espera subió a 4 días mientras el tiempo de escritura bajó a la mitad. El sprint siguiente fijaron un WIP de 4 en revisión y un bloque diario de revisión; la espera volvió a 1,5 días.

**Por qué importa:** si se acelera solo una etapa, el trabajo se acumula en la siguiente. Kanban ayuda a ver dónde.

## Casos prácticos

### Un sprint que siempre se desborda

**Situación:** el equipo del asistente de soporte cierra cada sprint con la mitad de los ítems "casi listos". La review muestra trabajo a medias y la planning siguiente arrastra todo.

**Qué se hace:** se revisan dos cosas. Primero, la definición de listo: varios ítems entraban sin criterios de aceptación y se aclaraban a mitad de sprint. Segundo, el WIP: cinco personas tenían nueve ítems abiertos. Se exige que todo ítem tenga criterios antes de la planning y se limita a un ítem en curso por persona, más uno en revisión. En dos sprints, lo planificado y lo terminado empiezan a coincidir.

### Plataforma ahogada en interrupciones

**Situación:** el equipo de plataforma usa sprints de dos semanas, pero un 40% de su tiempo se va en pedidos de otros equipos e incidentes que no estaban planificados. El objetivo del sprint nunca se cumple.

**Qué se hace:** pasa a Kanban con tres carriles: urgencias (sin límite pero visibles), pedidos de otros equipos (WIP 3) y mejoras propias (WIP 2). Mantiene una retrospectiva cada dos semanas y mide cycle time por carril. A las seis semanas puede decir con datos cuánto tarda un pedido y cuánta capacidad queda para mejoras.

### Agentes que llenan la cola de revisión

**Situación:** después de habilitar agentes de código, el servicio de asignación tiene 14 PRs abiertos, algunos de 600 líneas. Dos se fusionaron con revisiones apuradas y uno rompió el presupuesto de latencia de 50 ms.

**Qué se hace:** se fija un WIP de 4 PRs en revisión para el equipo, un tamaño máximo orientativo de 300 líneas y la regla de que todo PR generado con agentes incluya la especificación o la tarea que implementa y la evidencia de tests. Se agrega una prueba de latencia en CI. El throughput de PRs baja un poco, pero los fusionados ya no se revierten.

### Una historia con LLM comprometida demasiado pronto

**Situación:** producto pidió que el asistente clasifique automáticamente los tickets de soporte en 12 categorías. El equipo lo comprometió como historia de un sprint. A mitad de sprint, la precisión en datos reales era del 60% y nadie sabía si se podía llegar al 90% pedido.

**Qué se hace:** se reconvierte en un spike de 3 días con una pregunta concreta: "¿con qué precisión clasificamos 300 tickets etiquetados, con qué modelo y a qué costo?". El resultado muestra que 8 categorías superan el 90% y 4 no. La historia siguiente cubre solo esas 8 y deriva el resto a una persona; la definición de terminado incluye la evaluación sobre los 300 tickets.

## Errores comunes

- **Adoptar las reuniones sin el propósito.** Cada evento debe terminar en una decisión; si no, se acorta o se cambia.
- **Usar la velocity para comparar equipos o personas.** Es una herramienta interna de planificación; usada como meta, se infla y deja de servir.
- **Historias partidas por capa técnica.** "Backend del retiro" no entrega nada usable; se parte por comportamiento visible para el usuario.
- **No limitar el WIP.** Empezar mucho alarga todo; la ley de Little lo muestra con números.
- **Medir a los agentes por cuánto código producen.** Si la revisión no acompaña, solo se mueve la cola; se mira el tiempo de punta a punta.
- **Dejar la evaluación de LLMs fuera de la definición de terminado.** Una funcionalidad con modelo que pasa los tests puede igual responder peor.

## Para discutir en equipo

- ¿Nuestro equipo encaja mejor en Scrum, en Kanban o en una mezcla? ¿Qué porcentaje de nuestro trabajo es no planificado?
- ¿Qué incluye hoy nuestra definición de terminado y qué le falta para funcionalidades con LLM?
- ¿Dónde se acumula el trabajo en nuestro tablero? ¿Tiene límite de WIP esa columna?
- ¿Qué parte del refinamiento del backlog podría preparar un agente y qué decisiones no deberían salir de las personas?
- ¿Cuándo fue la última vez que una retrospectiva cambió algo concreto en cómo trabajamos?
