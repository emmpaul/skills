## MODIFIED Requirements

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

#### Scenario: Task needs a decision
- **WHEN** an apply phase ends with a question blocker for a task
- **THEN** the skill asks the user the question with the blocker's options plus `Stop`, and on an answer other than `Stop` re-runs the group with the answer as input, continuing from the task's uncommitted work, without stopping the run

#### Scenario: User stops at a task question
- **WHEN** the user answers `Stop` to an apply or fix question
- **THEN** the run ends with outcome `blocked`, the task stays unticked, and its work stays uncommitted in the working tree

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

#### Scenario: Fix needs a decision
- **WHEN** a fix phase ends with a question blocker for a finding
- **THEN** the skill asks the user, and on an answer other than `Stop` re-runs the fix phase of the same round with the answer, for the findings that have no fix commit yet; the re-run does not count as a new review round

#### Scenario: Fix needs a spec change
- **WHEN** a fix phase ends with a `spec:` blocker
- **THEN** the skill stops with outcome `blocked` without asking, as before

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

### Requirement: Questions only from the driving session
Only the driving session SHALL ask the user questions. Phase workers SHALL NOT call the question tool or wait for the user; a phase that needs an answer SHALL end with a question blocker (`blocker: needs input: <id>: <question>`, optionally followed by 2 or 3 options), and the driving session SHALL ask it and pass the answer into a re-run of that phase. Blockers that are not questions (failed verification, plan conflicts, findings that need a spec change) SHALL stop the run without a question. A task or finding SHALL come back with a question at most twice; a third question stops the run with outcome `blocked`. Questions that another skill asks under its own rules (such as `ep-stack`'s plan approval) SHALL stay with that skill.

#### Scenario: Phase subagent needs an answer
- **WHEN** a plan, apply, or fix phase running in a subagent finds a choice it cannot make
- **THEN** it ends with a question blocker naming the question, the driving session asks the user, and the phase re-runs with the answer

#### Scenario: Agent without subagents
- **WHEN** the host has no subagents and the skill runs the phases inline
- **THEN** a choice the phase cannot make still ends that phase with a question blocker, the question is asked at the driving session's question point, through the question tool when available, and never mid-phase, and the phase then re-runs inline with the answer

#### Scenario: Interrupted at a gate question
- **WHEN** the session ends while the gate question is unanswered
- **THEN** the state file already records `decision: paused`, and the next run asks the same question again

#### Scenario: Third question for the same task
- **WHEN** a task or finding comes back with a question after two answered questions
- **THEN** the skill does not ask again: it stops with outcome `blocked` and reports the question and the earlier answers
