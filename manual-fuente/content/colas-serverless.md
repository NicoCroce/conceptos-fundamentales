---
slug: colas-serverless
titulo: Colas y serverless en AWS
resumen: Cómo SQS, SNS, EventBridge, Lambda y Step Functions desacoplan servicios, absorben picos y orquestan tareas largas, incluidas las de agentes con LLMs.
lectura: 16
---

## La idea central

Una cola es una sala de espera entre quien pide un trabajo y quien lo hace. El productor deja el mensaje y sigue con lo suyo; los trabajadores (*workers*) lo toman cuando tienen capacidad. Si llegan 3.000 pedidos de trabajo en cinco minutos, nadie tiene que procesarlos en esos cinco minutos: la cola los guarda y los workers avanzan a su ritmo. Así un pico deja de ser una caída y se convierte en una demora controlada.

Los servicios *serverless* de AWS completan la idea: **Lambda** ejecuta código en respuesta a eventos sin que administremos servidores, y **Step Functions** encadena pasos largos con reintentos, esperas y aprobaciones humanas. Para sistemas con agentes esto es central. Una tarea de agente que tarda minutos, llama a un LLM con límites de uso y ejecuta herramientas con efectos reales (enviar un SMS, reasignar un pedido) no debería vivir dentro de una solicitud HTTP. Debería ser un trabajo asíncrono, con concurrencia limitada, reintentos que no repitan efectos y, cuando corresponda, una persona que apruebe antes de actuar.

## Conceptos

### Por qué una cola: desacoplar y absorber picos

Con una llamada síncrona, si el clasificador de tickets tarda o falla, la API de soporte tarda o falla. Una cola desacopla en el **tiempo** (el productor no espera a que el trabajo termine) y en la **capacidad** (el productor puede generar trabajo más rápido que los workers durante un rato, y la cola absorbe la diferencia).

**Ejemplo:** un lunes a las 9:00 llegan 3.000 tickets de soporte en 5 minutos (10 por segundo). Clasificar un ticket con el LLM tarda unos 4 segundos. El proveedor del LLM tiene un límite hipotético de 600 solicitudes por minuto (10 por segundo).

1. **Síncrono:** la API intenta clasificar 10 tickets por segundo, cada uno ocupando una conexión 4 segundos: unas 40 llamadas simultáneas. Cualquier reintento empuja por encima del límite del proveedor, aparecen errores 429 y los comercios ven fallar la carga de tickets.
2. **Con cola y 20 workers concurrentes:** cada worker procesa 1 ticket cada 4 segundos, en total 5 por segundo (300 por minuto, la mitad del límite). En los 5 minutos del pico se procesan 1.500 y quedan 1.500 en la cola, que se vacían en otros 5 minutos. El último ticket se clasifica unos 10 minutos después de llegar, pero ninguno falla.

**Por qué importa:** la cola cambia la pregunta de "¿cuánto aguantamos en el pico?" a "¿cuánta demora aceptamos?", y esa segunda pregunta se responde con una métrica: la antigüedad del mensaje más viejo.

### SQS estándar y FIFO

**SQS** (Simple Queue Service) es la cola administrada de AWS. Tiene dos tipos:

- **Estándar:** throughput prácticamente ilimitado, orden aproximado (*best effort*) y entrega **al menos una vez**: un mensaje puede llegar dos veces, en casos raros.
- **FIFO:** orden estricto y deduplicación. El orden se garantiza dentro de cada **grupo de mensajes** (`MessageGroupId`): los mensajes del mismo grupo se entregan en orden y de a uno por vez, mientras que grupos distintos se procesan en paralelo. La deduplicación descarta un mensaje con el mismo `MessageDeduplicationId` enviado dentro de una ventana de 5 minutos. El costo es un throughput menor: del orden de cientos de mensajes por segundo por cola, más con envío en lotes o con el modo de alto rendimiento.

**Ejemplo:** las acciones del agente de operaciones sobre un mismo pedido (proponer reasignación, reasignar, notificar) deben ejecutarse en orden. Con FIFO y `MessageGroupId = pedido_id`, cada pedido avanza en orden y 500 pedidos distintos avanzan en paralelo. Si se usara un único grupo para todo, la cola entera procesaría de a un mensaje.

**Por qué importa:** la deduplicación de FIFO cubre solo reenvíos del productor dentro de 5 minutos; no protege de que el consumidor procese dos veces. La idempotencia del consumidor sigue siendo necesaria en ambos tipos.

### Visibility timeout y entrega al menos una vez

En SQS, leer un mensaje no lo borra. Al recibirlo, el mensaje queda **invisible** para los demás consumidores durante el **visibility timeout** (por defecto 30 segundos, hasta 12 horas). El ciclo es:

1. El worker recibe el mensaje; empieza a correr el visibility timeout.
2. Procesa el trabajo.
3. Si termina bien, **borra** el mensaje explícitamente (`DeleteMessage`).
4. Si falla, o si se cae, o si tarda más que el visibility timeout, el mensaje vuelve a ser visible y otro worker lo recibe.

El paso 4 es la fuente de la entrega al menos una vez y también de la trampa más común: si el procesamiento dura más que el visibility timeout, el mensaje reaparece **mientras el primer worker sigue trabajando**, y dos workers hacen lo mismo.

**Ejemplo de dimensionamiento:** un worker que resume casos con el LLM tarda 8 segundos en p50, 40 segundos en p99 y hasta 90 segundos cuando el agente encadena varias herramientas. Un visibility timeout de 30 segundos duplicaría más del 1% de los trabajos. Se fija en 180 segundos (holgura sobre el máximo observado) y, para los casos excepcionales, el worker extiende la invisibilidad a mitad de camino con `ChangeMessageVisibility`, como un latido. El costo de un valor alto es que, si un worker se cae, el mensaje tarda 3 minutos en reintentarse.

### Long polling

Con **long polling** (`WaitTimeSeconds` hasta 20 segundos), la llamada de recepción espera hasta que llegue un mensaje o venza el plazo, en lugar de volver vacía al instante. Con 50 workers preguntando cada 100 ms son 500 solicitudes por segundo, casi todas vacías en horas tranquilas; con esperas de 20 segundos, del orden de 2,5 por segundo. Casi siempre conviene activarlo.

### Dead-letter queues y redrive

Una **dead-letter queue** (DLQ) es otra cola SQS a la que van los mensajes que fallaron demasiadas veces. Se configura con una **redrive policy**: `maxReceiveCount = 5` significa que, al quinto recibo sin borrado, el mensaje se mueve a la DLQ. El concepto general está en [Patrones de resiliencia](#t/resiliencia); en SQS los detalles prácticos son:

- El conteo es de **recibos**, no de errores: un mensaje que reaparece por visibility timeout corto también suma.
- La retención de la DLQ debe ser mayor que la de la cola original (la retención máxima es de 14 días), porque la antigüedad del mensaje se cuenta desde que se envió por primera vez.
- SQS permite **redrive** de vuelta: mover los mensajes de la DLQ a la cola original una vez corregido el bug.
- Una alarma sobre la cantidad de mensajes visibles en la DLQ, con un dueño definido, es obligatoria.

### SNS y fan-out

**SNS** (Simple Notification Service) es publicación-suscripción: un mensaje publicado en un **tópico** se entrega a todos sus suscriptores. El patrón **fan-out** combina SNS con varias colas SQS: el productor publica una vez y cada consumidor tiene su propia cola, con su propio ritmo, sus reintentos y su DLQ.

```text
                         +--> SQS soporte-clasificar  --> workers del clasificador
[API de soporte] --> SNS +--> SQS soporte-metricas    --> Lambda de métricas
  ticket_creado          +--> SQS soporte-agente      --> agente de seguimiento
                              (filtro: prioridad = alta)
```

Las suscripciones admiten **políticas de filtro**: la cola del agente solo recibe tickets de prioridad alta. Si el agente se cae una hora, su cola acumula mensajes sin afectar a los otros dos consumidores.

### EventBridge: bus, reglas, schedules y pipes

**EventBridge** es un **bus de eventos** con ruteo por contenido. Los eventos son JSON; las **reglas** comparan patrones sobre sus campos (`"source": ["rumbo.pedidos"], "detail": {"estado": ["fallido"], "zona": ["norte"]}`) y envían lo que coincide a uno o varios destinos: SQS, Lambda, Step Functions, otro bus, APIs externas. Recibe además eventos de los propios servicios de AWS (una instancia que cambia de estado, un objeto nuevo en S3).

Dos piezas más, a alto nivel:

- **Scheduler:** tareas programadas, recurrentes (`cron`) o únicas ("dentro de 2 horas, revisar si el pedido se entregó"), sin un servidor con cron.
- **Pipes:** conectan una fuente (una cola SQS, un stream) con un destino, con filtro y transformación opcionales en el medio, sin escribir el código de pegamento.

### Cuál elegir: SQS, SNS, EventBridge o Kafka

| Necesidad | SQS | SNS | EventBridge | Kafka (MSK) |
|---|---|---|---|---|
| Modelo | Cola de tareas | Pub/sub, entrega push | Bus con ruteo por contenido | Log particionado |
| Consumidores por mensaje | Uno | Todos los suscriptores | Todos los destinos de las reglas que coinciden | Todos los grupos |
| Ruteo | No | Filtros por atributos o cuerpo | Patrones ricos sobre el JSON | Por tópico; el filtrado lo hace el consumidor |
| Retención y replay | Hasta 14 días, sin replay | No retiene | Archivo y replay opcionales | Según retención, replay nativo |
| Orden | FIFO por grupo | FIFO por grupo (tópicos FIFO) | No garantizado | Por partición |
| Operación | Nula | Nula | Nula | Dimensionar brokers y particiones |
| Uso típico en Rumbo | Trabajos de LLM, tareas del agente | Difundir `ticket_creado` | Reaccionar a eventos de AWS, schedules, integración entre equipos | Eventos de pedidos de alto volumen, features en tiempo real |

La regla práctica: **SQS** para "que alguien haga este trabajo una vez"; **SNS + SQS** para "que varios hagan su trabajo con este hecho"; **EventBridge** para rutear por contenido entre muchos productores y consumidores con poco volumen por regla; y Kafka cuando hay volumen alto, orden por clave y necesidad de replay, como se explica en [Event streaming](#t/event-streaming).

### Lambda: modelo, cold starts y concurrencia

**Lambda** ejecuta una función cuando llega un evento: una solicitud HTTP, un mensaje de SQS, una regla de EventBridge. Cada instancia de la función atiende un evento por vez; si llegan 50 eventos simultáneos, Lambda crea hasta 50 instancias (entornos de ejecución). El costo depende de la cantidad de invocaciones y del tiempo de ejecución según la memoria asignada.

- **Cold start:** la primera invocación en un entorno nuevo suma la inicialización (descargar el código, arrancar el runtime, crear clientes): de decenas de milisegundos a varios segundos. Para un worker de cola es irrelevante; para una API con presupuesto de 50 ms, no. Se mitiga con paquetes pequeños o *provisioned concurrency* (entornos precalentados, con costo fijo).
- **Concurrencia:** hay un límite de ejecuciones simultáneas por cuenta y región (del orden de 1.000 por defecto, ampliable). Todas las funciones lo comparten. La **concurrencia reservada** garantiza un mínimo a una función y a la vez le pone un **tope**.
- **Timeout:** máximo 15 minutos por invocación. Un trabajo que puede durar más no va en una sola Lambda.

**Ejemplo de concurrencia como protección:** la función que llama al LLM para clasificar tickets tiene concurrencia reservada de 20. Si cada llamada tarda 4 segundos, el máximo es 5 solicitudes por segundo al proveedor, pase lo que pase con el volumen de entrada. Sin ese tope, un pico de 3.000 mensajes podría escalar a cientos de ejecuciones simultáneas, agotar el límite del proveedor y, de paso, la concurrencia de la cuenta que necesitan otras funciones.

### Lambda con SQS: lotes y fallas parciales

Cuando SQS dispara una Lambda, el servicio hace el polling por nosotros y entrega **lotes** de mensajes (por ejemplo, 10). Si la función termina bien, los borra todos; si lanza un error, el lote entero vuelve a la cola. Con 10 mensajes donde falla 1, los otros 9 se reprocesan: duplicados y costo de LLM tirado.

La solución es la **respuesta de falla parcial**: se activa `ReportBatchItemFailures` y la función devuelve solo los identificadores que fallaron.

```python
def handler(event, context):
    fallidos = []
    for registro in event["Records"]:
        try:
            clasificar_ticket(json.loads(registro["body"]))
        except Exception:
            fallidos.append({"itemIdentifier": registro["messageId"]})
    return {"batchItemFailures": fallidos}
```

Dos ajustes más: el visibility timeout de la cola debe ser bastante mayor que el timeout de la función (AWS recomienda al menos seis veces), y la integración permite fijar una **concurrencia máxima** por fuente de eventos, otra forma de limitar cuántas invocaciones simultáneas genera la cola.

### Step Functions: máquinas de estados

**Step Functions** define un flujo como una **máquina de estados** en JSON (lenguaje Amazon States Language): pasos de tarea, decisiones, paralelos, mapas sobre listas y esperas. Cada paso puede declarar **Retry** (qué errores reintentar, cuántas veces, con qué backoff) y **Catch** (a qué estado ir si se agotan los reintentos). El estado de cada ejecución queda registrado y se puede ver paso a paso.

| Aspecto | Standard | Express |
|---|---|---|
| Duración máxima | Hasta 1 año | Hasta 5 minutos |
| Semántica | Cada paso se ejecuta una vez salvo reintentos declarados | Al menos una vez (asíncrono) |
| Historial | Completo, visible en consola | En logs |
| Costo | Por transición de estado | Por ejecución y duración |
| Uso típico | Flujos largos, aprobaciones humanas | Alto volumen y corta duración |

El patrón clave para agentes es **esperar un callback con task token** (`.waitForTaskToken`). El paso envía un token a algún lado (una cola, un mensaje a una persona) y la ejecución queda pausada, sin consumir cómputo, hasta que alguien llama a `SendTaskSuccess` o `SendTaskFailure` con ese token. Con un `HeartbeatSeconds` o un timeout del paso, una espera sin respuesta termina en un estado definido en lugar de quedar abierta para siempre.

### Idempotencia en la práctica

Con entrega al menos una vez en SQS, SNS, EventBridge y Lambda, el consumidor **va a** ver duplicados. La técnica general está en [Patrones de resiliencia](#t/resiliencia); en AWS se implementa típicamente con una **escritura condicional**:

1. Cada trabajo lleva una clave de idempotencia derivada de la intención: `sms:{pedido_id}:{tipo_aviso}`, no un UUID nuevo por intento.
2. Antes del efecto, el worker escribe en DynamoDB `PutItem` con la condición `attribute_not_exists(clave)` (o en Aurora, `INSERT ... ON CONFLICT DO NOTHING`).
3. Si la escritura falla por la condición, el efecto ya se hizo o está en curso: se borra el mensaje sin repetir.
4. Si tiene éxito, se ejecuta el efecto y se marca el registro como completo, con un TTL que cubra la ventana de reintentos.

Para agentes, la regla es más fina: el reintento de una **tarea de agente** no debe repetir sus **llamadas a herramientas con efectos**. El agente puede volver a razonar, pero la herramienta `enviar_sms` verifica la clave antes de actuar (ver [Agentes y tool calling](#t/agentes)).

## Casos prácticos

### Clasificación de tickets: de síncrona a cola con workers

**Situación:** la API de soporte clasificaba cada ticket con el LLM dentro de la solicitud del comercio. En un pico de 3.000 tickets en 5 minutos, el proveedor devolvió errores 429, la API reintentó, la latencia de carga de tickets subió a 30 segundos y muchos comercios vieron errores.

**Qué se hace:** la API guarda el ticket con estado `pendiente_clasificacion`, publica `ticket_creado` en SNS y responde de inmediato con el identificador. Una cola SQS suscripta alimenta una Lambda con concurrencia reservada de 20, lotes de 5 y respuesta de falla parcial. La interfaz consulta un endpoint de estado y muestra "clasificando"; para tickets urgentes, una notificación avisa cuando quedan listos. Se alerta por la antigüedad del mensaje más viejo (umbral de 15 minutos) y no por la cantidad. En el siguiente pico, la cola llegó a 1.800 mensajes, se vació en 11 minutos y ningún comercio vio un error.

### Visibility timeout más corto que la llamada al LLM

**Situación:** el agente que resume casos largos corre en workers de EKS que leen de SQS con visibility timeout de 30 segundos. Tras cambiar a un modelo más capaz, el p99 de procesamiento sube a 50 segundos. Aparecen resúmenes duplicados, el gasto de tokens sube un 15% y, en algunos casos, el agente envía dos veces el mismo SMS al destinatario.

**Qué se hace:** el diagnóstico sale de cruzar mensajes con `ApproximateReceiveCount` mayor que 1, sin errores registrados, con la duración del procesamiento. Se sube el visibility timeout a 180 segundos y el worker lo extiende cada 60 segundos mientras trabaja. La herramienta `enviar_sms` pasa a exigir una clave de idempotencia `sms:{caso_id}:{plantilla}` con escritura condicional en DynamoDB, para que ningún duplicado futuro, venga de donde venga, repita el envío. Se agrega una alerta si el p99 de procesamiento supera la mitad del visibility timeout.

### Mensaje veneno que llena la DLQ

**Situación:** un comercio integra un sistema nuevo que envía tickets con un campo de texto de varios MB pegado desde un PDF. El worker falla al construir el prompt (supera la ventana de contexto del modelo), el mensaje se reintenta 5 veces y pasa a la DLQ. En dos días la DLQ tiene 4.000 mensajes y nadie lo nota, porque la alarma no existía.

**Qué se hace:** se crea la alarma sobre la DLQ con dueño en el equipo de soporte. Se distingue en el código entre errores **transitorios** (429, timeout del proveedor) y **permanentes** (entrada inválida): los permanentes no se reintentan, se marcan como `requiere_revision` y se borran de la cola. Se agrega truncado y resumen previo para textos largos. Con el arreglo desplegado, se hace redrive de los 4.000 mensajes a ritmo limitado, para no repetir el pico contra el proveedor del LLM. Los textos grandes pasan a S3 y el mensaje lleva solo la referencia.

### El agente propone, una persona aprueba

**Situación:** el agente de operaciones investiga una caída de entregas a tiempo en la zona norte y concluye que conviene reasignar 40 pedidos de un transportista con el vehículo averiado. Hasta ahora solo tenía herramientas de solo lectura; el equipo quiere que pueda proponer la acción, pero no ejecutarla sin aprobación.

**Qué se hace:** una máquina de estados Standard con estos pasos: (1) el agente produce la propuesta estructurada (pedidos, transportistas destino, justificación); (2) un paso de validación verifica que los pedidos siguen sin retirar; (3) un paso `.waitForTaskToken` publica la propuesta en el canal de operaciones con botones de aprobar y rechazar, que llaman a un endpoint autenticado con el token; el paso tiene un timeout de 30 minutos; (4) si se aprueba, una tarea reasigna con clave de idempotencia por pedido, con Retry ante errores transitorios y Catch hacia un estado que notifica fallas parciales; (5) si se rechaza o vence el plazo, se registra la decisión para evaluar al agente después. El agente no tiene el permiso de IAM para reasignar: solo lo tiene la tarea posterior a la aprobación, y cada ejecución deja un historial auditable.

## Errores comunes

- **Visibility timeout menor que el tiempo de procesamiento.** Genera duplicados silenciosos; se dimensiona sobre el máximo observado y se extiende con latidos en trabajos largos.
- **Confiar en la deduplicación de FIFO como garantía de efecto único.** Solo cubre reenvíos del productor en 5 minutos; el consumidor necesita su propia idempotencia.
- **Lotes de Lambda sin falla parcial.** Un mensaje malo reprocesa todo el lote; se activa `ReportBatchItemFailures`.
- **Lambda sin tope de concurrencia frente a un LLM.** Un pico escala cientos de invocaciones contra un proveedor con límites y gasto por token; se fija concurrencia reservada o máxima por fuente.
- **Reintentar errores permanentes.** Una entrada inválida falla igual las 5 veces y consume tokens en cada intento; se clasifican los errores y solo se reintentan los transitorios.
- **Tareas de agente de varios minutos dentro de una solicitud HTTP.** Se cortan por timeouts de balanceadores y clientes; se modelan como trabajos asíncronos con endpoint de estado.

## Para discutir en equipo

- ¿Qué llamadas a LLMs hacemos hoy de forma síncrona que podrían ser trabajos en cola, y qué demora aceptaría el usuario?
- Para cada herramienta con efectos de nuestros agentes, ¿cuál es su clave de idempotencia y dónde se verifica?
- ¿Cuál es el tope de concurrencia que protege el límite de nuestro proveedor de LLM, y está definido en un solo lugar o repartido entre funciones que compiten?
- ¿Qué acciones del agente de operaciones deberían pasar por aprobación humana, y cuáles podrían ejecutarse solas con límites?
- ¿Usaríamos EventBridge, SNS o Kafka para el próximo flujo de eventos entre equipos, y con qué criterio?
