# Autosquash

Read this only in direct use when the user asked to autosquash (`--autosquash`, or the
same in plain words). No-rewrite mode and caller mode never reach it.

## 1. Catch up with the remote

If the branch has an upstream, first bring in commits that exist only on the remote, so
the checks below and the rewrite see them, then recompute `$mb`:

```bash
git fetch origin <branch>
git pull --ff-only
```

When local and remote have diverged, stop and report.

## 2. Check the whole range

The rebase rewrites every commit after the oldest target, so check all of them, not only
the targets:

```bash
git rev-list --merges $mb..HEAD                    # merge commits in the range
git rev-list $mb..HEAD --not --remotes | wc -l     # commits on no remote branch
git rev-list --count $mb..HEAD                     # all commits in the range
```

- **Merge commits in the range** (for example after an `ep-sync` merge): keep the fixup
  commits, say why, and stop. `--autosquash` would drop the merge and replay commits onto
  the merge base.
- **None pushed** (the two counts are equal): squash locally without further
  confirmation: `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash $mb`. An unpushed
  branch needs no push; if it has no upstream, offer `git push -u origin HEAD`.
- **Some pushed** (fewer commits on no remote than in the range): explain that the
  rewrite replaces commits already on `origin/<branch>` and that anyone who pulled them
  must reset. Ask for explicit confirmation naming the branch. Only when confirmed:
  record the remote tip's literal sha (`git rev-parse origin/<branch>`, after the pull
  above; write the sha down, since shell variables may not persist), squash, and push
  with `git push --force-with-lease=<branch>:<remote-tip-sha>`. Never a bare
  `--force-with-lease` (its lease follows the last fetch), never `--force`. Without
  confirmation, keep the fixup commits and say they can be squashed later.

If the rebase stops on a conflict, run `git rebase --abort`, keep the fixup commits, and
report.

Done when the fixups are squashed (`outcome: squashed`, `rewritten: true`) or kept with
the reason reported.
