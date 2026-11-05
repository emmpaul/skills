# Design

## Context

The score rubric lives in `skills/ep-babysit-pr/references/score.md`. Item 5 ("tests added or touched", 10 points with OpenSpec, 45 without) is met only when the diff touches a test file. A PR with no code has nothing to test, so the item always fails.

## Goals / Non-Goals

**Goals:** let documentation and planning PRs reach the threshold; keep the decision deterministic and path-based.

**Non-Goals:** changing weights, the threshold, or the hard gates; judging whether a code change "needs" tests.

## Decisions

### D1. Path-based docs-only test

A PR is documentation-only when every changed path (`gh pr diff <n> --name-only`, including both sides of renames) matches one of: `*.md`, `*.mdx`, `*.rst`, `*.txt`, `docs/**`, `openspec/**`, `LICENSE*`, `CHANGELOG*`; and none is an agent instruction file: `**/AGENTS.md`, `**/CLAUDE.md`, anything under `.claude/` or `.agents/`, or any file in or below a directory that contains a `SKILL.md` (the whole skill folder, including its references and scripts).
- Alternative: ask the reviewer whether tests are needed. Rejected: that is self-assessed confidence, which the spec forbids.

### D2. Not applicable counts as met

For a docs-only PR the item scores its full weight and the breakdown shows `n/a: no code changed`. Every other item and gate is unchanged, so a docs-only PR still needs a clean review round.

### D3. Agent instruction files are behavior

In skill and agent repos, prompt files and the references they load are the product. They stay outside the docs-only set, so changes to them still need test evidence (or a human merge).

## Risks / Trade-offs

- [A behavior-relevant file with a docs extension slips through] → the exclusion list covers the agent files this repo uses; the review round still runs on every PR.
- [Docs-only PRs auto-merge with no human look] → same gates as before; branch protection requiring approval still applies where configured.
