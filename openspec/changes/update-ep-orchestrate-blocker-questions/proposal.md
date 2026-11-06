## Why

`ep-orchestrate` tells every phase that a choice it cannot make comes back as a `blocker`
naming the question, and that the driving session asks it ("Asking the user" in `SKILL.md`,
"Rules for every phase" in `references/briefs.md`). The main spec's requirement "Questions
only from the driving session" says the same for any phase. In practice only the plan
phase gets that: steps 6 (apply) and 8 (fix) stop the run with outcome `blocked` on any
blocker, so an apply or fix question is never asked and its answer has no way back into the
phase. The final review of PR #11 found this mismatch (findings r3.1 and r3.2, waived there
as out of scope). This change makes the skill do what its rule says.

## What Changes

- **Modified** `ep-orchestrate`:
  - **One blocker form for questions.** Every phase writes a question as
    `blocker: needs input: <id>: <question> | <option> ; <option>`. `<id>` is the task id
    (apply) or finding id (fix), and there are 0, 2 or 3 options. Other blockers keep
    stopping the run as today: failed verification, `plan:` conflicts, `spec:` findings,
    and `ticked but not done`.
  - **Apply (step 6) and fix (step 8) ask instead of stopping.**
    - On a question blocker, the driving session asks the question through "Asking the
      user". The phase's options are offered plus `Stop`.
    - It then re-runs the same group, or the same fix round, in a fresh phase. The answer
      is a new `answers` input to the `apply` and `fix` briefs.
    - The blocked task's partial work stays in the working tree, and the re-run continues
      from it.
    - `Stop` ends the run as `blocked`, the same as today's stop.
  - **A limit per task or finding.** Each task or finding may come back with a question at
    most twice. A third question stops the run as `blocked`.
  - **The state file records the open question.** It holds the phase, the id, the text,
    the options, and the paths the blocked work changed. Resume asks the question again
    before anything else. The clean-tree check accepts exactly the recorded paths as
    leftovers.
  - **The plan phase uses the same blocker form.** Its id is the change name. Step 4 asks
    as it does today.
- `README.md`, the frontmatter description, `shared/context.sh`, the summary block's
  `outcome` values, and the other skills are unchanged.
- **Not in scope:** a summary `outcome` value for a run the user stops at step 1.6 (a
  separate minor finding from the same PR).

Outward effects on GitHub: none. The change only alters local questions and phase re-runs.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `ep-orchestrate`: apply and fix blockers that name a question are asked by the driving
  session and answered into a re-run of the phase. Verification, plan, and spec blockers
  still stop. Resume asks an open question again.

## Impact

- `skills/ep-orchestrate/SKILL.md`:
  - "Asking the user": the question blocker form
  - the state file: the `question` and `answers` fields
  - Resume
  - step 4 (plan): the shared form
  - step 6 (apply)
  - step 8 (fix)
- `skills/ep-orchestrate/references/briefs.md`:
  - "Rules for every phase": the blocker form
  - `apply` and `fix`: the `answers` input and partial work left in place on a question
- No other skill, shared file, or README changes.
