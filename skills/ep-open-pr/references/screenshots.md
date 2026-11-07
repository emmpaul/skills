# UI screenshots

Step 5 of `SKILL.md`. It runs after the title and body are drafted and before
`gh pr create` or `gh pr edit`. It captures the pages the branch changes from the running
app at the branch head, publishes the images on the orphan `ep-pr-assets` branch, and adds
a `## Screenshots` section to the body.

Never change the PR branch or the default branch here: no commit, checkout, stash, or
reset in the working repository. Never install anything, never sign in, and never type
into a form. Capture is sequential: no subagents.

## Rules at a glance

| Situation | Result |
|---|---|
| `--no-screenshots` | Skip the whole step: nothing started or pushed, no `## Screenshots` section. |
| No UI file changed | Same as `--no-screenshots`. |
| Uncommitted changes in the working tree | Nothing started or pushed. Section: `Not captured: working tree differs from branch head`. |
| No start command | Section: `Not captured: no start command found`. |
| No browser | Nothing started or pushed. Section: `Not captured: no browser available`. |
| Gate 1 declined (Skip), or non-interactive without `--screenshots` | Nothing started. Section: `Not captured: not confirmed`. |
| Gate 1 Stop | End the whole skill before creating or editing the PR. |
| App did not start | Stop it, open the PR anyway. Section: `Not captured: app did not start`, plus its last output lines. |
| Page redirects to sign-in | That page is not captured. Section lists it with `Not captured: needs sign-in`. |
| Gate 2 declined, or push failed twice | Nothing pushed; the PR is still opened. Section lists the local paths. |

`--screenshots` pre-approves both gates. Without it, each gate is a question to the user
and waits for the answer.

## 1. UI touched?

List the changed paths: `git diff --name-only origin/<base>...HEAD`. The branch touches UI
when some path matches any of:

- anywhere: `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `*.astro`, `*.html`, `*.htm`, `*.css`,
  `*.scss`, `*.sass`, `*.less`, `*.stories.*`;
- a server-side page template under a `views/` or `templates/` directory: `*.erb`,
  `*.haml`, `*.slim`, `*.hbs`, `*.ejs`, `*.pug`, `*.njk`, `*.jinja`, `*.jinja2`, `*.twig`,
  `*.liquid`;
- a `*.js`, `*.mjs`, or `*.ts` file under a `components/`, `pages/`, `app/`, or `views/`
  directory, unless it also lies under an `api/` or `server/` directory.

A directory alone never makes a file UI: `app/models/user.rb`, `app/main.py`, and Helm's
`templates/deployment.yaml` are not UI files.

Ignore test files: a file name matching `*.test.*`, `*.spec.*`, `*_test.*`, `*_spec.*`, or
`test_*`, or a path under a `__tests__/`, `test/`, `tests/`, or `spec/` directory. A name
that merely contains `test` or `spec` (`Inspector.tsx`, `LatestPosts.tsx`) is not a test. When no path is left, skip this whole step: start nothing, push
nothing, and add no `## Screenshots` section.

The app is started from the working tree, but the images must show the branch head they
are filed under. So when `git status --porcelain` lists anything (staged, unstaged, or
untracked files, for example after the user declined to commit in `SKILL.md` step 2),
start nothing and push nothing, write `Not captured: working tree differs from branch
head`, and skip to [Body](#8-body).

## 2. Start command

Take the first that exists:

1. a `package.json` script, in this order: `dev`, `start`, `preview`, `storybook`; run it
   with the package manager the lockfile names (`pnpm-lock.yaml` → `pnpm run`,
   `yarn.lock` → `yarn`, `bun.lockb` → `bun run`, else `npm run`);
2. a command the README documents for starting the app locally (a dev or serve command,
   never a deploy, publish, or install command).

Find the port from the command or script (`--port`, `-p`, a bare port argument such as
`http.server 8000`), else the README, else the framework's default (Vite 5173, Next.js
and Create React App 3000, Astro 4321, SvelteKit 5173, Storybook 6006, `http.server`
8000). When no command is found, write `Not captured: no start command found` and skip to
[Body](#8-body).

## 3. Browser

Use the first available, in this order:

1. a host browser tool: the built-in browser, Claude in Chrome, or a Playwright MCP, when
   it can reach `localhost`;
2. Playwright already installed in the project: `node_modules/.bin/playwright` exists.
   Capture with `npx --no-install playwright screenshot`. `--no-install` makes `npx` fail
   rather than download.

Never install a browser, a Playwright package, or browser binaries (`npm install`,
`npx playwright install`, `pip install`, a system package manager). When nothing is
available, start nothing and push nothing, write `Not captured: no browser available`,
and skip to [Body](#8-body).

## 4. Pages

Derive routes from the changed files where the framework's convention makes it clear:

- Next.js: `app/<route>/page.*` → `/<route>`, `pages/<route>.*` → `/<route>`
  (`index` → `/`); route groups `(group)` drop out;
- SvelteKit: `src/routes/<route>/+page.svelte` → `/<route>`;
- Nuxt, Astro, and similar file routers: `pages/<route>.*` → `/<route>`;
- a static site: a changed `<path>.html` → `/<path>.html` (`index.html` → its folder);
- a changed story file (`*.stories.*`) with a `storybook` command: its story URL,
  `/?path=/story/<title-kebab>--<export-kebab>`.

Skip dynamic segments (`[id]`, `:id`) you cannot fill without guessing. When no route can
be derived (a changed shared component or stylesheet), use `/`. Take at most **5** pages,
in changed-file order, each at **1280×800** and **390×844**, so at most **10** images.
Pages past the cap are listed in the section as `Not captured: over the 5-page limit`.

## 5. Gate 1: run the app

Show, then ask **Run**, **Skip**, or **Stop**:

- the start command and its working directory, and the port;
- the pages and the two widths;
- the browser to use.

`--screenshots` answers Run. In a non-interactive run without `--screenshots`, answer
Skip. Skip writes `Not captured: not confirmed` and goes to [Body](#8-body). Stop ends the
skill before the PR is created or edited, and says so.

## 6. Capture

### Process lifecycle

1. Check that the port is free before starting (`ss -ltn 'sport = :<port>'`, or
   `lsof -iTCP:<port> -sTCP:LISTEN`). When something already listens there, start nothing:
   `Not captured: port <port> already in use`.
2. Start the command in the background in its own process group (and its own session
   with `setsid` where available; macOS has no `setsid`), with stdout and stderr in a
   scratch log outside the repository:

   ```bash
   log=<scratch>/ep-open-pr-app.log
   if command -v setsid >/dev/null 2>&1; then
     setsid sh -c '<command>' >"$log" 2>&1 < /dev/null &
   else   # macOS: perl ships with it; setpgrp gives the job its own process group
     perl -e 'setpgrp(0,0); exec @ARGV' sh -c '<command>' >"$log" 2>&1 < /dev/null &
   fi
   pid=$!   # either way, the process group id equals $pid
   ```

3. Poll `http://localhost:<port>/` for up to **60 s**. It is ready when the port answers
   and the process is still running. When the process exits first, or the port does not
   answer in time, stop it (below), write `Not captured: app did not start` with the last
   10 lines of `$log` in a fenced block, and go on to open the PR.
4. **Always stop it**, whether capture succeeded, failed, or was interrupted:
   `kill -TERM -- -<pid>`, wait up to 5 s, then `kill -KILL -- -<pid>` if any member is
   left (`ps -eo pid=,pgid= | awk '$2 == <pid>'`). Then check that the port is free. When it still answers,
   find the listener (`lsof -t -iTCP:<port> -sTCP:LISTEN`, else the `pid=` field of
   `ss -ltnp 'sport = :<port>'`, else `fuser <port>/tcp`) and kill its process group. If
   no tool can name it, never claim the port was freed: say in the final report what is
   still running.

### Shots

Save PNGs in a new, empty folder made for this run, outside the repository
(`shots=$(mktemp -d <scratch>/ep-open-pr-shots.XXXXXX)`), named
`<page-slug>-<width>.png` (`/` → `root`, other `/` → `-`). Never reuse a folder from an
earlier run: it would hold images gate 2 never showed.

- Host browser tool: open the page, set the viewport to the width and height, wait for
  the page to load, take the screenshot.
- Project Playwright:

  ```bash
  npx --no-install playwright screenshot --viewport-size=1280,800 \
    http://localhost:<port><route> "$shots/<page-slug>-1280.png"
  ```

  and the same with `--viewport-size=390,844`.

**Sign-in:** when a page ends on a sign-in page, do not capture it and list it as
`Not captured: needs sign-in`. It ends on one when the final URL is on another host, or
one of its path segments is exactly (ignoring case) `login`, `log-in`, `signin`,
`sign-in`, `sign_in`, `auth`, `oauth`, or `sso`, or the page shows only a sign-in form.
Match whole segments, never substrings: `/authors`, `/lessons`, and `/professors` are
ordinary pages. Never type into any field.

A page that errors (HTTP 4xx/5xx, a blank page) is captured as it is and noted
`(page returned <status>)` next to its images; it is evidence for the reviewer.

## 7. Publish (gate 2)

Skip this part when no image was captured.

Show every image path that will be pushed (exactly the files in `$shots`), the branch `ep-pr-assets`, and the target
folder, then ask **Push** or **Don't push**. `--screenshots` answers Push. Screenshots of
a local app may show local data; the list lets the user check before anything leaves the
machine. Don't push (or a non-interactive run without `--screenshots`) skips to
[Body](#8-body) with local paths.

On Push, work in a scratch worktree outside the repository, so the PR branch and the
default branch never change:

```bash
slug=<branch name, lowercased, every character outside [a-z0-9._-] replaced by ->
sha=$(git rev-parse --short HEAD)
wt=<scratch>/ep-pr-assets
git fetch origin ep-pr-assets          # fails when the branch does not exist yet
# exists:  git worktree add --detach "$wt" origin/ep-pr-assets
#          git -C "$wt" switch -c ep-pr-assets-tmp   (any local name; push names the ref)
# missing: git worktree add --detach "$wt" HEAD
#          git -C "$wt" switch --orphan ep-pr-assets-tmp
#          (an orphan switch empties the index and tree; the commit holds only images)
mkdir -p "$wt/$slug/$sha"
cp -- "$shots"/*.png "$wt/$slug/$sha/"   # only this run's images, as listed at gate 2
git -C "$wt" add -- "$slug/$sha"
msg=$(mktemp)
printf 'chore: add screenshots for %s at %s\n' "<branch>" "$sha" > "$msg"
git -C "$wt" commit -F "$msg"
rm -f "$msg"
git -C "$wt" push origin HEAD:refs/heads/ep-pr-assets
```

- The commit holds only PNG files under `<branch-slug>/<head-short-sha>/`. The message
  carries no model or tool attribution: check it with `git -C "$wt" log -1 --format=%B`.
- A plain push only: never `--force`, `--force-with-lease`, or a `+` refspec.
- A non-fast-forward rejection (someone pushed meanwhile) gets one retry: `git fetch
  origin ep-pr-assets`, `git -C "$wt" rebase origin/ep-pr-assets` (the temporary branch
  in the scratch worktree only), push again. When that fails too, fall back to local
  paths.
- **Always remove the worktree**, on success or failure: `git worktree remove --force
  "$wt"`, then `git branch -D ep-pr-assets-tmp`, then check that `git worktree list` no
  longer shows it.
- Never delete `ep-pr-assets` or anything in it. It grows over time; the user may delete
  it whenever they like.

**Updating a PR** after new commits: the head sha is new, so the images go in a new
`<branch-slug>/<new-sha>/` folder and the body links only the new ones. Older folders stay.

## 8. Body

Add `## Screenshots` right after `## Changes`. With pushed images, one line per image,
`<owner>/<repo>` from `gh repo view --json nameWithOwner --jq .nameWithOwner`:

```markdown
## Screenshots

![/ 1280](https://github.com/<owner>/<repo>/blob/ep-pr-assets/<slug>/<sha>/root-1280.png?raw=true)
![/ 390](https://github.com/<owner>/<repo>/blob/ep-pr-assets/<slug>/<sha>/root-390.png?raw=true)

- /settings: Not captured: needs sign-in
```

These blob URLs render in private repositories for viewers with access.

When nothing was pushed (gate 2 declined, or the push failed twice), list the local paths
instead and tell the reader to drag them in:

```markdown
## Screenshots

Not pushed. Drag these files into a comment:

- `<shots>/root-1280.png`
- `<shots>/root-390.png`
```

When nothing was captured, the section is the single reason line, for example
`Not captured: no browser available`. With `--no-screenshots`, or when no UI file changed,
there is no section at all.

## 9. Report

The final report lists each captured page and width, each page not captured with its
reason, and whether images were pushed to `ep-pr-assets` (the commit sha) or kept local.
