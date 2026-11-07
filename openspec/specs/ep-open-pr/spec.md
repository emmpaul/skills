# ep-open-pr Specification

## Purpose

Creates a GitHub pull request for the current branch with a title and body built from its commits and, when present, the active OpenSpec change, without model attribution.

## Requirements

### Requirement: Preconditions checked before opening
The skill SHALL verify the branch is not the default branch, has commits ahead of the base, and has no open PR already, before creating a PR.

#### Scenario: On default branch
- **WHEN** the current branch is the repository's default branch
- **THEN** the skill stops and asks the user to create or switch to a feature branch

#### Scenario: PR already exists
- **WHEN** an open PR already exists for the branch
- **THEN** the skill reports its URL and offers to update its body instead of creating a duplicate

#### Scenario: Uncommitted changes
- **WHEN** the working tree has uncommitted changes
- **THEN** the skill offers to run `ep-commit` first, or proceeds with committed work only if the user declines

### Requirement: Push before opening
The skill SHALL push the branch to the remote with upstream tracking if it is not yet pushed or is ahead of its upstream, and SHALL NOT force-push.

#### Scenario: Unpushed branch
- **WHEN** the branch has no upstream
- **THEN** the skill pushes it with upstream tracking and then opens the PR

### Requirement: Title and body from commits
The PR title SHALL summarize the change in Conventional Commit style and the body SHALL summarize the commits, list notable changes, and include a Testing section that states what was actually run and its result, or says plainly that nothing was run, followed by steps to test.

#### Scenario: Body content
- **WHEN** the skill opens a PR for a branch with several commits
- **THEN** the body includes a summary, a list of changes, and a Testing section

#### Scenario: Tests were run
- **WHEN** the session ran the repo's test command on the branch head and it passed
- **THEN** the Testing section names the command, the head sha it ran on, and the result

#### Scenario: Nothing was run
- **WHEN** there is no record of a test, build, or check having run on the branch
- **THEN** the Testing section says "Not run" and does not claim any result

### Requirement: Reversibility classification
The PR body SHALL classify the change as a one-way door (some effect remains after a revert, such as data migrations, public interface changes, releases, external side effects, or security changes) or a two-way door (fully undoable by reverting), with a one-sentence reason, SHALL state how to revert it, and for a one-way door SHALL list each irreversible element with a mitigation.

#### Scenario: Two-way door
- **WHEN** the branch only refactors internal code and adds tests
- **THEN** the body has a Reversibility section marking it a two-way door with a reason and a "How to revert" line naming `git revert` of the merge commit

#### Scenario: One-way door
- **WHEN** the branch adds a migration that drops a database column
- **THEN** the body marks it a one-way door, lists the column drop, gives a mitigation, states what a revert does and does not undo, and the final report mentions the classification

#### Scenario: Uncertain classification
- **WHEN** the skill cannot tell whether an effect is reversible
- **THEN** it classifies the PR as a one-way door and states what is uncertain

### Requirement: OpenSpec-aware body
When the branch relates to an active OpenSpec change, the PR body SHALL include the change name, a summary of the proposal's Why, the capabilities touched, and task progress (done/total).

#### Scenario: Active change
- **WHEN** the branch implements active change `add-auth` with 5 of 8 tasks done
- **THEN** the body names `add-auth`, summarizes its Why, lists its capabilities, and shows `5/8 tasks`

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the body is built from commits only and does not mention OpenSpec

### Requirement: No model attribution in PR
The PR title and body SHALL NOT contain model or tool attribution, such as "Generated with" footers.

#### Scenario: Host default footer
- **WHEN** the host agent's defaults would add a "Generated with" footer
- **THEN** the created PR body contains no such footer

### Requirement: Draft and base options
The skill SHALL support opening the PR as a draft and targeting a non-default base branch on request, and SHALL report the PR URL after creation.

#### Scenario: Draft requested
- **WHEN** the user asks for a draft PR
- **THEN** the PR is created as a draft and its URL is reported

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents.

#### Scenario: Agent without subagents
- **WHEN** the host agent has no subagent capability
- **THEN** the skill gathers context and opens the PR sequentially with the same result

### Requirement: Risk section
The PR body SHALL include a Risk section giving the change's risk tier (low, medium, or high) and its reasons, using the same risk rules as `ep-review`, including any `REVIEW.md` risk paths in the repository.

#### Scenario: Workflow file changed
- **WHEN** the branch changes `.github/workflows/ci.yml`
- **THEN** the Risk section says `high` and names that path as the reason

#### Scenario: Ordinary change
- **WHEN** the branch changes application code that no rule marks as low or high risk
- **THEN** the Risk section says `medium` with the reason "ordinary change"

### Requirement: UI screenshots
When the branch changes UI files, the skill SHALL capture screenshots of the affected pages from the running app at the branch head, publish them on the `ep-pr-assets` branch, and link them in a Screenshots section of the PR body. With `--no-screenshots`, or when no UI file changed, it SHALL skip this step and add no Screenshots section.

#### Scenario: UI component changed
- **WHEN** the branch changes `src/components/Button.tsx` and the repo has a `dev` script
- **THEN** after confirmation the skill starts the app, screenshots the pages that render the change, stops the app, and the PR body has a Screenshots section with one image per page at each capture width (desktop and mobile, at most 5 pages and 10 images)

#### Scenario: No UI change
- **WHEN** the branch changes only server code and tests
- **THEN** no app is started and the body has no Screenshots section

#### Scenario: Opted out
- **WHEN** the user passes `--no-screenshots` on a branch that changes UI files
- **THEN** no app is started, nothing is pushed to `ep-pr-assets`, and the body has no Screenshots section

### Requirement: Screenshot capture uses only available tools
The skill SHALL capture with a browser the host already provides, or with a browser automation tool already installed in the project. It SHALL NOT install any tool, SHALL NOT sign in or enter credentials, and SHALL stop every process it started.

#### Scenario: No browser available
- **WHEN** the host has no browser tool and the project has no browser automation installed
- **THEN** nothing is started or pushed, and the Screenshots section says "Not captured: no browser available"

#### Scenario: Page needs a login
- **WHEN** an affected page redirects to a sign-in page
- **THEN** that page is not captured and the Screenshots section names it with "Not captured: needs sign-in"

#### Scenario: App does not start
- **WHEN** the dev command exits or no port answers within the timeout
- **THEN** the skill stops the process, opens the PR anyway, and the Screenshots section says "Not captured: app did not start" with the last lines of its output

#### Scenario: Cleanup
- **WHEN** capture finishes or fails
- **THEN** no process the skill started is still running and its port is free

### Requirement: Screenshot publishing is gated
Before starting the app, and again before pushing to `ep-pr-assets`, the skill SHALL show what it will run or push and wait for confirmation, unless `--screenshots` pre-approved both. It SHALL push with a plain push only, SHALL commit only image files under a folder for this branch head, and SHALL never change the PR branch or the default branch for screenshots.

#### Scenario: First use
- **WHEN** the remote has no `ep-pr-assets` branch and the user confirms the push
- **THEN** the skill creates it as an orphan branch holding only the screenshot folder and pushes it without force

#### Scenario: Push declined
- **WHEN** the user declines the screenshot push
- **THEN** the PR is opened without pushing images, and the Screenshots section lists the local file paths

#### Scenario: PR updated after new commits
- **WHEN** the skill updates an existing PR's body after new commits that change UI files
- **THEN** it captures screenshots for the new head into a new folder, and the body links the new images

#### Scenario: No attribution
- **WHEN** the skill commits screenshots to `ep-pr-assets`
- **THEN** the commit message has no model or tool attribution
