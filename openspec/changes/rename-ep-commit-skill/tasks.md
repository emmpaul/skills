# Tasks

## 1. Rename the skill and add the push

- [x] 1.1 Move the folder with `git mv skills/ep-commit skills/ep-commit-and-push`, set the frontmatter `name` and the `#` heading to `ep-commit-and-push`, then run `scripts/sync-shared.sh` and `scripts/check-shared.sh`. Verify: `skills/ep-commit/` no longer exists, `skills/ep-commit-and-push/scripts/context.sh` is identical to `shared/context.sh`, and `check-shared.sh` exits 0.
- [x] 1.2 Load the `writing-for-agents` skill and rewrite `skills/ep-commit-and-push/SKILL.md` for the push (design D1-D4, D7): a new description (commit, commit and push, split changes into commits, write commit messages; valid YAML), hard rules replacing "Never push unless the user asks" with the plain-push, `--no-push`, and default-branch rules, a flags section for `--no-push`, the plan in step 3 naming the push target and commit count, a push step after "Verify" with the no-upstream, upstream, no-remote, rejected, and pre-push-hook branches and a completion criterion, and a report that states what was pushed or why nothing was. Verify: the frontmatter parses as YAML (`python3 -c` with `yaml.safe_load` on the block), no `<!-- ep-` summary block was added, and every requirement and scenario in `openspec/changes/rename-ep-commit-skill/specs/ep-commit-and-push/spec.md` maps to a line of the skill.
- [x] 1.3 Dry-run the push behavior in a scratch repository with a bare remote (in the scratchpad, never this repo's remote): follow the skill's steps once without `--no-push` and once with it. Verify: after the first run the bare remote's branch equals local `HEAD`; after the second the bare remote is unchanged and the report names the commit as local. Record the result in the task's commit body.

## 2. Callers

- [x] 2.1 In `skills/ep-orchestrate/SKILL.md` and `skills/ep-orchestrate/references/briefs.md`, rename every `ep-commit` to `ep-commit-and-push`, extend the general rule to tell the skill the intended commit, to just commit, and `--no-push` (design D4), and add the push line to the `#commit` fallback's "Rules that must match" while the fallback itself keeps "never push". Verify: `grep -nE 'ep-commit([^-]|$)' skills/ep-orchestrate -r` prints nothing, every line naming `ep-commit-and-push` as something a phase invokes is covered by the `--no-push` rule, the `#commit` anchor still exists, and `git diff` shows no change inside any `<!-- ep-orchestrate-` block.
- [x] 2.2 Rename the convention and offer references in `skills/ep-babysit-pr/SKILL.md`, `skills/ep-babysit-pr/references/side-paths.md`, `skills/ep-fixup/SKILL.md`, `skills/ep-ci-debug/SKILL.md`, `skills/ep-sync/SKILL.md`, `skills/ep-stack/SKILL.md`, `skills/ep-open-pr/SKILL.md`, `skills/ep-qa/SKILL.md`, and `skills/ep-a11y/references/fix.md` (name swaps only, design D4). Verify: `grep -rnE 'ep-commit([^-]|$)' skills/` prints nothing, `git diff --stat` touches no file under `skills/ep-a11y/references/wcag/`, no `<!-- ep-` block changed, and each edited skill's frontmatter is unchanged.

## 3. Docs and planning references

- [x] 3.1 Update `README.md`: the skills table row names `ep-commit-and-push` and says it pushes after committing (`--no-push` commits only, default branch asks first), every install command names `ep-commit-and-push`, and a short migration note gives `npx skills remove ep-commit` then `npx skills add emmpaul/skills --skill ep-commit-and-push`. Verify: `grep -nE 'ep-commit([^-]|$)' README.md` prints only the migration note's lines, and the "All twelve" command still lists twelve skills.
- [x] 3.2 Rename `ep-commit` to `ep-commit-and-push` in `openspec/config.yaml` (capability-naming example) and in `openspec/changes/add-ep-front-door-skills/proposal.md`, `openspec/changes/add-ep-hygiene-skills/specs/ep-spec-drift/spec.md`, and `openspec/changes/add-ep-after-merge-skills/design.md` (design D8). Verify: `grep -rnE 'ep-commit([^-]|$)' --exclude-dir=.git --exclude-dir=archive . | grep -v '^./openspec/specs/'` prints only the README migration note and files inside `openspec/changes/rename-ep-commit-skill/` (main specs under `openspec/specs/` keep the old name until archive), and `openspec validate --all --strict` passes or reports only failures already present before this task.

## 4. Integration check

- [ ] 4.1 Run `scripts/check-shared.sh`, `openspec validate rename-ep-commit-skill --strict`, and the stale-name grep from 3.2. Verify: all three pass as stated, and `ls skills` shows twelve skill folders including `ep-commit-and-push` and no `ep-commit`.

## Workflow follow-up

- Archive the change after review. `.openspec.yaml` sets `retire_capabilities: true`, so archive deletes `openspec/specs/ep-commit/` and creates `openspec/specs/ep-commit-and-push/`; verify both in the archive commit.
- Users with `ep-commit` installed replace it as the README migration note says.
