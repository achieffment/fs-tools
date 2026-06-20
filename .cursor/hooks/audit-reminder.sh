#!/usr/bin/env bash
set -euo pipefail

input="$(cat)"
prompt="$(
  printf '%s' "$input" | python3 -c '
import json
import sys

obj = json.load(sys.stdin)
val = (
    obj.get("prompt")
    or obj.get("text")
    or obj.get("message")
    or (obj.get("input") or {}).get("prompt")
    or (obj.get("input") or {}).get("text")
    or ""
)
print(str(val).strip())
'
)"
lower="$(printf '%s' "$prompt" | tr '[:upper:]' '[:lower:]')"

is_audit=0
if [[ "$lower" == *"аудит"* ]] || [[ "$lower" == *"audit"* ]]; then
  is_audit=1
fi

if [[ "$is_audit" -eq 0 ]]; then
  printf '%s\n' '{ "permission": "allow" }'
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
  printf '%s\n' '{ "permission": "allow" }'
  exit 0
fi

printf '%s\n' '{
  "permission": "allow",
  "agent_message": "Подсказка по аудиту: укажи режим `audit changed` или `audit full` и требование `до полного green`."
}'
