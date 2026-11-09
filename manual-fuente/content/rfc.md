---
slug: rfc
titulo: RFC: propuestas técnicas por escrito
resumen: Un documento que propone un cambio técnico, compara alternativas y abre un período de comentarios con fecha antes de decidir y construir.
lectura: 13
---

## La idea central

Un **RFC** (*request for comments*, pedido de comentarios) es una propuesta técnica escrita que se circula para que otras personas la critiquen antes de construir. El nombre viene de los documentos con que la comunidad de internet, hoy a través de la IETF, define sus protocolos desde 1969. En ingeniería se usa casi como sinónimo de *design doc*: alguien escribe "quiero hacer esto, así, por estas razones; estas son las otras opciones", y el resto tiene un plazo para responder.

El valor no está en el documento sino en la conversación que provoca. Un RFC bien usado convierte diez reuniones sin memoria en un hilo escrito donde los argumentos quedan a la vista y los ausentes pueden opinar. Las secciones de un design doc y el registro de decisiones con ADRs se tratan en [Revisión de arquitectura](#t/revision-arquitectura); este tema se concentra en **cómo se escribe, se discute y se cierra** una propuesta, y en qué cambia cuando lo que se decide es cómo se comporta un agente.

## Conceptos

### Qué es y qué no es un RFC

Un RFC tiene tres rasgos:

1. **Propone algo concreto.** No es un ensayo sobre un tema; termina en "proponemos X".
2. **Pide comentarios con plazo.** Tiene revisores nombrados y una fecha de cierre.
3. **Termina en una decisión.** Aceptado, rechazado o reemplazado, nunca "quedó ahí".

No es un [PRD](#t/prd), que dice qué problema resolver y cómo medir el éxito; el RFC dice cómo resolverlo técnicamente. Tampoco es un ADR: el RFC es la discusión; el ADR, el registro corto de lo decidido.

**Ejemplo:** el PRD del asistente para transportistas fija un techo de costo por conversación. El RFC "Introducir un gateway de LLM interno" propone cómo controlarlo en todos los productos con LLM de Rumbo. Al cerrarse, deja dos ADRs: "todo acceso a modelos pasa por el gateway" y "presupuesto por clave de servicio".

**Por qué importa:** mezclar los tres documentos produce RFCs que debaten el problema de producto y PRDs que eligen bases de datos.

### Cuándo escribir uno y cuándo no

Un RFC cuesta horas de escritura y de lectura. Se justifica si el cambio cumple al menos una de estas condiciones:

- **Impacto entre equipos:** cambia un contrato, una herramienta compartida o la forma de trabajar de otros.
- **Difícil de revertir:** esquemas de datos, formatos públicos, proveedores con contratos largos.
- **Dependencia nueva:** una base de datos, un servicio externo, un proveedor de modelos.
- **Implicancias de seguridad o privacidad:** datos personales, permisos, superficie de ataque nueva.

No hace falta para un cambio interno que no altera contratos, una corrección o un experimento descartable. Ante la duda: si dos personas razonables podrían elegir distinto y equivocarse sale caro, conviene escribirlo.

**Ejemplo:** cambiar el modelo que usa el clasificador de tickets por otra versión del mismo proveedor, con su evaluación, no requiere RFC. Permitir que el agente de operaciones ejecute acciones de escritura (reiniciar un consumidor de Kafka) sí: es una superficie de riesgo nueva y afecta a on-call.

**Por qué importa:** exigir RFC para todo enseña a esquivarlo; no exigirlo nunca deja las decisiones grandes en un chat.

### Estructura: qué responde cada sección

Más que la lista de secciones, importa la pregunta que obliga a responder cada una:

| Sección | Pregunta que obliga a responder |
|---|---|
| Contexto y problema | ¿Por qué ahora, y qué pasa si no hacemos nada? |
| Metas y no-metas | ¿Qué queda fuera de esta discusión? |
| Propuesta | ¿Qué cambia exactamente y en qué contratos? |
| Alternativas | ¿Qué otras opciones serias hay y por qué perdieron? |
| Riesgos | ¿Qué puede salir mal y cómo lo veríamos? |
| Rollout y migración | ¿Cómo se llega del estado actual al nuevo sin cortar el servicio, y cómo se vuelve? |
| Observabilidad | ¿Qué métrica o traza dice que funciona? |
| Seguridad y privacidad | ¿Qué datos o permisos nuevos aparecen? |
| Preguntas abiertas | ¿Qué no sabemos todavía y quién lo averigua? |
| Decisión | ¿Qué se decidió, quién, cuándo y con qué condiciones? |

**Ejemplo:** la sección **Decisión** queda vacía en el borrador y se completa al cerrar: "Aceptado el 21/4 por el tech lead de plataforma, con alerta obligatoria en el modo de paso directo".

**Por qué importa:** una sección que no responde su pregunta es relleno; un RFC aceptado sin Decisión escrita obliga a reconstruirla desde los comentarios.

### Alternativas consideradas

Es la sección que separa una propuesta de una justificación. Se exigen **al menos dos alternativas reales además de la propuesta**, y conviene incluir "no hacer nada" como línea de base. Cada una se describe con la misma honestidad que la elegida: qué gana, qué pierde, cuánto cuesta y por qué se descarta.

Un truco útil: escribirlas como si las defendiera otra persona; si una opción descartada no convencería a nadie, está caricaturizada.

**Ejemplo:** para controlar costo y acceso a modelos en Rumbo:

| Opción | A favor | En contra | Esfuerzo (hipotético) |
|---|---|---|---|
| A. Gateway interno propio | Control total de cuotas, redacción de PII y registro | Hay que operarlo; un punto más en el camino crítico | 6 semanas-persona |
| B. Biblioteca compartida en cada servicio | Sin salto de red extra | Cuotas imposibles de aplicar entre servicios; actualizar requiere desplegar todos | 3 semanas-persona |
| C. Gateway gestionado del proveedor de nube | Sin operar infraestructura | Ata a un proveedor; no funciona en instalaciones on-prem | 2 semanas-persona |
| D. No hacer nada | Cero esfuerzo | El costo sigue sin techo; cada equipo redacta PII a su manera | 0 |

**Por qué importa:** los revisores confían en la propuesta cuando ven que el autor entendió las opciones que perdieron.

### Plantilla compacta con un ejemplo

```markdown
# RFC-014: Gateway de LLM interno
Autor: plataforma de IA · Revisores: asistente, operaciones, seguridad, FinOps
Estado: en revisión · Comentarios hasta: 2026-04-18 · Reunión: 2026-04-21

## Contexto y problema
Tres servicios llaman a dos proveedores de modelos con claves propias.
Nadie ve el gasto por producto; dos incidentes de PII en registros de prompts.

## Metas / No-metas
- Meta: un único punto con cuotas por servicio, redacción de PII y trazas.
- No-meta: elegir proveedor ni cambiar prompts de los productos.

## Propuesta
Servicio en EKS con API compatible con la del proveedor principal.
Clave interna por servicio -> cuota diaria de tokens y modelos permitidos.
Redacción de PII antes de enviar y de registrar.

## Alternativas consideradas
B. Biblioteca compartida: sin cuotas globales.
C. Gateway gestionado: no sirve on-prem.
D. No hacer nada: costo sin techo.

## Riesgos
Latencia extra (objetivo < 15 ms p99). Punto único de falla:
2 réplicas por zona y modo de paso directo con flag de emergencia.

## Rollout y migración
1) Asistente de soporte en modo sombra. 2) Clasificador de tickets.
3) Agente de operaciones. Rollback: variable de entorno por servicio.

## Observabilidad / Seguridad
Tokens y latencia por servicio; alerta al 80% de la cuota.
Claves de proveedor solo en el gateway; prompts redactados, 30 días.

## Preguntas abiertas
- ¿Cuota dura (rechaza) o blanda (avisa) en el asistente? (dueño: producto)

## Decisión
(se completa al cerrar)
```

**Ejemplo:** el encabezado ya trae fecha de cierre de comentarios y de reunión; las alternativas se resumen en una línea porque la tabla completa vive en un anexo.

**Por qué importa:** una plantilla corta baja el costo de escribir RFCs y hace que todos se lean igual.

### El proceso: del borrador a la decisión

Un RFC sin proceso se queda en "en revisión" para siempre. Un ciclo simple:

1. **Borrador.** El autor lo comparte con una o dos personas para pulir lo obvio.
2. **Período de comentarios con fecha límite.** Revisores nombrados y un plazo de una o dos semanas. El plazo convierte "lo leo cuando pueda" en una prioridad.
3. **Reunión de revisión.** Solo para lo que no se resolvió por escrito; no repasa el documento.
4. **Decisión registrada.** Decide alguien con autoridad definida de antemano. La sección Decisión se completa y las decisiones de arquitectura pasan a ADRs, siguiendo [Revisión de arquitectura](#t/revision-arquitectura).
5. **Estado.** Cada RFC tiene uno visible: borrador, en revisión, aceptado, rechazado o reemplazado (con enlace al RFC que lo reemplaza).

```gantt
titulo: Ciclo del RFC-014
unidad: día
Borrador y revisión previa | 0 | 3
Período de comentarios | 3 | 8 | critica
Reunión de revisión | 11 | 1 | critica
Hito: decisión y ADRs | 12 | 0 | critica
```

**Ejemplo:** el RFC-014 recibe 46 comentarios en ocho días y 40 se resuelven por escrito. La reunión de 45 minutos trata tres puntos y el RFC se acepta con una condición: activar el modo de paso directo dispara una alerta en on-call.

**Por qué importa:** "rechazado" también es un resultado valioso. Un RFC rechazado con sus motivos evita que la misma idea se discuta otra vez dentro de seis meses.

### Comentar bien un RFC

Las reglas de [Feedback en revisiones](#t/feedback-revisiones) aplican igual: comentarios específicos, con motivo y con severidad marcada. En un RFC se suman tres hábitos:

- **Comentar el problema antes que la solución.** Si el problema está mal planteado, discutir la propuesta es tiempo perdido.
- **Distinguir objeción de preferencia.** "Bloqueante: no hay forma de volver atrás si el gateway falla" no pesa lo mismo que "preferiría otro lenguaje".
- **Proponer, no solo objetar.** "Esto no escala" ayuda poco; una pregunta con números se puede responder.

El autor responde cada comentario, aunque sea con "fuera de alcance, anotado en preguntas abiertas".

**Ejemplo:** "issue (bloqueante): con 300 solicitudes por segundo y 2 réplicas, ¿alcanza la memoria para redactar PII en prompts de 8.000 tokens? Sugiero una prueba de carga antes de la reunión".

**Por qué importa:** un comentario con números y propuesta se resuelve por escrito y no consume la reunión.

### Evitar el teatro del RFC

Se llama **teatro del RFC** al proceso que tiene la forma de una discusión pero no su función. Tres variantes frecuentes:

- **Demasiado largo.** Un documento de 25 páginas no se lee; se aprueba. Si supera las 6 a 8 páginas, se parte o se mueven los detalles a anexos.
- **Decidido de antemano.** El código ya está escrito o el contrato ya está firmado y el RFC se publica "para cumplir". Si la decisión ya está tomada, es más honesto escribir un ADR y explicar por qué no hubo discusión.
- **Sin fecha límite.** El RFC queda abierto meses; la decisión se toma de hecho en un PR y el documento queda desactualizado.

**Ejemplo:** un RFC para cambiar de proveedor de modelos se publica dos días después de que el equipo ya migró el asistente en staging. Los comentarios son pocos y superficiales. Desde entonces el RFC se publica antes de cualquier trabajo de más de un día, con prototipos explícitamente descartables.

**Por qué importa:** cada RFC teatral enseña al equipo que comentar no sirve, y el próximo RFC importante recibe silencio.

### RFCs para decisiones sobre agentes

Las decisiones sobre agentes mezclan impacto entre equipos, seguridad y dificultad para revertir. Tres conviene discutirlas por escrito:

- **Nivel de autonomía:** si el agente solo sugiere, actúa con aprobación humana o actúa solo dentro de límites. Pasar de un nivel a otro es un cambio de riesgo, no un ajuste de prompt.
- **Permisos de herramientas:** qué herramientas ve, cuáles escriben, con qué identidad se ejecutan y qué límites tienen (por ejemplo, máximo 5 reinicios de consumidores por hora).
- **Proveedor y modelo:** datos que salen de la red, compatibilidad on-prem, plan si el proveedor retira la versión.

**Ejemplo:** el RFC "Agente de operaciones con acciones de escritura" propone pasar de solo lectura a una herramienta `reiniciar_consumidor` con aprobación de la persona de guardia. Las alternativas: seguir en solo lectura con un runbook sugerido por el agente, o escritura sin aprobación limitada a staging. La sección de seguridad describe qué pasa si una alerta con texto malicioso intenta inducir reinicios.

**Por qué importa:** un cambio de autonomía puede ser un PR de diez líneas con el riesgo de un sistema nuevo.

### Un LLM para estresar el RFC y resumir la discusión

Un LLM ayuda al autor y a los revisores en tres tareas:

- **Generar contraargumentos.** Que actúe como el revisor más escéptico de cada área (operaciones, seguridad, costos) y liste objeciones con severidad. Muchas serán obvias; dos o tres suelen ser útiles.
- **Buscar modos de falla.** "Lista diez formas en que este diseño falla en producción y qué sección debería cubrirlas". Es una lista de verificación, no una verdad.
- **Resumir hilos largos.** Un resumen por tema, separando resueltos, abiertos y bloqueantes, acelera la reunión. Lo valida el autor: un LLM puede presentar como consenso una sola opinión.

El LLM no reemplaza a los revisores nombrados: no conoce los incidentes pasados ni las tensiones entre equipos, y su aprobación no cuenta como revisión.

**Ejemplo:** sobre el RFC-014, el LLM señala que si el gateway redacta direcciones antes de enviar, el asistente ya no puede responder "¿a qué dirección voy?". El autor agrega una lista de campos permitidos por servicio.

**Por qué importa:** encontrar ese hueco en el documento cuesta un párrafo; encontrarlo en el piloto, una semana.

### El RFC como contexto para agentes de código

Un RFC aceptado es contexto valioso para un agente de código que implementa el cambio: explica las restricciones, las alternativas descartadas y los no-objetivos. Entregarlo junto con la especificación evita que el agente "mejore" el diseño volviendo a una opción que ya se rechazó.

No conviene usarlo como especificación directa: es amplio y tiene secciones de debate. De él se derivan especificaciones acotadas con criterios de aceptación, como en [SDD](#t/sdd).

**Ejemplo:** al implementar el gateway, el agente de código recibe la especificación de la tarea "cuotas por servicio" y el RFC-014 como referencia. Cuando propone agregar una caché de respuestas "para ahorrar tokens", el revisor señala que la retención de prompts tiene límites de privacidad en el RFC.

**Por qué importa:** el agente no estuvo en la discusión; lo que el RFC no le cuenta, lo puede deshacer.

## Casos prácticos

### Un RFC que nadie comentaba

**Situación:** el RFC del gateway lleva tres semanas publicado con dos comentarios; los equipos consumidores "no tuvieron tiempo".

**Qué se hace:** se reabre con un revisor nombrado por equipo, fecha límite a ocho días y, arriba de todo, las tres preguntas donde se necesita opinión. Cada equipo debe dejar un comentario explícito, aunque sea "sin objeciones". En la nueva ronda, operaciones detecta que el modo de paso directo no tenía alerta.

### Una alternativa descartada que volvió

**Situación:** seis meses después, un equipo nuevo propone "una biblioteca compartida en lugar del gateway, para ahorrar latencia", y la discusión empieza de cero.

**Qué se hace:** se enlaza el RFC-014 y su ADR, donde la opción B figura descartada por no permitir cuotas globales. El equipo nuevo aporta un dato que no existía: la latencia extra medida es de 22 ms en el p99, por encima del objetivo de 15. En lugar de reabrir todo, se escribe un RFC chico para optimizar el gateway.

### Subir la autonomía del agente sin RFC

**Situación:** un ingeniero agrega al agente de operaciones la herramienta `reiniciar_consumidor` en un PR pequeño, "porque el runbook siempre dice lo mismo". Nadie lo ve como cambio de riesgo.

**Qué se hace:** seguridad lo detecta al auditar las herramientas y se revierte el despliegue. Se escribe el RFC con las tres opciones de autonomía y se acepta la variante con aprobación de la persona de guardia. El equipo agrega una regla: todo cambio en permisos de herramientas de un agente requiere RFC, aunque el código sea de diez líneas.

## Errores comunes

- **Una sola opción.** Sin alternativas reales, el RFC es un anuncio; se exigen al menos dos más "no hacer nada", descritas con honestidad.
- **Sin fecha ni revisores.** El RFC queda abierto indefinidamente; se publica con plazo y nombres.
- **No registrar la decisión.** La sección Decisión y los ADRs se completan al cerrar; si no, nadie sabe qué se acordó.
- **Tratar cambios de permisos de agentes como cambios menores.** Autonomía y herramientas son decisiones de riesgo y merecen discusión escrita.
- **Aceptar el resumen del LLM sin verificarlo.** El autor confirma que los acuerdos y los bloqueantes resumidos coinciden con el hilo real.

## Para discutir en equipo

- ¿Qué decisión de los últimos meses se tomó en una reunión o un chat y merecía un RFC?
- ¿Quién decide cuando un RFC no llega a consenso, y está escrito en algún lado?
- ¿Qué cambios en nuestros agentes deberían exigir RFC sin excepción?
- ¿Cuántos RFCs nuestros están en "en revisión" hace más de un mes, y qué hacemos con ellos?
- ¿Probaríamos un LLM como revisor escéptico antes de publicar? ¿Cómo sabríamos si encuentra algo útil?
