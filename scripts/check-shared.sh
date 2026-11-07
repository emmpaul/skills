#!/usr/bin/env bash
# Fail if any skill's copy of a shared file is missing or differs from shared/.
# Fix drift with scripts/sync-shared.sh.
set -uo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
# shellcheck source=shared-files.sh
. "$repo/scripts/shared-files.sh"
status=0
count=0
for entry in "${shared_files[@]}"; do
  IFS='|' read -r src dest skills <<<"$entry"
  targets=$(shared_targets "$repo" "$skills") || exit 1
  for skill in $targets; do
    count=$((count + 1))
    rel=skills/$skill/$dest
    if [ ! -f "$repo/$rel" ]; then
      echo "missing: $rel"
      status=1
    elif ! cmp -s "$repo/shared/$src" "$repo/$rel"; then
      echo "differs: $rel"
      status=1
    fi
  done
done
if [ "$status" -ne 0 ]; then
  echo "shared files out of sync; run scripts/sync-shared.sh" >&2
else
  echo "ok: $count shared cop(ies) match shared/"
fi
exit "$status"
