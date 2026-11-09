---
slug: ciclo-vida-modelos
titulo: Ciclo de vida de modelos
resumen: Las etapas que lleva un modelo desde la definición del problema hasta su reentrenamiento, y las prácticas que permiten lanzarlo, controlarlo y auditarlo sin sorpresas.
lectura: 16
---

## La idea central

Entrenar un modelo es una fracción pequeña del trabajo. Un modelo en producción es un componente de software que depende de datos que cambian, que toma decisiones que afectan a personas reales y que se degrada con el tiempo aunque nadie toque su código. El **ciclo de vida** es el conjunto de etapas y controles que permiten llevarlo a producción con confianza, saber en todo momento qué versión está decidiendo y con qué datos se entrenó, y reemplazarlo o revertirlo sin drama.

Una buena analogía es la de un medicamento: no basta con que funcione en el laboratorio. Se define para qué sirve, se prueba con distintos grupos, se aprueba con documentación, se libera en etapas, se vigilan efectos adversos y se puede retirar. Con los modelos hacemos lo mismo, en semanas en lugar de años.

## Conceptos

### Las 9 etapas

```text
   +-------------------------------------------------------------+
   |                                                             |
   v                                                             |
[1] Problema y métrica de negocio                                |
   |                                                             |
[2] Datos  ---->  [3] Features                                   |
                       |                                         |
                  [4] Entrenamiento y experimentación            |
                       |                                         |
                  [5] Evaluación offline por segmentos           |
                       |                                         |
                  [6] Aprobación (model card)                    |
                       |                                         |
                  [7] Despliegue gradual (sombra, canary, A/B)   |
                       |                                         |
                  [8] Monitoreo  ---- deriva / caída ---->  [9] Reentrenamiento
                                                                 |
                                         (vuelve a 4 o 5) <------+
```

1. **Problema y métrica de negocio.** Qué decisión mejora el modelo y cómo sabremos que funcionó. No "predecir ETA", sino "reducir el error de la ETA mostrada al comercio para bajar reclamos". Se define la métrica de negocio (tasa de entregas a tiempo, reclamos por cada mil pedidos) y la métrica técnica que se le aproxima (MAE).
2. **Datos.** De dónde salen las etiquetas y las features, con qué calidad, desde cuándo y con qué sesgos. En Rumbo, la mayoría viene de eventos de Kafka (pedido creado, asignado, entregado, fallido).
3. **Features.** Transformar datos crudos en variables útiles, con disponibilidad garantizada en el momento de predecir y cálculo idéntico en entrenamiento y producción (ver [Features y feature stores](#t/feature-stores)).
4. **Entrenamiento y experimentación.** Probar variantes y registrar cada experimento con sus parámetros, datos y resultados.
5. **Evaluación offline por segmentos.** No solo la métrica global: por zona, por franja horaria, por clima, por transportistas nuevos vs. antiguos. Un modelo que mejora 3% en promedio y empeora 15% en la zona sur no está listo.
6. **Aprobación.** Revisión con una **model card** y criterios explícitos.
7. **Despliegue gradual.** Modo sombra, canary, A/B.
8. **Monitoreo.** Latencia, errores, distribución de features y predicciones, y la métrica real cuando llegan las etiquetas (ver [Monitoreo de modelos](#t/monitoreo-modelos)).
9. **Reentrenamiento.** Con datos nuevos, pasando por los mismos controles que un modelo nuevo.

### MLOps

**MLOps** es la aplicación de prácticas de DevOps (automatización, versionado, CI/CD, observabilidad) al ciclo de vida de modelos. Agrega dos ejes que el software tradicional no tiene: los **datos** también se versionan, y el comportamiento del sistema puede cambiar sin que cambie el código, porque cambia el mundo.

Concretamente, en un equipo como el de Rumbo, MLOps significa: pipelines de entrenamiento ejecutables con un comando, un registro de modelos, despliegues que no requieren tocar el servicio que consume el modelo, métricas de modelo en los mismos dashboards que las del resto del sistema y la capacidad de responder "¿qué modelo tomó esta decisión y por qué?".

### Reproducibilidad

Un entrenamiento es **reproducible** si, con los mismos insumos, se obtiene el mismo modelo (o uno equivalente). Para eso hay que fijar:

- **Código:** commit exacto del repositorio.
- **Datos:** un snapshot o una consulta con fecha de corte fija ("pedidos asignados hasta 2026-10-01 00:00 UTC"), no "la tabla actual".
- **Entorno:** versiones de bibliotecas (una imagen de contenedor o un lockfile).
- **Configuración y semillas:** hiperparámetros y semillas aleatorias.

**Ejemplo:** un modelo de ETA en producción empieza a fallar y se necesita entender qué cambió respecto del anterior. Si ambos se entrenaron con "la tabla de pedidos" sin fecha de corte, y esa tabla fue corregida retroactivamente, es imposible saber si el cambio vino del código, de los datos o de la corrección.

### Registro de modelos

Un **registro de modelos** (model registry) es un catálogo central donde cada modelo entrenado queda guardado con su versión, sus artefactos (el archivo del modelo y el pipeline de preprocesamiento), sus métricas, el dataset y commit con que se entrenó, y su **estado**: candidato, en sombra, en producción, archivado. Herramientas como MLflow lo ofrecen.

**Por qué importa:** el servicio de serving no carga "el último archivo en S3", sino "la versión que el registro marca como producción para `eta-model`". Cambiar de versión, o volver a la anterior, es cambiar ese puntero.

### Model card

Una **model card** es un documento corto que acompaña a cada modelo aprobado. Resume para qué sirve, cómo se entrenó, cómo rinde y dónde no se debe usar. Es la base de la revisión de aprobación y de la auditoría posterior.

**Ejemplo breve:**

```text
Modelo: asignacion-ontime  ·  Versión: 14  ·  Estado: candidato
Propósito: estimar P(entrega a tiempo) por transportista candidato para el servicio de asignación.
No usar para: evaluar desempeño individual de transportistas ni decisiones disciplinarias.
Datos: pedidos asignados 2026-01-01 a 2026-09-30 (corte temporal); validación octubre; test 1-15 nov.
Features: 23 (distancia, zona, hora, clima, carga, historial 30 días...). Sin PII.
Métricas test: ROC-AUC 0,81 (v13: 0,79); Brier 0,071 (v13: 0,074).
Por segmento: zona sur ROC-AUC 0,76 (v13: 0,77, dentro de tolerancia); transportistas < 20 entregas: 0,70.
Limitaciones: poco dato con nieve; transportistas nuevos subrepresentados; sesgo de selección por asignaciones pasadas.
Criterio de éxito online: +0,5 p.p. en entregas a tiempo en A/B al 10% durante 14 días, sin empeorar p99.
Responsable: equipo de ML de asignación. Aprobado por: ...
```

### Modo sombra

En **modo sombra** (shadow mode) el modelo nuevo recibe las mismas peticiones que el de producción y calcula su predicción, pero esa predicción **no se usa** para decidir: solo se registra. Sirve para verificar, sin riesgo, que el modelo funciona en el entorno real: latencia, errores, features faltantes, distribución de predicciones y diferencias con el modelo actual.

**Ejemplo:** en sombra se descubre que el 4% de las peticiones llega con `clima` nulo, algo que nunca pasaba en el dataset de entrenamiento (donde los nulos se habían rellenado en la consulta). Sin la sombra, se habría descubierto en producción.

Limitación: la sombra no puede medir el efecto en el negocio, porque sus decisiones nunca se ejecutan.

### Canary y A/B con criterio de éxito previo

- **Canary:** se envía una fracción mínima del tráfico real (1% a 5%) al modelo nuevo para detectar problemas graves con un impacto acotado. El foco es la salud técnica.
- **A/B test:** se reparte el tráfico entre el modelo actual (control) y el nuevo (tratamiento), por ejemplo 90/10, durante un período suficiente para medir la métrica de negocio con significancia estadística.

La regla de oro: el **criterio de éxito se define antes** de empezar. "Se promueve si la tasa de entregas a tiempo sube al menos 0,5 puntos porcentuales con 95% de confianza en 14 días, sin empeorar la latencia p99 ni ninguna zona más de 1 punto". Si el criterio se decide mirando los resultados, siempre se encuentra algún segmento donde el modelo nuevo "gana".

Un detalle propio de la logística: la unidad de aleatorización importa. Si se asignan pedidos al azar entre los dos modelos, ambos compiten por los mismos transportistas y se contaminan entre sí. A veces conviene aleatorizar por zona o por franja horaria.

### Rollback sin redeploy

Revertir un modelo no debería requerir compilar ni desplegar el servicio. El servicio lee del registro (o de una configuración) qué versión usar, y el rollback es cambiar ese valor. Si el modelo está embebido en la imagen del servicio, cada rollback implica un pipeline de CI/CD completo, con minutos u horas de exposición.

**Ejemplo:** a las 19:10 la tasa de fallas del modelo v14 sube por un problema de features. Un operador marca v13 como producción en el registro; en menos de un minuto las réplicas recargan v13. Ningún contenedor se reinicia.

### Reentrenamiento con gates

El mundo cambia (nuevas zonas, nuevos transportistas, estacionalidad) y los modelos se degradan. El reentrenamiento periódico (por ejemplo semanal) los mantiene actualizados. Pero un reentrenamiento automático sin controles es un despliegue automático de código no revisado.

Los **gates** (compuertas) son verificaciones automáticas que el modelo reentrenado debe pasar para ser promovido:

- Métrica global en test no peor que la del modelo actual (con tolerancia).
- **Por segmento:** ninguna zona, franja o grupo relevante empeora más de X.
- Calibración dentro de rango.
- Validación de datos: volumen de entrenamiento, tasa de nulos y distribución de la etiqueta dentro de lo esperado.
- Pasa por sombra antes de producción.

Si un gate falla, el modelo queda como candidato y alguien lo revisa.

### Sesgo de selección y exploración

En asignación solo observamos el resultado de la opción elegida. Si el modelo siempre manda pedidos de la zona norte al transportista A, solo tendremos datos de A en el norte. El próximo modelo aprende de esos datos y vuelve a elegir a A. Este **bucle de retroalimentación** (feedback loop) produce un **sesgo de selección**: los datos de entrenamiento reflejan las decisiones del modelo anterior, no el mundo.

La forma de romperlo es la **exploración** descrita en [Fundamentos de ML](#t/fundamentos-ml): reservar una fracción de decisiones para probar opciones con algo de azar y **registrar la probabilidad** con que se eligió cada opción. Con esas probabilidades se pueden usar técnicas de evaluación fuera de política (off-policy evaluation), que reponderan los resultados observados para estimar cómo habría rendido una política distinta sin desplegarla.

### Trazabilidad de cada decisión

Cada decisión del modelo en producción debería poder reconstruirse. Para eso, se registra por cada predicción: identificador de la petición, timestamp, versión del modelo, versión de features, las features exactas usadas, la salida, la decisión final (que puede incluir reglas posteriores al modelo), si fue exploratoria y la probabilidad de selección. Este registro se escribe de forma asíncrona para no sumar latencia (ver [Serving e inferencia en tiempo real](#t/serving)) y se une después con el resultado real (entregado a tiempo o no).

**Por qué importa:** sirve para auditoría, para explicar decisiones, para depurar incidentes y como dataset del próximo entrenamiento sin recalcular features con fuga.

## Casos prácticos

### Lanzar un modelo de asignación nuevo

**Situación:** la versión 14 del modelo de entrega a tiempo mejora la ROC-AUC de 0,79 a 0,81 offline.
**Qué se hace:** se completa la model card con métricas por segmento y criterio de éxito online definido de antemano. Se despliega en **sombra durante 2 semanas**: se verifica latencia p99 dentro del presupuesto, ausencia de errores, tasa de features nulas y cuántas decisiones cambiarían respecto de v13 (si cambia el 40% de las asignaciones, el riesgo es mayor que si cambia el 5%). Luego pasa a **A/B con 10% del tráfico**, aleatorizado por zona y franja, durante 14 días. Se promueve solo si cumple el criterio pactado. Durante todo el proceso, el rollback es un cambio en el registro.

### Reentrenamiento semanal durante una tormenta atípica

**Situación:** el reentrenamiento semanal toma datos de una semana con una tormenta excepcional. El modelo resultante aprende que "todo llega tarde" y su métrica global en el test (también de esa semana) se ve aceptable. Un pipeline sin controles lo promovería.
**Qué se hace:** los gates detectan el problema: la distribución de la etiqueta (tasa de entregas tardías) está muy fuera del rango histórico, y en un **conjunto de evaluación de referencia** fijo, con semanas normales, el modelo empeora en todos los segmentos de clima seco. El modelo queda como candidato y no se promueve. Como mejora de diseño, se amplía la ventana de entrenamiento (varias semanas o meses, no solo la última) y se mantiene la evaluación contra conjuntos de referencia además de la semana más reciente.

### Transportistas nuevos que el modelo nunca prueba

**Situación:** los transportistas incorporados el último mes reciben una fracción mínima de pedidos. El modelo les asigna probabilidades conservadoras por falta de historial, así que casi no los elige, y por eso no acumulan historial.
**Qué se hace:** se reconoce el bucle de retroalimentación. Se agrega una política de exploración: una fracción acotada del tráfico (con candidatos que cumplen distancia y capacidad mínimas) se asigna con aleatoriedad que favorece a quienes tienen poca información, registrando la probabilidad de selección. En la model card se agrega un segmento "transportistas con menos de 20 entregas" y un indicador de cobertura (cuántos transportistas activos tuvieron al menos N asignaciones en la semana).

### Reconstruir por qué se tomó una decisión hace un mes

**Situación:** un comercio grande reclama que un pedido de hace un mes se asignó a un transportista lejano y llegó tarde. Piden explicación.
**Qué se hace:** con el ID del pedido se busca en el registro de predicciones: versión del modelo (v13), versión de features, las features de cada candidato tal como estaban en ese instante y los puntajes. Se ve que el transportista cercano tenía 5 pedidos en curso y el modelo estimó para él una probabilidad a tiempo de 0,62 contra 0,78 del elegido. Con el artefacto de v13 del registro se pueden recalcular los valores SHAP sobre esas mismas features. Sin este registro, habría que reconstruir las features a partir de tablas que cambiaron desde entonces, con resultados poco confiables.

## Errores comunes

- **Definir la métrica de éxito después de ver los resultados.** Escribe el criterio en la model card antes de la sombra y el A/B.
- **Evaluar solo la métrica global.** Exige métricas por segmento y define tolerancias por segmento en los gates.
- **Embeber el modelo en la imagen del servicio.** Carga la versión desde el registro para que cambiar o revertir no requiera redeploy.
- **Reentrenar y promover automáticamente sin gates.** Trata cada modelo reentrenado como un cambio de producción: validación de datos, métricas por segmento, sombra.
- **Ignorar el sesgo de selección.** Si el modelo decide qué datos se observan, reserva exploración y registra probabilidades de selección.
- **No registrar las features usadas en cada predicción.** Sin ese registro no hay auditoría ni explicación posterior confiable.

## Para discutir en equipo

- ¿Qué criterio de éxito online pondríamos hoy para el próximo modelo de asignación, y con qué unidad de aleatorización?
- ¿Qué segmentos son obligatorios en la evaluación y qué tolerancia de empeoramiento aceptamos en cada uno?
- ¿Cuánto tiempo de sombra es suficiente, y qué señales nos harían abortar antes?
- ¿Cuánto tiempo conservamos el registro de predicciones, y cómo protegemos la PII que pudiera contener?
- ¿Quién puede aprobar la promoción de un modelo, y qué pasa fuera del horario laboral si hay que hacer rollback?
