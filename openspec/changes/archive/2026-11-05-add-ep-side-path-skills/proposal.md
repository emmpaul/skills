# Proposal

## Why

The current `ep-*` chain handles the main path (commit, open PR, review, babysit). Everything that happens between commits on a live branch is improvised or buried inside `ep-babysit-pr`: bringing in the base branch, folding review fixes into the commit they belong to, debugging a red check, and splitting a large branch into reviewable pieces. Bringing in the base branch is the riskiest of these. A merge with no textual conflicts can still break the branch when base renamed a function the branch calls, changed a schema it writes to, or changed behaviour it relies on. Today nothing checks for that.

## What Changes

- **New** `ep-sync`: merges the base branch into the current branch (rebase only when invoked directly, and only on an unpushed branch or with explicit confirmation), then runs a **merge audit**. The audit finds semantic interactions between incoming base commits and the branch's own changes, even when there are no textual conflicts: renamed, removed, or re-signatured symbols the branch uses; changed behaviour; schema, migration, config, and API contract changes; new base call sites of code the branch modified; changed tests covering branch code; and, with OpenSpec, base spec changes overlapping the active change. Each interaction is classified as needs-update, review, or no-impact. The skill updates the branch's code for needs-update items, runs tests, commits each adaptation separately from the merge commit, and reports an audit table. It stops and asks when a semantic decision is ambiguous.
- **New** `ep-fixup`: turns a fix into a `fixup!` commit that targets the original commit it corrects. It autosquashes only unpushed commits, or pushed ones after explicit confirmation using `--force-with-lease`.
- **New** `ep-ci-debug`: diagnoses one failing check from its logs and classifies the cause (code, test, flaky-infra, config, secret). It reproduces locally where possible, then proposes or applies a fix. Infra failures are re-run once. Tests are never weakened.
- **New** `ep-stack`: splits a branch into dependent PRs, retargets children when a parent merges, and keeps the stack in sync (merge-based by default). PRs follow `ep-open-pr` conventions.
- **Modified** `ep-babysit-pr`: delegates CI failures to `ep-ci-debug`, review-comment fixes to `ep-fixup` in no-rewrite mode, and BEHIND/DIRTY branches to `ep-sync` in merge mode with the audit. When a sibling skill is not installed, it falls back to condensed inline steps bundled in its own folder. It reads each skill's summary block. Its forbidden actions are unchanged: no force-push, no rebase of a pushed branch.
- Every new skill ends with an `ep-<name>-summary` block that callers can parse.

Outward effects on GitHub:
- `ep-sync`, `ep-fixup`, and `ep-ci-debug` push to the current branch only after the user confirms, or when called by `ep-babysit-pr`, which already pushes. `ep-sync` rebase mode and `ep-fixup` autosquash of pushed commits use `--force-with-lease` and always need explicit confirmation.
- `ep-ci-debug` may re-run failed jobs (`gh run rerun --failed`) once per check.
- `ep-stack` creates PRs, changes PR base branches, and pushes stack branches after confirming the plan with the user.

## Capabilities

### New Capabilities
- `ep-sync`: bringing the base branch into the current branch and auditing the semantic interactions so the branch stays correct, not just conflict-free.
- `ep-fixup`: attaching fixes to the commit they correct with `fixup!` commits and safe autosquash.
- `ep-ci-debug`: diagnosing and fixing a single failing CI check from its logs.
- `ep-stack`: managing a stack of dependent PRs built from one branch.

### Modified Capabilities
- `ep-babysit-pr`: CI fixes, review-comment fixes, and branch updates for BEHIND/DIRTY go through `ep-ci-debug`, `ep-fixup`, and `ep-sync` (or their inline equivalents), and the results of those skills feed the loop.

## Impact

- New folders: `skills/ep-sync/`, `skills/ep-fixup/`, `skills/ep-ci-debug/`, `skills/ep-stack/`, each with `SKILL.md` and a synced `scripts/context.sh`, plus `references/` where needed.
- Modified: `skills/ep-babysit-pr/SKILL.md`, and a new `skills/ep-babysit-pr/references/side-paths.md` holding the condensed fallback steps.
- `README.md`: four new skill rows and install commands.
- `shared/context.sh` is unchanged. Skills run their extra git commands inline.
- Sibling changes: `add-ep-after-merge-skills` adds a separate post-merge requirement to `ep-babysit-pr`. This change does not touch the merge or post-merge requirements beyond the branch-behind and conflict handling.
