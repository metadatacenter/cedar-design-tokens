# Modern CEDAR UI contracts

These requirements apply to modern CEDAR applications and embedded components.
CEE's approved editable and read-only visuals are the reference; legacy AngularJS
is outside this contract. Use the [shared tokens and recipes](README.md) and
preserve existing behavior unless a product change is explicitly approved.

## Interaction requirements

| Area                | Required behavior                                                                                                                                                                                         |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Read-only values    | Content remains legible and selectable; no saving. Keep read-only and disabled states distinct.                                                                                                           |
| Dialogs             | Provide an accessible title, contain focus and keep actions reachable. Escape closes the innermost interaction; closing restores focus to the invoker. Busy writes cannot be dismissed.                   |
| Unsaved changes     | Confirm discard explicitly. Cancellation keeps input.                                                                                                                                                     |
| Saves and conflicts | Prevent duplicate writes; show progress and outcome; retain edits on failure. Use conditional writes. Conflicts require explicit reload/reopen, never automatic overwrite or retry with a newer revision. |
| Artifact commands   | Preserve labels, order and capability rules across all five artifact types. Support keyboard access and keep actions on screen.                                                                           |
| Destructive actions | Name the target and consequences; ownership transfer names the new owner. Cancel sends no write.                                                                                                          |
| Search and pickers  | Label inputs; support keyboard selection and clear/reset. Announce loading, no results and errors. Escape dismisses suggestions first.                                                                    |
| Navigation          | Preserve folder, search, sort and page in the URL. Editor return and browser Back restore context.                                                                                                        |
| Responsive layout   | Keep controls reachable at 375px and in narrow hosts. Wrap long labels or expose their full text. Tables may scroll within their own region.                                                              |
| Feedback            | Identify fields with errors; explain page-error recovery and retain edits. Announce asynchronous outcomes through status/alert regions.                                                                   |
| Motion              | Respect reduced motion, including JavaScript animations, while preserving functional completion callbacks.                                                                                                |

Components own keyboard handling, validation timing, save rules and accessible
descriptions. CSS recipes do not implement these behaviors. In particular,
`aria-disabled` styling must be paired with blocked activation; prefer native
`disabled` where appropriate. Use `aria-invalid` for validated errors so untouched
required fields are not marked prematurely.

## Fields and authoring

**Resizing.** Textareas use `resize: none`, including inside shadow roots.
Automatic sizing and scrolling remain supported. The sole manual-resize exception
is Workspace's Info panel Description, using `patterns.info-description-resize`:
a vertical handle with fixed width. Its height lasts only for the open resource
and is never saved to the artifact or preferences.

**Spellchecking.** Documents, inputs, textareas and editable content explicitly set
`spellcheck="false"`, including dialogs and shadow-root controls. There are no
prose exceptions. CEDAR validation remains unchanged; local opt-ins and missing
declarations fail adoption checks.

**Card navigation.** When an authoring card owns focus, unmodified Up/Down moves
focus and selection to the previous/next visible card and scrolls its header into
view. Clicking non-interactive card chrome focuses it. Cards have accessible names
and `aria-keyshortcuts="ArrowUp ArrowDown"`. Navigation stops at the ends and never
reorders, edits, saves or changes expanded settings. Element cards participate;
collapsed descendants do not. Inputs, tabs, menus, pickers and dialogs keep their
own keys; modified shortcuts and IME composition are not intercepted.

**Choice editors.** Options and default-value controls use `controls.choice-text`
and `controls.choice-row`: body text, regular weight and a 28px minimum row height.
Wrapped labels grow. Preserve host control typography overrides and verify parity
between CED's option editors and real CEF rendering for checkbox, radio and both
list types.

**Labels and read-only values.** Use `patterns.required-mark` for an asterisk that
does not enlarge the label's line box. Field label/help/error recipes support
`$size: small` and `$size: body`; choose the variant instead of overriding it.
Read-only specification recipes preserve selectable content, outlined-control
alignment and documented `--cedar-specification-*` overrides.

**Validation summaries.** Use `patterns.validation-summary` or
`validation-summary.css` with `.cedar-validation-summary`. Center the disclosure
icon, status icon and text together; expand issues into an indented, left-aligned
list. Errors use error roles; `validation-summary--warning` uses warning roles.
Warnings never disable saving. CED has validation errors only. The metadata host
classifies missing required values, collection properties and minimum occurrences
as incomplete-data warnings, and invalid supplied values as errors. Host code owns
classification and the save gate.

## Menus, icons and native controls

Menus use `patterns.menu-text`, included by `menu-surface` and `menu-item`:
shared family, body size, regular weight, default control line height and primary
theme color. Apply it to framework labels, nested actions, headings and empty
messages. Menu icons match the labels. Selection retains its background/checkmark;
disabled actions and input placeholders retain their state treatment.

Ordinary icons use the primary theme color, a transparent glyph background and no
glyph shadow. Apply `icon-contract`; choose `data-cedar-icon-tone` (`primary`,
`inverse`, `error`, `warning`, `success`) or a scoped `--cedar-icon-color` referencing
the corresponding token. Filled actions use inverse icons; disabled controls keep
their role with shared disabled opacity. Icon-only buttons need accessible names.
Person and settings glyphs have no decorative shaded badges. Logos and authored
imagery are separate; preserve selection fills, focus rings and surface shadows.

Modern Workspace imports `native-choices.css` globally and places
`cedar-native-choices` on its root. Preserve native checkbox/radio geometry,
keyboard behavior and disabled semantics. Shared select chevrons and date/time
indicators use the primary role; do not restore browser-default indicators locally.
Chromium and WebKit tests cover native controls and host palette overrides.

## Verification

Each modern frontend maintains `.ui-surfaces.json`. A rendered entry identifies its
source, central contract, selector, fixture scenario, states and test file.
Navigation/group entries need no rendered contract. Embedded components are tested
in their owning repository rather than duplicated in every host.

The strict adoption check validates source styles and registry coverage. It rejects
missing registrations, stale references and edited generated helpers. It also
checks resizing, spellchecking, icon use and documented host properties. It runs
offline and does **not** run browser tests or verify deployed bundles.

Registry-driven Playwright tests open real surfaces at 1440px and 375px, including
collapsed/expanded summaries. Expected values come from
[`surfaces/contracts.json`](surfaces/contracts.json), resolved in the surface's
theme/shadow root with central Sass defaults as fallback. Contract-specific rules
cover menus, dialogs, summaries, calendars, alerts and authoring controls. Every
registered surface also receives a scale check for typography, loaded fonts,
colors, paint and corners. A `page` contract uses that scale check without extra
property rules. Generated text, placeholders and SVG text are included; embedded
components, visually hidden text and glyph internals have targeted exclusions.

These style checks complement consumer keyboard, geometry, accessibility, failure
and save-flow suites. A registered surface is not proof that every state works.
Keep the relevant CEE, CED, CETP and Workspace browser/visual tests, plus live-stack
journeys for conflicts and persistence.

## Reviewing changes

Change shared roles or recipes first and preserve documented embedding overrides.
Add representative fixture states, run affected consumer suites and inspect
before/after/diff images. Update screenshots only for the approved change. Keep
browser, fonts, OS and architecture fixed; migrate those separately. Do not widen
pixel tolerances or regenerate CEE baselines to accommodate unrelated work.

Source baselines record exact existing findings by file, declaration and count.
Rendered differences use exact per-surface `debt` or `scaleDebt` records with a
reason. CI compares both against the trusted base revision; feature changes cannot
increase allowances. Remove resolved debt and use `--prune-baseline` for obsolete
source findings. Never delete and regenerate a baseline to pass CI. Unknown shared
properties, icon violations, forbidden resizing and spellcheck violations cannot
be waived. Policy upgrades use `--upgrade-policy` from a clean committed checkout;
CI derives allowances from the base under the new policy.

Add registrations and fixture scenarios with new surfaces; remove both when a
surface disappears. Keep IDs stable through renames. Change central rules here,
then run `cedarcli check design-tokens --sync-surfaces` and the affected browser
suites. Do not copy expected colors or dimensions into consumer tests, weaken a
contract to hide drift or change approved UI merely to clear existing debt.
