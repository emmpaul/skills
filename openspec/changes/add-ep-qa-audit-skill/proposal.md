# Proposal

## Why

No `ep-*` skill checks whether an app or repository actually works. `ep-review` and `ep-a11y` read a diff, and `ep-ci-debug` explains a check that is already red. Nobody installs the project from its README, runs its build, tests, and linters, starts the app, and tries its main flows and edge cases the way a senior QA engineer would. Broken setup steps, failing or flaky tests, crashes on bad input, and docs that no longer match behavior stay unnoticed until a user hits them. The user wants a skill that does this audit and writes down what is not working in an audit file.

## What Changes

- Add a new skill, `ep-qa` (new behavior), under `skills/ep-qa/`:
  - Audits the whole repository at its current checkout (default), one path inside it (for example one package of a monorepo), or a running app at a URL the user gives (`--url`).
  - Discovers how the project is meant to be set up, built, checked, tested, and run from its manifests, task runners, CI workflow, and docs, and turns that into a test plan of exact commands and probes.
  - Shows the plan and runs project commands only after the user confirms it (or passes `--yes`). It never runs commands that deploy, publish, release, push, migrate or touch non-local services, or need credentials, and it never installs global tools.
  - Executes the plan: install, build, lint, typecheck, and tests; starts the app where possible and probes its main flows plus edge cases (empty, invalid, large, and unicode input, missing config); checks documented commands, flags, and examples against observed behavior. With an OpenSpec root, the main specs' scenarios are also used as expected behavior.
  - Reports only verified findings: each one was observed (command output, HTTP response, or crash) and reproduced on a re-run, with severity (critical, major, minor), area, reproduction steps, expected versus actual, and evidence. A failure that does not reproduce is reported as flaky with both runs as evidence. Problems caused only by the auditing machine (a missing tool, no network) go to a "Not covered" list, not to findings.
  - Writes the audit file, `qa-audit.md` at the repository root by default (`--out <path>` overrides). It overwrites only a file that an earlier `ep-qa` run wrote, and never commits it.
  - Read-only toward source: it edits no source, test, config, or lock file. Files that the confirmed commands write (build output, caches, installed dependencies) are listed in the report and left in place.
  - Lists what it could not exercise ("Not covered") and never claims that the project works or is bug-free.
  - Ends with a machine-readable `ep-qa-summary` block that other skills can read.
- `ep-qa` ships its own synced copy of `scripts/context.sh` (through the existing `scripts/sync-shared.sh`). `shared/context.sh` does not change.
- README: add `ep-qa` to the skills table and install commands.

**Outward effects on GitHub:** none. `ep-qa` never posts, pushes, commits, or merges. With `--url`, it sends only read-only HTTP requests (`GET`, `HEAD`) to that URL.

## Capabilities

### New Capabilities
- `ep-qa`: a senior-QA audit of an app or repository that exercises it (setup, build, static checks, tests, running the app, edge cases, docs against behavior) and writes an audit file of verified, reproducible problems.

### Modified Capabilities
None. `ep-review`, `ep-a11y`, `ep-ci-debug`, and the other skills keep their current requirements.

## Impact

- New files: `skills/ep-qa/SKILL.md`, `skills/ep-qa/references/plan.md` (command discovery and probes per project type), `skills/ep-qa/references/audit.md` (finding shape, severity, verification, report template), and `skills/ep-qa/scripts/context.sh` (a synced copy).
- Modified: `README.md` (skills table and install commands).
- Unchanged: `shared/context.sh`, `.github/workflows/check.yml` (its existing shared-probe and shell-parse steps already cover the new folder), and every existing skill.
- Runtime: `git`. Project commands need whatever toolchain the project declares; the skill installs none. `gh` is not needed. Network access is needed only for steps in the confirmed plan that need it (for example dependency installs) and for `--url`.
- Local effects in the audited repository: the audit file, plus whatever the confirmed project commands write (listed in the report). Processes the skill starts are stopped before it ends.
