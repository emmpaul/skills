# Noise reference

How `noise` finds the reviews `ep-review` posted, classifies the author's response to
each posted finding, and proposes `REVIEW.md` lines. Read in `noise`, always. Read-only:
`noise` writes no file and posts nothing.

## Needs GitHub

`noise` reads PR reviews, so it needs the GitHub source (`references/collect.md`,
Sources). With the local source, say that `noise` reads PR reviews from GitHub and this
repository has none, and stop with zero counts.

## Posted reviews

PRs in range are those updated within the window (90 days, or `--days <n>`), any state:

```bash
gh pr list --state all --search "updated:>=<date>" --limit 200 --json number,author,headRefOid
gh api repos/{owner}/{repo}/pulls/<n>/reviews --paginate     # keep reviews whose body contains <!-- ep-review-summary
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate    # inline comments and their replies
```

An `ep-review` review is one whose body contains `<!-- ep-review-summary`. Its **posted
findings** are its inline comments (`pull_request_review_id` equal to the review's id)
and the finding lines in its body (`- [<severity>] ...`). Each has a severity, a
dimension, a file and line, a summary, and a class: the `Class:` text when the comment
or body line has one, otherwise a short label you give from the summary (the same label
for the same kind of defect across PRs). Findings tagged `pre-existing` are classified
too, and reported apart.

With no `ep-review` review on any PR in range, say so, suggest running
`ep-review <pr> --comment` on the next PRs, and stop.

## Response classes

Classify each posted finding by the first rule that applies:

| Class | Rule |
|---|---|
| `wrong` | a reply says the finding is incorrect: "not a bug", "false positive", "wrong", "can't happen", "already handled", or it explains why the scenario cannot occur |
| `intentional` | a reply says the behavior is deliberate: "intended", "by design", "on purpose", "expected" |
| `did not matter` | a reply accepts it but declines to act: "won't fix", "not worth it", "nit", "doesn't matter", "out of scope", "later" |
| `fixed` | a commit after the review's `commit_id` changed the finding's file within 3 lines of its line (`git diff <commit_id> <headRefOid> -- <file>`, after `git fetch origin pull/<n>/head`). A later `ep-review` review that does not repeat the finding is no evidence: `--comment` leaves already-posted findings out of later reviews |
| `unanswered` | none of the above |

A **reply** is a comment in the finding's thread (`in_reply_to_id` equal to the finding's
comment id), or for a body finding a later PR comment that quotes or names it, written by
anyone but the reviewer that posted it. Judge the reply's meaning, not only the cue words;
a reply that fits no class (a question, a thank you) does not count, and the next rule
applies. Quote each classifying reply's first line in the report.

## `REVIEW.md` suggestions

Group findings answered `wrong` or `did not matter` by class and path. A group that
covers **3 or more distinct PRs** gets one proposed line. The path is the shared file
when all are in one file, else the narrowest glob covering them (`src/gen/**`). Propose
a guidance bullet, which `ep-review` passes to every dimension:

```markdown
## Review guidance
- Do not report "<class>" in `<glob>`: answered wrong on #12, #18, #25.
```

When every finding in the path, of any class, was answered `wrong` or `did not matter`
on 3 or more PRs and the path is generated or vendored code, propose a `## Skip` bullet
for the glob instead. Never write these lines: print them, and say they go in
`REVIEW.md` at the repository root (or the existing `.github/REVIEW.md`) when the user
agrees. Fewer than 3 PRs: no proposal, only the counts.

## Report

Print the counts per class (all findings, then pre-existing apart), the rate of
`wrong` plus `did not matter` among answered findings, a table per class and dimension,
the findings answered `wrong` with their PR, file, and the reply's first line, and the
proposed `REVIEW.md` lines (or `No REVIEW.md lines proposed.`).
