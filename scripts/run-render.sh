#!/usr/bin/env bash
set -euo pipefail
config="$1"
plugin_root="$(cd "$(dirname "$0")/.." && pwd)"
blender="${BLENDER_BIN:-blender}"
blend="$($plugin_root/scripts/pipeline.py paths "$config" | python3 -c 'import json,sys; print(json.load(sys.stdin)["blend"])')"
exec "$blender" --background "$blend" --python "$plugin_root/scripts/blender_render.py" -- "$config"
