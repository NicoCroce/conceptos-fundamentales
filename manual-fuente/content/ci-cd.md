---
slug: ci-cd
titulo: CI/CD y GitOps
resumen: Cómo automatizar el camino de un cambio desde el commit hasta producción con pipelines rápidos, artefactos inmutables, credenciales temporales y estado deseado en git.
lectura: 15
---

## La idea central

Cada cambio que llega a producción se escribe, se revisa, se compila, se prueba, se empaqueta y se despliega. Si ese camino depende de pasos manuales, cada despliegue es un evento con riesgo y el equipo despliega menos seguido, con cambios más grandes y más difíciles de revertir. **CI/CD** propone automatizar ese camino completo para que desplegar sea aburrido, frecuente y reversible.

La analogía útil es una línea de montaje con controles de calidad en cada estación: la pieza avanza sola y cualquier estación puede rechazarla. **GitOps** agrega que el estado de cada entorno vive en git y un agente dentro del clúster hace que la realidad coincida con lo escrito. Con LLMs, por la línea pasan piezas nuevas (prompts, versiones de modelo, suites de evaluación) y aparece un actor nuevo: agentes de código que abren pull requests y a veces ejecutan pipelines.

## Conceptos

### Integración continua, entrega continua y despliegue continuo

Son tres prácticas distintas que suelen mezclarse bajo la misma sigla:

1. **Integración continua (CI):** cada cambio se integra a la rama principal con frecuencia (idealmente varias veces al día) y cada integración dispara una verificación automática: compilar, correr linters y tests. El objetivo es detectar conflictos y errores a los minutos, no a las semanas.
2. **Entrega continua (continuous delivery):** además de verificar, el pipeline produce un artefacto listo para desplegar y lo lleva automáticamente hasta un entorno previo a producción. Pasar a producción es una decisión humana de un clic.
3. **Despliegue continuo (continuous deployment):** no hay clic. Todo cambio que pasa los controles llega a producción solo.

**Ejemplo:** el servicio de asignación de Rumbo tiene unos 15 merges por día. Con entrega continua, cada merge llega a staging en unos 12 minutos y alguien de guardia promueve a producción dos veces por día, agrupando unos 7 cambios por promoción. Con despliegue continuo, cada uno de los 15 cambios llega solo a producción, con canary automático: si algo falla, se sabe exactamente qué cambio lo causó.

**Por qué importa:** el despliegue continuo exige controles automáticos muy confiables (tests, canary con métricas, rollback automático). Si no existen, la entrega continua con una promoción humana es el punto de partida razonable.

### Etapas de un pipeline y retroalimentación rápida

Un pipeline típico tiene estas etapas, en orden:

- **Lint y formato:** errores de estilo, imports sin uso, tipos. Tarda segundos y atrapa muchos errores baratos.
- **Tests:** unitarios primero, luego de integración (contra una base de datos efímera, por ejemplo).
- **Build:** compilar y construir la imagen del contenedor.
- **Escaneo de la imagen:** buscar vulnerabilidades conocidas en el sistema base y en las dependencias, y secretos filtrados.
- **Publicación del artefacto:** subir la imagen al registro (ECR) y registrar su identificador.
- **Deploy:** actualizar el entorno destino.

La propiedad más valiosa de un pipeline es la **velocidad de retroalimentación**. Si un PR tarda 40 minutos en dar resultado, los ingenieros cambian de tarea y acumulan cambios. Conviene fijar un **presupuesto de tiempo**: por ejemplo, 10 minutos desde el push hasta el resultado.

**Ejemplo:** el pipeline del modelo de ETA corre en serie: lint 1 min, tests unitarios 4 min, tests de integración 5 min, build 6 min, escaneo 1 min. Total: 17 minutos. Tres cambios lo bajan a unos 7:

1. **Paralelismo:** lint, tests unitarios y build no dependen entre sí; corren a la vez. El tiempo pasa a ser el de la rama más larga.
2. **Caché de dependencias:** instalar las bibliotecas de Python tardaba 3 de los 6 minutos del build. Con caché por hash del archivo de dependencias, solo se reinstalan cuando ese archivo cambia.
3. **Caché de capas de la imagen:** si solo cambió el código, las capas del sistema base y de las dependencias se reutilizan (ver [Contenedores, ECS y EKS](#t/contenedores)).

Además, los tests de integración se dividen en 3 grupos paralelos y bajan de 5 a 2 minutos.

### Construir una vez, promover el mismo artefacto

Un error clásico es reconstruir la imagen para cada entorno a partir del mismo commit. Parecen iguales, pero una dependencia sin versión fija o la imagen base pudieron cambiar entre una construcción y otra: lo probado en staging no es lo que llega a producción.

La regla es **construir una vez y promover el mismo artefacto** por dev, staging y producción. Lo que cambia entre entornos es la configuración (variables, secretos, réplicas), nunca la imagen.

Para garantizarlo, se despliega por **digest** y no por tag. El tag (`rumbo/asignacion:1.42.0`) es una etiqueta que se puede mover a otra imagen; el digest (`sha256:9f2c...`) es un hash del contenido. Además, conviene activar tags inmutables en ECR.

**Ejemplo:** el pipeline construye la imagen del commit `a1b2c3`, obtiene el digest `sha256:9f2c...e41` y lo escribe en los manifiestos de staging. Cuando se promueve a producción, se copia ese mismo digest, no el tag. Un mes después, el digest dice sin ambigüedad qué corría en producción.

### GitHub Actions: workflows, jobs y runners

GitHub Actions es el sistema de CI integrado a GitHub. Sus piezas:

- **Workflow:** un archivo YAML en `.github/workflows/` que define cuándo se ejecuta (un push, un PR, un horario, un disparo manual) y qué hace.
- **Job:** un grupo de pasos que corre en una misma máquina. Los jobs corren en paralelo salvo que uno declare que depende de otro (`needs`).
- **Step:** un comando o una **action** (un componente reutilizable publicado por terceros o por el propio equipo).
- **Runner:** la máquina que ejecuta el job. Puede ser alojada por GitHub (efímera: se crea para el job y se destruye al terminar) o **self-hosted** (una máquina propia).

```yaml
name: ci-asignacion
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read            # por defecto, el token del workflow solo lee

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@<sha-de-40-caracteres>   # fijada por SHA
      - run: go vet ./... && go test ./...

  imagen:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write       # necesario para pedir el token OIDC
    steps:
      - uses: actions/checkout@<sha-de-40-caracteres>
      - uses: aws-actions/configure-aws-credentials@<sha-de-40-caracteres>
        with:
          role-to-assume: arn:aws:iam::111111111111:role/ci-publicar-imagenes
          aws-region: us-east-1
      - run: ./scripts/build-y-publicar.sh
```

Los runners self-hosted dan acceso a la red interna, GPUs y caché persistente, pero tienen riesgos. Si el runner es **persistente**, un job malicioso puede dejar algo instalado que afecte a los siguientes. Si tiene **credenciales o acceso de red amplios**, todo código que corra ahí los hereda. Y si atiende PRs de forks de un repositorio público, cualquiera puede ejecutar código dentro de la red interna. Lo sano: runners efímeros (uno nuevo por job), separados por nivel de confianza y sin código no revisado.

### Federación OIDC en lugar de claves guardadas

Para publicar una imagen en ECR o aplicar un plan de [Terraform](#t/terraform), el pipeline necesita credenciales de AWS. La forma antigua era guardar como secreto del repositorio la clave de larga duración de un usuario de IAM: no vence, sirve desde cualquier lugar y, si se filtra, funciona hasta que alguien la revoque.

La alternativa es la **federación OIDC**:

1. En AWS se registra a GitHub como proveedor de identidad confiable.
2. Cuando un job corre, pide a GitHub un **token firmado** de corta duración que dice quién es: qué repositorio, qué rama, qué entorno.
3. El job presenta ese token a AWS STS y pide asumir un rol.
4. AWS verifica la firma y las condiciones del rol, y entrega credenciales temporales (por ejemplo, válidas por una hora).

La seguridad está en la **política de confianza** del rol, que dice qué identidades pueden asumirlo:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringEquals": {
      "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
      "token.actions.githubusercontent.com:sub": "repo:rumbo/asignacion:ref:refs/heads/main"
    }
  }
}
```

Solo los workflows de `main` en `rumbo/asignacion` pueden asumir el rol; otra rama u otro repositorio, no. Para producción conviene condicionar al **entorno** de GitHub (`repo:rumbo/asignacion:environment:prod`), que exige aprobación humana.

**Por qué importa:** desaparece el secreto de larga duración. Lo que hay que revisar con cuidado es la condición: un comodín como `repo:rumbo/*` abre el rol a cualquier repositorio.

### Seguridad de la cadena de suministro

El pipeline ejecuta código de terceros (actions, imágenes base, bibliotecas), y cada uno es una puerta de entrada:

- **Fijar actions por SHA**, no por tag. `@v3` ejecuta lo que el autor, o un atacante con acceso a su cuenta, apunte hoy a ese tag; ya ocurrió con actions populares que pasaron a filtrar secretos. Un SHA no se puede mover.
- **SBOM (Software Bill of Materials):** inventario de componentes y versiones de una imagen. Ante una vulnerabilidad nueva, dice en minutos qué imágenes la contienen.
- **Firma de imágenes:** el pipeline firma el digest (por ejemplo, con cosign) y el clúster solo admite imágenes firmadas; una subida a mano no se despliega.
- **Procedencia (provenance):** documento firmado que dice qué commit, workflow y runner produjeron el artefacto (marco SLSA).
- **Actualización de dependencias:** bots como Dependabot o Renovate abren PRs con versiones nuevas, incluidos los SHA de las actions.

**Ejemplo de `pull_request_target`:** este disparador sirve para comentar o etiquetar PRs de forks y, a diferencia de `pull_request`, corre en el contexto del repositorio base, **con secretos y un token con escritura**. Si además hace checkout del código del PR y lo ejecuta (`npm install`, `make test`), un atacante abre un PR desde un fork con un script de instalación que envía las variables de entorno a un servidor externo: secretos filtrados sin ninguna aprobación. La regla: con `pull_request_target`, nunca ejecutar código del PR; los tests de forks van con `pull_request`, que no tiene secretos.

### GitOps: estado deseado en git y reconciliación

En un pipeline tradicional ("push"), el CI tiene credenciales del clúster y ejecuta `kubectl apply` o `helm upgrade`. En **GitOps** el flujo se invierte ("pull"):

1. Un repositorio de configuración contiene los manifiestos de cada entorno: qué imagen (por digest), cuántas réplicas, qué configuración.
2. Un agente que corre dentro del clúster (**Argo CD** o **Flux**) lee ese repositorio cada pocos minutos o ante un aviso.
3. Compara lo escrito con lo que corre y aplica la diferencia. Esa comparación permanente se llama **reconciliación** (en inglés, *reconciliation loop*).

El CI ya no necesita credenciales del clúster: termina al proponer un commit que cambia el digest en el repositorio de configuración. Si alguien edita un Deployment a mano, el agente detecta el **drift** y lo marca o lo revierte solo (self-heal). Y el **rollback es `git revert`** del commit que cambió el digest: la imagen anterior sigue en el registro.

| Aspecto | Push desde CI | GitOps (pull) |
|---|---|---|
| Credenciales del clúster | En el CI | Solo dentro del clúster |
| Fuente de verdad | El último pipeline que corrió | El repositorio de configuración |
| Cambios manuales | Persisten hasta el próximo deploy | Se detectan y se revierten |
| Rollback | Volver a correr un pipeline viejo | `git revert` |
| Auditoría | Logs del CI | Historial de git |

### Entornos, aprobaciones y feature flags

Los **entornos** de GitHub (dev, staging, prod) exigen reglas antes de que un job corra: revisores obligatorios, espera mínima, ramas permitidas. Junto con la condición OIDC por entorno, nadie llega a producción sin aprobación aunque modifique el workflow.

Además, **desplegar no es lanzar**: desplegar es poner el código en producción; lanzar (release) es que los usuarios vean el comportamiento nuevo. Las **feature flags** separan ambos: el código llega desactivado y se enciende después, por porcentaje o por zona, sin desplegar. El canary y el azul-verde, que actúan sobre versiones y no sobre funcionalidades, se tratan en [Contenedores, ECS y EKS](#t/contenedores).

**Ejemplo:** el resumen automático de casos del asistente de soporte se despliega desactivado un lunes, se activa para el 5 % de los tickets el martes y para el 50 % el jueves. Si suben los resúmenes marcados como incorrectos, se desactiva en segundos, sin pipeline.

### Pipelines para cambios de ML y de LLMs

En sistemas con LLMs, el comportamiento cambia también con el **prompt**, la **versión del modelo**, los parámetros (temperatura, máximo de tokens) y el índice del RAG. Si esas piezas se editan a mano en una consola, cambian sin revisión ni historial.

La práctica es tratarlas como código:

- Los **prompts** viven en el repositorio, versionados, y se revisan en PRs.
- La **versión del modelo** se fija explícitamente (un identificador con fecha o versión, no un alias genérico que el proveedor puede mover).
- La **suite de evaluación** (casos de prueba con respuesta esperada o criterios) también vive en el repo y corre en el pipeline (ver [Evaluación de LLMs](#t/evaluacion-llms)).

Un cambio de prompt pasa por un **gate de evaluación offline**: el pipeline corre el prompt nuevo contra el golden set y compara con la versión en producción.

**Ejemplo:** el golden set del asistente de soporte tiene 400 casos. El gate exige: precisión de clasificación de tickets de al menos 92 %, fidelidad a las fuentes (medida con un LLM juez) de al menos 0,90 y ninguna caída de más de 2 puntos respecto de producción en ninguna categoría. Correr la suite consume unos 400 × 3.000 = 1,2 millones de tokens; a un precio hipotético de 3 USD por millón, son menos de 4 USD por ejecución. Por eso corre solo cuando el PR toca prompts, configuración del modelo o código del asistente.

### Agentes de código dentro del pipeline

Los agentes de código abren PRs (corregir un test, actualizar una dependencia) y a veces corren dentro del CI respondiendo a issues. Son un actor más del pipeline, con dos diferencias: se equivocan con mucha confianza y **leen texto que no controlamos** (ver [Agentes y tool calling](#t/agentes)).

Permisos razonables para un agente de código:

- **Token de solo lectura** sobre el repositorio; sus cambios llegan como PR desde una rama propia, nunca con permiso de merge a `main` ni de saltear protecciones.
- **Sin credenciales de producción.** El rol OIDC de producción está condicionado a `main` y al entorno `prod`; una rama del agente no lo puede asumir.
- **Revisión humana obligatoria**, con CODEOWNERS sobre `.github/workflows/`, los manifiestos de producción y los prompts.

El riesgo específico es la **inyección de prompts**: un issue, la descripción de un PR o un archivo del repo pueden traer instrucciones para el agente ("agrega este paso al workflow"). La defensa principal no es pedirle que no obedezca, sino que **no tenga nada valioso que entregar**: permisos mínimos, sin secretos y con un humano entre su PR y producción.

## Casos prácticos

### Claves de AWS filtradas desde el CI

**Situación:** un workflow de depuración imprimía las variables de entorno en el log, incluida la clave de larga duración de un usuario de IAM administrador de la cuenta de staging. Toda la organización podía leer esos logs.
**Qué se hace:** se desactiva la clave de inmediato y se revisa CloudTrail para detectar usos desde direcciones desconocidas. Luego se elimina el usuario de IAM y se reemplaza por roles OIDC, uno por propósito: `ci-publicar-imagenes` (solo escritura en ECR), `ci-terraform-staging` y `ci-terraform-prod`, cada uno con su condición de repositorio, rama y entorno. Un check falla si algún workflow referencia `AWS_ACCESS_KEY_ID`.

### Un cambio de prompt que pasó los tests y bajó la calidad

**Situación:** un ingeniero acorta el system prompt del asistente de soporte para reducir tokens: de 1.800 a 1.100 tokens por llamada, un 40 % menos de costo de entrada. Los tests unitarios pasan, porque solo verifican el formato JSON de la respuesta. El gate de evaluación muestra que la clasificación general baja de 93 % a 91,5 %, y la categoría "reclamo por entrega fallida" cae de 90 % a 81 %: el prompt recortado había perdido dos ejemplos de esa categoría.
**Qué se hace:** el gate bloquea el merge, porque una categoría cae más de 2 puntos. El ingeniero restaura los dos ejemplos y recorta en otro lado; el nuevo intento queda en 1.300 tokens y pasa el gate. Sin el gate, la caída se habría notado semanas después, en las quejas de los comercios.

### Staging y producción que divergieron

**Situación:** antes de adoptar GitOps, el pipeline hacía `helm upgrade` desde el CI. Durante un incidente, alguien subió a mano las réplicas del modelo de ETA en producción y cambió una variable de timeout. Meses después, un problema que no se reproducía en staging llevó dos días de investigación: nadie sabía cuántas diferencias había.
**Qué se hace:** se migra a Argo CD con un repositorio de configuración por entorno y self-heal activado en producción. Al importar el estado, Argo CD muestra 23 diferencias entre lo que estaba en los charts y lo que corría. Se revisan una por una: algunas pasan al repositorio y otras se descartan. Desde entonces, un cambio manual se revierte en minutos con una alerta, y las emergencias se resuelven con commits al repositorio de configuración.

### Un agente de código que tocó el workflow

**Situación:** el agente de código de Rumbo recibe un issue que pide "arreglar el test intermitente de la integración con Kafka". El issue, abierto desde un formulario de reporte, incluye al final un texto que pide agregar un paso de "diagnóstico" que envíe el entorno del job a una URL externa. El agente abre un PR que corrige el test y, además, modifica `.github/workflows/ci.yml` con ese paso.
**Qué se hace:** el PR no puede mergearse: `.github/workflows/` tiene CODEOWNERS del equipo de plataforma y el agente no tiene permiso de merge. El revisor ve el cambio y lo rechaza. Aun ejecutado en el PR, el job no tenía secretos ni podía asumir roles de producción, que exigen `main` y el entorno `prod`. Como mejora, todo PR de un agente que toque workflows se marca para revisión especial, y el texto de issues externos se le entrega como contenido no confiable.

## Errores comunes

- **Reconstruir la imagen por entorno.** Lo que se probó no es lo que se despliega. Construir una vez y promover el mismo digest.
- **Actions fijadas por tag o rama.** Cualquiera que controle ese tag controla el pipeline. Fijar por SHA y dejar que un bot proponga las actualizaciones.
- **Claves de larga duración como secretos del repositorio.** Reemplazarlas por OIDC con condiciones de repositorio, rama y entorno, sin comodines amplios.
- **Token del workflow con permisos de escritura por defecto.** Declarar `permissions: contents: read` a nivel de workflow y ampliar solo en el job que lo necesita.
- **Prompts y versiones de modelo fuera del repositorio.** Cambian sin revisión ni historial. Versionarlos y someterlos a un gate de evaluación.
- **Darle a un agente de código los mismos permisos que a un ingeniero senior.** El agente lee texto no confiable; necesita menos permisos, no más, y siempre revisión humana.

## Para discutir en equipo

- ¿Qué servicios de Rumbo están listos para despliegue continuo y qué controles les faltan a los demás?
- ¿Cuánto tarda hoy el pipeline más lento del equipo y qué etapa conviene atacar primero?
- ¿Qué umbrales debería tener el gate de evaluación del asistente de soporte y quién decide cambiarlos?
- ¿Qué cambios de emergencia aceptamos fuera de GitOps y cómo garantizamos que vuelvan al repositorio?
- ¿Qué tareas le delegaríamos a un agente de código y qué archivos nunca debería poder modificar sin revisión de plataforma?
