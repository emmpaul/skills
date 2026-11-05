# Proposal

## Why

The `ep-*` chain starts at `ep-commit`, so everything before the first commit happens by hand. That includes writing up the issue, choosing a branch name, branching from a stale base, and creating the OpenSpec change. Because the chain has no front door, branch names, issue links, and the active OpenSpec change all vary from one piece of work to the next, and these are exactly what `ep-commit`, `ep-open-pr`, and `ep-babysit-pr` read later.

## What Changes

- Add three new skills under `skills/`:
  - `ep-issue` (new): draft or triage a GitHub issue. It writes a title, a body with reproduction steps or acceptance criteria, labels chosen only from the repo's existing labels, and a one-way or two-way door call that reuses `ep-open-pr`'s classification. It searches for duplicates before creating anything.
  - `ep-issue-to-change` (new): turn a GitHub issue into an OpenSpec change with `openspec new change` and a proposal built from the issue. It can optionally comment on the issue to link the change. In a repo without OpenSpec it stops and says so; it never runs `openspec init`.
  - `ep-start` (new): start work from an issue number or a free-text description. It fetches the default branch, creates a branch named `<type>/<issue>-<slug>` (or `<type>/<slug>` with no issue) from the fresh base, can optionally create an OpenSpec change, and records the issue link so `ep-open-pr` can use it. It refuses to run on a dirty tree unless the user confirms a stash.
- `ep-open-pr` (modification): the PR body references the issue linked by `ep-start`, using `Closes #<n>` for fixes and features.
- Each skill ships its own copy of the context probe, synced by the existing `scripts/sync-shared.sh`. `shared/context.sh` itself does not change.
- Each skill ends its output with a machine-readable `ep-<name>-summary` block, so other skills can read the result.
- README: add the three skills to the skills table and install commands.

**Outward effects on GitHub:**
- `ep-issue` creates an issue, and may apply labels.
- `ep-issue-to-change` may post one comment on the source issue.
- `ep-start` makes no GitHub writes by default. It pushes the new branch only when the user asks.

Every one of these writes shows the draft first and waits for confirmation, unless the user passes an explicit flag (`--yes` for issue creation, `--comment` for the link comment, `--push` for the branch). None of the skills adds attribution.

## Capabilities

### New Capabilities
- `ep-issue`: drafting, deduplicating, labelling, and creating GitHub issues with a reversibility call.
- `ep-issue-to-change`: turning a GitHub issue into an OpenSpec change proposal, optionally linking back on the issue.
- `ep-start`: starting a unit of work: a fresh base, a conventional branch name, an optional OpenSpec change, and an issue link.

### Modified Capabilities
- `ep-open-pr`: adds a requirement to reference the issue linked to the branch in the PR body.

## Impact

- New files: `skills/ep-start/`, `skills/ep-issue/`, and `skills/ep-issue-to-change/`, each with a `SKILL.md` and `scripts/context.sh` (a synced copy), plus `references/` where needed.
- Modified: `README.md` (skills table, install commands), and `skills/ep-open-pr/SKILL.md` (issue reference in the body).
- Unchanged: `shared/context.sh`, `ep-commit`, `ep-review`, `ep-babysit-pr`.
- Runtime: `git` and `gh` are required. `openspec` is optional for `ep-start` and required for `ep-issue-to-change`.
- Local effects: `ep-start` creates a branch and may stash changes. Both `ep-start --change` and `ep-issue-to-change` write under `openspec/changes/`.
