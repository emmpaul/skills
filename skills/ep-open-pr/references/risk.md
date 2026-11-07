# Risk tier rules

Shared by `ep-review`, `ep-open-pr`, and `ep-babysit-pr`, so all three give the same tier
for the same change. The source is `shared/risk.md`; each skill ships a copy as
`references/risk.md`. Edit the source and run `scripts/sync-shared.sh`.

Every change gets one tier: `low`, `medium`, or `high`, with a list of reasons. Decide it
from the changed paths (`git diff --name-only <base>...<head>`, or `gh pr diff <n>
--name-only`), the PR author, and the repository's `REVIEW.md`. For a rename, check both
the old and the new path.

## Order

Evaluate the rules in this order and stop at the first that applies.

1. **high** when any rule in [High](#high) matches.
2. **low** when every condition in [Low](#low) holds.
3. **medium** otherwise.

Then apply [Raising the tier](#raising-the-tier).

## High

The tier is `high` when any changed path matches one of these built-in globs:

| What | Globs |
|---|---|
| CI | `.github/workflows/**`, `.github/actions/**` |
| Ownership | `CODEOWNERS` at any depth |
| Installers, updaters, releases | `**/install*`, `**/*updater*`, `**/release*` |
| Auth | `**/auth/**`, `**/*auth*` |
| Billing | `**/billing/**`, `**/payment*` |
| Database migrations | `**/migrations/**` |
| Secret config | `.env*` at any depth, `**/secrets*` |

It is also `high` when:

- a changed path matches a `high:` glob in the `REVIEW.md` `## Risk` section; or
- the PR body's Reversibility section (written by `ep-open-pr`; for `ep-open-pr`, its own
  classification) says the change is a one-way door.

Give one reason per match, naming the path and the rule, for example
`.github/workflows/ci.yml matches .github/workflows/** (CI)`, or
`one-way door per PR body`.

## Low

The tier is `low` only when both conditions hold:

1. **Paths:** every changed path is documentation-only (below) or matches a `low:` glob in
   the `REVIEW.md` `## Risk` section, and no changed path matches a `medium:` glob there.
2. **Author:** the author is trusted (below).

When condition 1 holds but condition 2 does not, the tier is `medium` with the reason
`author not trusted`.

### Documentation-only paths

A path is documentation-only when:

- it matches one of: `*.md`, `*.mdx`, `*.rst`, `*.txt`, `docs/**`, `openspec/**`,
  `LICENSE*`, `CHANGELOG*`; and
- it is **not** an agent instruction file: `AGENTS.md` or `CLAUDE.md` at any depth,
  anything under `.claude/` or `.agents/`, or any file in or below a directory that
  contains a `SKILL.md` (the whole skill folder, including `references/` and `scripts/`).

`ep-babysit-pr` uses this same rule for its documentation-only test-evidence item.

### Trusted authors

The author is trusted when it is:

- the authenticated `gh` user (`gh api user --jq .login`); or
- a login listed under `## Trusted authors` in `REVIEW.md`.

For a PR, the author is the PR's author (`gh pr view <n> --json author --jq .author.login`).
For a local diff or branch with no PR, the author is the user running the skill, who is
trusted.

Reasons for a low tier: `documentation only`, or `all paths match REVIEW.md low globs`,
or both, plus the author rule that matched, for example `author is the authenticated user`.

## Medium

Everything that is neither high nor low is `medium`. Reasons:

- a changed path matches a `medium:` glob in `REVIEW.md`: name the path and the glob;
- the path rules give low but the author is not trusted: `author not trusted`;
- otherwise: `ordinary change`.

## Raising the tier

A skill may raise the tier with a stated reason when the change needs a person anyway
(for example it changes behavior other teams rely on, or its effect cannot be checked from
the diff). It adds that reason to the list.

Nothing ever lowers the tier below the result of the rules above: not the reviewer, not a
`low:` or `medium:` glob in `REVIEW.md` (a built-in high match stays high), and not a
trusted author.

## Missing tier

A reader of an `ep-review-summary` block with no `risk:` line (an older `ep-review`)
treats the change as `medium`.

## `REVIEW.md` syntax

Look for `REVIEW.md` at the repository root, then `.github/REVIEW.md`; use the first one
found. The sections the risk rules read are bullet lists:

```markdown
## Risk

- high: infra/**
- medium: src/core/**
- low: examples/**

## Trusted authors

- octocat
- jane-doe
```

- `## Risk`: each bullet is `<tier>: <glob>`, with tier `high`, `medium`, or `low`. Globs
  match repository-relative paths; `**` spans directories.
- `## Trusted authors`: each bullet is one GitHub login, without `@`.

Bullets that do not fit these forms, and all other headings, are guidance, not errors.
With no `REVIEW.md`, only the built-in rules and the authenticated user apply.
