# Spec Delta

## Purpose

Audits an app or repository the way a senior QA engineer would: it exercises setup, build, checks, tests, the running app, edge cases, and the docs, and writes an audit file of verified, reproducible problems.

## ADDED Requirements

### Requirement: Audit targets
The skill SHALL audit the whole repository at its current checkout by default, SHALL accept one path inside the repository to limit the audit to that part (for example one package of a monorepo), and SHALL accept `--url <url>` to also probe an already running app at that URL.

#### Scenario: Default target
- **WHEN** the user invokes `ep-qa` with no arguments inside a repository
- **THEN** the skill audits the repository from its root, including uncommitted changes in the working tree

#### Scenario: Path target
- **WHEN** the user invokes `ep-qa packages/api`
- **THEN** the skill discovers commands and runs probes for that package only, and the report names `path:packages/api` as the target

#### Scenario: Path outside the repository
- **WHEN** the given path does not exist or is outside the repository
- **THEN** the skill stops before running anything and says the path is not auditable

### Requirement: Test plan from project sources
Before running anything, the skill SHALL build a test plan from the project's own sources: manifests, task runner and package scripts, CI workflow steps, and documentation. Each plan item SHALL name its area and the exact command or probe, and SHALL say where it came from.

#### Scenario: Documented commands become plan items
- **WHEN** the README tells users to run `make setup` and then `make test`
- **THEN** the plan contains both commands, each citing the README as its source

#### Scenario: No runnable commands
- **WHEN** the project defines no command for setup, build, checks, tests, or running
- **THEN** the plan says so, the audit continues with documentation checks only, and the report lists the missing commands under "Not covered"

### Requirement: Confirmation before running project commands
The skill SHALL show the test plan and run project commands only after the user confirms it, or when the user passed `--yes`. When it can neither ask nor rely on `--yes`, it SHALL run no project command and SHALL report every planned command as not covered.

#### Scenario: User confirms the plan
- **WHEN** the user confirms the plan shown by the skill
- **THEN** the skill runs exactly the confirmed commands and probes, and no others

#### Scenario: User declines
- **WHEN** the user declines the plan
- **THEN** the skill runs no project command, still writes the audit file from the checks that need no execution, and lists the planned commands under "Not covered"

#### Scenario: Pre-approved with --yes
- **WHEN** the user runs `ep-qa --yes`
- **THEN** the skill shows the plan and runs it without waiting for an answer

### Requirement: Commands never run
The skill SHALL NOT run, even with `--yes`, commands that deploy, publish, release, push, change non-local services or databases, need credentials or secrets, or delete files outside the project's build and cache output. It SHALL NOT install global tools or tools the project does not declare.

#### Scenario: Deploy script in the project
- **WHEN** the project's package scripts include `deploy` and `release`
- **THEN** neither appears in the plan as a command to run, and the report lists them under "Not covered" with the reason

#### Scenario: Undocumented credential-like variable
- **WHEN** the app needs an environment variable named like a credential, such as `PAYMENT_API_KEY`, that no doc or example env file provides
- **THEN** the skill never fills it with a placeholder, plans no placeholder start, and lists the start and its probes under "Not covered" naming the variable

#### Scenario: Missing toolchain
- **WHEN** the project needs a tool that is not installed on the machine, such as `cargo`
- **THEN** the skill does not install it, and lists the affected plan items under "Not covered"

### Requirement: Exercise the project
Within the confirmed plan, the skill SHALL install dependencies with the project's lockfile when it has one, build, run linters, type checkers, and tests, start the app when the project has one, probe its main flows and edge cases (empty, invalid, very large, and unicode input, and missing configuration), and stop every process it started before it ends.

#### Scenario: CLI app
- **WHEN** the project is a command-line tool
- **THEN** the skill runs its help output, the documented examples, and invalid or empty input, and records crashes, wrong exit codes, and unhelpful errors as candidates

#### Scenario: Web server
- **WHEN** the project starts an HTTP server
- **THEN** the skill starts it locally, waits until it answers, requests each documented route that passes the action-route filter plus a missing route and malformed input on those routes, records server errors and crashes as candidates, and stops the server at the end

#### Scenario: Local action route not probed
- **WHEN** a locally started app documents `GET /api/cron/send-digest`
- **THEN** the skill sends no request to that route with any method or body, and the report lists it under "Not covered" as `not probed: may change state (GET /api/cron/send-digest)`

#### Scenario: Local write route still probed
- **WHEN** a locally started app documents `POST /api/greet` and neither its path nor its doc text names an action
- **THEN** the skill sends it malformed bodies (invalid JSON, wrong types, missing fields) and records a 500 as a candidate

#### Scenario: Start needs an undocumented variable
- **WHEN** the documented start fails because a non-credential environment variable is missing that no doc mentions
- **THEN** the skill stops the documented start's process and checks its port is free before running a second start with that variable set to a harmless placeholder, and the two starts never run at the same time

#### Scenario: Server cannot start
- **WHEN** the app needs a service the skill cannot run locally, such as a remote database
- **THEN** the skill does not start it, and lists the runtime probes under "Not covered" with the reason

### Requirement: Documentation against behavior
The skill SHALL check documented setup steps, commands, flags, environment variables, and examples against the project's observed behavior, and SHALL report each mismatch it observes as a docs finding.

#### Scenario: README flag does not exist
- **WHEN** the README documents `--verbose` and running the tool with it fails with "unknown option"
- **THEN** the report has a docs finding with the README line, the command run, and its output

#### Scenario: Undocumented required variable
- **WHEN** the app fails to start without an environment variable that no doc or example env file mentions, and its output names the variable
- **THEN** the report has a docs finding for the undocumented requirement

#### Scenario: Variable read in code that never caused a failure
- **WHEN** the code reads an environment variable that no doc mentions, but nothing the skill ran failed for lack of it
- **THEN** the report has no finding for that variable

### Requirement: Read-only probing of a URL
With `--url`, the skill SHALL send only `GET` and `HEAD` requests to that URL and paths under it, SHALL NOT submit forms, sign in, or send any other method, SHALL request a documented route only when it is clearly read-only (documented as `GET` or `HEAD`, passes the action-route filter, and needs no token, signature, or id parameter), and SHALL send state-changing requests only to an app it started locally and never to an action route.

#### Scenario: Action route on a live app
- **WHEN** the user runs `ep-qa --url https://staging.example.com` and the docs give `GET /api/cron/send-digest`
- **THEN** the skill sends no request to that route, and the report lists it under "Not covered" as `not probed on --url: may change state (GET /api/cron/send-digest)`

#### Scenario: Probing a live app
- **WHEN** the user runs `ep-qa --url https://staging.example.com`
- **THEN** every request sent to that host is a `GET` or `HEAD`, and flows that need writes are listed under "Not covered"

### Requirement: Action-route filter
The skill SHALL apply one action-route filter, with one shared action-word list, to the documented routes of a locally started app and of a `--url` app. A route SHALL fail it, whatever its method, when its path or doc text names an action from the list or its docs say it changes, sends, schedules, or notifies anything outside the app. A route that fails it SHALL NOT be requested with any method or body.

#### Scenario: Failed route listed as not covered
- **WHEN** a documented route of a locally started app fails the filter
- **THEN** the report lists it under "Not covered" as `not probed: may change state (<METHOD> <route>)`, and routes that pass keep the local probes, including malformed bodies on documented write routes

#### Scenario: Action word in the doc text only
- **WHEN** a locally started app documents `POST /api/preview` whose doc text says it emails the digest to subscribers
- **THEN** the skill sends no request to that route, and lists it under "Not covered" as `not probed: may change state (POST /api/preview)`

### Requirement: Verified, reproducible findings
Each reported finding SHALL be observed by the skill and reproduced by running its reproduction steps again. Each SHALL include an id, severity, area, title, location (file and line, command, or URL), reproduction steps, expected and actual results, and quoted evidence. Code reading alone SHALL NOT produce a finding.

#### Scenario: Reproduced failure
- **WHEN** a test fails, and fails again when re-run alone
- **THEN** the report has one finding with the exact command, the failing assertion quoted from the output, and the test's file and line

#### Scenario: Suspicion from code only
- **WHEN** the skill suspects a bug from reading the code but no probe it ran shows it
- **THEN** the suspicion is not reported as a finding; it may appear under "Not covered" as worth testing

### Requirement: Flaky results
When a failure does not occur again on re-run, the skill SHALL report it as flaky, with the output of both runs as evidence, and SHALL NOT report it as a deterministic failure.

#### Scenario: Test passes on re-run
- **WHEN** a test fails in the full suite and passes when re-run
- **THEN** the report lists it as a flaky finding with both runs quoted

### Requirement: Environment problems are not defects
A failure caused only by the auditing machine (a missing tool, no network, a port in use, missing credentials) SHALL be listed under "Not covered" and SHALL NOT be reported as a finding, unless the project's docs fail to state the requirement, which is a docs finding.

#### Scenario: Port already in use
- **WHEN** the dev server fails because its port is taken by another process
- **THEN** the skill reports the runtime probes as not covered with that reason, and creates no finding

### Requirement: Severity by impact
The skill SHALL rate each finding critical, major, or minor by its impact on users and developers: critical when the project cannot be set up, built, or started, a core flow is broken, or data is lost or exposed; major when a feature or documented command is wrong in a realistic case, tests fail, or a check fails; minor for real but low-impact problems.

#### Scenario: Build fails
- **WHEN** the documented build command fails on a clean checkout
- **THEN** the finding is critical

#### Scenario: Misleading error message
- **WHEN** invalid input is rejected correctly but with a misleading message
- **THEN** the finding is minor

### Requirement: Audit file
The skill SHALL write the report to `qa-audit.md` at the repository root, or to the path given with `--out`. It SHALL overwrite an existing file only when an earlier `ep-qa` run wrote it, and otherwise SHALL write to a dated name next to it and say so. It SHALL NOT overwrite a dated report; when the dated name is taken it SHALL add a numeric suffix. It SHALL NOT commit the file.

#### Scenario: Default output
- **WHEN** an audit completes and no `qa-audit.md` exists
- **THEN** the skill writes `qa-audit.md` at the repository root and leaves it uncommitted

#### Scenario: Existing file not written by the skill
- **WHEN** `qa-audit.md` exists and was not written by `ep-qa`
- **THEN** the skill leaves it untouched, writes the report to a dated file name in the same folder, and names that path in its output

#### Scenario: Dated name already taken
- **WHEN** a dated report for the current minute already exists and the default `qa-audit.md` was not written by `ep-qa`
- **THEN** the skill writes the report with a `-2` suffix before `.md` and leaves both existing files untouched

#### Scenario: Custom path
- **WHEN** the user passes `--out docs/qa/report.md`
- **THEN** the report is written to that path

### Requirement: Read-only toward source
The skill SHALL NOT edit source, test, configuration, documentation, or lock files, and SHALL NOT add files to the repository, apart from writing the audit file and its run record. The report SHALL list every tracked or untracked file that the confirmed commands created or changed, and the skill SHALL leave those changes in place.

#### Scenario: Tests rewrite a snapshot
- **WHEN** running the confirmed test command changes a tracked snapshot file
- **THEN** the skill does not revert it and lists the file under the report's changed files

### Requirement: Coverage and no all-clear claim
The report SHALL list under "Not covered" every plan item that was skipped, blocked, or not run, each with its reason, and SHALL NOT state that the project works, has no bugs, or passed QA.

#### Scenario: No findings
- **WHEN** verification leaves no findings
- **THEN** the report says no problems were found in what was exercised, lists what was exercised and what was not covered, and makes no claim that the project works

### Requirement: Secrets kept out of the report
The skill SHALL NOT copy secret values (tokens, passwords, keys, values from env files) into the report or its output, and SHALL redact them in quoted evidence.

#### Scenario: Token in command output
- **WHEN** a command prints an API token as part of an error
- **THEN** the quoted evidence shows the token redacted

### Requirement: No GitHub writes
The skill SHALL NOT push, commit, merge, open issues or PRs, or post comments.

#### Scenario: Audit with findings
- **WHEN** an audit finds critical problems
- **THEN** the skill writes the audit file and prints the summary, and makes no GitHub or git history changes

### Requirement: Summary block
The skill SHALL end its output with a fenced `ep-qa-summary` block stating the target, the commit audited and whether the tree was dirty, the audit file path, the finding counts by severity, the plan item counts (run, passed, failed, skipped, not covered), the counts of earlier findings still failing, fixed, and not re-checked, the counts of findings with and without a proposed regression test, the run record path or `none`, whether `--full` was given, and whether the plan was confirmed.

#### Scenario: Summary present
- **WHEN** an audit completes, including one where the user declined the plan
- **THEN** the output ends with an `ep-qa-summary` block that another skill can parse

### Requirement: Works without OpenSpec
When the repository has an OpenSpec root, the skill SHALL also use the main specs' scenarios as expected behavior. Without one, its behavior SHALL NOT depend on OpenSpec and its output SHALL NOT mention OpenSpec.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the audit runs normally and neither the report nor the output mentions OpenSpec

#### Scenario: Repository with OpenSpec
- **WHEN** a main spec scenario says an empty name is rejected and the app accepts it
- **THEN** the report has a finding citing that spec scenario as the expected result

### Requirement: Subagents optional
The skill MAY use subagents for work that shares no running state, such as reading docs and specs into expected behavior or investigating a finding's cause. It SHALL run project commands and probes from one context, and SHALL produce the same report without subagents.

#### Scenario: Agent without subagents
- **WHEN** the agent cannot spawn subagents
- **THEN** the skill does every step in one context and produces the same audit file and summary

### Requirement: Run record
After a run that executed at least one check, the skill SHALL write a machine-readable record beside the audit file, named after the audit file's stem with `.state.json` (for example `qa-audit.state.json`). It SHALL hold each check's result, the commit sha it ran on, its dependent paths and a fingerprint of their contents, and each finding's id, reproduction, and status, and no command output or secret values. The skill SHALL NOT commit the record or add it to `.gitignore`.

#### Scenario: First run writes a record
- **WHEN** an audit with a confirmed plan completes and no record exists
- **THEN** `qa-audit.state.json` exists next to `qa-audit.md`, is uncommitted, and the git history is unchanged

#### Scenario: Declined plan keeps the record
- **WHEN** the user declines the plan on a run that has a record from an earlier run
- **THEN** the record is unchanged after the run

### Requirement: Unusable records
A record that does not parse, is not an `ep-qa` record, or belongs to another target SHALL be treated as absent, and the report SHALL say why. A file at the record path that is not a valid `ep-qa` record SHALL be left untouched.

#### Scenario: Corrupt record
- **WHEN** `qa-audit.state.json` exists but does not parse as JSON
- **THEN** the skill runs every check, skips none, leaves that file untouched, and the report notes that the previous record was ignored because it is corrupt

#### Scenario: Foreign record
- **WHEN** `qa-audit.state.json` is valid JSON that was not written by `ep-qa`
- **THEN** the skill treats it as absent, leaves it untouched, and the report notes that it is not an `ep-qa` record

### Requirement: Skip unchanged checks
With a usable record, the skill SHALL skip a plan item only when the same check passed last time and none of these changed since: the working-tree contents of its dependent paths (uncommitted, added, and removed files included), the lockfiles, manifests, and toolchain versions, and its own and its prerequisites' plan entries. The report SHALL list it as "skipped, unchanged since <sha>", the sha being the commit it last ran on.

#### Scenario: Second run on an unchanged checkout
- **WHEN** the skill runs twice in a row on the same checkout with no file changed
- **THEN** on the second run every check that passed on the first is not executed and is listed as "skipped, unchanged since <sha>" with the first run's commit

#### Scenario: Uncommitted edit invalidates checks
- **WHEN** a source file under the target is edited without committing between two runs
- **THEN** the checks that depend on that file run again on the second run

#### Scenario: Lockfile change
- **WHEN** the project's lockfile or manifest changed since the last run
- **THEN** no check that depends on it is skipped

#### Scenario: Plan entry changed
- **WHEN** the command of a plan item changed since the last run, for example a different test script in the Makefile
- **THEN** that item and every item depending on it run again

### Requirement: Checks never skipped
The skill SHALL NOT skip a check that failed or was flaky on its last run, or a probe against `--url`, and SHALL run a skipped-eligible prerequisite (install, build, start) when an item that runs needs it.

#### Scenario: Probe changed behind a skippable start
- **WHEN** the server start passed before and is unchanged, but one probe that needs the running server must run
- **THEN** the start runs too, and is not reported as skipped

#### Scenario: Earlier failure
- **WHEN** a test command failed on the last run and nothing changed since
- **THEN** it runs again

### Requirement: Re-check earlier findings
On a run with a usable record, the skill SHALL re-run the reproduction of every open finding from the record, whatever its fingerprints say, and SHALL mark each as still failing, keeping its id, or fixed, naming the commit it was found fixed at. A finding whose reproduction cannot run SHALL stay open and be listed under "Not covered" with the reason. New findings SHALL take ids after the highest id in the record.

#### Scenario: One finding fixed, one still failing
- **WHEN** one of two earlier findings was fixed in the working tree since the last run
- **THEN** the report lists the fixed one under "Fixed since last run" with the current commit, and the other as still failing with its original `QA-<n>` id and fresh evidence

### Requirement: Full re-run
With `--full`, the skill SHALL ignore the run record: it SHALL skip no check, SHALL number findings afresh, and SHALL replace the record at the end.

#### Scenario: Full run after an unchanged checkout
- **WHEN** the user runs `ep-qa --full` on a checkout whose record would allow skips
- **THEN** every check runs, none is listed as skipped, and the summary says `full: true`

### Requirement: Regression test proposals
For each reproduced finding where a sensible test exists, the audit file SHALL include a proposed regression test in the project's own test framework and conventions, the path where it would go, and quoted evidence that it fails today for the finding's reason. When no sensible test exists (an environment or infrastructure cause, a flaky external dependency, a visual-only problem), the finding SHALL say why. Proposed tests SHALL NOT contain secret values.

#### Scenario: Crash on empty input with pytest
- **WHEN** a Python CLI tested with pytest crashes with a traceback on empty input, and the finding reproduces
- **THEN** the finding includes a pytest test at a path following the project's test layout and the failing output of that test

#### Scenario: No sensible test
- **WHEN** a finding is caused by a flaky dependency on an external service
- **THEN** the finding has no proposed test and states why

#### Scenario: Finding involving a credential
- **WHEN** reproducing a finding needs an API token value
- **THEN** the proposed test uses a placeholder value and the audit file contains no real token

### Requirement: Proposed tests stay outside the repository
The skill SHALL write and run a proposed regression test only in a scratch copy outside the repository, deleted at the end of the run, and SHALL NOT write it into the repository's working tree or add it to the project. Running proposed tests SHALL require the confirmed plan.

#### Scenario: Proposed test not in the working tree
- **WHEN** a Python CLI tested with pytest crashes with a traceback on empty input, and the finding reproduces
- **THEN** the failing output comes from a scratch copy, the proposed path does not exist in the repository after the run, `git status` shows no new test file, and the scratch copy is gone

#### Scenario: Plan declined
- **WHEN** the user declines the plan
- **THEN** no proposed test is run, and any test proposed is marked as not run because the plan was not confirmed
