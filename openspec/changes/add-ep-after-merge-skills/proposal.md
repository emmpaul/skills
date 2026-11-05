# Proposal

## Why

The `ep-*` chain stops when the PR merges. Everything after that is still done by hand and is easy to forget: deleting the branch, pulling the default branch, archiving the OpenSpec change, closing linked issues, cutting a release, and reverting a bad merge. In this repo, change `add-ep-git-workflow-skills` was archived by hand in its own PR (#1). Releases and reverts have no tooling at all, even though every commit is already a Conventional Commit and changes are scoped to OpenSpec changes, which are exactly the inputs those two tasks need.

## What Changes

- Add `ep-land` (new): after a PR has merged, cleans up the local clone and closes the loop.
  - Confirms the merge with `gh`, switches to the default branch, fast-forwards it, deletes the local and remote branch, and prunes.
  - With OpenSpec, offers to archive the PR's change when all its tasks are done, through a separate archive branch and PR.
  - Offers to close linked issues that GitHub did not close automatically.
- Add `ep-release` (new): proposes the next semantic version from the Conventional Commits since the last tag and drafts release notes.
  - Notes are grouped by commit type and, with OpenSpec, by the capabilities of changes archived since that tag.
  - Updates `CHANGELOG.md` in its existing format when the file exists.
  - Creates the tag and the GitHub release only after the user confirms the draft.
- Add `ep-revert` (new): reverts a merged PR on a new branch and opens a revert PR that states the reason and impact.
  - With OpenSpec, lists the specs that would overstate behavior after the revert and suggests a follow-up change, without editing specs.
- Modify `ep-babysit-pr`: after a successful merge it runs `ep-land`, or its inline equivalent, for local cleanup, and records the result in its state file. OpenSpec archiving and issue closing stay offers to the user; babysit does not do them on its own.
- Add the three skills to the README skills table and install commands.

New outward effects on GitHub:

- `ep-land`: deletes the remote branch if it still exists; pushes a `chore/archive-<change>` branch and opens a PR (gated); closes issues (gated).
- `ep-release`: pushes a tag and creates a GitHub release (gated). With a `CHANGELOG.md`, the changelog commit goes through a release PR, never a direct push to the default branch.
- `ep-revert`: pushes a revert branch and opens a PR (gated).
- `ep-babysit-pr`: no new GitHub writes. It already deletes the remote branch through `gh pr merge --delete-branch`; local cleanup only changes the local clone.

## Capabilities

### New Capabilities
- `ep-land`: post-merge cleanup of the local clone, remote branch, OpenSpec change, and linked issues.
- `ep-release`: semantic version selection, release notes and changelog drafting, and gated tag and GitHub release creation.
- `ep-revert`: reverting a merged PR through a revert PR, with spec-drift flagging.

### Modified Capabilities
- `ep-babysit-pr`: adds a post-merge landing requirement. Existing requirements are unchanged.

## Impact

- New files: `skills/ep-land/`, `skills/ep-release/`, `skills/ep-revert/` (each with `SKILL.md` and a synced `scripts/context.sh`, plus `references/` where needed).
- Modified: `skills/ep-babysit-pr/SKILL.md` (merge and stop steps), `README.md`.
- `shared/context.sh` is unchanged; the new skills run their extra `git`/`gh` queries inline.
- Sequencing: `add-ep-side-path-skills` modifies other `ep-babysit-pr` requirements. This change only adds a requirement, so the two can merge in either order.
- Runtime dependencies are unchanged: `git`, `gh`, optional `openspec` and `bash`.
