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
When a check fails, the skill SHALL diagnose it from the check logs, apply a fix, commit via `ep-commit` conventions, and push to the PR branch. It SHALL delegate diagnosis and fixing to `ep-ci-debug` when that skill is installed, and otherwise SHALL perform the equivalent steps inline.

#### Scenario: Failing test
- **WHEN** a required check fails with a test failure
- **THEN** the skill fixes the cause, commits without attribution, and pushes

#### Scenario: Repeated failure
- **WHEN** the same check fails after 3 fix attempts
- **THEN** the skill stops and reports the failure and attempts to the user

#### Scenario: Delegated to ep-ci-debug
- **WHEN** a check fails and `ep-ci-debug` is installed
- **THEN** the skill invokes it for that check, reads its `ep-ci-debug-summary` block, and counts a fix attempt for each check reported as fixed

#### Scenario: ep-ci-debug not installed
- **WHEN** a check fails and `ep-ci-debug` is not installed
- **THEN** the skill follows the condensed CI-debug steps bundled in its own folder, with the same classification, re-run-once, and never-weaken-tests rules

#### Scenario: Non-code cause
- **WHEN** the failure is classified as flaky-infra, config, or secret and a single re-run does not fix it
- **THEN** the skill reports it to the user and makes no code change

### Requirement: Address review comments
The skill SHALL classify each new reviewer comment as fix, reply, or scope change; fix and push for fix, post a reply without model attribution for reply, and flag scope changes to the user without implementing them. When the repository's merge method is squash, fixes SHALL be committed as `fixup!` commits through `ep-fixup` in no-rewrite mode; otherwise as normal commits.

#### Scenario: Requested code fix
- **WHEN** a reviewer asks for a code change within the PR's scope
- **THEN** the skill implements it, pushes, and replies describing the fix

#### Scenario: Scope change against OpenSpec
- **WHEN** a comment asks for behavior that contradicts or extends the active OpenSpec change's specs
- **THEN** the skill does not implement it and tells the user the OpenSpec change needs updating

#### Scenario: Threads not resolved by skill
- **WHEN** the skill has replied to a review thread
- **THEN** the thread is left for the reviewer to resolve

#### Scenario: Fix in a squash-merge repository
- **WHEN** a fix-class comment is handled and the repository merges PRs by squash
- **THEN** the fix is a `fixup!` commit targeting the commit it corrects, pushed with a plain push, and the reply names the fixup and target shas

#### Scenario: Fix in a merge-commit or rebase repository
- **WHEN** a fix-class comment is handled and the repository's merge method is merge or rebase
- **THEN** the fix is a normal commit following `ep-commit` conventions, so no `fixup!` subject reaches the base branch

#### Scenario: Never autosquash
- **WHEN** the skill creates fixup commits
- **THEN** it never autosquashes, rebases, or force-pushes them

#### Scenario: ep-fixup not installed
- **WHEN** a fixup commit is needed and `ep-fixup` is not installed
- **THEN** the skill follows the condensed fixup steps bundled in its own folder

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

#### Scenario: Documentation-only PR
- **WHEN** every file the PR changes is a documentation or planning file by path (such as `*.md` outside agent instruction files, `docs/**`, or `openspec/**`)
- **THEN** the test evidence item counts as met and the breakdown marks it "not applicable: no code changed"

#### Scenario: Agent instruction files changed
- **WHEN** the PR changes a file in a skill folder (a directory containing `SKILL.md`), an `AGENTS.md` or `CLAUDE.md`, or a file under `.claude/`
- **THEN** the PR is not documentation-only and test evidence is required as usual

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
- **WHEN** GitHub reports the branch behind its base, or in conflict with it
- **THEN** the skill syncs the branch with its base through `ep-sync` in merge mode (or its condensed inline steps when `ep-sync` is not installed), runs the merge audit, pushes with a plain push, waits for checks, and re-evaluates

#### Scenario: Audit finds needed updates
- **WHEN** the sync's merge audit reports needs-update interactions
- **THEN** the skill applies the adaptations as a fix round, in commits separate from the merge commit, before re-evaluating the merge

#### Scenario: Audit needs a decision
- **WHEN** the sync stops on an incompatible conflict or an ambiguous adaptation
- **THEN** the skill does not push the sync, notifies the user with the options, and stops until the user decides

#### Scenario: Review items from the audit
- **WHEN** the merge audit reports review-class interactions
- **THEN** the skill lists them in its next status report and the next review round covers them

### Requirement: Forbidden actions
The skill SHALL NOT force-push, use admin or any other branch-protection bypass, resolve review threads itself, or add model attribution to commits, replies, or comments.

#### Scenario: Merge blocked by protection
- **WHEN** merging would require bypassing branch protection
- **THEN** the skill does not merge

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents or schedule loops, including when `ep-ci-debug`, `ep-fixup`, and `ep-sync` are not installed.

#### Scenario: Agent without subagents or loop scheduling
- **WHEN** the host agent can neither spawn subagents nor schedule recurring wakeups
- **THEN** the skill diagnoses failures inline and polls within the session until a stop condition

#### Scenario: Side-path skills missing
- **WHEN** none of `ep-ci-debug`, `ep-fixup`, and `ep-sync` is installed
- **THEN** the skill completes CI fixes, review fixes, and base syncs using the condensed steps bundled in its own folder

### Requirement: No history rewrite through sibling skills
When the skill invokes `ep-sync`, `ep-fixup`, or `ep-ci-debug`, it SHALL use their no-rewrite modes and SHALL NOT force-push or rebase a pushed branch through them.

#### Scenario: Sibling skill offers rewrite
- **WHEN** a sibling skill would need a rebase or force-push to finish
- **THEN** the skill does not proceed with the rewrite, and reports to the user
