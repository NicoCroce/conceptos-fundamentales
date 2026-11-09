---
slug: logging
titulo: Logging estructurado
resumen: Cómo escribir logs en JSON con campos fijos, correlacionarlos con trazas, proteger datos sensibles y controlar su volumen, costo y retención.
lectura: 12
---

## La idea central

Un log es el diario de a bordo de un servicio: cada línea cuenta algo que pasó en un momento dado. Durante años se escribieron como frases libres ("Error al asignar pedido 123 para el comercio X"), que una persona entiende bien pero una máquina no. Cuando hay cincuenta servicios y millones de líneas por hora, buscar entre frases libres con expresiones regulares es lento y frágil.

El **logging estructurado** cambia el enfoque: cada línea es un objeto (casi siempre JSON) con campos fijos y con nombre. En lugar de buscar texto, se consulta como una base de datos: "todas las líneas con `nivel=error`, `servicio=asignacion` y `zona=norte` en la última hora". A eso se suman tres preocupaciones que hacen la diferencia en producción: conectar los logs con las trazas, no filtrar datos sensibles y no gastar en logs más de lo que vale la información que contienen.

## Conceptos

### JSON con campos fijos

Un log estructurado tiene un conjunto de **campos comunes** que todos los servicios escriben igual, más campos específicos del evento. Acordar los nombres comunes es lo que permite buscar transversalmente: si un servicio escribe `trace_id` y otro `traceId`, la búsqueda se rompe.

Ejemplo de una línea del servicio de asignación (formateada en varias líneas para leerla; en producción va en una sola):

```json
{
  "ts": "2026-11-08T03:04:12.481Z",
  "nivel": "warn",
  "servicio": "asignacion",
  "version": "1.42.0",
  "entorno": "prod",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "evento": "modelo_timeout_respaldo",
  "mensaje": "El modelo no respondió en plazo; se usa respaldo heurístico",
  "pedido_id": "ped_8f2a91",
  "comercio_id": "com_1203",
  "zona": "sur",
  "modelo_version": "eta-v42",
  "duracion_ms": 35
}
```

Algunas claves de diseño:

- `evento` es un identificador estable y corto (`modelo_timeout_respaldo`), útil para contar y alertar; `mensaje` es el texto para humanos y puede cambiar.
- Las marcas de tiempo van en UTC con formato ISO 8601.
- Se usan identificadores (`pedido_id`), nunca datos de contacto del destinatario.
- Los tipos son consistentes: `duracion_ms` siempre numérico, nunca a veces `"35ms"`.

**Por qué importa:** con campos estables se pueden armar consultas, dashboards y alertas sobre logs sin depender de cómo alguien redactó una frase.

### Niveles

Los niveles indican gravedad y permiten filtrar. Un uso razonable:

| Nivel | Cuándo usarlo | Ejemplo en Rumbo |
|---|---|---|
| DEBUG | Detalle para desarrollo; normalmente apagado en producción | Lista de los 14 candidatos y sus puntajes |
| INFO | Hechos normales relevantes del ciclo de vida | Servicio arrancó con modelo eta-v42; pedido asignado |
| WARN | Algo anómalo que el sistema manejó solo | Timeout del modelo, se usó respaldo |
| ERROR | Una operación falló y no se pudo completar | No se pudo asignar el pedido tras tres intentos |

Errores frecuentes con los niveles: loguear como ERROR algo esperado (un pedido sin candidatos en una zona sin transportistas es un resultado de negocio, no un error del sistema) o dejar DEBUG activado en producción, lo que multiplica el volumen.

Conviene poder **cambiar el nivel en caliente** (por configuración o un endpoint interno) para activar DEBUG en un pod durante 15 minutos mientras se investiga.

### Correlación con trace id

Si cada línea incluye `trace_id` y `span_id`, se puede pasar de una traza a sus logs y de un log a su traza. Las librerías de logging en Go (`slog`) y Python (`structlog`, `logging` con filtros) pueden tomar el contexto de OpenTelemetry e inyectar estos campos automáticamente. Ver [OpenTelemetry y tracing](#t/opentelemetry).

**Ejemplo:** en un incidente, el panel de errores muestra un pico. Se filtran los logs con `nivel=error` y se elige uno; su `trace_id` abre la traza completa, donde se ve que el error del servicio de asignación vino de un timeout de Aurora tres saltos antes. Sin trace id habría que adivinar qué líneas de qué servicios pertenecen a la misma petición.

Además del trace id, conviene un **identificador de negocio** consistente (`pedido_id`) en todos los servicios: las trazas pueden estar muestreadas, pero el pedido existe siempre.

### Datos sensibles

Los logs suelen tener controles de acceso más amplios, más copias y retención más larga que la base de datos principal. Por eso son una vía frecuente de filtración.

Reglas para Rumbo:

- **Nunca credenciales:** contraseñas, tokens, claves de API ni headers `Authorization`. No hay forma segura de enmascararlos "un poco".
- **PII de destinatarios** (nombre, teléfono, dirección): no se loguea. Si hace falta para depurar, se usa una forma enmascarada (`+54 9 11 ****-**34`) o un hash con sal que permita correlacionar sin revelar el dato.
- **Redacción automática** en la librería de logging o en el agente que recolecta: detecta claves conocidas (`telefono`, `email`, `direccion`) y patrones (números de teléfono, emails) y los reemplaza. Es una red de seguridad, no un reemplazo de no loguearlos.
- **Cuidado con loguear objetos completos:** `log.Info("pedido", pedido)` serializa todos los campos, incluidos los del destinatario.

Ver [Secretos y cifrado](#t/secretos).

### Centralización y retención

Los logs de cada pod se pierden cuando el pod muere. Por eso se envían a un sistema central. El patrón habitual en Kubernetes: la aplicación escribe a la salida estándar, un agente en cada nodo (Fluent Bit, Vector o el Collector de OpenTelemetry) los lee, los enriquece con metadatos (pod, namespace, nodo) y los envía.

| Sistema | Modelo | Fortalezas | A tener en cuenta |
|---|---|---|---|
| CloudWatch Logs | Gestionado en AWS | Integración nativa con AWS, cero operación | Consultas limitadas frente a otros; costo por ingesta |
| OpenSearch | Índice de texto completo (gestionado o propio) | Búsqueda potente sobre cualquier campo | Indexar todo es caro en almacenamiento y cómputo |
| Grafana Loki | Indexa sólo labels, guarda el contenido en S3 | Muy barato a escala; se integra con Grafana | Consultas por contenido más lentas; labels con baja cardinalidad |
| Datadog Logs | SaaS comercial | Integrado con métricas y trazas, buena experiencia | Costo por volumen ingerido e indexado |

La **retención** se define por tipo de log. Un esquema típico: 7 a 15 días en almacenamiento "caliente" consultable, 90 días en almacenamiento barato (S3) por si hace falta reprocesar, y plazos más largos sólo para auditoría o requisitos legales. Guardar todo para siempre "por si acaso" es caro y aumenta el riesgo si hay datos personales.

### Volumen y costo

Los logs crecen sin que nadie lo note, porque cada línea parece gratis. Un cálculo de orden de magnitud: el servicio de asignación atiende 2.000 peticiones por segundo; si cada petición escribe 5 líneas de 600 bytes, son 6 MB por segundo, unos 520 GB por día, más de 15 TB por mes. Con un costo hipotético de ingesta de entre 0,25 y 0,50 dólares por GB en un servicio gestionado, son miles de dólares mensuales sólo para ese servicio.

Estrategias:

- **Muestrear los éxitos:** loguear el 100% de los errores y warnings, y el 1% de las peticiones exitosas. Las métricas ya cuentan los éxitos.
- **Una línea por petición** con todos los campos relevantes (estilo "evento ancho"), en lugar de cinco líneas parciales.
- **Bajar a DEBUG** lo que sólo sirve al desarrollar.
- **Enviar a almacenamiento barato** lo que rara vez se consulta, y sólo indexar lo necesario.
- **Medir el volumen por servicio y por evento** para saber dónde está el gasto. Ver [Costos cloud (FinOps)](#t/finops).

### Logs de auditoría

Los logs de auditoría responden "quién hizo qué, cuándo y desde dónde" sobre acciones sensibles: cambios de reglas de asignación, accesos a datos personales, cambios de permisos, despliegues. Son distintos de los logs operativos:

- Se escriben siempre, sin muestreo.
- Son **inmutables**: se guardan en un destino donde nadie, ni siquiera un administrador, pueda borrarlos o modificarlos durante el período de retención (por ejemplo, un bucket de S3 con Object Lock en modo compliance, en una cuenta separada).
- Tienen retención larga y acceso restringido.
- Registran el antes y el después del cambio, la identidad de quien lo hizo y el motivo si existe.

En AWS, CloudTrail cubre las acciones sobre la infraestructura; las acciones de negocio (cambiar una regla en el panel interno) las tiene que registrar la aplicación.

### Logs vs. eventos

Un log describe lo que el servicio hizo para que lo lea un humano o una herramienta de diagnóstico; puede perderse, muestrearse o cambiar de formato sin romper nada. Un **evento de negocio** (como "pedido entregado" en Kafka) es un contrato: otros sistemas dependen de él para funcionar, tiene esquema versionado y garantías de entrega. Ver [Event streaming](#t/event-streaming).

**Ejemplo:** el equipo de datos quiere calcular entregas a tiempo por zona. Si lo hace parseando logs del servicio de entregas, cualquier cambio en el texto o el muestreo de éxitos rompe la métrica sin aviso. Lo correcto es consumir el evento `pedido_entregado` de Kafka.

## Casos prácticos

### Rastrear un pedido por todos los servicios

**Situación:** un comercio pregunta por qué el pedido `ped_8f2a91` tardó 40 minutos en asignarse.

**Qué se hace:** como todos los servicios escriben `pedido_id` con el mismo nombre, una sola consulta (`pedido_id = "ped_8f2a91"`, ordenado por `ts`) devuelve la historia: la API lo recibió a las 10:02, el consumidor de asignación lo procesó a las 10:02 con resultado `sin_candidatos` en la zona oeste, reintentó cada 5 minutos con el mismo resultado y a las 10:41 apareció un transportista. Los logs de nivel INFO de esos reintentos estaban incluidos porque los resultados distintos de "ok" no se muestrean. La conclusión es operativa (falta de transportistas en esa franja), no técnica.

### Los logs cuestan más que el servicio

**Situación:** la factura hipotética de logs del servicio de asignación supera el costo de cómputo del propio servicio. El análisis por evento muestra que el 70% del volumen es una línea DEBUG con la lista completa de candidatos y sus features, que alguien dejó activa.

**Qué se hace:** se pasa esa línea a DEBUG real (apagado en producción) y se activa sólo bajo demanda en un pod. Se consolidan las cinco líneas por petición en una sola línea ancha. Se muestrean los éxitos al 2% y se conservan todos los warnings y errores. Se agrega una alerta de volumen de logs por servicio y un panel de costo. El volumen baja alrededor de un 90%, sin perder nada que se use en incidentes.

### Teléfonos de destinatarios en los logs

**Situación:** una revisión encuentra teléfonos completos de destinatarios en los logs del servicio de notificaciones: el código logueaba el payload completo enviado al proveedor de SMS.

**Qué se hace:** se corrige el código para loguear sólo `pedido_id`, el proveedor y el resultado. Se agrega **redacción automática** en el agente de logs, con reglas para claves conocidas y un patrón de números telefónicos. Se escribe un **test** en CI que ejecuta el flujo de notificación con un destinatario de prueba (`+00 0000-1234`) y falla si ese valor aparece en la salida de logs capturada. Junto con el equipo de privacidad, se purgan los datos históricos y se evalúa si corresponde notificar.

```python
def test_notificacion_no_loguea_telefono(caplog):
    enviar_notificacion(pedido_de_prueba(telefono="+00 0000-1234"))
    assert "0000-1234" not in caplog.text
```

### Quién cambió una regla de asignación a las 2 a.m.

**Situación:** a la mañana, la zona centro muestra muchas asignaciones a transportistas lejanos. Se descubre que la regla "radio máximo de búsqueda" pasó de 5 km a 25 km durante la noche.

**Qué se hace:** se consulta el log de auditoría del panel de reglas: a las 02:13 una cuenta de operaciones cambió el valor, con el motivo "cubrir falta de transportistas por lluvia". El registro incluye valor anterior, valor nuevo, identidad y origen. Con eso se habla con la persona, se entiende que fue una decisión deliberada que nadie revirtió y se agrega al proceso una expiración automática para cambios de emergencia. Si el log de auditoría hubiera estado mezclado con los operativos y muestreado, esa respuesta no existiría.

## Errores comunes

- **Loguear frases libres sin campos.** Imposibles de consultar a escala; cada dato relevante va en su propio campo con nombre acordado.
- **Nombres de campos distintos entre servicios.** `traceId`, `trace_id` y `TraceID` rompen las búsquedas transversales; conviene una convención común y una librería compartida.
- **Serializar objetos completos.** Es la forma más común de filtrar PII o credenciales; se loguean campos elegidos, no estructuras enteras.
- **Usar logs como fuente de métricas de negocio.** Si algo se cuenta para decidir, va como métrica o evento con contrato, no como texto a parsear.
- **Mezclar auditoría con logs operativos.** La auditoría necesita completitud, inmutabilidad y acceso restringido; los operativos, no.
- **Retención infinita por defecto.** Aumenta costo y riesgo; cada tipo de log necesita un plazo justificado.

## Para discutir en equipo

- ¿Qué campos comunes debería tener todo log de Rumbo, y cómo los hacemos obligatorios sin depender de la buena voluntad?
- ¿Qué porcentaje de éxitos conviene muestrear en el servicio de asignación sin perder capacidad de diagnóstico?
- ¿Qué acciones del panel interno deberían quedar en el log de auditoría y cuánto tiempo?
- ¿Cómo detectamos datos personales en logs de forma continua y no sólo en revisiones puntuales?
- ¿Qué logs deberían quedarse en las instalaciones on-prem de clientes y cuáles podemos centralizar?
