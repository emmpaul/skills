# Design

## Context

See proposal.md (Why). Current state the approach has to fit:

- `skills/ep-commit/SKILL.md` has a hard rule "Never push unless the user asks", six numbered steps (gather, scope, group and present plan, write, commit, verify and report), and the synced `scripts/context.sh`, which already reports upstream and ahead/behind.
- `ep-open-pr` already has the push rules this skill needs (step 3: `git push -u origin HEAD` without upstream, `git push` when ahead, skip when not ahead, stop on rejection; "Plain pushes only").
- `ep-orchestrate` keeps regular changes local (hard rule and spec "No outward effects for regular changes"), and its phases commit through `ep-commit` when available, otherwise through the condensed rules in `references/briefs.md#commit`, which say "Never push unless the user asks".
- Every other caller (`ep-babysit-pr`, `ep-fixup`, `ep-ci-debug`, `ep-sync`) cites "ep-commit conventions" for message rules and pushes, or not, under its own gates; `ep-open-pr`, `ep-sync`, `ep-stack`, `ep-qa`, `ep-a11y` only offer the skill to the user.
- `ep-commit` prints no summary block, and no `<!-- ep-… -->` block names it.

## Goals / Non-Goals

**Goals:**
- One skill folder, `skills/ep-commit-and-push/`, that commits as before and then pushes.
- Every caller that must stay local keeps pushing nothing, with mixed old and new installs failing safe.
- No stale `ep-commit` reference outside archived changes.

**Non-Goals:**
- No change to commit grouping, message format, scope, task ticking, or attribution rules beyond ordering them before the push.
- No new summary block, and no change to any existing one.
- No change to how `ep-babysit-pr`, `ep-ci-debug`, or `ep-fixup` push; they keep citing the conventions and pushing under their own gates.
- Archived changes under `openspec/changes/archive/` are history and stay as they are.

## Decisions

### D1. The skill pushes after committing (the user's choice)

The user decided that `ep-commit-and-push` pushes after committing, not just commits. This is settled input, not a planning default. The push becomes a new step after verification: commit, verify no attribution (amending the unpushed commit when needed), then push. Ordering the push last keeps the amend-to-strip-attribution step legal, since amending is only allowed on unpushed commits.

### D2. Push rules follow `ep-open-pr` step 3, with an explicit target

- The target is the remote branch with the current branch's name. No upstream and `origin` exists: `git push -u origin HEAD:refs/heads/<branch>`. Upstream with the branch's name: `git push <remote> HEAD:refs/heads/<branch>`. No upstream and no `origin`: push nothing and report it.
- Every push names its target with the explicit refspec `HEAD:refs/heads/<branch>`, never a bare `git push`: a bare push takes its destination from git config, so `push.default=matching` would also push an unpushed local `main` past the default-branch gate, and a configured `+refs/heads/*:refs/heads/*` push refspec would force-push. The explicit refspec makes the pushed ref the gated ref.
- Plain pushes only: never `--force`, `--force-with-lease`, or `+refspec`; hooks run, `--no-verify` only on the user's request.
- Rejected push or failing pre-push hook: stop, keep the commits, report the cause, suggest `ep-sync` for a remote that moved ahead. No pull or rebase from this skill.
- Push only when this run created a commit. "Nothing to commit" still stops without pushing, even with unpushed commits on the branch: pushing work the user did not hand to this run would be a surprise.

Alternative considered: delegate the push to `ep-open-pr`'s rules by reference. Rejected because skills install folder by folder and may only reference files inside their own folder; the rules are short enough to state in the skill.

### D3. Push gate: the plan prompt, plus confirmations for the riskiest targets

The push is an outward effect, so it gets an explicit gate (config rule for design). The existing plan prompt (step 3) is that gate: the plan now names the target branch and remote and how many commits the push sends, including earlier unpushed ones. When the user says "just commit", that instruction covers the push too, since they invoked a commit-and-push skill. The exceptions ask even when the user said to just commit:

- **Default branch.** Pushing straight to it is the hardest to undo, so the skill always asks before pushing the default branch. An unknown or guessed default branch also asks, whatever the current branch: without knowing the default, the skill cannot tell a feature push from a default-branch push.
- **Upstream named differently from the branch** (for example `fix` made with `git switch -c fix origin/main`). The skill never pushes to the upstream's branch; it asks whether to push the branch under its own name with `git push -u <remote> HEAD:refs/heads/<branch>`, which creates that remote branch and points the upstream at it, and keeps the commits local on a no.

Alternative considered: always ask before every push. Rejected: it turns the skill back into `ep-commit` plus a prompt, contrary to the user's choice.

### D4. Callers that must stay local use `--no-push`

`--no-push` (or the user or a calling skill saying to commit without pushing) runs every commit step and skips the push step, reporting the commits as local. Flag style follows `ep-open-pr`'s `--no-screenshots`.

- `ep-orchestrate`: every phase that commits through the skill passes `--no-push` together with "just commit". In `references/briefs.md` the general rule ("When a phase commits through `ep-commit`, tell it the intended commit and to just commit") becomes "...the intended commit, to just commit, and `--no-push`", and the apply, deadcode, fix, and plan steps that invoke the skill inherit it from that rule. The condensed `#commit` fallback keeps "never push": its "Rules that must match" list gains one line saying the skill pushes by default and that phases always run it with `--no-push`, so the fallback (no push) still states the same behavior the phases get from the skill. This keeps the "Condensed fallback copies" scenario of `skill-authoring` true.
- `ep-babysit-pr`, `ep-ci-debug`, `ep-fixup`, `ep-sync`: they cite "conventions" and do not invoke the skill, so only the name changes. Their own push gates are unchanged.
- `ep-open-pr`, `ep-sync`, `ep-stack`, `ep-qa`, `ep-a11y`: they offer the skill to the user; the user sees the push in the skill's plan and can decline or ask for `--no-push`. `ep-open-pr` needs nothing more: after the skill pushes, its own push step sees `ahead == 0` and skips.

Alternative considered: a separate commit-only skill for callers. Rejected: a second model-invoked skill pays permanent context load for its description, and the commit rules would live in two places.

### D5. Rename without an alias

The folder moves with `git mv skills/ep-commit skills/ep-commit-and-push`, keeping history. No `ep-commit` stub remains: a stub would cost a permanent description in context and keep two names for one behavior. Mixed installs fail safe: an old `ep-orchestrate` looking for `ep-commit` does not find it and falls back to its condensed rules, which never push; a new `ep-orchestrate` without `ep-commit-and-push` installed does the same.

### D6. Specs: new capability plus removal

OpenSpec has no capability rename, so the change adds `ep-commit-and-push` with every carried-over requirement (the push rule removed from "Never rewrite published history" and replaced by the push requirements) and removes every `ep-commit` requirement with a Reason and Migration; `retire_capabilities: true` in `.openspec.yaml` lets archive delete the emptied spec. The other capabilities get MODIFIED blocks that only swap the name, except `ep-orchestrate`, which also requires `--no-push`. The `skill-authoring` requirement "Rewrites preserve skill interfaces" covers wording rewrites; this change alters the name and behavior on purpose, and records that here and in the proposal as **BREAKING**.

### D7. Description and prose follow `writing-for-agents`

The new description front-loads the behavior and keeps one trigger per branch: commit, commit and push, split changes into commits, write commit messages. The hard rule "Never push unless the user asks" is replaced by positively worded rules (push after committing with a plain push; `--no-push` commits only; ask before pushing the default branch). The push step ends on a completion criterion: the remote branch matches local `HEAD`, or the report names why nothing was pushed. The description stays valid YAML (no unquoted `: ` sequence), as fixed for `ep-orchestrate` in 199df01.

### D8. In-flight changes and config name the new skill

`openspec/config.yaml`'s naming example and the three active changes (`add-ep-front-door-skills`, `add-ep-hygiene-skills`, `add-ep-after-merge-skills`) name `ep-commit-and-push`, so their later implementation does not reintroduce the old name. Edits there are name swaps only.

## Risks / Trade-offs

- [A user expecting the old commit-only behavior pushes unfinished work] → The plan prompt names the push; the README migration note states the new behavior and `--no-push`; the default branch always asks.
- [A caller forgets `--no-push` and a regular `ep-orchestrate` run pushes] → The flag lives in the single general rule in `briefs.md`, and task 2.1's check greps every invocation site in `ep-orchestrate`.
- [Existing installs keep a stale `ep-commit` folder that still triggers on "commit"] → The README migration note gives the remove-then-add commands; a stale `ep-commit` keeps its old commit-only behavior, so it pushes nothing unexpected.
- [Archive refuses to empty `openspec/specs/ep-commit/`] → The change's `.openspec.yaml` sets `retire_capabilities: true`, so archive deletes that spec (checked in a scratch copy with OpenSpec 1.16.0).

## Migration Plan

1. Land the change; the README tells existing users to run `npx skills remove ep-commit`, then `npx skills add emmpaul/skills --skill ep-commit-and-push` (with `-g` for global installs).
2. Rollback: revert the change's commits; the folder moves back with history, and callers name `ep-commit` again.
