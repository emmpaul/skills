# Audit reference

Finding shape, areas, severity, verification, redaction, wording, and the report template.
Read in step 8 (verify) and step 9 (report). The run record and how earlier findings
carry over are in `record.md`.

## Finding shape

Every finding in the report has every field below:

```
id:        QA-<n>: kept from the run record for an earlier finding, else the next number
severity:  critical | major | minor
area:      setup | build | lint | types | tests | runtime | docs
title:     one line naming what is wrong, with the command or route
where:     file:line (script entry, test, source line), the command, or the URL
steps:     numbered, exact commands or requests from the target's directory, enough
           for a person to reproduce it from a fresh shell
expected:  what should happen, with its source (README.md:42, a spec scenario,
           the tool's own --help, or the general rule it breaks: "no 500 on bad input")
actual:    what happened: exit code, status, the message
evidence:  the decisive output lines, quoted, secrets redacted
notes:     optional: likely cause (file:line), or both runs for a flaky finding
status:    new | still failing (first seen <sha>)
```

A finding comes only from something the audit observed (command output, an HTTP
response, a crash) and reproduced in step 8. **Code reading alone never makes a finding.**
A suspicion from code that no probe showed goes under "Not covered" as
`worth testing: <what> (<file>:<line>)`.

For a failing test, `where` is the test's file and line, `steps` is the command that runs
that test alone, and `evidence` quotes the failing assertion.

With an OpenSpec root, a result that contradicts a main spec scenario's THEN cites the
spec file and scenario name in `expected`.

## Areas

| Area | Covers |
|---|---|
| `setup` | dependency install, env and config setup, documented setup steps |
| `build` | compile, bundle, package |
| `lint` | configured linters and formatters in check mode |
| `types` | configured type checkers |
| `tests` | the project's test suites, flaky tests included |
| `runtime` | starting the app and probes against it |
| `docs` | documented commands, flags, env variables, and examples that do not match behavior, and requirements the docs leave out |

A failure of a command the README documents is a `docs` finding when the doc is what is
wrong (a flag that never existed, a renamed script), and a finding of the command's own
area when the code is what is wrong.

## Severity by impact

| Severity | Meaning | Examples |
|---|---|---|
| critical | The project cannot be set up, built, or started from its docs, a core flow is broken, or data is lost or exposed. | install or build fails on a clean checkout; app crashes on start, including from an undocumented required env variable; main command crashes on documented input; secret printed in normal output |
| major | Wrong in a realistic case, or a check the project defines fails. | failing test; lint or typecheck errors in a configured check; documented command or flag fails; 500 on malformed input; crash with a stack trace on empty input to a secondary command; flaky test; undocumented env variable that only a secondary feature needs |
| minor | Real but low impact. | invalid input rejected correctly but with a misleading message; doc typo in a flag name with an obvious fix; warning noise from the project's own code |

Rank findings by severity, then area in the table order above, then plan order. Ids do
not follow the rank and are never renumbered: an earlier finding still failing keeps its
`QA-<n>` from the run record, and each new finding takes the next number after the
highest id in the record (fixed ones included), in ranked order. Without a usable record,
or with `--full`, new findings are numbered `QA-1`, `QA-2`, ... in ranked order.

## Verification

Re-run each candidate's reproduction alone (the single test, the single command, the
single request), then classify it:

| Outcome | When | Goes to |
|---|---|---|
| **reproduced** | it fails again the same way | a finding |
| **flaky** | it failed once and passed on the re-run: re-run once more and quote every run | a finding marked `flaky` in its title, severity at most major, never reported as a deterministic failure |
| **environment** | the cause is the auditing machine: tool missing, port in use, no network, missing credentials, a service not running | "Not covered" with that reason, no finding; but when the docs do not state the requirement (an env variable, a service, a tool version), a `docs` finding |
| **refuted** | it does not happen again and the audit explains the first failure (the probe sent bad input on purpose and the app rejected it correctly, an earlier item left state behind) | dropped |

Before keeping a candidate, try to disprove it: re-read the doc or spec line it relies on,
check the command was run from the right directory with the documented env, and check an
earlier plan item did not cause it. Deduplicate: one root cause is one finding; mention
the other symptoms in its evidence.

## Secrets

Never copy secret values into the report or the output: tokens, passwords, API keys,
private keys, connection strings with credentials, cookies, and every value from a `.env`
file. Name the variable and replace the value with `[REDACTED]` in quoted evidence:
`Authorization: Bearer [REDACTED]`, `postgres://app:[REDACTED]@db:5432/app`. Never quote
a `.env` file; example env files are quoted by variable name only.

## Coverage

"Not covered" lists every plan item that did not run or whose result could not be
judged, each with its reason: never run (what it does), tool not installed, blocked by
P<n>, not confirmed, dropped by the user, environment (the cause), service not available
locally, needs a browser, needs writes to a `--url` app. It also lists project kinds with
no command at all ("no lint command defined") and code suspicions as `worth testing`.

## Wording

The report states what was exercised and what was found. It never says the project
works, is bug-free, is production-ready, or passed QA. With no findings, the Summary
says: "No problems found in what was exercised." followed by what was exercised, and the
"Not covered" section still lists what was not.

## Report template

The first line is the marker. An existing file at the report path is overwritten only
when its first line starts with `<!-- ep-qa audit:`; otherwise the report goes to
`qa-audit-<YYYY-MM-DD-HHMM>.md` in the same folder, with `-2`, `-3`, ... before `.md` when
that name is taken too (a dated file is never overwritten).

~~~
<!-- ep-qa audit: <full head sha> <ISO 8601 date> -->
# QA audit: <repo name> (<repo | path:<p>>[, url <u>])

Commit <short sha>, tree <clean | dirty>. Audited <date>. Plan <confirmed | not confirmed>.

## Summary
<critical n, major n, minor n>. <one line on what was exercised: for example "Ran install,
build, lint, and tests; started the server and probed 6 routes.">

## Findings
### QA-1 [critical] build: `npm run build` fails on a clean checkout
- Where: package.json:12 (`build` script); src/index.ts:40
- Steps to reproduce:
  1. npm ci
  2. npm run build
- Expected: build completes (README.md:18, "Getting started")
- Actual: exit 2, `TS2307: Cannot find module './config'`
- Evidence:
  ```
  src/index.ts(40,22): error TS2307: Cannot find module './config'
  ```
- Notes: src/config.ts is untracked in .gitignore:7
- Status: new
- Regression test: <proposed path> (<framework>)
  ```<lang>
  <test code, no secrets>
  ```
  Fails today: <quoted decisive lines from the scratch run>
  (or: No test proposed: <reason>)

### QA-4 [major] tests: `test_parse_dates` is flaky
- Where: tests/test_dates.py:31
- Steps to reproduce:
  1. .venv/bin/pytest tests/test_dates.py::test_parse_dates
- Expected: passes on every run
- Actual: failed in the full suite, passed on both re-runs
- Evidence: run 1 `AssertionError: ...`; run 2 `1 passed`; run 3 `1 passed`
- Status: still failing (first seen 1a2b3c4)
- Regression test: No test proposed: flaky by nature (timing)

## Fixed since last run
- QA-3 [major] tests: `test_slugify_unicode` fails, fixed at 5d6e7f8 (reproduction now passes)

## Plan and results
| Id | Area | Command or probe | Source | Result |
|---|---|---|---|---|
| P1 | setup | `npm ci` | README.md:15 | passed (34 s) |
| P2 | build | `npm run build` | README.md:18 | failed: QA-1 |
| P4 | tests | `npm test` | package.json:10 | skipped, unchanged since 1a2b3c4 |
| P7 | setup | `npm run deploy` | package.json:14 | not covered |

## Not covered
- P7 `npm run deploy`: never run (deploys)
- Runtime probes: need PostgreSQL at DATABASE_URL, not available locally
- worth testing: unchecked index in src/parse.ts:88 (no probe reached it)

## Files changed by the audit
- dist/ (created), coverage/ (created), tests/__snapshots__/x.snap (modified)

## Run record
qa-audit.state.json, 1 check skipped
~~~

Omit "Findings" subsections when there are none and write the no-findings line in the
Summary. Omit "Fixed since last run" when no earlier finding was fixed. With no changed
files, write `- none`; the audit file and the run record are never listed there. Results
are `passed`, `failed: QA-<n>` (or `failed: environment`, `failed: refuted` when
verification cleared it), `skipped, unchanged since <short sha>`, or `not covered`.

"Run record" names the record written this run and how many checks were skipped, or why
the previous one was ignored: `previous record ignored: <corrupt | not an ep-qa record |
other target | --full>`, and for a corrupt or foreign file, that no record was written
and to move or delete it. On a first run: `<record path>, first run`. When the plan was
not confirmed: `<record path> unchanged (plan not confirmed)`.
