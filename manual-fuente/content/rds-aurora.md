---
slug: rds-aurora
titulo: RDS y Aurora
resumen: Bases de datos relacionales gestionadas de AWS, con alta disponibilidad, réplicas, backups y recuperación a un punto en el tiempo, y cómo operarlas sin sorpresas.
lectura: 13
---

## La idea central

Operar una base de datos PostgreSQL propia implica instalarla, parcharla, configurar réplicas, hacer backups, probar que se pueden restaurar y estar despierto cuando el disco se llena. **RDS** (Relational Database Service) es el servicio de AWS que se encarga de buena parte de ese trabajo: el equipo elige motor, tamaño y configuración, y AWS opera las máquinas, aplica parches, toma backups y hace el failover cuando algo falla. **Aurora** es una variante de RDS con un almacenamiento distribuido propio, diseñado para que la base sobreviva fallas de hardware y de zona con menos pérdida de datos y menos tiempo de corte.

"Gestionada" no significa "sin preocupaciones". Sigue siendo nuestra responsabilidad elegir el tamaño, diseñar el esquema y las consultas, controlar las conexiones, decidir cuántos días de backups guardar, probar las restauraciones y lograr que las aplicaciones se reconecten bien después de un failover. En Rumbo, Aurora PostgreSQL guarda pedidos, asignaciones, transportistas y comercios: si la base no responde, no se asignan pedidos.

## Conceptos

### RDS: motores gestionados

RDS ofrece varios motores: PostgreSQL, MySQL, MariaDB, Oracle y SQL Server. En todos, el modelo es parecido:

1. Se elige una **clase de instancia** (CPU y memoria) y un **almacenamiento** (volúmenes EBS de cierto tamaño y rendimiento).
2. AWS crea la instancia en una subred privada de la VPC y entrega un **endpoint** DNS para conectarse.
3. AWS se encarga del sistema operativo, de los parches del motor (en ventanas de mantenimiento que elegimos), de los backups automáticos y del monitoreo básico.

Lo que **no** se tiene: acceso al sistema operativo ni permisos de superusuario completos. Ciertas extensiones o configuraciones no están disponibles, y los parámetros se cambian mediante **grupos de parámetros**.

En RDS clásico, el almacenamiento es un volumen EBS ligado a la instancia, en una sola zona. La alta disponibilidad se logra con una copia en otra zona (Multi-AZ, más abajo).

### Aurora: almacenamiento replicado y sus variantes

Aurora (compatible con PostgreSQL o MySQL) separa el cómputo del almacenamiento:

- El **almacenamiento** es un volumen compartido distribuido en **tres zonas de disponibilidad**, con **seis copias** de cada dato (dos por zona). Una escritura se confirma cuando cuatro de las seis copias la registraron. Así sobrevive la pérdida de una zona entera sin perder datos, y la lectura sigue funcionando incluso con tres copias perdidas.
- El **cómputo** son las instancias: una **escritora** y hasta 15 **réplicas de lectura**, todas leyendo del mismo volumen. Como las réplicas no copian datos sino que comparten almacenamiento, su retraso suele ser de milisegundos, y se pueden agregar en minutos sin copiar toda la base.
- El volumen crece automáticamente según se necesita.

**Failover en Aurora:** si la instancia escritora falla, Aurora promueve una réplica a escritora. Como el almacenamiento ya es compartido, no hay que copiar nada: el corte suele ser del orden de 30 segundos o menos. Si no hay réplicas, Aurora tiene que crear una instancia nueva, y el corte es de varios minutos. Por eso producción siempre debe tener al menos una réplica en otra zona.

Variantes importantes:

- **Aurora Serverless v2:** la capacidad se mide en ACU (unidades de capacidad) y escala automáticamente en pasos finos según la carga, entre un mínimo y un máximo configurados. Útil para cargas variables o entornos que pasan mucho tiempo ociosos.
- **Aurora Global Database:** replica el almacenamiento a otras regiones con retraso típico de alrededor de un segundo. Permite lecturas locales en otra región y recuperación ante la caída de una región entera, con un costo y una complejidad bastante mayores.

### Multi-AZ y failover

**Multi-AZ** significa tener una copia de la base lista en otra zona para tomar el control si la principal falla. En RDS clásico se mantiene una instancia **standby** con replicación síncrona: cada escritura se confirma solo cuando llegó a las dos zonas. En Aurora, el equivalente es tener réplicas en otras zonas sobre el almacenamiento compartido.

Cuando hay failover, el **endpoint DNS** de la base pasa a apuntar a la nueva instancia. Esto tiene una consecuencia práctica clave: las aplicaciones que tienen conexiones abiertas las pierden, y las que cachean la resolución DNS más tiempo del debido siguen intentando conectarse a la IP vieja.

**Ejemplo de línea de tiempo:**

1. 18:30:00 la escritora deja de responder.
2. 18:30:10 Aurora detecta la falla e inicia la promoción.
3. 18:30:25 la réplica de la zona b ya acepta escrituras; el DNS del endpoint de clúster se actualiza (TTL de 5 segundos).
4. 18:30:30 las aplicaciones bien configuradas ya se reconectaron. Las que cachean DNS por minutos siguen fallando.

### Réplicas de lectura y retraso

Las **réplicas de lectura** sirven para descargar consultas de solo lectura de la escritora: reportes, el dashboard de operaciones, consultas del agente interno. Aurora ofrece un **endpoint de lectura** que reparte conexiones entre réplicas.

El riesgo es el **retraso de replicación** (replica lag): la réplica puede estar algunos milisegundos (en Aurora) o segundos (en RDS clásico, bajo carga) detrás de la escritora. Una aplicación que escribe y lee inmediatamente después desde la réplica puede no ver su propia escritura.

**Ejemplo:** el servicio de asignación asigna el pedido 8812 al transportista 77 en la escritora y, 5 ms después, la API de seguimiento lee el pedido desde una réplica con 20 ms de retraso: muestra "sin asignar". Solución: las lecturas que deben ver la escritura propia van a la escritora; las réplicas se reservan para lecturas que toleran unos segundos de antigüedad.

### Backups y recuperación a un punto en el tiempo

RDS y Aurora toman **backups automáticos**: un snapshot diario más los registros de transacciones (WAL en PostgreSQL) continuos. Con eso se puede hacer **recuperación a un punto en el tiempo** (PITR, point-in-time recovery): crear una base nueva con el estado exacto de cualquier segundo dentro del período de retención (configurable, hasta 35 días).

Puntos importantes:

- La restauración **crea una base nueva**; no sobrescribe la existente. Luego hay que decidir si se migra la aplicación a la nueva base o se copian los datos necesarios a la original.
- Restaurar lleva tiempo: de minutos a horas según el tamaño. Aurora también ofrece **backtrack** (solo en MySQL) y **clones** rápidos que comparten almacenamiento.
- Los **snapshots manuales** no expiran solos; sirven para conservar un estado antes de una migración riesgosa.
- Para protegerse de un error humano o de un compromiso de la cuenta, conviene copiar backups a otra cuenta o región (AWS Backup lo facilita).

### RPO y RTO

Dos métricas definen cuánto daño se tolera en un desastre:

- **RPO** (Recovery Point Objective): cuántos datos se pueden perder, medido en tiempo. "RPO de 5 minutos" significa que, tras recuperarse, pueden faltar como máximo los últimos 5 minutos de datos.
- **RTO** (Recovery Time Objective): cuánto tiempo puede estar el sistema sin funcionar hasta recuperarse.

**Ejemplo con Rumbo:**

| Escenario | RPO típico | RTO típico | Mecanismo |
|---|---|---|---|
| Falla de la instancia escritora | 0 | Menos de 1 minuto | Failover a réplica de Aurora |
| Caída de una zona | 0 | Menos de 1 minuto | Almacenamiento en 3 zonas + réplica en otra zona |
| Borrado accidental de datos | Segundos (elegimos el punto) | 30 a 90 minutos | PITR a una base nueva + copia de los datos |
| Caída de toda la región | Alrededor de 1 segundo | Minutos a decenas de minutos | Aurora Global Database con failover manual |
| Caída de región sin Global Database | Horas | Horas | Restaurar backup copiado a otra región |

Las cifras son órdenes de magnitud; el RTO real depende sobre todo de cuánto se ensayó el procedimiento. **Por qué importa:** RPO y RTO se acuerdan con el negocio antes de elegir la tecnología. Un RTO de 1 minuto ante la caída de una región cuesta muchísimo más que uno de 4 horas, y el equipo tiene que saber cuál se prometió.

### RDS Proxy

Cada conexión a PostgreSQL consume memoria en el servidor (del orden de varios MB por proceso), y el número máximo de conexiones depende del tamaño de la instancia. Cuando hay muchos pods, cada uno con su pool, el total se dispara.

**RDS Proxy** es un pool de conexiones gestionado que se sitúa entre las aplicaciones y la base: las aplicaciones abren muchas conexiones al proxy, y el proxy las multiplexa sobre un número menor de conexiones reales a la base. Además, durante un failover, el proxy mantiene las conexiones de las aplicaciones y redirige a la nueva escritora, acortando el corte percibido, y puede autenticar con IAM en lugar de contraseñas.

Limitaciones: agrega una pequeña latencia, y ciertas características de sesión (por ejemplo, sentencias preparadas o variables de sesión) "fijan" la conexión al cliente y reducen la multiplexación. Una alternativa autogestionada es PgBouncer.

### Cifrado en reposo

RDS y Aurora cifran el almacenamiento, los backups, los snapshots y las réplicas con claves de **KMS**. Dos detalles importantes:

- El cifrado se decide **al crear** la base. Para cifrar una base existente sin cifrar hay que tomar un snapshot, copiarlo cifrado y restaurarlo como base nueva.
- Usar una clave KMS administrada por el equipo (no la por defecto) permite controlar quién puede usarla y compartir snapshots con otras cuentas de forma controlada.

El cifrado en tránsito (TLS) se configura aparte y conviene exigirlo desde los parámetros del servidor. Más detalle en [Secretos y cifrado](#t/secretos).

### Mantenimiento, actualizaciones y despliegue azul-verde

Hay dos tipos de actualización del motor:

- **Versiones menores** (por ejemplo, de 16.3 a 16.4): parches de seguridad y correcciones, compatibles. Se pueden aplicar automáticamente en la ventana de mantenimiento, con un corte breve.
- **Versiones mayores** (por ejemplo, de 15 a 16): pueden cambiar comportamientos, planes de consulta y compatibilidad de extensiones. Requieren pruebas.

Para las mayores, RDS y Aurora ofrecen **despliegues azul-verde**: se crea una copia ("verde") sincronizada con la producción ("azul") mediante replicación lógica, se actualiza la verde a la nueva versión, se prueba, y luego se hace el **switchover**: se bloquean las escrituras en azul, se espera que verde esté al día y se intercambian los endpoints. El corte suele ser de alrededor de un minuto o menos, y la base azul queda disponible para volver atrás si algo sale mal.

### Monitoreo

Métricas que conviene vigilar siempre, con alarmas:

- **CPU y memoria libre** de cada instancia.
- **Conexiones** (`DatabaseConnections`) frente al máximo configurado. Alarma al 80 %.
- **Retraso de réplicas** (`AuroraReplicaLag` o `ReplicaLag`).
- **Latencia de lectura y escritura** e IOPS.
- **Deadlocks** y edad de la transacción más vieja (en PostgreSQL, una transacción abierta durante horas impide limpiar filas muertas).

**Performance Insights** muestra la carga de la base desglosada por consulta y por tipo de espera (CPU, I/O, bloqueos). Es la herramienta para responder "¿qué consulta está saturando la base ahora mismo?". Complementa los índices y el diseño de consultas tratados en [Bases de datos](#t/bases-de-datos).

## Casos prácticos

### Failover en hora pico con DNS cacheado

**Situación:** a las 19:10 de un viernes la instancia escritora de Aurora falla. Aurora promueve la réplica en 25 segundos, pero el servicio de asignación sigue con errores durante 6 minutos. La causa: el runtime cacheaba la resolución DNS sin respetar el TTL, y el pool de conexiones mantenía conexiones muertas que no se descartaban hasta un timeout largo.
**Qué se hace:** se configura el cliente para respetar el TTL del DNS (o un máximo de unos segundos), el pool valida conexiones y descarta las que fallan, y los timeouts de conexión y de consulta son cortos (por ejemplo, 2 s y 1 s para asignación). Se evalúa poner RDS Proxy delante, que absorbe el cambio de escritora. Y lo más importante: se prueba el failover en staging forzándolo desde la consola, y se mide cuánto tarda cada servicio en recuperarse.

### Borrado accidental a las 15:02 y restauración a las 15:01

**Situación:** a las 15:02:30 un script de mantenimiento ejecuta un `DELETE` sin el filtro correcto y borra 40.000 asignaciones del día en la tabla de producción. La aplicación sigue funcionando, pero el historial del día desapareció.
**Qué se hace:** no se restaura la base de producción entera a las 15:01, porque se perderían todas las escrituras legítimas posteriores (pedidos nuevos, entregas). En cambio: (1) se crea una base nueva con PITR a las 15:01:00; (2) se extraen de ella solo las filas borradas; (3) se reinsertan en producción, verificando conflictos; (4) se borra la base temporal. El RPO efectivo es cero para el resto de los datos y el RTO, del orden de una hora, la mayor parte esperando la restauración. Como prevención, los scripts de mantenimiento corren en transacciones con conteo esperado y revisión previa, y el rol que usan no tiene `DELETE` sobre tablas críticas.

### Conexiones agotadas por el autoescalado

**Situación:** en un pico, el HPA escala el servicio de asignación de 10 a 60 pods. Cada pod abre un pool de 20 conexiones: 1.200 en total, más que el máximo de la instancia. Los pods nuevos fallan al arrancar, la readiness no pasa, y la escritora además se degrada por la memoria consumida por tantas conexiones.
**Qué se hace:** el cálculo de conexiones pasa a ser parte del diseño del autoescalado: `pods máximos × tamaño del pool` debe quedar por debajo del máximo de la base, con margen para otros servicios. Se reduce el pool por pod (rara vez se necesitan 20 conexiones si las consultas duran milisegundos), se pone RDS Proxy o PgBouncer para multiplexar, y se alarma al 80 % de conexiones. Escalar pods sin escalar la base solo traslada el cuello de botella (ver [Contenedores, ECS y EKS](#t/contenedores)).

### Actualización de versión mayor de PostgreSQL

**Situación:** la versión de PostgreSQL de Aurora en producción se acerca al fin de soporte estándar y hay que subir de versión mayor. La base tiene 2 TB y la asignación no tolera cortes largos.
**Qué se hace:** primero, se revisa la compatibilidad de extensiones y se restaura un clon de producción con la versión nueva para correr la batería de pruebas y comparar planes de las consultas más frecuentes (Performance Insights ayuda a elegirlas). Luego se crea un despliegue azul-verde, se deja la verde sincronizada unos días observando el retraso de replicación, y se hace el switchover en un horario de baja demanda con el equipo atento. Se mantiene la base azul unos días como camino de vuelta. Después del cambio, se ejecuta `ANALYZE` para regenerar estadísticas, porque estadísticas desactualizadas pueden degradar planes justo después de la actualización.

## Errores comunes

- **Producción sin réplica en otra zona.** En Aurora, sin réplica el failover implica crear una instancia nueva y tarda minutos. Siempre al menos una réplica en otra zona.
- **No probar nunca una restauración.** Un backup que nadie restauró es una hipótesis. Ensayar PITR periódicamente y medir el RTO real.
- **Leer desde réplicas lo que se acaba de escribir.** El retraso, aunque sea de milisegundos, produce inconsistencias visibles. Enviar a la escritora las lecturas que necesitan ver la escritura propia.
- **Pools de conexiones grandes multiplicados por muchos pods.** El autoescalado agota la base. Calcular el total máximo y usar un proxy.
- **Clientes que cachean DNS o no tienen timeouts.** Convierten un failover de 30 segundos en minutos de errores. Configurar TTL, validación de conexiones y timeouts cortos.
- **Postergar las versiones mayores.** Cuanto más se espera, más grande es el salto y mayor el riesgo. Planificarlas con tiempo y con azul-verde.

## Para discutir en equipo

- ¿Qué RPO y RTO tenemos acordados para la base de pedidos, y cuándo los verificamos por última vez con un ensayo?
- ¿Cuánto tardó cada servicio en recuperarse en el último failover, y por qué hubo diferencias?
- ¿Qué consultas leen hoy desde réplicas y cuáles de ellas podrían verse afectadas por el retraso?
- ¿Vale la pena Aurora Global Database para Rumbo, o un RTO de horas ante la caída de una región es aceptable?
- ¿Cuál es el número máximo de conexiones que el autoescalado puede generar hoy en el peor caso?
