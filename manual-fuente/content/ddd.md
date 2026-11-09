---
slug: ddd
titulo: Domain-Driven Design
resumen: Enfoque para modelar software complejo desde el lenguaje y los límites del negocio, con contextos acotados, agregados y eventos que también ordenan agentes.
lectura: 15
---

## La idea central

Domain-Driven Design (DDD, diseño guiado por el dominio) parte de una observación simple: en un sistema con lógica de negocio real, la parte difícil no es la tecnología sino **entender el negocio** y que el código lo refleje con fidelidad. Cuando el equipo de operaciones dice "el envío quedó huérfano" y el código dice `order.status = 7`, cada conversación entre negocio e ingeniería necesita un traductor, y en cada traducción se pierde algo. DDD propone cerrar esa brecha: hablar el mismo idioma, dividir el sistema donde el negocio se divide y proteger las reglas importantes dentro de objetos que no se puedan dejar en un estado inválido.

Tiene dos mitades. El **diseño estratégico** responde dónde trazar los límites: qué partes del negocio son distintas, qué palabras significan qué en cada una y cómo se relacionan. El **diseño táctico** responde cómo modelar el interior de cada parte: entidades, objetos de valor, agregados, eventos. La mayoría de los equipos que "prueban DDD y no les sirve" empezaron por la táctica y se saltearon la estrategia. Para nosotros hay un motivo extra: los límites que DDD dibuja resultan ser buenos límites para herramientas de agentes, subagentes y prompts, porque el modelo también lee nuestro vocabulario.

## Conceptos

### Lenguaje ubicuo

El **lenguaje ubicuo** (*ubiquitous language*) es el vocabulario que comparten negocio e ingeniería dentro de un área, y que aparece igual en las conversaciones, la documentación, el código, las tablas, los eventos y las APIs. Se construye en conjunto: los ingenieros preguntan, los expertos del negocio corrigen, y cuando una palabra resulta ambigua se decide qué significa y se usa solo así.

El trabajo concreto es detectar sinónimos y homónimos. En Rumbo, operaciones usaba "pedido", "envío", "orden" y "paquete" como si fueran lo mismo. Al preguntar, resultó que no: un **pedido** es lo que el comercio carga (puede tener varios bultos), un **envío** es el traslado físico que hace un transportista (un pedido puede generar dos envíos si no entra en un solo vehículo) y un **bulto** es cada paquete. "Orden" no significaba nada distinto y se descartó.

**Ejemplo:** antes, el código tenía `Order.Reassign()`. Después, `Envio.Reasignar(transportista, motivo)`, y el evento pasó de `order_updated` a `envio_reasignado`. Cuando operaciones lee una traza o un log, entiende lo que pasó sin preguntar.

**Por qué importa:** cada término mal usado es un bug latente. Si "entregado" significa "el transportista marcó entregado" en un servicio y "el destinatario confirmó" en otro, las métricas de entregas a tiempo no van a coincidir y nadie sabrá por qué.

### Subdominios: core, de soporte y genéricos

El **dominio** es el negocio entero. Se divide en **subdominios**, áreas del negocio con lógica propia, que no valen todas lo mismo:

- **Core (central):** donde la empresa se diferencia de la competencia. Merece el mejor equipo, el modelo más cuidado y desarrollo propio.
- **De soporte:** necesario y específico del negocio, pero no diferencial. Se construye, con menos inversión.
- **Genérico:** problemas resueltos que cualquier empresa tiene. Se compra o se usa un producto existente.

| Subdominio en Rumbo | Tipo | Decisión |
|---|---|---|
| Asignación de transportistas | Core | Equipo propio, modelo de ML, DDD táctico completo |
| Cálculo de ETA | Core | Equipo de ML, contrato estable con asignación |
| Gestión de franjas y zonas | Soporte | Servicio propio, simple, casi CRUD |
| Soporte al destinatario | Soporte | Asistente con LLM sobre casos de uso propios |
| Notificaciones (SMS, correo, push) | Genérico | Proveedor externo detrás de un adaptador |
| Identidad y acceso | Genérico | Proveedor de identidad estándar |

**Por qué importa:** el error más caro es invertir como core en algo genérico (construir un motor de notificaciones propio) o tratar como genérico algo core (usar un asignador de un proveedor que no entiende nuestras zonas).

### Contextos acotados

Un **contexto acotado** (*bounded context*) es un límite explícito dentro del cual un modelo y su lenguaje son consistentes. Fuera de ese límite, la misma palabra puede significar otra cosa, y está bien. Es un límite lingüístico y de modelo, y en la práctica suele coincidir con un servicio, un repositorio o un equipo.

En Rumbo, "transportista" significa cosas distintas según el contexto:

- En **Asignación**: alguien con ubicación actual, capacidad libre, zona y tasa de entregas a tiempo.
- En **Turnos**: alguien con horas trabajadas y kilómetros recorridos.
- En **Soporte**: un nombre y un teléfono enmascarado para que el destinatario lo contacte.

Intentar un único objeto `Transportista` que sirva a los tres termina en una clase de 60 campos donde cada equipo teme tocar lo de los demás. DDD propone tres modelos chicos, cada uno dueño de su significado, que se traducen en los bordes.

**Ejemplo:** un contexto acotado de Asignación contiene `Envio`, `Candidato`, `Asignacion` y la regla de elección. No contiene datos de contacto del destinatario, porque no los necesita para decidir. Eso además reduce la superficie de PII.

### Mapas de contexto

Un **mapa de contexto** dibuja cómo se relacionan los contextos acotados y quién depende de quién. Las relaciones más usadas:

- **Cliente–proveedor (customer–supplier):** el contexto de abajo (cliente) depende del de arriba (proveedor), y el proveedor tiene en cuenta sus necesidades al planificar.
- **Capa anticorrupción (ACL):** el cliente traduce el modelo ajeno al propio en un adaptador, para que conceptos extraños no se filtren a su dominio. Se usa con sistemas legados o externos.
- **Núcleo compartido (shared kernel):** dos contextos comparten un pedazo pequeño de modelo y código, y lo cambian de común acuerdo. Útil, pero acopla.
- **Lenguaje publicado (published language):** un formato de intercambio documentado y versionado, como los esquemas de eventos en Kafka.
- **Conformista:** el cliente adopta el modelo del proveedor tal cual, porque no tiene poder para negociar ni vale la pena traducir.

```text
   [Pedidos] --(lenguaje publicado: pedido_creado)--> [Asignación] (core)
                                                         |   ^
                                    envio_asignado       |   | cliente–proveedor
                                                         v   |
   [Soporte] <--(lenguaje publicado)-- [Seguimiento]   [ETA (ML)]
       |
       +--ACL--> [Proveedor de notificaciones] (genérico)
       +--ACL--> [Proveedor de LLM]
   [Asignación] ==núcleo compartido (Zona, FranjaHoraria)== [Franjas y zonas]
```

**Por qué importa:** el mapa hace visibles los acoplamientos y negociaciones entre equipos. Si Asignación es cliente de ETA, un cambio en el contrato de ETA necesita aviso y versionado, no un deploy sorpresa.

### Entidades y objetos de valor

Entramos en el diseño táctico. Una **entidad** es un objeto con identidad que persiste en el tiempo aunque cambien sus atributos: un `Envio` sigue siendo el mismo envío aunque cambien su fecha, su transportista y su estado. Dos envíos con los mismos datos pero distinto ID son envíos distintos.

Un **objeto de valor** (*value object*) no tiene identidad: se define por sus atributos, es inmutable y se compara por valor. Una `Direccion`, una `VentanaHoraria`, una `Distancia` o un `CodigoZona` son objetos de valor. Su gran utilidad es que **se validan al construirse**: si un `CodigoZona` existe, es válido.

```go
type VentanaHoraria struct{ desde, hasta time.Time }

func NuevaVentana(desde, hasta time.Time) (VentanaHoraria, error) {
    if !hasta.After(desde) {
        return VentanaHoraria{}, errors.New("la ventana termina antes de empezar")
    }
    if hasta.Sub(desde) > 4*time.Hour {
        return VentanaHoraria{}, errors.New("una ventana no puede durar más de 4 horas")
    }
    return VentanaHoraria{desde, hasta}, nil
}
```

**Ejemplo:** con `string` para la zona, un `"Norte "` con un espacio al final pasa por tres servicios antes de romper una consulta. Con `CodigoZona`, falla en el borde, con un mensaje claro.

### Agregados e invariantes

Un **agregado** es un grupo de entidades y objetos de valor que se tratan como una unidad para los cambios, con una entidad **raíz** como única puerta de entrada. Existe para proteger **invariantes**: reglas que tienen que ser verdad siempre, después de cada operación. Las reglas de diseño son:

1. Desde afuera solo se referencia la raíz; los objetos internos se modifican a través de ella.
2. Una transacción modifica un solo agregado.
3. Otros agregados se referencian por ID, no por objeto.
4. Los agregados se mantienen chicos.

**Ejemplo trabajado: el agregado `Envio`.** Contiene la entidad raíz `Envio`, una lista de `Bulto` (entidades internas), una `VentanaHoraria` y una `Direccion` (objetos de valor), el `TransportistaID` (referencia por ID a otro agregado) y un historial de reprogramaciones. Sus invariantes:

- Un envío `en_reparto` siempre tiene transportista asignado.
- El peso total de los bultos no supera 30 kg (límite hipotético por envío de moto).
- No hay más de 2 reprogramaciones.
- Un envío `entregado` no cambia más.

```go
func (e *Envio) AgregarBulto(b Bulto) error {
    if e.estado != Pendiente {
        return ErrEnvioNoModificable
    }
    if e.pesoTotal()+b.Peso > 30 {
        return ErrPesoExcedido
    }
    e.bultos = append(e.bultos, b)
    return nil
}

func (e *Envio) SalirAReparto() error {
    if e.transportista == "" {
        return ErrSinTransportista
    }
    e.estado = EnReparto
    e.registrar(EnvioSalioAReparto{ID: e.id, Transportista: e.transportista})
    return nil
}
```

Con números: el envío tiene bultos de 12 kg y 15 kg (27 kg). Agregar uno de 5 kg da 32 kg y falla. Si `bultos` fuera un campo público, cualquier servicio podría hacer `envio.Bultos = append(...)` y la invariante dejaría de existir. ¿Por qué el `Transportista` no está dentro del agregado? Porque si lo estuviera, actualizar la ubicación del transportista (cada pocos segundos) bloquearía el envío, y reasignar un envío obligaría a cargar al transportista completo.

**Por qué importa:** los agregados definen los límites de consistencia. Lo que está dentro es consistente al instante; lo que cruza agregados es consistente eventualmente, mediante eventos.

### Repositorios y servicios de dominio

Un **repositorio** guarda y recupera agregados completos, con una interfaz que parece una colección: `Obtener(id)`, `Guardar(envio)`. Hay un repositorio por agregado, no por tabla: `RepositorioEnvios` guarda el envío con sus bultos, aunque en Postgres sean dos tablas. La interfaz la define el dominio y la implementación vive en un adaptador (ver [Arquitectura en capas, hexagonal y limpia](#t/arquitectura-capas-hexagonal)).

Un **servicio de dominio** contiene lógica de negocio que no pertenece naturalmente a una sola entidad. Elegir el mejor transportista para un envío involucra al envío, a varios candidatos y a las estimaciones de ETA: no es responsabilidad del `Envio` ni de un `Transportista`. `ElectorDeTransportista` es un servicio de dominio, sin estado, con nombre del lenguaje ubicuo. No confundirlo con un servicio de aplicación, que orquesta (carga, invoca, guarda) pero no contiene reglas.

### Eventos de dominio

Un **evento de dominio** registra algo que pasó y que le importa al negocio, nombrado en pasado y con el lenguaje ubicuo: `envio_asignado`, `envio_reprogramado`, `entrega_fallida`. Lo genera el agregado al cambiar de estado, como en `SalirAReparto` de arriba.

Dentro de un contexto, los eventos permiten reaccionar sin acoplar: al reasignar, se libera la capacidad del transportista anterior en otra transacción. Entre contextos, se publican como **eventos de integración** en Kafka, con un esquema versionado que es el lenguaje publicado del mapa de contexto (ver [Event streaming](#t/event-streaming)). La distinción importa: un evento de dominio interno puede cambiar libremente; uno publicado es un contrato con otros equipos. Para no perder eventos cuando se guarda el agregado y se publica después, se usa el patrón outbox.

**Ejemplo:** `entrega_fallida` con motivo `destinatario_ausente` dispara, en Soporte, la creación de un caso; en Pronóstico, el ajuste de la tasa de fallos por zona; y en Asignación, nada.

### Event storming

El **event storming** es un taller de descubrimiento donde negocio e ingeniería reconstruyen un proceso con notas adhesivas (o su versión en una pizarra digital). Los pasos típicos:

1. Cada participante escribe **eventos** de dominio en naranja, en pasado, y los pega en una línea de tiempo: "pedido cargado", "envío asignado", "transportista rechazó", "entrega fallida".
2. Se ordenan y se discuten huecos y contradicciones. Acá aparecen los homónimos ("¿entregado cuándo, exactamente?").
3. Se agregan **comandos** en azul (lo que provoca cada evento), **actores**, **políticas** ("cuando X, entonces Y") y **sistemas externos**.
4. Se marcan **puntos calientes** en rosa: dudas, conflictos, dolores.
5. Se buscan agrupaciones naturales: suelen ser los contextos acotados y los agregados.

**Ejemplo:** en un taller de tres horas sobre devoluciones, el equipo descubrió que "devolución" eran dos procesos distintos (rechazo en puerta y devolución posterior), con reglas y actores diferentes. Terminaron como dos flujos en el mismo contexto en lugar de uno lleno de condicionales.

### Cuándo DDD es demasiado

DDD táctico completo tiene costo: más clases, más mapeo, más conversaciones. No conviene para:

- Servicios CRUD sin reglas (el administrador de plantillas de notificación).
- Subdominios genéricos, que se compran.
- Prototipos cuyo dominio todavía no se entiende y va a cambiar en semanas.
- Equipos sin acceso a expertos del negocio: sin ellos no hay lenguaje ubicuo, solo nombres nuevos.

El diseño estratégico, en cambio, casi siempre vale: nombrar bien, dibujar el mapa de contexto y decidir dónde invertir es barato y evita los errores más caros.

### DDD aplicado a agentes

Los conceptos de DDD encajan sorprendentemente bien con los sistemas con LLMs:

- **Contextos acotados como límites de herramientas.** Un servidor [MCP](#t/mcp) por contexto (`rumbo-asignacion`, `rumbo-soporte`) agrupa herramientas que comparten vocabulario y permisos. Un agente de soporte se conecta al de soporte y no ve herramientas de asignación.
- **Contextos acotados como límites de subagentes.** Un orquestador puede delegar a un subagente por contexto, cada uno con instrucciones, herramientas y glosario propios, en lugar de un agente con 40 herramientas mezcladas (ver [Subagentes y sistemas multiagente](#t/subagentes)).
- **Lenguaje ubicuo en nombres, descripciones y prompts.** El modelo elige herramientas leyendo sus nombres y descripciones. `reprogramar_envio` con "un envío es el traslado físico; un pedido puede tener varios envíos" evita que el modelo confunda conceptos, igual que evita que los confunda una persona nueva.
- **Eventos de dominio como disparadores de agentes.** `entrega_fallida` en una zona, si se repite 50 veces en una hora, puede disparar al agente de operaciones para investigar. El agente consume el lenguaje publicado, no tablas internas.
- **Capa anticorrupción entre el LLM y el dominio.** La salida de un modelo es un sistema externo poco confiable. Se trata como tal: se parsea y se valida para construir objetos de valor (`CodigoZona`, `VentanaHoraria`, `MotivoReprogramacion`) antes de tocar un agregado. Si el modelo devuelve "zona: el norte, cerca del puerto", la construcción falla en el borde y el dominio nunca ve ese texto.

## Casos prácticos

### Un "transportista" para todos

**Situación:** el struct `Transportista` compartido entre Asignación, Turnos y Soporte llegó a 58 campos. Un cambio de Turnos (agregar horas extra) rompió la serialización en Asignación y provocó 20 minutos de asignaciones fallidas.

**Qué se hace:** se dibuja el mapa de contexto y se separan tres modelos. Asignación mantiene su `Candidato` con 9 campos; Turnos, el suyo; Soporte, un `ContactoTransportista` mínimo. Se sincronizan con eventos publicados (`transportista_actualizado`) y cada contexto traduce lo que necesita. El blast radius de un cambio queda dentro de un contexto.

### El agente que confundía pedido y envío

**Situación:** el asistente de soporte respondía "su pedido fue entregado" cuando solo uno de los dos envíos de ese pedido había llegado. Las herramientas se llamaban `get_order_status` y `get_shipment`, con descripciones vagas, y el prompt usaba "pedido" y "envío" como sinónimos.

**Qué se hace:** se alinean las herramientas con el lenguaje ubicuo: `consultar_pedido` devuelve el pedido con la lista de sus envíos y el estado de cada uno; la descripción explica que un pedido está entregado solo si todos sus envíos lo están. El prompt incluye un glosario de cinco términos. En el golden set de evaluación, las respuestas incorrectas sobre estado bajan de forma clara en las conversaciones con pedidos de varios envíos.

### Integrar un proveedor de notificaciones sin contaminar el dominio

**Situación:** el proveedor externo de SMS usa los conceptos `campaign`, `audience` y `template_id`, y empezaban a aparecer en el código de Soporte, con un `campaign_id` guardado en la tabla de casos.

**Qué se hace:** se reconoce Notificaciones como subdominio genérico y se pone una capa anticorrupción. El dominio de Soporte habla de `AvisoAlDestinatario` con un `TipoAviso`; el adaptador lo traduce al modelo del proveedor. Cuando seis meses después se cambia de proveedor, solo cambia el adaptador.

### Clasificación de tickets que inventaba motivos

**Situación:** un LLM clasifica los mensajes de los destinatarios y su salida se guardaba directo como texto en el campo `motivo` del envío. Aparecieron 140 motivos distintos en una semana, incluidos "ausente", "Ausente." y "no estaba en casa", y los reportes por motivo dejaron de servir.

**Qué se hace:** se define el objeto de valor `MotivoReprogramacion` con un conjunto cerrado de valores y la capa anticorrupción valida la salida del modelo contra ese conjunto, usando salida estructurada con un `enum`. Lo que no valida va a `otro` con el texto original en un campo aparte para revisión. El agregado solo acepta motivos válidos.

## Errores comunes

- **Empezar por la táctica.** Crear agregados y repositorios sin haber definido contextos ni lenguaje produce las mismas confusiones con más clases; empezar por el mapa de contexto.
- **Agregados enormes.** Un `Pedido` que contiene envíos, transportistas y casos de soporte genera bloqueos y transacciones lentas; mantenerlos chicos y referenciar por ID.
- **Modelo anémico.** Entidades con solo getters y setters y las reglas en servicios dispersos; las invariantes van dentro del agregado.
- **Publicar eventos internos como contrato.** Exponer en Kafka cada evento de dominio ata a otros equipos a detalles internos; publicar eventos de integración versionados y deliberados.
- **Tratar la salida del LLM como dato confiable.** Todo lo que viene de un modelo pasa por una capa anticorrupción que construye objetos de valor o falla.
- **Lenguaje ubicuo solo en el código.** Si el prompt, las descripciones de herramientas y los dashboards usan otras palabras, el modelo y las personas vuelven a confundirse.

## Para discutir en equipo

- ¿Qué palabras usamos con dos significados distintos entre equipos, y dónde nos causó un incidente o una métrica que no cerraba?
- Si dibujamos hoy el mapa de contexto de Rumbo, ¿qué relación nos sorprende o nos incomoda?
- ¿Qué parte de lo que construimos es genérica y deberíamos comprar o simplificar?
- ¿Nuestras herramientas de agente están agrupadas por contexto acotado o por conveniencia técnica?
- ¿Qué eventos de dominio podrían disparar un agente hoy, y cuáles no deberían hacerlo sin aprobación humana?
