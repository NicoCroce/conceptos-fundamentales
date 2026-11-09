---
slug: web-components
titulo: Web components
resumen: Estándares del navegador para crear elementos HTML propios y encapsulados, útiles para compartir interfaz entre frameworks y para widgets embebibles como un chat con agentes.
lectura: 13
---

## La idea central

Rumbo tiene tres frentes de interfaz que comparten piezas: el panel de comercios está hecho en React, la consola interna de operaciones usa otro stack (digamos Vue, heredado de un proyecto anterior) y además existe un widget de seguimiento que los comercios pegan en sus propias tiendas online para que el destinatario vea dónde está su pedido. Si el componente "estado del envío" se escribe en React, la consola no puede usarlo sin arrastrar React; y en la tienda del comercio no controlamos nada: ni el framework, ni el CSS, ni qué otros scripts corren en la página.

Los **web components** son un conjunto de estándares del navegador que permiten definir etiquetas HTML propias, como `<rumbo-estado-envio>`, con su comportamiento y sus estilos encapsulados. Para el navegador son elementos de verdad, igual que `<video>` o `<select>`: cualquier framework (o ninguno) puede usarlos. La analogía es un electrodoméstico con enchufe estándar: funciona en cualquier instalación y lo que pasa dentro de la carcasa no se mezcla con el resto. El caso más interesante hoy es el de un asistente con LLM embebido en sitios ajenos, que tiene que verse bien, aislarse del entorno y mostrar texto generado por un modelo sin abrir agujeros de seguridad.

## Conceptos

### Las tres piezas del estándar

"Web components" no es una sola API, sino tres que se combinan:

1. **Custom elements:** registrar una etiqueta nueva y asociarle una clase de JavaScript con su comportamiento.
2. **Shadow DOM:** darle al elemento un árbol DOM propio y aislado, con estilos que no salen ni entran.
3. **Templates y slots:** declarar estructura HTML reutilizable y definir huecos donde quien usa el componente inserta su propio contenido.

Ninguna requiere bibliotecas; las livianas como Lit solo reducen código repetitivo.

### Custom elements: definir y ciclo de vida

Un custom element es una clase que extiende `HTMLElement` y se registra con un nombre que **debe contener un guion** (así el navegador nunca choca con etiquetas futuras del estándar). El navegador llama a ciertos métodos en momentos concretos de la vida del elemento:

- `constructor()`: se crea la instancia. Aquí se inicializa estado, pero no se leen atributos ni se toca el DOM externo.
- `connectedCallback()`: el elemento se insertó en el documento. Es el lugar para renderizar, suscribirse a eventos o abrir conexiones.
- `disconnectedCallback()`: se quitó del documento. Aquí se limpian timers, listeners y conexiones; si no, quedan fugas de memoria.
- `attributeChangedCallback(nombre, viejo, nuevo)`: cambió uno de los atributos declarados en `observedAttributes`.

```js
class RumboEstadoEnvio extends HTMLElement {
  static observedAttributes = ["pedido-id", "estado"];

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback(nombre, viejo, nuevo) {
    if (viejo !== nuevo) this.render();
  }

  render() {
    const estado = this.getAttribute("estado") ?? "desconocido";
    this.textContent = `Pedido ${this.getAttribute("pedido-id")}: ${estado}`;
  }
}

customElements.define("rumbo-estado-envio", RumboEstadoEnvio);
```

```html
<rumbo-estado-envio pedido-id="P-1042" estado="en camino"></rumbo-estado-envio>
```

**Por qué importa:** la mayoría de los errores en custom elements vienen de hacer trabajo en el lugar equivocado del ciclo de vida, por ejemplo abrir un WebSocket en el constructor y no cerrarlo nunca en `disconnectedCallback`.

### Atributos frente a propiedades

Los **atributos** viven en el HTML y siempre son cadenas de texto: `estado="en camino"`. Las **propiedades** viven en el objeto JavaScript y pueden ser cualquier cosa: un número, un arreglo, un objeto. En un custom element, la sincronización entre ambos hay que escribirla.

La regla práctica es: datos simples y configurables desde HTML (un id, un tema, un idioma) como atributos que se reflejan en propiedades; datos ricos (la lista de 30 eventos de seguimiento de un pedido) solo como propiedades.

**Ejemplo:** `<rumbo-estado-envio pedido-id="P-1042">` se configura desde HTML, mientras que `elemento.eventos = [...]` recibe el historial completo desde el código del panel.

### Shadow DOM: encapsulación de estilos y DOM

Con `this.attachShadow({ mode: "open" })` el elemento obtiene una **shadow root**: un subárbol DOM separado del documento principal. Dos consecuencias:

1. **Los estilos no cruzan la frontera.** Un `button { background: red }` de la tienda del comercio no afecta los botones internos del widget, y un `p { margin: 0 }` del widget no rompe los párrafos de la tienda.
2. **El DOM interno no aparece en las consultas externas.** Un `document.querySelector(".mensaje")` desde la página no encuentra los mensajes del widget.

El modo `open` permite acceder a la shadow root desde afuera con `elemento.shadowRoot`; el modo `closed` devuelve `null`. El modo cerrado **no es una barrera de seguridad**: cualquier script que corre en la misma página puede interceptar `attachShadow` antes de que se llame, o leer lo que el componente pinta. Sirve para desalentar dependencias accidentales, no para proteger datos. En la práctica conviene `open`, porque facilita tests y herramientas de accesibilidad.

### Qué se filtra a través del Shadow DOM, y cómo personalizar

La encapsulación no es total, y eso es deliberado:

- **Propiedades heredadas** como `color`, `font-family`, `font-size` y `line-height` pasan del elemento anfitrión a su contenido interno. Si la tienda usa una serif de 18 px, el widget la hereda salvo que la fije.
- **Las custom properties de CSS** (variables como `--rumbo-color-acento`) también atraviesan la frontera. Son el mecanismo previsto para tematizar: el componente las usa por dentro y el comercio las define por fuera.
- **`::part()`** permite exponer partes internas con nombre. Si el componente marca `<button part="enviar">`, la página puede escribir `rumbo-asistente::part(enviar) { border-radius: 0 }`, y solo puede tocar lo que el componente expuso.

```css
/* En la tienda del comercio */
rumbo-asistente {
  --rumbo-color-acento: #0a6b4f;
  --rumbo-radio: 12px;
}
rumbo-asistente::part(cabecera) { font-weight: 600; }
```

**Por qué importa:** el diseño de un componente embebible incluye decidir su superficie de tematización: qué variables y qué partes se exponen. Es un contrato público, igual que una API (ver [Design systems para interfaces con agentes](#t/design-systems)), y cambiarlo rompe a quien lo usa.

### Templates y slots

Un `<template>` contiene HTML que el navegador parsea pero no muestra ni ejecuta: se clona cuando hace falta. Un `<slot>` dentro del Shadow DOM marca dónde aparece el contenido que el usuario del componente pone entre las etiquetas (los "hijos de luz", *light DOM*). Los slots pueden tener nombre y **contenido por defecto**, que se muestra si nadie llena el hueco.

```js
const plantilla = document.createElement("template");
plantilla.innerHTML = `
  <style>
    :host { display: block; font-family: var(--rumbo-fuente, system-ui); }
    header { color: var(--rumbo-color-acento, #2b4acb); }
  </style>
  <header part="cabecera"><slot name="titulo">Asistente de Rumbo</slot></header>
  <div class="mensajes" role="log" aria-live="polite"></div>
  <slot name="pie"></slot>
`;

class RumboAsistente extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" })
      .appendChild(plantilla.content.cloneNode(true));
  }
}
customElements.define("rumbo-asistente", RumboAsistente);
```

```html
<rumbo-asistente>
  <span slot="titulo">Consultas sobre tu envío</span>
</rumbo-asistente>
```

Aquí `innerHTML` se usa sobre una plantilla constante escrita por nosotros, sin datos externos: la única situación en la que es aceptable.

**Ejemplo:** el comercio A deja el título por defecto; el comercio B pone "Seguimiento de tu compra" sin tocar el código del componente.

### Eventos a través de la frontera

Un componente se comunica hacia afuera con eventos. `CustomEvent` permite adjuntar datos en `detail`, pero dos opciones deciden hasta dónde llega:

- `bubbles: true`: el evento sube por los ancestros del DOM.
- `composed: true`: el evento cruza la frontera del Shadow DOM hacia el documento. Sin esta opción, un evento disparado dentro de la shadow root muere en el elemento anfitrión.

```js
this.dispatchEvent(new CustomEvent("rumbo-herramienta", {
  detail: { nombre: "consultar_pedido", estado: "en_curso" },
  bubbles: true,
  composed: true,
}));
```

Cuando un evento cruza la frontera, el navegador lo **retargetea**: para quien escucha afuera, `event.target` es el elemento anfitrión, no el botón interno. Así no se filtran detalles de implementación.

**Por qué importa:** el panel puede escuchar `rumbo-herramienta` para registrar métricas sin conocer la estructura interna del widget.

### Formularios, foco y accesibilidad

Un `<input>` dentro de un Shadow DOM **no participa** del `<form>` de la página: al enviar el formulario, su valor no viaja. Para eso existen los **form-associated custom elements**: con `static formAssociated = true` y `this.attachInternals()`, el componente declara su valor, su validez y su estado, y el formulario lo trata como un control nativo.

La accesibilidad sigue las mismas reglas que cualquier HTML: usar elementos nativos por dentro (`<button>`, no un `<div>` con click), roles y atributos ARIA cuando haga falta, y un orden de foco razonable. La opción `delegatesFocus: true` en `attachShadow` hace que, al enfocar el anfitrión, el foco pase al primer elemento enfocable interno. Ojo: las referencias ARIA por id (`aria-labelledby`) no cruzan la frontera, así que etiqueta y control deben vivir del mismo lado.

### SSR, hidratación e interoperabilidad con frameworks

Los web components nacen en el cliente: hasta que el JavaScript se carga y llama a `customElements.define`, el navegador muestra una etiqueta desconocida, sin estilo. El **Declarative Shadow DOM** (`<template shadowrootmode="open">` dentro del HTML) permite que el servidor envíe el árbol interno ya armado, de modo que se vea antes de ejecutar JavaScript. Pero la integración con el renderizado en servidor de los frameworks (SSR, y la hidratación posterior) es más limitada y menos pulida que la de sus propios componentes.

En cuanto a interoperabilidad, los frameworks modernos consumen custom elements con poca fricción: React 19 pasa propiedades y escucha eventos personalizados de forma nativa, mientras que versiones anteriores solo pasaban atributos de texto y requerían envoltorios. Conviene verificar la versión de cada app consumidora antes de comprometerse.

### Cuándo conviene: comparación

| Criterio | Web components | Biblioteca de componentes de un framework |
|---|---|---|
| Portabilidad | Funciona en cualquier framework o sin ninguno | Atada a un framework y, a veces, a su versión |
| Aislamiento de estilos | Fuerte, por Shadow DOM | Depende de convenciones (CSS modules, prefijos) |
| Ecosistema | Más chico: menos componentes listos y menos herramientas | Muy amplio: tablas, formularios, gestión de estado |
| SSR e hidratación | Limitado; Declarative Shadow DOM ayuda | Maduro e integrado |
| Experiencia de desarrollo | Más verbosa sin una biblioteca como Lit | Reactividad, tipado y tooling integrados |
| Tematización | Custom properties y `::part`, explícitas | Flexible, pero el CSS externo puede filtrarse |
| Caso ideal en Rumbo | Widget embebible, piezas compartidas entre stacks | Aplicación completa en un solo stack (panel de comercios) |

La conclusión habitual: web components para **los bordes** (lo que se embebe en sitios ajenos o se comparte entre stacks distintos) y el framework del equipo para **el interior** de cada aplicación.

### El widget `<rumbo-asistente>`: streaming y salida del modelo

El asistente de soporte de Rumbo se ofrece a los comercios como una línea de HTML que pegan en su tienda. Por dentro, el componente abre una conexión de streaming con el backend (ver [HTTP de punta a punta](#t/http)) y recibe la respuesta del LLM en fragmentos. Tres reglas guían su diseño:

1. **El texto del modelo es no confiable.** Un LLM puede devolver `<img src=x onerror=...>` porque se lo pidió un usuario, porque lo trajo un documento recuperado por RAG o por una inyección de prompt (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)). Si eso se inserta con `innerHTML`, se ejecuta en la página del comercio. La regla es: texto plano con `textContent`; si se quiere markdown, se convierte a HTML y se pasa por un sanitizador con una lista corta de etiquetas permitidas (párrafos, listas, negritas, código, enlaces con esquema `https` únicamente).
2. **Agregar, no repintar.** Con cada fragmento se agrega un nodo de texto al mensaje en curso en lugar de reconstruir todo el contenido. Repintar 2.000 caracteres 200 veces por respuesta genera parpadeos y pierde la selección del usuario.
3. **Comunicar el estado de las herramientas.** Cuando el agente consulta el pedido, el widget muestra "Consultando el pedido P-1042..." y emite el evento `rumbo-herramienta` hacia la página, para que el comercio pueda reaccionar si quiere.

```js
agregarFragmento(mensajeEl, fragmento) {
  // Nunca innerHTML con texto del modelo.
  mensajeEl.append(document.createTextNode(fragmento));
}
```

**Por qué importa:** el widget corre con los permisos de la página del comercio. Un XSS a través de la respuesta del modelo no es un problema estético: es código arbitrario en el sitio de un cliente.

## Casos prácticos

### El mismo componente de seguimiento en tres stacks

**Situación:** el componente que muestra la línea de tiempo de un envío está duplicado en el panel React, en la consola de operaciones y en el widget. Las versiones divergieron: para el mismo evento, una muestra "retirado" y otra "en camino".

**Qué se hace:** se reescribe como `<rumbo-linea-tiempo>` con Lit, publicado como paquete interno. Recibe los eventos por propiedad y expone variables CSS para colores y tipografía. El panel React y la consola lo usan directamente; la lógica de qué texto corresponde a cada evento vive en un solo lugar. Se mantiene en React todo lo que es propio del panel (tablas, filtros, navegación), donde el ecosistema del framework aporta más.

### El CSS de la tienda rompía el widget

**Situación:** la primera versión del widget de seguimiento usaba clases con prefijo (`.rumbo-boton`) sin Shadow DOM. En una tienda con un reset agresivo (`* { all: unset }` en ciertas secciones) los botones desaparecían, y en otra el widget heredaba un `z-index` que lo dejaba debajo del menú.

**Qué se hace:** se migra a Shadow DOM con `:host { all: initial; display: block; }` para cortar también la herencia, y se define una superficie de tematización explícita: cuatro custom properties (acento, fondo, radio, fuente) y tres partes (`cabecera`, `mensaje`, `enviar`). Los comercios dejan de depender de selectores internos que se rompían con cada versión.

### Inyección de HTML a través de la respuesta del asistente

**Situación:** en una prueba interna, alguien escribe en el chat "repite exactamente este texto" seguido de una etiqueta `<img>` con un manejador `onerror`. El prototipo de `<rumbo-asistente>` renderizaba markdown con una biblioteca que deja pasar HTML crudo, y el script se ejecuta en la página de prueba.

**Qué se hace:** el renderizado de markdown pasa a hacerse en un solo lugar, con HTML crudo deshabilitado y un sanitizador con lista permitida de etiquetas y atributos; los enlaces se limitan a `https` y se abren con `rel="noopener noreferrer"`. Se agregan casos de evaluación con cargas maliciosas conocidas que corren en la CI del componente. Además, el widget se sirve con una política de seguridad de contenido recomendada para los comercios (ver [Seguridad en el frontend](#t/seguridad-frontend)) como segunda capa.

### Mostrar herramientas lentas sin dejar al usuario a ciegas

**Situación:** cuando el agente consulta el pedido y el clima de la zona, la respuesta tarda entre 4 y 8 segundos en empezar, y los usuarios reenvían la pregunta, duplicando la conversación y el gasto de tokens.

**Qué se hace:** el backend envía, dentro del mismo stream, eventos de estado de herramienta además de los fragmentos de texto. El widget muestra una línea discreta por herramienta ("Consultando el pedido...", "Revisando el clima en la zona norte...") que pasa a "listo" al terminar, deshabilita el botón de enviar mientras hay una respuesta en curso y ofrece un botón para detenerla. Los reenvíos duplicados caen a casi cero.

## Errores comunes

- **Usar `innerHTML` con texto del modelo o del usuario.** Abre la puerta a XSS en sitios de terceros; usar `textContent` o markdown sanitizado con lista permitida.
- **Creer que el modo `closed` protege datos.** Cualquier script de la página puede llegar al contenido; el modo cerrado solo desalienta dependencias, no es un control de seguridad.
- **Olvidar `composed: true` en eventos que deben salir del componente.** El evento nunca llega a la página y el equipo consumidor cree que el componente "no emite nada".
- **No limpiar en `disconnectedCallback`.** Conexiones de streaming y timers que siguen vivos al cerrar el widget consumen recursos y, en el caso del chat, tokens.
- **Pasar datos complejos como atributos JSON.** Lento y frágil; usar propiedades para objetos y arreglos.
- **Usar web components para toda una aplicación por moda.** En el interior de una app de un solo stack, el framework suele ofrecer mejor SSR, tooling y ecosistema.

## Para discutir en equipo

- ¿Qué piezas de nuestra interfaz se usan realmente en más de un stack, y cuáles solo creemos que se van a compartir?
- ¿Qué custom properties y partes debería exponer `<rumbo-asistente>`, y cómo versionamos esa superficie sin romper a los comercios?
- ¿Dónde debe vivir la sanitización de la salida del modelo: en el backend, en el componente o en ambos, y por qué?
- Si un comercio pide integrar el asistente en una app con renderizado en servidor, ¿qué limitaciones le comunicamos?
- ¿Qué eventos del widget conviene exponer a la página del comercio sin filtrar datos personales del destinatario?
