---
slug: grpc-rest
titulo: gRPC y REST
resumen: Cuándo usar gRPC o REST, cómo evolucionar contratos sin romper clientes y qué cuidar en deadlines, errores, idempotencia, webhooks y balanceo.
lectura: 13
---

## La idea central

Una API es un contrato entre equipos que despliegan en momentos distintos. El problema central no es elegir un formato, sino poder **cambiar** ese contrato sin coordinar a todos sus clientes: el servicio de asignación se despliega diez veces por semana, el modelo de ETA dos, y los comercios integrados a la API pública actualizan su código cuando pueden, a veces una vez al año.

REST y gRPC resuelven el mismo problema con prioridades distintas. REST sobre HTTP y JSON es universal: cualquier lenguaje, herramienta o persona con `curl` puede usarlo, por eso es la opción natural hacia afuera. gRPC usa Protocol Buffers sobre HTTP/2: contratos tipados, mensajes binarios más chicos, generación de código y deadlines integrados, por eso encaja entre servicios internos con presupuestos de latencia ajustados. Muchas empresas, Rumbo incluida, usan las dos.

## Conceptos

### Comparación

| Aspecto | REST (HTTP + JSON) | gRPC (HTTP/2 + Protobuf) |
|---|---|---|
| Contrato | Opcional (OpenAPI); muchas veces implícito | Obligatorio (`.proto`), con código generado |
| Formato | Texto, legible, más grande | Binario, compacto, no legible sin herramientas |
| Costo de serialización | Mayor (parseo de JSON) | Menor |
| Streaming | Limitado (SSE, WebSockets aparte) | Nativo en ambos sentidos |
| Deadlines | Convención propia | Integrados y propagables |
| Soporte en navegadores | Total | Requiere un proxy (gRPC-Web) |
| Caché HTTP, CDNs | Natural para GET | No aplica |
| Depuración | `curl`, navegador | Herramientas específicas (`grpcurl`) |
| Balanceo | Funciona con cualquier balanceador | Requiere balanceo de capa 7 o en el cliente |
| Uso típico en Rumbo | API pública para comercios, webhooks | Asignación ↔ modelo de ETA, servicios internos |

### Protocol Buffers y números de campo

En un archivo `.proto` cada campo tiene un nombre, un tipo y un **número**. En el mensaje binario viaja el número, no el nombre. Esto tiene consecuencias importantes: se puede renombrar un campo sin romper nada en el cable, pero **el número es la identidad del campo para siempre**.

Si un cliente recibe un campo con un número que no conoce, lo ignora. Si un campo esperado no llega, toma el valor por defecto de su tipo (0, cadena vacía, `false`). Esta es la base de la compatibilidad, pero también de un problema: no se distingue "no enviado" de "enviado con valor 0", salvo que el campo se declare `optional` o se use un tipo envoltorio.

```proto
syntax = "proto3";

package rumbo.asignacion.v1;

service ServicioAsignacion {
  // Idempotente por clave_idempotencia.
  rpc AsignarPedido(AsignarPedidoRequest) returns (AsignarPedidoResponse);
}

service ModeloEta {
  // Predice para un lote de candidatos en una sola llamada.
  rpc PredecirLote(PredecirLoteRequest) returns (PredecirLoteResponse);
}

message AsignarPedidoRequest {
  string pedido_id = 1;
  string clave_idempotencia = 2;
  Ubicacion origen = 3;
  Ubicacion destino = 4;
  reserved 5;                 // antes: string zona_texto. No reutilizar.
  reserved "zona_texto";
  string zona_id = 6;
  optional int32 prioridad = 7; // optional: distingue "no enviado" de 0
}

message AsignarPedidoResponse {
  string pedido_id = 1;
  string transportista_id = 2;
  int32 eta_segundos = 3;
  Origen origen_decision = 4;

  enum Origen {
    ORIGEN_DESCONOCIDO = 0;   // el valor 0 siempre es "no especificado"
    ORIGEN_MODELO = 1;
    ORIGEN_REGLA_RESPALDO = 2;
  }
}

message Ubicacion {
  double lat = 1;
  double lon = 2;
}

message PredecirLoteRequest {
  string pedido_id = 1;
  repeated Candidato candidatos = 2;
}

message Candidato {
  string transportista_id = 1;
  map<string, double> features = 2;
}

message PredecirLoteResponse {
  repeated Prediccion predicciones = 1;
  string version_modelo = 2;
}

message Prediccion {
  string transportista_id = 1;
  double prob_a_tiempo = 2;
  int32 eta_segundos = 3;
}
```

### Compatibilidad hacia atrás

Un cambio es **compatible hacia atrás** si los clientes viejos siguen funcionando con el servidor nuevo, y **hacia adelante** si los clientes nuevos funcionan con un servidor viejo (lo que pasa durante un deploy gradual). Las reglas en Protobuf:

- Seguro: agregar un campo nuevo con un número nuevo; agregar un valor a un enum (los clientes viejos lo verán como desconocido); agregar un método.
- Peligroso: cambiar el tipo de un campo, cambiar el número, borrar un campo sin reservarlo, convertir un campo simple en `repeated`, cambiar la semántica de un campo existente aunque su tipo no cambie.
- Al borrar un campo se declara `reserved` su número y su nombre, para que nadie los reutilice.

En REST con JSON las reglas son análogas: agregar campos es seguro si los clientes ignoran los desconocidos; quitar o renombrar no lo es. El punto delicado es que los clientes externos a veces validan estrictamente y fallan ante un campo nuevo; conviene documentar desde el primer día que pueden aparecer campos nuevos.

### Versionado

Cuando un cambio incompatible es inevitable, se crea una nueva versión y ambas conviven. En gRPC la versión va en el paquete (`rumbo.asignacion.v1` y `v2`); en REST, normalmente en la ruta (`/v1/pedidos`) o en un header. La versión vieja se mantiene durante un período de deprecación anunciado, se mide quién la sigue usando y se apaga cuando el uso llega a cero o vence el plazo acordado.

Lo importante es que una versión nueva es cara: duplica código, tests y documentación. La mayoría de la evolución debe hacerse con cambios aditivos dentro de la misma versión.

### Deadlines propagados

En gRPC el cliente fija un **deadline** (un instante absoluto, no una duración) y viaja en la metadata de la llamada. El servidor sabe cuánto tiempo le queda y, si llama a otros servicios, les pasa el mismo deadline. Si vence, toda la cadena abandona el trabajo. En Go esto se expresa con `context.Context`: si el handler reenvía el `ctx` que recibió, el deadline se propaga solo.

Sin propagación, cada servicio usa su propio timeout fijo y aparece el "trabajo para nadie": el cliente ya se fue y los servicios de abajo siguen consumiendo CPU y conexiones. En Go, olvidar pasar el `ctx` recibido (y crear uno nuevo con `context.Background()`) corta la cadena sin ningún error visible (ver [Go](#t/go)). En REST no hay un estándar; se suele propagar con un header propio (por ejemplo `X-Deadline-Ms`) o confiar en timeouts menores en cada capa (ver [Patrones de resiliencia](#t/resiliencia)).

### Códigos de error: reintentables y no reintentables

El código de error le dice al cliente qué hacer. Distinguir los reintentables de los que no lo son evita tanto reintentar en vano como rendirse ante algo transitorio.

| Situación | gRPC | HTTP | ¿Reintentar? |
|---|---|---|---|
| Servicio no disponible, reiniciando | `UNAVAILABLE` | 503 | Sí, con backoff |
| Venció el deadline | `DEADLINE_EXCEEDED` | 504 | Solo si la operación es idempotente y queda tiempo |
| Sobrecarga, límite de tasa | `RESOURCE_EXHAUSTED` | 429 | Sí, respetando `Retry-After` |
| Conflicto de concurrencia | `ABORTED` | 409 | Sí, releyendo el estado antes |
| Datos inválidos | `INVALID_ARGUMENT` | 400 | No |
| Sin permisos | `PERMISSION_DENIED` | 403 | No |
| No existe | `NOT_FOUND` | 404 | No |
| Estado no permite la operación | `FAILED_PRECONDITION` | 409 o 422 | No, hasta que cambie el estado |
| Error interno | `INTERNAL` | 500 | Con cuidado: puede ser un bug determinista |

Un error frecuente es devolver `INTERNAL` o 500 para todo, lo que obliga al cliente a adivinar. Otro es devolver `UNAVAILABLE` ante un error de validación, lo que dispara reintentos inútiles.

### Idempotencia de métodos HTTP y claves de idempotencia

HTTP define que GET, PUT y DELETE son idempotentes: `PUT /pedidos/123/estado` con `entregado` deja el mismo resultado se envíe una o cinco veces. POST no lo es: `POST /pedidos` dos veces crea dos pedidos. Como los clientes reintentan (y las redes y proxies también), un POST sin protección termina duplicando.

La solución es el header `Idempotency-Key`: el comercio genera un UUID por pedido que quiere crear y lo reenvía en cada reintento. El servidor guarda la clave con la respuesta y, si la recibe de nuevo con el mismo cuerpo, devuelve la respuesta original en lugar de crear otro pedido. Si llega con otro cuerpo, devuelve 422. El mecanismo es el mismo que se describe en [Patrones de resiliencia](#t/resiliencia).

### Webhooks firmados con HMAC

Un webhook es una llamada HTTP que Rumbo hace al servidor del comercio para avisarle de un evento (pedido entregado, fallido). El comercio necesita saber que la llamada viene realmente de Rumbo y que nadie la modificó. Para eso se firma con **HMAC**: Rumbo y el comercio comparten un secreto; Rumbo calcula `HMAC-SHA256(secreto, timestamp + "." + cuerpo)` y lo envía en un header junto al timestamp.

El comercio recalcula la firma con el cuerpo crudo (antes de parsear el JSON, porque reformatearlo cambia los bytes), la compara en tiempo constante y rechaza la llamada si el timestamp tiene más de 5 minutos, para impedir que alguien reenvíe una solicitud capturada (*replay*). Otras reglas: cada webhook lleva un `evento_id` para que el comercio deduplique, porque Rumbo reintenta con backoff durante horas si no recibe un 2xx; el orden de llegada no está garantizado, así que el cuerpo incluye la versión o el timestamp del estado; y el secreto debe poder rotarse con un período en el que ambos sean válidos.

### Tests de contrato

Los tests de integración completos son lentos y frágiles; los tests unitarios no detectan que dos servicios dejaron de entenderse. Los **tests de contrato** cubren ese hueco. Para Protobuf, una herramienta de detección de cambios incompatibles corre en la CI y compara el `.proto` nuevo con el de la rama principal: falla si se reutilizó un número, se cambió un tipo o se borró un campo sin reservar. Para REST, el enfoque dirigido por el consumidor registra lo que cada consumidor espera ("necesito `eta_segundos` como entero") y verifica en la CI del proveedor que sigue cumpliéndose.

### Balanceo con HTTP/2: capa 4 vs. capa 7

gRPC usa HTTP/2, que mantiene **una conexión TCP de larga duración** y multiplexa muchas solicitudes sobre ella. Un balanceador de **capa 4** (que reparte conexiones TCP, como un Service estándar de Kubernetes o un NLB) decide el destino una sola vez, al abrir la conexión. Después, todas las solicitudes de ese cliente van al mismo pod.

Un balanceador de **capa 7** entiende HTTP/2 y reparte **solicitudes** individuales: un service mesh (Envoy, Linkerd), un ALB con soporte gRPC, o el balanceo en el propio cliente gRPC usando un Service *headless* para descubrir todos los pods. Con REST sobre HTTP/1.1 el problema es menor porque las conexiones se abren y cierran más seguido.

## Casos prácticos

### Asignación (Go) llama al modelo (Python) con deadline de 30 ms

**Situación:** el servicio de asignación tiene 50 ms en total y destina 30 al modelo de ETA, que corre en Python. Hay que garantizar que, si el modelo se demora, la asignación no espere más de lo previsto y el modelo no siga calculando inútilmente.

**Qué se hace:** la asignación crea un contexto derivado con `context.WithTimeout(ctx, 30*time.Millisecond)` (o menos, si el deadline del llamador está más cerca) y llama a `PredecirLote` con los 20 candidatos en una sola solicitud. El servidor Python consulta el tiempo restante antes de calcular y, si queda menos de lo que tarda la inferencia, devuelve `DEADLINE_EXCEEDED` de inmediato. Si vence, la asignación usa la regla de respaldo y marca `ORIGEN_REGLA_RESPALDO` en la respuesta, lo que permite medir la tasa de respaldo (el reparto completo del presupuesto está en [Baja latencia y alta disponibilidad](#t/latencia-disponibilidad)). No hay reintento: no queda tiempo para un segundo intento.

### Reutilizar un número de campo rompe clientes en silencio

**Situación:** alguien borra `string zona_texto = 5` (el nombre de la zona en texto libre, como "Palermo") porque ya no se usa, y semanas después agrega `string zona_id = 5` (un identificador como `z-0042`). Un cliente viejo, que no se redesplegó, sigue enviando "Palermo" en el campo 5. Como el tipo en el cable es el mismo, el servidor nuevo lo lee sin error como `zona_id = "Palermo"`, no encuentra esa zona y aplica la configuración de zona por defecto. No hay excepción ni alerta: los pedidos de ese cliente se asignan con los parámetros equivocados durante días, hasta que alguien nota que la tasa de entregas a tiempo cayó en esa zona. Si el tipo hubiera cambiado (de texto a entero), la mayoría de las bibliotecas tratarían el campo como desconocido y lo descartarían en silencio: otro modo de falla igual de invisible.

**Qué se hace:** al borrar un campo se declara `reserved 5; reserved "zona_texto";` como en el `.proto` de ejemplo, y el compilador impide reutilizarlo. La CI incorpora un detector de cambios incompatibles que bloquea el merge ante un número reutilizado o un tipo cambiado. La corrección del incidente: `zona_id` pasa a un número nuevo (6) y se agrega una métrica de zonas no encontradas por cliente.

### API pública REST para comercios con webhooks firmados

**Situación:** Rumbo abre una API para que los comercios creen pedidos y consulten su estado, y quiere avisarles de los cambios sin que tengan que consultar cada minuto.

**Qué se hace:** REST con JSON y OpenAPI publicada, versionado en la ruta (`/v1`). `POST /v1/pedidos` exige `Idempotency-Key`; los listados se paginan con cursores, no con offset; los errores siguen un formato uniforme con un código legible por máquinas; hay rate limiting por comercio con 429 y `Retry-After`. Los webhooks se firman con HMAC sobre timestamp y cuerpo, incluyen `evento_id` y la versión del estado, se reintentan con backoff exponencial durante 24 horas y, tras ese plazo, quedan disponibles en un endpoint de eventos pendientes para que el comercio los recupere. Se publican la regla de que pueden aparecer campos nuevos y la política de deprecación.

### Carga desigual tras migrar a gRPC

**Situación:** el servicio de features migra de REST a gRPC. Tras el cambio, de sus 12 pods, 3 están al 90% de CPU y el resto casi ocioso. El autoscaling agrega pods, pero los nuevos no reciben tráfico.

**Qué se hace:** el diagnóstico es el balanceo de capa 4: cada pod de la asignación abrió una conexión HTTP/2 al iniciar y la mantiene, así que la carga quedó repartida según dónde cayeron esas pocas conexiones, y los pods nuevos no reciben ninguna. Se pasa a balanceo de capa 7: un Service headless con balanceo *round robin* en el cliente gRPC (o el service mesh, si ya existe). Además, el servidor fija una antigüedad máxima de conexión (`MaxConnectionAge` de unos minutos) para que los clientes se reconecten periódicamente y descubran pods nuevos.

## Errores comunes

- **Reutilizar números de campo o cambiar su tipo.** Rompe clientes sin error visible; se usa `reserved` y un detector de cambios incompatibles en la CI.
- **POST sin clave de idempotencia en APIs donde el cliente reintenta.** Genera recursos duplicados; se exige `Idempotency-Key` en las operaciones de creación.
- **Timeouts fijos en lugar de deadlines propagados.** Los servicios de abajo trabajan para un cliente que ya se fue; se propaga el contexto.
- **Devolver 500 o `INTERNAL` para todo.** El cliente no puede decidir si reintentar; se usan códigos específicos.
- **Verificar la firma HMAC sobre el JSON reparseado o sin validar el timestamp.** Las firmas fallan o se aceptan replays; se usa el cuerpo crudo y una ventana de tiempo.
- **gRPC detrás de un balanceador de capa 4.** La carga se concentra en pocos pods; se usa balanceo de capa 7 o en el cliente.

## Para discutir en equipo

- ¿Qué servicios internos siguen en REST y ganarían con gRPC, y en cuáles el cambio no vale la pena?
- ¿Cómo detectaríamos hoy que un cambio de contrato rompe a un consumidor antes de desplegarlo?
- ¿Qué política de deprecación es razonable para la API pública de comercios, considerando a los que actualizan una vez al año?
- ¿Cuándo justifica una funcionalidad crear una nueva versión de la API en lugar de un cambio aditivo?
- ¿Cómo hacemos que un comercio que perdió webhooks durante una caída de su servidor recupere su estado sin consultar todos sus pedidos?
