---
name: ep-review-evals
description: Measure ep-review against the repository's own history. collect proposes incident and clean cases from merged PRs and saves only those the user confirms; run reviews them with ep-review and scores recall and noise; compare says keep or drop for a reviewer change from two runs; noise classifies how authors answered posted ep-review findings. Use when the user asks to evaluate, benchmark, or measure ep-review, build a review eval set, or check whether a reviewer change helps.
---

# ep-review-evals

Build a confirmed eval set from the repository's history, score `ep-review` on it, and
tell whether a reviewer change is worth keeping.

Paths under `references/` and `scripts/` are relative to this skill's own folder.

## Hard rules

- **Read-only on GitHub.** Read PRs, commits, and reviews only: no comment, review, issue,
  label, or PR change, and never `ep-review --comment`. Never push or fetch-and-write any
  remote.
- **The user's checkout stays as it was.** Case and run files stay uncommitted and out of
  `.gitignore`; the branch, index, and tracked files are unchanged.
- **Confirmation first.** Show what will be written (path and contents in short) before
  writing any file, and write it only after the user confirms. `run` states the case
  count and its cost and starts only after confirmation. Each collected case is
  confirmed on its own. No flag skips any of these; without a user to ask, write nothing
  and run nothing.
- **Only under the eval directory.** Write only `<dir>/cases.json` and `<dir>/runs/*.json`
  (`<dir>` is `review-evals/` at the repository root, or `--dir <path>`, relative to the
  root). Temporary worktrees live in the scratch directory, outside the repository.
- **No attribution** in any file or output.

## Usage

```
ep-review-evals collect [--days <n>]            # propose cases, confirm each, write cases.json
ep-review-evals run [--limit <n>] [--label <l>] # review the cases with ep-review, score, save a run
ep-review-evals compare <a> <b>                  # recall and noise of two runs, and keep or drop for b
ep-review-evals noise [--days <n>]               # how authors answered posted ep-review findings
ep-review-evals ... --dir <path>                 # eval directory (default review-evals/)
```

`--days` sets the window (default 90). `<a>` and `<b>` are run file paths or names under
`<dir>/runs/`. With no subcommand or an unknown one, print these four lines with their
descriptions, change nothing, and end with the summary block (`subcommand: none`).

## 1. Context

From the repository root, run the probe bundled in this skill's folder:

```bash
bash <skill-dir>/scripts/context.sh
```

Use its `git` (branch, dirty state, default branch). Entries in `warnings` are
informational. If bash is unavailable, or the probe exits non-zero or prints invalid JSON,
run `git status --porcelain=v1 -b` and `git symbolic-ref --short refs/remotes/origin/HEAD`
(else `main`, else `master`) inline. Leave the probe's `openspec` aside and OpenSpec out
of the output; `ep-review` decides on its own whether spec conformance applies to a case.

Decide the source (`references/collect.md`, Sources): `github` when `origin` is a GitHub
repository and `gh auth status` succeeds, `local` otherwise. Resolve `<dir>`. Done when
the default branch, the source, and `<dir>` are known.

## 2. collect

Read `references/collect.md`. Find incident proposals (Reverts, Fix forward) for PRs
merged within the window, then up to as many clean proposals, skipping cases already in
`<dir>/cases.json`. When there is nothing to propose, say so, write nothing, and end.

Ask about each proposal (Accept, Edit, Reject; "Confirming"). Then show the cases file
that would be written and ask once; write it only on yes ("Cases file"). With every
case rejected, write nothing. Print the accepted cases, the rejected count, and the
path. Leave the file uncommitted and suggest the user review it before committing it,
if they want to keep it in the repository.

Done when every proposal has an answer and the cases file is written or, with nothing
accepted or the write declined, left as it was.

## 3. run

Read `references/scoring.md`. Load `<dir>/cases.json`; without it, or with no cases,
say to run `collect` first and stop. Pick the cases (`--limit`, "Picking cases") and
compute the reviewer version ("Reviewer version").

**Confirm** once before any worktree exists. Show the number of cases by kind, their
ids, the cost (each case is a full `ep-review`: about 7 agents with subagents, one long
inline review without), the label, and the run file path it will write. Confirming
also confirms writing that file. Declined: run nothing, write nothing.

Take the before-snapshot (worktree list, branch, `HEAD`, `git status --porcelain`), then
for each case, one at a time:

1. Validate the case's fields before using any of them: `base` and `head` are 40 or 64
   lowercase hex characters, `pr` is `null` or a positive integer, and `id` matches
   `^[A-Za-z0-9._-]+$` and is not `.` or `..`. Any other value: `status: failed:
   invalid case`, next case, with nothing run for it. Then check `head` and `base` exist
   (`git cat-file -e <sha>^{commit}`); for the GitHub source, `git fetch origin
   pull/<pr>/head` first when the head is missing. Missing: `status: failed: commit
   missing`, next case.
2. `git worktree add --detach <scratch>/ep-review-evals/<run-id>/<case-id> <head>`.
3. Review it with `ep-review --since <base>` (no other flags, never `--comment`), run
   from the worktree's root, so the reviewed diff is `<base>..<head>`. Tell it that `<base>`
   is also the base for origin and blame: the head is already on the default branch, so
   the merge base would be the head itself and every finding would look pre-existing.
4. Record the result from the report and its `ep-review-summary` block ("Reading a
   review", "Hit rule").
5. `git worktree remove --force <path>`, also when the review failed.

**With subagents:** run each case in a fresh subagent, one case at a time (sequentially:
each `ep-review` already starts its own 7 agents). Give it the repository path, the case
(id, base, head), the worktree path, and steps 2-5, and ask for the report and summary
block back. The subagent posts nothing and changes nothing outside its worktree. After
it returns, check the worktree is gone and remove it if not.

**Without subagents:** run the cases inline, one after another, with the same steps,
using absolute paths so nothing runs in the user's checkout. `ep-review` then uses its
inline verification, and its summary records `verification: inline`; the run records
`verification: inline` too.

Then do Cleanup, score recall and noise ("Hit rule", "Noise rule"), and write the run
file ("Run file"). Print recall, noise, each case's id, kind, status, and hit, and the
path. A run that stopped partway still writes the cases that finished, with the others
as `status: failed: not run`.

### Cleanup

Act on this whenever `run` ends, finished or not (a failed case, a declined confirmation
after a worktree exists, an error, or an interruption you can still act on):

1. Every temporary worktree this run added lives under `<scratch>/ep-review-evals/`,
   where `<scratch>` is the host's scratch directory, else `$TMPDIR`, else `/tmp`, never
   inside the repository.
2. Remove each one: `git worktree remove --force <path>`, then `git worktree prune`.
3. Check `git worktree list --porcelain` matches the list taken before the run, and that
   the branch (`git rev-parse --abbrev-ref HEAD`), `HEAD`, and `git status --porcelain`
   match the before-snapshot. Report any difference as it stands, without reset or
   checkout.

Done when every case has a status, no worktree of this run is left, the checkout matches
the before-snapshot (or the difference is reported), and the run file is written.

## 4. compare

Read `references/scoring.md` and follow "Compare". Read-only: write nothing. Print the
table, the shared-case note when the case sets differ, and the verdict with what
decided it. Done when the verdict is printed with what decided it.

## 5. noise

Read `references/noise.md` and follow it. Read-only: write nothing and post nothing.
With no posted `ep-review` review in range, say so and suggest
`ep-review <pr> --comment`. Print the report and the proposed `REVIEW.md` lines. Done when
every posted finding in range has a response class.

## 6. Summary block

End every subcommand's output with this block, exactly in this form, as the last thing
in the output:

```
<!-- ep-review-evals-summary
subcommand: collect | run | compare | noise | none
source: github | local
dir: <eval dir>
cases: incident=<n> clean=<n>
proposed: incident=<n> clean=<n>
rejected: <n>
recall: <value> (<hits>/<incidents>) | n/a
noise: <value> (<findings>/<clean>) | n/a
verdict: keep | drop | n/a
verification: vote | inline | mixed | n/a
responses: fixed=<n> wrong=<n> intentional=<n> did_not_matter=<n> unanswered=<n>
written: <path>,<path> | none
-->
```

`cases` counts the cases accepted and written (`collect`), run with `status: ok` (`run`),
shared (`compare`), or zero (`noise`, `none`). `proposed` and `rejected` are zero outside
`collect`. `recall` and `noise` are for `run` (the run's values) and `compare` (`b`'s
values on the shared cases), `n/a` otherwise. `verdict` is only for `compare`,
`verification` only for `run`. `responses` counts posted findings for `noise` and is all
zero otherwise. `written` lists the files written this time.
