# Spec Delta

## MODIFIED Requirements

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
