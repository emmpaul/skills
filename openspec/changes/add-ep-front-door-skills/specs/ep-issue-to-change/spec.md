# Spec Delta

## Purpose

Turns a GitHub issue into an OpenSpec change whose proposal is grounded in the issue, optionally linking the change back on the issue.

## ADDED Requirements

### Requirement: Issue input
The skill SHALL take a GitHub issue number or URL and read its title, body, labels, and comments.

#### Scenario: Issue not found
- **WHEN** the issue does not exist or is not readable with the current `gh` credentials
- **THEN** the skill stops and reports the error without creating anything

### Requirement: Requires an OpenSpec root
The skill SHALL run only in a repository with an OpenSpec root and SHALL NOT initialize OpenSpec itself.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill stops, says OpenSpec is not set up here, and creates no files

### Requirement: Change creation through the CLI
The skill SHALL derive a kebab-case change name from the issue, create the change with `openspec new change`, and SHALL NOT hand-create change directories.

#### Scenario: Name already taken
- **WHEN** a change with the derived name already exists
- **THEN** the skill asks whether to continue that change or pick a new name

### Requirement: Proposal grounded in the issue
The skill SHALL write the change's proposal from the issue, referencing the issue number, mapping the issue's problem to Why and its asks to What Changes, and listing unresolved questions instead of inventing scope.

#### Scenario: Vague issue
- **WHEN** the issue does not say which behavior should change
- **THEN** the proposal records the ambiguity as open questions and the report asks the user to resolve them

#### Scenario: Existing capability touched
- **WHEN** the issue asks to change behavior an existing spec describes
- **THEN** the proposal lists that capability under Modified Capabilities by its existing path

### Requirement: Planning only
The skill SHALL write the proposal only, leave specs, design, and tasks to the OpenSpec propose workflow, and SHALL NOT edit project code.

#### Scenario: After proposal
- **WHEN** the proposal is written
- **THEN** the skill reports the change path and points to the propose workflow for the remaining artifacts

### Requirement: Optional link comment
The skill SHALL comment on the issue linking the change only when the user confirms or passes `--comment`, and the comment SHALL carry no attribution.

#### Scenario: Default run
- **WHEN** the user runs the skill without `--comment`
- **THEN** the skill shows the draft comment and posts it only after confirmation

### Requirement: Summary block
The skill SHALL end with an `ep-issue-to-change-summary` block giving the outcome, issue number, change name, and whether a comment was posted.

#### Scenario: Change created
- **WHEN** the skill creates change `fix-sso-login` from issue #17
- **THEN** the block reports `outcome: created`, `issue: 17`, `change: fix-sso-login`
