---
slug: componentizacion
titulo: Componentización
resumen: Cómo dividir una interfaz en componentes con una sola responsabilidad y una API clara, decidir dónde vive el estado y componer piezas en lugar de configurarlas.
lectura: 14
---

## La idea central

Un componente es una pieza de interfaz con un contrato: recibe datos, muestra algo y avisa cuando pasa algo. Componentizar es decidir dónde cortar. Si se corta poco, queda un archivo de 600 líneas que nadie quiere tocar; si se corta demasiado, para entender un botón hay que abrir once archivos. El objetivo es que cada pieza se pueda leer, probar y cambiar sin entender la pantalla entera.

La analogía útil es la de un camión de reparto de Rumbo: no se carga con objetos sueltos sino con cajas rotuladas. Cada caja tiene un contenido coherente, una etiqueta que dice qué hay adentro y un tamaño que se puede mover entre dos personas. [Arquitectura de frontend](#t/arquitectura-frontend) decide en qué depósito va cada caja (carpetas, capas, reglas de importación); este tema trata de cómo armar las cajas. Y hoy importa más que antes, porque buena parte de los componentes los escribe un agente de código, que tiende a meter todo en una sola caja si nadie le dice cómo cortar.

## Conceptos

### Qué es un buen componente

Un buen componente cumple tres condiciones:

1. **Una sola responsabilidad.** Se puede describir en una oración sin usar "y además". "Muestra el estado actual de un envío" es una responsabilidad; "muestra el estado, consulta la API, gestiona el chat y calcula la ETA" son cuatro. Es el principio de responsabilidad única de [SOLID](#t/principios-solid) aplicado a la interfaz: un componente debería tener un solo motivo para cambiar.
2. **Una API clara.** Sus props dicen qué necesita y qué ofrece, con nombres del dominio (`envio`, `onReprogramar`) y tipos estrechos. Quien lo usa no necesita leer su código.
3. **Pocas sorpresas.** No hace llamadas de red escondidas, no lee estado global sin declararlo y no modifica lo que recibe.

Una heurística práctica para saber si hay que dividir: más de unas 150 a 200 líneas, más de 3 o 4 `useState`, o un nombre que necesita "Y" o "Manager" para describirlo.

**Ejemplo:** `EstadoEnvio({ estado, actualizadoEn })` muestra una etiqueta de color y la hora del último cambio. Se puede usar en la tabla, en la ficha y en una respuesta del asistente sin cambiar una línea.

**Por qué importa:** los componentes con una responsabilidad se reutilizan solos; los que hacen cuatro cosas se copian y se modifican, y en seis meses hay tres versiones divergentes.

### Descomponer una pantalla paso a paso

La pantalla de seguimiento de un envío en el panel de comercios muestra un encabezado con el código y el estado, un mapa con la posición del transportista, una línea de tiempo de eventos, los datos del destinatario, acciones (reprogramar, contactar) y un panel lateral con el asistente. El proceso para cortarla:

1. **Dibujar cajas sobre una captura.** Cada bloque que tenga sentido por sí solo es un candidato.
2. **Nombrar cada caja con el vocabulario del negocio.** Si no hay un nombre claro, probablemente el corte está mal.
3. **Buscar repeticiones.** Los ítems de la línea de tiempo se repiten: son un componente `EventoSeguimiento` usado en un bucle.
4. **Marcar dónde se necesitan los datos.** El encabezado y las acciones usan el mismo envío; el mapa solo la posición; el asistente, el id.
5. **Separar lo que se reutiliza en otras pantallas** (`EstadoEnvio`, `DatoDestinatario`) de lo que es propio de esta (`AccionesSeguimiento`).

```arbol
titulo: Pantalla de seguimiento de un envío
PaginaSeguimiento
- EncabezadoEnvio
-- CodigoEnvio
-- EstadoEnvio
- MapaSeguimiento
-- MarcadorTransportista
- LineaTiempo
-- EventoSeguimiento (x n)
- PanelDestinatario
-- DatoDestinatario (enmascarado)
- AccionesSeguimiento
-- BotonReprogramar
- PanelAsistente
-- Conversacion
-- CampoMensaje
```

**Ejemplo:** el corte deja 14 componentes; 4 vienen del design system, 3 se reutilizan en la tabla de envíos y 7 son propios de la pantalla.

**Por qué importa:** cortar sobre una captura antes de escribir código evita la división por accidente, en la que los componentes se separan donde el archivo se volvió incómodo y no donde el dominio tiene sus límites.

### Componentes presentacionales y contenedores

La división clásica separa dos roles:

- **Presentacional:** recibe todo por props y devuelve interfaz. No sabe de dónde vienen los datos. Es fácil de probar y de mostrar en un catálogo de componentes.
- **Contenedor:** obtiene datos, maneja estado y efectos, y le pasa el resultado a componentes presentacionales.

Con los hooks, la frontera ya no exige dos archivos: la lógica suele vivir en un custom hook y el contenedor queda en tres líneas. Pero la idea sigue siendo valiosa como regla de diseño: los componentes de abajo del árbol deberían ser presentacionales, y la obtención de datos debería concentrarse en pocos puntos altos.

```tsx
function LineaTiempoContenedor({ envioId }: { envioId: string }) {
  const { eventos, cargando } = useEventosEnvio(envioId);
  return <LineaTiempo eventos={eventos} cargando={cargando} />;
}
```

**Ejemplo:** `LineaTiempo` se usa en el panel con datos reales, en el catálogo con 5 eventos de ejemplo y dentro de una respuesta del asistente con eventos que eligió una herramienta. Ninguno de los tres usos necesita una red simulada.

**Por qué importa:** un componente presentacional es una función pura de sus props; se prueba con datos, no con dobles de red.

### Composición sobre configuración

Cuando un componente tiene que adaptarse a varios usos, hay dos caminos. **Configurar** es agregar una prop por cada variación. **Componer** es dejar que quien lo usa le pase piezas.

La configuración crece mal. Una `FichaEnvio` empezó con `mostrarMapa`. Después llegaron `mostrarAcciones`, `compacta`, `mostrarDestinatario`, `soloLectura`, `mostrarAsistente`, `resaltarDemora` y `ocultarEncabezado`: 8 booleanos, es decir, 2⁸ = 256 combinaciones posibles. Nadie probó más de 10, varias son contradictorias (`soloLectura` con `mostrarAcciones`) y cada uso nuevo suma una prop. Es la **explosión de props**.

Las tres herramientas de composición:

- **`children` y slots.** El componente define el marco y el que lo usa pone el contenido. `<Panel titulo="Destinatario">{...}</Panel>`. Si hacen falta varios huecos, se pasan como props con nombre (`encabezado`, `acciones`), el equivalente a los slots de los [web components](#t/web-components).
- **Compound components.** Un componente padre y sus partes comparten estado por contexto: `<Ficha>`, `<Ficha.Encabezado>`, `<Ficha.Mapa>`, `<Ficha.Acciones>`. Quien lo usa elige qué partes incluir y en qué orden.
- **Render props.** El componente recibe una función que decide cómo dibujar cada elemento: `<ListaEnvios renderItem={(e) => <FilaCompacta envio={e} />} />`. Hoy se usan menos porque los hooks cubren casi todos los casos, pero siguen siendo útiles en listas virtualizadas.

```tsx
<Ficha envio={envio}>
  <Ficha.Encabezado />
  <Ficha.Mapa />
  {puedeEditar && <Ficha.Acciones />}
</Ficha>
```

**Ejemplo:** con compound components, las 256 combinaciones desaparecen: cada pantalla arma la ficha con las partes que necesita y cada parte se prueba una vez. La ficha pasó de 8 props booleanas a 1 (`envio`).

**Por qué importa:** cada booleano duplica los estados posibles; la composición los mantiene lineales.

### Controlados y no controlados

[Design systems](#t/design-systems) define los dos tipos y por qué un componente de biblioteca debería soportar ambos. Acá interesa cómo se implementa. La convención es la del HTML: `value` y `onChange` para el modo controlado, `defaultValue` para el no controlado. El componente decide en cada render quién manda.

```tsx
function useControlable<T>(valor: T | undefined, inicial: T, onChange?: (v: T) => void) {
  const [interno, setInterno] = useState(inicial);
  const controlado = valor !== undefined;
  const actual = controlado ? valor : interno;
  const cambiar = (v: T) => { if (!controlado) setInterno(v); onChange?.(v); };
  return [actual, cambiar] as const;
}
```

Dos reglas: un componente no debería pasar de no controlado a controlado durante su vida (React lo advierte) y, en modo controlado, el componente nunca cambia su valor por su cuenta.

**Ejemplo:** el `CampoMensaje` del asistente se usa no controlado en el widget simple. En el panel se usa controlado para que el código lo vacíe al enviar y restaure el borrador al volver a la conversación.

**Por qué importa:** elegir mal obliga a hacks: refs para leer valores, efectos para sincronizar dos estados que deberían ser uno.

### Dónde vive el estado y cómo elevarlo

La regla es **colocar el estado lo más cerca posible de donde se usa**, y subirlo solo cuando hace falta compartirlo. El proceso de elevar (**lifting state up**) paso a paso:

1. Dos componentes hermanos necesitan el mismo dato: `FiltroZona` lo cambia y `TablaEnvios` lo lee.
2. Se busca el ancestro común más cercano: `PaginaEnvios`.
3. El estado se mueve ahí; `FiltroZona` recibe `zona` y `onZonaChange`; `TablaEnvios` recibe `zona`.
4. Si el dato atraviesa tres o más niveles que no lo usan, se evalúa composición o contexto antes de seguir pasando props.

| Tipo de estado | Dónde vive | Ejemplo en Rumbo |
|---|---|---|
| De un solo componente | `useState` local | Si un acordeón está abierto |
| Compartido por hermanos | Ancestro común | Envío seleccionado en la tabla y en el mapa |
| Compartido por una feature | Contexto de la feature | Conversación activa del asistente |
| Datos del servidor | Biblioteca de caché | Lista de envíos |
| Navegable y compartible | URL | Filtros de zona y fecha |

**Ejemplo:** el envío seleccionado vivía en un store global "por las dudas". Cada clic en una fila redibujaba 40 componentes suscritos. Al bajarlo a `PaginaEnvios`, el clic redibuja 3.

**Por qué importa:** el estado demasiado arriba provoca renders de más y acoplamientos ocultos; demasiado abajo obliga a sincronizar copias.

### Custom hooks para extraer lógica

Cuando un componente mezcla mucha lógica con su interfaz, la lógica se mueve a un **custom hook**: una función `useAlgo` que combina estado, efectos y cálculos, y devuelve lo que la vista necesita. El componente queda declarativo.

Señales para extraer: el mismo bloque de `useState` + `useEffect` aparece en dos componentes; la lógica tiene casos borde que merecen sus propios tests; o el componente tiene más líneas de lógica que de JSX.

```tsx
function useRespuestaEnStreaming(conversacionId: string) {
  const [texto, setTexto] = useState("");
  const [estado, setEstado] = useState<"esperando" | "escribiendo" | "listo" | "error">("esperando");
  // abre el stream, acumula tokens, cancela en la limpieza
  return { texto, estado, detener };
}
```

**Ejemplo:** la lógica de streaming estaba copiada en el panel, la consola de operaciones y el widget, con tres manejos distintos de la cancelación. Al extraer `useRespuestaEnStreaming`, el bug de tokens después de cerrar se corrigió una vez, con un test.

**Por qué importa:** un hook separa el "qué hace" del "cómo se ve", y es la unidad natural para probar lógica sin dibujar nada.

### Atomic design y sus límites

**Atomic design** propone cinco niveles: átomos (botón, etiqueta), moléculas (campo con etiqueta y error), organismos (encabezado de la ficha), plantillas (estructura de la página sin datos) y páginas (la plantilla con datos reales). Sirve como vocabulario para un [design system](#t/design-systems): deja claro que un botón no debería saber de envíos.

Sus límites aparecen al aplicarlo como estructura de carpetas:

- La frontera entre molécula y organismo es discutible y genera debates sin valor.
- Agrupa por tamaño, no por dominio: `organismos/` termina con 80 componentes de áreas distintas, el mismo problema de organizar por tipo técnico.
- No dice nada sobre estado, datos ni lógica.

**Ejemplo:** en Rumbo, el design system usa átomos y moléculas como guía interna; las features organizan sus componentes por dominio (`seguimiento/`, `asistente/`) sin etiquetarlos por tamaño.

**Por qué importa:** atomic design es útil para pensar la biblioteca compartida y contraproducente como mapa de toda la aplicación.

### Diseñar la API de un componente compartido

Cuando un componente lo usan varios equipos, su API es un contrato. Algunas convenciones que reducen fricción, además de las de variantes y estados que define el design system:

- **Nombres de eventos con `on` + verbo del dominio:** `onReprogramar(fecha)`, no `onClick` genérico ni `handleSubmit`.
- **Pasar el resto de las props al elemento raíz** (`className`, `aria-*`, `data-*`) y reenviar la ref, para que se pueda posicionar, medir y enfocar.
- **Tipos estrechos:** una unión `"normal" | "compacta"` en lugar de `string`.
- **Valores por defecto sensatos:** el uso más común no debería necesitar más de 2 o 3 props.
- **Nada de datos de red adentro:** un componente compartido es presentacional.

**Ejemplo:** `FichaHerramienta` se diseñó con `estado`, `nombre`, `parametros` y `onAprobar`/`onRechazar`. El uso típico tiene 3 props; cuatro equipos la adoptaron sin pedir cambios en el primer trimestre.

**Por qué importa:** cambiar una API usada en 60 lugares cuesta un codemod y semanas de coordinación; pensarla bien al principio cuesta una tarde.

### Probar componentes

La pirámide práctica para componentes:

1. **Hooks y funciones puras** con tests unitarios: el reductor de estados de herramientas, el formateo de ETA.
2. **Componentes presentacionales** con Testing Library, buscando por rol y texto: "dado un envío demorado, aparece la etiqueta Demorado".
3. **Contenedores** con la red simulada en el borde (un servidor falso de peticiones), nunca simulando hooks internos. Qué doble usar en cada caso se discute en [Dobles de prueba](#t/testing-dobles).
4. **Regresión visual** para los componentes del design system, en claro y oscuro.

**Ejemplo:** para la ficha de aprobación se escriben 5 tests, uno por estado de la herramienta, más uno que verifica que el botón principal dice "Reprogramar 37 pedidos" con los parámetros reales.

**Por qué importa:** si probar un componente requiere simular seis módulos, el problema no es el test: el componente tiene demasiadas responsabilidades.

### Componentes para interfaces con agentes

Una interfaz con agentes se descompone en piezas con responsabilidades muy distintas, y conviene que cada una sea un componente aparte:

- **`Mensaje`:** rol, autor, contenido y acciones. Compuesto (`Mensaje.Contenido`, `Mensaje.Acciones`), presentacional.
- **`TextoEnStreaming`:** recibe texto parcial y un estado; sabe dibujar markdown incompleto sin romperse. No sabe de dónde vienen los tokens.
- **`FichaHerramienta`:** dibuja una llamada a herramienta según su estado (pendiente, en ejecución, fallida, completada).
- **`FichaAprobacion`:** muestra la acción exacta con sus parámetros y emite `onAprobar` u `onRechazar`. Nunca recibe un resumen redactado por el modelo.
- **`useConversacion`:** el hook que habla con el backend, maneja el stream y expone mensajes y estados. Es la única pieza con red.

El otro lado es el de los **agentes de código**. Al pedirle "agrega aprobación humana a la pantalla del asistente", un agente sin guía tiende a resolver todo en el archivo que está abierto: suma estados, efectos, llamadas y JSX al mismo componente. Tres o cuatro tareas después, `PanelAsistente.tsx` tiene 600 líneas, 12 `useState` y 5 efectos que se pisan. No es mala fe: es el camino de menor resistencia, y el agente no tiene la visión de la pantalla completa.

Lo que funciona: instrucciones explícitas en el archivo de la feature ("un componente por archivo, menos de 200 líneas, la red solo en `useConversacion`"), pedir primero el árbol de componentes y revisarlo antes de que escriba código, y una regla de lint de tamaño máximo que falle en la CI, para que el agente se corrija solo.

**Ejemplo:** con el árbol aprobado de antemano, el agente entregó la aprobación humana en 4 archivos de entre 40 y 120 líneas, en lugar de sumar 180 líneas al panel existente.

**Por qué importa:** en una interfaz con agentes, la ficha de aprobación es un control de seguridad; tiene que ser fácil de leer, probar y revisar, no estar enterrada en un archivo enorme.

## Casos prácticos

### La ficha de envío de 640 líneas

**Situación:** `FichaEnvio.tsx` creció a 640 líneas en varias tareas hechas con un agente de código. Tiene 11 `useState`, 4 efectos y 3 llamadas a la API. Un cambio en el mapa rompió las acciones porque compartían un estado de carga.

**Qué se hace:** se dibuja el árbol sobre una captura y se acuerda antes de tocar código. La red pasa a dos hooks (`useEnvio`, `useEventosEnvio`), cada sección a un componente presentacional y la ficha a compound components. Se agrega una regla de lint de 200 líneas por componente en la carpeta, y el archivo de instrucciones de la feature describe el árbol. Resultado: 9 archivos, ninguno de más de 120 líneas, y tests por sección.

### Una tabla con 14 props booleanas

**Situación:** la `TablaEnvios` compartida acumula 14 props booleanas para adaptarse a cuatro pantallas. Agregar una columna para el equipo de operaciones requiere una prop número 15 y nadie sabe qué combinaciones funcionan.

**Qué se hace:** se pasa a una API de columnas por composición: cada pantalla declara sus columnas como lista de definiciones (`{ id, titulo, celda: (e) => ... }`). La tabla se encarga de ordenar, virtualizar y seleccionar. Las 14 props desaparecen y cada pantalla ve en su propio código qué columnas muestra.

### La misma ficha de aprobación en dos productos

**Situación:** la consola de operaciones y el panel de comercios tienen cada uno su ficha de aprobación para acciones del agente. En la consola, el botón principal dice "Aceptar" y muestra un resumen del modelo; en el panel, los parámetros reales.

**Qué se hace:** se unifica en `FichaAprobacion` del design system, presentacional, que recibe los parámetros validados por el backend y el texto de la acción. Las dos apps solo deciden qué hacer en `onAprobar`. La diferencia de seguridad desaparece porque ya no hay dos implementaciones.

### Un filtro que se perdía al recargar

**Situación:** el filtro de zona vivía en el estado local de `FiltroZona`. La tabla lo leía por un evento propio y, al recargar o compartir el enlace, se perdía.

**Qué se hace:** se aplica la tabla de dónde vive el estado: un filtro navegable va en la URL. `PaginaEnvios` lo lee de ahí y lo pasa a `FiltroZona` (controlado) y a `TablaEnvios`. Se elimina el evento propio, y el agente de operaciones puede devolver enlaces con el filtro ya aplicado.

## Errores comunes

- **Dividir por tamaño de archivo y no por responsabilidad.** Partir un componente en `Parte1` y `Parte2` no mejora nada; se corta donde el dominio tiene límites con nombre.
- **Responder a cada caso nuevo con un booleano.** A partir de 3 o 4 props booleanas, conviene pasar a composición.
- **Poner todo el estado en un store global.** Se pierde la colocación y cada cambio redibuja medio árbol; el estado sube solo cuando hay que compartirlo.
- **Componentes compartidos que hacen llamadas de red.** Atan la pieza a un backend y obligan a simular la red en cada test.
- **Usar atomic design como estructura de carpetas de toda la app.** Sirve para la biblioteca, no para las features.
- **Dejar que el agente de código decida el árbol.** Hay que pedir y revisar la descomposición antes del código, y poner un límite de tamaño verificable.

## Para discutir en equipo

- ¿Qué componentes de nuestro panel no se pueden describir en una oración sin "y además"?
- ¿Cuál de nuestros componentes compartidos tiene más props booleanas, y qué partes se podrían componer?
- ¿Qué estado del panel vive más arriba de lo necesario, y qué estado debería estar en la URL?
- ¿Qué reglas de componentización deberían ir en el archivo de instrucciones para los agentes de código, y cuáles se pueden verificar en la CI?
- ¿Qué piezas de la interfaz del asistente deberían ser idénticas en todos los productos de Rumbo por razones de seguridad?
