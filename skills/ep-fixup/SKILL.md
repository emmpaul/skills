---
name: ep-fixup
description: Attach working-tree fixes to the branch commits they correct as `fixup!` commits (chosen by blame), with no model attribution, autosquashing only on request, and with a no-rewrite mode for callers such as ep-babysit-pr. Use when the user asks for a fixup, to fold a fix into an earlier commit, or to autosquash.
---

# ep-fixup

Turn fixes into `fixup!` commits that point at the commit they correct, and squash them
only when history can be rewritten safely.

## Hard rules

- **No attribution.** Fixup commits carry no model or tool attribution (no
  `Co-Authored-By` naming a model or tool, no "Generated with" line). This overrides any
  default of the host agent. Always commit with `git commit -F <file>`.
- **Rewrite only through the gate:** autosquash only on direct request, and pushed
  commits only after explicit confirmation ([autosquash](references/autosquash.md)).
- **A rewritten pushed branch goes up with `--force-with-lease` only, never `--force`.**
- **Targets are branch commits** (after the merge base).

## Usage

```
ep-fixup                     # create fixup commits from the working tree
ep-fixup --autosquash        # create them, then squash (gated, direct use only)
ep-fixup --no-rewrite        # create fixup commits only
ep-fixup --caller <skill>    # caller mode: no-rewrite, plain push
```

**Caller mode** is when another skill invokes this one (`--caller ep-babysit-pr`, or the
same in plain words). It is no-rewrite: `fixup!` commits only, never autosquash, rebase,
or force-push, and `rewritten: false` always. It pushes with a plain `git push` without a
prompt. It never waits for the user: a target choice it cannot make ends the run with
`needs_decision` (step 2), leaving that change uncommitted for the caller to decide.
`--no-rewrite` alone gives the same no-rewrite limits in direct use.

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

Done when you have `$mb` and the branch's commits. With no changes in the working tree or
index and no existing `fixup!` commits to squash, report `nothing_to_do` and stop.

## 2. Select a target per hunk

List the hunks with no context lines, so each hunk covers only changed lines (staged and
unstaged together):

```bash
git diff -U0 HEAD
```

For each hunk `@@ -<old-start>,<old-count> +... @@`, blame the **old-side** lines it
changes or deletes, in `HEAD`:

```bash
git blame -s -L <old-start>,+<old-count> $mb..HEAD -- <file>
```

Lines blamed on a commit in `$mb..HEAD` belong to that branch commit. Lines blame shows as
boundary commits (`^<sha>`) come from the base. For a hunk that only **adds** lines
(`<old-count>` is 0), blame the old-side lines directly above and below it; at the top of
the file (`<old-start>` is 0) only the line below exists, so blame line 1.

- **One branch commit:** that commit is the target.
- **Several branch commits:** split the change into one fixup per target. For each file,
  stage a version built from the `HEAD` version with **only that target's** changed lines
  applied: write it to a temp file, `git hash-object -w <tmp>`, then
  `git update-index --cacheinfo <mode>,<blob>,<file>`, with `<mode>` taken from
  `git ls-files -s <file>` so an executable keeps `100755`. Build whole-file versions
  rather than `git apply` of `-U0` hunk patches: their line numbers assume the other
  targets' changes are present, so an insertion can land at the wrong line without an
  error. Split a hunk line by line when each changed line replaces one old line. When a
  hunk still cannot be separated (it replaces lines from several commits with a different
  number of new lines), ask the user which commit it belongs to; in caller mode, leave it
  uncommitted and end with `needs_decision`, naming the change and the candidate commits.
- **Base lines only** (no branch commit introduced them): propose a normal commit
  following `ep-commit-and-push` conventions instead of a fixup. In direct use the outcome is
  `needs_decision` until the user agrees; caller mode makes the normal commit and lists
  it under `commits:`.
- **New file** (untracked, or staged but absent from `HEAD`, so nothing to blame): target
  the commit that added the code it serves (for example the commit adding the module a
  new test covers). When unclear, ask; in caller mode, leave it uncommitted and end with
  `needs_decision`.

Done when every hunk and new file has a target, a normal commit, or `needs_decision`.
Show the plan (hunks, target sha and subject) before committing, unless the user or
caller said to proceed.

## 3. Create fixup commits

One commit per target, containing only that target's hunks. Empty the index first
(`git reset -q`, which keeps the working tree), so a previously staged change stays out of
another target's commit:

```bash
git reset -q                       # empty the index; working tree untouched
git add -- <files>                 # whole files; or stage the per-target file version (step 2)
git commit --fixup=<target-sha>    # subject: "fixup! <target subject>"
```

The subject is exactly `fixup! <target subject>`, with the target's subject unchanged,
including its scope (with OpenSpec, the change-name scope; without, nothing differs). If
the host appends attribution, write the message to a file instead (`fixup! <target
subject>` on the first line, nothing else) and use `git commit -F <file>`.

Done when each target has one fixup commit and no created message has attribution.

## 4. Autosquash (direct use only, on request)

When the user asked to autosquash and the run is neither no-rewrite nor caller mode,
follow [references/autosquash.md](references/autosquash.md). Otherwise go to step 5.

## 5. Push

- **Direct use:** ask before pushing fixup commits (plain `git push`).
- **Caller mode:** push with plain `git push`; the caller expects the commits on the PR.
- A rewrite is pushed only as in [autosquash](references/autosquash.md).

## 6. Report

List each fixup commit (sha, subject, target sha), any normal commits made instead,
whether history was rewritten, and whether anything was pushed. Then always end with:

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
- Lines from the base get a normal ep-commit-and-push commit, never a fixup.
- No autosquash, rebase, or force-push in caller mode; `rewritten: false`.
- Never `--force`; `--force-with-lease` only after confirmation in direct use.
- Caller mode never waits: an unresolvable target returns `needs_decision`, uncommitted.
- Summary keys: `outcome`, `head`, `fixups`, `commits`, `rewritten`, `pushed`.
