---
slug: hooks-agentes
titulo: Hooks: reglas que el agente no puede saltarse
resumen: Qué son los hooks de un agente, en qué eventos se disparan, cómo deciden y cómo diseñarlos para que las reglas críticas se cumplan siempre.
lectura: 18
---

## La idea central

Un agente recibe instrucciones de muchas formas: el prompt de sistema, el archivo de reglas del repositorio, lo que la persona escribe en el chat. Todas tienen algo en común: el modelo las **interpreta**. Casi siempre las respeta, pero «casi siempre» no alcanza para reglas como «no leas las credenciales» o «no termines con los tests en rojo». Un **hook** es la otra mitad del sistema: código o un comando que el arnés ejecuta de forma **determinista** en un momento fijo del ciclo de vida del agente (al iniciar la sesión, antes de usar una herramienta, después de usarla, al intentar terminar). El modelo no decide si el hook corre; solo ve lo que el hook devuelve.

Es como una obra en construcción: las instrucciones son la charla de seguridad del lunes, que casi todos cumplen; los hooks son el molinete que no deja pasar a nadie sin casco. En [El arnés de un agente](#t/arnes-agentes) los hooks aparecen como la pieza L del arnés, en una sección breve; este tema los desarrolla en detalle: eventos, contrato de entrada y salida, usos, riesgos y un ejemplo completo en Rumbo. El mapa de todas las piezas con las que se configura un agente (instrucciones, comandos, skills, hooks) está en [Artefactos de un agente](#t/artefactos-agentes).

## Conceptos

### Instrucción frente a hook: casi siempre contra siempre

Una instrucción en el prompt o en el archivo de reglas del repositorio (ver [Instrucciones y reglas](#t/instrucciones-reglas)) es texto que el modelo pondera junto con todo lo demás que tiene en el contexto. Si la sesión es larga, si el contexto se compactó, si un archivo leído dice lo contrario o si la tarea parece justificar una excepción, la regla puede perder.

Un hook funciona distinto en tres aspectos:

1. **Lo dispara el arnés, no el modelo.** El evento ocurre (por ejemplo, «el modelo pidió editar un archivo») y el hook corre, sin importar lo que el modelo «piense».
2. **Su decisión es código.** Una expresión regular, una consulta, un test: el mismo dato de entrada da siempre la misma salida.
3. **Puede imponer el resultado.** Bloquear una acción, rechazar un cierre o modificar argumentos, en lugar de sugerirlo.

**Ejemplo:** el equipo de ruteo tiene en su archivo de reglas «nunca leer `.env`». Con mediciones internas (hipotéticas), el agente la respeta en el 97 % de las ejecuciones donde la tentación aparece. El agente corre unas 400 ejecuciones diarias entre todo el equipo: 400 × 0,03 = **12 violaciones por día**. Con un hook que bloquea cualquier lectura de `.env`, la cifra es cero, salvo que el propio hook tenga un error.

**Por qué importa:** para cada regla hay que preguntar «¿qué pasa el día que no se cumpla?». Si la respuesta es «un secreto en un log», va en un hook; si es «un comentario con otro estilo», alcanza con la instrucción.

| Mecanismo | Quién decide | Garantía | Bueno para |
|---|---|---|---|
| Instrucción o regla escrita | El modelo, al leerla | Alta, no total | Estilo, convenciones, preferencias |
| Comando o skill | El modelo, guiado por un procedimiento | Mejora la consistencia | Flujos repetibles (ver [Comandos](#t/comandos-agentes) y [Skills](#t/skills-agentes)) |
| Hook | Código del arnés | Determinista dentro de su alcance | Prohibiciones, verificaciones obligatorias, auditoría |
| Permisos y sandbox | Política y entorno | Determinista, independiente del agente | Límite duro de lo que se puede tocar |

### Eventos del ciclo de vida

Un hook se asocia a un **evento**: un punto del bucle del agente donde el arnés se detiene y pregunta «¿alguien quiere opinar?». Los eventos típicos, en el orden en que aparecen en una sesión, son:

1. **Inicio de sesión:** antes del primer turno; sirve para inyectar contexto.
2. **Envío del prompt de la persona:** permite agregar contexto o rechazar el mensaje.
3. **Antes de usar una herramienta:** pedida pero no ejecutada; para bloquear, pedir confirmación o corregir.
4. **Después de usar una herramienta:** para formatear, correr el linter o auditar.
5. **Notificación o pedido de permiso:** el agente necesita a la persona.
6. **Fin del turno o parada:** se verifica una condición de cierre y, si falla, el agente sigue.
7. **Fin de un subagente:** igual que el anterior, para un agente delegado (ver [Subagentes](#t/subagentes)).
8. **Antes de compactar el contexto:** guardar una copia o indicar qué preservar.
9. **Fin de sesión:** limpieza y métricas finales.

Como ejemplo actual, Claude Code los llama `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Notification`, `Stop`, `SubagentStop`, `PreCompact` y `SessionEnd`. Otras herramientas de agentes tienen equivalentes con otros nombres y no siempre el conjunto completo; los nombres y campos cambian entre versiones, así que conviene revisar la documentación de la versión que se usa.

```arbol
titulo: Eventos donde corre un hook
Sesión del agente
- Inicio y entrada
-- Inicio de sesión
-- Envío del prompt
- Cada herramienta
-- Antes de usarla
-- Después de usarla
-- Pedido de permiso
- Cierre
-- Fin del turno o parada
-- Fin de un subagente
-- Antes de compactar
-- Fin de sesión
```

**Ejemplo:** en una sesión de 40 minutos el agente de código de Rumbo hace 1 inicio, recibe 5 prompts, usa 150 herramientas (de las cuales 30 son ediciones) y termina 5 turnos. Un hook «antes de herramienta» sin filtro corre 150 veces; uno «después de editar» corre 30; uno de parada, 5.

**Por qué importa:** el evento define cuánto cuesta el hook y qué puede hacer: bloquear «después de usar» llega tarde.

### El contrato: qué recibe y qué devuelve un hook

Un hook de tipo comando es un programa cualquiera (script de shell, Python, un binario en Go) con un contrato simple:

1. **Entrada:** el arnés le pasa un JSON por entrada estándar con el nombre del evento, la sesión, el directorio de trabajo y, según el evento, la herramienta y sus argumentos (y el resultado, si es posterior).
2. **Decisión:** el script hace lo suyo: compara rutas, corre un formateador, consulta un servicio.
3. **Salida:** responde con su **código de salida** y, opcionalmente, con un JSON por salida estándar.

En Claude Code, la entrada de un evento `PreToolUse` se ve así:

```json
{
  "session_id": "a1b2c3",
  "transcript_path": "/home/ana/.claude/projects/ruteo/a1b2c3.jsonl",
  "cwd": "/home/ana/ruteo",
  "permission_mode": "default",
  "hook_event_name": "PreToolUse",
  "tool_name": "Read",
  "tool_input": { "file_path": "/home/ana/ruteo/.env" }
}
```

Las respuestas posibles, de la más simple a la más rica:

| Respuesta | Cómo se expresa (Claude Code) | Efecto |
|---|---|---|
| Permitir sin comentarios | Código de salida 0 | La acción sigue su curso normal |
| Bloquear con motivo | Código de salida 2 y el motivo por error estándar | La acción no se ejecuta; el motivo vuelve al modelo como observación |
| Error no bloqueante | Otro código distinto de 0 y 2 | Se registra el error y la acción sigue |
| Decidir con detalle | JSON con `permissionDecision`: `allow`, `deny` o `ask`, y `permissionDecisionReason` | Permite, bloquea o pide confirmación a la persona |
| Modificar argumentos | JSON con `updatedInput` | La herramienta corre con la entrada corregida |
| Agregar contexto | JSON con `additionalContext` (o texto por salida estándar en inicio de sesión y envío de prompt) | El modelo recibe información extra |
| Rechazar el cierre | En `Stop`, JSON con `"decision": "block"` y `reason` | El modelo no termina y recibe el motivo |

Lo más importante es la segunda fila: **el motivo vuelve al modelo**. Un bloqueo bien escrito es una señal de corrección: «no puedes leer `.env`; las variables están en `.env.example`» lleva al agente por el camino correcto en el turno siguiente.

**Ejemplo:** la configuración se declara en el archivo de ajustes del proyecto (`.claude/settings.json`), con un `matcher` que filtra por nombre de herramienta:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read|Edit|Write|Bash",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/rutas_protegidas.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```

Y el script, corto y sin dependencias:

```python
#!/usr/bin/env python3
import json, re, sys

evento = json.load(sys.stdin)
entrada = evento.get("tool_input", {})
objetivo = entrada.get("file_path") or entrada.get("command") or ""

PROTEGIDAS = {
    r"(^|[\s/'\"])\.env(?!\.example)": "las variables están descritas en .env.example",
    r"(^|[\s/'\"])datos/clientes/": "usar los fixtures anonimizados de testdata/",
}

for patron, alternativa in PROTEGIDAS.items():
    if re.search(patron, objetivo):
        print(f"Bloqueado por hook: '{objetivo}' toca una ruta protegida; {alternativa}.",
              file=sys.stderr)
        sys.exit(2)   # 2 = bloquear; el texto de stderr vuelve al modelo

sys.exit(0)           # 0 = permitir
```

**Por qué importa:** cualquiera del equipo puede escribir un hook en su lenguaje, probarlo con un JSON de ejemplo y revisarlo en un PR.

### Hooks previos a la herramienta: la última barrera

El evento «antes de usar una herramienta» es el más poderoso porque llega **después** de que el modelo decidió y **antes** de que algo ocurra. Ahí caben cuatro tipos de decisión:

- **Bloquear:** comandos peligrosos (`rm -rf`, `git push --force` a `main`, `terraform apply`), escritura en rutas protegidas, lectura de secretos.
- **Pedir confirmación:** acciones legítimas pero sensibles, como ejecutar una migración en la base local compartida.
- **Corregir:** agregar `--dry-run` a un comando, forzar un timeout, reescribir una ruta absoluta a una relativa.
- **Permitir explícitamente:** saltar el pedido de permiso para algo que el equipo considera siempre seguro, como `go test ./...`.

**Ejemplo:** el hook de comandos de plataforma revisa cada `Bash`. `kubectl delete` fuera del clúster local recibe `deny` con el motivo «En clústeres compartidos no se borra desde el agente; proponer el manifiesto en un PR»; `kubectl apply` en el clúster local recibe `ask`.

**Por qué importa:** es el único punto donde una regla se aplica antes del daño. Todo lo demás (auditoría, alertas) llega después.

### Hooks posteriores a la herramienta: calidad automática

Después de la herramienta, el hook ya no puede impedirla, pero puede **arreglar** (formatear), **informar** al modelo (errores del linter) y **registrar** (auditoría).

**Ejemplo:** tras cada edición de un archivo `.go`, un hook corre `gofmt -w` sobre ese archivo y `go vet` sobre su paquete. El formateo tarda unos 80 ms y el análisis unos 600 ms (hipotético). Si `go vet` encuentra un problema, el hook devuelve el error como contexto: el modelo lo ve en el turno siguiente y lo corrige sin que nadie se lo pida. Con 30 ediciones, suma unos 20 segundos por sesión.

**Por qué importa:** «formatea siempre» es una instrucción que el modelo olvida en sesiones largas; un hook posterior la convierte en una propiedad del entorno.

### Hooks de parada: no aceptar un «listo» falso

El hook de parada corre cuando el modelo da su respuesta final. Si una condición de cierre no se cumple, puede rechazar la parada y devolverle al modelo el motivo, que funciona como un nuevo mensaje: el agente sigue trabajando.

El riesgo obvio es el **bucle**: si los tests fallan por algo que el agente no puede arreglar (un servicio externo caído, un test inestable), el hook rechaza la parada, el agente intenta, falla, vuelve a intentar parar, y así sin fin. Por eso Claude Code pasa en la entrada del evento `Stop` el campo `stop_hook_active`, que indica que el agente ya está continuando por un hook de parada anterior. Un hook bien diseñado lo consulta, o lleva su propio contador, y deja terminar después de N intentos con un aviso claro.

**Ejemplo:**

```bash
#!/usr/bin/env bash
entrada=$(cat)
if [ "$(echo "$entrada" | jq -r '.stop_hook_active')" = "true" ]; then
  exit 0   # ya se pidió seguir una vez: dejar terminar y no entrar en bucle
fi
if ! salida=$(go test ./... 2>&1 | tail -n 30); then
  jq -n --arg r "Los tests fallan. Corregir o explicar por qué no aplica:\n$salida" \
     '{decision: "block", reason: $r}'
fi
exit 0
```

Si los tests fallan, el agente sigue con las últimas 30 líneas como guía; si ya se le pidió seguir una vez, termina igual.

**Por qué importa:** el hook de parada transforma «decir que terminó» en «terminar de verdad», que es la diferencia entre un agente que ahorra trabajo y uno que lo traslada al revisor.

### Inyectar contexto en el momento justo

Los eventos de inicio de sesión y de envío de prompt permiten **agregar información** que el modelo no tendría de otra forma, o que sería caro mantener en el archivo de reglas porque cambia todo el tiempo.

**Ejemplo:** al iniciar sesión en el repositorio de ruteo, un hook imprime la rama actual, los últimos tres commits de `main` y si hay un incidente abierto que congela despliegues. Son unos 300 tokens, y con congelamiento el agente no propone abrir un PR a `main`. Otro hook en el envío de prompt detecta patrones de tokens de acceso en lo que la persona escribe y bloquea el mensaje antes de que llegue al modelo, con el aviso «Parece que pegaste un token; quítalo y usa la variable de entorno».

**Por qué importa:** el contexto que cambia por sesión no debería vivir en un archivo estático; el hook lo trae fresco y solo cuando corresponde.

### Auditoría, notificaciones, costo y trazas

Hay hooks que no deciden nada: **observan**. Escriben cada acción en un log de auditoría, avisan cuando el agente espera aprobación o suman tokens y duración por sesión.

Estos hooks son el puente natural con la observabilidad. En lugar de escribir texto suelto, pueden emitir un span por herramienta o eventos dentro de la traza de la sesión, con los mismos atributos y reglas de redacción que el resto del sistema (ver [OpenTelemetry](#t/opentelemetry)).

**Ejemplo:** el hook de auditoría de Rumbo agrega una línea JSON por herramienta a `~/.rumbo/auditoria-agente.jsonl`: fecha, `session_id`, herramienta, primeros 200 caracteres del argumento con secretos enmascarados y decisión. Con 400 sesiones diarias de 150 herramientas cada una, son unas 60.000 líneas por día, del orden de 20 MB (hipotético).

**Por qué importa:** «¿qué hizo el agente y quién lo dejó?» se responde con datos, no con memoria.

### Riesgos: código con los permisos de la persona

Un hook no corre en un sandbox aparte: en las herramientas de programación de línea de comandos, corre **con los permisos de la persona que lanzó el agente**, en su máquina, con acceso a sus archivos, su red y sus credenciales. Eso tiene consecuencias:

- **Un hook es código ejecutable que llega con el repositorio.** Si alguien agrega un hook malicioso a `.claude/settings.json` en un PR, se ejecuta en la máquina de cada persona que abra el agente en esa rama. Hay que revisarlos como se revisa un script de CI.
- **Hooks de terceros.** Instalar un paquete de hooks o un plugin de la comunidad equivale a instalar una dependencia que corre con todos los permisos. Aplican las reglas de [Cadena de suministro](#t/cadena-suministro): fijar versión, leer el código, preferir lo mínimo.
- **Un hook no reemplaza al sandbox.** Un filtro por texto se puede eludir: `cat ./.e*` no contiene «.env» literal. El hook reduce errores honestos y deja rastro; el límite duro sigue siendo el sistema de archivos y la red del entorno (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

**Ejemplo:** un PR externo al repositorio de herramientas internas agrega un hook de inicio de sesión que «descarga la última configuración del linter». En la revisión se ve que hace `curl` a un dominio desconocido y ejecuta la respuesta. Se rechaza, y el equipo agrega una regla de CODEOWNERS: cualquier cambio en `.claude/` requiere revisión de plataforma.

**Por qué importa:** los hooks corren solos, en todas las máquinas y en cada sesión: una superficie de ataque muy bien ubicada. Lo mismo vale para los paquetes de hooks de la comunidad, que pueden mandar cada prompt a un servicio externo «para estadísticas».

### Latencia: el costo que se multiplica

Los hooks corren de forma sincrónica en el bucle: mientras un hook previo no responde, la herramienta no se ejecuta. Su costo se multiplica por la cantidad de eventos.

**Ejemplo:** un hook previo que consulta un servicio interno de políticas tarda 2 segundos. En una sesión con 150 llamadas a herramientas, eso suma 150 × 2 = **300 segundos, 5 minutos** de espera pura. Con un `matcher` que lo limita a `Bash` (40 llamadas) y una caché local de la política (20 ms por consulta), baja a menos de un segundo en toda la sesión.

**Por qué importa:** un hook lento termina desactivado, y entonces protege menos que una instrucción.

### Fallar abierto o fallar cerrado

¿Qué pasa si el hook se rompe (error de sintaxis, dependencia faltante, timeout)? Hay dos filosofías:

- **Fallar abierto:** si el hook falla, la acción sigue. Es lo que ocurre por defecto en Claude Code con un código de salida distinto de 0 y de 2, y con un timeout. Prioriza no trabar el trabajo.
- **Fallar cerrado:** si el hook falla, la acción se bloquea. Prioriza la seguridad.

La regla práctica: los hooks de calidad (formato, lint) fallan abiertos; los de protección (secretos, rutas, comandos destructivos) fallan cerrados. Para que un hook de protección falle cerrado, el propio script tiene que capturar sus errores y salir con 2 (o devolver `deny`), en lugar de dejar que una excepción termine con código 1.

**Ejemplo:** el hook de rutas protegidas de Rumbo envuelve todo en un `try`; ante cualquier excepción escribe «Hook de rutas protegidas con error interno; acción bloqueada por precaución» y sale con 2. El hook de formato, en cambio, si no encuentra `gofmt`, avisa y sale con 1: la edición queda sin formatear, pero el trabajo sigue.

**Por qué importa:** un hook de seguridad que falla abierto en silencio da una falsa sensación de protección: el día que se rompe, nadie se entera.

### Hooks en un agente propio: middleware alrededor de las herramientas

Los hooks no son exclusivos de los agentes de programación. En un arnés propio, construido sobre un SDK, el mismo concepto aparece como **middleware** o **callbacks** que envuelven la ejecución de herramientas y las llamadas al modelo. Varios frameworks de agentes ofrecen puntos de extensión con nombres como «antes de la herramienta» o «después del modelo»; si no los tienen, se escriben en el bucle, como en el esqueleto de [El arnés de un agente](#t/arnes-agentes).

**Ejemplo:** el asistente de soporte de Rumbo registra tres funciones en su arnés:

```python
@hook("antes_herramienta")
def solo_pedidos_propios(llamada, sesion):
    if llamada.nombre == "buscar_pedido" and llamada.args.get("telefono") != sesion.telefono:
        return Bloquear("Solo se consultan pedidos del destinatario autenticado.")

@hook("despues_herramienta")
def redactar_pii(llamada, resultado, sesion):
    return quitar_campos(resultado, ["telefono_transportista", "documento"])

@hook("despues_herramienta")
def auditar(llamada, resultado, sesion):
    traza_actual().add_event("herramienta", {"nombre": llamada.nombre, "sesion": sesion.id})
```

Es el mismo contrato que en Claude Code (evento, entrada, decisión), solo que en el mismo proceso y sin JSON por entrada estándar.

**Por qué importa:** ante un diseño nuevo, preguntar «¿qué corre antes y después de cada herramienta?» muestra rápido si las reglas críticas viven en código o en el prompt.

### Buenas prácticas de diseño

Un hook es código de producción del entorno de desarrollo:

1. **Rápido:** apuntar a menos de 100 ms en hooks previos; filtrar con `matcher` para no correr donde no hace falta.
2. **Idempotente:** si corre dos veces sobre lo mismo, el resultado es igual. Formatear un archivo ya formateado no cambia nada; agregar una línea de auditoría duplicada sí, así que se incluye un identificador de llamada.
3. **Con motivo accionable:** cada bloqueo dice qué se bloqueó, por qué y qué hacer en su lugar.
4. **Con registro:** cada decisión (incluidos los permisos) queda en un log o en la traza.
5. **Probado:** se le pasan JSON de ejemplo y se verifica el código de salida, igual que con cualquier función (ver [Testing y dobles de prueba](#t/testing-dobles)).
6. **Versionado y revisado:** vive en el repositorio, con dueño y revisión obligatoria.

**Ejemplo:** el repositorio de ruteo tiene 14 casos de prueba para su hook de rutas (`.env.local`, `.env.example` que debe permitirse, `cat datos/clientes/*`, rutas absolutas) que corren en CI en menos de 2 segundos.

**Por qué importa:** un hook sin tests se rompe en silencio con el primer cambio de formato de la entrada.

## Casos prácticos

### El repositorio de ruteo con cuatro hooks

**Situación:** el equipo de ruteo usa un agente de programación sobre un repositorio en Go que, por historia, tiene un `.env` con credenciales del entorno de staging y una carpeta `datos/clientes/` con exportaciones de direcciones reales usadas para reproducir bugs. Hubo dos incidentes de credenciales copiadas en logs de sesiones, y los PRs del agente llegan a veces sin formatear o con tests rotos.
**Qué se hace:** se configuran cuatro hooks en `.claude/settings.json`, revisados por plataforma:

| Evento | Matcher | Qué hace | Si falla |
|---|---|---|---|
| `PreToolUse` | Read, Edit, Write y Bash | Bloquea `.env` y `datos/clientes/` | Cerrado |
| `PostToolUse` | Edit y Write | `gofmt -w` y `go vet` del paquete | Abierto |
| `Stop` | (todos) | `go test ./...`; rechaza el cierre una vez si fallan | Abierto |
| `PostToolUse` | (todas) | Agrega una línea a la auditoría | Abierto, con alerta |

Recorrido de una sesión en la que Ana pide «arregla el bug de ventanas horarias que reportó el comercio 4471»:

1. **Inicio:** el agente lee `README` y `internal/ventanas/`. El hook de rutas permite todo; la auditoría registra cada lectura.
2. **El agente busca datos reales:** decide reproducir el bug y pide `Read` de `datos/clientes/comercio-4471.csv`. El hook previo responde con código 2: «Bloqueado por hook: 'datos/clientes/comercio-4471.csv' toca una ruta protegida; usar los fixtures anonimizados de testdata/».
3. **El agente se corrige:** en el turno siguiente lista `testdata/`, encuentra `ventanas_superpuestas.json` y escribe un test que reproduce el bug con esos datos.
4. **Edición:** modifica `ventanas.go`. El hook posterior formatea el archivo y `go vet` informa una variable sin usar; el modelo la quita en la edición siguiente.
5. **Intento de cerrar:** el agente responde «Listo, bug corregido». El hook de parada corre los tests: falla `TestVentanaCruzaMedianoche`. Rechaza el cierre con las últimas líneas de la salida.
6. **Segundo intento:** el agente corrige el caso de medianoche, los tests pasan y el hook de parada deja terminar.
7. **Resultado:** el PR llega formateado, con un test nuevo y en verde. La auditoría muestra 47 herramientas, 1 bloqueo y 1 cierre rechazado. Los hooks sumaron unos 35 segundos a una sesión de 18 minutos (hipotético).

### Un hook de parada que no dejaba terminar

**Situación:** el agente del equipo de pronóstico de demanda quedó una noche 2 horas trabajando en una tarea simple. El hook de parada exigía que pasaran los tests de integración, y uno dependía de un bucket de S3 de staging que estaba caído. Cada intento de terminar se rechazaba; el agente probaba cambios cada vez más extraños para «arreglar» el test.
**Qué se hace:** se agregó al hook la consulta de `stop_hook_active` y un contador por sesión: rechaza el cierre como máximo dos veces y luego deja terminar con el aviso «Tests de integración fallando; ver salida». Además, los tests que dependen de servicios externos se separaron de la verificación del hook, que ahora corre solo los unitarios.

### El hook de auditoría que agregaba 4 minutos

**Situación:** seguridad pidió auditoría centralizada de las acciones de los agentes. La primera versión del hook enviaba cada evento por HTTP al sistema de logs y esperaba la confirmación: unos 1,5 segundos por llamada a herramienta. En sesiones de 160 herramientas sumaba 4 minutos, y la gente empezó a desactivarlo localmente.
**Qué se hace:** el hook pasó a escribir en un archivo local (5 ms) y un proceso aparte envía los lotes cada minuto. Un hook de inicio de sesión verifica que la auditoría esté activa y avisa si no lo está.

### Hooks del asistente de soporte en producción

**Situación:** en una revisión de diseño del asistente de soporte, alguien propone agregar al prompt de sistema «nunca muestres el teléfono del transportista» después de que un destinatario lo recibió en una respuesta.
**Qué se hace:** se rechaza la solución por prompt como única defensa. El arnés propio ya tiene middleware posterior a herramientas: se agrega `redactar_pii`, que quita el campo antes de que el resultado llegue al modelo. Si el modelo nunca ve el dato, no puede filtrarlo. La instrucción en el prompt queda como capa adicional y el caso se suma a la suite de evaluación con 20 conversaciones que intentan obtener el teléfono.

## Errores comunes

- **Dejar las reglas críticas solo en el prompt o en el archivo de reglas.** Si la consecuencia de no cumplirla es grave, va en un hook o en la política de permisos; la instrucción queda como explicación.
- **Bloquear sin motivo útil.** «Acción denegada» hace que el modelo reintente variantes; «denegado; usar `testdata/` en su lugar» lo lleva al camino correcto en un turno.
- **Hooks de protección que fallan abiertos sin que nadie lo sepa.** Capturar los errores internos y bloquear, o al menos alertar, en los hooks de seguridad.
- **Hooks de parada sin salida.** Consultar `stop_hook_active` o llevar un contador, y separar las verificaciones que dependen de servicios externos.
- **Ignorar la latencia.** Medir cuánto suma cada hook por sesión, filtrar con `matcher` y mover lo lento a procesos asíncronos.
- **Tratar los hooks como configuración inofensiva.** Son código que corre con los permisos de cada persona: revisión obligatoria, dueño definido y nada de terceros sin leer.

## Para discutir en equipo

- ¿Qué reglas de nuestros archivos de instrucciones tienen consecuencias graves si fallan una vez de cada treinta y deberían pasar a un hook?
- ¿Cuáles de nuestros hooks deberían fallar cerrados y cuáles abiertos? ¿Nos enteraríamos hoy si uno dejara de funcionar?
- ¿Cuánto tiempo suman los hooks a una sesión típica, y cuál es el máximo aceptable antes de que la gente los desactive?
- ¿Quién revisa los cambios en la carpeta de configuración del agente y qué pasa si un PR externo agrega un hook?
- En el asistente de soporte y el agente de operaciones, ¿qué middleware antes y después de herramientas falta para que las reglas sobre datos personales no dependan del modelo?
