import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
const compile = (source) => sass.compileString(`@use 'controls'; ${source}`, { loadPaths: [process.cwd()] }).css;
test('pressed and hover recipes exclude both forms of disabled action', () => {
  const css = compile('button { @include controls.action-states; @include controls.primary-action; }');
  for (const selector of css.matchAll(/([^{}]+)\{/g)) {
    if (/:hover|:active/.test(selector[1])) {
      assert.match(selector[1], /:not\(:disabled\):not\(\[aria-disabled=true\]\)/);
    }
  }
  assert.match(css, /:focus-visible/);
  assert.match(css, /opacity: 0\.45/);
});
test('input recipes preserve host focus and error overrides and avoid premature errors', () => {
  const css = compile('input { @include controls.input-states(var(--host-focus), var(--host-error)); }');
  assert.match(css, /outline: 2px solid var\(--host-focus\)/);
  assert.match(css, /outline-offset: 2px/);
  assert.match(css, /\[aria-invalid=true\]/);
  assert.match(css, /border-color: var\(--host-error\)/);
  assert.doesNotMatch(css, /:invalid\b/);
});

test('table density leaves room for its matching controls and both cell gutters', () => {
  const css = sass.compileString(
    `@use 'tokens'; a { default-row: tokens.$table-row-height; authoring-row: tokens.$table-row-height-authoring; default-control: tokens.$control-height-default; authoring-control: tokens.$control-height-authoring; default-padding: tokens.$table-cell-padding-block; authoring-padding: tokens.$table-cell-padding-block-authoring; }`,
    { loadPaths: [process.cwd()] },
  ).css;
  const values = new Map([...css.matchAll(/([\w-]+): (\d+)px/g)].map((m) => [m[1], Number(m[2])]));
  for (const profile of ['default', 'authoring']) {
    assert.ok(
      values.get(`${profile}-row`) >= values.get(`${profile}-control`) + 2 * values.get(`${profile}-padding`),
      `${profile} row clips its controls`,
    );
  }
});
