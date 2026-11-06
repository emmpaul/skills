# Phase briefs

One section per phase. The orchestrator hands a phase worker (a fresh subagent, or itself
when running inline) **only** its section, plus the inputs listed there. Inputs are names,
shas, and paths: never paste artifact text, diffs, or logs into a brief. The worker reads
the artifacts from disk itself.

Every phase ends by printing its summary block exactly as shown, as the last thing in its
output. Values are flat `key: value` lines. Lists of ids or shas are comma-separated with no
spaces; lists of free-text items are separated by ` ; `.
The orchestrator reads only that block (and, for review, the findings list).

Rules for every phase:

- Work from the repository root, on the branch named in the inputs. Never switch
  branches, stash, reset, rebase, push, or touch GitHub. Amend only to strip attribution
  from your own unpushed commit ([commit](#commit) step 6).
- Never commit on the default branch: before every commit, check
  `git rev-parse --abbrev-ref HEAD` equals the input branch.
- When a phase commits through `ep-commit`, tell it the intended commit and to just
  commit, so it skips its plan prompt and does not regroup.
- Commit messages carry no model or tool attribution (no `Co-Authored-By` naming a model
  or tool, no "Generated with" line). This overrides any host default.
- Never edit the change's `proposal.md`, `design.md`, or `specs/` after the plan phase.
  When they turn out wrong, stop and report it as the `blocker`.
- Never ask the user or call a question tool, and never wait for a reply. A choice you
  cannot make ends the phase with a question blocker, on one line:
  `blocker: needs input: <id>: <question> | <option> ; <option>`. `<id>` is the task id
  (apply), the finding id (fix), or the change name (plan). Give 0, 2 or 3 options; with
  0, drop the ` | ` part and the question is asked open. The orchestrator asks it and
  re-runs the phase with the answer.
- A conflict with the specs or design is never a question: it is a `plan:` blocker
  (plan, apply) or a `spec:` blocker (fix). Any `blocker:` value other than
  `needs input:` stops the run.

## plan

**Inputs:** change name, `mode: new` with the user's description, or `mode: complete`
(an existing change missing some artifacts), branch, path of this file.

With `mode: complete`, skip creating the change and `openspec-propose`: run only the CLI
loop below for the artifacts that are not `done`, leaving existing ones untouched. With
`mode: new`:

1. Create the change and every artifact apply needs:
   - **If the skill `openspec-propose` is available to you**, follow it for this change
     name and description.
   - **Otherwise** use the CLI loop: `openspec new change <change>`, then repeat
     `openspec status --change <change> --json` → for the first artifact with status
     `ready`, `openspec instructions <artifact> --change <change> --json` → write the file
     at its output path following the instruction and template, until every artifact in
     `applyRequires` is `done`.
2. Planning boundary: write files under `openspec/changes/<change>/` only. Edit no code.
3. You cannot ask the user questions, even where `openspec-propose` would. Its
   "stop after planning" rule is met by this phase ending; the orchestrator decides
   what runs next. When the
   description leaves a choice open, pick the
   conservative option and state it in `design.md` (Decisions). When it is too vague to
   plan at all, stop with a `blocker` naming the question.
4. Run `openspec validate <change> --strict`. Fix what it reports in the artifacts; record
   the final result.
5. Commit the artifacts on their own, through `ep-commit` when it is available to you
   (as in apply), otherwise [commit](#commit): `git add -- openspec/changes/<change>/`,
   subject `docs(<change>): propose <change>`, body one or two sentences from the
   proposal's Why.

```
<!-- ep-orchestrate-plan
change: <change>
artifacts: <ids of the artifacts that exist, e.g. proposal,specs,design,tasks>
validate: passed | failed
commit: <sha | none>
head: <sha>
blocker: none | <one line>
-->
```

## gate

**Inputs:** change name, path of `references/confidence.md`.

Read-only. Compute the score and the hard-to-undo checklist exactly as in
`references/confidence.md`, and print its report format without the `Decision:` line:
the orchestrator decides. Change no files and make no commits.

```
<!-- ep-orchestrate-gate
score: <0-100>
items: validation=met|unmet,traceability=met|unmet,verifiable=met|unmet,grounded=met|unmet,no_overlap=met|unmet,no_open_questions=met|unmet,size=met|unmet
unmet: <id> <one line> ; <id> <one line>   (or none)
hard_to_undo: none | <element> ; <element>
counts: <name>=<files>,...   (or none)
size: groups=<n> tasks=<n> large=yes|no   (predicted from tasks.md; no diff yet)
-->
```

## apply

**Inputs:** change name, group number, the group's task ids (in order), branch, base sha,
path of this file. Artifact paths: `openspec/changes/<change>/{proposal,design,tasks}.md`
and `specs/**/spec.md`.

Read the change's proposal, design, specs, and `tasks.md` first. Then, for each task of
the group, in order, finish the task before starting the next:

1. **Check** its line in `tasks.md` is still `- [ ]` with the same text. If it is already
   `- [x]` and a commit since the base sha has a `Task:` line naming it, skip it. If it
   is `- [x]` with no such commit (for example the user finished it by hand, or a folded
   tick was never committed), run its verification on the current code: when it passes,
   commit any of its uncommitted files (or, with none, an empty commit via
   `git commit --allow-empty`) as `chore(<change>): record task <id>` with
   `Task: <id>`; when it fails, stop with `blocker: <id>: ticked but not done`.
2. **Implement** only that task. Keep the change minimal and inside what the specs and
   design describe.
3. **Verify** with the task's stated verification (command, test, observable check). On
   failure, fix and re-run, at most 3 attempts. Never skip, delete, loosen, or xfail a
   test to pass.
4. **Tick** `- [ ]` → `- [x]` on that task's line only.
5. **Commit** the task on its own (the commit rhythm below).

Stop the group at the first of:

- verification still fails after 3 attempts: leave the task unticked and its work
  uncommitted; `verification: failed`, `blocker: <id>: <failure in one line>`
- the specs or design are wrong or incomplete for this task: change nothing in them;
  leave the task's work uncommitted; `blocker: plan: <what conflicts>`

### Commit rhythm

- One commit per task: its code, its tests, and its own `tasks.md` tick, nothing from
  any other task. Stage by path (`git add -- <files>`), never `git add -A` or `git add .`.
- Subject `<type>(<change>): <what the task did>`, where type is `feat`, `fix`,
  `refactor`, `test`, `docs`, `build`, `ci`, or `chore` per what the task changed. Body
  ends with `Task: <id>`.
- **If the skill `ep-commit` is available to you**, invoke it and tell it the intended
  single commit (files, subject, the `Task:` line), that the tick is already made, and
  to just commit, so it skips its plan prompt and does not regroup. If it splits the task into
  several logical commits (for example a refactor, then the feature), allow it: more
  commits, never fewer. Each one carries the `Task:` line. **Otherwise** follow
  [commit](#commit).
- A task with no file change apart from its tick: fold the tick into the next task's
  commit and list both ids (`Task: 2.3, 2.4`). When it is the last task of the group,
  commit the tick alone.
- A failed task commits nothing.

```
<!-- ep-orchestrate-apply
group: <n>
tasks: <id>,<id>,<id> done=<n> total=<n>
verification: passed | failed
commits: <id>=<sha>,<id>=<sha>
head: <sha>
blocker: none | <one line>
-->
```

## deadcode

**Inputs:** change name, branch, base sha, path of `references/confidence.md`,
`large_predicted: yes|no` (and the task groups, as in [fix](#fix), when yes).

Runs once, after every task is done and before the first review round.

1. **Candidates.** From `git diff <base-sha>...HEAD`, list every symbol the branch adds
   (functions, classes, methods, constants, files, imports, parameters) and every
   pre-existing symbol whose references the branch removed. For each, count references
   outside its own definition: `git grep -n -w <name>`. Also run the repo's own
   dead-code tool when it is already configured (a script, config file, or dev
   dependency for `vulture`, `knip`, `ts-prune`, `staticcheck`, `deadcode`, or the
   compiler's unused warnings). Never install a tool. Unreachable branches the diff adds
   (code after a `return`, conditions that cannot be true) are candidates too.
2. **Not dead**, whatever the counts: code that implements a spec requirement of the
   change, even when only tests reach it; entry points (`main`, CLI commands, scripts in
   the package manifest); framework or plugin hooks. Tests are not callers for anything
   else: code reached only by tests and no requirement is dead.
3. **Remove or report.**
   - Dead code the branch added: remove it, unless it is exported from a public
     interface (a published package's exports, a documented CLI or API), registered or
     looked up by name (decorators, registries, `getattr`, reflection, config strings),
     or may be reached dynamically: report those and leave them.
   - Pre-existing code the branch orphaned: remove it only when it is internal (no
     export from a public interface, nothing in the README or docs) and passes the
     hard-to-undo checklist in `references/confidence.md`. Otherwise report it.
4. **Per removal** (or per group of removals sharing one cause): remove it, run the
   tests, then commit, staging by path: subject `refactor(<change>): remove unused
   <what>`, body ends with `Dead-code: <file>:<symbol>` (one line per item). Through
   `ep-commit` when available, as in apply; otherwise [commit](#commit). When the tests
   fail, restore the removed code (`git checkout -- <its files>`, only files you changed
   for it), commit nothing for it, and report it.
5. **When `large_predicted: yes`:** split removals per task group, as in fix step 5, so
   no commit mixes stack layers.

Never touch specs, design, or proposal, and never weaken tests. A test that exists only
for removed dead code goes in the same commit as the code.

```
<!-- ep-orchestrate-deadcode
removed: <n>   (items, one per `Dead-code:` line)
reported: <n>
commits: <file>:<symbol>=<sha>,...   (or none)
report: <file>:<symbol> <reason> ; ...   (or none)
head: <sha>
-->
```

## review

**Inputs:** branch, base sha, change name, round number.

Review the branch against its base. Post nothing to GitHub.

- **If the skill `ep-review` is available to you** and the base sha equals
  `git merge-base <branch> origin/<default>` (`<default>` when there is no remote; this
  is what `ep-review <branch>` diffs against), invoke
  `ep-review <branch>` (no `--comment`) and tell it the change name, so spec conformance
  runs against it.
- **Otherwise** (not installed, or the base sha differs, for example a run started on a
  branch that already had commits) follow [review](#review-fallback) with the base
  sha.

Then print the findings list (`finding: none` when there are none), one line per **verified** finding, ids numbered
`r<round>.<n>` (for example `r1.2`, distinct from task ids), and finally the `ep-review-summary` block exactly as the review produced
it:

```
finding: r<round>.<n> <dimension> <severity> <file>:<line> | <summary> | <scenario>
```

## fix

**Inputs:** change name, branch, round number, the verified findings (the `finding:`
lines from review, unchanged), `large_predicted: yes|no`, and when yes, the group of each
task id (`groups: 1=1.1-1.3,2=2.1-2.4`).

For each critical or major finding, and each minor one that is cheap to fix:

1. Fix the cause in code or tests. Group findings that share one root cause and fix them
   once.
2. Never weaken tests to pass, and never edit specs, design, or proposal to match the
   code. A finding whose fix needs a spec change is not fixed: count it as deferred and
   set `blocker: spec: <finding id> <one line>`.
3. Run the tests that cover the fix (and the suite when cheap). A fix whose tests fail
   after 3 attempts is reverted from the working tree (`git checkout -- <its files>`,
   only files you changed for it) and deferred.
4. **Commit** each fix on its own, staging by path: subject `fix(<change>): <what was
   wrong>`, body ends with `Finding: <dimension> <file>:<line>` (one line per finding the
   commit fixes). Through `ep-commit` when available, as in apply; otherwise
   [commit](#commit). Normal commits, never `fixup!`.
5. **When `large_predicted: yes`:** a fix that touches code from several task groups is
   split into one commit per group (files from one group each), each with the same
   `Finding:` line and `Group: <n>`, so no fix commit mixes stack layers. Assign a file
   to the group whose task created or last changed it (`git log -1 --format=%B -- <file>`
   and read its `Task:` line).

Minor findings left unfixed are counted as deferred, with no blocker.

```
<!-- ep-orchestrate-fix
round: <k>
fixed: <n>
deferred: <n>
commits: <finding-id>=<sha>,<finding-id>=<sha>
head: <sha>
blocker: none | <one line>
-->
```

## stack

Runs only for a large change, after the review rounds, when `ep-stack` and
`ep-babysit-pr` are both available. **Inputs:** change name, branch, base, the layer
grouping as `Task:` id ranges per layer (`layer 1: plan commit, 1.1-1.4`; adjacent small
groups may share a layer), and fix and dead-code commits per layer from their `Group:`
lines. When the change was large by diff only, those commits have no `Group:` lines and
may mix groups: pass them as they are; `ep-stack` asks how to place or split them.

This section runs in two parts, because only the user can approve the plan.

**Part 1, split (in the driving session, not a subagent):**

1. Invoke `ep-stack split <ref>` (the `<ref>` part of `base`, never `<ref>@<sha>`) and tell it the intended grouping. Fix commits sit
   after all task commits, so a fix for an early layer must move down to it: `ep-stack`
   asks how to handle that (its own rule), which is fine, because the branch is unpushed.
2. `ep-stack` shows its plan and waits. Its approval is the user's approval of the stack.
   Declined: nothing is pushed; the run ends as a regular run.
3. Read its `ep-stack-summary`: one `layer:` line per layer.

**Part 2, land layers, bottom up, one at a time:**

1. Babysit only the bottom open layer (its PR targets the default branch):
   `ep-babysit-pr <pr>`. With subagents, run each babysit in its own subagent, which polls
   inside its session. Read the result from `.git/ep-babysit/<pr>.json` (`outcome`:
   `merged`, `closed`, or `stopped: <reason>`) and the subagent's final report line, not
   its transcript.
2. `merged`: confirm with `gh pr view <pr> --json state` (`MERGED`). Then invoke
   `ep-stack retarget` in the driving session (it shows the base change and waits for
   confirmation, its own rule), read its `layer:` lines, and continue with the next layer.
3. Anything else: stop. Do not touch the layers above. Record the layer and the reason.

Never force-push, never merge outside `ep-babysit-pr`, and never retarget a layer whose
parent has not merged.

```
<!-- ep-orchestrate-stack
outcome: declined | merged | stopped
layer: <i> pr=<n> state=<planned|open|merged|closed|stopped>
stopped_reason: none | <one line>
-->
```

## commit

Condensed `ep-commit` steps, used **only when the skill `ep-commit` is not available to
you**. Commit without a plan prompt: the phase already decided what one commit holds.

### Committing

1. Check the branch is not the default branch.
2. Stage exactly the files of this commit: `git add -- <files>`.
3. Match the repo's style from `git log -n 15 --format='%s%n%b---'` (subject length,
   casing). Without a signal: lowercase imperative subject, no period, ≤ 72 characters.
4. Write the message to a temp file and commit with it:

   ```bash
   msg=$(mktemp)
   cat > "$msg" <<'MSG'
   feat(<change>): add slugify helper

   Task: 1.2
   MSG
   git commit -F "$msg"
   rm -f "$msg"
   ```

5. If a hook fails, fix the cause and commit again. Never `--no-verify`.
6. Check `git log -1 --format=%B` has no attribution line; if it does, rewrite it with
   `git commit --amend -F <file>` (your unpushed commit, removing attribution only).

**Rules that must match** (`ep-commit/SKILL.md`):

- Conventional Commits `type(scope): subject`, types `feat`, `fix`, `docs`, `style`,
  `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`; `!` and a
  `BREAKING CHANGE:` footer for breaking changes.
- Scope is the active OpenSpec change name when the diff relates to it.
- Match the repo's observable conventions; default to lowercase imperative, no period,
  ≤ 72 characters, body wrapped at 72 explaining why.
- Message from a file (`git commit -F`), never `-m` alone.
- No model or tool attribution; human `Co-Authored-By` lines the user asks for are fine.
- No amend, rebase, reset, or squash of pushed commits; amend an unpushed commit only to
  remove attribution or when the user asks.
- Never push; never `--no-verify` unless the user asks; on hook failure fix and retry.
- Tick a task only when the commit fully implements it, inside that commit.

## review fallback

Condensed `ep-review` steps, used **only when the skill `ep-review` is not available to
you**. Read-only: change no files and post nothing.

1. **Diff:** `git diff <base-sha>...<branch>`. Read whole changed functions and callers
   of changed signatures, not only hunks. Empty diff: report nothing to review.
2. **Spec input:** the change's `proposal.md`, `tasks.md`, and every `specs/**/spec.md`.
3. **Four dimensions**, one after another (with subagents, one per dimension in
   parallel, each without the others' results). Report only what the diff introduces or
   touches.
   - **correctness:** logic and operators, edge inputs (empty, null, zero, negative,
     large, unicode, duplicates), error paths, state and cleanup, concurrency, callers
     of changed contracts, data changes, removed code still in use.
   - **spec:** each requirement implemented (missing: critical if core, else major); no
     code path contradicts a scenario's THEN (major); outward behavior no requirement
     describes is out-of-spec; each scenario tested or covered by a documented
     verification (an untested scenario belongs here, not under tests); out-of-spec
     behavior is major when it has outward effects, else minor; an untested scenario is
     major when it guards a destructive or outward action, else minor; removed
     requirements really gone; ticked tasks really done (major if not).
   - **tests:** changed behavior has tests that would fail without the change;
     assertions check outcomes; bug fixes have a regression test; edge and error paths
     covered where they matter; no test deleted, skipped, or weakened; tests are
     deterministic.
   - **security:** injection; secrets committed or logged; authn and authz on new entry
     points; input validation at trust boundaries (size, type, path traversal,
     deserialization); unsafe defaults; unexpected or unpinned new dependencies;
     destructive or outward actions gated; sensitive data in errors, logs, or telemetry.
4. **Finding shape:** dimension, severity, file, line, summary, scenario (concrete input
   or state → wrong output, crash, leak, or missing behavior), evidence. No scenario, no
   finding. Severity: **critical** breaks core behavior, loses data, is exploitable, or a
   required spec behavior is missing entirely; **major** is wrong in a realistic case or a
   requirement is partly implemented; **minor** is real but low impact.
5. **Deduplicate** within each dimension only (same root cause: keep one, higher
   severity).
6. **Verify** each candidate by trying to disprove it: re-read the code and the paths
   reaching it, check the scenario can occur, check existing handling and tests, re-read
   the requirement and search the codebase for spec findings, run the test when cheap and
   safe. Drop what cannot occur, downgrade what is smaller than claimed.
7. **Summary block**, exactly:

```
<!-- ep-review-summary
target: branch:<name>
head: <commit sha reviewed>
verified: critical=<n> major=<n> minor=<n>
by_dimension: correctness=<n> spec=<n> tests=<n> security=<n>
spec_conformance: passed | failed | not_applicable
dropped_in_verification: <n>
-->
```

`spec_conformance` is `passed` when the spec dimension has no verified critical or major
finding, `failed` otherwise. `dropped_in_verification` counts findings refuted in step 6
only.

**Rules that must match** (`ep-review/SKILL.md`):

- Four dimensions: correctness, spec, tests, security; deduplicate within a dimension,
  never across.
- Every reported finding has a location, severity, and concrete failure scenario, and
  survived a disproval attempt.
- Severity scale critical, major, minor as in `ep-review`'s `references/dimensions.md`.
- Read-only without `--comment`; no attribution in anything posted.
- Summary keys: `target`, `head`, `verified` (critical, major, minor), `by_dimension`
  (correctness, spec, tests, security), `spec_conformance`
  (passed | failed | not_applicable), `dropped_in_verification`.
