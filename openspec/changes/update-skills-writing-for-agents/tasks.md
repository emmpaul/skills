# Tasks

Every rewrite task loads the `writing-for-agents` skill (`.agents/skills/writing-for-agents/SKILL.md` and `SKILL-MECHANICS.md`) first, applies the rewrite pass in design.md Decision 2, and finishes with the **interface checks** in design.md Decision 3 against base `6704efa`. The checks are: summary blocks, flags, anchors, frontmatter (description no longer than at base, every `Use when` trigger branch at base still covered), `SKILL.md` line count not above base, and a scenario-by-scenario trace of `openspec/specs/<skill>/spec.md`. A task is done only when every check passes.

## 1. Repo authoring rule

- [x] 1.1 Write the root `AGENTS.md` per design Decision 6, using the `writing-for-agents` skill: a pointer that names the skill and its trigger (creating or editing anything under `skills/` or `shared/`, or `AGENTS.md`/`CLAUDE.md`), plus the conventions an agent cannot find by looking (edit `shared/` and run `scripts/sync-shared.sh`, then `scripts/check-shared.sh`; summary blocks stay byte-compatible; WCAG files change only through `scripts/wcag.py`; vendored skills under `.agents/skills/` stay as they are). Write `CLAUDE.md` containing only `@AGENTS.md`. Verify both files exist, `AGENTS.md` names `writing-for-agents` and every convention listed here, and it restates nothing from the `openspec/config.yaml` context.
- [ ] 1.2 Add the three rules from design Decision 7 to `openspec/config.yaml` (one each under `proposal`, `design`, `tasks`), leaving `context` and the existing rules unchanged. Verify `openspec instructions proposal --change update-skills-writing-for-agents --json`, and the same for `design` and `tasks`, each return the new rule in `rules`, and `git diff 6704efa -- openspec/config.yaml` shows only added lines.
- [ ] 1.3 Add one unchecked task to the `## 5.` group of each active change's `tasks.md`, with the wording from design Decision 8: `add-ep-front-door-skills` (5.4), `add-ep-hygiene-skills` (5.4), `add-ep-after-merge-skills` (5.3). Verify `git diff 6704efa -- openspec/changes/add-ep-*/` shows exactly three added lines and nothing else, and that `openspec validate --all --strict` passes.

## 2. Commit and side-path skills

- [ ] 2.1 Rewrite `skills/ep-commit/SKILL.md`. Verify the interface checks for `ep-commit` pass, and that every rule in the "Rules that must match" list in `skills/ep-orchestrate/references/briefs.md` `## commit` is still stated in `ep-commit`.
- [ ] 2.2 Rewrite `skills/ep-fixup/SKILL.md`, keeping the `side-paths.md#fixup` link and the no-rewrite mode callers use. Verify the interface checks for `ep-fixup` pass.
- [ ] 2.3 Rewrite `skills/ep-ci-debug/SKILL.md` and `references/classes.md`, keeping the five cause classes and their names. Verify the interface checks for `ep-ci-debug` pass and the class names in `classes.md` match base (`git show 6704efa:skills/ep-ci-debug/references/classes.md`).
- [ ] 2.4 Rewrite `skills/ep-sync/SKILL.md` and `references/audit.md`. Verify the interface checks for `ep-sync` pass and every audit category at base is still present in `audit.md`.

## 3. PR and audit skills

- [ ] 3.1 Rewrite `skills/ep-open-pr/SKILL.md` and `references/screenshots.md`, keeping the `#5-screenshots` and `#8-body` anchors and the PR body sections. Verify the interface checks for `ep-open-pr` pass and the PR body section headings at base are unchanged. Also check that `skills/ep-orchestrate/references/confidence.md`, which cites `ep-open-pr/SKILL.md`, still matches what it cites.
- [ ] 3.2 Rewrite `skills/ep-a11y/SKILL.md`, `references/audit.md`, and `references/checks.md`, leaving `references/wcag/` untouched. Verify the interface checks for `ep-a11y` pass, `python3 scripts/wcag.py check` and `python3 -m unittest scripts/test_wcag.py` pass, and `git diff 6704efa -- skills/ep-a11y/references/wcag/` is empty.
- [ ] 3.3 Rewrite `skills/ep-qa/SKILL.md` and `references/plan.md`, `audit.md`, `record.md`, keeping the state-file and audit-file formats. Verify the interface checks for `ep-qa` pass and every fenced format template in `record.md` and `audit.md` at base is still present byte-identical.

## 4. Review skills and shared risk reference

- [ ] 4.1 Rewrite `skills/ep-review/SKILL.md` and `references/dimensions.md`, keeping the four dimensions, the 3-verifier vote and its inline fallback, `--since`/`--known`/`--comment`, and the finding and report formats that `ep-babysit-pr` and `ep-orchestrate` read. Verify the interface checks for `ep-review` pass and every fenced report or finding template at base is still present byte-identical.
- [ ] 4.2 Rewrite `shared/risk.md` (never the copies), then run `scripts/sync-shared.sh`. Verify `scripts/check-shared.sh` passes, the `#low`, `#high`, `#raising-the-tier`, `#documentation-only-paths`, and `#reviewmd-syntax` headings exist, the anchor check passes, and the summary-block and flags checks pass for `ep-review`, `ep-open-pr`, `ep-babysit-pr`, and `ep-stack`.
- [ ] 4.3 Rewrite `skills/ep-review-evals/SKILL.md` and `references/collect.md`, `scoring.md`, `noise.md`, keeping the case, run-file, and score formats and the `collect`/`run`/`compare`/`noise` modes. Verify the interface checks for `ep-review-evals` pass and every fenced file-format template at base is still present byte-identical.

## 5. Shepherding skills

- [ ] 5.1 Rewrite `skills/ep-babysit-pr/SKILL.md` and `references/score.md` and `side-paths.md`, keeping the hard gates, the 85 threshold, the risk gate, the attempt and round caps, the state-file format, and the `#ci-debug`, `#fixup`, `#sync`, and `#risk-gate` anchors. Verify the interface checks for `ep-babysit-pr` pass. Also verify each `side-paths.md` section still states the same rules as the rewritten `ep-ci-debug`, `ep-fixup`, and `ep-sync` (group 2).
- [ ] 5.2 Rewrite `skills/ep-stack/SKILL.md`, keeping the `split`, `link`, `status`, `sync`, and `retarget` modes, `--no-native`, every confirmation point, and the plain-branch fallback. Verify the interface checks for `ep-stack` pass.

## 6. Orchestrator and integration

- [ ] 6.1 Rewrite `skills/ep-orchestrate/SKILL.md` and `references/confidence.md`, keeping the 85 threshold, the hard-to-undo checklist, the score weights and item ids, the state-file format, the phase order, and the subagent path with its inline fallback. Verify the interface checks for `ep-orchestrate` pass, the weights still sum to 100, and every item id at base is unchanged.
- [ ] 6.2 Rewrite `skills/ep-orchestrate/references/briefs.md`, keeping every `## <phase>` heading name, the preamble's rules for every phase, and every phase summary block. Bring `## commit` in line with the rewritten `ep-commit` and `## review fallback` with the rewritten `ep-review`, stating the same rules. Verify the interface checks for `ep-orchestrate` pass, `grep -n '^## ' skills/ep-orchestrate/references/briefs.md` lists the same headings as at base, and the two fallbacks state the same rules as their sources.
- [ ] 6.3 Run the whole-repo checks: `scripts/check-shared.sh`, `bash -n` over `shared/*.sh scripts/*.sh skills/*/scripts/*.sh`, `python3 scripts/wcag.py check`, the anchor check, `openspec validate --all --strict`, and the summary-block and flags checks for all twelve skills. Also run `git diff --stat 6704efa -- shared/context.sh 'skills/*/scripts/' .agents/ README.md openspec/specs/` and confirm it is empty. Verify every command passes and that the total line count of the twelve `SKILL.md` files is below base.

## Workflow follow-up

- Re-install the skills (`npx skills add ./ --skill ...`) and use them for real before archiving.
- Archive the change; archive creates `openspec/specs/skill-authoring/spec.md`.
