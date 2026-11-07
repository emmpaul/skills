# Proposal

## Why

The Claude Code team's post "How the Claude Code team does code review" (claude.dev, Oct 2026) describes a review pipeline that more than doubled merged PRs while cutting reverts by over 40%. `ep-review`, `ep-babysit-pr`, and `ep-orchestrate` already cover its basics: parallel dimensions, verification before reporting, a 3-round cap, and a fresh-context review. They lack the parts the post credits with cutting noise and review rounds. Today one verifier decides each finding. Bugs that predate the PR are either dropped or blamed on its author. Every round re-reviews the whole diff, so a review can keep flagging findings it already reported. Nothing sets merge risk from the change itself. And nothing measures the reviewer against real incidents. This matters more because `ep-babysit-pr` acts on every finding automatically: as the post notes, noise costs most when the author is an agent.

## What Changes

**`ep-review` (modification)**
- Verifier voting: each candidate finding goes to 3 independent verifiers and is reported only when at least 2 confirm it. Without subagents, the existing single inline verification stays, and the summary records which path ran.
- Pre-existing findings: a bug in code the diff touches or calls, but did not introduce, is reported with the tag `pre-existing`. It never counts toward the blocking `verified:` counts, so callers do not ask the author to fix it.
- Bug class: a finding names its class and lists every other instance in the diff (`instances:`), so a fix covers them all.
- Intent and root cause: the review reads the PR title, body, and commits. For a bug fix, it checks that the fix reaches the root cause.
- `REVIEW.md`: when the target repo has one (repo root or `.github/`), the review follows it. The file can list paths to skip, cap minor findings, add risk paths, and name trusted authors. Breaks of `CLAUDE.md`/`AGENTS.md` conventions, and lines in those files the diff makes stale, are reported as correctness findings.
- Diff-only re-review: `--since <sha>` reviews only the commits after `<sha>`. `--known <file>` lists findings already reported. Known findings are re-checked rather than reported again, and `--comment` never re-posts a finding already on the PR.
- Risk tier: every review classifies the change as `low`, `medium`, or `high` from the paths it changes and the rules in `REVIEW.md`, with reasons. It can raise the tier, never lower it, when the change needs a person anyway.
- Report: the first line gives a count of findings to fix, or says plainly "Nothing to fix." The summary block gains `pre_existing`, `risk`, `risk_reasons`, `verification`, and `scope` lines. Existing lines keep their meaning.

**`ep-babysit-pr` (modification)**
- Rounds 2 and 3 run `ep-review --since <last reviewed head> --known <previous findings>`. A round runs in full again when a base sync landed since the last review.
- Pre-existing findings are listed in the report but not fixed, and they do not affect the score.
- New risk gate: low risk merges as today. Medium risk needs the user's explicit yes in the session for the exact head sha, and a new push needs a new yes. High risk also needs an approving GitHub review of that head from a human other than the PR author. Bot and agent approvals never count.
- When the round cap stops the run, the summary comment asks the author to step back and reconsider the approach.

**`ep-orchestrate` (modification)**
- Review rounds 2 and 3 are diff-only with known findings, and pre-existing findings do not make a round unclean.
- Fix rounds fix every listed instance of a bug class.
- The `--workflow` path uses 3 voter agents instead of up to 5 verify agents. It now uses at most 7 agents, down from 9.

**`ep-open-pr` (modification)**
- The body gains a `## Risk` section (tier and reasons, using the same rules as `ep-review`).
- `## How to test` becomes `## Testing`, with what was actually run and its result (or a plain "Not run"), followed by the steps to test.
- `## Reversibility` gains a "How to revert" line.
- UI screenshots (new behavior): when the branch changes UI files, the skill starts the app's documented dev or preview command (after confirmation), takes screenshots of the affected pages with a browser the host already has (a browser tool, or Playwright already installed in the project; it never installs one), and pushes the PNGs to an orphan `ep-pr-assets` branch. The body gets a `## Screenshots` section linking them. When capture is not possible, the section says why. `--no-screenshots` skips this step.

**`ep-review-evals` (new skill)**
- `collect`: finds merged PRs that were later reverted or fixed forward (through git blame of the fix lines) and proposes incident cases, plus a sample of clean PRs. Nothing is saved until the user confirms or edits each case.
- `run`: runs `ep-review` on every case in a temporary worktree. It scores recall (an incident's bug found at its file and lines) and noise (critical or major findings on clean PRs), and saves a labelled run.
- `compare`: says whether to keep a reviewer change: keep only if recall goes up and noise does not.
- `noise`: reads how authors answered findings `ep-review` posted (fixed, wrong, intentional, did not matter, unanswered) and suggests `REVIEW.md` lines for repeat false positives. It does not write them.

**Shared risk rules (tooling)**
- `shared/risk.md` holds the tier rules. `scripts/sync-shared.sh` and `scripts/check-shared.sh` copy and check it as `references/risk.md` in `ep-review`, `ep-open-pr`, and `ep-babysit-pr`.

**README**: add `ep-review-evals`, describe the risk gate in the auto-merge safety note, and update the install commands.

**Outward effects on GitHub**
- `ep-babysit-pr`: no new kind of write. It merges *less often* without asking: medium and high risk PRs now wait for the user (and, for high risk, a human GitHub approval). The round-cap summary comment exists today; only its text changes.
- `ep-review --comment`: same single PR review as today. It now posts fewer comments, because it skips findings already posted.
- `ep-open-pr`: same PR create or edit as today, with more body sections. **New push:** when UI is touched, it pushes a commit of screenshots to the `ep-pr-assets` branch, and creates that orphan branch on first use. It confirms first, unless `--screenshots` pre-approves it. That push is never a force-push and never touches the PR branch or the default branch.
- `ep-review-evals`: read-only on GitHub. It writes case and run files to the working tree only after confirmation, and never commits or pushes.

## Capabilities

### New Capabilities
- `ep-review-evals`: building a confirmed eval set of incident and clean PRs from a repo's history, scoring `ep-review` against it, comparing runs, and measuring how authors answered posted findings.

### Modified Capabilities
- `ep-review`: verifier voting, pre-existing tag, bug class instances, intent and root cause, `REVIEW.md` and convention checks, diff-only re-review with known findings, risk tier, count-first report and extended summary block.
- `ep-babysit-pr`: diff-only later rounds, pre-existing findings left unfixed, risk-tier merge gate, step-back text at the round cap.
- `ep-orchestrate`: diff-only later rounds, pre-existing findings ignored for cleanliness, class-wide fixes, voter-based Workflow budget.
- `ep-open-pr`: Risk section, Testing section with observed evidence, How to revert line, UI screenshots pushed to an assets branch and linked in the body.

## Impact

- Files: `skills/ep-review/SKILL.md` and `references/dimensions.md`; `skills/ep-babysit-pr/SKILL.md` and `references/score.md`; `skills/ep-orchestrate/SKILL.md` and `references/briefs.md`; `skills/ep-open-pr/SKILL.md`; new `skills/ep-review-evals/`; new `shared/risk.md`; `scripts/sync-shared.sh` and `scripts/check-shared.sh`; `README.md`.
- Behavior change for `ep-babysit-pr` users: most PRs that touch code are medium risk, so in repos without a `REVIEW.md` marking low-risk paths, babysit now asks before it merges. The user chose this ("ask in session").
- Cost: voting adds 2 verifier runs per review. Diff-only later rounds offset part of that. `ep-review-evals run` runs a full review per case and confirms the case count before it starts.
- Summary block consumers (`ep-babysit-pr`, `ep-orchestrate`) parse by key, so the new lines are additive. `verified:` now excludes pre-existing findings.
- Overlap: the in-progress changes `add-ep-hygiene-skills` (README, `ep-spec-drift` reuses the spec method) and `add-ep-after-merge-skills` (modifies `ep-babysit-pr` after a merge) touch nearby text. Requirements do not conflict, but README edits and the after-merge babysit step may need a manual merge.
