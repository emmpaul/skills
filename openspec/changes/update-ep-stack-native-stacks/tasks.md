# Tasks

## 1. ep-stack native mode

- [x] 1.1 In `skills/ep-stack/SKILL.md`:
  - Update the frontmatter description and Usage: native stacks when available, plain-branch
    fallback, the `link` subcommand, and `--no-native`.
  - Add a "Native mode" section. It covers the probe and fallback (D2), the
    `X-GitHub-Api-Version: 2026-03-10` header, and the endpoints used (D1). It also says the
    `gh stack` extension is not needed.

  Verify: every scenario of "Native stack detection" in
  `openspec/changes/update-ep-stack-native-stacks/specs/ep-stack/spec.md` maps to text, and
  `grep -n "gh extension install" skills/ep-stack/SKILL.md` finds nothing.
- [x] 1.2 Update `split`:
  - The plan line names the GitHub stack, and the PRs are linked bottom-up through
    `POST .../stacks` after they are opened.
  - On a rejected link, the PRs stay a plain stack and the skill warns.
  - Update the Stack record text so that in native mode the GitHub stack wins on
    disagreement (D3).

  Verify: the "Native stack linking on split", "Stack creation", and "Outward action gate"
  scenarios map to text.
- [x] 1.3 Update `status` to read the stack from `GET .../stacks?pull_request=<n>`, then
  `GET .../stacks/{number}`, in native mode, and fall back to the body section. Show the mode
  and stack number. Verify: the "Stack status and summary block" scenarios map to text.
- [x] 1.4 Add the refresh rule for layers that GitHub rewrote (D5) and use it in `sync`
  and `retarget` where `git pull --ff-only` is today. Keep merge-default sync and the gated
  rebase unchanged (D6). Verify: the "Refresh layers rewritten by GitHub" and "Stack sync"
  scenarios map to text. Also verify in a scratch local repo that `git cherry` shows no `+`
  line after the remote branch is rebased with identical patches, and shows a `+` line after
  a local-only commit is added.
- [x] 1.5 Update `retarget` for native mode (D4): check the retarget GitHub made, re-check
  once, offer the gated plain retarget when GitHub did not retarget, refresh local branches,
  update the body sections, and run no merge-sync. Verify: the "Retarget on parent merge"
  scenarios map to text.
- [x] 1.6 Add the `link` subcommand (D7): trust rules, open and chain checks, confirmation,
  create or add. Add `mode:` and `stack:` to the `ep-stack-summary` block (D9). Verify: the
  "Link an existing stack" scenarios map to text, and the summary block in SKILL.md lists
  `mode` and `stack`.
- [x] 1.7 Update the `ep-stack` row in `README.md` to match the new frontmatter description.
  Verify by comparing the two texts.

## 2. ep-babysit-pr stacked merge

- [x] 2.1 In `skills/ep-babysit-pr/SKILL.md` step 7 (the merge) and the Merge command in
  `skills/ep-babysit-pr/references/score.md`, add the stacked-PR path from D8:
  - stack detection
  - the lowest-open-PR check
  - `merge-async` pinned to `last_review.head`, with `bypass_rules=false`
  - polling and outcomes (`merged`, `enqueued`, `failed`, and 409)
  - no branch delete
  - stopping on a mid-stack PR

  Keep the non-stacked `gh pr merge` path unchanged. Verify: every scenario of "Merging a PR
  in a native stack" and the modified "No protection" scenario in
  `openspec/changes/update-ep-stack-native-stacks/specs/ep-babysit-pr/spec.md` maps to text,
  and the forbidden-actions list is unchanged.

## 3. Integration

- [x] 3.1 Run `scripts/check-shared.sh` and verify that it passes. No shared file changes,
  but the skill folders must stay in sync.

## Manual check (run by the user after review; not a tracked task)

This check creates PRs, a GitHub stack, and a merge, so no phase worker runs it.
On a sandbox GitHub repository, the user runs `ep-stack split` on a 3-layer branch. Verify:
  - In a repository where the stacks endpoint answers, the PRs are linked as one GitHub
    stack (`gh api repos/{o}/{r}/stacks?pull_request=<n>` lists all three in order).
  - Merge the bottom PR with `ep-babysit-pr`, which uses `merge-async`. Then `ep-stack
    retarget` reports PR 2 on `main` without editing its base, and refreshes the local
    branch.
  - Running `ep-babysit-pr` on the top PR refuses to merge.
  - With `--no-native`, the old flow runs unchanged.

  If native stacks are not available to the sandbox account, record that the plain-branch
  fallback ran and that the native path was verified only against the documented API
  shapes.
