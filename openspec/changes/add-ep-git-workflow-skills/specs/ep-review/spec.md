# Spec Delta

## Purpose

Reviews a code change across several dimensions, including conformance to the active OpenSpec change, verifies each finding before reporting it, and reports locally or as PR comments.

## ADDED Requirements

### Requirement: Review targets
The skill SHALL accept as target the local uncommitted diff (default), a branch compared to its base, or a GitHub PR number.

#### Scenario: Default target
- **WHEN** the user invokes `ep-review` with no target
- **THEN** the skill reviews the uncommitted diff, or the branch versus its base if the tree is clean

#### Scenario: PR target
- **WHEN** the user invokes `ep-review 42`
- **THEN** the skill reviews the diff of PR #42

### Requirement: Multi-dimension review
The skill SHALL review the target along the dimensions correctness, spec conformance, tests, and security.

#### Scenario: All dimensions covered
- **WHEN** a review runs
- **THEN** the report shows findings, or an explicit "no findings", for each of the four dimensions

### Requirement: Spec conformance against OpenSpec
When the target relates to an active OpenSpec change, the spec conformance dimension SHALL check each delta-spec requirement and scenario against the diff and flag requirements with no implementation, behavior not covered by any requirement, and scenarios with no test.

#### Scenario: Missing requirement
- **WHEN** a delta spec requires behavior that the diff does not implement
- **THEN** the review reports a spec-conformance finding naming that requirement

#### Scenario: Unspecified behavior
- **WHEN** the diff adds externally visible behavior that no requirement describes
- **THEN** the review reports it as out-of-spec

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the spec conformance dimension is reported as not applicable and the other dimensions run normally

### Requirement: Verified findings
Each candidate finding SHALL pass a verification step that tries to disprove it before it is reported, and each reported finding SHALL include location, severity (critical, major, minor), and a concrete failure scenario.

#### Scenario: False positive dropped
- **WHEN** verification shows a candidate finding cannot occur
- **THEN** the finding is not reported

#### Scenario: Finding shape
- **WHEN** a finding is reported
- **THEN** it includes file and line, severity, summary, and a failure scenario

### Requirement: Output modes
The skill SHALL print findings ranked most severe first by default, and SHALL post them as PR review comments only when the user passes `--comment` on a PR target.

#### Scenario: Comment mode
- **WHEN** the user runs `ep-review 42 --comment`
- **THEN** findings are posted as review comments on PR #42 without model attribution

#### Scenario: Default mode
- **WHEN** no `--comment` flag is given
- **THEN** nothing is posted to GitHub

### Requirement: Machine-readable result for callers
The skill SHALL produce a summary with counts of verified findings by severity and dimension, and spec-conformance status, usable by `ep-babysit-pr`.

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` runs a review round
- **THEN** it receives finding counts by severity and whether spec conformance passed

### Requirement: Parallel dimensions with sequential fallback
When the host agent can spawn subagents, the skill SHALL review dimensions in parallel; otherwise it SHALL review them sequentially with the same output.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the four dimensions and verification run sequentially and the report has the same structure

#### Scenario: High effort in Claude Code
- **WHEN** the user requests high effort in Claude Code
- **THEN** the skill MAY run the review as a Workflow with fan-out and per-finding verification
