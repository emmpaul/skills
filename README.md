# skills

Personal agent skills for git and GitHub workflows. Each skill is aware of the
active [OpenSpec](https://github.com/Fission-AI/OpenSpec) change when a repo uses
OpenSpec, works without it, and never adds model attribution to commits, PRs, or
comments.

## Skills

| Skill | What it does |
|---|---|
| `ep-commit` | Splits working-tree changes into logical Conventional Commits that match the repo's style. |
| `ep-open-pr` | Pushes the branch and opens a GitHub PR with a title and body built from the commits and the active OpenSpec change, labelled as a one-way or two-way door. |
| `ep-review` | Reviews a diff, branch, or PR for correctness, spec conformance, tests, and security, and verifies each finding before reporting it. |
| `ep-babysit-pr` | Watches a PR: fixes CI failures, answers review comments, runs up to 3 review rounds, and merges when gates pass and the confidence score is at least 85. |
| `ep-sync` | Merges the base branch into the current branch (rebase only on request, gated), then audits semantic interactions with no textual conflict (renamed or re-signatured symbols, behaviour and contract changes, new base callers, base tests), adapts the branch in separate commits, and runs tests. |
| `ep-fixup` | Attaches fixes to the branch commits they correct as `fixup!` commits, and autosquashes only on request: unpushed commits freely, pushed ones after confirmation with `--force-with-lease`. |
| `ep-ci-debug` | Diagnoses failing CI checks from their logs, classifies the cause (code, test, flaky-infra, config, secret), reproduces locally, and fixes it without weakening tests; re-runs infra failures once. |
| `ep-stack` | Splits a branch into a stack of dependent PRs after you approve the plan, shows stack status, syncs layers bottom up with merges, and retargets the next PR when a parent merges. |
| `ep-orchestrate` | Runs one OpenSpec change end to end: plans it, scores the plan and implements without asking only at 85 or more with nothing hard to undo, commits each task on its own, removes dead code the branch added, and runs up to 3 review and fix rounds, each phase in a fresh subagent with a resumable state file. Offers large changes as a stack of PRs landed with `ep-stack` and `ep-babysit-pr` after approval. |

## Install

Uses the [skills CLI](https://github.com/vercel-labs/skills).

```bash
# Interactive: pick from the skills found in the repo
npx skills add emmpaul/skills

# All nine ep-* skills
npx skills add emmpaul/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate

# A single skill
npx skills add emmpaul/skills --skill ep-commit

# From a local clone
npx skills add ./path/to/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate

# User-level (global) instead of project-level
npx skills add emmpaul/skills -g --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate
```

The repo also contains OpenSpec's own skills under `.claude/skills/` (used to develop this
repo), which the CLI lists too. Name the `ep-*` skills explicitly to install only these.

Remove with `npx skills remove ep-<name>`.

## Requirements

- `git`
- `gh`, authenticated (`gh auth login`)
- Optional: `openspec` CLI, for OpenSpec-aware behavior (required by `ep-orchestrate`)
- Optional: `bash`, to run the bundled context probe (`scripts/context.sh`); without it, skills run the equivalent commands inline

## Safety: `ep-babysit-pr` auto-merge

`ep-babysit-pr` can push to and merge your PR on its own. When it syncs a branch, fixes CI,
or commits review fixes, it calls `ep-sync`, `ep-ci-debug`, and `ep-fixup` in their
no-rewrite caller modes when they are installed, and uses bundled fallback steps when not. It never force-pushes,
never uses `--admin` or other protection bypasses, never resolves review threads,
and refuses to merge when checks fail, conflicts exist, threads are unresolved, or
changes are requested. It also defers to GitHub's merge state.

Because the reviewer it relies on is also an agent, **enable branch protection
requiring at least one human approval** on any repo where an unreviewed merge
would matter. The skill then waits for that approval instead of merging.

## Development

`shared/context.sh` is the source of truth for the context probe. Each skill ships
its own copy because skills are installed folder by folder.

```bash
scripts/sync-shared.sh    # copy shared/context.sh into every skill
scripts/check-shared.sh   # fail if any copy differs (run before committing)
```
