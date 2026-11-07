# Run record reference

Where the run record lives, what it holds, when a check is skipped, and how earlier
findings carry over. Read in step 1 (load), step 3 (version items, skips, and re-check
items), step 5 (toolchain comparison), steps 6 and 8 (re-check outcomes), and step 9
(write).

## Location

The record is `<audit-file stem>.state.json` in the same folder as the **requested** audit
path: `qa-audit.md` pairs with `qa-audit.state.json`, `--out reports/qa.md` with
`reports/qa.state.json`. The requested path is the default or `--out` path, never the
dated fallback (`qa-audit-<YYYY-MM-DD-HHMM>.md`), so a run that had to write a dated
report still loads and updates `qa-audit.state.json`. Each `--out` path keeps its own
record.

Like the audit file, the record stays uncommitted and out of `.gitignore`. Both are left
out of "Files changed by the audit". The user deletes the record to start fresh.

## Format

```json
{
  "tool": "ep-qa",
  "version": 1,
  "target": "repo | path:<p>",
  "report": "<audit file path written this run>",
  "head": "<sha>",
  "dirty": false,
  "toolchain": {"node": "v20.11.0", "python3": "Python 3.12.1"},
  "last_id": 3,
  "generated": ["<untracked path the audit's own commands created>", "..."],
  "checks": [
    {
      "key": "<sha256>",
      "id": "P4",
      "result": "passed | failed | flaky",
      "sha": "<head the check actually ran on>",
      "deps": ["<path>", "..."],
      "fingerprint": "<sha256>",
      "prereqs": ["<key>", "..."]
    }
  ],
  "findings": [
    {
      "id": "QA-3",
      "title": "...",
      "severity": "critical | major | minor",
      "area": "setup | build | lint | types | tests | runtime | docs",
      "check_key": "<key of the check that found it>",
      "repro": ["<step>", "..."],
      "first_seen": "<sha>",
      "status": "open | fixed",
      "fixed_at": "<sha, when fixed>",
      "regression_test": {"path": "...", "framework": "...", "code": "..."}
    }
  ]
}
```

- `key` is the sha256 of the check's area, its exact command or probe, the directory it
  runs in, and the sorted **names** of the env variables it sets. Any change to one of
  these is a different check.
- `sha` is the head the check last ran on. A skipped check keeps the `sha`, `result`, and
  `fingerprint` from the record.
- `generated` lists untracked, non-ignored paths that the audit's own commands created
  (a `__pycache__/` folder, a coverage file), kept out of every fingerprint.
- `last_id` is the highest `QA-<n>` number any run of this record has issued, including
  findings since fixed and dropped from `findings`.
- `regression_test` is present only when a test was proposed (`references/audit.md`,
  "Regression test proposals"); it holds code with placeholders, never a secret.
- The record holds **no command output, no env values, and no secrets**: results, shas,
  paths, hashes, and the reproduction steps only (the steps are redacted as in the report).

## Loading (step 1)

With `--full`, use nothing from the record: every check runs, finding ids start at
`QA-1`, and the record is replaced at the end. The report's "Run record" line says
`previous record ignored: --full`. Still run the first three checks of the table below
on the file at the record path, only to protect it: a corrupt or foreign file is left
untouched and no record is written this run, with the same report line and fix hint as
without `--full`. An ep-qa record of any target is replaced.

Otherwise the record is **usable** only when all hold:

| Check | When it fails | Report says | Record path at the end |
|---|---|---|---|
| the file exists | no record | nothing to ignore; first run | written |
| it parses as JSON | **corrupt** | `previous record ignored: corrupt` | left untouched; no record written this run |
| `"tool": "ep-qa"` and a known `version` (1) | **foreign** | `previous record ignored: not an ep-qa record` | left untouched; no record written this run |
| `target` equals this run's target | **other target** | `previous record ignored: other target (<its target>)` | replaced |

An unusable record counts as absent: nothing is skipped and there are no earlier findings
to re-check. For a corrupt or foreign file, the report and output also say how to fix it:
move or delete `<record path>` and run again.

## Toolchain versions (steps 3 and 5)

A version check is a project command too: `./gradlew --version` runs the repository's
wrapper script and may download Gradle, and `pnpm --version` under corepack may download
pnpm. So no version command runs before confirmation, and none runs when the plan is
declined or not confirmed.

- **Step 3:** once the items exist, add one **version item** per toolchain a plan item
  uses (the interpreter or compiler behind each command, the package manager, and any
  wrapper): area `setup`, command `node --version`, `python3 --version`, `go version`,
  `cargo --version`, `pnpm --version`, `./gradlew --version`, ..., source: the plan items
  that use it. Version items come first in the plan. An item that passes every other skip
  condition is marked `skip if toolchain unchanged: unchanged since <sha>` (the toolchain
  condition cannot be checked yet). Version files such as `.nvmrc`, `.tool-versions`, the
  `packageManager` field, or `gradle/wrapper/gradle-wrapper.properties` are read, not
  run, and are already in every fingerprint.
- **Step 5:** the version items run first. The toolchain versions are a global
  invalidator (below): when any version differs from the record's `toolchain`, the
  record's `toolchain` lacks it, or a version item was dropped, failed, or did not run,
  every `skip if toolchain unchanged` is cleared and those items run as confirmed. Only
  when every version matches do they stay skipped.
- Store this run's map (the version items' output) in the record; with no confirmed
  plan, nothing ran and the record stays as it was.

## Fingerprint

For each check, whatever its area, `deps` is the whole target, Markdown files and `docs/`
included: tests read `.md` fixtures and scripts read reference docs, so no file kind is
left out. Narrower sets are not used: which files a test reads needs coverage data the
audit cannot trust. For a path target, `deps` also holds the files
outside the target that configure it: the lockfiles and manifests (the Lockfiles and
Manifests rows of `references/plan.md`) in each folder from the target's parent up to the
repository root, so a workspace root's `pnpm-lock.yaml` or `package.json` is included,
and every other root file discovery read for the target (a workspace file such as
`pnpm-workspace.yaml` or `go.work`, the root CI workflow or task runner an item came
from).

Compute the fingerprint from the **working tree**, not `HEAD`, so uncommitted edits,
added files, and deleted files all change it. Run it with bash and keep `-z`: without it,
git quotes paths with non-ASCII or special characters (`"tests/na\303\257ve_test.py"`),
`[ -f ]` fails on the quoted name, and that file silently drops out of the fingerprint:

```bash
git ls-files -z -co --exclude-standard -- <deps> | LC_ALL=C sort -z | while IFS= read -r -d '' f; do
  [ -f "$f" ] && printf '%s %s\n' "$f" "$(git hash-object -- "$f")"
done | sha256sum
```

Add the `git hash-object` of each env file the item reads (`.env` and similar), even when
it is ignored: its hash only, never its contents. Exclude the record and every audit
file: the requested audit path and any file whose first line starts with
`<!-- ep-qa audit:`, such as a dated fallback (`qa-audit-<YYYY-MM-DD-HHMM>.md`) an earlier
run wrote, so a new report does not change the fingerprint of every `docs` check.

Also exclude files the audit itself creates, so a run does not invalidate the next one:
leave out every untracked path that is under the record's `generated` list, or that is
not in this run's step 1 before-snapshot (it appeared during the run). A path that is
tracked by git is never excluded. When writing the record, set `generated` to the
loaded record's paths that are still present and untracked, plus the untracked paths of
the after-snapshot (step 9) that are not in the before-snapshot, collapsing a created
folder to one entry.

## Skipping unchanged checks (step 3)

Skip a plan item (the check's recorded `sha` as `<sha>`) only when **every** condition
holds; any doubt means it runs. Step 3 checks conditions 1, 2, 4, and the files of 3, and
marks the item `skip if toolchain unchanged: unchanged since <sha>`; step 5 checks the
toolchain part of 3 ("Toolchain versions"):

1. The record has a check with the same `key` whose `result` is `passed`. A `failed` or
   `flaky` check always runs again.
2. Its fingerprint, recomputed now, equals the recorded one.
3. No **global invalidator** changed since the record: the lockfiles and manifests in the
   target and, for a path target, in each folder above it up to the repository root (the
   Lockfiles and Manifests rows of `references/plan.md`), the toolchain versions from
   the version items, checked in step 5 ("Toolchain versions"), and the CI or
   task-runner file the item came from (a changed `Makefile` test recipe changes the
   item). The files among these are in every check's `deps`
   (Fingerprint), so a change to any of them, inside the target or above it, changes the
   fingerprint of every check; the toolchain versions are compared with the record's
   `toolchain`.
4. Every prerequisite (by `prereqs`) has the same key as before. A changed or new
   prerequisite command invalidates every item that depends on it.

Items the record does not know run. Items marked `not covered` are decided afresh each
run.

## Checks never skipped

- A check that failed or was flaky on its last run.
- A version item ("Toolchain versions"): it decides the other skips. It is not stored in
  `checks`.
- A `--url` probe: the remote app changes without the repository changing.
- A re-check item for an earlier finding (below).
- The item `run proposed regression tests in a scratch copy` (`references/plan.md`): its
  tests encode this run's findings, so it runs whenever a finding is reproduced.
- A **prerequisite that produces state** (install, build, a started server) of any item
  that runs: when a probe must run, the server start it needs runs too, and so does that
  start's install and build. It is shown as run, never as skipped. Walk `prereqs` down
  from every item that runs and clear the skip on each one reached.
- A server's stop item (`references/plan.md`, "Running"): it runs whenever its start
  runs, and is never skipped on its own.

In step 5, a skipped item whose toolchain matched does not run; its result is copied
from the record. The shown plan marks it `skip if toolchain unchanged: unchanged since
<sha>`; the report table shows `skipped, unchanged since <short sha>`, or its run result
when step 5 cleared the skip.

## Earlier findings (steps 3 and 8)

Each finding with `status: open` in a usable record gets one re-check plan item (area of
the finding, command: its `repro`, source: `record <id>`), which runs whatever the
fingerprints say. A re-check item whose reproduction needs a server this run starts
(a request to it) is placed in that start's window, after its probes and before its stop
item, and runs there (`references/plan.md`, "Running", Start window);
when that start does not run or is not ready, the item is `not re-checked` (blocked
prerequisite), and no server is restarted for it. A re-check item whose reproduction is
itself a start of the app gets its own window instead, after the previous window's stop
item ran and its port is confirmed free: a port check, the start as the reproduction
gives it, the check, then its own stop item (planned as "Stop items" there says), never
overlapping another start. The others run in step 8. Either
way it ends in one of:

| Outcome | When | Report |
|---|---|---|
| **still failing** | the reproduction fails again (a flaky finding: fails in either of two runs) | keeps its `QA-<n>` id and `first_seen`, gets fresh evidence, `Status: still failing (first seen <sha>)` |
| **fixed** | the reproduction passes (a flaky finding: passes twice) | listed under "Fixed since last run" with the current head sha; `status: fixed` and `fixed_at` in the record |
| **not re-checked** | the reproduction could not run (toolchain missing, blocked prerequisite, plan declined, item dropped) | stays `open`, listed under "Not covered" with the reason |

Judge whether a reproduction fails by the finding's own failure (its title, and its proposed
regression test when it has one), not by the exit code alone: a probe that now exits
non-zero with a clear error, as its finding expected, passes.

A new candidate with the same root cause as an open finding is that finding, not a new
one. New findings take ids after the **highest** number the record has issued: the
larger of its `last_id` and the highest `QA-<n>` in its `findings` (fixed ones
included), so an id is never reused, even after its finding was dropped. The findings
section is still ranked by severity, area, and plan order; ids do not follow rank.

## Writing (step 9)

Write the record after the audit file whenever the plan was confirmed, even when every
check was skipped as unchanged (the record is then written again with the carried-over
checks, so the summary names it rather than `none`):

- **Plan declined, or not confirmed:** nothing executed; leave the record exactly as it
  was (or absent).
- **Corrupt or foreign file at the record path:** leave it untouched and write none; the
  summary says `record: none`.
- Otherwise write the full record: every check of this run (skipped ones with their
  carried-over `sha`, `result`, and `fingerprint`; run ones with the fingerprint computed
  before they ran), every open finding, and the findings fixed this run with `status:
  fixed`. Drop findings fixed in an earlier run, and set `last_id` to the highest
  number issued so far (the loaded record's, or this run's highest id when larger), so
  a dropped id is never issued again.

Write atomically: a temp file in the same folder (`<record path>.tmp-<pid>`), then rename
it over the record path, so an interrupted run leaves the old record or the new one,
never half of one.
