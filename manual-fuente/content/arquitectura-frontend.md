---
slug: arquitectura-frontend
titulo: Arquitectura de frontend
resumen: Cómo organizar el código de una aplicación web por dominio y por capas, con límites verificables, estado clasificado y un lugar claro para el asistente.
lectura: 16
---

## La idea central

Con cinco pantallas y dos personas, cualquier organización del código funciona. El problema aparece al crecer. El panel de comercios de Rumbo empezó con una lista de pedidos y un formulario; dos años después tiene seguimiento en vivo, gestión de transportistas, reportes, configuración de zonas, un asistente con LLM y cuatro equipos que lo modifican a la vez. Si la estructura no acompañó, cada cambio toca diez carpetas, nadie se anima a borrar nada y un ajuste en la ficha de un pedido rompe el asistente.

La **arquitectura de frontend** es el conjunto de decisiones que evita eso: cómo se agrupa el código, qué puede importar a qué, dónde vive cada tipo de estado y cómo se separa lo que se ve de lo que se calcula y de cómo se habla con el backend. La analogía es la de un depósito logístico: si las cajas se ordenan por color de embalaje, encontrar todo lo de un comercio obliga a recorrer el depósito entero; si se ordenan por destino, cada pedido está junto. El código funciona igual, y hoy importa doblemente, porque además de personas lo leen y lo modifican agentes de código que necesitan encontrar rápido el lugar correcto.

## Conceptos

### Organizar por tipo técnico, y por qué deja de escalar

La forma más común de empezar es agrupar por **tipo técnico**: todos los componentes juntos, todos los hooks juntos, todas las llamadas al backend juntas.

```text
panel-comercios/src/
  components/
    TablaPedidos.tsx
    FichaPedido.tsx
    MapaSeguimiento.tsx
    ListaTransportistas.tsx
    BurbujaChat.tsx
    ... (140 archivos más)
  hooks/
    usePedidos.ts
    useTransportistas.ts
    useChat.ts
  services/
    pedidosApi.ts
    transportistasApi.ts
    asistenteApi.ts
  utils/
    formatos.ts
```

Funciona bien hasta unos 30 o 40 archivos por carpeta. Después aparecen tres problemas:

1. **Un cambio funcional se reparte por todo el árbol.** Agregar "reprogramar entrega" toca `components/`, `hooks/`, `services/` y `utils/`, carpetas que también contienen código de otros equipos.
2. **No hay límites.** Cualquier componente puede importar cualquier hook. Con el tiempo, `MapaSeguimiento` termina importando algo de `useChat` porque "ya estaba ahí", y nadie lo nota hasta que borrar el chat rompe el mapa.
3. **No hay dueños naturales.** ¿De quién es `components/`? De todos, o sea, de nadie.

**Ejemplo:** en el panel de Rumbo, el 70% de los cambios de un trimestre tocaba tres o más carpetas de primer nivel.

**Por qué importa:** la estructura por tipo optimiza para "¿dónde están los hooks?", una pregunta que casi nadie se hace. La pregunta real es "¿dónde está todo lo de envíos?".

### Screaming architecture en el frontend

La idea de **screaming architecture** (arquitectura que grita) es que, al abrir la carpeta raíz, la estructura diga de qué trata el sistema, no con qué está hecho. Un plano de una casa grita "cocina, dormitorio, baño", no "ladrillos, caños, cables".

```text
panel-comercios/src/
  envios/
    TablaEnvios.tsx
    FichaEnvio.tsx
    useEnvios.ts
    enviosApi.ts
    reprogramar/
  seguimiento/
  transportistas/
  zonas/
  reportes/
  asistente/
  compartido/
```

Cada carpeta corresponde a un área del negocio y contiene sus componentes, hooks, llamadas al backend y tests. El vocabulario de las carpetas debería coincidir con el que usan producto y backend; si el backend habla de "envíos" y el front de "orders", la traducción mental se paga en cada conversación (ver [Domain-Driven Design](#t/ddd) para la idea de lenguaje común).

**Por qué importa:** la estructura es la primera documentación: quien llega, persona o agente, entiende el sistema mirando el árbol.

### Feature-Sliced Design: capas, slices y reglas de importación

Screaming architecture dice "agrupa por dominio", pero no responde dónde va algo que usan dos dominios, ni quién puede importar a quién. **Feature-Sliced Design** (FSD) es una metodología que formaliza eso con capas ordenadas, de más alta a más baja:

| Capa | Qué contiene | Ejemplo en Rumbo |
|---|---|---|
| `app` | Arranque, proveedores globales, rutas, estilos base | `App.tsx`, cliente de consultas, tema |
| `pages` | Pantallas completas, una por ruta | `PaginaEnvios`, `PaginaTransportista` |
| `widgets` | Bloques grandes y autónomos que combinan features | `PanelSeguimientoEnVivo`, `PanelAsistente` |
| `features` | Acciones del usuario con valor de negocio | `reprogramar-envio`, `asignar-transportista`, `chat-asistente` |
| `entities` | Conceptos del dominio y cómo se muestran | `envio`, `transportista`, `zona` |
| `shared` | Piezas sin conocimiento del negocio | cliente HTTP, componentes del design system, formatos de fecha |

Dentro de cada capa (salvo `app` y `shared`) el código se divide en **slices**, uno por concepto o acción, y cada slice en **segmentos** como `ui/`, `model/`, `api/`.

```text
src/
  app/
  pages/
    envios/
  widgets/
    panel-asistente/
  features/
    reprogramar-envio/
      ui/BotonReprogramar.tsx
      model/useReprogramar.ts
      api/reprogramar.ts
      index.ts
    chat-asistente/
  entities/
    envio/
      ui/FichaEnvio.tsx
      model/tipos.ts
      api/obtenerEnvio.ts
      index.ts
  shared/
    api/cliente.ts
    ui/
```

Las reglas de importación son el corazón del método:

1. **Una capa solo importa de capas inferiores.** `features` puede usar `entities` y `shared`; `entities` nunca importa de `features`.
2. **Los slices de una misma capa no se importan entre sí.** `reprogramar-envio` no importa de `asignar-transportista`. Si necesitan combinarse, eso ocurre una capa más arriba (un widget o una página).
3. **Cada slice expone una API pública** en su `index.ts`. Desde afuera solo se importa `@/entities/envio`, nunca `@/entities/envio/model/tipos`.

```ts
// entities/envio/index.ts
export { FichaEnvio } from "./ui/FichaEnvio";
export type { Envio, EstadoEnvio } from "./model/tipos";
export { useEnvio } from "./api/obtenerEnvio";
```

**Ejemplo:** si mañana `FichaEnvio` se divide en tres archivos internos, ningún consumidor se entera, porque todos importan desde `index.ts`.

Comparación de los tres enfoques:

| Criterio | Por tipo técnico | Screaming (por dominio) | Feature-Sliced Design |
|---|---|---|---|
| Curva de entrada | Mínima | Baja | Media: hay que aprender las capas |
| Localidad de un cambio | Mala: se reparte | Buena | Buena |
| Reglas de dependencia | Ninguna | Implícitas | Explícitas y verificables |
| Código compartido entre dominios | Todo mezclado | Ambiguo (¿en qué carpeta va?) | Resuelto por capas (`entities`, `shared`) |
| Tamaño ideal | Prototipos, menos de 20 pantallas | Apps medianas, un par de equipos | Apps grandes, varios equipos |

**Por qué importa:** sin reglas, la estructura por dominio se degrada en meses. FSD convierte la intención en reglas que una herramienta puede comprobar.

### Separar interfaz, dominio y acceso a datos

Dentro de cada slice conviene distinguir tres responsabilidades:

- **Componentes de presentación:** reciben datos por props y dibujan. No saben de dónde vienen los datos ni llaman al backend. `FichaEnvio` recibe un `Envio` y muestra destinatario, estado y ETA.
- **Lógica y orquestación:** hooks o funciones que deciden qué hacer. `useReprogramar` valida la franja, llama a la API y actualiza la caché.
- **Acceso a datos:** un **cliente de API delgado** que sabe hablar HTTP, agregar cabeceras, manejar errores comunes y convertir la respuesta en tipos del dominio.

Es la idea de la arquitectura hexagonal del backend (ver [Arquitectura en capas y hexagonal](#t/arquitectura-capas-hexagonal)), aplicada con moderación: las reglas de negocio no dependen de fetch ni del formato JSON del backend. No hace falta declarar puertos formales para todo; basta con que la regla viva en una función pura que se pueda testear sin red ni navegador.

```ts
// entities/envio/model/reglas.ts: pura, sin fetch ni React
export function puedeReprogramar(e: Envio, ahora: Date): boolean {
  return e.estado === "pendiente" && e.ventanaInicio.getTime() - ahora.getTime() > 2 * 3600_000;
}
```

**Ejemplo:** el test de "no se reprograma con menos de 2 horas de anticipación" son tres líneas; si la regla viviera en el `onClick` de un botón, habría que montar el componente, simular el backend y hacer clic.

**Por qué importa:** cuando el backend cambia un campo (`eta_min` pasa a `eta_segundos`), se ajusta un solo adaptador en `api/` y el resto del código ni se entera.

### Tres tipos de estado

Gran parte del desorden en un frontend viene de tratar todo el estado igual. Hay tres tipos con naturalezas distintas:

1. **Estado del servidor:** datos cuya fuente de verdad está en el backend (envíos, transportistas, zonas). En el navegador solo hay una copia que puede quedar vieja. Necesita caché, revalidación, reintentos, deduplicación de peticiones e invalidación tras una mutación.
2. **Estado del cliente:** lo que solo existe en el navegador (un panel abierto, un borrador del chat, la fila seleccionada). Es local, síncrono y no se comparte con nadie.
3. **Estado de la URL:** filtros, página actual, pestaña activa, el id del envío abierto. Vive en la URL para que se pueda compartir un enlace, recargar sin perder la vista y usar el botón atrás.

Para el estado del servidor existen **bibliotecas de caché de datos** (TanStack Query, SWR, RTK Query y similares). Conceptualmente todas hacen lo mismo: guardan la respuesta bajo una clave (`["envios", { zona: "norte", pagina: 2 }]`), la sirven al instante si está fresca, la revalidan en segundo plano si está vieja, juntan dos peticiones iguales en una sola y permiten invalidar claves después de una mutación.

**Ejemplo:** la tabla de envíos y el contador "12 envíos demorados" del encabezado piden la misma lista. Con una caché por clave, se hace una sola petición; tras reprogramar un envío se invalida `["envios"]` y ambos se actualizan.

El error clásico es poner los tres tipos en **un único store global**. Resultado: hay que escribir a mano la caché, la invalidación y los estados de carga; los datos quedan viejos sin que nadie lo note; y cualquier cambio redibuja componentes no relacionados. Un store global sigue siendo útil para estado del cliente realmente compartido (preferencias, sesión), no como depósito de todo.

**Por qué importa:** clasificar bien el estado elimina cientos de líneas de código de sincronización y la mayoría de los errores de "datos que no se actualizan".

### Hacer cumplir los límites

Una regla escrita en una wiki dura hasta la primera entrega apurada. Los límites se hacen cumplir con herramientas:

- **Reglas de lint de importación:** configuraciones que prohíben importar de capas superiores, entre slices hermanos o desde rutas internas de un slice. Existen plugins específicos para FSD y reglas genéricas de "zonas restringidas" en los linters habituales.
- **Alias de rutas:** `@/entities/envio` en lugar de `../../../entities/envio`, más legible y fácil de verificar.
- **Grafo de dependencias en la CI:** un análisis que falla si aparece un ciclo o si una dependencia prohibida entra en el código.
- **Dueños por carpeta:** un archivo de propietarios que pide revisión del equipo de asistente para cambios en `features/chat-asistente/`.

### Monorepos y paquetes compartidos

Rumbo tiene varias aplicaciones de frontend: el panel de comercios, la consola de operaciones y el widget de seguimiento. Comparten tipos del dominio, el cliente HTTP y el design system. Un **monorepo** las pone en un mismo repositorio con paquetes internos:

```text
rumbo-front/
  apps/
    panel-comercios/
    consola-operaciones/
    widget-seguimiento/
  packages/
    ui/              (design system)
    tipos-dominio/   (Envio, Transportista, eventos)
    cliente-api/
    chat-agente/     (componentes y lógica del chat)
```

Las herramientas de monorepo permiten correr build y tests **solo de lo afectado** por un cambio y cachear resultados: un cambio en `tipos-dominio` dispara los tests de las tres apps; uno en `consola-operaciones`, solo los suyos.

Un paquete compartido se justifica cuando lo usan al menos dos aplicaciones y tiene dueño; si no, `packages/` se vuelve otro `utils/` gigante.

### Microfrontends: qué son y cuándo no

Un **microfrontend** divide una aplicación en partes que equipos distintos construyen y despliegan por separado, y que se componen en el navegador. Hay tres técnicas principales:

| Técnica | Cómo funciona | A favor | En contra |
|---|---|---|---|
| Module Federation | El bundler carga en tiempo de ejecución módulos publicados por otra app y comparte dependencias como React | Integración fluida, una sola página | Versiones compartidas frágiles, errores que solo aparecen en producción |
| Iframes | Cada parte es una página aparte embebida | Aislamiento total de estilos, JavaScript y fallas | Comunicación por mensajes, accesibilidad y diseño responsive difíciles, carga duplicada |
| Web components | Cada parte se publica como un elemento propio (ver [Web components](#t/web-components)) | Independiente del framework | Ecosistema más chico, SSR limitado |

Los costos son reales: más infraestructura, dependencias duplicadas, inconsistencias visuales y depuración repartida. Lo que se gana es **independencia organizativa**: que un equipo despliegue sin coordinar con otros.

**Cuándo no:** con un solo equipo, un solo framework y despliegues que no se bloquean, o si el motivo es "probar una tecnología". Un monolito modular con límites verificados da casi todos los beneficios sin el costo. En Rumbo, el panel sigue como monolito modular; solo el widget del asistente que se embebe en tiendas ajenas va separado, como web component.

### Dónde vive el asistente

El chat con el asistente es una feature como cualquier otra, pero con estado más rico. En FSD queda así:

```text
features/chat-asistente/
  ui/
    Conversacion.tsx
    MensajeEnCurso.tsx
    EstadoHerramienta.tsx
    AprobacionAccion.tsx
  model/
    conversacion.ts     (máquina de estados de la conversación)
    useConversacion.ts
  api/
    streamRespuesta.ts  (lee el stream del backend)
  index.ts
  AGENTS.md
widgets/panel-asistente/  (combina el chat con la ficha del envío en contexto)
```

Su `model/` maneja estados propios: mensaje en streaming, herramientas en ejecución, acción **pendiente de aprobación**, cancelación y error parcial. Conviene modelarlo como una máquina de estados explícita (`inactivo → enviando → recibiendo → esperando_aprobacion → recibiendo → completo`) para que no existan combinaciones imposibles como "completo y esperando aprobación".

Dos reglas de arquitectura importan especialmente:

1. **Las llamadas al LLM pasan siempre por el backend.** El front habla con un endpoint propio de Rumbo (`/api/asistente/conversaciones/:id/mensajes`) que hace streaming de la respuesta. La clave del proveedor, el system prompt, la selección de herramientas y los permisos viven en el servidor. Una clave en el bundle de JavaScript es pública, aunque esté "escondida" en una variable de entorno de build (ver [Seguridad en el frontend](#t/seguridad-frontend)).
2. **El chat no importa features de otros dominios.** Si el asistente propone reprogramar un envío, la aprobación llama al backend, que ejecuta la herramienta con los permisos del usuario; el front no reimplementa `reprogramar-envio` dentro del chat.

### Una estructura que entienden los agentes de código

Cada vez más cambios del panel los hace o los propone un agente de código. Un agente no "conoce" el repositorio: lo explora leyendo archivos, y cada archivo leído consume contexto. Una estructura clara le ahorra exploración y reduce errores:

- **Nombres de dominio en las carpetas.** Ante "agrega un filtro por transportista en la tabla de envíos", un árbol que grita `pages/envios` y `entities/transportista` lleva al agente directo al lugar. Con `components/` de 140 archivos, el agente busca por texto y puede tocar el componente equivocado.
- **API pública por slice.** El agente solo necesita leer `index.ts` para saber qué ofrece un slice, en lugar de recorrer todos sus archivos.
- **Límites verificables.** Si el agente introduce una importación prohibida, el lint falla y el agente lo corrige solo en el mismo ciclo.
- **Archivos de instrucciones por feature.** Un `AGENTS.md` o `CLAUDE.md` dentro de `features/chat-asistente/` explica lo que no se deduce del código: "el texto del modelo nunca se inserta como HTML", "los estados de herramienta se toman del componente del design system", "los tests de streaming usan el simulador de `api/__fixtures__`". Un archivo corto por feature funciona mejor que uno gigante en la raíz, porque el agente carga solo el que corresponde a la carpeta en la que trabaja.


## Casos prácticos

### Migrar el panel de comercios sin congelar el desarrollo

**Situación:** el panel tiene 400 archivos organizados por tipo técnico y cuatro equipos trabajando. Reescribir la estructura de una vez implicaría semanas de conflictos.

**Qué se hace:** se crea la estructura FSD al lado de la vieja con la regla "código nuevo en la estructura nueva; archivo viejo que se toca en profundidad, se mueve". El lint de importaciones queda en advertencia para el código viejo y en error para el nuevo. Se migra primero `entities/envio`, del que casi todo depende. Un agente de código hace los movimientos mecánicos en PRs chicos, uno por slice, que revisan personas. En dos trimestres `components/` queda vacía.

### El asistente rompía la tabla de envíos

**Situación:** al cambiar el formato del mensaje en streaming, la tabla de envíos dejó de actualizarse. La causa: los envíos, los filtros y la conversación vivían en el mismo store global, y una acción del chat sobrescribía una propiedad que la tabla leía.

**Qué se hace:** los envíos pasan a una biblioteca de caché de datos con clave `["envios", filtros]`; los filtros, a la URL; la conversación, al `model/` de `features/chat-asistente`. Cuando el asistente completa una herramienta que modifica envíos, el chat invalida la clave `["envios"]` a través de una función expuesta por `entities/envio`, sin conocer la tabla. Desaparecen los acoplamientos ocultos y el store global queda con tres campos: sesión, tema y preferencias.

### La tentación de los microfrontends

**Situación:** el equipo de reportes propone convertir el panel en microfrontends con Module Federation porque "los despliegues del monolito son lentos": la CI tarda 25 minutos.

**Qué se hace:** se mide antes de decidir. La lentitud viene de correr todos los tests ante cualquier cambio; con ejecución solo de lo afectado y caché de resultados, la CI baja a 6 minutos. Se descarta Module Federation y un ADR registra qué señales harían revisar la decisión, como equipos con calendarios de despliegue incompatibles.

### Una clave del proveedor en el bundle

**Situación:** un prototipo del asistente llamaba al proveedor de LLM directamente desde el navegador, con la clave en una variable de entorno de build. Un análisis del bundle publicado la encuentra en texto plano.

**Qué se hace:** se revoca la clave. La feature `chat-asistente` pasa a hablar solo con el endpoint de Rumbo, que autentica al usuario, aplica límites por comercio y hace streaming. La CI busca patrones de claves en el bundle, una regla de lint prohíbe importar SDKs de proveedores de LLM en el front y el `AGENTS.md` de la feature lo deja escrito para que un agente de código no repita el atajo.

## Errores comunes

- **Mover carpetas sin reglas de importación.** La estructura por dominio se degrada en meses si nada impide que un slice importe las entrañas de otro; las reglas tienen que vivir en el lint y la CI.
- **Copiar datos del backend en un store global.** Se termina reescribiendo una caché a mano; el estado del servidor va a una biblioteca de caché y los filtros a la URL.
- **Un `shared/` que conoce el negocio.** Si `shared/` importa tipos de `Envio`, deja de ser compartido; lo que sabe del dominio va en `entities`.
- **Adoptar microfrontends para resolver problemas de CI o de organización interna.** Primero se prueban monolito modular, ejecución de lo afectado y dueños por carpeta.
- **Llamar al LLM desde el navegador.** Expone la clave, el prompt y los permisos; todo pasa por el backend.
- **Dejar al agente de código adivinar las convenciones.** Sin un archivo de instrucciones por feature, cada tarea redescubre las reglas, a veces mal.

## Para discutir en equipo

- Si hoy abrimos la carpeta raíz del panel, ¿qué grita: el dominio de Rumbo o el framework?
- ¿Qué slices de `entities` usan casi todas las features, y cómo protegemos su API pública de cambios incompatibles?
- ¿Qué parte del estado actual del store global es en realidad estado del servidor o de la URL?
- ¿Qué señales concretas justificarían separar algo del panel como microfrontend?
- ¿Qué debería decir el `AGENTS.md` de `chat-asistente` para que un agente de código no rompa el flujo de aprobación?
