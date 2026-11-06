# Design

## Context

See proposal.md (Why). Current behavior in `skills/ep-orchestrate/`:

| Where | Today |
|---|---|
| `SKILL.md` step 6 (apply) | after each group: record commits, check `Task:` lines, then the next group; no review between groups |
| `SKILL.md` step 7 / 8 | dead code once, then up to 3 review rounds on `base..HEAD`, each with one fix phase |
| `briefs.md#review` | `ep-review <branch>` only when the base sha equals `git merge-base <branch> origin/<default>`, else the review fallback with the base sha; finding ids `r<round>.<n>` |
| `briefs.md#fix` | input "round number", block `round: <k>`; question and `spec:` blockers as in step 8.4 |
| `ep-review` targets | none, `<branch>`, `<pr>`; no commit-range target |
| State file | `groups[].status` is `done|in_progress|pending`; `reviews[]` holds end-of-run rounds; `<change>.findings` holds the latest round's `finding:` lines and fix `commits:` lines |
| `--workflow` | runs step 8.1 as one Workflow; plan and apply never do |

The user chose: after each apply group commits, one `ep-review` pass on that group's
commits, with verified findings fixed before the next group starts. The end-of-run rounds
stay.

## Goals / Non-Goals

**Goals:**
- Each group's defects are found and fixed before later groups build on them.
- A bounded cost: one pass and at most one fix phase per group.
- Group passes resume like every other phase.

**Non-Goals:**
- A commit-range target in `ep-review`. That would change another skill.
- Repeat rounds per group, or dropping or shortening the end-of-run rounds.
- Running group passes as a Workflow.
- Retroactive passes for groups finished before this change, or before a resume
  rebuilt the state.

## Decisions

**D1. Exactly one pass per group, for every group.** The pass runs once the group has
every task done, after any apply re-runs (a question, or the one re-run when `done` is
below `total`). It runs for the last group too, before the dead-code phase. There is no
second pass after the fix phase: the next group's pass and the end-of-run rounds cover
the fixes.
*Alternative considered:* repeating each group's pass until it is clean, up to 3 times.
It was rejected because it multiplies the cost by the number of groups, and the user asked
for one pass.

**D2. Range: the group's start sha to its head.**
- `start` is `git rev-parse HEAD` just before the group's first apply phase. It is
  recorded in `groups[].start`.
- `head` is HEAD when the group finishes.
- On resume, git wins over the file: `start` is the parent of the earliest commit in
  `<base-sha>..HEAD` whose `Task:` line names a task of the group.

The range holds only the group's task commits, because the previous group's fix commits
are made before the next group starts.

**D3. Tool: `ep-review` when its diff base matches, else the fallback.** This is the
same rule as `briefs.md#review` today, with the group's start sha as the base sha.
- `ep-review <branch>` diffs from the merge base. It matches only when `start` is that
  merge base, which in practice means group 1 on a branch with no earlier run commits
  (no plan commit after `base`).
- Every other pass follows `briefs.md#review-fallback` with `git diff <start>...<head>`.
  The fallback mirrors `ep-review`'s rules, so the findings use the same dimensions and
  severities.

*Alternative considered:* running `ep-review <branch>` over the whole branch and keeping
only findings in the group's hunks. It was rejected because the summary counts would
cover other groups, and the filtering is guesswork. *Alternative considered:* adding a
range target to `ep-review`. It was rejected as out of scope: it is another skill's
change, and the fallback already covers a range.

**D4. Review brief inputs for a group pass.** `briefs.md#review` gains an optional
`group: <n>` input. With it:
- the base sha is the group's start sha, and the head is the group's head
- finding ids are `g<n>.<m>`, distinct from task ids and from `r<k>.<m>`
- the partial-change rule (D5) applies

The printed `finding:` lines and `ep-review-summary` keep their formats.

**D5. Spec conformance for a partial change.** In a group pass, tasks still `- [ ]` in
`tasks.md` belong to later groups.
- A missing or partial requirement whose implementing task is one of those is not a
  finding. It is dropped and counted in neither `verified` nor `dropped_in_verification`.
- This applies whether the finding came from `ep-review` or from the fallback. When
  `ep-review` produced the summary, the phase recomputes `verified`, `by_dimension`, and
  `spec_conformance` over the findings that remain, so the summary matches the findings
  list.
- Contradictions of a scenario's THEN, out-of-spec behavior, and ticked tasks of this
  group that are not done stay findings.

**D6. One fix phase per pass.**
- *When:* the pass has a critical or major finding, or `spec_conformance: failed`. The
  same "clean" test as step 8.2 decides it, so `not_applicable` also counts as not clean.
  It should not occur, because the pass is always given the change name.
- *Inputs:* `briefs.md#fix`, unchanged except that its round input and the block's
  `round:` value may be `g<n>`. It fixes critical and major findings and cheap minors,
  and defers the rest.
- *Large changes:* `large_predicted` and `groups:` are passed as in step 8, so group fix
  commits carry `Group:` lines and stay in their stack layer.
- *Questions:* a question blocker (`needs input: g<n>.<m>: ...`) uses the phase question
  point unchanged. Answers are keyed by finding id, the 2-question limit applies per id,
  and the re-run covers the pass's findings with no fix commit yet. A re-run is never a
  new pass.
- *Stops:* `Stop`, a `spec:` blocker, or any other blocker stops the run with outcome
  `blocked`, as in step 8.4.
- *Afterwards:* the next group starts, with no re-review.

**D7. Findings files.**
- When a pass returns, `.git/ep-orchestrate/<change>.findings` is overwritten with label
  `g<n>` and its `finding:` lines, and fix `commits:` lines are appended to it, as for a
  round. Step 8's first round overwrites it later.
- So that the final report can list them, the `finding:` lines of each pass's findings
  that have no fix commit when the pass ends are appended to
  `.git/ep-orchestrate/<change>.group-findings`. These are its minor findings and its
  deferred ones. This keeps finding text out of the state file.

**D8. State file fields.**
- `groups[]` gains `start: "<sha>"`. `status` gains `reviewing`: the tasks are done, and
  the pass or its fix phase is not finished. A group is `done` only after its pass, and
  its fix phase when one runs, finish.
- A new `group_reviews` array holds one entry per pass:
  `{ "group": 1, "critical": 0, "major": 1, "minor": 2, "spec": "passed",
  "head": "<sha>", "fixed": 1, "unfixed": 2 }`. `fixed` and `unfixed` are `null` until
  the fix phase ends. With no fix phase, `fixed` is 0 and `unfixed` is the minor count.
- `phase` stays `apply` during passes. An open fix question during `apply` is a group fix
  question.

**D9. Resume.**
- A group whose tasks are all done and that has no finished `group_reviews` entry gets
  its pass before the next group starts, but only when no later group has a commit with a
  `Task:` line. Earlier groups are not reviewed retroactively, which also covers state
  files written before this change.
- An entry that needs a fix phase but has `fixed: null` continues with the fix phase,
  using `<change>.findings` when its label is `g<n>`. When that file is missing or carries
  another label, the pass is run again, because the pass is read-only. This differs from
  step 8's "findings lost" stop for an open question: there the question stays the rule.
  An open group fix question with the file missing stops with outcome `blocked`, as
  today.
- When `phase` is already past `apply`, no group pass runs.

**D10. `--workflow`.** Group passes never run as a Workflow, with or without the flag.
The flag keeps its meaning for step 8. A Workflow per group would start up to 9 agents per
group, and one pass is meant to be cheap.

**D11. Subagent path and sequential fallback.**
- **With subagents:** each group pass is one fresh subagent on `briefs.md#review` with
  `group: <n>`. Its fix phase is one fresh subagent on `briefs.md#fix`. The driving
  session reads only the `finding:` lines and summary blocks.
- **Without subagents:** the same two phases run inline after the group. The state file
  is written after each, and the resume command is printed with the usual suggestion to
  clear context.

**D12. Report and summary block.**
- The report lists each group pass: the group, its counts, `fixed`, `unfixed`, and the
  lines from `<change>.group-findings`.
- The summary block gains `group_reviews: passes=<n> fixed=<n> unfixed=<n>`, after
  `deadcode:`. It is `passes=0 fixed=0 unfixed=0` before any pass. The line is additive,
  so readers of the existing keys are unaffected.

**D13. Gates.** Nothing outward or destructive is added. Passes are read-only and post
nothing. Fixes are local commits under the existing per-finding commit rules. The gate
score and the size thresholds in `references/confidence.md` are unchanged.

**D14. Description and README.** The frontmatter `description` and the README row say
that each group gets one review pass before the next. The description stays under 1024
characters.

## Risks / Trade-offs

- [More time and tokens: up to one review and one fix subagent per group] → one pass per
  group (D1), no Workflow (D10), and a fix phase only when a critical or major finding
  exists or spec conformance fails (D6).
- [The fallback, not `ep-review`, runs most group passes] → the fallback mirrors
  `ep-review`'s rules (`briefs.md` "Rules that must match"). The end-of-run rounds still
  use `ep-review` when the base matches.
- [The partial-change rule may hide a real gap] → it drops only findings tied to an
  unticked task of a later group, and step 8 reviews the finished change with no such
  rule.
- [Findings repeat between a group pass and step 8] → step 8 reviews the whole branch
  anyway, and repeated minors are reported once per review that found them.
- [A resume after a state rebuild skips passes of earlier groups] → by design (D9). Step
  8 still reviews the whole branch.

## Migration Plan

None beyond editing the skill. An in-flight run resumes under D9. Rollback is reverting
the skill's commits; state files with the new fields are still read, because the extra
fields are ignored by the old text.
