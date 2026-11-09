---
slug: wbs-edt
titulo: EDT o WBS: estructura de desglose del trabajo
resumen: Cómo descomponer un proyecto en entregables y paquetes de trabajo que cubren todo el alcance, para estimar, planificar y asignar responsables sin olvidar trabajo invisible.
lectura: 13
---

## La idea central

La **EDT** (estructura de desglose del trabajo), conocida en inglés como **WBS** (*work breakdown structure*), es un árbol que parte el proyecto en piezas cada vez más chicas hasta llegar a unidades que alguien puede estimar, hacer y entregar. La raíz es el resultado final ("piloto del asistente para transportistas"); las ramas son los entregables que lo componen; las hojas son **paquetes de trabajo**.

Lo importante es qué se descompone: **entregables, no actividades**. Una EDT no es una lista de tareas ordenada en el tiempo, sino un inventario completo de lo que hay que producir. Es como el plano de una casa antes del cronograma de obra: si en el plano falta la instalación eléctrica, ningún cronograma la va a agregar. El tema de [planificación y Gantt](#t/planificacion-gantt) presenta la EDT en pocas líneas y se concentra en dependencias y camino crítico; aquí se profundiza en cómo armarla bien.

## Conceptos

### Jerarquía orientada a entregables

Cada nivel de la EDT responde a la pregunta "¿de qué está hecho esto?". El primer nivel suele tener entre 4 y 8 entregables grandes, que se descomponen hasta que cada pieza se puede estimar con confianza.

Un entregable es un **sustantivo verificable**: "golden set de 200 consultas", "servidor MCP de pedidos asignados", "runbook de guardia". Una actividad es un verbo sin final claro: "investigar", "programar", "probar". La diferencia práctica es que un entregable se puede aceptar o rechazar; una actividad solo se puede dar por terminada cuando alguien se cansa.

**Ejemplo:** el piloto descompuesto por actividades, como suele salir en un primer borrador:

```arbol
titulo: Desglose por actividades (a evitar)
Piloto del asistente
- Reuniones de arranque
- Investigar
-- Investigar modelos
-- Investigar datos
- Programar
-- Backend
-- Frontend
- Probar
- Arreglar errores
- Lanzar
```

No aparecen la evaluación, la revisión de seguridad ni el runbook; "arreglar errores" no tiene tamaño y "investigar" puede durar cualquier cosa. La versión por entregables está en la regla del 100 %.

**Por qué importa:** si la EDT describe actividades, el proyecto se mide por esfuerzo gastado ("programamos tres semanas") en lugar de por cosas terminadas ("el servidor MCP pasó sus criterios de aceptación").

### La regla del 100 %

La regla central de la EDT dice que **la suma de los hijos es exactamente el padre**: ni más ni menos. Todo el trabajo del proyecto está en algún paquete, y nada que esté fuera del alcance aparece en el árbol. Se aplica en cada nivel: los hijos de "Calidad y seguridad" tienen que cubrir todo lo que significa calidad y seguridad para este piloto.

En la práctica, la regla se viola por omisión: falta trabajo poco visible como gestión, acceso a datos, documentación u operación. Por eso muchas EDT tienen ramas explícitas de **gestión del proyecto** y de **operación y lanzamiento**.

**Ejemplo:** EDT completa del piloto del asistente para transportistas de Rumbo, con tres niveles debajo de la raíz.

```arbol
titulo: EDT del piloto para transportistas
Piloto del asistente para transportistas
- 1 Gestión del proyecto
-- 1.1 Plan y seguimiento semanal
-- 1.2 Registro de riesgos y decisiones
- 2 Datos y conocimiento
-- 2.1 Aprobación de acceso a pedidos
-- 2.2 Índice de instructivos de retiro
-- 2.3 Golden set de 200 consultas
- 3 Agente y herramientas
-- 3.1 Servidor MCP de pedidos asignados
--- 3.1.1 Herramienta de consulta de retiro
--- 3.1.2 Filtro por transportista
-- 3.2 Prompt y política de derivación
- 4 Canal para transportistas
-- 4.1 Chat en la app de transportistas
-- 4.2 Derivación a un operador
- 5 Calidad y seguridad
-- 5.1 Evaluación offline
-- 5.2 Revisión de seguridad
- 6 Operación y lanzamiento
-- 6.1 Tableros, alertas y costo
-- 6.2 Runbook y guardia
-- 6.3 Piloto con 100 transportistas
-- 6.4 Documentación y capacitación
```

La rama 3.1 se cumple con la regla si "herramienta de consulta" y "filtro por transportista" son todo el servidor MCP. Si el servidor también necesita autenticación propia, falta un 3.1.3 y la estimación de 3.1 va a quedar corta.

**Por qué importa:** cada hueco en la EDT reaparece después como una sorpresa en el cronograma, casi siempre en la última semana.

### Elementos mutuamente excluyentes

La otra mitad de la regla del 100 % es que **ningún trabajo aparece dos veces**. Si "pruebas de inyección de prompts" está en 3.2 (prompt) y también en 5.2 (revisión de seguridad), se estima dos veces, dos personas creen que es suyo o, peor, cada una supone que lo hace la otra.

Se resuelve eligiendo un único lugar y escribiendo en el diccionario de la EDT qué incluye y qué no cada paquete.

**Ejemplo:** el equipo decide que las pruebas de inyección viven en 5.2, y que 3.2 solo entrega el prompt con sus reglas de derivación. El diccionario de 3.2 dice: "No incluye pruebas adversariales (ver 5.2)".

**Por qué importa:** la superposición infla la estimación y diluye la responsabilidad al mismo tiempo.

### Niveles y numeración

La numeración jerárquica (1, 1.1, 1.1.1) da a cada elemento un identificador estable que se usa en el cronograma, la matriz de responsabilidades, los tickets y las conversaciones ("3.1.2 está bloqueado").

No todas las ramas necesitan la misma profundidad, y los códigos no se reutilizan: si 4.3 se elimina, el siguiente nuevo es 4.4, para que los tickets viejos no apunten a otra cosa.

**Ejemplo:** en la EDT del piloto, la rama 1 termina en el nivel 2 (dos paquetes chicos), mientras que 3.1 baja al nivel 3 porque el servidor MCP es la pieza más grande e incierta.

**Por qué importa:** un código común hace que plan, tablero y conversaciones hablen de lo mismo.

### Paquetes de trabajo y la heurística 8/80

Un **paquete de trabajo** es una hoja del árbol: la unidad mínima que se estima, se asigna a un responsable y se acepta. ¿Cuándo dejar de descomponer? La heurística **8/80** dice que un paquete debería llevar entre 8 y 80 horas de esfuerzo: menos de 8 es microgestión; más de 80 (unas dos semanas de una persona) esconde demasiada incertidumbre. Además, que lo termine una persona o un par dentro de un período de reporte y que tenga un criterio de aceptación claro.

**Ejemplo:** la primera estimación de 3.1 Servidor MCP fue de 120 horas, fuera del rango. Al descomponerlo, quedaron 3.1.1 Herramienta de consulta de retiro (56 h) y 3.1.2 Filtro por transportista (40 h). La suma, 96 h, es mayor que la estimación original: al partir apareció trabajo que no se había visto (el filtro tiene que probarse contra pedidos de otros transportistas). En el otro extremo, "1.2 Registro de riesgos" lleva 12 horas en todo el piloto: no tiene sentido partirlo más.

**Por qué importa:** descomponer también descubre trabajo; es habitual que los hijos sumen más que la estimación del padre.

### Diccionario de la EDT

El árbol muestra nombres; el **diccionario de la EDT** dice qué significa cada nombre. Para cada paquete de trabajo registra, como mínimo: qué incluye y qué no, el responsable, la estimación, las dependencias y el criterio de aceptación. No hace falta un documento largo: una tabla o una ficha por paquete alcanza.

**Ejemplo:** ficha de dos paquetes del piloto.

| Código | Incluye | No incluye | Responsable | Estimación | Aceptación |
|---|---|---|---|---|---|
| 2.3 Golden set | 200 consultas reales anonimizadas con respuesta esperada y etiqueta de derivación | Casos en otros idiomas | Analista de soporte | 40 h | Revisado por dos personas; cubre los 8 motivos principales |
| 3.1.2 Filtro por transportista | Validar que cada consulta solo devuelva pedidos asignados a quien pregunta | Permisos de operadores internos | Backend | 40 h | Pruebas con 50 casos cruzados; cero fugas |

**Por qué importa:** el diccionario convierte el árbol en un acuerdo. Sin él, "golden set" significa 50 consultas para una persona y 500 para otra.

### Por entregables o por fases

Hay dos formas de organizar el primer nivel:

- **Por entregables o componentes:** datos, agente, canal, calidad, operación. Es la forma recomendada en la mayoría de los proyectos de software.
- **Por fases:** descubrimiento, construcción, piloto, lanzamiento. Conviene cuando las fases tienen aprobaciones formales entre sí o equipos distintos.

| Criterio | Por entregables | Por fases |
|---|---|---|
| Pregunta que responde | ¿Qué se produce? | ¿En qué etapa estamos? |
| Responsables | Claros por componente | Cambian de fase a fase |
| Riesgo típico | Olvidar trabajo transversal (gestión, documentación) | Mezclar tiempo con alcance y repetir trabajo en cada fase |
| Conviene en | Proyectos de producto y plataforma | Proyectos con compuertas de aprobación externas |

Se pueden combinar (fases en el nivel 1, entregables en el 2), pero no conviene mezclar criterios dentro del mismo nivel ("Datos", "Fase de pruebas", "Backend").

**Ejemplo:** para la instalación on-prem en un cliente grande, con aprobaciones formales del cliente al final de cada etapa, el equipo usa fases en el nivel 1. Para el piloto interno, entregables.

**Por qué importa:** el criterio del nivel 1 decide cómo se reporta el avance y quién es dueño de cada parte.

### De la EDT a estimaciones, cronograma y responsables

La EDT es el punto de partida de los otros artefactos de planificación:

1. **Estimación:** se estima cada paquete y se suma hacia arriba (estimación *bottom-up*). Conviene usar rangos o tres puntos, como se explica en [estimación de esfuerzo](#t/estimacion).
2. **Cronograma:** cada paquete se convierte en una o más barras del Gantt; se agregan dependencias e hitos.
3. **Responsables:** cada paquete es una fila de la [matriz RACI](#t/raci-rasi), con un único responsable que rinde cuentas.

**Ejemplo:** sumando los paquetes del piloto, con estimaciones hipotéticas.

| Rama | Horas |
|---|---|
| 1 Gestión del proyecto | 60 |
| 2 Datos y conocimiento | 112 |
| 3 Agente y herramientas | 136 |
| 4 Canal para transportistas | 104 |
| 5 Calidad y seguridad | 88 |
| 6 Operación y lanzamiento | 120 |
| **Total** | **620** |

Con 4 personas dedicadas al 70 %, unas 112 horas efectivas por semana, el esfuerzo da alrededor de 5,5 semanas; el cronograma real será más largo por las dependencias (la aprobación de acceso a pedidos es externa). Las ramas 1, 5 y 6 suman 268 horas, el 43 % del total: es el trabajo que un desglose por actividades no habría mostrado.

**Por qué importa:** una estimación hecha sobre la EDT se puede discutir pieza por pieza; un número global ("son dos meses") solo se puede aceptar o rechazar.

### Un LLM puede redactar la EDT, pero olvida lo invisible

Un LLM produce en segundos una EDT razonable a partir de un [PRD](#t/prd). Pero un PRD describe lo que ve el usuario, y el modelo descompone eso: lo que el usuario no ve casi nunca aparece.

Lista de trabajo invisible para revisar en cualquier EDT de un sistema con LLMs o agentes:

- **Evaluación:** golden set, métricas, corridas offline y su hito de aprobación.
- **Revisión de seguridad:** permisos de herramientas, inyección de prompts, exfiltración de PII.
- **Acceso a datos:** aprobaciones, anonimización, cuentas de servicio.
- **Operación:** tableros, alertas, runbook, guardia, límites de costo de tokens.
- **Documentación y capacitación:** para operadores de soporte y para el equipo que hereda el sistema.
- **Gestión:** seguimiento, riesgos, comunicación con quienes esperan el resultado.
- **Retiro o migración:** qué pasa con el proceso anterior y cuándo se apaga.

**Ejemplo:** el borrador de un LLM para el piloto tenía 18 paquetes, todos de las ramas 2, 3 y 4. Faltaban la revisión de seguridad, el runbook, la capacitación y la aprobación de acceso a pedidos. Aplicando la lista, se agregaron 7 paquetes y 230 horas.

**Por qué importa:** el borrador ahorra tiempo de redacción, pero la regla del 100 % la verifica el equipo, no el modelo.

### Paquetes de trabajo como unidades para agentes de código

Un buen paquete de trabajo tiene casi todo lo que necesita un agente de código: alcance acotado, qué incluye y qué no, dependencias y criterio de aceptación. Si el diccionario de la EDT está bien escrito, la ficha de un paquete es el esqueleto de la especificación que se le entrega al agente.

No todos los paquetes sirven para eso. Los que producen código con pruebas verificables (3.1.1, 3.1.2, 4.2) son buenos candidatos; los que dependen de decisiones humanas o externas (2.1 aprobación de acceso, 5.2 revisión de seguridad, 6.3 piloto) no.

**Ejemplo:** el paquete 3.1.2 Filtro por transportista se entrega a un agente con la ficha del diccionario, las interfaces del servidor MCP y los 50 casos cruzados como pruebas de aceptación. El agente produce el código en una tarde; la revisión humana lleva 6 horas porque es un control de acceso. La estimación del paquete baja de 40 a unas 16 horas, no a 4.

**Por qué importa:** la heurística 8/80 se mantiene, pero la mezcla cambia: menos horas de escritura y proporcionalmente más de especificación y revisión.

## Casos prácticos

### El proyecto que "estaba al 90 %" durante un mes

**Situación:** el piloto del asistente reportó 90 % de avance durante cuatro semanas seguidas. El plan original tenía ítems como "desarrollo del agente" y "pruebas", sin criterios de aceptación.

**Qué se hace:** se reescribe el plan como EDT por entregables con diccionario, y aparecen tres paquetes que nadie tenía: runbook, capacitación de operadores y revisión de seguridad. El avance se recalcula contando paquetes aceptados, no esfuerzo gastado: da 62 %. La fecha se renegocia con datos en lugar de seguir reportando 90 %.

### Dos equipos con el mismo trabajo

**Situación:** el equipo de plataforma y el del asistente estimaron, cada uno por su lado, "observabilidad del agente". Las dos estimaciones sumaban 90 horas y ninguno sabía que el otro la había incluido.

**Qué se hace:** al consolidar la EDT, el elemento aparece en dos ramas y viola la exclusividad. Se deja un único paquete, 6.1 Tableros, alertas y costo, con plataforma como responsable, y en el diccionario del paquete del asistente se aclara qué métricas emite el agente (que sí son suyas). El total baja 40 horas y la responsabilidad queda en un solo lugar.

### Del PRD a tareas para agentes de código

**Situación:** se le pasa a un agente de código el PRD completo para implementar el canal de chat. El resultado mezcla pantallas, derivación y cambios en el servidor MCP en un PR de 2.000 líneas.

**Qué se hace:** se vuelve a la EDT. El canal se divide en 4.1 Chat en la app y 4.2 Derivación a un operador, cada uno con su ficha y sus pruebas. El agente recibe un paquete por vez; cada PR queda por debajo de 400 líneas y se revisa en el día. Los paquetes que requieren decisiones (qué mensaje ve el transportista cuando se deriva) se cierran antes con producto.

## Errores comunes

- **Descomponer por actividades.** "Investigar", "programar" y "probar" no tienen final verificable; se reemplazan por entregables con criterio de aceptación.
- **Olvidar el trabajo invisible.** Evaluación, seguridad, acceso a datos, operación y documentación van como ramas propias; se revisa la lista en cada EDT.
- **Repetir trabajo en dos ramas.** Se elige un solo lugar y se escribe en el diccionario qué incluye y qué no cada paquete.
- **Paquetes de 200 horas.** Esconden la incertidumbre donde más duele; se parten hasta quedar cerca del rango 8/80.
- **Confundir la EDT con el cronograma.** La EDT no tiene orden ni fechas; el orden se define después, en el Gantt.
- **Aceptar sin revisar la EDT que redactó un LLM.** Sirve como borrador; la completitud la verifica el equipo con la regla del 100 %.

## Para discutir en equipo

- En nuestro proyecto actual, ¿qué porcentaje del esfuerzo está en gestión, calidad y operación? ¿Es realista?
- ¿Qué trabajo invisible apareció tarde en los últimos dos proyectos y en qué rama de la EDT debería haber estado?
- ¿Conviene organizar el nivel 1 por entregables o por fases en el próximo proyecto on-prem?
- ¿Qué paquetes de nuestra EDT actual podría tomar un agente de código con una especificación, y cuáles no?
- ¿Quién mantiene el diccionario de la EDT cuando cambia el alcance?
