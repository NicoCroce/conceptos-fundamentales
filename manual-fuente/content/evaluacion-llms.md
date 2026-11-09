---
slug: evaluacion-llms
titulo: Evaluación de LLMs
resumen: Cómo medir de forma sistemática si una funcionalidad con LLM funciona bien, detectar regresiones y decidir cambios de prompt o de modelo con datos.
lectura: 13
---

## La idea central

Con código tradicional, un test dice "esta función, con esta entrada, devuelve exactamente esto". Con un LLM eso no alcanza: la misma entrada puede dar respuestas distintas, muchas respuestas distintas pueden ser correctas, y un cambio mínimo en el prompt puede mejorar diez casos y romper otros tres sin que nadie lo note. Las **evals** (evaluaciones) son el equivalente a los tests para funcionalidades con LLM: un conjunto de casos representativos, una forma de puntuar cada respuesta y un número agregado que se compara entre versiones.

La idea de fondo es simple: **no se cambia un prompt, un modelo o un parámetro sin correr las evals antes**, igual que no se hace merge de código sin correr los tests. Sin evals, cada decisión ("¿este modelo más barato alcanza?", "¿este prompt nuevo es mejor?") se toma mirando cinco ejemplos a mano, y eso es intuición, no medición.

## Conceptos

### Las evals como tests

Una eval tiene tres partes:

1. **Casos:** entradas (y, cuando existe, la salida esperada o los criterios de una buena respuesta).
2. **Evaluador:** la forma de puntuar cada salida. Puede ser código ("¿el JSON es válido y la categoría coincide?"), otro LLM que juzga con una rúbrica, o una persona.
3. **Métrica agregada:** exactitud, tasa de éxito, puntaje promedio, latencia, costo. Es lo que se compara entre la versión actual y la candidata.

Las evals se corren en dos momentos: durante el desarrollo (para iterar sobre un prompt) y en CI (para detectar regresiones antes del merge).

**Por qué importa:** convierte discusiones subjetivas ("me parece que responde mejor") en comparaciones con números sobre los mismos casos.

### Golden set

El **golden set** es el conjunto de casos de referencia, con la respuesta correcta o los criterios acordados. Recomendaciones:

- **Tamaño:** entre 50 y 500 casos. Menos de 50 deja mucho ruido: con 40 casos, un caso más o menos mueve la exactitud 2,5 puntos. Más de 500 suele ser caro de mantener y etiquetar sin ganar mucha señal adicional, salvo que haya muchas categorías.
- **Origen:** casos **reales** de producción (anonimizados), no inventados. Los casos inventados tienden a ser más limpios y fáciles que la realidad.
- **Composición:** una mezcla de casos **frecuentes** (lo que pasa todos los días) y casos **difíciles** (ambiguos, raros, con errores de ortografía, en el borde entre dos categorías).
- **Crecimiento:** cada error que aparece en producción se agrega como caso nuevo, con su respuesta correcta. Así el golden set aprende de los incidentes y la misma falla no vuelve sin que lo detectemos.

**Ejemplo:** para el clasificador de tickets de Rumbo, un golden set de 300 tickets: 200 tomados al azar de los últimos tres meses (proporción real de categorías), 70 elegidos por ser difíciles y 30 que vienen de errores reportados.

### Evaluación offline y online

- **Offline:** se corre la funcionalidad sobre el golden set antes de desplegar. Es barata, repetible y rápida, pero solo mide lo que el golden set cubre.
- **Online:** se mide con tráfico real después de desplegar. Tres formas habituales:
  - **A/B:** una fracción de usuarios recibe la versión nueva, el resto la actual; se comparan métricas de negocio (resolución, aceptación, tiempo).
  - **Modo sombra:** la versión nueva procesa el tráfico real en paralelo, pero sus respuestas no se muestran; se comparan offline con las de la versión actual. No tiene riesgo para el usuario.
  - **Feedback:** señales explícitas (pulgar arriba o abajo, "esta respuesta me sirvió") o implícitas (el agente humano edita mucho el borrador sugerido, el usuario repregunta lo mismo).

Las dos se complementan: offline para no desplegar algo roto, online para confirmar que lo que mejoró en el laboratorio también mejora en la realidad.

### Métricas según la tarea

No hay una métrica universal. Depende de qué hace la funcionalidad:

- **Clasificación** (por ejemplo, categoría de ticket):
  - **Exactitud:** porcentaje de casos con la categoría correcta.
  - **Precision** de una categoría: de los que el modelo marcó como "reclamo urgente", qué porcentaje realmente lo era.
  - **Recall** de una categoría: de todos los reclamos urgentes reales, qué porcentaje detectó el modelo.
  Si hay 30 urgentes reales y el modelo marca 25 como urgentes, de los cuales 20 lo son: precision = 20/25 = 80%, recall = 20/30 = 67%. La exactitud global puede verse bien mientras el recall de la categoría crítica es malo.
- **RAG** (asistente sobre manuales y políticas, ver [RAG](#t/rag)):
  - **Fidelidad:** la respuesta se apoya en los documentos recuperados y no agrega afirmaciones inventadas.
  - **Relevancia:** la respuesta contesta lo que se preguntó, y los documentos recuperados son los adecuados.
- **Agentes:**
  - **Tasa de éxito:** porcentaje de tareas que terminan con el resultado correcto.
  - **Pasos:** cuántas llamadas a herramientas usó; más pasos implica más costo, latencia y riesgo.
- **Siempre:** **latencia** (p50 y p95) y **costo** por caso. Un prompt que mejora un punto de exactitud pero duplica el costo es una decisión de negocio, no una mejora automática.

### Regresiones que bloquean el merge

Las evals se integran en CI como cualquier test: cada cambio de prompt, modelo, parámetros o dependencias corre el golden set y compara contra la versión en producción. Se definen umbrales:

- Bloquea el merge si la exactitud cae más de 1 punto, si el recall de categorías críticas cae, o si aparecen errores de formato.
- Avisa (sin bloquear) si la latencia p95 o el costo por caso suben más de un 20%.

Los umbrales los acuerda el equipo con el dueño de producto y se revisan cuando cambia el contexto.

### No determinismo: correr varias veces

Los LLMs pueden dar respuestas distintas para la misma entrada, incluso con temperatura baja. Si se corre el golden set una vez y la versión nueva saca 92% contra 91% de la actual, la diferencia puede ser ruido.

La práctica es **correr cada eval varias veces** (por ejemplo, 3 a 5) y mirar el promedio y la dispersión. Si la versión actual da 91%, 92% y 90%, y la nueva da 92%, 93% y 91%, la mejora es pequeña y poco segura. Si la nueva da 95%, 95% y 96%, la mejora es clara. También conviene mirar los casos que cambian de resultado entre corridas: suelen ser los ambiguos, y vale la pena revisarlos.

### Evaluar la trayectoria de agentes

En un [agente](#t/agentes), la respuesta final puede ser correcta por casualidad o después de pasos innecesarios o riesgosos. Evaluar la **trayectoria** es mirar el camino, no solo el destino:

- ¿Usó las herramientas esperadas? Para "investigar caída de entregas en zona norte", se espera que consulte la métrica antes de buscar causas.
- ¿Cuántos pasos dio? Si el caso típico se resuelve en 5 y dio 14, hay un problema.
- ¿Intentó algo prohibido o repitió llamadas idénticas?
- ¿Los argumentos fueron correctos (zona, ventana de tiempo)?

Se evalúa con código (comparar la secuencia de herramientas contra una esperada o contra reglas) y, para lo más subjetivo, con un juez.

### LLM-as-judge

**LLM-as-judge** es usar un LLM para puntuar las respuestas de otro (o del mismo) según una **rúbrica** explícita. Sirve cuando la calidad no se puede verificar con código: tono, completitud, fidelidad a una fuente.

Una rúbrica de ejemplo para respuestas del asistente de soporte:

```text
Eres un evaluador de respuestas de soporte de Rumbo. Recibirás:
- la pregunta del comercio,
- los fragmentos de política recuperados,
- la respuesta generada.

Evalúa cada criterio con 0 (no cumple) o 1 (cumple):

1. Fidelidad: toda afirmación de la respuesta está respaldada por los fragmentos.
   Si menciona un plazo, monto de cupón o condición que no está en los fragmentos, es 0.
2. Responde la pregunta: aborda lo que se preguntó, no un tema relacionado.
3. Accionable: indica qué debe hacer el comercio a continuación, si corresponde.
4. Sin datos personales: no incluye nombre, teléfono ni dirección del destinatario.

Reglas:
- No premies la longitud. Una respuesta corta que cumple los cuatro criterios vale lo mismo que una larga.
- Primero escribe una justificación de una o dos oraciones por criterio, después el puntaje.

Formato de salida (JSON):
{"fidelidad": 0|1, "responde": 0|1, "accionable": 0|1, "sin_pii": 0|1, "justificacion": "..."}
```

El juez **se calibra contra etiquetas humanas**: se toman, por ejemplo, 100 respuestas, las puntúan dos personas del equipo y el juez, y se mide el acuerdo. Si el juez coincide con las personas en el 90% de los casos (y las personas entre sí en un porcentaje similar), es usable. Si coincide en el 70%, hay que ajustar la rúbrica, dar ejemplos o cambiar de modelo juez.

Sesgos conocidos de los jueces:

- **Longitud:** tienden a preferir respuestas más largas y detalladas aunque no sean mejores.
- **Posición:** al comparar dos respuestas A y B, tienden a favorecer la que aparece primero (o segunda, según el modelo). Se mitiga evaluando en ambos órdenes.
- **Autopreferencia:** un modelo puede favorecer respuestas con su propio estilo.
- **Tono seguro:** respuestas que suenan confiadas se puntúan mejor aunque sean incorrectas.

Por eso conviene preferir criterios binarios y concretos sobre escalas de 1 a 10, y revisar periódicamente una muestra a mano.

### Métodos de evaluación comparados

| Método | Cómo funciona | Sirve para | Limitación |
|---|---|---|---|
| Verificación por código | Reglas determinísticas: coincidencia exacta, JSON válido, categoría correcta, la cita existe en el documento | Clasificación, extracción, formato, trayectorias con secuencia esperada | No evalúa calidad abierta (tono, completitud, utilidad) |
| LLM-as-judge | Un LLM puntúa con una rúbrica explícita | Fidelidad, relevancia, tono, cumplimiento de criterios en texto libre | Tiene sesgos, cuesta tokens y necesita calibración contra humanos |
| Revisión humana | Personas puntúan con la misma rúbrica | Construir etiquetas de referencia, calibrar jueces, casos ambiguos | Lenta, cara, y dos personas pueden discrepar |
| Métricas online | Se miden señales de uso real: aceptación, edición, repreguntas, A/B | Confirmar impacto real después del deploy | Llegan tarde, tienen ruido y dependen del tráfico |

### Ejemplo de reporte de eval

Comparación de dos prompts para el clasificador de tickets, sobre el golden set de 300 casos, 3 corridas cada uno:

```text
Eval: clasificador_tickets  | golden set v7 (300 casos) | 3 corridas por variante

                          prompt_actual (v12)   prompt_candidato (v13)   delta
Exactitud (media)               91,3%                 93,8%              +2,5
  rango entre corridas      90,7 - 92,0           93,3 - 94,3
Recall "reclamo urgente"        84,0%                 90,0%              +6,0
Precision "reclamo urgente"     88,7%                 87,1%              -1,6
Errores de formato JSON            0                     0                 0
Latencia p95                    1,9 s                 2,1 s             +0,2 s
Tokens de entrada por caso        820                 1.140               +39%
Costo por 1.000 casos      (hipotético) 0,60 USD   0,78 USD               +30%

Casos que mejoran: 11  | Casos que empeoran: 4 (ver lista en anexo)
Umbrales de CI: OK (exactitud no cae, recall crítico no cae, formato sin errores)
Recomendación: aprobar v13; revisar los 4 casos que empeoran y agregarlos al golden set
si son representativos. El costo sube por los ejemplos adicionales en el prompt.
```

Fíjate en que el reporte no da solo un número: muestra dispersión, métricas por categoría crítica, costo y latencia, y los casos que cambian.

## Casos prácticos

### Cambiar a un modelo más barato

**Situación:** se evalúa reemplazar el modelo del clasificador de tickets por uno más chico. En el golden set, la exactitud baja de 94% a 91% y el costo baja un 60%.

**Qué se hace:** no es una decisión técnica sino de negocio, y se toma con datos:

- **Qué significan 3 puntos:** con 10.000 tickets por día, son unos 300 tickets más mal clasificados por día. ¿Qué cuesta cada uno? Si el error es mandar un ticket a la cola equivocada y se corrige en dos minutos, quizás es aceptable. Si el error es no detectar un reclamo urgente, no.
- **Mirar por categoría:** si los 3 puntos se pierden en categorías de bajo impacto y el recall de "reclamo urgente" se mantiene, la decisión es más fácil.
- **Opción intermedia:** usar el modelo barato para todos los tickets y enviar al modelo grande solo los casos donde el barato tiene baja confianza o detecta una categoría crítica. Si eso es un 15% del tráfico, el ahorro sigue siendo grande y la exactitud se acerca a la original. Esa variante también se evalúa en el golden set.

El reporte final presenta las tres opciones (actual, barato, intermedia) con exactitud, recall crítico y costo, y la decide el dueño de producto con el equipo.

### Armar el golden set del clasificador de tickets

**Situación:** el clasificador de tickets está en producción hace meses sin evals formales; cada cambio de prompt se prueba con un puñado de ejemplos.

**Qué se hace:**

1. Se exportan tickets de los últimos tres meses, se enmascaran datos personales (nombres, teléfonos, direcciones).
2. Se toma una muestra aleatoria de 200 que respete la proporción real de categorías.
3. Se agregan 70 casos difíciles: tickets en el límite entre dos categorías, mensajes muy cortos, mezcla de temas, errores de ortografía.
4. Se agregan 30 casos de errores reportados por el equipo de soporte.
5. Dos personas etiquetan cada caso por separado; donde discrepan, se discute y se ajusta la definición de la categoría. Ese desacuerdo es información valiosa: si las personas no se ponen de acuerdo, el modelo tampoco va a acertar.
6. Se versiona el golden set junto con el código y se conecta a CI.

### Juez que premia respuestas largas

**Situación:** después de cambiar el prompt del asistente de soporte, el puntaje del juez sube de 3,8 a 4,4 sobre 5. Pero los agentes de soporte se quejan de que las respuestas son más largas y menos directas.

**Qué se hace:** se revisan las puntuaciones y se confirma el sesgo de longitud: el juez prefería las respuestas más extensas. Se cambia la rúbrica a criterios binarios concretos (fidelidad, responde, accionable, sin datos personales), con la instrucción explícita de no premiar la longitud, se agrega la longitud como métrica separada, y se recalibra el juez contra 100 casos etiquetados por personas. Con el juez corregido, la mejora del prompt nuevo desaparece y se descarta el cambio.

### Métrica online de aceptación que cae y dispara rollback

**Situación:** el asistente sugiere borradores de respuesta a los agentes de soporte, que pueden aceptarlos tal cual, editarlos o descartarlos. La tasa de aceptación habitual ronda el 62%. Tras desplegar un prompt nuevo (que pasó las evals offline), en dos horas la aceptación baja al 48%.

**Qué se hace:** hay una alerta configurada sobre la tasa de aceptación por versión de prompt, con un umbral de caída relativa. Se dispara, y como el prompt está versionado y detrás de una feature flag, se hace rollback a la versión anterior en minutos (ver [LLMs en producción](#t/llms-produccion)). Después se investiga: el prompt nuevo cambió el tono a uno más formal que los agentes editaban sistemáticamente. Se agregan casos de tono al golden set y una métrica de "distancia de edición" a las evals online.

## Errores comunes

- **Evaluar con cinco ejemplos a mano.** Es intuición, no medición; con un golden set de al menos 50 casos reales las decisiones dejan de depender de qué ejemplos se eligieron.
- **Golden set con casos inventados o solo fáciles.** Da números optimistas; hay que incluir casos reales difíciles y los errores de producción.
- **Mirar solo la exactitud global.** Puede ocultar un recall malo en la categoría que más importa; siempre desglosar por categorías críticas.
- **Correr las evals una sola vez.** El no determinismo puede hacer que una diferencia de un punto sea ruido; correr varias veces y mirar la dispersión.
- **Usar un juez sin calibrar.** Un LLM-as-judge sin comparar contra etiquetas humanas puede medir sesgos (longitud, tono) en vez de calidad.
- **Olvidar costo y latencia.** Una mejora de calidad que triplica el costo o la latencia puede no valer la pena; esas métricas van en todo reporte.

## Para discutir en equipo

- ¿Qué funcionalidades con LLM tenemos hoy en producción sin golden set, y cuál deberíamos cubrir primero?
- ¿Qué umbrales de regresión deberían bloquear el merge para el clasificador de tickets, y quién los decide?
- ¿Qué señales online tenemos disponibles (aceptación, edición, repreguntas) y cuáles nos faltan instrumentar?
- ¿Cada cuánto deberíamos recalibrar los jueces y quién etiqueta los casos de referencia?
- Para el agente de operaciones, ¿cómo definiríamos una "trayectoria correcta" sin ser demasiado rígidos?
