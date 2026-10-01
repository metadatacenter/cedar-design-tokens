import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';

const compile = (body) => sass.compileString(`@use 'authoring'; ${body}`, { loadPaths: [process.cwd()] }).css;

test('authoring recipes are opt-in and preserve the native control host API', () => {
  assert.equal(compile(''), '');
  const css = compile('input { @include authoring.compact-control; }');
  for (const role of ['height', 'border', 'radius', 'font-size', 'line-height', 'focus'])
    assert.ok(css.includes(`var(--cedar-control-${role},`), `missing host override: ${role}`);
  assert.match(css, /min-height:/);
  assert.doesNotMatch(css, /(?:^|[;{])\s*height:/);
  assert.match(css, /font-weight: var\(--cedar-font-weight-regular, 400\)/);
});

test('authoring table closes its last row and uses authoring density without fixed control heights', () => {
  const css = compile('.editor { @include authoring.compact-table; @include authoring.density; }');
  assert.match(css, /\.editor table\s*\{[^}]*border-bottom: 1px solid var\(--cedar-border-rule\)/);
  assert.match(css, /--cedar-table-cell-padding-block-authoring/);
  assert.match(css, /--cedar-table-row-height-authoring/);
  assert.match(css, /--cedar-control-height-default: var\(--cedar-control-height-authoring\)/);
  assert.doesNotMatch(css, /overflow: hidden/);
});

test('authoring labels and values use distinct shared weights without forcing label layout', () => {
  const css = compile('label { @include authoring.label-text; }');
  assert.match(css, /font-weight: var\(--cedar-font-weight-medium, 500\)/);
  assert.doesNotMatch(css, /display:|margin:|font-style: italic/);
});

test('the authoring select arrow is the shared native-select chevron at authoring density', () => {
  const controls = sass.compileString(
    `@use 'controls'; select { @include controls.select-indicator($density: authoring); }`,
    {
      loadPaths: [process.cwd()],
    },
  ).css;
  assert.equal(compile('select { @include authoring.select-arrow; }'), controls);
});

test('settings dialog actions follow theme states without fixed content height', () => {
  const css = compile('.settings { @include authoring.settings-dialog; }');
  assert.match(css, /var\(--cedar-action-primary-hover-surface\)/);
  assert.match(css, /var\(--cedar-action-primary-pressed-surface\)/);
  assert.match(css, /gap: var\(--cedar-dialog-action-gap\)/);
  assert.match(css, /font-weight: var\(--cedar-font-weight-medium/);
  assert.doesNotMatch(css, /#[0-9a-f]{3,8}\b/i);
});
