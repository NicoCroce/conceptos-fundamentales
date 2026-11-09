---
slug: prd
titulo: PRD: documento de requisitos de producto
resumen: Un documento que define qué problema se resuelve, para quién, con qué metas y requisitos, antes de decidir cómo construirlo.
lectura: 13
---

## La idea central

Un **PRD** (*product requirements document*, documento de requisitos de producto) responde una pregunta antes que cualquier otra: **qué problema vamos a resolver, para quién y cómo sabremos que lo resolvimos**. No dice qué base de datos usar ni cómo se llaman los endpoints; eso viene después, en el RFC y en la especificación. Su trabajo es que producto, ingeniería, diseño, soporte y seguridad lean lo mismo y lleguen a la misma idea de "terminado".

La analogía útil es el encargo a un arquitecto: "una casa para cinco personas, ampliable y sin escaleras". El encargo no dibuja planos, pero descarta muchos. Con funcionalidades basadas en LLMs el PRD gana peso, porque "que responda bien" no es un requisito: hay que escribir qué es bien, qué pasa cuando responde mal, cuánto puede costar cada conversación y qué acciones nunca puede tomar el agente solo.

## Conceptos

### Qué es un PRD y quién lo usa

Un PRD es un documento corto, versionado y compartido, que describe una funcionalidad o producto desde el lado del problema. Lo escribe normalmente la persona de producto, con ingeniería y diseño como coautores desde el primer borrador. Lo leen ingeniería (para estimar y detectar riesgos técnicos), diseño, soporte y operaciones (para saber qué cambia y cuándo), seguridad y privacidad (para revisar qué datos se tocan) y dirección (para decidir si el problema merece la inversión).

**Ejemplo:** el PRD del "Asistente para transportistas" de Rumbo lo escribe la product manager de la app de transportistas; el tech lead del asistente y una diseñadora lo comentan durante una semana; seguridad revisa la sección de datos y la de acciones permitidas.

**Por qué importa:** si ingeniería ve el PRD por primera vez cuando ya está "aprobado", las restricciones técnicas llegan tarde y se negocian con el calendario encima.

### Primero el problema

La sección más importante es el **enunciado del problema**: qué pasa hoy, a quién le pasa y con qué evidencia. Un buen enunciado tiene tres partes:

1. **Quién tiene el problema**, lo más concreto posible ("transportistas de reparto en moto, en su primera semana").
2. **Qué les pasa**, con números ("llaman a soporte 2,3 veces por jornada para preguntar dónde retirar").
3. **Evidencia**, que puede ser datos de uso, tickets, entrevistas o un experimento previo.

Un enunciado que empieza con la solución ("necesitamos un chatbot") salta el paso donde se decide si un chatbot es la mejor respuesta.

**Ejemplo:** "Los transportistas generan unas 9.000 consultas diarias a soporte (cifras hipotéticas). El 62% son preguntas sobre su propio pedido (dirección de retiro, horario, estado) que ya están en los sistemas de Rumbo. La espera media es de 11 minutos, durante los cuales el transportista suele estar detenido".

**Por qué importa:** si el problema está bien escrito, varias soluciones distintas pueden competir; si está mal escrito, se evalúa la solución contra sí misma.

### Metas, no-metas y métricas de éxito

Las **metas** dicen qué cambia si la funcionalidad funciona. Las **no-metas** dicen qué queda explícitamente fuera, aunque parezca relacionado. Las **métricas de éxito** convierten las metas en números con fecha, idealmente siguiendo la forma de [objetivos SMART](#t/objetivos-smart).

Conviene separar tres tipos de métrica:

- **Métrica principal:** la que define el éxito. Una sola.
- **Métricas de soporte:** explican por qué se movió la principal.
- **Métricas de protección** (*guardrails*): las que no pueden empeorar.

**Ejemplo:** métrica principal: bajar las consultas a soporte por transportista de 2,3 a 1,2 por jornada en 90 días desde el lanzamiento. Soporte: tasa de resolución sin derivar (objetivo 75%). Protección: tasa de respuestas con horario o dirección incorrectos por debajo de 0,5%. No-meta: que el asistente atienda a destinatarios o comercios.

**Por qué importa:** sin métrica de protección, se puede "ganar" la principal con un asistente que contesta todo con seguridad, incluso lo que no sabe.

### Usuarios, casos de uso e historias de usuario

Después del problema se describen los usuarios (perfiles con contexto: qué dispositivo usan, en qué situación, con qué conocimiento) y los **casos de uso** principales. Una forma compacta son las historias de usuario: "Como transportista, quiero saber a qué hora abre el depósito de retiro para no esperar en la puerta".

Las historias sirven para conversar, pero un PRD también necesita los **casos borde** que cambian el diseño: el transportista sin conexión, el pedido reasignado a mitad de camino, la consulta por un pedido ajeno.

**Ejemplo:** el PRD lista los casos de uso por volumen: dirección y horario de retiro (38% de las consultas), estado del pedido (14%), contacto del comercio (6%), cambio de ventana horaria (3%).

**Por qué importa:** los porcentajes ordenan el trabajo y justifican qué queda para después.

### Requisitos funcionales y no funcionales, con prioridad

Los **requisitos funcionales** describen comportamiento observable: qué puede hacer el usuario y qué responde el sistema. Los **no funcionales** describen cualidades: latencia, disponibilidad, accesibilidad, idiomas, retención de datos. Ambos deben ser comprobables; "rápido" no lo es, "primera respuesta en menos de 3 segundos en el p95" sí.

Cada requisito lleva una prioridad. Lo habitual es **MoSCoW** (Must, Should, Could, Won't), que se explica en [Herramientas de priorización](#t/priorizacion). El PRD no es una lista de deseos: si todo es Must, nada lo es.

**Ejemplo:** R1 (Must): responder dirección y horario de retiro de un pedido asignado al transportista que pregunta. R7 (Won't en v1): reasignar pedidos desde el chat. RNF2 (Must): funcionar con conexión 3G intermitente, con reintentos que no dupliquen acciones.

**Por qué importa:** la prioridad es lo que permite recortar sin renegociar el documento entero cuando el calendario aprieta.

### Alcance, preguntas abiertas, dependencias y riesgos

Tres secciones que se suelen omitir:

- **Fuera de alcance:** lo que se pidió o se imaginó y no entra. Distinto de las no-metas: una no-meta es un resultado que no se persigue; fuera de alcance es una funcionalidad que no se construye ahora.
- **Preguntas abiertas:** lo que todavía no se sabe, con dueño y fecha. Un PRD sin preguntas abiertas suele esconderlas.
- **Dependencias y riesgos:** otros equipos, datos que hay que conseguir, proveedores, aprobaciones legales. El detalle de riesgos se trabaja con las técnicas de gestión de riesgos (registro, mapa de calor, premortem).

**Ejemplo:** pregunta abierta: "¿El horario de depósito lo carga el comercio o lo infiere Rumbo? Dueño: operaciones, para el 14/3".

**Por qué importa:** lo que no se escribe como fuera de alcance o como pregunta abierta aparece igual, pero tarde y como sorpresa.

### Plan de lanzamiento de alto nivel

El PRD no planifica sprints, pero sí dice **cómo se va a exponer la funcionalidad**: piloto, porcentaje de usuarios, zonas, criterios para avanzar y para volver atrás. El detalle técnico del rollout vive en el RFC.

**Ejemplo:** fase 1, 200 transportistas de zona norte durante 3 semanas; se avanza a fase 2 (toda la ciudad) si la resolución sin derivar supera 65% y las respuestas incorrectas quedan por debajo de 0,5%; si se superan 2 incidentes de datos de otro transportista, se apaga.

**Por qué importa:** fijar los criterios de avance antes del piloto evita leer los resultados a conveniencia.

### Secciones extra para funcionalidades con LLMs y agentes

Un PRD de una funcionalidad con LLM necesita cinco secciones que un PRD clásico no tiene:

1. **Nivel de calidad y conjunto de evaluación.** Qué casos se evalúan, cuántos, con qué criterio y qué puntaje mínimo habilita el lanzamiento. Es el mismo conjunto que después corre en cada cambio de prompt o de modelo.
2. **Comportamiento ante fallas y derivación a una persona.** Qué hace el asistente cuando no sabe, cuando la herramienta falla o cuando detecta enojo; en cuánto tiempo responde una persona.
3. **Presupuesto de costo por interacción.** Un techo por conversación, por ejemplo USD 0,02 hipotéticos, que condiciona el modelo, el contexto y la cantidad de llamadas a herramientas.
4. **Datos y privacidad.** Qué datos ve el modelo, cuáles se guardan, por cuánto tiempo, y si salen hacia un proveedor externo.
5. **Restricciones de seguridad del agente.** Qué herramientas puede usar, cuáles son de solo lectura y **qué acciones requieren aprobación humana** antes de ejecutarse.

**Ejemplo:** en el asistente para transportistas, el agente puede consultar pedidos del propio transportista (solo lectura) y proponer un cambio de ventana horaria, pero el cambio lo confirma el comercio. Nunca ve el teléfono del destinatario.

**Por qué importa:** son decisiones de producto. Si el PRD no las toma, las toma un ingeniero apurado o, peor, el agente.

### Plantilla compacta con un ejemplo

```markdown
# PRD: Asistente para transportistas (v1)
Dueña: PM app transportistas · Coautores: tech lead asistente, diseño
Estado: en revisión · Última actualización: 2026-03-02

## Problema
~9.000 consultas diarias a soporte; 62% son sobre el propio pedido.
Espera media 11 min con el transportista detenido. (Cifras hipotéticas.)

## Metas / No-metas
- Meta: resolver sin espera las consultas sobre el propio pedido.
- No-meta: atender a destinatarios o comercios.

## Métricas de éxito (90 días)
- Principal: consultas a soporte por transportista 2,3 -> 1,2 por jornada.
- Soporte: resolución sin derivar >= 75%.
- Protección: respuestas con dato incorrecto < 0,5%.

## Requisitos
- R1 Must: dirección y horario de retiro del pedido asignado.
- R2 Must: derivar a una persona en menos de 2 min si no sabe.
- R7 Won't (v1): reasignar pedidos o cambiar estados.
- RNF1 Must: primera respuesta < 3 s (p95).

## Calidad y evaluación
300 conversaciones reales anonimizadas; lanzar con >= 90% correctas
y 0 casos de datos de otro transportista.

## Fallas y derivación
Herramienta caída -> lo dice y deriva. Dos respuestas sin resolver -> deriva.

## Costo
Techo hipotético de USD 0,02 por conversación (p90).

## Datos y seguridad del agente
Solo lectura sobre pedidos del transportista autenticado.
Sin acceso a teléfono ni nombre del destinatario.
Cambio de ventana: el agente propone, el comercio aprueba.

## Fuera de alcance
Voz, otros idiomas, documentación del vehículo.

## Preguntas abiertas
- ¿Quién carga el horario del depósito? (operaciones, 14/3)

## Dependencias
API de pedidos sin horario para transportistas.

## Lanzamiento
Piloto 200 transportistas zona norte, 3 semanas; criterios de avance arriba.
```

**Ejemplo:** la plantilla entra en dos pantallas y cada requisito tiene un identificador (R1, RNF1) que después citan el RFC, las especificaciones y los casos de evaluación.

**Por qué importa:** con identificadores estables, un cambio en el PRD se puede rastrear hasta el código y los tests que afecta.

### PRD liviano o pesado, vivo o congelado

Un **PRD liviano** (una página: problema, metas, métricas, Must, fuera de alcance) alcanza para una mejora acotada. Un **PRD completo** se justifica con varios equipos, datos personales, un agente con herramientas o meses de inversión.

¿Documento **vivo** o **congelado**? Un punto intermedio: vivo hasta el lanzamiento, con cada cambio de meta, métrica o requisito Must anotado en un registro de cambios con fecha y motivo; después se congela y la versión siguiente es un PRD nuevo.

**Ejemplo:** a mitad del desarrollo se descubre que el 30% de los comercios no tiene horario de depósito. R1 cambia a "horario cuando exista; si no, decirlo", el registro lo anota y la evaluación suma 40 casos sin horario.

**Por qué importa:** un PRD editado sin registro hace que dos personas defiendan versiones distintas de "lo acordado".

### PRD, RFC, especificación y ADR

Cuatro documentos que comparten secciones y se confunden. Los separa la pregunta que responde cada uno.

| Documento | Quién lo escribe | Cuándo | Qué pregunta responde |
|---|---|---|---|
| PRD | Producto, con ingeniería y diseño | Antes de decidir construir | ¿Qué problema, para quién, y cómo sabremos que funcionó? |
| RFC o design doc | Ingeniería, con revisión de pares | Después del PRD, antes de implementar cambios grandes | ¿Cómo lo construimos y qué alternativas descartamos? |
| Especificación (SDD) | Ingeniería, con ayuda del agente | Antes y durante cada funcionalidad | ¿Qué comportamiento exacto y qué criterios de aceptación cumple el código? |
| ADR | Quien tomó la decisión | Al cerrar una decisión técnica | ¿Qué se decidió, por qué y cuándo revisarlo? |

**Ejemplo:** el PRD del asistente justifica el trabajo; el [RFC](#t/rfc) del gateway de LLM discute el cómo; dos ADRs registran lo decidido; y las especificaciones de [SDD](#t/sdd) bajan todo a criterios que un agente de código implementa y verifica.

**Por qué importa:** cuando cada documento responde su pregunta, ninguno se infla con el debate de otro.

### Un LLM como crítico del PRD y traductor a especificaciones

Un LLM ayuda en dos momentos:

- **Para criticar el borrador.** Se le da el PRD y se le pide que liste ambigüedades ("¿qué cuenta como 'pedido asignado' si fue reasignado?"), casos borde ausentes, requisitos no comprobables, contradicciones entre secciones y métricas que se podrían ganar con trampa. Funciona mejor con un formato de salida concreto (sección, problema, pregunta sugerida) que pidiendo "mejora este documento".
- **Para derivar especificaciones.** Con el PRD aprobado, el LLM propone una especificación por requisito con criterios de aceptación, que una persona revisa antes de entregarla a un agente de código.

En ambos casos el PRD no lleva datos personales reales, y lo que el LLM agrega se revisa: tiende a inventar requisitos razonables que nadie pidió.

**Ejemplo:** el LLM señala que R2 dice "derivar si no sabe" sin definir "no sabe", y que la métrica principal mejora si el asistente desalienta a los transportistas de contactar soporte. Las dos observaciones llevan a cambios.

**Por qué importa:** una ambigüedad en el PRD se multiplica: el agente de código la resuelve de una manera y soporte de otra.

## Casos prácticos

### Un PRD que empezaba por la solución

**Situación:** llega un PRD titulado "Chatbot con LLM para comercios", sin datos de tickets ni métrica principal.

**Qué se hace:** ingeniería pide reescribir el problema con evidencia antes de estimar. Al revisar tickets aparece que el 70% de las consultas de comercios son sobre el estado de pedidos con más de 2 horas de demora. Un aviso proactivo de demora, sin LLM, resuelve buena parte; el asistente queda como fase 2 para las consultas abiertas. El PRD se reescribe con dos alternativas y la métrica "consultas por pedido demorado".

### Un requisito que el agente interpretó a su manera

**Situación:** el PRD del asistente decía "el asistente puede ayudar a cambiar la ventana horaria". La especificación derivada por un LLM, aprobada con prisa, implementó una herramienta que cambiaba la ventana directamente. En staging, el agente cambió ventanas sin consultar al comercio.

**Qué se hace:** se corrige el PRD en la sección de seguridad del agente: "el agente propone; el comercio aprueba; ninguna escritura sin aprobación". La especificación se regenera, se agrega un criterio comprobable y un caso de evaluación donde el transportista insiste. La lección queda como regla: toda acción con efectos en otros actores se nombra en el PRD con su nivel de aprobación.

### Un PRD sin presupuesto de costo

**Situación:** el piloto cumple las métricas de calidad, pero el costo real ronda USD 0,09 por conversación (cifra hipotética): el agente recupera el historial completo del transportista en cada turno. A escala, el número no cierra.

**Qué se hace:** se agrega al PRD el techo de USD 0,02 por conversación en el p90 como requisito Must, con su métrica en el tablero. Ingeniería propone en el RFC acotar el contexto a los pedidos del día y usar un modelo más chico para clasificar la intención. El lanzamiento general exige cumplir calidad y costo a la vez.

## Errores comunes

- **Empezar por la solución.** Un PRD que nombra la tecnología en el título suele saltear el problema; se escribe primero quién sufre qué y con qué evidencia.
- **Métricas sin protección.** Una métrica principal sola se puede ganar empeorando la experiencia; se agrega al menos una métrica que no puede empeorar.
- **Todo es Must.** Sin prioridades reales no hay forma de recortar; si los Must superan el tiempo disponible, el PRD todavía no está listo.
- **Omitir las secciones de LLM.** Calidad, fallas, costo, datos y acciones con aprobación son decisiones de producto; si faltan, las decide el código.
- **Editar sin registro.** Cada cambio de meta o requisito Must se anota con fecha y motivo.
- **Confundir PRD con especificación.** Si aparecen tablas y endpoints, el PRD está decidiendo el cómo sin el debate técnico.

## Para discutir en equipo

- ¿Qué funcionalidad reciente habría cambiado si su PRD hubiera tenido una métrica de protección?
- ¿Qué acciones de nuestros agentes deberían requerir aprobación humana y dónde está escrito hoy?
- ¿Cuándo alcanza un PRD de una página y cuándo exigimos uno completo?
- ¿Quién mantiene el registro de cambios del PRD y cómo se entera ingeniería de cada cambio?
- ¿Usaríamos un LLM para revisar nuestros PRDs? ¿Qué le pediríamos exactamente y cómo mediríamos si ayuda?
