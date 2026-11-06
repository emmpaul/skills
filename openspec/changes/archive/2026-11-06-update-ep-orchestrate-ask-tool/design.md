# Design

## Context

See proposal.md (Why). Today `skills/ep-orchestrate/SKILL.md` asks the user at these points,
all in the driving session:

| Point | Current text | Options |
|---|---|---|
| step 1.3 | "ask whether to continue that change or pick a different name" | continue / different name |
| step 1.6 | "If that branch exists, ask." | none stated |
| step 4 | "On `blocker: needs input`, ask the user the question and re-run." | none stated |
| step 5 | hard-to-undo pause and score < 85 pause: "offer: approve, revise ..., or stop" | approve / revise / stop |
| step 9 | "Otherwise offer stacked delivery and follow `briefs.md#stack`." | none stated |

Not questions, and left as they are: the `needs_openspec` and `dirty_tree` stops, Resume step 0
("stop and ask the user to switch back", an instruction followed by a stop), apply and fix
blockers, and "With `--workflow` but no Workflow tool, say so". `briefs.md#stack` Part 1 hands
the approval to `ep-stack split`, which asks under its own rules; Part 2 uses
`ep-stack retarget`'s own confirmation.

Phase workers already cannot ask in the plan brief ("You cannot ask the user questions"); the
other briefs never ask but do not say so.

Claude Code's `AskUserQuestion` takes 1-4 questions, each with a short header, the question
text, and 2-4 options (label and description); the user can always answer "Other" with free
text. It may be missing in other hosts and in non-interactive runs.

## Goals / Non-Goals

**Goals:**
- Every question the orchestrator asks uses the structured tool when the host offers it.
- The skill stays host-agnostic: the tool is named conditionally, as the Workflow tool is, and
  plain text is the fallback.
- No change to what each question decides or to the run's outcomes.

**Non-Goals:**
- Changing the questions of `ep-stack`, `ep-babysit-pr`, `ep-commit`, or any other skill.
- New question points, or turning stops (dirty tree, wrong branch on resume) into questions.
- Adding the tool to `briefs.md` phases: they never ask.

## Decisions

**D1. One rule, stated once, referenced at each point.** Add a short "Asking the user"
subsection to `SKILL.md` (after "Hard rules", before "Usage"): ask through the host's
structured question tool (`AskUserQuestion` in Claude Code) when available, one question per
decision, with the options listed for that point, each option a short label plus a one-line
description; without the tool, ask in plain text with the options numbered and wait. Act only
on an answer that maps to an option or gives the requested input; otherwise ask again. Each
question point then says "ask (see Asking the user)" and names its options.
*Alternative:* repeat the tool instructions at every point. Rejected: five copies drift.

**D2. Options per point** (conservative: same decisions as today, made explicit):
- 1.3 name collision: `Continue <change>` / `Use a different name` (the name is then given
  through "Other" or a follow-up plain question).
- 1.6 existing branch: `Continue on <branch>` (switch to it with `git switch`, no new branch;
  the clean-tree check has already passed) / `Stop`. Stop ends the run before the state file
  exists, like the other step-1 stops. A typed answer that is neither option is asked again
  (no other branch is created). This is the conservative reading of today's bare "ask":
  nothing is created or deleted without the answer.
- 4 needs input: the planner's question as written. When the blocker names choices (2-4),
  they become the options; otherwise the question is open and goes as plain text even when
  the tool exists, since the tool needs at least two options.
- 5 gate pause: `Approve` / `Revise` / `Stop`, for both the score pause and the hard-to-undo
  pause. The score report (and the named hard-to-undo elements) is printed as text first;
  the question carries only the decision.
- 9 large change: `Deliver as a stack` / `Keep the local branch`. On `Deliver as a stack`,
  `briefs.md#stack` runs and `ep-stack split`'s own approval still applies.

**D3. Paused state is written before asking.** At a gate pause, write `decision: paused`
(and the score fields) and `outcome: paused_at_gate` to the state file, and print the
report with its summary block, before calling the tool. An interrupted session has then
already recorded the pause and its summary, and resumes at the same question (Resume step 4
already re-asks a `paused` decision). On Stop the outcome stays; on Approve,
`decision: approved` and `outcome` is cleared; on Revise, `outcome` is cleared and the
gate re-runs as today.

**D4. Phases never ask.** Add to `briefs.md` "Rules for every phase": "Never ask the user or
call a question tool. A choice you cannot make becomes your `blocker`; the orchestrator asks."
The plan brief's existing wording stays. `briefs.md#stack` Part 1 runs in the driving session
and its approval belongs to `ep-stack`, so it is untouched.

**D5. No frontmatter or README change.** The description lists what the skill does, not how
it asks; the README row mirrors the description.

## Risks / Trade-offs

- [The host's tool changes shape or name] → the skill names `AskUserQuestion` only as the
  Claude Code example and describes the behavior generically, so any structured question tool
  fits and the plain-text path always works.
- [A non-interactive run cannot answer a question] → unchanged from today: the run stops at
  the question; for the gate, `decision: paused` is already recorded (D3).
- [Free-text "Other" answers are ambiguous] → act only on a clear match, else ask again.
- [Installed copies under `~/.claude/skills/` diverge from `skills/`] → out of scope; users
  update with `npx skills add`.
