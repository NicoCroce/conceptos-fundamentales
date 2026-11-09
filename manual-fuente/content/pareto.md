---
slug: pareto
titulo: Principio de Pareto (80/20)
resumen: Un patrón empírico según el cual pocas causas explican la mayor parte de un efecto, y cómo usarlo para decidir dónde poner el esfuerzo.
lectura: 11
---

## La idea central

El **principio de Pareto** dice que, en muchos fenómenos, una minoría de causas explica la mayor parte del efecto: alrededor del 20% de las causas produce alrededor del 80% de los resultados. Toma el nombre del economista Vilfredo Pareto, que a fines del siglo XIX observó que una pequeña parte de la población concentraba la mayor parte de la tierra en Italia; décadas después, la idea se generalizó en el control de calidad industrial.

Para un equipo de ingeniería, la utilidad es práctica: antes de atacar un problema grande (entregas fallidas, latencia, costo de la nube, gasto en tokens), conviene medir cómo se reparte. Si el reparto está concentrado, arreglar dos o tres causas resuelve casi todo. Si no lo está, ningún arreglo puntual va a mover mucho la aguja y hace falta otra estrategia. El análisis de Pareto es la forma ordenada de averiguar en cuál de los dos mundos estamos.

## Conceptos

### Un patrón empírico, no una ley

El 80/20 no es una constante de la naturaleza. Es una observación que se repite en muchos dominios porque los fenómenos que crecen por acumulación (unos pocos clientes muy grandes, unos pocos endpoints muy usados, unos pocos bugs en módulos frágiles) tienden a producir distribuciones desiguales. Pero el reparto concreto cambia: puede ser 70/30, 90/10 o 95/5. Tampoco los números tienen que sumar 100: "el 10% de los tenants consume el 60% de los tokens" es una afirmación perfectamente válida.

Hay casos donde el patrón directamente no aparece. Si los errores de un servicio se reparten parejo entre 15 causas, cada una con un 6% o 7%, no hay "pocos vitales" que atacar, y el análisis lo dice con claridad.

**Ejemplo:** el equipo del asistente de soporte revisa 1.000 respuestas marcadas como incorrectas. Encuentra que 3 de 25 tipos de pregunta (12%) explican el 71% de los errores. No es 80/20, pero la concentración es fuerte y alcanza para decidir dónde empezar.

**Por qué importa:** si se asume el 80/20 sin medir, se termina forzando los datos para que lo confirmen. El principio sirve como hipótesis que se verifica, no como conclusión.

### Cómo armar un análisis de Pareto paso a paso

El procedimiento tiene cinco pasos:

1. **Categorizar.** Se define una lista de causas mutuamente excluyentes, con un criterio que dos personas aplicarían igual. Entre 6 y 12 categorías suele ser manejable.
2. **Contar.** Se asigna cada evento a una categoría y se suma. Puede ser cantidad de eventos o una medida de impacto (minutos, costo, pedidos afectados).
3. **Ordenar.** Se ordenan las categorías de mayor a menor.
4. **Calcular el porcentaje acumulado.** Para cada categoría, se suma su valor al de todas las anteriores y se divide por el total.
5. **Cortar.** Se marca el punto donde el acumulado llega a un umbral (típicamente 80%). Las categorías a la izquierda del corte son los "pocos vitales"; el resto es la "cola larga".

**Ejemplo:** en octubre, Rumbo tuvo 2.000 entregas fallidas (cifras hipotéticas). Operaciones clasificó cada una según el motivo registrado por el transportista:

```pareto
titulo: Motivos de entregas fallidas (octubre)
unidad: entregas
Destinatario ausente | 640
Dirección incompleta o errónea | 460
Ventana horaria no cumplida | 300
Comercio sin el paquete listo | 200
Vehículo sin capacidad | 140
Zona de acceso restringido | 110
Paquete dañado | 90
Otros | 60
```

El cálculo del acumulado queda así:

| Motivo | Entregas | % | % acumulado |
|---|---|---|---|
| Destinatario ausente | 640 | 32,0 | 32,0 |
| Dirección incompleta o errónea | 460 | 23,0 | 55,0 |
| Ventana horaria no cumplida | 300 | 15,0 | 70,0 |
| Comercio sin el paquete listo | 200 | 10,0 | 80,0 |
| Vehículo sin capacidad | 140 | 7,0 | 87,0 |
| Zona de acceso restringido | 110 | 5,5 | 92,5 |
| Paquete dañado | 90 | 4,5 | 97,0 |
| Otros | 60 | 3,0 | 100,0 |

Cuatro de ocho categorías explican el 80%. Son "la mitad de las causas", no el 20%, y está bien: el reparto depende de qué tan finas son las categorías. Lo importante es que las dos primeras ya suman 55%, y las dos tienen arreglos conocidos (avisar al destinatario con ETA precisa y validar la dirección al cargar el pedido).

**Por qué importa:** el gráfico convierte una discusión de opiniones ("el problema son los transportistas") en una conversación sobre datos, y deja visible qué se queda afuera.

### Pareto en bugs y calidad

En la mayoría de los sistemas, los bugs no se reparten parejo entre módulos. Suelen concentrarse en unos pocos archivos con mucha lógica, muchos cambios recientes o pocas pruebas. Cruzar los bugs del último trimestre con el módulo donde se corrigieron da un Pareto inmediato.

**Ejemplo:** de 120 bugs del servicio de asignación en seis meses, 74 (62%) se corrigieron en dos paquetes: el que calcula ventanas horarias y el que lee features del feature store. Esos dos paquetes son el 8% del código.

**Por qué importa:** en lugar de "mejorar la cobertura en general", el esfuerzo de pruebas y refactor va donde más bugs evita. También orienta la revisión de código: los cambios en esos paquetes merecen una segunda persona revisando.

### Pareto en latencia y costo de la nube

La latencia total de un sistema y su factura de infraestructura casi siempre están dominadas por pocos componentes. En latencia, unos pocos endpoints o consultas explican la mayor parte del tiempo acumulado (llamadas × latencia media). En costos, unos pocos servicios o recursos explican la mayor parte del gasto (ver [Costos cloud (FinOps)](#t/finops)).

El detalle es medir lo correcto. Para latencia se mira **tiempo acumulado** y no solo la latencia de cada endpoint: un endpoint que tarda 2 segundos pero se llama 100 veces al día pesa menos que uno de 80 ms que se llama 3 millones de veces.

**Ejemplo:** de 40 endpoints de la API de comercios, 3 explican el 78% del tiempo de CPU: la consulta de seguimiento en vivo, el listado de pedidos con filtros y el cálculo de ETA en lote. En la factura mensual hipotética de USD 85.000, Aurora, el clúster EKS de inferencia y la transferencia de datos entre zonas suman USD 64.000 (75%).

**Por qué importa:** optimizar un endpoint que nadie usa es trabajo bien hecho que no cambia nada. Pareto evita gastar semanas en lo que no mueve el total.

### Pareto en el gasto de tokens y en las fallas de evaluación

Los sistemas con LLMs y agentes muestran concentraciones muy marcadas. En el gasto de tokens, unos pocos prompts, flujos o clientes suelen consumir la mayor parte: un flujo que mete el historial completo de un caso en cada llamada, o un agente que entra en bucles de herramientas, puede pesar más que todo el resto junto. En evaluación, unos pocos tipos de falla explican la mayoría de las respuestas incorrectas (ver [Evaluación de LLMs](#t/evaluacion-llms)).

Para el gasto de tokens conviene etiquetar cada llamada al modelo con el flujo, el prompt y el tenant, y después agrupar. Para las evals, cada caso fallido se clasifica con una etiqueta de tipo de falla (dato inventado, herramienta equivocada, política desactualizada, formato roto), igual que los motivos de entrega del ejemplo anterior.

**Ejemplo:** el asistente de soporte consumió 900 millones de tokens en un mes (cifra hipotética):

```pareto
titulo: Tokens del asistente por flujo (millones)
unidad: M tokens
Resumen de casos con historial completo | 410
Agente de reprogramación con reintentos | 220
Respuesta a comercios con RAG | 120
Clasificación de tickets | 60
Respuesta a destinatarios | 45
Traducción de mensajes | 25
Etiquetado de sentimiento | 12
Otros | 8
```

Tres flujos superan el 80% del total, y los dos primeros solos suman 630 millones (70%). Recortar el historial a los últimos 10 mensajes más un resumen, y limitar los reintentos del agente a dos, baja el total a unos 600 millones sin tocar los flujos chicos.

**Por qué importa:** en sistemas con agentes el costo puede crecer sin que nadie lo note, porque un solo flujo mal acotado escala con el uso. El Pareto por flujo y por tenant es el primer tablero que conviene tener.

### Pareto ponderado: frecuencia frente a impacto

Contar eventos responde "qué pasa más seguido", que no siempre es "qué duele más". Si una categoría es frecuente pero barata y otra rara pero muy costosa, el Pareto por frecuencia apunta al lugar equivocado. La solución es **ponderar**: multiplicar cada evento por su costo (minutos de soporte, pedidos afectados, horas de guardia) y armar el Pareto sobre ese total.

**Ejemplo:** en tickets de soporte, "¿dónde está mi pedido?" es el 45% de los tickets, pero cada uno se resuelve en 2 minutos. "Pedido entregado a otra persona" es el 6%, pero cada uno requiere 35 minutos de investigación. Sobre 10.000 tickets, el primero suma 9.000 minutos y el segundo 21.000. Por frecuencia, el primero es el problema; por tiempo del equipo, el segundo pesa más del doble.

**Por qué importa:** la elección de la medida es la decisión más importante del análisis, y conviene hacerla explícita antes de mirar el gráfico.

### La cola larga y el riesgo

Cortar en el 80% no significa ignorar el resto. Hay causas que aparecen pocas veces pero tienen consecuencias graves: una filtración de datos personales, una respuesta del asistente que inventa una política, una caída total por una configuración rara. Esas causas no ganan nunca un Pareto por frecuencia y a veces tampoco por costo promedio, porque su costo real está en el riesgo, no en lo ocurrido.

Por eso el Pareto se complementa con una mirada de riesgo (ver [Gestión y medición de riesgos](#t/riesgos)): se revisa la cola larga buscando eventos de alta severidad, y esos se tratan aparte aunque sean pocos.

**Ejemplo:** entre los 60 "Otros" del primer gráfico hay 2 entregas donde el transportista dejó el paquete con un vecino y compartió por chat el teléfono del destinatario. Son el 0,1%, pero son exposición de datos personales.

**Por qué importa:** usar Pareto para justificar no mirar lo raro es su mal uso más peligroso.

## Casos prácticos

### Bajar las entregas fallidas en un trimestre

**Situación:** el objetivo trimestral es bajar las entregas fallidas un 30%. Hay ocho propuestas de mejora sobre la mesa, una por cada área.

**Qué se hace:** se arma el Pareto de motivos del primer gráfico y se descartan, por ahora, las propuestas que atacan categorías de menos del 7%. Se priorizan dos: el asistente envía la ETA actualizada al destinatario 30 minutos antes, con opción de reprogramar, y el panel de comercios valida la dirección contra un servicio de geocodificación al cargar el pedido. Si la primera reduce los ausentes a la mitad (320) y la segunda las direcciones erróneas un 40% (184), se evitan 504 fallas, un 25% del total. Para llegar al 30% se suma la ventana horaria. Las ocho propuestas originales no se rechazan: pasan a la cola de priorización (ver [Herramientas de priorización](#t/priorizacion)).

### El tenant que consume la mitad de los tokens

**Situación:** el gasto de tokens del asistente creció 40% en dos meses sin un aumento similar de conversaciones.

**Qué se hace:** se arma el Pareto por tenant. Un comercio grande explica el 48% del consumo: integró el asistente en su propio sistema y lo llama en cada actualización de estado, con el historial completo. Se le asigna una cuota de tokens por día, se cambia su integración a un endpoint de estado sin LLM para las consultas simples y se agrega una alerta cuando un tenant supera el 20% del gasto diario. Se deja el Pareto por tenant en el tablero semanal.

### Evals que fallan "por todos lados"

**Situación:** tras cambiar de modelo, el asistente baja del 88% al 81% en el golden set. El equipo empieza a ajustar el prompt caso por caso.

**Qué se hace:** se frena el ajuste caso por caso y se etiquetan los 70 casos que pasaron de bien a mal. Tres tipos de falla explican 55 (79%): el modelo nuevo ignora la instrucción de citar la política, responde en inglés cuando el ticket mezcla idiomas y llama a la herramienta de seguimiento con el ID del comercio en lugar del ID del pedido. Se corrigen esas tres cosas (una instrucción, un ejemplo y una validación de parámetros en la herramienta) y el resultado vuelve al 87%. Los 15 casos restantes se revisan uno por uno, buscando alguno de alta severidad.

## Errores comunes

- **Una categoría "Otros" enorme.** Si "Otros" supera el 10% o 15%, las categorías están mal definidas; se abre una muestra de "Otros" y se crean categorías nuevas.
- **Contar frecuencia cuando importa el impacto.** Se decide antes qué se mide (eventos, minutos, costo, pedidos afectados) y se dice en el título del gráfico.
- **Categorías que se solapan.** Si un evento puede caer en dos categorías, el conteo depende de quién clasifica; se escriben reglas de desempate.
- **Forzar el 80/20.** Si el reparto es parejo, el análisis aporta igual: indica que no hay atajo y que hace falta un cambio de fondo.
- **Ignorar la cola larga cuando lleva riesgo.** Las causas raras con consecuencias graves se tratan aparte, aunque no ganen ningún ranking.
- **Hacer el análisis una sola vez.** Después de arreglar las causas principales, el reparto cambia; se repite cada mes o trimestre.

## Para discutir en equipo

- ¿Qué medida de impacto usaríamos para los incidentes del último trimestre: cantidad, minutos de impacto o pedidos afectados? ¿Cambia el orden?
- ¿Tenemos hoy los datos para armar un Pareto del gasto de tokens por flujo y por tenant? ¿Qué etiquetas faltan en las llamadas al modelo?
- ¿Qué causa de la cola larga de nuestro sistema merece atención aunque sea rara?
- ¿Cómo evitamos que las categorías de un Pareto cambien cada vez que lo arma una persona distinta?
- ¿Podría un LLM clasificar los motivos de falla o los tickets para alimentar el Pareto? ¿Cómo validaríamos que clasifica bien?
