---
slug: inyeccion-dependencias
titulo: Inyección de dependencias
resumen: Técnica para que cada componente reciba desde afuera lo que necesita, en vez de construirlo, lo que permite cambiar implementaciones, controlar ciclos de vida y probar con dobles.
lectura: 14
---

## La idea central

Un componente casi nunca trabaja solo: el servicio de asignación necesita un cliente del modelo de ETA, un repositorio de envíos y un reloj; el asistente de soporte necesita un cliente de LLM, un buscador y un logger. La pregunta es **quién construye esas piezas**. Si cada componente las crea por su cuenta con `new` o con una función global, queda atado a una implementación concreta, con su configuración, sus credenciales y su red. Probarlo obliga a levantar todo; cambiar de proveedor obliga a editarlo.

La inyección de dependencias (DI, por *dependency injection*) invierte esa responsabilidad: el componente **declara** qué necesita y alguien de afuera se lo **entrega** ya armado. Es como un restaurante donde el cocinero recibe los ingredientes en la mesada en lugar de salir a comprarlos: la receta no cambia si mañana el proveedor de verduras es otro. Con agentes y LLMs esto pesa más de lo habitual, porque la dependencia más cara, lenta y no determinística del sistema es el cliente del modelo, y poder reemplazarlo por un doble en una prueba o por otro proveedor en producción es una decisión de diseño, no un detalle.

## Conceptos

### El problema: dependencias construidas adentro

Veamos el punto de partida. Este clasificador de tickets en Python crea su propio cliente:

```python
class ClasificadorTickets:
    def __init__(self):
        self.llm = ClienteLLM(api_key=os.environ["LLM_API_KEY"], modelo="modelo-grande")

    def clasificar(self, texto: str) -> Motivo:
        respuesta = self.llm.completar(prompt_clasificacion(texto))
        return Motivo.parse(respuesta)
```

Los problemas, uno por uno:

1. **No se puede probar sin red.** Cada test llama al proveedor real: tarda segundos, cuesta tokens y la respuesta cambia entre corridas.
2. **No se puede cambiar el modelo sin editar la clase.** Usar otro proveedor o un modelo chico para ciertos comercios requiere tocar este código.
3. **La configuración está escondida.** Para saber que la clase necesita una variable de entorno hay que leer su interior.
4. **Cada instancia crea un cliente nuevo.** Si se construyen 500 clasificadores, se abren 500 pools de conexiones.

La versión con inyección recibe el cliente:

```python
class ClasificadorTickets:
    def __init__(self, llm: ClienteLLM):
        self.llm = llm
```

**Ejemplo:** con la primera versión, la suite de 120 tests del clasificador tardaba 6 minutos y fallaba de forma intermitente cuando el proveedor limitaba la tasa. Con el cliente inyectado y un doble que devuelve respuestas grabadas, tarda 3 segundos y no falla por causas externas.

**Por qué importa:** una dependencia construida adentro es una decisión tomada en el lugar equivocado. El que sabe qué cliente usar es quien arma la aplicación, no el clasificador.

### Inversión de control, inyección de dependencias e inversión de dependencias

Tres nombres parecidos que conviene separar:

| Concepto | Qué dice | Nivel |
|---|---|---|
| Inversión de control (IoC) | Otro código decide cuándo llamarte y qué darte; tú no controlas el flujo principal | Principio general (frameworks, callbacks) |
| Inyección de dependencias (DI) | Las dependencias se pasan desde afuera en vez de crearse adentro | Técnica concreta, una forma de IoC |
| Principio de inversión de dependencias (DIP) | El código de alto nivel depende de abstracciones que él define, no de detalles | Principio de diseño, la D de [SOLID](#t/principios-solid) |

Se combinan pero no son lo mismo. Se puede inyectar una clase concreta (DI sin DIP): mejora la testabilidad, pero el dominio sigue conociendo al proveedor. Y se puede definir una interfaz en el dominio pero construir la implementación adentro (DIP sin DI), lo que no sirve de mucho. Lo valioso es la combinación: el dominio define la interfaz `ClienteLLM` o `EstimadorEta`, y la implementación concreta se inyecta desde afuera. Esa es la base de los puertos y adaptadores de [Arquitectura en capas, hexagonal y limpia](#t/arquitectura-capas-hexagonal).

**Ejemplo:** el servicio de asignación define `type EstimadorEta interface { Estimar(ctx, envio, candidato) (time.Duration, error) }`. Hay tres implementaciones: la que llama al servicio de ML por gRPC, una de respaldo con un cálculo por distancia, y un doble para tests. El servicio no importa ningún paquete de ML.

**Por qué importa:** en revisiones se oye "usamos DI" para referirse a cosas distintas. Separar los tres conceptos permite preguntar lo correcto: ¿el dominio depende de una abstracción propia, o solo recibe la clase concreta por constructor?

### Formas de inyectar: constructor, setter y parámetro

Hay tres maneras de entregar una dependencia:

- **Por constructor:** se pasa al crear el objeto y queda fija. Es la forma por defecto: el objeto nunca existe en un estado incompleto y las dependencias quedan a la vista en la firma.
- **Por setter o propiedad:** se asigna después de crear el objeto. Sirve para dependencias opcionales o para romper ciclos, pero permite objetos a medio armar.
- **Por parámetro de método:** se pasa en cada llamada. Útil cuando la dependencia cambia por invocación, como el contexto de la petición o el usuario actual.

```go
type ServicioAsignacion struct {
    envios   RepositorioEnvios
    eta      EstimadorEta
    reloj    func() time.Time
}

func NuevoServicioAsignacion(e RepositorioEnvios, eta EstimadorEta, reloj func() time.Time) *ServicioAsignacion {
    return &ServicioAsignacion{envios: e, eta: eta, reloj: reloj}
}

// Parámetro de método: el contexto viaja por llamada
func (s *ServicioAsignacion) Asignar(ctx context.Context, envioID string) error { /* ... */ }
```

**Ejemplo:** inyectar el reloj (`reloj func() time.Time`) parece exagerado hasta que hay que probar la regla "un envío sin retirar en 45 minutos se reasigna". Con `time.Now()` adentro, el test tendría que esperar 45 minutos o falsear la hora del sistema; con el reloj inyectado, se pasa una función que devuelve la hora deseada.

**Por qué importa:** un constructor con nueve parámetros es una señal útil: el componente hace demasiado. La inyección por constructor hace visible ese olor; un contenedor que inyecta campos privados lo esconde.

### La raíz de composición

Si cada componente recibe sus dependencias, alguien tiene que construirlas todas. Ese lugar es la **raíz de composición** (*composition root*): un único punto, lo más cerca posible del arranque (`main`, el módulo de inicio), donde se leen la configuración y los secretos, se crean las implementaciones concretas y se conectan entre sí. El resto del código no sabe de dónde vienen las piezas.

```go
func main() {
    cfg := config.Cargar()
    db := postgres.Conectar(cfg.DatabaseURL)
    etaCli := mlclient.Nuevo(cfg.EtaAddr, 40*time.Millisecond)

    envios := postgres.NuevoRepositorioEnvios(db)
    eta := eta.ConRespaldo(etaCli, eta.PorDistancia{})
    svc := asignacion.NuevoServicioAsignacion(envios, eta, time.Now)

    http.ListenAndServe(cfg.Addr, api.NuevoHandler(svc))
}
```

**Ejemplo:** el servicio de asignación tiene unas 25 dependencias en total. Todas se construyen en 60 líneas de `main.go`. Para saber qué timeout tiene la llamada al modelo de ETA o qué estimador de respaldo se usa, hay un solo archivo para mirar.

**Por qué importa:** la raíz de composición es el mapa del sistema. Cuando está dispersa (cada paquete con su `init()` que crea clientes globales) nadie sabe qué se conecta con qué hasta que falla.

### DI manual y contenedores

Hay dos maneras de armar la raíz de composición:

- **Manual** (*pure DI*): se escribe el código de construcción a mano, como en el ejemplo de Go. Es explícito, se depura con el debugger de siempre y los errores aparecen al compilar.
- **Con un contenedor:** una librería que conoce cómo construir cada tipo y resuelve el grafo automáticamente, a partir de anotaciones o registros.

| Ecosistema | Forma habitual |
|---|---|
| Go | Constructores manuales; `wire` genera ese mismo código en compilación |
| Kotlin / JVM | Spring (anotaciones, resuelve al arrancar) o Koin (DSL liviano) |
| TypeScript (Node) | NestJS con decoradores y módulos; o manual en servicios chicos |
| Python | Manual; en FastAPI, `Depends` resuelve dependencias por petición |
| React | Context y providers (ver más abajo) |

En FastAPI, la inyección por petición se ve así:

```python
def obtener_llm() -> ClienteLLM:
    return cliente_llm_global  # creado una vez al arrancar

@app.post("/tickets/clasificar")
def clasificar(t: Ticket, llm: ClienteLLM = Depends(obtener_llm)):
    return ClasificadorTickets(llm).clasificar(t.texto)

# En tests:
app.dependency_overrides[obtener_llm] = lambda: LLMGrabado("fixtures/tickets.json")
```

**Ejemplo:** un servicio de Go con 25 dependencias se arma bien a mano. Una aplicación Spring con 300 beans se beneficia del contenedor, a cambio de que un error de configuración aparezca al arrancar ("no se encontró un bean de tipo X") y no al compilar.

**Por qué importa:** el contenedor no es la inyección de dependencias; es una herramienta para automatizarla. En servicios chicos suele agregar más magia que valor.

### Ciclos de vida: singleton, por petición y transitorio

Además de qué implementación usar, hay que decidir **cuánto vive** cada instancia:

- **Singleton:** una sola instancia para toda la aplicación. Para cosas costosas y seguras de compartir: pools de conexiones, clientes HTTP, el cliente del LLM.
- **Por petición (scoped):** una instancia por petición HTTP o por conversación. Para lo que lleva datos de esa petición: el usuario autenticado, una transacción, el ID de traza.
- **Transitorio:** una instancia nueva cada vez que se pide. Para objetos livianos sin estado compartido.

La regla clave: **una dependencia no puede vivir menos que quien la tiene**. Si un singleton guarda una referencia a algo por petición, esa referencia queda congelada en la primera petición y se reutiliza en todas las siguientes.

**Ejemplo numérico de un bug por alcance equivocado.** El servicio que atiende al asistente registra `ContextoComercio` (el comercio autenticado) como singleton por error, en lugar de por petición:

1. A las 9:00:00 llega la primera consulta, del comercio A. Se crea `ContextoComercio(A)` y queda como singleton.
2. A las 9:00:01 llega una consulta del comercio B. El contenedor devuelve el mismo `ContextoComercio(A)`.
3. La herramienta `buscar_envios` del asistente filtra por el comercio del contexto: B ve envíos de A.
4. En el pod afectado, de 1.200 consultas por hora, todas las que no son de A (digamos 1.150) usan el contexto equivocado hasta el próximo reinicio.

Es una fuga de datos personales entre clientes causada por una línea de configuración. Al revés también duele: registrar el cliente del LLM como transitorio crea un cliente (y su pool de conexiones TLS) por consulta; con 50 consultas por segundo son 50 handshakes por segundo y decenas de milisegundos extra de latencia en cada una.

**Por qué importa:** los errores de alcance no fallan en los tests unitarios, que suelen tener una sola petición. Aparecen con concurrencia real. Los contenedores serios tienen validación de alcance (detectan un scoped dentro de un singleton); conviene activarla.

### Service locator: el antipatrón cercano

El **service locator** es un registro global al que cada componente le pide lo que necesita: `Locator.get(ClienteLLM)`. Parece inyección de dependencias porque desacopla de la implementación concreta, pero invierte la ventaja principal: las dependencias dejan de estar en la firma y quedan escondidas en el cuerpo de los métodos.

```kotlin
// Service locator: la dependencia no se ve desde afuera
class ResumidorCasos {
    fun resumir(caso: Caso): String = Locator.get<ClienteLLM>().completar(prompt(caso))
}

// Inyección por constructor: la dependencia es parte del contrato
class ResumidorCasos(private val llm: ClienteLLM) {
    fun resumir(caso: Caso): String = llm.completar(prompt(caso))
}
```

**Ejemplo:** un test de `ResumidorCasos` con locator pasa en local porque otro test registró antes un doble en el locator global, y falla en CI cuando cambia el orden de ejecución. Con constructor, el test construye el objeto con lo que necesita y no depende de nada global.

**Por qué importa:** el locator convierte errores de compilación en errores de ejecución y acopla los tests entre sí. Inyectar el propio contenedor en una clase es la misma idea con otro nombre.

### DI para probar: cambiar el cliente del LLM por un doble

El beneficio más inmediato de la inyección en sistemas con LLMs es poder reemplazar el modelo en las pruebas. Con el cliente inyectado detrás de una interfaz propia, el test le pasa un doble (ver [Testing y dobles de prueba](#t/testing-dobles)) que devuelve respuestas fijas o grabadas:

```typescript
interface ClienteLLM {
  completar(req: PedidoLLM): Promise<RespuestaLLM>;
}

class LLMFalso implements ClienteLLM {
  constructor(private respuestas: Map<string, RespuestaLLM>) {}
  async completar(req: PedidoLLM) {
    const r = this.respuestas.get(req.etiqueta);
    if (!r) throw new Error(`sin respuesta grabada para ${req.etiqueta}`);
    return r;
  }
}

const agente = new AgenteSoporte(new LLMFalso(grabadas), new HerramientasFalsas());
```

Lo mismo vale para las herramientas del agente: si `AgenteSoporte` recibe sus herramientas inyectadas, un test puede verificar que ante cierta respuesta del modelo se invoca `consultar_envio` con los argumentos correctos, sin tocar la base real.

**Ejemplo:** el agente de operaciones tiene 8 herramientas de solo lectura. En los tests unitarios se inyectan versiones falsas con datos fijos; en el entorno de evaluación, versiones que leen una copia anonimizada; en producción, las reales. El código del agente es idéntico en los tres casos.

**Por qué importa:** separar "el código que orquesta al modelo" de "el modelo" permite tests rápidos y determinísticos para lo primero, y dejar la calidad del modelo a las evaluaciones.

### DI en el frontend: context y providers

En React, la inyección de dependencias toma la forma de **context**: un componente proveedor en lo alto del árbol entrega una dependencia, y los componentes de abajo la consumen sin recibirla por props en cada nivel. El proveedor cumple el papel de raíz de composición de esa rama.

```tsx
const ApiEnviosContext = createContext<ApiEnvios | null>(null);

export function useApiEnvios() {
  const api = useContext(ApiEnviosContext);
  if (!api) throw new Error("falta ApiEnviosProvider");
  return api;
}

// App real
<ApiEnviosContext.Provider value={new ApiEnviosHttp("/bff")}>
  <PanelComercio />
</ApiEnviosContext.Provider>

// Storybook o test
<ApiEnviosContext.Provider value={new ApiEnviosEnMemoria(enviosDePrueba)}>
  <PanelComercio />
</ApiEnviosContext.Provider>
```

**Ejemplo:** el panel de comercios muestra el chat con el asistente. En Storybook se inyecta un cliente que simula una respuesta en streaming con pausas de 50 ms entre tokens, para diseñar los estados de carga sin llamar al modelo. Ver también [React](#t/react) y [Componentización](#t/componentizacion).

**Por qué importa:** el context no es solo para estado global; es el mecanismo para que los componentes no importen clientes concretos y se puedan mostrar y probar aislados.

## Casos prácticos

### Cambiar de proveedor de LLM sin tocar el asistente

**Situación:** por costo, se decide probar otro proveedor de LLM para el 20 % de las consultas del asistente. El cliente del proveedor actual se instanciaba en 11 archivos.

**Qué se hace:** se define la interfaz `ClienteLLM` en el dominio del asistente, con los tipos propios de pedido y respuesta. Se escriben dos adaptadores, uno por proveedor, y un tercero que reparte el tráfico entre ambos. Los 11 archivos pasan a recibir `ClienteLLM` por constructor, y la decisión de qué adaptador usar queda en la raíz de composición, leída de configuración. Volver atrás es cambiar un valor.

### Fuga de datos entre comercios por un singleton

**Situación:** un comercio reporta que el asistente le mostró un envío que no es suyo. Pasó solo en un pod y desapareció tras un reinicio.

**Qué se hace:** se encuentra el `ContextoComercio` registrado como singleton en el contenedor de NestJS. Se corrige a alcance por petición, se activa la validación de alcances y se agrega un test de integración que lanza 50 peticiones concurrentes de 5 comercios distintos y verifica que cada respuesta solo contiene envíos propios. Además, la herramienta `buscar_envios` recibe el comercio como parámetro explícito desde el token, no desde un objeto compartido.

### Tests del clasificador que costaban tokens

**Situación:** la suite de CI del clasificador de tickets llamaba al proveedor real: unos 2.000 pedidos por corrida, 40 corridas por día, y fallas intermitentes por límite de tasa.

**Qué se hace:** se inyecta el cliente y en los tests unitarios se usa un doble con respuestas grabadas de casos reales. La calidad del clasificador con el modelo real se mide aparte, en la evaluación nocturna sobre el golden set. La suite baja de 7 minutos a 10 segundos y deja de fallar por causas externas.

### Un contenedor para un servicio de cinco piezas

**Situación:** un agente de código propone agregar un framework de inyección con anotaciones al servicio de franjas y zonas, que tiene 5 dependencias.

**Qué se hace:** se rechaza en la revisión. Se arma la raíz de composición a mano en 20 líneas, explícitas y verificadas por el compilador. Se deja anotado en el ADR del servicio el criterio para reconsiderarlo: más de 40 dependencias o varios ciclos de vida por petición difíciles de cablear a mano.

## Errores comunes

- **Inyectar el contenedor o usar un locator global.** Esconde las dependencias y acopla los tests; recibir por constructor lo que se usa.
- **Alcances mal elegidos.** Datos de la petición en un singleton filtran información entre usuarios; clientes costosos como transitorios agotan conexiones. Activar la validación de alcances y probar con concurrencia.
- **Constructores gigantes tapados con anotaciones.** Diez dependencias inyectadas por campo no son un problema del contenedor, son una clase con demasiadas responsabilidades; dividirla.
- **Interfaces que copian al proveedor.** Una interfaz `ClienteLLM` con los tipos exactos de un SDK no permite cambiar de proveedor; definirla con los tipos propios del dominio.
- **Crear dependencias en el medio del código "solo esta vez".** Un `new ClienteHttp()` escondido en un helper rompe la raíz de composición; toda construcción de infraestructura va al arranque.
- **Usar dobles de LLM para medir calidad.** El doble sirve para probar el código que rodea al modelo; la calidad del modelo se mide con evaluaciones sobre el modelo real.

## Para discutir en equipo

- ¿Dónde está la raíz de composición de cada uno de nuestros servicios? ¿Se puede leer en un solo archivo?
- ¿Qué objetos con datos de la petición o de la conversación podrían estar registrados con un alcance equivocado?
- ¿En qué servicios el contenedor de inyección aporta y en cuáles solo agrega magia?
- Si mañana hay que cambiar de proveedor de LLM, ¿cuántos archivos tocamos? ¿Qué interfaz falta?
