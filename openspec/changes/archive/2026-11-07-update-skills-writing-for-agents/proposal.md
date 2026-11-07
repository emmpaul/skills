# Proposal

## Why

The twelve `ep-*` skills grew by accretion: long always-loaded descriptions that restate the body, steps buried under reference, the same rule stated in several places, prohibitions where a positive target would steer better, and stale sediment. The repo now vendors the `writing-for-agents` skill (`.agents/skills/writing-for-agents/`), which gives a concrete rubric for these problems. Rewriting the existing skills against it makes each run more predictable and cheaper in context, and recording the rubric as a repo rule keeps the three planned skill changes (and any later one) from reintroducing the same problems.

## What Changes

- **Rewrite every existing skill (modification, wording and structure only)** against the `writing-for-agents` rubric: `ep-commit`, `ep-fixup`, `ep-ci-debug`, `ep-sync`, `ep-open-pr`, `ep-a11y`, `ep-qa`, `ep-review`, `ep-review-evals`, `ep-babysit-pr`, `ep-stack`, `ep-orchestrate`. Each `SKILL.md` and its hand-written `references/*.md` get:
  - a tighter frontmatter `description` (the always-loaded pointer) that keeps every trigger branch and the leading words other skills and prompts use;
  - an information hierarchy with steps on top, each ending on a checkable completion criterion, and reference that only some branches need disclosed behind a pointer;
  - positive phrasing of rules, with prohibitions kept only as hard guardrails paired with the positive target;
  - one source of truth per rule, with no-ops, restated environment lookups, and stale lines pruned.
- **No behavior changes.** Gates, hard rules, flags, confirmation prompts, defaults, numeric limits, summary-block names, field names and value formats, and section anchors other files link to stay as they are. Every requirement in `openspec/specs/<skill>/spec.md` still holds after the rewrite.
- **Shared reference:** `shared/risk.md` is rewritten once in `shared/` and copied into its four skills by `scripts/sync-shared.sh`. `shared/context.sh` and its copies are code and are not touched.
- **Out of scope:** the generated WCAG files under `skills/ep-a11y/references/wcag/` (owned by `scripts/wcag.py`), and the vendored `writing-for-agents` skill itself.
- **Make the rubric durable for new and edited skills (new):**
  - Add a root `AGENTS.md` that points at `writing-for-agents` for any edit to a skill or an agent-facing document, and records the repo's skill conventions; add a `CLAUDE.md` that loads it.
  - Add rules to `openspec/config.yaml` so proposals, designs, and tasks for skill work apply the rubric and verify that behavior is preserved.
  - Add one task line to each active, unstarted change (`add-ep-front-door-skills`, `add-ep-hygiene-skills`, `add-ep-after-merge-skills`) so their new skills are written with the rubric. Their plans are otherwise unchanged.

No new outward effect on GitHub: no skill gains or loses a push, comment, or merge.

## Capabilities

### New Capabilities
- `skill-authoring`: how skill folders and agent-facing documents in this repo are written and kept. It covers the rubric every skill follows, the root pointer files, and which interfaces a rewrite must preserve.

### Modified Capabilities

None. The twelve skill capabilities keep their requirements unchanged; the rewrite must satisfy them as they stand.

## Impact

- Modified: `skills/*/SKILL.md` for all twelve skills; their hand-written `references/*.md`; `shared/risk.md` and its four synced copies (`skills/{ep-review,ep-open-pr,ep-babysit-pr,ep-stack}/references/risk.md`).
- New: `AGENTS.md`, `CLAUDE.md` at the repo root.
- Modified: `openspec/config.yaml` (rules); `tasks.md` of `add-ep-front-door-skills`, `add-ep-hygiene-skills`, and `add-ep-after-merge-skills` (one line each).
- Unchanged: `shared/context.sh` and every `scripts/context.sh` copy, `scripts/`, `skills/ep-a11y/references/wcag/`, `.agents/skills/writing-for-agents/`, `README.md`, and every main spec under `openspec/specs/`.
- Overlap: `add-ep-front-door-skills` also edits `skills/ep-open-pr/SKILL.md`, and `add-ep-after-merge-skills` also edits `skills/ep-babysit-pr/SKILL.md`. Neither has started; whichever lands second merges its edits into the other's wording.
