---
slug: estimacion
titulo: Estimación de esfuerzo
resumen: Técnicas para estimar trabajo de software con rangos en lugar de fechas únicas, incluidas funcionalidades con LLMs y trabajo hecho con agentes de código.
lectura: 14
---

## La idea central

Una estimación es una herramienta para **decidir**, no una promesa. Sirve para responder preguntas como "¿conviene hacer esto antes que aquello?", "¿llegamos a la fecha del cliente con este alcance?" o "¿vale la pena gastar seis semanas en esta funcionalidad?". Cuando se usa como compromiso firme sobre algo que todavía nadie entiende del todo, se convierte en una fuente de presión, de colchones escondidos y de desconfianza entre ingeniería y producto.

Como el pronóstico del clima, una buena estimación es un **rango con un nivel de confianza** ("entre 3 y 5 semanas, con 85 % de confianza") que se actualiza al aprender. Con agentes de código y funcionalidades basadas en LLMs aparecen dos giros nuevos: la implementación se acorta mucho, pero la verificación no; y la calidad que puede alcanzar un modelo no se conoce de antemano, así que parte del trabajo es descubrir si el objetivo es alcanzable.

## Conceptos

### Estimación, compromiso y objetivo

Son tres cosas distintas que se suelen mezclar:

- **Estimación:** lo que creemos que va a llevar, con su incertidumbre. "Entre 4 y 7 semanas."
- **Objetivo (target):** lo que el negocio quiere. "Lo necesitamos para el 1 de marzo."
- **Compromiso:** lo que el equipo acepta entregar, sabiendo la estimación y el objetivo. "Para el 1 de marzo entregamos el alcance A; el B queda para después."

Lo sano es comparar estimación con objetivo y negociar el compromiso, normalmente moviendo el alcance; lo enfermo es llamar estimación al objetivo y exigirlo.

**Ejemplo:** producto de Rumbo quiere el asistente para transportistas antes de la temporada alta, en 6 semanas. La estimación del equipo es de 6 a 10 semanas para el alcance completo. En lugar de "estimar 6", se acuerda un compromiso: en 6 semanas salen las consultas de estado de pedido y la reprogramación; las consultas sobre documentación de vehículos quedan para la versión siguiente.

**Por qué importa:** si se confunden, el equipo aprende a inflar números para protegerse.

### Estimación relativa: story points, planning poker y talles

Las personas somos malas estimando duraciones absolutas, pero bastante buenas comparando: "esto es el doble de grande que aquello". La **estimación relativa** aprovecha eso.

- **Story points:** una unidad sin dimensión que combina tamaño, complejidad e incertidumbre. Se usa una escala tipo Fibonacci (1, 2, 3, 5, 8, 13, 21) porque los huecos crecen con el tamaño: entre un 13 y un 21 no tiene sentido discutir si es 15 o 16.
- **Planning poker:** cada integrante elige su número en privado y todos lo muestran a la vez. Así se evita que la primera opinión arrastre a las demás. Si hay mucha dispersión (un 3 y un 13), quienes están en los extremos explican su razonamiento y se vuelve a votar.
- **Talles de remera (S, M, L, XL):** útiles al inicio, para dimensionar iniciativas grandes en un roadmap sin entrar en detalle.

**Ejemplo:** el equipo toma como referencia "agregar un campo al evento de pedido entregado" = 2 puntos. Al estimar "nueva herramienta del agente de operaciones para consultar demoras por zona", una persona vota 5 y otra 13. La de 13 explica que la consulta a Aurora necesita un índice nuevo y una revisión de permisos de solo lectura. La segunda ronda converge en 8.

**Por qué importa:** el valor del planning poker está más en la discusión que en el número: las diferencias revelan supuestos ocultos antes de empezar.

### Estimación absoluta: días ideales

Un **día ideal** es un día de trabajo concentrado sin reuniones, interrupciones ni on-call. Hay que convertirlo: un equipo suele lograr entre 0,5 y 0,7 días ideales por día calendario, según su carga de soporte y reuniones.

**Ejemplo:** una tarea de 6 días ideales, con un factor de 0,6, ocupa unos 10 días hábiles.

**Por qué importa:** dar "6 días" sin aclarar que son ideales es la forma más rápida de generar una fecha incumplida.

### Estimación de tres puntos y PERT

En lugar de un número, se piden tres por tarea: **optimista (O)**, **más probable (M)** y **pesimista (P)**. La técnica PERT combina esos valores en un esperado y una desviación estándar:

- Esperado: E = (O + 4M + P) / 6
- Desviación estándar: σ = (P − O) / 6

Para varias tareas, los esperados se suman, y las **varianzas** (σ²) también; la desviación total es la raíz de la suma de varianzas.

**Ejemplo:** funcionalidad "reprogramar una entrega desde el asistente", en días:

| Tarea | O | M | P | E | σ |
|---|---|---|---|---|---|
| Endpoint de reprogramación | 2 | 3 | 6 | 3,33 | 0,67 |
| Herramienta del asistente | 1 | 2 | 5 | 2,33 | 0,67 |
| Evaluación con golden set | 2 | 4 | 10 | 4,67 | 1,33 |
| Revisión de seguridad y deploy | 1 | 2 | 3 | 2,00 | 0,33 |
| **Total** | | **11** | | **12,33** | **1,67** |

La varianza total es 0,44 + 0,44 + 1,78 + 0,11 = 2,78, y su raíz da σ ≈ 1,67. Con una aproximación normal, hay alrededor de 84 % de probabilidad de terminar en E + 1σ ≈ 14 días y alrededor de 98 % en E + 2σ ≈ 15,7 días. Notar que la suma de los "más probables" da 11, menos que el esperado: las colas pesimistas empujan hacia arriba.

**Por qué importa:** el número que se comunica pasa a ser "entre 12 y 16 días", no "11 días". Una salvedad: PERT supone tareas independientes. Si la evaluación sale mal, probablemente también se alargue el ajuste de la herramienta, así que el rango real es algo más ancho.

### El cono de incertidumbre

La incertidumbre se reduce a medida que se toman decisiones. Los multiplicadores clásicos del **cono de incertidumbre** son orientativos:

| Momento | Rango sobre la estimación puntual |
|---|---|
| Idea inicial | 0,25x a 4x |
| Alcance de producto aprobado | 0,5x a 2x |
| Requisitos detallados | 0,67x a 1,5x |
| Diseño técnico detallado | 0,8x a 1,25x |

**Ejemplo:** si en la etapa de idea alguien dice "10 semanas", el rango honesto va de 2,5 a 40 semanas. Con los requisitos cerrados, la misma estimación se lee como 6,7 a 15 semanas.

Aplicando el multiplicador superior de cada momento a esa misma estimación de 10 semanas, se ve cómo se cierra la boca del cono:

```barras
titulo: Peor caso de 10 semanas estimadas
unidad: semanas
Idea inicial (4x) | 40
Alcance aprobado (2x) | 20
Requisitos detallados (1,5x) | 15
Diseño técnico detallado (1,25x) | 12,5
```

**Por qué importa:** el cono no se achica solo con el paso del tiempo, sino con decisiones. Un proyecto que lleva tres meses sin cerrar el alcance sigue en la boca ancha del cono.

### Velocidad y pronóstico con rangos

La **velocidad** es cuántos puntos completa el equipo por iteración. Sirve para pronosticar con rangos, no para medir productividad.

**Ejemplo:** en los últimos seis sprints de dos semanas el equipo completó 21, 18, 25, 20, 16 y 23 puntos. El promedio es 20,5; el peor, 16; el mejor, 25. Con 120 puntos pendientes: 120 / 25 = 4,8 y 120 / 16 = 7,5. El pronóstico honesto es "entre 5 y 8 sprints", es decir, de 10 a 16 semanas, y no "6 sprints".

**Por qué importa:** usar el promedio como certeza da una fecha que se incumple la mitad de las veces.

### Pronóstico Monte Carlo sobre el throughput

Una alternativa que evita estimar cada tarea es contar el **throughput**: cuántos ítems se terminan por semana. Con esos datos históricos se hace una **simulación Monte Carlo**:

1. Se toma el historial, por ejemplo las últimas 10 semanas: 3, 5, 2, 4, 6, 3, 4, 5, 2 y 4 ítems (promedio 3,8).
2. Se simula el futuro sorteando semanas al azar de ese historial y sumando ítems hasta completar los pendientes.
3. Se repite 10.000 veces y se mira la distribución de cuántas semanas hicieron falta.

**Ejemplo:** con 40 ítems pendientes, una simulación así da aproximadamente: 50 % de las corridas terminan en 11 semanas o menos, 85 % en 12 y 95 % en 13. Se comunica "con 85 % de confianza, en 12 semanas".

**Por qué importa:** responde "¿cuándo?" con probabilidades y casi sin esfuerzo de estimación. Requiere que los ítems sean de tamaño parecido y que el backlog no crezca mucho; si cada ítem se divide en tres a mitad de camino, el pronóstico se rompe.

### Dividir el trabajo

La forma más eficaz de mejorar una estimación es **partir el trabajo** en piezas chicas que entreguen algo verificable. Una tarea de 13 puntos esconde incertidumbre; tres de 3 o 5 la exponen. Se puede dividir por flujo de usuario, por regla de negocio o por variante de datos.

**Ejemplo:** "asistente para transportistas" se divide en: consultar estado de un pedido, reprogramar una entrega, avisar de una demora, escalar a una persona. Cada parte se puede evaluar y lanzar por separado.

**Por qué importa:** piezas chicas reducen la varianza y permiten cortar alcance sin tirar trabajo.

### #NoEstimates

El movimiento **#NoEstimates** propone dejar de estimar tareas individuales y, en su lugar, dividir todo en ítems de tamaño similar y pronosticar contando throughput, como en Monte Carlo. Funciona bien en equipos con flujo estable y trabajo parecido; no elimina la necesidad de dimensionar iniciativas grandes ni de responder "¿cuánto costaría esto?" antes de decidir hacerlo. 

**Ejemplo:** el equipo de plataforma de Rumbo atiende pedidos internos chicos (nuevos dashboards, permisos, alertas). En lugar de estimar cada uno, acuerda que ninguno supere los 3 días; si parece más grande, se divide. Con eso, para saber cuándo sale algo alcanza con mirar la cola y el throughput: unos 9 pedidos por semana.

**Por qué importa:** si el equipo pasa más tiempo discutiendo puntos que el que esa precisión le ahorra, estimar menos y dividir más es la mejor inversión.

### Sesgos y colchones

Los errores de estimación casi nunca son aleatorios: tienen sesgos conocidos.

- **Anclaje:** el primer número que se escucha arrastra a los demás. "Esto es cosa de una semana, ¿no?" deja la estimación pegada a una semana.
- **Falacia de planificación:** se estima pensando en el caso en que todo sale bien, aunque la experiencia diga lo contrario. El antídoto es mirar proyectos parecidos: "las últimas tres integraciones con clientes on-prem llevaron 8, 11 y 9 semanas".
- **Síndrome del estudiante:** si hay holgura, el trabajo empieza tarde y la holgura se consume antes de que haga falta.
- **Colchones escondidos (padding):** cada persona agrega un 30 % "por las dudas" a su tarea; cada líder agrega otro 20 %. El resultado es una estimación inflada que igual se incumple, porque el colchón se gasta por síndrome del estudiante.

**Ejemplo:** en lugar de que cada tarea tenga su colchón oculto, el equipo estima con tres puntos y agrega un colchón explícito al final del proyecto, visible para todos (ver [Planificación y diagramas de Gantt](#t/planificacion-gantt)).

**Por qué importa:** un colchón visible se puede discutir y medir; uno escondido solo genera desconfianza.

### Estimar funcionalidades con LLMs

En software tradicional la pregunta es "¿cuánto tardamos en construirlo?". En una funcionalidad con LLM aparece otra: **"¿se puede alcanzar la calidad necesaria?"**. Nadie sabe de antemano si el asistente va a responder bien el 80 % o el 95 % de las consultas, y el camino del 85 % al 95 % puede costar más que todo lo anterior.

Por eso se estima distinto:

1. **Spike con tiempo fijo:** "dos semanas para llegar al 85 % en el golden set"; al terminar se decide con datos si seguir, achicar o abandonar.
2. **Hitos de evaluación:** el plan no tiene solo tareas, tiene puntos de decisión basados en métricas (ver [Evaluación de LLMs](#t/evaluacion-llms)).
3. **Construir la evaluación primero:** sin golden set no hay forma de saber cuánto falta.

**Ejemplo:** para clasificar tickets de soporte de Rumbo, el equipo no estima "4 semanas para el clasificador". Estima "1 semana para armar 300 casos etiquetados y el harness de evaluación; 2 semanas de spike con meta de 90 % de precisión; luego, decisión". En la semana 3 el clasificador llega a 87 %; se decide lanzarlo solo para las tres categorías donde supera el 93 %.

**Por qué importa:** estimar una funcionalidad con LLM como si fuera un CRUD lleva a proyectos que llegan a la fecha con una calidad que no se puede lanzar.

### Estimar trabajo hecho con agentes de código

Con un agente de código (ver [SDD](#t/sdd)), escribir la implementación es mucho más rápido. Pero el esfuerzo total no baja en la misma proporción, porque **la revisión, la integración y la verificación no se aceleran igual**, y a veces crecen: hay más código para leer y menos contexto sobre por qué se escribió así.

**Ejemplo:** una funcionalidad que antes llevaba 5 días se repartía en 3 de implementación, 1 de revisión y 1 de integración y pruebas. Con un agente, la implementación baja a 1 día, pero la revisión sube a 1,5 (el diff es más grande y hay que leerlo con más cuidado) y la integración sigue en 1. Total: 3,5 días, no 1,7. La reducción real es del 30 %, no del 66 %.

La regla práctica es **estimar la verificación**: ¿cuánto lleva convencerse de que esto funciona? Eso incluye leer el diff, correr pruebas, probar casos borde y revisar áreas sensibles.

**Por qué importa:** si el equipo estima solo la implementación, el cuello de botella se traslada a la revisión, los PRs se acumulan y la velocidad aparente no se convierte en entregas.

### El costo en tokens como parte de la estimación

Una funcionalidad con LLM tiene dos costos que conviene estimar junto con el esfuerzo: el de **construirla** (sesiones de agentes de código, corridas de evaluación) y el de **operarla** (tokens por consulta en producción). El segundo suele ser el que importa.

**Ejemplo:** el asistente para transportistas recibe unas 50.000 consultas diarias, con 3.000 tokens de entrada promedio entre system prompt, contexto recuperado e historial. Son 150 millones de tokens por día. Con un precio hipotético de USD 3 por millón de tokens de entrada, son USD 450 diarios, unos USD 13.500 mensuales, sin contar salida.

**Por qué importa:** una estimación que solo dice "6 semanas" esconde una decisión de costo recurrente que puede pesar más que el desarrollo (ver [Costos cloud (FinOps)](#t/finops)).

## Casos prácticos

### El cliente on-prem que pidió una fecha

**Situación:** un cliente grande pide el asistente de soporte instalado on-prem y quiere una fecha de go-live en la primera reunión, sin saber todavía qué GPUs tiene ni qué datos se pueden indexar.

**Qué se hace:** se explica el cono de incertidumbre y se ofrece un rango amplio (8 a 20 semanas) junto con un compromiso concreto: en 2 semanas, tras relevar infraestructura y datos, se entrega una estimación con rango de ±25 %. Con el relevamiento hecho, el rango queda en 10 a 13 semanas y se acuerda una fecha con colchón explícito.

### Un clasificador que no llegaba a la meta

**Situación:** el plan decía "clasificador de tickets: 3 semanas". En la semana 3 la precisión está en 82 % y la meta era 92 %. El equipo pide "una semana más" por tercera vez.

**Qué se hace:** el problema no era de esfuerzo sino de techo de calidad. Se convierte en un spike con tiempo fijo de una semana con una decisión explícita al final, se analizan los errores por categoría y se lanza solo en las categorías que superan la meta. El resto se deriva a personas.

### Velocidad que subió con agentes, entregas que no

**Situación:** desde que el equipo usa agentes de código, los puntos "terminados" subieron 40 %, pero las funcionalidades en producción no aumentaron. Hay 14 PRs abiertos esperando revisión.

**Qué se hace:** se cambia la definición de terminado a "en producción y verificado", se limita el trabajo en curso a tres PRs por persona y, al estimar, se separa explícitamente el esfuerzo de revisión y verificación. La velocidad baja en el papel y las entregas suben.

### Pronóstico para la temporada alta

**Situación:** producto pregunta si el backlog del asistente (40 ítems) está listo antes de la temporada alta, dentro de 12 semanas.

**Qué se hace:** en lugar de estimar cada ítem, se corre un Monte Carlo sobre el throughput de las últimas 10 semanas: 85 % de probabilidad de terminar en 12 semanas, 50 % en 11. Se comunica que es probable pero sin margen, y se acuerda qué 8 ítems se sacan si a mitad de camino el pronóstico empeora.

## Errores comunes

- **Dar un número único.** Una estimación sin rango se lee como compromiso; se comunica siempre un rango y su nivel de confianza.
- **Convertir story points en horas o comparar velocidades entre equipos.** Los puntos son relativos al equipo; usarlos para medir productividad los infla de inmediato.
- **Estimar funcionalidades con LLM sin evaluación previa.** Sin golden set no se sabe cuánto falta; primero se construye la forma de medir, después se estima.
- **Estimar solo la implementación cuando trabaja un agente.** La verificación y la revisión son ahora la mayor parte del esfuerzo y deben aparecer en la estimación.
- **Colchones escondidos en cada tarea.** Se reemplazan por un colchón explícito y compartido al final del proyecto.
- **No reestimar.** Una estimación es válida para la información de ese momento; cuando aparece información nueva, se actualiza y se comunica.

## Para discutir en equipo

- ¿Distinguimos hoy, en las conversaciones con producto, entre estimación, objetivo y compromiso?
- ¿Cuánto de nuestro esfuerzo con agentes de código se va en revisión y verificación? ¿Lo medimos?
- ¿Qué funcionalidades con LLM deberían haber empezado como spike con tiempo fijo y hito de evaluación?
- ¿Tenemos datos de throughput suficientes para pronosticar con Monte Carlo en lugar de estimar ítem por ítem?
- ¿Incluimos el costo mensual de tokens en las propuestas de nuevas funcionalidades con LLM?
