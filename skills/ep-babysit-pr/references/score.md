# Merge confidence score

The score is computed only from verifiable evidence. Never add, remove, or adjust points
based on your own sense of how good the change is.

## Hard gates

All must pass, regardless of score. Any failure means **no merge**.

| Gate | Check | Source |
|---|---|---|
| Required checks green | every required check has conclusion SUCCESS, NEUTRAL, or SKIPPED; if the repo has no required checks (`gh pr checks --required` reports none), every check must pass instead | `gh pr checks <n> --required` |
| No conflicts | `mergeStateStatus` is not `DIRTY` | `gh pr view <n> --json mergeStateStatus` |
| No unresolved threads | every review thread has `isResolved: true` | GraphQL `reviewThreads` (see SKILL.md) |
| No changes requested | `reviewDecision` is not `CHANGES_REQUESTED` | `gh pr view <n> --json reviewDecision` |

## Evidence weights

### With OpenSpec (repo has an OpenSpec root and the PR maps to an active change)

| # | Evidence | Weight | Met when | Source |
|---|---|---|---|---|
| 1 | No verified critical/major findings | 35 | final round summary has `critical=0 major=0` | `ep-review-summary` block |
| 2 | Minor findings fixed or waived | 20 | every verified minor finding from the final round is fixed by a later commit, or waived in a PR comment with a reason | review summary + commits + comments |
| 3 | Spec conformance passed | 20 | `spec_conformance: passed` in the final summary | `ep-review-summary` block |
| 4 | Tasks complete | 15 | `tasks_done == tasks_total` for the change | context probe |
| 5 | Tests added or touched | 10 | the PR diff changes at least one test file covering changed code (paths under `test/`, `tests/`, `__tests__/`, `spec/`, or files named `*test*` / `*spec*`), or the PR is documentation-only (below) | `gh pr diff <n> --name-only` |
|   | **Total** | **100** | | |

### Without OpenSpec (no root, or no matching change)

Items 3 and 4 are dropped; their 35 points move to test evidence.

| # | Evidence | Weight | Met when |
|---|---|---|---|
| 1 | No verified critical/major findings | 35 | as above |
| 2 | Minor findings fixed or waived | 20 | as above |
| 5 | Tests added or touched | 45 | as above, including the documentation-only rule |
|   | **Total** | **100** | |

Items are all-or-nothing: an item scores its full weight when met, 0 otherwise. If the
final round had zero minor findings, item 2 is met.

### Documentation-only PRs

A PR with no code has nothing to test, so item 5 counts as **met (not applicable)** when
the PR is documentation-only. Decide from paths alone (`gh pr diff <n> --name-only`; for
renames, check both the old and new path):

- **Every** changed path matches one of: `*.md`, `*.mdx`, `*.rst`, `*.txt`, `docs/**`,
  `openspec/**`, `LICENSE*`, `CHANGELOG*`; and
- **no** changed path is an agent instruction file: `AGENTS.md` or `CLAUDE.md` at any depth,
  anything under `.claude/` or `.agents/`, or any file in or below a directory that
  contains a `SKILL.md` (the whole skill folder, including `references/` and `scripts/`).

If either condition fails, item 5 needs test evidence as usual. Only item 5 changes: the
review round, the other items, the gates, and the threshold apply unchanged.

## Threshold

Merge is allowed only when **score >= 85**, all hard gates pass, the merge state allows
it (below), and the review the score uses ran on the current head (`last_review.head`
equals `headRefOid`). Note that with OpenSpec, missing items 4+5 (25) or item 3 alone (20) is enough
to block; without OpenSpec, missing tests (45) blocks.

## Report format

Print after every round, and include in the PR summary comment:

```
Merge confidence: 90/100 (threshold 85)
Hard gates: required checks ✓ | no conflicts ✓ | threads resolved ✓ | no changes requested ✓
  [✓] 35  No verified critical/major findings (round 2: critical=0 major=0)
  [✓] 20  Minor findings fixed or waived (2 fixed in 3f2a1c9)
  [✓] 20  Spec conformance passed
  [✗]  0/15 Tasks complete (7/8)
  [✓] 10  Tests added or touched (tests/test_auth.py)
```

For a documentation-only PR, item 5 reads:

```
  [✓] 45  Tests added or touched (n/a: no code changed; 12 files, all docs/planning)
```

## Merge-state mapping

From `gh pr view <n> --json mergeStateStatus`:

| `mergeStateStatus` | Action |
|---|---|
| `CLEAN`, `HAS_HOOKS` | merge if score >= 85 and gates pass |
| `UNSTABLE` | non-required checks are failing: treat them as a fix round; merge allowed if score >= 85 and gates pass |
| `BLOCKED` | wait (protection, e.g. required approval); notify the user once; re-check each tick |
| `BEHIND` | sync with the base through `ep-sync --caller ep-babysit-pr` (or `side-paths.md#sync`): merge and merge audit; on `synced`, push with a plain push, wait for checks, and re-evaluate; needs-update adaptations are a fix round; `needs_decision` stops and notifies the user without pushing; review-class items go in the next status report and review round |
| `DIRTY` | same sync as `BEHIND`, as a fix round: the merge resolves conflicts that keep both sides' intent and stops with `needs_decision` on incompatible ones (never rebase a pushed branch, never force-push) |
| `UNKNOWN` | GitHub is still computing: retry for 3 ticks, then stop and report |
| `DRAFT` | do not merge; tell the user the PR is a draft and stop unless they ask to mark it ready |

## Merge command

```bash
method=$(gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed \
  --jq 'if .squashMergeAllowed then "--squash" elif .mergeCommitAllowed then "--merge" else "--rebase" end')
gh pr merge <n> $method --delete-branch --match-head-commit <last_review.head>
```

`--match-head-commit` makes GitHub refuse the merge when the head moved after the reviewed
commit.

Prefer the repo's configured default when it is known (for example from a
`CONTRIBUTING.md` or the user's instruction); otherwise use the first allowed method in the
order above. Never pass `--admin`. Do not use `--auto`: the skill itself decides when to merge.
