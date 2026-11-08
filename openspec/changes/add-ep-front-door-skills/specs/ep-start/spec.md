# Spec Delta

## Purpose

Starts a unit of work from an issue or a description: a fresh base, a conventional branch name, an optional OpenSpec change, and an issue link the later ep-* skills can read.

## ADDED Requirements

### Requirement: Work input
The skill SHALL accept a GitHub issue number or URL, or a free-text description of the work.

#### Scenario: From issue
- **WHEN** the user runs `ep-start 17`
- **THEN** the skill reads issue #17's title and labels to name the work

#### Scenario: From description
- **WHEN** the user runs `ep-start "add CSV export"`
- **THEN** the skill names the work from the description and links no issue

### Requirement: Branch naming
The skill SHALL name the branch `<type>/<issue>-<slug>`, or `<type>/<slug>` without an issue, where type is a Conventional Commit type inferred from the issue labels or description and slug is a short kebab-case summary.

#### Scenario: Bug issue
- **WHEN** issue #17 is labelled as a bug and titled "Login fails with SSO"
- **THEN** the branch is named `fix/17-login-fails-with-sso` or a shorter slug of it

#### Scenario: Branch already exists
- **WHEN** a local or remote branch with that name exists
- **THEN** the skill asks whether to switch to it or choose another name, and does not overwrite it

### Requirement: Fresh base
The skill SHALL fetch the remote and create the branch from the up-to-date remote default branch, or from a base the user names.

#### Scenario: Stale local main
- **WHEN** local `main` is behind `origin/main`
- **THEN** the new branch starts at `origin/main`, not at local `main`

### Requirement: Dirty tree protection
The skill SHALL NOT create or switch branches on a dirty working tree unless the user confirms stashing, and SHALL report the stash it created.

#### Scenario: Uncommitted changes
- **WHEN** the working tree has uncommitted changes
- **THEN** the skill stops and asks whether to stash them, carry them to the new branch, or abort

### Requirement: Optional OpenSpec change
When the user passes `--change` or confirms the offer, the skill SHALL create an OpenSpec change named after the work with `openspec new change`, so later skills detect it as active.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill does not offer or create a change and does not mention OpenSpec

#### Scenario: Change requested
- **WHEN** the user runs `ep-start 17 --change` in an OpenSpec repo
- **THEN** a change is created with the CLI and its name is reported

#### Scenario: Change marked with its issue
- **WHEN** the user runs `ep-start 17 --change` in an OpenSpec repo
- **THEN** the change is named by the same rules `ep-issue-to-change` uses, and its `README.md` carries the marker `From #17:`, so `ep-issue-to-change 17` finds it

### Requirement: Issue link recorded
The skill SHALL record the branch's issue link locally in `branch.<name>.ep-issue`, which `ep-open-pr` reads: the issue number when started from an issue, and `none` when started from a description, so `ep-open-pr` never reads an issue number out of a description branch's name. A description run that switches to an existing branch whose key is already set SHALL keep that value.

#### Scenario: PR after start
- **WHEN** work started with `ep-start 17` reaches `ep-open-pr`
- **THEN** the issue number is available to the PR body

#### Scenario: Description run
- **WHEN** the user runs `ep-start "add CSV export"`
- **THEN** the skill writes `branch.feat/add-csv-export.ep-issue=none` to `.git/config`, and nothing is committed or pushed

#### Scenario: Description run on a branch with a key
- **WHEN** a description run switches to an existing branch whose `ep-issue` key is `17`
- **THEN** the key stays `17`, and the summary reports `issue: 17`

### Requirement: No push by default
The skill SHALL NOT push or write to GitHub unless the user passes `--push` or confirms; when pushing it SHALL use a plain push that sets upstream.

#### Scenario: Default run
- **WHEN** the user runs `ep-start` without `--push`
- **THEN** the branch exists only locally

### Requirement: Summary block
The skill SHALL end with an `ep-start-summary` block giving the outcome, branch, base commit, issue number or null, OpenSpec change name or null, and stash reference or null.

#### Scenario: Branch created
- **WHEN** the skill creates `fix/17-login-fails-with-sso`
- **THEN** the block reports `outcome: started`, the branch name, and `issue: 17`
