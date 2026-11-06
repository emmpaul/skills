## Why

`ep-orchestrate` applies a change one task group at a time but reviews it only once every
group is done (step 8, up to 3 rounds). A defect in group 1 is found only after later
groups have built on it, when fixing it costs more and the end-of-run rounds may run out.
The user asked for one `ep-review` pass after each apply group, with its verified findings
fixed before the next group starts.

## What Changes

- **Modified** `ep-orchestrate`:
  - **One review pass per group.** After an apply group finishes with every task done,
    the orchestrator runs exactly one review pass on that group's commits (from the
    group's start sha to its head), for every group including the last. There is never a
    second pass for the same group.
  - **Scope and tool.** The pass uses `ep-review` when the group's start sha is the
    commit `ep-review <branch>` diffs against, and the review fallback in `briefs.md`
    with the group's range otherwise.
  - **Spec conformance for a partial change.** Behavior owned by tasks of later groups
    that are not done yet is not a finding in a group pass.
  - **One fix phase per pass.** It runs when the pass has a critical or major finding, or
    spec conformance failed. Minor findings and deferred ones go to the final report. A
    fix question is asked and answered with the existing phase-question mechanics. It
    re-runs the group's fix phase, not a new pass. A `spec:` blocker stops the run as
    today.
  - **State and resume.** The state file records each group's start sha and its pass
    result. A resume runs a missing pass before the next group starts, and continues an
    unanswered group fix question from the findings file.
  - **Unchanged:** the end-of-run review rounds (step 8, up to 3) still run after the
    dead-code phase. `--workflow` still applies only to those rounds. Group passes use
    the subagent or inline path.
  - **Report and summary block.** Both list the group passes. The summary block gains one
    line, `group_reviews: passes=<n> fixed=<n> unfixed=<n>`.
  - **Description and README.** The frontmatter description and the README row mention
    the per-group pass.
- Other skills (`ep-review` included) and `shared/` are unchanged.

Outward effects on GitHub: none. Group passes are read-only and their fixes are local
commits; nothing is pushed or posted.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `ep-orchestrate`: each apply group is followed by one review pass on its commits, with
  one fix phase for its critical or major findings, before the next group starts. The
  state file, resume, report, and summary block cover these passes. The end-of-run
  review rounds are unchanged.

## Impact

- `skills/ep-orchestrate/SKILL.md`:
  - frontmatter `description`
  - step 3 phase table
  - state file: group start sha and group pass fields, the findings file
  - Resume
  - step 6 (apply): the group review pass
  - step 8: a note that the rounds still run, and the `--workflow` scope
  - step 10: the report and summary block
- `skills/ep-orchestrate/references/briefs.md`: `review` (the group pass inputs, range,
  and partial-change spec rule) and `fix` (the group pass label).
- `README.md`: the `ep-orchestrate` row.
- No other skill or shared file changes.
