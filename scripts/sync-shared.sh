#!/usr/bin/env bash
# Copy shared files into skill folders. Skills are installed folder by
# folder, so each one ships its own copy of every shared file it uses.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=shared-files.sh
. "$repo/scripts/shared-files.sh"
for entry in "${shared_files[@]}"; do
  IFS='|' read -r src dest skills <<<"$entry"
  targets=$(shared_targets "$repo" "$skills") || exit 1
  for skill in $targets; do
    copy=$repo/skills/$skill/$dest
    mkdir -p "$(dirname "$copy")"
    cp "$repo/shared/$src" "$copy"
    case $copy in *.sh) chmod +x "$copy" ;; esac
    echo "synced skills/$skill/$dest"
  done
done
