---
slug: adaptar-modelos
titulo: Adaptar modelos: fine-tuning, destilación y cuantización
resumen: Cuándo y cómo ajustar, achicar o comprimir un modelo de lenguaje para una tarea propia, y qué cuesta evaluarlo y operarlo después.
lectura: 15
---

## La idea central

Un modelo de lenguaje recién salido del proveedor es un generalista: sabe un poco de todo y no conoce nada de Rumbo. Acercarlo a una tarea concreta puede costar una tarde (mejorar el prompt) o semanas de preparar datos, evaluar y mantener una pieza más en producción (ajustar sus pesos). La pregunta útil no es "¿hacemos fine-tuning?", sino "¿qué problema tenemos exactamente: le falta **conocimiento**, se **comporta** mal (formato, estilo, criterio) o es demasiado **caro o lento**?". Cada respuesta lleva a una herramienta distinta.

Una analogía: a una persona nueva con experiencia general, si no conoce las políticas se le da el manual (RAG); si redacta en un formato que no sirve, se la capacita con ejemplos (fine-tuning); si el trabajo es repetitivo, se forma a un junior con lo que produce el experto (destilación). La cuantización, en cambio, comprime el modelo para que quepa en menos memoria. En los agentes, estas técnicas permiten que un modelo chico y ajustado resuelva los pasos más frecuentes del bucle.

## Conceptos

### La escalera de decisión

Las opciones se ordenan de menor a mayor costo. La regla es subir un escalón solo cuando el anterior está agotado y medido:

1. **Mejor prompt:** instrucciones claras, formato de salida explícito, salidas estructuradas. Horas de trabajo.
2. **Few-shot:** agregar al prompt algunos ejemplos resueltos de la tarea. Horas.
3. **RAG:** recuperar en cada consulta los documentos relevantes (ver [RAG](#t/rag)). Días a semanas.
4. **Fine-tuning:** seguir entrenando el modelo con ejemplos propios para cambiar su comportamiento. Semanas, más el costo de operarlo.
5. **Entrenar desde cero:** casi nunca tiene sentido fuera de los laboratorios que construyen modelos base.

| Problema observado | Herramienta adecuada | Por qué |
|---|---|---|
| No conoce políticas, tarifas internas o datos que cambian | RAG | El conocimiento vive en documentos que se actualizan en minutos y se pueden citar |
| Formato inconsistente, tono incorrecto, no sigue un estilo | Prompt y few-shot; si no alcanza, fine-tuning | Es un problema de comportamiento, no de datos |
| Tarea estable y de alto volumen, prompt muy largo con decenas de ejemplos | Fine-tuning | Los ejemplos pasan a los pesos y el prompt se acorta |
| Costo o latencia altos en una tarea acotada | Destilación a un modelo chico | Un modelo chico especializado alcanza la calidad del grande en esa tarea |
| No entra en la GPU disponible | Cuantización | Reduce la memoria de los pesos a cambio de algo de calidad |

**Ejemplo:** el prompt de clasificación de tickets de Rumbo tiene 40 ejemplos few-shot y ocupa 3.000 tokens por llamada. A 30.000 tickets diarios, son 90 millones de tokens de entrada por día solo en ejemplos. Un modelo ajustado con esos casos (y muchos más) puede clasificar con un prompt de 300 tokens.

**Por qué importa:** el error más caro es usar fine-tuning para un problema de conocimiento: el modelo memoriza mal los datos, no cita fuentes y queda desactualizado con el próximo cambio.

### Fine-tuning supervisado: los datos

El **fine-tuning supervisado** (SFT, por sus siglas en inglés) parte de un modelo ya entrenado (ver [Fundamentos de LLMs](#t/fundamentos-llms)) y le muestra pares de **entrada** y **salida ideal**, para que ante entradas parecidas genere salidas parecidas.

Un ejemplo típico en formato JSONL (una línea por ejemplo):

```json
{"entrada": "Ticket: el repartidor dejó el paquete en la portería equivocada, edificio de al lado", "salida": {"categoria": "entrega_direccion_incorrecta", "urgencia": "media", "requiere_humano": false}}
```

Órdenes de magnitud orientativos:

- **Cientos de ejemplos** suelen alcanzar para enseñar un formato o un estilo.
- **Unos miles** para una clasificación con 10 a 30 categorías o una extracción con varios campos.
- **Decenas de miles** rara vez se justifican al principio; antes conviene mejorar la calidad.

La **calidad pesa más que la cantidad**. Mil ejemplos revisados, sin contradicciones y que cubren los casos difíciles rinden más que diez mil exportados sin mirar. Si el 15 % de las etiquetas históricas está mal, el modelo aprende ese 15 % de error con total convicción.

Los datos se dividen en **entrenamiento** (por ejemplo 80 %), **validación** (10 %, para decidir cuándo parar) y **prueba** (10 %, que se mira una sola vez al final), separando por tiempo o por comercio para que tickets casi idénticos no queden a ambos lados.

**Por qué importa:** el modelo nunca es mejor que sus datos; la mayor parte del esfuerzo está en construir y revisar los ejemplos, no en entrenar.

### Overfitting y olvido catastrófico

Dos riesgos aparecen en todo fine-tuning:

- **Overfitting (sobreajuste):** el modelo memoriza los ejemplos de entrenamiento en lugar de aprender el patrón. Se detecta cuando la pérdida en entrenamiento sigue bajando y la de validación empieza a subir. Se mitiga con menos épocas (pasadas completas por los datos) y más variedad de ejemplos.
- **Olvido catastrófico:** al especializarse, el modelo pierde capacidades generales que tenía: razonar, seguir instrucciones distintas a las del entrenamiento, negarse a pedidos fuera de alcance. Se mitiga con tasas de aprendizaje bajas, pocas épocas, mezclando algunos ejemplos generales en los datos y usando métodos que no tocan los pesos originales (LoRA, a continuación).

**Ejemplo:** tras 2 épocas, la precisión en validación es 91 %; tras 6 épocas, la de entrenamiento llega a 99 % y la de validación baja a 86 %. Se elige el punto de 2 épocas.

### Fine-tuning completo frente a LoRA y QLoRA

En el **fine-tuning completo** se actualizan todos los pesos del modelo. Para un modelo de 7.000 millones de parámetros (7B), eso exige guardar en memoria los pesos, los gradientes y el estado del optimizador. Una estimación habitual en entrenamiento con precisión mixta es del orden de 16 bytes por parámetro: 7B × 16 = unos 112 GB, sin contar las activaciones. Hace falta más de una GPU grande.

**LoRA** (Low-Rank Adaptation, adaptación de bajo rango) parte de otra intuición: el cambio que necesita el modelo para una tarea concreta es "pequeño" y se puede describir con pocos números. En lugar de modificar una matriz de pesos grande, se la **congela** y se le suman dos matrices delgadas, A y B, cuyo producto tiene la misma forma que la original. Solo se entrenan A y B.

Paso a paso con una matriz de 4.096 × 4.096:

1. La matriz original tiene 4.096 × 4.096 ≈ 16,8 millones de parámetros, que quedan congelados.
2. Con **rango** 8, A mide 4.096 × 8 y B mide 8 × 4.096: 32.768 + 32.768 = 65.536 parámetros entrenables, el 0,39 % de la matriz.
3. Si se aplica LoRA a 4 matrices de atención en cada una de 32 capas: 128 × 65.536 ≈ 8,4 millones de parámetros entrenables, alrededor del **0,12 %** de los 7B.
4. Memoria: los pesos congelados en 16 bits ocupan unos 14 GB; los gradientes y el optimizador solo existen para 8,4 millones de parámetros (decenas de MB). Con activaciones, el entrenamiento entra en una sola GPU de 24 GB, en orden de magnitud.
5. El resultado, el **adaptador**, pesa unos 8,4 M × 2 bytes ≈ 17 MB.

**QLoRA** combina LoRA con cuantización: los pesos congelados se cargan en 4 bits (unos 3,5 a 4 GB para 7B) y los adaptadores se entrenan en mayor precisión. Permite ajustar modelos medianos en GPUs de 12 a 16 GB, a cambio de un entrenamiento algo más lento.

**Adaptadores intercambiables:** un servidor puede cargar un solo modelo base y varios adaptadores de pocos MB (clasificar tickets, extraer franjas horarias, tono de respuestas) y, en algunos servidores de inferencia, elegir el adaptador por petición.

**Por qué importa:** LoRA abarata mucho el entrenamiento y reduce el olvido catastrófico, porque los pesos originales quedan intactos. Para nuestro equipo, es el punto de partida.

### Ajuste por preferencias

El SFT enseña "esta es la respuesta correcta". Hay tareas donde no existe una única respuesta correcta, pero sí se puede decir cuál de dos es **mejor**: más clara, más prudente, mejor tono. El **ajuste por preferencias** usa pares (pregunta, respuesta preferida, respuesta rechazada).

- **RLHF** (aprendizaje por refuerzo con retroalimentación humana): se entrena un modelo que puntúa respuestas a partir de las preferencias, y luego se optimiza el LLM para obtener buenos puntajes. Es potente y complejo de operar.
- **DPO** (Direct Preference Optimization): ajusta el modelo directamente con los pares, sin el modelo de puntaje intermedio. Es más simple y es la opción habitual cuando un equipo hace ajuste por preferencias.

**Ejemplo:** para el asistente de soporte se juntan 2.000 pares donde agentes humanos eligieron entre dos borradores. La respuesta rechazada suele prometer plazos que no corresponden; la preferida deriva a una persona.

### Fine-tuning para agentes: tool calling y salidas estructuradas

En un agente, la mayoría de las llamadas al modelo son decisiones cortas y repetitivas: qué herramienta llamar, con qué argumentos, qué campos extraer. Son tareas de comportamiento con formato estricto, el terreno ideal del fine-tuning.

Los ejemplos de entrenamiento incluyen la consulta, la lista de herramientas disponibles y la llamada correcta en JSON. Conviene incluir casos negativos: consultas donde la respuesta correcta es **no** llamar ninguna herramienta, o pedir una aclaración.

**Ejemplo:** el agente de operaciones de Rumbo hace en promedio 6 llamadas al modelo por investigación; 4 son selección de herramienta y extracción de parámetros ("zona norte, últimas 3 horas"). Si esas 4 pasan a un modelo chico ajustado y las 2 de razonamiento y redacción final siguen en el grande, y el chico cuesta un décimo, el costo por investigación baja a (4 × 0,1 + 2 × 1) / 6 = 0,4 del original, un 60 % menos.

**Por qué importa:** permite un diseño escalonado del agente: un modelo chico y predecible para el trabajo mecánico, y uno grande para el razonamiento.

### Destilación: el maestro y el alumno

Es una de las formas de conseguir el modelo pequeño de una cascada o de un esquema de ruteo (ver [Varios modelos y ruteo](#t/multimodelo)).

La **destilación** transfiere a un modelo chico (el **alumno**) la capacidad de uno grande (el **maestro**) en una tarea concreta:

1. Se toma un conjunto amplio de entradas reales sin etiquetar, por ejemplo 20.000 tickets.
2. El maestro las etiqueta o genera las respuestas, con un prompt cuidado y, si conviene, razonamiento paso a paso.
3. Se revisa una muestra a mano y se descartan o corrigen los errores.
4. Se ajusta el alumno con esos pares (normalmente con LoRA).
5. Se evalúa el alumno contra un conjunto de prueba etiquetado por personas, no por el maestro.

**Ejemplo (valores hipotéticos):** clasificar 30.000 tickets diarios con el modelo grande, a 1.500 tokens de entrada por ticket y 3 dólares por millón de tokens, cuesta 30.000 × 1.500 × 3 / 1.000.000 = 135 dólares por día, unos 4.000 por mes, con 1,5 s de latencia. Etiquetar 20.000 tickets una sola vez con el maestro cuesta 90 dólares. Un alumno chico servido en una GPU de 1 dólar por hora cuesta unos 720 dólares por mes y responde en 80 ms. Si el maestro acierta el 92 % y el alumno el 90 % sobre el conjunto de prueba, la pregunta de negocio es si 2 puntos de calidad valen 3.300 dólares por mes y 1,4 segundos.

**Atención a los términos de uso:** muchos proveedores restringen usar las salidas de sus modelos para entrenar otros, sobre todo si compiten con los suyos. Antes de destilar hay que verificar los términos vigentes del proveedor y la licencia del alumno, con el área legal si hace falta.

### Cuantización: cuántos bits por peso

Cada parámetro del modelo es un número. La **cuantización** reduce cuántos bits se usan para guardarlo:

- **fp16 / bf16 (16 bits, 2 bytes):** el formato habitual para servir; prácticamente sin pérdida respecto del entrenamiento.
- **int8 (8 bits, 1 byte):** la mitad de memoria; pérdida de calidad en general pequeña.
- **int4 (4 bits, medio byte):** un cuarto de la memoria; pérdida variable, que hay que medir en la tarea concreta.

Cuentas para los pesos de un modelo de 7B:

| Precisión | Bytes por parámetro | Memoria de pesos |
|---|---|---|
| 16 bits | 2 | ≈ 14 GB |
| 8 bits | 1 | ≈ 7 GB |
| 4 bits | 0,5 | ≈ 3,5 a 4 GB (con metadatos de escala) |

Para un modelo de 70B, las mismas cuentas dan unos 140 GB en 16 bits y unos 35 a 40 GB en 4 bits. A eso se suma la memoria del **caché KV** (la información que el modelo guarda de los tokens ya procesados), que crece con el largo del contexto y la cantidad de peticiones simultáneas.

**Efecto en la elección de GPU:** un 70B en 16 bits necesita varias GPUs grandes; en 4 bits puede entrar en una sola de 48 GB, lo que cambia el costo y la complejidad del despliegue (ver [Serving e inferencia en tiempo real](#t/serving)). Además, menos bytes que leer de memoria suele dar más tokens por segundo.

**Riesgos de calidad:** la cuantización agresiva tiende a degradar primero el razonamiento de varios pasos, la aritmética, los idiomas menos representados y los formatos estrictos. Se mide, no se supone.

### Evaluar el modelo adaptado contra el base

Un modelo adaptado se evalúa con la **misma batería de evaluación** que el modelo al que reemplaza (ver [Evaluación de LLMs](#t/evaluacion-llms)), y además con tres controles específicos:

1. **La tarea objetivo:** ¿mejoró lo que se buscaba? Precisión de clasificación, validez del JSON, tono.
2. **Regresiones generales:** un conjunto de preguntas fuera de la tarea (instrucciones distintas, razonamiento simple, preguntas fuera de alcance) para detectar olvido catastrófico.
3. **Seguridad:** intentos de inyección de prompt, pedidos de datos personales, consultas que deben rechazarse o derivarse.

**Ejemplo:** el modelo ajustado sube la validez del JSON de 94 % a 99,8 %, pero la tasa de rechazo correcto de preguntas fuera de alcance cae de 96 % a 71 %. No se despliega hasta corregirlo.

### Operar un modelo propio

Un modelo ajustado es un activo que hay que mantener:

- **Versionado:** cada adaptador queda asociado en el registro de modelos a la versión exacta del conjunto de datos, del modelo base, de la configuración y de la evaluación.
- **Reentrenamiento:** con una cadencia (por ejemplo trimestral) y cuando caen las métricas, cambian las categorías o se retira el modelo base.
- **Costo de poseerlo:** GPUs encendidas, personas que curan datos, evaluaciones, guardias. Con poco volumen, una API con buen prompt suele ser más barata; el modelo propio gana con volumen alto y tarea estable.

## Casos prácticos

### "Hagamos fine-tuning para que aprenda las políticas"

**Situación:** el asistente de soporte responde mal sobre plazos de reclamo y reintentos de entrega. Alguien propone ajustar un modelo con todos los manuales de políticas "para que las sepa de memoria".

**Qué se hace:** es un problema de conocimiento, no de comportamiento. Las políticas cambian varias veces por trimestre; un modelo ajustado quedaría desactualizado con cada cambio, no citaría la fuente y mezclaría versiones. Se revisa el pipeline de RAG: chunking de las tablas de plazos, filtro de vigencia y evaluaciones con políticas recién cambiadas. Si después el tono de las respuestas sigue siendo un problema, se puede considerar un ajuste de estilo que conviva con RAG.

### Destilar la clasificación de tickets

**Situación:** la clasificación de tickets con el modelo grande funciona bien pero cuesta unos 4.000 dólares por mes (hipotético) y agrega 1,5 s de latencia antes de que el ticket llegue a la cola correcta.

**Qué se hace:** se arma un conjunto de prueba de 1.000 tickets etiquetados por agentes de soporte. El modelo grande etiqueta 20.000 tickets históricos, se revisa a mano una muestra de 500 (se corrigen 40) y se ajusta un modelo chico con LoRA. En la prueba, el alumno alcanza 90 % frente a 92 % del maestro; la diferencia se concentra en dos categorías poco frecuentes. Se despliega con una regla: si la confianza del alumno es baja o la categoría es una de esas dos, el ticket va al modelo grande. El 85 % del tráfico queda en el alumno, el costo baja cerca de un 70 % y la latencia mediana pasa a 80 ms. Se verificaron previamente los términos del proveedor sobre el uso de sus salidas.

### Un modelo abierto para la GPU de un cliente on-prem

**Situación:** un cliente grande exige que el asistente de soporte corra dentro de su centro de datos, donde hay una sola GPU de 24 GB. El modelo abierto elegido tiene 14B parámetros: unos 28 GB en 16 bits, no entra.

**Qué se hace:** se cuantiza a 4 bits (unos 7 a 8 GB de pesos), lo que deja espacio para el caché KV de varias conversaciones simultáneas. Se corre la batería completa de evaluación en castellano en ambas versiones: la calidad de respuestas baja 2 puntos y la validez del JSON de las llamadas a herramientas, de 99 % a 96,5 %. Se agrega validación del JSON con un reintento, que recupera casi todos los casos. El paquete entregado incluye el modelo cuantizado, el adaptador y la versión exacta de la evaluación.

### Mejoró el formato y dejó de negarse

**Situación:** se ajustó un modelo para que el asistente responda con la estructura "resumen, pasos, enlace a la política". El formato quedó perfecto, pero aparecen respuestas detalladas a preguntas fuera de alcance, como asesoramiento legal sobre un contrato.

**Qué se hace:** los 3.000 ejemplos de entrenamiento tenían respuesta completa; ninguno enseñaba a derivar o rechazar. Se agregan 400 ejemplos de rechazo y derivación con el mismo formato, se baja de 4 a 2 épocas y se suma a la evaluación un bloque fijo de 150 preguntas fuera de alcance que debe superar el 95 % de rechazos correctos antes de cualquier despliegue. Mientras tanto, se vuelve al modelo anterior.

## Errores comunes

- **Usar fine-tuning para dar conocimiento.** Datos que cambian, que hay que citar o que dependen de permisos van por RAG; el fine-tuning es para comportamiento y formato.
- **Entrenar con datos sin revisar.** Las etiquetas históricas tienen errores y contradicciones; revisa una muestra antes de entrenar y mide el acuerdo entre personas.
- **Evaluar solo la tarea objetivo.** Un modelo ajustado puede perder la capacidad de negarse o de seguir otras instrucciones; incluye regresiones generales y de seguridad en cada evaluación.
- **Evaluar al alumno con datos del maestro.** Si la prueba la etiquetó el mismo modelo grande, se mide el parecido al maestro, no la calidad real; usa etiquetas humanas.
- **Cuantizar sin medir en la tarea concreta.** La pérdida de 4 bits varía mucho según la tarea y el idioma; corre la batería completa antes y después.
- **Ignorar el costo de poseer el modelo.** GPUs, curaduría de datos, reentrenamientos y guardias suman; compáralo con la API antes de decidir.

## Para discutir en equipo

- ¿Qué tareas de nuestros agentes son decisiones cortas, repetitivas y de alto volumen que un modelo chico ajustado podría resolver?
- ¿Tenemos un conjunto de prueba etiquetado por personas para cada tarea que pensamos adaptar? ¿Quién lo mantiene?
- ¿Qué haríamos si el proveedor retira el modelo base sobre el que entrenamos nuestros adaptadores?
- ¿A partir de qué volumen mensual nos conviene un modelo propio frente a la API, considerando también el costo en personas?
- ¿Qué pérdida de calidad estamos dispuestos a aceptar por cuantizar para un cliente on-prem, y cómo se la comunicamos?
