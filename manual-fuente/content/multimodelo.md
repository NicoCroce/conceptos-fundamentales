---
slug: multimodelo
titulo: Varios modelos y ruteo
resumen: Cómo elegir y rutear varios modelos de lenguaje según la tarea para equilibrar calidad, latencia y costo, y cómo gobernar ese portafolio.
lectura: 15
---

## La idea central

Usar un único modelo para todo es como mandar cada paquete en el camión más grande de la flota: llega, pero un sobre de 100 gramos no necesita un camión. En una plataforma con varias funcionalidades de LLM conviven tareas muy distintas: clasificar un ticket en una de doce categorías, resumir un caso de veinte mensajes, planificar la investigación de una alerta. Cada una tiene otro requisito de calidad, otro presupuesto de latencia y otro volumen. Un solo modelo, por definición, es demasiado caro para algunas y quizás insuficiente para otras.

Trabajar con varios modelos significa tres cosas: tener un **catálogo** de modelos aprobados con criterios claros para elegir entre ellos, **rutear** cada pedido (o cada paso de un agente) al modelo adecuado, y **medir de forma continua** que esa elección sigue siendo buena, porque los modelos, los precios y los proveedores cambian. La idea ya aparece resumida en [Fundamentos de LLMs](#t/fundamentos-llms); acá se desarrolla con las cuentas, las estrategias y los costos ocultos.

## Conceptos

### Por qué un solo modelo es un mal punto de partida

El costo de una tarea es tokens de entrada por precio de entrada más tokens de salida por precio de salida, multiplicado por el volumen. Como el volumen y la forma de cada tarea varían mucho, la tarea más simple puede terminar siendo la más cara.

**Ejemplo (precios hipotéticos, en USD por millón de tokens):**

| Nivel | Entrada | Salida |
|---|---|---|
| Modelo pequeño | 0,20 | 0,80 |
| Modelo mediano | 1,00 | 4,00 |
| Modelo grande | 5,00 | 20,00 |

Tres funcionalidades de Rumbo en un mes:

1. **Clasificación de tickets:** 300.000 tickets, 800 tokens de entrada y 20 de salida cada uno. Son 240 millones de tokens de entrada y 6 millones de salida. Con el modelo grande: 240 × 5 + 6 × 20 = 1.320 USD. Con el pequeño: 240 × 0,20 + 6 × 0,80 = 52,80 USD.
2. **Resumen de casos:** 60.000 resúmenes, 3.000 tokens de entrada y 300 de salida. Son 180 y 18 millones. Grande: 900 + 360 = 1.260 USD. Mediano: 180 + 72 = 252 USD.
3. **Planificación del agente de operaciones:** 2.000 investigaciones de 12 pasos, con 6.000 tokens de entrada y 400 de salida por paso. Son 144 y 9,6 millones. Grande: 720 + 192 = 912 USD.

Todo con el modelo grande: 3.492 USD al mes. Con un modelo por tarea (pequeño, mediano, grande): 52,80 + 252 + 912 = 1.216,80 USD, un 65 % menos. Lo llamativo es que la tarea más simple, clasificar, era la línea más cara con el modelo grande, solo por volumen.

**Por qué importa:** el ahorro no viene de degradar el agente, que sigue con el modelo grande, sino de dejar de gastar en capacidad que la clasificación nunca usó. Siempre que las evals confirmen que el modelo pequeño clasifica bien.

### Criterios para elegir un modelo por tarea

Los criterios que importan, en orden aproximado:

- **Calidad en las evals propias.** Lo único que cuenta es el resultado sobre el golden set de la tarea concreta, como se describe en [Evaluación de LLMs](#t/evaluacion-llms).
- **Latencia: TTFT y tokens por segundo.** El tiempo total es aproximadamente TTFT (tiempo al primer token) más tokens de salida divididos por la velocidad de generación. Qué componente pesa más depende de la salida.
- **Costo por tarea, no por token.** Un modelo con precio por token más bajo puede costar más por tarea si genera más texto o falla la validación y obliga a reintentar.
- **Ventana de contexto.** Si un caso largo necesita 60.000 tokens, un modelo con ventana menor queda descartado o obliga a recortar.
- **Fiabilidad en tool calling y salida estructurada.** En agentes, lo que más falla no es el razonamiento sino el formato: argumentos mal tipados, herramientas inexistentes, JSON inválido. Se mide como una métrica más.
- **Restricciones de datos y región.** Dónde se procesan los datos, si hay retención, si el proveedor está aprobado para datos con PII. Para clientes on-prem, solo sirven modelos que se puedan autoalojar.
- **Licencia, en modelos de pesos abiertos.** Algunas licencias limitan el uso comercial por encima de cierta cantidad de usuarios, prohíben usar las salidas para entrenar otros modelos o exigen atribución. Se revisan con legal antes de adoptarlos.

**Ejemplo de latencia:** una respuesta de 400 tokens. El modelo X tiene TTFT de 0,4 s y genera 50 tokens/s: 0,4 + 400/50 = 8,4 s. El modelo Y tiene TTFT de 1,2 s y genera 150 tokens/s: 1,2 + 400/150 ≈ 3,9 s. Para una clasificación de 5 tokens de salida, en cambio, X tarda 0,5 s e Y 1,23 s. El mismo par de modelos invierte su orden según la tarea.

**Ejemplo de costo por tarea:** el modelo A cuesta 1 USD por millón de tokens y usa 5.000 tokens por intento, pero el 30 % de sus salidas falla la validación y se reintenta: 1,3 intentos × 5.000 = 6.500 tokens, 0,0065 USD por tarea. El modelo B cuesta el doble por token, pero usa 2.500 tokens y solo reintenta el 5 %: 1,05 × 2.500 = 2.625 tokens, 0,00525 USD. B es más barato por tarea.

### Catálogo de modelos por tarea

Con esos criterios, se arma un catálogo que asigna un nivel de modelo a cada tipo de tarea. Un punto de partida razonable, que siempre se confirma con evals:

| Tipo de tarea | Nivel típico | Qué se prioriza |
|---|---|---|
| Clasificar, detectar idioma, extraer campos | Pequeño | Costo y latencia; salida estructurada estable |
| Resumir, redactar borradores, responder con RAG | Mediano | Fidelidad a las fuentes y tono |
| Elegir herramientas y armar argumentos en un agente | Pequeño o mediano | Fiabilidad de tool calling |
| Planificar, diagnosticar, sintetizar evidencia | Grande o de razonamiento | Calidad en varios pasos |
| Juez en evals | Grande, distinto del evaluado | Acuerdo con etiquetas humanas |
| Datos que no pueden salir de la infraestructura del cliente | Pesos abiertos autoalojado | Restricción de datos por encima de la calidad |

### Estrategias de ruteo

El **ruteo** decide qué modelo atiende cada pedido. Hay cuatro familias, de menor a mayor complejidad:

1. **Estático por tarea.** Cada funcionalidad tiene un modelo fijo configurado en el gateway: clasificación, pequeño; resumen, mediano. Es lo más simple y cubre la mayor parte del ahorro.
2. **Por reglas.** Dentro de una funcionalidad, reglas deterministas eligen el modelo: si el caso tiene más de 15 mensajes o el comercio es de cuenta grande, va al modelo mediano; si no, al pequeño.
3. **Router con clasificador o LLM.** Un modelo liviano (un clasificador entrenado o un LLM pequeño) mira la consulta y predice si es simple o compleja.
4. **Cascada.** Todos los pedidos van primero al modelo pequeño. Si su resultado tiene baja confianza o falla una validación, se escala al modelo grande. El modelo pequeño puede ser uno genérico o uno propio, destilado del grande para esa tarea (ver [Adaptar modelos](#t/adaptar-modelos)).

La **confianza** en una cascada puede salir de varias señales: el resultado de una validación (esquema, reglas de negocio, que lo citado exista), la probabilidad de los tokens cuando el proveedor la expone, la coincidencia entre dos respuestas o un puntaje que el propio modelo declara. Este último es el menos confiable: los modelos suelen declarar confianza alta aunque se equivoquen, así que se calibra contra el golden set antes de usarlo.

**La cuenta de la cascada.** El costo esperado por pedido es el costo del pequeño, que se incurre siempre, más la fracción escalada por el costo del grande. Con los precios de arriba, clasificar 1.000 tickets cuesta 0,176 USD con el pequeño y 4,40 USD con el grande. Si se escala el 20 %:

```text
costo cascada = 0,176 + 0,20 × 4,40 = 1,056 USD por 1.000 tickets
ahorro frente a solo grande = 1 - 1,056 / 4,40 = 76 %
```

La cascada deja de convenir cuando la fracción escalada se acerca a 1 − costo_pequeño / costo_grande, acá un 96 %. En la práctica el límite real es otro: la latencia. Los casos escalados suman las dos llamadas. Con 0,3 s el pequeño y 1,5 s el grande, la media baja a 0,3 + 0,2 × 1,5 = 0,6 s, pero el p95 sube a 1,8 s, porque ese percentil cae justo en los escalados.

| Estrategia | Cómo decide | Ventaja | Limitación | Cuándo usarla |
|---|---|---|---|---|
| Estático por tarea | Configuración por funcionalidad | Simple, predecible, fácil de evaluar | No distingue casos fáciles de difíciles dentro de la misma tarea | Siempre, como base |
| Por reglas | Atributos conocidos del pedido | Auditable y sin costo extra | Frágil; no ve la dificultad real del texto | Cuando hay atributos que correlacionan con la dificultad |
| Router clasificador o LLM | Predicción previa de dificultad | Captura matices; una sola llamada principal | Componente extra que se equivoca y hay que evaluar | Alto volumen con dificultad muy variable |
| Cascada | Intento con el pequeño y escalado | No necesita predecir; usa validación real | Latencia doble en escalados; riesgo de errores con confianza alta | Tareas con salida verificable (clasificar, extraer) |

### Un modelo distinto por paso dentro de un agente

En un [agente](#t/agentes), el ruteo no se hace solo por funcionalidad sino por **paso**. La mayoría de los pasos son mecánicos: elegir la herramienta siguiente, armar sus argumentos, extraer un dato del resultado. Unos pocos requieren juicio: planificar la investigación y redactar el diagnóstico final.

**Ejemplo (precios hipotéticos de la tabla):** una investigación del agente de operaciones tiene 12 pasos de 6.000 tokens de entrada y 400 de salida.

- **Todo con el grande:** entrada 72.000 × 5 / 1.000.000 = 0,36 USD; salida 4.800 × 20 / 1.000.000 = 0,096 USD. Total 0,456 USD.
- **10 pasos mecánicos con el pequeño y 2 con el grande:** pequeño 60.000 × 0,20 / 1.000.000 + 4.000 × 0,80 / 1.000.000 = 0,0152 USD; grande 12.000 × 5 / 1.000.000 + 800 × 20 / 1.000.000 = 0,076 USD. Total 0,0912 USD, un 80 % menos.

La latencia también baja: si un paso del grande tarda 3 s y uno del pequeño 0,8 s, la investigación pasa de 36 s a 10 × 0,8 + 2 × 3 = 14 s.

**Por qué importa:** el riesgo está en que un modelo pequeño que elige mal la herramienta agrega pasos, y cada paso extra se come el ahorro. Por eso este diseño se valida con evaluación de trayectoria (cantidad de pasos, herramientas correctas), no solo con la respuesta final.

### Modelos de razonamiento

Un **modelo de razonamiento** genera, antes de la respuesta, una cadena interna de pasos intermedios. Intercambia latencia y tokens por mejores resultados en problemas de varios pasos: diagnósticos con evidencia contradictoria, planes con dependencias, cálculos encadenados. En muchos proveedores esos tokens de razonamiento se cuentan como salida, aunque no se vean.

El **presupuesto de razonamiento** es un parámetro que limita cuántos tokens puede usar el modelo para pensar, expresado como un número de tokens o como niveles de esfuerzo según el proveedor. Fijarlo evita que una consulta simple consuma miles de tokens.

**Ejemplo (hipotético):** el diagnóstico final del agente de operaciones con el modelo grande genera 400 tokens de salida, cuesta 0,008 USD y tarda 4 s. Con un modelo de razonamiento genera 4.000 tokens de razonamiento más 400 de respuesta: 0,088 USD y 25 s. En el golden set de diagnósticos, la tasa de acierto sube del 70 % al 85 %. Cada diagnóstico errado le cuesta a una persona de guardia unos 20 minutos de investigación adicional. Gastar 8 centavos más y esperar 20 segundos para evitar 15 errores cada 100 diagnósticos conviene con holgura. Para clasificar tickets, en cambio, la misma cuenta no cierra: la tarea no tiene varios pasos y la latencia importa.

**Cuándo vale la pena:** cuando la tarea tiene varios pasos dependientes, el error es caro, el volumen es bajo y la latencia tolera decenas de segundos. Casi nunca en tareas de alto volumen con respuesta corta.

### Fallback entre proveedores y su costo oculto

El fallback a otro proveedor, descrito en [LLMs en producción](#t/llms-produccion), parece cambiar una URL. En la práctica, otro modelo es otra dependencia con su propio comportamiento:

- **Los prompts no se transfieren tal cual.** Un prompt ajustado durante meses para un modelo puede perder varios puntos en otro. Cada funcionalidad necesita una variante de prompt por modelo, versionada y evaluada.
- **Formatos de tool calling distintos.** Cada proveedor define herramientas, llamadas y resultados con su propia estructura. Los argumentos pueden llegar como objeto o como texto JSON, y el soporte de llamadas paralelas varía.
- **Salida estructurada desigual.** Algunos modelos garantizan el esquema; otros lo siguen "casi siempre" y a veces envuelven el JSON en texto.
- **Tokenizadores distintos.** El mismo texto ocupa otra cantidad de tokens, lo que cambia costos y límites de contexto.

Una **capa de abstracción** (normalmente dentro del gateway) define un formato interno único para mensajes, herramientas y salidas, con un adaptador por proveedor. Reduce el trabajo de cada equipo, pero tiene un riesgo: si el formato interno se limita a lo que todos los proveedores soportan, se pierden capacidades propias de cada uno. Lo habitual es un núcleo común más extensiones explícitas por proveedor.

### Comparar modelos de forma continua

Las comparaciones no se hacen una vez al elegir modelo; se sostienen en el tiempo:

- **Matriz de evals por modelo.** Cada funcionalidad corre su golden set contra el modelo principal, el de fallback y los candidatos. El resultado es una tabla tarea × modelo con calidad, latencia y costo por tarea.
- **Tráfico sombra.** El candidato procesa tráfico real en paralelo sin mostrar resultados; se comparan salidas, latencia y costo reales.
- **A/B.** Una fracción del tráfico usa el candidato y se comparan métricas de negocio.
- **Fijar versiones.** Los proveedores suelen exponer un alias genérico que apunta a "la versión vigente" y versiones con identificador fijo. En producción se usa la versión fija: si el alias se mueve, el comportamiento cambia sin que nadie haya desplegado nada.
- **Eval diaria de regresión.** Aun con versión fija, conviene correr cada día un subconjunto del golden set y alertar si cae. Detecta actualizaciones silenciosas, cambios de infraestructura del proveedor o variaciones que nadie anunció.

### Gobierno del portafolio de modelos

Sin gobierno aparecen modelos que nadie sabe quién usa ni por qué. El mínimo incluye:

- **Lista de modelos aprobados**, con proveedor, versión fija, clasificación de datos permitida (con o sin PII), regiones y tareas para las que pasó evals.
- **Dueño por modelo y por funcionalidad:** quién decide migraciones, quién recibe las alertas de regresión.
- **Calendario de deprecación:** los proveedores retiran versiones con unos meses de aviso. Cada fecha se registra con la funcionalidad afectada y un plan de migración que incluye evals del reemplazo con tiempo, no la semana anterior.
- **Proceso de alta:** un modelo nuevo entra al catálogo solo con evals en al menos una tarea, revisión de datos y licencia, y su adaptador en el gateway.

## Casos prácticos

### Cascada para clasificar tickets

**Situación:** el clasificador de tickets usa el modelo grande para 300.000 tickets al mes, con una exactitud del 96 % en el golden set. Es la línea de costo de LLM más alta de soporte.

**Qué se hace:** se prueba una cascada. El modelo pequeño clasifica todo y devuelve categoría y una señal de confianza; se escala si la confianza queda bajo un umbral, si la categoría es "reclamo urgente" o si la salida falla el esquema. Se mide sobre el golden set con dos umbrales:

- Umbral 0,70: escala el 12 %, exactitud 93,5 %. Costo por 1.000 tickets: 0,176 + 0,12 × 4,40 = 0,704 USD, un 84 % menos.
- Umbral 0,85: escala el 22 %, exactitud 95,8 %. Costo: 0,176 + 0,22 × 4,40 = 1,144 USD, un 74 % menos.

Se elige 0,85: casi la misma exactitud que el modelo grande solo, con el recall de "reclamo urgente" intacto porque esa categoría siempre escala. El costo mensual pasa de 1.320 a unos 343 USD. Se agrega una alerta si la tasa de escalado se aleja del 22 %: indica que cambiaron los tickets o el modelo.

### Agente de operaciones con dos modelos

**Situación:** el agente de operaciones investiga alertas como "cayó la tasa de entregas a tiempo en la zona norte". Todo corre con el modelo grande, cada investigación tarda cerca de 40 segundos y el equipo de guardia quiere usarlo más seguido.

**Qué se hace:** se separan los pasos. El modelo pequeño elige herramientas de solo lectura, arma argumentos (zona, ventana de tiempo) y extrae números de los resultados. El modelo grande arma el plan inicial y escribe el diagnóstico final. En la evaluación de trayectoria, la primera versión empeora: el pequeño confunde dos herramientas de métricas parecidas y el promedio de pasos sube de 11 a 15. Se mejoran las descripciones de esas herramientas y se agregan dos ejemplos; los pasos vuelven a 11, la tasa de diagnósticos correctos queda igual y el costo por investigación baja cerca de un 80 %.

### Caída del proveedor y salida estructurada rota

**Situación:** el proveedor principal cae una tarde. El gateway pasa al fallback y, en minutos, el 18 % de las extracciones de notas de comercios ("dejar en portería", "llamar antes") falla la validación. El modelo de fallback devuelve el JSON envuelto en texto, usa "Portería" en lugar del valor permitido `porteria` y, en el agente, entrega los argumentos de herramientas como texto en vez de objeto.

**Qué se hace:** de inmediato, el adaptador del gateway normaliza lo recuperable (extraer el JSON del texto, mapear valores equivalentes) y lo que sigue fallando va a una cola para reprocesar cuando vuelva el principal. Después del incidente se corrige la causa: el prompt de fallback era copia del principal y nunca se había evaluado. Se crea una variante de prompt específica para ese modelo, se usa salida estructurada con esquema donde el proveedor la soporta, se agregan las evals del fallback a CI y se programa un simulacro mensual que fuerza tráfico al fallback durante 15 minutos.

### Una actualización del proveedor baja las evals

**Situación:** el clasificador apuntaba al alias genérico del modelo pequeño. Un lunes, la eval diaria muestra que el recall de "reclamo urgente" cayó de 90 % a 83 %, sin ningún despliegue propio. El proveedor había movido el alias a una versión nueva.

**Qué se hace:** se fija la versión anterior por identificador y el recall vuelve al 90 % en la siguiente corrida. Luego se evalúa la versión nueva por separado: con un ajuste en el prompt recupera el 89 %, y además es un 15 % más barata. Se migra con sombra y canary, y se cambia la regla del catálogo: en producción solo se permiten versiones fijas, y los alias quedan para experimentos.

## Errores comunes

- **Elegir modelo por un ranking público.** Los benchmarks generales no miden tickets de Rumbo; la decisión sale del golden set propio, con calidad, latencia y costo por tarea.
- **Comparar precio por token en vez de costo por tarea.** Un modelo barato que genera el doble de texto o falla la validación seguido termina costando más; se mide el costo completo de resolver la tarea.
- **Escalar en la cascada según la confianza que declara el modelo, sin calibrar.** Los modelos se equivocan con confianza alta; se combinan validaciones objetivas y se calibra el umbral sobre el golden set.
- **Tener un fallback que nunca recibió tráfico.** Si el prompt de fallback no está evaluado ni se ejercita con simulacros, la primera prueba real es el incidente.
- **Apuntar producción a alias que se mueven.** El comportamiento cambia sin despliegue; se fijan versiones y se migra de forma deliberada.
- **Usar modelos de razonamiento en tareas de alto volumen.** Multiplican tokens y latencia sin mejorar tareas de un solo paso; se reservan para problemas de varios pasos donde el error es caro.

## Para discutir en equipo

- ¿Qué funcionalidad nuestra usa hoy un modelo más grande del necesario, y cuánto costaría comprobarlo con evals?
- Si el proveedor principal desaparece mañana, ¿cuántas variantes de prompt y adaptadores habría que tener listos, y quién es responsable de mantenerlos?
- ¿Qué señal de confianza usaríamos para escalar en una cascada del asistente de soporte, donde la salida es texto libre y no se puede validar con un esquema?
- ¿Qué pasos de nuestros agentes requieren de verdad un modelo grande o de razonamiento, y cuáles son mecánicos?
- ¿Quién debería aprobar el alta de un modelo nuevo al catálogo, y qué evidencia mínima debería presentar?
