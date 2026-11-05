# Spec Delta

## Purpose

Gives the user a read-only digest of their open pull requests, sorted by what needs their attention, for one repository or across GitHub, once or on a recurring schedule.

## ADDED Requirements

### Requirement: PR scope
The skill SHALL include open PRs the user authored and open PRs where the user's review is requested, in the current repository by default or across every repository the user can see with `--all`.

#### Scenario: Current repository
- **WHEN** the user runs `ep-pr-digest` inside a repository
- **THEN** the digest lists only that repository's open PRs authored by or awaiting review from the user

#### Scenario: Across repositories
- **WHEN** the user runs `ep-pr-digest --all`
- **THEN** the digest includes matching PRs from every repository, each labelled with its repository

#### Scenario: Outside a repository
- **WHEN** the skill runs outside a git repository without `--all`
- **THEN** it behaves as `--all` and says so

### Requirement: Attention buckets
The skill SHALL place each PR in exactly one bucket, checked in this order: ready to merge, blocked by CI, waiting on me, waiting on others, stale. Each bucket SHALL be ordered by last update, oldest first.

#### Scenario: Ready to merge
- **WHEN** a PR the user authored is approved, has green required checks, and GitHub reports it mergeable
- **THEN** it is listed under ready to merge

#### Scenario: Blocked by CI
- **WHEN** a PR the user authored has a failing required check
- **THEN** it is listed under blocked by CI with the failing check names

#### Scenario: Waiting on me
- **WHEN** the user's review is requested on a PR, or a reviewer has commented or requested changes on the user's PR since the user's last push or reply
- **THEN** the PR is listed under waiting on me

#### Scenario: Waiting on others
- **WHEN** a PR the user authored has green checks and awaits review or approval from someone else
- **THEN** it is listed under waiting on others

#### Scenario: Stale
- **WHEN** a PR in no earlier bucket has had no activity for longer than the stale threshold (7 days by default, changed with `--stale <days>`)
- **THEN** it is listed under stale with its age

### Requirement: Read-only
The skill SHALL NOT post, push, merge, label, or change any PR or repository.

#### Scenario: Ready PR listed
- **WHEN** a PR is ready to merge
- **THEN** the digest suggests the next step (for example `ep-babysit-pr <n>`) but takes no action

### Requirement: Empty digest
When no PR matches, the skill SHALL say so in one line.

#### Scenario: Nothing open
- **WHEN** the user has no matching open PRs
- **THEN** the digest reports that nothing needs attention

### Requirement: Optional recurrence
The skill SHALL run once by default. When the user asks for a recurring digest and the host agent supports loops or scheduled runs, it SHALL use that feature. Otherwise it SHALL run once and say that recurrence is unavailable.

#### Scenario: Recurring in a capable host
- **WHEN** the user asks for a weekday-morning digest in a host with scheduling
- **THEN** the skill sets up the recurring run through the host's scheduler and confirms the schedule

#### Scenario: Host without scheduling
- **WHEN** the user asks for a recurring digest in a host without loops or scheduling
- **THEN** the skill produces one digest and states that recurrence is not available in this agent

### Requirement: Changes since last digest
In recurring runs, the digest SHALL mark PRs that are new or that changed bucket since the previous digest of the same scope.

#### Scenario: PR became ready
- **WHEN** a PR was blocked by CI in the previous digest and is now ready to merge
- **THEN** the digest marks it as changed

### Requirement: Works without OpenSpec
The skill's behavior SHALL NOT depend on OpenSpec.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the digest is the same and does not mention OpenSpec

### Requirement: Summary for callers
The digest SHALL end with a summary block giving the PR count in each bucket.

#### Scenario: Summary counts
- **WHEN** the digest lists two ready PRs and one stale PR
- **THEN** the summary block reports ready=2 and stale=1, with zero for the other buckets
