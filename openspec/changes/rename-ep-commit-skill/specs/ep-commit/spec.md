# Spec Delta

## REMOVED Requirements

### Requirement: Gather repository context before committing
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability, unchanged apart from also reading the upstream state.

### Requirement: Split changes into logical commits
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability; its plan also names the push it will make.

### Requirement: Conventional Commit messages matching repo style
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability unchanged.

### Requirement: No model attribution
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability, with attribution removed before any push.

### Requirement: OpenSpec-aware scope
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability unchanged.

### Requirement: Never rewrite published history
**Reason**: The skill is renamed to `ep-commit-and-push`, which pushes after committing.
**Migration**: The no-rewrite rule moves to the `ep-commit-and-push` capability; the "no push unless asked" rule is replaced by its "Push after committing", "Plain pushes only", "Default branch push is gated", and "No-push mode" requirements. Callers that must stay local pass `--no-push`.

### Requirement: Works without subagents
**Reason**: The skill is renamed to `ep-commit-and-push`.
**Migration**: The requirement moves to the `ep-commit-and-push` capability unchanged.
