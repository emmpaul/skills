# Spec Delta

## MODIFIED Requirements

### Requirement: Frequent, traceable commits
The skill SHALL commit in small steps following `ep-commit-and-push` conventions, with no model or tool attribution. It SHALL commit newly written planning artifacts on their own, each task on its own once verified, together with its `tasks.md` tick, and each review fix on its own. It SHALL NOT batch several tasks or a whole group into one commit. Every commit made through `ep-commit-and-push` SHALL use its `--no-push` mode. A phase SHALL commit a file new to history with a secret-like name only on the user's yes by name, asked through a `needs input` blocker.

#### Scenario: Planning artifacts committed
- **WHEN** the skill has written a new change's artifacts and before it edits any code
- **THEN** it commits them as one `docs(<change>)` commit

#### Scenario: One commit per task
- **WHEN** a group of three tasks completes
- **THEN** the branch has three new commits, each scoped to the change, each naming its task id (for example `2.1`) in the body, and each including that task's tick in `tasks.md`

#### Scenario: Task with no file changes
- **WHEN** a task's work produces no file change apart from its tick (for example a pure verification task)
- **THEN** the tick is committed on its own, or with the next task's commit, and the commit body names both task ids

#### Scenario: Progress is visible mid-run
- **WHEN** the run is interrupted during group 2
- **THEN** `git log` shows one commit per finished task, and the unfinished task's work is the only uncommitted change

#### Scenario: Commits through ep-commit-and-push stay local
- **WHEN** a phase commits through `ep-commit-and-push`
- **THEN** it passes `--no-push`, and the branch's remote is unchanged after the commit

#### Scenario: Secret-like file in a phase commit
- **WHEN** a phase's commit would add a new file with a secret-like name (as `ep-commit-and-push` lists them) and no answer says yes to it by name
- **THEN** the phase commits nothing for that commit and ends with a `needs input` blocker naming the file, through `ep-commit-and-push` and the condensed fallback alike

#### Scenario: ep-commit-and-push not installed
- **WHEN** a phase commits and `ep-commit-and-push` is not installed
- **THEN** the phase follows the condensed commit steps bundled in the skill's folder, which push nothing
