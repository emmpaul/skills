# ep-review Specification

## Purpose

Reviews a code change across several dimensions, including conformance to the active OpenSpec change, verifies each finding before reporting it, and reports locally or as PR comments.

## Requirements

### Requirement: Review targets
The skill SHALL accept as target the local uncommitted diff (default), a branch compared to its base, or a GitHub PR number.

#### Scenario: Default target
- **WHEN** the user invokes `ep-review` with no target
- **THEN** the skill reviews the uncommitted diff, or the branch versus its base if the tree is clean

#### Scenario: PR target
- **WHEN** the user invokes `ep-review 42`
- **THEN** the skill reviews the diff of PR #42

### Requirement: Multi-dimension review
The skill SHALL review the target along the dimensions correctness, spec conformance, tests, and security.

#### Scenario: All dimensions covered
- **WHEN** a review runs
- **THEN** the report shows findings, or an explicit "no findings", for each of the four dimensions

### Requirement: Spec conformance against OpenSpec
When the target relates to an active OpenSpec change, the spec conformance dimension SHALL check each delta-spec requirement and scenario against the diff and flag requirements with no implementation, behavior not covered by any requirement, and scenarios with no test.

#### Scenario: Missing requirement
- **WHEN** a delta spec requires behavior that the diff does not implement
- **THEN** the review reports a spec-conformance finding naming that requirement

#### Scenario: Unspecified behavior
- **WHEN** the diff adds externally visible behavior that no requirement describes
- **THEN** the review reports it as out-of-spec

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the spec conformance dimension is reported as not applicable and the other dimensions run normally

### Requirement: Verified findings
Each candidate finding SHALL pass a verification step that tries to disprove it before it is reported, and each reported finding SHALL include location, severity (critical, major, minor), origin (introduced or pre-existing), and a concrete failure scenario. When the host can spawn subagents, verification SHALL be a vote of 3 independent verifiers, and a finding SHALL be reported only when at least 2 of them confirm it.

#### Scenario: False positive dropped
- **WHEN** verification shows a candidate finding cannot occur
- **THEN** the finding is not reported

#### Scenario: Finding shape
- **WHEN** a finding is reported
- **THEN** it includes file and line, severity, origin, summary, and a failure scenario

#### Scenario: Split vote
- **WHEN** 1 of 3 verifiers confirms a finding and 2 refute it
- **THEN** the finding is not reported and counts toward `dropped_in_verification`

#### Scenario: Majority downgrades
- **WHEN** a major candidate gets the verdicts confirmed, downgraded to minor, and downgraded to minor
- **THEN** the finding is reported as minor, the highest severity that at least 2 non-refuting verdicts support

#### Scenario: Agent without subagents verifies
- **WHEN** the host agent has no subagent capability
- **THEN** each finding is verified once inline with the same disproof steps, and the summary records `verification: inline`

### Requirement: Output modes
The skill SHALL print findings ranked most severe first by default, and SHALL post them as PR review comments only when the user passes `--comment` on a PR target. In comment mode it SHALL NOT post a finding that an earlier `ep-review` review on the same PR already posted.

#### Scenario: Comment mode
- **WHEN** the user runs `ep-review 42 --comment`
- **THEN** findings are posted as review comments on PR #42 without model attribution

#### Scenario: Default mode
- **WHEN** no `--comment` flag is given
- **THEN** nothing is posted to GitHub

#### Scenario: Finding already posted
- **WHEN** `ep-review 42 --comment` verifies a finding at the same file and summary as an inline comment from an earlier `ep-review` review on PR #42
- **THEN** that finding is left out of the new review's comments and the review body counts it as already posted

#### Scenario: Pre-existing finding posted
- **WHEN** a pre-existing finding is posted in comment mode
- **THEN** its comment is tagged `pre-existing` so it does not read as the author's fault

### Requirement: Machine-readable result for callers
The skill SHALL produce a summary with counts of verified introduced findings by severity and dimension, spec-conformance status, the count of pre-existing findings, the risk tier and its reasons, the verification path, and the review scope, usable by `ep-babysit-pr` and `ep-orchestrate`.

#### Scenario: Called by babysitter
- **WHEN** `ep-babysit-pr` runs a review round
- **THEN** it receives finding counts by severity, whether spec conformance passed, the risk tier, and the pre-existing count

#### Scenario: Pre-existing excluded from counts
- **WHEN** a review verifies 1 introduced major finding and 2 pre-existing major findings
- **THEN** the summary has `verified: critical=0 major=1 minor=0` and `pre_existing: 2`

### Requirement: Parallel dimensions with sequential fallback
When the host agent can spawn subagents, the skill SHALL review dimensions in parallel and verify findings by a vote of 3 verifier subagents; otherwise it SHALL review and verify sequentially with the same output.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the four dimensions and verification run sequentially and the report has the same structure

#### Scenario: High effort in Claude Code
- **WHEN** the user requests high effort in Claude Code
- **THEN** the skill MAY run the review as a Workflow with the four dimensions and 3 voter agents, using at most 7 agents

### Requirement: Pre-existing findings
The skill SHALL report verified defects in code the diff touches or directly calls but did not introduce, tagged `pre-existing`. They SHALL be listed apart from introduced findings and excluded from the blocking counts.

#### Scenario: Old bug in a touched function
- **WHEN** the diff edits a function, and a bug in that function's unchanged lines is verified, and blame shows those lines predate the diff
- **THEN** the finding is reported with origin `pre-existing` and is not counted in `verified:`

#### Scenario: Old bug in untouched code
- **WHEN** a defect sits in a file the diff neither changes nor calls into
- **THEN** it is not reported

### Requirement: Bug class instances
Each reported finding SHALL name the class of defect and list every other location in the diff with the same defect, so a fix can cover all of them.

#### Scenario: Same mistake repeated
- **WHEN** the same unchecked null dereference appears in three changed functions
- **THEN** one finding is reported with the class named and the other two locations listed under `instances`

### Requirement: Intent and root cause
The skill SHALL read the change's stated intent (PR title and body, or commit messages for a branch or diff) and, when the change is a bug fix, SHALL check whether the fix addresses the root cause.

#### Scenario: Symptom-only fix
- **WHEN** a PR titled as a fix guards one call site while another path in the repo still triggers the same failure
- **THEN** the review reports a correctness finding naming the unguarded path

### Requirement: REVIEW.md guidance
When the target repository has a `REVIEW.md` at its root or in `.github/`, the skill SHALL follow it: free text guides every dimension, and recognised sections set paths to skip, a cap on reported minor findings, risk paths, and trusted authors.

#### Scenario: Skipped path
- **WHEN** `REVIEW.md` lists `generated/**` under Skip and the diff changes `generated/api.ts`
- **THEN** no finding is reported in that file and the report says it was skipped by `REVIEW.md`

#### Scenario: Minor cap
- **WHEN** `REVIEW.md` sets a minor cap of 3 and 5 minor findings are verified
- **THEN** the 3 most important are reported and the report states that 2 more were omitted by the cap

#### Scenario: No REVIEW.md
- **WHEN** the repository has no `REVIEW.md`
- **THEN** the review runs with defaults and does not mention the file

### Requirement: Agent instruction file conventions
The skill SHALL report, under correctness, changes that break conventions stated in the repository's `CLAUDE.md` or `AGENTS.md`, and lines in those files that the diff makes stale.

#### Scenario: Stale instruction line
- **WHEN** the diff renames `scripts/build.sh` and `CLAUDE.md` still tells agents to run `scripts/build.sh`
- **THEN** the review reports a minor correctness finding at that `CLAUDE.md` line

### Requirement: Diff-only re-review
The skill SHALL accept `--since <sha>` to review only the changes from `<sha>` to the target head, reading surrounding code as usual, and SHALL record the scope in its summary.

#### Scenario: Since a reviewed head
- **WHEN** the user runs `ep-review 42 --since abc123`
- **THEN** only the diff from `abc123` to the PR head is reviewed and the summary has `scope: since:abc123`

#### Scenario: Full review
- **WHEN** `--since` is not given
- **THEN** the summary has `scope: full`

### Requirement: Known findings are not repeated
The skill SHALL accept `--known <file>` listing findings already reported, SHALL re-check each, and SHALL report a known finding again only when it is still present, marked `still open`, never as a new finding.

#### Scenario: Known finding fixed
- **WHEN** a known finding no longer occurs at the new head
- **THEN** it is not reported and the summary counts it under `known: fixed=<n>`

#### Scenario: Known finding still present
- **WHEN** a known major finding still occurs at the new head
- **THEN** it is reported once, marked `still open`, and counted in `verified:`

### Requirement: Risk tier
Every review SHALL classify the change as `low`, `medium`, or `high` risk from the paths it changes, the shared risk rules, and `REVIEW.md` risk paths, and SHALL give the reasons. The reviewer MAY raise the tier with a stated reason and SHALL NOT lower it below the path-based tier.

#### Scenario: CI workflow change
- **WHEN** the diff changes a file under `.github/workflows/`
- **THEN** the summary has `risk: high` with a reason naming that path

#### Scenario: Documentation only
- **WHEN** every changed path is documentation by the shared rules and the author is trusted
- **THEN** the summary has `risk: low`

#### Scenario: Untrusted author
- **WHEN** the path rules give `low` but the PR author is neither the authenticated user nor listed as trusted in `REVIEW.md`
- **THEN** the tier is raised to `medium` with the reason "author not trusted"

### Requirement: Count-first report
The report SHALL start, under its header, with one line giving the number of findings to fix by severity and the number of pre-existing findings, or the plain line "Nothing to fix." when there are none to fix.

#### Scenario: Clean review
- **WHEN** a review verifies no introduced findings and no pre-existing findings
- **THEN** the first line under the header is "Nothing to fix."
