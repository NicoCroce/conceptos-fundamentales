---
slug: planificacion-gantt
titulo: Planificación y diagramas de Gantt
resumen: Cómo descomponer un proyecto, ordenar dependencias, encontrar el camino crítico y mantener vivo un plan con fechas duras, incluidos proyectos con agentes.
lectura: 14
---

## La idea central

Planificar no es adivinar el futuro, sino hacer visibles tres cosas antes de empezar: **qué trabajo hay**, **en qué orden tiene que hacerse** y **qué parte del trabajo decide la fecha final**. La mayoría de las tareas de un proyecto pueden atrasarse un poco sin consecuencias; unas pocas no. Saber cuáles son esas pocas es lo que permite poner la atención donde importa.

El **diagrama de Gantt** es la representación clásica de un plan: cada tarea es una barra en una línea de tiempo, con su inicio, su duración y sus dependencias. Tiene mala fama en equipos ágiles porque se lo asocia con planes rígidos de dos años. Pero cuando hay una fecha dura y dependencias externas (el go-live acordado con un cliente, una instalación on-prem, una aprobación legal de acceso a datos), un Gantt bien usado es la herramienta más clara para ver si se llega y qué hacer si no.

## Conceptos

### Estructura de desglose del trabajo (WBS)

La **WBS** (*work breakdown structure*) descompone el proyecto en entregables y luego en paquetes de trabajo, hasta llegar a piezas que se pueden estimar y asignar. La regla del 100 %: la suma de las partes tiene que cubrir todo el trabajo, incluido el que nadie quiere hacer (documentación, revisión de seguridad, capacitación, migración de datos).

Un nivel de detalle razonable es que cada paquete dure entre unos días y dos semanas. Más grande, esconde incertidumbre; más chico, el plan se vuelve imposible de mantener.

**Ejemplo:** el proyecto "asistente de soporte on-prem para un cliente grande de Rumbo" se desglosa así:

```text
1. Alcance
   1.1 Casos de uso y criterios de aceptación
   1.2 Golden set de evaluación (200 consultas reales)
2. Infraestructura
   2.1 Cluster y GPUs en el datacenter del cliente
   2.2 Observabilidad y logs
3. Datos y conocimiento
   3.1 Aprobación de acceso a datos del cliente
   3.2 Indexado de manuales y tickets (RAG)
4. Integraciones
   4.1 Servidor MCP del sistema de tickets
5. Calidad y seguridad
   5.1 Evaluación offline
   5.2 Revisión de seguridad
6. Lanzamiento
   6.1 Piloto con 20 operadores de soporte
   6.2 Go-live
```

**Por qué importa:** las demoras más dolorosas vienen de tareas que no estaban en el plan. La WBS es el lugar para descubrirlas antes.

### Dependencias

Una dependencia dice qué tarea condiciona a otra. Hay cuatro tipos, aunque casi todo se resuelve con el primero:

- **Fin a inicio (FS):** B empieza cuando A termina. "La evaluación empieza cuando el indexado termina."
- **Inicio a inicio (SS):** B empieza cuando A empieza. "La documentación arranca junto con la implementación."
- **Fin a fin (FF):** B termina cuando A termina. "Las pruebas terminan cuando termina el desarrollo."
- **Inicio a fin (SF):** raro; B no puede terminar hasta que A empiece (por ejemplo, el sistema viejo sigue hasta que arranca el nuevo).

Además conviene distinguir dependencias **internas** (las controla el equipo) de **externas** (las controla otro: el cliente, el área legal, un proveedor de modelos). Las externas son las más riesgosas porque no se pueden acelerar con más esfuerzo.

**Ejemplo:** "indexar los tickets del cliente" depende de dos cosas: que la infraestructura esté instalada (interna) y que el área legal del cliente apruebe el acceso a los datos (externa).

**Por qué importa:** una dependencia externa sin fecha comprometida es un riesgo, no una tarea; hay que tratarla como tal (ver [Gestión y medición de riesgos](#t/riesgos)).

### Hitos

Un **hito** es un punto en el tiempo sin duración que marca algo verificable: "golden set aprobado", "acceso a datos concedido", "go-live". Sirven para comunicarse con quienes no siguen el detalle y para hacer chequeos de avance con criterio claro.

**Ejemplo:** el cliente no necesita ver las 15 tareas; necesita tres hitos: infraestructura lista (semana 5), piloto iniciado (semana 10) y go-live (semana 13).

**Por qué importa:** un hito bien definido es binario; "la evaluación va bien" no lo es, "evaluación con 90 % en el golden set" sí.

### Método del camino crítico (CPM)

El **camino crítico** es la secuencia más larga de tareas dependientes: su duración es la duración mínima del proyecto. Cualquier atraso en una tarea crítica atrasa el final. Se calcula en dos pasadas:

1. **Pasada hacia adelante:** para cada tarea, el inicio temprano (ES) es el máximo de los finales tempranos de sus predecesoras; el final temprano (EF) es ES + duración.
2. **Pasada hacia atrás:** desde el final, el final tardío (LF) es el mínimo de los inicios tardíos de sus sucesoras; el inicio tardío (LS) es LF − duración.
3. **Holgura** = LS − ES. Las tareas con holgura cero forman el camino crítico.

**Ejemplo:** el proyecto on-prem, en semanas:

| Tarea | Dur. | Depende de | ES | EF | LS | LF | Holgura |
|---|---|---|---|---|---|---|---|
| A. Alcance y golden set | 2 | — | 0 | 2 | 0 | 2 | 0 |
| B. Aprobación de acceso a datos | 4 | — | 0 | 4 | 1 | 5 | 1 |
| C. Infraestructura on-prem | 3 | A | 2 | 5 | 2 | 5 | 0 |
| D. Indexar manuales y tickets | 2 | B, C | 5 | 7 | 5 | 7 | 0 |
| E. Servidor MCP de tickets | 3 | A | 2 | 5 | 4 | 7 | 2 |
| F. Evaluación offline | 2 | D, E | 7 | 9 | 7 | 9 | 0 |
| G. Revisión de seguridad | 1 | F | 9 | 10 | 9 | 10 | 0 |
| H. Piloto | 2 | G | 10 | 12 | 10 | 12 | 0 |

Paso a paso: D no puede empezar hasta que terminen B (semana 4) y C (semana 5), así que empieza en la 5. F espera a D (7) y a E (5): empieza en la 7. El proyecto dura 12 semanas. En la pasada hacia atrás, E tiene que terminar a más tardar en la 7 (cuando empieza F), pero termina en la 5: tiene 2 semanas de holgura. B tiene que terminar en la 5 y termina en la 4: 1 semana. El camino crítico es **A → C → D → F → G → H** (2 + 3 + 2 + 2 + 1 + 2 = 12). La fecha acordada con el cliente es el final de la semana 13, así que queda una semana de colchón.

```gantt
titulo: Asistente on-prem: plan base
unidad: semana
Alcance y golden set | 0 | 2 | critica
Aprobación de acceso a datos | 0 | 4
Infraestructura on-prem | 2 | 3 | critica
Indexar manuales y tickets | 5 | 2 | critica
Servidor MCP de tickets | 2 | 3
Evaluación offline | 7 | 2 | critica
Revisión de seguridad | 9 | 1 | critica
Piloto con 20 operadores | 10 | 2 | critica
Colchón del proyecto | 12 | 1
Hito: go-live del cliente | 13 | 0 | critica
```

**Por qué importa:** si alguien propone sumar una persona al servidor MCP para "ir más rápido", el cálculo muestra que no adelanta nada: E no está en el camino crítico. El esfuerzo extra rinde en C o en D.

### Nivelación de recursos

El CPM supone recursos ilimitados. En la realidad, la misma persona no puede hacer dos tareas a la vez. La **nivelación de recursos** reordena tareas para que nadie quede sobreasignado, usando primero la holgura disponible.

**Ejemplo:** si C (infraestructura) y E (servidor MCP) los hace la misma ingeniera de plataforma, no pueden ir en paralelo en las semanas 2 a 5. E tiene 2 semanas de holgura, pero dura 3: si se corre al final de C (semana 5 a 8), termina una semana después de su final tardío y empuja todo el proyecto una semana. Las alternativas son sumar a otra persona en E, dividir E o aceptar el atraso consumiendo el colchón.

**Por qué importa:** un plan que no mira quién hace cada cosa suele tener un camino crítico falso; el verdadero pasa por la persona más cargada.

### Colchones (buffers)

En lugar de inflar cada tarea, se agrega un **colchón explícito** al final del camino crítico (colchón del proyecto) y, a veces, donde una rama no crítica se une a la crítica (colchón de alimentación). Esta idea viene de la *cadena crítica*: las tareas se estiman sin padding y el margen se gestiona de forma visible (ver [Estimación de esfuerzo](#t/estimacion)).

**Ejemplo:** con 12 semanas de plan y la fecha del cliente en la 13, el colchón es de 1 semana. Se mide su consumo: si en la semana 6 ya se consumió el 80 % del colchón con solo la mitad del camino crítico hecha, es momento de replanificar, no de esperar.

**Por qué importa:** el colchón visible permite una conversación temprana y honesta; el escondido se consume en silencio.

### Mantener vivo el plan: línea base y real

Un plan que no se actualiza deja de ser útil en dos semanas. La práctica es guardar una **línea base** (el plan aprobado) y compararla cada semana con lo **real**. Las diferencias se analizan en el camino crítico primero: un atraso de 2 semanas en una tarea con 3 de holgura no es noticia; uno de 2 días en una tarea crítica sí.

Cuando el desvío es grande, se **replanifica**: se ajustan dependencias, se divide trabajo o se negocia alcance, y la nueva versión pasa a ser la línea base, dejando registro de por qué cambió.

**Ejemplo:** en la semana 3, el área legal del cliente avisa que la aprobación de acceso a datos (B) va a tardar 6 semanas en lugar de 4. Con el plan original, D empezaría en la 6, F en la 8 y el piloto terminaría en la 13: se consume todo el colchón. El equipo replanifica: divide D en dos partes. Los manuales públicos de Rumbo no necesitan aprobación y se indexan apenas está la infraestructura (semana 5); los tickets del cliente se indexan en una semana cuando llega la aprobación (semana 6). F sigue empezando en la 7.

```gantt
titulo: Asistente on-prem: replanificado tras la demora legal
unidad: semana
Alcance y golden set | 0 | 2
Aprobación de acceso a datos | 0 | 6 | critica
Infraestructura on-prem | 2 | 3
Indexar manuales públicos | 5 | 1
Indexar tickets del cliente | 6 | 1 | critica
Servidor MCP de tickets | 2 | 3
Evaluación offline | 7 | 2 | critica
Revisión de seguridad | 9 | 1 | critica
Piloto con 20 operadores | 10 | 2 | critica
Colchón del proyecto | 12 | 1
Hito: go-live del cliente | 13 | 0 | critica
```

El camino crítico ahora pasa por la aprobación legal: B → indexar tickets → F → G → H. A y C ganaron una semana de holgura.

**Por qué importa:** la replanificación no recuperó tiempo trabajando más, sino rompiendo una dependencia. Además dejó a la vista que el proyecto depende de un tercero y que cualquier atraso adicional de legal mueve la fecha: hay que seguirlo cada semana.

### Gantt, roadmap y tablero Kanban

Son herramientas para preguntas distintas:

| Herramienta | Responde | Conviene cuando | No conviene cuando |
|---|---|---|---|
| Gantt | ¿Llegamos a la fecha? ¿Qué la decide? | Fecha dura, dependencias externas, varios equipos coordinados | El alcance cambia cada semana |
| Roadmap ahora / después / más adelante | ¿Qué es prioritario y en qué orden? | Producto en evolución, comunicación con dirección | Hay un compromiso contractual con fecha |
| Tablero Kanban | ¿Qué está en curso y qué está trabado? | Trabajo continuo, flujo de tareas parecidas | Hay que coordinar entregas con terceros |

**Ejemplo:** el asistente de soporte de Rumbo para todos los comercios evoluciona con un roadmap y se ejecuta con un tablero Kanban. La instalación on-prem para el cliente grande, con un go-live firmado, se gestiona además con un Gantt de 10 filas que se revisa cada semana.

**Por qué importa:** no son excluyentes. El error es usar una sola para todo: un Gantt para un producto exploratorio se vuelve ficción; un tablero Kanban para una instalación con fecha esconde el camino crítico.

### Planificar un proyecto con agentes y LLMs

Los proyectos con LLMs tienen tareas que los planes tradicionales omiten y que suelen quedar en el camino crítico:

- **Evaluación como tarea explícita:** armar el golden set y correr la evaluación lleva semanas, no una tarde. Va en el plan con su hito: "90 % en el golden set" (ver [Evaluación de LLMs](#t/evaluacion-llms)).
- **Revisión de seguridad:** un agente con herramientas que acceden a datos del cliente necesita una revisión de permisos, inyección de prompts y exfiltración antes del piloto (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).
- **Dependencias del proveedor:** cuotas de tokens por minuto, aprobación de acceso a un modelo, deprecación de una versión. Son externas y van como tales.
- **Aprobaciones de acceso a datos:** casi siempre son externas, lentas y críticas.

**Ejemplo:** el agente interno de operaciones de Rumbo necesitaba acceso de solo lectura a las métricas de producción. El plan original lo tenía como "configurar permisos: 1 día". En la práctica, la aprobación del equipo de seguridad llevó 3 semanas y fue la tarea más larga del proyecto.

**Por qué importa:** un plan de proyecto con LLM que no tiene evaluación ni revisión de seguridad como barras propias va a descubrirlas tarde, justo antes del go-live.

### Usar un LLM para armar la WBS

Un LLM es muy bueno generando un primer borrador de WBS y de lista de dependencias a partir de un documento de alcance: en minutos produce una estructura razonable y recuerda tareas genéricas que a veces se olvidan (documentación, capacitación, rollback). Pero no conoce las restricciones reales del proyecto: qué aprobaciones exige el cliente, quién está de vacaciones, qué equipo es el cuello de botella.

El uso sano es tratar el borrador como una lista de preguntas: cada tarea se valida con quien la va a hacer, cada dependencia se confirma y las duraciones se estiman con el equipo, no se copian del borrador.

**Ejemplo:** el borrador del LLM para el proyecto on-prem tenía 22 tareas bien ordenadas, pero ponía la aprobación de acceso a datos como "1 día" y no incluía la revisión de seguridad. También sugería una dependencia inexistente entre el servidor MCP y el indexado. Tras revisarlo con el equipo quedaron 15 tareas, con la aprobación legal marcada como externa.

**Por qué importa:** un plan generado y no validado tiene la apariencia de rigor sin el contenido; las duraciones inventadas son lo más peligroso.

## Casos prácticos

### El go-live con fecha firmada

**Situación:** el área comercial firma con un cliente grande un go-live en 13 semanas antes de que ingeniería vea el alcance. El primer cálculo del camino crítico da 14 semanas.

**Qué se hace:** se buscan formas de acortar el camino crítico sin magia: se divide el indexado para romper la dependencia con la aprobación legal, se adelanta el armado del golden set en paralelo con la infraestructura y se reduce el piloto de 3 a 2 semanas con más operadores. El plan queda en 12 semanas con 1 de colchón. Se acuerda con comercial que las próximas fechas se firman después de un primer cálculo de camino crítico.

### Más gente en la tarea equivocada

**Situación:** el proyecto viene atrasado y la dirección suma dos ingenieros "para acelerar". Los asignan al servidor MCP, la tarea más visible.

**Qué se hace:** se muestra la tabla de holguras: el servidor MCP tiene 2 semanas de holgura y no mueve la fecha. Los ingenieros se reasignan a la infraestructura on-prem, que está en el camino crítico, y uno de ellos prepara el indexado de manuales públicos para adelantarlo.

### La versión del modelo que se deprecaba en medio del piloto

**Situación:** a mitad del proyecto, el proveedor anuncia que la versión del modelo usada en la evaluación se retira en 8 semanas, justo después del go-live.

**Qué se hace:** se agrega al plan una tarea explícita de "reevaluar con la versión nueva" (1 semana), en paralelo con la revisión de seguridad para no tocar el camino crítico, y un hito de decisión antes del piloto. Se registra como riesgo con su disparador y responsable.

## Errores comunes

- **Plan sin dependencias externas.** Las aprobaciones, los proveedores y el cliente van como tareas con dueño y fecha comprometida, no como supuestos.
- **Colchón repartido en cada tarea.** Se consume sin que nadie lo vea; se concentra al final del camino crítico y se mide su consumo.
- **No actualizar el plan.** Un Gantt que no se compara con lo real cada semana es decoración; se mantiene línea base, real y motivo de cada cambio.
- **Ignorar la carga de las personas.** Si una persona tiene dos tareas críticas en paralelo, el plan es falso; se nivela.
- **Olvidar evaluación y seguridad en proyectos con LLM.** Van como tareas propias, con duración realista, y casi siempre en el camino crítico.
- **Copiar las duraciones de un borrador generado por un LLM.** El borrador sirve para no olvidar tareas; las duraciones se estiman con el equipo.

## Para discutir en equipo

- ¿Qué proyectos actuales tienen una fecha dura con un tercero y no tienen el camino crítico calculado?
- ¿Cuál de nuestras dependencias externas (aprobaciones, proveedores, clientes) es hoy la más riesgosa?
- ¿Tratamos la evaluación y la revisión de seguridad como tareas con duración propia o como "algo que se hace al final"?
- ¿Cuándo nos sirve un Gantt y cuándo nos alcanza con un roadmap y un tablero?
- ¿Cómo validamos un plan o una WBS que generó un LLM antes de comprometernos con fechas?
