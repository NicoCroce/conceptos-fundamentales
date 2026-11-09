---
slug: fundamentos-ml
titulo: Fundamentos de ML
resumen: Qué significa que un sistema aprenda de datos, cómo se evalúa un modelo sin engañarse y qué decisiones de diseño separan un modelo útil de uno que solo parece bueno.
lectura: 16
---

## La idea central

En el software tradicional, una persona escribe las reglas: "si la distancia es mayor a 10 km y llueve, sumar 15 minutos". En machine learning (ML, aprendizaje automático) invertimos el proceso: le damos al sistema miles de ejemplos del pasado, cada uno con su resultado conocido, y un algoritmo encuentra por sí mismo las reglas que mejor reproducen esos resultados. Lo que obtenemos se llama **modelo**: una función que recibe datos de entrada y devuelve una predicción.

La analogía útil es la de un despachador con diez años de experiencia en Rumbo. Nadie le dio un manual con todas las reglas; vio cientos de miles de entregas y desarrolló intuición: "los viernes a la tarde la zona centro se traba", "este transportista es rápido pero falla en edificios sin portero". Un modelo hace lo mismo, pero con números y sin cansarse. Y comparte los defectos del despachador: si solo vio entregas de verano, va a fallar en invierno; si aprendió de casos mal registrados, va a aprender mal. Casi todo este capítulo trata de esos defectos y de cómo detectarlos antes de que lleguen a producción.

## Conceptos

### Aprender de datos: supervisado, no supervisado y bandits

**Aprendizaje supervisado.** Cada ejemplo histórico trae la respuesta correcta. Para el modelo de ETA, cada pedido entregado tiene sus datos de entrada (distancia, zona, hora) y el resultado real (minutos que tardó). El algoritmo ajusta el modelo para que sus predicciones se acerquen a esos resultados. Es lo que usamos en la mayoría de los sistemas de Rumbo.

**Aprendizaje no supervisado.** No hay respuesta correcta, solo datos. El objetivo es encontrar estructura: agrupar zonas con patrones de demanda parecidos (clustering), detectar pedidos anómalos, reducir cien variables a cinco que resuman lo importante. Sirve para explorar y para generar insumos para otros modelos, pero no responde directamente "¿qué va a pasar?".

**Bandits (aprendizaje por interacción).** Aquí el sistema elige una acción, observa el resultado *solo de esa acción* y aprende sobre la marcha. El nombre viene de las máquinas tragamonedas ("one-armed bandit"): tienes varias palancas, no sabes cuál rinde más, y cada tirada te enseña algo únicamente sobre la palanca que tiraste. El dilema central es **explorar vs. explotar**: si siempre eliges la opción que hoy parece mejor (explotar), nunca descubres si otra era superior; si exploras demasiado, pierdes rendimiento probando opciones malas.

**Ejemplo:** la asignación de pedidos en Rumbo es naturalmente un bandit. Cuando asignamos un pedido al transportista A, vemos si A llegó a tiempo, pero nunca sabremos qué habría hecho B con ese mismo pedido.

**Por qué importa:** confundir un problema de bandit con uno supervisado clásico lleva a modelos que se refuerzan a sí mismos y nunca aprenden sobre las opciones que no eligen (lo retomamos en [Ciclo de vida de modelos](#t/ciclo-vida-modelos)).

### Clasificación vs. regresión

Dentro del aprendizaje supervisado, la distinción principal es qué tipo de respuesta queremos:

- **Clasificación:** la respuesta es una categoría. "¿Este pedido llega a tiempo, sí o no?". El modelo normalmente devuelve una **probabilidad** (0,87) y luego nosotros decidimos a partir de qué valor la tratamos como "sí".
- **Regresión:** la respuesta es un número continuo. "¿Cuántos minutos va a tardar?". El modelo devuelve 34,2 minutos.

**Ejemplo:** para un mismo pedido, el servicio de asignación de Rumbo pide ambas cosas por transportista candidato: un clasificador estima P(llega a tiempo) = 0,91 y un regresor estima ETA = 28 minutos. Son dos modelos distintos, con métricas distintas.

### Features y etiqueta

Las **features** (variables de entrada) son lo que el modelo puede mirar al momento de predecir. La **etiqueta** (label o target) es lo que queremos predecir. Una fila de entrenamiento del modelo de ETA podría verse así:

| distancia_km | zona | hora | lluvia | carga_actual | entregas_previas_zona | minutos_reales |
|---|---|---|---|---|---|---|
| 4,2 | norte | 18 | sí | 3 | 120 | 41 |

Las seis primeras columnas son features; `minutos_reales` es la etiqueta. Un dato clave: cada feature tiene que estar disponible *en el instante de la predicción* con el mismo valor que tendrá en producción. Esa regla, que parece obvia, es la fuente del error más caro del ML (ver fuga de datos, más abajo). El tema de cómo calcular y servir features de forma consistente se desarrolla en [Features y feature stores](#t/feature-stores).

### Train, validation y test: y por qué el corte es temporal

Para saber si un modelo funciona, no podemos evaluarlo con los mismos datos con que aprendió: sería como tomarle a un estudiante el mismo examen que usó para practicar. Por eso dividimos los datos en tres partes:

1. **Train (entrenamiento):** el modelo aprende de acá. Por ejemplo, 70% de los datos.
2. **Validation (validación):** se usa para elegir entre variantes (hiperparámetros, features) y para decidir cuándo parar de entrenar. 15%.
3. **Test (prueba):** se mira una sola vez, al final, para estimar el rendimiento real. 15%. Si se usa repetidamente para tomar decisiones, deja de ser una estimación honesta.

En problemas donde el tiempo importa (casi todos en Rumbo), el corte tiene que ser **temporal**: entrenar con enero a septiembre, validar con octubre, testear con noviembre. Si mezclamos al azar, el modelo ve pedidos del 15 de noviembre durante el entrenamiento y luego "predice" pedidos del 14 de noviembre, aprovechando información del futuro (un corte de ruta, una tormenta, un feriado largo) que en producción jamás tendría.

**Por qué importa:** en producción el modelo siempre predice el futuro con datos del pasado. El corte temporal es la única forma de simular eso offline.

### Overfitting y underfitting

Piensa en dos estudiantes que preparan un examen con 200 ejercicios resueltos:

- El primero **memoriza** las 200 respuestas. En los ejercicios de práctica saca 100%; en el examen, con ejercicios nuevos, saca 55%. Eso es **overfitting** (sobreajuste): el modelo aprendió el ruido y las particularidades de los datos de entrenamiento, no el patrón general.
- El segundo apenas leyó el resumen y aprendió una sola regla ("la respuesta suele ser la opción C"). Saca 40% en práctica y 40% en el examen. Eso es **underfitting** (subajuste): el modelo es demasiado simple para capturar el patrón.

La señal numérica es la brecha entre train y validación. Si el error del modelo de ETA es de 3 minutos en train y 11 minutos en validación, hay overfitting. Si es de 10 minutos en ambos y un modelo más rico logra 6, hay underfitting.

### Regularización

Regularizar es poner un freno a la complejidad del modelo para que no memorice. Las formas concretas dependen del algoritmo:

- En modelos lineales, penalizar coeficientes grandes (L1 o L2): la función de error del modelo suma una penalización por cada peso exagerado, así que solo usa pesos grandes cuando de verdad ayudan.
- En árboles, limitar la profundidad, exigir un mínimo de ejemplos por hoja o usar una tasa de aprendizaje baja.
- En general, más datos y menos features irrelevantes.

**Ejemplo:** un árbol sin límite puede crear una hoja para "pedidos de la calle Rivadavia 1234 los martes", con 2 ejemplos. Exigir al menos 50 ejemplos por hoja obliga al modelo a aprender reglas que se repiten.

### Fuga de datos (data leakage)

Hay fuga cuando una feature contiene, directa o indirectamente, información que no estaría disponible al momento de predecir. El modelo se ve brillante offline y falla en producción.

**Ejemplo:** queremos predecir, al momento de asignar, si la entrega fallará. Alguien agrega la feature `cantidad_intentos_contacto` (cuántas veces el transportista llamó al destinatario). Offline, el modelo pasa de ROC-AUC 0,74 a 0,96. Pero esa feature se calcula *después* de la asignación: un transportista llama tres veces precisamente cuando no encuentra a nadie. El modelo aprendió a reconocer la falla una vez ocurrida, no a anticiparla. En producción, al asignar, el valor siempre es 0, y el modelo vuelve a rendir como antes (o peor).

**Por qué importa:** una mejora offline enorme y repentina es casi siempre una fuga. La pregunta de rigor para cada feature es: "¿con qué timestamp se calculó y es anterior al momento de la predicción?".

### Desbalance de clases

Cuando una clase es mucho más frecuente que la otra, hablamos de desbalance. En Rumbo, aproximadamente 3 de cada 100 entregas fallan. Un modelo puede ignorar la clase rara y aun así parecer excelente en métricas ingenuas. Las herramientas habituales:

- Elegir métricas que miren la clase rara (precision, recall, PR-AUC) en lugar de exactitud.
- Dar más peso a los ejemplos raros durante el entrenamiento (por ejemplo, `scale_pos_weight` en XGBoost).
- Ajustar el umbral de decisión en lugar de quedarse con 0,5.

Ojo: reponderar o sobremuestrear distorsiona las probabilidades. Si luego se usan como probabilidades reales, hay que recalibrar.

### Umbral de decisión y matriz de confusión

Un clasificador devuelve una probabilidad; el negocio necesita una decisión. El **umbral** convierte una en otra: "si P(falla) ≥ 0,5, marcar el pedido como riesgoso". La **matriz de confusión** cuenta los cuatro resultados posibles.

Supongamos 10.000 pedidos de prueba, 300 de los cuales fallaron (3%). Con umbral 0,5:

| | Predicho: falla | Predicho: OK |
|---|---|---|
| **Real: falla** (300) | 180 verdaderos positivos (TP) | 120 falsos negativos (FN) |
| **Real: OK** (9.700) | 270 falsos positivos (FP) | 9.430 verdaderos negativos (TN) |

De ahí salen las métricas:

- **Precision** = TP / (TP + FP) = 180 / 450 = **40%**. De los pedidos que marcamos como riesgosos, 4 de cada 10 realmente fallaron.
- **Recall** = TP / (TP + FN) = 180 / 300 = **60%**. Detectamos 6 de cada 10 fallas.
- **Exactitud** = (TP + TN) / total = 9.610 / 10.000 = **96,1%**.

Si bajamos el umbral a 0,3, marcamos más pedidos: podríamos obtener 240 TP, 60 FN, 760 FP. El recall sube a 80% y la precision baja a 24%. No hay umbral "correcto" en abstracto: depende de cuánto cuesta cada error. Si marcar un pedido riesgoso solo implica enviar un SMS de confirmación al destinatario, un falso positivo es barato y conviene un umbral bajo. Si implica reasignarlo a un transportista más caro, conviene uno alto.

### Baseline

Un **baseline** es la solución más simple razonable, contra la cual se compara todo modelo. Para ETA: "la mediana histórica de minutos para esa zona y franja horaria". Para entrega fallida: "marcar como riesgosos los pedidos a direcciones con fallas previas".

**Ejemplo:** un modelo de ETA con MAE (error absoluto medio) de 7,5 minutos suena bien hasta que descubrimos que la mediana por zona y hora logra 8,1. La mejora real es de 0,6 minutos, y hay que decidir si justifica mantener un modelo.

**Por qué importa:** sin baseline no se puede saber si un modelo aporta. Además, el baseline suele ser el **fallback** natural en producción cuando el modelo no responde.

### Evaluación offline vs. online

- **Offline:** se evalúa con datos históricos, antes de desplegar. Es barato y rápido, pero solo mide lo que el modelo predice, no lo que pasa cuando sus predicciones cambian las decisiones.
- **Online:** se mide en producción con usuarios reales, típicamente con un **A/B test**: una fracción del tráfico (por ejemplo 10%) usa el modelo nuevo y el resto el actual, y se compara una métrica de negocio (tasa de entregas a tiempo).

Las dos pueden discrepar. Un modelo de asignación puede ser mejor prediciendo offline y aun así empeorar el resultado online, porque al cambiar qué transportista recibe qué pedido cambia la carga de todos, y con eso el mundo que el modelo intentaba predecir.

### Tabla de métricas

| Métrica | Qué pregunta responde | Cuándo usarla | Cuidado con |
|---|---|---|---|
| Exactitud (accuracy) | ¿Qué fracción de predicciones acertó? | Clases balanceadas y errores de costo similar | Con desbalance es engañosa: "nunca falla" da 97% |
| Precision | De lo que marqué como positivo, ¿cuánto lo era? | Cuando cada falso positivo cuesta (acciones caras) | Se puede inflar marcando muy pocos casos |
| Recall (sensibilidad) | De los positivos reales, ¿cuántos detecté? | Cuando perder un positivo es grave | Se puede inflar marcando todo |
| F1 | Equilibrio entre precision y recall (media armónica) | Resumen único cuando ambas importan parecido | Oculta cuál de las dos es débil; depende del umbral |
| ROC-AUC | Si tomo un positivo y un negativo al azar, ¿con qué probabilidad el modelo puntúa más alto al positivo? | Comparar capacidad de ordenar, independiente del umbral | Con clases muy raras puede verse alta aunque la precision sea pobre |
| PR-AUC | Área bajo la curva precision-recall: calidad en la clase rara a lo largo de todos los umbrales | Clases desbalanceadas (fallas al 3%) | Su valor "al azar" es la prevalencia (0,03), no 0,5 |
| Calibración | Cuando el modelo dice 0,8, ¿ocurre el 80% de las veces? | Cuando la probabilidad se usa como número (para combinar, priorizar o comunicar riesgo) | Un modelo puede ordenar bien y estar mal calibrado |
| MAE | Error promedio en unidades del problema ("me equivoco 6 minutos en promedio") | Regresión, cuando todos los errores pesan proporcional | No distingue muchos errores chicos de pocos grandes |
| RMSE | Raíz del error cuadrático medio: castiga más los errores grandes | Regresión, cuando un error de 30 minutos es mucho peor que tres de 10 | Muy sensible a outliers (una entrega de 6 horas) |

## Casos prácticos

### El modelo de entrega fallida con 97% de exactitud que no sirve

**Situación:** un primer modelo para predecir entregas fallidas reporta 97,0% de exactitud en test. Al mirar la matriz de confusión, predice "OK" para el 100% de los pedidos. Con 3% de fallas, no hacer nada da exactamente 97% de exactitud.
**Qué se hace:** se descarta la exactitud como métrica principal. Se pasa a PR-AUC para comparar modelos y a precision y recall en un umbral definido con operaciones ("queremos detectar al menos 60% de las fallas con precision mayor a 30%"). Se entrena con mayor peso para la clase rara y se compara contra un baseline de reglas. Un modelo con 96,1% de exactitud pero 60% de recall es mucho más útil que el de 97%.

### Fuga por una feature calculada después de la asignación

**Situación:** al agregar `tiempo_hasta_retiro` (minutos entre la asignación y el retiro en el comercio) el modelo de entrega a tiempo mejora muchísimo offline. Se propone desplegarlo.
**Qué se hace:** se revisa la línea de tiempo de cada feature. El retiro ocurre después de la asignación, así que esa feature no existe cuando el servicio de asignación llama al modelo. Se elimina. Como regla del equipo, cada feature se documenta con su "momento de disponibilidad" y el pipeline de entrenamiento se construye con consultas *point-in-time* (valores tal como estaban en el instante de la predicción), no con el estado actual de la tabla.

### Corte aleatorio vs. temporal

**Situación:** el modelo de ETA da MAE de 5,2 minutos con corte aleatorio. Se despliega y en producción el MAE es de 8,4.
**Qué se hace:** se reevalúa con corte temporal (entrenar hasta agosto, testear septiembre) y el MAE offline sube a 8,1, muy cerca de producción. El corte aleatorio permitía que el modelo viera pedidos del mismo día y la misma zona en train y test, compartiendo condiciones (lluvia, un corte de calle) que en producción son futuras. Desde entonces, toda evaluación de modelos en Rumbo usa corte temporal, y el número reportado es el del corte temporal.

### Asignación como bandit: reservar tráfico para explorar

**Situación:** se incorporan 40 transportistas nuevos. El modelo de asignación no tiene historial de ellos, les asigna probabilidades bajas por precaución y casi nunca los elige. Sin asignaciones, nunca se genera historial: el modelo no aprende y los transportistas nuevos se van.
**Qué se hace:** se trata la asignación como bandit. Se reserva una fracción pequeña de las decisiones (por ejemplo 5%) para exploración: entre los candidatos razonables (que cumplen restricciones mínimas de distancia y capacidad), se elige con algo de azar, favoreciendo a quienes tienen poca información. Cada decisión registra si fue exploratoria y con qué probabilidad se eligió a cada candidato, lo que permite luego evaluar políticas nuevas de forma justa. El costo es un pequeño empeoramiento esperado en ese 5%; el beneficio es un modelo que sigue aprendiendo.

## Errores comunes

- **Reportar exactitud con clases desbalanceadas.** Siempre mira la matriz de confusión y la tasa base; con eventos raros, usa PR-AUC, precision y recall.
- **Celebrar un salto offline grande sin sospechar fuga.** Antes de aceptar la mejora, verifica el timestamp de disponibilidad de cada feature nueva.
- **Cortar los datos al azar en problemas temporales.** Usa corte temporal; si además hay entidades repetidas (mismo comercio, mismo transportista), considera cortar también por entidad.
- **Mirar el test set muchas veces.** Si se usa para elegir, deja de ser test. Reserva un período final que se mire solo para la decisión de lanzamiento.
- **No tener baseline.** Sin una referencia simple, no se puede saber si el modelo aporta ni hay un fallback evidente.
- **Usar el umbral 0,5 por defecto.** El umbral es una decisión de negocio basada en el costo de cada tipo de error; acuérdalo con quien usa la predicción.

## Para discutir en equipo

- Para el modelo de entrega fallida, ¿cuánto cuesta en la práctica un falso positivo y cuánto un falso negativo? ¿Qué umbral implica eso?
- ¿Qué features actuales del modelo de ETA podrían tener fuga sutil (por ejemplo, agregados diarios que incluyen pedidos posteriores a la predicción)?
- ¿Cuánto tráfico estamos dispuestos a dedicar a exploración en asignación, y cómo mediríamos si vale la pena?
- ¿En qué casos una mejora offline no se traduciría en una mejora online para Rumbo?
- ¿Qué baseline usaríamos como fallback si el modelo de ETA dejara de responder?
