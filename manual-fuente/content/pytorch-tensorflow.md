---
slug: pytorch-tensorflow
titulo: PyTorch y TensorFlow
resumen: Los dos frameworks principales de deep learning: qué problemas resuelven, cómo se entrena una red neuronal y cómo llevarla a producción.
lectura: 13
---

## La idea central

El **deep learning** (aprendizaje profundo) es la rama del ML que usa **redes neuronales** con muchas capas. Una red neuronal es, en esencia, una cadena larga de multiplicaciones y sumas con millones de números ajustables, llamados **pesos**. Al principio los pesos son aleatorios y la red responde cualquier cosa. El entrenamiento consiste en mostrarle ejemplos, medir cuánto se equivoca y ajustar cada peso un poquito en la dirección que reduce el error, repitiendo millones de veces.

**PyTorch** y **TensorFlow** son las librerías que hacen ese trabajo pesado: guardan los números, calculan automáticamente cómo ajustar cada peso y ejecutan todo en GPU para que sea rápido. Una analogía: si XGBoost es una herramienta especializada que funciona de maravillas con tablas, PyTorch y TensorFlow son un taller completo con el que se puede construir casi cualquier modelo, a cambio de más trabajo, más datos y más cómputo. En Rumbo, el modelo de ETA es XGBoost y probablemente debe seguir siéndolo; el deep learning entra donde los datos no son una tabla prolija.

## Conceptos

### Cuándo conviene el deep learning

Para datos **tabulares** (filas y columnas con significado claro, como distancia, zona, hora y carga), los modelos de árboles como XGBoost suelen igualar o superar a las redes neuronales, con menos datos, menos ajuste y menos costo (ver [XGBoost y scikit-learn](#t/xgboost)). El deep learning gana cuando los datos tienen estructura que una tabla no captura bien:

- **Datos no estructurados:** texto, imágenes, audio. Una foto de un paquete dañado o el texto libre de un ticket de soporte no se pueden describir fácilmente con columnas hechas a mano.
- **Secuencias:** cuando importa el orden. Los últimos 50 eventos de un transportista (retiro, demora, entrega, entrega, intento fallido) cuentan una historia que un promedio pierde.
- **Representaciones aprendidas:** cuando se quiere que el modelo invente su propia forma de describir entidades, como zonas o comercios, en lugar de definirla a mano.

**Ejemplo:** para clasificar tickets de soporte en 12 categorías, un modelo de texto preentrenado ajustado con 5.000 tickets etiquetados puede llegar a un 90 % de acierto, mientras que un modelo de árboles sobre palabras clave contadas a mano se queda bastante por debajo, porque no entiende "no llegó nunca" y "sigue sin aparecer" como lo mismo.

**Por qué importa:** elegir deep learning donde no hace falta suma GPU, complejidad y tiempo de entrenamiento sin mejorar el resultado. La pregunta correcta es "¿qué estructura tienen los datos?", no "¿qué técnica es más moderna?".

### Tensores y GPU

Un **tensor** es un arreglo de números con cualquier cantidad de dimensiones. Un número suelto es un tensor de 0 dimensiones; una lista de números, de 1; una tabla, de 2. Un lote de 32 secuencias de 50 eventos, cada evento descrito por 8 números, es un tensor de forma `(32, 50, 8)`. Todo lo que entra, sale y vive dentro de una red es un tensor.

Las redes hacen sobre todo multiplicaciones de matrices enormes, operaciones que se pueden hacer en paralelo. Una **GPU** (unidad de procesamiento gráfico) tiene miles de núcleos simples diseñados justamente para eso. Una multiplicación que en CPU tarda 1 segundo puede tardar del orden de centésimas en una GPU. Por eso entrenar redes medianas o grandes sin GPU es impráctico.

En PyTorch, mover datos y modelo a la GPU es explícito: `tensor.to("cuda")`. Un error frecuente es que el modelo esté en GPU y los datos en CPU, y la operación falle.

**Por qué importa:** la forma de los tensores es el idioma de estos frameworks. Gran parte de los errores al principio son "la forma no coincide".

### Cómo se entrena una red

El entrenamiento repite un ciclo de cuatro pasos:

1. **Forward (pasada hacia adelante):** la red recibe un lote de ejemplos y produce predicciones. Por ejemplo, para 64 pedidos predice 64 ETA.
2. **Loss (función de pérdida):** un número que mide qué tan mal estuvo la predicción. Para ETA puede ser el error cuadrático medio: si predijo 30 y el real fue 36, aporta (36 − 30)² = 36. Se promedia sobre el lote.
3. **Backpropagation (retropropagación):** el framework calcula, para cada peso, cuánto cambiaría la pérdida si ese peso subiera un poquito. Ese valor se llama **gradiente**. Lo notable es que se calcula automáticamente para millones de pesos a la vez, recorriendo la red hacia atrás.
4. **Optimizador:** ajusta cada peso un paso pequeño en la dirección opuesta a su gradiente, es decir, hacia donde baja la pérdida. El tamaño del paso es la **tasa de aprendizaje** (learning rate). Adam y SGD son optimizadores comunes.

Una intuición: estar en una montaña con niebla y querer llegar al valle. No se ve el valle, pero se siente la pendiente bajo los pies (el gradiente). Se da un paso cuesta abajo (el optimizador), se vuelve a sentir la pendiente y se repite. Con pasos muy largos se salta el valle; con pasos muy cortos se tarda una eternidad.

**Lotes y épocas.** No se usan todos los datos a la vez: se toman de a **lotes** (batches), por ejemplo de 64 ejemplos, y se hace un ajuste por lote. Una **época** es una pasada completa por todo el dataset. Con 640.000 pedidos y lotes de 64, una época son 10.000 ajustes. Un entrenamiento típico corre entre 5 y 50 épocas, vigilando el error en un set de validación para detenerse cuando deja de mejorar.

**Ejemplo:** al empezar, la pérdida media es 400 (errores de unos 20 minutos). Tras la primera época baja a 90 (unos 9,5 minutos), tras la quinta a 50 (unos 7 minutos) y luego se estanca. Si la pérdida en entrenamiento sigue bajando pero la de validación sube, el modelo está memorizando (sobreajuste) y hay que parar.

### Ejemplo mínimo de bucle de entrenamiento en PyTorch

Este código es ilustrativo y está simplificado: entrena una red pequeña para predecir minutos de entrega a partir de 8 features numéricas.

```python
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

dispositivo = "cuda" if torch.cuda.is_available() else "cpu"

# Datos de ejemplo: X tiene forma (n_pedidos, 8), y tiene forma (n_pedidos, 1)
X = torch.randn(10_000, 8)
y = torch.randn(10_000, 1) * 10 + 35
cargador = DataLoader(TensorDataset(X, y), batch_size=64, shuffle=True)

# Red: 8 entradas -> 32 neuronas ocultas -> 1 salida (minutos)
modelo = nn.Sequential(
    nn.Linear(8, 32),
    nn.ReLU(),          # no linealidad: permite aprender relaciones no rectas
    nn.Linear(32, 1),
).to(dispositivo)

funcion_perdida = nn.MSELoss()                                  # error cuadrático medio
optimizador = torch.optim.Adam(modelo.parameters(), lr=1e-3)    # tasa de aprendizaje

for epoca in range(5):                       # 5 pasadas completas por los datos
    for lote_x, lote_y in cargador:          # de a 64 ejemplos
        lote_x, lote_y = lote_x.to(dispositivo), lote_y.to(dispositivo)

        prediccion = modelo(lote_x)                     # 1. forward
        perdida = funcion_perdida(prediccion, lote_y)   # 2. loss

        optimizador.zero_grad()   # borra gradientes del lote anterior
        perdida.backward()        # 3. backpropagation: calcula gradientes
        optimizador.step()        # 4. el optimizador ajusta los pesos

    print(f"época {epoca}: pérdida del último lote = {perdida.item():.2f}")
```

Lo que hay que llevarse no es la sintaxis sino la forma: en PyTorch el bucle es explícito y visible. En Keras (TensorFlow), el mismo ciclo se resume en `modelo.compile(...)` y `modelo.fit(X, y, epochs=5, batch_size=64)`, que es más corto pero oculta los pasos.

### Transfer learning y fine-tuning

Entrenar una red grande desde cero requiere muchos datos y mucho cómputo. El **transfer learning** (aprendizaje por transferencia) parte de un modelo ya entrenado por otros con enormes cantidades de datos generales, que ya "sabe" cosas útiles: un modelo de lenguaje ya entiende gramática y sinónimos; uno de imágenes ya reconoce bordes y formas.

Hay dos grados de reutilización:

- **Extracción de features:** se usa el modelo preentrenado tal cual, congelado, para convertir cada texto o imagen en un vector de números (un embedding, ver [Embeddings y bases vectoriales](#t/embeddings)), y encima se entrena un modelo chico.
- **Fine-tuning (ajuste fino):** se sigue entrenando el modelo preentrenado, o sus últimas capas, con los datos propios y una tasa de aprendizaje baja, para especializarlo.

**Ejemplo:** para clasificar tickets de soporte de Rumbo, en lugar de entrenar desde cero con 5.000 tickets (insuficientes), se toma un modelo de texto preentrenado y se ajusta durante 3 épocas. El entrenamiento tarda minutos en una GPU, no días.

**Por qué importa:** el transfer learning es la razón por la que equipos sin millones de ejemplos pueden usar deep learning. En la práctica, casi todo el deep learning en empresas medianas es fine-tuning o extracción de features.

### Exportación para serving

Un modelo entrenado en Python necesita llegar a producción, donde quizá no hay Python, o hay restricciones de latencia. Las opciones de exportación principales son:

- **TorchScript y torch.export (PyTorch):** convierten el modelo a una representación que se puede ejecutar sin el código Python original. TorchScript es el mecanismo histórico; `torch.export` es el enfoque más nuevo, que captura el grafo del modelo para compilarlo o ejecutarlo en otros entornos.
- **ONNX:** formato abierto e independiente del framework. Un modelo de PyTorch o TensorFlow exportado a ONNX se puede ejecutar con ONNX Runtime desde Python, C++, Java, C# y otros lenguajes, a menudo con buena latencia en CPU. Es una opción natural para llevar un modelo cerca de un servicio que no está en Python.
- **SavedModel (TensorFlow):** el formato estándar de TensorFlow, que incluye el grafo y los pesos. Se sirve con TensorFlow Serving, se convierte a TensorFlow Lite para dispositivos móviles o se carga en otros lenguajes.

**Ejemplo:** un modelo de secuencias en PyTorch se exporta a ONNX y se sirve con ONNX Runtime en CPU con latencia del orden de pocos milisegundos por lote pequeño. Los detalles de cómo exponerlo se ven en [Serving e inferencia en tiempo real](#t/serving).

**Por qué importa:** la exportación desacopla el entrenamiento del serving. Hay que verificar siempre que el modelo exportado da las mismas salidas que el original para un conjunto de entradas de prueba.

### Costo de GPU

Las GPU son caras y escasas. Como orden de magnitud hipotético, una instancia con una GPU de gama media puede costar alrededor de 1 dólar por hora en la nube, y una con varias GPU de gama alta, decenas de dólares por hora. Las decisiones que más influyen en el costo son:

- **Entrenamiento vs. inferencia:** entrenar requiere GPU casi siempre; servir modelos pequeños o medianos muchas veces se puede hacer en CPU, sobre todo exportando a ONNX.
- **Uso real:** una GPU encendida 24 horas para entrenar 2 horas por semana desperdicia más del 98 % del gasto. Conviene usar instancias bajo demanda o spot para trabajos de entrenamiento.
- **Tamaño del modelo:** un modelo diez veces más grande puede no mejorar el resultado de negocio. Medir antes de escalar.
- **Batching en inferencia:** agrupar peticiones aprovecha mejor la GPU, a cambio de algo de latencia.
### Usos en Rumbo

Algunos usos razonables del deep learning en el escenario de Rumbo:

- **Secuencias de eventos:** procesar los últimos eventos de un transportista o de un pedido para detectar patrones (demoras crecientes, rutas desordenadas) y resumirlos en un vector.
- **Embeddings de entidades:** representar zonas, comercios o transportistas como vectores aprendidos, de modo que entidades parecidas queden cerca.
- **Texto:** clasificación de tickets, extracción de datos de notas de entrega ("dejar en portería"), apoyo al asistente de soporte.

Lo que **no** cambia: el modelo de ETA principal, sobre features tabulares, probablemente siga siendo XGBoost. El deep learning se suma como productor de features, no como reemplazo.

### Tabla: PyTorch vs. TensorFlow/Keras

| Aspecto | PyTorch | TensorFlow / Keras |
|---|---|---|
| Estilo | Código Python explícito, el bucle de entrenamiento se escribe a mano | Keras ofrece una API de alto nivel (`fit`) más compacta |
| Depuración | Muy directa: se ejecuta como Python normal | Buena en modo eager; más difícil con grafos compilados |
| Popularidad en investigación | Dominante; la mayoría de modelos nuevos salen primero en PyTorch | Menor en investigación reciente |
| Ecosistema de modelos preentrenados | Muy amplio (por ejemplo, Hugging Face prioriza PyTorch) | Amplio, con menos novedades |
| Exportación | TorchScript, torch.export, ONNX | SavedModel, TF Lite, ONNX con conversores |
| Serving nativo | TorchServe (con menos actividad), o ONNX Runtime y servidores genéricos | TensorFlow Serving, maduro y probado |
| Móviles y dispositivos | ExecuTorch, en evolución | TF Lite, muy maduro |
| Keras multi-backend | No aplica | Keras 3 puede ejecutarse sobre TensorFlow, JAX o PyTorch |
| Encaje típico | Equipos nuevos, investigación aplicada, LLMs y fine-tuning | Sistemas existentes en TF, despliegue en dispositivos |

Para un equipo que empieza hoy sin historial, PyTorch es la opción por defecto más común. Si ya hay modelos en producción con TensorFlow y funcionan, migrarlos rara vez se justifica por sí solo.

## Casos prácticos

### Secuencia de eventos del transportista como feature del boosting

**Situación:** el equipo cree que los últimos 50 eventos de cada transportista (retiros, entregas, demoras, intentos fallidos, con sus tiempos) contienen información valiosa para el modelo de asignación, pero un modelo de secuencias en el camino crítico no entra en el presupuesto de 50 ms y agregaría una dependencia de GPU al servicio en Go.

**Qué se hace:** se entrena en PyTorch un modelo de secuencias que resume esos 50 eventos en un vector de 16 números (un embedding del "estado reciente" del transportista). Ese modelo corre **fuera del camino crítico**: un proceso consume eventos de Kafka y, cada vez que un transportista registra un evento nuevo, recalcula su vector y lo escribe en el almacén online del feature store. El modelo XGBoost de asignación lee esos 16 valores como features más, con costo de latencia de una lectura a Redis. Así se aprovecha el deep learning sin cambiar el serving principal. Hay que vigilar la frescura del vector y versionar juntos el modelo de secuencias y el XGBoost, porque si cambia el primero, los vectores significan otra cosa y el segundo debe reentrenarse (ver [Features y feature stores](#t/feature-stores)).

### Embeddings de zonas para zonas nuevas sin historial

**Situación:** Rumbo se expande a una ciudad nueva con 20 zonas. El modelo de ETA usa target encoding de la zona (el tiempo medio histórico), que para zonas nuevas no existe. Las primeras semanas, los ETA en la ciudad nueva tienen errores de 15 minutos o más.

**Qué se hace:** se entrena una red que aprende un embedding por zona a partir de atributos observables: densidad de calles, mezcla de comercios, tipo de edificación, distancia al centro, tráfico típico. Como el embedding se construye con atributos y no con el identificador de la zona, se puede calcular para una zona nueva desde el primer día. Las zonas con atributos parecidos a zonas conocidas reciben vectores cercanos, y el XGBoost los usa como features. Cuando la zona nueva acumula historial, su target encoding propio empieza a pesar más. Se valida simulando: se ocultan zonas existentes, se calcula su embedding solo con atributos y se mide el error.

### Mantener un solo framework

**Situación:** una persona del equipo prototipó el clasificador de tickets en TensorFlow y otra está haciendo el modelo de secuencias en PyTorch. Surge la pregunta de si conviene sostener los dos.

**Qué se hace:** se acuerda un framework único, PyTorch en este caso, porque la mayoría de modelos de texto preentrenados que interesan se publican primero allí y porque el resto del trabajo nuevo ya lo usa. Tener dos frameworks duplica imágenes de contenedor, versiones de drivers de GPU, pipelines de exportación, conocimiento necesario para la guardia y dependencias a actualizar. El clasificador en TensorFlow se migra mientras es un prototipo, que es cuando cuesta poco. Para el serving, ambos modelos se exportan a ONNX, lo que además deja un único runtime de inferencia. La excepción razonable sería un modelo maduro en producción que funciona bien: ese no se migra solo por uniformidad.

## Errores comunes

- **Usar deep learning sobre datos tabulares por defecto.** XGBoost suele ser igual o mejor, más barato y más fácil de explicar. El deep learning debe justificarse con una mejora medida.
- **Entrenar desde cero cuando existe un modelo preentrenado.** Desperdicia datos y cómputo. Primero hay que probar extracción de features o fine-tuning.
- **No comparar el modelo exportado con el original.** La conversión a ONNX o TorchScript puede introducir diferencias numéricas o fallar con ciertas operaciones. Hay que validar salidas con entradas de prueba antes de desplegar.
- **Dejar GPU encendidas sin uso.** Es uno de los gastos más fáciles de evitar. Usar instancias por trabajo y apagarlas al terminar.
- **Poner un modelo pesado en el camino crítico.** Si la latencia es estricta, conviene precalcular la salida fuera de línea y servirla como feature.
- **Mirar solo la pérdida de entrenamiento.** Que baje no significa que el modelo generalice. Siempre hay que seguir la pérdida en validación y detenerse cuando deja de mejorar.

## Para discutir en equipo

- ¿Qué problema de Rumbo tiene hoy datos con estructura (texto, secuencias) donde un modelo tabular se queda corto?
- ¿Qué mejora mínima en el negocio exigiríamos para justificar el costo de GPU y la complejidad de un modelo de deep learning?
- Si un vector producido por un modelo de secuencias alimenta al XGBoost, ¿cómo versionamos y desplegamos ambos sin romper la consistencia?
- ¿Serviríamos los modelos de deep learning en CPU con ONNX o en GPU, y qué mediríamos para decidir?
- ¿Qué criterios usaríamos para aceptar una excepción a la regla de un solo framework?
