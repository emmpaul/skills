# Spec Delta

## Purpose

Triages open dependency-update pull requests from Dependabot and Renovate by risk, recommends what to do with each, and hands the ones the user picks to `ep-babysit-pr`.

## ADDED Requirements

### Requirement: Dependency PR discovery
The skill SHALL list open PRs in the current repository authored by Dependabot or Renovate, or the PR numbers the user names, and SHALL report when there are none.

#### Scenario: No dependency PRs
- **WHEN** the repository has no open Dependabot or Renovate PRs
- **THEN** the skill reports that there is nothing to triage and stops

#### Scenario: Specific PRs given
- **WHEN** the user runs `ep-deps 12 15`
- **THEN** only PRs #12 and #15 are triaged

### Requirement: Risk classification
For each PR the skill SHALL determine the package, the from and to versions, and the semver bump. It SHALL classify the PR as low, medium, or high risk using the bump, breaking-change notes, CI state, and whether the dependency is runtime or development-only.

#### Scenario: Patch bump with green CI
- **WHEN** a development dependency moves from 2.3.1 to 2.3.2, the release notes mention no breaking change, and checks pass
- **THEN** the PR is classified low risk

#### Scenario: Major bump
- **WHEN** a runtime dependency moves from 4.x to 5.0.0
- **THEN** the PR is classified high risk and the report quotes the breaking changes from the release notes, or states that none could be found

#### Scenario: Failing checks
- **WHEN** a PR's required checks fail
- **THEN** the PR is classified at least medium risk and the failing checks are named

### Requirement: Release notes as evidence
The skill SHALL base breaking-change claims on the release notes or changelog linked from the PR, or on the upstream release. When none is available it SHALL say so instead of guessing.

#### Scenario: No changelog available
- **WHEN** neither the PR body nor the upstream repository provides release notes for the new version
- **THEN** the report marks the notes as unavailable and does not classify the PR as low risk on the strength of the notes

### Requirement: Security advisories
The skill SHALL flag PRs that fix a known security advisory and SHALL list them first in the report, whatever their risk class.

#### Scenario: Security fix
- **WHEN** a PR's body or labels reference a security advisory
- **THEN** the report lists that PR first, names the advisory, and marks it as a security update

### Requirement: Grouped recommendations
The report SHALL group PRs into security updates, low risk (recommended to merge), needs attention, and recommended to close or hold, with a one-line reason for each PR.

#### Scenario: Mixed set
- **WHEN** three low-risk PRs and one high-risk PR are triaged
- **THEN** the three appear together under low risk and the high-risk one under needs attention, each with a reason

### Requirement: Gated handoff to babysitting
The skill SHALL start `ep-babysit-pr` only on PRs the user explicitly selects after seeing the report. When `ep-babysit-pr` is not installed, it SHALL tell the user instead.

#### Scenario: User selects low-risk group
- **WHEN** the user confirms babysitting the low-risk group
- **THEN** the skill runs `ep-babysit-pr` on each selected PR, one at a time, and reports each outcome

#### Scenario: No confirmation
- **WHEN** the user does not confirm, or the run cannot ask, such as in a scheduled run
- **THEN** no PR is handed off and nothing is posted

### Requirement: Never merges directly
The skill SHALL NOT merge, approve, or push to any PR itself. Any merge happens only through `ep-babysit-pr` and its gates.

#### Scenario: Low-risk PR
- **WHEN** a PR is classified low risk
- **THEN** the skill recommends it but does not merge it

### Requirement: Gated comments and closes
The skill SHALL comment on or close a dependency PR only when the user explicitly asks for that PR, and anything it posts SHALL carry no model or tool attribution.

#### Scenario: Close rejected update
- **WHEN** the user asks to close a PR held back for a breaking change
- **THEN** the skill closes it with a comment stating the reason and no attribution

### Requirement: Works without OpenSpec
The skill's behavior SHALL NOT depend on OpenSpec.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** triage and handoff behave the same and the output does not mention OpenSpec

### Requirement: Parallel triage with sequential fallback
When the host agent can spawn subagents, the skill SHALL triage PRs in parallel. Otherwise it SHALL triage them one at a time, with the same report.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** each PR is triaged in sequence and the report has the same groups and fields
