---
slug: feature-stores
titulo: Features y feature stores
resumen: Cómo convertir datos crudos en señales útiles para un modelo y cómo servirlas igual al entrenar y en producción sin filtrar el futuro.
lectura: 13
---

## La idea central

Un modelo no ve "pedidos" ni "transportistas": ve columnas de números. Una **feature** (característica) es cada una de esas columnas, la señal que el modelo usa para predecir. "Distancia en km", "pedidos entregados por este transportista en los últimos 7 días" o "hora local del pedido" son features. La calidad de un modelo depende mucho más de qué features recibe y de que sean correctas que del algoritmo elegido.

El problema es que las features se calculan dos veces: una al armar el dataset de entrenamiento, mirando el pasado en lote, y otra en producción, en el momento de cada predicción y con pocos milisegundos. Si esos dos cálculos no dan lo mismo, el modelo se entrena con una realidad y opera con otra. Un **feature store** es la pieza de infraestructura que existe para que las features se definan una vez, se calculen de forma consistente y se puedan consultar tanto para entrenar como para servir. Una analogía: es como la cocina central de una cadena de restaurantes, donde las salsas se preparan con una sola receta y se reparten a cada local, en lugar de que cada local improvise la suya.

## Conceptos

### Feature engineering

El **feature engineering** es el trabajo de transformar datos crudos en señales que el modelo pueda aprovechar. Los datos crudos de Rumbo son eventos en Kafka (pedido creado, asignado, entregado) y tablas en Aurora. El modelo de ETA necesita algo más digerido. Las transformaciones más comunes son:

- **Agregados por ventana:** resumir lo que pasó en un período. "Pedidos entregados por el transportista en los últimos 7 días", "tiempo medio de entrega en la zona en la última hora".
- **Ratios:** dividir dos cantidades para obtener una tasa comparable. "Entregas a tiempo / entregas totales en 30 días" es más útil que dos conteos sueltos, porque un transportista con 10 de 10 y otro con 300 de 400 se vuelven comparables (100 % contra 75 %).
- **Codificación de categorías:** los modelos trabajan con números, así que "zona norte" hay que convertirla. Se puede usar one-hot (una columna 0/1 por zona) o target encoding (reemplazar la zona por el tiempo medio histórico de entrega en ella).
- **Hora local y calendario:** un timestamp en UTC no dice mucho. "Hora local = 18", "día de semana = viernes", "es feriado = sí" capturan los patrones de tráfico.
- **Desvíos:** comparar un valor con lo normal. "Carga actual del transportista menos su carga media" dice si hoy está más ocupado que de costumbre.

**Ejemplo:** a partir de un único evento "pedido creado" con origen, destino y timestamp UTC, se derivan `distancia_km = 6,3`, `zona_destino = norte`, `hora_local = 18`, `dia_semana = 5`, `entregas_zona_ultima_hora = 142`, `tasa_a_tiempo_transportista_30d = 0,91` y `desvio_carga = +2`.

**Por qué importa:** un modelo con buenas features y un algoritmo simple casi siempre le gana a un algoritmo sofisticado con features pobres. Más contexto en [Fundamentos de ML](#t/fundamentos-ml).

### Corrección temporal (point-in-time)

Al entrenar, cada fila del dataset representa un momento del pasado: "el pedido 812 se creó el 3 de marzo a las 14:00 y tardó 37 minutos". Las features de esa fila deben tener **el valor que tenían en ese momento**, no el de hoy. Si no, el modelo aprende con información del futuro que en producción nunca va a tener. Esto se llama **fuga de datos** (data leakage) temporal, y la técnica para evitarlo es el **join point-in-time** (unión en un punto del tiempo).

Una línea de tiempo lo aclara. Tomemos la feature `tasa_a_tiempo_transportista_30d` del transportista T7:

```
   1 mar          3 mar 14:00          10 mar           hoy
     |                 |                  |               |
  tasa = 0,93    pedido 812 creado   tasa = 0,78     tasa = 0,80
                 (momento de la         (tuvo una
                  predicción)          mala semana)
```

Para el pedido 812, el valor correcto es 0,93, el último conocido antes del 3 de marzo a las 14:00. Si el dataset se arma con el valor de hoy (0,80) o con uno posterior (0,78), el modelo "sabe" algo que todavía no había pasado.

El join point-in-time funciona así: para cada fila con su timestamp de predicción, busca en el historial de la feature el valor más reciente **anterior o igual** a ese timestamp. Requiere que las features se guarden con historial (valor más fecha de validez), no solo el valor actual.

**Por qué importa:** la fuga temporal produce modelos que se ven excelentes en la evaluación offline y decepcionan en producción. Es de los errores más comunes y más difíciles de ver.

### Training-serving skew

El **training-serving skew** (desfase entre entrenamiento y servicio) es cualquier diferencia entre cómo se calcula una feature al entrenar y cómo se calcula al servir. Las causas típicas son:

- Dos implementaciones: el pipeline de entrenamiento en Python con pandas y el de serving reescrito en Go dentro del servicio de asignación.
- Unidades o zonas horarias distintas.
- Ventanas que se cortan distinto: "últimos 7 días" con días calendario en un lado y 168 horas corridas en el otro.
- Manejo distinto de faltantes: el entrenamiento descarta filas con nulos, el serving las rellena con 0.

**Ejemplo:** en entrenamiento, `entregas_zona_ultima_hora` cuenta entregas completadas. En el servicio, alguien la implementa contando eventos "entregado", que incluyen duplicados por reintentos de Kafka. En producción el valor es un 8 % más alto en promedio y el modelo interpreta que las zonas están más activas de lo que están.

**Por qué importa:** el skew no rompe nada visible; degrada las predicciones en silencio. Se detecta comparando valores de features registrados en serving con los recalculados offline para los mismos pedidos, una práctica que conecta con [Monitoreo de modelos](#t/monitoreo-modelos).

### Feature store: qué es y qué partes tiene

Un **feature store** centraliza la definición, el cálculo, el almacenamiento y el acceso a las features. Sus piezas principales son:

- **Almacén offline:** guarda el historial completo de cada feature, con timestamps. Suele vivir en S3 (archivos Parquet) o en un data warehouse. Se usa para armar datasets de entrenamiento con joins point-in-time. Es barato y lento: consultas de segundos o minutos.
- **Almacén online:** guarda solo el valor más reciente de cada feature por entidad (por transportista, por zona). Vive en una base de baja latencia como Redis o DynamoDB. Se usa en producción: el servicio de asignación pide las features del transportista T7 y las obtiene en 2 a 5 ms.
- **Catálogo:** registro de qué features existen, qué significan, quién es el dueño, de qué datos vienen y qué modelos las usan. Evita que tres equipos calculen "tasa de entregas a tiempo" de tres maneras.
- **Linaje:** rastro de dónde sale cada feature y qué la consume. Si cambia el tópico de Kafka de eventos de entrega, el linaje dice qué features y qué modelos se ven afectados.
- **Reutilización:** una feature definida para el modelo de ETA puede usarla el de pronóstico de demanda sin reimplementarla.

```
  FUENTES                      FEATURE STORE                         CONSUMIDORES

  Kafka (eventos)    --+
  Aurora (pedidos)   --+-->  Definiciones de features
  S3 (históricos)    --+     (código único + catálogo + linaje)
                                        |
                                        v
                              Cálculo batch y streaming
                                        |
                       +----------------+----------------+
                       |                                 |
                       v                                 v
              Almacén offline                    Almacén online
              (S3 Parquet, historial            (Redis/DynamoDB,
               con timestamps)                   último valor)
                       |                                 |
                       | join point-in-time              | lectura en 2-5 ms
                       v                                 v
              Entrenamiento                      Servicio de asignación
              (datasets históricos)              (Go, presupuesto ~50 ms)
```

La clave es que el mismo cálculo alimenta los dos almacenes. Eso reduce mucho el training-serving skew, porque ya no hay dos implementaciones.

**Por qué importa:** cuando hay varios modelos y equipos, el feature store evita duplicar trabajo, asegura consistencia y hace auditable qué datos usa cada modelo.

### Tabla: tipos de features

| Tipo | Ejemplo en Rumbo | Frescura típica | Dónde se calcula |
|---|---|---|---|
| Estática | Tipo de vehículo del transportista, zona del comercio | Cambia rara vez (días o meses) | Batch, copiada al almacén online |
| Agregada batch | Tasa de entregas a tiempo del transportista en 30 días | Horas (recalculada cada noche o cada hora) | Job batch sobre S3 o el warehouse |
| Tiempo real | Carga actual del transportista, entregas en la zona en los últimos 15 min | Segundos | Procesamiento de streams sobre Kafka |
| De la petición | Distancia del pedido, hora local, peso declarado | Instantánea (viene con la consulta) | En el servicio, al momento de predecir |

Las features de la petición no se guardan en el almacén online porque no existen hasta que llega el pedido; se calculan en el servicio. Aun así, conviene que su código esté compartido con el entrenamiento para no introducir skew.

### Batch vs. streaming

Las features agregadas se pueden calcular de dos formas:

- **Batch:** un job corre cada cierto tiempo (cada noche, cada hora), lee el historial y recalcula. Es simple, barato y fácil de depurar. El costo es la frescura: una feature recalculada a las 2:00 tiene, a las 20:00, 18 horas de antigüedad.
- **Streaming:** un proceso consume eventos de Kafka y actualiza la feature a medida que llegan (con Flink, Kafka Streams o Spark Structured Streaming). Da frescura de segundos, pero es más caro, más difícil de operar y más difícil de reproducir exactamente para el historial offline. Más sobre el modelo de eventos en [Event streaming](#t/event-streaming).

**Ejemplo:** "tasa a tiempo en 30 días" cambia poco de una hora a otra; batch nocturno alcanza. "Carga actual del transportista" cambia cada vez que toma o entrega un pedido; si se calculara una vez por noche sería inútil.

**Por qué importa:** cada feature en streaming es un sistema en producción más que hay que mantener. Conviene reservar el streaming para las features donde la frescura realmente mejora la predicción.

### Frescura y valores vencidos

La **frescura** (freshness) es cuánto tiempo pasó desde que se actualizó un valor. Cada feature debería tener una frescura máxima aceptable, o TTL (time to live): pasado ese tiempo, el valor se considera vencido.

**Ejemplo:** la carga actual del transportista tiene TTL de 2 minutos. Si el servicio de asignación lee un valor actualizado hace 25 minutos, ese valor probablemente es incorrecto: el transportista pudo haber tomado o entregado varios pedidos. Usarlo como si fuera actual es peor que reconocer que no se sabe.

Qué hacer con un valor vencido depende de la feature: tratarlo como faltante, usar un valor por defecto razonable o usar un modelo de respaldo que no dependa de esa feature. Lo importante es decidirlo de forma explícita y medir cuántas veces pasa.

### Valores faltantes

Una feature puede faltar porque la entidad es nueva (un transportista que empezó hoy no tiene historial), porque falló una fuente o porque el valor venció. Hay varias estrategias:

- **Valor por defecto:** 0, la media o la mediana. Simple, pero puede confundir al modelo si el 0 tiene significado real.
- **Indicador de faltante:** agregar una columna `tasa_a_tiempo_es_nula = 1` para que el modelo aprenda a tratar ese caso aparte.
- **Dejar el nulo:** modelos como XGBoost manejan nulos de forma nativa y aprenden hacia qué lado mandarlos (ver [XGBoost y scikit-learn](#t/xgboost)).

La regla de oro es la consistencia: el faltante se debe tratar igual al entrenar y al servir. Si en entrenamiento los transportistas nuevos tenían nulo y en producción reciben 0, hay skew.

### El costo de cada feature

Cada feature tiene un costo que no aparece en el notebook donde se probó: cómputo para calcularla, almacenamiento online, latencia al leerla, monitoreo, un dueño que responda cuando se rompe y riesgo de que su fuente cambie. Una feature en streaming que aporta 0,05 minutos de mejora en el MAE del ETA probablemente no justifica su operación.

**Ejemplo:** el equipo evalúa agregar "nivel de tráfico en tiempo real" desde un proveedor externo. Mejora el MAE de 6,2 a 5,6 minutos (un 10 %), pero cuesta una integración nueva, una dependencia externa en el camino crítico y un plan de respaldo si el proveedor no responde. Se justifica. Otra feature que baja el MAE de 6,2 a 6,18 no.

**Por qué importa:** los modelos acumulan features con el tiempo y casi nunca se quitan. Revisar periódicamente la importancia de cada una ayuda a podar las que no aportan.

### Herramientas

- **Feast:** feature store open source. Define features en código Python, materializa a un almacén online (Redis, DynamoDB) y hace joins point-in-time desde el offline. No calcula transformaciones complejas por sí mismo: se apoya en jobs externos. Buena opción para empezar con control total.
- **Tecton:** plataforma comercial gestionada, creada por personas que trabajaron en feature stores internos de grandes empresas. Incluye cálculo batch y streaming, monitoreo y catálogo. Menos trabajo operativo, más costo y dependencia del proveedor.
- **SageMaker Feature Store:** servicio de AWS con almacén online y offline (sobre S3). Se integra bien si el resto del stack ya está en SageMaker. Relevante para Rumbo porque la infraestructura está en AWS.
- **Databricks Feature Store / Feature Engineering:** integrado con Unity Catalog y el ecosistema Databricks. Natural si el equipo de datos ya trabaja ahí.

Para clientes on-prem, solo las opciones open source como Feast se pueden instalar en su infraestructura sin depender de un servicio en la nube.

## Casos prácticos

### Skew por unidades: kilómetros al entrenar, metros al servir

**Situación:** el pipeline de entrenamiento calcula `distancia` en kilómetros. El servicio de asignación, escrito en Go, la calcula con una librería de geolocalización que devuelve metros, y nadie la convierte. En producción, un pedido de 5 km llega como 5.000. El modelo, que nunca vio distancias mayores a 60, trata todos los pedidos como "muy largos" y los ETA se disparan en todas las zonas a la vez.

**Qué se hace:** la mitigación inmediata es convertir las unidades y redesplegar. La corrección de fondo es eliminar la doble implementación: la feature se define una sola vez (en el feature store o en una librería compartida) con la unidad en el nombre (`distancia_km`). Además se agregan validaciones de rango en serving (distancia mayor a 200 km es imposible en última milla) y una comparación diaria de distribuciones entre los valores servidos y los de entrenamiento.

### Dataset de entrenamiento con valores actuales para pedidos viejos

**Situación:** para entrenar un modelo nuevo, alguien arma el dataset con un join simple entre la tabla de pedidos de 2025 y la tabla `transportistas`, que guarda la tasa de entregas a tiempo actual. El modelo da un MAE offline de 4,1 minutos contra 6,2 del actual, una mejora espectacular. En producción, el MAE es 6,8.

**Qué se hace:** el problema es fuga temporal. Para pedidos de hace un año se usó la tasa de hoy, que refleja cómo terminó ese año el transportista, información que no existía en el momento de cada pedido. Se rehace el dataset con un join point-in-time contra el historial de la feature. Si ese historial no existe, se empieza a guardar desde ya y, mientras tanto, se calcula la feature hacia atrás desde los eventos crudos. Como regla, una mejora offline demasiado buena para ser verdad se investiga antes de celebrarla.

### ¿Invertir ya en un feature store?

**Situación:** Rumbo tiene hoy dos modelos en producción (ETA y probabilidad de entrega a tiempo) que comparten unas 15 features, y un tercero en camino. Alguien propone adoptar un feature store completo.

**Qué se hace:** se evalúa el dolor real. Con pocos modelos y un equipo chico, un feature store gestionado puede ser más costo y complejidad que beneficio. Un paso intermedio razonable es una librería compartida de definiciones de features, usada por el entrenamiento y por el servicio, más una tabla de historial en S3 para joins point-in-time y Redis para los valores online. Si el número de modelos crece, aparecen features duplicadas entre equipos o el skew empieza a causar incidentes, se migra a Feast o SageMaker Feature Store. La decisión se revisa con criterios concretos: cuántos modelos, cuántas features compartidas, cuántos incidentes de skew por trimestre.

### Stream atrasado y valor por defecto

**Situación:** el consumidor de Kafka que actualiza `carga_actual_transportista` se atrasa 20 minutos por un pico de eventos. El almacén online sigue respondiendo, pero con valores viejos. El servicio de asignación no sabe que están vencidos y asigna como si los transportistas estuvieran menos cargados.

**Qué se hace:** cada valor online se guarda con su timestamp de actualización y el servicio compara con el TTL de 2 minutos. Si el valor está vencido, se trata como faltante: se usa un valor por defecto acordado (la carga media del transportista en esa franja horaria) junto con un indicador de "valor estimado", que el modelo ya vio en entrenamiento. Se emite una métrica de cuántas lecturas usaron el valor por defecto y una alerta sobre el lag del consumidor. Así el sistema degrada de forma controlada y visible, en lugar de decidir con datos viejos sin que nadie lo sepa.

## Errores comunes

- **Armar datasets con el valor actual de las features.** Produce fuga temporal y métricas offline infladas. Hay que guardar historial y usar joins point-in-time.
- **Reimplementar las features en el servicio de producción.** Cada reimplementación es una fuente de skew. Hay que compartir el código o la definición entre entrenamiento y serving.
- **Usar streaming para todo.** Encarece y complica sin beneficio cuando la feature cambia lento. Batch alcanza para la mayoría de los agregados largos.
- **Ignorar la frescura.** Un valor online sin timestamp no permite saber si está vencido. Hay que guardar cuándo se actualizó y definir un TTL por feature.
- **Tratar los faltantes distinto en cada lado.** Si el entrenamiento descarta nulos y el serving pone 0, el modelo ve casos que nunca aprendió. La política de faltantes debe ser única.
- **No poner unidades en los nombres.** `distancia` invita al error; `distancia_km` lo previene.

## Para discutir en equipo

- ¿Qué features de nuestros modelos se calculan hoy en dos lugares distintos y cómo verificaríamos que dan lo mismo?
- ¿Cuál es el TTL razonable para cada feature en tiempo real del servicio de asignación y qué hacemos cuando vence?
- ¿Qué señales concretas nos dirían que llegó el momento de adoptar un feature store completo?
- ¿Cómo resolveríamos las features para un cliente on-prem que no puede usar servicios gestionados de AWS?
- ¿Qué feature actual eliminaríamos si tuviéramos que justificar el costo de cada una?
