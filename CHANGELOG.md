# Changelog

## Unreleased

- The `spacing` recipes `element-narrow-inset` (4%) and `element-narrow-heading-inset` (8%) hold
  the editor's proportional element insets in a narrow component, and `spacing.apply` accepts
  `--_cee-element-body-inset`. The editor had stated both percentages directly.
- `patterns.drag-placeholder` fades the item a drag will drop. The designer's outline and child
  picker each spelled out their own opacity, 0.25 and 0.3; both now take 0.25.
- `spacing.$designer-outline-chevron-size` names the 12px chevron that collapses an element in the
  designer's outline, which no shared icon size fits.
- `spacing.$template-header-field-width` is removed. It sized the identifier column of the
  designer's template header, and the designer now edits a template's or element's identifier in
  its metadata settings. No other consumer read it.
- A resource card's name sits on the 21px body text line, like other 14px text, rather than the 20px
  line it had carried since it was a Workspace literal.
- `patterns.spinner` draws the continuous progress indicator OpenView and Monitoring each copied,
  and owns its rotation, so `motion-duration-spinner` is retired. Its arc takes the theme colour;
  Monitoring's had been grey.
- `patterns.icon-button($size)` draws an icon-only button's box: `small` (24px) for row actions and
  handles, `default` at the control height.
- The `spacing` export names the box sizes no role describes, for the designer, Workspace and the
  editor, and gains the `control-reserve` recipe and `padding-top` as a recipe property. A consumer
  reads a named size instead of a spacing step or control height whose value matches.
- `resource-card-icon` and `resource-card-heading` size their slot with `icon-size-large`, the
  settings-dialog badge and the save-state dot with sizes of their own. Each renders as before.
- A status text colour may fill a small indicator. A rule colour never draws text.
- `--strict` fails on a token that only one consumer reads, counting the recipes each consumer
  includes and the compiled stylesheets it imports. The JSON report names each such token and its
  reader under `singleReaderTokens`. The `Unused tokens` workflow is now `Token readers`.
- `shadow-dialog` is retired for `shadow-overlay`, so a dialog floats like a menu. Its backdrop already
  separates it from the page.
- `status-unsaved-dot` is retired for `status-warning-text`. The save-state mark turns from yellow
  `#eab308` to amber `#b45309`, and its contrast on white rises from 1.9:1 to 5.0:1.
- `motion-ease-enter` is retired for `motion-ease-standard`. Only the designer read it, for three
  fade-ins, and both curves decelerate.
- `table-row-height` is retired for `spacing.$table-row-height`, the same 44px derived from the
  default control height and `space-1`.
- `textarea-min-rows-default` is retired. Only the embeddable editor read it, as the default of its
  own `--cedar-textarea-min-rows` host property, so the editor now states that default itself.
- The Sass modules and their font faces sit under `scss/`, and the sources of the compiled
  stylesheets under `css/`, each named after the file it builds. The export names are unchanged,
  but they now resolve only through the package's `exports`: Angular's builder reads it, and a
  direct `sass` build needs the package importer, because a load path alone no longer finds them.
  A path into the package that bypasses `exports`, such as `fonts/_roboto-400.scss`, has moved.
- The type scale is four sizes. `font-size-large` (18px) replaces `font-size-element-heading` and
  the 20px `font-size-heading`, so a section break takes the size of a nested element's heading and
  no longer outranks the element that contains it. Both names are retired.
- The artifact title's floor rises from 19px to 20px, keeping a title above every heading on a
  narrow host.
- `line-height-tight`, 1, for an icon, caret, badge or one-line label whose box is exactly its type
  size. CEE, CED, CETP and Monitoring each set that value locally.
- `patterns.section-heading`, `patterns.notice` with `notice.css`, and `controls.secondary-action`
  with `secondary-action.css`.
- The breadcrumb trail mutes its ancestors, links included, and colours the current location.
- Validation-summary issue lines take no control box and no hover fill.
- The duplicate `compact-static` and `constraint-row` spacing recipes are gone; use `compact` and
  `compact-row`.
- Adoption policy 4 reads Material's theme inputs, styles that skip the template scan, Tailwind's
  arbitrary properties and further utility families, `className` attributes, SVG text attributes,
  and `.sass`, `.tsx` and `.jsx` files. An interpolated or `@property` override of a shared token is
  refused like a written one.
- A change cannot drop a contracted surface whose source remains, and a contract must suit the kind
  of element it checks.
- `patterns.visually-hidden` and `patterns.tooltip-surface`, with `tooltip.css` for plain-CSS hosts.
- The `fonts` export embeds the 400 and 500 faces only; nothing used the 300 weight.
- The rendered surface check also reads paint: backgrounds, borders, outlines and box shadows take
  only the vocabulary's colours. Generated `::before` and `::after` text, placeholders and SVG
  labels are checked as text, the shared family needs a loaded face for each weight a surface uses,
  and visually hidden text is skipped.
- Adoption policy 3 reads focus outlines, single-corner radii, opacity, easing, `color-mix()`, a
  z-index marked important and negative lengths. `--upgrade-policy` moves a repository up one step.
- `--strict` fails on baseline allowances the code no longer needs, on a pinned package that lacks
  a token the repository reads, and on a pin naming a commit the checkout does not have. The
  version report compares pins with the version the checkout's head publishes under.
- The `Unused tokens` workflow checks every consumer for a reader of each token.
- CETP, Monitoring and Bridging own surface registries with rendered contracts, and the check now
  requires all three, with Monitoring's and Bridging's literal routes registered as OpenView's are.
- The adoption check reads a page's style elements and inline scripts. A consumer without npm pins
  the package through a vendored copy of its compiled stylesheets and a manifest of their digests,
  and the session page `cedar-cee-mcp` serves is checked that way. `--repo` takes a path under the
  workspace.
- `patterns.save-state-dot` and `save-state-dot-modified`, and `save-state.css` for plain-CSS hosts,
  draw the hollow and filled save-state mark.
- The authoring recipes take their weight fallbacks from the tokens, and the settings badge and
  check use the pill radius and the small icon size; the emitted values are unchanged.
- The breadcrumb trail keeps one weight, and every tab and authoring label is muted medium. A tab
  row's first label starts on the content edge.
- The `spacing` export holds the finite spacing recipes, and the adoption check rejects spacing
  arithmetic and unresolved Sass aliases in consumers.
- Registered pages, menus, dialogs and summaries are walked against the scale as rendered.
  Checkbox marks count as glyphs.
- `controls.search-clear-indicator` themes a search field's clear button.
- A local adoption run compares each repository with its upstream branch, as CI does.
- The vocabulary is 61 tokens, down from 196. The palette steps, the accent and contrast entries,
  and every component-tier alias are no longer emitted; the recipes read the spacing scale and the
  colour roles directly. `tools/retired-tokens.json` names the replacement for each retired token.
- The type scale is five sizes: the 15px lead and the 34px display size are retired.
- One corner radius (`radius`, 4px) and `radius-pill` replace the control, dialog, menu and
  authoring radii. One rule colour replaces the light rule and the table divider, and one control
  outline replaces the `#777` and `#ccc` borders.
- `color-primary-strong`, `text-title`, `surface-subtle`, `row-height-compact`, `shadow-overlay`,
  `shadow-dialog` and `line-height-heading` are the roles that absorbed the retired tokens.
- Ordinary listing rows are 44px with a 4px cell gutter, which every Workspace table already drew
  through local overrides.
- `patterns.tabs` and `patterns.tab` draw every tab row, and `custom-properties.declare` declares
  the shared properties on a component's own shadow host.
- The adoption check rejects a consumer that redefines a shared token, names the replacement for a
  retired one, and fails when a token has no consumer.

## First Snapshot (2026-09-15)

- CEDAR's font stack, type scale, brand palettes and neutrals, extracted from the
  three copies that had been holding them: the embeddable editor's `_cee-tokens.scss`, the term
  picker's verbatim copy of it, and the designer's hand translation into CSS custom properties.
- The advisory colour is `#b45309`. The editor chose it deliberately, where the picker's copy had
  kept the `#856404` the editor started from.
- The type scale gains the 18px step a nested element's heading takes, which the editor stated in a
  comment and every consumer then wrote out as a literal.
