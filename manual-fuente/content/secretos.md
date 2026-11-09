---
slug: secretos
titulo: Secretos y cifrado
resumen: Cómo guardar, inyectar, rotar y auditar credenciales y claves, y cómo usar KMS y el cifrado de sobre para proteger datos sensibles.
lectura: 13
---

## La idea central

Un sistema como Rumbo depende de decenas de credenciales: la contraseña de Aurora, la clave de API del proveedor de mapas, la del proveedor de LLM, la clave con la que firmamos los webhooks que enviamos a los comercios, los certificados para hablar con socios. Cada una es una llave que abre una puerta. La gestión de secretos responde cuatro preguntas: **dónde** se guarda la llave, **cómo** llega al servicio que la usa sin pasar por lugares inseguros, **cada cuánto** se cambia y **quién** puede usarla (y queda registrado).

El cifrado es la otra mitad del tema. Cifrar datos es fácil; lo difícil es proteger las claves con las que se cifra. Por eso existen servicios como KMS, que guardan las claves maestras en hardware del que no se pueden extraer, y técnicas como el cifrado de sobre, que permiten cifrar terabytes sin que la clave maestra salga nunca de ese hardware. Una analogía: no guardas las joyas en una caja fuerte gigante, guardas cada joya en una cajita con su propia llave, y solo las llavecitas van a la caja fuerte.

## Conceptos

### Qué es un secreto

Un secreto es cualquier dato que, en manos equivocadas, permite hacerse pasar por nosotros o acceder a algo protegido. En Rumbo:

- **Contraseñas de bases de datos:** el usuario con el que el servicio de asignación se conecta a Aurora.
- **Claves de API de terceros:** el proveedor de mapas que calcula rutas y distancias, y el proveedor de LLM que usa el asistente de soporte. Además de dar acceso, se facturan por uso: una clave filtrada puede generar consumo ajeno a nuestro nombre.
- **Claves de firma de webhooks:** cuando avisamos a un comercio que su pedido fue entregado, firmamos el mensaje con HMAC para que el comercio verifique que viene de nosotros. Quien tenga la clave puede falsificar avisos.
- **Certificados y claves privadas TLS:** para servir HTTPS y para autenticarnos ante socios con mTLS.
- **Tokens de servicio:** credenciales del agente interno de operaciones para leer métricas y logs.

Un dato no es secreto por ser sensible: la dirección de un destinatario es PII (hay que protegerla), pero no es una credencial. Ambos requieren cuidado, con técnicas distintas.

**Por qué importa:** si no tenemos un inventario de secretos, no podemos rotarlos ni saber cuáles se vieron comprometidos en un incidente.

### Secrets Manager vs. Parameter Store

AWS ofrece dos servicios para guardar secretos:

| Aspecto | Secrets Manager | Parameter Store (SSM) |
|---|---|---|
| Pensado para | Secretos que hay que rotar | Configuración y secretos simples |
| Rotación automática | Sí, con funciones Lambda (integrada para RDS/Aurora) | No nativa, hay que construirla |
| Cifrado | Siempre con KMS | Opcional (tipo `SecureString`) |
| Versiones | Etiquetas `AWSCURRENT` / `AWSPREVIOUS` | Historial de versiones numeradas |
| Costo (orden de magnitud, hipotético) | Cargo mensual por secreto más llamadas | Gratis en nivel estándar, cargo en avanzado |
| Replicación entre regiones | Sí | No nativa |

Una regla práctica: credenciales de bases y claves que rotamos en Secrets Manager; flags y configuración no sensible en Parameter Store. Lo importante es elegir uno por tipo de dato y no repartir secretos en cinco lugares.

**Ejemplo:** la contraseña de Aurora vive en Secrets Manager con rotación cada 30 días; el umbral `ETA_TIMEOUT_MS=40` vive en Parameter Store como `String` normal.

### Nunca en el código

Un secreto en el repositorio queda en el historial de git para siempre, aunque se borre en el commit siguiente, y lo ve cualquiera con acceso al repo, a sus forks y a los logs de CI. La alternativa es **inyectar en ejecución**:

1. El servicio corre con una identidad (en EKS, un rol IAM asociado a su service account).
2. Al arrancar, o mediante un componente como External Secrets Operator o el CSI driver de secretos, se lee el secreto desde Secrets Manager.
3. El secreto llega como archivo montado en memoria o variable de entorno, nunca escrito en la imagen del contenedor ni en Terraform en texto plano.

Como red de seguridad, el pipeline de CI corre **escaneo de secretos** en cada push (herramientas que buscan patrones como claves de AWS o tokens de proveedores) y bloquea el merge si encuentra algo. Conviene también un hook local antes del commit, porque una vez que el secreto llegó al servidor remoto ya hay que considerarlo filtrado.

**Por qué importa:** el escaneo no reemplaza la rotación. Si algo se filtró, la única respuesta segura es invalidarlo.

### KMS

**KMS** (Key Management Service) gestiona claves criptográficas. Lo esencial: las claves maestras (llamadas KMS keys) **nunca salen** del servicio. No puedes descargar la clave; le pides a KMS que cifre o descifre por ti, y cada llamada queda registrada en CloudTrail con quién la hizo.

Cada clave tiene una **política de clave** que define quién la administra y quién la usa. Eso permite separar: el equipo de plataforma puede administrar la clave (rotarla, cambiar su política) sin poder usarla para descifrar datos, y el servicio de asignación puede descifrar sin poder modificar la política.

KMS rota automáticamente el material criptográfico de la clave (por ejemplo, una vez al año) conservando las versiones viejas para descifrar lo ya cifrado. Esto es transparente para las aplicaciones.

**Ejemplo:** la clave `alias/rumbo-pii` cifra los datos personales de destinatarios. Solo tres roles pueden usarla para descifrar: el servicio de pedidos, el de notificaciones y un rol de soporte con aprobación previa.

### Cifrado de sobre (envelope encryption)

KMS tiene un límite: cifra directamente solo hasta 4 KB, y cada llamada tarda unos milisegundos y cuesta. No podemos mandar un archivo de 5 GB ni millones de registros por segundo a KMS. La solución es el **cifrado de sobre**:

1. La aplicación pide a KMS una **clave de datos** (data key) con `GenerateDataKey`.
2. KMS devuelve dos cosas: la clave de datos **en claro** y la misma clave de datos **cifrada** con la clave maestra.
3. La aplicación cifra el dato localmente con la clave en claro (AES-256-GCM, rápido, sin límite de tamaño).
4. La aplicación **descarta** la clave en claro de la memoria.
5. Guarda juntos el dato cifrado y la clave de datos cifrada (el "sobre").
6. Para leer: envía la clave de datos cifrada a KMS con `Decrypt`, recibe la clave en claro, descifra el dato localmente y vuelve a descartar la clave.

```text
 CIFRAR
 ------
 Aplicación                         KMS (la clave maestra nunca sale)
     |   GenerateDataKey(rumbo-pii)   |
     |------------------------------->|
     |   DK_claro + DK_cifrada        |
     |<-------------------------------|
     |
     |  AES-GCM(DK_claro, dato) ---> dato_cifrado
     |  borrar DK_claro de memoria
     v
 Almacenamiento: [ DK_cifrada | dato_cifrado ]   <- el "sobre"

 DESCIFRAR
 ---------
 Aplicación                         KMS
     |   Decrypt(DK_cifrada)          |
     |------------------------------->|  (verifica permisos, registra en CloudTrail)
     |   DK_claro                     |
     |<-------------------------------|
     |  AES-GCM-decrypt(DK_claro, dato_cifrado) ---> dato
     |  borrar DK_claro de memoria
```

**Ejemplo:** cifrar 1 millón de direcciones con una clave de datos por registro serían 1 millón de llamadas a KMS. Si usamos una clave de datos por lote de 10.000 registros (o la cacheamos unos minutos con un SDK de cifrado), son 100 llamadas. Con un precio hipotético de 3 USD por cada 100.000 llamadas, pasamos de 30 USD a menos de un centavo, y la latencia cae de forma similar.

**Por qué importa:** es lo que usan por dentro S3, EBS y Aurora cuando dices "cifrar con KMS". Entenderlo permite razonar sobre costos, latencia y qué pasa si alguien pierde el permiso sobre la clave (no puede leer nada, aunque tenga el archivo).

### Rotación con dos versiones válidas

Rotar un secreto significa reemplazarlo por uno nuevo. Si se hace de golpe (cambiar la contraseña en la base y en el gestor a la vez), los pods que todavía tienen la vieja en memoria fallan. La técnica segura es tener **dos versiones válidas** durante una ventana:

1. Crear la credencial nueva sin invalidar la vieja (en bases de datos, se alternan dos usuarios: `asignacion_a` y `asignacion_b`).
2. Publicar la nueva como versión actual en Secrets Manager.
3. Esperar a que todos los consumidores la tomen (refresco periódico o reinicio gradual).
4. Verificar con métricas que nadie usa la vieja.
5. Recién entonces revocar la vieja.

Para claves de firma de webhooks, el equivalente es firmar con la nueva y que los comercios acepten ambas durante una semana. Para claves de API de proveedores, crear la segunda clave en el proveedor antes de borrar la primera.

**Por qué importa:** si rotar da miedo, no se rota, y un secreto que nunca rota es un secreto que eventualmente se filtra sin que lo notemos.

### HSM

Un **HSM** (Hardware Security Module) es un dispositivo físico diseñado para guardar claves y operar con ellas sin exponerlas, con protección contra manipulación. KMS usa HSM por dentro. **CloudHSM** da un HSM dedicado bajo nuestro control exclusivo; se justifica cuando una regulación o un cliente exige control exclusivo del hardware, o para clientes on-prem que tienen su propio HSM (ver [Despliegue híbrido y on-prem](#t/hibrido-on-prem)). Para la mayoría de los casos, KMS alcanza y es mucho más simple de operar.

### Certificados y mTLS

En TLS normal, solo el servidor presenta un certificado. En **mTLS** (TLS mutuo), ambos lados presentan uno: así un socio logístico que nos envía actualizaciones de estado sabe que habla con Rumbo, y nosotros sabemos que habla él. Cada certificado tiene fecha de vencimiento, y un certificado vencido corta la conexión de golpe.

Lo que hace falta:

- **Inventario:** lista de todos los certificados, para qué sirven, quién es el dueño, quién es la contraparte y cuándo vencen.
- **Renovación automática** donde se pueda (ACM para nuestros endpoints públicos, cert-manager dentro de EKS).
- **Alertas de vencimiento** escalonadas: a 30, 14 y 7 días, con un dueño que las reciba.

**Ejemplo:** un certificado de socio con vencimiento a 398 días. Si la alerta llega solo un día antes, no hay tiempo de coordinar con el otro lado; a 30 días sí.

### Separación de funciones

Ninguna persona o rol debería poder, sola, crear un secreto, leerlo y borrar el registro de que lo leyó. En la práctica:

- Quien administra las claves KMS no puede usarlas para descifrar datos.
- El acceso humano a secretos de producción es excepcional, con aprobación y tiempo limitado ("break glass"), y queda auditado.
- Los registros de CloudTrail van a una cuenta de auditoría separada donde los equipos operativos no pueden borrar.

## Casos prácticos

### Clave de API del proveedor de LLM en un commit

**Situación:** al depurar el asistente de soporte, alguien deja la clave del proveedor de LLM en un archivo de configuración y la sube a una rama. El escaneo de CI la detecta 10 minutos después, pero ya está en el servidor de git.

**Qué se hace:** se trata como comprometida aunque el repo sea privado. Primero se crea una clave nueva en el proveedor, se publica en Secrets Manager y se espera a que el asistente la tome; luego se revoca la vieja. Se revisa el consumo de la clave en el panel del proveedor para detectar uso ajeno. Reescribir el historial de git es opcional y secundario: la clave ya está invalidada. Como mejora, el gateway de LLM concentra la clave en un solo servicio, de modo que los desarrolladores usan credenciales propias de bajo límite y nunca ven la de producción (ver [LLMs en producción](#t/llms-produccion)).

### Rotación que corta el servicio

**Situación:** se activa la rotación automática de la contraseña de Aurora. A los 30 días, la función de rotación cambia la contraseña y el servicio de asignación, que la leyó solo al arrancar, empieza a fallar con errores de autenticación al abrir conexiones nuevas. La asignación de pedidos se degrada 20 minutos.

**Qué se hace:** se cambia a la estrategia de rotación con usuarios alternados, que deja la credencial anterior válida hasta la siguiente rotación. El servicio refresca el secreto cada 5 minutos y, ante un error de autenticación, relee el secreto y reintenta una vez. Se agrega una rotación en staging con frecuencia diaria para ejercitar el camino, y una alerta sobre errores de autenticación a la base.

### Cifrar datos personales de destinatarios con cifrado de sobre

**Situación:** Aurora ya cifra el disco, pero cualquiera con acceso de lectura a la base ve nombres, teléfonos y direcciones en claro, incluidas las réplicas que usa analítica.

**Qué se hace:** cifrado a nivel de campo con cifrado de sobre: el servicio de pedidos cifra `telefono` y `direccion` con claves de datos derivadas de `alias/rumbo-pii` antes de escribir. Solo los servicios que realmente necesitan el dato en claro (notificaciones, la app del transportista) tienen permiso de `Decrypt`. Analítica trabaja con la zona y un hash del teléfono, sin descifrar. Para la búsqueda exacta por teléfono que necesita soporte se guarda un HMAC del valor normalizado. Un beneficio extra: para "olvidar" a un comercio entero se puede destruir su clave de datos (crypto-shredding).

### Certificado mTLS con un socio que vence un viernes a la noche

**Situación:** el viernes a las 22:00 las actualizaciones de estado de un socio logístico empiezan a fallar con errores de handshake. El certificado cliente que nos presentaba venció; la persona del socio que lo gestionaba ya no trabaja ahí.

**Qué se hace:** en lo inmediato, el on-call sigue el runbook: confirma el vencimiento, contacta al socio por el canal de emergencia acordado y, si el socio genera un certificado nuevo, se agrega a la lista de confianza sin redeploy. Si no hay respuesta, se activa la alternativa acordada (polling a su API) mientras tanto. Después, el postmortem agrega el certificado al inventario con alertas a 30, 14 y 7 días hacia ambos lados, exige un contacto técnico de respaldo en el acuerdo con el socio y permite aceptar dos certificados a la vez para que la renovación sea un solapamiento y no un corte.

## Errores comunes

- **Borrar el secreto del repo y darlo por resuelto.** El historial y los clones lo conservan; hay que rotarlo siempre.
- **Rotar sin solapamiento.** Revocar la credencial vieja en el mismo instante en que se crea la nueva provoca caídas; usa dos versiones válidas.
- **Una sola clave KMS para todo.** Mezcla permisos de datos muy distintos; separa claves por dominio (PII, backups, logs) para poder restringir y auditar.
- **Secretos en variables de Terraform en texto plano.** Terminan en el estado y en los logs del plan; referencia el secreto por ARN y deja que el servicio lo lea en ejecución.
- **Certificados sin dueño ni alerta.** El vencimiento es la causa de corte más predecible que existe; inventario y alertas escalonadas.
- **Imprimir secretos en logs al depurar.** Configura el logger para enmascarar campos sensibles y revisa que los errores de conexión no incluyan la cadena con la contraseña.

## Para discutir en equipo

- ¿Tenemos un inventario de todos los secretos y certificados, con dueño y fecha de última rotación? Si mañana se filtra uno, ¿sabemos qué servicios dejan de funcionar al rotarlo?
- ¿Qué datos personales deberían cifrarse a nivel de campo y no solo en disco, y qué costo de latencia aceptamos por eso en el servicio de asignación?
- ¿Cuándo justificaría un cliente on-prem usar su propio HSM, y cómo cambia eso nuestra arquitectura de cifrado?
- ¿Quién puede hoy leer un secreto de producción a mano, y cómo nos enteraríamos si lo hiciera?
