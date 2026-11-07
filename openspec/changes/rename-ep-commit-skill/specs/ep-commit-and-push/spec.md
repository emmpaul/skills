# Spec Delta

## Purpose

Turns the current working-tree changes into one or more well-scoped Conventional Commits that match the repository's style, reference the active OpenSpec change when one exists, never carry model attribution, and then push the branch with a plain push unless the caller asks for commits only.

## ADDED Requirements

### Requirement: Gather repository context before committing
The skill SHALL collect branch, upstream, staged and unstaged diff, recent commit history, and OpenSpec state before proposing any commit.

#### Scenario: Context collected
- **WHEN** the user invokes `ep-commit-and-push` in a git repository with changes
- **THEN** the skill reads the diff, the last commits on the branch, the upstream state, and the OpenSpec state before drafting messages

#### Scenario: Nothing to commit
- **WHEN** the working tree has no staged, unstaged, or untracked changes
- **THEN** the skill reports that there is nothing to commit, makes no commit, and pushes nothing, even when the branch has unpushed commits

### Requirement: Split changes into logical commits
The skill SHALL group changes into one or more commits, each covering a single coherent purpose, and SHALL present the planned grouping, with the push it will make, before creating commits.

#### Scenario: Mixed changes
- **WHEN** the diff contains unrelated changes (for example a bug fix and a docs edit)
- **THEN** the skill proposes separate commits for each and shows the files or hunks in each

#### Scenario: Staged-only intent
- **WHEN** the user has staged a subset of changes and asks to commit only staged changes
- **THEN** the skill commits only the staged changes and leaves unstaged changes untouched

#### Scenario: Plan names the push
- **WHEN** the skill presents its commit plan and `--no-push` is not in effect
- **THEN** the plan names the branch and remote it will push to and the number of commits that push sends, counting earlier unpushed commits

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

#### Scenario: Attribution removed before the push
- **WHEN** a created commit carries an attribution line
- **THEN** the skill rewrites that message while the commit is still unpushed, and pushes only after every created message is free of attribution

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
The skill SHALL NOT amend, rebase, or otherwise rewrite commits that exist on the remote.

#### Scenario: Pushed commit
- **WHEN** the last commit is already on the upstream branch
- **THEN** the skill creates a new commit rather than amending

### Requirement: Push after committing
After it has created its commits and verified them free of attribution, the skill SHALL push the current branch: `git push -u origin HEAD` when the branch has no upstream, `git push` when it has one. It SHALL push only when it created at least one commit in this run.

#### Scenario: Branch without upstream
- **WHEN** the skill has committed on a branch with no upstream and `origin` exists
- **THEN** it runs `git push -u origin HEAD` and reports the remote branch it pushed to

#### Scenario: Branch with upstream
- **WHEN** the skill has committed on a branch whose upstream exists
- **THEN** it runs `git push` and reports the commits pushed

#### Scenario: No remote to push to
- **WHEN** the branch has no upstream and the repository has no `origin` remote
- **THEN** the skill keeps the commits, pushes nothing, and reports that no remote was found

### Requirement: Plain pushes only
The skill SHALL push with a plain push only: never `--force`, `--force-with-lease`, or a `+refspec`, and never `--no-verify` unless the user asks. When the push is rejected or a pre-push hook fails, it SHALL stop, keep the commits local, and report the cause.

#### Scenario: Remote has new commits
- **WHEN** the push is rejected because the remote branch has commits the local branch lacks
- **THEN** the skill does not pull, rebase, or force-push; it reports the rejection, keeps the commits, and suggests bringing the remote changes in (for example with `ep-sync`) before pushing again

#### Scenario: Pre-push hook fails
- **WHEN** a pre-push hook rejects the push
- **THEN** the skill reports the hook output, keeps the commits local, and does not retry with `--no-verify`

### Requirement: Default branch push is gated
When the current branch is the repository's default branch, the skill SHALL ask before pushing, even when it was told to just commit, and SHALL push nothing unless the user confirms.

#### Scenario: Committing on the default branch
- **WHEN** the skill has committed on `main`, the default branch, without `--no-push`
- **THEN** it asks whether to push `main` and, if the user declines, reports the commits as local

### Requirement: No-push mode
With `--no-push`, or when the user or a calling skill says to commit without pushing, the skill SHALL create and verify its commits as usual, push nothing, and report the commits as local.

#### Scenario: Caller keeps the branch local
- **WHEN** `ep-orchestrate` invokes the skill with `--no-push` and an intended single commit
- **THEN** the skill makes that commit, runs no `git push`, and the remote is unchanged

#### Scenario: User asks for commits only
- **WHEN** the user asks to commit but not push
- **THEN** the skill behaves as with `--no-push`

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents.

#### Scenario: Agent without subagents and large diff
- **WHEN** the host agent has no subagent capability and the diff is large
- **THEN** the skill analyzes the diff sequentially and still produces the commit plan
