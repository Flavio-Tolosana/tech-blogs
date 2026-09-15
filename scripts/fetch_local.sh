#!/usr/bin/env bash
#
# Ejecuta la generación en local:
#   - Crea el .venv si no existe e instala las dependencias
#   - Salida (index.html, posts_cache.json y opml/) en dist/
#
# Uso:
#   ./scripts/fetch_local.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 no está instalado." >&2
  exit 1
fi

# Crear el entorno virtual si no existe
if [[ ! -d "$REPO_ROOT/.venv" ]]; then
  echo "==> Creando .venv..."
  python3 -m venv "$REPO_ROOT/.venv"
  "$REPO_ROOT/.venv/bin/pip" install --upgrade pip
  "$REPO_ROOT/.venv/bin/pip" install -r "$REPO_ROOT/app/requirements.txt"
fi

PYTHON="$REPO_ROOT/.venv/bin/python"

cd "$REPO_ROOT"
exec "$PYTHON" -m app --local
