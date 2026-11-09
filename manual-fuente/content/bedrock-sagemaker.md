---
slug: bedrock-sagemaker
titulo: IA gestionada en AWS: Bedrock y SageMaker
resumen: Cómo consumir modelos con Bedrock y SageMaker y qué cambia en datos, red, permisos, cuotas, costo y dependencia frente a otras opciones.
lectura: 15
---

## La idea central

Hay tres formas de poner un modelo a trabajar para Rumbo: llamar a la API de un proveedor por internet, usar una **plataforma gestionada dentro de nuestra nube** como Amazon Bedrock (modelos de varios proveedores detrás de una API de AWS, con IAM, VPC y CloudTrail), o **alojar el modelo nosotros** en SageMaker o EKS. Las tres responden "texto entra, texto sale", pero difieren en dónde viajan los datos, quién autoriza cada llamada, cómo se limita el volumen, cómo se factura y cuánto cuesta irse.

Una analogía: la API del proveedor es pedir delivery; Bedrock es un patio de comidas dentro del edificio, con varios restaurantes y una sola credencial; SageMaker o EKS es tener cocina propia, con control total pero con alguien que cocina aunque no venga nadie. Este tema no repite lo que ya está en [LLMs en producción](#t/llms-produccion) (gateway, guardrails, fallbacks) ni en el tema de serving; se concentra en qué aportan y qué esconden los servicios gestionados de AWS. Los nombres de funcionalidades, límites y precios de estos servicios cambian seguido: todo lo concreto que aparece acá hay que **verificarlo en la documentación vigente**.

## Conceptos

### Tres formas de consumir un modelo

1. **API directa del proveedor:** se llama a un endpoint público con una clave de API. Los datos salen por el NAT gateway hacia internet y se procesan donde el proveedor indique por contrato.
2. **Plataforma gestionada (Bedrock):** se llama a una API de AWS en la región elegida, con un rol de IAM. Con un **interface endpoint (PrivateLink)**, el tráfico no sale de la red privada. Cuotas, factura y auditoría quedan en nuestra cuenta de AWS.
3. **Autoalojado (SageMaker o EKS):** servimos un modelo de pesos abiertos en instancias con GPU propias. Nada sale de la cuenta, pero capacidad, actualizaciones y disponibilidad son nuestras.

**Ejemplo:** una consulta al asistente de soporte, ya enmascarada por el gateway, viaja por internet al proveedor (opción 1), por PrivateLink a Bedrock en `us-east-1` con registro en CloudTrail bajo el rol `asistente-soporte` (opción 2), o a un pod del mismo clúster sin salir de la VPC (opción 3).

### Qué cambia entre las tres

| Criterio | API directa del proveedor | Bedrock (gestionado en AWS) | Autoalojado (SageMaker o EKS) |
|---|---|---|---|
| Residencia de datos | Donde procese el proveedor; se acuerda por contrato | En la región elegida, salvo funciones que enrutan entre regiones (verificar) | Donde estén nuestras instancias |
| Camino de red | Internet vía NAT | Privado con interface endpoint | Interno a la VPC |
| Identidad y permisos | Clave de API compartida, a guardar y rotar | Roles de IAM por servicio, políticas por modelo, SCP | IAM para el endpoint; el modelo no sabe de identidades |
| Cuotas | Del proveedor, por organización o clave | Por cuenta y región, en peticiones y tokens por minuto | Las fija nuestra capacidad instalada |
| Latencia | Incluye salto por internet; variable con la carga del proveedor | Similar al proveedor, sin salir a internet; variable con la carga compartida | Predecible si se dimensiona bien; crece con la saturación |
| Modelo de costo | Por token | Por token (bajo demanda) o por capacidad reservada | Por hora de instancia, se use o no, más operación |
| Catálogo | Solo los modelos de ese proveedor | Varios proveedores detrás de una API | Modelos de pesos abiertos |
| Lock-in | Con el proveedor del modelo | Con AWS y sus funciones propias (agentes, bases de conocimiento) | Con nuestra propia plataforma; el modelo es portable |

**Por qué importa:** la decisión rara vez es "cuál es mejor", sino qué restricción manda en cada funcionalidad: un cliente que exige región, un pico que choca con cuotas, un volumen que vuelve cara la tarifa por token.

### El catálogo de Bedrock y la API unificada

Bedrock expone modelos de texto, embeddings e imágenes de varios proveedores. Cada modelo debe **habilitarse** en la cuenta y la región antes de usarse, y no todos están en todas las regiones: verificar disponibilidad en la documentación vigente.

Además de una invocación "cruda" con el formato propio de cada modelo, ofrece una **API de conversación unificada** (del estilo de Converse): mensajes, parámetros, herramientas y streaming con la misma forma para todos los modelos que la soportan. Cambiar de modelo pasa a ser cambiar un identificador.

El **tool use** funciona como en cualquier proveedor (ver [Agentes y tool calling](#t/agentes)): el modelo pide una herramienta con argumentos; nuestro código la ejecuta y devuelve el resultado. Bedrock no ejecuta nada.

**Ejemplo:** el agente de operaciones declara `consultar_metricas_zona(zona, desde, hasta)`. El modelo pide `{"zona": "norte", "desde": "08:00", "hasta": "10:00"}`; nuestro servicio consulta Prometheus con un rol de solo lectura y devuelve "tasa a tiempo: 81 %". Al probar otro modelo del catálogo, el bucle no cambia, pero hay que volver a correr las evals.

**Por qué importa:** la API unificada abarata cambiar de modelo dentro de Bedrock, no fuera. Con un gateway interno, Bedrock es un destino más.

### Bajo demanda frente a throughput aprovisionado

- **Bajo demanda:** se factura por token de entrada y de salida. No hay compromiso, pero se comparte capacidad con otros clientes y hay **cuotas** por cuenta y región.
- **Throughput aprovisionado:** se reserva capacidad dedicada (en unidades de modelo) por hora, con un plazo mínimo que puede ser de meses. Se factura esté en uso o no, a cambio de rendimiento predecible. Los términos exactos cambian: verificar en la documentación vigente.

Las cuotas bajo demanda se expresan típicamente en **peticiones por minuto** y **tokens por minuto (TPM)**. Al superarlas, la API responde con un error de throttling (equivalente a un 429).

**Ejemplo (cifras hipotéticas):** la cuota es de 400.000 TPM para un modelo. En hora pico el asistente atiende 200 conversaciones por minuto con 2.500 tokens cada una (prompt, fragmentos de RAG y respuesta): 500.000 TPM. Un 20 % de las llamadas recibe throttling. A verificar: algunos servicios descuentan de la cuota el `max_tokens` pedido, no lo generado, así que un máximo exagerado consume cuota.

**Por qué importa:** la cuota es capacidad, tan real como el CPU, y se planifica con el pronóstico de volumen.

### Guardrails gestionados y sus límites

Bedrock ofrece **Guardrails** configurables que se aplican a la entrada y la salida del modelo:

- **Filtros de contenido** por categoría (odio, violencia, intentos de inyección), con umbrales de sensibilidad.
- **Temas denegados**, descritos en lenguaje natural ("asesoramiento legal sobre litigios con comercios").
- **Filtros de PII:** bloquear o enmascarar teléfonos, direcciones, nombres y patrones propios con expresiones regulares.
- **Filtros de palabras** y, según la versión, controles de anclaje en el contexto provisto.

Son útiles como capa base, pero tienen límites concretos:

1. **Son probabilísticos.** Un filtro de PII puede no reconocer "Siempreviva setecientos cuarenta y dos" como dirección. Hay que medir su recall con ejemplos propios.
2. **Actúan donde corren.** Si el guardrail enmascara dentro de Bedrock, el texto original ya salió de nuestro servicio y pudo quedar en nuestros logs antes. El enmascarado del gateway sigue siendo la primera línea.
3. **No conocen el negocio.** No saben que el número de pedido citado debe existir; esa validación sigue en nuestro código.
4. **Agregan latencia y costo** por cada evaluación de texto.

**Ejemplo:** se activa el filtro de PII en modo enmascarar sobre las respuestas del asistente. En una muestra de 500 conversaciones con datos sintéticos, detecta el 96 % de los teléfonos y el 71 % de las direcciones escritas de formas poco comunes (cifras ilustrativas). Se mantiene como segunda capa, detrás del enmascarado del gateway.

### Knowledge Bases: RAG gestionado

Las **Knowledge Bases** de Bedrock resuelven el pipeline de [RAG](#t/rag) como servicio: se apunta a una fuente (por ejemplo, un prefijo de S3), se elige modelo de embeddings y almacén vectorial, y el servicio parte los documentos en fragmentos, calcula embeddings, sincroniza cambios y expone una llamada de recuperación (y otra de recuperación más generación con citas).

Se gana un prototipo en horas y cero código de indexación. Se resigna control fino del chunking, la búsqueda híbrida, el reranking y los filtros, y visibilidad de cada paso para diagnosticar. El almacén vectorial se factura aparte.

**Ejemplo:** un equipo quiere un buscador interno sobre 80 procedimientos de depósito que casi no cambian. Una Knowledge Base sobre el bucket alcanza: recall@5 aceptable en 40 preguntas de prueba y cero mantenimiento de pipeline.

### Bedrock Agents frente a un bucle propio

**Bedrock Agents** orquesta el bucle de un agente: se definen instrucciones, grupos de acciones (herramientas, por ejemplo funciones Lambda) y bases de conocimiento opcionales; el servicio decide los pasos y mantiene la sesión. La alternativa es un bucle propio con un framework como LangGraph, que llama al modelo (en Bedrock o en otro lado) y ejecuta las herramientas en nuestro servicio.

| Aspecto | Bedrock Agents | Bucle propio (por ejemplo, LangGraph) |
|---|---|---|
| Tiempo hasta un prototipo | Corto | Mayor |
| Control del flujo | El servicio decide la orquestación; se ajusta con instrucciones y plantillas | Total: grafo explícito, límites de pasos, aprobaciones humanas |
| Observabilidad | Trazas del servicio, en su formato | Spans propios por paso y herramienta, integrados con OpenTelemetry |
| Pruebas | Más difícil reproducir un paso aislado | Cada nodo se prueba como código |
| Portabilidad | Atada a AWS | El modelo y la nube se cambian detrás de una interfaz |
| Operación | Gestionada | Un servicio más que operar |

**Por qué importa:** los errores de un agente se diagnostican mirando qué decidió en cada paso; si eso no está en nuestra observabilidad, cada investigación es más lenta.

### Registro de invocaciones y retención de datos

Bedrock permite activar el **registro de invocaciones**: guardar en S3 o CloudWatch Logs las entradas y salidas de cada llamada, con la PII que contengan. Aplican las reglas de cualquier log: cifrado, acceso restringido, retención corta.

Otra cosa es lo que retiene el servicio o el proveedor del modelo. AWS describe compromisos de no usar los datos para entrenar ni compartirlos con los proveedores de modelos, pero hay que **verificarlo en los términos vigentes** del servicio y de cada modelo, igual que el procesamiento entre regiones y la detección de abuso.

### SageMaker: opciones de inferencia

SageMaker sirve modelos propios (el XGBoost de ETA, un modelo de embeddings, un LLM de pesos abiertos) con varias modalidades:

- **Endpoint en tiempo real:** instancias siempre encendidas detrás de HTTPS, con autoescalado por invocaciones por instancia. Se factura por hora.
- **Inferencia serverless:** sin instancias que administrar; escala a cero y se factura por tiempo de cómputo. Tiene arranque en frío de segundos y límites de memoria; hoy no ofrece GPU (verificar). Sirve para tráfico esporádico.
- **Inferencia asíncrona:** la petición se encola y el resultado se escribe en S3. Admite cargas grandes y procesos de minutos; puede escalar a cero.
- **Batch transform:** procesa un dataset completo en S3 y termina. Sin endpoint permanente.
- **Endpoints multimodelo:** muchos modelos del mismo tipo comparten las instancias y se cargan bajo demanda. Útil para cientos de modelos chicos con poco tráfico cada uno; la primera llamada a un modelo no cargado es lenta.

**Ejemplo:** el pronóstico nocturno encaja en batch transform; transcribir y resumir 3.000 llamadas de soporte por día, en asíncrona; un modelo de ETA por cada uno de 150 comercios grandes, en multimodelo.

### SageMaker o EKS para el modelo de ETA

El modelo de ETA hoy corre como microservicio en EKS con caché local de features alimentada por Kafka y un deadline de 30 ms (ver el tema de serving). ¿Mejora en un endpoint de SageMaker?

**SageMaker conviene cuando:** el equipo no quiere operar Kubernetes; se quieren variantes con tráfico repartido sin construirlas; el modelo no depende de lógica de features local; o hay muchos modelos chicos.

**EKS conviene cuando:** la latencia se gana con datos locales al proceso (la caché alimentada por Kafka no se replica fácil en un contenedor de SageMaker); el presupuesto de 50 ms no admite un salto HTTPS extra con su sobrecarga; el clúster ya existe con observabilidad y despliegue resueltos; y las instancias de SageMaker suelen tener un recargo frente a EC2 equivalente (verificar en la tabla de precios vigente).

Para Rumbo, el ETA en tiempo real queda en EKS; el entrenamiento, el pronóstico batch y los experimentos con modelos que necesitan GPU son buenos candidatos para SageMaker.

### Comparación de costos con cifras hipotéticas

Cifras inventadas para ilustrar el razonamiento. Volumen del asistente de soporte: 30 millones de tokens de entrada y 6 millones de salida por día (36 millones en total).

1. **Bajo demanda:** USD 3 por millón de entrada y USD 15 por millón de salida. Costo diario: 30 × 3 + 6 × 15 = 90 + 90 = USD 180. Mensual: unos USD 5.400.
2. **Throughput aprovisionado:** una unidad cuesta USD 20 por hora y el pico requiere dos. Mensual: 2 × 20 × 730 h = USD 29.200. Cinco veces más caro: solo se justifica con latencia garantizada como requisito o con volumen mucho mayor y estable.
3. **Autoalojado en GPU:** una instancia cuesta USD 6 por hora y procesa unos 1.500 tokens por segundo con batching. Al 100 % de uso serían 5,4 millones de tokens por hora, unos 130 millones por día. Se necesitan tres instancias para tener redundancia y absorber el pico: 3 × 6 × 730 = USD 13.140 al mes, más el tiempo del equipo que la opera. La utilización real es 36 / (3 × 130) ≈ 9 %. Costo efectivo: 13.140 / (36 × 30) ≈ USD 12 por millón de tokens, contra unos USD 5 por millón bajo demanda.

Con diez veces el volumen, bajo demanda cuesta unos USD 54.000 al mes; el autoalojado necesita unas cinco instancias (USD 21.900) con utilización cercana al 55 %. Ahí compite, si un modelo abierto alcanza la calidad necesaria en las evals.

**Por qué importa:** el costo por token de una capacidad fija depende de la utilización. Una GPU al 9 % es cara aunque su precio por hora parezca bajo.

## Casos prácticos

### Un cliente exige que los datos de destinatarios no salgan de la región

**Situación:** un cliente grande de Rumbo exige por contrato que los datos de sus destinatarios se procesen solo en su región y que ningún tercero fuera de ella los reciba. Hoy el clasificador de tickets usa la API directa de un proveedor.

**Qué se hace:**

1. Se rutea en el gateway: las peticiones con `comercio_id` de ese cliente van a Bedrock en la región exigida, por un interface endpoint, con un rol de IAM que solo permite invocar los modelos aprobados. Una SCP en la cuenta niega Bedrock en otras regiones.
2. Se desactivan las funciones de inferencia entre regiones para ese tráfico y se verifica en la documentación vigente qué procesamiento puede ocurrir fuera de la región.
3. El enmascarado del gateway sigue activo: el contrato es la segunda defensa.
4. Si el modelo necesario no está disponible en esa región, la alternativa es un modelo abierto autoalojado en la misma región; para clientes on-prem estrictos, ver [Despliegue híbrido y on-prem](#t/hibrido-on-prem).

Antes de cambiar el tráfico se corren las evals del clasificador con el modelo nuevo.

### Throttling en el pico por cuota de tokens por minuto

**Situación:** en la temporada alta, entre las 10:00 y las 11:00, el asistente de soporte recibe errores de throttling en el 15 % de las llamadas. La cuota de TPM de la cuenta se comparte con el resumen de tickets, que corre en el mismo horario.

**Qué se hace:**

- **Separar prioridades:** el gateway reserva una porción de la cuota para el asistente (interactivo) y manda los resúmenes a una cola que se procesa fuera del pico.
- **Ajustar `max_tokens`:** se baja de 4.000 a 800, el máximo real observado en el p99, por si la cuota descuenta por reserva.
- **Backoff con jitter** y degradación a personas si se agota el tiempo.
- **Pedir aumento de cuota con anticipación**, con el pronóstico de la temporada; puede tardar días.
- **Capacidad dedicada** solo para la base estable del pico, si el volumen la justifica.

Se agrega una alerta cuando el consumo supera el 70 % de la cuota durante cinco minutos.

### Knowledge Bases o el pipeline de RAG existente

**Situación:** un equipo propone reemplazar el pipeline propio de RAG del asistente por una Knowledge Base de Bedrock "para no mantener código".

**Qué se hace:** se prueba sobre el golden set existente de 200 preguntas. Resultado ilustrativo: recall@5 de 78 % con la Knowledge Base frente a 89 % del pipeline propio, que tiene búsqueda híbrida para códigos como RMB-E-207, reranking y filtros de vigencia y de `comercio_id` probados. Se mantiene el pipeline propio para el asistente. La Knowledge Base se adopta para el buscador interno de procedimientos de depósito, donde los documentos son pocos, estables y sin restricciones de acceso.

### El agente de operaciones pasa de Bedrock Agents a un bucle propio

**Situación:** el agente de operaciones se construyó con Bedrock Agents. Cuando se equivoca ("la caída en zona norte es por clima" cuando era un despliegue), cuesta reconstruir qué herramientas llamó y qué vio, y no se puede imponer un tope de pasos.

**Qué se hace:** se migra a un grafo propio en LangGraph que sigue llamando a modelos de Bedrock con la API unificada. Cada herramienta de solo lectura emite un span de OpenTelemetry con argumentos y duración, y se fija un límite de 12 pasos y 50.000 tokens por investigación. Se opera un servicio más, a cambio de diagnosticar en minutos y ganar portabilidad. Para un agente nuevo y sencillo, empezar con Bedrock Agents sigue siendo razonable.

## Errores comunes

- **Suponer que "está en AWS" implica que los datos no salen de la región.** Algunas funciones enrutan entre regiones; verificar la configuración y los términos vigentes, y reforzar con SCP.
- **Usar Guardrails como único control de PII.** Son probabilísticos y actúan después de que el texto salió del servicio; el enmascarado propio va primero.
- **Activar el registro de invocaciones sin política de retención.** Se acumulan prompts completos con datos personales; cifrar, restringir y expirar.
- **Contratar capacidad aprovisionada sin medir la utilización.** Una reserva al 10 % de uso cuesta varias veces más por token que bajo demanda.
- **Descubrir la cuota en el pico.** Las cuotas se planifican con el pronóstico de volumen y se piden con días de anticipación.
- **Elegir un servicio gestionado por la demo.** Se compara contra el golden set y las necesidades de observabilidad.

## Para discutir en equipo

- ¿Qué funcionalidades con LLM tienen hoy restricciones de región o de cliente que cambiarían el destino de sus llamadas?
- ¿Cuánto de nuestra cuota de tokens por minuto consumen procesos que podrían correr fuera del pico?
- ¿Qué volumen y qué utilización mínima tendríamos que ver para justificar capacidad aprovisionada o un modelo autoalojado?
- Si mañana tuviéramos que mover el agente de operaciones a otra nube, ¿qué partes habría que reescribir?
