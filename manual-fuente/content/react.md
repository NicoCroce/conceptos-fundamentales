---
slug: react
titulo: React
resumen: Biblioteca para construir interfaces con componentes y estado; cubre su modelo de renderizado, hooks, datos del servidor, rendimiento y cómo armar un chat con streaming.
lectura: 17
---

## La idea central

React parte de una idea simple: la interfaz es una **función del estado**. En lugar de escribir instrucciones del tipo "cuando llegue este dato, busca tal elemento y cámbiale el texto", se describe cómo debe verse la pantalla para un estado dado, y React se encarga de llevar el DOM del navegador a esa descripción cada vez que el estado cambia. El panel de comercios de Rumbo está hecho en React: la tabla de envíos, el mapa de seguimiento y el chat con el asistente son componentes que reciben datos y devuelven qué dibujar.

La analogía es una planilla de cálculo: se escriben fórmulas, no se actualizan celdas a mano. El precio es entender cuándo y por qué React recalcula, y en interfaces con agentes, donde el texto llega token a token, eso deja de ser opcional.

## Conceptos

### Componentes y JSX

Un **componente** es una función que recibe datos y devuelve una descripción de interfaz. Esa descripción se escribe en **JSX**, una sintaxis parecida a HTML que se compila a llamadas de JavaScript.

```tsx
type Props = { envio: Envio; onAbrir: (id: string) => void };

export function FichaEnvio({ envio, onAbrir }: Props) {
  return (
    <article className="ficha">
      <h3>{envio.destinatario}</h3>
      <p>Llega en {envio.etaMin} min</p>
      <button onClick={() => onAbrir(envio.id)}>Ver detalle</button>
    </article>
  );
}
```

Lo que va entre llaves es JavaScript evaluado, y React **escapa** el texto por defecto. Los componentes empiezan con mayúscula y deben ser **puros**: con las mismas props y el mismo estado devuelven lo mismo, sin efectos secundarios durante el dibujo.

**Ejemplo:** si un comercio carga como destinatario `<img src=x onerror=...>`, la ficha muestra ese texto literal; no se ejecuta nada.

**Por qué importa:** el escape por defecto es la primera defensa cuando el texto viene de usuarios o de un modelo, y la pureza hace que React pueda dibujar de nuevo sin sorpresas.

### Props y estado

Las **props** son los datos que un componente recibe de su padre; son de solo lectura. El **estado** es la memoria propia del componente, que cambia con el tiempo y provoca un nuevo dibujo al cambiar.

```tsx
function FiltroZona({ onCambio }: { onCambio: (z: string) => void }) {
  const [zona, setZona] = useState("todas");
  return (
    <select value={zona} onChange={(e) => { setZona(e.target.value); onCambio(e.target.value); }}>
      <option value="todas">Todas</option>
      <option value="norte">Norte</option>
    </select>
  );
}
```

Los datos bajan por props y los eventos suben por callbacks. Si dos hermanos necesitan el mismo dato, el estado se **eleva** al ancestro común; si el dato atraviesa cinco niveles que no lo usan, aparece el **prop drilling**, que se resuelve con composición o contexto.

**Ejemplo:** la tabla de envíos y el contador de demorados dependen de la misma zona, así que el filtro vive en la página y baja a ambos por props.

**Por qué importa:** saber dónde vive cada estado decide qué se vuelve a dibujar y evita copias del mismo dato que se desincronizan.

### El modelo de renderizado: render, reconciliación y commit

Cada actualización pasa por tres fases:

1. **Render:** React llama a las funciones de los componentes afectados y obtiene un árbol nuevo de elementos. Es solo cálculo; todavía no se toca el DOM.
2. **Reconciliación:** compara el árbol nuevo con el anterior para encontrar las diferencias mínimas. Si un elemento cambió de tipo (un `div` pasa a ser `section`), descarta todo ese subárbol; si es del mismo tipo, reutiliza el nodo y actualiza atributos.
3. **Commit:** aplica esas diferencias al DOM real y luego ejecuta los efectos.

Un componente se vuelve a dibujar cuando **cambia su estado**, cuando **su padre se vuelve a dibujar** (aunque sus props no cambien) o cuando cambia un **contexto** que consume. Si la página de envíos guarda un reloj en su estado, todas sus fichas se recalculan cada segundo.

**Las keys en listas.** Al dibujar una lista, React necesita saber qué elemento es cuál entre un render y otro. La prop `key` cumple esa función:

```tsx
{envios.map((e) => <FichaEnvio key={e.id} envio={e} onAbrir={abrir} />)}
```

**Ejemplo:** con el índice como key, insertar un envío al principio de una lista de 50 hace que React actualice 50 fichas en vez de insertar una, y un desplegable abierto en la ficha 3 queda pegado a la posición, no al envío. Con `key={e.id}` se inserta un solo nodo.

**Por qué importa:** casi todos los problemas de rendimiento y de estado "que salta" se explican con estas tres fases y con las keys.

### Hooks básicos

Los **hooks** son funciones que empiezan con `use` y conectan un componente con capacidades de React. Se llaman siempre en el mismo orden, en el nivel superior del componente, nunca dentro de condiciones o bucles.

- **`useState`:** estado local. Si el nuevo valor depende del anterior, se usa la forma funcional: `setContador((c) => c + 1)`.
- **`useRef`:** una caja mutable que sobrevive entre renders y **no provoca un nuevo dibujo** al cambiar. Sirve para referencias al DOM (enfocar un campo) y para guardar valores que no se muestran, como un `AbortController` o el id de un temporizador.
- **`useMemo` y `useCallback`:** memorizan un valor calculado o una función entre renders, y solo la recalculan si cambian sus dependencias.
- **Custom hooks:** funciones propias que combinan otros hooks para reutilizar lógica. `useEnvio(id)` encapsula la petición, la caché y el estado de carga; el componente solo lo usa.

**Cuándo no molestarse con `useMemo` y `useCallback`:** memorizar tiene costo y complica el código. Vale la pena para un cálculo caro, un valor que recibe un componente envuelto en `memo` o una dependencia de un efecto; no por costumbre. Existe un compilador que agrega memorización automática; su estado y alcance hay que verificarlos en la documentación vigente.

**Ejemplo:** ordenar 10.000 envíos por ETA en cada tecla del buscador se nota; con `useMemo` dependiente de `[envios, orden]` se ordena solo cuando cambian.

**Por qué importa:** los hooks concentran la lógica reutilizable; usarlos bien evita tanto renders de más como código lleno de memorizaciones inútiles.

### useEffect y su mal uso

`useEffect` sincroniza el componente con algo **externo a React**: una conexión de red, una suscripción, un temporizador, un widget que no es de React. Se ejecuta después del commit, y la función que devuelve es la **limpieza**, que corre antes del siguiente efecto y al desmontar.

```tsx
useEffect(() => {
  const ws = abrirSeguimiento(envioId, setPosicion);
  return () => ws.close(); // sin esto, cada cambio de envío deja una conexión abierta
}, [envioId]);
```

El mal uso más frecuente es usarlo para **calcular datos derivados**:

```tsx
// Mal: dos renders y un estado que puede desincronizarse
const [demorados, setDemorados] = useState<Envio[]>([]);
useEffect(() => setDemorados(envios.filter((e) => e.demorado)), [envios]);

// Bien: se calcula durante el render
const demorados = envios.filter((e) => e.demorado);
```

Otros malos usos: reaccionar a un clic dentro de un efecto en lugar de en el manejador, y encadenar efectos. La pregunta guía es "¿esto sincroniza con algo externo?". En desarrollo, el modo estricto monta y desmonta dos veces cada componente para detectar efectos sin limpieza.

**Ejemplo:** el efecto de seguimiento de arriba, sin `ws.close()`, deja una conexión abierta por cada envío que el operador abre durante el turno.

**Por qué importa:** los efectos mal usados generan renders dobles, fugas de conexiones y, en el chat, tokens gastados en respuestas que nadie ve.

### Datos del servidor y formularios

Un `fetch` dentro de un `useEffect` no resuelve carreras (una respuesta vieja que llega tarde), caché, reintentos ni deduplicación. Por eso los datos del servidor se manejan con una biblioteca de caché de datos o con las capacidades de carga del framework (ver [Arquitectura de frontend](#t/arquitectura-frontend) para la distinción entre estado del servidor, del cliente y de la URL).

```tsx
const { data, isPending, error } = useQuery({
  queryKey: ["envio", id],
  queryFn: ({ signal }) => api.obtenerEnvio(id, { signal }),
});
```

En **formularios**, un campo **controlado** guarda su valor en estado (validación en vivo, a costa de un render por tecla) y uno **no controlado** deja el valor en el DOM y se lee al enviar. Las bibliotecas de formularios combinan ambos y validan con esquemas que conviene compartir con el backend.

**Ejemplo:** el formulario de reprogramación valida la franja con el mismo esquema que usa la API y deshabilita el botón mientras envía, para evitar reprogramaciones dobles.

**Por qué importa:** un `fetch` en un efecto ignora carreras y caché; una biblioteca resuelve eso y además cancela con `signal` al desmontar.

### Contexto frente a bibliotecas de estado

El **contexto** permite que un valor llegue a cualquier descendiente sin pasarlo por props. Es ideal para valores que cambian poco y usa casi toda la app: el tema, el idioma, la sesión. Su límite es que **todo consumidor se vuelve a dibujar cuando cambia el valor**. Un contexto con `{ envios, filtros, chat }` que cambia con cada token del asistente vuelve a dibujar la tabla entera.

| Necesidad | Herramienta razonable |
|---|---|
| Valor global que cambia poco (tema, sesión) | Contexto |
| Datos del backend | Biblioteca de caché de datos |
| Filtros, página, pestaña | URL |
| Estado del cliente compartido y frecuente (conversación activa) | Store con suscripciones por selector |
| Estado de un solo componente | `useState` o `useReducer` |

Los stores con **selectores** permiten suscribirse solo a una parte (`store((s) => s.conversacion.estado)`).

**Ejemplo:** el indicador "el asistente está respondiendo" del encabezado se suscribe solo a `conversacion.estado`, así que no se redibuja con cada token.

**Por qué importa:** elegir mal entre contexto y store convierte cada cambio frecuente en un redibujo de toda la app.

### Rendimiento: memoización, virtualización y división de código

Las herramientas, en el orden en que conviene probarlas:

1. **Medir.** El perfilador de las herramientas de desarrollo de React muestra qué componentes se dibujaron, por qué y cuánto tardaron. Optimizar sin medir suele atacar lo que no importa.
2. **Bajar el estado.** Si el reloj vive en un componente `Reloj` y no en la página, solo se redibuja el reloj.
3. **`memo`:** envolver un componente para que no se redibuje si sus props no cambiaron (comparación superficial). Requiere que las props sean estables, de ahí `useCallback`.
4. **Virtualización de listas:** dibujar solo las filas visibles; una tabla de 5.000 envíos con 40 visibles monta unas 50 filas.
5. **División de código:** cargar bajo demanda partes pesadas con `lazy` e importaciones dinámicas.
6. **Suspense:** declara qué mostrar mientras una parte del árbol espera código o datos: `<Suspense fallback={<Esqueleto />}>`.

**Ejemplo:** el mapa de seguimiento, con cientos de KB de biblioteca, se carga con `lazy` dentro de un `Suspense` que muestra un esqueleto; la tabla aparece sin esperarlo.

**Por qué importa:** el orden importa: medir y bajar el estado resuelve la mayoría de los casos antes de llegar a `memo`.

### Server Components, SSR y streaming

Con **renderizado en el servidor (SSR)**, el servidor ejecuta los componentes y envía HTML ya armado; el navegador lo muestra enseguida y luego la **hidratación** conecta ese HTML con el JavaScript para que sea interactivo. Con **SSR en streaming**, el servidor envía el HTML por partes: primero la estructura y los bloques rápidos, y los que esperan datos lentos llegan después dentro de sus límites de Suspense.

Los **React Server Components** van un paso más allá: algunos componentes se ejecutan **solo en el servidor**, pueden leer datos directamente y su código nunca llega al navegador. Solo los componentes marcados como de cliente (los que tienen estado, efectos o eventos) viajan al bundle. Frameworks como Next.js organizan una aplicación alrededor de este modelo, con rutas, carga de datos y acciones de servidor.

Directivas, convenciones de carpetas y caché por defecto cambian entre versiones mayores: verificar en la documentación vigente. Lo estable es el criterio: el servidor para leer datos y para lo que no debe llegar al navegador (claves, prompts); el cliente para la interactividad.

**Ejemplo:** la página de un envío se arma en el servidor con los datos del pedido; solo el chat y el mapa son componentes de cliente.

**Por qué importa:** menos JavaScript en el navegador y primer contenido más rápido, sin exponer lo que debe quedar en el backend.

### Testing y accesibilidad

La filosofía de **Testing Library** es probar como lo usa una persona: buscar elementos por su rol y su texto accesible, interactuar y verificar lo que se ve, sin depender de la estructura interna ni del estado del componente.

```tsx
render(<Conversacion />);
await user.type(screen.getByRole("textbox", { name: "Mensaje" }), "¿Dónde está P-1042?");
await user.click(screen.getByRole("button", { name: "Enviar" }));
expect(await screen.findByText(/en camino/i)).toBeInTheDocument();
```

La accesibilidad sigue las reglas del HTML: elementos nativos (`button`, no `div` con `onClick`), etiquetas en cada campo, foco gestionado en diálogos y regiones `aria-live` para contenido que cambia.

**Ejemplo:** si el botón de enviar del chat es un `div` con ícono, `getByRole("button", { name: "Enviar" })` falla, y un lector de pantalla tampoco lo encuentra.

**Por qué importa:** los tests que buscan por rol sobreviven a refactors internos y verifican accesibilidad de paso.

### Un chat con streaming que no redibuja todo

El asistente de Rumbo recibe del backend un stream de eventos: fragmentos de texto, estados de herramientas y el final. La implementación ingenua crea un arreglo nuevo de mensajes por token y redibuja toda la conversación, markdown incluido.

El diseño que funciona:

1. **Separar mensajes cerrados del mensaje en curso.** Los cerrados forman una lista **de solo agregado**, con `key` estable y cada mensaje envuelto en `memo`: una vez terminado, no se vuelve a dibujar. Solo el componente del mensaje en curso cambia con cada token.
2. **Agrupar tokens.** En lugar de un `setState` por token, se acumulan en un `useRef` y se vuelcan al estado una vez por cuadro de animación (unos 16 ms). React además agrupa automáticamente varias actualizaciones del mismo ciclo.
3. **Marcar lo no urgente.** `useTransition` o `useDeferredValue` indican que el render del markdown puede esperar si el usuario está escribiendo: el campo de texto sigue respondiendo aunque la respuesta sea larga.
4. **Cancelar en la limpieza.** Si el usuario cambia de conversación o presiona "Detener", el `AbortController` corta la petición; el backend, al ver la conexión cerrada, deja de generar tokens.

```tsx
useEffect(() => {
  const ctrl = new AbortController();
  let buffer = "";
  let frame = 0;
  const volcar = () => { frame = 0; const t = buffer; buffer = ""; setEnCurso((p) => p + t); };

  leerStream(`/api/asistente/conversaciones/${id}/stream`, ctrl.signal, (evento) => {
    if (evento.tipo === "texto") {
      buffer += evento.texto;
      if (!frame) frame = requestAnimationFrame(volcar);
    } else if (evento.tipo === "herramienta") {
      setHerramientas((h) => ({ ...h, [evento.llamadaId]: evento.estado }));
    }
  });
  return () => { ctrl.abort(); cancelAnimationFrame(frame); };
}, [id]);
```

**Markdown seguro.** La respuesta del modelo es texto no confiable: puede traer HTML inyectado por un usuario o por un documento recuperado. React escapa el texto, pero `dangerouslySetInnerHTML` desactiva esa protección. La regla: convertir markdown a elementos de React con una biblioteca que tenga el HTML crudo deshabilitado, o, si se genera HTML, pasarlo por un sanitizador con lista permitida de etiquetas y enlaces solo `https` (ver [Seguridad en el frontend](#t/seguridad-frontend)). Nunca `dangerouslySetInnerHTML` con texto del modelo sin sanitizar.

**Estados de herramientas.** Cada llamada a herramienta se guarda por su id, con estados como `pendiente`, `en_ejecucion`, `requiere_aprobacion`, `fallida` y `completada`, y se dibuja con el componente del design system (ver [Design systems para interfaces con agentes](#t/design-systems)). La ficha de aprobación muestra los parámetros reales que envió el backend, no un resumen redactado por el modelo.

**Interfaz generativa.** A veces conviene que el modelo devuelva una interfaz en lugar de texto: una ficha de envío, un mini mapa, una tabla de demoras por zona. El patrón seguro es una **lista permitida de componentes**: el modelo elige uno por nombre mediante una herramienta y le pasa props, el backend valida esas props contra un esquema y el front busca el componente en un registro fijo.

```tsx
const REGISTRO = { ficha_envio: FichaEnvio, demoras_zona: TablaDemoras } as const;

function BloqueGenerado({ b }: { b: { componente: string; props: unknown } }) {
  const C = REGISTRO[b.componente as keyof typeof REGISTRO];
  if (!C) return <p>Contenido no disponible.</p>;
  return <C {...(validarProps(b.componente, b.props) as any)} />;
}
```

El modelo nunca genera código que se ejecute: elige de un menú cerrado, y lo que esté fuera de la lista se registra.

**Ejemplo:** con 40 mensajes y 30 tokens por segundo, la versión ingenua hace 1.200 redibujos de mensaje por segundo; la de solo agregado, 60 del mensaje en curso.

**Por qué importa:** el chat es donde React, rendimiento y seguridad se cruzan: un mal diseño se nota en fluidez, en costo de tokens y en riesgo de XSS.

## Casos prácticos

### El chat se trababa con respuestas largas

**Situación:** con respuestas de más de 1.500 palabras, el panel del asistente se volvía lento y escribir en el campo tenía un retraso visible. El perfilador mostraba que cada token redibujaba los 60 mensajes de la conversación y volvía a procesar todo su markdown.

**Qué se hace:** se aplica el diseño de solo agregado: lista cerrada con `memo`, tokens agrupados por cuadro y markdown diferido con `useDeferredValue`. El render por actualización baja de unos 45 ms a menos de 4 ms (cifras hipotéticas).

### Tokens que seguían generándose después de cerrar

**Situación:** el costo del asistente creció un 20% sin más uso aparente. Los registros del backend mostraban respuestas completas para conversaciones que el usuario ya había cerrado.

**Qué se hace:** el efecto del stream no tenía limpieza. Se agrega `abort()` en la limpieza, se ignoran eventos de otra conversación y el backend propaga la cancelación al proveedor al detectar la desconexión.

### Un enlace malicioso en la respuesta del asistente

**Situación:** en una prueba de seguridad, un documento de la base de conocimiento con una inyección de prompt hace que el asistente responda con un enlace `javascript:` y una etiqueta `<img>` con un manejador de error. El prototipo usaba `dangerouslySetInnerHTML` con el HTML que generaba una biblioteca de markdown.

**Qué se hace:** se usa un renderizador que produce elementos de React sin HTML crudo, con enlaces solo `https`. Se suman cargas maliciosas conocidas a los tests y una regla de lint bloquea `dangerouslySetInnerHTML` fuera de un archivo revisado que sanitiza.

### Una tabla de 8.000 envíos

**Situación:** los comercios grandes abren la vista "todos los envíos de la semana" y la página tarda varios segundos en responder al scroll.

**Qué se hace:** se virtualiza la tabla, se paginan los datos con cursor, el filtro pasa a la URL y el mapa se carga con división de código. La tabla responde en menos de un segundo en un equipo de gama media.

## Errores comunes

- **Usar `useEffect` para calcular datos derivados.** Produce renders dobles y estado desincronizado; se calcula durante el render.
- **Usar el índice como `key` en listas que cambian.** El estado interno queda pegado a la posición y no al elemento; se usa un id estable.
- **Efectos sin limpieza.** Conexiones, temporizadores y streams que no se cierran filtran memoria y, en el chat, gastan tokens.
- **Un contexto gigante que cambia seguido.** Redibuja todos sus consumidores; se divide por frecuencia de cambio o se usa un store con selectores.
- **`dangerouslySetInnerHTML` con texto del modelo.** Abre la puerta a XSS; se renderiza markdown sin HTML crudo o se sanitiza con lista permitida.
- **Memorizar todo por las dudas.** Agrega complejidad sin ganancia; se mide primero y se memoriza donde el perfilador lo justifica.

## Para discutir en equipo

- ¿Qué partes de nuestro estado del chat cambian con cada token, y qué componentes se redibujan por eso hoy?
- ¿Qué vistas del panel ganarían con Server Components o SSR, y cuáles son interactivas de punta a punta?
- ¿Qué componentes puede elegir el modelo en la interfaz generativa, y quién aprueba que se agregue uno nuevo a la lista?
- ¿Cómo comprobamos en los tests que "Detener" corta la generación en el backend y no solo el dibujo?
- ¿Dónde conviene definir la sanitización de la salida del modelo para que ningún equipo la tenga que reimplementar?
