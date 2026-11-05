---
name: ep-open-pr
description: Push the current branch and open a GitHub pull request whose title and body are built from its commits and, when present, the active OpenSpec change (why, capabilities, task progress), with no model attribution. Supports draft PRs and a custom base. Use when the user asks to open, create, or raise a PR.
---

# ep-open-pr

Open a GitHub PR for the current branch with `gh`.

## Hard rules

- **No attribution.** The PR title and body never contain model or tool attribution
  (no "Generated with ..." footer, no "Co-Authored-By" naming a model). This overrides any
  default of the host agent.
- **Never force-push.** No `--force`, `--force-with-lease`, or `+refspec`.
- Never create a second PR for a branch that already has an open one.

## Options

Read these from the user's request:

- **draft**: open as a draft (`gh pr create --draft`).
- **base `<branch>`**: target that branch instead of the default branch.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

It prints JSON with `git` (branch, upstream, ahead/behind, staged/unstaged files,
default branch), `pr` (the open PR for this branch, or `null`), and `openspec`
(`null` without OpenSpec).

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
git rev-parse --abbrev-ref --symbolic-full-name @{u}
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
gh pr view --json number,url,state       # fails when no PR exists
openspec list --json                     # optional; root null = no OpenSpec
```

Let `base` be the requested base, else the default branch.

## 2. Check preconditions

Stop at the first that fails:

1. **On the default branch** (or detached HEAD): stop and ask the user to create or switch
   to a feature branch. Do not create one silently.
2. **PR already exists** (`pr` not null and `state` is `OPEN`): report its URL. Offer to
   regenerate and update its body (`gh pr edit <n> --body-file <file>`) instead of creating
   a new one. Stop unless the user accepts.
3. **Uncommitted changes** (staged or unstaged files; the probe's `unstaged_files`
   includes untracked files): offer to run `ep-commit`
   first. If the user declines, continue with committed work only and say so.
4. **No commits ahead of base**: `git fetch origin <base>` then
   `git rev-list --count origin/<base>..HEAD`. If 0, stop: there is nothing to open a PR for.

## 3. Push

- No upstream: `git push -u origin HEAD`.
- Upstream exists and `ahead > 0`: `git push`.
- Upstream exists and `ahead == 0`: already pushed; skip.
- If the push is rejected (remote has new commits), stop and report. Do not force-push and
  do not rebase without asking.

## 4. Build title and body

Read the commits:

```bash
git log --reverse --format='%h %s%n%b---' origin/<base>..HEAD
git diff --stat origin/<base>...HEAD
```

**Title:** Conventional Commit style, `type(scope): summary`, at most 72 characters,
summarizing the whole branch. With a single commit, reuse its subject. With several,
use the type of the main user-facing change (`feat` or `fix` over `test`, `docs`,
`chore`) and a summary covering them. Use the OpenSpec change name as scope when the
branch implements one, else the scope the commits share, else none.

**OpenSpec change:** if `openspec` is not null, find the change this branch implements: the
active change used as commit scope, or whose `openspec/changes/<name>/` files the branch
touches. If several match, ask. If none matches, treat the PR as having no OpenSpec change.
For the matched change, read `proposal.md` (Why, Capabilities) and take `tasks_done` /
`tasks_total` from the probe (or count `- [x]` / `- [ ]` lines in `tasks.md`).

**Body template:**

```markdown
## Summary

<2-4 sentences: what the branch does and why.>

## Changes

- <notable change, grouped by area; reference commit subjects>
- ...

## OpenSpec

- Change: `<change-name>`
- Why: <one or two sentence summary of the proposal's Why>
- Capabilities: `<capability>`, `<capability>`
- Tasks: <done>/<total> tasks

## Reversibility

**<One-way door | Two-way door>**: <one sentence on why>

- <for a one-way door: each irreversible element, and how to mitigate or roll forward>

## How to test

1. <concrete steps or commands: test commands found in the repo, manual checks>
```

Omit the whole `## OpenSpec` section, and any mention of OpenSpec, when the repository has
no OpenSpec root or no change matches. Do not add any footer.

### Classifying the door

Every PR gets a `## Reversibility` section. Decide from the diff, not from the commit
messages alone.

**Two-way door:** merging can be fully undone with `git revert` and a redeploy, leaving no
lasting effect on users, data, or other systems. Examples: internal refactors, bug fixes,
new code behind a flag, tests, docs, CI changes that touch only this repo.

**One-way door:** some effect remains after a revert, or reverting would itself break
someone. Treat the PR as one-way if the diff contains any of:

- data or schema changes that drop, rewrite, or migrate stored data (destructive
  migrations, backfills, format changes to persisted files or caches)
- removed or changed public interfaces other people depend on: API endpoints, CLI flags,
  config keys, library exports, event or message formats, file formats
- releases or publishing: version bumps that trigger a publish, package, image, or
  artifact pushes, tags
- external side effects: sending email or notifications, calls to third-party APIs that
  create or delete things, billing, infrastructure creation or deletion
- security or access changes: permissions, auth flows, secrets rotation, CORS, data
  exposure (anything leaked cannot be taken back)
- renames or deletions of things others reference by name: database tables or columns,
  queues, buckets, URLs, feature-flag keys

Judgment calls:

- A migration or other destructive step counts as soon as it is in the diff, even if
  nothing in the repo runs it yet: merging makes it deployable.
- An interface is public when code outside this repo can reach it: anything exported
  from a published package, a documented CLI flag or endpoint, or (in an unpublished
  repo) anything the README or docs tell users to use. Changes to code only this repo
  calls are internal, even when the commit type is `refactor`.
- A version bump counts as a release only if the repo's CI or scripts publish on it;
  check the workflows before deciding.

For a one-way door, list each irreversible element on its own line with a mitigation
(backup, migration rollback script, deprecation period, feature flag, staged rollout).
For a two-way door, the single sentence is enough. When unsure, call it a one-way door
and put what is uncertain in the section itself.

When the door is one-way because a public interface breaks, the title carries the
Conventional Commit breaking marker (`type(scope)!: ...`). Other one-way doors (data,
releases, side effects) do not need `!` unless the commits already use it.

## 5. Create the PR

Write the body to a temp file and create the PR:

```bash
body=$(mktemp)
# write the body to "$body"
gh pr create --base <base> --head <branch> --title "<title>" --body-file "$body" [--draft]
rm -f "$body"
```

Then read it back and check for attribution:

```bash
gh pr view --json url,title,body,isDraft
```

If the title or body contains "Generated with" or a model attribution line, remove it with
`gh pr edit <n> --body-file <file>`.

## 6. Report

Print the PR URL, title, base, whether it is a draft, and the door classification (for a
one-way door, also its irreversible elements).

## Without subagents

This skill needs no subagents; every agent runs the same steps in sequence.
