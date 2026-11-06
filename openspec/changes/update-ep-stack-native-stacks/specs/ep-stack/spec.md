## ADDED Requirements

### Requirement: Native stack detection
Before an action that creates, reads, or changes a stack, the skill SHALL find out whether the repository supports GitHub native stacked pull requests. It SHALL use native mode only when that check succeeds and the user did not pass `--no-native`. In every other case it SHALL use plain-branch mode, which keeps the existing behaviour.

#### Scenario: Native stacks available
- **WHEN** the repository's stacks endpoint answers successfully
- **THEN** the skill runs in native mode and says so in its plan or report

#### Scenario: Native stacks unavailable
- **WHEN** the stacks endpoint returns not found or another error, or `gh` cannot reach it
- **THEN** the skill runs in plain-branch mode, tells the user why, and otherwise behaves as before this change

#### Scenario: User opts out
- **WHEN** the user passes `--no-native`
- **THEN** the skill runs in plain-branch mode even if native stacks are available

### Requirement: Native stack linking on split
In native mode, after the approved layers' PRs are open, the skill SHALL link them bottom-up as one GitHub stack. The approval plan SHALL state that a GitHub stack will be created. When linking fails, the skill SHALL leave the PRs as a plain stack and warn.

#### Scenario: Stack linked
- **WHEN** a 3-layer plan is approved in native mode
- **THEN** three PRs are opened as in plain mode and then linked as one GitHub stack in layer order, and the report gives the stack number

#### Scenario: Linking rejected
- **WHEN** GitHub rejects the stack creation
- **THEN** the PRs and their body stack sections remain, the skill reports the error, and the summary shows `mode: branches`

### Requirement: Link an existing stack
The skill SHALL offer a `link` subcommand. It links a plain stack made by this skill as a native GitHub stack, after the user confirms the PRs and their order. It SHALL refuse when the base chain is broken, when a layer is closed, or when a PR comes from another repository or another author.

#### Scenario: Plain stack linked
- **WHEN** the user runs `ep-stack link` on a plain stack of three open PRs whose bases chain correctly, and confirms
- **THEN** the three PRs are linked as one GitHub stack in order

#### Scenario: Broken chain
- **WHEN** a layer's base is not the previous layer's head branch
- **THEN** the skill reports the mismatch and links nothing

### Requirement: Refresh layers rewritten by GitHub
When GitHub has rewritten a layer's remote branch (for example its cascading rebase after a lower PR merged), the skill SHALL reset the local branch to the remote copy only when the local branch has no commits of its own. Otherwise it SHALL stop for that layer and the layers above it, and SHALL push nothing.

#### Scenario: Clean local branch
- **WHEN** GitHub rebased layer 2 after layer 1 merged, and local layer 2 has no commits missing from the remote
- **THEN** the local branch is moved to the remote copy and the skill continues

#### Scenario: Local-only commits
- **WHEN** local layer 2 has a commit that the rewritten remote branch does not contain
- **THEN** the skill lists that commit and stops, pushing nothing for layer 2 or the layers above it

## MODIFIED Requirements

### Requirement: Stack creation
After approval, the skill SHALL create the stack branches, push them without force, and open one PR per layer whose base is the previous layer's branch. PRs follow `ep-open-pr` conventions, with no attribution.

#### Scenario: PRs opened
- **WHEN** a 3-layer plan is approved
- **THEN** three PRs exist, the first based on the base branch and each other based on the previous layer's branch

#### Scenario: Stack navigation in bodies
- **WHEN** stack PRs are opened, in native or plain-branch mode
- **THEN** each PR body lists the whole stack in order and marks the current PR

### Requirement: Retarget on parent merge
When a layer's PR merges, the skill SHALL make sure the next layer's PR targets the merged PR's base and is up to date, and update the stack lists in the PR bodies. In plain-branch mode it changes the base and syncs the layer. In native mode it checks the retarget that GitHub did, refreshes the local branches, and changes no base itself, unless GitHub did not retarget and the user confirms the plain retarget.

#### Scenario: Bottom PR merged
- **WHEN** the first PR of a plain-branch stack is merged into `main`
- **THEN** the second PR's base is changed to `main` and its branch is synced with `main`

#### Scenario: Bottom PR merged in a native stack
- **WHEN** the first PR of a native stack is merged into `main` and GitHub has retargeted the second PR to `main`
- **THEN** the skill changes no PR base, refreshes the local layer branches, updates the body stack sections, and reports the second PR's base as `main`

#### Scenario: GitHub did not retarget
- **WHEN** in native mode the parent PR is merged but the next PR still targets the merged branch
- **THEN** the skill reports this and changes the base only after the user confirms

### Requirement: Stack sync
The skill SHALL sync every layer with the layer below it, from the bottom up, using merges by default, in native and plain-branch mode. It SHALL use rebase only when the user asks and confirms a force-with-lease push.

#### Scenario: Change in lower layer
- **WHEN** a commit is added to layer 1
- **THEN** `ep-stack sync` merges layer 1 into layer 2, then layer 2 into layer 3, and pushes each without force

#### Scenario: Sync with audit
- **WHEN** `ep-sync` is installed
- **THEN** each layer sync runs through it so its merge audit applies to each layer

### Requirement: Outward action gate
The skill SHALL confirm with the user before creating PRs, creating or extending a GitHub stack, changing PR bases, or pushing more than one branch.

#### Scenario: Retarget confirmation
- **WHEN** the skill is about to change the base of open PRs
- **THEN** it lists the PRs and new bases and waits for confirmation

#### Scenario: Link confirmation
- **WHEN** the skill is about to link PRs as a GitHub stack
- **THEN** it lists the PRs in stack order and waits for confirmation

### Requirement: Stack status and summary block
The skill SHALL show the stack's state (each layer, its PR, checks, review state, and whether it is behind its parent), the mode, and in native mode the GitHub stack number. It SHALL end with an `ep-stack-summary` block listing the mode, the stack number, and each layer's branch, PR number, base, and state.

#### Scenario: Status view
- **WHEN** the user runs `ep-stack status`
- **THEN** each layer is listed in order with its PR and state, and nothing is changed

#### Scenario: Native status source
- **WHEN** the current PR belongs to a native GitHub stack
- **THEN** the layer order comes from the GitHub stack, a disagreement with the body stack section is reported, and the summary shows `mode: native` and the stack number

#### Scenario: Plain status source
- **WHEN** the current PR belongs to no native stack
- **THEN** the stack is rebuilt from the PR body sections as before, and the summary shows `mode: branches` and `stack: none`
