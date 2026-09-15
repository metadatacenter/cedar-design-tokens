# CEDAR Design Tokens

CEDAR's design values in one place: the font stack, the type scale, the brand palettes and the
neutrals. The [embeddable editor](https://github.com/metadatacenter/cedar-embeddable-editor), the
[embeddable designer](https://github.com/metadatacenter/cedar-embeddable-designer) and the
[embeddable term picker](https://github.com/metadatacenter/cedar-embeddable-term-picker) appear
together in one page, and they read as one product only if they agree on these.

They used to agree by being copied. The editor held the original, the picker a verbatim copy of it,
the designer a hand translation into CSS custom properties, and each copy carried a comment asking
the next person to consider a package. Copies drift: the editor moved its advisory colour from
`#856404` to `#b45309`, and the picker went on drawing the old one for a month.

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

`custom-properties.css` is generated from the partial by `npm run build`, and `npm test` checks that
it is: every literal the partial states has to appear in it, and nothing may be declared twice. It
is not a second source, which is why it is named for what it holds rather than for the module it
comes from — `tokens.css` beside `_tokens.scss` also left Sass's package importer unable to say
which of the two a consumer meant. Run the build after changing a value: a package installed from
the registry builds itself through `prepare`, but one linked from a working copy does not, so a
sibling checkout serves whatever it last compiled.

## The Type Scale

Five steps, in px:

| Variable                     | Size | What it is for                                      |
| ---------------------------- | ---- | --------------------------------------------------- |
| `$font-size-small`           | 12px | Hints, and the version stamp under a template title |
| `$font-size`                 | 14px | The body                                            |
| `$font-size-lead`            | 15px | A template description, one step above the body     |
| `$font-size-element-heading` | 18px | A nested element's heading                          |
| `$font-size-heading`         | 20px | A section break's heading                           |

px, not rem, and that is the point of it. These are web components in someone else's page, and
`rem` resolves against that page's root element — which a component neither sets nor can see. A host
with `html { font-size: 62.5% }`, a common reset idiom, would render every rem-sized thing at 62.5%
of the size it was drawn at.

A size between two steps is not on the scale. The designer ran a step below these for a while, 11px
controls under 10px labels, and every seam where it met a component at 14px showed. A glyph is not
prose and is off the scale: a count numeral sized to fit its pill, or an icon font, keeps its own
size.

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

A consumer's build resolves whatever snapshot Nexus holds when it starts, so a token change reaches
a component in this order: publish the snapshot here, then raise the dependency there. A consumer
built before the snapshot lands resolves the previous one and shows the previous values.
