# Spec Delta

## Purpose

Attaches a fix to the commit it corrects as a `fixup!` commit, and squashes those commits only when history can be rewritten safely, so branch history stays logical.

## ADDED Requirements

### Requirement: Target commit selection
The skill SHALL select, for each fix in the working tree, the commit on the branch (since its merge base) that introduced the lines being corrected. When no single commit fits, it SHALL ask the user.

#### Scenario: Fix to one commit's lines
- **WHEN** the uncommitted change edits lines that a single branch commit introduced
- **THEN** the skill targets that commit

#### Scenario: Fix spans several commits
- **WHEN** a change touches lines from several branch commits
- **THEN** the skill splits it into one fixup per target commit, or asks when the hunks cannot be separated

#### Scenario: No branch commit to target
- **WHEN** the fixed lines come from the base, not from branch commits
- **THEN** the skill proposes a normal commit following `ep-commit` conventions instead of a fixup

### Requirement: Fixup commits
The skill SHALL create `fixup!` commits whose subject matches the target commit's subject, with no model or tool attribution.

#### Scenario: Fixup created
- **WHEN** a target commit is selected
- **THEN** a commit with subject `fixup! <target subject>` is created and contains only that fix

### Requirement: Safe autosquash
The skill SHALL autosquash fixup commits only when the user invokes it directly and asks for it. It SHALL squash unpushed commits without further confirmation, and SHALL squash pushed commits only after explicit confirmation, pushing with `--force-with-lease`.

#### Scenario: Unpushed commits
- **WHEN** the user asks for autosquash and none of the affected commits are on the remote
- **THEN** the skill squashes them locally without a force push

#### Scenario: Pushed commits
- **WHEN** the user asks for autosquash and affected commits are on the remote
- **THEN** the skill explains the rewrite, asks for confirmation, and pushes with `--force-with-lease` only when confirmed

#### Scenario: Never plain force
- **WHEN** a rewritten branch is pushed
- **THEN** `--force` is never used

### Requirement: No-rewrite mode for callers
When invoked by another skill, or with a no-rewrite option, the skill SHALL create fixup commits only and SHALL NOT autosquash or force-push.

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` invokes `ep-fixup`
- **THEN** only `fixup!` commits are created and pushed with a plain push

### Requirement: Summary block
The skill SHALL end with an `ep-fixup-summary` block that gives the outcome, head sha, the fixup commits created with their target shas, and whether history was rewritten.

#### Scenario: Caller parses result
- **WHEN** a caller invokes `ep-fixup`
- **THEN** it receives each fixup sha and its target sha, and `rewritten: false` in no-rewrite mode

### Requirement: OpenSpec scope
When the repository has an OpenSpec root, a fixup commit SHALL keep the target commit's subject unchanged, including its OpenSpec scope.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill behaves the same and does not mention OpenSpec
