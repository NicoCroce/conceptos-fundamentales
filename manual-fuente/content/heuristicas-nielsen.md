---
slug: heuristicas-nielsen
titulo: Las 10 heurísticas de Nielsen
resumen: Las diez reglas generales de usabilidad de Jakob Nielsen, con ejemplos de Rumbo, su aplicación a chats con agentes y cómo hacer una evaluación heurística.
lectura: 16
---

## La idea central

Las heurísticas de Nielsen son diez reglas generales para juzgar si una interfaz es usable. Jakob Nielsen las formuló junto con Rolf Molich en 1990 y las publicó en su forma actual en 1994, a partir del análisis de cientos de problemas de usabilidad. No son reglas de estilo ni una lista de verificación exhaustiva: son principios amplios, como «el sistema siempre debe informar qué está pasando», que permiten detectar problemas mirando una pantalla con criterio.

Funcionan como un idioma común. Cuando alguien dice en una revisión «esto rompe la prevención de errores», todos entienden de qué tipo de problema se trata y qué familia de soluciones existe. Son útiles para quien diseña y también para quien revisa un PR de frontend o define cómo se comporta un agente. Y siguen vigentes: un chat con un agente que ejecuta herramientas, con estados largos, acciones con efectos y errores del modelo, pone a prueba casi todas.

## Conceptos

### 1. Visibilidad del estado del sistema

El sistema debe mantener informada a la persona sobre lo que está pasando, con una respuesta adecuada y en un tiempo razonable. Después de cada acción, la persona tiene que poder saber si se registró, si está en curso o si terminó.

Como referencia de tiempos, los umbrales clásicos son: hasta 0,1 segundos se percibe como instantáneo; hasta 1 segundo, la persona nota la demora pero no pierde el hilo; a partir de unos 10 segundos, pierde la atención y necesita un indicador de progreso y, si es posible, una estimación.

**Ejemplo:** bien: en el panel de comercios, al reprogramar 120 envíos aparece «Reprogramando 48 de 120…» y al terminar «120 envíos reprogramados al jueves 14». Mal: el botón se queda sin respuesta 6 segundos, la operadora lo toca otra vez y se envían dos solicitudes.

En una interfaz con agente, el estado incluye qué herramienta se está ejecutando («Consultando el pedido P-1042»), cuántos pasos lleva y si espera algo de la persona. Un indicador genérico de «pensando» durante 40 segundos es el equivalente moderno del reloj de arena.

**Por qué importa:** sin estado visible la gente repite acciones, abandona o desconfía. En sistemas con latencia variable, como los LLMs, es la heurística que más se rompe.

### 2. Correspondencia entre el sistema y el mundo real

El sistema debe hablar el idioma del usuario, con palabras, conceptos y orden familiares, y no la jerga interna. La información debe aparecer en un orden natural y lógico.

**Ejemplo:** bien: la app del transportista dice «Nadie en el domicilio» y «Dirección no encontrada». Mal: el panel muestra «Estado: FAILED_ATTEMPT_2» o «Excepción de geocodificación», nombres que vienen directamente del modelo de datos.

En un agente: el asistente no debería contar su trabajo en términos de sistema («Invoqué get_shipment_status con id 88412»), sino del dominio («Revisé el estado del envío: salió a reparto a las 9:12»). El detalle técnico puede quedar plegado para quien lo necesite.

**Por qué importa:** la jerga interna se filtra sola a la interfaz porque quien implementa la ve todo el día. Hay que revisarla a propósito.

### 3. Control y libertad del usuario

La gente se equivoca y necesita una «salida de emergencia» claramente marcada: deshacer, rehacer, cancelar, volver atrás, sin tener que recorrer un proceso largo.

**Ejemplo:** bien: al archivar 30 envíos aparece «30 envíos archivados · Deshacer» durante 10 segundos. Mal: un asistente de varios pasos para crear un envío que, al tocar «Atrás», pierde todos los datos cargados.

En un agente: la persona debe poder detener una respuesta en curso, cancelar una herramienta antes de que se ejecute y deshacer lo que el agente hizo. Si el agente reprogramó 37 pedidos por un malentendido, tiene que existir «Revertir esta acción» con el mismo detalle de lo que se cambió. Cuando una acción no se puede deshacer (un mensaje ya enviado a 37 destinatarios), eso debe decirse antes de aprobarla.

**Por qué importa:** la posibilidad de deshacer reduce el miedo a explorar y vuelve tolerables los errores, propios y del agente.

### 4. Consistencia y estándares

Las mismas palabras, situaciones y acciones deben significar lo mismo en todo el producto, y conviene seguir las convenciones de la plataforma y de la industria. Hay consistencia interna (dentro de Rumbo) y externa (con lo que la gente ya conoce de otras aplicaciones).

**Ejemplo:** bien: «Reprogramar» se llama igual y usa el mismo componente en el panel, en la app y en el asistente, gracias al [design system](#t/design-systems). Mal: en una pantalla el botón de peligro es rojo y a la derecha, en otra es azul y a la izquierda; en una vista se dice «horario» y en otra «franja».

En un agente: las fichas de acción y los diálogos de aprobación del asistente deben comportarse igual que los del resto del panel. Y el agente mismo debe ser consistente: si una vez pide confirmación para reprogramar, no puede otra vez hacerlo sin preguntar.

**Por qué importa:** cada inconsistencia obliga a la persona a pensar de nuevo algo que ya sabía. Es costo cognitivo puro, sin beneficio.

### 5. Prevención de errores

Mejor que un buen mensaje de error es un diseño que evite el error. Se previenen dos tipos: los **deslices** (la persona quiere hacer lo correcto pero se equivoca al ejecutarlo, como tocar el botón de al lado) y las **equivocaciones** (la persona tiene una idea equivocada de lo que va a pasar).

Técnicas: restricciones (mostrar solo opciones válidas), valores por defecto seguros, confirmaciones para acciones graves y separar físicamente las acciones destructivas.

**Ejemplo:** bien: el selector de fechas para reprogramar muestra deshabilitados los días sin capacidad, con el motivo al pasar el cursor. Mal: permite elegir cualquier día y al confirmar responde «No hay capacidad».

En un agente: antes de una acción con efectos, el agente muestra exactamente qué va a hacer y sobre cuántos elementos («Reprogramar 37 pedidos de zona norte al jueves 14, franja 9 a 12»), y pide aprobación. Si el pedido es ambiguo («pasa los de hoy a mañana»), pregunta antes de actuar. Las herramientas que el agente puede usar y sus límites también son prevención de errores (ver [Seguridad de LLMs y agentes](#t/seguridad-agentes)).

**Por qué importa:** en acciones en bloque, un error multiplica su costo por la cantidad de elementos. Prevenir es mucho más barato que reparar.

### 6. Reconocer antes que recordar

Hay que minimizar la carga de memoria: los objetos, acciones y opciones deben estar visibles o ser fáciles de recuperar. La persona no debería tener que recordar información de una pantalla para usarla en otra.

**Ejemplo:** bien: al reprogramar, la pantalla muestra la dirección, el contenido del pedido y la fecha original. Mal: para abrir un reclamo hay que escribir el número de envío de 12 dígitos que se vio dos pantallas antes.

En un agente: un cuadro de texto vacío obliga a recordar qué puede hacer el asistente. Sugerencias de consultas frecuentes («¿Dónde está mi envío?», «Reprogramar entregas de hoy») y acciones a partir del contexto (el envío que se está mirando) convierten el recordar en reconocer. También vale para la conversación: el agente no debe pedir de nuevo un dato que la persona ya dio tres mensajes antes.

**Por qué importa:** reconocer es mucho más fácil que recordar. Las interfaces de chat abiertas son, por defecto, de recordar; hay que diseñar para compensarlo.

### 7. Flexibilidad y eficiencia de uso

La interfaz debe servir a quien la usa por primera vez y a quien la usa cien veces por día. Los **aceleradores** (atajos de teclado, acciones en bloque, filtros guardados, plantillas) aceleran a los expertos sin estorbar a los novatos.

**Ejemplo:** bien: en el panel, las operadoras pueden seleccionar envíos con Mayúsculas y clic y reprogramarlos juntos, y guardar el filtro «Fallidos de hoy, zona norte». Mal: reprogramar 80 envíos exige abrir cada uno y repetir los mismos tres pasos.

En un agente: el lenguaje natural es un acelerador poderoso para tareas complejas («reprograma los fallidos de hoy por ausencia a mañana a la tarde») pero lento para tareas simples que un botón resuelve en un toque. Un buen diseño combina ambos: el agente propone y la persona ajusta con controles directos. Para expertos, comandos cortos o instrucciones guardadas.

**Por qué importa:** los usuarios intensivos son los que más tiempo pasan en el producto. Ignorar su eficiencia cuesta horas de trabajo por semana.

### 8. Diseño estético y minimalista

Cada elemento extra de una pantalla compite con los relevantes y reduce su visibilidad. No se trata de que se vea «limpio», sino de que la información y las acciones prioritarias resalten.

**Ejemplo:** bien: la pantalla de parada del transportista muestra dirección, nombre, una nota y dos botones grandes: «Entregado» y «No se pudo entregar». Mal: la misma pantalla con el peso del paquete, el ID interno, la hora de creación, el nombre del comercio y seis botones del mismo tamaño.

En un agente: respuestas largas con introducciones de cortesía, repeticiones de la pregunta y párrafos de advertencias genéricas entierran la respuesta. «El envío P-1042 llega hoy entre 14 y 16 h» debe ir primero; los detalles, después o plegados.

**Por qué importa:** en contextos de atención dividida, como un transportista en la calle o una operadora con 300 envíos, lo que no es esencial es ruido que provoca errores.

### 9. Ayudar a reconocer, diagnosticar y recuperarse de errores

Los mensajes de error deben estar en lenguaje claro, sin códigos, indicar con precisión el problema y sugerir una solución concreta.

**Ejemplo:** bien: «No pudimos cambiar la entrega: el pedido ya salió a reparto. Puedes indicar un lugar alternativo o pedir que lo dejen con un vecino». Mal: «Error 409» o «Algo salió mal. Inténtalo de nuevo» para un error que reintentar no va a resolver.

En un agente hay tres familias de error y cada una requiere un mensaje distinto: el **servicio falló** («No pude consultar el estado del envío; el sistema de seguimiento no responde. Probaré de nuevo en un minuto»); la **acción no está permitida** («No puedo cambiar la dirección de entrega; eso lo hace el comercio»); y el **modelo se equivocó**. Para este último, la persona necesita poder corregir («No, era el pedido P-1043») y que el agente rehaga el trabajo con la corrección, sin empezar de cero. Cuando el agente no sabe, debe decirlo en lugar de inventar.

**Por qué importa:** un error bien diagnosticado ahorra un ticket de soporte. Un error genérico genera reintentos inútiles y desconfianza.

### 10. Ayuda y documentación

Lo ideal es que no haga falta documentación, pero a veces es necesaria. Debe ser fácil de buscar, estar centrada en tareas concretas, listar pasos y aparecer en el contexto donde se necesita.

**Ejemplo:** bien: junto al campo «Ventana de entrega» del panel hay un ícono de ayuda que explica, en dos líneas, cómo afecta la ventana a la asignación. Mal: un enlace a un manual de 60 páginas en PDF desde el pie de página.

En un agente: el asistente puede ser la ayuda, respondiendo con [RAG](#t/rag) sobre los manuales y citando la sección. Pero también necesita su propia ayuda: qué puede y qué no puede hacer, qué datos ve, cuándo deriva a una persona. Una línea en el estado vacío del chat («Puedo consultar envíos y reprogramar entregas. No puedo cambiar direcciones») evita la mitad de las frustraciones.

**Por qué importa:** la ayuda en contexto reduce consultas a soporte; la ayuda que nadie encuentra es como no tenerla.

### Cómo hacer una evaluación heurística

Una **evaluación heurística** es una inspección en la que varias personas revisan la interfaz contra las heurísticas y registran los problemas. Es barata y rápida, y complementa (no reemplaza) las [pruebas con usuarios](#t/investigacion-usabilidad).

Pasos:

1. **Definir alcance y escenarios:** qué flujos y con qué tareas. Por ejemplo: «reprogramar un envío», «reprogramar en bloque», «consultar al asistente por un envío demorado».
2. **Evaluar por separado:** entre 3 y 5 evaluadores, cada uno solo, durante una o dos horas, recorriendo los flujos al menos dos veces: la primera para entender, la segunda para buscar problemas. En los estudios de Nielsen, un evaluador encontraba en promedio alrededor del 35 % de los problemas y cinco, alrededor del 75 %; con más de cinco el rendimiento cae.
3. **Registrar cada hallazgo:** dónde, qué heurística viola, descripción y captura.
4. **Consolidar:** juntar las listas, unificar duplicados y dar una severidad.
5. **Priorizar y asignar:** cada problema de severidad 3 o 4 con dueño y fecha.

La severidad combina frecuencia (¿a cuánta gente le pasa?), impacto (¿qué tan difícil es superarlo?) y persistencia (¿pasa una vez o cada vez?). La escala de Nielsen va de 0 a 4:

| Severidad | Significado | Qué se hace |
|---|---|---|
| 0 | No es un problema de usabilidad | Se descarta |
| 1 | Cosmético | Se arregla si sobra tiempo |
| 2 | Menor | Prioridad baja |
| 3 | Mayor | Prioridad alta, antes del lanzamiento |
| 4 | Catástrofe | Bloquea el lanzamiento |

Cada evaluador asigna su severidad sin ver las de los demás y se promedian; las diferencias grandes se discuten. Los evaluadores pueden ser diseñadores, ingenieros o personas de soporte: la mezcla encuentra problemas distintos.

**Ejemplo:** cuatro evaluadores revisan el panel con el asistente integrado. Encuentran 41 problemas en total, 26 únicos tras unificar duplicados. Distribución por heurística:

```barras
titulo: Problemas únicos por heurística (panel con asistente)
unidad: problemas
1 Estado del sistema | 7
5 Prevención de errores | 5
9 Recuperación de errores | 4
6 Reconocer antes que recordar | 3
4 Consistencia | 3
2 Mundo real | 2
3 Control y libertad | 1
8 Minimalismo | 1
```

Hay 2 de severidad 4 (el agente ejecuta reprogramaciones en bloque sin mostrar cuántos envíos afecta; no hay forma de revertir lo que hizo) y 6 de severidad 3. Los 8 se resuelven antes del lanzamiento.

**Por qué importa:** con un día de trabajo de cuatro personas se encuentran la mayoría de los problemas evidentes, y las sesiones con usuarios se aprovechan para lo que solo ellos pueden mostrar.

### Las heurísticas como revisión de un agente

La tabla resume qué preguntar en cada heurística al revisar una experiencia con agente. Sirve como guía en una design review o como parte de los criterios de aceptación; los patrones de diseño se desarrollan en [UX para agentes](#t/ux-agentes).

| Heurística | Pregunta para el agente |
|---|---|
| 1 Estado | ¿Se ve qué herramienta corre, cuánto lleva y si espera aprobación? |
| 2 Mundo real | ¿Habla del dominio y no de funciones internas? |
| 3 Control | ¿Se puede detener, cancelar y revertir lo que hizo? |
| 4 Consistencia | ¿Pide confirmación siempre en los mismos casos? |
| 5 Prevención | ¿Muestra el alcance exacto antes de actuar? ¿Pregunta si es ambiguo? |
| 6 Reconocer | ¿Sugiere qué puede hacer y usa el contexto de la pantalla? |
| 7 Eficiencia | ¿Combina lenguaje natural con controles directos? |
| 8 Minimalismo | ¿La respuesta va primero, sin relleno? |
| 9 Errores | ¿Distingue fallo del servicio, acción no permitida y error del modelo? |
| 10 Ayuda | ¿Explica sus límites y cuándo deriva a una persona? |

**Ejemplo:** el equipo del asistente agrega esta tabla al checklist de su definición de terminado. Una funcionalidad nueva («cancelar envíos desde el chat») no se da por terminada hasta que tiene respuesta para las diez filas; la fila 3 obliga a diseñar la reversión antes de construir la herramienta.

**Por qué importa:** los LLMs hacen que el comportamiento de la interfaz dependa de un modelo, pero las expectativas de las personas siguen siendo las mismas. Las heurísticas dan un marco para revisarlo sin inventar uno nuevo.

## Casos prácticos

### El doble envío por falta de estado

**Situación:** soporte recibe quejas de comercios que ven dos reprogramaciones para el mismo envío. Los logs muestran solicitudes duplicadas con un segundo de diferencia.

**Qué se hace:** se identifica la heurística 1: el botón no cambiaba de estado mientras la solicitud viajaba. Se corrige en dos capas. En la interfaz, el botón pasa a «Reprogramando…» y se deshabilita hasta la respuesta. En el backend, la operación usa una clave de idempotencia para que un doble envío no tenga efecto doble. El problema era de usabilidad y de diseño de API a la vez.

### Un agente que no se podía deshacer

**Situación:** en el piloto del agente de operaciones con permisos de escritura, una operadora pide «pasa los envíos de la zona norte a mañana» pensando en 12 envíos con problemas; el agente reprograma los 240 de la zona.

**Qué se hace:** la evaluación heurística lo clasifica como severidad 4 en dos heurísticas: prevención (no mostró el alcance) y control (no había forma de revertir). Se agregan tres cambios: el agente siempre muestra la cantidad y una muestra de los elementos antes de actuar; las acciones en bloque mayores a 20 elementos piden aprobación explícita con el número en el botón; y cada acción del agente queda registrada con su operación inversa, disponible como «Revertir» durante 30 minutos.

### Mensajes de error que generaban tickets

**Situación:** el 15 % de los tickets de soporte de destinatarios citan el mensaje «No se pudo procesar la solicitud» al intentar reprogramar.

**Qué se hace:** se clasifican los errores reales del backend detrás de ese mensaje: pedido ya en reparto (60 %), sin capacidad (30 %) y fallas técnicas (10 %). Para cada uno se escribe un mensaje con causa y salida, aplicando la heurística 9. En el mes siguiente los tickets con ese motivo bajan a menos de la mitad. El caso de falla técnica es el único que sugiere reintentar.

### Evaluación heurística antes de encargar un estudio

**Situación:** el equipo quiere encargar un estudio externo con 20 participantes para el nuevo panel, con un mes de demora.

**Qué se hace:** primero, cuatro personas (dos de diseño, una de frontend y una de soporte) hacen una evaluación heurística en un día. Se corrigen los problemas de severidad 3 y 4. El estudio con usuarios se reduce a dos rondas de 5 y se concentra en lo que la inspección no puede responder: si las operadoras confían en las propuestas del agente.

## Errores comunes

- **Usar las heurísticas como checklist de diseño visual.** Son principios de comportamiento y comunicación, no de estética; la octava habla de prioridad, no de «que se vea moderno».
- **Un solo evaluador.** Una persona encuentra alrededor de un tercio de los problemas. Usa de 3 a 5, cada uno por separado antes de consolidar.
- **Hallazgos sin severidad.** Una lista de 40 problemas sin prioridad no se resuelve nunca. Asigna severidad 0 a 4 y define qué niveles bloquean el lanzamiento.
- **Reemplazar las pruebas con usuarios.** La evaluación heurística encuentra violaciones de principios; no muestra si el flujo responde al problema real ni cómo lo vive la gente.
- **Olvidar al agente en la revisión.** Revisar solo las pantallas y no el comportamiento del asistente deja afuera estados, reversiones y errores del modelo.
- **Mensajes de error genéricos.** «Algo salió mal» rompe tres heurísticas a la vez. Distingue causas y ofrece una salida concreta para cada una.

## Para discutir en equipo

- ¿Qué heurística rompe más seguido nuestro producto, y en qué capa nace el problema: diseño, frontend o backend?
- ¿Qué acciones del asistente o del agente de operaciones no se pueden revertir hoy? ¿Deberían poder ejecutarse sin aprobación?
- ¿Sumamos una evaluación heurística a la definición de terminado de las funcionalidades con agentes? ¿Quiénes serían los evaluadores?
- ¿Cómo debería informar el asistente su estado cuando una herramienta tarda más de 10 segundos?
- ¿Qué severidad le daríamos a que el agente responda con seguridad algo que no sabe?
