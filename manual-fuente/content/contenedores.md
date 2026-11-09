---
slug: contenedores
titulo: Contenedores, ECS y EKS
resumen: Cómo empaquetar servicios en contenedores y operarlos con orquestadores como ECS y EKS, con recursos, probes, autoescalado y despliegues seguros.
lectura: 12
---

## La idea central

Un contenedor es una forma de empaquetar una aplicación junto con todo lo que necesita para ejecutarse (bibliotecas, runtime, archivos de configuración) de modo que corra igual en la laptop de un ingeniero, en el CI y en producción. La analogía clásica es la del contenedor de carga: al barco no le importa si adentro hay muebles o café, solo que la caja tenga medidas estándar. Al servidor tampoco le importa si adentro hay un servicio en Go o un modelo en Python.

Pero tener contenedores no alcanza. En producción hay decenas de servicios, cada uno con varias copias, que se caen, se actualizan y tienen que crecer cuando sube el tráfico. Alguien tiene que decidir en qué máquina corre cada copia, reiniciar las que fallan y repartir el tráfico entre las sanas. Ese "alguien" es el **orquestador**. En AWS hay dos opciones principales: **ECS**, el orquestador propio de AWS, y **EKS**, que es Kubernetes gestionado. En Rumbo usamos EKS, y este capítulo explica qué significa eso y qué decisiones hay detrás.

## Conceptos

### Imagen y contenedor

Una **imagen** es la plantilla: un paquete inmutable, construido en capas, que contiene el sistema de archivos de la aplicación. Un **contenedor** es una instancia en ejecución de esa imagen, igual que un proceso es una instancia en ejecución de un binario. De una misma imagen se pueden levantar cien contenedores.

La imagen se construye con un `Dockerfile`, que describe paso a paso cómo armarla: partir de una imagen base, copiar el código, instalar dependencias, definir el comando de arranque. Cada instrucción genera una **capa**; si una capa no cambió, se reutiliza del caché, y eso acelera mucho las construcciones.

Las imágenes se guardan en un **registro**. En AWS el registro gestionado es **ECR** (Elastic Container Registry). Cada imagen se identifica por repositorio y etiqueta (tag), por ejemplo `rumbo/asignacion:1.42.0`, y también por un **digest**, un hash del contenido que nunca cambia.

**Ejemplo:** la imagen del servicio de asignación (Go) puede construirse en dos etapas: una etapa compila el binario con todo el toolchain de Go (unos 800 MB), y la etapa final copia solo el binario a una imagen mínima. Resultado: una imagen de unos 20 MB en lugar de 800 MB. La imagen del modelo de ETA, en cambio, necesita Python, XGBoost y sus dependencias, y suele pesar varios cientos de MB.

**Por qué importa:** el tamaño de la imagen afecta directamente cuánto tarda un pod nuevo en arrancar, porque el nodo tiene que descargarla. En un pico de tráfico, una imagen de 2 GB puede significar un minuto extra antes de que la nueva copia atienda pedidos. Además, conviene desplegar por digest o por tag inmutable: si `latest` cambia de contenido, dos pods "iguales" pueden estar corriendo código distinto.

### Qué hace un orquestador

Un orquestador recibe una descripción del estado deseado ("quiero 6 copias del servicio de asignación, con esta imagen, cada una con 500 milicores de CPU") y trabaja continuamente para que la realidad coincida con esa descripción. Sus tareas principales:

- **Planificación (scheduling):** elegir en qué máquina corre cada copia según los recursos libres.
- **Corrección continua del estado:** si una copia muere, levantar otra; si una máquina desaparece, reubicar sus copias.
- **Descubrimiento de servicios y balanceo:** dar un nombre estable a un conjunto de copias que cambian todo el tiempo.
- **Despliegues:** reemplazar la versión vieja por la nueva de forma gradual.
- **Escalado:** agregar o quitar copias según la carga.

La clave es el modelo **declarativo**: no se le dice "arranca un contenedor en la máquina 3", sino "debe haber 6". La misma idea aparece en [Terraform](#t/terraform), aplicada a la infraestructura.

### ECS y EKS, Fargate y EC2

**ECS** es el orquestador nativo de AWS. Es más simple: menos conceptos, integración directa con IAM, balanceadores y CloudWatch, y no hay un plano de control que operar. Su unidad es la **task** (una o más imágenes que corren juntas) y el **service** (mantiene N tasks vivas).

**EKS** es Kubernetes gestionado: AWS opera el plano de control (la API y la base de estado del clúster) y el equipo opera lo demás. Kubernetes tiene más conceptos y más piezas, pero es un estándar abierto con un ecosistema enorme y corre en cualquier nube o en servidores propios.

En ambos casos hay que decidir **dónde corren los contenedores**:

- **EC2:** el equipo administra un grupo de máquinas virtuales (nodos). Más control (tipos de instancia, GPUs, caché de imágenes en disco local) y mejor costo a gran escala, pero hay que parchar y dimensionar los nodos.
- **Fargate:** AWS provee la capacidad por cada task o pod; no hay nodos que administrar. Es cómodo, pero el costo por unidad de cómputo es mayor, el arranque suele ser más lento y hay limitaciones (por ejemplo, sin GPUs y sin DaemonSets en EKS).

| Criterio | ECS | EKS |
|---|---|---|
| Curva de aprendizaje | Baja | Alta |
| Portabilidad | Solo AWS | Cualquier nube y on-prem |
| Ecosistema | Integraciones de AWS | Helm, operadores, Argo, Karpenter y muchas más |
| Plano de control | Incluido, sin costo aparte | Costo fijo por clúster (orden de magnitud: decenas de USD al mes) |
| Operación | Mínima | Actualizaciones de versión de Kubernetes, add-ons, redes |
| Encaja bien cuando | Equipo chico, todo en AWS, servicios simples | Varios equipos, necesidad de on-prem, cargas variadas (ML, batch, GPU) |

**Por qué importa:** la elección no es técnica en abstracto. Para un equipo de cinco personas con todo en AWS, ECS sobre Fargate suele ser lo más sensato. Rumbo eligió EKS por un motivo de negocio concreto que se ve en los casos prácticos: algunos clientes exigen instalación on-prem.

### Conceptos de Kubernetes

- **Pod:** la unidad mínima. Uno o más contenedores que comparten red (misma IP) y pueden compartir volúmenes. Casi siempre es un contenedor principal y, a veces, uno auxiliar (sidecar), por ejemplo un agente de logs.
- **Deployment:** declara "quiero N réplicas de este pod con esta plantilla" y gestiona las actualizaciones. Por debajo crea un **ReplicaSet** por cada versión.
- **Service:** un nombre DNS y una IP virtual estables que reparten tráfico entre los pods que coinciden con un selector de etiquetas. Los pods mueren y cambian de IP; el Service permanece.
- **Ingress:** reglas para exponer Services hacia afuera del clúster por HTTP (por host y ruta). En EKS, el AWS Load Balancer Controller traduce un Ingress en un ALB real.
- **Namespace:** una partición lógica del clúster. Sirve para separar equipos o entornos y aplicar cuotas y permisos por separado.
- **Helm:** un gestor de paquetes para Kubernetes. Un **chart** es un conjunto de plantillas de manifiestos con valores parametrizables; con el mismo chart se instala el servicio en staging, en producción o en el clúster de un cliente cambiando solo un archivo de valores.

Un manifiesto mínimo de un Deployment del modelo de ETA:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: modelo-eta
  namespace: ml-serving
spec:
  replicas: 4                       # estado deseado: 4 pods
  selector:
    matchLabels:
      app: modelo-eta
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                   # como máximo 1 pod extra durante el despliegue
      maxUnavailable: 0             # nunca bajar de 4 pods listos
  template:
    metadata:
      labels:
        app: modelo-eta
    spec:
      containers:
        - name: servidor
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/rumbo/modelo-eta:2.3.1
          ports:
            - containerPort: 8080
          resources:
            requests:               # lo que se reserva para planificar el pod
              cpu: "500m"           # medio núcleo
              memory: "1Gi"
            limits:
              cpu: "1"              # tope: por encima se estrangula (throttling)
              memory: "1536Mi"      # tope: por encima el contenedor muere (OOMKilled)
          startupProbe:             # da hasta 30 x 5 s = 150 s para cargar el modelo
            httpGet: { path: /healthz, port: 8080 }
            periodSeconds: 5
            failureThreshold: 30
          readinessProbe:           # ¿puede recibir tráfico ahora?
            httpGet: { path: /ready, port: 8080 }
            periodSeconds: 5
            failureThreshold: 2
          livenessProbe:            # ¿el proceso está colgado y hay que reiniciarlo?
            httpGet: { path: /healthz, port: 8080 }
            periodSeconds: 10
            failureThreshold: 3
```

### Requests y limits

Cada contenedor declara dos números por recurso:

1. **Request:** lo que el contenedor necesita como mínimo. El planificador lo usa para decidir en qué nodo cabe el pod: un nodo con 4 núcleos admite pods cuyos requests de CPU sumen hasta 4 (menos lo reservado para el sistema). El request es una reserva, no un tope.
2. **Limit:** el máximo que el contenedor puede usar. Aquí CPU y memoria se comportan distinto:
   - Si un contenedor quiere más **CPU** que su limit, el kernel lo **estrangula** (throttling): sigue vivo pero va más lento. La latencia sube sin que nada "falle".
   - Si quiere más **memoria** que su limit, el kernel lo **mata** (OOMKilled) y Kubernetes lo reinicia.

**Ejemplo:** un nodo de 8 núcleos tiene pods con requests que suman 6 núcleos. Llega un pod nuevo que pide 3: no cabe y queda en estado `Pending` hasta que haya otro nodo. Si ese mismo pod pidiera 1 núcleo pero en la práctica consumiera 3, cabría en el papel y saturaría el nodo en la realidad. Por eso los requests deben reflejar el consumo típico real, medido con métricas, no un número inventado.

Una práctica común es fijar el limit de memoria igual o cercano al request (la memoria no se puede "devolver" bajo presión) y ser más flexible con la CPU. Algunos equipos directamente no ponen limit de CPU para servicios sensibles a latencia y confían en requests bien calibrados; es un debate válido que conviene tener con datos.

**Por qué importa:** el servicio de asignación tiene un presupuesto de unos 50 ms. Un throttling de CPU de 20 ms por ciclo, invisible en los logs, alcanza para romper ese presupuesto.

### Readiness, liveness y startup probes

Kubernetes pregunta periódicamente a cada contenedor cómo está, mediante **probes** (sondas): una petición HTTP, una conexión TCP o un comando.

- **Readiness probe:** "¿puedes atender tráfico ahora?". Si falla, el pod se saca del Service (deja de recibir peticiones), pero no se reinicia. Es para estados transitorios: arrancando, cargando un modelo, sin conexión momentánea a una dependencia crítica.
- **Liveness probe:** "¿estás vivo o colgado?". Si falla varias veces seguidas, Kubernetes **reinicia** el contenedor. Es para estados de los que el proceso no puede salir solo, como un deadlock.
- **Startup probe:** protege el arranque lento. Mientras no pase, las otras dos no se evalúan.

La regla práctica: la liveness debe comprobar solo el propio proceso, nunca dependencias externas. Si la liveness del servicio de asignación consulta la base de datos y la base tiene un problema de 30 segundos, Kubernetes reiniciará todos los pods a la vez, convirtiendo un problema parcial en una caída total.

### Autoescalado de pods y de nodos

Hay dos niveles que trabajan juntos:

1. **Pods:** el **HPA** (Horizontal Pod Autoscaler) ajusta la cantidad de réplicas según una métrica. Con un objetivo de 60 % de CPU, si 4 pods están al 90 %, calcula `4 × 90 / 60 = 6` réplicas. También puede escalar con métricas propias, como peticiones por segundo o atraso de un consumidor de Kafka. El **VPA** (Vertical Pod Autoscaler) ajusta los requests en lugar de la cantidad de pods.
2. **Nodos:** si los pods nuevos quedan `Pending` por falta de espacio, el **Cluster Autoscaler** o **Karpenter** agregan nodos. Karpenter elige el tipo de instancia según lo que los pods necesitan y suele ser más rápido.

**Ejemplo de tiempos (orden de magnitud):** el HPA detecta la subida en 15 a 60 segundos; si hay espacio en nodos existentes, el pod nuevo está listo en 10 a 60 segundos más (descarga de imagen y arranque). Si hace falta un nodo nuevo, se suman uno a tres minutos. En total, de dos a cinco minutos entre el pico y la capacidad nueva.

### Estrategias de despliegue

- **Rolling update:** se reemplazan pods de a poco (`maxSurge`, `maxUnavailable`). Es la opción por defecto y no requiere capacidad doble. Desventaja: durante unos minutos conviven las dos versiones, y el rollback también es gradual.
- **Azul-verde (blue-green):** se levanta la versión nueva completa en paralelo ("verde") y se cambia todo el tráfico de golpe cuando está verificada. El rollback es instantáneo (volver a "azul"), pero se paga el doble de capacidad durante el cambio.
- **Canary:** se manda un porcentaje pequeño del tráfico (1 %, 5 %, 25 %...) a la versión nueva y se comparan métricas (errores, latencia) antes de avanzar. Herramientas como Argo Rollouts o Flagger automatizan el avance y el rollback.

| Estrategia | Costo extra | Velocidad de rollback | Exposición a un error |
|---|---|---|---|
| Rolling | Bajo | Media | Crece gradualmente hasta el 100 % |
| Azul-verde | Alto (doble capacidad) | Inmediata | 100 % al momento del cambio |
| Canary | Bajo a medio | Inmediata | Acotada al porcentaje del canary |

Para un modelo nuevo de ETA, el canary es especialmente útil porque los errores de un modelo no suelen ser excepciones sino predicciones peores, que solo se ven comparando métricas (ver [Serving e inferencia en tiempo real](#t/serving)).

## Casos prácticos

### Clientes grandes que exigen instalación on-prem

**Situación:** dos clientes grandes de Rumbo no permiten que los datos de sus destinatarios salgan de su centro de datos y exigen que la plataforma corra en sus servidores.
**Qué se hace:** se empaqueta cada servicio como chart de Helm y se instala en un clúster Kubernetes del cliente (por ejemplo, una distribución como OpenShift o RKE2). Kubernetes ayuda porque es la misma API en EKS y en el centro de datos del cliente: los mismos Deployments, Services y probes, cambiando solo un archivo de valores (registro de imágenes interno, clase de almacenamiento, sin ALB). Con ECS esto sería imposible, porque solo existe en AWS. El costo es real: hay que probar el chart en clústeres que no controlamos y evitar depender de servicios exclusivos de AWS en el camino crítico. El tema se desarrolla en [Despliegue híbrido y on-prem](#t/hibrido-on-prem).

### El servicio de inferencia que recibe tráfico antes de cargar el modelo

**Situación:** tras cada despliegue del modelo de ETA aparece un pico de errores 503 durante unos 40 segundos. El pod arranca el servidor HTTP en 2 segundos, pero tarda 40 en descargar el modelo de S3 y cargarlo en memoria. La readiness probe solo comprobaba que el puerto respondiera.
**Qué se hace:** el endpoint `/ready` devuelve 200 solo cuando el modelo está cargado y una predicción de prueba funciona. Se agrega una startup probe con margen suficiente para la carga, y se fija `maxUnavailable: 0` para que el rolling update no retire pods viejos hasta que los nuevos estén listos de verdad. Además, se mide el tiempo de carga como métrica, porque si el modelo crece, el margen de la probe deja de alcanzar.

### Vecino ruidoso sin límites de CPU

**Situación:** un job de recálculo de features, desplegado sin requests ni limits, cae en el mismo nodo que pods del servicio de asignación. Cuando corre, consume los 8 núcleos del nodo y la latencia p99 de asignación pasa de 40 ms a 300 ms.
**Qué se hace:** se le asignan requests y limits realistas al job; se aplica un `LimitRange` por namespace para que ningún pod sin valores entre con cero, y un `ResourceQuota` para acotar cuánto puede pedir cada namespace. Las cargas batch se separan en un grupo de nodos propio con taints y tolerations, de modo que nunca compartan máquina con servicios sensibles a latencia.

### Autoescalado lento en un pico

**Situación:** un viernes a las 19:00 los pedidos se triplican en diez minutos. El HPA escala con CPU, los pods nuevos quedan `Pending` esperando nodos y la capacidad llega cuatro minutos tarde. Mientras tanto, se acumulan pedidos sin asignar.
**Qué se hace:** varias medidas complementarias. Escalado programado antes de picos conocidos (el pronóstico de demanda ya sabe cuándo vienen). Escalar con una métrica que anticipa la carga, como pedidos por segundo o atraso del consumidor de Kafka, en vez de CPU, que reacciona tarde. Mantener capacidad ociosa con pods "de relleno" de baja prioridad que Kubernetes desaloja al instante cuando llega un pod real, así el nodo ya existe. Reducir el tamaño de la imagen y el tiempo de arranque. Y usar Karpenter para que los nodos nuevos lleguen antes.

## Errores comunes

- **Desplegar con el tag `latest`.** Hace imposible saber qué versión corre y rompe los rollbacks. Usar tags inmutables o digests.
- **Liveness probe que consulta dependencias externas.** Convierte una falla parcial de la base en reinicios masivos. La liveness verifica solo el proceso; las dependencias, como mucho, en la readiness.
- **Requests inventados.** Requests muy altos desperdician nodos; muy bajos provocan sobrecarga. Calibrarlos con el consumo real observado y revisarlos periódicamente.
- **Ignorar el throttling de CPU.** No genera errores ni reinicios, solo latencia. Vigilar la métrica de throttling de cada contenedor junto con la latencia.
- **Autoescalar solo pods.** Si no hay escalado de nodos, el HPA crea pods que quedan `Pending`. Los dos niveles deben diseñarse juntos y probarse con carga.
- **Elegir Kubernetes por moda.** Si no hay necesidad de portabilidad ni equipo para operarlo, ECS sobre Fargate puede ser mejor decisión.

## Para discutir en equipo

- ¿Qué servicios de Rumbo deberían tener limit de CPU y cuáles no? ¿Qué datos necesitamos para decidirlo?
- ¿Qué métrica anticipa mejor la carga del servicio de asignación para el HPA: CPU, pedidos por segundo o atraso en Kafka?
- ¿Qué dependencias de AWS en el camino crítico nos impiden hoy instalar la plataforma completa en el clúster de un cliente?
- ¿Para qué cambios vale la pena un canary y para cuáles alcanza con un rolling update?
- ¿Cuánto nos cuesta mantener capacidad ociosa para picos frente a lo que perdemos con pedidos asignados tarde?
