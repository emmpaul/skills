# Tasks

## 1. ep-orchestrate questions

- [x] 1.1 In `skills/ep-orchestrate/SKILL.md`, add an "Asking the user" subsection after
  "Hard rules" (D1): structured question tool when the host offers one (`AskUserQuestion`
  in Claude Code), one question per decision, options as short label plus one-line
  description; plain text with numbered options otherwise; open questions in plain text;
  act only on an answer that maps to an option or gives the requested input, else ask
  again; only the driving session asks. Verify: `grep -n "AskUserQuestion" skills/ep-orchestrate/SKILL.md`
  finds the subsection, and the "Structured user questions" requirement text and its
  "Gate pause without a question tool" and "Answer outside the options" scenarios in
  `openspec/changes/update-ep-orchestrate-ask-tool/specs/ep-orchestrate/spec.md` map to it.
- [x] 1.2 Reword the question points in `skills/ep-orchestrate/SKILL.md` to point at
  "Asking the user" and name their options (D2): step 1.3 (continue / different name),
  step 1.6 (continue on the existing branch / stop; another branch name through free
  text), step 4 (the planner's question; its options when it names 2 to 4), step 9
  (deliver as a stack / keep the local branch; `ep-stack split`'s approval still applies).
  Verify: the "Name collides with an existing change", "Work branch already exists",
  "Plan needs input", and "Large change offered as a stack" scenarios each map to text in
  the matching step, and `grep -n "ask" skills/ep-orchestrate/SKILL.md` shows no question
  point left without a reference to "Asking the user".
- [x] 1.3 Update step 5 (gate) in `skills/ep-orchestrate/SKILL.md` (D2, D3): print the score
  report and hard-to-undo elements as text, write `decision: paused` to the state file,
  then ask Approve / Revise / Stop through "Asking the user", for both the hard-to-undo
  and the score pause; outcome `paused_at_gate` only when the run ends at the pause.
  Verify: the "Gate pause with a question tool" and "Interrupted at a gate question"
  scenarios map to text, and the gate rows in `skills/ep-orchestrate/references/confidence.md`
  ("Gate decision") still agree with step 5.
- [ ] 1.4 In `skills/ep-orchestrate/references/briefs.md`, add to "Rules for every phase":
  never ask the user or call a question tool; a choice the phase cannot make becomes its
  `blocker` (D4). Leave `## stack` unchanged. Verify: the "Phase subagent needs an answer"
  and "Agent without subagents" scenarios map to text in `briefs.md` and `SKILL.md`
  ("How phases run"), and `git diff -- skills/ep-orchestrate/references/briefs.md` touches
  only "Rules for every phase".

## 2. Integration

- [ ] 2.1 Run `scripts/check-shared.sh` and verify that it passes, and check that
  `README.md` and the `description:` frontmatter of `skills/ep-orchestrate/SKILL.md` are
  unchanged (`git diff main -- README.md` is empty and the frontmatter line is identical) (D5).
