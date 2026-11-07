# Design

## Context

The existing skills (`skills/ep-*/`) share one pattern:

- a plain-instruction `SKILL.md`;
- a synced copy of `shared/context.sh`, which reports git, PR, and OpenSpec state;
- long reference material in `references/`;
- an HTML-comment summary block that other skills can read (`ep-review-summary`).

`ep-babysit-pr` merges with `gh pr merge --delete-branch`, so by the time landing runs, the remote branch is usually gone. `gh` may also have switched the checkout to the base branch and pulled it. Babysit forbids force-pushing, rebasing pushed branches, and changing repo settings. Every skill is installed folder by folder, so one skill cannot read another's files. See proposal.md for motivation and specs/ for required behavior.

## Goals / Non-Goals

**Goals:**
- Post-merge steps are idempotent: re-running `ep-land` after a partial run, or after babysit's own cleanup, is safe.
- No skill in this change writes to the default branch. Every file change goes through a branch and PR.
- Each outward action is listed with its gate (D7).

**Non-Goals:**
- Publishing packages (npm, PyPI, and so on). `ep-release` stops at the tag and the GitHub release.
- Automatic changelog generation tools such as release-please or semantic-release. The skill drafts the notes itself and respects an existing file.
- Reverting non-PR commits or partial reverts of a PR.
- Editing OpenSpec specs as part of a revert.

## Decisions

### D1. Layout

```
skills/
  ep-land/     SKILL.md  scripts/context.sh
  ep-release/  SKILL.md  scripts/context.sh  references/semver.md
  ep-revert/   SKILL.md  scripts/context.sh
```

`references/semver.md` holds the bump table, the pre-1.0 rules, the grouping order, and the changelog style detection, so that `SKILL.md` stays short. `shared/context.sh` is not changed:

- `ep-land` needs the PR's merge state and head sha, which come from `gh pr view --json state,mergedAt,headRefOid,headRefName,headRepository,isCrossRepository,mergeCommit,closingIssuesReferences`.
- `ep-release` needs tags.

Both are skill-specific queries, so adding them to the shared probe would make it larger for every skill. `sync-shared.sh` already copies the probe into any `skills/*/` folder that has a `SKILL.md`.

### D2. `ep-land`: safe local-branch deletion

A squash or rebase merge makes `git branch -d` refuse, because the branch tip is not an ancestor of the default branch. So the skill decides from evidence instead:

```
delete local branch if
    tip == PR.headRefOid                    (exactly what was merged)
 or git merge-base --is-ancestor tip origin/<default>
else keep it and list `git log origin/<default>..tip` minus the PR's commits
```

Deletion uses `git branch -D` only after this check passes. The remote branch is deleted with `git push origin --delete <head>` only when all three hold:

- the remote branch still exists (`git ls-remote`);
- the PR is not from a fork (`isCrossRepository` false);
- the remote tip equals `headRefOid`.

Anything else is reported and skipped. `git fetch --prune` always runs. If the checkout is already on the default branch (babysit or `gh` switched it), the "switch" step is a no-op.

The default branch is updated with `git pull --ff-only`. On failure (diverged), the skill reports and continues with cleanup. It never merges, rebases, or resets.

### D3. `ep-land`: archiving through a PR, not on main

Archiving (`openspec archive <change>`) moves files and updates `openspec/specs/`, so it is a commit.

- **Chosen:** an `chore/archive-<change>` branch from the fresh default branch, then `openspec archive <change> --yes`, a commit following ep-commit-and-push conventions (`chore(openspec): archive <change>`), a push, and a PR following ep-open-pr conventions (title, body, no attribution). It runs only after the user confirms the offer. It works under branch protection and gets reviewed like any other change. This is the same shape PR #1 in this repo took by hand.
- **Rejected:** committing the archive directly to the default branch. It breaks under branch protection, skips review of the generated main specs, and contradicts "never pushes to the default branch".
- **Rejected:** archiving inside the feature PR before merge. That's a valid team convention, but it isn't `ep-land`'s job, and it would change `ep-open-pr`.

Which change the PR implemented is resolved the same way babysit does it: the change named in the PR body, the commit scope, or the change folder the PR touched. Archiving is offered only when `tasks_done == tasks_total` according to the probe.

### D4. `ep-babysit-pr`: landing yes, archive no

After a merge, babysit runs landing in "local-only" mode:

- the default branch update;
- local branch deletion per D2;
- prune;
- tolerance for the remote branch already being gone.

It does not take the archive or issue-closing actions. It reports them as offers ("change X is ready to archive: run `ep-land <n>`").

Why not let babysit open the archive PR:

- Babysit runs unattended, and the archive PR is a new outward write the user didn't ask for when they started babysitting.
- It would spawn a second PR that babysit itself would then be tempted to shepherd.
- Archiving updates main specs, which deserves a human look.

So the user stays in control of everything that creates new GitHub state, while the local cleanup, which is purely local and reversible, happens automatically.

With `ep-land` installed, babysit invokes it as `ep-land <n> --caller ep-babysit-pr`, the same caller convention `add-ep-side-path-skills` defines for `ep-sync`, `ep-fixup`, and `ep-ci-debug` (for `ep-land`, caller mode means local-only: no archive, no issue closing, follow-ups returned in the summary's `pending` key). With subagents, it can delegate to a subagent running the skill. Babysit then reads the `ep-land-summary` block. Without `ep-land`, babysit follows the inline steps in a new `references/land.md` inside its own folder, which copies D2's rules. Babysit's state file gains:

```json
"landing": { "status": "done | partial | skipped", "default_head": "<sha>",
             "local_branch": "deleted | kept: <reason>", "pending": ["archive:<change>", "issue:#12"] }
```

`outcome` stays `merged` even when landing is partial.

### D5. `ep-release`: version, notes, and the changelog commit

Range: `git describe --tags --abbrev=0 --match 'v[0-9]*'` on the default branch, falling back to `[0-9]*` if the repo uses tags without a `v` prefix. The new tag keeps whichever prefix style the repo already uses (default `v`).

Classification parses each commit subject and footer:

| Signal | Bump (>= 1.0.0) | Bump (< 1.0.0) |
|---|---|---|
| `type!:` or `BREAKING CHANGE:` footer | major | minor |
| `feat` | minor | patch |
| anything else, including non-conventional | patch | patch |

PR links come from `(#123)` in squash subjects or `gh pr list --search <sha> --state merged`.

With OpenSpec, the capability section comes from `openspec/changes/archive/<date>-<name>/` folders whose archive commit is in the range (`git log --diff-filter=A --name-only <range> -- openspec/changes/archive/`). Each change's proposal Capabilities section supplies the names.

Changelog style is detected from the existing file: Keep a Changelog (`## [Unreleased]`, `### Added`), or a plain `## <version>` list. The new entry mirrors the latest existing entry.

Publication order, with confirmation of the full draft first:

```
no CHANGELOG.md  : git tag -a <v> -m <notes>  ->  git push origin <v>  ->  gh release create <v> --notes-file
with CHANGELOG.md: branch release/<v> -> commit "chore(release): <v>" -> push -> PR (stop)
                   re-run after the PR merges -> the changelog commit is in range and the entry exists
                   -> tag + release only
```

On re-run, the skill sees that `CHANGELOG.md` already has the `<v>` entry, uses it as the notes, and goes straight to tagging.

- **Rejected:** committing the changelog straight to the default branch. It breaks under protection and contradicts the no-default-branch-push rule.
- **Rejected:** tagging the release branch before merge. The tag would point at a commit that may never reach the default branch, or that changes on squash.

### D6. `ep-revert`: building the revert

```
merge method detection (gh pr view --json mergeCommit, commits):
  mergeCommit has 2 parents                 -> merge commit:  git revert -m 1 <mergeCommit>
  1 parent, and the PR's commits are found
    on the default branch by patch id      -> rebase merge: git revert <c_n> ... <c_1>
                                               (newest first, one revert commit each)
  1 parent, no PR commit found by patch id  -> squash merge: git revert <mergeCommit>
```

To detect a rebase merge, the skill finds the commits on the default branch between the merge commit's parent and the merge commit that `gh` lists as the PR's commits by patch id (`git patch-id`).

The commit message is `revert: <original title>`, with a body of `This reverts PR #<n> (<merge sha>).` plus the reason. On conflict, the skill runs `git revert --abort` after collecting the file list and later commits (`git log <merge>..origin/<default> -- <files>`), then stops.

An already-reverted PR is detected by searching the default branch log for `This reverts commit <sha>` or `This reverts PR #<n>`.

Spec drift, with OpenSpec: the change is resolved as in D3.

- If the change is archived, the skill reads its archived delta specs and lists each ADDED or MODIFIED requirement name with its capability.
- If it's active, the skill notes that its checked tasks are now false.

This only produces text in the PR body. A follow-up change is suggested (for example `revert-<change>`), and `openspec new change` is never run.

The PR body reuses ep-open-pr's reversibility classification. The revert itself is a two-way door unless the original listed one-way elements, which are carried over as "not undone".

### D7. Outward and destructive actions and their gates

| Skill | Action | Gate |
|---|---|---|
| ep-land | delete local branch | D2 evidence check; otherwise kept |
| ep-land | delete remote branch | exists, not a fork, tip == headRefOid |
| ep-land | archive branch, push, PR | user confirms offer; tasks all done |
| ep-land | close issue + comment | user confirms per batch listed |
| ep-release | push tag, create release | user confirms full draft; tag must not exist |
| ep-release | release branch + PR | user confirms full draft |
| ep-revert | push revert branch + PR | reason given; user confirms |
| ep-babysit-pr | local landing | runs only after merge is confirmed by GitHub |

None of the skills force-push, push to the default branch, move tags, merge PRs, or change repo settings.

### D8. Subagent path next to sequential fallback

| Skill | With subagents | Without |
|---|---|---|
| ep-land | none needed | inline |
| ep-release | ranges over ~200 commits: one subagent classifies commits and drafts groups; main agent reviews | classify inline |
| ep-revert | one subagent collects spec drift while the main agent builds the revert | sequential: revert, then drift |
| ep-babysit-pr | delegate landing to a subagent running `ep-land` | run `ep-land` or `references/land.md` inline |

### D9. Summary blocks

Same convention as `ep-review-summary`, so callers parse key/value lines:

```
<!-- ep-land-summary
pr: <n>
outcome: landed | partial | not_merged
default_head: <sha>
local_branch: deleted | kept | absent
remote_branch: deleted | already_gone | kept_fork | kept_moved
archive: offered:<change> | opened:<pr url> | declined | not_ready | not_applicable
issues: closed=<n> pending=<n>
-->

<!-- ep-release-summary
outcome: released | pr_opened | nothing_to_release | declined
previous: <tag|none>  version: <v>  bump: major|minor|patch
tag: <v|none>  release: <url|none>  changelog: updated | absent | pr:<url>
-->

<!-- ep-revert-summary
reverted_pr: <n>
outcome: pr_opened | conflict | declined | already_reverted | not_merged
branch: revert/pr-<n>  pr: <url|none>
spec_requirements_flagged: <n>
-->
```

## Risks / Trade-offs

- [Deleting a local branch that still had unpushed work] → delete only on exact head-sha match or ancestry; otherwise keep and list the commits.
- [Squash-merge detection is wrong for odd merge methods] → when D6 can't classify the merge with confidence, `ep-revert` stops and asks for the commits to revert instead of guessing.
- [Two-step release with a changelog is slower] → it's the price of never pushing to the default branch. The re-run detects the existing entry and only tags.
- [Version bump from inconsistent commit messages] → non-conventional commits are listed and treated as patch; the user can override the version.
- [Babysit and `ep-land` deleting the same branch] → every deletion checks existence first, so the second run is a no-op.
- [Archive PR conflicts with in-flight changes touching `openspec/specs/`] → it's a normal PR; it goes through review and CI, and the user can babysit it.
- [Spec-drift text goes stale if the revert PR is abandoned] → the text lives only in the revert PR; no spec or change is created.

## Migration Plan

Additive. Existing skills behave the same, except that `ep-babysit-pr` now cleans up the local clone after merging. Rollback is reverting the PR. Babysit's state file gains an optional `landing` field, and older state files without it get defaults, as babysit already does for missing fields.
