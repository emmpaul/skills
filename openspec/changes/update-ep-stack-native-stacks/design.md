# Design

## Context

For the motivation, see proposal.md (Why). Below is what the GitHub docs say, read on
2026-11-05 from the about page, the CLI reference
(`/en/pull-requests/reference/stacked-prs-cli-commands`), the quickstart, the rollout
tutorial, the REST stacks reference (`/en/rest/pulls/stacks`), and the async merge endpoint:

- A stack is two or more PRs in **one repository**. Cross-fork stacks are not supported. The
  bottom PR targets the trunk, and each PR above it targets the head branch of the PR below.
- REST, API version `2026-03-10`:
  - `GET /repos/{o}/{r}/stacks`, which takes an optional `?pull_request=<n>` filter.
  - `POST /repos/{o}/{r}/stacks` with `pull_requests` listed bottom to top. Each PR's base
    must equal the previous PR's head. Returns 422 when they cannot form a stack.
  - `GET .../stacks/{number}`, `POST .../stacks/{number}/add`, and
    `POST .../stacks/{number}/unstack`.
  - The PR object has an optional `stack` field (`id`, `number`, `size`, `position`,
    `base{ref,sha}`). The docs do not define `position`.
  - GraphQL stack fields are read-only.
- Merging a PR merges it and every open PR below it. PRs above stay open and are retargeted
  automatically. GitHub rebases the remaining branches server-side, so remote layer branches
  get rewritten. Merges are bottom-up, and the whole stack need not merge at once. Merge,
  squash, rebase, and merge queues are supported.
- `PUT /repos/{o}/{r}/pulls/{n}/merge-async` is "the required API for merging stacked pull
  requests", and the older merge endpoint does not support them. It takes `sha`,
  `merge_method`, `merge_action` (`default` uses the queue when one exists), and
  `bypass_rules` (default false). It answers 202 with a UUID. The result is read from
  `GET .../merge-async/{uuid}`, with status `pending`, `merged`, `enqueued`, or `failed`.
- Branch protection, CODEOWNERS, and CI from the trunk apply to every layer, and merge
  requirements cannot be bypassed.
- `gh stack` is a separate extension (`gh extension install github/gh-stack`). The
  quickstart says it needs gh 2.90.0 or later, and this machine has gh 2.89.0. It does
  rebase-based local stack tracking, and its `sync` and `push` use `--force-with-lease`.

**Uncertain points in the docs**, which the plan does not depend on:
- The rollout tutorial says stacks need "no setup or enablement". But the CLI reference has
  exit code 9, "Stacked PRs not enabled for the repository", and the docs links carry a
  "public-preview-2026" campaign tag. Availability may therefore vary by repository, plan, or
  GHES version.
- No page says whether `gh pr merge`, which uses GraphQL, can merge a stacked PR.
- No page says how GitHub's cascading rebase treats merge commits inside a layer.
- I did not find a separate page on managing or merging stacks; a guessed URL returned 404.

## Goals / Non-Goals

**Goals:**
- Stacks that `ep-stack` creates show up as native GitHub stacks when the repository supports
  them.
- `ep-stack` works with GitHub's automatic retargeting and rebasing instead of fighting it.
- `ep-babysit-pr` merges stacked PRs only through the documented API, and one layer at a time.
- Plain-branch behaviour is unchanged wherever native stacks are unavailable.

**Non-Goals:**
- Using or requiring the `gh stack` extension or its local tracking.
- An `unstack` command, editing a stack's order, or dissolving stacks. The user can use
  GitHub or `gh stack unstack` for that.
- Merging a whole stack in one operation. Each layer is still babysat and merged on its own.
- Cross-repository stacks, which GitHub does not support either.
- Changes to `ep-orchestrate`, `ep-sync`, or `shared/context.sh`.

## Decisions

**D1. Call the REST API through `gh api`, not the `gh stack` extension.** Every call passes
`-H "X-GitHub-Api-Version: 2026-03-10"`.
- Why: the extension needs a newer `gh` than some machines have (2.90 against 2.89 here).
  Installing it would change the user's environment without asking. Its model is
  rebase-and-force-push, which clashes with ep-stack's merge-by-default rule. The API is all
  that `split`, `link`, and `status` need.
- Alternative considered: delegating to `gh stack submit`, `gh stack link`, and
  `gh stack sync` when the extension is installed. Rejected, because that gives two code
  paths with different push semantics.

**D2. Detect native mode by probing the endpoint, and fall back to plain-branch mode.**
- The probe is `gh api "repos/{owner}/{repo}/stacks?per_page=1"`. Exit 0 means native. Any
  error means plain-branch mode, with a one-line reason.
- `--no-native` forces plain-branch mode.
- Why: the docs disagree on whether enablement is needed, and the feature may be in preview.
  A cheap read-only probe is the conservative test.
- When a split is already open and the create call returns 422 or 404, the PRs stay a plain
  stack. Nothing is rolled back, because the PRs are valid on their own.

**D3. Keep the `<!-- ep-stack -->` body section in both modes.** In native mode the GitHub
stack wins when the two disagree, and the skill reports the disagreement.
- Why: the body section makes the stack readable where the UI has no stack map (GitHub Desktop
  is unsupported). It lets `status` work when the API read fails. And it keeps a stack usable
  if the user later unstacks it on GitHub.
- Alternative considered: dropping the body section in native mode. Rejected, because it
  would leave `status` with no fallback.

**D4. In native mode, `retarget` checks the bases and changes none.**
- After a parent merges, `retarget` re-reads the stack and checks that the next PR's base is
  now the merged PR's base. Then it refreshes the local branches (D5) and updates the body
  sections, which edits only the bodies.
- If GitHub has not retargeted, `retarget` re-checks once after a short wait. Then it reports
  the problem and offers the plain `gh pr edit --base` retarget behind the existing
  confirmation.
- It does no merge-sync after the retarget, because GitHub has already rebased the layer onto
  the trunk.
- The summary contract (`layer:` lines) is unchanged, so `ep-orchestrate`'s stack brief needs
  no edit. Its "shows the base change and waits" note now covers a change GitHub made, and in
  native mode no confirmation is needed because nothing is pushed or edited.

**D5. Refreshing a branch that GitHub rewrote.**
- A layer is rewritten when `origin/<layer>` is not a descendant of the local `<layer>`.
- The skill runs `git cherry origin/<layer> <layer>`. When it shows no `+` line, the branch
  has no local-only patch. Then the skill moves the branch: `git branch -f` when the branch
  is not checked out, or `git reset --keep origin/<layer>` when it is checked out and the tree
  is clean.
- Otherwise it lists the commits and stops for that layer and every layer above it.
- This is a local pointer move to a commit that GitHub already published, so it is not a
  rewrite of pushed history by the skill. Nothing is pushed.
- The same check replaces the `git pull --ff-only` failure path in `sync` and `retarget`.

**D6. Sync stays merge-based in native mode.**
- The plain-branch merge sync works on native stacks unchanged, because merging the parent
  into a layer keeps the base chain.
- Rebase stays opt-in and gated, with the existing per-branch `--force-with-lease`.
- Why: this is conservative and matches the hard rules.
- Risk: GitHub's cascading rebase may handle layers with merge commits less cleanly. See
  Risks.

**D7. New `link` subcommand.**
- It rebuilds the plain stack (with the existing trust rules: same repository, same author).
- It checks that every listed PR is open and that the base chain holds: the bottom PR on the
  trunk, each PR above on the head of the PR below.
- It shows the ordered list and waits for confirmation. Then it calls
  `POST .../stacks` with the PR numbers.
- When the stack already exists and only new layers are on top, it uses `.../add` instead.
- Merged PRs are left out, and the stack starts at the lowest open PR.

**D8. Merging in `ep-babysit-pr`.**
- Detect stacking with `gh api repos/{o}/{r}/pulls/{n} --jq .stack`. A non-null value means
  stacked.
- Find out whether the PR is the lowest open PR from the stack itself:
  `gh api repos/{o}/{r}/stacks/{number} --jq '.pull_requests'`. It is the lowest when it is
  the first entry with `state: open` and `merged_at: null`. `position` is not used, because
  the docs do not define it.
- Merge with:
  `gh api -X PUT repos/{o}/{r}/pulls/{n}/merge-async -f sha=<last_review.head> -f merge_method=<squash|merge|rebase> -F bypass_rules=false`,
  where the method comes from the same detection as `references/score.md` and
  `merge_action` keeps its default.
- Poll `.../merge-async/{uuid}` once per babysit tick:
  - `merged` means done; confirm with `gh pr view --json state`.
  - `enqueued` waits, like `BLOCKED`.
  - `failed` reports the details and stops, with no bypass retry.
  - A 409 response (merge already pending) reuses the returned UUID.
- Do not delete the head branch. GitHub is about to rebase the PRs above, and deleting a
  stacked head is not described in the docs.
- Mid-stack PRs are never merged: the skill reports the lower open PRs and stops waiting on
  them. The skill never merges a PR below the target.
- Why: the docs name the async endpoint as required for stacks. Merging a mid-stack PR
  silently lands layers that were never babysat.

**D9. New summary keys.**
- `mode: native | branches` and `stack: <number|none>` are added to `ep-stack-summary`.
  Callers that parse only the keys they know (`ep-orchestrate` reads `layer:` lines) are
  unaffected.

**D10. Gates.**
- Creating or extending a GitHub stack is an outward action. In `split` it is covered by the
  plan approval, which names it. In `link` it gets its own confirmation.
- The async merge is gated by the existing babysit merge conditions.
- No new force-push path is added.

## Risks / Trade-offs

- [The docs are thin or in preview, and the API may change] → Pin the API version header.
  Any failure of a stack call falls back to plain-branch behaviour, or stops before an outward
  action, and the report names the endpoint and status.
- [The probe succeeds but create still fails, for example on a GHES or plan restriction] →
  The PRs stay valid as a plain stack. The skill warns and the summary shows
  `mode: branches`.
- [GitHub's cascading rebase may conflict on, or flatten, merge commits that `sync` added] →
  Report GitHub's state as `status` sees it. Document in the skill that native stacks pair
  best with few syncs. Rebase sync stays available on request.
- [The local refresh (D5) could discard work] → It only moves a branch with no local-only
  patches, uses `--keep` on a clean tree, and never pushes.
- [A babysat bottom PR's head branch stays undeleted] → The report says so, and the
  repository's auto-delete setting still applies.
- [`gh pr merge` might work on stacked PRs after all] → It is not used for them, since the
  documented API is safe either way.

## Migration Plan

Existing plain stacks keep working. `status` and `retarget` on a stack with no native object
run in plain-branch mode, even when the repository supports native stacks. `ep-stack link`
converts such a stack on request. To roll back, revert the skill files. Native stacks already
created on GitHub stay valid, and the plain-branch mode can read their body sections.

## Open Questions

- The exact semantics of the PR object's `stack.position`, and whether `gh pr merge` supports
  stacked PRs. Neither changes the plan: D8 avoids both.
