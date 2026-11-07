# ep-commit-and-push Specification

## Purpose
Turns the current working-tree changes into one or more well-scoped Conventional Commits that match the repository's style, reference the active OpenSpec change when one exists, never carry model attribution, and then push the branch to its own name on the remote with a plain push unless the caller asks for commits only.

## Requirements

### Requirement: Gather repository context before committing
The skill SHALL collect branch, upstream, staged and unstaged diff, recent commit history, and OpenSpec state before proposing any commit.

#### Scenario: Context collected
- **WHEN** the user invokes `ep-commit-and-push` in a git repository with changes
- **THEN** the skill reads the diff, the last commits on the branch, the upstream state, and the OpenSpec state before drafting messages

#### Scenario: Nothing to commit
- **WHEN** the working tree has no staged, unstaged, or untracked changes
- **THEN** the skill reports that there is nothing to commit, makes no commit, and pushes nothing, even when the branch has unpushed commits

### Requirement: Split changes into logical commits
The skill SHALL group changes into one or more commits, each covering a single coherent purpose, and SHALL present the planned grouping, with the push it will make, before creating commits.

#### Scenario: Mixed changes
- **WHEN** the diff contains unrelated changes (for example a bug fix and a docs edit)
- **THEN** the skill proposes separate commits for each and shows the files or hunks in each

#### Scenario: Staged-only intent
- **WHEN** the user has staged a subset of changes and asks to commit only staged changes
- **THEN** the skill commits only the staged changes and leaves unstaged changes untouched

#### Scenario: Plan names the push
- **WHEN** the skill presents its commit plan and `--no-push` is not in effect
- **THEN** the plan names the branch and remote it will push to and the number of commits that push sends, counting earlier unpushed commits

### Requirement: Conventional Commit messages matching repo style
Each commit message SHALL use Conventional Commits format (`type(scope): subject`) and SHALL follow observable conventions in recent history such as subject length and casing.

#### Scenario: Message format
- **WHEN** the skill creates a commit
- **THEN** the subject has the form `type(scope): subject` with a type from the Conventional Commits set

#### Scenario: Body explains why
- **WHEN** the reason for a change is not evident from the subject
- **THEN** the commit body explains why the change was made

### Requirement: No model attribution
Commit messages SHALL NOT contain model or tool attribution, including `Co-Authored-By` trailers naming an AI model and "Generated with" footers.

#### Scenario: Host agent injects attribution
- **WHEN** the host agent's defaults would append a `Co-Authored-By` trailer for a model
- **THEN** the created commit contains no such trailer

#### Scenario: Attribution removed before the push
- **WHEN** a created commit carries an attribution line
- **THEN** the skill rewrites that message while the commit is still unpushed, and pushes only after every created message is free of attribution

### Requirement: OpenSpec-aware scope
When the repository has exactly one active OpenSpec change that the diff relates to, the skill SHALL use the change name as the commit scope and SHALL offer to mark `tasks.md` items completed by the diff.

#### Scenario: Active change
- **WHEN** an active change `add-auth` exists and the diff implements its task 2.1
- **THEN** the commit scope is `add-auth` and the skill offers to tick task 2.1

#### Scenario: Multiple active changes
- **WHEN** several active changes exist
- **THEN** the skill picks the change the diff touches, or asks the user when ambiguous

#### Scenario: Repository without OpenSpec
- **WHEN** the repository has no OpenSpec root
- **THEN** the skill derives scope from the changed paths and makes no mention of OpenSpec

### Requirement: Never rewrite published history
The skill SHALL NOT amend, rebase, or otherwise rewrite commits that exist on the remote.

#### Scenario: Pushed commit
- **WHEN** the last commit is already on the upstream branch
- **THEN** the skill creates a new commit rather than amending

### Requirement: Push after committing
After it has created and verified its commits, the skill SHALL push the current branch to the same-named branch on its push remote, its target: `git push -u <remote> HEAD:refs/heads/<branch>` without an upstream, and `git push <remote> HEAD:refs/heads/<branch>` when the upstream has the branch's name. It SHALL push only when it created a commit in this run, and SHALL confirm the push with `git ls-remote`.

#### Scenario: Branch without upstream
- **WHEN** the skill has committed on a branch with no upstream and `origin` exists
- **THEN** it runs `git push -u origin HEAD:refs/heads/<branch>` and reports the remote branch it pushed to

#### Scenario: Branch with upstream
- **WHEN** the skill has committed on a branch whose upstream has the branch's name
- **THEN** it runs `git push <remote> HEAD:refs/heads/<branch>` and reports the commits pushed

### Requirement: Push remote is picked as git picks it
The skill SHALL take the push remote from `branch.<branch>.pushRemote`, else `remote.pushDefault`, else `branch.<branch>.remote`, else `origin`, and SHALL count it only when `git remote` lists it; otherwise it SHALL push nothing.

#### Scenario: Push remote configured
- **WHEN** `remote.pushDefault` is `fork`, the branch `feat` tracks `upstream/feat`, and both remotes exist
- **THEN** it runs `git push fork HEAD:refs/heads/feat`, and `upstream` is unchanged

#### Scenario: Single-branch clone
- **WHEN** the clone fetches only `main`, so the pushed branch has no remote-tracking ref
- **THEN** the skill confirms the push from `git ls-remote <remote> refs/heads/<branch>` and reports the remote branch it pushed to

#### Scenario: Upstream named differently
- **WHEN** the skill has committed on a branch whose upstream has another name (for example `fix` made with `git switch -c fix origin/main`)
- **THEN** it asks whether to push the branch under its own name, even when told to just commit; on a yes it runs `git push -u <remote> HEAD:refs/heads/<branch>`, creating that remote branch and pointing the upstream at it, and on a no it keeps the commits local; it never pushes to the upstream's branch

#### Scenario: No remote to push to
- **WHEN** the push remote is not a remote `git remote` lists (for example no `origin` exists, or the upstream is a local branch, remote `.`)
- **THEN** the skill keeps the commits, pushes nothing, and reports that no remote was found

### Requirement: Plain pushes only
The skill SHALL push with a plain push only: never `--force`, `--force-with-lease`, or a `+refspec`, and never `--no-verify` unless the user asks. Every push SHALL name its target with the explicit refspec `HEAD:refs/heads/<branch>`, so git configuration (`push.default`, a remote's push refspecs) cannot add branches or a force. When the push is rejected or a pre-push hook fails, it SHALL stop, keep the commits local, and report the cause.

#### Scenario: Configuration would widen the push
- **WHEN** `push.default` is `matching` with an unpushed local `main`, or the remote has a `+refs/heads/*:refs/heads/*` push refspec, and the skill pushes from `feature`
- **THEN** only `feature` is pushed, and no other remote branch changes

#### Scenario: Remote has new commits
- **WHEN** the push is rejected because the remote branch has commits the local branch lacks
- **THEN** the skill does not pull, rebase, or force-push; it reports the rejection, keeps the commits, and suggests bringing the remote changes in (for example with `ep-sync`) before pushing again

#### Scenario: Pre-push hook fails
- **WHEN** a pre-push hook rejects the push
- **THEN** the skill reports the hook output, keeps the commits local, and does not retry with `--no-verify`

### Requirement: Default branch push is gated
When the push target is the push remote's default branch, or that default branch is unknown, the skill SHALL ask before pushing, even when it was told to just commit, and SHALL push nothing unless the user confirms.

#### Scenario: Committing on the default branch
- **WHEN** the skill has committed on `main`, the default branch, without `--no-push`
- **THEN** it asks whether to push `main` and, if the user declines, reports the commits as local

#### Scenario: Default branch unknown
- **WHEN** the repository has no `origin/HEAD` and `gh` reports no default branch, so the default branch is guessed or not found
- **THEN** the skill asks before pushing, whatever the branch, and on a no reports the commits as local

### Requirement: Default branch is confirmed with GitHub
When `gh` is authenticated, the skill SHALL take the push remote's default branch from `gh repo view <remote URL> --json defaultBranchRef` and SHALL treat it as unknown when that differs from the local `<remote>/HEAD`. Without an answer from `gh`, the default branch is unknown for a push remote other than `origin`; for `origin` the local `origin/HEAD` stands, and the default branch is unknown when none is found or it is only guessed.

#### Scenario: Stale local default branch
- **WHEN** `origin/HEAD` points at `master` but `gh` reports `main` as the default branch
- **THEN** the skill treats the default branch as unknown and asks before pushing, whatever the branch

#### Scenario: Other push remote unconfirmed
- **WHEN** the push remote is `fork` and `gh` gives no default branch for it
- **THEN** the skill treats the default branch as unknown and asks before pushing

### Requirement: Secret-like files are staged only on a yes
A file new to history (untracked, listed with `git status --porcelain --untracked-files=all`, or staged added, from `git diff --cached --name-only --diff-filter=A`) whose name is secret-like SHALL be committed only after the user says yes to it by name, even when told to just commit. Until then the skill SHALL keep it out of every commit (untracked stays untracked, staged is unstaged) and list it in the plan and the report.

#### Scenario: Untracked env file
- **WHEN** the working tree has an un-ignored, untracked `.env.local` beside other changes and the user says to just commit
- **THEN** the skill commits and pushes the other changes, leaves `.env.local` untracked, and lists it in the plan and the report as left out

#### Scenario: Staged env file
- **WHEN** the user staged a never-committed `.env.local` and says to just commit
- **THEN** the skill unstages it, commits and pushes the other changes, and lists `.env.local` as left out

#### Scenario: Secret inside a new directory
- **WHEN** a new untracked directory `deploy/` holds `prod.pem` and other files
- **THEN** the skill commits the other files of `deploy/` and leaves `deploy/prod.pem` untracked and listed as left out

### Requirement: Secret-like names
The secret-like names SHALL be `.env*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.kdbx`, `*.tfvars`, `id_rsa*`, `id_ed25519*`, `id_ecdsa*`, `id_dsa*`, `*credentials*`, `secrets.*`, `.netrc`, `.npmrc`, and `.pypirc`, matched against the last path component.

#### Scenario: Private key
- **WHEN** an untracked `id_ed25519` sits beside other changes and the user says to just commit
- **THEN** the skill leaves `id_ed25519` untracked and lists it as left out

### Requirement: No-push mode
With `--no-push`, or when the user or a calling skill says to commit without pushing, the skill SHALL create and verify its commits as usual, push nothing, and report the commits as local.

#### Scenario: Caller keeps the branch local
- **WHEN** `ep-orchestrate` invokes the skill with `--no-push` and an intended single commit
- **THEN** the skill makes that commit, runs no `git push`, and the remote is unchanged

#### Scenario: User asks for commits only
- **WHEN** the user asks to commit but not push
- **THEN** the skill behaves as with `--no-push`

### Requirement: Works without subagents
The skill SHALL complete its full behavior in agents that cannot spawn subagents.

#### Scenario: Agent without subagents and large diff
- **WHEN** the host agent has no subagent capability and the diff is large
- **THEN** the skill analyzes the diff sequentially and still produces the commit plan
