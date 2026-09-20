# CEDAR Design Tokens

CEDAR's design values in one place: the font stack, the type scale, the brand palettes and the
neutrals. The [embeddable editor](https://github.com/metadatacenter/cedar-embeddable-editor), the
[embeddable designer](https://github.com/metadatacenter/cedar-embeddable-designer) and the
[embeddable term picker](https://github.com/metadatacenter/cedar-embeddable-term-picker) appear
together in one page, and they read as one product only if they agree on these.

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

That file declares each value as a custom property under a `--cedar-` prefix — `--cedar-font-size`,
`--cedar-primary-500`, `--cedar-text-muted`. A custom property has no alias to be scoped by, so the
prefix is on the name. The declarations land on `:root` **and** `:host`, because a CEDAR component
renders inside a shadow root when it is embedded and `:root` matches the document element, which is
outside it.

`custom-properties.css` is generated from the partial by `npm run build`. `npm test` checks
that every emitted name has its own evaluated Sass value, including derived colours and palette
contrast entries, and that nothing is declared twice. Run the build after changing a value:
the registry tarball contains the compiled CSS, prepared before packing. A linked working copy
serves whatever it last compiled.

## The Type Scale

Six roles, in px:

| Variable                     | Size | What it is for                                      |
| ---------------------------- | ---- | --------------------------------------------------- |
| `$font-size-small`           | 12px | Hints, and the version stamp under a template title |
| `$font-size`                 | 14px | The body                                            |
| `$font-size-lead`            | 15px | A template description, one step above the body     |
| `$font-size-element-heading` | 18px | A nested element's heading                          |
| `$font-size-heading`         | 20px | A section break's heading                           |
| `$font-size-display`         | 34px | OpenView's artifact title                           |

px, not rem, and that is the point of it. These are web components in someone else's page, and
`rem` resolves against that page's root element — which a component neither sets nor can see. A host
with `html { font-size: 62.5% }`, a common reset idiom, would render every rem-sized thing at 62.5%
of the size it was drawn at.

Small labels and count badges use the 12px floor; enlarge their containers to fit.
Icon glyphs retain their own geometry. Interface emphasis uses `$font-weight-medium`
(500), with `$font-weight-regular` (400) for body text. Authored rich-text formatting
is separate. `$font-family-monospace` supplies the common system monospace stack
for logs and identifiers.

The `fonts/regular` and `fonts/medium` Sass exports each include just one embedded
Roboto weight. A host supplying both can load CEE's `cedar-embeddable-editor.host-fonts.js`
variant to avoid duplicate text font data; standalone CEE still embeds its fonts.
Both use the same `CEE Roboto` family name. Consumers on older token snapshots may
use `var(--cedar-font-weight-medium, 500)` and the equivalent regular/display/mono
fallbacks until their immutable package pins are advanced.

## What Does Not Belong Here

A value only one component has. The editor's layout constants — the trailing slot in a title row,
the card's inline gutter, the size of a toolbar control — stay in the editor. A shared package that
carried them would hand two other components measurements of a card they do not draw.

Anything from `@angular/material`. These values are CEDAR's, and expressing them in the vocabulary
of a framework that renames that vocabulary every couple of releases means each rename edits the
brand. The editor's `_cee-material-theme.scss` is the adapter that feeds these to whatever theming
API the installed Material version offers, and it is the only file that imports Material.

## Releasing

The package is consumed at build time and nothing published references it at run time, so it is a
`devDependency` and never reaches a public consumer. There is no npmjs release: the scoped name
routes to the CEDAR Nexus registry, which `.npmrc` configures, and a dev snapshot is what consumers
resolve.

Consumers pin an exact snapshot in `package.json` and their lockfiles. A token
change reaches them by publishing a new version, updating those pins, and
rebuilding each component. Publishing alone does not change an existing pin.

## Component adapters and host styling

The shared package defines build-time defaults. Consumers translate those values
into their own styling systems: CEE's Material adapter, CED's CSS/Tailwind aliases,
and CETP's `--cetp-*` defaults. Adapters must read tokens for shared roles; controls
must not retain copies in TypeScript objects or local stylesheets.

Host customization is explicit and tested:

- CEE/CEF and CED's native controls retain the compact-control API documented in
  [CEE's STYLING.md](https://github.com/metadatacenter/cedar-embeddable-editor/blob/develop/STYLING.md).
- CETP retains its ten documented `--cetp-*` properties, including body size and
  primary/on-primary colors. Its constraint table and search surface both consume
  them; small and lead sizes use offsets derived from this package's scale.
- Generated `--cedar-*` palette and type properties are the CSS representation of
  these defaults, not a promise that setting one will theme all three components.
  CEE's Material palette is compiled from Sass. A broader runtime theme API must
  reach rendered controls before being documented as supported.

Keep Material internals private. Do not remove existing host properties to achieve
uniformity. Geometry remains component-owned except for the established compact
control API. Hosts overriding colors must preserve status meaning and readable
foreground/background combinations.

Consumer browser tests exercise actual controls, not just property declarations.
Package tests compare the complete name/value mapping and reject swapped sizes
or missing derived and contrast entries.

## Control defaults, authoring density and spacing

The `control-*-default` tokens describe the 36px compact control. The
`control-*-authoring` tokens describe the explicit authoring profile: 32px high,
12px text, 18px line height and 2px corners. Both use `color-error` for invalid
text and borders; `color-warning` and `surface-advisory` describe advisory notices.
`color-warn` remains available for legacy palette consumers. `surface-authoring`
and `text-authoring` describe settings panels.

These defaults intentionally do **not** declare public `--cedar-control-height`,
`--cedar-control-radius` or other host override properties. The component adapters
read a host override first, then the selected profile default. Embedding CEF in
an authoring surface uses `density="authoring"`; standalone CEE/CEF retain the
compact profile unless explicitly configured otherwise.

The optional spacing scale is `space-1/2/3/4/6`: 4/8/12/16/24px. Apply it to
ordinary padding, margins and gaps; icon sizes, widths, toolbar geometry and
responsive card gutters remain component-owned.

## Embedded fonts

`@use '@org.metadatacenter/cedar-design-tokens/fonts'` emits the self-contained
Roboto 300/400/500 font faces shared by the editor and designer. Include it in
the component's unencapsulated font registrar: browsers do not register font
faces inside shadow roots. The export contains no selectors or network URLs.
The font family remains `CEE Roboto`; consumers no longer keep copies of the
font source. Each built bundle still embeds the fonts it needs.

## Monitor adoption

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

### Common styling choices

| Intent             | Sass token / CSS property                                                |
| ------------------ | ------------------------------------------------------------------------ |
| Body text          | `tokens.$font-size` / `--cedar-font-size`                                |
| Secondary hint     | `tokens.$text-muted` / `--cedar-text-muted`                              |
| Validation error   | `tokens.$color-error` / `--cedar-color-error`                            |
| Advisory notice    | `color-warning` foreground and `surface-advisory` background             |
| Ordinary gap       | `tokens.$space-2` / `--cedar-space-2` (8px)                              |
| Designer input     | Shared authoring adapter; embedded CEF uses `density="authoring"`        |
| Host customization | Existing public `--cedar-control-*` overrides; defaults remain fallbacks |

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

### Compare the real components

CED's `browser/fixtures/style-comparison.html` renders CEE, CEF, CED and CEFD
from local distribution bundles with the same sample fields. It offers both entry
densities, narrow hosts, read-only entry/field design and inherited host overrides.
Tab through controls and clear required values or enter invalid email values to
inspect focus and validation. CED itself remains editable; it has no equivalent
host read-only property. No disabled state is simulated with a cosmetic overlay.
See the frontend runbook for building/staging the two bundles and opening the page.

## Shared iconography

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

## Interaction recipes

The `controls` Sass export provides opt-in `focus-ring`, `action-states`,
`primary-action` and `input-states` mixins. Applications supply selectors; the
package supplies shared state values. Include primary styles after ordinary
action styles. `aria-disabled` styling does not disable behavior: the component
must still block activation. Use native `disabled` where appropriate.

The focus and invalid recipes accept colors so existing documented embedding
overrides can remain authoritative. Invalid styling uses `aria-invalid`, not
`:invalid`, to avoid marking an untouched required field as an error.

## Dialog and menu surfaces

`dialog-*` and `menu-*` describe shared surfaces, not application-specific widths.
Native dialogs, designer popups and Material adapters consume the same corners,
shadows, backdrop and spacing. Menu items use the shared compact control height.
Keep viewport constraints, focus trapping, dismissal and focus restoration in the
component; tokens do not implement those behaviors. The template designer host
stages the same generated properties alongside its icon module.

## Semantic color roles

Use `surface-selected`/`text-selected` for selection and `surface-row-hover` for
hover, so a pointer does not make an unselected row look selected. Status pairs
(`status-error`, `status-warning`, `status-success`, `status-info`, each with
`-text` and `-surface`) are tested for normal-text contrast of at least 4.5:1.
Retain a label or icon alongside status color. `text-destructive` is for actions,
not a replacement for an error message. Read-only surfaces remain distinct from
native disabled behavior. CETP derives its selection tint from the documented
host primary override using the shared percentage.

## Forms and table density

Use `form-label-gap`, `form-help-gap`, `form-field-gap` and `form-section-gap`
for repeated form rhythm. Help and error text share the small type role and an
18px line box. Validation timing and accessible descriptions remain component
responsibilities.

Ordinary tables use 52px minimum rows with 8px/12px cell padding; authoring tables
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

### Motion and overlay layers

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

### Visual reference

CEE's approved editable and read-only rendering is the reference for the modern
CEDAR UI. Shared values should be extracted from that reference without changing
its appearance. Authoring needs additional controls and arrangements, but does
not establish a separate visual language of gradients, elevated cards or oversized
branding. The artifact-title size, color and line-height roles preserve CEE's
existing fluid title exactly. CED's real-component browser comparisons exercise
that relationship against CEE in both display modes; CEE's screenshot baselines
remain the reference, not snapshots to update to accommodate another component.

## Shared UI patterns

Use `@use '@org.metadatacenter/cedar-design-tokens/patterns';` for opt-in Sass
recipes: artifact titles, dialog surfaces/actions, menus/items, field labels/help/errors,
toolbars, tabs, table cells and empty states. For example:

```scss
@use '@org.metadatacenter/cedar-design-tokens/patterns';
.permissions-dialog {
  @include patterns.dialog-surface;
}
```

Recipes emit no global selectors and use the same semantic roles as CEE. Consumers
retain layout constraints and behavior. See [UI contracts](UI-CONTRACTS.md) for the
interaction requirements, baseline procedure and the suites that enforce them.

## Candidate consumer CI

The `Consumer contracts` workflow checks all eight modern consumers on token pushes
and pull requests. It records the consumer revision and candidate tarball hash,
replaces only the dependency-free token package in a locked consumer install,
and verifies every published file byte for byte. All consumers build; CEE, CED,
CETP and Workspace also compare their existing screenshots in the pinned ARM64
Playwright environment. It never publishes or updates consumer baselines.
