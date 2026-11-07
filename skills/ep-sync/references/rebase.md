# Rebase

Read this only in direct use when the user asked to rebase (`--rebase`, or "rebase onto
main"). Caller mode always merges and never reaches it.

## Before rebasing

Check whether the branch is pushed:

```bash
git rev-parse --abbrev-ref @{u}                       # upstream, may fail
git rev-list --count @{u}..HEAD                       # unpushed commits
git branch -r --contains <first-branch-commit>        # any remote holding them
```

- **Unpushed** (no remote branch contains the branch's commits): rebase with
  `git rebase $base_ref`.
- **Pushed:** explain that rebasing rewrites commits already on `origin/<branch>`, and
  that pushing needs a force-with-lease push. Ask for explicit confirmation naming the
  branch. Without it, keep the history and offer a merge instead. When confirmed, first
  bring in any commits that exist only on the remote, so the rewrite keeps them, and
  record the remote tip the push will replace:

  ```bash
  git fetch origin <branch>
  git pull --ff-only                       # fails if local and remote diverged: stop and report
  remote_tip=$(git rev-parse origin/<branch>)
  ```

  Write down the literal sha, not only a shell variable: shell state may not persist
  until the push. If the pull added commits, record the audit inputs again, so the audit
  covers them.

Done when the branch is rebased onto `$base_ref`, or the user declined and a merge was
offered.

## During and after

- Resolve conflicts as in SKILL.md step 4, then `git rebase --continue`; an incompatible
  conflict waits for the user (`git rebase --abort` leaves the branch as it was).
- Commit adaptations on top of the rebased commits, as their own commits.

## Push after a rebase

- Unpushed branch, after the user confirms: plain `git push` when it has an upstream,
  `git push -u origin HEAD` when it has none.
- Confirmed rebase of a pushed branch:
  `git push --force-with-lease=<branch>:<remote-tip-sha>`, with the literal sha recorded
  above. Never a bare `--force-with-lease` (its lease follows the last fetch), and never
  `--force`.
