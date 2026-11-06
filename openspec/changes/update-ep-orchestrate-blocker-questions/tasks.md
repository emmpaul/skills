# Tasks

## 1. Phase briefs

- [x] 1.1 In `skills/ep-orchestrate/references/briefs.md`, "Rules for every phase": replace
  the question rule's last sentence with the question blocker form (D1). The form is
  `blocker: needs input: <id>: <question> | <option> ; <option>`, with 0, 2 or 3 options,
  and `<id>` is the task id, finding id, or change name. Also state that conflicts with
  the specs or design are `plan:` or `spec:` blockers, never questions. Verify:
  `grep -n "needs input" skills/ep-orchestrate/references/briefs.md` shows the form in the
  rules, and the "Phase subagent needs an answer" scenario in
  `openspec/changes/update-ep-orchestrate-blocker-questions/specs/ep-orchestrate/spec.md`
  maps to it.
- [x] 1.2 In `briefs.md#apply`, make three changes (D2, D3):
  - add the inputs `answers:` (lines of `<id>: <question> => <answer>`) and the
    partial-work paths for a task being re-run
  - add a stop condition: a choice the task cannot make, which leaves the task unticked
    and its work uncommitted, writes the question blocker, and lists the changed paths
  - add `files: <path>,<path> | none` to the `ep-orchestrate-apply` block

  Verify: the "Task needs a decision" scenario maps to the stop condition and the inputs,
  and the block shows `files:`.
- [x] 1.3 In `briefs.md#fix`, make three changes (D2, D3):
  - add the `answers:` input
  - add the question blocker for a finding with an open choice, which leaves only that
    finding's work uncommitted
  - add `files:` to the `ep-orchestrate-fix` block

  Keep the `spec:` blocker as is. Verify: the "Fix needs a decision" and "Fix needs a
  spec change" scenarios map to the text.

## 2. Orchestrator

- [x] 2.1 In `skills/ep-orchestrate/SKILL.md`, "State file": add `question` (phase, id,
  text, options, files, or `null`) and `answers` (per id, a list of question and answer
  pairs) to the JSON example (D5). Verify: the example is valid JSON once its `<...>`
  placeholders are replaced, which you can check by pasting it into
  `python3 -c 'import json,sys; json.load(sys.stdin)'`.
- [x] 2.2 In `SKILL.md`, "Asking the user": describe the phase question point. A question
  blocker from plan, apply, or fix is asked with its options plus `Stop` (open when it
  has none). `question` is written to the state file before asking and cleared when the
  answer is recorded under `answers`. A third question for the same id stops as
  `blocked` (D1, D4, D5, D7). Point step 4 (plan) at it, keeping the plan behavior.
  Verify: the "Third question for the same task" and "Agent without subagents" scenarios
  map to the text.
- [x] 2.3 In `SKILL.md`, rewrite step 6 (apply) and step 8.4 (fix) to separate question
  blockers from stops (D2, D3, D7, D8):
  - On a question blocker: ask, then re-run the same group, or the same round's fix
    phase for findings without a fix commit, with `answers` and the partial-work paths.
    The re-run does not count as a review round.
  - On `Stop`: today's `blocked` stop and report.
  - All other blockers stop as today.

  Show the subagent path next to the inline path. Verify: the "Task needs a decision",
  "User stops at a task question", "Fix needs a decision", and "Fix needs a spec change"
  scenarios map to steps 6 and 8.
- [x] 2.4 In `SKILL.md`, "Resume": when `question` is set, change two steps (D6):
  - step 3: accept uncommitted changes only in `question.files` and the change folder,
    with any other path stopping as `dirty_tree`
  - step 4: ask the question again before continuing at the recorded phase, and start
    fresh when the recorded paths are clean

  Verify: the "Resume with an open question" and "Leftovers outside the recorded paths"
  scenarios map to the text.

## 3. Integration

- [x] 3.1 Run `openspec validate update-ep-orchestrate-blocker-questions --strict` and
  `bash scripts/check-shared.sh`, and check that both pass. Check that
  `git diff main -- README.md` is empty and that the `description:` line of
  `skills/ep-orchestrate/SKILL.md` matches `main`. Verify: both commands exit 0, and both
  checks are unchanged.
