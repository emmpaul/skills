# Proposal

## Why

Taking an OpenSpec change from idea to a reviewed branch is done by hand today. The user runs `/opsx:propose`, reads the plan, runs `/opsx:apply`, commits, reviews, and fixes, all in one session. That session's context fills up with diffs, test output, and artifact text, so later tasks and the review run with a degraded context or after a lossy compaction. The `ep-*` skills already provide the pieces (`ep-commit`, `ep-review`), but nothing chains them and the OpenSpec phases together, keeps the driving session lean, or decides when the plan is safe to implement without asking.

## What Changes

- Add `ep-orchestrate` (new): runs one OpenSpec change end to end, from a description or an existing change to a reviewed, committed local branch.
  - **Plan**: proposes the change (all artifacts) from a description, or picks up an existing change by name. New artifacts are committed on their own before any code changes.
  - **Confidence gate**: scores the plan from verifiable evidence (validation, scenario and task coverage, open questions, size, conflicts with other active changes). When it starts from a description it implements without asking if the score is at least 85. It always pauses when the change is a one-way door or would need a hard refactor to undo (for example a broad rename, a public interface change, a data or format migration, or a cross-cutting restructure), whatever the score.
  - **Apply**: implements tasks in batches, one task group per batch. Each task is committed through `ep-commit` conventions as soon as its verification passes (one commit per task, with its `tasks.md` tick), so progress can be followed and undone task by task in `git log`. A run never ends up as one or two large commits.
  - **Review**: runs `ep-review` on the branch and fixes verified findings, one commit per finding (or per shared root cause), for up to 3 rounds. It stops early when a round has no critical or major findings and spec conformance passes.
  - **Context awareness**: each phase and batch runs in a fresh subagent that reads the artifacts from disk and returns only a summary block. The driving session keeps a small state file and those summaries, never diffs or logs. The run can resume from the state file after a compaction or in a new session.
  - **Workflow path**: in Claude Code, when the user opts in with `--workflow`, the review-and-verify rounds run as a Workflow script. Without subagents, the phases run inline in sequence, with the same state file and checkpoints, and the skill suggests clearing context between phases.
  - **Regular changes** stop at a reviewed local branch, and the skill offers `ep-open-pr` and `ep-babysit-pr` as next steps.
  - **Large changes** (more than 6 task groups or 30 tasks, or a reviewed diff over 800 lines or 25 files) get an offer of stacked delivery. `ep-stack split` makes one layer per task group, which the per-task commits make clean to cut. After the user approves the stack plan, `ep-babysit-pr` lands the layers bottom up, with `ep-stack retarget` between layers. It stops at the first layer that does not merge.
  - Every run ends with an `ep-orchestrate-summary` block.
- Add the skill to the README skills table and install commands.

Outward effects on GitHub:
- Regular changes: none. The skill does not push, open PRs, comment, or merge. It creates a local branch when started on the default branch, and makes local commits with no model or tool attribution.
- Large changes, only after the user approves the stack plan: pushes the stack branches and opens one PR per layer (through `ep-stack`, which keeps its own confirmation), changes PR bases on retarget, and lets `ep-babysit-pr` push fixes, reply to comments, and merge each layer under its existing gates (score ≥ 85, no bypass, no force-push). Declining the plan pushes nothing.

## Capabilities

### New Capabilities
- `ep-orchestrate`: end-to-end orchestration of one OpenSpec change (plan, confidence gate, batched apply, review rounds) with fresh-context phases and a resumable state file.

### Modified Capabilities
<!-- None. ep-commit and ep-review are invoked as they are; their requirements do not change. -->

## Impact

- New files: `skills/ep-orchestrate/SKILL.md`, a synced `skills/ep-orchestrate/scripts/context.sh`, `references/confidence.md` (plan score and hard gates), and `references/briefs.md` (subagent briefs and summary formats for each phase).
- Modified: `README.md` (skills table, install commands).
- Unchanged: `shared/context.sh`, `ep-commit`, `ep-review`, and the other skills. `ep-orchestrate` calls `ep-commit` and `ep-review` by name when they are installed, and otherwise follows condensed steps in its own folder. Stacked delivery calls `ep-stack` and `ep-babysit-pr` by name and has no inline fallback: when either is missing, it does not push.
- Runtime: `git` and the `openspec` CLI are required. Without an OpenSpec root, the skill stops and says it needs one, and never runs `openspec init`. `gh` is optional for regular changes (used only by `ep-review` for base detection) and required for stacked delivery.
- Local effects: writes under `openspec/changes/<name>/`, edits code to implement tasks, creates a branch, makes commits, and keeps state in `.git/ep-orchestrate/<change>.json`.
- Sibling changes: `add-ep-front-door-skills` proposes `ep-start` (branch naming) and `ep-issue-to-change`. `ep-orchestrate` uses the same `<type>/<slug>` branch convention and does not depend on either being installed.
