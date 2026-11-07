# Spec Delta

## MODIFIED Requirements

### Requirement: Review rounds
After all tasks are done, the skill SHALL run `ep-review` on the branch and fix its verified findings, for at most 3 rounds. The first round SHALL review the whole branch; later rounds SHALL review only the commits since the previous round's head, with the earlier findings as known findings. It SHALL stop early when a round has no verified critical or major introduced findings and spec conformance passes. Fixes SHALL be committed separately from the apply commits, one commit per finding or shared root cause.

#### Scenario: Clean first round
- **WHEN** the first review round reports `critical=0 major=0` and `spec_conformance: passed`
- **THEN** the skill does not run another round and reports the minor findings, if any

#### Scenario: Findings fixed
- **WHEN** a round reports verified critical or major findings
- **THEN** the skill fixes them with one commit per finding, or per root cause when several findings share one, covering every listed instance of each finding's class, and runs the next round on the updated branch

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
