---
slug: roi
titulo: ROI: retorno de la inversión
resumen: Cómo calcular si una inversión de tiempo y presupuesto vale la pena, con costo total, beneficios en rangos y escenarios, aplicado a agentes.
lectura: 13
---

## La idea central

El **ROI** (*return on investment*, retorno de la inversión) responde una pregunta simple: por cada unidad que ponemos, ¿cuánto recuperamos? Sirve para decidir si un proyecto vale la pena, comparar opciones y revisar después si la apuesta salió bien. Cualquier propuesta del tipo "con este agente ahorramos X horas" ya es un cálculo de ROI hecho a ojo.

Lo difícil no es la fórmula, sino lo que entra en ella: los costos se subestiman (se cuenta construir y se olvida operar) y los beneficios se sobreestiman (se supone uso pleno desde el primer día). Un buen cálculo cuenta el costo total, da los beneficios como rangos y muestra el peor caso. Todas las cifras de este tema son hipotéticas.

## Conceptos

### La fórmula y un primer cálculo

```text
ROI = (beneficio − costo) / costo
```

Beneficio y costo se miden en la misma unidad y el mismo período. Un ROI de 0 % recupera exactamente lo invertido; uno negativo, pierde.

**Ejemplo:** el equipo de operaciones de Rumbo arma a mano un reporte semanal de entregas tardías por zona. Automatizarlo lleva 40 horas de desarrollo y unas 2 horas por mes de mantenimiento; ahorra 10 horas por mes de trabajo manual. En el primer año:

- Beneficio: 10 h × 12 = 120 horas.
- Costo: 40 h + 2 h × 12 = 64 horas.
- ROI = (120 − 64) / 64 = 0,875, es decir, **87,5 %**.

Con un costo hipotético de 50 USD por hora de ingeniería y operaciones, son 6.000 USD de beneficio contra 3.200 de costo: el porcentaje es el mismo.

**Por qué importa:** medir en horas permite calcular sin datos financieros y convertir a dinero solo para comparar con otros gastos.

### Período de recuperación

El **período de recuperación** (*payback*) es cuánto tiempo tarda el beneficio acumulado en igualar la inversión inicial. Es menos preciso que el ROI, pero se comunica sin explicación: "se recupera en cinco meses".

```text
recuperación = inversión inicial / beneficio neto por período
```

**Ejemplo:** en el reporte automatizado, la inversión inicial es de 40 horas y el beneficio neto mensual es 10 − 2 = 8 horas. La recuperación es 40 / 8 = **5 meses**. Si el reporte deja de necesitarse en el mes 4 porque cambia el proceso, la inversión no se recupera.

**Por qué importa:** cuanto más incierto es el futuro de un sistema (un modelo que puede quedar obsoleto, un proceso que puede cambiar), más pesa una recuperación corta frente a un ROI alto a tres años.

### Costo total de propiedad

El **costo total de propiedad** (TCO, *total cost of ownership*) suma todo lo que cuesta un sistema durante su vida útil, no solo construirlo. Se puede pensar en cuatro bloques:

1. **Construir:** diseño, desarrollo, evaluación inicial, revisión de seguridad.
2. **Operar:** infraestructura, tokens, licencias, observabilidad.
3. **Mantener:** actualizaciones, cambios de versión del modelo, reevaluaciones, corrección de errores.
4. **Personas:** guardia, revisión humana, capacitación, soporte interno.

**Ejemplo:** TCO del primer año del asistente de soporte que responde consultas de comercios, con cifras hipotéticas.

| Bloque | Detalle | USD primer año |
|---|---|---|
| Construir | 3 personas × 2 meses, evaluación y revisión de seguridad | 60.000 |
| Operar | Tokens 1.500/mes, plataforma (índice vectorial, observabilidad) 1.000/mes | 30.000 |
| Mantener | Media persona de ingeniería: 80 h/mes × 60 USD | 57.600 |
| Personas | Revisión humana de una muestra: 20 h/mes × 25 USD | 6.000 |
| **Total** | | **153.600** |

Construir es menos del 40 % del total; mantener cuesta casi lo mismo y es el bloque que más se olvida (el costo de operar se detalla en [Costos cloud (FinOps)](#t/finops)).

**Por qué importa:** un ROI calculado solo sobre el costo de construcción puede dar el triple del real.

### Beneficios difíciles de medir: rangos en lugar de números

Algunos beneficios se miden directo; otros hay que estimarlos con una cadena de supuestos. La forma más común es **horas ahorradas × costo por hora**, pero también hay beneficios por **reducción de errores** (menos entregas fallidas, menos retrabajo) y por **retención** (comercios que no se van porque el soporte responde rápido).

Para cada uno conviene escribir la cadena de supuestos y dar un rango (bajo, esperado, alto) en lugar de un solo número.

**Ejemplo:** el asistente propone validar direcciones antes de asignar un pedido. Supuestos: 4.000 entregas fallidas por mes por dirección incompleta; el asistente evitaría entre el 10 % y el 30 % (esperado 20 %); cada entrega fallida cuesta entre 3 y 5 USD en reintento y tiempo de soporte (esperado 4). Beneficio mensual: bajo 4.000 × 0,10 × 3 = 1.200 USD; esperado 4.000 × 0,20 × 4 = 3.200 USD; alto 4.000 × 0,30 × 5 = 6.000 USD. La retención se menciona, pero no se suma: no hay datos para estimarla con honestidad.

**Por qué importa:** un rango de 1.200 a 6.000 dice "vale la pena averiguar más"; un único 3.200 da falsa certeza.

### Sensibilidad: tres escenarios

El **análisis de sensibilidad** recalcula el resultado cambiando los supuestos que más pesan. La versión práctica es armar tres escenarios (pesimista, esperado y optimista) y preguntar: ¿el proyecto sigue valiendo la pena en el pesimista? Si no, ¿qué supuesto lo hunde y cómo se puede verificar antes de invertir todo?

**Ejemplo:** el asistente de soporte recibe 30.000 tickets por mes. El beneficio es tickets × tasa de deflexión (tickets que se resuelven sin un operador) × minutos ahorrados por ticket × costo por hora de soporte (25 USD, hipotético). El costo de operación mensual, sin construir, es de 7.800 USD (tokens, plataforma, mantenimiento y revisión).

- Pesimista: 10 % de deflexión, 5 minutos: 30.000 × 0,10 × 5 = 15.000 min = 250 h → 6.250 USD.
- Esperado: 20 %, 8 minutos: 48.000 min = 800 h → 20.000 USD.
- Optimista: 30 %, 10 minutos: 90.000 min = 1.500 h → 37.500 USD.

```barras
titulo: Ahorro mensual frente a costo de operar
unidad: USD/mes
Ahorro optimista | 37500
Ahorro esperado | 20000
Costo de operación | 7800
Ahorro pesimista | 6250
```

En el escenario pesimista, el asistente cuesta más de lo que ahorra, aun sin contar la construcción. El supuesto que decide es la tasa de deflexión: se mide en un piloto con 10 % del tráfico antes de lanzar a todos.

**Por qué importa:** la sensibilidad convierte el ROI de un sí o no en un plan: qué medir primero para reducir la incertidumbre que más pesa.

### El valor del tiempo, en un párrafo

Un ahorro dentro de tres años vale menos que el mismo ahorro hoy. El **valor actual neto** (VAN, *net present value*) descuenta cada beneficio futuro con una tasa anual: con 10 %, 100.000 USD dentro de un año equivalen a 100.000 / 1,10 ≈ 91.000 hoy, y dentro de dos años a 100.000 / 1,10² ≈ 83.000. En proyectos de menos de un año casi no cambia la decisión; al comparar opciones a tres años, sí. La tasa la suele fijar el área de finanzas.

**Ejemplo:** dos opciones con el mismo beneficio total de 300.000 USD en tres años. La A los da parejo (100.000 por año); la B los da todos en el año 3. Con 10 %, el VAN de los beneficios de A es unos 249.000 y el de B, unos 225.000. A es mejor, aunque el total sea igual.

**Por qué importa:** cuando una opción promete beneficios lejanos, el descuento y la incertidumbre juegan en su contra.

### ROI frente a RICE

[RICE y WSJF](#t/priorizacion) ordenan un backlog con puntajes relativos; el ROI estima un resultado absoluto en horas o dinero. Responden preguntas distintas.

| Criterio | ROI | RICE |
|---|---|---|
| Pregunta | ¿Vale la pena hacerlo, comparado con no hacerlo? | ¿Qué hacemos primero entre estas ideas? |
| Unidad | Horas o dinero | Puntos sin unidad |
| Cuenta la operación | Sí, si se usa TCO | No |
| Esfuerzo de cálculo | Alto | Medio |
| Conviene para | Inversiones grandes, construir o comprar, renovar o apagar | Backlog de producto con muchas ideas comparables |

**Ejemplo:** para decidir si se construye el asistente de soporte (153.600 USD el primer año), se calcula ROI. Para ordenar diez mejoras chicas del asistente ya en producción, alcanza con RICE.

**Por qué importa:** calcular ROI para cada ítem del backlog es un desperdicio; no calcularlo para la inversión más grande del año, también.

### ROI de una funcionalidad con LLMs o agentes

Una funcionalidad con LLMs tiene costos que crecen con el uso y beneficios que tardan en llegar. Conviene revisar:

1. **Costo en tokens por tarea:** no por llamada. Un agente que hace 6 llamadas por consulta cuesta 6 veces lo que sugiere el precio por llamada.
2. **Evaluación y mantenimiento:** el golden set, las reevaluaciones cuando cambia la versión del modelo y los ajustes de prompts son trabajo recurrente.
3. **Revisión humana que queda:** si un operador revisa una de cada diez respuestas, ese tiempo se resta del ahorro.
4. **Curva de adopción:** el uso arranca bajo y sube durante meses.

**Ejemplo:** con el escenario esperado del asistente (20.000 USD de ahorro mensual a plena adopción) y una adopción del 40 % en los meses 1 a 3, 70 % en los 4 a 6 y 100 % desde el 7, el ahorro del primer año es 20.000 × (3 × 0,4 + 3 × 0,7 + 6 × 1) = 20.000 × 9,3 = **186.000 USD**. Con el TCO de 153.600, el ROI del primer año es (186.000 − 153.600) / 153.600 ≈ **21 %**. Con adopción plena desde el mes 1 serían 240.000 y 56 %: más del doble. El beneficio neto mensual pasa de 200 USD en los primeros meses a 12.200 desde el séptimo, y la construcción (60.000) se recupera alrededor del **mes 10**. Para simplificar, el cálculo deja fijo el gasto en tokens; en la práctica crece con la adopción.

**Por qué importa:** el ROI de un agente depende sobre todo de dos números que no se conocen antes del piloto: la tasa de deflexión y la velocidad de adopción.

### ROI de los agentes de código para el equipo

El costo es visible (licencias y tokens por persona); el beneficio no, porque las horas ahorradas escribiendo código solo cuentan si se convierten en entregas. Se mide con cycle time y tasa de fallos, como en [métricas de entrega](#t/metricas-entrega), no con PRs generados.

**Ejemplo:** 10 personas, con un costo hipotético de 40 USD por persona por mes en licencias y 150 en tokens: 1.900 USD por mes. Si cada persona ahorra 4 horas semanales de escritura pero suma 1 hora de revisión, el ahorro neto es 3 h × 4 semanas × 10 = 120 horas por mes; a 60 USD la hora, 7.200 USD. ROI ≈ (7.200 − 1.900) / 1.900 ≈ 280 %. Si la tasa de retrabajo sube y se pierden 2 horas por persona por semana corrigiendo, el ahorro neto baja a 1 hora semanal, 2.400 USD por mes, y el ROI cae a 26 %.

**Por qué importa:** el ROI de los agentes de código se gana o se pierde en la revisión y el retrabajo, no en la escritura.

### Trampas frecuentes

- **Contar dos veces el mismo ahorro:** dos iniciativas reclaman la misma reducción de tickets.
- **Ignorar la adopción:** suponer uso pleno desde el primer día, como se vio arriba, duplica el ROI.
- **Costo hundido:** lo ya gastado no se recupera; la decisión de seguir se toma solo con costos y beneficios futuros.
- **Horas ahorradas que nadie reasigna:** si el tiempo liberado no se usa en algo útil, el beneficio es teórico.

**Ejemplo:** el asistente reclama 6.000 tickets deflectados por mes y la autogestión del panel de comercios, 5.000; el total bajó 7.000. Se atribuye por experimento (grupo con asistente y grupo sin él) en lugar de sumar.

**Por qué importa:** todas estas trampas empujan el resultado hacia el optimismo.

## Casos prácticos

### El agente de operaciones y un beneficio que no se ve

**Situación:** se propone que el agente interno de operaciones investigue todas las alertas de entregas tardías. El beneficio es "resolver incidentes más rápido", sin un número.

**Qué se hace:** se arma la cadena de supuestos con rangos: 30 incidentes por mes y entre 10 y 40 minutos de investigación ahorrados por incidente (esperado 20). Eso da entre 5 y 20 horas de guardia por mes, contra 12 horas mensuales de operación y mantenimiento: en el escenario esperado (10 h) no alcanza. El caso solo se sostiene si se valora la reducción de entregas tardías durante el incidente, así que se mide eso en un piloto de un mes antes de ampliar.

### Modelo grande o modelo adaptado

**Situación:** el clasificador de tickets usa un modelo grande y cuesta 3.000 USD por mes en tokens. Se propone adaptar un modelo chico, con un costo de construcción de 25.000 USD y 800 USD por mes de operación, incluida la reevaluación periódica.

**Qué se hace:** se compara el ahorro: 2.200 USD por mes, recuperación en unos 11 meses. Se suma al costo el riesgo de que la próxima versión del modelo grande baje de precio a la mitad: en ese escenario el ahorro cae a 700 USD por mes y la recuperación se estira a casi tres años. Se prueba primero una palanca más barata: prompt caching y ruteo de los tickets simples a un modelo mediano.

### El proyecto que ya consumió cuatro meses

**Situación:** un proyecto de resumen automático de casos lleva cuatro meses y 80.000 USD. La evaluación da 70 % de resúmenes aceptables, contra una meta de 90 %. Alguien argumenta que "ya invertimos demasiado para abandonarlo".

**Qué se hace:** se separa el costo hundido. La pregunta es si los próximos costos (30.000 USD y dos meses más) se justifican con los beneficios futuros y la probabilidad realista de llegar al 90 %. El equipo estima esa probabilidad en 40 %; el beneficio esperado no cubre el costo. Se decide reducir el alcance: usar los resúmenes solo como borrador interno para operadores, donde 70 % ya ahorra tiempo, y cerrar el resto.

## Errores comunes

- **Calcular solo con el costo de construcción.** Se usa el costo total de propiedad, con mantenimiento, operación y personas.
- **Dar un único número de beneficio.** Se presenta un rango con pesimista, esperado y optimista, y se dice qué supuesto pesa más.
- **Suponer adopción plena desde el primer día.** Se modela una curva de adopción y se verifica con un piloto.
- **Olvidar la revisión humana que queda.** Si alguien revisa las respuestas del agente, ese tiempo se resta del ahorro.
- **Dejarse llevar por el costo hundido.** Se decide con lo que falta gastar y lo que se puede ganar desde hoy.
- **Calcular ROI para todo.** Se reserva para inversiones grandes; para ordenar un backlog alcanza con RICE o WSJF.

## Para discutir en equipo

- ¿Qué funcionalidad con LLM que tenemos en producción revisaríamos con un cálculo de ROI real, con TCO y adopción medida?
- ¿Cuál es el supuesto más débil en el caso de negocio del próximo agente que queremos construir y cómo lo verificamos barato?
- ¿Cómo medimos si las horas que ahorran los agentes de código se convierten en entregas?
- ¿Quién valida los rangos de beneficio: el equipo que propone el proyecto o alguien externo?
- ¿En qué momento revisamos el ROI estimado contra el real, y qué hacemos si no se cumple?
