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

**Non-Goals:**
- Auditing a diff, branch, or PR. `ep-review` and `ep-a11y` cover changes; `ep-qa` audits the project as it stands.
- Fixing anything, opening issues, or commenting on GitHub. A later change can add `--issue`; fixes go through `ep-ci-debug`, `tdd`, or by hand.
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
    audit.md             finding shape, areas, severity scale, verification and flaky rules, environment-vs-defect rules, report template
```

`plan.md` is read in the planning step and `audit.md` in verification and reporting, so `SKILL.md` stays a short sequence of steps (the same split as `ep-a11y`'s `checks.md` and `audit.md`). Nothing is shared with another skill folder except the synced probe.

### D3. Targets and arguments

```
ep-qa                     whole repository at its current checkout (working tree included)
ep-qa <path>              one directory inside the repository (e.g. a monorepo package)
ep-qa ... --url <url>     also probe a running app at <url>, read-only
ep-qa ... --out <path>    audit file path (default qa-audit.md at the repository root)
ep-qa ... --yes           run the confirmed-by-flag plan without asking
```

An argument that is an existing directory inside the repository is the path target. Anything else is an error that stops the run before anything executes. `--out` paths are relative to the repository root; missing parent directories are created.

### D4. Flow

1. **Context.** Run `scripts/context.sh` (inline fallback: `git status --porcelain=v1 -b`, `git rev-parse HEAD`). Record the head sha and dirty state; record `git status --porcelain --untracked-files=all` as the before-snapshot.
2. **Discover.** Read `references/plan.md`. From the target, read manifests (`package.json`, `pyproject.toml`, `requirements*.txt`, `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle*`, `composer.json`, `*.csproj`), task runners (`Makefile`, `justfile`, `Taskfile.yml`, package scripts, `tox.ini`, `noxfile.py`), CI workflows (`.github/workflows/*.yml`), container files (`Dockerfile`, `docker-compose*.yml`), docs (`README*`, `CONTRIBUTING*`, `docs/`), and example env files (`.env.example`, `.env.sample`). With an OpenSpec root, read `openspec/specs/*/spec.md` too. Classify the project type: CLI, HTTP server or web app, library, or several.
3. **Plan.** Build plan items in this order: setup, build, lint, types, tests, run, probes, docs. Each item has an id (`P1`…), area, exact command or probe, source (file and line), and a run decision: `run`, or `not covered: <reason>` for items on the never-run list (D6) or with a missing toolchain (`command -v`).
4. **Confirm** (D5). Print the plan. Ask once; with `--yes`, skip the question.
5. **Execute.** Run confirmed items one at a time, in plan order, from one context. Each command runs with a 10-minute timeout; a timeout is a failed item with the timeout as evidence. Record exit code, duration, and the decisive output lines. When setup or build fails, later items that depend on it become `not covered: blocked by P<n>`. Servers start in the background; poll their documented port or health route for up to 2 minutes; record each started process's PID and stop it (and its process group) at the end, also when the run fails.
6. **Probe.** For a CLI: `--help`, each documented example, then empty, invalid, very large, and unicode input, and a missing config file. For a local server: each documented route, a missing route, malformed bodies on documented write routes, and missing required config. For a library: the README's code examples in a scratch directory outside the repository. For `--url`: `GET`/`HEAD` of documented routes and a missing route only. Each surprise (crash, stack trace, 5xx, wrong exit code, output contradicting docs or specs) is a candidate.
7. **Docs check.** Compare every documented command, flag, env variable, and example against what the run showed; the README's own commands are already plan items, so their failures are docs candidates when the doc is what is wrong.
8. **Verify** (D7). Re-run each candidate's reproduction alone. Classify: reproduced, flaky, environment, or refuted.
9. **Report** (D9, D10). Take the after-snapshot; list created or changed files. Write the audit file, print a short summary, and end with the summary block.

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
- commands that need credentials or secrets the project expects from the environment (cloud CLIs, API keys) when those are not provided by a local example env file;
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
- Never committed and never added to `.gitignore`; the output suggests committing it (for example with `ep-commit`) or deleting it.

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

## Plan and results
| Id | Area | Command or probe | Source | Result |

## Not covered
- P7 `npm run deploy`: never run (deploys)
- Runtime probes: needs PostgreSQL at DATABASE_URL, not available locally

## Files changed by the audit
- dist/ (created), coverage/ (created), tests/__snapshots__/x.snap (modified)
```

### D10. Summary block

```ep-qa-summary
target: <repo | path:<p>>[ url:<u>]
head: <sha>
dirty: <true | false>
report: <path>
findings: {critical: <n>, major: <n>, minor: <n>}
plan: {run: <n>, passed: <n>, failed: <n>, not_covered: <n>}
confirmed: <true | false>
```

`confirmed` is true when the user confirmed the plan or passed `--yes`. `findings` counts flaky findings under their severity.

### D11. Gates

| Action | Gate |
|---|---|
| Run a project command (install, build, checks, tests, start the app, probes) | Only items in the plan the user confirmed, or the plan as built with `--yes`. |
| Commands on the never-run list (D6) | Never, even with `--yes`. |
| HTTP requests to `--url` | `GET` and `HEAD` only; no forms, sign-in, or other methods. |
| State-changing requests | Only to an app the skill started locally. |
| Write the audit file | Always, at the default or `--out` path; overwrite only an earlier `ep-qa` report (D9). |
| Edit source, tests, config, docs, or lock files | Never. Changes made by confirmed commands are listed and left in place. |
| Stop processes | Only processes the skill started, always before ending. |
| Commit, push, merge, or post to GitHub | Never. |
| Install tools | Never; lockfile-respecting project dependency installs only as confirmed plan items. |

### D12. OpenSpec as an oracle

With an OpenSpec root, main spec scenarios are expected behavior next to the docs: a probe whose result contradicts a scenario's THEN is a finding whose "Expected" cites the spec file and scenario. The skill does not read or judge active changes under `openspec/changes/`, since they describe behavior not yet built. Without an OpenSpec root, nothing about OpenSpec is mentioned.

## Risks / Trade-offs

- [A project command does something harmful the never-run list does not catch, such as a test that hits a real API] → Every command is shown before it runs and needs the user's confirmation; `--yes` is the user's explicit choice. The report lists every file the run changed.
- [Running in place changes the working tree (snapshots, generated files)] → The before and after snapshots catch every change, and the report lists them for the user. Reverting is never automatic, because it could destroy the user's own uncommitted work. Alternative considered: run in a `git worktree` of HEAD; rejected because it misses uncommitted changes the user wants audited and repeats dependency installs.
- [Long or hanging commands] → 10-minute timeout per command and 2-minute readiness wait for servers; timeouts are reported as failures with that evidence.
- [Orphaned servers] → PIDs are recorded at start and stopped at the end, including when a later step fails.
- [False positives from the environment] → The environment classification (D7) keeps machine problems out of findings.
- [Context size on large repositories] → Discovery reads manifests, task runners, CI, and docs, not the whole source tree; output is kept to decisive lines.
- [Secrets in output] → Evidence is redacted, and `.env` files are never quoted.

## Migration Plan

This change is additive. To roll back, delete `skills/ep-qa/` and revert the README rows. No existing skill changes.

## Open Questions

- Should `ep-qa` gain `--issue` to file one GitHub issue per critical finding? Deferred to a later change; it does not affect this one.
