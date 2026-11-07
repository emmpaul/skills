# Tasks

## 1. ep-land

- [ ] 1.1 Write `skills/ep-land/SKILL.md` per design D2, D3, D7, D9 (frontmatter, probe usage with inline fallback, merged-state check, dirty-tree stop, ff-only update, evidence-based local deletion, guarded remote deletion and prune, gated archive branch and PR, gated issue closing, forbidden actions, `ep-land-summary` block, a "no follow-ups" mode for callers); verify every requirement and scenario in `specs/ep-land/spec.md` maps to a section
- [ ] 1.2 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify `skills/ep-land/scripts/context.sh` exists and the check passes
- [ ] 1.3 In a sandbox GitHub repo, land a squash-merged PR, a merge-commit PR whose remote branch was already deleted, and a PR whose local branch has an extra commit; verify the first two delete the local branch, the third keeps it and lists the commit, and no command errors on the missing remote branch
- [ ] 1.4 In the sandbox repo with OpenSpec, land a PR whose change has all tasks done, confirm the offer, and verify a `chore/archive-<change>` PR is opened with no attribution and nothing is committed to the default branch; repeat in a repo without OpenSpec and verify the archive step and any OpenSpec mention are absent
- [ ] 1.5 Add an `ep-land` row to the README skills table and install commands; verify the README install command names all skills listed in the table

## 2. ep-release

- [ ] 2.1 Write `skills/ep-release/references/semver.md` (bump table with the pre-1.0 column, first-release default, grouping order, PR link sources, changelog style detection) per design D5; verify the table reproduces the version scenarios in `specs/ep-release/spec.md` (1.4.2 + breaking = 2.0.0, 0.3.1 + feat = 0.3.2, no tag = 0.1.0)
- [ ] 2.2 Write `skills/ep-release/SKILL.md` (preconditions, range detection with tag prefix style, classification, OpenSpec capability section from archived changes, draft display, confirmation, tag-only path, release-branch PR path and re-run detection, existing-tag stop, no attribution, `ep-release-summary`, subagent classification with inline fallback); verify every requirement in `specs/ep-release/spec.md` maps to a section
- [ ] 2.3 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify the check passes
- [ ] 2.4 In the sandbox repo without a changelog, run the skill, decline once (verify no tag or release exists), then confirm and verify the annotated tag and GitHub release exist with grouped notes and no attribution
- [ ] 2.5 In the sandbox repo with a Keep a Changelog `CHANGELOG.md` and an archived OpenSpec change since the last tag, run the skill and verify it opens a `release/<v>` PR whose entry matches the file's style and lists the capability, then re-run after merging and verify it only tags and releases
- [ ] 2.6 Add an `ep-release` row to the README skills table and install commands; verify the table and commands list it

## 3. ep-revert

- [ ] 3.1 Write `skills/ep-revert/SKILL.md` per design D6, D7, D9 (merged check, already-reverted detection, merge-method detection, revert on `revert/pr-<n>`, conflict stop with abort, reason prompt, gated push and PR with reversibility section, OpenSpec spec-drift text without edits, never pushes to default or merges, `ep-revert-summary`, parallel drift subagent with sequential fallback); verify every requirement in `specs/ep-revert/spec.md` maps to a section
- [ ] 3.2 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify the check passes
- [ ] 3.3 In the sandbox repo, revert one merge-commit PR, one squash-merged PR, and one rebase-merged PR; verify each revert branch's diff against the default branch is the inverse of the original PR's diff and each PR body links the original, the reason, and the impact
- [ ] 3.4 In the sandbox repo with OpenSpec, revert a PR whose change was archived and verify the PR body names the affected capabilities and requirements and suggests a follow-up change while `git diff` shows no spec file edits; seed a conflicting later commit and verify the skill stops and lists the files
- [ ] 3.5 Add an `ep-revert` row to the README skills table and install commands; verify the table and commands list it

## 4. ep-babysit-pr post-merge landing

- [ ] 4.1 Write `skills/ep-babysit-pr/references/land.md` with the local-only landing steps from design D2 and D4 (ff-only update, evidence-based local deletion, tolerance for a deleted remote branch, prune); verify it matches the `ep-land` deletion rules in `skills/ep-land/SKILL.md`
- [ ] 4.2 Update `skills/ep-babysit-pr/SKILL.md`: after merge (step 7) and on the "merged by someone else" stop (step 4), run `ep-land <n>` in no-follow-ups mode or `references/land.md` inline; add the `landing` field to the state file with defaults for older files; report pending archive and issues as offers in the final report (step 8); verify each scenario in `specs/ep-babysit-pr/spec.md` of this change maps to text, and that the existing forbidden-actions list is unchanged
- [ ] 4.3 Run `scripts/check-shared.sh`; verify it passes
- [ ] 4.4 Babysit a passing PR in the sandbox repo to merge, with and without `ep-land` installed, and verify both runs leave the clone on an up-to-date default branch with the merged branch deleted, the state file `outcome` is `merged` with a `landing` entry, and no archive PR or issue closure happens

## 5. Integration

- [ ] 5.1 Install from the local path with `npx skills add ./ --skill ep-land ep-release ep-revert ep-babysit-pr` and verify the three new skills appear in `~/.agents/skills/` and are listed by the agent
- [ ] 5.2 Run `openspec validate add-ep-after-merge-skills --strict`; verify it passes
- [ ] 5.3 Write each new or edited `SKILL.md` and reference with the `writing-for-agents` skill; verify descriptions list each trigger branch once and steps end on completion criteria

## Workflow follow-up

- Archive the change after the skills are verified in real use, ideally with `ep-land` itself.
