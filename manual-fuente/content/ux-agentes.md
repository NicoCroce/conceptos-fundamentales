---
slug: ux-agentes
titulo: UX de interfaces con agentes
resumen: Cómo diseñar la experiencia de usar un agente: cuándo conviene el chat, latencia percibida, transparencia, aprobaciones, errores, traspaso a personas y cómo medir si funciona.
lectura: 16
---

## La idea central

Una interfaz tradicional muestra lo que se puede hacer: botones, menús, campos. Una interfaz con agente invierte la relación: la persona dice lo que quiere y el sistema decide cómo hacerlo. Eso es poderoso (una frase reemplaza diez pantallas) y frágil, porque la persona ya no ve las opciones, no sabe qué entendió el sistema, no sabe qué está haciendo mientras tanto y no siempre puede deshacer lo hecho. Casi todos los problemas de UX con agentes vienen de ahí: expectativas, visibilidad y control.

La analogía es delegar una tarea en alguien que recién entra al equipo. Funciona cuando sabemos qué puede hacer, nos cuenta en qué está, consulta antes de algo importante, avisa cuando no sabe y nos pasa con otra persona si se le escapa. Funciona mal cuando promete de más, desaparece diez minutos o actúa sin preguntar. Este tema baja esa intuición a decisiones de diseño para el asistente de soporte, el agente de operaciones y el asistente del panel de comercios de Rumbo. Los componentes que lo implementan están en [Design systems](#t/design-systems); el funcionamiento técnico, en [Agentes y tool calling](#t/agentes).

## Conceptos

### Cuándo el chat es (y no es) la interfaz correcta

El chat sirve cuando la intención es variada y difícil de anticipar, cuando la persona no conoce la estructura del sistema o cuando la tarea combina varias consultas. Es malo para tareas repetitivas, con pocas opciones conocidas, que requieren comparar muchos datos o que necesitan precisión (fechas, cantidades, direcciones).

| Situación | Mejor opción |
|---|---|
| "¿Por qué se atrasó este pedido y qué opciones tengo?" | Chat: pregunta abierta que combina datos y políticas |
| Marcar un pedido como entregado | Botón: una acción, cientos de veces por día |
| Ver los 300 pedidos de hoy y filtrar por zona | Tabla con filtros: comparar y escanear |
| Reprogramar un pedido | Mixto: el agente propone, un selector de franjas confirma |
| Investigar una caída de entregas a tiempo | Agente con panel de evidencia: tarea abierta de varios pasos |

**Ejemplo:** el primer prototipo del panel reemplazaba el formulario de alta de pedidos por un chat ("Cuéntame el pedido"). Los comercios tardaban el doble porque tenían que recordar qué datos hacían falta, y el modelo a veces leía mal un número de calle. La versión final mantiene el formulario y suma un asistente que lo completa a partir de un mensaje pegado, mostrando los campos para revisar.

**Por qué importa:** un chat donde alcanza un botón agrega latencia, costo y errores. La pregunta no es dónde poner el agente, sino qué tarea cuesta hoy y el lenguaje la simplifica.

### Establecer expectativas

Un campo vacío con "Pregunta lo que quieras" invita a pedir cosas que el agente no puede resolver. La primera pantalla dice, en concreto:

- **Qué puede hacer, con ejemplos:** "Puedo consultar el estado de tus pedidos, explicar demoras y reprogramar entregas".
- **Qué no:** "No puedo modificar direcciones; eso se hace desde la ficha del pedido".
- **Con qué datos:** "Veo los pedidos de tu comercio de los últimos 90 días".

Cuando el agente rechaza algo, repite el límite y dice adónde ir.

**Ejemplo:** antes del mensaje inicial, un 18 % de las consultas al asistente del panel pedía cosas fuera de alcance y terminaba en "No puedo ayudarte con eso". Con capacidades, límites y tres ejemplos clicables, bajó al 7 %.

**Por qué importa:** prevenir una expectativa equivocada cuesta un texto; repararla cuesta confianza.

### Streaming y latencia percibida

Un modelo genera la respuesta de a fragmentos, así que hay dos tiempos: el **tiempo al primer token** y el **tiempo total**. La latencia que la persona percibe depende mucho más del primero. Con números hipotéticos para el asistente de soporte:

1. Una respuesta típica tiene 240 tokens, generados a unos 40 por segundo: 6 s.
2. Antes de generar, hay recuperación de documentos y una consulta al servicio de pedidos: 1,2 s.
3. **Sin streaming**, la persona mira un indicador 7,2 s y después ve todo junto.
4. **Con streaming**, el primer texto aparece a los 1,2 s más unos 0,3 s: 1,5 s. Después lee mientras se genera el resto, que llega más rápido de lo que se lee (unas 4 a 5 palabras por segundo).
5. Y en menos de 400 ms (el umbral de Doherty, ver [Leyes de UX y diseño visual](#t/leyes-ux-diseno-visual)) se muestra un estado: "Buscando el pedido RB8K2M7Q4X…".

El tiempo total es el mismo; la experiencia, muy distinta. Dos cuidados: el texto que llega no debe hacer saltar el layout ni arrastrar el scroll si la persona subió a releer, y "Detener" debe cortar la generación en el backend, no solo ocultarla.

**Ejemplo:** al activar streaming y un primer estado en 300 ms, las conversaciones abandonadas antes de la primera respuesta bajaron de 9 % a 3 %, sin cambiar de modelo.

**Por qué importa:** optimizar el primer feedback suele ser más barato y efectivo que optimizar el tiempo total.

### Mostrar el progreso de las herramientas

Un agente que hace varios pasos puede tardar diez o veinte segundos. Mostrar el progreso reduce la ansiedad de la espera, da transparencia (qué datos consultó) y permite corregir a tiempo. El detalle depende del público: para un comercio, una línea por paso en lenguaje de negocio ("Revisando la política de reprogramación"); para un operador del agente de operaciones, además, la herramienta, los parámetros y un resumen del resultado, plegables.

**Ejemplo:** el agente de operaciones investiga "cayó la tasa de entregas a tiempo en la zona norte" y muestra: "1. Métricas de entregas de la zona norte (últimas 6 h) · listo. 2. Incidentes abiertos · listo: 1 corte de calle. 3. Carga de transportistas · en curso". Al ver el paso 1, el operador nota que necesitaba 24 h y lo corrige sin esperar el final.

**Por qué importa:** la visibilidad del estado es la primera de las [heurísticas de Nielsen](#t/heuristicas-nielsen), y en un agente el estado es justamente lo que no se ve.

### Confianza y transparencia

La confianza adecuada no es la máxima, sino la que corresponde a cuán confiable es el sistema: con exceso, nadie revisa y los errores pasan; con defecto, nadie lo usa. Dos herramientas la calibran:

- **Fuentes y citas.** En respuestas basadas en documentos ([RAG](#t/rag)), cada afirmación importante enlaza al fragmento de origen. Se puede verificar, y cuando no hay fuente, se nota.
- **Anticipar la acción.** Antes de algo con efectos, el agente muestra qué va a hacer con los parámetros reales, no con una paráfrasis del modelo.

**Ejemplo:** un comercio pregunta si se puede entregar en otra dirección. El asistente dice que sí y cita la política. Al abrir la cita, el comercio ve que dice "dentro del mismo código postal": la respuesta omitía la condición. La cita permitió detectarlo y el caso se sumó al conjunto de evaluación.

**Por qué importa:** sin fuentes, toda respuesta tiene la misma apariencia de certeza, sea correcta o inventada.

### La ficha de aprobación

Cuando el agente propone una acción con efectos (reprogramar, cancelar, avisar a destinatarios), la persona aprueba antes de que ocurra. El diseño decide si la aprobación es real o un clic automático. No puede faltar:

1. **La acción con verbo y objeto:** "Reprogramar 3 pedidos".
2. **Los parámetros reales de la herramienta**, no el texto del modelo.
3. **Las consecuencias:** "Se avisa por SMS a los 3 destinatarios"; "Es la segunda reprogramación de RB8K2M7Q4X; no se podrá reprogramar otra vez".
4. **Botones que nombran la acción**, no "Aceptar".
5. **Editar antes de aprobar**, sin reescribir todo.

```text
Reprogramar 3 pedidos
  RB8K2M7Q4X · mar 12, 14–18 h  →  jue 14, 9–12 h
  RB8K3P1L9Z · mar 12, 14–18 h  →  jue 14, 9–12 h
  RB8K5T6N2W · mar 12, 18–21 h  →  jue 14, 9–12 h
Consecuencias: se avisa por SMS a los 3 destinatarios.
[ Reprogramar 3 pedidos ]  [ Editar franja ]  [ Cancelar ]
```

**Ejemplo:** la primera versión decía "¿Confirmas reprogramar los pedidos afectados?" con "Sí / No". Un comercio aprobó y se reprogramaron 14 pedidos en lugar de 3, porque el agente interpretó "los afectados" de forma amplia. Con la lista explícita, el error se ve antes de aprobar.

**Por qué importa:** la aprobación humana es un control de seguridad (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)) solo si la persona ve lo que aprueba.

### Niveles de confirmación según el riesgo y deshacer

Pedir confirmación para todo entrena a aprobar sin leer; no pedirla nunca es peligroso. Una escala por riesgo:

| Nivel | Tipo de acción | Patrón |
|---|---|---|
| 0 | Lectura (consultar estado, buscar políticas) | Sin confirmación; visible en el progreso |
| 1 | Reversible y de bajo impacto (nota interna en el pedido) | Se ejecuta y se ofrece "Deshacer" unos segundos |
| 2 | Con efecto externo (reprogramar, avisar al destinatario) | Ficha de aprobación con parámetros y consecuencias |
| 3 | Irreversible o masiva (cancelar, más de 20 pedidos) | Ficha más un paso extra: escribir la cantidad |

"Deshacer" es mejor que "¿Estás seguro?" porque no interrumpe, pero el backend tiene que soportarlo de verdad: un SMS enviado no se deshace, así que una acción que avisa al destinatario es nivel 2 aunque el cambio de franja sea reversible.

**Ejemplo:** en el agente de operaciones, reprogramar 5 pedidos es nivel 2 y reprogramar 180 es nivel 3, con "escribe 180 para confirmar". El umbral de 20 salió de revisar tres meses de acciones: el 95 % afectaba a menos.

**Por qué importa:** la fricción es un recurso escaso; gastarla en lo trivial la agota para lo importante.

### Errores, incertidumbre y traspaso a una persona

Un agente falla de formas distintas, y cada una necesita su mensaje:

- **No sabe:** "No encontré una política sobre entregas en feriados. Puedo pasarte con un operador."
- **No puede:** "No puedo cambiar la dirección; se hace desde la ficha del pedido", con enlace.
- **Falló un servicio:** "No pude consultar el pedido ahora", con "Reintentar".
- **No está seguro:** pregunta en lugar de adivinar: "¿Te refieres al pedido de hoy o al de ayer?".

El modelo tiende a contestar algo aunque no sepa; parte del trabajo es diseñar "no sé" como respuesta legítima en el prompt y en las herramientas, y mostrarla bien.

El **traspaso a una persona** es la salida cuando el agente no resuelve. Bien hecho, se ofrece de forma visible, el operador recibe un resumen del caso para no hacer repetir todo y se informa cuánto tarda la atención. Mal hecho, es un bucle de "¿Puedo ayudarte con algo más?".

**Ejemplo:** el asistente de soporte deriva cuando la confianza de la clasificación es baja, cuando la persona lo pide dos veces o tras dos respuestas marcadas como no útiles. El operador ve: "Comercio consulta por RB8K2M7Q4X, entregado según el sistema; el destinatario dice que no lo recibió. Foto de comprobante revisada: puerta cerrada, sin paquete visible".

**Por qué importa:** el cierre pesa mucho en cómo se recuerda una conversación; un buen traspaso convierte un fallo del agente en una buena experiencia.

### Reparar la conversación y entradas estructuradas

Las conversaciones se desvían: el agente entendió mal, la persona cambió de idea. Reparar es corregir sin empezar de cero: **editar** un mensaje anterior y regenerar desde ahí, **regenerar** una respuesta, aceptar **correcciones dirigidas** ("no, el de ayer") que cambian solo eso, y **mostrar lo que el agente entendió** en tareas de varios pasos ("Entendí: reprogramar RB8K2M7Q4X al jueves por la mañana").

En paralelo, no todo tiene que ser texto libre. Los **prompts sugeridos** según el contexto ("¿Dónde está este pedido?" en la ficha de un pedido) muestran capacidades; las **respuestas rápidas** ofrecen el siguiente paso; y las **entradas estructuradas** dentro del chat (un selector de franjas, de pedidos o de fecha) resuelven lo que debe ser exacto.

**Ejemplo:** un comercio pide reprogramar "el pedido de Marta" y hay dos destinatarias con ese nombre. El asistente muestra las dos opciones con dirección y fecha, y elegir es un clic. Después, a "pásalo a la semana que viene a la tarde" responde con un selector de las 4 franjas con capacidad: un toque, sin ambigüedad.

**Por qué importa:** el lenguaje es bueno para la intención y los controles para los datos precisos; combinarlos reduce errores y turnos.

### UI generativa: el agente devuelve componentes

En la UI generativa, el agente no solo devuelve texto: elige componentes de la interfaz, como una ficha de pedido, una línea de tiempo o un selector de franjas. Técnicamente, llama a una herramienta como `mostrar_linea_de_tiempo(pedido_id)` y el frontend dibuja el componente del design system con datos reales del backend. Los datos son exactos, la presentación es consistente y accesible, y los componentes pueden ser interactivos. El riesgo es dejar que el modelo genere HTML o estilos arbitrarios, que abre la puerta a inyecciones e inconsistencias: la regla es un **catálogo cerrado** y el modelo solo elige cuál y con qué identificadores.

**Ejemplo:** a "¿Qué pasó con mi pedido RB8K2M7Q4X?", el asistente responde con una oración ("Se atrasó por un corte de calle; llega hoy entre 16 y 17 h") y el componente `LineaDeTiempoPedido` con los eventos reales de Kafka: creado, asignado, retirado, desvío, ETA actualizada.

**Por qué importa:** la mayor fuente de errores en respuestas de estado es que el modelo reescriba datos; con UI generativa, el modelo explica y el sistema muestra.

### Tono y UX writing del asistente

El asistente tiene una voz, se diseñe o no. Una guía breve, reflejada en el prompt del sistema, decide: tono (claro y directo, más simple para destinatarios), persona gramatical (primera persona y siempre el mismo tratamiento), nada de emociones fingidas ni presentarse como humano, disculpas breves y proporcionadas, y microtextos claros en botones, estados y errores: "Detener" mejor que "Abortar generación"; "No encontré ese pedido, ¿puedes revisar el código?" mejor que "Error 404".

**Ejemplo:** el asistente para destinatarios decía "Su envío se encuentra en estado de asignación pendiente". Con la guía: "Tu pedido todavía no salió. Te avisamos cuando un repartidor lo retire".

**Por qué importa:** el tono afecta la confianza tanto como la precisión, y se ajusta sin cambiar modelo ni herramientas.

### Medir la UX del agente

Las métricas de calidad del modelo ([Evaluación de LLMs](#t/evaluacion-llms)) no alcanzan: un modelo puede responder bien y la experiencia ser mala. Métricas de experiencia:

- **Éxito de la tarea:** conversaciones en las que la persona logró lo que buscaba (etiquetado de una muestra o señales del sistema, como una reprogramación hecha).
- **Deflexión frente a resolución:** la deflexión cuenta conversaciones que no llegaron a un operador; la resolución, las que resolvieron el problema.
- **Tasa de derivación**, con su motivo.
- **CSAT** al final de la conversación, sabiendo que responde una minoría y con sesgo hacia los extremos.
- **Fricción:** reformulaciones, respuestas marcadas como no útiles, abandonos.

**Ejemplo:** en un mes, 10.000 conversaciones; 7.000 no llegaron a un operador: deflexión del 70 %. Pero 1.500 de esas personas volvieron a contactar por el mismo pedido en 48 h y 500 reclamaron por otro canal. Resolución: (7.000 − 1.500 − 500) / 10.000 = 50 %. Reportar 70 % ocultaba que una de cada tres "deflexiones" era un abandono.

**Por qué importa:** optimizar solo la deflexión empuja a esconder la ayuda humana; la métrica que importa es la resolución.

### Accesibilidad del chat y patrones oscuros

El chat tiene desafíos de accesibilidad propios, desarrollados en [Accesibilidad web](#t/accesibilidad): anunciar el inicio y el fin de la respuesta y no cada fragmento, mover el foco a la ficha de aprobación, que todo funcione con teclado y que los componentes generativos tengan nombres accesibles.

Y hay **patrones oscuros** (diseños que llevan a hacer algo que la persona no haría si entendiera bien) propios de los agentes:

- **Escritura falsa:** demorar la respuesta con "Escribiendo…" para parecer humano.
- **Exagerar capacidades** o responder con certeza sin fuente.
- **Humanizar de más:** nombre y foto de persona sin aclarar que es automático.
- **Esconder la salida a una persona** para mejorar la deflexión.
- **Confirmaciones sesgadas:** aprobar destacado y con foco por defecto en acciones irreversibles.

**Ejemplo:** una propuesta de "humanizar" el asistente sugería nombre propio, foto y 2 segundos de "Escribiendo…" antes de cada respuesta. Se descartó: la demora contradecía el trabajo en latencia y el nombre sugería una persona. Se llama "Asistente de Rumbo" y lo dice en el primer mensaje.

**Por qué importa:** los patrones oscuros mejoran una métrica a corto plazo y destruyen la confianza, que es lo que habilita delegar tareas en un agente.

## Casos prácticos

### El asistente que prometía de más

**Situación:** el asistente del panel se lanzó con un campo de texto y "¿En qué te puedo ayudar?". En dos semanas, el 22 % de las conversaciones termina en "No puedo ayudarte con eso" y el CSAT es 2,9 sobre 5.

**Qué se hace:** mensaje inicial con capacidades, límites y alcance de datos; prompts sugeridos según la pantalla; toda respuesta de "no puedo" dice adónde ir. Se clasifican los pedidos fuera de alcance para decidir cuáles sumar como capacidad, y se mide la tasa de "no puedo" y el CSAT cuatro semanas después.

### Aprobaciones sin leer

**Situación:** el agente de operaciones pide aprobación para todo, incluidas las lecturas. Los operadores aprueban unas 60 veces por turno sin leer, y una reprogramación de 180 pedidos se aprobó por error.

**Qué se hace:** se aplica la escala de riesgo: las lecturas no piden aprobación, las notas internas usan "Deshacer", las reprogramaciones usan la ficha con parámetros y consecuencias, y por encima de 20 pedidos se escribe la cantidad. Las aprobaciones bajan a unas 8 por turno y quedan registradas con la traza del agente.

### Deflexión alta, comercios enojados

**Situación:** el tablero muestra 70 % de deflexión, el objetivo era 75 % y alguien propone mover "Hablar con un operador" a un submenú.

**Qué se hace:** la métrica principal pasa a ser la resolución (50 %). Analizando las derivaciones por motivo, el 40 % son entregas que el destinatario niega haber recibido, un caso que requiere una persona: para esos, el traspaso se hace más rápido y con resumen. El agente se mejora en los motivos que sí puede resolver, y se entrevista a comercios que recontactaron (ver [Investigación y pruebas de usabilidad](#t/investigacion-usabilidad)).

## Errores comunes

- **Chat para todo.** Las tareas precisas o repetitivas van mejor con formularios, tablas y botones; el chat, donde la intención es abierta.
- **Aprobar texto en lugar de acciones.** La ficha muestra parámetros reales y consecuencias, con un botón que nombra la acción.
- **La misma fricción para todo.** Se gradúa por riesgo y se usa "Deshacer" donde el backend lo permite.
- **Errores genéricos.** "Algo salió mal" no distingue "no sé", "no puedo" y "falló un servicio"; cada uno tiene su mensaje y su salida.
- **Medir solo deflexión.** Premia esconder la ayuda humana; se mide resolución, éxito de la tarea y recontactos.
- **Humanizar con engaños.** Escritura falsa, nombres de persona y certeza sin fuentes dañan la confianza.

## Para discutir en equipo

- ¿Qué tareas que hoy resolvemos con chat serían mejores como formulario, tabla o botón, y al revés?
- ¿Qué acciones de nuestros agentes van en cada nivel de la escala de riesgo, y quién decide los umbrales?
- ¿Qué ve hoy un operador al recibir una conversación derivada, y qué le falta para no hacer repetir a la persona?
- ¿Qué métrica de experiencia del agente reportaríamos, y cómo evitamos optimizarla a costa de la resolución?
- ¿Qué componentes debería poder devolver el agente como UI generativa, y cuáles nunca?
