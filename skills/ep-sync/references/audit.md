# Merge audit

The audit looks for semantic interactions between what the base brought in and what the
branch changed. A merge with no textual conflicts can still leave the branch wrong, so
the audit runs after every sync, conflicts or not. Done when all five checks have run,
every interaction sits in a cluster with exactly one class and its evidence, and the
report table is printed.

## Inputs

Compute these **before** the merge commit (or before the rebase), and keep them:

```bash
mb=$(git merge-base HEAD <base-ref>)
git log --format='%h %s' $mb..<base-ref>        # B: incoming base commits
git diff -M $mb <base-ref>                       # B's diff
git diff -M $mb HEAD                             # R: the branch's own diff
git diff -M --name-status $mb <base-ref>         # B's files, with renames
git diff -M --name-status $mb HEAD               # R's files, with renames
```

For a rebase, `HEAD` above is the branch tip before rebasing (`ORIG_HEAD` afterwards).

Collect **R's identifiers**: every function, method, class, type, constant, config key,
table, column, route, and exported name that R's hunks define, call, import, override,
read, or write. Use the hunk headers (`@@ ... @@ <function>`) and the added or changed
lines. The audit covers these identifiers only, which keeps large base updates
manageable.

## The five checks

Run each check and record every hit as an **interaction**: base commit, base location,
branch location, and what connects them.

### 1. Symbols the branch uses that base changed

For each identifier R uses but does not define itself, search B's diff for:

- **removed or renamed**: the definition line is deleted, or moved under another name
  (`git log -M --format=%h -S'<name>' $mb..<base-ref>` finds the commits; a rename shows
  as a deleted definition plus an added one with the same body).
- **re-signatured**: the definition line changes its parameters, required arguments,
  return type, generics, or decorators. List **every** branch call site affected, not only
  the first (`git grep -n '<name>(' HEAD -- <files R touched>`).
- **changed behaviour**: the body changes its return value, raised errors, side effects
  (I/O, mutation, events), defaults, or ordering. Report the dependency (where the branch
  relies on it) and the behaviour change (what base now does differently).

This check covers a rename used in a file base never touched: the hit comes from R's
identifier list, not from overlapping files.

### 2. Contracts touched by both sides

A contract is anything read or written across a boundary: database schemas and
migrations, ORM models, config keys and env vars, API routes, request/response shapes,
serialized formats, public type definitions, CLI flags, event names. Report an
interaction when B changes a contract that R reads, writes, or also changes. Examples:
base renames config key `retry_count` to `retries` while the branch reads `retry_count`;
base adds a migration that drops a column the branch's query selects; both sides add
migrations with the same sequence number.

### 3. New base callers of branch-modified code

For each function or method whose body or signature R changed, search B's **added** lines
for new call sites. Each new caller is affected by the branch: it was written against the
old behaviour, and after the merge it runs the branch's version.

### 4. Base tests covering branch code

List test files B added or changed (paths under `test/`, `tests/`, `__tests__/`, `spec/`,
or named `*test*` / `*spec*`) that import, call, or name a file or identifier R modified.
Report each so it is run after the sync and its assertions are checked against the
branch's behaviour.

### 5. Spec overlap (only with an OpenSpec root and an active change for this branch)

Run this check only when the repository has an OpenSpec root and the branch implements
an active change. Otherwise skip it and leave it, and OpenSpec, out of the report.

Otherwise, take the capabilities the active change touches (its
`openspec/changes/<name>/specs/<capability>/` folders). Report each base commit that:

- edits `openspec/specs/<capability>/spec.md` for one of those capabilities, or
- archives a change (adds `openspec/changes/archive/*/`) whose specs touch one of them, or
- adds an active change under `openspec/changes/` touching one of them.

Name the requirements on both sides: the base requirement headers that were added,
modified, or removed, and the branch change's requirements for the same capability.

## Clustering

Group interactions that share a file or an identifier into one **cluster**. A rename of
`load_user` with three branch call sites is one cluster, not three. Each cluster is
audited as a unit: read the code on both sides, then classify each interaction in it.

- **With subagents:** one subagent per cluster. Give it the cluster's interactions, the
  base commits' diffs for those files, the branch's diff for those files, and the
  classification rules below. Ask for each interaction's class, evidence, and, for
  needs-update, a proposed patch, or the options when more than one fix is reasonable.
  Subagents only propose; the main agent reviews and applies the patches.
- **Without subagents:** audit the clusters one after another inline, with the same
  rules. The report is identical.

## Classes

Every interaction gets exactly one class and its evidence.

| Class | Meaning | Example |
|---|---|---|
| **needs-update** | the branch is wrong with the new base unless it changes | base renamed `get_user` to `fetch_user`; `src/api/profile.py:42` on the branch still calls `get_user` |
| **review** | it may matter, and a person should look; the audit cannot decide from the code | base changed `parse_date` to return UTC; the branch formats its result for display in `src/report.py:18`, and whether local time was intended is unclear |
| **no-impact** | checked, and harmless | base reformatted `utils.py`, which the branch imports, without changing any definition the branch uses |

A needs-update interaction with more than one reasonable fix that behaves differently
(for example: base made `timeout` required, and the branch could pass the old default or
the caller's configured value) is **ambiguous**: present the options and stop
(`needs_decision`), leaving the choice to the user.

## Report table

Print every interaction as a row: needs-update and review rows first, then no-impact rows,
each with its evidence (base commit, branch location, reason). Large audits may group
no-impact rows that share a base commit and reason into one row listing the locations.

```
## Merge audit: <branch> <- <base>@<short-sha> (<n> incoming commits)

| # | Class | Check | Base commit | Branch location | Reason | Resolution |
|---|---|---|---|---|---|---|
| 1 | needs-update | symbol renamed | a1b2c3d refactor(users): rename get_user | src/api/profile.py:42 | calls `get_user`, removed in base | updated in 9f8e7d6 |
| 2 | review | behaviour | e4f5a6b fix(dates): normalise to UTC | src/report.py:18 | formats `parse_date` result for display | listed for review |
| 3 | no-impact | symbol changed | 7c8d9e0 style(utils): reformat | src/api/profile.py:3 | imports `slugify`; definition unchanged, only reformatted | none needed |

Totals: needs-update 1, review 1, no-impact 1
Checks run: symbols, contracts, new callers, tests[, spec overlap]
```

Resolution is one of: `updated in <sha>`, `options presented` (ambiguous), `listed for
review`, `none needed` (no-impact), `unresolved: <why>`. When the audit finds nothing,
print `No interactions found.` and still list the checks run.

## Summary keys

The audit fills these keys of the `ep-sync-summary` block (the block itself is in
SKILL.md):

```
audit: needs_update=<n> review=<n> no_impact=<n>
unresolved_needs_update: <n>
```

`needs_update` counts every needs-update interaction found; `unresolved_needs_update`
counts those without an adaptation commit (ambiguous ones, or ones that could not be
fixed). With no interactions, every count is 0.
