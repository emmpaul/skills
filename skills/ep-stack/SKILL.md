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
   base), following `ep-open-pr` conventions: Conventional Commit title for that layer's
   commits, body with Summary, Changes, (with OpenSpec) the OpenSpec section,
   Reversibility, and How to test, no attribution footer. Append the stack section:

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

## status

Fetch first (`git fetch origin`), then rebuild the stack (above), and for each layer,
bottom-up:

```bash
gh pr view <n> --json number,state,baseRefName,headRefName,reviewDecision,mergeStateStatus,statusCheckRollup
git rev-list --count origin/<layer>..origin/<parent>       # behind its parent when > 0
```

Print one row per layer: index, branch, PR, base, state (open/merged/closed), checks
(passing/failing/pending), review decision, and behind count. Flag a layer whose parent PR
has merged (needs `retarget`) and a layer behind its parent (needs `sync`). Change nothing.
Outcome `status`.

## sync

Bring every open layer up to date with the one below it, bottom-up: layer 1 with the base,
layer 2 with layer 1, and so on.

1. Run `status`. Show the layers that are behind and the branches that will be pushed;
   confirm when more than one branch will be pushed.
2. For each layer in order:
   - `git checkout <layer>` and `git pull --ff-only`. If the layer has local commits the
     remote lacks (`git rev-list --count origin/<layer>..<layer>` above 0, for example a
     merge an earlier run left unpushed after `needs_attention`), list them and stop: do
     not sync or push that layer until the user pushes or discards them.
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
   - `git checkout <layer>` and `git pull --ff-only`, so commits added on GitHub (for
     example committed review suggestions) are not lost; record
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

When a layer's PR has merged:

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

Outcome `retargeted`.

## Report and summary block

Report what was planned or changed: branches created or pushed, PRs opened or retargeted
(URLs), syncs (with their audit outcome when `ep-sync` ran), and anything waiting on the
user. Then always end with:

```
<!-- ep-stack-summary
outcome: planned | created | synced | retargeted | status
head: <sha of the current branch after the skill ran>
layer: 1 branch=<b> pr=<n|none> base=<b> state=<state>
layer: 2 branch=<b> pr=<n|none> base=<b> state=<state>
-->
```

One `layer:` line per layer, bottom-up. `state` is `planned`, `open`, `merged`, `closed`,
or `behind` (open and behind its parent).

## Without subagents

This skill needs no subagents; every agent runs the same steps in sequence. Layers are
always synced one at a time, because each depends on the one below.
