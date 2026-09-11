#!/usr/bin/env bash
#
# Actualiza los blogs de ingeniería:
#   1. git pull de engineering-blogs (renueva engineering_blogs.opml)
#   2. docker compose pull & up  (one-shot: ejecuta el script y el contenedor sale solo)
#   3. commit + push del index.html y posts_cache.json generados
#
# Requiere un fichero .env en la raíz del repo (ver .env.example).
#
set -euo pipefail

SEP="================================================================"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

START_EPOCH=$(date +%s)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$REPO_ROOT/.env"

echo "$SEP"
log "INICIO: actualización de engineering blogs"
echo "$SEP"

if [[ ! -f "$ENV_FILE" ]]; then
  log "ERROR: No existe $ENV_FILE. Copia .env.example a .env y configura las rutas."
  exit 1
fi

set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

: "${ENGINEERING_BLOGS_DIR:?Falta ENGINEERING_BLOGS_DIR en .env}"
: "${TECH_BLOGS_DIR:?Falta TECH_BLOGS_DIR en .env}"
: "${IMAGE_NAME:?Falta IMAGE_NAME en .env}"

COMPOSE="docker compose --env-file $ENV_FILE -f $REPO_ROOT/compose.yml"

log "==> [1/5] git pull de engineering-blogs"
git -C "$ENGINEERING_BLOGS_DIR" pull --ff-only

log "==> [2/5] git pull de tech-blogs (sincronizar antes de generar)"
git -C "$TECH_BLOGS_DIR" pull --ff-only

log "==> [3/5] docker compose pull + up (one-shot)"
$COMPOSE pull
$COMPOSE up

log "==> [4/5] commit + push de los archivos generados"
cd "$TECH_BLOGS_DIR"
git add index.html posts_cache.json
if git diff --cached --quiet; then
  log "    Sin cambios detectados. Nada que pushear."
else
  git commit -m "chore: actualizar engineering blogs"
  git push origin main
fi

echo "$SEP"
log "FIN: actualización completada en $(( $(date +%s) - START_EPOCH ))s"
echo "$SEP"