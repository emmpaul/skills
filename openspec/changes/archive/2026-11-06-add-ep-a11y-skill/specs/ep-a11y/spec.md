# Spec Delta

## Purpose

Audits UI changes for accessibility against WCAG 2.2 and reports verified, criterion-cited findings. It can fix them or post them to a PR, and it bundles WCAG references that are regenerated from W3C's published source and checked for drift.

## ADDED Requirements

### Requirement: Audit targets
The skill SHALL accept as target the uncommitted diff (default), a branch compared to its base, a GitHub PR number, or one or more explicit paths, and SHALL audit only UI-relevant files within that target (markup, components, templates, and styles).

#### Scenario: Default target
- **WHEN** the user invokes `ep-a11y` with no target
- **THEN** the skill audits the uncommitted diff, or the branch versus its base if the tree is clean

#### Scenario: PR target
- **WHEN** the user invokes `ep-a11y 42`
- **THEN** the skill audits the UI-relevant files changed in PR #42

#### Scenario: Path target
- **WHEN** the user invokes `ep-a11y src/components/Modal.tsx`
- **THEN** the skill audits that whole file, not only its changed lines

#### Scenario: No UI files
- **WHEN** the target contains no UI-relevant files
- **THEN** the skill reports "nothing to audit" and stops without writing anything

### Requirement: Conformance level
The skill SHALL audit against WCAG 2.2 Level AA (A and AA criteria) by default, and SHALL accept `--level A`, `--level AA`, or `--level AAA` to set the highest level checked.

#### Scenario: Default level
- **WHEN** the user runs `ep-a11y` without `--level`
- **THEN** findings cite only Level A and AA criteria, and the report states the level as WCAG 2.2 AA

#### Scenario: AAA requested
- **WHEN** the user runs `ep-a11y --level AAA`
- **THEN** Level AAA criteria are also checked and can produce findings

#### Scenario: Obsolete criterion
- **WHEN** a pattern would only violate 4.1.1 Parsing, which WCAG 2.2 marks obsolete
- **THEN** the skill does not report it as a WCAG finding

### Requirement: Criterion citations from bundled references
Every finding SHALL cite a success criterion by number, name, and level, taken from the bundled references. The skill SHALL NOT cite a criterion that is absent from them, and SHALL load only the criterion files it needs, not the whole set.

#### Scenario: Exact citation
- **WHEN** the skill reports a button with no accessible name
- **THEN** the finding cites "4.1.2 Name, Role, Value (A)" exactly as the bundled index records it and links its Understanding document

#### Scenario: Unknown criterion rejected
- **WHEN** a candidate finding cites a number that the bundled index does not contain
- **THEN** the skill corrects the citation from the index, or drops the finding

### Requirement: Verified findings
Each candidate finding SHALL pass a verification step that tries to disprove it, for example by finding a name supplied elsewhere, an element that is hidden from assistive technology, or a parent component that handles the issue. Each reported finding SHALL include the criterion, file and line, severity (critical, major, minor), a scenario naming the affected users and what blocks them, evidence, and a proposed fix.

#### Scenario: False positive dropped
- **WHEN** an icon button looks unlabelled but receives `aria-label` from its wrapper component
- **THEN** the finding is not reported

#### Scenario: Severity reflects impact
- **WHEN** a custom control cannot be reached or operated by keyboard
- **THEN** the finding is critical, regardless of the criterion's level

### Requirement: Manual-check list and no conformance claim
The report SHALL list, as "needs manual check", the in-scope criteria that the code cannot settle (for example rendered contrast, caption accuracy, or reading order after layout), and SHALL NOT state or imply that the target conforms to WCAG.

#### Scenario: Clean audit
- **WHEN** verification leaves no findings
- **THEN** the report says no issues were found in the code, lists the manual checks, and does not say the target is conformant

### Requirement: Existing accessibility tests
The skill SHALL run an accessibility test command only when the target project already defines one and the user confirms the exact command, SHALL NOT run one that the audited change defines or modifies, SHALL include its results in the report, and SHALL NOT install any tool or dependency.

#### Scenario: Project has an a11y test script
- **WHEN** the project's package scripts define an accessibility test, such as one running axe or pa11y, and the user confirms the command
- **THEN** the skill runs it, lists any files it created, and adds its failures as candidate findings, which then go through verification

#### Scenario: Test script defined by the audited change
- **WHEN** the target's diff adds or changes the accessibility test command's definition
- **THEN** the skill does not run it and says why in the report

#### Scenario: No a11y tooling
- **WHEN** the project defines no accessibility test command
- **THEN** the skill audits by reading code only and installs nothing

### Requirement: Fix mode
With `--fix`, the skill SHALL apply fixes for verified findings to the working tree, SHALL skip findings whose fix needs a product decision (wording, colours, or a design change) and list them instead, SHALL create no commits, and SHALL show the resulting diff. Without `--fix`, it SHALL change no files, except artifacts written by an accessibility test command the user confirmed, which the report lists.

#### Scenario: Fix applied
- **WHEN** the user runs `ep-a11y --fix` and a form input lacks a programmatic label
- **THEN** the skill associates a label with the input, makes no commit, and shows the diff

#### Scenario: Fix needs a decision
- **WHEN** a verified finding needs new visible text or a brand colour change
- **THEN** the skill leaves the code unchanged and lists the finding as needing a decision

#### Scenario: PR target with fix
- **WHEN** the user runs `ep-a11y 42 --fix` and the current branch is not PR #42's head branch
- **THEN** the skill reports the findings without editing files and says that fixes need the PR's branch checked out

#### Scenario: Branch target with fix
- **WHEN** the user runs `ep-a11y feature --fix` and the current branch is not `feature`
- **THEN** the skill reports the findings without editing files and says that fixes need that branch checked out

### Requirement: Output modes
The skill SHALL print findings ranked most severe first by default. Only when the user passes `--comment` with a PR target SHALL it post the report as a single PR comment, and that comment SHALL carry no model or tool attribution.

#### Scenario: Comment mode
- **WHEN** the user runs `ep-a11y 42 --comment`
- **THEN** one comment with the report is posted on PR #42 without attribution

#### Scenario: Comment without PR
- **WHEN** the user passes `--comment` with a non-PR target
- **THEN** the skill ignores the flag, says so, and posts nothing

### Requirement: Summary block
The skill SHALL end its output with a fenced `ep-a11y-summary` block stating the target, the WCAG version and level, the reference version from the manifest, the finding counts by severity, the number of manual checks, and whether fixes were applied or a comment was posted.

#### Scenario: Summary present
- **WHEN** an audit completes
- **THEN** the output ends with an `ep-a11y-summary` block that another skill can parse

### Requirement: Works without OpenSpec
The skill's behavior SHALL NOT depend on OpenSpec, and SHALL NOT mention OpenSpec when the target repository has no OpenSpec root.

#### Scenario: Repository without OpenSpec
- **WHEN** the target repository has no OpenSpec root
- **THEN** the audit runs normally and the report does not mention OpenSpec

### Requirement: Subagents optional
The skill MAY audit the four WCAG principles (Perceivable, Operable, Understandable, Robust) in parallel subagents, and SHALL produce the same report shape by auditing them sequentially when subagents are unavailable.

#### Scenario: Agent without subagents
- **WHEN** the agent cannot spawn subagents
- **THEN** the skill audits the principles one after another in a single context and produces the same report shape

### Requirement: Generated WCAG references
The skill folder SHALL contain WCAG references generated from W3C's official `wcag.json`: an index of every success criterion (number, name, level, versions, obsolete flag), one file per criterion with its normative text, Understanding link, and sufficient techniques and failures, and a manifest of the source URL, WCAG version, fetch date, source hash, and per-file hashes. Generated files SHALL be marked as generated.

#### Scenario: Reference coverage
- **WHEN** the references are generated from the WCAG 2.2 source
- **THEN** the index lists every success criterion in that source, and each one has a file

#### Scenario: Self-contained
- **WHEN** the skill is installed on its own with `npx skills add`
- **THEN** every reference it reads is inside its own folder, and it needs no network access to cite criteria

### Requirement: Hand-written guidance separate from generated text
Agent guidance on how to detect and fix each criterion in code SHALL live in a hand-written file keyed by criterion number, which regeneration SHALL never modify.

#### Scenario: Regeneration preserves guidance
- **WHEN** the maintainer regenerates the references
- **THEN** the hand-written guidance file is byte-for-byte unchanged

### Requirement: Reference update command
The repository SHALL provide a maintainer command that fetches the WCAG source and regenerates the references, takes the WCAG version from one setting, and has a dry-run mode that reports added, removed, and changed criteria without writing files. A source that fails to parse or has an unexpected structure SHALL abort the run and leave the existing files untouched.

#### Scenario: Upstream errata
- **WHEN** W3C changes a criterion's text and the maintainer runs the update in dry-run mode
- **THEN** the command lists that criterion as changed and writes nothing

#### Scenario: Version bump
- **WHEN** the maintainer changes the version setting to a newer WCAG 2.x release and runs the update
- **THEN** the references and manifest are regenerated for that version

#### Scenario: Bad source
- **WHEN** the fetched source is not valid JSON or lacks the expected principles, guidelines, and criteria structure
- **THEN** the command exits non-zero and changes no files

### Requirement: Offline reference check
The repository SHALL provide an offline check that fails when a generated file differs from its manifest hash, when the index and the criterion files disagree, or when the hand-written guidance cites a criterion number that is missing from the index or marked obsolete.

#### Scenario: Hand edit detected
- **WHEN** someone edits a generated criterion file by hand
- **THEN** the check fails, names the file, and says to regenerate instead

#### Scenario: Stale guidance detected
- **WHEN** the guidance file cites a criterion that the regenerated index no longer contains
- **THEN** the check fails and names the criterion and the guidance section that cites it
