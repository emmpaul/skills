# skills

Personal agent skills for git and GitHub workflows. Each skill is aware of the
active [OpenSpec](https://github.com/Fission-AI/OpenSpec) change when a repo uses
OpenSpec, works without it, and never adds model attribution to commits, PRs, or
comments.

## Skills

| Skill | What it does |
|---|---|
| `ep-commit` | Splits working-tree changes into logical Conventional Commits that match the repo's style. |
| `ep-open-pr` | Pushes the branch and opens a GitHub PR with a title and body built from the commits and the active OpenSpec change, labelled as a one-way or two-way door, with its risk tier, the tests actually run, and how to revert. When UI files change, screenshots the affected pages from the running app after confirmation and links them in the body (`--screenshots` pre-approves, `--no-screenshots` skips). |
| `ep-review` | Reviews a diff, branch, or PR for correctness, spec conformance, tests, and security, confirms each finding by a 3-verifier vote, tags bugs the change did not introduce as pre-existing, follows the repo's `REVIEW.md`, re-reviews only new commits with `--since` and `--known`, and reports the change's risk tier. |
| `ep-babysit-pr` | Watches a PR: fixes CI failures, answers review comments, runs up to 3 review rounds (later ones only on new commits), and merges when gates pass and the confidence score is at least 85; medium-risk PRs wait for your yes and high-risk ones also for a human approval. |
| `ep-sync` | Merges the base branch into the current branch (rebase only on request, gated), then audits semantic interactions with no textual conflict (renamed or re-signatured symbols, behaviour and contract changes, new base callers, base tests), adapts the branch in separate commits, and runs tests. |
| `ep-fixup` | Attaches fixes to the branch commits they correct as `fixup!` commits, and autosquashes only on request: unpushed commits freely, pushed ones after confirmation with `--force-with-lease`. |
| `ep-ci-debug` | Diagnoses failing CI checks from their logs, classifies the cause (code, test, flaky-infra, config, secret), reproduces locally, and fixes it without weakening tests; re-runs infra failures once. |
| `ep-stack` | Splits a branch into a stack of dependent PRs after you approve the plan, linked as a native GitHub stack when the repository supports it and as plain branches otherwise (`--no-native` forces plain). Links an existing plain stack as a GitHub stack, shows stack status, syncs layers bottom up with merges, and moves or checks the next PR's base when a parent merges. |
| `ep-orchestrate` | Runs one OpenSpec change end to end: plans it, scores the plan and implements without asking only at 85 or more with nothing hard to undo, commits each task on its own, reviews each task group once and fixes its findings before the next group, removes dead code the branch added, and still runs up to 3 review and fix rounds, each phase in a fresh subagent with a resumable state file. Offers large changes as a stack of PRs landed with `ep-stack` and `ep-babysit-pr` after approval. |
| `ep-a11y` | Audits UI changes (diff, branch, PR, or paths) against WCAG 2.2 at Level AA by default, cites each verified finding by exact success criterion from bundled W3C references, lists what needs a manual check, and never claims conformance. Fixes findings in the working tree with `--fix` and posts one PR comment with `--comment`. |
| `ep-qa` | Audits an app or repository (whole checkout, one path, or a running app via `--url`) the way a senior QA engineer would: builds a test plan from manifests, scripts, CI, and docs, runs it after confirmation (`--yes` pre-approves) without deploying, publishing, or installing tools, probes the app with edge cases (routes that may change state, such as cron, send, or webhook routes, are not requested on local apps or `--url` and are listed under "Not covered"), checks docs against behavior, and writes an audit file (`qa-audit.md`, `--out` to change) of verified, reproducible problems plus what was not covered. Re-runs skip unchanged checks, track fixed and still-failing findings, and propose a regression test for each finding. |
| `ep-review-evals` | Measures `ep-review` against the repository's own history: collects incident cases (merged PRs later reverted or fixed forward) and clean PRs you accept, runs `ep-review` on each in a temporary worktree, scores recall and noise into labelled run files, compares two runs to say keep or drop a reviewer change, and suggests `REVIEW.md` lines from how authors answered posted findings. Read-only on GitHub and never commits. |

## Install

Uses the [skills CLI](https://github.com/vercel-labs/skills).

```bash
# Interactive: pick from the skills found in the repo
npx skills add emmpaul/skills

# All twelve ep-* skills
npx skills add emmpaul/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate ep-a11y ep-qa ep-review-evals

# A single skill
npx skills add emmpaul/skills --skill ep-commit

# From a local clone
npx skills add ./path/to/skills --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate ep-a11y ep-qa ep-review-evals

# User-level (global) instead of project-level
npx skills add emmpaul/skills -g --skill ep-commit ep-open-pr ep-review ep-babysit-pr ep-sync ep-fixup ep-ci-debug ep-stack ep-orchestrate ep-a11y ep-qa ep-review-evals
```

The repo also contains OpenSpec's own skills under `.claude/skills/` (used to develop this
repo), which the CLI lists too. Name the `ep-*` skills explicitly to install only these.

Remove with `npx skills remove ep-<name>`.

## `ep-qa` re-runs

`ep-qa` keeps a run record, `<audit-file stem>.state.json` (`qa-audit.state.json` by
default), beside the audit file you asked for. Like the audit file, it is never committed
and never added to `.gitignore`.

- **Skipped checks:** a later run skips a check that passed when nothing it depends on
  changed (source files, lockfiles and manifests, the command itself, its env files) and
  lists it as "skipped, unchanged since <sha>". Failed or flaky checks, `--url` probes,
  and re-checks of earlier findings always run again.
- **Fixed and still failing:** earlier findings are re-checked. The report lists what was
  fixed under "Fixed since last run"; what still fails keeps its `QA-<n>` id, and new
  findings continue after the highest id.
- **Regression test proposals:** each finding comes with a test in the project's own
  framework and layout, shown in the report with the path it would go at, or a reason
  why none is proposed (for example an external-service cause). The test is run
  in a scratch copy outside the repository to confirm it fails for the right reason; it
  is never written to the working tree.
- **`--full`:** ignore the record, run every check, number findings afresh, and replace
  the record. To start fresh for good, delete the `.state.json` file.

## `ep-open-pr` screenshots

`ep-open-pr` publishes PR screenshots on an `ep-pr-assets` branch of your remote, one
folder per branch head, with a plain push only after you confirm. That branch holds only
images, never touches your PR or default branch, and can be deleted at any time; the
skill recreates it when needed and never deletes it itself. Deleting it breaks the image
links in older PR bodies.

## Requirements

- `git`
- `gh`, authenticated (`gh auth login`)
- Optional: `openspec` CLI, for OpenSpec-aware behavior (required by `ep-orchestrate`)
- Optional: `bash`, to run the bundled context probe (`scripts/context.sh`); without it, skills run the equivalent commands inline

## Safety: `ep-babysit-pr` auto-merge

`ep-babysit-pr` can push to and merge your PR on its own. When it syncs a branch, fixes CI,
or commits review fixes, it calls `ep-sync`, `ep-ci-debug`, and `ep-fixup` in their
no-rewrite caller modes when they are installed, and uses bundled fallback steps when not. It never force-pushes,
never uses `--admin` or other protection bypasses, never resolves review threads,
and refuses to merge when checks fail, conflicts exist, threads are unresolved, or
changes are requested. It also defers to GitHub's merge state.

It also gates every merge on the change's **risk tier**, which `ep-review` reports from
the rules in `shared/risk.md`:

- **low** (every changed path is documentation, or matches a `low:` glob in your
  `REVIEW.md`, and the author is trusted): merges without asking.
- **medium** (the default for code changes): asks you first, showing the tier reasons,
  score, and head sha, and merges only after your yes for that exact head. A new push
  needs a new yes. In an unattended run it notifies you once and waits.
- **high** (CI workflows, `CODEOWNERS`, installers and release scripts, auth, billing,
  migrations, secret config, `high:` globs, or a one-way door): needs your yes and an
  approving GitHub review of the current head from a human other than the PR author. Bot
  and app approvals never count.

To let chosen paths merge without asking, add a `REVIEW.md` (at the root or in
`.github/`) with `low:` globs under `## Risk` and, for authors other than the
authenticated `gh` user, their logins under `## Trusted authors`:

```markdown
## Risk

- low: examples/**

## Trusted authors

- octocat
```

A `low:` glob never lowers a built-in high match. The skills read `REVIEW.md` from the
PR's base branch, never from the PR itself, and a PR that changes `REVIEW.md` is at least
medium, so a PR cannot lower its own tier or trust its own author.

Because the reviewer it relies on is also an agent, **enable branch protection
requiring at least one human approval** on any repo where an unreviewed merge
would matter. The skill then waits for that approval instead of merging.

## Development

`shared/context.sh` is the source of truth for the context probe. Each skill ships
its own copy because skills are installed folder by folder.

```bash
scripts/sync-shared.sh    # copy shared/ files into the skills that use them
scripts/check-shared.sh   # fail if any copy differs (run before committing)
```

### WCAG references

`ep-a11y` cites WCAG from files generated from W3C's published `wcag.json` into
`skills/ep-a11y/references/wcag/`. Never edit them by hand; `scripts/wcag.py` (Python 3,
standard library only) regenerates and checks them. The WCAG version is the `VERSION`
setting at the top of the script (`--version` overrides it once).

```bash
python3 scripts/wcag.py update --dry-run   # list added, removed, and changed criteria; writes nothing
python3 scripts/wcag.py update             # fetch from www.w3.org and regenerate (atomic; a bad source changes nothing)
python3 scripts/wcag.py check              # offline: hashes, index vs files, guidance citations (CI runs this)
```

After an update, read the `git diff` of `references/wcag/`, and for every changed or
removed criterion review its section in `skills/ep-a11y/references/checks.md` (and any
mention in `audit.md`), since `check` catches removed or obsolete criteria but not a
change in meaning. `checks.md` and `audit.md` are hand-written; the generator never
touches them. Run `python3 -m unittest scripts/test_wcag.py` after changing the
generator.
