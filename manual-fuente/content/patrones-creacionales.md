---
slug: patrones-creacionales
titulo: Patrones creacionales: Factory, Builder y Singleton
resumen: Cómo y dónde crear objetos con Factory, Builder y Singleton, cuándo conviene cada uno y por qué el Singleton suele ser un antipatrón.
lectura: 12
---

## La idea central

Crear un objeto parece trivial: `new ClienteLLM(...)`. El problema aparece cuando esa línea se repite en veinte lugares y cada uno necesita saber qué proveedor usar, qué modelo, qué clave, qué timeout, qué región y qué cabeceras. Si mañana cambia cualquiera de esos detalles, hay que tocar los veinte. Los **patrones creacionales** separan el **qué se usa** del **cómo se construye**: el código que necesita un cliente de LLM pide "un cliente para clasificar tickets" y otro lugar decide que eso significa un modelo chico de cierto proveedor con un timeout de 8 segundos.

Los patrones de este tema vienen del catálogo clásico del libro *Design Patterns* (el "Gang of Four", 1994): Factory Method, Abstract Factory, Builder y Singleton, más algunas variantes modernas que en lenguajes como Go, Kotlin, TypeScript o Python reemplazan a las versiones originales con menos ceremonia. Una analogía: en un restaurante, el cliente pide "un plato del día", no compra los ingredientes ni enciende el horno. La cocina es la fábrica. Para nosotros el caso más importante es la creación de clientes de LLM y de herramientas de agentes, donde la configuración cambia seguido y equivocarse en un parámetro (el modelo grande en lugar del chico) se nota directamente en la factura y en la latencia.

## Conceptos

### Función fábrica o simple factory

La forma más simple, y la que más se usa en la práctica, es una **función que recibe parámetros y devuelve un objeto ya configurado**. No es un patrón del catálogo original, pero resuelve el 80 % de los casos. El código cliente llama a la función y recibe una interfaz; no sabe qué tipo concreto se construyó.

```typescript
interface ClienteLLM {
  completar(prompt: string, opciones?: OpcionesCompletado): Promise<Respuesta>;
}

function crearClienteLLM(cfg: ConfigModelo): ClienteLLM {
  switch (cfg.proveedor) {
    case "proveedor-a": return new ClienteProveedorA(cfg.modelo, cfg.claveRef, cfg.timeoutMs);
    case "proveedor-b": return new ClienteProveedorB(cfg.modelo, cfg.region, cfg.timeoutMs);
    case "local":       return new ClienteLocal(cfg.urlServidor, cfg.modelo);
    default: throw new Error(`proveedor desconocido: ${cfg.proveedor}`);
  }
}
```

Paso a paso: la configuración viene de un archivo o de variables de entorno, la fábrica la lee, elige la clase concreta y la devuelve tipada como `ClienteLLM`. El clasificador de tickets, el resumidor de casos y el agente de operaciones reciben un `ClienteLLM` y nunca importan los SDKs de los proveedores.

**Ejemplo:** el asistente de soporte usa tres modelos: uno chico para clasificar tickets (costo hipotético de 0,2 unidades por millón de tokens), uno mediano para responder y uno grande para resumir casos largos. Con una fábrica y un archivo de configuración, pasar el clasificador a un modelo local on-prem para un cliente grande es cambiar una línea de YAML, no un deploy de código.

**Por qué importa:** concentra en un solo lugar la decisión de qué proveedor y qué modelo se usa, que es exactamente la decisión que más cambia en sistemas con LLMs (ver [Varios modelos y ruteo](#t/multimodelo)).

### Factory Method

El **Factory Method** original define un método abstracto de creación en una clase base y deja que cada subclase decida qué objeto concreto crea. El resto del algoritmo, en la clase base, usa lo creado sin conocer su tipo.

```kotlin
abstract class ProcesadorNovedades {
    protected abstract fun crearParser(): ParserNovedad   // el factory method

    fun procesar(archivo: ByteArray): List<Novedad> {
        val parser = crearParser()
        return parser.parsear(archivo).filter { it.esValida() }.map { normalizar(it) }
    }
}

class ProcesadorTransportistaNorte : ProcesadorNovedades() {
    override fun crearParser() = ParserCsvNorte()
}
class ProcesadorTransportistaSur : ProcesadorNovedades() {
    override fun crearParser() = ParserXmlSur()
}
```

Cada transportista externo manda su archivo de novedades (entregado, ausente, dirección incorrecta) en un formato distinto. El flujo de validar y normalizar es el mismo; solo cambia el parser.

**Ejemplo:** sumar un transportista nuevo con formato JSON es crear `ProcesadorTransportistaEste` con un método de una línea. Las 120 líneas de validación y normalización no se tocan.

**Por qué importa:** es útil cuando hay un algoritmo fijo con un paso de creación que varía. Pero usa herencia, y en código moderno suele reemplazarse por pasar el parser como parámetro (composición): `ProcesadorNovedades(parser = ParserCsvNorte())`. Si se reconoce el patrón en código existente, conviene saber leerlo; para código nuevo, la composición suele ser más simple.

### Abstract Factory

La **Abstract Factory** crea **familias de objetos relacionados** que deben usarse juntos. En lugar de una fábrica por tipo, hay una interfaz de fábrica con varios métodos de creación, y cada implementación produce una familia coherente.

```go
type FabricaIA interface {
    Chat() ClienteChat
    Embeddings() ClienteEmbeddings
    Moderacion() ClienteModeracion
}

type fabricaNube struct{ cfg ConfigNube }      // todo de un proveedor cloud
type fabricaOnPrem struct{ cfg ConfigOnPrem }  // todo local, para clientes que lo exigen
```

El punto clave es la coherencia: si el chat corre on-prem pero los embeddings van a la nube, los datos del cliente salen de su infraestructura. La Abstract Factory garantiza que la instalación on-prem reciba los tres clientes locales juntos.

**Ejemplo:** un comercio grande exige instalación on-prem (ver [Despliegue híbrido y on-prem](#t/hibrido-on-prem)). Al arrancar, `main.go` lee `MODO=onprem`, crea `fabricaOnPrem` y se la pasa a los servicios. Ninguna parte del sistema puede obtener por error un cliente de embeddings de la nube, porque la única fábrica disponible no los produce.

**Por qué importa:** cuando las piezas tienen que ser compatibles entre sí (mismo proveedor, misma región, misma dimensión de embeddings), crearlas por separado invita a mezclas inválidas. La fábrica abstracta hace que la combinación incorrecta no se pueda expresar.

### Builder

El **Builder** construye un objeto complejo paso a paso, separando la construcción de la representación final. Se usa cuando un objeto tiene muchos parámetros, varios opcionales, y algunas combinaciones son inválidas. Sin builder aparece el **constructor telescópico**: `new Solicitud(prompt, null, null, 0.2, 1024, null, true)`, donde nadie recuerda qué es el quinto argumento.

```typescript
const solicitud = new SolicitudLLMBuilder()
  .sistema(promptSoporte)
  .mensajeUsuario(texto)
  .herramientas([consultarEnvio, consultarRetiro])
  .temperatura(0.2)
  .maxTokens(800)
  .build();   // valida: si hay herramientas, el modelo debe soportarlas
```

Paso a paso: cada método guarda un valor y devuelve el mismo builder; `build()` verifica las reglas (temperatura entre 0 y 1, al menos un mensaje, herramientas solo si el modelo las admite) y devuelve un objeto **inmutable**. Si algo está mal, falla en `build()` con un mensaje claro, no en el proveedor con un error 400 genérico.

**Ejemplo:** el equipo encontró que el 4 % de las llamadas al proveedor fallaban con error de validación porque algunos servicios mandaban `maxTokens` mayor al límite del modelo. Con un builder que conoce los límites de cada modelo, esos errores pasaron a detectarse en los tests unitarios.

**Por qué importa:** el builder vale cuando hay validación entre campos o construcción en varios pasos. Si solo se trata de muchos parámetros opcionales, el lenguaje probablemente ya ofrece algo mejor.

### Alternativas al Builder: parámetros con nombre y opciones

En Kotlin y Python, los **parámetros con nombre y valores por defecto** resuelven el constructor telescópico sin clase extra:

```kotlin
data class SolicitudLLM(
    val mensajes: List<Mensaje>,
    val temperatura: Double = 0.2,
    val maxTokens: Int = 800,
    val herramientas: List<Herramienta> = emptyList(),
) { init { require(temperatura in 0.0..1.0) } }

val s = SolicitudLLM(mensajes = listOf(m), maxTokens = 400)
```

En TypeScript, un **objeto de opciones** cumple el mismo rol. En Go, sin parámetros con nombre, el idioma habitual son las **opciones funcionales**:

```go
cliente := NuevoClienteLLM("modelo-chico",
    ConTimeout(8*time.Second),
    ConReintentos(3),
    ConCabecera("x-equipo", "soporte"))
```

**Ejemplo:** el servicio de asignación tenía un builder Java de 90 líneas heredado. Al migrarlo a Kotlin, se reemplazó por una `data class` de 12 líneas con valores por defecto y un bloque `init` con las validaciones. El comportamiento quedó igual.

**Por qué importa:** muchos patrones del catálogo de 1994 compensaban limitaciones de los lenguajes de la época. Antes de escribir un builder, conviene preguntar si el lenguaje ya lo resuelve.

### Singleton y por qué suele ser un antipatrón

El **Singleton** garantiza que una clase tenga una única instancia y ofrece un punto de acceso global a ella: `ClienteLLM.getInstance()`. Suena razonable para cosas que deberían existir una sola vez, como un pool de conexiones o un cliente HTTP. En la práctica trae tres problemas:

1. **Estado global encubierto.** Cualquier función puede llamar a `getInstance()` sin declararlo. Leyendo la firma de `clasificarTicket(texto)` no se sabe que depende de un cliente de LLM, una clave y la red.
2. **Tests acoplados.** Si un test cambia la configuración del singleton (por ejemplo, para simular un timeout), los tests siguientes heredan ese estado. Las suites empiezan a fallar según el orden en que corren, y paralelizarlas se vuelve imposible.
3. **Imposible tener dos.** El día que se necesitan dos clientes distintos (modelo chico para clasificar, grande para resumir), el singleton obliga a reescribir todos los llamadores.

**Ejemplo:** una suite de 400 tests del asistente tardaba 6 minutos porque no se podía paralelizar: un singleton de configuración se modificaba en varios tests. Al pasar la configuración por constructor, los tests corren en paralelo en 8 procesos y la suite baja a menos de un minuto.

**Por qué importa:** la necesidad real casi nunca es "que haya una sola instancia en el universo" sino "no crear una instancia nueva en cada petición". Son cosas distintas, y la segunda se resuelve sin estado global.

### Qué usar en lugar del Singleton

La alternativa es **crear una instancia en la raíz de composición y pasarla**. La **raíz de composición** es el único lugar (normalmente `main` o el arranque de la aplicación) donde se construyen los objetos de larga vida y se conectan entre sí. Allí se crea un cliente de LLM, uno de base de datos y un pool HTTP, y se inyectan por constructor a quien los necesite (ver [Inyección de dependencias](#t/inyeccion-dependencias)).

```python
def main():
    cfg = cargar_config()
    http = crear_pool_http(max_conexiones=50)
    llm_chico = crear_cliente_llm(cfg.modelos["clasificacion"], http)
    llm_grande = crear_cliente_llm(cfg.modelos["resumen"], http)
    clasificador = ClasificadorTickets(llm_chico)
    resumidor = ResumidorCasos(llm_grande)
    servir(clasificador, resumidor)
```

Sigue habiendo una sola instancia de cada cosa en producción, pero es una decisión del arranque, no una propiedad de la clase. En los tests, se construye otra con dobles.

**Ejemplo:** el pool HTTP de 50 conexiones se comparte entre los dos clientes de LLM. Nadie lo crea dos veces porque solo `main` crea cosas, no porque una clase lo prohíba.

**Por qué importa:** la dependencia queda visible en la firma de cada constructor. Un revisor (humano o agente) entiende qué toca cada componente sin buscar llamadas a `getInstance()`.

### Object pool, brevemente

Un **object pool** mantiene un conjunto de objetos caros de crear ya inicializados, los presta y los recibe de vuelta. Los pools de conexiones a la base de datos y de conexiones HTTP son el ejemplo universal: abrir una conexión TLS a Aurora puede costar decenas de milisegundos, y reutilizarla cuesta casi nada.

**Ejemplo:** el servicio de asignación, con un presupuesto de 50 ms, no puede abrir una conexión por petición. Usa un pool de 20 conexiones; si llegan 25 peticiones simultáneas, 5 esperan. El tamaño del pool se dimensiona con la latencia de las consultas y el tráfico esperado.

**Por qué importa:** casi nunca hace falta escribir un pool propio: los drivers y clientes HTTP ya lo traen. Lo que sí hay que entender es su configuración (tamaño, tiempo máximo de espera, tiempo de vida), porque un pool mal dimensionado aparece como latencia misteriosa bajo carga.

### Cuál elegir

| Necesidad | Patrón |
|---|---|
| Elegir la implementación según configuración | Función fábrica |
| Un algoritmo fijo con un paso de creación que varía | Factory Method, o pasar la dependencia |
| Varias piezas que deben ser compatibles entre sí | Abstract Factory |
| Muchos parámetros con validación entre ellos | Builder |
| Muchos parámetros opcionales sin reglas cruzadas | Parámetros con nombre u opciones funcionales |
| Una sola instancia compartida | Crearla en la raíz de composición e inyectarla |
| Objetos caros de crear y reutilizables | Pool (normalmente, el que trae la librería) |

## Casos prácticos

### Cambiar el modelo del clasificador sin tocar código

**Situación:** el clasificador de tickets instancia el SDK del proveedor en siete lugares distintos, cada uno con el nombre del modelo escrito a mano. El equipo quiere probar un modelo más barato y descubre que dos de los siete usaban un modelo viejo que el proveedor va a retirar en 60 días.

**Qué se hace:** se crea `crearClienteLLM(cfg)` y un archivo de configuración con un nombre lógico por uso (`clasificacion`, `respuesta`, `resumen`). Los siete lugares reciben el cliente ya construido. El cambio de modelo pasa a ser configuración, y se agrega un test que falla si algún archivo fuera de `adaptadores/` importa el SDK del proveedor.

### Instalación on-prem que filtraba datos a la nube

**Situación:** en la instalación on-prem de un comercio grande, el chat corría con un modelo local, pero una auditoría encontró que la búsqueda semántica seguía llamando a un servicio de [embeddings](#t/embeddings) en la nube, porque ese cliente se creaba en otro módulo con la configuración por defecto.

**Qué se hace:** se introduce una Abstract Factory `FabricaIA` con implementaciones `nube` y `onprem`, elegida una sola vez al arrancar. Todos los clientes de IA se obtienen de ella. La configuración por defecto desaparece: si no hay modo declarado, la aplicación no arranca.

### Tests que fallaban según el orden

**Situación:** la suite del agente de operaciones falla de forma intermitente en CI. La causa: `ConfigAgente.instancia()` es un singleton, y un test que simula "proveedor caído" le cambia la URL y no la restaura. Los tests que corren después usan la URL rota.

**Qué se hace:** se elimina el singleton. La configuración se construye en `main` y se pasa por constructor. Cada test arma su propia configuración. La suite deja de ser intermitente y se puede paralelizar. Como regla del repositorio: no se aceptan métodos `instancia()` o `getInstance()` nuevos.

### Herramientas del agente construidas por sesión

**Situación:** las herramientas del agente de soporte se crean una vez al arrancar el servidor y se comparten entre todas las conversaciones. Para saber en nombre de quién actúan, leen el usuario de una variable global que se actualiza en cada petición. Bajo carga, dos conversaciones simultáneas se mezclan y una herramienta consulta envíos de otro comercio.

**Qué se hace:** se crea una fábrica de herramientas por sesión: `crearHerramientas(sesion)` recibe la identidad del usuario y devuelve herramientas que la llevan adentro. Lo caro (clientes HTTP, pools) se sigue creando una vez en la raíz de composición y se comparte; lo que depende del usuario se crea por sesión. Es un problema de [seguridad de agentes](#t/seguridad-agentes) causado por un error de creación de objetos.

## Errores comunes

- **Crear clientes de proveedores dentro de la lógica de negocio.** Cada `new ClienteProveedor(...)` disperso es un lugar más a cambiar; centralizar en una fábrica y recibir una interfaz.
- **Usar Singleton para "compartir una instancia".** Compartir se logra creando una vez en la raíz de composición; el singleton agrega estado global y tests frágiles.
- **Builders en lenguajes que no los necesitan.** En Kotlin o Python, parámetros con nombre y valores por defecto cubren casi todos los casos con menos código.
- **Fábricas que devuelven tipos concretos.** Si la fábrica devuelve `ClienteProveedorA` en lugar de `ClienteLLM`, el llamador vuelve a acoplarse al proveedor.
- **Mezclar en el mismo objeto lo que vive toda la aplicación y lo que vive una petición.** La identidad del usuario no puede estar en un objeto compartido; separar fábricas por tiempo de vida.
- **Fábricas con valores por defecto peligrosos.** Un modelo grande o un modo nube por defecto se activa justo cuando alguien se olvida de configurar; mejor fallar al arrancar.

## Para discutir en equipo

- ¿Cuántos lugares de nuestro código instancian directamente un SDK de proveedor de LLM, y cuánto costaría cambiar de modelo hoy?
- ¿Qué singletons o variables globales tenemos, y cuáles explican tests intermitentes?
- ¿Qué objetos de nuestros agentes viven toda la aplicación y cuáles deberían vivir una sesión?
- ¿Dónde tendría sentido una Abstract Factory para garantizar que la instalación on-prem no use servicios de la nube?
- ¿Qué reglas de creación de objetos deberíamos dejar escritas para que un agente de código no las rompa?
