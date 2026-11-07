# Project accessibility tests

Step 5 of `SKILL.md`, read when the project defines an accessibility test command (a
`package.json` script, Makefile target, or task-runner entry whose name contains `a11y`,
`axe`, or `pa11y`). Run it only on the checked-out code the audit targets (step 2 of
`SKILL.md`).

A project script is code: running it runs whatever its author wrote. Decide in this
order:

1. **Skip it** when the target's diff touches anything the command could execute: the
   script entry or Makefile target, a file the command invokes, test or spec files the
   runner may pick up, test-runner, bundler, or setup config, or a dependency manifest or
   lockfile. When unsure whether a changed file runs, skip. Say in the report that it was
   skipped because the change under audit could run code through it.
2. **Skip it** when it needs installation, a server you cannot start, or network access,
   and say why.
3. Otherwise **ask the user** first, showing the exact command and noting it may write
   test artifacts (reports, screenshots). Run it only on a yes. When you cannot ask, skip
   it and say so.

When it runs, take `git status --porcelain` before and after, and list in the report any
files it created or changed; leave them for the user. Add each failure that maps to an
audited file as a candidate, citing the criterion from the index (the tool's rule usually
names it). These candidates go through verification (step 6) like any other.

Done when the command ran and its failures are candidates, or the report's
`### Project a11y tests` section states why it was skipped.
