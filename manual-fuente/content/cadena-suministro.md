---
slug: cadena-suministro
titulo: Cadena de suministro y vulnerabilidades
resumen: Cómo proteger el camino del código de terceros hasta producción y cómo priorizar vulnerabilidades con CVSS, EPSS y alcanzabilidad, incluidos agentes, MCP y modelos.
lectura: 15
---

## La idea central

Casi todo lo que corre en producción lo escribió otra persona. Un servicio de Go de 8.000 líneas propias puede arrastrar 150 módulos de terceros, una imagen base con 400 paquetes del sistema operativo y una docena de actions de CI. La **cadena de suministro de software** es todo ese camino: de dónde viene cada pieza, quién la construyó, cómo llegó a nuestro artefacto y qué termina corriendo. Un atacante no necesita romper nuestro código si puede meterse en cualquier eslabón anterior.

La analogía útil es una cocina profesional: hay que saber a qué proveedor se le compra cada ingrediente, verificar que el envase esté sellado y, cuando se anuncia un lote contaminado, saber en minutos qué platos lo usaron. Este tema profundiza lo que [CI/CD y GitOps](#t/ci-cd) presenta de forma breve y agrega qué hacer cuando aparece una vulnerabilidad, y cómo cambia todo con agentes que agregan dependencias, servidores MCP de terceros y archivos de modelos.

## Conceptos

### Los eslabones de la cadena y cómo se atacan

La cadena tiene cinco eslabones, cada uno con su forma de ataque típica:

1. **Código fuente:** el repositorio propio. Riesgo: una cuenta con permisos de escritura comprometida, o un cambio que entra sin revisión.
2. **Dependencias:** bibliotecas de registros públicos (npm, PyPI, Go modules, Maven). Riesgos:
   - **Mantenedor comprometido:** alguien toma la cuenta de quien publica un paquete popular y sube una versión con código malicioso. Todos los que actualizan la reciben.
   - **Typosquatting:** un paquete con un nombre casi igual a uno conocido (una letra cambiada, un guion de más) que espera a que alguien se equivoque al escribir.
   - **Confusión de dependencias:** la empresa usa un paquete interno llamado `rumbo-geo`; un atacante publica `rumbo-geo` en el registro público con un número de versión más alto. Si el gestor de paquetes consulta ambos registros y elige la versión mayor, instala el público.
3. **Build:** si se compromete el runner o un script de build, el artefacto sale contaminado aunque el código fuente esté limpio. La revisión de código no lo ve.
4. **Artefactos:** imágenes y paquetes en un registro. Riesgo: alguien sube a mano una imagen con el mismo tag.
5. **Deploy:** lo que efectivamente se ejecuta. Riesgo: desplegar algo que nunca pasó por el pipeline.

**Ejemplo:** un paquete de fechas muy descargado publica la versión 3.4.2 con un script de instalación que envía las variables de entorno a un servidor externo. Un servicio que declara `^3.4.0` sin lockfile la instala en el próximo build, y se filtran las credenciales del runner de CI.

**Por qué importa:** la mayoría de las defensas apuntan a un eslabón concreto. Pensar en los cinco evita creer que un escáner de vulnerabilidades cubre todo.

### Higiene de dependencias

La higiene de dependencias reduce la superficie antes de que aparezca un problema:

- **Lockfile:** archivo generado (`package-lock.json`, `poetry.lock`, `go.sum`) que registra la versión exacta y el hash de cada dependencia, incluidas las transitivas. Con lockfile, dos builds del mismo commit instalan lo mismo; sin él, `^3.4.0` puede resolver distinto de un día para otro. Se commitea y el CI instala en modo estricto (`npm ci`, por ejemplo), que falla si el lockfile no coincide.
- **Pocas dependencias:** una función de 10 líneas no justifica una dependencia con 30 transitivas.
- **Revisión de dependencias nuevas:** quién la mantiene, cuánta actividad tiene, cuántas dependencias trae, si tiene scripts de instalación y qué licencia usa.
- **PRs automáticos de actualización:** un bot abre PRs semanales con versiones nuevas. Mantenerse cerca de la última versión hace que un parche de seguridad sea un cambio chico.
- **Registro interno con prioridad:** para evitar la confusión de dependencias, los nombres internos se reservan con un prefijo de organización y el gestor de paquetes resuelve esos nombres solo desde el registro interno.

**Ejemplo:** el frontend del panel de comercios tiene 1.200 paquetes en su lockfile. Una revisión encuentra que 3 dependencias directas aportan 410 transitivas; dos se reemplazan por 60 líneas propias y el lockfile baja a 790 paquetes.

**Por qué importa:** la mitad de los incidentes de cadena de suministro se evitan con un lockfile estricto y un poco de demora en adoptar versiones recién publicadas.

### SBOM: el inventario de cada artefacto

Un **SBOM** (Software Bill of Materials) es la lista de ingredientes de un artefacto: cada componente, su versión, su origen y, a veces, su licencia y su hash. Se genera en el pipeline al construir la imagen y se guarda junto a ella en el registro.

Hay dos formatos estándar muy usados, SPDX y CycloneDX. A nivel conceptual son equivalentes para el uso diario: los dos describen componentes y relaciones en JSON, y las herramientas de escaneo leen ambos.

El valor aparece cuando se publica una vulnerabilidad nueva:

1. Llega el aviso: una biblioteca de XML, versiones 2.0 a 2.3, tiene una falla grave.
2. Sin SBOM, cada equipo revisa sus repositorios a mano y se le escapan las dependencias transitivas.
3. Con SBOM indexados, una consulta responde qué imágenes la contienen y, cruzado con el clúster, cuáles están en producción.

**Ejemplo:** Rumbo tiene 64 imágenes en producción. Con los SBOM indexados, la consulta devuelve en 2 minutos: 5 imágenes contienen la biblioteca afectada, 3 en producción, todas como dependencia transitiva de un cliente de mensajería.

**Por qué importa:** el tiempo entre "se publicó la vulnerabilidad" y "sabemos si nos afecta" pasa de días a minutos.

### Firma de artefactos y procedencia

Saber qué hay dentro de un artefacto no dice quién lo construyó. Para eso hay dos herramientas:

- **Firma:** el pipeline firma el digest de la imagen. Un controlador de admisión en el clúster verifica la firma antes de dejar correr un pod: una imagen subida a mano, sin firma válida, no se despliega. Herramientas como cosign permiten firmar sin manejar claves de larga duración, usando la identidad OIDC del workflow.
- **Procedencia (provenance):** un documento firmado que dice qué repositorio, qué commit, qué workflow y qué runner produjeron el artefacto. Permite verificar, por ejemplo, que la imagen viene de `main` del repositorio correcto y no de una rama de prueba.

**SLSA** es un marco que ordena estas prácticas en niveles crecientes. En términos generales: el nivel más bajo pide que exista procedencia; los intermedios, que la genere una plataforma de build alojada y que esté firmada; el más alto, que el build corra aislado y que la procedencia no pueda ser falsificada por el propio job. Los nombres exactos de los niveles y sus requisitos cambiaron entre versiones del marco: verificar la documentación vigente antes de comprometerse a un nivel.

**Ejemplo:** el clúster de producción de Rumbo exige firma del workflow de CI y procedencia de `main`. Durante un incidente, una imagen construida en una laptop con un parche rápido es rechazada; el parche entra por PR con revisión acelerada y llega en 14 minutos, con trazabilidad.

**Por qué importa:** la firma y la procedencia protegen los eslabones de build, artefacto y deploy, que el escaneo de dependencias no cubre.

### Vulnerabilidades: CVE, CVSS, EPSS y alcanzabilidad

Una **CVE** es un identificador público de una vulnerabilidad concreta. Sirve para que todos hablen de lo mismo; no dice cuán grave es para nosotros.

**CVSS** es un puntaje de 0 a 10 que describe la severidad técnica: cómo se explota (por red o local), si requiere privilegios o interacción del usuario, y qué impacto tiene en confidencialidad, integridad y disponibilidad. Las bandas habituales son baja (menos de 4), media (4 a 6,9), alta (7 a 8,9) y crítica (9 o más). Sus límites: describe el peor caso genérico, no nuestro contexto, y una gran cantidad de CVE altas y críticas nunca se explotan en la práctica.

**EPSS** estima la probabilidad de que una vulnerabilidad sea explotada en los próximos 30 días, a partir de datos observados. Una CVE con CVSS 9,8 puede tener EPSS de 0,2 % y otra con CVSS 7,5, de 60 %. Complementa al CVSS: uno dice cuánto daño haría, el otro cuán probable es que alguien lo intente. También existen catálogos públicos de vulnerabilidades con explotación activa confirmada, que pesan más que cualquier estimación.

La **alcanzabilidad** (reachability) pregunta si nuestro código llega a ejecutar la función vulnerable. Si la falla está en el parser de un formato de imagen y nuestro servicio usa la biblioteca solo para redimensionar imágenes ya validadas, o nunca llama a esa función, el riesgo real es mucho menor.

**Ejemplo de priorización** (cifras hipotéticas) con cuatro hallazgos del mismo día:

| CVE | Dónde | CVSS | EPSS | ¿Alcanzable? | ¿Expuesto? | Prioridad |
|---|---|---|---|---|---|---|
| A | Framework HTTP del API gateway | 8,1 | 45 % | Sí, en cada request | Internet | 1: parchear hoy |
| B | Biblioteca XML del servicio de importación de pedidos | 9,8 | 3 % | Sí, procesa archivos de comercios | Interno, recibe archivos externos | 2: parchear esta semana |
| C | Paquete del sistema en la imagen base del modelo de ETA | 9,1 | 0,4 % | No: es una herramienta de línea de comandos que el servicio no ejecuta | Interno | 3: se resuelve con la próxima imagen base |
| D | Biblioteca de gráficos en un script de análisis local | 7,5 | 1 % | Solo en notebooks | No corre en producción | 4: excepción documentada |

La CVE con mayor CVSS (B) no es la primera: A tiene probabilidad alta de explotación, es alcanzable y está expuesta a internet. C tiene CVSS crítico, pero el código no se ejecuta.

**Por qué importa:** con cientos de hallazgos por mes, ordenar solo por CVSS hace que el equipo pase semanas en falsos urgentes mientras lo realmente explotable espera.

### SLA por severidad y excepciones con vencimiento

Un **SLA de remediación** fija plazos por prioridad: por ejemplo, 2 días para críticas explotables y expuestas, 15 para altas, 60 para medias y las bajas con la próxima actualización. El plazo corre desde la detección.

Cuando no se puede parchear a tiempo (no hay versión corregida, o el cambio rompe algo), se registra una **excepción**: qué CVE, por qué no aplica o qué mitigación hay (una regla de WAF, deshabilitar la función), quién la aprueba y **cuándo vence**. Sin vencimiento, la excepción se vuelve permanente y nadie la vuelve a mirar.

**Ejemplo:** la CVE C del caso anterior recibe una excepción de 45 días con la justificación "binario no invocado; se elimina al migrar a imagen base mínima". A los 45 días, el escáner vuelve a marcarla si sigue presente, y la excepción no se puede renovar sin una nueva aprobación.

**Por qué importa:** un SLA sin excepciones con vencimiento termina en dos extremos: o se ignora, o bloquea despliegues por hallazgos irrelevantes.

### Imágenes base y escaneo de contenedores

La mayor parte de las vulnerabilidades de una imagen suele venir de la **imagen base**: shells, gestores de paquetes y cientos de bibliotecas que el servicio nunca usa.

Prácticas:

- **Imágenes mínimas** (distroless o equivalentes): solo el runtime necesario. Menos paquetes, menos CVE, menos herramientas para un atacante que logre entrar.
- **Imágenes base propias y actualizadas:** plataforma mantiene un pequeño conjunto de imágenes base, se reconstruyen semanalmente y los servicios las heredan.
- **Escaneo en dos momentos:** al construir y de forma continua sobre el registro, porque una imagen limpia hoy puede tener una CVE mañana.

**Ejemplo:** el servicio de asignación en Go pasa de una imagen basada en una distribución completa (unos 380 paquetes, 47 CVE reportadas) a una imagen mínima con el binario estático (menos de 10 paquetes, 2 CVE).

**Por qué importa:** elegir bien la imagen base elimina de una vez la mayoría de los hallazgos, en lugar de parchearlos uno por uno en cada servicio.

### Escaneo de secretos en repositorios

Un secreto commiteado queda en el historial de git aunque se borre después. El escaneo busca formatos de claves conocidos y cadenas de alta entropía en tres lugares: antes del commit, en el servidor al recibir el push (bloqueando) y sobre todo el historial, de forma periódica.

Si aparece un secreto, el orden es: **revocar y rotar primero**, investigar el uso después y limpiar el historial al final. Limpiar el historial sin rotar no sirve: alguien pudo clonarlo. El manejo y la rotación se detallan en [Secretos y cifrado](#t/secretos).

**Ejemplo:** el escaneo en el push bloquea un commit con un archivo `.env` que contiene la clave del proveedor de mapas. El commit nunca llega al servidor y no hay que rotar nada.

**Por qué importa:** cuanto antes se detecta el secreto, más barato es: bloquear un push no cuesta nada; una clave que estuvo meses en el historial obliga a rotar e investigar.

### Agentes de código que agregan dependencias

Los agentes de código instalan paquetes con la misma naturalidad con que escriben una función, y a veces **inventan nombres**: proponen `import geo_route_utils` o `npm install fast-eta-calc` porque el nombre suena plausible, aunque no exista. Los atacantes registran esos nombres alucinados de forma recurrente en los registros públicos con código malicioso; a esta variante del typosquatting se la llama **slopsquatting**.

Controles:

1. El agente no instala directamente: propone el cambio en un PR.
2. Un check del CI marca toda dependencia nueva y verifica antigüedad mínima (por ejemplo, 30 días), mantenedores identificables y que sea el paquete que se cree, no uno de nombre parecido.
3. Una persona revisa cada dependencia nueva, y el entorno del agente no tiene credenciales que valga la pena robar.

**Ejemplo:** un agente propone agregar `pydantic-xml-utils` para un parseo que resuelve la biblioteca estándar. El check muestra que el paquete tiene 6 días, una sola versión y un script de instalación; el PR queda bloqueado.

**Por qué importa:** un agente que agrega dependencias sin control multiplica el ritmo al que entran terceros desconocidos al código.

### Servidores MCP, plugins y modelos como dependencias

Un **servidor MCP** o un plugin de agente es una dependencia con privilegios: ejecuta código con acceso a red y credenciales, y sus descripciones de herramientas son texto que el modelo obedece (ver [MCP](#t/mcp) y [Seguridad de LLMs y agentes](#t/seguridad-agentes)). Se tratan como una biblioteca crítica: versión fija por digest, revisión del código y de las descripciones en cada actualización, red y permisos mínimos, e inventario por agente.

Los **archivos de modelos** también son artefactos. Algunos formatos de serialización, como pickle en Python, pueden ejecutar código arbitrario al cargarse: abrir un modelo descargado de un repositorio público equivale a ejecutar un programa de un desconocido. Los formatos que guardan solo tensores (como safetensors) no tienen ese riesgo. Para modelos de terceros conviene registrar la procedencia (de dónde vino, qué hash tenía, qué licencia), guardar una copia en un registro interno y cargarla siempre desde ahí.

Por último, **prompts y definiciones de herramientas** son parte del artefacto: viven en el repositorio, se revisan en PR y su versión queda asociada a cada despliegue, igual que el código.

**Ejemplo:** el agente de operaciones usa un servidor MCP comunitario para consultar métricas. Se fija por digest de imagen, corre en un pod sin salida a internet salvo hacia Prometheus y su manifiesto de herramientas se guarda en el repositorio. Cuando el bot propone una versión nueva, el diff muestra que una descripción de herramienta cambió de 2 a 14 líneas; la revisión lo detecta antes de conectarlo.

**Por qué importa:** en un sistema con agentes, la cadena de suministro incluye texto que el modelo interpreta como instrucciones, no solo código.

## Casos prácticos

### Una vulnerabilidad crítica en una biblioteca de logging, un viernes

**Situación:** se publica una vulnerabilidad de ejecución remota en una biblioteca de logging muy usada en la JVM, con explotación activa reportada.
**Qué se hace:** los SBOM indexados identifican en 5 minutos 7 imágenes afectadas, 4 en producción, una expuesta a internet. Se aplica una regla de WAF como mitigación temporal, se parchea la expuesta en 3 horas y las demás antes del lunes. Dos imágenes de un proveedor no tienen parche: excepción de 10 días con aislamiento de red.

### Confusión de dependencias en el build de Python

**Situación:** el paquete interno `rumbo-zonas` se instala desde el registro interno. Una auditoría descubre que el gestor de paquetes del CI consulta también el registro público y elige la versión más alta; alguien publicó `rumbo-zonas` versión 99.0 en el registro público (de momento, vacío).
**Qué se hace:** los paquetes con prefijo `rumbo-` se resuelven solo desde el registro interno, el lockfile incluye hashes y el CI instala en modo estricto. Un check falla si un paquete interno se resuelve desde otro origen.

### El agente que sugirió un paquete inexistente

**Situación:** un desarrollador acepta la sugerencia de un agente de código de instalar un paquete para validar direcciones. El paquete existe, pero tiene 3 semanas, un único autor y un script de instalación que envía las variables de entorno a un servidor externo. Ocurrió en una laptop.
**Qué se hace:** se trata como incidente: se rotan las credenciales de esa máquina y se revisa su uso. El agente deja de ejecutar instalaciones directamente, y en local el gestor de paquetes pasa por el registro interno como proxy, que exige antigüedad mínima y bloquea scripts de instalación por defecto.

### Modelo de clasificación descargado de un repositorio público

**Situación:** el equipo del asistente de soporte quiere probar un clasificador de intenciones publicado en un repositorio público de modelos. El archivo de pesos está en formato pickle.
**Qué se hace:** no se carga en ninguna máquina con credenciales. Se usa la versión en formato de solo tensores, se verifica su hash, se registra en el registro interno de modelos con origen y licencia, y el servicio carga siempre desde ahí. El pipeline rechaza formatos de modelo que permiten ejecutar código.

## Errores comunes

- **Priorizar solo por CVSS.** Genera urgencias falsas y oculta lo explotable. Combinar CVSS con EPSS, explotación activa conocida, alcanzabilidad y exposición.
- **Excepciones sin vencimiento.** Se vuelven permanentes. Toda excepción tiene responsable, mitigación y fecha de revisión.
- **Lockfile sin modo estricto en CI.** El lockfile existe pero el build lo ignora o lo regenera. Instalar con el comando que falla si no coincide.
- **Borrar un secreto del repositorio sin rotarlo.** El historial ya pudo copiarse. Rotar primero, limpiar después.
- **Conectar servidores MCP o plugins por "latest".** Una actualización puede cambiar código y descripciones sin aviso. Fijar por digest y revisar cada cambio.
- **Cargar modelos de terceros en formatos que ejecutan código.** Preferir formatos de solo tensores y cargar desde un registro interno con procedencia registrada.

## Para discutir en equipo

- Si hoy se publica una vulnerabilidad crítica en una biblioteca común, ¿cuánto tardamos en saber qué servicios en producción la tienen?
- ¿Qué SLA de remediación es realista para cada prioridad, y quién aprueba las excepciones?
- ¿Qué controles necesita un agente de código antes de poder proponer dependencias nuevas sin revisión especial?
- ¿Qué servidores MCP y plugins usan hoy nuestros agentes, quién los revisó y con qué versión están fijados?
- ¿Qué nivel de firma y procedencia exigimos para imágenes y para modelos, y qué hacemos en las instalaciones on-prem de clientes grandes?
