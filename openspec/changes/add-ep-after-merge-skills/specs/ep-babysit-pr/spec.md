# Spec Delta

## ADDED Requirements

### Requirement: Post-merge landing
After it merges a PR, the skill SHALL clean up the local clone by running `ep-land` on that PR when installed, or its equivalent steps inline otherwise, and SHALL record the landing result in its state file and final report.

#### Scenario: Merge followed by landing
- **WHEN** the skill merges a PR
- **THEN** it updates the local default branch, deletes the merged local branch when safe, and reports the landing result

#### Scenario: Remote branch already deleted
- **WHEN** the merge already deleted the remote branch and switched the local checkout to the default branch
- **THEN** landing completes without error and does not report the missing remote branch as a failure

#### Scenario: Landing problem does not undo merge
- **WHEN** landing cannot complete, for example because the local default branch has diverged
- **THEN** the skill still records the outcome as merged, records the landing problem, and tells the user what to do

#### Scenario: PR merged by someone else
- **WHEN** the skill observes that the PR was merged by another actor
- **THEN** it runs landing the same way before stopping

#### Scenario: ep-land not installed
- **WHEN** `ep-land` is not installed
- **THEN** the skill performs the same local cleanup inline

### Requirement: Post-merge follow-ups offered, not taken
After landing, the skill SHALL report any pending OpenSpec archive and linked issues left open as offers to the user, and SHALL NOT archive a change, open an archive PR, or close issues on its own.

#### Scenario: Change ready to archive
- **WHEN** the merged PR's OpenSpec change has every task done
- **THEN** the final report says the change is ready to archive and suggests running `ep-land <n>`, and no archive commit, branch, or PR is created

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the final report has no archive item and does not mention OpenSpec
