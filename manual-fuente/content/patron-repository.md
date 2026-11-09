---
slug: patron-repository
titulo: Patrón Repository y Unit of Work
resumen: Cómo guardar y recuperar agregados con una interfaz de colección, manejar transacciones y concurrencia, y por qué el repositorio es la única puerta de un agente a los datos.
lectura: 14
---

## La idea central

Un agregado bien diseñado protege sus reglas mientras está en memoria. Pero en algún momento hay que traerlo desde Postgres y volver a guardarlo, y ahí aparecen las preguntas incómodas: ¿quién arma el `Envio` a partir de tres tablas?, ¿quién decide qué se guarda en una transacción?, ¿qué pasa si dos personas lo modifican al mismo tiempo?, ¿cómo se testea sin base? El **patrón Repository** responde a la primera: una abstracción que se comporta como una colección de agregados en memoria, aunque por detrás haya SQL. El **Unit of Work** responde a la segunda: agrupa los cambios de una operación y los confirma juntos.

La analogía es un archivo con un archivista. Pedimos "el expediente del envío 812" y recibimos el expediente completo, con todas sus hojas; lo devolvemos y el archivista lo guarda. No nos importa en qué cajón está cada hoja. Para un agente con LLM, esa misma ventanilla es la diferencia entre "puede reprogramar un envío con las reglas de siempre" y "puede ejecutar cualquier SQL que se le ocurra".

## Conceptos

### Un repositorio por agregado, con forma de colección

Un **repositorio** ofrece al dominio la ilusión de una colección de agregados en memoria. Sus operaciones básicas son pocas: obtener por identidad, agregar o guardar y, a veces, quitar. Tres reglas lo definen:

1. **Uno por agregado, no por tabla.** `RepositorioEnvios` guarda y recupera el `Envio` con sus bultos e intentos de entrega, aunque en la base sean tres tablas. No existe `RepositorioBultos`: los bultos son internos al agregado (ver [DDD táctico](#t/ddd-tactico)).
2. **Devuelve agregados completos y válidos.** Nunca medio envío, ni filas sueltas, ni un objeto al que le faltan bultos "porque no hacían falta para esta pantalla".
3. **Habla el lenguaje del dominio.** `obtener(EnvioId)`, `pendientesDeAsignar(zona)`, no `selectByStatusAndZoneId`.

```typescript
// dominio/envios/RepositorioEnvios.ts
export interface RepositorioEnvios {
  obtener(id: EnvioId): Promise<Envio | null>;
  obtenerVarios(ids: EnvioId[]): Promise<Envio[]>;
  guardar(envio: Envio): Promise<void>;
  pendientesDeAsignar(zona: CodigoZona, limite: number): Promise<Envio[]>;
}
```

**Ejemplo:** el caso de uso `ReprogramarEntrega` hace tres cosas: `obtener`, llamar a `envio.reprogramar(...)` y `guardar`. No sabe que el envío ocupa las tablas `envios`, `bultos` e `intentos_entrega`, ni que la ventana horaria se guarda en dos columnas `timestamptz`.

**Por qué importa:** si el código de negocio arma agregados a partir de filas, cada caso de uso tiene su propia versión del mapeo y, tarde o temprano, uno de ellos construye un envío incompleto que pasa sus invariantes por accidente.

### Interfaz en el dominio, implementación en infraestructura

La interfaz la define el dominio, con sus tipos; la implementación vive en un adaptador de infraestructura que conoce Postgres, el ORM y el esquema. Es la inversión de dependencias de la [arquitectura hexagonal](#t/arquitectura-capas-hexagonal): la base depende del dominio, no al revés. Quién conecta la implementación concreta con los casos de uso es un tema de [inyección de dependencias](#t/inyeccion-dependencias).

```typescript
// infraestructura/postgres/RepositorioEnviosPg.ts
export class RepositorioEnviosPg implements RepositorioEnvios {
  constructor(private readonly tx: Transaccion) {}

  async obtener(id: EnvioId): Promise<Envio | null> {
    const fila = await this.tx.uno(
      "SELECT * FROM envios WHERE id = $1", [id.valor]);
    if (!fila) return null;
    const bultos = await this.tx.varios(
      "SELECT * FROM bultos WHERE envio_id = $1", [id.valor]);
    return Envio.reconstituir(mapearEnvio(fila), bultos.map(mapearBulto));
  }
  // guardar(...) en la sección de concurrencia
}
```

Un detalle importante es `Envio.reconstituir`: es distinto de la fábrica que crea envíos nuevos. Reconstituir no emite eventos ni vuelve a aplicar reglas de creación (un envío viejo puede tener una ventana que hoy ya no se permitiría crear), solo rearma el objeto a partir de datos que ya fueron válidos.

**Ejemplo:** cuando el equipo migró las ventanas horarias de dos columnas a un tipo `tstzrange` de Postgres, el cambio quedó dentro de `mapearEnvio` y de la migración. Ningún caso de uso ni test de dominio se tocó.

**Por qué importa:** el dominio se puede leer, testear y razonar sin conocer el esquema, y el esquema puede evolucionar sin reescribir reglas.

### Repository, DAO y ORM

Los tres términos aparecen juntos y se mezclan:

| | Repository | DAO (Data Access Object) | ORM |
|---|---|---|---|
| Unidad | Un agregado | Una tabla o una entidad persistente | Clases mapeadas a tablas |
| Vocabulario | Del dominio | De la base (`insert`, `update`, `findByX`) | Del framework |
| Qué devuelve | Agregados completos | Filas u objetos planos | Entidades del ORM, con lazy loading |
| Dónde vive la interfaz | En el dominio | En la capa de datos | En la librería |

No son excluyentes: una implementación de `RepositorioEnvios` puede usar un ORM por dentro, o varios DAOs. Lo que no conviene es que las entidades del ORM **sean** el modelo de dominio sin más: entonces el dominio hereda los setters públicos, el lazy loading y las anotaciones del framework, y el agregado deja de proteger algo.

**Ejemplo:** con entidades del ORM como dominio, `envio.bultos.add(b)` en cualquier servicio se persistía al cerrar la sesión, sin pasar por `agregarBulto` y su límite de 30 kg.

**Por qué importa:** "usamos un ORM" no responde a la pregunta de dónde se protegen las invariantes. El repositorio pone ese límite explícito.

### El repositorio genérico como antipatrón

Es común encontrar una interfaz `Repository<T>` con `findAll`, `findBy(criterios)`, `update(id, campos)` y `delete(id)`, heredada por todos los agregados. Parece reutilización, pero tiene tres problemas:

1. **Expone operaciones que el dominio no quiere.** ¿Tiene sentido borrar un envío? En Rumbo no: se cancela, con un evento. `delete` en la interfaz invita a usarlo.
2. **`update(id, campos)` saltea el agregado.** Es un `UPDATE` con otro nombre.
3. **`findBy(criterios)` filtra el lenguaje de la base hacia arriba.** Los criterios terminan siendo nombres de columnas armados como strings en los casos de uso.

Una implementación base genérica **por dentro** (para no repetir el mapeo de versiones o el manejo de errores) está bien. Lo que es un antipatrón es la interfaz genérica **hacia el dominio**.

**Ejemplo:** el servicio de franjas tenía `GenericRepository<Franja>` con `deleteAll()`. Un script de mantenimiento lo llamó contra el entorno equivocado. La interfaz específica `RepositorioFranjas` no tiene esa operación, porque el negocio nunca borra todas las franjas.

### Métodos de consulta frente al patrón Specification

Para buscar agregados por algo distinto de la identidad hay dos caminos:

- **Métodos de consulta con nombre:** `pendientesDeAsignar(zona, limite)`, `enRepartoDe(transportistaId)`. Son explícitos, fáciles de optimizar con un índice y de revisar. Su riesgo es la explosión: `pendientesDeAsignarPorZonaYVentanaYPeso...`.
- **Specification:** un objeto que representa un criterio del dominio, combinable con `y`, `o` y `no`, que el repositorio traduce a SQL y que también puede evaluarse en memoria.

```typescript
const urgentes = new EnZona(zona)
  .y(new EnEstado("PENDIENTE"))
  .y(new VentanaEmpiezaAntesDe(ahora.mas({ horas: 2 })));

const envios = await repo.buscar(urgentes, { limite: 100 });
// La misma especificación valida en memoria: urgentes.cumple(envio)
```

La regla práctica: empezar con métodos con nombre y pasar a especificaciones cuando hay muchas combinaciones de un mismo puñado de criterios, o cuando la misma regla ("un envío es urgente si...") se usa para buscar y para validar. Y recordar que el repositorio sirve al lado de **escritura**: para pantallas, reportes y búsquedas complejas conviene un modelo de lectura separado (ver [CQRS y Event Sourcing](#t/cqrs-event-sourcing)).

**Ejemplo:** la definición de "urgente" estaba escrita en SQL en el repositorio y en Kotlin en el asignador, y divergían en 15 minutos. Con la especificación `EsUrgente` una sola definición sirve para ambos.

### Unit of Work y transacciones

El **Unit of Work** (unidad de trabajo) registra qué agregados se cargaron y modificaron durante una operación y los confirma juntos al final, en una transacción. En la práctica suele ser la transacción de la base, más una lista de eventos a escribir en la outbox. La regla de DDD que la acompaña es: **una transacción modifica un solo agregado**.

```typescript
await uow.enTransaccion(async (repos) => {
  const envio = await repos.envios.obtener(id);
  envio.reprogramar(ventana, motivo, reloj.ahora());
  await repos.envios.guardar(envio);          // marca cambios y versión
  await repos.outbox.agregar(envio.extraerEventos());
});                                           // COMMIT de ambos, o de ninguno
```

**Ejemplo con números:** por un corte de ruta hay que reasignar 200 envíos de la zona Norte. Opción A: una sola transacción con los 200. Cargar y guardar cada uno toma unos 15 ms, así que la transacción dura unos 3 segundos y retiene locks de 200 filas; cualquier escaneo de la app del transportista sobre esos envíos espera o choca, y si el envío 187 falla, se deshacen los 186 anteriores. Opción B: 200 transacciones de 15 ms, una por envío, lanzadas por un job que registra progreso. Cada envío está bloqueado 15 ms; si el 187 falla, los otros 199 quedan bien y se reintenta uno solo. La opción B tarda lo mismo en total y no frena al resto del sistema.

Cuando una operación realmente necesita tocar dos agregados (asignar el envío y descontar capacidad del transportista), la opción por defecto es una transacción por agregado coordinada con eventos. Juntar ambos en una transacción es una excepción consciente, para casos con poca concurrencia, y conviene dejarla documentada.

**Por qué importa:** las transacciones grandes son la forma más común de convertir un sistema que funciona en pruebas en uno que se traba en hora pico.

### Concurrencia optimista con versiones

Dos personas o procesos pueden cargar el mismo envío, modificarlo y guardarlo. Sin control, gana el último y el cambio del primero se pierde en silencio. La solución habitual es una **versión** en la raíz del agregado, que se verifica al guardar (el mecanismo SQL está en [Bases de datos](#t/bases-de-datos)):

```typescript
async guardar(envio: Envio): Promise<void> {
  const r = await this.tx.ejecutar(
    `UPDATE envios SET estado = $1, ventana = $2, transportista_id = $3,
            version = version + 1
      WHERE id = $4 AND version = $5`,
    [envio.estado, envio.ventana, envio.transportista, envio.id.valor, envio.version]);
  if (r.filasAfectadas === 0) throw new ConflictoDeVersion(envio.id);
  await this.sincronizarBultos(envio);
}
```

Un punto fino: la versión es **del agregado entero**. Si solo cambia un bulto, la versión de la raíz igual se incrementa; de lo contrario, dos procesos podrían agregar bultos en paralelo, cada uno respetando los 30 kg por separado, y sumar 50 kg entre ambos.

**Ejemplo:** un operador abre el envío 812 (versión 7) en el panel para reprogramarlo. Mientras lo edita, el transportista lo escanea y la versión pasa a 8. Al guardar, el `UPDATE ... WHERE version = 7` afecta 0 filas: el panel muestra "el envío cambió mientras lo editabas" y recarga. Para un agente, el error vuelve como resultado de la herramienta y el agente relee el estado antes de decidir de nuevo, en lugar de reintentar a ciegas.

**Por qué importa:** sin versión, los conflictos existen igual; solo que nadie se entera y los datos quedan mal.

### N+1 y rendimiento

El problema **N+1** aparece cuando se carga una lista de N agregados y luego, por cada uno, una consulta más para sus partes. Con repositorios es fácil caer en él si `obtenerVarios` llama a `obtener` en un bucle, o si el ORM carga los bultos de forma perezosa.

**Ejemplo:** el panel de la zona muestra 50 envíos con sus bultos. Con N+1: 1 consulta de envíos + 50 de bultos = 51 consultas; a 2 ms cada una, unos 102 ms solo de idas y vueltas, más el uso del pool de conexiones. Con carga en lote: una consulta de envíos y una de bultos con `WHERE envio_id = ANY($1)`, 2 consultas, unos 6 ms. A 30 pedidos por segundo al panel, la diferencia es de 1.530 a 60 consultas por segundo contra la base.

Las salidas, en orden de preferencia:

1. Métodos de carga en lote en el repositorio (`obtenerVarios`) que traen las partes con una consulta por tabla.
2. Si la pantalla solo necesita mostrar datos, **no usar el repositorio**: leer de una proyección o consulta de lectura armada para esa vista.
3. Medir: contar consultas por request en los tests de integración y en las trazas.

**Por qué importa:** el repositorio optimiza la consistencia de escritura, no la lectura masiva. Usarlo para todo es una fuente constante de latencia.

### Repositorio en memoria para tests

Como la interfaz pertenece al dominio, se puede implementar con un `Map` para los tests de casos de uso. Es un **fake**, un tipo de doble de prueba que funciona de verdad pero de forma simplificada (ver [Testing y dobles de prueba](#t/testing-dobles)).

```typescript
export class RepositorioEnviosEnMemoria implements RepositorioEnvios {
  private datos = new Map<string, { snapshot: string; version: number }>();

  async obtener(id: EnvioId) {
    const d = this.datos.get(id.valor);
    return d ? Envio.desdeSnapshot(d.snapshot) : null;   // copia, no la misma instancia
  }
  async guardar(envio: Envio) {
    const actual = this.datos.get(envio.id.valor);
    if (actual && actual.version !== envio.version) throw new ConflictoDeVersion(envio.id);
    this.datos.set(envio.id.valor, { snapshot: envio.snapshot(), version: envio.version + 1 });
  }
  // obtenerVarios y pendientesDeAsignar, filtrando el Map
}
```

Dos cuidados lo hacen confiable: devolver **copias** (si devuelve la misma instancia, un test puede pasar aunque el caso de uso olvide llamar a `guardar`) y respetar la **versión**, para que los tests de conflicto sean posibles. Además, conviene un conjunto de **tests de contrato** que corran contra el repositorio en memoria y contra el de Postgres, para garantizar que se comportan igual.

**Ejemplo:** la suite de casos de uso de Asignación tiene 140 tests que corren en 2 segundos con el repositorio en memoria; los 12 tests de contrato corren también contra un Postgres en contenedor en CI.

### El repositorio como única puerta del agente a los datos

Ante un agente que necesita datos, la salida rápida es darle una herramienta `ejecutar_sql`. Es la peor opción posible: el modelo puede leer cualquier tabla (incluida PII que no necesita), escribir sin pasar por ningún agregado, generar consultas que bloquean la base y ser inducido por una [inyección de prompt](#t/seguridad-agentes) a hacer cualquiera de esas cosas.

La alternativa es la misma arquitectura que usa el resto del sistema:

1. **Herramientas de escritura** que llaman a casos de uso, que usan el repositorio, que reconstituye el agregado, que aplica sus reglas.
2. **Herramientas de lectura** que consultan modelos de lectura o métodos de consulta acotados, con límites de filas, filtros obligatorios (por comercio, por zona) y solo los campos necesarios.
3. **Ninguna herramienta** que reciba SQL, nombres de tablas o criterios libres.

**Ejemplo:** el agente de operaciones investigaba "cayó la tasa de entregas a tiempo en la zona norte" con una herramienta SQL de solo lectura. Una consulta sin filtro de fecha recorrió 40 millones de filas y saturó la réplica durante 6 minutos. Se reemplazó por `envios_atrasados(zona, desde, hasta, limite ≤ 200)` y `resumen_entregas_por_zona(zona, dia)`, implementadas sobre consultas con índice. La investigación sigue funcionando y el costo de cada llamada es predecible.

**Por qué importa:** el repositorio y los casos de uso ya concentran reglas, permisos y rendimiento. Darle al agente otra puerta es duplicar todo eso, o, más probablemente, no tenerlo.

## Casos prácticos

### La herramienta SQL del agente de operaciones

**Situación:** el agente tenía acceso de lectura a la réplica vía SQL libre. Además del incidente de rendimiento, una revisión encontró que en sus trazas aparecían teléfonos de destinatarios que nunca necesitó.

**Qué se hace:** se reemplaza por cinco herramientas de consulta con nombre del dominio, cada una con límites y sin campos de PII. Las que escriben llaman a casos de uso existentes con el operador como actor. Se agrega una alerta si alguna herramienta supera 500 ms en p95, para detectar consultas que necesitan índice o proyección.

### Reasignación masiva en una sola transacción

**Situación:** el job de reasignación por corte de ruta abría una transacción para 300 envíos. Durante sus 4 segundos, la app de los transportistas mostraba errores al escanear, y cuando un envío fallaba, ninguno quedaba reasignado.

**Qué se hace:** se pasa a una transacción por envío, con un registro del lote que guarda qué envíos se procesaron, para reanudar si el job se interrumpe. Cada reasignación emite su evento por outbox. Los errores de escaneo desaparecen y los fallos individuales se reintentan sin afectar al resto.

### Dos operadores y un envío

**Situación:** un operador reprogramaba un envío desde el panel mientras el asistente de soporte, a pedido del destinatario, lo reprogramaba a otra ventana. Ganaba el último en guardar y el destinatario recibía dos avisos contradictorios.

**Qué se hace:** se agrega versión al agregado `Envio` y se verifica en `guardar`. El segundo en guardar recibe un conflicto: el panel recarga y muestra el cambio nuevo; el agente recibe "el envío fue modificado, estado actual: ..." y responde al destinatario con la ventana vigente. Se emite un solo aviso.

### El panel de zona que tardaba un segundo

**Situación:** la vista de la zona cargaba 80 envíos con `repo.obtener` en un bucle, con bultos e intentos perezosos: 241 consultas por carga.

**Qué se hace:** a corto plazo, `obtenerVarios` con carga en lote (3 consultas). A mediano plazo, la vista pasa a leer de una proyección `envios_por_zona` que ya tiene los datos que se muestran, y el repositorio queda solo para las acciones que modifican envíos.

## Errores comunes

- **Un repositorio por tabla.** Rompe el agregado en pedazos que se guardan por separado. Un repositorio por agregado, que guarda la raíz y sus partes juntas.
- **Interfaz genérica con `update` y `delete`.** Permite saltear las reglas del agregado. Definir interfaces específicas con las operaciones que el negocio admite.
- **Varias raíces en una transacción por comodidad.** Aumenta locks y conflictos. Una transacción por agregado y coordinación con eventos, salvo excepciones documentadas.
- **Guardar sin versión.** Los cambios concurrentes se pisan en silencio. Versión en la raíz, incrementada ante cualquier cambio del agregado.
- **Usar el repositorio para pantallas y reportes.** Provoca N+1 y consultas pesadas. Leer de modelos de lectura o consultas específicas.
- **Darle SQL libre a un agente.** Abre lectura de PII, escrituras sin reglas y consultas que tumban la base. Exponer herramientas con nombre del dominio sobre repositorios y modelos de lectura.

## Para discutir en equipo

- ¿Qué repositorios nuestros devuelven agregados incompletos o exponen operaciones que el negocio no admite?
- ¿Qué jobs o casos de uso modifican varios agregados en una transacción, y cuánto duran en hora pico?
- ¿Tenemos tests de contrato que garanticen que el repositorio en memoria se comporta igual que el real?
- ¿Qué herramientas de agente acceden a datos sin pasar por un repositorio o un modelo de lectura?
- ¿Cómo debería reaccionar un agente ante un conflicto de versión: releer y decidir de nuevo, o devolver el control a una persona?
