#!/usr/bin/env bash
# Fail if any skill's copy of a shared file is missing or differs from shared/.
# Fix drift with scripts/sync-shared.sh.
set -uo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
src=$repo/shared/context.sh
status=0
count=0
for skill in "$repo"/skills/*/; do
  skill=${skill%/}
  [ -f "$skill/SKILL.md" ] || continue
  count=$((count + 1))
  copy=$skill/scripts/context.sh
  rel=${copy#"$repo"/}
  if [ ! -f "$copy" ]; then
    echo "missing: $rel"
    status=1
  elif ! cmp -s "$src" "$copy"; then
    echo "differs: $rel"
    status=1
  fi
done
if [ "$status" -ne 0 ]; then
  echo "shared files out of sync; run scripts/sync-shared.sh" >&2
else
  echo "ok: $count skill(s) match shared/context.sh"
fi
exit "$status"
