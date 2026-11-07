# Collect reference

How `collect` finds incident and clean cases, maps commits to PRs, asks the user about
each case, and writes the cases file. Read in `collect`, always.

## Sources

Two sources give the merged PRs and their commits:

- **GitHub** (the `origin` remote is a GitHub repository and `gh` is authenticated):
  PRs come from `gh pr list --state merged --search "merged:>=<date>" --limit 200 --json
  number,title,mergedAt,mergeCommit,baseRefName,headRefOid,author`, and a commit maps to
  its PR with `gh api repos/{owner}/{repo}/commits/<sha>/pulls`, keeping the PR that is
  merged into the default branch. A case's `base` is the PR's merge base
  (`git merge-base <merge commit>^1 <headRefOid>`) and its `head` is `headRefOid`
  (`git fetch origin pull/<n>/head` first when the head is not local).
- **Local** (no GitHub remote, `gh` missing or unauthenticated, or any other remote such
  as a bare repository): every first-parent commit of the default branch
  (`git log --first-parent --format='%H %P %ct %s' origin/<default>`, or `<default>`
  without a remote) is one merged change. For a merge commit `<m>`, `head` is its second
  parent and `base` is `git merge-base <m>^1 <m>^2` (not the first parent itself, which
  is not an ancestor of `head` when the default branch moved on before the merge); for
  any other commit, `base` is `<sha>^` and `head` is
  `<sha>`. Its `pr` is the number in the subject (`Merge pull request #<n>`, or a
  trailing `(#<n>)`), else `null`, and the case is then identified by its `merge` sha.
  A commit maps to the first-parent commit that brought it in:
  `git log --first-parent --ancestry-path --format=%H <sha>..origin/<default> | tail -1`,
  or the commit itself when it is on the first-parent line. A root commit (no parent)
  has no base and is never a case.

Say which source was used in the output (`source: github` or `source: local`). Both
give the same case shape. Read only: never fetch from or write to any remote other than
the reads above.

## Window

Incident cases are PRs **merged** within the window: the last 90 days by default, or
`--days <n>`. The fixes and reverts that reveal them may come at any time up to now.
Merge dates are the PR's `mergedAt` (GitHub) or the first-parent commit's committer date
(local).

## Reverts

```bash
git log --format='%H%x00%B%x00' --grep 'This reverts commit' origin/<default>
```

For each revert commit, take every `This reverts commit <sha>` sha in its body. Map
`<sha>` to its PR (Sources). Skip it when the PR was not merged within the window, when
`<sha>` is itself a revert (a revert of a revert), or when the revert reverts a merge
whose PR cannot be found. The proposal:

- `kind: incident`, `source: {type: revert, sha: <revert sha>}`
- `bug.file` and `bug.lines`: the largest hunk of added lines in `git diff <base> <head>`
  for the files the reverted commit changed (line numbers of the PR head). List the
  other changed files in the description so the user can pick another location.
- `bug.description`: the revert's subject and the first paragraph of its body after the
  `This reverts commit` line, or the subject alone.

## Fix forward

```bash
git log --format=%H --regexp-ignore-case --grep '^fix' origin/<default>
```

Keep commits whose **subject** starts with `fix` (Conventional `fix:`, `fix(<scope>):`,
`fix!:`, or the word "fix"/"fixes"); a body line alone does not count. Skip reverts and
merge commits (for a merged PR whose title starts with `fix`, use its commits). For each
fix commit `<fix>`:

1. Take its old-side line ranges per file from `git diff -U0 <fix>^ <fix>` (the
   `@@ -<start>,<count>` part). A pure insertion (`count` 0) blames the line above and
   the line below it, since a missing check sits next to the code it guards. Skip files
   the fix adds.
2. Blame each range at the fix's parent, ignoring whitespace:
   `git blame -w --porcelain -L <start>,<end> <fix>^ -- <file>`. Each porcelain header
   line `<sha> <orig-line> <final-line>` names the commit that last changed the line and
   its line number in that commit.
3. Map each blamed sha to its PR (Sources). Drop lines whose PR was not merged within the
   window, lines blamed to the fix's own PR, and boundary lines (`boundary` in the
   porcelain output).
4. Group the remaining lines by PR and file. For each group, find the lines at the PR
   head. When the blamed sha is in the head's history
   (`git merge-base --is-ancestor <sha> <head>` succeeds), match by commit:
   `git blame -w --porcelain <head> -- <file>` and keep the final line numbers of lines
   with the same blamed sha and original line. Otherwise the PR was squash- or
   rebase-merged and the blamed sha is the default-branch commit, which the head never
   contains, so match by content: take each blamed line's text at that commit
   (`git show <sha>:<file>`, line `<orig-line>`) and keep the head lines that
   `git diff -U0 <base> <head> -- <file>` adds with the same text, ignoring whitespace;
   when one text matches several added lines, keep the one nearest `<orig-line>`. The
   bug range is the smallest range that covers the kept lines; with lines far apart
   (more than 20 lines), make one range per cluster and propose the largest, naming the
   rest in the description. A group with no kept line gives no proposal.

The proposal: `kind: incident`, `source: {type: fix, sha: <fix>}`, `bug.file`,
`bug.lines` (at the PR head), and `bug.description` from the fix's subject and the first
paragraph of its body. One PR revealed by several fixes or reverts gives one proposal
per distinct bug location; the same location twice is proposed once.

### Worked example: a squash or rebase merge

Use this to check step 4 after editing it; the expected values are what a correct reading
gives.

1. `main` has `calc.py` with `total()` (5 lines); that commit is the PR's base.
2. PR branch `pr`: one commit appends `mean()`, so the PR head has
   `    return total(xs) / len(xs)` at line 9.
3. `main` gains a two-line header comment, then the PR lands as one squash commit (or,
   for a rebase merge, as a cherry-pick of the PR's commit). On `main` the same line is
   now line 11.
4. A fix commit `fix: mean of empty list` edits that line: `git diff -U0 <fix>^ <fix>`
   gives `@@ -11 +11 @@`.

Expected: step 2 blames line 11 to the squash (or rebased) commit, orig line 11. That
commit is **not** an ancestor of the PR head, so step 4 matches by content: the text at
the blamed commit's line 11 equals the head's added line 9, and the bug range is
`calc.py` lines 9-9. Matching by sha (`git blame <head>` lines with the blamed sha) keeps
no line and gives no proposal: that result is a regression.

## Clean cases

Propose **up to as many clean cases as incident proposals**, so the set stays balanced
(no incident proposals: no clean ones either, and say so). A clean candidate is a merged PR that:

- merged at least 30 days ago (so later fixes had time to land);
- was not reverted (Reverts) and has no line blamed by any fix commit (Fix forward,
  repeated over every fix commit since the candidate merged, not only the window);
- is not already an incident proposal or a case in the cases file;
- changes at least one path that is not documentation (prefer code over a docs-only
  change, which can never show noise).

Scan merged PRs newest first, up to 200. When there are more qualifying PRs than needed,
pick evenly spaced by merge date (for 6 out of 40, every 6th or 7th), so the sample is
not just the newest. The proposal: `kind: clean`, `bug: null`, `source: null`.

## Confirming

Show each proposal and ask **one structured question per case** (the host's question
tool when it has one), with the options **Accept**, **Edit**, and **Reject**. Show the
PR (number and title, or merge sha), base and head, the kind, and for incidents the bug
file, lines, description, and the commit that revealed it, with the bug lines quoted
from the PR head.

- **Accept:** the case is kept as shown.
- **Edit:** ask for the corrected file, line range, or description (any of them), check
  that the file exists at the head and the range is within it (ask again otherwise),
  then keep the case with the edits and `edited: true`.
- **Reject:** the case is dropped and not asked again in this run.

No flag skips these questions. When you cannot ask (no user to answer), accept nothing:
write no file and say that every case needs confirmation.

## Cases file

After the questions, when at least one case was accepted, show the path
(`<dir>/cases.json`), the accepted case ids with their kind and PR, and whether the file
is new or extended, then ask once to write it. With every case rejected, or the write
declined, write nothing.

```json
{
  "tool": "ep-review-evals",
  "version": 1,
  "repo": "<owner>/<repo> | <absolute path of the repository root>",
  "source": "github | local",
  "cases": [
    {
      "id": "i1",
      "kind": "incident",
      "pr": 12,
      "merge": "<merge or squash commit sha>",
      "base": "<sha>",
      "head": "<sha>",
      "bug": {"file": "src/a.ts", "lines": [40, 44], "description": "<from the revert or fix>"},
      "source": {"type": "revert | fix", "sha": "<sha>"},
      "edited": false,
      "confirmed_by": "<gh login | git user.name>",
      "confirmed_at": "<ISO 8601 time>"
    },
    {
      "id": "c1",
      "kind": "clean",
      "pr": 31,
      "merge": "<sha>",
      "base": "<sha>",
      "head": "<sha>",
      "bug": null,
      "source": null,
      "edited": false,
      "confirmed_by": "<login>",
      "confirmed_at": "<time>"
    }
  ]
}
```

Ids are `i<n>` for incidents and `c<n>` for clean cases, numbered after the highest id
of that kind already in the file. An existing file is extended, never rewritten: keep
its cases and add the new ones; a proposal with the same `merge` and kind (and, for
incidents, the same bug file and overlapping lines) as an existing case is not proposed
again. A file that is not valid JSON or has another `tool` is left untouched: stop and
say so. Write the file with 2-space indentation and a trailing newline, through a
temporary file in the same folder renamed over it. Never commit it or add it to
`.gitignore`.
