# Spec Delta

## MODIFIED Requirements

### Requirement: Evidence-based confidence score
After each round the skill SHALL compute a confidence score from 0 to 100 from verifiable evidence, report its breakdown, and SHALL NOT use self-assessed confidence.

#### Scenario: Score breakdown shown
- **WHEN** the skill computes the score
- **THEN** it reports each evidence item, its weight, and whether it was met

#### Scenario: No OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** OpenSpec-dependent items are dropped and their weight is redistributed to test evidence

#### Scenario: Documentation-only PR
- **WHEN** every file the PR changes is a documentation or planning file by path (such as `*.md` outside agent instruction files, `docs/**`, or `openspec/**`)
- **THEN** the test evidence item counts as met and the breakdown marks it "not applicable: no code changed"

#### Scenario: Agent instruction files changed
- **WHEN** the PR changes a file in a skill folder (a directory containing `SKILL.md`), an `AGENTS.md` or `CLAUDE.md`, or a file under `.claude/`
- **THEN** the PR is not documentation-only and test evidence is required as usual
