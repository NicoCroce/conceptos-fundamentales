---
slug: autenticacion
titulo: Autenticación, JWT y OAuth
resumen: Cómo un sistema sabe quién llama y qué puede hacer: sesiones, JWT, OAuth, OpenID Connect, API keys e identidad de agentes que actúan por usuarios.
lectura: 16
---

## La idea central

Cada pedido que llega a un backend trae, explícita o implícitamente, dos preguntas: **¿quién eres?** y **¿puedes hacer esto?** La primera es la **autenticación**: comprobar una identidad. La segunda es la **autorización**: decidir si esa identidad tiene permiso para esta acción sobre este recurso. Se confunden porque llegan juntas, pero fallan distinto: un sistema puede saber perfectamente quién es el comercio que llama y aun así dejarle ver pedidos de otro comercio.

Cookies de sesión, JWT, OAuth, OpenID Connect y API keys son formas de transportar esas respuestas entre navegador, servicios y agentes. Una analogía: la sesión con cookie es el guardarropa que te entrega un número y guarda tu abrigo; el JWT es una credencial plastificada con tu foto y tus permisos impresos: cualquiera la verifica sin llamar a nadie, pero no se retira fácilmente. Cuando un agente actúa en nombre de un usuario, se suma una tercera pregunta: **¿en nombre de quién actúa?**

## Conceptos

### Autenticación y autorización

- **Autenticación:** el usuario demuestra quién es (contraseña más segundo factor, una passkey, un inicio de sesión con el proveedor de identidad de su empresa). El resultado es una identidad: "usuaria 8812 del comercio 31".
- **Autorización:** en cada operación, el sistema decide con esa identidad y el contexto. "La usuaria 8812 tiene rol de operadora en el comercio 31; puede ver pedidos del comercio 31; no puede reprogramar más de 50 por día."

**Por qué importa:** la mayoría de los incidentes graves de APIs no son autenticaciones rotas, sino autorizaciones ausentes: el endpoint verifica que el token es válido y luego confía en el `comercio_id` que viene en la URL.

### Sesiones de servidor con cookies

El modelo clásico:

1. El usuario inicia sesión; el servidor genera un **identificador de sesión** aleatorio y largo (por ejemplo, 128 bits).
2. Guarda en un almacén (Redis, la base) un registro: sesión, usuario, fecha de creación, vencimiento.
3. Envía el identificador en una cookie. El navegador la adjunta en cada petición al mismo sitio.
4. En cada petición, el servidor busca la sesión en el almacén.

La ventaja: **revocar es trivial**; cerrar sesión o bloquear a un usuario es borrar registros. La desventaja: cada petición consulta el almacén, una dependencia compartida que otros servicios necesitan para validar la sesión. Cómo configurar esa cookie (HttpOnly, Secure, SameSite) se trata en [Seguridad en el frontend](#t/seguridad-frontend).

### JWT: estructura

Un **JWT** (JSON Web Token) lleva los datos dentro y una firma que prueba que nadie los alteró. Tiene tres partes separadas por puntos: `header.payload.signature`.

- **Header:** JSON con el algoritmo y el identificador de la clave, por ejemplo `{"alg":"RS256","kid":"2026-10"}`.
- **Payload:** JSON con las afirmaciones (claims) sobre el sujeto.
- **Signature:** la firma del header y el payload.

Cada parte se codifica en **base64url**, una variante de base64 segura para URLs. Codificar no es cifrar: cualquiera que tenga el token puede decodificar el payload y leerlo.

```json
{
  "iss": "https://auth.rumbo.example",
  "sub": "usuario-8812",
  "aud": "api-pedidos",
  "exp": 1793000900,
  "iat": 1793000000,
  "nbf": 1793000000,
  "jti": "c2f1a7e0-55d3-4b8e-9a41-0d7c6e1f2a90",
  "comercio": "31",
  "scope": "pedidos:lectura entregas:reprogramar"
}
```

**Por qué importa:** nunca se ponen en un JWT datos que el portador no deba ver (teléfonos de destinatarios, datos internos), porque el payload es legible.

### Firma: simétrica y asimétrica

- **HS256 (HMAC con SHA-256):** firma y verificación con el mismo secreto compartido. Simple, pero todo servicio que verifica también puede firmar, es decir, fabricar tokens válidos.
- **RS256 (RSA) y ES256 (curvas elípticas):** el servidor de autenticación firma con una **clave privada** y los servicios verifican con la **clave pública**. Un servicio comprometido puede leer tokens, pero no fabricarlos. ES256 produce firmas más cortas.

Las claves públicas se publican en un documento **JWKS** (JSON Web Key Set) en una URL conocida; cada una tiene un `kid`, y el header del token indica cuál usar.

La **rotación de claves** se hace con solapamiento: (1) se publica la clave nueva en el JWKS; (2) se espera a que los verificadores refresquen su copia (por ejemplo, la cachean 1 hora); (3) se empieza a firmar con la nueva; (4) se retira la vieja cuando vencieron todos los tokens firmados con ella. Si los access tokens duran 15 minutos y el JWKS se cachea 1 hora, la clave vieja debe quedar publicada al menos 1 hora y 15 minutos después del cambio.

**Ejemplo:** con HS256 compartido entre 12 servicios de Rumbo, una filtración en cualquiera permitiría fabricar tokens de administrador. Con ES256, solo el servidor de autenticación tiene la clave privada, guardada en KMS.

### Claims estándar

| Claim | Significado | Qué se verifica |
|---|---|---|
| `iss` | Quién emitió el token | Que sea el servidor de autenticación esperado |
| `sub` | Sujeto: a quién representa | Se usa como identidad; estable y no reasignable |
| `aud` | Audiencia: para qué servicio es | Que incluya a este servicio |
| `exp` | Vencimiento (segundos Unix) | Que no haya pasado |
| `iat` | Momento de emisión | Útil para auditoría y revocación por fecha |
| `nbf` | No válido antes de | Que ya haya llegado |
| `jti` | Identificador único del token | Permite listas de revocación y detectar reuso |

### Validación paso a paso

Un servicio que recibe un JWT debe, en este orden:

1. **Leer el header sin confiar en él.** El `alg` lo decide el verificador, no el token: se valida contra una **lista permitida** (por ejemplo, solo `ES256`). Esto cierra toda una familia de fallas históricas: bibliotecas que aceptaban `"alg":"none"` (sin firma) o que, configuradas con una clave pública RSA, aceptaban un token `HS256` firmado usando esa clave pública como secreto.
2. **Verificar la firma** con la clave del JWKS que corresponde al `kid`, solo si ese `kid` pertenece al `iss` esperado.
3. **Verificar `iss`** contra el valor exacto configurado.
4. **Verificar `aud`**: el token debe estar dirigido a este servicio.
5. **Verificar `exp` y `nbf`** con una tolerancia de reloj pequeña (30 a 60 segundos), porque los relojes de distintas máquinas no coinciden exactamente.
6. **Recién entonces autorizar** con `sub`, `scope` y los datos del recurso.

**Por qué importa:** casi todas las vulnerabilidades con JWT son validaciones omitidas. Se usa una biblioteca mantenida, configurada de forma explícita, y se prueba con tokens inválidos.

### Access tokens cortos y refresh tokens

Como un JWT no se retira fácilmente, se acorta su vida: un **access token** dura, por ejemplo, 15 minutos, y se entrega además un **refresh token** de larga duración (días), que solo sirve para pedir access tokens nuevos al servidor de autenticación y que normalmente es un valor opaco guardado en su base.

La **rotación de refresh tokens** agrega una defensa: cada vez que se usa un refresh token, el servidor lo invalida y entrega uno nuevo de la misma "familia". Si alguna vez llega un refresh token que ya fue usado, hay dos copias en circulación: una del usuario legítimo y otra de alguien que lo robó. El servidor no sabe cuál es cuál, así que **revoca toda la familia** y obliga a iniciar sesión de nuevo. Esto se llama **detección de reuso**.

**Ejemplo:** R1 se usa a las 9:00 y produce R2; a las 9:20 el cliente legítimo usa R2 y recibe R3. A las 9:25 llega R2 desde otra red: ya fue usado, así que se invalida toda la familia y se registra un evento de seguridad.

### Revocación de JWT

Opciones, de menor a mayor costo:

- **Vida corta:** un token revocado sirve hasta su `exp`; con 5 a 15 minutos suele bastar.
- **Lista de denegación por `jti`:** se guardan los `jti` revocados hasta su vencimiento y cada servicio consulta la lista; es pequeña porque solo contiene tokens vigentes.
- **Versión de token por usuario:** el token lleva `ver: 7`; al bloquear al usuario la versión pasa a 8 y se rechazan todos los tokens con 7.

Las dos últimas reintroducen el estado compartido que el JWT evitaba. El compromiso:

| Aspecto | Sesión con cookie | JWT |
|---|---|---|
| Dónde está el estado | En el servidor | En el token |
| Revocación | Inmediata, borrando la sesión | Al vencer, o con lista o versión |
| Verificación entre servicios | Requiere acceso al almacén | Local, con la clave pública |
| Tamaño en cada petición | Pequeño (un identificador) | Mayor (cientos de bytes) |
| Datos visibles para el cliente | Ninguno | El payload completo |
| Caso típico | Aplicación web de un solo backend | APIs y comunicación entre servicios |

### OAuth 2.0: roles

**OAuth 2.0** es un marco de **autorización delegada**: una aplicación accede a recursos en nombre de un usuario sin conocer su contraseña. Roles:

- **Resource owner:** el dueño de los datos, normalmente el usuario.
- **Client:** la aplicación que quiere acceder (el panel web, una app móvil, el asistente de un comercio).
- **Authorization server:** autentica al usuario, pide consentimiento y entrega tokens.
- **Resource server:** la API que guarda los recursos y valida los tokens.

### Flujo de código de autorización

Paso a paso, para el panel de comercios de Rumbo:

1. El usuario toca "Ingresar". El panel lo redirige al servidor de autorización con `client_id`, `redirect_uri`, `scope`, un `state` aleatorio y (ver PKCE) un `code_challenge`.
2. El servidor de autorización autentica al usuario y, si corresponde, le muestra qué permisos pide la aplicación.
3. Redirige de vuelta a la `redirect_uri` registrada con un **código de autorización** de un solo uso y vida muy corta, y el mismo `state`.
4. El panel verifica que `state` coincide con el que envió (protección contra que un atacante le inyecte su propio código).
5. El panel intercambia el código por tokens en una llamada directa al servidor de autorización, sin pasar por el navegador del usuario.
6. Con el access token, llama al resource server.

El código viaja por el navegador; los tokens, no. Por eso existe el paso intermedio.

### PKCE

Los **clientes públicos** (una SPA, una app móvil) no pueden guardar un secreto de cliente: cualquiera puede extraerlo del código. Sin secreto, quien intercepte el código de autorización (por ejemplo, otra app registrada con el mismo esquema de URL en el teléfono) podría canjearlo. **PKCE** (Proof Key for Code Exchange) lo evita:

1. El cliente genera un valor aleatorio, el `code_verifier`, por ejemplo de 43 a 128 caracteres.
2. Calcula `code_challenge = BASE64URL(SHA256(code_verifier))` y envía solo el challenge en el paso 1 del flujo.
3. Al canjear el código, envía el `code_verifier` original.
4. El servidor calcula el hash, lo compara con el challenge guardado y solo entonces entrega tokens.

```text
code_verifier  = dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
code_challenge = E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
                 (SHA-256 del verifier, en base64url)
```

Quien intercepta el código no tiene el verifier, y no puede deducirlo del challenge porque un hash no se invierte. Hoy se recomienda PKCE para todos los clientes, también los confidenciales.

### Client credentials

Para servicio a servicio, sin usuario de por medio, el flujo **client credentials** es directo: el servicio se autentica ante el servidor de autorización (con su secreto, una clave privada o mTLS) y recibe un access token con sus propios permisos.

**Ejemplo:** el job nocturno de pronóstico de demanda pide un token con `scope=pedidos:lectura-agregada` y `aud=api-pedidos`, válido 10 minutos. No representa a ningún usuario, y su `sub` es el propio job.

### OpenID Connect

OAuth trata sobre acceso, no sobre identidad. **OpenID Connect (OIDC)** se apoya en OAuth y agrega autenticación: al pedir el scope `openid`, además del access token se recibe un **ID token**, un JWT que dice quién inició sesión, cuándo y cómo, con `aud` igual al `client_id` de la aplicación.

La distinción clave:

- **ID token:** es para el cliente. Le dice a la aplicación quién es el usuario. Nunca se envía a una API.
- **Access token:** es para el resource server. Se envía a la API.

Usar el ID token para llamar APIs es un error común: su audiencia es la aplicación, no la API. La misma federación OIDC, aplicada a los pipelines de CI que piden credenciales de AWS, se describe en el tema de CI/CD.

### Scopes y consentimiento

Los **scopes** acotan lo que un token permite (`pedidos:lectura`, `entregas:reprogramar`): la intersección de lo que la aplicación pidió, lo que el usuario consintió y lo que tiene permitido. Los scopes no reemplazan la autorización por recurso: `pedidos:lectura` no dice cuáles pedidos, eso lo decide el servicio con el `sub` y el comercio. Conviene pedir scopes de forma incremental: lectura al entrar, escritura solo cuando el usuario intenta algo que la requiere.

### API keys

Una **API key** es un secreto estático que identifica a un cliente. Es aceptable en integraciones servidor a servidor sin usuario interactivo, como la carga de pedidos de comercios grandes. Prácticas:

- **Guardar solo el hash** (por ejemplo SHA-256) en la base, como con una contraseña; la clave completa se muestra una sola vez al crearla.
- **Prefijo reconocible**, como `rmb_live_` o `rmb_test_`, para que los escáneres de secretos las detecten y el soporte identifique el tipo sin ver el resto.
- **Varias claves activas por cliente**, para rotar sin corte, con fecha de último uso visible.
- **Límites y permisos por clave:** tasa máxima, scopes y, si se puede, rango de IPs.

### mTLS

Con **mTLS** cada lado presenta un certificado y la identidad del cliente queda ligada a la conexión. Es útil con socios y entre servicios internos, y puede combinarse con OAuth para que un token solo sirva desde el cliente que tiene el certificado. Certificados, vencimientos e inventario se tratan en [Secretos y cifrado](#t/secretos).

### Identidad de agentes

Cuando un agente actúa en nombre de un usuario (el asistente de soporte que reprograma una entrega pedida por un comercio), las reglas anteriores se aplican con más rigor:

1. **Delegación, no credencial propia amplia.** El agente opera con un token derivado del usuario, no con una cuenta de servicio con acceso a todos los comercios. Así nunca tiene más permisos que el usuario.
2. **Tokens cortos y acotados.** Mediante **intercambio de tokens** (token exchange, también llamado "on-behalf-of"), el backend del agente presenta el token del usuario al servidor de autorización y recibe uno nuevo con audiencia de una sola API, scopes mínimos para la tarea y vida de pocos minutos.
3. **Ambas identidades en el token y en la auditoría.** El token lleva el usuario como `sub` y el agente como actor (el estándar de intercambio de tokens prevé un claim `act`). Los registros dicen "el asistente, actuando por la usuaria 8812, reprogramó el pedido 4512".
4. **Aprobación humana para acciones sensibles.** Cancelar en masa, cambiar direcciones o exportar datos requieren confirmación explícita del usuario, fuera del texto que el modelo puede manipular.
5. **Sin credenciales compartidas de larga duración.** Una API key global para "el agente" mezcla a todos los usuarios, no se puede revocar para uno solo y es el premio mayor para una inyección de prompt.

Los principios aplicados a servidores MCP están en [MCP](#t/mcp), y los riesgos de agencia excesiva, en [Seguridad de LLMs y agentes](#t/seguridad-agentes).

## Casos prácticos

### Migrar el login del panel a OIDC con PKCE

**Situación:** el panel de comercios es una SPA con usuario y contraseña propios y un JWT HS256 de 7 días guardado en el navegador. Los comercios grandes piden iniciar sesión con el proveedor de identidad de su empresa.

**Qué se hace:** se adopta OIDC con flujo de código y PKCE. El panel deja de manejar tokens en JavaScript: un backend propio hace el canje y mantiene una sesión con cookie (patrón "backend for frontend"). Los access tokens pasan a ES256 con 10 minutos de vida y `aud` por API; los refresh tokens rotan con detección de reuso. Cada comercio grande se federa con su propio proveedor, y el alta y la baja de empleados pasan a resolverse allí.

### Un token aceptado por el servicio equivocado

**Situación:** una auditoría descubre que un token emitido para la API de seguimiento, que usa una integración de un socio con scope de solo lectura, también es aceptado por la API interna de asignación. Ambas verificaban firma y vencimiento, pero no `aud`.

**Qué se hace:** cada servicio pasa a exigir su propia audiencia y la biblioteca de validación compartida falla si no se configura `aud`. Se agrega una prueba de contrato que envía tokens válidos de otras audiencias y espera un 401. Se revisan los registros de 90 días buscando tokens de audiencia ajena.

### Refresh token robado detectado por reuso

**Situación:** una extensión del navegador maliciosa copia el refresh token de un operador de un comercio. Horas después, el atacante lo usa desde otro país; poco más tarde, la app legítima intenta refrescar con el mismo token.

**Qué se hace:** al segundo uso, el servidor detecta reuso, revoca toda la familia de tokens y obliga a iniciar sesión. Se genera una alerta con ambas IPs y el `jti` de la familia; el equipo revisa las acciones del atacante durante la ventana de un access token. Como mejora, se acorta la vida absoluta de la familia y se ligan los tokens al dispositivo cuando el cliente lo soporta.

### El asistente reprograma con un token delegado

**Situación:** una operadora de un comercio escribe al asistente de soporte: "reprograma para mañana los pedidos de hoy de la zona oeste que no salieron". Hasta ahora, el asistente usaba una cuenta de servicio capaz de reprogramar pedidos de cualquier comercio.

**Qué se hace:** el backend del asistente intercambia el token de la operadora por uno con `aud=api-entregas`, `scope=entregas:reprogramar`, vida de 5 minutos y el asistente como actor. La API de entregas verifica que cada pedido pertenezca al comercio de la operadora y que ella tenga ese permiso. Antes de ejecutar, el asistente muestra la lista (23 pedidos) y pide confirmación en un botón de la interfaz, no en el chat. Cada cambio se registra con la operadora, el asistente y la conversación. Un texto inyectado en un ticket ya no puede llevar al agente a tocar pedidos de otro comercio, porque el token no lo permite.

## Errores comunes

- **No verificar `aud`.** Un token válido para otro servicio pasa a ser válido para todos; cada servicio exige su audiencia.
- **Dejar que el token elija el algoritmo.** Abre la puerta a `alg: none` y a confusiones de clave; el verificador fija una lista permitida.
- **Usar el ID token para llamar APIs.** Está dirigido a la aplicación; a las APIs se les envía el access token.
- **JWT de larga duración sin estrategia de revocación.** Un token robado sirve días; vida corta más refresh tokens rotativos.
- **Datos sensibles en el payload.** El JWT se lee sin la clave; solo identificadores y permisos.
- **Dar al agente una credencial de servicio con acceso global.** Rompe el límite del usuario y la auditoría; tokens delegados, cortos y acotados.

## Para discutir en equipo

- ¿Qué servicios nuestros aceptan hoy un token sin verificar `aud` o `iss`, y cómo lo comprobaríamos de forma automática?
- ¿Cuál es el tiempo máximo que aceptamos entre bloquear a un usuario y que deje de tener acceso, y qué estrategia de revocación implica?
- ¿Qué acciones de los agentes de Rumbo deberían requerir aprobación humana aunque el token las permita?
- Si un comercio da de baja a un empleado en su proveedor de identidad, ¿cuánto tarda en perder acceso a Rumbo y a los agentes que actúan por él?
