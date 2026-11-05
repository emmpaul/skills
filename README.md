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

## Install

Uses the [skills CLI](https://github.com/vercel-labs/skills).

```bash
# Interactive: pick from the skills found in the repo
npx skills add emmpaul/skills

# All four ep-* skills
npx skills add emmpaul/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr

# A single skill
npx skills add emmpaul/skills --skill ep-commit

# From a local clone
npx skills add ./path/to/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr

# User-level (global) instead of project-level
npx skills add emmpaul/skills -g --skill ep-commit ep-open-pr ep-review ep-babysit-pr
```

The repo also contains OpenSpec's own skills under `.claude/skills/` (used to develop this
repo), which the CLI lists too. Name the `ep-*` skills explicitly to install only these.

Remove with `npx skills remove ep-<name>`.

## Requirements

- `git`
- `gh`, authenticated (`gh auth login`)
- Optional: `openspec` CLI, for OpenSpec-aware behavior
- Optional: `bash`, to run the bundled context probe (`scripts/context.sh`); without it, skills run the equivalent commands inline

## Safety: `ep-babysit-pr` auto-merge

`ep-babysit-pr` can push to and merge your PR on its own. It never force-pushes,
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
