# Proposal

## Why

No `ep-*` skill checks accessibility. `ep-review` covers correctness, spec conformance, tests, and security, so UI changes can merge with missing labels, keyboard traps, or focus that gets hidden, and nothing flags them. An agent that audits from memory cites WCAG loosely: it gets numbers wrong, invents criteria, or misses 2.2 additions such as 2.4.11 Focus Not Obscured and 2.5.8 Target Size. Its knowledge also goes stale when W3C publishes errata or a new version. The skill needs WCAG references it can cite exactly, and the maintainer needs a way to refresh them from W3C with one command instead of editing many files by hand.

## What Changes

- Add a new skill, `ep-a11y` (new behavior), under `skills/ep-a11y/`:
  - Audits UI code against WCAG 2.2. The default is Level AA (A and AA criteria), and `--level A|AA|AAA` changes it. The target can be the uncommitted diff, a branch, a GitHub PR, or explicit paths.
  - Reports only verified findings. Each one cites a success criterion by number, name, and level, and gives a location, a severity, a concrete scenario showing which users are blocked and how, and a fix. The report also lists the criteria that code cannot settle as "needs manual check", and never claims that the code conforms.
  - `--fix` applies fixes for verified findings to the working tree. It makes no commits.
  - `--comment` (PR targets only) posts the report as one PR comment, with no attribution.
  - Ends with a machine-readable `ep-a11y-summary` block that other skills can read.
- WCAG references bundled in the skill folder, split by who maintains them:
  - **Generated** (`references/wcag/`): an index, plus one file per success criterion with its normative text, level, the versions that include it, links to the Understanding document, and sufficient techniques and failures. A manifest records the source URL, the WCAG version, the fetch date, the source hash, and per-file hashes.
  - **Hand-written** (`references/checks.md`): agent guidance on how to detect and fix each criterion in code, keyed by criterion number. The generator never touches it.
- New maintainer script at the repo root, `scripts/wcag.py`, with three modes:
  - `update` fetches W3C's official `wcag.json` and regenerates `references/wcag/`.
  - `update --dry-run` reports what changed upstream without writing anything.
  - `check` runs offline. It fails when a generated file was edited by hand, when the index and the files disagree, or when `checks.md` cites a criterion that does not exist or is obsolete.
- `ep-a11y` ships its own synced copy of `scripts/context.sh` (through the existing `scripts/sync-shared.sh`). `shared/context.sh` does not change.
- README: add `ep-a11y` to the skills table and install commands, and document the WCAG update procedure under Development.

**Outward effects on GitHub:** `ep-a11y` posts one PR comment, and only when `--comment` is passed with a PR target. Without `--comment` it makes no GitHub writes. It never pushes, commits, or merges.

## Capabilities

### New Capabilities
- `ep-a11y`: WCAG accessibility audit of UI changes, with verified, criterion-cited findings, optional fixes and PR comment, and bundled WCAG references that are regenerated from W3C's source and checked for drift.

### Modified Capabilities
None. `ep-review` and the other skills keep their current requirements.

## Impact

- New files: `skills/ep-a11y/SKILL.md`, `skills/ep-a11y/scripts/context.sh` (a synced copy), `skills/ep-a11y/references/checks.md`, `skills/ep-a11y/references/wcag/**` (generated: about 87 criterion files, an index, and a manifest), and `scripts/wcag.py`.
- Modified: `README.md`, and `.github/workflows/check.yml`, which gains `python3 scripts/wcag.py check` and the generator's unit tests (`scripts/test_wcag.py`, with a small fixture under `scripts/fixtures/`).
- Unchanged: `shared/context.sh` and every existing skill.
- Runtime (skill): `git`, plus `gh` for PR targets and `--comment`. No network access, and no a11y tooling is installed. If the target project already has an accessibility test command, the skill may run it.
- Maintainer tooling: `python3` (standard library only). `update` needs network access to `www.w3.org`; `check` runs offline.
- Local effects: `--fix` edits files in the working tree.
