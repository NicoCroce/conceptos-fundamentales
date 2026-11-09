---
slug: raci-rasi
titulo: Matrices de responsabilidad: RACI y RASI
resumen: Cómo usar matrices RACI y RASI para dejar claro quién hace, quién aprueba, quién apoya y quién se entera, incluidos los agentes en producción.
lectura: 12
---

## La idea central

Muchos problemas de un proyecto no son técnicos sino de responsabilidad: una decisión queda frenada dos semanas porque nadie sabe quién la toma, dos personas creen ser dueñas del mismo tema y deciden cosas distintas, o un trabajo que "era de todos" no lo hace nadie. Casi nunca es mala voluntad: las responsabilidades se dieron por sobreentendidas y cada persona sobreentendió algo diferente.

Una **matriz de responsabilidad** es una tabla simple: en las filas van las actividades o decisiones, en las columnas los roles, y en cada celda una letra que dice qué papel cumple ese rol. Su valor está en la conversación que obliga a tener: al escribir una letra por celda aparecen desacuerdos que de otro modo se descubren en medio de un incidente. Con agentes en producción la pregunta se vuelve más urgente, porque aparece un actor que hace trabajo real pero no puede responder por él.

## Conceptos

### Para qué existe una matriz de responsabilidad

Los síntomas de responsabilidades confusas son reconocibles:

- **Decisiones que se estancan:** el tema vuelve a cada reunión sin cerrarse.
- **Dueños duplicados:** dos personas aprueban cosas contradictorias.
- **Huecos:** una tarea que nadie considera suya (actualizar el runbook, revisar la evaluación) no ocurre.
- **Consultas infinitas:** para cambiar algo hay que convencer a ocho personas, y cualquiera puede bloquear.

**Ejemplo:** en Rumbo, el cambio del modelo del asistente de soporte estuvo tres semanas en discusión. Producto creía que la decisión era de ML; ML, que era de plataforma, que maneja el gateway de LLM; plataforma esperaba el visto bueno de producto. Al armar la matriz, la fila "elegir el modelo del asistente" tenía tres A. Con una sola, la decisión se tomó en dos días.

**Por qué importa:** el costo de la ambigüedad no aparece en ningún tablero, pero se paga en semanas de demora y retrabajo.

### RACI: las cuatro letras

**RACI** es la variante más conocida:

- **R (Responsible), responsable de ejecutar:** hace el trabajo. Puede haber varios R por fila.
- **A (Accountable), quien rinde cuentas:** responde por el resultado, decide y aprueba que está terminado. Hay **uno solo** por fila.
- **C (Consulted), consultado:** da su opinión antes de decidir. Comunicación de ida y vuelta.
- **I (Informed), informado:** se entera del resultado. Comunicación de una vía.

La distinción que más cuesta es entre R y A. R es "quién lo hace"; A es "a quién se le pregunta si salió mal". Pueden coincidir (se escribe R/A), pero no son lo mismo: una tech lead puede ser A de una migración que ejecutan otras tres personas.

**Ejemplo:** en "actualizar el golden set del asistente", el ingeniero de ML que agrega casos es R, la líder de ML que firma que el conjunto es representativo es A, soporte, que aporta conversaciones reales, es C, y producto, que solo necesita saber que cambió, es I.

**Por qué importa:** separar R de A permite delegar el trabajo sin delegar la responsabilidad por el resultado.

### RASI: soporte en lugar de consultado

**RASI** usa **R** (Responsable), **A** (Aprobador), **S** (Soporte) e **I** (Informado). La diferencia de fondo está en la S:

- **Consultado (C)** opina. Su aporte es criterio antes de decidir.
- **Soporte (S)** trabaja. Aporta esfuerzo concreto (configura algo, escribe una parte, presta un entorno) bajo la conducción del R.

Una opinión y un trabajo se planifican distinto. Si plataforma figura como C en "desplegar el asistente para un comercio nuevo", nadie le reserva horas; si figura como S, su capacidad tiene que estar en el plan.

**Ejemplo:** en el lanzamiento del asistente para un comercio grande nuevo, seguridad es C en "definir qué datos del comercio puede ver el agente" (da criterio) y S en "red teaming antes del piloto" (dedica dos días a atacar el sistema).

**Por qué importa:** muchos atrasos vienen de equipos que figuraban como "consultados" y en realidad tenían trabajo que nadie les había pedido formalmente.

### Variantes: RACI-VS y DACI

| Matriz | Letras | Para qué sirve | Cuándo conviene |
|---|---|---|---|
| RACI | Responsible, Accountable, Consulted, Informed | Repartir trabajo y opinión | Procesos y proyectos con varias áreas |
| RASI | Responsable, Aprobador, Soporte, Informado | Igual, separando quién aporta trabajo | Equipos que prestan capacidad a otro |
| RACI-VS | RACI más Verifier y Signatory | Sumar quién verifica contra criterios y quién firma | Entregas reguladas o con aceptación del cliente |
| DACI | Driver, Approver, Contributors, Informed | Llevar **una decisión** hasta cerrarla | Diseño, elección de proveedor o de modelo |

DACI no reparte tareas: organiza una decisión. El **Driver** no decide, sino que la empuja (arma opciones, junta datos, convoca); el **Approver** decide; los **Contributors** aportan conocimiento.

**Ejemplo:** la elección de un segundo proveedor de LLM se maneja con un DACI: plataforma es Driver, la tech lead del asistente es Approver, ML y seguridad son Contributors y soporte es Informed, con fecha límite para decidir.

**Por qué importa:** usar RACI para una decisión única es pesado; usar DACI para un proceso recurrente deja tareas sin dueño.

### Reglas para que la matriz funcione

1. **Exactamente una A por fila.** Dos A equivalen a ninguna: cada una espera a la otra o deciden distinto.
2. **Al menos una R por fila.** Una actividad con aprobador y sin quien la haga es un deseo.
3. **Pocas C.** Con más de dos o tres consultados, la actividad se vuelve un comité.
4. **Pocas R.** Si cinco roles son R, en la práctica nadie lo es: se divide la actividad.
5. **La A tiene autoridad real** para decidir y conseguir recursos.
6. **Roles en las columnas, no nombres**, y aparte quién ocupa cada rol hoy, para que la matriz sobreviva a vacaciones y cambios de equipo.

**Ejemplo:** la fila "responder incidentes del asistente" tenía R en soporte, ML, plataforma y el equipo del asistente. Durante una caída, cuatro personas investigaban lo mismo y nadie avisaba a los comercios. Se dividió en "coordinar el incidente" (R/A: guardia del asistente), "diagnóstico de infraestructura" (R: plataforma) y "comunicar a comercios" (R: soporte).

**Por qué importa:** una matriz que rompe estas reglas ya muestra dónde va a haber fricción.

### Armar la matriz en una sesión de 45 minutos

1. **Antes:** quien convoca escribe un borrador con 8 a 15 actividades y 4 a 7 roles. Con más filas, la sesión no termina.
2. **Minutos 0 a 5:** se repasa el objetivo ("saber quién aprueba qué en el lanzamiento") y el significado de cada letra, a la vista.
3. **Minutos 5 a 15:** se agregan actividades faltantes. Preguntas útiles: "¿qué se hace cuando sale mal?" y "¿qué trabajo nadie quiere hacer?".
4. **Minutos 15 a 30:** se completa fila por fila, empezando por la A. Si una A se discute, se anota el desacuerdo y se sigue.
5. **Minutos 30 a 40:** se lee por columnas y se corrigen sobrecargas y huecos.
6. **Minutos 40 a 45:** cada desacuerdo abierto recibe responsable y fecha, y se decide dónde vive la matriz (junto al documento del proyecto o en el repositorio).

**Ejemplo:** el equipo del asistente armó la matriz del lanzamiento para un comercio nuevo con 6 roles y 7 actividades. Quedaron dos desacuerdos: quién aprueba el texto que ve el destinatario y quién es A del golden set del comercio. Se resolvieron al día siguiente.

**Por qué importa:** una matriz hecha por una persona y enviada por correo no genera acuerdo; el valor está en que los roles la discutan juntos.

### Leer la matriz por filas y por columnas

- **Por filas:** cada actividad tiene una A y al menos una R, sin exceso de C.
- **Por columnas:** una columna llena de R es un rol sobrecargado; una llena de A concentra demasiadas decisiones; una sin A ni R quizás no necesita estar en la reunión; una solo con I puede pasar a un canal de novedades.

```roles
titulo: RASI: asistente para un comercio grande nuevo
columnas: Producto | Tech lead | ML | Plataforma | Seguridad | Soporte
Definir casos de uso y alcance | A | R | S | I | I | S
Golden set del comercio | I | S | R/A | I | I | S
Servidor MCP de pedidos del comercio | I | A | I | R | S | I
Prompts y textos para destinatarios | A | S | R | I | I | S
Red teaming antes del piloto | I | A | S | S | R | I
Piloto con operadores del comercio | A | S | S | S | I | R
Guardia del asistente en producción | I | A | S | R | I | S
```

**Ejemplo:** en el primer borrador de esta matriz, la columna de la tech lead tenía 6 A sobre 7 filas. Cuando se fue una semana de vacaciones, el proyecto se frenó. Se pasaron dos A a producto (alcance y textos) y una a ML (golden set), y quedó como se ve arriba.

**Por qué importa:** la lectura por columnas detecta los cuellos de botella de personas antes de que aparezcan en el plan.

### Agentes en la matriz: pueden ser R, nunca A

Un agente hace trabajo real: un agente de código escribe una migración, el agente de operaciones investiga una alerta, el asistente redacta la respuesta a un ticket. Puede ocupar la R de una fila. No puede ocupar la A: no rinde cuentas, no se lo despierta a las tres de la mañana para explicar qué pasó, no decide aceptar un riesgo. La A de toda fila donde trabaja un agente es una persona.

- **Cambios generados por agentes:** el agente es R de escribir el cambio; quien lanzó la tarea es A de que sea correcto, y otra persona revisa. "Lo escribió el agente" no es una explicación válida en un postmortem (ver [Desarrollo guiado por especificaciones](#t/sdd)).
- **Acciones del agente en producción:** si el asistente reprograma una entrega por error, la A es el dueño de la funcionalidad, no el proveedor del modelo.
- **Herramientas con escritura:** cada una tiene una A que aprobó su alcance y sus permisos.

**Ejemplo:** el agente de operaciones abre un borrador de postmortem tras cada alerta. En la matriz es R de "redactar el borrador"; la persona de guardia es R/A de "completar y publicar el postmortem". El agente nunca publica solo.

**Por qué importa:** un agente sin una A humana asociada es una acción en producción sin dueño, justo lo que la matriz existe para evitar.

### Responsabilidades nuevas de los sistemas con agentes

Los sistemas con LLMs traen artefactos que suelen quedar sin dueño:

- **Prompts y system prompts:** son código de producción; cada cambio tiene una A y pasa por evaluación.
- **Datasets de evaluación:** alguien mantiene el golden set representativo y suma los casos que fallaron en producción (ver [Evaluación de LLMs](#t/evaluacion-llms)).
- **Herramientas y servidores MCP:** como cualquier API, tienen dueño de su contrato, de la ampliación de permisos y de su deprecación.
- **Guardia de funcionalidades con agentes:** cuando el asistente responde mal sin que nada "se caiga", alguien está de guardia con un runbook que incluye apagar herramientas o derivar a personas (ver [On-call, runbooks e incidentes](#t/on-call)).
- **Versión del modelo:** quién decide migrar y quién aprueba la reevaluación.

**Ejemplo:** un ingeniero cambió una línea del system prompt para corregir un caso puntual y las derivaciones a personas subieron del 12 % al 19 % en dos días. Nadie había definido quién aprobaba cambios de prompt. Desde entonces la fila existe: ML es R, la tech lead es A y ningún cambio se despliega sin pasar por el golden set.

**Por qué importa:** los artefactos de un sistema con LLM cambian el comportamiento tanto como el código; sin A, cambian sin control.

## Casos prácticos

### Arreglar una matriz que no servía

**Situación:** la matriz del agente de operaciones se armó rápido al inicio. Seis meses después nadie la consulta: tiene una fila con dos A, otras con tres R y una donde todos son C.

**Qué se hace:** se revisa con las reglas, se deja una A por fila y se divide "operar el agente" en actividades concretas. Las dos versiones se comparan en la sesión:

```roles
titulo: Antes: matriz del agente de operaciones
columnas: Producto | Tech lead | Plataforma | SRE | Seguridad
Elegir herramientas del agente | A | A | R | R | C
Permisos de solo lectura | C | R | R | R | A
Operar el agente | C | R | R | R | C
Revisar sus conclusiones | C | C | C | C | C
```

```roles
titulo: Después: una A por fila, tareas divididas
columnas: Producto | Tech lead | Plataforma | SRE | Seguridad
Elegir herramientas del agente | C | A | R | C | C
Permisos de solo lectura | I | C | R | I | A
Desplegar y monitorear el agente | I | A | R | S | I
Guardia del agente | I | I | S | R/A | I
Revisar sus conclusiones | I | I | I | R/A | I
Revisión trimestral de permisos | I | S | S | I | R/A
```

"Revisar sus conclusiones" pasó de cinco C (nadie revisaba) a una R/A en SRE, que es quien actúa sobre la alerta.

### Dos aprobadores para el texto al destinatario

**Situación:** producto y legal aprueban por separado los mensajes que el asistente envía a destinatarios y piden cambios contradictorios. El lanzamiento se demora una semana.

**Qué se hace:** producto queda como A y legal como C, con dos días hábiles para responder. Si legal detecta un problema de privacidad, bloquea; si es una preferencia de redacción, decide producto. La regla queda escrita en la matriz.

### ¿Quién responde por lo que hizo el agente?

**Situación:** el asistente reprogramó 14 entregas de un comercio porque interpretó mal una nota del pedido. En la reunión, cada equipo aclara que "el agente lo hizo solo".

**Qué se hace:** el agente es R pero nunca A: la tech lead del asistente es A de "reprogramar entregas desde el asistente", coordina la respuesta al comercio y el postmortem. Se agrega la fila "aprobar herramientas con escritura", con seguridad como C, y la reprogramación pasa a requerir confirmación del destinatario (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

## Errores comunes

- **Más de una A por fila.** Equivale a ninguna; se elige una persona y las demás pasan a C o S.
- **Equipos en lugar de roles concretos.** "Plataforma" como A diluye la responsabilidad; se nombra el rol y quién lo ocupa hoy.
- **Llenar de C por cortesía.** Cada C agrega una conversación; quien solo necesita enterarse es I.
- **Confundir C con S.** Si un equipo va a dedicar horas, es S y su capacidad entra en el plan.
- **Darle la A a un agente o al proveedor del modelo.** El agente ejecuta; la responsabilidad es de una persona.
- **Armarla una vez y no volver a mirarla.** Se revisa cuando cambia el equipo, el alcance o aparece una herramienta nueva para el agente.

## Para discutir en equipo

- ¿Qué decisión de los últimos meses se demoró porque no estaba claro quién la tomaba?
- ¿Quién es hoy la A de los prompts, del golden set y de cada herramienta de nuestros agentes?
- ¿Hay algún rol con tantas A que se volvió un cuello de botella?
- ¿Quién está de guardia cuando un agente empieza a responder mal sin que nada se caiga?
- ¿Cómo dejamos registro de quién aprobó un cambio generado por un agente de código?
