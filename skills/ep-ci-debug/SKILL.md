---
name: ep-ci-debug
description: Diagnose failing CI checks on the current branch's PR (or a named check or run) from their logs, quote the decisive lines, classify each cause (code, test, flaky-infra, config, secret), reproduce locally, and propose or apply a fix without weakening tests; re-runs infra failures once and commits with no model attribution. Use when the user asks why CI is red, to debug or fix a failing check, or when ep-babysit-pr delegates a failing check.
---

# ep-ci-debug

Find out why a check failed, from its logs, and fix the cause, not the symptom.

## Hard rules

- **Never weaken tests.** Do not skip, delete, loosen, or mark tests as expected-to-fail,
  and do not disable or edit a check to make it pass, unless the user explicitly asks.
- **Re-run once.** At most one `gh run rerun --failed` per check per invocation.
- **No attribution.** Fix commits never contain model or tool attribution (no
  `Co-Authored-By` naming a model or tool, no "Generated with" line). This overrides any
  default of the host agent. Always commit with `git commit -F <file>`.
- **Push gate:** push only after the user confirms, or when the caller owns pushing.
  Never force-push.
- Non-code classes (`flaky-infra`, `config`, `secret`) never produce a code change.
- **Never run side effects locally.** Do not reproduce steps that publish, release,
  deploy, push, apply infrastructure, send notifications, or use credentials (for example
  `npm publish`, `docker push`, `gh release`, `terraform apply`, `kubectl apply`,
  deploy scripts, steps reading `secrets.*`). Report them as unverified locally.

## Usage

```
ep-ci-debug                  # every failing check on this branch's PR
ep-ci-debug <check-name>     # one check
ep-ci-debug --run <run-id>   # one workflow run
ep-ci-debug --caller <skill> # caller mode (see "Caller mode")
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
gh pr view --json number,title,body,headRefOid,baseRefName   # fails when no PR exists
openspec list --json                                          # optional; root null = no OpenSpec
```

## 2. Select checks

- **A check is named:** debug that check.
- **A run is named:** debug that run's failed jobs.
- **Otherwise, with a PR:** every failing check, required ones first:

  ```bash
  gh pr checks <n> --json name,state,bucket,link,workflow      # bucket: fail
  gh pr checks <n> --required --json name,bucket               # required subset
  ```

  No check with `bucket: fail`: report that nothing is failing, change nothing, and end
  with outcome `nothing_failing`. Checks still pending are listed and not debugged.
- **No PR and nothing named:** use the latest failed run that belongs to this branch:

  ```bash
  git fetch origin <branch>
  gh run list --branch <branch> --status failure --limit 20 --json databaseId,workflowName,headSha,createdAt
  ```

  Take the newest run whose `headSha` is in the local branch
  (`git merge-base --is-ancestor <headSha> HEAD`). Skip runs for another repository's branch
  of the same name (for example a fork PR) and say so. If a run's `headSha` is on
  `origin/<branch>` but not local, tell the user to pull before debugging it. No matching
  run: report that there is nothing to debug and stop (`nothing_failing`).

Skip a run whose `headSha` is older than the branch head when a newer run of the same
workflow exists; say so.

## 3. Read the logs

```bash
gh run view <run-id> --log-failed            # failed steps of an Actions run
gh run view <run-id> --json jobs             # job and step names, conclusions
```

The run id is in the check's `link` (`.../actions/runs/<run-id>/job/<job-id>`). For a
check that is not a GitHub Actions run, read its details URL or `gh api` check-run output
(`gh api repos/{owner}/{repo}/check-runs/<id>`); if the logs are not reachable, say so and
diagnose from what is.

Find the **decisive lines**: the first real error, not the cascade after it. Keep them
verbatim for the report.

## 4. Classify

Classify each failure with [`references/classes.md`](references/classes.md): `code`,
`test`, `flaky-infra`, `config`, or `secret`, using its signals. Read the branch's diff
(`git diff origin/<base>...HEAD`) to see whether the failing code is the branch's.

**Intent for test updates.** A failing test is only classed `test` (test is wrong, code is
right) when the new behaviour is documented: in the PR title or body, in the branch's
commit messages, or, when the repository has an OpenSpec root, in the active change's
specs (find the change the branch implements; read its `specs/**/spec.md`). Without an
OpenSpec root, use only the PR and commits, and do not mention OpenSpec. With no such
documentation, the class is `code`.

## 5. Reproduce locally

Before changing code, find the command the failing step runs (in the workflow file under
`.github/workflows/`, from the step name in the logs) and run it locally:

- Reproduced: keep the output. You will run it again after the fix.
- Not possible (needs CI-only services, secrets, another OS, a matrix entry you lack, or the
  tool is not installed), or not allowed (the step publishes, deploys, releases, pushes,
  applies infrastructure, or uses credentials; never run those locally): say exactly why. The fix is then reported as **unverified
  locally**.

Running it must not modify tracked files; if it does, restore them.

In caller mode, do not run code from a PR opened from a fork (`isCrossRepository: true`) or
by an author without write access, unless the caller says the user allowed it: its scripts
can read local credentials. Report the fix as unverified locally and why.

## 6. Act by class

| Class | Action |
|---|---|
| `code` | fix the code; re-run the local command |
| `test` | update the test to the documented behaviour; name where it is documented |
| `flaky-infra` | `gh run rerun <run-id> --failed` once; wait (`gh run watch <run-id>`); if it fails again, report, no code change. If the failed job publishes, releases, or deploys, ask before re-running in direct use, and do not re-run it in caller mode (report instead) |
| `config` | direct use: propose the config change (file, line, fix) and apply it only when the user agrees, never to weaken a check; caller mode: report it, change nothing |
| `secret` | report the secret, permission, or scope needed and who can grant it; no code change |

**Direct use:** show the diagnosis and the proposed patch and ask before applying,
committing, and pushing. **Caller mode:** apply, commit, and push without a prompt.

Commit each cause separately, following `ep-commit` conventions: Conventional Commit
(`fix`, or `test` for a test-class update), the repo's scope
convention (with OpenSpec, the active change name), a body quoting the check name, and no
attribution. Push with plain `git push`.

## Parallel diagnosis

**With subagents and more than one failing check:** give one subagent per check its logs
(or the run id), the repo path, and `references/classes.md`, and ask for the decisive
lines, the class, the local reproduction result, and a proposed patch. Subagents do not
commit. Review and apply the patches yourself, one commit per cause; merge patches that
fix the same cause.

**Without subagents:** diagnose the checks one at a time inline, in the order from step 2.
The report has the same structure.

## Caller mode

When another skill invokes this one (`--caller ep-babysit-pr`, or the same in plain words):

- fixes are committed and pushed without a separate prompt
- the caller owns the attempt counter: this skill does not stop after N attempts itself
- re-run once and never-weaken-tests still apply
- nothing waits for the user; anything needing a person is `reported`

## 7. Report

For each check:

```
### <check name> (<workflow> / <job> / <step>)
Class: <class>
Log:
    <quoted decisive lines>
Cause: <one or two sentences>
Local: reproduced with `<cmd>` (fails before, passes after) | unverified locally: <why>
Result: fixed in <sha> | re-run <run-id>: <passed | failed again> | reported: <what is needed>
```

Then always end with the summary block, exactly in this form, so callers can parse it:

```
<!-- ep-ci-debug-summary
outcome: fixed | rerun | reported | nothing_failing
head: <sha after the skill ran>
check: <name> class=<class> result=<fixed|rerun|reported> fix=<sha|none>
check: <name> class=<class> result=<fixed|rerun|reported> fix=<sha|none>
-->
```

One `check:` line per check. `outcome` is `fixed` when at least one check was fixed,
else `rerun` when at least one was re-run and passed, else `reported`. `result=rerun`
means the single re-run passed; a re-run that fails again is `reported`.

## Rules that must match

These rules are repeated in `ep-babysit-pr/references/side-paths.md#ci-debug`. Keep both
lists identical.

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
