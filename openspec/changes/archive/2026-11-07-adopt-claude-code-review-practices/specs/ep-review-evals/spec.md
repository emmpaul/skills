# Spec Delta

## Purpose

Measures `ep-review` against a repository's own history: builds a user-confirmed eval set of PRs that caused incidents and PRs that stayed clean, scores review recall and noise on it, compares runs to decide whether a reviewer change helps, and reports how authors answered posted findings.

## ADDED Requirements

### Requirement: Subcommands
The skill SHALL provide the subcommands `collect`, `run`, `compare`, and `noise`, and SHALL print usage and stop when invoked with none or an unknown one.

#### Scenario: No subcommand
- **WHEN** the user invokes `ep-review-evals` with no subcommand
- **THEN** the skill prints the four subcommands with one line each and changes nothing

### Requirement: Collect incident candidates
`collect` SHALL find merged PRs that were later reverted, or whose changed lines a later fix commit changed again (found by blame of the fix's parent), within a window that defaults to 90 days. For each, it SHALL propose the introducing PR, the bug's file and line range at that PR's head, and a description taken from the revert or fix.

#### Scenario: Reverted PR
- **WHEN** a merged commit says "This reverts commit <sha>" and `<sha>` belongs to merged PR #12
- **THEN** PR #12 is proposed as an incident case with the revert as its description

#### Scenario: Fix forward
- **WHEN** a `fix:` commit changes lines that blame attributes to merged PR #20 within the window
- **THEN** PR #20 is proposed as an incident case with those lines as the bug location

### Requirement: Collect clean cases
`collect` SHALL also propose up to an equal number of clean cases: merged PRs at least 30 days old whose changed lines no later revert or fix commit touched.

#### Scenario: Clean sample
- **WHEN** collect proposes 6 incident cases and the repo has 40 qualifying clean PRs
- **THEN** it proposes 6 clean cases picked from them

### Requirement: Human-confirmed cases
`collect` SHALL save no case until the user confirms it. For each proposed case the user can accept it, edit its location or description, or reject it. Confirmation SHALL never be skipped by a flag.

#### Scenario: Case edited
- **WHEN** the user corrects an incident case's line range before accepting it
- **THEN** the saved case has the corrected range and is marked confirmed

#### Scenario: All rejected
- **WHEN** the user rejects every proposed case
- **THEN** no file is written

### Requirement: Eval files stay local
The skill SHALL write cases and runs only under the eval directory (default `review-evals/`, set with `--dir`), SHALL show what it will write before writing, and SHALL NOT commit, push, or post anything to GitHub.

#### Scenario: Files written
- **WHEN** the user confirms cases
- **THEN** they are written to `review-evals/cases.json` in the working tree and the skill leaves them uncommitted

### Requirement: Run the reviewer on cases
`run` SHALL state the number of cases and get the user's confirmation before starting. It SHALL review each case with `ep-review` at the case's head against the case's base, in a temporary worktree outside the repository's working tree, and SHALL remove each worktree afterwards.

#### Scenario: Working tree untouched
- **WHEN** `run` finishes or fails partway
- **THEN** the user's working tree and current branch are unchanged and no temporary worktree is left behind

#### Scenario: Limit
- **WHEN** the user runs `ep-review-evals run --limit 5` with 12 cases
- **THEN** only 5 cases run, chosen with incident and clean cases balanced, and the run records which ones

#### Scenario: Agent without subagents
- **WHEN** the host has no subagent capability
- **THEN** cases run one after another inline, with `ep-review`'s inline verification, and the run records `verification: inline`

### Requirement: Score recall and noise
`run` SHALL score recall as the share of incident cases where a verified introduced finding lies in the bug's file within 3 lines of its range, and noise as the number of verified critical or major findings per clean case, and SHALL save the run with a label, the reviewer version, and per-case results.

#### Scenario: Hit
- **WHEN** an incident case's bug is at `src/a.ts:40-44` and the review reports a verified finding at `src/a.ts:46`
- **THEN** the case counts as a hit

#### Scenario: Run saved
- **WHEN** a run with label `voting` completes
- **THEN** a file under `review-evals/runs/` holds its label, time, reviewer version, recall, noise, and each case's findings

### Requirement: Compare runs
`compare <a> <b>` SHALL print recall and noise for both runs and a verdict: `keep` when `b` has higher recall and no higher noise, or equal recall and lower noise; `drop` otherwise. Runs on different case sets SHALL be compared only on the cases both share, and the output SHALL say so.

#### Scenario: Regression in noise
- **WHEN** run `b` has higher recall than `a` but also higher noise
- **THEN** the verdict is `drop` with both numbers shown

### Requirement: Noise from author responses
`noise` SHALL read PR reviews that `ep-review` posted (identified by its summary block) and classify each posted finding by the author's response: fixed, said wrong, said intentional, said it did not matter, or unanswered. It SHALL be read-only and SHALL propose `REVIEW.md` lines for repeated wrong or did-not-matter findings without writing them.

#### Scenario: Repeat false positive
- **WHEN** findings of the same class on the same path were answered "wrong" on 3 PRs
- **THEN** the report proposes a `REVIEW.md` line covering that class and path, and writes nothing

#### Scenario: No posted reviews
- **WHEN** no PR in range has an `ep-review` review
- **THEN** the skill says so and suggests running `ep-review <pr> --comment`

### Requirement: Works without OpenSpec
The skill SHALL behave the same in repositories with or without an OpenSpec root and SHALL NOT mention OpenSpec when there is none.

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** collect, run, compare, and noise work normally and the output does not mention OpenSpec

### Requirement: No attribution and summary block
The skill SHALL add no model or tool attribution to anything it writes, and SHALL end its output with an `ep-review-evals-summary` block giving the subcommand, case counts, and for `run` and `compare` the recall, noise, and verdict.

#### Scenario: Summary after run
- **WHEN** `run` completes
- **THEN** the output ends with an `ep-review-evals-summary` block that includes `recall:` and `noise:`
