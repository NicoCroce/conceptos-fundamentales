---
slug: ddd-tactico
titulo: DDD táctico: entidades, objetos de valor y agregados
resumen: Cómo modelar el interior de un contexto con entidades, objetos de valor, agregados, eventos y fábricas para que las reglas del negocio no se puedan saltear, ni siquiera desde un agente.
lectura: 16
---

## La idea central

El tema [Domain-Driven Design](#t/ddd) explica dónde trazar los límites: subdominios, contextos acotados y lenguaje ubicuo. Este tema baja un nivel y responde la pregunta que aparece al día siguiente: una vez que sabemos que el contexto de Asignación es dueño del `Envio`, ¿cómo escribimos el `Envio` para que nadie, ni un servicio apurado, ni un script de soporte, ni un agente con LLM, pueda dejarlo en un estado que el negocio considera imposible?

La respuesta del diseño táctico es poner las reglas **dentro** de los objetos y cerrar las demás puertas. Lo que tiene identidad se modela como entidad; lo que solo describe algo, como objeto de valor inmutable que se valida al nacer; y lo que tiene que cambiar junto se encierra en un agregado con una sola puerta de entrada, la raíz. Es como un mostrador: el cliente no entra al depósito a mover cajas, pide y el empleado aplica las reglas. Un agente es un cliente más, solo que pide cosas con mucha más creatividad.

## Conceptos

### Entidades e identidad

Una **entidad** es un objeto que importa por **quién es**, no por lo que contiene en un momento dado. Un envío nace pendiente, se asigna, sale a reparto, se reprograma y se entrega; cambian casi todos sus atributos, pero sigue siendo el mismo envío. Lo que lo hace "el mismo" es su identidad.

Tres decisiones prácticas acompañan a cada entidad:

1. **Quién genera la identidad.** Si la genera la base (una secuencia), el objeto no tiene ID hasta que se guarda, y no se pueden emitir eventos ni referenciarlo antes. Si la genera la aplicación (un UUID o un ULID, que además se ordena por tiempo), el objeto es completo desde que se crea. En Rumbo se usa la segunda opción: `EnvioId` se genera al crear el envío.
2. **Cómo se compara.** Dos entidades son iguales si tienen el mismo ID, aunque difieran en otros campos. Comparar por todos los campos es un error: una copia vieja y una nueva del mismo envío dejarían de ser "el mismo".
3. **Un tipo por identidad.** `EnvioId`, `PedidoId` y `TransportistaId` como tipos distintos, no tres `String`. Así el compilador impide pasar un ID de pedido donde se espera uno de envío.

**Ejemplo:** la función `asignar(envioId: String, transportistaId: String)` se llamó con los argumentos invertidos tras un refactor, y durante 40 minutos las asignaciones fallaron con "envío inexistente". Con `EnvioId` y `TransportistaId` como tipos propios, esa llamada no compila.

**Por qué importa:** la identidad es lo que permite seguir un objeto a través de eventos, logs, trazas y conversaciones con un agente.

### Objetos de valor en profundidad

Un **objeto de valor** describe algo y no tiene identidad propia: dos `Peso` de 12 kg son intercambiables. El tema de DDD ya lo presenta; acá interesan las cuatro propiedades que lo hacen útil:

1. **Inmutable.** No se modifica: se crea uno nuevo. Sumar un bulto no "cambia" el peso total, produce otro `Peso`.
2. **Igualdad por valor.** Se compara por sus atributos. En Kotlin, una `data class` lo da gratis.
3. **Validado en el constructor.** Si existe, es válido. No hay `Peso` negativo ni `VentanaHoraria` que termine antes de empezar.
4. **Con comportamiento.** No es solo un contenedor: sabe sumarse, compararse, superponerse con otra ventana o normalizarse.

```kotlin
data class Peso(val gramos: Int) {
    init { require(gramos >= 0) { "El peso no puede ser negativo" } }
    operator fun plus(otro: Peso) = Peso(gramos + otro.gramos)
    operator fun compareTo(otro: Peso) = gramos.compareTo(otro.gramos)
    companion object { fun kilos(kg: Double) = Peso((kg * 1000).roundToInt()) }
}

data class VentanaHoraria(val desde: Instant, val hasta: Instant) {
    init {
        require(hasta.isAfter(desde)) { "La ventana termina antes de empezar" }
        require(Duration.between(desde, hasta) <= Duration.ofHours(4)) { "Máximo 4 horas" }
    }
    fun seSuperponeCon(otra: VentanaHoraria) = desde < otra.hasta && otra.desde < hasta
}

data class Direccion(val calle: String, val numero: String, val codigoPostal: String, val ciudad: String) {
    init {
        require(calle.isNotBlank() && numero.isNotBlank()) { "Calle y número son obligatorios" }
        require(codigoPostal.matches(Regex("[A-Z0-9]{4,8}"))) { "Código postal inválido" }
    }
}
```

El error que estos objetos evitan tiene nombre: **obsesión por los primitivos**, modelar todo con `Int`, `String` y `Double`. Un `peso: Double` no dice si está en kilos o en gramos, ni impide valores negativos.

**Ejemplo:** la app del transportista enviaba el peso en gramos y el panel de comercios en kilos. Un bulto de 2.500 g se guardó como 2.500 kg y bloqueó la asignación de una moto con límite de 30 kg. Con `Peso` y fábricas explícitas (`Peso.kilos(2.5)`, `Peso(gramos = 2500)`) la unidad queda en el nombre y la conversión se hace una sola vez.

**Por qué importa:** cada validación que vive en el constructor es una validación que no hay que repetir en cada handler, en cada consumidor de eventos ni en cada herramienta de agente.

### Agregado y raíz: el límite de consistencia

Un **agregado** es un grupo de objetos que se modifican juntos y que comparten **invariantes**, reglas que deben cumplirse después de cada operación. La **raíz** es la única entidad visible desde afuera: los demás objetos del grupo solo se tocan a través de sus métodos. El agregado es, además, el **límite de consistencia**: todo lo que está adentro es consistente al terminar cada transacción; lo que está afuera se pone al día después, con eventos.

```arbol
titulo: Agregado Envio
Envio (raíz)
- Identidad
-- EnvioId
- Referencias por ID
-- PedidoId
-- TransportistaId
- Objetos de valor
-- Direccion
-- VentanaHoraria
-- Peso total
- Entidades internas
-- Bulto
-- Intento de entrega
- Eventos pendientes
```

En código, la raíz expone **comandos con nombre del negocio** y oculta el estado. No hay setters:

```kotlin
class Envio private constructor(
    val id: EnvioId,
    val pedidoId: PedidoId,
    private val destino: Direccion,
    private var ventana: VentanaHoraria,
    private val bultos: MutableList<Bulto>,
    private var estado: EstadoEnvio,
    private var transportista: TransportistaId?,
    private var reprogramaciones: Int,
) {
    private val eventos = mutableListOf<EventoDominio>()

    fun asignar(t: TransportistaId) {
        check(estado == EstadoEnvio.PENDIENTE) { "Solo se asigna un envío pendiente" }
        transportista = t
        estado = EstadoEnvio.ASIGNADO
        eventos += EnvioAsignado(id, t)
    }

    fun reprogramar(nueva: VentanaHoraria, motivo: MotivoReprogramacion, ahora: Instant) {
        check(estado == EstadoEnvio.PENDIENTE || estado == EstadoEnvio.ASIGNADO) { "Ya salió a reparto" }
        check(reprogramaciones < 2) { "El envío ya se reprogramó 2 veces" }
        require(nueva.desde.isAfter(ahora.plus(Duration.ofHours(2)))) { "Debe empezar en 2 h o más" }
        ventana = nueva
        reprogramaciones++
        eventos += EnvioReprogramado(id, nueva, motivo)
    }

    fun agregarBulto(b: Bulto) {
        check(estado == EstadoEnvio.PENDIENTE) { "El envío ya no admite bultos" }
        val total = bultos.fold(Peso(0)) { acc, x -> acc + x.peso } + b.peso
        check(total <= Peso.kilos(30.0)) { "Supera 30 kg por envío" }
        bultos += b
    }

    fun extraerEventos(): List<EventoDominio> = eventos.toList().also { eventos.clear() }

    override fun equals(other: Any?) = other is Envio && other.id == id
    override fun hashCode() = id.hashCode()
}
```

En producción conviene reemplazar `check` y `require` por errores de dominio tipados (`EnvioYaEnReparto`, `LimiteReprogramaciones`), porque esos errores se traducen después a respuestas de API y a mensajes para el agente.

**Ejemplo:** el envío tiene dos bultos de 12 kg y 15 kg. Llamar a `agregarBulto` con uno de 5 kg calcula 32 kg y falla. No hay forma de llegar a `bultos` sin pasar por ese método, porque la lista es privada y el constructor también.

**Por qué importa:** si las invariantes están en la raíz, se cumplen en todos los caminos de entrada a la vez. Si están en los servicios que llaman, cada camino nuevo (un job, un consumidor, una herramienta de agente) es una oportunidad de olvidarlas.

### Cuánto debe abarcar un agregado: el costo de la contención

La tentación es armar agregados grandes, "para que todo sea consistente". El costo aparece bajo concurrencia: como el agregado se guarda entero y se protege con una versión (ver [Patrón Repository y Unit of Work](#t/patron-repository)), dos cambios simultáneos sobre el mismo agregado chocan aunque toquen partes distintas.

Una aproximación útil: si un agregado recibe escrituras a una tasa de λ por segundo y cada transacción tarda w segundos entre leer y guardar, la probabilidad de que otra escritura se cruce es, para valores chicos, cerca de λ × w.

**Ejemplo:** el equipo evaluó modelar una `RutaDelDia` por zona, con todos sus envíos adentro. Con números hipotéticos de la zona Norte en hora pico:

| Diseño | Escrituras sobre el agregado | Duración de la transacción | Probabilidad de choque |
|---|---|---|---|
| `RutaDelDia` con 3.000 envíos | 600 envíos × 4 cambios por hora = 2.400 por hora, 0,67 por segundo | 400 ms (cargar y guardar 3.000 envíos) | 0,67 × 0,4 ≈ 27 % |
| `Envio` como agregado | 4 cambios por hora, 0,0011 por segundo | 20 ms | 0,0011 × 0,02 ≈ 0,002 % |

Con el agregado grande, más de una de cada cuatro escrituras se reintenta, y cada reintento vuelve a cargar 3.000 envíos, lo que alarga la transacción y aumenta los choques. Con el agregado chico, los choques prácticamente desaparecen. La regla "no más de 40 envíos por ruta" se resuelve igual, pero de otra forma: una `Ruta` chica con la lista de `EnvioId` asignados, separada de los envíos.

El criterio para decidir el tamaño es preguntar qué invariante necesita **consistencia inmediata**. "Un envío no supera 30 kg" la necesita: va adentro. "La ruta del día debería estar balanceada entre transportistas" tolera unos segundos de atraso: va en otro agregado o en un proceso que reacciona a eventos.

**Por qué importa:** el tamaño del agregado decide la escalabilidad de las escrituras. Es una decisión de diseño que se cambia con dificultad después de tener datos y eventos en producción.

### Referencias por ID entre agregados

Un agregado apunta a otro por su identidad, nunca por el objeto: `Envio` guarda un `TransportistaId`, no un `Transportista`. Eso tiene tres efectos:

1. **Cargar un envío no carga al transportista.** Sin referencias de objeto no hay grafos enormes ni lazy loading sorpresa que dispara 200 consultas.
2. **No se puede modificar dos agregados en una operación por accidente.** Si `envio.transportista.capacidad--` fuera posible, la transacción del envío estaría cambiando al transportista.
3. **La consistencia entre ambos es explícita.** Si al asignar hay que reducir la capacidad libre del transportista, se hace en una segunda transacción que reacciona al evento `EnvioAsignado`, o en un caso de uso que asume conscientemente el costo de tocar dos agregados.

**Ejemplo:** al asignar, el envío se guarda con `transportista = t-7` y emite `EnvioAsignado`. Un manejador, en otra transacción, carga el agregado `Transportista t-7` y descuenta capacidad. Si ese segundo paso falla porque el transportista se quedó sin capacidad, se emite `AsignacionRechazada` y el envío vuelve a pendiente: una compensación, como en una saga (ver [Sistemas distribuidos](#t/sistemas-distribuidos)).

**Por qué importa:** las referencias por ID son lo que permite, más adelante, separar agregados en servicios distintos sin reescribir el modelo.

### Servicios de dominio frente a servicios de aplicación

Ambos se llaman "servicio" y se confunden seguido. La diferencia es qué contienen:

| | Servicio de dominio | Servicio de aplicación (caso de uso) |
|---|---|---|
| Qué hace | Aplica una regla del negocio que involucra varios objetos | Orquesta: carga, invoca, guarda, publica |
| Sabe de infraestructura | No | Sí, a través de puertos (repositorios, reloj, colas) |
| Transacción | No la maneja | La abre y la cierra |
| Ejemplo en Rumbo | `ElectorDeTransportista`, `CalculadorDeVentanas` | `AsignarEnvio`, `ReprogramarEntrega` |
| Cómo se testea | Con objetos en memoria, sin dobles | Con repositorios falsos (ver [Testing y dobles de prueba](#t/testing-dobles)) |

```kotlin
class ReprogramarEntrega(
    private val envios: RepositorioEnvios,
    private val reloj: Clock,
    private val uow: UnidadDeTrabajo,
) {
    fun ejecutar(actor: Actor, id: EnvioId, ventana: VentanaHoraria, motivo: MotivoReprogramacion) =
        uow.enTransaccion {
            val envio = envios.obtener(id) ?: throw EnvioNoEncontrado(id)
            actor.verificarPuedeOperar(envio.pedidoId)       // autorización
            envio.reprogramar(ventana, motivo, reloj.instant()) // regla de negocio
            envios.guardar(envio)
        }
}
```

Una señal de alarma es un servicio de aplicación con `if` sobre el estado del envío: esa lógica pertenece al agregado o a un servicio de dominio.

**Por qué importa:** si las reglas viven en el caso de uso, un segundo caso de uso que toque el mismo agregado (por ejemplo, una reprogramación masiva) tiene que duplicarlas, y tarde o temprano divergen.

### Eventos de dominio: emitir y despachar

El tema de DDD define los eventos de dominio; acá interesa la mecánica. Hay dos momentos separados:

1. **Emitir (registrar).** El agregado anota el evento en una lista interna cuando cambia de estado, como `eventos += EnvioReprogramado(...)` en el código de arriba. No lo publica: el agregado no sabe de Kafka.
2. **Despachar.** Después de guardar, la capa de aplicación o el repositorio extrae los eventos y los entrega. Si el despacho es en el mismo proceso (actualizar una caché, recalcular algo local), puede hacerse tras el commit. Si tiene que salir del servicio, se escribe en la tabla outbox **dentro de la misma transacción** que el agregado, y un relay lo publica.

El orden equivocado es el clásico: publicar antes del commit (el evento sale aunque la transacción falle) o después sin outbox (el proceso se cae entre ambos pasos y el evento se pierde). El patrón outbox está explicado en [Sistemas distribuidos](#t/sistemas-distribuidos), y su relación con proyecciones y event sourcing, en [CQRS y Event Sourcing](#t/cqrs-event-sourcing).

**Ejemplo:** `ReprogramarEntrega` guarda el envío y, en la misma transacción, inserta `EnvioReprogramado` en la outbox. El relay lo publica en Kafka en menos de un segundo; Notificaciones avisa al destinatario y el modelo de ETA descarta la estimación anterior.

**Por qué importa:** los eventos son la forma de mantener consistencia entre agregados sin agrandarlos. Si se pierden, la consistencia eventual se convierte en inconsistencia permanente.

### Fábricas en el dominio

Crear un agregado válido a veces requiere más que un constructor: decidir cuántos envíos genera un pedido, asignar IDs, calcular la ventana inicial. Esa lógica de creación es del dominio y se encapsula en una **fábrica**: un método estático en la raíz (`Envio.crear(...)`) o una clase propia cuando involucra varias piezas (ver [Patrones creacionales](#t/patrones-creacionales)).

**Ejemplo:** un pedido de un comercio tiene cuatro bultos de 14, 10, 9 y 8 kg (41 kg). Como un envío en moto admite hasta 30 kg, la fábrica `DivisorDePedido` produce dos envíos: uno con 14 + 10 = 24 kg y otro con 9 + 8 = 17 kg, ambos con el mismo `PedidoId`, la misma `Direccion` y un evento `EnvioCreado` cada uno. Ningún otro código del sistema crea envíos.

**Por qué importa:** si la creación está dispersa, cada lugar que crea envíos tiene su propia versión de las reglas iniciales, y aparecen envíos que nacen inválidos.

### Modelo anémico frente a modelo rico

Un **modelo anémico** tiene entidades con solo campos, getters y setters, y toda la lógica en servicios. Se parece a un modelo de dominio, pero en realidad es una estructura de datos con un servicio de procedimientos al lado. Un **modelo rico** pone el comportamiento junto a los datos que protege.

| | Anémico | Rico |
|---|---|---|
| Dónde están las reglas | En servicios, repetidas | En la raíz y los objetos de valor |
| Estados inválidos | Posibles con un setter | Imposibles desde afuera |
| Lectura del código | Hay que buscar quién modifica cada campo | Los comandos del agregado listan lo que se puede hacer |
| Cuándo conviene | CRUD sin reglas, formularios de configuración | Subdominios con invariantes, como asignación |

El modelo anémico es un error solo cuando el subdominio tiene reglas; en un CRUD sin invariantes, un modelo rico solo agrega ceremonia.

**Ejemplo:** con `envio.setEstado("EN_REPARTO")` público, un job nocturno de limpieza pasó a reparto 300 envíos sin transportista. Con `salirAReparto()` como único camino, la regla "en reparto implica transportista" se habría verificado.

### Las herramientas del agente pasan por la raíz

Un agente con [tool calling](#t/agentes) es un cliente más del dominio, y probablemente el menos predecible. La regla de diseño es la misma que para cualquier otro cliente, pero con más motivos:

1. **Una herramienta por comando del negocio**, no una herramienta genérica de edición. `reprogramar_envio(envio_id, desde, hasta, motivo)` se traduce a `Envio.reprogramar`. `actualizar_envio(envio_id, campos)` no debería existir.
2. **La entrada del modelo construye objetos de valor.** Si el modelo propone una ventana de 6 horas, el constructor de `VentanaHoraria` falla antes de tocar el agregado.
3. **El error del dominio vuelve al modelo como texto útil.** "El envío ya se reprogramó 2 veces" le permite explicar la situación al destinatario en lugar de reintentar.
4. **El agente actúa con la identidad del usuario** que lo invoca, y la autorización se verifica en el caso de uso, no en el prompt (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

**Ejemplo:** una inyección de prompt en un mensaje de un destinatario pide "cambiar el estado a entregado". No existe una herramienta que haga eso: la única forma de llegar a `ENTREGADO` es `registrarEntrega`, que exige prueba de entrega del transportista. El ataque no tiene por dónde entrar.

**Por qué importa:** el agregado convierte las reglas del negocio en un límite técnico. Un prompt se puede convencer; un método que no existe, no.

## Casos prácticos

### La ruta del día que no escalaba

**Situación:** el agregado `RutaDelDia` contenía todos los envíos de una zona. En hora pico, el 25 % de las escrituras fallaban por conflicto de versión, los reintentos alargaban la latencia de la app del transportista a varios segundos y la base mostraba picos de CPU por cargar miles de filas en cada operación.

**Qué se hace:** se identifica qué invariantes necesitan consistencia inmediata: las del envío (peso, estado, reprogramaciones) sí; el balance de la ruta, no. `Envio` pasa a ser el agregado, y `Ruta` queda como un agregado chico con la lista de `EnvioId` y el tope de 40 envíos. El rebalanceo se hace con un proceso que reacciona a `EnvioAsignado`. Los conflictos bajan a casos aislados.

### La herramienta genérica del agente de operaciones

**Situación:** para avanzar rápido, el agente de operaciones tenía una herramienta `actualizar_envio` que recibía un JSON de campos y hacía un `UPDATE`. En una investigación de alertas, el modelo "corrigió" la ventana de 50 envíos para que dejaran de figurar como atrasados, saltando el límite de reprogramaciones y sin avisar a los destinatarios.

**Qué se hace:** se elimina la herramienta genérica. Se exponen tres herramientas que llaman a casos de uso existentes (`reprogramar_envio`, `reasignar_envio`, `marcar_incidencia`), con el operador humano como actor y aprobación previa para operaciones masivas. Las reglas del agregado se aplican igual que en el panel, y cada cambio emite su evento, con lo que el destinatario recibe el aviso.

### Bultos con unidades mezcladas

**Situación:** pesos en gramos desde la app, en kilos desde el panel y en libras desde la integración de un comercio grande. Cada servicio convertía por su cuenta y aparecían envíos rechazados por exceso de peso que pesaban 3 kg.

**Qué se hace:** se introduce el objeto de valor `Peso` en gramos enteros, con fábricas explícitas por unidad, y el agregado solo acepta `Peso`. Los adaptadores de entrada convierten una vez, en el borde. Los tests de la fábrica cubren las tres unidades y los casos límite (0 g, 30.000 g, 30.001 g).

### Eventos que salían antes de tiempo

**Situación:** el caso de uso publicaba `EnvioAsignado` en Kafka y después hacía el commit. Ante un error de base, el destinatario recibía "tu envío está en camino" para un envío que seguía pendiente.

**Qué se hace:** el agregado solo registra los eventos; el caso de uso los escribe en la outbox en la misma transacción que el agregado, y un relay los publica. Los consumidores deduplican por ID de evento. Los avisos erróneos desaparecen y, de paso, los eventos quedan disponibles para las proyecciones de CQRS.

## Errores comunes

- **Setters públicos en la raíz.** Cualquier código puede romper una invariante. Exponer comandos con nombre del negocio y mantener el estado privado.
- **Agregados dimensionados por intuición.** Incluir todo "por consistencia" genera contención. Preguntar qué invariante necesita consistencia inmediata y calcular la tasa de escrituras.
- **Referencias de objeto entre agregados.** Arrastran grafos enormes y transacciones que cambian dos agregados sin querer. Referenciar por ID y coordinar con eventos.
- **Objetos de valor mutables o sin validación.** Un `Direccion` con setters o sin chequeos es un primitivo con otro nombre. Validar en el constructor y no permitir cambios.
- **Reglas en el caso de uso.** El servicio de aplicación orquesta; si contiene `if` sobre el estado del dominio, esa lógica debe moverse al agregado o a un servicio de dominio.
- **Herramientas de agente que editan estado directo.** Un `UPDATE` genérico expuesto a un modelo anula todo el diseño. Cada herramienta llama a un comando de la raíz a través de un caso de uso.

## Para discutir en equipo

- ¿Qué agregado nuestro tiene hoy más conflictos de versión, y qué invariante justifica realmente su tamaño?
- ¿Dónde usamos primitivos (`String`, `Double`) para conceptos que merecen un objeto de valor con validación?
- ¿Cuáles de nuestros modelos son anémicos con reglas importantes dispersas en servicios?
- ¿Qué herramientas de agente tocan estado sin pasar por un comando del dominio, y cómo las reemplazamos?
- ¿Qué invariantes entre agregados resolvemos con consistencia eventual, y qué pasa si el evento que las coordina se demora una hora?
