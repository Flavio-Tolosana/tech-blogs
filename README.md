# Tech Blogs

Agregador de blogs de ingeniería. Descarga dos fuentes OPML
([`kilimchoi/engineering-blogs`](https://github.com/kilimchoi/engineering-blogs) y
[`engineeringblogs.xyz`](https://engineeringblogs.xyz/engblogs.opml)), las mergea deduplicando
feeds, y genera un `index.html` estático con los posts agrupados por día.

## Ejecución en local

Requiere `python3`.

```bash
cd tech-blogs
./scripts/fetch_local.sh
```

`fetch_local.sh` hace lo siguiente:

1. Comprueba si existe `.venv`; si no, lo crea e instala las dependencias de `app/requirements.txt`.
2. Ejecuta `python -m app --local`.
3. Genera `index.html`, `posts_cache.json` y `opml/` en `dist/`.

Para usar el modo contenedor (variable de entorno `OUTPUT_DIR`):

```bash
OUTPUT_DIR=/ruta/salida .venv/bin/python -m app
```

## Tests

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest tests/
```

## Ejecución en servidor (homelab)

El repositorio está pensado para ejecutarse de forma periódica en un servidor con Docker:

1. **Clona el repo** en el servidor:
   ```bash
   git clone https://github.com/<tu-usuario>/tech-blogs.git
   ```
2. **Configura las rutas** (copia de `.env.example` a `.env`):
   ```bash
   cp tech-blogs/.env.example tech-blogs/.env
   # Edita TECH_BLOGS_DIR e IMAGE_NAME
   ```
3. **Ejecuta la actualización** cada vez que quieras refrescar (p. ej. con cron):
   ```bash
   ./tech-blogs/scripts/update.sh
   ```

`update.sh` hace:

1. `git pull` de `tech-blogs` (sincroniza antes de generar).
2. `docker compose pull && up`: arranca el contenedor `tech-blogs`, que ejecuta el script una vez
   (one-shot) y se detiene solo. El contenedor descarga y mergea los OPMLs, y escribe `index.html`,
   `posts_cache.json` y `opml/engineering_blogs.opml` en `TECH_BLOGS_DIR/dist` (volumen compartido
   entre el contenedor y el host).
3. Si hay cambios en `dist/`, los commitea y hace `git push`.

### Flujo de automatización (GitHub Actions)

| Workflow | Se activa con | Qué hace |
|---|---|---|
| `dockerhub.yml` | push en `app/**` (o tests/deps) | Construye la imagen y hace push a **DockerHub** |
| `pages.yml` | push en `dist/index.html` | Despliega la página en **GitHub Pages** |

Los triggers usan rutas disjuntas: el push de `update.sh` (solo `dist/`) nunca dispara la pipeline
de DockerHub, y los cambios de código en `app/` nunca disparan Pages.

### Requisitos de configuración (una vez)

- **DockerHub**: secrets `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` en GitHub.
- **GitHub Pages**: en Settings → Pages → Source = **GitHub Actions**.
- **Homelab**: Docker y Docker Compose instalados.

## Estructura

```
tech-blogs/
├── app/
│   ├── __main__.py         # entry point (python -m app)
│   ├── cli.py              # parsing de args y orquestación
│   ├── config.py           # Config dataclass y constantes
│   ├── opml.py             # descarga, parseo y merge de OPMLs
│   ├── feed.py             # fetching de feeds RSS (concurrente)
│   ├── cache.py            # caché JSON incremental
│   ├── html_generator.py   # generación del HTML desde template
│   ├── templates/
│   │   └── page.html       # template HTML/CSS/JS
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .dockerignore
├── tests/                  # pytest (ops, feeds, caché, HTML, CLI)
├── dist/                   # salida generada (se versiona para Pages)
│   ├── index.html
│   ├── posts_cache.json
│   └── opml/
│       └── engineering_blogs.opml  # mergeado (los intermedios se ignoran)
├── scripts/
│   ├── fetch_local.sh      # ejecución en local (crea .venv si falta)
│   └── update.sh           # actualización completa en el servidor
├── compose.yml             # servicio one-shot (monta dist/)
├── pyproject.toml          # configuración de pytest
├── requirements-dev.txt    # dependencias de desarrollo (pytest)
├── .env.example            # rutas e imagen configurables
└── .github/workflows/
    ├── dockerhub.yml
    └── pages.yml
```