# Code checks by criterion

Hand-written guidance for detecting and fixing WCAG 2.2 issues in markup, components, and
CSS. One `## <num> <name>` section per criterion that code can check; names match
`wcag/index.md` exactly. A criterion without a section can still be audited from its
`wcag/sc/` file. Every section has three parts:

- **Look for:** patterns in the code that suggest a failure.
- **Rule out:** common false positives to check before reporting (see also the
  verification checklist in `audit.md`).
- **Fix:** the preferred change. Prefer native HTML over ARIA.

Examples use HTML and JSX; apply the same idea to Vue, Svelte, Angular, and server
templates.

## 1.1.1 Non-text Content

- **Look for:** `<img>` with no `alt`; `<svg>` or icon components used as the only content
  of a button or link with no name; `<input type="image">` with no `alt`; `<area>` with no
  `alt`; `alt` values such as file names, "image", or "icon"; a `<canvas>` that carries
  information with no fallback text.
- **Rule out:** `alt=""` on decorative images; icons with `aria-hidden="true"` next to
  visible text; icon components that render a `<title>` or accept a required `label` prop
  that callers pass; CSS background images that are decorative.
- **Fix:** add a short `alt` that serves the same purpose (`alt="Company logo"` becomes
  `alt="Acme home"` on a home link). Mark decorative images `alt=""` and decorative SVGs
  `aria-hidden="true" focusable="false"`. Needs a decision when the right wording depends
  on content the code does not show.

## 1.3.1 Info and Relationships

- **Look for:** visual headings built from styled `<div>`/`<span>`/`<b>`; lists built from
  `<div>`s with bullets in CSS; data tables without `<th>`, `scope`, or `<caption>`; layout
  tables with `<th>`; form groups (radio sets, address blocks) without `<fieldset>` and
  `<legend>` or `role="group"` with a name; inputs whose label is adjacent text not tied
  with `for`/`id` or wrapping; required state shown only by an asterisk with no
  `required`/`aria-required`; duplicate `id` values that break a `for` or
  `aria-labelledby` reference.
- **Rule out:** components that render semantic elements internally (check their
  source); `role="heading"` with `aria-level`; tables marked `role="presentation"` used for
  layout only.
- **Fix:** use `<h1>`-`<h6>`, `<ul>/<ol>/<li>`, `<th scope>`, `<fieldset><legend>`, and
  `<label for>`. Keep heading levels in order.

## 1.3.5 Identify Input Purpose

- **Look for:** inputs that collect the user's own name, email, phone, address, postal
  code, birthday, username, or password with no `autocomplete` token, or with
  `autocomplete="off"`.
- **Rule out:** fields about someone other than the user (a recipient's address);
  search fields; one-time codes, which may use `autocomplete="one-time-code"`.
- **Fix:** add the matching token: `name`, `given-name`, `email`, `tel`, `street-address`,
  `postal-code`, `bday`, `username`, `current-password`, `new-password`.

## 1.4.1 Use of Color

- **Look for:** state or meaning carried only by colour classes: error fields marked only
  with a red border, required fields only in a colour, links inside text distinguished
  only by colour (`text-decoration: none` with no other cue), chart series told apart
  only by colour, status badges with colour and no text.
- **Rule out:** a text label, icon, pattern, underline, or weight change that also carries
  the meaning; links in navigation where position makes them identifiable.
- **Fix:** add a text or icon cue (error message, "Required", underline on in-text links).
  Needs a decision when the visual design must change.

## 1.4.3 Contrast (Minimum)

- **Look for:** hard-coded colour pairs in CSS or design tokens that you can compute:
  text colour on a known background below 4.5:1 (3:1 for 18.66px bold or 24px and larger);
  light grey placeholder used as the only label; text over images with no overlay.
- **Rule out:** disabled controls, logos, and purely decorative text, which are exempt;
  pairs where the background is not known from the code.
- **Fix:** propose a darker or lighter value from the existing palette that reaches the
  ratio, and state the computed ratio. This always needs a decision (colour), so list it
  instead of applying it unless the palette already has a compliant token for the role.
  When the background cannot be known from code, put it on the manual-check list.

## 1.4.4 Resize Text

- **Look for:** font sizes in `px` on containers with fixed `height` and
  `overflow: hidden`; `vh`/`vw`-only font sizes; `maximum-scale=1` or `user-scalable=no`
  in the viewport meta.
- **Rule out:** `px` font sizes alone (browsers zoom them); fixed heights on containers
  whose content cannot grow.
- **Fix:** use `rem`/`em`, `min-height` instead of `height`, and remove zoom limits from
  the viewport meta.

## 1.4.10 Reflow

- **Look for:** fixed widths larger than 320px on main content (`width: 960px`,
  `min-width` on body or wrappers); `white-space: nowrap` on long text; no responsive
  breakpoints in a layout that uses fixed columns.
- **Rule out:** content that needs two dimensions (data tables, maps, diagrams, toolbars),
  which is exempt.
- **Fix:** use `max-width` with fluid widths, flex or grid with wrapping, and
  `overflow-wrap: anywhere` for long strings.

## 1.4.11 Non-text Contrast

- **Look for:** input borders, checkbox and radio outlines, icon-only controls, and focus
  rings whose colour against the adjacent background is known and below 3:1; custom
  controls with `border: none` and only a faint background.
- **Rule out:** inactive (disabled) components; controls whose visible text label alone
  identifies them; colours that cannot be resolved from code.
- **Fix:** propose a border or icon colour that reaches 3:1. Needs a decision (colour).

## 1.4.12 Text Spacing

- **Look for:** fixed `height` plus `overflow: hidden` on text containers; `line-height`
  or `letter-spacing` set with `!important` in a way that blocks user styles; text in
  buttons or badges clipped by fixed dimensions.
- **Rule out:** containers that grow with content.
- **Fix:** use `min-height`, let text grow instead of clipping it, and leave spacing
  overridable (no `!important` on it).

## 1.4.13 Content on Hover or Focus

- **Look for:** tooltips, popovers, and menus shown on `:hover` or `mouseenter` that close
  on `mouseleave` of the trigger (so the pointer cannot move onto them), that cannot be
  dismissed with Escape, or that disappear on a timer.
- **Rule out:** native `title` tooltips (browser-controlled); content opened by a click
  rather than hover or focus.
- **Fix:** keep the content open while the pointer is over the trigger or the content,
  close it on Escape without moving focus, and remove auto-hide timers.

## 2.1.1 Keyboard

- **Look for:** `onClick` (or `@click`, `on:click`, `(click)`) on `<div>`, `<span>`,
  `<li>`, `<img>`, or `<tr>` with no `tabindex="0"` and no key handler; `<a>` without
  `href` used as a button; handlers that act only on `mousedown`, `mouseover`, or
  `dblclick`; drag-only reordering; custom widgets (tabs, menus, sliders, comboboxes)
  without arrow, Enter, Space, and Escape handling; `tabindex="-1"` on interactive
  elements.
- **Rule out:** elements inside a native `<button>` or `<a href>` that receives the event;
  click handlers on non-focusable wrappers that only mirror an inner native control;
  components whose source adds keyboard support.
- **Fix:** use a native `<button type="button">` or `<a href>`. When a native element is
  impossible, add `role`, `tabindex="0"`, and a key handler for Enter and Space (buttons)
  or Enter (links). A keyboard-unreachable control is critical.

## 2.1.2 No Keyboard Trap

- **Look for:** modal or focus-trap code with no Escape handler and no reachable close
  button; `keydown` handlers that call `preventDefault()` on Tab unconditionally;
  embedded editors or iframes that capture Tab with no documented exit.
- **Rule out:** dialogs that trap focus on purpose and close on Escape or a focusable
  close button; focus-trap libraries configured with `escapeDeactivates`.
- **Fix:** close the dialog on Escape, keep a focusable close control, and only trap Tab
  while the dialog is open. A trap is critical.

## 2.1.4 Character Key Shortcuts

- **Look for:** global `keydown` listeners that act on a single printable key (`"s"`,
  `"/"`, `"?"`) without a modifier and without checking that focus is outside text
  inputs.
- **Rule out:** shortcuts active only while a specific component has focus; shortcuts
  that can be turned off or remapped in settings.
- **Fix:** require a modifier, scope the listener to the focused component, or provide a
  setting to turn it off.

## 2.4.1 Bypass Blocks

- **Look for:** page layouts or app shells with repeated navigation before the main
  content and no skip link and no `<main>` landmark.
- **Rule out:** layouts that use `<header>`, `<nav>`, and `<main>` landmarks (sufficient
  on their own); single-component diffs that do not touch the page shell.
- **Fix:** add `<main id="main">` and a first focusable "Skip to main content" link that
  targets it and becomes visible on focus.

## 2.4.2 Page Titled

- **Look for:** HTML documents with no or empty `<title>`; route components in SPAs that
  never set `document.title` (or the framework's head API); every page sharing one
  generic title.
- **Rule out:** frameworks or layouts that set titles per route elsewhere (check the
  router or head configuration).
- **Fix:** set a title that names the page and the site, most specific first:
  `<title>Billing - Acme</title>`. Needs a decision when the wording is product copy.

## 2.4.3 Focus Order

- **Look for:** positive `tabindex` values; dialogs that do not move focus inside when
  they open or do not return it to the trigger on close; content inserted before the
  current position that steals focus; focus left on an element that is removed from the
  DOM or hidden; CSS `order` or absolute positioning that makes tab order differ from the
  visual order.
- **Rule out:** `tabindex="0"` and `tabindex="-1"`, which do not change order; dialog
  libraries that manage focus (check configuration).
- **Fix:** remove positive `tabindex`, move focus into dialogs on open and back to the
  trigger on close, and move focus to a sensible element before removing the focused one.
  Losing focus entirely is critical.

## 2.4.4 Link Purpose (In Context)

- **Look for:** links whose text and context are only "click here", "read more", "here",
  or "more", repeated with different targets; icon-only links with no name; links whose
  `aria-label` hides the visible text.
- **Rule out:** links whose purpose is clear from the same sentence, list item, table
  cell, or heading they sit in; `aria-describedby` or visually hidden text that completes
  the purpose.
- **Fix:** make the text describe the target, or add visually hidden text
  (`Read more<span class="sr-only"> about pricing</span>`). Needs a decision when visible
  wording changes.

## 2.4.6 Headings and Labels

- **Look for:** labels or headings that do not describe their field or section: empty
  headings, placeholder-like labels ("Field 1", "Input"), several fields with the same
  label in one form.
- **Rule out:** short labels that are clear in context (a "Search" field in a search
  form).
- **Fix:** make the label specific ("Billing email"). Usually needs a decision (wording).

## 2.4.7 Focus Visible

- **Look for:** `outline: none`, `outline: 0`, `outline-color: transparent`, or Tailwind
  `outline-none` / `focus:outline-none` on focusable elements or global selectors
  (`*`, `button`, `a`, `:focus`) without a replacement focus style; `:focus-visible`
  removed; focus styles that rely only on a colour change the code shows as tiny.
- **Rule out:** a replacement in the same rule or elsewhere (`:focus-visible` outline,
  `box-shadow` ring, `ring-*` utilities, border change); elements that are not focusable.
- **Fix:** keep the outline, or replace it:
  `:focus-visible { outline: 2px solid currentColor; outline-offset: 2px; }`.
  Removing focus visibility on primary controls is critical.

## 2.4.11 Focus Not Obscured (Minimum)

- **Look for:** `position: sticky` or `position: fixed` headers, footers, cookie banners,
  or chat widgets with no matching `scroll-padding-top` / `scroll-padding-bottom` (or
  `scroll-margin`) on the scroll container; overlays that stay open while focus moves
  behind them.
- **Rule out:** sticky elements that are small and leave the focused element partly
  visible (the minimum criterion fails only when it is entirely hidden); banners the user
  opened and can dismiss without moving focus.
- **Fix:** add `scroll-padding-top: <header height>` (and bottom for footers) on `html` or
  the scroll container; let focus close or avoid non-modal overlays.

## 2.5.3 Label in Name

- **Look for:** controls with visible text and an `aria-label` or `aria-labelledby` that
  does not contain that visible text, especially not at the start (visible "Send", name
  "Submit form").
- **Rule out:** names that start with the visible text and add context ("Send message").
- **Fix:** remove the redundant `aria-label`, or make it start with the visible text.

## 2.5.7 Dragging Movements

- **Look for:** drag-and-drop reordering, sliders, sortable lists, or map panning with no
  single-pointer alternative (buttons, inputs, menu actions).
- **Rule out:** components that offer move up/down buttons or keyboard and click
  alternatives; native `<input type="range">`.
- **Fix:** add a non-drag alternative such as "Move up"/"Move down" buttons or a
  position input. May need a decision (design).

## 2.5.8 Target Size (Minimum)

- **Look for:** clickable icons, close buttons, pagination links, or checkboxes styled
  smaller than 24 by 24 CSS px (width, height, padding, and font size) with neighbours
  closer than 24px.
- **Rule out:** inline links in sentences; targets with enough spacing; native controls
  at browser default size; sizes the code cannot determine.
- **Fix:** add padding or `min-width`/`min-height: 24px` (44px is better). Can need a
  decision (design) when it changes layout.

## 3.1.1 Language of Page

- **Look for:** `<html>` with no `lang` or an invalid value; SPA shells and
  framework document templates (`_document.tsx`, `app.html`, `index.html`) without
  `lang`.
- **Rule out:** frameworks that set `lang` from configuration (check it).
- **Fix:** `<html lang="en">` (or the page's language).

## 3.1.2 Language of Parts

- **Look for:** hard-coded passages in another language than the page with no `lang`
  attribute on their element (quotes, language pickers listing native names).
- **Rule out:** proper names, technical terms, and words that have become part of the
  surrounding language.
- **Fix:** add `lang` on the element: `<span lang="fr">Français</span>`.

## 3.2.1 On Focus

- **Look for:** `onFocus` / `focus` handlers that submit forms, navigate, open new
  windows, or move focus elsewhere.
- **Rule out:** handlers that only show help text or highlight the field.
- **Fix:** move the action to an explicit activation (click, Enter, submit).

## 3.2.2 On Input

- **Look for:** `onChange` on `<select>`, radio buttons, or checkboxes that navigates,
  submits, or reloads the page; inputs that auto-advance focus when filled.
- **Rule out:** changes that only update content near the control without moving focus
  or context; behaviour explained before the control.
- **Fix:** add an explicit submit button, or tell the user before the control what will
  happen.

## 3.3.1 Error Identification

- **Look for:** validation that only adds a red border or icon; error text not
  associated with the field (`aria-describedby` or `aria-errormessage` missing);
  `aria-invalid` never set; errors shown only in a toast that disappears.
- **Rule out:** native constraint validation with visible browser messages; form
  libraries that wire `aria-invalid` and `aria-describedby` (check their setup).
- **Fix:** show a text message next to the field, link it with `aria-describedby`, set
  `aria-invalid="true"`, and move focus or announce a summary on submit. Needs a decision
  when error wording must be written.

## 3.3.2 Labels or Instructions

- **Look for:** inputs whose only label is a `placeholder` (it disappears while typing,
  so nothing on screen still says what the field is for); required fields or format
  rules (date format, password rules) not stated before input; groups of inputs with no
  group label.
- **Rule out:** visible labels provided by a wrapper component; instructions in a linked
  `aria-describedby` element that is also visible; an adjacent button with visible text
  that labels the field (technique G167, for example a "Search" text button). An
  icon-only adjacent button does not count.
- **Severity:** a placeholder-only label is minor when the field's purpose is obvious from
  context (a lone search box) and major otherwise (a form with several such fields).
- **Fix:** add a visible `<label>`, and state format and required rules in visible text
  linked with `aria-describedby`. Needs a decision when new visible text is needed.

## 3.3.8 Accessible Authentication (Minimum)

- **Look for:** login or verification fields with `onPaste` blocked, `autocomplete="off"`
  on username or password, or puzzles and transcribed codes with no alternative.
- **Rule out:** CAPTCHAs that only ask to recognise objects or personal content, which
  this criterion allows; flows that offer another method.
- **Fix:** allow paste, use `autocomplete="username"` and `current-password`, and offer
  an alternative such as an email link or passkey.

## 4.1.2 Name, Role, Value

- **Look for:** buttons, links, and form controls with no accessible name (icon-only
  button, empty `<a>`, input with no label); custom widgets built from `<div>`/`<span>`
  with no `role`; toggles, accordions, menus, and tabs without state (`aria-expanded`,
  `aria-pressed`, `aria-selected`, `aria-checked`) or with state that is never updated;
  `aria-labelledby` or `aria-controls` pointing at an `id` that does not exist;
  `role="button"` on an element without keyboard support (also SC 2.1.1).
- **Rule out:** names from text content, `aria-label`, `aria-labelledby`, `<label>`,
  `title`, or a wrapper component that passes them; native elements whose role and state
  are already exposed (`<details>`, `<input type="checkbox">`).
- **Fix:** use the native element. Otherwise add the right `role`, a name, and state
  attributes kept in sync with the UI:
  `<button type="button" aria-label="Close dialog"><XIcon aria-hidden="true" /></button>`.
  A control with no name is critical; a wrong or missing state is major.

## 4.1.3 Status Messages

- **Look for:** success, error, loading, "added to cart", or search result count
  messages inserted into the page without `role="status"`, `role="alert"`,
  `aria-live`, or `<output>`; toasts rendered without a live region; live regions that
  are mounted at the same time as their message (often not announced).
- **Rule out:** messages that move focus to themselves (dialogs, error summaries that
  receive focus); toast libraries that render into a live region (check their source).
- **Fix:** render a persistent container with `role="status"` (polite) or `role="alert"`
  (urgent) when the page loads, then change its text.
