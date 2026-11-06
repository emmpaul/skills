## ADDED Requirements

### Requirement: Structured user questions
When the driving session asks the user a question with fixed options, the skill SHALL use the host's structured question tool (`AskUserQuestion` in Claude Code) when one is available. Without such a tool, it SHALL ask in plain text with the same options numbered and wait for the reply; an open question with no options is asked in plain text. The skill SHALL act only on an answer that maps to one option or gives the requested input, and ask again otherwise.

#### Scenario: Gate pause with a question tool
- **WHEN** the gate pauses (score below 85 without `--yes`, or a hard-to-undo element) and the host offers a structured question tool
- **THEN** the skill prints the score report, then asks through the tool with the options approve, revise, and stop, and makes no code change before the answer

#### Scenario: Gate pause without a question tool
- **WHEN** the gate pauses and the host has no structured question tool
- **THEN** the skill asks in plain text with the options approve, revise, and stop numbered, and waits for the reply

#### Scenario: Name collides with an existing change
- **WHEN** the derived name matches an existing change and the host offers a structured question tool
- **THEN** the skill asks through the tool with the options to continue that change or use a different name

#### Scenario: Work branch already exists
- **WHEN** the skill would create `<type>/<change>` and that branch already exists
- **THEN** it asks, through the tool when available, whether to continue on the existing branch or stop, and creates no branch before the answer

#### Scenario: Plan needs input
- **WHEN** the plan phase ends with `blocker: needs input`
- **THEN** the skill asks the planner's question, through the tool when available and the blocker names 2 to 4 options, otherwise in plain text, and re-runs the plan phase with the answer

#### Scenario: Large change offered as a stack
- **WHEN** the change is large and `ep-stack` and `ep-babysit-pr` are available
- **THEN** the skill asks, through the tool when available, whether to deliver it as a stack or keep the reviewed local branch, and pushes nothing before the answer

#### Scenario: Answer outside the options
- **WHEN** the user answers with free text that matches none of the options
- **THEN** the skill does not guess: it acts on the text only when it clearly picks one option or gives the requested input (such as a new change name), and otherwise asks again

### Requirement: Questions only from the driving session
Only the driving session SHALL ask the user questions. Phase workers SHALL NOT call the question tool or wait for the user; a phase that needs an answer SHALL end with a blocker naming the question, and the driving session SHALL ask it. Questions that another skill asks under its own rules (such as `ep-stack`'s plan approval) SHALL stay with that skill.

#### Scenario: Phase subagent needs an answer
- **WHEN** a phase running in a subagent finds a choice it cannot make
- **THEN** it ends with a blocker naming the question, and the driving session asks the user

#### Scenario: Agent without subagents
- **WHEN** the host has no subagents and the skill runs the phases inline
- **THEN** questions are still asked only at the driving session's question points, through the question tool when available, and never mid-phase

#### Scenario: Interrupted at a gate question
- **WHEN** the session ends while the gate question is unanswered
- **THEN** the state file already records `decision: paused`, and the next run asks the same question again
