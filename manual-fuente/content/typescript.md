---
slug: typescript
titulo: TypeScript
resumen: Capa de tipos estáticos sobre JavaScript para frontend y Node.js; cubre uniones, genéricos, validación en el borde y esquemas de herramientas para agentes.
lectura: 15
---

## La idea central

TypeScript es JavaScript con un sistema de tipos encima. Se escribe código JavaScript normal, se le agregan anotaciones (`pedidoId: string`, `eta: number`) y un compilador revisa que todo encaje antes de ejecutar. Después, los tipos se borran y lo que corre en el navegador o en Node.js es JavaScript común. TypeScript no agrega velocidad ni comportamiento nuevo en tiempo de ejecución: agrega una revisión exhaustiva antes de ejecutar, y un editor que sabe qué campos tiene cada objeto.

La analogía útil es la de un plano revisado por un ingeniero estructural: detecta antes de construir que una viga no apoya en nada, pero no controla los materiales que llegan de afuera. En software, lo que llega de afuera son las respuestas de una API, el JSON que devuelve un LLM o lo que escribe un usuario. Por eso la mitad de este tema trata sobre tipos dentro del programa y la otra mitad sobre cómo validar en el borde.

En Rumbo, TypeScript es el lenguaje del panel web de comercios (ver [React](#t/react)), del BFF que lo alimenta, de varias herramientas internas y de los servidores MCP que exponen datos a los agentes. Go queda para el servicio de asignación, con su presupuesto de 50 ms, y Python para modelos y datos.

## Conceptos

### Qué agrega y qué no agrega

TypeScript agrega tres cosas: **verificación estática** (el compilador `tsc` rechaza `pedido.direcion` si el campo se llama `direccion`), **autocompletado y navegación** en el editor, y **documentación ejecutable**: la firma de una función dice qué recibe y qué devuelve, y no puede quedar desactualizada sin que el compilador lo note.

Lo que no agrega es igual de importante:

- **Los tipos se borran.** No existe `typeof x === "Pedido"` en tiempo de ejecución. Si un servicio responde `{ eta: "12" }` en lugar de `{ eta: 12 }`, el programa sigue de largo con un string donde esperaba un número.
- **No hay validación automática de datos externos.** Escribir `const r = (await res.json()) as Pedido` es una promesa del programador, no una verificación.
- **No cambia el rendimiento.** El JavaScript resultante es prácticamente el mismo que se habría escrito a mano.

**Ejemplo:** una función que suma minutos de demora.

```ts
function etaConDemora(etaMin: number, demoraMin: number): number {
  return etaMin + demoraMin;
}

etaConDemora(12, "5"); // error de compilación: "5" no es number
```

En JavaScript puro, `12 + "5"` da `"125"`: un ETA de 125 minutos, sin ningún error visible.

**Por qué importa:** el equipo tiene que saber dónde termina la protección. Dentro del código, los tipos evitan una clase entera de errores; en los bordes, hace falta validar.

### Tipado estructural

En Java o Kotlin, un objeto es de tipo `Pedido` si se creó como `Pedido`. En TypeScript, un objeto es compatible con `Pedido` si **tiene la forma** de `Pedido`: los campos necesarios con los tipos correctos. Esto se llama tipado estructural.

```ts
interface ConUbicacion { lat: number; lng: number }

function distanciaKm(a: ConUbicacion, b: ConUbicacion): number { /* ... */ return 0; }

const transportista = { id: "t-42", lat: -34.6, lng: -58.4, carga: 3 };
const destino = { lat: -34.58, lng: -58.42 };
distanciaKm(transportista, destino); // válido: ambos tienen lat y lng
```

La ventaja es la flexibilidad: no hace falta declarar jerarquías. El costo es que un `PedidoId` y un `TransportistaId` declarados como `string` se pueden confundir sin que el compilador diga nada. Cuando eso importa, se usan tipos marcados (*branded types*), que agregan una etiqueta solo a nivel de tipos.

### Inferencia

No hace falta anotar todo. Si se escribe `const intentos = 3`, TypeScript infiere `number`; si una función devuelve `{ ok: true, eta: 14 }`, infiere ese tipo de retorno. La práctica habitual es anotar los **bordes** (parámetros de funciones exportadas, tipos de retorno de APIs públicas) y dejar que el compilador infiera el resto. Así el código queda corto y los contratos quedan explícitos.

### Uniones y narrowing

Una **unión** dice "es uno de estos": `string | null`, o `"norte" | "sur" | "centro"`. Para usar el valor, el código tiene que distinguir el caso, y el compilador sigue esa distinción. A esto se le llama **narrowing** (estrechamiento): después de un `if (x !== null)`, dentro del bloque `x` ya no puede ser `null`.

```ts
function etiquetaZona(zona: string | null): string {
  if (zona === null) return "sin zona";
  return zona.toUpperCase(); // aquí zona es string
}
```

### Uniones discriminadas y exhaustividad

El patrón más valioso de TypeScript para modelar estados es la **unión discriminada**: varias variantes que comparten un campo literal (el discriminante) y tienen campos propios. Sirve para representar, por ejemplo, el estado de una llamada a herramienta de un agente, tal como se muestra en el chat del panel.

```ts
type LlamadaHerramienta =
  | { estado: "pendiente"; id: string; nombre: string }
  | { estado: "ejecutando"; id: string; nombre: string; inicio: number }
  | { estado: "terminada"; id: string; nombre: string; resultado: unknown; ms: number }
  | { estado: "fallida"; id: string; nombre: string; error: string; reintentable: boolean };

function textoEstado(l: LlamadaHerramienta): string {
  switch (l.estado) {
    case "pendiente":  return `En cola: ${l.nombre}`;
    case "ejecutando": return `Consultando ${l.nombre}...`;
    case "terminada":  return `Listo en ${l.ms} ms`;
    case "fallida":    return l.reintentable ? "Error temporal, reintentando" : `Falló: ${l.error}`;
    default: {
      const imposible: never = l; // si falta un caso, esto no compila
      return imposible;
    }
  }
}
```

Dos cosas pasan acá. Dentro de cada `case`, el compilador sabe qué campos existen: `l.ms` solo es accesible en `"terminada"`. Y el `default` con `never` es la **verificación de exhaustividad**: si mañana alguien agrega la variante `"cancelada"`, todas las funciones que no la manejen dejan de compilar y señalan exactamente dónde falta código.

**Por qué importa:** la alternativa habitual, un objeto con `estado: string` y campos opcionales sueltos, permite estados imposibles como "terminada sin resultado" o "fallida con duración". Con la unión discriminada, esos estados no se pueden escribir.

### Genéricos

Un **genérico** es un tipo con un parámetro. En lugar de escribir una función de reintento para pedidos y otra para transportistas, se escribe una que funciona con cualquier tipo `T` y conserva ese tipo en el resultado.

```ts
async function conReintentos<T>(fn: () => Promise<T>, intentos = 3): Promise<T> {
  let ultimoError: unknown;
  for (let i = 0; i < intentos; i++) {
    try { return await fn(); } catch (e) { ultimoError = e; }
  }
  throw ultimoError;
}

const pedido = await conReintentos(() => api.obtenerPedido("p-981")); // pedido: Pedido
```

### Tipos utilitarios

TypeScript trae tipos que transforman otros tipos. Los cuatro más usados:

| Utilitario | Qué hace | Uso típico en Rumbo |
|---|---|---|
| `Partial<T>` | Todos los campos opcionales | Cuerpo de un `PATCH` que actualiza parte de un pedido |
| `Pick<T, K>` | Solo los campos elegidos | Vista pública del pedido con `id`, `estado` y `eta` |
| `Omit<T, K>` | Todos menos los elegidos | Pedido sin `telefono` ni `direccion` antes de enviarlo al log |
| `Record<K, V>` | Objeto con claves `K` y valores `V` | `Record<Zona, number>` con pedidos esperados por zona |

**Ejemplo:** `type PedidoSinPII = Omit<Pedido, "nombreDestinatario" | "telefono" | "direccion">`. Si alguien intenta loguear un `PedidoSinPII` con el teléfono, el compilador lo rechaza. No reemplaza a un filtro de PII en el pipeline de logs, pero evita el error más común.

### unknown frente a any

`any` desactiva el sistema de tipos: con un `any` se puede llamar cualquier método, acceder a cualquier campo y pasarlo a cualquier función, y nada se verifica. Además se "contagia": lo que sale de un `any` también es `any`.

`unknown` dice "no sé qué es esto" pero obliga a averiguarlo antes de usarlo. Es el tipo correcto para todo lo que llega de afuera: el cuerpo de una petición, un mensaje de Kafka, la salida de un LLM.

```ts
const dato: unknown = JSON.parse(textoDelModelo);
dato.categoria;            // error: hay que verificar primero
if (typeof dato === "object" && dato !== null && "categoria" in dato) { /* ... */ }
```

En la práctica, en lugar de escribir esas verificaciones a mano, se usa una librería de esquemas (más abajo).

### Modo estricto y tsconfig

El archivo `tsconfig.json` decide qué tan exigente es el compilador. Las opciones que más cambian la calidad del código:

- **`strict: true`**: activa un grupo de verificaciones, entre ellas `strictNullChecks` (sin ella, `null` y `undefined` se pueden asignar a cualquier tipo, y desaparece la mitad de la protección) y `noImplicitAny` (un parámetro sin tipo que no se puede inferir es un error, no un `any` silencioso).
- **`noUncheckedIndexedAccess`**: `zonas[i]` o `porZona["norte"]` pasan a ser `T | undefined`, porque el índice puede no existir.
- **`noEmit`** junto con un transpilador aparte: `tsc` solo verifica y otra herramienta genera el JavaScript.

**Ejemplo:** activar `strict` en un proyecto existente de 40.000 líneas puede mostrar cientos de errores. Lo razonable es activarlo por carpetas, o silenciar los errores existentes con comentarios marcados, para que el código nuevo nazca estricto y la deuda quede contada.

### Tipos en el borde: validación en tiempo de ejecución

Como los tipos se borran, todo dato que entra al sistema se valida con un **esquema en tiempo de ejecución**. Las librerías de esquemas, de las cuales Zod es la más conocida, permiten declarar la forma una sola vez y obtener dos cosas: un validador que corre en tiempo de ejecución y el tipo de TypeScript **inferido** del esquema. Es el equivalente a Pydantic en Python, pero con el tipo derivado del validador en lugar de al revés.

```ts
import { z } from "zod";

const Clasificacion = z.object({
  categoria: z.enum(["demora", "danio", "direccion", "otro"]),
  prioridad: z.number().int().min(1).max(4),
  pedidoId: z.string().regex(/^p-\d+$/).nullable(),
  resumen: z.string().max(300),
});

type Clasificacion = z.infer<typeof Clasificacion>; // el tipo sale del esquema

const r = Clasificacion.safeParse(JSON.parse(textoDelModelo));
if (!r.success) {
  log.warn({ errores: r.error.issues.length }, "salida_llm_invalida");
} else {
  usar(r.data); // r.data: Clasificacion, validado
}
```

**Por qué importa:** si el tipo y el validador se escriben por separado, tarde o temprano divergen. Derivar uno del otro elimina esa clase de error.

### Tipos compartidos en un monorepo

Cuando el panel (frontend) y el BFF (backend) están en TypeScript y en el mismo repositorio, los esquemas pueden vivir en un paquete compartido, por ejemplo `@rumbo/contratos`. El BFF valida las peticiones con esos esquemas y el panel usa los tipos inferidos. Si alguien renombra `etaMin` a `etaMinutos`, el cambio rompe la compilación de ambos lados en el mismo pull request, en lugar de romper producción después del deploy.

Para servicios en otros lenguajes (el de asignación en Go, el de ETA en Python), el contrato compartido es un esquema neutral: OpenAPI, JSON Schema o Protobuf, del cual se generan tipos para cada lenguaje.

### TypeScript en el backend con Node.js

Node.js ejecuta JavaScript fuera del navegador con un único hilo y un bucle de eventos: muy eficiente para E/S (llamar APIs, esperar a un LLM, hablar con la base) y poco apto para cálculo intenso, que bloquea a todas las peticiones a la vez.

En Rumbo eso define dónde encaja:

| Uso | Lenguaje | Motivo |
|---|---|---|
| Asignación en tiempo real | Go | Latencia estable, concurrencia en varios núcleos |
| Modelos, datos, RAG del asistente | Python | Ecosistema de ML y clientes de LLM |
| BFF del panel, orquestación de chat | TypeScript | Comparte tipos con el frontend, mucha E/S y poco cálculo |
| Servidores MCP, scripts y herramientas internas | TypeScript | SDKs maduros, mismo lenguaje que el equipo de producto |

### Herramientas de build, a nivel conceptual

Hay dos tareas distintas que conviene no mezclar. **Verificar tipos** lo hace `tsc`, y es relativamente lento porque analiza todo el proyecto. **Transpilar** (quitar los tipos y generar JavaScript) lo hacen herramientas muy rápidas como esbuild o swc, que no verifican nada. Un **bundler** (Vite, por ejemplo) junta los módulos del frontend en pocos archivos optimizados.

La configuración típica: en desarrollo, transpilación rápida para recargar al instante; en CI, `tsc --noEmit` como paso obligatorio. Las versiones recientes de Node.js pueden ejecutar archivos TypeScript quitando los tipos al vuelo, sin verificarlos; los detalles cambian entre versiones, así que conviene verificar en la documentación vigente.

### TypeScript y agentes

Aquí TypeScript conecta con el resto del manual. Cinco usos concretos:

**1. Un esquema por herramienta, dos salidas.** Un agente necesita la definición de cada herramienta como JSON Schema (ver [Agentes y tool calling](#t/agentes)); el código que la ejecuta necesita el tipo de sus argumentos. Se declara el esquema una vez y se derivan ambos.

```ts
const BuscarPedido = z.object({
  pedidoId: z.string().describe("Identificador del pedido, por ejemplo p-981"),
  incluirEventos: z.boolean().default(false),
});

const definicion = {
  name: "buscar_pedido",
  description: "Devuelve estado, ETA y eventos de un pedido. Solo lectura.",
  input_schema: aJsonSchema(BuscarPedido), // conversión provista por la librería
};

async function ejecutar(argsDelModelo: unknown) {
  const args = BuscarPedido.parse(argsDelModelo); // valida antes de tocar la base
  return repo.buscar(args.pedidoId, args.incluirEventos);
}
```

La conversión de esquema a JSON Schema depende de la librería y su versión (verificar en la documentación vigente); lo importante es que haya una única fuente.

**2. Validar la salida estructurada.** Aunque el proveedor ofrezca "salidas estructuradas" que respetan un JSON Schema, se valida igual: el esquema garantiza la forma, pero no reglas como "el pedido existe" o "la prioridad 1 exige un motivo". La validación también protege si se cambia de modelo o de proveedor (ver [LLMs en producción](#t/llms-produccion)).

**3. Tipar los eventos del streaming.** La respuesta de un agente llega como una secuencia de eventos: texto parcial, inicio de herramienta, resultado, fin. Modelarlos como unión discriminada hace que el frontend maneje cada caso y que un evento nuevo obligue a actualizar el renderizado.

```ts
type EventoAgente =
  | { tipo: "texto"; delta: string }
  | { tipo: "herramienta_inicio"; id: string; nombre: string }
  | { tipo: "herramienta_fin"; id: string; ok: boolean }
  | { tipo: "fin"; tokensSalida: number };
```

**4. Servidores MCP en TypeScript.** El SDK oficial de MCP para TypeScript es de los más usados para escribir servidores ([MCP](#t/mcp)), y define las herramientas con esquemas de validación como los de arriba. El servidor que expone pedidos y alertas de Rumbo al agente de operaciones valida cada argumento antes de consultar la base.

**5. Agentes de código.** Un agente que modifica el repositorio se equivoca menos cuando el compilador le responde. Si un agente renombra un campo y olvida un uso, `tsc` lo señala con archivo y línea, y el agente lo corrige en la siguiente iteración. En un proyecto sin tipos, el mismo error aparece en producción. Por eso `tsc --noEmit` y los tests son la primera verificación que se le pide a un agente antes de dar un cambio por terminado.

## Casos prácticos

### Estados de herramienta que no aparecen en el chat

**Situación:** el chat del panel muestra "Consultando..." para siempre en algunas conversaciones. Se descubre que el backend agregó el estado `"cancelada"` cuando el usuario cierra la pestaña, y el frontend no lo contempla: cae en un `if` genérico que no hace nada.

**Qué se hace:** se reemplaza el objeto con `estado: string` por la unión discriminada `LlamadaHerramienta`, con el `default` que asigna a `never`. Al agregar `"cancelada"` al tipo compartido, el compilador señala los tres componentes que no la manejan. Se corrigen en el mismo pull request.

### El modelo devuelve una prioridad como texto

**Situación:** el clasificador de tickets del BFF hace `JSON.parse(respuesta) as Clasificacion`. Un día el modelo responde `"prioridad": "alta"`. El código compila, el tipo dice `number`, y el ordenamiento de la cola de soporte queda roto sin ningún error.

**Qué se hace:** se reemplaza el `as` por `Clasificacion.safeParse`. Si falla, se reintenta una vez incluyendo los errores de validación en el prompt y, si vuelve a fallar, el ticket va a la cola humana. Se agrega la métrica de salidas inválidas por versión de modelo, que además sirve para comparar modelos.

### Contrato roto entre panel y BFF

**Situación:** el BFF y el panel viven en repositorios separados con tipos copiados a mano. Un cambio en el BFF renombra `eta` a `etaMin`; el panel muestra "NaN minutos" durante dos horas hasta que alguien lo reporta.

**Qué se hace:** se mueven ambos a un monorepo con el paquete `@rumbo/contratos`, donde están los esquemas. El BFF valida con ellos y el panel usa los tipos inferidos. El CI corre `tsc --noEmit` en todos los paquetes afectados por un cambio, de modo que un renombre incompleto no llega a fusionarse.

### Un agente de código que deja `any` por todos lados

**Situación:** un agente de código migra un módulo y, para que compile, introduce 30 `any` y varios `as`. El cambio pasa la compilación y los tests, pero quedó sin protección.

**Qué se hace:** se activa una regla de lint que prohíbe `any` explícito y marca los `as` sobre datos externos, y se agrega al archivo de instrucciones del repositorio que los datos externos se tipan como `unknown` y se validan con esquemas. El agente recibe el error de lint como cualquier otro error y lo corrige.

## Errores comunes

- **Creer que los tipos validan datos.** `as Pedido` no verifica nada; los datos externos entran como `unknown` y pasan por un esquema.
- **Usar `any` para "destrabar" la compilación.** Apaga la protección y se propaga; usar `unknown` y verificar, o corregir el tipo.
- **Proyectos sin `strict`.** Sin `strictNullChecks`, la mayoría de los errores de `undefined` siguen llegando a producción.
- **Modelar estados con campos opcionales sueltos.** Permite estados imposibles; usar uniones discriminadas con verificación de exhaustividad.
- **Duplicar el tipo y el validador.** Divergen con el tiempo; inferir el tipo desde el esquema.
- **Hacer cálculo pesado en Node.js.** Bloquea el bucle de eventos para todas las peticiones; moverlo a otro servicio o a un worker.

## Para discutir en equipo

- ¿Qué contratos entre servicios conviene definir con esquemas compartidos de TypeScript y cuáles con OpenAPI o Protobuf, sabiendo que hay servicios en Go y Python?
- ¿Cómo garantizamos que cada herramienta de nuestros agentes tenga una única fuente para su esquema y su tipo?
- ¿Qué opciones de `tsconfig` y reglas de lint exigimos en proyectos nuevos, y cómo migramos los existentes sin frenar el trabajo?
- ¿Qué hacemos cuando la salida estructurada del modelo es válida en forma pero incorrecta en contenido?
- ¿Qué verificaciones automáticas le pedimos a un agente de código antes de aceptar un cambio en TypeScript?
