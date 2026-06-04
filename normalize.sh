#!/usr/bin/env bash
# Тонкая обёртка для Linux/macOS: вся логика в normalize_fs.py.
set -euo pipefail
exec python3 "$(dirname -- "$0")/normalize_fs.py" "$@"
