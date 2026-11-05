# Review dimensions

Each dimension reviews the same diff and returns candidate findings in the shape below.
Only report what the diff introduces or touches; pre-existing issues in untouched code are
out of scope unless the diff makes them reachable.

## Finding shape

```
dimension:  correctness | spec | tests | security
severity:   critical | major | minor
file:       path/relative/to/repo
line:       line number in the new version (or the old one for deletions)
summary:    one sentence stating the defect
scenario:   concrete inputs or state -> wrong output, crash, leak, or missing behavior
evidence:   the code, spec text, or command output that shows it
```

A finding without a concrete scenario is not a finding. "Could be cleaner" is not a
finding for any of these dimensions.

## Severity scale

| Severity | Meaning | Examples |
|---|---|---|
| critical | Breaks core behavior, loses or corrupts data, or is exploitable. Must block merge. | crash on common input, data deletion, auth bypass, secret committed, required spec behavior missing entirely |
| major | Wrong behavior in a realistic case, or a spec requirement only partly implemented. Should block merge. | wrong result on an edge case users will hit, unhandled error path, scenario contradicted by code, changed behavior with no test |
| minor | Real but low-impact defect. Fix or explicitly waive. | misleading error message, missing test for a rare path, small spec wording drift |

## Correctness

- [ ] Logic does what the change intends: conditions, operators, off-by-one, inverted checks
- [ ] Edge inputs: empty, null/undefined, zero, negative, very large, unicode, duplicates
- [ ] Error paths: failures are handled, propagated, or reported; no swallowed errors that hide bugs
- [ ] State and lifecycle: initialization order, cleanup, resource leaks, idempotency on retry
- [ ] Concurrency: races, shared mutable state, missing awaits, ordering assumptions
- [ ] Contracts: callers of changed functions still get what they expect (signatures, return types, nullability, units)
- [ ] Data changes: migrations reversible or safe, no silent truncation or type coercion
- [ ] Removed code: nothing still depends on what was deleted or renamed

## Spec conformance

Applies only when the repository has an OpenSpec root and the target relates to an active
change. Otherwise report this dimension as **not applicable** and produce no findings.

Inputs: every `openspec/changes/<change>/specs/**/spec.md` delta, plus `proposal.md` and
`tasks.md` for intent.

Build a mapping table (working notes; include it under the spec section of the report only
when it has gaps), one row per requirement and per scenario:

```
requirement / scenario         | implemented at          | tested at
-------------------------------+-------------------------+------------------
Req: Preconditions checked     | src/pr.ts:40-62         | test/pr.test.ts:12
  Scen: On default branch      | src/pr.ts:44            | -
```

Then check:

- [ ] **Missing**: each ADDED or MODIFIED requirement has an implementation in the diff (or
      already in the codebase). A requirement with none is a finding naming the requirement
      (critical if core to the change, otherwise major).
- [ ] **Contradicted**: no code path behaves opposite to a scenario's THEN clause (major).
- [ ] **Unspecified**: externally visible behavior the diff adds (new flags, endpoints,
      outputs, side effects, defaults) that no requirement describes is reported as
      out-of-spec (major if it has outward effects, otherwise minor).
- [ ] **Untested**: each scenario has a test exercising it; a scenario with none is a
      finding (minor, or major for scenarios guarding destructive or outward actions).
      For repos whose artifacts are not code (e.g. prompt files), "tested" means a
      documented verification step covers it.
- [ ] **REMOVED requirements**: the behavior is actually gone.
- [ ] **Tasks**: ticked tasks in `tasks.md` are really done in the diff (a ticked task with no
      implementation is major).

Report status `passed` when there are no verified critical or major spec findings,
otherwise `failed`.

## Tests

- [ ] Changed or added behavior has tests that would fail without the change
- [ ] Tests assert outcomes, not just that code runs (no assertion-free tests)
- [ ] Bug fixes include a regression test for the reported case
- [ ] Edge and error paths named under Correctness are covered where they matter
- [ ] No tests deleted, skipped, or weakened to make the suite pass
- [ ] Tests are deterministic: no reliance on time, ordering, network, or shared state
- [ ] If the repo has a test command, run it on the target when feasible and include failures as evidence

## Security

- [ ] Injection: shell, SQL, path, template, or HTML built from untrusted input without escaping or parameters
- [ ] Secrets: keys, tokens, passwords, or private URLs committed or logged
- [ ] AuthN/AuthZ: new entry points check identity and permissions; no privilege widening
- [ ] Input validation at trust boundaries (size, type, path traversal, deserialization)
- [ ] Unsafe defaults: debug on, permissive CORS, world-readable files, TLS verification off
- [ ] Dependencies: newly added packages are expected, pinned as the repo does, not typosquats
- [ ] Destructive or outward actions (delete, push, publish, network calls) are gated as intended
- [ ] Sensitive data in error messages, logs, or telemetry
