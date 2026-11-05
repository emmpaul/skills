# Design

## Context

There are four `ep-*` skills, each a self-contained folder with `SKILL.md`, a synced `scripts/context.sh`, and optional `references/`. The probe reports git, PR, and OpenSpec state; it knows nothing about issues. `ep-open-pr` already classifies one-way and two-way doors (its section 4) and finds the active OpenSpec change. See proposal.md for why the front-door skills are needed, and specs/ for the behavior they must have.

## Goals / Non-Goals

**Goals:**
- Three new self-contained skill folders that follow the existing layout and probe convention.
- A local record of the issue link that `ep-open-pr` can read without any GitHub write.
- An explicit gate on every GitHub write.

**Non-Goals:**
- Changing `shared/context.sh`. Issue data is fetched inline with `gh issue view`.
- Creating labels, milestones, projects, or assignees.
- Writing specs, design, or tasks in `ep-issue-to-change`. Those belong to the propose workflow.
- Running `openspec init` in any skill.
- Forges other than GitHub.

## Decisions

### D1. Layout

```
skills/
  ep-start/            SKILL.md  scripts/context.sh
  ep-issue/            SKILL.md  scripts/context.sh  references/door.md
  ep-issue-to-change/  SKILL.md  scripts/context.sh
```

`scripts/sync-shared.sh` already loops over `skills/*/` folders that contain a `SKILL.md`, so writing the `SKILL.md` first is enough for the sync to pick each folder up.

### D2. Door rules: a copied reference, not a cross-skill link

`ep-issue` needs `ep-open-pr`'s one-way/two-way rules. Skills are installed folder by folder, so it cannot link to `ep-open-pr/SKILL.md`. It ships `references/door.md`, a copy of the classification rules adapted to describe requested work rather than a diff.
- Alternative: move the rules into `shared/` and sync them like the probe. Rejected for now. Only two skills use them, and `ep-open-pr` keeps them inline. If a third skill needs them, extract them into `shared/door.md` and add it to `sync-shared.sh` and `check-shared.sh`.
- Risk: the two copies drift (see Risks).

### D3. Issue link storage for `ep-start` → `ep-open-pr`

`ep-start` stores the link in per-branch git config: `git config branch.<branch>.ep-issue <n>`. `ep-open-pr` reads it first, then falls back to parsing `<type>/<n>-<slug>` from the branch name.
- Lives in `.git/config`: never committed, scoped to the branch, and readable with plain `git` on any agent.
- Alternative: a state file under `.git/ep-start/`. Rejected because git config is already per-branch and needs no file format.
- Alternative: rely on the branch name only. Rejected because users rename branches, and descriptions may contain digits.
- `ep-open-pr` uses a closing keyword (`Closes #n`) when the PR title type is `feat` or `fix`, and `Refs #n` otherwise. Only the PR body changes, so no new GitHub write is added.

### D4. Gates on outward and local-destructive actions

| Skill | Action | Gate | Flag to skip the prompt |
|---|---|---|---|
| ep-issue | create issue / edit body / add labels | show the full draft, then confirm | `--yes` (ignored if duplicates were found) |
| ep-issue-to-change | comment on the issue | show the draft comment, then confirm | `--comment` |
| ep-issue-to-change | `openspec new change` | name shown; ask if it already exists | none |
| ep-start | stash a dirty tree | always asks (stash, carry over, or abort) | none |
| ep-start | push the branch | off by default | `--push` (plain `git push -u`, never force) |
| ep-start | `openspec new change` | offered, never automatic | `--change` |

GitHub text is written with `--body-file`, so shell quoting can't add anything, and it carries no attribution.

### D5. Duplicate search (`ep-issue`)

Run `gh issue list --search "<key terms> in:title,body" --state all --limit 20`, plus a second query built from the error message or symptom if there is one. Show matches with their state and last update. Matching is a judgment call, so the skill shows candidates and lets the user decide.

**With subagents:** one subagent runs the duplicate searches and ranks candidates, while the main agent drafts the body.
**Without subagents:** search first, then draft, both in sequence. The output is the same.

### D6. Branch naming (`ep-start`)

The type comes from labels (`bug` → `fix`, `enhancement`/`feature` → `feat`, `documentation` → `docs`) and otherwise from the description's verb. The default is `feat`. The slug is lowercase ASCII and kebab-case, at most about 40 characters, with stop words dropped. Before creating, the skill checks `git show-ref` for the local name and `git ls-remote --heads origin` for the remote one. The base is `origin/<default_branch>` from the probe after `git fetch origin`, or `origin/<base>` when `--base` is given. The branch is created with `git switch -c <name> origin/<base> --no-track`, so a later plain push sets its own upstream.

### D7. Proposal from the issue (`ep-issue-to-change`)

Get the instructions and template from `openspec instructions proposal --change <name> --json` and follow them. Capabilities come from `openspec list --specs` plus `openspec show <id> --type spec --json --no-scenarios`, so existing paths are reused. The skill stops after the proposal and points to the propose workflow for the remaining artifacts. This keeps the issue as the single input and avoids inventing design.

### D8. Summary blocks

Each skill ends with the same shape as `ep-review`'s:

```
<!-- ep-start-summary
outcome: started | aborted
branch: <name>
base: <sha>
issue: <n> | null
change: <name> | null
stash: <stash ref> | null
-->
```

`ep-issue-summary` has the fields `outcome` (`created | updated | drafted | duplicate | aborted`), `issue`, `door`, and `labels`.
`ep-issue-to-change-summary` has the fields `outcome` (`created | exists | no_openspec | aborted`), `issue`, `change`, and `commented`.

## Risks / Trade-offs

- [The door rules in `ep-issue/references/door.md` drift from `ep-open-pr`] → a task diffs the rule lists by hand at implementation time. Extract into `shared/` if a third consumer appears (D2).
- [A stash created by `ep-start` is forgotten] → the stash message names the new branch, and the stash ref is printed in the report and the summary block.
- [Duplicate search misses a duplicate] → it's a best-effort search, and the user still confirms before creating.
- [The issue number is wrong when parsed from a branch name] → git config takes precedence, and parsing only runs on the `<type>/<digits>-` pattern.
- [`ep-issue-to-change` writes a proposal from a thin issue] → unknowns are written as open questions rather than invented scope (spec), and the report asks the user to resolve them.

## Migration Plan

This change only adds skills; nothing existing needs migrating. The `ep-open-pr` change is additive: branches without a recorded issue behave exactly as before. To roll back, remove the three folders and revert the `ep-open-pr` section.
