# Plan reference

Where to find a project's commands, how to write each plan item, which commands never run,
and what to probe per project type. Read in step 2 (discover) and step 3 (plan); use the
probe and edge-input sections again in step 6.

## Discovery sources

Read these from the target (the repository root, or the path target and the root files
that configure it, such as a workspace manifest or root CI workflow). Read manifests,
runners, CI, and docs; the source tree only where a doc or script points into it.

| Kind | Files |
|---|---|
| Manifests | `package.json`, `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `Cargo.toml`, `go.mod`, `Gemfile`, `pom.xml`, `build.gradle`, `build.gradle.kts`, `composer.json`, `*.csproj`, `*.sln` |
| Lockfiles | `package-lock.json`, `npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lock`, `bun.lockb`, `uv.lock`, `poetry.lock`, `Pipfile.lock`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`, `packages.lock.json` |
| Task runners | `Makefile`, `justfile`, `Taskfile.yml`, package `scripts`, `tox.ini`, `noxfile.py`, `[tool.*]` script tables in `pyproject.toml`, `Rakefile` |
| CI workflows | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `.circleci/config.yml`: the `run:` steps of test, lint, and build jobs |
| Containers | `Dockerfile`, `docker-compose*.yml`, `compose*.yml`: the start command, exposed ports, required env, and backing services |
| Docs | `README*`, `CONTRIBUTING*`, `docs/`: setup steps, commands, flags, env variables, examples |
| Example env | `.env.example`, `.env.sample`, `.env.template`: variable names only; never quote values from a real `.env` |
| OpenSpec | only when `openspec/` exists at the root: `openspec/specs/*/spec.md` scenarios are expected behavior. Skip `openspec/changes/`, which describes behavior not built yet. Without an OpenSpec root, leave OpenSpec out of the plan, report, and output |

Classify the project type from what you found: **CLI** (a `bin` entry, `[project.scripts]`,
`console_scripts`, a `main` package with flag parsing), **HTTP server or web app** (a
start or dev script that listens on a port, a web framework dependency, an exposed port),
**library** (a package with no entry point), or several. The type picks the probes below.

Also collect the **expected behavior**: every documented command, flag, env variable,
example, and (with OpenSpec) spec scenario, each with its file and line. Step 7 checks
each against what the run showed.

Also list the **env variables the app requires**: from the example env file, the
container files, and the entry point the docs or start script name (reads such as
`os.environ["X"]`, `process.env.X`, `os.Getenv("X")`, `ENV.fetch("X")` with no default).
Plan the documented start command as written. When it needs variables no doc or example
env file names, also plan a **placeholder start** after it that sets each of those to a
harmless placeholder (`X=qa-placeholder`, never a real secret), so the probes can run;
the probes depend on that item. The placeholder start runs only after the documented
start is stopped (its stop item, "Running") and its port is free (checked, not
assumed); the two starts never run at the same time. **Credentials win over
placeholders** ("Never-run list", Credentials): a variable whose name looks like a
credential is never filled with a placeholder; when the start requires any such
variable, plan no placeholder start, and mark the start and its probes
`not covered: needs credential <NAME>`. This list only shapes the plan;
whether a variable is a finding follows "Undocumented env variables" in
`references/audit.md`.

## Plan item shape

```
id:        P<n>, numbered in plan order
area:      setup | build | lint | types | tests | runtime | docs
command:   the exact command, from the directory it runs in; or the probe (input, request, expected)
source:    file:line it came from (README.md:42, package.json:9, .github/workflows/ci.yml:31)
decision:  run | skip if toolchain unchanged: unchanged since <sha> | not covered: <reason>
```

Version items (`node --version`, `./gradlew --version`, ...) open the plan, one per
toolchain the other items use (`references/record.md`, "Toolchain versions").

Order the plan by phase: setup, build, lint, types, tests, run (start the app), probes,
docs. Prefer the command as the docs or CI write it; when the docs and CI disagree, plan
the docs command and note the CI one in the source.

Set `not covered` when:

- the command is on the never-run list below (reason: what it does, for example
  `never run (deploys)`);
- its tool is missing: check with `command -v <tool>` before planning it as `run`
  (reason: `<tool> not installed`);
- it needs a service the audit cannot run locally (reason: the service and where the
  project expects it).

When the project defines no command for setup, build, checks, tests, or running, the plan
says so in one line, the audit continues with docs checks only, and each missing kind is
listed under "Not covered".

A plan item later blocked by a failed setup or build item becomes
`not covered: blocked by P<n>`.

When the project has a test command, add one item after the probes: area `tests`,
command `run proposed regression tests in a scratch copy` (under the system temp dir,
`references/audit.md`, "Regression test proposals"), source: the test command's source.
It runs in step 8, never in the repository's working tree, and only with the confirmed
plan.

## Showing the plan

Print the plan as a numbered list: id, area, exact command, source, and decision. Put the
`not covered` items after the runnable ones. Say that an item marked
`skip if toolchain unchanged` runs when a version item shows a changed toolchain, so
confirming covers it. Flag an install without a lockfile as
"may change dependency resolution". Then ask once whether to run it; the user may drop
items by id. `--yes` is confirmation of the plan as built. When the agent cannot ask and
`--yes` was not given, run no project command: every runnable item becomes
`not covered: not confirmed`, and steps 2, 3, and 7 run by reading only.

Reading files, `git` read commands, `command -v`, and `--url` `GET`/`HEAD` requests are
not project code and need no confirmation. Running a toolchain, package manager, or
wrapper is project code, a `--version` check included: it is a version item and runs only
once confirmed.

## Dependency installs

Install only with the project's lockfile-respecting command, into the project:

| Ecosystem | Lockfile | Command |
|---|---|---|
| npm | `package-lock.json` / `npm-shrinkwrap.json` | `npm ci` |
| pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
| Yarn (Berry) | `yarn.lock` | `yarn install --immutable` (Yarn 1: `yarn install --frozen-lockfile`) |
| Bun | `bun.lock` (Bun 1.2+, text) / `bun.lockb` | `bun install --frozen-lockfile` |
| pip | `requirements*.txt` (pinned) | `python -m venv .venv` then `.venv/bin/pip install -r requirements.txt` |
| uv | `uv.lock` | `uv sync --frozen` |
| Poetry | `poetry.lock` | `POETRY_VIRTUALENVS_IN_PROJECT=true poetry install` (installs the project too, so a src layout imports) |
| Pipenv | `Pipfile.lock` | `PIPENV_VENV_IN_PROJECT=1 pipenv sync` |
| Bundler | `Gemfile.lock` | `bundle install` (lockfile present) |
| Cargo | `Cargo.lock` | `cargo build --locked` |
| Go | `go.sum` | `go mod download` |
| Composer | `composer.lock` | `composer install` |
| .NET | `packages.lock.json` | `dotnet restore --locked-mode` |

Without a lockfile, plan the documented install command and flag it in the plan as "may
change dependency resolution", so the user decides. Python installs go into a
project-local `.venv`, never the system or user site: Poetry and Pipenv create their
environments outside the project unless the variables in the table tell them otherwise,
and uv uses `.venv` by default. Run the project's later Python commands through that
environment (`.venv/bin/<tool>`, `poetry run`, `pipenv run`, `uv run`).

## Never-run list

Never planned as `run`, with or without `--yes`. List each under "Not covered" with its
reason. Match by script name and by what the script body runs.

- **Deploy, publish, release, push, tag, upload:** `deploy`, `publish`, `release`,
  `npm publish`, `twine upload`, `cargo publish`, `gem push`, `docker push`, `git push`,
  `git tag`, `terraform apply`, `pulumi up`, `kubectl apply`, `helm install`/`upgrade`,
  `serverless deploy`, `vercel`, `netlify deploy`, `fly deploy`, and similar.
- **Non-local data:** database migrations or seeds whose target is not local (a
  connection string or env value pointing to a non-local host), and any `drop` or `reset`
  of a database, local or not.
- **Credentials:** commands that need secrets from the environment (cloud CLIs, API keys,
  tokens) that a local example env file does not provide. A variable is credential-like
  when its name matches `*KEY`, `*TOKEN`, `*SECRET`, `*PASSWORD`, `*PASSWD`, or
  `*CREDENTIALS`, case-insensitive (`PAYMENT_API_KEY`, `github_token`). This rule wins
  over the placeholder start ("Discovery sources", placeholder start): no placeholder
  start is planned for such a variable, and the start and its probes are reported
  `not covered: needs credential <NAME>`.
- **Deleting outside build and cache output:** `rm -rf` of anything other than the
  project's build or cache directories, `git clean`, `git reset`, `git checkout -- .`.
- **Global or system installs:** `npm i -g`, `pip install` outside a project `.venv`,
  `pipx install`, `cargo install`, `go install`, `sudo`, `brew`, `apt`, `apt-get`, `dnf`,
  `choco`, `winget`, and installing any tool the project does not declare.

A task-runner target that calls a never-run command (a `make check` that ends in
`deploy`) is never-run as a whole.

## Running

- Run items one at a time, in plan order, from the main context. Never run two at once:
  they fight over ports, caches, databases, and build output.
- Each command gets a 10-minute timeout (`timeout 600 <cmd>` where available). A timeout
  is a failed item with the timeout as evidence.
- Record exit code, duration, and the decisive output lines (the first error, the failing
  assertion, the summary line).
- **Servers:** before starting, check the documented port is free (`ss -ltn`, `lsof -i`,
  or a refused connection). When another process already listens on it, do not start
  and do not probe that port: the start is `failed: environment (port <n> in use by
  <process>)` and its probes are `not covered: blocked by P<n>`, never a finding
  (`references/audit.md`, Verification). Otherwise start in the background in its own
  session and process group (`setsid` where available), record the PID and session id,
  and poll the documented port or health route for up to 2 minutes. The app is ready
  when the port answers and either the started process is still running (a foreground
  start) or it exited 0 (a **detached start**: `docker compose up -d`, `pm2 start`, a
  script that daemonizes with `nohup ... &`). The port was free before this start, so a
  later answer comes from what this run launched. When the started process exits
  non-zero during the wait (for example `Address already in use`), the start failed,
  whatever the port answers. Not ready by then: a failed item, with the last
  output lines as evidence.
- **Start window:** a start stays up until its own runtime work is done, so nothing that
  needs it runs against a stopped server. In plan order: the start, its probes, then its
  **verification**: each candidate those probes raised (a surprise, a failed probe, output
  contradicting the docs) is re-run alone and classified there, by the rules of
  `SKILL.md` step 8 and "Verification" in `references/audit.md`; then each re-check item
  whose reproduction needs this start (`references/record.md`, "Earlier findings").
  Only then its stop item. A server is never restarted for verification, except once for
  a crash (below): a candidate or re-check item that needs a start whose stop already ran
  is not re-run (re-check: `not re-checked`). Everything that needs no server is verified
  in step 8.
- **Crash in a window:** when the started process dies during its window (or, for a
  detached start, the port stops answering), the crash is itself a candidate, with the
  probe sent just before it and the process exit code or last log lines as evidence. The
  window's remaining items are not sent to the dead port: each becomes `not covered:
  blocked by crash (P<n>)` (a re-check item: `not re-checked`), unless the re-start below
  runs it. Run the window's stop item as usual. To verify the crash, re-run the same
  confirmed start command once (it is already in the confirmed plan, so this is not an
  unplanned command): check the port is free, start and wait for readiness as above, send
  the crashing probe alone. It crashes again: reproduced, with that probe alone as the
  steps. It does not: in the same re-start, replay the window's earlier probes in their
  original order, then the crashing probe; a crash now is reproduced, with that whole
  sequence as the steps (the crash depends on state the earlier probes left). No crash
  either way: flaky, with both runs as evidence, and the blocked items run in this second
  window. Then run the same stop item.
  Never more than that one re-start per window; a crash in it blocks the rest the same
  way.
- **Stop items:** plan each start's stop right after that start's window (its probes and
  their verification, above), area `runtime`,
  source the start's source, and run it also when the start or a later step fails: for a
  foreground start, `kill -- -<pgid>` of the recorded process group; for a detached
  start, the matching stop command, `docker compose down` (with the same `-f`/`-p`
  options as the start, never `-v`) for `docker compose up -d`, `pm2 delete <name>` for
  `pm2 start` (the names it started), and for a daemonizing script the processes still in
  the recorded session (`ps -o pid= -s <sid>`, which `nohup ... &` children keep) plus
  the process listening on the port, each stopped with its process group. Find that
  listener with `lsof -t -iTCP:<n> -sTCP:LISTEN`, else `ss -ltnp 'sport = :<n>'` (Linux,
  the `pid=` field), else `fuser <n>/tcp`. When no tool can name it and the port still
  answers, never claim it was freed: the stop item fails with `environment (port <n>
  still held, listener not found)`, the report lists the leftover port and any recorded
  PID still running under "Not covered" (`references/audit.md`), and the final message
  tells the user what is still running. When `docker compose ps -a -q` (or `pm2 jlist`)
  already listed containers (or processes of that name) before the start, stop with
  `docker compose stop` (or `pm2 stop <name>`) instead, so what existed before stays.
  **PM2 daemon:** before the run's first `pm2` command (the pm2 version item included),
  record whether a PM2 daemon already runs, without starting one: `pm2 jlist`, and even
  `pm2 --version`, spawn the daemon, so check its pid file instead (`$PM2_HOME/pm2.pid`,
  default `~/.pm2/pm2.pid`, and that PID is alive; a pid file whose PID is dead means no
  daemon). At the `pm2 start`, use that record: run `pm2 jlist` only when a daemon ran
  before. When no daemon ran before, this run launched it:
  the stop also runs `pm2 kill`. Confirm the port is free afterwards, by the same check
  as before the start. When no daemon ran before and any `pm2` command ran (the version
  item alone spawns one), step 9's cleanup runs `pm2 kill` at the end, even when no
  `pm2 start` ran or its stop did not run.
- **One server at a time:** each start of the same app is its own start item with its own
  stop item: the documented start, the placeholder start, each missing-config start
  ("Probes per project type", Local HTTP server), and each re-check item whose
  reproduction is itself a start of the app (`references/record.md`, "Earlier
  findings"). Order them: the documented start, its
  probes and their verification, its stop; then each later start, its probes and their
  verification, its stop, one after another. A
  later start runs only after the previous start's stop item ran and its port is
  confirmed free; two starts of the app never run at the same time.

## Probes per project type

Each probe is a plan item with area `runtime` (or `docs` when it checks a documented
example). A surprise (crash, stack trace, 5xx, wrong exit code, output that contradicts the
docs or a spec scenario) is a candidate for step 8.

**CLI**

- `--help` (and `-h`, and the bare command when the docs show it).
- Each documented example, exactly as written.
- Each documented flag at least once.
- The edge inputs below, as arguments and on stdin where the tool reads stdin.
- A missing config file, when the tool reads one.
- Check the exit code: 0 on success, non-zero on error, and an error message that names
  the problem.

**Action-route filter** (local apps and `--url`)

A route can change state outside the app whatever its method: a
`GET /api/cron/send-digest` still sends real email, fires webhooks, or schedules jobs,
on a locally started app too. A documented route **fails the filter** when its path or
doc text names an action: `send`, `run`, `trigger`, `cron`, `job`, `task`, `queue`,
`webhook`, `hook`, `callback`, `sync`, `import`, `refresh`, `notify`, `email`, `mail`,
`digest`, `invoke`, `execute`, `exec`, `create`, `new`, `add`, `update`, `edit`,
`delete`, `remove`, `reset`, `purge`, `clear`, `flush`, `approve`, `cancel`, `confirm`,
`verify`, `unsubscribe`, `subscribe`, `login`, `logout`, `auth`, `token`, `deploy`,
`publish`, `restart`, `shutdown`, `migrate`, `seed`, `admin`, and the like; or when its
docs say it changes, sends, schedules, or notifies anything outside the app. Any doubt
means it fails. A route that fails gets no request at all, with any method or body,
malformed or not. The sections below say how each target lists it under "Not covered".

**Local HTTP server** (started by the audit)

- Each documented route that passes the "Action-route filter" above, with the
  documented method. A route that fails it is not requested and goes under "Not
  covered" as `not probed: may change state (<METHOD> <route>)`.
- A missing route (expect 404, not 500).
- Malformed bodies on documented write routes that pass the filter: invalid JSON, wrong
  types, missing required fields, the edge inputs below.
- Start with a required env variable or config missing (one variable at a time), when the
  docs or example env file name them, to see whether the failure is clear. Each is a
  separate start item with its own stop item, after the previous start's stop
  ("Running", One server at a time).
- Write requests go only to this locally started app.

**Library**

- Each code example from the README, run in a scratch directory outside the repository
  (under the system temp dir), importing the project from its checkout or the local
  install.
- The public functions the examples use, with the edge inputs below.

**`--url` (an app already running elsewhere)**

- `GET` and `HEAD` only, to that URL and paths under it: the root, a missing route, and
  each documented route that is **clearly read-only**.
- That app is not one this run started, so a documented route is probed only when all
  hold; any doubt means it is not probed:
  - it passes the "Action-route filter" above;
  - the docs give it as `GET` or `HEAD` (or name no method for a page), never another
    method;
  - it needs no token, signature, or id parameter.
  A documented route left out goes under "Not covered" as
  `not probed on --url: may change state (<METHOD> <route>)`.
- No forms, no sign-in, no other method, no request bodies, and no query strings beyond
  the ones a probed route's docs show. Flows that need writes go under "Not covered".

## Edge inputs

Use the ones that fit each input the project takes:

| Kind | Inputs |
|---|---|
| Empty | empty string, no arguments, empty stdin, empty file, `{}` and `[]` bodies |
| Invalid | wrong type (text for a number), negative and zero numbers, malformed JSON, unknown flag, unknown enum value, path that does not exist |
| Very large | a 1 MB string, a 100 000-line file, a number past 2^63, a deeply nested JSON body (1 000 levels) |
| Unicode | `naïve café`, `日本語`, emoji `👩🏽‍💻`, right-to-left `مرحبا`, a combining mark `é`, a NUL byte where text is accepted |
| Missing config | config file absent, required env variable unset, config file present but empty |

Keep large inputs in files under the system temp dir, and delete them at the end.
