---
slug: event-streaming
titulo: Event streaming
resumen: Cómo funcionan Kafka y sistemas similares, qué garantías de orden y entrega ofrecen, y cómo diseñar productores y consumidores confiables.
lectura: 14
---

## La idea central

Un sistema de event streaming es un **log**: una lista de eventos a la que solo se agregan elementos al final, que se conserva durante un tiempo y que muchos lectores pueden recorrer, cada uno a su ritmo y desde donde quiera. Cuando el servicio de pedidos publica `pedido_entregado`, no le importa quién lo lee: seguimiento, notificaciones, el pipeline de features de ML y analítica lo consumen de forma independiente. Si mañana aparece un quinto consumidor, el productor no cambia.

La diferencia con una cola de mensajes tradicional es la clave para entender todo lo demás. En una cola, leer un mensaje lo consume: desaparece para los demás. En un stream, leer no borra nada; cada consumidor solo recuerda hasta dónde leyó. Eso permite tener varios consumidores sobre los mismos eventos y volver atrás (*replay*) para reprocesar después de corregir un bug.

## Conceptos

### Tópico, partición y offset

Un **tópico** es una categoría de eventos, por ejemplo `pedidos`. Para escalar, el tópico se divide en **particiones**: logs independientes que pueden vivir en distintos brokers y leerse en paralelo. Cada evento dentro de una partición tiene un **offset**, un número secuencial que indica su posición (0, 1, 2...). El offset es local a la partición: el offset 500 de la partición 3 no tiene relación con el 500 de la partición 7.

```text
Tópico: pedidos (4 particiones)          clave = pedido_id

  P0: [0][1][2][3][4][5][6][7]   ->
  P1: [0][1][2][3][4][5]         ->
  P2: [0][1][2][3][4][5][6]      ->
  P3: [0][1][2][3][4]            ->

Consumer group "seguimiento" (2 instancias)
  instancia A  <- P0, P1    offsets confirmados: P0=7, P1=5
  instancia B  <- P2, P3    offsets confirmados: P2=6, P3=3   (lag P3 = 1)

Consumer group "features-ml" (4 instancias)
  instancia 1  <- P0        offset P0=4   (lag 3)
  instancia 2  <- P1        offset P1=5
  instancia 3  <- P2        offset P2=2   (lag 4)
  instancia 4  <- P3        offset P3=4

Cada grupo lee todos los eventos y lleva sus propios offsets.
Dentro de un grupo, cada partición la lee una sola instancia.
```

### Orden por partición y elección de clave

Kafka garantiza orden **solo dentro de una partición**. No hay orden global entre particiones. El productor elige la partición a partir de una **clave**: todos los eventos con la misma clave caen en la misma partición (por hash) y, por lo tanto, se leen en el orden en que se escribieron.

Elegir la clave es elegir qué eventos necesitan orden relativo. Para el tópico de pedidos, la clave natural es `pedido_id`: `creado`, `asignado`, `retirado` y `entregado` del mismo pedido se procesan en orden, que es lo que seguimiento necesita. Si la clave fuera aleatoria, seguimiento podría procesar `entregado` antes que `retirado`. La tensión: una clave de alta cardinalidad reparte bien la carga; una clave de baja cardinalidad (`comercio_id`, `zona_id`) da orden por comercio o zona pero arriesga particiones calientes.

Detalle importante: cambiar la cantidad de particiones de un tópico existente cambia el mapeo clave-partición, y durante la transición se pierde el orden para las claves que se movieron. Por eso conviene dimensionar las particiones con margen desde el inicio.

### Consumer groups y paralelismo máximo

Un **consumer group** es un conjunto de instancias que se reparten las particiones de un tópico: cada partición la lee exactamente una instancia del grupo. Distintos grupos son independientes y cada uno ve todos los eventos.

La consecuencia directa: **el paralelismo máximo de un grupo es la cantidad de particiones**. Con 12 particiones, la instancia número 13 queda ociosa. Si notificaciones necesita más throughput y ya tiene 12 instancias, agregar pods no ayuda; hay que aumentar particiones o paralelizar dentro de cada instancia (con cuidado de no romper el orden por clave).

Cuando una instancia entra o sale del grupo (un deploy, un crash, el autoscaling) se produce un **rebalanceo**: las particiones se redistribuyen y, según la configuración, el consumo se pausa unos segundos. Deploys frecuentes con rebalanceos largos son una causa común de picos de lag.

### Commit de offsets y at-least-once

El consumidor registra (*commit*) el offset hasta el que procesó, para retomar desde ahí si se reinicia. **Cuándo** se hace el commit define la semántica:

- **Commit después de procesar:** si el consumidor se cae entre procesar y confirmar, al reiniciar vuelve a procesar ese tramo. Ningún evento se pierde, pero puede haber duplicados: **at-least-once**. Es lo habitual.
- **Commit antes de procesar:** si se cae después del commit y antes de procesar, el evento se salta. Es **at-most-once**.

El auto-commit periódico de muchos clientes mezcla ambos riesgos, porque confirma en segundo plano lo que ya se leyó aunque no se haya terminado de procesar. Lo robusto es commit manual tras procesar y consumidores idempotentes que deduplican por `evento_id` (ver [Sistemas distribuidos](#t/sistemas-distribuidos)). Kafka ofrece transacciones para el caso "leer de un tópico, escribir en otro", pero en cuanto el efecto sale de Kafka (una base, un SMS), la idempotencia del consumidor sigue siendo necesaria.

### Retención y replay

Los eventos se conservan según una **política de retención**: por tiempo (7 días), por tamaño, o indefinidamente. También existe la **compactación**, que conserva solo el último evento de cada clave; sirve para tópicos que representan estado actual ("última posición de cada transportista").

La retención habilita el **replay**: mover los offsets de un grupo hacia atrás (a una fecha o un offset) y reprocesar. Es una herramienta poderosa para recuperarse de bugs, pero tiene condiciones: los efectos del consumidor tienen que ser idempotentes o reversibles, y los efectos externos (notificaciones a destinatarios) deben poder desactivarse durante el replay.

### Lag del consumidor

El **lag** es la distancia entre el último offset escrito en una partición y el último offset confirmado por un grupo. Es la métrica más importante de un consumidor, y conviene expresarla también en **tiempo** (antigüedad del evento más viejo sin procesar), porque 10.000 eventos de lag pueden ser 2 segundos en un tópico intenso o 3 horas en uno tranquilo.

El lag se mide por partición, no solo en total: un lag total bajo puede esconder una partición atascada (por un mensaje veneno o una partición caliente). La alerta se define sobre la antigüedad en el peor caso, con un umbral derivado del uso: seguimiento tolera segundos; analítica, horas.

### Schema registry

Productores y consumidores evolucionan por separado, igual que con las APIs. Un **schema registry** guarda los esquemas de cada tópico (en Avro, Protobuf o JSON Schema) con sus versiones, y valida en el momento de producir que cada cambio respete una regla de compatibilidad. Con compatibilidad *backward*, un consumidor con el esquema nuevo puede leer eventos escritos con el anterior. Cada mensaje lleva el identificador de su esquema, así el consumidor sabe cómo deserializarlo.

Sin registry, un productor que cambia un campo de entero a texto rompe a todos los consumidores en el siguiente evento, y como los eventos quedan retenidos, los rompe también a los que hagan replay. Las reglas son las mismas que en [gRPC y REST](#t/grpc-rest): agregar campos opcionales es seguro, cambiar tipos o semántica no.

### CDC: Change Data Capture

CDC captura los cambios de una base de datos leyendo su log de transacciones (en PostgreSQL, el WAL a través de replicación lógica) y los publica como eventos. Herramientas como Debezium lo hacen sin tocar el código de la aplicación.

Sirve para dos cosas distintas. Una es implementar el patrón outbox: CDC lee la tabla `outbox` y publica sus filas, lo que garantiza que el evento sale si y solo si la transacción se confirmó. La otra es replicar tablas hacia el lago de datos o analítica. Para la segunda hay que tener presente que publicar cambios de tablas convierte el **esquema interno** de la base en un contrato público: renombrar una columna rompe consumidores. Por eso, para eventos de dominio, se prefiere la outbox con un esquema diseñado para consumir.

### Procesamiento por ventanas

Muchas features y métricas son agregaciones en el tiempo: "entregas a tiempo por zona en los últimos 5 minutos". Los motores de stream processing, como Flink o Kafka Streams, mantienen estado y calculan esas agregaciones a medida que llegan los eventos. Los tipos de ventana:

- **Tumbling (fija):** intervalos sin solapamiento, por ejemplo 12:00-12:05, 12:05-12:10.
- **Hopping o sliding (deslizante):** intervalos de 5 minutos que avanzan cada 1 minuto, con solapamiento.
- **Session:** se agrupan eventos separados por menos de un tiempo de inactividad.

La sutileza central es el **tiempo del evento** frente al **tiempo de procesamiento**. Un evento `entregado` a las 12:04:50 puede llegar a las 12:05:30 porque el teléfono del transportista estuvo sin señal. Si se agrupa por la hora de llegada, cae en la ventana equivocada. Los motores usan **watermarks**: una estimación de "ya no deberían llegar eventos anteriores a T", que decide cuándo cerrar una ventana, más un margen de *lateness* permitida para eventos tardíos.

### Cola frente a stream

Una cola (SQS, RabbitMQ) reparte **tareas**: cada mensaje lo procesa un trabajador, se borra al confirmarlo, se pueden reintentar mensajes individuales y escalar trabajadores sin límite de particiones. Un stream distribuye **hechos**: muchos consumidores, orden por clave, replay. Si el uso es "procesar este trabajo una vez" (generar la etiqueta de envío en PDF), una cola es más simple. Si es "esto pasó y a varios les interesa", un stream.

| Aspecto | Kafka / MSK | Kinesis Data Streams | SQS |
|---|---|---|---|
| Modelo | Log particionado | Log particionado (shards) | Cola de tareas |
| Múltiples consumidores independientes | Sí, sin costo extra de lectura | Sí, pero comparten el límite de lectura por shard salvo enhanced fan-out | No (un mensaje, un consumidor; se combina con SNS para difundir) |
| Orden | Por partición | Por shard | No (estándar) o por grupo (FIFO, con menor throughput) |
| Replay | Sí, según retención (puede ser indefinida) | Sí, retención limitada (de horas a un máximo de alrededor de un año) | No |
| Paralelismo | Particiones | Shards | Prácticamente ilimitado |
| Operación | MSK reduce trabajo pero hay que dimensionar brokers y particiones | Totalmente administrado | Totalmente administrado |
| Ecosistema | Amplio: Connect, Streams, Flink, schema registry, Debezium | Integrado con AWS | Integrado con AWS |
| On-prem | Sí (Kafka autogestionado) | No | No |
| Uso en Rumbo | Eventos de pedidos, CDC, features en tiempo real | Alternativa para flujos simples dentro de AWS | Trabajos puntuales, reintentos diferidos |

## Casos prácticos

### Eventos de pedidos para cuatro consumidores

**Situación:** el tópico `pedidos` alimenta a seguimiento (necesita orden por pedido y latencia de segundos), notificaciones (no debe enviar SMS duplicados), el pipeline de features de ML (agrega por zona) y analítica (carga al lago de datos cada pocos minutos).

**Qué se hace:** el servicio de pedidos publica vía outbox con clave `pedido_id`, esquema Protobuf en el schema registry y un `evento_id` único por evento. Cada consumidor tiene su propio consumer group, sus propias alertas de lag con umbrales distintos y su propia estrategia: notificaciones deduplica por `evento_id` en una tabla con restricción única; seguimiento descarta eventos con una versión de pedido menor a la ya aplicada; analítica escribe archivos idempotentes por rango de offsets. El tópico se crea con 24 particiones aunque hoy alcanzarían 8, para no tener que cambiar el mapeo de claves pronto.

### Feature en tiempo real: entregas a tiempo por zona

**Situación:** el modelo de ETA mejora si conoce la tasa de entregas a tiempo de la zona en los últimos minutos (si hay un embotellamiento, cae). Se quiere calcularla en ventanas de 5 minutos.

**Qué se hace:** un job de Flink consume `pedidos`, filtra `entregado` y `fallido`, y agrupa por `zona_id` en ventanas deslizantes de 5 minutos que avanzan cada minuto, usando el **tiempo del evento**. El watermark tolera 2 minutos de retraso; los eventos más tardíos se cuentan en una métrica y se descartan para esta feature. El resultado se escribe en el almacén online de features con su marca de tiempo. El servicio de asignación lee el valor y, si tiene más de 10 minutos de antigüedad o no existe, usa el promedio histórico de la zona para esa franja horaria (ver [Features y feature stores](#t/feature-stores)). El mismo cálculo se reproduce en batch sobre los eventos históricos para generar los datos de entrenamiento, con la misma definición de ventana.

### Lag: un pico de demanda y una partición caliente

**Situación:** un viernes a las 20:00 los pedidos se triplican y el lag de notificaciones pasa de 1 segundo a 12 minutos: los destinatarios reciben "tu pedido está en camino" cuando ya llegó. El grupo tiene 12 instancias y el tópico, 12 particiones. Al mismo tiempo, en el tópico auxiliar `eventos_comercio` (clave `comercio_id`, usado para métricas por comercio) una sola partición acumula horas de lag mientras las demás están al día: un comercio grande que acaba de sumarse genera el 35% de los eventos.

**Qué se hace:** mirar el lag **por partición** distingue los dos problemas. En notificaciones el lag es parejo en todas: falta capacidad. Agregar pods no ayuda porque el paralelismo ya está al máximo; el análisis muestra que cada evento espera ~40 ms al proveedor de SMS de forma secuencial. Se procesa en paralelo dentro de cada instancia manteniendo el orden por clave (un worker por `pedido_id`), confirmando el offset solo hasta el último evento procesado de forma contigua, y se descartan los avisos de "en camino" de pedidos ya entregados: un aviso obsoleto es peor que ninguno. En `eventos_comercio` el lag se concentra en una partición: más instancias tampoco ayudan, porque una clave siempre cae en una sola partición. Se revisa qué orden se necesita realmente: las métricas por comercio solo requieren orden dentro de cada pedido, así que se migra a un tópico nuevo con clave `pedido_id` y la agregación por comercio pasa al motor de stream con estado. Si el orden por comercio fuera imprescindible, la alternativa sería salar la clave (`comercio_id#0` a `comercio_id#7`) y recombinar después. En ambos tópicos se alerta por antigüedad máxima del lag por partición.

### Replay tras un bug

**Situación:** un deploy del consumidor de features introdujo un bug que, durante 6 horas, contó los pedidos fallidos como entregados a tiempo. La feature quedó inflada y el modelo subestimó demoras.

**Qué se hace:** se corrige el bug y se despliega. Luego se detiene el grupo, se mueven sus offsets al instante previo al deploy defectuoso (con la herramienta de reset de offsets por fecha) y se reprocesa. Como el job escribe la feature por `(zona_id, ventana)` sobrescribiendo, el replay es idempotente y corrige los valores. Antes de hacerlo se verifica que la retención del tópico cubre el período. Si el consumidor hubiera tenido efectos externos (enviar SMS), el replay se haría en un grupo nuevo con esos efectos desactivados.

## Errores comunes

- **Suponer orden global en un tópico.** Solo hay orden por partición; si el orden importa, debe estar en la clave.
- **Agregar instancias por encima de la cantidad de particiones.** Quedan ociosas; se dimensionan particiones con margen o se paraleliza dentro de la instancia.
- **Auto-commit con procesamiento asíncrono.** Se confirman offsets de eventos no procesados y se pierden en un reinicio; se confirma después de procesar.
- **Medir lag solo en total y en cantidad de eventos.** Esconde particiones atascadas; se alerta por la antigüedad máxima por partición.
- **Publicar tablas por CDC como si fueran eventos de dominio.** El esquema interno se vuelve contrato; para dominio se usa outbox con esquema propio.
- **Agrupar por tiempo de llegada.** Los eventos tardíos caen en ventanas equivocadas; se usa tiempo del evento con watermarks.

## Para discutir en equipo

- Para cada tópico nuestro, ¿qué orden necesitan realmente sus consumidores y la clave actual lo garantiza?
- ¿Cuál de nuestros consumidores no es idempotente, y qué pasaría si mañana hacemos un replay de un día?
- ¿Qué umbral de lag, en tiempo, es aceptable para cada consumidor, y quién recibe la alerta?
- ¿Qué flujos tratamos como stream y serían más simples como cola, o al revés?
- ¿Cómo garantizamos que las features calculadas en streaming y las calculadas en batch para entrenamiento coincidan?
