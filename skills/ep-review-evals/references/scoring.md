# Scoring reference

How `run` picks cases, reads each review, scores recall and noise, and saves the run, and
how `compare` decides between two runs. Read in `run` and `compare`, always.

## Picking cases

Without `--limit`, every case in `<dir>/cases.json` runs. With `--limit <n>`, take
`ceil(n/2)` incident cases and `floor(n/2)` clean cases, each in file order; when one
kind has too few, fill the rest from the other kind. The run records the ids it ran
(`cases`), so a limited run is never mistaken for a full one.

## Reading a review

Each case's review is `ep-review`'s report and its `ep-review-summary` block. From it
take:

- the summary's `verified:` counts (introduced findings only: `ep-review` excludes
  pre-existing ones), `pre_existing:`, `verification:`, and `head:`;
- every finding of the four dimension sections as
  `{dimension, severity, origin: introduced, file, line, instances, summary}`, and every
  finding of the `### pre-existing` section with `origin: pre-existing`. A finding with
  no `file:line` (for example a missing spec requirement) has `file: null`.

A case whose review did not end with a summary block, whose `head:` differs from the
case's head, or that failed for any other reason is `status: failed` with a one-line
reason; it is kept in the run file and left out of recall and noise.

## Hit rule

An incident case is a **hit** when at least one verified **introduced** finding has a
location (its `file:line` or one of its `instances`) in the bug's file, with a line
within 3 lines of the bug's range: `start - 3 <= line <= end + 3`. For a bug at
`src/a.ts:40-44`, a finding at `src/a.ts:46` is a hit; one at `src/a.ts:48`, or at
`src/b.ts:42`, is not. Pre-existing findings never count as hits: the bug was introduced
by the case's PR, so a reviewer that calls it pre-existing missed its origin.

**Recall** = hits / incident cases that ran (`status: ok`). With no incident case, recall
is `n/a`.

## Noise rule

**Noise** = verified critical and major findings on clean cases / clean cases that ran,
using the summary's `verified:` counts (`critical + major`, so pre-existing findings
and minor findings do not count). With no clean case, noise is `n/a`. Lower is better: a
clean PR caused no incident, so a blocking finding on it is most likely noise.

Print both as a value with its parts: `recall: 0.50 (1/2)`, `noise: 0.50 (1/2)`, two
decimals.

## Reviewer version

The version of the `ep-review` that ran: its skill folder (the one the host loads as
`ep-review`; when unsure, the `ep-review` folder next to this skill's folder).

- When the folder is inside a git checkout: `git -C <folder> rev-parse HEAD`, plus
  `+<hash>` when `git -C <folder> status --porcelain -- .` is not empty, where `<hash>`
  is the content hash below (so uncommitted reviewer edits give a new version).
- Otherwise the content hash alone: the first 12 hex digits of
  `cat <folder>/SKILL.md <folder>/references/* | sha256sum` (files in sorted order).

## Run file

`<dir>/runs/<YYYYMMDD-HHMMSS>-<label>.json`, where the label is `--label <label>`
(letters, digits, `.`, `_`, `-`; default `run`). The time is the run's start, in UTC.
Each run gets a new file: when the name exists, add `-2`, `-3`, ... before `.json`.

```json
{
  "tool": "ep-review-evals",
  "version": 1,
  "label": "voting",
  "time": "<ISO 8601 start time, UTC>",
  "finished": "<ISO 8601 end time, UTC>",
  "reviewer_version": "<sha | sha+hash | hash>",
  "verification": "vote | inline | mixed",
  "cases": ["i1", "c1"],
  "limit": 2,
  "recall": {"hits": 1, "incidents": 1, "value": 1.0},
  "noise": {"findings": 0, "clean": 1, "value": 0.0},
  "results": [
    {
      "id": "i1",
      "kind": "incident",
      "head": "<sha>",
      "status": "ok",
      "hit": true,
      "verified": {"critical": 0, "major": 1, "minor": 0},
      "pre_existing": 0,
      "verification": "vote",
      "findings": [
        {"dimension": "correctness", "severity": "major", "origin": "introduced",
         "file": "src/a.ts", "line": 46, "instances": [], "summary": "<summary>"}
      ]
    },
    {
      "id": "c1", "kind": "clean", "head": "<sha>", "status": "failed: <reason>",
      "hit": null, "verified": null, "pre_existing": null, "verification": null,
      "findings": []
    }
  ]
}
```

`limit` is `null` without `--limit`. `hit` is `null` for clean and failed cases. The
run's `verification` is `vote` or `inline` when every case that ran used it, and `mixed`
otherwise. `value` is `null` where the rule above gives `n/a`. Write it with 2-space
indentation, through a temporary file in the same folder renamed over it, and leave it
uncommitted.

## Compare

`compare <a> <b>` reads two run files (paths, or file names under `<dir>/runs/`). It is
read-only.

1. **Shared cases.** The cases with `status: ok` in both runs, matched by id and head.
   When either run has cases the other lacks (or failed), compare only on the shared
   ones and say so: `compared on <n> shared cases (<a>: <n> cases, <b>: <n> cases)`.
   With no shared incident and no shared clean case, the verdict is `drop` with the
   reason `no shared cases`.
2. **Recompute** recall and noise for each run over the shared cases only, with the
   rules above (from each result's `hit` and `verified`), never from the stored totals.
3. **Verdict:**
   - `keep` when `b` has higher recall and noise no higher than `a`'s, or the same
     recall and lower noise;
   - `drop` otherwise (lower recall, higher noise, or no change).

   A `n/a` value on both sides counts as equal; on one side only, the verdict is `drop`
   with the reason `not comparable`.
4. **Print** a two-column table (`a`, `b`) with label, reviewer version, time, recall,
   and noise, then the verdict with one line naming what decided it, for example
   `drop: recall 0.50 -> 1.00, but noise 0.00 -> 0.50`. When the two reviewer versions
   are the same, say so: the difference is run-to-run variance, not a reviewer change.
