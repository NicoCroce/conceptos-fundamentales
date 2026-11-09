---
slug: instrucciones-reglas
titulo: Instrucciones y reglas de proyecto para agentes
resumen: Qué son los archivos de instrucciones persistentes que un agente lee en cada sesión (CLAUDE.md, AGENTS.md, reglas de Cursor y Copilot), cómo se combinan y cómo escribirlos y mantenerlos.
lectura: 19
---

## La idea central

Cada vez que alguien abre una sesión con un agente de código, el agente empieza sin saber nada del repositorio: no sabe que los tests se corren con `make test`, que las migraciones aplicadas no se tocan o que el equipo decidió no usar ORM. Puede descubrirlo leyendo, pero le cuesta turnos, tokens y a veces se equivoca. Los **archivos de instrucciones persistentes** resuelven eso: son documentos en texto plano que el arnés del agente carga automáticamente al inicio de cada sesión y mantiene en el contexto durante todo el trabajo. `CLAUDE.md`, `AGENTS.md`, las reglas de Cursor en `.cursor/rules/` y `.github/copilot-instructions.md` son variantes de la misma idea. En un agente propio, el equivalente es el prompt de sistema que arma el equipo.

La analogía útil es el documento de bienvenida de una persona nueva, con una diferencia: la persona lo lee una vez; el agente lo "relee" en cada turno, porque viaja dentro de cada llamada al modelo. Por eso un buen archivo de instrucciones se parece más a una lista de verificación corta que a una wiki. Este tema es una de las piezas del mapa general de [artefactos de agentes](#t/artefactos-agentes), junto con [comandos](#t/comandos-agentes), [skills](#t/skills-agentes) y [hooks](#t/hooks-agentes).

## Conceptos

### Qué es un archivo de instrucciones y en qué se diferencia de un prompt suelto

Un prompt suelto es lo que alguien escribe en el chat para una tarea: "agrega un endpoint para cancelar retiros". Vive en esa conversación y desaparece con ella. Un archivo de instrucciones es distinto en tres aspectos:

1. **Se carga siempre.** El arnés lo inyecta en el contexto sin que nadie lo pida, en todas las sesiones de todas las personas que trabajan en el repositorio.
2. **Está presente en cada turno.** No se lee una vez y se olvida: forma parte del bloque fijo que acompaña cada llamada al modelo, igual que el prompt de sistema (ver [Prompt engineering](#t/prompt-engineering)).
3. **Es compartido y versionado.** Vive en el repositorio, pasa por revisión de código y tiene historial, como cualquier otro archivo.

La consecuencia práctica es que el archivo de instrucciones cuesta contexto siempre, haga falta o no en esa tarea. Una regla sobre cómo nombrar migraciones ocupa espacio también cuando la tarea es corregir un typo en el README.

**Ejemplo:** un desarrollador de Rumbo escribe en cinco sesiones "los tests de integración necesitan `docker compose up db` antes". En el `AGENTS.md`, lo escribe una vez y vale para todo el equipo.

**Por qué importa:** lo que se repite en el chat debería estar en el archivo, y lo que solo sirve para una tarea no debería estar. Esa frontera define casi todo lo demás del tema.

### El panorama de formatos (noviembre de 2026)

Cada herramienta tiene su archivo, aunque convergen. Los nombres, rutas y campos cambian rápido; esta tabla describe ejemplos vigentes a noviembre de 2026 y conviene verificar la documentación de cada herramienta antes de adoptar un detalle.

| Archivo | Herramienta | Alcance típico | Notas |
|---|---|---|---|
| `CLAUDE.md` | Claude Code | Proyecto, usuario (`~/.claude/CLAUDE.md`), organización, subcarpetas | Admite importar otros archivos con `@ruta`; reglas por ruta en `.claude/rules/` |
| `AGENTS.md` | Formato abierto: Codex, Cursor, Copilot, Gemini CLI, Zed y otros | Raíz y subcarpetas | Markdown sin campos obligatorios; la idea es un archivo para todas las herramientas |
| `.cursor/rules/*.mdc` | Cursor | Proyecto, con reglas de usuario y de equipo aparte | Front matter con `description`, `globs` y `alwaysApply` |
| `.github/copilot-instructions.md` | GitHub Copilot | Repositorio | Además, `.github/instructions/*.instructions.md` con `applyTo` para patrones de archivos |
| Prompt de sistema | Agente propio sobre un SDK | Lo que el equipo decida | El equipo arma el ensamblado: base, reglas del dominio, datos del usuario |

`AGENTS.md` nació como formato neutro para no mantener cinco archivos iguales, y hoy lo leen muchas herramientas. Donde una no lo lee de forma nativa, su archivo propio puede ser una línea que importe o apunte al `AGENTS.md`.

**Ejemplo:** en el repositorio de ruteo de Rumbo conviven personas que usan Claude Code, Cursor y Copilot. El equipo mantiene un único `AGENTS.md` con el contenido real; `CLAUDE.md` contiene solo `@AGENTS.md` más dos líneas propias de Claude Code, y Cursor y Copilot leen el `AGENTS.md` directamente.

**Por qué importa:** cinco archivos con el mismo contenido se desincronizan en semanas. Una fuente única con adaptadores mínimos evita que cada herramienta siga reglas distintas.

### Jerarquía y alcance

Las instrucciones vienen en capas, de lo más general a lo más específico:

1. **Organización o empresa:** políticas que gestiona plataforma o seguridad y que el usuario no puede desactivar (por ejemplo, "no subir código a servicios externos de pegado"). Algunas herramientas lo implementan con un archivo en una ruta del sistema distribuida por MDM o con reglas de equipo en su consola.
2. **Usuario (global):** preferencias personales que valen en todos los proyectos de esa persona, en su carpeta de usuario: idioma de las respuestas, estilo de commits, "no agregar atribución en commits".
3. **Proyecto:** el archivo versionado en la raíz del repositorio. Es el que más importa, porque lo comparte todo el equipo.
4. **Carpeta o subdirectorio:** un archivo dentro de `services/eta/` que solo aplica al trabajar ahí. Según la herramienta se carga al iniciar o recién cuando el agente lee archivos de esa carpeta.
5. **Local no versionado:** notas personales sobre ese proyecto (rutas de la máquina, credenciales de prueba de un entorno local) que van en el `.gitignore`. En Claude Code existió `CLAUDE.local.md`; hoy se recomienda una importación desde la carpeta de usuario. Verificar la variante vigente.

**Cómo se combinan.** En casi todas las herramientas las capas **se suman**: el modelo recibe todas, una después de otra. No hay un motor que resuelva conflictos; si dos capas chocan, el modelo ve las dos y decide. Por convención, se espera que la más específica prevalezca (la de la carpeta sobre la del proyecto, la del proyecto sobre la del usuario), y algunas herramientas lo explicitan: con `AGENTS.md` anidados, el más cercano al archivo que se edita gana. La excepción son las políticas de organización, que deben ganar siempre; justamente por eso lo que es obligatorio de verdad no debería depender de instrucciones sino de permisos o hooks.

```arbol
titulo: Capas que recibe el agente
Contexto de instrucciones
- Organización
-- Políticas no desactivables
- Usuario
-- Preferencias personales
- Proyecto
-- AGENTS.md en la raíz
-- Reglas por ruta (globs)
- Carpeta
-- services/eta/AGENTS.md
- Local
-- Notas no versionadas
```

**Ejemplo:** el archivo global de un desarrollador dice "commits en inglés, formato Conventional Commits"; el del proyecto, "commits en castellano, en imperativo". El modelo recibe las dos y elige una, y el historial queda mezclado. Se resuelve en tres frentes: el proyecto aclara "aunque las preferencias personales digan otra cosa", el desarrollador acota su regla a "proyectos sin convención propia" y un hook de `commit-msg` verifica el formato para todos.

**Por qué importa:** cuando un agente "desobedece", muchas veces está obedeciendo otra capa que nadie revisó. Saber qué capas existen es el primer paso para depurar.

### Reglas condicionales por ruta e importaciones

Cargar todo siempre es caro. Por eso varias herramientas permiten **reglas condicionales**: una regla se activa solo cuando el agente trabaja con archivos que coinciden con un patrón (*glob*), como `**/*.sql` o `services/eta/**`. En Cursor es el campo `globs` de una regla `.mdc`; en Copilot, `applyTo` en un archivo `.instructions.md`; en Claude Code, el campo `paths` de un archivo en `.claude/rules/`. Cursor además permite reglas que el agente pide según su `description` y reglas que solo se aplican si alguien las menciona.

Una regla condicional de Cursor:

```markdown
---
description: Convenciones para migraciones de Aurora PostgreSQL
globs: db/migrations/**/*.sql
alwaysApply: false
---
- Cada migración nueva es un archivo nuevo; las aplicadas no se editan.
- Toda columna nueva en tablas con más de 1 millón de filas es nullable o tiene default.
- Crear índices con CREATE INDEX CONCURRENTLY.
```

Las **importaciones** permiten que el archivo principal referencie otros (en Claude Code, `@docs/arquitectura.md`) y el arnés los inserte: sirven para no duplicar y para separar por tema. Pero lo importado se carga siempre; no ahorra tokens. Ahorran la carga condicional o un puntero ("para cambios en el modelo de ETA, leer `docs/eta.md`") que el agente sigue solo cuando hace falta.

**Ejemplo:** las 25 líneas sobre migraciones del repositorio de ruteo pasan del archivo raíz a una regla condicional. Solo el 8 % de las tareas toca `db/migrations/`, así que en el 92 % restante esos 600 tokens dejan de viajar (cifras hipotéticas).

**Por qué importa:** las reglas por ruta permiten ser detallado donde hace falta sin pagar ese detalle en todas partes.

### Qué poner y qué no poner

La pregunta que filtra todo es: **¿el agente se equivocaría sin esta línea?** Si la respuesta es no, sobra.

| Poner | No poner |
|---|---|
| Comandos exactos de build, test y lint (`make test-unit`, no "corre los tests") | Lo que el agente deduce leyendo el código (que el proyecto usa Go, la lista de carpetas) |
| Convenciones no obvias ("los errores de dominio se envuelven con `apperr.Wrap`") | Instrucciones vagas ("escribe código limpio", "sigue buenas prácticas") |
| Arquitectura en 5 a 10 líneas: qué módulo hace qué y qué no se cruza | Documentación completa de la API o del dominio |
| "Nunca X" con el porqué ("no llamar al modelo de ETA desde handlers: tiene presupuesto de 50 ms y pasa por el cliente con caché") | Secretos, tokens, contraseñas o URLs internas sensibles |
| Decisiones tomadas para que no se reabran ("sin ORM; ver ADR-007") | Listas enormes: 80 reglas de estilo que ya aplica el linter |
| Definición de terminado ("tests verdes, linter limpio, sin TODO nuevos") | Historia del proyecto o quién escribió qué |

Dos criterios para cada línea: que sea **accionable** (dice qué hacer, no qué valorar) y **verificable** (alguien puede mirar el diff y decir si se cumplió). "Mantén las funciones cortas" no es verificable; "las funciones de handler no superan 40 líneas; la lógica va en `internal/asignacion`" sí.

Sobre secretos: el archivo se versiona y el agente puede citarlo en un PR o un log; nada que no se pegaría en un canal público va ahí (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

**Ejemplo:** "Usa buenas prácticas de concurrencia" no cambia nada. "Toda goroutine que se lance en `internal/asignacion` recibe un `context.Context` y termina cuando se cancela; el test `TestNoGoroutineLeaks` lo verifica" le dice al agente qué hacer y cómo comprobarlo.

**Por qué importa:** las instrucciones vagas no son neutras: ocupan contexto y le dan al modelo la impresión de haber cumplido algo sin cambiar su conducta.

### Tamaño y presupuesto

El archivo compite por la atención del modelo con el código, los resultados de herramientas y la tarea. Dos costos crecen con su tamaño.

**Costo en tokens.** Como viaja en cada llamada, se multiplica por el número de turnos. Supongamos que el `AGENTS.md` del repositorio de ruteo creció a 8.000 tokens por acumulación (cifras hipotéticas):

1. Una sesión típica tiene 40 llamadas al modelo: 8.000 × 40 = 320.000 tokens de entrada solo por las instrucciones.
2. El equipo hace unas 6.600 sesiones al mes (20 personas, 15 sesiones por día, 22 días): 2.100 millones de tokens al mes.
3. A un precio hipotético de USD 3 por millón de tokens de entrada, unos USD 6.300 al mes sin caché. Con [prompt caching](#t/contexto-memoria), si la lectura cacheada cuesta un 10 %, baja a unos USD 630 más las escrituras de caché.

La caché resuelve buena parte del costo, pero no el otro problema.

**Degradación.** Con más reglas, cada una recibe menos atención, y las del medio de un documento largo se cumplen peor. Un experimento hipotético en el repositorio: la regla "no editar migraciones aplicadas" se cumple en 19 de 20 tareas cuando el archivo tiene 1.500 tokens y en 15 de 20 cuando tiene 8.000 y la regla quedó en la línea 240.

Un objetivo razonable para el archivo raíz es de 1.000 a 3.000 tokens (unas 60 a 200 líneas); lo demás, en reglas condicionales o documentos que el agente lee cuando los necesita.

**Instrucción o hook.** Una instrucción es **probabilística**: el modelo la sigue casi siempre, no siempre. Un [hook](#t/hooks-agentes) o una regla de permisos es **determinista**: código que corre en momentos fijos del bucle y bloquea o corrige sin depender del modelo (ver [El arnés de un agente](#t/arnes-agentes)). La regla práctica:

- Si un incumplimiento es tolerable y se detecta en revisión, basta una instrucción.
- Si un incumplimiento rompe algo, expone datos o es irreversible, la regla va en un hook, un permiso o un check de CI, y la instrucción queda como explicación del porqué.
- Si una instrucción se incumple con frecuencia pese a estar bien escrita, es candidata a pasar a hook.

**Ejemplo:** "formatear con `gofmt`" se incumplía en 1 de cada 10 tareas. Se reemplazó por un hook que corre `gofmt` después de cada edición: la línea salió del archivo y el incumplimiento bajó a cero.

**Por qué importa:** usar el archivo de instrucciones como sistema de control da una falsa sensación de seguridad. Orienta; no garantiza.

### Redacción

Las reglas de [Prompt engineering](#t/prompt-engineering) aplican, con algunas particularidades de este tipo de archivo:

- **Imperativo y específico.** "Corre `make test-unit` antes de dar una tarea por terminada", no "sería bueno correr los tests".
- **Con ejemplos** cuando la convención es de formato: un mensaje de commit modelo vale más que tres líneas describiéndolo.
- **El porqué en una cláusula.** "No uses `time.Now()` en `internal/asignacion`; usa `clock.Now()` para que los tests sean deterministas". El porqué ayuda al modelo a generalizar a casos que la regla no nombra.
- **Énfasis con moderación.** Si diez reglas dicen IMPORTANTE, ninguna lo es, y los modelos recientes tienden a sobrerreaccionar a las enfáticas. Reservarlo para una o dos.
- **Estructura con títulos.** Comandos, Arquitectura, Convenciones, Prohibiciones, Definición de terminado. Ayuda al modelo y a las personas que lo mantienen.
- **Sin contradicciones.** "Agrega tests para todo cambio" y "no toques `_test.go` de otros paquetes" chocan cuando el cambio cruza paquetes. Aparecen cuando se suman reglas sin leer las existentes.

**Ejemplo:** "IMPORTANTE: SIEMPRE valida las entradas" llevó al agente a agregar validaciones redundantes en funciones internas ya validadas. Se reemplazó por "Valida las entradas en los handlers HTTP y en los consumidores de Kafka; las funciones internas confían en tipos ya validados".

**Por qué importa:** el modelo interpreta todo lo que lee. Una regla mal redactada no solo falla en su objetivo; puede causar daños colaterales en otros.

### Mantenimiento: dueño, revisión, poda y prueba

Un archivo de instrucciones es código que configura el comportamiento de un sistema; se mantiene como tal:

1. **Revisión en PR.** Cada cambio pasa por revisión, igual que un cambio de configuración. Un archivo `CODEOWNERS` puede exigir la aprobación de quien lo mantiene.
2. **Dueño.** Una persona o un equipo responde por él. Sin dueño, crece por acumulación y nadie se anima a borrar.
3. **Poda periódica.** Cada trimestre, revisar línea por línea: ¿sigue vigente?, ¿el agente lo haría bien sin ella?, ¿pasó a un hook o al linter? Si el comando cambió, actualizarlo; una instrucción desactualizada es peor que ninguna.
4. **Prueba con tareas reales.** Antes de agregar o quitar una regla importante, una mini evaluación (ver [Evaluación de LLMs](#t/evaluacion-llms)): 10 tareas representativas, corridas con y sin la regla, comparando el resultado.

**Ejemplo:** el equipo duda si la sección "Arquitectura" aporta. Corre 10 tareas reales con y sin ella. Con ella: 8 de 10 resueltas sin corrección manual y 3 cruces de capa indebidos evitados; sin ella: 6 de 10 y 2 cambios que importaban `internal/eta` desde handlers. La sección se queda. Otra prueba similar muestra que la lista de 30 reglas de nombres no cambia nada, porque el linter ya las impone: se borra.

**Por qué importa:** sin medición, el archivo solo crece. Con una prueba barata de diez tareas, cada línea tiene que justificar su lugar.

### Memoria del agente e instrucciones del equipo

Varias herramientas tienen además **memoria automática**: el agente guarda notas por su cuenta, normalmente fuera del repositorio, y las relee en sesiones siguientes. Es otra cosa:

| | Memoria del agente | Instrucciones del equipo |
|---|---|---|
| Quién escribe | El agente, a veces a pedido | Personas, por PR |
| Dónde vive | Normalmente fuera del repositorio, por usuario | En el repositorio, versionado |
| Alcance | Una persona o una máquina | Todo el equipo |
| Revisión | Ninguna o mínima | Revisión de código |
| Bueno para | Preferencias personales, descubrimientos de una sesión | Reglas, comandos, decisiones |

El riesgo es que algo importante quede solo en la memoria de una persona. La práctica sana es revisarla de vez en cuando y **promover** al archivo del proyecto lo que vale para todos. Y la memoria puede envenenarse con texto externo, así que nunca se trata como regla del equipo (ver [Contexto y memoria de agentes](#t/contexto-memoria)).

**Ejemplo:** la memoria de un desarrollador acumuló "los tests de integración de ruteo fallan si no hay datos de zonas; correr `make seed-zonas`". Lo descubrió el agente tras un error. Al verlo en una revisión, el desarrollador lo pasa al `AGENTS.md` en la sección Comandos.

**Por qué importa:** el conocimiento que vive en la memoria privada de un agente es tan frágil como el que vive en la cabeza de una sola persona.

### El prompt de sistema de un agente propio

En un agente construido por el equipo, como el asistente de soporte de Rumbo, el equivalente es el **prompt de sistema** que arma el arnés. Todo lo anterior aplica: se carga siempre, cuesta en cada llamada, conviene separarlo en capas (base, reglas del dominio, datos del comercio) y versionarlo con el código. La diferencia es que el equipo controla el ensamblado y puede cargar reglas según la intención detectada, sin depender de lo que permita una herramienta de terceros.

**Ejemplo:** el agente de operaciones arma su prompt de sistema con una base de 1.200 tokens y agrega 400 tokens de reglas de Kafka solo cuando la alerta viene de un consumidor con lag. El equivalente a un glob, pero decidido por código propio.

**Por qué importa:** los mismos criterios de tamaño, redacción y medición sirven para los dos mundos; quien sabe mantener un buen `AGENTS.md` sabe mantener un buen prompt de sistema.

### Ejemplo completo: el AGENTS.md del repositorio de ruteo

El repositorio `ruteo` contiene el servicio de asignación (Go), el cliente del modelo de ETA y los consumidores de eventos de Kafka. Este es su archivo; ocupa unos 900 tokens (cifra aproximada):

```markdown
# Repositorio ruteo

Servicio de asignación de pedidos a transportistas (Go 1.23) y su
integración con el modelo de ETA. Latencia objetivo: p99 < 50 ms.

## Comandos
- Compilar: `make build`
- Tests unitarios: `make test-unit` (rápidos, correr siempre)
- Tests de integración: `make up && make seed-zonas && make test-int`
- Lint y formato: `make lint` (incluye gofmt y golangci-lint)
- Un solo test: `go test ./internal/asignacion -run TestNombre`

## Arquitectura
- `cmd/asignacion`: arranque y configuración. Sin lógica.
- `internal/http`: handlers. Validan entrada y llaman a `internal/asignacion`.
- `internal/asignacion`: reglas de asignación. No importa `internal/http`.
- `internal/eta`: cliente del modelo de ETA con caché y timeout de 15 ms.
- `internal/eventos`: productores y consumidores de Kafka.
- Decisiones: sin ORM (ADR-007); consultas con sqlc en `db/queries`.

## Convenciones
- Errores de dominio: `apperr.Wrap(err, apperr.CodigoX)`. No `fmt.Errorf`
  en `internal/asignacion`.
- Tiempo: `clock.Now()`, nunca `time.Now()`, para tests deterministas.
- Toda goroutine recibe `context.Context` y termina al cancelarse.
- Nombres de tests: `Test<Funcion>_<Escenario>`, tabla de casos.
- Commits en castellano, en imperativo: "Agrega timeout a cliente ETA".

## Prohibido (y por qué)
- No llamar a `internal/eta` desde handlers: rompe el presupuesto de
  50 ms; va siempre por `asignacion.Estimador`.
- No editar migraciones ya aplicadas en `db/migrations/`: Aurora ya las
  corrió en producción. Crear una nueva.
- No registrar nombre, teléfono ni dirección del destinatario en logs:
  usar `logx.Pedido(id)`, que solo registra el ID.
- No agregar dependencias sin anotarlas en `docs/dependencias.md`.

## Antes de dar algo por terminado
1. `make lint` y `make test-unit` en verde.
2. Si el cambio toca `internal/eventos` o `db/`, también `make test-int`.
3. Sin TODO nuevos sin número de ticket.
4. Resume en el PR qué cambió y cómo se verificó.

## Más contexto (leer solo si la tarea lo necesita)
- Modelo de ETA y sus features: `docs/eta.md`
- Esquema de eventos de Kafka: `docs/eventos.md`
```

**Comentario del archivo, sección por sección:**

- **Encabezado:** el dato no deducible más importante, el presupuesto de latencia, que explica varias reglas de abajo.
- **Comandos:** exactos y copiables, con el orden para integración (`seed-zonas` es lo que el agente no adivinaría).
- **Arquitectura:** seis líneas que dicen qué no importa qué, que es lo que el agente rompería. "Sin ORM" lleva su ADR para que no se reabra.
- **Convenciones:** solo las no obvias. No dice "usa camelCase" porque el linter lo impone y el código lo muestra.
- **Prohibido:** cada prohibición tiene su porqué y su alternativa. La de logs es también un hook (un análisis de PII en CI), y la de migraciones, una regla de permisos; aquí quedan como explicación.
- **Terminado:** criterios verificables mirando la salida y el diff.
- **Más contexto:** punteros en vez de contenido. El agente lee `docs/eta.md` solo si la tarea toca el modelo.

### Un archivo malo y su versión corregida

Este archivo existió en otro repositorio de Rumbo:

```markdown
# Instrucciones
Eres un ingeniero senior experto en Go. Escribe código limpio, mantenible
y escalable siguiendo las mejores prácticas. IMPORTANTE: SIEMPRE escribe
tests. IMPORTANTE: NUNCA rompas nada. Este proyecto usa Go y PostgreSQL.
La carpeta internal tiene el código interno. Usa nombres descriptivos.
Para conectarte a staging usa DB_PASSWORD=rumbo-stg-2026.
Ten cuidado con el rendimiento. Documenta todo.
```

Problemas: el rol y los adjetivos no cambian conducta; "escribe tests" no dice cuáles ni cómo correrlos; "no rompas nada" no es verificable; "usa Go y PostgreSQL" y "internal tiene el código interno" se deducen del repositorio; hay un secreto versionado; "cuidado con el rendimiento" y "documenta todo" son vagos. Versión corregida:

```markdown
# Repositorio notificaciones

## Comandos
- Tests: `make test` (unitarios) · `make test-int` (requiere `make up`)
- Lint: `make lint`

## Reglas
- Todo cambio en `internal/plantillas` incluye un test de tabla en el
  mismo paquete.
- Los envíos a destinatarios pasan por `cola.Encolar`; no llamar al
  proveedor de SMS directamente (aplica límites por comercio).
- Credenciales de staging: se leen de `RUMBO_STG_*` vía `make env-stg`;
  nunca se escriben en archivos.

## Terminado
- `make lint` y `make test` en verde; si cambió el formato de un mensaje,
  agregar un caso a `testdata/plantillas_golden/`.
```

Es más corto, cada línea es accionable y verificable, y el secreto se revocó (estar en el historial de git ya lo comprometió).

## Casos prácticos

### Un archivo que creció hasta 9.000 tokens

**Situación:** el `AGENTS.md` del repositorio de ruteo pasó de 120 a 520 líneas en un año, una regla nueva por incidente. Las personas se quejan de que el agente "ignora reglas" y el tablero de costos muestra que las instrucciones representan el 18 % de los tokens de entrada (cifras hipotéticas).
**Qué se hace:** se asigna un dueño y se hace una poda en tres pasos. Primero, se borran las líneas que el linter o el código ya resuelven (unas 150). Segundo, las reglas de migraciones, Kafka y el modelo de ETA pasan a reglas condicionales por ruta o a documentos referenciados. Tercero, las cuatro reglas que más se incumplían y que eran críticas pasan a hooks y checks de CI. El archivo queda en 140 líneas, y una mini evaluación de 10 tareas muestra igual o mejor resultado que con el archivo largo.

### Cinco herramientas, cinco archivos desincronizados

**Situación:** el repositorio tiene `CLAUDE.md`, `.cursorrules`, `.github/copilot-instructions.md` y `AGENTS.md`, escritos en momentos distintos. El de Copilot todavía indica `go test ./...`, que hoy falla sin la base levantada.
**Qué se hace:** se declara `AGENTS.md` como fuente única. `CLAUDE.md` pasa a importarlo con `@AGENTS.md` y conserva solo lo específico de Claude Code; el archivo de Copilot se elimina porque la herramienta ya lee `AGENTS.md`, y el `.cursorrules` heredado se borra en favor de dos reglas `.mdc` con globs. Un check de CI falla si alguien vuelve a crear un archivo de instrucciones con contenido duplicado. Antes de borrar, se verifica en la documentación vigente de cada herramienta que efectivamente lee `AGENTS.md`.

### Una regla crítica que el agente cumple «casi siempre»

**Situación:** el archivo dice "no registrar el teléfono del destinatario en logs", y aun así un PR de un agente trae `log.Info("reintento", "tel", pedido.Telefono)`. El revisor lo detectó de casualidad: la regla se venía cumpliendo y nadie miraba.
**Qué se hace:** se acepta que una instrucción es probabilística y que esta regla no tolera fallas. Se agrega un hook posterior a la edición que busca campos de PII en llamadas de log y devuelve el error al agente, y un check en CI con la misma regla para los cambios hechos por personas. La línea queda en el archivo, ahora con la alternativa explícita (`logx.Pedido(id)`), porque explicar el porqué reduce los intentos fallidos que el hook tiene que frenar.

### Llevar el aprendizaje de un incidente al archivo, sin inflarlo

**Situación:** tras un incidente, un agente agregó un índice sin `CONCURRENTLY` en una tabla de 40 millones de filas y la migración bloqueó escrituras durante seis minutos. En el postmortem alguien propone agregar al `AGENTS.md` una sección de diez reglas sobre migraciones seguras.
**Qué se hace:** se separa en dos. La regla que evitó el incidente se vuelve determinista: un linter de migraciones en CI rechaza `CREATE INDEX` sin `CONCURRENTLY`. Las convenciones de migraciones se escriben en una regla condicional que solo se carga al tocar `db/migrations/**`. Al archivo raíz no se le agrega nada. Se corre una mini evaluación con cinco tareas de migración para confirmar que la regla condicional se activa y se respeta.

## Errores comunes

- **Usar el archivo como wiki.** Cuesta tokens en cada turno y diluye lo importante. Dejar lo que el agente no deduce y apuntar al resto.
- **Escribir reglas vagas o enfáticas.** "Código limpio" o diez IMPORTANTE no cambian la conducta o la cambian de más. Cada línea debe ser accionable, verificable y con su porqué.
- **Confiar en instrucciones para lo crítico.** Lo que no admite fallas va en hooks, permisos o CI; el archivo explica la razón.
- **Mantener varios archivos con el mismo contenido.** Se desincronizan. Una fuente única (por ejemplo, `AGENTS.md`) e importaciones o punteros mínimos para cada herramienta.
- **Poner secretos o datos sensibles.** El archivo se versiona y el agente puede repetirlo; si un secreto llegó al historial, hay que revocarlo, no solo borrarlo.
- **No tener dueño ni poda.** El archivo crece con cada incidente y nadie borra. Asignar responsable, revisar en PR y probar con tareas reales antes de agregar o quitar reglas importantes.

## Para discutir en equipo

- Si hoy midiéramos cuántos tokens de nuestros archivos de instrucciones viajan en cada sesión, ¿qué porcentaje de esas líneas sobreviviría a la pregunta "¿el agente se equivocaría sin esto?"?
- ¿Qué reglas de nuestros repositorios se cumplen hoy solo porque el agente las sigue y deberían pasar a un hook, a un permiso o a CI?
- ¿Adoptamos `AGENTS.md` como fuente única en todos los repositorios, o hay herramientas o equipos para los que eso no funciona?
- ¿Quién es dueño del archivo de instrucciones de cada repositorio, y cada cuánto lo revisamos?
- ¿Qué conocimiento útil está hoy solo en la memoria privada del agente de alguien y debería promoverse al archivo del proyecto?
