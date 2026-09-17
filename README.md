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
component repository's new and existing style findings, advisory spacing/geometry findings,
resolved debt, and token manifest/lock versions. `--repo cedar-embeddable-designer` selects
one repository; `--all` includes existing findings; `--json` supports dashboards.
`--strict` fails on new color/typography findings or missing baselines. No network,
Nexus credential or frontend build is needed. The modern Angular Workspace is included. The retiring AngularJS application
shells remain excluded; their styles are not migration targets.

This is a source heuristic, not an adoption percentage or an accessibility audit.
It scans first-party CSS/SCSS/Less under `src` and `app`, including unignored new
files. Vendor/assets, generated/ignored files, fixtures and the Material icon
font are excluded. Inline HTML/TypeScript styles, utility classes and runtime
computed styles are outside this first check. A matching dependency version
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
- For an intentional value, add its reported ID to the baseline's `exceptions`
  object with a concrete reason, such as an external vocabulary's fixed swatch.
  Exceptions match that exact declaration, not an entire file or rule.
- `--init-baseline` creates the initial inventory and refuses to replace one.
  Don't delete and regenerate a baseline to make CI green.

The consumer CI workflows call this repository's reusable `adoption.yml` workflow
and upload `adoption.json`, even when the strict gate fails. Pull requests compare
against the **base revision's** baseline and exceptions, so expanding them in the
same PR cannot conceal new drift. Initial rollout, where the base has no baseline,
uses the new inventory and emits a review notice. A later intentional exception
must be reviewed and merged separately before the styling change it permits.
Changes to the scanner need tests and a review of their effect on existing findings.

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
