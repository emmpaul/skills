# Workflow path (Claude Code, high effort)

Read this when running in Claude Code with a Workflow tool available and the user asked
for high effort (`--effort high`, "thorough", "deep review"). Running this skill at that
effort is the user's opt-in to a Workflow.

Run steps 4-5 as one Workflow: a `pipeline` over the four dimension agents, whose
deduplicated candidates (plus any known findings) go to a `parallel` stage of the 3 voter
agents that SKILL.md step 5 describes, then combine the verdicts with its voting rules.
That is **at most 7 agents** (4 dimensions and 3 voters); voters batch by 20 instead of
adding agents. The summary records `verification: vote`.

With no Workflow tool, use the subagent path in SKILL.md steps 4-5.
