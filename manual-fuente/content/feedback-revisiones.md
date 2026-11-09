---
slug: feedback-revisiones
titulo: Feedback en revisiones de código y diseño
resumen: Cómo escribir y recibir comentarios útiles en revisiones de código, diseños y ADRs, incluidos los PRs generados por agentes de código.
lectura: 12
---

## La idea central

Una revisión de código es una conversación escrita sobre un cambio, con dos objetivos: que el cambio sea correcto y que más de una persona entienda el sistema. No es un examen ni un peaje. Cuando funciona, el autor aprende, el revisor aprende y el código queda consistente. Cuando no funciona, se convierte en una cola donde los PRs esperan días, los comentarios se leen como ataques y las discusiones de estilo tapan los problemas reales.

Casi todo depende de cómo se escriben los comentarios. Con los agentes de código el tema gana peso: el volumen de PRs sube, el código generado se ve prolijo aunque tenga errores sutiles, y los comentarios de revisión ahora también los lee un agente que tiene que actuar sobre ellos.

## Conceptos

### Para qué sirve revisar

Una revisión cumple tres funciones, en este orden:

1. **Corrección:** errores de lógica, casos borde sin cubrir, riesgos de seguridad o de rendimiento.
2. **Conocimiento compartido:** que al menos otra persona entienda el cambio y pueda sostenerlo en un incidente.
3. **Consistencia:** que el código siga las convenciones del equipo.

No es un control para "atrapar" al autor ni un trámite que se aprueba sin leer.

**Ejemplo:** en un PR del modelo de ETA, la revisora encuentra un caso sin manejar (corrección), entiende cómo se calcula la feature de clima (conocimiento) y pide usar el logger estructurado del servicio (consistencia).

**Por qué importa:** vista como peaje, se aprueba sin leer; vista como examen, se evita con PRs enormes.

### Cómo escribir un comentario útil

Un buen comentario tiene cuatro rasgos:

- **Específico:** señala la línea y el problema concreto.
- **Accionable:** el autor sabe qué hacer después de leerlo.
- **Explica el porqué:** sin el motivo, el autor no puede evaluar si el comentario aplica ni aprender para la próxima.
- **Distingue preguntas de pedidos:** una pregunta genuina invita a explicar; un pedido indica un cambio.

**Ejemplo:**

- Mal: "Esto no me gusta."
- Mejor: "Este `for` llama al modelo de ETA una vez por transportista. Con 30 candidatos son 30 llamadas en serie y pasamos los 50 ms. ¿Podemos usar el endpoint por lotes que ya existe en `cliente_eta.go`?"
- Mal: "¿Por qué hiciste esto así?" (puede leerse como reproche).
- Mejor: "No entiendo por qué el reintento va antes de la validación. ¿Hay un caso donde convenga reintentar un pedido inválido? Si no, lo movería después."

**Por qué importa:** un comentario con motivo se resuelve en un intento; uno sin motivo abre una discusión.

### Etiquetar la severidad

Uno de los problemas más comunes es que el autor no sabe qué comentarios son obligatorios. Ante la duda, trata todos como bloqueantes, o ninguno. Una práctica difundida es el estilo **conventional comments**: cada comentario empieza con una etiqueta que indica su tipo, y opcionalmente si bloquea o no la aprobación.

| Etiqueta | Para qué se usa | ¿Bloquea? | Ejemplo en Rumbo |
|---|---|---|---|
| **praise** (elogio) | Reconocer algo bien hecho | No | "praise: el test con servidor lento simulado es excelente, lo voy a copiar." |
| **nitpick** (detalle) | Preferencia menor, de estilo | No | "nitpick: `calcEta` podría llamarse `estimarEta` como el resto del paquete." |
| **suggestion** (sugerencia) | Propuesta de mejora con motivo | Según se marque | "suggestion (no bloqueante): usar el cliente por lotes ahorraría unos 20 ms." |
| **issue** (problema) | Un problema concreto que hay que resolver | Normalmente sí | "issue: si el pedido no tiene zona, esto entra en pánico." |
| **question** (pregunta) | Algo que el revisor no entiende | No, hasta que se responda | "question: ¿este timeout se probó con la carga del pico de la tarde?" |
| **todo** (pendiente) | Cambio chico y necesario | Sí | "todo: falta registrar la métrica `eta_fallback_total`." |

Lo central no son los nombres exactos, sino que el equipo comparta un vocabulario.

**Ejemplo:** con "nitpick: prefiero `estimarEta`" e "issue (bloqueante): falta el caso sin zona", el autor sabe que solo el segundo frena la fusión.

**Por qué importa:** sin severidad, un PR con 15 comentarios parece desastroso aunque 13 sean detalles. Con etiquetas, el autor ve en segundos que hay dos cosas que resolver.

### Tamaño del PR y latencia de revisión

El tamaño del PR es probablemente la variable que más influye en la calidad de la revisión. La relación no es lineal: un PR de 50 líneas se revisa con atención en minutos; uno de 800 se hojea. Varios estudios de la industria coinciden en que, pasadas unas pocas cientos de líneas, la cantidad de problemas encontrados por línea cae y la espera para recibir la primera revisión sube. Los números de abajo son hipotéticos, en el orden de magnitud que suele observarse:

```barras
titulo: Tiempo hasta aprobar según tamaño (hipotético)
unidad: horas
Hasta 50 líneas | 2
50 a 200 líneas | 5
200 a 400 líneas | 12
400 a 800 líneas | 26
Más de 800 líneas | 48
```

Prácticas que ayudan:

- **PRs chicos y con un solo propósito.** Un refactor y un cambio de comportamiento van separados.
- **Feature flags** para fusionar código incompleto sin activarlo.
- **Un objetivo de latencia de revisión**, por ejemplo primera respuesta en menos de un día hábil, medido como parte de las [métricas de entrega](#t/metricas-entrega).

**Ejemplo:** el equipo del asistente midió que sus PRs de más de 400 líneas esperaban unos dos días la primera revisión, y los de menos de 100, unas horas.

**Por qué importa:** un PR que nadie puede revisar bien se aprueba igual, y por ahí pasan los errores.

### Qué revisar primero y qué automatizar

La atención del revisor es limitada; conviene gastarla donde una máquina no llega. Un orden útil:

1. **Diseño y enfoque:** ¿el cambio resuelve el problema correcto? ¿Está en el lugar correcto? Si el enfoque está mal, comentar los nombres de variables es tiempo perdido.
2. **Tests:** ¿cubren el comportamiento nuevo y los casos borde? Leer los tests primero muchas veces explica el cambio mejor que el código.
3. **Partes riesgosas:** autenticación, PII, migraciones de base, concurrencia, llamadas a servicios externos, configuración de timeouts.
4. **Legibilidad y consistencia.**

Lo que no debería ocupar a una persona: formato, orden de imports, reglas de lint, tipos. Eso lo resuelven el formateador y el linter en CI. Si un revisor escribe "falta un espacio", el problema es del pipeline, no del autor.

**Ejemplo:** en un PR que cambia la asignación, la revisora lee primero los tests, ve que falta el caso sin transportistas disponibles y lo pide antes de mirar nombres.

**Por qué importa:** la atención humana es lo más caro de la revisión; gastarla en espacios deja pasar los bugs.

### Revisar diseños, RFCs y ADRs

Un documento de diseño o un **RFC** (*request for comments*, propuesta abierta a comentarios) se revisa antes de escribir código, cuando cambiar de idea es barato. Las mismas reglas aplican, con algunas diferencias:

- **Se comenta el problema antes que la solución.** "¿Está claro qué pasa hoy y por qué hay que cambiarlo?" es la primera pregunta.
- **Se buscan alternativas no consideradas y supuestos ocultos.** "El diseño supone que el clima llega en menos de 10 ms. ¿Qué pasa si el proveedor tarda?"
- **Se distinguen objeciones de preferencias.** "Bloqueante: no hay plan de rollback" no es lo mismo que "Preferiría gRPC, pero REST también sirve".
- **Se cierra con una decisión registrada.** Un ADR (*architecture decision record*) deja el contexto, la decisión, las alternativas descartadas y las consecuencias. Los desacuerdos que no ganaron quedan escritos como riesgos, con un disparador para revisarlos.

**Ejemplo:** en el RFC para mover el pronóstico de demanda de batch nocturno a cada hora, un revisor escribe: "issue (bloqueante): el documento no dice qué pasa con los consumidores que leen el archivo nocturno de S3. ¿Se mantiene durante una transición?". El autor agrega una sección de migración en dos fases.

**Por qué importa:** un problema detectado en el documento cuesta una conversación; en producción, un incidente.

### Recibir comentarios de revisión

Del lado del autor:

- **Separar el código de uno mismo.** Un comentario sobre la función no es un comentario sobre la persona.
- **Responder cada comentario:** "hecho", "lo dejo para otro PR (ticket 931)" o una explicación de por qué no. Un comentario sin respuesta obliga al revisor a buscar si se resolvió.
- **Agradecer los hallazgos reales:** un bug encontrado es un incidente evitado.
- **Facilitar la revisión desde el principio:** una descripción con qué cambia, por qué, cómo se probó y dónde mirar con más cuidado.

**Ejemplo:** a "question: ¿por qué 3 reintentos?", el autor responde "el transportista corta a los 2 s y 3 reintentos de 500 ms entran; lo dejo comentado en el código".

**Por qué importa:** cómo responde el autor define si el revisor vuelve a revisar con cuidado.

### Desacuerdos y escalamiento

Cuando autor y revisor no se ponen de acuerdo:

1. **Pasar a sincrónico después de dos idas y vueltas.** Una llamada de diez minutos resuelve lo que veinte comentarios no.
2. **Volver a los criterios del equipo:** guía de estilo, ADRs previos, requisitos de latencia. Si no hay criterio escrito, el desacuerdo revela que falta uno.
3. **Pedir una tercera opinión** a alguien con contexto, no a quien tenga más jerarquía.
4. **Decidir y registrar.** Quien tiene la responsabilidad del componente decide; el otro acompaña (ver [Comunicación asertiva](#t/comunicacion-asertiva)). Si el tema vuelve a aparecer, se convierte en regla escrita.

**Ejemplo:** tras tres comentarios sobre gRPC o REST para una herramienta interna, autor y revisor hablan diez minutos, abren el ADR de APIs internas y eligen lo que dice.

**Por qué importa:** un desacuerdo que se arrastra en comentarios frena el PR y desgasta más que el tema en sí.

### Revisar PRs generados por agentes de código

Con agentes, cambian tres cosas en la revisión:

- **Más volumen.** Un ingeniero con un agente puede abrir tres o cuatro PRs por día. Si la revisión no acompaña, la cola crece y la tentación es aprobar rápido.
- **Código plausible.** El código generado compila, tiene nombres razonables y comentarios prolijos. Los errores son sutiles: un caso borde que no se maneja, un test que verifica la implementación en vez del comportamiento, una función que ya existía en otro módulo, una dependencia inventada.
- **Tests que acompañan al código.** Si el mismo agente escribió el código y los tests, pueden compartir el mismo malentendido. Conviene revisar los tests contra la especificación, no contra el código.

Prácticas concretas: pedir PRs chicos también al agente, exigir que la descripción incluya la tarea o especificación que implementa y la evidencia de tests, revisar primero los casos borde y, sobre todo, recordar que **el autor del PR sigue siendo responsable**, aunque lo haya escrito un agente. En una matriz de responsabilidades, el agente puede ser quien ejecuta, pero quien rinde cuentas es la persona (ver [RACI y RASI](#t/raci-rasi)).

**Ejemplo:** un agente agrega un helper `normalizarTelefono` de 40 líneas; el revisor nota que ya existe uno en `notificaciones`, con redacción de PII, y pide reutilizarlo.

**Por qué importa:** el código generado parece terminado antes de estarlo; la revisión es donde eso se nota.

### Un LLM como primer revisor

Un LLM puede hacer una primera pasada sobre el PR: detectar errores evidentes, señalar casos borde sin tests, inconsistencias de nombres o secretos en el código. Es útil como filtro antes de pedir revisión humana. Sus límites:

- **No conoce el contexto del negocio** salvo que se le dé.
- **Genera ruido.** Muchos comentarios irrelevantes.
- **No reemplaza la responsabilidad.** Una aprobación de un LLM no es una aprobación; el control sigue siendo humano.

Conviene medirlo como cualquier otro sistema: de los comentarios que hizo, ¿cuántos llevaron a un cambio? Si la proporción es baja, se ajusta o se limita a categorías concretas.

**Ejemplo:** el LLM señala una consulta sin `LIMIT` en un endpoint nuevo, un hallazgo real; en el mismo PR sugiere renombrar cinco variables, y eso se ignora.

**Por qué importa:** un revisor ruidoso entrena al equipo a ignorarlo, incluso cuando acierta.

### Comentarios que un agente pueda ejecutar

Cada vez más, quien atiende los comentarios de revisión es un agente, y los comentarios vagos producen cambios al azar. Un comentario ejecutable dice qué está mal, dónde, por qué y cómo se verifica.

**Ejemplo:**

- Vago: "Revisar el manejo de errores."
- Ejecutable: "issue (bloqueante): en `asignar.go` línea 84, si `cliente_eta` devuelve timeout se retorna el error y la asignación falla. Debe usar la ETA por distancia como respaldo. Agregar un test con servidor lento que verifique que la asignación termina en menos de 50 ms."

**Por qué importa:** un comentario ejecutable se resuelve en un intento, lo lea un agente o una persona.

## Casos prácticos

### Un PR de 1.200 líneas el viernes

**Situación:** un ingeniero abre el viernes un PR de 1.200 líneas con la integración de un transportista nuevo, el refactor del cliente HTTP y cambios de formato. Nadie lo toma hasta el martes; la revisión deja tres comentarios superficiales.

**Qué se hace:** se le pide partirlo en tres PRs: formato (automático, aprobación rápida), refactor del cliente sin cambio de comportamiento y la integración detrás de un feature flag. El equipo fija un tamaño orientativo de 400 líneas y un formateador obligatorio en CI. En la revisión del tercer PR aparece un error real: la integración no manejaba el estado "rechazado por el transportista".

### Un PR generado por un agente con tests que no prueban nada

**Situación:** un PR generado por un agente agrega la herramienta "consultar estado del pedido" al asistente. Tiene 14 tests, todos pasan. El revisor nota que los tests verifican que se llame a un mock con ciertos argumentos, pero ninguno cubre un pedido inexistente o de otro comercio.

**Qué se hace:** el revisor deja un comentario ejecutable pidiendo dos tests de comportamiento: pedido inexistente devuelve "no encontrado" y pedido de otro comercio devuelve "sin permiso". El segundo falla: la herramienta no verificaba el comercio. Se corrige, y el equipo suma a la plantilla de PR la sección "casos borde cubiertos".

### Un LLM revisor que nadie lee

**Situación:** el equipo activó un LLM que comenta automáticamente cada PR. A las tres semanas, nadie lee sus comentarios: deja un promedio de 12 por PR.

**Qué se hace:** se miden 50 PRs: solo el 10% de los comentarios del LLM llevaron a un cambio, pero casi todos esos eran de tres tipos (errores no manejados, secretos en el código, consultas sin límite). Se restringe el revisor a esas categorías, con un máximo de 3 comentarios por PR. La proporción útil sube al 50% y el equipo vuelve a leerlos.

## Errores comunes

- **Discutir estilo a mano.** Formato y lint van en CI; la atención humana se reserva para diseño, tests y riesgos.
- **Comentarios sin porqué.** "Cámbialo" no enseña nada; con el motivo, el autor aprende y puede discrepar con argumentos.
- **No marcar la severidad.** El autor no sabe qué bloquea y trata todo igual; se etiqueta cada comentario.
- **Aprobar PRs enormes sin leerlos.** Se piden PRs chicos; si no se puede revisar bien, se dice.
- **Confiar en el código del agente porque se ve prolijo.** Se revisan los tests contra la especificación y los casos borde.
- **Tratar la aprobación de un LLM como revisión.** Es un filtro previo; la responsabilidad sigue siendo humana.

## Para discutir en equipo

- ¿Cuál es hoy el tamaño mediano de nuestros PRs y cuánto esperan la primera revisión?
- ¿Adoptamos etiquetas de severidad? ¿Cuáles y con qué significado?
- ¿Qué discutimos a mano en las revisiones que podría automatizarse en CI?
- ¿Qué exigimos a un PR generado con agentes antes de pedir revisión humana?
- ¿Cómo sabríamos si un LLM revisor nos ayuda o solo agrega ruido?
