# Tasks

## 1. Phase briefs

- [x] 1.1 In `skills/ep-orchestrate/references/briefs.md`, `## review`: add the optional
  `group: <n>` input (D4). With it, the base sha is the group's start sha and the head is
  the group's head. The `ep-review` or fallback choice keeps today's merge-base rule
  (D3), with the fallback diffing `<start>...<head>`. Finding ids are `g<n>.<m>`. Add the
  partial-change rule (D5): findings about behavior owned by an unticked task of a later
  group are dropped, and after `ep-review` the summary counts and `spec_conformance` are
  recomputed over what remains. Verify: the "Range matches ep-review's base", "Range
  differs from ep-review's base", "Group with no diff", "Requirement owned by a later
  group", and "Ticked task not really done" scenarios in
  `openspec/changes/update-ep-orchestrate-group-review/specs/ep-orchestrate/spec.md` each
  map to text in `## review`. Also check that `grep -n "g<n>" skills/ep-orchestrate/references/briefs.md`
  shows the id form.
- [x] 1.2 In `briefs.md`, `## fix`: let the round input and the block's `round:` value be
  `<k>` or `g<n>` for a group pass (D6). Leave everything else in the section unchanged.
  Verify: `git diff -- skills/ep-orchestrate/references/briefs.md` touches only `## review`
  and `## fix`, and the fix block shows `round: <k> | g<n>`.

## 2. Orchestrator

- [ ] 2.1 In `skills/ep-orchestrate/SKILL.md`, "State file", make three changes (D7, D8):
  - add `start` and the `reviewing` status to `groups[]`
  - add the `group_reviews` array to the JSON example
  - describe `.git/ep-orchestrate/<change>.group-findings`, and note that a group pass
    overwrites `<change>.findings` with label `g<n>`

  Verify: the example is valid JSON once its `<...>` placeholders are replaced and the
  `"a|b"` enumerations are kept as strings, which you can check with
  `python3 -c 'import json,sys; json.load(sys.stdin)'`.
- [ ] 2.2 In `SKILL.md` step 6 (apply), add the group review pass after a group finishes
  with every task done, before the next group (D1, D2, D6, D11):
  - record `start` before the group's first phase
  - run one `review` phase with `group: <n>`
  - apply the clean test, and run one `fix` phase when it is not clean
  - handle question and stop blockers as in step 8.4, with the re-run never a new pass
  - mark the group `done`, then start the next group

  Also add the group pass and its fix to the step 3 phase table, and show the subagent
  path next to the inline path. Verify: the "Group finishes", "Last group finishes", "No
  second pass for a group", "Group stopped before finishing", "Agent without subagents",
  "Major finding in a group pass", "Only minor findings", "Group fix needs a decision",
  and "Group fix needs a spec change" scenarios map to step 6 or the table.
- [ ] 2.3 In `SKILL.md`, "Resume", add the group pass rules (D9):
  - derive `start` from git
  - run a missing pass only when no later group has `Task:` commits
  - continue a pass with `fixed: null` from `<change>.findings` labelled `g<n>`, or run
    the pass again when that file is missing or has another label
  - treat an open fix question during `apply` as a group fix question
  - run no passes once `phase` is past `apply`

  Verify: the "Interrupted before the pass", "Resume at a group fix question", and "State
  file from before group passes" scenarios map to the text.
- [ ] 2.4 In `SKILL.md`, edit two places (D1, D10, D12):
  - step 8 and its Workflow path: state that the end-of-run rounds still run after the
    dead-code phase, and that group passes never run as a Workflow
  - step 10: add the group passes and the `<change>.group-findings` lines to the report,
    and the `group_reviews: passes=<n> fixed=<n> unfixed=<n>` line, after `deadcode:`,
    to the summary block, with its `na` and zero rules

  Verify: the "Group passes with --workflow" and "Group passes reported" scenarios map to
  steps 8 and 10, and `grep -n "group_reviews:" skills/ep-orchestrate/SKILL.md` shows the
  summary line.

## 3. Description and README

- [ ] 3.1 Update the `description:` frontmatter of `skills/ep-orchestrate/SKILL.md` and the
  `ep-orchestrate` row of `README.md` to say that each task group gets one review pass,
  with its findings fixed, before the next group, and that up to 3 review rounds still
  follow (D14). Verify: the description is under 1024 characters
  (`python3 -c "import re;t=open('skills/ep-orchestrate/SKILL.md').read();print(len(re.search(r'^description: (.*)$',t,re.M).group(1)))"`),
  and `git diff -- README.md` changes only the `ep-orchestrate` row.

## 4. Integration

- [ ] 4.1 Run `openspec validate update-ep-orchestrate-group-review --strict` and
  `bash scripts/check-shared.sh`. Then check that
  `git diff main --stat -- skills/ shared/` lists only `skills/ep-orchestrate/SKILL.md` and
  `skills/ep-orchestrate/references/briefs.md`. Verify: both commands exit 0, and the stat
  lists no other skill or shared file.
