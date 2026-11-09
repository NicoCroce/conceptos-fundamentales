---
slug: terraform
titulo: Terraform
resumen: Herramienta de infraestructura como código que describe recursos cloud en archivos versionados y los crea, cambia o destruye de forma revisable y repetible.
lectura: 12
---

## La idea central

Hace años, crear una base de datos o un balanceador implicaba entrar a la consola web, hacer clic en una serie de pantallas y anotar (con suerte) lo que se había hecho. El resultado era infraestructura que nadie sabía reconstruir exactamente, con diferencias sutiles entre staging y producción. **Infraestructura como código** (IaC) propone tratar la infraestructura igual que el software: describirla en archivos de texto, guardarlos en git, revisarlos en pull requests y aplicarlos con una herramienta automática.

**Terraform** es la herramienta de IaC más difundida. Se le describe el estado final deseado ("quiero un bucket con este nombre y cifrado activado") y Terraform calcula qué tiene que crear, cambiar o borrar para llegar ahí. La analogía útil es la de un plano de arquitectura frente a una lista de instrucciones de obra: no se le dice "pon un ladrillo aquí", se le entrega el plano y la herramienta compara el plano con lo que ya está construido. Esa comparación es poderosa, y también peligrosa: si el plano dice que la base de datos debe ser distinta de la que existe, Terraform puede proponer demolerla y construir otra.

## Conceptos

### Declarativo frente a imperativo

Un script imperativo dice **cómo**: "crea el bucket; si ya existe, no hagas nada; luego activa el cifrado". Un archivo declarativo dice **qué**: "debe existir un bucket con cifrado". La diferencia aparece la segunda vez que se ejecuta: el script tiene que contemplar cada caso posible, mientras que la herramienta declarativa compara y solo aplica la diferencia.

Esa propiedad se llama **idempotencia**: aplicar el mismo código dos veces deja la infraestructura igual que aplicarlo una vez. Si nada cambió, Terraform dice "No changes" y no toca nada.

**Por qué importa:** permite reconstruir un entorno completo desde cero (por ejemplo, un entorno nuevo para un cliente) y saber, en cualquier momento, si la realidad coincide con lo que está en git.

### Providers, recursos, variables y outputs

Terraform se escribe en **HCL** (HashiCorp Configuration Language). Los bloques básicos son:

- **Provider:** el plugin que sabe hablar con una API concreta: AWS, Kubernetes, Datadog, GitHub. Terraform en sí no sabe nada de AWS; el provider traduce los recursos a llamadas a la API.
- **Resource:** una pieza de infraestructura que Terraform gestiona: un bucket, un rol de IAM, una instancia de Aurora. Tiene un tipo (`aws_s3_bucket`) y un nombre local (`modelos`).
- **Variable:** un parámetro de entrada, para reutilizar el mismo código con valores distintos (entorno, tamaño de instancia).
- **Output:** un valor que se expone hacia afuera, para que otro módulo o un humano lo use (el ARN de un bucket, el endpoint de una base).
- **Data source:** una consulta de solo lectura a algo que existe pero no gestiona este código (por ejemplo, el ID de una VPC creada por otro equipo).

Ejemplo de un bucket para los artefactos del modelo de ETA y el uso de un módulo estándar de servicio:

```hcl
variable "entorno" {
  type        = string
  description = "staging o prod"
}

resource "aws_s3_bucket" "modelos" {
  bucket = "rumbo-modelos-${var.entorno}"

  tags = {
    equipo = "ml"
    datos  = "sin-pii"
  }
}

resource "aws_s3_bucket_versioning" "modelos" {
  bucket = aws_s3_bucket.modelos.id   # referencia: Terraform deduce el orden
  versioning_configuration {
    status = "Enabled"
  }
}

module "servicio_eta" {
  source  = "git::https://git.rumbo.internal/plataforma/modulos.git//servicio-eks?ref=v3.2.0"

  nombre        = "modelo-eta"
  entorno       = var.entorno
  replicas_min  = 3
  replicas_max  = 20
  buckets_lectura = [aws_s3_bucket.modelos.arn]
}

output "bucket_modelos" {
  value = aws_s3_bucket.modelos.bucket
}
```

Las referencias entre recursos (`aws_s3_bucket.modelos.id`) arman un **grafo de dependencias**: Terraform sabe que primero debe crear el bucket y después configurar su versionado, sin que nadie se lo diga.

### El estado y por qué es sensible

Para saber qué existe, Terraform guarda un archivo de **estado** (state): un JSON que asocia cada recurso del código con el objeto real en AWS (por ejemplo, `aws_s3_bucket.modelos` corresponde al bucket `rumbo-modelos-prod`), junto con todos sus atributos.

Sin estado, Terraform no podría distinguir "este bucket lo creé yo y hay que modificarlo" de "este bucket no es mío". En equipo, el estado no puede vivir en la laptop de nadie. Se usa un **backend remoto**, típicamente un bucket S3 con versionado y cifrado, más un mecanismo de **bloqueo** (lock) para que dos ejecuciones no escriban a la vez. Históricamente el bloqueo se hacía con una tabla de DynamoDB; las versiones recientes también permiten bloqueo nativo en S3.

El estado es **sensible** por dos motivos:

1. **Contiene secretos en texto plano.** Si un recurso tiene una contraseña (por ejemplo, la contraseña maestra de una base), queda guardada en el estado aunque el código la marque como `sensitive`. Hay que restringir quién puede leer el bucket de estado y, mejor aún, no pasar secretos por Terraform (ver [Secretos y cifrado](#t/secretos)).
2. **Es la fuente de verdad de Terraform.** Si se corrompe o se pierde, Terraform cree que nada existe y propondrá crear todo de nuevo, chocando con lo que ya hay. El versionado del bucket permite volver a una versión anterior.

**Ejemplo:** un estado de producción con 600 recursos se divide en varios estados más chicos (red, bases de datos, clúster, cada servicio). Así un `plan` tarda segundos en lugar de minutos, y un error en el código de un servicio no puede afectar la red.

### Plan y apply

El flujo tiene dos pasos:

1. **`terraform plan`:** consulta la realidad, la compara con el código y el estado, y muestra qué haría, sin tocar nada.
2. **`terraform apply`:** ejecuta los cambios.

El plan usa símbolos: `+` crear, `~` modificar en el lugar, `-` destruir y `-/+` destruir y volver a crear (reemplazo). El reemplazo es el que más cuidado exige, porque Terraform marca qué atributo lo fuerza:

```text
Terraform will perform the following actions:

  # aws_rds_cluster.principal must be replaced
-/+ resource "aws_rds_cluster" "principal" {
      ~ arn                     = "arn:aws:rds:us-east-1:...:cluster:rumbo-prod" -> (known after apply)
      ~ cluster_identifier      = "rumbo-prod" -> "rumbo-prod-principal" # forces replacement
      ~ endpoint                = "rumbo-prod.cluster-xxxx.us-east-1.rds.amazonaws.com" -> (known after apply)
        engine                  = "aurora-postgresql"
        # (24 unchanged attributes hidden)
    }

  # aws_security_group_rule.app_a_db will be updated in-place
  ~ resource "aws_security_group_rule" "app_a_db" {
      ~ description = "app" -> "acceso desde servicio de asignacion"
    }

Plan: 1 to add, 1 to change, 1 to destroy.
```

Ese "1 to destroy" es una base de datos de producción. La práctica sana en equipo:

- El **plan se genera automáticamente en el pull request** y se publica como comentario, para que el revisor vea el efecto real del cambio y no solo el diff del código.
- El **apply corre desde CI**, después del merge, con credenciales del pipeline y aplicando exactamente el plan revisado (se guarda el archivo de plan y se aplica ese). Nadie aplica a producción desde su laptop.
- Cualquier `destroy` o `-/+` sobre recursos con datos exige aprobación explícita.

### Módulos

Un **módulo** es un conjunto de recursos empaquetados con variables de entrada y outputs, como una función. El equipo de plataforma de Rumbo mantiene, por ejemplo, un módulo `servicio-eks` que crea de una vez: el rol de IAM del servicio con permisos mínimos, el repositorio en ECR, las alarmas básicas, el registro DNS y los permisos de lectura sobre buckets indicados.

Los módulos se **versionan** (`?ref=v3.2.0`): actualizar el módulo no cambia los servicios que lo usan hasta que cada uno sube de versión, revisando su propio plan.

**Por qué importa:** los módulos codifican las buenas prácticas una sola vez. Un servicio nuevo hereda cifrado, etiquetas, alarmas y mínimo privilegio sin que el equipo que lo crea tenga que conocer cada detalle.

### Entornos y cuentas

Lo habitual es tener un mismo código para varios entornos (dev, staging, prod) cambiando variables, y que cada entorno viva en una **cuenta de AWS separada** (ver [Fundamentos de AWS](#t/aws)). Hay dos formas comunes de organizarlo:

- **Directorios por entorno** (`envs/staging`, `envs/prod`), cada uno con su backend de estado y su archivo de variables, llamando a los mismos módulos. Es explícito y fácil de revisar.
- **Workspaces** de Terraform: un mismo directorio con varios estados. Es más compacto, pero es fácil equivocarse de workspace, y por eso muchos equipos lo evitan para separar producción.

El pipeline de producción asume un rol de IAM en la cuenta de producción; el de staging, otro rol en la cuenta de staging. Así un error de configuración en staging no tiene permisos para tocar producción.

### Drift

**Drift** (deriva) es la diferencia entre lo que dice el código y lo que existe realmente, causada por cambios hechos fuera de Terraform: alguien modificó un security group desde la consola, un script cambió un tamaño de instancia.

Terraform lo detecta en el siguiente `plan`: mostrará que quiere "revertir" el cambio manual. Si nadie lo nota, el próximo apply deshace silenciosamente el arreglo que alguien hizo a mano. Por eso conviene correr un **plan programado** (por ejemplo, cada noche) en cada estado y alertar cuando haya diferencias.

### Reemplazos peligrosos y prevent_destroy

Algunos atributos no se pueden cambiar en el lugar: el nombre de un clúster de Aurora, la zona de un volumen, el motor de una base. Cambiarlos implica destruir y crear. Para recursos con datos hay varias protecciones complementarias:

- **`lifecycle { prevent_destroy = true }`:** Terraform falla si un plan intenta destruir ese recurso. Es una red de seguridad en el código.
- **Protección del lado de AWS:** `deletion_protection = true` en RDS/Aurora, bloqueo de objetos en S3. Funciona aunque alguien saltee Terraform.
- **Bloques `moved`:** para renombrar un recurso en el código sin destruirlo, indicando que `aws_rds_cluster.principal` ahora se llama `aws_rds_cluster.main`.
- **Revisión del plan con reglas:** herramientas de política (OPA, Sentinel o checks propios en CI) que bloquean el merge si el plan contiene un reemplazo de recursos marcados como críticos.

### Alternativas

| Herramienta | Lenguaje | Nubes | Comentario |
|---|---|---|---|
| Terraform | HCL | Multi-nube y SaaS | Estándar de facto; licencia BSL desde 2023 |
| OpenTofu | HCL | Multi-nube y SaaS | Bifurcación abierta de Terraform, compatible en la mayoría de los casos |
| CloudFormation | YAML/JSON | Solo AWS | Nativo, estado gestionado por AWS, sin archivo de estado propio |
| AWS CDK | TypeScript, Python, etc. | Solo AWS | Código imperativo que genera CloudFormation |
| Pulumi | TypeScript, Python, Go | Multi-nube | Lenguajes de programación generales, con estado propio |

La elección importa menos que la disciplina: código revisado, plan visible, apply automatizado y estado protegido.

## Casos prácticos

### El plan que iba a recrear la base Aurora de producción

**Situación:** un PR "de limpieza" renombra el identificador del clúster de Aurora de `rumbo-prod` a `rumbo-prod-principal` para seguir una convención nueva. El diff del código es de una línea. El plan, publicado en el PR, muestra `-/+` sobre `aws_rds_cluster.principal` con `# forces replacement`.
**Qué se hace:** el PR no se mergea. Se revierte el cambio de nombre, porque el identificador no es algo que valga la pena cambiar en una base viva. Como lección, se agrega `prevent_destroy` y `deletion_protection` a todas las bases con datos, y un check en CI que falla si un plan contiene destrucción o reemplazo de recursos de tipo `aws_rds_*`, `aws_s3_bucket` o `aws_dynamodb_table`, salvo aprobación explícita.

### Drift tras un cambio manual en un incidente

**Situación:** durante un incidente nocturno, el on-call aumentó desde la consola el tamaño de la instancia de una réplica de lectura de Aurora para aliviar la carga. El incidente se resolvió. Dos semanas después, alguien aplica un cambio no relacionado en el mismo estado y el plan incluye, entre otras cosas, volver la réplica al tamaño anterior. Nadie lo notó en la revisión.
**Qué se hace:** los cambios manuales en incidentes son legítimos, pero el runbook incluye un paso de cierre: abrir un PR que lleve el cambio al código (o revertirlo conscientemente) dentro de las 24 horas. Además, el plan programado nocturno detecta el drift y abre una alerta en el canal del equipo de plataforma. Más contexto en [On-call, runbooks e incidentes](#t/on-call).

### Servicio nuevo en un día con un módulo estándar

**Situación:** el equipo de ML necesita desplegar un servicio nuevo de clasificación de tickets para el asistente de soporte. Necesita un rol de IAM, acceso de lectura a un bucket, un repositorio de imágenes, alarmas y un registro DNS.
**Qué se hace:** en lugar de escribir 300 líneas de HCL, se usa el módulo `servicio-eks` con una docena de variables. El PR es corto, el plan muestra unos 15 recursos nuevos y ninguno destruido, el revisor de plataforma lo aprueba y CI lo aplica en staging y luego en producción. El servicio queda con las mismas protecciones que todos los demás, sin conocimiento especial.

### Dos personas aplicando a la vez sin bloqueo

**Situación:** en un proyecto viejo con el estado en S3 pero sin bloqueo, dos ingenieros corren `apply` desde sus laptops con un minuto de diferencia. Ambos leen el mismo estado, ambos crean recursos, y el segundo en terminar sobrescribe el estado del primero. Resultado: recursos huérfanos que existen en AWS pero no en el estado, y que el próximo apply intentará crear de nuevo (y fallará por nombre duplicado).
**Qué se hace:** a corto plazo, se recuperan los recursos huérfanos con `terraform import` o bloques `import`, comparando con la versión anterior del estado en el bucket versionado. A largo plazo: bloqueo activado en el backend, apply solo desde CI con una cola por estado (un apply a la vez) y permisos de escritura sobre el estado solo para el rol del pipeline.

## Errores comunes

- **Revisar solo el diff del código.** Una línea inocente puede producir un reemplazo. El revisor debe mirar el plan, especialmente los `-/+` y los `destroy`.
- **Aplicar desde la laptop.** Sin trazabilidad, con credenciales personales amplias y riesgo de usar código no mergeado. El apply va por CI.
- **Estados gigantes.** Un único estado con todo vuelve los planes lentos y amplía el radio de impacto de cada error. Dividir por dominio y por ciclo de vida.
- **Pasar secretos por variables de Terraform.** Terminan en el estado en texto plano. Generarlos y guardarlos en un gestor de secretos, y que Terraform solo maneje la referencia.
- **Módulos sin versión.** Referenciar la rama principal de un módulo hace que un cambio ajeno altere tu infraestructura en el próximo plan. Fijar versiones.
- **Ignorar el drift.** Cada cambio manual que no vuelve al código es una sorpresa futura. Plan programado y alerta.

## Para discutir en equipo

- ¿Qué recursos de Rumbo deberían tener `prevent_destroy` y cuáles no tiene sentido proteger?
- ¿Cómo dividimos hoy el estado y qué pasaría si un error de código afectara al estado más grande?
- ¿Qué cambios manuales en incidentes aceptamos y cómo garantizamos que vuelvan al código?
- ¿Qué debería traer por defecto el módulo estándar de servicio que hoy cada equipo agrega a mano?
- ¿Tiene sentido migrar a OpenTofu? ¿Qué ganaríamos y qué riesgo correríamos?
