---
slug: fundamentos-llms
titulo: Fundamentos de LLMs
resumen: Qué es un modelo de lenguaje grande, cómo genera texto token a token y qué implica eso en latencia, costo y confiabilidad.
lectura: 13
---

## La idea central

Un LLM (Large Language Model, modelo de lenguaje grande) es, en el fondo, una función que recibe un texto y devuelve una distribución de probabilidades sobre cuál debería ser el próximo fragmento de texto. Nada más. Todo lo que vemos que "hace" (responder preguntas, resumir, clasificar, escribir código) sale de repetir ese paso muchas veces: predecir un fragmento, agregarlo al texto, volver a predecir.

Esta idea simple explica casi todas las propiedades que importan al diseñar sistemas con LLMs. Explica por qué la latencia crece con el largo de la respuesta, por qué el costo se mide en fragmentos de texto, por qué el modelo puede inventar cosas con total seguridad y por qué no "recuerda" nada entre una llamada y la siguiente. Una analogía útil: un LLM se parece a un autocompletado de teclado extraordinariamente bueno, entrenado con una fracción enorme del texto escrito por la humanidad. Es muy capaz, pero sigue siendo un autocompletado: no consulta una base de datos ni verifica hechos salvo que se lo diseñe para eso.

## Conceptos

### Cómo genera texto: predicción del siguiente token en bucle

El proceso de generación funciona así:

1. El texto de entrada se convierte en una secuencia de tokens (fragmentos de texto, explicados en la sección siguiente).
2. El modelo procesa toda la secuencia y calcula, para cada token posible de su vocabulario (decenas de miles o más), la probabilidad de que sea el siguiente.
3. Se elige un token de esa distribución (cómo se elige depende de la temperatura).
4. Ese token se agrega al final de la secuencia y se vuelve al paso 2.
5. El bucle termina cuando el modelo genera un token especial de "fin" o se alcanza un límite de tokens de salida.

El modelo no planifica la respuesta completa de antemano y luego la escribe: cada token se decide mirando todo lo anterior, incluido lo que el propio modelo acaba de escribir.

**Ejemplo:** ante el texto "El pedido fue entregado a", el modelo podría calcular algo así (valores ilustrativos):

| Siguiente token | Probabilidad |
|---|---|
| " tiempo" | 0,62 |
| " las" | 0,12 |
| " domicilio" | 0,08 |
| " su" | 0,06 |
| (resto del vocabulario) | 0,12 |

Si se elige " tiempo", la nueva entrada es "El pedido fue entregado a tiempo" y el modelo vuelve a calcular: ahora lo más probable quizá sea "." o " según". Una respuesta de 300 tokens implica 300 vueltas de este bucle.

**Por qué importa:** como cada token depende de los anteriores, un error temprano (un dato inventado en la primera oración) condiciona todo lo que sigue. Y como el bucle es secuencial, generar más texto siempre tarda más.

### Token y tokenizador

Un **token** es la unidad mínima que el modelo lee y escribe. No es exactamente una palabra ni una letra: es un fragmento frecuente de texto. El **tokenizador** es el componente que corta el texto en tokens según un vocabulario fijo, aprendido antes del entrenamiento a partir de qué secuencias de caracteres aparecen más.

Las palabras muy comunes suelen ser un solo token; las raras o largas se parten en varios. Ejemplos ilustrativos (los cortes exactos dependen de cada tokenizador):

- "pedido" → `pedido` (1 token)
- "transportista" → `trans` + `port` + `ista` (3 tokens)
- "desafortunadamente" → `des` + `afort` + `un` + `adamente` (4 tokens)
- "RMB-4012" → `RM` + `B` + `-` + `401` + `2` (5 tokens)

Una regla práctica muy citada para inglés: 1.000 tokens equivalen a unas 750 palabras. En castellano, como los tokenizadores suelen estar optimizados para inglés, el mismo contenido tiende a necesitar algo más de tokens. Para estimaciones rápidas conviene medir con el tokenizador real del modelo que se va a usar sobre una muestra de textos propios.

**Ejemplo:** un manual interno de 30 páginas con 15.000 palabras en castellano puede rondar, en orden de magnitud, los 25.000 tokens.

**Por qué importa:** todo se mide en tokens: el costo, el límite de contexto y el tiempo de generación. Además, el corte en tokens explica rarezas, como que al modelo le cueste contar letras o manipular identificadores largos carácter por carácter.

### Ventana de contexto

La **ventana de contexto** es la cantidad máxima de tokens que el modelo puede considerar en una sola llamada, sumando entrada (instrucciones, historial, documentos) y salida (lo que genera). Los modelos actuales van, en orden de magnitud, de decenas de miles a cientos de miles de tokens, y algunos llegan más lejos.

Dos matices importantes. Primero, si la entrada ocupa casi toda la ventana, queda poco espacio para la respuesta. Segundo, que algo "entre" en la ventana no garantiza que el modelo lo use bien: con contextos muy largos, la información ubicada en el medio tiende a aprovecharse peor que la que está al principio o al final, y cada token extra suma costo y latencia.

**Ejemplo:** con una ventana hipotética de 200.000 tokens, cargar los 40 manuales de soporte de Rumbo completos (unos 600.000 tokens) es imposible. Hay que elegir qué fragmentos enviar en cada consulta, que es justamente lo que resuelve [RAG](#t/rag).

### Sin estado entre llamadas

Un LLM no guarda nada entre una llamada y la siguiente. Cada petición a la API es independiente, igual que una petición HTTP: el servidor no "se acuerda" del usuario salvo que la aplicación le envíe la información otra vez.

Entonces, ¿cómo "recuerda" un chat lo que se dijo antes? La aplicación reenvía el historial completo en cada turno. En el turno 1 se envía la pregunta 1. En el turno 2 se envía la pregunta 1, la respuesta 1 y la pregunta 2. En el turno 10 se envían los nueve intercambios anteriores más la pregunta nueva.

**Ejemplo:** si cada intercambio (pregunta más respuesta) suma 500 tokens y el prompt de sistema tiene 1.000, el turno 1 envía unos 1.000 tokens de entrada, el turno 10 unos 5.500 y el turno 30 unos 15.500. El costo de cada turno crece linealmente y el costo total de la conversación crece aproximadamente con el cuadrado de la cantidad de turnos.

**Por qué importa:** la "memoria" es una decisión de la aplicación, no del modelo. Qué se reenvía, qué se resume y qué se descarta define el costo y la calidad.

### Pre-entrenamiento, fine-tuning e inferencia

Un LLM pasa por tres etapas, que se entienden bien con una analogía laboral:

- **Pre-entrenamiento (la carrera universitaria):** el modelo aprende a predecir el siguiente token sobre cantidades enormes de texto. Así adquiere conocimiento general del lenguaje y del mundo. Es carísimo (semanas o meses de cómputo masivo) y lo hacen pocos laboratorios.
- **Fine-tuning (la capacitación de la empresa):** se ajusta el modelo ya entrenado con un conjunto más chico y específico de ejemplos para que se comporte de cierta manera: seguir instrucciones, responder en un formato, adoptar un tono o especializarse en un dominio. Es mucho más barato que el pre-entrenamiento, pero requiere datos de calidad y un proceso de evaluación.
- **Inferencia (el trabajo diario):** usar el modelo para responder peticiones reales. Los pesos del modelo no cambian; lo que aprende "en el momento" vive solo en el contexto de esa llamada.

**Ejemplo:** si el asistente de soporte de Rumbo desconoce una política nueva publicada ayer, no hay que reentrenar el modelo: basta con incluir la política en el contexto en el momento de la inferencia. El conocimiento general viene del pre-entrenamiento; el conocimiento fresco y específico, del contexto.

### Temperatura

La **temperatura** controla cuán "arriesgada" es la elección del siguiente token. Con temperatura 0 (o muy baja), el modelo elige casi siempre el token más probable: la salida es más predecible y repetible. Con temperatura alta, la distribución se aplana y tokens menos probables tienen más chances: la salida es más variada y creativa, pero también más propensa a desvíos.

**Ejemplo:** con la tabla de antes, a temperatura 0 el modelo elige " tiempo" prácticamente siempre. A temperatura 1 elegiría " tiempo" alrededor del 62 % de las veces y " domicilio" un 8 %. A temperatura 1,5 los tokens raros ganan aún más peso.

**Por qué importa:** para extracción de datos, clasificación o cualquier tarea con una respuesta correcta conviene temperatura baja. Para generar variantes de un texto, una temperatura media. Aun con temperatura 0 no hay garantía absoluta de determinismo: detalles de implementación del proveedor pueden producir pequeñas diferencias entre ejecuciones.

### Latencia: tiempo al primer token y tiempo por token

La latencia de una llamada a un LLM tiene dos componentes:

- **Tiempo al primer token (TTFT, time to first token):** lo que tarda el modelo en procesar toda la entrada y emitir el primer token. Crece con el largo de la entrada y con la carga del proveedor.
- **Tiempo por token de salida:** cada token adicional requiere una vuelta del bucle.

Fórmula aproximada: **latencia total ≈ TTFT + (tokens de salida × tiempo por token)**.

**Ejemplo (valores hipotéticos):** TTFT de 400 ms, respuesta de 300 tokens y 20 ms por token. Latencia total ≈ 400 ms + 300 × 20 ms = 400 ms + 6.000 ms = 6,4 segundos. Si la respuesta se acorta a 80 tokens: 400 + 1.600 = 2 segundos. Reducir la salida es la palanca más directa para bajar la latencia.

El **streaming** consiste en enviar al usuario cada token a medida que se genera, en lugar de esperar la respuesta completa. No reduce la latencia total, pero cambia la percepción: el usuario empieza a leer a los 400 ms en vez de mirar una pantalla vacía durante 6,4 segundos. Sirve para interfaces de chat; no sirve cuando otro sistema necesita la respuesta completa (por ejemplo, un JSON que hay que validar antes de usar).

### Costo por token de entrada y de salida

Los proveedores facturan el uso por token, con precios distintos para entrada y salida. La salida suele costar varias veces más que la entrada, porque generar cada token es una vuelta completa del bucle.

**Ejemplo (precios hipotéticos):** USD 3 por millón de tokens de entrada y USD 15 por millón de tokens de salida. Cada consulta del asistente envía 3.000 tokens de entrada y recibe 300 de salida.

- Entrada: 3.000 × 3 / 1.000.000 = USD 0,009
- Salida: 300 × 15 / 1.000.000 = USD 0,0045
- Total por consulta: USD 0,0135

Con 20.000 consultas por día durante 30 días (600.000 consultas al mes): 600.000 × 0,0135 = **USD 8.100 por mes**. Si el historial y los documentos inflan la entrada a 12.000 tokens por consulta, el costo de entrada se cuadruplica y el total sube a unos USD 24.300 por mes.

**Por qué importa:** el costo es lineal en tokens, y a escala los detalles cuentan. Recortar 1.000 tokens de un prompt de sistema que se envía en cada llamada vale más que optimizar cualquier otra cosa. En [LLMs en producción](#t/llms-produccion) se ven técnicas como caching y límites por usuario.

### Alucinación y cómo se mitiga

Una **alucinación** es una respuesta fluida y segura que es falsa: un dato inventado, una política que no existe, un número de seguimiento con formato correcto pero inexistente. Ocurre porque el modelo optimiza "texto plausible", no "texto verdadero": si no tiene la información, el bucle de predicción igual produce algo que suena bien.

No se elimina, pero se reduce con varias capas:

1. **Grounding (anclaje):** darle al modelo los datos relevantes en el contexto (por ejemplo, con RAG) e instruirlo a responder solo a partir de ellos.
2. **Permitir "no lo sé":** indicar explícitamente que, si la información no está en el contexto, debe decirlo. Sin esa salida, el modelo tiende a rellenar.
3. **Pedir citas:** que indique de qué documento sale cada afirmación, para poder verificarlo.
4. **Validar en código:** si la respuesta incluye un identificador de pedido, comprobar que exista antes de mostrarlo.
5. **Evaluar:** medir la tasa de respuestas sin sustento sobre un conjunto de preguntas conocidas (ver [Evaluación de LLMs](#t/evaluacion-llms)).

**Ejemplo:** un usuario pregunta "¿cuál es el plazo para reclamar un paquete dañado?". Sin contexto, el modelo puede responder "72 horas" con total seguridad. Con la política real en el contexto y la instrucción de citarla, responde "5 días hábiles (Política de reclamos, sección 3)" o, si la política no aparece, "no encuentro esa información".

### Tamaño del modelo y ruteo de tareas

Los modelos vienen en distintos tamaños. Los grandes razonan mejor, siguen instrucciones complejas y manejan casos ambiguos, pero son más lentos y caros. Los chicos son rápidos y baratos, y alcanzan de sobra para tareas acotadas: clasificar, extraer campos, resumir textos cortos.

El **ruteo** consiste en enviar cada tarea al modelo más chico que la resuelve bien. Puede ser estático (la clasificación de tickets siempre va al modelo chico) o dinámico (un clasificador o una regla decide si la consulta es simple o compleja).

**Ejemplo (valores hipotéticos):** si el modelo chico cuesta un décimo del grande y el 80 % de las consultas son simples, rutear esas al modelo chico reduce el costo total a 0,8 × 0,1 + 0,2 × 1 = 0,28 del original, es decir, un 72 % menos, y además baja la latencia de la mayoría de las consultas.

**Por qué importa:** usar siempre el modelo más grande "por las dudas" es una de las fuentes más comunes de costo innecesario. La decisión debe tomarse con evaluaciones: medir la calidad del modelo chico en la tarea concreta antes de rutear.

## Casos prácticos

### Por qué no poner un LLM en el camino crítico de la asignación

**Situación:** alguien propone que el servicio de asignación de Rumbo le pregunte a un LLM qué transportista debe tomar cada pedido, "porque puede razonar sobre el contexto".

**Qué se hace:** se descarta para el camino crítico. El servicio de asignación tiene un presupuesto de unos 50 ms, y un LLM tarda cientos de milisegundos solo en emitir el primer token, con variaciones grandes según la carga del proveedor. Además, la decisión de asignación es una optimización numérica sobre features (distancia, carga, ETA) que el modelo de ML actual resuelve mejor, de forma reproducible y auditable. El LLM sí aporta fuera de ese camino: extraer de las notas libres del comercio ("dejar en portería", "no tocar timbre, hay un bebé") campos estructurados que luego alimentan el modelo como features, en un proceso asincrónico; explicar a operaciones por qué se asignó un pedido a partir de los datos de la decisión; o resumir incidentes para el agente de operaciones.

### Un asistente interno cuyo costo se dispara

**Situación:** el asistente interno de operaciones costaba lo previsto en el piloto, pero al mes de abrirlo a todo el equipo la factura del proveedor se multiplicó por cinco, aunque la cantidad de conversaciones solo se duplicó.

**Qué se hace:** se analiza el tamaño de entrada por turno y aparece el problema: cada turno agrega al historial unos 4.000 tokens de documentos recuperados más 500 de conversación, y todo se reenvía en los turnos siguientes. En una conversación de 20 turnos, la entrada total ronda 20 × 1.000 (sistema) + 4.500 × (1 + 2 + ... + 20) = 20.000 + 945.000 ≈ 965.000 tokens. Si los documentos solo se envían en el turno en que se usan y el historial guarda únicamente preguntas y respuestas, la entrada baja a unos 20 × 5.000 + 500 × 210 = 205.000 tokens, casi cinco veces menos. Se complementa con resumir el historial después de cierto número de turnos, poner la parte fija del prompt al principio para aprovechar prompt caching y fijar un límite de turnos por conversación.

### Extracción de datos inconsistente

**Situación:** un proceso usa un LLM para extraer de los correos de comercios la franja horaria de entrega preferida. A veces devuelve "14 a 18 hs", otras "14:00-18:00", otras "por la tarde", y ocasionalmente agrega una frase explicativa que rompe el parser.

**Qué se hace:** tres cambios combinados. Temperatura 0 para reducir la variabilidad. Salida en JSON con un esquema explícito (`{"desde": "HH:MM", "hasta": "HH:MM", "encontrado": true|false}`), usando la función de salidas estructuradas del proveedor si existe. Y validación en código: si el JSON no cumple el esquema o "desde" es posterior a "hasta", se reintenta una vez y, si vuelve a fallar, el caso va a revisión manual. El campo "encontrado" le da al modelo una salida legítima cuando el correo no menciona horario, en lugar de forzarlo a inventar. El detalle de cómo escribir este tipo de prompt está en [Prompt engineering](#t/prompt-engineering).

### Cuándo no usar un LLM

**Situación:** en una revisión de diseño aparecen propuestas para usar un LLM en calcular el costo operativo de una ruta, validar el formato de códigos postales y decidir si un pedido superó su ETA.

**Qué se hace:** las tres se resuelven sin LLM. Son tareas deterministas con una respuesta exacta: una fórmula, una expresión regular y una comparación de timestamps. Un LLM agregaría latencia, costo y la posibilidad de error en algo que el código resuelve siempre bien. Criterio general: no usar un LLM cuando hay una regla o un cálculo exacto, cuando la latencia es de milisegundos, cuando se necesita reproducibilidad total o cuando un modelo de ML clásico entrenado con datos propios ya resuelve el problema. Sí usarlo cuando la entrada es lenguaje natural no estructurado, cuando la tarea es de redacción, resumen o clasificación difusa, o cuando escribir reglas a mano sería interminable.

## Errores comunes

- **Suponer que el modelo recuerda conversaciones anteriores.** No tiene estado; todo lo que debe saber tiene que estar en el contexto de cada llamada, y eso tiene costo.
- **Estimar costos solo con el precio de entrada.** La salida suele ser varias veces más cara por token; un cambio que alarga las respuestas puede disparar el costo aunque la entrada no cambie.
- **Confiar en que el contexto largo resuelve todo.** Que algo entre en la ventana no significa que se use bien; más tokens implican más costo, más latencia y más riesgo de que el modelo ignore lo importante.
- **Usar temperatura alta en tareas de extracción o clasificación.** Para tareas con respuesta correcta, temperatura baja y salida estructurada validada.
- **Medir latencia solo como promedio.** El tiempo al primer token varía mucho con la carga del proveedor; hay que mirar percentiles altos (p95, p99) y diseñar timeouts y alternativas.
- **Tratar las respuestas del modelo como datos verificados.** Cualquier identificador, número o afirmación crítica debe validarse en código o contra una fuente antes de usarse.

## Para discutir en equipo

- ¿Qué procesos de Rumbo hoy dependen de reglas escritas a mano sobre texto libre y podrían beneficiarse de un LLM fuera del camino crítico?
- Si mañana el proveedor duplica el precio de los tokens de salida, ¿qué funcionalidades se verían más afectadas y qué haríamos primero?
- ¿Qué latencia es aceptable para el asistente de soporte, y qué cambia si se usa streaming o no?
- ¿Cómo decidiríamos, con datos, si una tarea puede pasar del modelo grande al modelo chico?
- ¿Qué tipo de alucinación sería más dañina en el asistente de soporte y qué capa de mitigación la frenaría?
