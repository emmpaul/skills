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
the PR is documentation-only: **every** changed path (`gh pr diff <n> --name-only`; for
renames, both the old and new path) is documentation-only by the rule in
[`risk.md`](risk.md#documentation-only-paths), the same rule the risk tier uses.

If any path is not, item 5 needs test evidence as usual. Only item 5 changes: the
review round, the other items, the gates, and the threshold apply unchanged.

## Threshold

Merge is allowed only when **score >= 85**, all hard gates pass, the merge state allows
it (below), the review the score uses ran on the current head (`last_review.head`
equals `headRefOid`), and the [risk gate](#risk-gate) passes. Note that with OpenSpec, missing items 4+5 (25) or item 3 alone (20) is enough
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

## Risk gate

Evaluated after the score and the other merge conditions, just before the merge call. The
tier is the `risk:` line of the latest `ep-review-summary` (`last_review.summary`), which
ran on the current head. A summary with no `risk:` line (an older `ep-review`) counts as
`medium`. The tier rules themselves are in [`risk.md`](risk.md); this skill never lowers
the tier the review reported.

| Tier | Needs | Recorded in state |
|---|---|---|
| low | nothing extra | nothing |
| medium | the user's yes for `headRefOid` | `human_ok: { "head": "<headRefOid>" }` |
| high | the user's yes for `headRefOid`, and a human approval of that head (below) | `human_ok`, and the approval's review id in the status report |

**The ask.** When `human_ok.head` does not equal `headRefOid`, ask one structured question
(the host's question tool when it has one, else a plain message) showing the tier, its
`risk_reasons`, the score breakdown, and the head sha, with three options:

- **Merge:** set `human_ok` to `{ "head": "<headRefOid>" }` and continue to the merge.
- **Wait:** do not merge; keep the loop running and ask again on a later tick.
- **Stop:** do not merge; set `outcome: stopped: user declined merge` and stop.

A yes counts only for the head it named. Whenever `headRefOid` changes (a fix, a sync, a
reviewer's commit), clear `human_ok` to `null`, so the new head needs a new yes.

**Human approval (high only).** List the reviews:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --paginate \
  --jq '.[] | {id, state, commit_id, login: .user.login, type: .user.type}'
```

An approval counts only when `state` is `APPROVED`, `commit_id` equals `headRefOid`,
`login` is not the PR author, and `type` is `User` (an account of type `Bot`, or an app,
never counts, nor does any review this skill could post, since it never approves). With
no counting approval, do not merge: notify the user once (`blocked_notified`) that a human
approval of this head is needed, and wait as on `BLOCKED`.

**Unattended runs.** When the skill runs from a schedule or loop wakeup with no user
present to answer, it does not ask and does not merge: it notifies the user once
(`blocked_notified`) with the tier, reasons, and head sha, and waits. The next run where
the user is present asks the question.

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
order above. Never pass `--admin`. Do not use `--auto`: the skill itself decides when to merge.

### Stacked PRs

A PR in a GitHub native stack merges through the async merge API instead of `gh pr merge`
(GitHub names it the required API for stacked PRs). Every call passes the same API version
header as `ep-stack`.

Detect stacking; a non-null value means the PR is stacked, and gives the stack number:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>" --jq '.stack'
```

When that call fails, run `ep-stack`'s probe with `-i` to see its HTTP status. Only a 404,
or a 400 that rejects the API version, means the repository has no native stacks, so the PR
is not stacked. Any other result, success included, leaves the stack unknown, so SKILL.md
step 7 stops without merging. Unlike `ep-stack`, which falls back to plain branches on any
error, a merge cannot be undone, so a transient error must not count as "not stacked":

```bash
gh api -i -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks?per_page=1"
```

Find the lowest open PR of the stack. The order of `pull_requests` is the stack order,
bottom first; `stack.position` is not used, because GitHub does not define it:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks/<stack.number>" \
  --jq '[.pull_requests[] | select(.state == "open" and .merged_at == null)] | .[0].number'
```

The PR may merge only when this prints `<n>`. Merge pinned to the reviewed head, with the
method detected above without its dashes (`squash`, `merge`, or `rebase`), no bypass, and
the default `merge_action`:

```bash
gh api -i -X PUT -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>/merge-async" \
  -f sha=<last_review.head> -f merge_method="${method#--}" -F bypass_rules=false
```

`-i` prints the HTTP status line: `gh api` exits 0 for both 200 and 202, so read the status
from that line, not from the exit code. The UUID is at `.details.uuid` in the body, not at
the top level. A 202 body says `"status": "pending"` and may say "Merge request enqueued.":
that is the request being accepted, not the `enqueued` result below.

A 202 answer carries the merge UUID. A 409 answer means a merge is already pending: use the
UUID it returns. A 200 answer means the PR is already merged or already in a merge queue;
it has no UUID, so save `"queued"` in `merge_async` and do not request the merge again in this run
(SKILL.md step 7). Any other answer (an error such as 403, 405 or 422) rejected the merge:
SKILL.md step 7 stops without retrying. On later ticks after a 200, check the PR instead:

```bash
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
  pullRequest(number:$n){state mergeQueueEntry{state}}}}' -F o=<owner> -F r=<repo> -F n=<n>
```

`state: MERGED` means merged. A non-null `mergeQueueEntry` means it is still queued. An
open PR with a null `mergeQueueEntry` has left the queue.

With a UUID, read the result:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>/merge-async/<uuid>"
```

`status` is `pending`, `merged`, `enqueued`, or `failed`. `enqueued` is final: it does not
change when the queue later merges or ejects the PR, so from then on check the PR with the
query above. A 404 means the result expired (24 hours after its last update); check the PR
the same way. SKILL.md step 7 says what each one leads to. The head branch is left in place: GitHub rebases the PRs above onto it.
