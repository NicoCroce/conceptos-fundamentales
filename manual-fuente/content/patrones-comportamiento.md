---
slug: patrones-comportamiento
titulo: Patrones de comportamiento: Strategy, Observer, Command y State
resumen: Patrones que ordenan cómo se reparten las decisiones y las responsabilidades entre objetos, desde elegir un modelo por consulta hasta aprobar las acciones de un agente.
lectura: 14
---

## La idea central

Los patrones de comportamiento responden una pregunta concreta: **quién decide qué, y cómo se entera el resto**. Los creacionales tratan de cómo nacen los objetos y los estructurales de cómo se combinan; estos se ocupan del flujo de decisiones y avisos en tiempo de ejecución. Elegir un algoritmo entre varios, avisar a otros que algo pasó, convertir una acción en un objeto que se puede guardar, revisar o deshacer, y cambiar de comportamiento según el estado en que se está.

Conviene leerlos como vocabulario más que como recetas. Cuando alguien en una revisión de diseño dice "esto es un Strategy" o "ese `switch` de estados pide una máquina de estados", está comprimiendo una discusión de diez minutos en una palabra. Y tienen una relevancia nueva con agentes: una llamada a herramienta de un LLM es, literalmente, un **Command** que conviene validar antes de ejecutar; el bucle de un agente es una **máquina de estados**; elegir qué modelo atiende cada consulta es un **Strategy**. Al mismo tiempo, cada patrón agrega indirección: el criterio importante es saber cuándo un `if` es mejor.

## Conceptos

### Strategy: elegir el algoritmo en tiempo de ejecución

Strategy separa **qué** se quiere lograr de **cómo** se logra. Paso a paso:

1. Se identifica una operación con varias formas de hacerse (calcular una ruta, elegir un modelo, estimar un costo).
2. Se define una interfaz común para esa operación.
3. Cada forma concreta es una implementación de esa interfaz.
4. El código que la usa (el *contexto*) recibe una estrategia y la invoca sin saber cuál es.

Así se agrega una variante nueva sin tocar el código que la usa, y cada variante se prueba por separado. Es el principio abierto/cerrado de [SOLID](#t/principios-solid) aplicado a un algoritmo.

```go
type Ruteador interface {
    Ruta(paradas []Parada) ([]Parada, error)
}

type VecinoMasCercano struct{}        // rápido, calidad aceptable
type OptimizadorExterno struct{ c *Cliente } // lento, mejor calidad

func PlanificarReparto(r Ruteador, paradas []Parada) ([]Parada, error) {
    return r.Ruta(paradas)
}
```

**Ejemplo:** el servicio de planificación de Rumbo usa el heurístico de vecino más cercano para repartos de hasta 15 paradas (resuelve en 2 ms) y un optimizador externo para repartos de 40 paradas (tarda 800 ms, pero ahorra en promedio un 12 % de kilómetros, cifra hipotética). La decisión de cuál usar vive en un solo lugar; `PlanificarReparto` no cambia.

**Por qué importa:** sin Strategy, la elección se reparte en `if` por todo el código, y agregar una tercera variante obliga a encontrar todos esos `if`.

### Strategy con funciones y el ruteo de modelos

En lenguajes con funciones de primera clase (todos los de nuestro stack), una estrategia no necesita ser una clase: **una función es una estrategia**. Si la interfaz tiene un solo método, pasar una función es más simple y dice lo mismo.

```python
from typing import Callable

ElegirModelo = Callable[[Consulta], str]

def por_longitud(c: Consulta) -> str:
    return "modelo-chico" if c.tokens < 2_000 else "modelo-grande"

def por_tipo(c: Consulta) -> str:
    return "modelo-grande" if c.tipo == "reclamo" else "modelo-chico"

def responder(c: Consulta, elegir: ElegirModelo) -> Respuesta:
    return llamar_llm(elegir(c), c)
```

El caso más visible en nuestro trabajo es el **ruteo de modelos** (ver [Varios modelos y ruteo](#t/multimodelo)): el asistente de soporte decide por consulta qué LLM la atiende. La política de ruteo es un Strategy, y tenerla aislada permite compararlas con datos.

**Ejemplo:** el asistente recibe 100.000 consultas por día. Con la política `por_longitud`, el 80 % va al modelo chico (costo hipotético de 0,2 unidades por consulta) y el 20 % al grande (2 unidades): 56.000 unidades diarias. Con `por_tipo`, el 65 % va al chico: 83.000 unidades. Como ambas políticas son funciones intercambiables, se pueden correr las dos sobre el mismo golden set y comparar costo contra calidad antes de elegir.

**Por qué importa:** la política de ruteo cambia seguido (llega un modelo nuevo, cambian los precios). Si está aislada, cambiarla es un PR de diez líneas con su evaluación; si está mezclada con el resto, es una refactorización.

### Observer y pub/sub: avisar sin conocer al que escucha

Observer resuelve esto: cuando algo cambia en un objeto, otros quieren enterarse, pero el objeto no debería conocerlos. El funcionamiento:

1. El **sujeto** mantiene una lista de **observadores** suscritos.
2. Los observadores se registran (y se dan de baja) a través de una interfaz común.
3. Cuando ocurre algo, el sujeto recorre la lista y notifica a cada uno.

El sujeto no sabe si del otro lado hay un notificador de SMS, una métrica o un log. Agregar un observador nuevo no toca al sujeto.

**Pub/sub** (publicación y suscripción) es la versión desacoplada: entre el publicador y los suscriptores hay un intermediario, el canal o broker, y ninguno de los dos conoce al otro. Puede vivir en memoria (un bus de eventos dentro del proceso) o en un broker como Kafka (ver [Event streaming](#t/event-streaming)). La diferencia es grande:

| Aspecto | Observer en proceso | Pub/sub con broker |
|---|---|---|
| Entrega | Llamada directa, sincrónica o en el mismo proceso | Por red, asincrónica |
| Si el proceso se cae | Los avisos pendientes se pierden | El evento queda guardado en el broker |
| Errores de un observador | Pueden romper al sujeto si no se aíslan | Quedan del lado del consumidor |
| Orden y reintentos | Simples, implícitos | Hay que diseñarlos (particiones, idempotencia) |
| Cuándo | Avisos internos de un servicio | Integración entre servicios o equipos |

**Ejemplo:** cuando un envío pasa a `entregado`, dentro del servicio de seguimiento tres observadores en memoria actualizan una caché, incrementan una métrica y escriben un log. Además se publica `envio_entregado` en Kafka, que consumen el servicio de notificaciones y el pronóstico de demanda. Si notificaciones está caído 10 minutos, procesa los eventos acumulados al volver; si un observador en memoria lanza una excepción no controlada, puede cortar la transición del envío.

**Por qué importa:** confundir los dos niveles es un clásico. Un aviso que no puede perderse (avisar al destinatario) no debería depender de un observador en memoria.

### Command: la acción como objeto

Command convierte una petición en un **objeto** con todo lo necesario para ejecutarla: qué operación, sobre qué, con qué parámetros. Al ser un dato y no una llamada inmediata, se puede:

- **Encolar** y ejecutar después o en otro proceso.
- **Registrar** para auditoría.
- **Validar o aprobar** antes de ejecutar.
- **Deshacer**, si el comando sabe cómo revertirse.
- **Reintentar**, si es idempotente.

```kotlin
sealed interface ComandoEnvio {
    val envioId: String
    data class Reprogramar(override val envioId: String, val nuevaFranja: Franja) : ComandoEnvio
    data class Reasignar(override val envioId: String, val transportistaId: String, val motivo: String) : ComandoEnvio
    data class Cancelar(override val envioId: String, val motivo: String) : ComandoEnvio
}

fun ejecutar(cmd: ComandoEnvio, envios: RepositorioEnvios) = when (cmd) {
    is ComandoEnvio.Reprogramar -> envios.obtener(cmd.envioId).reprogramar(cmd.nuevaFranja)
    is ComandoEnvio.Reasignar   -> envios.obtener(cmd.envioId).reasignar(cmd.transportistaId, cmd.motivo)
    is ComandoEnvio.Cancelar    -> envios.obtener(cmd.envioId).cancelar(cmd.motivo)
}
```

La conexión con agentes es directa. Cuando un LLM decide usar una herramienta, no ejecuta nada: devuelve un objeto con el nombre de la herramienta y sus argumentos (ver [Agentes y tool calling](#t/agentes)). Eso **es** un comando. Tratarlo como tal permite un pipeline claro: parsear el pedido del modelo a un comando tipado, validar los argumentos, chequear permisos, pedir aprobación humana si la acción es riesgosa, registrar, ejecutar.

**Ejemplo:** el agente de operaciones propone `Reasignar(envio=E-881, transportista=T-12, motivo="moto averiada")`. El comando se valida (el envío existe, T-12 está activo en la zona), se registra con el ID de la conversación y, como reasignar está en la lista de acciones con aprobación, queda en una cola hasta que una persona de operaciones lo confirma. Si en el día hubo 300 comandos propuestos, el registro permite ver cuántos se aprobaron, cuántos se rechazaron y por qué.

**Por qué importa:** si la herramienta ejecuta directamente lo que el modelo pidió, no hay lugar donde poner controles. El comando crea ese lugar, que es la base de las defensas de [Seguridad de LLMs y agentes](#t/seguridad-agentes).

### State: el comportamiento depende del estado

State se usa cuando un objeto se comporta distinto según el estado en que está, y las transiciones entre estados tienen reglas. La alternativa ingenua es un campo `estado` y `if` en cada método; con cinco estados y seis operaciones eso son 30 combinaciones dispersas. La versión ordenada es una **máquina de estados** explícita:

1. Se enumeran los estados posibles.
2. Se enumeran los eventos u operaciones.
3. Se define una tabla de transiciones permitidas: desde qué estado, con qué evento, a qué estado.
4. Todo lo que no está en la tabla es un error.

```typescript
type Estado = "pendiente" | "asignado" | "en_reparto" | "entregado" | "fallido";
type Evento = "asignar" | "retirar" | "entregar" | "fallar" | "reintentar";

const transiciones: Record<Estado, Partial<Record<Evento, Estado>>> = {
  pendiente:  { asignar: "asignado" },
  asignado:   { retirar: "en_reparto", asignar: "asignado" },
  en_reparto: { entregar: "entregado", fallar: "fallido" },
  fallido:    { reintentar: "pendiente" },
  entregado:  {},
};

function aplicar(actual: Estado, ev: Evento): Estado {
  const siguiente = transiciones[actual][ev];
  if (!siguiente) throw new Error(`transición inválida: ${actual} + ${ev}`);
  return siguiente;
}
```

El patrón State clásico va más lejos: cada estado es una clase con su propio comportamiento, y el objeto delega en su estado actual. Con lógica simple por estado, la tabla alcanza; cuando cada estado tiene mucha lógica propia, las clases ayudan.

**Ejemplo:** la tabla anterior tiene 7 transiciones válidas de 25 combinaciones posibles (5 estados por 5 eventos). Las otras 18 fallan explícitamente. Un evento `entregar` que llega duplicado sobre un envío ya `entregado` se rechaza en vez de disparar una segunda notificación.

El **bucle de un agente** también es una máquina de estados: `esperando_modelo`, `ejecutando_herramienta`, `esperando_aprobacion`, `respondiendo`, `terminado`, `error`. Frameworks como [LangGraph](#t/langgraph) hacen explícito ese grafo. Escribirlo así deja ver preguntas que un bucle `while` esconde: ¿qué pasa si llega un mensaje del usuario mientras se espera aprobación? ¿Cuántas veces se puede volver de `ejecutando_herramienta` a `esperando_modelo` antes de cortar?

**Por qué importa:** los estados implícitos generan bugs que solo aparecen con eventos fuera de orden, que en sistemas distribuidos son la norma.

### Chain of Responsibility y pipelines de middleware

Chain of Responsibility encadena manejadores: cada uno recibe la petición, hace su parte y decide si la pasa al siguiente o la corta. Su forma más común hoy es el **middleware** de un servidor HTTP: autenticación, límite de tasa, logging, y recién después el handler.

```go
type Middleware func(http.Handler) http.Handler

func Encadenar(h http.Handler, mws ...Middleware) http.Handler {
    for i := len(mws) - 1; i >= 0; i-- {
        h = mws[i](h)
    }
    return h
}

// orden de ejecución: autenticar -> limitarTasa -> registrar -> handler
srv := Encadenar(handler, autenticar, limitarTasa, registrar)
```

**Ejemplo:** el gateway del asistente procesa cada consulta con una cadena de cinco pasos: autenticar al comercio, aplicar límite de 60 consultas por minuto, detectar y enmascarar PII, buscar en caché semántica y, si no hubo acierto, llamar al modelo. Si la caché responde en el paso 4, la cadena se corta y el 30 % de las consultas (hipotético) nunca llega al LLM. Los mismos pasos se aplican a la salida del modelo: filtros de contenido y validación de formato.

**Por qué importa:** el orden es parte del diseño. Registrar antes de enmascarar PII deja datos personales en los logs; limitar la tasa después de llamar al modelo no ahorra nada.

### Template Method: el esqueleto fijo con pasos variables

Template Method define el algoritmo general en una clase base y deja que las subclases completen pasos concretos. El orden no cambia; el contenido de cada paso sí. Se ve en frameworks: el framework llama a tus métodos (`setUp`, `handle`, `tearDown`) en un orden que él controla.

**Ejemplo:** los evaluadores del asistente siguen siempre el mismo esqueleto: cargar casos del golden set, ejecutar el sistema, puntuar cada respuesta y agregar resultados. Lo único que cambia entre el evaluador de clasificación y el de resúmenes es el paso de puntuar. La clase base fija el orden y garantiza que todos guarden los resultados con el mismo formato.

**Por qué importa:** es útil cuando el orden es una regla que no se quiere romper. Pero la herencia acopla; muchas veces el mismo efecto se logra pasando el paso variable como función, que es Strategy otra vez.

### Cuándo un if o un switch es mejor

Cada patrón agrega una interfaz, un archivo y un salto más para quien lee el código. Ese costo vale solo si compra algo. Señales para quedarse con un condicional:

- Hay dos o tres variantes y no se espera que crezcan.
- Las variantes son cortas y caben en la pantalla.
- Toda la lógica cambia junta, en el mismo PR, por el mismo equipo.
- Un `switch` exhaustivo sobre un tipo cerrado (un `sealed interface` en Kotlin, una unión en TypeScript) ya da lo que se busca: el compilador avisa si falta un caso.

**Ejemplo:** el formateo de una ETA tiene dos variantes ("llega en 15 min" y "llega entre 14 y 16 h"). Un `if` de cuatro líneas es más claro que una interfaz `FormateadorEta` con dos implementaciones y una fábrica. En cambio, la política de ruteo de modelos cambia cada mes, se evalúa por separado y la toca otro equipo: ahí la estrategia aislada se paga sola.

**Por qué importa:** los agentes de código tienden a aplicar patrones de más porque los vieron mucho en su entrenamiento. En revisión, la pregunta útil es "¿qué cambio futuro hace más fácil esta indirección, y es probable?".

## Casos prácticos

### Las herramientas del agente ejecutaban sin control

**Situación:** el agente de operaciones tenía una herramienta `reasignar_envio` que llamaba directo al servicio de asignación con los argumentos que el modelo generaba. Una consulta ambigua terminó con 14 envíos reasignados a un transportista de otra zona, y no había registro de qué conversación lo pidió.

**Qué se hace:** se reemplaza la ejecución directa por comandos. Cada llamada a herramienta se parsea a un `ComandoEnvio` tipado, pasa por validación (zona del transportista, estado del envío), se registra con el ID de conversación y, si modifica datos, entra a una cola de aprobación. Se agrega un límite de 3 comandos de escritura por conversación. El modelo sigue proponiendo; los controles quedan en código determinístico.

### El switch de estados de envío con 200 líneas

**Situación:** el método `actualizarEstado` tenía un `switch` anidado con reglas por estado, y aparecían envíos que pasaban de `entregado` a `en_reparto` cuando llegaban eventos duplicados del dispositivo del transportista.

**Qué se hace:** se extrae una tabla de transiciones explícita como la del ejemplo, con un test que recorre las 25 combinaciones y verifica cuáles son válidas. Las transiciones inválidas se rechazan y se cuentan en una métrica. En la primera semana la métrica muestra unas 400 transiciones inválidas por día, casi todas eventos duplicados, que antes corrompían el estado en silencio.

### Comparar políticas de ruteo de modelos

**Situación:** el equipo quiere bajar el costo del asistente y hay tres propuestas de ruteo: por longitud, por tipo de consulta y con un clasificador chico que predice dificultad.

**Qué se hace:** cada política se implementa como una función `Consulta -> modelo`, y el harness de evaluación las recibe como parámetro. Se corren las tres sobre 1.500 casos del golden set y se comparan costo, calidad y latencia en una tabla. La ganadora se activa por configuración, y el código del asistente no cambia.

### Un observador en memoria que se tragaba avisos

**Situación:** el aviso "su envío está cerca" al destinatario se disparaba desde un observador en memoria del servicio de seguimiento. En cada deploy, los avisos de los pods que se reiniciaban se perdían: unos 2.000 por deploy, con dos deploys por día.

**Qué se hace:** el aviso pasa a ser un evento publicado en Kafka y lo consume el servicio de notificaciones, idempotente por ID de envío y tipo de aviso. Los observadores en memoria quedan para lo que puede perderse sin daño: caché y métricas.

## Errores comunes

- **Patrones por reflejo.** Una interfaz con una sola implementación y sin un segundo caso previsible es ruido; empezar con una función o un `if` y extraer el patrón cuando aparece la segunda variante.
- **Ejecutar la salida del modelo sin pasar por un comando.** Las llamadas a herramientas son datos; convertirlas en comandos tipados que se validan, registran y aprueban antes de ejecutar.
- **Observadores en memoria para avisos que importan.** Si el aviso no puede perderse, va por un broker con reintentos e idempotencia, no por una lista de callbacks en un pod.
- **Estados implícitos.** Un campo `estado` modificado desde muchos lugares sin tabla de transiciones produce estados imposibles; centralizar las transiciones y rechazar las inválidas.
- **Ignorar el orden del middleware.** Registrar antes de enmascarar, o cachear antes de autenticar, son bugs de seguridad; documentar y probar el orden de la cadena.
- **Herencia profunda para Template Method.** Tres niveles de clases base para variar un paso; pasar ese paso como función suele bastar.

## Para discutir en equipo

- ¿Qué herramientas de nuestros agentes ejecutan hoy sin pasar por un comando validado y registrado? ¿Cuáles deberían pedir aprobación?
- ¿Dónde tenemos máquinas de estados implícitas (envíos, retiros, el bucle del agente) que convendría escribir como tabla?
- ¿Qué avisos viajan hoy por observadores en memoria y qué pasaría si se perdieran durante un deploy?
- ¿Qué patrón vimos en un PR reciente que agregó indirección sin un segundo caso que lo justifique?
