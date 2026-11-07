# Spec Delta

## MODIFIED Requirements

### Requirement: Branch adaptation
For each needs-update interaction, the skill SHALL update the branch's code so it is correct with the new base. It SHALL commit each adaptation following `ep-commit-and-push` conventions as a commit separate from the merge commit.

#### Scenario: Call sites updated
- **WHEN** base renamed a function that the branch calls
- **THEN** the skill updates the branch's call sites and commits that in its own commit after the merge commit

#### Scenario: Ambiguous adaptation
- **WHEN** a needs-update interaction has more than one reasonable fix with different behaviour
- **THEN** the skill does not choose one, presents the options, and waits for the user
