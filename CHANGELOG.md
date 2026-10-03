# Changelog

## Unreleased

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
