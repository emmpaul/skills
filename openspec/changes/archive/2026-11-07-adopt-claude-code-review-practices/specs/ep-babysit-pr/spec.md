# Spec Delta

## MODIFIED Requirements

### Requirement: Bounded review rounds
The skill SHALL run at most 3 review rounds, where a round is an `ep-review` pass on the PR, fixes for its findings, a push, and green required checks. The first round SHALL review the full PR; later rounds SHALL review only the commits since the last reviewed head and pass the earlier findings as known findings, unless a base sync landed since that head.

#### Scenario: Round limit reached
- **WHEN** 3 rounds complete and the merge gate is not met
- **THEN** the skill stops, posts a summary comment on the PR that asks the author to step back and reconsider the approach, and notifies the user

#### Scenario: Second round is diff-only
- **WHEN** round 1 ran on head `A`, fixes were pushed to head `B`, and no base sync happened in between
- **THEN** round 2 runs `ep-review <n> --since A --known <round 1 findings>`

#### Scenario: Sync between rounds
- **WHEN** a base sync was pushed after the last reviewed head
- **THEN** the next round reviews the full PR, with the earlier findings still passed as known findings

#### Scenario: Pre-existing findings
- **WHEN** a review round reports pre-existing findings
- **THEN** the skill does not fix them, lists them in its status report and final report, and they do not affect the score

### Requirement: Merge decision defers to GitHub
The skill SHALL merge only when the score is at least 85, hard gates pass, the risk gate passes, and GitHub reports the PR as mergeable without bypass; it SHALL wait while GitHub reports the PR as blocked and SHALL stop when the merge state is unknown after retries.

#### Scenario: Protection requires approval
- **WHEN** score is 90 and GitHub reports the PR blocked pending approval
- **THEN** the skill waits, notifies the user, and merges once GitHub reports it mergeable

#### Scenario: No protection
- **WHEN** score is 88, hard gates pass, the risk gate passes, GitHub reports the PR mergeable, and the PR is in no native stack
- **THEN** the skill merges using the repository's default merge method and deletes the branch

#### Scenario: Unknown merge state
- **WHEN** GitHub reports the merge state as unknown after several retries
- **THEN** the skill stops without merging and reports to the user

#### Scenario: Branch behind base
- **WHEN** GitHub reports the branch behind its base, or in conflict with it
- **THEN** the skill syncs the branch with its base through `ep-sync` in merge mode (or its condensed inline steps when `ep-sync` is not installed), runs the merge audit, pushes with a plain push, waits for checks, and re-evaluates

#### Scenario: Audit finds needed updates
- **WHEN** the sync's merge audit reports needs-update interactions
- **THEN** the skill applies the adaptations as a fix round, in commits separate from the merge commit, before re-evaluating the merge

#### Scenario: Audit needs a decision
- **WHEN** the sync stops on an incompatible conflict or an ambiguous adaptation
- **THEN** the skill does not push the sync, notifies the user with the options, and stops until the user decides

#### Scenario: Review items from the audit
- **WHEN** the merge audit reports review-class interactions
- **THEN** the skill lists them in its next status report and the next review round covers them

## ADDED Requirements

### Requirement: Risk-tier merge gate
The skill SHALL read the risk tier from the latest `ep-review` summary for the merge head. Low risk SHALL need no extra approval. Medium risk SHALL need the user's explicit yes in the session for that exact head sha. High risk SHALL need that yes and an approving GitHub review of that head from a human other than the PR author.

#### Scenario: Low risk
- **WHEN** the latest review reports `risk: low` and every other merge condition holds
- **THEN** the skill merges without asking

#### Scenario: Medium risk asks
- **WHEN** the latest review reports `risk: medium` and every other merge condition holds
- **THEN** the skill shows the risk reasons, score, and head sha, and merges only after the user says yes for that head

#### Scenario: New commits after a yes
- **WHEN** the user said yes for head `A` and a fix is pushed, making the head `B`
- **THEN** the earlier yes no longer counts and the skill asks again for `B`

#### Scenario: High risk without a human approval
- **WHEN** the latest review reports `risk: high` and no human other than the PR author has approved the current head
- **THEN** the skill does not merge, notifies the user once that a human approval is needed, and waits

#### Scenario: Bot approval
- **WHEN** the only approving review on a high-risk PR comes from an account of type Bot or an app
- **THEN** the approval is not counted and the skill keeps waiting

#### Scenario: Unattended run on medium risk
- **WHEN** the skill runs from a schedule or loop with no user present and the PR is medium risk
- **THEN** it does not merge, notifies the user once, and asks on the next run where the user is present

#### Scenario: Review summary without a tier
- **WHEN** the latest review summary has no `risk:` line (an older `ep-review`)
- **THEN** the skill treats the PR as medium risk
