# Failure classes

Every failing check gets exactly one class, decided from the quoted log lines and the
branch's diff rather than the check's name. When signals point to two classes, take the
one whose action changes less: `secret` over `config`, `config` over `code`, and
`flaky-infra` only when the same commit has passed the same job before or the error is
clearly outside the repository. When no class fits, report the check as `reported` with
the quoted lines and the open question.

| Class | Signals | Action |
|---|---|---|
| **code** | a compile, type, lint, or build error in files the branch changed; a test fails because the code under test is wrong; a stack trace through branch code; the failure reproduces locally | reproduce locally, fix the code, re-run the failing command, commit, push (gated) |
| **test** | the test asserts behaviour the branch intentionally changed; a fixture or snapshot is out of date because of an intended change; the code matches the documented intent but the test does not | update the test **only** when the new behaviour is documented (see [intent](#intent-for-test-updates)); say where it is documented. Otherwise treat as `code` |
| **flaky-infra** | network timeouts, registry or package mirror errors (`ECONNRESET`, `503`, `rate limit`), runner lost or out of disk, cancelled by the platform, a test that passes locally and on re-run with no code change, failure in a step the branch does not touch | re-run only the debugged job **once** (see [re-run](#re-run)); if it fails again, report and change nothing |
| **config** | workflow YAML errors, a missing or wrong tool version, a step references a path, script, or job that does not exist, cache-key or matrix mistakes, a required check name no workflow produces | report the cause and the exact config change needed (file, line, fix); apply it only in direct use when the user agrees, and only to repair the check, never to weaken it; in caller mode change nothing |
| **secret** | `secret not found`, empty env var where a secret is expected, `401`/`403` from a registry or cloud API, `Resource not accessible by integration`, missing `permissions:` scope, fork PRs without secrets | report what is needed (secret name, scope, or permission, and who can grant it); keep the code and the step as they are |

Only `code` and `test` produce a code change.

## Intent for test updates

A failing test is classed `test` (test is wrong, code is right) only when the new
behaviour is documented: in the PR title or body, in the branch's commit messages, or,
when the repository has an OpenSpec root, in the active change's specs (find the change
the branch implements; read its `specs/**/spec.md`). Without an OpenSpec root, use only
the PR and commits, and mention OpenSpec nowhere. With no such documentation, the
class is `code`.

## Re-run

At most one re-run per check per invocation, only for `flaky-infra`, of the debugged job
alone: `gh run rerun <run-id> --job <job-id>`, where `<job-id>` is the job's `databaseId`
from `gh run view <run-id> --json jobs --jq '.jobs[] | {name, databaseId}'`, not the
number in the check URL. Never `--failed`, which re-runs every failed job in the run.
Wait with `gh run watch <run-id>`. A second failure is reported, not retried.

GitHub also re-runs every job downstream of the debugged one (directly or through other
jobs' `needs:`). When that job or any job downstream of it publishes, releases, or
deploys: in direct use, re-run only after the user agrees; in caller mode, report instead
of re-running.

## Tests stay as strong as they are

A fix makes the check pass by fixing the cause. It never skips, deletes, loosens, or marks
tests as expected-to-fail (`skip`, `xfail`, `.only`, `it.skip`, `@Disabled`, lowered
thresholds, broadened matchers, deleted assertions), and never disables, edits, or makes
optional a check to make it pass, unless the user explicitly asks. A `test`-class update
changes the expected value to the documented new behaviour; it keeps the check.
