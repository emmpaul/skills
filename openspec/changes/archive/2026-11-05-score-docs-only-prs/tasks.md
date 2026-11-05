# Tasks

## 1. Rubric

- [x] 1.1 Update `skills/ep-babysit-pr/references/score.md` item 5 with the docs-only rule and exclusion list from design D1/D2, plus an example breakdown line; verify both weight tables still sum to 100
- [x] 1.2 Update the score step in `skills/ep-babysit-pr/SKILL.md` to point at the docs-only rule; verify the delta spec scenarios each map to text in score.md

## 2. Verify

- [x] 2.1 Run `scripts/check-shared.sh` and `openspec validate score-docs-only-prs --strict`; verify both pass
- [x] 2.2 Babysit PR #1 in this repo with the updated skill and verify the tests item is reported as not applicable only if the diff has no agent instruction files, with the resulting score and merge decision reported
