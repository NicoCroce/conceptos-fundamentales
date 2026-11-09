---
slug: responsive
titulo: Diseño responsive
resumen: Cómo construir interfaces que funcionen de un teléfono a un monitor ancho: mobile first, layouts fluidos, container queries, unidades relativas e imágenes adaptables.
lectura: 12
---

## La idea central

Rumbo tiene dos públicos con pantallas opuestas. Los transportistas usan la app en un teléfono, en la calle, con una mano, con sol de frente y señal irregular. Los comercios usan el panel en una computadora, con tablas de cien pedidos y el asistente abierto en un costado. El mismo código tiene que servir a los dos, y también al comercio que revisa un pedido desde el celular un domingo.

Diseño responsive no es "hacer una versión móvil". Es construir una interfaz que se reacomoda según el espacio disponible: los elementos fluyen, se apilan o se expanden, las imágenes llegan al tamaño necesario y el texto se puede leer sin zoom. La forma más sólida de lograrlo es empezar por la pantalla más chica y agregar complejidad a medida que hay lugar.

## Conceptos

### Mobile first

Mobile first significa escribir primero los estilos para la pantalla angosta y agregar reglas para pantallas anchas con `min-width`. Obliga a priorizar (en 360 px entra solo lo esencial, y esa jerarquía mejora también el escritorio) y deja estilos base simples, a los que las reglas siguientes suman columnas en lugar de deshacerlas.

```css
.panel { display: grid; gap: 1rem; }            /* base: una columna */
@media (min-width: 48rem) {                       /* ~768 px */
  .panel { grid-template-columns: 16rem 1fr; }    /* menú lateral + contenido */
}
```

**Por qué importa:** en Rumbo, el teléfono no es el caso secundario: es la herramienta de trabajo de cientos de transportistas.

### La etiqueta viewport

Sin indicación, los navegadores móviles simulan una pantalla de unos 980 px y achican la página para que entre, lo que deja el texto ilegible. Esta línea en el `<head>` les dice que usen el ancho real del dispositivo:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
```

`viewport-fit=cover` permite usar toda la pantalla en teléfonos con muesca, a cambio de respetar las áreas seguras (ver más abajo). No se debe agregar `maximum-scale=1` ni `user-scalable=no`: impide hacer zoom, que muchas personas necesitan para leer.

### Layouts fluidos con flexbox y grid

Un layout fluido usa proporciones y reglas de reparto, no anchos fijos en píxeles. **Flexbox** reparte elementos en una dirección (una fila de botones, un encabezado con título y acciones) y deja que pasen a la línea siguiente con `flex-wrap`. **Grid** organiza en dos dimensiones y puede calcular solo cuántas columnas entran:

```css
.lista-envios {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr));
  gap: 1rem;
}
```

**Ejemplo:** con columnas de mínimo 18 rem (288 px), en un teléfono de 375 px entra una columna; en una tablet de 768 px, dos; en un monitor de 1440 px con menú lateral, cuatro. Sin una sola media query.

Un detalle que causa muchos desbordes: un hijo de flexbox o grid no se achica por debajo del ancho de su contenido por defecto. Si contiene un bloque de código largo, empuja la página entera. Se corrige con `min-width: 0` en el hijo.

### Breakpoints elegidos por el contenido

Un **breakpoint** es el ancho a partir del cual cambia el layout. Copiar anchos de dispositivos populares envejece rápido; lo sólido es achicar la ventana despacio y cortar donde el contenido se rompe: líneas de más de 75 caracteres, una tabla que deja de entrar, dos columnas apretadas. Expresarlos en `rem` hace que respeten el tamaño de letra que eligió el usuario. En la práctica, dos o tres breakpoints alcanzan para casi todo.

### Media queries frente a container queries

Una **media query** pregunta por la ventana: "¿el viewport mide al menos 48 rem?". Sirve para el layout de la página. Pero un componente no sabe dónde lo van a poner: la ficha de un envío puede aparecer en la lista principal, que ocupa 900 px, o en el panel lateral del asistente, que ocupa 320 px, en la misma pantalla de escritorio. Con media queries, ambas versiones se verían igual porque la ventana es la misma.

Una **container query** pregunta por el contenedor del componente. Se declara el contenedor y el componente se adapta a él:

```css
.columna { container-type: inline-size; }

.envio { display: grid; gap: .5rem; }               /* angosto: todo apilado */
@container (min-width: 30rem) {
  .envio { grid-template-columns: 4rem 1fr auto; }  /* ancho: mapa, datos, estado */
}
```

**Ejemplo:** la ficha muestra miniatura del mapa, destinatario, ETA y estado. En el panel del asistente (320 px), se apila: estado arriba, destinatario y ETA debajo, sin mapa. En la lista principal (900 px), se acomoda en tres columnas. Es el mismo componente, sin variantes ni clases especiales según la ubicación.

| Aspecto | Media queries | Container queries |
|---|---|---|
| Pregunta por | El viewport (y preferencias del usuario) | El tamaño del contenedor |
| Uso típico | Layout de página, menú lateral, navegación | Componentes reutilizables |
| El componente funciona igual en cualquier lugar | No | Sí |
| Requiere declarar algo | No | `container-type` en un ancestro |
| Responde a modo oscuro o movimiento reducido | Sí | No |

Ambas conviven: media queries para la estructura de la página, container queries para los componentes de un [design system](#t/design-systems) o para [web components](#t/web-components) que se insertan en cualquier lugar.

### Unidades relativas y tipografía fluida

- **rem:** relativo al tamaño de letra de la raíz (16 px por defecto). Si el usuario configura 20 px, todo lo medido en rem crece con él. Es la unidad por defecto para tipografía y espaciado.
- **em:** relativo a la letra del propio elemento; útil para que el relleno de un botón escale con su texto.
- **%:** relativo al contenedor.
- **vw / vh:** 1% del ancho o alto del viewport. En móviles, `100vh` incluye la zona que tapan las barras del navegador, por eso un panel de alto completo queda cortado. **dvh** (alto dinámico) sigue el área visible real a medida que las barras aparecen y desaparecen; `svh` y `lvh` usan el alto con barras y sin ellas.

`clamp(mínimo, preferido, máximo)` permite que un tamaño crezca con la pantalla dentro de límites:

```css
h1 { font-size: clamp(1rem, 0.875rem + 0.5vw, 1.25rem); }
```

**Ejemplo:** con raíz de 16 px, `0.875rem` son 14 px. En un teléfono de 400 px, `0.5vw` son 2 px: 14 + 2 = 16 px, el mínimo. En un monitor de 1200 px, `0.5vw` son 6 px: 14 + 6 = 20 px, el máximo (1,25 rem). Entre ambos anchos, el tamaño crece de forma continua, sin saltos en cada breakpoint. Sumar una parte en `rem` al término preferido, en lugar de usar solo `vw`, mantiene el respeto por el zoom del usuario.

### Imágenes adaptables

Una foto de 1600 px de ancho puede pesar 350 KB; la misma a 480 px, unos 40 KB (cifras hipotéticas, dependen de la imagen y el formato). Enviar la grande a un teléfono que la muestra a 375 px desperdicia casi 90% de los bytes, en una red móvil.

`srcset` ofrece varias versiones y `sizes` le dice al navegador qué ancho ocupará la imagen, para que elija:

```html
<img src="comprobante-800.jpg"
     srcset="comprobante-480.jpg 480w, comprobante-800.jpg 800w, comprobante-1600.jpg 1600w"
     sizes="(min-width: 48rem) 40rem, 100vw"
     width="1600" height="1200" loading="lazy" alt="Foto del paquete entregado en la puerta">
```

En un teléfono de 375 px con densidad 2, la imagen ocupa 375 px y necesita unos 750 píxeles reales: el navegador elige la de 800w. `<picture>` agrega formatos modernos (AVIF, WebP, con JPEG de respaldo) y permite cambiar el recorte según el ancho. `loading="lazy"` difiere las imágenes fuera de pantalla, pero no se usa en la imagen principal visible al cargar, porque la retrasa.

Los atributos `width` y `height`, o la propiedad `aspect-ratio`, reservan el espacio antes de que la imagen llegue. Sin ellos, el contenido salta cuando la imagen carga (*layout shift*) y el usuario toca el botón equivocado.

### Pantallas táctiles, áreas seguras y orientación

Un dedo no es un puntero. WCAG 2.2 pide como mínimo 24 × 24 px por objetivo táctil, y las guías de las plataformas recomiendan alrededor de 44 a 48 px; para un transportista con guantes o en movimiento, más grande es mejor. `@media (hover: hover)` permite reservar los efectos al pasar el cursor para dispositivos que lo tienen, y `(pointer: coarse)` detecta pantallas táctiles para agrandar controles.

En teléfonos con muesca o barra de gestos, `env(safe-area-inset-bottom)` da el margen que hay que dejar para que un botón fijo abajo no quede debajo de la barra del sistema. Y la orientación puede cambiar en cualquier momento: un layout que solo se probó en vertical suele romperse en horizontal, donde el alto útil baja a 350 px o menos.

Un detalle frecuente en iOS: si un campo de texto tiene letra menor a 16 px, el navegador hace zoom al enfocarlo y la página queda desplazada.

### Preferencias del usuario

- `prefers-color-scheme`: claro u oscuro según el sistema. Con los colores definidos como variables CSS, el modo oscuro es redefinir esas variables, no duplicar estilos.
- `prefers-reduced-motion`: personas a las que las animaciones les causan mareo o distracción. Se reducen o eliminan transiciones, desplazamientos suaves y efectos de "escritura".

```css
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; scroll-behavior: auto !important; }
}
```

### Interfaces de agentes en pantallas chicas

Un chat con un asistente tiene problemas propios en un teléfono:

- **Texto que llega en streaming.** Cada fragmento nuevo puede mover el layout. Se fija el área de mensajes con `dvh`, se hace autoscroll solo si el usuario ya estaba al final (si subió a releer, no se lo arrastra) y se respeta `prefers-reduced-motion` en el cursor parpadeante o en la animación de escritura.
- **Indicadores de herramientas.** "Consultando el pedido", "buscando en políticas": en escritorio caben como una lista; en móvil conviene una sola línea con el paso actual y un control para expandir el detalle.
- **Tablas y código en las respuestas.** Un modelo puede devolver una tabla de diez columnas o una línea de log de 300 caracteres. Cada bloque va dentro de un contenedor con `overflow-x: auto`, para que se desplace solo ese bloque y no la página; las URLs largas se cortan con `overflow-wrap: anywhere`.
- **Campo de entrada y teclado virtual.** Al abrirse el teclado, el área visible se reduce a la mitad; el campo debe quedar visible y el botón de enviar, alcanzable con el pulgar.

En la app de transportistas, los flujos principales con el asistente son por voz y foto (ver [Modelos multimodales](#t/multimodal)): un botón grande para dictar "el destinatario no está, ¿qué hago?" y un `<input type="file" accept="image/*" capture="environment">` que abre directamente la cámara trasera para fotografiar el paquete. La foto se reduce en el propio teléfono antes de subirla: el modelo no necesita 12 megapíxeles para leer una etiqueta.

## Casos prácticos

### La respuesta del asistente rompe el panel en el teléfono

**Situación:** un comercio abre el panel en su celular y pregunta al asistente por los pedidos demorados. La respuesta incluye una tabla de seis columnas. Desde ese momento toda la página se desplaza en horizontal y el menú queda fuera de la pantalla.

**Qué se hace:** el diagnóstico es doble: la tabla no tenía contenedor propio con scroll y el mensaje era un hijo de flexbox sin `min-width: 0`, así que ensanchó toda la columna. Se envuelve cada tabla y bloque de código renderizado en un contenedor con `overflow-x: auto`, se agrega `min-width: 0` a los mensajes y una prueba automatizada que renderiza respuestas de ejemplo con tablas, código y URLs largas a 360 px y falla si el documento tiene scroll horizontal.

### La ficha de envío en dos lugares a la vez

**Situación:** el equipo agrega el detalle de envíos dentro del panel lateral del asistente. La ficha, diseñada con media queries para la lista principal, en el lateral de 320 px muestra tres columnas comprimidas e ilegibles, porque la ventana del escritorio sigue siendo ancha.

**Qué se hace:** se migra la ficha a container queries, como en el ejemplo de arriba. La lista principal y el panel lateral declaran `container-type: inline-size` y el componente decide su layout según el espacio que realmente tiene. Se elimina la variante "ficha compacta" que alguien había empezado a duplicar.

### Fotos de comprobante que consumen los datos del transportista

**Situación:** los transportistas reportan que la pantalla de historial del día tarda en cargar y que consume muchos datos móviles. Cada entrada muestra la foto del comprobante a 2.400 px, unos 900 KB, aunque se ve a 80 px de ancho.

**Qué se hace:** al subir la foto, un proceso genera versiones de 160, 480 y 1600 px en WebP. La lista usa `srcset` con `sizes="80px"`, lo que en un teléfono de densidad 2 trae la de 160 px (unos 12 KB hipotéticos); la vista ampliada usa la de 1600 px solo cuando se toca. Con 40 entregas por día, el historial pasa de unos 36 MB a menos de 1 MB. Se agrega `aspect-ratio` para que la lista no salte mientras las imágenes llegan y `loading="lazy"` para las que están fuera de pantalla.

### El panel del chat queda tapado por el teclado y la barra del navegador

**Situación:** en la app de transportistas, el chat con el asistente ocupa `height: 100vh`. En varios teléfonos el campo para escribir queda oculto bajo la barra del navegador, y al abrir el teclado el botón de enviar desaparece.

**Qué se hace:** se cambia a `height: 100dvh`, se agrega `padding-bottom: env(safe-area-inset-bottom)` al área de entrada y se sube la letra del campo a 16 px para evitar el zoom automático. Se prueba en dispositivos reales, en vertical y horizontal, con el teclado abierto, además del emulador del navegador. Ver también [Service workers y PWA](#t/pwa) para el caso en que la app se instala y corre a pantalla completa.

## Errores comunes

- **Diseñar para escritorio y "achicar" al final.** El móvil hereda reglas que hay que deshacer; se parte de la pantalla angosta y se agregan reglas con `min-width`.
- **Breakpoints copiados de modelos de teléfonos.** Quedan viejos y no reflejan el contenido; se ponen donde el layout se rompe, en `rem`.
- **Componentes que dependen del ancho de la ventana.** Fallan al reutilizarlos en un lateral o un modal; se usan container queries.
- **Usar `100vh` para paneles de alto completo en móvil.** La barra del navegador tapa una parte; se usa `dvh`.
- **Imágenes sin `srcset` ni dimensiones.** Se desperdician datos y la página salta al cargar; se ofrecen varias resoluciones y se reserva el espacio.
- **Bloquear el zoom o hacer objetivos táctiles chicos.** Excluye a quien necesita ampliar o tiene poca precisión; nunca `user-scalable=no` y objetivos de al menos 44 px en la app de calle.

## Para discutir en equipo

- ¿En qué anchos y dispositivos reales probamos hoy el panel y la app de transportistas, y quién lo hace antes de cada lanzamiento?
- ¿Qué componentes de nuestra interfaz se usan en más de un contexto y deberían pasar a container queries?
- ¿Cómo debería verse en un teléfono una respuesta del asistente con una tabla grande: scroll horizontal, tabla convertida en lista o un enlace a verla completa?
- ¿Qué presupuesto de bytes por pantalla le ponemos a la app de transportistas, y cómo lo medimos?
- ¿Cómo mostramos los pasos del agente en móvil sin que ocupen la mitad de la pantalla?
