# Work naming rules

Shared by `ep-start` and `ep-issue-to-change`, so one issue gives one type, one slug, and
one change name in both, and each skill finds the change the other made. Each skill ships
a copy as `references/naming.md`; the source is `shared/naming.md`: edit the source and
run `scripts/sync-shared.sh`.

Every rule here is mechanical: two runs on the same title and labels give the same names.
The title is the issue title, or the description for a run without an issue.

## Type

First match wins:

1. **Labels**, checked in this order: `bug` → `fix`; `enhancement` or `feature` →
   `feat`; `documentation` → `docs`.
2. **Title words**: take the title's words as the slug rule splits them (before stop
   words are dropped) and scan them left to right. The first word in one of these lists
   gives its type:
   - `fix`: fix, fixes, fail, fails, failed, failing, crash, crashes, crashed, broken,
     error, errors, wrong
   - `docs`: document, documents, documentation, docs, readme
   - `refactor`: refactor, rename, extract, simplify
   - `test`: test, tests
   - `feat`: add, adds, support, implement, allow
3. Otherwise `feat`.

Words outside the lists never set the type: "Login hangs with SSO" with no label is
`feat`.

## Slug

From the title:

1. Drop a leading bracketed tag (`[...]`) and code marks (backticks).
2. Lowercase it, and transliterate or drop non-ASCII.
3. Split it into words at every run of characters outside `[a-z0-9]`, and drop empty
   words.
4. Drop stop words: a, an, the, to, of, for, in, on, is, are, be, please, should.
5. Join the rest with single `-`, keeping whole words from the start while the slug is at
   most 40 characters. A first word longer than 40 characters is cut to 40.

The slug starts and ends with a letter or digit and has no `--`: leading or trailing
punctuation gives an empty word, and empty words are dropped. Examples:

- "Login fails with SSO" → `login-fails-with-sso`
- "Crash on save (Windows)" → `crash-save-windows`
- "(Windows) crash on save." → `windows-crash-save`

## Change name

The verb comes from the type: `fix` → `fix`, `feat` → `add`, `docs` → `document`,
`refactor` → `refactor`, `test` → `test`. The name is `<verb>-<slug>`, or the slug alone
when its first word is already the verb, keeping whole slug words while the name is at
most 40 characters. An empty slug gives `<verb>-<n>` with an issue; without one, ask the
user for a name.

- #17 "Login fails with SSO", label `bug` → `fix-login-fails-with-sso`
- "add CSV export" → `add-csv-export`
- #30 "Login hangs with SSO", no label → `add-login-hangs-with-sso`

A name the user supplies instead is accepted only when it matches
`^[a-z0-9][a-z0-9-]*$`.

## An issue's existing change

Each change made for an issue carries the marker `From #<n>:` (for an issue in another
repository, `From <owner>/<repo>#<n>:`): `ep-issue-to-change` writes it as the start of
the proposal's Why line, and `ep-start` passes it to `openspec new change` as
`--description "From #<n>: started by ep-start."`, which the CLI writes to the change's
`README.md`. A change for issue `<n>` exists when its derived name is in the probe's
`changes` (or `openspec list --json`), or when this lists a file; each listed file's
directory name is an existing change:

```bash
grep -rlF --include=proposal.md --include=README.md --exclude-dir=archive \
  "From #<n>:" "<root>/openspec/changes"
```

`<n>` is digits only, so the marker is safe inside double quotes.
