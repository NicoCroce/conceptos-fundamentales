---
slug: riesgos
titulo: Gestión y medición de riesgos
resumen: Cómo identificar, medir, priorizar y seguir los riesgos de un proyecto, con escalas, registro y respuestas concretas, incluidos los riesgos propios de sistemas con LLMs.
lectura: 14
---

## La idea central

Un **riesgo** es algo que todavía no pasó y que, si pasa, afecta al proyecto o al sistema. Gestionarlo no significa eliminar toda incertidumbre, sino decidir de antemano qué hacer con ella: qué se previene, qué se vigila, qué se acepta conscientemente y quién es responsable de cada cosa. La alternativa es enterarse de los riesgos cuando ya son problemas, que es la forma más cara de enterarse.

La analogía es el seguro de un auto: nadie sabe si va a chocar, pero se sabe que puede pasar, cuánto costaría y cuánto cuesta protegerse. Con esos números se decide. En sistemas con agentes y LLMs la lista de riesgos cambia: aparecen la calidad incierta de las respuestas, el costo variable de los tokens, la dependencia de un proveedor y la posibilidad de que un texto malicioso le dé órdenes al agente.

## Conceptos

### Riesgo frente a problema

Un **riesgo** tiene probabilidad: puede pasar o no. Un **problema** (*issue*) ya pasó y hay que resolverlo. La distinción importa porque se gestionan distinto: el riesgo se previene, se vigila o se acepta; el problema se resuelve con un responsable y una fecha.

Cada riesgo tiene además un **disparador**: la señal observable que indica que está por convertirse en problema.

**Ejemplo:** "el proveedor del modelo podría deprecar la versión que usamos" es un riesgo. "El proveedor anunció que la versión se retira en 60 días" es un problema, y el anuncio fue el disparador. Desde ese momento ya no se discute la probabilidad, sino el plan de migración.

**Por qué importa:** un registro lleno de problemas disfrazados de riesgos ("podría ser que el servicio esté lento", cuando ya está lento) hace que nadie actúe con urgencia.

### Identificar riesgos: premortem, listas y supuestos

Hay tres técnicas complementarias:

- **Premortem:** el equipo imagina que el proyecto ya fracasó y escribe por qué. Legitima el pesimismo: no es ser negativo, es el ejercicio.
- **Listas de verificación:** riesgos que se repiten en proyectos parecidos (dependencias externas, datos personales, rendimiento, proveedor único). Evitan olvidar lo obvio.
- **Revisión de supuestos:** cada supuesto del plan ("legal aprueba el acceso a datos en 4 semanas", "el modelo responde en menos de 2 segundos") es un riesgo si resulta falso.

**Ejemplo:** premortem del asistente para transportistas de Rumbo, con 8 personas y 45 minutos:

1. Se lee la consigna: "Es el día después de la fecha de lanzamiento. El asistente fue un fracaso. ¿Qué pasó?"
2. Diez minutos en silencio: cada persona escribe causas en notas adhesivas, una por idea. Salen 32.
3. Se agrupan las repetidas: quedan 9 temas, entre ellos "el asistente reprogramaba entregas que no debía", "la factura de tokens triplicó lo previsto", "un comercio escribió instrucciones en las notas del pedido y el agente las siguió" y "legal no aprobó a tiempo el uso de teléfonos de destinatarios".
4. Cada persona tiene 3 votos para marcar los más probables o graves. Los 6 más votados pasan al registro de riesgos con responsable.

**Por qué importa:** los riesgos más peligrosos son los que nadie dice en voz alta. El premortem da permiso para decirlos.

### Medir: probabilidad, impacto y exposición

La forma más usada es puntuar cada riesgo en dos escalas de 1 a 5 y multiplicarlas. Las escalas tienen que estar escritas, si no cada persona entiende algo distinto por "probabilidad 3":

| Valor | Probabilidad | Impacto en el proyecto |
|---|---|---|
| 1 | Menos de 10 % | Molestia; menos de 1 día de atraso |
| 2 | 10 % a 30 % | Hasta 1 semana de atraso o degradación menor |
| 3 | 30 % a 50 % | 2 a 3 semanas de atraso o una funcionalidad recortada |
| 4 | 50 % a 70 % | Más de un mes de atraso o daño visible para clientes |
| 5 | Más de 70 % | Proyecto cancelado, incidente de seguridad o de datos personales |

La **exposición** es probabilidad × impacto, de 1 a 25. Se definen bandas: 1 a 4 baja, 5 a 9 media, 10 a 16 alta, 20 a 25 crítica.

**Ejemplo:** "inyección de prompts a través de las notas que cargan los comercios" se puntúa con probabilidad 3 (los comercios escriben texto libre y hay miles) e impacto 5 (el agente podría reprogramar entregas ajenas). Exposición: 15, alta.

**Por qué importa:** sin un número, la discusión se gana por quién habla más fuerte. Con números se puede ordenar, aunque sean aproximados.

### El mapa de calor 5x5

El **mapa de calor** ubica cada riesgo en una grilla de probabilidad por impacto. El color de cada celda sale de la exposición y de su banda (baja, media, alta, crítica). Este es el mapa con los seis riesgos iniciales del registro del asistente para transportistas, que se detalla más abajo:

```calor
titulo: Riesgos iniciales del asistente
R1 Calidad en reprogramaciones | 3 | 4
R2 Sobrecosto por conversación | 3 | 3
R3 Deprecación o caída del proveedor | 2 | 4
R4 Inyección en notas del pedido | 3 | 5
R5 Filtración de datos personales | 2 | 5
R6 Demora en aprobación de privacidad | 4 | 2
```

**Ejemplo:** la filtración de datos personales tiene probabilidad baja (2) pero impacto máximo (5): cae en 10, alta. Un retraso en la aprobación de privacidad es probable (4) pero de impacto acotado (2): 8, media. A primera vista el segundo parece más urgente porque "seguro pasa"; el mapa muestra que el primero merece más atención.

**Por qué importa:** el mapa hace visible que los riesgos de baja probabilidad e impacto extremo no se pueden ignorar, y que la esquina superior derecha no admite "lo vemos después".

### Vista cuantitativa: pérdida esperada

Cuando hay datos, se puede ir más allá de las escalas. La **pérdida esperada** es probabilidad × costo, medido en horas de trabajo o en dinero hipotético. Sirve para decidir si una mitigación conviene.

**Ejemplo:** deprecación del modelo. Probabilidad de que la versión usada se retire en los próximos 6 meses, 30 %. Costo si pasa: 80 horas de reevaluación y ajuste de prompts; a un costo hipotético de USD 100 la hora, USD 8.000. Pérdida esperada: 0,3 × 8.000 = USD 2.400. Una capa de abstracción en el gateway de LLM cuesta 40 horas (USD 4.000) y baja el costo de migrar a 20 horas (USD 2.000): la pérdida esperada pasa a USD 600. El ahorro esperado (USD 1.800) no cubre la inversión solo por este riesgo; se justifica si también reduce el riesgo de caída del proveedor.

Otro caso, la caída del proveedor: probabilidad de una caída de 4 horas en un trimestre, 50 %. En 4 horas llegan 8.000 consultas; si cada una escalada a una persona lleva 2 minutos, son 267 horas de operadores. Pérdida esperada: 0,5 × 267 ≈ 133 horas por trimestre.

**Por qué importa:** la vista cuantitativa convierte "esto es riesgoso" en "esto nos cuesta unas 130 horas por trimestre y mitigarlo cuesta 40 una sola vez", que es una decisión fácil de tomar.

### Cualitativo frente a cuantitativo

| Enfoque | Ventajas | Límites | Cuándo usarlo |
|---|---|---|---|
| Cualitativo (escalas 1 a 5) | Rápido, todos participan, sirve para ordenar | Los números son ordinales; 12 no es "el doble de malo" que 6 | Siempre, como primera pasada |
| Cuantitativo (pérdida esperada) | Permite comparar con el costo de mitigar | Requiere datos; da falsa precisión si se inventan | Para los 3 o 4 riesgos más importantes |

**Ejemplo:** el equipo puntúa los 15 riesgos del registro con escalas en una reunión de 30 minutos y solo calcula pérdida esperada para los dos donde se discute una inversión concreta.

**Por qué importa:** cuantificar todo es caro y engañoso; no cuantificar nada impide comparar riesgos con inversiones.

### El registro de riesgos

El **registro de riesgos** es la tabla viva donde se anotan. Columnas mínimas: identificador, descripción (con forma "si pasa X, entonces Y"), probabilidad, impacto, exposición, **responsable** (una persona, no un equipo), **disparador**, **respuesta** y fecha de próxima revisión. Se revisa con una cadencia fija, por ejemplo cada dos semanas, o cada semana cerca de un lanzamiento.

**Ejemplo:** registro del asistente para transportistas al inicio del proyecto:

| ID | Riesgo | P | I | Exp. | Responsable | Disparador | Respuesta |
|---|---|---|---|---|---|---|---|
| R1 | Si la calidad en reprogramaciones no llega a la meta, se atrasa el lanzamiento | 3 | 4 | 12 | Líder de ML | Menos de 85 % en el golden set en el hito de la semana 4 | Mitigar: spike con tiempo fijo; lanzar solo consultas de estado |
| R2 | Si el costo por conversación supera lo previsto, el piloto se vuelve inviable | 3 | 3 | 9 | Plataforma | Costo por conversación mayor a USD 0,05 (hipotético) en el piloto | Mitigar: prompt caching, modelo chico para consultas simples |
| R3 | Si el proveedor depreca o cae, el asistente queda fuera de servicio | 2 | 4 | 8 | Plataforma | Anuncio de deprecación; tasa de errores del proveedor mayor a 2 % | Mitigar: segundo proveedor configurado en el gateway |
| R4 | Si un comercio inyecta instrucciones en notas del pedido, el agente actúa sobre entregas ajenas | 3 | 5 | 15 | Seguridad | Hallazgo en red teaming; acción sobre un pedido no consultado | Mitigar: herramientas acotadas al pedido del usuario; confirmación para reprogramar |
| R5 | Si teléfonos o direcciones de destinatarios llegan al modelo o a los logs, hay una filtración de datos personales | 2 | 5 | 10 | Líder técnico | PII detectada en logs por el escáner | Evitar: no enviar esos campos al modelo; redacción en logs |
| R6 | Si la aprobación de privacidad se demora, el piloto se atrasa | 4 | 2 | 8 | Producto | Sin respuesta de legal a la semana 3 | Mitigar: iniciar el trámite en la semana 1; piloto inicial sin datos personales |

**Por qué importa:** un riesgo sin responsable no lo vigila nadie. Uno sin disparador se descubre cuando ya es un problema.

### Respuestas: evitar, mitigar, transferir, aceptar

Hay cuatro respuestas clásicas:

- **Evitar:** cambiar el plan para que el riesgo no exista. No mandar teléfonos al modelo elimina el riesgo de que el modelo los repita.
- **Mitigar:** reducir probabilidad o impacto. Una confirmación humana antes de reprogramar no evita la inyección, pero limita el daño.
- **Transferir:** pasar el impacto a otro, normalmente por contrato. Un acuerdo de nivel de servicio con el proveedor transfiere parte del costo de una caída, aunque no la caída misma.
- **Aceptar:** decidir conscientemente no hacer nada, porque mitigar cuesta más que la pérdida esperada. Se documenta quién lo aceptó y por qué.

En marcos ágiles a escala se usa **ROAM** para clasificar riesgos en una revisión: **Resolved** (ya no aplica), **Owned** (tiene responsable que lo va a tratar), **Accepted** (se acepta) y **Mitigated** (hay una mitigación en marcha).

**Ejemplo:** en la revisión de la semana 2, R6 queda *Mitigated* (el trámite ya empezó), R3 queda *Owned* (plataforma evalúa el segundo proveedor), y un riesgo menor sobre la traducción de mensajes queda *Accepted*: se lanza solo en castellano.

**Por qué importa:** "aceptar" es una respuesta válida si es explícita. Lo que no es válido es aceptar por omisión.

### Seguir los riesgos en el tiempo

Un registro que no cambia es un registro que nadie mira. Una forma simple de seguirlo es sumar la exposición de todos los riesgos abiertos en cada revisión y graficarla: un **burn-down de exposición**. Debería bajar a medida que se avanza; si sube, aparecieron riesgos nuevos o las mitigaciones no funcionan.

**Ejemplo:** exposición total del asistente por sprint:

| Sprint | Exposición total | Qué cambió |
|---|---|---|
| 1 | 62 | Registro inicial (R1 a R6) |
| 2 | 53 | R6 baja a 4 tras iniciar el trámite; R5 baja a 5 con la redacción en logs |
| 3 | 50 | R1 baja a 6 tras llegar a 88 % en el golden set; aparece R7 (latencia) con 3 |
| 4 | 40 | R4 baja a 5 con herramientas acotadas y confirmación |
| 5 | 35 | R2 baja a 4 tras medir el costo real en el piloto |

```barras
titulo: Burn-down de exposición del asistente
Sprint 1 | 62
Sprint 2 | 53
Sprint 3 | 50
Sprint 4 | 40
Sprint 5 | 35
```

**Por qué importa:** muestra a dirección, en una línea, si el proyecto se está volviendo más seguro o no, y obliga a reevaluar cada riesgo en lugar de copiar la puntuación anterior.

### Apetito de riesgo

El **apetito de riesgo** es cuánto riesgo está dispuesta a aceptar la organización para lograr sus objetivos. Se expresa como reglas: "ningún riesgo de exposición 15 o más sin plan de mitigación aprobado antes del piloto" o "tolerancia cero a la exposición de datos personales, aunque cueste semanas".

**Ejemplo:** para el asistente de Rumbo se acuerda: hasta 3 % de respuestas incorrectas en consultas de estado es aceptable (hay una persona como respaldo); cero acciones de reprogramación sin confirmación del destinatario; cualquier riesgo de datos personales con impacto 5 requiere respuesta "evitar", no solo "mitigar".

**Por qué importa:** sin un apetito explícito, cada riesgo se discute desde cero y la decisión depende de quién esté en la reunión.

### Riesgos propios de sistemas con agentes y LLMs

Los sistemas con LLMs tienen riesgos que no aparecen en un servicio tradicional. Cada uno necesita un **indicador** medible y una **mitigación**:

| Riesgo | Indicador | Mitigación |
|---|---|---|
| Calidad insuficiente | Puntaje en el golden set; tasa de escalamiento a personas | Evaluación continua; lanzamiento por casos de uso |
| Alucinaciones | Respuestas sin respaldo en las fuentes, medidas por muestreo | RAG con citas; respuesta "no sé" permitida |
| Sobrecosto de tokens | Costo por conversación; tokens por consulta, percentil 95 | Límites por usuario, caché, ruteo a modelos chicos (ver [Costos cloud (FinOps)](#t/finops)) |
| Caída o deprecación del proveedor | Tasa de errores del proveedor; calendario de deprecación | Gateway con segundo proveedor; versión fija y reevaluación planificada |
| Inyección de prompts | Hallazgos de red teaming; acciones fuera del alcance del usuario | Herramientas mínimas, confirmación humana (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)) |
| Filtración de datos | PII detectada en logs o respuestas | Minimizar datos enviados, redacción, controles de egreso (ver [Fundamentos de seguridad](#t/fundamentos-seguridad)) |
| Regulación y privacidad | Aprobaciones pendientes; pedidos de borrado sin atender | Evaluación de impacto de privacidad temprana (ver [Privacidad y protección de datos](#t/privacidad-datos)) |
| Dependencia de un solo modelo | Porcentaje de tráfico en un único modelo; tiempo estimado de migración | Evaluación portable entre modelos; prompts sin trucos específicos de un proveedor |

**Ejemplo:** para el riesgo de dependencia de un solo modelo, el indicador del agente interno de operaciones es "horas estimadas para correr el golden set con otro modelo y llegar a la misma calidad". Al principio era "desconocido"; tras una prueba, 2 días. Ese número convirtió un riesgo difuso en uno aceptable.

**Por qué importa:** un riesgo de LLM sin indicador termina discutiéndose con anécdotas ("ayer respondió algo raro"); con indicador se puede seguir en el burn-down como cualquier otro.

## Casos prácticos

### El riesgo que nadie quería anotar

**Situación:** en el premortem del asistente, una ingeniera junior escribe "las notas de los comercios pueden traer instrucciones para el agente". En la reunión nadie lo había mencionado porque "el modelo no haría eso".

**Qué se hace:** se puntúa (probabilidad 3, impacto 5, exposición 15) y se asigna a seguridad. Una sesión de red teaming de una tarde logra que el agente intente reprogramar un pedido ajeno con una nota maliciosa. La mitigación (herramientas acotadas al pedido consultado y confirmación del destinatario) entra al plan como tarea del camino crítico.

### Aceptar con números

**Situación:** plataforma propone dos semanas para configurar un segundo proveedor de LLM "por las dudas". Producto lo ve como trabajo sin valor visible.

**Qué se hace:** se calcula la pérdida esperada de caídas y deprecación: unas 130 horas de operadores por trimestre más USD 2.400 esperados de migración. Dos semanas de una persona son unas 80 horas, una sola vez. Se aprueba, pero empezando por la abstracción en el gateway (40 horas) y dejando el segundo proveedor activo para después del piloto.

### El burn-down que subió

**Situación:** en el sprint 6 la exposición total pasa de 35 a 44. Hay preocupación de que el proyecto vaya mal.

**Qué se hace:** se mira el detalle: subió porque apareció un riesgo nuevo de exposición 9 (el cliente on-prem exige que el modelo corra en su infraestructura) y las mitigaciones siguieron su curso. La subida es una buena señal de que el registro está vivo. Se agrega el riesgo, se asigna y se ajusta el plan.

## Errores comunes

- **Registro sin responsables individuales.** "Plataforma" no es un responsable; una persona con nombre sí.
- **Puntuar sin escalas escritas.** Cada uno entiende algo distinto por "3"; las escalas se acuerdan y se dejan a la vista.
- **Tratar la exposición como precisa.** 12 no es el doble de 6; las escalas sirven para ordenar, y los números finos se reservan para el análisis cuantitativo.
- **Mantener problemas en el registro de riesgos.** Cuando el disparador ocurre, el riesgo se convierte en problema y se gestiona con urgencia.
- **Aceptar por omisión.** Si nadie decidió aceptar un riesgo, no está aceptado: está ignorado.
- **Olvidar los riesgos propios de LLMs.** Calidad, costo de tokens, proveedor e inyección de prompts van al registro con indicador, no solo en una charla de pasillo.

## Para discutir en equipo

- ¿Tenemos escalas de probabilidad e impacto escritas y compartidas, o cada uno puntúa a su manera?
- ¿Cuál es hoy el riesgo de exposición más alta en nuestros sistemas con agentes, y quién es su responsable?
- ¿Qué riesgos estamos aceptando por omisión?
- ¿Cuál es nuestro apetito de riesgo para datos personales y para acciones automáticas de un agente?
- ¿Hacemos premortems antes de proyectos con LLMs? ¿Qué descubrimos la última vez?
