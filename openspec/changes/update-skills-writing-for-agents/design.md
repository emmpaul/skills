# Design

## Context

See proposal.md (Why). The rubric is `.agents/skills/writing-for-agents/SKILL.md` and `SKILL-MECHANICS.md`, vendored from `mattpocock/skills` and pinned in `skills-lock.json`. It is not changed by this change.

What the rewrite has to preserve, as found in the repo at base `6704efa`:

- **Summary blocks** parsed across skills: `ep-review-summary` (read by `ep-babysit-pr`, `ep-orchestrate`, `ep-review-evals`, and quoted in `shared/risk.md`), `ep-orchestrate-*` phase blocks in `ep-orchestrate/references/briefs.md`, `ep-orchestrate-summary`, `ep-stack-summary`, `ep-sync-summary`, `ep-fixup-summary`, `ep-ci-debug-summary`, `ep-qa-*`, `ep-review-evals-summary`, `ep-a11y-summary`.
- **Anchored links** between files: `side-paths.md#ci-debug|#fixup|#sync` (from `ep-babysit-pr`, `ep-ci-debug`, `ep-fixup`, `ep-sync`), `score.md#risk-gate`, `risk.md#documentation-only-paths|#reviewmd-syntax|#low|#high|#raising-the-tier`, `screenshots.md` → `#8-body`, `ep-open-pr` → `#5-screenshots`, and `briefs.md#commit|#fix|#review|#review-fallback`. `ep-orchestrate/SKILL.md` also hands each phase worker a `briefs.md` section by its `## <phase>` heading name.
- **Condensed fallbacks**, where one skill restates another skill's rules for agents without that skill installed: `ep-babysit-pr/references/side-paths.md` condenses `ep-ci-debug`, `ep-fixup`, and `ep-sync`; `ep-orchestrate/references/briefs.md` has `## commit` (condenses `ep-commit`) and `## review fallback` (condenses `ep-review`); `ep-orchestrate/references/confidence.md` cites `ep-open-pr/SKILL.md`.
- **Generated or synced files**: `skills/ep-a11y/references/wcag/**` (from `scripts/wcag.py`; `checks.md` and `audit.md` may cite only criteria that `scripts/wcag.py check` accepts), `shared/risk.md` (copied to four skills), and `shared/context.sh` (copied to all twelve).
- **CI** (`.github/workflows/check.yml`): `scripts/check-shared.sh`, `bash -n` over scripts, `scripts/wcag.py check`, and `openspec validate --all --strict`.

Installed skills in `~/.agents/skills/` are separate copies, so editing `skills/` does not change a skill that is already running.

## Goals / Non-Goals

**Goals:**
- Every skill reads as the rubric describes: a lean description, steps first with completion criteria, disclosed reference, positive rules, one source per rule.
- The authoring rule reaches every future skill edit through an always-loaded pointer (`AGENTS.md`) and through the planning rules (`openspec/config.yaml`).
- Each rewrite is checked mechanically against the base, not only by reading.

**Non-Goals:**
- No change to what any skill does, and no edits to main specs.
- No new skills, scripts, or CI steps. The checks below run from the shell during apply and are not committed.
- No change to `README.md`. It is a human-facing catalogue, not an agent-facing document.
- No change to whether a skill is model-invoked. All twelve stay model-invoked, because other skills reach them (for example `ep-babysit-pr` calls `ep-review`, `ep-ci-debug`, `ep-fixup`, and `ep-sync`).

## Decisions

**1. One new `skill-authoring` capability, not twelve modified ones.** The rewrite keeps every skill's requirements as they are, so a delta on each skill spec would be empty or invented. The authoring rule and the interface-preservation contract belong to the repository, not to any one skill. The config rule "one capability per skill, named after the skill" governs specs of skills; `skill-authoring` is not a skill, so it does not conflict. Alternative considered: `skip_specs: true`. Rejected because `AGENTS.md` and the config rules are durable, checkable repo behavior that later changes rely on.

**2. Rewrite pass per file, in this order.**
1. Description: one sentence on what the skill does, then each trigger branch once. Keep the leading words that callers and prompts use (for example `babysit`, `shepherd`, `land`; `orchestrate`, `end to end`). Drop detail the body carries, such as numeric limits and flag lists, unless it decides whether the skill fires.
2. Hierarchy: steps first. Each step ends on a checkable completion criterion. Reference used by every branch stays in-file next to the step it governs (co-location). Reference used only by some branches (one mode, one flag, a fallback path) moves to `references/` behind a pointer that names when to read it.
3. Phrasing: turn prohibitions into the positive target. Keep a prohibition only for a hard guardrail (never push, never `--no-verify`, no attribution, never merge with bypass), and pair it with the positive target.
4. Pruning: state each rule in one place and point to it from the others. Delete no-ops: whole sentences that tell the model what it already does by default. Delete restatements of what one command or file lookup shows, and stale lines.

A meaning repeated across skills on purpose stays: a summary block quoted by its consumer, or a condensed fallback. The rubric's "single source" does not apply to them, because a skill folder may reference only files inside itself.

**3. Mechanical interface checks per skill, against base `6704efa`.** Every rewrite task runs these from the repo root with `<skill>` set. Each must print `ok` or nothing.

- *Summary blocks*: every `<!-- ep-… -->` block in the skill folder at base exists byte-identical somewhere in the folder now:
  ```bash
  python3 -c 'import re,subprocess as s,sys,glob;sk,b=sys.argv[1:];r=lambda t:set(re.findall(r"<!-- ep-[\s\S]*?-->",t));old=set().union(*[r(s.run(["git","show",b+":"+f],capture_output=True,text=True).stdout) for f in s.run(["git","ls-tree","-r","--name-only",b,"skills/"+sk],capture_output=True,text=True).stdout.split() if f.endswith(".md")]);new=set().union(*[r(open(f).read()) for f in glob.glob("skills/"+sk+"/**/*.md",recursive=True)]);m=old-new;print("\n".join(m) or "ok");sys.exit(bool(m))' <skill> 6704efa
  ```
- *Flags*: no `--flag` token present at base is missing now:
  ```bash
  comm -23 <(git ls-tree -r --name-only 6704efa skills/<skill> | grep '\.md$' | grep -v /wcag/ | xargs -I{} git show 6704efa:{} | grep -oE -- '--[a-z][a-z-]+' | sort -u) <(find skills/<skill> -name '*.md' -not -path '*/wcag/*' -exec cat {} + | grep -oE -- '--[a-z][a-z-]+' | sort -u)
  ```
- *Anchors*: every in-repo `](file#anchor)` link resolves to a heading:
  ```bash
  python3 -c 'import re,glob,os,sys;bad=0
  slug=lambda h:re.sub(r"[^\w\- ]","",h.strip().lower()).replace(" ","-")
  for f in glob.glob("skills/*/**/*.md",recursive=True)+glob.glob("shared/*.md"):
    if "/wcag/" in f: continue
    for p,a in re.findall(r"\]\(([^)#\s:]*)#([^)\s]+)\)",open(f).read()):
      t=os.path.normpath(os.path.join(os.path.dirname(f),p)) if p else f
      hs={slug(h) for h in re.findall(r"^#+ (.*)$",open(t).read(),re.M)} if os.path.exists(t) else set()
      if a not in hs: print("broken:",f,p+"#"+a); bad=1
  print("ok" if not bad else "");sys.exit(bad)'
  ```
- *Frontmatter*: `SKILL.md` starts with `---`, `name: <skill>`, and a one-line `description:`, then `---`. The description is not longer than at base: compare `git show 6704efa:skills/<skill>/SKILL.md | sed -n 3p | wc -c` with `sed -n 3p skills/<skill>/SKILL.md | wc -c`.
- *Size*: `wc -l skills/<skill>/SKILL.md` is not above its base count.
- *Spec*: read `openspec/specs/<skill>/spec.md` and confirm, scenario by scenario, that the rewritten files still state the behavior each THEN clause needs. List any requirement you could not trace in the commit body.

A failing check is fixed in the rewrite, not by editing the check or the spec. When a check fails because a duplicate was removed on purpose (for example a flag named twice and now named once), the set-based checks already allow it. Anything else that fails means behavior moved, and the rewrite goes back.

**4. Condensed fallbacks are rewritten with their owner, then re-checked against their source.** `side-paths.md` is rewritten in the `ep-babysit-pr` task, after `ep-ci-debug`, `ep-fixup`, and `ep-sync` are done, and is checked against them. `briefs.md` `## commit` and `## review fallback` are rewritten in the `ep-orchestrate` group, after `ep-commit` and `ep-review` are done. That is why the groups run small skills first and the two big consumers last.

**5. `shared/risk.md` is edited in `shared/` only, then synced.** It is rewritten in the `ep-review` group (its main consumer), followed by `scripts/sync-shared.sh` and `scripts/check-shared.sh`. The four copies are never edited by hand.

**6. Durable pointer: `AGENTS.md` as the single source, `CLAUDE.md` as a one-line import.** `AGENTS.md` is read by most agents. Claude Code reads `CLAUDE.md`, so `CLAUDE.md` holds only `@AGENTS.md`, keeping one source. `AGENTS.md` itself follows the rubric. It is a pointer: it names `writing-for-agents` with its trigger ("before creating or editing anything under `skills/` or `shared/`, or this file"), plus the repo conventions an agent cannot find by looking: edit `shared/` then sync, run `scripts/check-shared.sh`, keep summary blocks byte-compatible, change generated WCAG files only through `scripts/wcag.py`, and leave vendored skills under `.agents/skills/` as they are. It does not restate the `openspec/config.yaml` context. Alternative: duplicate the text in both files. Rejected as duplication.

**7. Planning rules in `openspec/config.yaml`.** Add one rule each under `proposal`, `design`, and `tasks`:
- proposal: a change that adds or edits a skill applies the `writing-for-agents` skill to its description and body;
- design: a skill design keeps reference that only some branches need in `references/`, behind a pointer;
- tasks: a task that writes or rewrites skill prose ends by checking frontmatter, summary-block format, and the skill's spec requirements.

The existing `context` string stays as it is.

**8. Active changes get one task line, no plan edits.** Each of `add-ep-front-door-skills`, `add-ep-hygiene-skills`, and `add-ep-after-merge-skills` gets one unchecked task in its last numbered group (`## 5.`): "write each new or edited `SKILL.md` and reference with the `writing-for-agents` skill; verify descriptions list each trigger branch once and steps end on completion criteria". Their proposals, designs, and specs are not touched. `openspec validate --all --strict` must still pass.

**9. Grouping.** There are six groups, sized by the lines of hand-written Markdown in each. Each group can be reviewed on its own:
1. Repo authoring rule: `AGENTS.md`, `CLAUDE.md`, config rules, active-change task lines (small, done first so later groups run under it).
2. `ep-commit`, `ep-fixup`, `ep-ci-debug`, `ep-sync`: about 1,000 lines, the side-path sources.
3. `ep-open-pr`, `ep-a11y`, `ep-qa`: about 2,200 lines, the audit and PR skills.
4. `ep-review`, `shared/risk.md`, `ep-review-evals`: about 1,300 lines, review and its evaluation.
5. `ep-babysit-pr`, `ep-stack`: about 1,350 lines, merge and stack shepherding, plus `side-paths.md`.
6. `ep-orchestrate`: about 1,300 lines, plus its fallbacks of `ep-commit` and `ep-review`, and a final whole-repo check.

**Subagent path and sequential fallback.** This change does not alter any skill's subagent path or its fallback. The rewrite keeps both paths in each skill, and each spec's "agents without subagents" scenarios are part of the spec check in Decision 3. No skill gains an outward or destructive action, so no new gate is needed. The existing gates are kept word for word in meaning, and the flag and summary-block checks confirm their tokens survive.

## Risks / Trade-offs

- [A rewrite drops a rule that no mechanical check covers, such as a sentence-level guardrail] → The spec check traces every THEN clause. Hard guardrails stay as explicit prohibitions under Decision 2.3. The per-group review compares the diff against base for removed rules.
- [Pruning a "no-op" that was not a no-op for some agent] → Delete only sentences that restate a default which every supported agent follows. When in doubt, keep the sentence: the rubric settles no-ops by running the skill, and this change does not run evals.
- [Moving reference into `references/` hides material a branch needs] → Move only material whose pointer can name the branch that needs it. Material every branch uses stays in `SKILL.md`.
- [A tighter description triggers less often] → Keep every trigger branch and its leading words. The task checks the trigger phrases at base are still covered.
- [Textual conflicts with `add-ep-front-door-skills` (`ep-open-pr/SKILL.md`) and `add-ep-after-merge-skills` (`ep-babysit-pr/SKILL.md`)] → Those changes are unstarted. Whichever lands second applies its edit to the current wording. Neither changes a summary block this change preserves.
- [`ep-review-evals` scores could shift because `ep-review` wording changed] → Accepted. Behavior is meant to stay the same, and `ep-review-evals compare` is how a user would measure any drift later.

## Migration Plan

Installed copies update when the user re-runs `npx skills add`. To roll back, revert the branch's commits: the change touches Markdown and YAML only.
