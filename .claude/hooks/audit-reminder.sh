#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
prompt="$(
  printf '%s' "$input" | python3 -c '
import json
import sys

obj = json.load(sys.stdin)
print(str(obj.get("prompt") or "").strip())
'
)"
lower="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')"

is_audit=0
if [[ "$lower" == *"аудит"* ]] || [[ "$lower" == *"audit"* ]]; then
  is_audit=1
fi

if [[ "$is_audit" -eq 0 ]]; then
  exit 0
fi

has_mode=0
if [[ "$lower" == *"audit changed"* ]] || [[ "$lower" == *"audit full"* ]] || [[ "$lower" == *"аудит changed"* ]] || [[ "$lower" == *"аудит full"* ]]; then
  has_mode=1
fi

has_green=0
if [[ "$lower" == *"до полного green"* ]] || [[ "$lower" == *"full green"* ]] || [[ "$lower" == *"полного green"* ]]; then
  has_green=1
fi

if [[ "$has_mode" -eq 1 ]] && [[ "$has_green" -eq 1 ]]; then
  exit 0
fi

echo "Подсказка по аудиту: укажи режим \`audit changed\` или \`audit full\` и требование \`до полного green\` (см. skill audit-governor)."
exit 0
