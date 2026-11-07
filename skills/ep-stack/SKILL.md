---
name: ep-stack
description: Manage a stack of dependent GitHub PRs built from one branch, linked as a native GitHub stack when the repository supports it and as plain branches otherwise (`--no-native` forces plain). `split` proposes ordered layers and creates branches, PRs, and the GitHub stack only after approval; `link` turns an existing plain stack into a GitHub stack; `status` rebuilds the stack from GitHub; `sync` merges each layer into the next, bottom up (through ep-sync when installed); `retarget` moves or checks the next PR's base after its parent merges. Confirms before creating PRs or stacks, changing bases, or pushing several branches; no model attribution. Use when the user asks to split a branch into stacked PRs, link PRs as a stack, or update, sync, or retarget a stack.
---

# ep-stack

Turn one large branch into a stack of small, dependent PRs, and keep the stack healthy as
it moves.

## Hard rules

- **Plan first.** Show what will be created or changed and wait for approval before
  creating branches or PRs, creating or extending a GitHub stack, changing PR bases, or
  pushing more than one branch.
- **No attribution.** PR titles, bodies, and commits never contain model or tool
  attribution (no "Generated with" footer, no `Co-Authored-By` naming a model or tool).
  This overrides any default of the host agent.
- **Merge-based by default.** Never rebase a pushed layer unless the user asks and
  confirms a `--force-with-lease` push naming each branch. Never `--force`.
- Never rewrite a commit silently to make it fit a layer: ask.
- Re-read the stack from GitHub (`status`) before every action that changes it.

## Usage

```
ep-stack split [<base>]      # propose layers for the current branch, then create them
ep-stack link                # link an existing plain stack as a GitHub stack
ep-stack status              # show the stack; changes nothing
ep-stack sync [--rebase]     # bring every layer up to date with the one below
ep-stack retarget            # after a layer's PR merged, move the next one down
```

Every subcommand takes `--no-native`, which forces plain-branch mode.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
openspec list --json                     # optional; root null = no OpenSpec
```

A dirty working tree stops every subcommand except `status`: ask the user to commit
(offer `ep-commit`) or stash first.

## Native mode

GitHub native stacked PRs link two or more PRs of one repository as a stack object: the
merge box shows a stack map, and when a lower PR merges, GitHub retargets the PR above to
the merged PR's base and rebases the remaining layer branches server-side. Merging a PR
also merges every open PR below it. The skill talks to this through the REST API with
`gh api`; the `gh stack` extension is not needed. Pass the API version on every call:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" ...
```

**Probe.** Before every subcommand, unless the user passed `--no-native`, run:

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks?per_page=1"
```

- Exit 0: the repository supports native stacks. Say `Mode: native` in the plan or report.
- Any error (404, another status, `gh` cannot reach GitHub): plain-branch mode. Tell the
  user why in one line (endpoint and status), then run every step as written for plain
  branches.
- `--no-native`: plain-branch mode without probing.

A stack that has no GitHub stack object (for example one made before this repository had
native stacks) runs in plain-branch mode even when the probe succeeds; `link` converts it.

**Endpoints** (all under `repos/{owner}/{repo}/`):

| Call | Use |
| --- | --- |
| `GET stacks?pull_request=<n>` | the stack that contains PR `<n>` (empty list: none) |
| `GET stacks/<number>` | the stack's `pull_requests`, bottom to top |
| `POST stacks` with `pull_requests` bottom to top | create a stack; 422 when the PRs cannot form one |
| `POST stacks/<number>/add` with `pull_requests` | add PRs on top of an existing stack |

Each PR's base must be the head branch of the PR below it. When a stack call fails, fall
back to plain-branch behaviour, or stop before the outward action it was part of, and
name the endpoint and status in the report.

Native stacks pair best with few syncs: GitHub's cascading rebase may handle the merge
commits `sync` adds less cleanly. Report GitHub's state as `status` sees it.

## Stack record

The stack lives on GitHub, not in a local file. Each stack PR body ends with this section,
between the markers, listing every layer bottom-up and marking the current one:

```markdown
<!-- ep-stack -->
## Stack

1. #101 feat(auth): add token model (`feature-1-token-model`)
2. **#102 feat(auth): add login endpoint (`feature-2-login`) ← this PR**
3. #103 docs(auth): document login (`feature-3-docs`)

Base: `main`
<!-- /ep-stack -->
```

To rebuild the stack, start from the current branch's PR (or a PR number the user gives),
read the section between the markers in its body, and view every PR it lists:

```bash
gh pr view [<n>] --json number,body              # the starting PR's stack section
gh pr view <listed-n> --json number,headRefName,baseRefName,state,body,author,isCrossRepository
```

If the current branch has no PR (for example, it is the original pre-split branch), look
for PRs whose head starts with `<branch>-` and whose body has the marker:
`gh pr list --state all --limit 200 --json number,headRefName,body,author,isCrossRepository`.

Trust only PRs from this repository (`isCrossRepository: false`) whose author is the
author of the starting PR (or the current `gh` user when there is none). Drop any other
listed PR from the stack, warn about it, and never push to, merge into, retarget, or edit
it.

Order comes from the list; cross-check it with the base chain (each PR's `baseRefName` is
the previous layer's head). When they disagree, report it and trust GitHub's bases.

The body section is written in both modes. In native mode the GitHub stack is the source
of truth: when it and the body section disagree, report the difference and trust the
GitHub stack.

Branch names: `<branch>-<i>-<slug>` (for example `feature-2-login`), where `<slug>` is a
short kebab-case summary of the layer, unless the user names the branches.

## split

1. **Base and commits.** Base is the named base, else the PR base of the current branch,
   else the default branch. `git fetch origin <base>`, then
   `git log --reverse --format='%h %s' origin/<base>..HEAD` and the files each commit
   touches (`git show --stat`).
2. **Propose layers.** Group consecutive commits into ordered layers, each one reviewable on
   its own and building only on the layers below:
   - **With an OpenSpec root**, when the commits map to OpenSpec changes or task groups
     (commit scopes, touched `openspec/changes/<name>/`, task group headings in
     `tasks.md`): layers follow those boundaries.
   - **Without an OpenSpec root**: layers follow commit scopes and file areas (package,
     module, top-level directory). Do not mention OpenSpec.
   - Layers keep commit order. If a later commit is needed by an earlier layer, or **one
     commit mixes changes belonging in different layers**, say so and ask how to split it
     (for example: split that commit, move it, or merge the two layers). Do not rewrite it
     silently.
3. **Show the plan** and wait for approval or edits:

   ```
   Mode: native
   Base: main
   1. feature-1-token-model   base: main                  commits: a1b2c3d, d4e5f6a
   2. feature-2-login         base: feature-1-token-model commits: 0718293, 9a8b7c6
   3. feature-3-docs          base: feature-2-login       commits: 5e4d3c2
   Will push 3 branches, open 3 PRs, and link them as one GitHub stack.
   ```

   In plain-branch mode the plan says `Mode: branches` (with the probe's reason) and ends
   at `open 3 PRs.`

4. **Create** after approval. Each layer branch points at the last commit of its layer, so
   no commit is rewritten:

   ```bash
   git branch <layer-branch> <last-commit-of-layer>
   git push -u origin <layer-branch>          # plain push, never force
   ```

   When the user approved splitting a mixed commit C of layer k into C_a (layer k) and C_b
   (layer k+1), rebuild before anything is pushed:
   1. Record every layer's original tip sha first.
   2. Layer k: create its commits with C_a in place of C.
   3. Layer k+1: start from the rebuilt layer k, commit C_b, then replay the layer's own
      commits: `git rebase --onto <rebuilt-k+1-so-far> <original tip of k> <layer k+1>`.
   4. Each higher layer j: `git rebase --onto <rebuilt j-1> <original tip of j-1> <layer j>`,
      in order, so each layer descends from the rebuilt one below it.
   5. Check that the top layer's tree equals the original branch's
      (`git diff <original-branch> <top-layer>` is empty).
   Say which commits were rewritten (they are unpushed).
5. **Open PRs** bottom-up, each based on the previous layer's branch (the first on the
   base). Title: a Conventional Commit title for that layer's commits. Body, built from
   that layer's commits and paths only, with these sections in order and no attribution
   footer:
   - `## Summary`: 2-4 sentences on what the layer does and why.
   - `## Changes`: notable changes grouped by area, referencing commit subjects.
   - `## OpenSpec` (only when the branch implements an OpenSpec change): change name,
     a one-sentence Why from its `proposal.md`, capabilities, and tasks done/total.
   - `## Reversibility`: **One-way door** or **Two-way door** with one sentence on why
     (one-way when a revert leaves an effect: data or schema changes, changed public
     interfaces, releases, external side effects, security or access changes, renames of
     things others reference; each irreversible element on its own line with a
     mitigation), then the line
     **How to revert:** `git revert -m 1 <merge commit>` (or `git revert <squash sha>`).
   - `## Risk`: the tier in bold and one bullet per reason, by
     [`references/risk.md`](references/risk.md) over the layer's changed paths (every
     path column of `git diff --name-status -M <parent>...<layer-branch>`, both sides of
     a rename), the authenticated `gh` user as author, and `REVIEW.md` from the base; a
     one-way door makes it `high`. Raise it with a stated reason as the rules allow; never
     lower it.
   - `## Testing`: **Run:** lists only commands seen run in this session on the layer's
     head (with its short sha and result) or the latest completed CI run for that head;
     otherwise the single line `Not run`. Never invent a command, result, or sha. Then
     **Steps:**, concrete commands or checks a reviewer can repeat.

   Append the stack section:

   ```bash
   gh pr create --base <prev-or-base> --head <layer-branch> --title "<title>" --body-file <file>
   ```

   After all PRs exist, update every body with the complete list
   (`gh pr edit <n> --body-file <file>`), so each PR lists the whole stack and marks itself.
6. **Link** (native mode only). Link the PRs as one GitHub stack, bottom to top:

   ```bash
   gh api -X POST -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks" \
     -F 'pull_requests[]=101' -F 'pull_requests[]=102' -F 'pull_requests[]=103' --jq .number
   ```

   Report the stack number. When GitHub rejects the call (422, 404, or any other error),
   keep the PRs and their body sections as a plain stack, roll nothing back, warn with the
   endpoint and status, and report `mode: branches`.
7. Leave the original branch untouched. Tell the user it can be deleted once the stack is
   up; do not delete it.

Outcome `planned` when stopped at the plan, `created` after creation.

## link

Link a plain stack made by this skill as one GitHub stack. `link` needs native mode: when
the probe fails or the user passed `--no-native`, report why and stop.

1. **Rebuild** the stack from the body sections (Stack record). Here the trust rules
   refuse instead of dropping: when a listed PR comes from another repository or another
   author, report it and link nothing.
2. **Check the layers.** Leave merged PRs out; the stack starts at the lowest open PR. Refuse
   and link nothing when:
   - a layer is closed without being merged;
   - the base chain is broken: the lowest open PR is not based on the stack's base (the
     body section's `Base:`), or a PR above is not based on the head branch of the PR below.
     Report each mismatch (`#102 base: feature-x, expected feature-1-token-model`);
   - fewer than two PRs remain open (a GitHub stack needs two or more).
3. **Existing stack.** Look up the lowest open PR with `GET stacks?pull_request=<n>`. When it
   is already in a GitHub stack whose PRs are the bottom of the list, only the PRs above
   them are added. When the stack already holds every PR, report it and stop. Any other
   overlap: report both orders and stop.
4. **Confirm.** Show the PRs in stack order and what will be called, and wait:

   ```
   GitHub stack (new), bottom to top:
   1. #101 feature-1-token-model   base: main
   2. #102 feature-2-login         base: feature-1-token-model
   3. #103 feature-3-docs          base: feature-2-login
   ```

5. **Create or add** after confirmation:

   ```bash
   gh api -X POST -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks" \
     -F 'pull_requests[]=101' -F 'pull_requests[]=102' -F 'pull_requests[]=103' --jq .number
   gh api -X POST -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks/<number>/add" \
     -F 'pull_requests[]=103'                           # extending an existing stack
   ```

   On an error, report the endpoint and status; the PRs stay a plain stack. Report the
   stack number on success.

Outcome `linked`.

## status

Fetch first (`git fetch origin`), then rebuild the stack. In native mode, read it from
GitHub, starting from the current branch's PR (or the PR number the user gives):

```bash
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks?pull_request=<n>" --jq '.[0].number'
gh api -H "X-GitHub-Api-Version: 2026-03-10" "repos/{owner}/{repo}/stacks/<number>" --jq '.pull_requests'
```

The layer order is the order of `pull_requests`; apply the trust rules of the Stack record
to each PR and compare with the body section, reporting any disagreement. When the PR
belongs to no GitHub stack (empty list) or either call fails, rebuild from the body
sections as in the Stack record: the stack is in plain-branch mode, with no stack number.

Then, for each layer, bottom-up:

```bash
gh pr view <n> --json number,state,baseRefName,headRefName,reviewDecision,mergeStateStatus,statusCheckRollup
git rev-list --count origin/<layer>..origin/<parent>       # behind its parent when > 0
```

Print the mode first (`Mode: native, stack #<number>` or `Mode: branches`, with the reason
when the probe or the stack read failed), then one row per layer: index, branch, PR, base, state (open/merged/closed), checks
(passing/failing/pending), review decision, and behind count. Flag a layer whose parent PR
has merged (needs `retarget`) and a layer behind its parent (needs `sync`). Change nothing.
Outcome `status`.

## Refresh a layer

`sync` and `retarget` refresh each local layer branch from `origin/<layer>` before using
it. GitHub may have rewritten the remote branch (its cascading rebase after a lower PR
merged), and other people may have pushed to it. After `git fetch origin`:

1. **Same or behind.** When `git merge-base --is-ancestor <layer> origin/<layer>` succeeds,
   fast-forward: `git merge --ff-only origin/<layer>` when the layer is checked out, else
   `git branch -f <layer> origin/<layer>`.
2. **Diverged or ahead.** Otherwise list the local commits, merge commits included, that
   have no equivalent patch on the remote, were never pushed, and do not come from a
   merged layer:

   ```bash
   git rev-list --right-only --cherry-pick origin/<layer>...<layer> \
     $(git reflog show --format='^%H' refs/remotes/origin/<layer>) ^<merged-head> ...
   ```

   The reflog of `origin/<layer>` holds every remote tip this clone has seen, so the
   `^%H` arguments drop commits that were pushed before GitHub rewrote the branch (its
   rebase drops the merge commits that `sync` pushed). Add one `^<merged-head>` for each
   merged layer below this one: the merged PR's `headRefOid` (`gh pr view <m> --json
   headRefOid`; run `git fetch origin refs/pull/<m>/head` when the commit is not local,
   since GitHub may have deleted the branch) and, when it still exists, that layer's local
   branch. After a squash merge the merged layer's own commits are not on the rebased
   remote branch in any form, so without these exclusions they would look local-only. With
   no merged layer below (as in `sync`) the list has no `^<merged-head>` arguments.
   - Empty output: every local commit is on the remote or in a merged layer, so the local
     branch has no work of its own. Move it to the remote copy: `git branch -f <layer>
     origin/<layer>` when it is not checked out, or `git reset --keep origin/<layer>` when
     it is checked out and the tree is clean.
   - Any commit listed: it exists only locally (for example a merge an earlier run left
     unpushed after `needs_attention`). List the commits and stop for this layer and every
     layer above it: sync, retarget, and push nothing there until the user pushes or
     discards them.

This moves a local pointer to a commit already on GitHub; nothing is pushed and no pushed
history is rewritten.

## sync

Bring every open layer up to date with the one below it, bottom-up: layer 1 with the base,
layer 2 with layer 1, and so on. Sync is the same in native and plain-branch mode: merging
the parent into a layer keeps the base chain GitHub expects.

1. Run `status`. Show the layers that are behind and the branches that will be pushed;
   confirm when more than one branch will be pushed.
2. For each layer in order:
   - `git checkout <layer>` and refresh it (Refresh a layer). When the refresh stops,
     stop the stack sync there.
   - **If `ep-sync` is available to you**, invoke it for this layer with the parent as the
     base, in caller mode (`ep-sync <parent> --caller ep-stack`), so its merge audit
     applies to each layer. Read its `ep-sync-summary`. On `needs_decision` or
     `needs_attention`, stop the stack sync there, report, and do not push that layer or
     anything above it.
   - Otherwise: `git merge --no-ff origin/<parent>` (message file, no attribution),
     resolving conflicts that preserve both sides and stopping on incompatible ones.
   - Push with plain `git push`, so the next layer merges the updated parent.
3. **Rebase** only when the user asked (`--rebase`) and confirms a `--force-with-lease`
   push naming each branch, after being told that rebase mode runs no merge audit
   (`ep-sync` never rebases for another skill; use merge mode to get the audit). Before
   rebasing, record each layer's current parent tip (`old_parent=$(git rev-parse
   origin/<parent>)`). Then, bottom-up, for each layer:
   - `git checkout <layer>` and refresh it (Refresh a layer), so commits added on GitHub
     (for example committed review suggestions) are not lost; record
     the literal sha of `git rev-parse origin/<layer>` (write it down; shell variables may
     not persist).
   - Move only the layer's own commits onto the updated parent:
     `git rebase --onto <updated-parent> $old_parent <layer>`. A plain
     `git rebase origin/<parent>` would replay the parent's old commits.
   - On a conflict, `git rebase --abort`, stop, and report; push nothing for this layer or
     any layer above it.
   - Push with an explicit lease: `git push --force-with-lease=<layer>:<recorded-sha>`.
     Never `--force`.

Outcome `synced`.

## retarget

When a layer's PR has merged. In native mode, follow **Native retarget** below; the steps
here are the plain-branch retarget.

1. Run `status`. Find each merged layer and the next open layer above it.
2. Show the change, including every branch that will be pushed by the sync in step 3, and
   wait for confirmation:

   ```
   #102 feature-2-login: base feature-1-token-model -> main  (parent #101 merged into main)
   push: feature-2-login (merge of main)
   ```

3. Change the base, then sync the layer with its new base (through `ep-sync` when it is
   available, as in `sync`), and push without force:

   ```bash
   gh pr edit <n> --base <merged-pr-base>
   ```

   When the parent was squash-merged, the merge brings in the squashed commit, and the
   parent's original commits are still in the layer's history; the PR diff on GitHub shows
   only the layer's changes once the base is updated. Say so if the user asks why the
   history looks doubled.
4. Update the stack section in every remaining PR body: mark merged layers as merged and
   keep the order.

### Native retarget

GitHub retargets and rebases the layers above a merged PR itself, so the skill checks
that work and changes no base.

1. Run `status`. Find each merged layer and the next open layer above it.
2. Check that the next PR's `baseRefName` is now the merged PR's `baseRefName`
   (`gh pr view <n> --json baseRefName`). When it still names the merged branch, wait
   about 30 seconds and check once more.
3. **GitHub retargeted:** refresh every remaining local layer branch, bottom-up (Refresh a
   layer), and run no merge-sync: GitHub has already rebased the layer onto its new base.
   No confirmation is needed, since nothing is pushed and no base is edited.
4. **GitHub did not retarget:** report the PR and the base it still has, then offer the
   plain retarget (steps 2 to 4 above), which changes the base only after the user
   confirms.
5. Update the stack section in every remaining PR body, as in step 4 above (this edits
   only the bodies). Report each next PR's new base, for example `#102 base: main (set by
   GitHub)`.

Outcome `retargeted`.

## Report and summary block

Report what was planned or changed: branches created or pushed, PRs opened or retargeted
(URLs), syncs (with their audit outcome when `ep-sync` ran), and anything waiting on the
user. Then always end with:

```
<!-- ep-stack-summary
outcome: planned | created | linked | synced | retargeted | status
mode: native | branches
stack: <GitHub stack number | none>
head: <sha of the current branch after the skill ran>
layer: 1 branch=<b> pr=<n|none> base=<b> state=<state>
layer: 2 branch=<b> pr=<n|none> base=<b> state=<state>
-->
```

`mode` is the mode the skill ran in: `branches` when the probe failed, a link or stack read
failed, or an existing stack has no GitHub stack object. `stack` is `none` until a GitHub
stack exists, and always in `branches` mode. One `layer:` line per layer,
bottom-up. `state` is `planned`, `open`, `merged`, `closed`,
or `behind` (open and behind its parent).

## Without subagents

This skill needs no subagents; every agent runs the same steps in sequence. Layers are
always synced one at a time, because each depends on the one below.
