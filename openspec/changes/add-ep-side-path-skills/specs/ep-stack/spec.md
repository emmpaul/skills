# Spec Delta

## Purpose

Manages a stack of dependent pull requests built from one branch: splits the branch, opens the PRs, retargets them as parents merge, and keeps the stack in sync.

## ADDED Requirements

### Requirement: Split plan
The skill SHALL propose a split of the current branch's commits into an ordered list of stack branches. Each branch builds on the previous one, and the skill SHALL wait for the user to approve or edit the plan before creating anything.

#### Scenario: Plan shown first
- **WHEN** the user runs `ep-stack split`
- **THEN** the skill shows each proposed branch, its commits, and its base, and creates nothing until the user approves

#### Scenario: Commits not separable
- **WHEN** a commit mixes changes that belong in different stack layers
- **THEN** the skill says so and asks the user how to split it, instead of rewriting it silently

#### Scenario: OpenSpec grouping
- **WHEN** the repository has an OpenSpec root and the commits map to OpenSpec changes or task groups
- **THEN** the proposed layers follow those boundaries

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** layers follow commit scopes and file areas, and OpenSpec is not mentioned

### Requirement: Stack creation
After approval, the skill SHALL create the stack branches, push them without force, and open one PR per layer whose base is the previous layer's branch. PRs follow `ep-open-pr` conventions, with no attribution.

#### Scenario: PRs opened
- **WHEN** a 3-layer plan is approved
- **THEN** three PRs exist, the first based on the base branch and each other based on the previous layer's branch

#### Scenario: Stack navigation in bodies
- **WHEN** stack PRs are opened
- **THEN** each PR body lists the whole stack in order and marks the current PR

### Requirement: Retarget on parent merge
When a layer's PR merges, the skill SHALL change the base of the next layer's PR to the merged PR's base, sync that layer, and update the stack lists in the PR bodies.

#### Scenario: Bottom PR merged
- **WHEN** the first PR of the stack is merged into `main`
- **THEN** the second PR's base is changed to `main` and its branch is synced with `main`

### Requirement: Stack sync
The skill SHALL sync every layer with the layer below it, from the bottom up, using merges by default. It SHALL use rebase only when the user asks and confirms a force-with-lease push.

#### Scenario: Change in lower layer
- **WHEN** a commit is added to layer 1
- **THEN** `ep-stack sync` merges layer 1 into layer 2, then layer 2 into layer 3, and pushes each without force

#### Scenario: Sync with audit
- **WHEN** `ep-sync` is installed
- **THEN** each layer sync runs through it so its merge audit applies to each layer

### Requirement: Outward action gate
The skill SHALL confirm with the user before creating PRs, changing PR bases, or pushing more than one branch.

#### Scenario: Retarget confirmation
- **WHEN** the skill is about to change the base of open PRs
- **THEN** it lists the PRs and new bases and waits for confirmation

### Requirement: Stack status and summary block
The skill SHALL show the stack's state (each layer, its PR, checks, review state, and whether it is behind its parent). It SHALL end with an `ep-stack-summary` block listing each layer's branch, PR number, base, and state.

#### Scenario: Status view
- **WHEN** the user runs `ep-stack status`
- **THEN** each layer is listed in order with its PR and state, and nothing is changed
