---
name: ep-review
description: Review a local diff, a branch, or a GitHub PR across four dimensions (correctness, OpenSpec spec conformance, tests, security), confirm every finding by a 3-verifier vote (one inline check without subagents), tag bugs the change did not introduce as pre-existing without counting them, follow the repo's REVIEW.md, re-review only new commits with --since and --known so known findings are re-checked, not repeated, and classify the change's risk tier (low, medium, high). Prints a ranked report starting with what to fix, or posts it to the PR with --comment. Produces a summary block other skills (ep-babysit-pr, ep-orchestrate) can read. Use when the user asks to review changes, a branch, or a PR.
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

The leading `finding: ` and the trailing `| <scenario>` are optional. After the scenario,
a line may add `| class: <label>` and `| instances: <file>:<line>,<file>:<line>` (the
finding's class and other locations, as the report prints them). Lines that do not fit
are ignored, and the report says how many.

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
  dimensions normally and do not mention OpenSpec anywhere in the report or comments.
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
(same root cause: keep one, at the higher severity, with the others' locations added to
its `instances`). Do not merge findings across dimensions: a bug that also contradicts a
spec scenario is reported once under correctness and once under spec, so the spec status
stays accurate. To avoid double reports on tests: an untested **spec scenario** belongs to
the spec dimension only; the tests dimension covers test gaps for code-level behavior and
weak or missing assertions.

**Known findings (`--known`).** Each **location** of a known finding (its `file:line` and
each of its `instances`) becomes a verification candidate too, marked `known`, whatever
the narrowed diff covers. Then drop every new candidate that duplicates a known one: same
file, within 3 lines of one of its locations (follow moved code, not only line numbers),
and the same defect (same class; when the known line names no class, judge it from the
summary). The known finding is the one that goes to verification, so it is never reported
as new.

## 5. Verify each finding

For every candidate, try to **disprove** it:

- Re-read the code at the location and the paths that reach it.
- Check whether the input or state in the scenario can actually occur (validation upstream,
  types, call sites, config).
- Check whether existing code or tests already handle it.
- For spec findings, re-read the requirement text and search the codebase (not only the
  diff) for an implementation.
- When cheap and safe, run the test or command that would show the failure.
- Decide the origin (`introduced` or `pre-existing`) with the blame rule in
  `references/dimensions.md`, and check each listed instance; drop instances that do
  not have the defect.
- For a `known` candidate (one location), check it at the new head: it is `fixed` when
  the defect no longer occurs there (moved lines count: follow the code, not the line
  number), and `still open` otherwise.

Running tests must not modify tracked files; if the runner is not installed, skip running
and rely on reading. Each check ends in one verdict per candidate, with a reason:
`confirmed`, `refuted` (it cannot occur, or a known finding is fixed), or
`downgraded:<severity>` (real, but smaller than claimed).

### Voting (with subagents)

Start **3 voter subagents in parallel**, after every dimension has finished. Each voter
gets every candidate (new and known), the diff or how to get it, the repo path, and
`references/dimensions.md`, plus the same brief: argue that each finding is wrong, run the
checks above, and return one verdict per candidate with its reason. No voter sees another
voter's verdicts. With more than 20 candidates, each voter takes them in batches of 20,
one batch after another in its own context; that adds no agents. This is 7 agents in all
(4 dimensions and 3 voters), for any number of findings.

Combine the 3 verdicts of each candidate:

- **Kept** when at least 2 verdicts are not `refuted`. A split vote, where only 1 of 3
  confirms and 2 refute, drops the finding, and it counts toward
  `dropped_in_verification`.
- **Severity** is the highest severity that at least 2 non-refuting verdicts support. A
  `confirmed` verdict supports the claimed severity and every severity below it;
  `downgraded:<x>` supports `<x>` and below. For example, a major candidate with the
  verdicts confirmed, downgraded:minor, downgraded:minor is reported as **minor**.
- **Origin** and **instances** follow the majority of the kept verdicts; on a tie, the
  origin is `introduced`.
- A **known** candidate that is dropped is counted as `fixed`, not in
  `dropped_in_verification`. One that is kept is `still open`. The still-open locations
  of one known finding are reported together as **one** finding, marked `still open`, at
  its first remaining location with the others as `instances`, and it counts once in
  `verified:` like any introduced finding (or in `pre_existing` when its origin is
  pre-existing).

The summary records `verification: vote`.

### Inline verification (without subagents)

Verify each candidate **once**, inline, one at a time, with the same disproof steps. Drop
it when the verdict is `refuted`; apply a `downgraded` severity as given. Known candidates
are `fixed` or `still open` as above. A single context cannot vote independently, so do
not pretend to: the summary records `verification: inline`.

Whatever the path, the findings that are kept are the **verified** findings.

### Workflow path (Claude Code, high effort)

When running in Claude Code with a Workflow tool available and the user asked for high
effort (`--effort high`, "thorough", "deep review"), running this skill at that effort is
the user's opt-in to a Workflow. Run steps 4-5 as one Workflow: a `pipeline` over the four
dimension agents, whose deduplicated candidates (plus any known findings) go to a
`parallel` stage of the 3 voter agents described above, then combine the verdicts with the
voting rules. That is **at most 7 agents** (4 dimensions and 3 voters); voters batch by 20
instead of adding agents. The summary records `verification: vote`. If no Workflow tool
exists, use the subagent path above.

## 6. Report

### Risk tier

Classify the change as `low`, `medium`, or `high` with the rules in
[`references/risk.md`](references/risk.md), and list the reasons it gives. Use the paths
the **whole** target changes (its base to its head, as in the table in step 2), even with
`--since`, and including paths skipped by `REVIEW.md`: a narrowed re-review never lowers the
tier. The author is the PR's author for a PR target, and the user running the review
otherwise. You may raise the tier with a stated reason when the change needs a person
anyway (as `references/risk.md` describes); never lower it below the rules' result.

### Findings

Rank verified introduced findings most severe first (critical, major, minor), then by
dimension. Pre-existing findings go in their own `### pre-existing` section after the four
dimensions, ranked the same way.

**Minor cap.** When `REVIEW.md` sets `max_minor: <n>` and more than `<n>` minor findings are
verified (introduced and pre-existing together), report the `<n>` most important
(introduced before pre-existing, then by impact) and state under the count line how many
were omitted by the cap. The summary counts only the reported findings.

The first line under the header is the **count line**: the findings to fix by severity and
the number of pre-existing findings, for example
`To fix: 0 critical, 1 major, 0 minor. Pre-existing: 1.` When there are no introduced
findings, it is the plain line **"Nothing to fix."**, followed by
`Pre-existing: <n>.` only when `<n>` is not zero. Below it, when they apply, one line
each: the paths skipped by `REVIEW.md`, the minor findings omitted by the cap, the known
locations (`Known findings: <n> fixed, <n> still open.`), and the `--known` lines that
could not be read.

```
## Review: <uncommitted diff | branch:<name> | PR #<n>>

To fix: 1 critical, 1 major, 0 minor. Pre-existing: 1.
Skipped by REVIEW.md: gen/client.ts
Known findings: 1 fixed, 0 still open.

### correctness
- [major] src/calc.py:3 — div returns None when b is negative
  Class: missing branch for negative input. Instances: src/calc.py:11
  Scenario: div(4, -2) -> None instead of -2.0, caller prints "None".
### spec
- [critical] Requirement "Draft and base options" not implemented
  Scenario: `ep-open-pr --draft` creates a non-draft PR; no --draft handling in the diff.
### tests
No findings.
### security
No findings.
### pre-existing
- [major] correctness src/calc.py:20 — mod divides by zero when b is 0
  Class: unchecked zero divisor. Instances: none
  Scenario: mod(1, 0) raises ZeroDivisionError; lines predate this change (git blame).

Risk: high
- .github/workflows/ci.yml matches .github/workflows/** (CI)
```

Every dimension appears, with findings, **"No findings."**, or (spec only)
**"Not applicable."** (with an OpenSpec root but no change that fits:
**"Not applicable: no matching OpenSpec change."**). The `### pre-existing` section appears only when
there are pre-existing findings. A known finding that is still open is marked
`(still open)` after its severity, for example `- [major] (still open) src/calc.py:3 — ...`.
Every finding shows its class and instances (`Instances: none` when there are none).

Then always end with the summary block, exactly in this form, so callers can parse it:

```
<!-- ep-review-summary
target: <diff | branch:<name> | pr:<n>>
head: <commit sha reviewed>
verified: critical=<n> major=<n> minor=<n>
by_dimension: correctness=<n> spec=<n> tests=<n> security=<n>
spec_conformance: passed | failed | not_applicable
dropped_in_verification: <n>
pre_existing: <n>
known: fixed=<n> still_open=<n>
risk: low | medium | high
risk_reasons: <reason> ; <reason>
verification: vote | inline
scope: full | since:<sha>
-->
```

`head` is the sha of `HEAD` (or the PR head) the review ran on; for an uncommitted diff it
is `HEAD`. `verified` and `by_dimension` count only **introduced** findings, including known
findings that are still open; pre-existing findings are counted only in `pre_existing`.
`dropped_in_verification` counts only new candidates refuted in step 5, not those merged
during deduplication and not known findings found fixed. `known` counts known locations (a
known finding's line and each instance), so fixing one of two instances gives `fixed=1`
and `still_open=1`; it is `fixed=0 still_open=0` without `--known`. `risk_reasons` separates reasons with ` ; `. `verification` is `vote` on
the subagent and Workflow paths and `inline` otherwise. `scope` is `since:<sha>` with
`--since` and `full` without it (or when step 2 fell back to a full review).

`spec_conformance` is `passed` when the spec dimension has no verified introduced critical
or major finding, `failed` otherwise, and `not_applicable` without an OpenSpec change.

## 7. `--comment` mode (PR targets only)

Post only after the report is final.

**Skip what is already posted.** List the PR's earlier `ep-review` reviews and their
comments:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --paginate      # keep reviews whose body contains <!-- ep-review-summary
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate     # keep comments whose pull_request_review_id is one of them
```

Leave out of the new review every finding whose file and summary match an inline comment
from one of those reviews (or a finding line in one of their bodies). The new review body
states `<n> already posted` when `<n>` is not zero. The report printed in the session and
the summary block keep every finding.

Use one PR review with inline comments for findings that map to a line in the diff, and
put the rest (plus the summary block) in the review body:

```bash
gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input <payload.json>
```

with `payload.json`:

```json
{
  "commit_id": "<headRefOid>",
  "event": "COMMENT",
  "body": "<report header, count line, non-inline findings, summary block>",
  "comments": [
    { "path": "src/calc.py", "line": 3, "side": "RIGHT",
      "body": "**[major] correctness** — <summary>\n\nScenario: <scenario>\nInstances: <file:line, ...>" }
  ]
}
```

Tag every pre-existing finding `pre-existing` in its comment, for example
`**[major] correctness · pre-existing** — <summary>`, and add one line saying it predates
this PR, so it does not read as the author's fault.

Always use `"event": "COMMENT"`, never `APPROVE` or `REQUEST_CHANGES`. If the inline
review is rejected (for example a line is outside the diff), move that finding into the
body and retry. With no findings left to post, post a single review body saying so, with
the summary block. No attribution anywhere. Report the review URL.
