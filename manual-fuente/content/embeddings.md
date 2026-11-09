---
slug: embeddings
titulo: Embeddings y bases vectoriales
resumen: Cómo se representa el significado de un texto como un vector numérico y cómo se almacenan y buscan millones de esos vectores de forma eficiente.
lectura: 12
---

## La idea central

Una computadora no entiende que "el paquete llegó roto" y "la mercadería vino dañada" dicen casi lo mismo: como cadenas de caracteres, no comparten casi ninguna palabra. Un **embedding** resuelve esto convirtiendo cada texto en una lista de números (un vector) de forma que los textos de significado parecido quedan representados por vectores cercanos. Una vez que el significado es geometría, "buscar textos parecidos" se convierte en "buscar puntos cercanos", algo que una computadora hace muy bien.

Pensemos en un mapa. Cada texto es un punto, y el modelo de embeddings decide dónde ubicarlo: las quejas por demoras quedan agrupadas en un barrio, los problemas de acceso a la cuenta en otro, las consultas sobre integraciones de API en un tercero. Una **base vectorial** es la infraestructura que guarda millones de esos puntos y responde rápido a la pregunta "¿cuáles son los 10 puntos más cercanos a este?". Es la pieza que hace posible la búsqueda semántica de [RAG](#t/rag), pero sirve para mucho más.

## Conceptos

### Qué es un embedding

Un embedding es un vector de números reales, típicamente de cientos a pocos miles de dimensiones (por ejemplo, 384, 768, 1.536 o 3.072, según el modelo). Lo produce un **modelo de embeddings**: una red neuronal entrenada para que textos con significado parecido den vectores parecidos y textos sin relación den vectores alejados.

Cada dimensión individual no tiene un significado legible ("la dimensión 47 es el enojo"). El significado está en la posición relativa del vector completo respecto de los demás. Lo único que importa es la distancia entre vectores.

**Ejemplo intuitivo en 2 dimensiones:** imaginemos un modelo de juguete que solo usa dos ejes, uno que mide "cuánto habla de tiempos" y otro que mide "cuánto habla del estado del paquete".

| Texto | Eje 1 (tiempos) | Eje 2 (estado del paquete) |
|---|---|---|
| "Mi pedido está demorado" | 0,90 | 0,10 |
| "Hace tres días que espero el envío" | 0,85 | 0,15 |
| "El paquete llegó roto" | 0,10 | 0,90 |
| "La mercadería vino dañada" | 0,15 | 0,88 |
| "¿Cómo cambio mi contraseña?" | 0,05 | 0,05 |

Las dos quejas por demora quedan juntas, las dos de daño también, y la pregunta sobre contraseña queda lejos de ambas. Un modelo real hace lo mismo en cientos de dimensiones, lo que le permite capturar muchísimos matices a la vez.

**Por qué importa:** los embeddings convierten "parecido en significado" en una operación matemática barata, que se puede ejecutar sobre millones de textos.

### Similitud coseno y producto punto

Para medir cuán cerca están dos vectores se usan principalmente dos medidas:

- **Producto punto:** se multiplican los vectores componente a componente y se suman los resultados. Da un número más alto cuanto más alineados están y cuanto más largos son.
- **Similitud coseno:** mide el ángulo entre los vectores, ignorando su largo. Vale 1 si apuntan en la misma dirección, 0 si son perpendiculares (sin relación) y -1 si son opuestos. Es el producto punto dividido por el producto de los largos.

**Ejemplo con la tabla anterior:** "Mi pedido está demorado" = (0,90; 0,10) y "Hace tres días que espero" = (0,85; 0,15).

- Producto punto: 0,90 × 0,85 + 0,10 × 0,15 = 0,765 + 0,015 = 0,78.
- Largos: raíz(0,81 + 0,01) ≈ 0,906 y raíz(0,7225 + 0,0225) ≈ 0,863.
- Coseno: 0,78 / (0,906 × 0,863) ≈ 0,78 / 0,782 ≈ 0,998. Casi idénticos.

Contra "El paquete llegó roto" = (0,10; 0,90): producto punto = 0,09 + 0,09 = 0,18; coseno ≈ 0,18 / (0,906 × 0,906) ≈ 0,22. Mucho menos parecidos.

Muchos modelos devuelven vectores **normalizados** (de largo 1); en ese caso coseno y producto punto dan exactamente lo mismo y se usa el producto punto porque es más barato de calcular. Conviene usar la métrica que recomienda el proveedor del modelo.

### El mismo modelo para documentos y consultas

Cada modelo de embeddings define su propio "mapa". Los vectores de dos modelos distintos no son comparables entre sí, ni siquiera si tienen la misma cantidad de dimensiones: es como comparar coordenadas de dos mapas con distinto origen y orientación.

Consecuencias prácticas:

1. Las consultas se vectorizan con exactamente el mismo modelo (y la misma versión) que los documentos.
2. **Cambiar de modelo obliga a reindexar todo:** recalcular los embeddings de todos los documentos.
3. Conviene guardar en los metadatos de cada vector qué modelo y versión lo generó.

Algunos modelos usan prefijos o modos distintos para documentos y consultas (por ejemplo, una instrucción del tipo "consulta:" antes del texto). Eso es parte del mismo modelo y hay que respetarlo de forma consistente.

**Ejemplo:** si el índice se generó con el modelo A y alguien actualiza la librería y las consultas empiezan a vectorizarse con el modelo B, la búsqueda sigue devolviendo resultados (siempre hay "vecinos más cercanos"), pero son prácticamente aleatorios. No hay error visible: solo una caída silenciosa de calidad.

### Búsqueda exacta y búsqueda aproximada (ANN)

La forma más simple de buscar es la **búsqueda exacta** (fuerza bruta): comparar la consulta contra todos los vectores y quedarse con los más cercanos. Es perfecta en calidad, pero su costo crece linealmente.

**Ejemplo (orden de magnitud):** 10 millones de vectores de 1.536 dimensiones implican unas 15.000 millones de multiplicaciones por consulta. Con 100 consultas por segundo, eso no escala.

La **búsqueda aproximada de vecinos más cercanos** (ANN, Approximate Nearest Neighbors) usa estructuras de índice para revisar solo una pequeña parte de los vectores. A cambio, puede no encontrar alguno de los verdaderos más cercanos. Esa calidad se mide con **recall**: si los 10 verdaderos vecinos más cercanos son conocidos y el índice ANN devuelve 9 de ellos, el recall@10 es 90 %.

Para colecciones chicas (decenas de miles de vectores), la búsqueda exacta suele ser suficiente y más simple. Por encima de cientos de miles o millones, ANN es lo habitual.

### HNSW, explicado intuitivamente

**HNSW** (Hierarchical Navigable Small World) es el algoritmo ANN más usado. La intuición se parece a cómo se viaja entre ciudades:

1. Se construye un grafo donde cada vector está conectado con algunos de sus vecinos cercanos.
2. Se arman varias capas: la capa superior tiene pocos nodos con conexiones largas (como autopistas entre ciudades), las intermedias tienen más nodos (rutas provinciales) y la inferior tiene todos los nodos con conexiones cortas (calles del barrio).
3. Para buscar, se entra por la capa superior y se avanza siempre hacia el nodo más cercano a la consulta. Cuando no se puede mejorar, se baja de capa y se repite con más detalle, hasta llegar a la capa inferior y explorar el vecindario final.

Así se llega a la zona correcta revisando unos pocos miles de vectores en lugar de millones.

HNSW tiene parámetros que regulan el compromiso: cuántas conexiones guarda cada nodo (más conexiones = mejor recall y más memoria) y cuántos candidatos explora en la búsqueda (más candidatos = mejor recall y más latencia). Su principal costo es que el grafo vive en memoria y ocupa bastante.

### El triple compromiso: recall, latencia y memoria

Todo índice vectorial equilibra tres cosas, y mejorar una suele empeorar otra:

- **Recall:** cuántos de los verdaderos vecinos encuentra.
- **Latencia:** cuánto tarda cada consulta.
- **Memoria (y costo):** cuánta RAM necesita el índice.

**Ejemplo (valores hipotéticos):** sobre 2 millones de vectores, una configuración de HNSW da 95 % de recall en 8 ms; subir el parámetro de exploración lleva a 99 % en 25 ms; reducir la memoria con **cuantización** (guardar cada número con menos precisión, por ejemplo 1 byte en lugar de 4) baja la RAM a un cuarto, pero el recall cae a 92 % si no se compensa.

**Por qué importa:** no existe "la mejor configuración". Para el asistente de soporte, 95 % de recall con 10 ms está bien porque después hay reranking; para detección de duplicados quizá se necesite más recall y se tolere más latencia.

### Metadatos y filtros

Además del vector, cada registro guarda metadatos: identificador del documento, fecha, idioma, zona, comercio, nivel de acceso, modelo de embeddings. Las búsquedas casi siempre combinan similitud con filtros: "los 10 fragmentos más parecidos, pero solo de documentos vigentes y del comercio 123".

Hay un detalle técnico que importa. Si el filtro se aplica **después** de la búsqueda ANN (post-filtrado) y el filtro es muy restrictivo, puede pasar que de los 10 vecinos encontrados ninguno cumpla el filtro y la búsqueda devuelva cero resultados. Las bases vectoriales modernas ofrecen filtrado integrado en la búsqueda o pre-filtrado; vale la pena verificar cómo lo hace la base elegida y probarlo con los filtros reales.

### Dimensiones y costo

Más dimensiones permiten capturar más matices, pero cuestan más en almacenamiento, memoria y tiempo de cálculo.

**Ejemplo de cálculo:** 1 millón de vectores de 1.536 dimensiones en float32 (4 bytes por número) ocupan 1.000.000 × 1.536 × 4 bytes ≈ 6,1 GB, solo los vectores. El índice HNSW agrega su grafo encima. Con 384 dimensiones serían unos 1,5 GB.

Algunos modelos permiten truncar el vector a menos dimensiones con una pérdida de calidad moderada. Antes de elegir el modelo más grande, conviene medir si el más chico alcanza para la tarea con un conjunto de evaluación propio.

### Usos más allá de RAG

Los embeddings sirven en cualquier problema donde "parecido en significado" sea útil:

- **Detección de duplicados:** dos tickets del mismo comercio con similitud mayor a cierto umbral en la misma hora probablemente son el mismo problema reportado dos veces.
- **Agrupar (clustering):** agrupar miles de tickets por cercanía para descubrir temas sin definir categorías de antemano.
- **Features para modelos de ML:** convertir texto libre (las notas de entrega de los comercios) en vectores que alimentan un modelo clásico, por ejemplo como entrada adicional al modelo de ETA, posiblemente reducidos a pocas dimensiones.
- **Recomendación y búsqueda semántica** en catálogos o bases de conocimiento.

### pgvector, Pinecone y OpenSearch

| Opción | Tipo | Cuándo conviene | Ojo con |
|---|---|---|---|
| pgvector | Extensión de PostgreSQL (disponible en Aurora PostgreSQL) | Ya se usa PostgreSQL; hasta unos pocos millones de vectores; se quieren filtros SQL, joins y transacciones con los datos de negocio | El índice HNSW consume memoria de la instancia y compite con la carga transaccional; afinar parámetros y filtros requiere cuidado; a escalas muy grandes exige más trabajo operativo |
| Pinecone | Base vectorial gestionada (servicio SaaS) | Se quiere no operar nada; escala grande; equipo chico | Los datos salen de la infraestructura propia (relevante con PII y clientes on-prem); dependencia de un proveedor; costo que crece con el volumen; no hay joins con datos de negocio |
| OpenSearch | Motor de búsqueda con soporte vectorial (gestionado en AWS o autoalojado) | Se necesita búsqueda híbrida (BM25 más vectores) en un mismo motor; ya existe un clúster; volúmenes grandes | Operar un clúster de OpenSearch no es trivial (shards, memoria, actualizaciones); otra pieza de infraestructura que mantener |

No hay una respuesta universal: la decisión depende de la escala, de lo que ya se opera, de los requisitos de datos y de si se necesita búsqueda híbrida.

## Casos prácticos

### Elegir la base para 200.000 fragmentos

**Situación:** el asistente de soporte de Rumbo va a indexar unos 200.000 fragmentos de manuales, políticas y tickets resueltos. El equipo ya opera Aurora PostgreSQL y algunos clientes grandes exigen instalación on-prem.

**Qué se hace:** se elige pgvector sobre Aurora PostgreSQL. El cálculo de tamaño lo respalda: 200.000 vectores de 1.536 dimensiones en float32 ocupan unos 1,2 GB, más el índice HNSW; entra cómodo en memoria de una instancia razonable. Ventajas: no se agrega infraestructura nueva, los permisos y la vigencia se filtran con SQL junto a las tablas existentes, se reutilizan backups y monitoreo, y en on-prem basta con un PostgreSQL con la extensión, sin depender de un servicio externo. Para la búsqueda híbrida se usa la búsqueda de texto completo de PostgreSQL combinada con la vectorial. Como precaución, se usa una réplica de lectura o una instancia separada para que las búsquedas no compitan con la carga transaccional, y se define un umbral (por ejemplo, decenas de millones de vectores o latencias fuera de presupuesto) a partir del cual se reevaluaría OpenSearch.

### Migrar a un modelo de embeddings nuevo

**Situación:** aparece un modelo de embeddings nuevo que, según pruebas preliminares, mejora la recuperación en castellano. El índice actual tiene 200.000 fragmentos con el modelo viejo.

**Qué se hace:** como los vectores de ambos modelos no son comparables, no se puede migrar "de a poco" dentro del mismo índice. El proceso es:

1. Crear un **índice paralelo** (otra tabla o colección) y calcular los embeddings de todos los fragmentos con el modelo nuevo, sin tocar el índice en uso.
2. **Comparar recall** de ambos índices sobre el conjunto de evaluación de recuperación: por ejemplo, recall@5 de 84 % con el viejo contra 90 % con el nuevo, mirando también tipos de pregunta específicos (códigos, preguntas largas).
3. **Cambio gradual:** enviar un porcentaje de las consultas (5 %, luego 25 %, luego 100 %) al índice nuevo, vectorizando la consulta con el modelo nuevo, y monitorear métricas de calidad (respuestas con "no lo sé", calificaciones de soporte).
4. Mientras dura la transición, el reindexado incremental escribe en ambos índices.
5. Mantener el índice viejo unos días como rollback y luego eliminarlo.

El costo de recalcular 200.000 embeddings suele ser bajo comparado con el riesgo de una migración sin medir.

### Agrupar tickets para detectar un problema emergente

**Situación:** un lunes, el volumen de tickets de la zona sur sube un 40 %, pero el clasificador los reparte entre `demora`, `no_entregado` y `otro`, y nadie ve un patrón claro.

**Qué se hace:** se calculan los embeddings de los tickets de las últimas 48 horas de la zona y se agrupan con un algoritmo de clustering. Aparece un grupo nuevo de unos 300 tickets muy cercanos entre sí que no existía la semana anterior. Al leer una muestra, todos mencionan que el transportista "no pudo ingresar al barrio cerrado" de un conjunto de urbanizaciones donde cambió el control de acceso. El clasificador los dispersaba porque cada comercio lo describía distinto, pero en el espacio de embeddings estaban juntos. Se arma un proceso diario que compara los grupos del día contra los históricos y alerta al agente de operaciones cuando surge un grupo nuevo de tamaño relevante en una zona.

## Errores comunes

- **Mezclar vectores de modelos distintos.** Consultas y documentos deben usar el mismo modelo y versión; guardar el modelo en los metadatos y validarlo al consultar.
- **Usar búsqueda aproximada sin medir el recall.** Comparar periódicamente los resultados ANN contra búsqueda exacta sobre una muestra para saber cuánto se pierde.
- **No probar los filtros con datos reales.** Un filtro restrictivo aplicado después de la búsqueda ANN puede devolver resultados vacíos o incompletos.
- **Elegir el modelo con más dimensiones por defecto.** Cuesta más memoria y latencia; medir si uno más chico alcanza para la tarea.
- **Agregar una base vectorial gestionada sin evaluar lo que ya se tiene.** Para cientos de miles de vectores, pgvector en la base existente suele ser suficiente y más simple de operar.
- **Usar umbrales de similitud fijos sin calibrar.** Un "0,8 es parecido" depende del modelo y del dominio; calibrar con ejemplos etiquetados.

## Para discutir en equipo

- ¿A partir de qué volumen o requisito dejaría de alcanzarnos pgvector en Aurora, y cómo lo detectaríamos antes de que sea un problema?
- ¿Qué implicaciones tiene enviar textos con PII de destinatarios a un servicio externo de embeddings, y qué alternativas tenemos?
- ¿Cómo sabríamos que un modelo de embeddings nuevo es mejor para nuestros datos y no solo en las pruebas públicas?
- ¿Qué otros problemas de Rumbo (además del soporte) podrían beneficiarse de agrupar o comparar textos por significado?
- ¿Qué métricas deberíamos monitorear en producción para notar una caída silenciosa de calidad en la búsqueda vectorial?
