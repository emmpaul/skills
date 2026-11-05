# Proposal

## Why

The current `ep-*` skills move one change from commit to merge, but nothing looks after the repository as a whole. The README asks users to set up branch protection by hand before trusting `ep-babysit-pr`, dependency-bot PRs pile up without triage, nothing checks whether the main OpenSpec specs still describe the code, and there is no single view of which open PRs need the user's attention. These are recurring chores that are easy to forget and cheap to automate safely.

## What Changes

- Add four new skills under `skills/`, each a self-contained folder with its own `SKILL.md` and a synced copy of the context probe:
  - `ep-protect` (new): audits the default branch's protection and rulesets against a safe baseline (at least one required approving review, required status checks matching the repo's CI jobs, no force pushes, no deletion, required conversation resolution) and reports gaps. A read-only `--check` mode makes it usable as a preflight before `ep-babysit-pr`. It can apply missing settings, but only after showing the exact API payload and getting explicit confirmation. It never weakens existing protection.
  - `ep-deps` (new): triages open Dependabot and Renovate PRs. It reads release notes and changelogs, classifies each update's risk (patch, minor, or major, plus breaking-change notes and security advisories), groups the low-risk ones, and recommends an action for each. It hands the PRs the user picks to `ep-babysit-pr` only after the user confirms. It never merges anything itself.
  - `ep-spec-drift` (new): a repo-wide check that the code still matches `openspec/specs/*`. It applies `ep-review`'s spec-conformance method to whole specs instead of a diff and marks each requirement and scenario as implemented, partial, missing, or untested. It also lists unspecified behavior hotspots. It is read-only; with `--issue` it can file one GitHub issue after confirmation.
  - `ep-pr-digest` (new): a digest of the user's open PRs (authored and review-requested) in the current repo, or across GitHub with `--all`. It buckets them as ready to merge, blocked by CI, waiting on me, waiting on others, or stale. It is read-only, runs once by default, and can recur through the host's loop or schedule feature when available.
- Each skill ends its output with an `ep-<name>-summary` block so other skills and recurring runs can read the result.
- Update `README.md` with the four skills and their install names, and point the auto-merge safety note at `ep-protect --check`.
- `ep-babysit-pr` is **not** modified in this change. Calling `ep-protect --check` as a babysit preflight is left as a follow-up.

### Outward effects on GitHub

- `ep-protect`: changes branch protection or rulesets (needs admin), only after the payload is shown and the user confirms. The audit and `--check` are read-only.
- `ep-deps`: posts nothing by default. With the user's confirmation it starts `ep-babysit-pr` on the selected PRs, which can push and merge under that skill's existing gates. It may also comment on or close a dependency PR the user chooses to reject, also after confirmation.
- `ep-spec-drift`: read-only. `--issue` creates one issue after confirmation.
- `ep-pr-digest`: read-only, no GitHub writes.

## Capabilities

### New Capabilities
- `ep-protect`: auditing and, with confirmation, tightening default-branch protection so autonomous merges stay behind human-controlled gates.
- `ep-deps`: risk triage of dependency-update PRs and a gated handoff of the chosen PRs to `ep-babysit-pr`.
- `ep-spec-drift`: repo-wide conformance check of code against the main OpenSpec specs.
- `ep-pr-digest`: a read-only, attention-oriented digest of the user's open pull requests.

### Modified Capabilities
<!-- None: ep-babysit-pr and the other existing skills keep their current requirements. -->

## Impact

- New files: `skills/ep-protect/`, `skills/ep-deps/`, `skills/ep-spec-drift/`, `skills/ep-pr-digest/` (each with `SKILL.md`, `scripts/context.sh` synced from `shared/context.sh`, and `references/` where needed).
- Modified: `README.md` (skills table, install command, safety note).
- Unchanged: `shared/context.sh` and the existing four skills.
- Runtime dependencies: `git` and `gh` (authenticated). `ep-protect` writes need a token with admin rights on the repo. The `openspec` CLI is optional, except that `ep-spec-drift` reports not applicable without it.
- Portability: all four work without subagents. `ep-spec-drift` fans out one subagent per capability when it can, and `ep-pr-digest` recurrence uses host scheduling only when it is available.
