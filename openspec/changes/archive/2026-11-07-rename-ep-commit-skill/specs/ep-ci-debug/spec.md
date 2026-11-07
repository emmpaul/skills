# Spec Delta

## MODIFIED Requirements

### Requirement: Fix and push gate
The skill SHALL propose the fix and apply it when the user agrees, committing it following `ep-commit-and-push` conventions with no attribution. It SHALL push only after the user confirms or when its caller owns pushing.

#### Scenario: Direct invocation
- **WHEN** the user runs `ep-ci-debug` directly
- **THEN** the skill shows the diagnosis and the proposed patch, and asks before committing and pushing

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` invokes it
- **THEN** the fix is committed and pushed without a separate prompt
