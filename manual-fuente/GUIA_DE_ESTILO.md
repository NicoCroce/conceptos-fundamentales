# Guía de redacción · Manual de estudio AI/ML y Plataforma

Vas a escribir capítulos de un manual de estudio interno para un equipo de ingeniería de AI/ML y plataforma. El manual se publica como sitio web y lo lee todo el equipo: ingenieros backend, de ML y de plataforma, de distintos niveles. El objetivo es **entender** cada tema lo suficiente para conversar con criterio, revisar diseños y cuestionar decisiones; no hace falta implementarlo.

## Reglas obligatorias

1. **Idioma:** castellano neutro (rioplatense suave está bien, pero sin voseo: usa "tú" o impersonal). Los términos técnicos en inglés se mantienen cuando son de uso común (token, embedding, deploy, rollback), explicándolos la primera vez.
2. **Cero contenido de pagos.** No menciones pagos, cobros, tarjetas, PSP, PCI, adquirentes, emisores, contracargos, fraude financiero, bancos, ledger, conciliación ni dinero de clientes. (Excepción: «reconciliación» en su sentido técnico de GitOps y Kubernetes, comparar el estado deseado con el real, está permitida.) Tampoco como ejemplo. Si un concepto venía ilustrado con pagos, reemplázalo por el escenario de abajo.
3. **Orientado al equipo, no a una entrevista.** Nada de "en la entrevista", "tu equipo", "como manager". Escribe para el lector que integra el equipo ("el equipo", "nosotros" está bien).
4. **Nivel de detalle ampliado.** Cada concepto se explica paso a paso, con un ejemplo concreto y numérico cuando se pueda, y con por qué importa. Suponé un lector inteligente que NO conoce el tema. Evita definiciones de una línea.
5. **No inventes datos que se puedan verificar como falsos.** Precios, versiones y cifras van como "hipotéticos" o "orden de magnitud" salvo que sean conocimiento estable. No incluyas enlaces externos.
6. **Formato:** markdown estándar (encabezados, listas, tablas GFM, bloques de código con lenguaje, negritas). Sin HTML. Sin emojis.

## Escenario de ejemplo común: "Rumbo"

Para que los ejemplos se conecten entre capítulos, usa esta empresa ficticia:

**Rumbo** es una plataforma de logística de última milla. Los comercios cargan pedidos; Rumbo asigna cada pedido a un transportista, calcula el tiempo estimado de entrega (ETA), hace seguimiento en vivo y atiende consultas de soporte.

Sistemas que puedes usar en los ejemplos:
- **Servicio de asignación** (Go): decide en tiempo real qué transportista toma cada pedido. Llama a un **modelo de ML** que estima probabilidad de entrega a tiempo y ETA por transportista. Presupuesto de latencia: ~50 ms.
- **Modelo de ETA** (XGBoost, Python): predice minutos hasta la entrega. Features: distancia, zona, hora, clima, carga actual del transportista, historial.
- **Pronóstico de demanda** (batch nocturno): pedidos esperados por zona y franja horaria.
- **Eventos** en Kafka: pedido creado, asignado, retirado, entregado, fallido.
- **Asistente de soporte con LLM:** RAG sobre manuales y políticas; clasifica tickets; resume casos.
- **Agente interno de operaciones:** investiga alertas (por ejemplo, "cayó la tasa de entregas a tiempo en la zona norte") con herramientas de solo lectura.
- **Datos personales:** nombre, teléfono y dirección de destinatarios (PII que hay que proteger).
- **Infra:** AWS (EKS, Aurora PostgreSQL, S3, Terraform), algunos clientes grandes exigen instalación on-prem.

No hace falta usar Rumbo en todo: los ejemplos genéricos claros también valen.

## Estructura de cada archivo

Un archivo por tema: `/home/claude/manual/content/<slug>.md`. Respeta exactamente este esqueleto:

```
---
slug: <slug>
titulo: <Título del tema>
resumen: <Una oración de 15 a 25 palabras que diga qué es y para qué sirve.>
lectura: <minutos estimados de lectura, número entero>
---

## La idea central

Uno o dos párrafos que den la intuición antes del detalle. Puede incluir una analogía.

## Conceptos

### <Concepto 1>

Explicación paso a paso (2 a 4 párrafos cortos o párrafo + lista).

**Ejemplo:** un caso concreto, idealmente con números.

**Por qué importa:** una o dos oraciones. (Opcional si ya quedó claro.)

### <Concepto 2>
...

(Incluye una tabla comparativa cuando ayude a decidir entre opciones.)

## Casos prácticos

### <Título breve del caso>

**Situación:** qué pasa.
**Qué se hace:** la decisión o solución, y por qué.

(3 o 4 casos.)

## Errores comunes

- 4 a 6 viñetas: el error y cómo evitarlo, en una o dos oraciones cada una.

## Para discutir en equipo

- 3 a 5 preguntas abiertas para una sesión de estudio o una revisión de diseño.
```

Extensión orientativa: 1.500 a 2.500 palabras por tema. Más corto si el tema es chico (Go, Python).

## Referencias cruzadas

Para enlazar otro tema usa `[texto](#t/<slug>)` con los slugs de la lista de abajo. Úsalas con moderación (2 a 4 por tema), solo cuando ayuden.

## Lista completa de temas y slugs

**Capítulo 1 · LLMs**
- fundamentos-llms · Fundamentos de LLMs
- prompt-engineering · Prompt engineering
- rag · RAG (Retrieval-Augmented Generation)
- embeddings · Embeddings y bases vectoriales
- multimodelo · Varios modelos y ruteo
- multimodal · Modelos multimodales: visión y voz
- adaptar-modelos · Adaptar modelos: fine-tuning, destilación y cuantización
- evaluacion-llms · Evaluación de LLMs

**Capítulo 2 · Agentes**
- agentes · Agentes y tool calling
- arnes-agentes · El arnés de un agente (agent harness)
- artefactos-agentes · Artefactos de un agente: el mapa completo
- instrucciones-reglas · Instrucciones y reglas de proyecto para agentes
- comandos-agentes · Comandos y prompts reutilizables
- skills-agentes · Skills: conocimiento que el agente carga cuando lo necesita
- hooks-agentes · Hooks: reglas que el agente no puede saltarse
- langgraph · LangGraph y LangChain
- mcp · MCP (Model Context Protocol)
- contexto-memoria · Contexto y memoria de agentes
- subagentes · Subagentes y sistemas multiagente
- meta-arnes · Meta-arnés: arneses que diseñan y orquestan arneses
- llms-produccion · LLMs en producción

**Capítulo 3 · Arquitectura y backend**
- revision-arquitectura · Revisión de arquitectura
- arquitectura-capas-hexagonal · Arquitectura en capas, hexagonal y limpia
- ddd · Domain-Driven Design
- sistemas-distribuidos · Sistemas distribuidos
- latencia-disponibilidad · Baja latencia y alta disponibilidad
- resiliencia · Patrones de resiliencia
- grpc-rest · gRPC y REST
- event-streaming · Event streaming
- bases-de-datos · Bases de datos

**Capítulo 4 · Diseño de software y patrones**
- principios-solid · SOLID y principios de diseño
- patrones-creacionales · Patrones creacionales: Factory, Builder y Singleton
- patrones-estructurales · Patrones estructurales: Adapter, Decorator, Facade y Proxy
- patrones-comportamiento · Patrones de comportamiento: Strategy, Observer, Command y State
- inyeccion-dependencias · Inyección de dependencias
- ddd-tactico · DDD táctico: entidades, objetos de valor y agregados
- patron-repository · Patrón Repository y Unit of Work
- cqrs-event-sourcing · CQRS y Event Sourcing
- testing-dobles · Testing y dobles de prueba

**Capítulo 5 · Machine Learning**
- fundamentos-ml · Fundamentos de ML
- xgboost · XGBoost y scikit-learn
- ciclo-vida-modelos · Ciclo de vida de modelos
- serving · Serving e inferencia en tiempo real
- monitoreo-modelos · Monitoreo de modelos
- feature-stores · Features y feature stores
- mlflow · MLflow y Weights & Biases
- pytorch-tensorflow · PyTorch y TensorFlow

**Capítulo 6 · Observabilidad**
- on-call · On-call, runbooks e incidentes
- opentelemetry · OpenTelemetry y tracing
- prometheus-grafana · Prometheus y Grafana
- logging · Logging estructurado

**Capítulo 7 · Cloud e infraestructura**
- aws · Fundamentos de AWS
- ec2 · EC2 y cómputo en AWS
- contenedores · Contenedores, ECS y EKS
- colas-serverless · Colas y serverless en AWS
- rds-aurora · RDS y Aurora
- s3 · S3
- bedrock-sagemaker · IA gestionada en AWS: Bedrock y SageMaker
- terraform · Terraform
- ci-cd · CI/CD y GitOps
- hibrido-on-prem · Despliegue híbrido y on-prem
- finops · Costos cloud (FinOps)

**Capítulo 8 · Frontend y web**
- http · HTTP de punta a punta
- arquitectura-frontend · Arquitectura de frontend
- componentizacion · Componentización
- eventos-dom · Eventos y event listeners
- web-components · Web components
- design-systems · Design systems para interfaces con agentes
- responsive · Diseño responsive
- pwa · Service workers y PWA
- recorrido-punta-a-punta · Recorrido de punta a punta: una consulta al asistente

**Capítulo 9 · UX, UI y diseño**
- ux-ui-fundamentos · UX y UI: fundamentos
- investigacion-usabilidad · Investigación de usuarios y pruebas de usabilidad
- heuristicas-nielsen · Las 10 heurísticas de Nielsen
- leyes-ux-diseno-visual · Leyes de UX y diseño visual
- accesibilidad · Accesibilidad web
- ux-agentes · UX de interfaces con agentes

**Capítulo 10 · Seguridad**
- fundamentos-seguridad · Fundamentos de seguridad y modelado de amenazas
- autenticacion · Autenticación, JWT y OAuth
- secretos · Secretos y cifrado
- seguridad-apis · Seguridad de APIs y backend
- seguridad-frontend · Seguridad en el frontend
- cloudflare · Cloudflare y protección perimetral
- seguridad-agentes · Seguridad de LLMs y agentes
- cadena-suministro · Cadena de suministro y vulnerabilidades
- privacidad-datos · Privacidad y datos personales

**Capítulo 11 · Metodologías y gestión**
- agile-scrum · Agile, Scrum y Kanban
- priorizacion · Herramientas de priorización
- estimacion · Estimación de esfuerzo
- triangulo-hierro · El triángulo de hierro: alcance, tiempo y costo
- wbs-edt · EDT o WBS: estructura de desglose del trabajo
- planificacion-gantt · Planificación y diagramas de Gantt
- raci-rasi · Matrices de responsabilidad: RACI y RASI
- riesgos · Gestión y medición de riesgos
- metricas-entrega · Métricas de entrega: DORA y flujo
- sdd · Desarrollo guiado por especificaciones (SDD) con agentes de código
- odd · Organic Driven Development (ODD): proceso proporcional con agentes

**Capítulo 12 · Análisis, decisiones y documentos**
- objetivos-smart · Objetivos SMART
- roi · ROI: retorno de la inversión
- pareto · Principio de Pareto (80/20)
- cinco-porques · La técnica de los 5 porqués
- brainstorming-mapas-mentales · Brainstorming y mapas mentales
- postmortem-premortem · Postmortem y premortem
- prd · PRD: documento de requisitos de producto
- rfc · RFC: propuestas técnicas por escrito

**Capítulo 13 · Comunicación y feedback**
- comunicacion-asertiva · Comunicación asertiva
- feedback-sbi · Cómo dar feedback: el modelo SBI
- feedback-revisiones · Feedback en revisiones de código y diseño

**Capítulo 14 · Lenguajes y frameworks**
- go · Go
- python · Python
- typescript · TypeScript
- react · React
- kotlin · Kotlin en el backend

Los perfiles (IA, Backend, Frontend, Plataforma, Diseño, Gestión) se definen en `PERFILES` de `build.py`. Al sumar un tema, agrégalo también a los perfiles que correspondan.

## Gráficos

Algunos bloques de código se convierten en figuras con los colores del tema claro y oscuro. Reglas comunes: sin líneas en blanco dentro del bloque, `titulo:` opcional en la primera línea, campos separados por `|`, textos cortos (menos de 40 caracteres por ítem). Úsalos cuando el gráfico explique mejor que el texto; uno o dos por tema bastan.

**Gantt** (`gantt`): una tarea por línea, `Nombre | inicio | duración | critica` (inicio desde 0, duración 0 = hito, `critica` opcional). `unidad:` opcional (por defecto, semana).

```gantt
titulo: Piloto del asistente
unidad: semana
Definir casos y métricas | 0 | 1
Servidor MCP de envíos | 1 | 3 | critica
Hito: decisión | 4 | 0 | critica
```

**Cuadrante 2×2** (`cuadrante`): ejes con extremo bajo y alto; cada cuadrante con título e ítems separados por `;`.

```cuadrante
titulo: Matriz de Eisenhower
eje-x: Menos urgente | Más urgente
eje-y: Menos importante | Más importante
arriba-izquierda: Planificar | PII en logs; MCP de zonas
arriba-derecha: Hacer ahora | Caída del asistente
abajo-izquierda: Eliminar | Modo oscuro
abajo-derecha: Delegar | Reporte semanal
```

**Mapa de calor 5×5** (`calor`): una línea por riesgo, `Etiqueta | probabilidad (1-5) | impacto (1-5)`. El color de cada celda sale de probabilidad × impacto.

```calor
titulo: Riesgos del asistente
R1 Alucinaciones | 4 | 4
R2 Caída del proveedor | 2 | 5
```

**Barras horizontales** (`barras`): `Etiqueta | valor`. `unidad:` opcional, se muestra junto a cada valor.

```barras
titulo: Puntaje RICE
unidad: puntos
Asistente para transportistas | 1200
Modo oscuro | 90
```

**Triángulo** (`triangulo`): tres vértices y un centro; cada uno con texto opcional después de `|`.

```triangulo
titulo: Triángulo de hierro
arriba: Alcance | qué se entrega
izquierda: Tiempo | fecha
derecha: Costo | personas y presupuesto
centro: Calidad
```

**Matriz de roles** (`roles`): primera línea `columnas:` con los roles; luego `Actividad | letra | letra…`. Las letras R, A, S, C, I (o combinaciones como `R/A`) se pintan con colores distintos y se agrega la leyenda.

```roles
titulo: RASI del lanzamiento
columnas: Producto | Tech lead | Plataforma | Seguridad
Definir alcance | A | R | I | S
Revisión de seguridad | I | S | S | R/A
```

**Pareto** (`pareto`): `Causa | valor`. Se ordena de mayor a menor, muestra el porcentaje acumulado y resalta las causas que suman hasta el 80 %. `unidad:` opcional.

```pareto
titulo: Motivos de tickets de soporte
unidad: tickets
Dirección incompleta | 420
Ventana horaria no cumplida | 260
Otros | 40
```

**5 porqués** (`porques`): `problema:`, luego una línea por cada respuesta a «¿por qué?», y al final `causa:` y `accion:` (ambos opcionales).

```porques
titulo: El asistente respondió con datos de ayer
problema: Un comercio vio el estado de un envío de hace 20 horas
La respuesta salió de la caché del gateway
La caché guardaba respuestas con datos personales por 24 h
La regla de caché se copió de otro endpoint
No hay revisión de cabeceras de caché en los PRs
causa: Falta un control de caché por tipo de endpoint
accion: Lista de endpoints que no se cachean y prueba en CI
```

**Árbol** (`arbol`): la primera línea sin guiones es la raíz; cada nivel se marca con guiones (`-` primer nivel, `--` segundo, `---` tercero). Sirve para EDT/WBS y mapas mentales; cada rama de primer nivel toma un color.

```arbol
titulo: EDT del piloto del asistente
Piloto del asistente
- 1 Gestión del proyecto
-- 1.1 Plan y seguimiento
-- 1.2 Riesgos
- 2 Datos
-- 2.1 Golden set
```

## Glosario

Además de los temas, escribe `/home/claude/manual/content/glosario-<tu-lote>.json`: una lista JSON de 8 a 15 términos clave de tus temas, cada uno `{"termino": "...", "definicion": "una o dos oraciones claras", "slug": "<slug del tema donde se explica>"}`.

## Antes de terminar

- Relee cada archivo y verifica que no aparezcan las palabras prohibidas de la regla 2 (busca con grep -i: pago, tarjeta, PSP, PCI, adquirente, emisor, contracargo, fraude, cobro, banco).
- Verifica que el front matter esté completo y que el slug coincida con el nombre del archivo.
- Responde al final solo con la lista de archivos escritos y sus palabras aproximadas.
