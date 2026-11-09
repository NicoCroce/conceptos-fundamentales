---
slug: langgraph
titulo: LangGraph y LangChain
resumen: Qué aportan LangChain, LangGraph y LangSmith para construir aplicaciones con LLMs y agentes, y cuándo conviene usarlos o quedarse con el SDK del proveedor.
lectura: 11
---

## La idea central

Cuando una aplicación con LLM crece, aparecen problemas repetidos: cambiar de proveedor de modelo, armar prompts a partir de plantillas, buscar documentos, llamar herramientas, guardar el estado de una conversación larga, pausar para que una persona apruebe. **LangChain** nació como una caja de piezas para esos problemas; **LangGraph**, del mismo ecosistema, se enfoca en orquestar flujos con estado (workflows y agentes) como un grafo; **LangSmith** es la herramienta para ver trazas y correr evaluaciones.

La pregunta útil no es "¿usamos LangChain o no?", sino **qué problema concreto nos resuelve cada pieza y qué nos cuesta**. Un framework ahorra código repetido y da patrones probados, pero agrega una capa entre nosotros y el prompt real que llega al modelo, y cambia seguido. Para un flujo con estado, pausas y reintentos, LangGraph suele pagar ese costo. Para un único prompt, casi nunca.

## Conceptos

### LangChain: componentes

LangChain es una biblioteca (en Python y JavaScript) que ofrece interfaces comunes para las piezas típicas de una aplicación con LLM. Las principales:

- **Integraciones con modelos:** una interfaz uniforme para llamar a distintos proveedores (modelos de chat, de embeddings). Cambiar de proveedor pasa a ser, en teoría, cambiar una clase.
- **Plantillas de prompt:** textos con variables (`"Clasifica este ticket: {texto}"`) que se completan en tiempo de ejecución, con soporte para mensajes de sistema, ejemplos y formato de salida.
- **Retrievers:** componentes que, dada una consulta, devuelven documentos relevantes desde una base vectorial u otra fuente. Son la pieza central de un pipeline de [RAG](#t/rag).
- **Herramientas:** funciones con nombre, descripción y esquema de argumentos que se pueden ofrecer a un modelo para [tool calling](#t/agentes).
- **Parsers de salida:** convierten la respuesta del modelo en estructuras (JSON, objetos tipados) y validan el formato.

Estas piezas se encadenan: plantilla, modelo, parser. Es cómodo para prototipos, pero cada eslabón agrega comportamiento implícito (reintentos, formateo de mensajes, prompts internos) que no siempre es evidente.

**Ejemplo:** el asistente de soporte de Rumbo usa un retriever sobre manuales y políticas, una plantilla que inserta los fragmentos recuperados y un parser que exige una respuesta con campos `respuesta` y `fuentes`.

### LangGraph: grafo de estados

LangGraph modela una aplicación como un **grafo de estados**. Sus elementos:

- **Estado compartido:** una estructura (típicamente un diccionario tipado) que todos los nodos leen y actualizan. Contiene, por ejemplo, el pedido, la evidencia recolectada, la clasificación y el borrador de respuesta.
- **Nodos:** funciones que reciben el estado y devuelven actualizaciones. Un nodo puede llamar a un LLM, a una herramienta o ser código puro (validar un formato, consultar una base).
- **Aristas fijas:** "después de A, siempre B".
- **Aristas condicionales:** una función mira el estado y decide a qué nodo ir. Es el lugar donde se ramifica el flujo: "si el impacto es alto, ir a revisión humana; si no, a redactar".
- **Ciclos:** un nodo puede volver a uno anterior. Así se implementa el bucle de un agente (modelo, herramienta, modelo) o un "validar y, si falla, corregir".
- **Checkpointer:** guarda el estado después de cada paso en un almacenamiento persistente (memoria para pruebas, PostgreSQL u otra base en producción). Permite reanudar tras una caída, retomar conversaciones y depurar reproduciendo ejecuciones.
- **Interrupciones:** el grafo puede pausarse antes o después de un nodo, persistir el estado y esperar una entrada externa, típicamente la aprobación de una persona. Cuando llega, se reanuda desde el checkpoint.

Lo valioso es que hace **explícito** el flujo: cualquiera puede leer el grafo y saber qué pasos existen, dónde decide el modelo y dónde decide el código. Eso encaja con la regla de "empezar por el workflow": se puede tener un grafo casi lineal con un único punto de decisión, y agregar autonomía solo donde haga falta.

**Por qué importa:** pausas para aprobación, reanudación tras fallas y estado persistente son difíciles de hacer bien a mano. Ahí está el valor real de LangGraph, más que en las llamadas al modelo.

### Ejemplo: grafo de reclamos por entrega fallida en Rumbo

Cuando un comercio reclama por una entrega fallida, el flujo es:

1. **Extraer evidencia:** leer el pedido y los eventos de seguimiento (creado, asignado, retirado, fallido), con hora, ubicación y notas del transportista.
2. **Clasificar el motivo:** con un LLM, elegir entre categorías cerradas (destinatario ausente, dirección incorrecta, demora del transportista, daño, otro), con una justificación breve basada en la evidencia.
3. **Evaluar impacto (arista condicional):** si el comercio es grande, si hay muchos pedidos involucrados o si el motivo implica responsabilidad de Rumbo, ir a revisión humana; si no, seguir directo.
4. **Revisión humana:** interrupción; una persona de soporte confirma o corrige la clasificación.
5. **Redactar respuesta:** el LLM redacta el mensaje al comercio usando la evidencia y las políticas vigentes.
6. **Validar:** código que verifica el formato, que no haya datos personales del destinatario en el texto y que las fechas citadas existan en la evidencia. Si falla, vuelve a redactar (máximo dos intentos).
7. **Enviar:** registrar la respuesta en el sistema de tickets, con clave de idempotencia por reclamo.

```text
                 +--------------------+
   inicio ---->  | extraer_evidencia  |
                 +---------+----------+
                           |
                           v
                 +--------------------+
                 | clasificar_motivo  |
                 +---------+----------+
                           |
                   [ impacto alto? ]
                    /             \
                  si               no
                  /                 \
                 v                   |
     +----------------------+        |
     | revision_humana      |        |
     | (interrupcion)       |        |
     +----------+-----------+        |
                \                   /
                 v                 v
                 +--------------------+
            +--> | redactar_respuesta |
            |    +---------+----------+
            |              |
            |              v
            |    +--------------------+
            |    |      validar       |
            |    +---------+----------+
            |              |
            +---- falla ---+ ok
         (max 2 intentos)  |
                           v
                 +--------------------+
                 |      enviar        | ----> fin
                 +--------------------+
```

Un esqueleto ilustrativo en Python. Es **pseudocódigo cercano a LangGraph**: los nombres de clases y funciones pueden variar entre versiones, así que no hay que tomarlo como API exacta.

```python
from typing import TypedDict, Literal

class EstadoReclamo(TypedDict, total=False):
    reclamo_id: str
    pedido: dict
    eventos: list[dict]
    motivo: str
    justificacion: str
    impacto_alto: bool
    aprobado_por: str
    borrador: str
    intentos_redaccion: int
    errores_validacion: list[str]

def extraer_evidencia(estado: EstadoReclamo) -> dict:
    pedido = pedidos_api.obtener(estado["pedido"]["id"])
    eventos = seguimiento_api.eventos(pedido["id"])
    return {"pedido": pedido, "eventos": eventos}

def clasificar_motivo(estado: EstadoReclamo) -> dict:
    salida = llm_clasificador.invocar(estado["pedido"], estado["eventos"])
    impacto = evaluar_impacto(estado["pedido"], salida.motivo)  # regla en código
    return {"motivo": salida.motivo, "justificacion": salida.justificacion,
            "impacto_alto": impacto}

def ruta_por_impacto(estado: EstadoReclamo) -> Literal["revision_humana", "redactar"]:
    return "revision_humana" if estado["impacto_alto"] else "redactar"

def validar(estado: EstadoReclamo) -> dict:
    errores = verificar_formato_pii_y_fechas(estado["borrador"], estado["eventos"])
    return {"errores_validacion": errores}

def ruta_validacion(estado: EstadoReclamo) -> Literal["redactar", "enviar", "escalar"]:
    if not estado["errores_validacion"]:
        return "enviar"
    return "redactar" if estado.get("intentos_redaccion", 0) < 2 else "escalar"

grafo = StateGraph(EstadoReclamo)
grafo.add_node("extraer_evidencia", extraer_evidencia)
grafo.add_node("clasificar", clasificar_motivo)
grafo.add_node("revision_humana", revision_humana)   # nodo con interrupción
grafo.add_node("redactar", redactar_respuesta)
grafo.add_node("validar", validar)
grafo.add_node("enviar", enviar_respuesta)            # usa clave de idempotencia
grafo.add_node("escalar", escalar_a_soporte)

grafo.set_entry_point("extraer_evidencia")
grafo.add_edge("extraer_evidencia", "clasificar")
grafo.add_conditional_edges("clasificar", ruta_por_impacto)
grafo.add_edge("revision_humana", "redactar")
grafo.add_edge("redactar", "validar")
grafo.add_conditional_edges("validar", ruta_validacion)

app = grafo.compile(
    checkpointer=CheckpointerPostgres(conexion),
    interrupt_before=["revision_humana"],
)

# Cada reclamo usa su propio hilo de estado, identificado por reclamo_id.
app.invoke({"reclamo_id": "R-1043", "pedido": {"id": "P-88121"}},
           config={"thread_id": "R-1043"})
```

Detalles a notar: la decisión de impacto es una **regla en código**, no del LLM; el ciclo de redacción tiene un tope; y el envío es idempotente. El LLM interviene en dos nodos (clasificar y redactar), el resto es código común y testeable.

### LangSmith: trazas y evals

LangSmith es una plataforma (servicio gestionado, con opción de instalación propia según el plan) para:

- **Trazas:** ver cada ejecución como un árbol de pasos, con el prompt exacto enviado al modelo, la respuesta, tokens, latencia y errores. Es la forma más directa de responder "¿qué le llegó realmente al modelo?" cuando se usa un framework.
- **Datasets y evaluaciones:** guardar casos de prueba (por ejemplo, reclamos reales con su clasificación correcta), correr el flujo sobre ellos y comparar versiones de prompt o de modelo con métricas. Es la misma idea que se desarrolla en [Evaluación de LLMs](#t/evaluacion-llms).

No es obligatorio: trazas equivalentes se pueden emitir con OpenTelemetry hacia la plataforma de observabilidad que ya tengamos. La decisión suele depender de dónde pueden vivir los datos (las trazas contienen prompts y, potencialmente, datos personales) y de qué herramientas ya usa el equipo.

### Cuándo un framework suma y cuándo estorba

**Suma** cuando:

- Hay estado que persistir entre pasos o entre sesiones.
- Hacen falta pausas para aprobación humana y reanudación.
- El flujo tiene ramas y ciclos que conviene ver explícitos.
- Varias aplicaciones comparten patrones y el equipo quiere un estándar.

**Estorba** cuando:

- **La abstracción oculta el prompt real.** Algunas cadenas agregan instrucciones o reformatean mensajes; cuando el modelo responde raro, hay que excavar varias capas para ver qué se le envió.
- **Las versiones cambian seguido.** Estos frameworks evolucionan rápido; las APIs se deprecan y cambian comportamientos entre versiones menores. Cada actualización es un riesgo.
- **El caso es simple.** Una llamada con un prompt y una salida estructurada se escribe en pocas líneas con el SDK del proveedor, sin dependencias extra.

| Situación | Recomendación |
|---|---|
| Un prompt, una salida estructurada | SDK del proveedor directo |
| Pipeline lineal de 2 a 4 pasos sin pausas | SDK directo o funciones propias; framework opcional |
| RAG con varias fuentes y rerankeo | LangChain puede ahorrar integraciones, con cuidado de ver el prompt final |
| Flujo con ramas, reintentos, estado persistente y aprobación humana | LangGraph aporta mucho |
| Agente con herramientas y checkpoints | LangGraph o similar |

**Por qué importa:** la elección de framework es una dependencia de largo plazo. Conviene que sea una decisión consciente, revisada como cualquier otra pieza de arquitectura.

## Casos prácticos

### Flujo de reclamos por entrega fallida

**Situación:** soporte recibe cientos de reclamos por día por entregas fallidas. Hoy cada agente humano busca el pedido, revisa el seguimiento, decide el motivo y redacta la respuesta.

**Qué se hace:** se implementa el grafo descrito arriba con LangGraph. La elección se justifica por tres necesidades concretas: pausar los casos de alto impacto hasta que una persona apruebe (pueden pasar horas), reanudar sin repetir pasos si el servicio se reinicia, y tener un ciclo de redacción-validación con tope. Los casos de bajo impacto salen automáticamente; los de alto impacto llegan a la persona con la evidencia y la clasificación ya armadas, lo que reduce el tiempo de atención aunque la decisión siga siendo humana.

### LangChain para un único prompt y no se puede depurar

**Situación:** un equipo implementó la clasificación de tickets con una cadena de LangChain: plantilla, modelo, parser. Un día la exactitud cae y nadie logra ver qué prompt exacto se está enviando, porque el parser inyecta instrucciones de formato y la plantilla combina varios mensajes.

**Qué se hace:** se reemplaza la cadena por una llamada directa al SDK del proveedor con el prompt escrito completo en el código y salida estructurada nativa. Son pocas líneas, el prompt queda versionado y legible, y se agregan trazas propias. La lección: para un solo prompt, la abstracción costaba más de lo que ahorraba.

### Una actualización menor del framework rompe producción

**Situación:** una actualización automática de dependencias sube una versión menor del framework. El cambio modifica cómo se serializan los mensajes de herramientas y el flujo de reclamos empieza a fallar en el nodo de validación para una fracción de casos.

**Qué se hace:**

- **Fijar versiones exactas** (lockfile) del framework y sus integraciones; nada de rangos abiertos.
- **Evals en CI:** cada cambio de dependencias corre el golden set de reclamos y bloquea el merge si caen las métricas o aumentan los errores de validación.
- **Actualizaciones deliberadas:** se actualiza en una rama propia, leyendo el changelog, y se despliega con canary.
- **Rollback rápido:** la imagen anterior queda disponible para volver en minutos.

## Errores comunes

- **Adoptar un framework "por si acaso".** Si el caso es un prompt y una salida, el SDK del proveedor alcanza y se depura mucho mejor.
- **No mirar el prompt final.** Con frameworks, siempre hay que poder ver en una traza exactamente qué texto recibió el modelo; si no se puede, falta observabilidad.
- **Dejar decisiones de riesgo al LLM dentro del grafo.** Las aristas condicionales de alto impacto (escalar, aprobar, enviar) conviene basarlas en reglas de código o en aprobación humana.
- **Ciclos sin tope.** Un ciclo "redactar, validar, redactar" sin contador puede quedar en bucle y gastar tokens indefinidamente.
- **Usar el checkpointer en memoria en producción.** Si el proceso se reinicia, se pierde el estado de los casos pausados; en producción va una base persistente.
- **Actualizar dependencias sin evals.** Los cambios de comportamiento en estos frameworks no siempre rompen tests unitarios; hacen falta evaluaciones sobre casos reales.

## Para discutir en equipo

- ¿Cuáles de nuestros usos actuales de LangChain podrían reemplazarse por llamadas directas al SDK, y qué ganaríamos en legibilidad?
- En el grafo de reclamos, ¿qué criterios de "impacto alto" deberían ser reglas fijas y cuáles podrían ajustarse con datos?
- ¿Dónde deberían vivir las trazas de nuestros flujos con LLM, considerando que pueden contener datos personales?
- ¿Qué política de actualización de dependencias de frameworks de LLM queremos (frecuencia, quién revisa, qué evals bloquean)?
