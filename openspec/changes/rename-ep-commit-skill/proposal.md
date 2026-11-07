# Proposal

## Why

Committing and pushing are one routine step in practice, but `ep-commit` stops at the commit and never pushes unless asked, so every commit is followed by a hand-run `git push`. Renaming the skill to `ep-commit-and-push` and making the push part of its run matches how it is used, while callers that must stay local need an explicit way to commit without pushing.

## What Changes

- **BREAKING** Rename the skill `ep-commit` to `ep-commit-and-push`: folder `skills/ep-commit/` becomes `skills/ep-commit-and-push/`, with the frontmatter `name`, heading, and description updated. No `ep-commit` alias stays behind; installs of `ep-commit` must be removed and replaced.
- **BREAKING** (modified behavior) After creating and verifying its commits, the skill pushes the current branch to its own name with a plain push and an explicit refspec (`git push -u origin HEAD:refs/heads/<branch>` without an upstream, `git push <remote> HEAD:refs/heads/<branch>` with one). It never force-pushes, stops on a rejected push with the commits kept local, asks before pushing the default branch or when the default branch is unknown (confirmed with `gh` when available) or the upstream has another name, and pushes nothing when it made no commit.
- New `--no-push` flag (also triggered when the user or a calling skill says to commit without pushing): commit only, push nothing, and report the commits as local.
- Modified callers (rename only, behavior unchanged): `ep-babysit-pr` (SKILL.md and `references/side-paths.md`), `ep-fixup`, `ep-ci-debug`, `ep-sync`, `ep-stack`, `ep-open-pr`, `ep-qa`, and `ep-a11y` (`references/fix.md`) name `ep-commit-and-push` and its conventions instead of `ep-commit`.
- Modified caller with new behavior: `ep-orchestrate` (SKILL.md and `references/briefs.md`) invokes `ep-commit-and-push` with `--no-push` from every phase, so a regular run still pushes nothing. Its condensed commit fallback keeps never pushing and states the push rule it now condenses.
- README: the skills table row, the install commands, and a migration note for existing `ep-commit` installs. `openspec/config.yaml`'s capability-naming example and the in-flight changes `add-ep-front-door-skills`, `add-ep-hygiene-skills`, and `add-ep-after-merge-skills` name the new skill. Archived changes stay as they are.
- New outward effect on GitHub: `ep-commit-and-push` pushes the current branch to its remote after committing (plain push only, default branch gated, skipped with `--no-push`). No other skill gains a push.

## Capabilities

### New Capabilities
- `ep-commit-and-push`: turns working-tree changes into Conventional Commits in the repo's style with no attribution (the former `ep-commit` behavior), then pushes the branch with a plain push unless `--no-push` is given.

### Modified Capabilities
- `ep-commit`: every requirement is removed; the capability moves to `ep-commit-and-push`.
- `ep-orchestrate`: "Frequent, traceable commits" names `ep-commit-and-push` conventions and requires its no-push mode, so regular runs stay local.
- `ep-babysit-pr`: "Fix CI failures" and "Address review comments" name `ep-commit-and-push` conventions.
- `ep-ci-debug`: "Fix and push gate" names `ep-commit-and-push` conventions.
- `ep-fixup`: "Target commit selection" names `ep-commit-and-push` conventions.
- `ep-sync`: "Branch adaptation" names `ep-commit-and-push` conventions.
- `ep-open-pr`: "Preconditions checked before opening" offers `ep-commit-and-push` for uncommitted changes.

## Impact

- Skills: `skills/ep-commit/` moves to `skills/ep-commit-and-push/` (SKILL.md and the synced `scripts/context.sh`); prose edits in `ep-orchestrate`, `ep-babysit-pr`, `ep-fixup`, `ep-ci-debug`, `ep-sync`, `ep-stack`, `ep-open-pr`, `ep-qa`, `ep-a11y`. The `writing-for-agents` rubric applies to every edited description and body.
- Shared files: `shared/context.sh` reaches the new folder through `scripts/sync-shared.sh` (target `*`); `scripts/check-shared.sh` must pass. No shared file changes.
- Summary blocks: `ep-commit` prints none and `ep-commit-and-push` adds none; every existing `<!-- ep-… -->` block keeps its marker, fields, and formats.
- Installs: users replace `ep-commit` with `ep-commit-and-push` (`npx skills remove ep-commit`, then `npx skills add emmpaul/skills --skill ep-commit-and-push`).
- Specs: archive retires `openspec/specs/ep-commit/` (`retire_capabilities: true` in `.openspec.yaml`) and creates `openspec/specs/ep-commit-and-push/`.
