# Tech Blogs

Agregador de blogs de ingeniería. Lee el listado de fuentes RSS de
[`engineering-blogs`](https://github.com/engineering-blogs/engineering-blogs) (un fichero
`engineering_blogs.opml`), descarga los posts de todos los feeds y genera un `index.html`
estático con los posts agrupados por día.

## Ejecución en local

Requiere `python3` y `git`.

```bash
cd tech-blogs
git clone https://github.com/engineering-blogs/engineering-blogs.git ../engineering-blogs
./scripts/fetch_local.sh
```

`fetch_local.sh` hace lo siguiente:

1. Comprueba si existe `.venv`; si no, lo crea e instala las dependencias de `app/requirements.txt`.
2. Ejecuta `app/fetch_blogs.py --local --opml <ruta>` con el Python del `.venv`.
3. Genera `index.html` y `posts_cache.json` en la raíz de `tech-blogs`.

La ruta del OPML es opcional (por defecto `../engineering-blogs/engineering_blogs.opml`):

```bash
./scripts/fetch_local.sh /ruta/al/engineering_blogs.opml
```

Para usar el modo contenedor (variables de entorno `OPML_FILE` y `OUTPUT_DIR`):

```bash
OPML_FILE=/ruta/engineering_blogs.opml OUTPUT_DIR=/ruta/salida .venv/bin/python app/fetch_blogs.py
```

## Ejecución en servidor (homelab)

El repositorio está pensado para ejecutarse de forma periódica en un servidor con Docker:

1. **Clona ambos repos** en el servidor:
   ```bash
   git clone https://github.com/engineering-blogs/engineering-blogs.git
   git clone https://github.com/<tu-usuario>/tech-blogs.git
   ```
2. **Configura las rutas** (copia de `.env.example` a `.env`):
   ```bash
   cp tech-blogs/.env.example tech-blogs/.env
   # Edita ENGINEERING_BLOGS_DIR, TECH_BLOGS_DIR e IMAGE_NAME
   ```
3. **Ejecuta la actualización** cada vez que quieras refrescar (p. ej. con cron):
   ```bash
   ./tech-blogs/scripts/update.sh
   ```

`update.sh` hace:

1. `git pull` de `engineering-blogs` (renueva el OPML).
2. `git pull` de `tech-blogs` (sincroniza antes de generar).
3. `docker compose pull && up`: arranca el contenedor `tech-blogs`, que ejecuta el script una vez
   (one-shot) y se detiene solo. Escribe `index.html` y `posts_cache.json` en `TECH_BLOGS_DIR`
   (volumen compartido entre el contenedor y el host).
4. Si hay cambios en `index.html`/`posts_cache.json`, los commitea y hace `git push`.

### Flujo de automatización (GitHub Actions)

| Workflow | Se activa con | Qué hace |
|---|---|---|
| `dockerhub.yml` | push en `app/**` | Construye la imagen y hace push a **DockerHub** |
| `pages.yml` | push en `index.html` | Despliega la página en **GitHub Pages** |

Los triggers usan rutas disjuntas: el push de `update.sh` (solo `index.html` + cache) nunca
dispara la pipeline de DockerHub, y los cambios de código en `app/` nunca disparan Pages.

### Requisitos de configuración (una vez)

- **DockerHub**: secrets `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` en GitHub.
- **GitHub Pages**: en Settings → Pages → Source = **GitHub Actions**.
- **Homelab**: Docker y Docker Compose instalados.

## Estructura

```
tech-blogs/
├── app/
│   ├── fetch_blogs.py      # script principal (modo contenedor y modo --local)
│   ├── requirements.txt
│   └── Dockerfile
├── compose.yml             # servicio one-shot (monta OPML y directorio de salida)
├── .env.example            # rutas e imagen configurables
├── scripts/
│   ├── fetch_local.sh      # ejecución en local (crea .venv si falta)
│   └── update.sh           # actualización completa en el servidor
├── index.html              # salida generada (se commitea para Pages)
├── posts_cache.json        # caché de posts (incremental)
└── .github/workflows/
    ├── dockerhub.yml
    └── pages.yml
```