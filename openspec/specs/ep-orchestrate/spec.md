# ep-orchestrate Specification

## Purpose
Runs one OpenSpec change end to end, from a description or an existing change to a reviewed, committed local branch, while keeping the driving session's context small and resumable.

## Requirements

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
- **THEN** all of the group's tasks are ticked and committed, the group's review pass runs, and the next group starts after it

#### Scenario: Verification fails
- **WHEN** a task's verification still fails after the batch's fix attempts
- **THEN** the skill stops, leaves the task unticked and its work uncommitted, records the failure in the state file, and reports it

#### Scenario: Plan turns out wrong
- **WHEN** implementing a task shows that the specs or design are wrong or incomplete
- **THEN** the skill stops and reports the conflict instead of silently changing the specs

#### Scenario: Task needs a decision
- **WHEN** an apply phase ends with a question blocker for a task
- **THEN** the skill asks the user the question with the blocker's options plus `Stop`, and on an answer other than `Stop` re-runs the group with the answer as input, continuing from the task's uncommitted work, without stopping the run

#### Scenario: User stops at a task question
- **WHEN** the user answers `Stop` to an apply or fix question
- **THEN** the run ends with outcome `blocked`, the task stays unticked, and its work stays uncommitted in the working tree

### Requirement: Frequent, traceable commits
The skill SHALL commit in small steps following `ep-commit-and-push` conventions, with no model or tool attribution. It SHALL commit newly written planning artifacts on their own, each task on its own once verified, together with its `tasks.md` tick, and each review fix on its own. It SHALL NOT batch several tasks or a whole group into one commit.

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

### Requirement: Phase commits stay local and hold secret-like files
Every commit made through `ep-commit-and-push` SHALL use its `--no-push` mode. A phase SHALL commit a file new to history with a secret-like name only on the user's yes by name, asked through a `needs input` blocker.

#### Scenario: Commits through ep-commit-and-push stay local
- **WHEN** a phase commits through `ep-commit-and-push`
- **THEN** it passes `--no-push`, and the branch's remote is unchanged after the commit

#### Scenario: Secret-like file in a phase commit
- **WHEN** a phase's commit would add a new file with a secret-like name (as `ep-commit-and-push` lists them) and no answer says yes to it by name
- **THEN** the phase commits nothing for that commit and ends with a `needs input` blocker naming the file, through `ep-commit-and-push` and the condensed fallback alike

#### Scenario: ep-commit-and-push not installed
- **WHEN** a phase commits and `ep-commit-and-push` is not installed
- **THEN** the phase follows the condensed commit steps bundled in the skill's folder, which push nothing

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
After all tasks are done, the skill SHALL run `ep-review` on the branch and fix its verified findings, for at most 3 rounds. The first round SHALL review the whole branch; later rounds SHALL review only the commits since the previous round's head, with the earlier findings as known findings. It SHALL stop early when a round has no verified critical or major introduced findings and spec conformance passes.

#### Scenario: Clean first round
- **WHEN** the first review round reports `critical=0 major=0` and `spec_conformance: passed`
- **THEN** the skill does not run another round and reports the minor findings, if any

#### Scenario: Findings fixed
- **WHEN** a round reports verified critical or major findings
- **THEN** the skill fixes them in commits separate from the apply commits, one commit per finding, or per root cause when several findings share one, covering every listed instance of each finding's class, and runs the next round on the updated branch

#### Scenario: Later round is diff-only
- **WHEN** round 1 ran on head `A` and its fix round moved the branch to head `B`
- **THEN** round 2 reviews only `A..B` and passes round 1's findings as known findings

#### Scenario: Pre-existing findings only
- **WHEN** a round's only critical or major findings are pre-existing
- **THEN** the round counts as clean, and the pre-existing findings are listed in the final report and not fixed

#### Scenario: Round limit reached
- **WHEN** the third round still reports critical or major findings
- **THEN** the skill stops, lists the remaining findings, and does not start a fourth round

#### Scenario: Fix needs a decision
- **WHEN** a fix phase ends with a question blocker for a finding
- **THEN** the skill asks the user, and on an answer other than `Stop` re-runs the fix phase of the same round with the answer, for the findings that have no fix commit yet; the re-run does not count as a new review round

#### Scenario: Fix needs a spec change
- **WHEN** a fix phase ends with a `spec:` blocker
- **THEN** the skill stops with outcome `blocked` without asking, as before

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
In Claude Code with a Workflow tool, the skill SHALL run the review rounds as a Workflow only when the user opts in with `--workflow`, and SHALL keep each Workflow under 10 agents: four dimension agents and 3 voter agents. Without the flag or the tool, it SHALL use the subagent or inline path.

#### Scenario: --workflow in Claude Code
- **WHEN** the user passes `--workflow` and a Workflow tool is available
- **THEN** the review and a 3-voter verification run as one Workflow script of at most 7 agents, and its confirmed findings feed the fix round

#### Scenario: --workflow without a Workflow tool
- **WHEN** the user passes `--workflow` and no Workflow tool exists
- **THEN** the skill says so and uses the subagent path, or the inline path without subagents

#### Scenario: Group passes with --workflow
- **WHEN** the user passes `--workflow` and a group review pass runs
- **THEN** the pass runs on the subagent or inline path, not as a Workflow; only the end-of-run review rounds use the Workflow

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the review rounds verify each finding once inline, as `ep-review` does without subagents, and the rounds' diff-only scope and known findings still apply

### Requirement: Resumable state
The skill SHALL keep run state in `.git/ep-orchestrate/<change>.json`, updated after every phase, and SHALL resume from the first unfinished phase when run again on the same change. An unanswered phase question SHALL be recorded in the state file with the paths its blocked work changed.

#### Scenario: Resume after interruption
- **WHEN** the skill is run again on a change whose state file and `git log` show tasks through 2.1 committed
- **THEN** it skips planning, the gate decision already made, and every committed task, and continues with task 2.2

#### Scenario: State disagrees with the repository
- **WHEN** the state file records a commit that is no longer on the branch, or tasks it marks done are unticked
- **THEN** the skill trusts `tasks.md` and git, says what differed, and rebuilds the state from them

#### Scenario: Resume with an open question
- **WHEN** the skill is run again on a change whose state file records an unanswered apply or fix question
- **THEN** the clean-tree check accepts uncommitted changes in exactly the recorded paths, and the skill asks the same question again before running any phase

#### Scenario: Leftovers outside the recorded paths
- **WHEN** a resume with an open question finds uncommitted changes outside the recorded paths and the change folder
- **THEN** the skill stops with outcome `dirty_tree` and lists those paths

#### Scenario: Resume at a fix question
- **WHEN** the skill is run again on a change whose state file records an unanswered fix question
- **THEN** it takes that round's findings and fix commits from `.git/ep-orchestrate/<change>.findings`, which keeps finding text out of the state file, and re-runs the fix phase of the same round with the recorded finding ids instead of starting a new review; when that file is missing, it stops with outcome `blocked` and says the round's findings are lost

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
The skill SHALL end its output with an `ep-orchestrate-summary` HTML comment block with flat `key: value` lines giving the change, branch, head, outcome, gate result, task progress, dead-code result, group review passes, review rounds, and remaining findings.

#### Scenario: Paused at the gate
- **WHEN** the run pauses at the confidence gate
- **THEN** the summary block has `outcome: paused_at_gate`, the score, and the hard-to-undo elements if any

#### Scenario: Completed
- **WHEN** the run finishes its review rounds with no critical or major findings
- **THEN** the summary block has `outcome: reviewed` and the last round's finding counts

#### Scenario: Stack delivered
- **WHEN** a large change was delivered as a stack
- **THEN** the summary block has `outcome: stacked_merged` or `outcome: stacked_stopped`, a `size:` line, and one `layer: <i> pr=<n> state=<state>` line per layer

#### Scenario: Group passes reported
- **WHEN** the run reviewed its groups
- **THEN** the summary block has a `group_reviews: passes=<n> fixed=<n> unfixed=<n>` line counting the passes run, the findings their fix phases fixed, and their findings left unfixed

### Requirement: Structured user questions
When the driving session asks the user a question with fixed options, the skill SHALL use the host's structured question tool (`AskUserQuestion` in Claude Code) when one is available. Without such a tool, it SHALL ask in plain text with the same options numbered and wait for the reply; an open question with no options is asked in plain text. The skill SHALL act only on an answer that maps to one option or gives the requested input, and ask again otherwise.

#### Scenario: Gate pause with a question tool
- **WHEN** the gate pauses (score below 85 without `--yes`, or a hard-to-undo element) and the host offers a structured question tool
- **THEN** the skill prints the score report, then asks through the tool with the options approve, revise, and stop, and makes no code change before the answer

#### Scenario: Gate pause without a question tool
- **WHEN** the gate pauses and the host has no structured question tool
- **THEN** the skill asks in plain text with the options approve, revise, and stop numbered, and waits for the reply

#### Scenario: Name collides with an existing change
- **WHEN** the derived name matches an existing change and the host offers a structured question tool
- **THEN** the skill asks through the tool with the options to continue that change or use a different name

#### Scenario: Work branch already exists
- **WHEN** the skill would create `<type>/<change>` and that branch already exists
- **THEN** it asks, through the tool when available, whether to continue on the existing branch or stop, and creates no branch before the answer

#### Scenario: Plan needs input
- **WHEN** the plan phase ends with `blocker: needs input`
- **THEN** the skill asks the planner's question, through the tool when available and the blocker names 2 to 4 options, otherwise in plain text, and re-runs the plan phase with the answer

#### Scenario: Large change offered as a stack
- **WHEN** the change is large and `ep-stack` and `ep-babysit-pr` are available
- **THEN** the skill asks, through the tool when available, whether to deliver it as a stack or keep the reviewed local branch, and pushes nothing before the answer

#### Scenario: Answer outside the options
- **WHEN** the user answers with free text that matches none of the options
- **THEN** the skill does not guess: it acts on the text only when it clearly picks one option or gives the requested input (such as a new change name), and otherwise asks again

### Requirement: Questions only from the driving session
Only the driving session SHALL ask the user questions. Phase workers SHALL NOT call the question tool or wait for the user; a phase that needs an answer SHALL end with a question blocker (`blocker: needs input: <id>: <question>`, optionally followed by 2 or 3 options), and the driving session SHALL ask it and pass the answer into a re-run of that phase. Questions that another skill asks under its own rules (such as `ep-stack`'s plan approval) SHALL stay with that skill.

#### Scenario: Phase subagent needs an answer
- **WHEN** a plan, apply, or fix phase running in a subagent finds a choice it cannot make
- **THEN** it ends with a question blocker naming the question, the driving session asks the user, and the phase re-runs with the answer

#### Scenario: Agent without subagents
- **WHEN** the host has no subagents and the skill runs the phases inline
- **THEN** a choice the phase cannot make still ends that phase with a question blocker, the question is asked at the driving session's question point, through the question tool when available, and never mid-phase, and the phase then re-runs inline with the answer

#### Scenario: Interrupted at a gate question
- **WHEN** the session ends while the gate question is unanswered
- **THEN** the state file already records `decision: paused`, and the next run asks the same question again

### Requirement: Blockers that stop without a question
Blockers that are not questions (failed verification, plan conflicts, findings that need a spec change) SHALL stop the run without a question. A task or finding SHALL come back with a question at most twice; a third question SHALL stop the run with outcome `blocked` instead of being asked.

#### Scenario: Third question for the same task
- **WHEN** a task or finding comes back with a question after two answered questions
- **THEN** the skill does not ask again: it stops with outcome `blocked` and reports the question and the earlier answers

### Requirement: Review pass after each apply group
After an apply group finishes with every task done, the skill SHALL run exactly one review pass on that group's commits, from the group's start sha to its head, before the next group starts. It SHALL do this for every group, the last included, and SHALL NOT run a second pass for the same group. The end-of-run review rounds SHALL still run after the dead-code check.

#### Scenario: Group finishes
- **WHEN** group 2 finishes with all its tasks done and committed
- **THEN** the skill runs one review pass on the commits from group 2's start sha to its head, and group 3 starts only after that pass, and its fix phase when one runs, are done

#### Scenario: Last group finishes
- **WHEN** the last group finishes with all its tasks done
- **THEN** the skill runs that group's review pass, then the dead-code check, then the end-of-run review rounds, up to 3, as before

#### Scenario: No second pass for a group
- **WHEN** a group's fix phase has committed fixes for that group's pass
- **THEN** the skill does not review that group again and starts the next group

#### Scenario: Group stopped before finishing
- **WHEN** an apply group stops with a blocker or a question and its tasks are not all done
- **THEN** no review pass runs for it until the group finishes, including after a re-run with an answer

#### Scenario: Agent without subagents
- **WHEN** the host has no subagents
- **THEN** the skill runs each group's review pass and fix phase inline after the group, writes the state file after each, and prints the command to resume

### Requirement: Group review scope
A group review pass SHALL cover only the group's commits. It SHALL use `ep-review` when that skill is available and the group's start sha equals the commit `ep-review <branch>` diffs against, and SHALL otherwise use the review fallback with the group's start sha and head. It SHALL post nothing to GitHub.

#### Scenario: Range matches ep-review's base
- **WHEN** `ep-review` is available and the group's start sha equals the merge base of the branch with the default branch
- **THEN** the pass runs `ep-review <branch>` with the change name and posts nothing

#### Scenario: Range differs from ep-review's base
- **WHEN** the group's start sha is not that merge base, for example for any group after the first
- **THEN** the pass follows the review fallback on the diff from the group's start sha to its head

#### Scenario: Group with no diff
- **WHEN** the group's commits change no file apart from task ticks
- **THEN** the review of the range reports nothing to review and the pass counts as clean

### Requirement: Spec conformance for a partial change
In a group review pass, behavior that a requirement needs and that a task of a later group, not done yet, is to implement SHALL NOT be a finding. Spec conformance SHALL be judged on the tasks done so far, and contradictions of a scenario by the group's own code SHALL still be findings.

#### Scenario: Requirement owned by a later group
- **WHEN** a group pass finds a requirement not implemented and the task that implements it belongs to a later group and is still unticked
- **THEN** the pass drops that finding, and spec conformance does not fail because of it

#### Scenario: Ticked task not really done
- **WHEN** a group pass finds a ticked task of that group whose behavior is missing
- **THEN** the pass reports it as a spec finding, as in the end-of-run rounds

### Requirement: Fixes after a group review pass
When a group pass has a verified critical or major finding, or its spec conformance failed, the skill SHALL run one fix phase for that pass before the next group starts. A pass with only minor findings SHALL run no fix phase. Minor and deferred findings of group passes SHALL be listed in the final report. Fix questions and blockers SHALL follow the same rules as in the end-of-run rounds.

#### Scenario: Major finding in a group pass
- **WHEN** group 1's pass reports a verified major finding
- **THEN** one fix phase commits its fix, one commit per finding or shared root cause, and group 2 starts after it without another review of group 1

#### Scenario: Only minor findings
- **WHEN** a group pass reports only minor findings and spec conformance passed
- **THEN** no fix phase runs, the next group starts, and the minor findings appear in the final report

#### Scenario: Group fix needs a decision
- **WHEN** a group pass's fix phase ends with a question blocker for a finding
- **THEN** the skill asks the user at the phase question point, and on an answer other than `Stop` re-runs that pass's fix phase for the findings with no fix commit yet; the re-run is not a new pass

#### Scenario: Group fix needs a spec change
- **WHEN** a group pass's fix phase ends with a `spec:` blocker
- **THEN** the skill stops with outcome `blocked` without asking

### Requirement: Resumable group review passes
The state file SHALL record each group's start sha and the result of its review pass and fix phase. On resume, the skill SHALL run a group's missing pass, or its unfinished fix phase, before starting the next group, and SHALL NOT run passes for groups whose next group already has commits.

#### Scenario: Interrupted before the pass
- **WHEN** the skill is run again after group 2's tasks were all committed but before its review pass was recorded
- **THEN** it runs group 2's pass before starting group 3

#### Scenario: Resume at a group fix question
- **WHEN** the skill is run again with an unanswered fix question from a group pass
- **THEN** it asks the question again and re-runs that pass's fix phase with the findings and fix commits from `.git/ep-orchestrate/<change>.findings`, without a new pass

#### Scenario: State file from before group passes
- **WHEN** the skill resumes a run whose state file has no group pass records and groups 1 and 2 are done with group 3 not started
- **THEN** it runs a pass for group 2 only, and none for group 1, whose next group already has commits
