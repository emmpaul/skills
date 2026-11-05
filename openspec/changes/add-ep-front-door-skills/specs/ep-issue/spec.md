# Spec Delta

## Purpose

Drafts or triages a GitHub issue: structured body, existing labels, reversibility call, and a duplicate check, creating or updating it only after confirmation.

## ADDED Requirements

### Requirement: Issue modes
The skill SHALL draft a new issue from a free-text description, or triage an existing issue when given its number.

#### Scenario: New issue from description
- **WHEN** the user runs `ep-issue "login fails with SSO"`
- **THEN** the skill drafts a title and body for a new issue

#### Scenario: Triage existing issue
- **WHEN** the user runs `ep-issue 17`
- **THEN** the skill reads issue #17 and proposes missing sections, labels, and a reversibility call without rewriting the author's text

### Requirement: Structured issue body
The drafted body SHALL contain a problem statement and, for bugs, reproduction steps with expected and actual behavior, or, for features, acceptance criteria; unknown facts SHALL be marked as open questions rather than invented.

#### Scenario: Bug without known repro
- **WHEN** the description reports a bug but gives no reproduction steps
- **THEN** the reproduction section lists what is known and an open question asking for steps

### Requirement: Existing labels only
The skill SHALL choose labels only from the repository's existing labels and SHALL NOT create labels.

#### Scenario: No matching label
- **WHEN** no existing label fits the issue type
- **THEN** the issue is drafted without that label and the report says none matched

### Requirement: Reversibility call
The skill SHALL classify the requested work as a one-way or two-way door using the same rules as `ep-open-pr`, and include the call with a one-sentence reason in the body.

#### Scenario: Destructive data change requested
- **WHEN** the issue asks to drop a stored field
- **THEN** the body marks it a one-way door and names the irreversible element

### Requirement: Duplicate check before creating
Before creating an issue, the skill SHALL search open and recently closed issues for likely duplicates and show any matches to the user.

#### Scenario: Likely duplicate found
- **WHEN** an open issue has a closely matching title or symptom
- **THEN** the skill shows it and asks whether to create anyway, comment there instead, or stop

### Requirement: Confirmed GitHub writes
The skill SHALL show the full draft and SHALL create the issue, edit it, or apply labels only after the user confirms, or when `--yes` is passed and no duplicate was found.

#### Scenario: Default run
- **WHEN** the user runs `ep-issue` without `--yes`
- **THEN** nothing is written to GitHub until the user confirms the draft

#### Scenario: No attribution
- **WHEN** the skill creates or edits an issue
- **THEN** the title, body, and any comment carry no model or tool attribution

### Requirement: Summary block
The skill SHALL end with an `ep-issue-summary` block giving the outcome, issue number or null, door classification, and labels applied.

#### Scenario: Issue created
- **WHEN** the skill creates issue #42
- **THEN** the summary block reports `outcome: created` and `issue: 42`
