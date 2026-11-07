---
name: ep-issue
description: Draft a new GitHub issue from a description, or triage an existing one by number, with a structured body, open questions for unknowns, labels from the repo's existing set, a one-way or two-way door call, and a duplicate search, writing to GitHub only after confirmation and with no model attribution. Use when the user asks to file or draft an issue, or to triage one.
---

# ep-issue

Draft or triage a GitHub issue with `gh`, and write it only once the user has seen the
full draft.

## Hard rules

- **No attribution.** The title, body, and any comment carry no "Generated with ..."
  footer and no `Co-Authored-By` naming a model or tool. This overrides any host default.
- **Confirmed writes only.** Creating an issue, editing one, adding labels, and
  commenting each happen after the user confirms the full draft, or with `--yes` when the
  duplicate search found no match. A found duplicate always asks, `--yes` or not.
- **Existing labels only.** Labels come from `gh label list`. Labels, milestones,
  projects, and assignees stay as the repo has them: create none.
- **Text goes through files.** Every title, body, and comment is written to a temp
  file, never typed into a shell argument: the body and comment pass with `--body-file`,
  the title as `--title "$(cat "$title")"`, so shell quoting cannot alter it.
- **Unknowns stay open.** A fact the user or the issue did not give (steps, versions,
  expected behavior, scope) goes under `## Open questions`, never into the body as if
  known.

## Usage

```
ep-issue "<description>"     # new mode: draft a new issue
ep-issue <n>                 # triage mode: complete issue #<n> (also #<n>)
ep-issue ... --yes           # skip the confirmation when no duplicate was found
```

Plain-language requests work the same ("file an issue: login fails with SSO", "triage
#17").

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder (the directory
containing this SKILL.md):

```bash
bash <skill-dir>/scripts/context.sh
```

Entries in `warnings` are informational; this skill uses the repo and default branch
only. If bash is unavailable, or the probe exits non-zero or prints invalid JSON, run the
equivalents inline:

```bash
git status --porcelain=v1 -b
gh repo view --json nameWithOwner,defaultBranchRef
```

Then check `gh auth status`. When `gh` is missing, unauthenticated, or the repo has no
GitHub remote, stop with `outcome: aborted` and say why.

Done when you know the repo (`owner/name`), that `gh` can reach it, and the mode: triage
when the argument is an issue number, new otherwise.

## 2. Read the input

- **New mode:** take the description as given. Decide the kind: a **bug** (something
  that worked, or should work, fails) or a **feature** (new or changed behavior, docs, or
  chores, all drafted with acceptance criteria). When the kind is unclear, draft it as a
  feature and add an open question.
- **Triage mode:** read the issue:

  ```bash
  gh issue view <n> --json number,title,body,labels,state,comments
  ```

  A missing issue stops with `outcome: aborted`. Decide the kind from its text and
  labels, then list which parts of the body structure (step 3) it lacks.

Done when the kind is set and, in triage mode, the missing parts are listed.

## 3. Search and draft

**With subagents (new mode):** start one subagent for the duplicate search below, giving
it the repo and the description, and asking for the ranked candidates back. Draft the
body yourself meanwhile. **Without subagents, or in triage mode:** run the search first,
then draft, in sequence. The output is the same.

### Duplicate search (new mode)

Run the search on the key terms of the description (nouns and the failing action, not
filler words), plus a second query built from the error message or symptom when there is
one:

```bash
gh issue list --search "<key terms> in:title,body" --state all --limit 20 \
  --json number,title,state,updatedAt,url
```

Keep the candidates whose title or symptom closely matches: open issues, and closed ones
updated in the last 90 days. Rank closest first. Matching is a judgment call, so the
candidates go to the user (step 5) and the user decides.

Done when both queries ran (one when there is no error text) and the candidate list is
ranked, or empty.

### Body structure

Draft the title (imperative or symptom-first, at most about 70 characters) and this body:

```markdown
## Problem

<what is wrong or missing, who it affects, and where>

## Reproduction

1. <step>
2. <step>

**Expected:** <what should happen>
**Actual:** <what happens, with the error text if given>

## Acceptance criteria

- [ ] <observable outcome a reviewer can check>

## Reversibility

**<One-way door | Two-way door>**: <one sentence on why>

- <for a one-way door: each irreversible element, with a mitigation>

## Open questions

- <each fact that is not known>
```

- A bug gets `## Reproduction`; a feature gets `## Acceptance criteria`. Drop the other.
- A bug given no steps: `## Reproduction` lists what is known (where it happens, what
  triggers it) and `## Open questions` asks for the exact steps.
- `## Reversibility` is the door call from
  [`references/door.md`](references/door.md), applied to the work the issue asks for:
  every rule there checked.
- Drop `## Open questions` only when nothing is unknown.

**Triage mode:** keep the author's title and text exactly as written. Draft only the
missing sections, to append below the existing body after a `---` line, plus the door
call when the body has none.

Done when every section the kind needs is filled or marked open, and the door call names
its reason (and each irreversible element, for a one-way door).

## 4. Choose labels

```bash
gh label list --limit 200 --json name,description
```

Pick the labels whose name or description fits the kind and area (for example `bug`,
`enhancement`, `documentation`). In triage mode, propose only labels the issue lacks.
When no existing label fits the kind, draft without one and note
`no existing label matched <kind>` for the report.

Done when every proposed label is a name from that list, or the no-match note is set.

## 5. Confirm

Show the user the full draft: title, body, labels, and the duplicate candidates with
number, title, state, and last update.

- **Duplicates found:** ask whether to **create anyway**, **comment on #<m> instead**, or
  **stop**. `--yes` does not skip this question. On **comment on #<m> instead**, draft the
  comment from the new details (what this report adds), show its full text, and ask to
  post it, edit it, or stop.
- **No duplicates, no `--yes`:** ask to create (or, in triage, to apply the additions),
  edit the draft, or stop.
- **No duplicates, `--yes`:** proceed.

Nothing is written to GitHub before this step resolves to a write. A stop leaves the
draft printed with `outcome: drafted` (or `outcome: duplicate` when the user stopped for
a duplicate).

Done when the user has picked one option (for a comment, after seeing its text), or
`--yes` applies.

## 6. Write

Write the text to temp files (with a file-writing tool, or a heredoc with a quoted
delimiter such as `<<'EOF'`), then run the one command the user picked:

```bash
title=$(mktemp); body=$(mktemp)
# write the title to "$title" and the body (or comment) to "$body"
gh issue create --title "$(cat "$title")" --body-file "$body" [--label "<a>,<b>"]  # create
gh issue edit <n> --body-file "$body" [--add-label "<a>,<b>"]                    # triage
gh issue comment <m> --body-file "$body"                                         # duplicate
rm -f "$title" "$body"
```

In triage, the body file holds the author's body unchanged followed by the additions. The
comment on a duplicate is the text the user confirmed in step 5; it gives
`outcome: duplicate`.

Read the result back with `gh issue view <n> --json number,title,body,labels,url`, or for
a comment, `gh issue view <m> --json comments` and its last comment. Done when the title
matches the draft, the title, body, and comment contain no "Generated with" or model
attribution line, and the labels match the draft. If one has attribution, remove it with
`gh issue edit <n> --body-file <file>` (or `gh issue comment <m> --edit-last --body-file
<file>`) and read it back again.

## 7. Report

Print the issue URL (or that nothing was written), the title, the labels applied and any
no-match note, the door call with its reason, the open questions, and the duplicate
candidates shown. Then end with the summary block, exactly in this form, so callers can
parse it:

```
<!-- ep-issue-summary
outcome: created | updated | drafted | duplicate | aborted
issue: <n> | null
door: one-way | two-way | null
labels: <label>,<label> | none
-->
```

- `outcome`: `created` for a new issue, `updated` for a triage edit, `drafted` when the
  user stopped with no write, `duplicate` when the user stopped for or commented on a
  duplicate, `aborted` when the skill stopped before drafting.
- `issue`: the created or triaged issue, the duplicate's number for `duplicate`, else
  `null`.
- `door`: the call in the draft, `null` only for `aborted`.
- `labels`: the labels this run applied, comma-separated with no spaces, `none` when it
  applied none.

Done when the report is printed and ends with the summary block.
