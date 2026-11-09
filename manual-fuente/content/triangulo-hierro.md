---
slug: triangulo-hierro
titulo: El triángulo de hierro: alcance, tiempo y costo
resumen: Cómo negociar el equilibrio entre alcance, tiempo y costo de un proyecto sin recortar calidad en silencio, incluidos proyectos con agentes y LLMs.
lectura: 12
---

## La idea central

Todo proyecto tiene tres restricciones que se tironean entre sí: **qué** se entrega (alcance), **cuándo** (tiempo) y **con cuántos recursos** (costo, que en ingeniería son sobre todo personas). Si se pide más alcance, hace falta más tiempo o más gente; si se adelanta la fecha, hay que recortar algo o sumar recursos. A esa relación se la llama **triángulo de hierro**: no se mueve un lado sin que se muevan los otros.

En el centro está la **calidad**. Cuando alguien fija los tres lados a la vez ("todo, para el 15, con el equipo actual") y el trabajo no entra, el triángulo no se rompe: se achica el centro. Se saltean tests, se recorta la evaluación, la revisión de seguridad queda "para después". Nadie lo decidió, pero pasó. Entender el triángulo sirve para que esa decisión se tome de manera explícita, con números y frente a quien corresponde.

## Conceptos

### Los tres lados y la calidad en el centro

- **Alcance:** funcionalidades y criterios de aceptación. No solo "qué hace", también "qué tan bien": cuántos casos cubre, qué tasa de aciertos se exige.
- **Tiempo:** la fecha de entrega y los hitos intermedios.
- **Costo:** personas, horas, infraestructura y, en proyectos con LLMs, tokens.

```triangulo
titulo: Triángulo de hierro
arriba: Alcance | qué se entrega
izquierda: Tiempo | cuándo
derecha: Costo | personas y presupuesto
centro: Calidad
```

La calidad está en el centro porque resulta de cómo se equilibran los otros tres.

**Ejemplo:** el asistente de soporte de Rumbo debía responder 5 tipos de consulta con 90 % de aciertos en el golden set, en 8 semanas, con 3 personas. A mitad de proyecto se agregaron 3 tipos más sin mover fecha ni sumar gente, y la evaluación se redujo de 200 casos a 60 "para llegar". Se lanzó a tiempo, con 84 % de aciertos reales.

**Por qué importa:** si la calidad no está en la conversación, es el lado que se ajusta por defecto.

### Por qué no se pueden fijar los tres

El trabajo disponible es, aproximadamente, capacidad por tiempo. Si cada persona aporta 0,8 semanas de trabajo efectivo por semana (el resto se va en reuniones, guardias y soporte), un equipo de 2 en 6 semanas tiene 2 × 6 × 0,8 = 9,6 semanas-persona. Si el alcance estimado es de 18, faltan más de 8. Ese hueco se cubre con más tiempo, más gente, menos alcance o menos calidad; no desaparece por voluntad.

**Ejemplo:** "lo sacamos igual, trabajando un poco más" equivale a pedir un 90 % más de horas durante 6 semanas. No ocurre; lo que ocurre es que se recortan las partes menos visibles.

**Por qué importa:** fijar los tres lados es una promesa imposible; decirlo en la semana 1 es mejor que descubrirlo en la 5.

### "Elige dos": qué se fija y qué flexiona

De los tres lados se pueden fijar dos; el tercero es la variable de ajuste:

| Se fija | Flexiona | Cuándo tiene sentido |
|---|---|---|
| Alcance y tiempo | Costo | Fecha contractual, alcance mínimo indiscutible y presupuesto para sumar gente **desde el inicio** |
| Alcance y costo | Tiempo | Producto interno sin fecha dura; equipo estable |
| Tiempo y costo | Alcance | Fecha dura y equipo fijo; el alcance se prioriza (ver [Herramientas de priorización](#t/priorizacion)) |

**Ejemplo:** el proyecto on-prem para un cliente grande tiene go-live firmado y no hay presupuesto para más gente: tiempo y costo fijos. El alcance se ordena con MoSCoW, y los Should y Could son el margen.

**Por qué importa:** si nadie definió qué flexiona, cada persona asume que flexiona otra cosa, y el conflicto aparece tarde.

### El triángulo invertido de los métodos ágiles

La gestión tradicional fija el alcance y estima tiempo y costo. Los métodos ágiles lo dan vuelta: fijan el tiempo (sprints, una fecha de lanzamiento) y el costo (un equipo estable), y el alcance varía: se entrega lo más valioso que entra.

```triangulo
titulo: Triángulo invertido de agile
arriba: Alcance | variable, por prioridad
izquierda: Tiempo | fijo: sprints y fecha
derecha: Costo | fijo: equipo estable
centro: Calidad
```

| | Tradicional | Ágil |
|---|---|---|
| Fijo | Alcance | Tiempo y costo |
| Variable | Tiempo y costo | Alcance |
| Pregunta inicial | ¿Cuánto tarda y cuesta hacer todo? | ¿Qué es lo más valioso que entra? |
| Calidad | Se sacrifica cuando el plan se atrasa | Se protege con la definición de terminado |

**Ejemplo:** en lugar de comprometer "el asistente con 8 tipos de consulta", el equipo compromete "un asistente en producción en 8 semanas con 3 personas, empezando por los tipos de mayor volumen". Si en la semana 6 hay 5 tipos con buena calidad, se lanza con 5.

**Por qué importa:** la tensión no desaparece, pero queda en el lado más fácil de negociar: siempre hay algo menos importante que puede esperar a la próxima versión.

### Negociar con números: el comercio que lo quiere todo

Las conversaciones con stakeholders funcionan mejor con opciones concretas que con un "no se puede".

**Ejemplo:** un comercio grande pide integrar el asistente de Rumbo con su sistema de tickets en 6 semanas, con las 2 personas disponibles y todo el alcance. La estimación:

| Componente | Semanas-persona | Prioridad |
|---|---|---|
| Golden set y evaluación con casos del comercio | 2 | Must |
| Servidor MCP del sistema de tickets (solo lectura) | 3 | Must |
| Base de conocimiento del comercio (RAG) | 3 | Must |
| Revisión de seguridad y piloto | 2 | Must |
| Reprogramar entregas desde el asistente | 5 | Should |
| Panel de métricas para el comercio | 3 | Could |
| **Total** | **18** | |

Con 9,6 semanas-persona de capacidad, las opciones son:

1. **A, sumar 2 personas desde el inicio:** capacidad nominal 4 × 6 × 0,8 = 19,2. Restando la incorporación (1,5 semanas a media productividad por persona nueva, más el tiempo que les dedican las originales) y la coordinación de un equipo de 4, queda cerca de 16. No entra en 6 semanas; en 8, sí.
2. **B, todo con el equipo actual:** 18 / (2 × 0,8) = 11,25 semanas; se redondea a 12.
3. **C, el núcleo en 6 semanas:** los Must suman 10, apenas por encima de la capacidad; se acorta el piloto. Se entrega el 55 % del alcance en la fecha pedida, y la reprogramación y el panel van a una segunda fase de 6 semanas.

```barras
titulo: Semanas hasta entregar, por opción
unidad: semanas
A. Todo, sumando 2 personas | 8
B. Todo, con el equipo actual | 12
C. Núcleo (55 %), equipo actual | 6
C. Fase 2 completa | 12
```

Se presenta en una página: lo pedido, su costo en semanas-persona, las tres opciones con lo que gana y pierde cada una, y una recomendación. El equipo recomienda C: el asistente responde en la fecha pedida, y la reprogramación, la parte con escritura y más riesgo, llega con tiempo para evaluarla bien.

**Por qué importa:** con opciones y números, la discusión pasa de "ingeniería dice que no" a "elijamos entre estas tres", y decide quien debe decidir.

### La ley de Brooks: más gente tarde lo atrasa más

Fred Brooks lo formuló en los años setenta: **sumar personas a un proyecto de software atrasado lo atrasa más**. Por dos motivos:

1. **Incorporación:** una persona nueva tarda en ser productiva y, mientras tanto, le quita tiempo a quienes ya conocen el sistema.
2. **Comunicación:** los canales entre n personas son n(n−1)/2. Con 2 personas hay 1; con 4, 6; con 6, 15; con 10, 45.

Además, no todo trabajo es divisible: si una tarea depende de la anterior, más gente no la acelera.

**Ejemplo:** el proyecto del comercio eligió B y en la semana 6 va atrasado; se suman dos personas. Sin ellas, el equipo aporta 2 × 0,8 = 1,6 semanas-persona por semana. Con ellas, durante las dos primeras semanas las originales dedican un 30 % a explicar el sistema (aportan 2 × 0,8 × 0,7 = 1,12) y las nuevas aportan 0,3 cada una (0,6). Total: 1,72. Una ganancia de 0,12 por semana a cambio de pasar de 1 canal a 6 y de revisar código de personas que no conocen las convenciones.

**Por qué importa:** sumar gente es una buena palanca al principio y una mala al final. Si se mueve el costo, conviene hacerlo temprano y donde está el camino crítico (ver [Planificación y diagramas de Gantt](#t/planificacion-gantt)).

### Recortes ocultos de calidad y deuda técnica

Cuando el triángulo no cierra y nadie negocia, la calidad se recorta donde no se ve en la demo: tests "pendientes", evaluación con menos casos, observabilidad mínima, revisión de seguridad a medias, runbooks inexistentes.

Cada recorte es **deuda técnica**: trabajo que se ahorra hoy y se devuelve después, con intereses. Tomar deuda a veces es la decisión correcta; el problema es tomarla sin registrarla.

**Ejemplo:** para llegar a una fecha, el equipo del asistente salteó la redacción de PII en los logs (2 días de trabajo). Tres meses después, una auditoría encontró teléfonos de destinatarios en los logs: limpiar el histórico, revisar retenciones y documentar el incidente llevó 3 semanas.

**Por qué importa:** un recorte explícito, anotado con su costo y fecha de devolución, es una decisión; uno implícito es una sorpresa futura.

### Más allá del triángulo: la estrella

Algunos marcos amplían el triángulo a una **estrella**: además de alcance, tiempo y costo, suman **riesgo**, **recursos** y **beneficios**, con la calidad en el centro. Sumar el riesgo ayuda porque muchos recortes cambian la exposición (sacar la revisión de seguridad ahorra una semana y sube el riesgo), y sumar beneficios recuerda que el objetivo no es entregar el alcance sino el valor que produce.

**Ejemplo:** sacar la reprogramación del primer lanzamiento baja el beneficio inmediato, pero también el riesgo, porque es la única parte del asistente que escribe en pedidos.

**Por qué importa:** mirar solo tres lados lleva a recortes que parecen gratis y no lo son.

### Agentes de código: cambian el costo, no la verificación

Los agentes de código bajan el costo de escribir código, pero no el de especificar, revisar, evaluar y desplegar, que siguen llevando lo mismo o más, porque hay más código para revisar. El cuello de botella pasa de la escritura a la **verificación**: si un equipo pasa de 15 a 40 PRs por semana y puede revisar bien 20, la mitad se revisa mal o se acumula (ver [Matrices de responsabilidad](#t/raci-rasi) para definir quién aprueba esos cambios).

**Ejemplo:** el servidor MCP de tickets estaba estimado en 3 semanas-persona. Con un agente de código, la implementación llevó una semana, pero la especificación, la revisión de permisos y las pruebas contra el sistema real del comercio llevaron 1,5 más. El ahorro fue del 17 %, no del 66 % que prometía la demo.

**Por qué importa:** si se planifica con el costo de escritura e ignorando la verificación, la calidad vuelve a ajustarse en silencio.

### Una cuarta tensión en funcionalidades con LLMs

Las funcionalidades con LLMs agregan una tensión propia: **calidad de respuesta frente a costo por respuesta**. Un modelo más grande responde mejor y consume más; más contexto recuperado mejora la precisión y suma costo y latencia; más pasos de herramientas resuelven casos difíciles y multiplican la factura.

**Ejemplo:** con valores hipotéticos, el modelo grande llega al 92 % en el golden set a USD 0,04 por conversación y el chico al 85 % a USD 0,01. Con 100.000 conversaciones por mes, USD 4.000 contra USD 1.000. Rutear las consultas simples al chico y las complejas al grande da 90 % a USD 0,018: USD 1.800 por mes.

**Por qué importa:** en un proyecto con LLM, el costo no termina con el desarrollo: sigue en producción y crece con el uso.

### Recortar alcance en una funcionalidad con agentes

Al recortar un agente, las mejores palancas no son sacar funcionalidades enteras sino reducir autonomía y superficie:

- **Menos herramientas:** primero las de solo lectura, las de escritura después.
- **Aprobación humana en lugar de autonomía:** el agente propone y una persona confirma.
- **Menos casos de uso, bien evaluados:** tres tipos de consulta al 92 % valen más que ocho al 80 %.
- **Un canal y un idioma** en la primera versión.

**Ejemplo:** la reprogramación autónoma requería 5 semanas-persona entre herramienta, salvaguardas, red teaming y evaluación. "El agente propone, el operador confirma" requiere 2, y genera datos reales para evaluar la autonomía más adelante.

**Por qué importa:** en sistemas con agentes, recortar autonomía es casi siempre más barato y más seguro que recortar calidad.

## Casos prácticos

### La fecha que nadie quería mover

**Situación:** dirección comprometió con un comercio una fecha de lanzamiento. A cuatro semanas, el equipo calcula que falta un 30 % de la capacidad necesaria.

**Qué se hace:** se presentan tres opciones en una página: sacar la reprogramación, mover la fecha 3 semanas o lanzar todo con la evaluación reducida a 60 casos. La tercera va con su riesgo explícito: la última vez, ese recorte bajó 6 puntos la calidad real. Dirección elige recortar alcance, y el comercio lo acepta porque la reprogramación tiene fecha en la segunda fase.

### El agente de código que llenó la cola de revisiones

**Situación:** un equipo planificó el trimestre suponiendo que los agentes de código duplicaban su capacidad. A las 6 semanas hay 45 PRs esperando revisión y dos incidentes por cambios aprobados sin mirar.

**Qué se hace:** se replanifica con el cuello de botella real, la revisión: se limitan los PRs abiertos por persona, se exige especificación antes de lanzar al agente (ver [Desarrollo guiado por especificaciones](#t/sdd)) y se recorta un 25 % del alcance del trimestre.

### Calidad contra costo de tokens

**Situación:** el piloto del asistente funciona bien, pero el costo por conversación triplica lo presupuestado. Producto pide mantener la calidad y bajar el costo a la mitad.

**Qué se hace:** se presentan opciones medidas en el golden set: ruteo entre modelos (−55 % de costo, −2 puntos), prompt caching (−25 % de costo, sin cambio de calidad) y bajar los fragmentos recuperados de 10 a 5 (−20 % de costo, −4 puntos). Se aplican las dos primeras y se descarta la tercera.

## Errores comunes

- **Fijar los tres lados.** Si no entran, se ajusta la calidad sin que nadie lo decida; se elige explícitamente qué flexiona.
- **Presentar un "no" en lugar de opciones.** Se llevan dos o tres alternativas con números y una recomendación.
- **Sumar gente tarde.** La incorporación y la comunicación se comen la ganancia; se suma temprano y en tareas divisibles.
- **Recortar calidad sin anotarlo.** Cada recorte va al registro de deuda técnica con costo estimado y fecha.
- **Planificar con el costo de escritura de los agentes.** Se planifica con la capacidad de verificación.
- **Olvidar el costo de tokens en producción.** Se negocia junto con la calidad de respuesta, antes de lanzar.

## Para discutir en equipo

- ¿Qué lado del triángulo flexiona en nuestros proyectos actuales? ¿Está escrito en algún lugar?
- ¿Qué recortes de calidad hicimos en los últimos lanzamientos sin registrarlos como deuda?
- ¿Cuál es nuestra capacidad real de revisión de PRs y cómo cambió con los agentes de código?
- ¿Cómo presentamos opciones a un comercio o a dirección cuando el pedido no entra?
- ¿Qué autonomía de nuestros agentes podríamos reemplazar por aprobación humana para entregar antes?
