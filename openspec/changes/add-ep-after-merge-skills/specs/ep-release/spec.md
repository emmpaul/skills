# Spec Delta

## Purpose

Prepares and publishes a release from the default branch: picks the next semantic version from Conventional Commits, drafts release notes and changelog entries, and creates the tag and GitHub release only after the user confirms.

## ADDED Requirements

### Requirement: Release range
The skill SHALL compute the release from the commits on the default branch since the latest semantic version tag, or since the first commit when no such tag exists.

#### Scenario: Previous tag exists
- **WHEN** the latest tag is `v1.4.2`
- **THEN** the release covers commits after `v1.4.2` up to the default branch head

#### Scenario: Nothing to release
- **WHEN** there are no commits since the latest tag
- **THEN** the skill reports that there is nothing to release and stops

#### Scenario: Not on an up-to-date default branch
- **WHEN** the local default branch is behind or diverged from its remote, or the working tree is dirty
- **THEN** the skill stops and tells the user what to fix before releasing

### Requirement: Version bump from Conventional Commits
The skill SHALL propose a major bump when any commit is breaking, a minor bump when any commit is a `feat`, and a patch bump otherwise. For versions below 1.0.0, breaking changes bump the minor version and features bump the patch version.

#### Scenario: Breaking change
- **WHEN** a commit in the range has a `!` after its type or a `BREAKING CHANGE:` footer and the current version is `1.4.2`
- **THEN** the proposed version is `2.0.0`

#### Scenario: Feature before 1.0
- **WHEN** the highest-impact commit is a `feat` and the current version is `0.3.1`
- **THEN** the proposed version is `0.3.2`

#### Scenario: First release
- **WHEN** no version tag exists
- **THEN** the skill proposes `0.1.0` and lets the user choose another version

#### Scenario: User override
- **WHEN** the user passes an explicit version or bump level
- **THEN** the skill uses it, and warns if it is lower than the computed bump

#### Scenario: Non-conventional commits
- **WHEN** some commits in the range do not follow Conventional Commits
- **THEN** the skill lists them under an "Other" group, treats them as patch-level, and tells the user

### Requirement: Release notes grouped by type
The draft notes SHALL group commits under breaking changes, features, fixes, and other changes, and SHALL link each entry to its PR when one exists.

#### Scenario: Grouped notes
- **WHEN** the range has a breaking change, two features, and a fix
- **THEN** the notes list the breaking change first, then the features, then the fix, each with its PR link

### Requirement: Capabilities in release notes
With OpenSpec, the notes SHALL also list the capabilities added or modified by changes archived since the previous tag, with each change's one-line purpose.

#### Scenario: Archived changes in range
- **WHEN** two OpenSpec changes were archived since the previous tag
- **THEN** the notes include a section naming each change and the capabilities it added or modified

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the notes contain only the commit-type groups and do not mention OpenSpec

### Requirement: Changelog follows existing format
When the repository has a `CHANGELOG.md`, the skill SHALL add the new release entry in that file's existing heading and section style, and SHALL NOT create a changelog file the repository does not have.

#### Scenario: Keep a Changelog file
- **WHEN** `CHANGELOG.md` uses Keep a Changelog headings with an `Unreleased` section
- **THEN** the skill moves the unreleased entries under the new version heading and adds the commit-derived entries in the same style

#### Scenario: No changelog file
- **WHEN** the repository has no `CHANGELOG.md`
- **THEN** the release notes appear only in the GitHub release

### Requirement: Confirmed publication
The skill SHALL show the proposed version, notes, and changelog diff, and SHALL push a tag or create a GitHub release only after the user confirms that draft.

#### Scenario: Draft declined
- **WHEN** the user declines or does not confirm the draft
- **THEN** no tag, release, commit, or push is made

#### Scenario: Release without changelog
- **WHEN** the user confirms and the repository has no `CHANGELOG.md`
- **THEN** the skill creates an annotated tag on the default branch head, pushes the tag, and creates the GitHub release with the notes

#### Scenario: Release with changelog
- **WHEN** the user confirms and the changelog needs a commit
- **THEN** the skill commits the changelog on a release branch and opens a PR, without pushing to the default branch, and tells the user to re-run the skill to tag after the PR merges

#### Scenario: Tag already exists
- **WHEN** the chosen version's tag already exists locally or on the remote
- **THEN** the skill stops without moving or overwriting the tag

### Requirement: No attribution
Release notes, changelog entries, tag messages, and commits SHALL carry no model or tool attribution.

#### Scenario: Release body
- **WHEN** the GitHub release is created
- **THEN** its body has no "Generated with" footer or model signature

### Requirement: Machine-readable result
The skill SHALL end with an `ep-release-summary` block reporting the outcome, previous and new version, bump level, tag, release URL, and changelog status.

#### Scenario: Summary after publication
- **WHEN** the release is published
- **THEN** the summary includes the tag and the release URL

### Requirement: Works without subagents
The skill SHALL complete its full behavior sequentially in agents that cannot spawn subagents.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** commit classification and note drafting run inline with the same output
