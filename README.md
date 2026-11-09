# Manual de AI/ML y Plataforma

Manual de estudio para un equipo de ingeniería: 108 temas en 14 capítulos (LLMs, agentes, arquitectura, diseño de software y patrones, ML, observabilidad, cloud, frontend, UX y UI, seguridad, metodologías, análisis y decisiones, comunicación y lenguajes). Se publica como sitio estático instalable como PWA y funciona sin conexión.

## Generar

```
cd manual-fuente
pip install -r requirements.txt
python3 build.py
```

Genera `manual-fuente/dist/web/` (el sitio a publicar) y `manual-fuente/dist/manual.html` (todo en un solo archivo, para abrir con doble clic).

## Publicar en Cloudflare Pages

Conectar este repositorio en *Workers & Pages → Create → Pages → Connect to Git* con:

- Directorio raíz: `manual-fuente`
- Comando de build: `python3 build.py`
- Directorio de salida: `dist/web`

Cloudflare instala `requirements.txt` solo. Cada push a `main` publica una versión nueva y los lectores ven el aviso «Actualizar».

## Estructura

- `manual-fuente/content/`: un Markdown por tema y su glosario en JSON.
- `manual-fuente/template.html`: diseño, estilos y JavaScript del sitio.
- `manual-fuente/web/`: service worker, manifest, icono y cabeceras de caché.
- `manual-fuente/fonts/`: fuentes (licencia SIL OFL).
- `manual-fuente/GUIA_DE_ESTILO.md`: reglas de redacción.
