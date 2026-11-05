# Failure classes

Every failing check gets exactly one class. Decide from the quoted log lines and the
branch's diff, not from the check's name. When signals point to two classes, prefer the
one whose action changes less: `secret` over `config`, `config` over `code`, and
`flaky-infra` only when the same commit has passed the same job before or the error is
clearly outside the repository.

| Class | Signals | Action |
|---|---|---|
| **code** | a compile, type, lint, or build error in files the branch changed; a test fails because the code under test is wrong; a stack trace through branch code; the failure reproduces locally | reproduce locally, fix the code, re-run the failing command, commit, push (gated) |
| **test** | the test asserts behaviour the branch intentionally changed; a fixture or snapshot is out of date because of an intended change; the code matches the documented intent but the test does not | update the test **only** when the new behaviour is documented in the PR body, commits, or the active OpenSpec change; say where it is documented. Otherwise treat as `code` |
| **flaky-infra** | network timeouts, registry or package mirror errors (`ECONNRESET`, `503`, `rate limit`), runner lost or out of disk, cancelled by the platform, a test that passes locally and on re-run with no code change, failure in a step the branch does not touch | re-run the failed jobs **once** (`gh run rerun <run-id> --failed`); if it fails again, report and change nothing. If the failed job, or any job that `needs:` it (`--failed` re-runs those too), publishes, releases, or deploys, re-run only after the user agrees (never in caller mode) |
| **config** | workflow YAML errors, a missing or wrong tool version, a step references a path, script, or job that does not exist, cache-key or matrix mistakes, a required check name no workflow produces | report the cause and the exact config change needed (file, line, fix); apply it only in direct use when the user agrees, never to weaken a check; in caller mode change nothing |
| **secret** | `secret not found`, empty env var where a secret is expected, `401`/`403` from a registry or cloud API, `Resource not accessible by integration`, missing `permissions:` scope, fork PRs without secrets | report what is needed (secret name, scope, or permission, and who can grant it); never change code, never remove the step |

## Rules for every class

- **Re-run once.** At most one `gh run rerun --failed` per check per invocation, and only
  for `flaky-infra`, and never for a publish, release, or deploy job without the user. A
  second failure is reported, not retried.
- **Never weaken tests.** Do not skip, delete, loosen, or mark tests as expected-to-fail
  (`skip`, `xfail`, `.only`, `it.skip`, `@Disabled`, lowered thresholds, broadened
  matchers, deleted assertions), and do not disable, edit, or make optional a check to make
  it pass, unless the user explicitly asks. A `test`-class update changes the expected value
  to the documented new behaviour; it never removes the check.
- A class other than `code` or `test` never produces a code change.
- When no class fits, report the check as `reported` with the quoted lines and the open
  question.
