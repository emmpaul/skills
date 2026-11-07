# Design

## Context

See proposal.md for the motivation and specs/ for the requirements. Constraints that shape the design:

- Each skill folder is installed on its own, so a skill can read only files inside its own folder. Text that several skills need has to be copied in by `scripts/sync-shared.sh`, and `scripts/check-shared.sh` has to verify each copy. Today those scripts handle only `shared/context.sh` → `scripts/context.sh`.
- `ep-review` already fans out one subagent per dimension and then sends each finding (or batch of up to 5) to one verifier. Its Workflow path and `ep-orchestrate`'s `--workflow` path must each stay under 10 agents.
- `ep-babysit-pr` reads the `ep-review-summary` block by key, and so do `ep-orchestrate` (`briefs.md#review`) and its condensed `review fallback`. That fallback must produce the same block.
- `ep-babysit-pr` already stores the reviewed head (`last_review.head`), merges pinned with `--match-head-commit`, and never approves its own PRs.

## Goals / Non-Goals

**Goals:**
- One source of truth for risk rules, used by `ep-review`, `ep-open-pr`, and `ep-babysit-pr`.
- Changes to the summary block are additive. Callers that do not know a new line ignore it, and a caller reading an older block treats a missing `risk:` line as medium.
- Every new subagent fan-out has a sequential fallback that gives the same report structure.

**Non-Goals:**
- Quick, Standard, and Deep depth settings. Depth is still `--effort high` plus the Workflow opt-in. Picking a depth from the risk tier would start a Workflow without the user opting in.
- Nightly reviews of existing code, circuit breakers on revert rates, and merge queues. These need hosted infrastructure.
- Writing `REVIEW.md` for the user. `ep-review-evals noise` only proposes lines.
- Changing `ep-a11y`, `ep-qa`, `ep-sync`, or `ep-ci-debug`.

## Decisions

### 1. Voting: 3 voter agents, each judging every candidate

Each voter gets all deduplicated candidates and returns `confirmed | refuted | downgraded:<severity>` with a reason for each one. A finding is kept when at least 2 verdicts are not `refuted`. Its severity is the highest one that at least 2 non-refuting verdicts support: a `confirmed` verdict supports the claimed severity and everything below it, and `downgraded:x` supports `x` and below.

- **Subagent path:** 3 voter subagents run in parallel after the dimension subagents finish. Each voter gets the same brief, which tells it to argue that each finding is wrong, and none sees the others' verdicts. This makes 7 agents in all, the same for any number of findings. Above 20 candidates, each voter gets them in batches of 20 in its own context, one after another. That adds no agents.
- **Workflow path (`--effort high` in ep-review, `--workflow` in ep-orchestrate):** a `pipeline` over the 4 dimensions, then `parallel` over 3 voters, for 7 agents in all. `ep-orchestrate`'s current limit of 5 verifiers (9 agents) becomes 3 voters (7 agents).
- **Sequential fallback:** one inline disproof pass per finding, as today, and the summary records `verification: inline`. A single context cannot vote independently, so the summary says so instead of pretending.
- **Alternatives:** one verifier per finding, 3 times over (3 × N agents) goes far over the agent budget. 5 voters costs more, and the post gives no threshold to justify it. A 2-of-3 majority is the smallest vote that can break a tie.

### 2. Origin, instances, and the `verified:` counts

The finding shape in `references/dimensions.md` gains `origin: introduced | pre-existing`, `class:` (a short label such as "unchecked null from lookup"), and `instances:` (other `file:line` locations with the same defect). Origin is decided during verification. If blame (`git blame <base>` for the lines, or "line not in the diff's added lines") shows the defect's lines predate the target's base, the origin is `pre-existing`. The scope rule changes from "out of scope unless reachable" to "report when the defect is in a changed function or a direct callee or caller of one". This keeps pre-existing findings bounded.

`verified:` and `by_dimension:` count only introduced findings, so callers' gates stay the same. A new `pre_existing: <n>` line carries the rest. Pre-existing findings get their own `### pre-existing` report section, after the four dimensions.

### 3. Re-review: `--since` and `--known`

- `--since <sha>` makes the diff `git diff <sha>..<head>` (for a PR, `<head>` is `headRefOid` after `git fetch origin pull/<n>/head`). Spec conformance still uses the whole change's specs: a spec finding needs the full implementation, so for the spec dimension `--since` only narrows which requirements to re-check, not which code to search.
- `--known <file>` takes the `finding:` line format that `ep-orchestrate` already writes, with fields `id dimension severity file:line summary`. Before review, known findings go to verification as candidates, so the voters decide whether each is `still open` or fixed. New candidates that duplicate a known finding (same class and file, lines within 3) are dropped. The summary gains `known: fixed=<n> still_open=<n>`.
- **Callers:** `ep-babysit-pr` stores `last_review.findings` (the path of a findings file in `.git/ep-babysit/<pr>.findings`) and `last_review.synced_after` (set when step 5c pushes a sync). `ep-orchestrate` already has `<change>.findings`.
- **Comment-mode repeats:** before posting, list the PR's review comments (`gh api .../pulls/<n>/comments --paginate`) from reviews whose body contains `<!-- ep-review-summary`. Drop any finding whose `file` and summary match one of them. The body states "<n> already posted".
- **Alternative:** using `git range-diff` for re-review after a sync was rejected as fragile. A full review after a sync is simpler and safer.

### 4. Shared risk rules (`shared/risk.md`)

The rules live in one Markdown file, copied to `references/risk.md` in `ep-review`, `ep-open-pr`, and `ep-babysit-pr`. Sharing is justified because the three skills must agree on the tier: if they drifted, a PR body would say "low" while babysit asked. `sync-shared.sh` gets a small table of `(source, destination-relative-path, skills)`: context.sh goes to every skill, risk.md to the three. `check-shared.sh` iterates over the same table.

Tier rules, evaluated in this order:
1. **high:** any changed path matching `.github/workflows/**`, `.github/actions/**`, `CODEOWNERS`, installer, updater, or release scripts (`**/install*`, `**/*updater*`, `**/release*`), auth (`**/auth/**`, `**/*auth*`), billing (`**/billing/**`, `**/payment*`), DB migrations (`**/migrations/**`), secret config (`.env*`, `**/secrets*`), or a `high:` glob in `REVIEW.md`. Also any PR whose `ep-open-pr` Reversibility section says one-way door.
2. **low:** every changed path is documentation by `ep-babysit-pr`'s existing documentation-only rule (shared via this file, so `score.md` points to it), or matches a `low:` glob in `REVIEW.md`. Also the author must be trusted, meaning the authenticated `gh` user or listed under `## Trusted authors`. Otherwise the tier is raised to medium.
3. **medium:** everything else, and any `medium:` glob in `REVIEW.md`.

The reviewer may raise the tier with a reason (step 2 in the post: "does this specific change need another person anyway"). It may never lower it.

### 5. `REVIEW.md` format

Free Markdown, plus these recognised headings, each with a bullet list: `## Skip` (globs), `## Risk` (bullets `high: <glob>`, `medium: <glob>`, `low: <glob>`), `## Trusted authors` (GitHub logins), and `## Limits` (`max_minor: <n>`). All other text is passed to every dimension agent as repository guidance. Lookup order is `REVIEW.md`, then `.github/REVIEW.md`. Unknown headings are guidance, not errors.

### 6. Risk gate in `ep-babysit-pr`

A new item in step 7's merge condition, evaluated after the score and before the merge call:

| Tier | Needs | Recorded in state |
|---|---|---|
| low | nothing extra | — |
| medium | user's yes for `headRefOid` | `human_ok: { head }` |
| high | user's yes + an `APPROVED` review whose `commit_id == headRefOid` and whose author is neither the PR author nor `type: Bot` / an app | `human_ok`, approval id |

The ask is one structured question that shows the tier reasons, score breakdown, and head sha, with the options Merge, Wait, and Stop. In an unattended run (scheduled or looping), the skill uses the existing notify-once (`blocked_notified`) path and waits. `human_ok` is cleared whenever `headRefOid` changes. The gate adds no GitHub write. It only removes merges.

The approval check runs `gh api repos/{o}/{r}/pulls/<n>/reviews --paginate` and reads `user.type` and `commit_id`. Sequential fallback: none is needed, because the gate needs no subagents.

### 7. `ep-orchestrate` changes

Round *k* > 1 tells the review phase `since: <head of round k-1>` and `known: <change>.findings`. `briefs.md#review` passes these to `ep-review` as `--since` and `--known`. `briefs.md#review-fallback` mirrors them with the same rules: diff from that sha and re-check the known lines. "Clean" ignores `pre_existing`. Pre-existing findings go to the final report. The fix brief gets the `instances:` of each finding and fixes all of them in the same commit.

### 8. `ep-open-pr` body

The body gets `## Risk` after Reversibility, with the tier and bullets of reasons from `references/risk.md`. `## How to test` becomes `## Testing`, with **Run:** listing each command observed in this session, or the latest green CI run for the head (`gh run list --commit <sha>`), plus result and sha, and "Not run" when there is none. Then come **Steps:** as today. Reversibility gains `**How to revert:**` with `git revert -m 1 <merge commit>` (or `git revert <squash sha>`), and for a one-way door, what stays after the revert. Nothing is invented: Testing evidence comes only from commands seen or CI records.

### 9. `ep-review-evals` structure

```
skills/ep-review-evals/
  SKILL.md                 usage, subcommands, gates, summary block
  references/collect.md    revert/fix-forward detection, blame mapping, clean sampling
  references/scoring.md    hit rule, noise rule, run file format, compare verdict
  references/noise.md      response classification, REVIEW.md suggestion rule
  scripts/context.sh       synced probe
```

- **collect:** `gh pr list --state merged --search "merged:>=<date>"` and `git log --grep "This reverts commit"`, plus `git log --format=%H --grep '^fix' --regexp-ignore-case`. For each fix commit, run `git blame -w --porcelain <fix>^ -L` over its changed old lines, then map each blamed commit to a PR with `gh api repos/{o}/{r}/commits/<sha>/pulls`. The user confirms one structured question per case (Accept, Edit, Reject). The cases file holds `{id, kind: incident|clean, pr, base, head, bug: {file, lines, description}, confirmed_by, confirmed_at}`.
- **run:** for each case, `git worktree add --detach <scratch>/<id> <head>` (the scratch dir is outside the repo: the agent's scratch or `$TMPDIR`), run `ep-review --since <base>` from there, then `git worktree remove --force`. Removal also runs on failure, from a cleanup step listed first in the instructions. **With subagents**, each case runs in a fresh subagent, one at a time, because each `ep-review` already fans out to 7. **Without subagents**, cases run inline one after another. The reviewer version is the `git rev-parse HEAD` of the installed `ep-review` folder when that folder is a git checkout, else a sha256 of its `SKILL.md` and `references/*`.
- **compare and noise:** read-only computations over run files and `gh api` reads.
- **Gates:** writing `cases.json` or a run file is shown first and then confirmed. `run` confirms the case count and its cost (cases × about 7 agents). Nothing is committed, pushed, or posted.

### 10. `ep-open-pr` UI screenshots

Steps run after the body is drafted and before `gh pr create` or `gh pr edit`. The details live in a new `skills/ep-open-pr/references/screenshots.md`.

1. **UI touched?** Some changed path matches `*.tsx *.jsx *.vue *.svelte *.astro *.html *.css *.scss *.sass *.less`, or `**/components/** **/pages/** **/app/** **/views/** **/templates/** **/*.stories.*`, excluding test files (`*test*`, `*spec*`, `__tests__/`). If none matches, skip all of this step.
2. **Start command:** the first match among `package.json` scripts `dev`, `start`, `preview`, `storybook`, or a start command documented in the README. If none is found, the section reads "Not captured: no start command found".
3. **Gate 1:** show the command, the pages to visit, and the browser to use, then ask Run, Skip, or Stop. `--screenshots` pre-approves this gate. In a non-interactive run without `--screenshots`, skip with "Not captured: not confirmed".
4. **Browser:** use, in order, a host browser tool (the built-in browser, Claude in Chrome, or a Playwright MCP), then a Playwright already installed in the project (`npx --no-install playwright screenshot`). Never install a browser.
5. **Pages:** routes derived from changed files where the framework's convention makes that clear (Next.js `app/`/`pages/`, SvelteKit `routes/`, and so on), or a story URL for changed stories. Otherwise use `/`. Take at most 5 pages, each at 1280×800 and at 390×844, so at most 10 images. A redirect to a sign-in path is recorded as "needs sign-in", and nothing is typed into any form.
6. **Process lifecycle:** start the command in its own process group, with stdout and stderr in a scratch log. Wait up to 60 s for the port to answer. Afterwards, kill the process group and verify the port is free, as `ep-qa` does.
7. **Publish (gate 2, also pre-approved by `--screenshots`):** in a scratch `git worktree` (outside the repo), check out `origin/ep-pr-assets`, or create it with `git switch --orphan ep-pr-assets` when it is missing. Copy the PNGs to `<branch-slug>/<head-short-sha>/`, commit `chore: add screenshots for <branch> at <sha>` with no attribution, and run `git push origin ep-pr-assets` (plain). A non-fast-forward rejection gets one fetch and one retry; after that, fall back to local paths. Remove the worktree.
8. **Body:** a `## Screenshots` section after `## Changes`, with one `![<page> <width>](https://github.com/<o>/<r>/blob/ep-pr-assets/<path>?raw=true)` per image. These blob URLs work in private repos for viewers with access. Pages that were not captured are listed with their reason. If the push was declined, the section lists local paths and says to drag them in.

- **Subagents:** not used. Capture is sequential in every host.
- **Alternatives:** committing to the PR branch was rejected because it puts images into main. Uploads through GitHub's undocumented user-attachments endpoint were rejected because there is no supported API, and `gh` can't do it. A gist can't hold binary files through `gh gist create`.
- **Risks:** the assets branch grows over time. The README notes it can be deleted at any time, and the skill never deletes it. Screenshots of a local dev app may show local data, which is why gate 2 lists every image before anything is pushed.

## Risks / Trade-offs

- [Medium risk is the default, so babysit asks on most code PRs] → The user chose this. The README explains how `REVIEW.md` `low:` globs and trusted authors restore autonomous merges for chosen paths.
- [Voting triples verification cost] → Diff-only later rounds and repeat suppression cut total review work, which is the effect the post reports (mean reviews to pass went from 2.08 to 1.32). Inline hosts are unaffected.
- [Path globs for high risk give false positives, for example `**/*auth*` matching `author.ts`] → They only make the skill ask more, never merge more. `REVIEW.md` can't lower a built-in high match, but the user answers the ask. The glob list is kept short and documented.
- [Pre-existing detection via blame can be wrong after a file move] → Blame uses `-M -C`. When unsure, origin is `introduced`, which errs toward asking for a fix.
- [Diff-only rounds may miss interactions between fix and untouched code] → The reviewer still reads surrounding code and callers. Known findings are re-verified, and a sync forces a full round.
- [Eval line-matching is approximate] → The user confirms each bug location, and the ±3-line window and file match are documented. `compare` uses only the cases both runs share.
- [Overlap with `add-ep-after-merge-skills`, which also edits `ep-babysit-pr`] → The edits touch different steps (step 7's merge condition here, after-merge cleanup there). Whichever change lands second rebases its text.

## Migration Plan

- The changes are additive for callers. An older `ep-review` summary without `risk:` is treated as medium by the new babysit. Without `pre_existing:`, the counts read as before.
- Rollback: revert the PR. No state migration is needed. The new `human_ok` and `last_review.findings` state fields are ignored by the older babysit, and the existing "add missing fields with defaults" rule covers the newer one reading old state.
