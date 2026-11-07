# Table of shared files, sourced by sync-shared.sh and check-shared.sh.
# Each entry: <file in shared/>|<destination inside the skill folder>|<skills>
# where <skills> is `*` (every skill folder with a SKILL.md) or a
# space-separated list of skill folder names.
shared_files=(
  "context.sh|scripts/context.sh|*"
  "risk.md|references/risk.md|ep-review ep-open-pr ep-babysit-pr ep-stack"
)

# Print the skill folder names an entry's <skills> field names.
shared_targets() {
  local repo=$1 skills=$2 dir name
  if [ "$skills" = "*" ]; then
    for dir in "$repo"/skills/*/; do
      dir=${dir%/}
      if [ -f "$dir/SKILL.md" ]; then echo "${dir##*/}"; fi
    done
  else
    for name in $skills; do
      if [ ! -f "$repo/skills/$name/SKILL.md" ]; then
        echo "shared-files: no skill folder skills/$name" >&2
        return 1
      fi
      echo "$name"
    done
  fi
}
