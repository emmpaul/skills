# Audit reference

Finding shape, severity scale, verification checklist, and the default manual-check list.
Criterion names and levels always come from `wcag/index.md`. The maintainer's check
confirms that every criterion number in this file exists, is not obsolete, and that a name
written after it matches the index.

## Finding shape

Every candidate, from any principle pass or from the project's own a11y test, uses this
shape:

```
criterion:  <num> <name> (<level>)        exactly as in wcag/index.md
principle:  perceivable | operable | understandable | robust
severity:   critical | major | minor
file:       path/relative/to/repo
line:       line in the current version of the file
summary:    one sentence stating the barrier
scenario:   who is affected and what blocks them, step by step
evidence:   the markup, component, or CSS that shows it (quote it)
fix:        the concrete change, as code when it is short
decision:   none | wording | colour | design     (what the fix needs from a human)
```

A finding with no concrete scenario is not a finding. "Could be more accessible" is not a
finding. Scope is what the target adds or touches; for a path target it is the whole file.
Pre-existing issues in untouched code are out of scope unless the change makes them
reachable.

Write the scenario in terms of people and tasks, for example: "A screen reader user tabs
to the search field and hears 'edit text, blank'; they cannot tell what to type."

## Severity by impact

Severity follows what the barrier does to people, never the criterion's level. A Level AA
criterion can produce a critical finding, and a Level A criterion can produce a minor one.

| Severity | Meaning | Examples |
|---|---|---|
| critical | Some users cannot complete the task. | keyboard trap (SC 2.1.2); control that cannot be reached or operated by keyboard (SC 2.1.1); form field or icon-only button with no accessible name (SC 4.1.2, SC 1.1.1); focus moved to a removed or hidden element so focus is lost (SC 2.4.3); focus indicator removed with no replacement on a primary control (SC 2.4.7) |
| major | The task is possible but significantly harder, or assistive technology gets wrong information. | wrong role or missing state such as `aria-expanded` (SC 4.1.2); error shown only in colour or not tied to the field (SC 3.3.1, SC 1.4.1); focused element hidden behind a sticky header (SC 2.4.11); status update not announced (SC 4.1.3); visible label not in the accessible name (SC 2.5.3) |
| minor | Real but low impact, or partial. | verbose or redundant alt text (SC 1.1.1); missing `autocomplete` token on a rarely used field (SC 1.3.5); heading level skipped with structure otherwise intact (SC 1.3.1) |

When one root cause breaks several criteria, report it once and mention the others in the
evidence. Pick the criterion by the capability that is missing:

| Missing capability | Cite |
|---|---|
| reaching or operating the control by keyboard | 2.1.1 Keyboard |
| accessible name, role, or state of a control (icon-only buttons included) | 4.1.2 Name, Role, Value |
| text alternative for an image or graphic that is not a control | 1.1.1 Non-text Content |
| visible label or instructions for a field that already has a name | 3.3.2 Labels or Instructions |
| visible focus indicator | 2.4.7 Focus Visible |

## Verification checklist

Try to disprove each candidate before keeping it. Drop it if any of these hold:

- [ ] **Name supplied elsewhere.** The accessible name comes from `aria-label`,
      `aria-labelledby`, a wrapping `<label>`, `<label for>`, `title` (as last resort),
      `alt`, visually hidden text (`sr-only`, `visually-hidden`), or text content. A
      `placeholder` is a fallback name too: a field named only by its placeholder is not
      a 4.1.2 finding; judge it under SC 3.3.2 (see `checks.md`).
- [ ] **Wrapper or design-system component.** The element is rendered by a component that
      adds the name, role, keyboard handling, or focus style. Open the component's source
      (or its typed props and defaults) and check before reporting. A prop that is
      required by the component's types counts as supplied only where callers pass it.
- [ ] **Hidden from assistive technology on purpose.** The element or an ancestor has
      `aria-hidden="true"`, `hidden`, `inert`, `display: none`, or `role="presentation"`
      / `role="none"` and is decorative.
- [ ] **Decorative use.** Images with `alt=""`, icons next to visible text, and CSS
      backgrounds that carry no information need no text alternative.
- [ ] **Native element.** A native `<button>`, `<a href>`, `<input>`, `<select>`, or
      `<summary>` already provides keyboard support and role; do not ask for `tabindex`
      or `role` on it.
- [ ] **Handled elsewhere in CSS.** An `outline: none` is replaced by `:focus-visible`
      styles, a `box-shadow` ring, or a border change in the same or a global stylesheet.
- [ ] **Code cannot settle it.** If the result depends on rendered colours, layout, real
      content, or runtime behaviour, move the item to "Needs manual check" instead of
      reporting it.

Then check the citation:

- [ ] The criterion number is a row in `wcag/index.md` and is not obsolete. If not, cite
      the right row or drop the finding. Parsing (obsolete in WCAG 2.2) is never cited:
      do not report markup validity issues (duplicate IDs, unclosed tags) on their own;
      report them only through the
      criterion they break, for example a duplicate `id` that breaks a label association
      under SC 1.3.1 or SC 4.1.2.
- [ ] The level is within the requested level (default A and AA).
- [ ] The criterion's `sc/` file was opened and its normative text supports the finding,
      including any exceptions it lists.

## Needs manual check

Code reading cannot settle these. List the ones that are in scope for the requested level
and relevant to the audited files (skip media items when there is no media, and so on),
each with one line saying what to check in the running UI.

| Criterion | What to check |
|---|---|
| SC 1.2.2 Captions (Prerecorded) | captions exist and match the audio |
| SC 1.2.5 Audio Description (Prerecorded) | video has audio description where visuals carry meaning |
| SC 1.3.2 Meaningful Sequence | reading order after CSS layout (grid, flex `order`, absolute positioning) matches the visual order |
| SC 1.3.3 Sensory Characteristics | instructions do not rely only on shape, position, or sound |
| SC 1.3.4 Orientation | the view works in portrait and landscape |
| SC 1.4.3 Contrast (Minimum) | rendered text contrast is at least 4.5:1 (3:1 for large text), including hover, focus, disabled-looking and placeholder states |
| SC 1.4.4 Resize Text | at 200% browser zoom no text is clipped or overlapping |
| SC 1.4.10 Reflow | at 320 CSS px width there is no two-direction scrolling |
| SC 1.4.11 Non-text Contrast | control borders, focus rings, and meaningful icons reach 3:1 |
| SC 1.4.12 Text Spacing | with the text-spacing bookmarklet applied nothing is cut off |
| SC 2.2.2 Pause, Stop, Hide | moving or auto-updating content can be paused |
| SC 2.3.1 Three Flashes or Below Threshold | nothing flashes more than three times a second |
| SC 2.4.3 Focus Order | tabbing through the page follows a logical order, including in dialogs |
| SC 2.4.11 Focus Not Obscured (Minimum) | focused elements are not fully hidden by sticky headers, footers, or banners |
| SC 2.5.8 Target Size (Minimum) | rendered targets are at least 24 by 24 CSS px or have enough spacing |
| SC 3.2.3 Consistent Navigation | navigation repeated across pages keeps the same order |
| SC 3.2.4 Consistent Identification | the same function has the same label across pages |
| SC 3.3.8 Accessible Authentication (Minimum) | login does not require a cognitive test without an alternative (paste and password managers work) |

At `--level AAA` also consider:

| Criterion | What to check |
|---|---|
| SC 1.4.6 Contrast (Enhanced) | rendered text contrast is at least 7:1 (4.5:1 for large text) |
| SC 2.4.13 Focus Appearance | the focus indicator is at least a 2 CSS px perimeter with 3:1 change |
| SC 3.1.5 Reading Level | text needs no more than lower secondary reading ability, or a simpler version exists |

## No conformance claim

A code audit cannot show that a page conforms to WCAG. Never write "conformant",
"compliant", "passes WCAG", or "meets AA". With no findings, write: "No issues found in the
audited code at WCAG 2.2 <level>. The manual checks below still need a person."
