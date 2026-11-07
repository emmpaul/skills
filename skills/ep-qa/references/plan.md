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
| Lockfiles | `package-lock.json`, `npm-shrinkwrap.json`, `pnpm-lock.yaml`, `yarn.lock`, `bun.lockb`, `uv.lock`, `poetry.lock`, `Pipfile.lock`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock`, `packages.lock.json` |
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
start's process and its process group are stopped and its port is free (checked, not
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
decision:  run | not covered: <reason>
```

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
`not covered` items after the runnable ones. Flag an install without a lockfile as
"may change dependency resolution". Then ask once whether to run it; the user may drop
items by id. `--yes` is confirmation of the plan as built. When the agent cannot ask and
`--yes` was not given, run no project command: every runnable item becomes
`not covered: not confirmed`, and steps 2, 3, and 7 run by reading only.

Reading files, `git` read commands, `command -v`, and `--url` `GET`/`HEAD` requests are
not project code and need no confirmation.

## Dependency installs

Install only with the project's lockfile-respecting command, into the project:

| Ecosystem | Lockfile | Command |
|---|---|---|
| npm | `package-lock.json` / `npm-shrinkwrap.json` | `npm ci` |
| pnpm | `pnpm-lock.yaml` | `pnpm install --frozen-lockfile` |
| Yarn (Berry) | `yarn.lock` | `yarn install --immutable` (Yarn 1: `yarn install --frozen-lockfile`) |
| Bun | `bun.lockb` | `bun install --frozen-lockfile` |
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
- **Servers:** start in the background in their own process group (`setsid` where
  available), record the PID, and poll the documented port or health route for up to
  2 minutes. Not ready by then: a failed item, with the last output lines as evidence.
  Stop every process you started, with its process group, before the run ends, also when
  a later step fails. Confirm the port is free afterwards.
- **One server at a time:** before any later start of the same app (the placeholder
  start), stop the earlier start's process group and confirm its port is free.

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

**Local HTTP server** (started by the audit)

- Each documented route, with the documented method.
- A missing route (expect 404, not 500).
- Malformed bodies on documented write routes: invalid JSON, wrong types, missing
  required fields, the edge inputs below.
- Start with a required env variable or config missing (one variable at a time), when the
  docs or example env file name them, to see whether the failure is clear.
- Write requests go only to this locally started app.

**Library**

- Each code example from the README, run in a scratch directory outside the repository
  (under the system temp dir), importing the project from its checkout or the local
  install.
- The public functions the examples use, with the edge inputs below.

**`--url` (an app already running elsewhere)**

- `GET` and `HEAD` only, to that URL and paths under it: the root, each documented route,
  and a missing route.
- No forms, no sign-in, no other method, no request bodies. Flows that need writes go
  under "Not covered".

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
