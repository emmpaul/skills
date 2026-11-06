# Plan confidence gate

The gate decides whether a change's plan is safe to implement without asking. It has two
independent parts: an evidence **score** and a **hard-to-undo checklist**. Both are
computed only from the artifacts and the repository. Never add, remove, or adjust points
from your own sense of how good the plan is: the same artifacts and repository must give
the same result.

The gate is read-only: it runs commands and reads files, and changes nothing.

## Score

Items are all-or-nothing: an item scores its full weight when met, 0 otherwise.

| # | Id | Evidence | Weight | Met when | Source |
|---|---|---|---|---|---|
| 1 | `validation` | Validation | 25 | `openspec validate <change> --strict` exits 0 | the command's exit code |
| 2 | `traceability` | Traceability | 20 | every `### Requirement:` in the change's `specs/**/spec.md` is covered by at least one tracked task (the task names it, or clearly implements its behavior) | spec headings vs `tasks.md` |
| 3 | `verifiable` | Verifiable tasks | 15 | every tracked task (`- [ ]` / `- [x]` line in `tasks.md`) states a concrete verification: a command, a test, or an observable behavior to check | `tasks.md` |
| 4 | `grounded` | Grounded | 15 | every existing file or symbol the design or tasks say to modify, rename, or delete exists in the repo (new files are exempt) | `git ls-files`, `git grep -n <symbol>` |
| 5 | `no_overlap` | No overlap | 10 | no other active change has a delta spec for the same capability, and no other active change names the same files in its proposal's Impact section | `openspec list --json`, other changes' `specs/` folders and `proposal.md` |
| 6 | `no_open_questions` | No open questions | 10 | `design.md` has no Open Questions section, or each question in it is marked deferrable; and no `TBD` or `TODO` appears in the change's artifacts | `design.md`, `grep -rn 'TBD\|TODO' openspec/changes/<change>/` |
| 7 | `size` | Size | 5 | at most 6 task groups (`## ` headings in `tasks.md` that hold tracked tasks) and at most 30 tracked tasks | `tasks.md` |
|   |   | **Total** | **100** | | |

The weights sum to 100 (25 + 20 + 15 + 15 + 10 + 10 + 5).

**Threshold: 85.** Failing item 1 alone (25 points), or items 2 and 3 together (35 points),
drops the score below 85, so invalid or unverifiable plans always pause. Any two of items
4-6 failing also pause.

For every unmet item, record one line naming what failed (for example
`verifiable: task 3.2 has no verification`), so the user sees the basis.

## Hard-to-undo checklist

Checked separately from the score. Any element found pauses the run **whatever the score
is**, even 100, and even with `--yes`. Name each element that triggered it.

Read the proposal, design, specs, and tasks, and check the repository for each item below.

### One-way doors (condensed from `ep-open-pr`, "Classifying the door")

The plan is hard to undo if it would put any of these in the diff:

- **data or schema**: changes that drop, rewrite, or migrate stored data (destructive
  migrations, backfills, format changes to persisted files or caches)
- **public interfaces**: removed or changed interfaces other people depend on: API
  endpoints, CLI flags, config keys, library exports, event or message formats, file
  formats
- **releases or publishing**: version bumps that trigger a publish, package, image, or
  artifact pushes, tags
- **external side effects**: sending email or notifications, calls to third-party APIs that
  create or delete things, billing, infrastructure creation or deletion
- **security or access**: permissions, auth flows, secrets rotation, CORS, data exposure
- **renames others reference by name**: renames or deletions of database tables or
  columns, queues, buckets, URLs, feature-flag keys

Judgment calls, as in `ep-open-pr`:

- A migration or other destructive step counts as soon as the plan puts it in the diff,
  even if nothing in the repo runs it yet.
- An interface is public when code outside this repo can reach it: anything exported
  from a published package, a documented CLI flag or endpoint, or (in an unpublished
  repo) anything the README or docs tell users to use. Code only this repo calls is
  internal.
- A version bump counts as a release only if the repo's CI or scripts publish on it;
  check the workflows before deciding.

### Hard refactors

Count with `git grep` on the exact names the tasks mention, outside `openspec/` (the
change's own artifacts do not count), and record the counts:

- renaming or moving a file or symbol referenced from **more than 10 files**
  (`git grep -l -w -e <name> -- . ':(exclude)openspec/**' | wc -l`; `-e` keeps a name
  such as `--flag` from being read as an option)
- restructuring code across **more than 3 top-level directories** (count the distinct
  first path segments of the files the tasks move, rename, or restructure; files at the
  repository root count as one segment)
- deleting a module that other modules import (`git grep -l` on its import path is
  non-empty outside the module itself)
- changing a format persisted on disk (written files, caches, lock or state files read
  back by a later run or another program)

### Uncertainty

Anything uncertain counts as hard to undo: when you cannot tell whether an element is
public, persisted, or referenced elsewhere (for example a name built dynamically, which
`git grep` cannot see), list it with what is uncertain.

**Rules that must match `ep-open-pr`** (`skills/ep-open-pr/SKILL.md`, "Classifying the
door"). Keep this list identical in meaning to that section when either changes:

- Six one-way categories: data or schema; public interfaces; releases or publishing;
  external side effects; security or access; renames or deletions others reference by
  name.
- A destructive step counts once it is in the diff, even if nothing runs it yet.
- Public means reachable by code outside the repo (published exports, documented CLI
  flags or endpoints, or what the README tells users to use); code only this repo calls
  is internal.
- A version bump is a release only if CI or scripts publish on it.
- When unsure, call it a one-way door and say what is uncertain.

## Gate decision

| Hard-to-undo found | Score | `--yes` | Result |
|---|---|---|---|
| yes | any | any | pause; name each element; wait for approval |
| no | ≥ 85 | any | proceed; print the score |
| no | < 85 | no | pause; show unmet items; options: approve, revise (run `openspec-update-change` or edit the artifacts, then re-score), stop |
| no | < 85 | yes | proceed; print the score and "proceeding on --yes" |

An existing change named by the user goes through the same gate: naming a change is not
approval of its risk. User approval after a pause is recorded as decision `approved`; an
automatic proceed as `auto`.

## Large-change thresholds

One place for the numbers stacked delivery uses:

- **Predicted large** (at the gate): more than **6** task groups or more than **30**
  tracked tasks. This is the inverse of item 7. When it holds, the gate output says
  "large: stacked delivery will be offered".
- **Large by diff** (after review): more than **800** changed lines (added + deleted) or
  more than **25** changed files against the base, excluding `openspec/` and lockfiles
  (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `Cargo.lock`, `poetry.lock`,
  `uv.lock`, `Gemfile.lock`, `go.sum`, `composer.lock`, and other `*.lock` files):

  ```bash
  git diff --numstat <base-sha>...HEAD -- . ':(exclude)openspec/**' \
    ':(exclude)**/*.lock' ':(exclude)**/package-lock.json' ':(exclude)**/pnpm-lock.yaml' \
    ':(exclude)**/go.sum'
  ```

  Sum the first two columns for lines; count rows for files.

A change is large when either holds. Report the classification with the four numbers
(groups, tasks, lines, files).

## Report format

```
Plan confidence: 90/100 (threshold 85)
  [✓] 25  validation
  [✓] 20  traceability (7/7 requirements covered)
  [✓] 15  verifiable
  [✓] 15  grounded
  [✗]  0/10 no_overlap (add-y also changes capability ep-review)
  [✓] 10  no_open_questions
  [✓]  5  size (4 groups, 14 tasks)
Hard to undo: none (counted: --old-flag in 3 files)
Decision: proceed
```

With a hard-to-undo element:

```
Hard to undo: public-interface: CLI flag --old-flag renamed (README documents it);
              hard-refactor: --old-flag referenced from 14 files
Decision: paused (hard to undo; --yes does not skip this)
```
