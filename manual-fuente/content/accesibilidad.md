---
slug: accesibilidad
titulo: Accesibilidad web
resumen: Cómo hacer interfaces que puedan usar personas con discapacidad, con WCAG 2.2, HTML semántico, ARIA, teclado, contraste y pruebas automáticas y manuales.
lectura: 16
---

## La idea central

Una interfaz accesible funciona para personas que no ven la pantalla, que no usan mouse, que ven con poco contraste, que agrandan el texto, que no distinguen ciertos colores o que se marean con las animaciones. No es un grupo chico: incluye discapacidades permanentes (ceguera, movilidad reducida), temporales (un brazo enyesado) y situacionales (un transportista con guantes, bajo el sol, con una mano ocupada). Lo que se diseña para el caso extremo suele mejorar la experiencia de todos, como las rampas de las veredas que terminan usando carritos y valijas.

Técnicamente, todo se apoya en una idea: el navegador construye, a partir del HTML, un **árbol de accesibilidad** con el rol, el nombre y el estado de cada elemento ("botón, Reprogramar entrega, habilitado"). Los lectores de pantalla, el control por voz y, cada vez más, los agentes que operan navegadores leen ese árbol, no los píxeles. Si el HTML dice la verdad sobre lo que es cada cosa, casi todo funciona; si una `div` se disfraza de botón, todos esos clientes quedan a ciegas. Este tema profundiza lo que [Design systems](#t/design-systems), [React](#t/react) y [Web components](#t/web-components) mencionan de paso.

## Conceptos

### Por qué importa: usuarios, ley, SEO y agentes

Cuatro razones, que convencen a públicos distintos:

1. **Usuarios.** La Organización Mundial de la Salud estima que alrededor de una de cada seis personas vive con una discapacidad significativa. Entre operadores de soporte, comercios y destinatarios de Rumbo hay personas que usan lectores de pantalla, ampliadores o solo teclado.
2. **Ley.** En la Unión Europea, el European Accessibility Act se aplica desde junio de 2025 a buena parte de los servicios digitales; en Estados Unidos hay demandas frecuentes basadas en la ADA; varios países de la región tienen normas para el sector público y sus proveedores. Los clientes grandes ya lo piden en sus contratos.
3. **SEO.** Los buscadores también leen estructura: encabezados, textos alternativos, enlaces descriptivos.
4. **Agentes.** Los agentes que automatizan tareas en un navegador leen el árbol de accesibilidad para entender la página. Un botón sin nombre accesible es invisible para un lector de pantalla y para un agente.

**Ejemplo:** un cliente grande quiere operar el panel de comercios con un agente de automatización. El agente no encuentra "Reprogramar" porque el control es una `div` con un ícono SVG y sin texto. El mismo defecto ya bloqueaba a una operadora que usa NVDA.

**Por qué importa:** la accesibilidad deja de parecer un extra cuando se ve que el mismo árbol lo consumen personas, buscadores y agentes.

### WCAG 2.2, POUR y los niveles

Las **WCAG** (Web Content Accessibility Guidelines) son las pautas del W3C que casi todas las leyes toman como referencia. La versión vigente es la 2.2, de 2023. Se organizan en cuatro principios, con la sigla **POUR**:

- **Perceptible:** texto alternativo, subtítulos, contraste suficiente, no depender solo del color.
- **Operable:** todo funciona con teclado, hay tiempo suficiente, los objetivos son alcanzables.
- **Comprensible:** idioma declarado, errores explicados, comportamiento previsible.
- **Robusto:** nombre, rol y valor correctos para que funcione con las tecnologías de asistencia.

Cada principio tiene **criterios de conformidad** comprobables, con número (1.4.3 es contraste mínimo) y nivel:

| Nivel | Qué representa | Ejemplos |
|---|---|---|
| A | Lo mínimo: sin esto, algunos grupos no pueden usar el sitio | Texto alternativo (1.1.1), teclado (2.1.1), sin trampas de foco (2.1.2), no solo color (1.4.1) |
| AA | El objetivo habitual de leyes y contratos | Contraste 4,5:1 (1.4.3), reflow a 320 px (1.4.10), foco visible (2.4.7), mensajes de estado (4.1.3), objetivos de 24 px (2.5.8) |
| AAA | Mejoras deseables, no exigibles en todo el sitio | Contraste 7:1 (1.4.6), objetivos de 44 px (2.5.5) |

WCAG 2.2 agregó, entre otros, foco no tapado (2.4.11), alternativa a arrastrar (2.5.7), tamaño mínimo de objetivo (2.5.8), no pedir dos veces el mismo dato (3.3.7) y autenticación accesible (3.3.8), y retiró el criterio 4.1.1 sobre parseo.

**Ejemplo:** el contrato con un cliente exige "WCAG 2.2 AA": todos los criterios A y AA, no solo contraste. En el tablero de operaciones, reordenar paradas se hacía solo arrastrando; por 2.5.7, cada parada suma botones "Subir" y "Bajar".

**Por qué importa:** "es accesible" es una opinión; "cumple 1.4.3 y 2.1.1" es verificable. El objetivo razonable es **AA completo**, con criterios AAA puntuales donde son baratos o críticos.

### Contraste: cómo se calcula la relación

WCAG AA pide **4,5:1** para texto normal; **3:1** para texto grande (desde 24 px regular o unos 18,7 px en negrita) y para componentes de interfaz y gráficos con significado, como el borde de un campo o el indicador de foco (1.4.11).

La relación se calcula con la **luminancia relativa** de cada color, entre 0 (negro) y 1 (blanco):

1. Cada canal (R, G, B) se divide por 255.
2. Se linealiza: si el valor es menor o igual a 0,04045, se divide por 12,92; si no, `((valor + 0,055) / 1,055) ^ 2,4`.
3. Se ponderan según la sensibilidad del ojo: `L = 0,2126 · R + 0,7152 · G + 0,0722 · B`.
4. Relación: `(L1 + 0,05) / (L2 + 0,05)`, con L1 la del color más claro.

**Ejemplo:** el azul de marca de Rumbo, `#2F6FEB`, sobre blanco.

1. R = 47/255 = 0,184; G = 111/255 = 0,435; B = 235/255 = 0,922.
2. Linealizados: R ≈ 0,028; G ≈ 0,159; B ≈ 0,831.
3. L = 0,2126 × 0,028 + 0,7152 × 0,159 + 0,0722 × 0,831 ≈ 0,006 + 0,114 + 0,060 = 0,180.
4. Contra blanco (L = 1): 1,05 / 0,230 ≈ **4,57:1**. Pasa para texto normal, por poco.

El mismo azul sobre el fondo oscuro `#121212` (L ≈ 0,006): 0,230 / 0,056 ≈ **4,1:1**. Sirve para texto grande e íconos, no para texto normal: el token de enlace necesita otro valor en el tema oscuro. Notar también que el canal azul, el más alto del color, aporta apenas 0,06: por eso los azules saturados tienen menos contraste del que aparentan.

**Por qué importa:** el contraste es el criterio que más falla en auditorías y el más fácil de automatizar validando los tokens en la CI.

### Teclado y foco

Todo lo que se hace con mouse tiene que poder hacerse con teclado (2.1.1). Tres reglas:

1. **Foco visible** (2.4.7), con un indicador de al menos 3:1. Quitar el `outline` sin reemplazo es uno de los errores más comunes; `:focus-visible` muestra el anillo con teclado y no al hacer clic.
2. **Orden lógico** (2.4.3), dado por el orden del DOM. Un `tabindex` positivo casi siempre empeora las cosas.
3. **Sin trampas** (2.1.2), salvo en diálogos modales: mientras están abiertos el foco circula dentro, Escape los cierra y el foco vuelve al elemento que los abrió. Además, el elemento con foco no puede quedar tapado por una barra fija o un banner (2.4.11).

```css
:focus-visible { outline: 3px solid var(--color-foco); outline-offset: 2px; }
```

**Ejemplo:** en el chat del panel, Tab desde el campo de mensaje lleva a "Enviar", luego a "Copiar", "Útil" y "No útil" de la última respuesta. Cuando el agente pide aprobación, el foco salta a la ficha de aprobación; Escape la cierra sin aprobar y devuelve el foco al campo de mensaje.

**Por qué importa:** la prueba de teclado lleva cinco minutos, no requiere herramientas y encuentra problemas que ninguna herramienta automática detecta.

### HTML semántico primero

Un `<button>` trae, sin escribir nada: foco con Tab, activación con Enter y Espacio, rol de botón, estado deshabilitado y participación en formularios. Una `<div onclick>` no trae nada de eso, y replicarlo a mano casi siempre deja algo afuera. Lo mismo con la estructura: encabezados `h1`–`h6` en orden (los usuarios de lectores navegan saltando entre ellos), regiones (`header`, `nav`, `main`), listas reales, tablas con `th`, enlaces para navegar y botones para actuar.

```html
<!-- Mal: no se enfoca, no tiene rol ni nombre -->
<div class="btn" onclick="reprogramar()"><svg>...</svg></div>

<!-- Bien: foco, teclado, rol y nombre accesible -->
<button type="button" onclick="reprogramar()">
  <svg aria-hidden="true">...</svg> Reprogramar entrega
</button>
```

**Ejemplo:** la lista de pedidos del panel estaba hecha con `div` anidadas. Convertida en `table` con encabezados de columna, el lector pasó a anunciar "Estado: En camino, columna 4 de 6" sin una línea de ARIA.

**Por qué importa:** cada `div` disfrazada de control es una deuda en teclado, roles y estados que suele pagarse incompleta.

### ARIA: reglas, estados y regiones vivas

ARIA es un conjunto de atributos que modifican el árbol de accesibilidad. Es poderoso y peligroso, porque **cambia lo que se anuncia, no el comportamiento**: `role="button"` no agrega teclado. La **primera regla de ARIA** dice: si existe un elemento nativo con la semántica y el comportamiento necesarios, se usa ese. Los relevamientos sobre sitios reales muestran de forma recurrente que las páginas con más ARIA tienden a tener más errores.

Lo que ARIA sí resuelve bien:

- **Nombres:** `aria-label` o `aria-labelledby` para controles sin texto visible.
- **Estados:** `aria-expanded`, `aria-selected`, `aria-invalid`, `aria-busy`.
- **Relaciones:** `aria-describedby` vincula un campo con su ayuda o su error.
- **Regiones vivas:** `aria-live` avisa que un contenido cambió sin mover el foco. `polite` espera a que el lector termine lo que dice; `assertive` interrumpe y se reserva para lo urgente. `role="status"` equivale a `polite`; `role="alert"`, a `assertive`.

**Ejemplo:** la respuesta del asistente llega en streaming. Si el contenedor del mensaje es una región viva, el lector intenta anunciar cada fragmento y la persona oye palabras sueltas durante veinte segundos. El patrón que funciona:

```html
<div role="status" class="solo-lectores" id="anuncios"></div>
<article aria-busy="true" aria-labelledby="autor-42">
  <h3 id="autor-42" class="solo-lectores">Respuesta del asistente</h3>
  <div class="contenido"><!-- tokens que llegan --></div>
</article>
```

Al empezar se escribe "El asistente está respondiendo" en `#anuncios`; al terminar se quita `aria-busy` y se anuncia "Respuesta lista" (o el texto si es corto, o por oraciones si es largo, con no más de un anuncio cada pocos segundos). La persona llega al mensaje navegando por encabezados y lo lee a su ritmo.

**Por qué importa:** el criterio 4.1.3 pide anunciar los mensajes de estado; hacerlo mal con streaming es peor que no hacerlo.

### Formularios y errores

Un formulario accesible tiene una **etiqueta visible por campo** vinculada con `<label for>` (el placeholder no es etiqueta: desaparece al escribir), instrucciones **antes** del campo, errores **en texto** junto al campo (3.3.1) con sugerencia de corrección cuando se conoce (3.3.3), y al enviar con errores, un resumen arriba con el foco movido ahí. No se pide dos veces el mismo dato (3.3.7) y se permite pegar y autocompletar.

```html
<label for="cp">Código postal</label>
<input id="cp" inputmode="numeric" autocomplete="postal-code"
       aria-invalid="true" aria-describedby="cp-error">
<p id="cp-error">El código postal tiene 4 dígitos. Ingresaste 3.</p>
```

**Ejemplo:** en el alta de pedidos, un error era solo un borde rojo. Para una persona con daltonismo no había error visible, y para un lector de pantalla no había error en absoluto. Con texto vinculado, ícono y resumen arriba, los envíos fallidos repetidos bajaron a la mitad.

**Por qué importa:** los formularios son donde se concreta el trabajo; un error mal comunicado bloquea la tarea entera.

### Imágenes y texto alternativo

Toda imagen con información necesita un `alt` que transmita esa información, no que describa los píxeles; las decorativas llevan `alt=""` para que el lector las saltee. La pregunta guía: si la imagen no cargara, ¿qué texto la reemplazaría sin perder nada? Un ícono junto a un texto es decorativo (`aria-hidden="true"`); un ícono que es todo el contenido de un botón necesita nombre en el botón; un gráfico necesita la conclusión en el alt y los datos en una tabla cercana.

**Ejemplo:** un modelo multimodal genera el alt de las fotos de comprobante que sube el transportista. Cubre miles de imágenes que nadie describiría a mano, pero en una prueba describió "paquete entregado en mano" una foto de una puerta cerrada. La regla adoptada: el alt generado se limita a lo visible ("paquete junto a una puerta con el número 1450"), se marca como generado y el estado de la entrega sale del sistema, no de la descripción.

**Por qué importa:** un alt incorrecto es peor que uno ausente, porque la persona no tiene forma de verificarlo.

### Movimiento, zoom y reflow

Las animaciones grandes (paralaje, zoom, desplazamientos largos) pueden causar mareo a personas con trastornos vestibulares. Los sistemas operativos tienen la opción de reducir movimiento, que la web recibe con `prefers-reduced-motion`. Lo que se mueve solo por más de cinco segundos necesita poder pausarse (2.2.2).

Quienes tienen baja visión suelen usar zoom, no lector de pantalla. El texto debe poder ampliarse al 200 % (1.4.4) y, a **320 px CSS** de ancho (un monitor de 1280 px con zoom al 400 %), el contenido debe reacomodarse en una columna sin scroll horizontal (1.4.10), salvo tablas grandes, mapas o código. Un layout [responsive](#t/responsive) resuelve casi todo; lo que falla son anchos fijos, alturas fijas y barras fijas.

```css
@media (prefers-reduced-motion: reduce) {
  .cursor-escritura { animation: none; }
}
```

**Ejemplo:** el indicador de "escribiendo" del chat (cursor que parpadea y puntos que rebotan) pasa a ser el texto estático "Respondiendo…" con movimiento reducido. Y a 400 % de zoom, la barra superior y el campo de chat fijos ocupaban 240 px de 250 disponibles: con zoom alto dejan de ser fijos.

**Por qué importa:** la persona ya dijo lo que necesita en la configuración de su sistema; respetarlo cuesta unas líneas de CSS.

### Lectores de pantalla

Un lector de pantalla lee el árbol de accesibilidad en voz o en braille y permite navegar por encabezados, regiones, enlaces y controles:

| Lector | Plataforma | Notas |
|---|---|---|
| VoiceOver | macOS e iOS | Incluido; en Mac se activa con Cmd + F5 |
| NVDA | Windows | Gratuito, de código abierto y muy usado |
| JAWS | Windows | Comercial; frecuente en empresas |
| TalkBack | Android | Incluido; clave para la app de transportistas |

Cada combinación de lector y navegador tiene diferencias; una matriz razonable es NVDA con Chrome o Firefox, VoiceOver con Safari en Mac e iPhone, y TalkBack con Chrome.

**Ejemplo:** con VoiceOver, la ficha de entrega anunciaba "imagen, imagen, botón". Con nombres accesibles: "Llamar a Ana Pérez, botón; Navegar a Av. Siempre Viva 1450, botón; Marcar como entregado, botón".

**Por qué importa:** escuchar la propia interfaz diez minutos cambia la percepción del equipo más que cualquier informe.

### Cómo se prueba

Las pruebas van en capas, de la más barata a la más costosa:

1. **Automáticas** (axe, Lighthouse, linters de JSX): contraste, imágenes sin alt, campos sin etiqueta, ARIA inválido. Se suele citar que detectan **aproximadamente un 30 a 40 %** de los problemas de WCAG; la cifra varía según cómo se cuente, pero la mayoría queda afuera. Van en la CI.
2. **Teclado:** desconectar el mouse y completar las tareas principales.
3. **Lector de pantalla:** recorrer los flujos principales con al menos uno.
4. **Zoom y reflow:** 200 % de texto y 320 px de ancho.
5. **Personas con discapacidad** en las pruebas de usabilidad (ver [Investigación y pruebas de usabilidad](#t/investigacion-usabilidad)).

**Ejemplo:** el chat pasa axe sin errores. La prueba de teclado encuentra que el foco se pierde al aparecer la ficha de aprobación; la de NVDA, que se anuncia cada fragmento del streaming. Ninguno era detectable automáticamente.

**Por qué importa:** "100 en Lighthouse" significa que no están los problemas que Lighthouse sabe buscar, no que la interfaz sea accesible.

### Design system y agentes de código

La forma eficiente de escalar es resolver la accesibilidad en los componentes compartidos: el `Dialogo` del design system mueve el foco al abrir, lo atrapa, cierra con Escape y lo devuelve; cuarenta pantallas lo usan y ninguna reimplementa esa lógica. Los tokens de color se validan con la fórmula de contraste en ambos temas.

Los agentes de código reproducen los patrones más frecuentes de su entrenamiento, que incluyen muchos `div` con `onClick` e íconos sin nombre: el resultado se ve bien en una captura y falla con teclado. Lo que funciona: indicarlo en el archivo de instrucciones del repositorio (usar componentes del sistema y elementos nativos), reglas de accesibilidad del linter en la CI y **tests que buscan por rol** (`getByRole('button', { name: 'Reprogramar entrega' })`), que fallan si el control no existe en el árbol de accesibilidad.

**Ejemplo:** un agente de código genera el menú de motivos de no entrega con 15 `div` clicables. El test que busca `getAllByRole('radio')` falla; el agente lo reescribe con `fieldset` e `input type="radio"`, y de paso el menú gana navegación con flechas.

**Por qué importa:** los tests por rol convierten la accesibilidad en un criterio verificable que un agente puede cumplir solo.

## Casos prácticos

### El asistente que nadie podía usar con lector de pantalla

**Situación:** una operadora que usa NVDA reporta que el asistente es inutilizable: oye palabras sueltas mientras llega la respuesta, no sabe cuándo terminó y no se entera cuando el agente pide aprobación.

**Qué se hace:** se quita `aria-live` del mensaje y se usa una región `role="status"` aparte para anuncios breves; el mensaje se marca con `aria-busy` mientras llega texto y al terminar se anuncia "Respuesta lista". La ficha de aprobación recibe el foco al aparecer, con un encabezado que la nombra. Se suma una prueba con NVDA a la lista de verificación del componente (ver [UX de interfaces con agentes](#t/ux-agentes)).

### Contrato con requisito WCAG 2.2 AA

**Situación:** un cliente grande exige WCAG 2.2 AA en el panel de comercios para renovar, con auditoría externa en tres meses.

**Qué se hace:** primero, axe en la CI para limpiar lo automático. Segundo, prueba de teclado y de lector en los cinco flujos principales (crear pedido, buscar, reprogramar, consultar al asistente, descargar reportes), registrando hallazgos por criterio. Tercero, se corrigen primero los componentes del design system, que arreglan muchas pantallas a la vez. Lo pendiente se documenta con fecha en una declaración de accesibilidad.

### Fotos de comprobante descritas por un modelo

**Situación:** se propone generar el alt de las fotos de comprobante con un modelo de visión. En la prueba, el 8 % de las descripciones infiere cosas que la foto no muestra ("entregado al destinatario").

**Qué se hace:** el prompt limita la descripción a lo visible; el estado de la entrega viene del sistema y se muestra aparte; las descripciones se marcan como generadas. Se arma un golden set de 200 fotos con alt escritos por personas para comparar versiones del prompt (ver [Evaluación de LLMs](#t/evaluacion-llms)).

## Errores comunes

- **Quitar el outline de foco sin reemplazo.** Se usa `:focus-visible` con un indicador de al menos 3:1.
- **ARIA para arreglar HTML incorrecto.** `role="button"` en una `div` no agrega teclado ni foco; se usa el elemento nativo.
- **Regiones vivas sobre texto en streaming.** Saturan el lector; se anuncia inicio y fin, o por oraciones, desde una región aparte.
- **Placeholder como etiqueta y errores solo en rojo.** Desaparecen al escribir y no existen para el lector ni para quien no distingue el color.
- **Confiar en el puntaje automático o en el alt generado sin control.** Las herramientas encuentran una minoría de los problemas, y un alt que inventa es peor que ninguno.

## Para discutir en equipo

- ¿Qué flujos de Rumbo nunca probamos con teclado ni con lector de pantalla, y cuál probamos esta semana?
- ¿Qué parte de la accesibilidad debería garantizar el design system y cuál queda en cada equipo?
- ¿Cómo debería anunciar el chat los pasos de un agente sin saturar a quien usa lector de pantalla?
- ¿Qué reglas de accesibilidad agregaríamos a las instrucciones de los agentes de código, y cómo las verificamos en la CI?
- ¿Qué criterios AAA valen la pena en la app de transportistas por su uso en la calle?
