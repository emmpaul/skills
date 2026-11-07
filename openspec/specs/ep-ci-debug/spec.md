# ep-ci-debug Specification

## Purpose
Diagnoses a failing CI check from its logs, classifies the cause, and proposes or applies a fix without weakening tests, as a standalone skill that `ep-babysit-pr` can call.

## Requirements

### Requirement: Check selection
The skill SHALL debug the check the user names, or every failing check on the current branch's PR when none is named, starting with required checks.

#### Scenario: No failing checks
- **WHEN** the PR has no failing checks
- **THEN** the skill reports that and changes nothing

#### Scenario: No PR
- **WHEN** the current branch has no open PR and no run is named
- **THEN** the skill uses the latest failed workflow run for the branch, or stops when there is none

### Requirement: Log-based diagnosis
The skill SHALL diagnose each failure from the failed job logs or the check's details. It SHALL quote the decisive log lines in its report.

#### Scenario: Diagnosis reported
- **WHEN** a failure is diagnosed
- **THEN** the report names the check, the failing step, the quoted log lines, and the cause

### Requirement: Failure classification
The skill SHALL classify each failure as code, test, flaky-infra, config, or secret, and SHALL act according to the class.

#### Scenario: Code failure
- **WHEN** the failure is caused by the branch's code
- **THEN** the class is code and the skill fixes the code

#### Scenario: Missing secret
- **WHEN** the failure is caused by a missing or invalid secret or permission
- **THEN** the class is secret and the skill reports what is needed without changing code

### Requirement: Local reproduction
Before changing code, the skill SHALL try to reproduce the failure locally with the same command the check runs. If that is not possible, it SHALL say why.

#### Scenario: Reproduced locally
- **WHEN** the failing command can run locally
- **THEN** the skill runs it before and after the fix and reports both results

#### Scenario: Cannot reproduce
- **WHEN** the failure depends on the CI environment
- **THEN** the report states that the fix is unverified locally and why

### Requirement: Infra re-run once
For a flaky-infra failure, the skill SHALL re-run the failed jobs at most once. If the re-run fails again, it SHALL report the failure instead of changing code.

#### Scenario: Re-run fails again
- **WHEN** a re-run of a flaky-infra failure fails again
- **THEN** the skill reports it to the user and makes no code change

### Requirement: Never weaken tests
The skill SHALL NOT skip, delete, loosen, or mark tests as expected-to-fail, and SHALL NOT disable or edit a check to make it pass, unless the user explicitly asks.

#### Scenario: Test failure from a real bug
- **WHEN** a test fails because the code is wrong
- **THEN** the skill fixes the code, not the test

#### Scenario: Test itself is wrong
- **WHEN** the test asserts behaviour that the branch intentionally changed
- **THEN** the skill updates the test only when the intended behaviour is documented in the PR or the active OpenSpec change, and says so in the report

### Requirement: Fix and push gate
The skill SHALL propose the fix and apply it when the user agrees, committing it following `ep-commit-and-push` conventions with no attribution. It SHALL push only after the user confirms or when its caller owns pushing.

#### Scenario: Direct invocation
- **WHEN** the user runs `ep-ci-debug` directly
- **THEN** the skill shows the diagnosis and the proposed patch, and asks before committing and pushing

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` invokes it
- **THEN** the fix is committed and pushed without a separate prompt

### Requirement: Summary block
The skill SHALL end with an `ep-ci-debug-summary` block giving, for each check, the check name, class, outcome (fixed, rerun, reported), and the fix commit sha when there is one.

#### Scenario: Caller parses result
- **WHEN** `ep-babysit-pr` invokes `ep-ci-debug`
- **THEN** it can read each check's class and fix sha to update its attempt counts

### Requirement: Parallel diagnosis with sequential fallback
When the host agent can spawn subagents and several checks fail, the skill SHALL diagnose them in parallel and apply the patches itself, one commit per cause. Otherwise it SHALL diagnose them sequentially.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** checks are diagnosed one at a time and the report has the same structure

### Requirement: OpenSpec context
When the repository has an OpenSpec root, the skill SHALL use the active change's specs to decide whether a failing test reflects intended new behaviour.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill uses only the PR description and commits as intent, and does not mention OpenSpec
