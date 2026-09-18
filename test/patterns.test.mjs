import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { readFileSync } from 'node:fs';

const roles = new Set(
  [...readFileSync('dist/custom-properties.css', 'utf8').matchAll(/(--cedar-[\w-]+)\s*:/g)].map((m) => m[1]),
);
const names = [
  'artifact-title',
  'dialog-surface',
  'dialog-actions',
  'menu-surface',
  'menu-item',
  'field-label',
  'field-help',
  'field-error',
  'toolbar',
  'tabs',
  'table-cell',
  'empty-state',
];
for (const name of names) {
  test(`${name} uses registered shared roles and stays opt-in`, () => {
    const css = sass.compileString(`@use 'patterns'; .consumer { @include patterns.${name}; }`, {
      loadPaths: [process.cwd()],
    }).css;
    for (const role of css.matchAll(/var\((--cedar-[\w-]+)/g))
      assert.ok(roles.has(role[1]), `Unknown role: ${role[1]}`);
    assert.match(css, /^\.consumer/);
    assert.doesNotMatch(css, /#(?:[\da-f]{3})\b|rgb\(|font-family:/i);
  });
}
test('recipes emit nothing until used', () => {
  assert.equal(sass.compileString("@use 'patterns';", { loadPaths: [process.cwd()] }).css, '');
});
