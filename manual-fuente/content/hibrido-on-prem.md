---
slug: hibrido-on-prem
titulo: Despliegue híbrido y on-prem
resumen: Cómo llevar la plataforma y los modelos de Rumbo al data center de un cliente sin mantener dos productos distintos ni perder la capacidad de operarlos.
lectura: 13
---

## La idea central

Rumbo nace como SaaS: todo corre en nuestras cuentas de AWS y los comercios lo usan por internet. Pero algunos clientes grandes no pueden o no quieren que sus datos salgan de su infraestructura. Para ellos ofrecemos un despliegue **híbrido** (parte en su data center, parte en nuestra nube) u **on-prem** completo (todo en su data center). El desafío no es instalar el software una vez; es que siga funcionando, actualizándose y mejorando durante años en un entorno que no controlamos y, a veces, que ni siquiera podemos ver.

Una analogía: el SaaS es un restaurante propio, donde controlas la cocina, los proveedores y la temperatura de la heladera. El on-prem es cocinar en la casa de otra persona, con su horno, sus horarios y sin poder entrar cuando quieras. Para que salga bien, tienes que llevar recetas que funcionen con hornos distintos, ingredientes empaquetados y un plan para cuando algo se queme y no estés ahí. Este tema trata sobre cómo diseñar el software para que esa diferencia sea manejable.

## Conceptos

### Por qué algunos clientes lo exigen

Las razones suelen caer en cuatro grupos:

1. **Residencia de datos:** la ley o el contrato exige que ciertos datos (por ejemplo, los datos personales de destinatarios) se almacenen y procesen dentro de un país o de una infraestructura concreta.
2. **Regulación sectorial:** clientes de salud o del sector público con reglas propias sobre dónde se procesa la información y quién puede acceder.
3. **Políticas de seguridad internas:** el área de seguridad del cliente no aprueba enviar datos a un proveedor externo, o exige auditar todo el software que procesa sus datos.
4. **Latencia o conectividad:** centros de distribución con enlaces poco confiables que necesitan seguir asignando pedidos si se corta internet.

**Ejemplo:** una cadena minorista con 300 sucursales y un millón de destinatarios por mes acepta que Rumbo reciba métricas agregadas, pero no nombres, teléfonos ni direcciones.

**Por qué importa:** la razón concreta define la arquitectura. Si el requisito es solo residencia de datos, a veces alcanza con una región de AWS en el país; si es "nada sale del data center", hace falta on-prem real.

### Kubernetes como capa común y Helm

La forma de no mantener dos productos es apoyarse en una capa que exista en ambos mundos. Esa capa es **Kubernetes**: en nuestra nube corremos EKS y en el cliente puede haber OpenShift, Rancher, EKS Anywhere o un Kubernetes estándar. Si nuestros servicios solo dependen de la API de Kubernetes (Deployments, Services, ConfigMaps, Secrets), corren igual en todos (ver [Contenedores, ECS y EKS](#t/contenedores)).

**Helm** es el gestor de paquetes de Kubernetes. Un *chart* agrupa los manifiestos de un servicio con plantillas y un archivo `values.yaml` con los parámetros que cambian entre entornos.

```yaml
# values-cliente-acme.yaml
cola:
  tipo: kafka            # en SaaS: sqs
  brokers: kafka.acme.local:9092
almacenamiento:
  tipo: s3-compatible    # en SaaS: s3
  endpoint: https://minio.acme.local
modeloEta:
  version: v42
telemetria:
  modo: agregada         # en SaaS: completa
```

**Por qué importa:** con un único chart parametrizado, cada mejora llega a todos los clientes. Con un fork por cliente, cada mejora se multiplica por el número de forks.

### EKS Anywhere y Outposts

AWS ofrece dos productos para acercar su modelo al data center del cliente:

- **EKS Anywhere:** una distribución de Kubernetes que el cliente instala en su propio hardware (vSphere, bare metal), con las mismas herramientas que EKS. No necesita conexión permanente a AWS.
- **Outposts:** racks de hardware de AWS instalados en el data center del cliente, gestionados por AWS, que exponen servicios como EC2, EBS, S3 y EKS localmente. Requieren conexión con la región de AWS.

En la práctica, muchos clientes ya tienen su plataforma de Kubernetes y no quieren otra. Por eso conviene no depender de ninguno de los dos y tratarlos como una opción más.

### Dependencias de servicios gestionados y cómo abstraerlas

El mayor obstáculo para el on-prem no es Kubernetes: son los servicios gestionados de AWS que usamos sin pensarlo. SQS, DynamoDB, S3, Secrets Manager y KMS no existen en el data center del cliente. Hay tres estrategias:

1. **Usar tecnologías abiertas en ambos lados:** PostgreSQL en vez de DynamoDB, Kafka en vez de SQS. Más simple de mantener, pero renunciamos a ventajas operativas del servicio gestionado.
2. **Abstraer detrás de interfaces:** el código depende de una interfaz propia, con una implementación por plataforma.
3. **Usar alternativas compatibles con la API:** almacenamiento compatible con S3 (MinIO, Ceph) habla el mismo protocolo, así que el cliente de S3 funciona cambiando el endpoint.

La estrategia 2 en Go:

```go
// La lógica de negocio solo conoce esta interfaz.
type ColaEventos interface {
    Publicar(ctx context.Context, tema string, msg []byte) error
    Consumir(ctx context.Context, tema string, h Handler) error
}

// Implementaciones: colasqs.New(...) en SaaS, colakafka.New(...) on-prem.
// Se elige por configuración al arrancar, no con ifs en todo el código.
```

Equivalencias habituales:

| En SaaS (AWS) | On-prem | Cómo se abstrae |
|---|---|---|
| SQS | Kafka o RabbitMQ | Interfaz de cola con dos implementaciones |
| DynamoDB | PostgreSQL | Interfaz de repositorio; modelo de datos simple |
| S3 | Almacenamiento compatible con S3 | Mismo cliente, otro endpoint |
| Secrets Manager / KMS | Vault, HSM del cliente | Interfaz de secretos y de cifrado |
| Aurora PostgreSQL | PostgreSQL del cliente o en el clúster | Mismo protocolo; cuidado con extensiones |

**Ejemplo:** el servicio de asignación usa solo características de PostgreSQL estándar. Una función específica de Aurora que no esté en PostgreSQL rompería la paridad.

**Por qué importa:** cada interfaz tiene un costo (dos implementaciones que probar), así que se abstrae lo necesario, no todo por si acaso.

### Distribución del software

En SaaS desplegamos nosotros; on-prem, el cliente instala lo que le entregamos. Eso exige:

- **Imágenes firmadas:** cada imagen de contenedor se firma (por ejemplo, con cosign) y el clúster del cliente verifica la firma antes de ejecutarla. Así el cliente sabe que la imagen es nuestra y no fue alterada.
- **Registro privado:** el cliente replica nuestras imágenes en su propio registro; sus nodos no descargan nada de internet.
- **Instalador:** un único comando o herramienta que valida requisitos (versión de Kubernetes, clases de almacenamiento, recursos), instala los charts en orden y corre verificaciones posteriores.
- **Versiones soportadas:** una política explícita, por ejemplo "soportamos las dos últimas versiones mayores; cada versión recibe parches de seguridad durante 12 meses". Sin esa política, terminamos depurando versiones de hace tres años.
- **SBOM:** la lista de componentes de cada imagen, que los equipos de seguridad de los clientes suelen pedir.

### Instalaciones air-gapped

Una instalación **air-gapped** no tiene ninguna conexión a internet. Todo entra por un medio controlado (un paquete descargado en otra red, revisado y copiado).

Pasos típicos para una actualización:

1. Generamos un paquete con imágenes, charts, modelos y el instalador, con checksums y firmas.
2. El cliente lo descarga en su red de tránsito, lo escanea con sus herramientas y lo transfiere.
3. El instalador carga las imágenes en el registro interno y actualiza.
4. Diagnóstico: el instalador genera un "bundle de soporte" (logs y estado sin datos personales) que el cliente revisa y nos envía.

**Ejemplo:** un paquete de actualización de 8 GB, de los cuales 5 GB son imágenes base. Separar las capas base que cambian poco de las capas de aplicación reduce los paquetes siguientes a unos cientos de MB.

### ML on-prem

Los modelos agregan un problema propio: un modelo no es solo código, depende de datos que cambian.

- **Entrega de modelos:** el artefacto del modelo de ETA viaja como un componente más del paquete, versionado y firmado. El servicio lo carga igual que en SaaS.
- **Reentrenamiento con datos que no salen:** si el cliente no permite extraer datos, el pipeline de entrenamiento corre en su infraestructura. Enviamos el código y la configuración; se entrena allí; se evalúa contra un conjunto de validación local y solo se promueve si supera métricas acordadas. Esto exige que el pipeline sea tan portable como los servicios.
- **Monitoreo remoto limitado:** no vemos los datos ni, a veces, las predicciones. Acordamos de antemano un conjunto de **métricas agregadas** (error medio de ETA por día, distribución de features resumida, volumen) que el cliente acepta compartir porque no contienen datos personales (ver [Monitoreo de modelos](#t/monitoreo-modelos)).

**Por qué importa:** un modelo que no se reentrena y no se monitorea se degrada en silencio, y en on-prem nadie lo nota hasta que el cliente se queja.

### LLMs on-prem

El asistente de soporte usa un proveedor externo de LLM. Si el cliente no permite que el texto de los tickets salga, hay que correr un **modelo abierto** dentro de su infraestructura. Implica:

- **GPUs:** un modelo mediano necesita una o varias GPUs con memoria suficiente; el cliente debe comprarlas o tenerlas, y eso alarga la venta.
- **Calidad distinta:** un modelo abierto más chico puede rendir peor en algunas tareas. Hay que correr nuestra suite de evaluación sobre él antes de prometer nada.
- **Servidor de inferencia:** algo como vLLM expone una API compatible con la que usa nuestro gateway, para que el asistente cambie de modelo por configuración.

**Ejemplo:** si la suite de evaluación da 92 % de clasificación correcta de tickets con el proveedor externo y 85 % con el modelo abierto, el cliente decide con ese dato si acepta la diferencia o prefiere limitar el asistente a resúmenes.

### Operación y soporte

Lo que cambia respecto del SaaS:

- **Responsabilidad compartida:** quién parchea el sistema operativo, quién hace backups, quién está de guardia. Tiene que estar escrito en el contrato y en un documento operativo.
- **Diagnóstico sin acceso:** logs estructurados, mensajes de error accionables y el bundle de soporte reemplazan al "entro y miro".
- **Runbooks para el cliente:** los operadores del cliente ejecutan acciones que en SaaS haríamos nosotros.

### Comparación de modelos de despliegue

| Aspecto | SaaS | Híbrido | On-prem completo |
|---|---|---|---|
| Dónde corre | Nuestra nube | Plano de control nuestro, datos en el cliente | Todo en el cliente |
| Datos personales | En nuestra nube | Quedan en el cliente | Quedan en el cliente |
| Actualizaciones | Continuas, las hacemos nosotros | Frecuentes, coordinadas | Por paquete, el cliente decide cuándo |
| Visibilidad para nosotros | Completa | Parcial (métricas y estado) | Mínima o acordada |
| Servicios gestionados de AWS | Todos | En la parte nuestra | Ninguno |
| Costo de soporte por cliente | Bajo | Medio | Alto |
| Tiempo hasta que llega una mejora | Horas o días | Días o semanas | Semanas o meses |

## Casos prácticos

### Un cliente grande que no permite que los datos de destinatarios salgan

**Situación:** una cadena con miles de pedidos diarios quiere Rumbo, pero su área de seguridad exige que nombres, teléfonos y direcciones de destinatarios nunca salgan de su data center.

**Qué se hace:** primero se precisa el requisito: ¿aplica a todo o solo a PII? Si solo a PII, un modelo híbrido sirve: los servicios que manejan PII (pedidos, notificaciones, app del transportista) corren en su clúster con su base de datos; la configuración, el panel de control y las métricas agregadas viven en nuestra nube. La asignación también corre local por su presupuesto de 50 ms. Se documenta exactamente qué cruza la frontera (identificadores opacos, conteos, latencias) y el cliente lo audita. Si el requisito es "nada sale", se pasa a on-prem completo y el precio y el plazo cambian.

### Servicio atado a SQS y DynamoDB

**Situación:** el servicio de notificaciones usa SQS para encolar mensajes y DynamoDB para deduplicar. Para el cliente on-prem no existe ninguno de los dos.

**Qué se hace:** se introducen dos interfaces: `ColaEventos` y `RegistroDeduplicacion`. En SaaS siguen usando SQS y DynamoDB; on-prem, Kafka (ya existe para eventos de pedidos) y una tabla PostgreSQL con clave única y expiración. La suite de pruebas de integración corre contra ambas implementaciones en CI. Antes de abstraer, se revisa si vale la pena usar Kafka y PostgreSQL también en SaaS: una sola implementación es más barata de mantener que dos, si la diferencia operativa es aceptable.

### Modelo degradado en un cliente on-prem sin visibilidad

**Situación:** un cliente on-prem reporta que "las ETA están mal". No tenemos acceso a sus datos ni a las predicciones individuales.

**Qué se hace:** gracias a las métricas agregadas acordadas en el contrato (error absoluto medio diario, porcentaje de entregas dentro de la ventana, medias y percentiles de features clave), vemos que el error subió de 6 a 14 minutos hace tres semanas y que la feature `carga_transportista` tiene media cero desde entonces. Hipótesis: cambió un sistema del cliente y esa feature dejó de llegar. Con su equipo se confirma y corrige. Se agrega una alerta que se dispara en su lado si una feature tiene varianza nula, y un reentrenamiento local con el pipeline portable.

### Dos velocidades de release y su costo en las estimaciones

**Situación:** en SaaS publicamos varias veces por semana; los clientes on-prem actualizan cada tres o seis meses. Una funcionalidad nueva se estima en dos semanas, pero en on-prem tarda tres meses en llegar y requiere migraciones de varias versiones a la vez.

**Qué se hace:** se acepta que hay dos velocidades y se presupuesta: cada épica incluye explícitamente el trabajo on-prem (implementación alternativa, migraciones que saltan versiones, pruebas del instalador, documentación para el operador del cliente). Como orden de magnitud, el equipo observa que eso agrega entre 20 % y 40 % a las estimaciones. Los feature flags permiten publicar código en ambos lados y activarlo cuando corresponde. La política de versiones soportadas limita cuántas versiones viejas hay que mantener.

## Errores comunes

- **Hacer un fork del código por cliente.** Cada fork diverge y las mejoras dejan de llegar; usa un único código con configuración y feature flags.
- **Abstraer todos los servicios de AWS por las dudas.** Cada interfaz duplica pruebas y mantenimiento; abstrae solo lo que un cliente real necesita.
- **Asumir conexión a internet.** Licencias, telemetría o descargas en tiempo de ejecución rompen en air-gapped; todo lo necesario va en el paquete.
- **Prometer monitoreo de modelos sin acordarlo por contrato.** Si no se pactan métricas agregadas antes, no se pueden pedir después; inclúyelas en la negociación.
- **No limitar versiones soportadas.** Terminas manteniendo cinco versiones a la vez; define una política y respétala.
- **Probar on-prem solo en el cliente.** Mantén un entorno de referencia propio (Kubernetes estándar, sin servicios de AWS) donde corre la suite en cada release.

## Para discutir en equipo

- ¿Qué servicios de AWS usamos hoy que no tienen equivalente fácil on-prem, y cuáles convendría reemplazar por tecnologías abiertas también en SaaS?
- ¿Qué métricas agregadas necesitamos de cada cliente on-prem para operar bien los modelos, y cuáles serían aceptables para un área de seguridad exigente?
- ¿Cuánto nos cuesta realmente cada cliente on-prem (soporte, releases, pruebas) y cómo se refleja eso en las estimaciones?
- Si un cliente exige el asistente de soporte on-prem, ¿qué nivel de calidad mínimo pedimos al modelo abierto antes de ofrecerlo?
