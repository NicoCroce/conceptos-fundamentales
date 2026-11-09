---
slug: monitoreo-modelos
titulo: Monitoreo de modelos
resumen: Cómo detectar que un modelo en producción se degrada antes de que lo noten los usuarios, vigilando su salud técnica, sus datos y sus resultados.
lectura: 15
---

## La idea central

Cuando un servicio tradicional se rompe, suele hacer ruido: lanza excepciones, devuelve errores 500, la latencia se dispara y alguien recibe una alerta. Un modelo de ML degradado, en cambio, falla en silencio. Sigue respondiendo en 8 ms, con código 200 y con números que parecen razonables. El modelo de ETA de Rumbo puede seguir diciendo "34 minutos" aunque la realidad ya sea "52 minutos", y ningún dashboard de infraestructura se va a poner rojo por eso.

Una analogía útil es un GPS con el mapa desactualizado. El aparato funciona perfecto, calcula rutas al instante y habla con voz segura, pero el mundo cambió: abrieron una autopista, cerraron un puente. El problema no está en el GPS, está en la distancia entre lo que aprendió y lo que pasa hoy. Monitorear un modelo es medir esa distancia de forma continua: vigilar si los datos que recibe se parecen a los de entrenamiento, si sus predicciones cambian de forma rara y, cuando llegan las respuestas reales, si sigue acertando.

## Conceptos

### Por qué un modelo se degrada en silencio

Un modelo es una función aprendida a partir de una foto del pasado. El modelo de ETA vio, por ejemplo, un año de entregas y aprendió que 5 km en la zona centro un martes a las 15 h suelen tomar unos 28 minutos. Esa relación no es una ley física: depende del tráfico, de los transportistas, de los comercios y de cómo se registran los datos. Cuando cualquiera de esas cosas cambia, el modelo sigue aplicando la regla vieja.

Hay tres motivos por los que nadie se entera enseguida:

1. **No hay error técnico.** El modelo siempre devuelve un número. No existe un "NullPointerException" de la mala predicción.
2. **La respuesta correcta llega tarde.** Para saber si el ETA de un pedido estaba bien, hay que esperar a que se entregue. Para saber si una entrega fue realmente fallida, a veces hay que esperar días.
3. **Los promedios esconden problemas.** Un error medio global de 6 minutos puede convivir con una zona donde el error es de 20 minutos, si esa zona es solo el 5 % del volumen.

**Por qué importa:** sin monitoreo específico de ML, el primer aviso de degradación suele ser una queja de un comercio o una caída en la tasa de entregas a tiempo, semanas después de que empezó el problema.

### Las tres capas del monitoreo

Conviene pensar el monitoreo en tres capas, de la más rápida y barata a la más lenta y valiosa:

- **Salud técnica:** latencia (p50, p99), tasa de errores, timeouts, uso de CPU y memoria del servicio que sirve el modelo, versión del modelo cargada. Es el monitoreo clásico de cualquier servicio y se hace con las mismas herramientas (ver [Prometheus y Grafana](#t/prometheus-grafana)).
- **Datos:** qué entra al modelo y qué sale. Distribución de cada feature, porcentaje de nulos, valores fuera de rango, distribución de las predicciones. Se puede medir en tiempo real porque no necesita la respuesta correcta.
- **Resultado:** qué tan bien acierta el modelo contra la realidad. Error absoluto medio (MAE) del ETA, tasa de acierto en entregas a tiempo, impacto en el negocio. Es la capa definitiva, pero depende de las etiquetas, que llegan tarde.

**Ejemplo:** en el servicio de asignación, la capa técnica dice "p99 de 41 ms, dentro del presupuesto de 50 ms". La capa de datos dice "la feature `distancia_km` tiene la misma distribución que la semana pasada". La capa de resultado dice "el MAE del ETA de ayer fue 6,4 minutos, contra 6,1 de referencia". Las tres juntas dan una imagen completa.

**Por qué importa:** cada capa detecta problemas que las otras no ven. Un modelo puede tener latencia perfecta y estar recibiendo basura.

### Data drift: cambian los datos de entrada

El **data drift** (deriva de datos) ocurre cuando la distribución de las features que recibe el modelo cambia respecto de la que vio al entrenar. La relación entre entradas y salida puede seguir siendo la misma; lo que cambia es la mezcla de casos.

**Ejemplo:** Rumbo firma con un comercio grande de muebles. Antes, el 10 % de los pedidos superaba los 10 km; ahora es el 20 %. El modelo vio pocos pedidos largos, así que en esa franja tiene menos experiencia y probablemente más error, aunque la física de manejar 15 km no haya cambiado.

**Por qué importa:** el data drift es una señal temprana. No prueba que el modelo empeoró, pero dice "estás operando en una región donde el modelo sabe menos".

### Concept drift: cambia la relación

El **concept drift** (deriva de concepto) ocurre cuando cambia la relación entre las entradas y la respuesta correcta. Las features pueden verse idénticas y, sin embargo, la misma combinación de entradas ahora produce otro resultado.

**Ejemplo:** la municipalidad cambia el sentido de varias calles en la zona sur. Un pedido de 4 km a las 18 h, que antes tardaba 25 minutos, ahora tarda 33. La distribución de distancias y horarios no cambió en nada; cambió lo que significan.

**Por qué importa:** el concept drift casi nunca se ve en la capa de datos. Solo aparece cuando llegan las etiquetas y el error sube. Por eso no alcanza con monitorear entradas.

### Prediction drift: cambian las salidas

El **prediction drift** es el cambio en la distribución de lo que el modelo predice. Es útil porque se mide al instante y resume muchas features en una sola señal.

**Ejemplo:** el ETA promedio predicho para la zona norte pasa de 31 a 24 minutos de un día para otro, sin ningún evento que lo justifique. Antes de esperar las entregas reales, eso ya merece una mirada: tal vez una feature dejó de llegar o cambió de unidad.

**Por qué importa:** cuando las etiquetas tardan, el prediction drift es uno de los mejores indicadores tempranos de que algo se movió.

### Tabla: tipos de degradación

| Tipo | Qué cambia | Ejemplo en Rumbo | Cómo se detecta |
|---|---|---|---|
| Data drift | La distribución de las entradas | Más pedidos de más de 10 km por un comercio nuevo | PSI o KS por feature contra una referencia |
| Concept drift | La relación entre entradas y resultado | Cambio de sentido de calles: misma distancia, más minutos | Error real (MAE) cuando llegan las etiquetas, por segmento |
| Prediction drift | La distribución de las salidas | ETA medio de la zona norte cae de 31 a 24 min sin motivo | PSI sobre las predicciones, comparación con días similares |
| Problema de calidad de datos | Valores rotos, nulos, unidades | Una feature llega siempre en cero | Reglas de validación: nulos, rangos, varianza cero |
| Cambio de población | Quién usa el sistema | Expansión a una ciudad nueva | Monitoreo por segmento y alertas de categorías nuevas |

### PSI: cuánto se movió una distribución

El **PSI** (Population Stability Index, índice de estabilidad de población) es una forma simple de medir cuánto cambió la distribución de una variable entre un período de referencia (por ejemplo, el set de entrenamiento) y un período actual (por ejemplo, la última semana).

El procedimiento es:

1. Dividir la variable en rangos (buckets), usualmente de 5 a 10, definidos con los datos de referencia.
2. Calcular qué porcentaje de casos cae en cada rango en la referencia (E, esperado) y en el período actual (A, actual).
3. Para cada rango, calcular `(A − E) × ln(A / E)`.
4. Sumar todos los rangos.

**Ejemplo:** la feature `distancia_km` del modelo de ETA, con cuatro rangos.

| Rango | Referencia (E) | Actual (A) | A − E | ln(A/E) | Aporte |
|---|---|---|---|---|---|
| 0 a 2 km | 30 % | 20 % | −0,10 | −0,405 | 0,041 |
| 2 a 5 km | 40 % | 35 % | −0,05 | −0,134 | 0,007 |
| 5 a 10 km | 20 % | 25 % | 0,05 | 0,223 | 0,011 |
| más de 10 km | 10 % | 20 % | 0,10 | 0,693 | 0,069 |
| **Total** | | | | | **0,128** |

Un PSI de 0,13 indica un cambio moderado. Si la semana siguiente el reparto fuera 12 %, 30 %, 28 % y 30 %, el PSI subiría a 0,44: un cambio grande.

La regla práctica más usada es:

- **PSI < 0,1:** estable, no hace falta hacer nada.
- **Entre 0,1 y 0,2:** cambio moderado, observar y ver si persiste.
- **PSI > 0,2:** investigar. No significa automáticamente "reentrenar", significa "alguien tiene que entender qué pasó".

Un detalle práctico: si un rango tiene 0 % en alguno de los dos períodos, el logaritmo explota. Se reemplaza el cero por un valor muy chico (por ejemplo 0,0001). Y los umbrales son convenciones, no leyes: conviene calibrarlos mirando cuánto se mueve el PSI en semanas normales.

**Por qué importa:** el PSI convierte "la distribución se ve distinta" en un número comparable entre features y en el tiempo, que se puede graficar y sobre el que se puede alertar.

### Test de Kolmogorov-Smirnov

El **test de Kolmogorov-Smirnov (KS)** compara dos distribuciones numéricas sin necesidad de definir rangos. Toma la distribución acumulada de cada muestra (qué fracción de valores es menor o igual a cada punto) y mide la mayor distancia vertical entre las dos curvas. Esa distancia máxima se llama estadístico D y va de 0 (idénticas) a 1 (totalmente distintas).

**Ejemplo:** en la referencia, el 70 % de los pedidos tiene menos de 5 km. Esta semana, solo el 55 %. Si ese es el punto de mayor diferencia, D = 0,15.

El test además da un p-valor, que indica qué tan probable es ver esa diferencia por azar. Acá hay una trampa: con muestras grandes, como los cientos de miles de pedidos diarios de Rumbo, cualquier diferencia minúscula da un p-valor bajísimo y el test "detecta drift" todos los días. En la práctica conviene mirar el tamaño de D (por ejemplo, alertar si D > 0,1) en lugar del p-valor, o usar muestras de tamaño fijo.

**Por qué importa:** KS es estándar y no depende de cómo se elijan los rangos, pero hay que usarlo con criterio para no generar ruido.

### Etiquetas tardías e indicadores aproximados

La **etiqueta** es la respuesta correcta: los minutos reales que tardó la entrega, o si la entrega fue exitosa. En Rumbo, el ETA real se conoce en minutos u horas, pero que una entrega fue fallida a veces se confirma días después (el destinatario reclama, el comercio revisa, soporte cierra el caso). Durante ese tiempo no se puede calcular el error real.

Mientras tanto se usan **indicadores aproximados** (proxies): señales disponibles antes que correlacionan con la calidad del modelo.

- Distribución de las predicciones (prediction drift).
- Señales tempranas del negocio: reasignaciones de pedidos, intentos de entrega reportados por el transportista, consultas al asistente de soporte del tipo "¿dónde está mi pedido?".
- Error parcial: para pedidos ya entregados, aunque sean una fracción, calcular el error sobre esa muestra sabiendo que puede estar sesgada (se entregan antes los pedidos cortos).

**Por qué importa:** si el equipo solo mira métricas que tardan una semana, reacciona una semana tarde. Los proxies permiten sospechar temprano y confirmar después.

### Calidad de datos

Una gran parte de las "degradaciones de modelo" son en realidad datos rotos. Las validaciones mínimas por feature son:

- **Nulos:** porcentaje de valores faltantes y su variación. Pasar de 1 % a 15 % de nulos en `clima` es una señal clara.
- **Rangos:** distancias negativas, horas mayores a 23, cargas de 400 pedidos para un transportista.
- **Varianza y cardinalidad:** una feature numérica que de pronto tiene siempre el mismo valor, o una categórica que pasa de 40 zonas a 3.
- **Tipos y unidades:** metros donde se esperaban kilómetros, UTC donde se esperaba hora local.

El caso más traicionero es **la feature que se rellena en silencio**. Muchos pipelines, ante un dato faltante, ponen un valor por defecto (0, el promedio, "desconocido") para no romper. El modelo nunca falla, pero recibe un dato falso como si fuera verdadero. Por eso hay que medir no solo los nulos, sino también cuántas veces se usó el valor por defecto. La relación con cómo se calculan y sirven las features se ve en [Features y feature stores](#t/feature-stores).

**Por qué importa:** estos problemas se detectan en minutos con reglas simples y explican una parte grande de los incidentes reales.

### Monitoreo por segmento

Las métricas globales promedian todo y esconden los problemas locales. Hay que cortar las métricas por los segmentos que importan: zona, franja horaria, tipo de comercio, tipo de vehículo, cliente grande.

**Ejemplo:** el MAE global del ETA es 6,2 minutos, igual que el mes pasado. Pero cortado por zona, la zona norte pasó de 6 a 14 minutos. Como la zona norte es el 5 % de los pedidos, en el promedio global solo suma 0,4 minutos, que se confunden con el ruido.

Cuidado con el exceso: 40 zonas por 24 horas por 5 tipos de vehículo son 4.800 combinaciones, muchas con pocos datos y mucho ruido. Conviene elegir pocos cortes con sentido de negocio y exigir un volumen mínimo para alertar.

**Por qué importa:** los usuarios no viven el promedio. El comercio de la zona norte vive su zona.

### Alertas accionables y disparadores de reentrenamiento

Una alerta útil responde tres preguntas: qué pasó, a quién le toca y qué hacer. "PSI de `carga_transportista` = 0,35" sin contexto termina ignorada. Una alerta accionable sería: "El 100 % de los valores de `carga_transportista` es 0 desde las 14:10; dueño: equipo de asignación; runbook: verificar el productor de eventos de carga". La forma de organizar guardias y runbooks se trata en [On-call, runbooks e incidentes](#t/on-call).

Reglas prácticas:

- Separar severidades: un problema de calidad de datos que rompe el modelo es una página urgente; un PSI moderado sostenido es un ticket para revisar en horario laboral.
- Exigir persistencia: alertar si el PSI supera 0,2 durante tres días seguidos, no por un pico de una hora.
- Anotar eventos esperados (feriados, campañas) para no alertar por ellos.

Los **disparadores de reentrenamiento** definen cuándo se entrena un modelo nuevo. Hay tres enfoques, que se suelen combinar:

1. **Por calendario:** cada semana o cada mes. Simple y predecible.
2. **Por desempeño:** cuando el error real supera un umbral, por ejemplo MAE > 7,5 minutos durante una semana.
3. **Por drift sostenido:** cuando varias features importantes superan PSI 0,2 durante varios días.

Reentrenar no es gratis ni siempre correcto: si la causa es un dato roto, reentrenar enseña al modelo a convivir con el error. El flujo completo de reentrenamiento y validación se ve en [Ciclo de vida de modelos](#t/ciclo-vida-modelos).

### Herramientas

- **Evidently:** librería open source en Python que genera reportes y tests de drift, calidad de datos y desempeño comparando un dataset de referencia con uno actual. Útil para empezar rápido y para correr en jobs batch.
- **Arize:** plataforma comercial de observabilidad de ML. Recibe predicciones y etiquetas, calcula drift y desempeño por segmento, y ayuda a investigar qué features explican la caída.
- **SageMaker Model Monitor:** servicio de AWS que captura las entradas y salidas de un endpoint de SageMaker, calcula una línea base a partir del set de entrenamiento y corre comparaciones programadas. Conveniente si el modelo ya se sirve en SageMaker.
- **Grafana (con Prometheus u otra fuente):** no calcula drift por sí mismo, pero es donde muchos equipos grafican las métricas que calculan sus propios jobs (PSI por feature, MAE por zona) y configuran las alertas junto con las métricas técnicas.

Una combinación habitual: métricas técnicas y de calidad en Prometheus y Grafana, y un job diario (con Evidently o código propio) que calcula PSI y MAE por segmento y publica los resultados como métricas.

## Casos prácticos

### La carga del transportista llega siempre en cero

**Situación:** el equipo de flota migra el sistema que publica la carga de cada transportista. El nuevo productor publica el campo con otro nombre. El pipeline de features no lo encuentra y, para no romper, rellena `carga_actual_transportista` con 0. Desde ese momento el modelo cree que todos los transportistas están libres, y el servicio de asignación empieza a darle pedidos a transportistas que ya tienen seis encima. La latencia es perfecta y no hay errores.

**Qué se hace:** la capa de datos lo detecta en minutos con dos reglas: la feature tiene varianza cero y el contador de "valor por defecto usado" pasa de 0,5 % a 100 %. La alerta es urgente y va al equipo de asignación. La mitigación inmediata es corregir el mapeo del campo o, si tarda, volver a una política de asignación sin modelo. No se reentrena: el modelo está bien, los datos están mal. Como prevención, se agrega un contrato de esquema entre el productor de eventos y el pipeline de features.

### Obras viales en la zona oeste

**Situación:** empiezan obras que cortan dos avenidas de la zona oeste durante tres meses. A los dos días, el MAE del ETA en esa zona sube de 6 a 11 minutos. Las distribuciones de las features no cambiaron: es concept drift, y no es culpa del modelo, que no tenía cómo saberlo.

**Qué se hace:** el monitoreo por segmento lo detecta y la alerta va como ticket, no como emergencia. A corto plazo se puede aplicar un ajuste explícito y documentado (por ejemplo, sumar un factor a los ETA de la zona) mientras duren las obras. A mediano plazo se reentrena con ventanas más recientes o se agrega una feature que capture el estado del tráfico. Lo importante es registrar el evento para que, cuando terminen las obras, alguien revise y quite el ajuste.

### Entregas fallidas que se confirman días después

**Situación:** el modelo de asignación estima la probabilidad de entrega exitosa, pero muchas entregas fallidas se confirman recién entre 3 y 7 días después, cuando soporte cierra el caso. Mirar la tasa de acierto de ayer da una imagen incompleta y engañosamente buena.

**Qué se hace:** se separan dos vistas. Una vista temprana con proxies: distribución de la probabilidad predicha, reintentos reportados por el transportista y consultas de destinatarios en el asistente de soporte. Una vista madura que calcula el desempeño real solo para pedidos con más de 7 días, cuando la etiqueta ya es confiable. Las alertas de desempeño usan la vista madura; las de sospecha, la temprana.

### Temporada alta con drift esperado

**Situación:** en la semana previa a las fiestas, el volumen de pedidos se triplica, la carga media de los transportistas sube y el PSI de varias features pasa de 0,3. Todos los dashboards de drift se ponen rojos.

**Qué se hace:** el drift es esperado y no es una falla. Se compara contra la misma temporada del año anterior en lugar de contra el último mes, se anotan las fechas en el calendario del monitoreo para silenciar las alertas de drift de entrada y se mantienen activas las de calidad de datos y desempeño por segmento, que son las que indican un problema real. Si el modelo nunca vio una temporada así, conviene validar su error con datos de la temporada anterior antes de que empiece.

## Errores comunes

- **Monitorear solo la salud técnica.** Latencia y errores no dicen nada sobre si el modelo acierta. Hay que agregar al menos la capa de datos desde el primer día.
- **Alertar sobre cada PSI alto.** Genera fatiga y alertas ignoradas. Hay que exigir persistencia, priorizar features importantes y separar ticket de página urgente.
- **Confiar en el p-valor de KS con millones de filas.** Siempre da "significativo". Hay que mirar el tamaño del efecto (D) o usar muestras de tamaño fijo.
- **Reentrenar automáticamente ante cualquier drift.** Si la causa es un dato roto, el modelo nuevo aprende el error. Primero se diagnostica, después se reentrena.
- **No medir los valores por defecto.** Una feature rellenada en silencio no aparece como nula. Hay que contar cuántas veces se usó el valor de relleno.
- **Mirar solo el promedio global.** Los problemas reales suelen estar en un segmento chico. Hay que cortar por zona, franja y tipo de cliente.

## Para discutir en equipo

- ¿Qué tres features del modelo de ETA monitorearíamos primero y con qué regla para cada una?
- ¿Cuánto tarda hoy en llegar la etiqueta de cada modelo de Rumbo y qué proxies tenemos mientras tanto?
- ¿Quién es el dueño de una alerta de drift: el equipo de ML, el dueño del servicio que produce el dato o el que consume la predicción?
- ¿Qué eventos esperados (temporadas, campañas, obras) deberíamos registrar en un calendario para no confundirlos con fallas?
- ¿En qué casos preferiríamos desactivar el modelo y usar una regla simple en lugar de esperar a reentrenar?
