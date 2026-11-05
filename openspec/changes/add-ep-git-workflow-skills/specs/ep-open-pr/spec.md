# Spec Delta

## Purpose

Creates a GitHub pull request for the current branch with a title and body built from its commits and, when present, the active OpenSpec change, without model attribution.

## ADDED Requirements

### Requirement: Preconditions checked before opening
The skill SHALL verify the branch is not the default branch, has commits ahead of the base, and has no open PR already, before creating a PR.

#### Scenario: On default branch
- **WHEN** the current branch is the repository's default branch
- **THEN** the skill stops and asks the user to create or switch to a feature branch

#### Scenario: PR already exists
- **WHEN** an open PR already exists for the branch
- **THEN** the skill reports its URL and offers to update its body instead of creating a duplicate

#### Scenario: Uncommitted changes
- **WHEN** the working tree has uncommitted changes
- **THEN** the skill offers to run `ep-commit` first, or proceeds with committed work only if the user declines

### Requirement: Push before opening
The skill SHALL push the branch to the remote with upstream tracking if it is not yet pushed or is ahead of its upstream, and SHALL NOT force-push.

#### Scenario: Unpushed branch
- **WHEN** the branch has no upstream
- **THEN** the skill pushes it with upstream tracking and then opens the PR

### Requirement: Title and body from commits
The PR title SHALL summarize the change in Conventional Commit style and the body SHALL summarize the commits, list notable changes, and describe how to test.

#### Scenario: Body content
- **WHEN** the skill opens a PR for a branch with several commits
- **THEN** the body includes a summary, a list of changes, and test instructions

### Requirement: Reversibility classification
The PR body SHALL classify the change as a one-way door (some effect remains after a revert, such as data migrations, public interface changes, releases, external side effects, or security changes) or a two-way door (fully undoable by reverting), with a one-sentence reason, and for a one-way door SHALL list each irreversible element with a mitigation.

#### Scenario: Two-way door
- **WHEN** the branch only refactors internal code and adds tests
- **THEN** the body has a Reversibility section marking it a two-way door with a reason

#### Scenario: One-way door
- **WHEN** the branch adds a migration that drops a database column
- **THEN** the body marks it a one-way door, lists the column drop, gives a mitigation, and the final report mentions the classification

#### Scenario: Uncertain classification
- **WHEN** the skill cannot tell whether an effect is reversible
- **THEN** it classifies the PR as a one-way door and states what is uncertain

### Requirement: OpenSpec-aware body
When the branch relates to an active OpenSpec change, the PR body SHALL include the change name, a summary of the proposal's Why, the capabilities touched, and task progress (done/total).

#### Scenario: Active change
- **WHEN** the branch implements active change `add-auth` with 5 of 8 tasks done
- **THEN** the body names `add-auth`, summarizes its Why, lists its capabilities, and shows `5/8 tasks`

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the body is built from commits only and does not mention OpenSpec

### Requirement: No model attribution in PR
The PR title and body SHALL NOT contain model or tool attribution, such as "Generated with" footers.

#### Scenario: Host default footer
- **WHEN** the host agent's defaults would add a "Generated with" footer
- **THEN** the created PR body contains no such footer

### Requirement: Draft and base options
The skill SHALL support opening the PR as a draft and targeting a non-default base branch on request, and SHALL report the PR URL after creation.

#### Scenario: Draft requested
- **WHEN** the user asks for a draft PR
- **THEN** the PR is created as a draft and its URL is reported

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the skill gathers context and opens the PR sequentially with the same result
