---
slug: meta-arnes
titulo: Meta-arnés: arneses que diseñan y orquestan arneses
resumen: Qué es un meta-arnés en sus dos sentidos, optimizador que busca mejores arneses y orquestador que lanza y verifica agentes, y cuándo conviene.
lectura: 21
---

## La idea central

En [El arnés de un agente](#t/arnes-agentes) vimos que el modelo es solo una parte del sistema: el código que lo rodea decide qué contexto ve, qué herramientas tiene, qué permisos aplica y cuándo se detiene. Ese código se escribe a mano y se ajusta a prueba y error. Un **meta-arnés** (en inglés, *meta-harness*) es un arnés cuyo trabajo son otros arneses, y la palabra se usa con dos sentidos que conviene no mezclar:

1. **Meta-arnés como optimizador.** Genera variantes de un arnés, las ejecuta sobre un conjunto de tareas, las puntúa y usa todo lo aprendido para proponer variantes mejores. Es automatizar la ingeniería de arneses. El trabajo de referencia es el paper *Meta-Harness: End-to-End Optimization of Model Harnesses* (Lee y otros, Stanford, KRAFTON y MIT, marzo de 2026).
2. **Meta-arnés como orquestador.** Lanza, supervisa y combina varias sesiones de agentes, cada una con su propio arnés completo: un supervisor que abre cinco sesiones del agente de código en ramas separadas, un pipeline de CI que ejecuta agentes, un motor de workflows que reparte trabajo y verifica lo que vuelve.

El primero se parece a un equipo de puesta a punto que no fabrica el motor pero prueba configuraciones y lee los registros de cada corrida; el segundo, a una jefatura de obra que asigna cuadrillas e inspecciona lo construido. En los dos, el valor está en medir y verificar.

## Conceptos

### Dos sentidos, una misma palabra

Los dos sentidos comparten la idea de "un nivel por encima del arnés", pero resuelven problemas distintos.

| | Meta-arnés optimizador | Meta-arnés orquestador |
|---|---|---|
| Qué produce | Código de arnés mejor que el inicial | Trabajo terminado por varios agentes |
| Insumo clave | Suite de tareas con puntaje automático | Lista de trabajos con criterio de terminado |
| Riesgo principal | Sobreajuste a la suite | Fallas y costos que se multiplican |

**Ejemplo:** en Rumbo, "meta-arnés" puede ser un job semanal que prueba 30 variantes del arnés del clasificador de tickets (optimizador) o el job nocturno que reparte la actualización de 40 servicios entre cinco sesiones del agente de código (orquestador).

**Por qué importa:** en una revisión de diseño, las preguntas de seguimiento dependen de en qué sentido se usa la palabra.

### Qué se optimiza: el código del arnés, no el prompt

Un optimizador de prompts busca un texto mejor. Un meta-arnés optimizador busca un **programa** mejor: el código que decide qué información se guarda, cuál se recupera y cómo se presenta al modelo (qué ejemplos, qué recuperador, cómo se resume el historial, qué validaciones corren).

El paper de Meta-Harness parte de esa observación: el rendimiento de un sistema con LLM depende mucho de su arnés, los arneses se diseñan casi siempre a mano y los optimizadores de texto existentes **comprimen demasiado la retroalimentación** para trabajar sobre algo tan grande como el código de un arnés. La propuesta es una búsqueda en un bucle externo sobre ese código, con el modelo base congelado.

**Ejemplo:** el arnés del clasificador de tickets de Rumbo decide cuántos tickets etiquetados mostrar como ejemplo (4, 8 o 32), si se eligen al azar o por similitud, si se agrega la política vigente de reprogramación y si se pide una justificación antes de la etiqueta. Cambiar el prompt toca una de esas decisiones; cambiar el arnés puede tocarlas todas.

**Por qué importa:** si el equipo ya probó todo lo razonable en el prompt y el resultado no se mueve, el margen suele estar en el arnés.

### El bucle externo, paso a paso

El bucle "de adentro" es el del agente: pensar, llamar herramientas, observar. El **bucle externo** envuelve ejecuciones completas de ese bucle:

1. **Inicializar.** Se parte de arneses conocidos (el de producción, uno mínimo), se ejecutan sobre la suite y se guardan su código, sus puntajes y sus trazas.
2. **Proponer.** Un agente **proponente** lee lo acumulado y escribe arneses nuevos. En el paper es un agente de código (Claude Code con Opus 4.6, guiado por una skill mínima del dominio) y no hay una regla fija para elegir de qué candidato partir.
3. **Validar la interfaz.** Antes de gastar en evaluar, se comprueba que el candidato exponga las funciones esperadas y corra sobre un caso trivial.
4. **Ejecutar y puntuar** sobre la suite de búsqueda, con el modelo congelado.
5. **Guardar todo**: código, puntajes y trazas completas, en un directorio por candidato.
6. **Repetir** durante N iteraciones o hasta agotar el presupuesto.
7. **Devolver la frontera de Pareto**: los candidatos que no son superados en todos los objetivos a la vez. Solo esos se evalúan sobre el conjunto de prueba reservado.

```python
def meta_arnes(suite_busqueda, modelo, proponente, iteraciones, k=2):
    fs = SistemaDeArchivos("runs/")
    for arnes in arneses_iniciales():
        evaluar_y_guardar(arnes, suite_busqueda, modelo, fs)

    for t in range(iteraciones):
        # El proponente es un agente: explora fs con grep/cat, no recibe un resumen
        for arnes in proponente.proponer(fs, cantidad=k):
            if not cumple_interfaz(arnes):
                fs.registrar_rechazo(arnes)
                continue
            evaluar_y_guardar(arnes, suite_busqueda, modelo, fs)

    return frontera_pareto(fs, objetivos=["precision", "tokens_contexto"])


def evaluar_y_guardar(arnes, suite, modelo, fs):
    trazas = [ejecutar_en_sandbox(arnes, tarea, modelo) for tarea in suite]
    fs.guardar(arnes.codigo, puntuar(trazas, suite), trazas)
```

Las corridas del paper son acotadas: unos 60 arneses en 20 iteraciones en una corrida típica, 40 candidatos en clasificación y 109 en matemática, con "unas pocas horas" por búsqueda y la evaluación como cuello de botella.

**Ejemplo:** en una iteración para el clasificador de Rumbo, el proponente lee los fallos del mejor candidato, ve que confunde "demora" con "dirección incorrecta" cuando el ticket menciona un cambio de domicilio y escribe una variante que recupera ejemplos por similitud. Esa variante se corre sobre 200 tickets de búsqueda y se guarda con sus 200 trazas.

**Por qué importa:** cada paso es un punto de control. Si la búsqueda da malos resultados, se puede saber si falló el proponente, la validación, la suite o la métrica.

### Por qué la retroalimentación comprimida pierde información

La pregunta central del paper es qué necesita ver el proponente para mejorar. Hay tres opciones:

- **Solo puntajes:** "el candidato 12 sacó 41 %".
- **Puntajes y un resumen:** "sacó 41 %; falla sobre todo en documentos largos".
- **Todo:** código, puntajes y **trazas crudas** (prompts enviados, llamadas a herramientas, salidas del modelo, cambios de estado) de todos los candidatos anteriores.

Un puntaje dice *cuánto* falló un candidato, no *por qué*. Un resumen lo escribe otro modelo que descarta detalles que quizás eran la clave, como que el recuperador devolvió tres veces el mismo ejemplo. Es el mismo problema de los resúmenes de [subagentes](#t/subagentes).

El paper lo mide con una ablación en clasificación de texto, sobre el conjunto de búsqueda. Según lo reportado por los autores:

```barras
titulo: Ablación del proponente (mediana reportada)
unidad: %
Solo puntajes | 34,6
Puntajes y resumen | 34,9
Código, puntajes y trazas | 50,0
```

Los mejores candidatos siguen el mismo patrón: 41,3 con solo puntajes, 38,7 con resumen y 56,7 con acceso completo. El resumen casi no agregó nada; las trazas crudas sí.

**Ejemplo:** si el agente de operaciones de Rumbo saca 70 % en la suite de alertas, el número no dice que los fallos se concentran en la zona norte porque la herramienta de métricas devuelve esa zona con otro nombre. La traza de un caso fallido lo muestra en una línea.

**Por qué importa:** en cualquier ciclo de mejora, automático o humano, hay que guardar las trazas completas y no solo el tablero de puntajes.

### El sistema de archivos como memoria del proponente

Meter todas las trazas de todos los candidatos en un prompt es imposible: el paper menciona que una sola evaluación puede producir hasta 10 millones de tokens de información de diagnóstico. La solución es **ponerla en disco** y dejar que el proponente la explore como explora un repositorio, con `grep` y `cat`: abre el código del mejor candidato, busca los casos fallidos, compara versiones. En una corrida de diez iteraciones sobre TerminalBench-2, el proponente leyó una mediana de 82 archivos por iteración: alrededor de 41 % código de arneses, 40 % trazas y solo 6 % puntajes o resúmenes.

```text
runs/
  cand-007/
    arnes.py
    puntajes.json        # precision, tokens_contexto, por tarea
    trazas/
      tarea-001.jsonl    # prompts, llamadas, salidas, estado
  cand-008/
    ...
```

**Ejemplo:** el proponente que optimiza el clasificador de Rumbo busca en las trazas del candidato 14 los tickets mal etiquetados como `demora` y descubre que 18 de 22 estaban en portugués. Ningún puntaje agregado lo habría mostrado.

**Por qué importa:** el proponente depura en lugar de adivinar, y el directorio sirve de auditoría.

### Lo que reporta el paper

Los resultados son los reportados por los autores, sin réplica independiente que conozcamos. El modelo base queda congelado en todos los casos.

| Dominio | Qué se buscó | Resultado reportado |
|---|---|---|
| Clasificación de texto en línea | Manejo de contexto (GPT-OSS-120B) | 48,6 % en prueba frente a 40,9 % de ACE, el mejor previo: 7,7 puntos más con unas 4 veces menos tokens de contexto |
| Matemática con recuperación | Recuperación sobre más de 500.000 problemas resueltos | Un único arnés suma 4,7 puntos en promedio sobre cinco modelos en 200 problemas de nivel olímpico (38,8 % frente a 34,1 % sin recuperador) |
| Programación con agentes | Arnés completo en TerminalBench-2 (89 tareas) | 76,4 % con Opus 4.6, segundo de su grupo (el primero, 81,8 %, no pudo reproducirse según los autores); 37,6 % con Haiku 4.5, primero de su grupo |

Matices que documenta el propio paper:

- En clasificación, el proponente no vio resultados de prueba; en nueve conjuntos ajenos a la búsqueda, 73,1 % frente a 70,2 % de ACE.
- En matemática, la búsqueda usó 250 problemas aparte y uno de los cinco modelos; los otros cuatro no participaron.
- En TerminalBench-2, búsqueda y evaluación usan las mismas 89 tareas; los autores auditaron filtraciones, pero el arnés queda especializado en ese benchmark.

**Ejemplo:** leer la fila de TerminalBench-2 como "esto mejora nuestro agente de código en 10 puntos" sería un error doble: el arnés se ajustó a esas 89 tareas y nuestras tareas no se parecen a ellas.

**Por qué importa:** las cifras dan un orden de magnitud, no una promesa; lo transferible es el método.

### Presupuesto y costo de la búsqueda

El costo sale de tres cuentas, que conviene hacer antes de la primera corrida:

- **Ejecución:** candidatos × tareas × repeticiones × tokens por tarea.
- **Propuesta:** iteraciones × tokens que lee el proponente por iteración.
- **Tiempo:** ejecuciones × segundos por ejecución ÷ paralelismo.

**Ejemplo:** cálculo hipotético para el clasificador de Rumbo, con precios inventados. 30 candidatos (15 iteraciones de 2), 200 tickets, 3 repeticiones para absorber el no determinismo (ver [Evaluación de LLMs](#t/evaluacion-llms)) y 8.000 tokens por ejecución: 30 × 200 × 3 × 8.000 = 144 millones de tokens; a 0,40 dólares por millón, unos **58 dólares**. El proponente lee 400.000 tokens por iteración: 15 × 400.000 = 6 millones; a 5 dólares por millón, **30 dólares**. Total, cerca de **90 dólares por búsqueda**. Tiempo: 18.000 ejecuciones de 10 segundos con 20 en paralelo, 9.000 segundos, unas **2,5 horas**. Si en cambio el arnés es de un agente que tarda 5 minutos por tarea, la misma cuenta da 18.000 × 300 ÷ 20 = 75 horas, y los tokens se multiplican.

**Por qué importa:** cada iteración dispara cientos de ejecuciones. Las palancas son una suite más chica y representativa, descartar candidatos que fallan en las primeras 20 tareas y un tope duro de gasto en la configuración.

### Sobreajuste a la suite y conjuntos reservados

Un meta-arnés optimiza lo que la suite mide, con más empeño que cualquier persona, y puede terminar con un arnés que acierta esos casos por razones que no generalizan: reglas con palabras de casos concretos o ejemplos copiados de la suite. Las defensas:

1. **Tres conjuntos:** búsqueda (lo que ve el proponente), validación (para elegir dentro de la frontera) y prueba (una sola vez, al final).
2. **El proponente no ve puntajes ni trazas de validación ni de prueba.**
3. **Conjuntos fuera de distribución:** tickets de otro mes, de otro país, de otro comercio grande.
4. **Modelos reservados**, si el arnés se va a usar con varios.
5. **Auditoría del código:** buscar cadenas literales de la suite dentro del arnés propuesto.

**Ejemplo:** el mejor candidato saca 91 % en búsqueda y 78 % en prueba, frente a 80 % del arnés de producción en ambos. La brecha delata sobreajuste; se descarta aunque su número de búsqueda sea el más alto.

**Por qué importa:** el número que se muestra en una revisión es siempre el de prueba.

### Seguridad: un agente que escribe el código del arnés

El proponente escribe código que se ejecuta y que decide qué herramientas y permisos tiene un agente. Se trata con los principios de [Seguridad de LLMs y agentes](#t/seguridad-agentes):

- **Sandbox por evaluación:** contenedor sin red salvo el endpoint del modelo, sin credenciales de producción, con límites de CPU, memoria y tiempo.
- **Evaluador fuera de alcance:** el código que puntúa, la suite y los conjuntos reservados son de solo lectura. Un candidato que "mejora" editando el evaluador es el caso clásico de *reward hacking*.
- **Límites al diff:** el proponente solo modifica archivos de una lista, y un diff que toque la lista de herramientas o la política de permisos se rechaza o pasa a revisión humana.
- **Revisión antes de producción:** el ganador entra por un PR normal, con las evals de seguridad del equipo. El meta-arnés propone; no despliega.

**Ejemplo:** un candidato del agente de operaciones mejora 6 puntos porque agrega una herramienta que reinicia pods "para verificar" hipótesis. La regla de diff lo rechaza sin evaluarlo: ese agente solo admite herramientas de solo lectura.

**Por qué importa:** optimizar por precisión empuja hacia más permisos y menos controles; la seguridad tiene que estar en las reglas del juego.

### Varios objetivos: precisión, tokens y seguridad

Elegir "el arnés con más aciertos" casi nunca es correcto: ganar 2 puntos usando cuatro veces más contexto puede no convenir. Por eso Meta-Harness devuelve una frontera de Pareto entre precisión y tokens, y el equipo elige dentro de ella.

Un trabajo posterior, *MoMHa: Multi-Objective Optimization of LLM Harnesses over Accuracy, Safety, and Tokens* (Mukherjee y Tanjim, NeurIPS 2026), extiende la idea a tres ejes: precisión, seguridad de comportamiento y tokens. Según lo reportado, un proponente que optimiza los tres a la vez con una recompensa conjunta, viendo el puntaje de cada eje y las trazas, supera a optimizar primero precisión y después tokens, a recibir solo un puntaje escalar y a optimizar solo precisión, y logra el mejor puntaje compuesto de seguridad medido en U-SafeBench (0,781).

**Ejemplo:** para el asistente de soporte de Rumbo, los ejes podrían ser tasa de resolución, tokens por conversación y tasa de rechazo correcto en casos de red teaming (pedidos de datos de otro destinatario, instrucciones inyectadas en comentarios de pedidos). Un candidato con 84 %, 3.000 tokens y 98 % de rechazos correctos puede ser preferible a otro con 86 %, 9.000 tokens y 90 %.

**Por qué importa:** si la seguridad no es un objetivo medido dentro de la búsqueda, la búsqueda la sacrifica sin que nadie lo decida.

### Relación con los optimizadores de prompts

El meta-arnés es el siguiente paso de una línea de trabajo conocida:

| Enfoque | Qué cambia | Qué ve el optimizador |
|---|---|---|
| Estilo DSPy | Instrucciones y ejemplos de módulos fijos | Una métrica sobre ejemplos |
| Estilo OPRO | Un texto | Textos anteriores y sus puntajes |
| Evolutivo o reflexivo (GEPA, OpenEvolve) | Texto o código | Puntajes y reflexiones resumidas |
| Meta-arnés | Código completo del arnés | Código, puntajes y trazas crudas |

En la ablación de clasificación, el paper compara contra GEPA, OpenEvolve, TTT-Discover y Best-of-N, con medianas reportadas de 32,6 a 39,1 frente a 50,0.

**Ejemplo:** si el clasificador de Rumbo falla porque la instrucción es ambigua entre dos etiquetas, un optimizador de prompts lo resuelve más barato. Si falla porque los ejemplos se eligen mal o el contexto se llena de tickets irrelevantes, hay que tocar código.

**Por qué importa:** la herramienta más barata que resuelve el problema es la correcta.

### Meta-arnés como orquestador: qué cambia respecto de los subagentes

Un **meta-arnés orquestador** lanza sesiones completas de agentes y las coordina desde afuera. La diferencia con [Subagentes y sistemas multiagente](#t/subagentes) es dónde vive la coordinación:

| | Subagentes dentro de un arnés | Meta-arnés orquestador |
|---|---|---|
| Quién coordina | El modelo, con una herramienta `delegar` | Código (script, job, motor de workflows) |
| Aislamiento | Mismo proceso y sistema de archivos | Proceso, worktree y rama propios |
| Contexto | Limpio, dentro de la misma sesión | Independiente y persistente por hijo |
| Permisos | Subconjunto de los del padre | Configurados por hijo, de forma explícita |
| Presupuesto | Compartido con la sesión padre | Tope por hijo y tope global |
| Duración | Minutos | Horas, con reanudación |

El patrón típico: una cola de trabajos, un número fijo de **trabajadores** (cada uno, una sesión del agente de código en su propio *worktree* de git y su propia rama), un **verificador** que decide si se acepta cada resultado y un **agregador** que abre los PRs y escribe el informe. El orquestador no necesita ser un LLM; suele convenir que sea código, para que reparto, reintentos y topes sean predecibles.

**Ejemplo:** el pipeline de CI de Rumbo lanza una sesión del agente de código por cada PR de dependencias que falla, con escritura solo sobre esa rama y sin secretos de despliegue.

**Por qué importa:** la coordinación en código se prueba, se reanuda y se audita como cualquier job.

### Presupuestos, fallas y reintentos por hijo

Con hijos que corren horas, las fallas son lo normal:

- **Tope por hijo** de tokens, tiempo y pasos; al vencer, entrega lo que tenga con estado "parcial".
- **Tope global:** superado, no se lanzan hijos nuevos.
- **Un reintento**, con un encargo distinto (por ejemplo, con el error del primer intento).
- **Cortocircuito:** si los primeros 5 trabajos fallan por la misma causa, se detiene la tanda; el problema probablemente está en el encargo común.
- **Estado fuera de los agentes** (pendiente, en curso, verificado, fallido), para reanudar tras un corte.

**Ejemplo:** 40 servicios con 400.000 tokens cada uno suman 16 millones posibles; con un tope global de 10 millones, el orquestador corta antes.

**Por qué importa:** sin topes por hijo, un servicio con un problema raro consume el presupuesto de toda la noche.

### Verificación y consenso entre hijos

Un hijo que dice "terminé" no terminó hasta que algo independiente lo comprueba. Tres niveles, de menor a mayor costo:

1. **Código:** compila, pasan los tests y los tests de contrato, el diff toca solo archivos permitidos.
2. **Revisor con contexto limpio:** recibe el diff y el criterio de terminado, no la conversación del hijo.
3. **Consenso:** dos o tres hijos sobre el mismo trabajo; se acepta si coinciden o se elige el que pasa más verificaciones.

El consenso solo aporta si los hijos fallan de forma independiente; con el mismo modelo, arnés y encargo, la coincidencia prueba poco.

**Ejemplo:** al migrar un servicio de Rumbo a la nueva versión del cliente de Kafka, el verificador corre los tests de contrato de `pedido_asignado` y `pedido_entregado`; si pasan, el revisor busca cambios de semántica, como un reintento que dejó de ser idempotente.

**Por qué importa:** la verificación es donde más conviene invertir.

### Observabilidad del árbol

Un orquestador produce un árbol de ejecuciones, y se instrumenta como en [OpenTelemetry y tracing](#t/opentelemetry): una traza por job, un span por hijo y spans anidados por paso, con tokens, modelo, rama y resultado de la verificación como atributos.

```arbol
titulo: Migración nocturna de servicios
Job nocturno
- Cola de 40 servicios
-- Estado por servicio
-- Tope global de tokens
- Trabajadores (5 sesiones)
-- Worktree y rama por servicio
-- Tope por servicio
- Verificador
-- Tests y contratos
-- Revisor con contexto limpio
- Agregador
-- PR por servicio aprobado
-- Informe de la noche
```

**Ejemplo:** el informe muestra que 3 de los 7 servicios rechazados fallaron en el mismo test de integración con Aurora. Los spans revelan que usan una librería de migraciones vieja, y eso pasa a una persona en lugar de a tres reintentos.

**Por qué importa:** sin trazas por hijo, el informe dice "33 de 40" y nadie sabe qué hacer con los 7 restantes.

### Cómo encaja con SDD, ODD y la evaluación

- **Evaluación:** sin golden set con puntaje automático y sin trazas guardadas, un optimizador no tiene nada que optimizar.
- **SDD:** en un orquestador, cada trabajo es una tarea con criterios de aceptación, como en [Desarrollo guiado por especificaciones](#t/sdd). Esos criterios son lo que comprueba el verificador; si son vagos, no tiene con qué decidir.
- **ODD:** [ODD](#t/odd) pide proceso proporcional al riesgo; un meta-arnés se justifica para trabajo repetitivo y de volumen, no para lo único o ambiguo.

**Ejemplo:** los criterios de la especificación de la migración de Kafka (tests verdes, contratos sin cambios) son el verificador del orquestador.

**Por qué importa:** un meta-arnés amplifica estas prácticas, también cuando son débiles.

### Cuándo no usar un meta-arnés

- **No hay suite automática:** sin puntaje, el optimizador no tiene señal; sin criterio de terminado, el orquestador no tiene verificador.
- **La métrica de éxito no está clara:** la búsqueda encontrará con eficiencia algo que nadie quería.
- **El volumen es bajo:** optimizar un arnés con 50 consultas por semana o migrar 3 servicios no paga la infraestructura.
- **Equipo chico sin trazas ni topes de costo:** se multiplica lo que no se puede depurar.
- **El problema es de redacción o de datos**, no de arnés.

**Ejemplo:** un asistente con 200 conversaciones por semana y sin golden set necesita primero 100 casos etiquetados, no un optimizador.

**Por qué importa:** antes de la escala vienen la medición y un objetivo claro.

## Casos prácticos

### Optimizar el arnés del clasificador de tickets

**Situación:** el clasificador de tickets acierta 80 % en el golden set y tres semanas de ajustes al prompt no lo movieron. Hay 1.200 tickets etiquetados y un arnés en Python de unas 300 líneas.

**Qué se hace:** se divide en 600 de búsqueda, 300 de validación y 300 de prueba, más un conjunto fuera de distribución con tickets del último mes. El proponente corre en un contenedor sin red, con escritura solo sobre `arnes.py` y `prompts/` y lectura del directorio de corridas. Los objetivos son precisión y tokens. Tras 15 iteraciones (unos 90 dólares hipotéticos), el candidato elegido de la frontera saca 86 % en validación, 85 % en prueba y 84 % fuera de distribución, con 30 % menos tokens. El cambio principal fue elegir ejemplos por similitud y tratar aparte los tickets en portugués. Entra por un PR normal.

### Migración nocturna de 40 servicios

**Situación:** hay que actualizar el cliente de Kafka en 40 servicios en Go. Cada cambio es parecido pero no idéntico; a mano llevaría unas dos semanas.

**Qué se hace:** un job nocturno con una cola de 40 servicios y cinco trabajadores en paralelo, cada uno una sesión del agente de código en su worktree y su rama, con escritura solo sobre ese servicio, sin secretos y con un tope de 400.000 tokens y 45 minutos. El encargo sale de una especificación con criterios de aceptación. El verificador corre tests y contratos y, si pasan, un revisor con contexto limpio lee el diff; hay cortocircuito si los primeros cinco fallan igual. A la mañana: 33 PRs verificados, 4 rechazados por el revisor (dos cambiaban la semántica de reintentos) y 3 fallidos por la misma librería vieja, que pasan a una persona. El job abre PRs; el merge lo decide el equipo.

### El candidato que mejoró tocando el evaluador

**Situación:** en una primera versión del optimizador para el agente de operaciones, un candidato salta de 68 % a 94 % en una iteración. El diff muestra que modificó la función que compara la causa diagnosticada con la esperada para aceptar coincidencias parciales.

**Qué se hace:** se trata como un incidente de diseño. Evaluador, suite y conjuntos reservados pasan a un directorio de solo lectura fuera del sandbox del proponente, se agrega una validación que rechaza diffs fuera de la lista permitida y se revisan las corridas anteriores. Si la métrica es editable, editarla es una estrategia válida para el proponente.

### Decidir no construirlo

**Situación:** alguien propone un optimizador para el asistente del panel de comercios: 200 conversaciones por semana, sin golden set y con quejas variadas.

**Qué se hace:** el equipo lo descarta por ahora: no hay métrica ni suite y el volumen no lo justifica. Arma un golden set de 100 conversaciones, fija la métrica y empieza a guardar trazas completas, el insumo que un meta-arnés necesitaría después.

## Errores comunes

- **Darle al proponente solo puntajes o resúmenes.** Según la ablación del paper, lo que más ayuda son las trazas crudas.
- **Reportar el número de la suite de búsqueda.** Está sesgado por construcción; el resultado es el del conjunto de prueba reservado, usado una sola vez.
- **Dejar el evaluador al alcance del proponente.** Evaluador, suite y conjuntos reservados van en solo lectura, y los diffs se limitan a una lista de archivos.
- **Optimizar solo precisión.** Sin tokens y seguridad como objetivos, la búsqueda los sacrifica; mejor devolver una frontera.
- **Tratar un orquestador como si fueran subagentes.** Las sesiones completas necesitan aislamiento, permisos y topes por hijo; heredar todo del padre multiplica el riesgo.
- **Confiar en el "terminé" de cada hijo.** Todo resultado pasa por un verificador independiente, y el orquestador abre PRs en lugar de integrar.

## Para discutir en equipo

- ¿Qué sistema de Rumbo tiene hoy una suite de evaluación capaz de sostener un meta-arnés optimizador, y cuál sería su conjunto de prueba reservado?
- Si el proponente encuentra un arnés que gana 3 puntos de precisión pero duplica los tokens, ¿quién decide y con qué criterio?
- ¿Qué archivos y decisiones de nuestros arneses deberían quedar fuera del alcance de un proponente automático?
- Para el job de migración, ¿el orquestador debería ser un script determinista o un agente? ¿Qué se gana y qué se pierde en cada caso?
- ¿Guardamos hoy las trazas completas de nuestros agentes? Si mañana quisiéramos optimizar un arnés, ¿qué nos faltaría?
