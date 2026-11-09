---
slug: priorizacion
titulo: Herramientas de priorización
resumen: Técnicas para decidir qué hacer primero, como Eisenhower, MoSCoW, RICE y WSJF, aplicadas a un backlog real que incluye casos de uso con agentes.
lectura: 14
---

## La idea central

Siempre hay más trabajo posible que capacidad para hacerlo. Priorizar es elegir qué se hace ahora, qué después y qué no se hace, y poder explicar por qué. Las herramientas de priorización no deciden por nosotros: ordenan la conversación. Obligan a nombrar los criterios (valor, urgencia, esfuerzo, riesgo) y a comparar cosas distintas con la misma vara.

Ninguna herramienta sirve para todo. Algunas son rápidas y gruesas, como una matriz de dos ejes; otras piden números y dan una sensación de precisión que a veces no tienen. Lo útil es conocer varias, saber qué pregunta responde cada una y usarlas sobre el mismo backlog para ver dónde coinciden y dónde no.

Para todo el tema usamos un único backlog de Rumbo:

| # | Ítem | Equipo |
|---|---|---|
| 1 | El asistente responde consultas de transportistas | Asistente de soporte |
| 2 | Redacción de PII en los logs del asistente | Asistente de soporte |
| 3 | Reentrenar el modelo de ETA (deriva en zona norte) | Modelo de ETA |
| 4 | Modo oscuro en el panel de comercios | Frontend |
| 5 | Servidor MCP de zonas para el agente de operaciones | Plataforma |
| 6 | Migrar el modelo fijo del asistente antes de su deprecación (6 semanas) | Asistente de soporte |
| 7 | Exportar reportes de entregas en CSV para comercios grandes | Frontend |
| 8 | Alertas de guardia basadas en SLO con burn rate | Plataforma |
| 9 | Rediseño del alta de comercios nuevos | Producto |

## Conceptos

### Matriz de Eisenhower

La **matriz de Eisenhower** separa dos ejes que solemos confundir: **urgente** (tiene una fecha cercana o algo se rompe si no se atiende) e **importante** (contribuye a los objetivos de fondo). Cada cuadrante tiene una acción:

```cuadrante
titulo: Matriz de Eisenhower
eje-x: No urgente | Urgente
eje-y: No importante | Importante
arriba-izquierda: Planificar | 1 Asistente para transportistas; 3 Reentrenar ETA; 5 MCP de zonas; 8 Alertas por SLO
arriba-derecha: Hacer ya | 2 PII en logs (ya detectada); 6 Deprecación en 6 semanas
abajo-izquierda: Descartar o posponer | 4 Modo oscuro; 9 Rediseño del alta (por ahora)
abajo-derecha: Delegar o automatizar | 7 CSV que un comercio pide para mañana
```

El cuadrante más valioso es "importante y no urgente": ahí está lo que mejora el sistema a largo plazo. La trampa es **vivir en "urgente"**: cada semana aparece algo con fecha, se atiende, y lo importante no llega nunca hasta que se vuelve urgente (el reentrenamiento del modelo se vuelve urgente cuando la ETA ya está mal y los comercios reclaman).

**Ejemplo:** el pedido del CSV para mañana es urgente para un comercio, pero no cambia los objetivos del trimestre. Se resuelve con un script ad hoc o lo atiende soporte; el reporte exportable de verdad compite después con el resto.

**Por qué importa:** si más de la mitad del tiempo se va en el cuadrante urgente, el problema no es de priorización sino de capacidad o de prevención.

### MoSCoW para definir el alcance de una entrega

**MoSCoW** clasifica requisitos de una entrega concreta en cuatro grupos: **Must** (sin esto no se lanza), **Should** (importante, pero se puede lanzar sin él), **Could** (deseable si sobra tiempo) y **Won't** (explícitamente fuera de esta versión). No ordena un backlog entero; recorta el alcance de un lanzamiento.

**Ejemplo:** primera versión del asistente para transportistas (ítem 1):

- **Must:** responder dónde y cuándo retirar un pedido asignado, con una herramienta de solo lectura; no revelar datos de pedidos de otros transportistas; derivar a una persona si no sabe; evaluación sobre 200 conversaciones reales.
- **Should:** avisar si el comercio cambió el horario de retiro.
- **Could:** responder por mensaje de voz.
- **Won't:** que el agente reasigne pedidos o cambie el estado de una entrega.

Una regla práctica es que los Must no superen alrededor del 60% del esfuerzo estimado, para dejar margen.

**Por qué importa:** el grupo Won't es tan valioso como el Must: deja escrito lo que no se hace, y evita que un agente de código o una persona lo agregue "de paso".

### Matriz de impacto y esfuerzo

Es la herramienta más rápida: se ubica cada ítem según su **impacto** esperado y su **esfuerzo**, ambos en escala gruesa (alto o bajo). Quedan cuatro grupos:

- **Quick wins** (alto impacto, bajo esfuerzo): se hacen primero.
- **Grandes apuestas** (alto impacto, alto esfuerzo): se planifican y se parten.
- **Rellenos** (bajo impacto, bajo esfuerzo): para huecos entre trabajo mayor.
- **Pozos sin fondo** (bajo impacto, alto esfuerzo): se evitan.

**Ejemplo:** el reentrenamiento del modelo de ETA (3) es un quick win: el pipeline ya existe y el error en zona norte afecta a todos los comercios de la zona. El asistente para transportistas (1) es una gran apuesta. El modo oscuro (4) es un relleno. El rediseño completo del alta (9), con tres equipos involucrados y sin evidencia de que el alta actual sea un problema, cae en pozo sin fondo hasta que haya datos.

```cuadrante
titulo: Impacto y esfuerzo
eje-x: Bajo esfuerzo | Alto esfuerzo
eje-y: Bajo impacto | Alto impacto
arriba-izquierda: Quick wins | 3 Reentrenar ETA
arriba-derecha: Grandes apuestas | 1 Asistente para transportistas
abajo-izquierda: Rellenos | 4 Modo oscuro
abajo-derecha: Pozos sin fondo | 9 Rediseño del alta
```

**Por qué importa:** sirve para una primera pasada en 15 minutos. Su debilidad es que "alto" y "bajo" dependen de quién opina, así que conviene anotar el porqué de cada ubicación.

### RICE: alcance, impacto, confianza y esfuerzo

**RICE** pone números a la intuición anterior:

```text
RICE = (Alcance × Impacto × Confianza) / Esfuerzo
```

- **Alcance (Reach):** cuántas personas o eventos afecta en un período, siempre en la misma unidad. Aquí, usuarios afectados por trimestre.
- **Impacto:** escala fija, por ejemplo 3 = masivo, 2 = alto, 1 = medio, 0,5 = bajo, 0,25 = mínimo.
- **Confianza:** cuánto creemos en las otras estimaciones: 100%, 80% o 50%.
- **Esfuerzo:** persona-mes.

**Ejemplo:** con cifras hipotéticas:

| Ítem | Alcance | Impacto | Confianza | Esfuerzo | RICE |
|---|---|---|---|---|---|
| 3. Reentrenar ETA | 2.000 comercios | 1 | 80% | 1 | 1.600 |
| 4. Modo oscuro | 2.000 comercios | 0,25 | 80% | 0,5 | 800 |
| 1. Asistente para transportistas | 3.000 transportistas | 2 | 50% | 4 | 750 |
| 7. Exportar CSV | 150 comercios | 2 | 100% | 0,5 | 600 |
| 5. MCP de zonas | 40 operadores | 3 | 50% | 1 | 60 |

Ordenados por puntaje, la distancia entre el primero y el último se ve de un vistazo:

```barras
titulo: Puntaje RICE (cifras hipotéticas)
unidad: puntos
3. Reentrenar ETA | 1600
4. Modo oscuro | 800
1. Asistente para transportistas | 750
7. Exportar CSV | 600
5. MCP de zonas | 60
```

El cálculo para el asistente: 3.000 × 2 × 0,5 / 4 = 750. El resultado es útil y, a la vez, muestra límites del método. El modo oscuro queda por encima del asistente porque toca a muchos y cuesta poco. El servidor MCP queda último porque lo usan 40 operadores, aunque cada investigación de alertas que acelera puede evitar horas de entregas tardías. El CSV toca pocos comercios, pero son los más grandes. Los ítems 2, 6 y 8 ni siquiera entran bien: su valor es reducir riesgo, y RICE no lo mide.

El factor de **confianza** es lo más interesante de RICE: castiga las ideas sin evidencia. Si un spike de una semana sube la confianza del asistente al 80%, su puntaje pasa a 1.200.

**Por qué importa:** RICE obliga a decir en voz alta cuántos usuarios y con qué certeza. Pero mide valor de producto, no riesgo ni deuda técnica; esos ítems necesitan otro carril.

### Costo de demora y WSJF

El **costo de demora** (*cost of delay*) pregunta cuánto se pierde por cada semana que un ítem no está listo. Cambia el foco de "cuánto vale" a "cuánto vale **hacerlo antes**".

**Ejemplo:** medido en horas, el asistente para transportistas ahorraría unas 60 horas semanales de soporte y tarda 8 semanas. El reentrenamiento de ETA ahorraría unas 20 horas semanales en reclamos y tarda 2 semanas.

- Si se hace primero el asistente, el reentrenamiento se demora 8 semanas: 8 × 20 = 160 horas perdidas.
- Si se hace primero el reentrenamiento, el asistente se demora 2 semanas: 2 × 60 = 120 horas perdidas.

Conviene empezar por el reentrenamiento, aunque valga menos. La regla general es dividir el costo de demora por la duración (60 / 8 = 7,5 contra 20 / 2 = 10) y empezar por el mayor.

**WSJF** (*weighted shortest job first*) aplica la misma idea con escalas relativas, al estilo de SAFe. El costo de demora se arma con tres componentes puntuados con la serie 1, 2, 3, 5, 8, 13: valor para el usuario, criticidad temporal y reducción de riesgo u oportunidad habilitada. Luego se divide por el tamaño.

| Ítem | Valor | Tiempo | Riesgo | Costo de demora | Tamaño | WSJF |
|---|---|---|---|---|---|---|
| 6. Migrar modelo antes de deprecación | 3 | 13 | 8 | 24 | 3 | 8,0 |
| 3. Reentrenar ETA | 8 | 5 | 3 | 16 | 3 | 5,3 |
| 2. Redacción de PII en logs | 5 | 8 | 13 | 26 | 5 | 5,2 |
| 4. Modo oscuro | 2 | 1 | 1 | 4 | 2 | 2,0 |
| 1. Asistente para transportistas | 13 | 3 | 5 | 21 | 13 | 1,6 |

```barras
titulo: Puntaje WSJF
6. Migrar modelo antes de deprecación | 8,0
3. Reentrenar ETA | 5,3
2. Redacción de PII en logs | 5,2
4. Modo oscuro | 2,0
1. Asistente para transportistas | 1,6
```

A diferencia de RICE, WSJF captura la fecha de deprecación y el riesgo de la PII.

**Por qué importa:** el costo de demora explica por qué lo chico y urgente suele ir antes que lo grande y valioso. Un 5,3 contra un 5,2, en cambio, es un empate: la diferencia está dentro del error de estimación.

### Modelo de Kano

El **modelo de Kano** clasifica funcionalidades según cómo reacciona el usuario:

- **Básicas:** se dan por sentadas. Si faltan, hay enojo; si están, nadie lo agradece. Que el asistente no muestre datos de otro destinatario.
- **De desempeño:** más es mejor, de forma lineal. Un ETA más preciso, una respuesta más rápida.
- **De entusiasmo:** no se esperan y sorprenden. Que el asistente avise proactivamente al destinatario de una demora antes de que pregunte.
- **Indiferentes:** no mueven la satisfacción. El modo oscuro, para buena parte de los comercios.

Con el tiempo, las de entusiasmo se vuelven de desempeño y luego básicas.

**Ejemplo:** el equipo del asistente quería invertir en respuestas de entusiasmo, pero el 8% de las respuestas citaba una política vieja. Eso es una falla básica y va primero.

**Por qué importa:** ayuda a no invertir en sorprender mientras falla lo básico.

### Cuándo usar cada herramienta

| Herramienta | Pregunta que responde | Cuándo conviene | Costo de uso |
|---|---|---|---|
| Eisenhower | ¿Qué atiendo yo esta semana? | Agenda personal o del equipo, interrupciones | Minutos |
| MoSCoW | ¿Qué entra en esta entrega? | Recortar el alcance de un lanzamiento | Una reunión |
| Impacto y esfuerzo | ¿Qué es obvio y qué es un pozo? | Primera pasada sobre un backlog largo | Minutos |
| RICE | ¿Qué funcionalidad aporta más por esfuerzo? | Comparar ideas de producto con datos de uso | Horas |
| Costo de demora y WSJF | ¿En qué orden, si el tiempo importa? | Fechas, dependencias, riesgos con vencimiento | Horas |
| Kano | ¿Qué tipo de valor da esto? | Diseñar una versión de producto | Investigación con usuarios |

**Ejemplo:** para el backlog de Rumbo, una combinación razonable es una pasada de impacto y esfuerzo para descartar pozos sin fondo, WSJF para ordenar lo que tiene fecha o riesgo (6, 2, 3) y RICE solo entre funcionalidades de producto comparables (1, 4, 7).

**Por qué importa:** usar la herramienta equivocada da una respuesta precisa a otra pregunta.

### Priorizar casos de uso con LLMs y agentes

Los casos de uso con LLMs tienen dimensiones que un backlog clásico no captura. Conviene puntuar cada uno, de 1 a 5, en:

1. **Valor:** horas ahorradas o mejora medible.
2. **Factibilidad:** si un modelo actual lo resuelve con la calidad necesaria, verificado con un spike y evaluación.
3. **Riesgo:** qué pasa si se equivoca, si es interno o externo, si lee o escribe, si toca PII (ver [riesgos](#t/riesgos)).
4. **Datos disponibles:** si existen los documentos, el historial y los casos de evaluación.

**Ejemplo:**

| Caso de uso | Valor | Factibilidad | Riesgo (5 = bajo) | Datos | Total |
|---|---|---|---|---|---|
| Resumen interno de tickets para soporte | 3 | 5 | 5 | 5 | 18 |
| Agente de operaciones con herramientas de solo lectura | 4 | 4 | 4 | 4 | 16 |
| Asistente que reprograma entregas para destinatarios | 5 | 3 | 2 | 3 | 13 |

La regla que sale de la tabla es la habitual: **empezar por herramientas internas y de bajo riesgo**, donde un error lo ve una persona del equipo y se aprende a operar modelos, y avanzar hacia lo externo y con escritura cuando hay evaluación y controles (ver [agentes](#t/agentes)).

Además, los **agentes de código cambian el eje del esfuerzo**. Un ítem que antes costaba 2 semanas puede costar 4 días de escritura, pero la especificación, la revisión y la verificación no se achican igual. Al estimar conviene separar esas partes (ver [estimación](#t/estimacion)): la que más baja es la escritura, y es justo la que menos domina en ítems riesgosos.

**Por qué importa:** un caso de uso con LLM vistoso y externo puede tener el mejor valor y el peor riesgo. Puntuar las cuatro dimensiones evita lanzarlo primero.

### Trampas comunes de la priorización

- **Falsa precisión:** un RICE de 1.600 contra 1.540 no dice nada. Los números ordenan en grupos, no en posiciones exactas.
- **HiPPO** (*highest paid person's opinion*): la opinión de quien tiene más jerarquía decide, y la herramienta se completa después para justificarla.
- **Ignorar deuda técnica y riesgo:** casi todas las fórmulas premian funcionalidades visibles. Un porcentaje fijo de capacidad (por ejemplo, 20%) para deuda, seguridad y operación evita que nunca entren.
- **Priorizar una vez por trimestre y no volver a mirar:** el valor cambia con lo que se aprende.

**Ejemplo:** la redacción de PII (ítem 2) no aparecía en ningún ranking de RICE del trimestre anterior. Entró recién cuando una auditoría interna encontró teléfonos de destinatarios en los logs, y para entonces ya era urgente.

**Por qué importa:** una herramienta mal usada no solo ordena mal; además le da apariencia objetiva a ese orden.

## Casos prácticos

### El backlog que siempre perdía contra lo urgente

**Situación:** durante tres meses, el equipo de plataforma postergó las alertas basadas en SLO (ítem 8) porque cada semana aparecía algo urgente. Mientras tanto, la guardia recibía 40 alertas semanales, la mayoría no accionables.

**Qué se hace:** se ubica todo el backlog en una matriz de Eisenhower y se mide cuánto tiempo fue a cada cuadrante: 70% a urgente. Se reserva capacidad fija del 25% para "importante y no urgente", protegida en la planificación, y las alertas por SLO entran en el sprint siguiente.

### RICE contra el criterio del equipo

**Situación:** con el RICE de la tabla, el modo oscuro quedó por encima del asistente para transportistas. Producto quiere seguir el número; ingeniería cree que es un error.

**Qué se hace:** se revisan supuestos en lugar de discutir el resultado. El impacto del modo oscuro (0,25) es razonable, pero el alcance de 2.000 comercios supone que todos lo usarían. La confianza del asistente es baja porque nadie probó si el modelo responde bien. Se decide un spike de 3 días con 200 conversaciones reales: si la precisión supera el 85%, la confianza sube al 80% y el asistente pasa adelante. El número sirvió para decidir qué averiguar.

### Elegir el primer caso de uso con agentes

**Situación:** dirección pide "un agente con impacto visible" y propone que el asistente reprograme entregas directamente para los destinatarios.

**Qué se hace:** se puntúan los tres casos de la tabla de casos de uso con LLMs. El de reprogramación tiene el mayor valor, pero escribe en pedidos, lo usan personas externas y no hay casos de evaluación. Se propone empezar por el resumen interno de tickets (un mes, bajo riesgo) y el agente de operaciones en solo lectura, y dejar la reprogramación para el trimestre siguiente con especificación, evaluación y una herramienta con parámetros acotados.

### Usar un LLM para puntuar el backlog

**Situación:** con 120 ítems en el backlog, un ingeniero propone que un LLM complete RICE para todos a partir de la descripción de cada ticket.

**Qué se hace:** se usa el LLM como borrador: propone alcance, impacto y esfuerzo con una justificación de una línea, y marca los tickets sin información suficiente. Las personas revisan los 30 primeros y los que tienen confianza baja, y el product owner firma el orden final. Se detecta que el modelo sobrestima el impacto de todo lo que menciona "IA" en la descripción; queda como sesgo conocido. La responsabilidad de la decisión sigue siendo humana.

## Errores comunes

- **Elegir la herramienta para justificar una decisión ya tomada.** Se fija el criterio antes de puntuar, no después.
- **Mezclar unidades en RICE.** Si un ítem mide alcance en pedidos y otro en comercios, el ranking no vale nada.
- **Dejar la seguridad y la deuda técnica fuera del sistema.** Se les da un carril o una capacidad fija; si compiten contra funcionalidades con RICE, pierden siempre.
- **Tratar empates numéricos como diferencias.** Dentro del margen de error se decide por otros motivos y se dice cuáles.
- **Suponer que los agentes de código bajan el esfuerzo por igual.** Bajan la escritura; la especificación, la revisión y la evaluación siguen costando.
- **Arrancar con el caso de uso de LLM más visible.** Lo externo y con escritura va después de lo interno y de solo lectura.

## Para discutir en equipo

- ¿Qué porcentaje de nuestra capacidad del último mes fue a lo urgente? ¿Es lo que queremos?
- ¿Qué ítem de nuestro backlog actual es un pozo sin fondo que seguimos manteniendo por inercia?
- ¿Cómo hacemos visible el riesgo (PII, deprecaciones, seguridad) en un sistema de priorización pensado para funcionalidades?
- ¿Cuál sería el próximo caso de uso con agentes si aplicamos valor, factibilidad, riesgo y datos?
- ¿Qué partes de priorizar podría preparar un LLM y quién firma la decisión final?
