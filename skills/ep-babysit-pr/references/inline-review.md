# Inline review round

Read when SKILL.md step 5d runs a review round and `ep-review` is not installed. Perform
its steps inline and produce the same `ep-review-summary` block, so step 5d records and
scores the round the same way.

1. Review the four dimensions: correctness, spec conformance, tests, and security.
2. Verify each finding before reporting it.
3. Apply `--since` and the known findings exactly as step 5d passes them to `ep-review`:
   with `--since`, review only the commits since that head; re-check each known finding
   instead of reporting it again.
4. Tag each verified finding's origin. It is **pre-existing** only when all of these hold:
   - the defect would occur at the base too (the PR did not cause it);
   - its lines are not among the PR's added lines;
   - `git blame -M -C <base>..<head> -L <start>,<end> -- <file>` marks every one as a
     boundary line (`^`).

   Any other case, or doubt, means **introduced**, including a defect the PR causes in
   unchanged lines (an unchanged caller of a changed callee, a `CLAUDE.md` line a rename
   makes stale). Count pre-existing findings only in `pre_existing:`, never in
   `verified:`.
5. Compute the risk tier and reasons from [`risk.md`](risk.md) over:
   - the whole PR's changed paths, both sides of each rename, even on a `--since` round:

     ```bash
     gh api repos/{owner}/{repo}/pulls/<n>/files --paginate \
       --jq '.[] | .filename, (.previous_filename // empty)'
     ```

   - the PR author;
   - the base's `REVIEW.md`.

   Write them as `risk:` and `risk_reasons:`. The block always has a `risk:` line, with
   `verification: inline`.

Done when the `ep-review-summary` block is printed with `risk:`, `risk_reasons:`,
`verification: inline`, and every verified finding counted in `verified:` or
`pre_existing:`.
