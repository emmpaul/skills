#!/usr/bin/env bash
# Copy shared files into every skill folder. Skills are installed folder by
# folder, so each one ships its own copy of the context probe.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
src=$repo/shared/context.sh
for skill in "$repo"/skills/*/; do
  skill=${skill%/}
  [ -f "$skill/SKILL.md" ] || continue
  mkdir -p "$skill/scripts"
  cp "$src" "$skill/scripts/context.sh"
  chmod +x "$skill/scripts/context.sh"
  echo "synced ${skill#"$repo"/}/scripts/context.sh"
done
