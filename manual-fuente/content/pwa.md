---
slug: pwa
titulo: Service workers y PWA
resumen: Qué es un service worker, cómo se instala y se actualiza, qué estrategias de caché existen y cómo construir aplicaciones web que funcionan sin conexión.
lectura: 14
---

## La idea central

Un **service worker** es un script que el navegador instala por sitio y que se ubica entre la página y la red. Cada vez que la página pide algo (el HTML, una imagen, una llamada a la API), el service worker puede interceptar el pedido y decidir: responder desde una caché local, ir a la red, combinar ambas cosas o fabricar una respuesta. Es como un recepcionista: algunas consultas las responde con lo que tiene en el escritorio, otras las deriva adentro, y cuando el edificio está cerrado deja un cartel útil.

Una **PWA** (Progressive Web App) es una aplicación web que usa esa pieza, más un archivo de manifiesto, para comportarse como una aplicación instalada: abre sin conexión, tiene ícono propio, se lanza en su ventana y puede recibir notificaciones. Para Rumbo importa sobre todo en la app del transportista, que se usa con señal intermitente. Y afecta a las interfaces con agentes: un service worker mal configurado puede servir respuestas viejas del asistente o romper el streaming de tokens.

## Conceptos

### Qué es un service worker

1. **Corre en su propio hilo**, separado de la página. No tiene acceso al DOM; se comunica con las páginas mediante mensajes (`postMessage`).
2. **Tiene un alcance (scope).** Controla las páginas bajo la ruta desde donde se sirve: un `sw.js` en `/app/` controla `/app/pedidos` pero no `/admin/`.
3. **Exige HTTPS** (con la excepción de `localhost` para desarrollo). Un script que intercepta todo el tráfico de un sitio sería un regalo para un atacante en una red insegura.
4. **Es efímero y orientado a eventos.** El navegador lo despierta para atender un evento (`install`, `activate`, `fetch`, `push`, `sync`) y lo detiene cuando está ocioso. Lo que debe persistir va a Cache Storage o IndexedDB, nunca a variables globales.

**Por qué importa:** es la única pieza del navegador que permite que una aplicación web abra sin red. También es una pieza con mucho poder sobre lo que el usuario ve, y sus errores persisten en el dispositivo.

### Ciclo de vida

Es la parte que más sorprende y la fuente de casi todos los problemas:

1. **Registro.** La página llama a `navigator.serviceWorker.register('/sw.js')`.
2. **Instalación (`install`).** Una vez por versión del script; se precachean los archivos básicos. Si alguno falla, la versión se descarta.
3. **Espera (`waiting`).** Si una versión anterior controla pestañas abiertas, la nueva queda **en espera** mientras exista al menos una.
4. **Activación (`activate`).** Cerradas esas pestañas, la nueva se activa y borra las cachés viejas.
5. **Control de clientes.** Intercepta los pedidos de sus páginas. Una página abierta antes del primer registro no queda controlada hasta recargarse.

Dos atajos alteran este orden:

- `self.skipWaiting()` hace que la versión nueva se active sin esperar a que se cierren las pestañas.
- `clients.claim()` hace que la versión activa tome el control de las páginas abiertas de inmediato, sin recarga.

El problema de usarlos siempre: una pestaña que cargó el JavaScript de la versión 1 empieza a recibir archivos de la versión 2. Si el código viejo pide de forma diferida un fragmento (`chunk-a1b2.js`) que ya no existe, la pantalla se rompe a mitad de uso. El patrón prudente: la versión nueva espera, la página lo detecta y muestra un aviso ("Hay una versión nueva. Actualizar") y, solo cuando el usuario acepta, le pide que llame a `skipWaiting()` y recarga.

**Ejemplo:** el propio manual hace eso. Su service worker precachea `index.html`, las fuentes, el manifiesto y el ícono, con un nombre de caché que incluye un hash del contenido. Ante una versión nueva muestra el banner "Actualizar" y no recarga solo, para no interrumpir la lectura.

### Estrategias de caché

Dentro del evento `fetch` se elige, por tipo de recurso, una estrategia:

- **Cache first (primero caché):** si está en caché, se responde desde ahí; si no, se va a la red y se guarda. Para archivos que nunca cambian bajo el mismo nombre.
- **Network first (primero red):** se intenta la red; si falla o tarda más que un límite, se responde desde caché. Para datos que conviene tener frescos pero que sirven viejos antes que nada.
- **Stale-while-revalidate:** se responde de inmediato desde caché y en paralelo se pide a la red para actualizar la caché de la próxima vez. Para contenido donde unos minutos de atraso son aceptables.
- **Network only (solo red):** nunca caché. Para lo que no tiene sentido o es peligroso guardar.
- **Cache only (solo caché):** solo se responde desde lo precacheado durante la instalación.

| Estrategia | Velocidad percibida | Frescura | Funciona sin red | Uso típico en Rumbo |
|---|---|---|---|---|
| Cache first | Máxima | Baja (depende del versionado) | Sí, si está en caché | Fuentes, íconos, JS con hash |
| Network first | Depende de la red | Alta | Sí, con datos viejos | Entregas del día del transportista |
| Stale-while-revalidate | Máxima | Media (una visita de atraso) | Sí | Catálogos y configuración |
| Network only | Depende de la red | Total | No | Chat con el asistente, POST, login |
| Cache only | Máxima | Fija por versión | Sí | Cascarón de la app precacheado |

**Ejemplo:** con network first y un límite de 3 segundos, si la red tarda 8 segundos en el subsuelo de un edificio, al tercer segundo el transportista ve la lista guardada hace 20 minutos con un aviso "datos de las 14:05", en vez de una pantalla en blanco.

**Por qué importa:** no hay una estrategia correcta para todo el sitio. Elegir por tipo de recurso es la decisión de diseño central.

### Precaching y caché en ejecución

El **precaching** guarda, durante `install`, una lista fija de archivos conocida en el build (HTML principal, CSS, JavaScript, fuentes) y garantiza que la aplicación abra sin red desde la primera visita completa. La **caché en ejecución** (runtime caching) guarda lo que se va pidiendo durante el uso, según las reglas del evento `fetch`; como no se conoce de antemano, necesita límites de cantidad o de antigüedad para no crecer sin control.

**Ejemplo:** la app del transportista precachea unos 600 KB (hipotético) de cascarón; en ejecución guarda como máximo 50 fotos de comprobantes de entrega pendientes de subir y las respuestas de entregas de las últimas 24 horas.

### Versionado e invalidación

Cada versión usa un nombre de caché propio (`rumbo-transportista-v42` o un hash del contenido) y, en `activate`, borra las cachés con otro nombre; sin esa limpieza, cada despliegue suma megabytes al dispositivo. El navegador detecta una versión nueva comparando byte a byte el `sw.js`: si el HTML cambia pero `sw.js` no, no ve nada nuevo. Por eso el script incluye la versión o el hash de lo precacheado.

El problema más temido son usuarios atascados días en una versión vieja. Causas típicas:

1. **`sw.js` cacheado por HTTP.** Si el servidor o el CDN lo sirve con `Cache-Control: max-age=86400`, el navegador puede tardar en descubrir que hay versión nueva. Los navegadores actuales limitan el efecto, pero lo correcto es servir `sw.js` con `Cache-Control: no-cache` (o `max-age=0`) y dejar que los recursos con hash en el nombre tengan caché larga. Cómo funcionan esas cabeceras se ve en [HTTP de punta a punta](#t/http).
2. **Pestañas que nunca se cierran.** Si la app queda abierta toda la jornada y nadie muestra el aviso, la versión nueva queda en `waiting` indefinidamente.
3. **HTML en cache first.** Si el documento principal nunca se pide a la red, nunca se descubren los archivos nuevos.

Como último recurso existe un "service worker de emergencia": publicar en la misma ruta un `sw.js` que no intercepta nada, borra las cachés y se desregistra. Conviene tenerlo escrito y probado antes de necesitarlo.

### Modo sin conexión y alternativas

Sin conexión hay que decidir qué ve el usuario en cada caso:

- **Página alternativa sin conexión:** para navegaciones a rutas no cacheadas, una página precacheada que explica qué se puede hacer sin red.
- **Datos viejos con fecha visible:** siempre indicando a qué hora corresponden.
- **Acciones en cola:** lo que el usuario hace sin red se guarda localmente y se envía al volver la conexión.

Esta última es la más delicada. Si el transportista marca "entregado" sin señal, la acción se guarda en IndexedDB con una **clave de idempotencia** generada en el dispositivo (por ejemplo un UUID). Al reconectar se envía; si la red se corta justo después de que el servidor la procesó y el cliente reintenta, el servidor reconoce la clave y no registra dos entregas. Es el mismo principio que en las herramientas de un agente que modifican estado.

### Almacenamiento y cuotas

- **Cache Storage:** pares pedido-respuesta HTTP. Lo natural para archivos y respuestas de red.
- **IndexedDB:** base de datos local de objetos, con índices y transacciones. Lo natural para datos estructurados: la cola de acciones pendientes, borradores, notas.
- **localStorage:** síncrono, pequeño y no disponible dentro del service worker. No sirve para esto.

Cada navegador asigna una cuota por origen (en general, una fracción del disco libre) y, si el dispositivo se queda sin espacio, puede **desalojar** todo el almacenamiento de los sitios menos usados de una vez; algunos también lo borran en sitios que no se visitan durante cierto tiempo. `navigator.storage.estimate()` informa uso y cuota; `navigator.storage.persist()` pide que el origen no sea desalojado automáticamente, y el navegador puede concederlo o no.

**Por qué importa:** una cola de acciones sin enviar es justamente el dato que no se puede perder. Hay que pedir persistencia, mostrar al usuario cuántas acciones están pendientes y no confiar en que el almacenamiento local es para siempre.

### Manifiesto e instalación

El **web app manifest** es un JSON enlazado desde el HTML que describe la aplicación instalada:

- `name`, `short_name` e `icons`: nombres e íconos en varios tamaños (por ejemplo 192 y 512 px), idealmente con una variante "maskable" que tolera recortes circulares.
- `start_url`: qué se abre al tocar el ícono.
- `display`: `standalone` (ventana propia, sin barra del navegador), `minimal-ui`, `fullscreen` o `browser`.
- `scope`: qué rutas pertenecen a la aplicación; navegar fuera abre el navegador común.

En Android y en navegadores de escritorio basados en Chromium, con HTTPS, manifiesto válido e ícono, el navegador ofrece instalar la aplicación. En iOS la instalación se hace desde el menú de compartir ("Agregar a pantalla de inicio"), sin un aviso automático equivalente, y algunas funciones (notificaciones, almacenamiento duradero) llegaron más tarde o con más restricciones. Conviene verificar el soporte vigente antes de prometer una función a usuarios de iPhone.

### Notificaciones push y sincronización en segundo plano

Las **notificaciones push** permiten avisar aunque la aplicación esté cerrada. El recorrido:

1. La página pide permiso al usuario para mostrar notificaciones.
2. Si acepta, el navegador crea una suscripción con el **servicio push** del navegador (operado por el fabricante) y devuelve un endpoint y claves.
3. El backend de Rumbo guarda la suscripción y, cuando hay algo que avisar, envía un mensaje cifrado a ese endpoint, firmado con sus claves VAPID.
4. El servicio push lo entrega al dispositivo; el navegador despierta al service worker con un evento `push` y este muestra la notificación.

El contenido del mensaje tiene un límite del orden de pocos kilobytes: se envía un aviso corto y la app busca el detalle al abrirse. Y pedir permiso al cargar la página produce rechazos casi automáticos; conviene pedirlo después de una acción que lo justifique ("Avisarme cuando me asignen un pedido").

La **sincronización en segundo plano** (Background Sync) dispara un evento `sync` cuando vuelve la conexión, aunque la pestaña esté cerrada. Su soporte no es universal, así que la cola debe funcionar también sin ella: reintentar al abrir la app y al detectar el evento `online`.

### Trampas frecuentes

- **Respuestas de API con datos personales en caché.** Nombre, teléfono y dirección quedan en el disco, al alcance de quien use ese navegador después; al cerrar sesión hay que borrar cachés y bases locales.
- **Redirecciones en el precache.** El navegador puede rechazar servir un redirect cacheado para una navegación; se precachea la URL final.
- **Respuestas opacas.** Un recurso de otro origen pedido sin CORS es "opaco": no se ve su estado (puede ser un error cacheado) y cuenta en la cuota con un tamaño ficticio grande. Cachear de otros orígenes solo con CORS.

### Service workers en interfaces con agentes

Tres reglas para el asistente de Rumbo y cualquier chat con un LLM:

1. **Nunca cachear respuestas del modelo.** Depende del momento, del usuario y del estado del pedido; la respuesta de ayer es hoy un dato falso dicho con confianza. Las rutas del chat van en network only.
2. **No interferir con el streaming.** Las respuestas se envían por partes (SSE o fetch con streams). Si el service worker hace `await response.text()` para guardarla, el usuario no ve nada hasta el final. Lo más simple es no llamar a `respondWith` en esas rutas.
3. **Acciones del agente sin conexión: en cola, no en ejecución.** Si el transportista le pide al asistente "marca la entrega 4512 como fallida, no había nadie", sin red la app no simula que el agente la ejecutó: queda pendiente, con clave de idempotencia, hasta que el backend la procesa. Los límites de qué puede hacer un agente se discuten en [Seguridad de LLMs y agentes](#t/seguridad-agentes).

## Casos prácticos

### Entregas marcadas sin señal

**Situación:** en edificios con subsuelo, el 7 % (hipotético) de los "entregado" fallaban porque la petición se hacía sin red, y el transportista repetía la acción hasta que funcionaba, a veces creando registros duplicados.

**Qué se hace:** la acción se guarda en IndexedDB con un UUID como clave de idempotencia y la interfaz responde al instante. Se reintenta con espera exponencial al abrir la app, al detectar `online` y, donde existe, con Background Sync; el servidor deduplica por clave. Se pide `storage.persist()`, se muestra un contador de pendientes y se advierte si alguien cierra sesión con acciones sin enviar.

### Usuarios atascados en una versión vieja

**Situación:** tras un despliegue del panel de comercios, un tercio de los usuarios sigue viendo la versión anterior tres días después, y algunos ven errores porque el JavaScript viejo llama a un endpoint que cambió.

**Qué se hace:** se encuentra que el CDN servía `sw.js` con un día de caché y que el panel quedaba abierto todo el día. Se configura `Cache-Control: no-cache` para `sw.js`, se agrega el banner "Hay una versión nueva" que activa la espera solo al aceptar, y el backend mantiene la versión anterior del endpoint durante dos semanas para que los clientes viejos no se rompan mientras se actualizan.

### El asistente respondía con datos de ayer

**Situación:** el chat de soporte del panel parecía responder "rápido" sobre el estado de un pedido, pero con información desactualizada. La regla del service worker aplicaba stale-while-revalidate a todo `/api/`.

**Qué se hace:** se reemplaza la regla genérica por reglas explícitas por ruta. `/api/asistente/` y toda petición con método distinto de GET quedan en network only y fuera de `respondWith`, lo que además restituye el streaming de tokens. Se agrega una prueba automática que verifica que ninguna respuesta del chat aparece en Cache Storage.

### Dispositivo compartido entre turnos

**Situación:** en un depósito, dos transportistas comparten una tableta. Tras cerrar sesión, el segundo puede ver en modo sin conexión la lista de direcciones y teléfonos del primero.

**Qué se hace:** las respuestas con datos personales pasan a guardarse en una caché separada por usuario, que se borra completa al cerrar sesión junto con las bases de IndexedDB del usuario. La lista sin conexión muestra solo lo necesario para la ruta del día.

## Errores comunes

- **Llamar a `skipWaiting()` siempre por defecto.** Rompe pestañas abiertas que mezclan código de dos versiones; mejor un aviso que el usuario acepta.
- **Servir `sw.js` con caché HTTP larga.** Retrasa el descubrimiento de versiones nuevas; servirlo con `no-cache` y usar hashes en el resto.
- **Una sola estrategia para todo el sitio.** El HTML, los archivos con hash, los datos y el chat necesitan reglas distintas.
- **Cachear respuestas con datos personales o del LLM.** Quedan en el dispositivo o se sirven desactualizadas; network only para el chat y limpieza al cerrar sesión.
- **Cola de acciones sin idempotencia.** Los reintentos crean duplicados; cada acción lleva una clave generada en el dispositivo.
- **No tener un plan para desactivar el service worker.** Un error que se instala en miles de dispositivos necesita un `sw.js` de emergencia ya probado.

## Para discutir en equipo

- ¿Qué acciones de la app del transportista deberían poder hacerse sin conexión y cuáles conviene bloquear hasta tener red?
- Si el asistente pudiera ejecutar acciones desde la app del transportista, ¿cómo mostramos la diferencia entre "pedido al agente", "en cola" y "hecho"?
- ¿Cuánto tiempo aceptamos que un usuario use una versión vieja del panel, y cómo lo medimos?
- ¿Qué datos personales están hoy en Cache Storage o IndexedDB de nuestros usuarios, y quién lo revisó?
