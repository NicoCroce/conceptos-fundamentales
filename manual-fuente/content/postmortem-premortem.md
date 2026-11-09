---
slug: postmortem-premortem
titulo: Postmortem y premortem
resumen: Cómo aprender de un incidente con un postmortem sin culpas y cómo anticipar fracasos con un premortem, incluidos los de sistemas con agentes.
lectura: 14
---

## La idea central

Un **postmortem** mira hacia atrás: algo salió mal y el equipo quiere entender qué condiciones lo hicieron posible y qué cambiar para que no se repita. Un **premortem** mira hacia adelante: el proyecto todavía no empezó, y el equipo imagina que ya fracasó para descubrir por qué. Son la misma pregunta («¿qué hizo que esto fallara?») en dos momentos distintos, y las dos dependen de lo mismo: que la gente pueda decir lo que vio sin miedo a quedar señalada.

El tema de [on-call](#t/on-call) cubre cómo se responde a un incidente mientras ocurre. Este empieza cuando terminó: si merece un postmortem, cómo se escribe, cómo se conduce la reunión y, sobre todo, cómo se logra que las acciones se cumplan, que es donde fracasa la mayoría. La segunda mitad cubre el premortem como ejercicio de facilitación. Con agentes en producción, las dos prácticas cambian un poco: el «quién hizo qué» incluye a un modelo, una versión de prompt y una cadena de llamadas a herramientas.

## Conceptos

### Cuándo se escribe un postmortem

Escribir un postmortem por cada alerta agota al equipo; no escribir ninguno garantiza repetir errores. Los criterios se fijan de antemano:

- **Siempre:** incidentes SEV1 y SEV2, cualquier exposición de datos personales y cualquier acción equivocada de un agente sobre datos o clientes reales, aunque el impacto haya sido chico.
- **A pedido:** SEV3 que se repite (por ejemplo, dos veces en un mes) o que tuvo un rescate heroico, y cualquier caso que alguien del equipo o de soporte pida revisar.
- **Casi incidentes (near misses):** algo que pudo causar daño y no lo hizo por suerte o porque una barrera tardía lo frenó. Son baratos de analizar porque nadie está bajo presión, y enseñan lo mismo que el incidente que no fue.

Para los casos menores alcanza un **postmortem liviano**: una página, sin reunión, con resumen, causa y dos o tres acciones.

**Ejemplo:** en un trimestre, Rumbo tiene 2 SEV1, 5 SEV2 y 21 SEV3. Se escriben 7 postmortems completos, 3 livianos por SEV3 repetidos y 2 por casi incidentes: uno de ellos, una migración que habría borrado la tabla de zonas y que se frenó solo porque el entorno de staging tenía otro nombre de esquema.

**Por qué importa:** con criterios escritos nadie discute si «vale la pena»; y los casi incidentes dan las lecciones más baratas que existen.

### Sin culpas: qué significa y por qué funciona

Un postmortem **sin culpas** (blameless) asume que las personas actuaron de forma razonable con la información, el tiempo y las herramientas que tenían. La pregunta deja de ser «¿quién se equivocó?» y pasa a ser «¿qué hizo que esa decisión pareciera correcta en ese momento?».

Funciona por tres razones:

1. **Información:** si señalar a alguien tiene consecuencias, la gente omite detalles, y los detalles son justamente lo que explica el incidente.
2. **Sesgo retrospectivo:** después de conocer el final, todo parece obvio. «Era evidente que el job estaba fallando» es fácil de decir cuando ya se sabe que falló; a las 3 a.m., entre 40 alertas, no lo era.
3. **Efectividad:** «tener más cuidado» no es una acción. Cambiar un sistema para que el mismo error no tenga el mismo efecto sí lo es.

Sin culpas no significa sin responsabilidad: cada acción tiene un dueño que responde por cumplirla. Lo que desaparece es el castigo por estar de guardia cuando el sistema falló.

**Ejemplo:** en la reunión, alguien pregunta «¿por qué no revisaste el dashboard de frescura?». El facilitador lo reformula: «¿qué información tenías a mano en ese momento y qué te hizo mirar primero el despliegue?». La respuesta revela que el dashboard de frescura no existía para esa feature.

**Por qué importa:** la calidad de un postmortem depende de lo que la gente se anima a contar; el tono es un requisito técnico, no cortesía.

### La estructura del documento

Un buen postmortem se lee en cinco minutos y se entiende sin haber estado en el incidente. El **impacto va con números**, la **línea de tiempo** cita sus fuentes y las **acciones** tienen responsable, fecha y ticket. En lugar de una única causa raíz se habla de **factores contribuyentes**: los incidentes reales casi siempre combinan varias condiciones.

```markdown
# Postmortem: <qué pasó, en una línea>
Severidad: SEV<n> · Fecha: <fecha> · Estado: borrador | revisado | cerrado
Autores: <personas> · Facilitador: <persona>

## Resumen (máximo 5 oraciones)
Qué pasó, a quién afectó, cuánto duró, cómo se mitigó.

## Impacto
- Usuarios o pedidos afectados: <n>
- Duración del impacto: <inicio> a <fin> (<min>)
- Tiempo hasta detectar: <min> · hasta mitigar: <min>

## Línea de tiempo (hora UTC, fuente)
| Hora | Evento | Fuente |
|---|---|---|

## Factores contribuyentes
## Qué funcionó bien
## Qué funcionó mal
## Dónde tuvimos suerte
## Acciones
| Acción | Tipo (prevenir / detectar / mitigar) | Responsable | Fecha | Ticket |
|---|---|---|---|---|
```

**Ejemplo:** en Rumbo, la feature de tráfico del modelo de ETA dejó de actualizarse durante 6 horas. Impacto: 3.400 pedidos de la zona centro con ETA subestimada en 25 minutos en promedio y 410 reclamos a soporte. El análisis de factores, hecho con [5 porqués](#t/cinco-porques):

```porques
titulo: ETA subestimada en la zona centro
problema: 3.400 pedidos con ETA subestimada
La feature de tráfico llegó 6 h tarde
El job de ingesta dejó de escribir datos
La credencial del proveedor rotó y falló
El job reportaba éxito sin escribir nada
Nadie medía la frescura de esa feature
causa: Sin control de frescura de features
accion: Alerta de frescura y job que falle
```

La sección «dónde tuvimos suerte» anotó que el incidente ocurrió un martes de poca demanda: un viernes habría triplicado los pedidos afectados.

**Por qué importa:** «dónde tuvimos suerte» es la sección que más se omite y la que mejor muestra el riesgo real; el impacto en números evita que el incidente se recuerde como «algo con las ETAs».

### La reunión de revisión

El documento se escribe antes de la reunión, no durante. La reunión sirve para validar la línea de tiempo, completar factores y acordar acciones. Dura **45 a 60 minutos** y se hace dentro de los 5 días hábiles posteriores, mientras la memoria está fresca.

Participan quienes respondieron al incidente, los dueños de los sistemas involucrados, un **facilitador** que no haya participado (para que pueda preguntar sin defender decisiones propias) y, si el impacto fue visible, alguien de soporte o producto. Más de 10 personas la convierte en una presentación.

Agenda típica de 50 minutos:

1. Recordar la regla sin culpas y el objetivo (2 min).
2. Recorrer la línea de tiempo y corregirla (15 min).
3. Factores contribuyentes: preguntar «¿qué más tuvo que ser cierto para que esto pasara?» (15 min).
4. Qué funcionó, qué no y dónde tuvimos suerte (8 min).
5. Acciones: priorizar, asignar responsable y fecha (10 min).

**Ejemplo:** en la revisión del incidente de tráfico, la persona de guardia cuenta que dos días antes silenció una alerta de «job lento» porque saltaba seguido. Ese dato no estaba en el borrador y suma una acción: revisar las alertas ruidosas del pipeline.

**Por qué importa:** el borrador refleja lo que vio quien lo escribió; la reunión junta las versiones de todos.

### Seguimiento de acciones: donde fallan casi todos

Un postmortem sin acciones cumplidas es solo un relato. El patrón más común es conocido: la reunión termina con 8 acciones, 2 se hacen la semana siguiente y el resto queda en un documento que nadie vuelve a abrir, hasta que el mismo incidente se repite.

Prácticas que ayudan:

- **Pocas acciones y buenas:** 3 a 5, con una clasificada como prioritaria. Una acción es concreta, verificable y tiene dueño individual.
- **En el backlog real**, con ticket, no en el documento.
- **Medir la tasa de cierre:** porcentaje de acciones cerradas en la fecha comprometida, revisado cada mes. Las prioritarias deberían cerrar en semanas, no en trimestres.
- **Cerrar el postmortem** solo cuando sus acciones prioritarias están hechas.

**Ejemplo:** en un trimestre se comprometieron 34 acciones; a los 60 días había 15 cerradas, un 44 %. Ninguna de las 6 acciones de «detectar» estaba cerrada. El equipo reserva un 10 % de cada sprint para acciones de postmortem y al trimestre siguiente la tasa sube al 78 %.

**Por qué importa:** la tasa de cierre es el indicador más honesto de si el equipo aprende de sus incidentes o solo los documenta.

### Compartir lo aprendido

Lo que un equipo aprendió suele servirle a otro. Formas simples: un repositorio de postmortems con etiquetas (servicio, tipo de causa, agente sí o no), una revisión mensual de 30 minutos con el caso más interesante y usar incidentes pasados como escenarios de game days.

**Ejemplo:** al etiquetar 30 postmortems del año, aparecen 5 con el factor «credencial rotada sin aviso a los consumidores». Ningún equipo lo había visto como patrón; se convierte en un proyecto de plataforma.

**Por qué importa:** los patrones solo se ven cuando los postmortems están juntos y se pueden comparar.

### Postmortem de un incidente con agentes

Cuando el error lo cometió un agente, la línea de tiempo necesita datos que no están en un log tradicional: la **traza** de la conversación con cada llamada a herramienta y sus parámetros, la **versión del prompt** y del modelo, el **contexto recuperado** (documentos, notas del pedido), y las **aprobaciones**: qué pidió confirmación, a quién y qué respondió. Si esos datos no se guardan, el postmortem se convierte en especulación. Ver [OpenTelemetry y tracing](#t/opentelemetry) para instrumentar esas trazas.

El enfoque sin culpas se extiende al agente: «el modelo alucinó» no es un factor contribuyente útil, igual que «la persona se equivocó». La pregunta es qué permitió que esa salida tuviera ese efecto: permisos demasiado amplios, una confirmación salteada, una evaluación que no cubría el caso.

**Ejemplo:** el asistente de soporte reprogramó 37 entregas que nadie había pedido reprogramar. La traza muestra que una nueva versión del prompt, desplegada a las 10:05, interpretaba «¿se puede cambiar el horario?» como un pedido de cambio y llamaba a la herramienta `reprogramar_entrega`. El paso de confirmación existía en la interfaz web, pero el canal de mensajería lo salteaba. Factores: la confirmación vivía en el cliente y no en la herramienta; el golden set no tenía preguntas hipotéticas; el despliegue del prompt no pasó por canary.

**Por qué importa:** con agentes, la reconstrucción depende de la observabilidad que se diseñó antes del incidente.

### Un LLM para el borrador de la línea de tiempo

Armar la línea de tiempo a mano desde el canal del incidente, los logs y los despliegues puede llevar dos horas. Un LLM produce un borrador en minutos con una instrucción clara: una fila por evento, hora UTC, la fuente de cada fila y nada que no esté en las fuentes.

El borrador se verifica entrada por entrada. Los errores típicos son mezclar husos horarios, inventar una hora plausible cuando la fuente no la tiene, convertir una hipótesis del chat («quizás es el deploy») en un hecho, y colar lenguaje que culpa («Juan olvidó…»). Además, antes de pasar logs al modelo hay que quitar datos personales de destinatarios.

**Ejemplo:** el LLM arma 42 filas desde 600 mensajes del canal y los eventos de despliegue. La revisión corrige 5: dos horarios en hora local, una hipótesis presentada como causa y dos eventos sin fuente que se eliminan.

**Por qué importa:** el LLM ahorra el trabajo mecánico, pero la línea de tiempo es la base del análisis; un error ahí se propaga a los factores y a las acciones.

### El premortem

El premortem invierte la pregunta: «Pasaron seis meses y el proyecto fracasó. ¿Qué pasó?». Al darlo por hecho, el pesimismo deja de ser una opinión incómoda y se vuelve la consigna, y las explicaciones salen más concretas que con «¿qué podría salir mal?».

Facilitación paso a paso, en unos 60 minutos:

1. **Contexto** (5 min): qué se va a lanzar, para cuándo y qué significa éxito.
2. **Consigna** (1 min): «Es seis meses después. Fracasó. Escribe la historia de por qué».
3. **Escritura en silencio** (10 min): cada persona por separado, una razón por nota. El silencio evita que la primera idea ancle al resto.
4. **Ronda** (15 min): cada persona lee una razón por turno, hasta agotar las notas. El líder del proyecto habla último.
5. **Agrupar** (10 min): se juntan razones parecidas por afinidad.
6. **Elegir** (5 min): votación con 3 votos por persona para los más probables o graves.
7. **Mitigar** (15 min): para los 3 a 5 más votados, una acción concreta con responsable, o la decisión explícita de aceptarlo.

**Ejemplo:** 9 personas, 61 notas, 11 grupos. Los cuatro más votados se convierten en acciones del plan antes del lanzamiento.

**Por qué importa:** da permiso para decir lo que todos piensan y nadie dice, en particular las personas con menos jerarquía.

### Cuándo correr un premortem y en qué se diferencia del registro de riesgos

Conviene antes de un compromiso difícil de deshacer: un lanzamiento a clientes, una migración, la firma de un plazo con un comercio grande, darle a un agente permisos de escritura. Más tarde pierde valor, porque las decisiones ya están tomadas.

El premortem **genera** riesgos; el registro de riesgos los **gestiona** a lo largo del tiempo, con probabilidad, impacto, disparador y revisión periódica. El resultado de un premortem alimenta el registro descrito en [Gestión y medición de riesgos](#t/riesgos); no lo reemplaza.

| | Postmortem | Premortem | Retrospectiva |
|---|---|---|---|
| Momento | Después de un incidente | Antes de un proyecto o lanzamiento | Al final de cada iteración |
| Pregunta | ¿Qué hizo posible esto? | ¿Por qué fracasaría? | ¿Qué cambiamos en cómo trabajamos? |
| Disparador | Severidad o casi incidente | Compromiso grande | Calendario fijo |
| Salida | Documento con acciones | Riesgos y mitigaciones | Uno o dos acuerdos de equipo |
| Foco | Sistema técnico y proceso | Plan y supuestos | Dinámica del equipo |

**Ejemplo:** el premortem del lanzamiento produce 11 riesgos; 6 entran al registro con puntuación y responsable, y el resto se acepta explícitamente.

**Por qué importa:** confundirlos lleva a hacer un premortem y creer que los riesgos ya están gestionados.

### Premortem de una función con agentes

Al lanzar una función con agentes, ciertas historias de fracaso aparecen casi siempre. Conviene tenerlas a mano, pero leerlas recién después de la escritura en silencio:

- **Alucinación frente al cliente:** el asistente le promete a un comercio una franja de entrega que no existe y el caso llega a dirección.
- **Costo descontrolado de tokens:** un bucle de reintentos o conversaciones larguísimas multiplican el gasto por diez en una semana.
- **Inyección de prompts por notas del pedido:** un texto en las notas le da instrucciones al agente y este actúa sobre pedidos ajenos.
- **Baja adopción:** el asistente funciona, pero los operadores no confían en él y siguen con el proceso anterior.

**Ejemplo:** en el premortem de «reprogramar desde el chat», la historia más votada no fue técnica: «los comercios desactivaron la función porque sus clientes reprogramaban demasiado». Se agrega un límite configurable por comercio y una métrica de reprogramaciones por pedido.

**Por qué importa:** en funciones con agentes, los fracasos de producto y de seguridad pesan tanto como los técnicos.

## Casos prácticos

### Un casi incidente que nadie quería documentar

**Situación:** en el canary de un prompt nuevo del asistente, una revisión de trazas detecta que el modelo incluía el teléfono del destinatario en el resumen enviado al proveedor. Se revirtió en 20 minutos, sin impacto, y alguien opina que «no hace falta postmortem».

**Qué se hace:** se aplica el criterio escrito: cualquier posible exposición de datos personales lleva postmortem. Se hace uno liviano. El factor principal es que el prompt nuevo pedía «todos los datos útiles del caso» y la redacción de datos personales se aplicaba después del modelo, no antes. Acción prioritaria: redactar en origen, antes de construir el prompt.

### Las acciones que no se hicieron

**Situación:** en febrero, la asignación se degrada por un pool de conexiones agotado en Aurora. En junio vuelve a pasar. El postmortem de febrero tenía la acción «alerta de saturación del pool», sin ticket.

**Qué se hace:** el segundo postmortem tiene un solo factor nuevo: la acción anterior no se hizo. El equipo empieza a medir la tasa de cierre en la reunión mensual de operaciones, exige ticket para cada acción y no cierra un postmortem hasta completar las prioritarias.

### Premortem antes de dar permisos de escritura a un agente

**Situación:** el agente interno de operaciones solo tiene herramientas de lectura. Se propone darle una herramienta para reasignar pedidos entre transportistas en incidentes de zona.

**Qué se hace:** premortem de 60 minutos con operaciones, plataforma y seguridad. Las historias más votadas: el agente reasigna en masa por una métrica mal leída, y nadie puede reconstruir después por qué lo hizo. Mitigaciones: tope de 20 reasignaciones por ejecución, aprobación humana por encima de ese tope y traza completa con versión de prompt y aprobaciones. Los riesgos pasan al registro y la herramienta se lanza primero en modo sugerencia.

## Errores comunes

- **Buscar una única causa raíz.** Los incidentes reales combinan varios factores; quedarse con uno deja los demás intactos.
- **Acciones como «tener más cuidado».** Una acción cambia el sistema, es verificable y tiene dueño y fecha.
- **Acciones fuera del backlog.** Si no tienen ticket y seguimiento, no se hacen; se mide la tasa de cierre.
- **Reunión sin borrador previo.** Se gasta la hora reconstruyendo la línea de tiempo en lugar de analizarla.
- **Aceptar el borrador del LLM sin verificar.** Cada fila de la línea de tiempo debe citar su fuente.
- **Premortem con el líder hablando primero.** Ancla al grupo; se escribe en silencio y el líder lee último.

## Para discutir en equipo

- ¿Cuál es nuestra tasa de cierre de acciones de postmortem en el último trimestre?
- ¿Qué casi incidentes recientes no documentamos y qué nos habrían enseñado?
- Si un agente actuara mal mañana, ¿tenemos las trazas, versiones de prompt y aprobaciones para reconstruirlo?
- ¿Qué lanzamiento próximo merece un premortem y quién lo facilitaría?
- ¿Nuestros postmortems se leen como búsqueda de culpables? ¿Qué frases lo delatan?
