---
slug: sdd
titulo: Desarrollo guiado por especificaciones (SDD) con agentes de código
resumen: Una práctica para trabajar con agentes de código en la que la especificación versionada guía el plan, las tareas, la implementación y la verificación.
lectura: 16
---

## La idea central

Un agente de código es un agente como cualquier otro (ver [Agentes y tool calling](#t/agentes)): un LLM en un bucle que lee archivos del repositorio, los edita, ejecuta comandos y corre tests. Es muy rápido escribiendo código, pero tiene dos limitaciones de fondo: no sabe lo que nosotros sabemos sobre el producto y olvida casi todo al terminar la sesión. Si le pedimos funcionalidades de manera improvisada, con mensajes sueltos en un chat, el resultado suele funcionar en la demo y alejarse de a poco de lo que se quería. Además, el razonamiento ("por qué se hizo así") queda perdido en una conversación que nadie vuelve a leer.

El **desarrollo guiado por especificaciones** (SDD, *spec-driven development*) invierte el orden de importancia: **el artefacto principal es la especificación**, un documento en lenguaje natural versionado en el repositorio, y el código se deriva de ella. La analogía útil es la de un plano de obra: los albañiles pueden ser muy rápidos, pero nadie los deja empezar sin plano, y cuando la obra cambia se actualiza el plano, no solo la pared. Con agentes la idea gana peso porque escribir código se volvió barato; lo caro pasó a ser decidir qué construir y verificar que lo construido es eso.

## Conceptos

### El problema: programar "a sensación"

Se llama **vibe coding** a pedirle cosas a un agente de código sobre la marcha, aceptar lo que produce si parece funcionar y seguir pidiendo ajustes. Para un prototipo de una tarde está bien. Para una funcionalidad que va a producción aparecen cuatro problemas:

1. **Deriva de intención.** Cada pedido corrige el anterior. Después de 20 mensajes, el comportamiento final responde al último pedido, no al objetivo original. Las restricciones dichas en el mensaje 3 ya no están en el contexto del modelo en el mensaje 18.
2. **Revisión difícil.** El revisor recibe un PR de 900 líneas sin saber qué se pretendía. Solo puede juzgar si el código "se ve bien", no si hace lo correcto.
3. **Razonamiento perdido.** Las decisiones ("no notificamos por SMS porque...") quedan en el historial del chat, no en el repositorio.
4. **No se puede repetir.** Si hay que rehacer la funcionalidad o portarla a otro servicio, no hay nada de qué partir salvo el código.

**Ejemplo:** un ingeniero de Rumbo pide al agente "agrega un endpoint para reprogramar entregas", luego "que valide la fecha", luego "que no permita domingos", luego "ah, y que avise al transportista". El resultado tiene cuatro capas de parches, valida los domingos en un lugar y no en otro, y nadie escribió que la reprogramación solo vale para pedidos todavía no retirados.

### El flujo típico, paso a paso

SDD organiza el trabajo en etapas, cada una con un archivo revisable:

1. **Especificación (qué y por qué).** Usuarios, comportamiento esperado, criterios de aceptación, no-objetivos y restricciones. No habla de clases ni de tablas.
2. **Plan técnico (cómo).** Arquitectura, modelo de datos, interfaces, dependencias y riesgos. Se apoya en la especificación y en las convenciones del repositorio.
3. **Lista de tareas.** Pasos pequeños, ordenados y verificables, cada uno con su test o comprobación.
4. **Implementación.** El agente toma una tarea a la vez, la implementa, corre los tests y se detiene.
5. **Verificación.** Se contrasta el resultado con los criterios de aceptación, no solo con "los tests pasan".
6. **Actualización.** Si la realidad obliga a cambiar algo (una API externa no se comporta como se pensaba), primero se actualiza la especificación o el plan, después el código.

El agente puede ayudar a redactar cada etapa: proponer la especificación a partir de una descripción breve, derivar el plan y partirlo en tareas. Lo que cambia es que **una persona revisa y aprueba cada etapa antes de pasar a la siguiente**.

Existen herramientas que generan esta estructura y sus plantillas, pero la práctica no depende de ninguna: alcanza con tres archivos markdown en el repositorio y disciplina para usarlos.

### Una especificación de ejemplo

La funcionalidad: que un destinatario pueda reprogramar su entrega desde el chat del asistente de soporte. Un extracto de `specs/reprogramar-entrega/spec.md`:

```markdown
# Reprogramar entrega desde el chat

## Contexto
El 12% de los contactos al asistente de soporte piden cambiar el día de entrega.
Hoy los deriva a una persona, con una espera media de 40 minutos.

## Usuarios
- Destinatario identificado por el enlace de seguimiento del pedido.

## Comportamiento
- El asistente ofrece hasta 3 franjas disponibles en los próximos 5 días hábiles.
- El destinatario elige una; el sistema confirma y actualiza el pedido.
- Se notifica al comercio y, si ya estaba asignado, al transportista.

## Criterios de aceptación
- CA1: Un pedido en estado "creado" o "asignado" puede reprogramarse.
- CA2: Un pedido "retirado", "entregado" o "fallido" no puede reprogramarse;
  el asistente lo explica y ofrece derivar a una persona.
- CA3: Un pedido admite como máximo 2 reprogramaciones.
- CA4: Repetir la misma confirmación no genera un segundo cambio.
- CA5: Ni el nombre, ni el teléfono, ni la dirección aparecen en logs ni en trazas.

## No-objetivos
- Cambiar la dirección de entrega.
- Reprogramar desde el panel del comercio.

## Restricciones
- El agente del asistente solo accede a la reprogramación mediante una herramienta
  con parámetros acotados; nunca escribe en la base directamente.
- Latencia de la confirmación: p95 menor a 2 s.
```

Fíjate en tres detalles: el contexto trae un número que justifica el trabajo, los criterios están numerados para poder citarlos en tests y PRs, y los **no-objetivos** dicen lo que queda afuera para que nadie, persona o agente, lo agregue "de paso".

### Del plan a las tareas

El plan técnico (`plan.md`) traduce la especificación a decisiones de ingeniería. En el ejemplo:

- **Interfaz:** nueva herramienta `reprogramar_entrega(pedido_id, franja_id, clave_idempotencia)` expuesta al agente de soporte; endpoint interno `POST /pedidos/{id}/reprogramaciones` en el servicio de pedidos.
- **Datos:** tabla `reprogramaciones` (pedido, franja anterior, franja nueva, origen, fecha) y contador en `pedidos`.
- **Eventos:** nuevo evento `pedido_reprogramado` en Kafka, consumido por notificaciones y asignación.
- **Riesgos:** carrera entre la reprogramación y el retiro del paquete; se resuelve con una transición de estado condicional en la base.

La lista de tareas (`tasks.md`) parte ese plan en pasos que un agente puede completar y verificar en una sesión:

```markdown
- [ ] T1. Migración: tabla `reprogramaciones` y columna `cantidad_reprogramaciones`.
      Verifica: la migración corre y revierte en la base de prueba.
- [ ] T2. Regla de dominio `puede_reprogramar(pedido)` (CA1, CA2, CA3).
      Verifica: tests unitarios por estado y por contador.
- [ ] T3. Endpoint con clave de idempotencia y transición condicional (CA4).
      Verifica: test que envía la misma confirmación dos veces.
- [ ] T4. Evento `pedido_reprogramado` con esquema registrado.
      Verifica: test de contrato del esquema.
- [ ] T5. Herramienta del agente de soporte y su descripción.
      Verifica: 20 casos de evaluación de conversación (ver evaluación de LLMs).
- [ ] T6. Redacción de PII en logs y trazas del flujo (CA5).
      Verifica: test que inspecciona los logs capturados.
- [ ] T7. Métricas y alerta de tasa de error de reprogramación.
      Verifica: la métrica aparece en el entorno de staging.
```

Cada tarea es chica (unas pocas horas de trabajo humano equivalente), declara qué criterios cubre y cómo se comprueba. Eso permite revisar PRs pequeños y detectar enseguida si el agente se desvió.

**Por qué importa:** una tarea sin verificación explícita es una invitación a que el agente la marque como hecha porque "compila".

### Criterios de aceptación que se convierten en tests

Un buen criterio de aceptación es una afirmación **comprobable**: alguien (o algo) puede decir si se cumple o no. "La reprogramación debe ser robusta" no lo es; "repetir la misma confirmación no genera un segundo cambio" sí. El formato Dado/Cuando/Entonces (*Given/When/Then*) ayuda, aunque no es obligatorio:

```text
CA4
Dado un pedido "asignado" con 0 reprogramaciones
Cuando se confirma la franja F2 con la clave K1
  y se vuelve a confirmar la franja F2 con la clave K1
Entonces el pedido queda en F2, el contador vale 1
  y existe un solo evento pedido_reprogramado
```

El paso clave es que **los tests se escriben a partir de los criterios antes o junto con el código**, y el agente recibe la consigna de hacerlos pasar sin modificarlos. Si el agente necesita cambiar un test, debe decirlo y justificarlo; ese cambio se revisa como un cambio de especificación. Para la parte conversacional (que el asistente explique bien por qué no se puede reprogramar un pedido retirado) los tests unitarios no alcanzan y se usan casos de [evaluación de LLMs](#t/evaluacion-llms).

### El archivo de instrucciones del repositorio

Además de la especificación de cada funcionalidad, conviene tener un **archivo de instrucciones del repositorio**: un documento en la raíz que el agente lee al comenzar cada sesión. Algunos equipos lo llaman "constitución". Contiene reglas que valen para todo el trabajo, no para una funcionalidad:

- **Convenciones:** estructura de carpetas, estilo de errores, cómo se nombran los tests.
- **Comandos:** cómo correr tests, linters y migraciones (`make test`, `make lint`).
- **Acciones prohibidas:** no tocar migraciones ya aplicadas, no desactivar tests, no agregar dependencias sin anotarlo, no imprimir datos de destinatarios.
- **Definición de terminado:** una tarea está hecha cuando sus tests pasan, el linter está limpio y la casilla en `tasks.md` está marcada con una línea que explica cómo se verificó.

**Por qué importa:** el agente no tiene memoria entre sesiones. Lo que no está escrito en el repositorio no existe para él la próxima vez.

### Relación con TDD, BDD y design docs

SDD no reemplaza prácticas conocidas; las combina. La diferencia está en el artefacto central y en quién lo consume.

| Práctica | Artefacto principal | Quién lo escribe | Cuándo | Qué verifica |
|---|---|---|---|---|
| TDD | Tests unitarios | Quien programa | Antes de cada pieza de código | Que cada unidad se comporta como el test exige |
| BDD | Escenarios Dado/Cuando/Entonces | Producto e ingeniería juntos | Antes de la funcionalidad | Que el comportamiento observable coincide con lo acordado |
| Design doc y ADR | Documento de diseño y registro de decisiones | Ingeniería, revisado por pares | Antes de cambios grandes; ADR al decidir | Que la arquitectura y sus trade-offs fueron pensados y quedan registrados |
| SDD | Especificación, plan y tareas versionados | Personas, con ayuda del agente | Antes y durante cada funcionalidad | Que el código derivado cumple los criterios de aceptación y respeta no-objetivos |

En la práctica, los criterios de una especificación suelen escribirse al estilo BDD, cada tarea se implementa con TDD y las decisiones de arquitectura que surgen del plan se registran como ADR (ver [Revisión de arquitectura](#t/revision-arquitectura)). Lo nuevo es que la especificación está pensada también para que **un agente** la lea y la siga.

### Dónde revisar con más cuidado

Corregir una línea de la especificación cuesta un minuto; corregir lo que el agente construyó sobre una especificación equivocada cuesta un día. Por eso la atención humana se reparte al revés de lo habitual:

- **Especificación:** revisión lenta, con producto si corresponde. ¿Los criterios son comprobables? ¿Faltan casos (pedido ya retirado, pedido de otro destinatario)? ¿Están los requisitos de seguridad y privacidad?
- **Plan:** revisión técnica. ¿Respeta los contratos existentes? ¿Hay decisiones irreversibles?
- **Tareas:** revisión rápida del orden y de la verificación de cada una.
- **Código:** se sigue revisando, pero con la especificación al lado. La pregunta deja de ser "¿se ve bien?" y pasa a ser "¿cumple CA3 y no hace nada fuera de alcance?".

**Ejemplo:** en un PR de 400 líneas generado por el agente, un revisor con la especificación a mano detecta en minutos que se agregó un parámetro `nueva_direccion` "por si acaso". Es un no-objetivo explícito, así que se rechaza sin discusión.

### Mantener especificación y código sincronizados

La **deriva de especificación** (*spec drift*) ocurre cuando el código cambia y la especificación no. A los tres meses la especificación describe un sistema que ya no existe y deja de ser confiable; el agente, que la sigue leyendo, toma decisiones sobre supuestos falsos.

Prácticas que ayudan:

- **Regla de orden:** si un PR cambia comportamiento, cambia primero la especificación en el mismo PR. El revisor rechaza PRs de comportamiento sin cambio de especificación.
- **Trazabilidad:** los tests citan el criterio que verifican (`test_ca3_maximo_dos_reprogramaciones`). Si se borra un criterio, aparecen tests huérfanos; si se agrega uno, falta su test.
- **Comprobación en CI:** un paso del pipeline de [CI/CD](#t/ci-cd) puede verificar que todo criterio tenga al menos un test que lo nombre, y fallar si no.

### Cuándo no vale la pena y cuándo sí

SDD agrega trabajo al principio. Ese trabajo se recupera solo si la funcionalidad es lo bastante grande o riesgosa.

No vale la pena para:

- Arreglos de una línea o bugs con causa clara.
- Spikes y exploración: cuando todavía no se sabe qué se quiere, escribir criterios de aceptación es ficción. Se explora libremente y, si la idea sobrevive, se escribe la especificación con lo aprendido.

Sí vale la pena para:

- Funcionalidades que tocan varios archivos o servicios.
- Trabajo en paralelo de varias personas o varios agentes, porque las tareas y sus límites quedan escritos.
- Áreas reguladas o sensibles (datos personales, permisos), donde hay que poder mostrar qué se pidió y cómo se verificó.
- Código que va a vivir años y que otros van a mantener.

Un umbral práctico: si la descripción del cambio no entra en el título de un PR, probablemente merece una especificación corta.

### Riesgos de la práctica

- **Especificaciones demasiado vagas.** "El asistente debe manejar bien las reprogramaciones" deja todas las decisiones al agente, que es justo lo que se quería evitar.
- **Especificaciones demasiado detalladas.** Si la especificación dice "crear la función `validar()` con un `if` por estado", es pseudocódigo: duplica el código, se desactualiza enseguida y quita al plan su razón de ser. La especificación describe comportamiento; el plan, estructura.
- **Tareas marcadas como hechas sin verificación.** Los agentes tienden a declarar éxito. La definición de terminado exige evidencia (salida de los tests, comando ejecutado), y CI vuelve a correr todo.
- **Confianza falsa por tests en verde.** Un test que verifica lo incorrecto pasa igual. Si el agente escribió el test y el código a la vez, puede haber codificado el mismo malentendido en ambos. Por eso los tests de criterios de aceptación se revisan como parte de la especificación.
- **Requisitos de seguridad omitidos.** El agente no agrega lo que nadie pidió: autorización, redacción de PII, límites de uso. Si no están en la especificación o en el archivo de instrucciones, lo más probable es que falten.

## Casos prácticos

### Una funcionalidad sin especificación que ignoró un no-objetivo

**Situación:** un ingeniero construyó con el agente, en una tarde y sin especificación, el aviso de "pedido demorado" al comercio. El PR pasó la revisión porque el código era limpio y tenía tests. Dos semanas después, operaciones notó que el aviso también se enviaba a los destinatarios por SMS. En planificación se había acordado no avisar a los destinatarios en esta etapa, pero ese acuerdo nunca llegó al agente ni al revisor.

**Qué se hace:** se escribe la especificación a posteriori con el no-objetivo explícito ("no notificar a destinatarios en esta versión") y un criterio comprobable ("ningún mensaje con destino en la tabla de destinatarios para este evento"), y se agrega el test correspondiente. Como práctica, el equipo acuerda que toda funcionalidad que envíe mensajes a personas externas requiere especificación con no-objetivos, y el archivo de instrucciones del repositorio de notificaciones lo recuerda.

### Dos agentes en paralelo sin pisarse

**Situación:** para llegar a tiempo con la reprogramación desde el chat, el equipo quiere que dos agentes trabajen a la vez: uno en el servicio de pedidos y otro en la herramienta del asistente de soporte. En un intento anterior, dos agentes editaron el mismo archivo de esquemas y terminaron con un evento en dos formatos distintos.

**Qué se hace:** el plan fija primero los **contratos** (el endpoint interno y el esquema de `pedido_reprogramado`) en una tarea T0 que se completa y se integra antes de abrir el trabajo en paralelo. Luego las tareas se reparten por límites de propiedad: T1 a T4 tocan solo el servicio de pedidos; T5 y su evaluación, solo el asistente, que usa un doble del endpoint basado en el contrato. Cada agente trabaja en su rama y su copia del repositorio, y la lista de tareas indica qué archivos puede tocar cada una. La integración final ejecuta los tests de contrato de ambos lados. La regla que queda: el paralelismo se diseña en el plan, no se improvisa en el merge.

### Un criterio de aceptación que detectó una fuga de PII

**Situación:** durante la implementación de T3, el agente agregó un log de depuración con el objeto pedido completo para diagnosticar un fallo intermitente. El código funcionaba, los tests de dominio pasaban y el PR parecía listo.

**Qué se hace:** el criterio CA5 ("ni el nombre, ni el teléfono, ni la dirección aparecen en logs ni en trazas") tenía su test en T6: ejecuta el flujo completo con un destinatario de prueba cuyos datos son marcadores reconocibles, captura logs y spans, y busca esos marcadores. El test falló y mostró la línea exacta. El agente reemplazó el log por uno con `pedido_id` y estado. La regla pasó al archivo de instrucciones del repositorio y el test se volvió un chequeo compartido para todos los flujos que tocan destinatarios. Sin el criterio escrito, la fuga habría llegado a producción.

### Saltear SDD para un hotfix

**Situación:** un viernes a la noche el servicio de asignación empieza a rechazar pedidos de una zona nueva porque un `enum` de zonas no la incluye. El incidente es claro y el arreglo es de una línea.

**Qué se hace:** no se escribe especificación. Se corrige con el agente o a mano, se agrega un test de regresión, se despliega y se registra en el postmortem. Lo que sí se hace el lunes es revisar si la especificación de zonas (si existía) decía cómo se agregan zonas nuevas; como no lo decía, se abre una especificación breve para que el alta de zonas sea un dato de configuración y no un cambio de código. SDD aplica a la mejora estructural, no a la urgencia.

## Errores comunes

- **Tratar la especificación como trámite.** Si se escribe después del código para "cumplir", no guía nada; se escribe antes y se revisa con la misma seriedad que un design doc.
- **Mezclar qué y cómo.** Nombres de tablas y clases en la especificación la vuelven pseudocódigo; el comportamiento va en la especificación y la estructura en el plan.
- **Tareas grandes y sin verificación.** "Implementar el backend" no es una tarea; cada una debe poder completarse y comprobarse en una sesión, con su test nombrado.
- **Dejar que el agente edite los tests de aceptación.** Si el test no pasa, el agente propone el cambio y una persona decide; si no, el agente puede hacer pasar el test cambiando lo que mide.
- **No actualizar la especificación cuando cambia el código.** La deriva convierte a la especificación en desinformación; los cambios de comportamiento sin cambio de especificación se rechazan en revisión.
- **Confiar en que el agente agregará seguridad por iniciativa propia.** Autorización, PII y límites deben estar escritos como criterios o como reglas del archivo de instrucciones.

## Para discutir en equipo

- ¿Qué funcionalidad reciente construida con agentes habría cambiado si hubiéramos escrito sus no-objetivos antes de empezar?
- ¿Qué reglas deberían estar hoy en el archivo de instrucciones de nuestros repositorios principales y no están?
- ¿Dónde ponemos el umbral entre "esto merece especificación" y "esto es un cambio directo"?
- ¿Cómo verificamos en CI que cada criterio de aceptación tenga un test, sin volverlo burocrático?
- Si dos agentes trabajan en paralelo, ¿quién es responsable de los contratos entre sus tareas y cuándo se fijan?
