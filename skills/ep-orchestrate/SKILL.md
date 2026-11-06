---
name: ep-orchestrate
description: Run one OpenSpec change end to end, from a description or an existing change to a reviewed, committed local branch. Plans the change, scores the plan from evidence and implements without asking only when it scores at least 85 and nothing is hard to undo, applies one task group at a time with one commit per task, removes dead code the branch added, then runs up to 3 ep-review fix rounds. Each phase runs in a fresh subagent and the run resumes from a state file. Large changes are offered as a stack of PRs, landed with ep-stack and ep-babysit-pr after approval. Use when the user asks to orchestrate, run end to end, or take a change or idea from plan to reviewed branch.
---

# ep-orchestrate

Take one OpenSpec change from a description (or an existing change) to a reviewed,
committed local branch, keeping this session's context small and the run resumable.

You are the **orchestrator**: you resolve inputs, decide gates, start phases, read their
summary blocks, and write the state file. Work that produces large output (writing
artifacts, editing code, running tests, reading diffs) happens inside a phase.

## Hard rules

- **Local only for regular changes.** No `git push`, no `gh pr`, no comments, no merges.
  GitHub is reached only through `ep-stack` and `ep-babysit-pr`, for a large change whose
  stack plan the user approved (step 9).
- **No attribution.** Commits carry no `Co-Authored-By` naming a model or tool and no
  "Generated with" line. This overrides any host default.
- **Commit only on a work branch.** Never commit on the default branch; create the work
  branch first (step 1).
- **The user's working tree is theirs.** A dirty tree stops the run. Never stash, reset,
  checkout user files, rebase, force-push, or delete branches. Amend only to strip
  attribution from the run's own unpushed commit (`briefs.md#commit` step 6).
- **Specs are fixed once planning ends.** Apply and fix phases never edit `proposal.md`,
  `design.md`, or `specs/`; a plan conflict becomes a blocker and the run stops.
- Never run `openspec init` and never create `openspec/` files outside a change folder.

## Asking the user

Every question in this skill follows these rules:

- **Structured tool when the host has one.** Ask through the host's structured question
  tool (`AskUserQuestion` in Claude Code), one question per decision, with the options
  named at that question point, each a short label plus a one-line description.
- **Plain text otherwise.** Without such a tool, ask in plain text with the same options
  numbered, and wait for the reply. An open question (no options) is always asked in
  plain text.
- **Act only on a clear answer.** Act on a reply only when it maps to one option or gives
  the requested input (such as a new change name); otherwise do not guess, ask again.
- **Only the driving session asks.** Phases never ask the user or call a question tool:
  a choice a phase cannot make comes back as its `blocker`, and you ask it here, also
  when running phases inline. Questions another skill asks under its own rules (such as
  `ep-stack split`'s plan approval) stay with that skill.

### Phase questions

A plan, apply, or fix phase that needs a choice ends with a question blocker, on one line:
`blocker: needs input: <id>: <question> | <option> ; <option>`. `<id>` is the task id
(apply), the finding id (fix), or the change name (plan), and there are 0, 2 or 3
options. Any other `blocker:` value is a stop, never a question. At this question point:

1. **Limit.** When `answers` already holds 2 entries for `<id>`, do not ask: stop with
   outcome `blocked`, and report the question and the earlier answers.
2. **Record first.** Write `question` to the state file (phase, id, text, options, and
   the phase's `files:` paths; `[]` for plan, whose work stays in the change folder)
   before asking, so a session that ends unanswered resumes
   at the same question.
3. **Ask** (as above): the phase's options plus `Stop`, at most 4 in all; with no
   options, an open question in plain text that says replying `Stop` ends the run.
4. **Answer.** Append `{ "q": <question>, "a": <answer> }` to `answers.<id>` and set
   `question` to `null`. Then re-run the phase as its step says (4, 6, or 8), passing every
   recorded answer as `answers:` lines (`<id>: <question> => <answer>`) and, for apply and
   fix, the blocked paths as `partial: <id>: <path>,<path>`. Every later run of a phase
   that covers an id with recorded answers (a group or fix run again after a stop, on
   resume, or for another question) gets that id's `answers:` lines too.
5. **`Stop`** ends the run with outcome `blocked`, reported as the phase's step says.
   `question` stays set, so the next run asks it again.

With subagents, the re-run is a fresh subagent; without them, the phase runs inline
again. Either way the question is asked here, between phases, never mid-phase.

## Usage

```
ep-orchestrate <description>       # propose a new change, then run it
ep-orchestrate <change-name>       # run (or resume) an existing active change
ep-orchestrate ... --yes           # skip the score threshold (never the hard-to-undo pause)
ep-orchestrate ... --workflow      # Claude Code: run review rounds as a Workflow
```

The bundled files live in this skill's folder (the directory containing this SKILL.md):
`references/confidence.md` (gate), `references/briefs.md` (one brief per phase, summary
formats, fallbacks for `ep-commit` and `ep-review`), `scripts/context.sh` (probe).

## 1. Resolve

1. **Probe**, from the repository root: `bash <skill-dir>/scripts/context.sh`. If bash is
   unavailable or the probe fails, run `git status --porcelain=v1 -b`,
   `git symbolic-ref --short refs/remotes/origin/HEAD` (or `gh repo view --json
   defaultBranchRef`), and `openspec list --json` inline.
2. **No OpenSpec root** (`openspec` is null, or `openspec list --json` reports
   `root: null`): stop. Say the skill needs an OpenSpec root and that the user can run
   `openspec init` themselves. Create nothing. Outcome `needs_openspec`.
3. **Input.** The argument names an active change (`openspec list --json`): use it.
   Otherwise it is a description: derive a kebab-case name of 2-5 words with a verb
   prefix such as `add-`, `fix-`, `update-`, `rename-`, or `remove-`. If that name matches an existing
   change, ask (see "Asking the user") with the options `Continue <change>` and
   `Use a different name`; take the new name from the reply or a follow-up plain
   question.
4. **State.** If `.git/ep-orchestrate/<change>.json` exists, this is a resume: go to
   "Resume" below.
5. **Clean tree.** Any staged, unstaged, or untracked path outside
   `openspec/changes/<change>/` stops the run: list the paths. Outcome `dirty_tree`.
6. **Branch.** On the default branch (or detached HEAD), create and switch to
   `<type>/<change>` (`git switch -c`), where `<type>` comes from the change name's
   prefix: `fix-` → `fix`, `docs-` → `docs`, `refactor-` → `refactor`, else `feat`. If that branch exists,
   create nothing and ask (see "Asking the user") with the options `Continue on <branch>`
   (`git switch <branch>`, no new branch) and `Stop` (the run ends; no state file). On any
   other branch, stay on it.
7. **Base.** `base` = `<ref>@<sha>`, where `<ref>` is the default branch and `<sha>` is
   `git rev-parse HEAD` now, before the run's first commit. On a new branch that is the
   default branch's tip; on an existing branch it keeps the user's earlier commits out
   of the run (dead code, review, and size cover only this run's commits; say so when
   the branch already had commits). Pass `<ref>` where a skill wants a branch name and
   `<sha>` where a brief wants the base sha. Create the state file (step 2).

## 2. State file

`.git/ep-orchestrate/<change>.json` (inside `.git`, never committed). Create the folder if
needed. Write it after every phase and every group; it holds no diffs, logs, or finding
text. Values not known yet are `null`; `plan_commit` stays `null` for an existing change
whose artifacts were already committed before `base`.

```json
{ "change": "add-x", "branch": "feat/add-x", "base": "main@<sha>",
  "phase": "resolve|plan|gate|apply|deadcode|review|fix|stack|done",
  "started_at": "<iso>", "updated_at": "<iso>",
  "flags": { "yes": false, "workflow": false },
  "gate": { "score": 90, "unmet": [], "hard_to_undo": [], "decision": "auto|approved|paused",
            "artifacts": "<plan fingerprint when scored>" },
  "plan_commit": "<sha|null>",
  "deadcode": { "removed": 0, "reported": 0, "head": "<sha>" },
  "tasks": { "1.1": "<sha>" },
  "groups": [ { "n": 1, "status": "done|reviewing|in_progress|pending", "start": "<sha>" } ],
  "group_reviews": [ { "group": 1, "critical": 0, "major": 1, "minor": 2, "spec": "passed",
                       "head": "<sha>", "fixed": 1, "unfixed": 2 } ],
  "reviews": [ { "round": 1, "critical": 0, "major": 1, "minor": 2, "spec": "passed", "head": "<sha>",
                 "fixed": 1, "deferred": 0 } ],
  "size": { "groups": 4, "tasks": 14, "lines": null, "files": null, "large": false },
  "stack": [ { "layer": 1, "branch": "...", "pr": 12, "state": "open" } ],
  "question": { "phase": "apply|fix|plan", "id": "2.3", "text": "<question>",
                "options": ["<option>", "<option>"], "files": ["<path>"] },
  "answers": { "2.3": [ { "q": "<question>", "a": "<answer>" } ] },
  "blocker": null, "outcome": null }
```

`groups[].start` is `git rev-parse HEAD` just before the group's first apply phase. A
group is `reviewing` once its tasks are all done and until its review pass, and its fix
phase when one runs, finish; only then is it `done`. `group_reviews` holds one entry per
group pass (step 6): its counts and `head`, then `fixed` and `unfixed`, both `null` until
the pass's fix phase ends (with no fix phase, `fixed` is 0 and `unfixed` the minor count).
`phase` stays `apply` while group passes run.

`question` is the open phase question, or `null` when none is open: the phase, the task
id, finding id, or change name, the question text, its options (`[]` when open), and the
paths holding the blocked work (the phase's `files:`, `[]` for `none`). `answers` keeps,
per id, every question asked and its answer, in order; the length of an id's list is its
question count. Both hold short user-facing text, not diffs, logs, or finding text.

Finding text lives in `.git/ep-orchestrate/<change>.findings` instead: the latest review's
label (the round number `<k>`, or `g<n>` for the pass after group `<n>`) and its
`finding:` lines, unchanged, then the `commits:` line of each fix block of that review.
Overwrite it when a review round or a group pass returns and append to it after each fix
block, so a fix question can be resumed in the same review. Step 8's first round
overwrites the last group pass's file.

`.git/ep-orchestrate/<change>.group-findings` keeps the group passes' findings for the
report: when a group pass ends (after its fix phase, when one runs), append its label and
the `finding:` lines that have no fix commit, which are its minor and deferred findings.

### Resume

Run again on a change with a state file, `tasks.md` and git win over the file:

0. HEAD must be on the recorded `branch`. If it is not, stop and ask the user to switch
   back to it (`git switch <branch>`); do not rebuild state from another branch.
1. A task is **done** when its `tasks.md` line is `- [x]` **and** a commit in
   `<base-sha>..HEAD` has a `Task:` line naming `<id>` (a folded tick names two ids)
   (`git log --format='%H%n%B' <base-sha>..HEAD`).
2. If the file disagrees (a recorded sha is not on the branch, a task it marks done is
   unticked, or ticked tasks lack a commit), say exactly what differed and rebuild
   `tasks`, `groups`, and `phase` from `tasks.md` and git.
3. The clean-tree check (step 1.5) still applies; the only acceptable leftovers are
   inside the change folder. When `question` is set, uncommitted changes in exactly the
   paths in `question.files` are accepted too; any other path stops the run with outcome
   `dirty_tree`, listing those paths.
4. **Open question first.** When `question` is set, first check whether the user has
   resolved it since: for apply, its task is done (step 1); for fix, a commit in
   `<base-sha>..HEAD` that is not in the `commits:` lines of `<change>.findings` has a
   `Finding:` line naming the finding's `<dimension> <file>:<line>`. If so, set `question`
   to `null` without asking (for fix, append `commits: <finding id>=<sha>` to
   `<change>.findings`) and continue at the recorded phase. Otherwise ask it again at the
   phase question point ("Phase questions") before running any phase, then continue at the recorded
   phase with the answer. When none of `question.files` still has changes (the user
   discarded them), leave `partial:` out: the task or finding starts fresh, and the
   answer still applies. For a fix question, re-run the fix phase of the round in
   `<change>.findings` (step 8.4), taking the findings and their fix commits from that
   file; never run a new review for it. When that file is missing, set `question` to `null`
   and stop with outcome `blocked`: say the round's findings are lost and list
   `question.files`, which the user commits or discards before running again.
5. Continue at the first unfinished phase: skip planning when the artifacts exist, keep
   a gate decision of `auto` or `approved` only while the plan is unchanged since it was
   scored (its "Plan fingerprint" in `references/confidence.md` equals `gate.artifacts`;
   ticks do not change it; otherwise re-run the gate), re-ask a `paused` one, continue apply at
   the first task that is not done, and run the dead-code check unless `deadcode` is
   recorded. Stack runs continue at the first unmerged layer.

## 3. How phases run

Each phase follows its section of `references/briefs.md` and ends with a summary block.

| Phase | With subagents | Without subagents |
|---|---|---|
| plan | 1 fresh subagent, brief `#plan` | inline, same section |
| gate | 1 fresh subagent, brief `#gate` (read-only) | inline |
| apply group *n* | 1 fresh subagent per group, brief `#apply` | inline, one group at a time |
| group pass *n* | 1 fresh subagent, brief `#review` with `group: <n>` | inline, after the group |
| group fix *n* | 1 fresh subagent, brief `#fix` with round `g<n>` | inline, after the pass |
| dead code | 1 fresh subagent, brief `#deadcode` | inline |
| review round *k* | 1 fresh subagent, brief `#review` | inline |
| fix round *k* | 1 fresh subagent, brief `#fix` | inline |
| stack | split and retarget in this session; 1 subagent per babysit run | inline, layer by layer |

**With subagents:** give each subagent the path of `briefs.md`, the name of its section,
and the inputs that section lists: names, shas, and paths, never pasted artifact text.
Read back only its summary block (for review, also its `finding:` lines). Do not read
diffs, logs, or artifact bodies yourself; short lookups (status, counts, names, shas,
the `tasks.md` headings and task ids) are fine.

**Without subagents:** run the same sections yourself, in the same order, with the same
gates, state file, and summary blocks; reading artifacts and diffs inside a phase is then
yours to do. After every phase (plan, gate, each apply group, each group pass and its
fix, dead code, each review and fix round, each stack layer), print `Resume with: ep-orchestrate <change>` and
suggest clearing or compacting context before continuing. Questions still come only at
this file's question points (see "Asking the user"), never mid-phase: a phase's open
choice ends it with a `blocker`, as with subagents.

If a summary block is missing or malformed, re-derive its facts from git and `tasks.md`
(commits and `Task:` lines since base, ticks, `git rev-parse HEAD`). Do not ask the
phase to resend.

## 4. Plan

- **Description given:** run the `plan` phase. On a question blocker (its id is the
  change name), ask it at the phase question point ("Phase questions" under "Asking the
  user") and re-run the plan phase with the answer. `Stop` ends the run with outcome
  `blocked`. Record `plan_commit`.
- **Existing change:** check `openspec status --change <change> --json` shows every
  `applyRequires` artifact done; otherwise run the `plan` phase with `mode: complete` to
  write the missing ones only. Never regenerate existing artifacts. Uncommitted files in the change folder
  are committed on their own as `docs(<change>): propose <change>` (briefs `#commit`
  rules) before any code changes.

## 5. Gate

Run the `gate` phase, then decide with the table in `references/confidence.md`
("Gate decision"):

- Print the score report: each item met or not with its weight, the total, the
  hard-to-undo result with what was counted, and the size (`large: stacked delivery will
  be offered` when predicted large).
- **Hard to undo found:** pause and name each element in the printed text, even at
  score 100 and even with `--yes`, then ask as below.
- **Score < 85 without `--yes`:** pause, list the unmet items in the printed text, and
  ask as below.
- **Otherwise:** proceed and state the score proceeded on (and "proceeding on --yes"
  when that is why).

Record `score`, `unmet`, `hard_to_undo`, `decision`, and `artifacts` (the "Plan
fingerprint" from `references/confidence.md`, computed now) under `gate`, so a resume can
keep the decision.

**At a pause** (either kind), first write `decision: paused` with those fields and
`outcome: paused_at_gate` to the state file, and print the report (step 10) with its
summary block, so a session that ends unanswered has already recorded the pause and the
next run resumes at the same question. Then ask (see "Asking the user"); the question
carries only the decision, with the options:

- `Approve`: set `decision: approved`, clear `outcome` to `null`, and continue to apply.
- `Revise`: clear `outcome` to `null`, run `openspec-update-change` or edit the
  artifacts, commit them as `docs(<change>)`, then re-run the gate.
- `Stop`: the run ends; the outcome stays `paused_at_gate`.

Make no code change before the answer.

## 6. Apply

Groups are the `## ` headings of `tasks.md` holding tracked tasks, in file order. For each
group with tasks not done, record its `start` (`git rev-parse HEAD`) and set it
`in_progress` before its first apply phase, then start one `apply` phase (one fresh
subagent per group). Never run groups in parallel: they commit in order.

After each group, read the `ep-orchestrate-apply` block and record each `commits` sha
under `tasks`, then check: every done task has a commit whose `Task:` line names it, and
the group finished before the next one starts. Then:

- `blocker: none` and all done: set the group `reviewing` and run its group pass (below);
  the next group starts after it.
- `blocker: none` but `done` below `total` (the phase ended early): run the group again
  in a fresh phase, once; it skips the tasks already done. Still short: stop as
  `blocked` naming the unfinished tasks.
- **Question blocker** (`blocker: needs input: <id>: ...`): the task stays unticked and
  its work uncommitted. Ask it at the phase question point ("Phase questions"), with the
  block's `files:` as the blocked paths. On an answer other than `Stop`, run the same
  group again with `answers:` and `partial: <id>: <files>`; it skips the tasks already
  done and continues the blocked task from its uncommitted work. With subagents that is a
  fresh subagent; without, the group runs inline again. This does not stop the run.
- **`Stop` at that question**, `verification: failed`, or any other blocker (`plan:`,
  `<id>: ticked but not done`, a failure): stop. The task stays unticked and its work
  uncommitted; record the blocker and report it, and tell the user that the next run
  needs that work finished and committed (with `Task: <id>` in the commit body), or
  discarded, by them (the clean-tree check stops otherwise; after `Stop` it accepts the
  recorded paths and asks the question again, see "Resume"). Outcome `blocked`.

A group that stops with tasks not done gets no pass until it finishes, including after a
re-run with an answer.

### Group pass

Each group gets exactly one review pass, once every task of it is done (after any apply
re-run) and before the next group starts; for the last group, before step 7. A group is
never reviewed twice: the next group's pass and step 8 cover its fix commits.

1. **Review.** Run the `review` phase with `group: <n>`, the group's `start` as the base
   sha, and HEAD as its head. It never runs as a Workflow, with or without `--workflow`.
   Append a `group_reviews` entry with its counts and `head` (`fixed` and `unfixed`
   `null`), and overwrite `<change>.findings` with label `g<n>` and its `finding:` lines.
2. **Clean** (the step 8.2 test: `critical=0 major=0` and `spec_conformance: passed`):
   run no fix phase; set `fixed: 0` and `unfixed` to the minor count; go to 4.
3. **Not clean:** run one `fix` phase with round `g<n>`, the pass's `finding:` lines, and
   `large_predicted` and `groups:` as in step 8. Append its `commits:` line to
   `<change>.findings`. Then, by its `blocker`, as in step 8.4:
   - **Question blocker** (`blocker: needs input: g<n>.<m>: ...`): ask it at the phase
     question point and, on an answer other than `Stop`, run the fix phase again for the
     pass's findings with no fix commit yet, with `answers:` and `partial:`. The re-run
     is never a new pass; repeat this step on its block.
   - **`Stop` at that question**, a `spec:` blocker (never asked), or any other blocker:
     stop the run with outcome `blocked`, reporting the blocker and any uncommitted paths.
   - **`blocker: none`:** set `fixed` to the findings with a fix commit and `unfixed` to
     the rest.
4. **Finish.** Append the label `g<n>` and the pass's `finding:` lines with no fix commit
   to `<change>.group-findings`, set the group `done`, write the state file, and start
   the next group.

## 7. Dead code

When every task is done, run the `deadcode` phase once, before any review, so review
covers its removals. It removes dead code the branch added (one `refactor(<change>)`
commit per removal with a `Dead-code:` line, tests run after each) and reports, without
removing, code that may be public, reached dynamically, or hard to undo. Record
`removed`, `reported`, and `head` under `deadcode`. Reported items go in the final report;
they never stop the run.

## 8. Review rounds

When every task is done, run up to 3 rounds. Round *k*:

1. Run the `review` phase on the branch against `base`. Record its counts and `head`,
   and write its `finding:` lines to `<change>.findings` (see "State file").
2. **Clean** (`critical=0 major=0` and `spec_conformance: passed`; the review phase is
   always told the change name, so `not_applicable` counts as not clean): stop
   the rounds; its minor findings go in the report.
3. **Round 3 not clean:** stop; list the remaining findings; no fourth round. Outcome
   `review_limit`.
4. Otherwise run the `fix` phase with that round's `finding:` lines (and the task groups
   when large is predicted, as in `briefs.md#fix`). Append its `commits:` line to
   `<change>.findings`. Then, by its `blocker`:
   - **Question blocker** (`blocker: needs input: <finding id>: ...`): fixes of other
     findings stay committed and only that finding's work is uncommitted. Ask it at the
     phase question point ("Phase questions"), with the block's `files:` as the blocked
     paths. On an answer other than `Stop`, run the fix phase of the same round again,
     only for the round's findings with no fix commit yet (from the `commits:` of the
     earlier fix blocks, kept in `<change>.findings`), with `answers:` and `partial: <finding id>: <files>`. With
     subagents that is a fresh subagent; without, the fix phase runs inline again. The
     re-run is not a new review round; repeat this step on its block.
   - **`Stop` at that question**, or any other blocker (such as `spec:` for a finding
     that needs a spec change, which is never asked): stop the run with outcome
     `blocked`, reporting the blocker and any uncommitted paths.
   - **`blocker: none`:** start round *k+1* on the new head.

**Workflow path (`--workflow`).** In Claude Code with a Workflow tool, the user's
`--workflow` is the opt-in: run each review round's step 1 as one Workflow, a `pipeline`
over the four dimensions (each agent gets its checklist from `briefs.md#review-fallback`,
the change name, and the base and head shas), feeding each dimension's findings to verify
agents that try to disprove them: at most 5 verify agents in total, each taking a batch
of findings across dimensions, so the Workflow has at most 9 agents. It returns the confirmed findings and counts; build the
`finding:` lines and `ep-review-summary` from them. The fix round stays one subagent. Plan
and apply never run as a Workflow. With `--workflow` but no Workflow tool, say so and use
the subagent or inline path.

## 9. Size and delivery

Measure the reviewed branch with "Large-change thresholds" in
`references/confidence.md` and record `size`. The change is **large** when it was
predicted large at the gate or the diff is over the thresholds; report the classification
with groups, tasks, lines, and files.

**Regular change:** done. Nothing is pushed. Suggest `ep-open-pr`, then `ep-babysit-pr`.
Outcome `reviewed` (or `review_limit` / `blocked` from step 8).

**Large change**, once the review rounds end without a blocker (`reviewed` or
`review_limit`; each layer is reviewed again by `ep-babysit-pr`):

- `gh` missing or unauthenticated, or `ep-stack` or `ep-babysit-pr` not available to you:
  push nothing. Report the change as large, name the missing piece, and recommend
  installing it (`npx skills add emmpaul/skills --skill <name>`) or splitting by hand.
  The outcome stays what step 8 gave (`reviewed` or `review_limit`).
- Otherwise ask (see "Asking the user") with the options `Deliver as a stack` and
  `Keep the local branch`, and push nothing before the answer. `Keep the local branch`
  ends the run as regular (outcome from step 8). `Deliver as a stack` follows
  `briefs.md#stack`, where `ep-stack split`'s own plan approval still applies. Layers
  are task groups (adjacent small groups may share one, so each layer stays under the
  diff thresholds); the plan commit, when it is on the branch, goes in layer 1. Gates:

| Action | Gate |
|---|---|
| create stack branches and PRs | the user approves the plan `ep-stack split` shows; declining pushes nothing and the run ends as regular (outcome from step 8) |
| babysit | only the bottom open layer, one at a time |
| retarget the next PR | after `gh pr view` shows the parent `MERGED`; `ep-stack retarget`'s own confirmation applies |
| merge a layer | only `ep-babysit-pr`, under its hard gates and score ≥ 85 |
| force-push | never, on any layer |

A layer whose babysit stops without merging stops the run: layers above it are left
untouched, the layer and reason go in `stack` and `blocker`. Outcome `stacked_stopped`;
all layers merged gives `stacked_merged`.

## 10. Report

On every stop, print: change, branch, outcome, the gate result, every commit made this
run (`git log --format='%h %s' <base-sha>..HEAD`, once `base` exists), the dead-code
removals and reported items, review rounds with counts, remaining or deferred findings, the size classification, stack layers if any, what the user should
do next, and the resume command when the run is unfinished. Set `outcome` in the state
file when it exists (early stops in step 1 create none). Then end with:

```
<!-- ep-orchestrate-summary
change: <change>
branch: <branch>
head: <sha>
outcome: needs_openspec | dirty_tree | paused_at_gate | blocked | reviewed | review_limit | stacked_merged | stacked_stopped
gate: score=<n> decision=<auto|approved|paused|none> hard_to_undo=<none|element ; element>
tasks: done=<n> total=<n>
deadcode: removed=<n> reported=<n>
reviews: rounds=<n> last=critical=<n>,major=<n>,minor=<n> spec=<passed|failed|not_applicable>
remaining: <ids of unfixed critical or major findings, or none>
size: groups=<n> tasks=<n> lines=<n|na> files=<n|na> large=<yes|no>
layer: <i> pr=<n> state=<state>
blocker: none | <one line>
-->
```

One `layer:` line per stack layer, bottom-up; omit `layer:` lines when there is no stack.
Any value not known yet is written `na` (for example `gate: score=na decision=none
hard_to_undo=none`, `reviews: rounds=0 last=na`, `large=na`).
