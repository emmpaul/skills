# ep-sync Specification

## Purpose
Brings the base branch into the current branch and audits how the incoming base changes interact with the branch's own changes, so the branch stays correct and not merely conflict-free.

## Requirements

### Requirement: Base and target resolution
The skill SHALL sync the current branch with its base. The base is the PR base when the branch has an open PR, otherwise the repository default branch, unless the user names one. The skill SHALL fetch the base before comparing.

#### Scenario: Branch with open PR
- **WHEN** the current branch has an open PR targeting `develop`
- **THEN** the skill fetches and syncs with `origin/develop`

#### Scenario: Already up to date
- **WHEN** the base has no commits that the branch lacks
- **THEN** the skill reports the branch is up to date and changes nothing

#### Scenario: Dirty working tree
- **WHEN** the working tree has uncommitted changes
- **THEN** the skill stops and asks the user to commit or stash before syncing

### Requirement: Merge by default
The skill SHALL integrate the base with a merge commit by default. It SHALL rebase only when the user invokes it directly and asks for rebase, and only when the branch is unpushed or the user explicitly confirms a `--force-with-lease` push.

#### Scenario: Default mode
- **WHEN** the user runs `ep-sync` with no mode
- **THEN** the base is merged into the branch with a merge commit and no history is rewritten

#### Scenario: Rebase on pushed branch
- **WHEN** the user asks for rebase and the branch has been pushed
- **THEN** the skill asks for explicit confirmation of a force-with-lease push and does not rebase without it

#### Scenario: Called by another skill
- **WHEN** another skill invokes `ep-sync` (for example `ep-babysit-pr`)
- **THEN** merge mode is used and rebase is not offered

### Requirement: Textual conflict resolution
The skill SHALL resolve textual conflicts that preserve the intent of both sides. It SHALL stop and ask the user when the two sides make incompatible decisions.

#### Scenario: Compatible conflict
- **WHEN** base and branch both add different entries to the same list
- **THEN** the skill keeps both entries and completes the merge

#### Scenario: Incompatible conflict
- **WHEN** base and branch change the same logic in contradictory ways
- **THEN** the skill shows both versions, explains the conflict, and waits for the user's decision

### Requirement: Merge audit of semantic interactions
After integrating the base, the skill SHALL audit the incoming base commits against the branch's own changes and find semantic interactions, whether or not textual conflicts occurred.

#### Scenario: Renamed symbol without conflict
- **WHEN** base renames a function that the branch calls in a file base did not touch
- **THEN** the audit reports the interaction even though the merge had no conflicts

#### Scenario: Changed signature
- **WHEN** base adds a required parameter to a function that the branch calls
- **THEN** the audit reports each branch call site that is affected

#### Scenario: Changed behaviour
- **WHEN** base changes the return value or side effects of code that the branch depends on
- **THEN** the audit reports the dependency and the behaviour change

#### Scenario: Contract change
- **WHEN** base changes a schema, migration, configuration key, or API contract that the branch reads or writes
- **THEN** the audit reports the interaction

#### Scenario: New base caller of modified code
- **WHEN** base adds a call site for code whose behaviour the branch changed
- **THEN** the audit reports the new caller as affected by the branch

#### Scenario: Changed tests over branch code
- **WHEN** base changes or adds tests that cover code the branch modified
- **THEN** the audit reports the tests so they are run and checked

### Requirement: OpenSpec overlap in the audit
When the repository has an OpenSpec root and the branch implements an active change, the audit SHALL report base commits that change or archive specs overlapping the capabilities of that change.

#### Scenario: Overlapping spec changed in base
- **WHEN** base archives a change that modifies a capability the branch's active change also modifies
- **THEN** the audit reports the overlap and names the requirements on both sides

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the audit skips spec overlap, does not mention OpenSpec, and the other checks run normally

### Requirement: Interaction classification
The skill SHALL classify each audit interaction as needs-update (the branch is wrong without a change), review (it may matter and a person should look), or no-impact (checked and harmless), and SHALL give the evidence for each.

#### Scenario: Classified finding
- **WHEN** the audit finds an interaction
- **THEN** the report gives its class, the base commit, the affected branch location, and the reason

### Requirement: Branch adaptation
For each needs-update interaction, the skill SHALL update the branch's code so it is correct with the new base. It SHALL commit each adaptation following `ep-commit` conventions as a commit separate from the merge commit.

#### Scenario: Call sites updated
- **WHEN** base renamed a function that the branch calls
- **THEN** the skill updates the branch's call sites and commits that in its own commit after the merge commit

#### Scenario: Ambiguous adaptation
- **WHEN** a needs-update interaction has more than one reasonable fix with different behaviour
- **THEN** the skill does not choose one, presents the options, and waits for the user

### Requirement: Verification after sync
After merging and adapting, the skill SHALL run the repository's tests, or the subset relevant to the interactions when the full suite is impractical, and report the results. It SHALL NOT report a successful sync while those tests fail.

#### Scenario: Tests fail after adaptation
- **WHEN** relevant tests fail after the merge and adaptations
- **THEN** the skill reports the failures and an outcome of `needs-attention` instead of `synced`

### Requirement: Push gate
The skill SHALL push the synced branch only after the user confirms, or when invoked by a caller that owns pushing. It SHALL never push with `--force` and SHALL use `--force-with-lease` only for a confirmed rebase.

#### Scenario: Direct invocation
- **WHEN** the user runs `ep-sync` directly and the sync succeeds
- **THEN** the skill asks before pushing

### Requirement: Audit report and summary block
The skill SHALL print an audit table of every interaction with its class and resolution. It SHALL end with an `ep-sync-summary` block that gives the outcome, head sha, mode, conflict count, and counts per class.

#### Scenario: Caller parses result
- **WHEN** `ep-babysit-pr` invokes `ep-sync`
- **THEN** it receives the outcome, the count of needs-update items still unresolved, and the count of review items

#### Scenario: Nothing found
- **WHEN** the audit finds no interactions
- **THEN** the report states that explicitly and the summary shows zero for each class

### Requirement: Parallel audit with sequential fallback
When the host agent can spawn subagents, the skill SHALL audit interaction clusters in parallel. Otherwise it SHALL audit them sequentially, producing the same report.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** each cluster is audited inline in sequence and the report has the same structure

### Requirement: No attribution
Commits and pushes made by the skill SHALL carry no model or tool attribution.

#### Scenario: Merge commit message
- **WHEN** the skill creates the merge commit or an adaptation commit
- **THEN** the message has no `Co-Authored-By` model trailer and no "Generated with" line
