---
slug: contexto-memoria
titulo: Contexto y memoria de agentes
resumen: Cómo decidir qué información entra en cada llamada de un agente y qué se recuerda entre tareas, para controlar calidad, costo y riesgo.
lectura: 15
---

## La idea central

Un modelo no tiene estado: en cada llamada solo sabe lo que viaja en su contexto (ver [Fundamentos de LLMs](#t/fundamentos-llms)). En un agente, ese contexto se arma de nuevo en cada paso del bucle con instrucciones, herramientas, historial y resultados. Por eso, cuando un agente funciona mal, la causa más frecuente no es el modelo sino lo que le mandamos: demasiado, en desorden, viejo o contradictorio. A ese trabajo de decidir qué entra, en qué forma y en qué orden se le llama **ingeniería de contexto**, y es la tarea principal al construir agentes.

Una analogía: el contexto es la mesa de trabajo de un analista. Puede ser enorme, pero si se le apilan encima trescientas páginas de logs, el analista pierde de vista la nota con la consigna. La **memoria de largo plazo**, en cambio, es el archivo del fondo de la oficina: no está sobre la mesa, se va a buscar cuando hace falta y alguien tiene que mantenerlo ordenado, depurado y bajo llave.

## Conceptos

### Anatomía del contexto de un agente

En cada paso, el contexto que recibe el modelo tiene estas piezas:

1. **System prompt:** rol, reglas y formato de salida. Fijo entre pasos.
2. **Definiciones de herramientas:** nombre, descripción y esquema de cada una. Fijas.
3. **Tarea:** la alerta o la pregunta del usuario.
4. **Historial:** lo que el modelo pidió en cada paso y su razonamiento breve.
5. **Resultados de herramientas:** lo que devolvieron las consultas. Suele ser lo que más crece.
6. **Documentos recuperados y memorias:** fragmentos traídos por búsqueda (ver [RAG](#t/rag)).
7. **Scratchpad o notas:** un resumen del plan y de lo ya averiguado, que el propio agente mantiene.

**Ejemplo:** el agente de operaciones de Rumbo investiga "cayó la tasa de entregas a tiempo en la zona norte" con un modelo de ventana de 200.000 tokens. Después de 15 llamadas a herramientas, el contexto queda así (cifras ilustrativas):

| Pieza | Tokens | % de la ventana |
|---|---|---|
| System prompt | 2.500 | 1,3 % |
| 12 definiciones de herramientas (400 c/u) | 4.800 | 2,4 % |
| Alerta | 500 | 0,3 % |
| Razonamiento y pedidos del modelo (15 × 300) | 4.500 | 2,3 % |
| Resultados de herramientas (15 × 6.000, muchos son logs) | 90.000 | 45 % |
| **Total** | **102.300** | **51 %** |

Entra con holgura. Pero el problema está en el costo acumulado: cada paso reenvía todo lo anterior. La entrada de la llamada número k es aproximadamente 7.800 + (k − 1) × 6.300 tokens. Sumando las 16 llamadas (15 pasos con herramienta más la respuesta final):

- Parte fija: 16 × 7.800 = 124.800 tokens.
- Parte creciente: 6.300 × (0 + 1 + ... + 15) = 6.300 × 120 = 756.000 tokens.
- Total de entrada: unos **880.800 tokens** por investigación. A un precio hipotético de USD 3 por millón, unos USD 2,64 solo de entrada.

Si cada resultado se resume a 600 tokens antes de entrar al contexto, el incremento por paso baja a 900 y el total queda en 124.800 + 900 × 120 = 232.800 tokens, unos USD 0,70. **Casi cuatro veces menos**, con la misma cantidad de pasos.

**Por qué importa:** el costo de un agente crece aproximadamente con el cuadrado de los pasos cuando los resultados se acumulan sin recortar. La pieza que más conviene vigilar casi nunca es el system prompt, sino los resultados de herramientas.

### "Entra" no es lo mismo que "funciona"

Un contexto largo degrada la calidad aunque quepa en la ventana. Tres mecanismos:

- **Perdido en el medio (lost in the middle):** la información ubicada en el centro de un contexto largo se aprovecha peor que la del principio o el final. Un dato clave en el paso 7 de 15 puede pasar desapercibido.
- **Distracción por ruido:** 6.000 tokens de logs donde lo relevante son dos líneas compiten por la atención del modelo. Aparecen conclusiones basadas en un error irrelevante que se repetía mucho.
- **Deriva de instrucciones:** las reglas del system prompt pierden peso a medida que crece el historial. El agente empieza a saltear el formato pedido o a sugerir acciones que las reglas prohibían.

**Ejemplo (cifras hipotéticas):** en una evaluación interna con 80 alertas históricas, el agente acierta la causa en el 86 % de los casos cuando el contexto final queda por debajo de 30.000 tokens, y en el 68 % cuando supera 100.000. Mismo modelo, mismas herramientas; cambia solo cuánto ruido acumuló.

**Por qué importa:** una ventana grande es un límite, no un objetivo. Diseñar para "lo mínimo suficiente" mejora calidad, costo y latencia a la vez.

### Recortar y resumir resultados antes de que entren

La técnica de mayor impacto es tratar la salida de cada herramienta antes de agregarla al historial:

1. **Recortar en la herramienta:** devolver solo los campos útiles, con límites (por ejemplo, máximo 50 filas y un aviso "hay 1.240 más; filtra por transportista").
2. **Agregar en código:** en vez de 3.000 líneas de log, devolver conteos por tipo de error y tres ejemplos de cada uno.
3. **Resumir con un modelo chico:** para salidas no estructuradas, una llamada barata que extrae lo relevante para la tarea en curso.
4. **Guardar el original fuera del contexto:** el resultado completo queda en almacenamiento con un identificador, y el agente puede pedirlo si de verdad lo necesita.

```text
[result] buscar_logs(servicio="asignacion", nivel="error", desde="15:30")
         3.112 líneas resumidas | ref: logs-ops-7f3a-04
         - "timeout calling eta-model": 2.890 (93%), desde 15:44
         - "carrier capacity exceeded": 201, desde 15:46
         - otros 4 tipos: 21 en total
         Ejemplos: [3 líneas por tipo]
```

### Compactación del historial

Cuando el contexto supera un umbral (por ejemplo, el 60 % de la ventana o 80.000 tokens), se **compacta**: una llamada resume los pasos viejos en un bloque breve (hipótesis vigentes, evidencia confirmada, caminos descartados, pendientes) y se conservan textuales solo los últimos pasos.

**Ejemplo:** 100.000 tokens de historial se reemplazan por un resumen de 3.000 tokens más los últimos 3 pasos completos (unos 6.000). El agente sigue con 17.000 tokens de contexto en vez de 107.000.

El riesgo es perder un detalle clave; por eso el resumen sigue una plantilla fija y conserva los identificadores de los resultados originales.

### Notas estructuradas y scratchpad

En lugar de depender del historial, el agente mantiene un archivo de notas que actualiza con una herramienta (`actualizar_notas`), por ejemplo:

```text
OBJETIVO: causa de la caída en zona norte desde las 16h
CONFIRMADO: caída 93% -> 76%; 3 transportistas concentran 70% de demoras
HIPÓTESIS: deploy asignacion v2.31.0 (15:42) -> concentración por cercanía
DESCARTADO: clima (sin lluvia), volumen (dentro de lo habitual)
PENDIENTE: comparar carga antes/después del deploy
```

Las notas sobreviven a la compactación, ocupan unos cientos de tokens y se ubican al final del contexto, donde el modelo las aprovecha mejor. Es la forma más barata de evitar la deriva en tareas de muchos pasos.

### Recuperar justo a tiempo en vez de precargar

**Precargar** es meter en el contexto inicial todo lo que podría servir: runbooks, lista de transportistas, incidentes pasados. **Recuperar justo a tiempo** (just-in-time) es darle al agente herramientas para traer cada cosa cuando la necesita: `buscar_runbook(tema)`, `obtener_transportista(id)`.

Precargar conviene si el material es chico, estable y se usa casi siempre; recuperar a demanda, si es grande o solo una parte aplica a cada caso. Lo habitual es combinar: un índice breve precargado ("existen estos 10 runbooks, sobre estos temas") y el contenido a demanda.

### Subagentes con contexto propio

El patrón completo, con sus costos y variantes, está en [Subagentes y sistemas multiagente](#t/subagentes).

Un **subagente** recibe una subtarea acotada, trabaja con su propio contexto limpio y devuelve solo un resumen. **Ejemplo:** el agente de operaciones delega "analizar los logs del servicio de asignación entre 15:30 y 17:00 y reportar errores nuevos" a un subagente. Este hace 8 consultas, acumula 45.000 tokens y devuelve un informe de 500. El contexto del principal crece 500 tokens, no 45.000.

El costo total no desaparece (el subagente también consume), pero se aísla el ruido y las subtareas independientes pueden correr en paralelo. Vale la advertencia de [Agentes y tool calling](#t/agentes): más agentes implican más llamadas y más puntos de falla.

### Menos herramientas, mejor descritas

Cada definición de herramienta ocupa tokens en todas las llamadas y es una opción más entre las que el modelo tiene que elegir. Con 40 herramientas de 400 tokens se gastan 16.000 tokens fijos por paso y aumentan los errores de elección entre herramientas parecidas.

Conviene ofrecer solo las herramientas de la tarea, fusionar las casi iguales con un parámetro y escribir descripciones precisas pero cortas.

### Prompt caching

Muchos proveedores permiten cachear el **prefijo** del contexto: si una llamada empieza exactamente igual que una anterior reciente, esos tokens se procesan más rápido y se facturan a un precio menor. En un agente esto rinde mucho, porque cada paso repite todo lo anterior y solo agrega al final.

Reglas para aprovecharlo:

1. **Lo estable primero:** system prompt, herramientas, documentos fijos; después la tarea; después el historial, que solo crece por el final.
2. **Nada variable en el prefijo:** una fecha con segundos, un identificador de petición o memorias del usuario dentro del system prompt invalidan todo lo que viene después.
3. **No reordenar ni editar el pasado:** cambiar el orden de las herramientas, editar un mensaje viejo o compactar el historial rompe la caché desde ese punto.
4. **Tener en cuenta la expiración:** la caché dura minutos (según el proveedor); un agente que espera una aprobación humana durante horas la pierde.

**Ejemplo (precios hipotéticos):** lectura de caché al 10 % del precio base (USD 0,30 por millón) y escritura al 125 % (USD 3,75 por millón). En la investigación de 16 llamadas de antes, cada llamada lee de caché todo lo que envió la anterior y escribe solo lo nuevo:

- Leído de caché: unos 778.500 tokens × 0,30 / 1.000.000 = USD 0,23.
- Escrito: 7.800 + 15 × 6.300 = 102.300 tokens × 3,75 / 1.000.000 = USD 0,38.
- Total: unos **USD 0,62** frente a USD 2,64 sin caché, alrededor de un 77 % menos. El tiempo al primer token también baja en pasos con prefijos largos.

Caché y compactación tiran en direcciones opuestas: compactar seguido rompe la caché. Conviene compactar pocas veces y con umbrales altos.

### Comparación de técnicas

| Técnica | Qué resuelve | Cuándo usarla | Costo o riesgo |
|---|---|---|---|
| Recortar y resumir resultados | Ruido y crecimiento por herramientas verbosas | Siempre que una herramienta devuelva más de unos miles de tokens | Perder un detalle; mitigar guardando el original |
| Compactación del historial | Tareas largas que se acercan al límite | Más de 20 o 30 pasos, o umbral de tokens | Pérdida de información; rompe la caché |
| Notas estructuradas | Deriva y olvido del objetivo | Tareas de muchos pasos | Notas desactualizadas si no se mantienen |
| Recuperación justo a tiempo | Precarga de material que no se usa | Corpus grande o casos variados | Un paso extra por consulta |
| Subagentes | Subtareas ruidosas o paralelizables | Subtareas independientes y voluminosas | Más llamadas y coordinación |
| Menos herramientas | Tokens fijos y errores de elección | Más de 10 o 15 herramientas | Ninguno relevante |
| Prompt caching | Costo y latencia del prefijo repetido | Siempre que haya prefijo estable | Diseño cuidadoso del orden |

### Memoria de largo plazo: qué se guarda

La memoria de largo plazo persiste entre tareas y conversaciones. Tres tipos útiles:

- **Preferencias:** "el comercio Librería Sur prefiere que lo contacten por correo, no por teléfono".
- **Hechos:** "el depósito del comercio X cierra a las 18h; el retiro tiene que ser antes".
- **Episodios:** registros de tareas pasadas: "alerta zona norte, 12/03: causa, deploy de asignación; resolución, rollback".

**Cómo se escribe.** Hay dos caminos. **Explícito:** el usuario o el agente lo pide ("recuerda que...") con una herramienta `guardar_memoria`. **Automático:** al cerrar una conversación, un proceso extrae candidatos. El automático captura más, pero también más basura y más errores; conviene exigir que cada memoria tenga fuente (qué conversación, quién lo dijo), confianza y fecha, y empezar por lo explícito.

**Cómo se lee.** Al inicio de una tarea se recuperan pocas memorias relevantes, combinando tres señales:

- **Similitud:** cercanía semántica con la tarea, con embeddings.
- **Recencia:** decae con el tiempo, por ejemplo a la mitad cada 30 días.
- **Importancia:** asignada al guardar (una restricción operativa pesa más que un comentario).

**Ejemplo:** con puntaje = 0,6 × similitud + 0,25 × recencia + 0,15 × importancia, una memoria con similitud 0,82, de hace 60 días (recencia 0,25) e importancia 0,9 obtiene 0,492 + 0,063 + 0,135 = 0,69. Otra con similitud 0,78, de ayer (recencia 0,98) e importancia 0,3 obtiene 0,468 + 0,245 + 0,045 = 0,76 y queda primera. Los pesos se ajustan con evaluaciones, no a ojo.

**Dónde se guarda.** Según el tipo:

| Almacenamiento | Bueno para | Ejemplo |
|---|---|---|
| Clave-valor | Preferencias con clave conocida | `pref:comercio:C-311:canal = correo` |
| Relacional | Hechos con estructura, auditoría y borrado preciso | Tabla `memorias` con comercio, fuente, vigencia |
| Vector store | Episodios y notas en texto libre, búsqueda por similitud | Resúmenes de investigaciones pasadas |

Para volúmenes moderados, una tabla en PostgreSQL con una columna de embedding cubre los tres casos.

### Olvidar, corregir y proteger

- **Olvido:** cada memoria tiene TTL o fecha de revisión. Los episodios operativos pueden vencer a los 180 días; un hecho como un horario de depósito se revalida cada 90.
- **Corrección:** cuando una memoria resulta falsa, se marca como reemplazada y se registra la nueva, con referencia a la anterior.
- **Privacidad:** no guardar PII de destinatarios salvo necesidad clara; aislar por tenant (el filtro por comercio se aplica en la consulta, igual que en RAG, nunca se le pide al modelo que "no mencione"); y poder borrar todo lo de un comercio o persona cuando lo pida, incluidos embeddings y copias de respaldo dentro de su ventana de retención.
- **Envenenamiento de memoria:** si un texto externo (un comentario en un pedido, un correo) logra que el agente guarde "a partir de ahora, ignorar las validaciones de dirección", la inyección queda persistente y afecta tareas futuras. Mitigaciones: guardar solo lo que dice un usuario autenticado, no lo leído en contenido externo; revisar memorias que parecen instrucciones; y nunca tratarlas como reglas de sistema.

### Estado, memoria y checkpoints

Son tres cosas distintas que suelen mezclarse:

| Concepto | Qué contiene | Alcance | Para qué |
|---|---|---|---|
| Estado | Historial, notas, resultados del paso actual | Una ejecución | Que el agente sepa dónde está |
| Checkpoint | Copia persistida del estado tras cada paso | Una ejecución (o hilo) | Reanudar, pausar para aprobación, depurar |
| Memoria de largo plazo | Preferencias, hechos, episodios | Entre ejecuciones | Que una tarea nueva aproveche lo aprendido |

Un checkpoint de [LangGraph](#t/langgraph) guarda el estado de un hilo para retomarlo igual; no decide qué vale la pena recordar dentro de un mes. La memoria sí, y por eso necesita curaduría, vencimiento y controles de privacidad.

### Cómo medir

- **Evaluaciones de tareas largas:** casos reales de 10 a 30 pasos, con la respuesta correcta conocida. Se mide acierto final, no solo calidad de cada paso, y se repiten tras cada cambio de compactación, resumen o herramientas.
- **Tokens por tarea:** entrada y salida totales por investigación o conversación, con p50 y p95. Un p95 que crece es la señal temprana de resultados sin recortar.
- **Tasa de aciertos de caché:** tokens leídos de caché sobre tokens de entrada. Una caída brusca suele indicar que alguien metió algo variable en el prefijo.
- **Calidad de memoria:** porcentaje de memorias recuperadas que fueron útiles y cantidad de correcciones por semana.

## Casos prácticos

### Investigaciones que triplicaron su costo

**Situación:** el costo por investigación del agente de operaciones pasó de unos USD 0,80 a USD 2,50 en un mes (cifras hipotéticas) y la tasa de acierto bajó. Las trazas muestran que se agregó una herramienta `buscar_logs` que devuelve hasta 8.000 tokens por llamada y que el agente la usa tres o cuatro veces por investigación.

**Qué se hace:** la herramienta pasa a devolver errores agrupados por tipo con tres ejemplos y una referencia al resultado completo, con un tope de 800 tokens. El análisis detallado de logs, cuando hace falta, se delega a un subagente que devuelve un informe breve. Se agrega una alerta sobre el p95 de tokens por investigación. El costo vuelve a niveles previos y el acierto sube, porque desaparece el ruido.

### Preferencias de cada comercio en el asistente de soporte

**Situación:** los comercios repiten en cada conversación lo mismo: "no nos llamen, escriban por correo", "el depósito cierra a las 18". Se pide que el asistente lo recuerde.

**Qué se hace:** una tabla de memorias en PostgreSQL con `comercio_id`, tipo, texto, fuente, fecha y vencimiento. Solo se guardan preferencias y hechos operativos cuando el usuario autenticado del comercio los confirma ("¿quieres que lo recuerde para próximas consultas?"); nada de datos de destinatarios. La consulta filtra por el `comercio_id` de la sesión, nunca por lo que diga el texto. Las memorias se inyectan al final del contexto, después del prefijo cacheable. El comercio puede ver y borrar sus memorias desde el panel, y el borrado elimina también los embeddings.

### Reordenar el prompt para aprovechar la caché

**Situación:** el asistente de soporte tiene un prefijo fijo de 9.000 tokens (instrucciones, políticas resumidas, herramientas), pero la tasa de aciertos de caché es casi cero y el tiempo al primer token ronda los 2,5 segundos.

**Qué se hace:** al revisar el prompt aparece que la primera línea es "Fecha y hora actual: 14:32:07" y que las memorias del comercio se insertan dentro del system prompt. Se mueve la fecha (con precisión de día) y las memorias al final, después del prefijo estable, y se fija el orden de las herramientas. La tasa de aciertos sube por encima del 80 % y el tiempo al primer token baja a menos de un segundo (valores hipotéticos), sin cambiar el modelo.

### Una memoria equivocada que se repetía

**Situación:** el asistente responde una y otra vez a un comercio que "los retiros solo se hacen por la mañana". Era cierto hace cuatro meses; el comercio cambió el horario y lo dijo en una conversación, pero la memoria vieja seguía ganando por importancia alta.

**Qué se hace:** se agrega el ciclo de corrección: cuando una conversación contradice una memoria, el sistema propone reemplazarla y el comercio lo confirma; la vieja queda marcada como reemplazada, no borrada, para auditoría. Los hechos operativos pasan a tener revalidación cada 90 días y, al recuperar memorias, se incluye su fecha para que el modelo pueda decir "según lo registrado en marzo". Se suma un caso de evaluación con memorias contradictorias.

## Errores comunes

- **Confundir capacidad de ventana con calidad.** Que el contexto entre en 200.000 tokens no significa que el modelo use bien lo que está en el medio; se diseña para el mínimo suficiente.
- **Agregar resultados de herramientas tal como llegan.** La salida cruda de logs o consultas es la causa principal de costo y distracción; se recorta, agrega o resume antes de entrar.
- **Romper la caché sin darse cuenta.** Un timestamp, un identificador o memorias dentro del prefijo anulan el ahorro; se monitorea la tasa de aciertos.
- **Guardar memorias automáticamente sin fuente ni vencimiento.** Termina en una base de hechos viejos o falsos que nadie puede corregir; cada memoria lleva origen, fecha y TTL.
- **Aislar tenants con instrucciones al modelo.** El filtro por comercio va en la consulta al almacenamiento, no en el prompt.
- **Tratar checkpoints como memoria.** Un checkpoint reanuda una ejecución; no sustituye una memoria curada ni sus controles de privacidad.

## Para discutir en equipo

- En nuestro agente de operaciones, ¿qué porcentaje del contexto final son resultados de herramientas, y cuáles de ellas deberían devolver menos?
- ¿Qué umbral de compactación usaríamos y cómo verificaríamos que no perdemos información clave?
- ¿Qué cosas vale la pena que el asistente de soporte recuerde de un comercio, y cuáles no deberíamos guardar nunca?
- ¿Cómo detectaríamos que una memoria fue escrita a partir de una inyección en contenido externo?
- ¿Qué métricas de contexto y caché agregaríamos al panel de costo por funcionalidad?
