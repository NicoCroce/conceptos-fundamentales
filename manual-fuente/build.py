#!/usr/bin/env python3
"""Genera el sitio del manual (un solo HTML) a partir de content/*.md y content/glosario-*.json."""
import json, re, sys, unicodedata, glob, html as htmllib, hashlib, shutil, base64, datetime
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
OUT = ROOT / "dist" / "manual.html"   # archivo único (doble clic, sin conexión, sin service worker)
SITE = ROOT / "dist" / "web"          # sitio para publicar en una URL
WEB = ROOT / "web"                    # sw.js, manifest, icono y cabeceras
FONTS_DIR = ROOT / "fonts"

# Fuentes variables (subconjunto latin de Google Fonts, licencia SIL OFL): archivo, familia, estilo, rango de pesos.
FONTS = [
    ("literata.woff2", "Literata", "normal", "200 900"),
    ("schibsted-grotesk.woff2", "Schibsted Grotesk", "normal", "400 900"),
    ("literata-italic.woff2", "Literata", "italic", "200 900"),
    ("jetbrains-mono.woff2", "JetBrains Mono", "normal", "100 800"),
]


def fonts_css(src):
    return "\n".join(
        f'@font-face {{ font-family: "{fam}"; font-style: {style}; font-weight: {w}; font-display: swap; src: url("{src(f)}") format("woff2"); }}'
        for f, fam, style, w in FONTS if (FONTS_DIR / f).exists())

CHAPTERS = [
    {"n": 1, "titulo": "LLMs",
     "descripcion": "Cómo funcionan los modelos de lenguaje y cómo se eligen, combinan, adaptan y evalúan: prompts, RAG, embeddings, varios modelos y multimodalidad.",
     "topics": ["fundamentos-llms", "prompt-engineering", "rag", "embeddings", "multimodelo", "multimodal", "adaptar-modelos", "evaluacion-llms"]},
    {"n": 2, "titulo": "Agentes",
     "descripcion": "Cómo se construyen, conectan y operan los sistemas con agentes: herramientas, orquestación, MCP, contexto y memoria, subagentes y producción.",
     "topics": ["agentes", "langgraph", "mcp", "contexto-memoria", "subagentes", "llms-produccion"]},
    {"n": 3, "titulo": "Arquitectura y backend",
     "descripcion": "Las bases para diseñar servicios rápidos y confiables: decisiones de diseño, capas y arquitectura hexagonal, DDD, sistemas distribuidos, resiliencia, APIs, eventos y datos.",
     "topics": ["revision-arquitectura", "arquitectura-capas-hexagonal", "ddd", "sistemas-distribuidos", "latencia-disponibilidad", "resiliencia", "grpc-rest", "event-streaming", "bases-de-datos"]},
    {"n": 4, "titulo": "Diseño de software y patrones",
     "descripcion": "Cómo se escribe código que se puede cambiar: principios SOLID, patrones de diseño, inyección de dependencias, DDD táctico, Repository, CQRS y testing, aplicados a servicios con agentes.",
     "topics": ["principios-solid", "patrones-creacionales", "patrones-estructurales", "patrones-comportamiento", "inyeccion-dependencias", "ddd-tactico", "patron-repository", "cqrs-event-sourcing", "testing-dobles"]},
    {"n": 5, "titulo": "Machine Learning",
     "descripcion": "Del entrenamiento a producción: fundamentos, modelos tabulares, ciclo de vida, serving, monitoreo y features.",
     "topics": ["fundamentos-ml", "xgboost", "ciclo-vida-modelos", "serving", "monitoreo-modelos", "feature-stores", "mlflow", "pytorch-tensorflow"]},
    {"n": 6, "titulo": "Observabilidad",
     "descripcion": "Cómo saber qué pasa en producción y cómo responder cuando algo falla: guardias, trazas, métricas y logs.",
     "topics": ["on-call", "opentelemetry", "prometheus-grafana", "logging"]},
    {"n": 7, "titulo": "Cloud e infraestructura",
     "descripcion": "AWS, cómputo, contenedores, colas y serverless, datos, IA gestionada, infraestructura como código, CI/CD, despliegues on-prem y costos.",
     "topics": ["aws", "ec2", "contenedores", "colas-serverless", "rds-aurora", "s3", "bedrock-sagemaker", "terraform", "ci-cd", "hibrido-on-prem", "finops"]},
    {"n": 8, "titulo": "Frontend y web",
     "descripcion": "De la acción del usuario en el navegador a la respuesta del agente: HTTP, arquitectura de frontend, componentización, eventos, web components, design systems, diseño responsive y PWA.",
     "topics": ["http", "arquitectura-frontend", "componentizacion", "eventos-dom", "web-components", "design-systems", "responsive", "pwa", "recorrido-punta-a-punta"]},
    {"n": 9, "titulo": "UX, UI y diseño",
     "descripcion": "Cómo se diseñan interfaces que la gente entiende y puede usar: fundamentos de UX y UI, investigación y usabilidad, heurísticas de Nielsen, leyes de UX y diseño visual, accesibilidad y la experiencia de usar un agente.",
     "topics": ["ux-ui-fundamentos", "investigacion-usabilidad", "heuristicas-nielsen", "leyes-ux-diseno-visual", "accesibilidad", "ux-agentes"]},
    {"n": 10, "titulo": "Seguridad",
     "descripcion": "Modelado de amenazas, identidad, secretos, APIs, frontend, perímetro, agentes, cadena de suministro y privacidad: cómo se protege un sistema con LLMs de punta a punta.",
     "topics": ["fundamentos-seguridad", "autenticacion", "secretos", "seguridad-apis", "seguridad-frontend", "cloudflare", "seguridad-agentes", "cadena-suministro", "privacidad-datos"]},
    {"n": 11, "titulo": "Metodologías y gestión",
     "descripcion": "Cómo se organiza el trabajo: Agile, Scrum y Kanban, priorización, estimación, triángulo de hierro, EDT/WBS, planificación con Gantt, matrices RACI y RASI, riesgos, métricas de entrega y desarrollo con agentes (SDD y ODD).",
     "topics": ["agile-scrum", "priorizacion", "estimacion", "triangulo-hierro", "wbs-edt", "planificacion-gantt", "raci-rasi", "riesgos", "metricas-entrega", "sdd", "odd"]},
    {"n": 12, "titulo": "Análisis, decisiones y documentos",
     "descripcion": "Herramientas para pensar y decidir con datos: objetivos SMART, ROI, Pareto, 5 porqués, brainstorming y mapas mentales, postmortem y premortem, y los documentos PRD y RFC.",
     "topics": ["objetivos-smart", "roi", "pareto", "cinco-porques", "brainstorming-mapas-mentales", "postmortem-premortem", "prd", "rfc"]},
    {"n": 13, "titulo": "Comunicación y feedback",
     "descripcion": "Cómo nos hablamos en el equipo: comunicación asertiva, feedback con el modelo SBI y comentarios útiles en revisiones de código y diseño, también cuando el trabajo lo hace un agente.",
     "topics": ["comunicacion-asertiva", "feedback-sbi", "feedback-revisiones"]},
    {"n": 14, "titulo": "Lenguajes y frameworks",
     "descripcion": "Go para los servicios de baja latencia, Python para ML, TypeScript y React en el frontend, y Kotlin en el backend sobre la JVM.",
     "topics": ["go", "python", "typescript", "react", "kotlin"]},
]

# Perfiles: filtros del índice y de la portada. Cada perfil es un recorrido sugerido; el orden y la
# numeración siguen siendo los de CHAPTERS. "Todo" no se declara: es la ausencia de filtro.
PERFILES = [
    {"id": "ia", "nombre": "Inteligencia artificial", "corto": "IA",
     "descripcion": "LLMs, agentes y machine learning de punta a punta, con lo justo de infraestructura para llevarlos a producción.",
     "topics": ["fundamentos-llms", "prompt-engineering", "rag", "embeddings", "multimodelo", "multimodal", "adaptar-modelos", "evaluacion-llms",
                "agentes", "langgraph", "mcp", "contexto-memoria", "subagentes", "seguridad-agentes", "sdd", "odd", "llms-produccion",
                "fundamentos-ml", "xgboost", "ciclo-vida-modelos", "serving", "monitoreo-modelos", "feature-stores", "mlflow", "pytorch-tensorflow",
                "bedrock-sagemaker", "finops", "python",
                "fundamentos-seguridad", "privacidad-datos", "priorizacion", "riesgos",
                "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones",
                "cinco-porques", "postmortem-premortem", "rfc", "prd", "objetivos-smart", "roi",
                "patrones-estructurales", "patrones-comportamiento", "inyeccion-dependencias", "testing-dobles",
                "ux-agentes"]},
    {"id": "back", "nombre": "Backend", "corto": "Backend",
     "descripcion": "Diseño de servicios, datos, APIs y eventos, cómo exponer herramientas a un agente y cómo operarlo en producción.",
     "topics": ["fundamentos-llms", "agentes", "mcp", "seguridad-agentes", "llms-produccion",
                "revision-arquitectura", "arquitectura-capas-hexagonal", "ddd", "sistemas-distribuidos", "latencia-disponibilidad", "resiliencia",
                "grpc-rest", "event-streaming", "bases-de-datos", "on-call", "opentelemetry", "logging",
                "contenedores", "colas-serverless", "rds-aurora", "secretos", "ci-cd",
                "http", "autenticacion", "recorrido-punta-a-punta", "go", "python", "typescript", "kotlin",
                "fundamentos-seguridad", "seguridad-apis", "cadena-suministro", "privacidad-datos", "agile-scrum", "priorizacion", "estimacion", "sdd",
                "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones",
                "cinco-porques", "postmortem-premortem", "rfc",
                "principios-solid", "patrones-creacionales", "patrones-estructurales", "patrones-comportamiento", "inyeccion-dependencias", "ddd-tactico", "patron-repository", "cqrs-event-sourcing", "testing-dobles"]},
    {"id": "front", "nombre": "Frontend", "corto": "Frontend",
     "descripcion": "Del navegador al agente: HTTP y streaming, arquitectura de frontend, componentes, design systems, PWA, autenticación y seguridad web.",
     "topics": ["fundamentos-llms", "prompt-engineering", "agentes", "seguridad-agentes",
                "latencia-disponibilidad", "grpc-rest", "arquitectura-capas-hexagonal",
                "http", "arquitectura-frontend", "web-components", "design-systems", "responsive", "pwa", "autenticacion",
                "seguridad-frontend", "cloudflare", "recorrido-punta-a-punta", "ci-cd", "typescript", "react",
                "fundamentos-seguridad", "seguridad-apis", "agile-scrum", "priorizacion", "estimacion", "sdd",
                "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones",
                "cinco-porques", "postmortem-premortem", "rfc", "prd",
                "principios-solid", "patrones-creacionales", "patrones-estructurales", "patrones-comportamiento", "inyeccion-dependencias", "testing-dobles", "componentizacion", "eventos-dom",
                "ux-ui-fundamentos", "heuristicas-nielsen", "leyes-ux-diseno-visual", "accesibilidad", "ux-agentes"]},
    {"id": "plataforma", "nombre": "Plataforma e infraestructura", "corto": "Plataforma",
     "descripcion": "Cloud, contenedores, CI/CD, observabilidad, costos y protección perimetral, incluida la operación de LLMs y agentes.",
     "topics": ["fundamentos-llms", "llms-produccion", "seguridad-agentes", "sistemas-distribuidos", "latencia-disponibilidad", "resiliencia",
                "on-call", "opentelemetry", "prometheus-grafana", "logging",
                "aws", "ec2", "contenedores", "colas-serverless", "rds-aurora", "s3", "bedrock-sagemaker", "terraform", "ci-cd", "secretos",
                "hibrido-on-prem", "finops", "http", "autenticacion", "cloudflare", "go",
                "fundamentos-seguridad", "seguridad-apis", "cadena-suministro", "privacidad-datos", "riesgos", "metricas-entrega",
                "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones",
                "cinco-porques", "postmortem-premortem", "rfc", "pareto",
                "testing-dobles"]},
    {"id": "diseno", "nombre": "Diseño UX/UI", "corto": "Diseño",
     "descripcion": "Para diseñadoras y diseñadores: UX y UI, investigación, heurísticas, accesibilidad, design systems y lo necesario de frontend, LLMs y agentes para diseñar productos con asistentes.",
     "topics": ["fundamentos-llms", "prompt-engineering", "agentes", "seguridad-agentes", "evaluacion-llms",
                "http", "arquitectura-frontend", "componentizacion", "web-components", "design-systems", "responsive", "pwa", "recorrido-punta-a-punta",
                "ux-ui-fundamentos", "investigacion-usabilidad", "heuristicas-nielsen", "leyes-ux-diseno-visual", "accesibilidad", "ux-agentes",
                "privacidad-datos", "agile-scrum", "priorizacion", "estimacion",
                "objetivos-smart", "brainstorming-mapas-mentales", "prd", "postmortem-premortem",
                "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones"]},
    {"id": "gestion", "nombre": "Gestión y liderazgo técnico", "corto": "Gestión",
     "descripcion": "Metodologías, priorización, estimación, planificación, riesgos y métricas, con la base técnica necesaria para conversar y decidir sobre LLMs, agentes, arquitectura y seguridad.",
     "topics": ["fundamentos-llms", "agentes", "llms-produccion", "evaluacion-llms", "revision-arquitectura", "on-call", "finops",
                "fundamentos-seguridad", "seguridad-agentes", "privacidad-datos",
                "agile-scrum", "priorizacion", "estimacion", "planificacion-gantt", "riesgos", "metricas-entrega", "sdd", "odd",
                "triangulo-hierro", "raci-rasi", "comunicacion-asertiva", "feedback-sbi", "feedback-revisiones",
                "wbs-edt", "objetivos-smart", "roi", "pareto", "cinco-porques", "brainstorming-mapas-mentales", "postmortem-premortem", "prd", "rfc",
                "principios-solid", "testing-dobles",
                "ux-ui-fundamentos", "investigacion-usabilidad", "heuristicas-nielsen", "ux-agentes"]},
]
SECTION_KEYS = {
    "la idea central": "idea",
    "conceptos": "conceptos",
    "casos practicos": "casos",
    "errores comunes": "errores",
    "para discutir en equipo": "discutir",
}

FORBIDDEN = re.compile(r"\b(pagos?|tarjetas?|psps?|pci|adquirente|emisor|contracargos?|fraude|cobros?|bancos?)\b", re.I)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def slugify(s):
    s = strip_accents(htmllib.unescape(re.sub(r"<[^>]+>", "", s))).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:60] or "s"


def parse(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.S)
    if not m:
        raise SystemExit(f"Sin front matter: {path.name}")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, m.group(2)


LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s")


def normalize(body):
    """Ajusta markdown estilo GFM a lo que espera python-markdown (fuera de bloques de código)."""
    out, fence = [], False
    for line in body.split("\n"):
        if line.lstrip().startswith("```"):
            if not fence and out and out[-1].strip():
                out.append("")
            fence = not fence
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        # Sublistas con 2-3 espacios -> 4
        m = re.match(r"^( {2,3})([-*+]|\d+\.)\s", line)
        if m:
            line = "    " + line[len(m.group(1)):]
        prev = out[-1] if out else ""
        starts_list = bool(LIST_RE.match(line)) and not line.startswith("    ")
        starts_table = line.startswith("|")
        if prev.strip():
            if starts_list and not LIST_RE.match(prev) and not prev.startswith("    "):
                out.append("")
            elif starts_table and not prev.startswith("|"):
                out.append("")
            # Líneas consecutivas que empiezan con **Etiqueta:** -> párrafos separados
            elif line.startswith("**") and re.match(r"^\*\*[^*]{2,40}:\*\*", line) and not LIST_RE.match(prev) and not prev.startswith("|"):
                out.append("")
        out.append(line)
    return "\n".join(out)


def gantt_html(src, problems):
    """Convierte un bloque ```gantt en una figura HTML. Formato: 'titulo:', 'unidad:' y
    una línea por tarea 'Nombre | inicio | duración | critica' (duración 0 = hito)."""
    titulo, unidad, rows = "", "semana", []
    for line in src.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("titulo:") or low.startswith("título:"):
            titulo = line.split(":", 1)[1].strip(); continue
        if low.startswith("unidad:"):
            unidad = line.split(":", 1)[1].strip(); continue
        parts = [x.strip() for x in line.split("|")]
        try:
            ini, dur = float(parts[1]), float(parts[2])
        except (IndexError, ValueError):
            problems.append(f"gantt: línea inválida '{line}'"); continue
        rows.append((parts[0], ini, dur, len(parts) > 3 and parts[3].lower().startswith("cr")))
    if not rows:
        return ""
    n = max(1, int(-(-max(i + d for _, i, d, _ in rows) // 1)))
    step = 1 if n <= 16 else 2
    esc = htmllib.escape
    fmt = lambda x: ("%g" % x)
    h = ['<figure class="gantt" style="--n:%d">' % n]
    if titulo:
        h.append("<figcaption>%s</figcaption>" % esc(titulo))
    h.append('<div class="g-row g-head"><span class="g-name">%s</span><div class="g-track">' % esc(unidad.capitalize()))
    for k in range(0, n, step):
        h.append('<b style="--s:%d">%d</b>' % (k, k + 1))
    h.append("</div></div>")
    for name, ini, dur, crit in rows:
        cls = " crit" if crit else ""
        if dur == 0:
            bar = '<i class="g-ms%s" style="--s:%s" title="%s"></i>' % (cls, fmt(ini), esc(name))
        else:
            bar = '<i class="g-bar%s" style="--s:%s;--d:%s" title="%s: %s a %s"></i>' % (cls, fmt(ini), fmt(dur), esc(name), fmt(ini + 1), fmt(ini + dur))
        h.append('<div class="g-row%s"><span class="g-name">%s</span><div class="g-track">%s</div></div>' % (cls, esc(name), bar))
    leg = "Cada columna: 1 %s." % esc(unidad.lower())
    if any(r[3] for r in rows):
        leg += ' <span class="g-key"></span> Ruta crítica.'
    if any(r[2] == 0 for r in rows):
        leg += ' <span class="g-key ms"></span> Hito.'
    h.append('<p class="g-leg">%s</p></figure>' % leg)
    return "".join(h)


# ---- Gráficos: bloques ```cuadrante, ```calor, ```barras, ```triangulo y ```roles ----
def _fig_lines(src):
    """Devuelve (titulo, campos clave: valor, filas con '|')."""
    titulo, keys, rows = "", {}, []
    for line in src.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^([a-záéíóúñ-]+):\s*(.*)$", line, re.I)
        if m and "|" not in m.group(1):
            k = strip_accents(m.group(1)).lower()
            if k == "titulo":
                titulo = m.group(2).strip()
            else:
                keys[k] = m.group(2).strip()
            continue
        rows.append([x.strip() for x in line.split("|")])
    return titulo, keys, rows


def _fig(kind, titulo, inner, leg=""):
    e = htmllib.escape
    return ('<figure class="fig fig-%s">' % kind + ("<figcaption>%s</figcaption>" % e(titulo) if titulo else "") + inner +
            ('<p class="fig-leg">%s</p>' % leg if leg else "") + "</figure>")


def cuadrante_html(src, problems):
    e = htmllib.escape
    titulo, k, _ = _fig_lines(src)
    def axis(name):
        v = [x.strip() for x in k.get(name, "").split("|")]
        return (v + ["", ""])[:2]
    xl, xh = axis("eje-x")
    yl, yh = axis("eje-y")
    cells = []
    for pos in ["arriba-izquierda", "arriba-derecha", "abajo-izquierda", "abajo-derecha"]:
        if pos not in k:
            problems.append(f"cuadrante: falta '{pos}'")
        parts = k.get(pos, "").split("|", 1)
        head = parts[0].strip()
        items = [x.strip() for x in parts[1].split(";")] if len(parts) > 1 else []
        cells.append('<div class="q q-%s"><b>%s</b>%s</div>' % (pos, e(head), "".join("<span>%s</span>" % e(i) for i in items if i)))
    # El eje Y está rotado 180°: el primer texto queda abajo (extremo bajo).
    inner = ('<div class="q-wrap"><div class="q-y"><span>%s</span><span>%s</span></div><div class="q-grid">%s</div>'
             '<div class="q-x"><span>%s</span><span>%s</span></div></div>') % (e(yl), e(yh), "".join(cells), e(xl), e(xh))
    return _fig("cuadrante", titulo, inner)


def calor_html(src, problems):
    e = htmllib.escape
    titulo, k, rows = _fig_lines(src)
    cell = {}
    for r in rows:
        try:
            p, i = int(r[1]), int(r[2])
            assert 1 <= p <= 5 and 1 <= i <= 5
        except Exception:
            problems.append(f"calor: línea inválida '{' | '.join(r)}'"); continue
        cell.setdefault((p, i), []).append(r[0])
    def band(x):
        return "b1" if x <= 4 else "b2" if x <= 9 else "b3" if x <= 16 else "b4"
    # Si la etiqueta empieza con un código corto ("R1 Alucinaciones"), la celda muestra el código
    # y la descripción va en una lista debajo: en el teléfono las celdas son angostas.
    def short(l):
        parts = l.split(" ", 1)
        return parts[0] if len(parts) == 2 and len(parts[0]) <= 4 else l
    h = ['<div class="hm"><div class="hm-ylab">%s</div><div class="hm-grid">' % e(k.get("eje-y", "Probabilidad"))]
    for p in range(5, 0, -1):
        h.append('<span class="hm-n">%d</span>' % p)
        for i in range(1, 6):
            labels = cell.get((p, i), [])
            h.append('<div class="hm-c %s" title="Probabilidad %d × impacto %d = %d">%s</div>' % (
                band(p * i), p, i, p * i, "".join('<span title="%s">%s</span>' % (e(l), e(short(l))) for l in labels)))
    h.append('<span></span>' + "".join('<span class="hm-n">%d</span>' % i for i in range(1, 6)))
    h.append('</div><div class="hm-xlab">%s</div></div>' % e(k.get("eje-x", "Impacto")))
    coded = [r for r in rows if len(r) >= 3 and short(r[0]) != r[0]]
    if coded:
        h.append('<ul class="hm-list">%s</ul>' % "".join(
            "<li><b>%s</b> %s <span>%s × %s</span></li>" % (e(short(r[0])), e(r[0].split(" ", 1)[1]), e(r[1]), e(r[2])) for r in coded))
    leg = " ".join('<span class="nw"><span class="hm-k %s"></span> %s</span>' % x for x in
                   [("b1", "Bajo (1-4)"), ("b2", "Medio (5-9)"), ("b3", "Alto (10-16)"), ("b4", "Crítico (20-25)")])
    return _fig("calor", titulo, "".join(h), leg)


def barras_html(src, problems):
    e = htmllib.escape
    titulo, k, rows = _fig_lines(src)
    vals = []
    for r in rows:
        try:
            vals.append((r[0], float(r[1].replace(",", ".")), r[1]))
        except Exception:
            problems.append(f"barras: línea inválida '{' | '.join(r)}'")
    if not vals:
        return ""
    mx = max(v for _, v, _ in vals) or 1
    unidad = k.get("unidad", "")
    h = ['<div class="bars">']
    for name, v, raw in vals:
        h.append('<div class="bar-row"><span class="bar-name">%s</span><div class="bar-track"><i style="width:%.1f%%"></i></div>'
                 '<span class="bar-val">%s%s</span></div>' % (e(name), max(v, 0) / mx * 100, e(raw), (" " + e(unidad)) if unidad else ""))
    h.append("</div>")
    return _fig("barras", titulo, "".join(h))


def triangulo_html(src, problems):
    e = htmllib.escape
    titulo, k, _ = _fig_lines(src)
    def part(name):
        v = k.get(name, "").split("|", 1)
        return e(v[0].strip()), e(v[1].strip()) if len(v) > 1 else ""
    (a, a2), (l, l2), (r, r2), (c, c2) = part("arriba"), part("izquierda"), part("derecha"), part("centro")
    svg = ('<svg viewBox="-50 0 460 290" role="img" aria-label="%s">'
           '<polygon points="180,52 50,236 310,236" class="tri-shape"/>'
           '<circle cx="180" cy="52" r="6" class="tri-dot"/><circle cx="50" cy="236" r="6" class="tri-dot"/><circle cx="310" cy="236" r="6" class="tri-dot"/>'
           '<text x="180" y="22" class="tri-t">%s</text><text x="180" y="38" class="tri-s">%s</text>'
           '<text x="50" y="262" class="tri-t">%s</text><text x="50" y="278" class="tri-s">%s</text>'
           '<text x="310" y="262" class="tri-t">%s</text><text x="310" y="278" class="tri-s">%s</text>'
           '<text x="180" y="170" class="tri-c">%s</text><text x="180" y="188" class="tri-s">%s</text></svg>') % (
        e(titulo or "Triángulo"), a, a2, l, l2, r, r2, c, c2)
    return _fig("triangulo", titulo, svg)


ROLE_NAMES = {"R": "Responsable", "A": "Aprobador / rinde cuentas", "S": "Soporte", "C": "Consultado", "I": "Informado"}


def roles_html(src, problems):
    e = htmllib.escape
    titulo, k, rows = _fig_lines(src)
    cols = [x.strip() for x in k.get("columnas", "").split("|") if x.strip()]
    if not cols:
        problems.append("roles: falta 'columnas:'")
    used = set()
    h = ['<div class="roles-wrap"><table class="roles"><thead><tr><th>Actividad</th>%s</tr></thead><tbody>' % "".join("<th>%s</th>" % e(c) for c in cols)]
    for r in rows:
        if len(r) - 1 != len(cols):
            problems.append(f"roles: '{r[0]}' tiene {len(r) - 1} celdas y hay {len(cols)} columnas")
        tds = []
        for v in r[1:]:
            letters = [x for x in re.split(r"[/,\s]+", v.upper()) if x]
            used.update(letters)
            tds.append("<td>%s</td>" % "".join('<span class="rl rl-%s">%s</span>' % (x.lower() if x in ROLE_NAMES else "x", e(x)) for x in letters))
        h.append("<tr><th>%s</th>%s</tr>" % (e(r[0]), "".join(tds)))
    h.append("</tbody></table></div>")
    leg = " ".join('<span class="rl rl-%s">%s</span> %s' % (x.lower(), x, ROLE_NAMES[x]) for x in "RASCI" if x in used)
    return _fig("roles", titulo, "".join(h), leg)


FIGURES = {"gantt": gantt_html, "cuadrante": cuadrante_html, "calor": calor_html, "barras": barras_html,
           "triangulo": triangulo_html, "roles": roles_html}


def pareto_html(src, problems):
    e = htmllib.escape
    titulo, k, rows = _fig_lines(src)
    vals = []
    for r in rows:
        try:
            vals.append((r[0], float(r[1].replace(",", ".")), r[1]))
        except Exception:
            problems.append(f"pareto: línea inválida '{' | '.join(r)}'")
    if not vals:
        return ""
    vals.sort(key=lambda x: -x[1])
    total = sum(v for _, v, _ in vals) or 1
    mx = vals[0][1] or 1
    unidad = k.get("unidad", "")
    acc, prev, h = 0.0, 0.0, ['<div class="bars pareto">']
    for name, v, raw in vals:
        acc += v
        vital = prev < 80          # entra mientras el acumulado anterior no llegó al 80 %
        prev = acc / total * 100
        h.append('<div class="bar-row%s"><span class="bar-name">%s</span><div class="bar-track"><i style="width:%.1f%%"></i></div>'
                 '<span class="bar-val">%s%s · <b>%d %%</b></span></div>' % (
                     " vital" if vital else "", e(name), v / mx * 100, e(raw), (" " + e(unidad)) if unidad else "", round(prev)))
    h.append("</div>")
    leg = '<span class="nw"><span class="pk vital"></span> Pocas causas que suman hasta el 80 %</span> <span class="nw"><span class="pk"></span> Resto</span> <span class="nw">Porcentaje = acumulado</span>'
    return _fig("pareto", titulo, "".join(h), leg)


def porques_html(src, problems):
    e = htmllib.escape
    titulo, k, rows = _fig_lines(src)
    whys = [" | ".join(r) for r in rows]
    if not k.get("problema"):
        problems.append("porques: falta 'problema:'")
    h = ['<ol class="why">', '<li class="why-p"><small>Problema</small>%s</li>' % e(k.get("problema", ""))]
    for i, w in enumerate(whys, 1):
        h.append('<li><small>¿Por qué? %d</small>%s</li>' % (i, e(w)))
    if k.get("causa"):
        h.append('<li class="why-c"><small>Causa raíz</small>%s</li>' % e(k["causa"]))
    if k.get("accion"):
        h.append('<li class="why-a"><small>Acción</small>%s</li>' % e(k["accion"]))
    h.append("</ol>")
    return _fig("porques", titulo, "".join(h))


def arbol_html(src, problems):
    e = htmllib.escape
    titulo, k, _ = _fig_lines(src)
    root, nodes = None, []
    for line in src.strip().splitlines():
        line = line.strip()
        if not line or re.match(r"^(titulo|título):", line, re.I):
            continue
        m = re.match(r"^(-+)\s*(.+)$", line)
        if m:
            nodes.append((len(m.group(1)), m.group(2).strip()))
        elif root is None:
            root = line
        else:
            problems.append(f"arbol: línea sin guiones fuera de la raíz '{line}'")
    if root is None:
        problems.append("arbol: falta la raíz"); return ""
    # Lista anidada a partir de los niveles
    out, depth, branch = ['<div class="tree"><div class="tree-root">%s</div><ul>' % e(root)], 1, -1
    for i, (lvl, text) in enumerate(nodes):
        if lvl > depth + 1 or (i == 0 and lvl != 1):
            problems.append(f"arbol: salto de nivel en '{text}'"); lvl = 1 if i == 0 else depth + 1
        if i == 0:
            pass
        elif lvl > depth:
            out.append("<ul>")
        else:
            out.append("</li>")
            while depth > lvl:
                out.append("</ul></li>"); depth -= 1
        depth = lvl
        if lvl == 1:
            branch += 1
        out.append('<li class="t%d br%d"><span>%s</span>' % (lvl, branch % 6, e(text)))
    out.append("</li>")
    while depth > 1:
        out.append("</ul></li>"); depth -= 1
    out.append("</ul></div>")
    return _fig("arbol", titulo, "".join(out))


FIGURES.update({"pareto": pareto_html, "porques": porques_html, "arbol": arbol_html})


def render(slug, body, valid):
    problems = []
    body = normalize(body)
    # Bloques ```gantt -> figura (se insertan después de markdown para que no los toque)
    figs = []
    def take_fig(mm):
        figs.append(FIGURES[mm.group(1)](mm.group(2), problems))
        return f"\n\nFIGURA{len(figs) - 1}X\n\n"
    body = re.sub(r"^```(%s)[ \t]*\n(.*?)^```[ \t]*$" % "|".join(FIGURES), take_fig, body, flags=re.S | re.M)
    # Referencias cruzadas #t/slug -> #slug
    def fix_link(mm):
        target = mm.group(1)
        if target not in valid:
            problems.append(f"enlace a tema inexistente: {target}")
        return f"(#{target})"
    body = re.sub(r"\(#t/([a-z0-9-]+)\)", fix_link, body)
    # Quita un H1 si lo hubiera (el título viene del front matter)
    body = re.sub(r"^# .*\n", "", body, count=1)

    h = markdown.markdown(body, extensions=["tables", "fenced_code", "sane_lists"], output_format="html5")
    for k, fig in enumerate(figs):
        h = h.replace(f"<p>FIGURA{k}X</p>", fig)

    toc, used = [], set()
    def add_id(mm):
        level, inner = mm.group(1), mm.group(2)
        base = f"{slug}--{slugify(inner)}"
        hid, i = base, 2
        while hid in used:
            hid, i = f"{base}-{i}", i + 1
        used.add(hid)
        toc.append({"id": hid, "text": htmllib.unescape(re.sub(r"<[^>]+>", "", inner)), "level": int(level)})
        return f'<h{level} id="{hid}">{inner}</h{level}>'
    h = re.sub(r"<h([23])>(.*?)</h\1>", add_id, h)

    # Callouts dentro de conceptos
    # También variantes como "**Ejemplo de dimensionamiento:**"
    h = re.sub(r"<p><strong>(Ejemplo[^<]{0,60}:)</strong>", r'<p class="co co-ej"><strong>\1</strong>', h)
    h = h.replace("<p><strong>Por qué importa:</strong>", '<p class="co co-pq"><strong>Por qué importa:</strong>')
    # Tablas con desplazamiento propio
    # Solo las tablas de markdown (sin clase); las de los gráficos ya traen su contenedor.
    h = re.sub(r"<table>(.*?)</table>", r'<div class="tw"><table>\1</table></div>', h, flags=re.S)

    # Envolver cada H2 en una sección con clave
    parts = re.split(r'(?=<h2 id=")', h)
    out = []
    for part in parts:
        mm = re.match(r'<h2 id="[^"]+">(.*?)</h2>', part)
        if not mm:
            out.append(part)
            continue
        key = SECTION_KEYS.get(strip_accents(re.sub(r"<[^>]+>", "", mm.group(1))).lower().strip(), "otra")
        if key == "casos":
            sub = re.split(r'(?=<h3 id=")', part)
            part = sub[0] + "".join(f'<div class="caso">{s}</div>' for s in sub[1:])
        out.append(f'<section class="sec sec-{key}">{part}</section>')
    h = "".join(out)

    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", h))
    text = re.sub(r"\s+", " ", text).strip()
    return h, toc, text, problems


def main():
    valid = {s for c in CHAPTERS for s in c["topics"]}
    topics, problems, words = {}, [], 0
    for c in CHAPTERS:
        for i, slug in enumerate(c["topics"], 1):
            path = CONTENT / f"{slug}.md"
            if not path.exists():
                problems.append(f"falta {slug}.md")
                continue
            meta, body = parse(path)
            if meta.get("slug") != slug:
                problems.append(f"{slug}: slug del front matter = {meta.get('slug')}")
            for hit in FORBIDDEN.finditer(body + " " + meta.get("resumen", "")):
                problems.append(f"{slug}: palabra prohibida '{hit.group(0)}'")
            h, toc, text, probs = render(slug, body, valid)
            problems += [f"{slug}: {p}" for p in probs]
            words += len(text.split())
            topics[slug] = {
                "slug": slug, "titulo": meta.get("titulo", slug), "resumen": meta.get("resumen", ""),
                "lectura": int(re.sub(r"\D", "", meta.get("lectura", "10")) or 10),
                "cap": c["n"], "num": f"{c['n']}.{i}", "html": h, "toc": toc, "text": text,
            }

    glos = []
    for gpath in sorted(CONTENT.glob("glosario-*.json")):
        try:
            items = json.loads(gpath.read_text(encoding="utf-8"))
        except Exception as e:
            problems.append(f"{gpath.name}: JSON inválido ({e})")
            continue
        for it in items:
            if it.get("slug") not in valid:
                problems.append(f"{gpath.name}: slug inválido en '{it.get('termino')}'")
                continue
            if FORBIDDEN.search(it.get("definicion", "") + it.get("termino", "")):
                problems.append(f"{gpath.name}: palabra prohibida en '{it.get('termino')}'")
            glos.append(it)
    seen, uniq = set(), []
    for it in sorted(glos, key=lambda x: strip_accents(x["termino"]).lower()):
        k = strip_accents(it["termino"]).lower()
        if k not in seen:
            seen.add(k)
            uniq.append(it)

    for p in PERFILES:
        for slug in p["topics"]:
            if slug not in valid:
                problems.append(f"perfil {p['id']}: tema inexistente {slug}")
    data = {"chapters": CHAPTERS, "topics": topics, "glosario": uniq, "perfiles": PERFILES}
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    missing = [f for f, *_ in FONTS if not (FONTS_DIR / f).exists()]
    problems += [f"falta la fuente fonts/{f}" for f in missing]

    # Versión: hash del contenido y de todo lo que se publica. Cambia solo si cambia algo.
    h = hashlib.sha256()
    h.update(json.dumps(data, ensure_ascii=False, sort_keys=True).encode())
    h.update(tpl.encode())
    for p in sorted(WEB.iterdir()):
        h.update(p.read_bytes())
    for f, *_ in FONTS:
        if (FONTS_DIR / f).exists():
            h.update((FONTS_DIR / f).read_bytes())
    version = h.hexdigest()[:10]
    generado = datetime.date.today().isoformat()

    def page(sw, fonts_css, head):
        d = dict(data, build={"version": version, "generado": generado, "sw": sw})
        blob = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
        return tpl.replace("__HEAD__", head).replace("__FONTS__", fonts_css).replace("__DATA__", blob)

    # 1) Sitio publicable: dist/web/ (index.html + service worker + manifest + fuentes).
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "fonts").mkdir(parents=True)
    for f, *_ in FONTS:
        if (FONTS_DIR / f).exists():
            shutil.copy2(FONTS_DIR / f, SITE / "fonts" / f)
    for name in ("icon.svg", "manifest.webmanifest", "_headers"):
        shutil.copy2(WEB / name, SITE / name)
    head = ('<link rel="manifest" href="manifest.webmanifest">\n<link rel="icon" href="icon.svg" type="image/svg+xml">\n'
            + "\n".join(f'<link rel="preload" href="fonts/{f}" as="font" type="font/woff2" crossorigin>' for f, *_ in FONTS[:2]))
    (SITE / "index.html").write_text(page(True, fonts_css(lambda f: f"fonts/{f}"), head), encoding="utf-8")
    assets = ["./", "manifest.webmanifest", "icon.svg"] + [f"fonts/{f}" for f, *_ in FONTS if (FONTS_DIR / f).exists()]
    sw = (WEB / "sw.js").read_text(encoding="utf-8").replace("__VERSION__", version).replace("__ASSETS__", json.dumps(assets))
    (SITE / "sw.js").write_text(sw, encoding="utf-8")

    # 2) Archivo único para abrir con doble clic: fuentes e icono incrustados, sin service worker.
    def data_uri(f):
        return "data:font/woff2;base64," + base64.b64encode((FONTS_DIR / f).read_bytes()).decode()
    icon = "data:image/svg+xml;base64," + base64.b64encode((WEB / "icon.svg").read_bytes()).decode()
    OUT.write_text(page(False, fonts_css(data_uri), f'<link rel="icon" href="{icon}">'), encoding="utf-8")

    site_kb = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file()) // 1024
    print(f"temas: {len(topics)}/{len(valid)} · palabras: {words} · glosario: {len(uniq)} · versión: {version}")
    print(f"  sitio: dist/web/ ({site_kb} KB) · archivo único: dist/manual.html ({OUT.stat().st_size//1024} KB)")
    for p in problems:
        print("  !", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
