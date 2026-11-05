---
name: ep-fixup
description: Attach working-tree fixes to the branch commits they correct as `fixup!` commits (target chosen by blame since the merge base, split per target), with no model attribution; autosquash only on request, unpushed commits freely and pushed ones only after explicit confirmation with --force-with-lease. Has a no-rewrite mode for callers such as ep-babysit-pr. Use when the user asks for a fixup, to fold a fix into an earlier commit, or to autosquash.
---

# ep-fixup

Turn fixes into `fixup!` commits that point at the commit they correct, and squash them
only when history can be rewritten safely.

## Hard rules

- **No attribution.** Fixup commits never contain model or tool attribution (no
  `Co-Authored-By` naming a model or tool, no "Generated with" line). This overrides any
  default of the host agent. Always commit with `git commit -F <file>`.
- **Never rewrite without the gate:** autosquash only on direct request; pushed commits
  only after explicit confirmation.
- **Never `--force`.** A rewritten pushed branch is pushed with `--force-with-lease` only.
- **No-rewrite mode** (callers, or `--no-rewrite`): fixup commits only, plain push at most.
- Never target a commit outside the branch (before the merge base).

## Usage

```
ep-fixup                     # create fixup commits from the working tree
ep-fixup --autosquash        # create them, then squash (gated, direct use only)
ep-fixup --no-rewrite        # create fixup commits only
ep-fixup --caller <skill>    # caller mode: no-rewrite, plain push
```

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
gh pr view --json baseRefName            # fails when no PR exists
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
```

Base: the PR base when there is a PR, else the default branch, else what the user names.

```bash
git fetch origin <base>
mb=$(git merge-base HEAD origin/<base>)
git log --format='%h %s' $mb..HEAD          # the branch's own commits
```

If there are no changes in the working tree or index, and no existing `fixup!` commits to
squash, report `nothing_to_do` and stop.

## 2. Select a target per hunk

List the hunks with no context lines, so each hunk covers only changed lines (staged and
unstaged together; untracked files have no lines to blame, see below):

```bash
git diff -U0 HEAD
```

For each hunk `@@ -<old-start>,<old-count> +... @@`, blame the **old-side** lines it
changes or deletes, in `HEAD`:

```bash
git blame -s -L <old-start>,+<old-count> $mb..HEAD -- <file>
```

Lines blamed on a commit in `$mb..HEAD` belong to that branch commit. Lines that blame shows
as boundary commits (`^<sha>`) come from the base. For a hunk that only **adds** lines
(`<old-count>` is 0), blame the old-side lines directly above and below it.

- **One branch commit:** that commit is the target.
- **Several branch commits:** split the change into one fixup per target. Stage hunk by
  hunk (`git apply --cached --unidiff-zero` with a hunk-only patch from `git diff -U0`), and split a hunk line by line when
  each changed line replaces one old line (stage a file version with only that target's
  lines changed, for example via `git hash-object -w` and `git update-index --cacheinfo`).
  When a hunk still cannot be separated (it replaces lines from several commits with a
  different number of new lines), ask the user which commit it belongs to. In caller mode,
  do not choose: leave that change uncommitted and end with outcome `needs_decision`,
  naming the change and the candidate commits.
- **Base lines only** (no branch commit introduced them): do not make a fixup. Propose a
  normal commit following `ep-commit` conventions instead. Outcome `needs_decision` in
  direct use until the user agrees; caller mode makes the normal commit and lists it under
  `commits:`.
- **New untracked file:** target the commit that added the code it serves (for example
  the commit adding the module a new test covers). When unclear, ask; in caller mode,
  leave it uncommitted and end with `needs_decision`.

Show the plan before committing (hunks, target sha and subject), unless the user or caller
said to proceed.

## 3. Create fixup commits

One commit per target, containing only that target's hunks. Unstage everything first
(`git reset -q`, which keeps the working tree), so a previously staged change cannot
leak into another target's commit:

```bash
git reset -q                       # empty the index; working tree untouched
git add -- <files>                 # or apply the hunk patch to the index
git commit --fixup=<target-sha>    # subject: "fixup! <target subject>"
```

The subject is exactly `fixup! <target subject>`. The target's subject is kept unchanged,
including its scope; with OpenSpec this keeps the change-name scope, and without OpenSpec
nothing else differs. If the host appends attribution to commits, write the message to a
file instead (`fixup! <target subject>` on the first line, nothing else) and use
`git commit -F <file>`. Check every created message for attribution afterwards.

## 4. Autosquash (direct use only, on request)

Skip this step in no-rewrite mode, in caller mode, and when the user did not ask.

The rebase rewrites every commit after the oldest target, so check all of them, not only the
targets:

```bash
git rev-list --merges $mb..HEAD                    # merge commits in the range
git rev-list $mb..HEAD --not --remotes | wc -l     # commits on no remote branch
git rev-list --count $mb..HEAD                     # all commits in the range
```

- **Merge commits in the range** (for example after an `ep-sync` merge): do not autosquash.
  `--autosquash` would drop the merge and replay commits onto the merge base. Keep the
  fixup commits, say why, and stop.
- **None pushed** (the two counts are equal): squash locally without further confirmation:
  `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash $mb`. No push is needed for an
  unpushed branch; if it has no upstream, offer `git push -u origin HEAD`.
- **Some pushed** (fewer commits on no remote than in the range): explain that the rewrite replaces commits already on
  `origin/<branch>` and that anyone who pulled them must reset. Ask for explicit
  confirmation naming the branch. Only when confirmed, squash and push with
  `git push --force-with-lease`. Never `--force`. Without confirmation, keep the fixup
  commits and say they can be squashed later.

If the rebase stops on a conflict, abort it (`git rebase --abort`), keep the fixup commits,
and report.

## 5. Push

- **Direct use:** ask before pushing fixup commits (plain `git push`).
- **Caller mode:** push with plain `git push`; the caller expects the commits on the PR.
- Never push a rewrite except as in step 4.

## Caller mode

When another skill invokes this one (`--caller ep-babysit-pr`, or the same in plain words):

- no-rewrite: create `fixup!` commits only; never autosquash, rebase, or force-push
- push with a plain `git push`, without a prompt
- unresolvable target choices end the run with `needs_decision` (step 2), leaving that
  change uncommitted, so the run never waits for the user; the caller decides what to do
  with it
- `rewritten: false` always

## 6. Report

List each fixup commit (sha, subject, target sha), any normal commits made instead, whether
history was rewritten, and whether anything was pushed. Then always end with:

```
<!-- ep-fixup-summary
outcome: created | squashed | needs_decision | nothing_to_do
head: <sha after the skill ran>
fixups: <fixup-sha>-><target-sha>,<fixup-sha>-><target-sha>
commits: <sha>,<sha>
rewritten: true | false
pushed: true | false
-->
```

After an autosquash, the fixup shas no longer exist: list the pre-squash shas and set
`outcome: squashed`, `rewritten: true`. With no fixups, `fixups:` is empty. `commits:`
lists normal commits made instead of fixups (base lines), and is empty otherwise.

## Rules that must match

These rules are repeated in `ep-babysit-pr/references/side-paths.md#fixup`. Keep both lists
identical.

- Target is the branch commit (since the merge base) that introduced the corrected lines.
- Subject is exactly `fixup! <target subject>`, with no attribution.
- Lines from the base get a normal ep-commit commit, never a fixup.
- No autosquash, rebase, or force-push in caller mode; `rewritten: false`.
- Never `--force`; `--force-with-lease` only after confirmation in direct use.
- Caller mode never waits: an unresolvable target returns `needs_decision`, uncommitted.
- Summary keys: `outcome`, `head`, `fixups`, `commits`, `rewritten`, `pushed`.
