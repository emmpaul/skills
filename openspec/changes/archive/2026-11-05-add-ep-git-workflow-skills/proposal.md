# Proposal

## Why

Git workflow chores (writing commits, opening PRs, reviewing diffs, shepherding PRs through CI and review) are repetitive and lose context: generic tools don't know which OpenSpec change is in flight, add model attribution, and stop at the first failure. This repo is empty apart from OpenSpec scaffolding, so it's a clean place to start a personal, installable skill set built around these needs.

## What Changes

- Add four agent skills under `skills/`, installable via `npx skills add <owner>/skills` (vercel-labs/skills CLI):
  - `ep-commit`: split working-tree changes into logical Conventional Commits, matching repo style, with no model attribution.
  - `ep-open-pr`: open a GitHub PR whose title/body is built from the commits and, when present, the active OpenSpec change (proposal summary, spec deltas, task progress), plus a one-way / two-way door reversibility classification.
  - `ep-review`: review a local diff, branch, or PR across parallel dimensions (correctness, OpenSpec spec conformance, tests, security) followed by an adversarial verify pass; report locally or post to the PR.
  - `ep-babysit-pr`: watch a PR, fix CI failures, address and reply to review comments, run up to 3 review rounds, and auto-merge when an evidence-based confidence score is >= 85 and GitHub's merge state allows it.
- Add a shared context probe (`shared/context.sh`) copied into each skill's `scripts/` folder, with a drift check, that emits git/PR/OpenSpec state as JSON.
- Fill in `openspec/config.yaml` `context` and `rules` with the constraints for this repo: per-folder self-contained skills, the `ep-` prefix, cross-agent portability, GitHub/`gh`, no attribution, and graceful behavior when OpenSpec is absent.
- Add a basic root `README.md`: what the repo is, the four skills with one-line descriptions, install commands (`npx skills add <owner>/skills`, single-skill and local-path installs), requirements (`git`, `gh`, optional `openspec` and `bash`), and a safety note on `ep-babysit-pr` auto-merge recommending branch protection.
- Every skill works without subagents (sequential fallback); subagents and Claude Code Workflows are optional accelerators.

## Capabilities

### New Capabilities
- `ep-commit`: turning working-tree changes into well-scoped, attribution-free commits aware of the active OpenSpec change.
- `ep-open-pr`: creating a GitHub pull request with an OpenSpec-aware, attribution-free title and body.
- `ep-review`: multi-dimension code review with spec conformance checking, verified findings, and local or PR output.
- `ep-babysit-pr`: autonomous PR shepherding through CI, review rounds, and gated auto-merge.

### Modified Capabilities
<!-- None: no existing specs in this repo. -->

## Impact

- New files: `skills/ep-*/SKILL.md`, `skills/ep-*/scripts/context.sh`, `shared/context.sh`, a drift-check script, and a root `README.md`.
- Modified: `openspec/config.yaml`.
- Runtime dependencies for users: `git`, `gh` (authenticated), `bash` (optional; inline fallback), `openspec` CLI (optional), `jq` or equivalent only if the probe needs it.
- Outward effects: `ep-open-pr`, `ep-review --comment`, and `ep-babysit-pr` write to GitHub; `ep-babysit-pr` can push to and merge PRs, gated as specified.
- Portability: full behavior in Claude Code; agents without subagents run the sequential path; Workflow fan-out in `ep-review` is Claude Code only.
