---
name: ep-commit
description: Turn working-tree changes into one or more logical Conventional Commits that match the repo's style, scoped to the active OpenSpec change when there is one, with no model attribution. Use when the user asks to commit, split changes into commits, or write commit messages.
---

# ep-commit

Turn the current changes into well-scoped Conventional Commits.

## Hard rules

- **No attribution.** Commit messages never contain model or tool attribution: no
  `Co-Authored-By` trailer naming an AI model or tool, no "Generated with" footer. This
  overrides any default of the host agent. Human `Co-Authored-By` trailers the user asks
  for are fine.
- **Always commit with a message file:** write the message to a temp file and run
  `git commit -F <file>`. Never use `-m` alone with tooling that appends trailers.
- **Never rewrite published history.** No `--amend`, rebase, reset, or squash of commits
  that exist on the upstream. If the last commit is already pushed, make a new commit.
  Only amend an unpushed commit when the user explicitly asks.
- **Never push** unless the user asks.
- Never skip hooks (`--no-verify`) unless the user asks. If a hook fails, fix the cause and
  create the commit again.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

It prints JSON with `git` (branch, upstream, ahead/behind, staged/unstaged files),
`pr`, and `openspec` (root and active changes with task counts; `null` without OpenSpec).

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # upstream, may fail
openspec list --json                                    # optional; root null = no OpenSpec
```

Then always read:

```bash
git diff --cached          # staged
git diff                   # unstaged
git log -n 15 --format='%s%n%b---'   # recent style
```

Include untracked files from `git status` (read their contents).

If there are no staged, unstaged, or untracked changes, say there is nothing to commit and
stop. Make no commit.

## 2. Decide what is in scope

- If the user asked to commit **only staged changes**, plan only from `git diff --cached`
  (one commit of the staged set). Do not stage anything else, and leave unstaged changes
  untouched (do not stash them).
- Otherwise plan from all changes.

## 3. Group changes into commits

Each commit covers one coherent purpose (a fix, a feature, a docs edit, a refactor,
a dependency bump). Unrelated changes go in separate commits, even within one file: split
by hunk when needed (`git apply --cached` with a hunk-only patch, or `git add -p` when
interactive input is possible).

**Large diffs (more than about 400 changed lines):** if you can spawn subagents, give one
subagent the full diff and ask it to propose the grouping (commit list with files/hunks and
a draft message each); review its proposal before using it. If you cannot spawn subagents,
work through the diff file by file yourself and produce the same plan. The result must be
the same either way.

**Present the plan before committing**, for example:

```
1. fix(parser): handle empty input
   - src/parser.ts (hunks 1-2)
   - test/parser.test.ts
2. docs: document --strict flag
   - README.md
```

Proceed when the user approves (or immediately if they said to just commit).

## 4. Write messages

Format: `type(scope): subject`

- `type` is one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`,
  `ci`, `chore`, `revert`. Use `!` after the scope plus a `BREAKING CHANGE:` footer for
  breaking changes.
- Match the repo's observable conventions from `git log`: subject length, casing,
  imperative mood, whether scopes are used, body wrapping. When history gives no signal:
  lowercase imperative subject, no trailing period, at most 72 characters.
- Add a body (wrapped at 72) explaining **why** whenever the reason is not evident from the
  subject.

### Scope

- **OpenSpec present** (`openspec` not null): find the active change the diff relates to:
  - exactly one active change, and the diff touches it (its `openspec/changes/<name>/`
    folder, or code its tasks describe): scope is the change name, e.g.
    `feat(add-auth): add login endpoint`.
  - several active changes: pick the one the diff touches (read each change's `tasks.md`
    and changed paths); if more than one fits or none clearly fits, ask the user.
  - a change unrelated to the diff: derive scope from paths as below.
- **No OpenSpec** (`openspec` is null): derive scope from the changed paths (the package,
  module, or top-level directory). Omit the scope when changes sit at the repo root or
  the repo's history mostly omits scopes. Do not mention OpenSpec anywhere.

### Ticking OpenSpec tasks

When the scope is an OpenSpec change, read its `tasks.md` and identify unchecked tasks the
diff fully implements. Offer to tick them (`- [ ]` → `- [x]`), naming each task. If the
user agrees (or already asked you to tick completed tasks), edit `tasks.md` and include it in the commit that implements the task. Never
tick a task that is only partly done.

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
staged set. Do not restage or split it unless the user asks.

## 6. Verify and report

```bash
git log -n <count> --format='%h %s%n%b---'
```

Check that no created message contains `Co-Authored-By` naming a model or tool, or a
"Generated with" line. If one does and the commit is not pushed, rewrite that message with
`git commit --amend -F <file>` (allowed here: it is your unpushed commit and removes
attribution), then re-check.

Report the commits created (hash and subject), any tasks ticked, and anything left
uncommitted. Do not push.
