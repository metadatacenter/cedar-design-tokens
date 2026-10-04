import test from 'node:test';
import assert from 'node:assert/strict';
import * as sass from 'sass';
import { readFileSync } from 'node:fs';

const compile = (body) => sass.compileString(`@use 'spacing'; ${body}`, { loadPaths: ['scss'] }).css;

test('spacing recipes emit nothing until selected and reject arbitrary values and token assignments', () => {
  assert.equal(compile(''), '');
  for (const args of ['padding, 13px', 'padding, invented', '--cedar-space-1, compact', 'color, compact'])
    assert.throws(() => compile(`a { @include spacing.apply(${args}); }`));
});

test('every finite spacing recipe compiles without consumer Sass variables', () => {
  const source = readFileSync('scss/_spacing.scss', 'utf8');
  const names = [...source.matchAll(/^  ([\w-]+):/gm)].map((m) => m[1]);
  assert.ok(names.length > 0);
  for (const name of names) assert.ok(compile(`a { @include spacing.apply(padding, ${name}); }`).includes('padding:'));
});

test('control alignment retains the existing geometry without local arithmetic', () => {
  assert.match(compile('a { @include spacing.apply(padding, view-switch); }'), /space-1\) \* 1.25/);
  assert.match(compile('a { @include spacing.apply(padding, compact); }'), /padding: 2px/);
  assert.doesNotMatch(compile('a { @include spacing.apply(padding, compact-row); }'), /var\(/);
  assert.match(compile('a { @include spacing.apply(padding, preview-select); }'), /space-2\) \* 3.75/);
});

test('named measurements say what a size is for and follow density where a control does', () => {
  const css = compile(
    'a { small: spacing.$icon-button-small; cell: spacing.$control-cell-width; brand: spacing.$brand-mark-size; chevron: spacing.$designer-outline-chevron-size; }',
  );
  assert.match(css, /small: 24px/);
  assert.match(css, /chevron: 12px/);
  assert.match(css, /brand: 36px/);
  // An authoring density re-points the default control height, so the column must read the property.
  assert.match(css, /cell: calc\(var\(--cedar-control-height-default\) \+ 2 \* var\(--cedar-space-2\)\)/);
  assert.match(
    compile('a { @include spacing.apply(padding-top, control-reserve); }'),
    /padding-top: var\(--cedar-control-height-default\)/,
  );
});
