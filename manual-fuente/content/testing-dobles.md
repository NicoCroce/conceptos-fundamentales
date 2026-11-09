---
slug: testing-dobles
titulo: Testing y dobles de prueba
resumen: Cómo repartir las pruebas entre unitarias, de integración y de punta a punta, cuándo usar cada doble de prueba y cómo probar código que llama a un LLM.
lectura: 15
---

## La idea central

Una suite de pruebas es una apuesta: se invierte tiempo en escribirla y mantenerla a cambio de **confianza para cambiar el código**. Una buena suite falla cuando algo se rompió y pasa cuando no; corre lo bastante rápido como para ejecutarla en cada cambio, y cuando falla dice dónde mirar. Una mala suite falla al azar, tarda 40 minutos, o pasa siempre porque en realidad no prueba nada.

Casi todas las decisiones de testing giran alrededor de una tensión: cuanto más real es una prueba (base de datos de verdad, servicios de verdad, navegador de verdad), más confianza da y más lenta y frágil es. Los **dobles de prueba** (objetos que reemplazan a una dependencia real durante un test) son la herramienta para ajustar ese equilibrio. Con LLMs aparece un problema adicional: la dependencia central del sistema no es determinística. La respuesta no es renunciar a las pruebas, sino separar con cuidado qué se prueba con tests (el código que rodea al modelo) y qué se mide con evaluaciones (la calidad del modelo). Y con agentes de código escribiendo tests, revisar si un test prueba algo pasó a ser una habilidad diaria.

## Conceptos

### Pirámide y trofeo: cómo repartir las pruebas

Las pruebas se suelen agrupar en tres niveles:

- **Unitarias:** prueban una función o una clase aislada, en memoria, sin red ni disco. Milisegundos cada una.
- **De integración:** prueban varias piezas juntas, con algunas dependencias reales (una base de datos en un contenedor, el cliente HTTP real contra un servidor de prueba). Segundos cada una.
- **De punta a punta (E2E):** prueban el sistema completo como lo usaría una persona o un cliente, con navegador o llamadas a la API pública. Decenas de segundos cada una.

La **pirámide de pruebas** propone muchas unitarias, menos de integración y pocas E2E, porque las de abajo son rápidas y estables. El **trofeo de pruebas**, popular en frontend, pone el peso en la integración: argumenta que muchas unitarias prueban detalles que no importan, y que una prueba que monta un componente con sus hijos y simula la red da más confianza por línea escrita.

**Ejemplo:** la suite del servicio de seguimiento de Rumbo, con cifras de orden de magnitud:

```barras
titulo: Pruebas del servicio de seguimiento
unidad: tests
Unitarias | 1400
Integración | 220
Contrato | 35
Punta a punta | 12
```

| Nivel | Cantidad | Tiempo por test | Tiempo total |
|---|---|---|---|
| Unitarias | 1.400 | ~5 ms | ~7 s |
| Integración | 220 | ~1,5 s (en paralelo) | ~2 min |
| Contrato | 35 | ~0,5 s | ~20 s |
| Punta a punta | 12 | ~30 s | ~6 min |

Las unitarias corren en cada guardado; integración y contrato, en cada PR; las E2E, antes de cada deploy (ver [CI/CD y GitOps](#t/ci-cd)). Si el reparto se invierte (200 E2E y 100 unitarias), la suite tarda una hora y nadie la corre en local.

**Por qué importa:** la forma exacta (pirámide o trofeo) importa menos que la pregunta de fondo: cada prueba debería estar en el nivel más bajo que todavía detecta el error que nos preocupa.

### Los cinco dobles de prueba

"Mock" se usa para todo, pero hay cinco tipos de dobles con propósitos distintos:

- **Dummy:** se pasa solo para cumplir una firma; nunca se usa. Un logger vacío cuando el test no mira los logs.
- **Stub:** devuelve respuestas fijas a las llamadas. Sirve para controlar la entrada indirecta del código bajo prueba: "el modelo de ETA responde 25 minutos".
- **Fake:** una implementación que funciona de verdad pero simplificada. Un repositorio en memoria con un mapa en lugar de Postgres.
- **Spy:** un stub que además registra cómo lo llamaron, para verificar después: "se envió un aviso, con este texto".
- **Mock:** un doble con expectativas preprogramadas que falla si no lo llaman exactamente como se esperaba: "se debe llamar a `notificar` una vez con estos argumentos".

```kotlin
// Stub: controla lo que entra
class EtaFija(private val minutos: Int) : EstimadorEta {
    override fun estimar(envio: Envio, t: Transportista) = Duration.ofMinutes(minutos.toLong())
}

// Fake: funciona de verdad, en memoria
class EnviosEnMemoria : RepositorioEnvios {
    private val datos = mutableMapOf<String, Envio>()
    override fun obtener(id: String) = datos[id] ?: throw EnvioNoEncontrado(id)
    override fun guardar(e: Envio) { datos[e.id] = e }
}

// Spy: registra lo que sale
class AvisosEspia : Notificador {
    val enviados = mutableListOf<Aviso>()
    override fun enviar(a: Aviso) { enviados += a }
}
```

| Doble | Pregunta que responde | Cuándo usarlo |
|---|---|---|
| Dummy | Ninguna | Parámetros obligatorios que el test no usa |
| Stub | ¿Qué hace mi código si la dependencia responde X? | Controlar entradas: respuestas, errores, timeouts |
| Fake | ¿Funciona el flujo con un almacenamiento creíble? | Repositorios, colas y cachés en tests de varias operaciones |
| Spy | ¿Qué le pidió mi código a la dependencia? | Efectos hacia afuera: avisos, eventos publicados |
| Mock | ¿Se respetó exactamente este protocolo de llamadas? | Pocas veces: cuando el orden o la cantidad de llamadas es el requisito |

**Ejemplo:** para probar "si un envío lleva 45 minutos sin retirar, se reasigna y se avisa al comercio", se usa un fake de envíos con un envío creado hace 46 minutos, un reloj stub, y un spy de avisos. El test verifica el estado final del envío en el fake y que el spy tenga un aviso. No le importa cuántas veces se llamó a `obtener`.

**Por qué importa:** usar el doble correcto evita tests frágiles. Un mock que verifica cada llamada rompe con cualquier refactorización interna, aunque el comportamiento siga igual.

### Mockear los bordes, no el interior

La regla práctica: se reemplazan con dobles **las dependencias que cruzan un borde del sistema** (red, disco, reloj, proveedores externos, el LLM) y se dejan reales las clases propias del dominio. Paso a paso:

1. Identificar qué hace el código bajo prueba que sea lento, no determinístico o con efectos externos.
2. Asegurarse de que eso entra por una interfaz inyectada (ver [Inyección de dependencias](#t/inyeccion-dependencias)).
3. Reemplazar solo eso por un doble.
4. Verificar el **resultado observable** (valor devuelto, estado guardado, mensaje publicado), no la secuencia de llamadas internas.

Una variante útil es "no mockear lo que no es tuyo": en lugar de mockear directamente el SDK del proveedor de LLM, se define una interfaz propia (`ClienteLLM`) con un adaptador delgado, se mockea la interfaz propia en los tests unitarios y se prueba el adaptador con una prueba de integración.

**Ejemplo:** un test del servicio de asignación mockeaba `Envio`, `Candidato` y `CalculadoraPuntaje`, todas clases propias, y verificaba que se llamara `calcular` tres veces. Al optimizar el código para calcular el puntaje una sola vez por lote, el test falló aunque el resultado era idéntico. La versión corregida usa las clases reales, un stub del modelo de ETA y verifica qué transportista quedó asignado.

**Por qué importa:** un test que conoce el interior del código prueba la implementación, no el comportamiento, y frena justamente las refactorizaciones que la suite debería habilitar.

### Pruebas de contrato entre servicios

Cuando el panel de comercios llama al BFF y el BFF llama al servicio de seguimiento, cada lado se prueba con un doble del otro. El riesgo es que los dobles se desactualicen: el panel prueba contra un BFF falso que devuelve `eta_minutos`, mientras el BFF real ya lo renombró a `eta`. Todas las pruebas pasan y producción se rompe.

Las **pruebas de contrato guiadas por el consumidor** (*consumer-driven contract tests*) cierran esa brecha:

1. El consumidor (el panel) escribe sus expectativas: "cuando pido `GET /envios/E-1`, espero un 200 con `estado` (string) y `eta` (número)".
2. Esas expectativas se guardan como un **contrato** versionado, en un repositorio o un broker de contratos.
3. El proveedor (el BFF) ejecuta en su CI todos los contratos de sus consumidores contra su implementación real.
4. Si un cambio del proveedor rompe un contrato, falla el CI del proveedor, antes del deploy.

**Ejemplo:** el BFF tiene 3 consumidores (panel web, app de transportistas y el asistente, que lo usa como herramienta). Un PR que elimina el campo `franja` rompe el contrato de la app de transportistas; el CI del BFF falla con el nombre del consumidor afectado y el campo. El equipo decide deprecarlo con una versión de transición. Las herramientas del asistente merecen contrato propio: si una respuesta cambia de forma, el modelo puede seguir "funcionando" con datos mal interpretados (ver [gRPC y REST](#t/grpc-rest)).

**Por qué importa:** los contratos reemplazan muchas pruebas E2E entre servicios, que son lentas y difíciles de mantener, por pruebas rápidas que fallan en el lugar correcto.

### Testcontainers: dependencias reales y descartables

Para las pruebas de integración, la pregunta es qué base de datos usar. Un fake en memoria o una base embebida distinta (SQLite en lugar de Postgres) no detecta errores de SQL específicos, índices, transacciones ni tipos. **Testcontainers** es una librería (disponible para Go, Kotlin/JVM, Python, Node y otros) que levanta contenedores reales desde el test: un Postgres, un Kafka o un Redis de la misma versión que producción, que se destruyen al terminar.

```go
func TestRepositorioEnvios(t *testing.T) {
    ctx := context.Background()
    pg, err := postgres.Run(ctx, "postgres:16-alpine",
        postgres.WithDatabase("rumbo"), postgres.BasicWaitStrategy())
    require.NoError(t, err)
    t.Cleanup(func() { pg.Terminate(ctx) })

    db := conectar(t, pg.MustConnectionString(ctx))
    migrar(t, db)
    repo := NuevoRepositorioEnvios(db)
    // ... guardar, obtener, verificar
}
```

**Ejemplo:** levantar el contenedor de Postgres tarda unos 3 segundos; se hace una vez por paquete y cada test corre en su propia transacción que se revierte al final. 80 tests de repositorio corren en unos 15 segundos y detectaron, entre otras cosas, una consulta que funcionaba en SQLite y fallaba en Postgres por el tipo de una columna de fecha.

**Por qué importa:** las pruebas de integración con la tecnología real son el lugar donde se prueban los adaptadores; con eso, los tests unitarios pueden usar fakes sin culpa.

### Tests flaky

Un test **flaky** (inestable) a veces pasa y a veces falla sin que cambie el código. Las causas típicas:

- **Tiempo:** `sleep(100)` esperando algo asincrónico, o dependencia de la hora real.
- **Orden:** tests que comparten estado global o datos en una base y dependen del orden de ejecución.
- **Concurrencia:** condiciones de carrera en el código o en el test.
- **Red y servicios externos:** llamadas reales a un proveedor, incluido el LLM.
- **Aleatoriedad sin semilla fija.**

El daño es acumulativo. Si cada uno de 20 tests flaky falla el 1 % de las veces, la probabilidad de que una corrida pase completa es 0,99^20, un 82 %: casi una de cada cinco corridas falla sin motivo, y el equipo aprende a apretar "reintentar" sin leer el error. A partir de ahí, las fallas reales también se ignoran.

**Ejemplo:** el equipo mide la tasa de falla de cada test en las últimas 200 corridas de CI. Los que fallan sin cambios de código van a cuarentena (corren, pero no bloquean el merge) con un ticket y un responsable, y se exige arreglarlos en dos semanas o borrarlos.

**Por qué importa:** una suite en la que no se confía no cumple su función, aunque tenga 90 % de cobertura.

### Probar código que llama a un LLM

El código alrededor del modelo (armar el prompt, parsear la salida, decidir qué herramienta ejecutar, manejar errores) es código común y se prueba como tal. Lo que no se prueba con tests unitarios es **si el modelo responde bien**; eso se mide con evaluaciones (ver [Evaluación de LLMs](#t/evaluacion-llms)). Las técnicas para la primera parte:

1. **Costuras determinísticas.** Separar el código en funciones puras alrededor de la llamada al modelo: `armar_prompt(caso) -> str`, `parsear(respuesta) -> Clasificacion`, `decidir(clasificacion) -> Accion`. Cada una se prueba sin modelo.
2. **Fakes con respuestas grabadas.** Se graba una vez la respuesta real del modelo para un conjunto de entradas y se guarda como fixture. Los tests reproducen esas respuestas. Si cambia el prompt, se regraban de forma deliberada y el cambio se revisa en el PR.
3. **Casos de borde de la salida.** Probar el parser con lo que los modelos hacen de verdad: JSON con texto alrededor, campos faltantes, un valor fuera del `enum`, una respuesta truncada por límite de tokens, una llamada a una herramienta que no existe.
4. **Bucle del agente con modelo guionado.** Un fake que devuelve una secuencia fija ("primero llama a `consultar_envio`, después responde") permite probar que el bucle ejecuta herramientas, respeta el límite de pasos y maneja errores.

```python
def test_reprograma_si_el_modelo_lo_pide():
    llm = LLMGuionado([
        llamada_herramienta("reprogramar_envio", envio="E-77", franja="14-16"),
        texto("Listo, su envío quedó para las 14 a 16 h."),
    ])
    envios = EnviosEnMemoria({"E-77": envio_pendiente("E-77")})
    agente = AgenteSoporte(llm, herramientas_con(envios), max_pasos=5)

    agente.atender("¿Pueden traerlo a la tarde?")

    assert envios.obtener("E-77").franja == Franja(14, 16)

def test_rechaza_motivo_fuera_del_enum():
    assert parsear('{"motivo": "no estaba"}').motivo == Motivo.OTRO
```

| Qué se verifica | Herramienta | Cuándo corre |
|---|---|---|
| Armado de prompt, parseo, validación, bucle | Tests unitarios con fakes | En cada PR, segundos |
| Adaptador del proveedor (formato, errores, timeouts) | Integración contra el proveedor o un servidor simulado | En cada PR o diario |
| Calidad de las respuestas | Evaluación sobre golden set con el modelo real | Nocturno o antes de cambiar modelo o prompt |

**Ejemplo:** el clasificador de tickets tiene 60 tests unitarios (3 segundos, sin red) y una evaluación de 800 casos con el modelo real que tarda 12 minutos y corre de noche. Un cambio de prompt que rompe el parser lo detectan los tests; un cambio que baja la exactitud del 91 % al 86 % lo detecta la evaluación.

**Por qué importa:** mezclar las dos cosas produce lo peor de ambas: tests lentos, caros y flaky que llaman al modelo, y ninguna medida estadística de calidad.

### Revisar tests escritos por un agente de código

Los agentes de código escriben tests con facilidad y en cantidad, y tienen sesgos reconocibles. El más común es el **test que verifica el mock**: configura un doble para devolver X y verifica que el código devuelve X, sin lógica propia en el medio.

```typescript
it("obtiene el envío", async () => {
  const repo = { obtener: vi.fn().mockResolvedValue({ id: "E-1", estado: "entregado" }) };
  const svc = new ServicioEnvios(repo);
  const r = await svc.obtener("E-1");
  expect(repo.obtener).toHaveBeenCalledWith("E-1");
  expect(r).toEqual({ id: "E-1", estado: "entregado" });
});
```

Este test pasa aunque `ServicioEnvios.obtener` sea una línea que delega, y seguiría pasando si se borrara toda la lógica de permisos que debería tener. Señales a buscar en la revisión:

- Los asserts repiten lo que configuró el doble.
- Se mockean clases propias del dominio.
- Hay muchos tests del camino feliz y ninguno de errores, límites o entradas inválidas.
- El test se modificó en el mismo PR para que pase con el código nuevo, en lugar de corregir el código.
- Nombres genéricos ("funciona correctamente") que no dicen qué regla protegen.

Una verificación útil es la **prueba de mutación** manual o automática: cambiar una condición del código (un `>` por `>=`, borrar una validación) y ver si algún test falla. Si ninguno falla, los tests no protegen esa regla.

**Ejemplo:** un agente agrega 40 tests a un módulo y la cobertura sube del 55 % al 88 %. Una corrida de mutación con 120 mutantes muestra que sobreviven 70: más de la mitad de los cambios al código no rompen ningún test. Con especificaciones claras del comportamiento esperado (ver [SDD](#t/sdd)) y la instrucción de escribir los tests a partir de ellas, la segunda versión deja sobrevivir 15.

**Por qué importa:** la cobertura mide qué líneas se ejecutaron, no qué se verificó. Con agentes generando código y tests a la vez, el riesgo es una suite que confirma lo que el código hace en lugar de lo que debería hacer.

## Casos prácticos

### La suite E2E de 45 minutos

**Situación:** el panel de comercios tiene 300 pruebas E2E con navegador que tardan 45 minutos y fallan en el 30 % de las corridas. El equipo hace merge sin esperarlas.

**Qué se hace:** se clasifican por qué protegen. Las que verifican reglas de formato o validaciones pasan a pruebas de componentes con la red simulada (trofeo). Las que verifican la forma de la respuesta del BFF pasan a pruebas de contrato. Quedan 15 E2E de flujos críticos (iniciar sesión, cargar un pedido, ver el seguimiento, consultar al asistente). La suite pasa a 8 minutos y la tasa de fallas espurias, por debajo del 2 %.

### Tests del asistente que llamaban al modelo real

**Situación:** los tests del asistente de soporte llamaban al LLM real. Fallaban una de cada diez corridas porque el modelo cambiaba la redacción, y alguien "arregló" los asserts para que verificaran solo que la respuesta no estuviera vacía.

**Qué se hace:** se separan las capas. El armado de prompt y el parseo se prueban con funciones puras; el bucle del agente, con un LLM guionado y herramientas falsas; las respuestas grabadas se guardan como fixtures versionados. La calidad de las respuestas pasa a la evaluación nocturna con el golden set y un juez con rúbrica. Los tests vuelven a fallar solo cuando el código está mal.

### Un cambio en el BFF que rompió al asistente

**Situación:** el BFF cambió `estado: "en_reparto"` por un objeto `estado: {codigo, descripcion}`. El panel se actualizó en el mismo PR, pero la herramienta `consultar_envio` del asistente seguía esperando un string. El modelo recibía `[object Object]` y respondía "el estado de su envío no está disponible".

**Qué se hace:** se agregan contratos guiados por el consumidor para las herramientas del asistente, igual que para el panel. El CI del BFF ejecuta los contratos de sus tres consumidores. Además, la herramienta valida la respuesta contra un esquema y, si no coincide, devuelve un error explícito en lugar de pasar datos rotos al modelo.

### Revisión de un PR con 60 tests nuevos

**Situación:** un agente de código implementó la regla de reprogramaciones (máximo 2 por envío) y agregó 60 tests. Todos pasan y la cobertura es del 94 %.

**Qué se hace:** el revisor busca primero el test de la regla: lo encuentra, pero el doble del repositorio está configurado para devolver un envío con `reprogramaciones = 0` en todos los casos, así que el límite nunca se ejerce. Pide tres tests concretos (0, 2 y 3 reprogramaciones previas), reemplazar el mock del repositorio por el fake en memoria, y eliminar 20 tests que solo verifican getters. El PR termina con 35 tests que protegen reglas.

## Errores comunes

- **Mockear todo.** Reemplazar clases propias por dobles produce tests que prueban el cableado; usar dobles solo en los bordes y verificar resultados observables.
- **Tests que llaman al LLM real en CI.** Son lentos, caros y flaky; usar respuestas grabadas y dejar la calidad para las evaluaciones.
- **Convivir con tests flaky.** El reintento automático sin seguimiento entrena al equipo a ignorar fallas; medir, poner en cuarentena con responsable y arreglar o borrar.
- **Fakes que divergen de la realidad.** Un repositorio en memoria que no respeta las restricciones de la base da falsa confianza; respaldar cada fake con pruebas de integración del adaptador real usando Testcontainers.
- **Confiar en la cobertura.** Un 90 % de líneas ejecutadas no dice qué se verificó; revisar asserts y usar pruebas de mutación en los módulos críticos.
- **Aceptar tests generados sin leerlos.** Un test escrito por un agente que repite lo que configuró el mock no protege nada; revisar los tests con el mismo cuidado que el código.

## Para discutir en equipo

- ¿Cuánto tarda hoy nuestra suite completa y qué parte se corre en local antes de un PR? ¿Qué tendríamos que mover de nivel?
- ¿Qué tests flaky conocemos y cuánto tiempo llevan así?
- ¿Dónde estamos probando la calidad del modelo con tests, o el código alrededor del modelo con evaluaciones?
- ¿Qué interfaces entre servicios (incluidas las herramientas de los agentes) no tienen contrato y se rompen sin aviso?
- ¿Qué criterio usamos para revisar tests escritos por agentes de código, y deberíamos escribirlo?
