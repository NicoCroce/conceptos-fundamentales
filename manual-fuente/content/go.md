---
slug: go
titulo: Go
resumen: Lenguaje compilado y concurrente, usado para servicios de baja latencia e infraestructura; cubre goroutines, contexto, errores, herramientas y riesgos típicos.
lectura: 7
---

## La idea central

Go es un lenguaje diseñado en Google para escribir servicios de red que muchas personas puedan mantener. Su apuesta es la simpleza: pocas características, un formato de código único, compilación rápida y un modelo de concurrencia integrado en el lenguaje. En Rumbo, el servicio de asignación está escrito en Go porque tiene que atender miles de peticiones por segundo dentro de un presupuesto de unos 50 ms, hablando con varias dependencias a la vez.

Si Python es una navaja suiza para explorar datos, Go es una llave fija bien calibrada: hace menos cosas, pero las hace de forma predecible.

## Conceptos

### Binario único y tipado estático

Go compila a un **binario único** que incluye todas sus dependencias. No hace falta instalar un intérprete ni librerías en el servidor: la imagen de contenedor puede pesar 15 a 30 MB y arrancar en milisegundos. Esto simplifica el despliegue, incluido el on-prem.

El **tipado estático** significa que el compilador verifica los tipos antes de ejecutar: pasar un `string` donde se espera un `int` no compila. Muchos errores que en otros lenguajes aparecen en producción, en Go aparecen al compilar.

### Recolector de basura y p99

Go gestiona la memoria con un **recolector de basura** (GC) concurrente: la mayor parte del trabajo ocurre en paralelo con el programa, con pausas muy breves. Pero el GC consume CPU, y si el servicio crea muchos objetos temporales por petición, el GC corre más seguido y compite con las peticiones, lo que se ve en el p99.

Dos parámetros importan:

- **GOGC** (por defecto 100): el GC se dispara cuando el heap creció un 100% desde la última recolección. Subirlo a 200 hace recolecciones menos frecuentes a cambio de más memoria.
- **GOMEMLIMIT**: un límite blando de memoria. Si el contenedor tiene 1 GiB, fijarlo en unos 900 MiB permite usar GOGC alto sin que el proceso sea eliminado por exceder memoria.

**Ejemplo:** un pod con 2 GiB que usa 300 MiB de heap y GC cada 50 ms puede pasar a GC cada 200 ms con `GOGC=400` y `GOMEMLIMIT=1800MiB`, liberando CPU para atender peticiones.

### Goroutines

Una **goroutine** es una función que corre de forma concurrente, lanzada con `go f()`. Son muy livianas (arrancan con unos pocos KB de pila) y el runtime de Go las reparte entre los hilos del sistema operativo. Un servicio puede tener decenas de miles sin problema; el servidor HTTP estándar usa una por petición.

### Canales y select

Los **canales** son tuberías tipadas para pasar valores entre goroutines: `ch <- v` envía, `v := <-ch` recibe. **`select`** espera sobre varios canales a la vez y ejecuta el primero que esté listo; es la herramienta para combinar resultados, timeouts y cancelaciones.

### context.Context y deadlines

`context.Context` transporta por la cadena de llamadas un **deadline** (hora límite), una señal de cancelación y valores de la petición (como el trace id). Si la petición tiene 50 ms de presupuesto, se crea un contexto con ese deadline y se pasa a cada llamada; cuando vence, todas las operaciones que lo respetan se cancelan. Por convención, es el primer parámetro de cualquier función que haga E/S.

**Ejemplo:** consultar el modelo con deadline y caer a una heurística si no responde a tiempo.

```go
func estimar(ctx context.Context, p Pedido, t Transportista) Estimacion {
	ctx, cancel := context.WithTimeout(ctx, 30*time.Millisecond)
	defer cancel()

	resultado := make(chan Estimacion, 1) // con buffer: la goroutine nunca queda bloqueada
	go func() {
		e, err := clienteModelo.Predecir(ctx, p, t)
		if err == nil {
			resultado <- e
		}
	}()

	select {
	case e := <-resultado:
		return e
	case <-ctx.Done():
		metricaRespaldo.Inc()
		return heuristica(p, t) // distancia y carga actual
	}
}
```

El canal con buffer de 1 es importante: si el modelo responde tarde, la goroutine puede depositar el resultado y terminar aunque nadie lo lea. Sin buffer, quedaría bloqueada para siempre (un goroutine leak).

### Errores como valores

Go no tiene excepciones: las funciones devuelven un `error` como último valor y se chequea explícitamente. Es verboso, pero hace visible cada punto de falla.

- **Wrapping:** `fmt.Errorf("leer features de %s: %w", zona, err)` agrega contexto conservando el error original.
- **`errors.Is(err, ErrSinCandidatos)`** pregunta si en la cadena hay un error concreto.
- **`errors.As(err, &errTimeout)`** busca un error de cierto tipo para leer sus campos.

### Interfaces implícitas, composición y genéricos

Un tipo cumple una interfaz si tiene sus métodos, sin declararlo. Esto permite definir interfaces pequeñas donde se usan: el servicio de asignación declara `type Estimador interface { Predecir(ctx, Pedido, Transportista) (Estimacion, error) }`, y en tests se pasa una implementación falsa. Go favorece la **composición** (incluir un tipo dentro de otro) sobre la herencia. Desde la versión 1.18 tiene **genéricos**, útiles para estructuras de datos y utilidades, aunque el código idiomático los usa con moderación.

### Herramientas

- `gofmt`: formato único, sin discusiones de estilo.
- `go vet`: detecta errores comunes (formatos mal usados, copias de locks).
- `go test`: tests y benchmarks integrados.
- **Race detector** (`go test -race`): detecta accesos concurrentes sin sincronización durante la ejecución.
- **pprof**: perfiles de CPU, memoria, goroutines y bloqueos, consultables en producción vía un endpoint HTTP interno.

### Ecosistema

Buena parte de la infraestructura cloud está escrita en Go: Kubernetes, Docker, Terraform, Prometheus, el Collector de OpenTelemetry, etcd. Leer Go ayuda a entender y depurar esas herramientas. Ver [Contenedores, ECS y EKS](#t/contenedores) y [gRPC y REST](#t/grpc-rest).

### Riesgos

- **Goroutine leaks:** goroutines bloqueadas para siempre que acumulan memoria.
- **Condiciones de carrera:** dos goroutines acceden a un mapa sin lock; en Go, la escritura concurrente sobre un mapa puede terminar el proceso.
- **nil:** punteros, mapas e interfaces nil causan panics; una interfaz que contiene un puntero nil no es igual a nil, una sorpresa clásica.

## Casos prácticos

### Consultas paralelas con deadline compartido

**Situación:** para cada pedido, el servicio necesita features del feature store y candidatos de Aurora. En serie tardan 28 + 8 = 36 ms.

**Qué se hace:** se lanzan en paralelo con `errgroup`, compartiendo el contexto de la petición. Si una falla, el contexto se cancela y la otra se detiene. El tiempo pasa a ser el máximo (28 ms), no la suma.

```go
g, ctx := errgroup.WithContext(ctx) // ctx ya trae el deadline de la petición
var feats Features
var cands []Transportista

g.Go(func() (err error) {
	feats, err = featureStore.Leer(ctx, pedido)
	return err
})
g.Go(func() (err error) {
	cands, err = repo.CandidatosCercanos(ctx, pedido.Ubicacion)
	return err
})
if err := g.Wait(); err != nil {
	return fmt.Errorf("preparar asignación: %w", err)
}
```

### Goroutines que se acumulan

**Situación:** la memoria del servicio crece de forma constante y el pod se reinicia cada dos días. El panel de pprof muestra 400.000 goroutines.

**Qué se hace:** el perfil de goroutines muestra que casi todas están bloqueadas enviando a un canal sin buffer que nadie lee después de un timeout, el patrón opuesto al ejemplo de arriba. Se agrega buffer al canal, se verifica que todas las llamadas respeten el contexto y se agrega una métrica `go_goroutines` con alerta de tendencia.

### Condición de carrera en una caché

**Situación:** una caché en memoria de features por zona es un `map` compartido. Ocasionalmente el proceso termina con "concurrent map writes".

**Qué se hace:** `go test -race` reproduce el problema en minutos. Se protege el mapa con `sync.RWMutex` (muchos lectores, un escritor) y se agrega `-race` al pipeline de CI.

### Picos de p99 por asignaciones de memoria

**Situación:** el p50 es de 12 ms, pero el p99 tiene picos de 70 ms que coinciden con ciclos del GC.

**Qué se hace:** el perfil de memoria de pprof muestra que cada petición crea slices nuevos para los 200 candidatos y serializa JSON con reflexión. Se reutilizan buffers con `sync.Pool`, se preasigna la capacidad de los slices y se ajustan `GOGC` y `GOMEMLIMIT`. El p99 baja a 30 ms. Ver [Baja latencia y alta disponibilidad](#t/latencia-disponibilidad).

## Errores comunes

- **Lanzar goroutines sin saber cómo terminan.** Cada `go f()` necesita una condición de salida clara: contexto, canal cerrado o resultado con buffer.
- **Ignorar el contexto.** Una función que hace E/S sin recibir `ctx` no respeta deadlines y sigue trabajando cuando el cliente ya se fue.
- **Descartar errores con `_`.** Se pierde la información justo donde algo falló; como mínimo, envolver y devolver.
- **No correr el race detector.** Las carreras son intermitentes; `-race` en CI las encuentra antes que producción.
- **Optimizar sin perfilar.** pprof indica dónde se va la CPU o la memoria; adivinar suele llevar a optimizar lo que no importa.

## Para discutir en equipo

- ¿Qué parte del presupuesto de 50 ms le damos al modelo antes de caer a la heurística, y cómo lo medimos?
- ¿Cómo hacemos visible en producción que hay goroutines acumulándose antes de que el pod se reinicie?
- ¿Vale la pena ajustar GOGC y GOMEMLIMIT por servicio, o preferimos reducir asignaciones en el código?
- ¿Qué servicios nuevos conviene escribir en Go y cuáles en Python?
