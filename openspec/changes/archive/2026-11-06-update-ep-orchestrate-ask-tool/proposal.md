# Proposal

## Why

`ep-orchestrate` asks the user questions at several points (a name that collides with an
existing change, an existing work branch, a plan that needs input, a gate pause, the offer of
stacked delivery), but it asks them as plain prose. In Claude Code the host has a structured
question tool, `AskUserQuestion`, that shows the choices as a selectable list, keeps the answer
unambiguous, and makes the pause visible. Plain prose leaves the user to type "approve" or
"revise" by hand, and the agent then has to interpret free text. The skill must stay portable,
so the structured tool has to be optional, with the current plain-text question as fallback.

## What Changes

- **Modified** `ep-orchestrate`:
  - New rule for every question the driving session asks the user: when the host offers a
    structured question tool (`AskUserQuestion` in Claude Code), ask through it, with the
    question's fixed options; otherwise ask in plain text with the same options, numbered,
    and wait for the reply.
  - Each question point names its options:
    - name collision (step 1.3): continue the existing change, or use a different name;
    - existing work branch (step 1.6): continue on the existing branch, or stop;
    - plan `blocker: needs input` (step 4): the planner's question, with its options when it
      names them;
    - gate pause (step 5, for a low score and for a hard-to-undo element): approve, revise,
      or stop;
    - large change (step 9): deliver as a stack, or keep the reviewed local branch.
  - Questions come only from the driving session. Phase subagents never ask the user (the
    plan brief already says so; the rule now covers every phase), and the question tool is
    never called from inside a phase.
  - A gate pause records `decision: paused` in the state file before the question is asked,
    so an interrupted session resumes at the same question.
- Questions that other skills ask (`ep-stack split`'s plan approval, `ep-stack retarget`'s
  confirmation, `ep-commit`'s prompts) are unchanged: they belong to those skills.
- No change to stops that are not questions (dirty tree, resume on the wrong branch, apply
  blockers, `--workflow` without a Workflow tool): they keep reporting and stopping.

Outward effects on GitHub: none. The change only alters how the skill asks the user locally.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `ep-orchestrate`: adds a requirement that user questions use the host's structured question
  tool when available, with a plain-text fallback, and are asked only by the driving session.

## Impact

- `skills/ep-orchestrate/SKILL.md`: a new "Asking the user" rule and the wording of each
  question point (steps 1.3, 1.6, 4, 5, 9).
- `skills/ep-orchestrate/references/briefs.md`: "Rules for every phase" gains the rule that
  phase workers never ask the user.
- `README.md`, the frontmatter description, `shared/context.sh`, and the other skills are
  unchanged.
