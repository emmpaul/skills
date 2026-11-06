# Spec Delta

## Purpose

Runs one OpenSpec change end to end, from a description or an existing change to a reviewed, committed local branch, while keeping the driving session's context small and resumable.

## ADDED Requirements

### Requirement: OpenSpec root required
The skill SHALL require an OpenSpec root. When the repository has none, it SHALL stop before writing anything, say that it needs OpenSpec, and SHALL NOT run `openspec init` or create `openspec/` files.

#### Scenario: Repository without OpenSpec
- **WHEN** the skill runs in a repository where `openspec list --json` reports `root: null`
- **THEN** it stops with a message that the skill needs an OpenSpec root, and no files, branches, or commits are created

### Requirement: Start from a description or an existing change
The skill SHALL accept either a free-text description, from which it proposes a new change with all artifacts, or the name of an existing active change, which it picks up without regenerating its artifacts.

#### Scenario: Description given
- **WHEN** the user runs the skill with a description and no change of the derived name exists
- **THEN** the skill creates the change and writes every artifact needed for apply, then runs the confidence gate

#### Scenario: Existing change named
- **WHEN** the user names an active change whose artifacts are complete
- **THEN** the skill skips planning, keeps the artifacts unchanged, and runs the confidence gate

#### Scenario: Name collides with an existing change
- **WHEN** the derived name matches an existing change and the user did not name it
- **THEN** the skill asks whether to continue that change or create one with a different name

### Requirement: Clean start on a work branch
The skill SHALL stop when the working tree has uncommitted changes outside the change folder. When started on the default branch, it SHALL create a `<type>/<change-name>` branch before the first commit and SHALL never commit to the default branch.

#### Scenario: Dirty tree
- **WHEN** the working tree has uncommitted changes outside `openspec/changes/<name>/`
- **THEN** the skill stops and lists them, without stashing or committing

#### Scenario: Started on the default branch
- **WHEN** the current branch is the repository's default branch
- **THEN** the skill creates and switches to a branch such as `feat/<change-name>` before any commit

### Requirement: Evidence-based plan confidence score
Before implementing, the skill SHALL compute a plan confidence score from 0 to 100 using only verifiable evidence about the artifacts and repository, and SHALL show the score with each item's result.

#### Scenario: Score shown
- **WHEN** the confidence gate runs
- **THEN** the output lists each evidence item as met or not met with its weight, and the total

#### Scenario: Failing validation lowers the score
- **WHEN** `openspec validate <name> --strict` fails
- **THEN** the validation item is not met and the score reflects it

### Requirement: Hard-to-undo changes always pause
The skill SHALL pause for user approval, whatever the score, when the plan is a one-way door or would need a hard refactor to undo, such as a broad rename, a public interface change, a data or format migration, or a cross-cutting restructure. It SHALL name each element that triggered the pause.

#### Scenario: Public interface change
- **WHEN** the change's specs or tasks remove or rename a CLI flag, config key, API, or exported symbol that others depend on
- **THEN** the skill pauses, names that element, and does not implement until the user approves

#### Scenario: Broad restructure
- **WHEN** the tasks move, rename, or restructure code across many modules
- **THEN** the skill pauses even if the score is 100

#### Scenario: Unsure about reversibility
- **WHEN** the skill cannot tell whether an element is reversible
- **THEN** it treats the element as hard to undo and pauses

### Requirement: Confidence gate decision
When no hard-to-undo element is found, the skill SHALL implement without asking if the score is at least 85, and SHALL pause for user approval otherwise. A `--yes` option SHALL skip the score threshold but SHALL NOT skip the hard-to-undo pause.

#### Scenario: High confidence, reversible
- **WHEN** the score is 85 or more and no hard-to-undo element is found
- **THEN** the skill proceeds to apply and states the score it proceeded on

#### Scenario: Low confidence
- **WHEN** the score is below 85
- **THEN** the skill shows the unmet items and waits for the user to approve, revise the plan, or stop

#### Scenario: --yes with a hard-to-undo element
- **WHEN** the user passed `--yes` and the plan contains a hard-to-undo element
- **THEN** the skill still pauses for approval

### Requirement: Batched apply with verification
The skill SHALL implement tasks one task group at a time, in order, run each task's stated verification, and tick the task in `tasks.md` only when its verification passes. It SHALL finish a group before starting the next.

#### Scenario: Group completes
- **WHEN** every task in a group is implemented and verified
- **THEN** all of the group's tasks are ticked and committed, and the next group starts

#### Scenario: Verification fails
- **WHEN** a task's verification still fails after the batch's fix attempts
- **THEN** the skill stops, leaves the task unticked and its work uncommitted, records the failure in the state file, and reports it

#### Scenario: Plan turns out wrong
- **WHEN** implementing a task shows that the specs or design are wrong or incomplete
- **THEN** the skill stops and reports the conflict instead of silently changing the specs

### Requirement: Frequent, traceable commits
The skill SHALL commit in small steps following `ep-commit` conventions, with no model or tool attribution. It SHALL commit newly written planning artifacts on their own, each task on its own once verified, together with its `tasks.md` tick, and each review fix on its own. It SHALL NOT batch several tasks or a whole group into one commit.

#### Scenario: Planning artifacts committed
- **WHEN** the skill has written a new change's artifacts and before it edits any code
- **THEN** it commits them as one `docs(<change>)` commit

#### Scenario: One commit per task
- **WHEN** a group of three tasks completes
- **THEN** the branch has three new commits, each scoped to the change, each naming its task id (for example `2.1`) in the body, and each including that task's tick in `tasks.md`

#### Scenario: Task with no file changes
- **WHEN** a task's work produces no file change apart from its tick (for example a pure verification task)
- **THEN** the tick is committed on its own, or with the next task's commit, and the commit body names both task ids

#### Scenario: Progress is visible mid-run
- **WHEN** the run is interrupted during group 2
- **THEN** `git log` shows one commit per finished task, and the unfinished task's work is the only uncommitted change

### Requirement: Dead-code check before review
After all tasks are done and before the first review round, the skill SHALL check the branch for dead code it added or orphaned, remove dead code the branch added (one commit per removal, tests run after each), and report instead of removing anything that may be public, reached dynamically, or hard to undo. Code that implements a spec requirement SHALL NOT count as dead.

#### Scenario: Unused helper added by the branch
- **WHEN** a task added a function that no code, test, or spec requirement uses
- **THEN** the skill removes it in its own `refactor(<change>)` commit whose body names it on a `Dead-code:` line, before review round 1

#### Scenario: Possibly reachable from outside
- **WHEN** an unreferenced symbol is exported from a public interface, registered by name, or may be reached dynamically
- **THEN** the skill leaves it in place and lists it in the report

#### Scenario: Removal breaks tests
- **WHEN** the tests fail after a removal
- **THEN** the skill reverts that removal, commits nothing for it, and lists it in the report

#### Scenario: No dead code
- **WHEN** the check finds no dead code
- **THEN** no commit is made and the review rounds start

### Requirement: Review rounds
After all tasks are done, the skill SHALL run `ep-review` on the branch and fix its verified findings, for at most 3 rounds. It SHALL stop early when a round has no verified critical or major findings and spec conformance passes. Fixes SHALL be committed separately from the apply commits, one commit per finding or shared root cause.

#### Scenario: Clean first round
- **WHEN** the first review round reports `critical=0 major=0` and `spec_conformance: passed`
- **THEN** the skill does not run another round and reports the minor findings, if any

#### Scenario: Findings fixed
- **WHEN** a round reports verified critical or major findings
- **THEN** the skill fixes them with one commit per finding, or per root cause when several findings share one, and runs the next round on the updated branch

#### Scenario: Round limit reached
- **WHEN** the third round still reports critical or major findings
- **THEN** the skill stops, lists the remaining findings, and does not start a fourth round

### Requirement: Fresh-context phases
When it can spawn subagents, the skill SHALL run planning, each apply batch, each review round, and each fix round in a fresh subagent that reads the artifacts from disk and returns only a summary block. The driving session SHALL NOT read full diffs, logs, or artifact bodies into its own context.

#### Scenario: Apply batch delegated
- **WHEN** an apply batch starts and subagents are available
- **THEN** a new subagent receives the change name, task group, and artifact paths, and the driving session reads back only its summary block

### Requirement: Works without subagents
When it cannot spawn subagents, the skill SHALL run the same phases inline in the same order, with the same gates, state file, and summary blocks, and SHALL suggest clearing or compacting context between phases with a resume command.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the skill runs plan, gate, apply batches, and review rounds itself in sequence, writes the state file after each, and prints the command to resume

### Requirement: Optional Workflow path
In Claude Code with a Workflow tool, the skill SHALL run the review rounds as a Workflow only when the user opts in with `--workflow`, and SHALL keep each Workflow under 10 agents. Without the flag or the tool, it SHALL use the subagent or inline path.

#### Scenario: --workflow in Claude Code
- **WHEN** the user passes `--workflow` and a Workflow tool is available
- **THEN** the review and verification run as one Workflow script and its confirmed findings feed the fix round

#### Scenario: --workflow without a Workflow tool
- **WHEN** the user passes `--workflow` and no Workflow tool exists
- **THEN** the skill says so and uses the subagent path, or the inline path without subagents

### Requirement: Resumable state
The skill SHALL keep run state in `.git/ep-orchestrate/<change>.json`, updated after every phase, and SHALL resume from the first unfinished phase when run again on the same change.

#### Scenario: Resume after interruption
- **WHEN** the skill is run again on a change whose state file and `git log` show tasks through 2.1 committed
- **THEN** it skips planning, the gate decision already made, and every committed task, and continues with task 2.2

#### Scenario: State disagrees with the repository
- **WHEN** the state file records a commit that is no longer on the branch, or tasks it marks done are unticked
- **THEN** the skill trusts `tasks.md` and git, says what differed, and rebuilds the state from them

### Requirement: No outward effects for regular changes
For a change below the large-change threshold, the skill SHALL NOT push, open or edit pull requests, comment, or merge. It SHALL end with a reviewed local branch and offer `ep-open-pr` and `ep-babysit-pr` as next steps.

#### Scenario: Regular run finishes
- **WHEN** the last review round ends for a change below the threshold
- **THEN** nothing has been pushed, and the report suggests `ep-open-pr` (and `ep-babysit-pr`) as the next step

### Requirement: Large-change detection
The skill SHALL classify a change as large when its plan has more than 6 task groups or 30 tracked tasks, or when the reviewed branch changes more than 800 lines or 25 files against its base, excluding `openspec/` and lockfiles. It SHALL report the classification and the numbers behind it.

#### Scenario: Large by diff size
- **WHEN** a plan with 4 groups produces a reviewed branch with 1,200 changed lines
- **THEN** the change is classified as large and the report shows the line and file counts

### Requirement: Stacked delivery for large changes
For a large change, the skill SHALL offer to deliver it as a stack: `ep-stack split` with one layer per task group (or adjacent groups merged), then `ep-babysit-pr` on the bottom PR, retargeting and babysitting each next layer after its parent merges. Nothing SHALL be pushed until the user approves the stack plan.

#### Scenario: Stack plan approved
- **WHEN** the change is large and the user approves the proposed layers
- **THEN** the skill creates the stack through `ep-stack`, babysits the bottom PR, and after it merges runs `ep-stack retarget` and babysits the next layer, until all layers merge or one stops

#### Scenario: Stack plan declined
- **WHEN** the user declines the stack plan
- **THEN** nothing is pushed and the run ends as a regular run with a reviewed local branch

#### Scenario: Layer babysitting stops
- **WHEN** `ep-babysit-pr` stops on a layer without merging it
- **THEN** the skill stops, does not touch the layers above it, records the layer in the state file, and reports the reason from the babysit summary

#### Scenario: Sibling skills missing
- **WHEN** the change is large and `ep-stack` or `ep-babysit-pr` is not installed
- **THEN** the skill does not push, reports the change as large, and recommends installing the missing skills or splitting by hand

#### Scenario: Agent without subagents
- **WHEN** the change is large and the agent has no subagents
- **THEN** the skill runs the stack and babysit steps inline, layer by layer, with the same approval and stop rules

### Requirement: Summary block
The skill SHALL end its output with an `ep-orchestrate-summary` HTML comment block with flat `key: value` lines giving the change, branch, head, outcome, gate result, task progress, dead-code result, review rounds, and remaining findings.

#### Scenario: Paused at the gate
- **WHEN** the run pauses at the confidence gate
- **THEN** the summary block has `outcome: paused_at_gate`, the score, and the hard-to-undo elements if any

#### Scenario: Completed
- **WHEN** the run finishes its review rounds with no critical or major findings
- **THEN** the summary block has `outcome: reviewed` and the last round's finding counts

#### Scenario: Stack delivered
- **WHEN** a large change was delivered as a stack
- **THEN** the summary block has `outcome: stacked_merged` or `outcome: stacked_stopped`, a `size:` line, and one `layer: <i> pr=<n> state=<state>` line per layer
