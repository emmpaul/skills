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
  checkout user files, amend, rebase, force-push, or delete branches.
- **Specs are fixed once planning ends.** Apply and fix phases never edit `proposal.md`,
  `design.md`, or `specs/`; a plan conflict becomes a blocker and the run stops.
- Never run `openspec init` and never create `openspec/` files outside a change folder.

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
   change, ask whether to continue that change or pick a different name.
4. **State.** If `.git/ep-orchestrate/<change>.json` exists, this is a resume: go to
   "Resume" below.
5. **Clean tree.** Any staged, unstaged, or untracked path outside
   `openspec/changes/<change>/` stops the run: list the paths. Outcome `dirty_tree`.
6. **Branch.** On the default branch (or detached HEAD), create and switch to
   `<type>/<change>` (`git switch -c`), where `<type>` comes from the change name's
   prefix: `fix-` → `fix`, `docs-` → `docs`, `refactor-` → `refactor`, else `feat`. If that branch exists,
   ask. On any other branch, stay on it.
7. **Base.** `base` = `<default>@<sha>` with sha `git merge-base HEAD <default>` (prefer
   `origin/<default>` when it exists). Create the state file (step 2).

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
  "gate": { "score": 90, "unmet": [], "hard_to_undo": [], "decision": "auto|approved|paused" },
  "plan_commit": "<sha|null>",
  "deadcode": { "removed": 0, "reported": 0, "head": "<sha>" },
  "tasks": { "1.1": "<sha>" },
  "groups": [ { "n": 1, "status": "done|in_progress|pending" } ],
  "reviews": [ { "round": 1, "critical": 0, "major": 1, "minor": 2, "spec": "passed", "head": "<sha>",
                 "fixed": 1, "deferred": 0 } ],
  "size": { "groups": 4, "tasks": 14, "lines": null, "files": null, "large": false },
  "stack": [ { "layer": 1, "branch": "...", "pr": 12, "state": "open" } ],
  "blocker": null, "outcome": null }
```

### Resume

Run again on a change with a state file, `tasks.md` and git win over the file:

1. A task is **done** when its `tasks.md` line is `- [x]` **and** a commit in
   `<base-sha>..HEAD` carries `Task: <id>` in its body
   (`git log --format='%H%n%B' <base-sha>..HEAD`).
2. If the file disagrees (a recorded sha is not on the branch, a task it marks done is
   unticked, or ticked tasks lack a commit), say exactly what differed and rebuild
   `tasks`, `groups`, and `phase` from `tasks.md` and git.
3. The clean-tree check (step 1.5) still applies; the only acceptable leftovers are
   inside the change folder.
4. Continue at the first unfinished phase: skip planning when the artifacts exist, keep
   a gate decision of `auto` or `approved`, re-ask a `paused` one, continue apply at
   the first task that is not done, and run the dead-code check unless `deadcode` is
   recorded. Stack runs continue at the first unmerged layer.

## 3. How phases run

Each phase follows its section of `references/briefs.md` and ends with a summary block.

| Phase | With subagents | Without subagents |
|---|---|---|
| plan | 1 fresh subagent, brief `#plan` | inline, same section |
| gate | 1 fresh subagent, brief `#gate` (read-only) | inline |
| apply group *n* | 1 fresh subagent per group, brief `#apply` | inline, one group at a time |
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
gates, state file, and summary blocks. After the plan, the gate, and each apply group,
print `Resume with: ep-orchestrate <change>` and suggest clearing or compacting context
before continuing.

If a summary block is missing or malformed, re-derive its facts from git and `tasks.md`
(commits and `Task:` lines since base, ticks, `git rev-parse HEAD`). Do not ask the
phase to resend.

## 4. Plan

- **Description given:** run the `plan` phase. On `blocker: needs input`, ask the user
  the question and re-run. Record `plan_commit`.
- **Existing change:** check `openspec status --change <change> --json` shows every
  `applyRequires` artifact done; otherwise run the `plan` phase to complete the missing
  ones only. Never regenerate existing artifacts. Uncommitted files in the change folder
  are committed on their own as `docs(<change>): propose <change>` (briefs `#commit`
  rules) before any code changes.

## 5. Gate

Run the `gate` phase, then decide with the table in `references/confidence.md`
("Gate decision"):

- Print the score report: each item met or not with its weight, the total, the
  hard-to-undo result with what was counted, and the size (`large: stacked delivery will
  be offered` when predicted large).
- **Hard to undo found:** pause and name each element, even at score 100 and even with
  `--yes`, then offer the same three options as below.
- **Score < 85 without `--yes`:** pause, list the unmet items, and offer: approve,
  revise (run `openspec-update-change` or edit the artifacts, commit them as
  `docs(<change>)`, then re-run the gate), or stop.
- **Otherwise:** proceed and state the score proceeded on (and "proceeding on --yes"
  when that is why).

A paused run records `decision: paused`, ends with outcome `paused_at_gate`, and makes
no code change. The user's approval sets `decision: approved` and continues to apply.

## 6. Apply

Groups are the `## ` headings of `tasks.md` holding tracked tasks, in file order. For each
group with tasks not done, start one `apply` phase (one fresh subagent per group). Never
run groups in parallel: they commit in order.

After each group, read the `ep-orchestrate-apply` block and record each `commits` sha
under `tasks`, then check: every done task has its own commit with a `Task:` line, and
the group finished before the next one starts. Then:

- `blocker: none` and all done: mark the group done; next group.
- `verification: failed` or any blocker: stop. The task stays unticked and its work
  uncommitted; record the blocker and report it. Outcome `blocked`.

## 7. Dead code

When every task is done, run the `deadcode` phase once, before any review, so review
covers its removals. It removes dead code the branch added (one `refactor(<change>)`
commit per removal with a `Dead-code:` line, tests run after each) and reports, without
removing, code that may be public, reached dynamically, or hard to undo. Record
`removed`, `reported`, and `head` under `deadcode`. Reported items go in the final report;
they never stop the run.

## 8. Review rounds

When every task is done, run up to 3 rounds. Round *k*:

1. Run the `review` phase on the branch against `base`. Record its counts and `head`.
2. **Clean** (`critical=0 major=0`, `spec_conformance` passed or not_applicable): stop
   the rounds; its minor findings go in the report.
3. **Round 3 not clean:** stop; list the remaining findings; no fourth round. Outcome
   `review_limit`.
4. Otherwise run the `fix` phase with that round's `finding:` lines (and the task groups
   when large is predicted). A `blocker` (for example a finding needing a spec change)
   stops the run with outcome `blocked`. Then start round *k+1* on the new head.

**Workflow path (`--workflow`).** In Claude Code with a Workflow tool, the user's
`--workflow` is the opt-in: run each review round's step 1 as one Workflow, a `pipeline`
over the four dimensions (each agent gets its checklist from `briefs.md#review-fallback`,
the change name, and the base and head shas), feeding each dimension's findings to verify
agents that try to disprove them, batched up to 5 findings per agent, so the Workflow
stays under 10 agents. It returns the confirmed findings and counts; build the
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

**Large change**, after a clean review only:

- `gh` missing or unauthenticated, or `ep-stack` or `ep-babysit-pr` not available to you:
  push nothing. Report the change as large, name the missing piece, and recommend
  installing it (`npx skills add emmpaul/skills --skill <name>`) or splitting by hand.
  Outcome `reviewed`.
- Otherwise offer stacked delivery and follow `briefs.md#stack`. Layers are task groups
  (adjacent small groups may share one, so each layer stays under the diff thresholds);
  the plan commit, when it is on the branch, goes in layer 1. Gates:

| Action | Gate |
|---|---|
| create stack branches and PRs | the user approves the plan `ep-stack split` shows; declining pushes nothing and the run ends as regular (`reviewed`) |
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
remaining: <finding ids, or none>
size: groups=<n> tasks=<n> lines=<n|na> files=<n|na> large=<yes|no>
layer: <i> pr=<n> state=<state>
blocker: none | <one line>
-->
```

One `layer:` line per stack layer, bottom-up; omit `layer:` lines when there is no stack.
Any value not known yet is written `na` (for example `gate: score=na decision=none
hard_to_undo=none`, `reviews: rounds=0 last=na`, `large=na`).
