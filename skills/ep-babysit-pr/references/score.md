# Merge confidence score

Score only from verifiable evidence: every point traces to a source in the tables below.
Your own sense of how good the change is never adds, removes, or adjusts points.

## Hard gates

Every gate must pass, whatever the score. Any failure means **no merge**.

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
the PR is documentation-only: **every** changed path, with both sides of each rename, is
documentation-only by the rule in [`risk.md`](risk.md#documentation-only-paths), the same
rule the risk tier uses. List the paths as `risk.md` does, never with
`gh pr diff <n> --name-only` (it lists only a rename's new path):

```bash
gh api repos/{owner}/{repo}/pulls/<n>/files --paginate \
  --jq '.[] | .filename, (.previous_filename // empty)'
```

If any path is not, item 5 needs test evidence as usual. Only item 5 changes: the
review round, the other items, the gates, and the threshold apply unchanged.

## Threshold

Merge is allowed only when **score >= 85**, all hard gates pass, the merge state allows
it (below), the review the score uses ran on the current head (`last_review.head`
equals `headRefOid`), and the [risk gate](#risk-gate) passes. With OpenSpec, missing
items 4+5 (25) or item 3 alone (20) is enough to block; without OpenSpec, missing tests
(45) blocks.

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

## Risk gate

Evaluated after the score and the other merge conditions, just before the merge call. The
tier is the `risk:` line of the latest `ep-review-summary` (`last_review.summary`), which
ran on the current head. A summary with no `risk:` line (an older `ep-review`) counts as
`medium`. The tier rules themselves are in [`risk.md`](risk.md). Use the tier the review
reported as it is: this skill never lowers it.

| Tier | Needs | Recorded in state |
|---|---|---|
| low | nothing extra | nothing |
| medium | the user's yes for `headRefOid` | `human_ok: { "head": "<headRefOid>" }` |
| high | the user's yes for `headRefOid`, and a human approval of that head (below) | `human_ok`, and the approval's review id in the status report |

**The ask.** When `human_ok.head` does not equal `headRefOid`, ask one structured question
(the host's question tool when it has one, else a plain message) showing the tier, its
`risk_reasons`, the score breakdown, and the head sha, with three options:

- **Merge:** set `human_ok` to `{ "head": "<headRefOid>" }` and continue to the merge.
- **Wait:** do not merge; keep the loop running and ask again on the next attended run.
- **Stop:** do not merge; set `outcome: stopped: user declined merge` and stop.

Risk-gate notices use their own flag, `risk_notified` (the head sha last notified), not
`blocked_notified`: an earlier `BLOCKED` notice must not silence them, and a new head needs
a new notice.

A yes counts only for the head it named. Whenever `headRefOid` changes (a fix, a sync, a
reviewer's commit), clear `human_ok` to `null`, so the new head needs a new yes.

**Human approval (high only).** List the reviews:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --paginate \
  --jq '.[] | {id, state, commit_id, login: .user.login, type: .user.type, association: .author_association}'
```

An approval counts only when `state` is `APPROVED`, `commit_id` equals `headRefOid`,
`login` is not the PR author, `association` is `OWNER`, `MEMBER`, or `COLLABORATOR` (an
account with no standing on the repository, such as a drive-by approval on a public
repository, never counts), and `type` is `User` (an account of type `Bot`, or an app,
never counts, nor does any review this skill could post, since it never approves). With
no counting approval, do not merge: notify the user that a human approval of this head is
needed, once per head (skip it when `risk_notified` equals `headRefOid`, else send it and
set `risk_notified` to `headRefOid`), and wait as on `BLOCKED`.

**Unattended runs.** A run is **unattended** when any of these holds:

- no way to ask exists: the host has no question tool and the session takes no reply
  from the user (a headless or non-interactive run, such as `claude -p` or CI); or
- the run was started by a schedule rather than a session the user has open: a cloud
  routine, a cron job, or a scheduled agent; or
- the run is a `/loop` tick or wakeup that no user message started, even in an
  interactive session: the user may have walked away, so it cannot assume anyone will
  answer.

A run is **attended** only when the user's own message started it in this session: an
invocation they typed (including the first pass of `/loop ep-babysit-pr <n>`), or their
reply to a risk-gate notice. There, ask the question (it waits for the answer, which is
safe, because nothing merges meanwhile). An unattended run does not ask and does not
merge: it notifies the user with the tier, reasons, and head sha, once per head
(`risk_notified`, as above), and waits; later ticks on the same head stay silent. The next
attended run asks the question, and a user reply to the notice naming Merge, Wait, or
Stop counts as the answer.

The gate adds no GitHub write; it only removes merges.

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
order above. Merge with this explicit call, never `--admin` and never `--auto`: the skill
itself decides when to merge.

### Stacked PRs

A PR in a GitHub native stack merges through the async merge API instead: detection, the
bottom-layer rule, and every merge answer are in [`stacked.md`](stacked.md).
