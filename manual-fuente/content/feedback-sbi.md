---
slug: feedback-sbi
titulo: Cómo dar feedback: el modelo SBI
resumen: Cómo dar y recibir feedback útil con el modelo Situación, Comportamiento, Impacto, entre colegas, hacia arriba, con otros equipos y con agentes de código.
lectura: 12
---

## La idea central

El **feedback** es información sobre cómo lo que alguien hizo afectó a otros o al resultado, dada para que pueda repetirlo o cambiarlo. Bien dado, es la forma más barata de mejorar: una conversación de cinco minutos puede evitar meses de repetir el mismo error. Mal dado, genera defensas, malentendidos o, peor, nada: la persona escucha "bien en general, algunas cosas a mejorar" y no sabe qué hacer distinto el lunes.

El modelo **SBI** (*Situation, Behavior, Impact*: situación, comportamiento, impacto) es una estructura simple para que el feedback sea concreto. Se nombra cuándo y dónde pasó algo, qué hizo la persona de forma observable y qué efecto tuvo. Funciona igual para reconocer algo bueno que para corregir algo. Y, como se verá, es casi la misma estructura que conviene usar para corregir a un agente de código o ajustar un prompt.

## Conceptos

### Por qué falla el feedback

La mayoría del feedback que no sirve cae en uno de estos patrones:

- **Vago:** "Tienes que comunicar mejor." ¿Mejor cuándo, con quién, cómo?
- **Tardío:** llega meses después, cuando ya no se puede corregir.
- **Sobre la persona y no sobre lo que hizo:** "Eres desordenado" ataca la identidad; la persona se defiende en lugar de escuchar.
- **Escondido en un sándwich:** elogio, crítica, elogio. El mensaje importante se pierde y el elogio pierde valor, porque anuncia una crítica.
- **Sin pedido:** se describe el problema, pero no se dice qué se espera ni se acuerda nada.

**Ejemplo:** en la evaluación semestral, Diego lee "buen año, a veces cuesta seguir tus PRs". No sabe qué PRs ni qué hacer distinto: vago, tardío y sin pedido a la vez.

**Por qué importa:** si el feedback no lleva a una acción concreta, solo deja una sensación, casi siempre negativa.

### SBI paso a paso

1. **Situación:** cuándo y dónde. Ancla la conversación en un momento concreto. "En la revisión de diseño del martes", "en el incidente de anoche en zona norte".
2. **Comportamiento:** qué hizo la persona, en términos que una cámara podría registrar. No "fuiste descuidado", sino "fusionaste el PR sin esperar el resultado de la prueba de latencia".
3. **Impacto:** qué efecto tuvo, en uno mismo, en el equipo, en el sistema o en los usuarios. Es lo que le da sentido al feedback: "el p99 subió a 70 ms durante 40 minutos y se reasignaron 300 pedidos tarde".

La regla de oro del paso 2: si la frase contiene un adjetivo sobre la persona ("desprolijo", "brillante", "lento"), todavía no es un comportamiento.

**Ejemplo:** "En la daily de hoy (S), contaste el bloqueo con la API del transportista antes de que nadie preguntara (B); pudimos reasignar la tarea esa misma mañana (I)."

**Por qué importa:** cada parte se puede verificar, así que se conversa sobre lo que pasó y no sobre opiniones.

### Ejemplos trabajados: de la versión mala a SBI

**Ejemplo:** cuatro casos, cada uno en versión mala y en versión SBI.

*Correctivo, en un incidente:*

- Mal: "Estuviste muy desorganizado en el incidente."
- SBI: "Anoche, durante el incidente del servicio de asignación (S), hiciste tres cambios de configuración seguidos sin avisar en el canal (B). Cuando quisimos entender cuál había bajado la latencia, no pudimos saberlo, y el postmortem quedó con un hueco en la línea de tiempo (I)."

*Positivo, en una revisión de código:*

- Mal: "Buen PR, excelente."
- SBI: "En el PR del cliente de ETA (S), agregaste un test con un servidor lento simulado y una explicación de por qué elegiste 40 ms de timeout (B). Pude revisarlo en diez minutos y ahora ese test nos protege si alguien cambia el valor (I)."

*Correctivo, en una reunión con producto:*

- Mal: "No puedes hablarle así a producto."
- SBI: "En la planning de ayer (S), cuando Lucía propuso la reprogramación desde el chat, dijiste 'eso es una idea absurda' antes de que terminara de explicarla (B). Lucía no volvió a hablar en la reunión y nos quedamos sin entender qué necesitaba el comercio (I)."

*Positivo, con operaciones:*

- Mal: "Gracias por todo, eres lo más."
- SBI: "En la alerta de entregas tardías del viernes (S), adjuntaste al ticket la consulta exacta y los tres pedidos de ejemplo (B). El agente de operaciones y la persona de guardia encontraron la causa en 15 minutos en vez de una hora (I)."

**Por qué importa:** el feedback positivo concreto es tan importante como el correctivo. "Buen trabajo" no enseña nada; decir qué hizo bien y por qué sirvió le dice a la persona qué repetir, y al resto del equipo qué se valora.

### SBI-I: preguntar antes de concluir y cerrar con un acuerdo

SBI describe lo observado, pero el observador no conoce todo el contexto. La variante **SBI-I** agrega una cuarta parte: **intención**, o más precisamente, una pregunta sobre ella. Después del impacto, se pregunta: "¿Qué estabas buscando en ese momento?" o "¿Cómo lo viste tú?".

La respuesta suele cambiar la conversación.

**Ejemplo:** en el caso del incidente, la persona responde: "El canal estaba saturado y el incident commander me había pedido probar rápido". El problema ya no es solo de ella; también es del proceso.

Después de escuchar, se cierra con un **pedido o un acuerdo**: algo concreto que se hará distinto. "¿Te parece si en el próximo incidente cada cambio va con un mensaje de una línea en el canal, aunque sea 'cambio timeout a 60'? Y lo sumo al runbook."

La secuencia completa queda: situación, comportamiento, impacto, pregunta, escucha, acuerdo.

**Por qué importa:** sin la pregunta se corrige a una persona por un problema que a veces es del proceso; sin el acuerdo, nada cambia.

### Momento y canal

- **Correctivo, en privado y sincrónico.** Una llamada o una conversación cara a cara permite ver la reacción, aclarar y preguntar. Por escrito, el feedback correctivo suena más duro de lo que es.
- **Reconocimiento, también en público y por escrito.** Un mensaje en el canal del equipo o en el PR deja registro y muestra qué se valora. Conviene preguntar antes si a la persona le incomoda la exposición.
- **Cerca del hecho.** Idealmente en uno o dos días. Lo bastante pronto para que los detalles estén frescos; lo bastante tarde para no darlo en caliente. En medio de un incidente no se da feedback: se anota y se conversa después.
- **Frecuencia.** Si el feedback aparece solo en la evaluación anual, cada conversación se vuelve un evento. Como hábito semanal, es rutina.

Sobre la proporción entre positivo y correctivo circulan números como "cinco a uno". Conviene tomarlos como orientación, no como fórmula: lo que importa es que el reconocimiento sea frecuente y genuino, de modo que el correctivo llegue a alguien que sabe que su trabajo se ve. Inventar elogios para cumplir una cuota produce el mismo efecto que el sándwich.

**Ejemplo:** después del incidente del martes, la tech lead conversa su comentario correctivo el miércoles en una llamada a solas; el reconocimiento a quien escribió el runbook va al canal del equipo ese mismo día.

**Por qué importa:** el mismo mensaje, en el canal o el momento equivocado, se recibe como castigo.

### Feedforward: hablar del próximo intento

El **feedforward** cambia el foco del pasado al futuro: en lugar de analizar qué salió mal, se sugiere qué probar la próxima vez. Es útil cuando el hecho ya no se puede corregir o cuando la persona pide ideas.

**Ejemplo:** "Para la próxima demo del asistente a un comercio, te sugiero abrir con los números de la evaluación y los casos donde falla, antes de mostrar la conversación de ejemplo." No hay juicio sobre la demo anterior; hay una idea accionable.

**Por qué importa:** hablar del próximo intento genera menos defensa y deja una acción concreta; combina bien con SBI.

### Cómo recibir feedback

Recibir bien depende solo de uno:

1. **Escuchar sin defenderse** hasta que el otro termine.
2. **Aclarar con preguntas.** "¿Me das un ejemplo concreto?" convierte un feedback vago en uno útil.
3. **Agradecer:** dar feedback cuesta.
4. **Decidir.** No todo feedback es correcto; se evalúa con calma. Si no se está de acuerdo, se dice con argumentos (ver [Comunicación asertiva](#t/comunicacion-asertiva)).

**Ejemplo:** ante "tus PRs son difíciles de revisar", Martín responde "gracias, ¿me das un ejemplo?". El problema era la falta de descripción; agrega una plantilla.

**Por qué importa:** quien recibe bien obtiene más feedback, y más concreto.

### Hacia arriba y entre equipos

**Hacia un líder** se usa la misma estructura, con un poco más de cuidado en el marco: pedir el espacio ("¿Tienes diez minutos para un comentario sobre la planning?") y centrarse en el impacto en el trabajo.

**Ejemplo:** "En las últimas tres plannings (S), las prioridades cambiaron el miércoles sin explicar el motivo (B). El equipo dejó a medias la migración dos veces y perdimos unos cuatro días (I). ¿Qué está pasando del lado de producto? ¿Podemos acordar que los cambios lleguen con el motivo escrito?"

**Entre equipos** el riesgo es hablar del "equipo de plataforma" como un bloque. Se nombra la situación y el canal acordado, y se busca el impacto compartido: "El cambio de versión del gateway de LLM del jueves (S) se anunció en el canal de plataforma pero no en el nuestro (B). El asistente devolvió errores 20 minutos hasta que lo vimos (I). ¿Podemos sumarnos a la lista de avisos de cambios?"

**Por qué importa:** lo que nadie le dice a un líder o a otro equipo se repite, porque quien puede cambiarlo no se entera.

### Cultura: seguridad psicológica y postmortems sin culpas

Ninguna técnica funciona si decir "me equivoqué" o "no entiendo" tiene costo. **Seguridad psicológica** es la creencia compartida de que en el equipo se puede preguntar, admitir errores o disentir sin ser castigado ni ridiculizado. Se construye con conductas repetidas: el líder admite sus errores primero, las preguntas se responden sin ironía, el feedback se da en privado.

El postmortem sin culpas es la versión institucional de esta idea: se analiza el sistema, no a la persona (ver [On-call, runbooks e incidentes](#t/on-call)). SBI encaja natural ahí: describe situación, acción e impacto sin juicio.

**Ejemplo:** en la retrospectiva, la tech lead empieza contando que aprobó sin leer el PR que causó el incidente; después, dos personas más cuentan errores propios.

**Por qué importa:** sin seguridad psicológica los errores se esconden y el feedback deja de circular.

### Feedback a un agente: SBI aplicado a prompts

Cuando un agente de código entrega algo que no sirve, la reacción típica es un mensaje vago: "no, está mal, hazlo de nuevo". El agente, igual que una persona, no sabe qué cambiar y prueba otra cosa al azar. La estructura SBI se traduce directamente:

| SBI con personas | Feedback a un agente |
|---|---|
| Situación | Contexto: qué tarea, qué archivo, qué restricciones aplicaban |
| Comportamiento | Salida observada: qué hizo exactamente |
| Impacto | Consecuencia: qué test falla, qué regla rompe |
| Pedido | Cambio deseado y cómo se verifica |

**Ejemplo:**

- Vago: "Esto no funciona, arréglalo."
- SBI: "En la tarea de reprogramar entregas (S), el endpoint que escribiste acepta una tercera reprogramación (B). Eso rompe la regla de producto de máximo dos y el test `TestLimiteReprogramaciones` falla (I). Cambia la validación para rechazar la tercera con 409 y corre ese test antes de dar la tarea por terminada."

**Por qué importa:** sin la salida observada y el impacto, cada reintento del agente es otra apuesta. Lo mismo vale al ajustar un prompt de producción: describir en qué tipo de consulta falla, qué respondió el modelo, por qué es un problema y qué se espera, y convertirlo en un caso de [evaluación](#t/evaluacion-llms) para que no vuelva.

### Feedback sobre trabajo hecho con IA

Cuando un colega entrega trabajo hecho con ayuda de un agente, el feedback va sobre el resultado y la revisión, no sobre la herramienta. "Esto lo hizo la IA, se nota" no ayuda y suena a reproche. El autor sigue siendo responsable de lo que entrega, y eso es lo que se conversa.

**Ejemplo:**

- Mal: "Otra vez código de ChatGPT sin revisar."
- SBI: "En el PR de la herramienta de clima (S), hay dos funciones que no se usan y un manejo de error que traga la excepción (B). Me llevó una hora entender qué parte era necesaria (I). ¿Puedes revisar el diff completo antes de pedir revisión y sacar lo que no corresponde?"

**Por qué importa:** discutir la herramienta desvía la conversación; discutir el resultado mantiene clara la responsabilidad del autor.

## Casos prácticos

### Un ingeniero senior que bloquea con comentarios cortantes

**Situación:** en el equipo del servicio de asignación, un ingeniero senior deja comentarios como "no" o "esto está mal" en los PRs. Dos personas nuevas dejaron de pedirle revisión.

**Qué se hace:** la tech lead le da feedback en privado con SBI-I: "En los PRs 512 y 518 de la semana pasada (S), tus comentarios fueron 'no' y 'esto está mal', sin explicación (B). Daniel me dijo que no sabía qué cambiar, y ahora pide revisión a otras personas aunque tú conoces mejor ese código (I). ¿Cómo lo ves?". Él explica que revisa entre reuniones con poco tiempo. Acuerdan que, si no tiene tiempo para explicar, deja "lo miro con calma mañana" en vez de un comentario seco, y que usará etiquetas de severidad (ver [Feedback en revisiones de código y diseño](#t/feedback-revisiones)).

### Reconocimiento que nadie vio

**Situación:** una ingeniera de plataforma pasó dos semanas reduciendo el tiempo de CI de 25 a 9 minutos. Nadie lo mencionó; ella siente que el trabajo de infraestructura no se ve.

**Qué se hace:** el líder publica en el canal de ingeniería un reconocimiento concreto: "Esta semana Carla bajó el CI del monorepo de 25 a 9 minutos, separando los tests de integración y cacheando las imágenes. Con unos 60 PRs por día, son unas 16 horas de espera menos por día para todo el equipo". El equipo agrega a la review del sprint un espacio para mejoras internas.

### Un agente que repite el mismo error

**Situación:** un ingeniero corrige tres veces al agente de código con "no, así no", y el agente sigue generando consultas SQL que leen la tabla de pedidos completa.

**Qué se hace:** reescribe el feedback con estructura: contexto (la tabla tiene 80 millones de filas y hay un índice por zona y fecha), salida observada (la consulta no filtra por fecha), impacto (el plan de ejecución muestra un escaneo completo) y pedido (filtrar siempre por rango de fechas y adjuntar el `EXPLAIN`). Agrega la regla al archivo de instrucciones del repositorio para que valga en las próximas sesiones.

## Errores comunes

- **Dar feedback sobre la persona en lugar del comportamiento.** Si la frase tiene un adjetivo sobre alguien, falta describir qué hizo.
- **Usar el sándwich.** El mensaje importante se diluye; se dice directo, con respeto, y el reconocimiento se da por separado cuando es genuino.
- **Concluir sin preguntar.** El observador no tiene todo el contexto; la pregunta de SBI-I suele cambiar el diagnóstico.
- **Terminar sin acuerdo.** Sin un próximo paso concreto, el feedback queda en una sensación.
- **Guardar el feedback para la evaluación.** Lo que tiene meses no se puede corregir; se da en uno o dos días.
- **Corregir a un agente con "hazlo de nuevo".** Sin la salida observada, el impacto y el cambio esperado, el agente prueba al azar.

## Para discutir en equipo

- ¿Cuándo fue la última vez que recibimos feedback concreto sobre algo que hicimos bien? ¿Qué nos dijo que repitiéramos?
- ¿Nuestros postmortems describen comportamientos e impactos, o se cuelan juicios sobre personas?
- ¿Qué canal usamos para el reconocimiento? ¿Llega a quienes hacen trabajo menos visible?
- ¿Cómo damos feedback hacia arriba hoy? ¿Qué lo haría más fácil?
- ¿Tenemos una forma compartida de corregir a los agentes de código, o cada uno improvisa?
