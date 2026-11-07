---
name: ep-sync
description: Bring the base branch into the current branch (merge by default, rebase only on request), resolve conflicts, then run a merge audit for semantic interactions with no textual conflict, adapt the branch in separate commits, run tests, and report. Use when the user asks to sync, update, or merge main into a branch, or to check what an update from base broke.
---

# ep-sync

Integrate the base branch and check that the branch is still correct, not just
conflict-free.

## Hard rules

- **No attribution.** Merge and adaptation commits carry no model or tool attribution
  (no `Co-Authored-By` naming a model or tool, no "Generated with" line). This overrides
  any default of the host agent. Commit with `git commit -F <file>`.
- **Merge by default.** Rebase only when the user invokes this skill directly and asks
  for it ([references/rebase.md](references/rebase.md)).
- **Never `--force`.** `--force-with-lease` only after a confirmed rebase of a pushed
  branch.
- **Push behind a gate:** the user confirms, or the caller owns pushing.
- **Decisions belong to the user.** An incompatible conflict or an ambiguous adaptation
  stops the run with the options shown, never a pick of your own.

## Usage

```
ep-sync                      # sync with the PR base, else the default branch
ep-sync <base>               # sync with a named base branch
ep-sync --rebase             # rebase instead of merge (direct use only, gated)
ep-sync --caller <skill>     # caller mode (see "Caller mode")
```

Plain-language requests work the same ("sync with develop", "rebase onto main").

**Caller mode** is when another skill invokes this one (`--caller ep-babysit-pr`, or the
same in plain words). It merges only and never offers a rebase. It neither pushes nor
asks to: the caller owns pushing (`pushed: false`). Anything that needs the user (an
incompatible conflict, an ambiguous adaptation) ends the run with outcome
`needs_decision` and the options in the report, instead of waiting. The audit,
adaptations, tests, and report run as usual.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
gh pr view --json number,baseRefName      # fails when no PR exists
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
openspec list --json                      # optional; root null = no OpenSpec
```

## 2. Resolve the base and check preconditions

**Base:** the name the user gave; else the open PR's `baseRefName`; else the repository
default branch. Fetch it before comparing:

```bash
git fetch origin <base>
base_ref=origin/<base>          # use the local <base> only when there is no remote
```

Stop at the first that fails:

1. **Detached HEAD**, or the current branch is the base itself: stop and say so.
2. **Dirty working tree** (staged, unstaged, or untracked files): stop and ask the user
   to commit (offer `ep-commit`) or stash first. Leave the stashing to them.
3. **Up to date:** `git rev-list --count HEAD..$base_ref` is 0. Report that the branch is
   up to date, change nothing, and end with outcome `up_to_date`.

**OpenSpec:** if the repository has an OpenSpec root, find the active change this branch
implements (used as commit scope, touched by the branch, or named in the PR body).
Without a root or a matching change, skip every OpenSpec step and mention OpenSpec
nowhere.

Done when the audit inputs are recorded, before integrating anything
([`references/audit.md`](references/audit.md#inputs)): the merge base, B (incoming base
commits and diff), R (the branch's own diff), and the pre-sync head sha.

## 3. Integrate

**Merge** (default, and always in caller mode):

```bash
git merge --no-ff --no-commit $base_ref
```

With no conflicts, commit the merge with a message file:

```
Merge <base> into <branch>
```

(match the repo's existing merge subjects if `git log --merges` shows a style).

**Rebase** (direct use only, on request): follow
[`references/rebase.md`](references/rebase.md), then continue with step 4.

## 4. Resolve textual conflicts

For each conflicted file (`git diff --name-only --diff-filter=U`), read both sides and
the merge base (`git show :1:<f>`, `:2:<f>`, `:3:<f>`).

- **Compatible:** both sides' intents can hold at once (both added different entries to a
  list, independent edits to adjacent lines, an import added on each side). Resolve
  keeping both, `git add` the file, and note it for the report.
- **Incompatible:** the sides make contradictory decisions about the same logic
  (different values for the same constant, opposite conditions, one side deletes code
  the other changes). Show both versions, explain the conflict, and wait for the user's
  decision. In caller mode, abort (`git merge --abort` / `git rebase --abort`), leave the
  branch as it was, and end with outcome `needs_decision`.

Done when no file is conflicted and the merge commit (or `git rebase --continue`) is made
with a message file.

## 5. Merge audit

Run the audit in [`references/audit.md`](references/audit.md) against the integrated
result, whether or not there were conflicts: the five checks, clustering (in parallel
with subagents, in sequence without), and one class per interaction with its evidence.

Done when every interaction has a class (needs-update, review, no-impact) and evidence:
base commit, branch location, reason.

## 6. Adapt the branch

For each needs-update interaction, update the branch's code so it is correct with the new
base (for example: update every call site of a renamed function, pass the new required
argument, read the renamed config key).

- Commit each adaptation **separately from the merge commit**, after it, following
  `ep-commit` conventions: Conventional Commit, type `fix` or `refactor`, the repo's
  scope convention (with OpenSpec, the active change name), and a body naming the base
  commit that caused it. Group interactions from one cluster into one commit.

  ```
  fix(api): call fetch_user after base rename

  Base commit a1b2c3d renamed get_user to fetch_user; profile.py still
  called the old name.
  ```

- **Ambiguous** (more than one reasonable fix with different behaviour): present the
  options with their consequences and wait for the user. In caller mode, end with outcome
  `needs_decision` and leave the push to the caller; the merge commit stays local.
- An interaction you could not fix stays `unresolved: <why>` in the report.

Done when every needs-update interaction has an adaptation commit, options presented, or
`unresolved: <why>`.

## 7. Verify

Run the repository's tests (find the command in CI workflows, `package.json`,
`Makefile`, `pyproject.toml`, and so on). When the full suite is impractical, run the
subset covering the interactions and the base tests from audit check 4, and say which
subset ran. Leave tracked files as they were after the run.

- Tests pass: outcome `synced` (unless something is unresolved or needs a decision).
- Tests fail: report the failures. Outcome is `needs_attention`, never `synced`.
- No test command found, or the runner is not installed: `tests: not_run`, and say so.

`needs_attention` is also the outcome when any needs-update interaction is unresolved.

## 8. Push gate

- **Direct use:** after a successful sync, show the report and ask before pushing. Push
  a merge with plain `git push`, or `git push -u origin HEAD` when the branch has no
  upstream; push a rebase as in
  [`references/rebase.md`](references/rebase.md#push-after-a-rebase).
- **Caller mode:** the caller pushes. `pushed: false`.
- On `needs_decision` or `needs_attention`, push only with the user's explicit go-ahead.

## 9. Report

Print, in order:

1. Base, mode, incoming commit count, and conflicts (each file and how it was resolved).
2. The audit table from [`references/audit.md`](references/audit.md), or
   `No interactions found.`, plus the checks run.
3. Adaptation commits (sha and subject).
4. Test command and result.
5. For `needs_decision`: each decision and its options.

Then always end with the summary block, exactly in this form, so callers can parse it:

```
<!-- ep-sync-summary
outcome: synced | up_to_date | needs_decision | needs_attention
head: <sha after the skill ran>
mode: merge | rebase
base: <base-ref>@<sha>
conflicts: <n>
audit: needs_update=<n> review=<n> no_impact=<n>
unresolved_needs_update: <n>
tests: passed | failed | not_run
pushed: true | false
-->
```

Callers parse only keys they know and ignore the rest. With no interactions, every audit
count is 0.

## Rules that must match

These rules are repeated in `ep-babysit-pr/references/side-paths.md#sync`. Keep both lists
identical.

- Merge only in caller mode; never rebase a pushed branch without explicit confirmation.
- Never `--force`; `--force-with-lease` only after a confirmed rebase, direct use only.
- Audit after every sync, conflicts or not, with the five checks and three classes.
- Adaptations are separate commits after the merge commit, with no attribution.
- Incompatible conflicts and ambiguous adaptations are never decided by the skill;
  caller mode returns `needs_decision` and nothing is pushed.
- Never report `synced` while tests fail.
- Summary keys: `outcome`, `head`, `mode`, `base`, `conflicts`, `audit`,
  `unresolved_needs_update`, `tests`, `pushed`.
