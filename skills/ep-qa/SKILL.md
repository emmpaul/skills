---
name: ep-qa
description: QA audit of an app or repository (whole checkout, one path, or a running app via --url) the way a senior QA engineer would. Builds a test plan from the project's manifests, scripts, CI, and docs, runs it after confirmation (--yes to pre-approve) without ever deploying, publishing, or installing tools, probes the running app with edge cases, checks docs against behavior, and writes an audit file (qa-audit.md, --out to change) of verified, reproducible problems plus what was not covered. Ends with an ep-qa-summary block other skills can read. Use when the user asks for a QA audit, to test or check whether an app or repo works, or to find what is broken in a project.
---

# ep-qa

Exercise a project as it stands (setup, build, checks, tests, the running app, edge
cases, its docs), reproduce every failure, and write an audit file of what is broken and
what was not covered.

## Hard rules

- **Read-only toward source.** Write only the audit file and its run record. Edit no
  source, test, config, docs, or lock file, and add no test: proposed regression tests
  live in a scratch copy under the system temp dir. Files that confirmed commands create
  or change are listed in the report and left in place, never reverted.
- **Confirmation first.** Run project commands only from the plan the user confirmed, or
  the plan as built with `--yes`. Without either, run none.
- **Never-run list.** Deploy, publish, release, push, non-local or destructive database
  commands, credentialed commands, and deletes outside build and cache output never run,
  even with `--yes` (`references/plan.md`).
- **Install nothing on the machine.** Dependency installs only with the project's
  lockfile-respecting command, as confirmed plan items; never a global or system install
  or a tool the project does not declare.
- **`--url` is read-only:** `GET` and `HEAD` only. State-changing requests go only to an
  app this run started locally.
- **No git or GitHub writes:** no commit, push, merge, issue, PR, or comment. The audit
  file and the run record stay uncommitted and out of `.gitignore`.
- **No all-clear.** The report says what was exercised and found; it never says the
  project works, is bug-free, or passed QA.
- **Secrets stay out.** Redact tokens, passwords, keys, and every `.env` value in the
  report and the output (`references/audit.md`).
- **No attribution** in the audit file or output.
- Stop every process this run started before ending, also when a step fails.

## Usage

```
ep-qa                     # whole repository at its current checkout, working tree included
ep-qa <path>              # one directory inside the repository (e.g. a monorepo package)
ep-qa ... --url <url>     # also probe a running app at <url>, GET and HEAD only
ep-qa ... --out <path>    # audit file path, relative to the repository root (default qa-audit.md)
ep-qa ... --yes           # run the plan as built without asking
ep-qa ... --full          # ignore the run record: run every check, number findings afresh, replace the record
```

An argument that is an existing directory inside the repository is the path target.
Anything else (missing, outside the repository, a file) stops the run before anything
executes: `not auditable: <path>`. Label the target `repo` or `path:<p>` (relative to the
root) in the report and summary.

## References

All in this skill's folder (the directory containing this SKILL.md):

| File | What it holds | When to read |
|---|---|---|
| `references/plan.md` | discovery sources, plan item shape, showing the plan, lockfile installs, never-run list, running and server rules, probes per project type, edge inputs | step 2, always |
| `references/audit.md` | finding shape, areas, severity, verification outcomes, regression test proposals, secrets, coverage, wording, report template | step 8, always |
| `references/record.md` | run record path and format, fingerprints, skip and invalidation rules, checks never skipped, earlier findings, unusable records, atomic write | steps 1, 3, and 9, always |

## 1. Context

From the repository root, run the probe bundled in this skill's folder:

```bash
bash <skill-dir>/scripts/context.sh
```

Use its `git` (branch, dirty state) and `openspec.root`; ignore the rest. Entries in
`warnings` are informational. `openspec` is also null when the openspec tool is not
installed, so null alone does not mean no OpenSpec: when it is null, an `openspec/` folder
at the repository root is the OpenSpec root, and only with neither is there no OpenSpec.
If bash is unavailable, or the probe exits non-zero or prints invalid JSON, run inline:

```bash
git status --porcelain=v1 -b
```

and treat an `openspec/` folder at the root as the OpenSpec root. Then record
`git rev-parse HEAD` as the head, and `git status --porcelain -z --untracked-files=all` as
the **before-snapshot** (`-z` keeps non-ASCII paths unquoted, as in the fingerprint). Resolve the target (Usage).

Read `references/record.md` and load the run record beside the requested audit path
(`<audit-file stem>.state.json`). With `--full`, use nothing from it, but still check a
file there is an ep-qa record so a corrupt or foreign file is never overwritten. A
missing, corrupt, foreign, or other-target record counts as absent; keep the reason for
the report.

## 2. Discover

Read `references/plan.md`. From the target, read the discovery sources it lists, classify
the project type, and collect the expected behavior (documented commands, flags, env
variables, examples, each with file and line). With an OpenSpec root, add the main spec
scenarios (`openspec/specs/*/spec.md`); never `openspec/changes/`. Without one, OpenSpec
appears nowhere in the plan, report, or output.

**With subagents:** one subagent reads the docs (and main specs when present) and returns
the expected-behavior list with file and line; you read manifests, runners, and CI
meanwhile. **Without subagents:** read all of it yourself. The list is the same.

Done when every manifest, runner, CI workflow, and doc in the table has been read, or
noted as absent.

## 3. Plan

Build plan items in the shape and order from `plan.md`: setup, build, lint, types,
tests, run, probes, docs. Mark each `run`, `skip: unchanged since <sha>`, or
`not covered: <reason>`. Once the items exist, and before marking any skip, record the
version of every toolchain the plan uses (`record.md`, "Toolchain versions"). Skips
follow "Skipping unchanged checks" and "Checks never skipped" in `record.md`; not covered
is for never-run commands, missing tools (`command -v`), and services the audit cannot run
locally. Add one re-check item per open
finding in a usable record (`record.md`, "Earlier findings"). Probes come from
the project type and the edge inputs in `plan.md`; with `--url`, add `GET`/`HEAD` probes of
that URL. When the project defines no runnable command, say so; the audit continues with
docs checks only.

Done when every documented or scripted command has a plan item, every one with a source
and a decision.

## 4. Confirm

Print the plan as `plan.md` describes, then ask once whether to run it; the user may drop
items by id. Then:

- **Confirmed:** run exactly the confirmed items, no others. Dropped items become
  `not covered: dropped by the user`.
- **`--yes`:** print the plan and continue without asking.
- **Declined, or you cannot ask and `--yes` was not given:** run no project command.
  Every runnable item becomes `not covered: not confirmed`. Skip step 5; in step 6 send
  only the `--url` `GET`/`HEAD` probes, which need no confirmation; do step 7 by reading;
  verify only `--url` candidates in step 8; write the report and leave the run record
  as it is. `confirmed: false`.

## 5. Execute

Skipped items do not run; copy their result from the record. Run the other confirmed
items one at a time, in plan order, from this context, following
"Running" in `plan.md`: 10-minute timeout per command, exit code and decisive lines
recorded, items depending on a failed setup or build become `not covered: blocked by
P<n>`. Start servers in the background, record each PID, and wait for readiness up to
2 minutes. Run a placeholder start (`plan.md`) only after the documented start's
process group is stopped and its port is free, never while it still runs. A server that
needs a service you cannot run locally is not started: its runtime probes become not
covered with that reason.

## 6. Probe

Run the probe items for the project type ("Probes per project type" in `plan.md`), from
this context, one at a time. Each surprise (crash, stack trace, 5xx, wrong exit code,
unhelpful error, output contradicting the docs or a spec scenario) is a candidate. Every
failed plan item from step 5 is a candidate too.

## 7. Docs check

Compare each entry of the expected-behavior list with what steps 5 and 6 showed:
documented setup steps, commands, flags, env variables, and examples. A mismatch is a
`docs` candidate citing the doc line, the command run, and its output. A required service
or tool that made something fail and that no doc mentions is a `docs` candidate. An
undocumented env variable is a candidate only as "Undocumented env variables" in
`references/audit.md` says. Entries nothing exercised go to "Not covered".

## 8. Verify

Read `references/audit.md`. Re-run each candidate's reproduction alone and classify it
reproduced, flaky, environment, or refuted, as "Verification" there describes. Keep
reproduced and flaky ones as findings in the finding shape, assign severity and area,
rank and number them `QA-<n>`. Re-run each re-check item and mark the earlier finding
still failing, fixed, or not re-checked (`record.md`, "Earlier findings"); new findings
take ids after the highest the record has issued. For each reproduced finding, draft a
regression test and run it in a scratch copy under the system temp dir to show it fails
today for the finding's reason, or record why no test is proposed ("Regression test
proposals" in `audit.md`); never write it into the working tree. With the plan not
confirmed, draft it and mark it not run. Code suspicions no probe confirmed go to "Not covered" as
`worth testing`.

**With subagents:** for a reproduced finding, a subagent may read code and return its
likely cause (file and line) for `notes`; it never changes the finding's existence or
severity. **Without subagents:** read the code yourself, or leave `notes` empty.

Done when every candidate has an outcome.

## 9. Report and clean up

1. Stop every process this run started, with its process group; check its port is free.
   Delete the scratch copies (regression tests, library examples) and large-input files
   under the system temp dir.
2. Take the after-snapshot (`git status --porcelain -z --untracked-files=all`) and compare
   it with the before-snapshot: every created or modified path goes under "Files changed
   by the audit" (collapse a created directory to one line). The audit file and the run
   record are not listed.
3. Write the report with the template in `audit.md`, redacting secrets. Path: `--out`
   (relative to the root; create missing parent folders) or `qa-audit.md` at the root.
   When a file already exists there and its first line does not start with
   `<!-- ep-qa audit:`, leave it untouched and write `qa-audit-<YYYY-MM-DD-HHMM>.md` in the
   same folder instead; when that name is taken too, add `-2`, `-3`, ... before `.md`
   (never overwrite a dated file). Do not commit it or add it to `.gitignore`.
4. Write the run record after the audit file, as "Writing" in `record.md` says: beside
   the requested path (not a dated fallback), atomically, whenever the plan was
   confirmed (even if every check was skipped) and no corrupt or foreign file holds the
   path. Do not commit it or add it to `.gitignore`.
5. Print a short summary: counts by severity, the top findings (id, severity, title), the
   report path (and, for a dated name, why), and a suggestion to commit the report (for
   example with `ep-commit`) or delete it.
6. End with this block, exactly in this form, as the last thing in the output:

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

`dirty` is the tree state from step 1. `findings` counts flaky findings under their
severity and includes still-failing ones. `plan.run` counts items that ran (`passed` +
`failed`); `skipped` counts items skipped as unchanged; `not_covered` counts the rest.
`previous` counts the open findings from the record (all zero without one).
`regression_tests` counts findings with a proposed test and with a no-test reason.
`record` is the record written this run, or `none` when none was written (plan declined,
or a corrupt or foreign file holds the path). `full` is true when `--full` was given.
`confirmed` is true when the user confirmed the plan or passed `--yes`.
