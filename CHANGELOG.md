# Changelog

## Unreleased

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

- First release. CEDAR's font stack, type scale, brand palettes and neutrals, extracted from the
  three copies that had been holding them: the embeddable editor's `_cee-tokens.scss`, the term
  picker's verbatim copy of it, and the designer's hand translation into CSS custom properties.
- The advisory colour is `#b45309`. The editor chose it deliberately, where the picker's copy had
  kept the `#856404` the editor started from.
- The type scale gains the 18px step a nested element's heading takes, which the editor stated in a
  comment and every consumer then wrote out as a literal.
