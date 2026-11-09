---
slug: aws
titulo: Fundamentos de AWS
resumen: Los bloques básicos de AWS (regiones, cuentas, IAM, redes, balanceadores y auditoría) para diseñar y revisar infraestructura segura y resistente a fallas.
lectura: 13
---

## La idea central

AWS ofrece cientos de servicios, pero casi toda la infraestructura de un sistema como Rumbo se apoya en un puñado de ideas: **dónde** corren las cosas (regiones y zonas), **quién** puede hacer qué (cuentas e IAM), **cómo** se conectan (VPC, subredes, balanceadores) y **cómo** se audita lo que pasó (CloudTrail y CloudWatch). Entender estas piezas permite leer un diagrama de arquitectura y hacer las preguntas correctas: ¿qué pasa si cae esta zona?, ¿quién puede leer esta base?, ¿por qué este tráfico sale a internet?

Una analogía útil: una región es una ciudad, cada zona de disponibilidad es un edificio independiente dentro de esa ciudad, la VPC es el terreno cercado donde construimos, las subredes son las habitaciones, los security groups son las cerraduras de cada puerta e IAM es el sistema de credenciales que dice quién puede entrar a cada habitación y qué puede tocar.

## Conceptos

### Regiones y zonas de disponibilidad

Una **región** es un área geográfica (por ejemplo, `us-east-1` en Virginia o `sa-east-1` en San Pablo) con su propio conjunto de servicios. Las regiones son independientes entre sí: una falla en una no debería afectar a otra, y los datos no salen de una región salvo que se configure explícitamente.

Cada región tiene varias **zonas de disponibilidad** (AZ, por availability zone), típicamente tres o más. Una AZ es uno o más centros de datos con energía, refrigeración y red propias, separados físicamente de las otras zonas pero conectados con baja latencia (del orden de 1 a 2 ms).

**Ejemplo:** el servicio de asignación corre con 6 pods repartidos en tres AZ (2 por zona). Si una zona entera falla, quedan 4 pods. Si el sistema necesita al menos 4 para el tráfico de hora pico, sobrevive; si necesita 5, no. Diseñar para fallas de zona significa dimensionar con N+1 zonas: con tres zonas, cualquier par debe poder con toda la carga.

**Por qué importa:** la mayoría de las fallas de infraestructura afectan a una zona, no a una región entera. Desplegar en varias zonas es la medida de disponibilidad más barata y efectiva. Desplegar en varias regiones es mucho más caro y complejo, y se justifica solo con requisitos muy exigentes (ver [Baja latencia y alta disponibilidad](#t/latencia-disponibilidad)).

### Cuentas separadas y AWS Organizations

Una **cuenta de AWS** es la unidad de aislamiento más fuerte: los recursos, permisos y límites de una cuenta no se mezclan con los de otra salvo que se configure explícitamente. Por eso la práctica recomendada es tener **muchas cuentas**, no una sola con todo adentro.

**AWS Organizations** agrupa las cuentas bajo una cuenta de gestión, organizadas en unidades organizativas (OU). Permite aplicar **SCP** (Service Control Policies): reglas que limitan lo que cualquier usuario o rol puede hacer en las cuentas de una OU, incluso si tiene permisos de administrador dentro de ella.

Una estructura típica en Rumbo:

- Cuenta de gestión (solo facturación y Organizations, nadie trabaja ahí).
- Cuenta de seguridad (recibe los logs de CloudTrail de todas, solo lectura para auditoría).
- Cuentas de cargas: `dev`, `staging`, `prod`, y una `prod-datos-personales` separada.
- Cuenta de red compartida, si se centraliza la conectividad.

**Ejemplo de SCP:** "en la OU de producción, nadie puede desactivar CloudTrail ni crear recursos fuera de `us-east-1` y `us-east-2`". Aunque un rol tenga `AdministratorAccess`, la SCP lo impide.

**Por qué importa:** si un ingeniero se equivoca en dev, o una credencial de dev se filtra, el daño queda contenido en esa cuenta. Además, la factura por cuenta muestra cuánto cuesta cada entorno.

### IAM: identidades, roles y políticas

**IAM** (Identity and Access Management) decide quién puede hacer qué sobre qué recurso. Sus piezas:

- **Usuario IAM:** una identidad con credenciales de larga duración (contraseña o claves de acceso). Hoy se recomienda evitarlos para personas: se usa inicio de sesión centralizado (IAM Identity Center con el proveedor de identidad de la empresa).
- **Rol:** una identidad sin credenciales propias que alguien o algo **asume** temporalmente. Lo asumen personas (vía inicio de sesión centralizado), servicios (un pod en EKS, una función Lambda) o pipelines de CI.
- **Política:** un documento JSON que lista permisos: qué acciones (`s3:GetObject`), sobre qué recursos (un ARN), con qué condiciones.
- **Credenciales temporales:** al asumir un rol, STS entrega credenciales que expiran (por defecto en una hora, configurable). Si se filtran, dejan de servir solas.

El principio rector es el **mínimo privilegio**: cada identidad tiene solo los permisos que necesita para su función, sobre los recursos concretos que usa. Un ejemplo de política para el servicio del modelo de ETA, que solo debe leer artefactos del modelo:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LeerArtefactosDelModeloETA",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::rumbo-modelos-prod/eta/*"
    },
    {
      "Sid": "ListarSoloElPrefijoETA",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::rumbo-modelos-prod",
      "Condition": {
        "StringLike": { "s3:prefix": ["eta/*"] }
      }
    }
  ]
}
```

Comparar con `"Action": "s3:*", "Resource": "*"`: esa política permitiría leer, sobrescribir y borrar cualquier bucket de la cuenta, incluidos los que tienen datos personales.

En EKS, cada service account de Kubernetes se asocia a un rol de IAM (con IRSA o EKS Pod Identity). Así cada pod obtiene credenciales temporales de su propio rol, y no las del nodo, que serían compartidas por todos los pods que corren en él.

### VPC, subredes y NAT gateway

Una **VPC** (Virtual Private Cloud) es una red privada aislada dentro de una región, con un rango de direcciones propio (por ejemplo, `10.20.0.0/16`, unas 65.000 direcciones). Dentro se crean **subredes**, cada una en una sola AZ:

- **Subred pública:** su tabla de rutas envía el tráfico de internet a un **internet gateway**. Los recursos con IP pública son alcanzables desde internet (si los security groups lo permiten). Aquí van los balanceadores públicos y los NAT gateways.
- **Subred privada:** no tiene ruta directa desde internet. Aquí van los nodos de EKS, las bases de datos y casi todo lo demás.

Los recursos privados a veces necesitan **salir** a internet (descargar dependencias, llamar a una API externa de clima). Para eso está el **NAT gateway**: vive en una subred pública y permite conexiones salientes desde subredes privadas, sin permitir conexiones entrantes. Su costo se calcula por hora y por cada GB procesado.

Diagrama de una VPC típica de producción de Rumbo:

```text
                                Internet
                                   |
                          [ Internet Gateway ]
                                   |
+-------------------- VPC 10.20.0.0/16 (us-east-1) --------------------+
| AZ a                   AZ b                   AZ c                   |
| +--------------------+ +--------------------+ +--------------------+ |
| | Pública            | | Pública            | | Pública            | |
| | 10.20.0.0/24       | | 10.20.1.0/24       | | 10.20.2.0/24       | |
| | ALB, NAT gw        | | ALB, NAT gw        | | ALB, NAT gw        | |
| +--------------------+ +--------------------+ +--------------------+ |
|           |                      |                      |            |
| +--------------------+ +--------------------+ +--------------------+ |
| | Privada (apps)     | | Privada (apps)     | | Privada (apps)     | |
| | 10.20.16.0/20      | | 10.20.32.0/20      | | 10.20.48.0/20      | |
| | nodos EKS          | | nodos EKS          | | nodos EKS          | |
| +--------------------+ +--------------------+ +--------------------+ |
|           |                      |                      |            |
| +--------------------+ +--------------------+ +--------------------+ |
| | Privada (datos)    | | Privada (datos)    | | Privada (datos)    | |
| | 10.20.64.0/24      | | 10.20.65.0/24      | | 10.20.66.0/24      | |
| | Aurora escritor    | | Aurora réplica     | | MSK (Kafka)        | |
| +--------------------+ +--------------------+ +--------------------+ |
|                                                                      |
| Gateway endpoint: S3                                                 |
| Interface endpoints: ECR, STS, Secrets Manager                       |
+----------------------------------------------------------------------+
```

Las subredes de aplicaciones son grandes (`/20`, unas 4.000 direcciones) porque en EKS cada pod consume una IP de la VPC; quedarse sin direcciones es un problema real en clústeres que crecen.

### Security groups frente a NACLs

Hay dos mecanismos de filtrado de tráfico:

- **Security group (SG):** un firewall asociado a cada interfaz de red (una instancia, un pod con IP propia, una base). Es **con estado** (stateful): si se permite una conexión entrante, la respuesta sale automáticamente. Solo tiene reglas de "permitir". Y puede referenciar a otro security group como origen: "permitir el puerto 5432 desde el SG de los nodos de EKS", sin tener que listar IPs.
- **NACL (Network ACL):** un filtro a nivel de subred. Es **sin estado** (stateless): hay que permitir explícitamente tanto la ida como la vuelta, incluidos los puertos efímeros de respuesta. Tiene reglas de permitir y denegar, evaluadas en orden numérico.

| Aspecto | Security group | NACL |
|---|---|---|
| Se aplica a | Interfaz de red (recurso) | Subred completa |
| Estado | Con estado | Sin estado |
| Reglas | Solo permitir | Permitir y denegar |
| Referencia a otros grupos | Sí | No, solo rangos de IP |
| Uso típico | Control principal, fino | Barrera gruesa adicional (bloquear un rango) |

**Por qué importa:** en la práctica, casi todo el control se hace con security groups referenciándose entre sí ("la base acepta conexiones solo desde el SG del servicio de asignación"). Las NACLs se dejan con reglas amplias o se usan para bloqueos excepcionales; usarlas como control principal genera errores difíciles de diagnosticar por su naturaleza sin estado.

### VPC endpoints y PrivateLink

Por defecto, cuando un pod en una subred privada llama a S3 o a la API de ECR, el tráfico sale por el NAT gateway hacia el endpoint público del servicio. Los **VPC endpoints** permiten llegar a servicios de AWS sin salir de la red privada:

- **Gateway endpoint:** solo para S3 y DynamoDB. Es una entrada en la tabla de rutas. **No tiene costo**.
- **Interface endpoint (PrivateLink):** crea una interfaz de red con IP privada dentro de la subred, que representa al servicio (ECR, STS, Secrets Manager, CloudWatch, y muchos más). Su costo es por hora y por GB, pero mucho menor que el de un NAT por GB en volúmenes altos.

**PrivateLink** también permite exponer un servicio propio a otra VPC (de otra cuenta o de un cliente) sin conectar las redes completas: el consumidor ve solo un endpoint, no la red del proveedor.

Además, las políticas de endpoint y de bucket permiten exigir que el acceso a un bucket llegue solo desde un endpoint concreto, lo que agrega una capa de protección para datos sensibles.

### Balanceadores: ALB y NLB

- **ALB (Application Load Balancer):** trabaja en capa 7 (HTTP/HTTPS, gRPC). Entiende rutas, hosts y cabeceras: puede mandar `/api/seguimiento` a un servicio y `/api/soporte` a otro. Termina TLS, se integra con un firewall de aplicaciones (WAF) y con autenticación. Es el que crea el Ingress de EKS.
- **NLB (Network Load Balancer):** trabaja en capa 4 (TCP/UDP). No mira el contenido; reenvía conexiones con latencia muy baja, soporta volúmenes enormes y ofrece IPs estáticas por zona. Es la base para exponer servicios por PrivateLink.

**Ejemplo:** la API pública de seguimiento en vivo que usan los comercios va detrás de un ALB con WAF y reglas por ruta. Un cliente que exige allowlist de IPs fijas en su firewall recibe un NLB, porque el ALB no tiene IPs estáticas.

### Modelo de responsabilidad compartida

AWS es responsable de la seguridad **de** la nube: centros de datos, hardware, la red física, el hipervisor y, en servicios gestionados, el sistema operativo y el motor. El cliente es responsable de la seguridad **en** la nube: configuración de IAM, security groups, cifrado, parches de sus instancias y de sus imágenes, y qué datos guarda y quién accede.

El reparto se mueve según el servicio: en EC2 el cliente parcha el sistema operativo; en Aurora, AWS parcha el motor, pero la configuración de acceso, los backups retenidos y el cifrado siguen siendo responsabilidad del equipo.

**Por qué importa:** un bucket público con datos de destinatarios no es una falla de AWS; es una falla de configuración nuestra.

### CloudTrail y CloudWatch

- **CloudTrail** registra cada llamada a la API de AWS: quién (qué identidad), qué acción, sobre qué recurso, desde qué IP y cuándo. Es la herramienta de auditoría y la primera fuente en un incidente de seguridad. Conviene enviar los registros de todas las cuentas a la cuenta de seguridad, con protección contra borrado.
- **CloudWatch** reúne métricas (CPU de una base, conexiones, errores del balanceador), logs y alarmas de los servicios de AWS. Muchos equipos usan Prometheus y Grafana para métricas de aplicación (ver [Prometheus y Grafana](#t/prometheus-grafana)), pero las métricas de los servicios gestionados de AWS nacen en CloudWatch.

## Casos prácticos

### Claves de acceso en el historial de un repositorio

**Situación:** un escáner detecta que hace tres meses alguien commiteó un archivo con claves de acceso de un usuario IAM con permisos amplios en la cuenta de staging. El commit se borró después, pero sigue en el historial de git.
**Qué se hace:** primero, **desactivar y rotar** las claves de inmediato; reescribir el historial de git no sirve, porque cualquiera pudo haberlas copiado. Segundo, revisar en CloudTrail todas las llamadas hechas con esa clave desde que se filtró, buscando IPs o acciones inusuales. Tercero, eliminar la causa raíz: reemplazar el usuario IAM por un rol que el proceso asuma con credenciales temporales (en CI, con federación OIDC, sin claves guardadas). Y agregar escaneo de secretos en pre-commit y en CI.

### Aislar el entorno que guarda datos personales de destinatarios

**Situación:** nombres, teléfonos y direcciones de destinatarios viven hoy en la misma cuenta y VPC que el resto de producción, incluidos jobs de análisis y el agente interno de operaciones.
**Qué se hace:** se mueve el servicio que guarda la PII y su base a una cuenta `prod-datos-personales` propia. Solo expone una API mínima por PrivateLink a la cuenta de producción general. Una SCP impide desactivar el cifrado y CloudTrail en esa cuenta. El acceso humano requiere un rol especial con aprobación y sesión registrada. Los demás sistemas trabajan con identificadores seudónimos y solo el servicio de notificaciones resuelve el teléfono real. Así, una credencial filtrada de un job de análisis no alcanza la PII.

### Cae una zona de disponibilidad

**Situación:** una AZ de `us-east-1` tiene problemas de red durante 40 minutos. Un tercio de los nodos de EKS dejan de responder y el escritor de Aurora estaba en esa zona.
**Qué se hace:** si el diseño es correcto, el ALB deja de enviar tráfico a los destinos de esa zona por los health checks, Aurora promueve una réplica de otra zona (ver [RDS y Aurora](#t/rds-aurora)), y Kubernetes reprograma los pods en las zonas sanas. Para que esto funcione, hay que haberlo preparado: capacidad suficiente en dos zonas para toda la carga, reglas de distribución de pods entre zonas (topology spread constraints), un NAT gateway por zona (si hay uno solo y está en la zona caída, nadie sale a internet) y réplica de Aurora en otra zona. Conviene ensayar la pérdida de una zona en staging.

### Factura alta por tráfico a S3 vía NAT

**Situación:** la factura del NAT gateway sube mucho de un mes a otro. El análisis muestra que el entrenamiento del modelo de ETA y el pronóstico de demanda leen varios TB por día de S3 desde subredes privadas, y todo ese tráfico pasa por el NAT, cuyo costo crece con cada GB procesado.
**Qué se hace:** se agrega un **gateway endpoint de S3** a las tablas de rutas de las subredes privadas. No tiene costo y el tráfico deja de pasar por el NAT. Con una cifra hipotética de 5 TB diarios y un costo por GB de NAT del orden de centavos de dólar, el ahorro es de miles de dólares al mes. Se aprovecha para agregar interface endpoints de ECR (las descargas de imágenes también pasaban por el NAT). Más en [Costos cloud (FinOps)](#t/finops).

## Errores comunes

- **Una sola cuenta para todo.** Un error o una filtración en dev alcanza producción. Separar por entorno y por sensibilidad de datos.
- **Políticas con `*` en acción y recurso.** Son cómodas al principio y peligrosas siempre. Acotar a acciones y ARNs concretos, y revisar con IAM Access Analyzer qué permisos se usan realmente.
- **Claves de acceso de larga duración.** En laptops, en CI o en el código. Usar roles con credenciales temporales en todos los casos posibles.
- **Un único NAT gateway.** Ahorra unos dólares y crea un punto único de falla para la salida a internet. Uno por zona en producción.
- **Bases en subredes públicas "por comodidad".** Aunque el security group las proteja, un cambio de regla las expone a internet. Las bases van en subredes privadas siempre.
- **CloudTrail desactivado o en la misma cuenta que audita.** Quien compromete la cuenta puede borrar el rastro. Centralizar en una cuenta de seguridad con protección contra borrado.

## Para discutir en equipo

- ¿Nuestro sistema sobrevive hoy la pérdida de una zona completa? ¿Cómo lo sabemos sin haberlo probado?
- ¿Qué identidades tienen hoy permisos más amplios de los que usan, y cómo lo detectamos sistemáticamente?
- ¿Qué tráfico interno sigue pasando por el NAT gateway y podría ir por endpoints?
- ¿Qué sistemas de Rumbo realmente necesitan la PII de los destinatarios y cuáles podrían trabajar con identificadores seudónimos?
- ¿Qué SCP deberían aplicarse a la OU de producción que hoy no tenemos?
