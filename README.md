# CEDAR Design Tokens

CEDAR's interface is plain text and boxes, and this package holds every value that decides how it
looks: one font, five type sizes, two weights, one theme colour, three text colours, two rule
colours, three surfaces, one spacing scale and one corner radius. The
[embeddable editor](https://github.com/metadatacenter/cedar-embeddable-editor), the
[embeddable designer](https://github.com/metadatacenter/cedar-embeddable-designer), the
[embeddable term picker](https://github.com/metadatacenter/cedar-embeddable-term-picker) and the
browser applications that host them read as one product only because none of them states a value of
its own.

## Using It

The values are authored once, in Sass, and served in two forms because the consumers are written
differently.

A Sass consumer takes the partial and reads the variables through an alias:

```scss
@use '@org.metadatacenter/cedar-design-tokens/tokens' as tokens;

.hint {
  font-size: tokens.$font-size-small;
  color: tokens.$text-muted;
}
```

The variables carry no component prefix. The alias is where the scope belongs, so it is
`tokens.$font-size` rather than `tokens.$cedar-font-size`.

Sass does not resolve a package path on its own, so `node_modules` has to be on the load path. In an
Angular application that is one entry in `angular.json`, beside the one the repository already has
for its own `src`:

```json
"stylePreprocessorOptions": {
  "includePaths": ["src", "node_modules"]
}
```

A build that runs `sass` directly takes `--load-path=node_modules`, and one whose Sass has the
package importer enabled can write `@use 'pkg:@org.metadatacenter/cedar-design-tokens/tokens'`
instead and skip the load path.

A consumer whose stylesheet is plain CSS imports the compiled declarations instead, resolved by the
bundler rather than by Sass:

```css
@import '@org.metadatacenter/cedar-design-tokens/custom-properties.css';
```

That file declares each value as a custom property under a `--cedar-` prefix: `--cedar-font-size`,
`--cedar-color-primary`, `--cedar-text-muted`. A custom property has no alias to be scoped by, so the
prefix is on the name. The declarations land on `:root` **and** `:host`, because a CEDAR component
renders inside a shadow root when it is embedded and `:root` matches the document element, which is
outside it. A component that renders in a shadow root of its own can include
`custom-properties.declare` on `:host` instead, so the shared recipes it uses resolve without relying
on the embedding page:

```scss
@use '@org.metadatacenter/cedar-design-tokens/custom-properties';

:host {
  @include custom-properties.declare;
}
```

`custom-properties.css` is generated from the partial by `npm run build`, which emits every scalar
in the Sass module under its own name. The two palette maps and the Material font string are
adapter inputs and are not emitted. Run the build after changing a value: the registry tarball
contains the compiled CSS, prepared before packing.

## The Vocabulary

Sixty-one tokens, in seven groups. A value between two of them is not on the scale; a consumer uses
the nearer one.

Typography is one family, five sizes and two weights. The sizes are in px rather than rem, because
`rem` resolves against the embedding page's root element, which a component neither sets nor can
see: a host with `html { font-size: 62.5% }` would render rem-sized type at 62.5% of its size.

| Token                       | Value                     | Role                                                  |
| --------------------------- | ------------------------- | ----------------------------------------------------- |
| `font-family`               | CEE Roboto stack          | All interface text                                    |
| `font-family-monospace`     | System monospace stack    | Logs, identifiers and code                            |
| `font-weight-regular`       | 400                       | Body text, values and unselected tabs                 |
| `font-weight-medium`        | 500                       | Labels, headings, the selected tab, the current crumb |
| `font-size-small`           | 12px                      | Hints, counts, versions and other secondary facts     |
| `font-size`                 | 14px                      | Body text, controls, labels, menus and tabs           |
| `font-size-element-heading` | 18px                      | A nested element's heading; a section inside a page   |
| `font-size-heading`         | 20px                      | A section break; the largest heading inside a form    |
| `font-size-artifact-title`  | `clamp(19px, 3cqi, 26px)` | The title of a page, an artifact or a dialog          |
| `line-height-heading`       | 1.25                      | Every heading and title                               |

Colour is one theme colour with a stronger variant, three text colours, two rules and three
surfaces. Status colours come in pairs, each tested for normal-text contrast against its surface,
and always accompany a label or icon. Information uses the primary roles.

| Token                                        | Role                                                      |
| -------------------------------------------- | --------------------------------------------------------- |
| `color-primary`, `color-on-primary`          | Links, icons, focus, selection marks and filled actions   |
| `color-primary-strong`                       | Primary text on a tinted surface; a filled action's hover |
| `text-primary`, `text-muted`, `text-title`   | Ordinary text, secondary text and titles                  |
| `border-rule`                                | Rules, card borders, table dividers and overlay outlines  |
| `control-border-default`                     | The outline of anything a person can edit                 |
| `surface-raised`                             | Pages, cards, menus, dialogs and controls                 |
| `surface-subtle`                             | Panels, read-only values, hovered rows and canvases       |
| `surface-selected`                           | Selected rows and hovered actions                         |
| `status-error-*`, `-warning-*`, `-success-*` | `-text` and `-surface` pairs                              |
| `status-unsaved-dot`, `dialog-backdrop`      | The unsaved-changes dot; the scrim behind a modal dialog  |

Controls have two densities. The `-default` tokens describe the 36px control with a 21px line; the
`-authoring` tokens the 32px control with an 18px line that authoring surfaces use. The
`authoring.density` mixin points the two `-default` properties at their `-authoring` values. These
are defaults only: the public host overrides, such as `--cedar-control-height`, have different
names, and the adapters read an override first. A choice option and an authoring table row are
`row-height-compact` (28px); an ordinary listing row is `table-row-height` (44px: a control with a
small gutter above and below).

Space, shape and elevation are each one short scale. Every padding, margin and gap is a step of
`space-1/2/3/4/6` (4, 8, 12, 16 and 24px), with `calc()` for a half step or a multiple. Every box
has the `radius` corner (4px); chips and pills take `radius-pill`. Icons are 16, 20 or 24px. Menus,
popovers, tooltips and drag previews take `shadow-overlay`; dialogs take `shadow-dialog`.

Motion is two interaction durations, a spinner duration and two easing curves. Layers are five
ordered stacking levels: sticky, menu, modal, overlay and tooltip.

## Holding the Line

The vocabulary stays small only if adding to it, or working around it, is visible. Five checks
make it so.

The package's `test/inventory.test.mjs` lists every token by group, and the build fails when the
emitted set differs from it. A new token is added there, for a role no existing token covers, in
the same change as the consumer that needs it.

`cedarcli check design-tokens --strict` fails on a token that no consumer and no recipe reads, so
an unused token is removed rather than kept in reserve.

The same check rejects a reference to a retired name and states its replacement, from
`tools/retired-tokens.json`. Retired names cannot be baselined.

A consumer may not give a shared token a local value: `--cedar-space-2: 6px` inside a component
changes the meaning of a shared name where no other surface can see it, and the check rejects it
without exception. A component may only re-point a shared role at one of its own documented host
properties, as the term picker does with `--cetp-*`.

The source checks cannot see what a framework draws, so every registered page, menu, dialog and
summary is also checked as rendered. The shared browser helper walks the open surface, shadow roots
included, and fails on a font size, weight, family, text colour, letter spacing or corner that no
token supplies. A page surface (contract `page`) has no property rules of its own: the whole frame
is walked against the scale. Another CEDAR component embedded in a surface is skipped, because its
own repository checks it. The allowed values resolve in the surface's own context, so a host theme override
passes. A reviewed exception is a `scaleDebt` entry on the surface (the property, the exact value
and a reason), and a change cannot add one against its base revision.

## What Does Not Belong Here

A value only one component has. The editor's layout constants (the trailing slot in a title row,
the card's inline gutter, the size of a toolbar control) stay in the editor. A shared package that
carried them would hand two other components measurements of a card they do not draw. Geometry
that a shared recipe needs, such as the minimum width of a resource card, lives in the recipe.

Anything from `@angular/material`. These values are CEDAR's, and expressing them in the vocabulary
of a framework that renames that vocabulary every couple of releases means each rename edits the
brand. The editor's `_cee-material-theme.scss` is the adapter that feeds these to whatever theming
API the installed Material version offers. The palette maps exist for such adapters: the primary
map feeds Material's tonal roles, and the rust accent map remains only as the M2 accent input of
Monitoring and Bridging.

## Releasing

The package is consumed at build time and nothing published references it at run time, so it is a
`devDependency` and never reaches a public consumer. There is no npmjs release: the scoped name
routes to the CEDAR Nexus registry, which `.npmrc` configures, and a dev snapshot is what consumers
resolve.

Consumers pin an exact snapshot in `package.json` and their lockfiles. A token
change reaches them by publishing a new version, updating those pins, and
rebuilding each component. Publishing alone does not change an existing pin.

## Component Adapters and Host Styling

The shared package defines build-time defaults. Consumers translate those values
into their own styling systems: CEE's Material adapter, CED's Tailwind theme and
CETP's `--cetp-*` defaults. Adapters read tokens for shared roles; controls do not
keep copies in TypeScript objects or local stylesheets. CED's Tailwind theme maps
its `teal-*` and `gray-*` scales, its shadows and its radii onto the shared roles,
so a utility written there can only produce a shared value.

Host customization is explicit and tested:

- CEE/CEF and CED's native controls retain the compact-control API documented in
  [CEE's STYLING.md](https://github.com/metadatacenter/cedar-embeddable-editor/blob/develop/STYLING.md),
  and CEE keeps its documented `--cedar-specification-*` overrides for read-only values.
- CETP retains its ten documented `--cetp-*` properties, including body size and
  primary/on-primary colors, and re-points the shared roles at them inside its
  shadow root, so the shared recipes it uses follow a host's settings too.
- The generated `--cedar-*` properties are the CSS representation of these defaults,
  not a promise that setting one will theme all three components.

Keep Material internals private. Do not remove existing host properties to achieve
uniformity. Hosts overriding colors must preserve status meaning and readable
foreground/background combinations.

## Embedded Fonts

`@use '@org.metadatacenter/cedar-design-tokens/fonts'` emits the self-contained
Roboto 300/400/500 font faces shared by the editor and designer. Include it in
the component's unencapsulated font registrar: browsers do not register font
faces inside shadow roots. The export contains no selectors or network URLs.
The font family remains `CEE Roboto`; consumers no longer keep copies of the
font source. Each built bundle still embeds the fonts it needs.

## Monitor Adoption

Run `cedarcli check design-tokens` from the CEDAR workspace. It reports each
component repository's new and existing gated style findings,
resolved debt, and token manifest/lock versions. `--repo cedar-embeddable-designer` selects
one repository; `--all` includes existing findings; `--json` supports dashboards.
`--strict` fails on new paint, typography, spacing, control geometry, layer, motion
or utility-style findings, unknown shared properties, missing baselines, or a missing,
ranged or lockfile-mismatched token dependency. It does not require every consumer
to match the token checkout's version before that version has been published. No network,
Nexus credential or frontend build is needed. The modern Angular Workspace is included. The retiring AngularJS application
shells remain excluded; their styles are not migration targets.

This is a source heuristic, not an adoption percentage or an accessibility audit.
It scans first-party CSS/SCSS/Less under `src` and `app`, including unignored new
files. Vendor/assets, generated/ignored files, fixtures and the Material icon
font are excluded. Policy 2 also inspects Angular component styles/templates,
HTML inline styles, style bindings and utility classes in static or bound classes.
It rejects dynamic paint/style bindings that cannot be inspected. Arbitrary
JavaScript-generated styles are not fully analyzed; browser contracts remain
necessary alongside this source heuristic. A matching dependency version
means agreement with the token checkout's version, not proof that unpublished
source changes have reached Nexus or the served bundle. Use `cedarcli check
components` to check served component freshness.

Each frontend owns `.design-tokens-baseline.json`. Entries identify the file,
rule, property and normalized value, with an occurrence allowance. Moving lines
does not create noise; adding another copy or replacing a literal does. Moving a
literal to another file requires review. Existing findings are debt candidates,
not a claim that every literal must be replaced.

- Prefer a semantic token; don't select a role just because its current hex matches.
- After fixing findings, run `cedarcli check design-tokens --repo <repo>
--prune-baseline`. This can only decrease allowances. Commit the smaller baseline.
- Add intentional shared values as semantic roles in this package. CI rejects
  new or altered exceptions against its trusted base; existing exceptions match
  exact declarations, never entire files or rules. Unknown roles and icon drift
  cannot be waived.
- `--init-baseline` creates the initial inventory and refuses to replace one.
  Don't delete and regenerate a baseline to make CI green.

The consumer CI workflows call this repository's reusable `adoption.yml` workflow
and upload `adoption.json`, even when the strict gate fails. Pull requests compare
against the **base revision's** baseline and exceptions, so expanding them in the
same PR cannot conceal new drift. Initial rollout, where the base has no baseline,
uses the new inventory and emits a review notice. A later intentional exception
must be reviewed and merged separately before the styling change it permits.
Changes to the scanner need tests and a review of their effect on existing findings.

Typography checks include keyword weights and sizes, percentage/viewport units,
font shorthand and literal fallbacks. A compatibility fallback on a shared token
is allowed only when it exactly matches that token's canonical Sass value; an
arbitrary local fallback is still checked. Modern CSS color functions (`lab`,
`lch`, `oklab`, `oklch`, `hwb`) are checked alongside hex, RGB and HSL colors.
Push runs compare baselines against the previous pushed revision, just as pull
requests compare against their base. Adding allowances beside new styles cannot
silence the gate in the same push.

Rollout order: merge the checker/reusable workflow in this repository first, then
the consumer baselines/workflows and CLI command. Consumers reference `develop`;
branch protection must require the adoption job if it is to block merging.
Publishing an npm package is not needed for this source check.

### Common Styling Choices

| Intent             | Sass token / CSS property                                                     |
| ------------------ | ----------------------------------------------------------------------------- |
| Body text          | `tokens.$font-size` / `--cedar-font-size`                                     |
| Secondary hint     | `tokens.$text-muted` / `--cedar-text-muted`                                   |
| Validation error   | `tokens.$status-error-text` / `--cedar-status-error-text`                     |
| Advisory notice    | `status-warning-text` foreground and `status-warning-surface` background      |
| Ordinary gap       | `tokens.$space-2` / `--cedar-space-2` (8px)                                   |
| Designer input     | Standard CEE adapter (14px text, 36px controls); inherited host overrides win |
| Host customization | Existing public `--cedar-control-*` overrides; defaults remain fallbacks      |

For example:

```css
.hint {
  color: var(--cedar-text-muted);
  font-size: var(--cedar-font-size-small);
  margin-top: var(--cedar-space-1);
}
```

Review a styling PR for the intended role, preserved host overrides and a check
of focus, errors, read-only behavior and narrow hosts. Component-specific geometry
can stay local. New values used across components belong here with a semantic name.

### Compare the Real Components

CED's `browser/fixtures/style-comparison.html` renders CEE, CEF, CED and CEFD
from local distribution bundles with the same sample fields. It offers both entry
densities, narrow hosts, read-only entry/field design and inherited host overrides.
Tab through controls and clear required values or enter invalid email values to
inspect focus and validation. CED itself remains editable; it has no equivalent
host read-only property. No disabled state is simulated with a cosmetic overlay.
See the frontend runbook for building/staging the two bundles and opening the page.

## Shared Iconography

The existing package also owns CEDAR's icon vocabulary. Import `getIcon`,
`iconSvg`, `iconStyle` and the `IconName` type from
`@org.metadatacenter/cedar-design-tokens/icons`. This export has no framework
or font dependency. Thin framework adapters render its SVG; applications must
not maintain their own geometry or import Lucide directly.

`icons/manifest.json` maps CEDAR meanings to a curated, exactly pinned Lucide
release. For example, `populate`, `artifact-instance`, `permissions` and
`field-controlled` describe actions and data types rather than upstream filenames.
Explicit aliases support existing callers. Unknown names throw instead of silently
rendering a misleading fallback. Add new meanings here with a test and update
consumers through an immutable package release.

Use the shared small/default/large icon sizes (16/20/24px) and 2-unit stroke.
SVGs inherit `currentColor`, are decorative and are hidden from assistive
technology. Give the enclosing icon-only button a descriptive accessible name;
never use an icon or tooltip as its only accessible name. Logos and authored
content remain separate from interface iconography.

The build copies only approved SVG geometry and preserves Lucide's license in
`icons/LICENSE`. Tests compare every icon with the pinned source, verify aliases,
reject unknown names and check SVG accessibility, color and sizing contracts.

The adoption gate also checks iconography in modern first-party HTML, TypeScript
and stylesheets. It rejects local SVG geometry, icon-font markup, direct icon-set
imports, unknown static semantic names and text glyphs used as controls. The thin
registry adapters and the exact CEDAR brand asset are recognized explicitly.
Icon violations cannot be added to a baseline or waived by its exceptions.
Dynamic icon names are validated at runtime and covered by adapter and browser
tests. Framework-owned native control internals and user-authored content are
outside this source guard.

The modern Angular OpenView, Monitoring and Bridging applications also consume
this registry. Their CI runs `tools/check_icons.py --repo .` against the nested
`*-src/src` application trees. This check has no baseline or exemption file;
AngularJS and generated distributions remain outside its scope.

## Interaction Recipes

The `authoring` Sass export owns native authoring controls, labels, compact tables,
entry-row density, themed select arrows, inline text actions and settings-dialog
structure. The `settings-dialog` mixin supplies `.settings-dialog-*` classes for
headers, bodies, groups and footer actions; consumers retain content and width.
The general `patterns.dialog-surface($padding: ...)` recipe also supports content
that owns its internal padding. It emits no CSS
until included. CED consumes it directly; `src/authoring.scss` in CED selects the
surfaces, while geometry and typography stay in this package. Do not copy these
recipes into component-local helpers or patch them with a second global recipe.
The `compact-control` recipe preserves the existing `--cedar-control-*` host API;
`density` selects the authoring defaults without overriding explicit host values.

The `patterns` export's `tabs` and `tab` recipes draw every tab row: muted body text, the
selected tab primary and medium over a 2px primary rule, and a rule under the row. Workspace's
Groups and information tabs, CED's settings tabs and the term picker's result tabs all use them.

The `controls` Sass export provides opt-in `focus-ring`, `action-states`,
`primary-action`, `input-states`, `select-indicator` and `picker-indicator` mixins.
Applications supply selectors; the package supplies shared state values. Include primary styles after ordinary
action styles. `aria-disabled` styling does not disable behavior: the component
must still block activation. Use native `disabled` where appropriate.

The focus and invalid recipes accept colors so existing documented embedding
overrides can remain authoritative. Invalid styling uses `aria-invalid`, not
`:invalid`, to avoid marking an untouched required field as an error.

## Dialog and Menu Surfaces

`patterns.dialog-surface`, `menu-surface` and `menu-item` describe shared surfaces, not
application-specific widths. Native dialogs, designer popups and Material adapters consume the same
corner, shadows, backdrop and spacing steps. Menu items use the shared control height.
Keep viewport constraints, focus trapping, dismissal and focus restoration in the
component; tokens do not implement those behaviors. The template designer host
stages the same generated properties alongside its icon module.

## Semantic Color Roles

Use `surface-selected` for selection and `surface-subtle` for hover, so a pointer does not make an
unselected row look selected. Every text role is tested for normal-text contrast of at least 4.5:1
on each surface it is drawn on, the status pairs included. Retain a label or icon alongside status
color. A destructive action uses `status-error-text`, which does not replace an error message.
Read-only surfaces remain distinct from native disabled behavior. CETP derives its selection tint
from the documented host primary override, so a host that re-points the primary gets a matching
tint.

`--cedar-status-unsaved-dot` supplies the yellow filled indicator beside an unsaved-changes label.

## Forms and Table Density

The field recipes set form rhythm from the spacing scale: a label sits `space-2` above its control
and help text `space-1` below it. Help and error text share the small type role and an 18px line
box. Validation timing and accessible descriptions remain component
responsibilities.

Form recipes default to the small type role for existing consumers. Larger-text forms
opt in with `patterns.field-label($size: body)`, `patterns.field-help($size: body)`
and `patterns.field-error($size: body)`. This uses the shared body role while keeping
each recipe's spacing, weight and semantic color. Use this variant instead of adding
a local font-size override after the mixin. Only `small` and `body` are supported.

Ordinary tables use 44px minimum rows with 4px/12px cell padding; authoring tables
use 28px minimum rows with 2px/8px padding. Authoring headers fit their text; rows
grow for wrapped values or larger controls. The ordinary profile fits its controls
plus both vertical gutters, an invariant checked by package tests. Column widths, scrolling limits and responsive layout stay local.

The adoption gate also scans the nested frontends in OpenView, Monitoring and
Bridging, and the Template Designer host. Their initial baselines inventory
existing literal colors and typography; they are not exemptions for new values.
CI reads the trusted base revision, so increasing a baseline in a change cannot
hide new drift. Policy 2 also gates spacing, control geometry, layers and embedded styles; icon drift is never waived.

Styling `var()` references must name a published CEDAR token, a documented host
property, or a locally declared alias. Framework variables are not implicit
contracts. Local aliases are checked at their declaration and in the context of
the consuming property, so an alias cannot hide a literal font size or spacing.
Undeclared styling variables cannot be baselined or excepted. Runtime layout
properties (for example a computed grid column definition) remain local.

### Motion and Overlay Layers

Use the fast and normal duration roles with the shared easing curves. Continuous
progress indicators use the spinner duration role. Literal transition/animation
durations and style utility classes in Angular bindings are gated as well. Include
`motion.reduced-motion` once per application/shadow root, or import `motion.css`.
The reduced-motion recipe finishes animations promptly rather than removing them,
so completion-driven behavior still runs. Component code must separately respect
the preference for animations driven by JavaScript.

Sticky content, menus, modals, overlays and tooltips have ordered layer roles.
They apply within each host's stacking context; they cannot escape a shadow host
or outrank the browser's native dialog top layer. Keep backdrop and modal siblings
in DOM order at the same modal layer.

### Visual Reference

CEE's editable and read-only rendering is the reference for the modern CEDAR UI, and it is drawn
from this vocabulary like everything else: its Material adapter maps every type level to the five
sizes and two weights without Material's per-level letter spacing, and every Material box to the
one radius. Authoring needs additional controls and arrangements, but does not establish a separate
visual language of gradients, elevated cards or oversized branding. CED's real-component browser comparisons exercise
that relationship against CEE in both display modes; CEE's screenshot baselines
remain the reference, not snapshots to update to accommodate another component.

## Shared UI Patterns

Use `@use '@org.metadatacenter/cedar-design-tokens/patterns';` for opt-in Sass
recipes: artifact titles, dialog surfaces/actions, menus/items, field labels/help/errors,
required marks, toolbars, tabs, breadcrumbs, resource grids and cards, table cells and
empty states. For example:

```scss
@use '@org.metadatacenter/cedar-design-tokens/patterns';
.permissions-dialog {
  @include patterns.dialog-surface;
}
```

Recipes emit no global selectors and use the same semantic roles as CEE. Consumers
retain layout constraints and behavior. Workspace's grid view and OpenView's folders
share the `resource-grid` and `resource-card-*` recipes and the `breadcrumbs` trail, so
a public folder reads like Workspace content; selection, menus and moves stay with
Workspace. See [UI contracts](UI-CONTRACTS.md) for the
interaction requirements, baseline procedure and the suites that enforce them.

## Candidate Consumer CI

The `Consumer contracts` workflow checks all eight modern consumers on token pushes
and pull requests. It records the consumer revision and candidate tarball hash,
replaces only the dependency-free token package in a locked consumer install,
and verifies every published file byte for byte. All consumers build; CEE, CED,
CETP and Workspace also compare their existing screenshots in the pinned ARM64
Playwright environment. It never publishes or updates consumer baselines.

### Choice Rows

Checkbox, radio, single-select and multi-select fields draw editable options and defaults in the
body text role: 14px regular text on a 21px line in the primary text colour, without letter spacing,
in rows of at least `row-height-compact` (28px). Long labels may grow; a row height is a minimum,
not clipping. Dropdown options use a 2px block padding. Disabled and read-only states retain their
state-specific treatment.

Use `controls.choice-text` and `controls.choice-row` in native option editors.
CEE applies these recipes inside its Material adapter and uses the row-height
role for radio/checkbox state layers and radio clear buttons. CED must not add
utility typography or inter-row gaps that override this contract. Existing
`--cedar-control-font-size` and `--cedar-control-line-height` host overrides take
precedence.

Verify option-editor/default parity for checkbox, radio and both list types,
including dropdown rows, long labels, host typography overrides and narrow hosts.

The Workspace Info panel Description may opt into `patterns.info-description-resize`
for its explicitly approved temporary vertical resize handle. All authoring fields
retain `resize: none`; see the Field resizing contract in `UI-CONTRACTS.md`.

The explorer's drag preview takes `shadow-overlay`, and its selection rectangle is the primary
colour at 13% opacity. The shared `grid` icon identifies the grid view alongside `list`.

### Native Checkbox and Radio Controls

`native-choices.css` applies `controls.native-choice` beneath a
`cedar-native-choices` host class. Import it once and place that class on the
modern application's root. This supplies primary accent and keyboard focus roles
without replacing browser semantics, disabled treatment or control dimensions.

The same stylesheet replaces the browser's black indicators on native single selects
and date and time pickers. `controls.select-indicator` draws the registry's
`chevron-down` with two gradient strokes, because a select cannot hold an SVG and a
background image cannot follow a host's primary colour. The glyph sits where a small
icon sits at the `space-3` inline inset, and the select reserves that icon column.
`select-indicator($density: authoring)` keeps the `space-2` inset of compact authoring
controls; `authoring.select-arrow` uses it.
`controls.picker-indicator` masks the indicator with a registry glyph (`field-date`,
or `field-time` for time inputs) in the icon role; the browser keeps the hit area
and the picker. `controls.search-clear-indicator` does the same for a search field's
clear button, with the registry's `close` glyph. The masks are generated from the registry into `dist/_icon-masks.scss`.
A select that places a registry icon beside itself declares `data-cedar-select-icon`
and keeps that icon.
Workspace uses this for Groups, Permissions, type filters and draft sharing.
The runtime `--cedar-color-primary` and `--cedar-focus-ring-*` values remain authoritative.

The adoption gate requires Workspace's root opt-in and the import in an injected
global build stylesheet. Missing coverage and resets to browser-default accent
colours cannot be baselined or excepted. Rendered Chromium/WebKit checks compare
actual controls with token values, including disabled and newly added native
controls and a changed host palette. The source check is an integration guard;
it does not prove the entire CSS cascade. Legacy AngularJS pages remain excluded.

## Maintained Surface Registry

Workspace, CED, CEE, the Template Designer host and OpenView own `.ui-surfaces.json` files.
These are the source for the human-readable surface hierarchy and the rendered
menu, dialog and validation-summary checks. Embedded CEE/CEF internals remain
opaque in the hierarchy; their own component suites retain that coverage.

OpenView's registry lives at its repository root; its source and owning package
live under `cedar-openview-src`. Coverage scans that nested source even when CI
names the checkout `consumer`. Its literal Angular routes must be registered,
including the hidden root redirect. The hierarchy lists the five resource pages,
metadata panel, legend, opaque CEE and host error/empty states. The unused JSON viewer is
not a user-facing surface.

OpenView currently has source/hierarchy coverage and the existing style-adoption
gate, with no rendered token contracts. Its errors are inline cards, not dialogs.
Registries without rendered contracts may omit `browserHelper`; adding a recognized
menu or dialog still requires registration, a rendered contract and browser tests.
CEE menus/dialogs remain registered once in CEE, rather than copied into each host.

Each checked surface has a stable ID, name, parent/section, source anchor,
central contract, browser selector, scenario, applicable states and test file.
Several commands may share one dialog implementation. Navigation/group entries
have no rendering contract. Source declarations and scenario implementations stay
in the owning repository, so a surface change and its registration travel together.

`cedarcli check design-tokens --strict` now also rejects missing registries,
duplicate IDs, missing parents/cycles, stale source/test references, unregistered
semantic dialogs/menus/validation summaries, and modified generated browser helpers.
This coverage gate has no style-baseline escape hatch. Discovery also recognizes
the existing custom menu/modal classes; arbitrary new unlabelled divs cannot be
reliably classified automatically and still require review.

Run these through the CLI:

```bash
cedarcli check design-tokens --strict
cedarcli check design-tokens --sync-surfaces
cedarcli check design-tokens --surface-inventory "$CEDAR_HOME/output/modern-workspace-ui-inventory.md"
```

`--sync-surfaces` copies the central browser implementation/types into each
consumer's test directory, allowing its ordinary CI suite to run without a sibling
checkout or a new package publication. Generated helpers are compared byte for byte
with the central implementation. Never edit those copies. Candidate-token CI
regenerates them against the candidate before exercising consumers.

The registries generate Playwright cases at 1440px and 375px. Summary cases cover
collapsed and expanded states. Tests open actual surfaces through local fixtures,
then compare computed styles with the central roles in `surfaces/contracts.json`.
Expected values resolve in the surface's own shadow root/theme, with compiled
central Sass defaults for adapters that do not expose CSS properties. Evidence is
attached to each Playwright result. Source validation remains offline: it does
**not** claim that browser cases ran or that a deployed bundle is current.

Current rendered contracts cover overlay colors/corners and validation-summary
colors/type, and every registered surface is checked against the shared scale. Existing interaction/visual suites continue to cover keyboard access,
focus, saving, disabled controls and geometry. A registry entry is not a claim that
every state or every property has been visually verified.

Existing measured differences use per-surface, per-property `debt` records with
exact actual/expected values and a reason. They preserve the approved UI during
registration; they are not an instruction to redesign it. Changed or resolved
values fail until the implementation or obsolete debt is addressed. Consumer CI
compares debt against the trusted base registry and rejects added/altered allowances.
The initial registry is reviewed as a migration, alongside the source-style baseline;
subsequent feature work cannot silently expand it.

To add a surface, add its registration and fixture scenario in the same change,
run the strict adoption check and its registry-driven browser suite, then regenerate
the Markdown if needed. Removing a surface removes its record and scenario. Keep
IDs stable through label changes. Add new shared visual rules centrally and sync
consumers; do not copy expected hex values or pixel constants into scenarios.

When changing the central token values used here, run `npm run surfaces:defaults`
to regenerate `surfaces/token-defaults.json`. Package tests compare that offline
reference with evaluated Sass, so a stale reference cannot pass token CI.

Roll out consumer registries and their self-contained browser tests first, then
the central coverage gate and CLI options. This avoids making adoption CI require
a registry before the consumer has it. No release version or application style
change is part of registration.

### Read-Only Specification Recipes

`patterns.specification-box`, `specification-separator` and `specification-link`
share the read-only rendering used by CEE and CEF and embedded by CED. They honour CEE's documented
`--cedar-specification-*` host properties and fall back to shared roles: facts and lead-in words in
`text-muted`, separators in `control-border-default`. The box keeps the outlined control's geometry,
6px and 14px of padding inside a 36px box, so a read-only value sits where its editable
counterpart's text does. The box grows for wrapped content;
consumers own suffix layout and whether a particular value intentionally truncates.
Specification roles describe quiet facts, lead-in words and discoverable authority
links, rather than replacing them with generic disabled text.

An adoption baseline is a record of existing debt, not an approval. Reasoned
exceptions are exact and count-limited by their baseline allowance: another copy is
new drift. Pruning removed findings must not leave a reusable exception budget.
