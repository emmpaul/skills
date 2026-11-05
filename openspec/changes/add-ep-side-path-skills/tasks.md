# Tasks

## 1. ep-sync

- [x] 1.1 Write `skills/ep-sync/references/audit.md`: the five interaction checks from design D5, clustering, the three classes with an example of each, the report table format, and the `ep-sync-summary` keys from D2. Verify that each scenario under "Merge audit of semantic interactions" and "OpenSpec overlap in the audit" in `specs/ep-sync/spec.md` maps to a checklist item
- [x] 1.2 Write `skills/ep-sync/SKILL.md` covering base resolution, dirty-tree stop, merge default, gated rebase, conflict resolution with stop-on-incompatible, the audit (subagent per cluster with sequential fallback), separate adaptation commits with no attribution, tests after sync, push gate, caller mode (D3), the summary block, and a "rules that must match" list. Verify that every requirement in `specs/ep-sync/spec.md` maps to a section
- [x] 1.3 Run `scripts/sync-shared.sh`, then verify in a scratch repo where base renames a function the branch calls in a file with no conflict. Check that `ep-sync` merges, reports a needs-update interaction, commits the call-site update separately from the merge commit, tests pass, and the summary shows `needs_update=1 unresolved_needs_update=0`
- [x] 1.4 Verify the remaining audit cases in scratch repos: a changed signature, a config-key rename, a new base caller of a branch-modified function, and an ambiguous adaptation, which must return `needs_decision` with nothing pushed. Also verify a non-OpenSpec repo's report does not mention OpenSpec

## 2. ep-fixup

- [x] 2.1 Write `skills/ep-fixup/SKILL.md` covering target selection by blame over merge-base..HEAD, splitting multi-target changes, the normal-commit fallback for base lines, `fixup!` subjects, gated autosquash (unpushed vs pushed with `--force-with-lease`), no-rewrite caller mode, the summary block, and a "rules that must match" list. Verify that every requirement in `specs/ep-fixup/spec.md` maps to a section
- [x] 2.2 Run `scripts/sync-shared.sh` and verify in a scratch repo that a fix to commit 2 of 3 produces `fixup! <subject of 2>`, that autosquash of unpushed commits leaves 3 clean commits, that pushed commits trigger the confirmation prompt, and that caller mode reports `rewritten: false`

## 3. ep-ci-debug

- [x] 3.1 Write `skills/ep-ci-debug/references/classes.md` with the five classes, the signals for each, and the action for each, including re-run-once and never-weaken-tests. Verify that each class has signals and an action
- [x] 3.2 Write `skills/ep-ci-debug/SKILL.md` covering check selection, the log commands (`gh run view --log-failed`), quoted diagnosis, local reproduction, the OpenSpec-or-PR intent rule for test updates, the fix and push gate, caller mode, the parallel path with sequential fallback, the summary block, and a "rules that must match" list. Verify that every requirement in `specs/ep-ci-debug/spec.md` maps to a section
- [x] 3.3 Run `scripts/sync-shared.sh` and verify on a sandbox GitHub repo that a seeded failing test is classified `code`, fixed, and pushed after confirmation, and that a workflow reading a missing secret is classified `secret` with no code change

## 4. ep-stack

- [x] 4.1 Write `skills/ep-stack/SKILL.md` covering the `split`, `status`, `sync`, and `retarget` subcommands, plan-first approval, branch naming and the `<!-- ep-stack -->` body marker (D8), PRs following ep-open-pr conventions with no attribution, the merge-based sync through `ep-sync` when installed, gates (D7), and the summary block. Verify that every requirement in `specs/ep-stack/spec.md` maps to a section
- [x] 4.2 Run `scripts/sync-shared.sh` and verify on a sandbox repo that a 6-commit branch splits into 3 approved layers with 3 correctly based PRs, and that `status` rebuilds the stack from PR bodies alone. Merge PR 1 and verify that `retarget` moves PR 2 to `main` and syncs it

## 5. ep-babysit-pr integration

- [x] 5.1 Write `skills/ep-babysit-pr/references/side-paths.md` with condensed ci-debug, fixup, and sync-and-audit sections that produce the same summary fields as D2. Verify that each section's "rules that must match" list is identical to the list in the matching sibling SKILL.md
- [x] 5.2 Update `skills/ep-babysit-pr/SKILL.md` step 5a to delegate to `ep-ci-debug` or `side-paths.md#ci-debug` and count attempts from the summary. Verify against the modified "Fix CI failures" requirement and its scenarios
- [x] 5.3 Update step 5b so fixes go through `ep-fixup` no-rewrite in squash repos and are normal commits otherwise, with the merge method detected as in `references/score.md`. Verify against the modified "Address review comments" scenarios
- [x] 5.4 Update step 5c and the BEHIND/DIRTY rows of the merge-state table in `references/score.md` to use `ep-sync --caller` or `side-paths.md#sync`. Needs-update items become a fix round; `needs_decision` stops and notifies; review items are listed. Verify against the modified "Merge decision defers to GitHub" scenarios, and that the forbidden-actions list is unchanged
- [x] 5.5 Add the "No history rewrite through sibling skills" rule to the forbidden actions or hard rules, and the side-path fallback note to the no-subagents text. Verify that every requirement in `specs/ep-babysit-pr/spec.md` (this change) maps to text
- [x] 5.6 Verify on a sandbox repo with the siblings installed, then again with them removed (`npx skills remove ep-sync ep-fixup ep-ci-debug`). In both runs, check that babysit fixes a failing check, handles a fix comment, and syncs a BEHIND branch with an audit, with no force-push in `git reflog` or the PR timeline

## 6. Integration

- [x] 6.1 Add the four skills to the `README.md` table and to the install commands. Verify that the rows match the skills' frontmatter descriptions
- [x] 6.2 Run `scripts/check-shared.sh` and verify that it passes for all eight skills
- [x] 6.3 Install from the local path with `npx skills add ./ --skill ep-sync ep-fixup ep-ci-debug ep-stack` and verify that they appear in `~/.agents/skills/`
- [x] 6.4 Run `openspec validate add-ep-side-path-skills --strict` and verify that it passes

## Workflow follow-up

- Archive the change after the skills have been verified in real use. Coordinate with `add-ep-after-merge-skills`, which also modifies `ep-babysit-pr`.
