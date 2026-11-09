---
slug: cloudflare
titulo: Cloudflare y protección perimetral
resumen: Cómo un proveedor de borde como Cloudflare se pone delante de la aplicación para acelerarla, filtrar ataques y proteger los endpoints con LLMs.
lectura: 16
---

## La idea central

Sin un proveedor de borde, el navegador de un comercio se conecta directamente a nuestro balanceador en AWS: cada pedido, legítimo o no, llega hasta nuestra infraestructura y la consume. Con un servicio como Cloudflare delante, el navegador se conecta a un servidor del proveedor que está cerca del usuario (el **borde**), y ese servidor decide qué hacer: responder desde su caché, bloquear, pedir una verificación o reenviar el pedido a nuestro origen. Nuestro balanceador deja de ser la puerta de entrada y pasa a ser una puerta trasera que solo debería abrirse para el proveedor.

La analogía útil es la recepción de un edificio: entrega folletos sin molestar a nadie (caché), pide identificación (verificación de bots), limita cuántas veces por hora sube la misma persona (rate limiting) y no deja pasar a quien viene con intenciones evidentes (WAF). Con agentes, la recepción tiene un papel extra: proteger los endpoints donde cada pedido cuesta tokens de LLM, porque ahí un abuso también infla la factura del proveedor de modelos.

## Conceptos

### CDN y proxy inverso: qué cambia cuando el tráfico pasa por el borde

Un **proxy inverso** es un servidor que recibe los pedidos en nombre de otro servidor (el **origen**) y se los reenvía. Una **CDN** (red de distribución de contenido) es un proxy inverso distribuido en cientos de ubicaciones del mundo, que además guarda copias del contenido cerca de los usuarios.

Paso a paso, lo que cambia al poner Cloudflare delante de Rumbo:

1. El DNS de `panel.rumbo.example` deja de apuntar al balanceador de AWS y devuelve IPs del proveedor.
2. Esas IPs son **anycast**: se anuncian desde muchas ubicaciones y el ruteo de internet lleva cada conexión a la más cercana. Un comercio en Córdoba y otro en Madrid usan la misma IP, pero llegan a centros de datos distintos.
3. El navegador abre TCP y TLS **con el borde**, que ve el pedido HTTP completo, ya descifrado.
4. Si el borde no puede responder solo, abre (o reutiliza) **otra** conexión hacia el origen y reenvía el pedido.

Hay dos conexiones independientes, con dos consecuencias. El origen ve la IP del borde, no la del usuario, y debe leer la IP real de una cabecera que agrega el proveedor (como `CF-Connecting-IP`). Y el proveedor ve todo el tráfico en claro: es una decisión de confianza que se toma explícitamente.

**Ejemplo:** un comercio en Mendoza a 120 ms de ida y vuelta (RTT) de `us-east-1`. Sin borde, TCP más TLS 1.3 cuestan unos 2 RTT, 240 ms, antes del primer byte. Con un borde a 10 ms, unos 20 ms, y la conexión borde-origen ya está abierta y se reutiliza.

**Por qué importa:** casi todo lo que sigue depende de que el tráfico pase por el borde; si el origen es alcanzable directamente, un atacante lo saltea. Más en [HTTP de punta a punta](#t/http).

### DNS: registros proxied y DNS-only

Cada registro DNS tiene un modo. **Proxied:** el DNS devuelve IPs del borde y el tráfico pasa por él, con todas las protecciones. **DNS-only:** devuelve la IP real del destino; el tráfico no pasa por el borde y no hay protección.

DNS-only tiene usos legítimos (correo, servicios que no son HTTP, registros de verificación). El riesgo es un registro DNS-only que apunta al mismo origen: `api-directa.rumbo.example` con la IP del balanceador revela el origen a cualquiera y permite enviar pedidos salteando el borde. Una revisión de DNS debería justificar cada registro DNS-only.

### Terminación TLS: certificado del borde, certificado del origen y modos

Hay dos tramos de TLS. En el tramo cliente-borde, el borde presenta un **certificado de borde** para `panel.rumbo.example`, que el proveedor emite y renueva. En el tramo borde-origen, el origen presenta el suyo: uno público (por ejemplo, de ACM en el ALB) o un **certificado de origen** emitido por el proveedor, que solo su borde reconoce.

El modo de cifrado define qué exige el borde en el segundo tramo (nombres a verificar en la documentación vigente):

| Modo | Borde-origen | Riesgo |
|---|---|---|
| Flexible | HTTP sin cifrar | Datos en claro por internet hasta el origen |
| Full | HTTPS sin validar el certificado | Un intermediario podría hacerse pasar por el origen |
| Full (strict) | HTTPS con certificado válido para el nombre | El recomendado |

El modo **flexible** es peligroso porque engaña: el usuario ve el candado, pero cookies de sesión y direcciones de destinatarios cruzan internet sin cifrar en el segundo tramo.

El paso siguiente es que el origen verifique que quien se conecta **es** el borde. Con **authenticated origin pulls**, el borde presenta un certificado de cliente (mTLS, TLS mutuo) y el origen rechaza cualquier conexión que no lo traiga. Aunque alguien descubra la IP del balanceador, no puede hablar con él.

**Ejemplo:** Rumbo configura `Full (strict)` con el certificado de ACM en el ALB, restringe el security group del ALB a los rangos de IP publicados por el proveedor y activa mTLS hacia el origen. Tres capas: cifrado validado, filtro de red y autenticación del borde.

### Caché en el borde

La caché del borde guarda respuestas bajo una **clave de caché** (por defecto, esquema, host, ruta y query string): dos pedidos con la misma clave reciben la misma respuesta.

Qué cachear en Rumbo: recursos estáticos con hash en el nombre (`app.3f9a1c.js`, fuentes), que pueden durar un año porque un cambio genera otro nombre; este manual y la documentación pública para comercios; y respuestas públicas iguales para todos, como las zonas de cobertura, con vida corta (5 minutos).

Qué no cachear nunca: respuestas con datos de un usuario o comercio (pedidos, destinatarios, conversaciones con el asistente). Si una respuesta personal entra en la caché con una clave que no incluye la identidad, el siguiente usuario recibe los datos del anterior: un incidente de privacidad.

Reglas prácticas:

1. **Respetar `Cache-Control` del origen:** `private, no-store` en todo lo personal, `public, max-age=...` en lo compartible. Las reglas del borde no deberían contradecir al origen.
2. **Bypass explícito** para `/api/*` y el endpoint del asistente.
3. **Purga:** al publicar un recurso sin hash en el nombre (el HTML del manual), se purga por URL o etiqueta. Purgar todo dispara una avalancha de pedidos al origen.

### WAF: reglas gestionadas y propias

Un **WAF** (web application firewall) inspecciona cada pedido HTTP y lo bloquea, lo desafía o lo deja pasar según reglas:

- **Reglas gestionadas:** mantenidas por el proveedor contra ataques conocidos (inyección SQL, XSS, vulnerabilidades publicadas) y actualizadas cuando aparece una nueva.
- **Reglas propias:** expresiones sobre campos del pedido, como "si el cuerpo de `/api/asistente` supera 32 KB, bloquear".

El problema práctico son los **falsos positivos**. Una regla contra inyección SQL puede bloquear la nota `"Dejar en portería; no tocar timbre -- llamar antes"`, porque `--` y `;` parecen SQL. Los mensajes al asistente, texto libre, son terreno fértil para esto.

Por eso las reglas nuevas se activan primero en modo **registro o simulación**: el WAF anota qué habría bloqueado sin bloquear. Se revisan una o dos semanas de registros, se agregan excepciones acotadas (por ruta y campo) y recién entonces se bloquea. Qué acciones ofrece cada plan cambia; verificar en la documentación vigente.

**Por qué importa:** el WAF frena ataques genéricos y masivos, pero no entiende la lógica de negocio ni la inyección de prompt. Es una capa, no la defensa principal (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

### Mitigación de DDoS: capa 3/4 y capa 7

Un **DDoS** (denegación de servicio distribuida) ataca desde muchas máquinas a la vez para agotar algún recurso:

- **Capa 3/4 (red y transporte):** inundaciones UDP, SYN o tráfico amplificado que buscan saturar ancho de banda o tablas de conexiones. El borde las absorbe por volumen: anycast reparte el ataque entre cientos de ubicaciones y, como el origen no está expuesto, nunca llega a AWS.
- **Capa 7 (aplicación):** pedidos HTTP que parecen legítimos, como miles de `GET /api/seguimiento?pedido=...` por segundo. El daño viene de la cantidad y de lo caro que es atender cada uno. Se mitigan con detección de patrones, desafíos, rate limiting y caché.

**Ejemplo:** 50.000 pedidos por segundo al endpoint del asistente: aunque el servicio aguantara, si cada uno llegara al LLM el costo sería enorme. El borde detecta la anomalía y desafía o limita antes de que el pedido toque el origen.

### Rate limiting: por IP, por clave y por usuario

El **rate limiting** cuenta pedidos por una clave durante una ventana de tiempo y rechaza los que superan el umbral. La clave define a quién se limita:

- **Por IP:** para tráfico anónimo (login, formularios públicos). Falla con usuarios que comparten IP (una oficina, una red móvil con NAT) y con atacantes que rotan IPs.
- **Por API key:** para integraciones de comercios, con un límite por clave según contrato.
- **Por usuario o tenant:** requiere identidad, así que suele aplicarse en el API gateway del origen, no en el borde.

Hay dos formas de contar:

- **Ventana fija:** se cuenta por minuto calendario. Simple, pero permite ráfagas en el borde de la ventana: con un límite de 60 por minuto, alguien envía 60 pedidos a las 10:00:59 y otros 60 a las 10:01:00, es decir, 120 en dos segundos.
- **Ventana deslizante:** se estima el conteo de los últimos 60 segundos en cada momento. Una aproximación común pondera la ventana anterior: `estimado = anterior × (1 − fracción transcurrida) + actual`.

**Ejemplo de cálculo:** límite de 60 por minuto. En el minuto anterior hubo 50 pedidos; en el actual van 20, y transcurrieron 15 segundos (25 %). Estimado: 50 × 0,75 + 20 = 57,5. El pedido 21 pasa. Si llegaran 3 más en el segundo 16, el estimado supera 60 y se rechazan. Con ventana fija, los 23 habrían pasado sin problema.

Un **token bucket**, que permite ráfagas acotadas, es otra alternativa común.

### Gestión de bots y Turnstile

No todo el tráfico automatizado es malo: buscadores, monitores de disponibilidad e integraciones de comercios son bots legítimos. La gestión de bots asigna a cada pedido una puntuación de probabilidad de automatización (por la huella del handshake TLS, el comportamiento, la reputación de la IP) y con ella se decide permitir, desafiar o bloquear.

**Turnstile** es la alternativa del proveedor a los CAPTCHA de rompecabezas: un widget que hace verificaciones en segundo plano y, en la mayoría de los casos, no le pide nada al usuario:

1. La página incluye el widget; el navegador completa la verificación y obtiene un token.
2. El formulario envía ese token junto con el pedido.
3. **Nuestro backend** valida el token contra la API del proveedor. Los tokens son de un solo uso y vencen en minutos (verificar en la documentación vigente). Si el backend no lo valida, el widget no protege nada.

Cuándo desafiar: en acciones baratas de pedir y caras de atender, como abrir una conversación anónima con el asistente público o registrarse. A usuarios autenticados no se los desafía en cada mensaje: su identidad y sus límites son mejores señales.

### Zero Trust: herramientas internas sin VPN

El modelo clásico pone las herramientas internas (Grafana, la consola del agente de operaciones) en una red privada con acceso por VPN. El problema es que la VPN da acceso a **la red**: una laptop comprometida puede intentar conectarse a todo.

**Zero Trust** reemplaza "estar en la red" por "demostrar identidad en cada pedido". Un **proxy consciente de identidad** delante de cada aplicación interna exige iniciar sesión con el proveedor de identidad de la empresa, verifica grupo, dispositivo y segundo factor, y solo entonces deja pasar, a esa aplicación y no a otra.

El complemento son los **túneles**: un agente liviano junto al origen abre una conexión **saliente** hacia el borde, y el tráfico entra por ella. El origen no necesita ningún puerto entrante abierto: no hay IP pública que escanear.

### Workers y cómputo en el borde

Los **Workers** son funciones que corren en cada ubicación del borde, antes de que el pedido llegue al origen, en entornos aislados livianos de arranque muy rápido. Sus límites de CPU, memoria y duración son más estrictos que los de un contenedor y dependen del plan (verificar en la documentación vigente).

Usos razonables: validar firma y expiración de un JWT y rechazar en el borde pedidos sin sesión válida (ver [Autenticación, JWT y OAuth](#t/autenticacion)); rutear `/v2/*` a otro origen; asignar variantes de una prueba A/B con una cookie; agregar cabeceras de seguridad o normalizar la clave de caché. Lo que no conviene: lógica de negocio pesada, consultas frecuentes a la base en `us-east-1` (cada una cruza el mundo) o procesos largos.

**Streaming de respuestas de LLM:** un Worker puede reenviar el cuerpo de la respuesta a medida que llega. La clave es devolver el stream tal cual; si lee el cuerpo completo antes de responder, el usuario ve todo de golpe al final.

**Gateway de IA en el borde:** el proveedor ofrece un servicio entre la aplicación y los proveedores de LLM que cachea respuestas idénticas, aplica límites, registra llamadas y mide costo, funciones parecidas a las del gateway interno de [LLMs en producción](#t/llms-produccion). Lo habitual es que el enmascarado de PII y los guardrails que dependen de nuestros datos queden en el gateway interno, y el borde aporte caché y límites cerca del usuario.

### Proteger los endpoints que usan agentes

Un endpoint de chat con LLM no es un endpoint REST típico: cada pedido puede costar miles de tokens, tarda segundos y consume capacidad limitada del proveedor. Uno sin límites permite a un atacante gastar nuestro presupuesto. Los controles se reparten entre borde y origen:

1. **Límites por usuario y por clave:** mensajes por minuto (por ejemplo, 10 por usuario y 300 por comercio) en el gateway del origen, más un límite por IP en el borde para tráfico anónimo.
2. **Presupuesto de tokens por usuario y tenant por día:** el gateway de LLM descuenta los tokens consumidos de cada comercio. Al llegar al 80 % avisa; al 100 % degrada a un modelo más chico o deriva a soporte humano.
3. **Detección de patrones de abuso:** uso automatizado (mensajes cada 2 segundos exactos, sin pausas de lectura), sondeo de inyección (muchas variantes de "ignora tus instrucciones", o el guardrail de entrada disparándose repetidamente para un usuario) y scraping (preguntas que recorren pedidos en secuencia: 1001, 1002, 1003...).
4. **Topes de costo:** tope de gasto diario global y por funcionalidad en el gateway, con kill switch, para que nadie lleve la factura del LLM a un número arbitrario.
5. **Respuestas claras:** `429 Too Many Requests` con `Retry-After`, para que el frontend muestre un mensaje y los clientes bien hechos esperen.

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{"error": "limite_mensajes", "detalle": "Superaste 10 mensajes por minuto. Intenta de nuevo en 45 segundos."}
```

**Ejemplo de cálculo (cifras hipotéticas):** sin límites, 100 sesiones automatizadas con 10 mensajes por minuto y 20.000 tokens por mensaje suman 20 millones de tokens por minuto; a 5 dólares por millón, 100 dólares por minuto. Con un presupuesto de 300.000 tokens por usuario y día, cada sesión se corta tras unos 15 mensajes (1,50 dólares), y como las sesiones anónimas exigen Turnstile y las autenticadas están atadas a una cuenta de comercio, el atacante no puede multiplicar sesiones a voluntad.

### Comparación con AWS

Rumbo corre en AWS, así que la alternativa natural es usar los servicios equivalentes de ese proveedor:

| Función | Cloudflare | AWS |
|---|---|---|
| CDN y caché en el borde | Red anycast con caché | CloudFront |
| WAF | WAF con reglas gestionadas y propias | AWS WAF (en CloudFront, ALB o API Gateway) |
| DDoS | Mitigación incluida en capa 3/4 y 7 | Shield Standard incluido; Shield Advanced con soporte especializado |
| Bots | Gestión de bots, Turnstile | Bot Control de AWS WAF, CAPTCHA y desafíos |
| Cómputo en el borde | Workers | CloudFront Functions y Lambda@Edge |
| Acceso sin VPN | Proxy de identidad y túneles | Verified Access, en parte |
| DNS | DNS con modos proxied y DNS-only | Route 53 |

Quedarse en AWS simplifica IAM, Terraform y la gestión de proveedores; un proveedor de borde especializado suele aportar más red, protecciones integradas y Zero Trust. Muchas organizaciones combinan ambos. El origen (VPC, balanceadores) se describe en [Fundamentos de AWS](#t/aws).

## Casos prácticos

### El origen expuesto por un registro viejo

**Situación:** con el WAF ya activo, un escaneo externo muestra pedidos que llegan al ALB sin pasar por el borde, gracias a un registro `legacy-api.rumbo.example` en modo DNS-only.
**Qué se hace:** se elimina el registro, el security group del ALB acepta solo los rangos del proveedor y se activa mTLS hacia el origen. A mediano plazo el tráfico entra por un túnel y el ALB deja de ser público. Un chequeo en CI falla si aparece un registro DNS-only sin justificación.

### El WAF bloquea a comercios legítimos

**Situación:** al activar reglas gestionadas en bloqueo, el 3 % de los mensajes al asistente fallan con 403: textos como `"piso 2 -- dpto B; select timbre 3"` parecen inyección SQL.
**Qué se hace:** se vuelve a modo registro, se analizan los bloqueos por regla y ruta y se agrega una excepción acotada: el campo `mensaje` de `/api/asistente` queda fuera de las reglas de inyección SQL (el backend usa consultas parametrizadas). El resto sigue activo, y cada regla nueva pasa dos semanas en registro antes de bloquear.

### Un script consume el asistente de soporte público

**Situación:** el asistente público de seguimiento (sin login, con número de pedido) recibe de madrugada miles de conversaciones desde unas 300 IPs que recorren números de pedido consecutivos. El costo diario del LLM se triplica.
**Qué se hace:** en el borde, Turnstile al abrir cada conversación y un límite de 5 conversaciones por hora por IP. En el origen, el asistente solo responde si número de pedido y código postal coinciden, sin revelar si el pedido existe. El gateway agrega un presupuesto diario global para el asistente público con alerta al 70 %. Las conversaciones automatizadas caen más del 95 %.

### Publicar la consola del agente de operaciones sin VPN

**Situación:** el equipo de operaciones necesita usar la consola del agente desde fuera de la oficina; la VPN actual da acceso a toda la red de producción.
**Qué se hace:** la consola, que corre en EKS sin balanceador público, se publica como `ops.rumbo.example` con un túnel y un proxy de identidad que exige grupo `operaciones`, segundo factor y dispositivo gestionado. Cada acceso queda registrado con la identidad, y quien deja la empresa pierde el acceso al desactivarse su cuenta, sin tocar reglas de red.

## Errores comunes

- **Usar el modo TLS flexible.** El candado del navegador oculta que el tramo hasta el origen viaja en claro; usar siempre validación estricta del certificado del origen.
- **Dejar el origen alcanzable directamente.** Sin restringir el balanceador a los rangos del proveedor, sin mTLS o sin túnel, cualquier protección del borde se puede saltear.
- **Cachear respuestas personales.** Una regla de caché amplia sobre `/api/*` puede servir datos de un comercio a otro; respetar `Cache-Control` y hacer bypass explícito de todo lo personal.
- **Activar reglas del WAF directamente en bloqueo.** Los falsos positivos sobre texto libre son frecuentes; pasar antes por modo registro y crear excepciones acotadas.
- **Limitar solo por IP los endpoints con LLM.** Los atacantes rotan IPs y los usuarios legítimos comparten IP; combinar con límites por usuario, por clave y presupuestos de tokens.

## Para discutir en equipo

- ¿Qué registros DNS tenemos hoy en modo DNS-only y cuál de ellos revela un origen que debería estar oculto?
- ¿Qué límites de mensajes y de tokens por usuario, por comercio y global serían razonables para el asistente, y qué experiencia debería ver un usuario que los alcanza?
- ¿Qué funciones del gateway de LLM tendría sentido mover al borde y cuáles deben quedarse cerca de nuestros datos?
- ¿Qué herramientas internas siguen dependiendo de la VPN y cuál sería la primera en pasar a acceso por identidad?
