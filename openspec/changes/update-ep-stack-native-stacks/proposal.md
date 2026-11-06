# Proposal

## Why

GitHub now has native stacked pull requests
(https://docs.github.com/en/pull-requests/get-started/about-stacked-prs). A stack is a
first-class object on GitHub, with a stack map in the merge box and REST endpoints to create,
read, extend, and dissolve it. When a lower PR merges, GitHub retargets and rebases the PRs above
it. Merging a PR also merges every open PR below it. `ep-stack` predates this. It builds stacks
from plain branches and keeps the stack record in PR bodies. In a repository with native stacks,
that has three problems: the PRs are not linked as a stack on GitHub; `retarget` redoes work that
GitHub already did; and after GitHub rebases a layer, the local branches go stale, so the next
plain push fails. `ep-babysit-pr` also merges with `gh pr merge`, but GitHub documents the async
merge endpoint as the required API for stacked PRs. Merging a mid-stack PR would also merge
layers below it that nobody babysat.

## What Changes

- **Modified** `ep-stack`:
  - Detects whether the repository supports native stacks: it reads the stacks endpoint
    through `gh api`. Native mode is used when the endpoint answers. Otherwise, or with
    `--no-native`, the skill runs the current plain-branch behaviour unchanged.
  - `split`, in native mode: creates branches and PRs as today, then links them as one GitHub
    stack (`POST /repos/{owner}/{repo}/stacks`). The approval plan says so. If linking fails,
    the PRs stay a plain stack and the skill warns.
  - New `link` subcommand: links an existing plain `ep-stack` stack as a native stack, after
    confirmation.
  - `status`: in native mode, the GitHub stack is the source of truth. The body section is the
    fallback. The output shows the stack number and mode.
  - `retarget`, in native mode: checks that GitHub has already moved the next PR's base. It
    does not edit bases. It refreshes stale local branches and updates the body sections. When
    GitHub has not moved the base, the skill reports this and offers the plain retarget, which
    is gated.
  - `sync`: still merge-based by default, with the same gated rebase. New: a local layer
    branch that GitHub rewrote on the remote is reset to the remote copy, but only when the
    local branch has no commits of its own. Otherwise the skill stops.
  - The `ep-stack-summary` block gains `mode: native | branches` and `stack: <number|none>`.
- **Modified** `ep-babysit-pr`: for a PR in a native stack, it merges only when the PR is the
  lowest open PR of the stack. It merges through the async merge endpoint with the reviewed
  head sha, the repository's merge method, and no bypass. It waits for a `merged` result and
  does not delete the head branch. Otherwise, merge behaviour is unchanged.
- No delta for `ep-orchestrate` or `ep-sync`. `ep-orchestrate` already babysits only the
  bottom layer, then calls `ep-stack retarget`, which keeps its contract (the `layer:` lines).
  `ep-sync` caller mode is unchanged.

Outward effects on GitHub:
- `ep-stack` creates a GitHub stack object (`split` and `link`), after the plan or link
  confirmation. In native mode it no longer changes PR bases unless GitHub has failed to do
  so and the user confirms.
- `ep-babysit-pr` merges stacked PRs through `PUT .../pulls/{n}/merge-async` instead of
  `gh pr merge`, and does not delete their head branches.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `ep-stack`: native stack detection with plain-branch fallback, native linking on split, a
  new `link` subcommand, native-aware status and retarget, refresh of layers that GitHub
  rewrote, and new summary keys.
- `ep-babysit-pr`: how a PR in a native stack is merged (bottom-only, async merge endpoint,
  no branch delete).

## Impact

- `skills/ep-stack/SKILL.md`: frontmatter description, usage, a native-mode section, and the
  split, status, sync, and retarget changes, plus the new link subcommand and summary keys.
- `skills/ep-babysit-pr/SKILL.md` and `skills/ep-babysit-pr/references/score.md`: the
  merge step and the merge command.
- `README.md`: the `ep-stack` row.
- `shared/context.sh` is unchanged. Stack API calls run inline through `gh api`. Nothing
  depends on the `gh stack` extension.
- Sibling change `add-ep-after-merge-skills` adds post-merge requirements to `ep-babysit-pr`.
  This change modifies only "Merge decision defers to GitHub" and adds a stacked-merge
  requirement, so the two do not overlap.
