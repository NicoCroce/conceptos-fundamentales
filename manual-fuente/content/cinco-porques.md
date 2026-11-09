---
slug: cinco-porques
titulo: La técnica de los 5 porqués
resumen: Una técnica para llegar de un síntoma a una causa raíz accionable preguntando por qué en cadena, con evidencia y sin buscar culpables.
lectura: 11
---

## La idea central

Ante un problema, la primera explicación que aparece casi nunca es la de fondo. "El asistente respondió mal porque el modelo se equivocó" es cierto, pero no dice qué cambiar. La técnica de los **5 porqués** consiste en tomar esa primera respuesta y volver a preguntar "¿por qué?", y repetir hasta llegar a una causa que el equipo pueda corregir y que, una vez corregida, evite que el problema vuelva. Nació en la industria automotriz japonesa como parte del trabajo de mejora continua en planta.

Su valor está en la disciplina: cada respuesta es un hecho verificable, la cadena mira procesos y no personas, y hay que saber cuándo parar. En el tema [On-call, runbooks e incidentes](#t/on-call) se ve dónde encaja el análisis dentro del postmortem; acá nos concentramos en cómo hacer bien la cadena.

## Conceptos

### La técnica paso a paso

1. **Escribir el problema con precisión.** Qué pasó, dónde, cuándo y con qué impacto, sin interpretaciones. "El asistente informó como entregado un pedido que no lo estaba, a 14 destinatarios, el martes entre las 10:00 y las 12:30" es mejor que "el asistente anda mal".
2. **Preguntar por qué ocurrió.** La respuesta tiene que explicar directamente el paso anterior, no saltar tres niveles.
3. **Verificar la respuesta.** Antes de seguir, se busca la evidencia: un log, una traza, un diff, una consulta a la base. Si no hay evidencia, la respuesta queda como hipótesis y se investiga.
4. **Repetir** con la nueva respuesta como problema.
5. **Parar** cuando se llega a una causa accionable, que el equipo controla y cuya corrección evitaría la repetición.
6. **Definir acciones** con responsable y fecha.

**Ejemplo:** una cadena bien hecha sobre un incidente del asistente de soporte:

```porques
titulo: El asistente informó entregas que no ocurrieron
problema: 14 destinatarios leyeron «entregado» sin tener su pedido
El asistente leyó el estado de otro pedido
Llamó a buscar_pedido con el teléfono y no con el ID
La herramienta acepta texto libre y busca por coincidencia
El esquema no restringe el parámetro ni valida el formato
No hay casos de eval con identificadores ambiguos
causa: Herramientas sin esquema estricto ni evals que las ejerzan
accion: Parámetro tipado con validación y 20 casos nuevos en el golden set
```

Cada eslabón tiene evidencia: las trazas del agente muestran el parámetro enviado, el código de la herramienta muestra la búsqueda parcial y el golden set no tiene ningún caso donde el destinatario dé un teléfono en lugar del número de pedido.

**Por qué importa:** si el análisis se detenía en el segundo porqué, la acción habría sido "ajustar el prompt para que use el ID", que arregla este caso y deja la puerta abierta a la próxima variante.

### Cinco es una guía, no una regla

El número cinco es orientativo: a veces la causa accionable aparece en el tercer porqué y a veces hacen falta siete. Seguir preguntando por obligación lleva a respuestas cada vez más generales ("porque la empresa crece rápido", "porque el mercado es competitivo") que nadie puede corregir.

**Ejemplo:** en un despliegue que rompió la asignación porque un feature llegó con otro nombre, el tercer porqué ya es "el despliegue no valida el esquema de features contra el que espera el modelo". Es accionable y controlado por el equipo. Un cuarto porqué ("porque nadie lo pidió en el diseño original") no agrega una acción mejor.

**Por qué importa:** fijar el número en cinco invita a rellenar; fijar el criterio de parada invita a pensar.

### Reglas para buenas respuestas

Tres reglas separan una cadena útil de una que solo parece rigurosa:

- **Hechos con evidencia.** "La caché guardó la respuesta 24 horas" se puede verificar; "seguramente fue la caché" no. Si se discute una respuesta, se busca el dato antes de seguir.
- **Procesos, no personas.** Un porqué que termina en una persona ("Ana no revisó") se reformula como pregunta sobre el sistema: ¿qué permitió que un descuido individual llegara a producción? Es el mismo principio del postmortem sin culpas (ver [Postmortem y premortem](#t/postmortem-premortem)).
- **Causalidad directa.** Cada respuesta tiene que explicar el eslabón anterior. Si al leer la cadena de abajo hacia arriba aparece un "y entonces" forzado, falta un paso.

La prueba más simple es leer la cadena al revés con "por lo tanto". Si se lee natural, está bien armada.

**Ejemplo:** esta cadena es típica y está mal:

```porques
titulo: Cadena que termina en error humano
problema: Se borraron 3.000 pedidos de staging compartido
Se ejecutó un script de limpieza en el entorno equivocado
El operador se confundió de entorno
El operador estaba apurado
causa: Error humano
accion: Recordar al equipo que tenga más cuidado
```

La versión corregida pregunta por el sistema en cada paso:

```porques
titulo: La misma cadena, corregida
problema: Se borraron 3.000 pedidos de staging compartido
Se ejecutó un script de limpieza en el entorno equivocado
El script toma el entorno de una variable ya cargada
La terminal no muestra en qué entorno se está
El script no pide confirmación ni muestra cuántas filas borra
causa: Scripts destructivos sin confirmación ni señal de entorno
accion: Confirmación con conteo y entorno visible en la terminal
```

**Por qué importa:** "error humano" no es una causa, es el punto donde se dejó de preguntar. La acción "tener más cuidado" no cambia nada, y la próxima persona apurada va a cometer el mismo error.

### Cuando hay más de una causa: ramificar

El defecto más citado de los 5 porqués es que sugiere una única cadena lineal, y los problemas reales suelen tener varias causas que se combinan. Un incidente puede necesitar a la vez un cambio defectuoso, una prueba ausente y una alerta que no sonó. Si en algún paso hay dos respuestas verdaderas, se abren dos ramas y se sigue cada una por separado.

**Ejemplo:** "¿por qué el problema duró 2 horas y no 10 minutos?" tiene dos respuestas independientes: la alerta mide entregas a tiempo y no respuestas del asistente, y el rollback del prompt no estaba documentado. Cada rama lleva a su propia acción.

**Por qué importa:** forzar una sola cadena hace que el equipo elija la causa más cómoda y deje sin tratar las demás.

### El diagrama de Ishikawa para problemas con muchas causas

Cuando las ramas se multiplican, o cuando el problema es crónico y no un incidente puntual, conviene cambiar de herramienta. El **diagrama de Ishikawa** (también llamado diagrama de espina de pescado o de causa y efecto) ordena las causas posibles en categorías antes de profundizar. La versión clásica de manufactura usa seis categorías, que en software se traducen así:

- **Método:** procesos, revisiones, pasos de despliegue.
- **Máquina:** infraestructura, servicios, herramientas, modelos.
- **Mano de obra:** conocimiento, carga, guardias, traspasos (siempre como condición del sistema, no como culpa).
- **Materiales:** datos de entrada, features, documentos del RAG.
- **Medición:** métricas, alertas, evals.
- **Medio ambiente:** proveedores externos, tráfico, estacionalidad.

**Ejemplo:** el asistente da respuestas desactualizadas sobre políticas de devolución, de forma intermitente desde hace semanas:

```arbol
titulo: Ishikawa: respuestas desactualizadas
Respuestas con políticas viejas
- Método
-- Cambios de política sin aviso al equipo
- Máquina
-- Índice vectorial que no borra versiones viejas
- Mano de obra
-- Nadie es dueño del corpus del RAG
- Materiales
-- PDFs duplicados con fechas distintas
- Medición
-- Ninguna eval mira la fecha de la política
- Medio ambiente
-- Cambios de política frecuentes en temporada alta
```

Después, sobre las dos o tres causas más probables, se aplica una cadena de porqués para llegar al fondo de cada una (ver [RAG](#t/rag) para el problema de documentos duplicados en el índice).

**Por qué importa:** Ishikawa amplía la búsqueda antes de profundizar; los 5 porqués profundizan una línea. Juntos evitan tanto la visión de túnel como la lista infinita de sospechosos.

### De la causa raíz a las acciones

Una cadena sin acciones es un ejercicio académico. Cada causa raíz se convierte en una o más acciones con estas características:

| Atributo | Qué significa | Ejemplo |
|---|---|---|
| Concreta | Se sabe cuándo está terminada | "Parámetro `pedido_id` con patrón validado" |
| Con responsable | Una persona, no un equipo | Lucía (equipo del asistente) |
| Con fecha | Plazo explícito | 20 de noviembre |
| Con tipo | Prevenir, detectar o mitigar | Prevenir |
| Verificable | Cómo se comprueba que funcionó | Los 20 casos nuevos pasan en CI |

Conviene tener al menos una acción de **prevención** (que no vuelva a pasar) y una de **detección** (si vuelve a pasar, enterarse antes). Las acciones van a la herramienta de seguimiento, no se quedan en el documento.

**Ejemplo:** del incidente de las entregas mal informadas salen tres acciones: tipar y validar el parámetro `pedido_id` (prevenir, Lucía, 20 de noviembre); agregar 20 casos con identificadores ambiguos al golden set (detectar, Tomás, 27 de noviembre); y una alerta cuando la herramienta devuelve más de un pedido para una misma consulta (detectar, Lucía, 4 de diciembre). Las tres se revisan en la reunión semanal hasta cerrarse.

**Por qué importa:** los análisis de causa raíz se desacreditan solos cuando las mismas causas aparecen en tres postmortems seguidos porque las acciones nunca se hicieron.

### Los 5 porqués en incidentes de agentes

Los incidentes con agentes tienen una particularidad: la primera respuesta casi siempre es "el modelo se equivocó", y es la menos útil. Un modelo probabilístico se va a equivocar a veces; la pregunta productiva es por qué ese error llegó a tener efecto. La cadena típica baja por estas capas: la acción incorrecta, la llamada a herramienta que la produjo, lo que el prompt o el contexto le indicaban, la restricción que faltaba en la herramienta y la eval que no lo detectó (ver [Agentes y tool calling](#t/agentes)).

Un LLM puede ayudar: con las trazas, los logs y la línea de tiempo, propone porqués candidatos y, para cada uno, qué evidencia lo confirmaría. Las personas verifican esa evidencia antes de aceptar cada eslabón. El modelo sugiere hipótesis útiles, pero no es fuente de verdad y tiende a producir cadenas plausibles aunque falten datos.

Lo mismo vale al depurar con un agente de código: preguntarle "¿por qué falla este test?" y, ante su respuesta, volver a preguntar "¿por qué pasa eso?" lo obliga a leer más código y a separar el síntoma de la causa, en lugar de proponer el parche más cercano.

**Ejemplo:** ante un test que falla de forma intermitente, el agente propone primero aumentar un timeout. Al preguntarle por qué el test tarda, encuentra que espera un evento de Kafka; al preguntar por qué el evento se demora, ve que el consumidor de prueba arranca después del productor. La corrección es ordenar el arranque, no subir el timeout.

**Por qué importa:** tanto con personas como con agentes, la primera explicación suele ser la más cercana al síntoma. Preguntar otra vez es barato y cambia la calidad de la solución.

## Casos prácticos

### El agente de operaciones que recomendó escalar sin motivo

**Situación:** el agente interno de operaciones, al investigar una alerta de la zona norte, recomendó declarar SEV1 y escalar a dirección. Era un falso positivo: la caída de entregas a tiempo era un feriado regional.

**Qué se hace:** se arma la cadena con las trazas. El agente comparó contra el mismo día de la semana anterior; porque su herramienta de métricas no tiene un parámetro de calendario; porque los feriados regionales viven en una planilla y no en un servicio; porque nunca se agregó un caso de eval con feriados. Causa accionable: la herramienta no expone el calendario operativo. Acciones: endpoint de calendario consultable por el agente (prevenir) y tres casos de eval con feriados (detectar). Nadie propone "cambiar de modelo", porque la evidencia muestra que el modelo razonó bien con datos incompletos.

### Una cadena que se trabó en la discusión

**Situación:** al tercer porqué, una persona dice que el índice no se actualizó y otra que el documento nuevo nunca se cargó.

**Qué se hace:** se deja de debatir y se busca evidencia. El log de ingesta muestra que el documento se cargó, y el índice tiene dos versiones del mismo documento. Las dos respuestas eran parcialmente ciertas; se abren dos ramas y se cierra la discusión con datos en 15 minutos.

### Usar un LLM para proponer porqués

**Situación:** un incidente de 3 horas dejó 40.000 líneas de logs y 200 trazas. El equipo propone que un LLM escriba el análisis.

**Qué se hace:** se le pide al modelo una lista de porqués candidatos, cada uno con el log o la traza que lo respaldaría. Propone seis. Al verificar, cuatro tienen evidencia, uno es una correlación sin causa (dos errores que coinciden en hora) y otro cita una línea de log que no existe. La cadena final la arma el equipo con los cuatro verificados. Queda como práctica: todo porqué propuesto por un modelo se acepta solo con evidencia enlazada.

## Errores comunes

- **Terminar en "error humano".** Se reformula como pregunta sobre el sistema: qué permitió que el error tuviera efecto.
- **Aceptar respuestas sin evidencia.** Cada eslabón necesita un log, una traza o un dato; si no lo hay, queda como hipótesis.
- **Forzar una cadena única.** Si hay dos causas verdaderas, se abren dos ramas; si hay muchas, se pasa a un diagrama de Ishikawa.
- **Seguir preguntando hasta lo incontrolable.** Se para en la primera causa que el equipo controla y cuya corrección evita la repetición.
- **Quedarse en "el modelo se equivocó".** En incidentes con agentes se sigue hacia la herramienta, el contexto y la eval que faltaba.
- **Acciones sin responsable ni fecha.** Cada causa raíz termina en acciones concretas, verificables y registradas.

## Para discutir en equipo

- Tomemos nuestro último postmortem: ¿la cadena de causas termina en algo que controlamos y que evita la repetición?
- ¿Qué evidencia nos falta guardar hoy (trazas de agentes, parámetros de herramientas, versiones de prompt) para poder armar una cadena con hechos?
- ¿Cuándo preferimos un diagrama de Ishikawa y cuándo una cadena de porqués?
- ¿Qué reglas pondríamos para usar un LLM como asistente de análisis sin que su relato reemplace la evidencia?
- ¿Qué causa raíz apareció en más de un incidente este año, y por qué sus acciones no alcanzaron?
