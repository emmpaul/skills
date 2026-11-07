# Tasks

## 1. ep-issue

- [x] 1.1 Write `skills/ep-issue/references/door.md` with the one-way/two-way rules adapted from `ep-open-pr` section 4 for requested work (design D2); verify each rule bullet in `skills/ep-open-pr/SKILL.md` has a counterpart in `door.md`
- [x] 1.2 Write `skills/ep-issue/SKILL.md` (frontmatter, probe usage with inline fallback, new and triage modes, body structure with open questions, existing-labels-only via `gh label list`, duplicate search with subagent path and sequential fallback per design D5, confirmation gate and `--yes`, `--body-file`, no attribution, `ep-issue-summary` block per design D8); verify every requirement in `specs/ep-issue/spec.md` maps to a section
- [x] 1.3 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify `skills/ep-issue/scripts/context.sh` exists and the check passes
- [x] 1.4 Verify on a sandbox GitHub repo: a default run writes nothing until confirmed; a description matching an existing issue surfaces it before creating; a created issue uses only existing labels, includes the door call, and has no attribution in `gh issue view --json body`

## 2. ep-issue-to-change

- [x] 2.1 Write `skills/ep-issue-to-change/SKILL.md` (issue input via `gh issue view --json title,body,labels,comments`, OpenSpec-root check that stops without init, name derivation and existing-name prompt, `openspec new change`, proposal from `openspec instructions proposal` with existing capability paths per design D7, planning-only stop with pointer to the propose workflow, gated `--comment` link, `ep-issue-to-change-summary` block); verify every requirement in `specs/ep-issue-to-change/spec.md` maps to a section
- [x] 2.2 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify the copy exists and the check passes
- [ ] 2.3 Verify in a scratch OpenSpec repo linked to a sandbox issue: the change is created by the CLI (`.openspec.yaml` present), the proposal references the issue number, `openspec validate <change>` reports only missing-spec errors, no comment is posted without confirmation; and in a repo without OpenSpec the skill stops with no `openspec/` directory created

## 3. ep-start

- [ ] 3.1 Write `skills/ep-start/SKILL.md` (issue or description input, branch naming and existing-branch check per design D6, `git fetch` and base from `origin/<default>` or `--base`, dirty-tree prompt with named stash, optional `--change` only when an OpenSpec root exists, issue link in `branch.<name>.ep-issue` per design D3, no push without `--push`, `ep-start-summary` block); verify every requirement in `specs/ep-start/spec.md` maps to a section
- [ ] 3.2 Run `scripts/sync-shared.sh` and `scripts/check-shared.sh`; verify the copy exists and the check passes
- [ ] 3.3 Verify in a scratch clone with local `main` behind `origin/main`: `ep-start 17` creates `fix/17-...` at `origin/main`, sets `git config branch.<name>.ep-issue` to 17, pushes nothing (`git ls-remote --heads origin` unchanged); a dirty tree triggers the prompt; in a non-OpenSpec repo `--change` is not offered and OpenSpec is not mentioned

## 4. ep-open-pr issue reference

- [ ] 4.1 Update `skills/ep-open-pr/SKILL.md` section 4 to read `branch.<branch>.ep-issue`, fall back to the `<type>/<n>-` branch pattern, and add `Closes #n` (feat/fix) or `Refs #n` (other types) to the body per design D3; verify the `specs/ep-open-pr/spec.md` delta scenarios map to the new text
- [ ] 4.2 Verify on the sandbox repo: a PR from a branch made by `ep-start 17` contains `Closes #17`, and a PR from a branch without an issue has no issue reference and an otherwise unchanged body

## 5. Docs and integration

- [ ] 5.1 Add `ep-start`, `ep-issue`, and `ep-issue-to-change` to the README skills table and the "all skills" install command; verify `npx skills add ./ --list` (or the CLI's listing form) shows all seven `ep-*` skills
- [ ] 5.2 Run `scripts/check-shared.sh` and the CI shell parse loop (`bash -n` over `skills/*/scripts/*.sh`); verify both pass
- [ ] 5.3 Run `openspec validate add-ep-front-door-skills --strict` and verify it passes
- [ ] 5.4 Write each new or edited `SKILL.md` and reference with the `writing-for-agents` skill; verify descriptions list each trigger branch once and steps end on completion criteria

## Workflow follow-up

- Archive the change after the skills are verified in real use.
