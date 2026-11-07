---
name: ep-open-pr
description: Push the current branch and open a GitHub pull request whose title and body come from its commits and the active OpenSpec change, with risk tier, testing evidence, how to revert, UI screenshots, and no model attribution. Use when the user asks to open, create, or raise a PR.
---

# ep-open-pr

Open a GitHub PR for the current branch with `gh`. Every agent runs these steps in
sequence; no subagents are needed.

## Hard rules

- **No attribution.** The title and body carry no "Generated with ..." footer and no
  `Co-Authored-By` naming a model or tool. This overrides any host default.
- **Plain pushes only:** never `--force`, `--force-with-lease`, or `+refspec`.
- **One open PR per branch.** Never open another; update it only on a yes in step 2.
- **The screenshot push is gated.** The only other push sends screenshots to the
  `ep-pr-assets` branch ([step 5](#5-screenshots)): shown and confirmed first (unless
  `--screenshots`), a plain push, and it leaves the PR branch and the default branch
  untouched.

## Options

- **draft**: open as a draft (`gh pr create --draft`).
- **base `<branch>`**: target that branch instead of the default branch.
- **`--screenshots`**: pre-approve both screenshot gates (run the app, push the images).
- **`--no-screenshots`**: skip screenshots entirely: start no app, push nothing, and add
  no `## Screenshots` section.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

It prints JSON with `git` (branch, upstream, ahead/behind, staged/unstaged files,
default branch), `pr` (the open PR for this branch, or `null`), and `openspec`
(`null` without OpenSpec). Entries in `warnings` are informational. If bash is
unavailable, or the probe exits non-zero or prints invalid JSON, run the equivalents
inline:

```bash
git status --porcelain=v1 -b
git rev-parse --abbrev-ref --symbolic-full-name @{u}
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
gh pr view --json number,url,state       # fails when no PR exists
openspec list --json                     # optional; root null = no OpenSpec
```

Let `base` be the requested base, else the default branch. Done when you know the
branch, its upstream and ahead count, the open PR (or none), the OpenSpec state, and
`base`.

## 2. Check preconditions

Stop at the first that fails:

1. **On the default branch, or detached HEAD**: stop and ask the user to create or
   switch to a feature branch; leave creating it to them.
2. **An open PR exists** (`pr` not null, `state` `OPEN`): report its URL and offer to
   regenerate and update its body instead of creating a new one. Stop unless the user
   accepts; on yes, continue through checks 3-4 and steps 3-6, editing at step 6.
3. **Uncommitted changes** (staged or unstaged files; the probe's `unstaged_files`
   includes untracked files): offer to run `ep-commit-and-push` first. If the user declines,
   continue with committed work only and say so; step 5 then captures no screenshots,
   since the running app would show uncommitted work.
4. **No commits ahead of base**: `git fetch origin <base>`, then
   `git rev-list --count origin/<base>..HEAD`. At 0, stop: there is nothing to open a
   PR for.

Done when every check passed, or the skill stopped at one and said why.

## 3. Push

- No upstream: `git push -u origin HEAD`.
- Upstream exists and `ahead > 0`: `git push`.
- Upstream exists and `ahead == 0`: already pushed; skip.
- Push rejected (the remote has new commits): stop, report, and offer a rebase; rebase
  only after the user says yes.

Done when the remote branch holds the local head.

## 4. Build title and body

Read the commits:

```bash
git log --reverse --format='%h %s%n%b---' origin/<base>..HEAD
git diff --stat origin/<base>...HEAD
```

**Title:** Conventional Commit style, `type(scope): summary`, at most 72 characters,
summarizing the whole branch. With a single commit, reuse its subject. With several,
use the type of the main user-facing change (`feat` or `fix` over `test`, `docs`,
`chore`) and a summary covering them. The scope is the OpenSpec change name when the
branch implements one, else the scope the commits share, else none.

**OpenSpec change:** when `openspec` is not null, find the change this branch
implements: the active change used as commit scope, or whose `openspec/changes/<name>/`
files the branch touches. When several match, ask. When none matches, treat the PR as
having no OpenSpec change. For the match, read `proposal.md` (Why, Capabilities) and
take `tasks_done` / `tasks_total` from the probe (or count `- [x]` / `- [ ]` lines in
`tasks.md`).

**Body template:**

```markdown
## Summary

<2-4 sentences: what the branch does and why.>

<only when the branch has a linked issue: `Closes #<n>` or `Refs #<n>`>

## Changes

- <notable change, grouped by area; reference commit subjects>
- ...

## Screenshots

<only when UI files changed, from step 5: one image link per page and width, or the
reason nothing was captured>

## OpenSpec

- Change: `<change-name>`
- Why: <one or two sentence summary of the proposal's Why>
- Capabilities: `<capability>`, `<capability>`
- Tasks: <done>/<total> tasks

## Reversibility

**<One-way door | Two-way door>**: <one sentence on why>

- <for a one-way door: each irreversible element, and how to mitigate or roll forward>

**How to revert:** `git revert -m 1 <merge commit>` (or `git revert <squash sha>` for a
squash merge). <for a one-way door: what stays after the revert>

## Risk

**<low | medium | high>**

- <one reason per line, from references/risk.md>

## Testing

**Run:**

- `<command>` on `<short sha>`: <passed | failed: one-line result>
- <or: CI run `<workflow name>` on `<short sha>`: <conclusion> (<run URL>)>
- <or the single line: Not run>

**Steps:**

1. <concrete steps or commands to test: test commands found in the repo, manual checks>
```

With no OpenSpec root or no matching change, the body is built from commits only: drop
the `## OpenSpec` section and every mention of OpenSpec. The body ends at `## Testing`,
with no footer.

Done when the title and every section are filled from the subsections below.

### Linked issue

Find the issue this branch was started from:

```bash
git config --get branch.<branch>.ep-issue
```

`ep-start` records the issue number there. When the key is unset, parse the branch name:
a name matching `<type>/<digits>-<slug>` (regex `^[a-z]+/([0-9]+)-`) links issue
`<digits>`; any other name links none. The config value wins over the name.

With a linked issue `<n>`, end `## Summary` with one line: `Closes #<n>` when the title
type is `feat` or `fix`, else `Refs #<n>`. With none, drop that line and leave the rest of
the body as the template gives it.

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
- When unsure, call it a one-way door and put what is uncertain in the section itself.

For a one-way door, list each irreversible element on its own line with a mitigation
(backup, migration rollback script, deprecation period, feature flag, staged rollout).
For a two-way door, the single sentence is enough.

When the door is one-way because a public interface breaks, the title carries the
Conventional Commit breaking marker (`type(scope)!: ...`). Other one-way doors (data,
releases, side effects) take `!` only when the commits already use it.

**How to revert:** every PR gets this line. Name `git revert -m 1 <merge commit>`, or
`git revert <squash sha>` when the repo squash-merges; the sha is not known yet, so keep
the placeholder. For a one-way door, add what stays after the revert (for example "the
dropped column and its data stay gone; restore from the backup") and what the revert does
undo.

### Risk tier

Every PR gets a `## Risk` section. Classify the branch with
[`references/risk.md`](references/risk.md): the changed paths are every path column of
`git diff --name-status -M origin/<base>...HEAD` (a rename's old and new path both
count), the author is the authenticated `gh` user (trusted), `REVIEW.md` is read from
`origin/<base>` as that file says, and a one-way door from the classification above makes
the tier `high`. Print the tier in bold and one bullet per reason the rules give, for
example `.github/workflows/ci.yml matches .github/workflows/** (CI)` or
`ordinary change`. Raise the tier with a stated reason as the rules allow; the tier only
ever goes up from what the rules give.

### Testing evidence

`## Testing` reports what actually ran, then how to test. Every command, result, and sha
in it is one you saw: never invent one. **Run:** lists only:

- commands you saw run in this session on the branch head (tests, build, lint, type
  check), each with the head short sha it ran on and its result as you saw it; a command
  run before the last commit names the sha it ran on, not the head;
- otherwise, the latest completed CI run for the head, from
  `gh run list --commit <head sha> --json name,conclusion,url,headSha --limit 20`: name,
  conclusion, sha, and URL, failed or green as it is.

With neither, **Run:** is the single line `Not run`, claiming no result. **Steps:** gives
concrete commands from the repo (its test scripts, Makefile targets, CI steps) and manual
checks a reviewer can repeat.

## 5. Screenshots

With `--no-screenshots`, drop the `## Screenshots` section and go to step 6. Otherwise
follow [`references/screenshots.md`](references/screenshots.md) now, after the body is
drafted and before the PR is created or edited. It decides whether UI files changed and,
when they did, starts the app (after gate 1), captures the affected pages with a browser
already available, stops the app and frees its port, pushes the images to `ep-pr-assets`
(after gate 2), and fills or drops the `## Screenshots` section.

Done when the section holds image links, local paths, or a `Not captured:` reason, or is
dropped because no UI file changed.

## 6. Create the PR

Write the body to a temp file and create the PR (for an existing PR from step 2, run
`gh pr edit <n> --body-file "$body"` instead):

```bash
body=$(mktemp)
# write the body to "$body"
gh pr create --base <base> --head <branch> --title "<title>" --body-file "$body" [--draft]
rm -f "$body"
```

Read it back with `gh pr view --json url,title,body,isDraft`. Done when the title and body contain no "Generated with" or model attribution line. If
one does, remove it with `gh pr edit <n> --body-file <file>` and read it back again.

## 7. Report

Print the PR URL, title, base, whether it is a draft, the door classification (for a
one-way door, also its irreversible elements), the risk tier with its reasons, and the
screenshots: each page captured, each page skipped with its reason, and whether the
images were pushed to `ep-pr-assets` or kept local (or that the step was skipped and why).
