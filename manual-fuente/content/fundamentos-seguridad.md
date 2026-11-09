---
slug: fundamentos-seguridad
titulo: Fundamentos de seguridad y modelado de amenazas
resumen: Los conceptos base de seguridad, los principios de diseño y el modelado de amenazas con STRIDE, aplicados a sistemas con agentes y LLMs.
lectura: 15
---

## La idea central

La seguridad no es una lista de herramientas, sino una forma de mirar un sistema: qué queremos proteger, de quién, por dónde puede entrar el daño y cuánto nos cuesta evitarlo. Antes de hablar de JWT, WAF o CSP hace falta un vocabulario común para responder esas preguntas en una revisión de diseño sin depender de la intuición de una sola persona.

Una analogía: en un depósito de Rumbo no todas las personas tienen las mismas llaves, hay cámaras para saber qué pasó y alguien recorrió el edificio preguntando "¿por dónde entraría yo si quisiera llevarme algo?". Eso último es el **modelado de amenazas**. Con agentes se suma un componente, el modelo, que lee texto de cualquiera y puede decidir acciones. Este tema da las bases del capítulo.

## Conceptos

### Confidencialidad, integridad y disponibilidad

Las tres propiedades clásicas (la "tríada CIA", por sus siglas en inglés) clasifican qué se rompe en un incidente:

1. **Confidencialidad:** solo quien corresponde puede leer un dato. Se rompe cuando un comercio ve pedidos de otro o cuando la dirección de un destinatario aparece en un log público.
2. **Integridad:** el dato no se modifica sin autorización y se puede confiar en él. Se rompe cuando alguien cambia la franja de entrega de un pedido ajeno o cuando un documento envenenado altera la base de conocimiento del asistente.
3. **Disponibilidad:** el sistema responde cuando se lo necesita. Se rompe con una caída, un ataque de denegación de servicio o un agente en bucle que agota la cuota de tokens del proveedor.

A estas se suman dos propiedades que aparecen seguido:

- **Autenticidad:** poder comprobar quién originó algo (un usuario, un servicio, un mensaje). Ver [Autenticación, JWT y OAuth](#t/autenticacion).
- **No repudio:** que quien hizo una acción no pueda negarla después, porque hay un registro confiable y atribuible.

**Ejemplo:** el asistente de soporte responde 1.000 consultas por hora. Si filtra el teléfono de un destinatario, falla la confidencialidad; si reprograma una entrega por una instrucción escondida en una nota, falla la integridad; si una página de 400.000 tokens lo deja en bucle y agota la cuota diaria a las 11 de la mañana, falla la disponibilidad para todos los comercios.

**Por qué importa:** nombrar la propiedad afectada ordena la discusión: cifrar protege la confidencialidad, no la disponibilidad.

### Principios de diseño seguro

Los principios son reglas de decisión que se repiten en todos los temas del capítulo:

- **Mínimo privilegio:** cada usuario, servicio o agente tiene solo los permisos que su tarea necesita, durante el tiempo que los necesita. El agente de operaciones lee métricas; no necesita escribir en la base de pedidos.
- **Defensa en profundidad:** varias capas independientes, de modo que si una falla otra contiene el daño. Sanitizar la salida del modelo en el backend y, además, restringir imágenes externas con CSP en el navegador.
- **Seguro por defecto (secure defaults):** la configuración inicial es la restrictiva y abrir requiere una decisión explícita. Un bucket nuevo nace privado; una herramienta nueva del agente nace de solo lectura.
- **Fallar cerrado (fail closed):** ante un error en un control, se deniega. Si el servicio de autorización no responde, la herramienta devuelve error en lugar de "dejar pasar por las dudas".
- **Separación de funciones:** una sola persona o componente no puede completar sola una acción crítica. Quien escribe el cambio de política de acceso no es quien lo aprueba.
- **Minimizar la superficie de ataque:** cada endpoint, puerto, herramienta o dependencia es una entrada posible. Lo que no se usa, se apaga o se elimina.

**Zero Trust** resume varios de estos principios: estar dentro de la red no da confianza. Cada petición se autentica y autoriza por sí misma, aunque venga de una IP interna: mTLS o tokens entre servicios, herramientas internas detrás de un proxy con identidad en lugar de una VPN que abre toda la red, y permisos evaluados en cada llamada.

**Ejemplo:** se propone que el agente de operaciones pueda reiniciar pods. Con mínimo privilegio, la herramienta solo reinicia deployments de una lista de 5 servicios, en un namespace; con fallar cerrado, si no se puede verificar la lista, no reinicia; con separación de funciones, el reinicio en producción queda pendiente hasta que una persona de guardia lo aprueba.

**Por qué importa:** en una revisión es más rápido preguntar "¿si este control falla, abre o cierra?" que discutir cada caso desde cero.

### Límites de confianza y diagramas de flujo de datos

Un **límite de confianza** (trust boundary) es cualquier punto donde los datos pasan entre dominios con distinto nivel de confianza: del navegador a nuestra API, del backend a un proveedor externo, de un documento de terceros al contexto del modelo. En cada cruce se pregunta: ¿quién controla lo que entra?, ¿qué se valida?, ¿con qué identidad sigue?

Un **diagrama de flujo de datos** (DFD) dibuja componentes, almacenes, flujos y límites de confianza. Alcanza con un diagrama de texto en el documento de diseño.

```text
 [Usuario del comercio]
        |  (1) navegador: contenido y código no controlados
 =======|=========================== límite: internet -> borde
        v
 [Borde: CDN / WAF / rate limiting]
        |  (2) TLS terminado, tráfico filtrado
 =======|=========================== límite: borde -> nuestra red
        v
 [API del asistente] --- sesión del usuario, autorización
        |
        v
 [Agente (bucle + herramientas)] <---------------------------+
        |  (3) prompt + contexto                             |
 =======|=========================== límite: proveedor       |
        v                                                    |
 [Proveedor de LLM]  -- respuesta: texto NO confiable -------+
        |
 =======|=========================== límite: agente -> herramientas
        v
 [Herramientas: obtener_pedido, buscar_docs, leer_url]
        |                     |                     |
        v                     v                     v
 [Aurora: pedidos, PII]  [Base vectorial]   [Internet: páginas
                         (docs internos)     de seguimiento]
                                             (4) contenido externo
```

Los cuatro cruces numerados son los lugares donde se concentran las amenazas: (1) entrada del usuario, (2) el borde, (3) datos que salen hacia un tercero y texto que vuelve sin garantías, (4) contenido externo que entra al contexto del agente. El tráfico en el borde se detalla en [Cloudflare y protección perimetral](#t/cloudflare).

**Ejemplo:** al dibujar el diagrama, el equipo nota que la herramienta `obtener_pedido` llama a Aurora con una cuenta de servicio que ve todos los comercios. El límite "agente -> herramientas" no tiene autorización por usuario: ese hallazgo aparece en el papel antes de llegar a producción.

**Por qué importa:** las amenazas viven en los cruces; sin diagrama se pierden justamente los puntos de entrada.

### STRIDE aplicado al asistente

**STRIDE** es un mnemotécnico de seis categorías de amenaza. No es exhaustivo, pero obliga a mirar cada componente y flujo desde seis ángulos. Una fila trabajada por letra para el asistente de soporte:

| Letra | Amenaza | Propiedad | Amenaza concreta en el asistente | Mitigación |
|---|---|---|---|---|
| S | Suplantación (spoofing) | Autenticidad | Alguien usa la API del asistente con un token robado de un comercio | Tokens cortos, sesión HttpOnly, detección de reuso de refresh token |
| T | Manipulación (tampering) | Integridad | Un documento modificado en la base vectorial cambia la política de reprogramación que cita el asistente | Ingesta solo desde fuentes aprobadas, procedencia por fragmento, revisión de cambios |
| R | Repudio | No repudio | Un comercio niega haber pedido una reprogramación hecha por el asistente | Auditoría con usuario, agente, herramienta, parámetros y confirmación en la interfaz |
| I | Divulgación de información | Confidencialidad | Una inyección en una nota lleva al asistente a incluir teléfonos de otros pedidos | Herramientas con permisos del usuario, filtrado por comercio en la consulta, sanitizar URLs de salida |
| D | Denegación de servicio | Disponibilidad | Un script abre 200 conversaciones con páginas enormes y agota la cuota de tokens | Límites por usuario y comercio, tope de tokens por resultado, presupuesto diario |
| E | Elevación de privilegios | Autorización | Un usuario con rol de lectura logra que el asistente ejecute `reprogramar_entrega` | Autorización en el backend de cada herramienta, no en el prompt; herramientas filtradas por rol |

**Ejemplo:** la fila E muestra un patrón frecuente: el prompt de sistema dice "solo los operadores pueden reprogramar", pero la herramienta no verifica el rol. Cualquier usuario que convenza al modelo obtiene el privilegio. La mitigación es que la lista de herramientas que recibe el modelo ya esté filtrada por el rol de la sesión y que la herramienta vuelva a verificarlo.

**Por qué importa:** STRIDE evita que el análisis se reduzca a la amenaza de moda (hoy, la inyección de prompt) y deje fuera el repudio o la denegación de servicio.

### Una sesión de modelado de amenazas de 60 minutos

El modelado de amenazas funciona mejor como una reunión corta y repetible que como un documento enorme:

**Qué llevar:** el documento de diseño, el diagrama de flujo de datos con los límites marcados, la lista de datos que maneja el sistema con su clasificación (PII, interno, público) y las herramientas del agente con sus permisos.

**Quiénes:** entre 4 y 6 personas: quien diseñó el cambio, quienes lo construyen u operan, alguien con mirada de seguridad (no hace falta que sea especialista) y, si hay agentes, alguien que conozca el prompt y las herramientas.

**Agenda:**

1. **Minutos 0 a 10:** quien diseñó recorre el diagrama. Se corrigen flujos que faltan.
2. **Minutos 10 a 40:** se recorre cada límite de confianza con STRIDE. Cada amenaza se anota en una línea: componente, letra, descripción, control existente.
3. **Minutos 40 a 50:** se prioriza (ver el concepto siguiente).
4. **Minutos 50 a 60:** se asigna una mitigación y un responsable a cada amenaza alta o media, y se decide qué riesgo se acepta explícitamente.

**Salida:** lista de amenazas, cada una con mitigación y un ticket con responsable; las aceptadas quedan registradas con motivo y quién las aceptó. Una herramienta nueva del agente es un cambio de diseño y amerita otra sesión.

**Ejemplo:** la sesión sobre la herramienta `leer_url` produce 11 amenazas: 3 altas (exfiltración por URL, SSRF hacia la red interna, inyección indirecta), 5 medias y 3 bajas. Las altas generan 4 tickets bloqueantes para el lanzamiento; una baja ("el proveedor de mapas cambia su HTML") se acepta.

**Por qué importa:** una hora encuentra los problemas cuando arreglarlos cuesta editar un documento, no atender un incidente.

### Priorizar amenazas: probabilidad por impacto

No todas las amenazas merecen el mismo esfuerzo. La forma más simple de ordenarlas es estimar **probabilidad** e **impacto** en una escala de 1 a 3 y multiplicar:

| Amenaza | Probabilidad | Impacto | Puntaje |
|---|---|---|---|
| Inyección indirecta que filtra PII por `leer_url` | 3 (contenido externo, fácil de intentar) | 3 (PII de destinatarios) | 9 |
| Token de comercio robado usado contra la API | 2 | 2 (datos de un comercio) | 4 |
| Documento interno manipulado en la base vectorial | 1 (requiere acceso interno) | 2 | 2 |

Con 7 a 9 se mitiga antes de lanzar; con 4 a 6 se planifica; con 1 a 3 se puede aceptar por escrito. La escala importa menos que aplicarla siempre igual. Cómo se gestiona un riesgo aceptado (dueño, revisión periódica, disparadores) se ve en [Gestión de riesgos](#t/riesgos).

**Ejemplo:** el equipo tiene capacidad para 3 tickets en el sprint. El puntaje deja claro que el primero es restringir `leer_url`, aunque el robo de tokens "suene" más grave.

**Por qué importa:** sin un criterio explícito, se prioriza lo que la persona más insistente de la sala considera grave.

### La mirada de agentes: el modelo como componente no confiable

En el diagrama, el LLM va **del lado no confiable** del límite. No porque el proveedor sea malicioso, sino porque el modelo no distingue de forma confiable entre instrucciones y datos: su salida puede estar influida por cualquier texto que leyó. Tres consecuencias de diseño:

1. **La trifecta letal.** Un agente es especialmente peligroso cuando reúne tres cosas: acceso a datos privados, exposición a contenido no confiable y alguna forma de enviar información hacia afuera. Con las tres, quien controla el contenido puede usar al agente para sacar los datos. Quitar cualquiera de las tres corta ese camino. El detalle de los canales está en [Seguridad de LLMs y agentes](#t/seguridad-agentes).
2. **Capacidades antes que prompts.** "No compartas datos de otros comercios" en el prompt reduce el problema; que la herramienta no pueda devolverlos lo impide. Las amenazas de un agente se modelan sobre sus capacidades (herramientas, permisos, destinos de red), no sobre lo que se le pidió.
3. **La salida del modelo cruza un límite.** Antes de llegar a SQL, a un comando, al navegador o a otra API, se valida como cualquier entrada externa.

**Ejemplo:** el agente de operaciones lee alertas (algunas escritas por integradores externos) y métricas internas, pero sus herramientas son de solo lectura y su salida es un informe para una persona. Tiene dos de los tres ingredientes. La propuesta de sumarle `enviar_mensaje(canal, texto)` con canal libre agrega el tercero; la alternativa que se aprueba es un canal fijo, elegido por código.

**Por qué importa:** cambia la pregunta de "¿el modelo se va a portar bien?", que nadie puede garantizar, a "¿qué puede hacer aunque se porte mal?", que sí se puede revisar.

### Seguridad en el ciclo de desarrollo

Cada etapa del ciclo tiene sus controles:

1. **Revisión de diseño:** modelado de amenazas para cambios que tocan límites de confianza: un endpoint público nuevo, una herramienta nueva del agente, un proveedor nuevo, datos personales nuevos.
2. **Revisión de código:** autorización por recurso, validación de entrada, sinks peligrosos y secretos, con una lista de verificación corta.
3. **Escaneo automatizado en CI:** análisis estático (SAST), dependencias con vulnerabilidades conocidas, secretos e imágenes de contenedor. Para agentes, el dataset de red teaming corre en CI como cualquier evaluación.
4. **Pruebas de penetración (pentest):** un equipo interno o externo intenta atacar el sistema, antes de lanzamientos grandes y de forma periódica; los hallazgos se priorizan igual que el resto.
5. **Operación:** monitoreo de eventos de seguridad, respuesta a incidentes y revisión posterior, para que cada hallazgo termine en un control o una prueba.

**Ejemplo:** un cambio que agrega `reprogramar_entrega` pasa por modelado de amenazas (6 amenazas, 2 altas), revisión de código con foco en autorización, 120 casos nuevos en el dataset de red teaming y un pentest acotado de dos días antes de habilitarlo a todos los comercios.

**Por qué importa:** cada etapa encuentra problemas distintos; ninguna reemplaza a las otras.

### Mapa del capítulo

Este tema da el vocabulario; los demás aplican cada parte:

| Tema | Qué cubre | Límite de confianza principal |
|---|---|---|
| [Autenticación, JWT y OAuth](#t/autenticacion) | Quién llama y en nombre de quién actúa un agente | Usuario -> API, agente -> API |
| [Seguridad de APIs y backend](#t/seguridad-apis) | Autorización por recurso, inyección, SSRF, aislamiento entre comercios | API -> datos |
| [Secretos y cifrado](#t/secretos) | Claves, cifrado y rotación | Servicios -> proveedores |
| [Seguridad en el frontend](#t/seguridad-frontend) | XSS, CSRF, CSP y salida del modelo en el navegador | Navegador |
| [Cloudflare y protección perimetral](#t/cloudflare) | Borde, WAF, DDoS, bots y límites | Internet -> borde |
| [Seguridad de LLMs y agentes](#t/seguridad-agentes) | Inyección de prompt, exfiltración, agencia excesiva | Contenido -> modelo -> herramientas |
| [Cadena de suministro](#t/cadena-suministro) | Dependencias, imágenes, modelos y servidores MCP de terceros | Terceros -> nuestro código |
| [Privacidad y datos personales](#t/privacidad-datos) | PII, retención, minimización y datos en prompts | Datos -> modelo y logs |

**Ejemplo:** en la sesión sobre `reprogramar_entrega`, la suplantación lleva a autenticación, la elevación a seguridad de APIs y la divulgación a seguridad de agentes y privacidad.

**Por qué importa:** cada amenaza encontrada tiene un tema que explica cómo mitigarla.

## Casos prácticos

### Modelar amenazas antes de darle `leer_url` al asistente

**Situación:** producto pide que el asistente lea las páginas de seguimiento que comparten los comercios. El diseño original permite cualquier URL y usa la misma red que el resto del backend.

**Qué se hace:** el diagrama muestra un límite nuevo: internet entra al contexto del agente. STRIDE marca divulgación (exfiltración en la propia URL), elevación (SSRF hacia servicios internos) y denegación de servicio (páginas enormes). Se quita la salida libre: lista permitida de dominios, egreso por un proxy aislado de la red interna y tope de 8.000 tokens por página. Las tres amenazas altas quedan como tickets bloqueantes.

### El control que fallaba abierto

**Situación:** en una revisión de código, el servicio de herramientas del agente consulta el servicio de permisos con un timeout de 200 ms. Si el timeout vence, el código registra una advertencia y deja pasar la llamada "para no degradar la experiencia". Durante un incidente del servicio de permisos, todas las herramientas quedaron sin autorización por 40 minutos.

**Qué se hace:** se aplica fallar cerrado: ante un error o timeout, la herramienta devuelve "no puedo verificar permisos, intenta en unos minutos". Para no perder disponibilidad se cachean las decisiones de permisos 60 segundos y se alerta si las denegaciones por error superan el 1 %.

### La sesión que olvidó el repudio

**Situación:** un comercio reclama que el asistente reprogramó 30 entregas que nadie pidió. Los logs muestran las llamadas a la herramienta, pero no quién confirmó ni desde qué sesión, y el texto del modelo no alcanza como prueba.

**Qué se hace:** se agrega la letra R, que el modelado había pasado por alto. Cada acción con efecto registra usuario, actor (el asistente), herramienta, parámetros, conversación y evento de confirmación en la interfaz, en un almacén de solo escritura con retención de un año.

### Priorizar con poco tiempo antes de un lanzamiento

**Situación:** faltan dos semanas para abrir el asistente a 300 comercios nuevos y la sesión de amenazas dejó 14 hallazgos. El equipo puede resolver 5.

**Qué se hace:** se puntúa cada hallazgo con probabilidad por impacto. Los 4 con puntaje 9 o 6 (autorización por comercio en dos herramientas, límites de tokens por comercio, sanitizar URLs de salida) se resuelven; uno de puntaje 4 se mitiga parcialmente con una alerta. Los restantes se aceptan por escrito con dueño y fecha de revisión, y entran al registro de riesgos.

## Errores comunes

- **Modelar amenazas una sola vez, al principio.** Una herramienta nueva, un proveedor nuevo o un dato nuevo cambian el diagrama; la sesión se repite en cada cambio de ese tipo.
- **Confiar en el prompt como control de seguridad.** Las reglas en el prompt orientan al modelo, pero el límite real lo ponen los permisos de las herramientas y la red.
- **Dejar al LLM del lado confiable del diagrama.** Su salida se valida como cualquier entrada externa antes de llegar a SQL, comandos, el navegador u otra API.
- **Controles que fallan abiertos "por disponibilidad".** Un timeout de autorización que deja pasar convierte una caída en un incidente de seguridad; se falla cerrado y se compensa con caché y alertas.
- **Listas de amenazas sin dueño ni ticket.** Un documento con 20 hallazgos y ningún responsable no reduce ningún riesgo; cada amenaza termina en un ticket o en una aceptación explícita.

## Para discutir en equipo

- Si dibujamos hoy el diagrama de flujo de datos del asistente, ¿cuántos límites de confianza encontramos que no tienen un control explícito?
- ¿Cuáles de nuestros agentes reúnen los tres ingredientes de la trifecta letal, y cuál podríamos quitar con menos costo?
- ¿Qué controles nuestros fallan abiertos cuando una dependencia no responde, y cuál sería el costo de que fallen cerrados?
- ¿Qué tipo de cambio debería disparar una sesión de modelado de amenazas, y quién decide que hace falta?
- ¿Qué riesgos tenemos aceptados de hecho sin que nadie los haya aceptado por escrito?
