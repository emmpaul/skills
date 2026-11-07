# Design

## Context

Each `ep-*` skill is a self-contained folder with `SKILL.md`, a synced `scripts/context.sh`, and optionally `references/`. `scripts/sync-shared.sh` and `scripts/check-shared.sh` loop over every `skills/*/` folder that has a `SKILL.md`, so the new skill must ship the probe copy. CI already runs `check-shared.sh`, `bash -n` over `skills/*/scripts/*.sh`, and `openspec validate --all --strict`, so a new skill folder needs no CI change.

The closest existing skills set the conventions this one follows:
- `ep-review` and `ep-a11y`: verified findings that survive a disproval attempt, a finding shape and severity scale in `references/`, a fenced `ep-<name>-summary` block at the end, no attribution.
- `ep-a11y`: running a project's own command is running code, so it asks first and shows the exact command, lists files the command wrote, never installs tools, and never claims conformance.
- `ep-ci-debug`: never reproduces publish, deploy, release, push, infrastructure, or credentialed steps locally.

See proposal.md for why, and specs/ep-qa/spec.md for the required behavior.

## Goals / Non-Goals

**Goals:**
- Every finding can be reproduced by a person from the audit file alone: exact commands, inputs, expected and actual results, quoted output.
- The audit is honest about coverage: what was exercised, what was not, and why.
- Running the audit is safe on a developer's machine: one confirmation covers every project command, dangerous commands are never planned, and started processes are stopped.
- A second run does not repeat work whose result cannot have changed: a check that passed and whose inputs are unchanged is skipped, while every earlier finding is checked again, so the audit file tracks progress across runs.
- Each reproduced finding comes with a regression test the team can add, in the project's own framework, shown to fail today, so the bug cannot quietly come back.

**Non-Goals:**
- Auditing a diff, branch, or PR. `ep-review` and `ep-a11y` cover changes; `ep-qa` audits the project as it stands.
- Fixing anything, adding tests to the repository, opening issues, or commenting on GitHub. A later change can add `--issue`; fixes go through `ep-ci-debug`, `tdd`, or by hand.
- Browser-driven UI testing, load or performance testing, penetration testing, and accessibility audits (`ep-a11y`). UI flows that need a browser go under "Not covered" with what to check by hand.
- Installing toolchains, test frameworks, or browsers in the target project or on the machine.

## Decisions

### D1. Name: `ep-qa`

The capability and skill are `ep-qa`, following the `ep-<short noun>` pattern (`ep-a11y`, `ep-review`). The change name keeps the longer `add-ep-qa-audit-skill`.
- Alternative: `ep-qa-audit`. Rejected as longer with no extra meaning; "audit" is in the description, which is what triggers the skill.
- Alternative: `ep-audit`. Rejected because it is ambiguous next to `ep-a11y`, which is also an audit.

### D2. Layout

```
skills/ep-qa/
  SKILL.md               steps, gates, usage, summary block
  scripts/context.sh     synced copy of shared/context.sh
  references/
    plan.md              where to find commands per ecosystem; probes per project type; edge-case inputs; never-run list
    audit.md             finding shape, areas, severity scale, verification and flaky rules, environment-vs-defect rules, env variable rule, regression test proposals, report template
    record.md            run record: location, format, fingerprints, skip and invalidation rules, previous findings, corrupt or foreign records
```

`plan.md` is read in the planning step, `record.md` when loading the record (step 1), marking skips (step 3), and writing the record (step 9), and `audit.md` in verification and reporting, so `SKILL.md` stays a short sequence of steps (the same split as `ep-a11y`'s `checks.md` and `audit.md`). Nothing is shared with another skill folder except the synced probe.

### D3. Targets and arguments

```
ep-qa                     whole repository at its current checkout (working tree included)
ep-qa <path>              one directory inside the repository (e.g. a monorepo package)
ep-qa ... --url <url>     also probe a running app at <url>, read-only
ep-qa ... --out <path>    audit file path (default qa-audit.md at the repository root)
ep-qa ... --yes           run the confirmed-by-flag plan without asking
ep-qa ... --full          ignore the run record: run every check, start finding ids afresh, replace the record
```

An argument that is an existing directory inside the repository is the path target. Anything else is an error that stops the run before anything executes. `--out` paths are relative to the repository root; missing parent directories are created. The run record lives beside the audit file (D13), so each `--out` path has its own record.

### D4. Flow

1. **Context.** Run `scripts/context.sh` (inline fallback: `git status --porcelain=v1 -b`, `git rev-parse HEAD`). Record the head sha and dirty state; record `git status --porcelain --untracked-files=all` as the before-snapshot. Load the run record (D13) unless `--full` was given; a missing, corrupt, foreign, or other-target record counts as absent, and the reason is kept for the report.
2. **Discover.** Read `references/plan.md`. From the target, read manifests (`package.json`, `pyproject.toml`, `requirements*.txt`, `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle*`, `composer.json`, `*.csproj`), task runners (`Makefile`, `justfile`, `Taskfile.yml`, package scripts, `tox.ini`, `noxfile.py`), CI workflows (`.github/workflows/*.yml`), container files (`Dockerfile`, `docker-compose*.yml`), docs (`README*`, `CONTRIBUTING*`, `docs/`), and example env files (`.env.example`, `.env.sample`). With an OpenSpec root, read `openspec/specs/*/spec.md` too. Classify the project type: CLI, HTTP server or web app, library, or several.
3. **Plan.** Build plan items in this order: setup, build, lint, types, tests, run, probes, docs. Each item has an id (`P1`…), area, exact command or probe, source (file and line), and a run decision: `run`, `skip: unchanged since <sha>` (D14), or `not covered: <reason>` for items on the never-run list (D6) or with a missing toolchain (`command -v`). The plan also carries one re-check item per open finding from the record (D15) and, when the project has a test command, one item for running proposed regression tests in a scratch copy (D16).
4. **Confirm** (D5). Print the plan. Ask once; with `--yes`, skip the question.
5. **Execute.** Skipped items do not run; their result is copied from the record. Run the other confirmed items one at a time, in plan order, from one context. Each command runs with a 10-minute timeout; a timeout is a failed item with the timeout as evidence. Record exit code, duration, and the decisive output lines. When setup or build fails, later items that depend on it become `not covered: blocked by P<n>`. Servers start in the background; poll their documented port or health route for up to 2 minutes; record each started process's PID and stop it (and its process group) at the end, also when the run fails.
6. **Probe.** For a CLI: `--help`, each documented example, then empty, invalid, very large, and unicode input, and a missing config file. For a local server: each documented route, a missing route, malformed bodies on documented write routes, and missing required config. For a library: the README's code examples in a scratch directory outside the repository. For `--url`: `GET`/`HEAD` of documented routes and a missing route only. Each surprise (crash, stack trace, 5xx, wrong exit code, output contradicting docs or specs) is a candidate.
7. **Docs check.** Compare every documented command, flag, env variable, and example against what the run showed; the README's own commands are already plan items, so their failures are docs candidates when the doc is what is wrong.
8. **Verify** (D7, D15, D16). Re-run each candidate's reproduction alone. Classify: reproduced, flaky, environment, or refuted. Re-run each open finding from the record and mark it still failing or fixed. For each reproduced finding, draft a regression test and run it in a scratch copy to show it fails today, or record why no test is proposed.
9. **Report** (D9, D10, D13). Take the after-snapshot; list created or changed files (the audit file and the record excluded). Write the audit file, then the record, print a short summary, and end with the summary block.

**Subagent path vs sequential fallback.** Commands and probes always run from the main context, one at a time, because parallel runs fight over ports, caches, databases, and build output. Subagents are used only for work with no running state:
- **With subagents:** in step 2, one subagent reads docs (and specs when present) and returns the expected-behavior list (documented commands, flags, env variables, examples, spec scenarios with file and line). In step 8, a subagent may read code to point at a reproduced finding's likely cause, for the report's "Notes" line; it never changes the finding's severity or existence.
- **Without subagents:** the main context does the same reading in the same steps. The audit file has the same shape.

### D5. Confirmation gate

The plan is shown as a numbered list of exact commands with their sources and the items marked not covered. One answer covers the whole plan. The user may drop items; the skill then runs only the remaining ones. `--yes` counts as confirmation for the plan as built. When the agent cannot ask (non-interactive) and `--yes` was not given, no project command runs: the audit does steps 2, 3, and 7 by reading only, and every planned command goes under "Not covered: not confirmed".

Reading files, `git` read commands, `command -v`, and the `--url` read-only requests need no confirmation; they are not project code.

### D6. Never-run list

Never planned as runnable, with or without `--yes`, and listed under "Not covered" with the reason:
- deploy, publish, release, push, tag, or upload commands (by name or content: `deploy`, `publish`, `release`, `npm publish`, `twine upload`, `cargo publish`, `docker push`, `git push`, `terraform apply`, `kubectl apply`, `serverless deploy`, and similar);
- database migrations or seeds whose target is not local (a connection string or env value pointing to a non-local host), and any `drop`/`reset` of a database;
- commands that need credentials or secrets the project expects from the environment (cloud CLIs, API keys) when those are not provided by a local example env file; this rule wins over the placeholder start (D17);
- commands that delete files outside the project's build and cache output (`rm -rf` of anything else, `git clean`, `git reset`);
- global or system installs (`npm i -g`, `pip install` outside a project virtual environment, `sudo`, `brew`, `apt`) and installing tools the project does not declare.

Dependency installs run only with the project's lockfile-respecting command (`npm ci`, `pnpm install --frozen-lockfile`, `yarn install --immutable`, `pip install -r` into a project-local `.venv`, `uv sync --frozen`, `poetry install --no-root` when locked, `bundle install` with a lock, `cargo build --locked`, `go mod download`). Without a lockfile, the install item is planned but flagged in the plan as "may change dependency resolution" so the user decides.

### D7. Verification

- **Reproduced:** the failure happens again when its reproduction runs alone. Reported as a finding.
- **Flaky:** it failed once and passed on the re-run. Re-run once more; report as a flaky finding with each run's result quoted. Severity is at most major.
- **Environment:** the cause is the machine, not the project (tool missing, port in use, no network, missing credentials). Goes under "Not covered" with the reason. When the docs do not state the requirement, a docs finding is reported instead.
- **Refuted:** it does not happen again and the first failure is explained by the audit itself (for example a probe sent malformed input on purpose and the app rejected it correctly). Dropped.

Code reading never makes a finding on its own. Suspicions from code that no probe confirmed go under "Not covered" as "worth testing", with the file and line.

### D8. Severity and areas

Areas: `setup`, `build`, `lint`, `types`, `tests`, `runtime`, `docs`.

| Severity | Meaning | Examples |
|---|---|---|
| critical | The project cannot be set up, built, or started from its docs, a core flow is broken, or data is lost or exposed. | install or build fails on a clean checkout; app crashes on start; main command crashes on documented input; secret printed in normal output |
| major | Wrong in a realistic case, or a check the project defines fails. | failing test; lint or typecheck errors in a configured check; documented command or flag fails; 500 on malformed input; flaky test |
| minor | Real but low impact. | misleading error message; doc typo in a flag name with an obvious fix; warning noise from the project's own code |

Ranking: severity, then area in the order above, then id.

### D9. Audit file

- Default path `qa-audit.md` at the repository root; `--out` overrides.
- The first line is a marker: `<!-- ep-qa audit: <head sha> <ISO date> -->`. An existing file at the path is overwritten only when its first line starts with `<!-- ep-qa audit:`. Otherwise the report goes to `qa-audit-<YYYY-MM-DD-HHMM>.md` in the same folder, and the output says so.
- When the dated name is taken too, `-2`, `-3`, ... is added before `.md`; a dated file is never overwritten.
- Never committed and never added to `.gitignore`; the output suggests committing it (for example with `ep-commit`) or deleting it. The same holds for the run record.

Report template (in `references/audit.md`):

```
<!-- ep-qa audit: <sha> <date> -->
# QA audit: <repo name> (<target>)

Commit <short sha>, tree <clean | dirty>. Audited <date>.

## Summary
<counts by severity; one-line verdict on what was exercised, never "works" or "passed">

## Findings
### QA-1 [critical] build: `npm run build` fails on a clean checkout
- Where: package.json:12 (`build` script); src/index.ts:40
- Steps to reproduce:
  1. npm ci
  2. npm run build
- Expected: build completes (README "Getting started")
- Actual: exit 2, `TS2307: Cannot find module './config'`
- Evidence: <quoted decisive lines, secrets redacted>
- Notes: <optional likely cause>
- Status: new | still failing (first seen <sha>)
- Regression test: <proposed path> (<framework>)
  ```<lang>
  <test code, no secrets>
  ```
  Fails today: <quoted decisive lines from the scratch run>
  (or: No test proposed: <reason>)

## Fixed since last run
- QA-3 [major] tests: ... fixed at <short sha> (reproduction now passes)

## Plan and results
| Id | Area | Command or probe | Source | Result |
| P4 | tests | `make test` | Makefile:7 | skipped, unchanged since <short sha> |

## Not covered
- P7 `npm run deploy`: never run (deploys)
- Runtime probes: needs PostgreSQL at DATABASE_URL, not available locally

## Files changed by the audit
- dist/ (created), coverage/ (created), tests/__snapshots__/x.snap (modified)

## Run record
<record path>, <n> checks skipped; or: "previous record ignored: <corrupt | not an ep-qa record | other target | --full>"
```

### D10. Summary block

```ep-qa-summary
target: <repo | path:<p>>[ url:<u>]
head: <sha>
dirty: <true | false>
report: <path>
findings: {critical: <n>, major: <n>, minor: <n>}
plan: {run: <n>, passed: <n>, failed: <n>, skipped: <n>, not_covered: <n>}
previous: {still_failing: <n>, fixed: <n>, not_rechecked: <n>}
regression_tests: {proposed: <n>, none: <n>}
record: <path | none>
full: <true | false>
confirmed: <true | false>
```

`confirmed` is true when the user confirmed the plan or passed `--yes`. `findings` counts flaky findings under their severity and includes still-failing ones. `previous` counts open findings from the record (all zero without one). `record` is the record written this run, or `none` when none was written (plan declined, or a foreign or corrupt file holds the path).

### D11. Gates

| Action | Gate |
|---|---|
| Run a project command (install, build, checks, tests, start the app, probes) | Only items in the plan the user confirmed, or the plan as built with `--yes`. |
| Commands on the never-run list (D6) | Never, even with `--yes`. |
| HTTP requests to `--url` | `GET` and `HEAD` only; no forms, sign-in, or other methods. |
| State-changing requests | Only to an app the skill started locally. |
| Write the audit file | Always, at the default or `--out` path; overwrite only an earlier `ep-qa` report (D9). |
| Write the run record | After a run that executed checks, beside the audit file; replace only an earlier `ep-qa` record (D13). Never committed. |
| Write a proposed regression test | Only inside a scratch copy under the system temp dir, deleted at the end; never in the repository's working tree (D16). |
| Edit source, tests, config, docs, or lock files, or add a test | Never. Changes made by confirmed commands are listed and left in place. |
| Stop processes | Only processes the skill started, always before ending. |
| Commit, push, merge, or post to GitHub | Never. |
| Install tools | Never; lockfile-respecting project dependency installs only as confirmed plan items. |

### D12. OpenSpec as an oracle

With an OpenSpec root, main spec scenarios are expected behavior next to the docs: a probe whose result contradicts a scenario's THEN is a finding whose "Expected" cites the spec file and scenario. The skill does not read or judge active changes under `openspec/changes/`, since they describe behavior not yet built. Without an OpenSpec root, nothing about OpenSpec is mentioned.

### D13. Run record

Each run that executed at least one check writes a JSON record next to the audit file: `<audit-file stem>.state.json`, so `qa-audit.md` pairs with `qa-audit.state.json` and `--out reports/qa.md` with `reports/qa.state.json`. The record path follows the requested path (default or `--out`), not a dated fallback name, so a run that had to write `qa-audit-<date>.md` still finds and updates `qa-audit.state.json`.
- Why beside the audit file: the user sees it, can delete it to force a fresh run, and each `--out` audit keeps its own history. Alternatives: `.git/ep-qa/state.json` (rejected: invisible, shared by every `--out`, and absent in some worktree layouts); a hidden `.qa-audit.state.json` (rejected: easy to forget and still shows in `git status`); embedding the state in the audit file (rejected: the report is for people and gets edited or committed).
- Format: `{"tool": "ep-qa", "version": 1, "target", "report", "head", "dirty", "toolchain", "checks": [...], "findings": [...]}`. Each check has `key` (sha256 of area, command or probe, working directory, and the names of env variables it sets), `id`, `result` (`passed`, `failed`, `flaky`), `sha` (the head it actually ran on), `deps` (paths), `fingerprint`, and `prereqs` (keys of items it depends on). Each finding has `id`, `title`, `severity`, `area`, `check_key`, `repro` (steps), `first_seen` (sha), `status`, and its proposed regression test (path, framework, code) when there is one. No command output, env values, or secrets are stored.
- Written atomically (a temp file in the same folder, then rename), so an interrupted run leaves the old record or the new one, never half of one.
- A record is used only when it parses, has `"tool": "ep-qa"` and a known `version`, and its `target` matches this run's. Otherwise it counts as absent and the report says why (corrupt, not an ep-qa record, other target). A file at the record path that does not parse or lacks the marker is left untouched and no record is written this run (the report says so and how to fix it: move or delete the file); a valid ep-qa record for another target is replaced.
- A run where the plan was not confirmed executes nothing, so it leaves the record as it was. With `--full`, the record is not read at all, and it is replaced at the end.
- Like the audit file, the record is never committed or added to `.gitignore`, and both are excluded from "Files changed by the audit".

### D14. Skipping unchanged checks

A plan item is marked `skip: unchanged since <sha>` only when all of these hold (conservative: any doubt means it runs):
1. The record has a check with the same `key` whose `result` is `passed` (failed and flaky checks always run again).
2. Its fingerprint is unchanged. The fingerprint is a sha256 over the sorted list of (path, `git hash-object` of the working-tree file) for every tracked and untracked, non-ignored file under its `deps` (`git ls-files -co --exclude-standard`), plus the hash of each env file the item reads even when ignored (`.env`, never its contents). Hashing the working tree, not `HEAD`, catches uncommitted edits, and the file list catches additions and deletions.
3. `deps` is the whole target, minus Markdown and `docs/` for items outside the `docs` area. Narrower dependency sets were rejected: knowing which files a test touches needs coverage data the skill cannot trust.
4. No global invalidator changed: lockfiles and manifests in the target, the toolchain versions recorded in step 1 (`node --version`, `python3 --version`, ... for the toolchains the plan uses), and CI or task-runner files the item came from.
5. Every prerequisite item (by `prereqs`) has the same key as before; a changed or new prerequisite command invalidates its dependents.

A skipped item is never a hidden prerequisite: when an item that must run depends on a skipped item that produces state (an install, a build, a started server), that prerequisite runs too and is shown as run. `--url` probes are never skipped, since the remote app can change without the repository changing. Items marked not covered are re-decided each run.

### D15. Previous findings

Every open finding in the record gets a re-check plan item that runs its reproduction alone, whatever the fingerprints say. Outcome:
- **Still failing:** it reproduces. It keeps its `QA-<n>` id and `first_seen`, and gets fresh evidence. A flaky finding stays flaky when it fails in either of two runs.
- **Fixed:** the reproduction passes (twice for a flaky finding). It moves to "Fixed since last run" with the sha it was found fixed at, and is closed in the record.
- **Not re-checked:** the reproduction could not run (toolchain missing, blocked prerequisite). It stays open and is listed under "Not covered" with the reason.

Ids are stable across runs: new findings take the next number after the highest id in the record, and the findings section is still ranked by severity, area, and plan order.

### D16. Regression test proposals

For each reproduced finding (new or still failing), the skill drafts one test that encodes the expected behavior:
- In the project's own framework and conventions, read from the test command, existing test files (location, naming, imports, fixtures), and the test config. No new framework or dependency.
- With the path where it would go (following those conventions) and the code in the audit file.
- Shown to fail today: the skill copies the target's tracked and untracked, non-ignored files to a scratch directory under the system temp dir (dependency directories such as `node_modules` or `.venv` are copied when the test command may write to them, otherwise linked), writes the test there, and runs only that test with the project's test command. The failure must be the finding's (the asserted behavior), not an import or syntax error; after two failed attempts at a test that fails for the right reason, the skill gives up and says so. The scratch directory is deleted at the end.
- The test is never written into the repository's working tree; the after-snapshot proves it. Running it is one plan item (area `tests`, "run proposed regression tests in a scratch copy"), so the confirmation gate covers it; when the plan is declined the tests are still proposed, marked "not run: plan not confirmed".
- No secrets: tests use placeholders (`qa-placeholder`) for any credential or env value, and the redaction rule applies to the test code.
- When no sensible test exists, the finding says why instead: the cause is environment or infrastructure, the finding is flaky by nature (timing, external service), it is visual-only, or the project has no test command or framework.

A still-failing finding reuses its proposed test from the record and re-runs it in the scratch copy for fresh evidence.

### D17. Undocumented env variables and placeholder starts

The three references disagreed on when an undocumented env variable is a finding. One rule, stated in `audit.md` and referenced from `plan.md` and `SKILL.md` step 7:
- An undocumented variable is a `docs` finding only when the documented start (or another documented command) fails or misbehaves without it, its output or a traceback names the variable, and no doc or example env file mentions it. Severity follows D8: critical when the app cannot start, major when only a secondary feature needs it. A variable read in code that never made anything fail is not a finding (code reading alone, D7).
- The placeholder start runs only after the documented start's process and its process group are stopped and its port is free, so the two never overlap.
- Credentials win over placeholders: a variable whose name looks like a credential (`*KEY`, `*TOKEN`, `*SECRET`, `*PASSWORD`, `*PASSWD`, `*CREDENTIALS`, case-insensitive) is never filled with a placeholder. When any such variable is required, no placeholder start is planned and the start and its probes go under "Not covered: needs credential <NAME>". The docs finding above still applies when the documented start failed and named it.

## Risks / Trade-offs

- [A project command does something harmful the never-run list does not catch, such as a test that hits a real API] → Every command is shown before it runs and needs the user's confirmation; `--yes` is the user's explicit choice. The report lists every file the run changed.
- [Running in place changes the working tree (snapshots, generated files)] → The before and after snapshots catch every change, and the report lists them for the user. Reverting is never automatic, because it could destroy the user's own uncommitted work. Alternative considered: run in a `git worktree` of HEAD; rejected because it misses uncommitted changes the user wants audited and repeats dependency installs.
- [Long or hanging commands] → 10-minute timeout per command and 2-minute readiness wait for servers; timeouts are reported as failures with that evidence.
- [Orphaned servers] → PIDs are recorded at start and stopped at the end, including when a later step fails.
- [False positives from the environment] → The environment classification (D7) keeps machine problems out of findings.
- [Context size on large repositories] → Discovery reads manifests, task runners, CI, and docs, not the whole source tree; output is kept to decisive lines.
- [Secrets in output] → Evidence is redacted, and `.env` files are never quoted.
- [A skipped check hides a regression caused by something outside its fingerprint, such as a system library or a service] → Skips are limited to checks that passed with identical files, lockfiles, toolchain versions, and commands; `--url` probes never skip; every earlier finding is always re-checked; `--full` runs everything, and the report lists every skip with its sha.
- [The record goes stale or is edited by hand] → Anything that does not parse or lacks the marker counts as absent and is never overwritten; the record holds no output or secrets.
- [`--full` loses finding history] → Accepted as the literal meaning of "ignore the record"; the previous audit file stays readable in git or on disk when the user committed or kept it.
- [A proposed regression test runs project code in a scratch copy] → It is a confirmed plan item, runs with the same timeout, and the scratch copy is deleted; the working tree is checked against the before-snapshot.

## Migration Plan

This change is additive. To roll back, delete `skills/ep-qa/` and revert the README rows. Records written by earlier runs (`*.state.json` beside audit files) are plain files users can delete. No existing skill changes.

## Open Questions

- Should `ep-qa` gain `--issue` to file one GitHub issue per critical finding? Deferred to a later change; it does not affect this one.
