# Spec Delta

## MODIFIED Requirements

### Requirement: Preconditions checked before opening
The skill SHALL verify the branch is not the default branch, has commits ahead of the base, and has no open PR already, before creating a PR.

#### Scenario: On default branch
- **WHEN** the current branch is the repository's default branch
- **THEN** the skill stops and asks the user to create or switch to a feature branch

#### Scenario: PR already exists
- **WHEN** an open PR already exists for the branch
- **THEN** the skill reports its URL and offers to update its body instead of creating a duplicate

#### Scenario: Uncommitted changes
- **WHEN** the working tree has uncommitted changes
- **THEN** the skill offers to run `ep-commit-and-push` first, or proceeds with committed work only if the user declines
