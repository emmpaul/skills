# AGENTS.md

Before creating or editing anything under `skills/` or `shared/`, or this file or `CLAUDE.md`, load the `writing-for-agents` skill (`.agents/skills/writing-for-agents/`) and write to its rubric.

## Conventions

- Shared files have one source in `shared/`. Edit them there, run `scripts/sync-shared.sh` to copy them into the skill folders, then run `scripts/check-shared.sh` to confirm the copies match. Leave the copies to the script.
- Summary blocks (`<!-- ep-… -->`) stay byte-compatible: other skills parse their marker, field names, field order, and value formats.
- Files under `skills/ep-a11y/references/wcag/` change only through `scripts/wcag.py`.
- Vendored skills under `.agents/skills/` stay as they are; they come from their source, pinned in `skills-lock.json`.
