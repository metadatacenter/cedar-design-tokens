import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { readFileSync } from 'node:fs';

test('all icon adapters receive the same enforced foreground and flat glyph surface', () => {
  const css = sass.compile('css/icon-contract.scss').css;
  for (const adapter of ['svg[data-cedar-icon]', 'mat-icon', '.material-icons', '.fa', '.glyphicon'])
    assert.ok(css.includes(adapter));
  assert.match(css, /color: var\(--cedar-icon-color, var\(--cedar-color-primary, #0f7686\)\) !important/);
  for (const property of ['background: transparent', 'box-shadow: none', 'text-shadow: none'])
    assert.ok(css.includes(property + ' !important'));
  for (const role of ['inverse', 'error', 'warning', 'success', 'primary'])
    assert.ok(css.includes(`[data-cedar-icon-tone=${role}]`));
  assert.doesNotMatch(css, /stroke-width:|font-family:/);
  assert.match(css, /button:disabled[\s\S]*opacity: var\(--cedar-control-disabled-opacity, 0.45\)/);
  assert.equal(css.trim(), readFileSync('dist/icon-contract.css', 'utf8').trim());
});

test('icon Sass contract stays opt-in for encapsulated consumers', () => {
  assert.equal(sass.compileString("@use 'icon-contract';", { loadPaths: ['scss'] }).css, '');
});
