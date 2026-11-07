# History rewrites

Read when the user approved splitting a mixed commit, or asked for `sync --rebase`
(before its confirmation, which carries the warning the user hears first). Every other
path of `ep-stack` keeps each commit as it is and pushes without force.

## Split a mixed commit

Read when the user approved, in `split` step 2, splitting a mixed commit C of layer k into
C_a (layer k) and C_b (layer k+1). Rebuild before anything is pushed:

1. Record every layer's original tip sha first.
2. Layer k: create its commits with C_a in place of C.
3. Layer k+1: start from the rebuilt layer k, commit C_b, then replay the layer's own
   commits: `git rebase --onto <rebuilt-k+1-so-far> <original tip of k> <layer k+1>`.
4. Each higher layer j: `git rebase --onto <rebuilt j-1> <original tip of j-1> <layer j>`,
   in order, so each layer descends from the rebuilt one below it.
5. Check that the top layer's tree equals the original branch's
   (`git diff <original-branch> <top-layer>` is empty).

Say which commits were rewritten (they are unpushed). Done when the diff in step 5 is
empty; then continue with `split` step 4's pushes.

## Rebase a stack

Read for `sync --rebase`. Rebase only when the user asked (`--rebase`) and confirms a
`--force-with-lease` push naming each branch, after being told that rebase mode runs no
merge audit (`ep-sync` never rebases for another skill; use merge mode to get the audit).

Before rebasing, record each layer's current parent tip (`old_parent=$(git rev-parse
origin/<parent>)`). Then, bottom-up, for each layer:

- `git checkout <layer>` and refresh it ("Refresh a layer" in SKILL.md), so commits added
  on GitHub (for example committed review suggestions) are not lost; record the literal
  sha of `git rev-parse origin/<layer>` (write it down; shell variables may not persist).
- Move only the layer's own commits onto the updated parent:
  `git rebase --onto <updated-parent> $old_parent <layer>`. A plain
  `git rebase origin/<parent>` would replay the parent's old commits.
- On a conflict, `git rebase --abort`, stop, and report; push nothing for this layer or
  any layer above it.
- Push with an explicit lease: `git push --force-with-lease=<layer>:<recorded-sha>`.
  Never `--force`.

Done when every layer is rebased and pushed with its lease, or the run stopped at a
conflict with nothing pushed for that layer or above.
