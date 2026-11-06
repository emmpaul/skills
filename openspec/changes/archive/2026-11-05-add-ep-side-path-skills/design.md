# Design

## Context

Today `ep-babysit-pr` handles CI fixes, review fixes, and BEHIND/DIRTY branches inline (SKILL.md steps 5a-5c and `references/score.md`). It forbids force-pushes and rebasing a pushed branch. Skills are installed folder by folder, so `ep-babysit-pr` cannot read files from `ep-sync` or the other new skills. It can invoke an installed sibling by name or follow its own copy of the steps. `ep-review` already sets the caller contract: an HTML-comment summary block (`ep-review-summary`) that `ep-babysit-pr` parses. See proposal.md for why, and the specs for behavior.

## Goals / Non-Goals

**Goals:**
- Each new skill is useful on its own and also callable by `ep-babysit-pr`.
- One summary-block convention across all callable skills.
- A merge audit that catches semantic breakage when there are no textual conflicts.
- No history rewrite when a skill runs unattended.

**Non-Goals:**
- Static analysis tooling or language servers. The audit uses git, grep, and reading code, and runs tests when they exist.
- Full stacked-diff tools (Graphite, ghstack, spr). `ep-stack` uses plain branches and `gh`.
- Changes to `shared/context.sh`.
- Changes to the merge or post-merge requirements of `ep-babysit-pr` beyond branch-behind handling. `add-ep-after-merge-skills` adds post-merge behavior separately.

## Decisions

### D1. Layout

```
skills/
  ep-sync/      SKILL.md  scripts/context.sh  references/audit.md
  ep-fixup/     SKILL.md  scripts/context.sh
  ep-ci-debug/  SKILL.md  scripts/context.sh  references/classes.md
  ep-stack/     SKILL.md  scripts/context.sh
  ep-babysit-pr/references/side-paths.md      (new: condensed fallback steps)
```

`audit.md` holds the interaction checklist and the report table format. `classes.md` holds the failure classes and the action for each.
- Alternative: one `references/` file shared across folders. Rejected because install is per folder (D4 covers the duplication).

### D2. Summary-block contract

Every callable skill ends its output with:

```
<!-- ep-<name>-summary
outcome: <skill-specific enum>
head: <sha after the skill ran>
<key>: <value>          # one per line, flat, no nesting
-->
```

| Skill | outcome | other keys |
|---|---|---|
| ep-sync | `synced`, `up_to_date`, `needs_decision`, `needs_attention` | `mode: merge\|rebase`, `base: <ref>@<sha>`, `conflicts: <n>`, `audit: needs_update=<n> review=<n> no_impact=<n>`, `unresolved_needs_update: <n>`, `tests: passed\|failed\|not_run`, `pushed: true\|false` |
| ep-fixup | `created`, `squashed`, `needs_decision`, `nothing_to_do` | `fixups: <fixup-sha>-><target-sha>,...`, `rewritten: true\|false`, `pushed: true\|false` |
| ep-ci-debug | `fixed`, `rerun`, `reported`, `nothing_failing` | one `check: <name> class=<class> result=<fixed\|rerun\|reported> fix=<sha\|none>` line per check |
| ep-stack | `planned`, `created`, `synced`, `retargeted`, `status` | one `layer: <i> branch=<b> pr=<n\|none> base=<b> state=<state>` line per layer |

Callers parse only keys they know and ignore the rest, so keys can be added later without breaking them. This mirrors `ep-review-summary`.

### D3. Invocation and the caller flag

`ep-babysit-pr` invokes a sibling skill by name when it is installed. It tells the skill it is a caller (`--caller ep-babysit-pr`, or the same words in plain-language agents). Caller mode means:
- `ep-sync`: merge mode only, no push prompt (the caller pushes), and it returns `needs_decision` instead of waiting for the user.
- `ep-fixup`: no-rewrite mode, plain push.
- `ep-ci-debug`: commit and push without a prompt; the caller owns the attempt counter.

When the sibling is not installed, babysit follows `references/side-paths.md`. That file has three short sections (ci-debug, fixup, sync-and-audit) with the same rules and summary fields, so the rest of the loop is the same on both paths. Detecting whether a skill is installed is a plain instruction ("if the skill `ep-sync` is available to you"), because skills cannot probe the host.

| Path | CI failure | Review fix | BEHIND / DIRTY |
|---|---|---|---|
| Sibling installed + subagents | subagent runs `ep-ci-debug` per check | `ep-fixup` (no-rewrite) inline | subagent runs `ep-sync --caller`; audit clusters fan out inside it |
| Sibling installed, no subagents | `ep-ci-debug` inline | `ep-fixup` inline | `ep-sync --caller` inline, clusters in sequence |
| Sibling missing | `side-paths.md#ci-debug` | `side-paths.md#fixup` | `side-paths.md#sync` |

### D4. Duplication of fallback steps

`side-paths.md` duplicates a condensed form of the three skills' core rules. That is the only file whose content is shared across skill folders. It is justified because install is per folder, and babysit must work alone (existing "Works without subagents" requirement, extended). Unlike `context.sh`, it is a condensed copy, not a byte-for-byte one, so a sync script can't keep it identical. Instead, each skill's SKILL.md and `side-paths.md` both carry a "rules that must match" list (never weaken tests, re-run once, no rewrite in caller mode, summary keys), and a task checks that the lists agree.
- Alternative: require the siblings to be installed. Rejected because it breaks partial installs, which the existing design already rejected for `ep-context`.

### D5. Merge audit method (`ep-sync`)

```
fetch base --> merge (or confirmed rebase) --> resolve textual conflicts
                                                   |
            +--------------------------------------+
            v
   B = commits in base not in branch (merge-base..base)
   R = branch's own diff (merge-base..branch, pre-merge)
            |
            v
   collect interactions:
     1. symbols R adds calls/imports/overrides for  x  symbols B renames/removes/re-signatures/changes
     2. contracts (schemas, migrations, config keys, API/route/type defs) touched by both
     3. new call sites in B of functions R modified
     4. tests in B that cover files R modified
     5. (OpenSpec) specs/changes in B overlapping the active change's capabilities
            |
            v
   cluster by file/symbol --> classify each: needs-update | review | no-impact
            |
            v
   adapt needs-update (separate commits) --> run tests --> report table + summary
```

Symbol collection is heuristic. It reads identifiers from R's diff hunks and greps B's diff for them (definitions, renames via `git log -M`, signature lines), then reads the surrounding code to decide. Clusters are groups of interactions sharing a file or symbol. With subagents, each cluster goes to one subagent, which returns a classification and a proposed patch, and the main agent applies the patches. Without subagents, clusters are audited in sequence. Adaptation commits use ep-commit conventions, with type `fix` or `refactor` and a body naming the base commit that caused them.

Rebase mode runs the same audit against the rebased result. Adaptations are then committed on top, never squashed into rewritten commits, so the audit trail stays visible.
- Alternative: rely only on tests after merging. Rejected because many branches have thin tests, and the user explicitly wants the logic checked.

### D6. Fixups in babysit depend on merge method

Babysit detects the merge method exactly as `references/score.md` already does. With squash, `fixup!` commits are useful: reviewers can see which commit a fix belongs to, and squash removes them at merge. With merge or rebase methods, babysit can never autosquash (no rewrite), so `fixup!` subjects would land on the base branch. Babysit therefore makes normal ep-commit commits there.
- Alternative: always use fixup commits and ask the user to autosquash before merging. Rejected because it blocks unattended merge.

### D7. Gates for outward and destructive actions

| Action | Gate |
|---|---|
| push after `ep-sync`, `ep-fixup`, `ep-ci-debug` (direct) | user confirms |
| push in caller mode | caller owns it (babysit already pushes) |
| `--force-with-lease` (sync rebase, fixup autosquash of pushed commits, stack rebase) | explicit confirmation naming the branch; direct invocation only; never `--force` |
| `gh run rerun --failed` | at most once per check per invocation |
| create PRs, change PR base, push several branches (`ep-stack`) | plan shown and confirmed |
| ambiguous conflict or adaptation | stop with options; caller gets `needs_decision` |

### D8. ep-stack branches and retargeting

Layer branches are named `<branch>-<i>-<slug>` unless the user names them. Stack order is stored in each PR body as a stack list marked with an HTML-comment marker (`<!-- ep-stack -->`) so `status` can rebuild it from GitHub, with no local state file. A child is retargeted with `gh pr edit <n> --base <b>` and then synced (through `ep-sync` when installed).
- Alternative: a local state file such as `.git/ep-stack.json`. Rejected because the stack must survive across clones and machines.

## Risks / Trade-offs

- [Audit misses an interaction because the heuristics have no type information] → Run tests after the sync, report what was checked, and treat "review" as a first-class class rather than forcing a yes/no.
- [Audit is noisy on large base updates] → Cluster interactions, report no-impact items only as counts, and audit only the symbols in R's diff.
- [Fallback steps in `side-paths.md` drift from the sibling skills] → "rules that must match" lists, plus a verification task (D4).
- [`fixup!` commits reach base when a repo changes merge method mid-PR] → Babysit checks the merge method each time it creates a fix.
- [Caller-mode sync merges base but the audit needs a human] → Nothing is pushed on `needs_decision`, and babysit stops and notifies.
- [Stack retarget races with a human editing the PRs] → `status` re-reads from GitHub before every action, and retargeting is confirmed.
