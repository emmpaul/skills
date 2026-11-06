---
name: ep-a11y
description: Audit UI changes (uncommitted diff, branch, GitHub PR, or paths) for accessibility against WCAG 2.2 (Level AA by default, --level A|AA|AAA), citing each verified finding by exact success criterion from bundled W3C references, listing what needs a manual check, and never claiming conformance. Optionally fixes findings in the working tree (--fix) or posts one PR comment (--comment). Ends with an ep-a11y-summary block other skills can read. Use when the user asks for an accessibility, a11y, or WCAG audit or review of UI code.
---

# ep-a11y

Audit UI code for accessibility barriers, try to disprove every candidate, and report only
what survives, each cited to a WCAG success criterion from this skill's references.

## Hard rules

- **Read-only by default.** Without `--fix`, change no files yourself; the only exception
  is what a project a11y test the user confirmed in step 5 writes, which the report lists.
  Without `--comment`, post nothing to GitHub.
- **Never** commit, push, merge, or install a tool or dependency.
- **Cite only from the bundled index.** Every criterion number, name, and level comes
  from `references/wcag/index.md`; open the criterion's `references/wcag/sc/` file before
  citing it. Obsolete criteria are never cited.
- **No conformance claim.** The report says what was found in code and what a person
  still has to check; it never says the target conforms, complies, or passes.
- **No attribution** in anything posted (no "Generated with" footer, no model signature).

## Usage

```
ep-a11y                       # uncommitted diff; if the tree is clean, branch vs its base
ep-a11y <branch>              # <branch> vs its base
ep-a11y <pr-number>           # files changed in that PR
ep-a11y <path> [<path>...]    # whole files, not only changed lines
ep-a11y ... --level A|AA|AAA  # highest level checked (default AA = A and AA)
ep-a11y ... --fix             # apply fixes for verified findings; no commit
ep-a11y <pr-number> --comment # also post the report as one PR comment
```

A numeric argument is a PR; an argument that is an existing file or directory is a path;
anything else is a branch. `--comment` is only valid with a PR target: with any other
target, ignore it, say so in the report, and post nothing.

## References

All in this skill's folder (the directory containing this SKILL.md):

| File | What it holds | When to read |
|---|---|---|
| `references/wcag/index.md` | every WCAG criterion: number, name, level, versions, obsolete flag, file | step 3, always |
| `references/checks.md` | per-criterion code patterns, false positives, preferred fixes | step 3, always |
| `references/audit.md` | finding shape, severity scale, verification checklist, manual-check list, wording without conformance claims | step 3, always |
| `references/wcag/sc/<num>-<id>.md` | one criterion's normative text, exceptions, Understanding link, techniques, failures | only for criteria you are about to cite |
| `references/wcag/manifest.json` | WCAG version and source hash of the references | step 3, always |

These files are generated from W3C's published WCAG source; read them, never edit them.

## 1. Gather context

From the repository root, run the probe bundled in this skill's folder, passing the PR
number when the target is a PR:

```bash
bash <skill-dir>/scripts/context.sh [<pr-number>]
```

Use its `git` (branch, dirty state, default branch) and `pr` fields; ignore the rest.
Entries in `warnings` are informational. If bash is unavailable, or the probe exits
non-zero or prints invalid JSON, run the equivalents inline:

```bash
git status --porcelain=v1 -b
gh repo view --json defaultBranchRef --jq .defaultBranchRef.name
```

## 2. Resolve the target and filter to UI files

| Target | Files and diff |
|---|---|
| none, tree dirty | `git diff HEAD` plus untracked files (`git ls-files --others --exclude-standard`; read them in full) |
| none, tree clean | `git diff origin/<default>...HEAD` (after `git fetch origin <default>`); no remote: `git diff <default>...HEAD` |
| `<branch>` | `git diff origin/<default>...<branch>`; no remote: `git diff <default>...<branch>` |
| `<pr-number>` | `gh pr diff <n>`; also `gh pr view <n> --json number,headRefName,headRefOid,files` |
| `<path>...` | the whole content of each file (every file under a directory) |

For a PR whose head branch is not checked out, read files at the PR head without touching
the working tree: `git fetch origin pull/<n>/head` (or the head branch), then
`git show <headRefOid>:<path>`, `git ls-tree` and `git grep <headRefOid>`. Look for the
project's a11y tests (step 5) in the PR head too, and run them only when that head is
checked out. The same holds for a branch target: run the project's tests only when that
branch is checked out, since otherwise they would test other code.

Label the target by what was audited, in both the report heading and the summary:
`diff` for uncommitted changes, `branch:<name>` for a branch (including the clean-tree
default), `pr:<n>` for a PR, or `paths`.

Keep only UI files:

- markup and components: `html`, `htm`, `jsx`, `tsx`, `vue`, `svelte`, `astro`
- styles: `css`, `scss`, `sass`, `less`
- templates: `erb`, `hbs`, `handlebars`, `njk`, `jinja`, `jinja2`, `j2`, `twig`, `liquid`,
  `cshtml`, `razor`, `ejs`, `pug`
- `js`, `ts`, `mjs`, `cjs` files that render markup (JSX, `createElement`, template
  literals of HTML, DOM building with `innerHTML` or `appendChild`)

If no UI file remains, report `nothing to audit: no UI files in <the target as given>`,
end with the summary block (all counts 0; `wcag` and `references` from
`references/wcag/manifest.json`), and stop.

For diff targets, audit the changed lines and read enough around them to judge: the whole
component, the wrapper and design-system components it renders, and the stylesheets that
style it. Report only what the change adds or touches.

## 3. Load references and scope

1. Parse `--level`: `A` audits A; `AA` (default) audits A and AA; `AAA` audits all three.
2. Read `references/wcag/index.md` and keep the in-scope rows: level within the requested
   level and not obsolete. These rows are the only citations allowed.
3. Read `references/checks.md` and `references/audit.md`.
4. Read `references/wcag/manifest.json`: its `wcag_version` is the `<version>` used in the
   report and summary, and its `source_sha256` goes in the summary.

## 4. Audit by principle

Run four passes, one per WCAG principle: **1 Perceivable**, **2 Operable**,
**3 Understandable**, **4 Robust**. Each pass walks its in-scope index rows against the UI
files, using `checks.md` for criteria that have a section and the index row's name for
those that do not; it opens an `sc/` file only for a criterion it has a candidate for, or
whose scope it must confirm. Each pass returns candidates in the finding shape from `audit.md`.
Before a pass records a candidate, it opens the criterion's `sc/` file and checks the
normative text and exceptions support it.

**If you can spawn subagents** and the target has more than a few UI files: start four
subagents in parallel, one per principle. Give
each the repo path, the target's file list and diff (or how to get it), its principle's
in-scope index rows, the path of this skill's folder, and the instruction to read
`references/checks.md` and `references/audit.md` and open `references/wcag/sc/` files on
demand. Ask for candidates in the finding shape, and no fixes. Do not give them each
other's results.

**Otherwise** (no subagents, or a small target): run the four passes one after another yourself, in the
order above, with the same inputs. Finish one principle before starting the next. The
output shape is identical.

## 5. Run the project's own accessibility tests, if any

Look for an existing accessibility test command: a `package.json` script, Makefile
target, or task-runner entry whose name contains `a11y`, `axe`, or `pa11y`. If there is
none, the audit is code reading only.

A project script is code: running it runs whatever its author wrote. Before running one:

- **Skip it** when the target's diff touches anything the command could execute: the
  script entry or Makefile target, a file the command invokes, test or spec files the
  runner may pick up, test-runner, bundler, or setup config, or a dependency manifest or
  lockfile. When unsure whether a changed file runs, skip. Say in the report that it was
  skipped because the change under audit could run code through it.
- **Skip it** when it needs installation, a server you cannot start, or network access,
  and say why.
- Otherwise **ask the user** first, showing the exact command and noting it may write
  test artifacts (reports, screenshots). Run it only on a yes. When you cannot ask, skip
  it and say so.

After it runs, list in the report any files it created or changed (`git status
--porcelain` before and after); leave them for the user. Add each failure that maps to an
audited file as a candidate, citing the criterion from the index (the tool's rule usually
names it).

## 6. Verify each candidate

Apply the verification checklist in `audit.md` to every candidate, trying to disprove it:
look for a name supplied elsewhere, `aria-hidden` / `inert` / `hidden`, a wrapper or
design-system component that handles it, decorative use, a native element, or a
replacement style elsewhere in CSS. Open the component or stylesheet; do not assume.

- Drop candidates that do not survive.
- Move candidates that depend on rendering or runtime behaviour to the manual-check list.
- Correct a citation from the index, or drop the finding when no in-scope row fits.
- Deduplicate: one root cause is one finding, under the criterion that best describes it.

**With subagents:** one verifier per finding (or per batch of up to 5 when there are
many), told to argue the finding is wrong and to return `confirmed | refuted |
downgraded` with the reason. **Without subagents:** verify inline, one at a time.

## 7. Severity, ranking, and manual checks

Assign severity by impact using the scale in `audit.md` (critical, major, minor), never by
the criterion's level. Rank most severe first, then by principle and criterion number.

Build the manual-check list from `audit.md`: the in-scope criteria the code cannot
settle, filtered to what the audited files touch, plus candidates moved there in step 6.

## 8. `--fix` (optional)

Without `--fix`, skip this step.

- **PR target:** fix only when `HEAD` equals the PR's `headRefOid`, whatever the local
  branch is called (`gh pr checkout <n>` may name it `<owner>/<branch>`; a local `main` or
  a stale branch fails this). Otherwise edit nothing, and say: "fixes need PR #<n>'s head
  `<headRefOid>` checked out" (for example with `gh pr checkout <n>`).
- **Branch target:** fix only when the current branch is that branch. Otherwise edit
  nothing, and say: "fixes need branch `<name>` checked out".
- Fix only verified findings whose `decision` is `none`, only in the audited files, using
  the preferred fix from `checks.md`. Keep each edit minimal and in the file's style.
- Findings that need new visible text, a colour, or a design change: leave the code
  unchanged and list them under "Needs a decision".
- An `aria-label` naming an icon-only control after its obvious function ("Close") needs
  no decision. Replacing a `<div>` with a native `<button>` needs none either, but say in
  the report that browser button styles now apply.
- Create no commits. After editing, show `git diff --stat` and the diff of the edited
  files under "Fixed", and suggest committing them (for example with `ep-commit`).
  Keep line numbers from before the fix in the report. Fixed findings still count in the
  summary's `findings`.

## 9. Report

```
## Accessibility audit: <diff | branch:<name> | pr:<n> | paths> (WCAG <version> <level>)

### Findings
- [critical] src/Search.tsx:12 — 4.1.2 Name, Role, Value (A)
  Search input has no accessible name.
  Scenario: a screen reader user tabs to the field and hears "edit text"; they cannot tell what it is for.
  Evidence: `<input type="search" />` with no label, `aria-label`, `title`, or placeholder
  Fix: `<label htmlFor="q">Search</label><input id="q" type="search" />`
  Understanding: <link from the sc/ file>

### Needs a decision            (only with --fix, when any)
### Fixed                       (only with --fix, when any)
### Needs manual check
- 1.4.3 Contrast (Minimum) (AA): rendered text contrast in the new card, including hover state
### Project a11y tests
- none found; code reading only    (or: the command run and its failures, or why it was skipped)
```

Cite every criterion as `<num> <name> (<level>)`, copied from the index. Manual-check
lines take their name and level from the index; they need no `sc/` file. Show the
`decision` field only through the "Needs a decision" section. With no
findings, write "No issues found in the audited code at WCAG <version> <level>. The manual
checks below still need a person." and still list the manual checks. Never call the
target conformant or compliant.

End with this block, exactly in this form, so other skills can parse it:

```ep-a11y-summary
target: <diff | branch:<name> | pr:<n> | paths>
wcag: <version>
level: <A | AA | AAA>
references: <manifest wcag_version> sha256:<first 12 chars of manifest source_sha256>
findings: {critical: <n>, major: <n>, minor: <n>}
manual_checks: <n>
fixed: <true | false>
commented: <true | false>
```

`fixed` is true only when step 8 edited files. `commented` is true only when step 10
posted the comment.

With `--comment` on a PR target, run step 10 before printing. Then print the report with
one line above the summary block: `Posted: <comment URL>`, or `Not posted: <error>` with
`commented: false`. The summary block is always the last thing in the output.

## 10. `--comment` (PR targets only)

Post once the report is final. Write the full report, ending with the summary block with
`commented: true`, to a temporary file and post one comment:

```bash
gh pr comment <n> --body-file <file>
```

One comment per run. No attribution anywhere. Keep the URL that `gh` prints for the
`Posted:` line. If posting fails, do not retry; print the report as step 9 describes.
