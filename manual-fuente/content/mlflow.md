---
slug: mlflow
titulo: MLflow y Weights & Biases
resumen: Herramientas para registrar cada experimento de entrenamiento y gestionar qué versión de modelo está aprobada para producción, con trazabilidad completa.
lectura: 10
---

## La idea central

Entrenar un modelo no es una ejecución única sino decenas o cientos de intentos: otra combinación de hiperparámetros, una feature nueva, una ventana de datos distinta. Sin un registro ordenado, al cabo de dos semanas nadie recuerda qué corrida dio el MAE de 5,9 minutos, con qué datos se entrenó ni qué versión del código la produjo. El conocimiento queda en notebooks locales y en la memoria de una persona.

**MLflow** y **Weights & Biases (W&B)** resuelven ese problema. Funcionan como un cuaderno de laboratorio automático: cada vez que se entrena, se anotan los parámetros usados, las métricas obtenidas, los archivos producidos y de dónde salieron el código y los datos. Encima de eso ofrecen un **registro de modelos**: un catálogo de versiones con un estado claro ("esta es la versión que está en producción"), parecido a lo que un registro de imágenes de contenedores hace para el software. Juntos convierten el entrenamiento en algo reproducible y auditable, que es la base de un [ciclo de vida de modelos](#t/ciclo-vida-modelos) sano.

## Conceptos

### Tracking de experimentos

Una **corrida** (run) es una ejecución de entrenamiento. El tracking registra, para cada corrida:

- **Parámetros:** las decisiones de entrada. Profundidad máxima del árbol = 6, tasa de aprendizaje = 0,1, ventana de datos = últimos 90 días.
- **Métricas:** los resultados numéricos. MAE en validación = 6,1 minutos, MAE en la zona norte = 7,4. Se pueden registrar por paso para ver curvas (el error en cada iteración del entrenamiento).
- **Artefactos:** archivos producidos. El modelo serializado, un gráfico de importancia de features, la lista de features usadas, un reporte de errores por zona.
- **Versión del código:** el commit de git desde el que se ejecutó. Sin esto, el modelo no se puede reconstruir.
- **Versión de los datos:** una referencia exacta al dataset usado, por ejemplo la ruta en S3 con fecha (`s3://rumbo-ml/eta/train/2026-10-01/`) o un hash del contenido.

Las corridas se agrupan en **experimentos** (por ejemplo, "eta-xgboost-2026q4") y se pueden comparar en una tabla o un gráfico.

**Ejemplo:** el equipo prueba 40 combinaciones para el modelo de ETA. En la interfaz de tracking se ordenan por MAE de validación y aparece que las cinco mejores usan ventana de 60 días en lugar de 90. Eso es un hallazgo que, sin tracking, se habría perdido entre notebooks.

**Por qué importa:** si no se registra la versión del código y de los datos, una corrida no es reproducible, y un modelo que no se puede reproducir no se puede auditar ni corregir con confianza.

### Registro de modelos

El **registro de modelos** (model registry) es un catálogo de modelos con nombre y versiones numeradas. Cada versión apunta a los artefactos de una corrida concreta. Sus elementos clave son:

- **Versiones:** "eta-modelo" versión 12, 13, 14. Cada una es inmutable.
- **Aliases (alias):** etiquetas móviles que apuntan a una versión, como `champion` (la de producción) o `challenger` (la candidata). El servicio de producción no pide "la versión 14" sino "la versión con alias `champion`". En MLflow, los aliases reemplazaron al esquema anterior de etapas fijas (Staging, Production).
- **Linaje:** desde cada versión se puede navegar a la corrida que la produjo, y desde ahí a los parámetros, al commit y al dataset. Responde "¿de dónde salió este modelo?".
- **Aprobaciones:** un proceso para pasar una versión a producción. Puede ser una revisión humana, una validación automática o ambas, y queda registrado quién aprobó y cuándo.

**Ejemplo:** el servicio de ETA arranca y pide `models:/eta-modelo@champion`. Hoy eso resuelve a la versión 14. Cuando se aprueba la 15, se mueve el alias y el servicio la toma en su próxima recarga. Si la 15 falla, mover el alias de vuelta a la 14 es el rollback.

**Por qué importa:** separar "qué modelos existen" de "cuál está en producción" permite promover y revertir sin cambiar código ni redesplegar el servicio.

### MLflow

**MLflow** es una plataforma open source, originada en Databricks, con varios componentes:

- **Tracking:** API y servidor para registrar corridas. Guarda metadatos en una base de datos (por ejemplo PostgreSQL) y artefactos en almacenamiento de objetos (por ejemplo S3).
- **Model Registry:** el registro de modelos con versiones y aliases.
- **Formato de modelos:** una forma estándar de empaquetar modelos de distintas librerías (XGBoost, scikit-learn, PyTorch) con sus dependencias, para cargarlos de manera uniforme.
- **Autologging:** con una línea, registra automáticamente parámetros y métricas de librerías conocidas.

MLflow se puede alojar en infraestructura propia (un contenedor en EKS, metadatos en Aurora PostgreSQL, artefactos en S3) o usar en versión gestionada dentro de Databricks o como servicio de AWS en SageMaker. Su interfaz es funcional pero más sobria que la de W&B.

Un ejemplo corto de cómo se registra una corrida. Es **ilustrativo**: los nombres, rutas y valores son de ejemplo y la API exacta puede variar entre versiones.

```python
import mlflow
import xgboost as xgb
from sklearn.metrics import mean_absolute_error

mlflow.set_tracking_uri("http://mlflow.interno.rumbo:5000")  # servidor propio, ejemplo
mlflow.set_experiment("eta-xgboost-2026q4")

params = {"max_depth": 6, "learning_rate": 0.1, "n_estimators": 400}
datos = "s3://rumbo-ml/eta/train/2026-10-01/"  # referencia exacta al dataset

with mlflow.start_run(run_name="ventana-60d"):
    mlflow.log_params(params)
    mlflow.set_tag("dataset", datos)
    mlflow.set_tag("git_commit", "a1b2c3d")  # normalmente se completa solo desde CI

    modelo = xgb.XGBRegressor(**params)
    modelo.fit(X_train, y_train)

    mae = mean_absolute_error(y_val, modelo.predict(X_val))
    mlflow.log_metric("mae_validacion_min", mae)

    # Guarda el modelo como artefacto y crea una versión nueva en el registro
    mlflow.xgboost.log_model(modelo, "modelo", registered_model_name="eta-modelo")
```

Al terminar, la corrida aparece en la interfaz con sus parámetros, la métrica y el modelo, y el registro tiene una versión nueva de `eta-modelo` lista para evaluar.

### Weights & Biases

**Weights & Biases (W&B)** es una plataforma comercial, principalmente SaaS, con planes gratuitos para uso individual y opciones de instalación dedicada o en infraestructura propia para empresas. Cubre lo mismo que el tracking de MLflow, con foco en la experiencia de análisis:

- **Visualización:** paneles interactivos muy cuidados para comparar cientos de corridas, superponer curvas de entrenamiento y filtrar por parámetros. Brilla especialmente en deep learning, donde se siguen curvas de pérdida durante horas (ver [PyTorch y TensorFlow](#t/pytorch-tensorflow)).
- **Sweeps:** búsqueda de hiperparámetros orquestada. Se define el espacio de búsqueda y W&B reparte combinaciones a varios "agentes" que entrenan en paralelo.
- **Reportes:** documentos que mezclan texto con gráficos vivos de corridas. Útiles para explicar a otro equipo por qué se eligió un modelo.
- **Artifacts y Registry:** versionado de datasets y modelos con linaje, comparable al registro de MLflow.

**Por qué importa:** W&B suele ganar en experiencia de usuario y colaboración; MLflow, en control, costo y facilidad de alojar todo internamente.

### Búsqueda de hiperparámetros

Los **hiperparámetros** son decisiones que se fijan antes de entrenar y que el modelo no aprende solo: profundidad de los árboles, tasa de aprendizaje, cantidad de árboles. Encontrar una buena combinación es una búsqueda. Las estrategias más comunes son:

- **Grid search (búsqueda en grilla):** probar todas las combinaciones de una lista. Con 4 valores de profundidad, 4 de tasa y 3 de cantidad de árboles son 48 corridas. Crece muy rápido con cada parámetro nuevo.
- **Random search (búsqueda aleatoria):** probar combinaciones al azar dentro de rangos. Con el mismo presupuesto de corridas suele encontrar algo igual o mejor que la grilla, porque explora más valores distintos de los parámetros que realmente importan.
- **Búsqueda bayesiana:** usa los resultados anteriores para elegir la próxima combinación más prometedora. Converge con menos corridas. Herramientas como Optuna o los sweeps de W&B la implementan.

**Ejemplo:** con un presupuesto de 30 corridas de 10 minutos cada una (5 horas de cómputo), una búsqueda bayesiana encuentra una combinación con MAE de 5,9 minutos en la corrida 18, mientras la grilla de 48 corridas no habría terminado.

**Por qué importa:** cada corrida de la búsqueda queda registrada en el tracking, lo que permite entender qué parámetros importan y no repetir búsquedas.

### Integración con CI/CD

El tracking y el registro rinden más cuando se integran con el pipeline de CI/CD (integración y despliegue continuos):

1. Un cambio en el código de entrenamiento dispara un pipeline que entrena con un dataset fijo y registra la corrida, con el commit automáticamente.
2. Una validación automática compara la nueva versión con la actual `champion`: MAE global, MAE por zona, latencia de inferencia, tamaño del modelo.
3. Si pasa los umbrales, se le asigna el alias `challenger` y se abre una aprobación.
4. Tras la aprobación, el pipeline mueve el alias `champion` y despliega o notifica al servicio de [serving](#t/serving).

El registro se vuelve la fuente de verdad: el despliegue no copia archivos sueltos, siempre referencia una versión registrada.

### Alternativas

Hay otras herramientas en el mismo espacio, con distinto énfasis:

- **Neptune y Comet:** plataformas comerciales de tracking, similares a W&B.
- **SageMaker Experiments y Model Registry:** integrados en AWS, convenientes si todo el pipeline ya corre en SageMaker.
- **Vertex AI:** el equivalente en Google Cloud.
- **DVC:** se enfoca en versionar datos y pipelines junto a git, y se combina bien con MLflow.
- **ClearML:** open source con tracking, orquestación y registro.

### Tabla comparativa: MLflow vs. W&B

| Aspecto | MLflow | Weights & Biases |
|---|---|---|
| Licencia | Open source | Comercial (plan gratuito limitado) |
| Alojamiento | Propio o gestionado (Databricks, AWS) | SaaS por defecto; dedicado o propio en planes empresariales |
| Tracking | Completo, interfaz sobria | Completo, visualización muy rica |
| Registro de modelos | Maduro, con aliases y linaje | Disponible, integrado con Artifacts |
| Búsqueda de hiperparámetros | Se combina con Optuna u otras | Sweeps integrados |
| Colaboración y reportes | Básica | Fuerte: reportes, comentarios, paneles compartidos |
| Costo | Infraestructura propia y operación | Licencia por usuario o uso (orden de magnitud a evaluar con el proveedor) |
| Datos sensibles | Todo queda dentro de la red si se aloja internamente | Requiere plan dedicado o propio para no salir de la red |
| Encaje típico | Equipos que priorizan control, on-prem, modelos tabulares | Equipos con mucho deep learning y foco en análisis visual |

## Casos prácticos

### El modelo huérfano salido de un notebook

**Situación:** el modelo de probabilidad de entrega a tiempo que corre en producción se entrenó hace ocho meses en el notebook de una persona que ya no está en el equipo. Hay un archivo `modelo_final_v3.pkl` en S3. Nadie sabe con qué datos se entrenó, qué features exactas usa ni con qué parámetros. Ahora hay que corregir un sesgo en la zona sur.

**Qué se hace:** primero, rescatar lo que se pueda: inspeccionar el archivo para obtener la lista de features y los parámetros que el propio modelo guarda, y buscar el notebook. Después, reconstruir el entrenamiento como un script versionado que registra en MLflow, entrenar sobre un dataset documentado y comparar contra el modelo huérfano en un período reciente. Si el nuevo iguala o mejora, se registra como versión 1 de `entrega-a-tiempo` y se reemplaza. Como regla para el futuro: ningún modelo llega a producción si no proviene de una versión del registro con linaje completo.

### Promoción con aprobación y rollback moviendo un alias

**Situación:** la versión 15 del modelo de ETA mejora el MAE global de 6,1 a 5,8 minutos. Pasa la validación automática y una persona del equipo la aprueba. Se mueve el alias `champion` de la 14 a la 15. A las tres horas, el monitoreo muestra que el MAE en pedidos de más de 10 km subió de 9 a 13 minutos, un segmento que la validación no evaluaba por separado.

**Qué se hace:** el rollback es mover el alias `champion` de vuelta a la versión 14. El servicio la recarga en su próximo ciclo, sin redesplegar código. El registro deja constancia de ambos movimientos, quién los hizo y por qué. Después, se agrega "MAE en pedidos largos" a los criterios de validación automática para que la próxima candidata no pase sin evaluarse en ese segmento. Conviene complementar con un despliegue gradual (por ejemplo, 10 % del tráfico primero) para detectar estos casos antes.

### Artefactos con datos personales

**Situación:** al registrar corridas del clasificador de tickets del asistente de soporte, el equipo guarda como artefacto una muestra de 500 tickets mal clasificados para análisis. Los tickets contienen nombres, teléfonos y direcciones de destinatarios. El tracking está configurado en un servicio SaaS externo.

**Qué se hace:** esos artefactos son datos personales que salieron de la red de Rumbo hacia un tercero. Lo correcto es alojar el tracking dentro de la red: un servidor MLflow en EKS, metadatos en Aurora PostgreSQL y artefactos en un bucket S3 privado, cifrado y con acceso restringido por rol. Además, se seudonimizan o eliminan los campos personales antes de guardar muestras, y se define una política de retención para borrarlas. Si se mantiene W&B por sus ventajas de análisis, debe ser en una instalación dedicada o propia, y nunca con artefactos que contengan PII.

## Errores comunes

- **No registrar la versión de los datos.** Registrar código y parámetros sin el dataset deja la corrida irreproducible. Hay que guardar una ruta inmutable o un hash.
- **Desplegar archivos sueltos.** Copiar un `.pkl` a producción rompe el linaje. El despliegue siempre debería referenciar una versión del registro.
- **Apuntar el servicio a una versión fija en el código.** Obliga a redesplegar para cambiar de modelo. Usar aliases permite promover y revertir sin tocar el servicio.
- **Registrar todo sin criterio.** Miles de corridas sin nombres ni etiquetas son tan inútiles como ninguna. Hay que nombrar experimentos y etiquetar corridas con su propósito.
- **Guardar datos personales en artefactos.** Muestras, predicciones con contexto o datasets pueden incluir PII. Hay que filtrarlos y alojar el tracking en infraestructura controlada.

## Para discutir en equipo

- ¿Qué información mínima exigiríamos en una corrida para que su modelo pueda llegar a producción?
- ¿Quién aprueba una promoción a `champion` y qué evidencia necesita ver?
- ¿Nos conviene MLflow alojado, MLflow gestionado o W&B, considerando los clientes on-prem y los datos personales?
- ¿Cómo garantizaríamos que un cliente on-prem tenga el mismo modelo exacto que corre en nuestra nube?
- ¿Qué segmentos deberían formar parte de la validación automática antes de mover un alias?
