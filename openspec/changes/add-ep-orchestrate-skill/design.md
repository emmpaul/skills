# Design

## Context

The repo already has the pieces this skill chains. OpenSpec's propose and apply workflows exist as the `openspec-propose` / `openspec-apply-change` skills and as the CLI (`openspec new change`, `status --json`, `instructions <artifact> --json`, `validate --strict`). `ep-commit` commits without prompting and ticks OpenSpec tasks. `ep-review` reviews a branch and ends with a parseable `ep-review-summary` block. `ep-babysit-pr` sets the patterns reused here: a state file under `.git/`, an evidence-only score with hard gates (`references/score.md`), sibling skills invoked by name with condensed fallbacks bundled in the skill's own folder, and a Workflow path only on explicit opt-in. `ep-open-pr` owns the one-way or two-way door checklist. `ep-stack split` already cuts layers along OpenSpec task-group boundaries, shows the plan, and creates branches and PRs only after approval. It asks before rewriting any commit that mixes layers. Skills are installed folder by folder, so `ep-orchestrate` cannot read sibling files. See proposal.md for why, and `specs/ep-orchestrate/spec.md` for behavior.

## Goals / Non-Goals

**Goals:**
- The driving session's context grows with the number of phases, not with the size of the diff.
- Any phase can be interrupted and resumed from disk alone.
- The gate decision is reproducible: the same artifacts and repository give the same score.

**Non-Goals:**
- Pushing, PRs, CI, or merging for regular changes. Those stay with `ep-open-pr` and `ep-babysit-pr`. Large changes reach GitHub only through `ep-stack` and `ep-babysit-pr` (D10). This skill never calls `git push` or `gh pr` itself.
- Archiving the change. That happens after merge, outside this skill.
- Running several changes at once, or apply batches in parallel. Batches touch overlapping files and must commit in order.
- Changes to `ep-commit`, `ep-review`, or `shared/context.sh`.

## Decisions

### D1. Layout

```
skills/ep-orchestrate/
  SKILL.md               phases, gates, state file, paths, summary block
  scripts/context.sh     synced copy of shared/context.sh
  references/confidence.md   score items, hard-to-undo checklist, threshold
  references/briefs.md       one brief per phase + its summary-block format,
                             condensed fallbacks for ep-commit and ep-review
```

SKILL.md stays short enough to load in full. A subagent receives only its own section of `briefs.md`.
- Alternative: one large SKILL.md. Rejected because every subagent would load the gate and review text it does not need.

### D2. Phase pipeline and the driving session's role

```
 resolve ──► plan ──► gate ──► apply g1 ──► apply g2 ─ … ─► review r1 ──► fix r1 ──► review r2 … (≤3) ──► report
   │          │        │          │                            │            │
   └──────────┴────────┴──────────┴──── state file updated after every arrow ┴───────────────────────────►
```

The driving session (the "orchestrator") only resolves inputs, decides gates, spawns phases, reads summary blocks, and writes the state file. Work that produces large output (writing artifacts, editing code, running tests, reading diffs) happens inside a phase.

| Phase | With subagents | Without subagents |
|---|---|---|
| resolve | inline: probe, `openspec list --json`, branch and dirty checks | same |
| plan | 1 subagent follows `openspec-propose` (if installed) or the CLI `instructions` loop, then commits the artifacts (`docs(<change>): propose …`); returns `plan-summary` | inline, same steps |
| gate | 1 subagent scores `references/confidence.md` read-only; orchestrator decides | inline, same checklist |
| apply group *n* | 1 fresh subagent per group; inside it, for each task: implement → verify → tick → commit via `ep-commit` (D9); returns `apply-summary` | inline, one group at a time, same per-task commits; after each group, print the resume command and suggest `/clear` or compaction |
| review round *k* | 1 subagent runs `ep-review <branch>`; orchestrator reads only `ep-review-summary` plus the findings list | inline `ep-review` |
| fix round *k* | 1 fresh subagent gets the verified findings; per finding (or shared root cause): fix → test → commit | inline |

The plan subagent works under OpenSpec's planning boundary: it writes artifacts only. The user's request to run `ep-orchestrate` is what authorizes apply, and apply runs in a separate phase after the gate. The OpenSpec planning boundary is therefore kept within each phase.
- Alternative: one long-lived worker subagent for all of apply. Rejected because its context then degrades exactly as the main session's does today.
- Alternative: parallel apply subagents per group. Rejected (see Non-Goals).

### D3. Summary blocks between phases

Every phase returns a flat block, the same convention as `ep-review-summary`:

```
<!-- ep-orchestrate-apply
group: 2
tasks: 2.1,2.2,2.3 done=3 total=3
verification: passed | failed
commits: 2.1=<sha>,2.2=<sha>,2.3=<sha>
head: <sha>
blocker: none | <one line>
-->
```

`plan` returns `change`, `artifacts`, `validate`. `gate` returns `score`, `items: <id>=met|unmet,...`, `hard_to_undo: none | <element>;<element>`. `fix` returns `fixed: <n>`, `deferred: <n>`, `commits: <finding-id>=<sha>,...`, `head`. Exact formats live in `briefs.md`. The orchestrator ignores keys it does not know. If a block is missing or malformed, the orchestrator re-derives the facts from git and `tasks.md` and does not ask the subagent to resend its output.

### D4. Confidence score (`references/confidence.md`)

All-or-nothing items with evidence only, mirroring babysit's score:

| # | Evidence | Weight | Met when |
|---|---|---|---|
| 1 | Validation | 25 | `openspec validate <name> --strict` exits 0 |
| 2 | Traceability | 20 | every `### Requirement:` is covered by at least one task (named or clearly implemented by it) |
| 3 | Verifiable tasks | 15 | every tracked task states a concrete verification (command, test, observable behavior) |
| 4 | Grounded | 15 | every existing file or symbol the design or tasks say to modify exists in the repo |
| 5 | No overlap | 10 | no other active change has a delta for the same capability, and no other active change names the same files in its Impact section |
| 6 | No open questions | 10 | design has no Open Questions section, or each one is marked deferrable, and no `TBD`/`TODO` appears in the artifacts |
| 7 | Size | 5 | at most 6 task groups and 30 tracked tasks |

Threshold: **85**. Item 1 alone (25 points) or items 2 and 3 together (35 points) failing drops the score below 85, so invalid or unverifiable plans always pause.

**Hard-to-undo checklist.** It is checked separately from the score and pauses whatever the score is:
- the one-way door elements from `ep-open-pr` (data or schema, public interfaces, releases or publishing, external side effects, security or access, renames others reference by name), copied in condensed form;
- hard refactors: renaming or moving files or symbols referenced from more than 10 files, or restructuring code across more than 3 top-level directories, counted with `git grep` on the names the tasks mention; deleting modules others import; changing a format persisted on disk;
- anything uncertain counts as hard to undo.

The checklist copy carries a "rules that must match `ep-open-pr`" list, and a task checks the two agree (the same mechanism as `side-paths.md` in `add-ep-side-path-skills` D4).
- Alternative: let the model judge confidence directly. Rejected because the decision must be reproducible and must not drift with the model's mood. That is also the user's explicit constraint that confidence must not be high when undoing is hard.

### D5. Gate decision table

| Hard-to-undo found | Score | `--yes` | Result |
|---|---|---|---|
| yes | any | any | pause; name elements; wait |
| no | ≥ 85 | any | proceed; print score |
| no | < 85 | no | pause; show unmet items; options: approve, revise (run `openspec-update-change` or edit, then re-score), stop |
| no | < 85 | yes | proceed; print score and "proceeding on --yes" |

An existing change named by the user goes through the same gate. Naming a change is not approval of its risk.

### D6. State file

`.git/ep-orchestrate/<change>.json` (inside `.git`, never committed):

```json
{ "change": "add-x", "branch": "feat/add-x", "base": "main@<sha>",
  "phase": "apply", "started_at": "...", "updated_at": "...",
  "gate": { "score": 90, "hard_to_undo": [], "decision": "auto" | "approved" | "paused" },
  "plan_commit": "<sha>",
  "tasks": { "1.1": "<sha>", "1.2": "<sha>", "2.1": "<sha>" },
  "groups": [ { "n": 1, "status": "done" }, { "n": 2, "status": "in_progress" } ],
  "reviews": [ { "round": 1, "critical": 0, "major": 1, "minor": 2, "spec": "passed", "head": "<sha>" } ],
  "blocker": null }
```

On resume, `tasks.md` and `git log` win over the file (spec: "State disagrees with the repository"). A task counts as done when it is ticked and a commit since `base` carries `Task: <id>` in its body (D9). Resume continues at the first task that is not done, so a crash loses at most one task's uncommitted work. The state file carries no diffs, logs, or findings text, so reading it is cheap.

### D7. Review and fix rounds

The review target is the branch against its base (`ep-review <branch>`). The fix subagent receives only the verified findings (location, severity, scenario), not the review transcript. It must not weaken tests or edit specs to match the code. A finding that needs a spec change becomes a blocker and the run stops. Fixes are committed as normal `ep-commit` commits with type `fix`, one per finding or per shared root cause, with `Finding: <dimension> <location>` in the body. They are not `fixup!` commits, because the branch is unpushed and the user may still squash it at PR time. Minor findings are fixed in the same round when cheap. Otherwise they are listed as deferred.

`ep-review` invoked by name when installed. Otherwise `briefs.md#review` carries its condensed four-dimension checklist and summary format. The same applies to `ep-commit` (`briefs.md#commit`). Both condensed copies carry a "rules that must match" list.

**Workflow path (`--workflow`, Claude Code only).** Each review round runs as one Workflow: `pipeline` over the four dimensions → per-finding verify agents (batched to stay under 10 agents) → return confirmed findings. The fix round stays a single subagent, because fixes must be applied serially. Plan and apply never run as a Workflow. They are serial by nature, and a Workflow would add cost without parallelism.

### D8. Gates for local and destructive actions

| Action | Gate |
|---|---|
| implement code | confidence gate (D5) |
| create branch | automatic only when on the default branch; never deletes or resets branches |
| commit | automatic: once for new artifacts, once per verified task, once per review fix (D9); never on the default branch; never `--no-verify` unless the user asked; never amend |
| stash, reset, checkout of user files | never; dirty tree stops the run |
| edit specs or design during apply | never; becomes a blocker |
| push, PR, comment, merge (regular change) | never |
| create stack branches and PRs (large change) | user approves the stack plan shown by `ep-stack split`; declining pushes nothing |
| retarget a layer's PR base | `ep-stack retarget` after the parent's merge is confirmed by `gh`; `ep-stack`'s own confirmation applies |
| merge a layer | only `ep-babysit-pr`, under its hard gates and score ≥ 85; bottom layer first, one layer at a time |
| force-push | never, including on stack layers |

### D9. Commit granularity

The user wants to be able to follow the run, and undo it, step by step. The commit rhythm is fixed, so it cannot slip into one or two large commits:

```
plan      ──► docs(<change>): propose <change>              (artifacts only; skipped for an existing change)
task 1.1  ──► <type>(<change>): <what 1.1 did>   body: Task: 1.1
task 1.2  ──► <type>(<change>): <what 1.2 did>   body: Task: 1.2
…
finding   ──► fix(<change>): <what was wrong>    body: Finding: correctness src/x.py:42
```

- A task's commit includes its code, its tests, and its own `tasks.md` tick, and nothing from other tasks. The apply subagent stages by path (`git add <files>`), never `git add -A`.
- `ep-commit` is told the intended single commit, so it does not regroup the change. If `ep-commit` would split a task into several logical commits (for example, a refactor and then a feature), that is allowed: more commits, never fewer. Each one carries the `Task:` line.
- A task with no file change apart from its tick folds its tick into the next task's commit and lists both ids. The last task in a group commits the tick alone.
- A failed verification commits nothing for that task, so the only uncommitted change is the task in progress.
- The `Task:` and `Finding:` trailers let resume (D6) and the final report map commits to work without reading diffs.
- Alternative: one commit per group. Rejected because the user explicitly wants frequent commits, and a group-sized commit is too big to review or revert on its own.
- Alternative: WIP commits on a timer. Rejected because they don't map to tasks and would need squashing.

### D10. Large changes: stacked delivery

```
review rounds done ──► size check ──► regular ──► report (local branch)
                           │
                           └─ large ──► ep-stack split (layers = task groups) ──► user approves? ── no ──► report (local branch)
                                                                                       │ yes
                                                                                       ▼
                                 ┌──► ep-babysit-pr <bottom PR> ── merged ──► ep-stack retarget ──► next layer ─┐
                                 │                                  │                                          │
                                 └──────────────────────────────────┼──────────────────────────────────────────┘
                                                                    └─ stopped ──► stop; layers above untouched; report
```

- **Threshold.** The plan predicts large when it has more than 6 groups or 30 tasks. The confidence score's size item (D4) already reads this, so the gate output says "large: stacked delivery will be offered". The diff check (more than 800 changed lines or 25 files against base, excluding `openspec/` and lockfiles) runs after review and catches plans that looked small. These numbers live in `references/confidence.md`, so they can be tuned in one place.
- **Why the stack is cut after review, not before.** Reviewing the whole branch once catches cross-layer problems that per-layer reviews miss. Babysit still runs its own review rounds on each layer PR.
- **Cuttable commits.** D9 already gives one commit per task, so layers fall on commit boundaries. When the plan predicts large, the fix subagent also splits each review fix by task group, making one commit per finding per group, so fix commits do not mix layers. When large is detected only from the diff, a mixed fix commit is possible, and `ep-stack` asks how to split it, as its own rules require.
- **Layer mapping.** The orchestrator passes `ep-stack split` the intended grouping as `Task:` id ranges per layer. Adjacent small groups may share a layer, so each layer stays under the diff threshold. The plan `docs(<change>)` commit goes in layer 1.
- **One layer at a time.** Babysit runs only on the bottom open layer, whose PR targets the default branch. Upper layers stay open for human review but are not babysat, because babysit would otherwise merge them into a parent branch. After a merge, `ep-stack retarget` moves the next PR onto the default branch, then babysit starts on it. With subagents, each babysit run is its own subagent, and the orchestrator reads only `ep-babysit-pr`'s summary and `ep-stack`'s `layer:` lines. Without subagents, the same loop runs inline.
- **State.** The state file gains `"size": {"groups", "tasks", "lines", "files", "large"}` and `"stack": [{"layer", "branch", "pr", "state"}]`, so a resumed run continues at the first unmerged layer.
- **No fallback.** Stacking and babysitting are too large to condense into this skill's folder. When either sibling is missing, the run ends as regular and says why.
- Alternative: one large PR babysat as-is. Rejected because the user asked for stacking on huge changes, and a single large PR is hard to review.
- Alternative: split before apply (one change per layer). Rejected because it multiplies OpenSpec changes and gates. A single change with stacked delivery keeps one plan and one review.

## Risks / Trade-offs

- [Score passes but the plan is still subtly wrong] → apply stops on the first verification failure or plan conflict instead of pushing on. Review rounds include spec conformance, so drift is caught before hand-off.
- [Hard-refactor heuristic misses a case (e.g. dynamic references grep cannot see)] → "uncertain counts as hard to undo", and the gate output lists what was counted, so the user can see the basis.
- [Subagent briefs lose detail] → every brief points at artifact paths on disk instead of paraphrasing them. Subagents re-read the artifacts themselves.
- [Condensed fallbacks drift from `ep-commit` / `ep-review` / `ep-open-pr`] → "rules that must match" lists plus a task that diffs them.
- [Long unattended runs on high-score plans surprise the user] → the run is local only, every task is its own commit, and the final report lists every commit, so any task can be reverted or the run reset to any task boundary on the unpushed branch.
- [Stacked delivery merges code unattended] → it only starts after the user approves the stack plan. Each merge passes babysit's existing hard gates and score, and a stopped layer halts everything above it.
- [Size threshold misjudges reviewability] → both numbers are shown with the classification, and the user can decline the stack and fall back to a regular run.
- [Many small commits clutter history] → accepted; the user can squash at PR time (`ep-open-pr` / squash merge), and fine-grained history is the goal during the run.
- [Token cost of fresh subagents re-reading artifacts] → accepted; it is the price of a lean driving context. Briefs ask subagents to read only the artifacts their phase needs.
