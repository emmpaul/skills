# Spec Delta

## Purpose

Checks a whole repository against its main OpenSpec specs, reporting for each requirement and scenario whether the code implements and tests it, and where code behavior has no spec.

## ADDED Requirements

### Requirement: Scope selection
The skill SHALL check every capability under the repository's main specs by default, or only the capabilities the user names.

#### Scenario: Single capability
- **WHEN** the user runs `ep-spec-drift ep-commit`
- **THEN** only the `ep-commit` capability is checked

#### Scenario: Unknown capability
- **WHEN** the user names a capability that has no main spec
- **THEN** the skill reports the name as unknown, lists the available capabilities, and checks nothing else

### Requirement: Requirement status
For each requirement and each scenario in scope, the skill SHALL assign one status: implemented, partial, missing, or untested. It SHALL cite the code locations, and the tests where they exist, that support the status.

#### Scenario: Implemented and tested
- **WHEN** code implements a scenario and a test exercises it
- **THEN** the scenario is reported implemented with the code and test locations

#### Scenario: Implemented but untested
- **WHEN** code implements a scenario but no test exercises it
- **THEN** the scenario is reported untested with the code location

#### Scenario: Missing behavior
- **WHEN** no code implements a requirement
- **THEN** the requirement is reported missing

#### Scenario: Partial implementation
- **WHEN** code implements some of a requirement's scenarios but not others
- **THEN** the requirement is reported partial and the report names the scenarios that are missing

### Requirement: Verified statuses
Each missing, partial, or untested status SHALL pass a verification step that searches for contrary evidence before it is reported. A status the step refutes SHALL be corrected.

#### Scenario: False missing corrected
- **WHEN** verification finds the behavior implemented under a different name
- **THEN** the status is changed to implemented or untested with that location

### Requirement: Unspecified behavior hotspots
The skill SHALL list externally visible behavior in the code that no requirement describes, such as commands, flags, endpoints, or outward actions, each with its location.

#### Scenario: Undocumented flag
- **WHEN** a skill or tool accepts a flag that no requirement mentions
- **THEN** the report lists the flag as unspecified behavior with its location

### Requirement: Read-only by default
Without `--issue` the skill SHALL change no files and post nothing to GitHub.

#### Scenario: Default run
- **WHEN** the user runs `ep-spec-drift` without flags
- **THEN** it prints the report and leaves the working tree and GitHub unchanged

### Requirement: Gated issue filing
With `--issue`, the skill SHALL show the issue title and body and create a single GitHub issue only after the user confirms. The issue SHALL carry no model or tool attribution.

#### Scenario: Confirmed issue
- **WHEN** the user runs `ep-spec-drift --issue` and confirms the shown issue
- **THEN** one issue containing the drift report is created and its URL reported

#### Scenario: No drift found
- **WHEN** every requirement in scope is implemented and tested and no hotspot is found
- **THEN** no issue is proposed and the skill reports that the specs and code agree

#### Scenario: Cannot ask for confirmation
- **WHEN** `--issue` is given in a run that cannot get a user's answer
- **THEN** no issue is created and the report says so

### Requirement: Repository without OpenSpec
When the repository has no OpenSpec root or no main specs, the skill SHALL report that the check is not applicable and stop.

#### Scenario: No OpenSpec root
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill reports the check as not applicable, with the reason, and does nothing else

#### Scenario: OpenSpec root without main specs
- **WHEN** the repository has an OpenSpec root but no main specs
- **THEN** the skill reports that there are no specs to check and stops

### Requirement: Summary for callers
The report SHALL end with a summary block that gives the outcome (clean, drift, or not applicable) and counts of requirements by status and of hotspots.

#### Scenario: Drift summary
- **WHEN** the check finds two missing requirements and one hotspot
- **THEN** the summary block reports outcome `drift`, missing=2, and hotspots=1

### Requirement: Parallel capabilities with sequential fallback
When the host agent can spawn subagents, the skill SHALL check capabilities in parallel. Otherwise it SHALL check them one at a time with the same report.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** capabilities are checked and verified sequentially and the report has the same structure
