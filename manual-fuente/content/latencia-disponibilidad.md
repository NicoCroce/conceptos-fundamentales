---
slug: latencia-disponibilidad
titulo: Baja latencia y alta disponibilidad
resumen: Cómo definir objetivos de latencia y disponibilidad con SLOs y percentiles, repartir un presupuesto por componente y diseñar para cumplirlo cuando algo falla.
lectura: 14
---

## La idea central

"Rápido" y "disponible" son promesas que solo se pueden cumplir si se definen con números y se reparten entre las piezas del sistema. El servicio de asignación tiene ~50 ms para decidir qué transportista toma un pedido. Esos 50 ms son un presupuesto, como el de un hogar: si el modelo de ETA gasta 45, no queda nada para la base, la red ni los imprevistos. Lo mismo pasa con la disponibilidad: un objetivo de 99,9% significa que hay un margen concreto de fallas permitido por mes, y se puede "gastar" en deploys arriesgados o ahorrar.

La segunda idea es que la experiencia de los usuarios la definen los casos lentos, no el caso típico. Un promedio de 8 ms puede convivir con un 1% de solicitudes que tardan 120 ms, y si una operación hace diez llamadas, ese 1% deja de ser raro. Por eso se habla de percentiles y no de promedios.

## Conceptos

### SLI, SLO y SLA

- **SLI** (*service level indicator*): la medición. Por ejemplo, "proporción de solicitudes de asignación que responden con éxito en menos de 50 ms, medida en el balanceador".
- **SLO** (*service level objective*): el objetivo interno sobre ese indicador en una ventana. "99,9% de las solicitudes en una ventana móvil de 30 días."
- **SLA** (*service level agreement*): el compromiso contractual con un cliente, con consecuencias si se incumple. Siempre es más laxo que el SLO interno, para tener margen: si el SLA con comercios es 99,5%, el SLO interno es 99,9%.

El SLI se mide lo más cerca posible del usuario. Medirlo dentro del pod ignora los errores que ocurren antes (el balanceador devolviendo 503 porque no hay pods sanos). Y conviene que el SLI combine disponibilidad y latencia: una respuesta correcta a los 3 segundos no le sirve a un servicio que tenía 50 ms.

### Presupuesto de error

Si el SLO es 99,9%, el 0,1% restante es el **presupuesto de error**: la cantidad de fallas que se pueden tolerar sin incumplir el objetivo. Con 10 millones de solicitudes de asignación al mes, son 10.000 solicitudes fallidas o lentas.

El presupuesto convierte una discusión de opiniones ("¿somos demasiado arriesgados con los deploys?") en una de datos. Si queda presupuesto, se puede desplegar más seguido y experimentar. Si se agotó, se prioriza confiabilidad. Y si cada mes sobra casi todo, el SLO quizá es demasiado bajo o el equipo es demasiado conservador. La condición para que funcione es que la política se acuerde **antes** de necesitarla, con producto.

| SLO de disponibilidad | Caída máxima por mes (30 días) | Caída máxima por año | Qué suele implicar |
|---|---|---|---|
| 99% | ~7 h 12 min | ~3,65 días | Una sola instancia con reinicio automático |
| 99,9% | ~43 min | ~8,8 h | Varias réplicas, multi-AZ, deploys graduales |
| 99,95% | ~22 min | ~4,4 h | Lo anterior más failover automático de la base y rollbacks rápidos |
| 99,99% | ~4 min 19 s | ~53 min | Sin intervención humana en la recuperación; a menudo multi-región |

La última columna es la importante: con 4 minutos por mes, una persona que recibe una alerta, abre la laptop y entiende el problema ya consumió el presupuesto. Cada nueve adicional multiplica el costo de ingeniería y de infraestructura.

### Percentiles y por qué el promedio engaña

El percentil 99 (p99) es el valor por debajo del cual queda el 99% de las solicitudes. Si el p99 es 120 ms, una de cada cien tarda 120 ms o más. El promedio esconde esa cola, porque mezcla muchas solicitudes rápidas con pocas muy lentas.

El efecto empeora con el **fan-out**. Si una operación hace 10 llamadas en paralelo y debe esperar a todas, la operación es lenta si **cualquiera** lo es. La probabilidad de que las 10 estén por debajo del p99 es 0,99^10 ≈ 0,904. Entonces, **1 − 0,99^10 ≈ 9,6%** de las operaciones sufre al menos una llamada en la cola lenta. Con 100 llamadas, el 63%. Lo que en un servicio es "el 1% raro" se vuelve la experiencia habitual del servicio que lo llama.

Dos reglas prácticas: los percentiles no se promedian entre pods (el promedio de los p99 de diez pods no es el p99 global; se calculan desde histogramas agregados), y conviene mirar p50, p99 y p99,9 a la vez.

### Presupuesto de latencia por componente

El presupuesto total se reparte entre cada paso del camino crítico, usando el p99 de cada componente y dejando margen. Si un paso excede su parte, el problema es visible antes de que lo vean los usuarios. Los pasos que no necesitan estar en el camino crítico (publicar eventos, registrar métricas de negocio) se sacan del camino con procesamiento asíncrono.

Las herramientas para cumplirlo: paralelizar lo independiente, hacer lecturas en lote en lugar de N llamadas, poner datos en memoria y, sobre todo, ponerle a cada llamada un timeout acorde a su porción del presupuesto (ver [Patrones de resiliencia](#t/resiliencia)).

### Caché local y distribuida

- **Caché local** (en memoria del proceso): lectura en microsegundos, sin red. Cada pod tiene su copia, así que puede haber inconsistencias entre pods y el uso de memoria se multiplica por la cantidad de réplicas.
- **Caché distribuida** (Redis, Memcached): una sola copia compartida, ~0,5 a 2 ms por lectura dentro de la misma zona. Es un componente más que puede fallar o saturarse.

La parte difícil es la **invalidación**. Opciones, de más simple a más compleja: TTL (el dato vence solo; se acepta que esté desactualizado hasta ese tiempo), invalidación por evento (al cambiar el dato se publica un evento y se borra la entrada) y escritura a través de la caché. El TTL se elige según cuánto tolera el negocio un dato viejo: la zona de cobertura de un comercio puede tolerar 10 minutos; la capacidad actual de un transportista, ninguno.

Dos problemas clásicos: el **thundering herd** (vence una clave muy leída y cien solicitudes van juntas a la base; se resuelve con *request coalescing*, una sola solicitud recarga y las demás esperan) y la caché fría después de un deploy (los primeros minutos tienen latencia de base; se resuelve precargando o desplegando de a poco).

### Escalado horizontal

Escalar horizontalmente es agregar réplicas en lugar de máquinas más grandes. Requiere que el servicio sea **sin estado** (el estado vive en la base, en la caché o en el cliente) para que cualquier réplica atienda cualquier solicitud. Con autoscaling por CPU o por solicitudes por segundo, la cantidad de pods sigue a la demanda.

Los límites aparecen en lo compartido: si cada pod abre 20 conexiones a Aurora y se escala de 10 a 60 pods, se pasa de 200 a 1.200 conexiones y la base, no los pods, se convierte en el cuello de botella (ver [Bases de datos](#t/bases-de-datos)). Además el autoscaling tarda minutos en reaccionar: no protege de un pico de segundos, para eso existe el load shedding.

### Redundancia multi-AZ y multi-región

Una **zona de disponibilidad** (AZ) es un conjunto de centros de datos aislados dentro de una región, con latencia entre zonas de uno o dos milisegundos. Desplegar en tres AZ, con Aurora replicando entre ellas y failover automático, protege de la caída de una zona con costo y complejidad moderados. Es la base razonable para casi cualquier servicio con SLO de 99,9% o más.

**Multi-región** protege de la caída de una región entera, pero es otra liga: las regiones están a decenas de milisegundos, la replicación de la base es asíncrona (así que un failover puede perder segundos de escrituras) y hay que decidir qué pasa con cada dato durante la partición (ver [Sistemas distribuidos](#t/sistemas-distribuidos)). Hay que justificarla con un SLO que la exija, y probar el failover con regularidad: un failover que nunca se probó no existe.

### Degradación elegante

Degradar con elegancia es seguir prestando una versión reducida del servicio cuando una dependencia falla, en lugar de fallar entero. Requiere decidir de antemano, por cada dependencia, qué se hace sin ella.

**Ejemplo:** si el modelo de ETA no responde, la asignación usa una regla simple (transportista más cercano con capacidad libre). Si el servicio de clima no responde, el modelo usa el valor por defecto "sin lluvia" y una métrica cuenta cuántas predicciones se hicieron así. Si el seguimiento en vivo se atrasa, la app muestra la última posición conocida con su antigüedad.

### Load shedding y backpressure

**Load shedding** es rechazar trabajo deliberadamente cuando el servicio está saturado, para que lo que sí se acepta se procese bien. Sin él, un servicio sobrecargado acepta todo, las colas internas crecen, todas las solicitudes superan su timeout y el throughput útil cae a cero. Rechazar rápido con un 503 (o `RESOURCE_EXHAUSTED` en gRPC) a un 20% es mejor que responder tarde al 100%. Conviene rechazar por prioridad: primero las consultas de dashboards, por último las asignaciones.

**Backpressure** es la versión cooperativa: el que recibe le indica al que envía que vaya más despacio. En un stream ocurre naturalmente, porque el consumidor lee a su ritmo y el lag crece. En llamadas síncronas se implementa con colas acotadas y límites de concurrencia: si la cola está llena, se rechaza en lugar de encolar indefinidamente.

### Inferencia rápida

Para que el modelo entre en su porción del presupuesto: se llama en **lote** (una solicitud con 20 candidatos, no 20 solicitudes), se mantiene el modelo cargado en memoria y "caliente" desde el arranque, se usa un formato binario (gRPC con Protocol Buffers en lugar de JSON) y, para modelos de árboles como XGBoost, se limita la profundidad y cantidad de árboles con un criterio de costo-beneficio. Las features costosas de calcular se precalculan y se leen, en lugar de computarse en la solicitud. Ver [Serving e inferencia en tiempo real](#t/serving).

### Pruebas de carga

Una prueba de carga verifica que los números del SLO se cumplen con el tráfico esperado y descubre dónde está el límite. Tipos: carga sostenida al pico esperado, estrés hasta romper (para saber cuál es el primer componente que cede), picos súbitos (para ver cómo responde el autoscaling) y prueba de larga duración (para detectar fugas de memoria o conexiones).

Errores frecuentes: probar contra un entorno con datos pequeños (los índices entran en memoria y todo parece rápido), usar siempre las mismas claves (la caché acierta el 100%) y medir la latencia desde un generador que espera la respuesta antes de enviar la siguiente solicitud, lo que oculta las demoras porque el generador baja su ritmo justo cuando el sistema se pone lento.

## Casos prácticos

### Presupuesto de 50 ms del servicio de asignación

**Situación:** la asignación debe responder con p99 menor a 50 ms. El equipo necesita saber cuánto puede gastar cada paso.

**Qué se hace:** se reparte el presupuesto usando el p99 de cada componente:

| Paso | Presupuesto p99 | Cómo se cumple |
|---|---|---|
| Red de entrada y deserialización | 3 ms | gRPC, misma AZ |
| Candidatos cercanos (índice geográfico) | 4 ms | Índice en memoria actualizado por eventos de posición |
| Features de los candidatos | 6 ms | Una lectura en lote; caché local para features lentas |
| Modelo de ETA (lote de 20 candidatos) | 25 ms | Timeout de 30 ms con regla de respaldo |
| Ranking y reglas de negocio | 2 ms | En memoria |
| Escritura de la asignación y outbox | 5 ms | Una transacción en Aurora |
| Margen | 5 ms | Pausas del runtime, reintentos de red |
| **Total** | **50 ms** | |

El presupuesto deja visibles las decisiones: la notificación al transportista sale del camino crítico vía outbox y Kafka, y las features se leen una sola vez para todos los candidatos.

### Timeout de 30 ms con regla de respaldo

**Situación:** el modelo de ETA tiene p99 de 22 ms, pero ocasionalmente (un deploy, una pausa larga) tarda 300 ms. Sin timeout, la asignación espera y rompe su presupuesto; con un timeout demasiado ajustado, cae en el respaldo demasiado seguido.

**Qué se hace:** timeout de 30 ms, que consume parte del margen pero no todo. Si vence, se usa la regla "transportista más cercano con capacidad y puntualidad histórica mayor a 85%". Se mide la tasa de respaldo como métrica propia con alerta si supera el 2% durante 10 minutos, porque un respaldo que se activa siempre degrada la calidad sin que nadie lo note. No se reintenta la llamada al modelo: no hay tiempo para un segundo intento dentro del presupuesto.

### Presupuesto de error agotado y congelamiento acordado

**Situación:** a mitad de mes, dos incidentes (una migración que bloqueó una tabla 9 minutos y un deploy con un bug de serialización) consumieron 38 de los 43 minutos de presupuesto del SLO de 99,9% del servicio de asignación. Producto quiere lanzar esta semana la reasignación automática.

**Qué se hace:** se aplica la política acordada de antemano con producto: con menos del 20% del presupuesto restante, se congelan los lanzamientos de funcionalidades en ese servicio y se priorizan las acciones de los postmortems (migraciones sin bloqueo, test de contrato para la serialización). Los arreglos de bugs y de confiabilidad siguen desplegándose. La reasignación automática se lanza al inicio de la ventana siguiente, detrás de un feature flag al 5% de los pedidos. Lo que hace que esto funcione sin conflicto es que la regla existía antes del incidente.

### Latencia media de 8 ms con p99 de 120 ms

**Situación:** el dashboard del servicio de features muestra una latencia media de 8 ms y todos lo consideran rápido. Pero la asignación, que lo llama una vez por solicitud con 20 claves, ve timeouts frecuentes.

**Qué se hace:** se mira el histograma y aparece una distribución bimodal: el 98,5% responde en 3 a 6 ms y un 1,5% tarda más de 100 ms. La causa son las claves sin caché: un fallo de caché obliga a leer de la base, y ciertos transportistas nuevos nunca están en caché. Se corrige con una lectura en lote a la base para todas las claves faltantes, precarga de transportistas activos y valores por defecto para los nuevos. El dashboard reemplaza la media por p50, p99 y p99,9, y la alerta se define sobre el p99.

## Errores comunes

- **Mirar la media de latencia.** Esconde la cola que sufren los usuarios; se monitorean p99 y p99,9 calculados desde histogramas agregados.
- **SLO al 100% o sin presupuesto acordado.** Un objetivo inalcanzable no guía decisiones; el presupuesto de error y su política se acuerdan con producto antes de necesitarlos.
- **Medir el SLI desde adentro del servicio.** Pierde los errores del balanceador y de la red; se mide lo más cerca posible de quien llama.
- **Autoscaling como única protección.** Reacciona en minutos; contra picos de segundos se necesitan load shedding y colas acotadas.
- **Caché sin plan de invalidación ni de arranque en frío.** Se define el TTL según la tolerancia del negocio y se protege la base contra el thundering herd.
- **Multi-región sin probar el failover.** Se paga el costo sin tener la garantía; se ensaya periódicamente.

## Para discutir en equipo

- ¿Nuestro SLO de asignación mide disponibilidad y latencia a la vez, y desde dónde se mide?
- ¿Qué política de presupuesto de error aceptaría producto, y quién decide cuándo se aplica?
- ¿Qué dependencias del camino crítico no tienen comportamiento degradado definido?
- ¿Qué componente cede primero si el tráfico se triplica durante una hora, y cómo lo sabemos?
- ¿Justifica algún servicio nuestro el costo de multi-región, o alcanza con multi-AZ?
