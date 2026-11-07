# Fix mode

Step 8 of `SKILL.md`, read only with `--fix`. Edits go to the working tree; no commits.

## Where fixes may land

- **PR target:** fix only when `HEAD` equals the PR's `headRefOid`, whatever the local
  branch is called (`gh pr checkout <n>` may name it `<owner>/<branch>`; a local `main` or
  a stale branch fails this). Otherwise edit nothing, and say: "fixes need PR #<n>'s head
  `<headRefOid>` checked out" (for example with `gh pr checkout <n>`).
- **Branch target:** fix only when the current branch is that branch. Otherwise edit
  nothing, and say: "fixes need branch `<name>` checked out".

## What to fix

- Fix only verified findings whose `decision` is `none`, only in the audited files, using
  the preferred fix from `checks.md`. Keep each edit minimal and in the file's style.
- Findings that need new visible text, a colour, or a design change: leave the code
  unchanged and list them under "Needs a decision".
- An `aria-label` naming an icon-only control after its obvious function ("Close") needs
  no decision. Replacing a `<div>` with a native `<button>` needs none either, but say in
  the report that browser button styles now apply.

## After editing

Leave the edits uncommitted. Show `git diff --stat` and the diff of the edited files under
"Fixed", and suggest committing them (for example with `ep-commit`). Keep line numbers
from before the fix in the report. Fixed findings still count in the summary's
`findings`, and `fixed: true` only when files were edited.

Done when every finding with `decision: none` is fixed or the report says why fixes could
not land, and every other finding is under "Needs a decision".
