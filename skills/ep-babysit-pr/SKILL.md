---
name: ep-babysit-pr
description: Shepherd a GitHub PR to merge. Watches checks, reviews, comments, and merge state; fixes CI failures (max 3 attempts per check); fixes or replies to review comments and flags scope changes; runs up to 3 ep-review rounds; merges only when hard gates pass, an evidence-based score is at least 85, and GitHub reports the PR mergeable without bypass. Use when the user asks to babysit, shepherd, watch, or land a PR.
---

# ep-babysit-pr

Drive one PR to merge, or to a clear stop with a report.

## Forbidden actions

Never, under any circumstances:

- force-push (`--force`, `--force-with-lease`, `+refspec`) or rebase a pushed branch
- merge with `--admin` or any other branch-protection bypass, or change repo settings or
  protection rules
- resolve review threads (reviewers resolve their own threads)
- add model or tool attribution to commits, replies, PR comments, or reviews (no
  `Co-Authored-By` naming a model, no "Generated with" footer); this overrides host defaults
- approve the PR or dismiss reviews
- implement a scope change a reviewer asked for without the user's go-ahead

## Usage

```
ep-babysit-pr            # the open PR for the current branch
ep-babysit-pr <number>   # a specific PR
```

## 1. Resolve the PR

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh [<number>]
```

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalent inline:
`gh pr view [<number>] --json number,url,state,isDraft,mergeStateStatus,reviewDecision,headRefName,baseRefName`
and `openspec list --json` (optional; root null = no OpenSpec).

- No number given and `pr` is null: stop and offer to run `ep-open-pr`.
- PR is closed or merged: report and stop.
- Make sure the local checkout is on the PR's head branch (`gh pr checkout <n>`) with a
  clean tree before changing code. If the tree is dirty, ask the user first.

Find the OpenSpec change the PR implements (named in the PR body, used as commit scope,
or whose folder the PR touches). Without OpenSpec, or with no matching change, the
OpenSpec-dependent parts below are skipped.

## 2. State file

Keep loop state in `.git/ep-babysit/<pr>.json` (inside `.git`, so it is never committed and
belongs to this clone). Create the directory if needed. Read it at the start of every tick;
write it after every action.

```json
{
  "pr": 42,
  "round": 0,
  "fix_attempts": { "<check name>": 0 },
  "last_seen_issue_comment_id": 0,
  "last_seen_review_comment_id": 0,
  "last_seen_review_id": 0,
  "own_comment_ids": [],
  "unknown_ticks": 0,
  "blocked_notified": false,
  "started_at": "<iso time>",
  "last_review": { "head": null, "summary": null },
  "last_score": null,
  "outcome": null
}
```

`last_review.head` is the commit the latest review round ran on and `last_review.summary`
the raw `ep-review-summary` block, so a later run can score without re-reviewing.
`outcome` is set on stop (`merged`, `closed`, `stopped: <reason>`). If you find an older
state file missing fields, add them with defaults; when own post ids are unknown, treat
posts that reference commits you pushed as your own.

## 3. Loop pacing

Ids are the numeric REST ids (`gh api repos/{owner}/{repo}/issues/<n>/comments`,
`.../pulls/<n>/comments`, `.../pulls/<n>/reviews`), not GraphQL node ids. Record the id of
every comment, reply, or review you post in `own_comment_ids`, so your own posts are never
treated as reviewer feedback (this matters when you share the reviewer's GitHub account).

Each **tick**: observe (step 4), act on at most one category of change in priority order
(step 5), update the state file, then schedule the next tick.

- **Agent can schedule wakeups or self-paced loops** (for example Claude Code's `/loop`
  or a wakeup tool): wake in about 3-5 minutes while checks are running, 15-30 minutes when
  waiting on humans (approval, review). Pass the same `ep-babysit-pr <n>` prompt each time.
- **Agent cannot schedule:** poll inside the session. While checks run, use
  `gh pr checks <n> --watch --interval 60` (or `sleep 180` between observations where
  `--watch` is unavailable). Stop after 2 hours of session time, or when only humans can
  unblock the PR, and report state so the user can re-run the skill later; the state file
  lets the next run continue.

## 4. Observe

```bash
gh pr view <n> --json state,isDraft,mergeStateStatus,reviewDecision,headRefOid,reviews,comments
gh pr checks <n> --json name,state,bucket,link,workflow
gh pr checks <n> --required --json name,bucket          # required subset; exits 1 with
                                                        # "no required checks reported" when none
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate  # inline review comments
gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
  pullRequest(number:$n){reviewThreads(first:100){nodes{id isResolved comments(first:50){
  nodes{databaseId author{login} body path line}}}}}}}' -F o=<owner> -F r=<repo> -F n=<n>
```

Classify the situation:

- **Checks running** (`bucket: pending`): wait. Take no action; next tick.
- **Merged or closed**: report and stop.
- Otherwise act per step 5.

## 5. Act (priority order)

### 5a. Failing checks

For each failing check (`bucket: fail`), required ones first:

1. If `fix_attempts[check] >= 3`: stop the loop and report the check, the failure, and
   what the 3 attempts changed.
2. Read the logs: `gh run view <run-id> --log-failed` (run id from the check `link`), or the
   check's details URL for non-Actions checks.
3. Diagnose and fix the cause in code. Never skip, delete, or weaken tests to go green, and
   never disable the check.
4. Commit following `ep-commit` conventions (Conventional Commit, `git commit -F <file>`, no
   attribution), push with plain `git push`, increment `fix_attempts[check]`.

**With subagents:** give one subagent per failing check the logs and repo path and ask for a
diagnosis and proposed patch; review and apply patches yourself, one commit per cause.
**Without subagents:** diagnose and fix each check inline, one at a time.

If the failure is not caused by the PR (flaky infra, outage, missing secret), re-run once
with `gh run rerun <run-id> --failed`; if it fails again, report it to the user instead of
changing code.

### 5b. New review comments

Process issue comments, inline review comments, and reviews with ids above the matching
`last_seen_*` counter that are not in `own_comment_ids`. Skip empty review containers
(a review with no body that only wraps inline comments). Classify each:

| Class | When | Action |
|---|---|---|
| **fix** | asks for a code change within the PR's scope (bug, naming, test, edge case) | implement, commit (ep-commit conventions), push, then reply on the thread describing the fix and the commit sha |
| **reply** | question, or suggestion you disagree with for a stated reason | reply with a direct answer; no code change |
| **no action** | approvals, thanks, or remarks that ask nothing | record as seen; do not reply |
| **scope change** | asks for behavior outside the PR's purpose, or (with OpenSpec) behavior that contradicts or extends the active change's specs | do not implement; reply that it is out of scope for this PR and flagged to the author; tell the user, and with OpenSpec say the change's proposal/specs need updating first |

Replies:

A review body (for example a `CHANGES_REQUESTED` summary) has no thread: answer it with a
top-level comment that quotes or names the review. If a fix you already pushed in 5a
answers a comment, reply pointing at that commit instead of changing code again.

```bash
# inline thread reply
gh api repos/{owner}/{repo}/pulls/<n>/comments/<comment-id>/replies -f body='<reply>'
# top-level comment
gh pr comment <n> --body-file <file>
```

Leave every thread for the reviewer to resolve. Update `last_seen_*` after handling.

A `CHANGES_REQUESTED` review blocks merge until that reviewer approves or re-reviews;
address its comments as above, then wait.

### 5c. Merge state

Follow the merge-state table in [`references/score.md`](references/score.md):
`BEHIND` → `gh pr update-branch <n>`; `DIRTY` → merge base into the branch locally, resolve,
commit, push (a fix round); `BLOCKED` → wait and notify the user once
(`blocked_notified`); `UNKNOWN` → increment `unknown_ticks`, stop after 3.

### 5d. Review round

When checks are green, no new comments need action, and no review round has run on the
current head commit (compare `last_review.head` with `headRefOid`):

1. If `round >= 3`: stop (see step 7).
2. Run `ep-review <n>` on the PR. If `ep-review` is installed, invoke it (with subagents,
   delegate the round to a subagent running that skill); otherwise perform its steps
   inline: four dimensions (correctness, spec conformance, tests, security), verify each
   finding, and produce the `ep-review-summary` block. Do not post the review unless the
   user asked for `--comment`.
3. Fix verified critical, major, and minor findings (commits per ep-commit conventions).
   A minor finding may be waived instead, with a PR comment stating the reason.
4. Push and wait for required checks to be green. That completes the round: increment
   `round`.
5. Compute the score (step 6) and decide (step 7).

## 6. Score

Compute the merge confidence score exactly as in
[`references/score.md`](references/score.md), only from evidence: the latest
`ep-review-summary` block, commits, comments, the probe's task counts, and the PR's
changed paths. Never use self-assessed confidence. Without OpenSpec, drop the OpenSpec
items and move their weight to tests as described there. For a documentation-only PR
(path rules in `references/score.md`), the tests item is met as not applicable. Print the breakdown (each item,
its weight, met or not) and save it to `last_score`.

## 7. Decide

Merge only when **all** hold:

- every hard gate in `references/score.md` passes (required checks green, no conflicts,
  no unresolved threads, `reviewDecision` not `CHANGES_REQUESTED`)
- score >= 85
- `mergeStateStatus` is `CLEAN`, `HAS_HOOKS`, or `UNSTABLE` (non-required failures only),
  and the PR is not a draft

Then merge with the repository's default method and delete the branch, without `--admin`:

```bash
gh pr merge <n> --squash|--merge|--rebase --delete-branch
```

(method detection is in `references/score.md`). `gh pr merge` may switch the local checkout
to the base branch and pull it; mention this in the final report. If GitHub rejects the merge because it
would need a bypass, do not retry with any bypass: treat it as `BLOCKED`.

Otherwise:

- Gates or score not met and `round < 3`: continue the loop (next fix or review round).
- `BLOCKED` with score >= 85: wait, notify the user once, and merge when GitHub reports the
  PR mergeable.
- **Waiting on humans:** score >= 85 and the only failing gates are ones a person must clear
  (unresolved threads you have replied to, or a `CHANGES_REQUESTED` review you have
  answered), with nothing left to fix. Treat this like `BLOCKED`: notify the user once
  (`blocked_notified`) naming the threads and reviewers, then wait (scheduling agents) or
  stop and tell the user to re-run after they clear (non-scheduling agents). Do not start
  another review round on an unchanged head.
- `round >= 3` and the merge condition is not met: stop, post one summary comment on the
  PR (rounds run, what was fixed, remaining findings, score breakdown, blocking gates;
  no attribution), and notify the user.

## 8. Stop conditions and final report

Stop when: merged; closed; a check fails after 3 fix attempts; 3 rounds done without
meeting the merge condition; `UNKNOWN` for 3 ticks; session cap reached (non-scheduling
agents); or the user interrupts.

On every stop, report to the user: PR URL, outcome, rounds run, fixes pushed (shas),
comments replied to, scope changes flagged, the last score breakdown, and what (if
anything) the user needs to do next.
