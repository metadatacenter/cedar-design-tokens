import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { readFileSync } from 'node:fs';
import { getIcon } from '../dist/icons.js';
const compile = (source) => sass.compileString(`@use 'controls'; ${source}`, { loadPaths: ['scss'] }).css;
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

test('table density keeps compact action rows at 28px and ordinary controls unclipped', () => {
  const css = sass.compileString(
    `@use 'sass:math'; @use 'tokens'; a { default-row: tokens.$table-row-height; authoring-row: tokens.$row-height-compact; default-control: tokens.$control-height-default; authoring-control: tokens.$control-height-authoring; default-padding: tokens.$space-1; authoring-padding: math.div(tokens.$space-1, 2); }`,
    { loadPaths: ['scss'] },
  ).css;
  const values = new Map([...css.matchAll(/([\w-]+): (\d+)px/g)].map((m) => [m[1], Number(m[2])]));
  assert.equal(values.get('authoring-row'), 28);
  assert.equal(values.get('authoring-padding'), 2);
  assert.ok(values.get('authoring-row') >= 24 + 2 * values.get('authoring-padding'));
  for (const profile of ['default']) {
    assert.ok(
      values.get(`${profile}-row`) >= values.get(`${profile}-control`) + 2 * values.get(`${profile}-padding`),
      `${profile} row clips its controls`,
    );
  }
});

test('overlay layers are ordered within a host stacking context', () => {
  const css = sass.compileString(
    "@use 'tokens'; a { sticky: tokens.$layer-sticky; menu: tokens.$layer-menu; modal: tokens.$layer-modal; overlay: tokens.$layer-overlay; tooltip: tokens.$layer-tooltip; }",
    { loadPaths: ['scss'] },
  ).css;
  const levels = [...css.matchAll(/: (\d+);/g)].map((m) => Number(m[1]));
  assert.equal(levels.length, 5);
  assert.ok(levels.every((n, i) => i === 0 || n > levels[i - 1]));
});
test('reduced motion preserves animation completion and covers pseudo elements', () => {
  const css = sass.compileString("@use 'motion'; @include motion.reduced-motion;", { loadPaths: ['scss'] }).css;
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /\*::before/);
  assert.match(css, /\*::after/);
  assert.match(css, /animation-duration: 0.01ms !important/);
  assert.match(css, /animation-iteration-count: 1 !important/);
  assert.match(css, /transition-duration: 0.01ms !important/);
});

test('choice recipes share typography and grow beyond a minimum row height', () => {
  const css = compile('.choice { @include controls.choice-text; @include controls.choice-row; }');
  assert.match(css, /--cedar-row-height-compact, 28px/);
  assert.match(css, /--cedar-control-font-size, var\(--cedar-font-size, 14px\)/);
  assert.match(css, /--cedar-control-line-height, var\(--cedar-control-line-height-default, 21px\)/);
  assert.match(css, /--cedar-font-weight-regular, 400/);
  assert.match(css, /letter-spacing: normal/);
  assert.doesNotMatch(css, /(?:^|[;{}])\s*height:/m);
});

test('native choices use runtime tokens without replacing browser semantics or geometry', () => {
  const css = compile('input { @include controls.native-choice; }');
  assert.match(css, /accent-color: var\(--cedar-color-primary, #0f7686\)/i);
  assert.match(css, /:focus-visible/);
  for (const role of ['focus-ring-width', 'color-primary', 'focus-ring-offset'])
    assert.ok(css.includes(`var(--cedar-${role},`));
  assert.doesNotMatch(css, /(?:appearance|width|height|padding|opacity)\s*:/);
});

test('the select chevron reserves its icon column at the inline inset and follows the host theme', () => {
  const css = compile('select { @include controls.select-indicator; }');
  assert.match(css, /appearance: none/);
  assert.match(
    css,
    /padding-inline-end: calc\(2 \* var\(--cedar-space-3, 12px\) \+ var\(--cedar-icon-size-small, 16px\)\)/,
  );
  assert.equal([...css.matchAll(/var\(--cedar-color-primary, #0f7686\)/gi)].length, 4);
  assert.match(
    css,
    /background-position: right calc\(var\(--cedar-space-3, 12px\) \+ 8px\) center, right calc\(var\(--cedar-space-3, 12px\) \+ 3px\) center/,
  );
  assert.doesNotMatch(css, /url\(/);
});

test('authoring density keeps the tighter control inset and rejects unknown densities', () => {
  const css = compile('select { @include controls.select-indicator($density: authoring); }');
  assert.match(css, /padding-inline-end: calc\(var\(--cedar-space-2, 8px\) \+ var\(--cedar-icon-size-small, 16px\)\)/);
  assert.match(css, /right calc\(var\(--cedar-space-2, 8px\) \+ 3px\) center/);
  assert.throws(() => compile('select { @include controls.select-indicator($density: huge); }'), /Select density/);
});

test('picker indicators paint a registry glyph in the icon role and keep the native control', () => {
  const css = compile("input { @include controls.picker-indicator('field-date'); }");
  assert.match(css, /input::-webkit-calendar-picker-indicator \{/);
  assert.match(css, /background: var\(--cedar-icon-color, var\(--cedar-color-primary, #0f7686\)\)/i);
  const masks = [...css.matchAll(/mask: url\("data:image\/svg\+xml,([^"]+)"\)/g)];
  assert.equal(masks.length, 2);
  // The mask is the registry's calendar, not a copy of it.
  assert.ok(decodeURIComponent(masks[0][1]).includes(getIcon('field-date').body.replace(/\s+/g, ' ')));
  assert.doesNotMatch(css, /appearance/);
  assert.throws(() => compile("input { @include controls.picker-indicator('no-such-icon'); }"), /Unknown CEDAR icon/);
});

test('the native-choices stylesheet themes selects and pickers beneath its root class', async () => {
  const css = readFileSync('dist/native-choices.css', 'utf8');
  assert.match(
    css,
    /\.cedar-native-choices select:not\(\[multiple\]\):not\(\[size\]\):not\(\[data-cedar-select-icon\]\)/,
  );
  assert.match(css, /\.cedar-native-choices :is\(input\[type=date\]/);
  assert.match(css, /\.cedar-native-choices input\[type=time\]::-webkit-calendar-picker-indicator/);
});

test('search fields clear with the registry close glyph in the icon role and keep the native button', () => {
  const css = compile('input { @include controls.search-clear-indicator; }');
  assert.match(css, /::-webkit-search-cancel-button/);
  assert.match(css, /background: var\(--cedar-icon-color, var\(--cedar-color-primary, #0f7686\)\)/i);
  assert.match(css, /mask: url\("?'?data:image\/svg\+xml/);
  assert.doesNotMatch(css, /display: none/);
});

test('the secondary action keeps host control overrides and the shared hover', () => {
  const css = compile('button { @include controls.secondary-action; }');
  assert.match(css, /min-height: var\(--cedar-control-height, var\(--cedar-control-height-default\)\)/);
  assert.match(css, /border: 1px solid var\(--cedar-control-border, var\(--cedar-control-border-default\)\)/);
  assert.match(css, /color: #0f7686/);
  assert.match(css, /:hover:not\(:disabled\):not\(\[aria-disabled=true\]\)/);
});
