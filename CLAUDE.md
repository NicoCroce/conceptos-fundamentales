# Manual de AI/ML y Plataforma

Manual de estudio para un equipo de ingeniería, publicado en una URL como sitio estático que funciona sin conexión (y también como un único HTML), con menú lateral, buscador, glosario y progreso de lectura. Lo leen ingenieros backend, de ML, de plataforma y de frontend. El objetivo es entender cada tema lo suficiente para conversar con criterio y revisar diseños, no para implementarlo.

## Estructura

- `manual-fuente/dist/web/`: el sitio que se publica (se genera; no se edita a mano).
- `Manual AI-ML y Plataforma.html`: la misma versión en un solo archivo, para abrir con doble clic. Se genera.
- `manual-fuente/content/<slug>.md`: un archivo por tema, con front matter (`slug`, `titulo`, `resumen`, `lectura`).
- `manual-fuente/content/glosario-*.json`: términos del glosario, `{termino, definicion, slug}`.
- `manual-fuente/template.html`: diseño, estilos y JavaScript del sitio. El contenido se inyecta en `__DATA__`.
- `manual-fuente/web/`: `sw.js` (plantilla del service worker), `manifest.webmanifest`, `icon.svg` y `_headers` (cabeceras de caché).
- `manual-fuente/fonts/`: las fuentes en woff2 (Literata, Schibsted Grotesk, JetBrains Mono, Source Serif 4 y Atkinson Hyperlegible) (subconjunto latin de Google Fonts, licencia SIL OFL). Ya no se cargan desde Google.
- `manual-fuente/build.py`: arma el sitio y el archivo único. La lista `CHAPTERS` define capítulos, orden y numeración de los temas.
- `manual-fuente/GUIA_DE_ESTILO.md`: reglas de redacción. Léela antes de escribir o editar un tema.

## Generar el manual

```
cd manual-fuente
python3 build.py
cp dist/manual.html "../Manual AI-ML y Plataforma.html"
```

Requiere Python 3 y el paquete `markdown`. Genera `dist/web/` (para publicar) y `dist/manual.html` (archivo único, con fuentes e icono incrustados y sin service worker). El script informa temas faltantes, enlaces internos rotos (`#t/<slug>`) y palabras prohibidas. La salida debe terminar sin líneas que empiecen con `!`.

## Modo lector: página y ajustes de lectura

- Botón **Aa** (en móvil, en la barra superior; en escritorio, fijo arriba a la derecha, `.themefab`) abre el panel `#lectura`: un panel flotante en escritorio y tablet, y una hoja inferior a 560 px o menos.
- **Página**: papel, sepia, tinta y noche (`data-theme`); noche por defecto. Los colores son tokens en `:root` y en `:root[data-theme="…"]`. Los valores viejos `light` y `dark` se leen como papel y noche.
- **Ajustes**: brillo (40–100), luz cálida (0–100), tamaño (5 pasos, `--fs` en em), tipografía (`data-letra`: Literata, Source Serif 4, Atkinson Hyperlegible, Schibsted Grotesk), interlineado (`data-interlineado`, `--lh`) y márgenes (`data-margenes`, `--measure`). Solo cambian el texto de los temas (`article`).
- Brillo, luz cálida y grano del papel son capas fijas (`.veil`) que no reciben clics; el grano no se muestra en noche.
- Se guarda en localStorage (`manual-aiml-tema` para la página y `manual-aiml-lectura` para el resto). Un script en el `<head>` aplica todo antes de pintar. El respaldo (`#respaldo`) lleva `ajustes.tema` y `ajustes.lectura`.

## Publicar y caché

- Repositorio: github.com/NicoCroce/conceptos-fundamentales (público, rama `main`). `dist/` y el archivo único no se versionan: se generan. Cloudflare Pages se conecta al repo con directorio raíz `manual-fuente`, comando `python3 build.py` y salida `dist/web`; instala `requirements.txt` solo y cada push a `main` publica.
- Se publica el contenido de `manual-fuente/dist/web/` en cualquier hosting estático (Cloudflare Pages, Netlify, S3 + CloudFront, GitHub Pages). Funciona en la raíz o en una subcarpeta y requiere HTTPS, salvo en `localhost`.
- El service worker guarda todo en la primera visita (la página, fuentes, manifest e icono) y desde ahí responde desde la caché, con o sin conexión. Todas las vistas usan rutas con `#`, así que hay una sola página.
- Versión = hash de contenido, template, `web/` y fuentes. Si nada cambió, el build da la misma versión y nadie descarga nada. Si cambió, la versión nueva se instala en segundo plano y el lector ve el aviso «Hay una versión nueva del manual · Actualizar»; no se recarga sola para no cortar una lectura. La caché vieja se borra al activar.
- Cabeceras: `sw.js`, `index.html` y el manifest con `Cache-Control: no-cache`; las fuentes, `immutable`. `_headers` ya lo trae para Cloudflare Pages y Netlify; en otro hosting hay que configurarlo igual. Si se cambia una fuente, cambiarle el nombre al archivo.
- Las notas y el progreso se guardan por origen: los de la URL publicada y los del archivo local no se comparten (se pasan con exportar e importar).
- Probar en local: `.claude/launch.json` sirve `manual-fuente/dist/web` en el puerto 8765. El navegador integrado de la app de Claude no registra service workers; para probar el modo sin conexión hay que usar Chrome.

## Reglas del contenido

- Castellano neutro, sin voseo. Escrito para el equipo, no para una entrevista.
- Sin contenido de pagos: ni como tema ni como ejemplo. `build.py` lo verifica.
- Los ejemplos usan la empresa ficticia **Rumbo** (logística de última milla), descrita en la guía de estilo.
- Cada tema sigue el esqueleto: La idea central, Conceptos (con **Ejemplo:** y **Por qué importa:**), Casos prácticos (**Situación:** / **Qué se hace:**), Errores comunes y Para discutir en equipo.
- Conceptos explicados paso a paso, con ejemplos numéricos cuando se pueda. Precios y cifras de proveedores, como hipotéticos.
- El hilo conductor es el uso de modelos agénticos: cada tema nuevo debe conectar con cómo se construyen, operan o protegen sistemas con agentes y LLMs.

## Verificación antes de dar algo por terminado

1. `python3 build.py` sin advertencias.
2. Abrir el sitio (`dist/web/` servido en local) a ancho de escritorio y de teléfono (unos 400 px), en tema claro y oscuro: sin scroll horizontal ni errores en la consola.
3. Si cambió el JavaScript, probar a mano la función tocada (buscador, glosario, marcar como leído, notas y resaltados, panel Aa de lectura, perfiles, compartir e importar).
4. Si cambió `web/` o la carga de recursos: en Chrome, confirmar que el service worker queda activo, que el manual carga con el servidor apagado y que una versión nueva muestra «Actualizar».

## Notas y resaltados (implementado)

- Todo vive en `template.html`. IndexedDB `manual-aiml` (v1) con dos almacenes: `notas` (keyPath `id`, índice `slug`) y `ajustes` (clave/valor; `leidos` guarda el progreso).
- Cada nota guarda `texto`, `prefijo` y `sufijo` (40 caracteres de contexto) y `posicion`. Al abrir un tema se busca el texto ignorando espacios; si hay varias ocurrencias gana la de mejor contexto. Si no aparece, `sinUbicar: true`.
- El contenido del tema va dentro de `#tcontent`; los resaltados son `<mark class="hl c-<color>" data-nota="<id>">`.
- Rutas: `#notas` (vista Mis notas), `#respaldo` (Pasar a otro dispositivo) y `#<slug>/nota/<id>` (abre el tema y lleva al resaltado).
- Progreso de lectura: la fuente de verdad es IndexedDB; localStorage queda como copia y respaldo, y se migra la primera vez.
- Sin IndexedDB las notas viven en memoria y se avisa.

## Perfiles (implementado)

- `PERFILES` en `build.py` define los recorridos IA, Backend, Frontend, Plataforma, Diseño (UX/UI) y Gestión; «Todo» es la ausencia de filtro. El build avisa si un perfil nombra un tema inexistente.
- El perfil filtra el índice lateral, la portada (cifras y capítulos) y el orden de «Anterior / Siguiente». El buscador siempre busca en todo el manual. Se guarda en localStorage (`manual-aiml-perfil`).
- Al sumar un tema, decidir a qué perfiles pertenece.

## Pasar a otro dispositivo (implementado)

- Vista `#respaldo`: un archivo JSON (`formato: "manual-aiml-respaldo"`, versión 2) con temas leídos, notas y ajustes (perfil y tema).
- «Compartir» usa el menú nativo (`navigator.share` con archivo; prueba `.json` y, si el sistema no lo acepta, `.txt`). Si no hay soporte, descarga el archivo.
- «Importar archivo» suma sin borrar: une los temas leídos, conserva la nota editada más recientemente y aplica perfil y tema. Acepta también las exportaciones viejas que solo traían notas.

## Capítulos (14)

LLMs · Agentes · Arquitectura y backend · Diseño de software y patrones · Machine Learning · Observabilidad · Cloud e infraestructura · Frontend y web · UX, UI y diseño · Seguridad · Metodologías y gestión · Análisis, decisiones y documentos · Comunicación y feedback · Lenguajes y frameworks. La lista completa de temas está en `CHAPTERS` (`build.py`) y en la guía de estilo.

- Agentes incluye `arnes-agentes` (el arnés: bucle, herramientas, contexto, permisos, hooks y evaluación) y `meta-arnes` (arneses que optimizan u orquestan otros arneses, con el paper Meta-Harness de 2026).
- Seguridad reúne autenticación, secretos, frontend, Cloudflare y agentes, y suma fundamentos y modelado de amenazas, APIs, cadena de suministro y privacidad.
- Diseño de software y patrones: SOLID, patrones creacionales, estructurales y de comportamiento, inyección de dependencias, DDD táctico, Repository y Unit of Work, CQRS y Event Sourcing, testing y dobles de prueba. El DDD estratégico sigue en Arquitectura y backend.
- Frontend y web suma componentización y eventos del DOM.
- UX, UI y diseño: fundamentos de UX y UI, investigación y usabilidad, heurísticas de Nielsen, leyes de UX y diseño visual, accesibilidad (WCAG 2.2) y UX de interfaces con agentes. Como «tarjeta» es palabra prohibida, las cards de UI se llaman «fichas».
- Metodologías y gestión: Agile/Scrum/Kanban, priorización (Eisenhower, RICE, WSJF), estimación, triángulo de hierro, EDT/WBS, planificación con Gantt, RACI/RASI, riesgos, métricas DORA, SDD y ODD.
- Análisis, decisiones y documentos: objetivos SMART, ROI, Pareto, 5 porqués, brainstorming y mapas mentales, postmortem y premortem, PRD y RFC.
- Comunicación y feedback: comunicación asertiva, feedback con SBI y feedback en revisiones de código y diseño.
- `recorrido-punta-a-punta` (capítulo 8) sigue una consulta al asistente de Rumbo de punta a punta y enlaza los temas de cada tramo.

## Gráficos

Los bloques de código `gantt`, `cuadrante`, `calor`, `barras`, `triangulo`, `roles`, `pareto`, `porques` y `arbol` se convierten en figuras HTML/SVG en `build.py` (`FIGURES`); los estilos (`.gantt`, `.fig`, `.q-*`, `.hm-*`, `.bar-*`, `.tri-*`, `.roles`, `.pareto`, `.why`, `.tree`) están en el template y usan los tokens de color, así que funcionan en claro y oscuro. El formato de cada uno está en la guía de estilo (sección «Gráficos»). Una línea inválida aparece como advertencia del build.

## Pendientes

Ninguno por ahora.
