---
slug: investigacion-usabilidad
titulo: Investigación de usuarios y pruebas de usabilidad
resumen: Cómo aprender de los usuarios con entrevistas, pruebas de usabilidad, métricas como SUS y tests A/B, y cómo usar LLMs en la síntesis sin inventar evidencia.
lectura: 17
---

## La idea central

Todo equipo de producto tiene opiniones sobre sus usuarios. La investigación es la disciplina de reemplazar esas opiniones por evidencia, con el menor costo posible. No hace falta un laboratorio: cinco conversaciones bien hechas con transportistas de Rumbo enseñan más sobre la app que una semana de debate interno, y un test A/B bien dimensionado cierra discusiones que de otra forma se repiten cada trimestre.

Hay dos grandes preguntas. La **generativa**: ¿qué problema tiene la gente y cómo lo resuelve hoy? La **evaluativa**: ¿lo que diseñamos funciona? Para cada una hay métodos **cualitativos**, que explican el porqué con pocas personas, y **cuantitativos**, que miden cuánto con muchas. El error clásico es usar el método equivocado para la pregunta: preguntar en una encuesta por qué la gente abandona un flujo, o intentar medir una tasa de éxito con tres entrevistas. Los LLMs agregan una herramienta potente para sintetizar y un riesgo nuevo: un resumen convincente de cosas que nadie dijo.

## Conceptos

### Generativa y evaluativa, cualitativa y cuantitativa

Cruzar las dos dimensiones da un mapa de métodos:

| | Cualitativa (por qué, cómo) | Cuantitativa (cuánto, cuántos) |
|---|---|---|
| **Generativa** (qué problema hay) | Entrevistas, observación en contexto, estudios de diario | Encuestas de comportamiento, análisis de tickets y logs |
| **Evaluativa** (funciona lo diseñado) | Pruebas de usabilidad moderadas, evaluación heurística | Tests A/B, pruebas no moderadas con métricas, analíticas de embudo |

La investigación generativa conviene al principio, en la fase de descubrir del doble diamante (ver [UX y UI: fundamentos](#t/ux-ui-fundamentos)). La evaluativa acompaña el desarrollo y el lanzamiento.

**Ejemplo:** para la app de transportistas, el equipo acompaña a 4 transportistas durante media jornada cada uno (generativa, cualitativa) y descubre que confirman entregas con el pulgar mientras sostienen el paquete con la otra mano. Después mide en las analíticas que el 22 % de las confirmaciones tarda más de 30 segundos (cuantitativa). Con ambas cosas se rediseña la pantalla de confirmación y se valida con pruebas de usabilidad (evaluativa).

**Por qué importa:** elegir el método por la pregunta, y no por costumbre, evita estudios caros que no responden lo que se necesitaba saber.

### Entrevistas: preguntas buenas y preguntas que inducen

Una entrevista de investigación busca entender comportamientos pasados y contexto, no recoger opiniones sobre ideas futuras. La gente predice mal lo que hará y cuenta bien lo que hizo. Algunas reglas:

1. Preguntar por hechos concretos y recientes: «Cuéntame la última vez que…».
2. Preguntas abiertas, que no se respondan con sí o no.
3. No mencionar la solución que el equipo tiene en mente.
4. Tolerar el silencio: después de una respuesta, esperar unos segundos suele traer lo más interesante.
5. Preguntar «¿por qué?» con cuidado, en formas como «¿qué te llevó a…?».

| Pregunta que induce | Mejor alternativa |
|---|---|
| ¿Te resultaría útil poder reprogramar desde el mensaje? | Cuéntame la última vez que no ibas a estar para recibir un pedido. ¿Qué hiciste? |
| ¿No te parece confusa la pantalla de confirmación? | Muéstrame cómo confirmaste la última entrega. ¿Qué pasó después? |

**Ejemplo:** a la pregunta «¿Te resultaría útil reprogramar desde el mensaje?», 9 de 10 destinatarios dicen que sí. Con la pregunta abierta sobre la última vez, aparece que 6 de 10 ni siquiera abrieron el mensaje: lo vieron como notificación y lo descartaron. El dato útil vino de la segunda pregunta.

**Por qué importa:** las preguntas que inducen producen confirmaciones baratas que después no se sostienen en el uso real.

### Pruebas de usabilidad: tareas y pensar en voz alta

En una **prueba de usabilidad** una persona intenta hacer tareas reales con el producto o un prototipo, y el equipo observa dónde se traba. Hay dos modalidades:

- **Moderada:** una persona facilita en vivo (presencial o por videollamada), puede repreguntar y profundizar. Más rica, más cara, pocas sesiones.
- **No moderada:** el participante hace las tareas solo, guiado por una herramienta que graba pantalla y voz. Más barata y rápida, buena para muchas sesiones, pero sin posibilidad de repreguntar.

Una buena tarea describe un objetivo con contexto, sin nombrar los botones: «Tu pedido llega mañana y no vas a estar. Haz lo necesario para recibirlo otro día», y no «Toca Reprogramar».

Durante la prueba se pide **pensar en voz alta** (think-aloud): el participante narra lo que busca, lo que espera y lo que lo sorprende. La regla de quien facilita es no ayudar; si el participante pregunta «¿aprieto acá?», se devuelve: «¿Qué esperarías que pase?».

**Ejemplo:** en 5 sesiones moderadas del panel de comercios, 4 operadoras buscan la reprogramación en bloque en el menú de la fila y no en la barra superior donde estaba. Una dice en voz alta «esto lo haría con el botón derecho, como en la planilla». Esa frase lleva a agregar la acción al menú contextual.

**Por qué importa:** ver a una sola persona fracasar con una tarea que el equipo creía obvia cambia más prioridades que cualquier informe.

### Por qué cinco usuarios encuentran la mayoría de los problemas

Nielsen y Landauer (1993) modelaron cuántos problemas de usabilidad aparecen según la cantidad de participantes. Si cada participante encuentra en promedio una proporción *L* de los problemas, la fracción encontrada con *n* participantes es:

```text
encontrados(n) = 1 - (1 - L)^n
```

En los proyectos que analizaron, *L* promedió 0,31. El cálculo paso a paso:

- Con 1 usuario: 1 − 0,69 = 31 %.
- Con 2: 1 − 0,69² = 1 − 0,476 = 52 %.
- Con 5: 1 − 0,69⁵ = 1 − 0,156 = 84 %.
- Con 10: 1 − 0,69¹⁰ = 1 − 0,024 = 98 %.

```barras
titulo: Problemas encontrados según participantes (L = 0,31)
unidad: %
1 participante | 31
2 participantes | 52
3 participantes | 67
4 participantes | 77
5 participantes | 84
10 participantes | 98
15 participantes | 99,6
```

La curva aplana rápido: del participante 6 al 15 se agregan pocos hallazgos nuevos. Por eso la recomendación de Nielsen no es «basta con 5», sino «es mejor hacer tres rondas de 5 que una de 15»: probar, corregir y volver a probar encuentra problemas que estaban tapados por los primeros.

Los supuestos importan: *L* varía según producto y tarea; si hay grupos muy distintos (destinatarios, transportistas, operadoras) se necesitan de 3 a 5 por grupo; y el modelo sirve para encontrar problemas, no para medir tasas.

**Ejemplo:** el equipo prueba la nueva confirmación de entrega con 5 transportistas, corrige los 6 problemas encontrados y prueba con otros 5. En la segunda ronda aparecen 3 problemas nuevos que antes no se veían porque los participantes se trababan antes de llegar a esa pantalla.

**Por qué importa:** la investigación cualitativa iterativa es barata. La excusa «no tenemos presupuesto para un estudio grande» casi nunca aplica.

### Métricas de usabilidad: éxito, tiempo y errores

Cuando la pregunta es «cuánto», se miden tres cosas por tarea:

- **Tasa de éxito:** proporción de participantes que completa la tarea. Puede ser binaria o con éxito parcial.
- **Tiempo en la tarea:** cuánto tardan quienes la completan. Conviene reportar la mediana o la media geométrica, porque unos pocos participantes muy lentos distorsionan el promedio.
- **Tasa de errores:** errores por intento (tocar la opción equivocada, ingresar un dato inválido).

**Ejemplo:** en una prueba no moderada con 40 operadoras, la reprogramación en bloque tiene 31 éxitos (78 %), una mediana de 95 segundos y 1,4 errores por intento. Con el rediseño: 37 éxitos (93 %), 52 segundos y 0,3 errores. Con 40 por versión, la tasa de éxito todavía tiene un margen amplio (unos ±12 puntos).

**Por qué importa:** una línea base numérica permite saber si un rediseño mejoró o solo cambió.

### SUS: cómo se calcula el puntaje

El **System Usability Scale** (SUS), creado por John Brooke en 1986, es un cuestionario de 10 afirmaciones respondidas de 1 (muy en desacuerdo) a 5 (muy de acuerdo). Las impares son positivas («Creo que usaría este sistema con frecuencia», «El sistema me resultó fácil de usar») y las pares negativas («El sistema me pareció innecesariamente complejo», «Necesité aprender muchas cosas antes de poder usarlo»).

El cálculo, paso a paso:

1. Para cada ítem **impar**: puntaje = respuesta − 1.
2. Para cada ítem **par**: puntaje = 5 − respuesta.
3. Sumar los 10 puntajes (queda entre 0 y 40).
4. Multiplicar por 2,5 (queda entre 0 y 100).

Un participante responde: 4, 2, 5, 1, 4, 2, 5, 2, 4, 3.

- Impares (1, 3, 5, 7, 9): (4−1) + (5−1) + (4−1) + (5−1) + (4−1) = 3 + 4 + 3 + 4 + 3 = 17.
- Pares (2, 4, 6, 8, 10): (5−2) + (5−1) + (5−2) + (5−2) + (5−3) = 3 + 4 + 3 + 3 + 2 = 15.
- Suma: 32. Por 2,5: **80**.

El puntaje de un estudio es el promedio de los participantes. Un SUS de 80 **no es un 80 %**: no es un porcentaje. En las bases de referencia publicadas (Sauro y Lewis) el promedio ronda 68, así que 80 está claramente por encima de la media y 55 claramente por debajo.

**Ejemplo:** el panel de comercios obtiene 61 con 25 operadoras. Tras el rediseño de la navegación, 74. La métrica no dice qué mejoró; eso lo dicen las sesiones, pero confirma la dirección.

**Por qué importa:** SUS es corto, gratuito, comparable entre versiones y productos, y funciona razonablemente bien incluso con muestras chicas.

### NPS y CSAT, con sus límites

El **NPS** (Net Promoter Score) pregunta «¿Qué tan probable es que recomiendes…?» de 0 a 10. Promotores: 9 y 10. Detractores: 0 a 6. NPS = % de promotores − % de detractores, entre −100 y 100. Con 45 promotores, 30 neutros y 25 detractores sobre 100, el NPS es 20.

Las críticas son serias y conviene conocerlas:

- Mide intención declarada, no comportamiento, y no dice qué arreglar.
- Pierde información: 50 promotores y 50 detractores dan NPS 0, igual que 100 neutros.
- Varía mucho con muestras chicas, porque resta dos proporciones.
- En logística, el destinatario a menudo no eligió a Rumbo: lo eligió el comercio. «¿Recomendarías Rumbo?» es una pregunta rara para Lucía.

El **CSAT** (customer satisfaction) pregunta por la satisfacción con una interacción concreta («¿Qué tan satisfecho quedaste con esta entrega?», de 1 a 5) y se reporta como el porcentaje de respuestas 4 o 5. Es más accionable porque está atado a un momento.

**Ejemplo:** el asistente de soporte pide un CSAT al cerrar cada conversación. Con 3.000 respuestas al mes, el 72 % es 4 o 5. Al cruzarlo con la categoría de consulta, las de reprogramación dan 85 % y las de pedidos perdidos 41 %: eso sí indica dónde trabajar.

**Por qué importa:** una métrica de satisfacción sin contexto ni desglose se vuelve un número para la presentación trimestral y no una herramienta de decisión.

### Tests A/B y tamaño de muestra

Un **test A/B** reparte usuarios al azar entre dos versiones y compara una métrica. Es la forma más confiable de saber si un cambio causa una diferencia, pero necesita muestras grandes.

La intuición: cuanto más chica la diferencia que se quiere detectar, más usuarios se necesitan, y la relación es cuadrática. Una regla aproximada (para 80 % de potencia y 5 % de significancia, dos colas) es:

```text
n por variante ≈ 16 · p · (1 − p) / δ²
```

donde *p* es la tasa base y *δ* la diferencia absoluta que se quiere detectar.

**Ejemplo:** hoy el 20 % de los destinatarios que abren el enlace termina reprogramando. Para detectar una mejora a 22 % (δ = 0,02): 16 · 0,2 · 0,8 / 0,0004 = **6.400 por variante**, 12.800 en total. Para detectar 21 % (δ = 0,01): 25.600 por variante, cuatro veces más. Si el enlace lo abren unas 1.500 personas por día, el primer test necesita unos 9 días y el segundo más de un mes.

Otras reglas: fijar métrica y tamaño antes de empezar; no cortar cuando un resultado parcial «da significativo» (infla los falsos positivos); correr semanas completas; y vigilar una métrica de protección, como los tickets de soporte.

**Por qué importa:** un test A/B corto y chico da resultados que parecen evidencia y son ruido. Con poco tráfico, las pruebas cualitativas suelen ser mejor inversión.

### Triangular analíticas y evidencia cualitativa

Las **analíticas** dicen qué pasa y dónde, pero no por qué. Las sesiones dicen por qué, pero no cuánto. **Triangular** es combinar fuentes para que se confirmen o se contradigan: las analíticas señalan dónde mirar, las sesiones explican el comportamiento, los tickets y las conversaciones del asistente aportan el lenguaje real, y un cambio medido cierra el ciclo.

**Ejemplo:** el embudo muestra un abandono del 35 % en «elegir horario». En 5 sesiones, 3 personas no ven que hay más días desplazando el selector hacia la derecha. En las conversaciones del asistente aparecen 200 consultas al mes del tipo «solo me deja elegir hasta el viernes». Las tres fuentes apuntan a lo mismo.

**Por qué importa:** una sola fuente engaña con facilidad. Cuando dos fuentes independientes coinciden, la decisión es mucho más segura.

### Síntesis y repositorios de investigación

Después de las sesiones queda una pila de notas, grabaciones y citas. **Sintetizar** es convertirla en hallazgos accionables. La técnica más usada es el **mapa de afinidad**: cada observación va en una nota adhesiva, se agrupan por similitud y se nombra cada grupo con un hallazgo (ver el diagrama de afinidad en [Brainstorming y mapas mentales](#t/brainstorming-mapas-mentales)).

Un buen hallazgo tiene tres partes: la observación, la evidencia (cuántos participantes, citas) y la implicancia. «4 de 5 transportistas confirman la entrega con una sola mano; los botones en la parte superior obligan a soltar el paquete» es un hallazgo. «Los usuarios quieren algo más simple» no lo es.

Un **repositorio de investigación** guarda los hallazgos con sus fuentes, etiquetados por tema, producto y fecha, para que el próximo equipo no repita el mismo estudio. Las grabaciones y transcripciones llevan datos personales: requieren consentimiento, acceso restringido y plazo de retención.

**Ejemplo:** antes de investigar la app de transportistas, una diseñadora busca «una mano» en el repositorio y encuentra un estudio de hace un año con el mismo hallazgo. En lugar de repetirlo, el equipo valida el rediseño directamente.

**Por qué importa:** la investigación que no se puede encontrar se pierde, y la organización vuelve a gastar tiempo en aprender lo mismo.

### LLMs para sintetizar: usos y riesgos

Los LLMs son muy útiles para la parte mecánica de la síntesis: transcribir, resumir sesiones, proponer agrupaciones iniciales, buscar en el repositorio por significado, etiquetar cientos de tickets. Los riesgos son concretos:

1. **Citas inventadas o retocadas.** El modelo puede producir una cita verosímil que nadie dijo, o mejorar la redacción de una real. Regla: toda cita en un informe se verifica contra la transcripción, con marca de tiempo.
2. **Sesgo hacia lo frecuente y lo complaciente.** Los resúmenes tienden a suavizar quejas y a omitir lo dicho por una sola persona, que a veces es lo más importante.
3. **Confirmación.** Si el prompt dice «resume las ventajas del nuevo flujo», el modelo las encontrará.
4. **Privacidad.** Las transcripciones tienen nombres, teléfonos y direcciones. Enviarlas a un proveedor externo exige acuerdos, redacción previa de datos personales y retención controlada (ver [Privacidad y datos personales](#t/privacidad-datos)).
5. **Pérdida de inmersión.** Quien solo lee el resumen generado no desarrolla el criterio que da ver sesiones.

**Ejemplo:** un resumen generado de 12 entrevistas dice «varios transportistas pidieron modo oscuro». Al pedirle las citas con marca de tiempo, aparece una sola mención, y era sobre el brillo de la pantalla al sol. El hallazgo real era de contraste, no de tema.

**Por qué importa:** la síntesis es donde la investigación se vuelve decisión. Un error ahí se propaga a todo lo que viene después con apariencia de evidencia.

### Investigar una experiencia con agentes: Mago de Oz

Antes de construir un agente conviene saber si la experiencia tiene sentido. El **test del Mago de Oz** (Wizard of Oz) simula el sistema con una persona detrás: el participante cree que habla con el asistente, pero quien responde es un miembro del equipo siguiendo un guion y unas reglas (qué puede hacer el «agente», qué no, cuánto tarda).

Sirve para descubrir cómo pide la gente las cosas, qué espera que el agente pueda hacer y cuánta confirmación quiere antes de una acción. Con un prototipo real se agregan otras preguntas: si entiende qué hizo el agente, si confía de más o de menos y si sabe deshacer. Las métricas de calidad de las respuestas se complementan con la [evaluación de LLMs](#t/evaluacion-llms), y los patrones de interfaz están en [UX para agentes](#t/ux-agentes).

**Ejemplo:** en un Mago de Oz con 8 operadoras de comercios, el «agente» puede reprogramar envíos. Seis de ocho escriben pedidos ambiguos («pasa los de hoy de zona norte a mañana») y esperan que el agente pregunte cuántos son antes de actuar. Dos se sorprenden porque no esperaban que pudiera ejecutar cambios. Se decide que toda acción en bloque muestre el número exacto y pida aprobación.

**Por qué importa:** simular un agente cuesta días; construir uno y descubrir que la gente lo usa distinto cuesta meses.

## Casos prácticos

### El test A/B que se cortó a los tres días

**Situación:** un test del nuevo texto del enlace muestra al tercer día 24 % contra 20 % de reprogramaciones, «significativo». El equipo quiere cerrarlo y publicar.

**Qué se hace:** se recalcula el tamaño necesario: para detectar 2 puntos hacían falta 6.400 por variante y había 1.900. Se deja correr dos semanas completas, como estaba planeado. El resultado final es 21,1 % contra 20,0 %, una mejora pequeña dentro del ruido. El texto nuevo se publica igual por claridad, pero sin atribuirle un impacto que no se demostró.

### Cinco sesiones antes de un trimestre de desarrollo

**Situación:** producto propone un rediseño completo de la app de transportistas, con un trimestre de trabajo estimado, basado en la intuición de que «la app es lenta de usar».

**Qué se hace:** se hacen 5 sesiones moderadas en la calle, acompañando a transportistas. Los hallazgos son tres problemas concretos (botón de confirmar lejos del pulgar, foto de comprobante que exige tres toques, mapa que se recentra solo). Se corrigen en tres semanas, se mide de nuevo y la mediana de tiempo por parada baja 18 segundos. El rediseño completo se posterga.

### Un informe con citas que no existían

**Situación:** un informe generado por un LLM sobre 20 entrevistas con comercios incluye la cita «el asistente nos ahorra una hora por día», que circula en una presentación de liderazgo.

**Qué se hace:** al buscar la cita en las transcripciones no aparece; la más cercana dice «a veces me ahorra tiempo, cuando acierta». Se corrige la presentación y se cambia el proceso: las citas se extraen con referencia a transcripción y minuto, una persona las verifica antes de publicar, y los informes generados llevan la marca «borrador sin verificar» hasta entonces.

## Errores comunes

- **Preguntar por el futuro.** «¿Usarías…?» produce síes que no se cumplen. Pregunta por la última vez que la persona enfrentó el problema.
- **Ayudar durante la prueba.** Cada pista invalida la tarea. Quien facilita devuelve las preguntas y anota dónde la persona se trabó.
- **Cinco usuarios para medir.** Cinco sirven para encontrar problemas, no para afirmar una tasa. Para medir se necesitan decenas, con su intervalo de confianza.
- **Leer SUS como porcentaje.** 70 no es «70 % de usabilidad»; se compara con la referencia de 68 y con versiones anteriores.
- **Cortar un A/B cuando conviene.** Fija el tamaño de muestra antes y respeta la duración, aunque el resultado parcial guste.
- **Publicar síntesis generada sin verificar.** Toda cita y todo conteo de un resumen hecho con un LLM se contrasta con las transcripciones antes de usarse para decidir.

## Para discutir en equipo

- ¿Cuándo fue la última vez que alguien de ingeniería vio en vivo una sesión con un usuario de Rumbo? ¿Cómo lo hacemos habitual?
- ¿Qué decisiones tomamos hoy con NPS que deberíamos tomar con CSAT por interacción o con métricas de tarea?
- ¿Tenemos el tráfico para los tests A/B que proponemos, o deberíamos usar más pruebas cualitativas?
- ¿Qué reglas necesitamos para usar LLMs con transcripciones de entrevistas: proveedor, redacción de datos personales, verificación de citas?
- ¿Qué parte de la experiencia del asistente podríamos validar con un Mago de Oz antes de construirla?
