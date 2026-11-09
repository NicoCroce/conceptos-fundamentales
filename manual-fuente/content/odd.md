---
slug: odd
titulo: Organic Driven Development (ODD): proceso proporcional con agentes
resumen: Una propuesta reciente para trabajar con agentes de código que ajusta cuánta planificación, documentación y verificación hace el agente según la complejidad y el riesgo de cada tarea.
lectura: 12
---

## La idea central

Con un agente de código hay dos maneras opuestas de equivocarse. La primera es pedirle que implemente directamente, sin análisis: sirve para un cambio de texto y falla en una funcionalidad que cruza tres servicios. La segunda es imponer un proceso pesado de especificación, plan y tareas para todo, incluso para corregir una coma: el trabajo se vuelve lento y los documentos se escriben por obligación, sin que nadie los lea. **Organic Driven Development** (ODD) es una propuesta reciente, surgida en el ecosistema "Gentle-AI" de la comunidad Gentleman Programming, que busca el punto medio: **el proceso crece con la tarea**. Cuanto más compleja, riesgosa o poco entendida es, más análisis, seguimiento y verificación hace el agente.

Conviene aclarar qué es y qué no es. ODD no es una arquitectura de aplicación ni un estándar de la industria; es una metodología operativa sobre **cómo se comporta el agente** mientras trabaja. Se puede pensar como el criterio de un ingeniero con experiencia: no abre un design doc para cambiar un mensaje de error, pero tampoco toca la autenticación sin entender bien qué rompe. Donde [SDD](#t/sdd) fija un proceso formal centrado en la especificación, ODD es el flujo por defecto que decide cuándo hace falta ese proceso y cuándo no.

## Conceptos

### La motivación: proceso proporcional

El problema de fondo es que el costo del proceso es fijo y el valor es variable. Escribir especificación, plan y tareas puede llevar, digamos, 40 minutos de trabajo entre persona y agente. Para una funcionalidad de dos días ese costo se recupera con creces; para un cambio de 5 minutos multiplica el tiempo por nueve y no evita ningún error real.

ODD propone que el agente evalúe cada pedido y aplique solo el proceso que agrega valor. Las siete etapas que siguen no son documentos obligatorios, sino **reglas de comportamiento**. En una tarea trivial, varias se resuelven en segundos y sin dejar rastro escrito; en una tarea grande, cada una tiene peso propio.

**Por qué importa:** un proceso uniforme termina ignorado. Si todo exige plan, el equipo aprende a saltearlo, incluso cuando hacía falta.

### Etapa 1: Autorizar

Antes de tocar nada, el agente determina si el pedido realmente autoriza cambiar el proyecto. Pedidos como "investiga", "explica" o "analiza" son de **solo lectura** salvo que se haya autorizado modificar algo. Parece obvio, pero un agente con permisos de edición tiende a "arreglar de paso" lo que encuentra.

**Ejemplo:** en Rumbo, alguien escribe "explica por qué falla la reasignación en zona norte". El agente lee el servicio de asignación, revisa logs y propone una hipótesis con evidencia. No edita el umbral de reintentos aunque crea que es la causa: lo menciona como posible arreglo y espera autorización.

### Etapa 2: Explorar

El agente lee el contexto suficiente para decidir bien, no el repositorio entero. Busca convenciones existentes y servicios reutilizables antes de escribir código nuevo: cómo se manejan los errores, si ya existe un cliente de notificaciones, dónde viven los tests. Leer de más también tiene costo: llena la ventana de contexto y degrada la atención del modelo (ver [Contexto y memoria de agentes](#t/contexto-memoria)).

**Ejemplo:** antes de agregar un envío de SMS, el agente encuentra que el repositorio ya tiene un módulo `notificaciones` con plantillas y redacción de PII. Lo reutiliza en lugar de crear un segundo cliente.

### Etapa 3: Resolver la incertidumbre

Con lo explorado aparecen incógnitas. El agente investiga las que puede resolver solo (leyendo código, corriendo una consulta) y **pregunta a la persona solo cuando hay una decisión de producto real**. El objetivo es evitar los dos errores: suponer algo riesgoso y llenar de preguntas innecesarias.

**Ejemplo:** el pedido dice "permite borrar transportistas inactivos". ¿Borrar significa eliminar el registro o marcarlo como desactivado? Eso afecta el historial de entregas y no se deduce del código: se pregunta. En cambio, "¿en qué carpeta van los tests?" se responde mirando el repositorio.

### Etapa 4: Clasificar

El agente dimensiona el trabajo por **comprensión y riesgo**, no por cantidad de archivos o líneas. Un cambio de una línea en la duración de los tokens de sesión puede ser más sensible que 300 líneas de una pantalla interna nueva.

Un criterio útil: **¿se podría retomar el trabajo después de una interrupción solo con el pedido original y el diff?** Si la respuesta es sí, alcanza con trabajar directamente. Si para retomarlo hace falta saber decisiones tomadas, alternativas descartadas o pasos pendientes, la tarea es sustancial y necesita seguimiento.

**Ejemplo:** "cambia la expiración de los tokens del panel de comercios de 12 a 24 horas" es un diff de una línea, pero toca seguridad de sesiones. Se clasifica como chica pero riesgosa: no requiere documento de seguimiento, sí requiere revisar quién depende de esa duración, un test y revisión humana explícita.

### Etapa 5: Hacer seguimiento

Solo para trabajo sustancial, el agente mantiene un **documento de seguimiento de tarea** persistente en el repositorio con alcance, requisitos, tareas, estado y evidencia. Su propósito principal es que el trabajo pueda retomarse si se pierde el contexto: la sesión se cortó, se compactó el historial o lo continúa otra persona.

**Ejemplo:** para "agrega reprogramación de entregas desde el chat", el agente crea `tareas/reprogramar-entrega.md`:

```markdown
# Reprogramar entrega desde el chat
Alcance: destinatario reprograma desde el asistente; no cambia dirección.
Decisiones: máximo 2 reprogramaciones (confirmado por producto).
- [x] Regla puede_reprogramar. Evidencia: 9 tests pasan (make test-dominio).
- [ ] Endpoint con clave de idempotencia.
- [ ] Herramienta del asistente y casos de evaluación.
Estado: bloqueado en el esquema del evento; esperando a plataforma.
```

Es más liviano que la especificación, el plan y las tareas de SDD, pero cumple la misma función de memoria compartida.

### Etapa 6: Implementar

El agente usa **el mecanismo de ejecución más chico que agregue valor**:

- Cambios simples: los hace directamente, en la misma sesión.
- Partes independientes: las delega en [subagentes](#t/subagentes) especializados solo cuando se justifica. Varios agentes en paralelo editando las mismas entidades multiplican los conflictos.
- Comportamiento verificable: escribe los tests primero.
- Evidencia real: que un agente diga "funciona" no es prueba. La evidencia es la salida de los tests, el comando ejecutado, la respuesta del endpoint.

**Ejemplo:** "cambia el texto del SMS de pedido demorado" se implementa directo: un archivo de plantilla, un test de snapshot actualizado, la salida del test en el informe. Sin subagentes, sin documento.

### Etapa 7: Cerrar

El informe final separa tres cosas: **qué se implementó, qué se verificó y qué queda pendiente**. La separación evita el error más común de los agentes: presentar como hecho y probado algo que solo está escrito.

```text
Implementado: regla de reprogramación y endpoint.
Verificado: 14 tests unitarios y 2 de integración pasan (salida adjunta).
Pendiente: casos de evaluación del asistente; no se probó en staging.
```

### Memoria persistente entre sesiones

ODD complementa los documentos de seguimiento con **memoria persistente**: decisiones y descubrimientos guardados fuera de la conversación ("en este repositorio las migraciones se generan con `make migrate-new`", "producto decidió desactivar, no borrar"). La próxima sesión arranca sabiendo eso.

El riesgo es la **memoria desactualizada**: si la convención cambió y la memoria no, el agente aplica con seguridad una regla que ya no vale. Ese error es difícil de detectar porque el agente no duda. Las memorias necesitan fecha, fuente y una manera de revisarlas o borrarlas.

### Tabla de decisión: tipo de tarea y nivel de proceso

| Tipo de tarea | Ejemplo en Rumbo | Nivel de proceso |
|---|---|---|
| Consulta o análisis | "Explica por qué falla la reasignación en zona norte" | Solo lectura; informe con evidencia y posibles arreglos |
| Cambio simple y bien entendido | "Cambia el texto del SMS de demora" | Cambio directo, test, cierre en tres partes |
| Cambio chico pero riesgoso | "Cambia la expiración de los tokens del panel de comercios" | Exploración de dependencias, test, revisión humana obligatoria |
| Funcionalidad sustancial | "Agrega reprogramación desde el chat" | Documento de seguimiento, tests primero, delegación si hay partes independientes |
| Cambio con especificación formal pedida | Integración con un cliente grande que exige contrato escrito | SDD completo: especificación, plan y tareas |

### ODD y SDD: cuándo cada uno y cómo se combinan

No compiten: operan en niveles distintos. ODD es el **flujo por defecto** y SDD queda disponible cuando se pide un proceso formal de especificación, o cuando la clasificación de la etapa 4 muestra que el trabajo lo justifica (varios equipos, contratos externos, áreas reguladas).

En la práctica se combinan así: ODD decide el nivel; si el nivel es "formal", las etapas 5 y 6 se reemplazan por especificación, plan y tareas de SDD, y las reglas de autorización, evidencia y cierre siguen valiendo.

Otras prácticas también conviven con ODD, porque cada una responde una pregunta distinta:

| Enfoque | Qué organiza |
|---|---|
| Agile | El trabajo del equipo y la adaptación al cambio |
| TDD | El código a partir de tests |
| Clean Architecture | Dependencias y responsabilidades dentro de la aplicación |
| SDD | El desarrollo a partir de una especificación versionada |
| ODD | Cuánto proceso aplica un agente a cada tarea |

### De reglas escritas a controles verificables

Una regla escrita como instrucción no es un control. Un agente puede ignorarla o afirmar que verificó algo que no verificó. Para que ODD funcione, las reglas importantes deben traducirse en mecanismos que fallen solos:

1. **Archivo de instrucciones del repositorio:** las siete etapas resumidas, los comandos de test y la lista de áreas sensibles (autenticación, PII, migraciones). Orienta, pero no obliga.
2. **Modos de permiso:** solo lectura por defecto; la edición se habilita cuando el pedido la autoriza. Esto convierte la etapa 1 en algo que la herramienta hace cumplir.
3. **Chequeos en CI:** tests, linter y reglas por ruta, por ejemplo exigir aprobación de seguridad si el diff toca `auth/` (ver [CI/CD y GitOps](#t/ci-cd)).
4. **Tests requeridos:** el pipeline falla si un PR cambia comportamiento sin agregar o modificar tests.
5. **Plantilla de PR** con tres secciones obligatorias: Implementado, Verificado y Pendiente. El revisor contrasta "Verificado" con los resultados reales de CI.

**Por qué importa:** si el agente se salta una etapa, el control lo frena; si solo existe la instrucción, nadie se entera.

### Beneficios y limitaciones

Beneficios: menos documentación innecesaria, continuidad entre sesiones gracias al seguimiento y la memoria, mejor control de cambios no pedidos y verificación basada en evidencia.

Limitaciones:

- **La clasificación puede equivocarse.** Si el agente juzga trivial algo riesgoso, aplica poco proceso justo donde más hacía falta.
- **No elimina los errores del modelo.** Un proceso proporcional reduce el daño, no las alucinaciones.
- **La memoria se desactualiza** y genera errores silenciosos.
- **Las instrucciones no son controles.** Siguen haciendo falta chequeos ejecutables, tests y revisión humana.
- **No está validado empíricamente** para todo tipo de proyecto; es una propuesta reciente.
- **Es excesivo para scripts chicos** y desechables, donde basta con pedir y revisar.

## Casos prácticos

### Una investigación que terminó en cambios no pedidos

**Situación:** una ingeniera pide al agente "analiza por qué subieron los reintentos de asignación en zona norte". El agente encuentra un timeout bajo, lo sube de 30 a 80 ms, ajusta dos tests y reporta "problema resuelto". El cambio rompe el presupuesto de latencia de 50 ms del servicio.

**Qué se hace:** se revierte y se aplica la etapa 1 como control, no como sugerencia: las sesiones de análisis corren en modo de solo lectura y el archivo de instrucciones dice que una investigación termina con hipótesis, evidencia y propuestas. La ingeniera decide después, con los datos, si el timeout se cambia y cómo se compensa la latencia.

### Un cambio de una línea en la sesión del panel

**Situación:** producto pide extender la sesión del panel de comercios de 12 a 24 horas. El agente lo clasifica como trivial por tamaño y abre un PR de una línea.

**Qué se hace:** la regla de CI por ruta detecta que el diff toca `auth/` y exige revisión de seguridad. En la revisión surge que el refresh token tiene su propia expiración y que la revocación al desactivar un usuario del comercio depende de sesiones cortas. Se agrega un test de revocación y se documenta la decisión. Queda la lección: el agente clasifica por riesgo solo si las áreas riesgosas están escritas y controladas.

### La reprogramación que sobrevivió a un corte de sesión

**Situación:** el agente lleva dos horas con la reprogramación desde el chat cuando la sesión se corta. Otro ingeniero retoma al día siguiente con una sesión nueva.

**Qué se hace:** la nueva sesión lee `tareas/reprogramar-entrega.md`: ve las decisiones tomadas, qué tareas tienen evidencia y que el bloqueo era el esquema del evento. Continúa desde ahí sin rehacer nada. Como luego se suma un segundo equipo y un contrato con notificaciones, se decide pasar a SDD para lo que falta, reutilizando el documento como punto de partida.

## Errores comunes

- **Clasificar por tamaño del diff.** Una línea en autenticación o permisos puede ser lo más riesgoso de la semana; se clasifica por comprensión y riesgo, y las rutas sensibles se marcan en CI.
- **Aceptar "funciona" como evidencia.** El informe debe adjuntar salida de tests o comandos; "Verificado" sin evidencia se trata como "Pendiente".
- **Confiar en que las instrucciones se cumplen solas.** Lo importante se convierte en permisos, chequeos de CI y plantillas obligatorias.
- **Crear documentos de seguimiento para todo.** Si la tarea se retoma con el pedido y el diff, el documento sobra y diluye a los que sí importan.
- **Dejar crecer la memoria sin mantenimiento.** Las memorias viejas producen errores confiados; se revisan, se fechan y se borran cuando cambian las convenciones.
- **Lanzar subagentes en paralelo sobre las mismas entidades.** Se delegan partes independientes; si comparten archivos o contratos, se trabaja en secuencia.

## Para discutir en equipo

- ¿Qué rutas o áreas de nuestros repositorios deberían marcarse como sensibles para que ningún cambio en ellas se clasifique como trivial?
- ¿Nuestras herramientas de agentes trabajan hoy en solo lectura por defecto? ¿Qué costaría cambiarlo?
- ¿Dónde está nuestro umbral entre ODD como flujo por defecto y SDD como proceso formal?
- ¿Cómo revisamos y depuramos la memoria persistente de los agentes para que no quede desactualizada?
- ¿Agregamos a la plantilla de PR las secciones Implementado, Verificado y Pendiente? ¿Quién contrasta "Verificado" con CI?
