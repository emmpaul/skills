# ep-babysit-pr Specification

## Purpose

Shepherds a GitHub pull request to merge autonomously: fixes CI failures, addresses review comments, runs bounded self-review rounds, and merges only when evidence-based gates pass and GitHub's merge rules allow it.

## Requirements

### Requirement: Target PR resolution
The skill SHALL babysit the PR given by number, or the open PR for the current branch when none is given.

#### Scenario: No PR found
- **WHEN** no PR number is given and the current branch has no open PR
- **THEN** the skill stops and offers to run `ep-open-pr`

### Requirement: Watch loop
The skill SHALL repeatedly observe the PR's checks, reviews, comments, and merge state, and act on changes until the PR is merged or a stop condition is reached.

#### Scenario: Waiting on CI
- **WHEN** checks are still running
- **THEN** the skill waits and re-observes without taking action

### Requirement: Fix CI failures
When a check fails, the skill SHALL diagnose it from the check logs, apply a fix, commit via `ep-commit` conventions, and push to the PR branch.

#### Scenario: Failing test
- **WHEN** a required check fails with a test failure
- **THEN** the skill fixes the cause, commits without attribution, and pushes

#### Scenario: Repeated failure
- **WHEN** the same check fails after 3 fix attempts
- **THEN** the skill stops and reports the failure and attempts to the user

### Requirement: Address review comments
The skill SHALL classify each new reviewer comment as fix, reply, or scope change; fix and push for fix, post a reply without model attribution for reply, and flag scope changes to the user without implementing them.

#### Scenario: Requested code fix
- **WHEN** a reviewer asks for a code change within the PR's scope
- **THEN** the skill implements it, pushes, and replies describing the fix

#### Scenario: Scope change against OpenSpec
- **WHEN** a comment asks for behavior that contradicts or extends the active OpenSpec change's specs
- **THEN** the skill does not implement it and tells the user the OpenSpec change needs updating

#### Scenario: Threads not resolved by skill
- **WHEN** the skill has replied to a review thread
- **THEN** the thread is left for the reviewer to resolve

### Requirement: Bounded review rounds
The skill SHALL run at most 3 review rounds, where a round is an `ep-review` pass on the PR, fixes for its findings, a push, and green required checks.

#### Scenario: Round limit reached
- **WHEN** 3 rounds complete and the merge gate is not met
- **THEN** the skill stops, posts a summary comment on the PR, and notifies the user

### Requirement: Evidence-based confidence score
After each round the skill SHALL compute a confidence score from 0 to 100 from verifiable evidence, report its breakdown, and SHALL NOT use self-assessed confidence.

#### Scenario: Score breakdown shown
- **WHEN** the skill computes the score
- **THEN** it reports each evidence item, its weight, and whether it was met

#### Scenario: No OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** OpenSpec-dependent items are dropped and their weight is redistributed to test evidence

### Requirement: Hard merge gates
The skill SHALL NOT merge unless all required checks pass, the branch has no conflicts, no review threads are unresolved, and no review requests changes, regardless of score.

#### Scenario: Changes requested
- **WHEN** a reviewer's latest review requests changes
- **THEN** the skill does not merge even if the score is 100

### Requirement: Merge decision defers to GitHub
The skill SHALL merge only when the score is at least 85, hard gates pass, and GitHub reports the PR as mergeable without bypass; it SHALL wait while GitHub reports the PR as blocked and SHALL stop when the merge state is unknown after retries.

#### Scenario: Protection requires approval
- **WHEN** score is 90 and GitHub reports the PR blocked pending approval
- **THEN** the skill waits, notifies the user, and merges once GitHub reports it mergeable

#### Scenario: No protection
- **WHEN** score is 88, hard gates pass, and GitHub reports the PR mergeable
- **THEN** the skill merges using the repository's default merge method and deletes the branch

#### Scenario: Unknown merge state
- **WHEN** GitHub reports the merge state as unknown after several retries
- **THEN** the skill stops without merging and reports to the user

#### Scenario: Branch behind base
- **WHEN** GitHub reports the branch behind its base
- **THEN** the skill updates the branch, waits for checks, and re-evaluates

### Requirement: Forbidden actions
The skill SHALL NOT force-push, use admin or any other branch-protection bypass, resolve review threads itself, or add model attribution to commits, replies, or comments.

#### Scenario: Merge blocked by protection
- **WHEN** merging would require bypassing branch protection
- **THEN** the skill does not merge

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents or schedule loops.

#### Scenario: Agent without subagents or loop scheduling
- **WHEN** the host agent can neither spawn subagents nor schedule recurring wakeups
- **THEN** the skill diagnoses failures inline and polls within the session until a stop condition
