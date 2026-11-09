---
slug: kotlin
titulo: Kotlin en el backend
resumen: Lenguaje moderno sobre la JVM para servicios backend; cubre null safety, sealed classes, corrutinas, Flow, frameworks y realidades del runtime en contenedores.
lectura: 14
---

## La idea central

Kotlin es un lenguaje creado por JetBrains que compila a bytecode de la JVM, la misma máquina virtual que ejecuta Java. Puede usar cualquier librería Java sin adaptadores, corre sobre un runtime con más de veinticinco años de optimizaciones y herramientas de diagnóstico, y corrige varios de los problemas históricos de Java: el `null` que explota en producción, la verbosidad de las clases de datos y la complejidad de la concurrencia con hilos.

Frente a Go y Python, ofrece más expresividad a cambio de un runtime más pesado. En Rumbo no hay hoy servicios en Kotlin; este tema sirve para evaluar cuándo tendría sentido, por ejemplo para el servicio de integraciones con comercios grandes, que dependen de librerías y protocolos que solo existen en el mundo Java, o si se incorpora un equipo con experiencia en la JVM.

## Conceptos

### Por qué Kotlin sobre la JVM

Tres razones sostienen la elección:

- **Interoperabilidad con Java.** Kotlin llama a clases Java y Java llama a clases Kotlin. Todo el ecosistema (clientes de Kafka, drivers de bases de datos, librerías de integración empresarial, SDKs de proveedores) queda disponible desde el primer día.
- **Herramientas maduras de la JVM.** Profilers, volcados de heap, Java Flight Recorder para registrar eventos en producción con bajo costo, métricas del recolector de basura.
- **Un lenguaje más seguro y conciso que Java.** Null safety en el sistema de tipos, clases de datos en una línea, inmutabilidad como opción por defecto y corrutinas para concurrencia.

**Ejemplo:** si un comercio grande entrega solo una librería Java para leer sus pedidos, un servicio en Kotlin la usa tal cual; en Go habría que reescribirla.

**Por qué importa:** el lenguaje se elige por el ecosistema que habilita, no solo por su sintaxis.

### Null safety

En Kotlin, un tipo no admite `null` salvo que lo diga explícitamente con `?`. `String` nunca es nulo; `String?` puede serlo, y el compilador obliga a manejar ese caso antes de usarlo.

El operador `!!` le dice al compilador "confía en mí, no es nulo" y lanza una excepción si se equivoca. Cada `!!` es un `NullPointerException` potencial; en código de producción se reemplaza por `?:` con un valor por defecto, un `return` temprano o un error explícito.

Los valores que vienen de Java llegan como "tipos de plataforma", sin verificar; conviene tratarlos como nulables.

**Ejemplo:** el teléfono del destinatario es opcional en Rumbo; declararlo `String?` obliga a decidir qué mostrar cuando falta.

```kotlin
data class Destinatario(val nombre: String, val telefono: String?)

fun contacto(d: Destinatario): String {
    val largo = d.telefono?.length          // ?. devuelve null si telefono es null
    val tel = d.telefono ?: "sin teléfono"  // ?: (Elvis) da un valor por defecto
    return "${d.nombre} ($tel, $largo dígitos)"
}
```

**Por qué importa:** el error más frecuente en servicios Java es el `NullPointerException`. Kotlin lo convierte en un error de compilación en casi todo el código propio.

### Data classes e inmutabilidad

Una **data class** genera automáticamente `equals`, `hashCode`, `toString` y `copy`. Con `val` (en lugar de `var`) los campos no se pueden reasignar, y las colecciones por defecto (`List`, `Map`) son de solo lectura.

**Ejemplo:** recalcular el ETA de un pedido de 14 a 22 minutos crea un objeto nuevo y deja el original intacto para auditoría.

```kotlin
data class Pedido(val id: String, val zona: String, val etaMin: Int)

val p = Pedido("p-981", "norte", 14)
val demorado = p.copy(etaMin = 22)   // nuevo objeto; p no cambia
```

**Por qué importa:** objetos inmutables se comparten entre corrutinas sin locks y sin carreras, y un `copy` deja claro qué cambió.

### Sealed classes para estados y resultados

Una **sealed class** (o sealed interface) declara un conjunto cerrado de variantes, todas conocidas por el compilador. Combinada con `when`, el compilador verifica que se manejen todas: si se agrega una variante, cada `when` que no la contemple deja de compilar. Es el equivalente de las uniones discriminadas de [TypeScript](#t/typescript).

**Ejemplo:** asignar un pedido termina en uno de tres resultados conocidos, y el mensaje para el comercio debe cubrir los tres.

```kotlin
sealed interface ResultadoAsignacion {
    data class Asignado(val transportistaId: String, val etaMin: Int) : ResultadoAsignacion
    data class SinCandidatos(val radioKm: Double) : ResultadoAsignacion
    data class Rechazado(val motivo: String) : ResultadoAsignacion
}

fun mensaje(r: ResultadoAsignacion): String = when (r) {
    is ResultadoAsignacion.Asignado      -> "Asignado a ${r.transportistaId}, ETA ${r.etaMin} min"
    is ResultadoAsignacion.SinCandidatos -> "Sin transportistas en ${r.radioKm} km"
    is ResultadoAsignacion.Rechazado     -> "Rechazado: ${r.motivo}"
}
```

**Por qué importa:** modelar resultados así, en lugar de lanzar excepciones para casos esperables, hace que los errores de negocio sean parte del tipo y no una sorpresa.

### Extension functions

Una **extension function** agrega una función a un tipo existente sin modificarlo ni heredar de él. Después se usa como si fuera un método. Son útiles para adaptar tipos de librerías Java a un vocabulario del dominio.

**Ejemplo:** `fun Pedido.esUrgente() = etaMin > 60` permite escribir `pedido.esUrgente()`; con una clase de una librería Java de un comercio, `mensaje.aPedido()` traduce su formato al de Rumbo.

**Por qué importa:** acercan el código al lenguaje del dominio, pero si se abusa de ellas la lógica queda dispersa en muchos archivos.

### Corrutinas y concurrencia estructurada

Una **corrutina** es una tarea que puede suspenderse mientras espera (la red, la base, un LLM) sin bloquear un hilo. Una función marcada con `suspend` puede pausar en esos puntos y reanudarse después, posiblemente en otro hilo. Miles de corrutinas comparten unos pocos hilos.

- **`launch`** inicia una corrutina que no devuelve resultado.
- **`async`** inicia una que devuelve un resultado; se obtiene con `await()`.
- **`coroutineScope`** agrupa corrutinas hijas y no termina hasta que terminan todas.

La idea clave es la **concurrencia estructurada**: cada corrutina vive dentro de un scope. Si una hija falla, el scope cancela a sus hermanas; si se cancela el scope, se cancelan todas las hijas. No quedan tareas huérfanas.

La **cancelación es cooperativa**: una corrutina se entera de que fue cancelada en los puntos de suspensión. Un bucle de cálculo largo sin suspensiones no se detiene hasta que termina, salvo que consulte `isActive` o llame a `ensureActive()`.

**Flow** es un flujo asíncrono de valores: una secuencia que se produce de a poco (`emit`) y se consume con `collect`. Es "frío": no hace nada hasta que alguien lo consume, y si el consumidor se cancela, el productor también.

**Ejemplo:** leer features y candidatos en paralelo. En serie tardan 28 + 8 = 36 ms; en paralelo, el máximo, 28 ms.

```kotlin
suspend fun prepararAsignacion(pedido: Pedido): Preparacion = coroutineScope {
    val features   = async { featureStore.leer(pedido) }
    val candidatos = async { repo.candidatosCercanos(pedido.ubicacion) }
    Preparacion(features.await(), candidatos.await())
}   // si una falla, la otra se cancela y el error se propaga
```

**Por qué importa:** la concurrencia estructurada evita, por diseño, las tareas colgadas que en otros lenguajes se detectan recién en producción.

### Comparación con goroutines y virtual threads

| Aspecto | Go goroutines | Java virtual threads | Kotlin corrutinas |
|---|---|---|---|
| Modelo | Hilos livianos del runtime | Hilos livianos de la JVM | Funciones suspendibles de una librería |
| Código | Bloqueante normal | Bloqueante normal | Marcado con `suspend` |
| Cancelación | Manual con `context.Context` | Interrupción del hilo | Estructurada, propagada por el scope |
| Ciclo de vida | Libre; fácil dejar goroutines colgadas | Libre, con APIs estructuradas en evolución | Atado a un scope por diseño |

Desde Java 21 los **virtual threads** permiten escribir código bloqueante que escala como si fuera asíncrono. Reducen una de las ventajas de las corrutinas, pero no la concurrencia estructurada ni Flow, que siguen siendo el punto fuerte de Kotlin. Para comparar con Go, ver [Go](#t/go).

**Ejemplo:** cien llamadas concurrentes al LLM ocupan unos pocos hilos en los tres modelos; la diferencia está en que, en Kotlin, cancelar la petición cancela las cien sin código extra.

**Por qué importa:** los tres resuelven la escala; lo que cambia es cuánto cuesta no dejar trabajo huérfano.

### Frameworks

- **Spring Boot con Kotlin.** El framework más usado de la JVM, con soporte oficial para Kotlin: controladores con funciones `suspend` y respuestas como `Flow` en el stack reactivo. Trae de todo (inyección de dependencias, seguridad, acceso a datos, métricas) a cambio de arranque más lento y más "magia" por convención.
- **Ktor.** Framework de JetBrains, escrito en Kotlin y basado en corrutinas desde el origen. Más liviano y explícito: se arma lo que se necesita. Arranca más rápido, pero hay que elegir y conectar más piezas a mano.

**Ejemplo:** el servicio de integraciones, con base de datos, seguridad y varios conectores, encaja en Spring Boot; un servidor MCP de solo lectura para el agente de operaciones, en Ktor.

**Por qué importa:** el framework define el arranque, la memoria y cuánta configuración implícita hay que entender al depurar.

### Realidades del runtime de la JVM

- **Arranque.** Un servicio Spring Boot típico tarda varios segundos en arrancar; uno en Ktor, alrededor de un segundo (órdenes de magnitud); Go, en milisegundos. Afecta al autoescalado rápido.
- **Calentamiento del JIT.** La JVM empieza interpretando y compila a código nativo las partes más usadas mientras corre. Las primeras miles de peticiones pueden ser varias veces más lentas que en régimen.
- **Memoria.** La JVM detecta los límites del contenedor, pero por defecto usa como heap máximo solo una fracción de la memoria disponible (del orden del 25%). En un pod de 2 GiB, eso deja unos 512 MiB de heap. Se ajusta con `-XX:MaxRAMPercentage` (por ejemplo, 70–75%), dejando espacio para la memoria fuera del heap: hilos, metaspace, buffers.
- **Recolector de basura.** G1 es el predeterminado y equilibra rendimiento y pausas; ZGC apunta a pausas de pocos milisegundos con heaps grandes, a cambio de más CPU.
- **GraalVM native image.** Compila la aplicación por adelantado a un binario nativo: arranque en decenas de milisegundos y menos memoria, a cambio de builds lentos, configuración extra para reflexión y, en algunos casos, menor rendimiento sostenido. El soporte en Spring Boot y Ktor mejora con cada versión; verificar en la documentación vigente antes de adoptarlo.

**Ejemplo:** en un pod de 1 GiB, un heap al 70% deja unos 700 MiB para objetos y 300 MiB para el resto del proceso.

**Por qué importa:** la mayoría de los problemas de la JVM en Kubernetes vienen de no configurar estos valores. Ver [Contenedores, ECS y EKS](#t/contenedores) para requests y limits.

### Testing

Se usa JUnit 5 o Kotest como framework, MockK para dobles de prueba (entiende funciones `suspend` y clases finales, que en Kotlin son la norma) y Testcontainers para levantar PostgreSQL o Kafka reales en los tests de integración. La librería de pruebas de corrutinas ofrece `runTest`, que usa **tiempo virtual**: los `delay` se ejecutan al instante.

**Ejemplo:** un test verifica que, si el LLM tarda más de 45 segundos, la respuesta se corta con el timeout; con tiempo virtual corre en milisegundos.

**Por qué importa:** los timeouts y reintentos son lo que más falla en producción y lo que menos se prueba si los tests son lentos.

### Kotlin y agentes

**Llamadas a LLMs con corrutinas.** Una llamada a un LLM es E/S pura: segundos de espera sin cálculo. Con corrutinas, un servicio atiende cientos de conversaciones simultáneas con pocos hilos, igual que asyncio en Python.

**Streaming con Flow.** Los tokens que llegan del proveedor se exponen como un `Flow<String>` y se reenvían al cliente con Server-Sent Events.

**Timeouts y cancelación cuando el cliente se va.** Si el usuario cierra el chat, el framework cancela la corrutina de la petición, la cancelación llega al `collect`, y el Flow cancela la conexión HTTP con el proveedor. Se dejan de generar tokens que nadie lee. El comportamiento exacto depende del framework y del motor HTTP; conviene probarlo.

**Resultados de herramientas con sealed classes.** El resultado de una herramienta de un agente se modela como `Exito`, `ErrorReintentable`, `ErrorDefinitivo` o `RequiereAprobacion`. El bucle del agente hace un `when` exhaustivo y decide si reintenta, informa al modelo o escala a un humano. Ver [Patrones de resiliencia](#t/resiliencia).

**SDKs para la JVM.** Los proveedores principales de LLMs ofrecen SDKs para Java, usables desde Kotlin, y hay frameworks de la JVM para agentes y servidores MCP. Cambian rápido: verificar en la documentación vigente qué soporta cada uno (streaming, tool calling, salidas estructuradas).

**Ejemplo:** el chat interno responde en streaming con un tope de 45 segundos y cuenta las respuestas canceladas.

```kotlin
fun responder(pregunta: String): Flow<String> = flow {
    withTimeout(45_000) {                      // tope total de la respuesta
        clienteLlm.streamCompletion(pregunta).collect { token -> emit(token) }
    }
}.onCompletion { causa ->
    if (causa is CancellationException) metricas.respuestasCanceladas.inc()
}
```

**Por qué importa:** en un agente, el costo y la latencia dependen de cortar a tiempo; la cancelación estructurada lo hace con poco código.

### Dónde encajaría en Rumbo

| Criterio | Go | Python | Kotlin |
|---|---|---|---|
| Latencia estable bajo carga | Excelente | Limitada por el GIL | Muy buena tras el calentamiento |
| Arranque y tamaño de imagen | Milisegundos, 15–30 MB | Segundos, cientos de MB con ML | Segundos, 200–400 MB con JVM |
| Ecosistema de ML y LLMs | Básico | El más completo | Bueno vía SDKs Java |
| Integraciones empresariales | Medio | Medio | El más completo |
| Modelado de dominio complejo | Simple, explícito | Flexible, menos verificado | Muy expresivo y verificado |

La conclusión razonable: Go sigue siendo la opción para asignación; Python, para modelos y el asistente. Kotlin tendría sentido en servicios con dominio complejo e integraciones con sistemas Java de comercios grandes, o en clientes on-prem que ya operan la JVM.

**Ejemplo:** un cliente on-prem que solo admite servicios en la JVM podría recibir el módulo de integraciones en Kotlin sin sumar otro runtime a su operación.

**Por qué importa:** cada lenguaje nuevo suma costo de operación y de conocimiento; tiene que justificarse con un caso concreto.

## Casos prácticos

### Integración con comercios que solo ofrecen librerías Java

**Situación:** tres comercios grandes envían pedidos por protocolos de intercambio empresarial cuyas librerías de referencia solo existen para Java. Reescribirlas en Go llevaría meses.

**Qué se hace:** se crea un servicio de integraciones en Kotlin con Spring Boot que usa esas librerías directamente, traduce los mensajes a eventos de Kafka (`pedido creado`) y modela cada resultado de parseo con una sealed class (`Valido`, `Incompleto`, `Rechazado`). El resto de Rumbo no cambia: solo ve eventos.

### Pods eliminados por memoria

**Situación:** el servicio de integraciones corre en pods de 1 GiB. Con `-XX:MaxRAMPercentage=90` el heap puede crecer hasta 900 MiB, y el proceso es eliminado por exceder la memoria del contenedor durante picos.

**Qué se hace:** se baja a 70% (unos 700 MiB de heap), dejando unos 300 MiB para metaspace, hilos y buffers, y se monitorean heap y memoria total del proceso por separado. Las eliminaciones desaparecen y las pausas del GC no cambian de forma visible.

### Tokens generados para nadie

**Situación:** un prototipo de chat interno en Kotlin hacía la llamada de streaming al LLM en un scope global (`GlobalScope.launch`). Cuando el usuario cerraba la pestaña, la generación seguía hasta el final. El 18% de los tokens de salida eran de respuestas que nadie leyó.

**Qué se hace:** se elimina el scope global y la llamada pasa a vivir dentro del scope de la petición, devolviendo un `Flow`. La desconexión cancela el `collect`, que cancela la llamada al proveedor. Se agrega la métrica de respuestas canceladas y una prueba que corta la conexión a mitad del streaming.

### Lentitud después de cada deploy

**Situación:** tras cada deploy, el p99 del servicio sube de 40 ms a 300 ms durante unos dos minutos y dispara alertas.

**Qué se hace:** es el calentamiento del JIT. Se agrega una fase de calentamiento con peticiones sintéticas antes de que la readiness probe declare listo el pod, y el rollout pasa a ser gradual. Se evalúa native image para este servicio, pero se descarta por ahora: los builds tardan mucho y el servicio no escala con frecuencia.

## Errores comunes

- **Usar `!!` para callar al compilador.** Reintroduce el `NullPointerException`; manejar el nulo con `?:`, un retorno temprano o un error explícito.
- **Lanzar corrutinas en `GlobalScope`.** Quedan fuera de la concurrencia estructurada y no se cancelan; usar el scope de la petición o uno con ciclo de vida propio.
- **Llamadas bloqueantes dentro de corrutinas.** Un driver JDBC o un `Thread.sleep` bloquean el hilo compartido; usar `withContext(Dispatchers.IO)` o clientes asíncronos.
- **Capturar `CancellationException` y seguir.** Rompe la cancelación; si se captura, se vuelve a lanzar.
- **Dimensionar el pod sin configurar el heap.** Con los valores por defecto se desperdicia memoria o se excede el límite; ajustar `MaxRAMPercentage` y medir.
- **Medir rendimiento sin calentamiento.** Los primeros minutos de la JVM no representan el régimen; descartar el calentamiento en benchmarks y pruebas de carga.

## Para discutir en equipo

- ¿Qué tipo de servicio justificaría sumar la JVM como tercer runtime en Rumbo, con su costo de operación y de conocimiento?
- ¿Cómo verificamos, en cualquier lenguaje, que una desconexión del cliente cancela la llamada al LLM?
- ¿Preferimos modelar los resultados de herramientas como tipos cerrados (sealed classes, uniones discriminadas) en todos los lenguajes del equipo?
- ¿Qué peso le damos al arranque lento y al calentamiento en servicios que autoescalan con picos de demanda?
