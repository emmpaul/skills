# Resume

Read this when `ep-orchestrate` finds `.git/ep-orchestrate/<change>.json` at its step 1.4,
before running any phase, including when the run stopped at a question or at the gate.
Step numbers name the steps of `SKILL.md`; the state file and its side files
(`<change>.findings`, `<change>.group-findings`) are described in its step 2.

`tasks.md` and git win over the state file:

0. HEAD must be on the recorded `branch`. If it is not, stop and ask the user to switch
   back to it (`git switch <branch>`); state is rebuilt only from that branch.
1. A task is **done** when its `tasks.md` line is `- [x]` **and** a commit in
   `<base-sha>..HEAD` has a `Task:` line naming `<id>` (a folded tick names two ids)
   (`git log --format='%H%n%B' <base-sha>..HEAD`).
2. If the file disagrees (a recorded sha is not on the branch, a task it marks done is
   unticked, or ticked tasks lack a commit), say exactly what differed and rebuild
   `tasks`, `groups`, and `phase` from `tasks.md` and git.
3. The clean-tree check (step 1.5) still applies; the only acceptable leftovers are
   inside the change folder. When `question` is set, uncommitted changes in exactly the
   paths in `question.files` are accepted too; any other path stops the run with outcome
   `dirty_tree`, listing those paths.
4. **Open question first.** When `question` is set, first check whether the user has
   resolved it since: for apply, its task is done (step 1 above); for fix, a commit in
   `<head>..HEAD` that is not in the `commits:` lines of `<change>.findings` has a
   `Finding:` line naming the finding's `<dimension> <file>:<line>`, where `<head>` is
   the `head` of the review that file holds (the `reviews` entry of round `<k>`, or the
   `group_reviews` entry of group `<n>` for `g<n>`), so earlier reviews' fix commits
   never match.
   - **Resolved:** set `question` to `null` without asking (for fix, append
     `commits: <finding id>=<sha>` to `<change>.findings`) and continue at the recorded
     phase.
   - **Not resolved:** ask it again at the phase question point ("Phase questions" in
     `SKILL.md`) before running any phase, then continue at the recorded phase with the
     answer. When none of `question.files` still has changes (the user discarded them),
     leave `partial:` out: the task or finding starts fresh, and the answer still
     applies.
   - **Fix question, not resolved:** with the answer, re-run the fix phase of the round
     in `<change>.findings` (step 8.4), taking the findings and their fix commits from
     that file; never run a new review for it. When that file is missing, set
     `question` to `null` and stop with outcome `blocked`: say the round's findings are
     lost and list `question.files`, which the user commits or discards before running
     again.
   - **Group fix question** (an open fix question while `phase` is `apply`): the fix
     question rules apply, with the pass's findings from `<change>.findings` labelled
     `g<n>`, re-run as step 6's group pass step 3; never a new pass.
5. **Group passes.** Rebuild each group's `start` from git: the parent of the earliest
   commit in `<base-sha>..HEAD` whose `Task:` line names a task of the group. While
   `phase` is `apply`:
   - A group with every task done and no `group_reviews` entry gets its pass (step 6)
     before the next group starts, only when no later group has a commit with a `Task:`
     line. Earlier groups are never reviewed after the fact, which also covers state
     files from before group passes.
   - An entry with `fixed: null` continues at step 6's group pass step 2, with the
     findings and fix commits from `<change>.findings` when its label is `g<n>`; its
     step 3 then fixes only findings with no fix commit yet. When that file is missing
     or has another label, run the pass again: it is read-only, and its step 1 replaces
     that entry instead of appending one.
   - A group whose entry has `fixed` set and no `g<n>` block in
     `<change>.group-findings` continues at step 6's group pass step 4 when no later
     group has a commit with a `Task:` line, whatever its status (a step-2 rebuild
     cannot tell `reviewing` from `done`), with the findings and fix commits from
     `<change>.findings` when its label is `g<n>`. When that file is missing or has
     another label, step 4 records the label `g<n>` with the note `findings lost`
     instead of its `finding:` lines.

   When step 2 above rebuilds `phase` with every task done and no `deadcode` recorded,
   the rebuilt phase stays `apply` while the last group still gets its pass, or finishes
   it, under the rules above. Once `phase` is past `apply`, no group pass runs.
6. Continue at the first unfinished phase:
   - skip planning when the artifacts exist;
   - keep a gate decision of `auto` or `approved` only while the plan is unchanged since
     it was scored (its "Plan fingerprint" in `references/confidence.md` equals
     `gate.artifacts`; ticks do not change it); otherwise re-run the gate;
   - re-ask a `paused` one;
   - continue apply at the first task that is not done;
   - run the dead-code check unless `deadcode` is recorded;
   - continue stack runs at the first unmerged layer.

Resume is done when the state file matches `tasks.md` and git, any open question is
resolved or asked, and the run has continued at the first unfinished phase.
