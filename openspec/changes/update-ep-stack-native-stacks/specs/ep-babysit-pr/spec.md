## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Merge decision defers to GitHub
The skill SHALL merge only when the score is at least 85, hard gates pass, and GitHub reports the PR as mergeable without bypass; it SHALL wait while GitHub reports the PR as blocked and SHALL stop when the merge state is unknown after retries.

#### Scenario: Protection requires approval
- **WHEN** score is 90 and GitHub reports the PR blocked pending approval
- **THEN** the skill waits, notifies the user, and merges once GitHub reports it mergeable

#### Scenario: No protection
- **WHEN** score is 88, hard gates pass, GitHub reports the PR mergeable, and the PR is in no native stack
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
