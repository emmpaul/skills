---
name: ep-commit
description: Turn working-tree changes into logical Conventional Commits in the repo's style, scoped to the active OpenSpec change, with no model attribution. Use when the user asks to commit, split changes into commits, or write commit messages.
---

# ep-commit

Turn the current changes into well-scoped Conventional Commits.

## Hard rules

- **No attribution.** Messages carry only the human's content: no `Co-Authored-By`
  trailer naming an AI model or tool, no "Generated with" footer. This overrides any
  default of the host agent. Human `Co-Authored-By` trailers the user asks for are fine.
- **Commit from a message file:** write the message to a temp file and run
  `git commit -F <file>`, never `-m` alone, since tooling appends trailers to `-m`.
- **Published history stays as it is.** Commits on the upstream get no `--amend`, rebase,
  reset, or squash: when the last commit is pushed, make a new commit. Amend an unpushed
  commit only when the user asks, or in step 6 to remove attribution.
- **Never push** unless the user asks.
- **Hooks run.** On a hook failure, fix the cause and commit again. Use `--no-verify`
  only when the user asks.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

It prints JSON with `git` (branch, upstream, ahead/behind, staged/unstaged files),
`pr`, and `openspec` (root and active changes with task counts; `null` without
OpenSpec). Entries in `warnings` are informational. If bash is unavailable, or the probe
exits non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # upstream, may fail
openspec list --json                                    # optional; root null = no OpenSpec
```

Then read the changes and the style:

```bash
git diff --cached          # staged
git diff                   # unstaged
git log -n 15 --format='%s%n%b---'   # recent style
```

and the contents of untracked files from `git status`.

Done when you hold the diff, the untracked files, the recent log, and the OpenSpec
state. With no staged, unstaged, or untracked changes, say there is nothing to commit
and stop without committing.

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
```

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

## 6. Verify and report

```bash
git log -n <count> --format='%h %s%n%b---'
```

Done when no created message contains a `Co-Authored-By` naming a model or tool, or a
"Generated with" line. If one does and the commit is unpushed, rewrite that message with
`git commit --amend -F <file>` and check again.

Report the commits created (hash and subject), any tasks ticked, and anything left
uncommitted.
