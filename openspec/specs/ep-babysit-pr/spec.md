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
When a check fails, the skill SHALL diagnose it from the check logs, apply a fix, commit via `ep-commit-and-push` conventions, and push to the PR branch. It SHALL delegate diagnosis and fixing to `ep-ci-debug` when that skill is installed, and otherwise SHALL perform the equivalent steps inline.

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
- **THEN** the fix is a normal commit following `ep-commit-and-push` conventions, so no `fixup!` subject reaches the base branch

#### Scenario: Never autosquash
- **WHEN** the skill creates fixup commits
- **THEN** it never autosquashes, rebases, or force-pushes them

#### Scenario: ep-fixup not installed
- **WHEN** a fixup commit is needed and `ep-fixup` is not installed
- **THEN** the skill follows the condensed fixup steps bundled in its own folder

### Requirement: Bounded review rounds
The skill SHALL run at most 3 review rounds, where a round is an `ep-review` pass on the PR, fixes for its findings, a push, and green required checks. The first round SHALL review the full PR; later rounds SHALL review only the commits since the last reviewed head and pass the earlier findings as known findings, unless a base sync landed since that head.

#### Scenario: Round limit reached
- **WHEN** 3 rounds complete and the merge gate is not met
- **THEN** the skill stops, posts a summary comment on the PR that asks the author to step back and reconsider the approach, and notifies the user

#### Scenario: Second round is diff-only
- **WHEN** round 1 ran on head `A`, fixes were pushed to head `B`, and no base sync happened in between
- **THEN** round 2 runs `ep-review <n> --since A --known <round 1 findings>`

#### Scenario: Sync between rounds
- **WHEN** a base sync was pushed after the last reviewed head
- **THEN** the next round reviews the full PR, with the earlier findings still passed as known findings

#### Scenario: Pre-existing findings
- **WHEN** a review round reports pre-existing findings
- **THEN** the skill does not fix them, lists them in its status report and final report, and they do not affect the score

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
The skill SHALL merge only when the score is at least 85, hard gates pass, the risk gate passes, and GitHub reports the PR as mergeable without bypass; it SHALL wait while GitHub reports the PR as blocked and SHALL stop when the merge state is unknown after retries.

#### Scenario: Protection requires approval
- **WHEN** score is 90 and GitHub reports the PR blocked pending approval
- **THEN** the skill waits, notifies the user, and merges once GitHub reports it mergeable

#### Scenario: No protection
- **WHEN** score is 88, hard gates pass, the risk gate passes, GitHub reports the PR mergeable, and the PR is in no native stack
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

### Requirement: Merging a PR in a native stack
For a PR in a GitHub native stack, the skill SHALL merge only when the PR is the lowest open PR of its stack. It SHALL merge through GitHub's async merge API, pinned to the reviewed head sha, with the repository's merge method and no bypass. It SHALL treat the merge as done only when GitHub reports `merged`, and SHALL NOT delete the head branch.

#### Scenario: Bottom layer merges
- **WHEN** the PR is the lowest open PR of a native stack, gates pass, and the score is at least 85
- **THEN** the skill requests an async merge pinned to the reviewed head, waits until the result is `merged`, and leaves the head branch in place

#### Scenario: Mid-stack PR
- **WHEN** the PR is in a native stack and an open PR sits below it
- **THEN** the skill does not merge, because the merge would also merge the PRs below, and it reports the lower PRs that must merge first

#### Scenario: Merge enqueued
- **WHEN** the async merge result is `enqueued`, or the merge request answers that the PR is already queued
- **THEN** the skill does not request the merge again and checks the PR on each tick, waiting as it waits on a blocked PR while the PR stays in the merge queue

#### Scenario: Ejected from the merge queue
- **WHEN** a PR the skill saw enqueued is open and no longer in the merge queue
- **THEN** the skill reports it and stops without requesting the merge again

#### Scenario: Merge request rejected
- **WHEN** GitHub answers the async merge request with an error
- **THEN** the skill reports the status and message and stops without retrying, with or without a bypass

#### Scenario: Stack detection unavailable
- **WHEN** reading the PR's stack fails and the repository's stacks endpoint answers 404, or 400 rejecting the API version
- **THEN** the skill treats the PR as not stacked and merges as it did before this change

#### Scenario: Stack detection failed
- **WHEN** reading the PR's stack fails and the stacks endpoint answers anything else (success, another error status, or no answer)
- **THEN** the skill does not merge, reports both answers, and stops

#### Scenario: Merge result expired
- **WHEN** reading the async merge result answers 404 because the result expired
- **THEN** the skill does not request the merge again and checks the PR on each tick, as for an enqueued merge

#### Scenario: Merge failed
- **WHEN** the async merge result is `failed`
- **THEN** the skill reports the details without retrying with any bypass

#### Scenario: Not stacked
- **WHEN** the PR belongs to no native stack
- **THEN** the skill merges as it did before this change

### Requirement: Risk-tier merge gate
The skill SHALL read the risk tier from the latest `ep-review` summary for the merge head. Low risk SHALL need no extra approval. Medium risk SHALL need the user's explicit yes in the session for that exact head sha. High risk SHALL need that yes and an approving GitHub review of that head from a human other than the PR author.

#### Scenario: Low risk
- **WHEN** the latest review reports `risk: low` and every other merge condition holds
- **THEN** the skill merges without asking

#### Scenario: Medium risk asks
- **WHEN** the latest review reports `risk: medium` and every other merge condition holds
- **THEN** the skill shows the risk reasons, score, and head sha, and merges only after the user says yes for that head

#### Scenario: New commits after a yes
- **WHEN** the user said yes for head `A` and a fix is pushed, making the head `B`
- **THEN** the earlier yes no longer counts and the skill asks again for `B`

#### Scenario: High risk without a human approval
- **WHEN** the latest review reports `risk: high` and no human other than the PR author has approved the current head
- **THEN** the skill does not merge, notifies the user once that a human approval is needed, and waits

#### Scenario: Bot approval
- **WHEN** the only approving review on a high-risk PR comes from an account of type Bot or an app
- **THEN** the approval is not counted and the skill keeps waiting

#### Scenario: Unattended run on medium risk
- **WHEN** the skill runs from a schedule or loop with no user present and the PR is medium risk
- **THEN** it does not merge, notifies the user once, and asks on the next run where the user is present

#### Scenario: Review summary without a tier
- **WHEN** the latest review summary has no `risk:` line (an older `ep-review`)
- **THEN** the skill treats the PR as medium risk
