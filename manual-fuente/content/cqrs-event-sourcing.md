---
slug: cqrs-event-sourcing
titulo: CQRS y Event Sourcing
resumen: Separar el modelo que escribe de los modelos que leen, y guardar el historial de eventos como fuente de verdad, con sus costos, sus límites y su uso con agentes.
lectura: 15
---

## La idea central

Un mismo envío se usa de formas muy distintas. Para **cambiarlo** (reprogramar, asignar, registrar una entrega) necesitamos el agregado completo con sus reglas, cargado de forma consistente y guardado con control de versión. Para **mostrarlo** necesitamos otra cosa: el panel de la zona quiere 200 envíos con nombre del transportista y ETA; el destinatario quiere un estado en lenguaje claro; el asistente de soporte quiere todo lo de un pedido en una sola respuesta. Forzar al mismo modelo a servir ambas cosas lo vuelve malo para las dos. **CQRS** (*Command Query Responsibility Segregation*) propone separarlos: un modelo de escritura y uno o varios modelos de lectura, cada uno diseñado para su uso.

**Event Sourcing** es una idea distinta que suele aparecer al lado: en lugar de guardar el estado actual del envío y pisarlo en cada cambio, se guarda la secuencia de eventos que le pasaron, y el estado se calcula a partir de ella. Es como la diferencia entre una foto del tablero de ajedrez y la planilla de jugadas: con la planilla se puede reconstruir cualquier posición y saber cómo se llegó a ella. Las dos ideas se combinan bien, pero cada una tiene costos propios y conviene adoptarlas por separado y solo donde pagan.

## Conceptos

### CQRS: un modelo para escribir, otros para leer

En CQRS las operaciones se dividen en dos tipos:

- **Comandos:** piden un cambio (`ReprogramarEntrega`, `AsignarEnvio`). Pasan por el caso de uso, el [repositorio](#t/patron-repository) y el agregado con sus invariantes. Devuelven poco: éxito, error o el ID creado.
- **Consultas:** piden datos y no cambian nada. No cargan agregados: leen de **modelos de lectura** con la forma exacta que necesita cada pantalla, API o herramienta.

La separación tiene grados. En el más simple, ambos lados usan la misma base: el lado de lectura usa consultas SQL directas o vistas, sin pasar por el dominio. En el más completo, los modelos de lectura viven en otros almacenes (una tabla desnormalizada, un índice de búsqueda, una caché) y se actualizan a partir de eventos.

**Ejemplo:** el panel de la zona Norte mostraba 200 envíos cargando agregados (envío, bultos, intentos) y luego consultando el servicio de transportistas para el nombre y el de ETA para la estimación: unas 400 consultas y 1,2 segundos. Con un modelo de lectura `envios_por_zona` que ya tiene una fila por envío con `transportista_nombre`, `eta_minutos` y `estado_visible`, la pantalla hace una consulta con índice y responde en 15 ms.

**Por qué importa:** el modelo de escritura se optimiza para proteger reglas; el de lectura, para responder rápido. Separarlos evita que cada pantalla nueva presione para agregar campos, joins y atajos al agregado.

### Proyecciones

Una **proyección** es el proceso que construye y mantiene un modelo de lectura a partir de los eventos. Consume `EnvioCreado`, `EnvioAsignado`, `EnvioReprogramado`, `EntregaRegistrada` y actualiza las filas correspondientes. Tres propiedades la hacen confiable:

1. **Idempotente.** Los eventos llegan al menos una vez (ver [Event streaming](#t/event-streaming)); aplicar dos veces el mismo evento no debe cambiar el resultado. Se logra guardando la última posición o el último ID de evento aplicado por entidad.
2. **Ordenada por entidad.** Los eventos del mismo envío se procesan en orden; con Kafka, usando el ID del envío como clave de partición.
3. **Reconstruible.** Si la proyección tiene un bug, se borra el modelo de lectura y se vuelve a calcular desde el principio del historial.

```python
def aplicar(evento, db):
    fila = db.envios_por_zona.get(evento.envio_id)
    if fila and evento.secuencia <= fila.ultima_secuencia:
        return                                   # ya aplicado: idempotencia
    match evento.tipo:
        case "EnvioCreado":
            db.envios_por_zona.insertar(envio_id=evento.envio_id, zona=evento.zona,
                                        estado_visible="Preparando", ultima_secuencia=evento.secuencia)
        case "EnvioAsignado":
            db.envios_por_zona.actualizar(evento.envio_id, transportista_nombre=evento.nombre,
                                          estado_visible="Asignado", ultima_secuencia=evento.secuencia)
        case "EnvioReprogramado":
            db.envios_por_zona.actualizar(evento.envio_id, ventana=evento.ventana,
                                          ultima_secuencia=evento.secuencia)
```

**Ejemplo:** el mismo flujo de eventos alimenta cuatro proyecciones: `envios_por_zona` para operaciones, `seguimiento_destinatario` para el widget público, `estado_pedido` para el asistente de soporte y `entregas_por_hora` para un tablero. Cada una tiene su forma, sus índices y su retención.

**Por qué importa:** sumar una vista nueva no requiere tocar el modelo de escritura: se agrega una proyección y se la alimenta desde el historial.

### Consistencia eventual y lag

El precio de CQRS con modelos de lectura separados es que la lectura llega tarde. Entre el commit del comando y la actualización de la proyección pasa un tiempo, el **lag**.

**Ejemplo con números hipotéticos:** el relay de la outbox lee cada 200 ms (en promedio, 100 ms de espera), Kafka entrega en unos 50 ms y la proyección procesa en 30 ms. El lag típico ronda 180 ms. En hora pico, con el consumidor atrasado 4.000 eventos y procesando 1.000 por segundo, el lag sube a 4 segundos. Si el destinatario reprograma desde el widget y la página recarga a los 500 ms, todavía ve la ventana vieja.

Las estrategias para que el usuario no lo note:

1. **Devolver el resultado en la respuesta del comando.** La pantalla muestra la ventana nueva a partir de la respuesta, sin releer.
2. **Leer tu propia escritura.** El comando devuelve la versión resultante (`version: 9`); la consulta espera hasta que la proyección tenga versión 9 o más, con un tope de 1 a 2 segundos.
3. **Decidir con el modelo de escritura.** Las lecturas que preceden a un cambio (¿puedo reprogramar?) se resuelven en el agregado, nunca en la proyección.
4. **Medir y alertar el lag.** Una métrica de antigüedad del último evento aplicado, con alerta si supera, por ejemplo, 10 segundos.

**Por qué importa:** la consistencia eventual no es un bug, pero si nadie la diseña aparece como uno: usuarios que ven datos viejos y decisiones tomadas sobre ellos.

### Cuándo no usar CQRS

CQRS completo agrega piezas: eventos, proyecciones, lag, reconstrucciones, monitoreo. No conviene cuando:

- El servicio es un CRUD donde lo que se escribe y lo que se lee tienen la misma forma (configuración de zonas).
- Las lecturas son pocas y simples y la base aguanta los joins sin problema.
- El negocio no tolera ningún atraso en lo que se muestra y no hay forma de diseñar alrededor.
- El equipo no tiene cómo operar consumidores y reconstrucciones.

La versión liviana casi siempre vale: separar en el código los comandos de las consultas, y que las consultas no carguen agregados. Eso no requiere eventos ni otra base.

**Ejemplo:** el servicio de franjas horarias tiene 300 filas que cambian una vez por semana. Se resolvió con una tabla y un endpoint; una proyección habría agregado un consumidor que vigilar para nada.

### Event Sourcing: los eventos como fuente de verdad

En Event Sourcing el agregado no se guarda como una fila con su estado actual, sino como la lista ordenada de sus eventos en un **event store** (un almacén de eventos, que puede ser una tabla de Postgres con `(agregado_id, secuencia)` única). Para cargar el agregado se leen sus eventos y se aplican uno por uno sobre un estado inicial vacío. Para guardar, se agregan los eventos nuevos al final, verificando que la última secuencia sea la esperada: es la concurrencia optimista, ahora sobre el historial.

```kotlin
data class EstadoEnvio(
    val estado: Estado = Estado.NUEVO,
    val transportista: TransportistaId? = null,
    val ventana: VentanaHoraria? = null,
    val reprogramaciones: Int = 0,
)

fun aplicar(s: EstadoEnvio, e: EventoEnvio): EstadoEnvio = when (e) {
    is EnvioCreado       -> s.copy(estado = Estado.PENDIENTE, ventana = e.ventana)
    is EnvioAsignado     -> s.copy(estado = Estado.ASIGNADO, transportista = e.transportista)
    is EnvioReprogramado -> s.copy(ventana = e.ventana, reprogramaciones = s.reprogramaciones + 1)
    is EntregaRegistrada -> s.copy(estado = Estado.ENTREGADO)
}

fun reconstruir(eventos: List<EventoEnvio>) = eventos.fold(EstadoEnvio(), ::aplicar)
```

Las reglas siguen en el agregado: el comando `reprogramar` mira el estado reconstruido, verifica que `reprogramaciones < 2` y, si corresponde, produce un `EnvioReprogramado`. La función `aplicar` no valida nada: aplica hechos que ya ocurrieron.

**Ejemplo:** un envío con historial `Creado → Asignado → Reprogramado → Reasignado → Reprogramado` se reconstruye en 5 pasos. Con esa misma lista se puede responder "¿quién era el transportista el martes a las 15?" aplicando solo los eventos hasta ese instante, algo imposible si solo se guarda el estado actual.

**Por qué importa:** el historial completo da auditoría, depuración en el tiempo y la capacidad de crear proyecciones nuevas con datos del pasado. El costo es que el estado actual siempre es un cálculo, y que los eventos se vuelven un contrato que no se puede editar.

### Snapshots

Reconstruir desde cero es barato con pocos eventos y caro con muchos. Un **snapshot** guarda el estado calculado hasta cierta secuencia; para cargar, se lee el último snapshot y solo los eventos posteriores.

**Ejemplo:** un envío tiene entre 5 y 30 eventos en toda su vida: no necesita snapshots. El agregado `Transportista`, en cambio, acumula unos 60 eventos por día (turnos, asignaciones, capacidad); en dos años son unos 44.000. A 5 microsegundos por evento, reconstruirlo toma 220 ms, más la lectura. Con un snapshot cada 500 eventos, la carga lee como máximo 499 eventos: unos 2,5 ms de aplicación.

Los snapshots son una optimización descartable: si cambia la forma del estado, se borran y se regeneran desde los eventos. Por eso no conviene agregarlos hasta medir que hacen falta.

### Versionado de eventos y upcasting

Los eventos guardados no se modifican, pero el modelo evoluciona. Si `EnvioReprogramado` v1 tenía `motivo` como texto libre y v2 tiene `motivo` como valor de un conjunto cerrado, el event store contiene ambos. Las técnicas, de menor a mayor costo:

1. **Cambios compatibles:** agregar campos opcionales con valor por defecto. El código nuevo lee eventos viejos sin ayuda.
2. **Upcasting:** al leer, una función transforma el evento viejo a la forma nueva antes de aplicarlo. El almacén no cambia.
3. **Copiar y transformar:** migrar el historial a un event store nuevo con los eventos convertidos. Se reserva para cambios profundos.

```typescript
function upcast(e: EventoGuardado): EventoEnvio {
  if (e.tipo === "EnvioReprogramado" && e.version === 1) {
    return { ...e.datos, version: 2,
             motivo: normalizarMotivo(e.datos.motivo) ?? "otro",
             motivoOriginal: e.datos.motivo };
  }
  return e.datos;
}
```

**Ejemplo:** 1,8 millones de `EnvioReprogramado` v1 tenían motivos como "ausente", "Ausente." o "no estaba". El upcaster los normaliza al leer; los 14.000 que no se pueden normalizar quedan como `otro` con el texto original al lado.

**Por qué importa:** en Event Sourcing un esquema de evento mal pensado vive para siempre. Conviene revisar los eventos nuevos con el mismo cuidado que un contrato público.

### Datos personales y el derecho al borrado

El historial inmutable choca con la obligación de borrar datos personales a pedido (ver [Privacidad y datos personales](#t/privacidad-datos)). Si `EnvioCreado` contiene nombre, teléfono y dirección del destinatario, borrar esos datos implica editar el pasado, que es justo lo que el event store promete no hacer. Las opciones:

1. **Mantener la PII fuera de los eventos.** El evento lleva `destinatario_id`; los datos viven en un almacén aparte que sí se puede borrar. Es la opción preferida.
2. **Borrado criptográfico (crypto-shredding).** Los campos personales se cifran con una clave por destinatario; borrar la clave vuelve ilegibles todos sus eventos sin tocarlos.
3. **Reescritura del historial.** Posible, pero rompe la promesa de inmutabilidad y obliga a reconstruir proyecciones. Último recurso.

Además, las proyecciones copian datos: el borrado tiene que llegar también a cada modelo de lectura y a los snapshots.

**Ejemplo:** Rumbo guarda en `EnvioCreado` solo `destinatario_id` y una zona; la dirección completa está en el servicio de destinatarios. Una solicitud de borrado elimina la fila allí y publica `destinatario_borrado`, que cada proyección usa para anonimizar sus filas.

### Outbox, CQRS y Event Sourcing: cómo se combinan

Las tres piezas resuelven problemas distintos y se pueden usar por separado:

| Combinación | Qué se guarda | Cómo salen los eventos | Cuándo alcanza |
|---|---|---|---|
| Solo outbox | Estado actual | Tabla outbox en la misma transacción | Otros servicios necesitan enterarse de los cambios |
| CQRS sin Event Sourcing | Estado actual | Outbox o CDC alimentan proyecciones | Lecturas variadas o pesadas, sin necesidad de historial completo |
| Event Sourcing con CQRS | Eventos | El event store es la fuente; las proyecciones lo leen | Historial y auditoría son requisitos del negocio |
| Event Sourcing sin CQRS | Eventos | Igual | Casi nunca: consultar "todos los envíos pendientes de la zona" sin proyecciones obliga a reconstruir todos |

Con Event Sourcing, el event store cumple el papel de la outbox: el evento se escribe una sola vez, en la misma operación que "guarda" el agregado, y un relay o una suscripción lo publica. El patrón outbox en sí está en [Sistemas distribuidos](#t/sistemas-distribuidos).

**Ejemplo:** en Rumbo, Asignación usa estado actual con outbox y CQRS para sus vistas. Solo el historial de cambios de un envío (quién hizo qué y cuándo) se guarda como eventos completos, porque soporte y auditoría lo necesitan.

**Por qué importa:** "vamos a usar Event Sourcing" suele ser la respuesta a un problema que se resolvía con una outbox y una proyección.

### Modelos de lectura para agentes y el historial como auditoría

Los agentes son consumidores de lectura muy particulares: hacen muchas consultas, cada respuesta ocupa contexto (y tokens) y cuanto más tiene que unir el modelo por su cuenta, más chances de error. Un modelo de lectura diseñado para un agente resuelve las tres cosas.

**Ejemplo:** para responder "¿dónde está mi pedido?", el asistente de soporte llamaba a cuatro herramientas (pedido, envíos, seguimiento, ETA) y unía los datos en el razonamiento. Eso eran 4 llamadas, unos 3.000 tokens de respuestas crudas y errores frecuentes con pedidos de dos envíos. Con una proyección `estado_pedido` que tiene, por pedido, la lista de envíos con su estado visible, la ventana vigente, la ETA y un campo `resumen` ya armado ("2 envíos: uno entregado hoy 11:40, otro en reparto, llega entre 15:00 y 17:00"), la herramienta `consultar_estado_pedido` hace una consulta, devuelve unos 250 tokens y no tiene que razonar sobre la relación entre pedidos y envíos.

El otro lado es la auditoría. Cuando un agente ejecuta comandos, cada evento resultante debe llevar **metadatos de origen**: el actor humano en nombre de quien actuó, que fue un agente, la conversación o sesión, la herramienta llamada y la versión del prompt. Con eso, el historial de eventos (o la outbox, si no hay Event Sourcing) responde exactamente qué hizo el agente.

```json
{ "tipo": "EnvioReprogramado", "envio_id": "e-812", "secuencia": 6,
  "datos": { "ventana": "2026-11-09T15:00/17:00", "motivo": "destinatario_ausente" },
  "metadatos": { "actor": "dest-4471", "via": "agente_soporte",
                 "conversacion": "c-90af", "herramienta": "reprogramar_envio",
                 "prompt_version": "soporte-v14" } }
```

**Por qué importa:** ante la pregunta "¿el asistente reprogramó envíos que no debía?", sin metadatos la respuesta es una búsqueda en logs; con ellos es una consulta sobre el historial, filtrada por `via` y `prompt_version`, que además se puede comparar antes y después de un cambio de prompt.

## Casos prácticos

### "¿Dónde está mi pedido?" en una sola herramienta

**Situación:** el asistente de soporte respondía mal en el 9 % de las consultas sobre pedidos con varios envíos, según el golden set de evaluación, y cada respuesta consumía cuatro llamadas a herramientas.

**Qué se hace:** se construye la proyección `estado_pedido` alimentada por eventos de pedidos, envíos y ETA, con un resumen en lenguaje del dominio. La herramienta del agente lee esa proyección y devuelve también `actualizado_hace_segundos`; si supera 30, el agente aclara que el dato puede estar atrasado. Las respuestas incorrectas bajan en el golden set y el costo por conversación cae por la reducción de tokens.

### Una proyección con un bug

**Situación:** la proyección `entregas_por_hora` contaba dos veces las entregas reintentadas tras una caída del consumidor, porque no era idempotente. El tablero mostró una tasa de entregas a tiempo inflada durante tres días.

**Qué se hace:** se agrega el control de secuencia por envío, se crea una tabla nueva y se reconstruye la proyección leyendo los eventos desde el inicio de la retención, mientras la vieja sigue en servicio. Al terminar, se cambia la lectura a la tabla nueva. Nadie tuvo que corregir datos a mano porque la fuente (los eventos) estaba bien.

### Event Sourcing para la configuración de zonas

**Situación:** un equipo implementó Event Sourcing para el servicio de zonas (40 zonas, cambios mensuales). Cada cambio de esquema requería upcasters y cada consulta necesitaba una proyección.

**Qué se hace:** se reconoce que el requisito real era "saber quién cambió qué", no reconstruir estados pasados. Se vuelve a una tabla con estado actual y una tabla de auditoría con el cambio, el actor y la fecha. Se deja escrito en un ADR que Event Sourcing se reserva para agregados donde el historial es parte del negocio.

### Qué hizo el agente de operaciones el viernes

**Situación:** después de un cambio de prompt, operaciones sospechaba que el agente había reasignado envíos de más en la zona Sur.

**Qué se hace:** como todos los eventos llevan metadatos de origen, una consulta sobre el historial filtra `EnvioReasignado` con `via = agente_operaciones` y compara las versiones de prompt: 31 reasignaciones con la versión anterior en una semana y 212 con la nueva en un día. Se revierte el prompt, se revisan los 212 casos y se agrega un tope diario de reasignaciones por agente en el caso de uso.

## Errores comunes

- **Adoptar CQRS y Event Sourcing juntos "por arquitectura".** Se suman todos los costos sin necesitar los beneficios. Empezar por separar comandos y consultas en el código, y agregar proyecciones o eventos donde haya un problema concreto.
- **Proyecciones que no son idempotentes.** Con entrega al menos una vez, cuentan doble. Guardar la última secuencia aplicada por entidad.
- **Tomar decisiones sobre el modelo de lectura.** Una proyección atrasada lleva a reprogramar o asignar sobre datos viejos. Las decisiones pasan por el agregado.
- **Datos personales dentro de eventos inmutables.** Vuelven imposible el borrado. Referenciar por ID o cifrar con clave por persona.
- **Eventos diseñados sin cuidado.** En Event Sourcing son permanentes. Revisarlos como un contrato y planificar el versionado desde el primer día.
- **Comandos de agentes sin metadatos de origen.** Se pierde la capacidad de auditar qué hizo el agente. Registrar actor, vía, sesión, herramienta y versión de prompt en cada evento.

## Para discutir en equipo

- ¿Qué pantallas o herramientas de agente sufren hoy por leer del modelo de escritura, y cuál sería su proyección ideal?
- ¿Cuánto lag de lectura toleramos en cada vista, y lo estamos midiendo?
- ¿Hay algún agregado donde el historial completo sea un requisito del negocio y no solo algo deseable?
- ¿Qué eventos nuestros contienen datos personales, y cómo responderíamos hoy a una solicitud de borrado?
- Si mañana hay que explicar qué hizo un agente en una semana, ¿qué consulta corremos y qué datos nos faltan?
