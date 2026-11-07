# Workflow path (`--workflow`)

Read this only when the user passed `--workflow` and the host is Claude Code with a
Workflow tool, at each end-of-run review round (`SKILL.md` step 8.1). The user's
`--workflow` is the opt-in. Group passes, plan, apply, and every fix phase never run as a
Workflow; without the Workflow tool, say so and use the subagent or inline path.

Run the round's step 1 as one Workflow that follows `briefs.md#review-fallback` with the
round's base, `since`, and `known`, except that steps 4 and 7 run as agents:

1. Before the agents, do its steps 1 to 3 (`REVIEW.md` from the default branch, the diff
   with `## Skip` paths removed, `scope`, spec input).
2. A `pipeline` over the four dimension agents yields candidates. Each gets its
   checklist from step 4, the `REVIEW.md` guidance and skipped paths, the change name,
   the base and head shas, and for round *k* > 1 the `since` sha. Deduplicate the
   candidates and drop new ones that duplicate a known location (step 6).
3. Those candidates, plus the known locations for round *k* > 1, go to a `parallel`
   stage of 3 voter agents. Each voter gets every candidate, tries to disprove each one,
   and sees no other voter's verdicts; above 20 candidates it takes them in batches of
   20, adding no agents. That is at most 7 agents (4 dimensions and 3 voters).
4. Keep a candidate when at least 2 of its 3 verdicts are not `refuted`, at the highest
   severity that 2 non-refuting verdicts support, as `ep-review` votes. A known location
   is `fixed` when 2 verdicts say its defect no longer occurs.
5. Then set origin, apply the minor cap, and compute `risk`, `risk_reasons`, `scope`, and
   the `known` counts as in steps 7 to 10, and build the `finding:` and `pre-existing:`
   lines and the `ep-review-summary` from the result, with `verification: vote`.

The round's fix phase stays one subagent. The Workflow is done when it has produced the
round's `finding:` and `pre-existing:` lines and its `ep-review-summary`.
