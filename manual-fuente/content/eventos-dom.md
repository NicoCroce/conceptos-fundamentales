---
slug: eventos-dom
titulo: Eventos y event listeners
resumen: Cómo el navegador propaga eventos por el DOM, cómo escucharlos sin fugas ni trabajo de más, y cómo usarlos para interfaces que reciben respuestas de agentes en streaming.
lectura: 15
---

## La idea central

Casi todo lo que hace una página web es reaccionar: un clic, una tecla, el scroll, un mensaje que llega del servidor. El navegador representa cada uno de esos hechos como un **evento** y lo entrega a las funciones que se registraron para escucharlo, los **event listeners**. Entender por dónde viaja un evento, quién puede frenarlo y cuándo deja de escucharse un listener explica una familia entera de bugs: el clic que dispara dos acciones, la lista que se vuelve lenta, el chat que sigue escribiendo después de cerrarse.

La analogía es la del sistema de avisos de un centro de distribución de Rumbo. Cuando un paquete se cae en el muelle 4, el aviso sale del muelle, pasa por el supervisor del sector y llega a la oficina central. Cualquiera en ese camino puede reaccionar, y alguien puede decir "ya lo resolví, no sigan avisando". Los eventos del DOM funcionan así, con un recorrido fijo y reglas para cortarlo.

## Conceptos

### El modelo de eventos del navegador

El navegador tiene un solo hilo principal para la página. Cuando ocurre algo (el usuario hace clic, llega un mensaje por la red, vence un temporizador), el navegador pone una tarea en una cola. El **event loop** toma tareas de a una y, para cada evento, ejecuta en orden todos los listeners que corresponden. Mientras un listener corre, nada más corre: ni otro listener, ni el dibujo de la pantalla.

**Ejemplo:** si un listener de `input` en el buscador de envíos tarda 120 ms en filtrar 8.000 filas, durante esos 120 ms la página no dibuja la tecla siguiente. A 60 cuadros por segundo hay unos 16 ms por cuadro, así que se pierden 7.

**Por qué importa:** un listener lento no es un problema local; bloquea toda la página.

### addEventListener y sus opciones

`addEventListener(tipo, listener, opciones)` registra una función. El tercer argumento acepta un objeto con cuatro opciones:

- **`once: true`:** el listener se quita solo después de la primera ejecución.
- **`passive: true`:** promete que el listener no va a llamar a `preventDefault()`. El navegador puede hacer scroll sin esperar a que el listener termine. Si dentro de uno pasivo se llama a `preventDefault()`, se ignora.
- **`capture: true`:** el listener corre en la fase de captura, de afuera hacia adentro (se explica más abajo).
- **`signal`:** un `AbortSignal`; cuando se aborta, el listener se quita. Es la forma moderna de limpiar.

```ts
const ctrl = new AbortController();
lista.addEventListener("click", alHacerClic, { signal: ctrl.signal });
window.addEventListener("scroll", alDesplazar, { passive: true, signal: ctrl.signal });
// más tarde, una sola línea quita ambos
ctrl.abort();
```

**Ejemplo:** un listener de `touchmove` no pasivo que tarda 30 ms hace que el scroll en el teléfono del transportista se trabe 30 ms en cada movimiento. Con `passive: true` el scroll arranca de inmediato.

**Por qué importa:** las opciones correctas evitan scroll trabado y listeners olvidados sin código extra.

### El objeto evento

Cada listener recibe un objeto con información del hecho. Los campos que más se usan:

- **`target`:** el elemento donde se originó el evento (el ícono dentro del botón, por ejemplo).
- **`currentTarget`:** el elemento cuyo listener se está ejecutando ahora. Cambia a medida que el evento viaja.
- **`isTrusted`:** verdadero si lo generó el usuario y no un `dispatchEvent` del código.

**Ejemplo:** en un botón "Reprogramar" con un ícono y un texto, un clic sobre el ícono tiene `target` igual al `<svg>` y `currentTarget` igual al `<button>`. El código que lee `event.target.dataset.envioId` falla según dónde caiga el clic; el que lee `currentTarget` o usa `closest` no.

**Por qué importa:** confundir `target` con `currentTarget` produce bugs que aparecen "a veces", según el píxel exacto del clic.

### Fases: captura, objetivo y burbujeo

Un evento que se origina en un elemento no ocurre solo ahí. Recorre el árbol en tres fases. Paso a paso, para un clic en el botón "Contactar" de la tercera fila de la tabla de envíos:

1. **Captura.** El evento baja desde `window` hacia el elemento: `window` → `document` → `<html>` → `<body>` → `<main>` → `<table>` → `<tr>` → `<button>`. Corren los listeners registrados con `capture: true`.
2. **Objetivo.** Llega al `<button>`. Corren sus listeners.
3. **Burbujeo.** El evento sube por el mismo camino al revés: `<tr>` → `<table>` → `<main>` → ... → `window`. Corren los listeners normales (sin `capture`).

Si la fila tiene un listener que abre la ficha del envío y el botón uno que abre el chat con el transportista, un clic en el botón ejecuta ambos: primero el del botón, después el de la fila. No todos los eventos burbujean: `focus` y `blur` no lo hacen (sus versiones `focusin` y `focusout` sí), ni `mouseenter`, ni `scroll` en elementos.

**Ejemplo:** un listener de analítica registrado en captura sobre `document` ve todos los clics, aunque algún componente frene el burbujeo.

**Por qué importa:** casi todos los efectos dobles ("abre la ficha y además el chat") se explican mirando el recorrido del evento.

### stopPropagation frente a preventDefault

Son dos cosas independientes que suelen confundirse:

| Método | Qué hace | Ejemplo |
|---|---|---|
| `preventDefault()` | Cancela la acción por defecto del navegador. El evento sigue viajando. | Que un formulario no recargue la página al enviarse; que Enter no agregue un salto de línea |
| `stopPropagation()` | Frena el viaje del evento hacia los siguientes elementos. La acción por defecto sigue. | Que el clic en "Contactar" no llegue a la fila |

`stopPropagation` debería ser la excepción. Frenar el burbujeo rompe a quien escuche más arriba: analítica, cierre de menús, atajos globales. La alternativa suele ser que el listener de la fila ignore los clics que vienen de un control interactivo.

```ts
fila.addEventListener("click", (e) => {
  if ((e.target as Element).closest("button, a, input")) return;
  abrirFicha(fila.dataset.envioId!);
});
```

**Ejemplo:** un `stopPropagation` en el botón "Contactar" hizo que el menú desplegable de la fila dejara de cerrarse al hacer clic en el botón, porque el menú escuchaba clics en `document`.

**Por qué importa:** frenar la propagación es una decisión global disfrazada de local.

### Delegación de eventos

Como los eventos burbujean, en lugar de poner un listener en cada elemento se puede poner **uno solo en el contenedor** y averiguar, con `event.target.closest(...)`, sobre qué hijo ocurrió. Es la **delegación de eventos**.

```ts
tabla.addEventListener("click", (e) => {
  const boton = (e.target as Element).closest<HTMLButtonElement>("button[data-accion]");
  if (!boton || !tabla.contains(boton)) return;
  const id = boton.closest("tr")!.dataset.envioId!;
  acciones[boton.dataset.accion!](id); // "reprogramar" | "contactar" | "ver"
});
```

Las cuentas, como orden de magnitud: la tabla de la consola muestra 8.000 envíos con 3 botones por fila. Con un listener por botón son 24.000 listeners, cada uno con su closure que retiene el id del envío. Si cada par listener más closure ocupa del orden de 100 a 200 bytes, son entre 2,4 y 4,8 MB solo en listeners. Con delegación es 1 listener, un par de cientos de bytes, y las filas que se agregan después funcionan sin registrar nada.

**Ejemplo:** al aplicar delegación en la tabla, el cambio de filtro de "todas las zonas" a "zona norte" pasó de 180 ms a 40 ms en una laptop de gama media, porque ya no había que registrar y quitar miles de listeners.

**Por qué importa:** la delegación escala con la cantidad de tipos de acción, no con la cantidad de filas, y funciona con contenido dinámico.

### Eventos personalizados

Un componente puede crear sus propios eventos con `CustomEvent` y dispararlos con `dispatchEvent`. Los datos van en `detail`. Por defecto un evento propio no burbujea; hay que pedirlo.

```ts
this.dispatchEvent(new CustomEvent("envio-seleccionado", {
  detail: { envioId: "P-1042" },
  bubbles: true,
  composed: true, // cruza el Shadow DOM
}));
```

Las opciones `bubbles` y `composed`, y el retargeting al cruzar la frontera del Shadow DOM, se explican en [Web components](#t/web-components). Dos reglas de diseño adicionales: el nombre del evento lleva un prefijo propio (`rumbo-`) para no chocar con eventos nativos o de otras bibliotecas, y `detail` lleva identificadores, no objetos con datos personales, porque cualquier código de la página que escuche en `document` lo recibe.

**Ejemplo:** el widget `<rumbo-asistente>` emite `rumbo-herramienta` con `{ nombre: "consultar_envio", estado: "completada" }`. La página del comercio puede escucharlo para actualizar su propia vista, sin recibir el teléfono del destinatario.

**Por qué importa:** los eventos personalizados son la API de salida de un componente; se diseñan con el mismo cuidado que sus props.

### Quitar listeners y evitar fugas de memoria

Un listener retiene su función y todo lo que ella usa (su closure). Mientras esté registrado en algo que sigue vivo, como `window` o una conexión abierta, nada de eso se libera aunque el componente ya no esté en pantalla: es una **fuga de memoria**.

`removeEventListener` exige pasar exactamente la misma función y la misma opción `capture` con que se registró, lo que falla a menudo con funciones flecha creadas en el momento. La solución moderna es un `AbortController` por ciclo de vida: todos los listeners del componente se registran con su `signal` y se quitan con un solo `abort()`.

```ts
class PanelSeguimiento {
  #ctrl = new AbortController();
  montar() {
    const { signal } = this.#ctrl;
    window.addEventListener("resize", this.#ajustar, { signal });
    document.addEventListener("keydown", this.#atajos, { signal });
    fuente.addEventListener("posicion", this.#mover, { signal });
  }
  desmontar() { this.#ctrl.abort(); }
}
```

**Ejemplo:** un operador abre y cierra la ficha de envío 300 veces en un turno. Si cada apertura deja un listener de `resize` que retiene la ficha (unos 2 MB con el mapa), al final del turno hay del orden de 600 MB retenidos y la pestaña se vuelve inutilizable.

**Por qué importa:** las fugas por listeners no fallan en las pruebas cortas; aparecen en la sexta hora de un turno de operaciones.

### Eventos en React y limpieza en efectos

React no registra un listener por cada `onClick`. Usa delegación: registra los listeners en la raíz donde se montó la aplicación y, cuando llega un evento nativo, recorre su propio árbol y llama a los manejadores. El manejador recibe un **evento sintético**, un envoltorio con la misma interfaz en todos los navegadores (`nativeEvent` da acceso al original). Diferencias con el DOM: `onChange` se dispara en cada tecla, como el nativo `input`, y la captura se pide con `onClickCapture`.

Para lo que React no cubre (eventos de `window`, `document`, un `EventSource`, un widget externo), se usa un efecto con limpieza, como explica [React](#t/react). El `AbortController` encaja bien:

```tsx
useEffect(() => {
  const ctrl = new AbortController();
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") cerrarPanel();
  }, { signal: ctrl.signal });
  return () => ctrl.abort();
}, [cerrarPanel]);
```

**Ejemplo:** en modo estricto, React monta, desmonta y vuelve a montar cada componente en desarrollo. Un efecto sin limpieza deja dos listeners de `Escape` y el panel intenta cerrarse dos veces: el error aparece antes de llegar a producción.

**Por qué importa:** la mitad de las fugas en apps React vienen de efectos que registran algo y no lo quitan.

### Debounce y throttle

Algunos eventos llegan en ráfagas: `scroll` y `pointermove` pueden dispararse en cada cuadro (60 veces por segundo o más), `resize` decenas de veces durante un arrastre, `input` en cada tecla. Dos técnicas limitan cuántas veces se hace el trabajo caro:

- **Debounce:** espera a que la ráfaga termine. Cada evento reinicia un temporizador; el trabajo corre cuando pasan N ms sin eventos.
- **Throttle:** como máximo una vez cada N ms, aunque los eventos sigan llegando.

| Evento | Técnica | Número de referencia |
|---|---|---|
| Escribir en el buscador o el chat | Debounce | 250 a 400 ms |
| Scroll para cargar más o marcar "leído" | Throttle | 100 a 200 ms |
| Resize para recalcular el mapa | Debounce | 150 a 250 ms |
| Arrastre o animación ligada al puntero | `requestAnimationFrame` | Una vez por cuadro |

```ts
function debounce<A extends unknown[]>(fn: (...a: A) => void, ms: number) {
  let t: ReturnType<typeof setTimeout> | undefined;
  return (...a: A) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}
```

**Ejemplo:** el buscador de la consola sugiere consultas al agente de operaciones. Un operador escribe "demoras zona norte" (18 caracteres) a unas 5 teclas por segundo. Sin debounce son 18 peticiones al backend, varias de las cuales llaman a un modelo. Con 300 ms de debounce, como hay pausas solo entre palabras, son 3 o 4 peticiones, y la última es la única que importa. Para el scroll, 10 segundos a 60 eventos por segundo son 600 ejecuciones; con throttle de 100 ms, 100.

**Por qué importa:** en interfaces conectadas a un LLM, cada evento de más puede ser una llamada de más, con su latencia y su costo en tokens.

### Teclado y accesibilidad

Una interfaz que solo responde al mouse deja afuera a quien usa teclado o lector de pantalla. Lo básico:

- **`key` frente a `code`.** `key` es el carácter producido ("Enter", "a"); `code` es la tecla física ("KeyA"). Para atajos con letras se usa `key`, que respeta la distribución del teclado.
- **Elementos nativos.** Un `<button>` ya responde a Enter y Espacio y es enfocable. Un `<div>` con `onClick` no.
- **Composición de texto.** Al escribir con un método de entrada (por ejemplo, para japonés o con acentos compuestos), Enter confirma la palabra, no el mensaje. El chat debe ignorar Enter si `event.isComposing` es verdadero.

```ts
campo.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey && !e.isComposing) {
    e.preventDefault(); // no agrega salto de línea
    enviarMensaje();
  }
});
```

**Ejemplo:** el campo del asistente enviaba palabras a medias con métodos de entrada de otros idiomas; la condición de `isComposing` lo resolvió.

**Por qué importa:** los eventos de teclado bien manejados hacen el producto usable para más personas y más rápido para quienes lo usan todo el día.

### Eventos para respuestas de agentes en streaming

La respuesta de un agente llega por partes: texto, estados de herramientas, pedidos de aprobación y un fin. Con [Server-Sent Events](#t/http), el navegador ofrece `EventSource`:

- Cada bloque `data:` del servidor sin nombre llega como evento `message`.
- Si el servidor escribe `event: herramienta`, llega como un evento con ese nombre, que se escucha con `addEventListener("herramienta", ...)`. `onmessage` no lo ve.
- Si la conexión se corta, `EventSource` reconecta solo y manda el último `id` recibido en la cabecera `Last-Event-ID`, para que el servidor retome sin repetir tokens.

`EventSource` solo hace GET y no permite cabeceras propias, así que muchos chats usan `fetch` con un stream de lectura y un `AbortSignal`, y despachan internamente los mismos tipos de evento.

El problema clásico es el de los **tokens que llegan después de desmontar**: el usuario cierra el panel o cambia de conversación y el stream sigue entregando eventos. El texto de la conversación A aparece en la B y el backend sigue generando tokens que nadie lee. La solución tiene tres partes:

1. **Cerrar en la limpieza:** `fuente.close()` o `ctrl.abort()` al desmontar o al cambiar de id.
2. **Descartar lo que no corresponde:** cada evento trae el id de la conversación y el componente ignora los que no coinciden con la activa.
3. **Propagar la cancelación al backend:** al ver la conexión cerrada, el backend corta la llamada al proveedor.

```ts
useEffect(() => {
  const fuente = new EventSource(`/api/asistente/conversaciones/${id}/eventos`);
  fuente.addEventListener("message", (e) => agregarTexto(id, JSON.parse(e.data).texto));
  fuente.addEventListener("herramienta", (e) => actualizarHerramienta(JSON.parse(e.data)));
  fuente.addEventListener("fin", () => fuente.close());
  return () => fuente.close();
}, [id]);
```

**Ejemplo:** sin el cierre en la limpieza, un operador que cambia 20 veces de conversación en una hora deja 20 conexiones abiertas. Los navegadores limitan las conexiones simultáneas por dominio en HTTP/1.1 (del orden de 6), así que las siguientes peticiones del panel quedan en espera y la consola "se congela".

**Por qué importa:** en el chat, cada evento que llega tarde cuesta tokens y puede mostrar información en el lugar equivocado.

### Pub/sub en el frontend: el bus de eventos

Un **bus de eventos** es un objeto central donde cualquier parte de la app publica eventos y cualquier otra se suscribe, construible sobre un `EventTarget`. Es el patrón observador de [patrones de comportamiento](#t/patrones-comportamiento) aplicado a toda la aplicación.

```ts
export const bus = new EventTarget();
bus.dispatchEvent(new CustomEvent("envio-actualizado", { detail: { id: "P-1042" } }));
bus.addEventListener("envio-actualizado", recargar, { signal });
```

Sirve para avisos verdaderamente transversales y de bajo volumen: "la sesión expiró", "hay una versión nueva", "el agente terminó una acción que modificó envíos". Se vuelve espagueti cuando reemplaza el flujo normal de datos. Las señales:

- Para saber qué pasa al hacer clic hay que buscar el nombre del evento en todo el repositorio.
- Hay eventos que disparan eventos que disparan eventos, y el orden importa.
- El `detail` no tiene tipos, y un cambio en quien publica rompe a un suscriptor lejano en tiempo de ejecución.

La regla práctica: los datos compartidos van por props, contexto o caché; el bus queda para unas pocas notificaciones, tipadas en un solo archivo.

**Ejemplo:** cuando el agente de operaciones reprograma pedidos, publica `envios-modificados` con la lista de ids. La tabla invalida su caché. Es un solo evento, tipado, con un solo suscriptor conocido.

**Por qué importa:** el bus desacopla tanto que borra la traza de causa y efecto; usado con moderación resuelve avisos globales, usado para todo hace imposible depurar.

## Casos prácticos

### La tabla de 8.000 envíos tardaba en cambiar de filtro

**Situación:** la consola de operaciones registraba tres listeners por fila. Al cambiar de filtro, el perfil de rendimiento mostraba 140 ms solo en registrar y quitar listeners, y la memoria crecía en cada cambio porque algunos no se quitaban.

**Qué se hace:** un solo listener delegado en la tabla, con `closest("button[data-accion]")` y un mapa de acciones. Las filas solo llevan `data-envio-id`. Desaparecen el costo de registrar y la fuga, y las filas virtualizadas funcionan sin código extra.

### El asistente escribía en la conversación equivocada

**Situación:** al cambiar rápido entre dos conversaciones, el final de la respuesta de la primera aparecía en la segunda. Además, el costo de tokens del asistente era un 15 % mayor de lo esperado.

**Qué se hace:** el efecto del stream no tenía limpieza: se agrega `fuente.close()` en el retorno, cada evento incluye el id de conversación y se descartan los que no coinciden, y el backend corta la generación al detectar la conexión cerrada. Un test verifica que, al cambiar de id, no llegan tokens de la conversación anterior.

### Catorce llamadas al agente por cada búsqueda

**Situación:** el buscador de la consola pedía sugerencias al agente en cada tecla. Las respuestas llegaban desordenadas y a veces se mostraba la sugerencia de "demo" en lugar de la de "demoras zona norte".

**Qué se hace:** debounce de 300 ms y un `AbortController` por petición: cada búsqueda nueva aborta la anterior, así que una respuesta vieja nunca pisa a una nueva. Las llamadas al modelo bajan de un promedio de 14 a 3 por consulta.

### Un bus de eventos que nadie entendía

**Situación:** el panel tenía 46 tipos de eventos en un bus global. Un cambio en `zona-seleccionada` rompió el mapa y el resumen del asistente, y encontrar los suscriptores tomó dos días.

**Qué se hace:** los eventos que transportaban datos compartidos (zona, filtros, envío seleccionado) pasan a la URL o al estado del ancestro común. Quedan 5 avisos transversales, tipados en un archivo que una regla de lint hace obligatorio.

## Errores comunes

- **Usar `stopPropagation` para resolver un conflicto local.** Rompe a los que escuchan más arriba; es mejor que el listener del contenedor ignore los clics que vienen de controles interactivos.
- **Confundir `target` con `currentTarget`.** Con delegación se usa `closest` sobre `target`.
- **Registrar listeners sin plan de limpieza.** Todo `addEventListener` en `window`, `document` o una conexión necesita un `AbortController` o una limpieza en el efecto.
- **Hacer trabajo caro en cada evento de una ráfaga.** Scroll, resize e input se limitan con throttle, debounce o `requestAnimationFrame`.
- **Dejar streams abiertos al desmontar.** Mezcla conversaciones, agota conexiones y gasta tokens que nadie lee.
- **Convertir el bus de eventos en el canal de datos.** Los datos compartidos van por props, contexto, URL o caché; el bus, solo para avisos globales.

## Para discutir en equipo

- ¿Dónde usamos `stopPropagation` hoy, y qué listener de más arriba podría estar dejando de funcionar por eso?
- ¿Qué listeners de nuestras pantallas largas se podrían reemplazar por delegación?
- ¿Cómo verificamos, en un test o en producción, que cerrar el panel del asistente corta la generación en el backend?
- ¿Qué eventos de nuestros componentes exponen datos personales en `detail`, y quién puede escucharlos?
- ¿Qué eventos de nuestro bus deberían ser estado compartido y cuáles son realmente avisos globales?
