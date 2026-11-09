---
slug: revision-arquitectura
titulo: Revisión de arquitectura
resumen: Cómo proponer, documentar y revisar decisiones técnicas con design docs y ADRs, haciendo explícitos requisitos, trade-offs y deuda antes de construir.
lectura: 13
---

## La idea central

Una revisión de arquitectura existe para equivocarse en papel, que es barato, en lugar de equivocarse en producción, que es caro. Mover una flecha en un diagrama cuesta minutos; migrar un sistema que ya procesa miles de pedidos por hora cuesta trimestres. El objetivo no es "aprobar" un diseño, sino sacar a la luz sus supuestos: qué números se esperan, qué se sacrifica a cambio de qué, qué pasa cuando una dependencia falla y qué decisiones van a ser difíciles de deshacer.

La segunda función es la memoria. Los sistemas viven más que los equipos que los diseñaron. Dentro de dos años alguien va a preguntar "¿por qué usamos esto?", y "lo decidió alguien que ya no está" es la semilla de muchas reescrituras innecesarias. Para eso usamos dos herramientas distintas: el **design doc** sirve para pensar y discutir antes de construir; el **ADR** registra qué se decidió y por qué, en un formato corto que sobrevive al paso del tiempo.

## Conceptos

### Design doc o RFC

Un design doc (también llamado RFC, *request for comments*) es un documento que se escribe antes de implementar y se circula para recibir comentarios. Su valor no está en la prosa sino en obligar al autor a responder preguntas incómodas antes de escribir código. Las secciones que usamos:

- **Contexto y problema:** qué duele hoy, con datos. "El 4% de los pedidos espera más de 3 minutos sin transportista" es un problema; "mejorar la asignación" no.
- **Objetivos y no-objetivos:** los no-objetivos acotan la discusión. Si el documento dice "no cambiamos el modelo de scoring", nadie gasta la revisión debatiendo el modelo.
- **Requisitos no funcionales** con números (ver más abajo).
- **Propuesta:** el diseño, con un diagrama de contenedores.
- **Alternativas consideradas:** incluida "no hacer nada". Es la sección más valiosa: un documento con una sola opción es un folleto de venta, no un análisis.
- **Trade-offs, riesgos y modos de falla.**
- **Rollout y rollback:** cómo se despliega de a poco y cómo se vuelve atrás, sobre todo si hay migración de datos.
- **Operación:** métricas, alertas, runbook, quién atiende el on-call.
- **Preguntas abiertas.**

**Ejemplo:** un design doc para "reasignar automáticamente si el transportista no acepta en 60 segundos". No-objetivo: cambiar cómo se rankean los candidatos. Alternativa descartada: bajar el tiempo de aceptación a 30 segundos, porque los datos muestran que el 18% de las aceptaciones llega entre los 30 y los 60 segundos.

```markdown
# Design doc: <título>
Autor · Revisores · Estado (borrador / en revisión / aceptado / abandonado) · Fecha

## Contexto y problema
Qué pasa hoy, con métricas. Por qué ahora.

## Objetivos / No-objetivos
- Objetivo medible 1
- No-objetivo: lo que explícitamente queda afuera

## Requisitos no funcionales
Latencia p99, throughput pico, disponibilidad, RPO/RTO, retención, PII, costo.

## Propuesta
Diagrama de contenedores. Flujo principal. Contratos nuevos o modificados.

## Alternativas consideradas
| Opción | A favor | En contra | Por qué se descarta |

## Trade-offs y riesgos
Optimizamos para X; aceptamos Y. Qué pasa si cada dependencia falla.

## Rollout y rollback
Fases, feature flags, migraciones, criterio para revertir.

## Operación
SLI/SLO, alertas, runbook, dueño.

## Deuda que asumimos
Qué, por qué, disparador para pagarla, responsable.

## Preguntas abiertas
```

### Cuándo hace falta un design doc

Si todo requiere documento, el equipo aprende a esquivar el proceso; si nada lo requiere, las decisiones grandes se toman en un hilo de chat. Un umbral razonable: hace falta design doc cuando el cambio cumple **al menos uno** de estos criterios:

- Cambia un contrato que otro equipo consume (API, esquema de evento, tabla compartida).
- Introduce tecnología nueva en el stack (una base de datos, una cola, un lenguaje).
- Es difícil de revertir (ver más abajo).
- Toca el camino crítico de latencia, un SLO o datos personales.
- Lleva más de dos o tres semanas-persona.

No hace falta para corregir bugs, refactors internos o funcionalidades dentro de un servicio que no alteran sus contratos. El tamaño del documento también escala: una página para un cambio mediano, diez para una plataforma nueva.

**Ejemplo:** agregar un campo opcional al evento `pedido_entregado` no requiere documento: alcanza con un PR que revise el esquema. Cambiar la clave de partición del tópico de pedidos sí, porque altera las garantías de orden de todos los consumidores (ver [Event streaming](#t/event-streaming)).

### ADR: Architecture Decision Record

Un ADR es un archivo corto, versionado en el repositorio junto al código (por ejemplo `docs/adr/0012-eventos-en-kinesis.md`), que registra una sola decisión: el contexto, la decisión, las consecuencias y su estado.

La regla clave es que **un ADR aceptado es inmutable**. Si la decisión cambia, no se edita el viejo: se escribe uno nuevo que lo reemplaza, y el viejo queda marcado como "reemplazado por 0031". El porqué: la decisión original probablemente era correcta en su contexto (otro volumen, otro equipo, otros precios). Editarla borra ese razonamiento y deja la impresión de que alguien se equivocó. La secuencia de ADRs cuenta la historia de cómo evolucionó el sistema y por qué.

Diferencia con el design doc: el design doc es largo, se discute y a veces se abandona; el ADR es el residuo destilado. Un design doc puede producir tres ADRs. La sección más subestimada es **Consecuencias**, en particular "cuándo revisar esta decisión".

```markdown
# ADR 0012: Usar Kinesis para eventos de pedidos
Estado: Aceptado (2025-03-10) | Reemplazado por: —

## Contexto
Dos consumidores (seguimiento y notificaciones). Nadie en el equipo opera Kafka.
Retención necesaria: 24 h. Volumen pico estimado: 300 eventos/s.

## Decisión
Kinesis Data Streams administrado, 4 shards, clave de partición = pedido_id.

## Consecuencias
+ Sin operación de brokers.
- Límite de lectura compartido por shard: más de 3-4 consumidores requiere enhanced fan-out.
- No hay instalación on-prem equivalente.
Revisar si: más de 4 consumidores, necesidad de replay mayor a 7 días,
o un cliente on-prem necesita el mismo flujo de eventos.
```

### Requisitos no funcionales con números

"Debe ser rápido, escalable y altamente disponible" no es un requisito: todos lo cumplen y nadie lo cumple. Un requisito no funcional útil tiene número, percentil y condición:

- p99 menor a 50 ms con 3.000 solicitudes por segundo en el pico.
- Disponibilidad 99,95% mensual medida en el balanceador.
- RPO de 1 minuto (cuántos datos se pueden perder) y RTO de 15 minutos (cuánto se tarda en volver).
- Crecimiento esperado: 3x en 18 meses.
- La dirección del destinatario no sale de la región y su acceso queda auditado.

Los números importan porque **eligen la arquitectura**. Un p99 de 50 ms excluye una llamada síncrona a una API externa cuyo p99 es de 200 ms. Un 99,99% obliga a eliminar puntos únicos de falla dentro de la región. En el pronóstico de demanda, en cambio, la latencia es irrelevante; el requisito es "listo antes de las 5:00 con 99% de las noches". Ver [Baja latencia y alta disponibilidad](#t/latencia-disponibilidad) para convertir estos números en presupuestos.

### Trade-offs explícitos

Todo diseño sacrifica algo. La pregunta más útil en una revisión es "¿qué empeora con esto?". Si el autor no puede responderla, todavía no entendió su propio diseño. Un formato que funciona: **optimizamos para A, aceptamos B, no nos importa C**.

**Ejemplo:** cachear en memoria del pod las features lentas del transportista (historial de puntualidad de los últimos 30 días). Optimizamos latencia: la lectura baja de ~8 ms a menos de 1 ms. Aceptamos que el dato puede estar hasta 10 minutos desactualizado y unos 200 MB extra de memoria por pod. No nos importa que dos pods vean valores levemente distintos durante esos minutos, porque la feature cambia despacio.

### Decisiones reversibles e irreversibles

Algunas decisiones son puertas de dos vías: elegir una biblioteca dentro de un servicio, el TTL de una caché, la cantidad de réplicas. Se deciden rápido, se miden y se revierten si salen mal. Otras son puertas de una vía: el contrato de una API pública, el esquema de un evento que consumen seis equipos, el almacén de datos principal, la clave de partición, borrar datos, o una versión instalada on-prem en un cliente que actualiza dos veces por año.

El esfuerzo de revisión debe ser proporcional a la irreversibilidad. El error simétrico también existe: tratar como irreversible algo que no lo es paraliza al equipo. Y hay técnicas para **convertir** una decisión irreversible en reversible: feature flags, escritura dual durante una migración, una interfaz que oculte la implementación, APIs versionadas.

**Ejemplo:** usar Redis o caché local para features es reversible si queda detrás de una interfaz `FeatureReader`. El formato de identificador de pedido de la API pública es irreversible apenas lo integran 200 comercios.

### Diagramas C4

C4 propone cuatro niveles de zoom: **Contexto** (el sistema y sus actores: comercios, transportistas, destinatarios, proveedor de mapas), **Contenedores** (unidades desplegables: API pública, servicio de asignación, modelo de ETA, Aurora, Kafka), **Componentes** (módulos dentro de un contenedor) y **Código** (rara vez vale la pena). Para una revisión casi siempre alcanzan Contexto y Contenedores.

La regla que más valor aporta: **cada flecha lleva protocolo y si es síncrona o asíncrona**. Una flecha sin etiqueta esconde lo más importante del diseño: una llamada síncrona acopla la disponibilidad y la latencia de ambos lados; un evento asíncrono no.

```text
[Comercio] --HTTPS/REST--> [API pública] --gRPC síncrono--> [Asignación (Go)]
                                                               |  gRPC síncrono, timeout 30 ms
                                                               v
                                                          [Modelo ETA (Python)]
[Asignación] --SQL--> [Aurora PostgreSQL]
[Asignación] --outbox + Kafka, asíncrono--> [Seguimiento] [Notificaciones]
```

### Deuda técnica explícita

La deuda técnica no es mala en sí misma: es una herramienta para llegar antes. Es mala cuando es accidental o invisible. La deuda explícita se registra con cinco datos: **qué** atajo se tomó, **por qué**, cuál es el **interés** (incidentes, lentitud para cambiar, costo), el **disparador** para pagarla y un **responsable**.

El disparador es lo que la hace pagable. "Algún día lo arreglamos" nunca llega; "antes de que exista un segundo servicio que escriba en la tabla de pedidos" o "cuando superemos 5.000 pedidos por minuto" se puede vigilar.

**Ejemplo:** para el lanzamiento, el servicio de asignación escribe directamente en la tabla `pedidos`, que pertenece al servicio de pedidos. Interés: cualquier cambio de esquema requiere coordinar dos equipos. Disparador: el próximo cambio de esquema en `pedidos` o el próximo servicio que necesite escribirla, lo que llegue primero.

### Checklist de revisión

Ocho preguntas que todo revisor debería poder responder al terminar de leer:

1. ¿Qué problema resuelve y con qué métrica sabremos que funcionó?
2. ¿Cuáles son los requisitos no funcionales con números, y cómo se van a validar (prueba de carga, shadow traffic)?
3. ¿Qué pasa cuando cada dependencia está lenta, no solo caída?
4. ¿Qué alternativas se descartaron, incluida no hacer nada, y por qué?
5. ¿Qué decisiones son irreversibles y qué las hace así?
6. ¿Cómo se despliega de forma gradual y cómo se revierte, incluidos los datos?
7. ¿Cómo se opera: métricas, alertas, runbook, quién recibe la alerta a las 3 de la mañana?
8. ¿Qué datos personales toca, dónde se guardan y quién puede leerlos?

## Casos prácticos

### Asignación consulta un feature store remoto de forma síncrona

**Situación:** un design doc propone que el servicio de asignación, con presupuesto de 50 ms, consulte un feature store remoto por cada transportista candidato. El p99 del feature store es de 25 ms. Con 20 candidatos en paralelo, la probabilidad de que al menos una llamada caiga en su cola lenta es alta, y el p99 total se acerca a 40 ms solo en features. Además, si el feature store se cae, la asignación se cae con él: la disponibilidad del servicio pasa a ser el producto de ambas.

**Qué se hace:** la pregunta 3 del checklist desarma la propuesta. Se rediseña con una sola lectura en lote para todos los candidatos, caché local para las features que cambian despacio, un timeout de 10 ms y valores por defecto documentados si la lectura falla (ver [Patrones de resiliencia](#t/resiliencia)). Se registra en un ADR el trade-off aceptado: features hasta 10 minutos desactualizadas a cambio de desacoplar la disponibilidad. Alternativa evaluada y dejada para más adelante: empujar las features por stream a un almacén local de cada pod (ver [Features y feature stores](#t/feature-stores)).

### Propuesta de reescribir un servicio Python en Go

**Situación:** alguien propone reescribir en Go el servicio que expone el modelo de ETA "porque Python es lento". Su p99 actual es de 35 ms. Un perfilado muestra: 22 ms de inferencia de XGBoost (que ya corre en código nativo), 8 ms de serialización JSON y 5 ms del framework web. La reescritura se estima en tres meses para dos personas.

**Qué se hace:** la revisión pide los números y las alternativas. Reescribir en Go no toca los 22 ms de inferencia: en el mejor caso ahorra unos 13 ms. Además introduce un riesgo serio: recalcular las features en Go, mientras el entrenamiento sigue en Python, abre la puerta a diferencias sutiles entre entrenamiento y serving. Alternativas baratas: pasar de JSON a gRPC con Protocol Buffers, compilar el modelo con un runtime optimizado y ajustar la cantidad de workers. Son unas dos semanas de trabajo y capturan buena parte de la mejora. El costo de oportunidad de seis meses-persona (por ejemplo, la reasignación automática que espera hace un trimestre) termina de inclinar la decisión. Se deja escrito un criterio para reabrir el tema: si el p99 sigue por encima de 25 ms después de las alternativas.

### La decisión olvidada de Kinesis vs. Kafka

**Situación:** hace 18 meses se eligió Kinesis para los eventos de pedidos. Hoy hay cuatro consumidores, el equipo de ML quiere un quinto para features en tiempo real y un cliente on-prem necesita el mismo flujo de eventos. Alguien propone migrar a Kafka. Durante dos semanas de reuniones se discute por qué se eligió Kinesis: unos creen que fue por costo, otros por latencia. Nadie lo sabe, y la discusión se trata como si el primer equipo se hubiera equivocado.

**Qué se hace:** si hubiera existido el ADR 0012 de la plantilla, la conversación habría durado una hora: el contexto original (dos consumidores, nadie para operar Kafka) ya no aplica, y dos de las tres condiciones de revisión se cumplen. La decisión original fue correcta en su momento y la nueva también lo es. Se escribe el ADR 0031, "Migrar eventos de pedidos a Kafka (MSK)", que reemplaza al 0012, y como práctica se acuerda que toda elección de tecnología de infraestructura lleve ADR con su sección "Revisar si".

## Errores comunes

- **Un design doc con una sola opción.** Sin alternativas no hay análisis; exige al menos dos más "no hacer nada", con el motivo concreto del descarte.
- **Requisitos sin números.** "Alta disponibilidad" no guía ninguna decisión; pide percentil, umbral y condición de carga.
- **Revisar todo con el mismo rigor.** Gastar una semana en elegir una biblioteca reversible y diez minutos en el esquema de un evento público invierte las prioridades.
- **Editar ADRs aceptados.** Se pierde el razonamiento original; se escribe uno nuevo que reemplaza al anterior.
- **Diagramas con flechas sin etiquetar.** Sin protocolo ni sincronía, nadie puede razonar sobre latencia o propagación de fallas.
- **Escribir el documento después de construir.** La revisión se vuelve un trámite y los problemas que encuentra ya cuestan caro de arreglar.

## Para discutir en equipo

- ¿Qué decisión de nuestro sistema actual nadie sabe explicar, y cuánto nos costaría reconstruir su contexto hoy?
- ¿Nuestro umbral para exigir design doc es demasiado alto o demasiado bajo? ¿Qué cambio reciente debería haber tenido uno?
- ¿Qué decisión que tratamos como irreversible podríamos volver reversible con un flag o una interfaz?
- ¿Qué deuda técnica tenemos hoy sin disparador explícito, y cuál sería un disparador razonable?
- ¿Cómo evitamos que la revisión de arquitectura se convierta en un cuello de botella para equipos pequeños?
