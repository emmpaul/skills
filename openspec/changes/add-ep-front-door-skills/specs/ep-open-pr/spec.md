# Spec Delta

## ADDED Requirements

### Requirement: Linked issue reference
When the branch has a linked issue recorded by `ep-start`, or its name follows `<type>/<issue>-<slug>`, the PR body SHALL reference that issue with a closing keyword for fixes and features, or a plain reference otherwise.

#### Scenario: Branch started from an issue
- **WHEN** the branch was created by `ep-start 17` and the PR is a fix
- **THEN** the PR body contains `Closes #17`

#### Scenario: No linked issue
- **WHEN** the branch has no recorded issue and its name carries no issue number
- **THEN** the PR body has no issue reference and nothing else changes
