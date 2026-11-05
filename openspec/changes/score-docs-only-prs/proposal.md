# Proposal

## Why

`ep-babysit-pr` can never merge a PR that only changes documentation or planning files: the "tests added or touched" item can't be met when there is no code to test, so the score caps at 55 without OpenSpec (90 with it only if every other item is met). PR #1 in this repo, which archives a change and adds main specs, stopped at 55/100 for that reason alone.

## What Changes

- `ep-babysit-pr` (modification): when every file in the PR diff is documentation or planning, the tests item counts as met (not applicable) instead of failed, and the score report says so.
- "Documentation or planning" is decided from paths only, so the score stays evidence-based. Agent instruction files (anything in a skill folder, `AGENTS.md`, `CLAUDE.md`, `.claude/**`) count as behavior, not documentation.
- No new outward effect on GitHub: merges still need every hard gate, a score of at least 85, and GitHub's mergeable state.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `ep-babysit-pr`: the confidence score treats test evidence as not applicable for documentation-only PRs.

## Impact

- `skills/ep-babysit-pr/references/score.md`, `skills/ep-babysit-pr/SKILL.md` (score step).
- Docs-only PRs can now auto-merge when the review round finds no critical or major issues. Changes to skill instructions still need test evidence, so they are not auto-merged by this rule.
