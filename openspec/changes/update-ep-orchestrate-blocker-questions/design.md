# Design

## Context

See proposal.md (Why). Current behavior in `skills/ep-orchestrate/`:

| Where | Today |
|---|---|
| `SKILL.md` "Asking the user" | "a choice a phase cannot make comes back as its `blocker`, and you ask it here" |
| `briefs.md` "Rules for every phase" | "A choice you cannot make becomes your `blocker`, naming the question; the orchestrator asks it." |
| `SKILL.md` step 4 (plan) | on `blocker: needs input`, ask the planner's question (options when it names 2 to 4) and re-run the plan phase |
| `SKILL.md` step 6 (apply) | "`verification: failed` or any blocker: stop" → outcome `blocked`; the task stays unticked and its work uncommitted; the user must finish and commit it or discard it before the next run |
| `SKILL.md` step 8.4 (fix) | "A `blocker` (for example a finding needing a spec change) stops the run with outcome `blocked`." |
| `briefs.md#apply` | stops on failed verification (`blocker: <id>: <failure>`), on plan conflicts (`blocker: plan: ...`), and on ticked-but-not-done tasks |
| `briefs.md#fix` | `blocker: spec: <finding id> ...` for a finding that needs a spec change; other unfixed findings are deferred |
| State file | no field for an open phase question; Resume re-asks only a `paused` gate |
| Clean-tree check (step 1.5, Resume 3) | any path outside the change folder stops the run |

No brief defines the wording of a question blocker: step 4 matches `needs input` loosely.
`AskUserQuestion` takes 2 to 4 options per question, and the user can always type "Other".

## Goals / Non-Goals

**Goals:**
- An apply or fix phase's open choice reaches the user as a question, and the answer
  reaches a re-run of that phase.
- One blocker form that the driving session can tell apart from stops, the same in every
  phase.
- An interrupted session resumes at the same question without losing the partial work.

**Non-Goals:**
- Changing which blockers stop: failed verification, `plan:`, `spec:`, and
  ticked-but-not-done stay stops.
- Letting phases ask mid-phase, or the question tool being called from a subagent.
- A summary `outcome` value for a user stop at step 1.6, which is a separate finding.
- Changes to other skills, `shared/`, or the README.

## Decisions

**D1. Question blocker form.** Every phase writes a question as one line:
`blocker: needs input: <id>: <question> | <option> ; <option> [; <option>]`.
- `<id>` is the task id (apply), the finding id (fix), or the change name (plan).
- The `| options` part is optional. With 2 or 3 options they become the question's options,
  and the driving session adds `Stop`, so the total stays within the tool's limit of 4.
  With none, the question is open and asked in plain text.
- Any other `blocker:` value is a stop.

*Alternative considered:* a separate `question:` key in the summary blocks. It was rejected
because every block already has a `blocker:` line that the orchestrator reads, and the plan
phase already uses `needs input`.

**D2. Partial work stays in place.** An apply phase that stops on a question leaves the
task unticked and its work uncommitted, as it does today for other blockers, and reports
the paths it changed in a new summary field, `files: <path>,<path>`. The driving session
records those paths. The re-run phase gets an input saying the working tree holds partial
work for `<id>` in those paths, and it continues from it rather than starting over.
*Alternative considered:* reverting the partial work before asking. It was rejected because
that work may be most of the task, and reverting means checking out files, which the skill
avoids doing on the user's tree.

The fix phase works the same way. Its fixes are committed per finding, so only the blocked
finding's work is left in place.

**D3. Answers reach the phase as an input.** `briefs.md#apply` and `briefs.md#fix` gain
the input `answers:`, given as lines of `<id>: <question> => <answer>`. The phase treats an
answer as a decision for that id. When an answer conflicts with the specs or design, it
stops with a `plan:` or `spec:` blocker as today, because answers never override the fixed
plan. For a fix re-run, the driving session passes only the findings that have no fix
commit yet, read from the `commits:` field of the earlier fix summary.

**D4. Limit.** A task or finding may come back with a question at most twice. A third
question stops the run with outcome `blocked` and reports the question and the earlier
answers. This bounds the loop the same way the 3 verification attempts and the 3 review
rounds do. The count is kept in the state file, so a resume does not reset it.

**D5. State file fields.**
- `question` holds `{ "phase": "apply|fix|plan", "id": "<id>", "text": "...", "options":
  [..], "files": [..] }`, or `null`.
- `answers` holds `{ "<id>": [ { "q": "...", "a": "..." } ] }`.

These are short user-facing text, not diffs or logs, so they fit the rule that the state
file holds no diffs, logs, or finding text. `question` is written before asking, the same
way the gate writes `decision: paused` before asking. It is cleared when the answer is
recorded.

**D6. Resume.**
- When `question` is set, Resume step 3 (the clean-tree check) accepts uncommitted changes
  only in `question.files` and the change folder. Any other path stops the run as
  `dirty_tree`.
- Resume step 4 then asks the question again before continuing at the recorded phase.
- When the recorded paths no longer have changes (for example the user discarded them),
  the re-run starts the task fresh. The answer still applies.

**D7. `Stop` keeps today's behavior.** `Stop` ends the run as `blocked`, with the same
report as today (finish and commit with `Task: <id>`, or discard). The `question` field
stays set, so a later run can ask the question again.

**D8. Subagent path and sequential fallback.**
- **With subagents:** the phase subagent ends with the blocker. The driving session asks,
  then starts a fresh subagent for the re-run with `answers` and the partial-work paths.
- **Without subagents:** the inline phase ends at the blocker in the same way, by printing
  its summary block. The driving session asks, then runs the phase inline again with the
  answers. The question is never asked mid-phase in either path.

**D9. Gates.** Nothing outward or destructive is added. The question is asked before any
code change for that choice. A re-run commits only through the existing per-task and
per-finding commit rules.

## Risks / Trade-offs

- [A phase may label a real plan conflict as a question] → `briefs.md` states that
  conflicts with the specs or design are `plan:` or `spec:` blockers, never questions, and
  an answer can never override the plan (D3).
- [A partial-work path list may be incomplete] → the clean-tree check stops on any
  unrecorded path, so nothing outside the list is silently accepted (D6).
- [Re-runs cost a fresh subagent each] → at most two per task or finding (D4).
- [The open-question resume adds a second accepted-leftover rule] → it is limited to
  recorded paths and applies only while `question` is set.
