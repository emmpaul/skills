# Spec Delta

## Purpose

Cleans up after a merged GitHub pull request: brings the local clone back to an up-to-date default branch, removes the merged branch, and closes the loop on its OpenSpec change and linked issues.

## ADDED Requirements

### Requirement: Target PR resolution
The skill SHALL land the PR given by number, or the PR whose head is the current branch when none is given, and SHALL confirm with GitHub that the PR is merged before changing anything.

#### Scenario: PR not merged
- **WHEN** the target PR is open or was closed without merging
- **THEN** the skill reports its state and stops without changing the local clone, branches, or GitHub

#### Scenario: No PR found
- **WHEN** no PR number is given and no PR exists for the current branch
- **THEN** the skill stops and asks the user for a PR number

#### Scenario: Already on the default branch
- **WHEN** the current branch is the default branch and a PR number is given
- **THEN** the skill lands that PR without requiring its branch to be checked out

### Requirement: Default branch updated
The skill SHALL switch to the default branch and fast-forward it to its remote, and SHALL NOT create a merge commit, rebase, or reset it.

#### Scenario: Fast-forward
- **WHEN** the local default branch is behind its remote
- **THEN** the skill fast-forwards it and reports the new head

#### Scenario: Diverged default branch
- **WHEN** the local default branch has commits that are not on its remote
- **THEN** the skill does not update it, reports the extra commits, and continues with branch cleanup

#### Scenario: Dirty working tree
- **WHEN** the working tree has uncommitted changes when the skill starts
- **THEN** the skill stops before switching branches and asks the user to commit or stash them

### Requirement: Merged branch deleted safely
The skill SHALL delete the local head branch only when its tip is the PR's merged head commit or is contained in the default branch, and otherwise SHALL keep it and report why.

#### Scenario: Squash-merged branch
- **WHEN** the PR was squash-merged and the local branch tip equals the PR's head commit on GitHub
- **THEN** the skill deletes the local branch even though its commits are not ancestors of the default branch

#### Scenario: Local commits after merge
- **WHEN** the local branch has commits that are not in the merged PR
- **THEN** the skill keeps the branch, lists those commits, and tells the user

#### Scenario: Remote branch already deleted
- **WHEN** the remote head branch no longer exists
- **THEN** the skill skips remote deletion without error and prunes stale remote-tracking refs

#### Scenario: Remote branch still present
- **WHEN** the remote head branch still exists, belongs to the same repository, and its tip is the PR's head commit
- **THEN** the skill deletes it and reports the deletion

#### Scenario: Fork head branch
- **WHEN** the PR's head branch is in a fork
- **THEN** the skill does not delete the remote branch and only cleans up local refs

### Requirement: OpenSpec change archived through a PR
With OpenSpec, when the PR's change has every task done and is not yet archived, the skill SHALL offer to archive it on a new branch and open a PR for the archive, and SHALL act only after the user confirms.

#### Scenario: Change complete
- **WHEN** the merged PR implements an OpenSpec change whose tasks are all done
- **THEN** the skill offers to archive it and, on confirmation, archives it on a `chore/archive-<change>` branch, pushes it, and opens a PR without model attribution

#### Scenario: Tasks remaining
- **WHEN** the change still has unchecked tasks
- **THEN** the skill does not offer archiving and reports the remaining task count

#### Scenario: Archive declined
- **WHEN** the user declines the archive offer
- **THEN** the skill makes no commit, push, or PR for it

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill skips the archive step and does not mention OpenSpec

### Requirement: Linked issues closed on confirmation
The skill SHALL list issues the PR references as fixed that are still open after the merge, and SHALL close them, with a comment naming the PR, only after the user confirms.

#### Scenario: Issue not auto-closed
- **WHEN** the PR body says it fixes an issue that is still open after the merge
- **THEN** the skill offers to close it and closes it only on confirmation

#### Scenario: Issues already closed
- **WHEN** every linked issue was closed by GitHub on merge
- **THEN** the skill reports them as closed and takes no action

### Requirement: Never rewrites history
The skill SHALL NOT force-push, rewrite commits, push to the default branch, or delete any branch other than the merged PR's head branch.

#### Scenario: Default branch protected
- **WHEN** the archive step needs a commit
- **THEN** the commit goes on the archive branch, never directly on the default branch

### Requirement: Machine-readable result for callers
The skill SHALL end with an `ep-land-summary` block reporting the PR, outcome, default branch head, local and remote branch deletion results, archive status, and issue status.

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` runs landing after a merge
- **THEN** it can read from the summary whether the clone is clean and whether an archive or issue action is pending for the user

### Requirement: Works without subagents
The skill SHALL complete its full behavior sequentially in agents that cannot spawn subagents.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** every step runs inline with the same result and summary
