# Spec Delta

## Purpose

Reverts a merged GitHub pull request safely: builds the revert on a new branch, opens a revert PR that explains the reason and impact, and flags OpenSpec specs that would overstate the code once the revert lands.

## ADDED Requirements

### Requirement: Target is a merged PR
The skill SHALL accept a PR number, SHALL confirm with GitHub that the PR is merged, and SHALL stop for PRs that are open or closed without merging.

#### Scenario: PR not merged
- **WHEN** the given PR is open or closed without merging
- **THEN** the skill reports its state and stops without creating a branch

#### Scenario: Already reverted
- **WHEN** the default branch already contains a revert of the PR's merge commit
- **THEN** the skill reports the existing revert and stops

### Requirement: Revert on a new branch
The skill SHALL create a `revert/pr-<n>` branch from the up-to-date default branch and revert the PR's changes there with revert commits, for merge commits, squash merges, and rebase merges alike.

#### Scenario: Merge commit
- **WHEN** the PR was merged with a merge commit
- **THEN** the skill reverts that merge commit against its first parent

#### Scenario: Squash merge
- **WHEN** the PR was squash-merged
- **THEN** the skill reverts the single squash commit

#### Scenario: Rebase merge
- **WHEN** the PR was rebase-merged into several commits
- **THEN** the skill reverts each of those commits in reverse order on the revert branch

#### Scenario: Revert conflicts
- **WHEN** later commits on the default branch make the revert conflict
- **THEN** the skill stops before committing, lists the conflicting files and the later commits that touched them, and asks the user how to proceed

### Requirement: Reason required
The skill SHALL ask for the reason for the revert when the user does not give one, and SHALL NOT open the revert PR without a reason.

#### Scenario: No reason given
- **WHEN** the user runs the skill without a reason
- **THEN** the skill asks for one before pushing

### Requirement: Revert PR with reason and impact
The skill SHALL push the revert branch and open a PR that names the reverted PR, states the reason, lists the behavior removed, and classifies the revert as a one-way or two-way door, only after the user confirms.

#### Scenario: PR opened
- **WHEN** the user confirms the revert
- **THEN** the skill pushes `revert/pr-<n>`, opens a PR titled `revert: <original title>` whose body links the original PR, the reason, and the impact, without model attribution

#### Scenario: One-way door in the original
- **WHEN** the original PR included effects a revert cannot undo, such as a data migration or a published release
- **THEN** the revert PR body lists those effects as not undone by this revert

#### Scenario: Confirmation declined
- **WHEN** the user declines
- **THEN** the revert branch stays local and nothing is pushed

### Requirement: Spec drift flagged
With OpenSpec, the skill SHALL list the main spec requirements added or modified by the change the reverted PR implemented, state in the revert PR that they will overstate behavior once the revert merges, and suggest a follow-up change, without editing any spec.

#### Scenario: Reverted PR implemented an archived change
- **WHEN** the reverted PR's OpenSpec change was archived into main specs
- **THEN** the revert PR body names the affected capabilities and requirements and suggests a follow-up OpenSpec change to update them

#### Scenario: Change still active
- **WHEN** the reverted PR's OpenSpec change is not archived
- **THEN** the revert PR body notes that the change's tasks no longer reflect the code

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill skips spec drift and does not mention OpenSpec

### Requirement: Never pushes to the default branch
The skill SHALL NOT push to the default branch, force-push, or merge the revert PR itself.

#### Scenario: Urgent revert
- **WHEN** the user asks for the revert to land quickly
- **THEN** the skill still opens a PR and may suggest running `ep-babysit-pr` on it

### Requirement: Machine-readable result
The skill SHALL end with an `ep-revert-summary` block reporting the reverted PR, outcome, revert branch, revert PR URL, and the number of flagged spec requirements.

#### Scenario: Summary after opening
- **WHEN** the revert PR is opened
- **THEN** the summary includes its URL and the flagged requirement count

### Requirement: Works without subagents
The skill SHALL complete its full behavior sequentially in agents that cannot spawn subagents.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the revert and spec-drift check run inline with the same output
