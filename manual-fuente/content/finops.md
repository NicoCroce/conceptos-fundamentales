---
slug: finops
titulo: Costos cloud (FinOps)
resumen: Práctica para entender, atribuir y optimizar el gasto en la nube midiendo costo unitario, con dueños claros y decisiones que equilibran costo y confiabilidad.
lectura: 12
---

## La idea central

En la nube cualquier ingeniero puede crear en un minuto un recurso que cuesta miles de dólares por mes. Eso es una ventaja enorme (nadie espera semanas para comprar servidores) y un riesgo igual de grande: el gasto se decide en cientos de pequeñas decisiones técnicas distribuidas en el equipo, no en una oficina de compras. **FinOps** es la práctica de hacer visible ese gasto, asignarle dueños y tomar decisiones informadas de costo, con la misma naturalidad con la que miramos latencia o errores.

La pregunta clave de FinOps no es "¿cuánto gastamos?", sino "¿cuánto nos cuesta producir una unidad de valor, y va mejorando?". Si la factura de Rumbo sube 40 % pero los pedidos subieron 60 %, el equipo está siendo más eficiente, no menos. Una analogía: en una flota de camiones, el gasto total en combustible no dice nada si no sabes cuántos kilómetros se recorrieron; lo que importa son los litros por kilómetro.

## Conceptos

### Qué es FinOps

FinOps combina tres cosas:

1. **Visibilidad:** saber en qué se gasta, con el detalle suficiente para que cada equipo vea su parte (por servicio, entorno y producto).
2. **Optimización:** aplicar palancas técnicas y comerciales para gastar menos por unidad de valor.
3. **Operación continua:** presupuestos, alertas, revisiones periódicas y costo como criterio de diseño, no como auditoría anual.

No es un equipo que dice "no" a todo. Es un ciclo en el que los ingenieros, que son quienes toman las decisiones que generan costo, tienen la información para decidir bien.

**Por qué importa:** en equipos de AI/ML el gasto crece rápido (GPUs, tokens de LLM, datos) y sin visibilidad se descubre tarde, cuando ya se gastó.

### Etiquetado y dueños del costo

Para atribuir costos, cada recurso lleva **etiquetas** (tags) con metadatos: `servicio=asignacion`, `equipo=ml-plataforma`, `entorno=prod`, `producto=eta`. AWS Cost Explorer y los reportes de costo permiten agrupar el gasto por esas etiquetas.

Pasos para que funcione:

1. Definir un conjunto mínimo de etiquetas obligatorias (cuatro o cinco, no veinte).
2. Imponerlas en Terraform con etiquetas por defecto del proveedor y validaciones en CI que rechazan recursos sin ellas (ver [Terraform](#t/terraform)).
3. Activarlas como "etiquetas de asignación de costos" en la cuenta.
4. Repartir los costos compartidos (el clúster de EKS, el NAT Gateway) con una regla explícita: por ejemplo, por CPU solicitada de cada servicio, usando herramientas que leen las métricas de Kubernetes.
5. Asignar un **dueño** a cada etiqueta `servicio`: una persona o equipo que recibe el reporte y las alertas.

**Ejemplo:** si el 30 % del gasto aparece como "sin etiqueta", nadie es responsable de ese 30 %. Una meta razonable es menos del 5 % sin atribuir.

### Costo unitario

El **costo unitario** divide el gasto por una métrica de negocio. En Rumbo usamos dos:

- **Costo por pedido** (o por 1.000 pedidos): todo el gasto de la plataforma dividido por los pedidos procesados.
- **Costo por 1.000 inferencias:** el gasto del serving del modelo de ETA dividido por las predicciones servidas. Como el servicio de asignación consulta el modelo para varios transportistas por pedido, esta métrica sigue la eficiencia del serving en sí.

Tabla de ejemplo, con números hipotéticos:

| Mes | Costo cloud total (USD) | Pedidos | Costo por 1.000 pedidos (USD) | Comentario |
|---|---|---|---|---|
| Junio | 100.000 | 4.000.000 | 25,00 | Línea base |
| Julio | 104.000 | 4.300.000 | 24,19 | Crecimiento normal |
| Agosto | 118.000 | 4.400.000 | 26,82 | Anomalía: GPUs encendidas sin uso |
| Septiembre | 112.000 | 5.000.000 | 22,40 | Rightsizing de Aurora y Savings Plan |
| Octubre | 126.000 | 5.800.000 | 21,72 | Temporada alta |
| Noviembre | 140.000 | 6.400.000 | 21,88 | Nuevo cliente grande |

El total subió 40 % de junio a noviembre, pero el costo por 1.000 pedidos bajó 12,5 %. Agosto se destaca porque el costo unitario subió sin un cambio de volumen que lo explique: esa es la señal que hay que investigar.

**Por qué importa:** el total sube cuando el negocio crece y eso está bien. El costo unitario separa el crecimiento sano del desperdicio, y permite prever cuánto costará un cliente nuevo de 500.000 pedidos mensuales.

### Impulsores de costo en AI/ML

En un equipo de AI/ML y plataforma, el gasto suele concentrarse en:

- **GPUs:** una instancia con GPU puede costar diez o veinte veces más por hora que una de CPU. Entrenamientos que quedan encendidos, notebooks olvidados y servidores de inferencia sobredimensionados son la fuente más habitual de desperdicio.
- **Tokens de LLM:** el asistente de soporte se factura por token de entrada y de salida. Un prompt de sistema largo con muchos fragmentos de RAG multiplica el costo de cada consulta (ver [LLMs en producción](#t/llms-produccion)).
- **Almacenamiento:** datasets duplicados, versiones viejas en S3, snapshots que nadie borra.
- **Transferencia de datos:** tráfico entre zonas de disponibilidad, entre regiones y hacia internet; también el procesamiento del NAT Gateway.
- **Logs:** ingestión e indexación de logs muy verbosos. No es raro que la observabilidad cueste tanto como los servicios que observa.
- **Bases sobredimensionadas:** una instancia de Aurora elegida "por si acaso" para un pico que nunca llegó.

**Ejemplo:** el asistente procesa 200.000 consultas al mes con un prompt de 6.000 tokens de entrada y 400 de salida. Con precios hipotéticos de 3 USD por millón de tokens de entrada y 15 USD por millón de salida, son 3.600 + 1.200 = 4.800 USD al mes. Reducir el contexto recuperado a 3.000 tokens baja ese número a unos 3.000 USD sin tocar el modelo.

### Palancas de optimización

Las palancas más comunes, de menor a mayor esfuerzo:

1. **Apagar entornos fuera de horario:** staging y desarrollo no necesitan correr de noche ni el fin de semana. Encendidos 12 horas en días hábiles, pasan de 168 a 60 horas semanales: un 64 % menos.
2. **Rightsizing:** ajustar el tamaño de instancias y requests de pods a lo que realmente usan. Si un servicio pide 4 CPU y usa 0,5 en el percentil 95, sobra capacidad.
3. **Autoescalado:** que la capacidad siga a la demanda (más pods en la hora pico, menos de madrugada) en lugar de dimensionar todo para el pico.
4. **Ciclo de vida en S3:** mover datos fríos a clases baratas y expirar lo que ya no sirve (ver [S3](#t/s3)).
5. **Graviton:** instancias con procesadores ARM de AWS, con mejor relación precio-rendimiento para muchos servicios. Requiere imágenes multi-arquitectura; un servicio en Go suele migrar con poco esfuerzo.
6. **Savings Plans:** compromiso de gasto por hora durante uno o tres años a cambio de un descuento significativo. Conviene sobre la base estable de uso, nunca sobre el pico.
7. **Spot con checkpoints:** capacidad sobrante de AWS con grandes descuentos, que AWS puede reclamar con dos minutos de aviso. Ideal para entrenamientos y batch (como el pronóstico de demanda), siempre que el job guarde checkpoints y pueda retomar donde quedó.
8. **En LLMs, caché y modelos chicos:** cachear respuestas o prefijos de prompt repetidos, y derivar las tareas simples (clasificar un ticket) a un modelo más chico y barato, reservando el grande para resumir casos complejos.

**Ejemplo:** un reentrenamiento de 10 horas en GPU con precio hipotético de 4 USD por hora cuesta 40 USD on-demand. En Spot con un descuento del 70 %, unos 12 USD; si se interrumpe dos veces y el checkpoint cada 30 minutos hace perder como mucho una hora en total, sigue saliendo menos de la mitad.

### Presupuestos y detección de anomalías

Un **presupuesto** (AWS Budgets) define un umbral de gasto por cuenta, servicio o etiqueta y avisa cuando el gasto real o el pronosticado lo supera. La **detección de anomalías** (Cost Anomaly Detection) aprende el patrón habitual y alerta ante desvíos, aunque no se haya superado ningún presupuesto.

Para que sirvan:

- Las alertas van al dueño del costo, no a un buzón genérico.
- Se revisan a diario o casi: un desvío de 500 USD por día descubierto a fin de mes ya costó 15.000.
- Se complementan con alertas propias en el sistema de métricas para lo que más varía: horas de GPU encendidas, tokens por hora del gateway de LLM.

### Costo dentro de las estimaciones

Cuando el equipo estima una funcionalidad, también estima su costo de operación. No hace falta precisión contable: alcanza con orden de magnitud y el impacto en el costo unitario.

**Ejemplo:** agregar un resumen automático con LLM a cada ticket. 300.000 tickets al mes, unos 2.000 tokens por resumen, precio hipotético combinado de 5 USD por millón de tokens: 3.000 USD al mes, unos 0,5 USD por cada 1.000 pedidos. Con ese número, el producto decide si el beneficio lo justifica o si conviene resumir solo los tickets escalados.

### Costo vs. confiabilidad

Muchas decisiones de confiabilidad cuestan: réplicas en varias zonas, capacidad de reserva, multi-región. FinOps no busca minimizar el costo a cualquier precio, sino que cada gasto en confiabilidad responda a un objetivo explícito (un SLO) y no a un miedo genérico (ver [Baja latencia y alta disponibilidad](#t/latencia-disponibilidad)). Del mismo modo, una optimización que pone en riesgo el SLO (por ejemplo, el servicio de asignación en Spot sin margen) no es un ahorro, es un riesgo trasladado.

## Casos prácticos

### El costo sube 40 % pero los pedidos subieron 60 %

**Situación:** en la revisión trimestral, alguien señala que la factura de AWS pasó de 100.000 a 140.000 USD mensuales y pide recortes urgentes.

**Qué se hace:** se muestra el costo unitario: de 25,00 a 21,88 USD por cada 1.000 pedidos, una mejora del 12,5 %. La plataforma escala mejor que el negocio. En lugar de recortes generales, se miran los componentes cuyo costo unitario empeoró (por ejemplo, logs por pedido) y se fija como objetivo de equipo el costo por 1.000 pedidos, no el total. Así se evita frenar el crecimiento por una métrica mal elegida.

### GPUs encendidas todo el fin de semana

**Situación:** el lunes llega una alerta de anomalía: el gasto en EC2 del fin de semana fue cinco veces el habitual. Un experimento lanzó un grupo de 8 instancias con GPU el viernes a la tarde, el job falló a la hora y las instancias quedaron ociosas 60 horas.

**Qué se hace:** se apagan y se calcula el impacto (8 instancias por 60 horas por un precio hipotético de 30 USD la hora: unos 14.000 USD). Se corrigen las causas, no a la persona: los jobs de entrenamiento corren en un orquestador que libera los nodos al terminar o fallar; los nodos de GPU del clúster escalan a cero sin carga; una alerta avisa si hay GPUs con utilización menor a 5 % por más de una hora; y las cuentas de experimentación tienen un presupuesto con aviso diario.

### Factura de LLM sin dueño descubierta por etiquetas en el gateway

**Situación:** la factura del proveedor de LLM se triplicó en dos meses y aparece como una sola línea. Nadie sabe qué la generó.

**Qué se hace:** como todo el tráfico pasa por el gateway de LLM, se exige que cada llamada lleve encabezados con `servicio`, `equipo` y `caso_de_uso`, y el gateway registra tokens de entrada y salida por cada etiqueta. En una semana aparece la respuesta: el agente interno de operaciones, en un bucle de reintentos, enviaba el historial completo de la conversación en cada paso; representaba el 55 % del consumo. Se le asigna dueño, un límite de tokens por investigación y una alerta. Las llamadas sin etiquetas se rechazan.

### Propuesta de multi-región activa-activa

**Situación:** después de una caída de una zona de disponibilidad, se propone correr Rumbo en dos regiones activas a la vez para "no caernos nunca".

**Qué se hace:** se estima el costo: duplicar cómputo, replicar Aurora entre regiones (Aurora Global Database), pagar transferencia entre regiones por cada evento de Kafka replicado y la complejidad de resolver conflictos de escritura. Orden de magnitud: el costo de infraestructura sube entre 60 % y 100 %, más el esfuerzo de ingeniería. Se compara con el SLO real (99,9 % mensual) y con el historial: la caída fue de una zona, y la arquitectura multi-zona ya la absorbió con degradación parcial. La decisión razonable es reforzar el diseño multi-zona y tener una recuperación en otra región con backups y Terraform probados (activa-pasiva fría), mucho más barata, y revisar la decisión si el SLO o los contratos cambian.

## Errores comunes

- **Mirar solo el total.** El total sube con el negocio; mide costo unitario para distinguir crecimiento de desperdicio.
- **Etiquetado opcional.** Sin etiquetas obligatorias impuestas en CI, el gasto sin dueño crece; rechaza recursos sin etiquetas.
- **Comprar Savings Plans sobre el pico.** El compromiso se paga aunque no se use; dimensiónalo sobre el piso estable de los últimos meses.
- **Spot sin checkpoints.** Una interrupción hace perder horas de entrenamiento; guarda estado con frecuencia y diseña el job para retomar.
- **Optimizar lo chico.** Discutir 50 USD de un bucket mientras una base sobredimensionada cuesta 8.000; ordena por impacto antes de actuar.
- **Recortar a costa del SLO.** Quitar réplicas o margen sin mirar los objetivos de confiabilidad traslada el costo a un incidente.

## Para discutir en equipo

- ¿Cuál es nuestro costo por 1.000 pedidos hoy y cómo se reparte entre cómputo, datos, observabilidad y LLMs?
- ¿Qué porcentaje del gasto no tiene dueño y qué haría falta para bajarlo a menos del 5 %?
- ¿Qué cargas podrían pasar a Spot o Graviton este trimestre, y qué riesgo tiene cada una?
- ¿Cómo incorporamos el costo de operación en las revisiones de diseño sin volverlas lentas?
- ¿Qué nivel de disponibilidad necesitamos de verdad, y cuánto estamos dispuestos a gastar por cada nueve adicional?
