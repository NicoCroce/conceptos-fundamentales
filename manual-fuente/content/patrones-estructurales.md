---
slug: patrones-estructurales
titulo: Patrones estructurales: Adapter, Decorator, Facade y Proxy
resumen: Cuatro formas de envolver objetos para traducir interfaces, sumar comportamiento, simplificar subsistemas o controlar el acceso, y cómo distinguirlas aunque el código se parezca.
lectura: 12
---

## La idea central

Los **patrones estructurales** responden a una pregunta: cómo combinar objetos que ya existen para obtener algo más útil, sin reescribirlos. Casi todos funcionan igual por fuera: un objeto **envuelve** a otro y se interpone entre él y quien lo usa. Lo que cambia es la **intención** del envoltorio. El Adapter traduce una interfaz que no encaja. El Decorator agrega comportamiento sin cambiar la interfaz. La Facade ofrece una interfaz más simple sobre muchas piezas. El Proxy controla el acceso al objeto real.

Una analogía con un viaje: el **adaptador** de enchufe hace que el cargador entre en la pared de otro país; la **funda** con batería extra (decorador) es el mismo teléfono con algo más; la **recepción** del hotel (fachada) resuelve con una sola llamada cosas que involucran a limpieza, cocina y mantenimiento; el **portero** (proxy) decide quién pasa y cuándo. Para nosotros estos patrones son el material del que están hechas las integraciones con agentes: cada proveedor de LLM y cada API de transportista se integran con un adaptador, cada herramienta del agente se envuelve con reintentos, caché y métricas, el agente ve el sistema de envíos a través de una fachada, y los límites de uso se aplican con un proxy. Saber cuál es cuál ayuda a nombrar las cosas en una revisión y a no mezclar responsabilidades en un mismo envoltorio.

## Conceptos

### Adapter: traducir una interfaz que no encaja

El **Adapter** convierte la interfaz de una clase existente en la interfaz que el código cliente espera. Se usa cuando hay algo que funciona pero no tiene la forma correcta: un SDK de terceros, un sistema legado, la API de un transportista externo. El cliente sigue hablando su idioma; el adaptador traduce en ambas direcciones.

Paso a paso:

1. El dominio define la interfaz que necesita, con sus propios nombres y tipos.
2. Por cada sistema externo se escribe un adaptador que la implementa.
3. Adentro, el adaptador llama al sistema externo, convierte los datos y traduce los errores.

```go
// Interfaz del dominio
type Transportista interface {
    CrearRetiro(ctx context.Context, r Retiro) (CodigoSeguimiento, error)
}

// Adaptador para la API de un transportista externo
type adaptadorTransportistaNorte struct{ api *norteapi.Client }

func (a adaptadorTransportistaNorte) CrearRetiro(ctx context.Context, r Retiro) (CodigoSeguimiento, error) {
    resp, err := a.api.PostPickup(ctx, norteapi.Pickup{
        Addr:   formatearDireccionNorte(r.Origen), // ellos esperan una sola línea
        Weight: r.PesoGramos / 1000.0,             // ellos usan kg
        Window: r.Ventana.Desde.Format("15:04"),
    })
    if errors.Is(err, norteapi.ErrZoneNotCovered) {
        return "", ErrZonaNoCubierta // error del dominio, no del proveedor
    }
    return CodigoSeguimiento(resp.TrackingID), err
}
```

**Ejemplo:** Rumbo trabaja con 6 transportistas externos. Sin adaptadores, el servicio de asignación tendría 6 formatos de dirección, 3 unidades de peso y 6 familias de errores mezclados con la lógica de elección. Con adaptadores, la lógica conoce una sola interfaz, y sumar el séptimo transportista es escribir un adaptador de unas 150 líneas con sus tests.

**Por qué importa:** el adaptador es el lugar natural para la **traducción de errores** y la **validación de lo que entra**. Es lo que en [DDD](#t/ddd) se llama capa anticorrupción: impide que el modelo de un tercero (o la salida de un LLM) se filtre al dominio.

### Adapter por proveedor de LLM

El caso más frecuente en sistemas con agentes: cada proveedor de LLM tiene su formato de mensajes, de herramientas, de streaming y de errores. Uno llama "tools" a lo que otro llama "functions"; uno devuelve los argumentos de la herramienta como objeto y otro como texto JSON; los códigos de "límite de uso excedido" difieren.

```typescript
interface ModeloChat {
  responder(m: Mensaje[], herramientas: DefHerramienta[]): Promise<Turno>;
}

class AdaptadorProveedorA implements ModeloChat {
  async responder(m: Mensaje[], h: DefHerramienta[]): Promise<Turno> {
    const r = await this.sdk.messages.create({ messages: m.map(aFormatoA), tools: h.map(aToolA) });
    return {
      texto: extraerTexto(r),
      llamadas: r.content.filter(esToolUse).map(c => ({ nombre: c.name, args: c.input })),
      tokens: { entrada: r.usage.input_tokens, salida: r.usage.output_tokens },
    };
  }
}
```

El bucle del agente trabaja con `Turno`, que es nuestro: texto, llamadas a herramientas y consumo de tokens. Cambiar de proveedor o rutear entre varios (ver [Varios modelos y ruteo](#t/multimodelo)) no toca el bucle.

**Ejemplo:** al probar un segundo proveedor, el adaptador nuevo midió que ese proveedor contaba los tokens de las definiciones de herramientas de otra forma. Como el adaptador normaliza `tokens`, los dashboards de costo siguieron siendo comparables entre ambos.

**Por qué importa:** un servidor [MCP](#t/mcp) es, visto desde aquí, un adaptador estandarizado: traduce nuestras capacidades a un protocolo que cualquier cliente de agente entiende.

### Decorator: sumar comportamiento sin cambiar la interfaz

El **Decorator** envuelve un objeto con otro que implementa **la misma interfaz**, hace algo antes o después, y delega en el original. Como la interfaz no cambia, los decoradores se pueden apilar en cualquier orden y el código cliente no se entera. Es la aplicación directa de "composición sobre herencia" (ver [SOLID y principios de diseño](#t/principios-solid)).

```python
class Herramienta(Protocol):
    nombre: str
    def ejecutar(self, args: dict) -> dict: ...

class ConReintentos:
    def __init__(self, interna: Herramienta, intentos: int = 3, espera_s: float = 0.5):
        self.interna, self.intentos, self.espera_s = interna, intentos, espera_s
        self.nombre = interna.nombre

    def ejecutar(self, args: dict) -> dict:
        for i in range(self.intentos):
            try:
                return self.interna.ejecutar(args)
            except ErrorTransitorio:
                if i == self.intentos - 1:
                    raise
                time.sleep(self.espera_s * 2 ** i)   # 0,5 s, 1 s, ...
```

Con la misma forma se escriben `ConCache`, `ConMetricas` y `ConLog`, y se componen al registrar la herramienta:

```python
consultar_envio = ConMetricas(ConCache(ConReintentos(ConsultarEnvio(repo)), ttl_s=30))
```

**Ejemplo:** con valores hipotéticos, la herramienta `consultar_envio` falla el 2 % de las veces por errores transitorios de red. Con 3 intentos independientes, la probabilidad de que fallen los tres es 0,02³ = 0,000008, es decir 8 por millón. Y la caché de 30 segundos evita que el agente consulte 5 veces el mismo envío en una conversación: en las mediciones del equipo, eso redujo un 40 % las llamadas a la base.

**Por qué importa:** el orden importa. `ConCache(ConReintentos(x))` no reintenta lo que está en caché; `ConReintentos(ConCache(x))` sí intentaría la caché tres veces, lo que no tiene sentido. Y `ConMetricas` por fuera mide la latencia que percibe el agente; por dentro de los reintentos, mediría cada intento. Ambas son válidas, pero hay que decidirlo a propósito.

### Facade: una interfaz simple sobre un subsistema

La **Facade** ofrece una interfaz única y simplificada sobre un conjunto de componentes. No agrega capacidades nuevas ni oculta por completo el subsistema: quien necesite el detalle puede seguir usándolo. Lo que hace es resolver los casos frecuentes con una sola llamada que coordina varias piezas.

Para responder "¿dónde está mi pedido?", el asistente de soporte necesitaría consultar cinco componentes: pedidos (qué envíos generó), asignación (qué transportista), tracking (ubicación), ETA (minutos estimados) y novedades (incidentes). Si cada uno es una herramienta, el modelo tiene que descubrir el orden, encadenar 5 llamadas y combinar resultados.

```kotlin
class FachadaEnviosParaAgente(
    private val pedidos: Pedidos, private val asignacion: Asignacion,
    private val tracking: Tracking, private val eta: ServicioEta, private val novedades: Novedades,
) {
    fun estadoDePedido(pedidoId: String, actor: Actor): EstadoPedidoResumen {
        val envios = pedidos.enviosDe(pedidoId, actor)          // valida permisos
        return EstadoPedidoResumen(envios.map { e ->
            EnvioResumen(
                estado = e.estado,
                transportista = asignacion.nombreVisible(e.id),
                etaMinutos = eta.estimar(e.id),
                ultimaNovedad = novedades.ultima(e.id)?.descripcionCorta,
            )
        })
    }
}
```

La herramienta del agente `estado_de_pedido` llama a la fachada. El modelo hace una llamada en lugar de cinco.

**Ejemplo:** en una prueba con 200 conversaciones del golden set, pasar de 5 herramientas finas a 1 herramienta sobre la fachada bajó el promedio de llamadas por respuesta de 4,1 a 1,3, la latencia de la respuesta completa de 9 a 4 segundos, y los errores de encadenamiento (consultar ETA de un envío equivocado) prácticamente desaparecieron.

**Por qué importa:** diseñar herramientas para agentes es, en buena medida, diseñar fachadas. Los modelos rinden mejor con pocas herramientas de alto nivel, con nombres del negocio, que con muchas que reflejan la estructura interna de los servicios (ver [Agentes y tool calling](#t/agentes)).

### Proxy: controlar el acceso al objeto real

El **Proxy** tiene la misma interfaz que el objeto real y se interpone para **controlar el acceso**: cuándo se crea, quién puede usarlo, cuántas veces o desde dónde. La diferencia con el decorador es de intención: el decorador enriquece, el proxy custodia. Hay varias variantes:

- **Proxy virtual (carga diferida):** posterga la creación de algo caro hasta que se usa por primera vez.
- **Proxy de protección:** verifica permisos antes de delegar.
- **Proxy de límite de uso:** aplica cuotas o *rate limiting*.
- **Proxy remoto:** representa un objeto que vive en otro proceso (un stub de gRPC es un proxy remoto generado).

```typescript
class ProxyLimiteHerramienta implements Herramienta {
  constructor(private real: Herramienta, private limitador: Limitador, private sesion: Sesion) {}
  get nombre() { return this.real.nombre; }

  async ejecutar(args: unknown) {
    if (!this.sesion.permisos.includes(this.real.nombre))
      return { error: "herramienta no permitida para este usuario" };
    if (!(await this.limitador.permitir(this.sesion.usuarioId, this.real.nombre)))
      return { error: "límite de consultas alcanzado, intentar en un minuto" };
    return this.real.ejecutar(args);
  }
}
```

**Ejemplo:** el agente de operaciones tiene una herramienta `exportar_historial_zona` que lee hasta 50.000 filas. Un proxy limita a 10 ejecuciones por usuario por hora. Un día, un bucle del agente que repetía la misma llamada se cortó en la undécima en lugar de saturar la réplica de lectura. Otro proxy, virtual, carga el índice de zonas (300 MB) solo cuando alguna herramienta lo necesita por primera vez, y el servidor arranca en 2 segundos en lugar de 40.

**Por qué importa:** los controles que protegen a un sistema con agentes (permisos, cuotas, presupuesto de tokens por conversación) tienen que estar en código que el modelo no puede saltear. Un proxy alrededor de cada herramienta es un lugar ordenado para ponerlos, complementario a lo que se describe en [Seguridad de LLMs y agentes](#t/seguridad-agentes).

### Composite, brevemente

El **Composite** permite tratar a un objeto individual y a un grupo de objetos de la misma forma, armando estructuras de árbol. Un grupo implementa la misma interfaz que sus elementos y delega en cada uno.

**Ejemplo:** una ruta de reparto contiene paradas; un lote contiene rutas. Si `Ruta`, `Parada` y `Lote` implementan `DuracionEstimada()`, el lote la calcula sumando la de sus rutas, y cada ruta la de sus paradas. En agentes aparece igual: un "kit de herramientas" que agrupa herramientas y se registra como una unidad, o un plan con subtareas que a su vez tienen subtareas.

**Por qué importa:** evita el código cliente lleno de `if es_grupo ... else ...`. Pero solo vale cuando de verdad hay jerarquía; para listas planas, una lista alcanza.

### Por qué se parecen y cómo distinguirlos

En el código, los cuatro patrones principales se ven casi iguales: una clase que guarda una referencia a otra y delega. La forma de distinguirlos es mirar dos cosas: si la interfaz cambia y para qué existe el envoltorio.

| Patrón | ¿Cambia la interfaz? | Envuelve a | Intención | Ejemplo en Rumbo |
|---|---|---|---|---|
| Adapter | Sí, la traduce | Uno | Hacer encajar algo ajeno | API de un transportista externo |
| Decorator | No | Uno | Agregar comportamiento | Reintentos y caché en una herramienta |
| Facade | Sí, la simplifica | Varios | Ofrecer una entrada simple | Estado de pedido para el agente |
| Proxy | No | Uno | Controlar el acceso | Permisos y cuotas por usuario |
| Composite | No | Muchos del mismo tipo | Tratar grupo e individuo igual | Lote de rutas con paradas |

Una pregunta rápida para una revisión: "si quito este envoltorio, ¿qué deja de pasar?". Si el código deja de compilar porque las interfaces no encajan, era un adaptador. Si deja de haber reintentos o métricas, era un decorador. Si el cliente tiene que hacer cinco llamadas en lugar de una, era una fachada. Si cualquiera puede hacer cualquier cosa sin límite, era un proxy.

**Ejemplo:** en un PR, una clase `HerramientaEnvioWrapper` traducía el formato del SDK, reintentaba, verificaba permisos y medía latencia. Se pidió separarla en un adaptador, un decorador de reintentos, un proxy de permisos y un decorador de métricas. Cuatro clases chicas, cada una testeable por separado, que se pueden reutilizar en las otras 11 herramientas.

**Por qué importa:** mezclar intenciones en un solo envoltorio es el error más común con estos patrones. Nombrar cada pieza por su intención hace que el diseño se lea solo.

## Casos prácticos

### El séptimo transportista

**Situación:** Rumbo incorpora un transportista regional cuya API devuelve los estados como códigos numéricos (`3` es "en camino", `7` es "ausente") y las fechas en hora local sin zona horaria. El primer borrador, generado por un agente de código, agregaba `if transportista == "regional"` en cuatro lugares del servicio de tracking.

**Qué se hace:** se rechaza el enfoque y se pide un adaptador que implemente la interfaz `Transportista` existente, con una tabla de traducción de estados y la conversión de fechas a UTC. Los cuatro `if` desaparecen. Se agrega un test de contrato que corre contra todos los adaptadores: crear un retiro, consultarlo y verificar que los estados devueltos pertenecen al conjunto del dominio.

### Herramientas que fallaban sin dejar rastro

**Situación:** el agente de operaciones a veces responde "no pude consultar los datos" y nadie sabe qué herramienta falló ni por qué. Cada herramienta tiene su propio manejo de errores, algunas reintentan, otras no, y ninguna emite métricas.

**Qué se hace:** se definen tres decoradores comunes, `ConReintentos` (solo para errores transitorios y solo en herramientas de lectura), `ConMetricas` (latencia, errores y tamaño de respuesta por herramienta) y `ConTraza` (un span de [OpenTelemetry](#t/opentelemetry) por ejecución), y se aplican en el registro de herramientas, no dentro de cada una. En una semana el tablero muestra que el 80 % de los fallos viene de una sola herramienta con un timeout demasiado corto.

### Demasiadas herramientas para el asistente

**Situación:** el asistente de soporte expone 23 herramientas, una por endpoint interno. Las evaluaciones muestran que el modelo elige mal la herramienta en el 12 % de los casos y encadena llamadas innecesarias, lo que sube la latencia y el consumo de tokens.

**Qué se hace:** se diseña una fachada por intención del usuario: `estado_de_pedido`, `reprogramar_entrega`, `reportar_problema` y `consultar_politica`. Cada una coordina los servicios necesarios por dentro. El asistente pasa a tener 6 herramientas; el error de selección baja al 3 % en el golden set. Las 23 operaciones finas siguen existiendo para el agente de operaciones, que las necesita.

### Un agente en bucle contra la réplica

**Situación:** un cambio de prompt hizo que el agente de operaciones, ante una respuesta ambigua, repitiera la misma consulta pesada. En una hora ejecutó 340 veces `exportar_historial_zona` y la réplica de lectura de Aurora llegó al 95 % de CPU.

**Qué se hace:** se envuelve cada herramienta costosa en un proxy con cuota por usuario y por conversación, y se agrega un decorador de caché de 5 minutos para consultas idénticas. El proxy responde con un error explícito que el modelo puede leer ("límite alcanzado"), en lugar de una excepción. Se suma una alerta cuando una conversación supera 20 llamadas a herramientas.

## Errores comunes

- **Un envoltorio que hace todo.** Traducir, reintentar, autorizar y medir en la misma clase impide reutilizar y testear; separar por intención.
- **Adaptadores que dejan pasar tipos y errores del proveedor.** Si el dominio termina atrapando `norteapi.ErrZoneNotCovered`, el adaptador no está aislando nada; traducir siempre a tipos propios.
- **Apilar decoradores sin pensar el orden.** Reintentos por fuera de la caché, métricas por dentro de los reintentos o reintentos sobre operaciones de escritura no idempotentes producen comportamientos sorprendentes.
- **Fachadas que se vuelven el sistema entero.** Una fachada con 60 métodos es otra interfaz gorda; diseñarla para un cliente concreto (el agente de soporte) y no para todos.
- **Poner los controles de acceso en el prompt en lugar de en un proxy.** El modelo puede ser convencido de ignorar una instrucción; un proxy en el código no.
- **Llamar "adapter" o "proxy" a cualquier wrapper.** El nombre guía al próximo que lea el código; usar el del patrón que corresponde a la intención real.

## Para discutir en equipo

- ¿Qué integraciones con proveedores de LLM o transportistas tenemos sin un adaptador claro, y qué tipos ajenos se filtran a nuestra lógica?
- ¿Qué comportamientos (reintentos, caché, métricas, trazas) repetimos dentro de cada herramienta en lugar de aplicarlos como decoradores?
- ¿Cuántas herramientas ve cada agente hoy, y cuáles convendría agrupar detrás de una fachada?
- ¿Dónde están hoy los permisos y las cuotas de las herramientas: en el prompt, en un proxy o en el caso de uso?
- ¿Qué envoltorios de nuestro código mezclan varias intenciones y cómo los separaríamos?
