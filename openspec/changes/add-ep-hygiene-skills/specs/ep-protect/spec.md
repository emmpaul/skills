# Spec Delta

## Purpose

Audits a GitHub repository's default-branch protection against a safe baseline and, only with explicit confirmation, adds missing protection so autonomous merges stay behind human-controlled gates.

## ADDED Requirements

### Requirement: Protection audit
The skill SHALL read the default branch's classic branch protection and every active ruleset that targets it, and report the effective state of each baseline item.

#### Scenario: Protection via rulesets only
- **WHEN** the default branch has no classic protection but an active ruleset requires one approving review
- **THEN** the report shows the required-review item as met and names the ruleset that provides it

#### Scenario: No protection at all
- **WHEN** the default branch has neither classic protection nor any active ruleset
- **THEN** the report marks every baseline item as missing

### Requirement: Safe baseline
The baseline SHALL be: at least one required approving review, required status checks, force pushes blocked, branch deletion blocked, and conversation resolution required.

#### Scenario: Gap reported
- **WHEN** protection requires reviews but allows force pushes
- **THEN** the report lists "force pushes blocked" as a gap and the other met items as met

### Requirement: Status checks match CI
The skill SHALL derive the expected required status checks from check names that have actually reported on recent default-branch commits or PRs, and SHALL flag required checks that never report.

#### Scenario: Stale required check
- **WHEN** protection requires a check named `build` that has not reported on any of the recent commits
- **THEN** the report flags `build` as a required check that never reports, which would block every merge

#### Scenario: No CI in repository
- **WHEN** no check has reported on recent commits
- **THEN** the required-status-checks item is reported as not applicable, with the reason

### Requirement: Read-only check mode
With `--check`, the skill SHALL make no changes, print the audit, end with a summary block whose outcome is `pass` or `gaps`, and SHALL treat a missing required approving review as `gaps`.

#### Scenario: Preflight before babysitting
- **WHEN** the user runs `ep-protect --check` on a repository without required reviews
- **THEN** the skill reports outcome `gaps`, names the missing review requirement, and changes nothing

#### Scenario: Baseline met
- **WHEN** every baseline item is met
- **THEN** the summary block reports outcome `pass`

### Requirement: Gated apply
Outside `--check`, the skill SHALL show the exact API request (method, endpoint, and payload) that would close the gaps, and SHALL send it only after the user explicitly confirms that request.

#### Scenario: User confirms
- **WHEN** the user confirms the shown request
- **THEN** the skill sends it, re-reads protection, and reports the new state of each baseline item

#### Scenario: User declines
- **WHEN** the user declines or does not answer
- **THEN** no request is sent and the report states that nothing was changed

#### Scenario: Agent cannot ask for confirmation
- **WHEN** the skill runs where it cannot get a user's answer, such as a scheduled or non-interactive run
- **THEN** it behaves as `--check` and changes nothing

### Requirement: Never weaken protection
The skill SHALL only add or tighten settings and SHALL preserve every existing setting it does not tighten, including required reviewers, required checks, and bypass lists.

#### Scenario: Stricter existing setting
- **WHEN** protection already requires two approving reviews
- **THEN** the proposed request keeps two and does not lower it to one

#### Scenario: Existing required checks preserved
- **WHEN** protection already requires checks `lint` and `test` and CI also reports `build`
- **THEN** the proposed request keeps `lint` and `test` and adds `build` only if the user selects it

### Requirement: Insufficient permission reported
When the token lacks the rights to read or change protection, the skill SHALL say so plainly, name the permission that is missing, and SHALL NOT report the baseline as met.

#### Scenario: Not an admin
- **WHEN** reading protection returns a permission error
- **THEN** the skill reports that repository admin rights are needed, marks the audit as incomplete, and the summary outcome is `unknown`

### Requirement: Works without OpenSpec
The skill's behavior SHALL NOT depend on OpenSpec.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the audit, check mode, and apply behave exactly as in a repository with OpenSpec and the output does not mention OpenSpec

### Requirement: No attribution
Nothing the skill writes to GitHub SHALL carry model or tool attribution.

#### Scenario: Applied change
- **WHEN** the skill applies protection settings
- **THEN** no field it sets contains a model name or a "Generated with" note
