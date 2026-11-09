---
slug: python
titulo: Python
resumen: Lenguaje dominante en datos y ML; cubre su ecosistema, el GIL, asyncio, tipado con Pydantic, dependencias, rendimiento y cómo llevar código a producción.
lectura: 7
---

## La idea central

Python es el idioma común del trabajo con datos y machine learning. No es el lenguaje más rápido, pero tiene el ecosistema más rico: casi toda librería de ML, cliente de LLM o herramienta de análisis existe primero en Python. Su punto débil es la ejecución pura de código Python, que es lenta comparada con Go; su truco es que el trabajo pesado se delega a librerías escritas en C, C++ o Rust.

En Rumbo, el modelo de ETA, el pronóstico de demanda y el asistente de soporte con LLM están en Python. La pregunta no es si Python es "rápido", sino cómo usarlo para que el código lento no esté en el camino crítico.

## Conceptos

### Ecosistema

| Área | Librerías | Para qué |
|---|---|---|
| Cálculo numérico | NumPy | Arreglos y operaciones vectorizadas en C |
| Datos tabulares | pandas, Polars | Tablas en memoria; Polars es más rápido y paralelo, escrito en Rust |
| ML clásico | scikit-learn, XGBoost | Modelos sobre datos tabulares; ver [XGBoost y scikit-learn](#t/xgboost) |
| Deep learning | PyTorch | Redes neuronales y GPUs |
| Exploración | Jupyter | Notebooks interactivos |
| Servicios | FastAPI, Pydantic | APIs HTTP con validación de datos |

### El GIL y cómo se sortea

El **GIL** (*Global Interpreter Lock*) es un candado del intérprete estándar (CPython) que permite que un solo hilo ejecute código Python a la vez. Con 8 hilos haciendo cálculos en Python puro, se usa en la práctica un solo núcleo.

Formas de sortearlo:

- **Multiproceso:** varios procesos, cada uno con su GIL (`multiprocessing`, o varios workers de Uvicorn). Cuesta más memoria y los datos se copian entre procesos.
- **Librerías en C:** NumPy, pandas, XGBoost y PyTorch liberan el GIL durante sus cálculos internos, así que pueden usar varios núcleos.
- **E/S:** mientras un hilo espera la red, libera el GIL; para trabajo de E/S, los hilos o asyncio funcionan bien.
- **Variante sin GIL:** desde Python 3.13 existe una compilación experimental sin GIL (*free-threaded*). Es prometedora pero todavía poco adoptada y no todas las librerías la soportan.

### asyncio para E/S

`asyncio` permite que un solo hilo atienda muchas operaciones de red concurrentes: mientras una llamada espera respuesta, el bucle de eventos avanza con otra. Es ideal para llamar a un LLM o a APIs externas. No acelera cálculo, y una función bloqueante (como `requests.get` o un cálculo pesado) dentro de código async congela todo el bucle.

**Ejemplo:** resumir documentos llamando a un LLM, con un máximo de 10 llamadas simultáneas para no superar el límite de peticiones del proveedor.

```python
import asyncio

async def resumir_todos(docs: list[str], cliente, max_concurrencia: int = 10) -> list[str]:
    semaforo = asyncio.Semaphore(max_concurrencia)

    async def resumir(doc: str) -> str:
        async with semaforo:  # como mucho 10 dentro a la vez
            return await cliente.resumir(doc)

    return await asyncio.gather(*(resumir(d) for d in docs))
```

### Tipado y Pydantic

Python es dinámico, pero admite **anotaciones de tipo** que verifican herramientas como **mypy** o **pyright** antes de ejecutar. No cambian el comportamiento en tiempo de ejecución, pero detectan errores en CI.

**Pydantic** sí valida en tiempo de ejecución: se define un modelo con tipos y restricciones, y Pydantic convierte y verifica los datos de entrada, fallando con un mensaje claro si no cumplen. Es especialmente útil con LLMs, cuya salida es texto que *debería* ser JSON válido pero no siempre lo es.

**Ejemplo:** validar la clasificación de un ticket hecha por el LLM.

```python
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

class ClasificacionTicket(BaseModel):
    categoria: Literal["demora", "danio", "direccion", "otro"]
    prioridad: int = Field(ge=1, le=4)
    pedido_id: str | None = None
    resumen: str = Field(max_length=300)

def clasificar(texto_llm: str) -> ClasificacionTicket | None:
    try:
        return ClasificacionTicket.model_validate_json(texto_llm)
    except ValidationError as e:
        log.warning("salida_llm_invalida", extra={"errores": e.error_count()})
        return None  # reintentar con el error en el prompt o derivar a un humano
```

Ver [LLMs en producción](#t/llms-produccion).

### Dependencias y lockfile

Un proyecto declara dependencias con rangos (`pandas>=2.1`), pero lo que se instala debe ser reproducible: el **lockfile** fija la versión exacta de cada paquete, incluidas las dependencias indirectas, con sus hashes. **uv** (rápido, escrito en Rust) y **Poetry** generan y respetan lockfiles. Sin uno, el mismo `pip install` puede instalar versiones distintas en tu máquina y en producción.

### Notebook vs. producción

Los notebooks son excelentes para explorar, pero mezclan código, estado oculto (celdas ejecutadas en cualquier orden) y resultados. El código de producción necesita módulos importables, funciones con entradas y salidas claras, tests, configuración externa, logs y dependencias fijadas. La transición es una reescritura deliberada, no copiar celdas a un archivo.

### Rendimiento

- **Vectorizar:** reemplazar bucles de Python por operaciones sobre columnas completas en NumPy, pandas o Polars, que se ejecutan en C.
- **Perfilar antes de optimizar:** `cProfile` mide dónde se va el tiempo en una ejecución local; **py-spy** se engancha a un proceso en producción sin modificarlo y genera gráficos de llamas.

### Serving

Para exponer un modelo, **FastAPI** ofrece endpoints HTTP con validación Pydantic y documentación automática; **gRPC** es preferible cuando el cliente es otro servicio interno sensible a la latencia, como el servicio de asignación en Go. Ver [Serving e inferencia en tiempo real](#t/serving).

## Casos prácticos

### Del notebook a producción

**Situación:** el pronóstico de demanda vive en un notebook que una persona ejecuta a mano cada noche.

**Qué se hace:** se extraen las funciones a un paquete (`cargar_datos`, `construir_features`, `entrenar`, `predecir`), se fijan dependencias con uv y lockfile, se mueven rutas y fechas a configuración, se agregan tests con un dataset chico y se ejecuta como job programado con logs estructurados. El notebook queda para exploración, importando el paquete.

### Salida de LLM inválida

**Situación:** el 3% de las clasificaciones del asistente de soporte devuelve JSON roto o categorías inventadas, y rompe el flujo de tickets.

**Qué se hace:** se valida cada respuesta con el modelo Pydantic de arriba. Si falla, se reintenta una vez incluyendo el error de validación en el prompt; si vuelve a fallar, el ticket va a la cola humana. Se mide la tasa de salidas inválidas como métrica.

### 200 documentos en serie vs. concurrentes

**Situación:** resumir 200 manuales con un LLM, a unos 4 segundos por llamada, tarda 800 segundos (más de 13 minutos) en serie.

**Qué se hace:** con asyncio y un semáforo de 10, se procesan en unas 20 tandas de 4 segundos: alrededor de 80 segundos. El semáforo evita superar el límite de peticiones del proveedor; subirlo a 50 bajaría el tiempo, pero probablemente generaría errores de límite.

### Bucle sobre 10 millones de filas vs. vectorizado

**Situación:** calcular la velocidad media (distancia / minutos) de 10 millones de entregas con un bucle `for` sobre filas de pandas tarda varios minutos.

**Qué se hace:** se reemplaza por `df["velocidad"] = df["distancia_km"] / df["minutos"]`, que opera sobre columnas completas en C. El tiempo pasa a fracciones de segundo, una mejora de dos o tres órdenes de magnitud.

## Errores comunes

- **Usar hilos para cálculo en Python puro.** El GIL lo impide; usar procesos o librerías que liberen el GIL.
- **Llamadas bloqueantes dentro de código async.** Congelan el bucle; usar clientes async o mover el trabajo a un hilo con `asyncio.to_thread`.
- **Confiar en que el LLM devuelve JSON válido.** Validar siempre con Pydantic y tener un camino de respaldo.
- **Instalar sin lockfile.** Cada entorno termina con versiones distintas y errores difíciles de reproducir.
- **Iterar filas de un DataFrame.** Casi siempre existe una forma vectorizada mucho más rápida.

## Para discutir en equipo

- ¿Qué criterios usamos para decidir si un servicio nuevo va en Python o en Go?
- ¿Cómo hacemos la transición de notebook a producción sin frenar la exploración?
- ¿Qué concurrencia máxima toleran nuestros proveedores de LLM y cómo la configuramos de forma centralizada?
- ¿Vale la pena evaluar Polars en lugar de pandas para el pronóstico de demanda?
