# Tasks

## 1. ep-protect

- [ ] 1.1 Write `skills/ep-protect/references/baseline.md`: the five baseline item ids, how each is read from classic protection and from effective rules (design D3), the stricter-wins rule, the check-name discovery, and the ruleset-first apply strategy with the classic fallback (design D4). Verify that every baseline item has a read source and an apply field in both modes.
- [ ] 1.2 Write `skills/ep-protect/SKILL.md`: frontmatter, probe with inline fallback, audit, `--check` mode, gated apply showing method, endpoint, and JSON body, the never-weaken rule, the permission-error path (`unknown`), the non-interactive degrade to `--check`, no attribution, and the `ep-protect-summary` block (design D2). Verify that every requirement in `specs/ep-protect/spec.md` maps to a section.
- [ ] 1.3 Run `scripts/sync-shared.sh` and verify `skills/ep-protect/scripts/context.sh` exists and `scripts/check-shared.sh` passes.
- [ ] 1.4 In a sandbox GitHub repo with no protection, run `ep-protect --check` and verify outcome `gaps` with all five items listed and no API write (protection unchanged). Then run `ep-protect`, decline, and verify nothing changed. Then confirm, and verify that a ruleset named `ep-protect baseline` exists and a re-run reports `pass`.
- [ ] 1.5 In the sandbox, set classic protection to 2 required reviews plus a required check `lint`, run `ep-protect`, and verify that the shown request keeps 2 reviews and `lint`. Run it with a token without admin rights and verify outcome `unknown` with the missing permission named.
- [ ] 1.6 Add `ep-protect` to the README skills table and install commands, and point the auto-merge safety note at `ep-protect --check`. Verify the install command lists the new skill name.

## 2. ep-deps

- [ ] 2.1 Write `skills/ep-deps/references/risk.md` with the discovery queries, version parsing for Dependabot and Renovate titles, runtime vs development detection, release-note sources, security signals, and the low/medium/high rubric (design D5). Verify the three spec risk scenarios (patch with green CI, major, failing checks) each resolve to one class under the rubric.
- [ ] 2.2 Write `skills/ep-deps/SKILL.md`: discovery or explicit PR numbers, triage with the subagent path and sequential fallback, grouped report with security first, gated handoff to `ep-babysit-pr` (with the not-installed message), gated comment and close, no merge path, no attribution, and the `ep-deps-summary` block. Verify that every requirement in `specs/ep-deps/spec.md` maps to a section.
- [ ] 2.3 Run `scripts/sync-shared.sh` and verify `scripts/check-shared.sh` passes.
- [ ] 2.4 On a sandbox repo with Dependabot enabled and at least one patch and one major bump PR open, run `ep-deps` and verify the classification and grouping, quoted release notes, and that nothing is posted or merged without selection. Then select one low-risk PR and verify `ep-babysit-pr` starts on that PR only.
- [ ] 2.5 Add `ep-deps` to the README skills table and install commands, and verify the rows render.

## 3. ep-spec-drift

- [ ] 3.1 Write `skills/ep-spec-drift/references/method.md`: status definitions (implemented, partial, missing, untested), location citation, the verification pass, hotspot detection, and the no-tests note (design D6), with a short note that it adapts `ep-review`'s spec-conformance method. Verify that each status has a decision rule and an example.
- [ ] 3.2 Write `skills/ep-spec-drift/SKILL.md`: scope selection with unknown-capability handling, not-applicable stop without OpenSpec or main specs, per-capability subagents with sequential fallback, read-only default, gated `--issue` (including the no-drift and non-interactive cases), no attribution, and the `ep-spec-drift-summary` block. Verify that every requirement in `specs/ep-spec-drift/spec.md` maps to a section.
- [ ] 3.3 Run `scripts/sync-shared.sh` and verify `scripts/check-shared.sh` passes.
- [ ] 3.4 Run `ep-spec-drift` on this repository and verify that each main-spec requirement gets a status with locations, the working tree is unchanged (`git status` clean), and the summary counts match the report. Run it in a scratch repo without OpenSpec and verify it reports not applicable and stops.
- [ ] 3.5 Seed a missing requirement in a scratch copy of a main spec, run `ep-spec-drift <capability> --issue`, decline, and verify that the requirement is reported missing and no issue is created.
- [ ] 3.6 Add `ep-spec-drift` to the README skills table and install commands, and verify the rows render.

## 4. ep-pr-digest

- [ ] 4.1 Write `skills/ep-pr-digest/SKILL.md`: repo and `--all` scopes (including the outside-a-repo case), queries (design D8), first-match bucket order with oldest-first sorting, `--stale <days>`, the read-only rule with suggested next steps, empty digest, recurrence through host scheduling with the one-shot fallback, change markers from the cache file, and the `ep-pr-digest-summary` block. Verify that every requirement in `specs/ep-pr-digest/spec.md` maps to a section.
- [ ] 4.2 Run `scripts/sync-shared.sh` and verify `scripts/check-shared.sh` passes.
- [ ] 4.3 Run `ep-pr-digest` in this repository and with `--all`, and verify that each open PR authored by or awaiting review from the user appears in exactly one bucket, that the summary counts match, and that no GitHub write happened (no new comments, labels, or reviews on any listed PR).
- [ ] 4.4 Run it twice in a row with the cache, change one PR's state in between (for example, push a failing commit), and verify that the second digest marks that PR as changed.
- [ ] 4.5 Add `ep-pr-digest` to the README skills table and install commands, and verify the rows render.

## 5. Integration

- [ ] 5.1 Run `scripts/check-shared.sh` and verify it passes for all eight skills.
- [ ] 5.2 Install from the local path with `npx skills add ./ --skill ep-protect ep-deps ep-spec-drift ep-pr-digest` and verify that the four folders appear in `~/.agents/skills/` and the agent lists them.
- [ ] 5.3 Run `openspec validate add-ep-hygiene-skills --strict` and verify it passes.

## Workflow follow-up

- Follow-up change: make `ep-babysit-pr` run `ep-protect --check` as a preflight and warn or stop on `reviews` gaps.
- Archive the change after the skills are verified in real use.
