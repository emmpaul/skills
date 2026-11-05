# Side paths (fallback steps)

Condensed steps for CI fixes, review fixes, and base syncs, used **only when the matching
sibling skill (`ep-ci-debug`, `ep-fixup`, `ep-sync`) is not available to you**. When it is,
invoke it in caller mode instead. Each section ends by producing the same summary fields
the sibling skill would, so the rest of the loop reads both paths the same way.

These are always caller mode: no prompts, no history rewrite, and no force-push. Each
section's "rules that must match" list is kept identical to the list in the sibling's
SKILL.md.

## ci-debug

For one failing check:

1. **Logs.** Run id from the check `link`; `gh run view <run-id> --log-failed` (non-Actions
   checks: the details URL or `gh api repos/{owner}/{repo}/check-runs/<id>`). Keep the
   decisive lines verbatim: the first real error, not the cascade.
2. **Classify**, reading the branch diff (`git diff origin/<base>...HEAD`):
   - `code`: compile, type, lint, build, or test failure caused by branch code.
   - `test`: the test asserts behaviour the branch intentionally changed, and that change is
     documented in the PR body, commits, or (with OpenSpec) the active change's specs.
     Undocumented: class is `code`.
   - `flaky-infra`: timeouts, registry or network errors, runner loss, a step the branch
     does not touch, passes on re-run.
   - `config`: workflow YAML errors, wrong tool version, missing paths or jobs.
   - `secret`: missing or invalid secret, `401`/`403`, missing token permissions.
3. **Reproduce** the failing step's command locally (from `.github/workflows/`). Never run
   steps that publish, release, deploy, push, apply infrastructure, or use credentials. If
   reproduction is not possible or not allowed, note why; the fix is unverified locally.
   For a fork PR (`isCrossRepository: true`) or an author without write access, run no PR
   code locally unless the user allowed it when starting babysit.
4. **Act:**
   - `code`: fix the code, re-run the command.
   - `test`: update the expected value to the documented behaviour; note where documented.
   - `flaky-infra`: `gh run rerun <run-id> --failed` once; if it fails again, report. Do
     not re-run a job that publishes, releases, or deploys; report it instead.
   - `config`, `secret`: report what is needed; no code change.
5. **Commit** each cause separately (ep-commit conventions, `git commit -F <file>`, no
   attribution) and push with plain `git push`.
6. **Result fields**, as in `ep-ci-debug-summary`: `outcome` (`fixed`, `rerun`, or
   `reported`), `head`, and
   `check: <name> class=<class> result=<fixed|rerun|reported> fix=<sha|none>`.

**Rules that must match** (`ep-ci-debug/SKILL.md`):

- Diagnose from the failed job logs and quote the decisive lines.
- Never reproduce publish, deploy, release, push, infrastructure, or credentialed steps
  locally.
- Five classes: code, test, flaky-infra, config, secret; only code and test change code;
  a config fix is applied only in direct use, after the user agrees.
- Re-run failed jobs at most once per check; a second failure is reported; never re-run a
  publish, release, or deploy job without the user.
- Never skip, delete, loosen, or xfail tests, or disable or edit a check, to go green.
- Update a test only when the new behaviour is documented in the PR, commits, or the
  active OpenSpec change.
- Caller mode commits and pushes without a prompt; the caller counts attempts.
- Summary keys: `outcome`, `head`, one `check:` line per check with `class`, `result`,
  `fix`.

## fixup

For one fix-class review comment, in a repository whose merge method is squash:

1. Make the code change in the working tree.
2. **Target:** `mb=$(git merge-base HEAD origin/<base>)`; list hunks with
   `git diff -U0 HEAD` and, for each, blame its old-side lines:
   `git blame -s -L <old-start>,+<old-count> $mb..HEAD -- <file>` (for added-only hunks,
   blame the neighbouring old-side lines). A branch sha is the target; boundary lines
   (`^<sha>`) come from the base.
   - one branch commit: target it.
   - several: one fixup per target (run `git reset -q` first so nothing else is staged),
     staging per file a version built from `HEAD` with only that target's lines changed
     (`git hash-object -w` + `git update-index --cacheinfo <mode from git ls-files -s>`;
   never `git apply` of `-U0`
     hunks, whose line numbers shift), splitting a hunk line by line when each
     changed line replaces one old line. A change that still cannot be separated, or a new
     file with no clear target, is not guessed: outcome `needs_decision` for that change.
   - base lines only: make a normal ep-commit commit instead (listed under `commits:`).
3. **Commit:** `git commit --fixup=<target-sha>` per target, containing only its hunks.
   Subject is exactly `fixup! <target subject>`; check it has no attribution.
4. **Push** with plain `git push`. Never autosquash, rebase, or force-push.
5. **Result fields**, as in `ep-fixup-summary`: `outcome` (`created`, `needs_decision`,
   or `nothing_to_do`), `head`, `fixups: <fixup-sha>-><target-sha>,...`,
   `commits: <sha>,...`, `rewritten: false`, `pushed`.

**Rules that must match** (`ep-fixup/SKILL.md`):

- Target is the branch commit (since the merge base) that introduced the corrected lines.
- Subject is exactly `fixup! <target subject>`, with no attribution.
- Lines from the base get a normal ep-commit commit, never a fixup.
- No autosquash, rebase, or force-push in caller mode; `rewritten: false`.
- Never `--force`; `--force-with-lease` only after confirmation in direct use.
- Caller mode never waits: an unresolvable target returns `needs_decision`, uncommitted.
- Summary keys: `outcome`, `head`, `fixups`, `commits`, `rewritten`, `pushed`.

## sync

Bring the PR base into the branch (for `BEHIND` and `DIRTY`) and audit it:

1. Clean tree required. `git fetch origin <base>`. Record, **before merging**:
   `mb=$(git merge-base HEAD origin/<base>)`, B = `git log $mb..origin/<base>` and
   `git diff -M $mb origin/<base>`, R = `git diff -M $mb HEAD`. If B is empty, the branch
   is up to date.
2. **Merge:** `git merge --no-ff --no-commit origin/<base>`. Resolve conflicts that keep
   both sides' intent; on contradictory decisions, `git merge --abort` and stop with
   `needs_decision` (show both versions). Commit the merge with a message file, no
   attribution.
3. **Audit** R's identifiers (names R defines, calls, imports, reads, or writes) against B,
   conflicts or not:
   1. symbols R uses that B renamed, removed, re-signatured (every affected call site), or
      changed in behaviour (returns, errors, side effects)
   2. contracts both touch: schemas, migrations, config keys, routes, API or type shapes
   3. new call sites in B of functions R modified
   4. tests in B covering files or identifiers R modified (run them)
   5. with an OpenSpec root and an active change only: base commits that edit, archive, or
      add specs for the change's capabilities (name the requirements on both sides);
      otherwise skip and do not mention OpenSpec

   Group interactions by file or identifier into clusters; classify each interaction as
   `needs-update`, `review`, or `no-impact`, with base commit, branch location, and reason.
4. **Adapt** each needs-update cluster in its own commit after the merge commit (ep-commit
   conventions, `fix`/`refactor`, body naming the base commit, no attribution). If more
   than one reasonable fix behaves differently, do not choose: stop with `needs_decision`
   and the options.
5. **Test** (full suite, or the subset covering the interactions; for a fork PR or an
   author without write access, only if the user allowed running PR code, else
   `tests: not_run`). Failures: outcome
   `needs_attention`, never `synced`.
6. **Report** the audit table (`# | Class | Check | Base commit | Branch location | Reason |
   Resolution`; every interaction, no-impact rows last; `No interactions found.` when
   empty), then the
   fields as in `ep-sync-summary`: `outcome`, `head`, `mode: merge`,
   `base: origin/<base>@<sha>`, `conflicts`, `audit: needs_update=<n> review=<n>
   no_impact=<n>`, `unresolved_needs_update`, `tests`, `pushed: false`. The loop pushes.

**Rules that must match** (`ep-sync/SKILL.md`):

- Merge only in caller mode; never rebase a pushed branch without explicit confirmation.
- Never `--force`; `--force-with-lease` only after a confirmed rebase, direct use only.
- Audit after every sync, conflicts or not, with the five checks and three classes.
- Adaptations are separate commits after the merge commit, with no attribution.
- Incompatible conflicts and ambiguous adaptations are never decided by the skill;
  caller mode returns `needs_decision` and nothing is pushed.
- Never report `synced` while tests fail.
- Summary keys: `outcome`, `head`, `mode`, `base`, `conflicts`, `audit`,
  `unresolved_needs_update`, `tests`, `pushed`.
