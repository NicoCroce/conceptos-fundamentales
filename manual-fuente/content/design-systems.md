---
slug: design-systems
titulo: Design systems para interfaces con agentes
resumen: Qué es un design system, cómo se construye con tokens, componentes, accesibilidad y gobierno, y qué patrones propios necesitan las interfaces con agentes.
lectura: 15
---

## La idea central

Cuando varias aplicaciones las hacen equipos distintos, cada pantalla termina tomando sus propias decisiones: qué gris usar, cuánto espacio dejar, cómo se ve un error, qué pasa al presionar Escape. Al principio no se nota; un año después hay siete tonos de azul, tres botones primarios que se comportan distinto y un tema oscuro que nadie se anima a tocar. Un **design system** es la respuesta organizativa a ese problema: un conjunto compartido de decisiones de diseño, convertidas en código reutilizable, documentadas y con dueños claros.

La analogía es un sistema de señalización vial. Nadie diseña un cartel de "pare" nuevo para cada esquina: hay formas, colores y reglas de ubicación que todos reconocen, y por eso se leen sin pensar. Con las interfaces de agentes este acuerdo se vuelve más importante, porque aparecen estados que antes no existían: texto que llega de a pedazos, herramientas que se ejecutan en segundo plano, acciones que esperan la aprobación de una persona. Si cada equipo los resuelve a su manera, el usuario no sabe cuándo el agente está pensando, cuándo terminó y, sobre todo, qué está a punto de hacer.

## Conceptos

### Qué es (y qué no es) un design system

Tres términos se usan como sinónimos y no lo son:

- **Guía de estilo:** un documento con reglas visuales y de tono (colores de marca, tipografía, cómo se escriben los mensajes de error). Es una referencia; nadie la "instala".
- **Biblioteca de componentes:** código reutilizable (botones, campos, diálogos) que se instala como dependencia. Resuelve la implementación, pero no dice cuándo usar cada pieza.
- **Design system:** el conjunto completo. Incluye **tokens** (las decisiones de diseño en forma de datos), **componentes**, **patrones** (combinaciones de componentes para resolver un problema recurrente, como "formulario con validación" o "conversación con un agente"), **documentación** con ejemplos y criterios de uso, y **gobierno**: quién decide, cómo se proponen cambios y cómo se versionan.

**Ejemplo:** en Rumbo, la biblioteca tiene un componente `Dialogo`. El design system además define el patrón "confirmación de acción riesgosa": cuándo se usa, qué texto lleva el botón principal (un verbo concreto, no "Aceptar"), qué pasa con el foco y cómo se registra la decisión.

**Por qué importa:** muchos equipos creen tener un design system porque tienen una biblioteca. Sin patrones, documentación y gobierno, la biblioteca se usa de formas inconsistentes y termina fragmentándose igual.

### Design tokens: primitivos y semánticos

Un **token** es una decisión de diseño con nombre: un color, un espaciado, un radio de borde, una duración de animación. Se guardan como datos (habitualmente JSON) y una herramienta los transforma en variables CSS, constantes de Swift o Kotlin, o lo que necesite cada plataforma.

Hay dos niveles que conviene separar:

1. **Tokens primitivos:** la paleta cruda, sin significado de uso. `color.gris.50 = #f6f7f9`, `color.gris.900 = #121417`, `espacio.4 = 16px`.
2. **Tokens semánticos:** el propósito, que apunta a un primitivo. `color.superficie`, `color.texto.principal`, `color.borde.foco`, `color.estado.error`.

Los componentes **solo usan tokens semánticos**. Un botón no dice "azul 600"; dice "color de acción principal". Así se puede cambiar la paleta, o tener varios temas, sin tocar un solo componente.

La convención de nombres importa más de lo que parece. Un esquema habitual es `categoría.propósito.variante.estado`: `color.accion.principal.hover`. Nombres como `color.azul-claro-nuevo` envejecen mal, porque describen el valor y no el uso.

### Temas claro y oscuro con tokens

Un tema es simplemente **otra asignación de los tokens semánticos a primitivos**. El componente no cambia; cambia a qué valor apunta cada nombre.

| Token semántico | Tema claro | Tema oscuro |
|---|---|---|
| `color.superficie` | `gris.0` (#ffffff) | `gris.900` (#121417) |
| `color.superficie.elevada` | `gris.0` con sombra | `gris.800` (#1c1f24) |
| `color.texto.principal` | `gris.900` (#121417) | `gris.50` (#f6f7f9) |
| `color.texto.secundario` | `gris.600` (#5b6270) | `gris.300` (#a9afba) |
| `color.estado.error` | `rojo.600` (#c62828) | `rojo.300` (#ef8a80) |

Fíjate en `color.superficie.elevada`: en tema claro la elevación se expresa con sombra, pero en oscuro las sombras casi no se ven, así que se usa una superficie un poco más clara. Ese tipo de decisión vive en los tokens, no en cada componente.

```css
:root {
  --color-superficie: #ffffff;
  --color-texto-principal: #121417;
}
:root[data-tema="oscuro"] {
  --color-superficie: #121417;
  --color-texto-principal: #f6f7f9;
}
.burbuja-mensaje {
  background: var(--color-superficie);
  color: var(--color-texto-principal);
}
```

**Distribución:** desde la misma fuente JSON se generan variables CSS para la web, constantes para la app móvil de transportistas y valores para las herramientas de diseño. Si el equipo de producto cambia `color.estado.error`, el cambio llega a las tres plataformas en la siguiente versión del paquete de tokens, sin que nadie copie hexadecimales a mano.

### Componentes y diseño de su API

Un componente de un design system es una API pública, y se diseña con el mismo cuidado que un contrato entre servicios. Cuatro decisiones aparecen siempre:

- **Variantes:** formas visuales distintas del mismo componente, expresadas con un parámetro acotado (`variante: "principal" | "secundaria" | "peligro"`), no con diez booleanos que pueden combinarse de formas imposibles.
- **Estados:** reposo, hover, foco, presionado, deshabilitado, cargando, error. Cada uno debe estar diseñado y documentado; el estado de foco olvidado es el más común.
- **Composición:** en lugar de un componente gigante con 40 propiedades, piezas pequeñas que se combinan. Un `Mensaje` compuesto por `Mensaje.Autor`, `Mensaje.Contenido` y `Mensaje.Acciones` es más flexible que un `Mensaje` con `mostrarAutor`, `mostrarAcciones`, `accionesExtra`.
- **Controlado frente a no controlado:** un componente **controlado** recibe su valor desde afuera y avisa cuando debería cambiar; el que lo usa tiene el control total. Uno **no controlado** guarda su propio estado interno. Los buenos componentes soportan ambos: no controlado por defecto (fácil de usar) y controlado cuando hace falta (por ejemplo, un campo de chat cuyo texto se limpia desde el código al enviar).

**Ejemplo:** si el componente `CampoChat` es solo no controlado, el equipo del asistente no puede vaciarlo después de enviar ni restaurar un borrador. Si es solo controlado, cada uso simple obliga a escribir estado y manejadores.

### Accesibilidad incorporada

La ventaja más subestimada de un design system es que la accesibilidad se resuelve **una vez** y todos la heredan. Los puntos básicos:

- **Contraste:** las pautas WCAG piden una relación de al menos **4,5:1** entre texto normal y fondo, y 3:1 para texto grande y componentes de interfaz (bordes de campos, íconos con significado). La relación se calcula a partir de la luminancia relativa de cada color: `(L1 + 0,05) / (L2 + 0,05)`, con L1 la más clara. El blanco tiene luminancia 1; el gris `#767676`, aproximadamente 0,18. Resultado: 1,05 / 0,23 ≈ 4,5:1, justo en el límite. Un gris `#999999` sobre blanco da cerca de 2,8:1 y no pasa. Si los tokens semánticos se validan automáticamente con esta fórmula, ningún componente puede introducir texto ilegible.
- **Foco visible y gestión del foco:** todo lo interactivo muestra un indicador de foco claro. Al abrir un diálogo, el foco entra en él y queda atrapado dentro; al cerrarlo, vuelve al elemento que lo abrió.
- **Teclado:** todo lo que se hace con el mouse se puede hacer con teclado. Enter envía, Escape cierra, las flechas recorren listas.
- **Lectores de pantalla:** elementos semánticos (`button`, `dialog`, `nav`), etiquetas en cada control y anuncios de cambios dinámicos con regiones `aria-live`.
- **Movimiento reducido:** si el usuario configuró `prefers-reduced-motion`, las animaciones se acortan o se eliminan. Los tokens de duración pueden tener un valor alternativo para ese caso.

### Documentación y playgrounds

Un componente que no está documentado no existe para los equipos. La documentación útil tiene, por cada componente: para qué sirve y para qué **no**, ejemplos vivos de cada variante y estado, la API completa, notas de accesibilidad (qué se anuncia, qué teclas funcionan) y ejemplos de uso correcto e incorrecto.

Un **playground** (herramientas como Storybook) muestra cada componente aislado, con controles para cambiar sus propiedades en vivo. Además de documentar, sirve como entorno de pruebas: tests visuales que comparan capturas entre versiones, y tests automáticos de accesibilidad sobre cada historia.

### Versionado, deprecaciones y adopción

El paquete del design system se versiona con **semver**: `MAYOR.MENOR.PARCHE`. Un parche corrige errores sin cambiar la API; una versión menor agrega cosas compatibles; una mayor rompe algo. Para un design system, "romper" incluye cambios que no son de tipos: cambiar el valor por defecto de una variante, el espaciado interno de un botón o el orden del foco puede romper pantallas sin que el compilador diga nada.

Las eliminaciones siguen un camino gradual: se marca la pieza como **deprecada** con un aviso en consola y en la documentación, se publica la alternativa, se da un plazo y se retira en la siguiente versión mayor. Cuando el cambio es mecánico (renombrar una propiedad, cambiar `tipo` por `variante`), se acompaña con un **codemod**, un script que reescribe automáticamente el código de los equipos consumidores.

Para saber si el sistema se usa, se miden métricas de **adopción**: qué porcentaje de las pantallas usa componentes del sistema, qué versión usa cada aplicación, cuántos colores hexadecimales "sueltos" quedan en el código. Un análisis estático en la CI puede contar estos casos.

### Gobierno y modelo de contribución

Alguien tiene que ser dueño. Los modelos habituales son:

- **Centralizado:** un equipo dedicado construye y decide todo. Es consistente, pero se vuelve cuello de botella.
- **Federado:** representantes de cada equipo de producto deciden juntos. Hay más velocidad y adopción, pero menos coherencia si no hay reglas claras.
- **Híbrido:** un equipo pequeño mantiene el núcleo (tokens, componentes base, accesibilidad) y acepta contribuciones de los equipos de producto con un proceso definido: propuesta, revisión de diseño y accesibilidad, implementación con tests y documentación.

Para Rumbo, con pocos ingenieros de frontend, un modelo híbrido suele funcionar: dos personas como núcleo y contribuciones de los equipos del panel de comercios, la consola de operaciones y el asistente.

### Patrones específicos para interfaces con agentes

Los agentes introducen patrones que el sistema debe definir una sola vez. Los principales:

**Mensajes de chat.** Un componente de mensaje con roles (usuario, asistente, sistema, herramienta), autor, hora, contenido y acciones. El rol determina la alineación y el estilo, siempre con tokens semánticos.

**Texto en streaming.** La respuesta llega token a token. El componente debe:

1. Mostrar un cursor o indicador mientras llega texto y quitarlo al terminar.
2. Renderizar markdown parcial con tolerancia: un bloque de código abierto que todavía no se cerró no debe romper el resto del mensaje ni hacer saltar el contenido. Una estrategia es renderizar como texto plano la última línea incompleta y aplicar formato a lo ya cerrado.
3. Evitar **saltos de diseño**: reservar espacio, no reordenar mensajes y no mover el scroll si el usuario subió a leer algo anterior.

**Estados de herramientas.** Cuando el agente usa herramientas (ver [Agentes y tool calling](#t/agentes)), la interfaz muestra en qué estado está cada una. El sistema define un único componente con estos estados:

| Estado | Qué ve el usuario | Acciones disponibles | Anuncio accesible |
|---|---|---|---|
| Pendiente | "Va a consultar el pedido P-1042" en gris | Cancelar | Ninguno |
| En ejecución | Indicador animado y nombre de la herramienta | Detener | "Consultando el pedido" (una vez) |
| Requiere aprobación | Ficha destacada con el detalle exacto de la acción | Aprobar, rechazar, editar | "Se necesita tu aprobación", con el foco en la ficha |
| Fallida | Ícono y mensaje de error comprensible | Reintentar, ver detalle | "No se pudo consultar el pedido" |
| Completada | Resumen breve, detalle plegable | Ver entrada y salida | "Consulta completada" (o silencio si hay más pasos) |

**Diálogos de aprobación humana.** Cuando el agente propone una acción con efectos, el diálogo muestra **exactamente** lo que se va a ejecutar: la herramienta, los parámetros reales y el alcance ("reprogramar 37 pedidos de la zona norte al jueves 14, franja 9 a 12"), no un resumen redactado por el modelo. El botón principal nombra la acción ("Reprogramar 37 pedidos"), no dice "Aceptar". Las acciones irreversibles usan la variante de peligro y no reciben el foco por defecto.

**Citas y fuentes.** En respuestas con [RAG](#t/rag), cada afirmación relevante enlaza al fragmento del documento de donde salió, con el título y la sección. Sin fuentes, el componente lo indica.

**Incertidumbre y errores.** Mensajes distintos para "no encontré información sobre esto", "el servicio no respondió" y "esta acción no está permitida". Un error genérico ("algo salió mal") lleva a reintentar cosas que no tienen sentido reintentar.

**Detener y regenerar.** Mientras hay una respuesta en curso, el botón de enviar se convierte en "Detener". Al terminar, aparece "Regenerar". Detener corta también el consumo de tokens en el backend, no solo el dibujo en pantalla.

**Retroalimentación.** Botones de pulgar arriba y abajo, con un campo opcional de comentario al marcar una respuesta negativa. El evento se registra con el id de la traza, para que sirva luego como caso de [evaluación](#t/evaluacion-llms).

**Accesibilidad del streaming.** Una región `aria-live="assertive"` que se actualiza con cada token hace que el lector de pantalla interrumpa constantemente o repita fragmentos sueltos. Lo correcto es usar `aria-live="polite"`, anunciar "El asistente está respondiendo" al empezar y anunciar el mensaje completo (o por oraciones) al terminar, con `aria-busy="true"` mientras el contenido cambia.

## Casos prácticos

### Tres equipos, tres burbujas de chat

**Situación:** el asistente de soporte, el agente de operaciones y un prototipo de ayuda para comercios tienen cada uno su propio componente de mensaje. Uno muestra las herramientas como texto plano, otro como íconos sin etiqueta y el tercero no las muestra. Un operador que usa dos de esas herramientas en el mismo día interpreta mal el estado de una investigación.

**Qué se hace:** se crea en el design system un patrón "conversación con agente": `Mensaje`, `EstadoHerramienta`, `DialogoAprobacion` y `Fuentes`, con la tabla de estados como especificación. Se migra primero el agente de operaciones (el de mayor riesgo), luego el asistente y por último el prototipo. Un codemod reemplaza las importaciones viejas, y una métrica de adopción en la CI cuenta los componentes de mensaje propios que quedan.

### El tema oscuro roto por colores fijos

**Situación:** al lanzar el tema oscuro en el panel de comercios, la mitad de las pantallas se ve bien y la otra mitad muestra texto gris oscuro sobre fondo casi negro. La causa: cientos de colores hexadecimales escritos a mano en lugar de tokens semánticos.

**Qué se hace:** se agrega una regla de lint que prohíbe colores literales fuera del paquete de tokens, con una lista de excepciones temporal y una fecha de vencimiento. Se escribe un codemod que reemplaza los valores más frecuentes por su token semántico equivalente, y los casos ambiguos se revisan a mano. Los tokens semánticos se validan en la CI con la fórmula de contraste para ambos temas, de modo que un nuevo par texto/fondo por debajo de 4,5:1 bloquea la publicación.

### Un operador aprobó la acción equivocada

**Situación:** el agente de operaciones propone "reprogramar los pedidos afectados por la tormenta". El diálogo de aprobación muestra ese texto, generado por el modelo, y un botón "Aceptar". El operador aprueba, pero el agente había seleccionado pedidos de dos zonas, no de una, y se reprograman 180 entregas en lugar de 40.

**Qué se hace:** el `DialogoAprobacion` se rediseña para mostrar los parámetros reales de la llamada a la herramienta, no la descripción del modelo: zonas, cantidad de pedidos, fecha y franja nuevas, con una lista desplegable de los pedidos afectados. El botón dice "Reprogramar 180 pedidos" y, por encima de un umbral (por ejemplo, 100), se pide escribir la cantidad para confirmar. La aprobación queda registrada con el usuario, la hora y los parámetros, y se vincula a la traza del agente (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

### Lectores de pantalla abrumados por el streaming

**Situación:** usuarios de lectores de pantalla del equipo de soporte reportan que el asistente es inutilizable: cada fragmento de texto interrumpe la lectura y oyen palabras sueltas durante 20 segundos.

**Qué se hace:** el componente de mensaje cambia la región de `assertive` a `polite`, marca el mensaje con `aria-busy` mientras llega texto y anuncia el contenido completo al terminar, o por oraciones si la respuesta es larga. Los estados de herramientas se anuncian una sola vez al cambiar. Se suma al playground una historia con streaming simulado y una prueba manual con lector de pantalla en la lista de verificación de cada versión.

## Errores comunes

- **Confundir la biblioteca de componentes con el design system.** Sin tokens, patrones, documentación y gobierno, cada equipo usa las piezas a su manera y la inconsistencia vuelve.
- **Usar tokens primitivos en los componentes.** Cualquier cambio de tema obliga a tocar componentes; se usan solo tokens semánticos.
- **Mostrar en la aprobación lo que el modelo dice que va a hacer.** La persona aprueba un texto, no una acción; se muestran los parámetros reales de la herramienta.
- **Anunciar cada token a los lectores de pantalla.** Se usa `polite`, `aria-busy` y anuncios por mensaje u oración.
- **Cambios de comportamiento publicados como versión menor.** Cambiar valores por defecto o el orden del foco rompe pantallas; se tratan como versión mayor o se protegen con una opción.
- **Un "Detener" que solo oculta el texto.** Si el backend sigue generando, se consumen tokens y herramientas; detener debe cancelar la ejecución.

## Para discutir en equipo

- ¿Qué decisiones de diseño de nuestras interfaces con agentes viven hoy en una sola aplicación y deberían subir al design system?
- ¿Qué información mínima debe mostrar un diálogo de aprobación para que la persona entienda el alcance real de la acción?
- ¿Qué modelo de gobierno es realista con el tamaño actual del equipo, y quién revisa accesibilidad en cada contribución?
- ¿Cómo medimos si los estados de herramientas reducen los reenvíos y las aprobaciones equivocadas?
- ¿Qué cambios de un componente consideramos incompatibles aunque el compilador no los detecte?
