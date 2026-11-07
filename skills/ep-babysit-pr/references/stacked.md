# Stacked PRs

Read when SKILL.md step 7 is about to merge. A PR in a GitHub native stack merges through
the async merge API instead of `gh pr merge` (GitHub names it the required API for stacked
PRs). Every call passes the same API version header as `ep-stack`. Every merge condition of
step 7, the risk gate included, already holds when these steps run.

## Detect the stack

Read `.stack` on the REST PR object:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>" --jq '.stack'
```

- **Non-null:** the PR is stacked, and the value gives the stack number. Merge it by
  [Merge the bottom layer](#merge-the-bottom-layer).
- **Null:** the PR is in no native stack. Merge it with `gh pr merge` (SKILL.md step 7).
- **The call fails:** run `ep-stack`'s probe with `-i` to see its HTTP status:

  ```bash
  gh api -i -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks?per_page=1"
  ```

  Only a 404, or a 400 that rejects the API version, means the repository has no native
  stacks, so the PR is not stacked: merge it with `gh pr merge`. Any other result (the
  probe succeeds, a 403 or 5xx, a rate limit, no network) means the stack is unknown: do
  not merge, report both answers, set `outcome: stopped: stack detection failed` and stop.
  Unlike `ep-stack`, which falls back to plain branches on any error, a merge cannot be
  undone, so a transient error never counts as "not stacked".

## Merge the bottom layer

Merging a stacked PR also merges every open PR below it, so only the bottom layer merges.

1. **Find the lowest open PR of the stack.** The order of `pull_requests` is the stack
   order, bottom first; `stack.position` is not used, because GitHub does not define it:

   ```bash
   gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks/<stack.number>" \
     --jq '[.pull_requests[] | select(.state == "open" and .merged_at == null)] | .[0].number'
   ```

   The PR may merge only when this prints `<n>`. When an open PR sits below this one, do
   not merge: report the lower open PRs, in order, as the ones that must merge first, set
   `outcome: stopped: mid-stack` and stop. Never merge a PR below this one.
2. **Request the merge** when this PR is the lowest open PR and `merge_async` is null.
   When `merge_async` is already set, skip the request and go to step 3. Pin it to
   `last_review.head`, with the method detected in `score.md` ("Merge command") without its
   dashes (`squash`, `merge`, or `rebase`), no bypass (`bypass_rules=false`), and the
   default `merge_action`:

   ```bash
   gh api -i -X PUT -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>/merge-async" \
     -f sha=<last_review.head> -f merge_method="${method#--}" -F bypass_rules=false
   ```

   `-i` prints the HTTP status line: `gh api` exits 0 for both 200 and 202, so read the
   status from that line, not from the exit code. The UUID is at `.details.uuid` in the
   body, not at the top level. A 202 body says `"status": "pending"` and may say "Merge
   request enqueued.": that is the request being accepted, not the `enqueued` result
   below.

   - **202:** save the merge UUID in `merge_async`.
   - **409:** a merge is already pending: save the UUID it returns.
   - **200:** the PR is already merged or already in a merge queue. The answer has no
     UUID: save `"queued"` in `merge_async`, so no later tick requests the merge again in
     this run.
   - **Any other answer** (an error such as 403, 405 or 422) rejected the merge: report
     the status and message, leave `merge_async` `null`, set
     `outcome: stopped: merge rejected` and stop. Do not retry, with or without a bypass,
     in this run.
3. **Follow the merge**, once per tick.
   - **`merge_async` is `"queued"`:** check the PR instead:

     ```bash
     gh api graphql -f query='query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){
       pullRequest(number:$n){state mergeQueueEntry{state}}}}' -F o=<owner> -F r=<repo> -F n=<n>
     ```

     `state: MERGED` means the PR is merged. A non-null `mergeQueueEntry` means it is
     still in the merge queue: wait as on `BLOCKED`. An open PR with a null
     `mergeQueueEntry` has left the queue (the queue ejected it): report it, set
     `merge_async` to `null`, set `outcome: stopped: left merge queue` and stop. Do not
     request the merge again in this run.
   - **`merge_async` holds a UUID:** read the result:

     ```bash
     gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/pulls/<n>/merge-async/<uuid>"
     ```

     Its `status` is `pending`, `merged`, `enqueued`, or `failed`:

     - `pending`: next tick.
     - `enqueued`: the merge queue holds it. This result is final and does not change
       when the queue merges or ejects the PR, so set `merge_async` to `"queued"` and
       check the PR from the next tick on, as above.
     - a 404 answer: the result expired (results are kept for 24 hours after their last
       update). Set `merge_async` to `"queued"` and check the PR as above.
     - `merged`: confirm with `gh pr view <n> --json state` (`MERGED`). Then the PR is
       merged.
     - `failed`: report the response details, set `merge_async` to `null`, set
       `outcome: stopped: merge failed` and stop. Do not retry, with or without a bypass,
       in this run.
4. **Leave the head branch in place.** GitHub rebases the PRs above onto it. The final
   report says the branch was kept and that the repository's auto-delete setting still
   applies.

Done when the PR is merged, is waiting in the merge queue, or the run has stopped with
one of the outcomes above.
