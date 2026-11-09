---
slug: privacidad-datos
titulo: Privacidad y datos personales
resumen: Qué datos personales maneja Rumbo, qué principios guían su uso y qué técnicas los protegen en logs, analítica, RAG, memoria de agentes y prompts.
lectura: 14
---

## La idea central

Un dato personal es cualquier información que permite identificar a una persona, directa o indirectamente. En Rumbo no es un tema lateral: cada pedido lleva el nombre, el teléfono y la dirección de alguien, cada entrega puede tener una foto de su puerta y cada transportista emite su ubicación cada pocos segundos. Son necesarios para entregar, pero se copian a logs, analítica, índices de búsqueda, prompts y datasets de evaluación, y cada copia es un lugar más donde pueden filtrarse.

La analogía útil es el cartero: necesita la dirección del sobre, pero no tiene por qué fotocopiarla ni guardarla en un cajón. En sistemas es lo mismo: usar el dato para lo que se recolectó, con la menor exposición y durante el menor tiempo posible, y poder demostrar dónde está. Este tema no es asesoramiento legal: las obligaciones concretas dependen del país y las define el área legal o de privacidad; aquí se cubren los principios y las técnicas que el equipo aplica en el diseño.

## Conceptos

### Qué es un dato personal en Rumbo

Hay datos que identifican por sí solos y datos que identifican combinados:

- **Identificadores directos:** nombre del destinatario, teléfono, email, dirección.
- **Identificadores indirectos:** combinaciones que apuntan a una persona aunque no tengan su nombre, como "entrega diaria a las 19:10 en el edificio de tal esquina, piso 4".
- **Contenido:** fotos de entrega (pueden mostrar la cara de quien recibe o el interior de un domicilio), mensajes al soporte, notas de entrega ("dejar con la vecina del 3B").
- **Datos de los transportistas:** ubicación en tiempo real, recorridos, horarios. Son personas, y su ubicación revela dónde viven y qué hacen fuera del turno si se guarda sin límite.

La sigla **PII** (personally identifiable information) se usa en la industria para todo este conjunto.

**Ejemplo:** un ID de pedido `ped_8f2a91` solo no identifica a nadie. Unido en la misma tabla a la dirección y la hora de entrega, sí.

**Por qué importa:** si el equipo piensa solo en "nombre y teléfono", se le escapan las fotos, las notas libres y las trazas de ubicación, que suelen ser las más reveladoras.

### Principios de tratamiento

Las leyes de protección de datos varían por país: hay regímenes del estilo del GDPR europeo y leyes locales con requisitos propios (bases legales, plazos para responder solicitudes, notificación de incidentes, transferencias internacionales). Casi todas comparten estos principios, que sirven como guía de diseño:

1. **Minimización:** recolectar y guardar solo lo necesario para el fin. Si para calcular la ETA alcanza con la zona, el modelo no recibe la dirección exacta.
2. **Limitación de la finalidad:** usar el dato solo para el fin con que se obtuvo. El teléfono se pidió para coordinar la entrega, no para campañas ni para entrenar un modelo sin evaluarlo antes.
3. **Retención limitada:** cada dato tiene un plazo y se borra o se anonimiza al cumplirse.
4. **Control de acceso:** solo quien lo necesita para su tarea lo ve, y el acceso queda registrado.
5. **Transparencia:** la persona puede saber qué se guarda, para qué y cómo pedir acceso o borrado.

**Ejemplo:** un equipo propone usar las notas de entrega para entrenar un modelo que sugiera franjas horarias. Antes de empezar se pregunta: ¿el fin es compatible con aquel para el que se recolectaron?, ¿alcanza con las notas sin nombres ni direcciones?, ¿cuánto tiempo se guarda el dataset?

**Por qué importa:** estos principios convierten "cuidar la privacidad" en preguntas concretas para una revisión de diseño.

### Clasificación de datos y retención

Clasificar es asignar a cada tipo de dato un nivel de sensibilidad, del que dependen los controles: quién accede, si se cifra por campo, si puede ir a logs o a un proveedor externo y cuánto se guarda. Plazos hipotéticos, a definir con legal:

| Dato | Sensibilidad | Uso principal | Retención en sistemas operativos |
|---|---|---|---|
| Nombre, teléfono y dirección del destinatario | Alta | Entregar y avisar | 90 días después de la entrega |
| Foto de entrega | Alta | Prueba de entrega y reclamos | 30 días, o hasta cerrar el reclamo |
| Notas de entrega (texto libre) | Alta | Indicaciones al transportista | 90 días |
| Ubicación del transportista | Alta | Seguimiento en vivo y ETA | Detalle 30 días; luego solo agregados por zona |
| Conversaciones con el asistente de soporte | Alta | Atender el caso | 180 días |
| Contacto del comercio | Media | Relación comercial | Mientras dure el contrato |
| Zona, franja horaria, duración de la entrega | Baja | Modelos y métricas | Sin límite, si no se cruza con identificadores |

**Ejemplo:** la foto de entrega se guarda en S3 con una regla de ciclo de vida que la borra a los 30 días, salvo que el pedido tenga un reclamo abierto, en cuyo caso se mueve a un prefijo con retención hasta el cierre.

**Por qué importa:** sin clasificación, cada equipo decide por su cuenta y el dato más sensible termina con los controles del menos sensible.

### Enmascarado, seudonimización y anonimización

Son técnicas distintas, con garantías distintas:

- **Enmascarado:** ocultar parte del valor al mostrarlo (`+54 9 11 ****-**34`). Sirve para pantallas y logs; el dato original sigue existiendo en la fuente.
- **Seudonimización:** reemplazar el identificador por otro que no lo revela, pero que permite volver a vincularlo con información adicional (una clave o una tabla). El dato seudonimizado **sigue siendo personal**: quien tenga la clave lo revierte.
- **Anonimización:** transformar los datos de forma que ya no se pueda identificar a nadie, ni siquiera combinándolos con otras fuentes. Si se logra de verdad, el dato deja de ser personal. Es mucho más difícil de lo que parece.

El problema de la anonimización es la **reidentificación**. Supongamos un dataset de entregas "anónimo" donde se quitó el nombre y el teléfono se reemplazó por un hash SHA-256 sin clave:

1. Los teléfonos de un país tienen un espacio pequeño: unos 100 millones de combinaciones posibles para un formato dado. Calcular el hash de todas lleva minutos en una laptop. El hash se revierte.
2. Aun sin el teléfono, cada fila tiene coordenadas de entrega y hora. Una persona que recibe pedidos casi todos los días a las 19:10 en el mismo edificio queda identificada con tres o cuatro puntos: muy pocas personas comparten ese patrón.
3. Las trazas de los transportistas empiezan y terminan cada día cerca de su casa.

Por eso, para correlacionar sin revelar se usa un **HMAC con una clave secreta** guardada en un gestor de secretos (seudonimización real), y para publicar o compartir datos se recurre a **agregación**: contar entregas por zona y franja, con un mínimo de casos por celda (por ejemplo, no mostrar celdas con menos de 10 entregas).

**Ejemplo:** analítica necesita saber cuántas veces reintenta Rumbo una entrega al mismo destinatario. Recibe `dest_id = HMAC(clave, telefono_normalizado)`: puede contar reintentos por destinatario sin ver el teléfono, y nadie fuera del servicio de pedidos tiene la clave.

**Por qué importa:** llamar "anónimo" a un dataset seudonimizado lleva a compartirlo con controles de dato no personal, y es una de las formas más comunes de filtración.

### Tokenización de identificadores

La **tokenización** reemplaza el dato real por un valor sustituto aleatorio (un token, sin relación con los tokens de un LLM) y guarda la correspondencia en un servicio aislado, la **bóveda**. Los demás sistemas trabajan solo con el token; cuando alguien necesita el valor real (la app del transportista, para llamar al destinatario), lo pide a la bóveda, que verifica permisos y registra el acceso.

A diferencia del HMAC, el token no se deriva del valor: no se puede revertir sin la bóveda. A diferencia del cifrado de campo (ver [Secretos y cifrado](#t/secretos)), el sistema que guarda el token ni siquiera tiene el texto cifrado.

**Ejemplo:** el servicio de pedidos guarda `telefono_token = tok_7Qx2...`. Kafka, el data lake y los logs solo ven el token. De 14 servicios que antes leían el teléfono, solo 2 tienen permiso de canjearlo.

**Por qué importa:** reduce de forma drástica cuántos sistemas contienen el dato real, y por lo tanto cuántos hay que proteger, auditar y limpiar ante una solicitud de borrado.

### Datos personales en logs, trazas y analítica

Los logs y las trazas tienen más copias, más lectores y más retención que la base de datos principal (ver [Logging estructurado](#t/logging)). La regla es **redactar en origen**: el dato no sale del proceso que lo maneja. Las redacciones posteriores (en el colector de logs o en la plataforma de analítica) son una red de seguridad, porque para entonces el dato ya viajó y pudo quedar en buffers o reintentos.

Lugares donde la PII se cuela sin que nadie lo decida:

- Atributos de spans con el cuerpo completo de un request.
- Mensajes de error que incluyen el valor que falló al validar ("teléfono inválido: +54 9 ...").
- Prompts y respuestas de LLM guardados íntegros para depuración.

**Ejemplo:** el asistente de soporte guarda cada llamada al LLM en el registro de invocaciones. Un muestreo encuentra direcciones en el 38 % de los prompts. Se agrega redacción antes de escribir el registro, y el texto completo queda solo en un almacén separado con 15 días de retención y acceso restringido.

**Por qué importa:** la mayoría de las filtraciones de datos personales no vienen de la base principal, sino de sus copias secundarias.

### Solicitudes de borrado y dónde se esconden las copias

Cuando una persona pide que se borren sus datos, borrar la fila en la tabla de destinatarios es la parte fácil. Las copias suelen estar en:

- **Réplicas y data lake:** tablas de analítica, exportaciones a S3, snapshots de features.
- **Logs y trazas:** si se redactó en origen, no deberían estar.
- **Backups:** normalmente no se editan; se acepta que el dato expire con el ciclo de retención del backup y que, si se restaura, se vuelva a aplicar la lista de borrados pendientes.
- **Cachés:** respuestas cacheadas, cachés de prompts o de resultados de herramientas.
- **Embeddings e índices vectoriales:** fragmentos de conversaciones o tickets indexados para RAG.
- **Memoria de agentes:** notas o resúmenes guardados por usuario.
- **Datasets de evaluación y de fine-tuning:** y los modelos ya entrenados con ellos, de los que no se puede "sacar" un ejemplo.

**Ejemplo:** el proceso de borrado de Rumbo recibe un `dest_id` y publica un evento `borrado_solicitado`. Cada sistema dueño de una copia lo consume y confirma: pedidos, data lake, índice del RAG, memoria del asistente, datasets. El caso se cierra cuando todos confirmaron.

**Por qué importa:** un inventario de copias armado de antemano es la diferencia entre responder a tiempo y buscar a ciegas en cada solicitud.

### LLMs externos: qué sale y bajo qué condiciones

Cada llamada a un proveedor externo de LLM envía el prompt completo fuera de nuestra infraestructura. Antes de mandar datos personales hay que conocer las condiciones: si existe un acuerdo de tratamiento de datos, cuánto tiempo retiene el proveedor los prompts, si los usa para entrenar y si se puede desactivar, y en qué región se procesan. Estas condiciones cambian y dependen del contrato: verificar las condiciones vigentes del proveedor, junto con legal, antes de cada uso nuevo.

La práctica de diseño es **redactar la PII antes del prompt** siempre que la tarea no la necesite:

1. Un detector (reglas para teléfonos y emails más un modelo de reconocimiento de entidades para nombres y direcciones) reemplaza cada valor por un marcador: `[DESTINATARIO_1]`, `[TELEFONO_1]`.
2. El LLM trabaja con los marcadores.
3. Si la respuesta debe mostrar el dato al usuario autorizado, el sistema reemplaza los marcadores después, en nuestra infraestructura.

**Ejemplo:** para resumir un ticket, el asistente no necesita el teléfono ni la dirección exacta; basta "destinatario en zona norte, segundo intento fallido". El prompt pasa de contener 4 datos personales a ninguno, y el resumen es igual de útil.

**Por qué importa:** lo que nunca se envía no depende de las políticas de retención de nadie.

### PII en memoria, índices vectoriales y salidas del agente

Los sistemas con agentes crean copias nuevas de datos personales que no existían en una aplicación tradicional:

- **Memoria de conversación:** si el asistente recuerda "el usuario vive en tal dirección", esa memoria es un dato personal con su propia retención y su propio borrado (ver [Contexto y memoria de agentes](#t/contexto-memoria)).
- **Índices vectoriales:** un embedding de un fragmento con datos personales también es dato personal: con acceso al índice se recuperan los fragmentos originales. Cada fragmento debe guardar en sus metadatos a quién pertenece (`dest_id`, `comercio_id`), para filtrar en la búsqueda y para borrar. Borrar de un índice RAG es borrar por metadato y verificar que la búsqueda ya no lo devuelva.
- **Salidas:** un guardrail de salida detecta PII en la respuesta del agente y la bloquea o enmascara si no corresponde al usuario que pregunta; por ejemplo, el teléfono de otro destinatario que apareció en un documento recuperado.
- **Datasets de evaluación:** las conversaciones reales son la mejor fuente para armar casos de prueba, pero se redactan antes de entrar al dataset, se registra su origen y se respeta su retención.

**Ejemplo:** se pide borrar los datos de un destinatario. El índice del RAG de soporte tiene 23 fragmentos con su `dest_id` en metadatos: se borran, se ejecutan 5 consultas con su nombre y su dirección y ninguna devuelve resultados.

**Por qué importa:** si los metadatos de pertenencia no se guardan al indexar, más adelante no hay forma confiable de encontrar qué borrar.

## Casos prácticos

### Analítica pide la tabla de entregas "anonimizada"

**Situación:** el equipo de analítica pide una copia de las entregas del último año para estudiar reintentos, con el teléfono hasheado y sin nombre. Incluye coordenadas exactas y hora al minuto.
**Qué se hace:** se explica que el hash sin clave se revierte y que las coordenadas con hora reidentifican. Se entrega `dest_id` con HMAC, coordenadas redondeadas a una celda de unos 500 metros, hora redondeada a la franja de 30 minutos y retención de 12 meses en el data lake. Para el tablero compartido con comercios, solo agregados por zona con un mínimo de 10 entregas por celda.

### Fotos de entrega enviadas a un modelo multimodal

**Situación:** se propone que un modelo multimodal de un proveedor externo revise las fotos de entrega para detectar paquetes dejados en lugares inseguros. Las fotos muestran puertas, a veces caras y números de departamento.
**Qué se hace:** se revisan con legal las condiciones del proveedor (retención, uso para entrenamiento, región). Antes de enviar, un paso en nuestra infraestructura difumina caras y recorta la imagen al área del paquete. Las respuestas guardan solo la clasificación, no la imagen, y se mide en una muestra que el difuminado no empeora la detección.

### Solicitud de borrado con el asistente de soporte en el medio

**Situación:** un destinatario pide borrar sus datos. Tuvo tres conversaciones con el asistente, que guardó un resumen en su memoria por usuario, y dos de esas conversaciones se usaron como casos en el golden set de evaluación.
**Qué se hace:** el evento de borrado llega al servicio de memoria, que elimina el resumen; al índice del RAG, que borra por `dest_id`; y al repositorio del dataset de evaluación, donde los dos casos se reemplazan por variantes sintéticas que conservan el comportamiento a evaluar sin los datos reales.

### Un agente de operaciones que lee demasiado

**Situación:** el agente de operaciones investiga "cayó la tasa de entregas a tiempo en zona norte" y, para hacerlo, consulta la tabla de pedidos completa, con nombres y direcciones, que terminan en el prompt y en el informe.
**Qué se hace:** se aplica minimización a la herramienta: `consultar_pedidos` devuelve una vista con zona, franja, estado, transportista seudonimizado y tiempos, sin datos del destinatario. El análisis no pierde nada, y el informe y los prompts dejan de contener PII.

## Errores comunes

- **Llamar anónimo a lo que es seudónimo.** Un hash sin clave de un teléfono se revierte en minutos. Usar HMAC con clave y tratar el resultado como dato personal.
- **Redactar solo en el colector de logs.** Para entonces el dato ya viajó. Redactar en origen y dejar la redacción posterior como red de seguridad.
- **Indexar en RAG sin metadatos de pertenencia.** Después no se puede borrar ni filtrar por usuario. Guardar `dest_id` o `comercio_id` en cada fragmento desde el primer día.
- **Mandar el ticket completo al LLM "porque es más fácil".** Redactar antes del prompt lo que la tarea no necesita y conocer las condiciones vigentes del proveedor.
- **Retención "por si acaso".** Cada copia guardada sin plazo es una copia más que proteger y borrar. Definir retención por tipo de dato y automatizarla.
- **Armar datasets de evaluación con conversaciones reales sin redactar.** Se copian a repositorios y laptops; redactar al ingresarlas y registrar su origen.

## Para discutir en equipo

- ¿Cuántas copias del teléfono de un destinatario existen hoy en nuestros sistemas, y cuáles no sabríamos borrar?
- ¿Qué tareas del asistente de soporte necesitan realmente datos personales en el prompt y cuáles podrían trabajar con marcadores?
- ¿Qué plazos de retención proponemos para memoria del asistente, registro de invocaciones e índices vectoriales?
- ¿Cómo verificamos, de forma automática, que una solicitud de borrado llegó a todas las copias, incluidos los datasets de evaluación?
- ¿Qué condiciones mínimas exigimos a un proveedor de LLM antes de enviarle datos de destinatarios o de transportistas?
