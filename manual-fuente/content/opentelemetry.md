---
slug: opentelemetry
titulo: OpenTelemetry y tracing
resumen: Cómo seguir una petición a través de muchos servicios con trazas distribuidas, usando el estándar abierto OpenTelemetry para instrumentar y exportar.
lectura: 13
---

## La idea central

En un sistema con un solo proceso, cuando algo es lento se abre un profiler y se mira. En un sistema distribuido, una petición atraviesa cinco o diez servicios, colas y bases de datos, y ningún log individual cuenta la historia completa. El **tracing distribuido** resuelve esto: cada petición recibe un identificador único que viaja con ella por todos los servicios, y cada servicio registra cuánto tardó su parte. Al final se puede reconstruir el recorrido completo, como el historial de seguimiento de un paquete que muestra cada centro de distribución por el que pasó y cuánto tiempo estuvo en cada uno.

**OpenTelemetry** (abreviado OTel) es el estándar abierto que define cómo generar, propagar y exportar esa información (y también métricas y logs) sin atarse a un proveedor. Instrumentas una vez con OTel y puedes mandar los datos a Jaeger, Tempo, Datadog u otro backend cambiando la configuración, no el código.

## Conceptos

### Los tres pilares

La observabilidad suele describirse con tres tipos de señales que se complementan:

- **Métricas:** números agregados en el tiempo (peticiones por segundo, p99 de latencia, tasa de errores). Son baratas y sirven para detectar que algo anda mal. Ver [Prometheus y Grafana](#t/prometheus-grafana).
- **Logs:** registros de eventos individuales con detalle. Sirven para entender qué pasó en un punto concreto. Ver [Logging estructurado](#t/logging).
- **Trazas:** el recorrido de una petición por el sistema con los tiempos de cada paso. Sirven para entender **dónde** se fue el tiempo o dónde falló algo.

Un flujo típico: la métrica avisa que el p99 subió, la traza muestra qué tramo es lento y el log de ese tramo explica por qué.

### Traza y span

Una **traza** representa una petición completa de punta a punta. Está formada por **spans**: cada span es una operación con nombre, hora de inicio, duración, estado (ok o error) y atributos (pares clave-valor). Los spans se organizan en árbol: cada uno tiene un padre, salvo el span raíz.

Un span típico contiene:

- `trace_id`: identificador de 16 bytes, igual para todos los spans de la traza.
- `span_id`: identificador de 8 bytes, único para este span.
- `parent_span_id`: el span que lo originó.
- nombre, inicio, duración, estado, atributos y eventos (marcas puntuales dentro del span, como "reintento 2").

**Ejemplo:** cascada (*waterfall*) de una petición de asignación en Rumbo. Cada línea es un span; la posición de la barra muestra cuándo empezó y su largo cuánto duró.

```text
                                0    10   20   30   40   50 ms
                                |------------------------|
asignacion: POST /asignar       ========================   48 ms
  validar pedido                =                          2 ms
  feature store: leer features   ==============            28 ms
  aurora: candidatos cercanos    ====                      8 ms
  modelo.Predecir (gRPC)                       ======      12 ms
    modelo: inferencia XGBoost                  ====       8 ms
  kafka: publicar asignado                           ==    4 ms
```

Se lee así: la petición total tardó 48 ms. La lectura de features y la consulta a Aurora corrieron en paralelo, pero la de features tardó 28 ms y bloqueó todo lo siguiente. El modelo, con 12 ms (8 de inferencia y 4 de red y serialización), no es el problema. Con un presupuesto de 50 ms, el feature store se lleva más de la mitad.

**Por qué importa:** sin la traza, alguien podría pasar días optimizando el modelo cuando el cuello de botella está en otro lado.

### Propagación de contexto

Para que los spans de distintos servicios formen una sola traza, el `trace_id` y el `span_id` del padre tienen que viajar con la petición. Eso es la **propagación de contexto**. El estándar más usado es **W3C Trace Context**, que define un header HTTP llamado `traceparent`:

```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01

  00                                 versión del formato
  4bf92f3577b34da6a3ce929d0e0e4736   trace_id (16 bytes en hexadecimal)
  00f067aa0ba902b7                   span_id del padre (8 bytes)
  01                                 flags (01 = esta traza se muestrea)
```

El servicio que recibe la petición lee el header, crea su span como hijo del indicado y, si llama a otro servicio, inyecta un `traceparent` nuevo con su propio `span_id`. En gRPC viaja en los metadatos; las librerías de OTel lo hacen automáticamente.

**Kafka y mensajería:** cuando el servicio de asignación publica el evento "pedido asignado", el contexto viaja en los **headers del mensaje** de Kafka. El consumidor (por ejemplo, el servicio de notificaciones) extrae el contexto y crea su span. Como el consumo puede ocurrir segundos u horas después, muchas veces no se lo modela como hijo sino con un **link** (un vínculo entre spans de trazas distintas), para no tener trazas que duran horas. Ver [Event streaming](#t/event-streaming).

**Ejemplo:** si un servicio intermedio escrito a mano reenvía la petición sin copiar el header, la traza se corta en dos: se verá la primera mitad y una segunda traza "huérfana" sin relación aparente. Es el problema de instrumentación más común.

### OpenTelemetry: API, SDK y Collector

OTel tiene piezas separadas:

- **API:** las interfaces que usa el código para crear spans y métricas. Si no hay SDK configurado, las llamadas no hacen nada, lo que permite que las librerías se instrumenten sin imponer dependencias.
- **SDK:** la implementación que procesa los spans, decide el muestreo y los exporta. Existe para Go, Python, Java, JavaScript y otros lenguajes.
- **Protocolo OTLP:** el formato estándar de envío de datos (sobre gRPC o HTTP).
- **Collector:** un proceso independiente que recibe telemetría, la transforma y la reenvía a uno o varios backends.

Los **backends** son donde se guardan y consultan las trazas:

| Backend | Tipo | Notas |
|---|---|---|
| Jaeger | Open source | Clásico, interfaz de búsqueda y cascada; se autogestiona |
| Grafana Tempo | Open source | Almacena trazas en object storage (S3), barato a escala; se integra con Grafana |
| Datadog APM | Comercial (SaaS) | Todo integrado con métricas y logs; costo por volumen e hosts |
| AWS X-Ray | Gestionado en AWS | Integración nativa con servicios AWS; menos flexible fuera de AWS |

Gracias a OTel, cambiar de backend es cambiar el exporter del Collector, no reinstrumentar los servicios.

### Instrumentación automática y manual

La **instrumentación automática** usa librerías o agentes que envuelven frameworks conocidos (HTTP, gRPC, clientes de base de datos, Kafka) y crean spans sin tocar el código de negocio. En Python y Java puede ser literalmente un agente que se carga al arrancar; en Go se usan wrappers de las librerías (middleware HTTP, interceptores gRPC), porque el lenguaje no permite inyectar código en tiempo de ejecución.

La **instrumentación manual** agrega spans y atributos donde la automática no llega: lógica de negocio importante. En el servicio de asignación, por ejemplo, un span `elegir_transportista` con atributos `candidatos=14`, `zona=norte`, `modelo.version=v42`.

**Ejemplo en Go (manual):**

```go
ctx, span := tracer.Start(ctx, "elegir_transportista")
defer span.End()
span.SetAttributes(
    attribute.Int("candidatos", len(candidatos)),
    attribute.String("zona", pedido.Zona),
)
if err != nil {
    span.RecordError(err)
    span.SetStatus(codes.Error, "sin candidatos")
}
```

**Por qué importa:** la automática da el esqueleto (red y bases de datos); la manual da el significado (qué decidió el sistema y por qué).

### El Collector: filtrar, redactar, muestrear

El Collector es un pipeline de **receivers** (reciben datos), **processors** (los transforman) y **exporters** (los envían). Suele desplegarse como sidecar o DaemonSet en Kubernetes y como gateway central.

Ventajas de pasar todo por el Collector:

- **Filtrar:** descartar spans de health checks que generan miles de trazas inútiles por minuto.
- **Redactar:** borrar o enmascarar atributos con datos personales antes de que salgan del cluster.
- **Muestrear:** decidir qué trazas guardar (ver abajo).
- **Enriquecer:** agregar atributos de entorno (cluster, región, versión).
- **Desacoplar:** las aplicaciones sólo hablan OTLP con el Collector; el destino final se configura en un único lugar.

```yaml
processors:
  attributes/redactar:
    actions:
      - key: destinatario.telefono
        action: delete
      - key: destinatario.email
        action: hash
```

### Muestreo head vs. tail

Guardar el 100% de las trazas es caro. Con 2.000 peticiones por segundo y unos 10 spans por traza, son 20.000 spans por segundo, unos 1.700 millones por día. El **muestreo** decide cuáles se conservan.

- **Head sampling (al inicio):** la decisión se toma cuando empieza la traza, normalmente al azar (por ejemplo, 5%), y se propaga en el flag de `traceparent` para que todos los servicios respeten la misma decisión. Es simple y barato, pero ciego: decide antes de saber si la petición fallará o será lenta. Con 5%, se pierde el 95% de los errores.
- **Tail sampling (al final):** el Collector junta todos los spans de una traza, espera a que termine (por ejemplo, 10 segundos) y entonces decide con reglas: guardar el 100% de las trazas con error, el 100% de las que superan 200 ms y un 2% del resto. Es mucho más útil, pero requiere un Collector con memoria suficiente y que todos los spans de una traza lleguen a la misma instancia (se enruta por `trace_id`).

| Criterio | Head sampling | Tail sampling |
|---|---|---|
| Momento de la decisión | Al iniciar la traza | Cuando la traza terminó |
| Conserva todos los errores | No | Sí, si la regla lo indica |
| Costo de infraestructura | Bajo | Collector con estado y memoria |
| Complejidad | Baja | Media o alta |

### Atributos y datos personales

Los atributos hacen útiles las trazas, pero también son un riesgo: es fácil terminar con nombres, teléfonos o direcciones de destinatarios en el backend de trazas, que suele tener controles de acceso más laxos y retención distinta que la base principal.

Reglas razonables: usar identificadores internos (`pedido.id`, `comercio.id`) y nunca datos de contacto; mantener una lista de atributos permitidos; redactar en el Collector como red de seguridad y revisar periódicamente qué claves aparecen.

### Correlación con logs y métricas

La potencia aparece cuando las tres señales se conectan:

- **Logs con trace id:** si cada línea de log incluye `trace_id` y `span_id`, desde un span se pueden ver los logs exactos de esa petición y viceversa.
- **Exemplars:** una métrica de histograma puede guardar, junto con cada bucket, el `trace_id` de una petición de ejemplo. En Grafana, al ver un pico en el p99, se hace clic en el punto y se abre una traza real que cayó en ese bucket lento.

**Ejemplo:** el panel muestra p99 de 140 ms a las 10:32. El exemplar asociado lleva a la traza `4bf92f...`, donde el span de Aurora tardó 110 ms. Del span se salta a los logs, que muestran "esperando conexión del pool". En tres clics se pasó del síntoma a la causa.

## Casos prácticos

### Sube el p99 de asignación y la traza señala a las features

**Situación:** el p99 del servicio de asignación pasa de 45 ms a 95 ms, por encima del presupuesto de 50 ms. El p50 casi no cambió.

**Qué se hace:** desde el panel de latencia se abre un exemplar del p99. La cascada muestra que el span `feature store: leer features` pasó de 28 ms a 75 ms, y el atributo `features.cantidad` muestra 180 claves en lugar de las 40 habituales. Resulta que una versión nueva del modelo pide features históricas adicionales. Se decide precalcular esas features en el batch nocturno y servirlas en una sola lectura. La traza evitó optimizar el modelo, que nunca fue el problema. Ver [Features y feature stores](#t/feature-stores).

### Un pedido "perdido" que terminó en la DLQ

**Situación:** un comercio reporta que un pedido creado hace dos horas nunca se asignó. En la base, el pedido existe pero sin transportista.

**Qué se hace:** se busca la traza por el atributo `pedido.id`. La traza muestra que la API publicó "pedido creado" en Kafka, el consumidor de asignación lo leyó (span vinculado por link), falló tres veces deserializando un campo de dirección con un carácter inesperado y lo mandó a la DLQ (*dead letter queue*, cola donde van los mensajes que no se pudieron procesar). El span final tiene estado error y el evento `enviado_a_dlq`. Sin propagación en los headers de Kafka, el rastro se habría cortado en la publicación. Se corrige el parser, se reprocesa la DLQ y se agrega una alerta por mensajes en la DLQ mayores a cero durante 10 minutos.

### El costo de las trazas se dispara

**Situación:** la factura hipotética del backend de trazas se triplicó tras instrumentar todos los servicios. Se guarda el 100% de las trazas.

**Qué se hace:** primero se filtran en el Collector los spans de health checks y readiness probes (alrededor del 30% del volumen en este caso hipotético). Luego se configura tail sampling: 100% de errores, 100% de trazas con duración mayor a 100 ms, 100% de las que tocan el endpoint de reasignación manual (poco tráfico, mucho valor) y 3% del resto. El volumen baja en más del 90% y se conservan prácticamente todas las trazas que alguien buscaría durante un incidente.

### Email del destinatario en un atributo

**Situación:** revisando trazas, alguien nota que un span del servicio de notificaciones tiene el atributo `destinatario.email` con direcciones reales. Lleva tres semanas en producción.

**Qué se hace:** se trata como incidente de datos personales: se agrega de inmediato una regla de redacción en el Collector para eliminar el atributo, se corrige el código, y se coordina con el equipo responsable de privacidad el borrado de los datos ya almacenados (según el backend, puede requerir borrar por rango de tiempo). Como prevención, se agrega una lista de atributos permitidos en el Collector, un test en CI que falla si el código usa claves de atributo con `email`, `telefono` o `direccion`, y una revisión mensual de claves nuevas.

## Errores comunes

- **Instrumentar sólo un servicio.** Una traza que se corta en el primer salto aporta poco; la propagación de contexto tiene que funcionar en todos los servicios, incluidos los consumidores de Kafka.
- **Head sampling bajo y después buscar errores.** Con 1% de muestreo al inicio, el 99% de las trazas con error se pierde; para depurar fallas, tail sampling o reglas que conserven errores.
- **Atributos de alta cardinalidad en métricas derivadas.** En trazas, el `pedido.id` como atributo es útil; si se convierte en label de una métrica, explota la cardinalidad.
- **Datos personales en atributos.** Usar identificadores internos y redactar en el Collector como segunda barrera.
- **Spans demasiado finos.** Un span por cada iteración de un bucle genera miles de spans por traza, ruido y costo; los spans van en operaciones con significado.
- **No conectar trazas con logs.** Sin `trace_id` en los logs, se pierde el salto más útil durante un incidente.

## Para discutir en equipo

- ¿Qué atributos de negocio deberían tener los spans del servicio de asignación para que una traza responda "por qué se eligió este transportista"?
- ¿Cómo modelamos en trazas un flujo que pasa por Kafka y puede tardar minutos: hijos o links?
- ¿Qué reglas de tail sampling reflejan lo que de verdad buscamos durante un incidente?
- ¿Cómo verificamos de forma continua que no se filtran datos personales en la telemetría?
- ¿Qué parte de la telemetría de las instalaciones on-prem de clientes podemos recibir y cuál debe quedarse allí?
