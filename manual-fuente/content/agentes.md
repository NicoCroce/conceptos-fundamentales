---
slug: agentes
titulo: Agentes y tool calling
resumen: Cómo un LLM pasa de responder texto a usar herramientas en un bucle, y qué controles hacen falta para que eso sea seguro y predecible.
lectura: 13
---

## La idea central

Un LLM por sí solo es una función que recibe texto y devuelve texto: no consulta bases de datos, no llama APIs y no sabe qué pasó hace cinco minutos en nuestros sistemas. El **tool calling** (llamada a herramientas) le da una forma de pedir acciones: el modelo dice "quiero ejecutar `consultar_metricas` con estos parámetros", nuestro código la ejecuta y le devuelve el resultado. Un **agente** es simplemente eso repetido en un bucle: el modelo pide una herramienta, recibe el resultado, decide el siguiente paso y así hasta que considera que puede responder.

Una analogía útil es la de un analista nuevo con acceso a un panel de control y una lista de comandos permitidos. Él decide qué mirar y en qué orden, pero no toca nada directamente: cada comando pasa por un operador (nuestro código) que lo valida, lo ejecuta y le entrega la salida. Casi todo lo que importa en ingeniería de agentes está en ese operador: qué comandos existen, quién los autoriza, cuántas veces se pueden pedir y qué queda registrado.

## Conceptos

### Qué es un agente: un LLM en un bucle

La definición más práctica es: **un agente es un LLM que, en un bucle, elige qué herramienta usar a continuación a partir de lo que observó hasta ahora**. No hay magia adicional. El bucle tiene esta forma:

1. Se arma el contexto: instrucciones del sistema, la tarea, la lista de herramientas disponibles y el historial de pasos anteriores.
2. Se llama al modelo.
3. Si el modelo pide una herramienta, el código la ejecuta, agrega el resultado al historial y vuelve al paso 2.
4. Si el modelo responde con texto final, el bucle termina.

La diferencia con una llamada simple a un LLM es que **el camino no está fijado de antemano**: el modelo decide cuántos pasos dar y en qué orden. Eso es lo que lo hace flexible y, al mismo tiempo, lo que lo hace difícil de predecir, testear y acotar en costo.

**Ejemplo:** ante la pregunta "¿por qué cayó la tasa de entregas a tiempo en la zona norte?", un agente podría consultar la métrica, después los pedidos fallidos, después el clima y recién ahí responder. Otro día, con otra alerta, podría dar dos pasos o doce.

**Por qué importa:** cuando alguien propone "hagamos un agente", la primera pregunta es si realmente necesitamos que el modelo decida el camino, o si el camino ya lo conocemos.

### Cómo funciona el tool calling paso a paso

El mecanismo es el mismo en todos los proveedores, aunque el formato exacto de los mensajes cambia:

1. **Definimos las herramientas con un esquema.** Cada herramienta tiene un nombre, una descripción en lenguaje natural (que el modelo lee para decidir cuándo usarla) y un esquema JSON de sus parámetros.
2. **El modelo devuelve una petición, no ejecuta nada.** Si decide usar una herramienta, su respuesta no es texto sino un bloque estructurado del tipo "herramienta X, argumentos Y". El modelo no tiene acceso a la red ni a nuestros sistemas.
3. **Nuestro código ejecuta y devuelve el resultado.** Validamos los argumentos contra el esquema, verificamos permisos, llamamos al servicio real y devolvemos la salida al modelo como un mensaje más del historial.
4. **El modelo decide seguir o responder.** Con el resultado a la vista, puede pedir otra herramienta o dar la respuesta final.

Un ejemplo de definición de herramienta (formato ilustrativo; cada proveedor usa nombres de campos ligeramente distintos):

```json
{
  "name": "consultar_metrica_entregas",
  "description": "Devuelve la tasa de entregas a tiempo para una zona y una ventana de tiempo. Usar para confirmar o descartar una caída antes de investigar causas. Solo lectura.",
  "input_schema": {
    "type": "object",
    "properties": {
      "zona": {
        "type": "string",
        "enum": ["norte", "sur", "este", "oeste", "centro"],
        "description": "Zona operativa de Rumbo."
      },
      "desde": {
        "type": "string",
        "format": "date-time",
        "description": "Inicio de la ventana, en UTC."
      },
      "hasta": {
        "type": "string",
        "format": "date-time",
        "description": "Fin de la ventana, en UTC."
      },
      "agrupar_por": {
        "type": "string",
        "enum": ["hora", "transportista", "franja"],
        "default": "hora"
      }
    },
    "required": ["zona", "desde", "hasta"]
  }
}
```

Fíjate en tres detalles: la descripción dice **cuándo** usarla (no solo qué hace), los valores posibles están acotados con `enum` y la herramienta declara que es de solo lectura. Cuanto más preciso el esquema, menos argumentos inventados.

**Por qué importa:** como el modelo solo "pide", todo el control de seguridad vive en el paso 3. Si una herramienta peligrosa existe y el código la ejecuta sin verificar, el problema no es del modelo sino nuestro.

### Workflow vs. agente: empezar por el workflow

Conviene distinguir dos cosas que a menudo se llaman "agente":

- **Workflow:** una secuencia de pasos definida en código, donde algunos pasos usan un LLM. El camino lo decide el programador. Ejemplo: extraer datos del ticket, clasificarlo, buscar la política relevante, redactar respuesta.
- **Agente:** el LLM decide qué paso sigue. El camino lo decide el modelo.

La regla práctica es **empezar por el workflow** y pasar a agente solo cuando el camino realmente no se puede anticipar. Un workflow es más barato (menos llamadas), más rápido, más fácil de testear (cada paso tiene entrada y salida conocidas) y más fácil de explicar cuando algo sale mal.

| Criterio | Workflow | Agente |
|---|---|---|
| Quién decide el siguiente paso | El código | El modelo |
| Predecibilidad de costo y latencia | Alta | Baja, depende de cuántos pasos dé |
| Testeo | Por paso, como cualquier pipeline | Requiere evaluar trayectorias completas |
| Cuándo conviene | Tareas repetitivas con pasos conocidos | Investigación abierta, problemas con muchas ramas posibles |
| Riesgo con acciones de escritura | Acotado y auditable | Alto si no hay controles extra |

**Ejemplo:** resumir un ticket de soporte siempre sigue los mismos tres pasos; es un workflow. Investigar por qué cayó una métrica puede requerir mirar clima, despliegues, carga de transportistas o un comercio puntual, según lo que vaya apareciendo; ahí un agente aporta.

### Patrones comunes

- **ReAct (Reason + Act):** el modelo alterna razonamiento breve ("necesito ver si hubo lluvia") y acción (llamar a la herramienta). Es el patrón base de casi todos los agentes y el que se ve en la traza de más abajo.
- **Planificador-ejecutor:** un primer paso arma un plan explícito ("1. confirmar caída, 2. segmentar por transportista, 3. revisar despliegues") y luego un ejecutor lo recorre. El plan se puede revisar o validar antes de ejecutar, lo que da más control.
- **Router:** un LLM clasifica la entrada y la deriva a un flujo especializado. Por ejemplo, un ticket de "pedido demorado" va a un flujo, uno de "cambio de dirección" a otro. Es un workflow con una bifurcación decidida por el modelo, y suele ser el primer paso sensato antes de un agente completo.
- **Multiagente con supervisor:** un agente supervisor reparte subtareas a agentes especializados (uno para métricas, otro para logs, otro para redactar) y combina sus resultados. Suena elegante, pero multiplica llamadas, costo y puntos de falla. Conviene solo cuando las subtareas son realmente independientes y cada especialista necesita herramientas o contexto muy distintos.

**Por qué importa:** casi siempre el patrón más simple que resuelve el problema es el correcto. Un router con tres workflows suele ganarle a un sistema multiagente en costo, latencia y depuración.

### Memoria de corto y largo plazo

- **Memoria de corto plazo:** el historial de la conversación o de la ejecución actual, que viaja en la ventana de contexto en cada llamada. Crece con cada paso: si cada resultado de herramienta ocupa 2.000 tokens, a los 15 pasos el contexto ya tiene 30.000 tokens solo de resultados. Por eso se resumen o recortan los resultados viejos.
- **Memoria de largo plazo:** información que persiste entre ejecuciones, guardada fuera del modelo (una base de datos, un índice vectorial) y que se recupera cuando hace falta. Ejemplo: "la última vez que cayó la zona norte fue por un corte en la autopista; el runbook es X".

La memoria de largo plazo es, en la práctica, un caso de [RAG](#t/rag): hay que decidir qué se guarda, cómo se recupera y cuándo caduca, porque una memoria vieja o incorrecta contamina decisiones futuras.

### Estado y checkpoints

El **estado** de un agente es todo lo que necesita para continuar: el historial, los resultados intermedios, en qué paso está. Un **checkpoint** es guardar ese estado en almacenamiento persistente después de cada paso.

Esto permite tres cosas: reanudar si el proceso se cae a mitad de camino (sin repetir herramientas ya ejecutadas), pausar para esperar una aprobación humana durante horas, y reproducir una ejecución para depurarla. Frameworks como [LangGraph](#t/langgraph) lo resuelven con un "checkpointer" que guarda el estado en una base como PostgreSQL.

### Humano en el circuito

"Humano en el circuito" (human-in-the-loop) significa que ciertos pasos requieren que una persona apruebe, corrija o rechace antes de continuar. Se aplica a acciones con impacto: escribir en sistemas, contactar clientes, cambiar asignaciones.

La implementación típica: el agente llega a una acción sensible, guarda su estado (checkpoint), genera una propuesta legible ("reprogramar 42 entregas al turno tarde, motivo: corte de ruta") y queda en pausa. Cuando la persona aprueba, se reanuda desde el checkpoint.

**Por qué importa:** permite usar agentes en tareas de riesgo sin delegar la decisión final, y el registro de aprobaciones sirve como auditoría.

### Mínimo privilegio en herramientas

Cada herramienta es una puerta a nuestros sistemas. El principio de mínimo privilegio aplicado a agentes dice:

- Dar solo las herramientas necesarias para la tarea, no "todas por si acaso".
- Preferir herramientas de solo lectura; las de escritura van separadas y con controles extra.
- Acotar parámetros: `enum` en vez de texto libre, rangos máximos, nunca SQL arbitrario.
- Ejecutar con credenciales propias del agente, con permisos limitados, no con las de un administrador.

**Ejemplo:** en vez de una herramienta `ejecutar_sql(query)`, el agente de operaciones tiene `consultar_metrica_entregas(zona, desde, hasta)` y `listar_pedidos_fallidos(zona, desde, hasta, limite<=200)`. Si una inyección de prompt en un comentario de pedido intenta "borra la tabla", no hay herramienta que lo permita.

### Límites de ejecución

Un agente sin límites puede quedar en bucle: pide la misma herramienta una y otra vez, o se va por las ramas. Los límites mínimos son:

- **Máximo de pasos:** por ejemplo, 15 llamadas a herramientas por ejecución.
- **Presupuesto de tokens o de costo:** por ejemplo, 200.000 tokens por ejecución y un tope diario por agente.
- **Timeouts:** por herramienta (10 segundos) y por ejecución completa (5 minutos).
- **Detección de repetición:** si se pide la misma herramienta con los mismos argumentos tres veces, cortar.

Al alcanzar un límite, el agente no debe fallar en silencio: devuelve lo que encontró hasta ahí y avisa que no terminó.

### Multiplicación de errores

Si cada paso de un agente sale bien con probabilidad 0,95, la probabilidad de que una ejecución de 10 pasos salga bien de punta a punta es 0,95 elevado a 10, aproximadamente **0,60**. Es decir, cuatro de cada diez ejecuciones tienen al menos un paso mal. Con 20 pasos baja a cerca de 0,36.

Esto explica por qué los agentes largos se sienten poco confiables aunque cada paso individual parezca bueno, y por qué conviene: reducir pasos, validar resultados intermedios con código, y cortar tareas largas en workflows con puntos de control.

### Herramientas idempotentes

Una operación es **idempotente** si ejecutarla dos veces tiene el mismo efecto que ejecutarla una vez. En agentes es crítico porque los reintentos son frecuentes: el modelo puede pedir lo mismo dos veces, un timeout puede disparar un reintento aunque la primera llamada sí se haya ejecutado, o el proceso se reanuda desde un checkpoint.

La técnica habitual es una **clave de idempotencia**: cada acción de escritura lleva un identificador único (por ejemplo, `reprogramacion:{pedido_id}:{fecha}`), y el servicio receptor ignora pedidos repetidos con la misma clave.

**Ejemplo:** sin idempotencia, un reintento de "enviar SMS al destinatario avisando la demora" manda dos SMS. Con clave de idempotencia, el segundo se descarta.

### Trazas por paso

Una **traza** registra cada paso de la ejecución: qué vio el modelo, qué pidió, con qué argumentos, qué devolvió la herramienta, cuánto tardó y cuántos tokens consumió. Sin trazas, depurar un agente es adivinar. Se integran naturalmente con [OpenTelemetry](#t/opentelemetry): cada ejecución es una traza y cada llamada al modelo o a una herramienta es un span.

Traza de ejemplo del agente de operaciones de Rumbo ante la alerta "cayó la tasa de entregas a tiempo en la zona norte":

```text
ejecucion_id: ops-7f3a  | alerta: entregas_a_tiempo_norte < 85%  | limite: 15 pasos

Paso 1  [modelo] Razonamiento: confirmar la caída y su forma antes de buscar causas.
        [tool]   consultar_metrica_entregas(zona="norte", desde="14:00", hasta="18:00", agrupar_por="hora")
        [result] 14h 93% | 15h 91% | 16h 79% | 17h 76%        (320 ms, 410 tokens)

Paso 2  [modelo] La caída empieza a las 16h. Ver si es general o de algunos transportistas.
        [tool]   consultar_metrica_entregas(zona="norte", desde="16:00", hasta="18:00", agrupar_por="transportista")
        [result] 3 de 41 transportistas concentran el 70% de las demoras   (290 ms, 650 tokens)

Paso 3  [modelo] Revisar carga de esos 3 transportistas.
        [tool]   consultar_carga_transportistas(ids=["T-118","T-204","T-377"])
        [result] promedio 14 pedidos activos (habitual: 6)     (180 ms, 300 tokens)

Paso 4  [modelo] Sobrecarga anómala. ¿Cambió algo en la asignación?
        [tool]   listar_despliegues(servicio="asignacion", desde="12:00")
        [result] v2.31.0 desplegada 15:42, cambio: "nuevo peso por cercanía"   (150 ms, 220 tokens)

Paso 5  [modelo] Coincide en tiempo. Tengo evidencia suficiente para responder.
        [final]  Hipótesis: el deploy v2.31.0 del servicio de asignación concentra pedidos
                 en pocos transportistas cercanos. Sugerencia: evaluar rollback. No se
                 ejecutó ninguna acción.

Total: 5 pasos | 6.100 tokens | 9,8 s | costo estimado: centavos de dólar
```

Fíjate en que todas las herramientas son de solo lectura, que cada paso deja registro de su razonamiento breve y que el agente **sugiere** el rollback pero no lo ejecuta.

### MCP (Model Context Protocol)

**MCP** es un protocolo abierto para conectar modelos con herramientas y fuentes de datos de forma estándar. En vez de que cada aplicación defina sus integraciones a mano, un **servidor MCP** expone herramientas (con su nombre, descripción y esquema), recursos de solo lectura y plantillas de prompt; un **cliente MCP** (la aplicación que usa el LLM) los descubre y los ofrece al modelo.

**Ejemplo:** el equipo de plataforma publica un servidor MCP "rumbo-metricas" con las herramientas de consulta de métricas. El agente de operaciones, un asistente en el IDE y un bot de chat interno lo usan sin reimplementar nada.

**Por qué importa:** facilita reutilizar herramientas, pero no resuelve la seguridad. Un servidor MCP de terceros es código y descripciones que el modelo va a leer y obedecer; hay que revisarlos, fijar versiones y aplicar el mismo mínimo privilegio que a cualquier otra herramienta.

## Casos prácticos

### Investigar una caída de entregas a tiempo con herramientas de solo lectura

**Situación:** el equipo de operaciones recibe varias alertas por semana del tipo "cayó la tasa de entregas a tiempo en la zona X" y cada investigación manual lleva 30 a 60 minutos de cruzar paneles.

**Qué se hace:** se construye el agente de operaciones con cinco herramientas de solo lectura (métricas, pedidos fallidos, carga de transportistas, clima, despliegues recientes), un límite de 15 pasos y 5 minutos, y trazas completas. El agente produce un informe con hipótesis y evidencia, y una persona decide qué hacer. Como no puede escribir nada, el peor caso es un informe equivocado, que la persona detecta revisando la evidencia citada. Es un buen primer uso de agentes justamente porque el riesgo es bajo y el camino de investigación varía mucho de una alerta a otra.

### Un agente que reprograma entregas o compensa a clientes

**Situación:** se propone que el agente, además de investigar, reprograme automáticamente las entregas afectadas y envíe a los comercios un cupón de envío gratis como compensación.

**Qué se hace:** estas son acciones de riesgo alto, así que se diseñan distinto:

- **Workflow fijo, no agente libre:** el agente solo propone; la ejecución la hace un workflow con pasos definidos (seleccionar pedidos según criterio explícito, generar propuesta, aprobar, ejecutar).
- **Aprobación humana:** nada se ejecuta sin que una persona de operaciones apruebe la propuesta, con el detalle de cuántos pedidos y comercios se afectan.
- **Idempotencia:** cada reprogramación y cada cupón llevan clave única por pedido; un reintento no duplica.
- **Topes:** máximo de pedidos por lote (por ejemplo, 200), máximo de cupones por comercio por día, y alerta si una propuesta supera un umbral.

Así el agente aporta velocidad en el análisis sin que un error de razonamiento se convierta en cientos de acciones irreversibles.

### Agente en bucle que gasta cientos de dólares en una noche

**Situación:** un prototipo de agente quedó corriendo con un disparador nocturno. Una herramienta devolvía un error intermitente, el modelo reintentaba con argumentos levemente distintos y cada paso arrastraba un contexto cada vez más largo. A la mañana, la factura del proveedor mostraba cientos de dólares en una noche (cifra hipotética, pero el orden de magnitud es realista).

**Qué se hace:** se agregan límites en varias capas: máximo de pasos por ejecución, presupuesto de tokens por ejecución, detección de llamadas repetidas, timeout total y tope de gasto diario por agente en el gateway (ver [LLMs en producción](#t/llms-produccion)). Además, se alerta cuando el costo por hora de un agente supera su media histórica y los errores de herramientas se devuelven al modelo con un mensaje claro ("servicio no disponible, no reintentar") en vez de un stack trace ambiguo.

## Errores comunes

- **Construir un agente cuando alcanzaba un workflow.** Si los pasos se conocen de antemano, un pipeline con llamadas al LLM es más barato, rápido y testeable.
- **Dar herramientas genéricas y poderosas.** Una herramienta `ejecutar_sql` o `llamar_api(url)` convierte cualquier error o inyección en un incidente; mejor herramientas específicas con parámetros acotados.
- **No poner límites de pasos, tokens y tiempo.** Un agente sin topes tarde o temprano entra en bucle; los límites se definen antes del primer deploy, no después de la primera factura.
- **Acciones de escritura sin idempotencia.** Los reintentos son parte normal del bucle; sin clave de idempotencia se duplican mensajes, reprogramaciones o cupones.
- **Descripciones de herramientas vagas.** El modelo elige herramientas leyendo su descripción; si dice solo "obtiene datos", la va a usar mal o no la va a usar.
- **No guardar trazas.** Sin el registro de cada paso no hay forma de saber por qué el agente concluyó lo que concluyó ni de construir casos de evaluación.

## Para discutir en equipo

- ¿Cuáles de nuestros procesos que hoy llamamos "agente" son en realidad workflows, y qué ganaríamos reescribiéndolos así?
- Si el agente de operaciones tuviera que ejecutar un rollback del servicio de asignación, ¿qué controles exigiríamos antes de permitirlo?
- ¿Qué presupuesto de pasos, tokens y tiempo es razonable para una investigación de alerta, y cómo lo validamos con datos?
- ¿Cómo revisamos un servidor MCP de terceros antes de conectarlo a un agente interno?
- Con la multiplicación de errores en mente, ¿dónde convendría poner validaciones por código entre pasos?
