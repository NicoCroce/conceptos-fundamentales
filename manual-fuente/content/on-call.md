---
slug: on-call
titulo: On-call, runbooks e incidentes
resumen: Cómo organizar la guardia, alertar bien, responder a incidentes con roles claros y aprender de ellos con postmortems sin culpas.
lectura: 13
---

## La idea central

Un sistema en producción falla tarde o temprano, y casi nunca en horario de oficina. El **on-call** (guardia) es el acuerdo por el cual una persona del equipo está disponible para responder cuando algo se rompe. Hacerlo bien no consiste en tener héroes que se despiertan a las 3 a.m. y arreglan todo de memoria, sino en diseñar un proceso donde cualquier integrante entrenado pueda recibir una alerta clara, seguir un procedimiento escrito, contener el daño rápido y dejar el sistema un poco mejor que antes.

Una analogía útil es la guardia de un hospital: no se espera que el médico de turno sepa todo, sino que tenga protocolos, sepa a quién llamar, priorice estabilizar al paciente antes de investigar la causa y deje registro de lo que hizo. En Rumbo, eso significa que si cae la tasa de entregas a tiempo en una zona, la persona de guardia sabe en minutos si es grave, qué mirar primero, cómo mitigar y a quién avisar.

## Conceptos

### Rotación de guardia

La rotación define quién está de guardia y cuándo. Lo habitual es tener una **guardia primaria**, que recibe todas las alertas y responde primero, y una **secundaria**, que entra si la primaria no reconoce la alerta en un tiempo pactado (por ejemplo, 10 minutos) o si necesita ayuda. Las herramientas de paging (PagerDuty, Opsgenie o similares) automatizan esa escalada.

El tamaño de la rotación importa más de lo que parece. Si la guardia dura una semana y la rotación tiene 3 personas, cada una está de guardia 1 de cada 3 semanas: unas 17 semanas al año con el teléfono encima. Con 6 personas baja a una semana cada mes y medio, algo mucho más sostenible. Una regla práctica común es no bajar de **5 a 8 personas** por rotación; por debajo de eso, el cansancio se acumula y la gente se va.

Otros acuerdos que conviene dejar escritos:

- **Traspaso de guardia** (handoff): una nota breve al terminar el turno con incidentes abiertos, alertas ruidosas y cambios riesgosos programados.
- **Compensación y descanso**: si alguien fue despertado varias veces, al día siguiente no se espera que rinda igual.
- **Horario "follow the sun"**: si el equipo está repartido en husos horarios distintos, cada región cubre su día y nadie hace noches.

**Ejemplo:** el equipo de asignación de Rumbo tiene 7 personas. Turnos semanales de lunes a lunes, primaria y secundaria. Cada persona hace primaria unas 7 semanas al año y secundaria otras 7. La secundaria de esta semana es la primaria de la semana anterior, así conoce el contexto reciente.

**Por qué importa:** una rotación chica produce agotamiento, y la gente agotada comete más errores durante los incidentes.

### Alertar por síntomas, no por causas

Una alerta debería sonar cuando **el usuario está sufriendo** (o está a punto de sufrir), no cuando una métrica interna se ve rara. Los síntomas son lo que percibe el comercio o el destinatario: pedidos que no se asignan, ETAs muy erróneas, errores en la API. Las causas son cosas como CPU alta, una réplica de base de datos atrasada o un pod reiniciado.

El problema de alertar por causas es doble. Primero, muchas causas no producen síntomas: un nodo con 90% de CPU puede estar funcionando perfecto. Segundo, nunca se pueden enumerar todas las causas posibles, así que siempre habrá fallas que no disparen nada. Alertar por síntomas cubre fallas que nadie imaginó.

Las causas siguen siendo útiles, pero en **dashboards** y en alertas de baja prioridad (un ticket, no un page). Las métricas de síntoma suelen expresarse como SLO (objetivo de nivel de servicio); ver [Prometheus y Grafana](#t/prometheus-grafana) para alertas por burn rate.

**Ejemplo:** en vez de alertar "CPU del servicio de asignación > 80%", se alerta "más del 2% de los pedidos tarda más de 5 segundos en asignarse durante 10 minutos". La primera puede sonar sin daño; la segunda sólo suena si hay daño.

### Fatiga de alertas

La fatiga de alertas aparece cuando suenan tantas alertas inútiles que la gente deja de prestarles atención. Es peligrosa porque la alerta real termina ignorada entre el ruido, igual que el cuento del pastor y el lobo.

Toda alerta que despierta a alguien debería cumplir tres condiciones: ser **urgente** (no puede esperar a la mañana), ser **accionable** (hay algo concreto que hacer) y ser **real** (no un falso positivo). Si una alerta no cumple las tres, se baja a ticket, se ajusta el umbral o se elimina.

**Ejemplo:** si una alerta sonó 12 veces en el mes y en 11 la respuesta fue "esperar a que se resuelva sola", esa alerta no es accionable y hay que rediseñarla o borrarla.

### Severidades

Las severidades permiten responder de forma proporcional: no es lo mismo una caída total que un dashboard roto. Definirlas antes del incidente evita discutir en medio de la crisis si "esto es grave o no". La severidad decide quién se convoca, con qué urgencia y cada cuánto se comunica.

| Severidad | Definición | Ejemplo en Rumbo | Respuesta esperada |
|---|---|---|---|
| SEV1 | Caída total o daño masivo a usuarios; exposición de datos personales | El servicio de asignación no asigna pedidos en ninguna zona; se filtran teléfonos de destinatarios | Page inmediato, incident commander, comunicación a clientes cada 30 min, todos los roles activos |
| SEV2 | Degradación importante de una función central o de una región | Entregas a tiempo caen del 92% al 70% en la zona norte; ETAs con error de más de 40 minutos | Page inmediato a primaria y secundaria, actualizaciones internas cada hora |
| SEV3 | Problema parcial con alternativa disponible | El asistente de soporte con LLM no responde y los tickets van a humanos; el pronóstico de demanda nocturno se atrasó 3 horas | Se atiende en horario laboral o en las próximas horas, sin despertar a nadie |
| SEV4 | Molestia menor, sin impacto visible al usuario | Un dashboard interno muestra datos incompletos; una alerta ruidosa | Ticket en el backlog |

Una regla sana: ante la duda, se declara la severidad más alta y se baja después. Es más barato desescalar que llegar tarde.

### Roles en un incidente

En un incidente grande, el error típico es que todos investigan a la vez y nadie coordina. Por eso se separan roles:

- **Incident commander (IC):** coordina. No toca el sistema; decide prioridades, asigna tareas, define cuándo escalar y cuándo se da por mitigado. Su pregunta constante es "¿qué estamos haciendo ahora y quién lo hace?".
- **Responsable técnico** (a veces llamado *ops lead*): investiga y ejecuta los cambios técnicos, con ayuda de otras personas si hace falta.
- **Comunicaciones:** redacta las actualizaciones para el resto de la empresa, soporte y clientes, con una cadencia fija. Libera al resto de responder "¿cómo va?" cada cinco minutos.
- **Escriba** (opcional): registra la línea de tiempo con horarios; esa línea será la base del postmortem.

En un SEV3 una sola persona puede cubrir todos los roles. En un SEV1 conviene que sean personas distintas.

### Mitigar primero, entender después

Durante un incidente, el objetivo es **detener el daño**, no encontrar la causa raíz. Mitigar puede ser hacer rollback (volver a la versión anterior), desactivar un feature flag, redirigir tráfico a otra región, escalar réplicas o activar un modo degradado. La investigación profunda viene después, con calma.

**Ejemplo:** si tras un despliegue la tasa de errores sube del 0,1% al 8%, la primera acción es revertir el despliegue (5 minutos) y no leer el diff línea por línea (que podría tomar una hora con usuarios afectados todo ese tiempo).

**Por qué importa:** cada minuto de investigación con el sistema roto es un minuto de impacto. Entender la causa con el sistema sano es igual de posible y mucho menos estresante.

### Runbooks

Un **runbook** es un procedimiento escrito para responder a una alerta concreta. Idealmente, cada alerta que puede despertar a alguien enlaza a su runbook. Un buen runbook permite que alguien que nunca vio ese servicio pueda diagnosticar y mitigar en los primeros 15 minutos.

Plantilla sugerida:

```markdown
# Runbook: <nombre de la alerta>

## Qué significa
Una o dos oraciones: qué síntoma detecta y qué ve el usuario.

## Impacto
Quién se ve afectado y severidad sugerida (SEV1–SEV4).

## Diagnóstico rápido (primeros 10 minutos)
1. Abrir el dashboard <nombre> y mirar la fila <fila>.
2. ¿Hubo un despliegue en la última hora? Revisar <herramienta>.
3. ¿Está afectada una zona o todas? Filtrar por label `zona`.
4. Revisar dependencias: feature store, Aurora, servicio del modelo.

## Mitigación
- Si hubo despliegue reciente: rollback con `<comando>`.
- Si el modelo responde lento: activar respaldo heurístico con el flag `asignacion_fallback`.
- Si una dependencia está caída: <pasos>.

## Escalada
- Equipo dueño de la dependencia: <canal o rotación>.
- Cuándo declarar SEV1: <criterio>.

## Contexto
Enlaces a diseño, dashboards, postmortems previos relacionados.
Última revisión: <fecha> por <persona>.
```

Los runbooks se pudren: si nadie los usa ni los revisa, quedan desactualizados. Conviene revisarlos después de cada incidente y en los simulacros.

### Postmortem sin culpas

El **postmortem** es el documento que se escribe después de un incidente para entender qué pasó y qué cambiar. "Sin culpas" (*blameless*) significa que el análisis busca fallas en el sistema y en los procesos, no personas a quien señalar. La premisa es que la gente actuó razonablemente con la información que tenía; si un error humano causó daño, la pregunta es por qué el sistema permitió que ese error tuviera ese efecto.

No es una cuestión de amabilidad: si el postmortem castiga, la gente oculta información y el equipo deja de aprender.

Plantilla sugerida:

```markdown
# Postmortem: <título descriptivo>

**Fecha del incidente:** <fecha>   **Severidad:** SEV<n>
**Duración del impacto:** <hh:mm> a <hh:mm> (<n> minutos)
**Autores:** <personas>   **Estado:** borrador / revisado

## Resumen
Tres o cuatro oraciones: qué pasó, impacto, cómo se mitigó.

## Impacto
Métricas concretas: pedidos afectados, zonas, clientes, minutos.

## Línea de tiempo
| Hora | Evento |
|---|---|
| 02:58 | Se despliega la versión X |
| 03:04 | Suena la alerta Y |

## Causas y factores contribuyentes
Qué condiciones del sistema hicieron posible el incidente.
Preferir "el proceso permitió..." a "la persona hizo...".

## Qué funcionó bien
## Qué funcionó mal
## Dónde tuvimos suerte

## Acciones
| Acción | Tipo (prevenir / detectar / mitigar) | Responsable | Fecha |
|---|---|---|---|
```

### Métricas de la guardia

Para saber si el proceso mejora, se miden algunas cosas:

- **MTTD** (*mean time to detect*): tiempo medio desde que empieza el impacto hasta que alguien se entera. Si el impacto empezó a las 02:50 y la alerta sonó a las 03:04, el tiempo de detección fue de 14 minutos.
- **MTTR** (*mean time to recover/restore*): tiempo medio desde el inicio del impacto hasta la recuperación del servicio. Ojo: algunas organizaciones lo miden desde la detección; conviene acordar la definición.
- **Alertas fuera de horario por semana**: cuántas veces se despierta a alguien. Un objetivo razonable es que sean pocas, del orden de una o dos por turno.
- **Porcentaje de alertas accionables**: de las alertas que sonaron, cuántas requirieron una acción. Si es bajo, hay fatiga en camino.

**Ejemplo:** en un trimestre hubo 6 incidentes con tiempos de recuperación de 20, 35, 15, 90, 25 y 30 minutos. El MTTR es 215 / 6, unos 36 minutos. El de 90 minutos merece atención aparte: los promedios esconden casos extremos.

### Simulacros (game days)

Un **game day** es un ejercicio planificado en el que se provoca o se simula una falla para practicar la respuesta. Puede ser tan simple como "mesa de discusión" (se narra un escenario y el equipo dice qué haría) o tan realista como inyectar latencia en el feature store en un entorno de staging.

Sirve para encontrar runbooks desactualizados, alertas que no suenan, permisos que faltan y huecos de conocimiento, todo sin usuarios afectados. También entrena a quienes recién entran a la rotación. Ver [Patrones de resiliencia](#t/resiliencia) para las técnicas de degradación que conviene ejercitar.

## Casos prácticos

### Alerta a las 3 a.m.: caen las entregas a tiempo en la zona sur

**Situación:** suena la alerta "tasa de entregas a tiempo en zona sur < 80% durante 15 minutos" (el valor normal es 93%). La persona de guardia primaria la reconoce a las 03:06.

**Qué se hace:** abre el runbook enlazado. Primero determina el alcance: sólo zona sur, el resto normal. Evalúa severidad: una zona con degradación importante, SEV2. Revisa cambios recientes: no hubo despliegues, pero el dashboard muestra que el modelo de ETA recibe la feature de clima con valor nulo para esa zona desde las 02:40. Le pregunta al agente interno de operaciones, que con herramientas de solo lectura confirma que el proveedor de clima devuelve errores para esas coordenadas. Mitiga activando el valor por defecto de clima para la zona (un flag documentado en el runbook). A las 03:35 la métrica se recupera. Deja nota en el traspaso y abre un ticket para que, ante feature faltante, el sistema use el valor por defecto automáticamente y emita una alerta de baja prioridad.

### 40 alertas por semana, 80% no accionables

**Situación:** el equipo recibe unas 40 alertas semanales. Al revisarlas, 32 se resolvieron solas o no requirieron acción. La guardia está agotada y ya hubo una alerta real ignorada durante 25 minutos.

**Qué se hace:** se hace una revisión semanal de alertas. Para cada alerta ruidosa se decide: eliminar (si nunca lleva a una acción), convertir en ticket (si importa pero no es urgente), ajustar ventana y umbral (si salta por picos breves) o reemplazar por una alerta de síntoma basada en SLO. En un mes se pasa a 8 alertas semanales con 75% accionables. Se adopta la regla de que toda alerta nueva necesita un runbook y una persona responsable.

### Un despliegue de modelo rompe la asignación

**Situación:** a las 14:10 se despliega una nueva versión del modelo de ETA. A las 14:14 la tasa de pedidos sin asignar sube del 0,5% al 12%. No es obvio por qué: las métricas offline del modelo eran mejores.

**Qué se hace:** el responsable técnico propone revertir al modelo anterior antes de investigar; el incident commander aprueba. A las 14:19 el rollback está hecho y la métrica vuelve a la normalidad. Con el servicio sano, se investiga: el nuevo modelo esperaba una feature con un nombre distinto, recibía nulos y devolvía probabilidades cercanas a cero para todos los transportistas, así que la lógica de asignación descartaba a todos. Acciones: validación de esquema de features en el despliegue y despliegue canario (primero al 5% del tráfico). Ver [Ciclo de vida de modelos](#t/ciclo-vida-modelos).

### Reescribir un postmortem que culpa a una persona

**Situación:** un borrador dice: "El incidente ocurrió porque Martín ejecutó un script de migración en producción en lugar de staging, por descuido."

**Qué se hace:** se reescribe en clave de sistema: "El script de migración acepta el entorno como parámetro sin confirmación y las credenciales de producción estaban disponibles en la misma terminal que las de staging. Nada distinguía visualmente un entorno del otro." Las acciones cambian de "Martín debe tener más cuidado" (inútil) a "el script pide confirmación explícita en producción", "credenciales de producción sólo vía acceso temporal" y "prompt de terminal con color distinto por entorno". El nombre de la persona desaparece del documento.

## Errores comunes

- **Alertar por todo lo medible.** Cada alerta debe ser urgente, accionable y real; el resto va a dashboards o tickets.
- **Investigar la causa con el sistema roto.** Primero se mitiga (rollback, flag, respaldo) y después se investiga con calma.
- **Runbooks escritos una vez y nunca revisados.** Se actualizan después de cada incidente y se prueban en simulacros.
- **Postmortems con acciones vagas.** "Mejorar el monitoreo" no es una acción; "alerta de nulos en la feature clima, responsable Ana, fecha 15/12" sí lo es.
- **Rotaciones de tres personas.** No son sostenibles; si el equipo es chico, conviene compartir rotación con otro equipo o reducir el alcance de lo que despierta.
- **Que el incident commander también arregle.** Si coordina y ejecuta a la vez, ninguna de las dos cosas se hace bien.

## Para discutir en equipo

- ¿Qué alertas de las últimas cuatro semanas no llevaron a ninguna acción, y qué hacemos con cada una?
- ¿Cómo debería clasificarse un incidente del asistente de soporte con LLM que da respuestas incorrectas pero no se cae?
- ¿Qué mitigaciones de un solo paso (flags, rollback, respaldo) existen hoy para el servicio de asignación, y cuáles faltan?
- ¿Cómo medimos el impacto de un incidente en términos de negocio (pedidos tarde, comercios afectados) y no sólo técnicos?
- ¿Qué escenario elegiríamos para el próximo game day y qué esperamos descubrir?
