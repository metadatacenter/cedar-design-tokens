# CEDAR Design Tokens

Shared typography, colors, spacing, controls, fonts and icons for CEDAR's browser
applications and embeddable components. Values are defined in
[`scss/_tokens.scss`](scss/_tokens.scss); framework adapters and shared recipes
apply them to the UI.

See [UI contracts](UI-CONTRACTS.md) for behavior, accessibility and visual review requirements.

## Usage

Install `@org.metadatacenter/cedar-design-tokens` through the CEDAR Nexus registry
configured in `.npmrc`. Consumers pin an exact development version and lockfile.
The package is a build-time `devDependency` in published components; it must not
become a runtime dependency of their public npm packages.

For Sass:

```scss
@use '@org.metadatacenter/cedar-design-tokens/tokens' as tokens;

.hint {
  font-size: tokens.$font-size-small;
  color: tokens.$text-muted;
}
```

Angular resolves these package exports directly. With the Sass CLI, use
`--pkg-importer=node` and prefix the import with `pkg:`; a load path alone is insufficient.

For CSS, import through your bundler:

```css
@import '@org.metadatacenter/cedar-design-tokens/custom-properties.css';

.hint {
  font-size: var(--cedar-font-size-small);
  color: var(--cedar-text-muted);
}
```

Generated properties apply to both `:root` and `:host`. A Sass component can also
include `custom-properties.declare` on its shadow root's `:host`:

```scss
@use '@org.metadatacenter/cedar-design-tokens/custom-properties';

:host {
  @include custom-properties.declare;
}
```

## Token reference

The current inventory contains **55 CSS tokens**. Names below become Sass
variables (`$space-2`) and CSS properties (`--cedar-space-2`). The
[inventory test](test/inventory.test.mjs) checks the emitted set.

### Typography

| Token                                       | Default                                          | Use                                   |
| ------------------------------------------- | ------------------------------------------------ | ------------------------------------- |
| `font-family`                               | `'CEE Roboto', 'Helvetica Neue', sans-serif`     | Interface text                        |
| `font-family-monospace`                     | `ui-monospace, SFMono-Regular, Menlo, monospace` | Code, logs, identifiers               |
| `font-weight-regular`, `font-weight-medium` | 400, 500                                         | Body; labels and headings             |
| `font-size-small`                           | 12px                                             | Hints and secondary facts             |
| `font-size`                                 | 14px                                             | Body, controls, menus and tabs        |
| `font-size-large`                           | 18px                                             | Section headings                      |
| `font-size-artifact-title`                  | `clamp(20px, 3cqi, 26px)`                        | Page, artifact and dialog titles      |
| `line-height-heading`, `line-height-tight`  | 1.25, 1                                          | Headings; icons and single-line boxes |

Sizes use pixels so an embedding page's root font size cannot shrink component
text. Titles scale with the nearest eligible query container, with a 20–26px range.

### Colors

| Token                                           | Default               | Use                                        |
| ----------------------------------------------- | --------------------- | ------------------------------------------ |
| `color-primary`                                 | `#0f7686`             | Theme color, links, focus and actions      |
| `color-primary-strong`                          | `#0b6373`             | Primary text on tints; filled-action hover |
| `color-on-primary`                              | `#ffffff`             | Text and icons on filled actions           |
| `text-primary`                                  | `rgba(0, 0, 0, 0.87)` | Body text                                  |
| `text-muted`                                    | `#555555`             | Secondary text and placeholders            |
| `text-title`                                    | `#173f3e`             | Titles                                     |
| `border-rule`                                   | `#d7e0df`             | Dividers and surface outlines              |
| `control-border-default`                        | `rgba(0, 0, 0, 0.38)` | Editable control outlines                  |
| `surface-raised`                                | `#ffffff`             | Pages, cards, menus, dialogs and controls  |
| `surface-subtle`                                | `#f4f6f6`             | Panels, read-only values and hovered rows  |
| `surface-selected`                              | `#e4f1f1`             | Selection and hovered actions              |
| `status-error-text`, `status-error-surface`     | `#b42318`, `#fef3f2`  | Errors                                     |
| `status-warning-text`, `status-warning-surface` | `#b45309`, `#fff8e5`  | Warnings                                   |
| `status-success-text`, `status-success-surface` | `#176b3a`, `#ecfdf3`  | Success                                    |
| `dialog-backdrop`                               | `rgba(0, 0, 0, 0.4)`  | Modal scrim                                |

Use roles for their meaning, not because their current values match. Status colors
need a label or icon; their foreground/background pairs are contrast-tested.
Palette maps `brand-primary` and `brand-accent`, plus `font-family-string`, are
Sass-only adapter inputs. They are not CSS tokens; the accent map serves legacy
Material M2 adapters.

### Controls, spacing and effects

| Token                                                                         | Default                          |
| ----------------------------------------------------------------------------- | -------------------------------- |
| `control-height-default`, `control-height-authoring`                          | 36px, 32px                       |
| `control-line-height-default`, `control-line-height-authoring`                | 21px, 18px                       |
| `control-disabled-opacity`                                                    | 0.45                             |
| `focus-ring-width`, `focus-ring-offset`                                       | 2px, 2px                         |
| `row-height-compact`                                                          | 28px                             |
| `space-1`, `space-2`, `space-3`, `space-4`, `space-6`                         | 4px, 8px, 12px, 16px, 24px       |
| `radius`, `radius-pill`                                                       | 4px, 9999px                      |
| `icon-size-small`, `icon-size-default`, `icon-size-large`                     | 16px, 20px, 24px                 |
| `shadow-overlay`                                                              | `0 4px 18px rgba(0, 0, 0, 0.13)` |
| `motion-duration-fast`, `motion-duration-normal`                              | 120ms, 200ms                     |
| `motion-ease-standard`                                                        | `cubic-bezier(0.2, 0, 0, 1)`     |
| `layer-sticky`, `layer-menu`, `layer-modal`, `layer-overlay`, `layer-tooltip` | 10, 100, 1000, 1100, 1200        |

`authoring.density` selects authoring control defaults. Explicit host overrides
still win. Ordinary table rows use `spacing.$table-row-height` (44px); compact
rows use `row-height-compact` as a minimum and grow for wrapped content.

## Recipes, fonts and icons

Sass recipes are opt-in: consumers choose selectors and retain behavior and layout
constraints. Import each module through the package export, as in the token example.

| Export                                      | Provides                                                                                                                                                                                 |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`patterns`](scss/_patterns.scss)           | Titles, menus, dialogs, forms, tabs, breadcrumbs, resource cards, validation summaries, read-only specifications, notices, tooltips, drag placeholders and selected and invalid outlines |
| [`controls`](scss/_controls.scss)           | Focus, action/input states, choice rows and native control indicators                                                                                                                    |
| [`authoring`](scss/_authoring.scss)         | Compact controls/tables, labels, entry rows and settings-dialog structure                                                                                                                |
| [`spacing`](scss/_spacing.scss)             | Named measurements and derived insets, e.g. `spacing.apply(padding, compact-row)`                                                                                                        |
| [`motion`](scss/_motion.scss)               | `reduced-motion`; also available as `motion.css`                                                                                                                                         |
| [`icon-contract`](scss/_icon-contract.scss) | Shared icon foreground and state rules; also available as `icon-contract.css`                                                                                                            |

Plain CSS exports include `notice.css`, `tooltip.css`, `secondary-action.css`,
`save-state.css`, `validation-summary.css` and `native-choices.css`. Their class
names are defined in the corresponding [`css/`](css/) sources. Load
`custom-properties.css` alongside them.

Import `fonts` in an unencapsulated font registrar to embed Roboto 400 and 500.
`fonts/regular` and `fonts/medium` emit individual weights. Font faces must be
registered outside shadow roots; the files contain no network URLs.

Import `getIcon`, `iconSvg`, `iconStyle` and `IconName` from the `icons` export.
[`icons/manifest.json`](icons/manifest.json) maps semantic names to a pinned Lucide
version. Use this registry rather than local SVG geometry, icon fonts or direct
Lucide imports. Unknown names throw. Icons use 16/20/24px sizes and a 2-unit stroke;
icon-only controls need an accessible name. `icons.svg` supplies SVG symbols for
hosts without JavaScript adapters.

## Host styling and shared values

Keep documented `--cedar-control-*`, `--cedar-specification-*` and `--cetp-*`
overrides working. The supported names are registered in
[`tools/host-properties.json`](tools/host-properties.json); CEE's
[STYLING.md](https://github.com/metadatacenter/cedar-embeddable-editor/blob/develop/STYLING.md)
describes its host API. Generated token properties alone do not promise uniform
runtime theming across every framework adapter.

Do not redefine shared tokens locally or calculate new spacing values in consumers.
Use the `spacing` recipes for derived measurements. Component layout constraints
remain local; framework dependencies stay in adapters. Add a token only for a new
shared role with at least two consumers, and update the inventory test with it.
Retired names and replacements live in [`tools/retired-tokens.json`](tools/retired-tokens.json).

## Checks and maintenance

From the CEDAR workspace:

```bash
cedarcli check design-tokens --strict
cedarcli check design-tokens --repo cedar-embeddable-designer --strict
cedarcli check design-tokens --repo <repo> --prune-baseline
cedarcli check components
```

The adoption check covers source styles, icons, host properties, dependency pins
and surface registration. It rejects new drift and obsolete baseline allowances.
CI compares allowances with the trusted base revision; expanding a baseline beside
a styling change cannot hide it. Use `--all` for existing findings and `--json` for
reports. A matching source pin does not prove a current served bundle; use
`check components` for that.

### Maintained surface registry

Each modern frontend owns `.ui-surfaces.json`. Register surfaces and their source,
selector, scenario, states and browser tests together. Keep IDs stable when labels
change; remove registrations when their surfaces are removed.

```bash
cedarcli check design-tokens --sync-surfaces
cedarcli check design-tokens --surface-inventory "$CEDAR_HOME/output/modern-workspace-ui-inventory.md"
```

Sync copies the central browser helpers into consumer test directories. Never edit
those generated copies. [UI contracts](UI-CONTRACTS.md#verification) explains what
the source gate and rendered tests verify.

## Development and publishing

Use the Node version in `.nvmrc`. After loading the CEDAR develop profile:

```bash
npm ci
npm test
npm run format:check
```

`npm test` builds the CSS and icons, then runs package tests. After changing token
values, run `npm run surfaces:defaults` to refresh the offline browser defaults.
Checker changes also require `python3 -m unittest discover -s tools -p 'test_*.py'`.

[Consumer CI](.github/workflows/consumers.yml) tests a candidate tarball against
locked consumer dependencies, including the configured browser and screenshot
suites. It neither publishes nor updates visual baselines.

Publish a pushed `develop` head through:

```bash
cedarcli publish components --component tokens --apply
```

Nexus versions follow `<base>-dev.<UTC-commit-date>.<8-character-head>`; the `dev`
tag identifies the latest publication. Advance consumer pins and lockfiles, then
rebuild to adopt it. Non-npm consumers vendor compiled assets with a version and
SHA-256 manifest checked by the adoption gate. See the
[frontend runbook](https://github.com/metadatacenter/cedar-development/blob/develop/ops/FRONTEND-RUNBOOK.md)
for consumer build and deployment procedures.
