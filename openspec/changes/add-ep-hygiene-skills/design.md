# Design

## Context

The repository ships four `ep-*` skills, each a self-contained folder (`SKILL.md`, a synced `scripts/context.sh`, optional `references/`). The probe gives git, PR, and OpenSpec state for one branch. It knows nothing about protection, dependency bots, or PRs in other repositories, so the new skills fetch that state with `gh` themselves. See proposal.md for why these four skills exist, and specs/ for the required behavior.

## Goals / Non-Goals

**Goals:**
- Same structure as the existing skills: probe first, inline fallback, explicit gates, and a summary block at the end.
- Every write to GitHub sits behind a confirmation that names exactly what will be sent.
- Each skill is useful in a single non-interactive run (scheduled, or in an agent that cannot ask), where it degrades to read-only.

**Non-Goals:**
- Changing `shared/context.sh` or any existing skill. Wiring `ep-protect --check` into `ep-babysit-pr` is a follow-up change.
- Protection for branches other than the default branch, tag protection, or organization-level rulesets the token cannot see.
- Editing dependency manifests or lockfiles (`ep-deps` triages bot PRs; it does not create upgrades).
- Fixing drift. `ep-spec-drift` reports it; fixes go through a normal OpenSpec change.
- Notifications. `ep-pr-digest` prints a digest; delivery is whatever the host does with output.

## Decisions

### D1. Layout

```
skills/
  ep-protect/     SKILL.md  scripts/context.sh  references/baseline.md
  ep-deps/        SKILL.md  scripts/context.sh  references/risk.md
  ep-spec-drift/  SKILL.md  scripts/context.sh  references/method.md
  ep-pr-digest/   SKILL.md  scripts/context.sh
```

`scripts/sync-shared.sh` already copies the probe into every `skills/*/` that has a `SKILL.md`, so new folders need no script changes. Each skill still runs the probe for repo, default branch, `gh` availability, and OpenSpec root. Nothing new is shared across folders.

`ep-spec-drift/references/method.md` restates the requirement-to-code mapping from `ep-review/references/dimensions.md` (spec-conformance section), adapted to whole specs. It is duplicated deliberately: skills install folder by folder, and the drift check needs extra states (partial, untested) that the review dimension doesn't have.
- Alternative: point at `ep-review`'s file. Rejected because it breaks when only `ep-spec-drift` is installed.

### D2. Summary blocks

Every skill ends with one block in the existing `ep-review-summary` style: an HTML comment, one `key: value` per line, `outcome` first.

```
<!-- ep-protect-summary
outcome: pass | gaps | unknown
branch: <default branch>
gaps: <comma-separated baseline item ids, or none>
applied: yes | no
-->

<!-- ep-deps-summary
outcome: triaged | none
security=<n> low=<n> attention=<n> hold=<n>
handed_off: <comma-separated PR numbers, or none>
-->

<!-- ep-spec-drift-summary
outcome: clean | drift | not_applicable
capabilities: <n>
implemented=<n> partial=<n> missing=<n> untested=<n> hotspots=<n>
issue: <url or none>
-->

<!-- ep-pr-digest-summary
scope: repo:<owner/name> | all
ready=<n> ci=<n> me=<n> others=<n> stale=<n>
-->
```

Baseline item ids for `ep-protect`: `reviews`, `checks`, `no_force_push`, `no_deletion`, `conversations`. A later babysit preflight can then gate on `outcome` and on `reviews` being absent from `gaps`.

### D3. ep-protect: reading the effective protection

- Classic protection: `gh api repos/{o}/{r}/branches/{b}/protection` (404 means none; 403 means no permission).
- Rulesets: `gh api repos/{o}/{r}/rules/branches/{b}` returns the *effective* rules from every active ruleset (repository and visible organization rulesets), and `gh api repos/{o}/{r}/rulesets` gives their names for the report.
- An item is met if either source enforces it. Where both set a value (for example, the review count), the report shows the stricter one, because GitHub enforces the strictest.
- Expected check names come from `gh api repos/{o}/{r}/commits/{b}/check-runs` over the last ~10 default-branch commits, plus the latest merged PR's checks, deduplicated. A required check that appears in none of them is flagged as one that never reports (spec: Status checks match CI).

### D4. ep-protect: tighten by adding a ruleset, not by rewriting

The classic `PUT .../branches/{b}/protection` endpoint replaces the whole configuration, so building that payload is exactly where an existing setting could be dropped. Rulesets are additive: GitHub applies the most restrictive rule across classic protection and all rulesets.

1. **Preferred:** create or update one ruleset named `ep-protect baseline` (`POST` or `PUT repos/{o}/{r}/rulesets[/{id}]`) that targets `~DEFAULT_BRANCH` and holds only the missing items: `pull_request` (approvals at 1, or the existing stricter value; `required_review_thread_resolution: true`), `required_status_checks` (the user-selected check names), `non_fast_forward`, `deletion`. Bypass actors are left empty. If the ruleset already exists, its current rules are merged in and never removed.
2. **Fallback**, when rulesets are unavailable (a 403 or 404 that indicates the plan doesn't support them on private repos): use classic `PUT` with a payload built by reading the current protection and changing only the gap fields. The skill diffs the payload against the current settings, and that diff is shown alongside the request.

Either way, the exact method, endpoint, and JSON body are printed before asking. The confirmation must answer that specific request, and any edit to the selection means showing it again.
- Alternative: always use classic protection. Rejected because a rewrite risks dropping settings, and rulesets are GitHub's current mechanism.

### D5. ep-deps: discovery and risk

- Discovery: `gh pr list --author app/dependabot` and `--author app/renovate` (and their `[bot]` logins), with `--json number,title,body,labels,headRefName,statusCheckRollup,files`.
- Package and versions are parsed from the title or body (both bots use a stable "Bump X from A to B" or "Update X to B" form). Grouped bot PRs are split into one entry per package.
- Runtime vs development is read from the changed manifest section (for example `devDependencies`, `[dev-dependencies]`, `group :development`). If it can't be determined, the dependency is treated as runtime.
- Release notes: the PR body (both bots embed them), then `gh release view` on the upstream repo when one is linked. Evidence is quoted, never summarized from memory.
- Security: the `security` label, GHSA/CVE ids in the body, or (if the token allows) `gh api repos/{o}/{r}/dependabot/alerts?state=open` matched by package.
- Rubric (in `references/risk.md`): low = patch or minor, notes found and non-breaking, checks green, or a dev-only dependency at patch or minor. High = major bump, breaking notes, or notes unavailable for a runtime dependency. Medium = everything else. A failing check raises the class to at least medium.

Handoff runs `ep-babysit-pr <n>` sequentially per selected PR (or, with subagents, one subagent per PR running that skill). `ep-deps` itself has no merge path at all.

### D6. ep-spec-drift: method

```
  main specs --> per capability: requirements + scenarios
                    |
                    v
          locate implementation (search names, flags, commands from the text)
                    |
                    v
          status: implemented | partial | missing | untested
                    |
                    v
          verify non-implemented statuses (search for contrary evidence)
                    |
                    v
          hotspots: visible behavior with no requirement
```

"Untested" follows the target repo's conventions: test files that exercise the code, or, for instruction-only repos like this one, an explicit verification artifact. When a repository has no tests at all, the report says so once, instead of marking every scenario untested without comment.

### D7. Subagent path next to the sequential fallback

| Skill | With subagents | Without subagents |
|---|---|---|
| ep-protect | none needed (a few API calls) | same |
| ep-deps | one subagent per PR gathers notes and classifies; the main agent groups | triage each PR in turn |
| ep-deps handoff | one subagent per selected PR runs `ep-babysit-pr` | babysit selected PRs one after another |
| ep-spec-drift | one subagent per capability maps statuses; one verifier pass per capability | capabilities in sequence, then verify inline |
| ep-pr-digest | none needed | same |

### D8. ep-pr-digest: queries and state

- Repo scope: `gh pr list --search "is:open author:@me"` and `--search "is:open review-requested:@me"`.
- `--all`: `gh search prs --author @me --state open` and `gh search prs --review-requested @me --state open`, then `gh pr view <url> --json reviewDecision,mergeStateStatus,statusCheckRollup,updatedAt,latestReviews,commits` for each result.
- Buckets are assigned with the first-match order from the spec. "Waiting on me" for authored PRs compares the latest reviewer comment or review time with the user's latest push or comment.
- State for change markers lives in `${XDG_CACHE_HOME:-~/.cache}/ep-pr-digest/<scope>.json`: PR id to bucket, from the last run. Without a writable cache (for example a cloud scheduled run), change markers are skipped and the digest says so.
- Recurrence: when the user asks for it and the host has a loop or schedule feature (in Claude Code, `/loop` or `/schedule`), the skill sets it up with the same `ep-pr-digest` arguments. Otherwise it runs once.

### D9. Gates for outward actions

| Action | Skill | Gate |
|---|---|---|
| Create or update ruleset / classic protection | ep-protect | exact request shown, then explicit yes to that request; never in `--check` or non-interactive runs; never removes or lowers a setting |
| Start `ep-babysit-pr` on a PR | ep-deps | user selects PRs after the report; never in non-interactive runs |
| Comment on or close a dependency PR | ep-deps | user names the PR and the action; comment text shown first |
| Create an issue | ep-spec-drift | `--issue` given, title and body shown, explicit yes; never in non-interactive runs |
| Any write | ep-pr-digest | none allowed |

Everything posted carries no model or tool attribution. Bodies are passed with `--body-file` or `-F` from a file the skill wrote.

## Risks / Trade-offs

- [`ep-protect` locks the owner out of their own workflow, for example a required check that never runs] → only checks that have actually reported are proposed; the user selects them; the never-reports flag covers existing protection too.
- [Rulesets and classic protection overlap, so later edits to classic protection seem to have no effect] → the report names which source enforces each item; the ruleset has a fixed, recognizable name.
- [The token cannot see organization rulesets, so the audit is incomplete] → effective-rules endpoint first; any 403 marks the audit `unknown` rather than `gaps` or `pass`.
- [Risk classification is wrong and a breaking update gets babysat] → it is a recommendation only; handoff needs user selection; `ep-babysit-pr` still requires green checks, review rounds, and its score.
- [Drift check reports false "missing"] → verification pass looks for contrary evidence; statuses cite locations so the user can check.
- [Spec-drift cost on large repos] → scope selection by capability; parallel per capability where available.
- [Digest misbuckets PRs because GitHub's review state is ambiguous] → read-only, so the cost is a wrong suggestion, not a wrong action; the digest shows the reason for each bucket.
- [`gh search` rate limits with `--all`] → one search per role, then per-PR views; on a rate-limit error the digest reports partial results and says so.

## Open Questions

- Exact default for the stale threshold (7 days chosen). It can be tuned after use without changing the specs' shape.
