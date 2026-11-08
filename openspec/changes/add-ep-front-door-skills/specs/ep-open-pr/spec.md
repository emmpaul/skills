# Spec Delta

## ADDED Requirements

### Requirement: Linked issue reference
The PR body SHALL reference the branch's linked issue with a closing keyword for fixes and features, or a plain reference otherwise. The linked issue comes from the branch's `ep-issue` key when it is set, and the key is final: digits link that issue, and `none` links no issue, whatever the branch name says. Only when the key is unset SHALL the skill parse a name of the form `<type>/<issue>-<slug>`, with `<type>` a Conventional Commit type, for the issue number.

#### Scenario: Branch started from an issue
- **WHEN** the branch was created by `ep-start 17` and the PR is a fix
- **THEN** the PR body contains `Closes #17`

#### Scenario: No linked issue
- **WHEN** the branch has no recorded issue and its name carries no issue number
- **THEN** the PR body has no issue reference and nothing else changes

#### Scenario: Key set to none
- **WHEN** the branch is `fix/404-page-shows-stack-trace` and its `ep-issue` key is `none`
- **THEN** the PR body has no issue reference, and the name's `404` is not read as an issue

#### Scenario: Key unset, conventional name
- **WHEN** the branch `fix/17-login-fails-with-sso` has no `ep-issue` key and the PR is a fix
- **THEN** the PR body contains `Closes #17`
