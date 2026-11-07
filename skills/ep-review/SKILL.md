---
name: ep-review
description: Review a local diff, a branch, or a GitHub PR across four dimensions (correctness, OpenSpec spec conformance, tests, security), verify every finding before reporting it, and print a ranked report or post it to the PR with --comment. Produces a summary block other skills (ep-babysit-pr) can read. Use when the user asks to review changes, a branch, or a PR.
---

# ep-review

Review a change, try to disprove every candidate finding, and report only what survives.

## Hard rules

- **Read-only by default.** Without `--comment`, post nothing to GitHub and change no files.
- **No attribution** in anything posted (no "Generated with" footer, no model signature).
- Report only verified findings. Every reported finding has a location, severity, and a
  concrete failure scenario.

## Usage

```
ep-review                 # uncommitted diff; if the tree is clean, branch vs its base
ep-review <branch>        # <branch> vs its base
ep-review <pr-number>     # diff of that PR
ep-review <pr-number> --comment   # also post findings to the PR
ep-review ... --since <sha>       # review only the changes from <sha> to the target head
ep-review ... --known <file>      # findings already reported: re-check, never repeat
ep-review ... --effort high       # thorough mode (see Workflow path)
```

`--comment` is only valid with a PR target. With any other target, ignore it and say so.

`--since <sha>` and `--known <file>` work with every target and with each other. Callers
(`ep-babysit-pr`, `ep-orchestrate`) pass both for review rounds after the first. The
`--known` file holds one finding per line, in the form callers already write:

```
finding: <id> <dimension> <severity> <file>:<line> | <summary> | <scenario>
```

The leading `finding: ` and the trailing `| <scenario>` are optional. Lines that do not
fit are ignored, and the report says how many.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md), passing the PR number when the target is a PR:

```bash
bash <skill-dir>/scripts/context.sh [<pr-number>]
```

Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
openspec list --json        # optional; root null = no OpenSpec
```

### `REVIEW.md`

Look for `REVIEW.md` at the repository root, then `.github/REVIEW.md`, and use the first
one found. Free Markdown, plus these recognised headings, each a bullet list:

| Heading | Bullets | Effect |
|---|---|---|
| `## Skip` | globs (`**` spans directories) | changed paths matching one are not reviewed |
| `## Risk` | `high: <glob>`, `medium: <glob>`, `low: <glob>` | risk paths, read by [`references/risk.md`](references/risk.md) |
| `## Trusted authors` | GitHub logins, without `@` | trusted authors, read by `references/risk.md` |
| `## Limits` | `max_minor: <n>` | at most `<n>` minor findings are reported (step 6) |

Everything else in the file (other headings, prose, and bullets that do not fit these
forms) is **repository guidance**: pass it verbatim to every dimension in step 4, and
follow it as you would a reviewer's standing instructions. Unknown headings are guidance,
not errors.

With no `REVIEW.md`, use the defaults (nothing skipped, no minor cap, built-in risk rules)
and do not mention the file anywhere in the report.

## 2. Resolve the target and get the diff

| Target | Diff command |
|---|---|
| none, tree dirty | `git diff HEAD` plus untracked files (`git ls-files --others --exclude-standard`; read them in full) |
| none, tree clean | `git diff origin/<default>...HEAD` (after `git fetch origin <default>`); no remote: `git diff <default>...HEAD` |
| `<branch>` | `git diff origin/<default>...<branch>`; no remote: `git diff <default>...<branch>` |
| `<pr-number>` | `gh pr diff <n>`; also `gh pr view <n> --json title,body,author,baseRefName,headRefName,headRefOid,files,commits` |

**With `--since <sha>`**, the diff is `git diff <sha>..<head>` instead, where `<head>` is
the target's head: `HEAD` for a branch or a clean tree (plus the working tree for an
uncommitted diff, `git diff <sha>`), and for a PR `headRefOid` after
`git fetch origin pull/<n>/head`. If `<sha>` is not an ancestor of the head
(`git merge-base --is-ancestor <sha> <head>` fails, for example after a force-push), say
so and review the full diff instead, with `scope: full`. Still read the code around the
narrowed diff as usual; only the hunks under review shrink. The base for origin and
blame (`references/dimensions.md`) stays the target's base, not `<sha>`. Record the scope
for the summary: `since:<sha>` with `--since`, `full` without it.

**Skipped paths.** Remove from the diff every changed path that matches a `## Skip` glob in
`REVIEW.md`. Review nothing in those files and report no finding there. List them in the
report (step 6) as skipped by `REVIEW.md`. They still count as changed paths for the risk tier.

If the diff is empty, report "nothing to review" and stop. When `--known` was given,
re-check the known findings first (step 5) so the summary still records them.

**Intent.** Read the change's stated intent: for a PR, its title, body, and commit
messages; for a branch, `git log --format=%s%n%b <base>..<head>`; for an uncommitted diff,
any commits ahead of the base plus what the user said. Pass it to every dimension. When
the intent is a bug fix (a `fix` type, "fix" or "bug" in the title, or a linked issue),
the correctness dimension checks that the fix reaches the root cause.

Read enough surrounding code (whole changed functions, callers of changed signatures) to
judge behavior, not just the hunks.

## 3. Find the OpenSpec change (spec conformance input)

- `openspec` is null: spec conformance is **not applicable**. Run the other three
  dimensions normally and do not mention OpenSpec beyond that line.
- Otherwise pick the active change the target relates to: its folder is in the diff, the
  commits use it as scope, or the PR body names it. If several fit, review against each
  one that fits; if none fits, spec conformance is not applicable.
- Read the change's `proposal.md`, `tasks.md`, and every `specs/**/spec.md`.
- With `--since`, conformance still uses the whole change's specs and searches the whole
  codebase for implementations; `--since` only narrows which requirements to re-check
  (those the narrowed diff touches, plus those named by known spec findings).

## 4. Review the four dimensions

The checklists, finding shape, and severity scale are in
[`references/dimensions.md`](references/dimensions.md). Read it before reviewing.

Dimensions: **correctness**, **spec** (conformance), **tests**, **security**.

**If you can spawn subagents:** start one subagent per dimension in parallel. Give each the
diff (or how to get it), the repo path, the relevant checklist section from
`references/dimensions.md`, the stated intent, the `REVIEW.md` guidance (when there is
one), the OpenSpec change files for the spec dimension, and ask for candidate findings in
the finding shape. Do not give them each other's results.

**If you cannot spawn subagents:** review the dimensions one after another yourself, in the
order above, with the same checklists. Finish one dimension before starting the next.

Either way, collect all candidate findings, then deduplicate **within** each dimension
(same root cause: keep one, at the higher severity). Do not merge findings across
dimensions: a bug that also contradicts a spec scenario is reported once under
correctness and once under spec, so the spec status stays accurate. To avoid double
reports on tests: an untested **spec scenario** belongs to the spec dimension only; the
tests dimension covers test gaps for code-level behavior and weak or missing assertions.

## 5. Verify each finding

For every candidate, try to **disprove** it:

- Re-read the code at the location and the paths that reach it.
- Check whether the input or state in the scenario can actually occur (validation upstream,
  types, call sites, config).
- Check whether existing code or tests already handle it.
- For spec findings, re-read the requirement text and search the codebase (not only the
  diff) for an implementation.
- When cheap and safe, run the test or command that would show the failure.

Running tests must not modify tracked files; if the runner is not installed, skip running
and rely on reading. Drop findings that cannot occur. Downgrade severity when impact is smaller than claimed.
Keep the rest as **verified**.

**With subagents:** use one verifier subagent per finding (or per batch of up to 5 findings
when there are many), told to argue the finding is wrong and to return
`confirmed | refuted | downgraded` with the reason. **Without subagents:** verify each
finding inline, one at a time, using the same steps.

### Workflow path (Claude Code, high effort)

When running in Claude Code with a Workflow tool available and the user asked for high
effort (`--effort high`, "thorough", "deep review"), running this skill at that effort is
the user's opt-in to a Workflow. Run steps 4-5 as one Workflow: a `pipeline` over the four
dimensions where each dimension's findings go straight to per-finding verify agents, then
collect confirmed findings. Keep it under 10 agents (batch verifications when needed).
If no Workflow tool exists, use the subagent path above.

## 6. Report

Rank verified findings most severe first (critical, major, minor), then by dimension.

```
## Review: <uncommitted diff | branch:<name> | PR #<n>>

### correctness
- [major] src/calc.py:3 — div returns None when b is negative
  Scenario: div(4, -2) -> None instead of -2.0, caller prints "None".
### spec
- [critical] Requirement "Draft and base options" not implemented
  Scenario: `ep-open-pr --draft` creates a non-draft PR; no --draft handling in the diff.
### tests
No findings.
### security
No findings.
```

Every dimension appears, with findings, **"No findings."**, or (spec only)
**"Not applicable: no OpenSpec change."**

Then always end with the summary block, exactly in this form, so callers can parse it:

```
<!-- ep-review-summary
target: <diff | branch:<name> | pr:<n>>
head: <commit sha reviewed>
verified: critical=<n> major=<n> minor=<n>
by_dimension: correctness=<n> spec=<n> tests=<n> security=<n>
spec_conformance: passed | failed | not_applicable
dropped_in_verification: <n>
-->
```

`head` is the sha of `HEAD` (or the PR head) the review ran on; for an uncommitted diff it
is `HEAD`. `dropped_in_verification` counts only findings refuted in step 5, not those
merged during deduplication.

`spec_conformance` is `passed` when the spec dimension has no verified critical or major
finding, `failed` otherwise, and `not_applicable` without an OpenSpec change.

## 7. `--comment` mode (PR targets only)

Post only after the report is final. Use one PR review with inline comments for findings
that map to a line in the diff, and put the rest (plus the summary block) in the review body:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input <payload.json>
```

with `payload.json`:

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "<report header, non-inline findings, summary block>",
  "comments": [
    { "path": "src/calc.py", "line": 3, "side": "RIGHT",
      "body": "**[major] correctness** — <summary>\n\nScenario: <scenario>" }
  ]
}
```

Always use `"event": "COMMENT"`, never `APPROVE` or `REQUEST_CHANGES`. If the inline
review is rejected (for example a line is outside the diff), move that finding into the
body and retry. With no findings, post a single review body saying so, with the summary
block. No attribution anywhere. Report the review URL.
