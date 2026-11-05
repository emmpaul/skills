# Tasks

## 1. Repo setup and project config

- [x] 1.1 Update `openspec/config.yaml` with `context` and `rules` per design D8, and verify `openspec instructions proposal --change add-ep-git-workflow-skills --json` returns the new context and rules
- [x] 1.2 Create `skills/`, `shared/`, `scripts/` directories and verify they exist
- [x] 1.3 Write a basic root `README.md`: repo purpose, the four skills with one-line descriptions, install commands (`npx skills add emmpaul/skills`, single-skill install, local-path install), requirements (`git`, `gh`; optional `openspec`, `bash`), and a safety note on `ep-babysit-pr` auto-merge recommending branch protection; verify every section is present and the install commands match the CLI's syntax

## 2. Context probe

- [x] 2.1 Implement `shared/context.sh` emitting the JSON shape in design D2, with `pr: null` / `openspec: null` when `gh` or `openspec` is missing; verify the output parses as JSON in this repo, in a non-OpenSpec repo, and with `gh` unavailable on PATH
- [x] 2.2 Implement `scripts/sync-shared.sh` (copy probe into each `skills/*/scripts/`) and `scripts/check-shared.sh` (exit non-zero on any difference); verify the check fails after editing one copy and passes after sync

## 3. ep-commit

- [x] 3.1 Write `skills/ep-commit/SKILL.md` (frontmatter name/description, probe usage with inline fallback, grouping, Conventional Commit format, OpenSpec scope and task ticking, no-attribution rule using `git commit -F`, no history rewrite, subagent split for large diffs with sequential fallback); verify every requirement in `specs/ep-commit/spec.md` maps to a section
- [x] 3.2 Sync probe into `skills/ep-commit/scripts/` and verify in a scratch repo: mixed changes yield separate commits, no `Co-Authored-By` in `git log --format=%B`, and OpenSpec scope appears when a change is active

## 4. ep-open-pr

- [x] 4.1 Write `skills/ep-open-pr/SKILL.md` (preconditions, push without force, title/body template, OpenSpec section, draft/base options, no attribution); verify every requirement in `specs/ep-open-pr/spec.md` maps to a section
- [x] 4.2 Sync probe and verify against a test GitHub repo: PR is created with OpenSpec section and task progress, no "Generated with" footer, and a second run reports the existing PR instead of duplicating
- [x] 4.3 Add one-way / two-way door classification to `skills/ep-open-pr/SKILL.md` (Reversibility section, classification rules, report line) and the matching requirement to `specs/ep-open-pr/spec.md`; verify by opening a PR on the sandbox repo for a two-way change and checking the section, and check the one-way rules against a destructive-migration example

## 5. ep-review

- [x] 5.1 Write `skills/ep-review/references/dimensions.md` with checklists for correctness, spec conformance (requirement/scenario mapping), tests, and security, plus the finding shape and severity scale; verify each dimension has a checklist and the spec-conformance one covers missing, unspecified, and untested cases
- [x] 5.2 Write `skills/ep-review/SKILL.md` (targets, parallel dimension subagents with sequential fallback, verify pass, Workflow path at high effort in Claude Code, output modes incl. `--comment`, summary block for callers); verify every requirement in `specs/ep-review/spec.md` maps to a section
- [x] 5.3 Sync probe and verify on a branch with a seeded bug and a missing spec requirement: both are reported with location, severity, and failure scenario; a non-OpenSpec repo reports spec conformance as not applicable

## 6. ep-babysit-pr

- [x] 6.1 Write `skills/ep-babysit-pr/references/score.md` with hard gates, weights, no-OpenSpec redistribution, and the merge-state table from design D5/D6; verify weights sum to 100 in both modes
- [x] 6.2 Write `skills/ep-babysit-pr/SKILL.md` (PR resolution, loop pacing with and without scheduling, local state file in `.git/ep-babysit/`, CI fix with 3-attempt cap, comment classification incl. scope-change flagging, 3-round cap, score report, merge via `gh pr merge --delete-branch` with no `--admin`, forbidden actions); verify every requirement in `specs/ep-babysit-pr/spec.md` maps to a section
- [x] 6.3 Sync probe and verify on a test GitHub repo: a failing check gets fixed and pushed, a review comment gets a reply, a CHANGES_REQUESTED review blocks merge, and a clean PR with score >= 85 merges with branch deleted

## 7. Integration

- [x] 7.1 Run `scripts/check-shared.sh` and verify it passes for all four skills
- [ ] 7.2 Install from the local path with `npx skills add ./` (or the CLI's local-source form) and verify all four `ep-*` skills appear in `~/.agents/skills/` and are listed by the agent
- [x] 7.3 Run `openspec validate add-ep-git-workflow-skills --strict` and verify it passes

## Workflow follow-up

- Archive the change after the skills are verified in real use.
