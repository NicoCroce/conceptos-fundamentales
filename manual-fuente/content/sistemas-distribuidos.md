---
slug: sistemas-distribuidos
titulo: Sistemas distribuidos
resumen: Qué cambia cuando un sistema vive en varias máquinas que fallan por separado, y cómo razonar sobre consistencia, orden y fallas parciales.
lectura: 15
---

## La idea central

Un programa en una sola máquina falla de forma bastante binaria: funciona o no. Un sistema distribuido falla **por partes**: la base responde pero Kafka no, un pod ve la red y otro no, una réplica está tres segundos atrasada. Lo más difícil es que, desde un nodo, una respuesta que no llega no distingue entre "el otro está caído", "está lento", "procesó la orden y se perdió la respuesta" y "nunca recibió la orden". Casi todos los patrones de este tema existen para convivir con esa ambigüedad.

Una analogía útil: coordinar por mensajes de texto a un grupo de transportistas con mala señal. Si mandas "toma el pedido 123" y no hay respuesta, no sabes si lo leyó. Si lo mandas otra vez, quizá dos personas terminen yendo. Para no depender de la suerte necesitas reglas: identificadores para detectar duplicados, una fuente de verdad que diga quién tiene cada pedido y acuerdos sobre qué hacer cuando no hay respuesta.

## Conceptos

### Las falacias de la computación distribuida

Son ocho supuestos que parecen razonables y son falsos: la red es confiable, la latencia es cero, el ancho de banda es infinito, la red es segura, la topología no cambia, hay un solo administrador, el costo de transporte es cero y la red es homogénea. Cada una se traduce en un bug concreto.

- "La red es confiable": el código asume que si `Send()` no devolvió error, el otro lado procesó el mensaje. Falso: puede haberlo procesado y perdido la respuesta.
- "La latencia es cero": un endpoint hace 40 llamadas secuenciales a otro servicio. En local tarda 4 ms; en producción, con 2 ms por llamada, 80 ms.
- "La topología no cambia": un cliente guarda en caché la IP de un pod que Kubernetes ya reemplazó.

**Por qué importa:** en una revisión, muchas preguntas útiles son una falacia disfrazada: "¿y si esta llamada tarda 2 segundos?", "¿y si llega dos veces?".

### CAP y PACELC

El teorema **CAP** dice que, ante una **partición de red** (dos grupos de nodos que no pueden comunicarse), un sistema tiene que elegir entre **consistencia** (todos ven el mismo dato, o se rechaza la operación) y **disponibilidad** (todos responden, aunque sea con un dato viejo o divergente). No es "elige dos de tres": las particiones van a ocurrir, así que la elección real es qué hacer cuando ocurren.

**Ejemplo:** el servicio de asignación corre en dos zonas de disponibilidad y se corta la red entre ellas. Si ambas siguen asignando sin coordinarse, un mismo transportista puede recibir dos pedidos que exceden su capacidad (elegimos disponibilidad). Si la zona que perdió contacto con el líder de la base deja de asignar, algunos pedidos esperan (elegimos consistencia).

**PACELC** completa a CAP con el caso normal: **si** hay **P**artición, elegir entre **A** y **C**; **E**n otro caso (*else*), elegir entre **L**atencia y **C**onsistencia. Esta segunda mitad es la que más pesa en el día a día, porque las particiones son raras pero cada lectura paga su costo. Leer de la réplica más cercana es rápido pero puede devolver un dato viejo; confirmar una escritura en tres zonas antes de responder es consistente pero suma milisegundos.

### Modelos de consistencia

- **Fuerte (linealizable):** cada lectura ve la última escritura confirmada, como si hubiera una sola copia. Es lo que da una lectura al líder de Aurora.
- **Eventual:** si dejan de llegar escrituras, todas las copias convergen en algún momento. No hay garantía sobre cuándo. Un dashboard que lee de una réplica o de un agregado en un almacén analítico es eventualmente consistente.
- **Read-your-writes:** un usuario siempre ve sus propias escrituras, aunque otros vean datos más viejos. Es un punto intermedio muy práctico.

**Ejemplo:** un comercio crea un pedido y la pantalla siguiente lo lista leyendo de una réplica con 800 ms de atraso. El pedido "no existe". Para el comercio es un bug, aunque el sistema funcione según su diseño. Read-your-writes se logra leyendo del líder durante unos segundos después de una escritura de ese comercio, o enviando la versión escrita para que la réplica espere hasta tenerla.

### Qué prioriza cada dato de Rumbo

No hay una única respuesta para todo el sistema: se decide por dato, según el costo de equivocarse.

| Dato | Prioridad | Por qué | Qué pasa ante falla |
|---|---|---|---|
| Estado del pedido | Consistencia | Un pedido "entregado" que vuelve a "en camino" rompe seguimiento, soporte y las métricas de cumplimiento | Se rechaza la escritura y se reintenta |
| Asignación pedido-transportista | Consistencia | Dos transportistas yendo al mismo pedido es un costo operativo real | Se demora la asignación antes que duplicarla |
| Capacidad disponible del transportista | Consistencia | Si se pisa, se sobrecarga al transportista | Lock o versión (ver [Bases de datos](#t/bases-de-datos)) |
| Dashboards de operaciones | Disponibilidad | Un dato con 1 minuto de atraso es aceptable; un dashboard caído en medio de un incidente no | Se muestra el último dato con su marca de tiempo |
| Features del modelo de ETA | Disponibilidad con valor por defecto | Una feature de hace 5 minutos apenas cambia la predicción | Se usa el valor por defecto documentado y se registra una métrica |
| Posición GPS del transportista | Disponibilidad | Llega cada pocos segundos; la próxima corrige la anterior | Se descarta y se espera la siguiente |

### Replicación líder-seguidores y replication lag

En la replicación líder-seguidores, todas las escrituras van al **líder**, que las envía a los **seguidores** (réplicas de lectura). Si la replicación es asíncrona, el líder confirma la escritura sin esperar a las réplicas, y la diferencia temporal entre ambos es el **replication lag**. En Aurora suele ser de decenas de milisegundos, pero bajo carga de escritura intensa o consultas pesadas en la réplica puede llegar a segundos.

Consecuencias concretas: leer de una réplica justo después de escribir puede devolver el valor anterior; dos lecturas seguidas a réplicas distintas pueden "ir hacia atrás en el tiempo"; y si el líder falla antes de replicar, las escrituras confirmadas pero no replicadas se pueden perder (según la tecnología). Se mitiga leyendo del líder lo que necesita estar fresco, midiendo el lag como métrica con alerta y no usando réplicas para decisiones que luego se escriben.

### Particionado y particiones calientes

Cuando los datos no entran en una máquina, o el volumen de escrituras excede su capacidad, se reparten en **particiones** (o *shards*) según una clave. Las dos estrategias clásicas son por **rango** (pedidos del 1 al 1.000.000 en la partición A) y por **hash** (hash(clave) módulo N). El hash reparte mejor; el rango permite consultas por rango eficientes.

El problema típico es la **partición caliente**: una clave concentra una fracción desproporcionada de la carga. Si se particiona por `comercio_id` y un comercio representa el 30% de los pedidos, la partición que lo contiene recibe el 30% de la carga mientras las otras reciben fracciones pequeñas. Agregar particiones no ayuda, porque una sola clave siempre cae en una sola. Las soluciones: elegir una clave de mayor cardinalidad (`pedido_id`), o agregar un sufijo a las claves calientes (`comercio_id#0` a `comercio_id#7`) a costa de perder el orden y la localidad entre ellas.

### Consenso: qué resuelven Raft y Paxos

El problema del consenso es que varios nodos se pongan de acuerdo en un valor (por ejemplo, quién es el líder o cuál es la siguiente entrada de un log) aunque algunos fallen o se aíslen. Raft y Paxos lo resuelven con **quórum**: una decisión vale si la acepta una mayoría (3 de 5, 2 de 3). Como dos mayorías siempre comparten al menos un nodo, nunca pueden quedar dos líderes decidiendo cosas distintas.

No hace falta implementarlos: vienen dentro de etcd (el almacén de estado de Kubernetes), de Kafka con KRaft, de muchas bases distribuidas. Lo que sí hace falta entender son sus consecuencias: con 3 nodos se tolera 1 falla, con 5 se toleran 2; un grupo en minoría queda sin poder escribir (eligen consistencia); y cada escritura paga al menos un viaje de ida y vuelta a la mayoría.

**Por qué importa:** cuando alguien propone "elegimos un líder con un flag en Redis", la pregunta correcta es qué pasa si dos nodos creen ser líder al mismo tiempo. El consenso existe porque ese problema es más difícil de lo que parece.

### Semánticas de entrega

- **At-most-once:** se envía una vez sin reintentar. Puede perderse; nunca se duplica.
- **At-least-once:** se reintenta hasta tener confirmación. Nunca se pierde, pero puede duplicarse (el mensaje llegó, la confirmación no).
- **Exactly-once:** en un sistema con red no confiable, la entrega exactamente una vez no existe como propiedad del transporte. Lo que sí se logra es **procesamiento con efecto exactamente una vez**: entrega at-least-once más un consumidor **idempotente**, que reconoce y descarta duplicados.

**Ejemplo:** el consumidor de notificaciones recibe `pedido_asignado` con `evento_id = e-91`. Antes de enviar el SMS registra `e-91` en una tabla con restricción única dentro de la misma transacción que marca la notificación como enviada. Si el evento llega de nuevo, la inserción falla y no se envía un segundo SMS. Ver [Patrones de resiliencia](#t/resiliencia) para el detalle de las claves de idempotencia.

### Concurrencia y locks distribuidos

Dentro de una base relacional, los locks y las transacciones resuelven la concurrencia con garantías fuertes. Fuera de ella, un "lock distribuido" (en Redis, por ejemplo) es más frágil de lo que parece: el proceso que lo tiene puede pausarse (una pausa larga del recolector de basura, una VM congelada), el lock vence por TTL, otro proceso lo toma y el primero despierta convencido de que todavía lo tiene.

La protección es un **fencing token**: cada vez que se otorga el lock se entrega un número creciente, y el recurso protegido rechaza escrituras con un token menor al último visto. Muchas veces la alternativa más simple es no usar un lock externo y apoyarse en la base: una restricción única, `SELECT ... FOR UPDATE` o una columna de versión.

### Sagas y patrón outbox

Cuando una operación toca varios servicios con bases distintas, no hay una transacción que los abarque a todos. Una **saga** es una secuencia de transacciones locales en la que cada paso tiene una **compensación** que deshace su efecto si un paso posterior falla. La compensación no es un rollback: es una acción nueva de negocio (liberar capacidad, avisar al transportista), y también tiene que ser idempotente.

El **patrón outbox** resuelve un problema previo: cómo actualizar la base y publicar un evento de forma atómica. Si se escribe en la base y luego se publica en Kafka, el proceso puede caerse entre ambos pasos y el evento se pierde. Si se publica primero, el evento puede salir aunque la transacción falle. La solución es escribir el evento en una tabla `outbox` **dentro de la misma transacción** que el cambio de negocio, y que un proceso aparte (un *relay* o CDC sobre el log de la base) lo publique.

```text
  Servicio de asignación
  +--------------------------------------------+
  | BEGIN                                      |
  |   UPDATE pedidos SET estado='asignado' ... |
  |   INSERT INTO outbox (evento_id, tipo,     |
  |          payload) VALUES ('e-91', ...)     |
  | COMMIT  <- ambos o ninguno                 |
  +--------------------------------------------+
                   |
                   v
           +---------------+     publica      +-----------------+
           | Relay / CDC   | ---------------> | Kafka: pedidos  |
           | lee outbox    |  at-least-once   +-----------------+
           +---------------+                    |      |      |
                   |                            v      v      v
           marca publicado              seguimiento  notif.  features
                                         (consumidores idempotentes)
```

El relay puede publicar un evento dos veces (se cae después de publicar y antes de marcarlo), así que los consumidores deduplican por `evento_id`.

### Relojes

Los relojes de distintas máquinas no coinciden: NTP los mantiene cerca, típicamente a pocos milisegundos, pero pueden saltar hacia atrás tras una corrección. Por eso no se usa el reloj de pared para ordenar eventos entre máquinas ("el último que escribió gana" según timestamp puede descartar la escritura realmente más nueva), ni para medir duraciones (para eso existe el reloj monotónico, que nunca retrocede).

Para orden se usan números de secuencia asignados por una sola fuente (el offset de una partición de Kafka, una versión en la fila), o relojes lógicos que capturan causalidad. Los timestamps siguen siendo útiles para mostrar y analizar, siempre con zona horaria.

## Casos prácticos

### Un pedido asignado a dos transportistas por un reintento

**Situación:** el servicio de asignación envía `AsignarPedido(p-123, t-7)` al servicio de pedidos. La llamada supera su timeout, aunque en realidad se procesó. El cliente reintenta, pero mientras tanto el ranking se recalculó y ahora elige a `t-9`. Resultado: dos transportistas notificados para el mismo pedido.

**Qué se hace:** dos defensas complementarias. Primero, una **clave de idempotencia** por intento de asignación: el reintento usa la misma clave, y el servidor devuelve el resultado original en lugar de procesarlo de nuevo. Segundo, una **restricción en la base** que haga imposible el estado inválido: un índice único parcial sobre `asignaciones(pedido_id) WHERE activa`. Aunque la lógica falle, la segunda inserción es rechazada. Además, ante un timeout ambiguo se consulta el estado del pedido antes de elegir otro transportista.

### Evento perdido entre la base y Kafka

**Situación:** el servicio de pedidos marca un pedido como entregado y luego publica `pedido_entregado`. Un deploy reinicia el pod entre ambos pasos. El pedido figura como entregado en la base, pero seguimiento sigue mostrándolo en camino y el destinatario no recibe la confirmación.

**Qué se hace:** se adopta el patrón outbox del diagrama. El evento se inserta en la misma transacción que el cambio de estado, y un relay basado en CDC lo publica. Se agrega una métrica de antigüedad del evento no publicado más viejo en la outbox, con alerta si supera 1 minuto, y los consumidores deduplican por `evento_id`.

### Lectura atrasada desde una réplica

**Situación:** para aliviar al líder, el endpoint `GET /pedidos/{id}` se movió a una réplica de lectura. En un pico de escritura el lag sube a 4 segundos. El servicio de asignación lee el pedido de la réplica, ve `pendiente` (ya estaba asignado) y lo vuelve a asignar.

**Qué se hace:** se separan las lecturas según su uso. Las que preceden a una decisión que escribe (asignar, cancelar, cambiar estado) van al líder, o se hacen dentro de la transacción con un lock. La réplica queda para consultas de visualización tolerantes a segundos de atraso. Se alerta si el lag supera 1 segundo y, como red de seguridad, la escritura de asignación verifica el estado esperado (`UPDATE ... WHERE estado = 'pendiente'`) y falla si cambió.

### Saga de cancelación de pedido con compensaciones

**Situación:** un comercio cancela un pedido ya asignado. Hay que marcar el pedido como cancelado, liberar la capacidad del transportista, retirar la ruta del dispositivo del transportista y avisar al destinatario. Son cuatro servicios con bases propias.

**Qué se hace:** una saga orquestada con estado persistido:

1. Pedidos: estado `cancelando` (evita que se retire mientras tanto).
2. Asignación: liberar capacidad del transportista. Compensación: volver a reservarla.
3. App del transportista: retirar la ruta. Si el transportista ya retiró el paquete, el paso falla con un error de negocio.
4. Pedidos: estado `cancelado`; outbox emite `pedido_cancelado`, que dispara la notificación.

Si el paso 3 falla porque el paquete ya fue retirado, se ejecutan las compensaciones en orden inverso: se vuelve a reservar la capacidad y el pedido vuelve a `en_camino` con el motivo registrado, para que soporte gestione la devolución. Cada paso usa el id de la saga como clave de idempotencia, y la saga se reanuda desde su último paso confirmado si el orquestador se reinicia.

## Errores comunes

- **Tratar un timeout como un fallo.** Un timeout significa "no sé"; reintentar sin idempotencia o reasignar sin consultar el estado produce duplicados.
- **Confiar en exactly-once del transporte.** Hay que diseñar los consumidores como idempotentes y deduplicar por un identificador del evento.
- **Leer de réplicas para decidir y luego escribir.** El lag convierte la lectura en una decisión sobre datos viejos; las lecturas que preceden escrituras van al líder.
- **Usar el reloj de pared para ordenar.** Diferencias de milisegundos entre máquinas reordenan eventos; se usan secuencias o versiones.
- **Locks distribuidos sin fencing.** Un proceso pausado puede seguir escribiendo con un lock vencido; si no hay fencing token, conviene apoyarse en la base.
- **Escribir en la base y publicar el evento por separado.** Tarde o temprano se pierde un evento; se usa outbox o CDC.

## Para discutir en equipo

- ¿Qué operaciones nuestras hoy tratan un timeout como fallo y podrían generar duplicados?
- Para cada dato de la tabla de prioridades, ¿estamos de acuerdo con la elección? ¿Qué dato falta?
- ¿Dónde estamos leyendo de réplicas, y alguna de esas lecturas precede a una escritura?
- ¿Preferimos sagas orquestadas o coreografiadas por eventos para los flujos de pedidos, y qué nos cuesta depurar cada una?
- ¿Qué invariantes de negocio podríamos convertir en restricciones de la base para que sean imposibles de violar?
