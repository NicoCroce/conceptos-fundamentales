---
slug: http
titulo: HTTP de punta a punta
resumen: Qué ocurre entre el navegador y la API del asistente: DNS, TLS, versiones de HTTP, códigos, caché, CORS y streaming de respuestas de LLMs.
lectura: 16
---

## La idea central

Cuando un comercio escribe en el panel de Rumbo "¿por qué el pedido 4812 sigue sin retirar?", la pregunta no viaja directo al agente. Primero el navegador averigua a qué dirección IP corresponde `api.rumbo.app`, abre una conexión, negocia cifrado, envía una solicitud HTTP que puede pasar por un CDN, un balanceador y un API gateway, y recién entonces el backend arma el contexto y llama al modelo. Después la respuesta recorre el mismo camino al revés, de a pedacitos si se transmite en streaming.

Cada tramo tiene su costo en idas y vueltas de red y sus formas de fallar. Entenderlas permite contestar preguntas frecuentes en las revisiones de diseño: por qué la primera consulta tarda el triple que las siguientes, por qué el texto del asistente llega todo junto al final o por qué el navegador bloquea una llamada que con `curl` funciona.

## Conceptos

### DNS: del nombre a la dirección

Para conectarse, el navegador necesita la dirección IP de `api.rumbo.app`. La busca en una cadena de cachés: la del navegador, la del sistema operativo y la del **resolver** (el servidor DNS de la red). Si nadie la tiene, el resolver consulta a los servidores raíz, luego a los de `.app` y por último al servidor **autoritativo** de `rumbo.app`.

Los registros más comunes son `A` (nombre a IPv4), `AAAA` (nombre a IPv6) y `CNAME` (un nombre que apunta a otro nombre, por ejemplo `api.rumbo.app` apuntando al nombre del CDN). Cada respuesta lleva un **TTL** (*time to live*): los segundos durante los cuales las cachés pueden reutilizarla sin preguntar de nuevo.

**Ejemplo:** con TTL de 300 segundos, una vez que el resolver del comercio aprendió la IP, durante cinco minutos la resolución cuesta cerca de 0 ms. Sin caché, la cadena completa puede costar entre 20 y 150 ms. El reverso: si Rumbo cambia la IP, algunos clientes seguirán yendo a la vieja hasta que venza el TTL.

**Por qué importa:** antes de una migración se baja el TTL (por ejemplo a 60 segundos) con un día de anticipación, para que el cambio se propague rápido y un rollback también.

### TCP y TLS: el precio de abrir una conexión

Con la IP en mano, el navegador abre una conexión **TCP**: envía un SYN, recibe un SYN-ACK y ya puede enviar datos. Eso cuesta una ida y vuelta completa (un **RTT**, *round-trip time*). Después viene **TLS**, que cifra la conexión y prueba la identidad del servidor: el servidor presenta un **certificado** firmado por una autoridad en la que el navegador confía, que dice "esta clave pública pertenece a `api.rumbo.app`". Si el nombre no coincide o el certificado venció, el navegador corta.

TLS 1.2 necesitaba dos RTT para el handshake. **TLS 1.3** lo reduce a uno, elimina algoritmos débiles y usa siempre claves efímeras (robar la clave del servidor más adelante no permite descifrar tráfico grabado). Además permite **0-RTT** al reanudar una sesión: el cliente envía datos junto con el primer mensaje, a cambio de que esos datos podrían ser reenviados por un atacante (*replay*), así que solo se usa para solicitudes seguras como un GET.

**Ejemplo:** el comercio está a 80 ms de RTT del API. Una primera consulta con conexión nueva:

| Paso | Costo con TLS 1.3 | Costo con TLS 1.2 |
|---|---|---|
| DNS (sin caché) | ~40 ms | ~40 ms |
| Handshake TCP | 80 ms | 80 ms |
| Handshake TLS | 80 ms | 160 ms |
| Solicitud y primer byte de respuesta | 80 ms + tiempo del servidor | 80 ms + tiempo del servidor |
| **Total antes del trabajo útil** | **~280 ms** | **~360 ms** |

La segunda consulta, sobre la misma conexión, cuesta 80 ms más el tiempo del servidor. Por eso reutilizar conexiones (*keep-alive*) rinde tanto, y por eso ayuda un CDN cercano: los handshakes se hacen contra un punto a 10 ms, no contra el origen a 80.

### HTTP/1.1, HTTP/2 y HTTP/3

**HTTP/1.1** atiende una solicitud por conexión a la vez; los navegadores abren unas seis conexiones por origen para compensar, y las cabeceras se repiten como texto en cada solicitud.

**HTTP/2** multiplexa muchas solicitudes (*streams*) sobre una conexión, en marcos binarios intercalados, y comprime cabeceras con HPACK: una cookie de 800 bytes viaja completa una vez y luego se referencia con pocos bytes. Pero TCP entrega los bytes en orden: si se pierde un paquete, **todos** los streams esperan la retransmisión. Es el **head-of-line blocking** de transporte.

**HTTP/3** reemplaza TCP por **QUIC**, sobre UDP y con TLS 1.3 integrado. Cada stream se ordena por separado, así que un paquete perdido solo frena al suyo, y el handshake es uno solo (1 RTT; 0-RTT al reanudar). La conexión tiene un ID propio, no atado a IP y puerto: cuando un transportista pasa del wifi del depósito a datos móviles, sobrevive (**migración de conexión**).

| Aspecto | HTTP/1.1 | HTTP/2 | HTTP/3 |
|---|---|---|---|
| Transporte | TCP | TCP | QUIC sobre UDP |
| Solicitudes concurrentes por conexión | Una a la vez | Muchas (multiplexadas) | Muchas (multiplexadas) |
| Cabeceras | Texto, repetidas | Comprimidas (HPACK) | Comprimidas (QPACK) |
| Head-of-line blocking | Por solicitud | En TCP, ante pérdida de paquetes | Solo dentro del stream afectado |
| Handshake con conexión nueva | TCP + TLS: 2 RTT | TCP + TLS: 2 RTT | 1 RTT (0-RTT al reanudar) |
| Cambio de red | Conexión nueva | Conexión nueva | La conexión migra |
| Dónde brilla | Simplicidad, compatibilidad | Páginas con muchos recursos | Redes móviles con pérdida |

El navegador y el CDN negocian la versión solos; HTTP/3 rinde más donde Rumbo más lo necesita: la app de transportistas en la calle, con señal irregular.

### Métodos: seguros e idempotentes

Un método es **seguro** si no cambia el estado del servidor (GET, HEAD, OPTIONS) e **idempotente** si repetirlo deja el mismo resultado que hacerlo una vez (los seguros, más PUT y DELETE). POST y PATCH, en general, no son ninguna de las dos. Proxies, navegadores y bibliotecas de reintentos usan estas garantías para decidir si pueden repetir una solicitud.

**Ejemplo:** `GET /v1/pedidos/4812` se puede reintentar libremente. `POST /v1/asistente/consultas` crea una consulta y dispara una llamada al LLM, que cuesta tokens; reintentarla a ciegas duplica el gasto y puede duplicar acciones del agente. Por eso lleva una clave de idempotencia como se describe en el tema de gRPC y REST.

### Códigos de estado que hay que leer bien

El código es el primer diagnóstico. Los que más aparecen en una API con agentes:

- **200, 201, 204:** éxito; 201 indica recurso creado (con `Location`), 204 éxito sin cuerpo.
- **301, 308, 302, 307:** redirecciones; 301 y 308 son permanentes, y solo 307 y 308 garantizan que un POST siga siendo POST.
- **304 Not Modified:** el recurso no cambió desde la versión que el cliente ya tiene (ver caché).
- **400:** solicitud mal formada. **422:** bien formada pero con datos inválidos, por ejemplo una fecha de entrega en el pasado.
- **401 frente a 403:** 401 significa "no sé quién eres" (falta credencial o venció; se resuelve autenticándose de nuevo); 403 significa "sé quién eres y no puedes hacer esto". Confundirlos hace que el frontend mande al usuario a iniciar sesión cuando el problema es de permisos (ver [Autenticación, JWT y OAuth](#t/autenticacion)).
- **409 Conflict:** el estado actual impide la operación, por ejemplo editar un pedido que otro usuario acaba de cancelar.
- **429 Too Many Requests:** se superó un límite de tasa. Debería venir con `Retry-After` (segundos o fecha) que dice cuándo volver.
- **500:** error interno; puede ser un bug determinista, así que reintentar no siempre sirve.
- **502 Bad Gateway:** un proxy recibió una respuesta inválida del servicio de atrás (el pod se cayó a mitad de la respuesta). **503 Service Unavailable:** el servicio no puede atender ahora (sin pods sanos, load shedding). **504 Gateway Timeout:** el proxy se cansó de esperar al servicio de atrás. Un 504 en el endpoint del asistente casi siempre significa que el timeout del balanceador es menor que lo que tarda el LLM.

### Cabeceras que importan

Pocas cabeceras explican casi todo: `Content-Type` y `Accept` (formato del cuerpo y formato pedido), `Authorization` (la credencial), `Cache-Control` y `ETag` (caché), `Content-Encoding` (compresión), `Origin` (sitio de origen, clave para CORS), `Vary` (de qué cabeceras depende la respuesta, para que una caché no mezcle versiones) y `traceparent`, que permite seguir una consulta desde el navegador hasta la llamada al modelo.

### Caché HTTP

`Cache-Control` le dice a cada caché qué puede hacer con la respuesta. `max-age=600` permite reutilizarla diez minutos sin preguntar. `no-cache`, a pesar del nombre, permite guardarla pero obliga a **revalidar** antes de usarla. `no-store` prohíbe guardarla en cualquier lado. `private` limita el guardado al navegador del usuario; `public` y `s-maxage` habilitan las cachés compartidas, como un CDN.

La revalidación usa **ETag**, una huella de la versión del recurso. El cliente envía `If-None-Match: "v42"`; si no cambió, el servidor contesta 304 sin cuerpo.

**Ejemplo:** la lista de zonas de cobertura pesa 180 KB y cambia una vez por semana. Con `max-age=300` y ETag, un comercio que abre el panel 50 veces por día la descarga pocas veces; el resto son 304 de unos 200 bytes.

Lo que **nunca** debe ir a una caché compartida: respuestas con datos personales (nombre, teléfono y dirección de destinatarios), respuestas del asistente sobre un pedido concreto y cualquier cosa que dependa de quién la pide. Esas llevan `Cache-Control: private, no-store`. Un CDN que cachea por URL sin mirar la sesión puede servirle la respuesta de un comercio a otro.

### Cookies a nivel de protocolo

El servidor crea una cookie con `Set-Cookie` y el navegador la devuelve automáticamente en la cabecera `Cookie` de cada solicitud que corresponda. Los atributos definen a qué solicitudes corresponde y cómo se protege: `Domain` y `Path` (alcance), `Max-Age` o `Expires` (vida), `Secure` (solo por HTTPS), `HttpOnly` (invisible para JavaScript) y `SameSite` (si se envía en solicitudes iniciadas desde otro sitio).

```
Set-Cookie: sesion=7f3a...; Path=/; Max-Age=3600; Secure; HttpOnly; SameSite=Lax
```

El envío automático es justamente lo que las hace cómodas y peligrosas; qué combinación usar y por qué está en [Seguridad en el frontend](#t/seguridad-frontend).

### CORS y la política de mismo origen

Un **origen** es esquema, dominio y puerto: `https://panel.rumbo.app` y `https://api.rumbo.app` son orígenes distintos. La **política de mismo origen** impide que el JavaScript de un sitio lea respuestas de otro. **CORS** (*Cross-Origin Resource Sharing*) permite al servidor declarar qué orígenes ajenos sí pueden. Lo aplica el navegador; `curl` lo ignora, así que CORS protege al usuario, no al servidor.

Las solicitudes **simples** (GET, HEAD o POST de formulario o texto plano, sin cabeceras propias) se envían directamente y el navegador decide después si deja leer la respuesta. Las demás, incluido un POST con JSON o con `Authorization`, requieren un **preflight**: primero un `OPTIONS` que pregunta si se puede.

```
OPTIONS /v1/asistente/consultas
Origin: https://panel.rumbo.app
Access-Control-Request-Method: POST
Access-Control-Request-Headers: content-type, authorization

204 No Content
Access-Control-Allow-Origin: https://panel.rumbo.app
Access-Control-Allow-Methods: POST
Access-Control-Allow-Headers: content-type, authorization
Access-Control-Allow-Credentials: true
Access-Control-Max-Age: 600
```

`Max-Age` evita repetir el preflight, que cuesta un RTT. Con credenciales, `Allow-Origin` no puede ser `*`. Los errores riesgosos típicos: reflejar cualquier `Origin` con credenciales o aceptar subdominios con una expresión regular floja.

### Por qué transmitir la respuesta del LLM

Un LLM genera token a token. Si el asistente produce 400 tokens a 40 por segundo, la respuesta tarda unos 10 segundos. Sin streaming, el comercio mira un indicador de carga todo ese tiempo; con streaming, lee desde el **tiempo al primer token**, digamos 0,8 segundos. El total es el mismo; la experiencia es otra. Además permite mostrar los pasos del agente: "consultando el pedido", "buscando en las políticas".

### Server-Sent Events, WebSockets y fetch con streams

**Server-Sent Events (SSE)** es una respuesta HTTP normal con `Content-Type: text/event-stream` que no termina: el servidor va escribiendo eventos en texto, separados por una línea en blanco.

```
event: herramienta
data: {"nombre":"consultar_pedido","estado":"iniciada"}

id: 17
data: {"delta":"El pedido 4812 "}

: ping
```

Va en un solo sentido. La API `EventSource` reconecta sola y envía `Last-Event-ID` para retomar, pero solo hace GET y sin cabeceras propias. Por eso muchas interfaces de chat usan **fetch con `ReadableStream`**: un POST con la consulta y `Authorization`, cuya respuesta se lee por fragmentos y se parsea en formato SSE; la reconexión queda a cargo de la aplicación.

**WebSockets** abre, tras un handshake HTTP, un canal bidireccional persistente. Sirve cuando el cliente también envía datos de forma continua (audio de voz, interrupciones). El costo es operativo: cada conexión queda atada a un pod, un deploy corta miles a la vez, el balanceador necesita afinidad o un bus para reenviar mensajes y el autoscaling por CPU no refleja bien la carga.

| Aspecto | SSE | fetch con streams | WebSockets |
|---|---|---|---|
| Dirección | Servidor a cliente | Servidor a cliente (la solicitud es una sola) | Ambas |
| Método y cabeceras | GET sin cabeceras propias (con `EventSource`) | Cualquiera | Solo en el handshake |
| Reconexión | Automática con `Last-Event-ID` | Manual | Manual |
| Pasa por proxies y CDNs | Bien, si no hacen buffering | Bien, si no hacen buffering | Requiere soporte explícito |
| Estado en el servidor | Por solicitud | Por solicitud | Por conexión, de larga vida |
| Uso típico | Notificaciones, seguimiento en vivo | Respuestas del asistente | Voz en tiempo real, edición colaborativa |

### Lo que rompe el streaming en el camino

Proxy inverso, balanceador, API gateway o CDN: cualquiera puede romper el streaming.

- **Buffering:** el proxy acumula la respuesta completa antes de enviarla. En nginx se desactiva con `proxy_buffering off` o con la cabecera `X-Accel-Buffering: no` desde el backend.
- **Compresión:** gzip junta bytes para comprimir mejor y retiene los fragmentos chicos. Se desactiva para `text/event-stream` o se fuerza el envío de cada fragmento.
- **Timeouts por inactividad:** muchos balanceadores cortan tras 60 segundos sin tráfico; si el agente pasa 70 segundos en una herramienta, la conexión muere. Se envía un **heartbeat** (`: ping`) cada 15 segundos.
- **Timeouts totales:** un gateway con límite de 30 segundos por solicitud corta respuestas largas aunque fluyan.

### Cancelar la generación

Si el comercio cierra la pestaña o aprieta "detener", el navegador cancela con `AbortController` y la conexión se cierra. El backend debe **detectarlo** (en Go, se cancela el `context` de la solicitud) y cancelar la llamada al modelo y las herramientas en curso; si no, el LLM sigue consumiendo tokens para nadie.

**Ejemplo:** si el 25% de las consultas se abandona con 600 tokens de salida por delante, propagar la cancelación ahorra unos 150 tokens por consulta en promedio: 150 millones por mes con un millón de consultas. Ver [LLMs en producción](#t/llms-produccion).

```js
const control = new AbortController();
botonDetener.onclick = () => control.abort();

const resp = await fetch("https://api.rumbo.app/v1/asistente/consultas", {
  method: "POST",
  headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
  body: JSON.stringify({ pregunta, pedidoId: "4812" }),
  signal: control.signal,
});
const lector = resp.body.pipeThrough(new TextDecoderStream()).getReader();
for (;;) {
  const { value, done } = await lector.read();
  if (done) break;
  procesarEventos(value); // parsea líneas "data:" y actualiza la interfaz
}
```

## Casos prácticos

### Las respuestas del asistente llegan todas juntas

**Situación:** en local, el asistente de soporte escribe palabra por palabra. En producción, el comercio espera 9 segundos y el texto aparece completo de golpe, aunque el backend emitió el primer evento a los 0,7 segundos.

**Qué se hace:** se compara el tiempo al primer byte en el backend y en el navegador, salto por salto. El culpable es el proxy inverso, con buffering activado y gzip para todo. Se agrega `X-Accel-Buffering: no` y `Cache-Control: no-store` en las respuestas `text/event-stream`, se excluye ese tipo de la compresión y se suma un heartbeat cada 15 segundos. Una prueba sintética mide desde afuera el tiempo al primer fragmento para detectar regresiones.

### 429 durante un pico y un frontend que no sabe esperar

**Situación:** un lunes a las 10 hay un pico de consultas. El API del asistente empieza a devolver 429 porque el proveedor del LLM limitó los tokens por minuto. El panel reintenta cada error de inmediato, tres veces, y triplica la carga justo cuando el sistema está saturado.

**Qué se hace:** el backend traduce el límite del proveedor en un 429 propio con `Retry-After: 8`, en lugar de un 500 genérico. El frontend respeta `Retry-After` cuando viene y, si no, usa backoff exponencial con jitter (1, 2, 4 segundos más un componente aleatorio) y un máximo de tres intentos (ver [Patrones de resiliencia](#t/resiliencia)). Mientras espera, muestra "reintentando en 8 segundos" en lugar de un error. El servidor agrega un límite por comercio para que uno solo no agote la cuota de todos.

### Error de CORS al mudar el panel de dominio

**Situación:** el panel pasa de `https://rumbo.app/panel` a `https://panel.rumbo.app`. Al día siguiente, el asistente no responde y la consola muestra un error de CORS en el preflight. Con `curl`, el endpoint funciona.

**Qué se hace:** antes, panel y API compartían origen y nunca hubo preflight; ahora son orígenes distintos y el POST con JSON y `Authorization` dispara un `OPTIONS` que el API gateway no conocía. Se configura el gateway para responder el preflight con una lista explícita de orígenes permitidos (no reflejando cualquier `Origin`), los métodos y cabeceras usados, `Allow-Credentials` porque la sesión va en cookie, y `Max-Age: 600`. Se agrega `Vary: Origin` para que ninguna caché mezcle respuestas entre orígenes.

### Datos personales cacheados en el CDN

**Situación:** para aliviar el origen, alguien activa en el CDN "cachear todas las respuestas GET por 60 segundos". Un comercio reporta que en el detalle de un pedido vio el nombre y el teléfono de un destinatario que no era suyo.

**Qué se hace:** se desactiva la regla, se purga la caché y se trata como incidente de datos personales. La causa: el CDN cacheaba por URL, y `GET /v1/pedidos/4812/detalle` devolvía datos distintos según la sesión, sin que la respuesta lo indicara. La corrección es explícita y por defecto segura: todas las respuestas del API llevan `Cache-Control: private, no-store` salvo una lista blanca de recursos públicos (zonas de cobertura, manuales de políticas) que declaran `public, s-maxage`. El CDN no cachea nada sin esa declaración, y una prueba en la CI verifica la cabecera en cada endpoint con datos de destinatarios o respuestas del asistente.

## Errores comunes

- **Abrir una conexión nueva por llamada.** DNS, TCP y TLS cuestan cientos de milisegundos con RTT alto; se reutilizan conexiones y se termina TLS cerca del usuario.
- **Devolver 403 cuando falta la sesión o 401 cuando faltan permisos.** El frontend toma la acción equivocada; 401 es "autentícate", 403 es "no puedes".
- **Reintentar POST sin clave de idempotencia ni respeto por `Retry-After`.** Duplica acciones y gasto de tokens; se reintenta solo lo idempotente o protegido, con backoff.
- **Confundir `no-cache` con `no-store`.** `no-cache` sí guarda; para datos personales se usa `private, no-store`.
- **Configurar CORS reflejando cualquier `Origin` con credenciales.** Cualquier sitio podría leer respuestas con la sesión del usuario; se usa una lista explícita.
- **Probar el streaming solo en local.** Los proxies, la compresión y los timeouts aparecen en producción; se mide el tiempo al primer fragmento desde afuera y se usa heartbeat.

## Para discutir en equipo

- ¿Qué saltos (CDN, balanceador, gateway, proxy) atraviesa hoy una consulta al asistente, y cuál es el timeout por inactividad y total de cada uno?
- ¿Cuándo justificaría la interfaz del asistente pasar de SSE o fetch con streams a WebSockets, y quién operaría esas conexiones?
- ¿Qué endpoints devuelven datos personales y cómo verificamos que ninguno pueda quedar en una caché compartida?
- Si el comercio cierra la pestaña, ¿hasta dónde llega hoy la cancelación: el backend, la llamada al modelo, las herramientas del agente?
- ¿Qué debería ver el usuario ante un 429, un 503 y un 504 del asistente, y en qué casos reintenta el frontend solo?
