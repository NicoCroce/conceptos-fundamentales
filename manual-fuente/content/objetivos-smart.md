---
slug: objetivos-smart
titulo: Objetivos SMART
resumen: Cómo escribir objetivos específicos, medibles, alcanzables, relevantes y con fecha, para equipos, personas y funcionalidades con LLMs y agentes.
lectura: 11
---

## La idea central

"Mejorar el asistente" no es un objetivo: es una dirección. Nadie puede decir si se cumplió, cuándo, ni cuánto falta. Un objetivo útil permite que dos personas, mirando los mismos datos, coincidan en si se logró. **SMART** es una lista de control para lograrlo: un objetivo debe ser **específico** (*Specific*), **medible** (*Measurable*), **alcanzable** (*Achievable*), **relevante** (*Relevant*) y **con fecha** (*Time-bound*).

Es un filtro, y su valor está en las preguntas que obliga a hacer: ¿qué cambia exactamente?, ¿con qué número lo vemos?, ¿es realista?, ¿a quién le importa?, ¿para cuándo? En equipos que trabajan con LLMs y agentes, esas preguntas son todavía más necesarias, porque "funciona bien" es especialmente difícil de definir cuando el sistema responde distinto cada vez.

## Conceptos

### Las cinco letras, una por una

Vamos a tomar un objetivo vago de Rumbo y reescribirlo letra por letra: **"Mejorar las ETAs"**.

**S, específico.** Dice qué cambia, en qué sistema y para quién. "Mejorar las ETAs" puede significar más precisión, menos latencia o mejor comunicación al destinatario. Versión específica: "Reducir el error de la ETA que ve el destinatario en la zona norte".

**M, medible.** Tiene una métrica, un valor de partida y un valor objetivo. Sin el valor de partida no se sabe si el objetivo es ambicioso o trivial. Versión medible: "Reducir el error absoluto medio de la ETA en la zona norte de 14 a 9 minutos".

**A, alcanzable.** Es posible con los recursos y el tiempo disponibles. Se apoya en algún dato: un piloto, una referencia de otra zona, una estimación del equipo. Si la zona sur ya está en 8 minutos con el mismo modelo y mejores features de tráfico, llegar a 9 en la zona norte es exigente pero creíble.

**R, relevante.** Conecta con algo que importa más allá del equipo. Las ETAs erróneas generan ausencias del destinatario, que son el primer motivo de entregas fallidas (ver [Principio de Pareto](#t/pareto)). Un objetivo relevante explica esa conexión en una línea.

**T, con fecha.** Tiene un plazo y, si conviene, puntos de control intermedios. "Antes del 31 de marzo, medido sobre las entregas de las últimas cuatro semanas".

**Ejemplo:** el objetivo final queda así: "Reducir el error absoluto medio de la ETA en la zona norte de 14 a 9 minutos antes del 31 de marzo, medido sobre las últimas cuatro semanas, para bajar las entregas fallidas por destinatario ausente".

**Por qué importa:** con la versión vaga, en marzo cualquier resultado puede presentarse como éxito. Con la versión SMART, el equipo sabe en enero si va bien encaminado.

### De vago a SMART: ejemplos

| Vago | SMART |
|---|---|
| Mejorar la calidad del asistente | Subir la precisión del asistente en el golden set de 82% a 90% antes del fin del segundo trimestre, con costo por conversación menor a USD 0,04 (hipotético) |
| Que la asignación sea más rápida | Bajar el p99 de latencia del servicio de asignación de 70 a 45 ms antes del 30 de abril, sin aumentar la tasa de pedidos sin asignar |
| Reducir alertas | Pasar de 40 a menos de 10 alertas semanales fuera de horario en 8 semanas, con al menos 70% accionables |
| Adoptar agentes de código | Que el 60% de los PRs de los equipos de backend usen especificación y agente de código al fin del trimestre, con tasa de fallos de cambios igual o menor a la actual |
| Proteger mejor los datos personales | Cero teléfonos o direcciones de destinatarios en los logs del asistente, verificado por un escaneo diario, a partir del 15 de diciembre |

Notar que varios objetivos SMART incluyen una **métrica de control**: algo que no debe empeorar mientras se mejora lo principal. Sin ella, se puede bajar la latencia descartando pedidos difíciles o subir la precisión con un modelo diez veces más caro.

**Ejemplo:** el objetivo de alertas de la tabla tiene como métrica principal la cantidad de alertas fuera de horario y como control el porcentaje de accionables. Sin el control, la forma más fácil de cumplirlo sería subir todos los umbrales, y la próxima caída real pasaría sin aviso.

**Por qué importa:** la columna de la derecha es más larga, y está bien: cada palabra agregada elimina una discusión futura sobre qué se quiso decir.

### Indicadores adelantados y rezagados

Un **indicador rezagado** (*lagging*) mide el resultado final, pero llega tarde: cuando se ve, ya no se puede corregir. Un **indicador adelantado** (*leading*) se mueve antes y predice el resultado, y se puede influir directamente.

Para el objetivo de ETAs, las entregas fallidas por ausencia son el indicador rezagado: se ven al final del mes. Los adelantados podrían ser el error medio de la ETA por semana, el porcentaje de destinatarios que recibió el aviso 30 minutos antes y la cobertura del feature de tráfico en la zona norte.

**Ejemplo:** en las primeras tres semanas del trimestre, las entregas fallidas no se mueven. Pero el error de la ETA bajó de 14 a 12 minutos y el aviso anticipado llega al 85% de los destinatarios. Los indicadores adelantados dicen que se va por buen camino aunque el resultado todavía no lo muestre.

**Por qué importa:** un objetivo que solo tiene indicadores rezagados se evalúa una vez, cuando ya es tarde. Conviene acompañar cada objetivo con uno o dos adelantados que se revisen cada semana.

### SMART y OKR

Los **OKR** (*Objectives and Key Results*) son un formato complementario. El **objetivo** es cualitativo e inspirador, sin números; los **resultados clave** (entre dos y cinco) son medibles y dicen cómo se sabrá que el objetivo se logró. Cada resultado clave, en la práctica, es un pequeño objetivo SMART.

**Ejemplo:**

- **Objetivo:** que los destinatarios confíen en lo que les dice Rumbo sobre su entrega.
- **KR1:** error absoluto medio de la ETA menor a 9 minutos en todas las zonas al 31 de marzo.
- **KR2:** precisión del asistente en preguntas de seguimiento mayor a 92% en el golden set.
- **KR3:** reclamos por "me dijeron una hora y no vino" bajan de 1.200 a 600 por mes.

Una diferencia práctica: los OKR suelen ser ambiciosos, y lograr el 70% se considera bueno; un objetivo SMART suele ser un compromiso que se espera cumplir completo. Conviene aclarar cuál se usa.

**Por qué importa:** mezclar compromisos con apuestas ambiciosas, sin decirlo, genera desconfianza en el sistema de objetivos.

### Objetivos SMART para funcionalidades con LLMs

Las funcionalidades con LLMs necesitan objetivos con al menos tres dimensiones: **calidad**, **costo** y **latencia**, y casi siempre una de **seguridad**. Optimizar una sola es fácil; el objetivo útil es el que las acota juntas.

La calidad se mide sobre un golden set (ver [Evaluación de LLMs](#t/evaluacion-llms)), que tiene que estar definido antes de fijar el número. Un "90% de precisión" sin decir sobre qué conjunto, con qué criterio y con qué juez no es medible.

**Ejemplo:** "Subir la precisión de respuestas del asistente de soporte en el golden set v3 (400 casos) de 82% a 90% antes del fin del segundo trimestre, manteniendo el costo por conversación por debajo de USD 0,04 (hipotético), el p95 del tiempo al primer token por debajo de 1,5 segundos y cero respuestas con datos personales de otro destinatario". Hay un indicador principal, dos de control y un límite de seguridad.

**Por qué importa:** sin las métricas de control, la forma más rápida de subir la precisión es usar un modelo más grande y más lento, y el objetivo se cumple empeorando la funcionalidad.

### Criterios de éxito en especificaciones para agentes de código

Cuando se trabaja con agentes de código, la especificación tiene que decir cuándo la tarea está terminada (ver [Desarrollo guiado por especificaciones](#t/sdd)). Esos criterios de aceptación son objetivos SMART en miniatura: específicos (qué endpoint, qué comportamiento), medibles (un test que pasa, un umbral), alcanzables en el alcance de la tarea, relevantes para el pedido y acotados en tiempo o en iteraciones.

**Ejemplo:** "Mejorar el endpoint de seguimiento" se convierte en: "El endpoint `GET /pedidos/{id}/seguimiento` responde en menos de 120 ms en p95 con la prueba de carga existente; los tests actuales siguen pasando; no se agregan dependencias; si después de tres intentos no se llega al umbral, el agente se detiene y reporta qué probó".

**Por qué importa:** un agente optimiza contra lo que se le pide. Si el criterio es vago, el agente decide por su cuenta cuándo terminó.

### Objetivos de crecimiento personal

En las reuniones uno a uno, los objetivos de crecimiento suelen quedar en "mejorar en arquitectura" o "ganar visibilidad". Aplicar SMART no significa medir a las personas con métricas de producción, sino hacer concreto qué se va a practicar y cómo se va a notar el progreso.

**Ejemplo:** "Aprender sobre agentes" se convierte en: "En el próximo trimestre, diseñar y liderar la revisión de diseño del servidor MCP de zonas, escribir su especificación y presentar los resultados de su eval en la reunión técnica de marzo". Es específico, verificable y relevante para el equipo, y la persona y quien la acompaña pueden revisarlo cada dos semanas.

**Por qué importa:** un objetivo concreto vuelve la conversación de crecimiento algo que se puede seguir.

### Trampas comunes

- **Medible pero sin sentido.** "Escribir 50 prompts nuevos" es medible y no dice nada sobre el resultado. Es el problema de la ley de Goodhart: cuando una métrica se vuelve objetivo, deja de medir bien.
- **Sandbagging.** Fijar objetivos fáciles a propósito para cumplirlos con seguridad. Se detecta comparando contra la tendencia: si el valor ya venía mejorando solo, el objetivo no agrega nada.
- **Demasiados objetivos.** Diez objetivos por trimestre equivalen a ninguno; entre dos y cuatro por equipo es razonable.
- **Output en lugar de outcome.** "Lanzar el asistente para transportistas" es un entregable (*output*); "que el 40% de las consultas de transportistas se resuelvan sin intervención humana" es un resultado (*outcome*). Lo primero puede cumplirse sin que nada mejore.

**Ejemplo:** un equipo tiene como objetivo "integrar el agente de operaciones en Slack" y lo cumple en la semana tres. En el mes dos, nadie lo usa. El objetivo debió ser de adopción: "que el 70% de las alertas SEV2 se investiguen primero con el agente, con una mediana de diagnóstico menor a 10 minutos".

**Por qué importa:** cada trampa produce objetivos que se cumplen sin que el sistema mejore, que es peor que no cumplirlos.

## Casos prácticos

### El objetivo de calidad que se cumplió duplicando el costo

**Situación:** el equipo del asistente tenía como objetivo "subir la precisión del golden set de 82% a 90% en el trimestre". Lo logró cambiando a un modelo más grande. El costo por conversación pasó de USD 0,03 a USD 0,07 (hipotético) y el tiempo de respuesta se duplicó.

**Qué se hace:** se reescribe el objetivo con métricas de control: precisión de 90% con costo por conversación menor a USD 0,04 y p95 de tiempo al primer token menor a 1,5 segundos. Con esas restricciones el equipo prueba un ruteo entre modelos: las preguntas simples van al modelo chico y las complejas al grande. Llega al 89% con costo de USD 0,038. El objetivo no se cumplió completo, pero el resultado es mejor que el del trimestre anterior.

### Medir la adopción del agente de código

**Situación:** dirección pregunta si los agentes de código "están funcionando". El único dato disponible es cuántas licencias están activas.

**Qué se hace:** se define un objetivo con indicadores adelantados y rezagados. Adelantados: porcentaje de PRs con especificación escrita, porcentaje de PRs donde el agente generó la primera versión. Rezagados: lead time de cambios y tasa de fallos de cambios, comparados con el trimestre anterior (ver [Métricas de entrega](#t/metricas-entrega)). Objetivo: "60% de PRs con especificación y agente al fin del trimestre, con lead time 20% menor y tasa de fallos igual o menor". Las licencias activas dejan de reportarse como métrica de éxito.

### Un objetivo personal que no avanzaba

**Situación:** una ingeniera tiene desde hace dos trimestres el objetivo "mejorar en comunicación técnica". En cada uno a uno se repite que "va bien".

**Qué se hace:** se reescribe en SMART: "Antes de fin de febrero, escribir el RFC del cambio de feature store, recibir revisión de al menos tres equipos y presentarlo en la reunión de arquitectura". Se acuerda un punto de control a mitad de camino con el borrador. En febrero hay un documento revisado y una presentación hecha; la conversación pasa de "va bien" a qué salió bien y qué se haría distinto.

## Errores comunes

- **Objetivos sin valor de partida.** "Llegar a 90%" no dice nada si no se sabe desde dónde se parte; se mide la línea de base antes de fijar la meta.
- **Omitir las métricas de control.** Todo objetivo de mejora se acompaña de lo que no debe empeorar: costo, latencia, seguridad o calidad.
- **Confundir entregables con resultados.** Lanzar algo es un hito; el objetivo es el cambio que ese lanzamiento produce.
- **Fijar números en funcionalidades con LLMs sin golden set.** Primero se define qué se evalúa y cómo; después, la meta.
- **Revisar los objetivos solo al final del período.** Se acompañan de indicadores adelantados y se revisan cada semana o cada dos.
- **Copiar el formato sin el criterio.** Un objetivo con las cinco letras puede seguir siendo irrelevante; la R es la que más se olvida.

## Para discutir en equipo

- ¿Cuáles de nuestros objetivos actuales son entregables disfrazados de resultados? ¿Cómo los reescribiríamos?
- ¿Qué métricas de control deberían acompañar cualquier objetivo del asistente de soporte?
- ¿Qué indicadores adelantados nos dirían en la semana tres si vamos a cumplir el objetivo del trimestre?
- ¿Usamos los objetivos como compromisos o como apuestas ambiciosas? ¿Lo sabe todo el equipo?
- ¿Cómo escribiríamos los criterios de aceptación de la próxima tarea que le demos a un agente de código para que sean verificables?
