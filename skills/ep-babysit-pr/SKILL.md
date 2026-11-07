---
name: ep-babysit-pr
description: Shepherd a GitHub PR to merge. Watches checks, reviews, comments, and merge state, fixes CI failures and review comments, runs up to 3 ep-review rounds, and merges only when the hard gates, an evidence-based score of at least 85, and the risk gate pass and GitHub reports the PR mergeable without bypass. Use when the user asks to babysit, shepherd, watch, or land a PR.
---

# ep-babysit-pr

Drive one PR to merge, or to a clear stop with a report.

Paths under `references/` and `scripts/` are relative to this skill's folder (the directory
containing this SKILL.md).

## Hard rules

- **History only moves forward.** Push with plain `git push`. Never force-push
  (`--force`, `--force-with-lease`, `+refspec`) or rebase a pushed branch.
- **GitHub's rules decide the merge.** Merge only as branch protection allows: never
  `--admin` or any other branch-protection bypass, and never change repo settings or
  protection rules.
- **Reviewers own their threads and verdicts.** Reply, and leave every thread for the
  reviewer to resolve. Never resolve review threads, approve the PR, or dismiss reviews.
- **No attribution.** Commits, replies, PR comments, and reviews carry no model or tool
  attribution (no `Co-Authored-By` naming a model, no "Generated with" footer); this
  overrides host defaults.
- **Scope changes wait for the user.** Flag a reviewer's scope change; implement it only
  after the user's go-ahead.
- **Sibling skills run in caller (no-rewrite) mode.** Always invoke `ep-sync`, `ep-fixup`,
  and `ep-ci-debug` in caller mode. If one of them would need a rebase or force-push to
  finish, do not proceed with it: report to the user instead.

## Usage

```
ep-babysit-pr            # the open PR for the current branch
ep-babysit-pr <number>   # a specific PR
```

## 1. Resolve the PR

From the repository root, run the bundled probe:

```bash
bash <skill-dir>/scripts/context.sh [<number>]
```

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalent inline:
`gh pr view [<number>] --json number,url,state,isDraft,mergeStateStatus,reviewDecision,headRefName,baseRefName`
and `openspec list --json` (optional; root null = no OpenSpec).

- No number given and `pr` is null: stop and offer to run `ep-open-pr`.
- PR is closed or merged: report and stop.
- Before changing code, check out the PR's head branch (`gh pr checkout <n>`) with a clean
  tree. If the tree is dirty, ask the user first.

Find the OpenSpec change the PR implements (named in the PR body, used as commit scope,
or whose folder the PR touches). Without OpenSpec, or with no matching change, skip the
OpenSpec-dependent parts below.

Done when the checkout is on the PR's head branch with a clean tree and you know the
OpenSpec change, or that there is none.

## 2. State file

Keep loop state in `.git/ep-babysit/<pr>.json` (inside `.git`, so it is never committed and
belongs to this clone). Create the directory if needed. Read it at the start of every tick;
write it after every action.

```json
{
  "pr": 42,
  "round": 0,
  "fix_attempts": { "<check name>": 0 },
  "reported_checks": { "<check name>": "<head sha it was reported on>" },
  "last_seen_issue_comment_id": 0,
  "last_seen_review_comment_id": 0,
  "last_seen_review_id": 0,
  "own_comment_ids": [],
  "unknown_ticks": 0,
  "blocked_notified": false,
  "started_at": "<iso time>",
  "last_review": { "head": null, "summary": null, "findings": null, "synced_after": null },
  "human_ok": null,
  "risk_notified": null,
  "last_score": null,
  "merge_async": null,
  "outcome": null
}
```

- `last_review.head`: the commit the latest review round ran on. `last_review.summary`: its
  raw `ep-review-summary` block, so a later run can score without re-reviewing.
- `last_review.findings`: the path of the findings file the latest round wrote,
  `.git/ep-babysit/<pr>.findings` (step 5d).
- `last_review.synced_after`: the head sha of a base sync pushed after `last_review.head`
  (step 5c), or `null` when none was. It tells the next round to review the full PR again
  (step 5d also detects base merges this skill did not make).
- `human_ok`: `{ "head": "<sha>" }` after the user said yes to merging that exact head
  (step 7), or `null`. Clear it to `null` whenever `headRefOid` changes.
- `risk_notified`: the head sha the latest risk-gate notice (step 7) was sent for, or
  `null`. It is separate from `blocked_notified`, so an earlier `BLOCKED` or
  waiting-on-humans notice never silences it, and a new head gets a new notice.
- `merge_async`: the UUID of a requested async merge of a stacked PR (step 7), or
  `"queued"` when GitHub answered that the PR was already merged or queued, so later ticks
  read its result or check the PR instead of requesting another merge. It belongs to one
  run: a stop with `left merge queue` or `merge failed` clears it to `null`, so a re-run
  after the user fixes the cause can request the merge again.
- `outcome`: set on stop (`merged`, `closed`, `stopped: <reason>`).

An older state file missing fields gets them with defaults (`last_review.findings`,
`last_review.synced_after`, `human_ok`, and `risk_notified` default to `null`). When own
post ids are unknown, treat posts that reference commits you pushed as your own.

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

Before acting, compare the local branch with the PR head on GitHub. This works for fork
PRs too, where `@{u}` may not resolve:

```bash
git fetch "$(gh repo view --json url --jq .url)" pull/<n>/head   # the base repo, even in a fork clone
git rev-list --count FETCH_HEAD..HEAD    # local commits GitHub does not have
git rev-list --count HEAD..FETCH_HEAD    # GitHub commits the local branch lacks
```

- **A command fails:** commit and push nothing this tick; report and stop.
- **Only the second count is above 0** (for example a reviewer committed a suggestion on
  GitHub): fast-forward first with `git merge --ff-only FETCH_HEAD`, so fixes build on the
  PR's real head.
- **The first count is above 0:** the branch holds commits no step of this tick made, for
  example a merge left local by an earlier `needs_decision` or `needs_attention` sync.
  Every push in steps 5a-5d would publish them, so commit and push nothing: report those
  commits and stop until the user pushes or discards them.

Then classify:

- **Checks running** (`bucket: pending`): wait. Take no action; next tick.
- **Merged or closed**: report and stop.
- Otherwise act per step 5.

## 5. Act (priority order)

### 5a. Failing checks

For each failing check (`bucket: fail`), required ones first:

1. If `fix_attempts[check] >= 3`: stop the loop and report the check, the failure, and
   what the 3 attempts changed. If `reported_checks[check]` equals the current head, it was
   already diagnosed and reported on this commit: invoke nothing for it again (no new
   re-run); it is waiting on the user.
2. Diagnose and fix it:
   - **If the skill `ep-ci-debug` is available to you**, invoke it for that check in caller
     mode (`ep-ci-debug <check> --caller ep-babysit-pr`). It reads the logs, classifies
     the cause, fixes, commits, and pushes without a prompt.
   - **Otherwise**, follow [`references/side-paths.md#ci-debug`](references/side-paths.md#ci-debug)
     inline. It has the same classes, re-run-once, and never-weaken-tests rules, and
     produces the same `check:` fields.
3. Read the result: the `ep-ci-debug-summary` block, or the `check:` line from the side
   path. For each check with `result=fixed`, increment `fix_attempts[check]` and record the
   `fix` sha. Only fixed checks count as attempts.
4. A check with `result=reported` (class `flaky-infra`, `config`, or `secret` whose single
   re-run did not fix it or that needs a person, or class `code`/`test` with no safe fix):
   set `reported_checks[check]` to the current head, make no code change, and notify the
   user once with the diagnosis. If it is a required check, the PR cannot merge: treat it
   like waiting on humans (step 7). A new head commit clears the entry, so the check is
   diagnosed again (with a fresh single re-run) only after something changed.

On either path, fix the cause and keep tests and checks as strong as they are: never skip,
delete, or weaken tests to go green, and never disable the check. Commit fixes following
`ep-commit` conventions (no attribution) and push with plain `git push`.

**With subagents:** when several checks fail, invoke `ep-ci-debug` once for all of them
(it diagnoses them in parallel itself and commits one fix per cause), or delegate that run
to a subagent and read back its summary. On the side path, give one subagent per check
the logs and `side-paths.md#ci-debug` and ask for a classification and proposed patch;
apply the patches yourself, one commit per cause. Subagents never push concurrently.
**Without subagents:** handle the checks inline, one at a time.

Done when every failing check is fixed, waiting on CI, reported, or has stopped the loop.

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

**How fix-class changes are committed** depends on the repository's merge method, detected
each time exactly as in [`references/score.md`](references/score.md) ("Merge command"):

- **Squash:** commit the fix as a `fixup!` commit targeting the commit it corrects, so
  reviewers see where it belongs and the squash merge removes it. If the skill `ep-fixup`
  is available to you, invoke it in caller mode (`ep-fixup --caller ep-babysit-pr`, which
  is no-rewrite and pushes with a plain push); otherwise follow
  [`references/side-paths.md#fixup`](references/side-paths.md#fixup). Read the
  `fixups:` field and name the fixup and target shas in the reply. When the corrected lines
  come from the base, it makes a normal commit instead.
- **Merge or rebase:** commit a normal commit following `ep-commit` conventions, so no
  `fixup!` subject reaches the base branch.

If `ep-fixup` (or the side path) returns `needs_decision` (a change it cannot attach to one
commit without asking), commit that remaining change as a normal ep-commit commit and push
it. The reply names each fixup and its target from `fixups:`, and any normal commit from
`commits:`. Fixup commits stay as they are: never autosquash, rebase, or force-push them.

**Replies.** A review body (for example a `CHANGES_REQUESTED` summary) has no thread:
answer it with a top-level comment that quotes or names the review. If a fix you already
pushed in 5a answers a comment, reply pointing at that commit instead of changing code
again.

```bash
# inline thread reply
gh api repos/{owner}/{repo}/pulls/<n>/comments/<comment-id>/replies -f body='<reply>'
# top-level comment
gh pr comment <n> --body-file <file>
```

Leave every thread for the reviewer to resolve. Update `last_seen_*` after handling.

A `CHANGES_REQUESTED` review blocks merge until that reviewer approves or re-reviews;
address its comments as above, then wait.

Done when every new comment is classified and handled, and `last_seen_*` is updated.

### 5c. Merge state

Follow the merge-state table in [`references/score.md`](references/score.md):
`BEHIND` or `DIRTY` → sync with the base and audit (below); `BLOCKED` → wait and notify the
user once (`blocked_notified`); `UNKNOWN` → increment `unknown_ticks`, stop after 3.

**Sync with the base** (`BEHIND`, `DIRTY`), always by merge: never
`gh pr update-branch --rebase`, rebase, or force-push.

1. If the skill `ep-sync` is available to you, invoke it in caller mode
   (`ep-sync --caller ep-babysit-pr`: merge only, no push, never waits for the user).
   With subagents, you may delegate that run to a subagent; its audit clusters fan out
   inside it. Otherwise follow
   [`references/side-paths.md#sync`](references/side-paths.md#sync) inline.
2. Read the `ep-sync-summary` block (or the side path's fields):
   - `outcome: synced`: push with plain `git push`, set `last_review.synced_after` to the
     pushed head sha when `last_review.head` is set, wait for checks, re-evaluate. The
     adaptation commits for needs-update items are this sync's **fix round**: they are
     separate from the merge commit and get the same checks as any fix.
   - `outcome: needs_decision`: do not push. Notify the user with the options from the
     report and stop until they decide. For an incompatible conflict the merge was already
     aborted and the branch is unchanged. For an ambiguous adaptation the merge commit (and
     any adaptations) stays local and unpushed; say so, so the user can keep or discard it.
   - `outcome: needs_attention` (tests fail, or `unresolved_needs_update > 0`): do not push
     the sync. Report the failures or unresolved items and stop.
   - `outcome: up_to_date`: nothing to do; GitHub's state will catch up.
3. List every **review**-class interaction from the audit in the next status report, and
   include them in the next review round's scope (tell `ep-review` which base commits and
   branch locations to check).

### 5d. Review round

When checks are green, no new comments need action, and no review round has run on the
current head commit (compare `last_review.head` with `headRefOid`):

1. If `round >= 3`: stop (see step 7).
2. Run the review on the PR:
   - **Round 1** (`last_review.head` is `null`): `ep-review <n>`, the full PR.
   - **Later rounds:** `ep-review <n> --since <last_review.head> --known <last_review.findings>`,
     so only the commits since the last reviewed head are reviewed and the earlier
     findings are re-checked instead of reported again. When base code entered the branch
     after that head, drop `--since` and review the full PR, still passing
     `--known <last_review.findings>`. That is the case when `last_review.synced_after` is
     set (this skill pushed a base sync), and also when the base arrived another way (GitHub's
     "Update branch", a merge a person pushed, then fast-forwarded in step 4). Check it
     every later round, after `git fetch origin <baseRefName>`:

     ```bash
     git rev-list --count --merges <last_review.head>..<headRefOid>            # merge commits
     git rev-list --count <last_review.head>..<headRefOid> --not origin/<baseRefName>
     git rev-list --count <last_review.head>..<headRefOid>
     ```

     A merge commit in the range (first count above 0), or a range holding commits that are
     already on the base (second count below the third), means base code came in: review
     the full PR. If a command fails, review the full PR too.

   If `ep-review` is installed, invoke it (with subagents, delegate the round to a
   subagent running that skill); otherwise follow
   [`references/inline-review.md`](references/inline-review.md), which produces the same
   `ep-review-summary` block. Post the review only when the user asked for `--comment`.
3. Record the round: set `last_review.head` to the reviewed head and `last_review.summary`
   to the summary block, clear `last_review.synced_after` to `null`, and overwrite
   `.git/ep-babysit/<pr>.findings` with one line per verified finding of this round
   (introduced, still open, and pre-existing), then set `last_review.findings` to that path:

   ```
   finding: <id> <dimension> <severity> <file>:<line> | <summary> | <scenario> | class: <label> | instances: <file>:<line>,<file>:<line>
   ```

   `<id>` is `r<round>.<n>`. Drop the `| instances:` part when the finding has none.
4. Fix verified critical, major, and minor **introduced** findings (commits per ep-commit
   conventions). A fix covers the finding's location and every one of its `instances`, in
   the same commit. A minor finding may be waived instead, with a PR comment stating the
   reason. **Pre-existing** findings (the `### pre-existing` section, counted in
   `pre_existing:`) stay unfixed: list them in the next status report and in the final
   report. They do not count in `verified:`, so they do not affect the score.
5. Push and wait for required checks to be green. That completes the round: increment
   `round`.
6. Compute the score (step 6) and decide (step 7).

## 6. Score

Compute the merge confidence score exactly as in
[`references/score.md`](references/score.md), only from evidence: the latest
`ep-review-summary` block, commits, comments, the probe's task counts, and the PR's
changed paths. Never use self-assessed confidence. Without OpenSpec, drop the OpenSpec
items and move their weight to tests as described there. For a documentation-only PR
(path rule in [`references/risk.md`](references/risk.md#documentation-only-paths)), the
tests item is met as not applicable. Done when the breakdown (each item, its weight, met
or not) is printed and saved to `last_score`.

## 7. Decide

Merge only when **all** hold:

- every hard gate in [`references/score.md`](references/score.md#hard-gates) passes
  (required checks green, no conflicts, no unresolved threads, `reviewDecision` not
  `CHANGES_REQUESTED`)
- score >= 85
- `mergeStateStatus` is `CLEAN`, `HAS_HOOKS`, or `UNSTABLE` (non-required failures only),
  and the PR is not a draft
- the score's review ran on the current head: `last_review.head` equals `headRefOid`.
  Commits pushed after the last review round (CI fixes, review fixes, a sync's
  adaptations) need a review before merging. With rounds left, run one; at `round >= 3`,
  stop and report the unreviewed commits instead of merging
- the **risk gate** passes, checked last, after every condition above. The tier is the
  `risk:` line of `last_review.summary`; a summary without one counts as `medium`. The
  question, the approval test, and the unattended test are in
  [`references/score.md`](references/score.md#risk-gate):
  - **low:** nothing extra; merge.
  - **medium:** the user's explicit yes for this exact head (`human_ok.head` equals
    `headRefOid`). Otherwise ask the structured question (Merge, Wait, Stop). A new head
    clears `human_ok`, so it needs a new yes.
  - **high:** the same yes, and an `APPROVED` review of `headRefOid` from a human other
    than the PR author with standing on the repository; bot and app approvals never
    count. Without one, do not merge: notify the user once per head (`risk_notified`)
    that a human approval of this head is needed, then wait as on `BLOCKED`.
  - **Unattended run** (a `/loop` tick or wakeup that no user message started, a
    scheduled run, or no way to ask): do not ask and do not merge. Notify the user once
    per head (`risk_notified`) with the tier, reasons, and head sha, then wait; ask on the
    next attended run.

**Stacked or not.** Before merging, check whether the PR is in a GitHub native stack, as
in [`references/stacked.md`](references/stacked.md#detect-the-stack). A stacked PR merges
by the steps there (only the bottom open layer merges, through the async merge API, and
its head branch stays). When detection leaves the stack unknown, stacked.md stops the run
without merging. A PR in no native stack merges with the repository's default method and
deletes the branch, without `--admin`:

```bash
gh pr merge <n> --squash|--merge|--rebase --delete-branch --match-head-commit <last_review.head>
```

(`--match-head-commit` makes GitHub refuse the merge if the head moved after the review;
method detection is in `references/score.md`). `gh pr merge` may switch the local checkout
to the base branch and pull it; mention this in the final report. If GitHub rejects the
merge because it would need a bypass, never retry with any bypass: treat it as `BLOCKED`.

Otherwise, apply the first rule below that matches. The waiting rules come before the
round rules, so a PR that only needs a person (GitHub, a reviewer, or the risk gate) waits
at any round, including after round 3:

- Only the risk gate fails (score >= 85, every other condition met): this is waiting on
  humans, not a reason for another review round or a round-cap stop. Wait as described in
  the gate.
- `BLOCKED` with score >= 85: wait, notify the user once, and merge when GitHub reports the
  PR mergeable.
- **Waiting on humans:** score >= 85 and the only failing gates are ones a person must clear
  (unresolved threads you have replied to, or a `CHANGES_REQUESTED` review you have
  answered), with nothing left to fix. Treat this like `BLOCKED`: notify the user once
  (`blocked_notified`) naming the threads and reviewers, then wait (scheduling agents) or
  stop and tell the user to re-run after they clear (non-scheduling agents). Start no
  other review round on an unchanged head.
- Gates or score not met and `round < 3`: continue the loop (next fix or review round).
- `round >= 3` and the merge condition is not met: stop, post one summary comment on the
  PR, and notify the user. The comment states the rounds run, what was fixed, remaining
  findings, pre-existing findings left unfixed, the score breakdown, and the blocking
  gates, and asks the author to step back and reconsider the approach rather than
  continue patching findings (three rounds that did not converge suggest the approach,
  not the details, needs another look). No attribution.

## 8. Stop conditions and final report

Stop when any of these holds:

- merged, or closed;
- the user chose Stop at the risk gate (step 7);
- the PR is mid-stack, stack detection failed, its async merge was rejected or failed, or
  it left the merge queue (step 7);
- a sync returned `needs_decision` or `needs_attention`;
- a check fails after 3 fix attempts;
- 3 rounds done without meeting the merge condition (not when only a person is left to
  act: those waiting rules in step 7 come first);
- `UNKNOWN` for 3 ticks;
- session cap reached (non-scheduling agents);
- the user interrupts.

On every stop, report to the user: PR URL, outcome, rounds run, fixes pushed (shas),
comments replied to, scope changes flagged, pre-existing findings left unfixed (file,
line, summary), the last score breakdown, and what (if anything) the user needs to do
next.

## Without subagents, loops, or sibling skills

Every step has a sequential path: checks are diagnosed one at a time inline, review rounds
run inline, and polling happens inside the session (step 3). The side-path skills are
optional too: when `ep-ci-debug`, `ep-fixup`, or `ep-sync` is not available to you, follow
the matching section of [`references/side-paths.md`](references/side-paths.md), which
produces the same summary fields, so CI fixes, review fixes, and base syncs work the same
with none of them installed.
