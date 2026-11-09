---
slug: bases-de-datos
titulo: Bases de datos
resumen: Transacciones, aislamiento, locks, índices, conexiones y migraciones en PostgreSQL, con foco en los errores que aparecen bajo concurrencia y en producción.
lectura: 15
---

## La idea central

Una base de datos relacional como Aurora PostgreSQL es, en el fondo, un acuerdo sobre qué pasa cuando muchas personas tocan los mismos datos a la vez. En desarrollo, con un solo usuario, casi cualquier código funciona. Los problemas aparecen en producción: dos procesos leen la capacidad de un transportista al mismo tiempo y uno pisa al otro, una migración bloquea una tabla durante minutos, un reporte pesado frena las escrituras de pedidos.

Por eso este tema no trata de SQL básico sino de las garantías que da la base y de sus límites: qué protege una transacción y qué no, cómo elegir un índice que realmente se use, cómo cambiar el esquema sin detener el servicio y qué tipos de datos evitan errores silenciosos. La base es también el lugar donde conviene poner las invariantes del negocio: una restricción en la base se cumple aunque haya un bug en cualquiera de los servicios que escriben.

## Conceptos

### ACID

- **Atomicidad:** una transacción se aplica entera o no se aplica. Si la asignación actualiza el pedido e inserta en la outbox, o se hacen ambas cosas o ninguna (ver el patrón outbox en [Sistemas distribuidos](#t/sistemas-distribuidos)).
- **Consistencia:** la transacción lleva la base de un estado válido a otro, respetando las restricciones declaradas (claves foráneas, únicas, `CHECK`). Solo protege lo que se declaró: si la regla "la capacidad no puede ser negativa" no está como `CHECK`, la base no la conoce.
- **Aislamiento:** las transacciones concurrentes no se ven a medio hacer. Cuánto se aíslan depende del nivel elegido (ver abajo), y es la propiedad que más sorpresas da.
- **Durabilidad:** una vez confirmada, la transacción sobrevive a una caída. En Aurora, la escritura se replica en varias zonas antes de confirmar.

### Niveles de aislamiento y sus anomalías

Aislar totalmente las transacciones es caro, así que las bases ofrecen niveles que permiten ciertas **anomalías** a cambio de más concurrencia. En PostgreSQL:

| Nivel | Qué ve cada consulta | Anomalías posibles |
|---|---|---|
| Read Committed (por defecto) | Lo confirmado al inicio de **cada sentencia** | Lectura no repetible, actualización perdida, write skew |
| Repeatable Read | Una foto fija desde el inicio de la **transacción** | Write skew; las actualizaciones concurrentes de la misma fila fallan y hay que reintentar |
| Serializable | Como si las transacciones corrieran de a una | Ninguna; a cambio, más transacciones abortadas que hay que reintentar |

Las anomalías clave:

- **Lectura no repetible:** la misma consulta, dos veces dentro de la transacción, devuelve valores distintos porque otro confirmó entre medio.
- **Actualización perdida:** dos transacciones leen un valor, ambas calculan uno nuevo en la aplicación y ambas escriben; la segunda borra el efecto de la primera.
- **Write skew:** dos transacciones leen el mismo conjunto, cada una escribe en filas distintas y juntas violan una regla. Por ejemplo, la regla "al menos un supervisor de guardia por zona": dos supervisores consultan, ven que hay otro y ambos se quitan.

**Ejemplo de actualización perdida:** un transportista tiene `capacidad_libre = 3`. Dos procesos de asignación corren en paralelo con Read Committed:

```sql
-- Proceso A                              -- Proceso B
SELECT capacidad_libre FROM transportistas
 WHERE id = 't-7';        -- lee 3
                                          SELECT capacidad_libre FROM transportistas
                                           WHERE id = 't-7';        -- lee 3
-- la aplicación calcula 3 - 1 = 2
UPDATE transportistas SET capacidad_libre = 2
 WHERE id = 't-7';
COMMIT;
                                          -- la aplicación calcula 3 - 1 = 2
                                          UPDATE transportistas SET capacidad_libre = 2
                                           WHERE id = 't-7';
                                          COMMIT;
-- Resultado: 2. Debería ser 1. Se asignaron dos pedidos y se descontó uno.
```

La forma más simple de evitarlo es dejar que la base haga el cálculo de forma atómica y verifique la regla:

```sql
UPDATE transportistas
   SET capacidad_libre = capacidad_libre - 1
 WHERE id = 't-7' AND capacidad_libre > 0
RETURNING capacidad_libre;
-- 0 filas devueltas: no había capacidad, no se asigna.
```

Cuando la lógica es más compleja que una resta, se usan locks.

### Lock pesimista: SELECT FOR UPDATE

El lock pesimista asume que habrá conflicto y bloquea la fila al leerla. Las demás transacciones que quieran bloquearla esperan hasta el `COMMIT`.

```sql
BEGIN;
SELECT capacidad_libre, zona_id, estado
  FROM transportistas
 WHERE id = 't-7'
   FOR UPDATE;           -- B espera aquí hasta que A termine
-- lógica de negocio en la aplicación
UPDATE transportistas SET capacidad_libre = 1 WHERE id = 't-7';
INSERT INTO asignaciones (pedido_id, transportista_id) VALUES ('p-123', 't-7');
COMMIT;
```

Es simple y correcto, pero tiene costos: la transacción debe ser corta (nunca se llama a un servicio externo con el lock tomado), y si dos transacciones bloquean filas en distinto orden pueden quedar en **deadlock**; PostgreSQL detecta el ciclo y aborta una. Se evita bloqueando siempre en el mismo orden (por ejemplo, por id). Variantes útiles: `NOWAIT` (falla en vez de esperar) y `SKIP LOCKED` (saltea filas bloqueadas, ideal para que varios trabajadores tomen tareas de una tabla sin pisarse).

### Lock optimista: columna de versión

El lock optimista asume que el conflicto es raro: no bloquea al leer, pero verifica al escribir que nadie cambió la fila.

```sql
SELECT capacidad_libre, version FROM transportistas WHERE id = 't-7';
-- devuelve capacidad_libre = 3, version = 41

UPDATE transportistas
   SET capacidad_libre = 2, version = version + 1
 WHERE id = 't-7' AND version = 41;
-- 1 fila: éxito. 0 filas: alguien cambió la fila, se relee y se reintenta.
```

Conviene cuando los conflictos son poco frecuentes y la lógica entre leer y escribir puede ser larga (incluso con interacción del usuario, como un operador editando un pedido en un panel). Con mucha contención sobre la misma fila, los reintentos se multiplican y el pesimista rinde más.

### Índices B-tree y compuestos

Un índice B-tree es una estructura ordenada que permite encontrar filas sin recorrer toda la tabla: con 100 millones de pedidos, pasar de leer todo a unas pocas páginas. Cada índice acelera lecturas pero encarece cada escritura (hay que actualizarlo) y ocupa espacio.

En un **índice compuesto** el orden de las columnas importa. Un índice en `(comercio_id, estado, creado_en)` sirve para filtrar por `comercio_id`, por `comercio_id` y `estado`, o por los tres; **no** sirve para filtrar solo por `estado`, porque está ordenado primero por comercio. La regla práctica: primero las columnas de igualdad, después la de rango u orden.

```sql
-- Consulta frecuente del panel de comercios
SELECT id, estado, creado_en FROM pedidos
 WHERE comercio_id = 'c-55' AND estado = 'en_camino'
 ORDER BY creado_en DESC LIMIT 50;

CREATE INDEX CONCURRENTLY idx_pedidos_comercio_estado_fecha
    ON pedidos (comercio_id, estado, creado_en DESC);
```

Otros tipos útiles: **índices parciales** (`WHERE estado <> 'entregado'`, que indexan solo los pedidos activos, una fracción pequeña de la tabla) y **únicos parciales**, que expresan invariantes como "un pedido tiene a lo sumo una asignación activa".

### EXPLAIN

`EXPLAIN` muestra el plan que eligió el optimizador; `EXPLAIN (ANALYZE, BUFFERS)` además ejecuta la consulta y muestra tiempos y filas reales. Qué mirar:

- `Seq Scan` sobre una tabla grande donde se esperaba un índice.
- Diferencias grandes entre filas estimadas y reales (`rows=10` estimadas contra `rows=200000` reales): las estadísticas están desactualizadas o los datos están sesgados, y el optimizador elige mal.
- Nodos `Sort` o `Hash` que se desbordan a disco.
- Muchas páginas leídas (`Buffers: shared read`) para pocas filas devueltas.

`ANALYZE` ejecuta la consulta, así que no se usa sin cuidado sobre un `UPDATE` o `DELETE` en producción (o se envuelve en una transacción con `ROLLBACK`).

### Pool de conexiones: PgBouncer y RDS Proxy

Cada conexión de PostgreSQL es un proceso del servidor que consume memoria (del orden de varios MB). Con 60 pods y 20 conexiones cada uno, son 1.200 conexiones, la mayoría ociosas, y la base se degrada por la cantidad de procesos antes de que la consulta sea el problema.

Un **pooler** como PgBouncer o RDS Proxy mantiene pocas conexiones reales hacia la base y las presta a muchas conexiones de clientes. En modo **transaction pooling**, una conexión real se asigna solo durante una transacción, y 1.200 conexiones de clientes pueden atenderse con 100 reales. El costo: se pierden las características que dependen de la sesión (sentencias preparadas con nombre en versiones antiguas, `SET` de sesión, locks asesores de sesión, `LISTEN`). RDS Proxy además acelera los failovers, porque mantiene las conexiones de los clientes mientras cambia el destino. Ver [RDS y Aurora](#t/rds-aurora).

### Migraciones sin downtime: expandir y contraer

Un cambio de esquema en producción convive con al menos dos versiones del código (la vieja y la nueva durante el deploy gradual). La técnica de **expandir y contraer** divide un cambio incompatible en pasos donde cada uno es compatible con el código que corre en ese momento:

1. **Expandir:** agregar lo nuevo (columna, tabla, índice) sin quitar nada. Las columnas nuevas son anulables o tienen un default constante, lo que en PostgreSQL moderno no reescribe la tabla.
2. **Escritura dual:** desplegar código que escribe en lo viejo y en lo nuevo.
3. **Backfill:** copiar los datos históricos en lotes pequeños (por ejemplo, 5.000 filas por transacción con pausas), para no generar transacciones largas, picos de replicación ni bloqueos.
4. **Cambiar lecturas:** desplegar código que lee de lo nuevo. Verificar con métricas o comparaciones.
5. **Dejar de escribir lo viejo:** desplegar código que solo usa lo nuevo.
6. **Contraer:** eliminar lo viejo, cuando ya no hay código que lo use (incluidos jobs batch y consultas de analítica).

Detalles que causan incidentes: `CREATE INDEX` sin `CONCURRENTLY` bloquea escrituras durante toda la construcción; cualquier `ALTER TABLE` necesita un lock exclusivo, aunque sea breve, y si hay una transacción larga en curso queda esperando y bloquea a todos los que vienen detrás. Por eso las migraciones fijan `SET lock_timeout = '3s'` y se reintentan si no consiguen el lock.

### OLTP frente a OLAP

**OLTP** (procesamiento transaccional) son muchas operaciones pequeñas que tocan pocas filas por clave: crear un pedido, asignarlo, actualizar su estado. **OLAP** (procesamiento analítico) son pocas consultas que recorren millones de filas para agregar: entregas a tiempo por zona y semana del último año. Aurora PostgreSQL está optimizada para OLTP, con almacenamiento por filas; los almacenes analíticos usan almacenamiento por columnas, que lee solo las columnas necesarias y comprime mucho mejor.

Mezclar ambos en la misma base es una fuente clásica de incidentes: una consulta analítica consume CPU, memoria y E/S, y además una transacción larga impide que PostgreSQL limpie versiones viejas de filas (el proceso de *vacuum*), con lo que las tablas e índices se inflan y todo se vuelve más lento.

### Particionado de tablas por fecha

PostgreSQL permite **particionar** una tabla declarativamente: `pedidos` se divide en `pedidos_2026_10`, `pedidos_2026_11`, etc., según `creado_en`. Las consultas que filtran por fecha leen solo las particiones relevantes (*partition pruning*), los índices de cada partición son más chicos, y borrar datos viejos es un `DROP` o `DETACH` de una partición en lugar de un `DELETE` masivo que genera bloat y carga de replicación.

Condiciones: la clave de partición debe aparecer en la clave primaria y en las restricciones únicas, y las consultas que no filtran por fecha recorren todas las particiones. Conviene particionar cuando la tabla es grande, crece con el tiempo y casi todas las consultas filtran por fecha. Las particiones futuras se crean por adelantado con un job.

### Tipos de datos correctos

- **No usar `float` o `double` para cantidades exactas.** Son aproximaciones binarias: `0.1 + 0.2` da `0.30000000000000004`. Para pesos declarados de paquetes, volúmenes de carga o cualquier valor que se sume, compare o redondee con reglas, se usa `numeric(p, s)` o enteros en la unidad mínima (gramos, metros). Coordenadas o scores de un modelo sí pueden ser `double`.
- **Timestamps con zona horaria.** `timestamptz` guarda un instante absoluto (internamente en UTC) y lo convierte al mostrarlo. `timestamp` sin zona guarda un "reloj de pared" sin contexto: si un servicio escribe hora local y otro UTC, la base no tiene forma de saberlo. Para instantes (creado, entregado, ETA) siempre `timestamptz`.
- **Enums o tablas de referencia** para estados, no texto libre, para que `'Entregado'` y `'entregado'` no convivan.
- **Identificadores:** `bigint` o UUID; un `int` de 32 bits se agota alrededor de los 2.100 millones, y migrar una clave primaria en una tabla grande es una de las migraciones más caras que hay.

## Casos prácticos

### Dos procesos actualizan la capacidad de un transportista

**Situación:** un transportista con capacidad para 4 paquetes termina con 6 asignados. Los logs muestran dos asignaciones confirmadas con 3 ms de diferencia, ambas habiendo leído `capacidad_libre = 1`. Es la actualización perdida del ejemplo: lectura en la aplicación, cálculo y escritura del valor absoluto.

**Qué se hace:** la asignación se reescribe como `UPDATE ... SET capacidad_libre = capacidad_libre - 1 WHERE id = $1 AND capacidad_libre > 0 RETURNING ...`, dentro de la misma transacción que inserta la asignación y el evento en la outbox. Si el `UPDATE` no devuelve filas, se pasa al siguiente candidato. Se agrega `CHECK (capacidad_libre >= 0)` como red de seguridad: si algún otro camino de código intenta lo mismo, la base lo rechaza. Se descarta subir todo a Serializable porque el resto de las operaciones no lo necesita y aumentaría los reintentos.

### Renombrar una columna en producción

**Situación:** la columna `pedidos.direccion` debe pasar a llamarse `direccion_destino` porque se agrega `direccion_retiro`. Un `ALTER TABLE ... RENAME COLUMN` es instantáneo, pero el código que corre en ese momento sigue usando el nombre viejo y empieza a fallar en cuanto se ejecuta, y el deploy gradual hace imposible cambiar ambos al mismo tiempo.

**Qué se hace:** expandir y contraer en seis pasos:

1. Migración: `ALTER TABLE pedidos ADD COLUMN direccion_destino text;` con `lock_timeout`.
2. Deploy: el código escribe en ambas columnas.
3. Backfill en lotes: `UPDATE pedidos SET direccion_destino = direccion WHERE id BETWEEN $1 AND $2 AND direccion_destino IS NULL;`
4. Deploy: el código lee `direccion_destino`; se verifica que no haya filas con `direccion_destino` nulo y `direccion` con valor.
5. Deploy: el código deja de escribir `direccion`. Se revisan jobs batch, consultas de analítica y el CDC hacia el lago de datos, que también usan la columna.
6. Migración final, días después: `ALTER TABLE pedidos DROP COLUMN direccion;`

Como la columna contiene PII, el backfill se ejecuta con el mismo control de acceso que la aplicación y sin volcar valores a los logs.

### Reporte analítico que frena la base primaria

**Situación:** un analista corre contra la primaria de Aurora una consulta de entregas a tiempo por zona y hora del último año. La consulta dura 25 minutos, el CPU sube al 90%, la asignación ve su p99 de escritura pasar de 4 a 60 ms y, por la transacción larga, el vacuum no puede limpiar y las tablas de pedidos se inflan.

**Qué se hace:** a corto plazo, se cancela la consulta (`pg_cancel_backend`) y se fija `statement_timeout` para el rol de analítica. A mediano plazo, analítica deja de consultar la base transaccional: los datos llegan al lago de datos por CDC (ver [Event streaming](#t/event-streaming)) y se consultan con un motor por columnas. Como paso intermedio, se habilita una réplica de lectura dedicada a reportes, con la advertencia de que una consulta muy larga en una réplica también puede generar presión de replicación. Se separan los usuarios de base por uso para que el control de acceso y los límites sean distintos.

### Timestamps sin zona horaria que rompen los ETA

**Situación:** la columna `eta_estimada` es `timestamp` sin zona. El servicio de ETA escribe en UTC; un servicio heredado de un cliente grande escribe en hora local (UTC−3). Los destinatarios de ese cliente ven ETA tres horas desplazados, y el monitoreo de entregas a tiempo marca como tarde pedidos que llegaron bien. El modelo, además, se reentrenó con esas etiquetas incorrectas.

**Qué se hace:** se define que todo instante se guarda como `timestamptz` y se convierte a la zona del destinatario solo al mostrar. La migración sigue el patrón de expandir y contraer: nueva columna `eta_estimada_tz timestamptz`, escritura dual en la que cada productor declara explícitamente su zona, y backfill que interpreta las filas antiguas según el servicio que las escribió (dato que estaba en la columna `origen`). Se corrigen las etiquetas de entrenamiento afectadas y se vuelve a entrenar. Para evitar la repetición, el servidor de base fija `timezone = 'UTC'` y una regla en la revisión de migraciones rechaza columnas `timestamp` sin zona.

## Errores comunes

- **Leer, calcular en la aplicación y escribir un valor absoluto.** Produce actualizaciones perdidas; se usa un `UPDATE` atómico, un lock o una versión.
- **Confiar solo en la lógica de la aplicación para las invariantes.** Basta un bug en otro servicio para violarlas; se declaran como `CHECK`, únicas o claves foráneas.
- **Índices compuestos con el orden de columnas equivocado.** No se usan para la consulta pensada; se verifica con `EXPLAIN` antes de crearlos.
- **Migraciones en un solo paso o sin `lock_timeout`.** Rompen el código en curso o bloquean la tabla detrás de una transacción larga; se usa expandir y contraer.
- **Consultas analíticas sobre la primaria transaccional.** Degradan las escrituras y frenan el vacuum; se derivan a un almacén analítico.
- **`float` para cantidades exactas y `timestamp` sin zona para instantes.** Generan errores silenciosos y difíciles de rastrear; se usan `numeric` o enteros y `timestamptz`.

## Para discutir en equipo

- ¿Qué invariantes de negocio hoy solo viven en el código y podríamos declarar en la base?
- ¿Dónde preferimos lock pesimista y dónde optimista, según cuánta contención real tiene cada tabla?
- ¿Qué tablas nuestras van a necesitar particionado en un año, y qué consultas no filtran por fecha?
- ¿Cómo revisamos las migraciones antes de producción para detectar bloqueos y reescrituras de tabla?
- ¿Quién consulta hoy directamente la base transaccional sin ser un servicio, y cómo lo encauzamos?
