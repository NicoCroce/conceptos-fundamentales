---
slug: metricas-entrega
titulo: Métricas de entrega: DORA y flujo
resumen: Cómo medir la velocidad y la estabilidad con que un equipo entrega software, y cómo saber si los agentes de código realmente ayudan.
lectura: 11
---

## La idea central

"¿Estamos entregando mejor que hace seis meses?" es una pregunta que casi todo equipo se hace y pocos pueden responder con datos. Las **métricas de entrega** dan esa respuesta mirando el sistema completo, desde que un cambio se escribe hasta que funciona en producción, y no el esfuerzo de cada persona. Las más conocidas son las cuatro métricas **DORA**, que salen de años de investigación sobre equipos de software: dos miden velocidad y dos miden estabilidad. Se complementan con las **métricas de flujo**, que miran cómo avanza el trabajo por el tablero.

La idea clave es que velocidad y estabilidad no compiten: los equipos que mejor rinden despliegan seguido **y** fallan poco, porque cambios chicos y frecuentes son más fáciles de revisar, probar y revertir. Hoy la pregunta tiene una vuelta más: si los agentes de código escriben buena parte del código, ¿el equipo entrega más rápido o solo produce más?

## Conceptos

### Las cuatro métricas DORA

1. **Frecuencia de despliegue:** cuántas veces por período se despliega a producción.
2. **Lead time de cambios** (*lead time for changes*): cuánto tarda un cambio desde el commit hasta estar en producción.
3. **Tasa de fallos de cambios** (*change failure rate*): qué porcentaje de despliegues provoca una degradación que obliga a revertir, aplicar un hotfix o abrir un incidente.
4. **Tiempo de recuperación** (*time to restore*): cuánto se tarda en restablecer el servicio después de un despliegue fallido. Está emparentado con el MTTR de la guardia (ver [On-call](#t/on-call)).

Las dos primeras miden **throughput** (cuánto y qué tan rápido fluye el cambio); las dos últimas, **estabilidad**. Mirar solo un par es engañoso: desplegar 20 veces por día con un 30% de fallos no es buen desempeño.

El programa de investigación que las define fue ajustando el modelo con los años: se sumó una métrica de confiabilidad operativa, se renombró el tiempo de recuperación para centrarlo en despliegues fallidos y se propuso una **tasa de retrabajo** (despliegues no planificados para corregir errores visibles por usuarios). Los rangos de referencia ("elite", "alto", "medio", "bajo") también cambian según el año. Conviene verificar la edición vigente del informe antes de citar umbrales; como orden de magnitud, los equipos de mejor desempeño despliegan a demanda varias veces por día, con lead times de menos de un día y recuperación en menos de una hora.

**Ejemplo:** el equipo del servicio de asignación de Rumbo despliega 2 veces por semana, con lead time de 6 días, 4% de fallos y recuperación de 45 minutos. Es estable, pero lento: cada despliegue junta muchos cambios y cuesta encontrar cuál falló.

**Por qué importa:** las cuatro juntas evitan optimizar una a costa de otra.

### Cómo se miden con datos reales

Ninguna de las cuatro necesita encuestas; salen de sistemas que ya existen:

- **Pipeline de CI/CD:** cada despliegue a producción con su timestamp y la lista de commits que incluye (ver [CI/CD](#t/ci-cd)).
- **Repositorio:** el timestamp de cada commit.
- **Gestión de incidentes:** cada incidente con su inicio, su recuperación y el despliegue que lo causó, si lo hubo.

**Ejemplo:** datos de un mes del equipo del asistente de soporte, con cifras hipotéticas:

| Métrica | Cálculo | Resultado |
|---|---|---|
| Frecuencia de despliegue | 46 despliegues en 20 días hábiles | 2,3 por día |
| Lead time de cambios | Mediana de (despliegue − commit) sobre 310 commits | 26 horas (p85: 3 días) |
| Tasa de fallos de cambios | 4 despliegues con rollback o hotfix / 46 | 8,7% |
| Tiempo de recuperación | Mediana de 25, 40, 15 y 120 minutos | 32,5 minutos |

Tres detalles de cálculo. Se usa **mediana y percentiles**, no promedio: un incidente de 120 minutos arrastra el promedio a 50. Hay que **acordar qué cuenta como fallo**: un despliegue que se revirtió por precaución sin impacto, ¿suma o no? Y hay que **vincular el incidente con el despliegue**: si la herramienta de incidentes no guarda qué versión estaba activa, la tasa de fallos se calcula a mano y deja de medirse.

**Por qué importa:** si la medición es manual, dura dos meses. Automatizarla desde el pipeline es la diferencia entre una métrica y una planilla abandonada.

### Métricas de flujo

Las métricas DORA miran desde el commit en adelante. Las **métricas de flujo** miran el ítem de trabajo completo, desde que se empieza (ver [Agile, Scrum y Kanban](#t/agile-scrum)):

- **Throughput:** ítems terminados por período.
- **WIP:** ítems en curso en un momento dado.
- **Cycle time:** tiempo desde que se empieza un ítem hasta que se termina.
- **Eficiencia de flujo:** porcentaje del cycle time en que alguien trabajó activamente en el ítem, frente al tiempo esperando (revisión, otro equipo, despliegue).

**Ejemplo:** el equipo de plataforma termina 18 ítems cada dos semanas, con un WIP promedio de 22 y un cycle time mediano de 4 días. Tomando un ítem típico: tardó 10 días en total, de los cuales 2 fueron de trabajo activo y 8 de espera (3 en revisión, 4 esperando a otro equipo, 1 esperando la ventana de despliegue). La eficiencia de flujo es 2 / 10 = 20%. Como orden de magnitud, muchos equipos están entre 15% y 40%.

**Por qué importa:** con 20% de eficiencia, trabajar el doble de rápido ahorra un día de diez; reducir la espera en revisión ahorra tres.

### SPACE: más allá de la velocidad

El marco **SPACE** propone mirar la productividad en cinco dimensiones, porque ninguna métrica sola la captura:

- **Satisfacción y bienestar:** cómo se siente el equipo con su trabajo y sus herramientas.
- **Desempeño** (*performance*): resultados, como calidad o impacto en usuarios.
- **Actividad:** conteos de acciones, como commits o PRs; útil solo en contexto.
- **Comunicación y colaboración:** qué tan bien fluye la información.
- **Eficiencia y flujo:** cuánto trabajo avanza sin interrupciones ni esperas.

La recomendación del marco es combinar al menos tres dimensiones e incluir alguna percepción de las personas, medida con encuestas breves.

**Ejemplo:** el equipo del modelo de ETA tiene buen throughput, pero la encuesta trimestral muestra que el 70% siente que pierde medio día por semana esperando que se libere el entorno de entrenamiento. Eso no aparecía en DORA.

**Por qué importa:** las métricas de actividad son las más fáciles de juntar y las más peligrosas de usar solas.

### La ley de Goodhart y cómo se manipulan las métricas

La **ley de Goodhart** dice que cuando una medida se convierte en objetivo, deja de ser una buena medida. La gente optimiza el número, no lo que el número representaba.

Algunas formas típicas:

- Exigir más **frecuencia de despliegue**: aparecen despliegues vacíos o partidos sin sentido.
- Premiar baja **tasa de fallos**: se deja de declarar incidentes o se reclasifican como "mantenimiento".
- Fijar meta de **lead time**: se abren PRs tarde, cuando el código ya está listo hace días.
- Contar **PRs o líneas de código**: se parten PRs artificialmente o se genera código de más.

Y una regla sin excepciones: **estas métricas no se usan para evaluar ni comparar personas**. Miden un sistema (equipo, pipeline, arquitectura). Usadas para rankear individuos, empeoran la colaboración (nadie revisa el PR ajeno si cuenta solo el propio) y se distorsionan en semanas.

**Ejemplo:** un área fijó como objetivo "tasa de fallos menor al 5%". Al trimestre siguiente la tasa cayó al 2%, pero los incidentes reportados por comercios no bajaron: muchos fallos se habían registrado como "ajustes de configuración".

**Por qué importa:** las métricas sirven para hacer preguntas, no para repartir premios.

### ¿Los agentes de código nos aceleran?

Medir el efecto de los agentes de código es el caso de uso más actual de estas métricas, y el más fácil de medir mal. Contar líneas de código o PRs generados con agentes dice cuánto se produjo, no si llegó antes ni si funciona. Lo que conviene comparar, antes y después, en un período de al menos dos o tres meses:

1. **Cycle time de punta a punta**, desglosado en escritura, espera de revisión y revisión.
2. **Tiempo de revisión** y tamaño de PR.
3. **Tasa de fallos de cambios.**
4. **Tasa de retrabajo:** cambios que corrigen otros cambios recientes.

**Ejemplo:** el equipo del asistente de soporte comparó tres meses antes y tres meses después de adoptar agentes, con cifras hipotéticas:

| Métrica | Antes | Después |
|---|---|---|
| PRs por persona por semana | 4 | 6,5 |
| Tamaño mediano de PR | 120 líneas | 260 líneas |
| Tiempo de escritura (mediana) | 2,0 días | 0,8 días |
| Espera de revisión (mediana) | 1,2 días | 2,1 días |
| Cycle time (mediana) | 5,0 días | 4,6 días |
| Tasa de fallos de cambios | 6% | 9% |
| Tasa de retrabajo | 7% | 12% |

Mirando solo PRs, parecía un 60% más de productividad. El cycle time mejoró apenas un 8%, porque la espera de revisión casi se duplicó, y la estabilidad empeoró. El equipo respondió con PRs más chicos ligados a una especificación y un límite de PRs en revisión; tres meses después el cycle time bajó a 3,8 días y la tasa de fallos volvió al 6%.

Dos cuidados metodológicos: comparar períodos parecidos (sin temporada alta en uno solo) y tener en cuenta que otras cosas cambiaron a la vez, como el equipo, la base de código o el pipeline.

**Por qué importa:** acelerar la escritura y frenar la revisión deja el resultado igual o peor, con más esfuerzo.

### Métricas para operar funcionalidades con agentes

Además de medir cómo construimos, hay que medir cómo se comportan en producción las funcionalidades con agentes. A alto nivel:

- **Tasa de éxito de tareas:** porcentaje de conversaciones o tareas resueltas sin intervención humana, verificado con muestreo.
- **Tasa de derivación:** cuántas veces el agente pasa el caso a una persona.
- **Calidad en evaluación:** puntaje sobre un conjunto fijo de casos, en cada cambio de modelo o prompt.
- **Latencia y costo por tarea:** p95 de respuesta y tokens consumidos.
- **Errores de herramientas:** llamadas fallidas o rechazadas por permisos.

El detalle de cómo se instrumentan está en [LLMs en producción](#t/llms-produccion).

**Ejemplo:** el asistente para transportistas resuelve el 78% de las consultas sin derivar, con un p95 de 3,1 segundos. Tras un cambio de prompt, la tasa sube al 84% pero la evaluación muestra un 3% más de respuestas con horarios incorrectos: resolver más no es mejor si resuelve mal.

**Por qué importa:** una métrica de volumen sin una de calidad al lado repite el problema de Goodhart, ahora en el agente.

## Casos prácticos

### Un equipo rápido que fallaba seguido

**Situación:** el equipo del panel de comercios despliega 5 veces por día, con lead time de 3 horas. Pero su tasa de fallos es del 22% y los comercios reportan errores con frecuencia.

**Qué se hace:** se analizan los 30 fallos del trimestre. El 60% eran regresiones visuales y de permisos que ningún test cubría. Se agregan tests de extremo a extremo para los cinco flujos principales y despliegues canary con métricas de error. La frecuencia baja a 4 por día y la tasa de fallos cae al 7%. El equipo acepta un poco menos de velocidad por mucha más estabilidad.

### La meta de frecuencia de despliegue

**Situación:** la dirección de ingeniería quiere que todos los equipos lleguen a "elite" en frecuencia de despliegue y propone publicar un ranking mensual por equipo.

**Qué se hace:** se discute antes de publicar nada. Los equipos tienen contextos distintos: el modelo de ETA despliega con validación offline y modo sombra, y los clientes on-prem reciben versiones mensuales. Se acuerda que cada equipo mire sus cuatro métricas contra su propia línea de base, que se publiquen tendencias y no rankings, y que ninguna se use en evaluaciones individuales.

### Medir el efecto de los agentes en el servicio de asignación

**Situación:** el líder del servicio de asignación quiere saber si conviene ampliar el uso de agentes de código. La primera propuesta es contar las líneas generadas por agentes.

**Qué se hace:** se descarta contar líneas. Se toma la línea de base de los tres meses previos (cycle time desglosado, tiempo de revisión, tasa de fallos y retrabajo) y se habilitan agentes en dos de los cuatro subequipos durante tres meses, con la misma base de código. Al final se comparan los dos grupos y cada uno contra su línea de base. Se agrega una encuesta corta de SPACE sobre carga de revisión, porque es donde se espera que aparezca el costo.

## Errores comunes

- **Mirar solo velocidad.** Frecuencia y lead time sin tasa de fallos y recuperación premian el desorden; se miran las cuatro juntas.
- **Usar promedios.** Un caso extremo distorsiona todo; se usan mediana y percentiles.
- **Rankear personas o equipos con estas métricas.** Miden sistemas; usadas como evaluación, se manipulan y dañan la colaboración.
- **Medir agentes por volumen.** Líneas y PRs no son entrega; se mide cycle time de punta a punta, revisión, fallos y retrabajo.
- **Medición manual.** Si depende de una planilla, se abandona; se automatiza desde el pipeline y la herramienta de incidentes.
- **No acordar definiciones.** Qué es un fallo o cuándo empieza el lead time debe estar escrito antes de medir.

## Para discutir en equipo

- ¿Podemos calcular hoy nuestras cuatro métricas DORA sin trabajo manual? ¿Qué dato nos falta?
- ¿Cuál es nuestra eficiencia de flujo aproximada y dónde está la espera más larga?
- ¿Qué métrica nuestra podría estar siendo manipulada sin que nadie lo haya decidido?
- ¿Cómo mediríamos, con rigor razonable, si los agentes de código nos están ayudando?
- ¿Qué métrica de calidad acompaña hoy a cada métrica de volumen de nuestras funcionalidades con agentes?
