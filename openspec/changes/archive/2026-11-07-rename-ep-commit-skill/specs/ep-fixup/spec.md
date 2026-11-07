# Spec Delta

## MODIFIED Requirements

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
- **THEN** the skill proposes a normal commit following `ep-commit-and-push` conventions instead of a fixup
