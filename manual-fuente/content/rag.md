---
slug: rag
titulo: RAG (Retrieval-Augmented Generation)
resumen: Técnica que busca los fragmentos relevantes de documentos propios y se los entrega al LLM para que responda con información actual, específica y citable.
lectura: 14
---

## La idea central

Un LLM sabe mucho en general, pero no conoce los manuales internos de Rumbo, ni la política de reclamos actualizada la semana pasada, ni los contratos de cada comercio. Y aunque los conociera, no podríamos cargarlos todos en cada llamada: no entran en la ventana de contexto y, aunque entraran, el costo y la latencia serían enormes. **RAG** (Retrieval-Augmented Generation, generación aumentada por recuperación) resuelve esto en dos pasos: primero **busca** los pocos fragmentos de documentos que son relevantes para la pregunta, y luego **genera** la respuesta dándole al modelo solo esos fragmentos como contexto.

La analogía es un examen a libro abierto. El estudiante (el LLM) sabe razonar y redactar, pero no memorizó el reglamento. Un buen bibliotecario (el sistema de recuperación) le acerca las tres páginas que importan para cada pregunta. Si el bibliotecario trae las páginas equivocadas, la respuesta será mala aunque el estudiante sea brillante. Por eso la mayor parte del trabajo de un sistema RAG no está en el LLM, sino en la búsqueda.

## Conceptos

### El problema que resuelve

RAG ataca cuatro limitaciones de un LLM solo:

1. **Conocimiento privado:** el modelo no vio los documentos internos durante su entrenamiento.
2. **Conocimiento desactualizado:** el modelo tiene una fecha de corte; las políticas cambian todas las semanas.
3. **Alucinaciones:** sin datos concretos, el modelo rellena con texto plausible. Con los fragmentos correctos en el contexto, puede responder anclado a ellos.
4. **Trazabilidad:** con RAG cada respuesta puede citar de qué documento sale, lo que permite verificarla.

**Ejemplo:** un comercio pregunta al asistente "¿hasta cuándo puedo reclamar un paquete dañado?". Sin RAG, el modelo inventa un plazo razonable. Con RAG, el sistema encuentra el fragmento de la Política de reclamos que dice "5 días hábiles desde la entrega" y el modelo responde con ese dato y la cita.

### El flujo completo

RAG tiene dos procesos separados: la **indexación**, que se ejecuta cuando los documentos cambian, y la **consulta**, que se ejecuta en cada pregunta.

```text
INDEXACIÓN (offline, cuando cambian los documentos)

  Documentos ──> Cargar y ──> Partir en ──> Calcular ──> Guardar en índice
  (manuales,     limpiar       fragmentos    embeddings   (vector + texto +
   políticas)                  (chunks)                    metadatos)

CONSULTA (online, en cada pregunta)

  Pregunta ──> Vectorizar ──> Recuperar top-k ──> Reranking ──> LLM genera
  del usuario  la pregunta    (vectorial +        (ordenar y    respuesta
                              palabras clave,     quedarse con  con citas
                              con filtros)        los mejores)
```

### Pipeline de indexación

La indexación prepara los documentos para que se puedan buscar:

1. **Cargar:** leer los documentos de sus fuentes (PDFs en S3, páginas de la wiki, tablas de Aurora) y extraer el texto limpio, descartando encabezados repetidos, menús y basura de formato.
2. **Chunking (partir en fragmentos):** dividir cada documento en trozos de tamaño manejable, típicamente de unos cientos de tokens. Se usa **solapamiento**: cada fragmento repite el final del anterior (por ejemplo, 50 tokens) para que una idea que cae justo en el corte no quede partida sin contexto.
3. **Embeddings:** convertir cada fragmento en un vector numérico que representa su significado, con un modelo de embeddings (ver [Embeddings y bases vectoriales](#t/embeddings)).
4. **Guardar con metadatos:** almacenar el vector, el texto original y metadatos útiles: documento de origen, sección, fecha de vigencia, versión, idioma, nivel de acceso, comercio al que aplica.

**Ejemplo:** un manual de 40 páginas (unos 20.000 tokens) partido en fragmentos de 400 tokens con 50 de solapamiento genera unos 57 fragmentos. Los 300 documentos de soporte de Rumbo quedan en unos 15.000 fragmentos.

**Por qué importa:** los metadatos se ven aburridos, pero son los que después permiten filtrar por permisos, descartar versiones viejas y mostrar citas útiles.

### Pipeline de consulta

En cada pregunta:

1. **Vectorizar la pregunta** con el mismo modelo de embeddings que se usó para los documentos.
2. **Recuperar los top-k:** buscar los k fragmentos más parecidos (por ejemplo, k = 20), aplicando filtros de metadatos (permisos, vigencia).
3. **Reranking:** reordenar esos candidatos con un modelo más preciso y quedarse con los mejores (por ejemplo, 5).
4. **Generar:** armar el prompt con las instrucciones, los fragmentos elegidos (cada uno con un identificador) y la pregunta, y pedirle al LLM que responda solo con esa información y cite las fuentes.

### Chunking por estructura o por tamaño fijo

Hay dos enfoques principales para partir documentos:

- **Tamaño fijo:** cortar cada N tokens, con solapamiento. Es simple y predecible, pero puede cortar una tabla por la mitad o mezclar el final de una sección con el comienzo de otra que no tiene relación.
- **Por estructura:** cortar respetando la estructura del documento: secciones, subtítulos, párrafos, filas de tabla. Cada fragmento es una unidad de sentido. Si una sección es muy larga se subdivide; si es muy corta se combina con la vecina.

Un recurso útil en ambos casos es anteponer al texto del fragmento su contexto jerárquico: "Política de reclamos > Paquetes dañados > Plazos".

**Ejemplo:** la sección "Plazos para reclamar" de la política tiene una tabla con plazos por tipo de servicio. Con tamaño fijo, el corte cae en medio de la tabla y el segundo fragmento queda con filas sin encabezado: "Express | 48 h". Con chunking por estructura, la tabla completa con su título queda en un único fragmento y la búsqueda de "plazo reclamo express" la encuentra entera.

**Por qué importa:** si el fragmento no contiene la respuesta completa y entendible por sí sola, ni la mejor búsqueda ni el mejor LLM la van a reconstruir.

### Búsqueda híbrida: vectorial más palabras clave

La **búsqueda vectorial** encuentra fragmentos de significado parecido aunque usen otras palabras: "el paquete llegó roto" encuentra "mercadería dañada". Pero es débil con términos exactos: códigos de error, números de pedido, nombres de producto o siglas. Para un modelo de embeddings, "ERR-4012" y "ERR-4021" son casi idénticos.

La **búsqueda por palabras clave** (con algoritmos como BM25, que puntúa según cuántas veces aparece un término y cuán raro es en el conjunto) hace lo contrario: es excelente con coincidencias exactas y no entiende sinónimos.

La **búsqueda híbrida** ejecuta ambas y combina los resultados. Una técnica común para combinarlos es la fusión por ranking recíproco (RRF): cada fragmento suma puntos según la posición que ocupó en cada lista, de modo que los que aparecen arriba en ambas quedan primeros.

**Ejemplo:** la pregunta "¿qué significa el error RMB-E-207 al crear un pedido por API?". La búsqueda vectorial trae fragmentos genéricos sobre errores de API. BM25 trae el fragmento exacto de la tabla de códigos donde aparece "RMB-E-207: zona de entrega no habilitada". La fusión pone ese fragmento primero.

### Reranking

La búsqueda inicial está optimizada para velocidad sobre miles o millones de fragmentos, así que compara la pregunta y cada fragmento de forma aproximada. Un **reranker** es un modelo que recibe la pregunta y un fragmento juntos y evalúa con más precisión cuán relevante es. Es más lento, por eso se aplica solo a los primeros candidatos.

**Ejemplo:** se recuperan 30 candidatos en 20 ms; el reranker los evalúa en unos 150 ms (valores hipotéticos) y se pasan al LLM los 5 mejores. Es habitual que el fragmento correcto esté en la posición 12 de la búsqueda inicial y suba a la 1 después del reranking.

**Por qué importa:** permite buscar con k amplio (para no perder el fragmento correcto) y enviar al LLM pocos fragmentos (para no meter ruido ni gastar tokens).

### Top-k y ruido

Elegir cuántos fragmentos se le dan al LLM es un compromiso:

- **k muy chico (1 o 2):** si el fragmento correcto quedó tercero, se pierde y el modelo responde sin la información.
- **k muy grande (20 o más):** sube el costo y la latencia, y los fragmentos irrelevantes confunden al modelo, que puede mezclar datos de documentos distintos.

**Ejemplo (valores hipotéticos):** con k = 3, el fragmento correcto está presente en el 78 % de las preguntas; con k = 8, en el 93 %; con k = 20, en el 96 %, pero la calidad de las respuestas baja porque el modelo se distrae. Un esquema habitual es recuperar 30, rerankear y enviar 5 a 8.

### Grounding, citas y "no lo sé"

**Grounding** (anclaje) significa que la respuesta se apoya solo en los fragmentos provistos. Se logra con tres instrucciones en el prompt:

1. Responder exclusivamente con la información de los fragmentos.
2. Citar el identificador del fragmento o documento de cada afirmación.
3. Si la información no está, decirlo explícitamente ("no encuentro esa información en la documentación disponible") en lugar de completar con conocimiento general.

Las citas se pueden validar en código: si el modelo cita un identificador que no estaba entre los fragmentos enviados, la respuesta se marca como sospechosa.

**Por qué importa:** en soporte, un "no lo sé" que deriva a una persona es mucho mejor que un plazo inventado que el comercio después reclama como compromiso.

### Permisos aplicados como filtro en la búsqueda

Si distintos usuarios pueden ver distintos documentos, los permisos se aplican **dentro de la búsqueda**, como filtro de metadatos, antes de que cualquier fragmento llegue al LLM. Nunca se le pide al modelo que "no mencione" información a la que el usuario no tiene acceso: si el fragmento está en el contexto, puede filtrarse en la respuesta, por error o por una inyección.

**Ejemplo:** cada fragmento de contrato tiene el metadato `comercio_id`. La consulta de un usuario incluye el filtro `comercio_id IN (comercios permitidos para este usuario)`, calculado a partir de su identidad en el sistema de autorización, no de lo que diga la pregunta.

### Frescura y reindexado

El índice es una copia de los documentos en un momento dado. Si la política cambia y el índice no se actualiza, el asistente sigue respondiendo con la versión vieja. Hace falta:

- **Reindexado incremental:** detectar documentos nuevos, modificados o eliminados (por fecha de modificación o hash del contenido) y actualizar solo esos fragmentos, borrando los anteriores.
- **Metadatos de vigencia:** fecha desde la que rige y estado (vigente, reemplazado).
- **Monitoreo:** alertar si el último reindexado exitoso es más viejo que lo esperado.

### Medir recuperación y generación por separado

Cuando una respuesta es mala, la causa está en uno de dos lugares: la búsqueda no trajo el fragmento correcto, o el fragmento estaba y el LLM lo usó mal. Por eso se mide cada parte por separado:

- **Recuperación:** con un conjunto de preguntas donde se sabe qué fragmento contiene la respuesta, se mide **recall@k**: en qué porcentaje de preguntas el fragmento correcto aparece entre los primeros k resultados. Ejemplo: si en 170 de 200 preguntas está en el top 5, el recall@5 es 85 %.
- **Generación:** dado que el fragmento correcto estaba, se mide **fidelidad** (la respuesta no afirma nada que no esté en los fragmentos) y **relevancia** (la respuesta contesta lo que se preguntó). Suele evaluarse con revisión humana sobre una muestra y con un LLM evaluador calibrado contra esa revisión (ver [Evaluación de LLMs](#t/evaluacion-llms)).

### RAG, fine-tuning o contexto largo

| Criterio | RAG | Fine-tuning | Contexto largo |
|---|---|---|---|
| Qué resuelve | Dar al modelo conocimiento específico y cambiante | Cambiar el comportamiento, estilo o formato del modelo | Procesar uno o pocos documentos completos en una llamada |
| Actualizar conocimiento | Reindexar el documento (minutos) | Reentrenar (días, con datos y evaluación) | Enviar el documento nuevo |
| Citas y trazabilidad | Sí, naturalmente | No | Posible, pero menos precisas |
| Permisos por usuario | Sí, con filtros en la búsqueda | No (lo aprendido es visible para todos) | Sí, si la aplicación controla qué envía |
| Costo por consulta | Bajo a medio (pocos fragmentos) | Bajo (prompt corto) | Alto (muchos tokens por llamada) |
| Cuándo conviene | Base documental grande y viva | Tarea estable, mucho volumen, formato específico | Analizar un contrato o un informe puntual |

No son excluyentes: un modelo con fine-tuning para responder en el tono de soporte puede usar RAG para los datos.

## Casos prácticos

### El asistente no encuentra códigos de error exactos

**Situación:** los comercios preguntan por códigos de error de la API ("me sale RMB-E-207") y el asistente responde con información de otros errores parecidos. La búsqueda es solo vectorial.

**Qué se hace:** se agrega búsqueda por palabras clave (BM25) en paralelo a la vectorial y se fusionan los resultados con RRF. Además, se revisa el chunking de la tabla de códigos: cada código con su descripción y solución queda como un fragmento propio, con el código también en los metadatos. Se agregan 50 preguntas con códigos al conjunto de evaluación y el recall@5 para ese tipo de pregunta pasa de un 40 % a más de un 90 % (valores ilustrativos). Lo mismo aplica a números de pedido, nombres de zonas y siglas internas.

### Diagnosticar respuestas malas

**Situación:** el equipo de soporte reporta que "el asistente responde mal" y alguien propone cambiar a un LLM más grande.

**Qué se hace:** antes de cambiar nada, se toman 100 respuestas marcadas como malas y se clasifica cada una: ¿el fragmento correcto estaba entre los enviados al LLM? Resultado (ilustrativo): en 70 casos no estaba (falla de recuperación), en 20 estaba y el modelo lo ignoró o lo mezcló (falla de generación) y en 10 la documentación directamente no tenía la respuesta. Cambiar de LLM solo atacaría el 20 %. Se prioriza mejorar la recuperación (chunking, búsqueda híbrida, reranking) y se informa al equipo de documentación sobre los temas faltantes. A partir de ahí se registran en cada consulta los fragmentos recuperados, para poder hacer este diagnóstico de forma continua.

### Política desactualizada que convive con la vieja

**Situación:** se publicó una nueva política de reintentos de entrega (de 2 a 3 intentos), pero el asistente a veces responde 2 y a veces 3. El documento nuevo se subió como archivo aparte y el viejo nunca se retiró del índice.

**Qué se hace:** se corrige el proceso, no solo el dato. Cada documento tiene un identificador estable y una versión; al indexar una versión nueva, los fragmentos de la anterior se marcan como reemplazados y se excluyen con un filtro de metadatos (`estado = vigente`). Si hace falta responder preguntas históricas ("¿qué regía en marzo?"), se filtra por fecha de vigencia en lugar de borrar. Se agrega una alerta cuando dos documentos vigentes tienen el mismo título o tema, y un control en las evals con preguntas sobre políticas recién cambiadas.

### Un analista que no debe ver contratos de ciertos comercios

**Situación:** el asistente interno indexa contratos comerciales. Algunos clientes grandes exigen que solo su ejecutivo de cuenta vea su contrato. Un analista pregunta "¿qué penalidades por demora tienen los contratos de la zona norte?".

**Qué se hace:** cada fragmento de contrato se indexa con `comercio_id` y nivel de acceso. Antes de buscar, el sistema consulta el servicio de autorización con la identidad del analista y obtiene la lista de comercios permitidos; la búsqueda aplica ese filtro, por lo que los fragmentos restringidos nunca se recuperan ni llegan al LLM. No se confía en una instrucción del tipo "no reveles contratos de X", porque una pregunta bien formulada o una inyección podrían saltearla. Se agrega un test automático: un usuario sin permisos pregunta por un comercio restringido y se verifica que ningún fragmento de ese comercio aparezca en la recuperación.

## Errores comunes

- **Culpar al LLM sin mirar la recuperación.** La mayoría de las respuestas malas vienen de no haber encontrado el fragmento correcto; hay que registrar y medir la recuperación por separado.
- **Usar solo búsqueda vectorial en dominios con códigos e identificadores.** Agregar búsqueda por palabras clave y fusionar resultados.
- **Aplicar permisos con instrucciones en el prompt.** Los permisos se aplican como filtro en la búsqueda, antes de que el contenido llegue al modelo.
- **Indexar una vez y olvidarse.** Sin reindexado incremental, metadatos de vigencia y monitoreo, conviven versiones contradictorias de los documentos.
- **Elegir el tamaño de fragmento sin mirar los documentos.** Tablas, listas y secciones cortas necesitan chunking por estructura; conviene revisar a mano una muestra de fragmentos.
- **Enviar muchos fragmentos "por las dudas".** Más contexto aumenta costo, latencia y confusión; recuperar amplio, rerankear y enviar pocos.

## Para discutir en equipo

- ¿Cuántas de las respuestas malas de nuestro asistente son fallas de recuperación y cuántas de generación? ¿Tenemos registrados los fragmentos recuperados para saberlo?
- ¿Qué tipos de preguntas de los comercios dependen de términos exactos y cómo los estamos cubriendo en la búsqueda?
- ¿Quién es dueño de que un documento reemplazado salga del índice: el equipo de documentación o el de plataforma?
- ¿Qué documentos tienen restricciones de acceso y cómo nos aseguramos de que el filtro se aplique en todas las rutas de búsqueda?
- Para clientes con instalación on-prem, ¿qué partes del pipeline de RAG tendrían que correr dentro de su infraestructura?
