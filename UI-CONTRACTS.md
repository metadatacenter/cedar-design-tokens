# Modern CEDAR UI contracts

CEE's approved editable and read-only visuals are the reference. Legacy AngularJS
is outside this contract. A shared token value is necessary but does not establish
a complete interaction or layout; use the patterns export where a recipe applies.

| Surface             | Required contract                                                                                                                                                    | Verification                                                         |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Read-only values    | Legible, selectable content; no saving. Disabled actions remain distinct.                                                                                            | CEE approved baselines; Workspace read-only browser checks           |
| Dialogs             | Named target/title, contained keyboard focus, reachable actions, Escape closes the innermost interaction, focus returns to invoker. Busy writes cannot be dismissed. | Workspace keyboard suite and narrow Permissions baselines            |
| Unsaved changes     | Never silently discard; explicit discard confirmation; cancellation retains input.                                                                                   | Workspace resource and metadata browser flows; CED/CEE suites        |
| Saves               | Prevent duplicate writes; show progress and outcome; retain edits on failure.                                                                                        | Workspace duplicate/stale-save browser checks and real-stack journey |
| Conflicts           | Conditional writes; no automatic overwrite/retry with a newer revision; explicit reload/reopen.                                                                      | Permissions/Groups unit suites and two-user live journey             |
| Artifact commands   | Stable labels, order and capability rules for all five artifact types; keyboard access; no hidden off-screen actions.                                                | Workspace artifact-type/permission matrix and browser suite          |
| Destructive actions | Name the target and consequences before confirmation. Cancel sends no write. Ownership transfer identifies the new owner.                                            | Workspace browser and Permissions tests                              |
| Search/pickers      | Labelled input, keyboard selection, clear/reset, announced loading/no-results/errors; Escape dismisses suggestions first.                                            | GroupPicker tests, Workspace browser suite, CETP browser suite       |
| Navigation          | URL retains folder/search/sort/page; editor return and browser Back restore context.                                                                                 | Workspace browser tests and host return tests                        |
| Responsive UI       | Controls stay reachable at 375px and in narrow embedded hosts; long labels wrap or expose their full text; data tables may scroll within their own region.           | Workspace, CED, CEE and CETP browser geometry/visual tests           |
| Feedback            | Field errors identify their field; page errors explain recovery and retain edits; asynchronous outcomes use live status/alert regions.                               | Axe plus explicit failure-flow tests                                 |
| Motion              | Respect reduced-motion; keep functional completion callbacks.                                                                                                        | Shared motion tests and component browser suites                     |

## Making an intentional visual change

Change shared roles or recipes first. Add a representative state to the fixture
gallery, run the impacted consumer suites, and inspect before/after/diff images.
Update baselines only for the intended change. Keep browser, fonts, OS and CPU
architecture fixed; changing these is a separate baseline migration. Never widen
pixel tolerances to make a failure disappear. CEE's approved baselines must not be
regenerated incidentally during consumer work.

The checker scans stylesheet files, Angular styles/templates and inline bindings.
Policy 2 gates typography, color, fixed spacing/control geometry, utility styles,
overlay layers and unknown shared properties. Existing debt is tracked per exact
file/declaration/count. `--prune-baseline` can only remove allowances. Policy rollout
uses `--upgrade-policy` on a clean committed checkout; CI independently derives its
maximum allowances from the trusted base revision. Unknown shared properties and
icon violations cannot be waived. Documented embedding overrides are registered
in `tools/host-properties.json`; this does not permit arbitrary new token names.

Local layout can still use percentages, flexible tracks and positional bindings.
A new fixed design dimension should become a shared semantic role rather than an
unexplained exception. Inline dynamic paint bindings should become inspectable
semantic classes. Existing exceptions cannot be silently added to a feature PR.

Reviewer ownership and repository approval rules are intentionally unchanged.

## Field resizing

Manual field resizing is forbidden across modern CEDAR surfaces, including embedded
shadow roots. Textareas must set `resize: none`. Automatic sizing to fit content
and scrolling remain supported. Other resize values, dynamic resize bindings and
resizing utility classes fail the adoption gate and cannot be grandfathered through
a baseline or exception.

## Browser spellchecking

Modern CEDAR controls explicitly set `spellcheck="false"`. Browser spelling marks
are inappropriate for scientific names, controlled terms, identifiers and artifact
metadata. This behavior applies to inputs, textareas and editable content, including
controls inside shadow roots and dialogs. Application documents also default to off.
This is an HTML behavior contract, not a CSS token. CEDAR validation is unchanged.

There are currently no prose exceptions. An exception requires a deliberate update
to this shared contract and its adoption gate; do not enable it locally. The adoption
check rejects missing declarations and spellcheck opt-ins, including bindings. These
findings cannot be grandfathered into visual/style baselines.

## Card navigation

In vertical authoring-card collections, unmodified Up/Down moves keyboard focus and
selection to the previous/next visible card in document order and brings its header
into view. Clicking non-interactive card chrome gives that card keyboard focus.
Cards expose an accessible name and `aria-keyshortcuts="ArrowUp ArrowDown"`.
Navigation stops at the ends; it never wraps, reorders, edits, saves or changes a
card's expanded settings. Element cards participate; collapsed descendants do not.

Arrow navigation applies when the card itself owns focus. Inputs, textareas,
selects, tabs, menus, pickers and dialogs retain their own keyboard behavior.
Modified shortcuts and IME composition are not intercepted. This is an interaction
contract, not a CSS token or a document-wide keyboard handler. CED's card-navigation
browser tests enforce it at desktop and narrow widths and across nested elements.

## Choice editors and default values

Editable checkbox, radio and list options and their default-value controls share
`controls.choice-text` and the `choice-row-height` role. Minimum row height is
28px; wrapped labels grow. Consumers must not derive this height independently
from ordinary-control density or layer utility text colors over the shared role.
The CED real-CEF browser suite compares both renderers for every choice type;
CEE visual baselines cover selected, disabled, read-only and wrapped states.

## Validation summaries

Use `patterns.validation-summary` for a collapsible validation notice in an authoring editor.
Center the summary's disclosure icon, warning icon and text as one group. Expanded issues form
an indented, left-aligned list below it. Errors use the shared error foreground and surface;
`validation-summary--warning` uses the orange warning roles. Warnings never disable saving.
CED currently has only validation errors. The metadata host treats missing required values,
missing collection properties and unmet minimum occurrences as incomplete-data warnings;
invalid supplied values are errors. Host code owns that classification and the save gate.

Hosts without Sass can load `custom-properties.css` and `validation-summary.css`, then use
`.cedar-validation-summary`. The compiled stylesheet includes the shared regular font;
`icons.svg` exposes the same icon registry as SVG symbols for those hosts. Main consumes
these assets through its declared design-token dependency and stages them with `copy:tokens`.
