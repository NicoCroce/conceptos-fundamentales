---
slug: leyes-ux-diseno-visual
titulo: Leyes de UX y diseño visual
resumen: Principios de percepción, leyes de interacción y reglas de tipografía, color y espaciado que explican por qué una interfaz se entiende rápido o confunde.
lectura: 16
---

## La idea central

Muchas discusiones de diseño se resuelven por gusto: "a mí me gusta más así". Las leyes de UX cambian esa conversación por otra más útil: cómo percibe una persona lo que ve, cuánto tarda en alcanzar un botón, cuánto le cuesta elegir y qué recuerda de una experiencia. No son leyes físicas, sino regularidades observadas en estudios de psicología e interacción persona-computadora. Algunas tienen fórmula y sirven para estimar; otras son heurísticas que orientan.

La analogía es la ergonomía de una cocina: nadie discute por gusto a qué altura va la mesada. Este tema recorre esas regularidades, desde la percepción hasta el diseño visual concreto (tipografía, color, espaciado), y termina aplicándolas a algo que el equipo diseña todos los días: la respuesta de un agente en un chat. Complementa a [Fundamentos de UX y UI](#t/ux-ui-fundamentos) y a las [heurísticas de Nielsen](#t/heuristicas-nielsen).

## Conceptos

### Principios de la Gestalt

La psicología de la Gestalt estudió cómo el cerebro agrupa elementos sueltos en formas con sentido. Antes de leer una palabra, el ojo ya decidió qué va con qué. Los principios más útiles:

- **Proximidad:** lo que está cerca se percibe como grupo. Es el principio más fuerte y el más barato: alcanza con espacio.
- **Similitud:** lo que se parece (color, forma, tamaño) se percibe como relacionado. Si los enlaces son azules, un texto azul que no es enlace confunde.
- **Región común:** lo que comparte un borde o un fondo se percibe como grupo. Es lo que hace funcionar a las fichas (cards).
- **Continuidad:** el ojo sigue líneas y alineaciones; una columna de campos alineada se lee como secuencia.
- **Figura y fondo:** el cerebro separa lo que está "adelante" de lo que está "atrás". Un diálogo con el fondo oscurecido dice "ahora solo importa esto".

**Ejemplo:** en el panel de comercios, la ficha de un pedido mostraba destinatario, dirección, teléfono, estado y ETA con 16 px entre todas las líneas, y la gente leía el estado como un dato de contacto. Con 8 px dentro del grupo de contacto y 24 px antes del bloque de estado y ETA, el agrupamiento aparece solo, sin agregar un borde.

**Por qué importa:** cuando el agrupamiento visual contradice el lógico, la persona tiene que leer todo para entender la estructura. Corregirlo suele costar unos píxeles de espacio.

### Ley de Fitts

La ley de Fitts estima el tiempo para llevar un puntero o un dedo hasta un objetivo, según la distancia (D) y el tamaño del objetivo en la dirección del movimiento (W):

`T = a + b · log2(D / W + 1)`

El término `log2(D / W + 1)` es el **índice de dificultad**, en bits; `a` y `b` dependen de la persona y el dispositivo. Objetivos más grandes y cercanos se alcanzan más rápido, y como el efecto es logarítmico, duplicar el tamaño no duplica la velocidad. En escritorio, los bordes de la pantalla son objetivos "infinitos" porque el cursor se frena solo; en un teléfono no.

**Ejemplo:** en la app de transportistas, el botón "Entregado" mide 10 mm y está arriba a la derecha, a unos 80 mm del pulgar cuando el teléfono se usa con una mano. Índice: log2(80/10 + 1) = log2(9) ≈ 3,17 bits. Con constantes hipotéticas a = 0,1 s y b = 0,15 s/bit: 0,1 + 0,15 × 3,17 ≈ 0,58 s, y además obliga a estirar el pulgar o usar la otra mano, que suele sostener el paquete. Como barra de 20 mm de alto abajo, a 30 mm del pulgar: log2(30/20 + 1) ≈ 1,32 bits, unos 0,30 s. Con 120 entregas por día son más de 30 segundos, pero sobre todo menos toques fallidos con guantes o en movimiento.

**Por qué importa:** las acciones frecuentes van grandes y en la zona del pulgar; las peligrosas ("Marcar como fallida") pueden ir más lejos a propósito.

### Ley de Hick

La ley de Hick-Hyman dice que el tiempo para decidir crece con el logaritmo de la cantidad de opciones igualmente probables:

`T = a + b · log2(n + 1)`

Pasar de 2 a 4 opciones agrega lo mismo que pasar de 8 a 16. Se cumple bien cuando la persona tiene que considerar todas las opciones; con opciones conocidas o listas ordenadas alfabéticamente, el efecto se reduce.

**Ejemplo:** el menú "¿Qué pasó con la entrega?" tiene 15 motivos: log2(16) = 4 bits. Con b = 0,2 s/bit (hipotético), decidir agrega unos 0,8 s. Si se muestran primero los 5 motivos más frecuentes y un "Otros motivos", la primera decisión es entre 6: log2(7) ≈ 2,8 bits, unos 0,56 s. El ahorro de tiempo es chico; el de errores por cansancio es lo que más se nota en los datos.

**Por qué importa:** cada opción agregada tiene un costo. Ordenar por frecuencia y mostrar primero lo probable reduce tiempo y errores.

### Ley de Jakob y ley de Miller (y el mal uso del 7±2)

La **ley de Jakob** (de Jakob Nielsen) dice que las personas pasan la mayor parte del tiempo en otros productos y esperan que el nuestro funcione igual: el logo lleva al inicio, el campo de chat está abajo con el botón de enviar a la derecha. Romper una convención tiene un costo de aprendizaje que solo vale si la mejora es grande.

La **ley de Miller** viene de un artículo de 1956 sobre la memoria de corto plazo: retenemos "siete, más o menos dos" elementos. Trabajos posteriores bajaron el número a unos cuatro bloques (chunks) y mostraron que depende del tipo de información. El mal uso habitual es "un menú no puede tener más de siete opciones". Un menú está a la vista: la persona **reconoce**, no **recuerda**. Miller aplica cuando hay que retener algo en la cabeza.

**Ejemplo:** el código de seguimiento `RB8K2M7Q4X` se dicta mucho mejor a soporte si se muestra en bloques: `RB8 K2M 7Q4X`. Eso es aplicar bien a Miller. Limitar el menú lateral del panel a siete entradas "por Miller", no.

**Por qué importa:** citar una ley fuera de su dominio da argumentos falsos con apariencia de rigor.

### Ley de Tesler: la complejidad se conserva

Larry Tesler propuso que todo proceso tiene una complejidad que no se elimina, solo se traslada: la absorbe el sistema o la absorbe el usuario. Simplificar una interfaz muchas veces significa mover trabajo al backend.

**Ejemplo:** para reprogramar una entrega, el panel pedía elegir fecha y franja, verificar la capacidad de la zona y confirmar. La versión nueva muestra solo franjas con capacidad, ya calculadas por el servicio de asignación. La complejidad pasó al backend. Con un agente pasa lo mismo: si el comercio escribe "pásalo al jueves a la tarde", el agente tiene que resolver qué es "la tarde", qué franjas hay y qué hacer si no hay lugar.

**Por qué importa:** cuando alguien dice "esto es simple para el usuario", la pregunta siguiente es quién absorbe la complejidad y si ese equipo lo sabe.

### Umbral de Doherty y regla pico-final

El **umbral de Doherty** viene de un estudio de IBM de 1982: si el sistema responde en menos de unos **400 ms**, las personas mantienen el ritmo de trabajo; por encima, la atención se dispersa. No significa que todo termine en 400 ms, sino que en ese tiempo tiene que haber **alguna** respuesta visible: un estado, un indicador, el primer texto.

La **regla pico-final**, de Daniel Kahneman, dice que juzgamos una experiencia por su momento más intenso y por cómo terminó, no por el promedio.

**Ejemplo:** el asistente de soporte tarda 5 s en responder. Si en 300 ms aparece "Buscando el pedido RB8K2M7Q4X…" y el texto llega en streaming desde el segundo 1, se siente fluido. Si la conversación termina con el problema resuelto, se recuerda bien aunque hubo una aclaración incómoda en el medio; si termina en "No pude ayudarte" sin salida, se recuerda mal aunque todo lo anterior fuera bueno.

**Por qué importa:** con agentes la latencia total es de segundos; el primer feedback y el cierre pesan más que optimizar el medio (ver [UX de interfaces con agentes](#t/ux-agentes)).

### Jerarquía visual

La jerarquía visual ordena qué ve el ojo primero, segundo y tercero, combinando tamaño, peso, color y contraste, posición y espacio. Una prueba simple es **entrecerrar los ojos**: si con la pantalla borrosa no se distingue lo principal, la jerarquía falla. Idealmente hay una sola acción principal por pantalla; si todo está en negrita, nada lo está.

**Ejemplo:** en la ficha de entrega, lo primero que se necesita es la dirección (22 px semibold), después el destinatario y las indicaciones (17 px regular) y por último el número de pedido (13 px, gris secundario). "Entregado" es el único botón con color de marca sólido.

**Por qué importa:** la jerarquía permite usar una pantalla sin leerla entera, que es como la usa alguien entre una entrega y otra.

### Tipografía: escala, largo de línea e interlineado

Tres decisiones explican casi toda la legibilidad:

1. **Escala tipográfica.** Se parte de un tamaño base y se multiplica por una razón fija. Con base 16 px y razón 1,25: 16, 20, 25, 31, 39 px. Cinco o seis pasos alcanzan, y cada uno se vuelve un token del [design system](#t/design-systems).
2. **Largo de línea.** Para texto corrido, entre **45 y 75 caracteres** por línea. Más largas, el ojo pierde el renglón al volver; más cortas, la lectura se entrecorta. En CSS, `max-width: 65ch`.
3. **Interlineado.** Para el cuerpo, alrededor de **1,4 a 1,6** veces el tamaño de letra; los títulos grandes, 1,1 a 1,3. Las pautas de accesibilidad piden que el contenido siga funcionando si el usuario sube el interlineado a 1,5.

```css
.mensaje-asistente { font-size: 1rem; line-height: 1.55; max-width: 65ch; }
```

**Ejemplo:** el panel mostraba las políticas de entrega a todo el ancho de un monitor de 27 pulgadas, unos 180 caracteres por línea. Con `65ch` e interlineado 1,55, el texto ocupa más alto pero se lee sin perder el renglón.

**Por qué importa:** los agentes producen mucho texto corrido; sin estos ajustes, una buena respuesta se ve como un bloque intimidante.

### Color: 60-30-10, colores semánticos y no depender solo del color

La regla **60-30-10** es una guía de proporciones: alrededor del 60 % de la superficie en un neutro dominante, 30 % en un secundario y 10 % en un acento para acciones y estados importantes. Evita el error de usar el color de marca en todas partes, con lo que deja de señalar algo.

Los **colores semánticos** (éxito, advertencia, error, información) se definen como tokens, no como valores sueltos, para que sean consistentes y cambien con el tema. Y la regla más importante: **no depender solo del color**. Alrededor del 8 % de los hombres y del 0,5 % de las mujeres tienen alguna forma de daltonismo, y rojo y verde son los más difíciles de distinguir. Todo estado comunicado con color necesita un segundo canal: ícono, texto o forma.

**Ejemplo:** el tablero de operaciones marcaba zonas atrasadas en rojo y normales en verde; para un operador con deuteranopía, el mapa era de un solo color. La versión corregida agrega un ícono de alerta y el texto "12 atrasadas". Además, el verde `#16A34A` como texto sobre blanco da 3,3:1, que no alcanza para texto normal: queda para íconos y fondos (ver [Accesibilidad web](#t/accesibilidad)).

**Por qué importa:** el color es el canal más rápido para llamar la atención y el menos confiable para transmitir significado por sí solo.

### Espaciado y grillas

En lugar de espacios a ojo (7 px acá, 13 px allá), se usa una escala de múltiplos de 4 u 8: 4, 8, 12, 16, 24, 32, 48, 64. La **grilla de 8 puntos** es la convención más común, con el 4 para ajustes finos. Reduce decisiones (entre 16 y 24 se elige rápido) y expresa la proximidad de la Gestalt: una regla práctica es que el espacio entre grupos sea al menos el doble que dentro de un grupo.

Las **grillas de layout** dividen el ancho en columnas con separaciones (gutters) y márgenes fijos: por ejemplo, 12 columnas en escritorio, 8 en tablet y 4 en teléfono, con gutters de 16 a 24 px. Los elementos ocupan un número entero de columnas, y eso produce alineaciones que el ojo detecta sin que nadie las piense una por una.

**Ejemplo:** el formulario de alta de pedido usa 8 px entre etiqueta y campo, 16 px entre campos de un bloque y 32 px entre bloques (destinatario, paquete, ventana horaria). En escritorio, la lista de pedidos ocupa 8 columnas y el chat con el asistente 4; en teléfono, cada uno ocupa las 4 y el chat pasa a una pestaña (ver [Diseño responsive](#t/responsive)).

**Por qué importa:** la escala y la grilla son un acuerdo entre diseño y frontend; con ellas, pantallas hechas por personas distintas se ven parte del mismo producto.

### Objetivos táctiles

Un dedo es mucho menos preciso que un cursor:

| Referencia | Tamaño mínimo | Equivalente físico aproximado |
|---|---|---|
| Apple (Human Interface Guidelines) | 44 × 44 pt | unos 7 mm |
| Material Design (Android) | 48 × 48 dp | unos 7 a 8 mm |
| WCAG 2.2, criterio 2.5.8 (AA) | 24 × 24 px CSS, o espacio equivalente alrededor | piso, no ideal |
| WCAG 2.2, criterio 2.5.5 (AAA) | 44 × 44 px CSS | |

El área tocable puede ser mayor que el dibujo: un ícono de 24 px con padding hasta 48 px. También importa la separación entre objetivos.

**Ejemplo:** "Llamar" y "Navegar" eran íconos de 24 × 24 px a 4 px uno del otro, y un 6 % de las llamadas se cortaba en menos de 2 segundos: toques accidentales. Con áreas de 48 × 48 y 8 px de separación, bajó a menos del 1 %.

**Por qué importa:** con guantes, en movimiento o con una mano ocupada, conviene ir por encima del mínimo de las guías.

### Modo oscuro

El modo oscuro no es invertir colores:

- **Evitar negro puro con blanco puro:** el contraste extremo produce un halo en el texto. Se usa un gris muy oscuro (por ejemplo `#121212`) y texto blanco atenuado.
- **La elevación se expresa con luminosidad:** las sombras casi no se ven, así que las superficies más altas (un menú, un diálogo) son algo más claras.
- **Desaturar los acentos:** un azul saturado vibra sobre fondo oscuro.
- **Verificar el contraste en ambos temas:** el azul `#2F6FEB` da 4,57:1 sobre blanco (pasa) y 4,1:1 sobre `#121212` (no pasa para texto normal). El token semántico necesita un valor por tema.

**Ejemplo:** la app de transportistas se usa mucho de noche. En oscuro, "Entregado" usa un azul más claro y menos saturado, y el mapa cambia a un estilo oscuro para no encandilar al conductor.

**Por qué importa:** un modo oscuro hecho a último momento rompe el contraste en decenas de lugares; con tokens semánticos por tema, es una configuración.

### Aplicado a la respuesta de un agente

El modelo produce markdown, pero cómo se dibuja es una decisión de diseño que tiene que vivir en el componente y en el prompt, porque nadie revisa cada respuesta antes de mostrarla:

1. **Conclusión primero.** En respuestas de más de tres o cuatro oraciones, la respuesta directa en una línea y después el detalle. Se pide en el prompt del sistema.
2. **Énfasis escaso.** El prompt limita la negrita a datos clave (una fecha, un pedido); el estilo usa semibold, no un bold marcado.
3. **Listas y tablas con la escala de espaciado:** 4 a 8 px entre ítems, 16 px antes y después.
4. **Respuestas largas plegables:** por encima de un umbral (por ejemplo, 250 palabras), resumen y "Ver detalle". Ancho máximo de 65ch.
5. **Datos accionables como componentes:** un estado de envío es un chip con ícono y texto, no una palabra en verde.

**Ejemplo:** a "¿Por qué se atrasó el pedido RB8K2M7Q4X?", la primera versión respondía con 6 párrafos y 11 frases en negrita. La nueva: una línea con la causa ("Hubo un desvío por un corte de calle; nueva ETA 16:40"), un chip de estado, tres pasos de lo que pasó y "Ver historial completo".

**Por qué importa:** en un chat el contenido cambia en cada respuesta; las reglas visuales tienen que aplicarse solas.

## Casos prácticos

### El botón de entrega que se tocaba por error

**Situación:** "Entregado" y "No entregado" son dos botones iguales, juntos, en la parte superior de la app. Soporte recibe 40 reclamos por semana de entregas marcadas como fallidas que sí se entregaron.

**Qué se hace:** Fitts en las dos direcciones: "Entregado", la acción frecuente, pasa a una barra ancha abajo; "No entregado" se vuelve un enlace secundario que abre el menú de motivos (con los 5 frecuentes primero, por Hick). Se distinguen por posición, texto y color, no solo por color, y marcar "No entregado" muestra "Deshacer" durante 5 segundos. Se mide la tasa de correcciones dos semanas antes y después.

### El 7±2 en la revisión de diseño

**Situación:** en una revisión del menú lateral del panel, alguien rechaza una propuesta con 9 secciones "porque Miller dice que el máximo es 7". La alternativa esconde "Reprogramaciones", la segunda sección más usada, dentro de otra.

**Qué se hace:** se aclara que el menú está a la vista y la persona reconoce, no recuerda. Se aplica Hick con frecuencia de uso: las 9 secciones se ordenan según la analítica, se agrupan en dos bloques por proximidad y se valida con una prueba rápida con cinco comercios (ver [Investigación y pruebas de usabilidad](#t/investigacion-usabilidad)).

### Respuestas del asistente que nadie terminaba de leer

**Situación:** las respuestas sobre políticas de entrega promedian 380 palabras a todo el ancho del panel, y el 60 % de los usuarios vuelve a preguntar lo mismo con otras palabras.

**Qué se hace:** el prompt pide la respuesta directa en la primera oración y limita el énfasis; el componente de mensaje limita el ancho a 65ch, usa interlineado 1,55 y la escala de espaciado; las respuestas de más de 250 palabras se pliegan con resumen. Se mide la tasa de reformulación antes y después.

## Errores comunes

- **Citar leyes fuera de su dominio.** El 7±2 no limita los ítems de un menú; antes de usar una ley para cerrar una discusión, conviene saber qué midió el estudio original.
- **Agrandar todos los botones.** Fitts aplica a lo frecuente; agrandar también la acción destructiva aumenta los errores.
- **Comunicar estados solo con color.** Siempre se suma ícono, texto o forma, y se verifica el contraste cuando el color se usa como texto.
- **Espaciados arbitrarios y texto a todo el ancho.** Valores sueltos rompen la proximidad; líneas de más de 75 caracteres cansan.
- **Modo oscuro como inversión.** Negro puro, acentos saturados y contraste sin verificar por tema producen una interfaz que encandila y no pasa las pautas.

## Para discutir en equipo

- ¿Qué acciones frecuentes de la app de transportistas están hoy fuera de la zona del pulgar?
- ¿Qué parte de la complejidad de reprogramar absorbe hoy el usuario y cuánta podríamos mover al backend o al agente?
- ¿Cómo debería verse una respuesta larga del asistente, y qué parte de esa decisión va en el prompt y cuál en el componente?
- ¿Dónde usamos el color como único canal de información, y cómo lo detectaríamos automáticamente?
- ¿Cuál es el "pico" negativo más frecuente en las conversaciones con el asistente, y cómo cambiaría su cierre?
