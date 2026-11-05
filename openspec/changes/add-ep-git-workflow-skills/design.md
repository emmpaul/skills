# Design

## Context

The repo contains only OpenSpec scaffolding (`openspec/`, `.claude/` OpenSpec commands). Skills are installed on the user's machine via `npx skills add` (vercel-labs/skills CLI), which copies each skill folder into `~/.agents/skills/<name>/` and links it into agent directories such as `~/.claude/skills/`. Each folder is installed independently, so a skill cannot rely on files outside its own folder. See proposal.md for motivation and specs/ for required behavior.

## Goals / Non-Goals

**Goals:**
- One self-contained folder per skill, discoverable by `npx skills add`.
- Identical, deterministic context gathering across all four skills.
- Subagent and Workflow use as an accelerator, never a requirement.
- Every outward or destructive action has an explicit gate.

**Non-Goals:**
- GitLab, Bitbucket, or other forges.
- Native Windows shells (bash path; inline fallback covers others).
- Publishing the repo or registering it in any skills directory.
- Tuning confidence-score weights beyond the initial values.

## Decisions

### D1. Repo layout

```
skills/
  ep-commit/      SKILL.md  scripts/context.sh
  ep-open-pr/     SKILL.md  scripts/context.sh
  ep-review/      SKILL.md  scripts/context.sh  references/dimensions.md
  ep-babysit-pr/  SKILL.md  scripts/context.sh  references/score.md
shared/
  context.sh                  # source of truth for the probe
scripts/
  sync-shared.sh              # copy shared/context.sh into each skill
  check-shared.sh             # fail if any copy differs (drift check)
README.md
```

`skills/<name>/SKILL.md` is the layout `npx skills add` discovers. Long reference material (review dimension checklists, score rubric) sits in `references/` so `SKILL.md` stays short and loads fast.
- Alternative: root-level skill folders. Rejected because `skills/` keeps the repo root free for tooling and docs.

### D2. Context probe: duplicated script with drift check

`shared/context.sh` prints one JSON object:

```
{ git:      { branch, upstream, ahead, behind, dirty, staged_files, unstaged_files, default_branch },
  pr:       { number, url, state, isDraft, mergeStateStatus, reviewDecision, checks: [...] } | null,
  openspec: { root, changes: [{ name, tasks_done, tasks_total }] } | null }
```

It uses only `git`, `gh` (optional: `pr: null` when missing or unauthenticated), and `openspec` (optional: `openspec: null` when missing or no root). JSON is assembled with `gh --jq`, `openspec --json` output, and printf, so `jq` is not required.

Each `SKILL.md` says: run `scripts/context.sh`; if bash is unavailable or it fails, run the listed commands inline.
- Alternative: prose-only commands. Rejected because the agent would improvise, giving inconsistent results and spending more tokens.
- Alternative: an `ep-context` skill invoked by name. Rejected because it breaks on partial installs and cross-skill invocation is agent-specific.

### D3. Subagent fan-out next to its sequential fallback

| Skill | With subagents | Without subagents |
|---|---|---|
| ep-commit | diff > ~400 changed lines: one subagent proposes the grouping | main agent groups hunks directly |
| ep-open-pr | none needed | same |
| ep-review | 4 dimension subagents in parallel, then 1 verifier per finding (or batched) | dimensions in sequence, then verify each finding inline |
| ep-review (high effort, Claude Code) | Workflow: `pipeline(dimensions -> verify)` | falls back to the subagent path |
| ep-babysit-pr | one subagent per failing check to read logs and propose a fix; `ep-review` round delegated | diagnose inline, run review steps inline |

Capability detection lives in each SKILL.md as plain instructions ("If you can spawn subagents, ...; otherwise ..."), because skills have no runtime to probe the host. Workflow use is explicitly instructed in `ep-review`, which counts as user opt-in when the user runs the skill at high effort.

### D4. Babysit loop pacing

In Claude Code, `ep-babysit-pr` uses the host's self-paced loop or scheduled wakeups (~3-5 min while CI runs, longer when waiting on humans). Agents without scheduling poll inline using `gh pr checks --watch` where available, and stop at a bounded session duration.

State between ticks (round number, fix attempts per check, last seen comment id) is kept in a local state file `.git/ep-babysit/<pr>.json`, which is never committed, survives across ticks, and is per-clone.
- Alternative: hidden PR comment state. Rejected because it adds GitHub noise and needs extra writes.

### D5. Confidence score rubric (`references/score.md`)

Hard gates (any fail means no merge): required checks green; `mergeStateStatus` not DIRTY; no unresolved threads; `reviewDecision != CHANGES_REQUESTED`.

| Evidence | Weight | Source |
|---|---|---|
| Final `ep-review` round: 0 verified critical/major | 35 | ep-review summary |
| Minor findings fixed or explicitly waived | 20 | ep-review summary + commits |
| Spec conformance passed | 20 | ep-review spec dimension |
| tasks.md complete | 15 | context probe |
| Tests added or touched for changed code | 10 | diff paths |

Without OpenSpec, the 35 points for spec conformance and tasks move to tests (total 45). Merge threshold: 85.

### D6. Merge-state mapping

| `mergeStateStatus` | Action |
|---|---|
| CLEAN, HAS_HOOKS | merge if score >= 85 and gates pass |
| UNSTABLE | treat non-required failures as a fix round; merge allowed if score >= 85 |
| BLOCKED | wait; notify the user once; re-check each tick |
| BEHIND | `gh pr update-branch`, then wait for checks |
| DIRTY | resolve conflicts as a fix round (merge or rebase locally, never force-push; use merge commit from base if needed) |
| UNKNOWN | retry 3 ticks, then stop |

Merge command: `gh pr merge <n> --delete-branch` with the repo's default method (detected from repo settings via `gh repo view --json`). `--admin` is never used.

### D7. Attribution suppression

Each SKILL.md states that commits, PR bodies, replies, and comments carry no model attribution, overriding host-agent defaults. Commits use `git commit -F <file>` with an explicit message so no trailer is appended by tooling.

### D8. `openspec/config.yaml`

Add `context` (distribution model, per-folder isolation, `ep-` prefix, portability, GitHub/gh, no attribution, OpenSpec optional) and `rules` for proposal/specs/design/tasks as agreed during exploration, so future changes in this repo inherit the constraints.

## Risks / Trade-offs

- [Auto-merge of a wrong change] → hard gates, evidence-only score, deference to branch protection, 3-round cap, printed score breakdown on the PR.
- [Self-review bias: ep-review checks code the babysitter wrote] → adversarial verify pass; recommend branch protection requiring human approval on important repos (README).
- [Probe copies drift] → `check-shared.sh` run in tasks and documented for pre-commit use.
- [Host agent injects attribution despite instructions] → explicit `-F` message files; verification task inspects created commits.
- [`gh` JSON field names change] → probe isolates gh calls in one place; fallback to `pr: null` with a warning.
- [Skill name collisions with other installs] → `ep-` prefix.
- [Babysit loop runs unbounded] → round cap, per-check attempt cap, session duration cap for non-scheduling agents.
- [Conflict resolution without force-push may create merge commits] → accepted; history cleanliness is secondary to never rewriting a shared branch.

## Migration Plan

Not applicable: new skills, nothing to migrate. Rollback is `npx skills remove ep-<name>`, or removing the folder from the repo.

## Open Questions

- Exact poll intervals for babysit ticks; tune after first use.
- Whether `ep-review --comment` should post one review with inline comments or a single summary comment; either satisfies the spec.
