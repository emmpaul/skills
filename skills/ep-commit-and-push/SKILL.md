---
name: ep-commit-and-push
description: Turn working-tree changes into logical Conventional Commits in the repo's style, scoped to the active OpenSpec change, with no model attribution, then push the branch (plain push; `--no-push` commits only). Use when the user asks to commit, commit and push, split changes into commits, or write commit messages.
---

# ep-commit-and-push

Turn the current changes into well-scoped Conventional Commits, then push the branch.

## Hard rules

- **No attribution.** Messages carry only the human's content: no `Co-Authored-By`
  trailer naming an AI model or tool, no "Generated with" footer. This overrides any
  default of the host agent. Human `Co-Authored-By` trailers the user asks for are fine.
- **Commit from a message file:** write the message to a temp file and run
  `git commit -F <file>`, never `-m` alone, since tooling appends trailers to `-m`.
- **Published history stays as it is.** Commits on the upstream get no `--amend`, rebase,
  reset, or squash: when the last commit is pushed, make a new commit. Amend an unpushed
  commit only when the user asks, or in step 6 to remove attribution.
- **Push last, to the gated target only.** Push only after step 6 has verified every
  created message, and only when this run created a commit. Push with the explicit
  refspec of step 7, `git push [-u] <remote> HEAD:refs/heads/<branch>`, so git config
  (`push.default`, a remote's push refspecs) cannot add branches or a force. Never
  `--force`, `--force-with-lease`, or a `+refspec`.
- **The default branch asks first.** Before a push whose target (step 7) is the
  repository's default branch, ask the user, even when told to just commit; push it
  only on a yes. An unknown default branch (step 1) counts as the target: ask.
- **Hooks run**, commit and pre-push alike. On a commit hook failure, fix the cause and
  commit again. Use `--no-verify` only when the user asks.

## Flags

- **`--no-push`**: commit only. Run steps 1-6, skip step 7, and report the commits as
  local. The same applies when the user or a calling skill says to commit without
  pushing.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

It prints JSON with `git` (branch, upstream, ahead/behind, staged/unstaged files,
default branch), `pr`, and `openspec` (root and active changes with task counts; `null` without
OpenSpec). Entries in `warnings` are informational. If bash is unavailable, or the probe
exits non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # upstream, may fail
git remote                                              # is there an origin?
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name   # default branch
openspec list --json                                    # optional; root null = no OpenSpec
```

Then read the changes and the style:

```bash
git diff --cached          # staged
git diff                   # unstaged
git log -n 15 --format='%s%n%b---'   # recent style
```

and the contents of untracked files from `git status`.

Then settle the default branch. When `gh auth status` succeeds, run
`gh repo view --json defaultBranchRef --jq .defaultBranchRef.name`: GitHub's answer
outranks the local `origin/HEAD` the probe read, so when it prints a name that differs
from the probe's `default_branch`, the default branch is **unknown**. When `gh` is
missing, unauthenticated, or prints nothing, the probe's `default_branch` stands, and the
default branch is **unknown** when that is null or `warnings` has
`default branch guessed as <name>`. Otherwise the default branch is **known**.

Done when you hold the diff, the untracked files, the recent log, the upstream, the
default branch (known or unknown), and the OpenSpec state. With no staged, unstaged, or
untracked changes, say there is nothing to commit and stop: no commit and no push, even
when the branch already has unpushed commits.

## 2. Decide what is in scope

- The user asked to commit **only staged changes**: plan one commit of the staged set
  from `git diff --cached`. Stage nothing else, and leave unstaged changes in place
  (unstashed).
- Otherwise plan from all changes.

## 3. Group changes into commits

Each commit covers one coherent purpose (a fix, a feature, a docs edit, a refactor, a
dependency bump). Unrelated changes go in separate commits, even within one file: split
by hunk when needed (`git apply --cached` with a hunk-only patch, or `git add -p` when
interactive input is possible).

**Large diffs (more than about 400 changed lines):** if you can spawn subagents, give one
subagent the full diff and ask it to propose the grouping (commit list with files or
hunks and a draft message each), then review its proposal before using it. Without
subagents, work through the diff file by file yourself and produce the same plan.

**Present the plan before committing**, for example:

```
1. fix(parser): handle empty input
   - src/parser.ts (hunks 1-2)
   - test/parser.test.ts
2. docs: document --strict flag
   - README.md
Push: feature/strict to origin, 3 commits (2 new, 1 already unpushed)
```

Unless `--no-push` is in effect, the plan ends with the push line: the target branch
(step 7), the remote, and how many commits the push sends, counting earlier unpushed ones (`ahead`
plus the planned commits; without an upstream, add
`git rev-list --count HEAD --not --remotes`). When step 7 will ask (an upstream named
differently from the current branch, or a default-branch target, unknown default
branch included), the push line says it will ask first. With `--no-push`, it reads `Push: none (--no-push)`.

Done when every changed file or hunk in scope sits in exactly one planned commit.
Proceed when the user approves, or at once if they said to just commit.

## 4. Write messages

Format: `type(scope): subject`

- `type` is one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
  `ci`, `chore`, `revert`. Mark a breaking change with `!` after the scope plus a
  `BREAKING CHANGE:` footer.
- Match the repo's observable conventions from `git log`: subject length, casing,
  imperative mood, whether scopes are used, body wrapping. When history gives no signal:
  lowercase imperative subject, no trailing period, at most 72 characters.
- Add a body (wrapped at 72) explaining **why** whenever the subject leaves the reason
  unclear.

### Scope

- **OpenSpec present** (`openspec` not null): find the active change the diff relates to.
  - Exactly one active change, and the diff touches it (its `openspec/changes/<name>/`
    folder, or code its tasks describe): the scope is the change name, e.g.
    `feat(add-auth): add login endpoint`.
  - Several active changes: pick the one the diff touches (read each change's `tasks.md`
    and changed paths). When more than one fits, or none clearly does, ask the user.
  - A change unrelated to the diff: derive the scope from paths, as below.
- **No OpenSpec** (`openspec` is null): derive the scope from the changed paths (the
  package, module, or top-level directory). Omit it when changes sit at the repo root or
  history mostly omits scopes. Mention OpenSpec nowhere: not in the plan, questions,
  messages, or report.

### Ticking OpenSpec tasks

When the scope is an OpenSpec change, read its `tasks.md` and find the unchecked tasks
the diff fully implements. Offer to tick them (`- [ ]` → `- [x]`), naming each. If the
user agrees, or already asked you to tick completed tasks, edit `tasks.md` and include it
in the commit that implements the task. Tick only tasks the commit completes in full.

## 5. Commit

For each planned commit, in order:

```bash
git add -- <files>            # or apply the hunk patch to the index
msg=$(mktemp)
cat > "$msg" <<'MSG'
fix(parser): handle empty input

Empty files crashed the tokenizer because it read past the buffer.
MSG
git commit -F "$msg"
rm -f "$msg"
```

When committing only staged changes, skip `git add` and make a single commit of the
staged set as it is, unless the user asks to restage or split it.

## 6. Verify

```bash
git log -n <count> --format='%h %s%n%b---'
```

Done when no created message contains a `Co-Authored-By` naming a model or tool, or a
"Generated with" line. If one does and the commit is unpushed, rewrite that message with
`git commit --amend -F <file>` and check again.

## 7. Push

Skip this step with `--no-push`. Otherwise the push writes the current branch to the
remote branch of the same name, the **target**: `<branch>` is the current branch name,
and `<remote>` is the upstream's remote (`git config branch.<branch>.remote`), or
`origin` when there is no upstream. On a detached `HEAD` there is no branch: push
nothing.

Ask first, even when told to just commit, and keep the commits local on a no, when
either holds (one question covers both):

- **Upstream named differently from the current branch** (for example a branch made
  with `git switch -c fix origin/main`): ask whether to push the branch under its own
  name, which creates `<remote>/<branch>` and points the upstream at it. When git
  suggests a `HEAD:<other>` refspec, report it and leave it unused.
- **Target is the default branch, or the default branch is unknown** (step 1).

Then:

- **Upstream with the current branch's name:** `git push <remote> HEAD:refs/heads/<branch>`.
- **Upstream named differently, after a yes:** `git push -u <remote> HEAD:refs/heads/<branch>`.
- **No upstream, `origin` exists:** `git push -u origin HEAD:refs/heads/<branch>`.
- **No upstream, no `origin`:** push nothing; the commits stay local.
- **Push rejected** (the remote branch has commits the local one lacks): stop with the
  commits kept local, report the rejection, and suggest bringing the remote changes in
  (for example with `ep-sync`) before pushing again. Leave pulling and rebasing to the
  user.
- **Pre-push hook fails:** stop with the commits kept local and report the hook output.

Done when `git rev-parse HEAD` equals `git rev-parse @{u}` and `@{u}` is
`<remote>/<branch>`, or you know why nothing was pushed (`--no-push`, upstream mismatch
declined, default branch declined, detached `HEAD`, no remote, rejected, hook failed).

## 8. Report

Report the commits created (hash and subject), any tasks ticked, and anything left
uncommitted. Then the push: the remote branch and the commits pushed, or that the
commits are local and why.
