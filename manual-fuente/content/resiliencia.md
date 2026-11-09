---
slug: resiliencia
titulo: Patrones de resiliencia
resumen: Los patrones que impiden que una falla parcial se propague: idempotencia, timeouts, reintentos con jitter, circuit breakers, bulkheads, fallbacks y pruebas de caos.
lectura: 14
---

## La idea central

En un sistema con decenas de servicios, siempre hay algo fallando o lento. La resiliencia no consiste en evitar las fallas, sino en **contenerlas**: que un proveedor de mapas lento afecte solo a lo que depende de él, que un reintento no duplique una asignación y que un servicio caído no arrastre a los que lo llaman. La mayoría de los grandes incidentes no son la falla inicial, sino su amplificación: reintentos que multiplican la carga, hilos bloqueados esperando sin límite, colas que crecen hasta agotar la memoria.

Los patrones de este tema son piezas que se combinan. Un timeout sin idempotencia lleva a duplicados; reintentos sin backoff ni presupuesto llevan a tormentas; un circuit breaker sin fallback solo cambia un error lento por uno rápido. Conviene pensarlos juntos, por cada dependencia, con una pregunta guía: ¿qué hacemos cuando esto está lento, cuando está caído y cuando no sabemos qué pasó?

## Conceptos

### Idempotencia con clave de idempotencia

Una operación es idempotente si ejecutarla varias veces tiene el mismo efecto que ejecutarla una. "Marcar el pedido 123 como entregado" lo es; "sumar 1 a los pedidos activos del transportista" no. Cuando una operación no es naturalmente idempotente, se la vuelve idempotente con una **clave de idempotencia**: un identificador único que el **cliente** genera por intención (no por intento) y reenvía igual en cada reintento.

Implementación en el servidor, paso a paso:

1. Recibe la solicitud con la clave `K` y calcula un hash del cuerpo.
2. Intenta insertar `(K, hash, estado='en_proceso')` en una tabla con `K` como clave primaria.
3. Si la inserción tiene éxito, procesa la operación y guarda la respuesta junto a `K`, idealmente en la misma transacción que el efecto de negocio.
4. Si `K` ya existe y está completa, devuelve la respuesta guardada sin volver a procesar.
5. Si `K` existe y sigue en proceso, responde "en curso" (409 o reintentable) para que el cliente espere.
6. Si `K` existe con un hash distinto, es un error del cliente (misma clave, otra operación): se rechaza.
7. Las claves se guardan por un período que cubra todos los reintentos posibles, por ejemplo 24 horas.

**Ejemplo:** el servicio de asignación usa como clave `asig:{pedido_id}:{ronda}`. Si reintenta la ronda 1 tres veces, solo la primera escribe; las otras reciben la misma respuesta.

### Timeouts

Toda llamada por red necesita un timeout. Sin él, un servidor que dejó de responder retiene hilos, conexiones y memoria del cliente hasta agotarlos. Hay dos niveles:

- **Por intento:** cuánto se espera cada llamada individual.
- **Total (deadline):** cuánto se puede gastar en la operación completa, contando reintentos.

La regla clave: **el timeout de una dependencia debe ser menor que el del llamador**, descontando lo ya consumido. Si la API pública espera 2 segundos a la asignación y la asignación espera 5 segundos al proveedor de mapas, la API devuelve error a los 2 segundos mientras la asignación sigue trabajando 3 segundos más para nadie. Por eso se propagan **deadlines** a lo largo de la cadena (ver [gRPC y REST](#t/grpc-rest)).

Para elegir el valor se parte del p99 o p99,9 de la dependencia en condiciones normales, con algo de margen, y se verifica que entre en el presupuesto del llamador. Un timeout de "30 segundos por las dudas" es casi lo mismo que no tener ninguno.

### Reintentos con backoff exponencial y jitter

Reintentar tiene sentido ante errores transitorios (timeout, 503, conexión rechazada) y **solo** si la operación es idempotente. No se reintentan errores de validación ni de permisos.

El **backoff exponencial** espera cada vez más entre intentos (100 ms, 200 ms, 400 ms) para darle tiempo a la dependencia de recuperarse. El **jitter** agrega aleatoriedad a esa espera. Sin jitter, mil clientes que fallaron al mismo tiempo reintentan al mismo tiempo, en oleadas sincronizadas que vuelven a tumbar al servidor. Con *full jitter*, cada cliente espera un tiempo aleatorio entre 0 y el tope del backoff, y la carga se reparte.

```go
func conReintentos(ctx context.Context, op func(context.Context) error) error {
    const (
        base       = 50 * time.Millisecond
        tope       = 1 * time.Second
        maxIntentos = 4
    )
    var err error
    for intento := 0; intento < maxIntentos; intento++ {
        intentoCtx, cancel := context.WithTimeout(ctx, 300*time.Millisecond) // timeout por intento
        err = op(intentoCtx)
        cancel()
        if err == nil || !esReintentable(err) {
            return err
        }
        if !presupuestoReintentos.Permitir() { // ver presupuesto de reintentos
            return err
        }
        espera := min(tope, base<<intento)                     // 50, 100, 200, 400 ms
        espera = time.Duration(rand.Int63n(int64(espera)))     // full jitter
        select {
        case <-time.After(espera):
        case <-ctx.Done(): // deadline total del llamador
            return ctx.Err()
        }
    }
    return err
}
```

### Presupuesto de reintentos

Los reintentos multiplican la carga justo cuando la dependencia está peor. Si cada capa de una cadena de tres servicios reintenta 3 veces, una sola solicitud original puede convertirse en 3 × 3 × 3 = 27 llamadas a la última dependencia. Ese es el mecanismo detrás de muchas caídas en cascada.

Dos defensas. Primero, **reintentar en una sola capa**, normalmente la más cercana a la falla o la más cercana al usuario, no en todas. Segundo, un **presupuesto de reintentos**: los reintentos no pueden superar un porcentaje de las solicitudes originales, por ejemplo 10% en una ventana de 10 segundos. Cuando la dependencia falla de forma masiva, el presupuesto se agota y el cliente deja de amplificar la carga.

### Circuit breaker

Un circuit breaker envuelve las llamadas a una dependencia y deja de llamarla cuando falla demasiado, para no desperdiciar recursos ni empeorar su situación. Tiene tres estados:

```text
              tasa de error > 50% en 20 s
              (con al menos 50 llamadas)
   +---------+ -------------------------> +---------+
   | CERRADO |                            | ABIERTO |  falla de inmediato,
   | llama   | <---+                      |         |  sin llamar; va al fallback
   +---------+     |                      +---------+
                   |                         |    ^
       N pruebas   |        pasan 30 s       |    | alguna prueba falla
       exitosas    |                         v    |
                   |                    +------------+
                   +------------------- | SEMIABIERTO|  deja pasar pocas
                                        |            |  llamadas de prueba
                                        +------------+
```

- **Cerrado:** las llamadas pasan normalmente y se cuentan los errores.
- **Abierto:** las llamadas fallan de inmediato sin tocar la dependencia. Esto libera recursos del llamador y le da respiro a la dependencia.
- **Semiabierto:** tras un tiempo, se dejan pasar unas pocas llamadas de prueba. Si funcionan, se vuelve a cerrado; si fallan, a abierto.

Hay que exigir un mínimo de llamadas antes de abrir (para que 2 errores de 3 llamadas no lo disparen) y contar los timeouts como errores. Lo valioso es combinarlo con un fallback: abrir el circuito solo cambia un error lento por uno rápido.

### Bulkhead

Un bulkhead (mamparo, como los compartimentos estancos de un barco) aísla los recursos de cada dependencia para que la falla de una no agote los de todas. Se implementa con pools de conexiones o límites de concurrencia separados por dependencia.

**Ejemplo:** el servicio de seguimiento llama al proveedor de mapas y a la base. Si comparten un pool de 100 goroutines o hilos y los mapas se ponen lentos, las 100 quedan esperando a los mapas y ni siquiera se pueden servir consultas que solo necesitan la base. Con un límite de 30 llamadas concurrentes a mapas, las otras 70 siguen disponibles.

### Fallback

El fallback es lo que se hace cuando la llamada principal falla: un valor por defecto, un dato cacheado, un proveedor alternativo, una regla simple o una respuesta parcial. Tiene que ser **más simple y más confiable** que lo que reemplaza; un fallback que depende de lo mismo que falló no sirve. También tiene que probarse: un camino de código que se ejecuta una vez por trimestre suele estar roto cuando se necesita.

### Rate limiting

El rate limiting limita cuántas solicitudes acepta un servicio por cliente y por unidad de tiempo, típicamente con un *token bucket* (un balde que se rellena a ritmo constante; cada solicitud consume un token). Protege de un cliente que, por bug o por abuso, envía mucho más de lo esperado, y garantiza un reparto justo entre clientes. En la API pública de Rumbo, cada comercio tiene un límite según su plan y recibe un 429 con el header `Retry-After` al excederlo.

### Dead letter queue

Una dead letter queue (DLQ) recibe los mensajes que un consumidor no pudo procesar después de varios intentos. Sin ella, un mensaje malformado (un "mensaje veneno") bloquea una partición entera, porque el consumidor lo reintenta para siempre y no avanza. Con DLQ, se aparta, se sigue procesando y se alerta. La DLQ necesita un dueño, una alerta y una herramienta para reprocesar sus mensajes una vez corregido el bug; si no, es un lugar donde los datos van a morir en silencio.

### Fail-open y fail-closed

Cuando falla un control, hay que decidir qué pasa por defecto. **Fail-closed** bloquea la operación (más seguro); **fail-open** la deja pasar (más disponible). La elección depende del costo de cada error: un control de autenticación siempre falla cerrado; una verificación que mejora la calidad pero no protege nada crítico puede fallar abierto, idealmente con límites (por tiempo, por volumen o por tipo de cliente) y con registro para revisar después.

### Chaos engineering

El chaos engineering consiste en inyectar fallas de forma controlada para verificar que los patrones anteriores funcionan: agregar 200 ms de latencia al modelo de ETA, matar pods, cortar el acceso a una AZ. Se arranca con una hipótesis ("si el modelo tarda 200 ms, la asignación usa la regla de respaldo y su p99 se mantiene bajo 50 ms"), un radio de impacto acotado (un entorno de staging o el 1% del tráfico) y un mecanismo para abortar. Muchas veces el hallazgo es que el fallback tenía un bug o que una alerta no se dispara.

### Resumen de patrones

| Patrón | Problema que evita | Ejemplo en Rumbo |
|---|---|---|
| Clave de idempotencia | Efectos duplicados al reintentar | Un reintento de asignación no notifica a un segundo transportista |
| Timeout | Recursos retenidos por dependencias colgadas | 30 ms al modelo de ETA |
| Reintento con backoff y jitter | Fallas transitorias y reintentos sincronizados | Lectura de features ante un error de conexión |
| Presupuesto de reintentos | Amplificación de carga en cascada | Máximo 10% de reintentos hacia el proveedor de mapas |
| Circuit breaker | Seguir llamando a algo que está caído | Corte del proveedor de mapas principal |
| Bulkhead | Que una dependencia lenta agote todos los recursos | Pool separado para mapas en seguimiento |
| Fallback | Fallar entero por una dependencia no crítica | Regla del más cercano si el modelo no responde |
| Rate limiting | Un cliente que satura a todos | Límite por comercio en la API pública |
| Dead letter queue | Un mensaje veneno que bloquea una partición | Eventos con esquema inválido en notificaciones |
| Fail-open con límites | Bloquear la operación por un control no crítico | Verificación de direcciones caída |

## Casos prácticos

### Timeout ambiguo al notificar a un transportista

**Situación:** la asignación llama a `NotificarAsignacion(p-123, t-7)` y la llamada vence a los 500 ms. No se sabe si el transportista recibió la oferta. Si se asume que falló y se ofrece el pedido a `t-9`, puede que ambos lo acepten.

**Qué se hace:** un timeout es "no sé", no "falló". Primero se **consulta el estado** de la oferta (`GET oferta?pedido=p-123`) antes de decidir. Si existe, se espera su resultado. Si no existe, se reintenta con la **misma clave de idempotencia** (`oferta:p-123:1`), de modo que si la primera sí se había procesado, el reintento no crea una segunda. Solo cuando la oferta vence o es rechazada se pasa a `t-9`, con una nueva clave. Como red de seguridad, la base tiene una restricción única de asignación activa por pedido (ver [Sistemas distribuidos](#t/sistemas-distribuidos)).

### Tormenta de reintentos contra un proveedor de mapas lento

**Situación:** el proveedor de mapas que calcula rutas pasa de 80 ms a 2 segundos de latencia. El servicio de seguimiento tiene timeout de 1 segundo y 3 reintentos sin jitter; la API de ETA que lo llama también reintenta 3 veces. Las llamadas al proveedor se multiplican por 9, el proveedor aplica rate limiting a Rumbo, y lo que era lentitud se convierte en caída total.

**Qué se hace:** se dejan los reintentos solo en el cliente más cercano al proveedor, con backoff exponencial, full jitter y un presupuesto del 10%. La API de ETA deja de reintentar y propaga el deadline. Se agrega caché de rutas por par de celdas geográficas con TTL de 15 minutos, que absorbe buena parte de las consultas repetidas. El resultado: ante la misma degradación, la carga extra al proveedor queda acotada a un 10% en lugar de multiplicarse por 9.

### Circuit breaker sobre el proveedor de mapas con ruteo a uno secundario

**Situación:** Rumbo contrató un segundo proveedor de mapas, con peor calidad en algunas zonas y un costo hipotético mayor por consulta. Se quiere usarlo solo cuando el principal falla.

**Qué se hace:** un circuit breaker sobre el principal: abre con más de 50% de errores o timeouts en 20 segundos, con un mínimo de 50 llamadas; queda abierto 30 segundos y pasa a semiabierto con 5 llamadas de prueba. Con el circuito abierto, las rutas van al secundario, también protegido por su propio breaker y su bulkhead. Si ambos están abiertos, se usa una estimación por distancia en línea recta multiplicada por un factor por zona. Cada respuesta registra qué proveedor la generó, para que el modelo de ETA y los análisis posteriores lo sepan. Se agrega una alerta por el estado del circuito y un ejercicio de caos trimestral que fuerza su apertura.

### Se cae el servicio de verificación de direcciones

**Situación:** al crear un pedido, la API valida la dirección del destinatario contra un servicio de verificación. El servicio se cae un viernes a la noche. Con fail-closed, ningún comercio puede crear pedidos.

**Qué se hace:** se elige **fail-open con límites**. Si la verificación no responde en 200 ms o su circuit breaker está abierto, el pedido se acepta con la marca `direccion_no_verificada` y entra en una cola de verificación diferida que se procesa cuando el servicio vuelve. Los límites: el modo fail-open dura como máximo 2 horas antes de requerir una decisión humana; los comercios nuevos (menos de 30 días) siguen en fail-closed porque concentran la mayoría de las direcciones erróneas; y la asignación prioriza la verificación diferida para esos pedidos antes de ofrecerlos a un transportista. Una alerta avisa cuando se entra en el modo fail-open, y una métrica mide cuántos pedidos pasaron sin verificar.

## Errores comunes

- **Reintentar operaciones no idempotentes.** Duplica efectos; primero se hace la operación idempotente con una clave generada por el cliente.
- **Reintentar en todas las capas.** La carga se multiplica geométricamente; se reintenta en una capa y con presupuesto.
- **Timeouts más largos que los del llamador.** Se trabaja para nadie; se propagan deadlines y se descuenta lo consumido.
- **Backoff sin jitter.** Los clientes reintentan sincronizados y generan oleadas; se usa full jitter.
- **Fallbacks que nunca se prueban o que dependen de lo mismo que falló.** Se ejercitan con pruebas de caos y se mantienen simples.
- **DLQ sin dueño ni alerta.** Los mensajes se acumulan sin que nadie lo sepa; se asigna responsable, alerta y herramienta de reprocesamiento.

## Para discutir en equipo

- Para cada dependencia del servicio de asignación, ¿qué hacemos si está lenta, si está caída y si no sabemos qué pasó?
- ¿En qué capa de nuestra cadena de llamadas deberían vivir los reintentos, y dónde hoy se duplican?
- ¿Qué controles nuestros fallan abiertos sin que lo hayamos decidido explícitamente?
- ¿Qué fallback no ejecutamos en producción desde hace meses, y cómo lo probaríamos sin riesgo?
- ¿Qué experimento de caos nos daría más información con menos riesgo como primer ejercicio?
