## ADDED Requirements

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

## MODIFIED Requirements

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

### Requirement: Optional Workflow path
In Claude Code with a Workflow tool, the skill SHALL run the review rounds as a Workflow only when the user opts in with `--workflow`, and SHALL keep each Workflow under 10 agents. Without the flag or the tool, it SHALL use the subagent or inline path.

#### Scenario: --workflow in Claude Code
- **WHEN** the user passes `--workflow` and a Workflow tool is available
- **THEN** the review and verification run as one Workflow script and its confirmed findings feed the fix round

#### Scenario: --workflow without a Workflow tool
- **WHEN** the user passes `--workflow` and no Workflow tool exists
- **THEN** the skill says so and uses the subagent path, or the inline path without subagents

#### Scenario: Group passes with --workflow
- **WHEN** the user passes `--workflow` and a group review pass runs
- **THEN** the pass runs on the subagent or inline path, not as a Workflow; only the end-of-run review rounds use the Workflow

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
