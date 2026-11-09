---
slug: prometheus-grafana
titulo: Prometheus y Grafana
resumen: Cómo recolectar métricas como series temporales con Prometheus, consultarlas con PromQL, visualizarlas en Grafana y alertar por consumo del presupuesto de errores.
lectura: 14
---

## La idea central

Las métricas son la forma más barata de saber si un sistema está sano. En lugar de guardar cada evento, se guardan números agregados a intervalos regulares: cuántas peticiones llegaron, cuántas fallaron, cuánto tardaron. **Prometheus** es el sistema open source más usado para recolectar y consultar esas métricas, y **Grafana** es la herramienta con la que se arman los dashboards y se exploran los datos. Juntos son el "tablero del auto" de un servicio: no dicen exactamente qué pieza falló, pero muestran en segundos que la temperatura subió.

La clave para usarlos bien no está en la herramienta sino en las decisiones: qué medir, con qué etiquetas, cómo resumirlo y cuándo despertar a alguien. Una métrica mal diseñada puede tumbar a Prometheus por exceso de series, y una alerta mal pensada puede despertar a la guardia por nada.

## Conceptos

### Modelo pull y series temporales

Prometheus funciona con un modelo **pull**: cada servicio expone un endpoint HTTP (normalmente `/metrics`) con sus valores actuales en texto plano, y Prometheus pasa a "rasparlos" (*scrape*) cada cierto intervalo, por ejemplo cada 15 segundos. Descubre qué servicios raspar consultando a Kubernetes, que le informa qué pods existen.

```text
# HELP pedidos_asignados_total Pedidos asignados a un transportista.
# TYPE pedidos_asignados_total counter
pedidos_asignados_total{zona="norte",resultado="ok"} 182344
pedidos_asignados_total{zona="norte",resultado="sin_candidatos"} 211
```

Cada combinación de nombre de métrica y valores de labels es una **serie temporal**: una secuencia de pares (marca de tiempo, valor). En el ejemplo hay dos series. Si hubiera 12 zonas y 3 resultados posibles, habría 36.

Ventajas del modelo pull: Prometheus sabe si un servicio está caído (el scrape falla) y los servicios no necesitan saber a dónde enviar. Para procesos muy cortos, como un job batch que dura 30 segundos, se usa un intermediario (*Pushgateway*) o se envían métricas por OTLP.

### Tipos de métricas

| Tipo | Qué representa | Ejemplo en Rumbo | Cómo se consulta |
|---|---|---|---|
| Counter | Valor que sólo sube (se reinicia a 0 si el proceso reinicia) | `pedidos_asignados_total`, `errores_modelo_total` | Casi siempre con `rate()` o `increase()`, nunca el valor crudo |
| Gauge | Valor que sube y baja | Pedidos en cola, transportistas activos por zona, memoria usada | Directo, o con `avg_over_time()`, `max_over_time()` |
| Histogram | Distribución de valores en buckets predefinidos | Latencia de asignación con buckets de 5, 10, 25, 50, 100, 250 ms | `histogram_quantile()` sobre `rate()` de los buckets |

Un histograma no guarda cada valor: cuenta cuántas observaciones cayeron por debajo de cada límite (`le`, "less or equal"). Si 9.900 de 10.000 peticiones tardaron 50 ms o menos y 9.990 tardaron 100 ms o menos, el p99 está entre 50 y 100 ms, y Prometheus lo estima interpolando. Por eso los buckets deben elegirse alrededor de los umbrales que importan: si el presupuesto es 50 ms, conviene tener buckets en 40, 50 y 60.

### PromQL

PromQL es el lenguaje de consultas de Prometheus. Tres consultas comentadas:

```promql
# 1. Tasa de errores del servicio de asignación (fracción entre 0 y 1).
#    rate(...[5m]) calcula peticiones por segundo promediadas en 5 minutos.
#    Se divide la tasa de respuestas con error por la tasa total.
sum(rate(asignacion_peticiones_total{codigo=~"5.."}[5m]))
/
sum(rate(asignacion_peticiones_total[5m]))
```

```promql
# 2. Latencia p99 a partir de un histograma.
#    Primero se calcula la tasa por bucket (le) sumando todos los pods,
#    después histogram_quantile estima el percentil 99.
histogram_quantile(
  0.99,
  sum by (le) (rate(asignacion_latencia_segundos_bucket[5m]))
)
```

```promql
# 3. Pedidos asignados por segundo, desglosados por zona.
#    "sum by (zona)" conserva sólo el label zona y suma el resto
#    (pods, versiones), dando una serie por zona.
sum by (zona) (rate(pedidos_asignados_total{resultado="ok"}[5m]))
```

Un detalle importante: siempre se aplica `rate()` antes de `sum()`. Si se suman counters crudos de varios pods y uno reinicia, la suma cae de golpe y el cálculo se rompe; `rate()` detecta los reinicios de cada serie por separado.

### Labels y cardinalidad

Los **labels** permiten desglosar una métrica (por zona, por código de respuesta, por versión del modelo). Pero cada combinación nueva de labels crea una serie nueva, y cada serie consume memoria en Prometheus. La **cardinalidad** es la cantidad de series distintas.

Se multiplica: una métrica con labels `zona` (12 valores), `codigo` (6), `endpoint` (10) y `pod` (30) puede generar hasta 12 × 6 × 10 × 30 = 21.600 series. Si además se agrega un label con el id del transportista (20.000 valores), el máximo teórico supera los 400 millones.

Regla práctica: los labels deben tener **pocos valores posibles y acotados** (decenas, a lo sumo cientos). Identificadores de pedidos, usuarios, transportistas, emails o URLs completas con parámetros nunca van como label; ese detalle pertenece a logs y trazas.

### Métodos RED y USE

Dos recetas para decidir qué medir:

- **RED**, para servicios que atienden peticiones: **R**ate (peticiones por segundo), **E**rrors (fracción con error), **D**uration (distribución de latencia). Con esas tres se sabe si un servicio atiende bien a sus clientes.
- **USE**, para recursos (CPU, memoria, disco, pools de conexiones, colas): **U**tilization (cuánto se usa), **S**aturation (cuánto trabajo espera), **E**rrors.

**Ejemplo:** para el servicio de asignación, RED: 1.800 peticiones por segundo, 0,2% de errores, p99 de 42 ms. Para el pool de conexiones a Aurora, USE: 45 de 50 conexiones en uso (90% de utilización), 12 goroutines esperando conexión (saturación), 3 timeouts por minuto (errores). La saturación del pool anticipa un problema de latencia antes de que aparezca en RED.

### Métricas de negocio y de ML

Las métricas técnicas pueden estar perfectas mientras el negocio sufre. Por eso conviene medir también:

- **Negocio:** pedidos creados y asignados por minuto, tasa de entregas a tiempo por zona, tiempo desde creación hasta asignación, pedidos sin candidatos.
- **Modelo:** distribución de las predicciones (por ejemplo, histograma de probabilidad de entrega a tiempo), latencia de inferencia, tasa de respaldo (cuántas veces se usó la heurística porque el modelo no respondió), porcentaje de features nulas, error de ETA cuando se conoce el resultado real.

**Ejemplo:** si la probabilidad media predicha pasa de 0,88 a 0,52 en una hora sin cambios en la tasa real de entregas a tiempo, algo cambió en las entradas del modelo. Ver [Monitoreo de modelos](#t/monitoreo-modelos).

### Grafana y diseño de dashboards

Grafana se conecta a Prometheus (y a otras fuentes: Loki para logs, Tempo para trazas, bases SQL) y permite armar paneles. Un buen dashboard cuenta una historia **de lo general a lo particular**: arriba, lo que responde "¿estamos bien?"; abajo, lo que ayuda a encontrar el porqué.

Buenas prácticas:

- La primera fila debe poder leerse en 5 segundos durante un incidente.
- Variables de dashboard (desplegables) para zona, entorno o versión, en lugar de un panel por zona.
- Unidades y umbrales visibles (líneas en 50 ms si ese es el presupuesto).
- Marcar despliegues como anotaciones verticales, porque "¿qué cambió?" es la primera pregunta.
- Mostrar percentiles (p50, p95, p99), no sólo promedios.
- Dashboards como código (JSON versionado o Terraform), para no perderlos ni editarlos a mano en producción.

### Alertas por burn rate

Un **SLO** (objetivo de nivel de servicio) es una meta como "el 99,9% de las peticiones de asignación responde sin error en 30 días". El 0,1% restante es el **presupuesto de errores**: lo que se puede fallar sin incumplir.

Con números: en 30 días hay 43.200 minutos. Un 0,1% equivale a 43,2 minutos de caída total, o a muchas más horas de degradación parcial. Si el servicio atiende 100 millones de peticiones al mes, el presupuesto son 100.000 peticiones fallidas.

El **burn rate** (velocidad de consumo) mide qué tan rápido se gasta ese presupuesto. Burn rate 1 significa que, a este ritmo, el presupuesto se agota justo al terminar los 30 días. Burn rate 10 significa que se agotaría en 3 días.

- Si la tasa de errores actual es 0,1%, el burn rate es 0,1 / 0,1 = 1.
- Si es 1,44%, el burn rate es 14,4. En una hora consume 14,4 × (1 / 720) = 2% del presupuesto mensual (un mes tiene 720 horas). Mantenido, lo agota en unas 50 horas.
- Si es 0,6%, el burn rate es 6. En 6 horas consume 6 × 6 / 720 = 5% del presupuesto.

Una configuración muy difundida combina ventanas:

| Alerta | Condición | Acción |
|---|---|---|
| Rápida | Burn rate > 14,4 en la última hora **y** en los últimos 5 minutos | Page |
| Media | Burn rate > 6 en las últimas 6 horas **y** en los últimos 30 minutos | Page |
| Lenta | Burn rate > 1 en los últimos 3 días | Ticket |

La ventana corta (5 o 30 minutos) evita que la alerta siga sonando cuando el problema ya se resolvió. Este enfoque alerta por síntoma y en proporción al daño real; ver [On-call, runbooks e incidentes](#t/on-call).

### Alertmanager

Prometheus evalúa las reglas de alerta, pero no notifica. Eso lo hace **Alertmanager**, que recibe las alertas activas y se encarga de:

- **Agrupar:** si fallan 30 pods a la vez, envía una notificación, no 30.
- **Enrutar:** según labels (`severidad="page"` va a la herramienta de paging; `severidad="ticket"`, a un canal de chat).
- **Inhibir:** si está activa "Aurora caída", silencia las alertas derivadas de los servicios que dependen de Aurora.
- **Silenciar:** durante un mantenimiento programado.

### Escala: Thanos, Mimir y servicios gestionados

Un Prometheus aislado guarda datos en disco local, por pocas semanas, y no tiene alta disponibilidad. Cuando hay varios clusters o se necesita retención larga:

- **Thanos:** agrega a los Prometheus existentes almacenamiento en object storage (S3), consultas globales entre clusters y deduplicación de réplicas.
- **Grafana Mimir** (y su antecesor Cortex): backend horizontalmente escalable que recibe métricas por *remote write*, multi-tenant, pensado para cientos de millones de series.
- **Servicios gestionados:** Amazon Managed Service for Prometheus, Grafana Cloud y otros. Menos operación a cambio de un costo por serie o por muestra ingerida. Ver [Costos cloud (FinOps)](#t/finops).

Para clientes on-prem suele bastar un Prometheus local con retención corta y, si el contrato lo permite, el envío de un subconjunto agregado de métricas.

## Casos prácticos

### Dashboard del servicio de asignación

**Situación:** el dashboard actual tiene 40 paneles sin orden; en el último incidente nadie supo dónde mirar.

**Qué se hace:** se reorganiza en cuatro filas, de lo general a lo particular:

1. **Negocio:** pedidos asignados por minuto, tiempo de creación a asignación (p50 y p95), porcentaje sin candidatos, tasa de entregas a tiempo por zona.
2. **Servicio (RED):** peticiones por segundo, tasa de errores con línea de SLO, latencia p50/p95/p99 con línea en 50 ms, presupuesto de errores restante.
3. **Modelo:** latencia de inferencia, tasa de respaldo heurístico, distribución de predicciones, porcentaje de features nulas, versión desplegada.
4. **Dependencias (USE y RED):** feature store, Aurora (pool de conexiones, latencia), Kafka (lag del consumidor), proveedor de clima.

Se agregan variables de zona y entorno y anotaciones de despliegue. La primera fila basta para decidir si hay incidente; las siguientes guían el diagnóstico.

### Explosión de cardinalidad por el id del pedido

**Situación:** alguien agrega `pedido_id` como label a la métrica de latencia para "poder buscar pedidos lentos". En dos días, Prometheus pasa de 300.000 a 9 millones de series, usa toda su memoria y se reinicia en bucle. Durante ese tiempo no hay alertas.

**Qué se hace:** se revierte el cambio y se borran las series afectadas. Para buscar pedidos lentos se usan trazas con `pedido.id` como atributo y exemplars en el histograma. Como prevención: límites de series por scrape en la configuración de Prometheus, una alerta sobre la cantidad total de series y revisión de labels nuevos en code review. Además, se monitorea a Prometheus desde un sistema independiente, para no quedar ciegos cuando él falla.

### Alerta por burn rate en lugar de umbral fijo

**Situación:** existe la alerta "tasa de errores > 1% durante 5 minutos". Suena por picos breves de madrugada con muy poco tráfico (2 errores en 100 peticiones) y no suena cuando la tasa se mantiene en 0,8% durante dos días, lo que consume más de la mitad del presupuesto mensual (burn rate 8 durante 48 horas: 8 × 48 / 720, alrededor del 53%).

**Qué se hace:** se reemplaza por alertas de burn rate multi-ventana sobre un SLO de 99,9%. El pico breve no sostiene un burn rate de 14,4 en una hora y no despierta a nadie. El 0,8% sostenido es un burn rate de 8, que dispara la alerta media de 6 horas. Resultado: menos pages y más relevantes.

### El promedio que oculta la cola

**Situación:** el panel de latencia muestra un promedio de 22 ms, cómodo frente al presupuesto de 50 ms. Sin embargo, soporte recibe quejas de comercios grandes por asignaciones lentas.

**Qué se hace:** se agregan p95 y p99 desde el histograma. El p99 está en 180 ms. Con 1.800 peticiones por segundo, el 1% más lento son 18 peticiones por segundo, más de 1,5 millones al día. Desglosando por tipo de comercio, los comercios grandes envían lotes de pedidos que disparan consultas pesadas al feature store. El promedio nunca lo habría mostrado porque el 99% rápido diluye el 1% lento. Se fija el SLO de latencia sobre el p99, no sobre el promedio.

## Errores comunes

- **Usar el valor crudo de un counter.** Siempre se usa `rate()` o `increase()`; el valor absoluto depende de cuándo reinició el proceso.
- **Labels con identificadores.** Pedido, usuario, transportista o URL completa nunca van como label; ese detalle va en trazas y logs.
- **Promediar percentiles.** El promedio de los p99 de 30 pods no es el p99 del servicio; se suman los buckets y después se calcula el percentil.
- **Buckets mal elegidos.** Si el presupuesto es 50 ms y los buckets son 10, 100 y 1.000 ms, el p99 estimado será muy impreciso justo donde importa.
- **Dashboards sin jerarquía.** Cuarenta paneles al mismo nivel no ayudan en un incidente; primero negocio y síntomas, después causas.
- **Alertas por umbral fijo sobre todo.** Generan ruido con poco tráfico y silencio ante degradaciones lentas; el burn rate escala con el daño real.

## Para discutir en equipo

- ¿Qué SLO tiene sentido para el servicio de asignación: de disponibilidad, de latencia o ambos? ¿Con qué ventana?
- ¿Qué métricas del modelo de ETA deberían estar en la primera fila del dashboard y cuáles más abajo?
- ¿Cómo evitamos que un label nuevo explote la cardinalidad sin frenar a quien quiere instrumentar?
- ¿Conviene operar Prometheus y Thanos nosotros o usar un servicio gestionado, considerando también las instalaciones on-prem?
- ¿Qué alertas actuales podrían reemplazarse por alertas de burn rate?
