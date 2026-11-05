# Spec Delta

## Purpose

Turns the current working-tree changes into one or more well-scoped Conventional Commits that match the repository's style, reference the active OpenSpec change when one exists, and never carry model attribution.

## ADDED Requirements

### Requirement: Gather repository context before committing
The skill SHALL collect branch, staged and unstaged diff, recent commit history, and OpenSpec state before proposing any commit.

#### Scenario: Context collected
- **WHEN** the user invokes `ep-commit` in a git repository with changes
- **THEN** the skill reads the diff, the last commits on the branch, and the OpenSpec state before drafting messages

#### Scenario: Nothing to commit
- **WHEN** the working tree has no staged or unstaged changes
- **THEN** the skill reports that there is nothing to commit and makes no commit

### Requirement: Split changes into logical commits
The skill SHALL group changes into one or more commits, each covering a single coherent purpose, and SHALL present the planned grouping before creating commits.

#### Scenario: Mixed changes
- **WHEN** the diff contains unrelated changes (for example a bug fix and a docs edit)
- **THEN** the skill proposes separate commits for each and shows the files or hunks in each

#### Scenario: Staged-only intent
- **WHEN** the user has staged a subset of changes and asks to commit only staged changes
- **THEN** the skill commits only the staged changes and leaves unstaged changes untouched

### Requirement: Conventional Commit messages matching repo style
Each commit message SHALL use Conventional Commits format (`type(scope): subject`) and SHALL follow observable conventions in recent history such as subject length and casing.

#### Scenario: Message format
- **WHEN** the skill creates a commit
- **THEN** the subject has the form `type(scope): subject` with a type from the Conventional Commits set

#### Scenario: Body explains why
- **WHEN** the reason for a change is not evident from the subject
- **THEN** the commit body explains why the change was made

### Requirement: No model attribution
Commit messages SHALL NOT contain model or tool attribution, including `Co-Authored-By` trailers naming an AI model and "Generated with" footers.

#### Scenario: Host agent injects attribution
- **WHEN** the host agent's defaults would append a `Co-Authored-By` trailer for a model
- **THEN** the created commit contains no such trailer

### Requirement: OpenSpec-aware scope
When the repository has exactly one active OpenSpec change that the diff relates to, the skill SHALL use the change name as the commit scope and SHALL offer to mark `tasks.md` items completed by the diff.

#### Scenario: Active change
- **WHEN** an active change `add-auth` exists and the diff implements its task 2.1
- **THEN** the commit scope is `add-auth` and the skill offers to tick task 2.1

#### Scenario: Multiple active changes
- **WHEN** several active changes exist
- **THEN** the skill picks the change the diff touches, or asks the user when ambiguous

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill derives scope from the changed paths and makes no mention of OpenSpec

### Requirement: Never rewrite published history
The skill SHALL NOT amend, rebase, or otherwise rewrite commits that exist on the remote, and SHALL NOT push unless asked.

#### Scenario: Pushed commit
- **WHEN** the last commit is already on the upstream branch
- **THEN** the skill creates a new commit rather than amending

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents.

#### Scenario: Agent without subagents and large diff
- **WHEN** the host agent has no subagent capability and the diff is large
- **THEN** the skill analyzes the diff sequentially and still produces the commit plan
