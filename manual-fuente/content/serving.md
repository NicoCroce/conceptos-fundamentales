---
slug: serving
titulo: Serving e inferencia en tiempo real
resumen: Cómo se pone un modelo a responder predicciones en producción dentro de un presupuesto de latencia, con features consistentes, escalado, fallback y trazabilidad.
lectura: 15
---

## La idea central

**Serving** es la parte del sistema que recibe una petición, obtiene los datos necesarios, ejecuta el modelo y devuelve una predicción. **Inferencia** es el acto de usar el modelo ya entrenado para predecir. Entrenar puede tardar horas; servir tiene que tardar milisegundos, miles de veces por segundo, sin caerse.

La intuición más importante, y la que más sorprende a quien viene de fuera del ML: en datos tabulares, ejecutar el modelo casi nunca es lo lento. Un XGBoost de unos cientos de árboles evalúa 20 candidatos en una fracción de milisegundo. Lo que consume el presupuesto es **conseguir las features**: leer la carga actual del transportista, su historial, el clima de la zona. Un buen sistema de serving es, sobre todo, un buen sistema de datos de baja latencia con un modelo al final.

## Conceptos

### Batch vs. online

- **Batch (por lotes):** las predicciones se calculan de antemano, para muchas entidades a la vez, y se guardan en una tabla. Quien las necesita, las lee. Es barato, simple y tolera modelos lentos. Sirve cuando las entradas se conocen con anticipación.
- **Online (en tiempo real):** la predicción se calcula en el momento de la petición, con datos actuales. Es necesaria cuando las entradas no se pueden conocer antes (qué pedido, qué transportistas están libres ahora, a qué distancia).

**Ejemplo:** el pronóstico de demanda por zona y franja horaria para mañana se calcula de noche (batch). La probabilidad de entrega a tiempo para el pedido que acaba de entrar con los transportistas disponibles en este instante solo puede calcularse online.

Existe un punto intermedio: precalcular en batch las partes lentas (historial de 30 días de cada transportista) y combinar online con las partes rápidas (distancia actual).

### Modelo en memoria y precalentamiento

Para inferencia de baja latencia, el modelo se carga **una vez** al arrancar el proceso y queda en memoria. Cargarlo desde S3 en cada petición agregaría decenas o cientos de milisegundos.

Pero las primeras predicciones tras cargar suelen ser más lentas: cachés de CPU frías, inicialización perezosa de estructuras, compilación justo a tiempo en algunos runtimes, conexiones a Redis o al feature store aún no abiertas. El **precalentamiento** (warm-up) consiste en ejecutar unas cuantas predicciones sintéticas y abrir conexiones *antes* de declararse listo. En Kubernetes, eso se traduce en que la **readiness probe** solo responde OK al terminar el warm-up, así el balanceador no le manda tráfico real a una réplica fría.

### Las features como cuello de botella real

Un desglose típico, hipotético, de una petición de asignación con 20 candidatos:

| Paso | Tiempo |
|---|---|
| Recibir y validar la petición | 0,3 ms |
| Obtener features de 20 transportistas (lecturas de red) | 8 a 40 ms |
| Construir la matriz de features | 0,5 ms |
| Inferencia XGBoost (20 filas) | 0,3 ms |
| Serializar respuesta | 0,1 ms |

El rango de las features depende de cómo se lean. Veinte lecturas secuenciales a Redis de 1 ms cada una suman 20 ms, y en el p99 (el 1% más lento) cada lectura puede tardar 3 o 5 ms. Las estrategias para bajar ese número:

- **Lecturas en lote:** un solo `MGET` o pipeline en lugar de 20 llamadas.
- **Caché local en memoria** del proceso, alimentada por un stream de eventos: leer de un mapa en memoria cuesta microsegundos.
- **Precalcular** lo que no cambia durante el día.
- **Paralelizar** lecturas a fuentes distintas.

### Formatos optimizados, CPU vs. GPU

El archivo del modelo tal como sale del entrenamiento no siempre es el más eficiente para servir. Opciones:

- **ONNX:** un formato estándar e intercambiable de modelos, con un runtime optimizado (ONNX Runtime). Permite entrenar en Python y servir desde otro lenguaje o con un ejecutor más rápido.
- **Compiladores de árboles:** herramientas que convierten un ensamble de árboles en código nativo o en operaciones vectorizadas, reduciendo la latencia de inferencia. Útiles cuando hay muchos árboles o volumen muy alto.

**CPU vs. GPU:** las GPU brillan con operaciones masivamente paralelas sobre matrices grandes (redes neuronales, LLMs) y con lotes grandes. Para un árbol con 20 filas por petición, la CPU es más rápida (no hay que copiar datos a la GPU) y mucho más barata. Regla práctica: modelos de árboles y lineales en CPU; redes neuronales grandes en GPU, idealmente con **batching dinámico** (agrupar varias peticiones que llegan en pocos milisegundos para procesarlas juntas).

### Servidores de modelos

Hay software especializado que resuelve carga de modelos, versiones, métricas y batching:

- **Triton Inference Server:** soporta muchos formatos (ONNX, PyTorch, TensorFlow, XGBoost mediante backend de árboles), batching dinámico, múltiples modelos por servidor; fuerte en GPU.
- **TorchServe:** orientado a modelos PyTorch.
- **KServe:** capa sobre Kubernetes que estandariza el despliegue de modelos (con autoescalado, canary y distintos runtimes por debajo).
- **SageMaker (endpoints):** servicio gestionado de AWS; se sube el modelo y AWS administra la infraestructura.

No siempre hacen falta. Para un XGBoost con lógica de features propia, un microservicio pequeño en Python o Go suele ser más simple y controlable.

### Modelo separado del código

El servicio y el modelo tienen ciclos de vida distintos: el código cambia cuando cambia la lógica; el modelo cambia cada semana con reentrenamiento. Por eso el servicio no debería traer el modelo dentro de su imagen, sino **consultar al registro de modelos** qué versión está marcada como producción, descargarla y cargarla, y vigilar si cambia (ver [Ciclo de vida de modelos](#t/ciclo-vida-modelos)). Así, promover o revertir un modelo es cambiar un puntero, sin redeploy.

Una precaución: el servicio debe validar que la versión nueva es compatible (mismo esquema de features, mismo formato de salida) antes de cambiar, y conservar la anterior en memoria hasta que la nueva haya pasado su warm-up.

### Escalado y mínimo de réplicas

El servicio escala horizontalmente agregando réplicas según CPU, peticiones por segundo o latencia. Dos detalles propios de serving de modelos:

- **Mínimo de réplicas:** cargar el modelo, llenar la caché local de features y calentar puede tardar de segundos a minutos. Si el autoescalado baja a una réplica de madrugada y a las 8:00 llega el pico, las réplicas nuevas no estarán listas a tiempo. Conviene mantener un mínimo que absorba el pico inicial y escalar por anticipado en horarios conocidos.
- **Memoria:** cada réplica tiene su copia del modelo y de la caché. Un modelo de 200 MB más una caché de 1 GB multiplicados por 30 réplicas es una cifra a vigilar.

### Fallback

¿Qué pasa si el modelo no responde a tiempo, si faltan features o si el servicio está caído? Siempre hay que tener una respuesta de respaldo, decidida de antemano:

- Una heurística simple: elegir el transportista disponible más cercano con carga menor a N.
- Un baseline: ETA por mediana de zona y franja.
- Una versión anterior del modelo.

El llamador fija un **deadline** (tiempo máximo de espera). Si se supera, usa el fallback y registra que lo hizo. La tasa de fallback es una métrica de primera clase: si pasa del 0,1% al 8%, hay un problema aunque no haya errores visibles.

### Registro de predicciones asíncrono

Cada predicción debe registrarse (features, versión, salida, decisión) para monitoreo, auditoría y entrenamiento futuro. Pero escribirlo en la base de datos dentro de la petición suma latencia y acopla la disponibilidad del serving a la de la base. Lo correcto es escribirlo de forma **asíncrona**: se encola en memoria y un proceso de fondo lo publica a Kafka (por ejemplo, un tópico `predicciones-asignacion`), desde donde se persiste en S3 o en un data warehouse. Si el buffer se llena, se descartan registros y se incrementa un contador, en lugar de bloquear la petición.

### Consistencia entrenamiento-serving

El **training-serving skew** (sesgo entrenamiento-serving) ocurre cuando las features que ve el modelo en producción se calculan distinto que en entrenamiento. Ejemplos típicos:

- En entrenamiento, `carga_actual` se calculó con una consulta SQL que contaba pedidos "asignados o retirados"; en producción, el servicio cuenta solo "asignados".
- Zona horaria UTC en un lado y hora local en el otro para la feature `hora`.
- Nulos rellenados con 0 en el pipeline de entrenamiento y enviados como `NaN` en producción.

El modelo no da error: simplemente predice peor. Se previene con una sola definición de cada feature usada en ambos lados (un feature store o una biblioteca compartida, ver [Features y feature stores](#t/feature-stores)) y se detecta comparando las features registradas en producción con las del dataset de entrenamiento.

### Tabla de patrones de serving

| Patrón | Latencia típica (orden de magnitud) | Ventaja | Desventaja |
|---|---|---|---|
| Embebido en el servicio llamador | Microsegundos a 1 ms (sin red) | Sin salto de red, sin servicio extra | Acopla el ciclo del modelo al del servicio; obliga a usar el lenguaje del llamador o un runtime portable (ONNX) |
| Microservicio de inferencia (gRPC) | 1 a 10 ms más la obtención de features | Separa equipos y despliegues; Python con el ecosistema de ML; escala independiente | Un salto de red más; otro servicio que operar |
| Plataforma gestionada (SageMaker, KServe, Triton) | 5 a 50 ms según configuración | Versiones, autoescalado, canary y métricas resueltos | Menos control fino; costo; la lógica de features suele quedar afuera |
| Batch precalculado | Lo que tarde una lectura (1 a 5 ms) | Barato, simple, admite modelos pesados | Solo sirve si las entradas se conocen antes; los datos envejecen |

### El camino de una petición de asignación

```text
Comercio crea pedido
        |
        v
[Servicio de asignación (Go)]
   | 1. filtra candidatos (disponibles, distancia, capacidad) -> 20 transportistas
   | 2. llamada gRPC con deadline 30 ms
   v
[Servicio de inferencia (Python)]
   | 3. lee features de los 20 candidatos de la caché local en memoria
   |       ^
   |       | (actualizada continuamente por un consumidor de Kafka:
   |       |  pedido asignado, retirado, entregado -> carga e historial)
   | 4. arma matriz 20 x N, XGBoost en memoria -> P(a tiempo), ETA
   | 5. encola registro de predicción (asíncrono -> Kafka)
   v
[Servicio de asignación]
   | 6. combina puntajes con reglas de negocio, elige transportista
   | 7. si venció el deadline o hubo error -> heurística de respaldo
   v
Evento "pedido asignado" a Kafka
```

## Casos prácticos

### Arquitectura del servicio de asignación de Rumbo

**Situación:** la asignación tiene un presupuesto total de alrededor de 50 ms. El servicio de asignación está en Go; el equipo de ML trabaja en Python con XGBoost.
**Qué se hace:** se adopta un microservicio de inferencia en Python, llamado por gRPC (ver [gRPC y REST](#t/grpc-rest)) con un **deadline de 30 ms**, que deja margen para el filtrado de candidatos y la lógica posterior. El modelo XGBoost vive en memoria y su versión se toma del registro de modelos. Las features dinámicas (carga actual, pedidos en curso, tasa a tiempo reciente) se mantienen en una **caché local** alimentada por un consumidor de Kafka, de modo que obtenerlas cuesta microsegundos en lugar de lecturas de red. Si la llamada supera el deadline o falla, el servicio en Go usa la heurística de respaldo (más cercano con menor carga) y emite una métrica de fallback. El registro de predicciones se publica a Kafka de forma asíncrona. Se mantiene un mínimo de réplicas suficiente para el pico de la mañana.

### p99 alto por lecturas sucesivas a Redis

**Situación:** una primera versión leía las features de cada candidato con una llamada a Redis por transportista y por grupo de features: unas 60 lecturas secuenciales. La mediana era 12 ms, pero el p99 llegaba a 45 ms y el fallback se activaba en el 3% de las peticiones en hora pico.
**Qué se hace:** se identifica con tracing que el tiempo está en Redis, no en el modelo. Primer paso: agrupar las lecturas en un solo pipeline o `MGET` (el p99 baja a unos 9 ms). Segundo paso, para las features más calientes: mover la carga y los pedidos en curso a la caché local alimentada por Kafka, dejando Redis solo para features menos frecuentes. Se agrega un límite: si una feature no está disponible a tiempo, se usa un valor por defecto documentado en lugar de esperar, y se cuenta cuántas veces pasa.

### Arranque en frío tras autoescalado

**Situación:** a las 12:00 entra un pico de pedidos, el autoescalado crea 6 réplicas nuevas y durante 2 minutos la latencia se dispara y el fallback sube al 15%.
**Qué se hace:** se descubre que las réplicas nuevas se declaraban listas apenas arrancaba el proceso, pero todavía estaban descargando el modelo, llenando la caché desde Kafka y abriendo conexiones. Se cambia la readiness probe para que solo responda OK tras cargar el modelo, completar la caché y ejecutar predicciones de warm-up. Además, se sube el mínimo de réplicas en las franjas de pico conocidas y se escala de forma programada 15 minutos antes, en lugar de depender solo de la reacción del autoescalado.

### Pronóstico de demanda que no necesita tiempo real

**Situación:** alguien propone exponer el modelo de pronóstico de demanda como servicio online "para que sea más moderno".
**Qué se hace:** se analiza quién usa la predicción y cuándo. El pronóstico se usa para planificar turnos de transportistas del día siguiente; las entradas (zona, franja, día, calendario, clima pronosticado) se conocen la noche anterior. Se mantiene en **batch nocturno**: se calcula para todas las zonas y franjas, se guarda en una tabla y los consumidores la leen. Un servicio online agregaría infraestructura, costo y un punto de falla sin ningún beneficio. Si más adelante se necesita reajustar el pronóstico durante el día, se puede recalcular cada hora en batch antes de pensar en tiempo real.

## Errores comunes

- **Optimizar el modelo cuando el problema son las features.** Mide con tracing dónde se va el tiempo antes de optimizar; casi siempre son las lecturas de datos.
- **No tener fallback ni deadline.** Define el deadline en el llamador, una respuesta de respaldo concreta y una métrica de tasa de fallback con alerta.
- **Declarar la réplica lista antes del warm-up.** La readiness debe esperar a que el modelo esté cargado, la caché llena y las conexiones abiertas.
- **Registrar predicciones de forma síncrona.** Encola y publica en segundo plano; si el buffer se llena, descarta y cuenta, nunca bloquees la petición.
- **Calcular features distinto en entrenamiento y producción.** Usa una única definición compartida y compara periódicamente las distribuciones de ambos lados.
- **Servir online lo que podría ser batch.** Si las entradas se conocen de antemano, precalcular es más barato y más confiable.

## Para discutir en equipo

- ¿Cuál es hoy nuestra tasa de fallback en asignación, y qué valor debería disparar una alerta?
- ¿Qué features podríamos precalcular en batch sin perder calidad, y cuáles necesitan estar al segundo?
- Si mañana el modelo pasa a ser una red neuronal que necesita GPU, ¿qué partes de esta arquitectura cambian?
- ¿Cómo verificamos que una versión nueva del modelo es compatible con el esquema de features antes de cargarla?
- ¿Cuánto tarda una réplica nueva en estar realmente lista, y lo medimos?
