---
slug: principios-solid
titulo: SOLID y principios de diseño
resumen: Los cinco principios SOLID y sus vecinos (cohesión, acoplamiento, DRY, KISS, YAGNI, Demeter) para escribir y revisar código que se pueda cambiar sin miedo.
lectura: 15
---

## La idea central

Casi todo el costo de un software aparece después de escribirlo: cuando hay que cambiarlo. Un cambio barato toca un solo lugar, se entiende leyendo poco código y no rompe nada lejano. Un cambio caro obliga a recorrer diez archivos, a adivinar qué depende de qué y a cruzar los dedos en el deploy. Los principios de diseño son heurísticas acumuladas para que los cambios caigan del lado barato. No son leyes ni reglas de estilo: son preguntas que conviene hacerle al código antes de que crezca.

**SOLID** es el grupo más conocido, cinco principios que Robert C. Martin reunió a principios de los 2000: responsabilidad única, abierto/cerrado, sustitución de Liskov, segregación de interfaces e inversión de dependencias. Alrededor hay otros igual de útiles: cohesión y acoplamiento, composición sobre herencia, DRY, KISS, YAGNI y la Ley de Demeter. Este tema los recorre con código de Rumbo y con una preocupación nueva: hoy una parte grande del código lo escribe un agente de código, que produce rápido y con buena sintaxis, pero que tiende a violar algunos de estos principios de forma sistemática. Saber nombrarlos es lo que permite revisar ese código con criterio y pedir cambios concretos en lugar de "esto no me gusta".

## Conceptos

### Cohesión y acoplamiento: la base de todo lo demás

Antes de SOLID conviene tener dos ideas, porque todos los principios son formas de mejorarlas:

- **Cohesión:** cuánto tienen que ver entre sí las cosas que están juntas. Un módulo es cohesivo si todo lo que contiene cambia por el mismo motivo. `calculo_eta.py` con funciones de distancia, tráfico y ajuste por zona es cohesivo; `utils.py` con formateo de teléfonos, reintentos HTTP y cálculo de ETA no lo es.
- **Acoplamiento:** cuánto necesita saber un módulo de otro para funcionar. Si el servicio de asignación lee directamente las tablas internas del servicio de turnos, está fuertemente acoplado: cualquier cambio de esquema en turnos lo rompe.

El objetivo es **alta cohesión y bajo acoplamiento**. Una forma práctica de medirlo es contar: ante un cambio típico del negocio, ¿cuántos archivos o servicios se tocan? Si agregar un estado nuevo de envío (`retenido_en_aduana`) obliga a tocar 14 archivos en 4 paquetes, hay baja cohesión (la noción de estado está dispersa) y alto acoplamiento (todos conocen la lista completa de estados).

**Ejemplo:** en un análisis del historial de commits del servicio de envíos, el equipo vio que el 70 % de los PRs que tocaban `envio.go` también tocaban `notificaciones.go` y `metricas.go`. Eso indica que una sola responsabilidad (el ciclo de vida del envío) está repartida en tres lugares que cambian juntos.

**Por qué importa:** cohesión y acoplamiento son el vocabulario común de toda revisión de diseño. Los principios que siguen son recetas para subir una y bajar el otro.

### S: responsabilidad única (SRP)

El **principio de responsabilidad única** dice que un módulo debe tener **un solo motivo para cambiar**. La formulación con "motivo para cambiar" es más útil que "hacer una sola cosa", porque obliga a preguntar quién pide los cambios. Si dos personas o áreas distintas pueden pedir cambios sobre la misma clase, esa clase tiene dos responsabilidades.

Antes:

```kotlin
class ReporteEntregas(private val db: DataSource) {
    fun generar(zona: String): String {
        val filas = db.query("SELECT ... WHERE zona = ?", zona)   // datos
        val tasa = filas.count { it.aTiempo } * 100.0 / filas.size // regla de negocio
        return "<h1>Zona $zona</h1><p>A tiempo: $tasa%</p>"        // presentación
    }
}
```

Esta clase cambia si el equipo de datos mueve la tabla, si operaciones redefine qué es "a tiempo" o si producto quiere el reporte en PDF. Tres motivos, tres áreas. Después:

```kotlin
class RepositorioEntregas(private val db: DataSource) { fun deZona(z: String): List<Entrega> = TODO() }
object TasaATiempo { fun calcular(e: List<Entrega>): Double = TODO() }
class FormatoHtmlReporte { fun render(zona: String, tasa: Double): String = TODO() }
```

**Ejemplo:** operaciones decide que una entrega con hasta 10 minutos de demora cuenta como "a tiempo". En la versión nueva se cambia una línea en `TasaATiempo` y su test; el HTML y la consulta no se tocan, así que el revisor solo mira 5 líneas en lugar de 40.

**Por qué importa:** SRP reduce el tamaño de los cambios y de los conflictos. Llevado al extremo produce clases de tres líneas imposibles de seguir; el criterio es el motivo de cambio, no la cantidad de líneas.

### O: abierto/cerrado (OCP)

El **principio abierto/cerrado** dice que un módulo debería estar **abierto a extensión y cerrado a modificación**: agregar comportamiento nuevo sin editar el código existente que ya funciona. La herramienta habitual es un punto de extensión: una interfaz, un mapa de estrategias o un registro.

Antes, en Go, el cálculo de tarifa por tipo de vehículo:

```go
func Tarifa(v Vehiculo, km float64) float64 {
    switch v.Tipo {
    case "moto":      return 300 + 40*km
    case "auto":      return 450 + 55*km
    case "camioneta": return 700 + 80*km
    }
    return 0
}
```

Cada vehículo nuevo (bicicleta, furgón refrigerado) obliga a editar esta función y a volver a probar todos los casos. Después:

```go
type Tarifador interface{ Tarifa(km float64) float64 }

var tarifadores = map[string]Tarifador{
    "moto": Lineal{Base: 300, PorKm: 40},
    "auto": Lineal{Base: 450, PorKm: 55},
    "refrigerado": ConRecargoFrio{Lineal{Base: 900, PorKm: 90}, 0.15},
}
```

Agregar el furgón refrigerado es sumar un tipo y una entrada en el mapa; `Lineal` y sus tests no se tocan.

**Ejemplo:** con valores hipotéticos, un envío de 12 km en moto cuesta 300 + 40 × 12 = 780 unidades. Ese cálculo queda congelado y testeado, aunque el mes siguiente se sumen tres tipos de vehículo nuevos.

**Por qué importa:** OCP protege lo que ya funciona. Pero no hay que aplicarlo preventivamente: un `switch` con tres casos estables es más claro que una interfaz. Se extrae el punto de extensión cuando el segundo o tercer caso nuevo demuestra que el eje de variación es real.

### L: sustitución de Liskov (LSP)

El **principio de sustitución de Liskov** (por Barbara Liskov) dice que si `B` es un subtipo de `A`, cualquier código que funciona con `A` tiene que seguir funcionando cuando recibe un `B`, sin sorpresas. No alcanza con que compile: el subtipo debe respetar el **contrato** del tipo base. En concreto, no puede pedir más (precondiciones más fuertes), ni garantizar menos (postcondiciones más débiles), ni lanzar errores que el base no lanzaba.

Antes, en TypeScript:

```typescript
interface ProveedorTracking { ubicacion(envioId: string): Promise<Coordenadas>; }

class TrackingTransportistaExterno implements ProveedorTracking {
  async ubicacion(id: string) {
    if (!id.startsWith("EXT-")) throw new Error("solo envíos externos"); // precondición más fuerte
    return this.api.posicion(id);
  }
}
```

Todo el código que recibe un `ProveedorTracking` asume que sirve para cualquier envío. Con esta implementación, el mapa en vivo se rompe en producción para los envíos propios. Después hay dos opciones: el contrato se hace explícito (`soporta(envioId): boolean` y un enrutador que elige el proveedor), o la clase deja de declararse sustituta y pasa a ser un tipo distinto.

**Ejemplo:** la señal típica de una violación de LSP es un `if (proveedor instanceof TrackingTransportistaExterno)` en el código cliente. Si alguien tiene que preguntar qué subtipo recibió, el subtipo no es sustituible.

**Por qué importa:** con agentes esto se vuelve concreto. Si el agente de operaciones recibe una lista de herramientas que implementan la misma interfaz `HerramientaConsulta`, y una de ellas en realidad escribe o tarda 40 segundos, el orquestador (que asume lectura rápida) toma decisiones equivocadas.

### I: segregación de interfaces (ISP)

El **principio de segregación de interfaces** dice que ningún cliente debería depender de métodos que no usa. Las interfaces grandes obligan a todos sus implementadores a escribir métodos vacíos y acoplan a los clientes a cambios que no les interesan.

Antes, en Python:

```python
class ServicioEnvios(Protocol):
    def consultar(self, envio_id: str) -> Envio: ...
    def reasignar(self, envio_id: str, transportista: str) -> None: ...
    def cancelar(self, envio_id: str, motivo: str) -> None: ...
    def exportar_csv(self, zona: str) -> bytes: ...
```

El agente de operaciones solo necesita consultar, pero recibe un objeto que también sabe cancelar. Después:

```python
class LectorEnvios(Protocol):
    def consultar(self, envio_id: str) -> Envio: ...

class GestorEnvios(LectorEnvios, Protocol):
    def reasignar(self, envio_id: str, transportista: str) -> None: ...
    def cancelar(self, envio_id: str, motivo: str) -> None: ...
```

**Ejemplo:** las herramientas del agente de operaciones se construyen recibiendo un `LectorEnvios`. Aunque una inyección de prompt convenza al modelo de intentar cancelar 200 envíos, el código de esa herramienta no tiene acceso a ningún método que escriba.

**Por qué importa:** ISP es diseño y también seguridad. Interfaces chicas son el equivalente en código del mínimo privilegio que se pide en [seguridad de agentes](#t/seguridad-agentes): cada herramienta recibe exactamente las capacidades que necesita.

### D: inversión de dependencias (DIP)

El **principio de inversión de dependencias** dice que los módulos de alto nivel (las reglas de negocio) no deben depender de los de bajo nivel (la base, el SDK de un proveedor), sino que ambos deben depender de abstracciones, y que esas abstracciones las define el que las usa. Es la idea que sostiene la arquitectura hexagonal (ver [Arquitectura en capas, hexagonal y limpia](#t/arquitectura-capas-hexagonal)).

Antes, en Go:

```go
type ClasificadorTickets struct{ cliente *proveedorx.Client } // SDK concreto

func (c *ClasificadorTickets) Clasificar(t string) (Categoria, error) {
    r, err := c.cliente.Chat(proveedorx.Request{Model: "modelo-x-grande", Prompt: t})
    // ... parseo específico del formato de proveedorx
}
```

Después, el dominio define lo que necesita:

```go
type ModeloTexto interface {
    Completar(ctx context.Context, prompt string) (string, error)
}
type ClasificadorTickets struct{ modelo ModeloTexto }
```

y un adaptador por proveedor implementa `ModeloTexto`. Cómo se cablean esas dependencias desde afuera es el tema de [inyección de dependencias](#t/inyeccion-dependencias).

**Ejemplo:** el test del clasificador pasa un `ModeloTexto` falso que devuelve `"demora"` para cierto texto. El test corre en 3 ms, no consume tokens y no falla cuando el proveedor tiene una caída.

**Por qué importa:** en sistemas con LLMs, el proveedor, el modelo y el precio cambian cada pocos meses. Sin DIP, cada cambio de modelo es un cambio en la lógica de negocio.

### Composición sobre herencia

La herencia dice "B **es un** A"; la composición dice "B **tiene un** A y le delega". La herencia acopla fuertemente: el hijo depende de detalles internos del padre, y una jerarquía de tres niveles obliga a leer tres clases para entender una. La composición permite combinar comportamientos en tiempo de ejecución y cambiar uno sin tocar los demás.

**Ejemplo:** el equipo empezó con `class Herramienta`, `class HerramientaConCache(Herramienta)`, `class HerramientaConReintentos(Herramienta)`. Cuando hizo falta una con caché y reintentos, la herencia no alcanzaba: o se crea `HerramientaConCacheYReintentos` (y la combinatoria explota: con 4 comportamientos hay 15 combinaciones) o se compone. Con composición, cada comportamiento envuelve a otro: `ConCache(ConReintentos(consultarEnvio))`. Es el patrón Decorator, que se ve en [patrones estructurales](#t/patrones-estructurales).

**Por qué importa:** la herencia sigue siendo útil para jerarquías estables y chicas, pero cuando el motivo es "reutilizar código", la composición casi siempre es mejor.

### DRY, KISS y YAGNI, y cuando chocan

Tres principios cortos que se citan mucho y se aplican mal:

- **DRY** (*don't repeat yourself*): cada **conocimiento** del sistema debe tener una única representación. Importa la palabra conocimiento: dos fragmentos de código iguales que representan reglas distintas no son duplicación, son coincidencia.
- **KISS** (*keep it simple*): preferir la solución más simple que resuelva el problema. Simple no es corto: un bucle explícito de 8 líneas puede ser más simple que una expresión funcional de una línea que nadie entiende.
- **YAGNI** (*you aren't gonna need it*): no construir capacidades para necesidades que todavía no existen. Cada abstracción especulativa tiene costo de lectura y de mantenimiento hoy, a cambio de un beneficio que quizás nunca llegue.

Chocan con frecuencia. DRY empuja a abstraer; KISS y YAGNI empujan a no hacerlo. Una regla práctica es la **regla de tres**: la primera vez se escribe, la segunda se tolera la copia, la tercera se abstrae, porque recién ahí se ve qué varía y qué no.

**Ejemplo:** la validación de dirección de los pedidos de comercios y la de los retiros en depósito se ven iguales hoy (calle, número, código postal). Alguien las unifica en `validarDireccion`. Seis meses después, los retiros admiten coordenadas sin calle y la función gana un parámetro `esRetiro: bool` y tres `if`. Era coincidencia, no conocimiento compartido: DRY mal aplicado.

**Por qué importa:** la duplicación equivocada se arregla copiando; la abstracción equivocada cuesta mucho más deshacerla, porque todos sus clientes dependen de ella.

### Ley de Demeter

La **Ley de Demeter** (o principio del menor conocimiento) dice que un método solo debería hablar con sus "vecinos inmediatos": sus parámetros, sus atributos y los objetos que crea. La señal de violación son las cadenas: `pedido.comercio().zona().deposito().direccion().ciudad()`. Ese código conoce la estructura interna de cinco objetos, y cualquier cambio en cualquiera lo rompe.

**Ejemplo:** en lugar de la cadena anterior, `pedido.ciudadDeOrigen()`. Si mañana el depósito sale del comercio y pasa a la ruta, cambia un método, no cuarenta llamadores. No aplica a builders ni a APIs fluidas, donde cada llamada devuelve el mismo objeto.

**Por qué importa:** en el contexto de un agente, una herramienta que devuelve un objeto anidado de seis niveles obliga al modelo a navegar estructura interna; una que devuelve exactamente lo que se pidió gasta menos tokens y se equivoca menos.

### Cómo los violan los agentes de código y cómo revisarlo

Los agentes de código optimizan para que la tarea pedida funcione ahora, con el contexto que tienen a la vista. Eso produce patrones de violación predecibles:

| Tendencia del agente | Principio afectado | Qué pedir en la revisión |
|---|---|---|
| Agregar un `if` más a una función grande en lugar de extraer | SRP, OCP | "Separar la regla nueva en su propia función con test" |
| Copiar un bloque parecido de otro archivo | DRY (o coincidencia) | "Decidir si es el mismo conocimiento; si lo es, reutilizar" |
| Crear interfaces, fábricas y capas "por si acaso" | YAGNI, KISS | "Quitar la abstracción con una sola implementación" |
| Instanciar el SDK o el cliente HTTP dentro de la lógica | DIP | "Recibir la dependencia por constructor" |
| Acceder a campos anidados de objetos ajenos | Demeter | "Exponer un método en el objeto dueño" |
| Silenciar errores para que el test pase | LSP (contrato) | "Respetar el error que declara la interfaz" |

Dos prácticas ayudan. La primera, darle al agente los principios como restricciones explícitas en la especificación o en las instrucciones del repositorio (ver [SDD](#t/sdd)): "las herramientas reciben interfaces de solo lectura", "no instanciar clientes de proveedores fuera de `adaptadores/`". La segunda, automatizar lo que se pueda: linters de imports por carpeta, límites de complejidad ciclomática, tests de arquitectura.

**Ejemplo:** en un PR generado por un agente para sumar el estado `retenido_en_aduana`, el revisor aplica la tabla en cinco minutos: encuentra dos `switch` editados (OCP), una copia de la validación de estados en otro paquete (DRY) y un cliente de base creado dentro del handler (DIP). Pide tres cambios concretos en lugar de reescribir el PR.

**Por qué importa:** el revisor humano se convierte en el guardián del diseño. Un PR de 600 líneas generado en 3 minutos se revisa mejor con una lista corta de preguntas de diseño que leyendo línea por línea.

## Casos prácticos

### El handler que hacía todo

**Situación:** un agente de código agregó la funcionalidad "notificar al comercio cuando un envío se demora más de 30 minutos". El PR modificó el handler de eventos `envio_actualizado`: ahora calcula la demora, consulta la base del comercio, arma el texto, llama al proveedor de SMS y registra métricas. El handler pasó de 40 a 190 líneas, y los tests existentes se modificaron para mockear el proveedor de SMS.

**Qué se hace:** la revisión nombra el problema como SRP: el handler cambia ahora por cinco motivos. Se pide separar la regla (`DetectorDemora`, función pura con tests de borde en 29, 30 y 31 minutos), el armado del mensaje y el envío detrás de una interfaz `Notificador`. El handler vuelve a orquestar en 15 líneas. Los tests viejos dejan de necesitar el mock de SMS, señal de que el acoplamiento bajó.

### Un tipo de transportista nuevo cada trimestre

**Situación:** Rumbo suma transportistas en bicicleta, luego furgones refrigerados, luego lockers de retiro. Cada vez hay que tocar el `switch` de capacidad, el de tarifa y el de zonas permitidas, que están en tres servicios distintos. Dos veces se olvidó uno y hubo envíos asignados a bicicletas fuera de zona.

**Qué se hace:** se aplica OCP con un registro de tipos de transportista: cada tipo implementa `Capacidad`, `Tarifa` y `ZonasPermitidas`, y un test recorre todos los tipos registrados verificando que implementan las tres. Sumar un tipo es agregar una implementación; olvidar un aspecto ya no compila. Tres tipos nuevos en un trimestre justificaron la abstracción; con uno solo no habría valido.

### La interfaz gorda del servidor MCP

**Situación:** el servidor [MCP](#t/mcp) interno expone al agente de operaciones un único objeto `ServicioOperaciones` con 22 métodos, de los cuales 6 escriben. Las herramientas de lectura reciben ese objeto completo. En una auditoría aparece que una herramienta de "consulta" llamaba a `reasignar` como efecto secundario para "refrescar" un dato.

**Qué se hace:** se aplica ISP: `LectorOperaciones` con los 16 métodos de lectura y `EscritorOperaciones` con los 6 de escritura. Las herramientas del agente de solo lectura se construyen únicamente con el lector, y el compilador impide el atajo. Las de escritura quedan en otro servidor con confirmación humana.

### La abstracción que nadie pidió

**Situación:** al pedirle a un agente de código "un endpoint para listar las franjas horarias por zona", el PR trae `FranjaRepositoryInterface`, `FranjaRepositoryImpl`, `FranjaServiceFactory`, `FranjaDTO`, `FranjaMapper` y un sistema de plugins para fuentes de datos. Doce archivos para una consulta.

**Qué se hace:** se nombra como YAGNI y KISS: hay una sola fuente de datos y ningún plan de otra. Se pide reducir a un handler, una función de consulta y un test. Se agrega a las instrucciones del repositorio una regla: "no crear interfaces con una sola implementación salvo en los puertos listados en `ARQUITECTURA.md`".

## Errores comunes

- **Aplicar SOLID como checklist en todo el código.** Los principios tienen costo; en un script de una vez o un CRUD sin reglas, una interfaz por clase es ruido. Aplicarlos donde hay cambio esperado o reglas que proteger.
- **Confundir duplicación de código con duplicación de conocimiento.** Unificar dos bloques iguales que representan reglas distintas crea acoplamiento falso; antes de abstraer, preguntar si cambiarían juntos.
- **Usar herencia para reutilizar.** Si la relación no es un "es un" estable, componer y delegar.
- **Subtipos que lanzan "no soportado".** Es la violación de Liskov más común; si un implementador no puede cumplir el contrato, el contrato o la jerarquía están mal.
- **Aceptar sin revisar las abstracciones especulativas de un agente de código.** Parecen prolijas, pero cada capa extra se mantiene para siempre; pedir que se justifiquen con un segundo caso real.
- **Darle a una herramienta del agente más interfaz de la que necesita.** El principio de segregación de interfaces es también una barrera de seguridad.

## Para discutir en equipo

- ¿En qué servicio nuestro un cambio de negocio típico toca más archivos, y qué principio está detrás?
- ¿Qué abstracciones tenemos con una sola implementación, y cuáles se justifican por tests o por incertidumbre real?
- ¿Qué reglas de diseño deberíamos escribir en las instrucciones del repositorio para que los agentes de código las respeten desde el primer intento?
- ¿Qué herramientas de nuestros agentes reciben interfaces más amplias que las que usan?
- ¿Dónde aplicamos DRY sobre algo que era coincidencia y hoy nos cuesta separar?
