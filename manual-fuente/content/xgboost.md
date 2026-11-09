---
slug: xgboost
titulo: XGBoost y scikit-learn
resumen: Cómo funcionan los árboles de decisión y el gradient boosting, por qué dominan en datos tabulares y cómo entrenarlos, explicarlos y evaluarlos con scikit-learn y XGBoost.
lectura: 17
---

## La idea central

La mayoría de los datos de Rumbo son **tabulares**: filas (pedidos) y columnas (distancia, zona, hora, clima, carga del transportista). Para este tipo de datos, la familia de modelos que mejor funciona en la práctica no son las redes neuronales de las que más se habla, sino los **ensambles de árboles de decisión**, y en particular el **gradient boosting**, cuya implementación más conocida es XGBoost.

La intuición: un solo árbol de decisión es como un despachador novato que razona con unas pocas preguntas ("¿es lejos?, ¿llueve?"). Es fácil de entender pero se equivoca bastante. El gradient boosting arma un equipo de cientos de despachadores novatos donde cada uno se especializa en corregir los errores que dejaron los anteriores. Ninguno es brillante por sí solo; la suma, sí. Y scikit-learn es la caja de herramientas de Python que rodea a esos modelos: preparar datos, validar, comparar y empaquetar todo en un pipeline reproducible.

## Conceptos

### Árbol de decisión

Un árbol de decisión predice haciendo una secuencia de preguntas de sí o no sobre las features. Cada pregunta divide los datos en dos grupos; al final de cada camino hay una **hoja** con una predicción.

**Ejemplo:** un árbol pequeño para el ETA:

```text
¿distancia_km <= 3?
├── sí: ¿hora entre 18 y 21?
│       ├── sí: 26 min
│       └── no: 18 min
└── no: ¿llueve?
        ├── sí: 47 min
        └── no: 35 min
```

Un pedido de 5 km sin lluvia cae en la hoja de 35 minutos. ¿Cómo elige el árbol las preguntas? Durante el entrenamiento, prueba muchos cortes posibles ("distancia <= 2", "distancia <= 3", "llueve", ...) y elige el que deja los grupos resultantes más homogéneos, es decir, el que más reduce el error. Luego repite el proceso dentro de cada grupo.

Ventajas: no necesita escalar variables, maneja relaciones no lineales ("la hora pico importa solo en distancias cortas") y se puede leer. Desventaja: un árbol profundo memoriza (overfitting, ver [Fundamentos de ML](#t/fundamentos-ml)) y uno poco profundo es demasiado tosco.

### Ensambles: random forest vs. gradient boosting

Un **ensamble** combina muchos modelos. Hay dos estrategias principales con árboles:

**Random forest (bosque aleatorio).** Entrena cientos de árboles profundos *en paralelo e independientes*, cada uno con una muestra aleatoria de filas y de features. La predicción final es el promedio. Cada árbol individual sobreajusta a su manera, pero sus errores son distintos y al promediar se cancelan en parte. Es robusto y difícil de configurar mal.

**Gradient boosting.** Entrena árboles chicos *en secuencia*: cada árbol nuevo se entrena para predecir el error (residuo) que dejaron los anteriores. La predicción final es la suma de todos.

**Ejemplo con números:** tres pedidos con ETA real de 30, 40 y 50 minutos.

1. **Paso 0:** se arranca con una predicción constante, el promedio: 40 para todos. Residuos (real menos predicho): -10, 0, +10.
2. **Árbol 1:** se entrena para predecir esos residuos. Supongamos que aprende "si distancia corta: -10; si larga: +10; si media: 0". No se suma entero, sino multiplicado por una **tasa de aprendizaje** (learning rate), por ejemplo 0,3: las predicciones pasan a 37, 40 y 43. Nuevos residuos: -7, 0, +7.
3. **Árbol 2:** aprende los residuos -7, 0, +7. Con la misma tasa, las predicciones pasan a 34,9; 40; 45,1. Residuos: -4,9; 0; +4,9.
4. Y así sucesivamente, cientos de veces. Cada paso cierra un poco la brecha.

La tasa de aprendizaje baja hace que el modelo avance de a poco y no se "enamore" del ruido de un árbol individual. El nombre "gradient" viene de que, en general, cada árbol se ajusta a la dirección en que más rápido baja la función de error; para el error cuadrático, esa dirección es justamente el residuo.

**Por qué importa:** random forest reduce varianza (promedia modelos inestables); boosting reduce sesgo (va corrigiendo un modelo simple). Por eso boosting suele lograr mejor precisión, a cambio de más hiperparámetros sensibles.

### XGBoost, LightGBM y CatBoost

Son tres bibliotecas de gradient boosting maduras y muy usadas. Comparten la idea, difieren en detalles de ingeniería:

- **XGBoost:** el más difundido. Regularización incorporada, soporte para valores faltantes (aprende hacia qué lado mandar los nulos), entrenamiento por histogramas rápido, soporte nativo de categóricas en versiones recientes.
- **LightGBM:** muy rápido en datasets grandes; hace crecer los árboles por la hoja que más reduce el error (leaf-wise) en lugar de por niveles, lo que lo hace eficiente pero algo más propenso a sobreajustar si no se limita.
- **CatBoost:** se destaca con features categóricas, porque implementa internamente un target encoding ordenado que evita fugas, y suele dar buenos resultados con poca configuración.

En la práctica, las diferencias de precisión entre los tres suelen ser pequeñas; pesan más la calidad de las features y la evaluación. Rumbo usa XGBoost para el modelo de ETA.

### Por qué dominan en datos tabulares

- Manejan sin esfuerzo features de escalas distintas (kilómetros, horas, conteos) y relaciones no lineales con interacciones.
- Toleran valores faltantes y features irrelevantes.
- Funcionan bien con decenas de miles a millones de filas, que es el tamaño típico de estos problemas; las redes neuronales suelen necesitar más datos o más trabajo para igualarlos.
- Entrenan en minutos en CPU, predicen en microsegundos a milisegundos y son relativamente explicables.

### Hiperparámetros clave y early stopping

Los **hiperparámetros** son decisiones de configuración que no se aprenden de los datos. Los que más importan en XGBoost:

| Hiperparámetro | Qué controla | Valores típicos (orden de magnitud) |
|---|---|---|
| `n_estimators` | Cantidad máxima de árboles | 200 a 2.000 |
| `learning_rate` | Cuánto aporta cada árbol | 0,03 a 0,1 |
| `max_depth` | Profundidad de cada árbol (interacciones que captura) | 4 a 8 |
| `min_child_weight` | Mínimo "peso" de ejemplos por hoja | 1 a 20 |
| `subsample` / `colsample_bytree` | Fracción de filas y columnas por árbol | 0,7 a 0,9 |
| `reg_lambda` / `reg_alpha` | Penalización L2 / L1 sobre las hojas | 0 a 10 |

**Early stopping** (parada temprana): en lugar de adivinar cuántos árboles usar, se entrena mirando el error en el conjunto de validación y se detiene cuando deja de mejorar durante N rondas (por ejemplo 50). Si el error de validación es mínimo en el árbol 430 y sube después, se queda con 430. Es la forma más simple y efectiva de evitar overfitting en boosting.

### Explicabilidad: importancia global y SHAP

**Importancia global** responde "¿qué features usa más el modelo en general?". Por ejemplo: distancia 41%, hora 18%, carga actual 15%. Es útil para revisar que el modelo use cosas sensatas, pero no explica una predicción individual y puede ser engañosa con features correlacionadas.

**SHAP** (SHapley Additive exPlanations) explica una predicción concreta repartiendo la diferencia entre la predicción y el promedio entre las features, de forma que los aportes sumen exactamente.

**Ejemplo:** el promedio de P(llega a tiempo) es 0,85. Para el pedido 8812 y el transportista Ana, el modelo da 0,94. SHAP descompone la diferencia de +0,09:

| Feature | Valor | Aporte |
|---|---|---|
| distancia_km | 1,8 | +0,05 |
| tasa_a_tiempo_transportista_30d | 0,97 | +0,04 |
| carga_actual | 1 pedido | +0,02 |
| lluvia | sí | -0,02 |
| **Total** | | **+0,09** |

Se lee: "Ana está cerca, tiene muy buen historial reciente y poca carga; la lluvia resta un poco". (En XGBoost para clasificación, SHAP suele calcularse en escala de log-odds; aquí se muestra en probabilidad para simplificar.)

### Categóricas de alta cardinalidad y target encoding sin fuga

Una feature categórica tiene valores discretos sin orden: zona, comercio, transportista. Si tiene pocos valores (5 zonas) se puede codificar con **one-hot** (una columna 0/1 por valor). Si tiene miles (12.000 comercios), one-hot genera demasiadas columnas.

**Target encoding** reemplaza cada categoría por el promedio de la etiqueta en esa categoría: el comercio 551 tiene 18% de entregas tardías, así que la feature vale 0,18. Funciona muy bien, pero tiene una trampa: si el promedio se calcula usando la fila que se está prediciendo, la etiqueta se filtra en la feature. Un comercio con un solo pedido, tardío, recibe encoding 1,0, y el modelo aprende que "1,0 significa tardío" con certeza.

Para hacerlo sin fuga:

1. Calcular el encoding **solo con datos anteriores** a cada fila (respetando el tiempo), o con validación cruzada fuera del pliegue (out-of-fold): cada fila recibe un promedio calculado sin su propio pliegue.
2. **Suavizar** hacia el promedio global cuando hay pocos ejemplos: con 3 pedidos, el encoding se acerca a la media general; con 3.000, al promedio propio.
3. En producción, usar exactamente la misma tabla de encodings calculada con datos de entrenamiento.

### Calibración de probabilidades

Un modelo está **calibrado** si, entre todos los casos en que dice 0,8, el evento ocurre cerca del 80% de las veces. Los ensambles de árboles suelen ordenar bien pero no siempre están calibrados, sobre todo si se entrenaron con pesos para clases raras.

Se verifica agrupando predicciones por rangos (0,7 a 0,8; 0,8 a 0,9...) y comparando con la tasa real. Se corrige entrenando un pequeño modelo de ajuste sobre las salidas, con datos de validación: **Platt scaling** (una regresión logística) o **regresión isotónica** (una función escalonada monótona). En scikit-learn, `CalibratedClassifierCV`.

**Por qué importa:** el servicio de asignación combina probabilidad de entrega a tiempo con ETA y costo en un puntaje. Si la probabilidad está inflada, ese puntaje pondera mal los factores.

### scikit-learn: pipelines, validación cruzada y baseline

scikit-learn es la biblioteca estándar de ML clásico en Python. Tres piezas que conviene conocer:

- **Pipeline:** encadena preprocesamiento y modelo en un solo objeto (`imputar nulos → codificar categóricas → modelo`). Se entrena y se guarda como una unidad, lo que garantiza que en producción se aplique la misma transformación que en entrenamiento.
- **Validación cruzada:** divide los datos en K partes, entrena K veces dejando una parte afuera cada vez y promedia el resultado. Da una estimación más estable. Para datos temporales se usa `TimeSeriesSplit`, que siempre valida con datos posteriores a los de entrenamiento.
- **Regresión logística como baseline:** un modelo lineal que convierte una suma ponderada de features en una probabilidad. Es rápido, estable y explicable. Si XGBoost no le gana por un margen claro, hay que preguntarse si la complejidad se justifica.

### Ejemplo de código: modelo de ETA

```python
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

df = pd.read_parquet("pedidos_entregados.parquet")  # una fila por pedido
df = df.sort_values("asignado_en")

features = ["distancia_km", "hora", "lluvia", "carga_actual",
            "tasa_a_tiempo_30d", "zona"]
target = "minutos_reales"

# Corte temporal: nunca aleatorio
train = df[df.asignado_en < "2026-09-01"]
valid = df[(df.asignado_en >= "2026-09-01") & (df.asignado_en < "2026-10-01")]
test  = df[df.asignado_en >= "2026-10-01"]

prep = ColumnTransformer(
    [("zona", OneHotEncoder(handle_unknown="ignore"), ["zona"])],
    remainder="passthrough",
)
modelo = XGBRegressor(
    n_estimators=2000, learning_rate=0.05, max_depth=6,
    subsample=0.8, colsample_bytree=0.8, early_stopping_rounds=50,
)

# El preprocesamiento se ajusta solo con train
X_train = prep.fit_transform(train[features])
X_valid = prep.transform(valid[features])
modelo.fit(X_train, train[target], eval_set=[(X_valid, valid[target])], verbose=False)

pipeline = Pipeline([("prep", prep), ("modelo", modelo)])
pred = pipeline.predict(test[features])
print("MAE test:", mean_absolute_error(test[target], pred))
print("Árboles usados:", modelo.best_iteration + 1)
```

Puntos a notar: el corte es temporal, el encoder se ajusta solo con train, el early stopping usa validación y el test se mira una sola vez al final. Lo que se guarda y versiona es el `pipeline` completo, no solo el modelo.

### Tabla comparativa de familias de modelos

| Modelo | Fortalezas | Debilidades | Cuándo elegirlo |
|---|---|---|---|
| Regresión logística (o lineal) | Simple, rápida, estable, coeficientes interpretables, bien calibrada | No captura interacciones ni no linealidades sin trabajo manual | Baseline siempre; problemas casi lineales; cuando la explicación es requisito fuerte |
| Random forest | Robusto, pocos hiperparámetros críticos, difícil de romper | Modelos pesados en memoria; algo menos preciso que boosting; predicción más lenta con muchos árboles profundos | Primer modelo no lineal rápido; cuando se busca robustez sin ajuste fino |
| Gradient boosting (XGBoost, LightGBM, CatBoost) | El mejor rendimiento típico en tabulares, rápido en CPU, maneja nulos, explicable con SHAP | Más hiperparámetros sensibles; puede sobreajustar sin early stopping | Opción por defecto para datos tabulares de producción |
| Redes neuronales | Excelentes con texto, imagen, audio, secuencias; aprenden representaciones (embeddings) | En tabulares suelen no superar a boosting; más datos, más ajuste, GPU, menos explicables | Datos no estructurados, o tabulares muy grandes con señales secuenciales (ver [PyTorch y TensorFlow](#t/pytorch-tensorflow)) |

## Casos prácticos

### Modelo de ETA en Rumbo

**Situación:** el modelo de ETA debe predecir minutos hasta la entrega para cada transportista candidato, dentro del presupuesto de latencia del servicio de asignación.
**Qué se hace:** se entrena un `XGBRegressor` con corte temporal y early stopping, se compara contra el baseline "mediana por zona y franja" y se reporta MAE global y por segmento (zona, lluvia, franja horaria), porque un buen promedio puede esconder una zona donde el modelo es peor que el baseline. Se elige MAE como métrica principal porque operaciones razona en "minutos de error", y se mira RMSE como control de errores grandes. Con profundidad 6 y unos cientos de árboles, la predicción para 20 candidatos tarda bastante menos de un milisegundo en CPU; el cuello de botella real estará en obtener las features (ver [Serving e inferencia en tiempo real](#t/serving)).

### Explicarle a operaciones por qué se asignó un transportista

**Situación:** un líder de operaciones pregunta por qué el pedido 8812 fue a Ana y no a Bruno, que estaba más cerca.
**Qué se hace:** se recuperan del registro de predicciones las features y salidas de ambos candidatos y se calculan sus valores SHAP. Bruno estaba a 1,2 km (+0,06) pero tenía 4 pedidos en curso (-0,07) y una tasa a tiempo reciente baja (-0,03); Ana quedó con 0,94 contra 0,81. La explicación se presenta en lenguaje de operaciones: "Bruno estaba más cerca pero cargado y con atrasos recientes". Esto requiere que cada decisión guarde las features exactas usadas, no recalcularlas después.

### Propuesta de reemplazar XGBoost por una red neuronal

**Situación:** alguien propone reemplazar el modelo de ETA por una red neuronal "porque es más moderna".
**Qué se pide antes de aprobar:** (1) comparación con el mismo corte temporal, mismas features y mismo test, contra el XGBoost actual y contra el baseline; (2) métricas por segmento, no solo globales; (3) latencia p99 de inferencia y costo de infraestructura (¿necesita GPU?); (4) plan de explicabilidad equivalente; (5) calibración; (6) cuánto mejora en una métrica de negocio, no solo en MAE. Si la ganancia es de 0,2 minutos con el triple de complejidad operativa, probablemente no conviene. Si incorpora una señal nueva que XGBoost no puede usar bien (por ejemplo la secuencia de posiciones GPS), la discusión cambia.

### Target encoding con fuga

**Situación:** al agregar `tasa_tardia_comercio` (target encoding del comercio) el modelo mejora mucho offline y empeora en producción, sobre todo en comercios nuevos o pequeños.
**Qué se hace:** se descubre que el encoding se calculó con todo el dataset, incluyendo la fila de cada pedido y pedidos futuros. Se recalcula de forma temporal (para cada pedido, solo con pedidos anteriores del comercio), se suaviza hacia la media global con un mínimo de ejemplos y se asigna la media global a comercios sin historial. La mejora offline baja a algo modesto pero real, y coincide con lo que se ve en producción.

## Errores comunes

- **Ajustar el preprocesamiento con todos los datos.** Encoders, imputadores y escaladores se ajustan solo con train; empaquetarlos en un Pipeline evita el error.
- **Entrenar boosting sin early stopping.** Con muchos árboles y sin validación, el modelo memoriza; usa un conjunto de validación temporal para cortar.
- **Leer la importancia global como causalidad.** Que una feature sea importante no significa que cambiarla cambie el resultado; para decisiones individuales, usa SHAP y aun así con cautela.
- **Usar probabilidades sin verificar calibración.** Si se combinan con otros números o se muestran a personas, mide y corrige la calibración.
- **Optimizar hiperparámetros contra el test.** Toda búsqueda se hace en validación; el test queda para la decisión final.
- **Saltar el baseline lineal.** Si la regresión logística está a un punto del boosting, la diferencia de complejidad merece discusión.

## Para discutir en equipo

- ¿Qué features del modelo de ETA podrían justificar otra familia de modelos, y cuáles no?
- ¿Cómo presentamos las explicaciones SHAP a operaciones sin que se interpreten como causas?
- ¿Qué categóricas de alta cardinalidad usamos hoy y cómo calculamos su encoding?
- ¿Qué umbral de mejora (en minutos de MAE o en entregas a tiempo) justificaría cambiar de familia de modelo?
- ¿Medimos la calibración de P(llega a tiempo) por segmento, o solo en global?
